"""Real Linux parent-input leases and native pipes; no recovery acceptance."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def engine(tmp_path_factory):
    spec = importlib.util.spec_from_file_location('parent_guard_variants', ROOT / 'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    original, _ = builder.standard_sources()
    payload = builder.safe_fixes(original)
    root = tmp_path_factory.mktemp('actual-standard-parent-inputs')
    for name, raw in payload.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    sys.path[:0] = [str(root / name) for name in ('formal', 'common', 'control')]
    import minimal_capture_support
    import formal_capture_recovery_inputs
    return SimpleNamespace(support=minimal_capture_support, inputs=formal_capture_recovery_inputs,
                           payload=payload)


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def document(path, value):
    path.write_bytes(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    return reference(path)


def descriptors():
    result = {}
    for path in Path('/proc/self/fd').iterdir():
        try:
            result[int(path.name)] = os.readlink(path)
        except FileNotFoundError:
            pass  # The iterator's own descriptor has already closed.
    return result


@pytest.fixture
def parent(tmp_path, engine):
    # A real STANDARD _parent validates this small repository handoff and hashes
    # all contents. Tests never claim these fixture files are production data.
    content = tmp_path / 'content.bin'
    content.write_bytes(b'original-content' * 131072)
    content_pin = reference(content)
    sha = content_pin['sha256']
    inventory = tmp_path / 'versions.jsonl'
    inventory.write_bytes(json.dumps(dict(kind='version', bucket='objects', key='a',
                                         versionId='v1', sha256=sha)).encode() + b'\n')
    inventory_pin = reference(inventory)
    receipt_pin = document(tmp_path / 'receipt.json', dict(inventorySha256=inventory_pin['sha256'],
                                                           inventoryBytes=inventory_pin['bytes']))
    manifest_pin = document(tmp_path / 'manifest.json', dict(schemaVersion='RepositoryManifest/v1',
        backupId='parent', generationId='generation', commonRecoveryPoint='point',
        payloadRefs=[inventory_pin, receipt_pin, content_pin]))
    index_pin = document(tmp_path / 'index.json', dict(schemaVersion='backup-capture-object-index/v1',
        backupId='parent', generationId='generation', sourceIdentity='source', recoveryPoint='point',
        pointType='FULL', parentExportIndexPin=None, inventoryPin=inventory_pin,
        exportReceiptPin=receipt_pin, contentPins={sha: content_pin}, changedContentSha256=[sha],
        repositoryBound=True, manifestPin=manifest_pin))
    semantic = engine.support.MinimalSemantic.__new__(engine.support.MinimalSemantic)
    semantic.originals = engine.support.Originals(lambda: None)
    provisioned = tmp_path / 'provisioned.bin'
    provisioned.write_bytes(b'provisioned-original' * 65536)
    semantic.originals.read(reference(provisioned))
    semantic.series = SimpleNamespace(spec=dict(generationId='generation'),
        parent=dict(backupId='parent', commonRecoveryPoint='point'),
        repository_parent=dict(manifestPin=manifest_pin), check=lambda: None)
    semantic.source = dict(sourceIdentity='source', parentExportIndexPin=index_pin)
    semantic.scope = {}; semantic.identity = {}; semantic.reference_recipe = {}
    semantic.derived_recipe = {}; semantic.derived = {}
    semantic.raw = engine.support.canonical(semantic.source)
    semantic.provisioned_raw = engine.support.canonical(dict(scope={}, identity={}, references={}, recipe={}, derived={}))
    semantic.parent_originals = []; semantic.parent_content_identities = []
    before = descriptors()
    full_checks = []
    original_check = semantic.originals.check
    def check(*, full=True):
        full_checks.append(full)
        original_check(full=full)
    semantic.originals.check = check
    semantic.parent = semantic._parent()
    yield SimpleNamespace(semantic=semantic, content=content, index=Path(index_pin['path']),
                          metadata=[Path(r['path']) for r, _, _ in semantic.parent_originals],
                          before=before, provisioned=provisioned, full_checks=full_checks)
    if hasattr(semantic, 'close'):
        semantic.close()


def test_per_buffer_checks_do_not_reopen_parent_bytes_or_scan_all_parent_paths(parent, engine, monkeypatch):
    reads = []; stats = []
    original_bytes = engine.inputs.original_bytes
    original_lstat = Path.lstat
    protected = {str(parent.content), *(str(p) for p in parent.metadata)}
    def read(ref, **kwargs):
        if ref['path'] in protected:
            reads.append(ref['path'])
        return original_bytes(ref, **kwargs)
    def lstat(path, *args, **kwargs):
        if str(path) in protected:
            stats.append(str(path))
        return original_lstat(path, *args, **kwargs)
    monkeypatch.setattr(engine.inputs, 'original_bytes', read)
    monkeypatch.setattr(Path, 'lstat', lstat)
    for _ in range(200):
        parent.semantic.check()
    assert reads == [], 'parent metadata must not be reread per pipe buffer'
    assert stats == [], 'parent content set must not be rescanned per pipe buffer'


def test_parent_files_and_all_ancestors_are_leased_until_explicit_close(parent):
    paths = [parent.content, *parent.metadata]
    expected = {str(node) for path in paths for node in (path, *path.parents)}
    added = {fd: path for fd, path in descriptors().items() if fd not in parent.before}
    assert expected <= set(added.values()), 'each parent path must retain its Linux lease'
    parent.semantic.close()
    assert descriptors() == parent.before
    parent.semantic.close()
    assert descriptors() == parent.before


def test_initial_content_verification_keeps_owner_identities_without_rehashing_all_originals(parent):
    assert parent.full_checks and not any(parent.full_checks)


def test_normal_formal_owner_keeps_its_original_full_parent_verifier(parent, engine):
    base = engine.support.SemanticCapture.__new__(engine.support.SemanticCapture)
    base.originals = parent.semantic.originals
    base.series = parent.semantic.series
    base.source = parent.semantic.source
    base.parent_originals = []; base.parent_content_identities = []
    assert base._parent() == parent.semantic.parent
    assert base.parent_guard is None
    assert len(base.parent_content_identities) == 1
    assert any(parent.full_checks)


@pytest.mark.parametrize('mutation', ['content-write', 'content-replace', 'metadata-write', 'ancestor-rename'])
def test_parent_mutation_is_rejected_by_continuous_checks(parent, mutation):
    if mutation == 'content-write':
        raw = parent.content.read_bytes()
        parent.content.write_bytes(b'x' * len(raw))
        parent.content.write_bytes(raw)
    elif mutation == 'content-replace':
        replacement = parent.content.with_name('replacement')
        replacement.write_bytes(parent.content.read_bytes())
        replacement.replace(parent.content)
    elif mutation == 'metadata-write':
        parent.index.write_bytes(parent.index.read_bytes() + b' ')
    else:
        parent.content.parent.rename(parent.content.parent.with_name('renamed-parent'))
    with pytest.raises(Exception, match='CHANGED|ALIAS'):
        parent.semantic.check()


def test_full_boundary_check_rejects_changes_without_a_delivered_watch_event(parent, monkeypatch):
    # Models a remote filesystem for which local inotify is not authoritative.
    # Full metadata bytes and complete identities are still checked at phases.
    guard = parent.semantic.parent_guard
    monkeypatch.setattr(guard.lease, 'check', lambda: None)
    parent.index.write_bytes(parent.index.read_bytes() + b' ')
    with pytest.raises(Exception, match='CHANGED'):
        parent.semantic.verify_parent()


def test_full_boundary_check_rejects_content_identity_changes_without_events(parent, monkeypatch):
    guard = parent.semantic.parent_guard
    monkeypatch.setattr(guard.lease, 'check', lambda: None)
    parent.content.write_bytes(b'x' * parent.content.stat().st_size)
    with pytest.raises(Exception, match='CHANGED'):
        parent.semantic.verify_parent()


def test_real_native_pipe_finishes_with_original_deadline_and_continuous_guard(parent):
    from formal_capture_budget import drain_owned_process
    child = subprocess.Popen([sys.executable, '-c', 'import os;os.write(1,b"x"*1518704)'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = io.BytesIO()
    result = drain_owned_process(child, b'', output, guard=parent.semantic.check,
                                 deadline=time.monotonic() + 2, stderr_limit=0)
    assert result['returncode'] == 0
    assert output.getvalue() == b'x' * 1518704


def test_initial_content_hash_failure_closes_every_acquired_lease(tmp_path, engine):
    from formal_capture_parent_guard import ParentInputGuard
    content = tmp_path / 'content'
    content.write_bytes(b'actual')
    pin = reference(content)
    pin['sha256'] = '0' * 64
    before = descriptors()
    with pytest.raises(Exception, match='FORMAL_CAPTURE_OBJECT_PARENT_CHANGED'):
        ParentInputGuard([], [pin], lambda: None, engine.support.SemanticCapture.verify_content)
    assert descriptors() == before


def test_callback_failure_during_initial_full_hash_closes_all_leases(tmp_path, engine):
    from formal_capture_parent_guard import ParentInputGuard
    content = tmp_path / 'content'
    content.write_bytes(b'actual')
    before = descriptors()
    def interrupted(ref, guard):
        guard()
        raise TimeoutError('ORIGINAL_CAPTURE_DEADLINE')
    with pytest.raises(TimeoutError, match='ORIGINAL_CAPTURE_DEADLINE'):
        ParentInputGuard([], [reference(content)], lambda: None, interrupted)
    assert descriptors() == before


def test_semantic_constructor_failure_after_parent_acquisition_closes_leases(parent, engine, monkeypatch):
    from formal_capture_parent_guard import ParentInputGuard
    support = engine.support
    scope_ref, recipe_ref, derived_ref, credential_ref = [reference(p) for p in parent.metadata]
    identity_ref = reference(parent.content)
    descriptor = dict(sourceIdentity='unit-source', minioContainerId='unit-minio',
        endpoint='http://127.0.0.1:9000', sourceScopePin=scope_ref, referenceRecipePin=recipe_ref,
        derivedRecipePin=derived_ref, credentialReference=credential_ref, versionPins=[])
    documents = {scope_ref['path']: dict(endpointHosts=['127.0.0.1'], sourceIdentityPin=identity_ref),
        identity_ref['path']: dict(sourceFingerprint='unit-fingerprint', databaseUuid='unit-uuid'),
        recipe_ref['path']: {}, derived_ref['path']: dict(classes={}),
        credential_ref['path']: dict(schemaVersion='backup-source-s3-credential/v1',
            endpoint=descriptor['endpoint'], accessKey='unit-access', secretKey='unit-secret')}
    originals = SimpleNamespace(document=lambda ref, *a: documents[ref['path']], current=lambda: None)
    monkeypatch.setattr(support, 'validate_source', lambda value, kind: value)
    monkeypatch.setattr(support, 'validate_reference_recipe', lambda *a: {})
    created = []
    class Interrupted(support.MinimalSemantic):
        def _derived(self):
            return {}
        def _parent(self):
            self.parent_guard = ParentInputGuard(parent.semantic.parent_originals,
                [reference(parent.content)], originals.current, self.verify_content)
            created.append(self)
            return {}
        def __setattr__(self, name, value):
            if name == 'entries':
                raise RuntimeError('INTENTIONAL_POST_PARENT_INITIALIZATION_FAILURE')
            super().__setattr__(name, value)
    before = descriptors()
    try:
        with pytest.raises(RuntimeError, match='INTENTIONAL_POST_PARENT_INITIALIZATION_FAILURE'):
            Interrupted(SimpleNamespace(spec=dict(pointType='INCREMENTAL')), originals, descriptor,
                dict(sourceIdentity='unit-source', minioContainerId='unit-minio',
                     sourceFingerprint='unit-fingerprint', databaseUuid='unit-uuid'))
        assert descriptors() == before, 'semantic constructor failure leaked parent leases'
    finally:
        for semantic in created:
            semantic.close()


def test_parent_guard_refuses_insufficient_fd_budget_and_leaks_nothing(tmp_path, engine):
    from formal_capture_parent_guard import ParentInputGuard
    content = tmp_path / 'content'
    content.write_bytes(b'actual')
    limits = resource.getrlimit(resource.RLIMIT_NOFILE)
    held = []
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, limits[1]))
        held = [os.open('/dev/null', os.O_RDONLY) for _ in range(70)]
        before = descriptors()
        with pytest.raises(Exception, match='ARCHIVE_LEASE_FD_BUDGET_EXCEEDED'):
            ParentInputGuard([], [reference(content)], lambda: None, engine.support.SemanticCapture.verify_content)
        assert descriptors() == before
    finally:
        for fd in held:
            os.close(fd)
        resource.setrlimit(resource.RLIMIT_NOFILE, limits)


def test_full_capture_does_not_require_parent_leases(engine):
    semantic = engine.support.MinimalSemantic.__new__(engine.support.MinimalSemantic)
    semantic.source = dict(parentExportIndexPin=None)
    semantic.parent_originals = []; semantic.parent_content_identities = []
    assert semantic._parent() == {}
    assert semantic.parent_guard is None
    semantic.close()


def test_worker_retains_full_original_bytes_check_and_closes_parent_lease(engine):
    import ast
    code = engine.payload['formal/minimal_capture_worker.py'].decode()
    tree = ast.parse(code)
    capture = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'capture_locked')
    outer = next(n for n in capture.body if isinstance(n, ast.Try))
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
               isinstance(n.func.value, ast.Name) and n.func.value.id == 'semantic' and
               n.func.attr == 'close' for n in ast.walk(ast.Module(body=outer.finalbody, type_ignores=[])))
    assert 'originals.check(full=True)' in ast.get_source_segment(code, capture)
    assert ast.get_source_segment(code, capture).count('semantic.verify_parent()') >= 1
