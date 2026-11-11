"""Versioned disk forecasts, separate from actual write limits and acceptance.

Finite capacity observations below are unit boundaries. The opt-in tmpfs node
performs a real kernel ENOSPC write in the isolated Linux test container.
"""
from copy import deepcopy
import errno
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
import recovery_resource_admission as admission
from recovery_program_resources import check_program_budget
from recovery_target_capture import MainTargetCapture
from recovery_target_preservation import TargetPreservation
from recovery_engine import RecoveryError
from repository_records import RepositoryError
from test_recovery_resource_budget import resource_host
from test_recovery_target_capture_session import case, restore_case, capture_protocol

GIB = 1024**3


def policy(mode='OBSERVE_ONLY'):
    return dict(schemaVersion='RestoreResourceBudget/v2', diskAdmissionMode=mode,
        mysqlMemoryBytes=2*GIB, hostAvailableMemoryBytes=3*GIB,
        diskBytesByPath={'/operation':64*GIB, '/minio':32*GIB, '/mysql':8*GIB, '/redis':8*GIB})


def observed(value, *, free=122*GIB, device=1):
    return dict(mysqlMemoryLimitBytes=2*GIB, hostAvailableMemoryBytes=4*GIB,
        disks=[dict(path=path, device=device, freeBytes=free) for path in value['diskBytesByPath']])


def configured_policy(value=None):
    selected=policy() if value is None else deepcopy(value)
    original={key:deepcopy(item) for key,item in selected.items() if key!='diskAdmissionMode'}
    original['schemaVersion']='RestoreResourceBudget/v1'
    owner=dict(targets={'target57':dict(resourceBudget=original)},
        targetResourceAdmissionPolicies={'target57':selected})
    return owner,dict(operationId='disk-policy-unit',targetConfigRef='target57')


def test_configured_policy_selects_v2_without_changing_physical_target_or_baseline():
    owner,request=configured_policy();before=deepcopy(owner)
    selected=admission.configured_budget(owner,request)
    assert selected==owner['targetResourceAdmissionPolicies']['target57']
    assert selected['schemaVersion']=='RestoreResourceBudget/v2'
    assert owner==before
    selected['diskBytesByPath']['/mysql']=1
    assert owner==before


def test_absent_operational_policy_retains_exact_legacy_v1():
    owner,request=configured_policy();del owner['targetResourceAdmissionPolicies']
    before=deepcopy(owner)
    selected=admission.configured_budget(owner,request)
    assert selected==owner['targets']['target57']['resourceBudget']
    assert admission.disk_admission_mode(selected)=='RESERVE' and owner==before


@pytest.mark.parametrize('problem', ['null','list','empty','missing_current','unknown_target',
    'mysql_memory','host_memory','disk_maximum','disk_path','v1_override','extra','missing_mode'])
def test_explicit_operational_policy_never_silently_uses_physical_budget(problem):
    owner,request=configured_policy();overrides=owner['targetResourceAdmissionPolicies'];selected=overrides['target57']
    if problem=='null':owner['targetResourceAdmissionPolicies']=None
    elif problem=='list':owner['targetResourceAdmissionPolicies']=[]
    elif problem=='empty':overrides.clear()
    elif problem=='missing_current':
        owner['targets']['target58']=deepcopy(owner['targets']['target57'])
        overrides['target58']=overrides.pop('target57')
    elif problem=='unknown_target':overrides['unregistered']=deepcopy(selected)
    elif problem=='mysql_memory':selected['mysqlMemoryBytes']+=1
    elif problem=='host_memory':selected['hostAvailableMemoryBytes']+=1
    elif problem=='disk_maximum':selected['diskBytesByPath']['/mysql']+=1
    elif problem=='disk_path':selected['diskBytesByPath']['/other']=selected['diskBytesByPath'].pop('/mysql')
    elif problem=='v1_override':selected['schemaVersion']='RestoreResourceBudget/v1';del selected['diskAdmissionMode']
    elif problem=='extra':selected['fallback']=True
    else:del selected['diskAdmissionMode']
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_RESOURCE_ADMISSION_POLICY_INVALID$'):
        admission.configured_budget(owner,request)


