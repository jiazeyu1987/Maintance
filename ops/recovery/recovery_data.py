"""Native full SQL/binlog and complete object-history recovery, with no replay.

This worker consumes the provisioned W04 trust and the W05 prepared target.
Formal modules are imported only from one explicit fully pinned directory.
Credentials are read into memory and never serialized in invocation evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from recovery_engine import (Budget, RecoveryError, absolute, authorities, canonical, check_pin,
    digest, load, pin, pinned_json, require, utc, validate_record, write, persist_evidence, repository_guard)
from recovery_engine_read_guard import inherit_read_guard
from recovery_plan import (immutable_inputs, prepared_target, resolve_chain, trusted_configuration)


def stage_private_sql(reference, destination, seconds):
    """Read the archive once into an exclusive private SQL input, retaining its pin."""
    source = absolute(reference['path'])
    destination = absolute(str(destination))
    deadline = time.monotonic() + seconds
    digest = hashlib.sha256()
    total = 0
    with source.open('rb') as incoming:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as outgoing:
            while True:
                require(time.monotonic() < deadline, 'SQL_ARCHIVE_STAGE_TIMEOUT')
                chunk = incoming.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                outgoing.write(chunk)
                digest.update(chunk)
            outgoing.flush()
            os.fsync(outgoing.fileno())
    return {'path': str(destination), 'bytes': total, 'sha256': digest.hexdigest()}


def load_formal(policy):
    pins = policy['formalModulePins']
    require(pins, 'FORMAL_MODULE_PINS_REQUIRED')
    roots = {absolute(item['path']).parent for item in pins}
    require(len(roots) == 1, 'FORMAL_MODULE_ROOT_AMBIGUOUS')
    root = roots.pop()
    require({absolute(item['path']) for item in pins} == set(root.glob('*.py')),
            'FORMAL_MODULE_DEPENDENCIES_NOT_FULLY_PINNED')
    for item in pins:
        check_pin(item, content=False)
    names = ('formal_sql_restore', 'formal_restore_producer', 'formal_physical_restore_producer',
             'formal_physical_restore_readback', 'formal_data_evidence', 'formal_s3_export')
    require(not any(name in sys.modules for name in names), 'FORMAL_MODULE_ALREADY_IMPORTED')
    sys.path.insert(0, str(root))
    modules = {name: importlib.import_module(name) for name in names}
    for name, module in tuple(sys.modules.items()):
        if name.startswith('formal_') and getattr(module, '__file__', None):
            require(Path(module.__file__).resolve().parent == root, 'FORMAL_MODULE_WRONG_ORIGIN')
    for item in pins:
        check_pin(item, content=False)
    return modules


def position(value):
    require(type(value) is dict and set(value) == {'file', 'position'} and
            type(value['file']) is str and re.fullmatch(r'[A-Za-z0-9_-]+\.[0-9]{6,}', value['file']) and
            type(value['position']) is int and value['position'] >= 4, 'BINLOG_POSITION_INVALID')
    return value


def database_settings(definition, database):
    """Read only the database attributes represented by MySQL 8 SHOW CREATE.

    Reject additional clauses rather than silently dropping archived settings.
    Identifiers and attribute values are restricted before constructing ALTER.
    """
    require(type(database) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,63}', database),
            'ARCHIVED_DATABASE_NAME_INVALID')
    require(type(definition) is list and len(definition) == 2 and
            definition[0] == database and type(definition[1]) is str,
            'ARCHIVED_DATABASE_DEFINITION_INVALID')
    match = re.fullmatch(re.escape('CREATE DATABASE `' + database + '`') +
        r" /\*!\d{5} DEFAULT CHARACTER SET (?P<characterSet>[a-z0-9_]+)"
        r"(?: COLLATE (?P<collation>[a-z0-9_]+))? \*/"
        r" /\*!\d{5} DEFAULT ENCRYPTION='(?P<encryption>[YN])' \*/", definition[1])
    require(match is not None, 'ARCHIVED_DATABASE_SETTINGS_UNSUPPORTED')
    return match.groupdict()


def ordered_segments(material):
    database = material['database']; start = position(database['startPosition']); segments = database['segments']
    require(segments, 'BINLOG_SEGMENTS_REQUIRED')
    previous = start
    for segment in segments:
        require(set(segment) == {'payloadPin', 'startPosition', 'endPosition'}, 'BINLOG_SEGMENT_INVALID')
        left = position(segment['startPosition']); right = position(segment['endPosition'])
        same = left == previous
        rotate = (left['position'] == 4 and left['file'].rsplit('.', 1)[0] == previous['file'].rsplit('.', 1)[0]
                  and int(left['file'].rsplit('.', 1)[1]) == int(previous['file'].rsplit('.', 1)[1]) + 1)
        require((same or rotate) and left['file'] == right['file'] and right['position'] > left['position'],
                'BINLOG_SEGMENT_GAP_OR_REVERSED')
        check_pin(segment['payloadPin'], content=False)
        require(segment['payloadPin'] in material['payloadPins'], 'BINLOG_PAYLOAD_NOT_ARCHIVED')
        previous = right
    require(previous == position(database['endPosition']), 'BINLOG_STOP_POINT_MISMATCH')
    return segments


class NativeData:
    def __init__(self, request, original, trust, policy, config, target, plan, material, budget, root):
        require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        self.request, self.original, self.trust, self.policy = request, original, trust, policy
        self.config, self.target, self.plan, self.material = config, target, plan, material
        self.budget, self.root = budget, root
        from recovery_engine import signature
        self.payload_signatures = {}
        for item in material['payloadPins']:
            check_pin(item, content=False)
            self.payload_signatures[item['path']] = signature(absolute(item['path']).stat())
        self.modules = load_formal(policy)
        self.original_pins = []; self.last_exit = None; self.mutation_dispatched = False
        proof = pinned_json(target['resourcesProofPin'])
        require(proof['operationId'] == original['operationId'] and proof['targetIdentityPin'] == target['targetIdentityPin'],
                'PREPARED_RESOURCE_BINDING_INVALID')
        self.services = {item['name'].lstrip('/'): item for item in proof['services']}
        self.config_services = {item['role']: item for item in config['services']}
        self.db_container = self.service('mysql')['id']
        self.db_uuid = self.database_uuid()
        source = pinned_json(pinned_json(material['sourceScopePin'])['sourceIdentityPin'])
        require(self.db_uuid != source['databaseUuid'], 'SOURCE_DATABASE_TARGET_REJECTED')
        credentials = [pinned_json(ref) for ref in config['secretRefs']]
        self.secrets = {(item['service'], item['environment']): item for item in credentials}
        mysql_password = self.secret('mysql', 'MYSQL_ROOT_PASSWORD')
        sql = self.modules['formal_sql_restore']
        native = self

        class BoundMySql(sql.IsolatedTargetMySql):
            def _command(self, program, arguments):
                # Use the explicitly pinned local daemon, never ambient context.
                command = super()._command(program, arguments)
                return [native.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *command[1:]]

            def query(self, statement):
                return native.docker(['exec', native.db_container, native.policy['environmentMysqlClientPath'],
                    '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--batch', '--skip-column-names',
                    '-e', statement]).decode('utf-8')

        self.mysql = BoundMySql(self.db_container, mysql_password, timeout=self.seconds())
        self.db_target = dict(database=config['database'], databaseUuid=self.db_uuid)

    @contextmanager
    def timed_stage(self, name):
        started = time.monotonic()
        write(self.root/('timing-'+name+'-start.json'), dict(stage=name, startedAt=utc()))
        complete = False
        try:
            yield
            complete = True
        finally:
            write(self.root/('timing-'+name+'-end.json'), dict(stage=name, finishedAt=utc(),
                elapsedSeconds=round(time.monotonic()-started, 3), completed=complete))

    def import_sql(self, path, checksum):
        """Retain the original importer exit while reusing formal streaming guards."""
        sql = self.modules['formal_sql_restore']
        import types
        children = []
        real_subprocess = sql.subprocess
        def tracked_popen(argv, **kwargs):
            intent_path = self.root/('importer-%03d.json' % len(self.original_pins))
            value = dict(schemaVersion='RecoverySqlImporter/v1', argvSha256=digest(argv),
                         sqlPin=pin(path), startedAt=utc(), actualExitCode=None, state='TERMINAL_UNKNOWN')
            write(intent_path, value)
            active = repository_guard()
            if active is not None:
                kwargs.update(active.child_options(kwargs.get('env', dict(os.environ)), kwargs.get('pass_fds', ())))
            process = subprocess.Popen(argv, **kwargs)
            children.append((process, intent_path, value))
            return process
        sql.subprocess = types.SimpleNamespace(Popen=tracked_popen, TimeoutExpired=subprocess.TimeoutExpired,
                                               PIPE=real_subprocess.PIPE, DEVNULL=real_subprocess.DEVNULL)
        self.mutation_dispatched = True
        confirmed_failure = False
        try:
            self.bound(importing=True)
            sql.stream_import(self.mysql, path, checksum, self.seconds(), database=self.config['database'],
                              guard=self.guard)
            self.bound(importing=True)
        except Exception as error:
            confirmed_failure = (getattr(error, 'code', None) == 'FORMAL_SQL_IMPORT_FAILED' and
                getattr(error, 'unknown', None) is False and children and
                all(process.poll() is not None for process, _, _ in children))
            if children:
                error.unknown = not confirmed_failure
            raise
        finally:
            sql.subprocess = real_subprocess
            for process, intent_path, value in children:
                self.last_exit = process.poll()
                value.update(actualExitCode=self.last_exit, finishedAt=utc(),
                             state='SUCCEEDED' if self.last_exit == 0 else
                                   'FAILED_RETAINED' if confirmed_failure else 'TERMINAL_UNKNOWN')
                persist_evidence(intent_path, value, self.original_pins, unknown=self.last_exit != 0,
                                 exit_code=self.last_exit)

    def seconds(self):
        return max(1, min(7200, math.floor(self.budget.remaining())))

    def service(self, role):
        name = '/' + self.config_services[role]['name']
        require(name.lstrip('/') in self.services, 'PREPARED_DEPENDENCY_MISSING')
        item = self.services[name.lstrip('/')]
        require(item['labels'].get('intruoyi.recovery.target') == self.config['targetId'] and
                item['labels'].get('intruoyi.recovery.operation') == self.original['operationId'],
                'PREPARED_SERVICE_LABEL_INVALID')
        return item

    def secret(self, role, environment):
        item = self.secrets[(role, environment)]
        require(item['custody'] == 'INDEPENDENT' and item['provider'] == 'FILE', 'SECRET_CUSTODY_INVALID')
        raw = check_pin(item['filePin'])
        require(os.stat(item['filePin']['path']).st_mode & 0o077 == 0, 'SECRET_NOT_PRIVATE')
        value = raw.decode('utf-8')
        require(value and not any(char in value for char in '\r\n\0'), 'SECRET_FORMAT_INVALID')
        return value

    def guard(self):
        active = repository_guard()
        require(active is not None, 'SUPERVISOR_READ_GUARD_REQUIRED')
        active.check()
        self.budget.remaining()
        current_trust, current_policy, current_config = trusted_configuration(self.original)
        require(current_trust == self.trust and current_policy == self.policy and current_config == self.config,
                'EXECUTION_INPUT_DRIFT')
        check_pin(self.request['originalRequestPin'])
        from recovery_engine_state import inherited_target_lock
        inherited_target_lock(self.policy, self.target['targetIdentityPin'])
        authorities(self.original, self.target['targetIdentityPin'], ['RESTORE_EXECUTE'], self.trust)
        for ref in self.policy['formalModulePins']:
            check_pin(ref, content=False)
        check_pin(self.request['materialPin'])
        for ref in self.material['payloadPins']:
            # Hash at admission and each readback. Continuous inode/size/time
            # checks avoid re-reading an entire archive on every streamed chunk.
            from recovery_engine import signature
            require(signature(absolute(ref['path']).stat()) == self.payload_signatures[ref['path']], 'ARCHIVED_PAYLOAD_CHANGED')

    def command(self, argv, *, input_bytes=None, mutation=False):
        self.guard(); self.mutation_dispatched |= mutation
        sequence = len(self.original_pins)
        intent = dict(schemaVersion='RecoveryDataInvocation/v1', operationId=self.original['operationId'],
                      action=self.request['action'], argvSha256=digest(argv), mutation=mutation,
                      startedAt=utc(), finishedAt=None, actualExitCode=None, state='TERMINAL_UNKNOWN')
        path = self.root / ('native-%03d.json' % sequence)
        write(path, intent)
        process = None; raw = errors = b''
        try:
            options = dict(env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'})
            active = repository_guard()
            if active is not None: options.update(active.child_options(options['env']))
            process = subprocess.Popen(argv, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                **options)
            try:
                raw, errors = process.communicate(input_bytes, timeout=self.budget.remaining())
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
                try:
                    raw, errors = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    raise RecoveryError('NATIVE_EXECUTOR_TERMINAL_UNKNOWN', unknown=True) from None
                raise RecoveryError('NATIVE_EXECUTOR_TIMEOUT', unknown=mutation, exit_code=process.returncode) from None
            self.last_exit = process.returncode
            require(len(raw) <= 64*1024*1024 and len(errors) <= 1024*1024, 'NATIVE_OUTPUT_LIMIT')
            require(process.returncode == 0, 'NATIVE_EXECUTOR_FAILED')
            require(not errors, 'NATIVE_EXECUTOR_STDERR')
            intent['state'] = 'SUCCEEDED'
            self.guard()
            return raw
        except Exception as error:
            if process is not None and process.poll() is None: error.unknown = True
            if mutation and process is not None:
                error.unknown = True
            raise
        finally:
            intent.update(finishedAt=utc(), actualExitCode=None if process is None else process.poll(),
                          stdoutBytes=len(raw), stdoutSha256=hashlib.sha256(raw).hexdigest(),
                          stderrBytes=len(errors), stderrSha256=hashlib.sha256(errors).hexdigest())
            persist_evidence(path, intent, self.original_pins,
                unknown=process is not None and (mutation or process.poll() is None), exit_code=intent['actualExitCode'])

    def docker(self, args, **kwargs):
        check_pin(self.config['dockerPin'], content=False)
        return self.command([self.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *args], **kwargs)

    def database_uuid(self):
        client = self.policy['environmentMysqlClientPath']
        raw = self.docker(['exec', self.db_container, client, '--defaults-extra-file=/run/recovery/mysql-client.cnf',
                          '--batch', '--skip-column-names', '-e', 'SELECT @@server_uuid;'])
        value = raw.decode('ascii').strip()
        require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value), 'TARGET_DATABASE_UUID_INVALID')
        return value

    def bound(self, *, importing=False, minio_stopped=False):
        self.guard()
        identity = pinned_json(self.target['targetIdentityPin'])
        require(absolute('/etc/machine-id').read_text().strip() == identity['machineId'], 'TARGET_MACHINE_CHANGED')
        info = json.loads(self.docker(['info', '--format', '{{json .}}']))
        require(info['ID'] == identity['dockerEngineId'], 'TARGET_DOCKER_ENGINE_CHANGED')
        # Complete current labels, image, mounts and network binding is re-read.
        for role in ('mysql', 'minio', 'redis'):
            expected = self.service(role)
            rows = json.loads(self.docker(['inspect', expected['id']]))
            require(len(rows) == 1, 'TARGET_INSPECT_INVALID')
            row = rows[0]
            proof_digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                separators=(',', ':'), allow_nan=False).encode('ascii')).hexdigest()
            require(row['Id'] == expected['id'] and row['Image'] == expected['imageId'] and
                    row['Config']['Labels'] == expected['labels'] and row['Mounts'] == expected['mounts'] and
                    proof_digest(row['Config']['Env']) == expected['envSha256'] and
                    proof_digest([row['Path'], row['Args']]) == expected['commandSha256'] and
                    proof_digest(row['HostConfig']) == expected['hostConfigSha256'] and
                    row['RestartCount'] == expected['restartCount'] and
                    row['HostConfig']['Privileged'] is False and row['State']['Running'] is (not (role == 'minio' and minio_stopped)) and
                    row['State']['Paused'] is False and row['State']['Restarting'] is False and
                    set(row['NetworkSettings']['Networks']) == set(expected['networks']) and
                    (minio_stopped and role == 'minio' or all(row['NetworkSettings']['Networks'][name]['IPAddress'] ==
                     expected['networks'][name]['IPAddress'] for name in expected['networks'])) and
                    row['HostConfig']['PortBindings'] in (None, {}), 'TARGET_CHANGED_OR_EXPOSED')
        proof = pinned_json(self.target['isolationProofPin'])
        network_id = proof['network']['networkId']
        network = json.loads(self.docker(['network', 'inspect', network_id]))[0]
        require(network['Id'] == network_id and network['Internal'] is True and
                set(network['Containers']) == {self.service(role)['id'] for role in ('mysql', 'minio', 'redis')
                                              if not (minio_stopped and role == 'minio')},
                'TARGET_NETWORK_NOT_EXCLUSIVE')
        firewall = pinned_json(self.target['sideEffectIsolationPin'])['firewall']
        import shlex
        for rule in firewall['rules']:
            check_pin(self.config['iptablesPin'], content=False)
            self.command([self.config['iptablesPin']['path'], '-w', '5', '-C', *rule])
            raw = self.command([self.config['iptablesPin']['path'], '-w', '5', '-S', rule[0]])
            first = next((line for line in raw.decode().splitlines() if line.startswith('-A ')), None)
            require(first and shlex.split(first) == ['-A', *rule], 'TARGET_FIREWALL_CHANGED')
        sql = self.modules['formal_sql_restore']
        (sql.import_database_state if importing else sql.database_state)(self.mysql, self.db_target)

    def restore_database_settings(self):
        """Align the already provisioned, empty database from this FULL step.

        No live source access or final-incremental settings are used. The same
        pinned observation and proof validator also feed the final comparison.
        """
        self.bound()
        database = self.material['database']
        require(database['method'] == 'FORMAL_SQL_FULL', 'FULL_DATABASE_SETTINGS_REQUIRED')
        reference = database['expectedDataPin']
        require(reference in self.material['payloadPins'], 'DATABASE_SETTINGS_NOT_ARCHIVED')
        expected = pinned_json(reference)
        self.modules['formal_data_evidence'].compare_data(expected, expected)
        name = self.config['database']
        schema = expected['schema']
        require(schema['database'] == name and set(schema['definitions']['DATABASE']) == {name},
                'ARCHIVED_DATABASE_TARGET_MISMATCH')
        wanted = database_settings(schema['definitions']['DATABASE'][name], name)
        sql = self.modules['formal_sql_restore']
        sql.empty_database(self.mysql, self.db_target)

        def observe():
            self.bound()
            rows = self.mysql.schema_query('SHOW CREATE DATABASE `' + name + '`;',
                database=name, expected_uuid=self.db_uuid)
            require(len(rows) == 1, 'TARGET_DATABASE_DEFINITION_INVALID')
            return database_settings(rows[0], name)

        before = observe()
        intent = write(self.root/'database-settings-intent.json', dict(
            archivedDataPin=reference, database=name, databaseUuid=self.db_uuid,
            before=before, expected=wanted))
        self.original_pins.append(intent)
        if before != wanted:
            self.bound()
            sql.empty_database(self.mysql, self.db_target)
            statement = ('ALTER DATABASE `' + name + '` DEFAULT CHARACTER SET ' + wanted['characterSet'] +
                (' COLLATE ' + wanted['collation'] if wanted['collation'] is not None else '') +
                " DEFAULT ENCRYPTION='" + wanted['encryption'] + "';")
            self.docker(['exec', self.db_container, self.policy['environmentMysqlClientPath'],
                '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--batch', '--skip-column-names',
                '-e', statement], mutation=True)
        after = observe()
        require(after == wanted, 'DATABASE_SETTINGS_READBACK_MISMATCH')
        evidence = write(self.root/'database-settings.json', dict(archivedDataPin=reference,
            database=name, databaseUuid=self.db_uuid, before=before, expected=wanted, after=after,
            changed=before != wanted))
        self.original_pins.append(evidence)
        return evidence

    def full_database(self):
        self.bound()
        sql = self.modules['formal_sql_restore']; database = self.material['database']
        require(database['method'] == 'FORMAL_SQL_FULL' and database['sqlPin'] in self.material['payloadPins'],
                'FULL_SQL_ARCHIVED_PAYLOAD_REQUIRED')
        sql.empty_database(self.mysql, self.db_target)
        expanded = self.root/'expanded.sql'
        with self.timed_stage('sql-stage'):
            staged = stage_private_sql(database['sqlPin'], self.root/'archive-sql.private.gz', self.seconds())
        write(self.root/'sql-archive-stage.json', dict(sourcePin=database['sqlPin'], stagedPin=staged))
        with self.timed_stage('sql-expand'):
            checksum, size = sql.expand_checked(staged['path'], expanded, database['sqlPin']['sha256'],
                                              self.policy['maxExpandedBytes'], self.seconds())
        settings = self.restore_database_settings()
        self.bound(); sql.empty_database(self.mysql, self.db_target)
        write(self.root/'sql-import-intent.json', dict(operationId=self.original['operationId'],
              targetIdentityPin=self.target['targetIdentityPin'], databaseUuid=self.db_uuid,
              sourceSqlPin=database['sqlPin'], expandedSha256=checksum, expandedBytes=size))
        with self.timed_stage('sql-import'):
            self.import_sql(expanded, checksum)
        with self.timed_stage('sql-readback'):
            result = self.database_readback()
        result['databaseSettingsPin'] = settings
        return result

    def incremental_database(self):
        previous = pinned_json(self.request['previousDatabaseResultPin'])
        require(previous['endPosition'] == self.material['database']['startPosition'] and
                previous['databaseUuid'] == self.db_uuid and (previous['fullSchemaDataEquivalenceVerified'] is True or
                 previous.get('incrementalReplayAndAffectedDataVerified') is True),
                'PREVIOUS_DATABASE_STEP_REQUIRED')
        if self.material['database']['method'] == 'BINLOG_SQL':
            return self.incremental_captured_sql()
        segments = ordered_segments(self.material)
        tool = self.policy['mysqlbinlogPin']; check_pin(tool, content=False)
        results = []
        for index, segment in enumerate(segments):
            self.bound()
            expanded = self.root/('binlog-%03d.sql' % index)
            argv = [tool['path'], '--no-defaults', '--disable-log-bin',
                    '--start-position=' + str(segment['startPosition']['position']),
                    '--stop-position=' + str(segment['endPosition']['position']), segment['payloadPin']['path']]
            raw = self.command(argv)
            require(raw and b'BINLOG ' in raw, 'BINLOG_ROW_EVENTS_REQUIRED')
            require(len(raw) <= self.policy['maxExpandedBytes'], 'BINLOG_EXPANSION_LIMIT')
            with expanded.open('xb') as stream:
                os.chmod(expanded, 0o600); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            checksum = hashlib.sha256(raw).hexdigest()
            intent = write(self.root/('binlog-intent-%03d.json' % index),
                dict(segment=segment, targetIdentityPin=self.target['targetIdentityPin'], expandedPin=pin(expanded)))
            self.import_sql(expanded, checksum)
            results.append(intent)
        result = self.database_readback()
        result['segmentEvidencePins'] = results
        return result

    def incremental_captured_sql(self):
        """W02 archives verified mysqlbinlog output, never another full dump."""
        database = self.material['database']; capture = pinned_json(database['capturePointPin'])
        delta = capture['databaseDelta']
        require(capture['schemaVersion'] == 'backup-capture-point/v1' and capture['pointType'] == 'INCREMENTAL' and
                capture['commonRecoveryPoint'] == self.material['recoveryPoint'] and
                delta['kind'] == 'BINLOG_SQL' and delta['parentPosition'] == database['startPosition'] and
                capture['databaseEnd'] == database['endPosition'], 'CAPTURED_BINLOG_BINDING_INVALID')
        previous = database['startPosition']
        for segment in delta['segments']:
            require(segment['startPosition'] >= 4 and segment['stopPosition'] > segment['startPosition'],
                    'CAPTURED_BINLOG_RANGE_INVALID')
            require(segment['file'] == previous['file'] and segment['startPosition'] == previous['position'] or
                    segment['startPosition'] == 4 and
                    segment['file'].rsplit('.', 1)[0] == previous['file'].rsplit('.', 1)[0] and
                    int(segment['file'].rsplit('.', 1)[1]) == int(previous['file'].rsplit('.', 1)[1])+1,
                    'CAPTURED_BINLOG_GAP')
            previous = {**previous, 'file': segment['file'], 'position': segment['stopPosition']}
        require(all(previous[key] == database['endPosition'][key] for key in ('file', 'position')) and
                all(database['startPosition'][key] == database['endPosition'][key] for key in ('databaseUuid', 'serverVersion')),
                'CAPTURED_BINLOG_STOP_MISMATCH')
        require(database['sqlPin'] in self.material['payloadPins'] and database['rawSqlPin'] in self.material['payloadPins'],
                'INCREMENTAL_SQL_NOT_ARCHIVED')
        # Archived paths may differ from capture-host paths; verify exact bytes.
        require(database['rawSqlPin']['sha256'] == delta['rawPin']['sha256'] and
                database['rawSqlPin']['bytes'] == delta['rawPin']['bytes'], 'CAPTURED_BINLOG_RAW_MISMATCH')
        self.bound()
        expanded = self.root/'incremental.sql'
        with self.timed_stage('sql-stage'):
            staged = stage_private_sql(database['sqlPin'], self.root/'archive-sql.private.gz', self.seconds())
        with self.timed_stage('sql-expand'):
            checksum, _ = self.modules['formal_sql_restore'].expand_checked(staged['path'], expanded,
                database['sqlPin']['sha256'], self.policy['maxExpandedBytes'], self.seconds())
        raw = expanded.read_bytes()
        # DDL Query events are executable text in mysqlbinlog output; a DDL-only
        # range need not contain a row-event BINLOG block. Exact archived bytes,
        # capture binding and contiguous positions were verified above. Scope
        # is checked against the original events before/after capture export.
        require(raw.startswith(b'-- IntRuoyi binlog incremental;'), 'CAPTURED_BINLOG_SQL_REQUIRED')
        mode = delta.get('logMode', 'GTID')
        require(mode in ('GTID', 'FILE_POSITION'), 'CAPTURED_BINLOG_LOG_MODE_INVALID')
        if mode == 'GTID':
            require(not delta['segments'] or b'BINLOG ' in raw or
                    re.search(rb"SET @@SESSION\.GTID_NEXT\s*=\s*'[0-9a-fA-F-]+:[0-9]+'", raw),
                    'CAPTURED_BINLOG_SQL_REQUIRED')
        scoped = delta.get('dataObservation') == 'AFFECTED_TABLES_V1'
        require(delta.get('dataObservation') in (None, 'AFFECTED_TABLES_V1'), 'CAPTURED_DATA_OBSERVATION_INVALID')
        if mode == 'FILE_POSITION':
            modes = [ref for ref in self.material['payloadPins']
                     if ref['path'].endswith('/payload/database-log-mode.json')]
            require(len(modes) == 1 and pinned_json(modes[0]) ==
                    dict(mode='FILE_POSITION', observedGtidMode='OFF') and
                    database['startPosition']['executedGtidSet'] ==
                    database['endPosition']['executedGtidSet'] == '', 'CAPTURED_BINLOG_LOG_MODE_CHANGED')
        if mode == 'FILE_POSITION' or scoped:
            scopes = [ref for ref in self.material['payloadPins']
                      if ref['path'].endswith('/payload/database.sql.incremental-scope.json')]
            require(len(scopes) == 1, 'CAPTURED_BINLOG_SCOPE_BINDING_INVALID')
            scope = pinned_json(scopes[0])
            require(scope['schemaVersion'] in (('backup-binlog-event-scope/v2', 'backup-binlog-event-scope/v3') if scoped else
                    ('backup-binlog-event-scope/v1', 'backup-binlog-event-scope/v2', 'backup-binlog-event-scope/v3')) and
                    scope['logMode'] == mode and scope['databaseScope'] == [self.config['database']] and
                    (scope['policy'] == ('MYSQL80_ROW_AND_SCOPED_DATABASE_DDL' if
                     scope['schemaVersion'] == 'backup-binlog-event-scope/v3' else 'MYSQL80_ROW_AND_SCOPED_TABLE_DDL')) and
                    scope['parentPosition'] == database['startPosition'] and
                    scope['endPosition'] == database['endPosition'] and
                    [s['segment'] for s in scope['segments']] == delta['segments'] and
                    all(scope['rawSqlPin'][k] == database['rawSqlPin'][k] for k in ('bytes', 'sha256')),
                    'CAPTURED_BINLOG_SCOPE_BINDING_INVALID')
        if scoped:
            self.modules['formal_data_evidence'].incremental_observation_tables(
                pinned_json(database['expectedDataPin']), scope, capture, self.config['database'])
        if delta['segments']:
            with self.timed_stage('sql-import'):
                self.import_sql(expanded, checksum)
        with self.timed_stage('sql-readback'):
            result = self.database_readback()
        return result

    def database_readback(self):
        self.bound()
        data = self.modules['formal_data_evidence']
        limits = data.validate_limits(self.policy['dataLimits'])
        limits['seconds'] = min(limits['seconds'], self.seconds())
        database = self.material['database']
        expected = pinned_json(database['expectedDataPin'])
        capture = pinned_json(database['capturePointPin']) if database['method'] == 'BINLOG_SQL' else None
        scoped = capture is not None and capture['databaseDelta'].get('dataObservation') == 'AFFECTED_TABLES_V1'
        if scoped:
            refs = [ref for ref in self.material['payloadPins']
                if ref['path'].endswith('/payload/database.sql.incremental-scope.json')]
            require(len(refs) == 1, 'CAPTURED_BINLOG_SCOPE_BINDING_INVALID')
            scope = pinned_json(refs[0])
            changed = data.incremental_observation_tables(expected, scope, capture, self.config['database'])
            observed = data.observe_affected_data(self.mysql, self.config['database'], self.db_uuid,
                affected_tables=changed, guard=self.guard, scratch=self.root/'database-readback', **limits)
        else:
            require(expected['encoding'] == data.ENCODING, 'CAPTURED_DATA_OBSERVATION_INVALID')
            observed = data.observe_data(self.mysql, self.config['database'], self.db_uuid, guard=self.guard,
                scratch=self.root/'database-readback', **limits)
        comparison = data.compare_data(expected, observed)
        observed_pin = write(self.root/'database-observed.json', observed)
        comparison_pin = write(self.root/'database-comparison.json', comparison)
        self.bound()
        result = dict(recoveryPoint=self.material['recoveryPoint'], databaseUuid=self.db_uuid,
                    endPosition=self.material['database']['endPosition'],
                    observedPin=observed_pin, comparisonPin=comparison_pin,
                    fullSchemaDataEquivalenceVerified=not scoped,
                    applicationVerified=False)
        if scoped:
            result.update(incrementalReplayAndAffectedDataVerified=True,
                previousDatabaseResultPin=self.request['previousDatabaseResultPin'])
        return result

    def object_client(self):
        self.bound()
        service = self.config_services['minio']
        endpoint = 'http://' + service['ip'] + ':9000'
        require(endpoint not in pinned_json(self.material['sourceScopePin'])['endpointHosts'], 'SOURCE_ENDPOINT_REJECTED')
        client = self.modules['formal_s3_export'].IsolatedRestoreS3(endpoint,
            self.secret('minio', 'MINIO_ROOT_USER'), self.secret('minio', 'MINIO_ROOT_PASSWORD'),
            approved_endpoint=endpoint, timeout=min(30, self.seconds()))
        native = self

        class GuardedClient:
            def __getattr__(self, name):
                method = getattr(client, name)
                def call(*args, **kwargs):
                    mutation = name in ('put_version', 'delete_marker')
                    (native.bound if mutation else native.guard)()
                    native.mutation_dispatched |= mutation
                    try:
                        result = method(*args, **kwargs)
                    except Exception as error:
                        if mutation: error.unknown = True
                        raise
                    (native.bound if mutation else native.guard)()
                    return result
                return call
        return GuardedClient()

    def full_objects(self):
        objects = self.material['objects']
        require(objects['method'] == 'FORMAL_OBJECT_EXPORT', 'OBJECT_FULL_METHOD_UNSUPPORTED')
        receipt = pinned_json(objects['exportReceiptPin'])
        check_pin(objects['inventoryPin'])
        require(objects['inventoryPin']['path'] == str(Path(objects['exportReceiptPin']['path']).parent/'versions.jsonl'),
                'OBJECT_EXPORT_PATH_BINDING_INVALID')
        mapping = self.policy['bucketMapping']
        require(set(mapping.values()) == set(self.config['buckets']), 'TARGET_BUCKET_SCOPE_MISMATCH')
        self.prepare_empty_buckets()
        result = self.modules['formal_s3_export'].restore_s3_versions(self.object_client(),
            str(Path(objects['exportReceiptPin']['path']).parent), str(self.root/'object-restore'),
            bucket_mapping=mapping, source_inventory_sha256=objects['inventoryPin']['sha256'],
            source_export_receipt_sha256=objects['exportReceiptPin']['sha256'], timeout=self.seconds())
        self.bound()
        return dict(recoveryPoint=self.material['recoveryPoint'], restoreReceiptPin=pin(self.root/'object-restore'/'restore-receipt.json'),
                    versionMappingPin=pin(self.root/'object-restore'/'version-mapping.jsonl'), result=result,
                    permissionEvidencePin=self.check_bucket_permissions())

    def physical_object_chain(self):
        """Keep storage stopped across the whole raw file chain; start once."""
        from recovery_data_files import apply_tree, inventory, physical_chain_inputs
        chain = resolve_chain(self.original['selectedPointPin'], self.policy)
        require(self.request['allMaterialPins'] == [step[3] for step in chain] and
                all(step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain), 'PHYSICAL_CHAIN_SCOPE_INVALID')
        require(all(key == value for key, value in self.policy['bucketMapping'].items()),
                'PHYSICAL_BUCKET_RENAME_UNSUPPORTED')
        file_steps = physical_chain_inputs(chain)
        approval_pin = self.policy['physicalStartupApprovalPin']
        require(approval_pin['sha256'] in self.trust['physicalStartupApprovalSha256s'], 'PHYSICAL_STARTUP_NOT_APPROVED')
        approval = pinned_json(approval_pin)
        from recovery_engine import current_window
        require(approval['schemaVersion'] == 'RecoveryPhysicalStartupApproval/v1' and
                approval['approved'] is True and approval['targetIdentityPin'] == self.target['targetIdentityPin'] and
                approval['recoveryPoint'] == self.plan['recoveryPoint'] and
                approval['imageId'] == self.service('minio')['imageId'] and
                all(approval[name] is True for name in ('notificationAbsent', 'lifecycleAbsent', 'replicationAbsent',
                    'externalTierAbsent', 'pendingJobsAbsent', 'credentialsCompatible')), 'PHYSICAL_STARTUP_DEPENDENCIES_UNPROVEN')
        current_window(approval)
        require(approval['inventoryPins'] == [step[2]['objects']['fileInventoryPin'] for step in chain],
                'PHYSICAL_CAPTURE_INVENTORY_MISMATCH')
        self.bound()
        service = self.service('minio')
        mounts = [entry for entry in service['mounts'] if entry['Destination'] == self.policy['minioDataMount']]
        require(len(mounts) == 1 and mounts[0]['Type'] == 'volume', 'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')
        volume = json.loads(self.docker(['volume', 'inspect', mounts[0]['Name']]))[0]
        require(volume['Driver'] == 'local' and not volume['Options'] and volume['Labels'] == service['labels'] and
                volume['Mountpoint'] == mounts[0]['Source'] ==
                pinned_json(self.policy['dataTargetPin'])['versionedDataLocation'], 'PHYSICAL_TARGET_VOLUME_INVALID')
        all_ids = self.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines()
        for identity in all_ids:
            if identity == service['id']: continue
            row = json.loads(self.docker(['inspect', identity]))[0]
            require(all(mount.get('Name') != mounts[0]['Name'] and mount.get('Source') != mounts[0]['Source']
                        for mount in row['Mounts']), 'PHYSICAL_VOLUME_SHARED')
        write(self.root/'physical-stop-intent.json', dict(containerId=service['id'], approvalPin=approval_pin,
              volumeIdentity=volume, preserveExisting=True))
        self.docker(['stop', '--time', str(self.policy['storageStopSeconds']), service['id']], mutation=True)
        self.bound(minio_stopped=True)
        root = absolute(volume['Mountpoint'])
        initial = pinned_json(approval['initializationInventoryPin'])
        require(inventory(root, lambda: self.bound(minio_stopped=True)) == initial and
                all(name == '.minio.sys' or name.startswith('.minio.sys/') for name in initial),
                'INITIALIZED_TARGET_TREE_NOT_APPROVED')
        apply_tree(root, initial, {}, {}, full=False, guard=lambda: self.bound(minio_stopped=True))
        steps = []
        for index, (material_pin, prior, expected, payloads, changed, deleted) in enumerate(file_steps):
            intent = write(self.root/('physical-step-%03d-intent.json' % index),
                           dict(materialPin=material_pin, changedPaths=sorted(changed), deletedPaths=sorted(deleted)))
            self.original_pins.append(intent)
            result = apply_tree(root, prior, expected, payloads, full=index == 0,
                guard=lambda: self.bound(minio_stopped=True), ownership=self.policy['minioFileOwnership'])
            steps.append(write(self.root/('physical-step-%03d-readback.json' % index), result))
        current_window(approval); self.bound(minio_stopped=True)
        self.docker(['start', service['id']], mutation=True)
        # Read-only readiness polling never repeats a storage mutation.
        deadline = min(time.monotonic()+self.policy['storageReadinessSeconds'], self.budget.deadline)
        import urllib.error
        while True:
            self.bound()
            client = self.object_client()
            try:
                with client._get('') as response: response.read(1024*1024+1)
                break
            except (urllib.error.URLError, OSError) as error:
                if time.monotonic() >= deadline: raise RecoveryError('PHYSICAL_STORAGE_NOT_READY') from error
                time.sleep(0.25)
        descriptor = self.material['objects']
        check_pin(descriptor['inventoryPin']); check_pin(descriptor['exportReceiptPin'])
        export = self.modules['formal_s3_export'].export_s3_versions(client, self.config['buckets'],
                  self.root/'physical-export', guard=self.bound, timeout=self.seconds())
        from recovery_data_objects import compare_indexed_restore
        comparison = compare_indexed_restore(chain, self.policy, self.root/'physical-export', export,
                                             self.modules['formal_physical_restore_readback'], self.bound)
        mapping = self.root/'physical-version-mapping.jsonl'
        with mapping.open('xb') as output:
            os.chmod(mapping, 0o600)
            for row in [json.loads(line) for line in check_pin(descriptor['inventoryPin']).splitlines()]:
                output.write(canonical(dict(sourceBucket=row['bucket'], targetBucket=row['bucket'], key=row['key'],
                    sourceVersionId=row['versionId'], targetVersionId=row['versionId'], kind=row['kind'], isLatest=row['isLatest']))+b'\n')
            output.flush(); os.fsync(output.fileno())
        return dict(recoveryPoint=self.plan['recoveryPoint'], versionMappingPin=pin(mapping),
                    physicalStepEvidencePins=steps, comparisonPin=write(self.root/'physical-comparison.json', comparison),
                    permissionEvidencePin=self.check_bucket_permissions(), originalVersionIdsPreserved=True)

    def prepare_empty_buckets(self):
        """Only create explicitly listed absent buckets inside the bound netns."""
        service = self.config_services['minio']
        client = self.modules['formal_s3_export'].IsolatedRestoreS3('http://'+service['ip']+':9000',
            self.secret('minio', 'MINIO_ROOT_USER'), self.secret('minio', 'MINIO_ROOT_PASSWORD'),
            approved_endpoint='http://'+service['ip']+':9000', timeout=min(30, self.seconds()))
        from recovery_data_objects import prepare_buckets
        def record(name, value):
            self.mutation_dispatched |= value.get('state') != 'NOT_DISPATCHED'
            persist_evidence(self.root/name, value, self.original_pins,
                             unknown=value.get('state') == 'TERMINAL_UNKNOWN')
        try:
            prepare_buckets(client, self.config['buckets'], self.policy['bucketSettings'],
                            guard=self.bound, intent=record)
            self.mutation_dispatched = True
        except Exception as error:
            self.mutation_dispatched |= bool(getattr(error, 'unknown', False))
            raise

    def check_bucket_permissions(self):
        self.bound()
        client = self.object_client(); expected_pin = self.policy['bucketProtectionPin']; expected = pinned_json(expected_pin)
        from recovery_data_objects import protection
        observed = protection(client, self.config['buckets'], expected, guard=self.bound)
        check_pin(expected_pin); self.bound()
        observed.update(expectedProtectionPin=expected_pin, targetIdentityPin=self.target['targetIdentityPin'],
                        operationId=self.original['operationId'], recoveryPoint=self.plan['recoveryPoint'])
        return write(self.root/'bucket-permissions.json', observed)

    def incremental_objects(self):
        objects = self.material['objects']
        require(objects['method'] == 'VERSION_DELTA', 'REAL_OBJECT_DELTA_REQUIRED')
        delta = pinned_json(objects['deltaPin'])
        require(delta['schemaVersion'] == 'RecoveryObjectDelta/v1' and delta['recoveryPoint'] == self.material['recoveryPoint'] and
                delta['parentRecoveryPoint'] == self.request['parentRecoveryPoint'], 'OBJECT_DELTA_POINT_MISMATCH')
        mapping = self.policy['bucketMapping']; client = self.object_client(); rows = []
        old = self.request['previousObjectResultPin']
        require(old is not None, 'OBJECT_PARENT_RESULT_REQUIRED')
        previous = pinned_json(old)
        for line in check_pin(previous['versionMappingPin']).splitlines():
            rows.append(json.loads(line))
        for index, row in enumerate(delta['changes']):
            require(row['kind'] in ('PUT', 'DELETE_MARKER') and row['bucket'] in mapping and row['key'], 'OBJECT_DELTA_INVALID')
            bucket = mapping[row['bucket']]
            intent = write(self.root/('object-intent-%06d.json' % index), row)
            self.original_pins.append(intent)
            if row['kind'] == 'PUT':
                payload = row['contentPin']; check_pin(payload, content=False)
                require(payload in self.material['payloadPins'], 'OBJECT_CONTENT_NOT_ARCHIVED')
                version = client.put_version(bucket, row['key'], payload['path'], row['headers'], payload['bytes'], payload['sha256'])
            else:
                require(row['contentPin'] is None, 'DELETE_MARKER_CONTENT_INVALID')
                version = client.delete_marker(bucket, row['key'])
            for old_row in rows:
                if old_row['targetBucket'] == bucket and old_row['key'] == row['key']:
                    old_row['isLatest'] = False
            rows.append(dict(sourceBucket=row['bucket'], targetBucket=bucket, key=row['key'],
                             kind='version' if row['kind'] == 'PUT' else 'delete-marker', sourceVersionId=row['sourceVersionId'],
                             targetVersionId=version, isLatest=True))
            with (self.root/'version-mapping.jsonl').open('ab') as stream:
                os.chmod(self.root/'version-mapping.jsonl', 0o600)
                stream.write(canonical(rows[-1])+b'\n'); stream.flush(); os.fsync(stream.fileno())
        # Retain the full original-to-target version mapping for downstream references.
        complete = self.root/'complete-version-mapping.jsonl'
        with complete.open('xb') as stream:
            os.chmod(complete, 0o600)
            for row in rows:
                stream.write(canonical(row)+b'\n')
            stream.flush(); os.fsync(stream.fileno())
        self.verify_object_inventory(client, rows, objects['expectedInventoryPin'])
        return dict(recoveryPoint=self.material['recoveryPoint'], versionMappingPin=pin(complete),
                    permissionEvidencePin=self.check_bucket_permissions())

    def verify_object_inventory(self, client, rows, expected_pin):
        expected_rows = [json.loads(line) for line in check_pin(expected_pin).splitlines()]
        lookup = {(r['bucket'], r['key'], r['versionId']): r for r in expected_rows}
        require(len(lookup) == len(expected_rows) == len(rows), 'OBJECT_HISTORY_SCOPE_MISMATCH')
        for bucket in self.config['buckets']:
            observed = {}; cursor = None; seen = set()
            while True:
                page, next_cursor = client.versions(bucket, cursor)
                for row in page:
                    key = (row['key'], row['versionId'])
                    require(key not in observed, 'OBJECT_VERSION_DUPLICATE')
                    observed[key] = (row['kind'], row['isLatest'])
                if next_cursor is None:
                    break
                require(next_cursor not in seen, 'OBJECT_CURSOR_CYCLE')
                seen.add(next_cursor); cursor = next_cursor
            mapped = {(r['key'], r['targetVersionId']): (r['kind'], r['isLatest']) for r in rows if r['targetBucket'] == bucket}
            require(observed == mapped, 'OBJECT_TARGET_HISTORY_MISMATCH')
        for row in rows:
            expected = lookup[(row['sourceBucket'], row['key'], row['sourceVersionId'])]
            require((expected['kind'], expected['isLatest']) == (row['kind'], row['isLatest']), 'OBJECT_SOURCE_HISTORY_MISMATCH')
            if row['kind'] == 'version':
                response, headers = client.content(row['targetBucket'], row['key'], row['targetVersionId'])
                sha = hashlib.sha256(); size = 0
                try:
                    require(all(headers.get(k) == v for k, v in expected['headers'].items()), 'OBJECT_METADATA_MISMATCH')
                    while chunk := response.read(1024*1024):
                        self.guard(); size += len(chunk); sha.update(chunk)
                        require(size <= expected['size'], 'OBJECT_CONTENT_SIZE_MISMATCH')
                finally:
                    response.close()
                require(size == expected['size'] and sha.hexdigest() == expected['sha256'], 'OBJECT_CONTENT_DIGEST_MISMATCH')

    def consistency(self):
        self.bound()
        db = pinned_json(self.request['databaseResultPin']); objects = pinned_json(self.request['objectResultPin'])
        require(db['recoveryPoint'] == objects['recoveryPoint'] == self.plan['recoveryPoint'], 'COMMON_RECOVERY_POINT_MISMATCH')
        reference = pinned_json(self.material['referenceInventoryPin'])
        require(reference['schemaVersion'] == 'RecoveryReferenceInventory/v1' and
                reference['recoveryPoint'] == self.plan['recoveryPoint'] and reference['complete'] is True,
                'COMPLETE_REFERENCE_INVENTORY_REQUIRED')
        mappings = [json.loads(line) for line in check_pin(objects['versionMappingPin']).splitlines()]
        latest = {(r['sourceBucket'], r['key']): r for r in mappings if r['isLatest']}
        versions = {(r['sourceBucket'], r['key'], r['sourceVersionId']): r for r in mappings}
        # Query recipes come from the provisioned policy, never request SQL.
        observations = []
        for recipe in self.policy['referenceQueries']:
            require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', recipe['table']) and
                    all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', c) for c in recipe['columns']), 'REFERENCE_QUERY_IDENTIFIER_INVALID')
            self.mysql.query('DESCRIBE `' + self.config['database'] + '`.`' + recipe['table'] + '`;')
            query = 'SELECT ' + ','.join('HEX(CAST(`'+c+'` AS BINARY))' for c in recipe['columns']) + \
                    ' FROM `'+self.config['database']+'`.`'+recipe['table']+'`;'
            raw = self.mysql.query(query)
            rows = [[None if cell == 'NULL' else bytes.fromhex(cell).decode('utf-8') for cell in line.split('\t')]
                    for line in raw.splitlines()]
            observations.extend(dict(zip(recipe['columns'], row), table=recipe['table']) for row in rows)
        require(sorted(observations, key=canonical) == sorted(reference['databaseRows'], key=canonical),
                'DATABASE_REFERENCE_ROWS_MISMATCH')
        client = self.object_client()
        missing = reference.get('sourceMissingObjectReferences', [])
        if 'sourceMissingObjectReferences' in reference:
            require(self.policy.get('sourceMissingReferencePolicy') == 'PRESERVE_SOURCE_BASELINE',
                'SOURCE_MISSING_REFERENCE_POLICY_REQUIRED')
            from formal_capture_semantics import resolve_object_references
            source_versions = [json.loads(line) for line in check_pin(self.material['objects']['inventoryPin']).splitlines()]
            derived_missing = []
            derived_present = resolve_object_references(observations, self.policy['objectBindings'],
                source_versions, missing=derived_missing)
            # SQL row order is unspecified; preserve multiplicity while comparing references.
            require(sorted(derived_missing, key=canonical) == sorted(missing, key=canonical) and
                derived_present == reference['objectReferences'],
                'SOURCE_MISSING_REFERENCE_BASELINE_MISMATCH')
            for ref in missing:
                require((ref['bucket'], ref['key']) not in latest if ref['sourceVersionId'] is None else
                    (ref['bucket'], ref['key'], ref['sourceVersionId']) not in versions,
                    'SOURCE_MISSING_REFERENCE_BASELINE_CHANGED')
        for ref in {canonical(r): r for r in reference['objectReferences']}.values():
            match = latest.get((ref['bucket'], ref['key'])) if ref['sourceVersionId'] is None else \
                    versions.get((ref['bucket'], ref['key'], ref['sourceVersionId']))
            require(match and match['kind'] == 'version', 'REFERENCED_OBJECT_MISSING_OR_DELETED')
            if ref['sourceVersionId'] is not None:
                require(match['sourceVersionId'] == match['targetVersionId'], 'DATABASE_VERSION_REFERENCE_REWRITE_REQUIRED')
            if objects.get('payloadContentVerified') is False:
                continue
            response, headers = client.content(match['targetBucket'], match['key'], match['targetVersionId'])
            checksum = hashlib.sha256(); size = 0
            try:
                while chunk := response.read(1024*1024):
                    self.guard(); size += len(chunk); checksum.update(chunk)
                    require(size <= ref['bytes'], 'REFERENCE_CONTENT_SIZE_MISMATCH')
            finally:
                response.close()
            require(size == ref['bytes'] and checksum.hexdigest() == ref['sha256'], 'REFERENCE_CONTENT_MISMATCH')
        for invariant in self.policy['businessInvariants']:
            require(invariant['queryPin'] in self.policy['approvedReadOnlyQueryPins'], 'INVARIANT_QUERY_NOT_APPROVED')
            query = check_pin(invariant['queryPin']).decode('utf-8')
            require(query.lstrip().upper().startswith('SELECT ') and ';' not in query.rstrip().rstrip(';') and
                    not re.search(r'\b(INTO|OUTFILE|DUMPFILE|LOAD_FILE|SLEEP|GET_LOCK|RELEASE_LOCK|FOR\s+UPDATE)\b',
                                  query, re.IGNORECASE), 'INVARIANT_QUERY_NOT_READONLY')
            require(self.mysql.query(query) == invariant['expectedOutput'], 'BUSINESS_INVARIANT_FAILED')
        return dict(schemaVersion='RecoveryConsistencyEvidence/v1', recoveryPoint=self.plan['recoveryPoint'],
                    targetIdentityPin=self.target['targetIdentityPin'], databaseResultPin=self.request['databaseResultPin'],
                    objectResultPin=self.request['objectResultPin'], referenceInventoryPin=self.material['referenceInventoryPin'],
                    allReferencesVerified=not missing, presentReferencesVerified=True,
                    sourceMissingReferenceCount=len(missing), sourceMissingBaselinePreserved=True,
                    invariantsVerified=True, payloadContentVerified=objects.get('payloadContentVerified', True),
                    applicationVerified=False, observedAt=utc())


def run_worker(request, root):
    budget = Budget(request['deadlineMilliseconds'])
    base = {'schemaVersion', 'operationId', 'requestId', 'action', 'originalRequestPin', 'planPin',
            'recoveryTargetPin', 'materialPin', 'deadlineMilliseconds'}
    extras = {'DATABASE_FULL': set(), 'DATABASE_INCREMENTAL': {'previousDatabaseResultPin'},
              'OBJECT_FULL': {'previousObjectResultPin', 'parentRecoveryPoint'},
              'OBJECT_INCREMENTAL': {'previousObjectResultPin', 'parentRecoveryPoint'},
              'OBJECT_CHAIN_PHYSICAL': {'allMaterialPins'}, 'DERIVED_DATA': {'databaseResultPin', 'objectResultPin'},
              'CONSISTENCY': {'databaseResultPin', 'objectResultPin'}}
    require(request['schemaVersion'] == 'RecoveryDataRequest/v1' and request['action'] in extras and
            set(request) == base | extras[request['action']], 'DATA_WORKER_REQUEST_INVALID')
    original = pinned_json(request['originalRequestPin'])
    trust, policy, config = trusted_configuration(original)
    identity = pinned_json(policy['dataTargetPin'])['targetIdentityPin']
    authorities(original, identity, ['RESTORE_EXECUTE'], trust)
    inherit_read_guard(original, request['originalRequestPin'], policy, budget)
    plan = validate_record(pinned_json(request['planPin']), 'RestorePlan', policy['recordSchemasPin'])
    chain = resolve_chain(original['selectedPointPin'], policy)
    require(plan['immutableInputsSha256'] == digest(immutable_inputs(original, policy, chain)) and
            request['materialPin'] in [s[3] for s in chain], 'WORKER_INPUT_PLAN_MISMATCH')
    target_request = dict(original, inputPins={'recoveryTarget': request['recoveryTargetPin']})
    target = prepared_target(target_request, plan, policy, trust)
    require(request['operationId'] == original['operationId'] and request['deadlineMilliseconds'] <= original['deadlineMilliseconds'],
            'WORKER_OPERATION_OR_DEADLINE_MISMATCH')
    require(request['planPin'] in original['inputPins'].values() or original['action'] in ('REHEARSAL', 'CONTROLLED_CUTOVER'),
            'WORKER_PLAN_NOT_AUTHORIZED')
    material = pinned_json(request['materialPin']); budget.remaining()
    native = NativeData(request, original, trust, policy, config, target, plan, material, budget, root)
    actions = {'DATABASE_FULL': native.full_database, 'DATABASE_INCREMENTAL': native.incremental_database,
               'OBJECT_FULL': native.full_objects, 'OBJECT_INCREMENTAL': native.incremental_objects,
               'OBJECT_CHAIN_PHYSICAL': native.physical_object_chain,
               'CONSISTENCY': native.consistency}
    from recovery_data_derived import restore_derived
    actions['DERIVED_DATA'] = lambda: restore_derived(native)
    require(request['action'] in actions, 'DATA_WORKER_ACTION_UNSUPPORTED')
    try:
        result = actions[request['action']]()
        for item in material['payloadPins']: check_pin(item, content=False)
        return result, native
    except Exception as error:
        error.native = native
        if native.mutation_dispatched and native.last_exit is None:
            error.unknown = True
        persist_evidence(root/'failure-protection.json', dict(schemaVersion='RecoveryFailureProtection/v1',
            targetIdentityPin=target['targetIdentityPin'], applicationWrites='UNKNOWN',
            partialTargetRetained=True, retryPermitted=False, sourceWritesPerformed=False,
            mutationDispatched=native.mutation_dispatched, originalInvocationPins=native.original_pins,
            errorType=type(error).__name__, remoteTerminalConfirmed=False), native.original_pins,
            unknown=bool(getattr(error, 'unknown', False)), exit_code=native.last_exit)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv); started = utc(); request = load(args.request); native = None
    root = absolute(args.output).parent
    try:
        data, native = run_worker(request, root)
        state, code = 'SUCCEEDED', None
    except Exception as error:
        native = getattr(error, 'native', None)
        data = None
        state = 'TERMINAL_UNKNOWN' if getattr(error, 'unknown', False) else 'FAILED_RETAINED'
        code = getattr(error, 'code', 'DATA_WORKER_' + type(error).__name__.upper())
    result = dict(schemaVersion='RecoveryDataStepResult/v1', operationId=request['operationId'], requestId=request['requestId'],
                  action=request['action'], state=state, failureCode=code, data=data,
                  originalResultPins=[] if native is None else native.original_pins,
                  actualExitCode=None if native is None else native.last_exit, startedAt=started, finishedAt=utc())
    try:
        persist_evidence(args.output, result, [] if native is None else native.original_pins,
                         unknown=state == 'TERMINAL_UNKNOWN', exit_code=result['actualExitCode'])
    except RecoveryError as recording:
        print(recording.code)
        return 2 if recording.unknown else 1
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[state]


if __name__ == '__main__':
    raise SystemExit(main())
