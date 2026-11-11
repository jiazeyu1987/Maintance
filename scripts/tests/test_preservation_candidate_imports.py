"""Actual official-writer candidates and isolated import routing; no business IO."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture(scope='module')
def official_candidate(tmp_path_factory):
    base = tmp_path_factory.mktemp('official-candidate')
    spec = importlib.util.spec_from_file_location('candidate_import_builder', ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    mapping = json.loads((ROOT/'ops/backup_engine/files.json').read_bytes())
    names = sorted(set(mapping) | {'ops/backup_engine/build_variants.py',
        'ops/backup_engine/standard_fixes.py', 'ops/backup_engine/files.json',
        'ops/backup_engine/baselines/backup-restore-standard-20261021.tgz'})
    before = {name:pin(ROOT/name) for name in names}
    frozen, origin = builder.standard_sources()
    payload = builder.safe_fixes(frozen)
    snapshot_sha = hashlib.sha256(builder.canonical(before)).hexdigest()
    origin.update(source='isolated-frozen-candidate-test', candidateOnly=True,
        candidateSourceSnapshotSha256=snapshot_sha)
    package = base/'standard-candidate.tgz'
    builder.write_package(package, 'standard', payload, origin)
    assert {name:pin(ROOT/name) for name in names} == before
    engine = base/'engine'; engine.mkdir()
    with tarfile.open(package) as archive:
        members = archive.getmembers()
        assert len({m.name for m in members}) == len(members)
        assert all(m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts for m in members)
        archive.extractall(engine, filter='data')
    metadata = json.loads((engine/'package.json').read_bytes())
    assert metadata['candidateOnly'] is True
    assert metadata['candidateSourceSnapshotSha256'] == snapshot_sha
    assert set(metadata['files']) | {'package.json'} == {m.name for m in members}
    assert not (engine/'common/repository_native_browser_schemas.json').exists()
    (base/'input-pins.json').write_text(json.dumps(before, sort_keys=True), encoding='utf-8')
    return engine


@pytest.mark.parametrize('scenario', ['late', 'missing', 'sha', 'undeclared',
    'preloaded', 'metadata', 'extra', 'manifest', 'ordinary_inputs', 'preservation_inputs'])
def test_manifest_candidate_import_routing(official_candidate, tmp_path, scenario):
    engine = tmp_path/'engine'; shutil.copytree(official_candidate, engine)
    shadow = tmp_path/'source-shadow'; shadow.mkdir()
    (shadow/'recovery_program_containers.py').write_text("raise AssertionError('SOURCE_EXECUTED')\n", encoding='utf-8')
    (shadow/'recovery_unpublished.py').write_text("raise AssertionError('UNDECLARED_SOURCE_EXECUTED')\n", encoding='utf-8')
    script = r'''
from pathlib import Path
from types import ModuleType
import hashlib,importlib,importlib.metadata,json,sys
task,engine,shadow=map(Path,sys.argv[1:4]);scenario=sys.argv[4]
sys.path.insert(0,str(task))
from preservation_candidate_imports import candidate_imports
raw=(engine/'package.json').read_bytes()
reference=dict(path=str((engine/'package.json').resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
target=engine/'common/recovery_program_containers.py'
if scenario=='missing':target.unlink()
if scenario=='manifest':
 value=json.loads(raw);value['packageSha256']='0'*64
 raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n'
 (engine/'package.json').write_bytes(raw)
 reference.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if scenario=='preloaded':
 module=ModuleType('recovery_program_containers');module.__file__=str(shadow/'recovery_program_containers.py')
 sys.modules[module.__name__]=module
expected={'missing':'CANDIDATE_MEMBER_MISSING','sha':'CANDIDATE_MEMBER_CHANGED',
 'undeclared':'CANDIDATE_MODULE_UNDECLARED','preloaded':'CANDIDATE_MODULE_PRELOADED',
 'extra':'CANDIDATE_FILE_SET_CHANGED','manifest':'CANDIDATE_MANIFEST_DIGEST_CHANGED'}
before=importlib.metadata.version('pytest')
try:
 with candidate_imports(engine,reference) as route:
  sys.path.insert(0,str(shadow))
  if scenario=='sha':target.write_bytes(target.read_bytes()+b'\n# drift\n')
  if scenario=='extra':(engine/'common/extra-resource.json').write_bytes(b'{}')
  elif scenario=='undeclared':importlib.import_module('recovery_unpublished')
  elif scenario in ('late','sha'):
   module=importlib.import_module('recovery_program_containers')
   assert Path(module.__file__).resolve()==target.resolve()
   assert hashlib.sha256(target.read_bytes()).hexdigest()==route.manifest['files']['common/recovery_program_containers.py']
  elif scenario in ('ordinary_inputs','preservation_inputs'):
   name={'ordinary_inputs':'recovery_restore_inputs',
    'preservation_inputs':'recovery_preservation_inputs'}[scenario]
   member='common/'+name+'.py'
   module=importlib.import_module(name)
   actual=engine/member
   assert Path(module.__file__).resolve()==actual.resolve()
   assert hashlib.sha256(actual.read_bytes()).hexdigest()==route.manifest['files'][member]
   assert actual.read_bytes()==(task.parents[2]/'ops/recovery'/(name+'.py')).read_bytes()
  if scenario=='metadata':
   distribution=importlib.metadata.distribution('pytest')
   import pytest
   assert distribution.version==before==pytest.__version__
   assert distribution.files and distribution.read_text('METADATA')
except RuntimeError as error:
 assert scenario in expected and str(error)==expected[scenario],(scenario,str(error))
else:
 assert scenario in ('late','metadata','ordinary_inputs','preservation_inputs'),'INVALID_CANDIDATE_ACCEPTED '+scenario
assert importlib.metadata.version('pytest')==before
print('ACTUAL_CANDIDATE_ROUTE_PASS '+scenario)
'''
    result = subprocess.run([sys.executable,'-B','-X','utf8','-c',script,
        str(TASK),str(engine),str(shadow),scenario], capture_output=True,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'), timeout=60)
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8', errors='replace')
    assert result.stdout.rstrip().endswith(('ACTUAL_CANDIDATE_ROUTE_PASS '+scenario).encode())


@pytest.mark.parametrize('name', ['recovery_restore_inputs', 'recovery_preservation_inputs'])
def test_lightweight_declares_actual_restore_input_members(name):
    spec = importlib.util.spec_from_file_location('restore_input_lightweight_builder',
        ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    mapping = json.loads((ROOT/'ops/backup_engine/files.json').read_bytes())
    source, member = 'ops/recovery/'+name+'.py', 'common/'+name+'.py'
    assert mapping.get(source) == member
    payload, origin = builder.lightweight_sources()
    assert origin['source'] == 'explicit-working-tree-snapshot'
    assert payload[member] == (ROOT/source).read_bytes()