def test_inline_v2_does_not_mutate_or_replace_a_registered_physical_budget():
    owner,request=configured_policy();owner['targets']['target57']['resourceBudget']=policy()
    del owner['targetResourceAdmissionPolicies']
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_RESOURCE_BUDGET_INVALID$'):
        admission.configured_budget(owner,request)


def test_owner_admission_uses_explicit_policy_and_preserves_real_target(resource_host):
    from recovery_engine import pin,pinned_json
    owner,request,base,_,_,root=resource_host
    base['diskBytesByPath']={str(root):1024*GIB}
    selected=dict(deepcopy(base),schemaVersion='RestoreResourceBudget/v2',diskAdmissionMode='OBSERVE_ONLY')
    owner['targetResourceAdmissionPolicies']={request['targetConfigRef']:selected};before=deepcopy(owner)
    assert admission.admit(owner,request,root,'owner')['admitted'] is True
    record=pinned_json(pin(root/'resource-admission-owner.json'))
    assert record['budget']==selected and record['forecastReservationsEnforced'] is False
    assert record['diskRequirements'][0]['requiredBytes']>record['diskRequirements'][0]['availableBytes']
    assert owner==before


def test_observe_only_records_forecast_without_reserving_maxima():
    value=policy(); measured=observed(value, free=7*GIB); before=deepcopy((value,measured))
    result=admission.check_budget(value,measured)
    assert result['admitted'] is True and result['businessAcceptance']=='NOT_PERFORMED'
    assert result['diskAdmissionMode']=='OBSERVE_ONLY' and result['forecastReservationsEnforced'] is False
    assert result['diskRequirements']==[dict(device=1,requiredBytes=112*GIB,availableBytes=7*GIB)]
    assert (value,measured)==before


@pytest.mark.parametrize('version', [1,2])
def test_strict_modes_still_reserve_all_same_device_paths(version):
    value=policy('RESERVE')
    if version==1:
        value['schemaVersion']='RestoreResourceBudget/v1';del value['diskAdmissionMode']
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_DISK_SPACE_INSUFFICIENT$'):
        admission.check_budget(value,observed(value,free=111*GIB))


def test_v1_return_shape_stays_exact():
    value=policy('RESERVE');value['schemaVersion']='RestoreResourceBudget/v1';del value['diskAdmissionMode']
    assert admission.check_budget(value,observed(value))==dict(admitted=True,
        businessAcceptance='NOT_PERFORMED',diskRequirements=[dict(device=1,requiredBytes=112*GIB,availableBytes=122*GIB)],
        mysqlMemoryLimitBytes=2*GIB,hostAvailableMemoryBytes=4*GIB)


@pytest.mark.parametrize('change', ['missing','unknown','bool','extra','v1_mode','unknown_version'])
def test_invalid_version_or_mode_never_falls_back(change):
    value=policy()
    if change=='missing':del value['diskAdmissionMode']
    elif change=='unknown':value['diskAdmissionMode']='ignore'
    elif change=='bool':value['diskAdmissionMode']=True
    elif change=='extra':value['other']=True
    elif change=='v1_mode':value['schemaVersion']='RestoreResourceBudget/v1'
    else:value['schemaVersion']='RestoreResourceBudget/v3'
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_RESOURCE_BUDGET_INVALID$'):
        admission.check_budget(value,observed(value))


@pytest.mark.parametrize('field,code', [('mysqlMemoryLimitBytes','RESTORE_MYSQL_MEMORY_INSUFFICIENT'),
    ('hostAvailableMemoryBytes','RESTORE_HOST_MEMORY_INSUFFICIENT')])
def test_observe_only_preserves_memory_rejections(field,code):
    value=policy();measured=observed(value);measured[field]=1
    with pytest.raises(admission.ResourceAdmissionError,match='^'+code+'$'):
        admission.check_budget(value,measured)


