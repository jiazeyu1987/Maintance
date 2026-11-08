"""Owner adapter units and separate real-file program-generation integrations."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'backend/src/main/resources')]
from recovery_engine import RecoveryError
from recovery_program_generation import document
from test_recovery_program_generation import case as generation_fixture, complete, switched, write


def module():
    return importlib.import_module('recovery_program_targets')


@pytest.fixture
def owner_case(tmp_path):
    real = generation_fixture.__wrapped__(tmp_path)
    owner = dict(targets={'target57':deepcopy(real['target']),'other':{'untouched':'target'}},
        sources={'source57':{'untouched':'source'}}, operationsRoot=str(tmp_path/'operations'),
        targetProgramPolicies={'target57':real['policy']},
        targetBackupEpochPolicies={'target57':real['epoch']}, other={'nested':['keep']})
    return SimpleNamespace(real=real,owner=owner)


def test_no_selected_policy_preserves_original_owner_contract(owner_case):
    owner = owner_case.owner
    owner.pop('targetProgramPolicies')
    effective,binding = module().resolve_configuration(owner,'target57')
    assert effective is owner and binding is None


def test_unselected_target_policy_does_not_change_other_target(owner_case):
    effective,binding = module().resolve_configuration(owner_case.owner,'other')
    assert effective is owner_case.owner and binding is None


@pytest.mark.parametrize('problem,code',[
    ('not-map','PROGRAM_TARGET_POLICIES_INVALID'),
    ('unknown-target','PROGRAM_TARGET_POLICIES_INVALID'),
    ('policy-ref','PROGRAM_TARGET_POLICY_BINDING_INVALID'),
    ('missing-epoch','PROGRAM_TARGET_EPOCH_BINDING_INVALID'),
    ('epoch-change','PROGRAM_TARGET_EPOCH_BINDING_INVALID'),
    ('baseline-change','PROGRAM_TARGET_BASELINE_CHANGED'),
    ('non-main','PROGRAM_TARGET_MAIN_REQUIRED'),
])
def test_owner_binding_mismatch_rejects_before_resolver(owner_case,monkeypatch,problem,code):
    import recovery_program_generation
    owner = owner_case.owner
    if problem == 'not-map': owner['targetProgramPolicies'] = []
    elif problem == 'unknown-target': owner['targetProgramPolicies']['unknown'] = owner['targetProgramPolicies']['target57']
    elif problem == 'policy-ref': owner['targetProgramPolicies']['target57']['targetConfigRef'] = 'other'
    elif problem == 'missing-epoch': owner.pop('targetBackupEpochPolicies')
    elif problem == 'epoch-change': owner['targetBackupEpochPolicies']['target57'] = {'different':'epoch'}
    elif problem == 'baseline-change': owner['targets']['target57']['database'] = 'other'
    else: owner['targets']['target57'].pop('mainApplication')
    def forbidden(*a,**kw):pytest.fail('invalid owner must not reach generation resolver')
    monkeypatch.setattr(recovery_program_generation,'resolve_target',forbidden)
    with pytest.raises(RecoveryError,match=code):module().resolve_configuration(owner,'target57')


def test_adapter_passes_original_reader_and_guard_and_keeps_private_binding(owner_case,monkeypatch):
    """Dependency injection tests routing; it is not a real restore proof."""
    import recovery_program_generation
    owner = owner_case.owner
    before = deepcopy(owner)
    active = deepcopy(owner['targets']['target57']); active['active-unit-marker'] = True
    selected = write(owner_case.real['root']/'unit-active.json',active)
    evidence = [owner_case.real['policy']['baselineTargetPin'],owner_case.real['event'][1],selected]
    calls = []; reads = []; guards = []
    def reader(reference):reads.append(reference); return document(reference)
    def guard():guards.append(1)
    def resolve(policy,*,reader,guard):
        calls.append((policy,reader,guard));guard()
        return active,selected,evidence
    monkeypatch.setattr(recovery_program_generation,'resolve_target',resolve)
    effective,binding = module().resolve_configuration(owner,'target57',reader=reader,guard=guard)
    assert calls == [(owner['targetProgramPolicies']['target57'],reader,guard)]
    assert owner_case.real['policy']['baselineTargetPin'] in reads and guards
    assert effective['targets']['target57'] == active and effective is not owner
    assert binding == dict(policy=owner['targetProgramPolicies']['target57'],targetPin=selected,evidencePins=evidence)
    assert owner == before
    assert {k:v for k,v in effective.items() if k!='targets'} == {k:v for k,v in owner.items() if k!='targets'}
    effective['other']['nested'].append('local')
    assert owner == before


@pytest.mark.parametrize('generation',['initial','completed','switched'])
def test_real_journal_resolves_only_proven_active_target_without_changing_owner(owner_case,generation):
    """Actual immutable journal, receipt and switch proof; no resolver injection."""
    real = owner_case.real
    target = real['target']; record = None
    if generation == 'switched':
        target,capture,switch = switched(real,real['root'])
        owner_case.owner['targets']['target57'] = deepcopy(real['target'])
        record = complete(real,target=target,capture=capture,generation_changes={'switchResultPin':switch})[0]
    elif generation == 'completed': record = complete(real)[0]
    owner_pin = write(real['root']/'owner.json',owner_case.owner)
    before = {str(p):p.read_bytes() for p in real['root'].rglob('*.json')}
    effective,binding = module().resolve_configuration(document(owner_pin),'target57')
    assert effective['targets']['target57'] == target
    assert binding['targetPin'] == (record['targetPin'] if record else real['policy']['baselineTargetPin'])
    assert real['event'][1] in binding['evidencePins']
    assert {str(p):p.read_bytes() for p in real['root'].rglob('*.json')} == before
    assert effective['targets']['other'] == owner_case.owner['targets']['other']


@pytest.mark.parametrize('state',['REPLACING','FAILED_RETAINED'])
def test_real_nonready_epoch_never_falls_back_to_owner(owner_case,state):
    from test_backup_epoch import fixture_event
    real = owner_case.real
    start = fixture_event(real['epoch'],real['event'],kind='RESTORE_STARTED',state='REPLACING',operation='unfinished')
    if state == 'FAILED_RETAINED':
        receipt = write(real['root']/'failure.json',dict(operationId='unfinished',state='FAILED_RETAINED'))
        fixture_event(real['epoch'],start,kind='RESTORE_FINISHED',state=state,operation='unfinished',evidence=receipt)
    with pytest.raises(RecoveryError,match='PROGRAM_EPOCH_NOT_READY'):
        module().resolve_configuration(owner_case.owner,'target57')


def test_real_capture_source_mismatch_rejects_target_generation(owner_case):
    real = owner_case.real
    capture = deepcopy(real['capture']);capture['source']['sourceIdentity'] = 'other'
    complete(real,capture=capture)
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_SCOPE_CHANGED'):
        module().resolve_configuration(owner_case.owner,'target57')


def test_real_pinned_target_drift_is_not_original_owner_fallback(owner_case):
    record = complete(owner_case.real)[0]
    Path(record['targetPin']['path']).write_text('{}',encoding='utf-8')
    with pytest.raises(RecoveryError,match='PROGRAM_DOCUMENT_CHANGED'):
        module().resolve_configuration(owner_case.owner,'target57')


def test_observer_uses_active_target_but_retains_original_configuration_pin(tmp_path,monkeypatch):
    """Control observation adapter only; Docker and validation are unit fixtures."""
    import recovery_main_target as main
    import recovery_replace
    binary = write(tmp_path/'docker',{'unit':'not executable'})
    row = dict(Id='new-backend',Image='new-image',Path='/entry',Args=[],Mounts=[],ExecIDs=None,
        Config={'Labels':{}},HostConfig={'NetworkMode':'main'},State={'Running':False},
        NetworkSettings={'Networks':{}})
    target = dict(targetId='main57',mainApplication={},dockerPin=binary,dataPolicy={},replacement={},secrets={},
        machineId='machine',dockerEngineId='engine',services=[dict(role='mysql',id='mysql'),dict(role='backend',id='old-backend')])
    active = deepcopy(target);active['services'][1]['id'] = 'new-backend'
    owner = dict(targets={'target57':target},sources={'source57':{}},
        environmentMysqlClientPath='/mysql',operationsRoot=str(tmp_path/'operations'))
    owner_pin = write(tmp_path/'owner.json',owner)
    control = SimpleNamespace(document=document)
    calls = []
    def resolve(configuration,reference,*,reader,**kwargs):
        calls.append((configuration,reference,reader))
        return dict(configuration,targets={'target57':active}),{'private':'binding'}
    monkeypatch.setitem(sys.modules,'recovery_program_targets',SimpleNamespace(resolve_configuration=resolve))
    monkeypatch.setattr(main,'validate',lambda target:None)
    monkeypatch.setattr(main,'check_pin',lambda *a,**kw:None)
    monkeypatch.setattr(main,'verify_runtime',lambda *a,**kw:None)
    monkeypatch.setattr(main,'verify_redis_authentication',lambda *a,**kw:None)
    monkeypatch.setattr(recovery_replace,'verify_services',lambda *a,**kw:None)
    observed = []
    def run(argv,**kw):
        identity = argv[-1];observed.append(identity)
        return SimpleNamespace(returncode=0,stderr=b'',stdout=json.dumps([dict(row,Id=identity)]).encode())
    monkeypatch.setattr(main.subprocess,'run',run)
    read_text = Path.read_text
    monkeypatch.setattr(Path,'read_text',lambda path,*a,**kw:
        'boot-unit' if str(path).replace('\\','/')=='/proc/sys/kernel/random/boot_id' else read_text(path,*a,**kw))
    result = main.observe_main_target(control,dict(operationId='observe',targetConfigRef='target57',sourceConfigRef='source57'),
        dict(ownerConfigurationPin=owner_pin))
    assert calls and calls[0] == (owner,'target57',control.document)
    assert 'new-backend' in observed and 'old-backend' not in observed
    assert result['configurationPin'] == owner_pin
    assert 'binding' not in json.dumps(result) and 'evidencePins' not in result
