"""Shared capture entry contracts; no build, server or business dispatch.

The candidate payload is the real authenticated SAFE source transformation.
Reading it does not create a package or claim a deployment. Normal-source
lifecycle tests below inspect the actual strict worker, never LIGHT semantics.
"""
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
sys.path.insert(0, str(ROOT/'ops/backup_engine/formal'))


def definitions(raw):
    return {node.name:node for node in ast.parse(raw).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def called(node, name):
    return [item for item in ast.walk(node) if isinstance(item, ast.Call) and
            isinstance(item.func, ast.Name) and item.func.id == name]


@pytest.fixture(scope='module')
def safe_payload():
    # Pure source selection only. Do not call build()/write_package(). The
    # production transformer authenticates the original frozen tar itself.
    path = ROOT/'ops/backup_engine/build_variants.py'
    spec = importlib.util.spec_from_file_location('target_capture_variant_contract', path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    frozen, _ = builder.standard_sources()
    return builder.safe_fixes(frozen)


def test_strict_source_really_delegates_materials_without_optional_source_restore():
    raw = (ROOT/'ops/recovery/minimal_capture_worker.py').read_text(encoding='utf-8')
    worker = definitions(raw)['capture_locked']
    assert called(worker, 'capture_protected_materials'), 'STRICT_WORKER_SHARED_MATERIALS_NOT_WIRED'
    # Source restoration remains mandatory after both material success/failure.
    restore_calls = [n for n in ast.walk(worker) if isinstance(n, ast.Call) and
                     isinstance(n.func, ast.Attribute) and n.func.attr == 'restore' and
                     isinstance(n.func.value, ast.Name) and n.func.value.id == 'runtime']
    assert len(restore_calls) == 1
    source = ast.get_source_segment(raw, worker)
    assert "result['sourceRestorationPin'] = restored" in source
    assert 'if primary is not None: raise primary' in source
    assert not any(word in source for word in ('skip_restore', 'skip_stop', 'restore=False'))


@pytest.mark.parametrize('member,source', [
    ('common/recovery_capture_materials.py', 'ops/recovery/recovery_capture_materials.py'),
    ('common/recovery_target_capture.py', 'ops/recovery/recovery_target_capture.py'),
])
def test_real_safe_candidate_contains_exact_new_capture_entry(safe_payload, member, source):
    assert member in safe_payload, 'SAFE_CAPTURE_ENTRY_MISSING '+member
    expected = (ROOT/source).read_bytes()
    assert hashlib.sha256(safe_payload[member]).digest() == hashlib.sha256(expected).digest()
    compile(safe_payload[member], member, 'exec')


def test_real_safe_candidate_worker_delegates_same_core_and_keeps_source_restoration(safe_payload):
    raw = safe_payload['formal/minimal_capture_worker.py'].decode('utf-8')
    worker = definitions(raw)['capture_locked']
    assert called(worker, 'capture_protected_materials'), 'SAFE_WORKER_SHARED_MATERIALS_NOT_WIRED'
    source = ast.get_source_segment(raw, worker)
    assert "result['sourceRestorationPin'] = restored" in source
    assert 'runtime.restore()' in source and 'semantic.close()' in source
    assert 'semantic.verify_parent()' in source
    semantic = definitions(safe_payload['formal/formal_capture_semantics.py'])['SemanticCapture']
    body = ast.get_source_segment(safe_payload['formal/formal_capture_semantics.py'].decode('utf-8'), semantic)
    assert 'complete=True' in body and 'observe_replica_bucket_dependencies' in body
    assert '_require_empty_multipart_observation' in body
