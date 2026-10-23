"""Single-operator Linux restore using the existing SQL and object engines."""
from __future__ import annotations

import importlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time

from recovery_data import NativeData
from recovery_engine import (Budget, absolute, canonical, check_pin, digest, pin,
    pinned_json, RecoveryError, require, signature, utc, write)
from recovery_minimal_plan import disjoint, selected_chain, target_configuration
from staging_cleanup import cleanup, restore_paths
from recovery_step_timing import step as step_timing


def modules_from(root):
    sys.path.insert(0, str(absolute(root)))
    names = ('formal_sql_restore', 'formal_data_evidence', 'formal_s3_export',
             'formal_physical_restore_readback')
    return {name: importlib.import_module(name) for name in names}


def json_value(reference, path):
    value = pinned_json(reference)
    require(type(path) is list, 'VERSION_VALUE_PATH_INVALID')
    for key in path:
        require(type(key) in (str, int), 'VERSION_VALUE_PATH_INVALID')
        value = value[key]
    return value


def lightweight_physical_inputs(chain):
    prior = {}
    for _, _, material, reference in chain:
        descriptor = material['objects']
        capture = pinned_json(descriptor['capturePointPin'])
        expected = capture['fileInventory']
        delta = capture['fileDelta']
        yield reference, prior, expected, descriptor['filePayloadPins'], delta['changedPaths'], delta['deletedPaths']
        prior = expected


