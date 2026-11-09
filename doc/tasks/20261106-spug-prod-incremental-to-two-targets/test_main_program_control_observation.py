"""Real local files and process metadata at explicit systemd/Docker seams.

The actual 899/45 plan is read only. Temporary protocol data is not an actual
server observation. No test invokes SSH or an installed control API.
"""
from copy import deepcopy
import hashlib
import importlib
import json
import ast
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys

import pytest

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
sys.path.insert(0,str(TASK))
from test_main_program_control_runtime import runtime, gates


def module():return importlib.import_module('main_program_control_observation')


def local(path):
    raw=path.read_bytes()
    return dict(file=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def actual_inputs():
    return dict(suffix='58',generation_pin=local(TASK/'main-program-control-generation-899730d-r1.json'),
        plan_pin=local(TASK/'main-program-configuration-plan-45dd7dc-r5.json'),
        source_commit='45dd7dc65409c87fe856584b85873ea96c0b830e',revision_id='r5')


def test_actual_prepare_uses_formal_generation_and_exact_v4_names_without_writing():
    before={p:p.read_bytes() for p in (TASK/'main-program-control-generation-899730d-r1.json',
        TASK/'main-program-configuration-plan-45dd7dc-r5.json',PRIVATE/'main-program-configuration-plan-45dd7dc-r5.private.json')}
    context=module().prepare_observation(TASK,PRIVATE,**actual_inputs())
    assert context['selection']['currentControlGenerationPin']==actual_inputs()['generation_pin']
    assert [r['pid'] for r in context['selection']['controllers']]==[18785]
    assert context['unitFile']=='main-program-control-units-58-45dd7dc-r5.json'
    assert context['environmentFile']=='main-program-control-environment-baseline-58-45dd7dc-r5.json'
    assert context['readOnly'] is True
    assert all(p.read_bytes()==raw for p,raw in before.items())


@pytest.mark.parametrize('change',['commit','revision','generation-pin','plan-pin','host'])
def test_prepare_rejects_explicit_generation_or_plan_mismatch(change):
    inputs=actual_inputs()
    if change=='commit':inputs['source_commit']='f'*40
    elif change=='revision':inputs['revision_id']='r6'
    elif change=='host':inputs['suffix']='60'
    elif change=='generation-pin':inputs['generation_pin']['sha256']='f'*64
    else:inputs['plan_pin']['sha256']='f'*64
    with pytest.raises(ValueError):module().prepare_observation(TASK,PRIVATE,**inputs)


def reader(runtime):
    api=gates(runtime)
    class UnitDirectories(module().ObservationPaths):
        def unit_directory(self,service):
            return Path(runtime['properties']['FragmentPath']).parent/(service+'.d')
    paths=UnitDirectories(proc_root=runtime['proc_root'],reservation_path=runtime['reservation'],
        fstab_path=runtime['fstab'],mountinfo_path=runtime['mounts'])
    spec=deepcopy(runtime['spec'])
    spec['current'].update(host='172.30.30.58',suffix='58')
    spec.update(sourceCommit='d'*40,revisionId='r5',previousControlGenerationPin=dict(file='generation.json',bytes=1,sha256='a'*64))
    # Discover the baseline from real process protocol bytes, not from the
    # already-existing fixture's baseline. Keep its command/filesystem seams.
    spec.pop('environmentBaseline')
    spec['unit']={k:v for k,v in spec['unit'].items() if k!='controllers'}
    for row in spec['current']['controllers']:
        row.pop('argvSha256');row.pop('environmentMode')
    api.spec=spec
    return module().ReadonlyObserver(api,paths=paths)


def test_collection_reads_process_units_environment_and_complete_runtime(runtime):
    subject=reader(runtime);value=subject.collect_units()
    assert value['status']=='PASS' and value['serverFilesWritten'] is False
    assert value['allOriginalControlsAndBusinessUnchanged'] is True
    assert value['fstabAndMountsUnchanged'] is True
    assert value['controllers'][0]['unitPin']==runtime['spec']['unit']['controllers'][0]['unitPin']
    unit_pin=dict(file='main-program-control-units-58-ddddddd-r5.json',bytes=1,sha256='e'*64)
    baseline=subject.collect_environment(value,unit_pin)
    row=baseline['controllers'][0]
    assert row['argvSha256']==runtime['spec']['current']['controllers'][0]['argvSha256']
    assert row['environmentSha256']==hashlib.sha256((runtime['process_dir']/'environ').read_bytes()).hexdigest()
    assert baseline['unitObservationPin']==unit_pin
    assert baseline['revisionId']=='r5' and baseline['serverFilesWritten'] is False
    assert all(args[:2] not in (['systemctl','restart'],['systemctl','daemon-reload']) for args in runtime['calls'])


@pytest.mark.parametrize('change',['pid','worker','package','guard','environment','mount-during-read'])
def test_collection_refuses_real_protocol_drift(runtime,change):
    subject=reader(runtime)
    if change=='pid':runtime['properties']['MainPID']='999999'
    elif change=='worker':
        p=runtime['proc_root']/'999999';p.mkdir()
        root=str(runtime['other'].parent.parent/'working')
        p.joinpath('cmdline').write_bytes(root.encode()+b'\0worker')
    elif change=='package':runtime['other'].write_bytes(b'changed')
    elif change=='guard':runtime['guard_properties']['ActiveState']='inactive'
    elif change=='environment':(runtime['process_dir']/'environ').write_bytes(b'PYTHONPATH=changed\0')
    else:
        original=subject.gates.run
        def run(*args,**kwargs):
            result=original(*args,**kwargs)
            runtime['mounts'].write_bytes(b'mount changed during observation')
            return result
        subject.gates.run=run
    with pytest.raises((ValueError,KeyError)):subject.collect_units()


def test_public_projection_never_contains_environment_declarations(runtime,tmp_path):
    subject=reader(runtime);unit=subject.collect_units()
    unit_pin=dict(file='main-program-control-units-58-ddddddd-r5.json',bytes=1,sha256='e'*64)
    env=subject.collect_environment(unit,unit_pin)
    pin=dict(path=str(tmp_path/'private.json'),bytes=1,sha256='f'*64)
    public=module().project_environment(env,pin)
    assert all(set(row).isdisjoint({'systemdEnvironmentRaw','declaredEnvironment'}) for row in public['controllers'])
    assert env['controllers'][0]['systemdEnvironmentRaw'] not in json.dumps(public)
    assert public['privateSnapshotPin']==pin
    with pytest.raises(ValueError):module().project_environment(dict(env,unexpectedSecret='must-not-publish'),pin)


def test_transport_entry_is_real_dispatch_and_duplicate_output_refuses_before_dispatch(tmp_path,monkeypatch):
    subject=module();context=subject.prepare_observation(TASK,PRIVATE,**actual_inputs())
    # This test only verifies the dispatch boundary with actual local receipts;
    # collection semantics are separately exercised by the real process fixture.
    context=dict(context,task=str(tmp_path/'public'),private=str(tmp_path/'private'))
    Path(context['task']).mkdir();Path(context['private']).mkdir()
    Path(context['task'],context['unitFile']).write_bytes(b'existing original')
    calls=[]
    def transport(*args,**kwargs):calls.append(args);raise AssertionError('must reject before dispatch')
    with pytest.raises(ValueError,match='EXISTS'):subject.observe_units(context,transport=transport)
    assert calls==[]


def test_generated_remote_program_contains_only_formal_helpers_and_readonly_transport():
    context=module().prepare_observation(TASK,PRIVATE,**actual_inputs())
    payload=module().build_remote_program(context,'units')
    compile(payload,'<control-observation>','exec')
    assert 'stage-main-program-engine-r3.py' not in payload
    assert 'observe-main-control-units-r1.py' not in payload
    assert 'collect-main-control-environment-baseline-r2.py' not in payload
    assert 'systemctl restart' not in payload and 'daemon-reload' not in payload


def observation_context(subject,tmp_path):
    public=tmp_path/'public';private=tmp_path/'private';public.mkdir();private.mkdir()
    spec=subject.gates.spec
    return dict(task=str(public),private=str(private),selection=deepcopy(spec['current']),spec=deepcopy(spec),
        inputPins=[subject.gates.pin(subject.gates.spec['historyPins'][0]['path'])],sourceCommit=spec['sourceCommit'],
        revisionId=spec['revisionId'],readOnly=True,unitFile='main-program-control-units-58-ddddddd-r5.json',
        environmentFile='main-program-control-environment-baseline-58-ddddddd-r5.json')


def protocol_transport(subject,wire=lambda value:value):
    """Use the real collector; only remote transport is replaced by local I/O."""
    units=[]
    def transport(host,payload,timeout):
        assert host=='172.30.30.58' and timeout==660
        compile(payload,'<actual-observation-payload>','exec')
        literals={node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(payload).body
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
            and node.targets[0].id in ('MODE','UNIT','UNIT_PIN')}
        if literals['MODE']=='units':
            value=subject.collect_units();units.append(value);return wire(value)
        assert literals['UNIT']==wire(units[-1])
        return wire(subject.collect_environment(units[-1],literals['UNIT_PIN']))
    return transport


def test_actual_local_observation_lifecycle_is_accepted_by_formal_v4_baseline_reader(runtime,tmp_path):
    import main_program_control_activation as activation
    from main_program_installation_selection import Records
    subject=reader(runtime);context=observation_context(subject,tmp_path)
    # Deployment readers intentionally require POSIX remote paths. This
    # transport protocol maps only path fields; actual bytes, process identity,
    # environment declarations and hashes still come from the real collector.
    # Local PRIVATE snapshot pins remain actual Windows paths.
    def wire(value,key=None):
        if type(value) is dict:return {k:wire(v,k) for k,v in value.items()}
        if type(value) is list:return [wire(v,key) for v in value]
        if key in ('path','engine','directory','FragmentPath','DropInPaths','executable') and type(value) is str and len(value)>2 and value[1]==':':
            return '/protocol/'+value[0].lower()+value[2:].replace('\\','/')
        return value
    context['selection']=wire(context['selection']);context['spec']=wire(context['spec'])
    result=module().observe_all(context,transport=protocol_transport(subject,wire))
    records=Records(context['task']);unit=records.pinned(result['unit']['observationPin'])
    inputs=dict(schemaVersion='MainProgramControlActivationInputs/v4',suffix='58',sourceCommit='d'*40,
        revisionId='r5',previousControlGenerationPin=context['spec']['previousControlGenerationPin'],
        unitObservationPin=result['unit']['observationPin'],originalEnvironmentObservationPin=result['environment']['observationPin'])
    value=activation.validate_environment_baseline(records,Path(context['private']),inputs,unit,
        wire(subject.gates.spec['current']['controllers']))
    assert value['controllers'][0]['declaredEnvironment']==dict(PYTHONDONTWRITEBYTECODE='1',
        PYTHONPATH=str(runtime['other'].parent).replace('\\','/'))
    assert set(Path(context['task']).iterdir())=={Path(context['task'])/context['unitFile'],
        Path(context['task'])/context['environmentFile']}
    assert result['status']=='PASS' and result['serverFilesWritten'] is False


def test_drift_after_dispatch_retains_private_response_but_never_publishes_pass(runtime,tmp_path):
    subject=reader(runtime);context=observation_context(subject,tmp_path);original=protocol_transport(subject)
    def transport(*args,**kwargs):
        value=original(*args,**kwargs);Path(context['inputPins'][0]['path']).write_bytes(b'changed after dispatch');return value
    with pytest.raises(ValueError,match='OBSERVATION_INPUT_CHANGED'):
        module().observe_units(context,transport=transport)
    assert not Path(context['task'],context['unitFile']).exists()
    assert Path(context['private'],context['unitFile'][:-5]+'.private.json').exists()


def test_public_units_reject_unrecognized_nested_runtime_private_field(runtime):
    subject=reader(runtime);unit=subject.collect_units()
    unit['runtimeEvidence']['controllers'][0]['unexpectedSecret']='private diagnostic'
    with pytest.raises(ValueError,match='PROJECTION'):
        module().project_units(unit,dict(path='/private/unit.json',bytes=1,sha256='a'*64))


def test_environment_transport_cannot_publish_other_process_identity(runtime,tmp_path):
    subject=reader(runtime);context=observation_context(subject,tmp_path);original=protocol_transport(subject)
    unit=module().observe_units(context,transport=original)
    def transport(*args,**kwargs):
        value=original(*args,**kwargs);value['controllers'][0]['pid']+=1;return value
    with pytest.raises(ValueError,match='OBSERVATION_RESPONSE_CONTROLS_CHANGED'):
        module().observe_environment(context,unit['observationPin'],transport=transport)
    assert not Path(context['task'],context['environmentFile']).exists()


@pytest.mark.parametrize('suffix,pids,roles',[
    ('57',[20440,9785],['source','target']),('59',[6329],['target'])])
def test_other_actual_hosts_keep_generation_roles_and_local_source_scope(suffix,pids,roles):
    inputs=dict(actual_inputs(),suffix=suffix)
    context=module().prepare_observation(TASK,PRIVATE,**inputs)
    assert [row['pid'] for row in context['selection']['controllers']]==pids
    assert [row['role'] for row in context['selection']['controllers']]==roles
    assert len(context['spec']['sourceEvidencePins'])==(3 if suffix=='57' else 0)
    assert (context['spec']['previousCustody'] is None)==(suffix=='57')


def test_generated_formal_program_executes_discovery_with_only_external_protocol_seams(runtime,tmp_path):
    subject=reader(runtime);context=observation_context(subject,tmp_path)
    payload=module().build_remote_program(context,'units')
    tree=ast.parse(payload)
    # Execute the emitted bootstrap and both exact new module sources. Inject
    # only command/file/proc boundaries immediately before the native gates are
    # instantiated. No production function is replaced with a successful fact.
    def boundaries(namespace):
        actual_runtime=sys.modules['main_program_control_runtime']
        actual_observation=sys.modules['main_program_control_observation']
        original_gate=namespace['RuntimeGates'];original_observer=namespace['ReadonlyObserver']
        def gate(spec,**kwargs):
            kwargs.update(run=runtime['run'],pin=runtime['pin'],read=runtime['read'],paths=subject.gates.paths)
            value=original_gate(spec,**kwargs)
            assert isinstance(value,actual_runtime.RuntimeGates)
            return value
        def observer(gates,**kwargs):
            kwargs['paths']=subject.paths
            value=original_observer(gates,**kwargs)
            assert isinstance(value,actual_observation.ReadonlyObserver)
            return value
        namespace.update(RuntimeGates=gate,ReadonlyObserver=observer)
    index=next(i for i,node in enumerate(tree.body) if isinstance(node,ast.Assign) and
        any(isinstance(target,ast.Name) and target.id=='gates' for target in node.targets))
    tree.body.insert(index,ast.Expr(ast.Call(ast.Name('_test_boundaries',ast.Load()),
        [ast.Call(ast.Name('globals',ast.Load()),[],[])],[])))
    ast.fix_missing_locations(tree)
    names=('main_program_control_runtime','main_program_control_observation')
    original={name:sys.modules[name] for name in names};output=io.StringIO()
    try:
        with redirect_stdout(output):exec(compile(tree,'<readonly-bootstrap-protocol>','exec'),{'_test_boundaries':boundaries})
    finally:
        for name,value in original.items():sys.modules[name]=value
    value=json.loads(output.getvalue())
    assert value['status']=='PASS' and value['controllers'][0]['pid']==runtime['spec']['current']['controllers'][0]['pid']
    assert value['serverFilesWritten'] is False and value['restoreDispatched'] is False


def test_environment_discovery_cannot_adopt_drift_since_the_pinned_unit_observation(runtime):
    subject=reader(runtime);unit=subject.collect_units()
    path=runtime['process_dir']/'environ'
    path.write_bytes(path.read_bytes()+b'OBSERVATION_TEST_EXTRA=changed-between-observations\0')
    with pytest.raises(ValueError,match='UNIT_ENVIRONMENT_BINDING_CHANGED'):
        subject.collect_environment(unit,dict(file='unit.json',bytes=1,sha256='e'*64))
