"""Filesystem contracts use temporary files, never live stage paths or services."""
from copy import deepcopy
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile

import pytest

import main_program_control_staging as subject
import main_program_control_activation as activation
import main_program_control_upgrade_plan as planner
import main_program_control_generation as generation
from test_main_program_control_upgrade_plan import originals


COMMIT='c'*40
SOURCE='intruoyi-57-safe-20261024-v1'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def pin(path,raw):return dict(path=str(path),bytes=len(raw),sha256=digest(raw))


def archive(files,*,extra=None,change=None):
    metadata=dict(variant='standard',fileVerification=True,payloadContentVerification=True,
        files={name:digest(raw) for name,raw in files.items()})
    metadata['packageSha256']=digest(subject.canonical(metadata['files']))
    payload=dict(files,**{'package.json':subject.canonical(metadata)})
    if change:change(payload)
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as output:
        for name,raw in payload.items():
            row=tarfile.TarInfo(name);row.size=len(raw);output.addfile(row,io.BytesIO(raw))
        if extra:
            row,raw=extra;output.addfile(row,io.BytesIO(raw))
    raw=buffer.getvalue()
    return raw,dict(status='PASS',targetCommit=COMMIT,fileCount=147,
        allFilesShaAndCompileVerified=True,packageSha256=digest(raw),fileManifestSha256=metadata['packageSha256'])


@pytest.fixture
def package():
    return archive({'formal/module_'+str(i)+'.py':b'value = 1\n' for i in range(147)})


@pytest.fixture
def filesystem(tmp_path,package):
    raw,build=package;root=tmp_path/'target';root.mkdir();configuration=root/'configuration';configuration.mkdir()
    prior=configuration/'prior';prior.mkdir();retained=[]
    for index in range(9):
        value={'retained':index};content=subject.canonical(value);path=prior/(str(index)+'.json');path.write_bytes(content)
        retained.append(dict(pin=pin(path,content),value=value))
    future=configuration/('main-program-'+COMMIT[:7]+'-r5')
    new=[]
    for name in ('owner','control'):
        value={'new':name};content=subject.canonical(value)
        new.append(dict(pin=pin(future/(name+'.json'),content),value=value))
    spec=dict(schemaVersion='MainProgramControlFilesystemStaging/v1',sourceCommit=COMMIT,revisionId='r5',
        host='172.30.30.58',suffix='58',build=build,
        engines=[dict(path=str(root/('engine-main-program-'+COMMIT[:7])),previousEngine=str(root/'engine-main-program-aaaaaaa'))],
        newDocuments=new,retainedDocuments=retained)
    return spec,raw


def test_actual_standard_package_is_verified_without_extracting(originals):
    args=originals.kwargs;delta=json.loads(args['package_delta_document']['raw'])
    row=next(r for r in delta['packages'] if r['variant']=='standard')
    raw=Path(row['path']).read_bytes();build=json.loads(args['build_document']['raw'])
    loaded=subject.verify_package(raw,build)
    assert loaded['payloadFiles']==args['package_files'] and len(loaded['files'])==148
    assert loaded['packageSha256']==build['packageSha256']


@pytest.mark.parametrize('change',['package-sha','member-sha','duplicate','traversal','symlink','missing','syntax'])
def test_package_rejects_unsafe_or_changed_members(package,change):
    raw,build=package
    if change=='package-sha':build=dict(build,packageSha256='0'*64)
    else:
        files={'formal/module_'+str(i)+'.py':b'value = 1\n' for i in range(147)}
        extra=None;mutate=None
        if change=='member-sha':mutate=lambda items:items.update({'formal/module_0.py':b'value = 2\n'})
        if change in ('duplicate','traversal','symlink'):
            files.pop('formal/module_146.py') # Keep 148 tar members so safety gates, not count alone, reject.
            row=tarfile.TarInfo('formal/module_0.py' if change=='duplicate' else '../outside.py' if change=='traversal' else 'alias.py')
            content=b'value=0\n';row.size=len(content)
            if change=='symlink':row.type=tarfile.SYMTYPE;row.linkname='formal/module_0.py';content=b'';row.size=0
            extra=(row,content)
        if change=='missing':files.pop('formal/module_0.py')
        if change=='syntax':files['formal/module_0.py']=b'def broken(\n'
        raw,build=archive(files,extra=extra,change=mutate)
    reason={'package-sha':'PACKAGE_BUILD_CHANGED','member-sha':'PACKAGE_MANIFEST_CHANGED',
        'duplicate':'PACKAGE_MEMBER_CLOSURE','traversal':'PACKAGE_MEMBER_UNSAFE',
        'symlink':'PACKAGE_MEMBER_UNSAFE','missing':'PACKAGE_MEMBER_CLOSURE'}.get(change)
    with pytest.raises((ValueError,SyntaxError),match=reason):subject.verify_package(raw,build)


