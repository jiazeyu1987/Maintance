"""Local filesystem/protocol tests, never a real Spug publication claim."""
from copy import deepcopy
import hashlib
import base64
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

import main_program_spug_publication as legacy


def module():
    return importlib.import_module('main_program_spug_publication_continuation')


def mounts():
    return [dict(Type='bind',Source='C:/Spug/runtime/private',Destination='/run/intruoyi-spug',RW=False,Name=None),
        dict(Type='bind',Source=legacy.RUNTIME,Destination='/opt/intruoyi-spug',RW=False,Name=None),
        dict(Type='volume',Source='/var/lib/docker/volumes/exact/_data',Destination='/var/lib/intruoyi-spug',
             RW=True,Name='exact')]


def writes():
    paths=['/run/intruoyi-spug/new-'+str(i)+'.json' for i in range(4)]
    paths += [legacy.SETTINGS[k] for k in ('simple','entry','bridge')]
    return [dict(path=p,expected=None if i<4 else dict(path=p,bytes=3,sha256=hashlib.sha256(b'old').hexdigest()),
                 value={'index':i}) for i,p in enumerate(paths)]


def test_original_order_routes_two_storage_classes_without_any_transport():
    result=module().classify_writes(writes(),mounts())
    assert [r['index'] for r in result]==list(range(7))
    assert [r['executor'] for r in result]==['HOST_BIND']*4+['CONTAINER_VOLUME']*2+['HOST_BIND']
    assert result[-1]['hostPath']=='C:/Spug/runtime/private/smallapp-bridge.private.json'
    assert all(r['hostPath'] is None for r in result[4:6])


@pytest.mark.parametrize('change',['rw','source','volume-ro','volume-type','shadow','duplicate','escape','unknown','order','case'])
def test_mount_and_path_ambiguity_refuses_before_write(change):
    ms,ws=mounts(),writes()
    if change=='rw':ms[0]['RW']=True
    elif change=='source':ms[0]['Source']='C:/other'
    elif change=='volume-ro':ms[2]['RW']=False
    elif change=='volume-type':ms[2]['Type']='bind'
    elif change=='shadow':ms.append(dict(ms[0],Destination='/run/intruoyi-spug/new-0.json'))
    elif change=='duplicate':ms.append(deepcopy(ms[0]))
    elif change=='escape':ws[0]['path']='/run/intruoyi-spug/../private.json'
    elif change=='unknown':ws[4]['path']='/var/lib/intruoyi-spug/extra.json'
    elif change=='order':ws[4],ws[6]=ws[6],ws[4]
    else:ws[1]['path']=ws[0]['path'].upper()
    with pytest.raises(ValueError,match='MAIN_SPUG_'):module().classify_writes(ws,ms)


def files(tmp_path, absent=False):
    active=tmp_path/'active.json';archive=tmp_path/'before.json';staged=tmp_path/'pending.json'
    if absent:return active,archive,staged,None,None
    original=b'{ "private": "original bytes" }\r\n'
    active.write_bytes(original);archive.write_bytes(original)
    return active,archive,staged,legacy.file_pin(active),legacy.file_pin(archive)


def test_real_atomic_transition_preserves_original_and_fsyncs(tmp_path,monkeypatch):
    subject=module();active,archive,staged,expected,custody=files(tmp_path)
    before=archive.read_bytes();calls=[];original_fsync=os.fsync
    def fsync(fd):
        calls.append(fd);return original_fsync(fd)
    monkeypatch.setattr(subject.os,'fsync',fsync)
    result=subject.replace_after_custody(active,staged,expected,b'{"new":true}',custody)
    assert active.read_bytes()==b'{"new":true}' and archive.read_bytes()==before and not staged.exists()
    assert calls and result['fileFsyncCompleted'] is True and result['atomicMoveCompleted'] is True
    assert result['powerLossDurabilityVerified'] is False
    assert result['installedPin']==legacy.file_pin(active)