def test_observe_only_preserves_complete_disk_observations():
    value=policy();measured=observed(value);measured['disks'].pop()
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_RESOURCE_OBSERVATION_INVALID$'):
        admission.check_budget(value,measured)


def test_shared_capacity_contract_uses_existing_minimum_not_forecast():
    result=admission.enforce_disk_capacity(policy(),178*GIB,122*GIB,'UNIT_CAPACITY',minimum_free_bytes=2*GIB)
    assert result==dict(diskAdmissionMode='OBSERVE_ONLY',forecastReservationsEnforced=False,
        requiredBytes=178*GIB,minimumFreeBytes=2*GIB,availableBytes=122*GIB)
    with pytest.raises(admission.ResourceAdmissionError,match='^UNIT_CAPACITY$') as caught:
        admission.enforce_disk_capacity(policy(),178*GIB,GIB,'UNIT_CAPACITY',minimum_free_bytes=2*GIB)
    assert caught.value.details['availableBytes']==GIB


@pytest.mark.parametrize('required,available,minimum', [(True,10,0),(10,-1,0),(10,10,11),(10,10,True)])
def test_shared_capacity_rejects_invalid_measurements(required,available,minimum):
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_DISK_CAPACITY_ARGUMENT_INVALID$'):
        admission.enforce_disk_capacity(policy(),required,available,'UNIT_CAPACITY',minimum_free_bytes=minimum)


def test_program_import_observes_combined_forecast_and_keeps_minimum():
    value=policy();measured=observed(value,free=3*GIB)
    extra=[dict(role='projection',path='/claim',device=1,freeBytes=3*GIB),
        dict(role='docker',path='/docker',device=1,freeBytes=3*GIB)]
    program=dict(schemaVersion='MainProgramResourceBudget/v1',targetConfigRef='target',
        projectionBytes=8*GIB,dockerImportBytes=4*GIB,minimumFreeBytes=2*GIB)
    source=dict(schemaVersion='MainProgramSourceArchive/v1',maxImportBytes=8*GIB,
        archivePin=dict(path='/archive/image.tar',bytes=4*GIB,sha256='a'*64))
    result=check_program_budget(value,measured,program,source,extra)
    assert result['diskRequirements']==[dict(device=1,requiredBytes=126*GIB,availableBytes=3*GIB)]
    assert result['forecastReservationsEnforced'] is False
    extra[1]['freeBytes']=GIB
    with pytest.raises(admission.ResourceAdmissionError,match='^RESTORE_PROGRAM_DISK_SPACE_INSUFFICIENT$'):
        check_program_budget(value,measured,program,source,extra)


@pytest.fixture
def stage_capacity(tmp_path,monkeypatch):
    value=policy();value['diskBytesByPath']={str(tmp_path):112*GIB}
    owner,request=configured_policy(value)
    measured=observed(value,device=tmp_path.stat().st_dev)
    monkeypatch.setattr(admission,'observe_resources',lambda *_:deepcopy(measured))
    monkeypatch.setattr(admission,'verify_reservation',lambda *_:{'reservation':'unit-protocol'})
    records=[]
    context=SimpleNamespace(_owner=owner,_request=request,_root=tmp_path)
    fake=SimpleNamespace(root=tmp_path,_native=SimpleNamespace(config=owner['targets']['target57']),
        _context=context,_reservation={'reservation':'unit-protocol'},
        budget=SimpleNamespace(maximum=64*GIB,reserve=2*GIB),_record=lambda name,record:records.append(record))
    return fake,records,value,measured


def test_capture_admission_records_178_gib_forecast_but_accepts_122_gib(stage_capacity,monkeypatch):
    fake,records,_,_=stage_capacity
    monkeypatch.setattr('recovery_target_capture.shutil.disk_usage',lambda _:SimpleNamespace(free=122*GIB))
    MainTargetCapture._admit_resources(fake)
    assert records[0]['requiredBytes']==178*GIB and records[0]['freeBytes']==122*GIB
    assert records[0]['diskAdmissionMode']=='OBSERVE_ONLY' and records[0]['forecastReservationsEnforced'] is False