def test_preflight_reads_all_retained_without_creating_paths(filesystem):
    spec,raw=filesystem;before={r['pin']['path']:Path(r['pin']['path']).stat().st_mtime_ns for r in spec['retainedDocuments']}
    result=subject.preflight_filesystem(spec,raw)
    assert len(result['newDocuments'])==2 and len(result['retainedDocuments'])==9
    assert not Path(spec['engines'][0]['path']).exists()
    assert not Path(spec['newDocuments'][0]['pin']['path']).parent.exists()
    assert {path:Path(path).stat().st_mtime_ns for path in before}==before


@pytest.mark.parametrize('change',['retained-bytes','new-count','retained-count','new-pin','outside','existing-engine','existing-config','revision','old-engine'])
def test_filesystem_preflight_refuses_before_any_new_write(filesystem,change):
    spec,raw=filesystem;engine=Path(spec['engines'][0]['path']);future=Path(spec['newDocuments'][0]['pin']['path']).parent
    if change=='retained-bytes':Path(spec['retainedDocuments'][0]['pin']['path']).write_bytes(b'changed')
    elif change=='new-count':spec['newDocuments'].pop()
    elif change=='retained-count':spec['retainedDocuments'].pop()
    elif change=='new-pin':spec['newDocuments'][0]['pin']['sha256']='0'*64
    elif change=='outside':spec['newDocuments'][0]['pin']['path']=str(engine.parent.parent/'outside.json')
    elif change=='existing-engine':engine.mkdir()
    elif change=='existing-config':future.mkdir()
    elif change=='revision':spec['revisionId']='r4'
    elif change=='old-engine':spec['engines'][0]['path']=spec['engines'][0]['previousEngine']
    with pytest.raises(ValueError):subject.preflight_filesystem(spec,raw)
    assert engine.exists() is (change=='existing-engine')
    assert future.exists() is (change=='existing-config')


def test_missing_prepare_inputs_and_remote_stage_have_zero_transport(tmp_path):
    calls=[]
    with pytest.raises(FileNotFoundError):subject.run_request(tmp_path,tmp_path,'missing.json',stage=True,transport=calls.append)
    with pytest.raises(ValueError,match='RUNTIME_GATES_REQUIRED'):
        subject.dispatch_remote({},transport=calls.append)
    assert calls==[] and list(tmp_path.iterdir())==[]


def test_native_module_import_needs_only_stdlib_and_performs_no_stage(tmp_path):
    module=Path(subject.__file__).resolve()
    program="import importlib.util,sys; s=importlib.util.spec_from_file_location('native_staging',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.stage_filesystem); print('NATIVE_IMPORT_OK')"
    result=subprocess.run([sys.executable,'-I','-B','-c',program,str(module)],cwd=tmp_path,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr.decode('utf-8')
    assert result.stdout.strip()==b'NATIVE_IMPORT_OK' and list(tmp_path.iterdir())==[]


def test_runtime_materials_bind_full_originals_without_treating_observation_as_admission(prepared_records):
    task,private,bundle,plan_pin,save=prepared_records
    original=json.loads((task/'fixture-input-57.json').read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:original[key] for key in keys})
    save(task,'staging-input.json',inputs)
    prepared=subject.run_request(task,private,'staging-input.json')
    runtime=prepared['runtimeSpec']
    assert runtime['current']['controllers']==[dict(row,environmentMode='ORIGINAL_BASELINE') for row in prepared['hostIdentity']['controllers']]
    assert runtime['sourceExpected']==dict(baseFullRef=bundle['sourceBaseline']['chain'][0]['operationId'],
        parentChainRef=bundle['sourceBaseline']['operationId'],generationId=bundle['sourceBaseline']['generationId'])
    assert runtime['sourceEvidencePins']==[bundle['sourceBaseline'][key] for key in ('pointPin','manifestPin','epochBindingPin')]
    assert runtime['newDocuments']==[row['pin'] for row in prepared['filesystemSpec']['newDocuments']]
    assert runtime['retainedDocuments']==[row['pin'] for row in prepared['filesystemSpec']['retainedDocuments']]
    assert runtime['previousCustody'] is None and runtime['oldReceiptPin'] is None
    assert prepared['remoteExecutable'] is False


