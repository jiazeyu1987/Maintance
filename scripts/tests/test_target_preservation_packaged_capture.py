"""Pure authenticated payload contracts and actual child-worker admission.

No build/deployment or business restore is claimed. Control adapters below
inject only the external registration/file protocol, never an owner success.
The delivered-package full constructor/restore suite is a separate boundary.
"""
from copy import deepcopy
from contextlib import nullcontext
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'backend/src/main/resources'), str(ROOT/'ops/recovery')]
import recovery_minimal_runtime as runtime
from recovery_engine import RecoveryError, canonical, pin, write
from recovery_control_smallapp import Failure
from recovery_control_smallapp_native import Native
import recovery_control_target_availability as availability
import recovery_control_executor as executor


def request():
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='capability-test-1',
        action='RESTORE', sourceConfigRef='source57', parentChainRef=None,
        recoveryPointRef='point1', targetConfigRef='target57')


@pytest.fixture(scope='module')
def builder():
    path = ROOT/'ops/backup_engine/build_variants.py'
    spec = importlib.util.spec_from_file_location('preservation_scope_builder', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture(scope='module')
def safe_payload(builder):
    baseline, _ = builder.standard_sources()
    return builder.safe_fixes(baseline)


@pytest.mark.parametrize('caller_grant', [False, True])
def test_actual_light_worker_rejects_main_before_any_replacement(tmp_path, caller_grant):
    owner = dict(operationsRoot=str(tmp_path), targets={'target57':dict(mainApplication={},
        supports_main_target_preservation=caller_grant)}, supports_main_target_preservation=caller_grant)
    configuration = write(tmp_path/'configuration.json', owner)
    ui = write(tmp_path/'request.json', request())
    output = tmp_path/'worker-result.json'
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run([sys.executable, '-B', str(ROOT/'ops/recovery/recovery_minimal_worker.py'),
        '--configuration', configuration['path'], '--request', ui['path'], '--output', str(output)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
    assert output.is_file(), (process.returncode, process.stderr.decode('utf-8', errors='replace'))
    result = json.loads(output.read_bytes())
    assert result['failureCode'] == 'MAIN_PRESERVATION_REQUIRES_SAFE_ENGINE', result
    assert process.returncode == result['actualExitCode'] == 1
    assert result['state'] == 'FAILED_RETAINED' and result['data']['mutationDispatched'] is False
    assert {p.name for p in tmp_path.iterdir()} == {'configuration.json','request.json','worker-result.json'}


def test_direct_empty_light_entry_cannot_bypass_main_capability(tmp_path):
    with pytest.raises(RecoveryError, match='^MAIN_PRESERVATION_REQUIRES_SAFE_ENGINE$'):
        runtime.execute_empty(dict(targets={'target57':dict(mainApplication={})}), request(), tmp_path, [])
    assert not list(tmp_path.iterdir())


def test_light_ordinary_target_keeps_original_dispatch(monkeypatch, tmp_path):
    seen = []
    def original(*args):
        seen.append(args)
        raise RecoveryError('ORDINARY_EXECUTION_BOUNDARY')
    monkeypatch.setattr(runtime, 'execute_empty', original)
    with pytest.raises(RecoveryError, match='^ORDINARY_EXECUTION_BOUNDARY$'):
        runtime.execute(dict(targets={'target57':{}}), request(), tmp_path, [])
    assert len(seen) == 1


@pytest.mark.parametrize('observe_main', [False, True])
def test_control_target_preflight_refuses_light_even_without_live_observation(tmp_path, monkeypatch, observe_main):
    owner = dict(targets={'target57':dict(mainApplication={})})
    reference = write(tmp_path/'owner.json', owner)
    native = SimpleNamespace(document=lambda p: json.loads(Path(p['path']).read_bytes()))
    # Availability of the target's ordinary claim is a separate unit boundary;
    # no native observation or successful restore is replaced here.
    monkeypatch.setattr(availability, 'unclaimed_target', lambda *a, **k: True)
    with pytest.raises(Failure, match='^MAIN_PRESERVATION_REQUIRES_SAFE_ENGINE$'):
        availability.available(native, reference, 'target57', 'source57', observe_main=observe_main)


def test_control_submit_refuses_light_before_dispatch(tmp_path, monkeypatch):
    source_pin = write(tmp_path/'source-owner.json', {})
    target_pin = write(tmp_path/'target-owner.json', dict(sources={'source57':{}},
        targets={'target57':dict(mainApplication={})}))
    owner_program = pin(Path(runtime.__file__))
    control = dict(sourceConfigurations={'source57':source_pin},
        restoreConfigurations={'source57':{'target57':target_pin}}, programPins={'recovery':owner_program})
    adapter = SimpleNamespace(config_pin=source_pin, configuration=lambda:deepcopy(control),
        registration=lambda ref:(dict(allowedRestoreTargets=[dict(configRef='target57')]), source_pin),
        document=lambda p:json.loads(Path(p['path']).read_bytes()), point=lambda *a:source_pin)
    checked = []
    monkeypatch.setattr(executor, 'verify', lambda p:checked.append(p))
    with pytest.raises(Failure, match='^MAIN_PRESERVATION_REQUIRES_SAFE_ENGINE$'):
        Native.resolve(adapter, request())
    assert checked == [owner_program]


@pytest.mark.parametrize('member,source', [
    ('common/recovery_capture_materials.py','ops/recovery/recovery_capture_materials.py'),
    ('common/recovery_target_capture.py','ops/recovery/recovery_target_capture.py'),
    ('common/recovery_target_preservation.py','ops/recovery/recovery_target_preservation.py'),
    ('common/recovery_preservation_source.py','ops/recovery/recovery_preservation_source.py'),
])
def test_safe_has_reviewed_typed_members(safe_payload, member, source):
    assert member in safe_payload, 'SAFE_PRESERVATION_MEMBER_MISSING '+member
    if member != 'common/recovery_capture_materials.py':
        assert safe_payload[member] == (ROOT/source).read_bytes()
    else:
        # The only SAFE-specific changes are the explicit SOURCE adapters;
        # every MAIN/shared strict algorithm must remain exactly the source.
        expected = ast.parse((ROOT/source).read_bytes())
        actual = ast.parse(safe_payload[member])
        for tree in (expected, actual):
            owner = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SourceCaptureLifecycle')
            owner.body = [n for n in owner.body if not isinstance(n,ast.FunctionDef) or
                n.name not in ('_capture_database','_save_images','_verify_parent')]
        assert ast.dump(actual) == ast.dump(expected)


def test_light_manifest_adds_typed_members_without_changing_formal_algorithms():
    mapping = json.loads((ROOT/'ops/backup_engine/files.json').read_bytes())
    for name in ('recovery_capture_materials','recovery_target_capture','recovery_target_preservation',
            'recovery_preservation_source'):
        assert mapping.get('ops/recovery/'+name+'.py') == 'common/'+name+'.py'
    assert mapping['ops/backup_engine/formal/minimal_capture_worker.py'] == 'formal/minimal_capture_worker.py'
    assert mapping['ops/backup_engine/formal/minimal_capture_support.py'] == 'formal/minimal_capture_support.py'


def test_safe_runtime_explicitly_grants_only_authenticated_implementation(safe_payload):
    nodes = [n for n in ast.parse(safe_payload['common/recovery_minimal_runtime.py']).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and
            t.id == 'supports_main_target_preservation' for t in n.targets)]
    assert len(nodes) == 1 and ast.literal_eval(nodes[0].value) is True, 'SAFE_PRESERVATION_CAPABILITY_MISSING'
    assert getattr(runtime,'supports_main_target_preservation',None) is False


@pytest.mark.parametrize('function', ['execute', 'execute_empty'])
def test_safe_checks_capability_once_at_each_public_execution_boundary(safe_payload, function):
    text = safe_payload['common/recovery_minimal_runtime.py'].decode('utf-8')
    node = next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==function)
    calls = [n for n in ast.walk(node) if isinstance(n,ast.Call) and
        isinstance(n.func,ast.Name) and n.func.id=='_require_main_capability']
    assert len(calls) == 1, 'CAPABILITY_BOUNDARY_MUST_BE_SINGLE'
    assert isinstance(node.body[0],ast.Expr) and node.body[0].value is calls[0]


def test_safe_source_worker_reuses_materials_and_original_restoration(safe_payload):
    text = safe_payload['formal/minimal_capture_worker.py'].decode('utf-8')
    node = next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='capture_locked')
    method = ast.get_source_segment(text,node)
    assert 'capture_protected_materials(prepared, lifecycle)' in method, 'SAFE_SHARED_CAPTURE_NOT_WIRED'
    assert "result['sourceRestorationPin'] = restored" in method and 'runtime.restore()' in method
    assert 'semantic.verify_parent()' in method and 'semantic.close()' in method


