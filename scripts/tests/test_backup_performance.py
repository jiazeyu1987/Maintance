"""Local engine behavior tests; no server/database/E2E success is implied."""
import ast
from contextlib import nullcontext
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/backup_engine/formal'), str(ROOT/'ops/recovery')]
import minimal_capture_worker as capture
import minimal_image_export as images
import formal_sql_restore as sql
from formal_capture_semantics import SemanticCapture
from minimal_capture_support import Budget, exclusive_json
from formal_snapshot_linux import FormalSnapshotError
from recovery_data import NativeData
from recovery_minimal_runtime import MinimalData
from recovery_engine import Budget as RecoveryBudget, RecoveryError
import repository_minimal as repository


@pytest.mark.parametrize('declared_size', [0, 5, 2000000])
def test_lightweight_archives_actual_eof_without_hash_or_size_checks(tmp_path, declared_size):
    import repository_native_publisher as publisher_module
    raw = b'file-data' * 140000
    source = tmp_path/'source'; source.mkdir()
    (source/'file').write_bytes(raw)
    target_root = tmp_path/'archives'; target_root.mkdir()
    config = SimpleNamespace(archives=target_root, identity_pin={'sha256': 'a'*64}, current=lambda: None)
    deadline = SimpleNamespace(check=lambda: None)
    tree = {'file': 'file|'+str(declared_size)+'|'+'0'*64}
    owner = repository.CapturedPublisher(config, source, tree, {'operationId': 'local-test'}, deadline)
    with patch.object(publisher_module.os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), create=True), \
         patch.object(publisher_module, 'pin_file', side_effect=AssertionError('no destination rehash')):
        pins = owner.stream(target_root/'new', tree, verify_content=False)
    assert (target_root/'new/file').read_bytes() == raw
    assert pins['file']['bytes'] == len(raw)
    # Missing files must still fail, even with file verification disabled.
    (source/'file').unlink()
    with pytest.raises(FileNotFoundError):
        owner.archive_request('read-chunk', 'file', 0)


def test_lightweight_incremental_detection_does_not_read_file_contents(tmp_path):
    from formal_capture_incremental import scan_files
    source = tmp_path/'file'; source.write_bytes(b'first')
    with patch.object(Path, 'open', side_effect=AssertionError('no content scan')):
        before = scan_files(tmp_path, guard=lambda: None)
    source.write_bytes(b'longer replacement')
    with patch.object(Path, 'open', side_effect=AssertionError('no content scan')):
        after = scan_files(tmp_path, guard=lambda: None)
    assert before['file'] != after['file']


@pytest.mark.parametrize('action', ['FULL', 'INCREMENTAL'])
def test_lightweight_capture_only_reads_database_attributes(tmp_path, action):
    (tmp_path/'payload').mkdir()
    mysql = SimpleNamespace(query=Mock(return_value='app\tCREATE DATABASE `app`\n'))
    runtime = SimpleNamespace(protected=Mock())
    series = SimpleNamespace(database=Mock())
    config = {'source': {'database': 'app', 'databaseUuid': 'source'}}
    budget = Budget(tmp_path, dict(workSeconds=30, maxWrittenBytes=100000, minimumFreeBytes=1))
    with budget.activate(), patch.object(capture, 'observe_data', side_effect=AssertionError('no full scan')), \
         patch.object(capture, 'observe_affected_data', side_effect=AssertionError('no affected scan')), \
         patch.object(capture, 'observe_position', side_effect=AssertionError('no comparison')):
        capture.capture_database(config, {'action': action}, tmp_path, runtime, series, mysql, object())
    series.database.assert_called_once()
    mysql.query.assert_called_once_with('SHOW CREATE DATABASE `app`;')
    record = json.loads((tmp_path/'payload/011-source-data.json').read_bytes())
    assert record['definition'] == ['app', 'CREATE DATABASE `app`']
    assert record['verificationState'] == 'NOT_PERFORMED'
    assert not (tmp_path/'scratch-after').exists()


