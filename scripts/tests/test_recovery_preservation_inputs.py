"""Real metadata originals; no payload validation or restore admission is faked."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal'),
    str(ROOT/'backend/src/main/resources')]
from recovery_engine import RecoveryError
from repository_records import RepositoryError, canonical
from recovery_preservation_inputs import (derive_preservation_restore_owner,
    verify_preservation_restore_inputs, resolve_preservation_control_pins, _Reads)
from test_recovery_preservation_source import metadata, put, reference
from test_recovery_preservation_source_publishers import unchanged, derived, load, sync_history
from test_recovery_restore_inputs import sized_metadata


FLAGS = ('payloadContentVerified', 'sourceAdmissionGranted', 'targetAdmitted', 'clearAuthorized')
BOUND_FIELDS = set(('schemaVersion kind originTargetConfigRef repositoryConfigurationPin '
    'sourceScopePin sourceIdentityPin policyRef sourcePolicyPin pointBindingPin '
    'publisherControlPins recoveryPoints archiveRoots repositoryBindingPinsByManifestSha256').split())


class Inputs:
    """Actual protocol files deliberately lacking any full payload proof."""
    def __init__(self, h):
        self.h = h
        self.root = h['root']
        self.scope = put(self.root/'config/selected-scope.json',
            dict(schemaVersion='RecoverySourceScope/v1', sourceIdentityPin=h['identity_pin']))
        sidecar = Path(h['point_pin']['path']).parent
        point = load(h['point_pin'])
        self.material = put(sidecar/'recovery-material.json', dict(schemaVersion='RecoveryMaterial/v1',
            pointType='FULL', recoveryPoint=point['commonRecoveryPoint'], manifestPin=point['manifestPin'],
            sourceScopePin=self.scope, payloadPins=point['payloadRefs'], protocolOnly=True))
        index = put(sidecar/'object-content-index.json', {'protocolOnly': 'not a content proof'})
        self.repository_binding = put(sidecar/'recovery-repository-binding.json',
            dict(schemaVersion='RecoveryRepositoryBinding/v1', backupId=point['backupId'],
                generationId=point['generationId'], repositoryPointPin=h['point_pin'],
                manifestPin=point['manifestPin'], sourceScopePin=self.scope,
                recoveryMaterialPin=self.material, objectContentIndexPin=index))
        proof = load(h['proof_pin'])
        proof.update(repositoryBindingPin=self.repository_binding,
            recoveryMaterialPin=self.material, objectContentIndexPin=index)
        h['proof_pin'] = put(Path(h['proof_pin']['path']), proof)
        sync_history(h)
        self.task_root = self.root/'control-task'
        self.request_root = self.task_root/'request-configurations'
        self.request_root.mkdir(parents=True)
        self.source = dict(schemaVersion='MainTargetPreservationSource/v1', kind='TARGET_PRE_RESTORE',
            originTargetConfigRef='target58', repositoryConfigurationPin=h['repository_pin'],
            sourceScopePin=self.scope, sourceIdentityPin=h['identity_pin'], policyRef='preservation-policy58')
        self.owner = dict(schemaVersion='RecoveryMinimalConfiguration/v1',
            operationsRoot=str(self.root/'new-operations'),
            sources={'preserved58': self.source, 'other-source': {'untouched': [1, {'flag': False}]}},
            targets={'target59': {'typeSensitive': 1}, 'target58': {'untouched': True}},
            sourceProgramArchivePolicies={'preserved58': {'untouched': 'five roles belong to later gates'}},
            targetPreservationPolicies=deepcopy(h['owner']['targetPreservationPolicies']),
            deadlineMilliseconds=120000)
        self.base_pin = put(self.root/'config/current-base.json', self.owner)
        self.control = dict(schemaVersion='SmallAppExecutionServiceConfig/v2', taskRoot=str(self.task_root),
            preservationSourcePolicies={'preservation-policy58': h['v2_pin']},
            restoreConfigurations={'preserved58': {'target59': self.base_pin}})
        self.control_pin = put(self.root/'config/control-000.json', self.control)
        self.controls = [self.control_pin]
        self.request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='preservation-new-001',
            action='RESTORE', sourceConfigRef='preserved58', parentChainRef=None,
            recoveryPointRef='preservation-'+hashlib.sha256(canonical(h['point_pin'])).hexdigest(),
            targetConfigRef='target59')
        self.request_pin = put(Path(self.owner['operationsRoot'])/self.request['operationId']/'request.json',
            self.request)
        self.binding = dict(schemaVersion='SmallAppPreservationPointBinding/v1',
            reference=self.request['recoveryPointRef'], sourceConfigRef='preserved58',
            sourcePolicyPin=h['v2_pin'], pointPin=h['point_pin'],
            publicationOperationId='original_restore', controlConfigurationPin=self.control_pin)
        directory = self.request_root/self.request['operationId']
        self.inputs_pin = put(directory/'restore-inputs.json',
            dict(request=self.request, ownerConfigurationPin=self.base_pin))
        self.binding_pin = put(directory/'preservation-point.json', self.binding)

    def derive(self, **kwargs):
        return derive_preservation_restore_owner(self.base_pin, self.request, self.binding_pin,
            request_configurations_root=str(self.request_root),
            publisher_control_pins=kwargs.pop('publisher_control_pins', self.controls),
            guard=kwargs.pop('guard', lambda: None), **kwargs)

    def complete(self):
        self.result = self.derive()
        self.originals = dict(requestInputsPin=self.inputs_pin, pointBindingPin=self.binding_pin,
            recoveryConfigurationPin=put(self.request_root/self.request['operationId']/'recovery.json', self.result))
        return self

    def verify(self, **kwargs):
        return verify_preservation_restore_inputs(self.base_pin, self.request_pin,
            request_configurations_root=str(self.request_root), originals=self.originals,
            publisher_control_pins=kwargs.pop('publisher_control_pins', self.controls),
            guard=kwargs.pop('guard', lambda: None), **kwargs)

    def replace_binding(self, binding):
        self.binding = binding
        self.binding_pin = put(Path(self.binding_pin['path']), binding)


@pytest.fixture(params=['unchanged', 'derived'], ids=['unchanged-publisher', 'real-A1-publisher'])
def inputs(request):
    return Inputs(request.getfixturevalue(request.param))


def test_complete_owner_is_deterministic_and_metadata_only(inputs, monkeypatch):
    f = inputs
    payloads = {f.h['payload'], *(f.root/'ordinary/archives').rglob('payload.bin')}
    opened = []
    outer = _Reads(lambda: None)
    def actual_reader(pin, maximum):
        path = Path(pin['path'])
        assert path not in payloads, 'C1_METADATA_OPENED_PAYLOAD'
        opened.append(path)
        return outer.raw(pin, maximum)
    before = {p: p.read_bytes() for p in f.root.rglob('*') if p.is_file()}
    actual = f.derive(reader=actual_reader, fixed_reader=outer.fixed)
    outer.finish()
    expected = deepcopy(f.owner)
    expected['sources']['preserved58'] = dict(f.source,
        schemaVersion='MainTargetPreservationBoundSource/v1', sourcePolicyPin=f.h['v2_pin'],
        pointBindingPin=dict(f.binding_pin, path=Path(f.binding_pin['path']).as_posix()), publisherControlPins=[f.control_pin],
        recoveryPoints={f.request['recoveryPointRef']: f.h['point_pin']},
        archiveRoots=[str(f.h['repository'])],
        repositoryBindingPinsByManifestSha256={load(f.h['point_pin'])['manifestPin']['sha256']: f.repository_binding})
    assert canonical(actual) == canonical(expected)
    assert set(actual['sources']['preserved58']) == BOUND_FIELDS
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert opened and f.control_pin['path'] in [str(p) for p in opened]
    actual['targets']['target59']['typeSensitive'] = 9
    assert f.owner['targets']['target59']['typeSensitive'] == 1


def test_three_originals_and_full_owner_verify_never_grant_permissions(inputs):
    f = inputs.complete()
    result = f.verify()
    assert result['schemaVersion'] == 'PreservationRestoreInputsVerification/v1'
    assert result['derivedOwner'] == f.result
    assert result['baseOwnerPin'] == f.base_pin and result['requestPin'] == f.request_pin
    assert result['originals'] == f.originals and result['controlConfigurationPin'] == f.control_pin
    assert result['sourcePolicyPin'] == f.h['v2_pin']
    assert all(result[flag] is False for flag in FLAGS)
    for pin in [f.base_pin, f.request_pin, f.control_pin, *f.originals.values(), f.repository_binding, f.material]:
        assert pin in result['originalResultPins']
    if 'a1' in f.h:
        for pin in [f.h['a1'].base_pin, *f.h['a1'].originals.values()]:
            assert pin in result['originalResultPins']
    assert len({str(Path(p['path'])) for p in result['originalResultPins']}) == len(result['originalResultPins'])


@pytest.mark.parametrize('change', ['target', 'other-source', 'type'])
def test_non_source_owner_drift_is_rejected(inputs, change):
    f = inputs.complete()
    owner = deepcopy(f.result)
    if change == 'target': owner['targets']['target59']['typeSensitive'] = 2
    elif change == 'other-source': owner['sources']['other-source']['untouched'].append(3)
    else: owner['targets']['target59']['typeSensitive'] = True
    f.originals['recoveryConfigurationPin'] = put(Path(f.originals['recoveryConfigurationPin']['path']), owner)
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_DERIVED_OWNER_CHANGED'):
        f.verify()


@pytest.mark.parametrize('change', ['extra', 'reference', 'source', 'point', 'old-op', 'control', 'policy'])
def test_exact_binding_cannot_select_other_originals(inputs, change):
    f = inputs
    binding = deepcopy(f.binding)
    if change == 'extra': binding['evidencePins'] = []
    elif change == 'reference': binding['reference'] = 'another-reference'
    elif change == 'source': binding['sourceConfigRef'] = 'another-source'
    elif change == 'point': binding['pointPin']['sha256'] = '0'*64
    elif change == 'old-op': binding['publicationOperationId'] = f.request['operationId']
    elif change == 'control': binding['controlConfigurationPin'] = f.base_pin
    else: binding['sourcePolicyPin'] = f.h['preservation_policy']
    f.replace_binding(binding)
    with pytest.raises((RecoveryError, RepositoryError)):
        f.derive()


@pytest.mark.parametrize('key', ['requestInputsPin', 'pointBindingPin', 'recoveryConfigurationPin'])
def test_originals_require_exact_paths_and_all_three_files(inputs, key):
    f = inputs.complete()
    f.originals[key] = put(f.root/('copy-'+Path(f.originals[key]['path']).name), load(f.originals[key]))
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_ORIGINAL_PATH_INVALID'):
        f.verify()


def test_future_retained_control_does_not_change_original_owner(inputs):
    f = inputs.complete()
    successor = dict(f.control, retainedPreservationControlPins=[f.control_pin])
    successor_pin = put(f.root/'config/control-001.json', successor)
    resolution = resolve_preservation_control_pins(successor_pin, guard=lambda: None)
    assert set(resolution) == {'schemaVersion','currentControlPin','publisherControlPins','originalResultPins','metadataBytes'}
    assert resolution['schemaVersion'] == 'PreservationControlPinsResolution/v1'
    assert resolution['publisherControlPins'] == [successor_pin, f.control_pin]
    assert resolution['currentControlPin'] == successor_pin
    assert resolution['metadataBytes'] == sum(p['bytes'] for p in resolution['originalResultPins'])
    assert f.verify(publisher_control_pins=resolution['publisherControlPins'])['derivedOwner'] == f.result


def test_nas_binding_cannot_promote_an_untrusted_control(inputs):
    f = inputs
    foreign = put(f.root/'config/untrusted-control.json', dict(f.control, unapproved=True))
    f.replace_binding(dict(f.binding, controlConfigurationPin=foreign))
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_CONTROL_UNTRUSTED'):
        f.derive()


@pytest.mark.parametrize('extra', [0, 1], ids=['exact-64MiB','64MiB-plus-one'])
def test_raw_budget_is_unique_shared_and_never_reset(tmp_path, extra):
    sizes = [16*1024*1024]*3 + [16*1024*1024-1024, 1024+extra]
    pins = [sized_metadata(tmp_path/('budget-'+str(i)+'.json'), size) for i, size in enumerate(sizes)]
    seen = []
    def actual(pin, maximum):
        seen.append(pin['path'])
        return Path(pin['path']).read_bytes()
    reads = _Reads(lambda: None, actual)
    for pin in pins[:-1]:
        assert reads.read(pin, 16*1024*1024) == {}
        assert reads.read(deepcopy(pin), 16*1024*1024) == {}
    if extra:
        with pytest.raises(RecoveryError, match='METADATA_LIMIT'):
            reads.read(pins[-1], 16*1024*1024)
        assert pins[-1]['path'] not in seen
    else:
        assert reads.read(pins[-1], 16*1024*1024) == {}
        reads.finish()
        assert sum(p['bytes'] for p in reads.pins()) == 64*1024*1024
        assert seen == [p['path'] for p in pins]


@pytest.mark.parametrize('count', [32, 33], ids=['exact-32-controls','33-controls'])
def test_control_closure_is_real_bounded_and_sorted(tmp_path, count):
    pins = []
    for i in range(count):
        value = dict(schemaVersion='SmallAppExecutionServiceConfig/v2')
        if pins: value['retainedPreservationControlPins'] = [pins[-1]]
        pins.append(put(tmp_path/('control-'+str(i).zfill(3)+'.json'), value))
    if count > 32:
        with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_HISTORY_LIMIT'):
            resolve_preservation_control_pins(pins[-1], guard=lambda: None)
    else:
        result = resolve_preservation_control_pins(pins[-1], guard=lambda: None)
        assert result['publisherControlPins'] == [pins[-1], *pins[:-1]]
        assert sorted(result['originalResultPins'], key=lambda p: p['path']) == pins


@pytest.mark.parametrize('change', ['duplicate','unsorted','cycle','boolean-pin'])
def test_control_retained_graph_rejects_invalid_originals(tmp_path, change):
    first = put(tmp_path/'a.json', {'schemaVersion':'SmallAppExecutionServiceConfig/v2'})
    second = put(tmp_path/'b.json', {'schemaVersion':'SmallAppExecutionServiceConfig/v2'})
    retained = [first, second]
    path = tmp_path/'root.json'
    if change == 'duplicate': retained = [first, first]
    elif change == 'unsorted': retained.reverse()
    elif change == 'boolean-pin': retained[0] = dict(first, bytes=True)
    else:
        path = Path(first['path']); retained = [first]
    root = put(path, dict(schemaVersion='SmallAppExecutionServiceConfig/v2', retainedPreservationControlPins=retained))
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_(CONTROL_CHANGED|HISTORY_CYCLE|PIN_INVALID)'):
        resolve_preservation_control_pins(root, guard=lambda: None)


def test_control_resolver_uses_callers_existing_raw_meter(tmp_path):
    control = put(tmp_path/'control.json', {'schemaVersion':'SmallAppExecutionServiceConfig/v2'})
    outer = _Reads(lambda: None)
    outer.total_limit = control['bytes'] + 1
    existing = sized_metadata(tmp_path/'already-read.json', 2)
    outer.read(existing)
    with pytest.raises(RecoveryError, match='METADATA_LIMIT'):
        resolve_preservation_control_pins(control, guard=lambda: None, reader=outer.raw)
    assert [p['path'] for p in outer.pins()] == [existing['path']]


def test_external_reader_cannot_waive_actual_file_finish(tmp_path):
    original = b'{"value":1}'
    path = tmp_path/'original.json'; path.write_bytes(original)
    pin = reference(path)
    path.write_bytes(b'{"value":2}')
    reads = _Reads(lambda: None, lambda reference, maximum: original)
    assert reads.read(pin) == {'value':1}
    with pytest.raises(RecoveryError, match='METADATA_CHANGED'):
        reads.finish()


def test_document_limit_rejects_before_body_read(tmp_path):
    pin = sized_metadata(tmp_path/'large.json', 16*1024*1024+1)
    opened = []
    with pytest.raises(RecoveryError, match='METADATA_LIMIT'):
        _Reads(lambda: None, lambda pin, maximum: opened.append(pin)).read(pin)
    assert not opened


@pytest.mark.parametrize('change', ['base','request','extra','missing'])
def test_restore_inputs_requires_exact_existing_original(inputs, change):
    f = inputs
    value = load(f.inputs_pin)
    if change == 'base': value['ownerConfigurationPin'] = f.control_pin
    elif change == 'request': value['request']['targetConfigRef'] = 'target58'
    elif change == 'extra': value['extra'] = True
    else:
        Path(f.inputs_pin['path']).unlink()
        with pytest.raises(FileNotFoundError): f.derive()
        return
    f.inputs_pin = put(Path(f.inputs_pin['path']), value)
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_ORIGINAL_BINDING_INVALID'):
        f.derive()


def test_unrelated_caller_pin_is_not_a_retained_generation(inputs):
    f = inputs
    other = put(f.root/'config/unrelated.json', dict(f.control, unrelated=True))
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_CONTROL_UNTRUSTED'):
        f.derive(publisher_control_pins=[f.control_pin, other])


def test_guard_error_is_not_swallowed(inputs):
    def stop(): raise RuntimeError('C1_EXPLICIT_GUARD_STOP')
    with pytest.raises(RuntimeError, match='C1_EXPLICIT_GUARD_STOP'):
        inputs.derive(guard=stop)


def test_restore_inputs_64kib_cap_precedes_first_body_read(inputs, monkeypatch):
    import recovery_preservation_inputs as module
    f = inputs
    path = Path(f.inputs_pin['path'])
    raw = path.read_bytes()
    path.write_bytes(raw + b' ' * (65537-len(raw)))
    actual = module._read_file
    def checked(candidate, maximum):
        assert Path(candidate) != path, 'C1_RESTORE_INPUTS_BODY_OPENED_BEFORE_64KIB_CHECK'
        return actual(candidate, maximum)
    monkeypatch.setattr(module, '_read_file', checked)
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_METADATA_LIMIT'):
        f.derive()


def test_same_original_path_spellings_derive_identical_complete_owner(inputs):
    f = inputs
    original = f.derive()
    alternate = deepcopy(f.binding_pin)
    alternate['path'] = Path(alternate['path']).as_posix()
    actual = derive_preservation_restore_owner(f.base_pin, f.request, alternate,
        request_configurations_root=str(f.request_root), publisher_control_pins=f.controls, guard=lambda:None)
    assert canonical(actual) == canonical(original)
    assert original['sources']['preserved58']['pointBindingPin']['path'] == Path(f.binding_pin['path']).as_posix()


def test_shared_fixed_reader_rejects_before_body_when_outer_budget_is_used(tmp_path, monkeypatch):
    import recovery_preservation_inputs as module
    existing = sized_metadata(tmp_path/'existing.json', 2)
    candidate = sized_metadata(tmp_path/'fixed.json', 32)
    outer = module._source._Reads(lambda: None)
    outer.total_limit = 33
    outer.read(existing)
    actual = module._read_file
    def checked(path, maximum):
        assert Path(path) != Path(candidate['path']), 'C1_SHARED_FIXED_OPENED_BODY_BEFORE_OUTER_BUDGET'
        return actual(path, maximum)
    monkeypatch.setattr(module, '_read_file', checked)
    monkeypatch.setattr(module._source, '_read_file', checked)
    reads = _Reads(lambda: None, reader=outer.raw, fixed_reader=outer.fixed)
    with pytest.raises((RecoveryError, RepositoryError), match='METADATA_LIMIT'):
        reads.fixed(Path(candidate['path']), 64)
    assert reads.total == 0 and outer.total == 2
    assert candidate not in reads.pins() and candidate not in outer.pins()


def test_external_fixed_read_requires_explicit_shared_callback(tmp_path, monkeypatch):
    import recovery_preservation_inputs as module
    pin = sized_metadata(tmp_path/'fixed.json', 32)
    outer = _Reads(lambda: None)
    def forbidden(path, maximum):
        raise AssertionError('C1_FIXED_WITHOUT_CALLBACK_OPENED_BODY')
    monkeypatch.setattr(module, '_read_file', forbidden)
    with pytest.raises(RecoveryError, match='PRESERVATION_RESTORE_FIXED_READER_REQUIRED'):
        _Reads(lambda: None, reader=outer.raw).fixed(Path(pin['path']))


@pytest.mark.parametrize('change', ['path','bytes','sha256'])
def test_shared_fixed_callback_pin_never_replaces_real_raw(tmp_path, change):
    pin = sized_metadata(tmp_path/'fixed.json', 32)
    other = sized_metadata(tmp_path/'other.json', 32)
    returned = deepcopy(pin)
    if change == 'path': returned = other
    elif change == 'bytes': returned['bytes'] = 33
    else: returned['sha256'] = '0'*64
    outer = _Reads(lambda: None)
    reads = _Reads(lambda: None, reader=outer.raw,
        fixed_reader=lambda path, maximum: (returned, {'notActual': True}))
    with pytest.raises((RecoveryError, RepositoryError)):
        reads.fixed(Path(pin['path']), 32)