@pytest.mark.parametrize('member,owner,method', [
    ('formal/minimal_capture_support.py','MinimalSemantic','__init__'),
    ('formal/formal_capture_semantics.py','SemanticCapture','verify_endpoint'),
    ('formal/formal_snapshot_linux.py','PrivateDockerMySql','__init__'),
])
def test_safe_real_capture_classes_accept_typed_observer(safe_payload, member, owner, method):
    tree=ast.parse(safe_payload[member]); cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==owner)
    function=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==method)
    assert 'process_observer' in [a.arg for a in function.args.kwonlyargs], 'SAFE_OBSERVER_MISSING '+owner+'.'+method


def test_safe_runtime_preserves_proof_identity_before_first_bound(safe_payload):
    text=safe_payload['common/recovery_minimal_runtime.py'].decode('utf-8')
    assert text.count('require_preservation(native_context._context') >= 2, 'SAFE_PRESERVATION_HANDOFF_MISSING'
    assert 'target_preservation=None' in text
    assert 'fresh_target' in text and 'native.archive_guard.close()' in text


def declaration(raw, owner, name):
    text = raw.decode('utf-8').replace('\r\n', '\n') if isinstance(raw, bytes) else raw
    tree = ast.parse(text)
    body = tree.body if owner is None else next(n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == owner).body
    node = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])


