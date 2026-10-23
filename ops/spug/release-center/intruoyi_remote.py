"""IntRuoyi remote inspection. Credential values never leave the target host."""
import hashlib
import json
import re
import subprocess
import sys


def run(args, data=None, timeout=120):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        # Docker/MySQL errors can echo runtime configuration. Do not return them.
        code = re.search(rb'ERROR\s+\d+\s+\([A-Z0-9]+\)', result.stderr)
        raise RuntimeError('%s operation failed (exit %s)%s' % (args[0], result.returncode, ': '+code[0].decode('ascii') if code else ''))
    return result.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def sql(profile, query):
    database = profile['database']
    environment = dict(item.split('=', 1) for item in inspect(database)['Config']['Env'])
    if not environment.get('MYSQL_DATABASE'):
        raise ValueError('Database container has no explicit MYSQL_DATABASE')
    if 'MYSQL_ROOT_PASSWORD_FILE' in environment:
        auth = 'export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; '
    elif environment.get('MYSQL_ROOT_PASSWORD'):
        auth = 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; '
    else:
        raise ValueError('Database container has no configured root credential source')
    return run(['docker', 'exec', '-i', database, 'sh', '-c', auth + 'exec mysql -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names "$MYSQL_DATABASE"'], query.encode('utf-8')).decode('utf-8').rstrip('\r\n')


def observe(profile):
    result = {'entryUrl': profile['entryUrl'], 'host': profile['host'], 'components': {}}
    for role in ('frontend', 'backend', 'database'):
        container = inspect(profile[role])
        result['components'][role] = {
            'name': container['Name'], 'containerId': container['Id'],
            'image': container['Config']['Image'], 'imageId': container['Image'],
            'running': container['State']['Running'], 'startedAt': container['State']['StartedAt']}
    tables = sql(profile, 'SHOW TABLES;').splitlines()
    columns = sql(profile, 'SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COALESCE(COLUMN_DEFAULT,\'<NULL>\'),EXTRA,COLLATION_NAME,GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION;')
    indexes = sql(profile, 'SELECT TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME,SUB_PART,INDEX_TYPE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;')
    options = sql(profile, 'SELECT TABLE_NAME,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME;')
    triggers = sql(profile, 'SELECT TRIGGER_NAME,EVENT_MANIPULATION,EVENT_OBJECT_TABLE,ACTION_TIMING,ACTION_STATEMENT,SQL_MODE FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() ORDER BY TRIGGER_NAME;')
    routines = sql(profile, 'SELECT ROUTINE_NAME,ROUTINE_TYPE,ROUTINE_DEFINITION,SQL_MODE FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() ORDER BY ROUTINE_NAME;')
    events = sql(profile, 'SELECT EVENT_NAME,STATUS,EVENT_DEFINITION FROM information_schema.EVENTS WHERE EVENT_SCHEMA=DATABASE() ORDER BY EVENT_NAME;')
    result['databaseIdentity'] = sql(profile, 'SELECT DATABASE(),@@server_uuid,@@version,@@lower_case_table_names;')
    result['schema'] = dict(tables=tables, columns=columns, indexes=indexes, options=options, triggers=triggers, routines=routines, events=events)
    result['schemaSha256'] = hashlib.sha256(json.dumps(result['schema'], sort_keys=True).encode()).hexdigest()
    ledgers = [t for t in tables if re.search(r'release.*migration|migration.*history|databasechangelog|flyway', t, re.I)]
    result['migrationLedgers'] = {}
    for table in ledgers:
        if not re.fullmatch(r'[A-Za-z0-9_]+', table):
            raise ValueError('Invalid ledger table identifier')
        definition = sql(profile, 'DESCRIBE `' + table + '`;')
        # A ledger contains release operations, not application row data.
        rows = sql(profile, 'SELECT * FROM `' + table + '` ORDER BY 1;')
        result['migrationLedgers'][table] = dict(definition=definition, rows=rows)
    sql(profile, 'DESCRIBE system_users;')
    result['identityConflicts'] = sql(profile, "SELECT tenant_id,SHA2(canonical_name,256),duplicate_count,active_count,user_ids FROM (SELECT tenant_id,LOWER(TRIM(username)) canonical_name,COUNT(*) duplicate_count,SUM(deleted=b'0') active_count,GROUP_CONCAT(CONCAT(id,':',CAST(deleted AS UNSIGNED)) ORDER BY id) user_ids FROM system_users GROUP BY tenant_id,LOWER(TRIM(username)) HAVING COUNT(*)>1) conflicts;")
    result['adminAccounts'] = sql(profile, "SELECT id,tenant_id,CAST(deleted AS UNSIGNED),status FROM system_users WHERE username='admin' ORDER BY tenant_id,id;")
    return result


def main():
    payload = json.loads(sys.stdin.read())
    if payload.get('action') != 'observe':
        raise ValueError('Unsupported IntRuoyi remote operation')
    print(json.dumps(observe(payload['profile']), ensure_ascii=False))


if __name__ == '__main__':
    main()
