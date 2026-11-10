"""Real local files/Git; protocol projections never claim an actual installation."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import main_program_installation_selection as contract
import main_program_spug_publication as publication
import spug_runtime_dependency_completion as dependency
from test_main_program_spug_publication_verify_only import originals, prepared


def subject():return importlib.import_module('main_program_spug_resource_transition')
def content(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(publication.canonical(value));return publication.file_pin(path)


def predecessor_files(prepared):
    return {p['path'].removeprefix('/opt/intruoyi-spug/'):{k:p[k] for k in ('bytes','sha256')}
            for p in prepared['dependency']['core']['filePinsAfter']}


def delta(before,after,build):
    return dict(schemaVersion='MainProgramSpugResourceDeploymentDelta/v2',resourceBuildPin=build,
                changes=[dict(relativePath=n,beforePin=dict(path='/opt/intruoyi-spug/'+n,**before[n]),
                              afterPin=dict(path='/opt/intruoyi-spug/'+n,**after[n]))
                         for n in sorted(before) if before[n]!=after[n]])


@pytest.mark.parametrize('count',[1,2,5,14])
def test_exact_nonempty_difference_is_not_a_fixed_file_count(prepared,count):
    before=predecessor_files(prepared);after=deepcopy(before)
    for name in sorted(after)[:count]:after[name]=content(('new '+name).encode())
    pin=dict(file='build.json',bytes=1,sha256='a'*64);value=delta(before,after,pin)
    assert subject().validate_delta(value,before,after,pin)==value['changes']


@pytest.mark.parametrize('bad',['empty','missing','extra','unchanged','before','after','duplicate','outside'])
def test_difference_rejects_incomplete_or_false_changes(prepared,bad):
    before=predecessor_files(prepared);after=deepcopy(before);names=sorted(before)
    for name in names[:2]:after[name]=content(('new '+name).encode())
    pin=dict(file='build.json',bytes=1,sha256='a'*64);value=delta(before,after,pin)
    if bad=='empty':after=deepcopy(before);value['changes']=[]
    elif bad=='missing':value['changes'].pop()
    elif bad=='extra':value['changes'].append(dict(value['changes'][0],relativePath=names[2]))
    elif bad=='unchanged':value['changes'][0]['afterPin']=value['changes'][0]['beforePin']
    elif bad in ('before','after'):value['changes'][0][bad+'Pin']['sha256']='0'*64
    elif bad=='duplicate':value['changes'].append(deepcopy(value['changes'][0]))
    else:after['../escape']=after.pop(names[-1])
    with pytest.raises(ValueError):subject().validate_delta(value,before,after,pin)


@pytest.fixture
def local_build(tmp_path,prepared):
    root=tmp_path/'checkout';private=tmp_path/'private';task=tmp_path/'task'
    root.mkdir();private.mkdir();task.mkdir()
    completion=prepared['dependency']['prepared']['completion']
    custody=json.loads(Path(completion['sourceCustodyPin']['path']).read_bytes())
    entries=custody['entries'];sources={}
    for name in dependency.ALLOWED:
        row=next(r for r in entries if r['originalPin']['path'].replace('\\','/').endswith('/ops/spug/'+name))
        raw=publication.verify_bytes(row['preservedPin']);sources[name]=raw
        path=root/'ops/spug'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    adapter=root/'ops/spug/smallapp_adapter.py'
    adapter.write_bytes(adapter.read_bytes()+b'\nSELECTION_TOTAL_SECONDS = 50\n')
    sources['smallapp_adapter.py']=adapter.read_bytes()
    (root/'ops/spug/test_contract.py').write_bytes(b'def test_fixture(): assert True\n')
    def git(*args):
        result=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=20)
        assert result.returncode==0,result.stderr;return result.stdout.decode().strip()
    git('init','-q');git('config','user.name','Local contract fixture');git('config','user.email','fixture@example.invalid')
    git('config','core.autocrlf','false');git('add','.');git('commit','-qm','local fixture')
    repository=root.parent/'repository'
    root.rename(repository)
    created=subprocess.run(['git','-C',str(repository),'worktree','add','--detach',str(root),'HEAD'],capture_output=True,timeout=20)
    assert created.returncode==0,created.stderr
    graph=dependency.inspect_runtime_dependencies(sources=sources)
    pins={str(p.relative_to(root)).replace('\\','/'):publication.file_pin(p) for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
    # This report is a validator protocol fixture, not a report of product tests.
    log=private/'protocol.log';log.write_bytes(b'1 passed in 0.01s\r\n')
    proof=dict(schemaVersion='TaskSpugResourceValidation/v2',status='PASS',actualExitCode=0,actualPassed=1,
               actualSkipped=0,inputPins={n:p['sha256'] for n,p in pins.items()},logPin=publication.file_pin(log))
    proofpin=put(task/'proof.json',proof);proofpin=dict(file='proof.json',**{k:proofpin[k] for k in ('bytes','sha256')})
    kept=[]
    for index,(name,pin) in enumerate(sorted(pins.items())):
        keep=private/('source-'+str(index));keep.write_bytes(publication.verify_bytes(pin))
        kept.append(dict(relativePath=name,originalPin=pin,preservedPin=publication.file_pin(keep)))
    custody_pin=put(private/'candidate-custody.json',dict(schemaVersion='MainProgramSpugResourceSourceCustody/v1',entries=kept))
    report=dict(schemaVersion='MainProgramSpugResourceBuild/v2',status='PASS',sourceCommit=git('rev-parse','HEAD'),
                worktree=str(root),fileCount=14,files={'ops/spug/'+n:p for n,p in graph['files'].items()},
                dependencyGraph=graph,testEvidencePin=proofpin,sourceCustodyPin=custody_pin,selectionReadBudgetSeconds=50)
    ref=put(task/'build.json',report);ref=dict(file='build.json',**{k:ref[k] for k in ('bytes','sha256')})
    return task,private,root,report,ref


def test_real_git_build_and_explicit_preserved_source_readback(local_build):
    task,private,root,report,ref=local_build
    actual,pins=subject().validate_build(contract.Records(task),private,ref,verify_checkout=True)
    assert actual==report and pins
    (root/'ops/spug/smallapp-ui/app.js').write_bytes(b'changed')
    with pytest.raises(ValueError):subject().validate_build(contract.Records(task),private,ref,verify_checkout=True)
    actual,pins=subject().validate_build(contract.Records(task),private,ref,verify_checkout=False)
    assert actual==report and not any(Path(p['path']).is_relative_to(root) for p in pins)


def test_lf_crlf_and_failure_summaries_preserve_original_log_bytes(local_build):
    task,private,root,report,ref=local_build
    # These are parser/receipt protocol cases. Historical mode uses the actual
    # preserved source files and avoids repeating unrelated Git admission.
    for ending in (b'\n',b'\r\n'):
        for failure in (None,b'failed',b'skipped',b'error'):
            raw=b'1 passed in 0.01s'+ending
            if failure:raw+=b'1 '+failure+b' in 0.01s'+ending
            log=private/'protocol.log';log.write_bytes(raw)
            proof=json.loads((task/'proof.json').read_bytes());proof['logPin']=publication.file_pin(log)
            pin=put(task/'proof.json',proof)
            report['testEvidencePin']=dict(file='proof.json',**{k:pin[k] for k in ('bytes','sha256')})
            pin=put(task/'build.json',report);ref=dict(file='build.json',**{k:pin[k] for k in ('bytes','sha256')})
            if failure:
                with pytest.raises(ValueError,match='TEST_LOG_NOT_PASSED'):
                    subject().validate_build(contract.Records(task),private,ref,verify_checkout=False)
            else:assert subject().validate_build(contract.Records(task),private,ref,verify_checkout=False)[0]==report
            assert log.read_bytes()==raw


def test_main_checkout_is_not_a_dedicated_candidate_worktree(local_build):
    task,private,root,report,ref=local_build
    if (root.parent/'repository').is_dir():report['worktree']=str(root.parent/'repository')
    p=put(task/'build.json',report);ref=dict(file='build.json',**{k:p[k] for k in ('bytes','sha256')})
    with pytest.raises(ValueError,match='DEDICATED_WORKTREE_REQUIRED'):
        subject().validate_build(contract.Records(task),private,ref,verify_checkout=True)


@pytest.mark.parametrize('bad',['graph','custody','commit','test-log'])
def test_candidate_build_refuses_incorrect_evidence(local_build,bad):
    task,private,root,report,ref=local_build
    if bad=='graph':report['dependencyGraph']['edges'].pop()
    elif bad=='custody':
        value=json.loads(Path(report['sourceCustodyPin']['path']).read_bytes())
        Path(value['entries'][0]['preservedPin']['path']).write_bytes(b'drift')
    elif bad=='commit':report['sourceCommit']='0'*40
    else:(private/'protocol.log').write_bytes(b'1 failed in 0.01s\n')
    if bad in ('graph','commit'):
        p=put(task/'build.json',report);ref=dict(file='build.json',**{k:p[k] for k in ('bytes','sha256')})
    with pytest.raises(ValueError):subject().validate_build(contract.Records(task),private,ref,verify_checkout=True)


def test_runtime_view_uses_new_full_set_without_mutating_historical_a(prepared):
    old=deepcopy(prepared);files=predecessor_files(prepared);files['smallapp-ui/app.js']=content(b'new')
    core=prepared['dependency']['core'];identity=dict(core['entryAfter'],pid=160001,startTicks='130000000')
    view=subject().runtime_view(prepared,files,identity,core['entryEnvironmentSha256'])
    spec=dependency.runtime_spec(view,'after',identity,core['entryEnvironmentSha256'])
    assert len(spec['filePins'])==14 and len(spec['configurationPins'])==7
    assert next(p for p in spec['filePins'] if p['path'].endswith('/app.js'))['sha256']==files['smallapp-ui/app.js']['sha256']
    assert prepared==old
    with pytest.raises(ValueError):dependency.validate_runtime_result(view,{'status':'PASS'},'after',identity,core['entryEnvironmentSha256'])


@pytest.mark.parametrize('fail_at',[None,1])
def test_actual_file_replacement_preserves_all_before_first_write(tmp_path,prepared,fail_at):
    module=subject();runtime=tmp_path/'runtime';candidate=tmp_path/'candidate';private=tmp_path/'private'
    runtime.mkdir();candidate.mkdir();private.mkdir();before=predecessor_files(prepared);after=deepcopy(before)
    names=['smallapp_adapter.py','smallapp-ui/app.js','smallapp_simple.py']
    # Real local bytes, the guard is a protocol seam and asserts every archive.
    for n in before:
        p=runtime/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('old '+n).encode());before[n]=content(p.read_bytes())
        q=candidate/'ops/spug'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes());after[n]=before[n]
    for n in names:(candidate/'ops/spug'/n).write_bytes(('new '+n).encode());after[n]=content(('new '+n).encode())
    buildpin=dict(file='build.json',bytes=1,sha256='a'*64)
    value=dict(runtime=str(runtime),build=dict(worktree=str(candidate)),beforeFiles=before,afterFiles=after,
               changes=delta(before,after,buildpin)['changes'],stem='local-transition',inputPins=[])
    seen=[]
    def guard(replaced):
        assert len(list((private/'local-transition-originals').glob('*-before*')))==3
        module.check_runtime(value,replaced);seen.append(set(replaced))
        if fail_at is not None and len(replaced)==fail_at:raise ValueError('LOCAL_PROTOCOL_STOP')
    if fail_at is None:
        result=module.replace_files(value,private,guard)
        assert len(result)==3 and seen[0]==set() and seen[-1]==set(names)
    else:
        with pytest.raises(ValueError,match='LOCAL_PROTOCOL_STOP'):module.replace_files(value,private,guard)
        assert len([n for n in names if (runtime/n).read_bytes().startswith(b'new')])==1
    with pytest.raises(ValueError,match='ORIGINALS_EXIST'):module.replace_files(value,private,guard)


def test_generated_guard_really_refuses_absent_process(prepared,tmp_path,local_build):
    module=subject();core=prepared['dependency']['core'];view=module.runtime_view(prepared,predecessor_files(prepared),core['entryAfter'],core['entryEnvironmentSha256'])
    program=dependency.runtime_program(view,'after',core['entryAfter'],core['entryEnvironmentSha256'])
    assert not Path('/proc').exists()
    env=dict(os.environ,PYTHONPATH=str(local_build[2]/'ops/spug'),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-X','utf8','-B','-'],input=program.encode(),capture_output=True,cwd=tmp_path,env=env,timeout=20)
    assert result.returncode==0 and json.loads(result.stdout)['status']=='FAILED'


def test_default_transition_cli_has_no_implicit_transport():
    args=subject().parser().parse_args(['--inputs','candidate.json'])
    assert args.apply is False and args.observe is False


@pytest.mark.parametrize('failure',[False,True])
def test_real_local_transition_native_journal_and_historical_b_view(local_build,prepared,monkeypatch,failure):
    """Actual files/Git/native children; Docker/DB/process semantics are a protocol seam.

    The seam redirects only Docker Popen to a local Python protocol peer. It does
    not execute the generated Linux guard and proves no actual container update.
    """
    module=subject();task,private,root,report,buildref=local_build;historical_runtime=publication.RUNTIME
    for pin in prepared['inputPins']:
        path=Path(pin['path'])
        if path.parent==Path(__file__).parent and path.suffix=='.json':
            (task/path.name).write_bytes(publication.verify_bytes(pin))
    runtime=private/'runtime';runtime.mkdir()
    old=prepared['dependency']['prepared']['completion']
    custody=json.loads(Path(old['sourceCustodyPin']['path']).read_bytes())
    for name in dependency.ALLOWED:
        row=next(r for r in custody['entries'] if r['originalPin']['path'].replace('\\','/').endswith('/ops/spug/'+name))
        path=runtime/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(publication.verify_bytes(row['preservedPin']))
    monkeypatch.setattr(publication,'RUNTIME',str(runtime))
    # Inspect is replayed only at the declared external protocol boundary.
    a=prepared['dependency'];native=json.loads(Path(a['rich']['nativeReceiptPins'][0]['path']).read_bytes())
    inspect_rows=json.loads(Path(native['stdoutPin']['path']).read_bytes())
    for container in inspect_rows:
        if container['Id']==publication.CONTAINER:
            for mount in container['Mounts']:
                if mount['Destination']=='/opt/intruoyi-spug':mount['Source']=str(runtime)
    (private/'inspect.json').write_bytes(publication.canonical(inspect_rows))
    identity=a['core']['entryAfter'];new=dict(identity,pid=identity['pid']+1000,startTicks=str(int(identity['startTicks'])+1000))
    (private/'identity.json').write_bytes(publication.canonical(dict(before=identity,after=new)))
    peer=private/'docker_protocol.py'
    peer.write_text('''import ast,json,sys
from pathlib import Path
root=Path(__file__).parent
if sys.argv[1]=='inspect':print((root/'inspect.json').read_text(encoding='utf-8'));raise SystemExit(0)
program=sys.stdin.read();identities=json.loads((root/'identity.json').read_bytes())
if 'dependency-supervised-reload' in program:print(json.dumps(identities['after']));raise SystemExit(0)
tree=ast.parse(program)
node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SPEC' for t in n.targets))
spec=json.loads(ast.literal_eval(node.value.args[0]))
if (root/'fail').exists() and spec['filePins'][0]['sha256']!='':
    print('local protocol error',file=sys.stderr);raise SystemExit(3)
identity=spec['expectedIdentity'];files=spec['filePins']
for pin in files:
    import hashlib
    raw=(root/'runtime'/pin['path'].removeprefix('/opt/intruoyi-spug/')).read_bytes()
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
out=dict(status='PASS',phase=spec['phase'],configurationWrites=False,backupDispatched=False,restoreDispatched=False,
 entryIdentity=identity,entryEnvironmentSha256=spec['expectedEnvironment'],filePins=files,configurationPins=spec['configurationPins'],
 importedSourcePins=[next(p for p in files if p['path']=='/opt/intruoyi-spug/'+n+'.py') for n in ('smallapp_entry','smallapp_adapter','smallapp_simple')],
 taskSnapshotSha256=spec['taskSnapshotSha256'],applicationCount=33,taskCount=3,historicalRouteCount=len(spec['historyBindings']),
 historicalFingerprintsUnchanged=True,originalAuditPreserved=True,freshProcessConfigurationParsed=True,liveUiVerified=False)
print(json.dumps(out))
''',encoding='utf-8')
    original_popen=subprocess.Popen
    def docker_protocol(argv,*args,**kwargs):
        if argv[0]==publication.DOCKER:argv=[sys.executable,'-X','utf8','-B',str(peer),*argv[1:]]
        return original_popen(argv,*args,**kwargs)
    monkeypatch.setattr(subprocess,'Popen',docker_protocol)
    before=predecessor_files(prepared);after={n:report['files']['ops/spug/'+n] for n in dependency.ALLOWED}
    diffref=put(task/'delta.json',delta(before,after,buildref));diffref=dict(file='delta.json',**{k:diffref[k] for k in ('bytes','sha256')})
    base=contract.Records(task);base_name='main-program-spug-verification-inputs-45dd7dc-r6-c1-v1.json'
    original=Path(__file__).parent/base_name;(task/base_name).write_bytes(original.read_bytes());base.read(base_name)
    # Reuse the already fully read real A/c1 fixture. Only its input reference
    # is supplied here; the actual bytes are identical to the committed B input.
    prepared=deepcopy(prepared);prepared['inputPin']=base.references[base_name]
    # This protocol fixture keeps old historical originals in their actual
    # TASK/PRIVATE, while all new transition files live in temp/task+private.
    # Invoke the real baseline reader with that explicit original scope; never fabricate
    # a successful baseline or widen the product reader's private boundary.
    import main_program_spug_publication_verify_only as verify
    read_baseline=verify.prepare_value
    def original_history_scope(records,private_scope,base_inputs,input_pin):
        assert base_inputs['schemaVersion']==verify.INPUT_SCHEMA
        historical=contract.Records(Path(__file__).resolve().parent)
        assert historical.pinned(input_pin)==base_inputs
        with monkeypatch.context() as original_paths:
            original_paths.setattr(publication,'RUNTIME',historical_runtime)
            return read_baseline(historical,Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106'),base_inputs,input_pin)
    monkeypatch.setattr(verify,'prepare_value',original_history_scope)
    # Exact external bind protocol maps only this test's product directory.
    for context in (prepared['c1'],prepared['dependency']['prepared']['c1']):
        for mount in context['mountObservation']['mounts']:
            if mount['Destination']=='/opt/intruoyi-spug':mount['Source']=str(runtime)
        context['mountObservation']['containerSnapshot']=publication.container_snapshot(inspect_rows[0])
    inputs=dict(schemaVersion=module.SCHEMA,baseVerificationInputsPin=base.references[base_name],resourceBuildPin=buildref,
        deploymentDeltaPin=diffref,observationPin=None,operationId='r1',outputFile='main-program-spug-resource-transition-'+report['sourceCommit'][:7]+'-r1.json')
    put(task/'inputs.json',inputs)
    record=contract.Records(task);record.read('inputs.json')
    value=module._prepare(record,private,inputs,record.references['inputs.json'],verify_checkout=True,allow_unobserved=True,base=prepared)
    inputs['observationPin']=module.observe_transition(private,value);put(task/'inputs.json',inputs)
    record=contract.Records(task);record.read('inputs.json')
    value=module._prepare(record,private,inputs,record.references['inputs.json'],verify_checkout=True,base=prepared)
    if failure:
        (private/'fail').write_bytes(b'1')
        with pytest.raises(ValueError,match='FAILED_CHECK_PRIVATE_EVIDENCE'):module.execute_transition(task,private,value)
        assert not (task/inputs['outputFile']).exists()
        evidence=json.loads((private/(value['stem']+'.private.json')).read_bytes())
        assert evidence['status']=='FAILED' and evidence['nativeReceiptPins']
        with pytest.raises(ValueError,match='ALREADY_ATTEMPTED'):module.execute_transition(task,private,value)
    else:
        result=module.execute_transition(task,private,value);assert result['status']=='PASS'
        records=contract.Records(task);records.read(inputs['outputFile']);reference=records.references[inputs['outputFile']]
        completed=module.load_completed_transition(records,private,reference,prepared)
        assert completed['afterFiles']==after and completed['entryAfter']==new
        import main_program_spug_publication_verify_only as verify
        v2=dict(schemaVersion='MainProgramSpugPublicationVerificationInputs/v2',baseVerificationInputsPin=inputs['baseVerificationInputsPin'],
            resourceTransitionPin=reference,verificationId='v2',outputFile=prepared['inputs']['outputFile'].replace('-v1.json','-v2.json'))
        view=verify.prepare_transition_verification(records,private,v2,None,prepared)
        assert view['resourceTransition']['entryAfter']==new and verify.command_arguments(view,'spug-verify')[1]==570
        assert verify.binding(view)['resourceTransitionPin']==reference
        with pytest.raises(ValueError,match='INPUTS_INVALID'):
            verify.prepare_transition_verification(records,private,dict(v2,extra=True),None,prepared)
        archive=private/(value['stem']+'-originals')/'0-before.py'
        assert archive.exists();archive.write_bytes(b'tampered')
        with pytest.raises(ValueError):module.load_completed_transition(contract.Records(task),private,reference,prepared)


# The following cases read the real completed installation, never synthesize a
# PASS installation. Only new consumer metadata lives in exclusive test files.
@pytest.fixture(scope='module')
def installed_reader_history():
    import main_program_spug_publication_verify_only as verify
    task=Path(__file__).resolve().parent;private=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
    records=contract.Records(task);name='main-program-spug-resource-transition-5651efc-r1.json'
    core=records.read(name);reference=records.references[name]
    attempt=json.loads(publication.verify_bytes(core['attemptPin']))
    old=next(p for p in attempt['inputPins'] if p['path']==str(Path(subject().__file__).resolve()))
    kept=private/('spug-resource-transition-reader-'+old['sha256']+'.py')
    assert publication.verify_bytes(publication.file_pin(kept))==publication.verify_bytes(dict(old,path=str(kept)))
    base=verify.prepare_verification(task,private,'main-program-spug-verification-inputs-45dd7dc-r6-c1-v1.json')
    return task,private,core,reference,attempt,old,publication.file_pin(kept),base


def consumer_metadata(task,wrapper,base_pin):
    import uuid
    from contextlib import contextmanager
    @contextmanager
    def files():
        names=['test-reader-custody-'+uuid.uuid4().hex+'.json','test-reader-inputs-'+uuid.uuid4().hex+'.json']
        try:
            raw=publication.canonical(wrapper)
            with (task/names[0]).open('xb') as stream:stream.write(raw)
            ref=dict(file=names[0],**content(raw))
            value=dict(schemaVersion='MainProgramSpugPublicationVerificationInputs/v2',baseVerificationInputsPin=base_pin,
                resourceTransitionPin=ref,verificationId='v3',
                outputFile='main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v3.json')
            with (task/names[1]).open('xb') as stream:stream.write(publication.canonical(value))
            yield names,ref
        finally:
            for name in names:
                path=task/name
                if path.exists():path.unlink()
    return files()


def reader_custody(history):
    _,_,core,ref,_,old,kept,_=history
    return dict(schemaVersion='MainProgramSpugResourceTransitionReaderCustody/v1',transitionCorePin=ref,
        attemptPin=core['attemptPin'],originalReaderPin=old,preservedReaderPin=kept,
        currentReaderPin=publication.file_pin(subject().__file__))


def test_actual_nested_b_scope_matches_the_exact_original_attempt(installed_reader_history):
    # The old direct reader remains valid only before its physical source changes.
    # This exact real v2 entry first reproduces the 1142/1141 scope defect; the
    # post-upgrade explicit rejection is separately checked below.
    import main_program_spug_publication_verify_only as verify
    task,private,_,_,_,old,_,_=installed_reader_history
    if publication.file_pin(subject().__file__)!=old:
        with pytest.raises(ValueError,match='READER_CUSTODY_REQUIRED'):
            verify.prepare_verification(task,private,'main-program-spug-verification-inputs-45dd7dc-r6-c1-v2.json')
    else:
        value=verify.prepare_verification(task,private,'main-program-spug-verification-inputs-45dd7dc-r6-c1-v2.json')
        assert value['resourceTransition']['entryAfter']['pid']==152321


def test_explicit_reader_custody_real_nested_b_entry_and_complete_closure(installed_reader_history):
    import main_program_spug_publication_verify_only as verify
    task,private,core,reference,attempt,old,kept,base=installed_reader_history
    wrapper=reader_custody(installed_reader_history)
    original_raw=publication.verify_bytes(old if old==publication.file_pin(subject().__file__) else dict(old,path=kept['path']))
    before={p['path']:publication.verify_bytes(p) for p in [core['attemptPin'],core['privateEvidencePin'],attempt['gatePin']]}
    with consumer_metadata(task,wrapper,core['baseVerificationInputsPin']) as (names,ref):
        value=verify.prepare_verification(task,private,names[1])
        assert value['resourceTransition']['entryAfter']==core['entryAfter']
        pins={p['path']:p for p in value['inputPins']}
        for pin in [kept,wrapper['currentReaderPin'],core['attemptPin'],core['privateEvidencePin']]:assert pins[pin['path']]==pin
        assert pins[str(task/names[0])]['sha256']==ref['sha256'] and str(task/names[1]) in pins
        assert verify.binding(value)['resourceTransitionPin']==ref
        assert verify.command_arguments(value,'spug-verify')[1]==570
        assert all(publication.verify_bytes(dict(path=p,**content(raw)))==raw for p,raw in before.items())
        assert publication.verify_bytes(kept)==original_raw


@pytest.mark.parametrize('bad',['extra','recursive','attempt','original-path','original-pin','preserved','current'])
def test_reader_custody_rejects_cross_binding_and_byte_drift(installed_reader_history,bad,tmp_path):
    task,private,core,ref,_,old,kept,base=installed_reader_history
    wrapper=reader_custody(installed_reader_history)
    if bad=='extra':wrapper['extra']=True
    elif bad=='attempt':wrapper['attemptPin']=core['privateEvidencePin']
    elif bad=='original-path':wrapper['originalReaderPin']=dict(old,path=str(task/'main_program_spug_publication_verify_only.py'))
    elif bad=='original-pin':wrapper['originalReaderPin']=dict(old,sha256='0'*64)
    elif bad=='preserved':wrapper['preservedReaderPin']=dict(kept,sha256='0'*64)
    elif bad=='current':wrapper['currentReaderPin']=dict(wrapper['currentReaderPin'],sha256='0'*64)
    with consumer_metadata(task,wrapper,core['baseVerificationInputsPin']) as (names,reference):
        if bad=='recursive':
            # A second public wrapper is an actual file; no recursive resolution.
            nested=dict(wrapper,transitionCorePin=reference)
            with consumer_metadata(task,nested,core['baseVerificationInputsPin']) as (_,recursive_ref):
                with pytest.raises(ValueError,match='READER_CUSTODY_CORE_INVALID'):
                    subject().load_completed_transition(contract.Records(task),private,recursive_ref,base)
        else:
            with pytest.raises(ValueError,match='READER_CUSTODY_'):
                subject().load_completed_transition(contract.Records(task),private,reference,base)
