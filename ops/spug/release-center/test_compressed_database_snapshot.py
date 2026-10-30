"""Real subprocess/stream tests; these do not claim a live database restore."""
import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from intruoyi_runtime import (RuntimeBlocked, capture_sql_snapshot,
                              database_snapshot_path, restore_sql_snapshot)
import intruoyi_runtime_agent as agent


class CompressedSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Include binary hex, Unicode, NULLs and delimiter-sensitive SQL.
        self.sql = ("-- MySQL dump\nINSERT INTO showroom_release_asset VALUES(1,0x".encode()
                    + os.urandom(512 * 1024).hex().encode()
                    + ",NULL,'展厅原有数据');\n".encode('utf-8'))
        self.source = self.root/'source.sql'
        self.source.write_bytes(self.sql)
        self.snapshot = self.root/'recovery.sql.gz'

    def capture(self):
        return capture_sql_snapshot([sys.executable, '-c',
            'import pathlib,sys;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())',
            str(self.source)], self.snapshot, timeout=10)

    def consumer(self, output):
        return [sys.executable, '-c',
                'import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())', str(output)]

    def test_all_sql_and_showroom_blob_bytes_survive_capture_and_restore(self):
        record = self.capture()
        self.assertEqual(record['uncompressedBytes'], len(self.sql))
        self.assertEqual(record['sha256'], hashlib.sha256(self.snapshot.read_bytes()).hexdigest())
        self.assertEqual(record['encoding'], 'gzip')
        self.assertLess(record['bytes'], len(self.sql))
        self.assertEqual(gzip.decompress(self.snapshot.read_bytes()), self.sql)
        output = self.root/'restored.sql'
        restore_sql_snapshot(self.snapshot, self.consumer(output), timeout=10)
        self.assertEqual(output.read_bytes(), self.sql)
        self.assertFalse((self.root/'recovery.sql').exists())

    def test_historical_plain_sql_still_restores_exact_bytes(self):
        path = self.root/'recovery.sql'
        path.write_bytes(self.sql)
        output = self.root/'restored.sql'
        restore_sql_snapshot(path, self.consumer(output), timeout=10)
        self.assertEqual(output.read_bytes(), self.sql)

    def test_failed_or_empty_export_cannot_create_success_record(self):
        for program in ('import sys;sys.stdout.write("partial");sys.exit(3)', 'pass'):
            with self.subTest(program=program), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(RuntimeBlocked):
                    capture_sql_snapshot([sys.executable, '-c', program], Path(folder)/'recovery.sql.gz', 10)

    def test_existing_snapshot_is_never_overwritten(self):
        self.snapshot.write_bytes(b'old point')
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(self.snapshot.read_bytes(), b'old point')

    def test_corrupt_gzip_is_not_treated_as_plain_sql(self):
        self.snapshot.write_bytes(b'not gzip')
        with self.assertRaises(gzip.BadGzipFile):
            restore_sql_snapshot(self.snapshot, self.consumer(self.root/'out.sql'), 10)

    def test_truncated_gzip_cannot_report_success(self):
        self.capture()
        self.snapshot.write_bytes(self.snapshot.read_bytes()[:-8])
        with self.assertRaises(EOFError):
            restore_sql_snapshot(self.snapshot, self.consumer(self.root/'out.sql'), 10)

    def test_failed_consumer_cannot_report_success(self):
        self.capture()
        with self.assertRaises((RuntimeBlocked, BrokenPipeError, OSError)):
            restore_sql_snapshot(self.snapshot, [sys.executable, '-c', 'import sys;sys.exit(9)'], 10)

    def test_capture_timeout_is_failure(self):
        with self.assertRaises(RuntimeBlocked):
            capture_sql_snapshot([sys.executable, '-c', 'import time;time.sleep(10)'], self.snapshot, .1)

    def test_restore_timeout_is_failure(self):
        self.capture()
        with self.assertRaises((RuntimeBlocked, BrokenPipeError, OSError)):
            restore_sql_snapshot(self.snapshot, [sys.executable, '-c', 'import time;time.sleep(10)'], .1)

    def test_recovery_path_cannot_escape_its_release(self):
        for path in (self.root.parent/'recovery.sql.gz', self.root/'anything.sql'):
            with self.assertRaises(RuntimeBlocked):
                database_snapshot_path(self.root, {'path': str(path)})

    def test_actual_backup_command_keeps_all_tables_and_objects(self):
        with patch.object(agent, 'check_storage'), patch.object(agent.remote, 'inspect',
                return_value={'Config': {'Env': ['MYSQL_ROOT_PASSWORD=unit-test-only']}}), \
                patch.object(agent, 'capture_sql_snapshot', return_value={'encoding': 'gzip'}) as capture:
            agent.backup({'database': 'registered-db'}, self.root)
        command = capture.call_args.args[0][-1]
        for flag in ('--routines', '--events', '--triggers', '--hex-blob', '--single-transaction'):
            self.assertIn(flag, command)
        self.assertNotIn('ignore-table', command)
        self.assertNotIn('showroom', command)
        self.assertNotIn('unit-test-only', command)
        self.assertEqual(capture.call_args.args[1], self.snapshot)


if __name__ == '__main__':
    unittest.main()
