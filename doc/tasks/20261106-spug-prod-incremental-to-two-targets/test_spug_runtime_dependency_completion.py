"""Local real-file contracts; never dispatch Docker, SSH or business operations."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import os
import subprocess
import sys

import pytest

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
BUILD = json.loads((TASK/'spug-resource-build-c7728ad.json').read_text(encoding='utf-8'))
SOURCE = Path(BUILD['worktree'])/'ops/spug'
RUNTIME = Path('C:/Spug/runtime/ops/spug')
SETTINGS = PRIVATE/'spug-runtime-dependency-test-settings-c1.private.json'
OLD_SIMPLE = PRIVATE/'spug-runtime-dependency-old-simple-r1.private.py'
ADDITIONS = ('smallapp_simple.py','smallapp_progress_remote.py','smallapp-ui/preview/style.css')
FILES = tuple(name.removeprefix('ops/spug/') for name in BUILD['files']) + ADDITIONS


def subject():
    return importlib.import_module('spug_runtime_dependency_completion')


@pytest.fixture
def source(tmp_path):
    root=tmp_path/'source';root.mkdir()
    for name in FILES:
        destination=root/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(SOURCE/name,destination)
    return root


def real_simple(root, settings_path):
    saved=sys.modules.get('smallapp_adapter')
    try:
        spec=importlib.util.spec_from_file_location('smallapp_adapter',root/'smallapp_adapter.py')
        adapter=importlib.util.module_from_spec(spec);sys.modules['smallapp_adapter']=adapter;spec.loader.exec_module(adapter)
        spec=importlib.util.spec_from_file_location('contract_simple',root/'smallapp_simple.py')
        simple=importlib.util.module_from_spec(spec);spec.loader.exec_module(simple);simple.CONFIG=settings_path
        return simple.configuration(),simple.public_configuration()
    finally:
        if saved is None:sys.modules.pop('smallapp_adapter',None)
        else:sys.modules['smallapp_adapter']=saved


def test_actual_old_parser_reproduces_c1_failure_without_network(tmp_path):
    raw=SETTINGS.read_bytes()
    assert len(raw)==55106 and hashlib.sha256(raw).hexdigest()=='a915ba94553de5817674e7af79f09a3da83fe44279fcb12155c82f107392d935'
    path=tmp_path/'settings.json';path.write_bytes(raw)
    old=tmp_path/'old';old.mkdir();old_bytes=OLD_SIMPLE.read_bytes()
    assert len(old_bytes)==6431 and hashlib.sha256(old_bytes).hexdigest()=='0c44e4d058dafab71bbd27c34eac4205b9a7e0ef93b80379be8b89226d05efab'
    (old/'smallapp_simple.py').write_bytes(old_bytes)
    shutil.copyfile(SOURCE/'smallapp_adapter.py',old/'smallapp_adapter.py')
    with pytest.raises(Exception,match='^SIMPLE_CONFIGURATION_INVALID$') as rejected:
        real_simple(old,path)
    assert type(rejected.value).__name__=='Refused'
    original=json.loads(raw);actual,public=real_simple(SOURCE,path)
    assert actual==original and public['catalogueRestoreBindings']==original['catalogueRestoreBindings']
    assert [b['selectable'] for b in public['bindings']]==[b['selectable'] for b in original['bindings']]


def test_actual_entry_graph_contains_three_missing_runtime_dependencies(source):
    graph=subject().inspect_runtime_dependencies(source)
    assert set(graph['files'])==set(FILES)
    assert graph['additionalFiles']==sorted(ADDITIONS)
    assert {'from':'smallapp_simple.py','kind':'EXECUTED_FILE','to':'smallapp_progress_remote.py'} in graph['edges']
    assert {'from':'smallapp-ui/index.html','kind':'WEB_RESOURCE','to':'smallapp-ui/preview/style.css'} in graph['edges']


def test_old_eleven_file_manifest_is_not_a_closed_runtime(source):
    with pytest.raises(ValueError,match='DEPENDENCY_MANIFEST_INCOMPLETE'):
        subject().validate_manifest_coverage(source,BUILD['files'])


def test_complete_manifest_requires_actual_file_hashes(source):
    graph=subject().inspect_runtime_dependencies(source)
    files={'ops/spug/'+name:pin for name,pin in graph['files'].items()}
    assert subject().validate_manifest_coverage(source,files)==graph
    files['ops/spug/smallapp_simple.py']['sha256']='0'*64
    with pytest.raises(ValueError,match='DEPENDENCY_MANIFEST_CHANGED'):
        subject().validate_manifest_coverage(source,files)


@pytest.mark.parametrize('name',ADDITIONS)
def test_missing_dependency_is_not_ignored(source,name):
    (source/name).unlink()
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        subject().inspect_runtime_dependencies(source)


@pytest.mark.parametrize('extra',[
    '\nimport missing_business_module\n',
    '\nimport importlib\nimportlib.import_module("unreviewed")\n',
    '\n__import__("unreviewed")\n',
    '\nimport importlib as loader\nloader.import_module("unreviewed")\n',
    '\nfrom importlib import import_module as load\nload("unreviewed")\n',
])
def test_unknown_or_dynamic_import_is_explicitly_rejected(source,extra):
    path=source/'smallapp_entry.py';path.write_text(path.read_text(encoding='utf-8')+extra,encoding='utf-8')
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        subject().inspect_runtime_dependencies(source)


def test_new_local_import_requires_manifest_addition(source):
    path=source/'smallapp_entry.py';path.write_text(path.read_text(encoding='utf-8')+'\nimport local_new\n',encoding='utf-8')
    (source/'local_new.py').write_text('VALUE=1\n',encoding='utf-8')
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        subject().inspect_runtime_dependencies(source)


def test_alias_in_web_dependency_is_rejected(source):
    path=source/'smallapp-ui/index.html';path.write_text(path.read_text(encoding='utf-8').replace('preview/style.css','../../outside.css'),encoding='utf-8')
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        subject().inspect_runtime_dependencies(source)


def test_only_simple_is_a_deployment_candidate(source,tmp_path):
    runtime=tmp_path/'runtime';shutil.copytree(source,runtime)
    (runtime/'smallapp_simple.py').write_bytes(OLD_SIMPLE.read_bytes())
    graph=subject().inspect_runtime_dependencies(source)
    changes=subject().deployment_difference(runtime,graph)
    assert len(changes)==1 and changes[0]['relativePath']=='smallapp_simple.py'
    (runtime/'smallapp_progress_remote.py').write_bytes(b'changed')
    with pytest.raises(ValueError,match='DEPENDENCY_UNRELATED_RUNTIME_CHANGED'):
        subject().deployment_difference(runtime,graph)


def test_actual_clean_checkout_receipts_are_verified():
    module=subject();reference=module.publication.file_pin(PRIVATE/'spug-dependency-checkout-r1.private.json')
    pins=module.validate_checkout_observation(PRIVATE,reference,BUILD['sourceCommit'],Path(BUILD['worktree']))
    assert reference in pins and len(pins)==13


@pytest.fixture
def actual_continuation():
    import main_program_spug_publication_continuation as original
    prepared=original.prepare_continuation(TASK,PRIVATE,'main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')
    path=PRIVATE/'main-program-spug-installation-45dd7dc-r6-continuation-c1.private.json'
    return prepared,json.loads(path.read_text(encoding='utf-8'))


def test_actual_seven_applied_and_three_host_verifications_remain_proven(actual_continuation):
    prepared,failure=actual_continuation;pins=[]
    custody=json.loads((TASK/'spug-verification-source-custody-r1.json').read_text(encoding='utf-8'))
    result=subject().validate_failed_continuation(prepared,PRIVATE,failure,pins,historical_source_custody=custody)
    assert result['appliedCount']==7 and result['hostVerifications']==3
    assert result['lastNativeError']=='SIMPLE_CONFIGURATION_INVALID' and result['lastNativeExitCode']==0
    assert len(pins)>50


@pytest.mark.parametrize('change', ['write','stage','failure','generation'])
def test_changed_c1_summary_cannot_authorize_simple_installation(actual_continuation,change):
    prepared,failure=actual_continuation
    if change=='write':failure['writeStates'][0]['state']='UNKNOWN'
    if change=='stage':failure['stages']=failure['stages'][:-1]
    if change=='failure':failure['status']='PASS'
    if change=='generation':failure['sourceCommit']='0'*40
    custody=json.loads((TASK/'spug-verification-source-custody-r1.json').read_text(encoding='utf-8'))
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        subject().validate_failed_continuation(prepared,PRIVATE,failure,[],historical_source_custody=custody)


def test_actual_runner_exit_binds_the_original_dispatch_and_native_absence(actual_continuation):
    prepared,failure=actual_continuation;module=subject();records=module.contract.Records(TASK)
    report=records.read('spug-c1-runner-terminal-r1.json');pins=[]
    module.validate_runner_exit(PRIVATE,report,prepared,pins)
    assert len(pins)>=6
    report['originalRunnerPid']+=1
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        module.validate_runner_exit(PRIVATE,report,prepared,[])


def test_missing_coverage_cannot_produce_a_completion_record():
    module=subject();records=module.contract.Records(TASK);records.read('spug-resource-build-c7728ad.json')
    checkout=module.publication.file_pin(PRIVATE/'spug-dependency-checkout-r1.private.json')
    with pytest.raises((ValueError,FileNotFoundError),match='COVERAGE|MISSING|No such|cannot find'):
        module.make_dependency_completion(TASK,PRIVATE,records.references['spug-resource-build-c7728ad.json'],None,checkout)


def test_real_runtime_observation_binds_configuration_and_import_origins(actual_continuation):
    prepared,failure=actual_continuation;module=subject();records=module.contract.Records(TASK)
    observation=records.read('spug-runtime-dependency-observation-r1.json');pins=[]
    validated=module.validate_runtime_observation(PRIVATE,observation,prepared,publication_pin(failure),pins)
    assert validated['entryIdentity']['pid']==151768 and len(validated['configPins'])==7
    observation['result']['importedSources'][0]['sourcePin']['path']='/elsewhere/adapter.py'
    with pytest.raises(ValueError,match='DEPENDENCY_'):
        module.validate_runtime_observation(PRIVATE,observation,prepared,publication_pin(failure),[])


def publication_pin(failure):
    return subject().publication.file_pin(PRIVATE/'main-program-spug-installation-45dd7dc-r6-continuation-c1.private.json')


def test_graph_can_be_rebuilt_from_preserved_bytes_after_checkout_removal(source):
    module=subject();before=module.inspect_runtime_dependencies(source)
    originals={name:(source/name).read_bytes() for name in FILES}
    for name in FILES:(source/name).unlink()
    assert module.inspect_runtime_dependencies(sources=originals)==before


def test_cim_query_request_must_bind_the_exact_command_and_pid():
    module=subject();request=json.loads((PRIVATE/'spug-c1-runner-terminal-r1.request.private.json').read_text(encoding='utf-8'))
    program=Path(request['programPin']['path']).read_bytes()
    module.validate_runner_query_request(request,program,27312,request['completionPin'],request['dispatchPin'])
    request['argv'][3]="[Console]::Write('{\"pid\":27312,\"count\":0}')"
    with pytest.raises(ValueError,match='DEPENDENCY_RUNNER_QUERY_COMMAND'):
        module.validate_runner_query_request(request,request['argv'][3].encode(),27312,request['completionPin'],request['dispatchPin'])


@pytest.mark.parametrize('failure',['guard','readback','none'])
def test_real_file_replacement_preserves_old_bytes_and_unknown_outcomes(tmp_path,failure):
    module=subject();target=tmp_path/'simple.py';target.write_bytes(b'old');archive=tmp_path/'before.py';pending=tmp_path/'pending.py'
    before=module.publication.file_pin(target);events=[]
    def guard():
        assert target.read_bytes()==b'old' and archive.read_bytes()==b'old';events.append('guard')
        if failure=='guard':raise ValueError('GUARD_REFUSED')
    def readback():
        assert target.read_bytes()==b'new' and archive.read_bytes()==b'old';events.append('readback')
        if failure=='readback':raise ValueError('READBACK_UNKNOWN')
        return module.publication.file_pin(target)
    if failure=='none':
        result=module.replace_simple(target,b'new',before,archive,pending,guard,readback)
        assert result['transition']['atomicMoveCompleted'] is True and result['containerReadbackPin']['sha256']==hashlib.sha256(b'new').hexdigest()
    else:
        with pytest.raises(ValueError,match='GUARD_REFUSED|READBACK_UNKNOWN'):
            module.replace_simple(target,b'new',before,archive,pending,guard,readback)
    assert target.read_bytes()==(b'old' if failure=='guard' else b'new')
    assert archive.read_bytes()==b'old' and events==(['guard'] if failure=='guard' else ['guard','readback'])


def test_default_cli_cannot_activate_or_repeat_c1():
    args=subject().parser().parse_args(['--inputs','fixture.json'])
    assert args.activate is False
    with pytest.raises(SystemExit):subject().parser().parse_args(['--inputs','fixture.json','--apply'])


def test_installation_input_refuses_unknown_fields_before_any_external_call():
    with pytest.raises(ValueError,match='DEPENDENCY_ACTIVATION_INPUTS_INVALID'):
        subject().prepare_value(subject().contract.Records(TASK),PRIVATE,{'schemaVersion':'wrong'},None)


@pytest.fixture
def source_custody(tmp_path,source):
    module=subject();private=tmp_path/'private';private.mkdir();checkout=tmp_path/'checkout'
    root=checkout/'ops/spug';shutil.copytree(source,root)
    base=dict(BUILD,worktree=str(checkout));basepin={'file':'base.json','bytes':1,'sha256':'a'*64}
    originals=[root/name for name in sorted(FILES)]+[Path(module.__file__),Path(module.__file__).with_name('test_spug_runtime_dependency_completion.py')]
    rows=[]
    for index,path in enumerate(originals):
        kept=private/(str(index)+'.original');kept.write_bytes(path.read_bytes())
        rows.append(dict(originalPin=module.publication.file_pin(path),preservedPin=module.publication.file_pin(kept)))
    value=dict(schemaVersion='MainProgramSpugRuntimeDependencySourceCustody/v1',baseResourceBuildPin=basepin,entries=rows)
    path=private/'custody.json';path.write_bytes(module.publication.canonical(value))
    return private,base,basepin,path,value


def test_history_custody_survives_checkout_removal_and_reader_relocation(source_custody,monkeypatch,tmp_path):
    module=subject();private,base,basepin,path,value=source_custody;pin=module.publication.file_pin(path)
    before=module.load_source_custody(private,pin,base,basepin,verify_checkout=True)[0]
    shutil.rmtree(base['worktree'])
    monkeypatch.setattr(module,'__file__',str(tmp_path/'int_main/doc/tasks'/TASK.name/Path(module.__file__).name))
    after,mapping,_=module.load_source_custody(private,pin,base,basepin,verify_checkout=False)
    assert after==before and set(mapping)=={row['originalPin']['path'] for row in value['entries']}
    log=private/'local-protocol-fixture.log';log.write_text('1 passed in 0.01s\n',encoding='utf-8')
    coverage=dict(schemaVersion='MainProgramSpugRuntimeDependencyCoverage/v1',status='PASS',actualExitCode=0,
                  actualPassed=1,actualSkipped=0,inputPins=[r['originalPin'] for r in value['entries']],logPin=module.publication.file_pin(log))
    report=private/'local-protocol-fixture.json';report.write_bytes(module.publication.canonical(coverage))
    module.validate_coverage(private,module.publication.file_pin(report),Path(base['worktree'])/'ops/spug',after,[],source_custody=mapping)
    with pytest.raises((ValueError,FileNotFoundError)):
        module.load_source_custody(private,pin,base,basepin,verify_checkout=True)


@pytest.mark.parametrize('tamper',['extra','duplicate','bytes'])
def test_source_custody_is_exact_and_full_bytes(source_custody,tamper):
    module=subject();private,base,basepin,path,value=source_custody
    if tamper=='extra':value['entries'].append(value['entries'][0])
    elif tamper=='duplicate':value['entries'][-1]=value['entries'][-2]
    else:Path(value['entries'][0]['preservedPin']['path']).write_bytes(b'changed')
    path.write_bytes(module.publication.canonical(value))
    with pytest.raises(ValueError):module.load_source_custody(private,module.publication.file_pin(path),base,basepin,verify_checkout=False)


@pytest.fixture
def runtime_prepared(actual_continuation):
    c1,failure=actual_continuation;module=subject()
    observation=json.loads((TASK/'spug-runtime-dependency-observation-r1.json').read_bytes())['result']
    old=json.loads(Path(c1['resourceInstallation']['observationPin']['path']).read_bytes())
    return dict(c1=c1,failure=failure,runtime=observation,oldObservation=old,
                change=dict(beforePin=module.publication.file_pin(OLD_SIMPLE)),completion=module.inspect_runtime_dependencies(SOURCE))


@pytest.mark.parametrize('kind',['runtime','reload'])
def test_generated_program_really_executes_and_refuses_missing_original_entry(runtime_prepared,tmp_path,kind):
    module=subject();identity={'pid':151768};environment='a'*64
    program=module.runtime_program(runtime_prepared,'before') if kind=='runtime' else module.reload_program(runtime_prepared,identity,environment)
    # Real candidate imports and real local Python; /proc is absent on this Windows fixture.
    # This is a refusal test, not a simulated successful installation.
    assert not Path('/proc').exists()
    env=dict(os.environ,PYTHONPATH=str(SOURCE),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-X','utf8','-B','-'],input=program.encode('utf-8'),capture_output=True,cwd=tmp_path,env=env,timeout=20)
    if kind=='runtime':
        assert result.returncode==0 and result.stderr==b''
        value=json.loads(result.stdout);assert value['status']=='FAILED' and value['errorType']=='FileNotFoundError'
        assert value['configurationWrites'] is False and value['backupDispatched'] is False
    else:
        assert result.returncode!=0 and result.stdout==b'' and b'DEPENDENCY_RELOAD_GUARD_FAILED' in result.stderr


def test_reload_requires_new_pid_ticks_and_identical_process_ownership():
    module=subject();before=dict(pid=10,startTicks='100',argv=['python3'],executable='/python',parentPid=1)
    after=dict(before,pid=11,startTicks='101')
    assert module.validate_reload_identity(before,after)==after
    for invalid in (before,dict(after,startTicks='100'),dict(after,executable='/other')):
        with pytest.raises(ValueError,match='RELOAD_IDENTITY_INVALID'):module.validate_reload_identity(before,invalid)


def test_actual_runtime_spec_has_no_conflicting_preserved_and_installed_pins(runtime_prepared):
    module=subject();spec=module.runtime_spec(runtime_prepared,'installed')
    indexed={}
    for pin in spec['preservedPins']+spec['configurationPins']+spec['filePins']:
        assert pin['path'] not in indexed or indexed[pin['path']]==pin
        indexed[pin['path']]=pin
    assert len(spec['filePins'])==14 and len(spec['configurationPins'])==7
    assert spec['continuationAudit'] not in spec['emptyAudits']
    with pytest.raises(ValueError,match='RUNTIME_VERIFICATION_FAILED'):
        module.validate_runtime_result(runtime_prepared,{'status':'PASS','freshProcessConfigurationParsed':True},'after')