@pytest.mark.parametrize('change',['custody-drift','active-drift','missing-custody','pending','hardlink'])
def test_real_files_refuse_unpreserved_or_ambiguous_transition(tmp_path,change):
    subject=module();active,archive,staged,expected,custody=files(tmp_path)
    if change=='custody-drift':archive.write_bytes(b'changed')
    elif change=='active-drift':active.write_bytes(b'changed')
    elif change=='missing-custody':custody=None
    elif change=='pending':staged.write_bytes(b'earlier attempt')
    else:os.link(active,tmp_path/'alias.json')
    before=active.read_bytes()
    with pytest.raises((ValueError,OSError)):subject.replace_after_custody(active,staged,expected,b'new',custody)
    assert active.read_bytes()==before


def test_new_file_no_clobber_refuses_last_moment_competing_writer(tmp_path,monkeypatch):
    subject=module();active,archive,staged,expected,custody=files(tmp_path,True)
    original=subject.atomic_move
    def raced(source,target,*,replace):
        Path(target).write_bytes(b'other writer')
        return original(source,target,replace=replace)
    monkeypatch.setattr(subject,'atomic_move',raced)
    with pytest.raises((ValueError,OSError)):subject.replace_after_custody(active,staged,None,b'ours',None)
    assert active.read_bytes()==b'other writer'


def test_actual_replace_then_readback_exception_does_not_rollback_or_retry(tmp_path,monkeypatch):
    subject=module();active,archive,staged,expected,custody=files(tmp_path)
    old=archive.read_bytes();original=subject.atomic_move;calls=[]
    def replaced_then_failed(source,target,*,replace):
        calls.append(str(target));original(source,target,replace=replace)
        raise OSError('real replacement completed; result unavailable')
    monkeypatch.setattr(subject,'atomic_move',replaced_then_failed)
    with pytest.raises(OSError):subject.replace_after_custody(active,staged,expected,b'new',custody)
    assert active.read_bytes()==b'new' and archive.read_bytes()==old and calls==[str(active)]


def test_default_parser_cannot_apply_implicitly():
    result=module().parser().parse_args(['--inputs','explicit.json'])
    assert result.apply is False


def test_missing_input_never_constructs_or_calls_transport(tmp_path):
    calls=[]
    with pytest.raises((ValueError,OSError)):
        module().run_request(tmp_path,tmp_path,'missing.json',apply=True,transport=lambda *args:calls.append(args))
    assert calls==[] and not list(tmp_path.iterdir())


@pytest.fixture(scope='module')
def original_failure():
    """Read-only real failed records, never a fixture success or a dispatch."""
    task,private=legacy.TASK,legacy.PRIVATE
    name='main-program-spug-publication-inputs-45dd7dc-r6.json'
    raw=(task/name).read_bytes();inputs=json.loads(raw)
    input_pin=dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    stem='main-program-spug-installation-45dd7dc-r6'
    failure=json.loads((private/(stem+'.private.json')).read_bytes())
    attempt=json.loads((private/(stem+'.attempt.private.json')).read_bytes())
    stages=[json.loads(Path(r['resultPin']['path']).read_bytes()) for r in failure['stages']]
    return inputs,input_pin,failure,attempt,stages


def test_actual_original_seven_pass_and_one_failed_remain_failed(original_failure):
    before=deepcopy(original_failure)
    result=module().validate_failure_records(*original_failure)
    assert result['successfulStages']==legacy.publication_schedule()[:7]
    assert result['failedStage']=='spug-publish' and result['hostWriteCounts']==[6,3,3]
    assert original_failure==before and original_failure[2]['status']=='FAILED'


