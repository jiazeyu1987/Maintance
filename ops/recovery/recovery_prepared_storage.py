"""Apply explicit application storage connections after restoring an empty target."""
import ipaddress
import re


def need(value, message):
    if not value:
        raise ValueError(message)


def literal(value):
    return 'CONVERT(0x' + value.encode('utf-8').hex() + ' USING utf8mb4)'


def connection_update(database, policy, observed, endpoint, access, secret):
    need(re.fullmatch(r'[A-Za-z0-9_-]+', database), 'FILE_STORAGE_DATABASE_INVALID')
    need(type(policy['id']) is int and policy['id'] > 0, 'FILE_STORAGE_ID_INVALID')
    need(observed['id'] == policy['id'] and observed['bucket'] == policy['bucket'] and
         observed['endpoint'] in [*policy['sourceEndpoints'], endpoint], 'FILE_STORAGE_SCOPE_CHANGED')
    need(re.fullmatch('[a-f0-9]{64}', observed['sha256']), 'FILE_STORAGE_HASH_INVALID')
    need(access and secret, 'FILE_STORAGE_CREDENTIAL_MISSING')
    fields = [('endpoint', endpoint), ('accessKey', access), ('accessSecret', secret)]
    assignments = ','.join("'$." + key + "'," + literal(value) for key, value in fields)
    sql = ('UPDATE `' + database + '`.infra_file_config SET config=JSON_SET(config,' + assignments +
           ') WHERE id=' + str(policy['id']) + " AND deleted=b'0' AND SHA2(config,256)='" + observed['sha256'] + "';")
    receipt = dict(id=policy['id'], bucket=policy['bucket'], beforeSha256=observed['sha256'],
                   endpoint=endpoint, changedFields=[key for key, _ in fields])
    return sql, receipt


def adapt_file_storage(native):
    policies = native.config.get('preparedFileStorage', [])
    if not policies:
        return None
    need(native.config.get('preparedEmptyTarget') is True and not native.running_applications,
         'FILE_STORAGE_REQUIRES_STOPPED_EMPTY_TARGET')
    need(len({item['id'] for item in policies}) == len(policies), 'FILE_STORAGE_DUPLICATE_ID')
    native.bound()
    database = native.config['database']
    need(re.fullmatch(r'[A-Za-z0-9_-]+', database), 'FILE_STORAGE_DATABASE_INVALID')
    table = '`' + database + '`.infra_file_config'
    columns = {line.split('\t')[0] for line in native.mysql.query('DESCRIBE ' + table + ';').splitlines()}
    need({'id', 'config', 'deleted'} <= columns, 'FILE_STORAGE_SCHEMA_INVALID')
    endpoint = 'http://' + str(ipaddress.IPv4Address(native.config_services['minio']['ip'])) + ':9000'
    access = native.secret('minio', 'MINIO_ROOT_USER')
    secret = native.secret('minio', 'MINIO_ROOT_PASSWORD')
    updates = []
    for policy in policies:
        need(type(policy['id']) is int and policy['id'] > 0, 'FILE_STORAGE_ID_INVALID')
        row = native.mysql.query("SELECT id,JSON_UNQUOTE(JSON_EXTRACT(config,'$.bucket'))," +
              "JSON_UNQUOTE(JSON_EXTRACT(config,'$.endpoint')),SHA2(config,256) FROM " + table +
              " WHERE deleted=b'0' AND id=" + str(policy['id']) + ';').splitlines()
        need(len(row) == 1, 'FILE_STORAGE_CONFIGURATION_MISSING')
        parts = row[0].split('\t')
        need(len(parts) == 4, 'FILE_STORAGE_CONFIGURATION_INVALID')
        observed = dict(id=int(parts[0]), bucket=parts[1], endpoint=parts[2], sha256=parts[3])
        updates.append(connection_update(database, policy, observed, endpoint, access, secret))
    # Credentials are sent through stdin, never process arguments or receipts.
    command = ['exec', '-i', native.db_container, native.policy['environmentMysqlClientPath'],
               '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost',
               '--batch', '--skip-column-names']
    receipts = []
    for statement, receipt in updates:
        native.bound()
        verify = ' AND '.join("JSON_UNQUOTE(JSON_EXTRACT(config,'$." + key + "'))=" + literal(value)
                              for key, value in [('endpoint', endpoint), ('accessKey', access), ('accessSecret', secret)])
        batch = (statement + '\nSELECT ROW_COUNT();\nSELECT SHA2(config,256),(' + verify + ') FROM ' + table +
                 ' WHERE id=' + str(receipt['id']) + ';\n')
        result = native.docker(command, input_bytes=batch.encode('utf-8'), mutation=True).decode('utf-8').splitlines()
        need(len(result) == 2 and result[0] in ('0', '1'), 'FILE_STORAGE_UPDATE_FAILED')
        after = result[1].split('\t')
        need(len(after) == 2 and after[1] == '1', 'FILE_STORAGE_READBACK_FAILED')
        receipt['afterSha256'] = after[0]
        receipts.append(receipt)
    from recovery_engine import write
    return write(native.root / 'prepared-file-storage.json', dict(state='SUCCEEDED', configurations=receipts))
