"""Real file/FD pin contract; controlled syscall barriers, never fake stat success.

Linux cases use real local mutations, not a CIFS model. The separately retained
NAS probe is the environment RED. Portable cases preserve the Windows API.
"""
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
import minimal_capture_support as support


@pytest.fixture
def linux():
    assert sys.platform.startswith('linux'), 'REAL_LINUX_REQUIRED_NOT_A_SKIP'


@pytest.fixture(autouse=True)
def exact_source():
    assert Path(support.__file__).resolve() == ROOT/'ops/recovery/minimal_capture_support.py'


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def fd_snapshot():
    values = {}
    for path in Path('/proc/self/fd').iterdir():
        try:
            values[int(path.name)] = os.readlink(path)
        except FileNotFoundError:
            pass  # scandir's own descriptor is already closed.
    return values


MUTATOR = r'''
import os,sys
from pathlib import Path
p=Path(sys.argv[1]);action=sys.argv[2];before=p.stat()
raw=p.read_bytes()
if action=='time':os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns+1000000000))
elif action=='same-size':
    with p.open('r+b') as f:f.write(bytes(x^1 for x in raw));f.flush();os.fsync(f.fileno())
elif action=='restore-content-and-mtime':
    with p.open('r+b') as f:
        f.write(bytes(x^1 for x in raw));f.flush();os.fsync(f.fileno())
        f.seek(0);f.write(raw);f.flush();os.fsync(f.fileno())
    os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
elif action=='append':
    with p.open('ab') as f:f.write(b'append');f.flush();os.fsync(f.fileno())
elif action=='truncate':
    with p.open('r+b') as f:f.truncate(3);f.flush();os.fsync(f.fileno())
elif action=='mode':os.chmod(p,0o400)
elif action=='hardlink':os.link(p,p.with_name(p.name+'.alias'))
elif action=='replace':
    other=p.with_name(p.name+'.replacement');other.write_bytes(raw);os.replace(other,p)
elif action=='unlink':p.unlink()
elif action=='symlink':
    other=p.with_name(p.name+'.original');p.rename(other);p.symlink_to(other)
else:raise AssertionError(action)
'''


def mutate(path, action):
    result = subprocess.run([sys.executable, '-B', '-S', '-c', MUTATOR, str(path), action],
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=5)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert not result.stdout and not result.stderr


def before_open(monkeypatch, path, action=lambda: None):
    """Pause immediately before the real syscall; do not forge return values."""
    original_io, original_os = io.open, os.open
    seen = dict(fired=False, descriptors=[], nativeFlags=[])

    def fire(candidate, reading):
        if isinstance(candidate, (str, bytes, os.PathLike)) and Path(candidate) == path and reading:
            if not seen['fired']:
                seen['fired'] = True
                action()
            return True
        return False

    def opened_io(candidate, mode='r', *args, **kwargs):
        chosen = fire(candidate, mode in ('r', 'rb'))
        stream = original_io(candidate, mode, *args, **kwargs)
        if chosen:
            seen['descriptors'].append(stream.fileno())
        return stream

    def opened_os(candidate, flags, *args, **kwargs):
        reading = flags & os.O_ACCMODE == os.O_RDONLY and not flags & os.O_PATH
        chosen = fire(candidate, reading)
        descriptor = original_os(candidate, flags, *args, **kwargs)
        if chosen:
            seen['descriptors'].append(descriptor)
            seen['nativeFlags'].append(flags)
        return descriptor

    monkeypatch.setattr(io, 'open', opened_io)
    monkeypatch.setattr(os, 'open', opened_os)
    return seen


@pytest.mark.parametrize('raw', [b'', b'actual bytes\x00\xff', b'actual-block-'*200000],
                         ids=['empty', 'binary', 'streamed-2mb'])
def test_portable_stable_file_returns_actual_full_pin(tmp_path, raw):
    path = tmp_path/'original'; path.write_bytes(raw)
    assert support.actual_pin(path) == reference(path)


def test_portable_exclusive_json_preserves_known_canonical_bytes(tmp_path):
    path = tmp_path/'document.json'; value = {'value': 'original'}
    result = support.exclusive_json(path, value)
    assert path.read_bytes() == support.canonical(value)
    assert result == reference(path)
    assert not list(tmp_path.glob('*.pending'))