def test_lightweight_dump_failure_is_not_hidden(tmp_path):
    series = SimpleNamespace(database=Mock(side_effect=RuntimeError('dump failed')))
    with pytest.raises(RuntimeError, match='dump failed'):
        capture.capture_database({'source': {'database': 'app'}}, {'action': 'FULL'}, tmp_path,
            SimpleNamespace(protected=Mock()), series, object(), object())
    assert not (tmp_path/'payload/011-source-data.json').exists()


@pytest.mark.parametrize('kind', ['new', 'parent', 'duplicate', 'changed-null', 'immutable-parent'])
def test_incremental_object_get_once_and_preserves_parent_and_metadata(tmp_path, kind):
    raw = b'actual version bytes'
    sha = hashlib.sha256(raw).hexdigest()
    row = dict(kind='version', key='attachment.txt', versionId='null', isLatest=True,
               lastModified='2026-10-21T00:00:00Z', size=len(raw), etag='"etag"')
    instance = SemanticCapture.__new__(SemanticCapture)
    instance.root = tmp_path/'semantic-capture'; (instance.root/'objects/sha256').mkdir(parents=True)
    instance.records = []; instance.entries = {}; instance.contents = {}; instance.parent = {}
    instance.parent_versions = {}
    instance.series = SimpleNamespace(spec={'pointType': 'INCREMENTAL'})
    metadata = {'content-type': 'text/plain'}
    response = lambda *a: (io.BytesIO(raw), {'content-length': str(len(raw)), 'etag': row['etag'], **metadata})
    instance.client = SimpleNamespace(content=Mock(side_effect=response))
    if kind == 'immutable-parent':
        row['versionId'] = 'immutable-version-123'
    if kind in ('parent', 'changed-null', 'immutable-parent'):
        instance.parent_versions = {('docs', row['key'], row['versionId']): dict(row, bucket='docs',
            sha256='0'*64 if kind == 'changed-null' else sha, headers=metadata)}
        parent_sha = '0'*64 if kind == 'changed-null' else sha
        instance.parent = {parent_sha: {'path': str(tmp_path/'parent.bin'), 'bytes': len(raw), 'sha256': parent_sha}}
    if kind == 'duplicate':
        instance.contents[sha] = {'path': str(tmp_path/'previous.bin'), 'bytes': len(raw), 'sha256': sha}
    budget = Budget(tmp_path, dict(workSeconds=30, maxWrittenBytes=100000, minimumFreeBytes=1))
    changed = set()
    got_sha, _, headers = instance.capture_version('docs', row, lambda: None, budget, changed)
    assert got_sha == ('0'*64 if kind == 'changed-null' else sha) and headers == metadata
    assert changed == ({sha} if kind == 'new' else set())
    if kind == 'new':
        assert Path(instance.contents[sha]['path']).read_bytes() == raw
    assert instance.client.content.call_count == (0 if kind in ('parent', 'changed-null', 'immutable-parent') else 1)
    assert not list((instance.root/'objects').glob('capture-*.bin'))


def test_binding_without_content_verification_never_rehashes_payload(tmp_path):
    import repository_binding as binding
    from repository_records import canonical
    archive = tmp_path/'archive'; (archive/'sidecar').mkdir(parents=True)
    manifest_pin = {'path': str(archive/'sidecar/manifest.json')}
    raw = canonical({'schemaVersion': 'capture-test'})
    reference = dict(path=str(archive/'capture-recovery-inputs.json'), bytes=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest())
    manifest = dict(payloadRefs=[reference], parentPointPins=[])
    originals = dict(schemaVersion='RepositoryReadbackOriginals/v1', manifestPin=manifest_pin,
                     archivedFilePins={'capture-recovery-inputs.json': reference},
                     readbackOriginalPins={'capture-recovery-inputs.json': {'path': 'readback'}})
    outputs = dict(recoveryMaterial={'manifestPin': manifest_pin},
                   objectContentIndex=dict(manifestPin=manifest_pin, repositoryBound=True,
                                           contentPins={'object': {'path': 'large-object'}}))
    with patch.object(binding, 'read_pin', side_effect=[canonical(manifest), canonical(originals), raw]), \
         patch.object(binding, 'pin_file', side_effect=AssertionError('redundant payload read')):
        assert binding.assemble_readback_bindings(manifest_pin, {'originalRecordsPin': {}},
            SimpleNamespace(check=lambda: None), lambda *a, **kw: outputs,
            verify_content=False) == outputs


