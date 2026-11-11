"""Deterministic preservation restore owners from trusted control originals.

This is bounded metadata reconstruction. It neither verifies archive payloads
nor grants source, target, or clear authority. Ordinary publisher history remains
the real A1 contract; preservation ancestors share its bounded raw metadata ledger.
"""
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import os
import re
import stat

from recovery_backup_epoch import _path, _read_file, _signature
from recovery_engine import canonical, require
from recovery_restore_inputs import _Reads as _ArchiveReads
import recovery_preservation_source as _source


DOCUMENT_LIMIT = 16 * 1024 * 1024
METADATA_LIMIT = 64 * 1024 * 1024
CONTROL_LIMIT = 32
REQUEST_FIELDS = ('schemaVersion operationId action sourceConfigRef parentChainRef '
    'recoveryPointRef targetConfigRef')
BINDING_FIELDS = ('schemaVersion reference sourceConfigRef sourcePolicyPin pointPin '
    'publicationOperationId controlConfigurationPin')
SOURCE_FIELDS = ('schemaVersion kind originTargetConfigRef repositoryConfigurationPin '
    'sourceScopePin sourceIdentityPin policyRef')
ORIGINAL_FIELDS = 'requestInputsPin pointBindingPin recoveryConfigurationPin'


def _need(condition, suffix):
    require(condition, 'PRESERVATION_RESTORE_' + suffix)


def _exact(value, fields, suffix):
    _need(type(value) is dict and set(value) == set(fields.split()), suffix)


def _same(left, right):
    return canonical(left) == canonical(right)


def _pin(value):
    _exact(value, 'path bytes sha256', 'PIN_INVALID')
    _need(type(value['bytes']) is int and 0 <= value['bytes'] < 2**63 and
        type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'PIN_INVALID')
    return _path(value['path'])


def _same_pin(left, right):
    return (_pin(left) == _pin(right) and left['bytes'] == right['bytes'] and
        left['sha256'] == right['sha256'])


def _pin_key(value):
    return _pin(value).as_posix(), value['bytes'], value['sha256']


def _text(value):
    return type(value) is str and 0 < len(value) <= 256 and not any(ord(c) < 32 for c in value)