def test_safe_source_keeps_authenticated_database_and_image_cache(safe_payload):
    core = safe_payload.get('common/recovery_capture_materials.py', b'')
    assert b'def _capture_database(' in core, 'SAFE_SOURCE_DATABASE_HOOK_MISSING'
    database = declaration(core, 'SourceCaptureLifecycle', '_capture_database')
    assert 'self.worker.capture_database(' in database
    image = declaration(core, 'SourceCaptureLifecycle', '_save_images')
    assert 'capture_images(' in image and "runtime.event('IMAGE_EXPORT_COMPLETE'" in image
    assert 'result=image_pin' in image and 'return image_pin' in image
    # Existing FULL/incremental observation and cache implementation are not
    # replaced by the shared MAIN algorithm. This is exact method evidence.
    body = declaration(safe_payload['formal/minimal_capture_worker.py'], None, 'capture_database')
    assert hashlib.sha256(body.encode()).hexdigest() == \
        '305ead2e88c68896479889368be0bf7a06915683d880f53e903fca3b63ec43bb'


def test_safe_source_preparation_keeps_endpoint_redis_and_tools_before_stop(safe_payload):
    core = safe_payload.get('common/recovery_capture_materials.py', b'')
    assert b'def _admit_semantic(' in core, 'SAFE_SOURCE_ADMISSION_HOOK_MISSING'
    method = declaration(core, 'SourceCaptureLifecycle', '_admit_semantic')
    assert 'semantic.verify_endpoint(' in method and 'redis_preflight(' in method
    assert "programs.append('mysqldump')" in method and 'self.runtime.command(' in method
    prepared = declaration(core, None, 'prepare_materials')
    assert prepared.index('transport._admit_semantic(') < prepared.index("runtime.phase='CONFIGURATION_AND_IMAGE_CAPTURE'")
    captured = declaration(core, None, 'capture_protected_materials')
    assert captured.index('lifecycle._verify_parent(semantic)') < captured.index('capture_recovery_inputs(')
    parent = declaration(core, 'SourceCaptureLifecycle', '_verify_parent')
    assert 'semantic.verify_parent()' in parent


