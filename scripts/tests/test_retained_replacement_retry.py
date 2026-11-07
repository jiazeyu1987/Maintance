"""Append-only recovery clearances; no remote or business operations."""
import copy
import json
import os
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import pin,write,digest
from recovery_retained_retry import validate_clearance,bind_clearances


@pytest.fixture
def retained(tmp_path):
    state=tmp_path/'state';state.mkdir();claim=state/'failed-1';claim.mkdir()
    root=tmp_path/'failed-1';root.mkdir()
    request=dict(operationId='failed-1',action='RESTORE',sourceConfigRef='source',
                 recoveryPointRef='point',targetConfigRef='target')
    target=dict(database='component_test',services=[{'role':'mysql'},{'role':'minio'}],
        redisRebuild={'database':0},fixture='same-target',replacement=dict(
        schemaVersion='RegisteredApplicationReplacement/v1',stateRoot=str(state),
        lockPath=str(tmp_path/'target.lock'),databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',
        services={'mysql':{},'minio':{}}))
    refs={
      'requestPin':write(root/'request.json',request),
      'resultPin':write(root/'worker-result.json',dict(operationId='failed-1',state='FAILED_RETAINED',actualExitCode=1)),
      'exitPin':write(root/'child-exit.json',dict(actualExitCode=1,timedOut=False)),
      'replacementResultPin':write(claim/'replacement-result.json',dict(operationId='failed-1',targetConfigRef='target',state='FAILED_RETAINED'))}
    clearance=dict(schemaVersion='RetainedReplacementRecovery/v1',operationId='failed-1',
        sourceConfigRef='source',recoveryPointRef='point',targetConfigRef='target',
        targetConfigurationSha256=digest(target),authorization='User requested actual restore',
        issuedAt='2026-01-01T00:00:00Z',expiresAt='2099-01-01T00:00:00Z',**refs)
    clearance_pin=write(claim/'recovery-clearance.json',clearance)
    release=write(root/'resource-recovery-release.json',dict(clearancePin=clearance_pin,
        reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
    write(claim/'recovery-ready.json',dict(clearancePin=clearance_pin,releasePin=release))
    return target,claim,request,clearance


def test_no_clearance_does_not_enable_failed_claim(tmp_path):
    claim=tmp_path/'claim';claim.mkdir()
    assert validate_clearance({},claim) is None


def test_clearance_keeps_original_failed_receipt_and_pins(retained):
    target,claim,request,value=retained
    before=(claim/'replacement-result.json').read_bytes()
    assert validate_clearance(target,claim)['operationId']=='failed-1'
    assert (claim/'replacement-result.json').read_bytes()==before
    assert json.loads(before)['state']=='FAILED_RETAINED'


@pytest.mark.parametrize('field,value',[('sourceConfigRef','different'),('recoveryPointRef','old-point'),('targetConfigRef','other')])
def test_clearance_rejects_different_request_before_consumption(retained,field,value):
    target,claim,request,_=retained
    request=dict(request,operationId='retry-1',**{field:value})
    with pytest.raises(Exception,match='RECOVERY_CLEARANCE_REQUEST_CHANGED'):
        bind_clearances(target,request,consume=False)
    assert not (claim/'recovery-consumption.json').exists()


def test_original_changed_and_unknown_result_are_never_cleared(retained):
    target,claim,_,value=retained
    p=Path(value['resultPin']['path'])
    p.write_text(json.dumps({'state':'TERMINAL_UNKNOWN'}),encoding='utf-8')
    with pytest.raises(Exception):validate_clearance(target,claim)


def test_changed_target_is_rejected(retained):
    target,claim,_,_=retained
    with pytest.raises(Exception,match='RECOVERY_CLEARANCE_TARGET_CHANGED'):
        validate_clearance(dict(target,fixture='different'),claim)


def test_explicit_consumption_is_once_and_keeps_failure(retained):
    target,claim,request,_=retained
    new=claim.parent/'retry-1';new.mkdir()
    request=dict(request,operationId='retry-1')
    bind_clearances(target,request,consume=False)
    assert not (claim/'recovery-consumption.json').exists()
    refs=bind_clearances(target,request,consume=True)
    receipt=json.loads((claim/'recovery-consumption.json').read_bytes())
    assert receipt['replacementOperationId']=='retry-1' and refs
    assert json.loads((claim/'replacement-result.json').read_bytes())['state']=='FAILED_RETAINED'
    assert bind_clearances(target,dict(request,operationId='retry-2',recoveryPointRef='later'),consume=False)==[]
    assert validate_clearance(target,claim)


def test_missing_consuming_claim_is_rejected(retained):
    target,claim,_,_=retained
    write(claim/'recovery-consumption.json',{'replacementOperationId':'missing','clearancePin':pin(claim/'recovery-clearance.json')})
    with pytest.raises(Exception,match='RECOVERY_CLEARANCE_CONSUMER_MISSING'):
        validate_clearance(target,claim)


def test_next_failure_still_blocks_available_and_original_is_preserved(retained):
    from recovery_replace import available
    target,claim,request,_=retained
    before=(claim/'replacement-result.json').read_bytes()
    assert available(target)
    new=claim.parent/'retry-1';new.mkdir()
    bind_clearances(target,dict(request,operationId='retry-1'),consume=True)
    assert not available(target)
    write(new/'replacement-result.json',dict(state='FAILED_RETAINED'))
    assert not available(target)
    assert (claim/'replacement-result.json').read_bytes()==before


def test_clearance_without_ready_release_cannot_enable_target(retained):
    target,claim,_,_=retained
    (claim/'recovery-ready.json').unlink()
    with pytest.raises(Exception):validate_clearance(target,claim)


def test_unknown_even_with_matching_pin_is_rejected(retained):
    target,claim,_,value=retained
    value['resultPin']=write(Path(value['resultPin']['path']),dict(operationId='failed-1',state='TERMINAL_UNKNOWN',actualExitCode=1))
    clearance=write(claim/'recovery-clearance.json',value)
    release=write(claim.parent.parent/'failed-1/resource-recovery-release.json',
        dict(clearancePin=clearance,reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
    write(claim/'recovery-ready.json',dict(clearancePin=clearance,releasePin=release))
    with pytest.raises(Exception,match='RECOVERY_CLEARANCE_ORIGINAL_CHANGED'):
        validate_clearance(target,claim)


@pytest.fixture
def authorization_case(tmp_path,monkeypatch):
    if os.name!='posix':pytest.skip('Actual POSIX flock and host reservation filesystem required')
    import recovery_resource_admission as resource
    import recovery_retained_retry as retry
    host=tmp_path/'host';host.mkdir(mode=0o700)
    machine=tmp_path/'machine';machine.write_text('machine-1',encoding='ascii')
    monkeypatch.setattr(resource,'HOST_ROOT',host);monkeypatch.setattr(resource,'MACHINE_ID',machine)
    state=tmp_path/'state';state.mkdir();claim=state/'failed-1';claim.mkdir()
    operations=tmp_path/'operations';operations.mkdir();root=operations/'failed-1';root.mkdir()
    lock=tmp_path/'source.lock';lock.touch(mode=0o600)
    target=dict(machineId='machine-1',database='component_test',services=[{'role':'mysql'},{'role':'minio'}],
        redisRebuild={'database':0},replacement=dict(schemaVersion='RegisteredApplicationReplacement/v1',
        stateRoot=str(state),lockPath=str(lock),databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',
        services={'mysql':{},'minio':{}}))
    config=dict(operationsRoot=str(operations),targets={'target':target})
    request=dict(operationId='failed-1',action='RESTORE',sourceConfigRef='source',recoveryPointRef='point',targetConfigRef='target')
    write(root/'request.json',request);write(root/'configuration.json',config)
    write(root/'worker-result.json',dict(operationId='failed-1',state='FAILED_RETAINED',actualExitCode=1,data={'mutationDispatched':True}))
    write(root/'child-exit.json',dict(actualExitCode=1,timedOut=False))
    prep=root/'replacement-preparation';prep.mkdir();write(prep/'replacement-intent.json',{'started':True})
    write(claim/'replacement-result.json',dict(operationId='failed-1',targetConfigRef='target',state='FAILED_RETAINED'))
    binding=resource._binding(config,request,root)
    reservation=write(root/'resource-reservation.json',dict(binding,schemaVersion='RestoreHostReservation/v1'))
    write(host/'active.json',dict(binding,reservationPin=reservation))
    monkeypatch.setattr(retry,'observe',lambda *a:{'tableCount':0,'componentObservation':True})
    return retry,resource,config,request,root,claim,host


def test_explicit_authorization_preserves_failure_and_releases_exact_pointer(authorization_case):
    retry,resource,config,request,root,claim,host=authorization_case
    original=(root/'worker-result.json').read_bytes(),(claim/'replacement-result.json').read_bytes()
    result=retry.authorize(config,request,root,'Explicit approved restore of the same point',0)
    assert result['restoreDispatched'] is False and not (host/'active.json').exists()
    assert original==((root/'worker-result.json').read_bytes(),(claim/'replacement-result.json').read_bytes())
    assert retry.validate_clearance(config['targets']['target'],claim)


def test_another_reservation_is_not_released(authorization_case):
    retry,resource,config,request,root,claim,host=authorization_case
    write(host/'active.json',{'operationId':'unrelated'})
    before=(host/'active.json').read_bytes()
    with pytest.raises(Exception,match='RESTORE_RESOURCE_RESERVATION_CHANGED'):
        retry.authorize(config,request,root,'Explicit approved restore of the same point',0)
    assert (host/'active.json').read_bytes()==before and not (claim/'recovery-clearance.json').exists()


def test_failed_observation_never_releases_pointer(authorization_case,monkeypatch):
    retry,resource,config,request,root,claim,host=authorization_case
    def reject(*a):raise RuntimeError('TARGET_DRIFT')
    monkeypatch.setattr(retry,'observe',reject)
    before=(host/'active.json').read_bytes()
    with pytest.raises(RuntimeError,match='TARGET_DRIFT'):
        retry.authorize(config,request,root,'Explicit approved restore of the same point',0)
    assert (host/'active.json').read_bytes()==before and not (claim/'recovery-clearance.json').exists()


def test_retained_main_protection_handoff_precedes_clearance_and_keeps_originals(authorization_case,monkeypatch):
    retry,resource,config,request,root,claim,host=authorization_case
    import recovery_main_target as main
    target=config['targets']['target'];target['mainApplication']={'schemaVersion':'RegisteredMainApplication/v2'}
    write(root/'configuration.json',config)
    binding=resource._binding(config,request,root)
    reservation=write(root/'resource-reservation.json',dict(binding,schemaVersion='RestoreHostReservation/v1'))
    write(host/'active.json',dict(binding,reservationPin=reservation))
    original=pin(root/'worker-result.json');called=[]
    def release(*args):
        assert (host/'active.json').exists() and not (claim/'recovery-clearance.json').exists()
        called.append('release')
        return {'mainProtectionRecoveryPin':write(claim/'main-protection-recovery.json',
            dict(schemaVersion='RetainedMainProtectionRecovery/v1',operationId=request['operationId'],
                 targetConfigurationSha256=digest(target),releasePins=[],originalPins=[]))}
    monkeypatch.setattr(main,'release_retained_protections',release,raising=False)
    retry.authorize(config,request,root,'Explicit approved same point MAIN continuation',0)
    assert called==['release'] and pin(root/'worker-result.json')==original
    value=retry.validate_clearance(target,claim)
    assert value['mainProtectionRecoveryPin']==pin(claim/'main-protection-recovery.json')


def test_failed_protection_handoff_retains_reservation_and_blocks_clearance(authorization_case,monkeypatch):
    retry,resource,config,request,root,claim,host=authorization_case
    import recovery_main_target as main
    def reject(*args):raise ValueError('PROTECTION_DRIFT')
    monkeypatch.setattr(main,'release_retained_protections',reject,raising=False)
    before=pin(host/'active.json')
    with pytest.raises(ValueError,match='PROTECTION_DRIFT'):
        retry.authorize(config,request,root,'Explicit approved same point continuation',0)
    assert pin(host/'active.json')==before and not (claim/'recovery-clearance.json').exists()


@pytest.fixture
def before_mutation_case(authorization_case):
    retry,resource,config,request,root,claim,host=authorization_case
    (root/'replacement-preparation/replacement-intent.json').unlink()
    result=write(root/'worker-result.json',dict(operationId=request['operationId'],state='FAILED_RETAINED',
        actualExitCode=1,data={'mutationDispatched':False},originalResultPins=[]))
    resource.release_no_mutation(config,request,root,result,pin(root/'child-exit.json'))
    return authorization_case


def test_explicit_before_mutation_clearance_preserves_originals_and_binds_one_point(before_mutation_case):
    retry,resource,config,request,root,claim,host=before_mutation_case
    originals={p:p.read_bytes() for p in (*root.rglob('*.json'),claim/'replacement-result.json')}
    result=retry.authorize(config,request,root,'Explicit same point restore with no target writes',885,no_mutation=True)
    assert result['restoreDispatched'] is False and not (host/'active.json').exists()
    assert all(p.read_bytes()==b for p,b in originals.items())
    clearance=retry.validate_clearance(config['targets']['target'],claim)
    assert clearance['schemaVersion']=='RetainedReplacementRecovery/v2'
    assert clearance['failurePhase']=='BEFORE_MUTATION'
    assert clearance['noMutationReleasePin']==pin(root/'resource-no-mutation-release.json')
    with pytest.raises(Exception,match='RECOVERY_CLEARANCE_REQUEST_CHANGED'):
        retry.bind_clearances(config['targets']['target'],dict(request,operationId='next',recoveryPointRef='other'),consume=False)
    (claim.parent/'next').mkdir()
    retry.bind_clearances(config['targets']['target'],dict(request,operationId='next'),consume=True)
    assert json.loads((claim/'recovery-consumption.json').read_bytes())['replacementOperationId']=='next'


@pytest.mark.parametrize('problem',['missing-release','other-reservation','intent','importer','native-mutation','result-mutation','unknown','exit-unknown','reservation-drift','release-drift'])
def test_before_mutation_clearance_rejects_incomplete_or_unsafe_evidence(before_mutation_case,problem):
    retry,resource,config,request,root,claim,host=before_mutation_case
    if problem=='missing-release':(root/'resource-no-mutation-release.json').unlink()
    elif problem=='other-reservation':write(host/'active.json',{'operationId':'other'})
    elif problem=='intent':write(root/'replacement-preparation/replacement-intent.json',{'started':True})
    elif problem=='importer':write(root/'importer-database.json',{'started':True})
    elif problem=='native-mutation':write(root/'native-sql.json',{'mutation':True,'actualExitCode':0,'finishedAt':'now'})
    elif problem in ('result-mutation','unknown'):
        p=root/'worker-result.json';v=json.loads(p.read_bytes())
        if problem=='result-mutation':v['data']['mutationDispatched']=True
        else:v['state']='TERMINAL_UNKNOWN'
        write(p,v)
    elif problem=='exit-unknown':write(root/'child-exit.json',{'actualExitCode':1,'timedOut':True})
    elif problem=='reservation-drift':write(root/'resource-reservation.json',{'operationId':'other'})
    elif problem=='release-drift':write(root/'resource-no-mutation-release.json',{'reason':'PROVEN_NO_MUTATION'})
    pointer=(host/'active.json').read_bytes() if (host/'active.json').exists() else None
    with pytest.raises(Exception):
        retry.authorize(config,request,root,'Explicit same point restore with no target writes',885,no_mutation=True)
    assert not (claim/'recovery-clearance.json').exists()
    assert ((host/'active.json').read_bytes() if (host/'active.json').exists() else None)==pointer


def test_before_mutation_mode_cannot_clear_written_failure(authorization_case):
    retry,resource,config,request,root,claim,host=authorization_case
    pointer=(host/'active.json').read_bytes()
    with pytest.raises(Exception):retry.authorize(config,request,root,'Explicit before mutation mode',885,no_mutation=True)
    assert (host/'active.json').read_bytes()==pointer


def test_before_mutation_clearance_stays_bound_to_release_pin(before_mutation_case):
    retry,resource,config,request,root,claim,host=before_mutation_case
    retry.authorize(config,request,root,'Explicit same point restore with no target writes',885,no_mutation=True)
    write(root/'resource-no-mutation-release.json',{'reason':'tampered'})
    with pytest.raises(Exception):retry.validate_clearance(config['targets']['target'],claim)


def test_before_mutation_clearance_rejects_actual_live_original_process(before_mutation_case):
    import subprocess
    retry,resource,config,request,root,claim,host=before_mutation_case
    worker=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)',
                             'recovery_minimal_worker.py',request['operationId']])
    try:
        with pytest.raises(Exception,match='RECOVERY_ORIGINAL_PROCESS_RUNNING'):
            retry.authorize(config,request,root,'Explicit same point restore with no target writes',885,no_mutation=True)
        assert not (claim/'recovery-clearance.json').exists()
    finally:worker.terminate();worker.wait(timeout=5)


def test_before_mutation_failed_current_observation_creates_no_clearance(before_mutation_case,monkeypatch):
    retry,resource,config,request,root,claim,host=before_mutation_case
    def reject(*args):
        assert args[-1] is True
        raise RuntimeError('CURRENT_TARGET_TABLE_OR_IDENTITY_DRIFT')
    monkeypatch.setattr(retry,'observe',reject)
    with pytest.raises(RuntimeError,match='CURRENT_TARGET_TABLE_OR_IDENTITY_DRIFT'):
        retry.authorize(config,request,root,'Explicit same point restore with no target writes',885,no_mutation=True)
    assert not (claim/'recovery-clearance.json').exists() and not (host/'active.json').exists()


@pytest.fixture
def inherited_quiescence(before_mutation_case, monkeypatch):
    retry,resource,config,request,root,claim,host=before_mutation_case
    target=config['targets']['target']
    prior=claim.parent/'prior';prior.mkdir();oldroot=root.parent/'prior';oldroot.mkdir()
    observed=dict(schemaVersion='RetainedReplacementObservation/v1',targetConfigRef='target',
        databaseUuid=target['replacement']['databaseUuid'],tableCount=885,observedAt='old',
        services={'mysql':dict(id='mysql',image='image-mysql',running=True,startedAt='stable'),
                  'minio':dict(id='minio',image='image-minio',running=False,startedAt='stable')})
    refs=dict(requestPin=write(oldroot/'request.json',dict(request,operationId='prior')),
        resultPin=write(oldroot/'worker-result.json',dict(operationId='prior',state='FAILED_RETAINED',actualExitCode=1)),
        exitPin=write(oldroot/'child-exit.json',dict(actualExitCode=1,timedOut=False)),
        replacementResultPin=write(prior/'replacement-result.json',dict(operationId='prior',targetConfigRef='target',state='FAILED_RETAINED')))
    value=dict(schemaVersion='RetainedReplacementRecovery/v1',operationId='prior',sourceConfigRef='source',
        targetConfigRef='target',recoveryPointRef='point',targetConfigurationSha256=digest(target),
        authorization='Explicit same point continuation',expiresAt='2099-01-01T00:00:00Z',
        observationPin=write(prior/'recovery-observation.json',observed),**refs)
    ref=write(prior/'recovery-clearance.json',value)
    release=write(oldroot/'resource-recovery-release.json',dict(clearancePin=ref,reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
    write(prior/'recovery-ready.json',dict(clearancePin=ref,releasePin=release))
    write(prior/'recovery-consumption.json',dict(schemaVersion='RetainedReplacementConsumption/v1',
        clearancePin=ref,replacementOperationId=request['operationId']))
    calls=[]
    def current(*args):
        calls.append(args[-1])
        assert args[-1] is False, 'INHERITED_TARGET_MUST_STAY_QUIESCED'
        return dict(observed,observedAt='current')
    monkeypatch.setattr(retry,'observe',current)
    return before_mutation_case,prior,observed,calls


def test_no_mutation_after_consumed_clearance_keeps_original_quiescence(inherited_quiescence):
    case,prior,observed,calls=inherited_quiescence
    retry,resource,config,request,root,claim,host=case
    original={p:p.read_bytes() for p in prior.iterdir()}
    retry.authorize(config,request,root,'Explicit same point continuation from retained quiescence',885,no_mutation=True)
    value=retry.validate_clearance(config['targets']['target'],claim)
    assert calls==[False] and value['inheritedQuiescencePin']==pin(prior/'recovery-clearance.json')
    assert all(p.read_bytes()==raw for p,raw in original.items()) and not (host/'active.json').exists()


@pytest.mark.parametrize('field', ['services','databaseUuid','tableCount'])
def test_inherited_quiescence_drift_never_creates_clearance(inherited_quiescence,monkeypatch,field):
    case,prior,observed,calls=inherited_quiescence
    retry,resource,config,request,root,claim,host=case
    value=copy.deepcopy(observed)
    if field=='services':value['services']['minio']['startedAt']='changed'
    elif field=='databaseUuid':value[field]='different'
    else:value[field]=884
    monkeypatch.setattr(retry,'observe',lambda *a:value)
    with pytest.raises(Exception,match='RECOVERY_INHERITED_QUIESCENCE_CHANGED'):
        retry.authorize(config,request,root,'Explicit same point continuation from retained quiescence',885,no_mutation=True)
    assert not (claim/'recovery-clearance.json').exists()


def test_inherited_quiescence_clearance_remains_bound_to_consumption(inherited_quiescence):
    case,prior,observed,calls=inherited_quiescence
    retry,resource,config,request,root,claim,host=case
    retry.authorize(config,request,root,'Explicit same point continuation from retained quiescence',885,no_mutation=True)
    used=json.loads((prior/'recovery-consumption.json').read_bytes());used['replacementOperationId']='unrelated'
    write(prior/'recovery-consumption.json',used)
    with pytest.raises(Exception,match='RECOVERY_INHERITED_QUIESCENCE_CHANGED'):
        retry.validate_clearance(config['targets']['target'],claim)
