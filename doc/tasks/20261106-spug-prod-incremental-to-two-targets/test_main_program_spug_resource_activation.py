"""Local contracts only; transport replies never prove a live deployment."""
from copy import deepcopy
import ast
import hashlib
import importlib.util
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType,SimpleNamespace

import pytest

import main_program_spug_publication as publication
import main_program_spug_resource_activation as subject


def put(path, value):
    path.write_bytes(publication.canonical(value))
    reference = publication.file_pin(path)
    return dict(file=path.name, bytes=reference['bytes'], sha256=reference['sha256'])


def digest(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def observation(files):
    def pin(path): return dict(path=path, **digest(b'fixture'))
    identity = dict(pid=123, startTicks='456', argv=['python3','-B','/opt/intruoyi-spug/smallapp_entry.py'],
        parentPid=1, cwd='/data/spug/spug_api', executable='/usr/local/bin/python3.8',
        supervisorStartTicks='1')
    return dict(schemaVersion='MainProgramSpugResourceActivationObservation/v1', sourceCommit='a'*40,
        spug=dict(containerId=publication.CONTAINER, containerSnapshot={'id':publication.CONTAINER},
            protectedContainerId='b'*64, protectedContainerSnapshot={'id':'b'*64}, entryPid=123,
            settings={k:pin(p) for k,p in publication.SETTINGS.items()}, connections={'connection.json':pin('/run/intruoyi-spug/connection.json')},
            productPins=[dict(path='/opt/intruoyi-spug/'+n, **(digest(b'# old adapter') if n=='smallapp_adapter.py' else files['ops/spug/'+n]))
                         for n in publication.PRODUCT_FILES], taskSnapshotSha256='c'*64),
        entryIdentity=identity, supervisorPin=pin('/etc/supervisord.conf'), nginxPin=pin('/etc/nginx/nginx.conf'),
        modulePins=[dict(path='/opt/intruoyi-spug/'+n,**(digest(b'# old adapter') if n=='smallapp_adapter.py' else
            files['ops/spug/'+n] if n=='smallapp_entry.py' else digest(b'fixture')))
            for n in ('smallapp_entry.py','smallapp_adapter.py','smallapp_simple.py')], credentialPins=[pin('/run/intruoyi-spug/auth.json')],
        routeFingerprints={'root':'c'*64}, catalogueSourceRef='existing-source', catalogueSha256='d'*64,
        historySha256='e'*64, ledgerPins=[])


@pytest.fixture
def resource(tmp_path):
    """Real Git + actual pytest proof, with explicit tiny resource protocol inputs."""
    task=tmp_path/'task'; private=tmp_path/'private'; root=tmp_path/'resource'; runtime=tmp_path/'runtime'
    for path in (task,private,root,runtime): path.mkdir()
    files={}
    for name in publication.PRODUCT_FILES:
        raw=b'# new adapter\n' if name=='smallapp_adapter.py' else b'# unchanged resource\n'
        path=root/'ops/spug'/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
        files['ops/spug/'+name]=digest(raw)
        current=runtime/name; current.parent.mkdir(parents=True,exist_ok=True)
        current.write_bytes(b'# old adapter' if name=='smallapp_adapter.py' else raw)
    test='doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archived_source_catalogue_routing.py'
    p=root/test; p.parent.mkdir(parents=True); p.write_text(
        "from pathlib import Path\ndef test_actual_fixture_bytes():\n    assert Path('ops/spug/smallapp_adapter.py').read_bytes() == b'# new adapter\\n'\n",encoding='utf-8')
    def git(*args):
        return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True).stdout.decode().strip()
    git('init'); git('config','user.name','Contract Fixture'); git('config','user.email','fixture@example.invalid')
    git('config','core.autocrlf','false'); git('add','.'); git('commit','-m','local contract fixture')
    commit=git('rev-parse','HEAD')
    result=subprocess.run([sys.executable,'-B','-c',
        "import sys,pytest; sys.stdout.reconfigure(newline='\\n'); sys.stderr.reconfigure(newline='\\n'); raise SystemExit(pytest.main(sys.argv[1:]))",
        '-q','-p','no:cacheprovider',test],
        cwd=root,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),check=True)
    log=private/'actual-fixture-tests.log'; log.write_bytes(result.stdout+result.stderr)
    proof=dict(schemaVersion='TaskSpugResourceValidation/v1',status='PASS',actualExitCode=0,actualPassed=1,actualSkipped=0,
        inputPins={name:row['sha256'] for name,row in files.items()},logPin=publication.file_pin(log))
    proof['inputPins'][test]=publication.file_pin(p)['sha256']
    report=dict(schemaVersion='MainProgramSpugResourceBuild/v1',status='PASS',sourceCommit=commit,worktree=str(root),
        fileCount=11,files=files,changedFiles=['ops/spug/smallapp_adapter.py'],selectionConnectionsSupported=True,
        historyRoutesPreserved=True,testEvidencePin=put(task/'tests.json',proof))
    observed=observation(files); observed['sourceCommit']=commit
    op=private/'observation.private.json'; put(op,observed)
    inputs=dict(schemaVersion='MainProgramSpugResourceActivationInputs/v1',resourceBuildPin=put(task/'resource.json',report),
        observationPin=publication.file_pin(op))
    put(task/'inputs.json',inputs)
    return task,private,root,runtime,report,observed,inputs