@pytest.mark.parametrize('cleanup_error', [False, True])
def test_safe_source_preparation_failure_closes_actual_semantic_owner(safe_payload, monkeypatch, tmp_path, cleanup_error):
    """Worker ownership unit seam; no source capture/business success is claimed."""
    import types
    closed = []
    class Semantic:
        def close(self):
            closed.append(True)
            if cleanup_error:
                raise RuntimeError('PARENT_CLOSE_FAILED')
    class Lifecycle:
        def __init__(self, runtime):
            self.semantic = Semantic()
    def failed_prepare(*args, **kwargs):
        raise RuntimeError('IMAGE_PREPARATION_FAILED')
    adapter = types.ModuleType('recovery_capture_materials')
    adapter.SourceCaptureLifecycle = Lifecycle
    adapter.prepare_materials = failed_prepare
    adapter.capture_protected_materials = lambda *a: pytest.fail('capture after preparation failed')
    monkeypatch.setitem(sys.modules, 'recovery_capture_materials', adapter)
    state = SimpleNamespace(preflight=lambda:None)
    budget = SimpleNamespace(check=lambda:None, deadline=123.0, activate=nullcontext)
    class Deadline:
        def set(self, value): return value
        def reset(self, token): pass
    namespace = dict(Originals=lambda guard:object(), observation_deadline=Deadline(),
        diagnostic_value=lambda value:value, failure_code=lambda error:str(error))
    method = declaration(safe_payload['formal/minimal_capture_worker.py'], None, 'capture_locked')
    assert 'SourceCaptureLifecycle(' in method, 'SAFE_SOURCE_OWNER_NOT_WIRED'
    exec(method, namespace)
    with pytest.raises(RuntimeError, match='^IMAGE_PREPARATION_FAILED$') as caught:
        namespace['capture_locked'](dict(source={}), request(), tmp_path, budget, state)
    assert closed == [True]
    if cleanup_error:
        assert caught.value.diagnostic['parentLeaseCleanupFailureCode'] == 'PARENT_CLOSE_FAILED'


def test_light_ordinary_retention_import_has_no_strict_capture_dependency(builder, tmp_path):
    """Actual LIGHT candidate imports, no capture capability or business action."""
    payload, _ = builder.lightweight_sources()
    engine = tmp_path/'engine'
    for name, raw in payload.items():
        target = engine/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    repository = tmp_path/'repository'; repository.mkdir()
    script = r'''
from pathlib import Path
from types import SimpleNamespace
import sys
engine,repository=map(Path,sys.argv[1:3])
sys.path[:0]=[str(engine/'common'),str(engine/'formal')]
import repository_retention as retention
from repository_records import RepositoryError
import recovery_target_preservation as preservation
assert Path(retention.__file__).resolve().parent==(engine/'common').resolve()
assert Path(preservation.__file__).resolve().parent==(engine/'common').resolve()
assert preservation.preservation_holds(SimpleNamespace(root=repository),guard=lambda:None)==set()
catalog=SimpleNamespace(config=SimpleNamespace(root=repository),list=lambda:[],
    deadline=SimpleNamespace(check=lambda:None))
try:
 retention.plan_retention(catalog,{})
except RepositoryError as error:
 assert str(error)=='REPOSITORY_RETENTION_EMPTY'
else:
 raise AssertionError('ordinary empty repository was accepted')
assert 'recovery_target_capture' not in sys.modules
print('LIGHT_ORDINARY_RETENTION_IMPORT_PASS')
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(engine),str(repository)],
        capture_output=True,timeout=60)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.rstrip().endswith(b'LIGHT_ORDINARY_RETENTION_IMPORT_PASS')


@pytest.fixture(scope='module')
def safe_candidate_directory(safe_payload, tmp_path_factory):
    # Authentication/transform output only, not a release build: no tar,
    # package.json, version identity, deployment or fabricated manifest.
    engine = tmp_path_factory.mktemp('authenticated-safe-candidate')
    for name, raw in safe_payload.items():
        target = engine/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return engine


@pytest.mark.parametrize('problem', ['headers', 'short', 'long'])
def test_safe_actual_content_reader_rejects_protocol_drift(safe_candidate_directory, problem):
    """Real SAFE method and real byte stream; finite S3 protocol unit only."""
    script = r'''
from pathlib import Path
from types import SimpleNamespace
import hashlib,io,sys
engine=Path(sys.argv[1]);problem=sys.argv[2]
sys.path[:0]=[str(engine/'common'),str(engine/'formal')]
import formal_capture_semantics as semantic
import formal_snapshot_linux as snapshot
assert Path(semantic.__file__).resolve().parent==(engine/'formal').resolve()
assert Path(snapshot.__file__).resolve().parent==(engine/'formal').resolve()
row=dict(key='private/object',versionId='null',size=3,etag='"tag"')
headers={'content-length':'3','etag':'"tag"'}
if problem=='headers':headers['content-length']='4'
raw=b'ab' if problem=='short' else b'abcd' if problem=='long' else b'abc'
response=io.BytesIO(raw)
client=SimpleNamespace(content=lambda *a:(response,headers))
try:
 semantic.SemanticCapture._read_content(SimpleNamespace(client=client),'private',row,lambda:None)
