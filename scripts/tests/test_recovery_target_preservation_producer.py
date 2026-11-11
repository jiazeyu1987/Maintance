"""Actual producer/runtime and persistent preservation proof; finite services.

Uses the real original chain, source, capture, publication, ctx/custody, epoch,
and restore executor. Only the external Docker/SQL/SMB protocols are local.
"""
from pathlib import Path
import base64
import hashlib
import importlib
import json
import shlex
import subprocess
import sys
import traceback
from copy import deepcopy
from types import SimpleNamespace

import pytest

from test_recovery_target_preservation_handoff import (handoff_case,publication_case,
    capture_protocol,original_capture_protocol,case,restore_case)
from test_recovery_program_restore import freeze_inputs
from test_recovery_program_producer_contract import producer_case as actual_process_protocol, SQL_CONSUMER
import recovery_minimal_runtime as runtime
import recovery_minimal_worker as worker
import recovery_program_evidence as historical
from recovery_engine import RecoveryError,canonical,digest,pin,pinned_json,utc,write
from repository_records import RepositoryError


def _composite_capture_protocol(h,base):
    class CompositeCaptureProtocol(base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            if self.native_context.phase=='RESTORE':
                self.storage_running=h.engine.inspect(self.config_services['minio']['id'])['State']['Running']
                self.running_applications={role for role in ('backend','frontend')
                    if h.engine.inspect(self.config_services[role]['id'])['State']['Running']}

        def docker(self,args,**kwargs):
            if args[:1] in (['start'],['stop']):
                identity=args[-1];state=json.loads(h.state_path.read_bytes())
                if identity not in state['containers']:
                    assert self.native_context.phase=='RESTORE'
                    assert identity in {self.config_services[role]['id'] for role in ('backend','frontend')}
                    row=h.engine.inspect(identity)
                    assert row['Id']==identity
                    state['containers'][identity]=dict(running=row['State']['Running'],image=row['Image'],
                        mounts=row['Mounts'],ports=row['HostConfig']['PortBindings'],
                        networks=row['NetworkSettings']['Networks'])
                    h.state_path.write_bytes(canonical(state))
            return super().docker(args,**kwargs)
    return CompositeCaptureProtocol


def _emit_protocol_diagnostics(h):
    # Only fixed outputs and the real last invocation are exported. This runs
    # before the carrier removes tmpfs and never polls/reaps a process itself.
    files={}
    def keep(path):
        path=Path(path)
        if path.is_file():
            raw=path.read_bytes()
            assert len(raw)<=16*1024*1024
            files[str(path)]=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                rawBase64=base64.b64encode(raw).decode('ascii'))
    keep(h.output);keep(h.state_path)
    if h.output.is_file():
        data=json.loads(h.output.read_bytes()).get('data',{})
        for name in ('replacementReceiptPin','targetPreservationPin'):
            if type(data.get(name)) is dict:keep(data[name]['path'])
    natives=[]
    for native in h.natives:
        context=native.native_context._context
        last=deepcopy(context._invocations[-1]) if context._invocations else None
        if last is not None:
            for name in ('intentPinAtDispatch','terminalPin'):
                if type(last.get(name)) is dict:keep(last[name]['path'])
        natives.append(dict(phase=native.native_context.phase,closed=context._closed,
            invocationCount=len(context._invocations),lastInvocation=last))
    value=dict(schemaVersion='TargetPreservationProtocolDiagnostics/v1',actualBusinessRestore=False,
        producerTrace=getattr(h,'producer_trace',None),natives=natives,
        processes=[dict(pid=row['process'].pid,returncode=row['process'].returncode,
            phase=row['phase']) for row in h.processes],rawFiles=list(files.values()))
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode('utf-8')
    print('\nLOCAL_PROTOCOL_DIAGNOSTICS_BASE64='+base64.b64encode(raw).decode('ascii'),flush=True)


