"""Read one MAIN operation's durable execution proof without execution authority.

This is a metadata validator, not a live-target observer or a release decision.
It never acquires a source/host lock, resolves the latest target for an old
operation, repairs an epoch, dispatches a process, or writes a receipt. Source
archives and SQL payloads retain their separate full-content verification gate.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import stat
from urllib.parse import parse_qs, urlsplit

from recovery_engine import RecoveryError, canonical, digest, parse, require
from recovery_archive_view import select_configuration
from recovery_backup_epoch import _path, _signature, _snapshot, read_current
from recovery_minimal_plan import request_contract
from recovery_program_generation import (GENERATION_FIELDS, validate_policy,
    _resolve_at_ready, _target_transition, _capture_transition)
from recovery_program_activation import CONTEXT_FIELDS
from recovery_program_execution import BINDING_FIELDS
from recovery_program_native import RESTORE_ACTIONS
from recovery_program_protection import KINDS, JOURNALS, FILES, _references


MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_NATIVE_BYTES = 64 * 1024 * 1024
MAX_DIRECTORY_ENTRIES = 200000
PIN_FIELDS = {'path', 'bytes', 'sha256'}
NATIVE_FIELDS = {'schemaVersion', 'operationId', 'bindingPin', 'generationPin', 'phase',
    'originalResultPins', 'invocations', 'mutationDispatched', 'terminalUnknown', 'lastExitCode'}
COMMON = ('programExecutionPhase', 'programNativeEvidencePin',
          'programProtectionCustodyPin', 'programGenerationPin')


def _need(condition, suffix):
    require(condition, 'PROGRAM_EVIDENCE_' + suffix)


def _text(value):
    return type(value) is str and bool(value) and not any(ord(c) < 32 for c in value)


def _pin(reference, maximum=2**63-1, *, empty=True):
    _need(type(reference) is dict and set(reference) == PIN_FIELDS and
        type(reference['path']) is str and type(reference['bytes']) is int and
        (0 if empty else 1) <= reference['bytes'] <= maximum and
        type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']),
        'PIN_INVALID')
    return _path(reference['path'])


def _index(references):
    _need(type(references) is list, 'PINS_INVALID')
    result = {}
    for reference in references:
        path = _pin(reference)
        _need(str(path) not in result or result[str(path)] == reference, 'PIN_CONFLICT')
        result[str(path)] = reference
    return result


class _Reader:
    """One bounded read per original, followed by identity revalidation."""
    def __init__(self, guard, roots):
        self.guard = guard
        self.roots = roots
        self.values, self.records, self.directories, self.listings = {}, {}, {}, {}
        self.deferred = {}
        self.absent_paths = set()

    def private(self, path):
        return any(path == root or root in path.parents for root in self.roots)

    def directory(self, path, *, private=False):
        self.guard(); path = _path(str(path)); info = path.stat()
        _need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            (not private or stat.S_IMODE(info.st_mode) == 0o700), 'DIRECTORY_INVALID')
        identity = (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid)
        _need(path not in self.directories or self.directories[path] == identity, 'DIRECTORY_CHANGED')
        self.directories[path] = identity
        return path

    def listing(self, path):
        path = self.directory(path)
        names = tuple(sorted(item.name for item in path.iterdir()))
        _need(len(names) <= MAX_DIRECTORY_ENTRIES, 'DIRECTORY_LIMIT')
        _need(path not in self.listings or self.listings[path] == names, 'DIRECTORY_CHANGED')
        self.listings[path] = names
        return names

    def _info(self, path):
        self.guard(); path = _path(str(path)); info = path.stat()
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid() and
            not info.st_mode & (0o077 if self.private(path) else 0o022), 'FILE_INVALID')
        return info

    @staticmethod
    def signature(info):
        return (*_signature(info), info.st_mode, info.st_uid, info.st_nlink)

    def _read(self, path, maximum, *, reference=None, json=True):
        self.guard(); path = _path(str(path))
        if path in self.records:
            recorded, identity = self.records[path]
            _need(reference is None or recorded == reference, 'PIN_CONFLICT')
            _need(recorded['bytes'] <= maximum and self.signature(self._info(path)) == identity,
                'FILE_CHANGED')
            if json:
                _need(path in self.values, 'DOCUMENT_REQUIRED')
                return self.values[path], recorded
            return None, recorded
        before = self._info(path)
        _need(0 <= before.st_size <= maximum, 'DOCUMENT_LIMIT')
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        chunks, checksum, size = [], hashlib.sha256(), 0
        try:
            opened = os.fstat(descriptor)
            _need(self.signature(opened) == self.signature(before), 'FILE_CHANGED')
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                while True:
                    self.guard(); chunk = stream.read(min(65536, maximum-size+1))
                    if not chunk: break
                    size += len(chunk)
                    _need(size <= maximum, 'DOCUMENT_LIMIT')
                    checksum.update(chunk)
                    if json: chunks.append(chunk)
            _need(self.signature(opened) == self.signature(os.fstat(descriptor)) ==
                self.signature(self._info(path)), 'FILE_CHANGED')
        finally:
            os.close(descriptor)
        observed = dict(path=path.as_posix(), bytes=size, sha256=checksum.hexdigest())
        _need(reference is None or observed == reference, 'PIN_CHANGED')
        self.records[path] = (observed, self.signature(before))
        if json:
            value = parse(b''.join(chunks))
            self.values[path] = value
        else: value = None
        self.guard()
        return value, observed

    def read(self, reference, maximum=MAX_DOCUMENT_BYTES):
        path = _pin(reference, maximum, empty=False)
        return self._read(path, maximum, reference=reference)[0]

    def fixed(self, path, maximum=MAX_DOCUMENT_BYTES):
        return self._read(path, maximum)

    def blob(self, reference):
        return self._read(_pin(reference), reference['bytes'], reference=reference, json=False)[1]

    def payload(self, reference):
        """Retain the payload pin and identity; full content remains a separate gate."""
        path = _pin(reference)
        info = self._info(path)
        _need(info.st_size == reference['bytes'], 'PAYLOAD_CHANGED')
        record = (deepcopy(reference), self.signature(info))
        _need(path not in self.deferred or self.deferred[path] == record, 'PAYLOAD_CHANGED')
        self.deferred[path] = record

    def absent(self, path):
        self.guard(); path = _path(str(path))
        self.directory(path.parent, private=True)
        _need(not os.path.lexists(path), 'CLEANED_SQL_PRESENT')
        self.absent_paths.add(path)

    def unchanged(self):
        for path, (_, identity) in self.records.items():
            _need(self.signature(self._info(path)) == identity, 'FILE_CHANGED')
        for path, (_, identity) in self.deferred.items():
            _need(self.signature(self._info(path)) == identity, 'PAYLOAD_CHANGED')
        for path, identity in self.directories.items():
            self.guard(); info = _path(str(path)).stat()
            _need((info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode), info.st_uid) == identity,
                'DIRECTORY_CHANGED')
        for path, names in self.listings.items():
            self.guard()
            _need(tuple(sorted(item.name for item in path.iterdir())) == names, 'DIRECTORY_CHANGED')
        for path in self.absent_paths:
            self.guard(); _need(not os.path.lexists(path), 'CLEANED_SQL_PRESENT')
        self.guard()


def _scan_invocations(reader, roots):
    found, visited, pending = {}, set(), list(roots)
    entries = 0
    while pending:
        root = pending.pop()
        if root in visited: continue
        visited.add(root)
        for name in reader.listing(root):
            reader.guard(); entries += 1
            _need(entries <= MAX_DIRECTORY_ENTRIES, 'DIRECTORY_LIMIT')
            path = _path(str(root/name)); info = path.lstat()
            if stat.S_ISDIR(info.st_mode): pending.append(path)
            elif name.endswith('.json') and name != 'native-execution-evidence.json' and (
                    name.startswith('native-') or name.startswith('importer-')):
                value, reference = reader.fixed(path)
                found[str(path)] = (value, reference)
    return found


def _originals(owner, request, root, reader):
    request_contract(request)
    _need(request['action'] == 'RESTORE' and request['targetConfigRef'] is not None and
        request['recoveryPointRef'] is not None and root == _path(owner['operationsRoot'])/request['operationId'],
        'REQUEST_INVALID')
    reader.directory(root, private=True)
    configuration, configuration_pin = reader.fixed(root/'configuration.json')
    original_request, request_pin = reader.fixed(root/'request.json')
    operation, _ = reader.fixed(root/'operation.json')
    _need(configuration == owner and original_request == request and
        operation.get('operationId') == request['operationId'] and operation.get('requestPin') == request_pin and
        operation.get('configurationSha256') == digest(owner), 'ORIGINAL_CHANGED')
    target_ref = request['targetConfigRef']
    policies = owner.get('targetProgramPolicies')
    _need(type(policies) is dict and target_ref in policies, 'POLICY_REQUIRED')
    policy = validate_policy(policies[target_ref])
    baseline = reader.read(policy['baselineTargetPin'])
    _need(policy['targetConfigRef'] == target_ref and owner['targets'][target_ref] == baseline and
        'mainApplication' in baseline and owner.get('targetBackupEpochPolicies', {}).get(target_ref) ==
        policy['backupEpochPolicy'] and baseline['replacement'].get('backupEpoch', policy['backupEpochPolicy']) ==
        policy['backupEpochPolicy'], 'POLICY_BINDING_INVALID')
    claim = _path(baseline['replacement']['stateRoot'])/request['operationId']
    reader.directory(claim, private=True)
    reservation, reservation_pin = reader.fixed(root/'resource-reservation.json')
    expected = dict(operationId=request['operationId'], targetConfigRef=target_ref,
        configurationSha256=digest(owner), machineId=baseline['machineId'], operationRoot=str(root))
    _need(reservation.get('schemaVersion') == 'RestoreHostReservation/v1' and
        all(type(reservation.get(k)) is type(v) and reservation[k] == v for k, v in expected.items()),
        'RESERVATION_INVALID')
    return dict(root=root, claim=claim, policy=policy, baseline=baseline,
        source=configuration['sources'][request['sourceConfigRef']],
        configurationPin=configuration_pin, requestPin=request_pin, reservationPin=reservation_pin)


def _outer(request, inputs, reference, reader):
    root, claim = inputs['root'], inputs['claim']
    _need(_pin(reference, MAX_NATIVE_BYTES, empty=False) in (root/'worker-result.json', root/'result.json'),
        'RESULT_LOCATION_INVALID')
    result = reader.read(reference, MAX_NATIVE_BYTES)
    _need(type(result) is dict and result.get('schemaVersion') == 'backup-restore-operation-result/v1' and
        result.get('operationId') == result.get('requestId') == request['operationId'] and
        result.get('action') == 'RESTORE' and type(result.get('data')) is dict and
        type(result.get('actualExitCode')) is int and _text(result.get('finishedAt')),
        'RESULT_INVALID')
    state, code = result.get('state'), result['actualExitCode']
    _need((state == 'SUCCEEDED' and code == 0 and result.get('failureCode') is None) or
        (state == 'FAILED_RETAINED' and code == 1 and _text(result.get('failureCode'))) or
        (state == 'TERMINAL_UNKNOWN' and code == 2 and _text(result.get('failureCode'))), 'RESULT_TERMINAL_INVALID')
    data = result['data']; receipt_pin = data['replacementReceiptPin']
    _need(_pin(receipt_pin) == claim/'replacement-result.json', 'RECEIPT_LOCATION_INVALID')
    receipt = reader.read(receipt_pin)
    _need(type(receipt) is dict and receipt.get('state') in ('SUCCEEDED', 'FAILED_RETAINED') and
        receipt.get('operationId') == request['operationId'] and
        receipt.get('targetConfigRef') == request['targetConfigRef'] and
        receipt.get('databaseUuid') == inputs['policy']['backupEpochPolicy']['databaseUuid'] and
        _text(receipt.get('finishedAt')) and all(k in data and k in receipt and data[k] == receipt[k] for k in COMMON),
        'RECEIPT_BINDING_INVALID')
    _need(data['programExecutionPhase'] in ('NOT_STARTED', 'PREPARATION', 'RESTORE'), 'PHASE_INVALID')
    _need(state != 'SUCCEEDED' or receipt['state'] == 'SUCCEEDED', 'RESULT_RECEIPT_CONFLICT')
    if receipt['state'] == 'FAILED_RETAINED': _need(_text(receipt.get('failureCode')), 'FAILURE_CODE_REQUIRED')
    for item in (data, receipt):
        _need(type(item.get('mutationDispatched')) is bool and type(item.get('terminalUnknown')) is bool,
            'RESULT_SUMMARY_INVALID')
    return result, receipt, _index(result['originalResultPins']), _index(receipt['originalResultPins'])


def _execution(request, inputs, native, generation_pin, reader):
    policy, claim = inputs['policy'], inputs['claim']
    binding_pin = native['bindingPin']
    _need(_pin(binding_pin) == claim/'program-execution-binding.json', 'BINDING_LOCATION_INVALID')
    binding = reader.read(binding_pin)
    _need(type(binding) is dict and set(binding) == BINDING_FIELDS and
        binding['schemaVersion'] == 'MainProgramExecutionBinding/v1' and
        binding['operationId'] == request['operationId'] and binding['targetConfigRef'] == request['targetConfigRef'] and
        binding['policySha256'] == digest(policy) and
        all(binding[k] == inputs[k] for k in ('configurationPin', 'requestPin', 'reservationPin')),
        'BINDING_INVALID')
    context_pin = binding['contextPin']
    _need(_pin(context_pin) == claim/'program-context.json', 'CONTEXT_LOCATION_INVALID')
    context = reader.read(context_pin)
    _need(type(context) is dict and set(context) == CONTEXT_FIELDS and
        context['schemaVersion'] == 'MainProgramRestoreContext/v1' and context['operationId'] == request['operationId'] and
        context['policySha256'] == digest(policy) and type(context['readyEpoch']) is dict and
        type(context['evidencePins']) is list, 'CONTEXT_INVALID')
    epoch_policy = policy['backupEpochPolicy']
    tail = read_current(epoch_policy, guard=reader.guard)
    historical = _resolve_at_ready(policy, context['readyEpoch']['eventPin'], reader.read, reader.guard)
    _need(context['readyEpoch'] == historical['epoch'] and context['targetPin'] == historical['targetPin'] and
        context['parentGenerationPin'] == historical['generationPin'] and context['capturePins'] == historical['captures'],
        'CONTEXT_INVALID')
    expected = [p for p in historical['evidence'] if p != tail['eventPin'] or p == context['readyEpoch']['eventPin']]
    _need(len(context['evidencePins']) == len(expected) and all(p in context['evidencePins'] for p in expected),
        'CONTEXT_INVALID')
    for reference in context['evidencePins']: reader.read(reference)
    ready_pin = context['readyEpoch']['eventPin']; ready = reader.read(ready_pin)
    started, started_pin = reader.fixed(Path(epoch_policy['root'])/('%020d.json' % (ready['sequence']+1)))
    _need(started.get('kind') == 'RESTORE_STARTED' and started.get('state') == 'REPLACING' and
        started.get('operationId') == request['operationId'] and started.get('previousSha256') == ready_pin['sha256'],
        'EPOCH_BINDING_INVALID')
    intent = reader.read(started['evidencePin'])
    _need(intent.get('schemaVersion') == 'ReplacementBackupEpochIntent/v1' and
        intent.get('operationId') == request['operationId'] and intent.get('targetConfigRef') == request['targetConfigRef'] and
        intent.get('databaseUuid') == epoch_policy['databaseUuid'] and
        _path(intent['replacementReceiptPath']) == claim/'replacement-result.json', 'EPOCH_INTENT_INVALID')
    ended = Path(epoch_policy['root'])/('%020d.json' % (ready['sequence']+2))
    operation_epoch = dict(state='REPLACING', epochId=started['epochId'], eventPin=started_pin)
    if ended.exists():
        terminal, terminal_pin = reader.fixed(ended)
        _, receipt_pin = reader.fixed(claim/'replacement-result.json')
        _need(terminal.get('kind') == 'RESTORE_FINISHED' and terminal.get('operationId') == request['operationId'] and
            terminal.get('epochId') == started['epochId'] and terminal.get('evidencePin') == receipt_pin,
            'EPOCH_RECEIPT_INVALID')
        operation_epoch.update(state=terminal['state'], eventPin=terminal_pin)
    target, target_pin = historical['target'], historical['targetPin']
    generation = None
    if generation_pin is not None:
        _need(_pin(generation_pin) == claim/'generation.json', 'GENERATION_LOCATION_INVALID')
        generation = reader.read(generation_pin)
        _need(type(generation) is dict and set(generation) == GENERATION_FIELDS and
            generation['schemaVersion'] == 'MainProgramGeneration/v1' and generation['operationId'] == request['operationId'] and
            generation['epochId'] == started['epochId'] and generation['targetConfigRef'] == request['targetConfigRef'] and
            generation['policySha256'] == digest(policy) and generation['baselineTargetPin'] == policy['baselineTargetPin'] and
            generation['parentGenerationPin'] == context['parentGenerationPin'], 'GENERATION_INVALID')
        target_pin = generation['targetPin']; target = reader.read(target_pin)
        _target_transition(historical['target'], target, generation['switchResultPin'], request['operationId'], reader.read)
        _need(type(generation['captureBindings']) is dict and
            set(generation['captureBindings']) == set(policy['captureConfigurationPins']), 'CAPTURE_BINDINGS_INVALID')
        for source_ref, base_pin in policy['captureConfigurationPins'].items():
            entry = generation['captureBindings'][source_ref]
            _need(type(entry) is dict and set(entry) == {'baseCapturePin', 'capturePin'} and
                entry['baseCapturePin'] == base_pin, 'CAPTURE_BINDINGS_INVALID')
            _capture_transition(reader.read(base_pin), reader.read(entry['capturePin']), inputs['baseline'],
                target, source_ref, epoch_policy, reader.read)
    else: _need(not os.path.lexists(claim/'generation.json'), 'GENERATION_REQUIRED')
    _need(read_current(epoch_policy, guard=reader.guard) == tail, 'EPOCH_CHANGED')
    return dict(bindingPin=binding_pin, contextPin=context_pin, generation=generation, target=target,
        targetPin=target_pin, previousTarget=historical['target'], epoch=operation_epoch,
        startedEpoch=_snapshot(started, started_pin))


def _sql_cleanup(request, inputs, data, receipt, outer, reader):
    """Accept missing SQL only from this operation's complete deletion proof."""
    from recovery_program_sql_staging import INTENT_NAME, RESULT_NAME, IDENTITY_FIELDS, MAX_ENTRIES, cleanup_relative
    root = inputs['root']; reference = data.get('programSqlCleanupPin')
    _need(reference == receipt.get('programSqlCleanupPin'), 'SQL_CLEANUP_BINDING_INVALID')
    if reference is None:
        _need(not os.path.lexists(root/INTENT_NAME) and not os.path.lexists(root/RESULT_NAME),
            'SQL_CLEANUP_REQUIRED')
        return {}
    _need(_pin(reference, MAX_DOCUMENT_BYTES, empty=False) == root/RESULT_NAME and
        outer.get(str(root/RESULT_NAME)) == reference and data['programExecutionPhase'] == 'RESTORE' and
        data['programGenerationPin'] is not None, 'SQL_CLEANUP_LOCATION_INVALID')
    result = reader.read(reference)
    _need(type(result) is dict and set(result) == {'schemaVersion', 'state', 'operationId',
        'intentPin', 'deletedSqlPins', 'finishedAt'} and
        result['schemaVersion'] == 'MainSqlStagingCleanup/v1' and result['state'] == 'SUCCEEDED' and
        result['operationId'] == request['operationId'] and _text(result['finishedAt']) and
        _pin(result['intentPin'], MAX_DOCUMENT_BYTES, empty=False) == root/INTENT_NAME and
        outer.get(str(root/INTENT_NAME)) == result['intentPin'], 'SQL_CLEANUP_RESULT_INVALID')
    intent = reader.read(result['intentPin'])
    native = reader.read(data['programNativeEvidencePin'], MAX_NATIVE_BYTES)
    _need(type(intent) is dict and set(intent) == {'schemaVersion', 'state', 'operationId', 'bindingPin',
        'generationPin', 'operationRoot', 'entries', 'startedAt'} and
        intent['schemaVersion'] == 'MainSqlStagingCleanupIntent/v1' and intent['state'] == 'PLANNED' and
        intent['operationId'] == request['operationId'] and _path(intent['operationRoot']) == root and
        intent['bindingPin'] == native['bindingPin'] and intent['generationPin'] == data['programGenerationPin'] and
        native['generationPin'] == intent['generationPin'] and _text(intent['startedAt']) and
        type(intent['entries']) is list and 0 < len(intent['entries']) <= MAX_ENTRIES,
        'SQL_CLEANUP_INTENT_INVALID')
    sql_rows = [row for row in native['invocations']
        if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2']
    _need(len(sql_rows) == len(intent['entries']) and
        result['deletedSqlPins'] == [entry['sqlPin'] for entry in intent['entries']], 'SQL_CLEANUP_COVERAGE_INVALID')
    cleaned = {}
    for entry, row in zip(intent['entries'], sql_rows):
        reader.guard()
        _need(type(entry) is dict and set(entry) == {'sqlPin', 'importerPin', 'fileIdentity'}, 'SQL_CLEANUP_ENTRY_INVALID')
        path = _pin(entry['sqlPin']); cleanup_relative(root, path)
        identity = entry['fileIdentity']
        _need(type(identity) is dict and set(identity) == IDENTITY_FIELDS and
            all(type(value) is int and value >= 0 for value in identity.values()) and identity['inode'] > 0 and
            stat.S_ISREG(identity['mode']) and stat.S_IMODE(identity['mode']) == 0o600 and
            identity['uid'] == os.geteuid() and identity['links'] == 1 and
            identity['bytes'] == entry['sqlPin']['bytes'], 'SQL_CLEANUP_IDENTITY_INVALID')
        _need(str(path) not in cleaned and row['phase'] == 'RESTORE' and
            row['intentObservation']['sqlPin'] == entry['sqlPin'] and
            row['terminalPin'] == entry['importerPin'] and row['terminalPin'] is not None,
            'SQL_CLEANUP_IMPORTER_INVALID')
        terminal = reader.read(entry['importerPin'])
        _need(row['terminalObservation'] == terminal and terminal.get('schemaVersion') == 'RecoverySqlImporter/v2' and
            terminal.get('operationId') == request['operationId'] and terminal.get('mutation') is True and
            terminal.get('action') in ('DATABASE_FULL', 'DATABASE_INCREMENTAL') and
            terminal.get('sqlPin') == entry['sqlPin'] and terminal.get('state') == 'SUCCEEDED' and
            type(terminal.get('actualExitCode')) is int and terminal['actualExitCode'] == 0,
            'SQL_CLEANUP_IMPORTER_INVALID')
        reader.absent(path); cleaned[str(path)] = entry['sqlPin']
    return cleaned


def _native(request, inputs, reference, phase, generation_pin, result_state, found, reader, cleaned):
    _need(_pin(reference, MAX_NATIVE_BYTES, empty=False) == inputs['claim']/'native-execution-evidence.json',
        'NATIVE_LOCATION_INVALID')
    value = reader.read(reference, MAX_NATIVE_BYTES)
    _need(type(value) is dict and set(value) == NATIVE_FIELDS and
        value['schemaVersion'] == 'MainNativeExecutionEvidence/v1' and value['operationId'] == request['operationId'] and
        value['phase'] == phase and type(value['invocations']) is list, 'NATIVE_INVALID')
    if phase == 'RESTORE':
        _need(generation_pin is not None and value['generationPin'] == generation_pin, 'NATIVE_GENERATION_INVALID')
    else:
        _need(phase == 'PREPARATION' and value['generationPin'] is None and result_state != 'SUCCEEDED',
            'NATIVE_GENERATION_INVALID')
    paths, pins, mutation, unknown, last, restore_seen = set(), [], False, False, None, False
    for sequence, row in enumerate(value['invocations']):
        reader.guard()
        _need(type(row) is dict and type(row.get('sequence')) is int and row['sequence'] == sequence and
            row.get('phase') in ('PREPARATION', 'RESTORE') and
            not (restore_seen and row['phase'] == 'PREPARATION') and
            (phase == 'RESTORE' or row['phase'] == 'PREPARATION'), 'INVOCATION_ORDER_INVALID')
        _need(not unknown, 'INVOCATION_AFTER_UNKNOWN')
        restore_seen |= row['phase'] == 'RESTORE'
        intent, dispatch = row['intentObservation'], row['intentPinAtDispatch']
        path = _pin(dispatch, MAX_DOCUMENT_BYTES, empty=False)
        _need((inputs['root'] in path.parents or inputs['claim'] in path.parents) and path not in paths,
            'INVOCATION_LOCATION_INVALID')
        _need(not (inputs['root']/'replacement-preparation' in path.parents and row['phase'] != 'PREPARATION') and
            not (inputs['claim']/'runtime' in path.parents and row['phase'] != 'RESTORE'), 'INVOCATION_PHASE_INVALID')
        paths.add(path)
        _need(type(intent) is dict and len(canonical(intent)) == dispatch['bytes'] and digest(intent) == dispatch['sha256'],
            'INVOCATION_INTENT_CHANGED')
        actions = ('RESTORE',) if row['phase'] == 'PREPARATION' else RESTORE_ACTIONS
        _need(intent.get('schemaVersion') in ('RecoveryDataInvocation/v1', 'RecoverySqlImporter/v2') and
            intent.get('operationId') == request['operationId'] and intent.get('action') in actions and
            type(intent.get('mutation')) is bool and _text(intent.get('startedAt')) and
            type(intent.get('argvSha256')) is str and re.fullmatch('[0-9a-f]{64}', intent['argvSha256']) and
            intent.get('actualExitCode') is None and intent.get('finishedAt') is None and
            intent.get('state') == 'TERMINAL_UNKNOWN', 'INVOCATION_INTENT_INVALID')
        identity = ('schemaVersion', 'operationId', 'action', 'argvSha256', 'mutation', 'startedAt')
        if intent['schemaVersion'] == 'RecoverySqlImporter/v2':
            _need(intent['mutation'] is True, 'SQL_INTENT_INVALID')
            path_key = str(_pin(intent['sqlPin']))
            if path_key in cleaned:
                _need(cleaned[path_key] == intent['sqlPin'], 'SQL_CLEANUP_PIN_INVALID')
            else: reader.payload(intent['sqlPin'])
            identity += ('sqlPin',)
        mutation |= intent['mutation']
        terminal_pin = row.get('terminalPin')
        if terminal_pin is None:
            _need('terminalObservation' not in row and str(path) in found and
                found[str(path)] == (intent, dispatch), 'INVOCATION_PENDING_INVALID')
            unknown, last = True, None
        else:
            _need(_pin(terminal_pin) == path and str(path) in found and found[str(path)][1] == terminal_pin,
                'INVOCATION_TERMINAL_LOCATION_INVALID')
            terminal = reader.read(terminal_pin)
            _need(row.get('terminalObservation') == terminal and all(type(terminal.get(k)) is type(intent[k]) and
                terminal[k] == intent[k] for k in identity), 'INVOCATION_IDENTITY_INVALID')
            code, state = terminal.get('actualExitCode'), terminal.get('state')
            _need(_text(terminal.get('finishedAt')) and (code is None or type(code) is int) and
                state in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN') and
                (state != 'SUCCEEDED' or code == 0) and
                (state != 'FAILED_RETAINED' or type(code) is int), 'INVOCATION_TERMINAL_INVALID')
            unknown |= state == 'TERMINAL_UNKNOWN'; last = code; pins.append(terminal_pin)
    _need({str(path) for path in paths} == set(found), 'INVOCATION_COVERAGE_INVALID')
    _need(value['originalResultPins'] == pins and type(value['mutationDispatched']) is bool and
        value['mutationDispatched'] == mutation and type(value['terminalUnknown']) is bool and
        value['terminalUnknown'] == unknown and type(value['lastExitCode']) is type(last) and
        value['lastExitCode'] == last, 'NATIVE_SUMMARY_INVALID')
    if result_state == 'SUCCEEDED':
        _need(not unknown and all(row['terminalObservation']['state'] == 'SUCCEEDED' and
            row['terminalObservation']['actualExitCode'] == 0 for row in value['invocations']), 'NATIVE_SUCCESS_INVALID')
    return value


def _journal(reader, root, allowed, outer):
    if not os.path.lexists(root): return {}
    reader.directory(root, private=True)
    result = {}
    for name in reader.listing(root):
        _need(name in allowed, 'JOURNAL_FILE_INVALID')
        value, reference = reader.fixed(root/name)
        _need(outer.get(str(root/name)) == reference, 'JOURNAL_PIN_REQUIRED')
        result[name] = (value, reference)
    return result


def _protection(request, inputs, reference, target, success, outer, reader):
    claim, operation = inputs['claim'], request['operationId']
    if reference is None:
        _need(not success and all(not os.path.lexists(claim/name) for name in JOURNALS.values()),
            'CUSTODY_REQUIRED')
        return None
    _need(_pin(reference) == claim/'protection-custody-evidence.json', 'CUSTODY_LOCATION_INVALID')
    value = reader.read(reference)
    _need(type(value) is dict and set(value) == {'schemaVersion', 'operationId', 'state', 'protections', 'originalResultPins'} and
        value['schemaVersion'] == 'MainProgramProtectionCustody/v1' and value['operationId'] == operation and
        value['state'] in ('ACTIVE', 'RELEASED', 'FAILED_RETAINED') and
        type(value['protections']) is dict and set(value['protections']) == set(KINDS), 'CUSTODY_INVALID')
    custody_pins = _index(value['originalResultPins'])
    main = target['mainApplication']
    endpoints = [item for item in main.get('publishedDataEndpoints', []) if item.get('role') == 'minio']
    _need(len(endpoints) <= 1, 'PROTECTION_SCOPE_INVALID')
    archive_configuration = select_configuration(target, inputs['source'])
    configurations = dict(archive=archive_configuration,
        fence=endpoints[0].get('writeFence') if endpoints else None, scheduler=target)
    expected_inputs = _index(list(_references([target['secrets'], archive_configuration,
        main.get('publishedDataEndpoints', [])])))
    for path, item in expected_inputs.items():
        _need(custody_pins.get(path) == item, 'CUSTODY_INPUT_REQUIRED'); reader.blob(item)
    expected_paths = set(expected_inputs)
    for kind in KINDS:
        reader.guard(); step = value['protections'][kind]; configuration = configurations[kind]
        _need(type(step) is dict and step.get('state') in
            ('ABSENT', 'NOT_INSTALLED', 'INSTALLED', 'RELEASED', 'FAILED_RETAINED'), 'PROTECTION_STATE_INVALID')
        state = step['state']; root = claim/JOURNALS[kind]
        journal = _journal(reader, root, FILES[kind], custody_pins)
        expected_paths.update(str(root/name) for name in journal)
        if configuration is None:
            _need(state == 'ABSENT' and not journal and not os.path.lexists(root), 'PROTECTION_ABSENT_INVALID')
            continue
        _need(state != 'ABSENT', 'PROTECTION_REQUIRED')
        if state == 'NOT_INSTALLED': _need(not journal and not os.path.lexists(root), 'PROTECTION_STATE_INVALID')
        if state == 'FAILED_RETAINED':
            _need(value['state'] == 'FAILED_RETAINED' and step.get('failedMethod') in
                ('preflight', 'install', 'verify', 'release') and _text(step.get('errorCode')), 'PROTECTION_FAILURE_INVALID')
        if kind == 'scheduler':
            binding = digest(dict(database=target['database'], databaseUuid=target['replacement']['databaseUuid'],
                mysql=[s for s in target['services'] if s['role'] == 'mysql'], mainApplication=main))
            schemas = ('MainMysqlSchedulerIntent/v1', 'MainMysqlSchedulerActive/v1', 'MainMysqlSchedulerRelease/v1')
        elif kind == 'archive':
            binding = digest(configuration)
            schemas = ('ArchiveViewProtectionIntent/v1', 'ArchiveViewProtectionActive/v1', 'ArchiveViewProtectionRelease/v1')
        else:
            binding = digest(configuration)
            schemas = ('PublishedHostWriteFenceIntent/v1', 'PublishedHostWriteFenceActive/v1', 'PublishedHostWriteFenceRelease/v1')
        for name, schema in zip(('intent.json', 'active.json', 'released.json'), schemas):
            if name not in journal: continue
            record, _ = journal[name]
            _need(record.get('schemaVersion') == schema and record.get('operationId') == operation,
                'PROTECTION_BINDING_INVALID')
            if name != 'released.json' or kind == 'scheduler':
                _need(record.get('configurationDigest') == binding, 'PROTECTION_BINDING_INVALID')
        if state in ('INSTALLED', 'RELEASED'):
            _need({'intent.json', 'active.json'} <= set(journal), 'PROTECTION_JOURNAL_INCOMPLETE')
        if state == 'INSTALLED': _need('released.json' not in journal, 'PROTECTION_STATE_INVALID')
        if state == 'RELEASED':
            _need('released.json' in journal and step.get('releasePin') == journal['released.json'][1],
                'PROTECTION_RELEASE_INVALID')
            released = journal['released.json'][0]
            flag = {'archive': 'originalMountRestored', 'fence': 'originalRulesPreserved',
                'scheduler': 'originalStateRestored'}[kind]
            _need(released.get(flag) is True, 'PROTECTION_RELEASE_INVALID')
        if kind == 'scheduler' and 'intent.json' in journal:
            intent, intent_pin = journal['intent.json']
            original = intent.get('originalState'); paused = 'DISABLED' if original == 'DISABLED' else 'OFF'
            _need(original in ('ON', 'OFF', 'DISABLED') and intent.get('pausedState') == paused,
                'SCHEDULER_INTENT_INVALID')
            if 'active.json' in journal:
                active, active_pin = journal['active.json']
                _need(active.get('intentPin') == intent_pin and active.get('pausedState') == paused,
                    'SCHEDULER_ACTIVE_INVALID')
                for name in ('release-intent.json', 'released.json', 'recovery-custody.json'):
                    if name not in journal: continue
                    record = journal[name][0]
                    _need(record.get('operationId') == operation and record.get('activePin') == active_pin and
                        record.get('originalState') == original, 'SCHEDULER_RELEASE_INVALID')
                    if name != 'release-intent.json':
                        _need(record.get('intentPin') == intent_pin and record.get('configurationDigest') == binding,
                            'SCHEDULER_RELEASE_INVALID')
            else: _need(not {'release-intent.json', 'released.json', 'recovery-custody.json'} & set(journal),
                'SCHEDULER_JOURNAL_INCOMPLETE')
        elif kind == 'archive' and 'active.json' in journal:
            readonly = deepcopy(configuration['mountIdentity'])
            readonly['options'] = ['ro' if entry == 'rw' else entry for entry in readonly['options']]
            _need(journal['active.json'][0].get('observedMountDigest') == digest(readonly), 'ARCHIVE_ACTIVE_INVALID')
    _need(set(custody_pins) == expected_paths, 'CUSTODY_COVERAGE_INVALID')
    if value['state'] == 'FAILED_RETAINED':
        _need(any(step['state'] == 'FAILED_RETAINED' for step in value['protections'].values()), 'CUSTODY_STATE_INVALID')
    if value['state'] == 'RELEASED' or success:
        _need(value['state'] == 'RELEASED' and all(step['state'] in ('ABSENT', 'RELEASED')
            for step in value['protections'].values()), 'CUSTODY_NOT_RELEASED')
    return value


def _switch(request, inputs, generation, previous_target, outer, reader, *, complete):
    root = inputs['claim']/'program-switch'
    if not os.path.lexists(root):
        _need(generation is None or generation['switchResultPin'] is None, 'SWITCH_JOURNAL_REQUIRED')
        return False, False
    names = reader.listing(root)
    allowed = {'intent.json', 'result.json', 'failure.json', 'frontend-created-observation.json',
        'backend-created-observation.json', 'frontend-verified.json', 'backend-verified.json'}
    allowed.update(n for n in names if re.fullmatch('[0-9]{4}-(intent|result)\\.json', n))
    journal = _journal(reader, root, allowed, outer)
    if not journal:
        _need(not complete, 'SWITCH_SUCCESS_INCOMPLETE')
        return False, False
    _need('intent.json' in journal, 'SWITCH_INTENT_REQUIRED')
    intent, intent_pin = journal['intent.json']
    _need(intent.get('schemaVersion') == 'MainProgramSwitchIntent/v1' and
        intent.get('operationId') == request['operationId'] and set(intent.get('originals', {})) == {'frontend', 'backend'} and
        set(intent.get('requests', {})) == {'frontend', 'backend'}, 'SWITCH_INTENT_INVALID')
    from recovery_main_target import service_configuration_digest
    services = {entry['role']: entry for entry in previous_target['services']}
    expected = []
    for role in ('frontend', 'backend'):
        original = intent['originals'][role]; planned = intent['requests'][role]
        _need(original['Id'] == services[role]['id'] and original['Image'] == services[role]['imageId'] and
            service_configuration_digest(original) == previous_target['mainApplication']['serviceConfigurationDigests'][role],
            'SWITCH_TARGET_INVALID')
        expected.append(('rename', original, None, None))
        for network in original['NetworkSettings']['Networks'].values():
            expected.append(('exact', '/networks/'+network['NetworkID']+'/disconnect',
                digest(dict(Container=original['Id'], Force=False)), None))
        body = dict(planned['Config'], HostConfig=planned['HostConfig'], NetworkingConfig=planned['NetworkingConfig'])
        expected.append(('create', original, digest(body), role))
    attempts = sorted(int(name[:4]) for name in journal if re.fullmatch('[0-9]{4}-intent\\.json', name))
    results = {int(name[:4]) for name in journal if re.fullmatch('[0-9]{4}-result\\.json', name)}
    _need(attempts == list(range(1, len(attempts)+1)) and len(attempts) <= len(expected) and results <= set(attempts),
        'SWITCH_SEQUENCE_INVALID')
    unknown = False
    for sequence in attempts:
        attempt, attempt_pin = journal['%04d-intent.json' % sequence]
        kind, target, checksum, role = expected[sequence-1]
        _need(attempt.get('method') == 'POST' and attempt.get('bodySha256') == checksum and
            _text(attempt.get('startedAt')) and type(attempt.get('path')) is str, 'SWITCH_REQUEST_INVALID')
        path = urlsplit(attempt['path']); query = parse_qs(path.query, strict_parsing=True)
        if kind == 'exact': _need(attempt['path'] == target, 'SWITCH_REQUEST_INVALID')
        elif kind == 'rename':
            _need(not path.scheme and not path.netloc and not path.fragment and
                path.path == '/containers/'+target['Id']+'/rename' and set(query) == {'name'} and
                len(query['name']) == 1 and query['name'][0].startswith(target['Name'][1:]+'-retained-'),
                'SWITCH_REQUEST_INVALID')
        else:
            _need(not path.scheme and not path.netloc and not path.fragment and path.path == '/containers/create' and
                query == {'name': [target['Name'][1:]]}, 'SWITCH_REQUEST_INVALID')
        if sequence not in results:
            _need(sequence == attempts[-1] and 'result.json' not in journal, 'SWITCH_RESULT_REQUIRED')
            unknown = True
        else:
            result = journal['%04d-result.json' % sequence][0]
            _need(result.get('intentPin') == attempt_pin and _text(result.get('finishedAt')), 'SWITCH_RESULT_INVALID')
            if kind == 'create':
                created = result.get('result')
                _need(type(created) is dict and type(created.get('Id')) is str and
                    re.fullmatch('[0-9a-f]{64}', created['Id']) and not created.get('Warnings'), 'SWITCH_CREATE_INVALID')
                if role+'-verified.json' in journal:
                    _need(journal[role+'-verified.json'][0]['created']['Id'] == created['Id'], 'SWITCH_CREATE_INVALID')
    if 'result.json' in journal:
        result, result_pin = journal['result.json']
        _need('failure.json' not in journal and len(attempts) == len(expected) and not unknown and
            result.get('schemaVersion') == 'MainProgramSwitchResult/v1' and result.get('state') == 'CREATED_STOPPED' and
            result.get('operationId') == request['operationId'] and result.get('intentPin') == intent_pin and
            set(result.get('applicationPins', {})) == {'frontend', 'backend'}, 'SWITCH_SUCCESS_INVALID')
        for role in ('frontend', 'backend'):
            _need(role+'-verified.json' in journal and role+'-created-observation.json' in journal and
                result['applicationPins'][role] == journal[role+'-verified.json'][1] and
                journal[role+'-verified.json'][0]['original'] == intent['originals'][role] and
                journal[role+'-verified.json'][0]['created'] == journal[role+'-created-observation.json'][0],
                'SWITCH_APPLICATION_INVALID')
        _need(generation is None or generation['switchResultPin'] == result_pin, 'SWITCH_GENERATION_INVALID')
    elif 'failure.json' in journal:
        failure = journal['failure.json'][0]
        _need(failure.get('schemaVersion') == 'MainProgramSwitchFailure/v1' and
            failure.get('state') == 'FAILED_RETAINED' and failure.get('operationId') == request['operationId'] and
            failure.get('intentPin') == intent_pin and type(failure.get('attemptedMutations')) is int and
            failure['attemptedMutations'] == len(attempts) and _text(failure.get('failureCode')), 'SWITCH_FAILURE_INVALID')
    elif attempts: unknown = True
    _need(not complete or 'result.json' in journal, 'SWITCH_SUCCESS_INCOMPLETE')
    return bool(attempts), unknown


def _image_import(request, inputs, epoch, outer, reader, *, complete):
    root = inputs['claim']/'program-import'
    if not os.path.lexists(root): return False, False
    names = reader.listing(root)
    _need(set(names) <= {'preparation.json', 'images.tar', 'load-intent.json', 'load-result.json', 'load-failure.json'},
        'IMPORT_JOURNAL_INVALID')
    journal = {}
    for name in names:
        if name == 'images.tar': continue
        value, reference = reader.fixed(root/name)
        _need(outer.get(str(root/name)) == reference, 'IMPORT_PIN_REQUIRED')
        journal[name] = (value, reference)
    if 'preparation.json' not in journal:
        _need(not journal and not complete, 'IMPORT_PREPARATION_REQUIRED')
        return False, False
    plan, preparation_pin = journal['preparation.json']
    _need(plan.get('schemaVersion') == 'MainProgramImageImport/v1' and
        plan['archiveProgram'].get('schemaVersion') == 'ArchivedProgramImages/v1' and
        _pin(plan['importPin']) == root/'images.tar', 'IMPORT_PREPARATION_INVALID')
    reader.payload(plan['importPin'])
    if 'load-intent.json' not in journal:
        _need(not {'load-result.json', 'load-failure.json'} & set(journal) and not complete, 'IMPORT_INTENT_REQUIRED')
        return False, False
    intent, intent_pin = journal['load-intent.json']
    _need(intent.get('schemaVersion') == 'MainProgramImageLoadIntent/v1' and
        intent.get('operationId') == request['operationId'] and intent.get('preparationPin') == preparation_pin and
        intent.get('epoch') == epoch, 'IMPORT_INTENT_INVALID')
    if 'load-result.json' in journal:
        result = journal['load-result.json'][0]
        _need('load-failure.json' not in journal and result.get('schemaVersion') == 'MainProgramImageLoadResult/v1' and
            result.get('state') == 'LOADED' and result.get('operationId') == request['operationId'] and
            result.get('intentPin') == intent_pin and result.get('preparationPin') == preparation_pin and
            result.get('epoch') == intent['epoch'], 'IMPORT_RESULT_INVALID')
        images = plan['archiveProgram']['images']
        _need(set(result['images']) == {image['imageId'] for image in images}, 'IMPORT_IMAGES_INVALID')
        for image in images:
            observed = result['images'][image['imageId']]
            _need(observed['Id'] == image['imageId'] and observed['Os'] == image['os'] and
                observed['Architecture'] == image['architecture'] and observed['RootFS']['Type'] == 'layers' and
                observed['RootFS']['Layers'] == image['diffIds'], 'IMPORT_IMAGES_INVALID')
        return True, False
    if 'load-failure.json' in journal:
        failure = journal['load-failure.json'][0]
        _need(failure.get('schemaVersion') == 'MainProgramImageLoadFailure/v1' and
            failure.get('operationId') == request['operationId'] and failure.get('intentPin') == intent_pin and
            failure.get('state') in ('FAILED_RETAINED', 'TERMINAL_UNKNOWN') and _text(failure.get('failureCode')),
            'IMPORT_FAILURE_INVALID')
        _need(not complete, 'IMPORT_SUCCESS_INCOMPLETE')
        return True, failure['state'] == 'TERMINAL_UNKNOWN'
    _need(not complete, 'IMPORT_SUCCESS_INCOMPLETE')
    return True, True


def _not_started(inputs, data, result, receipt, found, reader):
    claim = inputs['claim']
    _need(result['state'] == receipt['state'] == 'FAILED_RETAINED' and not found and
        all(data[k] is None for k in COMMON[1:]) and
        data['mutationDispatched'] is receipt['mutationDispatched'] is False and
        data['terminalUnknown'] is receipt['terminalUnknown'] is False, 'NOT_STARTED_INVALID')
    forbidden = ['program-context.json', 'program-execution-binding.json', 'generation.json',
        'native-execution-evidence.json', 'protection-custody-evidence.json',
        'program-switch', 'program-import', *JOURNALS.values()]
    _need(all(not os.path.lexists(claim/name) for name in forbidden) and
        not os.path.lexists(inputs['root']/'replacement-preparation/replacement-intent.json'), 'NOT_STARTED_UNPROVEN')
    return dict(bindingPin=None, contextPin=None, generation=None, target=inputs['baseline'],
        targetPin=inputs['policy']['baselineTargetPin'], epoch=None)


def validate_program_evidence(owner, request, operation_root, *, result_pin, guard=None):
    """Return verified historical facts only; the caller retains all live gates.

    ``deferredPayloadPins`` identifies SQL/image content whose separate existing
    verification is required; no large payload is interpreted as JSON here.
    A valid ``terminalUnknown`` result is retained uncertainty, never permission
    to release exclusion, retry mutation, or start an application.
    """
    guard = (lambda: None) if guard is None else guard
    _need(callable(guard), 'GUARD_INVALID')
    try:
        guard(); root = _path(str(operation_root))
        # Validate the policy-selected claim before using it as a private root.
        target = owner['targets'][request['targetConfigRef']]
        claim = _path(target['replacement']['stateRoot'])/request['operationId']
        reader = _Reader(guard, (root, claim))
        inputs = _originals(owner, request, root, reader)
        result, receipt, result_pins, receipt_pins = _outer(request, inputs, result_pin, reader)
        data = result['data']; phase = data['programExecutionPhase']
        outer = _index([*result_pins.values(), *receipt_pins.values()])
        found = _scan_invocations(reader, (root, claim))
        cleaned = _sql_cleanup(request, inputs, data, receipt, outer, reader)
        native = custody = None
        unknown_causes = dict(native=False, programSwitch=False, programImport=False, outerConservative=False)
        if phase == 'NOT_STARTED':
            execution = _not_started(inputs, data, result, receipt, found, reader)
            mutation = unknown = False; invocations = []; last = None
        else:
            _need(data['programNativeEvidencePin'] is not None, 'NATIVE_REQUIRED')
            native = _native(request, inputs, data['programNativeEvidencePin'], phase,
                data['programGenerationPin'], receipt['state'] if receipt['state'] == 'SUCCEEDED' else result['state'],
                found, reader, cleaned)
            execution = _execution(request, inputs, native, data['programGenerationPin'], reader)
            custody = _protection(request, inputs, data['programProtectionCustodyPin'],
                execution['previousTarget'], receipt['state'] == 'SUCCEEDED', outer, reader)
            switched, switch_unknown = _switch(request, inputs, execution['generation'],
                execution['previousTarget'], outer, reader, complete=receipt['state'] == 'SUCCEEDED')
            imported, import_unknown = _image_import(request, inputs, execution['startedEpoch'], outer, reader,
                complete=receipt['state'] == 'SUCCEEDED')
            mutation = native['mutationDispatched'] or switched or imported
            unknown_causes.update(native=native['terminalUnknown'],
                programSwitch=switch_unknown, programImport=import_unknown)
            unknown = native['terminalUnknown'] or switch_unknown or import_unknown
            invocations, last = native['invocations'], native['lastExitCode']
            if phase == 'PREPARATION': _need(result['state'] != 'SUCCEEDED', 'PREPARATION_SUCCESS_INVALID')
        completed_receipt_unknown = (receipt['state'] == 'SUCCEEDED' and receipt['terminalUnknown'] is False and
            data['terminalUnknown'] is True and result['state'] == 'TERMINAL_UNKNOWN' and
            _text(result.get('failureCode')) and not unknown and phase == 'RESTORE' and
            native is not None and bool(native['invocations']))
        _need(all(item['mutationDispatched'] == mutation for item in (data, receipt)) and
            (data['terminalUnknown'] == receipt['terminalUnknown'] or completed_receipt_unknown) and
            (not unknown or data['terminalUnknown']), 'AGGREGATE_SUMMARY_INVALID')
        if data['terminalUnknown'] and not unknown:
            # Archive/protection/recording uncertainty may conservatively retain
            # exclusion after every observed native exit was known. This never
            # suppresses an observed unknown or converts failure into success.
            _need(result['state'] == 'TERMINAL_UNKNOWN' and _text(result.get('failureCode')),
                'UNKNOWN_SUMMARY_INVALID')
            unknown_causes['outerConservative'] = True
            unknown = True
        if 'actualNativeExitCode' in data:
            _need(type(data['actualNativeExitCode']) is type(last) and data['actualNativeExitCode'] == last,
                'ACTUAL_EXIT_CHANGED')
        if result['state'] == 'SUCCEEDED':
            _need(not unknown and phase == 'RESTORE' and data['programGenerationPin'] is not None,
                'SUCCESS_UNPROVEN')
        elif result['state'] == 'TERMINAL_UNKNOWN': _need(unknown, 'UNKNOWN_UNPROVEN')
        else: _need(not unknown, 'UNKNOWN_MISLABELLED')
        reader.unchanged()
        references = _index([*outer.values(), *(record[0] for record in reader.records.values()),
            *(native['originalResultPins'] if native else []), *(custody['originalResultPins'] if custody else [])])
        proof = dict(schemaVersion='MainProgramEvidenceValidation/v1', operationId=request['operationId'],
            resultState=result['state'], replacementState=receipt['state'], phase=phase,
            bindingPin=deepcopy(execution['bindingPin']), contextPin=deepcopy(execution['contextPin']),
            generationPin=deepcopy(data['programGenerationPin']), target=deepcopy(execution['target']),
            programNativeEvidencePin=deepcopy(data['programNativeEvidencePin']),
            programProtectionCustodyPin=deepcopy(data['programProtectionCustodyPin']),
            targetPin=deepcopy(execution['targetPin']), epoch=deepcopy(execution['epoch']),
            invocations=deepcopy(invocations), originalResultPins=deepcopy(list(references.values())),
            mutationDispatched=mutation, terminalUnknown=unknown, lastExitCode=last,
            unknownCauses=deepcopy(unknown_causes),
            protectionState=None if custody is None else custody['state'],
            protectionStates=None if custody is None else deepcopy(custody['protections']),
            cleanedSqlPins=deepcopy(list(cleaned.values())),
            deferredPayloadPins=deepcopy([entry[0] for entry in reader.deferred.values()]))
        guard()
        return proof
    except RecoveryError:
        raise
    except (KeyError, TypeError, IndexError, AttributeError, OSError, ValueError, RecursionError) as error:
        raise RecoveryError('PROGRAM_EVIDENCE_INVALID') from error