def test_stage_orchestration_refuses_changed_candidate_and_retains_created_files(tmp_path):
    order=[];new=tmp_path/'staged'
    class Gates:
        def before(self):order.append('before');return {'state':'original'}
        def preserve(self,before,documents_created):order.append('preserve-new' if documents_created else 'preserve-old');return before
    def write():order.append('files');new.write_bytes(b'new');return {'status':'FILES_STAGED_RUNTIME_UNVERIFIED'}
    def candidate(stage):order.append(stage);return {'epoch':'original' if stage=='before' else 'changed'}
    with pytest.raises(ValueError,match='CANDIDATE_BINDING_CHANGED'):
        subject.run_stage_steps(runtime_gates=Gates(),write_files=write,candidate_gate=candidate,lock_guard=lambda:order.append('lock'))
    assert new.read_bytes()==b'new' and order==['lock','before','before','preserve-old','lock','files','lock','after']


def test_stage_orchestration_gate_failure_precedes_any_write(tmp_path):
    calls=[]
    class Gates:
        def before(self):raise ValueError('ORIGINAL_HISTORY_CHANGED')
    with pytest.raises(ValueError,match='ORIGINAL_HISTORY_CHANGED'):
        subject.run_stage_steps(runtime_gates=Gates(),write_files=lambda:calls.append('write'),
            candidate_gate=lambda stage:calls.append(stage),lock_guard=lambda:calls.append('lock'))
    assert calls==['lock'] and list(tmp_path.iterdir())==[]


def test_stage_orchestration_orders_both_complete_gates_and_rechecks_candidates():
    order=[];baseline={'original':'unchanged'}
    class Gates:
        def before(self):order.append('before');return baseline
        def preserve(self,before,documents_created):
            assert before is baseline and type(documents_created) is bool
            order.append('preserve-new' if documents_created else 'preserve-old');return baseline
    def write():order.append('files');return {'status':'FILES_STAGED_RUNTIME_UNVERIFIED'}
    def candidate(stage):order.append(stage);return {'epoch':'original'}
    result=subject.run_stage_steps(runtime_gates=Gates(),write_files=write,candidate_gate=candidate,lock_guard=lambda:order.append('lock'))
    assert result['before']==result['after']==baseline and result['candidate']=={'epoch':'original'}
    assert order==['lock','before','before','preserve-old','lock','files','lock','after','final','preserve-new','lock']


def test_candidate_before_mutation_is_rejected_before_file_stage():
    writes=[]
    class Gates:
        def before(self):return {'original':'state'}
        def preserve(self,before,documents_created):
            assert documents_created is False
            raise ValueError('RUNTIME_ORIGINALS_CHANGED')
    with pytest.raises(ValueError,match='RUNTIME_ORIGINALS_CHANGED'):
        subject.run_stage_steps(runtime_gates=Gates(),write_files=lambda:writes.append('unexpected'),
            candidate_gate=lambda phase:{},lock_guard=lambda:None)
    assert writes==[]


def test_final_candidate_mutation_is_verified_before_success():
    state={'changed':False}
    class Gates:
        def before(self):return {'original':'state'}
        def preserve(self,before,documents_created):
            if state['changed']:raise ValueError('RUNTIME_ORIGINALS_CHANGED')
            return before
    def candidate(phase):
        if phase=='final':state['changed']=True
        return {}
    with pytest.raises(ValueError,match='RUNTIME_ORIGINALS_CHANGED'):
        subject.run_stage_steps(runtime_gates=Gates(),write_files=lambda:{},candidate_gate=candidate,lock_guard=lambda:None)


def test_candidate_protocol_uses_old_then_new_same_physical_admission(prepared_records):
    task,private,_,_,save=prepared_records
    original=json.loads((task/'fixture-input-58.json').read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:original[key] for key in keys})
    save(task,'staging-input.json',inputs);prepared=subject.run_request(task,private,'staging-input.json')
    calls=[];old=prepared['runtimeSpec']['current']['controllers'][0];new=prepared['candidateControllers'][0]
    configs={}
    for row in (old,new):
        ref=row.get('controlConfigurationPin',row.get('controlPin'))
        configs[ref['path']]=dict(pythonPin={'path':'/pinned/python'},environment={'PYTHONPATH':row['engine']+'/control'})
    def read(ref):return configs[ref['path']]
    def run(args,timeout,env):
        calls.append((args,timeout,env))
        if args[-1]=='--check-imports':return subject.canonical({'role':Path(args[-2]).name.removesuffix('_entry.py')})
        value=json.loads(args[-1]);assert value['oldOwnerPin']==old['ownerConfigurationPin']
        return subject.canonical(dict(actualConfigurationReadPassed=True,directlyAdmittedSources=list(subject.SOURCES),
            archiveViewsPreflightVerified=True,epochPolicy={'original':'policy'},epoch={'state':'READY'}))
    programs={'candidate':activation.CANDIDATE_GATE,'sourceIdle':activation.SOURCE_IDLE}
    before=subject.candidate_admission(prepared,'before',programs,run=run,read=read,source_plan=None)
    after=subject.candidate_admission(prepared,'after',programs,run=run,read=read,source_plan=None)
    assert before==after and len(calls)==8
    assert json.loads(calls[3][0][-1])['controlPin']==old['controlConfigurationPin']
    assert json.loads(calls[7][0][-1])['controlPin']==new['controlPin']
    assert calls[3][0][-2]==programs['candidate'] and calls[7][0][-2]==programs['candidate']


