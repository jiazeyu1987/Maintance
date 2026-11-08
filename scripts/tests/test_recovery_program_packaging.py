"""Exercise archived program handling inside both deliverable engines."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from test_recovery_program_archive import fixture_archive

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def program_packages(tmp_path_factory):
    spec = importlib.util.spec_from_file_location('program_package_builder', ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    output = tmp_path_factory.mktemp('program-packages')/'packages'
    builder.build(output)
    return output


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_inputs_execute_in_packaged_engine(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        for module in ('recovery_archive_versions', 'recovery_program_archive'):
            assert archive.extractfile('common/'+module+'.py').read() == (ROOT/'ops/recovery'/(module+'.py')).read_bytes()
        archive.extractall(engine, filter='data')
    path, roles = fixture_archive(tmp_path)
    version = tmp_path/'version.json'
    version.write_text(json.dumps({'images': roles}), encoding='utf-8')
    script = r'''
from pathlib import Path
import json,sys
engine,archive_path,version_path,test_root=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(test_root)]
import recovery_main_target
from recovery_engine import pin
from recovery_archive_versions import resolve_archive_images
from recovery_program_archive import inspect_program_archive
assert Path(recovery_main_target.__file__).resolve().parent == (engine/'common').resolve()
roles=json.loads(version_path.read_text(encoding='utf-8'))['images']
bindings=[dict(role=role,versionPath=['images',role]) for role in roles]
resolved=resolve_archive_images([pin(version_path)],bindings)
assert {role:row['imageId'] for role,row in resolved.items()}==roles
program=inspect_program_archive(pin(archive_path),roles,guard=lambda:None,architecture='amd64',max_archive_bytes=2**20)
assert {row['role']:row['imageId'] for row in program['images']}==roles
from test_main_restore_target import MainContractTests
case=MainContractTests()
case.setUp()
try:
 case.test_registered_main_accepts_matching_archived_program()
 case.test_archive_image_mismatch_blocks_before_reset()
finally:case.doCleanups()
print('PACKAGED_PROGRAM_INPUTS_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(path), str(version),
                             str(ROOT/'scripts/tests')], capture_output=True, timeout=60,
                            env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.strip() == b'PACKAGED_PROGRAM_INPUTS_PASS'


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_container_contract_executes_in_packaged_engine(variant, program_packages, tmp_path):
    from test_recovery_program_containers import original, image
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_program_containers.py').read() == (
            ROOT/'ops/recovery/recovery_program_containers.py').read_bytes()
        archive.extractall(engine, filter='data')
    inputs = tmp_path/'input.json'
    inputs.write_text(json.dumps(dict(original=original(), image=image())), encoding='utf-8')
    script = r'''
from copy import deepcopy
from pathlib import Path
import json,sys
engine,inputs=map(Path,sys.argv[1:])
sys.path.insert(0,str(engine/'common'))
import recovery_program_containers as program
assert Path(program.__file__).resolve().parent == (engine/'common').resolve()
values=json.loads(inputs.read_text(encoding='utf-8'));original=values['original']
request=program.create_request(original,values['image'])
created=deepcopy(original)
created.update(Id='b'*64,Image=values['image']['Id'],Config=request['Config'],HostConfig=request['HostConfig'])
created['NetworkSettings']['Networks']['task-network']['Aliases']=['program-backend','b'*12]
program.verify_created(original,request,created)
created['Image']='sha256:'+'3'*64
try:program.verify_created(original,request,created)
except Exception as error:assert error.code=='PROGRAM_CREATED_IDENTITY_CHANGED'
else:raise AssertionError('image drift accepted')
print('PACKAGED_PROGRAM_CONTAINER_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(inputs)],
        capture_output=True, timeout=60, env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.strip() == b'PACKAGED_PROGRAM_CONTAINER_PASS'


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_generation_resolves_in_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_program_generation.py').read() == (
            ROOT/'ops/recovery/recovery_program_generation.py').read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,test_root,work=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(test_root)]
import recovery_program_generation as generation
assert Path(generation.__file__).resolve().parent == (engine/'common').resolve()
from test_recovery_program_generation import case,test_initial_epoch_uses_exact_registered_configuration
from test_recovery_program_generation import test_completed_epoch_resolves_immutable_capture_and_target
from test_recovery_program_generation import test_successful_switch_advances_program_ids_and_capture_images
from test_recovery_program_generation import test_changed_generation_bytes_fail_pin_verification
checks=[test_initial_epoch_uses_exact_registered_configuration,
test_completed_epoch_resolves_immutable_capture_and_target,
test_successful_switch_advances_program_ids_and_capture_images,
test_changed_generation_bytes_fail_pin_verification]
for i,check in enumerate(checks):
 root=work/str(i);root.mkdir(mode=0o700)
 fixture=case.__wrapped__(root)
 if i==2:check(fixture,root)
 else:check(fixture)
assert Path(generation.__file__).resolve().parent == (engine/'common').resolve()
print('PACKAGED_PROGRAM_GENERATION_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests'), str(tmp_path)],
        capture_output=True, timeout=120, env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8',errors='replace')
    assert result.stdout.strip() == b'PACKAGED_PROGRAM_GENERATION_PASS'


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux flock required')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_activation_and_target_binding_execute_in_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        for name in ('recovery_program_activation', 'recovery_program_targets'):
            assert archive.extractfile('common/'+name+'.py').read() == (ROOT/'ops/recovery'/(name+'.py')).read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests,work=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(tests)]
import recovery_program_activation as activation
import recovery_program_targets as targets
assert Path(activation.__file__).resolve().parent == (engine/'common').resolve()
assert Path(targets.__file__).resolve().parent == (engine/'common').resolve()
from test_recovery_program_generation import case
from test_recovery_program_activation import test_locked_snapshot_and_stage_activate_only_after_real_success
from test_recovery_program_activation import test_switched_generation_produced_from_real_replacement_epoch
from test_recovery_program_activation import test_second_restore_continues_exact_parent_generation
checks=[test_locked_snapshot_and_stage_activate_only_after_real_success,
test_switched_generation_produced_from_real_replacement_epoch,test_second_restore_continues_exact_parent_generation]
for i,check in enumerate(checks):
 root=work/str(i);root.mkdir(mode=0o700)
 fixture=case.__wrapped__(root)
 if i==1:check(fixture,root)
 else:check(fixture)
 if i!=2:
  owner=dict(targets={'target57':fixture['target']},targetProgramPolicies={'target57':fixture['policy']},
      targetBackupEpochPolicies={'target57':fixture['epoch']})
  effective,binding=targets.resolve_configuration(owner,'target57')
  assert binding['targetPin'] in binding['evidencePins']
  assert effective['targets']['target57']['database']==owner['targets']['target57']['database']
assert Path(activation.__file__).resolve().parent == (engine/'common').resolve()
assert Path(targets.__file__).resolve().parent == (engine/'common').resolve()
print('PACKAGED_PROGRAM_ACTIVATION_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests'), str(tmp_path)],
        capture_output=True, timeout=120, env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.strip() == b'PACKAGED_PROGRAM_ACTIVATION_PASS'


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux flock required')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_execution_and_derivation_run_together_in_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        for name in ('recovery_program_execution', 'recovery_program_derivation'):
            assert archive.extractfile('common/'+name+'.py').read() == (ROOT/'ops/recovery'/(name+'.py')).read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from copy import deepcopy
from pathlib import Path
import sys
engine,tests,work=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(tests)]
import pytest
import recovery_program_execution as execution
import recovery_program_derivation as derivation
import recovery_program_generation as generation
import recovery_program_activation as activation
import recovery_program_targets as targets
import recovery_resource_admission as admission
modules=(execution,derivation,generation,activation,targets,admission)
assert all(Path(m.__file__).resolve().parent == (engine/'common').resolve() for m in modules)
from recovery_engine import pinned_json
from test_recovery_program_generation import case
from test_recovery_program_execution import execution as fixture,bind,resolve
from test_recovery_program_activation import locked,start,stage,finish
with pytest.MonkeyPatch.context() as seam:
 # Only resource observation is a unit seam. Files, reservations, journal,
 # exclusive locks, metadata production and all package modules are real.
 e=fixture.__wrapped__(case.__wrapped__(work),seam)
 owner=deepcopy(e.owner)
 original={Path(p['path']):Path(p['path']).read_bytes()
           for p in (e.owner_pin,e.request_pin,e.reservation)}
 with locked(e.case) as fd:
  context,binding=bind(e,fd)
  before,proof=resolve(e,binding,fd)
  assert before == owner and proof['generationPin'] is None
  epoch=start(e.case,e.claim,fd)
  proposed=derivation.derive(e.case['policy'],before['targets']['target57'],e.switch,
      e.request['operationId'],e.claim,fd)
  captures={source:entry['capturePin'] for source,entry in proposed['captureBindings'].items()}
  candidate=stage(e.case,context,fd,target_pin=proposed['targetPin'],
      capture_pins=captures,switch_result_pin=e.switch)
  effective,proof=resolve(e,binding,fd,generation_pin=candidate)
  assert effective['targets']['target57']['services'] == e.candidate['services']
  assert effective['targets']['target57']['secrets'] == owner['targets']['target57']['secrets']
  admitted=admission.admit(effective,e.request,e.root,'replacement',reservation_configuration=owner,
      execution_binding_pin=binding,execution_generation_pin=candidate,execution_lock_fd=fd)
  assert admitted['admitted'] is True and e.observations[-1] == effective
  (e.claim/'runtime').mkdir(mode=0o700)
  runtime,runtime_proof=resolve(e,binding,fd,generation_pin=candidate,runtime=True)
  assert runtime['targets']['target57']['dataRoot'] == str(e.claim/'runtime')
  assert runtime_proof['generationPin'] == proof['generationPin'] == candidate
  admitted=admission.admit(runtime,e.request,e.root,'target',reservation_configuration=owner,
      execution_binding_pin=binding,execution_generation_pin=candidate,execution_lock_fd=fd)
  assert admitted['admitted'] is True and e.observations[-1] == runtime
  try:generation.resolve_target(e.case['policy'])
  except Exception as error:assert error.code == 'PROGRAM_EPOCH_NOT_READY'
  else:raise AssertionError('unfinished generation globally activated')
  finish(e.case,e.claim,epoch,candidate,fd)
  active,active_binding=targets.resolve_configuration(owner,'target57')
  assert active == effective and active_binding['targetPin'] == proposed['targetPin']
  capture,evidence=generation.resolve_capture(e.case['policy'],'source57',e.case['base_pin'])
  assert capture == captures['source57'] and candidate in evidence
  assert pinned_json(capture)['source']['writerContainerIds'] == [
      s['id'] for s in e.candidate['services'] if s['role'] in ('backend','frontend')]
 assert e.owner == owner and all(path.read_bytes() == data for path,data in original.items())
assert all(Path(m.__file__).resolve().parent == (engine/'common').resolve() for m in modules)
print('PACKAGED_PROGRAM_EXECUTION_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests'), str(tmp_path)],
        capture_output=True, timeout=120, env={**os.environ, 'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.strip() == b'PACKAGED_PROGRAM_EXECUTION_PASS'


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux flock required')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
@pytest.mark.parametrize('component', ['image_import', 'native_context'])
def test_import_and_native_components_execute_from_delivered_package(component, variant, program_packages, tmp_path):
    names = {'image_import':'recovery_program_import', 'native_context':'recovery_program_native'}
    name = names[component]
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/'+name+'.py').read() == (ROOT/'ops/recovery'/(name+'.py')).read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import importlib,sys
engine,tests,work=map(Path,sys.argv[1:4]);component=sys.argv[4]
sys.path[:0]=[str(engine/'common'),str(tests)]
import pytest
module=importlib.import_module('recovery_program_import' if component=='image_import' else 'recovery_program_native')
assert Path(module.__file__).resolve().parent==(engine/'common').resolve()
from test_recovery_program_generation import case
if component=='image_import':
 from test_recovery_program_import import test_tagless_projection_preserves_content_identities_and_original_bytes
 from test_recovery_program_import import test_loading_requires_same_real_epoch_and_records_verified_image_observation
 first=work/'projection';first.mkdir(mode=0o700)
 test_tagless_projection_preserves_content_identities_and_original_bytes(first)
 second=work/'loading';second.mkdir(mode=0o700)
 # The load and inspect callbacks here are explicit unit protocol seams.
 # A separate classic-native run proves real Docker load and execution.
 test_loading_requires_same_real_epoch_and_records_verified_image_observation(case.__wrapped__(second))
else:
 from test_recovery_program_execution import execution
 from test_recovery_program_native import test_native_evidence_combines_phases_and_pending_unknown_without_losing_last_exit
 with pytest.MonkeyPatch.context() as patch:
  fixture=execution.__wrapped__(case.__wrapped__(work),patch)
  test_native_evidence_combines_phases_and_pending_unknown_without_losing_last_exit(fixture)
assert Path(module.__file__).resolve().parent==(engine/'common').resolve()
print('PACKAGED_IMPORT_NATIVE_PASS')
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests'),
        str(tmp_path), component], capture_output=True, timeout=120,
        env={**os.environ, 'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.strip() == b'PACKAGED_IMPORT_NATIVE_PASS'


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux archive watches required')
def test_safe_capture_archive_guard_uses_actual_standard_reader(program_packages, tmp_path):
    """The full reader's integrity contract belongs to the STANDARD package."""
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/'backup-restore-standard.tgz') as archive:
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests=map(Path,sys.argv[1:])
sys.path.insert(0,str(engine/'common'))
import repository_minimal
import repository_native_archive_reader
import recovery_archive_guard
modules=(repository_minimal,repository_native_archive_reader,recovery_archive_guard)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short',str(tests/'test_capture_archive_guard.py')])
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
raise SystemExit(code)
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests')],
        capture_output=True, timeout=120, env={**os.environ, 'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8', errors='replace')
    assert b'17 passed' in result.stdout and b' skipped' not in result.stdout
