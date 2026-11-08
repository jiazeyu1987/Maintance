"""Check frozen-vs-lightweight packages locally; no server operations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('backup_variants', ROOT/'ops/backup_engine/build_variants.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture(scope='module')
def packages(tmp_path_factory):
    output = tmp_path_factory.mktemp('variants')/'packages'
    builder.build(output)
    return output


def test_standard_keeps_original_code_except_reviewed_fixes_and_archive_names(packages):
    original, _ = builder.standard_sources()
    reviewed = builder.safe_fixes(original)
    allowed = {'common/recovery_minimal_runtime.py', 'common/recovery_step_timing.py',
        'common/recovery_minimal.py', 'common/recovery_resource_admission.py',
        'common/recovery_firewall.py', 'common/recovery_minimal_worker.py', 'common/recovery_archive_guard.py',
        'common/repository_minimal.py', 'control/recovery_control_capture_config.py',
        'control/recovery_control_smallapp_native.py', 'control/recovery_control_executor.py',
        'control/recovery_control_target_availability.py',
        'control/recovery_control_incremental_plan.py', 'control/recovery_control_smallapp.py',
        'common/recovery_backup_epoch.py', 'common/recovery_sql_stream.py', 'common/recovery_target_sources.py',
        'control/recovery_control_point_quarantine.py', 'formal/formal_binlog_scope.py',
        'common/recovery_replace.py', 'common/recovery_data.py', 'formal/formal_data_evidence.py', 'formal/formal_schema_evidence.py',
        'common/recovery_main_target.py', 'common/recovery_archive_versions.py', 'common/recovery_program_archive.py',
        'common/recovery_program_containers.py',
        'common/recovery_program_generation.py',
        'common/recovery_program_activation.py', 'common/recovery_program_targets.py',
        'common/recovery_program_execution.py', 'common/recovery_program_derivation.py',
        'common/recovery_program_import.py', 'common/recovery_program_native.py',
        'common/recovery_program_source.py', 'common/recovery_program_protection.py',
        'common/recovery_replacement_storage.py', 'common/recovery_minimal_plan.py',
        'common/recovery_retained_retry.py', 'common/recovery_minimal_redis_dump.py', 'common/recovery_published_fence.py', 'common/recovery_archive_view.py',
        'common/recovery_mysql_scheduler.py', 'common/recovery_main_health.py',
        'control/recovery_control_restore_catalogue.py', 'control/recovery_control_smallapp_http.py',
        'formal/minimal_capture_support.py', 'formal/minimal_capture_worker.py',
        'formal/formal_capture_semantics.py', 'formal/formal_capture_parent_guard.py',
        'formal/minimal_redis_snapshot.py'}
    assert {name for name, raw in reviewed.items() if original.get(name) != raw} <= allowed
    with tarfile.open(packages/'backup-restore-standard.tgz') as archive:
        version = json.load(archive.extractfile('package.json'))
        assert version['payloadContentVerification'] is True
        assert version['fileVerification'] is True and version['requestParentBinding'] is True
        assert version['backupStepTimings'] is True
        for name, raw in reviewed.items():
            expected = raw.replace(b"'prod-'", b"'prod-standard-'") if name == 'common/repository_minimal.py' else raw
            assert archive.extractfile(name).read() == expected, name
        code = archive.extractfile('common/repository_minimal.py').read()
        assert code.count(b"'prod-standard-'") == 2  # publish and cancellation agree


def test_changed_safe_baseline_patch_context_is_rejected():
    original, _ = builder.standard_sources()
    original['formal/minimal_redis_snapshot.py'] = b'# an incompatible baseline\n'
    with pytest.raises(ValueError, match='STANDARD_FIX_CONTEXT_CHANGED'):
        builder.safe_fixes(original)


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_original_target_source_admission_executes_from_each_real_package(variant, packages, tmp_path):
    root = tmp_path/'engine'
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        member='common/recovery_target_sources.py'
        assert archive.extractfile(member).read() == (ROOT/'ops/recovery/recovery_target_sources.py').read_bytes()
        archive.extractall(root,filter='data')
    code = r'''
import copy,pathlib,sys
sys.path.insert(0,str(pathlib.Path(sys.argv[1])/'common'))
from recovery_target_sources import admit_target_source
target=dict(sourceConfigRef='current',mainApplication={'schemaVersion':'RegisteredMainApplication/v2'},
 replacement={'schemaVersion':'RegisteredApplicationReplacement/v2','stateRoot':'original-claims'})
owner=dict(targets={'main':target},sources={'current':{},'archive':{}},
 targetSourceAdmissions=dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'main':['current','archive']}))
original=copy.deepcopy(owner)
assert admit_target_source(owner,dict(targetConfigRef='main',sourceConfigRef='archive')) is target
assert owner==original
owner.pop('targetSourceAdmissions')
try:admit_target_source(owner,dict(targetConfigRef='main',sourceConfigRef='archive'))
except ValueError as error:assert str(error)=='TARGET_SOURCE_MISMATCH'
else:raise AssertionError('unregistered source admitted')
'''
    subprocess.run([sys.executable,'-B','-c',code,str(root)],check=True)


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_automatic_incremental_components_execute_from_real_package(variant, packages, tmp_path):
    root = tmp_path / 'engine'
    root.mkdir()
    with tarfile.open(packages / ('backup-restore-' + variant + '.tgz')) as archive:
        archive.extractall(root, filter='data')
    code = r'''
import hashlib,json,pathlib,sys,tempfile
root=pathlib.Path(sys.argv[1])
sys.path[:0]=[str(root/p) for p in ('common','control','formal')]
from recovery_control_incremental_plan import response
from recovery_control_smallapp import Ledger
from recovery_control_smallapp_native import Native
from recovery_backup_epoch import validate_policy
from recovery_sql_stream import inspect_incremental_sql
assert callable(Ledger.require_source_idle)
assert callable(Native.incremental_plan)
plan=response('packaged-source','BASELINE_REQUIRED','NO_SUCCESSFUL_FULL_BASELINE')
digest=plan.pop('planDigest')
assert digest==hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
with tempfile.TemporaryDirectory() as folder:
 path=pathlib.Path(folder)/'captured.sql'
 path.write_bytes(b'-- IntRuoyi binlog incremental;\nBINLOG payload')
 inspect_incremental_sql(path,mode='GTID',has_segments=True,guard=lambda:None,seconds=60)
print('PACKAGED_AUTOMATIC_INCREMENTAL_COMPONENTS_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', code, str(root)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'PACKAGED_AUTOMATIC_INCREMENTAL_COMPONENTS_PASS'


def test_safe_allocator_baseline_drift_is_rejected():
    original, _ = builder.standard_sources()
    original['formal/formal_schema_evidence.py'] += b'\n# drift\n'
    with pytest.raises(ValueError, match='STANDARD_SCHEMA_BASELINE_CHANGED'):
        builder.safe_fixes(original)


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_allocator_behavior_and_native_mutation_audit(variant, packages, tmp_path):
    import ast
    import types
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        schema_code = archive.extractfile('formal/formal_schema_evidence.py').read()
        native_code = archive.extractfile('common/recovery_data.py').read()
    assert schema_code.replace(b'\r\n', b'\n') == (ROOT/'ops/backup_engine/formal/formal_schema_evidence.py').read_bytes().replace(b'\r\n', b'\n')
    tree = ast.parse(native_code)
    native = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'NativeData')
    method = next(n for n in native.body if isinstance(n, ast.FunctionDef) and n.name == 'restore_allocator_state')
    namespace = dict(pinned_json=lambda ref: {'schema': {'database': 'unit_db'}},
                     require=lambda condition, reason: condition or (_ for _ in ()).throw(ValueError(reason)))
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<packaged-native-allocator>', 'exec'), namespace)
    calls = []
    class NativeFailure(Exception):pass
    def actual_failure(argv, **kwargs):
        calls.append((argv, kwargs));raise NativeFailure('confirmed process failure')
    def restore(mysql, source, uuid, **kwargs):
        return kwargs['mutate']('ALTER TABLE `unit_table` AUTO_INCREMENT = 11;')
    subject = types.SimpleNamespace(modules={'formal_schema_evidence': types.SimpleNamespace(
        identifier=lambda s: '`'+s+'`', restore_frozen_auto_increment=restore)},
        material={'database': {'expectedDataPin': {}}}, config={'database': 'unit_db'}, db_uuid='target-uuid',
        root=tmp_path, original_pins=[], bound=lambda **kwargs: None, guard=lambda: None,
        seconds=lambda: 60, secret=lambda *args: 'private-test-secret', command=actual_failure,
        mysql=types.SimpleNamespace(_command=lambda program, arguments: ['pinned-docker', program, *arguments]))
    with pytest.raises(NativeFailure):
        namespace['restore_allocator_state'](subject)
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert kwargs['mutation'] is True and b'private-test-secret\nUSE `unit_db`;' in kwargs['input_bytes']
    assert 'private-test-secret' not in repr(argv) and '--batch' in argv
    assert not list(tmp_path.iterdir()), 'failed native mutation must not publish success evidence'


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_minimal_runtime_loads_real_allocator_dependency(variant, packages, tmp_path):
    """Run the shipped minimal loader in a fresh process, without module stubs."""
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path/'package', filter='data')
    program = r'''
import sys
from pathlib import Path
root=Path(sys.argv[1])
sys.path.insert(0,str(root/'common'))
from recovery_minimal_runtime import modules_from
modules=modules_from(str(root/'formal'))
schema=modules['formal_schema_evidence']
assert Path(schema.__file__).resolve()==(root/'formal/formal_schema_evidence.py').resolve()
assert callable(schema.restore_frozen_auto_increment) and callable(schema.frozen_auto_increment_plan)
assert issubclass(modules['formal_sql_restore'].IsolatedTargetMySql,schema.SchemaMySql)
print('actual minimal loader supplies the packaged allocator and schema-capable MySQL')
'''
    result = subprocess.run([sys.executable, '-B', '-c', program, str(tmp_path/'package')],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_redis_dump_uses_registered_authentication(variant, packages):
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        code=archive.extractfile('common/recovery_minimal_redis_dump.py').read().decode()
        assert 'password=redis_password(native)' in code
        assert 'from recovery_main_target import redis_password' in code
        main=archive.extractfile('common/recovery_main_target.py').read().decode()
        assert 'RegisteredMainApplication/v2' in main and 'MAIN_REDIS_ACL_CHANGED' in main


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_constructor_binds_only_requested_frontend_readiness(variant, packages, tmp_path):
    """Execute the actual delivered constructor up to its first database read."""
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path/'package', filter='data')
    program = r'''
import sys
from pathlib import Path
sys.path[:0]=[sys.argv[1]+'/common',sys.argv[1]+'/formal']
import recovery_minimal_runtime as runtime
from recovery_engine import pin
class BeforeDatabaseIO(Exception):pass
class Boundary(runtime.MinimalData):
 def database_uuid(self):raise BeforeDatabaseIO()
configuration={'environmentMysqlClientPath':'/usr/bin/mysql','maxExpandedBytes':64*1024**3,
 'formalModuleDirectory':sys.argv[1]+'/formal','deadlineMilliseconds':7200000,
 'dataLimits':{'max_rows':10000000,'max_nodes':100000000,'max_bytes':16*1024**3,'seconds':7200},
 'frontendReadiness':{'target-a':{'address':'192.168.20.58','port':8081},
                     'target-b':{'address':'192.168.20.59','port':38081}}}
root=Path(sys.argv[2]);root.mkdir()
inputs=root.parent/'inputs';inputs.mkdir();archive=inputs/'archive';archive.write_bytes(b'actual component archive bytes')
reference=pin(archive)
chain=[(reference,None,{'recoveryPoint':'component-point','objects':{'method':'PHYSICAL_FILES'},
 'payloadPins':[],'versionPins':[]},reference)]
target={'dataPolicy':{'businessInvariants':[]},'services':[{'role':'mysql','id':'component-db'}],
 'dockerPin':reference,'iptablesPin':reference}
for name in ('target-a','target-b','target-without-profile'):
 subject=Boundary.__new__(Boundary)
 try:
  subject.__init__(configuration,{'operationId':'component','targetConfigRef':name},None,{},chain,target,root,[])
 except BeforeDatabaseIO:pass
 else:raise AssertionError('Actual constructor did not reach native database boundary')
 assert getattr(subject,'frontend_readiness',None)==configuration['frontendReadiness'].get(name),'PACKAGED_FRONTEND_PROFILE_NOT_PROPAGATED'
print('delivered constructor binds exact requested frontend profile before native I/O')
'''
    result=subprocess.run([sys.executable,'-B','-c',program,str(tmp_path/'package'),str(tmp_path/'work')],
                          capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_published_fence_and_preparation_hooks_are_actually_packaged(variant, packages):
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_published_fence.py').read()==(ROOT/'ops/recovery/recovery_published_fence.py').read_bytes()
        assert archive.extractfile('common/recovery_archive_view.py').read()==(ROOT/'ops/recovery/recovery_archive_view.py').read_bytes()
        code=archive.extractfile('common/recovery_replace.py').read().decode()
        assert code.index('native.replacement_write_fence()') < code.index("native.docker(['stop'")
        assert code.index('native.replacement_quiescence()') < code.index("native.mysql.query('DROP DATABASE")
        assert 'native.replacement_finish()' in code


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_main_scheduler_lifecycle_and_retained_handoff_are_packaged(variant, packages):
    import ast
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_mysql_scheduler.py').read()==(ROOT/'ops/recovery/recovery_mysql_scheduler.py').read_bytes()
        main=archive.extractfile('common/recovery_main_target.py').read().decode()
        for name in ('recovery_main_target.py','recovery_program_protection.py'):
            delivered=archive.extractfile('common/'+name).read().replace(b'\r\n',b'\n')
            assert delivered==(ROOT/'ops/recovery'/name).read_bytes().replace(b'\r\n',b'\n')
        retry=archive.extractfile('common/recovery_retained_retry.py').read().decode()
        tree=ast.parse(main)
        definitions={node.name:node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        guarded=next(node for node in definitions['guarded_type'].body if isinstance(node,ast.ClassDef))
        methods={node.name:node for node in guarded.body if isinstance(node,ast.FunctionDef)}
        def calls(node):
            return [ast.unparse(item) for item in ast.walk(node) if isinstance(item,ast.Call)]
        for name in ('replacement_preflight','replacement_write_fence','replacement_quiescence',
                     'replacement_finish','bound'):
            assert 'protections(self)' in calls(methods[name])
        assert 'protected.scheduler.install()' in calls(methods['replacement_quiescence'])
        assert 'protected.scheduler.verify()' in calls(methods['bound'])
        finish=ast.unparse(methods['replacement_finish'])
        assert finish.index('protections(self)') < finish.index('custody.release(self)')
        assert "result['mysqlSchedulerReleasePin'] = protected.scheduler.release()" in finish
        assert finish.index('archive.release()') < finish.index('fence.release()') < finish.index('protected.scheduler.release()')
        selector=ast.unparse(definitions['protections'])
        assert 'type(custody) is ProtectionCustody' in selector
        assert 'return custody.view_for(native)' in selector
        assert 'return _LegacyProtections(native)' in selector
        legacy={node.name:node for node in definitions['_LegacyProtections'].body if isinstance(node,ast.FunctionDef)}
        for field,factory in (('archive','archive_view'),('fence','published_fence'),('scheduler','mysql_scheduler')):
            assert factory+'(self._native)' in calls(legacy[field])
        assert 'release_retained_protections(configuration,request,root,claim)' in retry


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_both_packages_include_reviewed_failure_convergence(variant, packages):
    with tarfile.open(packages / ('backup-restore-' + variant + '.tgz')) as archive:
        for name in ('recovery_control_smallapp_native.py', 'recovery_control_executor.py',
                     'recovery_control_restore_catalogue.py'):
            expected = (ROOT / 'backend/src/main/resources' / name).read_bytes().replace(b'\r\n', b'\n')
            assert archive.extractfile('control/' + name).read().replace(b'\r\n', b'\n') == expected


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_both_packages_gate_owner_and_target_on_resource_budget(variant, packages):
    with tarfile.open(packages / ('backup-restore-' + variant + '.tgz')) as archive:
        name = 'common/recovery_resource_admission.py'
        assert archive.extractfile(name).read() == (ROOT / 'ops/recovery/recovery_resource_admission.py').read_bytes()
        owner = archive.extractfile('common/recovery_minimal.py').read().decode()
        assert 'reserve(configuration, request, root)' in owner
        assert 'release_success(configuration, request, root,' in owner
        for name, stage in [('recovery_minimal_runtime.py', 'target'), ('recovery_replace.py', 'replacement')]:
            code = archive.extractfile('common/' + name).read().decode().replace('\r\n', '\n')
            assert "admit(configuration, request, root, '" + stage + "'" in code


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_both_packages_preserve_isolation_order_checks(variant, packages):
    with tarfile.open(packages / ('backup-restore-' + variant + '.tgz')) as archive:
        name = 'common/recovery_firewall.py'
        assert archive.extractfile(name).read() == (ROOT / 'ops/recovery/recovery_firewall.py').read_bytes()
        for name in ('recovery_data.py',):
            code = archive.extractfile('common/' + name).read().decode()
            assert 'isolation_rule_effective(raw.decode(' in code
        runtime = archive.extractfile('common/recovery_minimal_runtime.py').read().decode()
        if variant == 'standard':
            assert "subnet_isolation_rule_effective(raw.decode('utf-8'), rule)" in runtime
            assert "require(first and shlex.split(first)" not in runtime
        else:
            assert 'subnet_isolation_rule_effective' not in runtime
            assert "isolation='NOT_CHECKED'" in runtime


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_variant_package_entries_and_real_file_manifest(packages, tmp_path, variant):
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path, filter='data')
    manifest = json.loads((tmp_path/'package.json').read_bytes())
    assert manifest['variant'] == variant
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((tmp_path/name).read_bytes()).hexdigest() == expected
    code = (tmp_path/'common/repository_minimal.py').read_text(encoding='utf-8')
    assert code.count(repr('prod-'+variant+'-')) == 2
    if variant == 'lightweight':
        assert 'payload_content=False' in code and 'verify_content=False' in code
        assert manifest['fileVerification'] is False
        # File changes no longer trigger an entry-time checksum scan.
        with (tmp_path/'common/repository_cli.py').open('a', encoding='utf-8') as output:
            output.write('\n# changed since packaging: lightweight does not verify source files\n')
    for role in ('repository', 'recovery', 'control'):
        result = subprocess.run([sys.executable, str(tmp_path/(role+'_entry.py')), '--check-imports'],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)['role'] == role


def test_existing_outputs_cannot_be_overwritten(packages):
    before = (packages/'backup-restore-standard.tgz').read_bytes()
    with pytest.raises(FileExistsError, match='VARIANT_OUTPUT_ALREADY_EXISTS'):
        builder.build(packages)
    assert (packages/'backup-restore-standard.tgz').read_bytes() == before


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_replacement_preparation_matches_its_actual_file_engine(packages, tmp_path, variant):
    """Exercise the shipped caller and file engine, including real local removal."""
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path/'package', filter='data')
    program = r'''
import ast,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1])
import recovery_replace as replace
root=Path(sys.argv[2]);root.mkdir()
(root/'old-attachment').write_bytes(b'existing local component fixture')
work=root.parent/'work';work.mkdir()
calls=[]
class Mysql:
 def query(self,statement,**kwargs):
  calls.append({'sql':statement,'mutation':kwargs.get('mutation',False)})
  return '1' if statement=='SELECT @@GLOBAL.log_bin;' else ''
native=SimpleNamespace(root=work,original={'targetConfigRef':'component-target'},
 config={'database':'component_test','application':{'startOrder':['backend','frontend']},
         'redisRebuild':{'database':0},'redisClientPath':'redis-cli'},
 config_services={r:{'id':r} for r in ('backend','frontend','minio','redis')},
 policy={'minioDataMount':'/data'},mysql=Mysql(),guard=lambda:None,
 docker=lambda *a,**k:b'',secret=lambda *a:'component-secret',mutation_dispatched=False)
replace.verify_services=lambda *a:None
replace.prepare(native,{'databaseUuid':'component-db',
 'services':{'minio':{'id':'minio','mounts':[{'Destination':'/data','RW':True,'Source':str(root)}]}}})
assert not list(root.iterdir())
assert json.loads((work/'replacement-prepared.json').read_text())['state']=='PREPARED'
drop=next(c for c in calls if c['sql'].startswith('DROP DATABASE'))
assert drop['mutation'] is True,'Destructive SQL must be recorded as a mutation'
# Exercise the shipped nested query wrapper itself, rather than only a stub.
tree=ast.parse((Path(sys.argv[1])/'recovery_minimal_runtime.py').read_text())
bound=next(n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='BoundMySql')
query=next(n for n in bound.body if isinstance(n,ast.FunctionDef) and n.name=='query')
recorded=[]
native=SimpleNamespace(db_container='component-db',policy={'environmentMysqlClientPath':'/usr/bin/mysql'},
 docker=lambda args,**kwargs:recorded.append(kwargs) or b'query-result')
scope={'native':native}
exec(compile(ast.Module(body=[query],type_ignores=[]),'shipped-query-wrapper','exec'),scope)
assert scope['query'](None,'DROP DATABASE `component_test`;',mutation=True)=='query-result'
assert recorded==[{'mutation':True}]
print(json.dumps({'prepared':True,'destructiveSqlTracked':True}))
'''
    result=subprocess.run([sys.executable,'-c',program,str(tmp_path/'package/common'),str(tmp_path/'data')],
                          capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('registered_main',[True,False])
def test_safe_registered_main_archive_inputs_do_not_require_rehearsal_firewall(packages,tmp_path,registered_main):
    """Execute the shipped initializer's actual lease/hash block on real files."""
    if sys.platform!='linux':pytest.skip('Real Linux O_PATH/inotify lease required')
    with tarfile.open(packages/'backup-restore-standard.tgz') as archive:
        archive.extractall(tmp_path/'package',filter='data')
    program=r'''
import ast,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]+'/common')
from recovery_engine import pin,require,absolute,signature,check_pin
root=Path(sys.argv[2]);root.mkdir()
files=[]
for name in ('payload','version','material','docker','input'):
 p=root/name;p.write_bytes(name.encode());files.append(p)
payload,version,material,docker,control=[pin(p) for p in files]
target={'dockerPin':docker,'iptablesPin':{'path':str(root/'missing-rehearsal-iptables'),'bytes':1,'sha256':'0'*64}}
main=sys.argv[3]=='True'
if main:target['mainApplication']={'contract':'registered MAIN path selected before initialization'}
chain=[(material,None,{'payloadPins':[payload],'versionPins':[version]},material)]
self=SimpleNamespace(input_pins=[control])
tree=ast.parse((Path(sys.argv[1])/'common/recovery_minimal_runtime.py').read_text())
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MinimalData')
initialize=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_initialize')
def assigns(node,attribute):
 return isinstance(node,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr==attribute for t in node.targets)
start=next(i for i,n in enumerate(initialize.body) if assigns(n,'payload_signatures'))
stop=next(i for i,n in enumerate(initialize.body) if assigns(n,'target'))
block=compile(ast.Module(body=initialize.body[start:stop],type_ignores=[]),'shipped-safe-archive-input-lease','exec')
scope=dict(self=self,target=target,chain=chain,require=require,absolute=absolute,signature=signature,check_pin=check_pin)
try:
 try:exec(block,scope)
 except FileNotFoundError:
  assert not main,'Registered MAIN must not lease an unused rehearsal firewall executable'
 else:
  assert main,'Rehearsal must still require its actual firewall executable'
  assert set(self.payload_signatures)=={str(p) for p in files}
  assert set(self.archive_guard.path_fds)>={str(p) for p in files} or set(map(str,self.archive_guard.path_fds))>={str(p) for p in files}
  self.archive_guard.check()
finally:
 if getattr(self,'archive_guard',None) is not None:self.archive_guard.close()
print(json.dumps({'registeredMain':main,'allArchiveVersionDockerAndInputLeasesRequired':True}))
'''
    result=subprocess.run([sys.executable,'-B','-c',program,str(tmp_path/'package'),str(tmp_path/'files'),str(registered_main)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('variant', builder.VARIANTS)
def test_packaged_data_limits_reject_invalid_budget_before_target_access(packages, tmp_path, variant):
    """Use shipped constructor and formal validator before any native I/O."""
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path/'package', filter='data')
    program = r'''
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path[:0]=[sys.argv[1]+'/common',sys.argv[1]+'/formal']
import recovery_minimal_runtime as runtime
runtime.os=SimpleNamespace(name='posix')
class TargetBoundary(Exception):pass
class Target(dict):
 def __getitem__(self,key):
  if key=='services':raise TargetBoundary('target access after budget validation')
  return super().__getitem__(key)
target=Target(dataPolicy={'businessInvariants':[]})
configuration={'environmentMysqlClientPath':'/usr/bin/mysql','maxExpandedBytes':64*1024**3,
 'formalModuleDirectory':sys.argv[1]+'/formal','deadlineMilliseconds':7200000}
chain=[(None,None,{'recoveryPoint':'component-point','objects':{'method':'PHYSICAL_FILES'}},None)]
for size,expected in [(64*1024**3,'FORMAL_DATA_LIMITS_REQUIRED'),(16*1024**3,'VALID')]:
 configuration['dataLimits']={'max_rows':10000000,'max_nodes':100000000,'max_bytes':size,'seconds':7200}
 try:
  runtime.MinimalData(configuration,{'operationId':'component','targetConfigRef':'component-target'},None,{},chain,target,Path(sys.argv[2]),[])
 except TargetBoundary:
  assert expected=='VALID','Invalid budget reached target access before formal validation'
 except Exception as error:
  assert expected!='VALID' and getattr(error,'code',str(error))=='FORMAL_DATA_LIMITS_REQUIRED',repr(error)
 else:raise AssertionError('Expected constructor boundary')
print('invalid budget rejected early; independent 64GiB SQL and 16GiB data limits accepted')
'''
    result=subprocess.run([sys.executable,'-c',program,str(tmp_path/'package'),str(tmp_path/'work')],
                          capture_output=True,text=True)
    assert result.returncode==0,result.stderr