def test_stage_report_projection_requires_complete_actual_runtime_result(filesystem):
    spec,_=filesystem
    prepared={'inputs':dict(revisionId='r5',previousControlGenerationPin={'file':'original'},buildPin={'file':'build'},planPin={'file':'plan'}),
        'filesystemSpec':spec,'candidateControllers':[dict(role='target',controlPin={'path':'new-control'},ownerPin={'path':'new-owner'})]}
    before=dict(controllers=[dict(service='original',pid=17,argvSha256='a'*64)],containers={'original':{}},
        fstabPin={'sha256':'b'*64},mountinfoSha256='c'*64,documentsCreated=False)
    after=dict(before,documentsCreated=True)
    actual=dict(before=before,after=after,candidate={'controllers':[dict(actualConfigurationReadPassed=True,
        directlyAdmittedSources=list(subject.SOURCES),archiveViewsPreflightVerified=True,epoch={'state':'READY'})]},
        files=dict(status='FILES_STAGED_RUNTIME_UNVERIFIED',engines=[dict(path=spec['engines'][0]['path'])]))
    report=subject.project_stage_reports(prepared,actual)
    assert report['engine']['status']==report['configuration']['status']=='STAGED_NOT_ACTIVATED'
    assert report['configuration']['configurationStaging']['retainedDocuments']==[row['pin'] for row in spec['retainedDocuments']]
    actual['after']['containers']={'unrelated':{}}
    with pytest.raises(ValueError,match='RUNTIME_ORIGINALS_CHANGED'):subject.project_stage_reports(prepared,actual)


def test_source_http_uses_fixed_loopback_and_one_ten_second_budget():
    from types import SimpleNamespace
    calls=[];times=iter([0,1,2,3,4]);payload=b'{"state":"READY"}'
    class Response:
        status=200
        fp=SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=lambda v:calls.append(('socket',v)))))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read1(self,size):
            nonlocal payload
            result=payload;payload=b'';return result
    class Opener:
        def open(self,request,timeout):
            calls.append(('request',request.full_url,timeout));return Response()
    result=subject.fetch_source_plan({'listenPort':17301},{'pid':51},lambda row:calls.append(('pid',row['pid'])),
        {'X-Fixture':'secret'},opener=Opener(),clock=lambda:next(times))
    assert result=={'state':'READY'}
    assert calls==[('pid',51),('request','http://127.0.0.1:17301/incremental-plan?sourceConfigRef='+SOURCE,9),
        ('socket',8),('socket',7),('pid',51)]


def test_source_http_refuses_deadline_and_changed_controller_without_retry():
    from types import SimpleNamespace
    calls=[];times=iter([0,1,11])
    class Response:
        status=200
        fp=SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=lambda v:calls.append(v))))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read1(self,size):raise AssertionError('expired response must not be read')
    class Opener:
        def open(self,request,timeout):calls.append('open');return Response()
    with pytest.raises(ValueError,match='SOURCE_HTTP_DEADLINE'):
        subject.fetch_source_plan({'listenPort':17301},{'pid':51},lambda row:None,{},opener=Opener(),clock=lambda:next(times))
    assert calls==['open']
    def changed(row):raise ValueError('CONTROL_PROCESS_CHANGED')
    with pytest.raises(ValueError,match='CONTROL_PROCESS_CHANGED'):
        subject.fetch_source_plan({'listenPort':17301},{'pid':51},changed,{},opener=Opener(),clock=lambda:0)
    assert calls==['open']


