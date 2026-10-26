"""Real Linux descriptor/transport contracts; no database or recovery acceptance."""
import errno
import fcntl
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
from recovery_archive_guard import ArchivePathGuard
from recovery_engine import RecoveryError


def descriptors():
    result = {}
    for entry in Path('/proc/self/fd').iterdir():
        try:
            result[int(entry.name)] = os.readlink(entry)
        except FileNotFoundError:
            pass  # The directory iterator's own fd has already closed.
    return result


def files(root, count=1):
    root.mkdir()
    paths = [root/str(index) for index in range(count)]
    for path in paths:
        path.write_bytes(b'original')
    return paths


@pytest.mark.parametrize('count,held_count', [(100, 0), (1, 70)])
def test_insufficient_budget_accounts_for_existing_fds_and_64_work_slots(tmp_path, monkeypatch, count, held_count):
    paths = files(tmp_path/'archive', count)
    limits = resource.getrlimit(resource.RLIMIT_NOFILE)
    before = descriptors()
    held = []
    guard = None
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, limits[1]))
        held = [os.open('/dev/null', os.O_RDONLY | os.O_CLOEXEC) for _ in range(held_count)]
        expected = descriptors()
        def forbidden(*_):
            raise AssertionError('archive guard must not change process limits')
        monkeypatch.setattr(resource, 'setrlimit', forbidden)
        with pytest.raises(RecoveryError, match='ARCHIVE_LEASE_FD_BUDGET_EXCEEDED'):
            guard = ArchivePathGuard.capture(paths)
        assert descriptors() == expected
        assert resource.getrlimit(resource.RLIMIT_NOFILE) == (128, limits[1])
    finally:
        monkeypatch.undo()
        if guard is not None:
            guard.close()
        for fd in held:
            os.close(fd)
        resource.setrlimit(resource.RLIMIT_NOFILE, limits)
    assert descriptors() == before