@pytest.mark.parametrize('change',['missing','order','unknown','partial','failed-host','binding','attempt','revision'])
def test_original_failure_is_not_a_generic_resume_permission(original_failure,change):
    values=deepcopy(original_failure);inputs,pin,failure,attempt,stages=values
    if change=='missing':stages.pop()
    elif change=='order':stages[0],stages[1]=stages[1],stages[0]
    elif change=='unknown':stages[-1]['result']['status']='UNKNOWN'
    elif change=='partial':stages[-1]['result']['completedWrites']=['/run/intruoyi-spug/changed.json']
    elif change=='failed-host':stages[4]['result']['status']='FAILED'
    elif change=='binding':stages[0]['controlGenerationPin']={'file':'other.json'}
    elif change=='attempt':attempt['retryPermitted']=True
    else:inputs['revisionId']='r7'
    with pytest.raises(ValueError,match='MAIN_SPUG_'):module().validate_failure_records(*values)


def test_real_mount_evidence_requires_original_stdout_not_boolean_claims(original_failure):
    inputs,pin,failure,*_=original_failure
    reference=legacy.contract.Records(legacy.TASK)
    name='spug-continuation-mount-observation-r2.json'
    raw=(legacy.TASK/name).read_bytes()
    local=dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    obs=legacy.read_document(Path(inputs['publicationObservationPin']['path']))['spug']
    result=module().load_mount_observation(reference,legacy.PRIVATE,local,pin,
        legacy.file_pin(legacy.PRIVATE/'main-program-spug-installation-45dd7dc-r6.private.json'),obs)
    assert result['value']['originalRunnerAbsent'] is True
    assert result['value']['entryIdentity']['pid']==151768
    assert result['pins'] and all(legacy.file_pin(p['path'])==p for p in result['pins'])


def test_complete_custody_is_a_barrier_before_any_real_file_changes(tmp_path):
    subject=module();active,archive,staged,expected,custody=files(tmp_path)
    calls=[]
    rows=[dict(index=0,expected=expected,custody=custody),dict(index=1,expected=expected,custody=None)]
    with pytest.raises(ValueError,match='MAIN_SPUG_'):
        subject.check_custody_barrier(rows,2)
        calls.append(subject.replace_after_custody(active,staged,expected,b'changed',custody))
    assert calls==[] and active.read_bytes()==archive.read_bytes()


def test_historical_source_mapping_reads_archived_bytes_without_rebinding_old_pin(tmp_path):
    task=tmp_path/'task';private=tmp_path/'private';task.mkdir();private.mkdir()
    source=task/'main_program_spug_publication.py';source.write_bytes(b'old implementation')
    old=legacy.file_pin(source);saved=private/'preserved.py';saved.write_bytes(source.read_bytes())
    source.write_bytes(b'new implementation')
    value=dict(schemaVersion='MainProgramSpugPublicationSourceCustody/v1',
        originalAttemptPin={'path':str(private/'attempt.json'),'bytes':1,'sha256':'a'*64},
        entries=[dict(originalPin=old,preservedPin=legacy.file_pin(saved))])
    result=module().validate_source_custody(value,value['originalAttemptPin'],[old],task,private)
    assert result==[legacy.file_pin(saved)] and value['entries'][0]['originalPin']==old


@pytest.mark.parametrize('change',['unrelated','publisher','wrong-bytes','missing','duplicate'])
def test_historical_source_mapping_is_exact_and_not_an_input_skip(tmp_path,change):
    task=tmp_path/'task';private=tmp_path/'private';task.mkdir();private.mkdir()
    source=task/('main_program_spug_publication_v2.py' if change=='publisher' else 'main_program_spug_publication.py')
    source.write_bytes(b'old');old=legacy.file_pin(source)
    saved=private/'preserved.py';saved.write_bytes(b'bad' if change=='wrong-bytes' else b'old')
    source.write_bytes(b'new')
    attempt_pin=dict(path=str(private/'attempt'),bytes=1,sha256='a'*64)
    rows=[dict(originalPin=old,preservedPin=legacy.file_pin(saved))]
    if change=='missing':rows=[]
    if change=='duplicate':rows=rows*2
    value=dict(schemaVersion='MainProgramSpugPublicationSourceCustody/v1',originalAttemptPin=attempt_pin,entries=rows)
    with pytest.raises(ValueError,match='MAIN_SPUG_'):
        module().validate_source_custody(value,attempt_pin,[] if change=='unrelated' else [old],task,private)