@pytest.mark.parametrize('case', ['valid', 'digest', 'truncated', 'limit', 'concatenated', 'empty'])
def test_sql_expand_hashes_consumed_stream_without_separate_hash_pass(tmp_path, case):
    raw = b'CREATE TABLE app (id INT);\nINSERT INTO app VALUES (1);\n'*500
    compressed = gzip.compress(raw, mtime=0)
    if case == 'concatenated': compressed += gzip.compress(raw, mtime=0); raw *= 2
    if case == 'truncated': compressed = compressed[:-3]
    if case == 'empty': raw = b''; compressed = gzip.compress(raw, mtime=0)
    source = tmp_path/'sql.gz'; source.write_bytes(compressed); source.chmod(0o600)
    expected = '0'*64 if case == 'digest' else hashlib.sha256(compressed).hexdigest()
    limit = 10 if case == 'limit' else len(raw)+1
    with patch.object(sql, '_hash_object', side_effect=AssertionError('redundant gzip hash pass')):
        if case in ('valid', 'digest', 'concatenated', 'empty'):
            sha, size = sql.expand_checked(source, tmp_path/'expanded.sql', expected, limit, 10)
            assert sha == hashlib.sha256(raw).hexdigest() and size == len(raw)
            assert (tmp_path/'expanded.sql').read_bytes() == raw
        else:
            with pytest.raises((FormalSnapshotError, EOFError, gzip.BadGzipFile)):
                sql.expand_checked(source, tmp_path/'expanded.sql', expected, limit, 10)


def test_restore_hot_guard_does_not_rehash_inputs():
    native = MinimalData.__new__(MinimalData)
    native.budget = RecoveryBudget(10000)
    native.input_pins = [{'path': '/not-read-in-hot-loop', 'bytes': 1000000000, 'sha256': '0'*64}]
    native.archive_guard = SimpleNamespace(check=Mock())
    with patch('recovery_minimal_runtime.check_pin', side_effect=AssertionError('rehash')):
        for _ in range(10000): native.guard()
    native.archive_guard.check.assert_not_called()
    native.budget = SimpleNamespace(remaining=Mock(side_effect=RecoveryError('BUDGET_EXPIRED')))
    with pytest.raises(RecoveryError, match='BUDGET_EXPIRED'): native.guard()


def test_stage_timing_keeps_success_and_failure(tmp_path):
    native = NativeData.__new__(NativeData); native.root = tmp_path
    with native.timed_stage('sql-expand'): time.sleep(.002)
    assert json.loads((tmp_path/'timing-sql-expand-end.json').read_bytes())['completed'] is True
    with pytest.raises(ValueError):
        with native.timed_stage('sql-import'): raise ValueError('unit-error')
    result = json.loads((tmp_path/'timing-sql-import-end.json').read_bytes())
    assert result['completed'] is False and result['elapsedSeconds'] >= 0


def test_repository_timing_keeps_success_and_failure(tmp_path):
    with repository.timed_stage(tmp_path, 'nas-upload'): pass
    assert json.loads((tmp_path/'timing-nas-upload-end.json').read_bytes())['completed'] is True
    with pytest.raises(ValueError):
        with repository.timed_stage(tmp_path, 'nas-readback'): raise ValueError('readback failed')
    record = json.loads((tmp_path/'timing-nas-readback-end.json').read_bytes())
    assert record['completed'] is False and record['elapsedSeconds'] >= 0


def test_lightweight_does_not_probe_smb_before_capture(tmp_path):
    operation = tmp_path/'operation'; operation.mkdir()
    config = SimpleNamespace(source={'configurationPath': 'config', 'captureCommand': ['capture']})
    request = {'action': 'FULL', 'operationId': 'unit', 'sourceConfigRef': 'src'}
    with patch.object(repository, 'MinimumCatalog'), patch.object(repository, 'pin_file', return_value={}), \
         patch.object(repository, 'read_pin', return_value=b'{}'), \
         patch.object(repository, 'SmbReadback', side_effect=AssertionError('no SMB preflight')), \
         patch.object(repository, 'run_child', side_effect=RuntimeError('actual capture attempted')) as start:
        with pytest.raises(RuntimeError, match='actual capture attempted'):
            repository.publish(config, request, operation, object())
        start.assert_called_once()


