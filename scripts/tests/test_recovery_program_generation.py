"""Real immutable files and epoch journal; no success mocked into the resolver."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import digest, write as engine_write
from test_backup_epoch import policy as epoch_policy, fixture_event


def write(path, value):
    reference = engine_write(path, value)
    return dict(reference, path=Path(reference['path']).as_posix())


def module():
    import recovery_program_generation
    return recovery_program_generation


@pytest.fixture
def case(tmp_path):
    epoch = epoch_policy(tmp_path)
    initial = fixture_event(epoch)
    services = [dict(role=role, id=char*64, imageId='sha256:'+str(i+1)*64, ip='172.20.0.'+str(i+2))
        for i,(role,char) in enumerate(zip(('mysql','minio','redis','backend','frontend'),'abcde'))]
    target = dict(targetId='main57', sourceConfigRef='source57', database='app', dataPaths=['/data'],
        services=services, secrets={'mysql':{'reference':'unchanged'}},
        replacement=dict(stateRoot=str(tmp_path/'replacements'),lockPath=epoch['sourceLockPath'],
            databaseUuid=epoch['databaseUuid'],services={s['role']:dict(id=s['id'],imageId=s['imageId'],
                labels={},mounts=[]) for s in services},storage={'same':'storage'}),
        mainApplication=dict(serviceConfigurationDigests={s['role']:'f'*64 for s in services},
            networkAttachments={s['role']:{'network':{'networkId':'9'*64,'ipAddress':s['ip'],
                'globalIPv6Address':'','aliases':[s['role'],s['id'][:12]],'links':[],'driverOpts':{}}} for s in services},
            networks=[dict(id='9'*64,name='network',memberContainerIds=sorted(s['id'] for s in services))],
            archiveImageBindings=[dict(role=s['role'],versionPath=['images',s['role']],imageId=s['imageId']) for s in services],
            writerAdmission=dict(approvedWriterContainerIds=['d'*64],exclusiveResources={'database':True},
                evidencePin=write(tmp_path/'writer.json',dict(writerContainerIds=['d'*64],database='app')))))
    Path(target['replacement']['stateRoot']).mkdir(mode=0o700)
    capture = dict(schemaVersion='minimal-source-capture-config/v1',sourceConfigRef='source57',
        sourceLockPath=epoch['sourceLockPath'],archiveRoot='/archives',parent=None,
        source=dict(sourceIdentity=epoch['sourceIdentity'],sourceFingerprint=epoch['sourceIdentity'],
            databaseUuid=epoch['databaseUuid'],database='app',mysqlContainerId='a'*64,minioContainerId='b'*64,
            writerContainerIds=['d'*64,'e'*64],applicationImageIds=[s['imageId'] for s in services],
            configurationPins=[],materialPins=[],objectSourcePin=write(tmp_path/'objects.json',dict(
                sourceIdentity=epoch['sourceIdentity'],versionPins=[write(tmp_path/'versions.json',
                    dict(images={s['role']:s['imageId'] for s in services}))]))))
    base_pin = write(tmp_path/'capture.json',capture)
    policy = dict(schemaVersion='RegisteredMainProgramPolicy/v1',targetConfigRef='target57',
        baselineTargetPin=write(tmp_path/'target.json',target),initialEpochPin=initial[1],
        backupEpochPolicy=epoch,captureConfigurationPins={'source57':base_pin})
    return dict(root=tmp_path,epoch=epoch,event=initial,policy=policy,capture=capture,base_pin=base_pin,
                target=target,parent=None)


def complete(case, operation='restore-1', *, target=None, capture=None, generation_changes=None, receipt_changes=None):
    root = Path(case['target']['replacement']['stateRoot'])/operation
    root.mkdir(mode=0o700)
    intent = write(root/'intent.json',dict(schemaVersion='ReplacementBackupEpochIntent/v1',
        operationId=operation,targetConfigRef='target57',databaseUuid=case['epoch']['databaseUuid'],
        replacementReceiptPath=(root/'replacement-result.json').as_posix()))
    started = fixture_event(case['epoch'],case['event'],kind='RESTORE_STARTED',state='REPLACING',operation=operation,evidence=intent)
    generation = dict(schemaVersion='MainProgramGeneration/v1',operationId=operation,epochId=started[0]['epochId'],
        policySha256=digest(case['policy']),targetConfigRef='target57',baselineTargetPin=case['policy']['baselineTargetPin'],
        parentGenerationPin=case['parent'],targetPin=write(root/'target.json',target or case['target']),
        captureBindings={'source57':dict(baseCapturePin=case['base_pin'],
            capturePin=write(root/'capture.json',capture or case['capture']))},switchResultPin=None)
    generation.update(generation_changes or {})
    generation_pin = write(root/'generation.json',generation)
    receipt = dict(state='SUCCEEDED',operationId=operation,targetConfigRef='target57',
        databaseUuid=case['epoch']['databaseUuid'],programGenerationPin=generation_pin)
    receipt.update(receipt_changes or {})
    reference = write(root/'replacement-result.json',receipt)
    finished = fixture_event(case['epoch'],started,kind='RESTORE_FINISHED',state='READY',operation=operation,evidence=reference)
    case.update(event=finished,parent=generation_pin)
    return generation,generation_pin,reference


def test_initial_epoch_uses_exact_registered_configuration(case):
    effective,evidence = module().resolve_capture(case['policy'],'source57',case['base_pin'])
    assert effective == case['base_pin']
    assert case['event'][1] in evidence and case['policy']['baselineTargetPin'] in evidence


def test_completed_epoch_resolves_immutable_capture_and_target(case):
    original = case['root'].joinpath('capture.json').read_bytes()
    generation,gen_pin,receipt = complete(case)
    selected,evidence = module().resolve_capture(case['policy'],'source57',case['base_pin'])
    assert selected == generation['captureBindings']['source57']['capturePin']
    assert all(p in evidence for p in (gen_pin,receipt,case['event'][1]))
    target,target_pin,proof = module().resolve_target(case['policy'])
    assert target == case['target'] and target_pin == generation['targetPin'] and gen_pin in proof
    assert case['root'].joinpath('capture.json').read_bytes() == original


@pytest.mark.parametrize('state',['REPLACING','FAILED_RETAINED'])
def test_nonready_epoch_cannot_capture_old_program(case,state):
    start = fixture_event(case['epoch'],case['event'],kind='RESTORE_STARTED',state='REPLACING',operation='incomplete')
    if state == 'FAILED_RETAINED':
        ref = write(case['root']/'failed.json',dict(state=state,operationId='incomplete'))
        fixture_event(case['epoch'],start,kind='RESTORE_FINISHED',state=state,operation='incomplete',evidence=ref)
    with pytest.raises(Exception,match='PROGRAM_EPOCH_NOT_READY'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


@pytest.mark.parametrize('field,value',[
    ('operationId','other'),('epochId','f'*64),('policySha256','0'*64),('targetConfigRef','other'),
    ('parentGenerationPin',{'path':'/wrong','bytes':0,'sha256':'0'*64}),('baselineTargetPin',None)])
def test_generation_binding_mismatch_is_not_baseline_fallback(case,field,value):
    complete(case,generation_changes={field:value})
    with pytest.raises(Exception,match='PROGRAM_GENERATION_BINDING_INVALID'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


def test_subsequent_success_without_generation_is_rejected(case):
    complete(case,receipt_changes={'programGenerationPin':None})
    with pytest.raises(Exception,match='PROGRAM_GENERATION_REQUIRED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


def test_two_successes_must_continue_original_program_generation(case):
    _,first,_ = complete(case)
    complete(case,'restore-2',generation_changes={'parentGenerationPin':None})
    with pytest.raises(Exception,match='PROGRAM_GENERATION_BINDING_INVALID'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


@pytest.mark.parametrize('change',['database','lock','data-service','data-path','credential','storage','source'])
def test_program_generation_cannot_reassign_target_resources(case,change):
    target = deepcopy(case['target'])
    if change=='database': target['database']='other'
    elif change=='lock': target['replacement']['lockPath']='/other.lock'
    elif change=='data-service': target['services'][0]['id']='0'*64
    elif change=='data-path': target['dataPaths']=['/other']
    elif change=='credential': target['secrets']={}
    elif change=='storage': target['replacement']['storage']={}
    else: target['sourceConfigRef']='other'
    complete(case,target=target)
    with pytest.raises(Exception,match='PROGRAM_TARGET_SCOPE_CHANGED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


@pytest.mark.parametrize('change',['source','lock','database','mysql','objects','writers','images','tools'])
def test_capture_generation_cannot_change_physical_source(case,change):
    capture=deepcopy(case['capture'])
    if change=='source': capture['source']['sourceIdentity']='other'
    elif change=='lock': capture['sourceLockPath']='/other.lock'
    elif change=='database': capture['source']['database']='other'
    elif change=='mysql': capture['source']['mysqlContainerId']='0'*64
    elif change=='objects': capture['source']['objectSourcePin']=write(case['root']/'other-objects.json',dict(sourceIdentity='other',versionPins=[]))
    elif change=='writers': capture['source']['writerContainerIds']=['0'*64]
    elif change=='images': capture['source']['applicationImageIds']=['sha256:'+'0'*64]
    else: capture['tools']={'docker':'/other'}
    complete(case,capture=capture)
    with pytest.raises(Exception,match='PROGRAM_CAPTURE_SCOPE_CHANGED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


def test_requested_source_and_base_pin_must_match_registered_policy(case):
    with pytest.raises(Exception,match='PROGRAM_CAPTURE_SOURCE_UNREGISTERED'):
        module().resolve_capture(case['policy'],'other',case['base_pin'])
    changed=dict(case['base_pin'],sha256='0'*64)
    with pytest.raises(Exception,match='PROGRAM_CAPTURE_BASE_CHANGED'):
        module().resolve_capture(case['policy'],'source57',changed)


def test_current_epoch_is_rechecked_after_reading_generation(case):
    generation,_,_=complete(case)
    from recovery_engine import pinned_json
    def reader(reference):
        value=pinned_json(reference)
        if reference==generation['targetPin']:
            fixture_event(case['epoch'],case['event'],kind='RESTORE_STARTED',state='REPLACING',operation='next')
        return value
    with pytest.raises(Exception,match='PROGRAM_EPOCH_CHANGED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'],reader=reader)


def test_changed_generation_bytes_fail_pin_verification(case):
    _,reference,_=complete(case)
    Path(reference['path']).write_text('{}',encoding='utf-8')
    with pytest.raises(Exception,match='PROGRAM_DOCUMENT_CHANGED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


def switched(case, tmp_path):
    """Construct a private, validated stopped-switch receipt from explicit rows."""
    from test_recovery_program_containers import original, image, created
    from recovery_main_target import service_configuration_digest, network_attachments
    from recovery_program_containers import create_request
    baseline = case['target']; target = deepcopy(baseline)
    old_services = {row['role']:row for row in baseline['services']}
    new_services = {row['role']:row for row in target['services']}
    originals={}; requests={}; applications={}; ids={}
    for role,identity,new_id in [('backend','d','6'),('frontend','e','7')]:
        before=original(); before.update(Id=identity*64,Name='/program-'+role,Image=old_services[role]['imageId'])
        before['NetworkSettings']['Networks']['task-network']['Aliases']=[role,identity*12]
        old_services[role]['ip']='172.20.0.5' if role=='backend' else '172.20.0.6'
        baseline['replacement']['services'][role].update(labels=before['Config']['Labels'],mounts=before['Mounts'])
        baseline['mainApplication']['serviceConfigurationDigests'][role]=service_configuration_digest(before)
        baseline['mainApplication']['networkAttachments'][role]=network_attachments(before)
        request=create_request(before,image()); after=created(request)
        after.update(Id=new_id*64,Name=before['Name'])
        after['NetworkSettings']['Networks']['task-network']['Aliases']=[role,new_id*12]
        retained=deepcopy(before);retained['Name']+="-retained-test";retained['NetworkSettings']['Networks']={}
        originals[role]=before;requests[role]=request
        applications[role]=write(tmp_path/(role+'-verified.json'),dict(original=before,created=after,retained=retained))
        ids[before['Id']]=after['Id']
        new_services[role].update(id=after['Id'],imageId=after['Image'])
        target['replacement']['services'][role].update(id=after['Id'],imageId=after['Image'],labels=after['Config']['Labels'],mounts=after['Mounts'])
        target['mainApplication']['serviceConfigurationDigests'][role]=service_configuration_digest(after)
        target['mainApplication']['networkAttachments'][role]=network_attachments(after)
        for binding in target['mainApplication']['archiveImageBindings']:
            if binding['role']==role:binding['imageId']=after['Image']
    target['mainApplication']['networks'][0]['memberContainerIds']=sorted(ids.get(i,i) for i in baseline['mainApplication']['networks'][0]['memberContainerIds'])
    target['mainApplication']['writerAdmission']['approvedWriterContainerIds']=['6'*64]
    target['mainApplication']['writerAdmission']['evidencePin']=write(tmp_path/'new-writer.json',dict(writerContainerIds=['6'*64],database='app'))
    case['policy']['baselineTargetPin']=write(case['root']/'target.json',baseline)
    intent=write(tmp_path/'switch-intent.json',dict(schemaVersion='MainProgramSwitchIntent/v1',operationId='restore-1',
        originals=originals,requests=requests,engineMetadata={'OperatingSystem':'Linux'}))
    switch=write(tmp_path/'switch-result.json',dict(schemaVersion='MainProgramSwitchResult/v1',state='CREATED_STOPPED',
        operationId='restore-1',intentPin=intent,applicationPins=applications))
    capture=deepcopy(case['capture']);capture['source']['writerContainerIds']=['6'*64,'7'*64]
    capture['source']['applicationImageIds']=[new_services[s['role']]['imageId'] for s in baseline['services']]
    versions=write(tmp_path/'new-version.json',dict(images={r:s['imageId'] for r,s in new_services.items()}))
    capture['source']['objectSourcePin']=write(tmp_path/'new-objects.json',dict(sourceIdentity=case['epoch']['sourceIdentity'],versionPins=[versions]))
    return target,capture,switch


def test_successful_switch_advances_program_ids_and_capture_images(case,tmp_path):
    target,capture,switch=switched(case,tmp_path)
    generation,_,_=complete(case,target=target,capture=capture,generation_changes={'switchResultPin':switch})
    selected,_=module().resolve_capture(case['policy'],'source57',case['base_pin'])
    assert selected==generation['captureBindings']['source57']['capturePin']
    current,_,_=module().resolve_target(case['policy'])
    assert current==target


@pytest.mark.parametrize('field',['mounts','port','writer','image','data-scope'])
def test_switch_receipt_does_not_authorize_unrelated_target_changes(case,tmp_path,field):
    target,capture,switch=switched(case,tmp_path)
    if field=='mounts': target['replacement']['services']['backend']['mounts']=[]
    elif field=='port': target['services'][3]['ip']='10.20.30.40'
    elif field=='writer': target['mainApplication']['writerAdmission']['approvedWriterContainerIds']=['8'*64]
    elif field=='image': target['services'][3]['imageId']='sha256:'+'8'*64
    else:target['database']='other'
    complete(case,target=target,capture=capture,generation_changes={'switchResultPin':switch})
    with pytest.raises(Exception,match='PROGRAM_TARGET_SCOPE_CHANGED'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


@pytest.mark.parametrize('field',['target','capture'])
def test_malformed_pinned_configuration_has_explicit_program_error(case,field):
    if field=='target':
        complete(case,target={'invalid':'target'})
    else:
        complete(case,capture={'source':{}})
    code='PROGRAM_TARGET_SCOPE_CHANGED' if field=='target' else 'PROGRAM_GENERATION_FORMAT_INVALID'
    with pytest.raises(Exception,match=code):
        module().resolve_capture(case['policy'],'source57',case['base_pin'])


def test_guard_is_checked_during_epoch_history_scan(case):
    complete(case)
    from recovery_backup_epoch import read_current
    checks=[]
    def guard():
        checks.append(1)
        if len(checks)==3:raise RuntimeError('shared budget expired')
    with pytest.raises(RuntimeError,match='shared budget expired'):
        read_current(case['epoch'],guard=guard)
    assert len(checks)==3


def test_resolver_propagates_shared_guard_before_reading_history(case):
    def guard():raise TimeoutError('shared program budget expired')
    with pytest.raises(TimeoutError,match='shared program budget expired'):
        module().resolve_capture(case['policy'],'source57',case['base_pin'],guard=guard)


def test_metadata_reconciliation_keeps_shared_budget(case):
    from recovery_backup_epoch import try_reconcile_current
    def guard():raise RuntimeError('shared metadata budget expired')
    with pytest.raises(RuntimeError,match='shared metadata budget expired'):
        try_reconcile_current(case['epoch'],guard=guard)