@pytest.fixture
def preservation_producer_case(handoff_case,monkeypatch,capsys):
    # Reuse the actual NativeData.command/formal importer harness. Its finite
    # SQL/Docker replies are the same declared protocol boundary; all command,
    # SQL staging/cleanup, capture exporters, ctx and worker files are real.
    h=handoff_case
    # This full-chain protocol runs every native call in an actual child as
    # well as every real capture exporter. r5 measured capture107s+copy56s;
    # retain an explicit480s capture/publication budget inside the unchanged
    # owner600s deadline. New roots/pins/reservation preserve all old originals.
    operations=h.case['root']/'producer-preservation-operations';operations.mkdir(mode=0o700)
    h.root=operations/'restore-1';h.root.mkdir(mode=0o700)
    host=h.case['root']/'producer-preservation-host';host.mkdir(mode=0o700)
    import recovery_resource_admission as admission
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.owner['operationsRoot']=str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin']=write(h.case['root']/'producer-preservation-target.json',h.owner['targets']['target57'])
    h.capture_config['limits']['workSeconds']=480
    h.capture_config['limits']['dataSeconds']=180
    h.case['base_pin']=write(h.case['root']/'producer-preservation-capture.json',h.capture_config)
    h.case['policy']['captureConfigurationPins']={'source57':h.case['base_pin']}
    h.owner['targetProgramPolicies']['target57']=deepcopy(h.case['policy'])
    policy=pinned_json(h.preservation_policy)
    repository=pinned_json(policy['repositoryConfigurationPin'])
    readback=pinned_json(repository['readbackConfigPin'])
    readback['recordRoot']=str(h.root/'target-preservation'/'publication')
    repository['readbackConfigPin']=write(h.case['root']/'producer-preservation-readback.json',readback)
    policy.update(captureConfigurationPin=h.case['base_pin'],maxPreservationSeconds=480,
        repositoryConfigurationPin=write(h.case['root']/'producer-preservation-repository.json',repository))
    h.preservation_policy=write(h.case['root']/'producer-preservation-policy.json',policy)
    h.owner['targetPreservationPolicies']={'target57':h.preservation_policy}
    freeze_inputs(h)
    capture_type=_composite_capture_protocol(h,h.native_type)
    h.native_type=capture_type
    h=actual_process_protocol.__wrapped__(h,monkeypatch)
    process_type=h.native_type
    class PreservationProcessProtocol(process_type):
        def __init__(self,*args,**kwargs):
            # The old harness's same-directory assertion is for its source-only
            # loader. MAIN capture deliberately already loaded strict Data.
            # Keep that actual module; validate each exact origin instead.
            capture_type.__init__(self,*args,**kwargs)
            self.policy['maxExpandedBytes']=1024*1024
            formal=(Path(runtime.__file__).resolve().parent.parent/'formal'
                if Path(runtime.__file__).resolve().parent.name=='common'
                else Path(runtime.__file__).resolve().parents[1]/'backup_engine'/'formal')
            strict=Path(runtime.__file__).resolve().parent
            self.modules=runtime.modules_from(str(formal))
            for name,module in self.modules.items():
                expected=(strict if (strict/(name+'.py')).is_file() else formal)/(name+'.py')
                assert Path(module.__file__).resolve()==expected
                print('ACTUAL_RESTORE_COMPONENT='+str(expected)+' SHA256='+
                    hashlib.sha256(expected.read_bytes()).hexdigest(),flush=True)
            native=self
            class LocalSqlTransport:
                _password=Path(native.config['secrets']['mysql']['MYSQL_ROOT_PASSWORD']['path']).read_text(encoding='utf-8')
                def query(self,statement,*,mutation=False):
                    return native.query(statement,mutation=mutation).decode('utf-8').strip()
                def _command(self,_program,_arguments):
                    destination=native.root/'received-sql.protocol.bin'
                    h.sql_received.append(destination)
                    return ['sh','-ec',shlex.join([sys.executable,'-B','-c',SQL_CONSUMER,str(destination)])]
            self.mysql=LocalSqlTransport()
    h.native_type=PreservationProcessProtocol
    monkeypatch.setattr(runtime,'MinimalData',PreservationProcessProtocol)
    # The original harness observes a short restore chain by snapshotting the
    # whole ledger at every Popen. Capture adds hundreds of real invocations;
    # copying that growing ledger belongs to the fixture, not the product's
    # five-second protected observation. Inspect the same real last intent
    # directly, retaining every admission/argv assertion and actual process.
    def observed_popen(argv,**kwargs):
        assert argv[0] in (sys.executable,'sh')
        native=h.current_dispatch[0] if h.current_dispatch is not None else h.natives[-1]
        pending=native.native_context._context._invocations[-1]
        assert pending['terminalPin'] is None
        assert pending['intentObservation']['argvSha256']==digest(argv)
        process=subprocess.Popen(argv,**kwargs)
        h.processes.append(dict(process=process,argv=deepcopy(argv),phase=native.native_context.phase,
            intent=deepcopy(pending['intentObservation']),intentPin=deepcopy(pending['intentPinAtDispatch'])))
        return process
    import recovery_data as native_data
    monkeypatch.setattr(native_data,'subprocess',SimpleNamespace(Popen=observed_popen,
        PIPE=subprocess.PIPE,DEVNULL=subprocess.DEVNULL,TimeoutExpired=subprocess.TimeoutExpired))
    execute_empty=runtime.execute_empty
    def recorded(*args,**kwargs):
        h.original_execute_calls.append((args,kwargs))
        return execute_empty(*args,**kwargs)
    monkeypatch.setattr(runtime,'execute_empty',recorded)
    # Keep the real worker's public failure schema unchanged. The local test
    # carrier needs the actual producer traceback when that worker deliberately
    # reduces a structural error to RESTORE_KEYERROR; no success is synthesized.
    import recovery_program_restore as producer
    original_producer=producer.execute
    def traced(*args,**kwargs):
        try:return original_producer(*args,**kwargs)
        except BaseException:
            h.producer_trace=traceback.format_exc()
            traceback.print_exc()
            raise
    monkeypatch.setattr(producer,'execute',traced)
    try:yield h
    finally:
        with capsys.disabled():_emit_protocol_diagnostics(h)