@pytest.mark.skipif(os.name != 'posix', reason='Linux fcntl and native inode timestamps required')
def test_lightweight_image_cache_reuses_export_without_integrity_check(tmp_path):
    archive_root = tmp_path/'captures'; archive_root.mkdir()
    cache = archive_root/'.image-exports'; cache.mkdir()
    config_bytes = b'{"image":"unit"}'
    image_id = 'sha256:'+hashlib.sha256(config_bytes).hexdigest()
    key = hashlib.sha256(images.canonical([image_id])).hexdigest()
    entry = cache/key; entry.mkdir()
    archive = entry/'images.tar'
    with tarfile.open(archive, 'w:') as out:
        for name, raw in [('config.json', config_bytes), ('manifest.json', b'[{"Config":"config.json"}]')]:
            member = tarfile.TarInfo(name); member.size = len(raw); out.addfile(member, io.BytesIO(raw))
    archive.chmod(0o600)
    exclusive_json(entry/'metadata.json', dict(imageIds=[image_id], archivePin={
        'path': str(archive), 'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}))
    config = {'archiveRoot': str(archive_root), 'source': {'applicationImageIds': [image_id]}}
    budget = Budget(tmp_path, dict(workSeconds=30, maxWrittenBytes=1000000, minimumFreeBytes=1))
    with patch.object(images.subprocess, 'Popen', side_effect=AssertionError('must reuse export')):
        result = {}
        assert images.capture_images(config, tmp_path/'images.tar', budget, capture.validate_image_export, result=result) is True
        assert (tmp_path/'images.tar').read_bytes() == archive.read_bytes()
        assert result == dict(path=str(tmp_path/'images.tar'), bytes=archive.stat().st_size,
            sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        with archive.open('r+b') as out: out.write(b'DAMAGE')
        assert images.capture_images(config, tmp_path/'bad.tar', budget,
            lambda *a: pytest.fail('lightweight must not validate the archive')) is True
        assert (tmp_path/'bad.tar').read_bytes() == archive.read_bytes()


@pytest.mark.parametrize('failure', ['metadata', 'publish', 'none'])
def test_image_cache_publishes_complete_pair_or_nothing(tmp_path, failure):
    # Portable publication unit test; Linux locking/Docker are not exercised here.
    config = {'archiveRoot': str(tmp_path), 'source': {'applicationImageIds': ['unit-image']}}
    key = hashlib.sha256(images.canonical(['unit-image'])).hexdigest()
    entry = tmp_path/'.image-exports'/key
    rename = os.rename
    budget = SimpleNamespace(check=lambda: None, written=0, maximum=10000, deadline=30)
    def checked(path, **kwargs):
        if Path(path) == entry/'images.tar':
            raise RuntimeError('publication-complete')
        return Path(path)
    def write_metadata(path, value):
        if failure == 'metadata': raise RuntimeError('metadata-failed')
        Path(path).write_text(json.dumps(value), encoding='utf-8')
    def publish(source, target):
        assert (source/'images.tar').read_bytes() == b'exported-image'
        assert json.loads((source/'metadata.json').read_text())['archivePin']['path'] == str(entry/'images.tar')
        if failure == 'publish': raise RuntimeError('publish-failed')
        rename(source, target)
    lock_api = SimpleNamespace(flock=lambda *a: None, LOCK_EX=1, LOCK_NB=2)
    with patch.dict(sys.modules, {'fcntl': lock_api}), \
         patch.object(images.os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), create=True), \
         patch.object(images, 'path_checked', side_effect=checked), \
         patch.object(images, 'exclusive_json', side_effect=write_metadata), \
         patch.object(images.subprocess, 'Popen'), \
         patch.object(images, 'drain_owned_process', side_effect=lambda child, raw, sink, **kw: sink.write(b'exported-image')), \
         patch.object(images.os, 'rename', side_effect=publish), \
         pytest.raises(RuntimeError, match='publication-complete' if failure == 'none' else failure+'-failed'):
        images.capture_images(config, tmp_path/'backup.tar', budget, lambda *a: None)
    assert entry.exists() == (failure == 'none')
    assert not list((tmp_path/'.image-exports').glob('*.pending'))


def test_package_includes_new_image_helper():
    mapping = json.loads((ROOT/'ops/backup_engine/files.json').read_bytes())
    assert mapping['ops/backup_engine/formal/minimal_image_export.py'] == 'formal/minimal_image_export.py'
    for source in mapping:
        compile((ROOT/source).read_bytes(), source, 'exec')


@pytest.mark.skipif(os.name != 'posix', reason='Native Linux paths required')
def test_linear_path_validation_still_rejects_symlinks(tmp_path):
    from recovery_engine import absolute
    directory = tmp_path/'archive'; directory.mkdir()
    alias = tmp_path/'alias'; alias.symlink_to(directory, target_is_directory=True)
    with patch('pathlib.Path.resolve', side_effect=AssertionError('repeated ancestry resolution')):
        assert absolute(str(directory/'not-created-yet')) == directory/'not-created-yet'
        with pytest.raises(RecoveryError, match='PATH_ALIAS_REJECTED'):
            absolute(str(alias/'payload'))
        with pytest.raises(RecoveryError, match='PATH_ALIAS_REJECTED'):
            absolute(str(directory/'..'/'archive'/'payload'))


@pytest.mark.parametrize('failure', ['none', 'empty', 'child', 'guard'])
def test_dump_streams_directly_to_gzip_and_never_publishes_failure(tmp_path, failure):
    import subprocess
    import formal_snapshot_linux as snapshot
    import formal_capture_budget as capture_budget
    raw = b'INSERT INTO app VALUES (1);\n'*10000 if failure != 'empty' else b''
    client = snapshot.PrivateDockerMySql('local-child', 'private-input')
    client._command = lambda *a: [sys.executable, '-c',
        'import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write('+
        (repr(b'INSERT INTO app VALUES (1);\n')+'*10000' if raw else repr(b''))+'); sys.exit('+
        ('7' if failure == 'child' else '0')+')']
    def local_drain(process, input_bytes, writer, *, guard, deadline):
        # Portable subprocess adapter; Linux selector ownership is tested separately.
        out, err = process.communicate(input_bytes, timeout=10)
        assert not err
        for offset in range(0, len(out), 65536):
            guard(); writer.write(out[offset:offset+65536])
        if process.returncode: raise snapshot.FormalSnapshotError('FORMAL_CAPTURE_CHILD_FAILED')
    def remaining():
        if failure == 'guard' and list(tmp_path.glob('*.pending')):
            raise snapshot.FormalSnapshotError('TEST_DEADLINE')
        return 10
    destination = tmp_path/'database.sql.gz'
    with patch.object(capture_budget, 'drain_owned_process', side_effect=local_drain):
        if failure == 'none':
            reference = client._dump_current('app', destination, remaining)
            assert gzip.decompress(destination.read_bytes()) == raw
            assert reference == dict(bytes=destination.stat().st_size,
                sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
        else:
            with pytest.raises(snapshot.FormalSnapshotError):
                client._dump_current('app', destination, remaining)
            assert not destination.exists()
    assert not list(tmp_path.glob('*.raw'))


@pytest.mark.parametrize('corrupt', [False, True])
def test_physical_copy_has_one_final_destination_readback(tmp_path, corrupt):
    import formal_snapshot_linux as snapshot
    source = tmp_path/'source'; source.mkdir()
    (source/'object').write_bytes(b'physical object bytes')
    destination = tmp_path/'copy'
    original_hash = snapshot._hash_object; calls = []
    def hash_checked(path, **kwargs):
        calls.append(Path(path))
        if corrupt and Path(path) == destination/'object':
            Path(path).write_bytes(b'damaged object bytes')
        return original_hash(path, **kwargs)
    with patch.object(snapshot, '_hash_object', side_effect=hash_checked):
        if corrupt:
            with pytest.raises(snapshot.FormalSnapshotError, match='FORMAL_PHYSICAL_COPY_MISMATCH'):
                snapshot.copy_physical_minio_tree(source, destination)
        else:
            result = snapshot.copy_physical_minio_tree(source, destination)
            assert result['fileCount'] == 1 and (destination/'object').read_bytes() == (source/'object').read_bytes()
    assert calls == [source/'object', destination/'object']


@pytest.mark.parametrize('outcome', ['success', 'failed', 'unknown', 'hash'])
def test_sql_import_wakes_on_next_block_with_real_child(tmp_path, outcome):
    import subprocess
    raw = b'SELECT 1;\n'*(1024*1024)
    expanded = tmp_path/'expanded.sql'; expanded.write_bytes(raw)
    expected = hashlib.sha256(raw).hexdigest()
    code = 7 if outcome == 'failed' else 0
    child = ('import sys,hashlib; data=sys.stdin.buffer.read(); '
        'assert data.split(b"\\n",1)[0]==b"private-input"; '
        'assert hashlib.sha256(data.split(b"\\n",1)[1]).hexdigest()=="'+expected+'"; '
        'sys.stdout.buffer.write('+repr((('unconfirmed' if outcome == 'unknown' else 'RECOVERY_SQL_EXIT='+str(code))+'\n').encode())+'); '
        'sys.exit('+str(code)+')')
    mysql = SimpleNamespace(_password='private-input',
        _command=lambda *a: [sys.executable, '-c', child, 'sh', '-ec', 'ignored-shell-argument'])
    processes = []; real_popen = subprocess.Popen
    def launch(*a, **kw):
        instance = real_popen(*a, **kw); processes.append(instance)
        # The old loop waited on the long-lived process once for every MiB.
        instance.wait = Mock(wraps=instance.wait)
        return instance
    with patch.object(sql.subprocess, 'Popen', side_effect=launch):
        if outcome in ('success', 'hash'):
            sql.stream_import(mysql, expanded, '0'*64 if outcome == 'hash' else expected,
                15, database='app', guard=lambda: None)
        else:
            with pytest.raises(FormalSnapshotError) as error:
                sql.stream_import(mysql, expanded, '0'*64 if outcome == 'hash' else expected,
                    15, database='app', guard=lambda: None)
            if outcome == 'unknown': assert error.value.unknown is True
    assert processes[0].poll() is not None
    assert not any(call.kwargs.get('timeout', 1) <= .05 for call in processes[0].wait.call_args_list)


@pytest.mark.parametrize('corrupt', [False, True])
def test_publisher_returns_already_verified_pins(tmp_path, corrupt):
    from repository_native_publisher import Publisher
    import repository_native_publisher as publisher_module
    raw = b'archive content'*1000
    expected = hashlib.sha256(raw).hexdigest()
    owner = Publisher.__new__(Publisher)
    owner.source = {'archiveRoot': str(tmp_path)}
    owner.deadline = SimpleNamespace(check=lambda: None)
    owner.guard = lambda: None
    owner.archive_request = lambda action, relative, offset: (b'X'+raw[1:] if corrupt else raw)[offset:offset+1024*1024]
    target = tmp_path/'new-archive'
    # Windows lacks this Linux flag; this portable I/O test does not assert
    # native symlink protection, which remains required in Linux validation.
    with patch.object(publisher_module.os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), create=True), \
         patch.object(publisher_module, 'pin_file', side_effect=AssertionError('no duplicate NAS read')):
        if corrupt:
            from repository_records import RepositoryError
            with pytest.raises(RepositoryError, match='REPOSITORY_NATIVE_PAYLOAD_CORRUPT'):
                owner.stream(target, {'data': 'file|'+str(len(raw))+'|'+expected})
        else:
            pins = owner.stream(target, {'data': 'file|'+str(len(raw))+'|'+expected})
            assert pins == {'data': dict(path=str(target/'data').replace('\\','/'), bytes=len(raw), sha256=expected)}
            assert (target/'data').read_bytes() == raw


@pytest.mark.parametrize('corrupt', [False, True])
def test_lightweight_readback_reads_bytes_without_comparing_expected_digest(corrupt):
    from repository_native_readback import SmbReadback
    from repository_records import RepositoryError
    import stat
    original = b'archive-data'
    stored = b'X'+original[1:] if corrupt else original
    reader = SmbReadback.__new__(SmbReadback)
    reader.check = lambda: None
    reader.remote = lambda path: path
    reader.kwargs = {}
    info = SimpleNamespace(st_mode=stat.S_IFREG, st_size=len(stored), st_ino=1,
        st_mtime_ns=1, st_ctime_ns=1)
    reader.client = SimpleNamespace(stat=lambda *a, **kw: info,
        open_file=lambda *a, **kw: io.BytesIO(stored))
    expected = dict(path='/nas/backup/data', bytes=len(original), sha256=hashlib.sha256(original).hexdigest())
    actual = dict(expected, sha256=hashlib.sha256(stored).hexdigest())
    assert reader.read(expected['path'], expected=expected) == (actual, None)


def test_operator_archive_reads_only_metadata_not_payload_bytes():
    from repository_native_readback import SmbReadback
    reader = SmbReadback.__new__(SmbReadback)
    reader.connection_id = 'metadata-only'
    reader.check = lambda: None
    reader.tree = lambda archive: {'data': 3}
    reader.read = Mock(side_effect=AssertionError('payload readback must not run'))
    assert reader.verify('/nas/archive', {'data': 'file|3|'+'a'*64},
                         payload_content=False) == ('metadata-only', None)


def test_operator_physical_restore_copies_without_content_verification(tmp_path):
    import recovery_data_files as files
    source = tmp_path/'payload'; source.write_bytes(b'new')
    root = tmp_path/'target'; root.mkdir()
    expected = {'attachment': dict(kind='file', bytes=3, sha256='a'*64)}
    ref = dict(path=str(source), bytes=3, sha256='a'*64)
    with patch.object(files, 'pin', side_effect=AssertionError('no content reread')), \
         patch.object(files, 'check_pin', side_effect=AssertionError('no content verification')):
        result = files.apply_tree(root, {}, expected, {'attachment': ref}, full=True,
                                  guard=lambda: None, verify_content=False)
        assert files.inventory(root, lambda: None, content=False) == {
            'attachment': dict(kind='file', bytes=3)}
    assert (root/'attachment').read_bytes() == b'new'
    assert result['completeTreeReadback'] is False


def test_archive_list_reuses_capture_fingerprints_without_rereading_files(tmp_path):
    import formal_capture_incremental as incremental
    for name in ('payload', 'semantic-capture', 'recovery-materials', 'original-configs'):
        (tmp_path/name).mkdir()
    (tmp_path/'payload'/'attachment').write_bytes(b'abc')
    known = {'payload/attachment': 'file|3|'+'a'*64}
    with patch.object(incremental, '_file_pin', side_effect=AssertionError('no repeated hash scan')):
        result = capture.archive_entries(tmp_path, lambda: None, known)
    assert result['payload/attachment'] == known['payload/attachment']


@pytest.mark.parametrize('version', ['7.0.0', '6.2.0'])
def test_redis_preflight_checks_dependency_without_key_scan(version):
    import minimal_redis_snapshot as redis_snapshot
    client = SimpleNamespace(info=Mock(return_value={'redis_version': version}), eval=Mock(), close=Mock())
    module = SimpleNamespace(Redis=Mock(return_value=client))
    container = {'Id': 'source', 'State': {'Running': True},
        'NetworkSettings': {'Networks': {'private': {'IPAddress': '172.20.0.2'}}}}
    with patch.dict(sys.modules, redis=module), \
         patch.object(redis_snapshot.subprocess, 'check_output', return_value=json.dumps([container]).encode()):
        if version == '7.0.0':
            redis_snapshot.preflight(dict(containerId='source', host='172.20.0.2', database=0), lambda: None)
        else:
            with pytest.raises(FormalSnapshotError, match='REDIS_ABSOLUTE_EXPIRY_REQUIRED'):
                redis_snapshot.preflight(dict(containerId='source', host='172.20.0.2', database=0), lambda: None)
    client.eval.assert_not_called(); client.close.assert_called_once()