class MinimalData(NativeData):
    """Reuse native data methods; the new main path has no legacy trust calls."""

    def import_sql(self, path, checksum):
        from recovery_replace import enabled, preserve_binary_logging
        if enabled(self.config):
            checksum = preserve_binary_logging(self, path, checksum)
        return super().import_sql(path, checksum)

    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins):
        require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        self.original = request
        self.request = dict(request, requestId=request['operationId'])
        self.source, self.chain, self.config = source, chain, target
        self.policy = dict(policy, **{key: configuration[key] for key in
            ('environmentMysqlClientPath', 'maxExpandedBytes')})
        self.policy.update(target['dataPolicy'])
        # Read-only query recipes are local configuration, not approval records.
        self.plan = {'recoveryPoint': chain[-1][2]['recoveryPoint']}
        self.material = chain[-1][2]
        self.budget = Budget(configuration['deadlineMilliseconds'])
        self.root = root
        self.input_pins = input_pins
        self.original_pins = []
        self.last_exit = None
        self.mutation_dispatched = False
        self.modules = modules_from(configuration['formalModuleDirectory'])
        self.config_services = {row['role']: row for row in target['services']}
        self.storage_running = chain[0][2]['objects']['method'] != 'PHYSICAL_FILES'
        self.running_applications = set()
        self.snapshots = {}
        self.target = {'targetIdentityPin': write(root/'target-configuration.json', target)}
        self.db_container = self.config_services['mysql']['id']
        self.db_uuid = self.database_uuid()
        sql = self.modules['formal_sql_restore']; native = self

        class BoundMySql(sql.IsolatedTargetMySql):
            def _command(self, program, arguments):
                command = super()._command(program, arguments)
                return [native.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *command[1:]]

            def query(self, statement):
                return native.docker(['exec', native.db_container, native.policy['environmentMysqlClientPath'],
                    '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost',
                    '--batch', '--skip-column-names',
                    '-e', statement]).decode('utf-8')

        self.mysql = BoundMySql(self.db_container, self.secret('mysql', 'MYSQL_ROOT_PASSWORD'), timeout=self.seconds())
        self.db_target = dict(database=target['database'], databaseUuid=self.db_uuid)

    def secret(self, role, environment):
        ref = self.config['secrets'][role][environment]
        raw = check_pin(ref)
        value = raw.decode('utf-8')
        require(value and not any(char in value for char in '\r\n\0'), 'SECRET_FORMAT_INVALID')
        return value

    def service(self, role):
        item = self.config_services[role]
        return dict(id=item['id'], imageId=item['imageId'], mounts=self.snapshots[role]['Mounts'])

    def guard(self):
        self.budget.remaining()

    def inspect(self, identity):
        rows = json.loads(self.docker(['inspect', identity]))
        require(type(rows) is list and len(rows) == 1, 'TARGET_INSPECT_INVALID')
        return rows[0]

    def docker(self, args, **kwargs):
        # Lightweight invokes the configured executable without integrity scans.
        return self.command([self.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *args], **kwargs)

    def database_uuid(self):
        raw = self.docker(['exec', self.db_container, self.policy['environmentMysqlClientPath'],
            '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost',
            '--batch', '--skip-column-names', '-e', 'SELECT @@server_uuid;'])
        value = raw.decode('ascii').strip()
        require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value), 'TARGET_DATABASE_UUID_INVALID')
        return value

    def bound(self, *, importing=False, minio_stopped=False):
        self.guard()

    def stop_application(self):
        # Keep writers off throughout database and object replay, without health probes.
        for role in reversed(self.config['application']['startOrder']):
            self.docker(['stop', self.config_services[role]['id']], mutation=True)


    def check_bucket_permissions(self):
        return write(self.root/'bucket-permissions.json', dict(verificationState='NOT_PERFORMED'))

    def restore_database_settings(self):
        from recovery_data import database_settings
        reference = self.material['database']['expectedDataPin']
        value = pinned_json(reference)
        name = self.config['database']
        if value.get('schemaVersion') == 'LightweightDatabaseSettings/v1':
            definition = value['definition']
        else:
            # Read the attributes in older archived observations without comparing data.
            definition = value['schema']['definitions']['DATABASE'][name]
        wanted = database_settings(definition, name)
        statement = ('ALTER DATABASE `'+name+'` DEFAULT CHARACTER SET '+wanted['characterSet']+
            (' COLLATE '+wanted['collation'] if wanted['collation'] is not None else '')+
            " DEFAULT ENCRYPTION='"+wanted['encryption']+"';")
        self.mysql.query(statement)
        return write(self.root/'database-settings.json', dict(database=name, applied=wanted,
            verificationState='NOT_PERFORMED'))

    def full_database(self):
        settings = self.restore_database_settings()
        self.import_archived_sql(self.material['database']['sqlPin'], 'full')
        return dict(self.database_readback(), databaseSettingsPin=settings)

    def import_archived_sql(self, reference, name):
        from recovery_data import stage_private_sql
        expanded = self.root/(name+'.sql')
        with self.timed_stage('sql-stage'):
            staged = stage_private_sql(reference, self.root/(name+'.private.gz'), self.seconds())
        with self.timed_stage('sql-expand'):
            checksum, _ = self.modules['formal_sql_restore'].expand_checked(staged['path'], expanded,
                reference['sha256'], self.policy['maxExpandedBytes'], self.seconds())
        with self.timed_stage('sql-import'):
            self.import_sql(expanded, checksum)

    def incremental_database(self):
        database = self.material['database']
        if database['method'] == 'BINLOG_SQL':
            self.import_archived_sql(database['sqlPin'], 'incremental')
        elif database['method'] == 'MYSQL_BINLOG':
            for index, segment in enumerate(database['segments']):
                raw = self.command([self.policy['mysqlbinlogPin']['path'], '--no-defaults', '--disable-log-bin',
                    '--start-position='+str(segment['startPosition']['position']),
                    '--stop-position='+str(segment['endPosition']['position']), segment['payloadPin']['path']])
                expanded = self.root/('binlog-%03d.sql' % index)
                with expanded.open('xb') as output:
                    output.write(raw)
                self.import_sql(expanded, __import__('hashlib').sha256(raw).hexdigest())
        else:
            raise RecoveryError('UNSUPPORTED_INCREMENTAL_METHOD')
        return self.database_readback()

    def database_readback(self):
        # No row, schema or affected-table reads.
        return dict(recoveryPoint=self.material['recoveryPoint'], databaseUuid=self.db_uuid,
            endPosition=self.material['database']['endPosition'], verificationState='NOT_PERFORMED',
            fullSchemaDataEquivalenceVerified=False, incrementalReplayAndAffectedDataVerified=False,
            applicationVerified=False)

    def consistency(self):
        # No attachment-reference or business-invariant queries.
        return dict(recoveryPoint=self.material['recoveryPoint'], verificationState='NOT_PERFORMED',
            databaseReferencesVerified=False, objectReferencesVerified=False, businessInvariantsVerified=False)

    def object_client(self):
        service = self.config_services['minio']
        endpoint = 'http://'+service['ip']+':9000'
        return self.modules['formal_s3_export'].IsolatedRestoreS3(endpoint,
            self.secret('minio', 'MINIO_ROOT_USER'), self.secret('minio', 'MINIO_ROOT_PASSWORD'),
            approved_endpoint=endpoint, timeout=min(30, self.seconds()), verify_payload=False)

    def restore_object_rows(self, rows, *, full):
        client = self.object_client()
        if full:
            from recovery_data_objects import create_buckets_unchecked
            create_buckets_unchecked(client, self.config['buckets'], self.policy['bucketSettings'])
        mapping = []
        if not full:
            previous = pinned_json(self.request['previousObjectResultPin'])
            mapping = [json.loads(line) for line in check_pin(previous['versionMappingPin']).splitlines()]
        for row in rows:
            self.guard()
            bucket = self.policy['bucketMapping'][row['bucket']]
            self.mutation_dispatched = True
            if row['kind'] in ('PUT', 'version'):
                content = row['contentPin']
                version = client.put_version(bucket, row['key'], content['path'], row['headers'],
                    content['bytes'], content['sha256'])
            else:
                version = client.delete_marker(bucket, row['key'])
            for prior in mapping:
                if prior['targetBucket'] == bucket and prior['key'] == row['key']:
                    prior['isLatest'] = False
            mapping.append(dict(sourceBucket=row['bucket'], targetBucket=bucket, key=row['key'],
                sourceVersionId=row.get('sourceVersionId', row.get('versionId')), targetVersionId=version,
                kind='version' if row['kind'] in ('PUT', 'version') else 'delete-marker', isLatest=True))
        path = self.root/'version-mapping.jsonl'
        with path.open('xb') as output:
            for row in mapping:
                output.write(canonical(row)+b'\n')
        return dict(recoveryPoint=self.material['recoveryPoint'], versionMappingPin=pin(path),
            payloadContentVerified=False, verificationState='NOT_PERFORMED')

    def full_objects(self):
        objects = self.material['objects']
        root = Path(objects['inventoryPin']['path']).parent
        rows = [json.loads(line) for line in check_pin(objects['inventoryPin']).splitlines()]
        # Export inventories list newest first; replay oldest first per key.
        groups = {}
        for row in rows:
            groups.setdefault((row['bucket'], row['key']), []).append(row)
        replay = []
        for group in groups.values():
            for row in reversed(group):
                item = dict(row)
                if row['kind'] == 'version':
                    item['contentPin'] = dict(path=str(root/row['repositoryPath']), bytes=row['size'], sha256=row['sha256'])
                replay.append(item)
        return self.restore_object_rows(replay, full=True)

    def incremental_objects(self):
        return self.restore_object_rows(pinned_json(self.material['objects']['deltaPin'])['changes'], full=False)

    def physical_object_chain(self):
        from recovery_data_files import apply_tree
        from formal_capture_semantics import export_listing
        row = self.inspect(self.config_services['minio']['id'])
        mount = next(item for item in row['Mounts'] if item['Destination'] == self.policy['minioDataMount'])
        root = absolute(mount['Source'])
        # Offline copying is a required mutation step, not an inspection.
        self.docker(['stop', row['Id']], mutation=True)
        steps = []
        for index, (material_ref, prior, expected, payloads, changed, deleted) in enumerate(
                lightweight_physical_inputs(self.chain)):
            self.bound()
            self.mutation_dispatched = True
            intent = write(self.root/('physical-step-%03d-intent.json' % index),
                dict(materialPin=material_ref, changedPaths=sorted(changed), deletedPaths=sorted(deleted)))
            self.original_pins.append(intent)
            value = apply_tree(root, prior, expected, payloads, full=index == 0, guard=self.guard,
                               ownership=self.policy['minioFileOwnership'], verify_content=False)
            self.bound()
            steps.append(write(self.root/('physical-step-%03d-readback.json' % index), value))
        # ponytail: lightweight restore has no final file inventory/readback pass.
        # The isolated network/firewall is checked before the only storage start.
        self.bound()
        self.docker(['start', row['Id']], mutation=True)
        self.storage_running = True
        self.bound()
        comparison = dict(state='PHYSICAL_RESTORED_WITHOUT_FILE_VERIFICATION', payloadContentVerified=False,
                          exactVersionIdentityVerified=False, productionEvidence=False)
        self.bound()
        mapping = self.root/'physical-version-mapping.jsonl'
        with mapping.open('xb') as output:
            os.chmod(mapping, 0o600)
            for line in check_pin(self.material['objects']['inventoryPin']).splitlines():
                entry = json.loads(line)
                output.write(canonical(dict(sourceBucket=entry['bucket'], targetBucket=entry['bucket'], key=entry['key'],
                    sourceVersionId=entry['versionId'], targetVersionId=entry['versionId'], kind=entry['kind'],
                    isLatest=entry['isLatest']))+b'\n')
            output.flush(); os.fsync(output.fileno())
        return dict(recoveryPoint=self.plan['recoveryPoint'], versionMappingPin=pin(mapping),
            physicalStepEvidencePins=steps, comparisonPin=write(self.root/'physical-comparison.json', comparison),
            permissionEvidencePin=self.check_bucket_permissions(), originalVersionIdsPreserved=True,
            payloadContentVerified=False)



    def start_application(self):
        observations = {}
        for role in self.config['application']['startOrder']:
            self.docker(['start', self.config_services[role]['id']], mutation=True)
            self.running_applications.add(role)
            observations[role] = dict(containerId=self.config_services[role]['id'], state='START_COMMAND_COMPLETED')
        return dict(services=observations, state='START_COMMANDS_COMPLETED',
            healthVerification='NOT_PERFORMED', businessAcceptance='NOT_PERFORMED', isolation='NOT_CHECKED')


