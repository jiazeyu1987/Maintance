"""Actual program journals/release and processes; launcher records are protocols."""
from copy import deepcopy
from pathlib import Path
import os
import sys

import pytest

from test_recovery_program_retained_retry import retained, history_factory
from recovery_engine import pin, pinned_json, write

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend/src/main/resources'))
from recovery_control_smallapp_native import Native

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='real Linux locks/program proof')


@pytest.mark.parametrize('fault',['none','release_missing','release_wrong','worker_changed',
    'exit_missing','exit_timeout','exit_request','wrong_reason','not_main','live_pid','boot','outer_exit'])
def test_original_unknown_closes_only_from_released_same_program_failure(retained,tmp_path,fault):
    h=retained; e=h.e
    operation=tmp_path/'control-operation'; (operation/'execute').mkdir(parents=True,mode=0o700)
    request_pin=write(operation/'request.json',e.request)
    program_pin=write(tmp_path/'owner-program.json',{'program':'protocol boundary'})
    selection=dict(ownerConfigurationPin=e.owner_pin,ownerProgramPin=program_pin)
    outer=dict(schemaVersion='backup-restore-operation-result/v1',operationId=e.request['operationId'],
        requestId=e.request['operationId'],action='RESTORE',state='TERMINAL_UNKNOWN',
        failureCode='RESTORE_RESOURCE_NO_MUTATION_NOT_PROVEN',message='original failure',
        data={'retryPermitted':False},originalResultPins=[pin(e.root/'child-exit.json'),e.reservation],
        actualExitCode=1,startedAt='2026-11-11T00:00:00Z',finishedAt='2026-11-11T00:00:01Z')
    if fault=='wrong_reason':outer['failureCode']='ORIGINAL_CHILD_TIMEOUT'
    if fault=='outer_exit':outer['actualExitCode']=True
    original=write(e.root/'result.json',outer)
    intent=write(operation/'execute/native-intent.json',dict(operationId=e.request['operationId'],
        requestId=e.request['operationId'],requestPin=request_pin,configurationPin=e.owner_pin,programPin=program_pin))
    exited=dict(operationId=e.request['operationId'],requestId=e.request['operationId'],requestPin=request_pin,
        intentPin=intent,pid=99999999,actualExitCode=2,timedOut=False,resultPin=original)
    if fault=='exit_timeout':exited['timedOut']=True
    if fault=='exit_request':exited['requestPin']=program_pin
    if fault=='live_pid':exited['pid']=os.getpid()
    if fault!='exit_missing':write(operation/'execute/native-original-exit.json',exited)
    write(operation/'execute/native-process.json',dict(operationId=e.request['operationId'],
        requestId=e.request['operationId'],intentPin=intent,pid=exited['pid'],
        bootId='other' if fault=='boot' else Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
    release=e.root/'resource-no-mutation-release.json'
    if fault=='release_missing':release.unlink()
    elif fault=='release_wrong':
        changed=pinned_json(pin(release));changed['resultPin']=original;write(release,changed)
    elif fault=='worker_changed':Path(h.result_pin['path']).write_bytes(b'{}')
    if fault=='not_main':
        owner=deepcopy(e.owner);owner.pop('targetProgramPolicies')
        owner_pin=write(tmp_path/'legacy-owner.json',owner)
        selection['ownerConfigurationPin']=owner_pin
        write(operation/'execute/native-intent.json',dict(operationId=e.request['operationId'],
            requestId=e.request['operationId'],requestPin=request_pin,configurationPin=owner_pin,programPin=program_pin))
    class Routed(Native):
        def accepted_operation(self,value,selected):
            assert value==e.request and selected==selection
            return e.root
    native=Routed.__new__(Routed)
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    reply=native.refresh_original(e.request,operation,selection)
    assert reply['state']==('FAILED' if fault=='none' else 'RUNNING')
    if fault=='none':
        assert reply['errorCode']=='PROGRAM_TEST_RETAINED'
        observations=[pinned_json(pin(p)) for p in (operation/'queries').glob('*.json')]
        assert pin(release) in observations[0]['resolutionPins']
        assert h.result_pin in observations[0]['resolutionPins']
    assert all(p.read_bytes()==raw for p,raw in before.items())