def test_execution_bundle_rejects_modified_module_before_module_execution(tmp_path):
    marker=tmp_path/'must-not-exist'
    modules=[]
    for name in ('main_program_control_runtime','main_program_control_staging'):
        source=(Path(subject.__file__).parent/(name+'.py')).read_text(encoding='utf-8')
        modules.append(dict(name=name,source=source,pin=dict(file=name+'.py',bytes=len(source.encode()),sha256=digest(source.encode()))))
    programs={name:dict(source='pass',bytes=4,sha256=digest(b'pass')) for name in ('environment','custody','candidate','sourceIdle')}
    envelope=dict(schemaVersion='MainProgramControlStagingExecution/v1',modules=modules,programs=programs,prepared={},packageBase64='')
    modules[0]['source']='from pathlib import Path\nPath('+repr(str(marker))+').write_text("unexpected")\n'
    with pytest.raises(ValueError,match='MODULE_SOURCE_CHANGED'):subject.load_execution(envelope)
    assert not marker.exists()


def test_execution_bundle_is_fixed_and_generated_bootstrap_fails_without_mutation(prepared_records,tmp_path):
    task,private,_,_,save=prepared_records
    original=json.loads((task/'fixture-input-58.json').read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:original[key] for key in keys})
    save(task,'staging-input.json',inputs);prepared=subject.run_request(task,private,'staging-input.json')
    bundle=subject.execution_bundle(prepared)
    assert [row['name'] for row in bundle['modules']]==['main_program_control_runtime','main_program_control_staging']
    assert set(bundle['programs'])=={'environment','custody','candidate','sourceIdle'}
    assert bundle['programs']['candidate']['source']==activation.CANDIDATE_GATE
    bundle['prepared']['filesystemSpec']['sourceCommit']='invalid'
    script=subject.render_bootstrap(bundle)
    result=subprocess.run([sys.executable,'-I','-B','-'],input=script.encode('utf-8'),cwd=tmp_path,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr.decode('utf-8')
    value=json.loads(result.stdout)
    assert value['status']=='FAILED' and value['backupDispatched'] is False and value['restoreDispatched'] is False
    assert value['stage']=='preflight' and value['filesMayHaveBeenCreated'] is False


def test_failed_transport_keeps_attempt_and_raw_original_without_success_reports(prepared_records):
    task,private,_,_,save=prepared_records
    original=json.loads((task/'fixture-input-58.json').read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:original[key] for key in keys})
    save(task,'staging-input.json',inputs);prepared=subject.run_request(task,private,'staging-input.json')
    for name in (prepared['engineReportFile'],prepared['configurationReportFile']):(task/name).unlink()
    calls=[];failure=subject.canonical(dict(status='FAILED',stage='write-files',errorCode='ENOSPC',filesMayHaveBeenCreated=True))
    def transport(host,script):calls.append(host);return dict(stdout=failure,stderr=b'original stderr',returncode=0,timedOut=False)
    with pytest.raises(ValueError,match='REMOTE_STAGE_FAILED'):
        subject.dispatch_prepared(task,private,prepared,transport=transport)
    stem='main-program-control-staging-58-45dd7dc-r5'
    assert calls==['172.30.30.58']
    assert (private/(stem+'-stdout.private.log')).read_bytes()==failure
    assert (private/(stem+'-stderr.private.log')).read_bytes()==b'original stderr'
    attempt=(private/(stem+'-attempt.private.json')).read_bytes()
    assert json.loads(attempt)['status']=='ATTEMPT_RESERVED'
    assert not (task/prepared['engineReportFile']).exists() and not (task/prepared['configurationReportFile']).exists()
    with pytest.raises(ValueError,match='ATTEMPT_OR_REPORT_EXISTS'):
        subject.dispatch_prepared(task,private,prepared,transport=transport)
    assert calls==['172.30.30.58'] and (private/(stem+'-attempt.private.json')).read_bytes()==attempt


def test_staging_capacity_refuses_without_creating_paths(filesystem,monkeypatch):
    from types import SimpleNamespace
    spec,raw=filesystem;ready=subject.preflight_filesystem(spec,raw)
    import shutil
    monkeypatch.setattr(shutil,'disk_usage',lambda path:SimpleNamespace(free=0))
    with pytest.raises(ValueError,match='STAGING_CAPACITY_INSUFFICIENT'):subject.verify_staging_space(spec,ready)
    assert not Path(spec['engines'][0]['path']).exists()


