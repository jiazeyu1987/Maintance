"""Explicit attempt selection must never reinterpret or overwrite History368."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import common


class AttemptSelection(unittest.TestCase):
    def test_missing_selection_cannot_fall_back_to_old_failed_request(self):
        with tempfile.TemporaryDirectory() as name, patch.object(common, 'TASK', Path(name)):
            (Path(name) / 'restore-58-ui-submission.json').write_text('{}', encoding='utf8')
            with self.assertRaises(FileNotFoundError):common.restore_kind('58')

    def test_only_explicit_new_kind_is_selected_and_original_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as name, patch.object(common, 'TASK', Path(name)):
            root = Path(name);original = root / 'restore-58-ui-submission.json'
            original.write_bytes(b'{"operationId":"original-failed"}')
            manifest = dict(schemaVersion='TaskRestoreAttempts/v1', targets={
                '58': dict(kind='restore-58-r2'), '59': dict(kind='restore-59')})
            (root / 'restore-selected-attempts.json').write_text(json.dumps(manifest), encoding='utf8')
            self.assertEqual(common.restore_kind('58'), 'restore-58-r2')
            self.assertEqual(common.restore_kind('59'), 'restore-59')
            self.assertEqual(original.read_bytes(), b'{"operationId":"original-failed"}')
            manifest['targets']['58']['kind'] = 'restore-59'
            (root / 'restore-selected-attempts.json').write_text(json.dumps(manifest), encoding='utf8')
            with self.assertRaises(AssertionError):common.restore_kind('58')


if __name__ == '__main__':unittest.main()
