"""Explicit replacement of a registered existing application, never an empty-target retry."""
from copy import deepcopy
from pathlib import Path, PurePosixPath
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
    version = value.get('schemaVersion')
    require(version in ('RegisteredApplicationReplacement/v1', 'RegisteredApplicationReplacement/v2') and
            set(value) == {'schemaVersion', 'stateRoot', 'lockPath', 'databaseUuid', 'services'} |
            ({'storage'} if version == 'RegisteredApplicationReplacement/v2' else set()) |
            ({'backupEpoch'} if 'backupEpoch' in value else set()),
            'REPLACEMENT_CONFIGURATION_INVALID')
    require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['databaseUuid']),
            'REPLACEMENT_CONFIGURATION_INVALID')
    if version == 'RegisteredApplicationReplacement/v2':
        from recovery_replacement_storage import validate_storage
        validate_storage(value['storage'])
    require(set(value['services']) == {row['role'] for row in target['services']},
            'REPLACEMENT_SERVICES_INVALID')
    require(target['database'] not in {'mysql', 'sys', 'information_schema', 'performance_schema'} and
            re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}', target['database']), 'REPLACEMENT_DATABASE_INVALID')
    database = target['redisRebuild']['database']
    require(type(database) is int and 0 <= database < 16, 'REPLACEMENT_REDIS_DATABASE_INVALID')
    state, lock = absolute(value['stateRoot']), absolute(value['lockPath'])
    require(state.is_dir() and lock.parent.is_dir() and lock != state and not lock.is_relative_to(state),
            'REPLACEMENT_STATE_INVALID')
    if 'backupEpoch' in value:
        _validate_epoch(value, value['backupEpoch'])
    return value


def _epoch_physical_overlap(protected, writable, mounts):
    """Include nested bind mounts, whose backing may be outside the lexical tree."""
    from recovery_replacement_storage import physical_location, overlaps
    device, location = physical_location(protected, mounts)
    paths = [writable] + [row['mountPoint'] for row in mounts
        if PurePosixPath(writable) in PurePosixPath(row['mountPoint']).parents]
    return any(device == other_device and overlaps(location, other_location)
        for other_device, other_location in (physical_location(path, mounts) for path in paths))


def _epoch_mount_path(value, role, mount):
    from recovery_replacement_storage import DATA_ROLES, observe_preserved_mount
    contract = value.get('storage', {})
    if contract.get('schemaVersion') == 'RegisteredReplacementStorage/v3' and role not in DATA_ROLES:
        entries = [entry for entry in contract['preservedApplicationMounts']
                   if entry['role'] == role and entry['mount'] == mount]
        if entries:
            require(len(entries) == 1, 'BACKUP_EPOCH_RETAINED_MOUNT_CHANGED')
            observed = observe_preserved_mount(mount)
            require(observed == entries[0]['identity'], 'BACKUP_EPOCH_RETAINED_MOUNT_CHANGED')
            return absolute(observed['resolvedPath'])
    # Data, legacy and unregistered mounts never inherit the retained alias contract.
    return absolute(mount['Source'])


def _validate_epoch(value, policy):
    from recovery_backup_epoch import validate_policy
    epoch = validate_policy(policy)
    if epoch['sourceLockPath'] != value['lockPath']:
        raise ValueError('BACKUP_EPOCH_SOURCE_LOCK_MISMATCH')
    if epoch['databaseUuid'] != value['databaseUuid']:
        raise ValueError('BACKUP_EPOCH_DATABASE_MISMATCH')
    epoch_root = absolute(epoch['root'])
    state, lock = absolute(value['stateRoot']), absolute(value['lockPath'])
    if epoch_root.is_relative_to(state) or state.is_relative_to(epoch_root):
        raise ValueError('BACKUP_EPOCH_REPLACEMENT_STATE_OVERLAP')
    mounts = None
    if os.name == 'posix':
        from recovery_replacement_storage import parse_mountinfo
        mounts = parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
        if _epoch_physical_overlap(str(epoch_root), str(state), mounts):
            raise ValueError('BACKUP_EPOCH_REPLACEMENT_STATE_OVERLAP')
    for role, service in value['services'].items():
        for mount in service.get('mounts', []):
            if mount.get('RW'):
                storage = _epoch_mount_path(value, role, mount)
                if (epoch_root.is_relative_to(storage) or storage.is_relative_to(epoch_root) or
                        lock.is_relative_to(storage) or mounts is not None and
                        any(_epoch_physical_overlap(str(path), str(storage), mounts)
                            for path in (epoch_root, lock))):
                    raise ValueError('BACKUP_EPOCH_REPLACEMENT_STORAGE_OVERLAP')


