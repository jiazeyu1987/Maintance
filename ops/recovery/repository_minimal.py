"""Single-operator capture/archive/readback, using the existing byte engine.

This is the explicitly selected primary path. It does not load the legacy
service configuration, signed context, grant, lease, custodian or approval chain.
The source adapter must really capture the application; this module only streams
its complete, hashed capture outputs and independently reads them back via SMB.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

from repository_records import (Deadline, RepositoryError, absolute, atomic_output,
    atomic_output_bytes, canonical, document, exact, pin_file, read_pin, require, safe_path, timestamp,
    utc, validate_pin, write_new)
from repository_binding import assemble_readback_bindings, repository_binding
from repository_catalog import Catalog
from repository_native_archive_reader import LabBackupArchiveReader
from repository_native_publisher import Publisher
from repository_native_readback import SmbReadback

REQUEST_FIELDS = 'schemaVersion operationId action sourceConfigRef parentChainRef recoveryPointRef targetConfigRef'


def request_document(path):
    value = document(read_pin(pin_file(path)))
    exact(value, REQUEST_FIELDS, 'SmallAppBackupUiRequest/v1')
    require(type(value['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', value['operationId']) and
        value['action'] in ('FULL', 'INCREMENTAL', 'RESTORE') and
        type(value['sourceConfigRef']) is str and value['sourceConfigRef'], 'REPOSITORY_MINIMUM_REQUEST_INVALID')
    for key in ('parentChainRef', 'recoveryPointRef', 'targetConfigRef'):
        require(value[key] is None or (type(value[key]) is str and value[key]),
            'REPOSITORY_MINIMUM_REFERENCE_INVALID')
    if value['action'] == 'FULL':
        require(all(value[k] is None for k in ('parentChainRef', 'recoveryPointRef', 'targetConfigRef')),
            'REPOSITORY_FULL_REFERENCES_FORBIDDEN')
    elif value['action'] == 'INCREMENTAL':
        require(value['parentChainRef'] is not None and value['recoveryPointRef'] is None and
            value['targetConfigRef'] is None, 'REPOSITORY_INCREMENTAL_PARENT_REQUIRED')
    else:
        require(value['recoveryPointRef'] is not None and value['targetConfigRef'] is not None and
            value['parentChainRef'] is None, 'REPOSITORY_RESTORE_REFERENCES_REQUIRED')
    return value


class MinimumConfiguration:
    def __init__(self, path, request):
        self.pin = pin_file(path)
        self.value = document(read_pin(self.pin))
        exact(self.value, 'schemaVersion repositoryId repositoryRoot operationRoot timeoutMilliseconds '
            'responseTimeoutMilliseconds maxChainPoints maxChainAgeSeconds captureBinderPath sources '
            'parentChains recoveryPoints readback maximumArchiveBytes minimumFreeBytes', 'RepositoryMinimumConfiguration/v1')
        require(type(self.value['repositoryId']) is str and self.value['repositoryId'], 'REPOSITORY_ID_REQUIRED')
        self.root = safe_path(self.value['repositoryRoot'])
        self.evidence = safe_path(self.value['operationRoot'])
        self.archives = safe_path(self.root / 'archives')
        require(self.root.is_dir() and self.evidence.is_dir() and self.archives.is_dir() and
            not overlap(self.root, self.evidence), 'REPOSITORY_MINIMUM_ROOTS_INVALID')
        require(type(self.value['sources']) is dict and request['sourceConfigRef'] in self.value['sources'],
            'REPOSITORY_SOURCE_NOT_CONFIGURED')
        self.source = self.value['sources'][request['sourceConfigRef']]
        require(type(self.source) is dict and set(self.source) == {'captureCommand', 'configurationPath',
            'stagingRoot', 'sourceIdentityPath', 'toolPaths'}, 'REPOSITORY_MINIMUM_SOURCE_INVALID')
        self.staging = safe_path(self.source['stagingRoot'])
        require(self.staging.is_dir() and not overlap(self.staging, self.root) and
            not overlap(self.staging, self.evidence), 'REPOSITORY_STAGING_OVERLAP')
        self.identity_pin = pin_file(self.source['sourceIdentityPath'])
        identity = document(read_pin(self.identity_pin))
        require(type(identity.get('sourceFingerprint')) is str and identity['sourceFingerprint'] and
            type(identity.get('databaseUuid')) is str and identity['databaseUuid'],
            'REPOSITORY_SOURCE_IDENTITY_INVALID')
        require(type(self.source['captureCommand']) is list and self.source['captureCommand'] and
            all(type(x) is str and x for x in self.source['captureCommand']) and
            type(self.source['toolPaths']) is list and self.source['toolPaths'], 'REPOSITORY_MINIMUM_COMMAND_INVALID')
        Deadline(self.value['timeoutMilliseconds'])
        require(type(self.value['responseTimeoutMilliseconds']) is int and
            0 < self.value['responseTimeoutMilliseconds'] <= self.value['timeoutMilliseconds'] and
            type(self.value['maxChainPoints']) is int and 1 <= self.value['maxChainPoints'] <= 1024 and
            type(self.value['maxChainAgeSeconds']) is int and self.value['maxChainAgeSeconds'] > 0,
            'REPOSITORY_MINIMUM_BUDGET_INVALID')
        require(all(type(self.value[k]) is int and self.value[k] > 0 for k in ('maximumArchiveBytes', 'minimumFreeBytes')),
            'REPOSITORY_ARCHIVE_CAPACITY_BUDGET_REQUIRED')
        for key in ('parentChains', 'recoveryPoints'):
            require(type(self.value[key]) is dict, 'REPOSITORY_POINT_REGISTRY_INVALID')
        self.root_identities = {p: self.directory_identity(p) for p in
            (self.root, self.archives, self.evidence, self.staging)}

    @staticmethod
    def directory_identity(path):
        info = safe_path(path).stat()
        return info.st_dev, info.st_ino, info.st_mode

    def current(self):
        read_pin(self.pin)
        read_pin(self.identity_pin)
        require(safe_path(self.value['repositoryRoot']) == self.root and
            safe_path(self.value['operationRoot']) == self.evidence and
            safe_path(self.source['stagingRoot']) == self.staging, 'REPOSITORY_MINIMUM_ROOT_CHANGED')
        require(all(self.directory_identity(p) == value for p, value in self.root_identities.items()),
            'REPOSITORY_MINIMUM_ROOT_IDENTITY_CHANGED')


def overlap(left, right):
    return left == right or left in right.parents or right in left.parents


def failure_code(error):
    code = getattr(error, 'code', None)
    return code if type(code) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,150}', code) else 'REPOSITORY_' + type(error).__name__.upper()


def load_binder(path):
    """Select W02's installed real assembly function, without a proof graph."""
    path = safe_path(path)
    spec = importlib.util.spec_from_file_location('repository_minimum_w02_binder', path)
    require(spec is not None and spec.loader is not None, 'REPOSITORY_CAPTURE_BINDER_REQUIRED')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    binder = getattr(module, 'assemble_repository_capture_records', None)
    require(callable(binder), 'REPOSITORY_CAPTURE_BINDER_REQUIRED')
    return binder


