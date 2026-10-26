"""Real loopback HTTP/durable files; no backup or restore is dispatched."""
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/spug'))
import smallapp_adapter as adapter
import smallapp_entry as entry


@pytest.fixture
def original(tmp_path):
    request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='original-restore-query',
        action='RESTORE',sourceConfigRef='source',targetConfigRef='target',parentChainRef=None,
        recoveryPointRef='full-point')
    result=dict(adapter.running(request),state='FAILED',errorCode='FORMAL_DATA_TYPE_UNSUPPORTED',
                logRefs=['original-logs'],resultRef='original-result')
    state=dict(result=result,requests=[],status=200)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            state['requests'].append(('GET',self.path))
            body=json.dumps(state['result']).encode()
            self.send_response(state['status']);self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def do_POST(self):
            state['requests'].append(('POST',self.path));self.send_response(500);self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,kwargs=dict(poll_interval=0.01),daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    adapter.write_json(tmp_path/'auth.json',dict(headers={}))
    adapter.write_json(tmp_path/'bridge.json',dict(sourceConfigRefs=['source'],targetConfigRefs=['target'],
        submitUrl=base+'/operations',queryUrlTemplate=base+'/operations/{operationId}',credentialRef='auth.json'))
    bridge=adapter.HttpBridge(tmp_path/'bridge.json')
    journal=tmp_path/'journal'
    path=journal/(hashlib.sha256(request['operationId'].encode()).hexdigest()+'.json')
    adapter.write_json(path,dict(request=request,bridgeFingerprint=bridge.fingerprint,lastResult=result))
    try:yield request,result,bridge,journal,path,state
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


@pytest.mark.parametrize('terminal_file',[False,True])
def test_explicit_failed_restore_query_uses_get_and_retains_original(original,terminal_file):
    request,result,bridge,journal,path,state=original
    if terminal_file:adapter.remember_terminal(request,bridge.fingerprint,result,journal)
    before=path.read_bytes()
    terminal=adapter.terminal_path(request,journal)
    terminal_before=terminal.read_bytes() if terminal.exists() else None
    assert adapter.execute(request,bridge,journal,query_only=True)==result
    assert state['requests']==[('GET','/operations/'+request['operationId'])]
    assert path.read_bytes()==before
    assert adapter.read_json(terminal)['result']==result
    if terminal_before is not None:assert terminal.read_bytes()==terminal_before
    observation=adapter.read_json(next((journal/'observations').glob('*.json')))
    assert observation['submissionIssuedThisRun'] is False and observation['queryError'] is None


@pytest.mark.parametrize('change',['bridge','request'])
def test_binding_drift_never_queries_or_submits(original,change):
    request,result,bridge,journal,path,state=original
    adapter.remember_terminal(request,bridge.fingerprint,result,journal)
    before=path.read_bytes()
    if change=='bridge':bridge.fingerprint='changed'
    else:request=dict(request,recoveryPointRef='another-point')
    with pytest.raises(adapter.Refused):adapter.execute(request,bridge,journal,query_only=True)
    assert state['requests']==[] and path.read_bytes()==before


@pytest.mark.parametrize('change',['success','running','failure','http'])
@pytest.mark.parametrize('terminal_file',[False,True])
def test_query_conflict_or_transport_error_preserves_failed_result_and_is_exposed(
        original,tmp_path,monkeypatch,change,terminal_file):
    request,result,bridge,journal,path,state=original
    if terminal_file:adapter.remember_terminal(request,bridge.fingerprint,result,journal)
    before=path.read_bytes()
    if change=='success':state['result']=dict(result,state='SUCCEEDED',errorCode=None)
    if change=='running':state['result']=adapter.running(request)
    if change=='failure':state['result']=dict(result,errorCode='DIFFERENT_FAILURE')
    if change=='http':state.update(status=503,result=dict(errorCode='BRIDGE_TEMPORARILY_UNAVAILABLE'))
    ui=tmp_path/'ui'
    adapter.write_json(entry.record_path(request['operationId'],ui),dict(request=request,applicationId='app',
        spugTaskId=1,createdAt='2026-10-26T00:00:00Z',spugHistoryId=1,dispatchErrorCode=None,dispatchState='DISPATCHED'))
    monkeypatch.setattr(adapter,'request_bridge',lambda value:bridge)
    reply=entry.original_result(request['operationId'],ui,journal)
    assert reply['result']==result and reply['repeatSubmissionAllowed'] is False
    expected='BRIDGE_TEMPORARILY_UNAVAILABLE' if change=='http' else 'TERMINAL_EVIDENCE_CONFLICT'
    assert reply['queryError']==expected
    assert state['requests']==[('GET','/operations/'+request['operationId'])]
    assert path.read_bytes()==before
    assert adapter.read_json(adapter.terminal_path(request,journal))['result']==result
    observations=[adapter.read_json(p) for p in (journal/'observations').glob('*.json')]
    assert observations[-1]['queryError']==expected and observations[-1]['originalTerminalResult']==result


@pytest.mark.parametrize('kind',['duplicate_submit','successful_restore','failed_capture'])
def test_other_cached_terminal_behaviors_do_not_query(original,kind):
    request,result,bridge,journal,path,state=original
    if kind=='successful_restore':result=dict(result,state='SUCCEEDED',errorCode=None)
    if kind=='failed_capture':
        request=dict(request,action='FULL',recoveryPointRef=None,targetConfigRef=None)
        result=dict(result,action='FULL')
    adapter.write_json(path,dict(request=request,bridgeFingerprint=bridge.fingerprint,lastResult=result))
    assert adapter.execute(request,bridge,journal,query_only=kind!='duplicate_submit')==result
    assert state['requests']==[]
