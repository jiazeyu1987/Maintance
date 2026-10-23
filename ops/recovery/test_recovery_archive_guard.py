import os
from pathlib import Path
import tempfile
import time
import struct
import unittest
from unittest.mock import patch

from recovery_engine import RecoveryError, signature
from recovery_archive_guard import ArchivePathGuard


class ArchiveGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.parent = self.root / 'archive'
        self.parent.mkdir()
        self.file = self.parent / 'payload'
        self.file.write_bytes(b'original')
        self.guard = ArchivePathGuard({str(self.file): signature(self.file.stat())})

    def tearDown(self):
        self.guard.close()
        self.temp.cleanup()

    def changed(self):
        with self.assertRaises(RecoveryError):
            self.guard.check()

    def test_reads_and_unrelated_sibling_writes_are_allowed(self):
        self.assertEqual(b'original', self.file.read_bytes())
        other = self.parent / 'other-operation'
        other.write_bytes(b'unrelated')
        other.unlink()
        self.guard.check()

    def test_same_bytes_and_restored_mtime_fail(self):
        before = self.file.stat()
        # Linux filesystem timestamps may share one scheduler clock tick.
        time.sleep(0.03)
        self.file.write_bytes(b'modified')
        os.utime(self.file, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.changed()

    def test_atomic_replacement_fails(self):
        replacement = self.parent / 'replacement'
        replacement.write_bytes(b'original')
        os.replace(replacement, self.file)
        self.changed()

    def test_parent_renamed_and_symlinked_back_fails(self):
        moved = self.root / 'moved'
        self.parent.rename(moved)
        self.parent.symlink_to(moved, target_is_directory=True)
        self.changed()

    def test_replaced_empty_parent_fails(self):
        self.file.unlink()
        self.parent.rmdir()
        self.parent.mkdir()
        self.file.write_bytes(b'original')
        self.changed()

    def test_hardlink_outside_parent_fails(self):
        os.link(self.file, self.root / 'external-link')
        self.changed()

    def test_file_permissions_changed_fails(self):
        self.file.chmod(0o400)
        self.changed()

    def test_parent_permissions_changed_fails(self):
        self.parent.chmod(0o750)
        self.changed()

    def test_deleted_file_fails(self):
        self.file.unlink()
        self.changed()

    def test_event_overflow_fails_closed(self):
        with patch('recovery_archive_guard.os.read', return_value=struct.pack('iIII', -1, 0x4000, 0, 0)):
            with self.assertRaises(RecoveryError) as raised:
                self.guard.check()
        self.assertEqual('ARCHIVE_WATCH_OVERFLOW', raised.exception.code)

    def test_no_repeated_resolve(self):
        with patch('pathlib.Path.resolve', side_effect=AssertionError('repeated resolve')):
            for _ in range(100):
                self.guard.check()


if __name__ == '__main__':
    unittest.main()
