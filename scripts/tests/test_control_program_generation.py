"""Control adapters use real pinned files; resolver injection tests only routing.

These tests do not claim a restore, live MySQL, or generation validation. The
generation reader itself is covered independently with actual epoch journals.
"""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'backend/src/main/resources'), str(ROOT/'ops/recovery')]
import recovery_control_capture_config as capture_config
import recovery_control_executor as executor
from recovery_control_smallapp import Failure, fingerprint, persist
from recovery_control_smallapp_native import Native
from recovery_control_incremental_plan import PlanReader, build_plan
from test_automatic_incremental_plan import MetadataFixture, ui_request


@pytest.fixture
def case(tmp_path, monkeypatch):
    def write(name, value):
        path = tmp_path/name
        persist(path, value)
        return executor.pin(path)
    objects = write('objects.json', dict(parentExportIndexPin=None))
    base = dict(sourceConfigRef='source-A', parent=None,
        source=dict(sourceIdentity='source-id', databaseUuid='db-id', objectSourcePin=objects,
                    writerContainerIds=['old']))
    base_pin = write('base.json', base)
    effective = deepcopy(base); effective['source']['writerContainerIds'] = ['new']
    effective_pin = write('effective.json', effective)
    event_pin = write('event.json', dict(state='READY', epochId='new-epoch'))
    epoch_policy = dict(sourceIdentity='source-id',databaseUuid='db-id', sourceLockPath=str(tmp_path/'lock'))
    policy = dict(schemaVersion='RegisteredMainProgramPolicy/v1',backupEpochPolicy=epoch_policy,
                  captureConfigurationPins={'source-A':base_pin})
    control = dict(taskRoot=str(tmp_path),sourceProgramPolicies={'source-A':policy},
                   sourceEpochPolicies={'source-A':epoch_policy})
    owner = dict(sources={'source-A':dict(configurationPath=base_pin['path'])})
    owner_pin = write('owner.json',owner)
    native = Native(write('control.json',control))
    calls = []
    def resolve(policy_arg, source_ref, base_arg, *, reader, guard=None):
        calls.append((policy_arg,source_ref,base_arg,reader))
        return effective_pin,[base_pin,event_pin,effective_pin]
    module = SimpleNamespace(resolve_capture=resolve)
    monkeypatch.setitem(sys.modules,'recovery_program_generation',module)
    return SimpleNamespace(**locals())


def read(case, reader=None):
    return capture_config.read_capture_configuration(reader or case.native,case.control,case.owner,'source-A')


def test_without_policy_keeps_original_capture(case):
    case.control.pop('sourceProgramPolicies')
    reference,value,evidence = read(case)
    assert reference == case.base_pin and value == case.base and evidence == []
    assert not case.calls


def test_selected_generation_uses_caller_reader_and_all_evidence(case):
    reader = PlanReader(case.native)
    original = deepcopy((case.owner,case.base))
    reference,value,evidence = read(case,reader)
    assert reference == case.effective_pin and value == case.effective
    assert evidence == [case.base_pin,case.event_pin,case.effective_pin]
    assert case.calls[0][:3] == (case.policy,'source-A',case.base_pin)
    assert case.calls[0][3].__self__ is reader
    assert set(reader.documents) == {fingerprint(pin) for pin in evidence}
    reader.finish()
    assert original == (case.owner,case.base)


@pytest.mark.parametrize('change', ['missing','different','null_policy','invalid_map'])
def test_policy_must_bind_same_registered_epoch_before_resolver(case,change):
    if change == 'missing': case.control.pop('sourceEpochPolicies')
    elif change == 'different': case.control['sourceEpochPolicies'] = {'source-A': {'sourceIdentity':'other'}}
    elif change == 'null_policy': case.control['sourceProgramPolicies']['source-A'] = None
    else: case.control['sourceProgramPolicies'] = []
    with pytest.raises(Failure, match='SOURCE_PROGRAM_(?:EPOCH_BINDING|POLICIES)_INVALID'):
        read(case)
    assert not case.calls