def prepared(resource):
    task,private,_,runtime,_,_,_=resource
    spec=subject.prepare(task,private,'inputs.json'); spec['runtime']=str(runtime)
    return spec


class Transport:
    """Explicit external protocol boundary; no Docker commands are performed."""
    def __init__(self, observed): self.observed=deepcopy(observed); self.calls=[]; self.failure=None
    def observe(self): self.calls.append('observe'); return deepcopy(self.observed)
    def reload(self, expected):
        self.calls.append('reload')
        if self.failure: raise RuntimeError(self.failure)
        assert self.observed['entryIdentity']==expected
        self.observed['entryIdentity'].update(pid=124,startTicks='457'); self.observed['spug']['entryPid']=124
        return deepcopy(self.observed['entryIdentity'])


def test_default_prepare_has_no_transport(resource):
    task,private,*_=resource; transport=Transport({})
    assert subject.run_request(task,private,'inputs.json',transport=transport)['status']=='PREPARED'
    assert transport.calls==[] and not subject.parser().parse_args(['--inputs','inputs.json']).apply


@pytest.mark.parametrize('apply',[False,True])
def test_missing_inputs_never_dispatch(tmp_path,apply):
    transport=Transport({})
    with pytest.raises((OSError,ValueError)):
        subject.run_request(tmp_path,tmp_path,'missing.json',apply=apply,transport=transport)
    assert transport.calls==[]


def test_observation_requires_explicit_mode_and_is_never_overwritten(resource):
    task,private,_,_,_,obs,inputs=resource;inputs['observationPin']=None;put(task/'inputs.json',inputs)
    transport=Transport(obs)
    with pytest.raises(ValueError,match='OBSERVATION_REQUIRED'):
        subject.run_request(task,private,'inputs.json',transport=transport)
    assert transport.calls==[]
    result=subject.run_request(task,private,'inputs.json',observe=True,transport=transport)
    assert result['status']=='OBSERVED' and result['runtimeWrites'] is False and transport.calls==['observe']
    original=Path(result['observationPin']['path']).read_bytes()
    with pytest.raises(ValueError,match='OBSERVATION_EXISTS'):
        subject.run_request(task,private,'inputs.json',observe=True,transport=transport)
    assert transport.calls==['observe'] and Path(result['observationPin']['path']).read_bytes()==original


def test_build_is_really_pinned_clean_committed_and_tested(resource):
    task,private,root,_,report,_,_=resource
    spec=subject.prepare(task,private,'inputs.json')
    assert spec['resource']['sourceCommit']==report['sourceCommit']
    assert {str(task/'resource.json'),str(task/'tests.json')} <= {p['path'] for p in spec['inputPins']}
    (root/'ops/spug/smallapp_entry.py').write_bytes(b'drift')
    with pytest.raises(ValueError,match='RESOURCE_BUILD'):
        subject.prepare(task,private,'inputs.json')


