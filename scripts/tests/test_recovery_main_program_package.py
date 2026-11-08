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