@pytest.mark.parametrize('error,code',[
    (ValueError('PROGRAM_GENERATION_NOT_READY'),'PROGRAM_GENERATION_NOT_READY'),
    (ValueError('private detail /secret/path'),'SOURCE_PROGRAM_GENERATION_INVALID'),
])
def test_generation_failure_is_explicit_without_original_fallback(case,error,code):
    def fail(*args,**kwargs): raise error
    case.module.resolve_capture = fail
    with pytest.raises(Failure,match=code): read(case)


def test_resolver_cannot_return_another_source_capture(case):
    wrong = deepcopy(case.effective); wrong['sourceConfigRef'] = 'source-B'
    reference = case.write('wrong.json',wrong)
    case.module.resolve_capture = lambda *a,**kw: (reference,[case.event_pin])
    with pytest.raises(Failure,match='CAPTURE_REQUEST_SOURCE_MISMATCH'): read(case)


def test_plan_reader_detects_generation_evidence_change(case):
    reader = PlanReader(case.native)
    read(case,reader)
    Path(case.event_pin['path']).write_bytes(b'{"state":"CHANGED"}')
    with pytest.raises(Failure,match='INCREMENTAL_PLAN_INPUT_CHANGED'): reader.finish()


def test_request_inputs_retain_generation_and_effective_capture(case,monkeypatch):
    # Adapter-only test: filesystem custody is verified by the Linux suite.
    import recovery_control_smallapp_native
    monkeypatch.setattr(recovery_control_smallapp_native,'directory',lambda path,scope:Path(path))
    before = {pin['path']:Path(pin['path']).read_bytes() for pin in (case.base_pin,case.effective_pin,case.owner_pin)}
    output = capture_config.for_request(case.native,case.control,ui_request('program-request'),case.owner_pin,None)
    request_root = case.tmp_path/'request-configurations/program-request'
    inputs = case.native.document(executor.pin(request_root/'request-inputs.json'))
    assert inputs['captureConfigurationPin'] == case.effective_pin
    assert inputs['programGenerationEvidencePins'] == [case.base_pin,case.event_pin,case.effective_pin]
    repository = case.native.document(output)
    captured = case.native.document(executor.pin(repository['sources']['source-A']['configurationPath']))
    assert captured['source']['writerContainerIds'] == ['new']
    assert all(Path(path).read_bytes() == raw for path,raw in before.items())


def test_source_epoch_uses_effective_configuration(case,monkeypatch):
    import recovery_backup_epoch
    snapshot = dict(state='READY',eventPin=case.event_pin,epochId='new-epoch')
    case.effective['sourceLockPath'] = case.epoch_policy['sourceLockPath']
    case.effective_pin = case.write('effective-epoch.json',case.effective)
    case.module.resolve_capture = lambda *a,**kw: (case.effective_pin,[case.event_pin])
    case.control['sourceConfigurations'] = {'source-A':case.owner_pin}
    monkeypatch.setattr(recovery_backup_epoch,'read_current',lambda policy:snapshot)
    assert case.native.source_epoch(case.control,'source-A') == snapshot


def test_source_epoch_change_after_generation_resolution_blocks(case,monkeypatch):
    import recovery_backup_epoch
    case.effective['sourceLockPath'] = case.epoch_policy['sourceLockPath']
    reference = case.write('effective-epoch.json',case.effective)
    case.module.resolve_capture = lambda *a,**kw:(reference,[case.event_pin])
    case.control['sourceConfigurations'] = {'source-A':case.owner_pin}
    monkeypatch.setattr(recovery_backup_epoch,'read_current',lambda policy:dict(
        state='READY',eventPin=case.write('next-event.json',dict(state='READY')),epochId='next'))
    with pytest.raises(Failure,match='SOURCE_PROGRAM_EPOCH_CHANGED'):
        case.native.source_epoch(case.control,'source-A')


