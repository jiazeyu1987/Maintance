"""Linux filesystem lease lifecycle; no remote operation or simulated acceptance."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine')]
import build_variants
import repository_minimal
import recovery_minimal_runtime
from recovery_archive_guard import ArchivePathGuard
from recovery_engine import RecoveryError, signature


def fd_count():
    return len(list(Path('/proc/self/fd').iterdir()))


def lease_fd_count(paths):
    return 1 + len({item for path in paths for item in (path, *path.parents)})


def test_capture_keeps_all_path_descriptors_until_close(tmp_path):
    paths = []
    for index in range(1100):
        path = tmp_path/str(index)
        path.write_bytes(b'original')
        paths.append(path)
    before = fd_count()
    guard = None
    try:
        guard = ArchivePathGuard.capture(paths)
        assert fd_count() == before + lease_fd_count(paths)
        assert guard.signatures == {str(p): signature(p.lstat()) for p in paths}
        guard.check()
    finally:
        if guard is not None:
            guard.close()
    assert fd_count() == before


@pytest.mark.parametrize('mutation', ['same_bytes', 'replace', 'hardlink', 'ancestor', 'member'])
def test_captured_lease_keeps_full_mutation_rejection(tmp_path, mutation):
    directory = tmp_path/'archive'
    directory.mkdir()
    path = directory/'payload'
    path.write_bytes(b'original')
    guard = ArchivePathGuard.capture([path], closed_directories=[directory])
    try:
        if mutation == 'same_bytes':
            path.write_bytes(path.read_bytes())
        elif mutation == 'replace':
            path.unlink()
            path.write_bytes(b'original')
        elif mutation == 'hardlink':
            os.link(path, tmp_path/'alias')
        elif mutation == 'ancestor':
            directory.chmod(0o700)
        else:
            (directory/'unexpected').touch()
        with pytest.raises(RecoveryError, match='ARCHIVED_PAYLOAD_CHANGED'):
            guard.check()
    finally:
        guard.close()


def test_installation_exception_closes_all_descriptors(tmp_path, monkeypatch):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    original = ArchivePathGuard._watch
    def fail(self, path, *args, **kwargs):
        original(self, path, *args, **kwargs)
        raise RuntimeError('installation interrupted')
    monkeypatch.setattr(ArchivePathGuard, '_watch', fail)
    with pytest.raises(RuntimeError, match='installation interrupted'):
        ArchivePathGuard.capture([path])
    assert fd_count() == before


def test_installation_drains_without_discarding_changes(tmp_path, monkeypatch):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    original = ArchivePathGuard._watch
    def change(self, selected, *args, **kwargs):
        result = original(self, selected, *args, **kwargs)
        if Path(selected) == path:
            path.write_bytes(b'original')
        return result
    monkeypatch.setattr(ArchivePathGuard, '_watch', change)
    with pytest.raises(RecoveryError, match='ARCHIVED_PAYLOAD_CHANGED'):
        ArchivePathGuard.capture([path])
    assert fd_count() == before


@pytest.fixture
def reader_class():
    payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
    tree = ast.parse(payload['common/repository_minimal.py'])
    selected = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CapturedReader')
    namespace = dict(vars(repository_minimal))
    exec(compile(ast.Module(body=[selected], type_ignores=[]), '<safe-reader>', 'exec'), namespace)
    return namespace['CapturedReader']


def entries_for(path):
    return {path.name: 'file|8|' + hashlib.sha256(b'original').hexdigest()}


def test_safe_reader_installs_before_first_content_read_and_reuses_watch(tmp_path, monkeypatch, reader_class):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    opened = []
    original = Path.open
    def observe(selected, *args, **kwargs):
        if selected == path:
            count = fd_count()
            opened.append(count)
            assert count == before + lease_fd_count([path]), 'identity must be leased BEFORE full content verification'
        return original(selected, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', observe)
    reader = reader_class(str(tmp_path), entries_for(path), 'a'*64, 'b'*64, guard=lambda: None)
    try:
        assert opened
        assert fd_count() == before + lease_fd_count([path])
        reader._current()
        response = reader.handle(json.dumps(dict(schemaVersion=reader.SCHEMA,
            attemptId=reader.attempt, sourceContextSha256=reader.context, sequence=1, action='close')).encode())
        assert response['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
        assert fd_count() == before
    finally:
        if reader.path_guard is not None:
            reader.path_guard.close()


def test_safe_reader_constructor_failure_deterministically_closes(tmp_path, reader_class):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    def interrupted():
        assert fd_count() == before + lease_fd_count([path]), 'lease must precede native constructor baseline'
        raise RuntimeError('owner check failed')
    with pytest.raises(RuntimeError, match='owner check failed'):
        reader_class(str(tmp_path), entries_for(path), 'a'*64, 'b'*64, guard=interrupted)
    assert fd_count() == before


def test_safe_reader_explicit_abandon_closes_without_success_receipt(tmp_path, reader_class):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    reader = reader_class(str(tmp_path), entries_for(path), 'a'*64, 'b'*64, guard=lambda: None)
    reader.close()
    reader.close()
    assert reader.failed and not reader.closed
    assert fd_count() == before


@pytest.mark.parametrize('stage', ['first_hash', 'target_identity'])
def test_minimal_data_leases_before_hash_and_closes_constructor_failure(tmp_path, stage):
    payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
    tree = ast.parse(payload['common/recovery_minimal_runtime.py'])
    selected = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MinimalData')
    namespace = dict(vars(recovery_minimal_runtime))
    safe_engine = {'__name__': 'safe_engine_unit'}
    exec(compile(payload['common/recovery_engine.py'], '<safe-engine>', 'exec'), safe_engine)
    namespace['modules_from'] = lambda _: {}
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    reference = safe_engine['pin'](path)
    before = fd_count()
    observed = []
    def check_pin(*args, **kwargs):
        assert fd_count() == before + lease_fd_count([path]), 'full hash started before identity lease'
        observed.append('hash')
        result = safe_engine['check_pin'](*args, **kwargs)
        if stage == 'first_hash':
            raise RuntimeError('hash interrupted')
        return result
    namespace['check_pin'] = check_pin
    exec(compile(ast.Module(body=[selected], type_ignores=[]), '<safe-minimal-data>', 'exec'), namespace)
    cls = namespace['MinimalData']
    def database_uuid(self):
        assert fd_count() == before + lease_fd_count([path])
        assert self.archive_guard.fd >= 0
        observed.append('identity')
        raise RuntimeError('identity interrupted')
    cls.database_uuid = database_uuid
    configuration = dict(environmentMysqlClientPath='/unused', maxExpandedBytes=1024,
        dataLimits={}, deadlineMilliseconds=60000, formalModuleDirectory='/unused')
    policy = dict(businessInvariants=[])
    target = dict(dataPolicy={}, services=[dict(role='mysql', id='unit-target')],
        dockerPin=reference, iptablesPin=reference)
    material = dict(recoveryPoint={}, objects=dict(method='PHYSICAL_FILES'),
        payloadPins=[reference], versionPins=[], sourceDatabaseUuid='unused')
    with pytest.raises(RuntimeError, match='interrupted'):
        cls(configuration, dict(operationId='unit-lease'), {}, policy,
            [(reference, {}, material, reference)], target, tmp_path, [])
    assert observed == (['hash'] if stage == 'first_hash' else ['hash', 'identity'])
    assert fd_count() == before


def test_watch_is_bound_to_held_inode_when_path_replaced_during_install(tmp_path, monkeypatch):
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    original = ArchivePathGuard._install
    def replace(self, selected, *args, **kwargs):
        if Path(selected) == path:
            path.rename(tmp_path/'old')
            path.write_bytes(b'original')
        return original(self, selected, *args, **kwargs)
    monkeypatch.setattr(ArchivePathGuard, '_install', replace)
    with pytest.raises(RecoveryError, match='PATH_ALIAS_REJECTED'):
        ArchivePathGuard.capture([path])
    assert fd_count() == before


@pytest.mark.parametrize('kind', ['file', 'directory', 'ancestor'])
def test_reader_rejects_eventless_baseline_identity_drift(tmp_path, reader_class, kind):
    # Fault injection models a filesystem lookup identity change without an
    # inotify event. It is a rejection test, not a reproduced CIFS incident.
    path = tmp_path/'payload'
    path.write_bytes(b'original')
    before = fd_count()
    class DriftedReader(reader_class):
        @staticmethod
        def _stamp(info):
            original = reader_class._stamp(info)
            if ((kind == 'file' and stat.S_ISREG(info.st_mode)) or
                    (kind == 'directory' and stat.S_ISDIR(info.st_mode))):
                return (original[0], original[1] + 1000, *original[2:])
            return original

        def _current(self, **kwargs):
            if kind == 'ancestor' and not self.baseline_ready:
                ancestor = next(iter(self.ancestors))
                original = self.ancestors[ancestor]
                self.ancestors[ancestor] = (original[0], original[1] + 1000, *original[2:])
            return super()._current(**kwargs)
    with pytest.raises(Exception, match='ARCHIVED_PAYLOAD_CHANGED'):
        DriftedReader(str(tmp_path), entries_for(path), 'a'*64, 'b'*64, guard=lambda: None)
    assert fd_count() == before


@pytest.mark.parametrize('outcome', ['stream_error', 'bad_ack', 'success'])
def test_publish_cleanup_preserves_required_close_ack(outcome):
    # Execute the generated archive stream/close block with failing transports;
    # cleanup must neither replace a protocol ACK nor suppress an exception.
    from types import SimpleNamespace
    payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
    tree = ast.parse(payload['common/repository_minimal.py'])
    publish = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'publish')
    block = next(node for node in ast.walk(publish) if isinstance(node, ast.Try)
                 and any(isinstance(child, ast.Attribute) and child.attr == 'stream'
                         for child in ast.walk(node)))
    calls = []
    def stream(*_):
        calls.append('stream')
        if outcome == 'stream_error':
            raise RuntimeError('stream failed')
        return {}
    def ack(*_):
        calls.append('ack')
        return dict(state='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF' if outcome == 'success' else 'INVALID')
    publisher = SimpleNamespace(binding=dict(attemptId='unit'), stream=stream, archive_request=ack,
        reader=SimpleNamespace(close=lambda: calls.append('cleanup')))
    namespace = dict(publisher=publisher, config=SimpleNamespace(archives=Path('/unused')), tree={},
        require=repository_minimal.require)
    code = compile(ast.Module(body=[block], type_ignores=[]), '<safe-publish-lifecycle>', 'exec')
    if outcome == 'success':
        exec(code, namespace)
    else:
        with pytest.raises(Exception, match='stream failed|REPOSITORY_ARCHIVE_CLOSE_FAILED'):
            exec(code, namespace)
    assert calls == (['stream', 'cleanup'] if outcome == 'stream_error' else ['stream', 'ack', 'cleanup'])
