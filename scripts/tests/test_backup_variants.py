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
        'common/repository_minimal.py', 'control/recovery_control_capture_config.py',
        'control/recovery_control_smallapp_native.py', 'control/recovery_control_target_availability.py',
        'control/recovery_control_point_quarantine.py', 'formal/formal_binlog_scope.py',
        'common/recovery_replace.py', 'common/recovery_data.py', 'formal/formal_data_evidence.py',
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
