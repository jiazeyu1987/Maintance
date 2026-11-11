"""Real metadata files and FD boundaries; no simulated NAS/stat success.

Select ``-k portable`` on Windows. The remaining cases require actual Linux;
they assert their prerequisite rather than silently skip.
"""
import errno
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
import recovery_backup_epoch as epoch


@pytest.fixture(autouse=True)
def exact_source():
    assert Path(epoch.__file__).resolve() == ROOT / 'ops/recovery/recovery_backup_epoch.py'


@pytest.fixture
def linux():
    assert sys.platform.startswith('linux'), 'REAL_LINUX_REQUIRED_NOT_A_SKIP'


def original(tmp_path, raw=b'actual original bytes'):
    path = tmp_path / 'metadata.json'
    path.write_bytes(raw)
    path.chmod(0o600)
    return path


def expected_pin(path, raw):
    return dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def observe_open(monkeypatch, path, before=lambda: None):
    """Observe one actual syscall; a boundary action changes only real files."""
    actual_open = os.open
    seen = dict(fired=False, descriptors=[], flags=[])

    def opened(candidate, flags, *args, **kwargs):
        chosen = isinstance(candidate, (str, bytes, os.PathLike)) and Path(candidate) == path
        if chosen:
            assert not seen['fired'], 'ONE_OPEN_NO_RETRY'
            seen['fired'] = True
            before()
        descriptor = actual_open(candidate, flags, *args, **kwargs)
        if chosen:
            seen['descriptors'].append(descriptor)
            seen['flags'].append(flags)
        return descriptor

    monkeypatch.setattr(os, 'open', opened)
    return seen


def assert_closed(seen):
    for descriptor in seen['descriptors']:
        with pytest.raises(OSError) as error:
            os.fstat(descriptor)
        assert error.value.errno == errno.EBADF


def after_read(monkeypatch, action):
    """Retain the real stream and bytes, changing files after its actual read."""
    actual_fdopen = os.fdopen
    seen = []

    class Stream:
        def __init__(self, actual):
            self.actual = actual

        def __getattr__(self, name):
            return getattr(self.actual, name)

        def __enter__(self):
            self.actual.__enter__()
            return self

        def __exit__(self, *args):
            return self.actual.__exit__(*args)

        def read(self, *args):
            raw = self.actual.read(*args)
            assert not seen, 'ONE_BOUNDED_READ_NO_RETRY'
            seen.append(True)
            action()
            return raw

    def wrapped(*args, **kwargs):
        return Stream(actual_fdopen(*args, **kwargs))

    monkeypatch.setattr(os, 'fdopen', wrapped)
    return seen


@pytest.mark.parametrize('raw', [b'', '真实 UTF-8 metadata'.encode('utf-8'), b'\x00\xff' * 5000],
                         ids=['empty', 'utf8', 'binary'])
def test_portable_stable_original_returns_exact_bytes_and_pin(tmp_path, monkeypatch, raw):
    path = original(tmp_path, raw)
    seen = observe_open(monkeypatch, path)
    assert epoch._read_file(path, len(raw)) == (raw, expected_pin(path, raw))
    assert len(seen['descriptors']) == 1
    assert_closed(seen)


def test_portable_original_input_limit_is_not_expanded(tmp_path, monkeypatch):
    path = original(tmp_path, b'abcd')
    seen = observe_open(monkeypatch, path)
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_INPUT_LIMIT$'):
        epoch._read_file(path, 3)
    assert_closed(seen)


def test_portable_real_remaining_hardlink_is_rejected(tmp_path, monkeypatch):
    path = original(tmp_path)
    os.link(path, tmp_path / 'actual-second-link')
    assert path.stat().st_nlink == 2
    seen = observe_open(monkeypatch, path)
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_REGULAR_SINGLE_LINK_REQUIRED$'):
        epoch._read_file(path)
    assert_closed(seen)


