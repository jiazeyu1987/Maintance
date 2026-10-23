"""Explicit replacement of a registered existing application, never an empty-target retry."""
from copy import deepcopy
import hashlib
import json
import os
import re

from recovery_engine import absolute, load, require, utc, write


def enabled(target):
    return 'replacement' in target


def preserve_binary_logging(native, path, checksum):
    """Log replayed rows so later increments of this same database include them.

    mysqlbinlog archives deliberately disable session logging for a fresh
    target. Replacement keeps the source UUID and its existing backup chains,
    so its replay must also be visible in that source's binary log.
    Only the operation-owned expanded SQL changes; archived bytes stay pinned.
    """
    disabled = b'/*!32316 SET @OLD_SQL_LOG_BIN=@@SQL_LOG_BIN, SQL_LOG_BIN=0*/;'
    logged = disabled.replace(b'SQL_LOG_BIN=0', b'SQL_LOG_BIN=1')
    staged = path.with_name(path.name+'.binary-logged')
    original, transformed = hashlib.sha256(), hashlib.sha256()
    count = 0
    with path.open('rb') as source, staged.open('xb') as output:
        os.chmod(staged, 0o600)
        prefix = b'SET SESSION sql_log_bin=1;\n'
        output.write(prefix); transformed.update(prefix)
        for line in source:
            native.guard()
            original.update(line)
            if line.rstrip(b'\r\n') == disabled:
                line = line.replace(disabled, logged, 1)
                count += 1
            output.write(line); transformed.update(line)
        output.flush(); os.fsync(output.fileno())
    require(original.hexdigest() == checksum, 'REPLACEMENT_EXPANDED_SQL_CHANGED')
    os.replace(staged, path)
    write(native.root/(path.name+'-binary-logging.json'), dict(
        schemaVersion='ReplacementBinaryLogging/v1', sourceSha256=checksum,
        importSha256=transformed.hexdigest(), reenabledSegments=count))
    return transformed.hexdigest()


def validate(target):
    value = target['replacement']
    require(set(value) == {'schemaVersion', 'stateRoot', 'lockPath', 'databaseUuid', 'services'},
            'REPLACEMENT_CONFIGURATION_INVALID')
    require(value['schemaVersion'] == 'RegisteredApplicationReplacement/v1' and
            re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['databaseUuid']),
            'REPLACEMENT_CONFIGURATION_INVALID')
    require(set(value['services']) == {row['role'] for row in target['services']},
            'REPLACEMENT_SERVICES_INVALID')
    require(target['database'] not in {'mysql', 'sys', 'information_schema', 'performance_schema'} and
            re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}', target['database']), 'REPLACEMENT_DATABASE_INVALID')
    database = target['redisRebuild']['database']
    require(type(database) is int and 0 <= database < 16, 'REPLACEMENT_REDIS_DATABASE_INVALID')
    state, lock = absolute(value['stateRoot']), absolute(value['lockPath'])
    require(state.is_dir() and lock.parent.is_dir() and lock != state and not lock.is_relative_to(state),
            'REPLACEMENT_STATE_INVALID')
    return value


def available(target):
    value = validate(target)
    # A failed or interrupted replacement stays unavailable. No claim is
    # deleted or reinterpreted to make an existing target appear empty.
    return all(load(p)['state'] == 'SUCCEEDED'
               for p in absolute(value['stateRoot']).glob('*/replacement-result.json')) and all(
               (p/'replacement-result.json').is_file() for p in absolute(value['stateRoot']).iterdir() if p.is_dir())


def verify_services(native, value):
    require(absolute('/etc/machine-id').read_text().strip() == native.config['machineId'],
            'REPLACEMENT_MACHINE_CHANGED')
    info = json.loads(native.docker(['info', '--format', '{{json .}}']))
    require(info['ID'] == native.config['dockerEngineId'], 'REPLACEMENT_DOCKER_ENGINE_CHANGED')
    writable = {}
    for role, expected in value['services'].items():
        row = native.inspect(expected['id'])
        require(row['Id'] == native.config_services[role]['id'] == expected['id'] and
                row['Image'] == native.config_services[role]['imageId'] == expected['imageId'] and
                row['Config']['Labels'] == expected['labels'] and
                sorted(row['Mounts'], key=lambda m:m['Destination']) == expected['mounts'] and
                not row['HostConfig']['Privileged'] and not row['State']['Paused'] and
                not row['State']['Restarting'], 'REPLACEMENT_TARGET_IDENTITY_CHANGED')
        for mount in row['Mounts']:
            if not mount['RW']:
                continue
            require(role in {'mysql', 'minio', 'redis'} and mount['Type'] == 'volume' and
                    mount['Source'] not in writable, 'REPLACEMENT_STORAGE_INVALID')
            volume = json.loads(native.docker(['volume', 'inspect', mount['Name']]))[0]
            require(volume['Driver'] == 'local' and not volume['Options'] and
                    volume['Mountpoint'] == mount['Source'], 'REPLACEMENT_STORAGE_INVALID')
            writable[mount['Source']] = row['Id']
    for identity in native.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines():
        for mount in native.inspect(identity)['Mounts']:
            require(mount['Source'] not in writable or writable[mount['Source']] == identity or not mount['RW'],
                    'REPLACEMENT_VOLUME_SHARED')
    require(native.database_uuid() == value['databaseUuid'], 'REPLACEMENT_DATABASE_CHANGED')
    mounts = [m for m in value['services']['minio']['mounts']
              if m['Destination'] == native.policy['minioDataMount']]
    require(len(mounts) == 1 and mounts[0]['RW'], 'REPLACEMENT_STORAGE_INVALID')
    return writable


