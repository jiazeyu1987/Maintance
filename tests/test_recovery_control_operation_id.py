"""Only operation-ID validation and temporary ledger IO; no execution or HTTP."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_smallapp import Failure, Ledger, local_read, persist, request
from recovery_control_smallapp_native import Native


ORIGINAL_ID = 'smallapp-20261014-full-r1'


def full(operation=ORIGINAL_ID):
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId=operation,
        action='FULL', sourceConfigRef='contract-source', parentChainRef=None,
        recoveryPointRef=None, targetConfigRef=None)


def ledger(root):
    configuration = root / 'unconfigured.json'
    persist(configuration, {})
    return Ledger(root, Native(executor.pin(configuration)))


class OperationIdentifierChecks(unittest.TestCase):
    def test_original_generated_format_and_safe_bounds_are_preserved(self):
        for operation in (ORIGINAL_ID, 'smallapp-' + '0123456789abcdef' * 2,
                          'backup_20261015.full:r1', 'a' * 8, 'a' * 160):
            with self.subTest(operation=operation):
                value = full(operation)
                self.assertIs(request(value), value)
                self.assertEqual(value['operationId'], operation)

    def test_unsafe_and_out_of_bounds_ids_are_rejected_before_storage(self):
        invalid = (None, 123, '', 'a' * 7, 'a' * 161, '.', '..', '../outside-operation',
            '/tmp/outside-operation', r'C:\outside-operation', 'C:outside-operation',
            r'\\server\share\operation', 'smallapp/../outside', 'smallapp%2foutside',
            'smallapp with-space', 'smallapp\noperation', 'smallapp\roperation',
            'smallapp\toperation', 'smallapp\x00operation', 'smallapp-操作编号')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            actual = ledger(root)
            before = {p.name for p in root.iterdir()}
            for operation in invalid:
                with self.subTest(operation=repr(operation)):
                    with self.assertRaises(Failure):
                        request(full(operation))
                    with self.assertRaises(Failure):
                        actual.directory(operation)
            self.assertEqual({p.name for p in root.iterdir()}, before)

    def test_same_original_only_queries_unchanged_temporary_intent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            actual = ledger(root)
            value = full()
            # Exercise the real storage primitive using only temporary local
            # intent files. They are never installed or used as runtime receipts.
            self.assertTrue(actual.reserve(value, None))
            directory = actual.directory(ORIGINAL_ID)
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            self.assertFalse(actual.reserve(value, None))
            observed = actual.submit(value)  # Existing ID: query branch only.
            self.assertEqual(observed['operationId'], ORIGINAL_ID)
            self.assertEqual(actual.status(ORIGINAL_ID), observed)
            self.assertEqual(local_read(directory / 'request.json'), value)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before)
            self.assertEqual(actual.active, set())

    def test_same_original_with_changed_request_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            actual = ledger(root)
            value = full()
            actual.reserve(value, None)
            directory = actual.directory(ORIGINAL_ID)
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            for changed in ({**value, 'sourceConfigRef': 'different-source'},
                            {**value, 'action': 'INCREMENTAL', 'parentChainRef': 'different-parent'}):
                with self.subTest(changed=changed):
                    for accept in (actual.reserve, actual.submit):
                        with self.assertRaisesRegex(Failure, '^OPERATION_ID_REUSED$'):
                            if accept == actual.reserve:
                                accept(changed, None)
                            else:
                                accept(changed)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, before)
            self.assertEqual(actual.active, set())


if __name__ == '__main__':
    unittest.main(verbosity=2)
