import os
from pathlib import Path
import tempfile
import time
import struct
import json
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

    def test_write_failure_identifies_watch_without_file_contents(self):
        self.file.write_bytes(b'secret-content-not-for-diagnostics')
        with self.assertRaises(RecoveryError) as raised:
            self.guard.check()
        self.assertEqual('ARCHIVED_PAYLOAD_CHANGED', raised.exception.code)
        detail = raised.exception.archive_diagnostic
        self.assertEqual('inotify', detail['kind'])
        self.assertEqual(str(self.file), str(Path(detail['watchPath']) / detail['name']) if detail['name'] else detail['watchPath'])
        self.assertIsInstance(detail['mask'], int)
        self.assertNotIn('secret-content', str(detail))

    def test_setup_drift_records_expected_and_observed_signature(self):
        expected = signature(self.file.stat())
        self.file.write_bytes(b'a-different-length')
        with self.assertRaises(RecoveryError) as raised:
            ArchivePathGuard({str(self.file): expected})
        self.assertEqual('ARCHIVED_PAYLOAD_CHANGED', raised.exception.code)
        detail = raised.exception.archive_diagnostic
        self.assertEqual('signature', detail['kind'])
        self.assertEqual(str(self.file), detail['path'])
        self.assertEqual(list(expected), detail['expected'])
        self.assertEqual(list(signature(self.file.stat())), detail['observed'])

    def test_worker_preserves_archive_diagnostic_in_failed_result(self):
        from recovery_minimal_worker import main
        self.file.write_bytes(b'changed')
        with self.assertRaises(RecoveryError) as raised:
            self.guard.check()
        request = self.root / 'request.json'
        configuration = self.root / 'configuration.json'
        output = self.root / 'result.json'
        request.write_text(json.dumps(dict(schemaVersion='SmallAppBackupUiRequest/v1',
            operationId='diagnostic-test', action='RESTORE', sourceConfigRef='source',
            parentChainRef=None, recoveryPointRef='point', targetConfigRef='target')))
        configuration.write_text(json.dumps(dict(operationsRoot=str(self.root / 'operations'))))
        # This unit boundary tests error serialization, not configuration admission.
        # The triggering archive event and the written result are real local files.
        with patch('recovery_minimal_worker.configuration_contract'), \
                patch('recovery_minimal_runtime.execute', side_effect=raised.exception):
            code = main(['--configuration', str(configuration), '--request', str(request), '--output', str(output)])
        result = json.loads(output.read_text())
        self.assertEqual(1, code)
        self.assertEqual('FAILED_RETAINED', result['state'])
        self.assertEqual('ARCHIVED_PAYLOAD_CHANGED', result['failureCode'])
        self.assertFalse(result['data']['mutationDispatched'])
        self.assertEqual(raised.exception.archive_diagnostic, result['data']['archiveDiagnostic'])


if __name__ == '__main__':
    unittest.main()