def prepare(native, value):
    from recovery_data_files import apply_tree, inventory
    verify_services(native, value)
    require(native.mysql.query('SELECT @@GLOBAL.log_bin;').strip() == '1',
            'REPLACEMENT_BINARY_LOGGING_REQUIRED')
    write(native.root/'replacement-intent.json', dict(targetConfigRef=native.original['targetConfigRef'],
          database=native.config['database'], databaseUuid=value['databaseUuid'],
          serviceIds={role:item['id'] for role,item in value['services'].items()}, startedAt=utc()))
    for role in reversed(native.config['application']['startOrder']):
        native.docker(['stop', native.config_services[role]['id']], mutation=True)
    native.docker(['stop', native.config_services['minio']['id']], mutation=True)
    verify_services(native, value)
    # Inspect the declared application schema before its explicit replacement.
    database = native.config['database']
    native.mysql.query('SHOW FULL TABLES FROM `'+database+'`;')
    native.mutation_dispatched = True
    native.mysql.query('DROP DATABASE `'+database+'`; CREATE DATABASE `'+database+'`;')
    mount = [m for m in value['services']['minio']['mounts'] if m['Destination'] == native.policy['minioDataMount']]
    require(len(mount) == 1 and mount[0]['RW'], 'REPLACEMENT_STORAGE_INVALID')
    root = absolute(mount[0]['Source'])
    before = inventory(root, native.guard, content=False)
    apply_tree(root, before, {}, {}, full=False, guard=native.guard, verify_content=False)
    # Clear only the registered application Redis database. Password stays on stdin.
    database = native.config['redisRebuild']['database']
    script = 'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
    native.docker(['exec', '-i', native.config_services['redis']['id'], 'sh', '-ec', script,
                  'recovery-redis', native.config['redisClientPath'], '-n', str(database), 'FLUSHDB'],
                  input_bytes=(native.secret('redis','REDIS_PASSWORD')+'\n').encode(), mutation=True)
    write(native.root/'replacement-prepared.json', dict(state='PREPARED', finishedAt=utc()))


def execute(configuration, request, root, input_pins, original_execute, native_type, selected_chain):
    """Hold the same physical-source lock as capture across reset and all restore writes."""
    import fcntl
    from recovery_minimal_plan import disjoint, request_contract
    request_contract(request)
    require(request['action'] == 'RESTORE', 'REPLACEMENT_RESTORE_REQUIRED')
    target = configuration['targets'][request['targetConfigRef']]
    value = validate(target)
    lock = os.open(value['lockPath'], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('REPLACEMENT_TARGET_BUSY') from error
        require(available(target), 'PREVIOUS_REPLACEMENT_NOT_SUCCEEDED')
        claim = absolute(value['stateRoot'])/request['operationId']
        claim.mkdir(mode=0o700)
        native = None
        try:
            source, policy, chain = selected_chain(configuration, request)
            require(all(step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain),
                    'REPLACEMENT_PHYSICAL_ARCHIVE_REQUIRED')
            require(all(disjoint(value['stateRoot'], path) for path in source['archiveRoots']),
                    'REPLACEMENT_STATE_ARCHIVE_OVERLAP')
            preparation = root/'replacement-preparation'; preparation.mkdir(mode=0o700)
            native = native_type(configuration, request, source, policy, chain, target, preparation, input_pins)
            with native.timed_stage('target-replacement'):
                prepare(native, value)
            effective = deepcopy(configuration)
            runtime = claim/'runtime'; runtime.mkdir(mode=0o700)
            effective['targets'][request['targetConfigRef']]['dataRoot'] = str(runtime)
            result = original_execute(effective, request, root, input_pins)
            receipt = write(claim/'replacement-result.json', dict(state='SUCCEEDED', operationId=request['operationId'],
                           targetConfigRef=request['targetConfigRef'], finishedAt=utc()))
            result[0]['replacementReceiptPin'] = receipt
            return result
        except BaseException as error:
            write(claim/'replacement-result.json', dict(state='FAILED_RETAINED', operationId=request['operationId'],
                  targetConfigRef=request['targetConfigRef'], finishedAt=utc()))
            if native is not None and getattr(error, 'native', None) is None:
                error.native = native
            raise
        finally:
            if native is not None and hasattr(native, 'archive_guard'):
                native.archive_guard.close()
    finally:
        os.close(lock)