def test_incremental_plan_includes_generation_evidence_in_digest(tmp_path,monkeypatch):
    fixture = MetadataFixture(tmp_path)
    config = fixture.native.configuration()
    base = executor.pin(tmp_path/'capture.json')
    event = fixture.write('program-event.json',dict(state='READY'))
    config['sourceProgramPolicies'] = {'source-A':dict(backupEpochPolicy={'sourceIdentity':'fixture'})}
    config['sourceEpochPolicies'] = {'source-A':{'sourceIdentity':'fixture'}}
    fixture.native.config_pin = fixture.write('program-config.json',config)
    module = SimpleNamespace(resolve_capture=lambda *a,**kw:(base,[event]))
    monkeypatch.setitem(sys.modules,'recovery_program_generation',module)
    monkeypatch.setattr(fixture.native,'source_epoch',lambda *a,**kw:None)
    observed = build_plan(fixture.native,'source-A')
    assert observed['state'] == 'BASELINE_REQUIRED'
    owner_pin = config['sourceConfigurations']['source-A']
    assert observed['evidenceDigest'] == fingerprint([owner_pin,base,event,None])


@pytest.mark.parametrize('changed',[False,True])
def test_dispatch_binds_resolved_capture_to_same_epoch(case,monkeypatch,changed):
    import recovery_control_smallapp_native
    monkeypatch.setattr(recovery_control_smallapp_native,'directory',lambda path,scope:Path(path))
    case.control.update(sourceConfigurations={'source-A':case.owner_pin},restoreConfigurations={},
                        programPins={'repository':case.event_pin})
    monkeypatch.setattr(case.native,'configuration',lambda:case.control)
    monkeypatch.setattr(case.native,'registration',lambda _:({},case.owner_pin))
    selected = case.write('changed-epoch.json',dict(state='READY')) if changed else case.event_pin
    epoch = dict(state='READY',eventPin=selected)
    monkeypatch.setattr(case.native,'source_epoch',lambda *a,**kw:epoch)
    if changed:
        with pytest.raises(Failure,match='SOURCE_PROGRAM_EPOCH_CHANGED'):
            case.native.resolve(ui_request('dispatch-program'))
    else:
        value = case.native.resolve(ui_request('dispatch-program'))
        assert value['sourceEpoch'] == epoch


@pytest.mark.parametrize('policies,expected',[(None,'SOURCE_PROGRAM_POLICIES_INVALID'),
    ({'source-B':{}},'SOURCE_PROGRAM_POLICIES_INVALID'),
    ({'source-A':{}},'SOURCE_PROGRAM_EPOCH_BINDING_INVALID')])
def test_native_configuration_rejects_program_policy_scope(case,monkeypatch,policies,expected):
    import recovery_control_smallapp_native as module
    monkeypatch.setattr(module,'native_required',lambda:None)
    monkeypatch.setattr(module,'directory',lambda path,scope:Path(path))
    config = {key:None for key in module.SINGLE_CONFIG_FIELDS.split()}
    config.update(schemaVersion='SmallAppExecutionServiceConfig/v2',taskRoot=str(case.tmp_path),
        ledgerRoot=str(case.tmp_path/'ledger'),registryRoot=str(case.tmp_path/'registry'),
        engineSelectionRef='safe-engine',deadlineMilliseconds=1000,
        programPins={'repository':case.event_pin},sourceConfigurations={'source-A':case.owner_pin},
        restoreConfigurations={},sourceProgramPolicies=policies)
    native = Native(case.write('invalid-control.json',config))
    with pytest.raises(Failure,match=expected):native.configuration()


@pytest.mark.parametrize('completed',[False,True])
def test_real_epoch_and_generation_reader_flow_through_control(tmp_path,completed):
    from test_recovery_program_generation import case as fixture, complete, write
    real = fixture.__wrapped__(tmp_path)
    # This adapter validates host paths, so use the current host's absolute
    # fixture path rather than the resolver-only Linux example /archives.
    real['capture']['archiveRoot'] = str(tmp_path/'archives')
    real['base_pin'] = write(tmp_path/'host-capture.json',real['capture'])
    real['policy']['captureConfigurationPins']['source57'] = real['base_pin']
    generation = complete(real)[0] if completed else None
    owner = dict(sources={'source57':dict(configurationPath=real['base_pin']['path'])})
    owner_pin = write(tmp_path/'owner.json',owner)
    control = dict(sourceConfigurations={'source57':owner_pin},
        sourceEpochPolicies={'source57':real['epoch']},sourceProgramPolicies={'source57':real['policy']})
    native = Native(write(tmp_path/'control.json',control))
    reader = PlanReader(native)
    reference,value,evidence = capture_config.read_capture_configuration(reader,control,owner,'source57')
    assert reference == (generation['captureBindings']['source57']['capturePin'] if completed else real['base_pin'])
    assert value == real['capture']
    assert real['event'][1] in evidence
    snapshot = native.source_epoch(control,'source57',reader=reader,
        capture_configuration=(reference,value,evidence))
    assert snapshot['eventPin'] == real['event'][1]
    reader.finish()


