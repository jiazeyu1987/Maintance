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
        'control/recovery_control_point_quarantine.py', 'formal/formal_binlog_scope.py',
        'common/recovery_replace.py', 'common/recovery_data.py', 'formal/formal_data_evidence.py',
        'common/recovery_main_target.py', 'common/recovery_replacement_storage.py', 'common/recovery_minimal_plan.py',
        'common/recovery_retained_retry.py',
        'control/recovery_control_restore_catalogue.py', 'control/recovery_control_smallapp_http.py',
        'formal/minimal_capture_support.py', 'formal/minimal_capture_worker.py',
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
def test_both_packages_include_reviewed_failure_convergence(variant, packages):
    with tarfile.open(packages / ('backup-restore-' + variant + '.tgz')) as archive:
        for name in ('recovery_control_smallapp_native.py', 'recovery_control_executor.py'):
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
  runtime.MinimalData(configuration,{'operationId':'component'},None,{},chain,target,Path(sys.argv[2]),[])
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