def test_capture_admission_keeps_existing_minimum(stage_capacity,monkeypatch):
    fake,records,_,_=stage_capacity
    monkeypatch.setattr('recovery_target_capture.shutil.disk_usage',lambda _:SimpleNamespace(free=GIB))
    with pytest.raises(RecoveryError,match='^PROGRAM_CAPTURE_DISK_SPACE_INSUFFICIENT$'):
        MainTargetCapture._admit_resources(fake)
    assert records==[]


def preservation(fake,records):
    return SimpleNamespace(native=fake._native,context=fake._context,
        configuration=SimpleNamespace(root=fake.root),root=fake.root,session=fake,
        policy=dict(maxArchiveBytes=64*GIB,maxReadbackRecordBytes=512*1024**2,minimumFreeBytes=2*GIB),
        check=lambda:None,_write=lambda path,record:records.append(record))


def test_preservation_preflight_observes_maxima_and_keeps_minimum(stage_capacity,monkeypatch):
    fake,records,_,_=stage_capacity;current=preservation(fake,records)
    monkeypatch.setattr('recovery_target_preservation.shutil.disk_usage',lambda _:SimpleNamespace(free=122*GIB))
    TargetPreservation._admit_archive_resources(current)
    assert records[0]['diskAdmissionMode']=='OBSERVE_ONLY' and records[0]['forecastReservationsEnforced'] is False
    assert records[0]['devices'][0]['requiredBytes']>178*GIB
    monkeypatch.setattr('recovery_target_preservation.shutil.disk_usage',lambda _:SimpleNamespace(free=GIB))
    with pytest.raises(RepositoryError,match='^PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT$'):
        TargetPreservation._admit_archive_resources(current)


def test_publication_keeps_measured_archive_bytes_and_minimum(stage_capacity,monkeypatch):
    fake,records,_,_=stage_capacity;current=preservation(fake,records)
    monkeypatch.setattr('recovery_target_preservation.shutil.disk_usage',lambda _:SimpleNamespace(free=5*GIB))
    TargetPreservation._admit_publication_resources(current,3*GIB)
    monkeypatch.setattr('recovery_target_preservation.shutil.disk_usage',lambda _:SimpleNamespace(free=5*GIB-1))
    with pytest.raises(RepositoryError,match='^PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT$'):
        TargetPreservation._admit_publication_resources(current,3*GIB)


@pytest.fixture
def program_v2_execution(case,monkeypatch):
    import test_recovery_program_resources as fixtures
    write=fixtures.write
    def register(path,value):
        if Path(path).name=='configuration.json':
            original=value['targets']['target57']['resourceBudget']
            value['targetResourceAdmissionPolicies']={'target57':dict(deepcopy(original),
                schemaVersion='RestoreResourceBudget/v2',diskAdmissionMode='OBSERVE_ONLY')}
        return write(path,value)
    with monkeypatch.context() as setup:
        setup.setattr(fixtures,'write',register)
        return fixtures.resource_execution.__wrapped__(case,monkeypatch)


@pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual Linux reservation and flock required')
def test_program_native_admission_uses_owner_policy_without_rebinding_target(program_v2_execution):
    from test_recovery_program_resources import locked,bind,start,MainNativeExecutionContext,Budget,resource_native,admit
    from recovery_engine import pin,pinned_json
    e=program_v2_execution;original=deepcopy(e.owner['targets'])
    with locked(e.case) as fd:
        _,binding=bind(e,fd);start(e.case,e.claim,fd)
        with MainNativeExecutionContext(e.owner,e.request,e.root,binding_pin=binding,lock_fd=fd,budget=Budget(120000)) as ctx:
            result=admit(e,resource_native(e,ctx),binding,fd)
            assert result['admitted'] is True and result['forecastReservationsEnforced'] is False
            record=pinned_json(pin(e.root/'resource-admission-program.json'))
            assert record['budget']==e.owner['targetResourceAdmissionPolicies']['target57']
            assert record['reservationPin']==e.reservation
    assert e.owner['targets']==original


