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