except snapshot.FormalSnapshotError as error:
 assert str(error)=='FORMAL_CAPTURE_OBJECT_CONTENT_CHANGED'
else:
 raise AssertionError('SAFE content drift was accepted')
assert response.closed
print('ACTUAL_SAFE_CONTENT_REJECTION '+problem)
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(safe_candidate_directory),problem],
        capture_output=True,timeout=60)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.rstrip().endswith(('ACTUAL_SAFE_CONTENT_REJECTION '+problem).encode())


@pytest.mark.parametrize('scenario', ['safe-live', 'safe-skip', 'light-main', 'light-ordinary'])
def test_actual_control_candidate_keeps_catalogue_capability_contract(
        builder, safe_candidate_directory, tmp_path, scenario):
    """Actual runtime/control imports; claim and live observation are unit seams."""
    engine = safe_candidate_directory
    if scenario.startswith('light-'):
        payload, _ = builder.lightweight_sources()
        engine = tmp_path/'light-engine'
        for name, raw in payload.items():
            path = engine/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    script = r'''
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,sys,unittest
engine,root=map(Path,sys.argv[1:3]);scenario=sys.argv[3]
sys.path[:0]=[str(engine/'common'),str(engine/'formal'),str(engine/'control'),str(root/'scripts/tests')]
import recovery_minimal_runtime as runtime
import recovery_control_smallapp_native as native
import recovery_control_target_availability as availability
tracked=(runtime,native,availability)
pins={m.__name__:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in tracked}
for module in tracked:
 assert Path(module.__file__).resolve().parent in {(engine/p).resolve() for p in ('common','control')}
assert runtime.supports_main_target_preservation is scenario.startswith('safe-')
if scenario=='light-ordinary':
 adapter=SimpleNamespace(document=lambda pin:dict(targets={'target-B':{}}))
 with patch.object(availability,'unclaimed_target',return_value=True) as claimed:
  assert availability.available(adapter,'owner','target-B','source-A') is True
  assert claimed.call_count==1
else:
 from test_restore_archive_catalogue import ArchiveCatalogue
 name={'safe-live':'test_main_availability_observes_live_target_and_propagates_identity_errors',
  'safe-skip':'test_source_catalogue_can_skip_live_main_probe_without_masking_selected_target_error',
  'light-main':'test_lightweight_control_refuses_main_target_before_configuration_binding'}[scenario]
 result=unittest.TestResult();ArchiveCatalogue(name).run(result)
 if not result.wasSuccessful():
  for _,trace in result.errors+result.failures:print(trace,flush=True)
  raise AssertionError('ORIGINAL_CATALOGUE_CAPABILITY_CONTRACT_FAILED '+scenario)
for module in tracked:
 assert sys.modules[module.__name__] is module
 assert hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()==pins[module.__name__]
print('ACTUAL_CONTROL_CANDIDATE_CONTRACT_PASS '+scenario)
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(engine),str(ROOT),scenario],
        capture_output=True,timeout=90)
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8',errors='replace')
    assert result.stdout.rstrip().endswith(('ACTUAL_CONTROL_CANDIDATE_CONTRACT_PASS '+scenario).encode())


@pytest.mark.parametrize('entry', ['main', 'source'])
@pytest.mark.parametrize('problem', ['valid', 'content', 'listing', 'multipart'])
def test_actual_safe_offline_verifier_propagates_main_observer_and_keeps_source_checks(
        safe_candidate_directory, safe_payload, entry, problem):
    """Actual candidate method delegation; finite S3/endpoint protocol only.

    This proves the optional argument/strict verifier contract, not a complete
    context construction, business restore or server observation.
    """
    script = r'''
from pathlib import Path
from types import SimpleNamespace
import hashlib,io,sys
engine=Path(sys.argv[1]);entry,problem=sys.argv[2:4]
sys.path[:0]=[str(engine/'common'),str(engine/'formal')]
import minimal_capture_worker as worker
import recovery_target_capture as capture
import formal_capture_semantics as semantics
import formal_snapshot_linux as snapshot
for module,folder in ((worker,'formal'),(capture,'common'),(semantics,'formal'),(snapshot,'formal')):
 assert Path(module.__file__).resolve().parent==(engine/folder).resolve()
pins={module.__name__:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
 for module in (worker,capture,semantics,snapshot)}
