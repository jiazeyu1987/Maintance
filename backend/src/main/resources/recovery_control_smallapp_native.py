"""Single-operator Spug control over the shared capture/archive/recovery CLIs.

Applications differ by registered source and target configuration. Per-operation
signatures, participants, approvals and proof closures are not execution inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

import recovery_control_executor as executor
from recovery_control_smallapp import (BATCH, ROOT, Failure, canonical,
    decode, exact, fingerprint, local_read, native_required, need, opaque, persist, public_error, request, result)

CONFIG_FIELDS = ('schemaVersion batchId hostAddress ledgerRoot registryRoot installationPin '
                 'authorityKeyPin serviceEntryPin nativeEntryPin httpEntryPin supervisorPin dependencyPins '
                 'listenAddress listenPort authCredentialRef allowedClientAddresses engineSelection issuedAt expiresAt')
RESOURCE_FIELDS = ('schemaVersion batchId role configRef tenantId identityPin sourceIdentityPin hostAddress '
    'hostIdentityPin targetId databaseUuid database databaseContainerId objectContainerId applicationContainerId '
    'applicationArtifactPin runtimePin versionPins configurationPin nativeConfigPin ownerProofPin fresh issuedAt expiresAt')
POINT_FIELDS = ('schemaVersion batchId reference sourceIdentityPin pointPin orderedChainPins '
                'acceptedResultPin generationId ownerOperationId issuedAt expiresAt')
BINDING_FIELDS = ('schemaVersion batchId operationId uiRequestSha256 action sourceBindingPin targetBindingPin '
    'pointBindingPin operationRequestPin dispatchPin nativeLaunchPin grantEnvelopePin leaseEnvelopePin '
    'claimPin issuedAt expiresAt')
CLAIM_FIELDS = ('schemaVersion batchId operationId sourceIdentityPin targetIdentityPin leaseRef executorId '
                'state leaseId fenceToken resourceObservationPin issuedAt expiresAt')
OWNERSHIP_FIELDS = ('schemaVersion batchId role tenantId hostAddress resourcePrefix isolatedFromProtectedResources '
    'state identityPin sourceIdentityPin hostIdentityPin targetId databaseUuid database databaseContainerId '
    'objectContainerId applicationContainerId applicationArtifactPin runtimePin versionPins configurationPin '
    'nativeConfigPin fresh originalObservationPins issuedAt expiresAt')
OBSERVATION_FIELDS = ('schemaVersion batchId operationId resourceBindingPin state leaseId fenceToken '
                      'databaseUuid originalObservationPins issuedAt expiresAt')
ACTION = {'FULL': 'BACKUP_FULL', 'INCREMENTAL': 'BACKUP_INCREMENTAL', 'RESTORE': 'REHEARSAL'}


def stamp(value):
    need(type(value) is str and value.endswith('Z'), 'CONTROL_UTC_REQUIRED')
    try:
        converted = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        raise Failure('CONTROL_UTC_INVALID') from None
    need(converted.utcoffset().total_seconds() == 0, 'CONTROL_UTC_INVALID')
    return converted


def window(value):
    now = datetime.now(timezone.utc)
    need(stamp(value['issuedAt']) <= now < stamp(value['expiresAt']), 'CURRENT_CONTROL_EXPIRED')


def directory(path, task_root):
    native_required()
    value = Path(path)
    scope = Path(task_root)
    need(scope.is_absolute() and scope.resolve() == scope and scope != Path('/') and
         value.is_absolute() and value.resolve() == value and scope in value.parents,
         'PRIVATE_DIRECTORY_SCOPE_INVALID')
    for ancestor in reversed((value, *value.parents)):
        info = ancestor.lstat()
        need(stat_directory(info) and not info.st_mode & 0o022, 'PRIVATE_DIRECTORY_ANCESTOR_INVALID')
    info = value.stat()
    need(info.st_uid == info.st_gid == 0 and info.st_mode & 0o777 == 0o700,
         'PRIVATE_DIRECTORY_CUSTODY_INVALID')
    return value


def stat_directory(info):
    import stat
    return stat.S_ISDIR(info.st_mode)


SINGLE_CONFIG_FIELDS = ('schemaVersion taskRoot ledgerRoot registryRoot listenAddress listenPort authCredentialRef '
    'allowedClientAddresses pythonPin programPins workingDirectory environment deadlineMilliseconds '
    'engineSelectionRef sourceConfigurations restoreConfigurations')


class Native:
    """Single-operator Spug -> common owner CLI, with durable original-ID queries."""
    def __init__(self, config_pin):
        self.config_pin = config_pin
        executor.pin_reference(config_pin)

    def raw(self, pin):
        executor.verify(pin)
        actual, raw = executor.pinned_read(pin['path'], True)
        need(actual == pin, 'CONFIGURATION_CHANGED')
        return raw

    def document(self, pin):
        return decode(self.raw(pin))

    def configuration(self):
        native_required()
        config = self.document(self.config_pin)
        exact(config, SINGLE_CONFIG_FIELDS, 'SERVER_CONFIGURATION_FIELDS_INVALID')
        need(config['schemaVersion'] == 'SmallAppExecutionServiceConfig/v2',
             'SINGLE_OPERATOR_CONFIGURATION_REQUIRED')
        ledger, registry = (directory(config[key], config['taskRoot']) for key in ('ledgerRoot', 'registryRoot'))
        need(ledger != registry and ledger not in registry.parents and registry not in ledger.parents,
             'SERVER_ROOTS_INVALID')
        for lane in ('applications', 'points'):
            directory(registry / lane, config['taskRoot'])
        opaque(config['engineSelectionRef'])
        need(type(config['deadlineMilliseconds']) is int and
             0 < config['deadlineMilliseconds'] <= 28800000, 'ORIGINAL_DEADLINE_REQUIRED')
        need(type(config['programPins']) is dict and set(config['programPins']) <= {'repository', 'recovery'} and
             'repository' in config['programPins'], 'COMMON_OWNER_PROGRAMS_REQUIRED')
        need(type(config['sourceConfigurations']) is dict and config['sourceConfigurations'] and
             type(config['restoreConfigurations']) is dict, 'OWNER_CONFIGURATIONS_REQUIRED')
        need(type(config['environment']) is dict and config['environment'] and
             all(type(k) is str and type(v) is str and k and '=' not in k and '\x00' not in k + v
                 for k, v in config['environment'].items()), 'NATIVE_ENVIRONMENT_REQUIRED')
        need(Path(config['workingDirectory']).is_absolute() and Path(config['workingDirectory']).is_dir(),
             'EXECUTION_WORKING_DIRECTORY_REQUIRED')
        executor.verify(config['pythonPin'])
        return config

    def selector(self, root, reference):
        pin = local_read(Path(root) / (opaque(reference) + '.pin.json'))
        executor.pin_reference(pin)
        executor.verify(pin)
        return pin

    def registration(self, config_ref):
        config = self.configuration()
        matches = [item for item in self.registrations(config) if item['sourceConfigRef'] == config_ref]
        need(len(matches) == 1, 'SOURCE_NOT_REGISTERED')
        registered = matches[0]
        selected = self.selector(Path(config['registryRoot']) / 'applications', registered['applicationId'])
        return registered, selected

    def registration_metadata(self, value):
        need(type(value) is dict and value.get('schemaVersion') == 'ApplicationRegistration/v1',
             'REGISTRATION_VERSION_INVALID')
        opaque(value['applicationId'])
        if value['sourceConfigRef'] is not None:
            opaque(value['sourceConfigRef'])
        need(type(value['allowedRestoreTargets']) is list, 'REGISTRATION_TARGETS_INVALID')
        # Existing W08 metadata remains the display/source catalogue. Resource
        # proof fields and signatures are not single-operator prerequisites.
        return value

    def registrations(self, config):
        values = []
        for path in sorted((Path(config['registryRoot']) / 'applications').glob('*.pin.json')):
            reference = opaque(path.name[:-9])
            value = self.registration_metadata(self.document(self.selector(path.parent, reference)))
            need(value['applicationId'] == reference, 'REGISTRATION_APPLICATION_ID_MISMATCH')
            values.append(value)
        refs = [value['sourceConfigRef'] for value in values if value['sourceConfigRef'] is not None]
        need(len(refs) == len(set(refs)), 'REGISTERED_SOURCE_AMBIGUOUS')
        return values

    def point(self, config, reference, source_ref):
        binding_pin = self.selector(Path(config['registryRoot']) / 'points', reference)
        from recovery_control_point_quarantine import quarantined
        need(not quarantined(self, config, reference, source_ref, binding_pin), 'POINT_QUARANTINED')
        point = self.document(binding_pin)
        exact(point, 'schemaVersion reference sourceConfigRef resultPin', 'POINT_BINDING_FIELDS_INVALID')
        need(point['schemaVersion'] == 'SmallAppPointBinding/v2' and point['reference'] == reference and
             point['sourceConfigRef'] == source_ref, 'POINT_SOURCE_MISMATCH')
        output = self.document(point['resultPin'])
        need(output['operationId'] == reference and output['requestId'] == reference and
             output['action'] in ('FULL', 'INCREMENTAL') and output['state'] == 'SUCCEEDED' and
             type(output['actualExitCode']) is int and output['actualExitCode'] == 0,
             'POINT_ORIGINAL_RESULT_INVALID')
        for pin in output['originalResultPins']:
            executor.verify(pin)
        return binding_pin

    def resolve(self, value):
        request(value)
        config = self.configuration()
        registered, registration_pin = self.registration(value['sourceConfigRef'])
        need(value['sourceConfigRef'] in config['sourceConfigurations'], 'SOURCE_CONFIGURATION_REQUIRED')
        owner_configuration = config['sourceConfigurations'][value['sourceConfigRef']]
        program = 'repository'
        point_pin = None
        reference = value['parentChainRef'] if value['action'] == 'INCREMENTAL' else value['recoveryPointRef']
        if reference is not None:
            point_pin = self.point(config, reference, value['sourceConfigRef'])
        if value['action'] == 'RESTORE':
            matches = [target for target in registered['allowedRestoreTargets']
                       if target['configRef'] == value['targetConfigRef']]
            need(len(matches) == 1, 'TARGET_NOT_REGISTERED_FOR_SOURCE')
            targets = config['restoreConfigurations'].get(value['sourceConfigRef'])
            need(type(targets) is dict and value['targetConfigRef'] in targets, 'NEW_TARGET_CONFIGURATION_REQUIRED')
            owner_configuration = targets[value['targetConfigRef']]
            need(owner_configuration != config['sourceConfigurations'][value['sourceConfigRef']],
                 'RESTORE_REUSES_SOURCE_CONFIGURATION')
            program = 'recovery'
        need(program in config['programPins'], 'ORIGINAL_OWNER_PROGRAM_REQUIRED')
        executor.verify(config['programPins'][program])
        # Owner configuration is interpreted by the real owner CLI, not by a
        # parallel W01 capture/restore implementation. FULL resolves no target.
        self.document(owner_configuration)
        if value['action'] in ('FULL', 'INCREMENTAL'):
            from recovery_control_capture_config import for_request
            owner_configuration = for_request(self, config, value, owner_configuration, point_pin)
        return dict(schemaVersion='SmallAppResolvedSelection/v2', configurationPin=self.config_pin,
            registrationPin=registration_pin, ownerConfigurationPin=owner_configuration,
            ownerProgramPin=config['programPins'][program], pointBindingPin=point_pin)

    def execute(self, value, operation_directory, selection):
        dispatch = {'started': False}
        try:
            self._execute(value, operation_directory, selection, dispatch)
        except Exception as error:
            error.dispatch_started = dispatch['started']
            raise

    def _execute(self, value, operation_directory, selection, dispatch):
        config = self.configuration()
        need(self.resolve(value) == selection, 'CURRENT_SELECTION_CHANGED')
        argv = [config['pythonPin']['path'], '-B', str(Path(__file__).with_name('recovery_control_smallapp.py')),
                'worker', '--config-pin', canonical(self.config_pin).decode(), '--operation-id', value['operationId']]
        with (operation_directory / 'worker-stdout').open('xb') as stdout, \
                (operation_directory / 'worker-stderr').open('xb') as stderr:
            if os.name == 'posix':
                os.chmod(stdout.name, 0o600); os.chmod(stderr.name, 0o600)
            process = subprocess.Popen(argv, cwd=config['workingDirectory'], env=config['environment'],
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            dispatch['started'] = True
            persist(operation_directory / 'worker-process.json', dict(operationId=value['operationId'],
                uiRequestSha256=fingerprint(value), pid=process.pid, argv=argv))
            deadline = time.monotonic() + config['deadlineMilliseconds'] / 1000
            while True:
                try:
                    code = process.wait(timeout=.2)
                    break
                except subprocess.TimeoutExpired:
                    timeout = operation_directory / 'timeout-observation.json'
                    if time.monotonic() >= deadline and not timeout.exists():
                        persist(timeout, dict(operationId=value['operationId'], originalOperationOnly=True, retryAllowed=False))
        persist(operation_directory / 'worker-terminal.json', dict(operationId=value['operationId'],
            uiRequestSha256=fingerprint(value), actualExitCode=code, pid=process.pid,
            stdoutPin=executor.pin(operation_directory / 'worker-stdout'),
            stderrPin=executor.pin(operation_directory / 'worker-stderr')))

    def owner_result(self, value, terminal):
        if terminal['resultPin'] is None:
            return result(value, 'RUNNING' if terminal['actualExitCode'] == 0 else 'FAILED', 'OWNER_RESULT_MISSING')
        output = self.operation_output(value, terminal['resultPin'])
        if output['state'] == 'SUCCEEDED' and terminal['actualExitCode'] != 0:
            return result(value, 'FAILED', output['failureCode'] or 'ORIGINAL_EXECUTOR_FAILED')
        return self.operation_result(value, output)

    def operation_output(self, value, reference):
        output = self.document(reference)
        exact(output, 'schemaVersion operationId requestId action state failureCode message data originalResultPins '
              'startedAt finishedAt actualExitCode', 'ORIGINAL_RESULT_FIELDS_INVALID')
        need(output['schemaVersion'] == 'backup-restore-operation-result/v1' and
             output['operationId'] == output['requestId'] == value['operationId'] and
             output['action'] == value['action'] and
             output['state'] in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN'),
             'ORIGINAL_RESULT_BINDING_INVALID')
        error = output['failureCode']
        need(error is None or type(error) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}', error),
             'ORIGINAL_ERROR_CODE_INVALID')
        need(type(output['originalResultPins']) is list, 'ORIGINAL_RESULT_PINS_REQUIRED')
        need(output['actualExitCode'] is None or type(output['actualExitCode']) is int,
             'ORIGINAL_ACTUAL_EXIT_INVALID')
        for pin in output['originalResultPins']:
            executor.verify(pin)
        return output

    def operation_result(self, value, output):
        error = output['failureCode']
        if output['state'] == 'TERMINAL_UNKNOWN':
            return result(value, 'RUNNING', error or 'ORIGINAL_TERMINAL_UNRESOLVED')
        if output['state'] != 'SUCCEEDED':
            return result(value, 'FAILED', error or 'ORIGINAL_EXECUTOR_FAILED')
        need(type(output['actualExitCode']) is int and output['actualExitCode'] == 0 and
             type(output['data']) is dict and output['data'] and output['originalResultPins'] and error is None,
             'ORIGINAL_SUCCESS_INCOMPLETE')
        return result(value, 'SUCCEEDED')

    def publish_point(self, value, operation_directory, result_pin, config):
        if value['action'] == 'RESTORE':
            return
        binding_path = operation_directory / 'point-binding.json'
        binding = dict(schemaVersion='SmallAppPointBinding/v2', reference=value['operationId'],
            sourceConfigRef=value['sourceConfigRef'], resultPin=result_pin)
        for path, document in ((binding_path, binding),
                (Path(config['registryRoot']) / 'points' / (value['operationId'] + '.pin.json'), None)):
            if document is None:
                document = executor.pin(binding_path)
            try:
                persist(path, document)
            except FileExistsError:
                need(local_read(path) == document, 'POINT_PUBLICATION_CHANGED')

    @staticmethod
    def repository_journal(root, name):
        """W03 writes canonical request/start with the process umask, usually 0644."""
        path = root / name
        need(name in ('request.json', 'start.json') and root.is_absolute() and
             path.resolve() == path, 'ORIGINAL_OWNER_JOURNAL_PATH_INVALID')
        directories = [(item, item.lstat()) for item in (root.parent, root)]
        directory_key = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)
        for item, info in directories:
            need(item.resolve() == item and stat.S_ISDIR(info.st_mode), 'ORIGINAL_OWNER_DIRECTORY_INVALID')
            if os.name == 'posix':
                need(info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022,
                     'ORIGINAL_OWNER_DIRECTORY_CUSTODY_INVALID')
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
        initial = path.lstat()
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 1048576,
                 'ORIGINAL_OWNER_JOURNAL_FILE_INVALID')
            if os.name == 'posix':
                need(before.st_uid == before.st_gid == 0 and not before.st_mode & 0o022,
                     'ORIGINAL_OWNER_JOURNAL_CUSTODY_INVALID')
            raw = stream.read(1048577)
            after = os.fstat(stream.fileno())
        key = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                            info.st_nlink, info.st_size, info.st_mtime_ns)
        current = path.lstat()
        need(key(initial) == key(before) == key(after) == key(current) and
             initial.st_ctime_ns == current.st_ctime_ns and before.st_ctime_ns == after.st_ctime_ns and
             len(raw) == before.st_size and path.resolve() == path and
             all(directory_key(info) == directory_key(item.lstat()) for item, info in directories),
             'ORIGINAL_OWNER_JOURNAL_CHANGED')
        return decode(raw)

    def accepted_operation(self, value, selection):
        config = self.document(selection['ownerConfigurationPin'])
        if value['action'] == 'RESTORE':
            need(config['schemaVersion'] == 'RecoveryMinimalConfiguration/v1', 'ORIGINAL_OWNER_CONFIGURATION_INVALID')
            root = Path(config['operationsRoot']) / value['operationId']
            admission_name = 'operation.json'
            read_journal = local_read
        else:
            need(config['schemaVersion'] == 'RepositoryMinimumConfiguration/v1', 'ORIGINAL_OWNER_CONFIGURATION_INVALID')
            root = Path(config['operationRoot']) / hashlib.sha256(value['operationId'].encode()).hexdigest()
            admission_name = 'start.json'
            read_journal = lambda path: self.repository_journal(root, path.name)
        need(root.is_absolute() and root.resolve() == root and root.is_dir(), 'ORIGINAL_OWNER_ADMISSION_NOT_FOUND')
        need((root / 'request.json').is_file() and (root / admission_name).is_file(),
             'ORIGINAL_OWNER_ADMISSION_INCOMPLETE')
        need(read_journal(root / 'request.json') == value, 'ORIGINAL_OWNER_REQUEST_CHANGED')
        admission = read_journal(root / admission_name)
        if value['action'] == 'RESTORE':
            need(admission['operationId'] == value['operationId'] and
                 admission['requestPin'] == executor.pin(root / 'request.json') and
                 admission['configurationSha256'] == fingerprint(config), 'ORIGINAL_OWNER_ADMISSION_CHANGED')
        else:
            need(admission['configurationPin'] == selection['ownerConfigurationPin'] and
                 admission['requestSha256'] == fingerprint(value) and admission['readbackOnly'] is False,
                 'ORIGINAL_OWNER_ADMISSION_CHANGED')
        return root

    def stopped_sql_target(self, value, selection):
        """A disconnected import client alone cannot prove the remote writer stopped."""
        configuration = self.document(selection['ownerConfigurationPin'])
        target = configuration['targets'][value['targetConfigRef']]
        executor.verify(target['dockerPin'])
        services = [row for row in target['services'] if row['role'] == 'mysql']
        need(len(services) == 1, 'ORIGINAL_IMPORT_TARGET_NOT_UNIQUE')
        expected = services[0]
        observed = subprocess.run([target['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock',
            'inspect', expected['id']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
        need(observed.returncode == 0 and not observed.stderr, 'ORIGINAL_IMPORT_TARGET_OBSERVATION_FAILED')
        rows = decode(observed.stdout)
        need(type(rows) is list and len(rows) == 1, 'ORIGINAL_IMPORT_TARGET_OBSERVATION_FAILED')
        row = rows[0]
        need(row['Id'] == expected['id'] and row['Image'] == expected['imageId'] and
             row['Config']['Labels'].get('intruoyi.recovery.target') == target['targetId'] and
             not row['ExecIDs'] and row['State']['Running'] is False and row['State']['Pid'] == 0 and
             row['State']['Paused'] is False and row['State']['Restarting'] is False,
             'ORIGINAL_IMPORT_REMOTE_WRITER_UNRESOLVED')

    def restore_timeout_stopped(self, value, operation_directory, selection, root, output):
        """Resolve only a killed owner with completed writes and no live native call."""
        exited = self.document(executor.pin(operation_directory / 'execute' / 'native-original-exit.json'))
        child = self.document(executor.pin(root / 'child-exit.json'))
        need(exited['operationId'] == exited['requestId'] == value['operationId'] and
             exited['requestPin'] == executor.pin(operation_directory / 'request.json') and
             exited['actualExitCode'] == 2 and child['timedOut'] is True and
             child['actualExitCode'] == output['actualExitCode'] == -9,
             'ORIGINAL_TIMEOUT_EXIT_NOT_PROVEN')
        calls = [self.document(executor.pin(p)) for p in root.rglob('native-*.json')]
        need(calls and all(row['schemaVersion'] == 'RecoveryDataInvocation/v1' and
             row['operationId'] == value['operationId'] and
             (row['actualExitCode'] == 0 and row['finishedAt'] or
              row['actualExitCode'] is None and row['mutation'] is False) for row in calls),
             'ORIGINAL_TIMEOUT_WRITER_UNRESOLVED')
        importers = [self.document(executor.pin(p)) for p in root.rglob('importer-*.json')]
        need(all(row['schemaVersion'] == 'RecoverySqlImporter/v1' and row['actualExitCode'] == 0 and
                 row['finishedAt'] for row in importers), 'ORIGINAL_TIMEOUT_IMPORTER_UNRESOLVED')
        # Native commands have separate sessions: inspect actual argv, not operationId.
        hashes = {row['argvSha256'] for row in calls if row['actualExitCode'] is None}
        need(os.name == 'posix' and Path('/proc').is_dir(), 'ORIGINAL_PROCESS_OBSERVATION_UNAVAILABLE')
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                raw = path.read_bytes()
            except FileNotFoundError:
                continue
            need(not raw or fingerprint([os.fsdecode(part) for part in raw.rstrip(b'\0').split(b'\0')])
                 not in hashes, 'ORIGINAL_NATIVE_CALL_STILL_RUNNING')
        configuration = self.document(selection['ownerConfigurationPin'])
        target = configuration['targets'][value['targetConfigRef']]
        executor.verify(target['dockerPin'])
        services = {row['id']: row for row in target['services']}
        observed = subprocess.run([target['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock',
            'inspect', *services], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
        need(observed.returncode == 0 and not observed.stderr, 'ORIGINAL_TARGET_OBSERVATION_FAILED')
        rows = decode(observed.stdout)
        need(type(rows) is list and {row['Id'] for row in rows} == set(services),
             'ORIGINAL_TARGET_OBSERVATION_FAILED')
        for row in rows:
            expected = services[row['Id']]
            need(row['Image'] == expected['imageId'] and
                 row['Config']['Labels'].get('intruoyi.recovery.target') == target['targetId'] and
                 not row['ExecIDs'] and not row['State']['Paused'] and not row['State']['Restarting'] and
                 (expected['role'] in ('mysql', 'redis') or
                  not row['State']['Running'] and row['State']['Pid'] == 0),
                 'ORIGINAL_TARGET_WRITER_UNRESOLVED')

    def stopped_capture_failure(self, value, selection, root, output):
        """Resolve an owner wait timeout only after a failed capture restored its source."""
        owner = self.document(selection['ownerConfigurationPin'])
        source = owner['sources'][value['sourceConfigRef']]
        capture_root = Path(source['stagingRoot']) / value['operationId']
        capture_pin = executor.pin(capture_root / 'terminal-result.json')
        capture = self.operation_output(value, capture_pin)
        binding_pin = executor.pin(capture_root / 'operation.json')
        binding = self.document(binding_pin)
        need(capture['state'] == 'FAILED_RETAINED' and capture['actualExitCode'] == 1 and
             capture['failureCode'] is not None and binding['request'] == value and
             binding['configurationPin'] == executor.pin(source['configurationPath']) and
             binding['requestPin'] in capture['originalResultPins'] and
             self.document(binding['requestPin']) == value, 'ORIGINAL_CAPTURE_FAILURE_NOT_PROVEN')
        restored_pin = capture['data']['sourceRestorationPin']
        need(restored_pin == executor.pin(capture_root / 'source-restoration.json'),
             'ORIGINAL_SOURCE_RESTORATION_CHANGED')
        restored = self.document(restored_pin)
        need(restored['restored'] is True and restored['errors'] == [], 'ORIGINAL_SOURCE_NOT_RESTORED')
        need(not (capture_root / 'worker-completion.json').exists() and
             not (capture_root / 'capture-recovery-inputs.json').exists() and
             all(p.name in ('request.json', 'start.json', 'result.json', 'capture.stdout.log', 'capture.stderr.log') or
                 p.name.startswith(('capture-', 'worker')) for p in root.iterdir()),
             'ORIGINAL_ARCHIVE_DISPATCH_UNRESOLVED')
        observations = list(root.glob('*-process.json')) + [capture_root / name
            for name in ('worker-started.json', 'job-started.json')]
        need(observations, 'ORIGINAL_PROCESS_OBSERVATION_UNAVAILABLE')
        for path in observations:
            row = self.document(executor.pin(path))
            need(type(row['pid']) is int and row['pid'] > 0, 'ORIGINAL_PROCESS_OBSERVATION_INVALID')
            command = Path('/proc') / str(row['pid']) / 'cmdline'
            if command.exists():
                args = command.read_bytes().split(b'\0')
                need(not any(str(scope).encode() in arg for scope in (root, capture_root) for arg in args),
                     'ORIGINAL_CAPTURE_STILL_RUNNING')
        return capture['failureCode'], [capture_pin, binding_pin, restored_pin]

    def refresh_original(self, value, operation_directory, selection):
        reference, output = None, None
        resolution_pins = []
        try:
            original_intent = self.document(executor.pin(operation_directory / 'execute' / 'native-intent.json'))
            need(original_intent['operationId'] == original_intent['requestId'] == value['operationId'] and
                 original_intent['requestPin'] == executor.pin(operation_directory / 'request.json') and
                 original_intent['configurationPin'] == selection['ownerConfigurationPin'] and
                 original_intent['programPin'] == selection['ownerProgramPin'], 'ORIGINAL_OWNER_INTENT_CHANGED')
            root = self.accepted_operation(value, selection)
            need((root / 'result.json').is_file(), 'ORIGINAL_OWNER_RESULT_NOT_READY')
            reference = executor.pin(root / 'result.json')
            output = self.operation_output(value, reference)
            reply = self.operation_result(value, output)
            if (value['action'] != 'RESTORE' and output['state'] == 'TERMINAL_UNKNOWN' and
                    output['failureCode'] == 'REPOSITORY_CHILD_TIMEOUT_QUERY_ORIGINAL_OPERATION'):
                code, resolution_pins = self.stopped_capture_failure(value, selection, root, output)
                reply = result(value, 'FAILED', code)
            if (value['action'] == 'RESTORE' and output['state'] == 'TERMINAL_UNKNOWN' and
                    output['failureCode'] in ('FORMAL_SQL_IMPORT_FAILED', 'FORMAL_SQL_IMPORT_STREAM_FAILED')):
                # Partial SQL effects remain unknown and the target stays reserved.
                # A recorded importer exit plus the owner OS exit does, however,
                # prove this operation has failed rather than still executing.
                exited = self.document(executor.pin(operation_directory / 'execute' / 'native-original-exit.json'))
                importers = [self.document(ref) for ref in output['originalResultPins']
                    if re.fullmatch(r'importer-[0-9]+\.json', Path(ref['path']).name)]
                need(exited['operationId'] == exited['requestId'] == value['operationId'] and
                     exited['requestPin'] == executor.pin(operation_directory / 'request.json') and
                     exited['actualExitCode'] == output['actualExitCode'] == 2 and importers and
                     importers[-1].get('schemaVersion') == 'RecoverySqlImporter/v1' and
                     type(importers[-1].get('actualExitCode')) is int and
                     importers[-1]['actualExitCode'] > 0 and
                     importers[-1]['actualExitCode'] not in (124, 137, 143) and importers[-1].get('finishedAt') and
                     output['data']['actualNativeExitCode'] == importers[-1]['actualExitCode'] and
                     output['data']['partialTargetRetained'] is True and output['data']['retryPermitted'] is False,
                     'ORIGINAL_IMPORT_FAILURE_EXIT_NOT_PROVEN')
                if output['failureCode'] == 'FORMAL_SQL_IMPORT_STREAM_FAILED':
                    self.stopped_sql_target(value, selection)
                reply = result(value, 'FAILED', output['failureCode'])
            if (value['action'] == 'RESTORE' and output['state'] == 'TERMINAL_UNKNOWN' and
                    output['failureCode'] == 'ORIGINAL_CHILD_TIMEOUT'):
                self.restore_timeout_stopped(value, operation_directory, selection, root, output)
                reply = result(value, 'FAILED', output['failureCode'])
            if reply['state'] == 'SUCCEEDED':
                def inspect(item):
                    if type(item) is dict:
                        if set(item) == {'path', 'bytes', 'sha256'}:
                            executor.verify(item)
                            return 1
                        return sum(inspect(child) for child in item.values())
                    if type(item) is list:
                        return sum(inspect(child) for child in item)
                    return 0
                need(inspect(output['data']) > 0, 'ORIGINAL_SUCCESS_MATERIAL_MISSING')
                self.publish_point(value, operation_directory, reference, self.document(selection['configurationPin']))
        except Exception as error:
            reply = result(value, 'RUNNING', public_error(error))
        observations = operation_directory / 'queries'
        observations.mkdir(mode=0o700, exist_ok=True)
        persist(observations / (uuid.uuid4().hex + '.json'), dict(operationId=value['operationId'],
            requestSha256=fingerprint(value), ownerResultPin=reference,
            resolutionPins=resolution_pins,
            ownerActualExitCode=None if output is None else output['actualExitCode'], result=reply,
            observedAt=datetime.now(timezone.utc).isoformat()))
        return reply

    def worker(self, operation):
        config = self.configuration()
        operation_directory = Path(config['ledgerRoot']) / opaque(operation)
        value = request(local_read(operation_directory / 'request.json'))
        selection = local_read(operation_directory / 'selection.json')
        terminal = None
        try:
            need(value['operationId'] == operation and self.resolve(value) == selection, 'CURRENT_SELECTION_CHANGED')
            root = operation_directory / 'execute'
            root.mkdir(mode=0o700)
            # Pass the existing seven UI fields unchanged to the owner adapter.
            terminal = executor.run_owner(config['pythonPin'], selection['ownerProgramPin'],
                selection['ownerConfigurationPin'], executor.pin(operation_directory / 'request.json'),
                root / 'result.json', environment=config['environment'],
                working_directory=config['workingDirectory'], deadline_milliseconds=config['deadlineMilliseconds'])
            reply = self.owner_result(value, terminal)
            if reply['state'] == 'SUCCEEDED':
                # The archive adapter returns success only after independent
                # material/hash readback. Logical point references are original
                # operation IDs; the owner resolves its actual archived material.
                self.publish_point(value, operation_directory, terminal['resultPin'], config)
        except Exception as error:
            uncertain = getattr(error, 'owner_dispatched', False) or (
                terminal is not None and terminal['actualExitCode'] == 0)
            reply = result(value, 'RUNNING' if uncertain else 'FAILED',
                           public_error(error))
        reply['logRefs'] = [operation + '-originals']
        reply['resultRef'] = operation + '-result'
        persist(operation_directory / 'completion.json', dict(operationId=operation,
            uiRequestSha256=fingerprint(value), selection=selection, result=reply, terminal=terminal,
            actualResultPath=str(operation_directory / 'execute' / 'result.json'),
            originalLogRoot=str(operation_directory)))
        return {'SUCCEEDED': 0, 'FAILED': 1, 'RUNNING': 2}[reply['state']]

    def reconcile(self, value, operation_directory, selection):
        terminal_path = operation_directory / 'worker-terminal.json'
        terminal = local_read(terminal_path) if terminal_path.is_file() else None
        if terminal is not None:
            need(terminal['operationId'] == value['operationId'] and
                 terminal['uiRequestSha256'] == fingerprint(value) and type(terminal['actualExitCode']) is int,
                 'ORIGINAL_WORKER_BINDING_INVALID')
        completion_path = operation_directory / 'completion.json'
        if not completion_path.is_file():
            if terminal is None and not (operation_directory / 'execute' / 'native-original-exit.json').is_file():
                return None
            if (operation_directory / 'execute' / 'native-intent.json').is_file():
                return self.refresh_original(value, operation_directory, selection)
            reply = result(value, 'FAILED', 'WORKER_FAILED_WITHOUT_RESULT')
            reply.update(logRefs=[value['operationId'] + '-originals'], resultRef=value['operationId'] + '-result')
            return reply
        completion = local_read(completion_path)
        need(completion['operationId'] == value['operationId'] and
             completion['uiRequestSha256'] == fingerprint(value) and completion['selection'] == selection,
             'ORIGINAL_RESULT_BINDING_INVALID')
        reply = completion['result']
        need(reply['state'] in ('RUNNING', 'SUCCEEDED', 'FAILED') and
             (reply['state'] != 'SUCCEEDED' or terminal is None or terminal['actualExitCode'] == 0),
             'ORIGINAL_EXIT_MISMATCH')
        owner_terminal = completion['terminal']
        if owner_terminal is not None:
            # The HTTP service may have restarted while its worker was running.
            # The worker owns the actual owner-child wait/exit and writes these
            # originals independently of the HTTP supervisor's lifetime.
            original = local_read(operation_directory / 'execute' / 'native-original-exit.json')
            need(original == owner_terminal and original['operationId'] == original['requestId'] == value['operationId'] and
                 original['requestPin'] == executor.pin(operation_directory / 'request.json') and
                 type(original['actualExitCode']) is int, 'ORIGINAL_OWNER_EXIT_INVALID')
            for key in ('stdoutPin', 'stderrPin'):
                executor.verify(original[key])
            if original['resultPin'] is not None:
                executor.verify(original['resultPin'])
            if reply['state'] == 'SUCCEEDED':
                need(self.owner_result(value, original) == reply, 'ORIGINAL_RESULT_CHANGED')
        else:
            need(reply['state'] != 'SUCCEEDED', 'ORIGINAL_SUCCESS_EXIT_MISSING')
        if reply['state'] == 'RUNNING' and (operation_directory / 'execute' / 'native-intent.json').is_file():
            return self.refresh_original(value, operation_directory, selection)
        return reply

    def import_registration(self, registration_pin, expected_pin=None):
        from recovery_control_registration import publish_registration
        import fcntl
        config = self.configuration()
        value = self.registration_metadata(self.document(registration_pin))
        root = Path(config['registryRoot']) / 'applications'
        fd = os.open(root / 'import.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            need(not any(item['applicationId'] != value['applicationId'] and value['sourceConfigRef'] is not None and
                item['sourceConfigRef'] == value['sourceConfigRef'] for item in self.registrations(config)),
                'REGISTERED_SOURCE_AMBIGUOUS')
            publish_registration(root / (value['applicationId'] + '.pin.json'), registration_pin, expected_pin)
        finally:
            os.close(fd)
        return dict(applicationId=value['applicationId'], metadataImported=True)

    def selections(self):
        from recovery_control_registration import blocked_choice
        config = self.configuration()
        rows = []
        for registered in self.registrations(config):
            source_ref = registered['sourceConfigRef']
            if source_ref is None:
                continue
            row = blocked_choice(registered, 'SOURCE_CONFIGURATION_REQUIRED')
            row['historyErrorCode'] = None
            try:
                need(source_ref in config['sourceConfigurations'], 'SOURCE_CONFIGURATION_REQUIRED')
                self.document(config['sourceConfigurations'][source_ref])
                executor.verify(config['programPins']['repository'])
                row.update(fullReady=True, fullErrorCode=None, engineSelectionRef=config['engineSelectionRef'])
            except Exception as error:
                row['fullErrorCode'] = public_error(error)
                rows.append(row)
                continue
            try:
                references = []
                for path in sorted((Path(config['registryRoot']) / 'points').glob('*.pin.json')):
                    reference = path.name[:-9]
                    candidate = self.document(self.selector(path.parent, reference))
                    if candidate.get('sourceConfigRef') != source_ref:
                        continue
                    from recovery_control_point_quarantine import quarantined
                    if quarantined(self, config, reference, source_ref, self.selector(path.parent, reference)):
                        continue
                    self.point(config, reference, source_ref)
                    references.append(reference)
                need(len(references) <= 1000, 'HISTORY_REFERENCE_LIMIT_EXCEEDED')
                row['parentChainRefs'] = list(references)
                row['recoveryPointRefs'] = references
            except Exception as error:
                # A failed historical read blocks chain selection, not a new
                # FULL. Surface the real failure instead of implying no history.
                row['historyErrorCode'] = public_error(error)
            targets = config['restoreConfigurations'].get(source_ref, {})
            from recovery_control_target_availability import available
            row['freshTargetConfigRefs'] = [target['configRef'] for target in registered['allowedRestoreTargets']
                if type(targets) is dict and target['configRef'] in targets and
                available(self, targets[target['configRef']], target['configRef'], source_ref)]
            rows.append(row)
        return dict(observedAt=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), applications=rows)