def test_offline_preservation_rejects_unbound_scope_before_reading_payload(tmp_path):
    # Pure malformed-input unit. Actual archive/native proof is exercised by
    # the complete producer test below; this case must never grant authority.
    validator=importlib.import_module('recovery_target_preservation')
    unknown=dict(path=str(tmp_path/'unbound.json'),bytes=1,sha256='a'*64)
    with pytest.raises(RepositoryError,match='PRESERVATION_EVIDENCE_INVALID'):
        validator.validate_preservation_evidence({}, {}, unknown,binding_pin=unknown)


def test_created_app_external_protocol_keeps_real_engine_and_capture_state_aligned(capture_protocol):
    # Only the existing external Docker protocol adapter is exercised here.
    # No ctx, native ledger, producer, capture or restored database is claimed.
    h=capture_protocol
    target=deepcopy(h.owner['targets']['target57'])
    service=next(row for row in target['services'] if row['role']=='backend')
    before=h.engine.inspect(service['id']);body=deepcopy(before['Config'])
    body.update(Image=before['Image'],HostConfig=deepcopy(before['HostConfig']),
        NetworkingConfig={'EndpointsConfig':deepcopy(before['NetworkSettings']['Networks'])})
    created=h.engine.request('POST','/containers/create?name=program-backend',body)
    identity=created['Id'];assert identity=='8'*64
    assert identity not in json.loads(h.state_path.read_bytes())['containers']
    service['id']=identity
    protocol=_composite_capture_protocol(h,h.native_type)
    native=protocol.__new__(protocol)
    native.config=target;native.config_services={row['role']:row for row in target['services']}
    native.native_context=SimpleNamespace(phase='RESTORE')
    native.running_applications=set();native.storage_running=False
    native._invoke=lambda _kind,_arguments,callback,_mutation:callback()
    native.docker(['start',identity],mutation=True)
    state=json.loads(h.state_path.read_bytes())
    assert h.engine.inspect(identity)['State']['Running'] is True
    assert state['containers'][identity]['running'] is True
    assert state['actions'][-1]==['start',identity]
    assert not h.natives and not h.original_execute_calls