calls=[];responses=[];observer=object();guard=lambda:calls.append('guard')
row=dict(kind='version',key='private/object',versionId='null',isLatest=True,
 lastModified='2026-11-10T00:00:00Z',size=3,etag='"finite-etag"')
record=dict(row,bucket='private',sha256=hashlib.sha256(b'abc').hexdigest(),
 repositoryPath='objects/finite.bin',headers={'content-type':'text/plain'})
def versions(bucket,cursor):
 assert (bucket,cursor)==('private',None)
 calls.append('listing')
 value=dict(row)
 if problem=='listing' and calls.count('listing')==2:value['etag']='"drift"'
 return [value],None
def multipart(bucket):
 assert bucket=='private';calls.append('multipart')
 return dict(bucket=bucket,state='NO_MULTIPART_UPLOAD_OBSERVED',httpStatus=200,
  rawSha256='a'*64,rawBytes=1,maxUploads=1,uploadCount=1 if problem=='multipart' else 0,
  isTruncated=False,scope='WHOLE_BUCKET_FROM_START')
def content(bucket,key,version):
 assert (bucket,key,version)==('private','private/object','null');calls.append('content')
 response=io.BytesIO(b'abd' if problem=='content' else b'abc');responses.append(response)
 return response,{'content-length':'3','etag':'"finite-etag"','content-type':'text/plain'}
def endpoint(actual_guard,**kwargs):
 assert actual_guard is guard
 assert kwargs==({'process_observer':observer} if entry=='main' else {})
 calls.append('endpoint')
semantic=object.__new__(semantics.SemanticCapture)
semantic.source={'buckets':['private']};semantic.records=[record]
semantic.client=SimpleNamespace(versions=versions,multipart_empty=multipart,content=content)
semantic.verify_endpoint=endpoint
runtime=SimpleNamespace(protected=guard)
session=object.__new__(capture.MainTargetCapture)
session.worker=worker;session._observer=observer;session.protected=guard
expected={'content':'MINIMAL_OBJECT_OFFLINE_POINT_CHANGED',
 'listing':'MINIMAL_OBJECT_OFFLINE_POINT_CHANGED','multipart':'FORMAL_S3_MULTIPART_LIST_INVALID'}
try:
 if entry=='main':session._verify_objects(semantic)
 else:worker.verify_objects_after_offline(semantic,runtime)
except snapshot.FormalSnapshotError as error:
 assert problem!='valid' and str(error)==expected[problem],str(error)
else:
 assert problem=='valid','strict SAFE verifier accepted drift'
assert calls.count('endpoint')==1
assert calls.count('listing')==(2 if problem in ('valid','listing') else 1)
assert calls.count('multipart')==1
assert calls.count('content')==(0 if problem=='multipart' else 1)
assert all(response.closed for response in responses)
for name,sha in pins.items():
 assert hashlib.sha256(Path(sys.modules[name].__file__).read_bytes()).hexdigest()==sha
print('ACTUAL_SAFE_OFFLINE_VERIFIER_PASS '+entry+' '+problem)
'''
    result = subprocess.run([sys.executable, '-B', '-c', script,
        str(safe_candidate_directory), entry, problem], capture_output=True, timeout=60)
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8', errors='replace')
    assert result.stdout.rstrip().endswith(('ACTUAL_SAFE_OFFLINE_VERIFIER_PASS '+entry+' '+problem).encode())


def test_safe_offline_observer_transform_keeps_authenticated_checks(builder, safe_payload):
    baseline, _ = builder.standard_sources()
    member = 'formal/minimal_capture_worker.py'
    original = declaration(baseline[member], None, 'verify_objects_after_offline')
    assert hashlib.sha256(original.encode()).hexdigest() == \
        'f923288d37c422db7ee7443ee00603a2b5eb01bf528834fb5dbf8cc6e2da9091'
    updated = declaration(safe_payload[member], None, 'verify_objects_after_offline')
    # Undo only the two declared AST sites; all original checks/order remain.
    updated = updated.replace(', *, process_observer=None):', '):')
    branch = ('    if process_observer is None:\n'
        '        semantic.verify_endpoint(guard)\n'
        '    else:\n'
        '        semantic.verify_endpoint(guard, process_observer=process_observer)\n')
    assert updated.count(branch) == 1
    assert ast.dump(ast.parse(updated.replace(branch, '    semantic.verify_endpoint(guard)\n'))) == \
        ast.dump(ast.parse(original))