def test_every_path_has_retained_opath_and_cloexec(tmp_path):
    paths = files(tmp_path/'archive', 20)
    before = descriptors()
    expected = {str(item) for path in paths for item in (path, *path.parents)}
    guard = ArchivePathGuard.capture(paths)
    try:
        added = {fd: value for fd, value in descriptors().items() if fd not in before}
        leased = {fd: value for fd, value in added.items() if value in expected}
        assert set(leased.values()) == expected
        assert len(leased) == len(expected)
        for fd in leased:
            assert fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_PATH
            assert fcntl.fcntl(fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        # close_fds=False proves CLOEXEC itself protects exec'd subprocesses.
        child = subprocess.run([sys.executable, '-c',
            "import os,json;print(json.dumps([os.readlink('/proc/self/fd/'+v) for v in os.listdir('/proc/self/fd') if os.path.exists('/proc/self/fd/'+v)]))"],
            close_fds=False, capture_output=True, check=True, text=True)
        assert not expected.intersection(json.loads(child.stdout))
        guard.check()
    finally:
        guard.close()
        guard.close()
    assert descriptors() == before


@pytest.mark.parametrize('errno_value', [errno.EMFILE, errno.ENFILE])
def test_partial_path_allocation_failure_closes_all_resources(tmp_path, monkeypatch, errno_value):
    paths = files(tmp_path/'archive', 20)
    before = descriptors()
    original = os.open
    observed = []
    def interrupted(path, flags, *args, **kwargs):
        if flags & os.O_PATH:
            observed.append(str(path))
            if len(observed) == 8:
                raise OSError(errno_value, 'injected descriptor exhaustion')
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', interrupted)
    with pytest.raises((OSError, RecoveryError)):
        ArchivePathGuard.capture(paths)
    assert len(observed) == 8
    assert descriptors() == before


def test_close_releases_remaining_paths_when_one_close_reports_error(tmp_path, monkeypatch):
    paths = files(tmp_path/'archive', 20)
    before = descriptors()
    guard = ArchivePathGuard.capture(paths)
    original = os.close
    seen = []
    def reported_error(fd):
        original(fd)
        seen.append(fd)
        if len(seen) == 1:
            raise OSError(errno.EIO, 'close reported an error')
    monkeypatch.setattr(os, 'close', reported_error)
    with pytest.raises(OSError, match='close reported an error'):
        guard.close()
    assert len(seen) == len({item for path in paths for item in (path, *path.parents)}) + 1
    assert descriptors() == before
    guard.close()


@pytest.fixture
def high_fd_lease(tmp_path):
    paths = files(tmp_path/'archive', 1100)
    before = descriptors()
    held = []
    guard = None
    try:
        # Real test-owned O_PATH references impose descriptor pressure now.
        # Their transport tests are independent of the implementation RED
        # assertions above; they do not claim the guard already retains paths.
        for path in sorted({item for path in paths for item in (path, *path.parents)}):
            held.append(os.open(path, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC))
        guard = ArchivePathGuard.capture(paths)
        sentinel = os.open('/dev/null', os.O_RDONLY | os.O_CLOEXEC)
        try:
            assert sentinel > 1024, 'transport must execute while the full path lease is held'
        finally:
            os.close(sentinel)
        yield guard, tmp_path
        guard.check()
    finally:
        if guard is not None:
            guard.close()
        for fd in reversed(held):
            os.close(fd)
    assert descriptors() == before


def test_high_fd_communicate_and_timeout(high_fd_lease):
    guard, _ = high_fd_lease
    # Verify an exec child cannot retain any real fixture path lease even
    # when descriptor-closing behavior is disabled at Popen itself.
    owned_paths = {value for fd, value in descriptors().items()
                   if fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_PATH}
    child = subprocess.run([sys.executable, '-c',
        "import os,json;print(json.dumps([os.readlink('/proc/self/fd/'+v) for v in os.listdir('/proc/self/fd') if os.path.exists('/proc/self/fd/'+v)]))"],
        close_fds=False, capture_output=True, check=True, text=True)
    assert not owned_paths.intersection(json.loads(child.stdout))
    assert subprocess._PopenSelector.__name__ != 'SelectSelector'
    process = subprocess.Popen([sys.executable, '-c',
        "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read());sys.stderr.write('transport')"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw = b'x' * (1024*1024)
    try:
        assert process.communicate(raw, timeout=10) == (raw, b'transport')
        assert process.returncode == 0
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
    process = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            process.communicate(timeout=.1)
    finally:
        process.kill()
        process.communicate(timeout=5)
        process.stdout.close()
        process.stderr.close()


def test_high_fd_real_sql_transport_thread_protocol(high_fd_lease):
    # Exercise the real stream_import transport against an owned shell sink.
    # This is not a MySQL import or business recovery result.
    import formal_sql_restore
    guard, root = high_fd_lease
    source = root/'transport.sql'
    raw = b'SELECT 1;\n' * 150000
    source.write_bytes(raw)
    class TransportSink:
        _password = 'local-transport-only'
        def _command(self, *_):
            return ['sh', '-ec', 'cat >/dev/null']
    formal_sql_restore.stream_import(TransportSink(), source, hashlib.sha256(raw).hexdigest(),
        10, database='transport', guard=guard.check)


@pytest.mark.parametrize('outcome', ['response', 'timeout'])
def test_high_fd_real_loopback_http(high_fd_lease, outcome):
    guard, _ = high_fd_lease
    release = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if outcome == 'timeout':
                release.wait(5)
                return
            self.send_response(200)
            self.send_header('Content-Length', '9')
            self.end_headers()
            self.wfile.write(b'transport')
        def log_message(self, *_):
            pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    assert server.fileno() > 1024
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    connection = http.client.HTTPConnection(*server.server_address, timeout=.1 if outcome == 'timeout' else 5)
    try:
        connection.request('GET', '/')
        if outcome == 'timeout':
            with pytest.raises(TimeoutError):
                connection.getresponse()
        else:
            response = connection.getresponse()
            assert response.status == 200 and response.read() == b'transport'
    finally:
        connection.close()
        release.set()
        thread.join(timeout=6)
        server.server_close()
    assert not thread.is_alive()