@pytest.fixture
def physical_scope(tmp_path):
    lock=tmp_path/'physical.lock';lock.write_bytes(b'')
    policy=dict(sourceLockPath=str(lock),databaseUuid='database-scope')
    target='original-target'
    owner=dict(targets={target:dict(replacement=dict(lockPath=str(lock),databaseUuid='database-scope'))},
        targetBackupEpochPolicies={target:policy},targetProgramPolicies={target:dict(backupEpochPolicy=policy)})
    control=dict(sourceEpochPolicies={SOURCE:policy})
    owner_path=tmp_path/'owner.json';owner_raw=subject.canonical(owner);owner_path.write_bytes(owner_raw)
    control_path=tmp_path/'control.json';control_raw=subject.canonical(control);control_path.write_bytes(control_raw)
    spec=dict(targetConfigRef=target,current=dict(host='172.30.30.57',suffix='57',controllers=[
        dict(role='source',controlConfigurationPin=pin(control_path,control_raw)),
        dict(role='target',ownerConfigurationPin=pin(owner_path,owner_raw))]))
    return spec,lock,control_path,control


def test_physical_lock_selection_uses_original_target_and_same_source_epoch(physical_scope):
    spec,lock,_,_=physical_scope
    assert subject.select_physical_lock(spec)==str(lock)


def test_physical_lock_selection_refuses_other_source_scope_before_write(physical_scope):
    spec,lock,path,control=physical_scope;control['sourceEpochPolicies'][SOURCE]['sourceLockPath']=str(lock.with_name('other'))
    raw=subject.canonical(control);path.write_bytes(raw)
    spec['current']['controllers'][0]['controlConfigurationPin']=pin(path,raw)
    with pytest.raises(ValueError,match='SOURCE_TARGET_EPOCH_MISMATCH'):subject.select_physical_lock(spec)
    assert not lock.with_name('other').exists()


def test_linux_physical_lock_is_real_and_never_recreated(tmp_path):
    assert os.name=='posix','Requires native Linux.'
    path=tmp_path/'physical.lock';path.write_bytes(b'');before=path.stat()
    with subject.PhysicalLock(path) as lock:
        lock.guard()
        program="import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
        reply=subprocess.run([sys.executable,'-I','-B','-c',program,str(path)],capture_output=True,timeout=10)
        assert reply.returncode!=0 and b'BlockingIOError' in reply.stderr
    assert path.stat().st_ino==before.st_ino and path.read_bytes()==b''
    with subject.PhysicalLock(path) as lock:lock.guard()


def test_linux_physical_lock_replacement_is_rejected_and_preserved(tmp_path):
    assert os.name=='posix','Requires native Linux.'
    path=tmp_path/'physical.lock';path.write_bytes(b'')
    with subject.PhysicalLock(path) as lock:
        old=tmp_path/'original.lock';path.rename(old);path.write_bytes(b'other')
        with pytest.raises(ValueError,match='LOCK_IDENTITY_CHANGED'):lock.guard()
    assert old.exists() and path.read_bytes()==b'other'


def test_linux_stage_steps_use_shared_runtime_gate_real_lock_and_real_files(filesystem,tmp_path):
    assert os.name=='posix','Requires native Linux.'
    from test_main_program_control_runtime import runtime,gates
    stream=runtime.__wrapped__(tmp_path);case=next(stream)
    try:
        spec,raw=filesystem
        case['spec']['newDocuments']=[row['pin'] for row in spec['newDocuments']]
        case['spec']['retainedDocuments']=[row['pin'] for row in spec['retainedDocuments']]
        lock_path=tmp_path/'actual-physical.lock';lock_path.write_bytes(b'')
        with subject.PhysicalLock(lock_path) as lock:
            api=gates(case);api.lock_guard=lock.guard
            result=subject.run_stage_steps(runtime_gates=api,write_files=lambda:subject.stage_filesystem(spec,raw),
                candidate_gate=lambda phase:{'explicitExternalAdmissionProtocol':'unchanged'},lock_guard=lock.guard)
            assert result['files']['status']=='FILES_STAGED_RUNTIME_UNVERIFIED'
            assert result['before']['documentsCreated'] is False and result['after']['documentsCreated'] is True
            assert result['before']['containers']==result['after']['containers']
            assert len(result['files']['engines'])==1
    finally:
        with pytest.raises(StopIteration):next(stream)


class Materials:
    def __init__(self,kwargs):self.kwargs=kwargs
    def __repr__(self):return '<actual-staging-materials-with-explicit-host-protocol>'


