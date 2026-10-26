"""Exercise generated SAFE code; do not confuse source tests with package tests."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_generated_safe_payload_preserves_diagnostics_and_rejection(tmp_path):
    spec = importlib.util.spec_from_file_location('diagnostic_builder', ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    original, _ = builder.standard_sources()
    payload = builder.safe_fixes(original)
    for name, raw in payload.items():
        destination = tmp_path/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    test = tmp_path/'test_archive_diagnostics.py'
    test.write_bytes((ROOT/'ops/recovery/test_recovery_archive_guard.py').read_bytes())
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(tmp_path/'common'), str(tmp_path/'formal'),
        str(tmp_path/'control'), env.get('PYTHONPATH', '')])
    program = ('import pathlib,sys; import recovery_archive_guard, recovery_minimal_worker; '
        'assert pathlib.Path(recovery_archive_guard.__file__).parent == pathlib.Path(sys.argv[1]); '
        'assert pathlib.Path(recovery_minimal_worker.__file__).parent == pathlib.Path(sys.argv[1]); '
        'import pytest; sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", sys.argv[2]]))')
    run = subprocess.run([sys.executable, '-B', '-c', program, str(tmp_path/'common'), str(test)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert '14 passed' in run.stdout


def test_fast_runtime_does_not_add_archive_watch():
    runtime = (ROOT/'ops/recovery/recovery_minimal_runtime.py').read_text(encoding='utf-8')
    assert 'ArchivePathGuard' not in runtime
    assert 'archive_guard' not in runtime