def test_real_incomplete_restore_blocks_control_capture_read(tmp_path):
    from test_recovery_program_generation import case as fixture, write
    from test_backup_epoch import fixture_event
    real = fixture.__wrapped__(tmp_path)
    real['capture']['archiveRoot'] = str(tmp_path/'archives')
    real['base_pin'] = write(tmp_path/'host-capture.json',real['capture'])
    real['policy']['captureConfigurationPins']['source57'] = real['base_pin']
    fixture_event(real['epoch'],real['event'],kind='RESTORE_STARTED',state='REPLACING',operation='ongoing')
    owner = dict(sources={'source57':dict(configurationPath=real['base_pin']['path'])})
    control = dict(sourceEpochPolicies={'source57':real['epoch']},sourceProgramPolicies={'source57':real['policy']})
    native = Native(write(tmp_path/'control.json',control))
    with pytest.raises(Failure,match='PROGRAM_EPOCH_NOT_READY|BACKUP_EPOCH_(?:LINUX_LOCK_REQUIRED|SOURCE_LOCK_UNAVAILABLE|RESTORE_INTENT_REQUIRED)'):
        capture_config.read_capture_configuration(native,control,owner,'source57')


def pending_generation(tmp_path):
    """Real terminal files with a simulated crash before final epoch publication."""
    from test_recovery_program_generation import case as fixture, complete, write
    real = fixture.__wrapped__(tmp_path)
    real['capture']['archiveRoot'] = str(tmp_path/'archives')
    real['base_pin'] = write(tmp_path/'host-capture.json',real['capture'])
    real['policy']['captureConfigurationPins']['source57'] = real['base_pin']
    generation,_,receipt_pin = complete(real)
    # Preserve the real intent and terminal files; remove only the final fixture
    # event to model a process exiting before its metadata append.
    Path(real['event'][1]['path']).unlink()
    Path(real['epoch']['sourceLockPath']).touch(mode=0o600)
    owner = dict(sources={'source57':dict(configurationPath=real['base_pin']['path'])})
    owner_pin = write(tmp_path/'owner.json',owner)
    control = dict(sourceConfigurations={'source57':owner_pin},
        sourceEpochPolicies={'source57':real['epoch']},sourceProgramPolicies={'source57':real['policy']})
    native = Native(write(tmp_path/'control.json',control))
    return SimpleNamespace(**locals())


@pytest.mark.skipif(not sys.platform.startswith('linux'),reason='requires real Linux flock and epoch publication')
def test_control_reconciles_proven_generation_after_terminal_publication_crash(tmp_path):
    import recovery_backup_epoch as epoch
    fixture = pending_generation(tmp_path)
    assert epoch.read_current(fixture.real['epoch'])['state'] == 'REPLACING'
    reader = PlanReader(fixture.native)
    reference,_,evidence = capture_config.read_capture_configuration(
        reader,fixture.control,fixture.owner,'source57')
    current = epoch.read_current(fixture.real['epoch'])
    assert current['state'] == 'READY' and current['operationId'] == 'restore-1'
    assert current['eventPin'] in evidence
    assert reference == fixture.generation['captureBindings']['source57']['capturePin']
    assert len(list(Path(fixture.real['epoch']['root']).iterdir())) == 3
    assert fixture.native.source_epoch(fixture.control,'source57',reader=reader,
        capture_configuration=(reference,fixture.real['capture'],evidence)) == current
    reader.finish()


