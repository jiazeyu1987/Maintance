"""Real-filesystem capture-reader integrity and continuous Linux watch checks."""
import base64
import hashlib
import json
import mmap
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
from repository_minimal import CapturedReader
from repository_native_archive_reader import LabArchiveError
from recovery_engine import RecoveryError


def make_reader(root, *, capture=False, many=0):
    root.mkdir()
    names = {'a/data.bin', 'a/second.bin'}
    directories = {'a', 'empty'}
    if capture:
        names = set(CapturedReader.CAPTURE_REQUIRED_FILES)
        directories = set(CapturedReader.CAPTURE_DIRECTORIES)
    names.update(f'a/data-{number}.bin' for number in range(many))
    entries = {}
    for name in sorted(directories):
        (root / name).mkdir(parents=True, exist_ok=True)
        entries[name] = 'directory'
    for name in sorted(names):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = name.encode() * 3
        path.write_bytes(data)
        entries[name] = f'file|{len(data)}|{hashlib.sha256(data).hexdigest()}'
        for parent in path.relative_to(root).parents:
            if str(parent) != '.':
                entries[parent.as_posix()] = 'directory'
    if capture:
        (root / 'live-control.json').write_text('before')
        (root / 'payload/native-fence').mkdir()
        (root / 'payload/native-fence/state').write_text('before')
    return CapturedReader(str(root), entries, 'a' * 64, 'b' * 64,
                          guard=lambda: None, capture_layout=capture)


def request(reader, action, name=None):
    value = dict(schemaVersion=reader.SCHEMA, attemptId=reader.attempt,
                 sourceContextSha256=reader.context, sequence=reader.sequence + 1,
                 action=action)
    if name is not None:
        value.update(relativePath=name, offset=0)
    return reader.handle(json.dumps(value).encode())


def close(reader):
    if reader.path_guard is not None:
        reader.path_guard.close()


def test_reads_and_close_keep_actual_bytes_and_tree(tmp_path):
    reader = make_reader(tmp_path / 'capture', many=150)
    try:
        for name, value in reader.entries.items():
            if value != 'directory':
                answer = request(reader, 'read-chunk', name)
                assert base64.b64decode(answer['bytesBase64']) == (reader.root / name).read_bytes()
                assert answer['treeDigest'] == reader.tree_digest
        assert request(reader, 'close')['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
        with pytest.raises(LabArchiveError):
            request(reader, 'guard')
    finally:
        close(reader)


@pytest.mark.skipif(os.name != 'posix', reason='Linux inotify behavior')
@pytest.mark.parametrize('change', [
    'same_bytes_write', 'replace_file', 'delete_file', 'chmod_file', 'chmod_directory',
    'add_empty_child', 'transient_child', 'rename_directory', 'replace_root',
    'change_ancestor_mode',
])
def test_unrelated_selected_path_changes_fail_before_next_chunk(tmp_path, change):
    reader = make_reader(tmp_path / 'capture')
    root = reader.root
    victim = root / 'a/second.bin'
    ancestor_mode = tmp_path.stat().st_mode & 0o777
    try:
        if change == 'same_bytes_write':
            victim.write_bytes(victim.read_bytes())
        elif change == 'replace_file':
            data = victim.read_bytes()
            victim.unlink()
            victim.write_bytes(data)
        elif change == 'delete_file':
            victim.unlink()
        elif change == 'chmod_file':
            victim.chmod(0o400)
        elif change == 'chmod_directory':
            (root / 'a').chmod(0o700)
        elif change == 'add_empty_child':
            (root / 'empty/unexpected').mkdir()
        elif change == 'transient_child':
            extra = root / 'empty/transient'
            extra.touch()
            extra.unlink()
        elif change == 'rename_directory':
            (root / 'a').rename(root / 'moved')
        elif change == 'replace_root':
            root.rename(tmp_path / 'old')
            root.mkdir()
        elif change == 'change_ancestor_mode':
            tmp_path.chmod(ancestor_mode ^ 0o100)
        with pytest.raises((RecoveryError, LabArchiveError)):
            request(reader, 'read-chunk', 'a/data.bin')
        assert reader.failed
        assert reader.path_guard.fd == -1
    finally:
        tmp_path.chmod(ancestor_mode)
        close(reader)


def test_excluded_live_control_content_remains_owner_guarded(tmp_path):
    reader = make_reader(tmp_path / 'capture', capture=True)
    try:
        (reader.root / 'live-control.json').write_text('updated')
        (reader.root / 'payload/native-fence/state').write_text('updated')
        assert request(reader, 'guard')['state'] == 'OWNER_GUARD_CURRENT'
        assert request(reader, 'close')['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
    finally:
        close(reader)


def test_excluded_control_membership_is_still_fixed(tmp_path):
    reader = make_reader(tmp_path / 'capture', capture=True)
    try:
        (reader.root / 'unexpected-control.json').touch()
        with pytest.raises((RecoveryError, LabArchiveError)):
            request(reader, 'guard')
    finally:
        close(reader)


@pytest.mark.skipif(os.name != 'posix', reason='Linux inotify behavior')
def test_watch_descriptor_failure_is_not_downgraded(tmp_path):
    reader = make_reader(tmp_path / 'capture')
    try:
        os.close(reader.path_guard.fd)
        # Do not leave an invalid fd for the finally block to close again.
        reader.path_guard.fd = -1
        with pytest.raises(RecoveryError, match='ARCHIVE_WATCH_CLOSED'):
            request(reader, 'guard')
        assert reader.failed
    finally:
        close(reader)


@pytest.mark.skipif(os.name != 'posix', reason='Linux inotify behavior')
def test_write_through_already_open_descriptor_is_detected(tmp_path):
    root = tmp_path / 'capture'
    reader = make_reader(root)
    try:
        with (root / 'a/second.bin').open('r+b') as stream:
            stream.write(b'X')
            stream.flush()
            with pytest.raises(RecoveryError, match='ARCHIVED_PAYLOAD_CHANGED'):
                request(reader, 'read-chunk', 'a/data.bin')
    finally:
        close(reader)


@pytest.mark.skipif(os.name != 'posix', reason='Linux inotify behavior')
def test_real_event_queue_overflow_fails_closed(tmp_path):
    # These siblings are outside the capture. Their events must ordinarily be
    # ignored, but overflow must never be ignored or reported as success.
    paths = [tmp_path / 'unselected-1', tmp_path / 'unselected-2']
    for path in paths:
        path.write_bytes(b'')
    reader = make_reader(tmp_path / 'capture')
    try:
        limit = int(Path('/proc/sys/fs/inotify/max_queued_events').read_text())
        for number in range(limit + 1):
            with paths[number % 2].open('wb') as stream:
                stream.write(b'X')
        with pytest.raises(RecoveryError, match='ARCHIVE_WATCH_OVERFLOW'):
            request(reader, 'guard')
        assert reader.failed
    finally:
        close(reader)


@pytest.mark.skipif(os.name != 'posix', reason='Windows mmap does not reliably update observable timestamps; content readback is disabled')
def test_final_snapshot_rejects_observable_mmap_metadata_change(tmp_path):
    reader = make_reader(tmp_path / 'capture')
    try:
        with (reader.root / 'a/second.bin').open('r+b') as stream:
            with mmap.mmap(stream.fileno(), 0) as mapping:
                mapping[0:1] = b'X'
                mapping.flush()
        # No content readback: the Linux metadata snapshot still detects this write.
        with pytest.raises((RecoveryError, LabArchiveError)):
            request(reader, 'close')
        assert reader.failed
    finally:
        close(reader)
