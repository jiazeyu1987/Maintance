"""Local process/file checks; Docker response snapshots are explicit unit fixtures."""
import os
from pathlib import Path

import pytest

from test_native_oom_target import module, target
from test_native_import_process_evidence import evidence, put


def retained_exit(evidence):
    native, value, operation, root, output = evidence
    for path in (operation/'execute/native-original-exit.json', root/'child-exit.json'):
        row = module.executor.document(module.executor.pin(path))
        row['actualExitCode'] = 1
        reference = put(path, row)
        if path.name == 'child-exit.json':
            output['originalResultPins'][1] = reference
    output['actualExitCode'] = 1
    return evidence


@pytest.mark.parametrize('change', ['none', 'boot', 'pid', 'timeout', 'unlisted', 'pending', 'boolean_owner_exit'])
def test_failed_retained_process_proof_requires_complete_exits(evidence, change):
    native, value, operation, root, output = retained_exit(evidence)
    process_path = operation/'execute/native-process.json'
    process = module.executor.document(module.executor.pin(process_path))
    if change == 'boot': process['bootId'] = 'other'
    if change == 'pid':
        process['pid'] = os.getpid()
        path = operation/'execute/native-original-exit.json'
        exited = module.executor.document(module.executor.pin(path))
        exited['pid'] = os.getpid()
        put(path, exited)
    put(process_path, process)
    if change == 'boolean_owner_exit':
        path=operation/'execute/native-original-exit.json'
        row=module.executor.document(module.executor.pin(path));row['actualExitCode']=True
        put(path,row)
    if change == 'timeout':
        output['originalResultPins'][1] = put(root/'child-exit.json', dict(actualExitCode=1,timedOut=True))
    if change in ('unlisted','pending'):
        row = module.executor.document(output['originalResultPins'][0])
        row['actualExitCode'] = None
        ref = put(root/('native-003.json' if change == 'unlisted' else 'native-001.json'), row)
        if change == 'pending': output['originalResultPins'][0] = ref
    if change == 'none':
        assert native.stopped_import_processes(value,operation,root,output,expected_exit=1)
    else:
        with pytest.raises(RuntimeError):
            native.stopped_import_processes(value,operation,root,output,expected_exit=1)


@pytest.mark.parametrize('change', ['none','mysql','redis','minio','backend','frontend','exec','paused',
                                  'restarting','claim','image','mount','before'])
def test_retained_failure_requires_all_original_services_stopped(target,tmp_path,change):
    native,value,selection,rows,data = target
    before = put(tmp_path/'restore-target-before.json',native.restore_target_observation(value,selection))
    (tmp_path/'execute').mkdir()
    put(tmp_path/'execute/native-intent.json',dict(restoreTargetPin=before))
    claim = put(data/'.recovery-operation.json',dict(operationId=value['operationId']))
    if change in ('mysql','redis','minio','backend','frontend'):
        next(row for row in rows if row['Id']==change)['State'].update(Running=True,Pid=123)
    if change == 'exec': rows[0]['ExecIDs'] = ['live']
    if change == 'paused': rows[0]['State']['Paused'] = True
    if change == 'restarting': rows[0]['State']['Restarting'] = True
    if change == 'claim': put(data/'.recovery-operation.json',dict(operationId='other'))
    if change == 'image': rows[0]['Image'] = 'other'
    if change == 'mount': rows[0]['Mounts'][0]['Source'] = str(data/'other')
    if change == 'before': put(tmp_path/'restore-target-before.json',{})
    if change == 'none':
        proof = native.stopped_retained_target(value,tmp_path,selection)
        assert proof['claimPin']==claim and proof['partialTargetRetained'] is True
        assert module.executor.verify(claim).is_file()
    else:
        with pytest.raises(RuntimeError): native.stopped_retained_target(value,tmp_path,selection)


def test_known_failure_refresh_exposes_release_blocker_without_running_projection(target,evidence,monkeypatch):
    native,value,operation,root,output = retained_exit(evidence)
    _,_,selection,_,_ = target
    value['targetConfigRef']='target'
    selection['ownerProgramPin']=selection['ownerConfigurationPin']
    request_pin=put(operation/'request.json',value)
    put(operation/'execute/native-intent.json',dict(operationId=value['operationId'],requestId=value['operationId'],
        requestPin=request_pin,configurationPin=selection['ownerConfigurationPin'],programPin=selection['ownerProgramPin']))
    output.update(schemaVersion='backup-restore-operation-result/v1',operationId=value['operationId'],
        requestId=value['operationId'],action='RESTORE',state='FAILED_RETAINED',failureCode='FORMAL_DATA_TYPE_UNSUPPORTED',
        message='failure',data=dict(mutationDispatched=True,partialTargetRetained=True,retryPermitted=False),
        startedAt='2026-10-26T00:00:00Z',finishedAt='2026-10-26T00:00:01Z')
    put(root/'result.json',output)
    put(root/'resource-reservation.json',{})
    monkeypatch.setattr(native,'accepted_operation',lambda *_:root)
    import recovery_resource_admission as admission
    def reject(*args): raise RuntimeError('ORIGINAL_TARGET_WRITER_UNRESOLVED')
    monkeypatch.setattr(admission,'release_retained_failure',reject,raising=False)
    reply=native.refresh_original(value,operation,selection)
    assert reply['state']=='FAILED' and reply['errorCode']=='FORMAL_DATA_TYPE_UNSUPPORTED'
    observations=[module.executor.document(module.executor.pin(p)) for p in (operation/'queries').glob('*.json')]
    assert observations[-1]['resourceReleaseError']=='ORIGINAL_TARGET_WRITER_UNRESOLVED'