def test_non_adapter_resource_change_is_rejected(resource):
    task,private,_,_,_,obs,inputs=resource
    obs['spug']['productPins'][0]['sha256']='f'*64
    put(Path(inputs['observationPin']['path']),obs); inputs['observationPin']=publication.file_pin(inputs['observationPin']['path'])
    put(task/'inputs.json',inputs)
    with pytest.raises(ValueError,match='NON_ADAPTER'):
        subject.prepare(task,private,'inputs.json')


@pytest.mark.parametrize('field',['settings','protectedContainerSnapshot','connections'])
def test_fresh_drift_has_no_file_change_or_signal(resource,field):
    task,private,_,runtime,_,obs,_=resource; spec=prepared(resource); transport=Transport(obs)
    transport.observed['spug'][field]={}
    before=(runtime/'smallapp_adapter.py').read_bytes()
    with pytest.raises(ValueError): subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert transport.calls==['observe'] and (runtime/'smallapp_adapter.py').read_bytes()==before


def test_single_atomic_file_preserves_original_and_forbids_repeat(resource):
    task,private,root,runtime,report,obs,_=resource; spec=prepared(resource); transport=Transport(obs)
    before={n:(runtime/n).read_bytes() for n in publication.PRODUCT_FILES}
    original_reload=transport.reload
    def reload(expected):
        result=original_reload(expected)
        transport.observed['spug']['productPins']=[dict(path='/opt/intruoyi-spug/'+n,**report['files']['ops/spug/'+n]) for n in publication.PRODUCT_FILES]
        next(p for p in transport.observed['modulePins'] if p['path'].endswith('/smallapp_adapter.py')).update(report['files']['ops/spug/smallapp_adapter.py'])
        return result
    transport.reload=reload
    result=subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert result['status']=='PASS' and transport.calls==['observe','reload','observe']
    assert (runtime/'smallapp_adapter.py').read_bytes()==(root/'ops/spug/smallapp_adapter.py').read_bytes()
    assert all((runtime/n).read_bytes()==raw for n,raw in before.items() if n!='smallapp_adapter.py')
    assert list(private.rglob('adapter-before.py'))[0].read_bytes()==before['smallapp_adapter.py']
    prior=list(transport.calls)
    with pytest.raises(ValueError,match='ATTEMPT'): subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert transport.calls==prior


def test_reload_failure_keeps_replaced_bytes_and_private_stage(resource):
    task,private,root,runtime,_,obs,_=resource; spec=prepared(resource); transport=Transport(obs);transport.failure='fixture reload failed'
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):
        subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert (runtime/'smallapp_adapter.py').read_bytes()==(root/'ops/spug/smallapp_adapter.py').read_bytes()
    reports=[json.loads(p.read_bytes()) for p in private.glob('*activation*.private.json')]
    assert any(r['status']=='FAILED' and r['adapterReplaced'] is True and r['stage']=='reload-entry' for r in reports)
    assert not list(task.glob('main-program-spug-resource-activation-*.json'))
    prior=list(transport.calls)
    with pytest.raises(ValueError,match='ATTEMPT'):subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert transport.calls==prior


def test_required_module_origin_cannot_be_omitted(resource):
    _,_,_,_,report,obs,_=resource;obs['modulePins']=[]
    with pytest.raises(ValueError,match='MODULE'):subject.validate_observation(obs,report)


@pytest.mark.parametrize('change',['old-bytes','hardlink','staged'])
def test_real_file_preflight_blocks_drift_alias_or_pending(resource,change):
    task,private,_,runtime,report,obs,_=resource;spec=prepared(resource);transport=Transport(obs)
    active=runtime/'smallapp_adapter.py'
    if change=='old-bytes':active.write_bytes(b'changed by another owner')
    elif change=='hardlink':os.link(active,runtime/'alias.py')
    else:active.with_name(active.name+'.main-program-'+report['sourceCommit'][:7]+'.pending').write_bytes(b'prior attempt')
    raw=active.read_bytes()
    with pytest.raises(ValueError):subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    assert 'reload' not in transport.calls and active.read_bytes()==raw


