"""Real metadata files prove deterministic inputs, never a restore or admission."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
sys.path.insert(0, str(ROOT/'backend/src/main/resources'))

from recovery_control_restore_catalogue import bind_archive_chain
from recovery_engine import RecoveryError
from recovery_restore_inputs import _Reads, derive_archive_restore_owner, verify_archive_restore_inputs


def raw_pin(path):
    raw = path.read_bytes()
    return dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


class Originals:
    """Protocol fixtures are actual files, not a business backup or live success."""
    def __init__(self, root):
        self.root = root
        self.identity = self.write(root/'id.json', dict(sourceFingerprint='source-A', databaseUuid='uuid-A'))
        self.scope = self.write(root/'scope.json', dict(schemaVersion='RecoverySourceScope/v1',
            sourceIdentityPin=self.identity))
        (root/'archives').mkdir()
        self.source = dict(sourceScopePin=self.scope, archiveRoots=[str(root/'archives')],
            archiveCatalogue=dict(schemaVersion='RecoveryArchiveCatalogue/v1', maximumPointFiles=100,
                maximumMetadataBytes=1048576, sourceAdmissionPin={'notReadByThisAPI':True}),
            expectedDataPolicy={'preserved':True})
        self.request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-inputs-001',
            action='RESTORE', sourceConfigRef='source-A', parentChainRef=None,
            recoveryPointRef='backup-new', targetConfigRef='target-B')
        self.owner = dict(operationsRoot=str(root/'operations'), sources={'source-A':self.source,
            'other-source':{'mustRemain':{'values':[1,2]}}}, targets={'target-B':{'guard':1}},
            sourceProgramArchivePolicies={'source-A':{'preserved':'exact'}}, deadlineMilliseconds=120000)
        self.request_root = root/'request-configurations'

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode('utf-8'))
        path.chmod(0o600)
        return raw_pin(path)

    def point(self, reference, parents=(), *, scope=None, generation='full-first', terminal_exit=0,
              readback_operation=None, closed=True):
        scope = scope or self.scope
        identity = json.loads(Path(scope['path']).read_text(encoding='utf-8'))['sourceIdentityPin']
        sidecar = self.root/'archives'/reference/'.repository'
        payload = sidecar.parent/'payload.bin'
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(b'This payload must never be opened by the input verifier.')
        manifest = self.write(sidecar/'manifest.json', dict(schemaVersion='RepositoryManifest/v1',
            backupId=reference, generationId=generation, sourceIdentityPin=identity,
            pointType='INCREMENTAL' if parents else 'FULL', parentPointPins=list(parents),
            payloadRefs=[raw_pin(payload)]))
        terminal = self.write(sidecar/'original-exit.json', dict(state='EXITED', processTerminated=True,
            actualExitCode=terminal_exit))
        readback = self.write(sidecar/'readback-original.json', dict(schemaVersion='RepositoryMinimumReadback/v1',
            operationId=readback_operation or reference, manifestPin=manifest, sourceScopePin=scope))
        close = self.write(sidecar/'archive-close.json', dict(schemaVersion='RepositoryMinimumArchiveClose/v1',
            operationId=reference, archiveReaderClosed=closed))
        point = self.write(sidecar/'point.json', dict(schemaVersion='RepositoryPoint/v1', backupId=reference,
            generationId=generation, pointType='INCREMENTAL' if parents else 'FULL',
            parentPointPins=list(parents), manifestPin=manifest, originalExitEvidencePin=terminal,
            readbackEvidencePin=readback, ownerCloseEvidencePin=close, integrityState='COMPLETE'))
        self.write(sidecar/'recovery-repository-binding.json', dict(schemaVersion='RecoveryRepositoryBinding/v1',
            backupId=reference, generationId=generation, repositoryPointPin=point, manifestPin=manifest,
            sourceScopePin=scope, recoveryMaterialPin={'notValidatedHere':'material'},
            objectContentIndexPin={'notValidatedHere':'index'}))
        return point

    def controller_originals(self):
        resolved, self.binding = bind_archive_chain(self.source, self.request)
        self.derived = deepcopy(self.owner)
        self.derived['sources']['source-A'] = resolved
        self.base_pin = self.write(self.root/'owner.json', self.owner)
        self.request_pin = self.write(Path(self.owner['operationsRoot'])/self.request['operationId']/'request.json', self.request)
        directory = self.request_root/self.request['operationId']
        self.originals = dict(requestInputsPin=self.write(directory/'restore-inputs.json',
            dict(request=self.request, ownerConfigurationPin=self.base_pin)),
            pointBindingPin=self.write(directory/'archive-point.json', self.binding),
            recoveryConfigurationPin=self.write(directory/'recovery.json', self.derived))
        return self

    def verify(self, **kwargs):
        return verify_archive_restore_inputs(self.base_pin, self.request_pin,
            request_configurations_root=str(self.request_root), originals=self.originals,
            guard=kwargs.pop('guard', lambda:None), **kwargs)

    def replace_original(self, key, value):
        self.originals[key] = self.write(Path(self.originals[key]['path']), value)


@pytest.fixture
def originals(tmp_path_factory):
    return Originals(tmp_path_factory.mktemp('i').resolve())


@pytest.mark.parametrize('increments', [0,2], ids=['full','full-two-increments'])
def test_derived_owner_exactly_matches_original_controller_and_preserves_bytes(originals, increments):
    f = originals
    parents = []
    for index in range(increments):
        parents.append(f.point('ancestor-'+str(index), parents))
    f.point('backup-new', parents)
    f.controller_originals()
    before = {path:path.read_bytes() for path in f.root.rglob('*') if path.is_file()}
    seen = []
    def reader(reference, limit):
        path = Path(reference['path'])
        assert path.suffix == '.json' and reference['bytes'] <= limit
        seen.append(path)
        return path.read_bytes()
    owner = derive_archive_restore_owner(f.owner, f.request, f.binding, guard=lambda:None, reader=reader)
    assert owner == f.derived
    assert owner is not f.owner and owner['targets'] is not f.owner['targets']
    assert {path:path.read_bytes() for path in f.root.rglob('*') if path.is_file()} == before
    assert seen and not any(path.name == 'payload.bin' for path in seen)
    owner['targets']['target-B']['guard'] = 9
    assert f.owner['targets']['target-B']['guard'] == 1
    original_binding = deepcopy(f.binding)
    owner['sources']['source-A']['recoveryPoints']['backup-new']['sha256'] = '0'*64
    assert f.binding == original_binding


def test_explicit_historical_scope_retains_original_identity_path(originals):
    f = originals
    old_identity = f.write(f.root/'old/id.json', json.loads(Path(f.identity['path']).read_text(encoding='utf-8')))
    historical = f.write(f.root/'old/scope.json', dict(schemaVersion='RecoverySourceScope/v1', sourceIdentityPin=old_identity))
    f.source['archiveCatalogue'].update(schemaVersion='RecoveryArchiveCatalogue/v2', sourceScopePins=[f.scope,historical])
    first = f.point('old-first', scope=historical)
    f.point('backup-new', [first], scope=historical)
    f.controller_originals()
    result = f.verify()
    assert result['derivedOwner'] == f.derived
    assert result['derivedOwner']['sources']['source-A']['sourceScopePin'] == historical
    assert old_identity in result['originalResultPins']


def test_original_input_closure_is_bound_without_granting_restore_permissions(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    result = f.verify()
    assert result['schemaVersion'] == 'ArchiveRestoreInputsVerification/v1'
    assert result['baseOwnerPin'] == f.base_pin and result['requestPin'] == f.request_pin
    assert result['originals'] == f.originals and result['derivedOwner'] == f.derived
    for flag in ('payloadContentVerified','sourceAdmissionGranted','targetAdmitted','clearAuthorized'):
        assert result[flag] is False
    for pin in [f.base_pin,f.request_pin,*f.originals.values(),*f.binding['evidencePins']]:
        assert pin in result['originalResultPins']
    assert len({str(Path(pin['path'])) for pin in result['originalResultPins']}) == len(result['originalResultPins'])


@pytest.mark.parametrize('change', ['source','reference','evidence-order','missing-evidence','extra-field'],
    ids=['foreign-source','foreign-point-ref','evidence-reordered','evidence-missing','binding-extra'])
def test_binding_cannot_choose_different_originals(originals, change):
    f = originals
    f.point('backup-new'); f.controller_originals()
    binding = deepcopy(f.binding)
    if change == 'source': binding['sourceConfigRef'] = 'other-source'
    elif change == 'reference': binding['reference'] = 'other-point'
    elif change == 'evidence-order': binding['evidencePins'].reverse()
    elif change == 'missing-evidence': binding['evidencePins'].pop()
    else: binding['extra'] = True
    with pytest.raises(RecoveryError):
        derive_archive_restore_owner(f.owner, f.request, binding, guard=lambda:None)


@pytest.mark.parametrize('change', ['targets','other-source','source','number-type'])
def test_original_recovery_owner_must_equal_complete_deterministic_result(originals, change):
    f = originals
    f.point('backup-new'); f.controller_originals()
    tampered = deepcopy(f.derived)
    if change == 'targets': tampered['targets']['target-B']['guard'] = 8
    elif change == 'other-source': tampered['sources']['other-source']['mustRemain']['values'].append(3)
    elif change == 'source': tampered['sources']['source-A']['parentChains'] = {'invented':[]}
    else: tampered['targets']['target-B']['guard'] = True
    f.replace_original('recoveryConfigurationPin', tampered)
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_DERIVED_OWNER_CHANGED'):
        f.verify()


@pytest.mark.parametrize('change', ['base','request','extra'])
def test_restore_inputs_original_must_bind_exact_base_and_request(originals, change):
    f = originals
    f.point('backup-new'); f.controller_originals()
    document = dict(request=deepcopy(f.request), ownerConfigurationPin=deepcopy(f.base_pin))
    if change == 'base': document['ownerConfigurationPin']['sha256'] = '0'*64
    elif change == 'request': document['request']['targetConfigRef'] = 'target-C'
    else: document['extra'] = None
    f.replace_original('requestInputsPin', document)
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_ORIGINAL_BINDING_INVALID'):
        f.verify()


@pytest.mark.parametrize('key', ['requestInputsPin','pointBindingPin','recoveryConfigurationPin'])
def test_equal_bytes_at_other_original_path_are_not_accepted(originals, key):
    f = originals
    f.point('backup-new'); f.controller_originals()
    reference = f.originals[key]
    f.originals[key] = f.write(f.root/Path(reference['path']).name,
        json.loads(Path(reference['path']).read_text(encoding='utf-8')))
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_ORIGINAL_PATH_INVALID'):
        f.verify()


def test_request_original_must_be_the_owner_operation_request(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    f.request_pin = f.write(f.root/'request-copy.json', f.request)
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_REQUEST_PATH_INVALID'):
        f.verify()


@pytest.mark.parametrize('kind', ['failed-exit','boolean-exit','wrong-readback','reader-open'])
def test_ordinary_original_publication_rejections_are_preserved(originals, kind):
    f = originals
    f.point('backup-new', terminal_exit=(True if kind == 'boolean-exit' else 1 if kind == 'failed-exit' else 0),
        readback_operation='foreign' if kind == 'wrong-readback' else None, closed=kind != 'reader-open')
    # Assemble the same explicit point binding from originals without calling a
    # successful validator. Both real algorithms must reject the bad metadata.
    sidecar = f.root/'archives/backup-new/.repository'
    evidence = [raw_pin(sidecar/name) for name in ('original-exit.json','readback-original.json','archive-close.json',
        'point.json','manifest.json','recovery-repository-binding.json')]
    binding = dict(schemaVersion='SmallAppArchivePointBinding/v1', sourceConfigRef='source-A',
        reference='backup-new', pointPin=evidence[3], evidencePins=evidence)
    with pytest.raises(Exception, match='ARCHIVE_ORIGINAL_PUBLICATION_INVALID'):
        bind_archive_chain(f.source, f.request)
    with pytest.raises(RecoveryError, match='ARCHIVE_ORIGINAL_PUBLICATION_INVALID'):
        derive_archive_restore_owner(f.owner, f.request, binding, guard=lambda:None)


def test_parent_prefix_is_rebuilt_instead_of_trusting_evidence_list(originals):
    f = originals
    first = f.point('first')
    second = f.point('second', [first])
    selected = f.point('backup-new', [second])
    sidecar = Path(selected['path']).parent
    binding = dict(schemaVersion='SmallAppArchivePointBinding/v1', sourceConfigRef='source-A', reference='backup-new',
        pointPin=selected, evidencePins=[raw_pin(path) for path in f.root.rglob('*.json')])
    with pytest.raises(RecoveryError, match='ARCHIVE_PARENT_PREFIX_INVALID'):
        derive_archive_restore_owner(f.owner, f.request, binding, guard=lambda:None)


def test_metadata_sha_cannot_be_waived_by_reader(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    def reader(reference, limit):
        raw = Path(reference['path']).read_bytes()
        return b' '*len(raw)
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_PIN_CHANGED'):
        f.verify(reader=reader)


def test_reader_replacement_with_equal_bytes_is_not_hidden_by_matching_sha(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    once = []
    def reader(reference, limit):
        path = Path(reference['path']); raw = path.read_bytes()
        if not once:
            once.append(path)
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(raw); replacement.chmod(0o600)
            os.replace(replacement, path)
        return raw
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_METADATA_CHANGED'):
        f.verify(reader=reader)


def test_guard_and_reader_failures_propagate_without_success(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    def failure(*args): raise RuntimeError('explicit-guard-or-reader-failure')
    for kwargs in ({'guard':failure},{'reader':failure}):
        with pytest.raises(RuntimeError, match='explicit-guard-or-reader-failure'):
            f.verify(**kwargs)


def test_final_freshness_barrier_rejects_an_earlier_original_changed_during_later_reads(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    altered = []
    def reader(reference, limit):
        raw = Path(reference['path']).read_bytes()
        if Path(reference['path']).name == 'archive-close.json' and not altered:
            altered.append(True)
            Path(f.base_pin['path']).write_bytes(b' '*f.base_pin['bytes'])
        return raw
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_METADATA_CHANGED'):
        f.verify(reader=reader)


def test_missing_original_and_strict_pin_types_are_not_accepted(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    invalid = deepcopy(f.originals); invalid['pointBindingPin']['bytes'] = True
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_PIN_INVALID'):
        verify_archive_restore_inputs(f.base_pin, f.request_pin, request_configurations_root=str(f.request_root),
            originals=invalid, guard=lambda:None)
    Path(f.originals['pointBindingPin']['path']).unlink()
    with pytest.raises(FileNotFoundError): f.verify()


def test_only_restore_requests_and_ordinary_bindings_are_accepted(originals):
    f = originals
    f.point('backup-new'); f.controller_originals()
    request = dict(f.request, action='FULL', recoveryPointRef=None, targetConfigRef=None)
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_REQUEST_INVALID'):
        derive_archive_restore_owner(f.owner, request, f.binding, guard=lambda:None)
    binding = dict(f.binding, schemaVersion='MainTargetPreservationPoint/v1')
    with pytest.raises(RecoveryError, match='RESTORE_INPUTS_POINT_BINDING_INVALID'):
        derive_archive_restore_owner(f.owner, f.request, binding, guard=lambda:None)


def sized_metadata(path, size, body=b'{}'):
    """Real valid JSON with bounded whitespace, without a large decoded value."""
    assert len(body) <= size
    with path.open('wb') as stream:
        stream.write(body)
        remaining = size - len(body)
        block = b' ' * (1024*1024)
        while remaining:
            chunk = block[:min(remaining,len(block))]
            stream.write(chunk)
            remaining -= len(chunk)
    path.chmod(0o600)
    return raw_pin(path)


@pytest.mark.parametrize('extra', [0,1], ids=['exact-64MiB','64MiB-plus-one'])
def test_total_metadata_budget_counts_unique_actual_bytes_and_not_cache_or_finish(originals, extra):
    root = originals.root
    limit = 64*1024*1024
    sizes = [16*1024*1024]*3 + [16*1024*1024-1024,1024+extra]
    references = [sized_metadata(root/('budget-'+str(index)+'.json'), size)
        for index,size in enumerate(sizes)]
    opened = []
    def actual_reader(reference, maximum):
        opened.append(reference['path'])
        with Path(reference['path']).open('rb') as stream:
            return stream.read(maximum+1)
    reads = _Reads(lambda:None, actual_reader)
    for reference in references[:-1]:
        assert reads.read(reference, 16*1024*1024) == {}
        assert reads.read(deepcopy(reference), 16*1024*1024) == {}
    if extra:
        with pytest.raises(RecoveryError, match='^RESTORE_INPUTS_METADATA_LIMIT$'):
            reads.read(references[-1], 16*1024*1024)
        assert references[-1]['path'] not in opened
    else:
        assert reads.read(references[-1], 16*1024*1024) == {}
        for reference in references:
            assert reads.read(reference, 16*1024*1024) == {}
        reads.finish()
        reads.finish()
        assert sum(pin['bytes'] for pin in reads.pins()) == limit
        assert opened == [reference['path'] for reference in references]


@pytest.mark.parametrize('extra', [0,1], ids=['exact-64MiB','64MiB-plus-one'])
def test_total_metadata_budget_includes_original_inputs_and_selected_chain(originals, extra):
    f = originals
    first = f.point('first')
    f.point('backup-new', [first]); f.controller_originals()
    baseline = f.verify()
    actual_total = sum(reference['bytes'] for reference in baseline['originalResultPins'])
    assert f.base_pin in baseline['originalResultPins'] and f.request_pin in baseline['originalResultPins']
    for reference in [*f.originals.values(), *f.binding['evidencePins']]:
        assert reference in baseline['originalResultPins']
    original = f.originals['pointBindingPin']
    body = Path(original['path']).read_bytes()
    target_size = original['bytes'] + 64*1024*1024 - actual_total + extra
    assert 0 < target_size < 64*1024*1024
    f.originals['pointBindingPin'] = sized_metadata(Path(original['path']), target_size, body)
    if extra:
        with pytest.raises(RecoveryError, match='^RESTORE_INPUTS_METADATA_LIMIT$'):
            f.verify()
    else:
        verified = f.verify()
        assert sum(reference['bytes'] for reference in verified['originalResultPins']) == 64*1024*1024
        assert verified['derivedOwner'] == f.derived and verified['clearAuthorized'] is False


def test_first_reference_above_total_budget_is_rejected_before_body_read(originals):
    reference = sized_metadata(originals.root/'first-too-large.json', 64*1024*1024+1)
    opened = []
    def actual_reader(pin, maximum):
        opened.append(pin['path'])
        with Path(pin['path']).open('rb') as stream:
            return stream.read(maximum+1)
    with pytest.raises(RecoveryError, match='^RESTORE_INPUTS_METADATA_LIMIT$'):
        _Reads(lambda:None, actual_reader).read(reference, 128*1024*1024)
    assert opened == []