def test_preopen_timestamp_update_uses_one_actual_fd_baseline(tmp_path, monkeypatch, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual unchanged bytes')
    expected = reference(path)
    seen = before_open(monkeypatch, path, lambda: mutate(path, 'time'))
    before = fd_snapshot()
    assert support.actual_pin(path) == expected
    assert seen['fired'] and len(seen['descriptors']) == 1, 'NO_RETRY_OR_RESAMPLE'
    assert fd_snapshot() == before


def test_linux_read_open_uses_all_three_safety_flags(tmp_path, monkeypatch, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual unchanged bytes')
    seen = before_open(monkeypatch, path)
    assert support.actual_pin(path) == reference(path)
    assert len(seen['nativeFlags']) == 1, 'ACTUAL_NATIVE_READ_OPEN_REQUIRED'
    flags = seen['nativeFlags'][0]
    for required in (os.O_NOFOLLOW, os.O_CLOEXEC, os.O_NONBLOCK):
        assert flags & required == required


@pytest.mark.parametrize('action', ['replace', 'symlink'])
def test_preopen_path_replacement_is_rejected(tmp_path, monkeypatch, linux, action):
    path = tmp_path/'original'; path.write_bytes(b'actual original bytes')
    seen = before_open(monkeypatch, path, lambda: mutate(path, action))
    before = fd_snapshot()
    with pytest.raises((RuntimeError, OSError)):
        support.actual_pin(path)
    assert seen['fired'] and fd_snapshot() == before


@pytest.mark.parametrize('action', ['same-size', 'restore-content-and-mtime', 'append',
    'truncate', 'time', 'mode', 'hardlink', 'replace', 'unlink'])
def test_read_interval_mutation_is_rejected_and_fd_closed(tmp_path, linux, action):
    path = tmp_path/'original'; path.write_bytes(b'actual immutable payload-'*90000)
    calls = []
    def guard():
        if not calls:
            calls.append(action)
            mutate(path, action)
    before = fd_snapshot()
    with pytest.raises((RuntimeError, OSError)):
        support.actual_pin(path, guard)
    assert calls == [action] and fd_snapshot() == before


@pytest.mark.parametrize('kind', ['leaf-symlink', 'ancestor-symlink', 'hardlink'])
def test_initial_aliases_are_rejected(tmp_path, linux, kind):
    directory = tmp_path/'directory'; directory.mkdir()
    path = directory/'original'; path.write_bytes(b'actual original')
    if kind == 'leaf-symlink':
        alias = directory/'alias'; alias.symlink_to(path); path = alias
    elif kind == 'ancestor-symlink':
        alias = tmp_path/'alias'; alias.symlink_to(directory, target_is_directory=True); path = alias/path.name
    else:
        os.link(path, directory/'hardlink')
    before = fd_snapshot()
    with pytest.raises((RuntimeError, OSError)):
        support.actual_pin(path)
    assert fd_snapshot() == before


def test_final_path_is_checked_while_original_fd_is_alive(tmp_path, monkeypatch, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual immutable bytes')
    seen = before_open(monkeypatch, path)
    original = Path.lstat; observations = []
    def lstat(current, *args, **kwargs):
        value = original(current, *args, **kwargs)
        if current == path and seen['descriptors']:
            alive = []
            for descriptor in seen['descriptors']:
                try:alive.append(os.fstat(descriptor).st_ino == value.st_ino)
                except OSError as error:
                    assert error.errno == errno.EBADF
            observations.append(any(alive))
        return value
    monkeypatch.setattr(Path, 'lstat', lstat)
    before = fd_snapshot()
    assert support.actual_pin(path)['bytes'] == len(b'actual immutable bytes')
    assert observations and all(observations), 'FINAL_PATH_MUST_BE_BOUND_TO_LIVE_FD'
    assert fd_snapshot() == before


def test_guard_error_is_preserved_and_fd_closed(tmp_path, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual immutable bytes')
    error = LookupError('exact-original-guard-error')
    def guard():raise error
    before = fd_snapshot()
    with pytest.raises(LookupError) as captured:
        support.actual_pin(path, guard)
    assert captured.value is error and fd_snapshot() == before


def test_final_lstat_error_is_preserved_and_fd_closed(tmp_path, monkeypatch, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual immutable bytes')
    original = Path.lstat; reading = []; error = OSError(errno.EIO, 'original-stat-error')
    def lstat(current, *args, **kwargs):
        if current == path and reading:raise error
        return original(current, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', lstat)
    before = fd_snapshot()
    with pytest.raises(OSError) as captured:
        support.actual_pin(path, lambda: reading.append(True))
    assert captured.value is error and fd_snapshot() == before


@pytest.mark.parametrize('point', ['read', 'fdopen'])
def test_stream_error_is_preserved_and_fd_closed(tmp_path, monkeypatch, linux, point):
    path = tmp_path/'original'; path.write_bytes(b'actual immutable bytes')
    error = OSError(errno.EIO, 'exact-original-stream-error')
    original_io, original_fdopen = io.open, os.fdopen
    class FailingRead:
        def __init__(self, stream):self.stream = stream
        def __enter__(self):return self
        def __exit__(self, *args):return self.stream.__exit__(*args)
        def fileno(self):return self.stream.fileno()
        def read(self, *args):raise error
    def opened_io(candidate, mode='r', *args, **kwargs):
        stream = original_io(candidate, mode, *args, **kwargs)
        if point == 'read' and isinstance(candidate, (str, os.PathLike)) and Path(candidate) == path and mode == 'rb':
            return FailingRead(stream)
        return stream
    def opened_fdopen(descriptor, mode='r', *args, **kwargs):
        if os.readlink('/proc/self/fd/'+str(descriptor)) == str(path) and mode == 'rb':
            if point == 'fdopen':raise error
            return FailingRead(original_fdopen(descriptor, mode, *args, **kwargs))
        return original_fdopen(descriptor, mode, *args, **kwargs)
    monkeypatch.setattr(io, 'open', opened_io)
    monkeypatch.setattr(os, 'fdopen', opened_fdopen)
    before = fd_snapshot()
    with pytest.raises(OSError) as captured:
        support.actual_pin(path)
    assert captured.value is error and fd_snapshot() == before


@pytest.mark.parametrize('writer', ['preservation', 'ordinary'])
def test_writer_rejects_changed_known_bytes_before_pin_baseline(tmp_path, monkeypatch, linux, writer):
    # Real mutation at the writer->pin boundary, then the unmodified actual reader.
    # No successful pin or stat is forged by this wrapper.
    import recovery_target_preservation as preservation
    module = preservation if writer == 'preservation' else support
    path = tmp_path/'document.json'; actual = module.actual_pin
    def changed(candidate, *args, **kwargs):
        mutate(Path(candidate), 'same-size')
        return actual(candidate, *args, **kwargs)
    monkeypatch.setattr(module, 'actual_pin', changed)
    before = fd_snapshot()
    if writer == 'preservation':
        with pytest.raises(preservation.RepositoryError, match='^PRESERVATION_INPUT_CHANGED$') as caught:
            preservation._new(path, {'value': 'original'})
        assert type(caught.value) is preservation.RepositoryError
        assert caught.value.code == 'PRESERVATION_INPUT_CHANGED'
    else:
        from formal_snapshot_linux import FormalSnapshotError
        with pytest.raises(FormalSnapshotError, match='^MINIMAL_INPUT_CHANGED$') as caught:
            support.exclusive_json(path, {'value': 'original'})
        assert type(caught.value) is FormalSnapshotError
        assert caught.value.code == 'MINIMAL_INPUT_CHANGED'
    assert path.exists() and fd_snapshot() == before


def _fifo_child(path):
    """Invoked by a bounded real child; an old blocking open must not hang pytest."""
    class Patch:
        @staticmethod
        def setattr(obj, name, value):setattr(obj, name, value)
    def replace():
        path.unlink(); os.mkfifo(path, 0o600)
    before_open(Patch(), path, replace)
    try:support.actual_pin(path)
    except (RuntimeError, OSError):return 0
    return 3


def test_preopen_fifo_replacement_fails_without_blocking(tmp_path, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual file')
    code = ('import sys;from pathlib import Path;'
            'from test_minimal_capture_pin_contract import _fifo_child;'
            'raise SystemExit(_fifo_child(Path(sys.argv[1])))')
    try:
        result = subprocess.run([sys.executable, '-B', '-c', code, str(path)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail('REAL_FIFO_OPEN_BLOCKED_WITHOUT_NONBLOCK')
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')


def test_existing_reference_still_rejects_new_stable_content(tmp_path, linux):
    path = tmp_path/'original'; path.write_bytes(b'actual original bytes')
    original = reference(path)
    mutate(path, 'same-size')
    assert support.actual_pin(path) != original
    with pytest.raises(RuntimeError, match='BACKUP_INTERFACE_SOURCE_CHANGED'):
        support.original_bytes(original)