def replacement_value(configuration, target_ref):
    """Bind owner metadata without changing the target pinned by old history."""
    target = configuration['targets'][target_ref]
    value = validate(target)
    policies = configuration.get('targetBackupEpochPolicies', {})
    if not (type(policies) is dict and all(type(key) is str for key in policies) and
            set(policies).issubset(configuration['targets'])):
        raise ValueError('BACKUP_EPOCH_TARGET_POLICIES_INVALID')
    if target_ref not in policies:
        return value
    policy = policies[target_ref]
    if 'backupEpoch' in value and value['backupEpoch'] != policy:
        raise ValueError('BACKUP_EPOCH_TARGET_POLICY_CONFLICT')
    _validate_epoch(value, policy)
    effective = deepcopy(value)
    effective['backupEpoch'] = deepcopy(policy)
    return effective


def available(target):
    value = validate(target)
    # Failure remains immutable. Only an explicitly audited, terminated-failure
    # recovery clearance may allow a new request; incomplete claims still block.
    from recovery_retained_retry import validate_clearance
    return all(load(p)['state'] == 'SUCCEEDED' or validate_clearance(target,p.parent) is not None
               for p in absolute(value['stateRoot']).glob('*/replacement-result.json')) and all(
               (p/'replacement-result.json').is_file() for p in absolute(value['stateRoot']).iterdir() if p.is_dir())


def verify_services(native, value):
    require(absolute('/etc/machine-id').read_text().strip() == native.config['machineId'],
            'REPLACEMENT_MACHINE_CHANGED')
    info = json.loads(native.docker(['info', '--format', '{{json .}}']))
    require(info['ID'] == native.config['dockerEngineId'], 'REPLACEMENT_DOCKER_ENGINE_CHANGED')
    rows = {}
    for role, expected in value['services'].items():
        row = native.inspect(expected['id'])
        require(row['Id'] == native.config_services[role]['id'] == expected['id'] and
                row['Image'] == native.config_services[role]['imageId'] == expected['imageId'] and
                row['Config']['Labels'] == expected['labels'] and
                sorted(row['Mounts'], key=lambda m:m['Destination']) == expected['mounts'] and
                not row['HostConfig']['Privileged'] and not row['State']['Paused'] and
                not row['State']['Restarting'], 'REPLACEMENT_TARGET_IDENTITY_CHANGED')
        rows[role] = row
    from recovery_replacement_storage import verify_storage
    writable = verify_storage(native, value, rows)
    require(native.database_uuid() == value['databaseUuid'], 'REPLACEMENT_DATABASE_CHANGED')
    mounts = [m for m in value['services']['minio']['mounts']
              if m['Destination'] == native.policy['minioDataMount']]
    require(len(mounts) == 1 and mounts[0]['RW'], 'REPLACEMENT_STORAGE_INVALID')
    return writable


def prepare(native, value, *, source_lock_fd=None):
    from recovery_data_files import apply_tree, inventory
    if hasattr(native, 'replacement_preflight'):
        native.replacement_preflight()
    verify_services(native, value)
    require(native.mysql.query('SELECT @@GLOBAL.log_bin;').strip() == '1',
            'REPLACEMENT_BINARY_LOGGING_REQUIRED')
    intent = dict(targetConfigRef=native.original['targetConfigRef'],
          database=native.config['database'], databaseUuid=value['databaseUuid'],
          serviceIds={role:item['id'] for role,item in value['services'].items()}, startedAt=utc())
    if 'backupEpoch' in value:
        intent.update(schemaVersion='ReplacementBackupEpochIntent/v1', operationId=native.original['operationId'],
            replacementReceiptPath=(absolute(value['stateRoot'])/native.original['operationId']/'replacement-result.json').as_posix())
    intent_pin = write(native.root/'replacement-intent.json', intent)
    if hasattr(native, 'replacement_write_fence'):
        native.replacement_write_fence()
    for role in reversed(native.config['application']['startOrder']):
        native.docker(['stop', native.config_services[role]['id']], mutation=True)
    native.docker(['stop', native.config_services['minio']['id']], mutation=True)
    verify_services(native, value)
    # Inspect the declared application schema before its explicit replacement.
    database = native.config['database']
    native.mysql.query('SHOW FULL TABLES FROM `'+database+'`;')
    verify_services(native, value)
    if hasattr(native, 'replacement_quiescence'):
        native.replacement_quiescence()
    if 'backupEpoch' in value:
        from recovery_backup_epoch import begin_restore
        native.backup_epoch = begin_restore(value['backupEpoch'], native.original['operationId'], source_lock_fd,
                                          intent_pin=intent_pin)
    native.mutation_dispatched = True
    native.mysql.query('DROP DATABASE `'+database+'`; CREATE DATABASE `'+database+'`;', mutation=True)
    mount = [m for m in value['services']['minio']['mounts'] if m['Destination'] == native.policy['minioDataMount']]
    require(len(mount) == 1 and mount[0]['RW'], 'REPLACEMENT_STORAGE_INVALID')
    root = absolute(mount[0]['Source'])
    before = inventory(root, native.guard, content=False)
    verify_services(native, value)
    apply_tree(root, before, {}, {}, full=False, guard=native.guard, verify_content=False)
    # Clear only the registered application Redis database. Password stays on stdin.
    database = native.config['redisRebuild']['database']
    verify_services(native, value)
    from recovery_main_target import redis_command
    redis_command(native, ['-n', str(database), 'FLUSHDB'], mutation=True)
    write(native.root/'replacement-prepared.json', dict(state='PREPARED', finishedAt=utc()))