def test_error_after_atomic_replace_records_actual_write(resource,monkeypatch):
    task,private,root,runtime,_,obs,_=resource;spec=prepared(resource);transport=Transport(obs)
    replace=publication.replace_once
    def fail_after(*args):
        replace(*args)
        raise OSError('explicit post-replace storage boundary failure')
    monkeypatch.setattr(publication,'replace_once',fail_after)
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    report=json.loads(next(private.glob('*activation*.private.json')).read_bytes())
    assert report['status']=='FAILED' and report['adapterReplaced'] is True
    assert report['stage']=='replace-adapter' and transport.calls==['observe']
    assert (runtime/'smallapp_adapter.py').read_bytes()==(root/'ops/spug/smallapp_adapter.py').read_bytes()


def test_post_reload_drift_never_produces_pass(resource):
    task,private,_,_,report,obs,_=resource;spec=prepared(resource);transport=Transport(obs)
    original=transport.reload
    def reload(expected):
        identity=original(expected)
        transport.observed['spug']['productPins']=[dict(path='/opt/intruoyi-spug/'+n,**report['files']['ops/spug/'+n]) for n in publication.PRODUCT_FILES]
        next(p for p in transport.observed['modulePins'] if p['path'].endswith('/smallapp_adapter.py')).update(report['files']['ops/spug/smallapp_adapter.py'])
        transport.observed['spug']['settings']['entry']['sha256']='f'*64
        return identity
    transport.reload=reload
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):subject.dispatch_prepared(task,private,spec,apply=True,transport=transport)
    report=json.loads(next(private.glob('*activation*.private.json')).read_bytes())
    assert report['status']=='FAILED' and report['adapterReplaced'] is True and report['entryReloaded'] is True
    assert not list(task.glob('main-program-spug-resource-activation-*.json'))


@pytest.mark.parametrize('change',['same-pid','same-start','parent','argv'])
def test_successor_process_must_keep_original_ownership(change):
    files={'ops/spug/'+n:digest(b'fixture') for n in publication.PRODUCT_FILES};obs=observation(files)
    identity=dict(obs['entryIdentity'],pid=124,startTicks='457')
    if change=='same-pid':identity['pid']=123
    if change=='same-start':identity['startTicks']='456'
    if change=='parent':identity['parentPid']=77
    if change=='argv':identity['argv']=['python3','other.py']
    with pytest.raises(ValueError,match='NEW_ENTRY_IDENTITY'):
        subject.expected_after(dict(observation=obs,resource={'files':files}),identity)


def test_output_scripts_compile_without_executing():
    compile(subject.OBSERVE_PROGRAM,'observe','exec')
    compile(subject.reload_program(dict(pid=123,startTicks='45',argv=['python3','-B','/opt/intruoyi-spug/smallapp_entry.py'],
        parentPid=1,cwd='/data/spug/spug_api',executable='/usr/bin/python3',supervisorStartTicks='1')),'reload','exec')
    assert 'nginx -s' not in subject.OBSERVE_PROGRAM and 'docker restart' not in subject.OBSERVE_PROGRAM


def generated_observer():
    """Capture the actual program at its dedicated observation transport seam."""
    from unittest.mock import patch
    captured=[]
    class Captured(Exception):pass
    class CaptureOperation:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def run(self,program):captured.append(program);raise Captured()
    class CaptureTransport(subject.ActualTransport):
        def instances(self,operation=None):return {}
    with patch.object(subject.observation_lifecycle,'Observation',CaptureOperation):
        with pytest.raises(Captured):
            CaptureTransport(Path(__file__).parent,dict(resource=dict(sourceCommit='a'*40),inputPins=[])).observe()
    assert len(captured)==1
    return captured[0]


