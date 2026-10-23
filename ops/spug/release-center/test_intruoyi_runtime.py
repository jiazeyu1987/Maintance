from state_store import StateStore, migrate
"""Pure migration identity policy tests; no DB/SSH success is simulated."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
from intruoyi_runtime import audit_ledger, Runtime, RuntimeBlocked, package_identity, validate_release_state, runtime_config_snapshot, sha, validate_migration_handler, migration_execution_sql


class LedgerAuditTest(unittest.TestCase):
    def setUp(self):
        self.a = {'migrationId': '20261001_alpha', 'sha256': 'a' * 64}
        self.b = {'migrationId': '20261002_beta', 'sha256': 'b' * 64}
        self.manifest = {'migrations': [self.a, self.b]}
        self.obs = {'ledgerRecords': [dict(self.a, status='APPLIED')]}

    def test_only_verified_applied_history_is_satisfied(self):
        self.assertEqual(audit_ledger(self.obs, self.manifest)['missing'], [self.b['migrationId']])

    def test_identical_records_from_multiple_release_operations_preserve_evidence(self):
        self.obs['ledgerRecords'].append(dict(self.a, status='SKIPPED_ALREADY_APPLIED'))
        result = audit_ledger(self.obs, self.manifest)
        self.assertEqual(result['recordCount'], 2)
        self.assertEqual(result['applied'], [self.a['migrationId']])

    def test_excluded_record_does_not_claim_applied(self):
        self.obs['ledgerRecords'][0]['status'] = 'SKIPPED_ENV_NOT_ALLOWED'
        self.assertEqual(len(audit_ledger(self.obs, self.manifest)['missing']), 2)

    def test_unknown_history_is_blocked(self):
        self.obs['ledgerRecords'][0]['migrationId'] = 'unknown'
        with self.assertRaisesRegex(RuntimeBlocked, 'Unknown target migration'):
            audit_ledger(self.obs, self.manifest)

    def test_any_failed_or_running_record_blocks_even_with_later_applied(self):
        for status in ('FAILED', 'RUNNING', 'UNKNOWN'):
            with self.subTest(status=status):
                obs = {'ledgerRecords': [dict(self.a, status=status), dict(self.a, status='APPLIED')]}
                with self.assertRaisesRegex(RuntimeBlocked, 'Unresolved target migration'):
                    audit_ledger(obs, self.manifest)

    def test_checksum_conflict_is_not_silently_rebaselined(self):
        self.obs['ledgerRecords'][0]['sha256'] = 'c' * 64
        with self.assertRaisesRegex(RuntimeBlocked, 'checksum conflict'):
            audit_ledger(self.obs, self.manifest)

    def test_explicit_initial_history_can_preserve_removed_immutable_file(self):
        historical = {'migrationId': '20260901_retired', 'sha256': 'c' * 64, 'status': 'APPLIED'}
        self.manifest['initialBaseline'] = {'ledgerRecords': [historical]}
        self.obs['ledgerRecords'].append(historical)
        self.assertIn(historical['migrationId'], audit_ledger(self.obs, self.manifest)['applied'])

    def test_same_named_source_cannot_override_initial_history(self):
        self.manifest['initialBaseline'] = {'ledgerRecords': [dict(self.a, sha256='c' * 64, status='APPLIED')]}
        with self.assertRaisesRegex(RuntimeBlocked, 'Conflicting manifest migration identity'):
            audit_ledger(self.obs, self.manifest)

    def test_duplicate_manifest_id_is_blocked(self):
        self.manifest['migrations'].append(copy.deepcopy(self.a))
        with self.assertRaisesRegex(RuntimeBlocked, 'Duplicate manifest'):
            audit_ledger(self.obs, self.manifest)

    def test_missing_observation_is_not_success(self):
        with self.assertRaises(RuntimeBlocked):
            audit_ledger({}, self.manifest)

    def test_unregistered_host_is_never_inferred(self):
        runtime = Runtime({'targets': {}})
        with self.assertRaisesRegex(RuntimeBlocked, 'Unregistered'):
            runtime.observe('prod')


class MigrationSessionTest(unittest.TestCase):
    def test_only_explicit_two_migrations_can_use_the_reviewed_profile(self):
        for mid in ['20261009_system_workbench_visibility_context','20261009_system_workbench_visibility_stable_keys']:
            migration = dict(migrationId=mid, sessionProfile='workbench-s3-maintenance')
            with self.assertRaisesRegex(RuntimeBlocked, 'stopped writers'):
                migration_execution_sql(migration, 'SELECT @profile_workbench_s3_maintenance;')
            self.assertEqual(migration_execution_sql(migration, 'SELECT 1;', True),
                             'SET @profile_workbench_s3_maintenance=1;\nSELECT 1;')
            with self.assertRaises(RuntimeBlocked):
                validate_migration_handler(dict(migrationId=mid))
        for migration in [dict(migrationId='other', sessionProfile='workbench-s3-maintenance'),
                          dict(migrationId='other', approvedHook='arbitrary'),
                          dict(migrationId='other', sessionProfile='unknown')]:
            with self.assertRaises(RuntimeBlocked):
                validate_migration_handler(migration)

    def test_normal_migrations_never_receive_the_maintenance_variable(self):
        self.assertEqual(migration_execution_sql(dict(migrationId='normal'), 'SELECT 1;'), 'SELECT 1;')


class PackageBindingTest(unittest.TestCase):
    def test_only_explicit_job_evidence_is_outside_package_identity(self):
        manifest = {'releaseTag': '2026-10-21-20-00-00', 'images': {'backend': {'id': 'sha256:a'}}}
        injected = dict(manifest, baselines={'prod': {}}, executionPlans={'prod': {}}, expectedSchemaSha256='b' * 64)
        self.assertEqual(package_identity(manifest), package_identity(injected))
        injected['images'] = {'backend': {'id': 'sha256:changed'}}
        self.assertNotEqual(package_identity(manifest), package_identity(injected))

    def test_unknown_manifest_fields_remain_bound(self):
        self.assertNotEqual(package_identity({'releaseTag': 'a'}), package_identity({'releaseTag': 'a', 'unexpected': True}))


class ReleaseStateTest(unittest.TestCase):
    def test_direct_test_requires_no_rehearsal_but_formal_targets_do(self):
        from intruoyi_runtime import validate_expected_schema
        for environment in ('test', 'rehearsal'):
            validate_expected_schema(environment, None)
        for environment in ('prod', 'backup'):
            with self.assertRaises(RuntimeBlocked):
                validate_expected_schema(environment, None)
            validate_expected_schema(environment, 'a' * 64)
        for environment in ('test', 'prod', 'backup', 'rehearsal'):
            with self.assertRaises(RuntimeBlocked):
                validate_expected_schema(environment, 'invalid')

    def test_normal_mode_accepts_legitimately_absent_consumers(self):
        validate_release_state({'status': 'available', 'releaseTag': 'tag', 'maintenance': False,
                                'schedulingDisabled': False, 'consumersDisabled': True}, 'tag', False)

    def test_unavailable_attestation_blocks_even_with_correct_tag(self):
        with self.assertRaisesRegex(RuntimeBlocked, 'not available'):
            validate_release_state({'status': 'unavailable', 'releaseTag': 'tag', 'maintenance': False}, 'tag', False)

    def test_maintenance_requires_both_actual_writer_controls(self):
        for field in ('schedulingDisabled', 'consumersDisabled'):
            state = {'status': 'available', 'releaseTag': 'tag', 'maintenance': True,
                     'schedulingDisabled': True, 'consumersDisabled': True}
            state[field] = False
            with self.assertRaisesRegex(RuntimeBlocked, 'not disabled'):
                validate_release_state(state, 'tag', True)


class StorageAndRehearsalBindingTest(unittest.TestCase):
    def test_production_only_rehearsal_needs_no_unused_origin_roots(self):
        from intruoyi_runtime import rehearsal_profile
        config = dict(rehearsalStagingRoots={'prod': '/copy/prod'}, targets={
            'test': dict(host='58', stagingRoot='/live/test'),
            'rehearsal': dict(host='58', stagingRoot='/old')})
        self.assertEqual(rehearsal_profile(config, 'prod')['stagingRoot'], '/copy/prod')
        for source in ('test', 'backup'):
            with self.assertRaises(RuntimeBlocked):
                rehearsal_profile(config, source)

    def test_storage_budget_blocks_before_write_when_missing_or_insufficient(self):
        from intruoyi_runtime import validate_storage_budget
        for minimum in (None,False,0,-1):
            with self.assertRaises(RuntimeBlocked):
                validate_storage_budget({'minimumStagingFreeBytes':minimum},100)
        with self.assertRaisesRegex(RuntimeBlocked,'before stopping writers'):
            validate_storage_budget({'minimumStagingFreeBytes':100},99)
        validate_storage_budget({'minimumStagingFreeBytes':100},100)

    def test_explicit_backup_choice_binds_its_own_namespace_without_changing_other_targets(self):
        from intruoyi_runtime import rehearsal_profile
        config=dict(rehearsalStagingRoots={'prod':'/data/rehearsal/prod','backup':'/data/rehearsal/backup'},
                    targets={'test':dict(host='58',stagingRoot='/data/test'),
                             'rehearsal':dict(host='58',stagingRoot='/old',sourceEnvironment='prod')})
        before=copy.deepcopy(config)
        selected=rehearsal_profile(config,'backup')
        self.assertEqual(selected['sourceEnvironment'],'backup')
        self.assertEqual(selected['stagingRoot'],'/data/rehearsal/backup')
        self.assertEqual(config,before)
        for source in (None,'test'):
            with self.assertRaises(RuntimeBlocked): rehearsal_profile(config,source)
        config['rehearsalStagingRoots']['backup']='/data/test'
        with self.assertRaisesRegex(RuntimeBlocked,'conflicts'):
            rehearsal_profile(config,'backup')


class QuiescenceRecoveryTest(unittest.TestCase):
    def test_only_matching_task_origin_and_original_containers_can_close_no_sql_failure(self):
        from intruoyi_runtime import validate_quiescence_recovery
        record = dict(recoveryKind='no-migrations-started', restored=True, snapshotComplete=False,
                      jobId='job', restoredFingerprint='origin', originalContainerIds={r:r for r in ('backend','frontend','database')})
        payload = dict(jobId='job', originFingerprint='origin')
        observation = dict(fingerprint='origin', components={r:dict(containerId=r) for r in ('backend','frontend','database')})
        validate_quiescence_recovery(record,payload,observation)
        for bad in [dict(record, jobId='other'),dict(record,snapshotComplete=True),dict(record,restored=False),
                    dict(record,restoredFingerprint='changed'),dict(record,originalContainerIds={})]:
            with self.assertRaises(RuntimeBlocked):
                validate_quiescence_recovery(bad,payload,observation)
        changed=copy.deepcopy(observation)
        changed['components']['database']['containerId']='replaced'
        with self.assertRaises(RuntimeBlocked):
            validate_quiescence_recovery(record,payload,changed)


class RuntimeConfigIdentityTest(unittest.TestCase):
    def setUp(self):
        self.info = {'Config': {'Env': ['MODE=prod']}, 'HostConfig': {'NetworkMode': 'application'},
                     'Mounts': [{'Destination': '/data', 'Source': '/srv/data', 'Type': 'bind', 'RW': True},
                                {'Destination': '/config', 'Source': '/srv/config', 'Type': 'bind', 'RW': False}],
                     'NetworkSettings': {'Networks': {'application': {}, 'operations': {}}}}

    def test_docker_mount_observation_order_does_not_change_fingerprint(self):
        reordered = copy.deepcopy(self.info)
        reordered['Mounts'].reverse()
        reordered['NetworkSettings']['Networks'] = {'operations': {}, 'application': {}}
        self.assertEqual(sha(runtime_config_snapshot(self.info)), sha(runtime_config_snapshot(reordered)))
        self.assertEqual(self.info['Mounts'][0]['Destination'], '/data')

    def test_mount_content_changes_remain_bound_to_fingerprint(self):
        for field, value in [('Destination', '/other'), ('Source', '/srv/other'),
                             ('Type', 'volume'), ('RW', False), ('Propagation', 'rshared')]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.info)
                changed['Mounts'][0][field] = value
                self.assertNotEqual(sha(runtime_config_snapshot(self.info)), sha(runtime_config_snapshot(changed)))


class InterruptedRuntimeTest(unittest.TestCase):
    def test_deployment_journal_preserves_job_binding_and_refuses_replay(self):
        from intruoyi_runtime_agent import deployment_progress
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / '2026-10-22-12-00-00'
            root.mkdir()
            self.enterContext(patch('intruoyi_runtime_agent.directory', return_value=root))
            profile = dict(stagingRoot=folder)
            payload = dict(jobId='JOB-1234567890', manifest={'releaseTag': root.name})
            with patch('intruoyi_rehearsal_agent.process_start_identity', return_value='boot:start'):
                deployment_progress(profile, payload, 'running')
                with self.assertRaises(FileExistsError):
                    deployment_progress(profile, payload, 'running')
                with self.assertRaisesRegex(RuntimeBlocked, 'another execution'):
                    deployment_progress(profile, dict(payload, jobId='JOB-abcdef1234'), 'failed')
                deployment_progress(profile, payload, 'failed')
            record = json.loads((root / 'deployment-progress.private.json').read_text())
            self.assertEqual((record['jobId'], record['phase']), ('JOB-1234567890', 'failed'))

    def test_disposable_rehearsal_requires_retained_evidence_and_quiet_database(self):
        from intruoyi_runtime_agent import verify_deployment_stopped
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / '2026-10-22-12-00-00'
            root.mkdir()
            self.enterContext(patch('intruoyi_runtime_agent.directory', return_value=root))
            profile = dict(stagingRoot=folder, environment='rehearsal')
            payload = dict(jobId='JOB-1234567890', releaseTag=root.name, profile=profile)
            with self.assertRaisesRegex(RuntimeBlocked, 'recovery evidence'):
                verify_deployment_stopped(profile, payload)
            for name in ('stage-verified.json', 'recovery-record.private.json'):
                (root / name).write_text('{}')
            with patch('intruoyi_rehearsal_agent.dispatch', return_value={'stopped': True}), \
                    patch('intruoyi_runtime_agent.remote.sql', side_effect=['1']):
                with self.assertRaisesRegex(RuntimeBlocked, 'Active database statements'):
                    verify_deployment_stopped(profile, payload)
            with patch('intruoyi_rehearsal_agent.dispatch', return_value={'stopped': True}), \
                    patch('intruoyi_runtime_agent.remote.sql', side_effect=['0', '1']):
                with self.assertRaisesRegex(RuntimeBlocked, 'Active database transactions'):
                    verify_deployment_stopped(profile, payload)
            with self.assertRaisesRegex(RuntimeBlocked, 'restricted to isolated'):
                verify_deployment_stopped(dict(profile, environment='prod'), payload)

    def test_restart_marks_only_running_job_and_its_outcome_interrupted(self):
        from executor import Executor
        with tempfile.TemporaryDirectory() as folder:
            old = dict(id='old', status='failed', resolution={'recoveryEvidence': {'verified': True}})
            active = dict(id='active', status='running', effectsStarted=True)
            state = dict(jobs=[active, old], packages=[dict(outcomes={'test': {
                'deployment': dict(jobId='active', status='running'),
                'acceptance': dict(jobId='prior', status='passed')}})], environments={})
            path = Path(folder) / 'state.json'
            path.write_text(json.dumps(state), encoding='utf-8')
            migrate(folder)
            executor = Executor(dict(stateDir=folder, applicationId='test-app', mysqlImage='mysql:8.0.39'))
            try:
                saved = StateStore(folder).load()
                self.assertEqual(saved['jobs'][0]['status'], 'interrupted')
                self.assertTrue(saved['jobs'][0]['effectsStarted'])
                self.assertEqual(saved['jobs'][1], old)
                self.assertEqual(saved['packages'][0]['outcomes']['test']['deployment']['status'], 'interrupted')
                self.assertEqual(saved['packages'][0]['outcomes']['test']['acceptance']['status'], 'passed')
            finally:
                executor.process_lock.close()

    def test_disconnected_mutations_never_report_definite_remote_failure(self):
        from intruoyi_runtime import RuntimeUncertain
        runtime = Runtime({'targets': {'test': dict(host='example.invalid', python='/usr/bin/python3',
                           entryUrl='http://example.invalid', frontend='front', backend='back', database='db')}})
        for action in ('deploy', 'maintenance', 'rehearsal-capture', 'rehearsal-restore', 'rehearsal-reset'):
            for effect in (subprocess.TimeoutExpired('ssh', 1),
                           subprocess.CompletedProcess('ssh', 255, b'', b''),
                           subprocess.CompletedProcess('ssh', 0, b'incomplete', b''),
                           subprocess.CompletedProcess('ssh', 0, b'{"ok":true}', b''),
                           subprocess.CompletedProcess('ssh', 0, b'[]', b'')):
                options = {'side_effect': effect} if isinstance(effect, Exception) else {'return_value': effect}
                with self.subTest(action=action, effect=type(effect).__name__), patch('intruoyi_runtime.subprocess.run', **options):
                    with self.assertRaises(RuntimeUncertain):
                        runtime.call('test', action)
        with patch('intruoyi_runtime.subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 1)):
            with self.assertRaises(RuntimeBlocked) as failure:
                runtime.observe('test')
            self.assertNotIsInstance(failure.exception, RuntimeUncertain)




class TargetRehearsalAuthorizationTest(unittest.TestCase):
    def test_evidence_is_bound_to_target_package_and_current_origin(self):
        from intruoyi_executor import passed_rehearsal_schema
        record = dict(source='test', status='passed', originFingerprint='origin',
                      packageSha256='package', upgradedSchemaSha256='schema')
        package = dict(packageSha256='package', rehearsals=[record])
        self.assertEqual(passed_rehearsal_schema(package, 'test', 'origin'), 'schema')
        for target, origin in [('prod', 'origin'), ('backup', 'origin'), ('test', 'changed')]:
            with self.subTest(target=target, origin=origin), self.assertRaises(ValueError):
                passed_rehearsal_schema(package, target, origin)
        for field, value in [('status', 'upgraded'), ('status', 'failed'), ('packageSha256', 'other'),
                             ('upgradedSchemaSha256', None)]:
            changed = dict(record, **{field:value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                passed_rehearsal_schema(dict(packageSha256='package', rehearsals=[changed]), 'test', 'origin')

    def test_test_copy_has_an_explicit_separate_directory(self):
        from intruoyi_runtime import rehearsal_profile
        config = dict(rehearsalStagingRoots={'test':'/copy/test', 'prod':'/copy/prod', 'backup':'/copy/backup'},
                      targets={'test':dict(host='58', stagingRoot='/live/test'),
                               'rehearsal':dict(host='58', stagingRoot='/copy/old')})
        profile = rehearsal_profile(config, 'test')
        self.assertEqual(profile['sourceEnvironment'], 'test')
        self.assertEqual(profile['stagingRoot'], '/copy/test')
        config['rehearsalStagingRoots']['test']='/copy/prod'
        with self.assertRaises(RuntimeBlocked): rehearsal_profile(config, 'test')
        config['rehearsalStagingRoots']['test']='/live/test'
        with self.assertRaises(RuntimeBlocked): rehearsal_profile(config, 'test')

if __name__ == '__main__':
    unittest.main()
