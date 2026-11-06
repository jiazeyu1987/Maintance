"""Continuous Linux custody for fully authenticated incremental parent inputs.

Pipe callbacks drain kernel events rather than rehashing the complete parent.
Phase boundaries still reread all metadata and check every file and ancestor:
remote filesystem changes are not assumed to generate local inotify events.
"""
import os
from pathlib import Path
import stat

from formal_capture_incremental import require
from formal_capture_recovery_inputs import original_bytes
from recovery_archive_guard import ArchivePathGuard


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class ParentInputGuard:
    def __init__(self, metadata, contents, owner_current, verify_content):
        self.lease = None
        self.owner_current = owner_current
        self.metadata = [(dict(ref), raw, allow_empty) for ref, raw, allow_empty in metadata]
        self.contents = [dict(ref) for ref in contents]
        references = [ref for ref, _, _ in self.metadata] + self.contents
        paths = {ref['path'] for ref in references}
        try:
            # Hold ancestors and all files before collecting the full identity
            # baseline or authenticating content. Capture closes setup races.
            self.lease = ArchivePathGuard.capture(paths)
            self.files = {str(path): identity(os.fstat(fd))
                          for path, fd in self.lease.path_fds.items()
                          if str(path) in paths}
            self.directories = {str(path): (info.st_dev, info.st_ino, info.st_mode)
                                for path, fd in self.lease.path_fds.items()
                                if str(path) not in paths for info in [os.fstat(fd)]}
            self.verify()
            for ref in self.contents:
                # The original strict STANDARD verifier still reads every byte
                # and checks SHA/size plus before/after fd and path identities.
                verify_content(ref, self._current)
            self.verify()
        except BaseException:
            self.close()
            raise

    def check(self):
        require(self.lease is not None, 'FORMAL_CAPTURE_PARENT_GUARD_CLOSED')
        self.lease.check()

    def _current(self):
        self.owner_current()
        self.check()

    def verify(self):
        self._current()
        for path, wanted in self.directories.items():
            info = Path(path).lstat()
            require(stat.S_ISDIR(info.st_mode) and
                    (info.st_dev, info.st_ino, info.st_mode) == wanted,
                    'FORMAL_CAPTURE_SEMANTIC_PARENT_CHANGED')
        for path, wanted in self.files.items():
            require(identity(Path(path).lstat()) == wanted,
                    'FORMAL_CAPTURE_OBJECT_PARENT_CHANGED')
        for ref, raw, allow_empty in self.metadata:
            self._current()
            require(original_bytes(ref, allow_empty=allow_empty) == raw,
                    'FORMAL_CAPTURE_SEMANTIC_PARENT_CHANGED')
        self._current()

    def close(self):
        lease, self.lease = self.lease, None
        if lease is not None:
            lease.close()