@pytest.mark.parametrize('changed_command',[False,True])
def test_generated_observer_initializes_before_real_task_readback(tmp_path,monkeypatch,changed_command):
    """Execute the generated observer body with real product task validation.

    Django/ORM, config and proc are explicit external protocol fixtures. Task
    rows are real local bytes. Neither initialize_spug nor installed_task is
    stubbed, and reaching the following directory boundary is not deployment.
    """
    root=Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root/'ops/spug'))
    spec=importlib.util.spec_from_file_location('smallapp_entry',root/'ops/spug/smallapp_entry.py')
    entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
    monkeypatch.setitem(sys.modules,'smallapp_entry',entry)
    import smallapp_simple as simple
    adapter=entry.adapter
    config={'tasks':{action:index for index,action in enumerate(entry.ACTIONS,1)}}
    rows=[dict(id=index,is_active=False,command=entry.PREFIX+action,interpreter='sh',targets='["local"]')
          for action,index in config['tasks'].items()]
    if changed_command:rows[1]['command']='different task command'
    path=tmp_path/'actual-task-protocol.json';path.write_text(json.dumps(rows),encoding='utf-8')
    events=[]
    class Manager:
        def filter(self,*,pk):
            events.append(('task',pk))
            matches=[SimpleNamespace(**row) for row in json.loads(path.read_bytes()) if row['id']==pk]
            return SimpleNamespace(first=lambda:matches[0] if matches else None)
    def setup():
        assert os.environ['DJANGO_SETTINGS_MODULE']=='spug.settings'
        assert '/data/spug/spug_api' in sys.path
        events.append(('setup',None))
        for name in ('apps','apps.schedule','apps.schedule.models'):
            module=ModuleType(name);module.__path__=[];monkeypatch.setitem(sys.modules,name,module)
        sys.modules['apps.schedule.models'].Task=SimpleNamespace(objects=Manager())
    for name in ('apps','apps.schedule','apps.schedule.models'):monkeypatch.delitem(sys.modules,name,raising=False)
    django=ModuleType('django');django.setup=setup;monkeypatch.setitem(sys.modules,'django',django)
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE','before-fixture')
    monkeypatch.setattr(sys,'dont_write_bytecode',True)
    monkeypatch.setattr(entry,'settings',lambda:config)
    monkeypatch.setattr(simple,'configuration',lambda:{'boundary':'explicit external config fixture'})
    class AfterTaskReadback(Exception):pass
    def directory_boundary(_):raise AfterTaskReadback()
    monkeypatch.setattr(adapter,'read_json',directory_boundary)
    import configparser
    class Supervisor:
        def read(self,*args,**kwargs):pass
        def get(self,section,key,**kwargs):
            assert section=='program:intruoyi-spug-backup-entry'
            return dict(command='python3 -B /opt/intruoyi-spug/smallapp_entry.py',
                directory='/data/spug/spug_api',autorestart='unexpected',exitcodes='0')[key]
    monkeypatch.setattr(configparser,'RawConfigParser',Supervisor)
    tree=ast.parse(generated_observer())
    for index,node in enumerate(tree.body):
        if isinstance(node,ast.FunctionDef) and node.name=='process_identity':
            tree.body[index]=ast.copy_location(ast.Assign(targets=[ast.Name(id='process_identity',ctx=ast.Store())],
                value=ast.Name(id='_observe_process_protocol',ctx=ast.Load())),node)
    ast.fix_missing_locations(tree)
    namespace={'_observe_process_protocol':lambda:{'pid':123}}
    if changed_command:
        with pytest.raises(adapter.Refused,match='SPUG_MANUAL_TEMPLATE_CHANGED'):
            exec(compile(tree,'actual-generated-observer','exec'),namespace)
        assert events==[('setup',None),('task',1),('task',2)]
    else:
        with pytest.raises(AfterTaskReadback):exec(compile(tree,'actual-generated-observer','exec'),namespace)
        assert events==[('setup',None),('task',1),('task',2),('task',3)]