def test_observe_only_actual_enospc_propagates_from_capture_budget():
    """Explicit opt-in real 1 MiB tmpfs, never a business filesystem."""
    configured=os.environ.get('SPUG_DISK_POLICY_ENOSPC_ROOT')
    if configured is None:
        pytest.skip('explicit isolated tiny tmpfs root required')
    assert sys.platform.startswith('linux') and configured=='/disk-policy-enospc'
    from minimal_capture_support import Budget
    target=Path(configured);assert target.is_dir() and os.statvfs(target).f_blocks*os.statvfs(target).f_frsize<=1024**2
    budget=Budget(target,dict(workSeconds=30,maxWrittenBytes=16*1024**2,minimumFreeBytes=1))
    with pytest.raises(OSError) as caught:
        with budget.open(target/'payload.bin','unit-enospc') as stream:
            stream.write(b'x'*(8*1024**2));stream.flush()
    assert caught.value.errno==errno.ENOSPC


@pytest.fixture
def v2_publication_case(request,monkeypatch,capsys):
    # Construct a fresh registered owner/reservation through the established
    # SAFE fixture, before binding a native context. No success is injected.
    from test_recovery_target_preservation import publication_case
    h=request.getfixturevalue('capture_protocol')
    target=h.owner['targets']['target57']
    target['resourceBudget']['diskBytesByPath']={path:1024*GIB for path in target['resourceBudget']['diskBytesByPath']}
    h.owner['targetResourceAdmissionPolicies']={'target57':dict(deepcopy(target['resourceBudget']),
        schemaVersion='RestoreResourceBudget/v2',diskAdmissionMode='OBSERVE_ONLY')}
    return publication_case.__wrapped__(h,monkeypatch,capsys,request)


@pytest.mark.skipif(not sys.platform.startswith('linux'),reason='real Linux flock and capture processes required')
def test_full_v2_preservation_archives_and_reads_back_under_original_custody(v2_publication_case):
    from test_recovery_target_capture_session import claim,locked,started,context,construct,quiesce,frozen_journals
    from recovery_engine import Budget,pin,pinned_json
    from recovery_target_preservation import validate_archive,preservation_holds
    h=v2_publication_case;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=TargetPreservation.prepare(native,policy_pin=h.preservation_policy,reservation_pin=h.reservation)
            before_capture=pinned_json(pin(publication.session._journal/'resource-admission.json'))
            assert before_capture['requiredBytes']>before_capture['freeBytes']
            assert before_capture['diskAdmissionMode']=='OBSERVE_ONLY' and before_capture['forecastReservationsEnforced'] is False
            quiesce(h,native);originals=frozen_journals(h)
            proof_pin=publication.capture_and_publish();proof=pinned_json(proof_pin)
            assert validate_archive(native,proof_pin).archive_pin==proof_pin
            assert proof['state']=='ARCHIVED_VERIFIED' and proof['payloadContentVerified'] is True
            assert proof['serverDurabilityVerified'] is proof['independentFailureDomain'] is False
            point=pinned_json(proof['pointPin']);assert point['pointType']=='FULL' and point['parentPointPins']==[]
            assert preservation_holds(publication.configuration,guard=publication.check)=={proof['pointPin']['path']}
            measured=pinned_json(pin(publication.root/'publication-resource-admission.json'))
            assert measured['actualArchiveBytes']>0 and measured['minimumFreeBytes']>=measured['actualArchiveBytes']
            assert measured['availableBytes']>=measured['minimumFreeBytes']
            assert measured['forecastReservationsEnforced'] is False
            assert all(path.read_bytes()==raw for path,raw in originals.items())
            assert h.transport.scheduler=='OFF' and not h.transport.releases
            publication.close()