@pytest.fixture(scope='module')
def staging_materials(originals):
    # Real original plans/packages/coverage; generation index and current host
    # observations are explicit protocol fixtures, never live admission proof.
    args=deepcopy(originals.kwargs);task=Path(__file__).resolve().parent
    for host,cores in args['predecessor']['controllersByHost'].items():
        args['predecessor']['selections'][host]['controllers']=[
            {key:row[key] for key in generation.SELECTION_CONTROLLER_KEYS} for row in cores]
    result=planner.plan_control_upgrade(**args);public=result['plan'];private=result['privatePlan']
    coverage_path=task/'main-program-control-coverage-45dd7dc-r1.json';content=coverage_path.read_bytes()
    coverage_ref=dict(file=coverage_path.name,bytes=len(content),sha256=digest(content))
    reference=lambda name:dict(file=name,bytes=3,sha256='a'*64)
    commit=args['source_commit'];short=commit[:7];suffix='58';revision=args['revision_id']
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',sourceCommit=commit,revisionId=revision,suffix=suffix,
        previousControlGenerationPin=args['predecessor']['generationPin'],buildPin=args['build_document']['pin'],
        planPin=dict(file='main-program-configuration-plan-'+short+'-'+revision+'.json',
            bytes=len(subject.canonical(public)),sha256=digest(subject.canonical(public))),coveragePin=coverage_ref,
        unitObservationPin=reference('main-program-control-units-'+suffix+'-'+short+'-'+revision+'.json'),
        originalEnvironmentObservationPin=reference('main-program-control-environment-baseline-'+suffix+'-'+short+'-'+revision+'.json'))
    coverage=activation.validate_generation_coverage(activation.contract.Records(task),inputs,args['predecessor'])
    delta=json.loads(args['package_delta_document']['raw']);standard=next(r for r in delta['packages'] if r['variant']=='standard')
    controllers=[]
    for row in args['predecessor']['selections'][suffix]['controllers']:
        controllers.append(dict({k:row[k] for k in generation.SELECTION_CONTROLLER_KEYS},
            argvSha256='b'*64,environmentSha256='c'*64,systemdEnvironmentSha256='d'*64,
            unitPin=dict(path='/etc/systemd/system/'+row['service'],bytes=1,sha256='e'*64),dropinPins=[row['dropinPin']]))
    identity=dict(host='172.30.30.'+suffix,previousControlGenerationPin=inputs['previousControlGenerationPin'],
        unitObservationPin=inputs['unitObservationPin'],environmentObservationPin=inputs['originalEnvironmentObservationPin'],controllers=controllers)
    return Materials(dict(inputs=inputs,predecessor=args['predecessor'],public=public,private=private,coverage=coverage,
        plan_document=dict(pin=deepcopy(inputs['planPin']),raw=subject.canonical(public)),
        build_document=args['build_document'],delta_document=args['package_delta_document'],
        package_raw=Path(standard['path']).read_bytes(),host_identity=identity))


def test_prepare_materials_reconstructs_exact_plan_without_creating_stage(staging_materials):
    prepared=subject.prepare_materials(**staging_materials.kwargs)
    assert prepared['status']=='PREPARED_NOT_STAGED' and prepared['remoteExecutable'] is False
    assert prepared['filesystemSpec']['host']=='172.30.30.58'
    assert len(prepared['filesystemSpec']['newDocuments'])==2 and len(prepared['filesystemSpec']['retainedDocuments'])==9
    assert prepared['engineReportFile']=='main-program-engine-staged-58-45dd7dc-r5.json'
    assert prepared['configurationReportFile']=='main-program-configuration-staged-58-45dd7dc-r5.json'
    assert prepared['requiredRuntimeGates']==list(subject.RUNTIME_GATES)


@pytest.mark.parametrize('change',['commit','host','plan-pin','generation','host-pid','coverage','member'])
def test_prepare_materials_rejects_changed_bound_material(staging_materials,change):
    values=deepcopy(staging_materials.kwargs)
    if change=='commit':values['inputs']['sourceCommit']='d'*40
    elif change=='host':values['host_identity']['host']='172.30.30.59'
    elif change=='plan-pin':values['inputs']['planPin']['sha256']='0'*64
    elif change=='generation':values['inputs']['previousControlGenerationPin']['sha256']='0'*64
    elif change=='host-pid':values['host_identity']['controllers'][0]['pid']+=1
    elif change=='coverage':values['coverage']['coverage']['candidateBuildPin']['sha256']='0'*64
    elif change=='member':values['package_raw']=values['package_raw']+b'changed'
    with pytest.raises(ValueError):subject.prepare_materials(**values)


@pytest.fixture
def prepared_records(tmp_path,originals,monkeypatch):
    from test_main_program_control_generation_activation import coverage_documents,prepared_protocol
    coverage=coverage_documents.__wrapped__(tmp_path)
    return prepared_protocol.__wrapped__(coverage,originals,monkeypatch)