def test_main_producer_preserves_before_import_then_restores_and_validates_history(preservation_producer_case):
    h=preservation_producer_case
    code=worker.main(['--configuration',h.owner_pin['path'],'--request',h.request_pin['path'],
        '--output',str(h.output)])
    result=pinned_json(pin(h.output))
    assert code==0,(result['failureCode'],result['data'])
    assert result['state']=='SUCCEEDED' and result['actualExitCode']==0
    data=result['data'];native=h.natives[-1]
    final=data['targetPreservationPin']
    receipt=pinned_json(data['replacementReceiptPin'])
    assert receipt['targetPreservationPin']==final and receipt['state']=='SUCCEEDED'
    value=pinned_json(final)
    assert value['schemaVersion']=='MainTargetPreservation/v1' and value['state']=='SUCCEEDED'
    assert h.handoff_dispatches==1
    assert all(row['terminalPin'] is not None for row in
        pinned_json(data['programNativeEvidencePin'])['invocations'])
    assert native.native_context.phase=='RESTORE'
    ctx=native.native_context._context
    assert ctx._target_preservation._closed and ctx._target_preservation._repository_lock.stream.closed
    assert Path(value['holdPin']['path']).exists()
    assert h.original_execute_calls and 'target_preservation' in h.original_execute_calls[0][1]
    # This is offline strict evidence validation after ctx/transport leases
    # close, not a synthetic live proof or a caller-provided success envelope.
    validator=importlib.import_module('recovery_target_preservation')
    report=validator.validate_preservation_evidence(h.owner,h.request,final,
        binding_pin=pinned_json(data['programNativeEvidencePin'])['bindingPin'])
    assert report['payloadContentVerified'] is True and report['targetPreservationPin']==final
    full=historical.validate_program_evidence(h.owner,h.request,h.root,result_pin=pin(h.output))
    assert full['targetPreservationPin']==final and not full['terminalUnknown']
    archive=pinned_json(value['archiveProofPin']);point=pinned_json(archive['pointPin'])
    payload=Path(point['payloadRefs'][0]['path']);payload.write_bytes(b'drift')
    with pytest.raises((RecoveryError,RepositoryError)) as caught:
        validator.validate_preservation_evidence(h.owner,h.request,final,
            binding_pin=pinned_json(data['programNativeEvidencePin'])['bindingPin'])
    assert 'PRESERVATION_' in str(caught.value)


def test_main_handoff_unknown_retains_archive_and_never_imports_or_clears(preservation_producer_case):
    h=preservation_producer_case;query=h.transport.query
    def unavailable(native,sql,*,mutation=False):
        if sql=='SET GLOBAL super_read_only=OFF; SET GLOBAL read_only=OFF;':
            # Explicit external SQL-protocol uncertainty, not a claim that a
            # real database or an unobserved subprocess accepted the write.
            raise RecoveryError('PROTOCOL_HANDOFF_UNKNOWN',unknown=True)
        return query(native,sql,mutation=mutation)
    h.transport.query=unavailable
    code=worker.main(['--configuration',h.owner_pin['path'],'--request',h.request_pin['path'],'--output',str(h.output)])
    result=pinned_json(pin(h.output));data=result['data'];receipt=pinned_json(data['replacementReceiptPin'])
    assert code==2 and result['state']=='TERMINAL_UNKNOWN' and result['failureCode']=='PROTOCOL_HANDOFF_UNKNOWN'
    assert data['terminalUnknown'] is receipt['terminalUnknown'] is True
    assert data['targetPreservationPin'] is receipt['targetPreservationPin'] is None
    assert not h.sql_received and not h.original_execute_calls and not h.transport.releases
    ctx=h.natives[0].native_context._context;publication=ctx._target_preservation
    assert publication._proof and publication.session._state=='FAILED_RETAINED'
    assert publication._closed and publication._repository_lock.stream.closed
    assert Path(publication._proof['path']).exists() and Path(publication.hold_intent['path']).exists()
    assert not (h.claim/'program-import'/'load-intent.json').exists()
    assert historical.validate_program_evidence(h.owner,h.request,h.root,result_pin=pin(h.output))['terminalUnknown']


