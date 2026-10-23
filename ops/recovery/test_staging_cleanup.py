"""Real filesystem safety checks for successful-operation staging cleanup."""
import json
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from staging_cleanup import cleanup, capture_paths, restore_paths, StagingCleanupError


@unittest.skipUnless(os.name == 'posix', 'Linux directory-descriptor cleanup')
class StagingCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)/'operation-1'; self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def put(self, relative, data=b'temporary-data'):
        p = self.root/relative; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def test_full_and_incremental_capture_leave_only_operation_evidence(self):
        for name in ['payload/database.sql.gz', 'payload/binlog-000.sql',
                     'payload/minio-physical/bucket/xl.meta', 'original-configs/application.bin',
                     'semantic-capture/objects/sha256/aa/content.bin',
                     'recovery-materials/code.bin', 'scratch-before/0/tokens.tsv',
                     'scratch-after/0/rows.bin']:
            self.put(name)
        evidence = self.put('terminal-result.json', b'original-receipt')
        archived = {p.relative_to(self.root).as_posix(): (p.stat().st_size,
                    hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.root.rglob('*')
                    if p.is_file() and not p.relative_to(self.root).parts[0].startswith('scratch-')}
        result = cleanup(self.root, capture_paths(self.root), 'operation-1', guard=lambda: None,
                         archived_files=archived, scratch_paths=('scratch-before', 'scratch-after'))
        receipt = json.loads(result.read_bytes())
        self.assertEqual(receipt['state'], 'SUCCEEDED')
        self.assertEqual(receipt['deletedFiles'], 8)
        self.assertEqual(receipt['deletedBytes'], 8*len(b'temporary-data'))
        self.assertEqual(evidence.read_bytes(), b'original-receipt')
        self.assertEqual(capture_paths(self.root), [])

    def test_restore_cleans_full_and_all_incremental_steps(self):
        temporary = ['database-000/archive-sql.private.gz', 'database-000/expanded.sql',
                     'database-000/database-readback/0/tokens.tsv',
                     'database-001/incremental.sql', 'database-002/binlog-000.sql',
                     'objects/physical-export/objects/sha256/aa/object.bin']
        for name in temporary:
            self.put(name)
        retained = [self.put(name) for name in ['database-000/result.json',
            'objects/physical-export/versions.jsonl', 'objects/physical-export/export-receipt.json',
            'objects/physical-version-mapping.jsonl', 'final/application-start.json']]
        with patch('staging_cleanup.hashlib.sha256', side_effect=AssertionError('disposable content must not be read')):
            receipt = cleanup(self.root, restore_paths(self.root), 'operation-1', guard=lambda: None)
        self.assertTrue(all('sha256' not in row for row in json.loads(receipt.read_bytes())['files']))
        self.assertTrue(all(not (self.root/name).exists() for name in temporary))
        self.assertTrue(all(p.exists() for p in retained))

    def test_scratch_is_not_hashed_but_archived_bytes_are_checked(self):
        data = b'archived-content'
        self.put('payload/database.sql.gz', data)
        self.put('scratch-after/0/rows.bin', b'disposable')
        checksum = hashlib.sha256(data).hexdigest()
        with patch('staging_cleanup.hashlib.sha256', wraps=hashlib.sha256) as hashes:
            receipt = cleanup(self.root, ['payload', 'scratch-after'], 'operation-1', guard=lambda: None,
                archived_files={'payload/database.sql.gz': (len(data), checksum)}, scratch_paths=('scratch-after',))
        self.assertEqual(hashes.call_count, 1)
        rows = json.loads(receipt.read_bytes())['files']
        self.assertEqual(rows[0]['sha256'], checksum)
        self.assertNotIn('sha256', rows[1])

    def test_symlink_rejected_before_any_deletion(self):
        good = self.put('payload/a.bin')
        outside = Path(self.temp.name)/'outside'; outside.write_bytes(b'untouched')
        (self.root/'payload/z-link').symlink_to(outside)
        with self.assertRaises(StagingCleanupError):
            cleanup(self.root, ['payload'], 'operation-1', guard=lambda: None)
        self.assertTrue(good.exists())
        self.assertEqual(outside.read_bytes(), b'untouched')

    def test_traversal_and_wrong_operation_rejected(self):
        self.put('payload/a.bin')
        for paths, op in [(['../outside'], 'operation-1'), (['payload'], 'different-operation')]:
            with self.assertRaises(StagingCleanupError):
                cleanup(self.root, paths, op, guard=lambda: None)

    def test_changed_file_after_intent_is_retained_and_error_surfaces(self):
        p = self.put('payload/a.bin')
        changed = False
        def guard():
            nonlocal changed
            if (self.root/'staging-cleanup-intent.json').exists() and not changed:
                p.write_bytes(b'changed-after-validation'); changed = True
        with self.assertRaises(StagingCleanupError):
            cleanup(self.root, ['payload'], 'operation-1', guard=guard)
        self.assertEqual(p.read_bytes(), b'changed-after-validation')
        self.assertFalse((self.root/'staging-cleanup.json').exists())

    def test_parent_symlink_rejected(self):
        outside = Path(self.temp.name)/'outside'; outside.mkdir()
        (outside/'data').write_bytes(b'untouched')
        (self.root/'payload').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            cleanup(self.root, ['payload/data'], 'operation-1', guard=lambda: None)
        self.assertEqual((outside/'data').read_bytes(), b'untouched')

    def test_unarchived_or_changed_backup_bytes_are_not_deleted(self):
        p = self.put('payload/database.sql.gz', b'changed-backup')
        with self.assertRaises(StagingCleanupError):
            cleanup(self.root, ['payload'], 'operation-1', guard=lambda: None,
                archived_files={'payload/database.sql.gz': (3, hashlib.sha256(b'old').hexdigest())})
        self.assertEqual(p.read_bytes(), b'changed-backup')
        self.assertFalse((self.root/'staging-cleanup-intent.json').exists())


if __name__ == '__main__':
    unittest.main()