@pytest.mark.parametrize('registered',[True,False])
def test_generated_directory_uses_only_registered_current_source(monkeypatch,registered):
    """Execute the generated directory body through real product validation."""
    root=Path(__file__).resolve().parents[3];monkeypatch.syspath_prepend(str(root/'ops/spug'))
    spec=importlib.util.spec_from_file_location('smallapp_entry',root/'ops/spug/smallapp_entry.py')
    entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
    adapter=entry.adapter;current=publication.SOURCES[0];retired='retired-root-source'
    binding=dict(sourceConfigRefs=[retired],sourceConnections={current:'current.json',
        **{'retired-source-'+str(i):'retired-'+str(i)+'.json' for i in range(30)}},targetConnections={})
    if not registered:del binding['sourceConnections'][current]
    config=dict(applications=[dict(applicationId='current-app',sourceConfigRef=current,targetConfigRefs=[]),
        dict(applicationId='retired-app',sourceConfigRef=retired,targetConfigRefs=[])])
    monkeypatch.setattr(adapter,'read_json',lambda path:binding)
    calls=[]
    class Bridge:
        fingerprint='f'*64
        def __init__(self,source_ref=None,target_ref=None):self.source=source_ref
        def selections(self):
            calls.append(self.source)
            assert self.source==current,'retired source must never be queried'
            return dict(observedAt=datetime.now(timezone.utc).isoformat(),applications=[dict(applicationId='current-app',
                sourceConfigRef=current,engineSelectionRef='fixture-engine',fullReady=True,fullErrorCode=None,
                parentChainRefs=['fixture-point'],recoveryPointRefs=['fixture-point'],freshTargetConfigRefs=[],historyErrorCode=None)])
    monkeypatch.setattr(adapter,'HttpBridge',Bridge)
    class AfterCatalogueReadback(Exception):pass
    class Manager:
        def order_by(self,*args):raise AfterCatalogueReadback()
    for name in ('apps','apps.schedule','apps.schedule.models'):
        module=ModuleType(name);module.__path__=[];monkeypatch.setitem(sys.modules,name,module)
    sys.modules['apps.schedule.models'].Task=SimpleNamespace(objects=Manager())
    sys.modules['apps.schedule.models'].History=SimpleNamespace()
    tree=ast.parse(generated_observer())
    start=next(i for i,node in enumerate(tree.body) if isinstance(node,ast.Assign) and
        any(isinstance(target,ast.Name) and target.id=='binding' for target in node.targets))
    prefix=[node for node in tree.body[:start] if isinstance(node,ast.Assign) and
        any(isinstance(target,ast.Name) and target.id=='ORIGINAL_SOURCE' for target in node.targets)]
    tree.body=prefix+tree.body[start:]
    namespace=dict(entry=entry,adapter=adapter,config=config,need=subject.need,Path=Path,
        file_pin=lambda path:dict(path=path,bytes=1,sha256='a'*64))
    if registered:
        with pytest.raises(AfterCatalogueReadback):exec(compile(tree,'actual-generated-directory','exec'),namespace)
        assert calls==[current]
    else:
        with pytest.raises(ValueError,match='ORIGINAL_CATALOGUE_SOURCE_NOT_REGISTERED'):
            exec(compile(tree,'actual-generated-directory','exec'),namespace)
        assert calls==[]