class MinimumCatalog:
    """The same manifest/payload/material layout, with real unsigned facts."""
    contained = Catalog.contained

    def __init__(self, config, deadline):
        self.config, self.deadline, self.archives = config, deadline, config.archives

    def binding(self, reference, point=None):
        point = document(read_pin(reference)) if point is None else point
        sidecar = safe_path(Path(point['manifestPin']['path']).parent)
        value = document(read_pin(pin_file(sidecar / 'recovery-repository-binding.json')))
        expected = repository_binding(SimpleNamespace(policy={'sourceIdentityPin': self.config.identity_pin}),
            reference, point, value['recoveryMaterialPin'], value['objectContentIndexPin'])
        require(value == expected, 'REPOSITORY_CAPTURE_BINDING_INVALID')
        for key in ('recoveryMaterialPin', 'objectContentIndexPin'):
            require(safe_path(value[key]['path']).parent == sidecar, 'REPOSITORY_MATERIAL_PATH_ESCAPED')
        return value

    def load(self, reference, *, candidate=None):
        path = absolute(reference['path'])
        safe_path(path.parent)
        require(path.name == 'point.json' and path.parent.name == '.repository' and
            path.parent.parent.parent == self.archives, 'REPOSITORY_POINT_LOCATION_INVALID')
        point = document(read_pin(reference, deadline=self.deadline)) if candidate is None else candidate
        if candidate is not None:
            raw = canonical(point)
            require(reference['bytes'] == len(raw) and reference['sha256'] == hashlib.sha256(raw).hexdigest(),
                'REPOSITORY_POINT_PUBLICATION_CHANGED')
        require(point['schemaVersion'] == 'RepositoryPoint/v1' and point['integrityState'] == 'COMPLETE',
            'REPOSITORY_POINT_INCOMPLETE')
        manifest = document(read_pin(point['manifestPin'], deadline=self.deadline))
        require(safe_path(point['manifestPin']['path']) == path.parent / 'manifest.json' and
            manifest['schemaVersion'] == 'RepositoryManifest/v1' and
            manifest['sourceIdentityPin'] == self.config.identity_pin and manifest['copyProtectionPin'] is None and
            all(point[k] == manifest[k] for k in ('backupId', 'generationId', 'pointType', 'parentPointPins',
                'commonRecoveryPoint', 'payloadRefs')), 'REPOSITORY_MANIFEST_POINT_MISMATCH')
        require(manifest['versionPins'] and manifest['toolPins'], 'REPOSITORY_VERSION_METADATA_REQUIRED')
        for p in manifest['versionPins']:
            read_pin(p, deadline=self.deadline)
        # Tool pins identify binaries; verify their bytes by streaming rather
        # than loading them as bounded metadata records.
        for p in manifest['toolPins']:
            validate_pin(p)
            require(pin_file(p['path'], self.deadline) == p, 'REPOSITORY_PIN_CHANGED')
        require(timestamp(manifest['createdAt']) <= datetime.now(timezone.utc), 'REPOSITORY_FUTURE_POINT_REFUSED')
        require(safe_path(manifest['payloadTreePin']['path']).parent == path.parent,
            'REPOSITORY_PAYLOAD_TREE_ESCAPED')
        Catalog.payload(self, point, manifest, path.parent.parent)
        require(all(safe_path(point[k]['path']).parent == path.parent for k in
            ('originalExitEvidencePin', 'ownerCloseEvidencePin', 'readbackEvidencePin')),
            'REPOSITORY_POINT_FACTS_ESCAPED')
        exit_record = document(read_pin(point['originalExitEvidencePin']))
        close = document(read_pin(point['ownerCloseEvidencePin']))
        readback = document(read_pin(point['readbackEvidencePin']))
        require(exit_record['schemaVersion'] == 'RepositoryMinimumChildTerminal/v1' and
            type(exit_record['actualExitCode']) is int and exit_record['actualExitCode'] == 0 and
            exit_record['processTerminated'] is True and exit_record['state'] == 'EXITED' and
            readback['schemaVersion'] == 'RepositoryMinimumReadback/v1' and
            readback['manifestPin'] == point['manifestPin'] and readback['independentConnectionId'] and
            readback['payloadRefs'] == point['payloadRefs'] and close['schemaVersion'] == 'RepositoryMinimumArchiveClose/v1' and
            close['archiveReaderClosed'] is True and
            close['closeResponse']['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF' and
            exit_record['operationId'] == readback['operationId'] == close['operationId'] == point['backupId'],
            'REPOSITORY_MINIMUM_POINT_FACTS_INVALID')
        binding = self.binding(reference, point)
        require(all(readback[k] == binding[k] for k in ('recoveryMaterialPin', 'objectContentIndexPin', 'sourceScopePin')),
            'REPOSITORY_READBACK_BINDING_CHANGED')
        index = document(read_pin(binding['objectContentIndexPin'], 64 * 1024 * 1024, self.deadline))
        owned = list(point['payloadRefs'])
        for parent in point['parentPointPins']:
            parent_point = document(read_pin(parent, deadline=self.deadline))
            require(parent_point['generationId'] == point['generationId'], 'REPOSITORY_CONTENT_OWNER_MISMATCH')
            owned.extend(parent_point['payloadRefs'])
        for sha, p in index['contentPins'].items():
            require(p in owned and p['sha256'] == sha and pin_file(p['path'], self.deadline) == p,
                'REPOSITORY_OBJECT_CONTENT_CHANGED')
        return point, manifest

    def chain(self, reference, *, candidate=None):
        point, _ = self.load(reference, candidate=candidate)
        pins = point['parentPointPins'] + [reference]
        require(len(pins) <= self.config.value['maxChainPoints'] and
            len({p['path'] for p in pins}) == len(pins), 'REPOSITORY_CHAIN_CYCLE_OR_LIMIT')
        rows, prior = [], None
        for number, p in enumerate(pins):
            current, manifest = self.load(p, candidate=candidate if p == reference else None)
            require(current['parentPointPins'] == pins[:number] and
                current['generationId'] == point['generationId'] and
                current['pointType'] == ('FULL' if number == 0 else 'INCREMENTAL'), 'REPOSITORY_CHAIN_INVALID')
            at = timestamp(manifest['createdAt'])
            require(prior is None or at > prior, 'REPOSITORY_CHAIN_ORDER_INVALID')
            prior = at
            rows.append((p, current, manifest))
        require((prior - timestamp(rows[0][2]['createdAt'])).total_seconds() <=
            self.config.value['maxChainAgeSeconds'], 'REPOSITORY_NEW_FULL_REQUIRED')
        return rows


class CapturedReader(LabBackupArchiveReader):
    # The new source adapter retains capture material, without manufacturing a
    # legacy original-release-binding just to satisfy the obsolete owner path.
    CAPTURE_REQUIRED_FILES = frozenset({'capture-recovery-inputs.json', 'semantic-capture/source-inputs.json',
        'semantic-capture/supplement.json', 'semantic-capture/object-content-index.json',
        'semantic-capture/multipart-observations.json', 'payload/database.sql.gz',
        'payload/original-application-images.tar', 'payload/050-original-images.json',
        'payload/011-source-data.json', 'payload/capture-content-point.json',
        'payload/capture-file-inventory.json', 'recovery-materials/index.json',
        'original-configs/config-capture-stage.json'})
    CAPTURE_PROOF_FILES = LabBackupArchiveReader.CAPTURE_PROOF_FILES

    def __init__(self, root, entries, *args, **kwargs):
        configurations = {name for name in entries if re.fullmatch(
            r'original-configs/[A-Za-z0-9][A-Za-z0-9_-]{0,100}\.bin', name)}
        self.CAPTURE_PROOF_FILES = self.CAPTURE_PROOF_FILES | configurations
        super().__init__(root, entries, *args, **kwargs)


class CapturedPublisher(Publisher):
    """Reuse Publisher.stream and the actual byte/epoch reader after capture."""
    def __init__(self, config, root, tree, request, deadline):
        self.config, self.deadline = config, deadline
        self.source = {'archiveRoot': str(config.archives)}
        self.binding = {'attemptId': hashlib.sha256(request['operationId'].encode()).hexdigest(),
            'sourceContextSha256': config.identity_pin['sha256']}
        self.archive_sequence = 0
        self.reader = CapturedReader(str(root), tree, self.binding['attemptId'],
            self.binding['sourceContextSha256'], guard=self.check, capture_layout=True)

    def check(self):
        self.deadline.check()
        self.config.current()

    def guard(self):
        self.reader._current()

    def archive_request(self, action, relative=None, offset=None):
        self.archive_sequence += 1
        value = dict(schemaVersion=self.reader.SCHEMA, **self.binding, sequence=self.archive_sequence, action=action)
        if action == 'read-chunk':
            value.update(relativePath=relative, offset=offset)
        result = self.reader.handle(canonical(value))
        if action == 'read-chunk':
            raw = base64.b64decode(result['bytesBase64'], validate=True)
            require(hashlib.sha256(raw).hexdigest() == result['chunkSha256'], 'REPOSITORY_NATIVE_CHUNK_CHANGED')
            return raw
        return result


def capture_tree(root, inputs_pin, inputs):
    require(safe_path(inputs_pin['path']) == root / 'capture-recovery-inputs.json',
        'REPOSITORY_CAPTURE_INPUT_LOCATION_INVALID')
    tree = {}
    for name, reference in {**inputs['archiveFilePins'], 'capture-recovery-inputs.json': inputs_pin}.items():
        LabBackupArchiveReader._relative(name)
        require(safe_path(reference['path']) == root / name, 'REPOSITORY_CAPTURE_PATH_ESCAPED')
        require(pin_file(reference['path']) == reference, 'REPOSITORY_CAPTURE_INPUT_CHANGED')
        tree[name] = 'file|' + str(reference['bytes']) + '|' + reference['sha256']
        parent = Path(name).parent
        while str(parent) != '.':
            tree.setdefault(parent.as_posix(), 'directory')
            parent = parent.parent
    # Preserve legitimate empty directories in the existing capture layout.
    for name in CapturedReader.CAPTURE_DIRECTORIES:
        require(safe_path(root / name).is_dir(), 'REPOSITORY_CAPTURE_DIRECTORY_REQUIRED')
        tree.setdefault(name, 'directory')
    for name in ('payload/minio-physical', 'semantic-capture', 'recovery-materials'):
        for directory, dirs, _ in os.walk(root / name, followlinks=False):
            for child in dirs:
                path = safe_path(Path(directory) / child)
                tree.setdefault(path.relative_to(root).as_posix(), 'directory')
    return tree


def smb_configuration(config, operation, deadline):
    # Library and credential hashes are measured from selected local files; no
    # signing/installation Pin graph or technical approval is requested.
    import smbclient
    import smbprotocol
    value = dict(config.value['readback'])
    exact(value, 'schemaVersion uncRoot repositoryRelativePath credentialPath port authProtocol '
        'maximumRecordBytes maximumTotalRecordBytes', 'RepositoryMinimumSmb/v1')
    credential = value.pop('credentialPath')
    value.update(schemaVersion='RepositorySmbReadbackConfig/v1', repositoryRoot=str(config.root),
        credentialPin=pin_file(credential, deadline), libraryPins=[pin_file(m.__file__, deadline) for m in (smbclient, smbprotocol)],
        recordRoot=str(operation))
    return value


def run_child(argv, output, operation, request, deadline, role, *, capture_query=False):
    require(type(argv) is list and argv and all(type(x) is str and x for x in argv),
        'REPOSITORY_CHILD_COMMAND_INVALID')
    require(safe_path(argv[0]).is_file(), 'REPOSITORY_CHILD_EXECUTABLE_REQUIRED')
    deadline.check()
    terminal_path = operation / (role + '-terminal.json')
    with (operation / (role + '.stdout.log')).open('xb') as stdout, (operation / (role + '.stderr.log')).open('xb') as stderr:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            cwd=str(safe_path(argv[0]).parent), start_new_session=True)
        write_new(operation / (role + '-process.json'), dict(operationId=request['operationId'], pid=process.pid, startedAt=utc()))
        try:
            code = process.wait(timeout=max(0, deadline.end - time.monotonic()))
        except subprocess.TimeoutExpired as error:
            code = process.poll()
            write_new(terminal_path, dict(schemaVersion='RepositoryMinimumChildTerminal/v1', operationId=request['operationId'],
                pid=process.pid, actualExitCode=code, processTerminated=code is not None, state='TERMINAL_UNKNOWN', at=utc()))
            raise RepositoryError('REPOSITORY_CHILD_TIMEOUT_QUERY_ORIGINAL_OPERATION', unknown=True, actual_exit=code) from error
    terminal = write_new(terminal_path, dict(schemaVersion='RepositoryMinimumChildTerminal/v1', operationId=request['operationId'],
        pid=process.pid, actualExitCode=code, processTerminated=True, state='EXITED', at=utc()))
    if code != 0:
        if capture_query and code < 0:
            raise RepositoryError('REPOSITORY_CAPTURE_ENTRY_SIGNAL_QUERY_ORIGINAL_OPERATION', unknown=True, actual_exit=code)
        if capture_query and code == 3:
            result = document(read_pin(pin_file(output), 64 * 1024 * 1024, deadline))
            require(result['schemaVersion'] == 'backup-restore-operation-result/v1' and
                result['operationId'] == result['requestId'] == request['operationId'] and
                result['action'] == request['action'] and result['state'] == 'TERMINAL_UNKNOWN',
                'REPOSITORY_CAPTURE_UNKNOWN_RESULT_INVALID')
            return result, terminal
        if capture_query and output.exists():
            result = document(read_pin(pin_file(output), 64 * 1024 * 1024, deadline))
            require(result['schemaVersion'] == 'backup-restore-operation-result/v1' and
                result['operationId'] == result['requestId'] == request['operationId'] and
                result['action'] == request['action'] and result['state'] == 'FAILED_RETAINED',
                'REPOSITORY_CAPTURE_FAILED_RESULT_INVALID')
            reported = result['failureCode']
            require(type(reported) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,150}', reported),
                'REPOSITORY_CAPTURE_FAILURE_CODE_INVALID')
            raise RepositoryError(reported, actual_exit=code)
        raise RepositoryError('REPOSITORY_CHILD_EXIT_FAILED', actual_exit=code)
    return document(read_pin(pin_file(output), 64 * 1024 * 1024, deadline)), terminal