def execute(configuration, request, root, input_pins):
    from recovery_replace import enabled, execute as replace
    if enabled(configuration['targets'][request['targetConfigRef']]):
        return replace(configuration, request, root, input_pins, execute_empty, MinimalData, selected_chain)
    return execute_empty(configuration, request, root, input_pins)


def execute_empty(configuration, request, root, input_pins):
    with step_timing(root, 'restore-admission'):
        source, policy, chain = selected_chain(configuration, request)
        target = target_configuration(configuration, request, source)
        require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        # A permanent local reservation prevents a second operation overwriting a
        # target even when the first process has ended or its result is unknown.
        reservation = absolute(target['dataRoot'])/'.recovery-operation.json'
        try:
            with reservation.open('xb') as stream:
                os.chmod(reservation, 0o600)
                stream.write(canonical(dict(operationId=request['operationId'], startedAt=utc())))
                stream.flush(); os.fsync(stream.fileno())
        except FileExistsError as error:
            raise RecoveryError('TARGET_ALREADY_RESERVED') from error
        native = MinimalData(configuration, request, source, policy, chain, target, root, input_pins)
    try:
        with native.timed_stage('target-quiesce'):
            native.stop_application()
        db_pins, object_pins = [], []
        for index, step in enumerate(chain):
            native.material = step[2]
            native.root = root/('database-%03d' % index); native.root.mkdir(mode=0o700)
            native.request.update(action='DATABASE_FULL' if index == 0 else 'DATABASE_INCREMENTAL',
                                  previousDatabaseResultPin=db_pins[-1] if db_pins else None)
            with native.timed_stage('database-restore'):
                result = native.full_database() if index == 0 else native.incremental_database()
                db_pins.append(write(native.root/'result.json', result))
        native.material = chain[-1][2]
        if chain[0][2]['objects']['method'] == 'PHYSICAL_FILES':
            native.root = root/'objects'; native.root.mkdir(mode=0o700)
            native.request['action'] = 'OBJECT_CHAIN_PHYSICAL'
            with native.timed_stage('object-restore'):
                object_pins.append(write(native.root/'result.json', native.physical_object_chain()))
        else:
            for index, step in enumerate(chain):
                native.material = step[2]
                native.root = root/('objects-%03d' % index); native.root.mkdir(mode=0o700)
                native.request.update(action='OBJECT_FULL' if index == 0 else 'OBJECT_INCREMENTAL',
                    previousObjectResultPin=object_pins[-1] if object_pins else None,
                    parentRecoveryPoint=chain[index-1][2]['recoveryPoint'] if index else None)
                with native.timed_stage('object-restore'):
                    result = native.full_objects() if index == 0 else native.incremental_objects()
                    object_pins.append(write(native.root/'result.json', result))
        native.material = chain[-1][2]
        native.root = root/'final'; native.root.mkdir(mode=0o700)
        native.request.update(action='CONSISTENCY', databaseResultPin=db_pins[-1], objectResultPin=object_pins[-1])
        consistent = write(native.root/'consistency.json', native.consistency())
        from recovery_minimal_derived import rebuild
        with native.timed_stage('redis-rebuild'):
            derived = write(native.root/'derived.json', rebuild(native))
        native.request['action'] = 'START_APPLICATION'
        with native.timed_stage('application-start'):
            application = write(native.root/'application-start.json', native.start_application())
        with native.timed_stage('restore-cleanup'):
            cleanup_pin = pin(cleanup(root, restore_paths(root), request['operationId'],
                                      guard=native.guard, verify_files=False))
        return dict(recoveryPoint=chain[-1][2]['recoveryPoint'], targetConfigRef=request['targetConfigRef'],
            orderedChainPins=[step[0] for step in chain], databaseResultPins=db_pins, objectResultPins=object_pins,
            consistencyPin=consistent, derivedPin=derived, applicationStartPin=application,
            businessAcceptance='NOT_PERFORMED', stagingCleanupPin=cleanup_pin), native
    except Exception as error:
        error.native = native
        raise