@pytest.mark.parametrize('suffix',['57','58','59'])
def test_record_prepare_reads_real_pins_and_keeps_all_inputs_unchanged(prepared_records,suffix):
    task,private,bundle,plan_pin,save=prepared_records
    original=json.loads((task/('fixture-input-'+suffix+'.json')).read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:original[key] for key in keys})
    save(task,'staging-input.json',inputs)
    before={path:path.read_bytes() for path in task.rglob('*') if path.is_file()}
    prepared=subject.run_request(task,private,'staging-input.json')
    assert prepared['status']=='PREPARED_NOT_STAGED' and prepared['remoteExecutable'] is False
    assert len(prepared['filesystemSpec']['newDocuments'])==(4 if suffix=='57' else 2)
    assert len(prepared['filesystemSpec']['retainedDocuments'])==9
    actual={p['path']:p for p in prepared['inputPins']}
    assert str(task/'staging-input.json') in actual
    assert str(task/inputs['unitObservationPin']['file']) in actual
    assert str(private/inputs['originalEnvironmentObservationPin']['file'].replace('.json','.private.json')) in actual
    assert all(activation.file_pin(path)==reference for path,reference in actual.items())
    assert {path:path.read_bytes() for path in task.rglob('*') if path.is_file()}==before


def test_linux_exclusive_stage_modes_and_retained_bytes(filesystem):
    assert os.name=='posix','Requires the separate native Linux test runner; do not skip or emulate.'
    spec,raw=filesystem;before={r['pin']['path']:(Path(r['pin']['path']).read_bytes(),Path(r['pin']['path']).stat()) for r in spec['retainedDocuments']}
    result=subject.stage_filesystem(spec,raw)
    assert result['status']=='FILES_STAGED_RUNTIME_UNVERIFIED' and result['activationReportEligible'] is False
    engine=Path(spec['engines'][0]['path']);files=[p for p in engine.rglob('*') if p.is_file()]
    assert len(files)==148
    for path in files+[Path(r['pin']['path']) for r in spec['newDocuments']]:
        item=path.lstat();assert stat.S_IMODE(item.st_mode)==0o400 and item.st_nlink==1 and item.st_uid==os.geteuid()
    for name,(content,info) in before.items():
        current=Path(name).stat();assert Path(name).read_bytes()==content
        assert (current.st_ino,current.st_mtime_ns,current.st_ctime_ns)==(info.st_ino,info.st_mtime_ns,info.st_ctime_ns)
    with pytest.raises(ValueError,match='EXISTS'):subject.stage_filesystem(spec,raw)


@pytest.mark.parametrize('alias',['symlink-file','symlink-parent','hardlink'])
def test_linux_aliases_refuse_before_new_write(filesystem,alias):
    assert os.name=='posix','Requires the separate native Linux test runner; do not skip or emulate.'
    spec,raw=filesystem;path=Path(spec['retainedDocuments'][0]['pin']['path']);saved=path.with_suffix('.original')
    path.rename(saved)
    if alias=='symlink-file':path.symlink_to(saved)
    elif alias=='hardlink':os.link(saved,path)
    else:
        parent=path.parent;real=parent.with_name('actual-prior');parent.rename(real);parent.symlink_to(real,target_is_directory=True)
        (real/path.name).write_bytes(saved.read_bytes() if saved.exists() else (real/saved.name).read_bytes())
    with pytest.raises(ValueError,match='ALIAS|HARDLINK'):subject.stage_filesystem(spec,raw)
    assert not Path(spec['engines'][0]['path']).exists()


def test_linux_partial_write_is_retained_and_repeat_is_refused(filesystem,monkeypatch):
    assert os.name=='posix','Requires the separate native Linux test runner; do not skip or emulate.'
    spec,raw=filesystem;original=os.write;calls=[]
    def fail(fd,data):
        calls.append(fd)
        if len(calls)==3:raise OSError(errno.ENOSPC,'explicit storage boundary failure')
        return original(fd,data)
    monkeypatch.setattr(subject.os,'write',fail)
    with pytest.raises(subject.StagingFailure) as observed:subject.stage_filesystem(spec,raw)
    assert len(observed.value.created_paths)>=3 and all(Path(p).exists() for p in observed.value.created_paths)
    assert Path(spec['engines'][0]['path']).is_dir()
    with pytest.raises(ValueError,match='EXISTS'):subject.stage_filesystem(spec,raw)
