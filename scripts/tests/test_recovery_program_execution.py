"""Operation-private execution contracts using real files, epochs and Linux locks.

Only resource observation is a unit seam: no Docker/host capacity result here is
claimed as a real deployment admission. Reservation and physical locks are real.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os
import sys

import pytest

from test_recovery_program_generation import case, switched, write
from test_recovery_program_activation import locked, claim, start, snapshot, stage, finish
from recovery_engine import digest, pinned_json
import recovery_resource_admission as admission

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux flock required')


def module():
    import recovery_program_execution
    return recovery_program_execution


@pytest.fixture
def execution(case, monkeypatch):
    base = case['root']
    target = case['target']
    target.update(machineId='private-test-machine', dataRoot=str(base), resourceBudget=dict(
        schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=1,
        hostAvailableMemoryBytes=1, diskBytesByPath={str(base): 1}))
    candidate, capture, switch = switched(case, base)
    operations = base/'operations'; operations.mkdir(mode=0o700)
    operation = operations/'restore-1'; operation.mkdir(mode=0o700)
    host = base/'resource-host'; host.mkdir(mode=0o700)
    machine = base/'machine-id'; machine.write_text(target['machineId'], encoding='ascii')
    monkeypatch.setattr(admission, 'HOST_ROOT', host)
    monkeypatch.setattr(admission, 'MACHINE_ID', machine)
    observations = []
    def observe(owner, request, policy):
        observations.append(deepcopy(owner))
        return dict(mysqlMemoryLimitBytes=10, hostAvailableMemoryBytes=10,
                    disks=[dict(path=str(base), device=1, freeBytes=10)])
    monkeypatch.setattr(admission, 'observe_resources', observe)
    owner = dict(operationsRoot=str(operations), targets={'target57':deepcopy(target), 'other':{'keep':True}},
        sources={'source57':{'keep':True}}, targetProgramPolicies={'target57':deepcopy(case['policy'])},
        targetBackupEpochPolicies={'target57':deepcopy(case['epoch'])}, unrelated={'keep':['exact']})
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-1', action='RESTORE',
        sourceConfigRef='source57', parentChainRef=None, recoveryPointRef='point1', targetConfigRef='target57')
    owner_pin = write(operation/'configuration.json', owner)
    request_pin = write(operation/'request.json', request)
    reservation = admission.reserve(owner, request, operation)
    root = claim(case)
    return SimpleNamespace(case=case, owner=owner, request=request, root=operation, claim=root,
        owner_pin=owner_pin, request_pin=request_pin, reservation=reservation,
        candidate=candidate, capture=capture, switch=switch, observations=observations)


def bind(e, fd):
    context = snapshot(e.case, fd)
    binding = module().bind_execution(e.owner, e.request, e.root, context, fd)
    return context, binding


def resolve(e, binding, fd, **kwargs):
    return module().resolve_execution_configuration(e.owner, e.request, e.root,
        binding_pin=binding, lock_fd=fd, **kwargs)


def staged(e, context, fd):
    current = start(e.case, e.claim, fd)
    target_pin = write(e.claim/'target.json', e.candidate)
    capture_pin = write(e.claim/'capture.json', e.capture)
    generation = stage(e.case, context, fd, target_pin=target_pin,
        capture_pins={'source57':capture_pin}, switch_result_pin=e.switch)
    return current, generation


def test_binding_records_original_owner_request_reservation_and_is_immutable(execution):
    e = execution
    before = {Path(p['path']):Path(p['path']).read_bytes()
              for p in (e.owner_pin, e.request_pin, e.reservation)}
    with locked(e.case) as fd:
        context, binding = bind(e, fd)
        assert Path(binding['path']) == e.claim/'program-execution-binding.json'
        value = pinned_json(binding)
        assert value['schemaVersion'] == 'MainProgramExecutionBinding/v1'
        assert value['configurationPin'] == e.owner_pin
        assert value['requestPin'] == e.request_pin
        assert value['reservationPin'] == e.reservation
        assert value['contextPin'] == context
        original = Path(binding['path']).read_bytes()
        with pytest.raises(Exception, match='PROGRAM_METADATA_ALREADY_EXISTS'):
            module().bind_execution(e.owner, e.request, e.root, context, fd)
        assert Path(binding['path']).read_bytes() == original
    assert all(path.read_bytes() == data for path,data in before.items())


@pytest.mark.parametrize('phase', ['ready', 'replacing', 'staged'])
@pytest.mark.parametrize('runtime', [False, True])
def test_actual_context_and_stage_resolve_private_target_without_mutating_owner(execution, phase, runtime):
    e = execution; original = deepcopy(e.owner)
    if runtime: (e.claim/'runtime').mkdir(mode=0o700)
    with locked(e.case) as fd:
        context, binding = bind(e, fd)
        generation = None
        if phase == 'replacing': start(e.case, e.claim, fd)
        elif phase == 'staged': _,generation = staged(e, context, fd)
        effective, evidence = resolve(e, binding, fd, generation_pin=generation, runtime=runtime)
    expected = deepcopy(e.owner)
    expected['targets']['target57'] = deepcopy(e.candidate if phase=='staged' else e.case['target'])
    if runtime: expected['targets']['target57']['dataRoot'] = str(e.claim/'runtime')
    assert effective == expected and e.owner == original
    assert evidence['bindingPin'] == binding and evidence['contextPin'] == context
    assert evidence['generationPin'] == generation
    assert evidence['reservationPin'] == e.reservation
    effective['unrelated']['keep'].append('local')
    assert e.owner == original


@pytest.mark.parametrize('field', ['targetPin', 'parentGenerationPin', 'capturePins', 'readyEpoch', 'operationId', 'policySha256'])
def test_valid_sha_context_must_reconstruct_exact_actual_ready_history(execution, field):
    e = execution
    with locked(e.case) as fd:
        context = snapshot(e.case, fd); value = pinned_json(context)
        if field == 'targetPin': value[field] = write(e.claim/'same-target.json', e.case['target'])
        elif field == 'parentGenerationPin': value[field] = e.case['policy']['baselineTargetPin']
        elif field == 'capturePins': value[field] = {'source57':write(e.claim/'same-capture.json', e.case['capture'])}
        elif field == 'readyEpoch': value[field] = dict(value[field], epochId='0'*64)
        elif field == 'operationId': value[field] = 'different'
        else: value[field] = '0'*64
        changed = write(Path(context['path']), value)
        with pytest.raises(Exception, match='PROGRAM_'):
            module().bind_execution(e.owner, e.request, e.root, changed, fd)
    assert not (e.claim/'program-execution-binding.json').exists()


@pytest.mark.parametrize('field', ['sourceConfigRef', 'recoveryPointRef', 'targetConfigRef'])
def test_request_must_equal_fixed_original_before_binding(execution, field):
    e = execution
    with locked(e.case) as fd:
        context = snapshot(e.case, fd)
        changed = dict(e.request, **{field:'other'})
        with pytest.raises(Exception, match='PROGRAM_|MINIMAL_'):
            module().bind_execution(e.owner, changed, e.root, context, fd)
    assert not (e.claim/'program-execution-binding.json').exists()


@pytest.mark.parametrize('field', ['configurationSha256', 'operationId', 'targetConfigRef', 'operationRoot'])
def test_reservation_cannot_be_rebound_to_valid_but_different_identity(execution, field):
    e = execution
    value = pinned_json(e.reservation); value[field] = 'different'
    write(Path(e.reservation['path']), value)
    with locked(e.case) as fd:
        context = snapshot(e.case, fd)
        with pytest.raises(Exception, match='RESTORE_RESOURCE_|PROGRAM_'):
            module().bind_execution(e.owner, e.request, e.root, context, fd)
    assert not (e.claim/'program-execution-binding.json').exists()


@pytest.mark.parametrize('phase', ['bind', 'resolve'])
@pytest.mark.parametrize('problem', ['unheld', 'wrong-file'])
def test_actual_same_physical_exclusive_lock_required(execution, phase, problem):
    e = execution
    with locked(e.case) as fd:
        context = snapshot(e.case, fd)
        if phase == 'resolve': binding = module().bind_execution(e.owner,e.request,e.root,context,fd)
    if problem == 'wrong-file': e.case['epoch'] = dict(e.case['epoch'],sourceLockPath=str(e.case['root']/'wrong.lock'))
    with locked(e.case, held=problem=='wrong-file') as fd:
        with pytest.raises(Exception, match='BACKUP_EPOCH_'):
            if phase == 'bind': module().bind_execution(e.owner,e.request,e.root,context,fd)
            else: resolve(e,binding,fd)


@pytest.mark.parametrize('original', ['configuration.json', 'request.json', 'resource-reservation.json', 'program-context.json'])
def test_original_change_after_binding_blocks_resolution(execution, original):
    e=execution
    with locked(e.case) as fd:
        _,binding=bind(e,fd)
        path=(e.claim if original=='program-context.json' else e.root)/original
        path.write_bytes(b'{}')
        with pytest.raises(Exception, match='PROGRAM_|RESTORE_RESOURCE_'):
            resolve(e,binding,fd)


@pytest.mark.parametrize('problem', ['missing', 'symlink', 'public'])
def test_runtime_root_must_be_exact_existing_private_directory(execution, problem):
    e=execution
    if problem=='symlink': (e.claim/'runtime').symlink_to(e.case['root'],target_is_directory=True)
    elif problem=='public': (e.claim/'runtime').mkdir(mode=0o755)
    with locked(e.case) as fd:
        _,binding=bind(e,fd)
        with pytest.raises(Exception, match='PROGRAM_|PATH_ALIAS_'):
            resolve(e,binding,fd,runtime=True)


@pytest.mark.parametrize('phase', ['bind','resolve'])
def test_shared_guard_propagates_without_fallback(execution,phase):
    e=execution
    def expired(): raise TimeoutError('execution guard expired')
    with locked(e.case) as fd:
        context=snapshot(e.case,fd)
        if phase=='resolve': binding=module().bind_execution(e.owner,e.request,e.root,context,fd)
        with pytest.raises(TimeoutError,match='execution guard expired'):
            if phase=='bind': module().bind_execution(e.owner,e.request,e.root,context,fd,guard=expired)
            else: resolve(e,binding,fd,guard=expired)


@pytest.mark.parametrize('state', ['foreign-operation', 'FAILED_RETAINED', 'SUCCEEDED'])
def test_execution_cannot_cross_operation_or_completed_epoch(execution,state):
    e=execution
    with locked(e.case) as fd:
        context,binding=bind(e,fd)
        if state=='foreign-operation':
            other=claim(e.case,'other'); start(e.case,other,fd,operation='other')
        else:
            current,generation=staged(e,context,fd)
            finish(e.case,e.claim,current,generation,fd,state=state)
        with pytest.raises(Exception,match='PROGRAM_'):
            resolve(e,binding,fd)


@pytest.mark.parametrize('field', ['operationId','parentGenerationPin','targetPin','captureBindings','epochId'])
def test_re_pinned_stage_is_revalidated_not_trusted_by_sha(execution,field):
    e=execution
    with locked(e.case) as fd:
        context,binding=bind(e,fd); _,generation=staged(e,context,fd)
        value=pinned_json(generation)
        if field=='targetPin':
            wrong=deepcopy(e.candidate);wrong['secrets']={}
            value[field]=write(e.claim/'unauthorized-target.json',wrong)
        elif field=='captureBindings': value[field]={}
        elif field=='parentGenerationPin': value[field]=e.case['policy']['baselineTargetPin']
        else: value[field]='wrong'
        changed=write(Path(generation['path']),value)
        with pytest.raises(Exception,match='PROGRAM_'):
            resolve(e,binding,fd,generation_pin=changed)


@pytest.mark.parametrize('stage_name', ['replacement','target'])
def test_admission_keeps_original_reservation_and_records_proven_execution(execution,stage_name):
    e=execution
    with locked(e.case) as fd:
        context,binding=bind(e,fd); _,generation=staged(e,context,fd)
        if stage_name=='target': (e.claim/'runtime').mkdir(mode=0o700)
        effective,_=resolve(e,binding,fd,generation_pin=generation,runtime=stage_name=='target')
        result=admission.admit(effective,e.request,e.root,stage_name,reservation_configuration=e.owner,
            execution_binding_pin=binding,execution_generation_pin=generation,execution_lock_fd=fd)
    assert result['admitted'] is True and e.observations[-1]==effective
    reservation=pinned_json(e.reservation)
    assert reservation['configurationSha256']==digest(e.owner)!=digest(effective)
    record=pinned_json(write(e.case['root']/'record-copy.json',__import__('json').loads(
        (e.root/('resource-admission-'+stage_name+'.json')).read_bytes())))
    assert record['reservationPin']==e.reservation
    assert record['reservationConfigurationSha256']==digest(e.owner)
    assert record['programExecution']['bindingPin']==binding


@pytest.mark.parametrize('field', ['unrelated','other-target','dataRoot','budget','credentials'])
def test_admission_compares_complete_derived_configuration(execution,field):
    e=execution
    with locked(e.case) as fd:
        context,binding=bind(e,fd); _,generation=staged(e,context,fd)
        effective,_=resolve(e,binding,fd,generation_pin=generation)
        if field=='unrelated': effective['unrelated']={}
        elif field=='other-target': effective['targets']['other']={}
        else:
            target=effective['targets']['target57']
            if field=='dataRoot': target['dataRoot']=str(e.claim)
            elif field=='budget': target['resourceBudget']['mysqlMemoryBytes']=2
            else: target['secrets']={}
        count=len(e.observations)
        with pytest.raises(admission.ResourceAdmissionError,match='RESTORE_REPLACEMENT_CONFIGURATION_CHANGED'):
            admission.admit(effective,e.request,e.root,'replacement',reservation_configuration=e.owner,
                execution_binding_pin=binding,execution_generation_pin=generation,execution_lock_fd=fd)
        assert len(e.observations)==count


def test_default_admission_does_not_accept_program_changes_without_binding(execution):
    e=execution
    effective=deepcopy(e.owner);effective['targets']['target57']=deepcopy(e.candidate)
    (e.claim/'runtime').mkdir(mode=0o700)
    effective['targets']['target57']['dataRoot']=str(e.claim/'runtime')
    with pytest.raises(admission.ResourceAdmissionError,match='RESTORE_REPLACEMENT_CONFIGURATION_CHANGED'):
        admission.admit(effective,e.request,e.root,'target',reservation_configuration=e.owner)


@pytest.mark.parametrize('missing', ['owner','binding','lock'])
def test_partial_execution_arguments_cannot_bypass_legacy_checks(execution,missing):
    e=execution
    with locked(e.case) as fd:
        _,binding=bind(e,fd)
        args=dict(reservation_configuration=e.owner,execution_binding_pin=binding,execution_lock_fd=fd)
        args.pop({'owner':'reservation_configuration','binding':'execution_binding_pin','lock':'execution_lock_fd'}[missing])
        with pytest.raises(admission.ResourceAdmissionError,match='RESTORE_PROGRAM_EXECUTION_BINDING_REQUIRED'):
            admission.admit(e.owner,e.request,e.root,'replacement',**args)
