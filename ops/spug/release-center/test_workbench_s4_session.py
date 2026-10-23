"""S4 session authorization contracts; no remote SQL is executed."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import intruoyi_build as build
import intruoyi_runtime_agent as agent
from intruoyi_runtime import (WORKBENCH_S4_MAINTENANCE_MIGRATIONS, RuntimeBlocked,
                              bind_reviewed_session_profile, migration_execution_sql, validate_migration_handler)


class S4SessionTests(unittest.TestCase):
    def migration(self, mid=None):
        mid = mid or next(iter(WORKBENCH_S4_MAINTENANCE_MIGRATIONS))
        return dict(migrationId=mid, sha256=WORKBENCH_S4_MAINTENANCE_MIGRATIONS[mid],
                    type='schema', sessionProfile='workbench-s4-maintenance', file=mid+'.sql')

    def test_exact_reviewed_migrations_require_confirmed_maintenance(self):
        for mid in WORKBENCH_S4_MAINTENANCE_MIGRATIONS:
            migration = self.migration(mid)
            for unconfirmed in (False, None, 'true', 1):
                with self.subTest(mid=mid, maintenance=unconfirmed), self.assertRaisesRegex(RuntimeBlocked, 'stopped writers'):
                    migration_execution_sql(migration, 'SELECT 1;', unconfirmed)
            self.assertEqual(migration_execution_sql(migration, 'SELECT 1;', True),
                             'SET @profile_workbench_s4_maintenance=1;\nSELECT 1;')

    def test_wrong_identity_bytes_profile_and_arbitrary_hooks_are_rejected(self):
        for mid in WORKBENCH_S4_MAINTENANCE_MIGRATIONS:
            for changes in (dict(migrationId='other'), dict(sha256='0'*64), dict(sessionProfile=''),
                            dict(sessionProfile='workbench-s3-maintenance'), dict(approvedHook='arbitrary')):
                with self.subTest(mid=mid, changes=changes), self.assertRaises(RuntimeBlocked):
                    validate_migration_handler(dict(self.migration(mid), **changes))
        normal = dict(migrationId='normal', sessionProfile='')
        bind_reviewed_session_profile(normal)
        self.assertEqual(normal['sessionProfile'], '')
        self.assertEqual(migration_execution_sql(normal, 'SELECT 1;', True), 'SELECT 1;')

    def test_collector_seals_profile_without_modifying_sql_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sql = root/'IntRuoyiBackend/sql/mysql'
            sql.mkdir(parents=True)
            (sql/'release-sources.json').write_text(json.dumps({}), encoding='utf-8')
            entries = [dict(self.migration(mid), sessionProfile='', file='sql/mysql/'+mid+'.sql',
                            requiresTargetPreflight=False, dependsOn=[], applyOrder=None)
                       for mid in WORKBENCH_S4_MAINTENANCE_MIGRATIONS]
            for item in entries:
                (sql/Path(item['file']).name).write_bytes(b'untouched collector boundary fixture')
            before = {path:path.read_bytes() for path in sql.iterdir()}
            with patch.object(build, 'release_paths', return_value=([], [])), \
                    patch.object(build, 'run_migration_policy_gate', return_value={'migrations':copy.deepcopy(entries)}):
                migrations, _, artifacts = build.migration_inputs(root)
            self.assertEqual({item['sessionProfile'] for item in migrations}, {'workbench-s4-maintenance'})
            self.assertEqual({path:path.read_bytes() for path in sql.iterdir()}, before)
            self.assertTrue(all(item['file'] in artifacts for item in migrations))

    def test_remote_execution_checks_snapshot_fence_and_stopped_writers_before_injection(self):
        for missing in ('snapshot', 'fence', 'writer', None):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                migration = self.migration()
                (root/migration['file']).write_text('SELECT 1;', encoding='utf-8')
                (root/'recovery-record.private.json').write_text('{}', encoding='utf-8')
                recovery = dict(path=str(root/'recovery.sql'), sha256='a'*64)
                if missing == 'snapshot': recovery = None
                with patch.object(agent, 'file_sha', return_value=migration['sha256']), \
                        patch.object(agent.remote, 'sql', return_value='') as execute, \
                        patch.object(agent, 'check_fence', side_effect=RuntimeBlocked('fence active') if missing == 'fence' else None), \
                        patch.object(agent.remote, 'inspect', return_value={'State':{'Running':missing == 'writer'}}):
                    if missing:
                        with self.assertRaises(RuntimeBlocked):
                            agent.apply_migration_plan(dict(environment='test', writers=['app']), root,
                                dict(releaseTag='candidate', migrations=[migration]),
                                [dict(migrationId=migration['migrationId'], action='APPLY')], recovery)
                    else:
                        agent.apply_migration_plan(dict(environment='test', writers=['app']), root,
                            dict(releaseTag='candidate', migrations=[migration]),
                            [dict(migrationId=migration['migrationId'], action='APPLY')], recovery)
                    injected = [call.args[1] for call in execute.call_args_list if call.args[1].startswith('SET @profile_')]
                    self.assertEqual(injected, [] if missing else ['SET @profile_workbench_s4_maintenance=1;\nSELECT 1;'])


if __name__ == '__main__':
    unittest.main()