def test_main_stage_failure_keeps_final_preservation_without_clear(preservation_producer_case,monkeypatch):
    from recovery_program_native import MainNativeExecutionContext
    h=preservation_producer_case;original=MainNativeExecutionContext.stage
    def unavailable(context,generation_pin):
        lease=context._lease_and_resolve
        def reject(expected,evidence,*,generation=None,runtime=False):
            if generation is not None:raise RecoveryError('PROTOCOL_PRESERVATION_STAGE_FAILURE')
            return lease(expected,evidence,generation=generation,runtime=runtime)
        with monkeypatch.context() as boundary:
            boundary.setattr(context,'_lease_and_resolve',reject)
            return original(context,generation_pin)
    monkeypatch.setattr(MainNativeExecutionContext,'stage',unavailable)
    code=worker.main(['--configuration',h.owner_pin['path'],'--request',h.request_pin['path'],'--output',str(h.output)])
    result=pinned_json(pin(h.output));data=result['data'];receipt=pinned_json(data['replacementReceiptPin'])
    assert code==1 and result['failureCode']=='PROTOCOL_PRESERVATION_STAGE_FAILURE'
    assert data['programExecutionPhase']=='PREPARATION' and data['programGenerationPin'] is not None
    assert data['targetPreservationPin']==receipt['targetPreservationPin'] is not None
    assert not h.sql_received and not h.original_execute_calls and not h.transport.releases
    ctx=h.natives[0].native_context._context
    assert ctx._target_preservation._closed and ctx._target_preservation._repository_lock.stream.closed
    proof=historical.validate_program_evidence(h.owner,h.request,h.root,result_pin=pin(h.output))
    assert proof['targetPreservationPin']==data['targetPreservationPin'] and not proof['terminalUnknown']


def test_main_ready_unknown_preserves_success_receipt_and_final_proof(preservation_producer_case,monkeypatch):
    import recovery_backup_epoch as epoch
    h=preservation_producer_case;complete=epoch.complete_restore;fixed={}
    def unavailable(*args,**kwargs):
        if args[3]=='READY':
            receipt=pinned_json(args[4])
            assert receipt['state']=='SUCCEEDED' and receipt['terminalUnknown'] is False
            for reference in (args[4],receipt['programNativeEvidencePin'],receipt['programProtectionCustodyPin'],
                    receipt['targetPreservationPin']):
                fixed[Path(reference['path'])]=Path(reference['path']).read_bytes()
            raise RecoveryError('PROTOCOL_PRESERVATION_READY_UNKNOWN',unknown=True)
        return complete(*args,**kwargs)
    monkeypatch.setattr(epoch,'complete_restore',unavailable)
    code=worker.main(['--configuration',h.owner_pin['path'],'--request',h.request_pin['path'],'--output',str(h.output)])
    result=pinned_json(pin(h.output));data=result['data'];receipt=pinned_json(data['replacementReceiptPin'])
    assert code==2 and result['state']=='TERMINAL_UNKNOWN'
    assert receipt['state']=='SUCCEEDED' and receipt['terminalUnknown'] is False and data['terminalUnknown'] is True
    assert data['targetPreservationPin']==receipt['targetPreservationPin'] is not None
    assert fixed and all(path.read_bytes()==raw for path,raw in fixed.items())
    assert epoch.read_current(h.case['epoch'])['state']=='REPLACING'
    assert h.sql_received and not (h.root/'resource-release.json').exists()
    ctx=h.natives[-1].native_context._context
    assert ctx._target_preservation._closed and ctx._target_preservation._repository_lock.stream.closed
    proof=historical.validate_program_evidence(h.owner,h.request,h.root,result_pin=pin(h.output))
    assert proof['targetPreservationPin']==data['targetPreservationPin'] and proof['terminalUnknown']
    assert all(path.read_bytes()==raw for path,raw in fixed.items())
