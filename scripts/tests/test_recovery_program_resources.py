"""Program capacity contracts; protocol observations are not server measurements.

Pure checks cover device aggregation. Integration uses real private original
metadata, the durable reservation, epoch and physical flock. Docker/MySQL
capacity replies are explicit unit boundaries; no image or data is restored.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_recovery_program_generation import case, switched, write
from test_recovery_program_execution import bind
from test_recovery_program_activation import locked, start, stage
from recovery_engine import Budget, RecoveryError, digest, pin, pinned_json
from recovery_program_native import MainNativeExecutionContext
import recovery_resource_admission as admission


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux reservation and flock')


def module():
    import recovery_program_resources
    return recovery_program_resources


@pytest.fixture
def budget_case():
    data = dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=2,
        hostAvailableMemoryBytes=3, diskBytesByPath={'/data': 400, '/sql': 600})
    observed = dict(mysqlMemoryLimitBytes=2, hostAvailableMemoryBytes=3,
        disks=[dict(path='/data', device=1, freeBytes=10000), dict(path='/sql', device=1, freeBytes=10000)])
    program = dict(schemaVersion='MainProgramResourceBudget/v1', targetConfigRef='target57',
        projectionBytes=200, dockerImportBytes=300, minimumFreeBytes=100)
    source = dict(schemaVersion='MainProgramSourceArchive/v1', maxImportBytes=200,
        archivePin=dict(path='/archive/original-application-images.tar', bytes=250, sha256='a'*64))
    extra = [dict(role='projection', path='/claim', device=1, freeBytes=10000),
             dict(role='docker', path='/docker', device=1, freeBytes=10000)]
    return data, observed, program, source, extra


def check(case):
    return module().check_program_budget(*case)


def test_data_projection_and_image_store_add_on_the_same_device(budget_case):
    before = deepcopy(budget_case)
    result = check(budget_case)
    assert result['admitted'] is True and result['businessAcceptance'] == 'NOT_PERFORMED'
    assert result['diskRequirements'] == [dict(device=1, requiredBytes=1600, availableBytes=10000)]
    assert budget_case == before


def test_separate_paths_do_not_reuse_the_same_free_bytes(budget_case):
    for row in budget_case[1]['disks'] + budget_case[4]: row['freeBytes'] = 1500
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_PROGRAM_DISK_SPACE_INSUFFICIENT'):
        check(budget_case)


def test_each_distinct_device_keeps_its_own_headroom(budget_case):
    budget_case[4][0]['device'] = 2
    budget_case[4][1]['device'] = 3
    result = check(budget_case)
    assert result['diskRequirements'] == [dict(device=1, requiredBytes=1100, availableBytes=10000),
        dict(device=2, requiredBytes=300, availableBytes=10000),
        dict(device=3, requiredBytes=400, availableBytes=10000)]


def test_free_bytes_are_the_minimum_observation_for_each_device(budget_case):
    budget_case[4][1]['freeBytes'] = 1599
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_PROGRAM_DISK_SPACE_INSUFFICIENT'):
        check(budget_case)


@pytest.mark.parametrize('field', ['projectionBytes', 'dockerImportBytes', 'minimumFreeBytes'])
@pytest.mark.parametrize('value', [0, -1, True, '300', 2**63])
def test_program_budget_has_explicit_bounded_integer_capacities(budget_case, field, value):
    budget_case[2][field] = value
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_PROGRAM_RESOURCE_BUDGET_INVALID'):
        check(budget_case)


@pytest.mark.parametrize('field', ['projectionBytes', 'dockerImportBytes'])
def test_capacity_cannot_be_smaller_than_the_declared_program_input(budget_case, field):
    budget_case[2][field] = 1
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_PROGRAM_RESOURCE_BUDGET_INCOMPLETE'):
        check(budget_case)


@pytest.mark.parametrize('change', ['role', 'duplicate', 'missing', 'negative', 'path'])
def test_extra_disk_observations_must_be_complete(budget_case, change):
    if change == 'role': budget_case[4][0]['role'] = 'unknown'
    elif change == 'duplicate': budget_case[4].append(dict(budget_case[4][0]))
    elif change == 'missing': budget_case[4].pop()
    elif change == 'negative': budget_case[4][0]['freeBytes'] = -1
    else: budget_case[4][0]['path'] = 'relative'
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_PROGRAM_RESOURCE_OBSERVATION_INVALID'):
        check(budget_case)


def test_program_admission_preserves_the_original_memory_rejection(budget_case):
    budget_case[1]['mysqlMemoryLimitBytes'] = 1
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_MYSQL_MEMORY_INSUFFICIENT'):
        check(budget_case)


@pytest.fixture
def resource_execution(case, monkeypatch):
    base = case['root']; target = case['target']
    target.update(machineId='resource-unit-machine', dockerEngineId='resource-unit-engine',
        dataRoot=str(base), resourceBudget=dict(schemaVersion='RestoreResourceBudget/v1',
            mysqlMemoryBytes=1, hostAvailableMemoryBytes=1, diskBytesByPath={str(base):1}))
    candidate, capture, switch = switched(case, base)
    operations = base/'operations'; operations.mkdir(mode=0o700)
    root = operations/'restore-1'; root.mkdir(mode=0o700)
    host = base/'resource-host'; host.mkdir(mode=0o700)
    machine = base/'machine-id'; machine.write_text(target['machineId'], encoding='ascii')
    monkeypatch.setattr(admission, 'HOST_ROOT', host)
    monkeypatch.setattr(admission, 'MACHINE_ID', machine)
    def observe(*_):
        disk = base.stat().st_dev
        return dict(mysqlMemoryLimitBytes=10, hostAvailableMemoryBytes=10,
            disks=[dict(path=str(base), device=disk, freeBytes=2**40)])
    monkeypatch.setattr(admission, 'observe_resources', observe)
    source_policy = dict(schemaVersion='MainProgramSourceArchivePolicy/v1', sourceConfigRef='source57',
        roleVersionBindings=[dict(role=role, versionPath=['images',role])
            for role in ('mysql','redis','minio','backend','frontend')],
        architecture='amd64', maxArchiveBytes=1024, maxImportBytes=1024)
    budget = dict(schemaVersion='MainProgramResourceBudget/v1', targetConfigRef='target57',
        projectionBytes=2048, dockerImportBytes=4096, minimumFreeBytes=1024)
    owner = dict(operationsRoot=str(operations), targets={'target57':deepcopy(target)},
        sources={'source57':{}}, targetProgramPolicies={'target57':deepcopy(case['policy'])},
        targetBackupEpochPolicies={'target57':deepcopy(case['epoch'])},
        sourceProgramArchivePolicies={'source57':source_policy}, targetProgramResourceBudgets={'target57':budget})
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-1', action='RESTORE',
        sourceConfigRef='source57', parentChainRef=None, recoveryPointRef='point1', targetConfigRef='target57')
    owner_pin=write(root/'configuration.json',owner);request_pin=write(root/'request.json',request)
    reservation=admission.reserve(owner,request,root)
    claim=Path(target['replacement']['stateRoot'])/request['operationId'];claim.mkdir(mode=0o700)
    image=base/'program-input.tar';image.write_bytes(b'unit capacity input metadata, not an image archive')
    source=dict(schemaVersion='MainProgramSourceArchive/v1', sourceConfigRef='source57',
        policySha256=digest(source_policy), archivePin=pin(image), architecture='amd64',
        maxArchiveBytes=1024,maxImportBytes=1024)
    docker=base/'docker-store';docker.mkdir(mode=0o700)
    return SimpleNamespace(case=case,owner=owner,request=request,root=root,claim=claim,owner_pin=owner_pin,
        request_pin=request_pin,reservation=reservation,candidate=candidate,capture=capture,switch=switch,
        source_program=source,docker=docker,command_observations=[])


def resource_native(e, ctx):
    configuration=deepcopy(e.owner);view=ctx.preparation(configuration)
    def docker(args):
        e.command_observations.append(list(args))
        assert args==['info','--format','{{json .}}']
        return json.dumps(dict(ID='resource-unit-engine',DockerRootDir=str(e.docker))).encode()
    return SimpleNamespace(native_context=view, original=deepcopy(e.request),
        config=deepcopy(configuration['targets']['target57']), budget=ctx.budget,docker=docker)


def admit(e, native, binding, fd, **changes):
    arguments=dict(reservation_configuration=e.owner,execution_binding_pin=binding,execution_lock_fd=fd)
    arguments.update(changes)
    return module().admit_program_resources(native,e.source_program,e.claim,**arguments)


def test_actual_reservation_context_and_devices_produce_pinned_admission(resource_execution):
    e=resource_execution
    before={p['path']:Path(p['path']).read_bytes() for p in (e.owner_pin,e.request_pin,e.reservation)}
    with locked(e.case) as fd:
        _,binding=bind(e,fd);start(e.case,e.claim,fd)
        with MainNativeExecutionContext(e.owner,e.request,e.root,binding_pin=binding,lock_fd=fd,budget=Budget(120000)) as ctx:
            native=resource_native(e,ctx)
            result=admit(e,native,binding,fd)
            assert result['admitted'] is True
            record=pinned_json(pin(e.root/'resource-admission-program.json'))
            assert record['admitted'] is True and record['programExecution']['bindingPin']==binding
            assert record['reservationPin']==e.reservation and record['sourceProgramPolicySha256']==e.source_program['policySha256']
            assert record['diskRequirements'][0]['requiredBytes']==1+2048+4096+1024
    assert all(Path(name).read_bytes()==raw for name,raw in before.items())
    assert e.command_observations==[['info','--format','{{json .}}']]


def test_rejected_data_memory_keeps_original_budget_and_observation(resource_execution, monkeypatch):
    e=resource_execution
    with locked(e.case) as fd:
        _,binding=bind(e,fd);start(e.case,e.claim,fd)
        with MainNativeExecutionContext(e.owner,e.request,e.root,binding_pin=binding,lock_fd=fd,budget=Budget(120000)) as ctx:
            observed=dict(mysqlMemoryLimitBytes=10,hostAvailableMemoryBytes=0,
                disks=[dict(path=str(e.case['root']),device=e.case['root'].stat().st_dev,freeBytes=2**40)])
            monkeypatch.setattr(admission,'observe_resources',lambda *_:deepcopy(observed))
            with pytest.raises(admission.ResourceAdmissionError,match='RESTORE_HOST_MEMORY_INSUFFICIENT'):
                admit(e,resource_native(e,ctx),binding,fd)
            record=pinned_json(pin(e.root/'resource-admission-program.json'))
            assert record['admitted'] is False and record['failureCode']=='RESTORE_HOST_MEMORY_INSUFFICIENT'
            assert record['budget']==e.owner['targets']['target57']['resourceBudget']
            assert record['observation']==observed
    assert e.command_observations==[]


@pytest.mark.parametrize('problem', ['native','claim','binding','owner','source','engine','symlink','lost-lock'])
def test_changed_inputs_are_rejected_before_any_write(resource_execution,problem):
    e=resource_execution
    with locked(e.case) as fd:
        _,binding=bind(e,fd);start(e.case,e.claim,fd)
        with MainNativeExecutionContext(e.owner,e.request,e.root,binding_pin=binding,lock_fd=fd,budget=Budget(120000)) as ctx:
            native=resource_native(e,ctx);arguments={}
            if problem=='native':native.config['database']='wrong'
            elif problem=='claim':e.claim=e.claim.parent
            elif problem=='binding':arguments['execution_binding_pin']=e.owner_pin
            elif problem=='owner':arguments['reservation_configuration']=dict(e.owner,other='changed')
            elif problem=='source':e.source_program=dict(e.source_program,policySha256='0'*64)
            elif problem=='engine':native.docker=lambda args:json.dumps(dict(ID='foreign',DockerRootDir=str(e.docker))).encode()
            elif problem=='symlink':
                alias=e.docker.parent/'docker-alias';alias.symlink_to(e.docker,target_is_directory=True)
                native.docker=lambda args:json.dumps(dict(ID='resource-unit-engine',DockerRootDir=str(alias))).encode()
            else:
                import fcntl
                fcntl.flock(fd,fcntl.LOCK_UN)
            error_type=ValueError if problem=='lost-lock' else (RecoveryError,admission.ResourceAdmissionError)
            with pytest.raises(error_type,match='PROGRAM_|BACKUP_EPOCH_'):
                admit(e,native,binding,fd,**arguments)
