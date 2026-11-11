"""Real win32 file times and FD lifetime; no Linux flags or successful stat mocks."""
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
import minimal_capture_support as support


@pytest.fixture(autouse=True)
def actual_windows():
    assert sys.platform == 'win32', 'ACTUAL_WINDOWS_REQUIRED_NOT_A_SKIP'
    assert Path(support.__file__).resolve() == ROOT/'ops/recovery/minimal_capture_support.py'


def set_creation_time(path, nanoseconds):
    """Actual SetFileTime on the owned temporary file, not a stat substitute."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.SetFileTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)]
    kernel.SetFileTime.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(path), 0x100, 0x1|0x2|0x4, None, 3, 0x80, None)
    assert handle != ctypes.c_void_p(-1).value, ctypes.get_last_error()
    ticks = nanoseconds//100 + 116444736000000000
    value = wintypes.FILETIME(ticks & 0xffffffff, ticks >> 32)
    try:
        assert kernel.SetFileTime(handle, ctypes.byref(value), None, None), ctypes.get_last_error()
    finally:
        assert kernel.CloseHandle(handle), ctypes.get_last_error()


def original(tmp_path):
    path = tmp_path/'actual-original.bin'; raw = b'owned real Windows bytes\x00'*80000
    path.write_bytes(raw)
    # Establish an actual, intentionally different path creation time. This is
    # not CIFS modeling; it exposes the installed CPython win32 API distinction.
    set_creation_time(path, path.lstat().st_ctime_ns-1000000000)
    return path, raw


def test_windows_stable_cross_api_ctime_difference_has_exact_pin(tmp_path):
    path, raw = original(tmp_path)
    before = path.lstat()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        assert before.st_ctime_ns != opened.st_ctime_ns, 'REAL_PLATFORM_DISTINCTION_NOT_REPRODUCED'
    assert support.actual_pin(path) == dict(path=str(path), bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('which', ['fd-change-time', 'path-creation-time'])
def test_windows_read_interval_ctime_change_is_rejected(tmp_path, which):
    path, raw = original(tmp_path); calls = []; observations = []
    def guard():
        if calls:return
        calls.append(which)
        before = path.lstat()
        with path.open('rb') as stream:fd_before = os.fstat(stream.fileno())
        if which == 'fd-change-time':
            with path.open('r+b') as stream:
                stream.write(bytes([raw[0]^1]));stream.flush();os.fsync(stream.fileno())
                stream.seek(0);stream.write(raw[:1]);stream.flush();os.fsync(stream.fileno())
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        else:
            set_creation_time(path, before.st_ctime_ns-1000000000)
        after = path.lstat()
        with path.open('rb') as stream:fd_after = os.fstat(stream.fileno())
        assert path.read_bytes() == raw and before.st_mtime_ns == after.st_mtime_ns
        assert (fd_before.st_ctime_ns != fd_after.st_ctime_ns if which == 'fd-change-time'
                else before.st_ctime_ns != after.st_ctime_ns)
        observations.append((before.st_ctime_ns, after.st_ctime_ns,
                             fd_before.st_ctime_ns, fd_after.st_ctime_ns))
    with pytest.raises(RuntimeError, match='MINIMAL_INPUT_CHANGED'):
        support.actual_pin(path, guard)
    assert calls == [which] and len(observations) == 1, 'READ_INTERVAL_GUARD_NOT_REACHED'


def test_windows_guard_original_error_preserved_after_fd_baseline(tmp_path):
    path, _ = original(tmp_path); calls = []; error = LookupError('original-windows-guard-error')
    def guard():
        calls.append(True)
        raise error
    with pytest.raises(LookupError) as caught:
        support.actual_pin(path, guard)
    assert caught.value is error and calls == [True]
