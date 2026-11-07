"""Real launcher/worker processes exercise the asynchronous journal protocol.

These fixtures do not execute database backups. They reproduce the production
exit-2 waiting receipt, immutable RUNNING completion, and separate final result.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend/src/main/resources'),str(Path(__file__).resolve().parent)]
import recovery_control_executor as executor
from recovery_control_smallapp import Ledger,canonical,fingerprint,local_read,persist,result,Failure
from test_automatic_incremental_plan import MetadataFixture,ui_request


LAUNCHER=r'''
import argparse,hashlib,json,pathlib,sys
p=argparse.ArgumentParser();p.add_argument('--configuration');p.add_argument('--request');p.add_argument('--output');a=p.parse_args()
config=json.loads(pathlib.Path(a.configuration).read_bytes());request=json.loads(pathlib.Path(a.request).read_bytes())
root=pathlib.Path(config['operationRoot'])/hashlib.sha256(request['operationId'].encode()).hexdigest()
value=dict(schemaVersion='backup-restore-operation-result/v1',operationId=request['operationId'],requestId=request['operationId'],
 action=request['action'],state='TERMINAL_UNKNOWN',failureCode='REPOSITORY_QUERY_ORIGINAL_OPERATION',message='Protocol fixture waiting for actual child',
 data=dict(operationDirectory=str(root),resultRef=str(root/'result.json')),originalResultPins=[],actualExitCode=None,
 startedAt='2026-11-07T00:00:00Z',finishedAt='2026-11-07T00:00:01Z')
pathlib.Path(a.output).write_text(json.dumps(value),encoding='utf-8');sys.exit(2)
'''
WORKER=r'''
import json,pathlib,sys,time,os
root=pathlib.Path(sys.argv[1])
while not (root/'release').exists():time.sleep(.005)
value=json.loads((root/'terminal-input.json').read_bytes())
(root/'result.json').write_text(json.dumps(value),encoding='utf-8')
'''


def overwrite(path,value):
    path.write_bytes(canonical(value));path.chmod(0o600)
    return executor.pin(path)


class AsyncFixture:
    def __init__(self,root):
        self.metadata=MetadataFixture(root);self.root=root;self.native=self.metadata.native
        owner_path=root/'repository.json';owner=local_read(owner_path)
        owner.update(schemaVersion='RepositoryMinimumConfiguration/v1',operationRoot=str(root/'owners'))
        (root/'owners').mkdir(mode=0o700)
        self.owner=overwrite(owner_path,owner)
        config=self.native.configuration();config['sourceConfigurations']['source-A']=self.owner
        self.native.config_pin=overwrite(root/'configuration.json',config)
        self.launcher=root/'waiting-launcher.py';self.launcher.write_text(LAUNCHER,encoding='utf-8')
        self.worker=root/'actual-worker.py';self.worker.write_text(WORKER,encoding='utf-8')
        self.ledger=Ledger(root/'ledger',self.native);self.children=[]

    def close(self):
        for process in self.children:
            if process.poll() is None:process.terminate()
            process.wait(timeout=5)

    def operation(self,reference,*,terminal='SUCCEEDED',finish=True,failure_exit=1):
        value=ui_request(reference);selection=dict(ownerConfigurationPin=self.owner,
            ownerProgramPin=executor.pin(self.launcher),configurationPin=self.native.config_pin)
        self.ledger.reserve(value,selection);directory=self.root/'ledger'/reference
        owner_root=self.root/'owners'/hashlib.sha256(reference.encode()).hexdigest();owner_root.mkdir(mode=0o700)
        persist(owner_root/'request.json',value)
        persist(owner_root/'start.json',dict(configurationPin=self.owner,requestSha256=fingerprint(value),readbackOnly=False,
            startedAt='2026-11-07T00:00:00Z',deadlineMonotonic=time.monotonic()+60))
        self.metadata.point(reference)
        final=local_read(self.root/reference/'operation.json')
        if terminal!='SUCCEEDED':
            final.update(state=terminal,actualExitCode=failure_exit,failureCode='CAPTURE_FAILED' if terminal=='FAILED_RETAINED' else 'UNKNOWN',data={})
            if failure_exit is not None:
                child=subprocess.Popen([sys.executable,'-B','-c','import sys;sys.exit('+str(failure_exit)+')'])
                assert child.wait(timeout=5)==failure_exit
                persist(owner_root/'capture-process.json',dict(operationId=reference,pid=child.pid,startedAt='2026-11-07T00:00:00Z'))
                persist(owner_root/'capture-terminal.json',dict(schemaVersion='RepositoryMinimumChildTerminal/v1',operationId=reference,
                    pid=child.pid,actualExitCode=failure_exit,processTerminated=True,state='EXITED',at='2026-11-07T00:00:01Z'))
                final['originalResultPins'].append(executor.pin(owner_root/'capture-terminal.json'))
        # Large original is deliberately a metadata record. Scheduling closure
        # must not read it; detailed queries/current-chain admission still must.
        large=owner_root/'large-readback.json';large.write_bytes(b'{"padding":"'+b'x'*(2*1024*1024)+b'"}')
        final['originalResultPins'].append(executor.pin(large))
        persist(owner_root/'terminal-input.json',final)
        process=subprocess.Popen([sys.executable,'-B',str(self.worker),str(owner_root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.children.append(process)
        persist(owner_root/'worker-process.json',dict(operationId=reference,pid=process.pid,startedAt='2026-11-07T00:00:00Z'))
        execute=directory/'execute';execute.mkdir(mode=0o700)
        launcher_exit=executor.run_owner(executor.pin(Path(sys.executable).resolve()),executor.pin(self.launcher),self.owner,
            executor.pin(directory/'request.json'),execute/'result.json',environment=dict(os.environ),working_directory=str(self.root),deadline_milliseconds=5000)
        assert launcher_exit['actualExitCode']==2
        persist(directory/'completion.json',dict(operationId=reference,uiRequestSha256=fingerprint(value),selection=selection,
            result=result(value,'RUNNING','REPOSITORY_QUERY_ORIGINAL_OPERATION'),terminal=launcher_exit))
        if finish:
            (owner_root/'release').touch();assert process.wait(timeout=5)==0
            if terminal=='SUCCEEDED':
                binding=dict(schemaVersion='SmallAppPointBinding/v2',reference=reference,sourceConfigRef='source-A',
                    resultPin=executor.pin(owner_root/'result.json'))
                persist(directory/'point-binding.json',binding)
                overwrite(self.root/'registry/points'/(reference+'.pin.json'),executor.pin(directory/'point-binding.json'))
        return dict(value=value,directory=directory,root=owner_root,selection=selection,process=process,large=large)


@pytest.fixture
def fixture(tmp_path):
    f=AsyncFixture(tmp_path)
    try:yield f
    finally:f.close()


def test_fifteen_real_async_operations_close_without_reconciling_or_reading_large_originals(fixture,monkeypatch):
    rows=[fixture.operation('async-%02d'%i,terminal='SUCCEEDED' if i%2==0 else 'FAILED_RETAINED') for i in range(15)]
    read=executor.pinned_read;reconcile=fixture.native.reconcile;counts={'readback':0,'reconcile':0}
    def measured(path,*a,**kw):
        if Path(path).name=='large-readback.json':counts['readback']+=1
        return read(path,*a,**kw)
    def observed(*a,**kw):counts['reconcile']+=1;return reconcile(*a,**kw)
    monkeypatch.setattr(executor,'pinned_read',measured);monkeypatch.setattr(fixture.native,'reconcile',observed)
    fixture.ledger.require_source_idle('source-A')
    assert counts=={'readback':0,'reconcile':0},counts
    assert all(local_read(r['directory']/'completion.json')['result']['state']=='RUNNING' for r in rows)
    assert all(not (r['directory']/'queries').exists() for r in rows)


def test_live_matching_worker_cannot_close_even_if_result_is_present(fixture):
    row=fixture.operation('live-worker',finish=False)
    overwrite(row['root']/'result.json',local_read(row['root']/'terminal-input.json'))
    with pytest.raises(Failure,match='SOURCE_ASYNC_WORKER_STILL_RUNNING'):
        fixture.native.asynchronously_closed(row['directory'],row['value'])


@pytest.mark.parametrize('case',['waiting-other-root','waiting-other-result','waiting-other-operation','final-other-operation','final-other-action','worker-other-operation','worker-invalid-pid','launcher-wrong-pid','wrong-start'])
def test_async_binding_corruption_is_rejected(fixture,case):
    row=fixture.operation('corrupt-'+case)
    directory=row['directory'];root=row['root']
    if case.startswith('waiting-'):
        path=directory/'execute/result.json';waiting=json.loads(path.read_bytes())
        if case=='waiting-other-root':waiting['data']['operationDirectory']=str(root.parent/'foreign')
        elif case=='waiting-other-result':waiting['data']['resultRef']=str(root/'foreign.json')
        else:waiting['operationId']='foreign'
        newpin=overwrite(path,waiting);exitpath=directory/'execute/native-original-exit.json';exited=local_read(exitpath);exited['resultPin']=newpin;overwrite(exitpath,exited)
        completion=local_read(directory/'completion.json');completion['terminal']=exited;overwrite(directory/'completion.json',completion)
    elif case.startswith('final-'):
        path=root/'result.json';value=json.loads(path.read_bytes());value['operationId' if case.endswith('operation') else 'action']='foreign';overwrite(path,value)
    elif case.startswith('worker-'):
        path=root/'worker-process.json';value=local_read(path);value['operationId' if case.endswith('operation') else 'pid']='foreign';overwrite(path,value)
    elif case=='launcher-wrong-pid':
        path=directory/'execute/native-process.json';value=local_read(path);value['pid']+=1;overwrite(path,value)
    else:
        path=root/'start.json';value=local_read(path);value['requestSha256']='0'*64;overwrite(path,value)
    with pytest.raises(Failure):fixture.native.asynchronously_closed(directory,row['value'])


def test_unknown_terminal_or_missing_result_is_not_closed(fixture):
    row=fixture.operation('unknown-terminal',terminal='TERMINAL_UNKNOWN')
    assert fixture.native.asynchronously_closed(row['directory'],row['value']) is False
    row2=fixture.operation('missing-terminal',finish=False)
    assert fixture.native.asynchronously_closed(row2['directory'],row2['value']) is False


def test_immutable_async_terminals_survive_new_ledger_instance(fixture):
    row=fixture.operation('restart-success')
    rebuilt=Ledger(fixture.root/'ledger',fixture.native)
    rebuilt.require_source_idle('source-A')
    assert not (row['directory']/'queries').exists()


def test_restore_never_uses_backup_async_termination(fixture):
    value=dict(ui_request('restore-boundary'),action='RESTORE',targetConfigRef='target-A',recoveryPointRef='point-A')
    assert fixture.native.asynchronously_closed(fixture.root/'not-existing',value) is False


def test_failed_async_closure_is_not_source_health_or_new_backup_admission(fixture):
    row=fixture.operation('failed-source',terminal='FAILED_RETAINED')
    assert fixture.native.asynchronously_closed(row['directory'],row['value']) is True
    assert not (row['directory']/'queries').exists()
    assert json.loads((row['root']/'result.json').read_bytes())['state']=='FAILED_RETAINED'


@pytest.mark.parametrize('case',['failure-missing','failure-empty','failure-invalid','exit-none','exit-zero','terminal-not-pinned','terminal-other-operation','terminal-not-ended','child-pid-mismatch'])
def test_failed_async_terminal_proof_cannot_be_replaced_by_state_string(fixture,case):
    row=fixture.operation('bad-failure-'+case,terminal='FAILED_RETAINED')
    path=row['root']/'result.json';value=json.loads(path.read_bytes())
    if case.startswith('failure-'):
        value['failureCode']={'failure-missing':None,'failure-empty':'','failure-invalid':'not a failure code'}[case]
    elif case.startswith('exit-'):value['actualExitCode']=None if case=='exit-none' else 0
    elif case=='terminal-not-pinned':value['originalResultPins']=[p for p in value['originalResultPins'] if not p['path'].endswith('capture-terminal.json')]
    elif case=='child-pid-mismatch':
        childpath=row['root']/'capture-process.json';child=local_read(childpath);child['pid']+=1;overwrite(childpath,child)
    else:
        childpath=row['root']/'capture-terminal.json';child=local_read(childpath)
        child['operationId' if case=='terminal-other-operation' else 'processTerminated']='foreign' if case=='terminal-other-operation' else False
        newpin=overwrite(childpath,child);value['originalResultPins']=[newpin if p['path']==str(childpath) else p for p in value['originalResultPins']]
    overwrite(path,value)
    with pytest.raises(Failure):fixture.native.asynchronously_closed(row['directory'],row['value'])


def test_failed_archive_can_have_successful_capture_child(fixture):
    row=fixture.operation('failed-archive-after-capture',terminal='FAILED_RETAINED',failure_exit=0)
    assert fixture.native.asynchronously_closed(row['directory'],row['value']) is True
    assert json.loads((row['root']/'result.json').read_bytes())['actualExitCode']==0


def test_failure_before_any_child_keeps_unobserved_exit(fixture):
    row=fixture.operation('failed-before-capture',terminal='FAILED_RETAINED',failure_exit=None)
    assert fixture.native.asynchronously_closed(row['directory'],row['value']) is True


def test_explicit_cancelled_worker_keeps_unobserved_owner_exit(fixture):
    row=fixture.operation('cancelled-owner',terminal='FAILED_RETAINED',finish=False,failure_exit=0)
    worker=row['process'];ticks=int(Path('/proc',str(worker.pid),'stat').read_text().split(') ')[1].split()[19])
    intent=dict(operationId=row['value']['operationId'],pid=worker.pid,signal='SIGTERM',authorizedByUser=True,processStartTicks=ticks)
    persist(row['root']/'external-stop-intent.json',intent)
    worker.terminate();assert worker.wait(timeout=5)==-15
    persist(row['root']/'external-stop-observation.json',dict(intent,processObservedExited=True,originalTerminalResultPresent=False,actualProcessExitCode=None))
    value=local_read(row['root']/'terminal-input.json')
    value.update(actualExitCode=None,failureCode='REPOSITORY_ARCHIVE_CANCELLED_BY_OPERATOR',
        data=dict(operatorCancellation=True,originalWorkerResultProduced=False,workerExitCodeObserved=False,archiveCreated=False,restoreExecuted=False))
    value['originalResultPins']=[executor.pin(row['root']/name) for name in ('request.json','start.json','worker-process.json','external-stop-intent.json','external-stop-observation.json')]
    overwrite(row['root']/'result.json',value)
    assert fixture.native.asynchronously_closed(row['directory'],row['value']) is True


def test_detailed_original_id_query_keeps_full_original_validation(fixture,monkeypatch):
    row=fixture.operation('detail-failure',terminal='FAILED_RETAINED')
    read=executor.pinned_read;counts=[]
    def measured(path,*a,**kw):
        if Path(path)==row['large']:counts.append(path)
        return read(path,*a,**kw)
    monkeypatch.setattr(executor,'pinned_read',measured)
    assert fixture.ledger.status(row['value']['operationId'])['state']=='FAILED'
    assert counts and (row['directory']/'queries').is_dir()
