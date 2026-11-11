"""Reconstruct ordinary archive restore inputs, without admission or execution.

The explicit point binding supplies the original selected point and evidence.
Discovery and live source eligibility remain controller responsibilities. This
module reads metadata only; neither a successful reconstruction nor its output
authorizes a source, target, payload, or clear operation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from recovery_backup_epoch import _path, _read_file, _signature
from recovery_engine import canonical, require
from repository_records import document


REQUEST_FIELDS = ('schemaVersion operationId action sourceConfigRef parentChainRef '
    'recoveryPointRef targetConfigRef')
BINDING_FIELDS = 'schemaVersion reference sourceConfigRef pointPin evidencePins'
ORIGINAL_FIELDS = 'requestInputsPin pointBindingPin recoveryConfigurationPin'
OWNER_LIMIT = 16 * 1024 * 1024
METADATA_LIMIT = 64 * 1024 * 1024


def _exact(value, fields, code):
    require(type(value) is dict and set(value) == set(fields.split()), code)


def _same(left, right):
    # JSON equality must retain scalar types: Python considers True == 1.
    return canonical(left) == canonical(right)


def _pin(reference):
    require(type(reference) is dict and set(reference) == {'path','bytes','sha256'} and
        type(reference['bytes']) is int and reference['bytes'] >= 0 and
        type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']),
        'RESTORE_INPUTS_PIN_INVALID')
    return _path(reference['path'])


def _same_pin(left, right):
    return _pin(left) == _pin(right) and left['bytes'] == right['bytes'] and left['sha256'] == right['sha256']


def _opaque(value):
    require(type(value) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,159}', value) and
        value not in ('.','..'), 'RESTORE_INPUTS_REQUEST_INVALID')
    return value


def _request(value):
    _exact(value, REQUEST_FIELDS, 'RESTORE_INPUTS_REQUEST_INVALID')
    require(value['schemaVersion'] == 'SmallAppBackupUiRequest/v1' and value['action'] == 'RESTORE',
        'RESTORE_INPUTS_REQUEST_INVALID')
    require(len(_opaque(value['operationId'])) >= 8 and value['parentChainRef'] is None,
        'RESTORE_INPUTS_REQUEST_INVALID')
    for key in ('sourceConfigRef','recoveryPointRef','targetConfigRef'):
        _opaque(value[key])
    require(value['sourceConfigRef'] != value['targetConfigRef'], 'RESTORE_INPUTS_REQUEST_INVALID')


class _Reads:
    """Actual bounded metadata reads, with a final independent byte/identity check."""
    def __init__(self, guard, reader):
        require(callable(guard) and (reader is None or callable(reader)), 'RESTORE_INPUTS_READER_INVALID')
        self.guard, self.reader, self.records = guard, reader, {}
        self.total = 0

    def read(self, reference, maximum):
        self.guard()
        path = _pin(reference)
        require(reference['bytes'] <= maximum, 'RESTORE_INPUTS_METADATA_LIMIT')
        stamp = _signature(path.stat())
        if path in self.records:
            original, value, observed = self.records[path]
            require(stamp == observed, 'RESTORE_INPUTS_METADATA_CHANGED')
            require(_same_pin(reference, original), 'RESTORE_INPUTS_PIN_CHANGED')
            self.guard()
            return deepcopy(value)
        remaining = METADATA_LIMIT - self.total
        require(reference['bytes'] <= remaining and stamp[2] <= min(maximum, remaining),
            'RESTORE_INPUTS_METADATA_LIMIT')
        read_limit = min(maximum, remaining)
        if self.reader is None:
            raw, actual = _read_file(path, read_limit)
        else:
            raw = self.reader(deepcopy(reference), read_limit)
            require(type(raw) is bytes and len(raw) <= read_limit, 'RESTORE_INPUTS_METADATA_LIMIT')
            actual = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        require(_signature(_path(str(path)).stat()) == stamp, 'RESTORE_INPUTS_METADATA_CHANGED')
        require(_same_pin(actual, reference), 'RESTORE_INPUTS_PIN_CHANGED')
        self.total += len(raw)
        value = document(raw)
        require(type(value) is dict, 'RESTORE_INPUTS_DOCUMENT_INVALID')
        self.records[path] = (deepcopy(reference), value, stamp)
        self.guard()
        return deepcopy(value)

    def finish(self):
        for path, (reference, _, stamp) in self.records.items():
            self.guard()
            require(_signature(_path(str(path)).stat()) == stamp, 'RESTORE_INPUTS_METADATA_CHANGED')
            # The protocol reader cannot waive verification of the actual file.
            _, observed = _read_file(path, reference['bytes'])
            require(_same_pin(reference, observed) and _signature(path.stat()) == stamp,
                'RESTORE_INPUTS_METADATA_CHANGED')
        self.guard()
        # A later read or guard cannot hide changes to an earlier original.
        for path, (_, _, stamp) in self.records.items():
            require(_signature(_path(str(path)).stat()) == stamp, 'RESTORE_INPUTS_METADATA_CHANGED')

    def pins(self):
        return [deepcopy(record[0]) for record in self.records.values()]


def _derive(base_owner, request, point_binding, reads):
    _request(request)
    _exact(point_binding, BINDING_FIELDS, 'RESTORE_INPUTS_POINT_BINDING_INVALID')
    require(point_binding['schemaVersion'] == 'SmallAppArchivePointBinding/v1' and
        point_binding['reference'] == request['recoveryPointRef'] and
        point_binding['sourceConfigRef'] == request['sourceConfigRef'], 'RESTORE_INPUTS_POINT_BINDING_INVALID')
    require(type(base_owner) is dict and type(base_owner.get('sources')) is dict and
        type(base_owner['sources'].get(request['sourceConfigRef'])) is dict,
        'RESTORE_INPUTS_SOURCE_INVALID')
    source = base_owner['sources'][request['sourceConfigRef']]
    catalogue = source.get('archiveCatalogue')
    multiple = type(catalogue) is dict and catalogue.get('schemaVersion') == 'RecoveryArchiveCatalogue/v2'
    _exact(catalogue, 'schemaVersion maximumPointFiles maximumMetadataBytes sourceAdmissionPin' +
        (' sourceScopePins' if multiple else ''), 'ARCHIVE_CATALOGUE_FIELDS_INVALID')
    require(catalogue['schemaVersion'] in ('RecoveryArchiveCatalogue/v1','RecoveryArchiveCatalogue/v2') and
        type(catalogue['maximumPointFiles']) is int and 1 <= catalogue['maximumPointFiles'] <= 10000 and
        type(catalogue['maximumMetadataBytes']) is int and
        1024 <= catalogue['maximumMetadataBytes'] <= METADATA_LIMIT, 'ARCHIVE_CATALOGUE_LIMIT_INVALID')
    maximum = catalogue['maximumMetadataBytes']
    require(type(source.get('archiveRoots')) is list, 'ARCHIVE_ROOT_UNAVAILABLE')
    roots = [_path(value) for value in source['archiveRoots']]
    require(roots and len(roots) == len(set(roots)) and all(root.is_dir() for root in roots),
        'ARCHIVE_ROOT_UNAVAILABLE')
    scopes = catalogue['sourceScopePins'] if multiple else [source['sourceScopePin']]
    require(type(scopes) is list and 1 <= len(scopes) <= 32 and source['sourceScopePin'] in scopes and
        len({canonical(pin) for pin in scopes}) == len(scopes), 'ARCHIVE_SOURCE_SCOPES_INVALID')
    primary = reads.read(source['sourceScopePin'], maximum)
    identity = primary['sourceIdentityPin']
    reads.read(identity, maximum)
    identities = {canonical(source['sourceScopePin']):identity}
    if multiple:
        for reference in scopes:
            scope = reads.read(reference, maximum)
            selected_identity = scope.get('sourceIdentityPin')
            require(scope.get('schemaVersion') == 'RecoverySourceScope/v1' and type(selected_identity) is dict and
                all(selected_identity.get(key) == identity[key] for key in ('bytes','sha256')),
                'ARCHIVE_SCOPE_IDENTITY_MISMATCH')
            reads.read(selected_identity, maximum)
            identities[canonical(reference)] = selected_identity
    evidence_pins = point_binding['evidencePins']
    require(type(evidence_pins) is list and 1 <= len(evidence_pins) <= catalogue['maximumPointFiles'] * 6,
        'RESTORE_INPUTS_POINT_BINDING_INVALID')
    evidence_by_path = {}
    for reference in evidence_pins:
        path = _pin(reference)
        require(path not in evidence_by_path, 'RESTORE_INPUTS_POINT_BINDING_INVALID')
        evidence_by_path[path] = reference
    selected = point_binding['pointPin']
    _pin(selected)
    points, bindings, evidence, visiting = [], {}, [], set()
    selected_scope = None

    def visit(reference):
        nonlocal selected_scope
        path = _pin(reference)
        require(reference['sha256'] not in visiting and len(visiting) < catalogue['maximumPointFiles'],
            'ARCHIVE_CHAIN_CYCLE_OR_LIMIT')
        visiting.add(reference['sha256'])
        require(path.name == 'point.json' and path.parent.name == '.repository' and
            path.parent.parent.parent in roots, 'ARCHIVE_PARENT_OUTSIDE_ROOT')
        point = reads.read(reference, maximum)
        require(point.get('schemaVersion') == 'RepositoryPoint/v1' and point.get('integrityState') == 'COMPLETE' and
            point.get('pointType') in ('FULL','INCREMENTAL'), 'ARCHIVE_POINT_INCOMPLETE')
        manifest = reads.read(point['manifestPin'], maximum)
        require(_pin(point['manifestPin']) == path.parent/'manifest.json' and
            manifest.get('schemaVersion') == 'RepositoryManifest/v1' and all(
                _same(point[key], manifest[key]) for key in ('backupId','generationId','pointType','parentPointPins')) and
            manifest['sourceIdentityPin'] in identities.values(), 'ARCHIVE_SOURCE_BINDING_INVALID')
        binding_reference = evidence_by_path.get(path.parent/'recovery-repository-binding.json')
        require(binding_reference is not None, 'RESTORE_INPUTS_POINT_BINDING_INVALID')
        binding = reads.read(binding_reference, maximum)
        _exact(binding, 'schemaVersion backupId generationId repositoryPointPin manifestPin sourceScopePin '
            'recoveryMaterialPin objectContentIndexPin', 'ARCHIVE_REPOSITORY_BINDING_INVALID')
        require(binding['schemaVersion'] == 'RecoveryRepositoryBinding/v1' and
            _same(binding['repositoryPointPin'], reference) and _same(binding['manifestPin'], point['manifestPin']) and
            binding['sourceScopePin'] in scopes and
            _same(manifest['sourceIdentityPin'], identities[canonical(binding['sourceScopePin'])]) and
            binding['backupId'] == point['backupId'] and binding['generationId'] == point['generationId'],
            'ARCHIVE_SOURCE_BINDING_INVALID')
        if selected_scope is None:
            selected_scope = binding['sourceScopePin']
        require(_same(binding['sourceScopePin'], selected_scope), 'ARCHIVE_CHAIN_SCOPE_MISMATCH')
        parents = point['parentPointPins']
        require(type(parents) is list, 'ARCHIVE_PARENT_PREFIX_INVALID')
        if point['pointType'] == 'FULL':
            require(not parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
        else:
            require(parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
            visit(parents[-1])
            require(_same(parents, points) and all(reads.read(parent, maximum)['generationId'] ==
                point['generationId'] for parent in points), 'ARCHIVE_PARENT_PREFIX_INVALID')
        terminal, readback, close = [reads.read(point[key], maximum) for key in
            ('originalExitEvidencePin','readbackEvidencePin','ownerCloseEvidencePin')]
        for key, name in (('originalExitEvidencePin','original-exit.json'),
                ('readbackEvidencePin','readback-original.json'),('ownerCloseEvidencePin','archive-close.json')):
            require(_pin(point[key]) == path.parent/name, 'ARCHIVE_ORIGINAL_OUTSIDE_SIDECAR')
            evidence.append(point[key])
        require(terminal.get('state') == 'EXITED' and terminal.get('processTerminated') is True and
            type(terminal.get('actualExitCode')) is int and terminal['actualExitCode'] == 0 and
            readback.get('schemaVersion') == 'RepositoryMinimumReadback/v1' and
            readback.get('operationId') == point['backupId'] and _same(readback.get('manifestPin'), point['manifestPin']) and
            _same(readback.get('sourceScopePin'), selected_scope) and
            close.get('schemaVersion') == 'RepositoryMinimumArchiveClose/v1' and
            close.get('operationId') == point['backupId'] and close.get('archiveReaderClosed') is True,
            'ARCHIVE_ORIGINAL_PUBLICATION_INVALID')
        require(point['manifestPin']['sha256'] not in bindings, 'ARCHIVE_MANIFEST_DUPLICATE')
        points.append(reference)
        bindings[point['manifestPin']['sha256']] = binding_reference
        evidence.extend([reference, point['manifestPin'], binding_reference])

    visit(selected)
    require(reads.read(selected, maximum)['backupId'] == request['recoveryPointRef'],
        'RESTORE_INPUTS_POINT_BINDING_INVALID')
    expected_binding = dict(schemaVersion='SmallAppArchivePointBinding/v1', reference=request['recoveryPointRef'],
        sourceConfigRef=request['sourceConfigRef'], pointPin=selected, evidencePins=evidence)
    require(_same(point_binding, expected_binding), 'RESTORE_INPUTS_POINT_BINDING_INVALID')
    resolved = deepcopy(source)
    resolved.pop('archiveCatalogue')
    resolved.update(sourceScopePin=selected_scope, recoveryPoints={request['recoveryPointRef']:selected},
        repositoryPointPins=points, repositoryBindingPinsByManifestSha256=bindings, parentChains={})
    owner = deepcopy(base_owner)
    owner['sources'][request['sourceConfigRef']] = deepcopy(resolved)
    return owner


def derive_archive_restore_owner(base_owner, request, point_binding, *, guard, reader=None):
    """Derive one ordinary source from explicit originals; do not grant admission."""
    reads = _Reads(guard, reader)
    result = _derive(base_owner, request, point_binding, reads)
    reads.finish()
    return result


def verify_archive_restore_inputs(base_owner_pin, request_pin, *, request_configurations_root,
        originals, guard, reader=None):
    """Close pinned historical request inputs against their deterministic owner."""
    _exact(originals, ORIGINAL_FIELDS, 'RESTORE_INPUTS_ORIGINALS_INVALID')
    reads = _Reads(guard, reader)
    owner = reads.read(base_owner_pin, OWNER_LIMIT)
    request = reads.read(request_pin, 65536)
    _request(request)
    require(_pin(request_pin) == _path(owner['operationsRoot'])/request['operationId']/'request.json',
        'RESTORE_INPUTS_REQUEST_PATH_INVALID')
    root = _path(request_configurations_root)
    require(root.is_dir(), 'RESTORE_INPUTS_ORIGINAL_PATH_INVALID')
    directory = root/request['operationId']
    for key, filename in (('requestInputsPin','restore-inputs.json'),('pointBindingPin','archive-point.json'),
            ('recoveryConfigurationPin','recovery.json')):
        require(_pin(originals[key]) == directory/filename, 'RESTORE_INPUTS_ORIGINAL_PATH_INVALID')
    inputs = reads.read(originals['requestInputsPin'], 65536)
    _exact(inputs, 'request ownerConfigurationPin', 'RESTORE_INPUTS_ORIGINAL_BINDING_INVALID')
    require(_same(inputs['request'], request) and _same(inputs['ownerConfigurationPin'], base_owner_pin),
        'RESTORE_INPUTS_ORIGINAL_BINDING_INVALID')
    binding = reads.read(originals['pointBindingPin'], METADATA_LIMIT)
    recovery = reads.read(originals['recoveryConfigurationPin'], OWNER_LIMIT)
    derived = _derive(owner, request, binding, reads)
    require(_same(recovery, derived), 'RESTORE_INPUTS_DERIVED_OWNER_CHANGED')
    reads.finish()
    return dict(schemaVersion='ArchiveRestoreInputsVerification/v1', baseOwnerPin=deepcopy(base_owner_pin),
        requestPin=deepcopy(request_pin), originals=deepcopy(originals), derivedOwner=deepcopy(derived),
        originalResultPins=reads.pins(), payloadContentVerified=False, sourceAdmissionGranted=False,
        targetAdmitted=False, clearAuthorized=False)