def test_shared_deep_verify_refuses_boolean_only_native_success():
    controls=[dict(service='fixture-source.service')]
    bundle=dict(controllersByHost={'57':controls},targets={'57':'fixture-target'})
    result=dict(host='172.30.30.57',controllers=controls,selectorCount=6,
        **{k:True for k in ('selectorsReadBack','actualNativeSelectionsVerified','oldFilesPreserved',
             'businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')})
    with pytest.raises(ValueError,match='V2_NATIVE_CONTROL_SET_CHANGED'):
        legacy.validate_verify_stage({},bundle,'57',result)


def batch_fixture(tmp_path):
    rows=[];custody=[];locations=[]
    for i in range(3):
        folder=tmp_path/str(i);folder.mkdir()
        active,archive,staged,expected,kept=files(folder)
        rows.append(dict(path='/fixture/'+str(i),expected=expected,value={'new':i}))
        custody.append(dict(index=i,expected=expected,custody=kept))
        locations.append((active,staged,expected,kept))
    return rows,custody,locations


def test_real_batch_stops_after_receipt_failure_without_hiding_written_bytes(tmp_path):
    subject=module();rows,custody,locations=batch_fixture(tmp_path);calls=[];states=[]
    def install(index):
        active,staged,expected,kept=locations[index];calls.append(index)
        return subject.replace_after_custody(active,staged,expected,legacy.canonical(rows[index]['value']),kept)
    def readback(index):
        p=legacy.file_pin(locations[index][0]);return dict(p,path=rows[index]['path'])
    def record(index,state):
        if index==0 and state['state']=='APPLIED':raise OSError('receipt disk full')
    with pytest.raises(OSError):subject.execute_write_batch(rows,custody,states,install,readback,record)
    assert calls==[0] and locations[0][0].read_bytes()==legacy.canonical(rows[0]['value'])
    assert locations[1][0].read_bytes()==Path(custody[1]['custody']['path']).read_bytes()
    assert states[0]['state']=='APPLIED' and [r['state'] for r in states[1:]]==['NOT_STARTED']*2


def test_real_batch_checks_last_custody_before_first_install(tmp_path):
    subject=module();rows,custody,locations=batch_fixture(tmp_path);calls=[];states=[]
    Path(custody[-1]['custody']['path']).write_bytes(b'changed')
    with pytest.raises(ValueError):
        subject.execute_write_batch(rows,custody,states,lambda i:calls.append(i),lambda i:None,lambda *args:None)
    assert calls==[] and all(active.read_bytes()!=b'changed' for active,*_ in locations)


def test_real_explicit_c1_preparation_is_local_and_consumes_original_failed_chain():
    subject=module()
    prepared=subject.prepare_continuation(legacy.TASK,legacy.PRIVATE,
        'main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')
    assert prepared['inputs']['revisionId']=='r6' and prepared['originalFailure']['status']=='FAILED'
    assert [r['executor'] for r in prepared['routes']]==['HOST_BIND']*4+['CONTAINER_VOLUME']*2+['HOST_BIND']
    assert prepared['originalSpec']['hostSpecs']['57']['auditPath'].endswith('-r6')
    assert prepared['originalSpec']['spugSpec']['auditPath'].endswith('-r6-continuation-c1')
    assert all(legacy.file_pin(pin['path'])==pin for pin in prepared['inputPins'])


@pytest.mark.parametrize('code,exit_code',[('import json;print(json.dumps({"status":"PASS"}));raise SystemExit(7)',7),
    ('print("not json")',0)])
