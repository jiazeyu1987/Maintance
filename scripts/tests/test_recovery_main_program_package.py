"""Run source and MAIN protection contracts inside both actual delivered packages.

External SQL/container replies remain declared unit protocol boundaries in the
underlying tests. This proves packaging and module identity, not server restore.
"""
from pathlib import Path
import os
import subprocess
import sys
import tarfile

import pytest

from test_recovery_program_packaging import program_packages

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux custody and flock')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_source_and_main_custody_run_in_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        for name in ('recovery_program_source', 'recovery_program_protection'):
            assert archive.extractfile('common/'+name+'.py').read() == (
                ROOT/'ops/recovery'/(name+'.py')).read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(tests)]
import recovery_program_source
import recovery_program_protection
import recovery_program_native
import recovery_program_execution
import recovery_program_activation
import recovery_program_generation
import recovery_main_target
import recovery_minimal_runtime
modules=(recovery_program_source,recovery_program_protection,recovery_program_native,
    recovery_program_execution,recovery_program_activation,recovery_program_generation,
    recovery_main_target,recovery_minimal_runtime)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short',
    str(tests/'test_recovery_program_source.py'),str(tests/'test_recovery_main_program_protection.py')])
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
raise SystemExit(code)
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests')],
        capture_output=True, timeout=120, env={**os.environ, 'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8', errors='replace')
    assert b'88 passed' in result.stdout and b' skipped' not in result.stdout


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux child processes')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_native_commands_and_sql_ledger_run_from_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests,work=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(engine/'formal'),str(tests)]
import recovery_data
import recovery_program_native
import recovery_minimal_runtime
modules=(recovery_data,recovery_program_native,recovery_minimal_runtime)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
from test_recovery_program_native_invocations import InvocationCase
from test_recovery_program_native_invocations import test_preparation_and_restore_commands_share_actual_invocation_ledger
from test_recovery_program_native_invocations import test_sql_terminal_is_closed_before_post_stream_bound_dispatches_real_native_command
checks=(test_preparation_and_restore_commands_share_actual_invocation_ledger,
    test_sql_terminal_is_closed_before_post_stream_bound_dispatches_real_native_command)
for number,check in enumerate(checks):
    root=work/str(number);root.mkdir(mode=0o700)
    with pytest.MonkeyPatch.context() as seam:
        check(InvocationCase(root,seam,formal_directory=engine/'formal'))
    print('PACKAGED_NATIVE_INVOCATION_CASE_PASS',flush=True)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
print('PACKAGED_NATIVE_INVOCATION_PASS')
'''
    work=tmp_path/'cases';work.mkdir(mode=0o700)
    result=subprocess.run([sys.executable,'-B','-c',script,str(engine),str(ROOT/'scripts/tests'),str(work)],
        capture_output=True,timeout=120,env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode==0,(result.stdout+result.stderr).decode('utf-8',errors='replace')
    assert result.stdout.count(b'PACKAGED_NATIVE_INVOCATION_CASE_PASS')==2
    assert result.stdout.rstrip().endswith(b'PACKAGED_NATIVE_INVOCATION_PASS')


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged Linux resource admission')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_program_resource_admission_runs_inside_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_program_resources.py').read() == (
            ROOT/'ops/recovery/recovery_program_resources.py').read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests=map(Path,sys.argv[1:])
sys.path[:0]=[str(engine/'common'),str(tests)]
import recovery_program_resources
import recovery_resource_admission
import recovery_program_native
import recovery_program_execution
import recovery_program_source
modules=(recovery_program_resources,recovery_resource_admission,recovery_program_native,
    recovery_program_execution,recovery_program_source)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short',str(tests/'test_recovery_program_resources.py')])
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
raise SystemExit(code)
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(engine),str(ROOT/'scripts/tests')],
        capture_output=True,timeout=120,env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8',errors='replace')
    assert b'37 passed' in result.stdout and b' skipped' not in result.stdout


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged MAIN orchestration')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_main_restore_and_worker_run_inside_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_program_restore.py').read() == (
            ROOT/'ops/recovery/recovery_program_restore.py').read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import importlib,os,sys
engine,tests=map(Path,sys.argv[1:3])
variant=sys.argv[3]
assert variant in ('standard','lightweight')
os.environ['RECOVERY_TEST_ENGINE_VARIANT']=variant
sys.path[:0]=[str(engine/'common'),str(tests)]
names=('recovery_engine','recovery_minimal_plan','recovery_archive_guard','recovery_data_files',
    'recovery_backup_epoch','recovery_program_generation','recovery_program_activation',
    'recovery_program_execution','recovery_program_native','recovery_program_protection',
    'recovery_program_source','recovery_program_archive','recovery_program_import',
    'recovery_program_containers','recovery_program_derivation','recovery_program_resources',
    'recovery_resource_admission','recovery_main_target','recovery_replacement_storage',
    'recovery_replace','recovery_minimal_runtime','recovery_minimal_worker','recovery_program_restore')
modules=tuple(importlib.import_module(name) for name in names)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short',
    str(tests/'test_recovery_program_restore.py'),str(tests/'test_recovery_program_worker_result.py')])
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
raise SystemExit(code)
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(engine),str(ROOT/'scripts/tests'),variant],
        capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode==0,(result.stdout+result.stderr).decode('utf-8',errors='replace')
    assert b'21 passed' in result.stdout and b' skipped' not in result.stdout


@pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual packaged SQL lifecycle and original worker')
@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_producer_history_and_sql_lifecycle_run_from_actual_package(variant, program_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        assert archive.extractfile('common/recovery_program_sql_staging.py').read() == (
            ROOT/'ops/recovery/recovery_program_sql_staging.py').read_bytes()
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import importlib,os,sys
engine,tests=map(Path,sys.argv[1:3])
variant=sys.argv[3]
assert variant in ('standard','lightweight')
os.environ['RECOVERY_TEST_ENGINE_VARIANT']=variant
os.environ['RECOVERY_TEST_FORMAL_DIRECTORY']=str((engine/'formal').resolve())
sys.path[:0]=[str(engine/'common'),str(tests)]
names=('recovery_engine','recovery_minimal_plan','recovery_archive_guard','recovery_data_files',
    'recovery_backup_epoch','recovery_program_generation','recovery_program_activation',
    'recovery_program_execution','recovery_program_native','recovery_program_protection',
    'recovery_program_source','recovery_program_archive','recovery_program_import',
    'recovery_program_containers','recovery_program_derivation','recovery_program_resources',
    'recovery_resource_admission','recovery_main_target','recovery_replacement_storage',
    'recovery_replace','recovery_minimal_runtime','recovery_minimal_worker','recovery_program_restore',
    'recovery_data','recovery_program_evidence','recovery_program_sql_staging','staging_cleanup')
modules=tuple(importlib.import_module(name) for name in names)
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
import pytest
code=pytest.main(['-q','-p','no:cacheprovider','--tb=short',
    str(tests/'test_recovery_program_producer_contract.py'),
    str(tests/'test_recovery_program_producer_sql_lifecycle.py')])
assert all(Path(m.__file__).resolve().parent==(engine/'common').resolve() for m in modules)
raise SystemExit(code)
'''
    result = subprocess.run([sys.executable,'-B','-c',script,str(engine),str(ROOT/'scripts/tests'),variant],
        capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':os.pathsep.join(sys.path)})
    assert result.returncode == 0, (result.stdout+result.stderr).decode('utf-8',errors='replace')
    assert b'12 passed' in result.stdout and b' skipped' not in result.stdout