def publish(config, request, operation, deadline):
    require(request['action'] in ('FULL', 'INCREMENTAL'), 'REPOSITORY_ARCHIVE_ACTION_UNSUPPORTED')
    catalog = MinimumCatalog(config, deadline)
    parents = []
    if request['action'] == 'INCREMENTAL':
        require(request['parentChainRef'] in config.value['parentChains'], 'REPOSITORY_PARENT_NOT_CONFIGURED')
        parents = catalog.chain(config.value['parentChains'][request['parentChainRef']])
        require(len(parents) < config.value['maxChainPoints'], 'REPOSITORY_NEW_FULL_REQUIRED')
    capture_config_pin = pin_file(config.source['configurationPath'], deadline)
    selected = document(read_pin(capture_config_pin, deadline=deadline))
    identity = document(read_pin(config.identity_pin))
    require(selected['schemaVersion'] == 'minimal-source-capture-config/v1' and
        selected['sourceConfigRef'] == request['sourceConfigRef'] and
        safe_path(selected['archiveRoot']) == config.staging and
        selected['source']['sourceIdentity'] == selected['source']['sourceFingerprint'] == identity['sourceFingerprint'] and
        selected['source']['databaseUuid'] == identity['databaseUuid'], 'REPOSITORY_CAPTURE_CONFIGURATION_MISMATCH')
    parent_binding = None
    if parents:
        parent_binding = catalog.binding(parents[-1][0])
        parent_material = document(read_pin(parent_binding['recoveryMaterialPin'], 64 * 1024 * 1024, deadline))
        require(selected['parent'] == dict(parentChainRef=request['parentChainRef'],
            capturePointPin=parent_material['database']['capturePointPin'], repositoryPointPin=parents[-1][0],
            objectContentIndexPin=parent_binding['objectContentIndexPin']), 'REPOSITORY_CAPTURE_CONFIGURATION_PARENT_MISMATCH')
    else:
        require(selected['parent'] is None, 'REPOSITORY_FULL_PARENT_FORBIDDEN')
    # The configured adapter is W02's real capture CLI, shared by all apps.
    command = list(config.source['captureCommand'])
    query = 0
    while True:
        role = 'capture' if query == 0 else 'capture-query-' + str(query)
        capture_output = operation / (role + '-output.json')
        result, terminal = run_child(command + ['--configuration', config.source['configurationPath'],
            '--request', str(operation / 'request.json'), '--output', str(capture_output)],
            capture_output, operation, request, deadline, role, capture_query=True)
        if result.get('state') != 'TERMINAL_UNKNOWN':
            break
        # W02's documented exit 3 means query its SAME operation, never recapture.
        if deadline.end - time.monotonic() <= 0.25:
            raise RepositoryError('REPOSITORY_CAPTURE_TIMEOUT_QUERY_ORIGINAL_OPERATION', unknown=True)
        time.sleep(min(0.25, max(0, deadline.end - time.monotonic())))
        query += 1
    require(result['schemaVersion'] == 'backup-restore-operation-result/v1' and
        result['operationId'] == result['requestId'] == request['operationId'] and result['action'] == request['action'],
        'REPOSITORY_CAPTURE_RESULT_IDENTITY_MISMATCH')
    require(result['state'] == 'SUCCEEDED' and type(result['actualExitCode']) is int and result['actualExitCode'] == 0,
        'REPOSITORY_CAPTURE_RESULT_FAILED')
    require(capture_config_pin in result['originalResultPins'] and
        pin_file(config.source['configurationPath'], deadline) == capture_config_pin,
        'REPOSITORY_CAPTURE_CONFIGURATION_CHANGED')
    root = safe_path(result['data']['captureRoot'])
    require(config.staging in root.parents, 'REPOSITORY_CAPTURE_ROOT_ESCAPED')
    inputs_pin = result['data']['captureInputsPin']
    require(inputs_pin == pin_file(root / 'capture-recovery-inputs.json', deadline), 'REPOSITORY_CAPTURE_INPUT_CHANGED')
    inputs = document(read_pin(inputs_pin, 64 * 1024 * 1024, deadline))
    require(inputs['schemaVersion'] == 'backup-capture-recovery-inputs/v1' and
        inputs['pointType'] == request['action'] and inputs['sourceIdentity'] ==
        document(read_pin(config.identity_pin))['sourceFingerprint'], 'REPOSITORY_CAPTURE_SCOPE_MISMATCH')
    if parents:
        captured_point = document(read_pin(inputs['capturePointPin'], 64 * 1024 * 1024, deadline))
        require(inputs['parentRepositoryPointPin'] == parents[-1][0] and
            inputs['generationId'] == parents[-1][1]['generationId'] and
            captured_point['parentPointPin'] == parent_material['database']['capturePointPin'] and
            inputs['database']['startPosition'] == parent_material['database']['endPosition'],
            'REPOSITORY_CAPTURE_PARENT_MISMATCH')
    else:
        require(inputs['parentRepositoryPointPin'] is None, 'REPOSITORY_FULL_PARENT_FORBIDDEN')
    require(inputs['backupId'] == request['operationId'] and
        result['data']['capturePointPin'] == inputs['capturePointPin'] and
        result['data']['objectContentIndexPin'] == inputs['objectContentIndexPin'] and
        result['data']['recoveryPoint'] == inputs['recoveryPoint'] and
        result['data']['sourceIdentity'] == inputs['sourceIdentity'] and
        type(result['data']['logRefs']) is list and result['data']['logRefs'], 'REPOSITORY_CAPTURE_OUTPUT_MISMATCH')
    for reference in result['data']['logRefs']:
        read_pin(reference, 64 * 1024 * 1024, deadline)
    tree = capture_tree(root, inputs_pin, inputs)
    entries_pin = result['data']['archiveEntriesPin']
    require(safe_path(entries_pin['path']) == root / 'capture-archive-entries.json' and
        document(read_pin(entries_pin, 64 * 1024 * 1024, deadline)) == tree, 'REPOSITORY_CAPTURE_TREE_CHANGED')
    restoration_pin = result['data']['sourceRestorationPin']
    require(safe_path(restoration_pin['path']) == root / 'source-restoration.json', 'REPOSITORY_SOURCE_RESTORATION_ESCAPED')
    restoration = document(read_pin(restoration_pin, deadline=deadline))
    require(restoration['schemaVersion'] == 'minimal-capture-source-restoration/v1' and
        restoration['sourceIdentity'] == inputs['sourceIdentity'] and
        restoration['restored'] is True and restoration['errors'] == [], 'REPOSITORY_SOURCE_NOT_RESTORED')
    total = sum(int(marker.split('|')[1]) for marker in tree.values() if marker != 'directory')
    require(total <= config.value['maximumArchiveBytes'] and
        shutil.disk_usage(config.archives).free >= total + config.value['minimumFreeBytes'],
        'REPOSITORY_ARCHIVE_CAPACITY_INSUFFICIENT')
    publisher = CapturedPublisher(config, root, tree, request, deadline)
    target = config.archives / ('prod-' + publisher.binding['attemptId'])
    publisher.stream(target, tree)
    close = publisher.archive_request('close')
    require(close['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF', 'REPOSITORY_ARCHIVE_CLOSE_FAILED')
    sidecar = target / '.repository'
    sidecar.mkdir(mode=0o700)
    atomic_output_bytes(sidecar / 'original-exit.json', read_pin(terminal))
    archived_terminal = pin_file(sidecar / 'original-exit.json', deadline)
    tree_pin = write_new(sidecar / 'payload-tree.json', tree)
    payloads = [pin_file(target / name, deadline) for name in sorted(tree) if tree[name] != 'directory']
    created = utc()
    if parents:
        require(timestamp(created) > timestamp(parents[-1][2]['createdAt']) and
            (timestamp(created) - timestamp(parents[0][2]['createdAt'])).total_seconds() <=
            config.value['maxChainAgeSeconds'], 'REPOSITORY_NEW_FULL_REQUIRED')
    manifest = dict(schemaVersion='RepositoryManifest/v1', backupId=inputs['backupId'], generationId=inputs['generationId'],
        pointType=inputs['pointType'], parentPointPins=[row[0] for row in parents], commonRecoveryPoint=inputs['recoveryPoint'],
        sourceIdentityPin=config.identity_pin, createdAt=created, versionPins=inputs['semanticSupplement']['versionPins'],
        toolPins=[pin_file(p, deadline) for p in config.source['toolPaths']], payloadRefs=payloads,
        payloadTreePin=tree_pin, copyProtectionPin=None)
    require(manifest['versionPins'] and manifest['toolPins'], 'REPOSITORY_VERSION_METADATA_REQUIRED')
    manifest_pin = write_new(sidecar / 'manifest.json', manifest)
    material = dict(manifestPin=manifest_pin, payloadTreePin=tree_pin, payloadRefs=payloads)
    with SmbReadback(smb_configuration(config, operation, deadline), deadline) as reader:
        connection_id, originals = reader.verify(str(target), tree, material)
    outputs = assemble_readback_bindings(manifest_pin, {'originalRecordsPin': originals}, deadline,
        load_binder(config.value['captureBinderPath']), parent_binding)
    config.current()
    bindings = dict(recoveryMaterialPin=write_new(sidecar / 'recovery-material.json', outputs['recoveryMaterial']),
        objectContentIndexPin=write_new(sidecar / 'object-content-index.json', outputs['objectContentIndex']),
        sourceScopePin=outputs['recoveryMaterial']['sourceScopePin'])
    readback_pin = write_new(sidecar / 'readback-original.json', dict(schemaVersion='RepositoryMinimumReadback/v1',
        operationId=request['operationId'], manifestPin=manifest_pin, independentConnectionId=connection_id,
        payloadRefs=payloads, originalRecordsPin=originals, serverDurabilityVerified=False, **bindings))
    close_pin = write_new(sidecar / 'archive-close.json', dict(schemaVersion='RepositoryMinimumArchiveClose/v1',
        operationId=request['operationId'], archiveReaderClosed=True, closeResponse=close))
    point = {k: manifest[k] for k in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
    point.update(schemaVersion='RepositoryPoint/v1', manifestPin=manifest_pin, readbackEvidencePin=readback_pin,
        ownerCloseEvidencePin=close_pin, originalExitEvidencePin=archived_terminal, integrityState='COMPLETE',
        blockedReason='REPOSITORY_RECOVERY_NOT_RUN', rehearsalEligible=True, controlledRestoreEligible=False)
    raw = canonical(point)
    point_pin = dict(path=(sidecar / 'point.json').as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    binding = repository_binding(SimpleNamespace(policy={'sourceIdentityPin': config.identity_pin}),
        point_pin, point, bindings['recoveryMaterialPin'], bindings['objectContentIndexPin'])
    binding_pin = write_new(sidecar / 'recovery-repository-binding.json', binding)
    catalog.chain(point_pin, candidate=point)
    with SmbReadback(smb_configuration(config, operation, deadline), deadline) as reader:
        for reference in (bindings['recoveryMaterialPin'], bindings['objectContentIndexPin'], binding_pin,
                archived_terminal, readback_pin, close_pin):
            reader.read(reference['path'], reference)
    config.current()
    # COMPLETE is the last publication. Interrupted work has no selectable point.
    require(write_new(sidecar / 'point.json', point) == point_pin, 'REPOSITORY_POINT_PUBLICATION_CHANGED')
    return dict(pointPin=point_pin, manifestPin=manifest_pin, repositoryBindingPin=binding_pin, **bindings,
        captureResultPin=pin_file(capture_output), readbackPin=readback_pin,
        logRefs=[pin_file(operation / (role + '.stdout.log')), pin_file(operation / (role + '.stderr.log')),
            *result['data']['logRefs']]), [archived_terminal, readback_pin]


def verify_point(config, request, operation, deadline, output):
    require(request['recoveryPointRef'] in config.value['recoveryPoints'], 'REPOSITORY_POINT_NOT_CONFIGURED')
    reference = config.value['recoveryPoints'][request['recoveryPointRef']]
    catalog = MinimumCatalog(config, deadline)
    rows = catalog.chain(reference)
    connections = []
    for point_pin, point, manifest in rows:
        with SmbReadback(smb_configuration(config, operation, deadline), deadline) as reader:
            connection_id, _ = reader.verify(str(Path(point_pin['path']).parent.parent),
                document(read_pin(manifest['payloadTreePin'])),
                dict(manifestPin=point['manifestPin'], payloadTreePin=manifest['payloadTreePin'], payloadRefs=point['payloadRefs']))
            for key in ('recoveryMaterialPin', 'objectContentIndexPin'):
                p = catalog.binding(point_pin)[key]
                reader.read(p['path'], p)
            for p in (point_pin, pin_file(Path(point_pin['path']).parent / 'recovery-repository-binding.json'),
                    point['originalExitEvidencePin'], point['readbackEvidencePin'], point['ownerCloseEvidencePin']):
                reader.read(p['path'], p)
        connections.append(connection_id)
    config.current()
    atomic_output(output, dict(schemaVersion='RepositoryMinimumIndependentReadback/v1', operationId=request['operationId'],
        pointPin=reference, chainPointPins=[row[0] for row in rows], independentConnectionIds=connections,
        verificationOnly=True, restoreExecuted=False))


def result_base(request, started):
    return dict(schemaVersion='backup-restore-operation-result/v1', operationId=request['operationId'],
        requestId=request['operationId'], action=request['action'], state='FAILED_RETAINED', failureCode=None,
        message='', data=None, originalResultPins=[], startedAt=started, finishedAt=started, actualExitCode=None)


def worker(operation):
    operation = safe_path(operation)
    start = document(read_pin(pin_file(operation / 'start.json')))
    request = request_document(operation / 'request.json')
    result = result_base(request, start['startedAt'])
    try:
        config = MinimumConfiguration(start['configurationPin']['path'], request)
        require(config.pin == start['configurationPin'], 'REPOSITORY_CONFIGURATION_CHANGED')
        deadline = Deadline(config.value['timeoutMilliseconds'])
        deadline.end = start['deadlineMonotonic']
        deadline.check()
        if start['readbackOnly']:
            output = operation / 'independent-readback.json'
            data, terminal = run_child([str(Path(sys.executable).resolve()), '-B', str(Path(__file__).absolute()), '--verify-point', str(operation)],
                output, operation, request, deadline, 'readback')
            require(data['schemaVersion'] == 'RepositoryMinimumIndependentReadback/v1' and
                data['operationId'] == request['operationId'] and data['verificationOnly'] is True and
                data['restoreExecuted'] is False and data['independentConnectionIds'], 'REPOSITORY_READBACK_RESULT_INVALID')
            pins = [terminal, pin_file(output)]
        else:
            data, pins = publish(config, request, operation, deadline)
        result.update(state='SUCCEEDED', data=data, originalResultPins=pins, actualExitCode=0,
            message='Independent archive readback completed' if start['readbackOnly'] else 'Capture, archive and independent SMB readback completed')
    except Exception as error:
        unknown = isinstance(error, RepositoryError) and error.unknown
        result.update(state='TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED',
            failureCode=failure_code(error),
            message='Operation stopped; retain materials and query the original operationId',
            actualExitCode=error.actual_exit if isinstance(error, RepositoryError) else None)
        for terminal in sorted(operation.glob('*-terminal.json'), key=lambda p: p.stat().st_mtime_ns):
            reference = pin_file(terminal)
            original = document(read_pin(reference))
            result['actualExitCode'] = original['actualExitCode']
            result['originalResultPins'].append(reference)
            if original['state'] == 'TERMINAL_UNKNOWN':
                result['state'] = 'TERMINAL_UNKNOWN'
        for original in sorted(operation.glob('*-output.json')):
            result['originalResultPins'].append(pin_file(original))
    result['finishedAt'] = utc()
    atomic_output(operation / 'result.json', result)
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]


def execute(configuration, request_path, output, *, readback_only=False):
    request = request_document(request_path)
    started = utc()
    result = result_base(request, started)
    output_safe, owned, spawned = False, False, False
    operation = None
    try:
        config = MinimumConfiguration(configuration, request)
        require(readback_only or request['action'] in ('FULL', 'INCREMENTAL'), 'REPOSITORY_ARCHIVE_ACTION_UNSUPPORTED')
        operation = config.evidence / hashlib.sha256(request['operationId'].encode()).hexdigest()
        safe_path(absolute(str(output)).parent)
        require(not Path(output).exists() and not overlap(absolute(str(output)), config.root) and
            not overlap(absolute(str(output)), config.staging) and
            not overlap(absolute(str(output)), operation), 'REPOSITORY_OUTPUT_EXISTS_OR_OVERLAPS')
        output_safe = True
        try:
            operation.mkdir(mode=0o700)
            owned = True
        except FileExistsError:
            owned = False
        if owned:
            write_new(operation / 'request.json', request)
            write_new(operation / 'start.json', dict(configurationPin=config.pin, requestSha256=hashlib.sha256(canonical(request)).hexdigest(),
                startedAt=started, deadlineMonotonic=time.monotonic() + config.value['timeoutMilliseconds'] / 1000,
                readbackOnly=readback_only))
            with (operation / 'worker.stdout.log').open('xb') as stdout, (operation / 'worker.stderr.log').open('xb') as stderr:
                process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).absolute()), '--worker', str(operation)],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
                spawned = True
            write_new(operation / 'worker-process.json', dict(operationId=request['operationId'], pid=process.pid, startedAt=utc()))
        else:
            if not (operation / 'request.json').exists() or not (operation / 'start.json').exists():
                raise RepositoryError('REPOSITORY_OPERATION_START_UNRESOLVED', unknown=True)
            require(document(read_pin(pin_file(operation / 'request.json'))) == request, 'REPOSITORY_OPERATION_ID_REUSED')
            start = document(read_pin(pin_file(operation / 'start.json')))
            require(start['configurationPin'] == config.pin and start['readbackOnly'] == readback_only,
                'REPOSITORY_OPERATION_CONFIGURATION_REUSED')
        end = time.monotonic() + config.value['responseTimeoutMilliseconds'] / 1000
        while not (operation / 'result.json').exists() and time.monotonic() < end:
            time.sleep(min(0.05, max(0, end - time.monotonic())))
        if (operation / 'result.json').exists():
            result = document(read_pin(pin_file(operation / 'result.json')))
            require(result['operationId'] == result['requestId'] == request['operationId'] and
                result['action'] == request['action'], 'REPOSITORY_OPERATION_RESULT_CHANGED')
            if result['state'] == 'SUCCEEDED':
                MinimumCatalog(config, Deadline(config.value['timeoutMilliseconds'])).chain(result['data']['pointPin'])
        else:
            result.update(state='TERMINAL_UNKNOWN', failureCode='REPOSITORY_QUERY_ORIGINAL_OPERATION',
                message='Original operation still has no terminal result; query using the same operationId',
                data={'operationDirectory': str(operation), 'resultRef': str(operation / 'result.json')}, finishedAt=utc())
    except Exception as error:
        if not output_safe:
            raise
        result.update(state='TERMINAL_UNKNOWN' if isinstance(error, RepositoryError) and error.unknown else 'FAILED_RETAINED',
            failureCode=failure_code(error),
            message='Repository operation failed; original materials retained', finishedAt=utc(),
            actualExitCode=error.actual_exit if isinstance(error, RepositoryError) else None)
        if owned and not spawned and operation is not None and not (operation / 'result.json').exists():
            atomic_output(operation / 'result.json', result)
    atomic_output(output, result)
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]


def main():
    sys.dont_write_bytecode = True
    if hasattr(os, 'umask'):
        os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    internal = parser.add_mutually_exclusive_group()
    internal.add_argument('--worker')
    internal.add_argument('--verify-point')
    parser.add_argument('--configuration')
    parser.add_argument('--request')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.worker:
        return worker(args.worker)
    if args.verify_point:
        operation = safe_path(args.verify_point)
        start = document(read_pin(pin_file(operation / 'start.json')))
        request = request_document(operation / 'request.json')
        config = MinimumConfiguration(start['configurationPin']['path'], request)
        require(config.pin == start['configurationPin'], 'REPOSITORY_CONFIGURATION_CHANGED')
        deadline = Deadline(config.value['timeoutMilliseconds'])
        deadline.end = start['deadlineMonotonic']
        verify_point(config, request, operation, deadline, operation / 'independent-readback.json')
        return 0
    require(all((args.configuration, args.request, args.output)), 'REPOSITORY_ENTRY_ARGUMENTS_REQUIRED')
    return execute(args.configuration, args.request, args.output)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(error.code if isinstance(error, RepositoryError) else 'REPOSITORY_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