def _request(value):
    _exact(value, REQUEST_FIELDS, 'REQUEST_INVALID')
    _need(value['schemaVersion'] == 'SmallAppBackupUiRequest/v1' and value['action'] == 'RESTORE' and
        type(value['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value['operationId']) and
        value['parentChainRef'] is None and all(_text(value[k]) for k in
            ('sourceConfigRef', 'recoveryPointRef', 'targetConfigRef')) and
        value['sourceConfigRef'] != value['targetConfigRef'], 'REQUEST_INVALID')


class _History:
    """One bounded publication traversal; no cached admission or owner result."""
    def __init__(self):
        self.active, self.seen, self.depth = set(), {}, 0

    @contextmanager
    def publication(self, operations_root, operation, origin, pins, *, derived):
        _need(type(operation) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', operation) and
            _text(origin) and type(derived) is bool, 'BINDING_INVALID')
        key = (_path(str(operations_root)), operation, origin)
        _exact(pins, 'sourcePolicyPin pointPin configurationPin requestPin intentPin executionBindingPin originals',
            'BINDING_INVALID')
        for name, pin in pins.items():
            if name != 'originals': _pin(pin)
        _need(type(pins['originals']) is dict and (not pins['originals'] or
            set(pins['originals']) == set(ORIGINAL_FIELDS.split())), 'ORIGINAL_BINDING_INVALID')
        for pin in pins['originals'].values(): _pin(pin)
        normalized = {name:dict(deepcopy(pin), path=_pin(pin).as_posix())
            for name, pin in pins.items() if name != 'originals'}
        normalized['originals'] = {name:dict(deepcopy(pin), path=_pin(pin).as_posix())
            for name, pin in pins['originals'].items()}
        fingerprint = canonical(normalized)
        _need(key not in self.active, 'HISTORY_CYCLE')
        _need(key not in self.seen or self.seen[key] == fingerprint, 'OPERATION_CONFLICT')
        _need(key in self.seen or len(self.seen) < 128, 'HISTORY_LIMIT')
        _need(self.depth + int(derived) <= 32, 'HISTORY_LIMIT')
        self.seen[key] = fingerprint
        self.active.add(key); self.depth += int(derived)
        try:
            yield
        finally:
            self.depth -= int(derived); self.active.remove(key)


def _tighten_preservation_limits(reads, document_maximum, metadata_maximum):
    """One monotone policy transition over the actual shared raw ledger."""
    _need(type(document_maximum) is int and 0 < document_maximum <= DOCUMENT_LIMIT and
        type(metadata_maximum) is int and document_maximum <= metadata_maximum <= METADATA_LIMIT,
        'METADATA_LIMIT')
    maximum = min(reads.maximum, document_maximum)
    total_limit = min(reads.total_limit, metadata_maximum)
    reads.guard()
    reads.budget(reads.total <= total_limit and all(
        pin['bytes'] <= maximum for pin, _, _ in reads.records.values()))
    reads.maximum, reads.total_limit = maximum, total_limit
    reads.guard()


class _Reads(_ArchiveReads):
    """One A1 raw ledger, adapted to the consumer's narrow metadata protocol."""
    def __init__(self, guard, reader=None, fixed_reader=None):
        super().__init__(guard, reader)
        _need(fixed_reader is None or callable(fixed_reader), 'FIXED_READER_INVALID')
        self.fixed_reader = fixed_reader
        self.maximum = DOCUMENT_LIMIT
        self.total_limit = METADATA_LIMIT
        self.directories, self.absent = {}, set()

    def budget(self, condition):
        _need(condition, 'METADATA_LIMIT')

    def read(self, reference, maximum=None):
        maximum = self.maximum if maximum is None else maximum
        _need(type(maximum) is int and maximum > 0, 'METADATA_LIMIT')
        path = _pin(reference)
        maximum = min(maximum, self.maximum, DOCUMENT_LIMIT)
        _need(reference['bytes'] <= maximum, 'METADATA_LIMIT')
        if path in self.records:
            _need(_same_pin(self.records[path][0], reference), 'PIN_CHANGED')
        else:
            self.guard()
            self.budget(path.stat().st_size <= min(maximum, self.total_limit - self.total))
        self.budget(self.total + (0 if path in self.records else reference['bytes']) <= self.total_limit)
        return super().read(reference, maximum)

    def fixed(self, path, maximum=None):
        self.guard()
        path = _path(str(path))
        maximum = self.maximum if maximum is None else maximum
        _need(type(maximum) is int and maximum > 0, 'METADATA_LIMIT')
        maximum = min(maximum, self.maximum, DOCUMENT_LIMIT)
        if path in self.records:
            pin = deepcopy(self.records[path][0])
        else:
            limit = min(maximum, self.total_limit - self.total)
            stamp = _signature(path.stat())
            self.budget(stamp[2] <= limit)
            if self.reader is None:
                _, pin = _read_file(path, limit)
            else:
                _need(self.fixed_reader is not None, 'FIXED_READER_REQUIRED')
                result = self.fixed_reader(path, limit)
                _need(type(result) in (tuple, list) and len(result) == 2, 'FIXED_READER_INVALID')
                pin = result[0]
                _need(_pin(pin) == path and pin['bytes'] == stamp[2] and pin['bytes'] <= limit,
                    'FIXED_READER_INVALID')
            _need(_signature(path.stat()) == stamp, 'METADATA_CHANGED')
        return pin, self.read(pin, maximum)

    def raw(self, reference, maximum):
        self.read(reference, maximum)
        self.guard()
        path = _pin(reference)
        pin, _, stamp = self.records[path]
        raw, observed = _read_file(path, min(maximum, self.maximum, DOCUMENT_LIMIT))
        _need(_same_pin(pin, observed) and _signature(path.stat()) == stamp, 'METADATA_CHANGED')
        self.guard()
        return raw

    def directory(self, path):
        self.guard()
        path = _path(str(path)); info = path.stat()
        _need(stat.S_ISDIR(info.st_mode) and (os.name != 'posix' or
            info.st_uid == os.geteuid() and not info.st_mode & 0o022), 'DIRECTORY_INVALID')
        stamp = (_signature(info), info.st_mode)
        _need(path not in self.directories or self.directories[path] == stamp, 'DIRECTORY_CHANGED')
        self.directories[path] = stamp
        return path

    def optional(self, path):
        self.guard(); path = _path(str(path))
        if os.path.lexists(path):
            return True
        parent = path.parent
        while not parent.exists():
            parent = parent.parent
        self.directory(parent)
        self.absent.add(path)
        return False

    def finish(self):
        # A1 always re-reads actual files, even when an external reader exists.
        super().finish()
        for path, stamp in self.directories.items():
            self.guard(); info = _path(str(path)).stat()
            _need((_signature(info), info.st_mode) == stamp, 'DIRECTORY_CHANGED')
        for path in self.absent:
            self.guard(); _need(not os.path.lexists(path), 'METADATA_CHANGED')
        for path, (_, _, stamp) in self.records.items():
            _need(_signature(_path(str(path)).stat()) == stamp, 'METADATA_CHANGED')


def _resolve_control_pins(reads, current_control_pin):
    controls, pins, active = {}, {}, set()

    def visit(pin):
        path = _pin(pin)
        _need(path not in active, 'HISTORY_CYCLE')
        if path in pins:
            _need(_same_pin(pins[path], pin), 'CONTROL_CHANGED')
            return
        _need(len(pins) < CONTROL_LIMIT, 'HISTORY_LIMIT')
        active.add(path)
        value = reads.read(pin, DOCUMENT_LIMIT)
        _need(value.get('schemaVersion') == 'SmallAppExecutionServiceConfig/v2', 'CONTROL_CHANGED')
        retained = value.get('retainedPreservationControlPins', [])
        _need(type(retained) is list and len(retained) < CONTROL_LIMIT, 'CONTROL_CHANGED')
        paths = [_pin(p) for p in retained]
        _need(len(set(paths)) == len(paths) and _same(retained, sorted(retained, key=_pin_key)), 'CONTROL_CHANGED')
        pins[path], controls[path] = deepcopy(pin), value
        for prior in retained:
            visit(prior)
        active.remove(path)

    visit(current_control_pin)
    root = _pin(current_control_pin)
    result = [deepcopy(current_control_pin), *sorted(
        (deepcopy(pin) for path, pin in pins.items() if path != root), key=_pin_key)]
    return result, controls


def resolve_preservation_control_pins(current_control_pin, *, guard, reader=None):
    """Resolve only the caller-trusted root's actual retained control graph.

    A supplied outer ``reads.raw`` must retain its own final ``finish``. Every
    actual raw body is charged through it; this wrapper cannot reset its budget.
    """
    reads = _Reads(guard, reader)
    pins, _ = _resolve_control_pins(reads, current_control_pin)
    reads.finish()
    return dict(schemaVersion='PreservationControlPinsResolution/v1',
        currentControlPin=deepcopy(current_control_pin), publisherControlPins=pins,
        originalResultPins=reads.pins(), metadataBytes=reads.total)


def _trusted_control(reads, supplied, selected_pin):
    _need(type(supplied) in (list, tuple) and 1 <= len(supplied) <= CONTROL_LIMIT, 'CONTROL_UNTRUSTED')
    paths = [_pin(pin) for pin in supplied]
    _need(len(set(paths)) == len(paths), 'CONTROL_UNTRUSTED')
    closure, controls = _resolve_control_pins(reads, supplied[0])
    _need(len(closure) == len(supplied) and all(_same_pin(a, b) for a, b in zip(closure, supplied)),
        'CONTROL_UNTRUSTED')
    _need(any(_same_pin(selected_pin, pin) for pin in closure), 'CONTROL_UNTRUSTED')
    original_pins, _ = _resolve_control_pins(reads, selected_pin)
    return controls[_pin(selected_pin)], original_pins


def _derive(reads, base_owner_pin, request, point_binding_pin, *, request_configurations_root,
        publisher_control_pins, history):
    _request(request)
    base = reads.read(base_owner_pin, DOCUMENT_LIMIT)
    _need(base.get('schemaVersion') == 'RecoveryMinimalConfiguration/v1' and
        type(base.get('sources')) is dict and request['sourceConfigRef'] in base['sources'], 'SOURCE_INVALID')
    descriptor = base['sources'][request['sourceConfigRef']]
    _exact(descriptor, SOURCE_FIELDS, 'SOURCE_INVALID')
    _need(descriptor['schemaVersion'] == 'MainTargetPreservationSource/v1' and
        descriptor['kind'] == 'TARGET_PRE_RESTORE' and
        _text(descriptor['originTargetConfigRef']) and _text(descriptor['policyRef']), 'SOURCE_INVALID')
    for name in ('repositoryConfigurationPin', 'sourceScopePin', 'sourceIdentityPin'):
        _pin(descriptor[name])
    root = reads.directory(_path(request_configurations_root))
    directory = root/request['operationId']
    _need(_pin(point_binding_pin) == directory/'preservation-point.json', 'ORIGINAL_PATH_INVALID')
    binding = reads.read(point_binding_pin, 65536)
    _exact(binding, BINDING_FIELDS, 'BINDING_INVALID')
    _need(binding['schemaVersion'] == 'SmallAppPreservationPointBinding/v1' and
        binding['reference'] == request['recoveryPointRef'] and binding['sourceConfigRef'] == request['sourceConfigRef'] and
        type(binding['publicationOperationId']) is str and
        re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', binding['publicationOperationId']) and
        binding['publicationOperationId'] != request['operationId'], 'BINDING_INVALID')
    for name in ('sourcePolicyPin', 'pointPin', 'controlConfigurationPin'):
        _pin(binding[name])
    control, original_controls = _trusted_control(reads, publisher_control_pins, binding['controlConfigurationPin'])
    _need(type(control.get('taskRoot')) is str and
        root == _path(control['taskRoot'])/'request-configurations', 'ORIGINAL_PATH_INVALID')
    policies, routes = control.get('preservationSourcePolicies'), control.get('restoreConfigurations')
    _need(type(policies) is dict and descriptor['policyRef'] in policies and
        _same_pin(policies[descriptor['policyRef']], binding['sourcePolicyPin']) and type(routes) is dict and
        type(routes.get(request['sourceConfigRef'])) is dict and
        request['targetConfigRef'] in routes[request['sourceConfigRef']] and
        _same_pin(routes[request['sourceConfigRef']][request['targetConfigRef']], base_owner_pin), 'CONTROL_CHANGED')
    _, inputs = reads.fixed(directory/'restore-inputs.json', 65536)
    _exact(inputs, 'request ownerConfigurationPin', 'ORIGINAL_BINDING_INVALID')
    _need(_same(inputs['request'], request) and _same_pin(inputs['ownerConfigurationPin'], base_owner_pin),
        'ORIGINAL_BINDING_INVALID')
    # Enforce the consumer's initial source-policy document cap before its helper.
    reads.read(binding['sourcePolicyPin'], 4*1024*1024)
    policy, repository, row, historical = _source._describe_bound_preservation(
        reads, binding['sourcePolicyPin'], request, binding,
        publisher_control_pins=original_controls, history=history)
    _need(policy['schemaVersion'] == 'MainTargetPreservationSourcePolicy/v2' and
        policy['sourceConfigRef'] == request['sourceConfigRef'] and
        policy['originTargetConfigRef'] == descriptor['originTargetConfigRef'] and
        _same_pin(policy['repositoryConfigurationPin'], descriptor['repositoryConfigurationPin']) and
        _same_pin(repository['sourceIdentityPin'], descriptor['sourceIdentityPin']), 'SOURCE_INVALID')
    scope = reads.read(descriptor['sourceScopePin'])
    _need(scope.get('schemaVersion') == 'RecoverySourceScope/v1' and
        _same_pin(scope.get('sourceIdentityPin'), descriptor['sourceIdentityPin']), 'SOURCE_INVALID')
    reads.read(descriptor['sourceIdentityPin'])
    point = historical['point']; sidecar = _pin(binding['pointPin']).parent
    proof = historical['proof']; repository_binding_pin = proof['repositoryBindingPin']
    _need(_pin(repository_binding_pin) == sidecar/'recovery-repository-binding.json', 'BINDING_INVALID')
    repository_binding = reads.read(repository_binding_pin)
    _exact(repository_binding, 'schemaVersion backupId generationId repositoryPointPin manifestPin '
        'sourceScopePin recoveryMaterialPin objectContentIndexPin', 'BINDING_INVALID')
    _need(repository_binding['schemaVersion'] == 'RecoveryRepositoryBinding/v1' and
        _same_pin(repository_binding['repositoryPointPin'], binding['pointPin']) and
        _same_pin(repository_binding['manifestPin'], point['manifestPin']) and
        _same_pin(repository_binding['sourceScopePin'], descriptor['sourceScopePin']) and
        repository_binding['backupId'] == point['backupId'] and
        repository_binding['generationId'] == point['generationId'] and
        _same_pin(repository_binding['recoveryMaterialPin'], proof['recoveryMaterialPin']) and
        _pin(repository_binding['recoveryMaterialPin']) == sidecar/'recovery-material.json' and
        _same_pin(repository_binding['objectContentIndexPin'], proof['objectContentIndexPin']) and
        _pin(repository_binding['objectContentIndexPin']) == sidecar/'object-content-index.json', 'BINDING_INVALID')
    material = reads.read(repository_binding['recoveryMaterialPin'])
    _need(material.get('schemaVersion') == 'RecoveryMaterial/v1' and material.get('pointType') == 'FULL' and
        _same_pin(material.get('manifestPin'), point['manifestPin']) and
        _same_pin(material.get('sourceScopePin'), descriptor['sourceScopePin']) and
        _same(material.get('payloadPins'), point['payloadRefs']) and
        _same(material.get('recoveryPoint'), point['commonRecoveryPoint']), 'BINDING_INVALID')
    # Earlier controls/base are also subject to the source's smaller limits.
    reads.budget(reads.total <= reads.total_limit and all(
        pin['bytes'] <= reads.maximum for pin, _, _ in reads.records.values()))
    selected = dict(deepcopy(descriptor), schemaVersion='MainTargetPreservationBoundSource/v1',
        sourcePolicyPin=deepcopy(binding['sourcePolicyPin']),
        pointBindingPin=dict(deepcopy(point_binding_pin), path=_pin(point_binding_pin).as_posix()),
        publisherControlPins=original_controls, recoveryPoints={request['recoveryPointRef']: deepcopy(binding['pointPin'])},
        archiveRoots=[str(_path(repository['repositoryRoot']))],
        repositoryBindingPinsByManifestSha256={point['manifestPin']['sha256']: deepcopy(repository_binding_pin)})
    owner = deepcopy(base)
    owner['sources'][request['sourceConfigRef']] = selected
    return owner, binding


def derive_preservation_restore_owner(base_owner_pin, request, point_binding_pin, *,
        request_configurations_root, publisher_control_pins, guard, reader=None, fixed_reader=None):
    reads = _Reads(guard, reader, fixed_reader)
    owner, _ = _derive(reads, base_owner_pin, request, point_binding_pin,
        request_configurations_root=request_configurations_root, publisher_control_pins=publisher_control_pins,
        history=_History())
    reads.finish()
    return owner


def _verify_preservation_originals(reads, base_owner_pin, request_pin, *, request_configurations_root,
        originals, publisher_control_pins, history):
    """Rebuild only real historical originals, borrowing one outer ledger."""
    _need(type(history) is _History, 'HISTORY_INVALID')
    _exact(originals, ORIGINAL_FIELDS, 'ORIGINAL_BINDING_INVALID')
    base = reads.read(base_owner_pin, DOCUMENT_LIMIT)
    request = reads.read(request_pin, 65536); _request(request)
    _need(_pin(request_pin) == _path(base['operationsRoot'])/request['operationId']/'request.json',
        'REQUEST_PATH_INVALID')
    directory = _path(request_configurations_root)/request['operationId']
    for key, name in (('requestInputsPin', 'restore-inputs.json'),
            ('pointBindingPin', 'preservation-point.json'), ('recoveryConfigurationPin', 'recovery.json')):
        _need(_pin(originals[key]) == directory/name, 'ORIGINAL_PATH_INVALID')
    reads.read(originals['requestInputsPin'], 65536)
    recovery = reads.read(originals['recoveryConfigurationPin'], DOCUMENT_LIMIT)
    owner, binding = _derive(reads, base_owner_pin, request, originals['pointBindingPin'],
        request_configurations_root=request_configurations_root, publisher_control_pins=publisher_control_pins,
        history=history)
    _need(_same(recovery, owner), 'DERIVED_OWNER_CHANGED')
    return owner, binding


def verify_preservation_restore_inputs(base_owner_pin, request_pin, *, request_configurations_root,
        originals, publisher_control_pins, guard, reader=None, fixed_reader=None):
    reads = _Reads(guard, reader, fixed_reader)
    owner, binding = _verify_preservation_originals(reads, base_owner_pin, request_pin,
        request_configurations_root=request_configurations_root, originals=originals,
        publisher_control_pins=publisher_control_pins, history=_History())
    reads.finish()
    return dict(schemaVersion='PreservationRestoreInputsVerification/v1', baseOwnerPin=deepcopy(base_owner_pin),
        requestPin=deepcopy(request_pin), originals=deepcopy(originals),
        controlConfigurationPin=deepcopy(binding['controlConfigurationPin']),
        sourcePolicyPin=deepcopy(binding['sourcePolicyPin']), derivedOwner=owner, originalResultPins=reads.pins(),
        payloadContentVerified=False, sourceAdmissionGranted=False, targetAdmitted=False, clearAuthorized=False)