def observation_budget_transport(tmp_path,monkeypatch=None,*,drift=False,error=None):
    """Explicit Docker protocol boundary; actual instance/observe/reload methods run."""
    files={'ops/spug/'+name:digest(b'fixture') for name in publication.PRODUCT_FILES}
    observed=observation(files)
    rows=[]
    for identifier,port,name in ((publication.CONTAINER,'18080','/intruoyi-spug-transfer-spug-1'),
        ('b'*64,'18081','/protected-unrelated')):
        rows.append(dict(Id=identifier,Name=name,Image='sha256:'+('a'*64),RestartCount=0,
            State=dict(Running=True,Paused=False,Restarting=False,Pid=42,StartedAt='fixed-start',FinishedAt='fixed-finish'),
            Path='supervisord',Args=[],Config={},HostConfig={'PortBindings':{'80/tcp':[{'HostIp':'127.0.0.1','HostPort':port}]}},
            Mounts=[dict(Destination='/opt/intruoyi-spug',Source=publication.RUNTIME)]))
    observed['spug'].update(containerSnapshot=publication.container_snapshot(rows[0]),
        protectedContainerSnapshot=publication.container_snapshot(rows[1]))
    result={key:deepcopy(value) for key,value in observed.items() if key not in ('schemaVersion','sourceCommit','spug')}
    result.update({key:deepcopy(observed['spug'][key]) for key in
        ('entryPid','settings','connections','productPins','taskSnapshotSha256')})
    class BudgetTransport(subject.ActualTransport):
        def __init__(self):
            super().__init__(tmp_path,dict(resource=dict(sourceCommit=observed['sourceCommit'],files=files),observation=observed,inputPins=[]))
            self.calls=[];self.inspect_count=0;self.reply=result
        def command(self,*args,input=None,timeout=240):
            self.calls.append((args,timeout))
            if args==('ps','-aq','--no-trunc'):
                assert input is None
                return ('\n'.join(row['Id'] for row in rows)).encode('utf-8')
            if args==('inspect',*(row['Id'] for row in rows)):
                assert input is None
                self.inspect_count+=1;actual=deepcopy(rows)
                if drift and self.inspect_count==2:actual[0]['Image']='sha256:'+('c'*64)
                return publication.canonical(actual)
            assert args==('exec','-i',publication.CONTAINER,'python3','-B','-')
            compile(input.decode('utf-8'),'actual-transport-program','exec')
            if error is not None:raise ValueError(error)
            return publication.canonical(self.reply)
    transport=BudgetTransport()
    if monkeypatch is not None:
        class Operation:
            def __init__(self,private,identity):
                assert identity==dict(sourceCommit=observed['sourceCommit'],inputPins=[])
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def short_command(self,command,*args):return command(*args,timeout=240)
            def run(self,program):
                compile(program,'actual-observation-program','exec')
                transport.calls.append((('complete-observer',),(900,1800)))
                if error is not None:raise ValueError(error)
                return publication.canonical(transport.reply)
        monkeypatch.setattr(subject.observation_lifecycle,'Observation',Operation)
    return transport,observed


def test_observation_transport_uses_dedicated_idle_and_hard_budget(tmp_path,monkeypatch):
    transport,expected=observation_budget_transport(tmp_path,monkeypatch)
    assert transport.observe()==expected
    assert [args[0] for args,_ in transport.calls]==['ps','inspect','complete-observer','ps','inspect']
    assert [timeout for _,timeout in transport.calls]==[240,240,(900,1800),240,240]
    assert list(tmp_path.iterdir())==[]


def test_reload_transport_keeps_default_240_budget(tmp_path):
    transport,observed=observation_budget_transport(tmp_path)
    successor=dict(observed['entryIdentity'],pid=124,startTicks='457')
    transport.reply=successor
    assert transport.reload(observed['entryIdentity'])==successor
    assert [args[0] for args,_ in transport.calls]==['ps','inspect','exec','ps','inspect']
    assert [timeout for _,timeout in transport.calls]==[240]*5
    assert list(tmp_path.iterdir())==[]


def test_observation_transport_preserves_post_observation_instance_guard(tmp_path,monkeypatch):
    transport,_=observation_budget_transport(tmp_path,monkeypatch,drift=True)
    with pytest.raises(ValueError,match='INSTANCE_CHANGED_DURING_OBSERVATION'):
        transport.observe()
    assert [timeout for _,timeout in transport.calls]==[240,240,(900,1800),240,240]
    assert list(tmp_path.iterdir())==[]


def test_observation_transport_keeps_timeout_error_without_retry(tmp_path,monkeypatch):
    transport,_=observation_budget_transport(tmp_path,monkeypatch,error='MAIN_SPUG_DOCKER_COMMAND_TIMEOUT')
    with pytest.raises(ValueError,match='^MAIN_SPUG_DOCKER_COMMAND_TIMEOUT$'):
        transport.observe()
    assert [args[0] for args,_ in transport.calls]==['ps','inspect','complete-observer']
    assert [timeout for _,timeout in transport.calls]==[240,240,(900,1800)]
    assert list(tmp_path.iterdir())==[]