def execute(configuration, request, root, input_pins, original_execute, native_type, selected_chain):
    """Hold the same physical-source lock as capture across reset and all restore writes."""
    import fcntl
    from recovery_minimal_plan import disjoint, request_contract
    request_contract(request)
    require(request['action'] == 'RESTORE', 'REPLACEMENT_RESTORE_REQUIRED')
    target = configuration['targets'][request['targetConfigRef']]
    value = replacement_value(configuration, request['targetConfigRef'])
    lock = os.open(value['lockPath'], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('REPLACEMENT_TARGET_BUSY') from error
        if 'backupEpoch' in value:
            from recovery_backup_epoch import read_current, reconcile_completed_restore
            epoch = read_current(value['backupEpoch'])
            if epoch['state'] == 'REPLACING':
                epoch = reconcile_completed_restore(value['backupEpoch'], lock)
            require(epoch['state'] in ('READY', 'FAILED_RETAINED'),
                    'BACKUP_EPOCH_RESTORE_IN_PROGRESS')
        require(available(target), 'PREVIOUS_REPLACEMENT_NOT_SUCCEEDED')
        from recovery_retained_retry import bind_clearances
        bind_clearances(target,request,consume=False)
        claim = absolute(value['stateRoot'])/request['operationId']
        claim.mkdir(mode=0o700)
        bind_clearances(target,request,consume=True)
        native = None
        receipt = None
        try:
            source, policy, chain = selected_chain(configuration, request)
            require(all(step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain),
                    'REPLACEMENT_PHYSICAL_ARCHIVE_REQUIRED')
            require(all(disjoint(value['stateRoot'], path) for path in source['archiveRoots']),
                    'REPLACEMENT_STATE_ARCHIVE_OVERLAP')
            preparation = root/'replacement-preparation'; preparation.mkdir(mode=0o700)
            from recovery_resource_admission import admit
            admit(configuration, request, root, 'replacement')
            native = native_type(configuration, request, source, policy, chain, target, preparation, input_pins)
            with native.timed_stage('target-replacement'):
                prepare(native, value, source_lock_fd=lock)
            effective = deepcopy(configuration)
            runtime = claim/'runtime'; runtime.mkdir(mode=0o700)
            effective['targets'][request['targetConfigRef']]['dataRoot'] = str(runtime)
            result = original_execute(effective, request, root, input_pins, reservation_configuration=configuration)
            if hasattr(native, 'replacement_finish'):
                result[0].update(native.replacement_finish())
            receipt = write(claim/'replacement-result.json', dict(state='SUCCEEDED', operationId=request['operationId'],
                           targetConfigRef=request['targetConfigRef'], databaseUuid=value['databaseUuid'], finishedAt=utc()))
            result[0]['replacementReceiptPin'] = receipt
            if 'backupEpoch' in value:
                from recovery_backup_epoch import complete_restore
                result[0]['sourceBackupEpoch'] = complete_restore(value['backupEpoch'], request['operationId'],
                    native.backup_epoch['epochId'], 'READY', receipt, lock)
            return result
        except BaseException as error:
            failure_native = getattr(error, 'native', None)
            if failure_native is None:
                failure_native = native
            if failure_native is not None:
                error.native = failure_native
            # Once the completed restore receipt exists, an epoch publication
            # failure must not rewrite evidence already pinned by its journal.
            try:
                if receipt is None:
                    failed = write(claim/'replacement-result.json', dict(state='FAILED_RETAINED', operationId=request['operationId'],
                          targetConfigRef=request['targetConfigRef'], databaseUuid=value['databaseUuid'], finishedAt=utc()))
                    if native is not None and hasattr(native, 'backup_epoch'):
                        from recovery_backup_epoch import complete_restore
                        complete_restore(value['backupEpoch'], request['operationId'], native.backup_epoch['epochId'],
                                         'FAILED_RETAINED', failed, lock)
            except BaseException as evidence_error:
                if failure_native is not None and getattr(evidence_error, 'native', None) is None:
                    evidence_error.native = failure_native
                raise
            raise
        finally:
            if native is not None and hasattr(native, 'archive_guard'):
                native.archive_guard.close()
    finally:
        os.close(lock)