@pytest.mark.skipif(not sys.platform.startswith('linux'),reason='requires real Linux flock owner process')
def test_control_never_reconciles_while_actual_restore_lock_is_held(tmp_path):
    import recovery_backup_epoch as epoch
    fixture = pending_generation(tmp_path)
    child = subprocess.Popen([sys.executable,'-c',
        'import fcntl,os,sys; fd=os.open(sys.argv[1],os.O_RDWR); '
        'fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); print("LOCKED",flush=True); sys.stdin.readline()',
        fixture.real['epoch']['sourceLockPath']],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,text=True,encoding='utf-8')
    try:
        assert child.stdout.readline().strip() == 'LOCKED'
        before = epoch.read_current(fixture.real['epoch'])
        with pytest.raises(Failure,match='PROGRAM_EPOCH_NOT_READY'):
            capture_config.read_capture_configuration(fixture.native,fixture.control,fixture.owner,'source57')
        assert epoch.read_current(fixture.real['epoch']) == before
        assert len(list(Path(fixture.real['epoch']['root']).iterdir())) == 2
    finally:
        child.communicate('\n',timeout=5)


@pytest.mark.skipif(not sys.platform.startswith('linux'),reason='requires real Linux flock and epoch publication')
@pytest.mark.parametrize('fault,code,state',[
    ('missing','BACKUP_EPOCH_TERMINAL_RECEIPT_UNAVAILABLE','REPLACING'),
    ('target','BACKUP_EPOCH_RECEIPT_BINDING_INVALID','REPLACING'),
    ('uuid','BACKUP_EPOCH_RECEIPT_BINDING_INVALID','REPLACING'),
    ('failure','PROGRAM_EPOCH_NOT_READY','FAILED_RETAINED'),
])
def test_control_reconciliation_preserves_terminal_receipt_failures(tmp_path,fault,code,state):
    import recovery_backup_epoch as epoch
    fixture = pending_generation(tmp_path)
    path = Path(fixture.receipt_pin['path'])
    if fault == 'missing': path.unlink()
    else:
        value = json.loads(path.read_text(encoding='utf-8'))
        if fault == 'target': value['targetConfigRef'] = 'other-target'
        elif fault == 'uuid': value['databaseUuid'] = 'other-database'
        else: value['state'] = 'FAILED_RETAINED'
        path.write_text(json.dumps(value,sort_keys=True,separators=(',',':')),encoding='utf-8')
    with pytest.raises(Failure,match=code):
        capture_config.read_capture_configuration(fixture.native,fixture.control,fixture.owner,'source57')
    assert epoch.read_current(fixture.real['epoch'])['state'] == state


def test_reconciliation_checks_physical_scope_before_any_metadata_write(tmp_path,monkeypatch):
    import recovery_backup_epoch as epoch
    from test_recovery_program_generation import write
    fixture = pending_generation(tmp_path)
    fixture.real['capture']['archiveRoot'] = fixture.real['epoch']['root']
    pin = write(tmp_path/'overlap-capture.json',fixture.real['capture'])
    fixture.owner['sources']['source57']['configurationPath'] = pin['path']
    fixture.real['policy']['captureConfigurationPins']['source57'] = pin
    def forbidden(*a,**kw): pytest.fail('must validate physical scope before reconciliation')
    monkeypatch.setattr(epoch,'try_reconcile_current',forbidden)
    with pytest.raises(Failure,match='SOURCE_EPOCH_STORAGE_OVERLAP'):
        capture_config.read_capture_configuration(fixture.native,fixture.control,fixture.owner,'source57')
    assert epoch.read_current(fixture.real['epoch'])['state'] == 'REPLACING'


def test_ready_generation_does_not_add_a_reconciliation_scan(tmp_path,monkeypatch):
    import recovery_backup_epoch as epoch
    from test_recovery_program_generation import case as fixture,write
    real = fixture.__wrapped__(tmp_path)
    owner = dict(sources={'source57':dict(configurationPath=real['base_pin']['path'])})
    control = dict(sourceEpochPolicies={'source57':real['epoch']},sourceProgramPolicies={'source57':real['policy']})
    native = Native(write(tmp_path/'control.json',control))
    def forbidden(*a,**kw): pytest.fail('READY must not add a reconciliation journal scan')
    monkeypatch.setattr(epoch,'try_reconcile_current',forbidden)
    assert capture_config.read_capture_configuration(native,control,owner,'source57')[0] == real['base_pin']