def test_real_native_exit_and_payload_errors_are_preserved(tmp_path,code,exit_code):
    subject=module();prepared=dict(inputs=dict(outputFile='fixture-continuation.json'))
    transport=subject.ActualContinuationTransport(tmp_path,prepared)
    with pytest.raises((ValueError,json.JSONDecodeError)):
        transport.command('fixture',[sys.executable,'-B','-c',code])
    assert len(transport.receipts)==1
    receipt=json.loads(Path(transport.receipts[0]['path']).read_bytes())
    assert receipt['actualExitCode']==exit_code and receipt['errorType']
    assert Path(receipt['stdoutPin']['path']).read_bytes()


def test_real_native_timeout_is_unknown_and_not_retried(tmp_path):
    subject=module();transport=subject.ActualContinuationTransport(tmp_path,dict(inputs=dict(outputFile='fixture.json')))
    import subprocess
    with pytest.raises(subprocess.TimeoutExpired):
        transport.command('fixture',[sys.executable,'-B','-c','import time;time.sleep(20)'],timeout=.1)
    receipt=json.loads(Path(transport.receipts[0]['path']).read_bytes())
    assert receipt['status']=='UNKNOWN' and receipt['actualExitCode'] is None and transport.counter==1


def test_all_generated_continuation_programs_compile_and_old_programs_are_unchanged():
    subject=module();prepared=subject.prepare_continuation(legacy.TASK,legacy.PRIVATE,
        'main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')
    for phase,index in [('custody',None),('write',4),('write',5),*[("readback",i) for i in range(7)]]:
        compile(subject.container_program(prepared,phase,index),'local-compile-only','exec')
    # Actual prepare already compared all eight original generated programs byte
    # for byte. This fixture does not execute an installed or remote program.
    assert subject.original.__file__.endswith('main_program_spug_publication_v2.py')


def test_same_failed_attempt_cannot_start_again_under_another_continuation_id(tmp_path):
    subject=module();private=tmp_path/'private';private.mkdir();task=tmp_path/'task';task.mkdir()
    inputs=dict(outputFile='fixture.json',sourceCommit='a'*40,revisionId='r6',continuationId='c2',
        controlGenerationPin={},spugResourceBuildPin={},originalFailurePin=dict(sha256='b'*64))
    gate=private/('spug-publication-container-'+legacy.CONTAINER+'.gate.private.json');gate.write_bytes(b'unknown original')
    prepared=dict(inputs=inputs,inputPin={},inputPins=[])
    with pytest.raises(ValueError,match='ALREADY_CLAIMED'):
        subject.execute_prepared(task,private,prepared,transport=object())
    assert gate.read_bytes()==b'unknown original' and not list(task.iterdir())


def test_custody_result_cannot_be_promoted_without_actual_container_originals(tmp_path):
    subject=module();rows,custody,_=batch_fixture(tmp_path)
    prepared=dict(originalSpec=dict(spugSpec=dict(writes=rows,auditPath='/fixture/audit')))
    with pytest.raises(ValueError,match='CONTINUATION_CONTAINER_CUSTODY'):
        subject.validate_container_custody(prepared,custody,{'status':'PASS','rows':[]})