def test_completed_failure_without_owner_result_is_not_refreshed(tmp_path,monkeypatch):
    native=module.Native.__new__(module.Native)
    value=dict(operationId='original',action='RESTORE')
    selection={}
    reply=module.result(value,'FAILED','ORIGINAL_FAILURE')
    completion=dict(operationId='original',uiRequestSha256=module.fingerprint(value),selection=selection,
                    result=reply,terminal=None)
    reference=put(tmp_path/'completion.json',completion)
    (tmp_path/'execute').mkdir()
    put(tmp_path/'execute/native-intent.json',{})
    calls=[]
    monkeypatch.setattr(native,'refresh_original',lambda *args:(calls.append(args) or reply))
    assert native.reconcile(value,tmp_path,selection)==reply
    assert not calls and module.executor.verify(reference).is_file()


@pytest.mark.parametrize('change',['none','mysql_running','claim','unlisted','worker_unpinned'])
def test_refresh_releases_only_proven_retained_failure_and_preserves_later_reservation(
        target,evidence,monkeypatch,change):
    import recovery_resource_admission as admission
    native,value,operation,root,output=retained_exit(evidence)
    _,_,selection,rows,data=target
    value['targetConfigRef']='target'
    selection['ownerProgramPin']=selection['ownerConfigurationPin']
    request_pin=put(operation/'request.json',value)
    before=put(operation/'restore-target-before.json',native.restore_target_observation(value,selection))
    intent=put(operation/'execute/native-intent.json',dict(operationId=value['operationId'],
        requestId=value['operationId'],requestPin=request_pin,configurationPin=selection['ownerConfigurationPin'],
        programPin=selection['ownerProgramPin'],restoreTargetPin=before))
    for name in ('native-process.json','native-original-exit.json'):
        path=operation/'execute'/name
        row=module.executor.document(module.executor.pin(path))
        row['intentPin']=intent
        if name=='native-original-exit.json':row['requestPin']=request_pin
        put(path,row)
    importer=module.executor.document(output['originalResultPins'][-1])
    importer['actualExitCode']=0
    output['originalResultPins'][-1]=put(root/'importer-002.json',importer)
    output.update(schemaVersion='backup-restore-operation-result/v1',operationId=value['operationId'],
        requestId=value['operationId'],action='RESTORE',state='FAILED_RETAINED',failureCode='FORMAL_DATA_TYPE_UNSUPPORTED',
        message='failure',data=dict(mutationDispatched=True,partialTargetRetained=True,retryPermitted=False),
        startedAt='2026-10-26T00:00:00Z',finishedAt='2026-10-26T00:00:01Z')
    host=root.parent/'host-resources';host.mkdir(mode=0o700)
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    monkeypatch.setattr(admission,'admit',lambda *args:{'admitted':True})
    configuration=module.executor.document(selection['ownerConfigurationPin'])
    reservation=admission.reserve(configuration,value,root)
    output['originalResultPins'].append(reservation)
    worker=put(root/'worker-result.json',output)
    if change!='worker_unpinned':output['originalResultPins'].append(worker)
    result_pin=put(root/'result.json',output)
    native_exit_path=operation/'execute/native-original-exit.json'
    native_exit=module.executor.document(module.executor.pin(native_exit_path))
    native_exit.update(resultPin=result_pin,timedOut=False,
        stdoutPin=put(operation/'execute/stdout',{}),stderrPin=put(operation/'execute/stderr',{}))
    put(native_exit_path,native_exit)
    original_reply=module.result(value,'FAILED','FORMAL_DATA_TYPE_UNSUPPORTED')
    completion_pin=put(operation/'completion.json',dict(operationId=value['operationId'],
        uiRequestSha256=module.fingerprint(value),selection=selection,result=original_reply,terminal=native_exit))
    claim=put(data/'.recovery-operation.json',dict(operationId='other' if change=='claim' else value['operationId']))
    if change=='mysql_running':rows[0]['State'].update(Running=True,Pid=123)
    if change=='unlisted':put(root/'native-003.json',dict(actualExitCode=0))
    monkeypatch.setattr(native,'accepted_operation',lambda *_:root)
    reply=native.reconcile(value,operation,selection)
    assert reply['state']=='FAILED' and reply['errorCode']=='FORMAL_DATA_TYPE_UNSUPPORTED'
    assert (host/'active.json').exists() is (change!='none')
    assert module.executor.verify(claim).is_file() and module.executor.verify(result_pin).is_file()
    assert module.executor.verify(completion_pin).is_file()
    if change=='none':
        next_root=root.parent/'next';next_root.mkdir()
        admission.reserve(configuration,dict(value,operationId='next'),next_root)
        prior=(host/'active.json').read_bytes()
        assert native.reconcile(value,operation,selection)==reply
        assert (host/'active.json').read_bytes()==prior
