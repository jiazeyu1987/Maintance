"""Standalone CLI orchestration contracts only; no target database is contacted."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import intruoyi_runtime_agent as agent
from intruoyi_runtime import (ROUTE_SNAPSHOT_MIGRATION, ROUTE_SNAPSHOT_SHA256, ROUTE_SNAPSHOT_HOOK,
                              Runtime, RuntimeBlocked, package_identity, validate_migration_handler, validate_snapshot_cli_report)


class SnapshotHandlerTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(migrationId=ROUTE_SNAPSHOT_MIGRATION, sha256=ROUTE_SNAPSHOT_SHA256,
                         approvedHook=ROUTE_SNAPSHOT_HOOK, type='schema', file='enforce.sql')
        self.manifest = dict(releaseTag='2026-10-23-01-00-00', migrations=[self.item],
                             images={'backend':{'id':'sha256:'+'a'*64}})
        self.expected = dict(mode='PRECHECK', releaseTag=self.manifest['releaseTag'],
                            migrationId=ROUTE_SNAPSHOT_MIGRATION, imageId=self.manifest['images']['backend']['id'],
                            operationId='operation', packageIdentity=package_identity(self.manifest), targetDatabase='ruoyi-vue-pro')
        self.report = dict(self.expected, schemaVersion='route-snapshot-migration/v1', status='READY',
                           scannedCount=5, updatedCount=0, blockerCount=0, blockers=[])

    def test_binding_semantics_counts_and_readonly_writes_are_required_beyond_exit_zero(self):
        self.assertEqual(validate_snapshot_cli_report(self.report, self.expected, 0), self.report)
        for changes in (dict(imageId='other'), dict(packageIdentity='other'), dict(targetDatabase='other'),
                        dict(updatedCount=1), dict(blockerCount=1), dict(scannedCount=-1), dict(scannedCount=True),
                        dict(sql='secret')):
            with self.subTest(changes=changes), self.assertRaises(RuntimeBlocked):
                validate_snapshot_cli_report(dict(self.report, **changes), self.expected, 0)
        with self.assertRaises(RuntimeBlocked):
            validate_snapshot_cli_report(self.report, self.expected, 2)

    def test_error_does_not_invent_zero_writes_after_uncertain_database_failure(self):
        report = dict(self.expected, schemaVersion='route-snapshot-migration/v1', status='ERROR', errorCode='DATABASE_COMMAND_FAILED')
        report.pop('targetDatabase')
        checked = validate_snapshot_cli_report(report, self.expected, 3)
        self.assertNotIn('updatedCount', checked)
        with self.assertRaises(RuntimeBlocked):
            validate_snapshot_cli_report(report, self.expected, 0)

    def test_hook_is_fixed_to_one_immutable_migration_and_never_arbitrary(self):
        self.assertEqual(validate_migration_handler(self.item), '')
        for changes in (dict(sha256='0'*64), dict(migrationId='other'), dict(approvedHook='arbitrary'), dict(approvedHook='')):
            with self.subTest(changes=changes), self.assertRaises(RuntimeBlocked):
                validate_migration_handler(dict(self.item, **changes))

    def test_cli_uses_only_candidate_launcher_private_auth_and_bound_database_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'stage-verified.json').write_text(json.dumps(dict(manifestSha256=package_identity(self.manifest))), encoding='utf-8')
            database = dict(Id='b'*64, State={'Running':True}, Config={'Env':['MYSQL_DATABASE=ruoyi-vue-pro', 'MYSQL_ROOT_PASSWORD=unit-secret']})
            def process(command, **kwargs):
                self.assertNotIn('unit-secret', ' '.join(command))
                self.assertIn('container:'+'b'*64, command)
                self.assertIn('/yudao-server/app.jar', command)
                self.assertIn('org.springframework.boot.loader.launch.PropertiesLauncher', command)
                self.assertIn(self.expected['imageId'], command)
                self.assertNotIn('-jar', command)
                self.assertFalse(any(part.startswith(('-p=', '--publish', '--volumes-from')) for part in command))
                credentials = Path(command[command.index('--env-file')+1])
                self.assertIn('MES_SNAPSHOT_JDBC_PASSWORD=unit-secret', credentials.read_text())
                self.assertIn('jdbc:mysql://127.0.0.1:3306/ruoyi-vue-pro?', credentials.read_text())
                options = dict(value[2:].split('=',1) for value in command if value.startswith('--') and '=' in value)
                report = dict(self.report, operationId=options['operation-id'], packageIdentity=options['package-identity'])
                (credentials.parent/'report.json').write_text(json.dumps(report), encoding='utf-8')
                return SimpleNamespace(returncode=0, stdout=b'ignored private output', stderr=b'ignored private error')
            with patch.object(agent.remote, 'inspect', return_value=database), \
                    patch.object(agent.remote, 'run', return_value=(self.expected['imageId']+'\n').encode()), \
                    patch.object(agent.subprocess, 'run', side_effect=process):
                result = agent.run_snapshot_cli({'database':'registered-db'}, root, self.manifest, self.item, 'PRECHECK')
            self.assertEqual(result['status'], 'READY')
            self.assertEqual(result['databaseContainerId'], 'b'*64)
            self.assertEqual(list(root.rglob('jdbc.private.env')), [])
            self.assertTrue(Path(result['reportPath']).is_file())

    def test_precheck_failure_does_not_stop_application_or_write_migration(self):
        with patch.object(agent, 'preflight', side_effect=RuntimeBlocked('PRECHECK blocked: MISSING_NODES')), \
                patch.object(agent, 'stop_writers') as stop, patch.object(agent, 'apply_migration_plan') as apply:
            with self.assertRaisesRegex(RuntimeBlocked, 'MISSING_NODES'):
                agent.deploy({}, self.manifest)
            stop.assert_not_called()
            apply.assert_not_called()
        runtime = object.__new__(Runtime)
        with patch.object(runtime, 'preflight', side_effect=RuntimeBlocked('PRECHECK blocked: MISSING_NODES')), \
                patch.object(runtime, 'call') as call:
            events = []
            with self.assertRaisesRegex(RuntimeBlocked, 'MISSING_NODES'):
                runtime.deploy('test', self.manifest, lambda *args, **kwargs:events.append((args, kwargs)), 'JOB-1234567890')
            self.assertEqual(events, [])
            call.assert_not_called()

    def test_backfill_and_readiness_require_maintenance_before_launch(self):
        for mode in ('BACKFILL', 'READINESS'):
            with self.subTest(mode=mode), patch.object(agent.subprocess, 'run') as process:
                with self.assertRaisesRegex(RuntimeBlocked, 'Completed recovery record'):
                    agent.run_snapshot_cli({}, Path('.'), self.manifest, self.item, mode)
                process.assert_not_called()

    def test_applied_enforcement_does_not_repeat_hook(self):
        with patch.object(agent, 'run_snapshot_cli') as cli:
            self.assertEqual(agent.snapshot_precheck({}, self.manifest, [dict(migrationId=ROUTE_SNAPSHOT_MIGRATION, action='SKIP_ALREADY_APPLIED')]), [])
            agent.apply_migration_plan({}, Path('.'), self.manifest, [dict(migrationId=ROUTE_SNAPSHOT_MIGRATION, action='SKIP_ALREADY_APPLIED')])
            cli.assert_not_called()

    def test_backfill_readiness_precede_original_enforcement_and_need_maintenance(self):
        for blocked in (False, True):
            with self.subTest(blocked=blocked), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'enforce.sql').write_text('ORIGINAL ENFORCE', encoding='utf-8')
                events = []
                def cli(profile, folder, manifest, item, mode, recovery):
                    agent.require_migration_maintenance(profile, folder, recovery)
                    events.append(mode)
                    if blocked: raise RuntimeBlocked('snapshot blocked')
                item = dict(self.item, requiresTargetPreflight=True)
                with patch.object(agent, 'file_sha', return_value=ROUTE_SNAPSHOT_SHA256), \
                        patch.object(agent, 'require_migration_maintenance', side_effect=lambda *args:events.append('maintenance')), \
                        patch.object(agent, 'run_snapshot_cli', side_effect=cli), \
                        patch.object(agent, 'run_target_preflight', side_effect=lambda *args:events.append('sql-preflight')), \
                        patch.object(agent.remote, 'sql', side_effect=lambda profile, sql:events.append('enforce' if sql=='ORIGINAL ENFORCE' else 'ledger')):
                    operation = lambda:agent.apply_migration_plan({'environment':'test'}, root, dict(self.manifest, migrations=[item]),
                        [dict(migrationId=ROUTE_SNAPSHOT_MIGRATION, action='APPLY', targetPreflight={})], recovery={'evidence':'unit'})
                    if blocked:
                        with self.assertRaises(RuntimeBlocked): operation()
                        self.assertEqual(events, ['maintenance', 'BACKFILL'])
                    else:
                        operation()
                        self.assertEqual(events, ['maintenance', 'BACKFILL', 'maintenance', 'READINESS', 'sql-preflight', 'ledger', 'enforce', 'ledger'])


if __name__ == '__main__':
    unittest.main()