@pytest.mark.parametrize('wrong_archive',[False,True])
def test_actual_host_custody_method_decodes_and_preserves_all_original_bytes(tmp_path,monkeypatch,wrong_archive):
    subject=module();ws=writes();prepared=dict(inputs=dict(outputFile='fixture.json',sourceCommit='a'*40,
        revisionId='r6',continuationId='c1'),originalSpec=dict(spugSpec=dict(writes=ws,auditPath='/audit')),
        originalAuditPath='/old-audit',mountObservation=dict(entryIdentity={}))
    rows=[]
    for i,row in enumerate(ws):
        expected=row['expected'];archive=None if expected is None else dict(expected,path='/audit/before-'+str(i)+'.private.json')
        rows.append(dict(index=i,path=row['path'],expected=expected,archivePin=archive,
            rawBase64=None if expected is None else base64.b64encode(b'old').decode('ascii')))
    transport=subject.ActualContinuationTransport(tmp_path,prepared)
    monkeypatch.setattr(transport,'container',lambda label,program:dict(status='PASS',rows=rows))
    if wrong_archive:
        rows[-1]['archivePin']['path']='/other/before-6.private.json'
        with pytest.raises(ValueError,match='CONTAINER_CUSTODY'):transport.prepare_custody()
        return
    result=transport.prepare_custody()
    assert len(result)==7 and len(list(tmp_path.iterdir()))==3
    assert [Path(r['custody']['path']).read_bytes() for r in result if r['custody']]==[b'old']*3


def test_entry_drift_is_rejected_before_host_bind_file_change(tmp_path,monkeypatch):
    subject=module();active,archive,staged,expected,kept=files(tmp_path)
    prepared=dict(inputs=dict(outputFile='fixture.json',sourceCommit='a'*40,revisionId='r6',continuationId='c1'),
        inputPins=[],routes=[dict(executor='HOST_BIND',hostPath=str(active))],
        originalSpec=dict(spugSpec=dict(writes=[dict(path='/run/intruoyi-spug/file.json',expected=expected,value={'new':True})],
            auditPath='/audit')),originalAuditPath='/old-audit',mountObservation=dict(entryIdentity={}))
    transport=subject.ActualContinuationTransport(tmp_path,prepared);calls=[]
    monkeypatch.setattr(transport,'inspect_current',lambda:None)
    def drift(label,program):calls.append(label);raise ValueError('MAIN_SPUG_CONTINUATION_ENTRY_CHANGED')
    monkeypatch.setattr(transport,'container',drift)
    with pytest.raises(ValueError,match='ENTRY_CHANGED'):transport.install(0,[dict(custody=kept)])
    assert active.read_bytes()==archive.read_bytes() and calls==['guard-0']


@pytest.mark.parametrize('change',['other-container','missing-readback','other-program'])
def test_native_file_binding_refuses_missing_or_unrelated_real_command(change,tmp_path):
    subject=module()
    prepared=dict(inputs=dict(originalFailurePin=dict(sha256='a'*64)),mountObservation=dict(protectedContainerId='b'*64))
    if change=='other-container':
        value=dict(label='readback-0');request=dict(argv=[legacy.DOCKER,'exec','-i','c'*64,'python3','-B','-',
            'spug-continuation-'+'a'*24])
        with pytest.raises(ValueError,match='CONTAINER_TARGET'):subject.validate_native_targets(prepared,[(value,request,{})])
    else:
        native=[] if change=='missing-readback' else [(dict(label='inspect'),{},[])]
        with pytest.raises(ValueError,match='FILE_SET_INCOMPLETE'):
            subject.validate_publish_native(prepared,tmp_path,{},native,[])


def test_native_host_executable_must_match_exact_profile():
    subject=module();import common
    prepared=dict(inputs=dict(originalFailurePin=dict(sha256='a'*64)),
        hostCommands={'57':[*common.SSH,'root@172.30.30.57','/registered/python -B -']})
    native=[(dict(label='host-verify-57'),dict(argv=[*common.SSH,'root@172.30.30.57','/unregistered/python -B -']),{})]
    with pytest.raises(ValueError,match='HOST_TARGET'):subject.validate_native_targets(prepared,native)


