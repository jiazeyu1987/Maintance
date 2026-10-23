"""Execute actual migration files against SQLite to verify prerequisite-check ordering."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import intruoyi_runtime_agent as agent
from intruoyi_runtime import file_sha
from ops.release.release_preflight_plan import build_preflight_plan


class MigrationPreflightOrderTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = sqlite3.connect(':memory:')
        self.db.create_function('NOW', 0, lambda: '2026-10-21 00:00:00')
        self.db.execute('CREATE TABLE infra_release_migration(release_tag TEXT,migration_id TEXT,file_name TEXT,sha256 TEXT,target_environment TEXT,status TEXT,operation_id TEXT,creator TEXT,updater TEXT,finished_at TEXT,error_message TEXT)')
        (self.root/'M1.sql').write_text('CREATE TABLE employee(id INTEGER PRIMARY KEY);', encoding='utf-8')
        (self.root/'M2.sql').write_text('INSERT INTO employee(id) VALUES(1);', encoding='utf-8')
        (self.root/'M2.preflight.sql').write_text('SELECT COUNT(*) FROM employee;', encoding='utf-8')
        self.manifest = {'releaseTag': '2026-10-21-00-00-00', 'migrations': [
            {'migrationId': 'M1', 'file': 'M1.sql', 'sha256': file_sha(self.root/'M1.sql'), 'type': 'schema'},
            {'migrationId': 'M2', 'file': 'M2.sql', 'sha256': file_sha(self.root/'M2.sql'), 'type': 'data'}]}
        self.check = {'reference': 'M2.preflight.sql'}

    def tearDown(self):
        self.db.close()
        self.directory.cleanup()

    def sql(self, profile, query):
        # Every statement executes on the real test DB, including the migration ledger.
        self.db.executescript(query)
        return ''

    def preflight(self, profile, root, migration, descriptor):
        self.db.execute('PRAGMA query_only=ON')
        try:
            count = self.db.execute((root/descriptor['reference']).read_text('utf-8')).fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            self.db.execute('PRAGMA query_only=OFF')

    def test_prior_create_table_runs_before_dependent_readonly_check(self):
        plan = [{'migrationId': 'M1', 'action': 'APPLY'},
                {'migrationId': 'M2', 'action': 'APPLY', 'targetPreflight': self.check}]
        with patch.object(agent.remote, 'sql', side_effect=self.sql), patch.object(agent, 'run_target_preflight', side_effect=self.preflight):
            agent.apply_migration_plan({'environment': 'test'}, self.root, self.manifest, plan)
        self.assertEqual(self.db.execute('SELECT id FROM employee').fetchall(), [(1,)])
        self.assertEqual(self.db.execute('SELECT migration_id,status FROM infra_release_migration ORDER BY rowid').fetchall(), [('M1', 'APPLIED'), ('M2', 'APPLIED')])

    def test_missing_prerequisite_is_real_failure_not_default_pass(self):
        plan = [{'migrationId': 'M2', 'action': 'APPLY', 'targetPreflight': self.check}]
        with patch.object(agent.remote, 'sql', side_effect=self.sql), patch.object(agent, 'run_target_preflight', side_effect=self.preflight):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'no such table'):
                agent.apply_migration_plan({'environment': 'test'}, self.root, self.manifest, plan)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM infra_release_migration').fetchone()[0], 0)

    def test_scope_exclusion_does_not_execute_sql_or_write_applied_ledger(self):
        with patch.object(agent.remote, 'sql', side_effect=self.sql) as execute:
            agent.apply_migration_plan({'environment': 'test'}, self.root, self.manifest,
                                       [{'migrationId':'M1','action':'SKIP_SCOPE_EXCLUDED'}])
        execute.assert_not_called()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM infra_release_migration').fetchone()[0], 0)

    def test_later_preflight_failure_preserves_completed_migrations_without_success_receipt(self):
        (self.root/'M2.preflight.sql').write_text('SELECT COUNT(*) FROM missing_policy;', encoding='utf-8')
        plan = [{'migrationId': 'M1', 'action': 'APPLY'},
                {'migrationId': 'M2', 'action': 'APPLY', 'targetPreflight': self.check}]
        with patch.object(agent.remote, 'sql', side_effect=self.sql), patch.object(agent, 'run_target_preflight', side_effect=self.preflight):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'no such table'):
                agent.apply_migration_plan({'environment': 'test'}, self.root, self.manifest, plan)
        self.assertEqual(self.db.execute('SELECT migration_id,status FROM infra_release_migration').fetchall(), [('M1', 'APPLIED')])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM employee').fetchone()[0], 0)

    def test_partial_sql_failure_is_failed_and_blocks_replanning_without_replaying_prior_sql(self):
        # SQLite commits the first insert before the second statement fails, just
        # as a multi-statement migration can leave effects after MySQL DDL commits.
        (self.root/'M2.sql').write_text('INSERT INTO employee VALUES(1); INSERT INTO employee VALUES(1);', encoding='utf-8')
        self.manifest['migrations'][1]['sha256'] = file_sha(self.root/'M2.sql')
        plan = [{'migrationId': 'M1', 'action': 'APPLY'},
                {'migrationId': 'M2', 'action': 'APPLY', 'targetPreflight': self.check}]
        with patch.object(agent.remote, 'sql', side_effect=self.sql), patch.object(agent, 'run_target_preflight', side_effect=self.preflight):
            with self.assertRaisesRegex(agent.RuntimeBlocked, 'Migration execution failed: M2'):
                agent.apply_migration_plan({'environment': 'test'}, self.root, self.manifest, plan)
        self.assertEqual(self.db.execute('SELECT id FROM employee').fetchall(), [(1,)])
        state = {mid: {'status': status, 'sha256': checksum} for mid, status, checksum in
                 self.db.execute('SELECT migration_id,status,sha256 FROM infra_release_migration')}
        self.assertEqual({mid: row['status'] for mid, row in state.items()}, {'M1': 'APPLIED', 'M2': 'FAILED'})
        migrations = [dict(item, allowedEnvironments=['test'], dependsOn=[] if item['migrationId'] == 'M1' else ['M1'])
                      for item in self.manifest['migrations']]
        replanned = build_preflight_plan(migrations, state, target_environment='test', publish_scope='app-release')
        self.assertEqual(replanned['status'], 'blocked')
        self.assertEqual([item['action'] for item in replanned['items']], ['SKIP_ALREADY_APPLIED', 'BLOCKED_LEDGER_STATE'])


if __name__ == '__main__':
    unittest.main()