def test_portable_hardlink_created_after_read_is_rejected(tmp_path, monkeypatch):
    path = original(tmp_path)
    seen = observe_open(monkeypatch, path)
    changed = after_read(monkeypatch, lambda: os.link(path, tmp_path / 'actual-second-link'))
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_(FILE_CHANGED|REGULAR_SINGLE_LINK_REQUIRED)$'):
        epoch._read_file(path)
    assert changed == [True] and path.stat().st_nlink == 2
    assert_closed(seen)


@pytest.mark.parametrize('boundary', ['fdopen', 'read'])
def test_portable_stream_failure_preserves_original_error_and_closes_fd(tmp_path, monkeypatch, boundary):
    path = original(tmp_path)
    seen = observe_open(monkeypatch, path)
    failure = RuntimeError('actual-' + boundary + '-failure')

    def failed(*args, **kwargs):
        raise failure

    if boundary == 'fdopen':
        monkeypatch.setattr(os, 'fdopen', failed)
    else:
        after_read(monkeypatch, failed)
    with pytest.raises(RuntimeError) as error:
        epoch._read_file(path)
    assert error.value is failure
    assert_closed(seen)


def test_portable_final_path_is_checked_with_live_original_fd(tmp_path, monkeypatch):
    raw = b'actual metadata'
    path = original(tmp_path, raw)
    seen = observe_open(monkeypatch, path)
    actual_stat = Path.stat
    final_checks = []

    def checked(candidate, *args, **kwargs):
        if candidate == path and seen['descriptors']:
            os.fstat(seen['descriptors'][0])
            final_checks.append(True)
        return actual_stat(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', checked)
    assert epoch._read_file(path) == (raw, expected_pin(path, raw))
    assert final_checks
    assert_closed(seen)


def test_portable_final_path_error_is_preserved_and_fd_closed(tmp_path, monkeypatch):
    path = original(tmp_path)
    seen = observe_open(monkeypatch, path)
    read_complete = after_read(monkeypatch, lambda: None)
    actual_stat = Path.stat
    failure = OSError(errno.EIO, 'actual-final-path-failure')

    def failed(candidate, *args, **kwargs):
        if candidate == path and read_complete:
            os.fstat(seen['descriptors'][0])
            raise failure
        return actual_stat(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, 'stat', failed)
    with pytest.raises(OSError) as error:
        epoch._read_file(path)
    assert error.value is failure
    assert_closed(seen)


def test_linux_actual_open_uses_all_safety_flags(tmp_path, monkeypatch, linux):
    raw = b'actual metadata'
    path = original(tmp_path, raw)
    seen = observe_open(monkeypatch, path)
    assert epoch._read_file(path) == (raw, expected_pin(path, raw))
    assert len(seen['flags']) == 1
    for flag in (os.O_NOFOLLOW, os.O_CLOEXEC, os.O_NONBLOCK):
        assert seen['flags'][0] & flag == flag
    assert_closed(seen)


@pytest.mark.parametrize('kind', ['leaf', 'ancestor'])
def test_linux_initial_symlink_is_rejected(tmp_path, monkeypatch, linux, kind):
    directory = tmp_path / 'real'
    directory.mkdir()
    path = original(directory)
    if kind == 'leaf':
        alias = directory / 'alias'
        alias.symlink_to(path)
    else:
        alias = tmp_path / 'alias'
        alias.symlink_to(directory, target_is_directory=True)
        alias = alias / path.name
    seen = observe_open(monkeypatch, alias)
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_PATH_ALIAS_REJECTED$'):
        epoch._read_file(alias)
    assert_closed(seen)


@pytest.mark.parametrize('action', ['replace-inode', 'add-link', 'remove-second-link'])
def test_linux_preopen_real_change_is_rejected(tmp_path, monkeypatch, linux, action):
    path = original(tmp_path)
    raw = path.read_bytes()
    alias = tmp_path / 'actual-second-link'
    if action == 'remove-second-link':
        os.link(path, alias)
        assert path.stat().st_nlink == 2
    before = path.stat()

    def change():
        if action == 'replace-inode':
            replacement = tmp_path / 'replacement'
            replacement.write_bytes(raw)
            replacement.chmod(0o600)
            os.replace(replacement, path)
        elif action == 'add-link':
            os.link(path, alias)
        else:
            alias.unlink()
            assert path.stat().st_nlink == 1
            assert path.stat().st_ctime_ns != before.st_ctime_ns

    seen = observe_open(monkeypatch, path, change)
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_(FILE_CHANGED|REGULAR_SINGLE_LINK_REQUIRED)$'):
        epoch._read_file(path)
    assert seen['fired'], 'ACTUAL_PREOPEN_BOUNDARY_REQUIRED'
    assert_closed(seen)


@pytest.mark.parametrize('action', ['rewrite-restore-mtime', 'append', 'truncate', 'utime',
    'mode', 'uid', 'gid', 'link-unlink'])
def test_linux_read_interval_actual_change_is_rejected(tmp_path, monkeypatch, linux, action):
    path = original(tmp_path)
    before = path.stat()

    def change():
        if action == 'rewrite-restore-mtime':
            with path.open('r+b') as stream:
                stream.write(b'X' * before.st_size)
                stream.flush()
                os.fsync(stream.fileno())
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        elif action == 'append':
            with path.open('ab') as stream:
                stream.write(b'actual append')
        elif action == 'truncate':
            with path.open('r+b') as stream:
                stream.truncate(3)
        elif action == 'utime':
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
        elif action == 'mode':
            path.chmod(0o400)
        elif action in ('uid', 'gid'):
            assert os.geteuid() == 0, 'REAL_ROOT_CHOWN_CAPABILITY_REQUIRED'
            os.chown(path, 12345 if action == 'uid' else -1, 12345 if action == 'gid' else -1)
        else:
            alias = tmp_path / 'actual-second-link'
            os.link(path, alias)
            alias.unlink()
            assert path.stat().st_nlink == 1
        assert path.stat().st_ctime_ns != before.st_ctime_ns

    seen = observe_open(monkeypatch, path)
    changed = after_read(monkeypatch, change)
    with pytest.raises(ValueError, match='^BACKUP_EPOCH_(FILE_CHANGED|FILE_PERMISSIONS_INVALID|REGULAR_SINGLE_LINK_REQUIRED)$'):
        epoch._read_file(path)
    assert changed == [True]
    assert_closed(seen)


FIFO_RACE = r'''
import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import recovery_backup_epoch as epoch
path=Path(sys.argv[2]);actual_open=os.open;seen=[]
def opened(candidate,flags,*args,**kwargs):
    if Path(candidate)==path:
        assert not seen
        seen.append(True);path.unlink();os.mkfifo(path,0o600)
    return actual_open(candidate,flags,*args,**kwargs)
os.open=opened
try:
    epoch._read_file(path)
except ValueError as error:
    assert str(error)=='BACKUP_EPOCH_REGULAR_SINGLE_LINK_REQUIRED',str(error)
else:
    raise AssertionError('FIFO_WAS_ACCEPTED')
assert seen==[True]
print('ACTUAL_FIFO_REJECTED')
'''


def test_linux_fifo_replacement_cannot_block_before_type_check(tmp_path, linux):
    path = original(tmp_path)
    try:
        result = subprocess.run([sys.executable, '-B', '-S', '-c', FIFO_RACE,
            str(ROOT / 'ops/recovery'), str(path)], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
    except subprocess.TimeoutExpired:
        pytest.fail('ACTUAL_FIFO_OPEN_BLOCKED_BEFORE_TYPE_CHECK')
    assert result.returncode == 0, result.stderr.decode('utf-8')
    assert result.stdout == b'ACTUAL_FIFO_REJECTED\n' and not result.stderr