def test_selection_and_closeout_dispatch_v3_to_strict_reader_without_accepting_control_only(tmp_path,monkeypatch):
    subject=module();import main_program_installation_selection as selection;import observe_closeout_hosts as closeout
    path=tmp_path/'selection.json';path.write_bytes(legacy.canonical(dict(schemaVersion='TaskMainProgramInstallations/v3',
        sourceCommit='a'*40,controlGenerationPin={},spugInstallationPin={},continuationInputsPin={})))
    calls=[]
    def reject(*args):calls.append(1);raise ValueError('MAIN_SPUG_CONTINUATION_TEST_REJECTED')
    monkeypatch.setattr(subject,'validate_publication_v3',reject)
    for fn in (selection.select_main_program_installation,closeout.controller_selection):
        with pytest.raises(ValueError,match='CONTINUATION_TEST_REJECTED'):
            fn('57',tmp_path,selection_file=path.name,private=tmp_path)
    assert calls==[1,1]


def test_full_local_write_orchestration_preserves_partial_failure_without_any_core(tmp_path):
    """Real seven-file mutations; external proof deliberately rejects, never PASS."""
    subject=module();task=tmp_path/'task';private=tmp_path/'private';runtime=tmp_path/'runtime'
    for p in (task,private,runtime):p.mkdir()
    ws=writes();locations=[];custody=[]
    for i,row in enumerate(ws):
        active=runtime/(str(i)+'.json');kept=None
        if row['expected'] is not None:
            active.write_bytes(b'old');archive=private/('before-'+str(i));archive.write_bytes(b'old');kept=legacy.file_pin(archive)
        locations.append(active);custody.append(dict(index=i,expected=row['expected'],custody=kept))
    inputs=dict(schemaVersion='MainProgramSpugPublicationInputs/v3',outputFile='fixture.json',sourceCommit='a'*40,
        revisionId='r6',continuationId='c1',controlGenerationPin={},spugResourceBuildPin={},
        originalFailurePin=dict(sha256='b'*64),originalAttemptPin={})
    spug=dict(sourceCommit='a'*40,writes=ws,auditPath='/fixture/new-audit')
    prepared=dict(inputs=inputs,inputPin={},inputPins=[],originalFailure=dict(stages=[]),originalAuditPath='/fixture/old-audit',
        originalSpec=dict(inputs=dict(inputs,schemaVersion='MainProgramSpugPublicationInputs/v2'),
            spugSpec=spug,hostSpecs={h:{} for h in legacy.HOSTS}),
        mountObservation=dict(entryIdentity={}),routes=[])
    calls=[]
    class LocalFiles:
        receipts=[]
        def container(self,label,program):
            calls.append(label);compile(program,'protocol-only-not-executed','exec')
            return dict(status='PASS',phase='preflight')
        def prepare_custody(self):calls.append('custody');return custody
        def install(self,i,kept):
            calls.append('write-'+str(i));active=locations[i]
            expected=None if ws[i]['expected'] is None else dict(ws[i]['expected'],path=str(active))
            return subject.replace_after_custody(active,active.with_suffix('.pending'),expected,
                legacy.canonical(ws[i]['value']),kept[i]['custody'])
        def readback(self,i):return dict(legacy.file_pin(locations[i]),path=ws[i]['path'])
        def host_verify(self,host,program):
            calls.append('host-verify-'+host)
            raise RuntimeError('protocol fixture refuses external verification; no server called')
    with pytest.raises(ValueError,match='FAILED_CHECK_PRIVATE_EVIDENCE'):
        subject.execute_prepared(task,private,prepared,transport=LocalFiles())
    assert not (task/'fixture.json').exists()
    failed=json.loads((private/'fixture.private.json').read_bytes())
    assert failed['status']=='FAILED' and failed['stage']=='host-verify-57'
    assert [r['state'] for r in failed['writeStates']]==['APPLIED']*7
    assert calls[:3]==['guard-before-custody','spug-continuation-preflight','custody']
    assert calls[3:10]==['write-'+str(i) for i in range(7)] and calls[-1]=='host-verify-57'
    assert [p.read_bytes() for p in locations]==[legacy.canonical(r['value']) for r in ws]
    assert [Path(r['custody']['path']).read_bytes() for r in custody if r['custody']]==[b'old']*3
