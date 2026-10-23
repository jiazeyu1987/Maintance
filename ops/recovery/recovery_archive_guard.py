"""Fail closed when a verified Linux archive path or its ancestry changes."""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import stat
import struct

from recovery_engine import RecoveryError, require, signature


class ArchivePathGuard:
    # Reads do not produce these events. File watches also catch writes through
    # an open descriptor and link-count changes outside a watched parent.
    _CHANGES = 0x2 | 0x4 | 0x8 | 0x40 | 0x80 | 0x100 | 0x200
    _SELF = 0x400 | 0x800 | 0x2000 | 0x8000
    _OVERFLOW = 0x4000

    def __init__(self, expected, *, closed_directories=()):
        require(os.name == 'posix' and bool(expected), 'ARCHIVE_WATCH_LINUX_REQUIRED')
        self.fd = -1
        self.watches = {}
        self.closed_directory_watches = set()
        libc = ctypes.CDLL(None, use_errno=True)
        init = libc.inotify_init1
        init.argtypes = [ctypes.c_int]
        init.restype = ctypes.c_int
        self.add = libc.inotify_add_watch
        self.add.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        self.add.restype = ctypes.c_int
        self.fd = init(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise RecoveryError('ARCHIVE_WATCH_INIT_FAILED')
        try:
            parents = {}
            closed_directories = {Path(value) for value in closed_directories}
            for path in closed_directories:
                require(path.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
                parents.setdefault(path, set())
                for child in (path, *path.parents[:-1]):
                    parents.setdefault(child.parent, set()).add(child.name)
            for value in expected:
                path = Path(value)
                require(path.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
                for child in (path, *path.parents[:-1]):
                    parents.setdefault(child.parent, set()).add(child.name)
            require(int(Path('/proc/sys/fs/inotify/max_user_watches').read_text()) >= len(parents) + len(expected),
                    'ARCHIVE_WATCH_LIMIT_TOO_LOW')
            identities = {}
            for path, names in parents.items():
                before = path.lstat()
                require(stat.S_ISDIR(before.st_mode), 'PATH_ALIAS_REJECTED')
                identities[path] = (before.st_dev, before.st_ino)
                wd = self._watch(path, names, directory=True)
                if path in closed_directories:
                    self.closed_directory_watches.add(wd)
            for value in expected:
                self._watch(Path(value), None, directory=False)
            # Close setup races after both directory and inode watches exist.
            for value, wanted in expected.items():
                require(signature(Path(value).lstat()) == wanted, 'ARCHIVED_PAYLOAD_CHANGED')
            for path, wanted in identities.items():
                current = path.lstat()
                require(stat.S_ISDIR(current.st_mode) and
                        (current.st_dev, current.st_ino) == wanted, 'PATH_ALIAS_REJECTED')
            self.check()
        except BaseException:
            self.close()
            raise

    def _watch(self, path, names, *, directory):
        mask = self._CHANGES | self._SELF | 0x02000000  # IN_DONT_FOLLOW
        if directory:
            mask |= 0x01000000  # IN_ONLYDIR
        wd = self.add(self.fd, os.fsencode(path), mask)
        if wd < 0:
            raise RecoveryError('ARCHIVE_WATCH_INSTALL_FAILED')
        if wd in self.watches:
            prior = self.watches[wd]
            require(prior is not None and names is not None, 'ARCHIVE_WATCH_ALIAS_REJECTED')
            prior.update(names)
        else:
            self.watches[wd] = None if names is None else set(names)
        return wd

    def check(self):
        require(self.fd >= 0, 'ARCHIVE_WATCH_CLOSED')
        while True:
            try:
                events = os.read(self.fd, 65536)
            except BlockingIOError:
                return
            except OSError as error:
                raise RecoveryError('ARCHIVE_WATCH_READ_FAILED') from error
            require(bool(events), 'ARCHIVE_WATCH_READ_FAILED')
            offset = 0
            while offset < len(events):
                require(offset + 16 <= len(events), 'ARCHIVE_WATCH_EVENT_INVALID')
                wd, mask, _, length = struct.unpack_from('iIII', events, offset)
                end = offset + 16 + length
                require(end <= len(events), 'ARCHIVE_WATCH_EVENT_INVALID')
                name = os.fsdecode(events[offset + 16:end].split(b'\0', 1)[0])
                offset = end
                require(not mask & self._OVERFLOW, 'ARCHIVE_WATCH_OVERFLOW')
                require(wd in self.watches, 'ARCHIVE_WATCH_EVENT_INVALID')
                names = self.watches[wd]
                require(not mask & self._SELF, 'ARCHIVED_PAYLOAD_CHANGED')
                # Membership includes unexpected children, even in empty dirs.
                # Writes to excluded live control files remain owner-guarded.
                require(not (wd in self.closed_directory_watches and
                             mask & (0x40 | 0x80 | 0x100 | 0x200)),
                        'ARCHIVED_PAYLOAD_CHANGED')
                require(not (mask & self._CHANGES and
                             (names is None or not name or name in names)),
                        'ARCHIVED_PAYLOAD_CHANGED')

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1
