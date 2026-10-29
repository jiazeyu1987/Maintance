"""Pure archive/history contracts; these tests do not claim a remote deployment."""
import hashlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from intruoyi_build import archive_image_identities, build, copy_original_package, frontend_dependency_store, historical_integrity, historical_package_integrity, install_frontend, target_input_plan
from intruoyi_executor import IntRuoyiExecutor, validate_origin, validate_restored_origin
from intruoyi_runtime_agent import migration_plan
from intruoyi_runtime import RuntimeBlocked
from executor import digest


@unittest.skipUnless(os.name == 'nt', 'Windows build command integration')
class DependencyCommandTests(unittest.TestCase):
    def run_command(self, exit_code):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = root/'dependency-install.cmd'
            command.write_text('@echo off\necho %*\necho Progress: resolved 3, reused 3, downloaded 0, added 3\necho private diagnostic marker\nexit /b '+str(exit_code)+'\n')
            messages = []
            executor = SimpleNamespace(root=root, log=lambda job, message:messages.append(message))
            job = {'id':'JOB-command-contract'}
            if exit_code:
                with self.assertRaisesRegex(ValueError, r'installation failed \(7\)'):
                    install_frontend(executor, job, str(command), root)
            else:
                install_frontend(executor, job, str(command), root)
            self.assertTrue(any('resolved 3, reused 3' in message for message in messages))
            self.assertFalse(any('private diagnostic marker' in message for message in messages))
            diagnostic = (root/'build-logs/JOB-command-contract-pnpm.private.log').read_text()
            self.assertIn('private diagnostic marker', diagnostic)
            self.assertIn('--frozen-lockfile', diagnostic)
            self.assertIn('--package-import-method=hardlink', diagnostic)
            self.assertIn('--verify-store-integrity=true', diagnostic)
            self.assertIn(str(root/'pnpm-store'), diagnostic)
            self.assertEqual(any('completed in' in message for message in messages), not exit_code)

    def test_actual_command_success_reports_counts_without_raw_diagnostics(self):
        self.run_command(0)

    def test_actual_command_failure_cannot_be_reported_as_success(self):
        self.run_command(7)


class DependencyStoreTests(unittest.TestCase):
    def test_real_hardlink_probe_leaves_source_and_existing_store_content_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frontend = root/'frontend'
            frontend.mkdir()
            (frontend/'pnpm-lock.yaml').write_text('immutable-lock')
            store = root/'pnpm-store'
            store.mkdir()
            (store/'existing').write_bytes(b'cached-dependency')
            self.assertEqual(frontend_dependency_store(SimpleNamespace(root=root), frontend), store)
            self.assertEqual([p.name for p in frontend.iterdir()], ['pnpm-lock.yaml'])
            self.assertEqual([p.name for p in store.iterdir()], ['existing'])
            self.assertEqual((store/'existing').read_bytes(), b'cached-dependency')

    def test_failed_hardlink_is_reported_without_copy_or_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('intruoyi_build.os.link', side_effect=OSError('cross-device link')), \
                    patch('intruoyi_build.subprocess.Popen') as process, \
                    self.assertRaisesRegex(ValueError, 'same local volume'):
                install_frontend(SimpleNamespace(root=root), {'id':'JOB-no-link'}, 'pnpm', root)
            process.assert_not_called()
            self.assertFalse((root/'build-logs').exists())


class BuildRegistrationTests(unittest.TestCase):
    """Exercise the actual build preamble; stop before any storage/build effects."""
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[3]
        self.commit = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD']).decode().strip()
        self.config = {'repo': str(self.repo), 'gxpConfigurationSourceUrl': 'http://source.invalid', 'rehearsalStagingRoots': {'prod':'/rehearsal/prod'},
                       'buildWorktreeRoot': str(self.repo), 'localBuildSpaceBytes': dict(worktree=1, package=1, state=1),
                       'targets': {'rehearsal': {'host':'isolated', 'stagingRoot':'/rehearsal'},
                                   'test': {'host':'test', 'stagingRoot':'/release'},
                                   'prod': {'host':'prod', 'stagingRoot':'/release'},
                                   'backup': {'host':'backup', 'stagingRoot':'/release'}}}
        self.environments = {env: {'baselineStatus':'registered'} for env in ('test', 'prod', 'backup')}

    def run_preamble(self):
        steps = []
        def stop_before_effects(job, name):
            steps.append(name)
            if name == 'authenticate-package-storage':
                raise InterruptedError('registration passed; no build attempted')
        executor = SimpleNamespace(c=self.config, root=self.repo, save=lambda:None, state={'environments':self.environments},
                                   run=subprocess.check_output, step=stop_before_effects)
        with patch('intruoyi_build.verify_login', return_value={'gxpAuditMode':'DEVELOPMENT_DISABLED'}):
            build(executor, {'id':'unit-build', 'payload':{'commit':self.commit}})

    def test_only_production_rehearsal_registration_is_required(self):
        with self.assertRaisesRegex(InterruptedError, 'registration passed'):
            self.run_preamble()

    def test_missing_production_rehearsal_still_blocks_before_storage(self):
        self.config['rehearsalStagingRoots'] = {'test':'/rehearsal/test', 'backup':'/rehearsal/backup'}
        with self.assertRaises(RuntimeBlocked):
            self.run_preamble()

    def test_insufficient_local_storage_stops_before_nas_or_build(self):
        self.config['localBuildSpaceBytes']['worktree'] = 2**63
        with self.assertRaisesRegex(ValueError, 'Local build storage insufficient'):
            self.run_preamble()

    def test_each_real_target_baseline_remains_required(self):
        for env in ('test', 'prod', 'backup'):
            with self.subTest(environment=env):
                self.environments[env]['baselineStatus'] = 'unregistered'
                with self.assertRaisesRegex(ValueError, 'three-server baselines'):
                    self.run_preamble()
                self.environments[env]['baselineStatus'] = 'registered'


class ArchiveContractTests(unittest.TestCase):
    def test_archive_config_bytes_define_classic_remote_identity(self):
        config = b'{"rootfs":{"type":"layers","diff_ids":[]}}'
        expected = 'sha256:'+hashlib.sha256(config).hexdigest()
        image = {'name':'intruoyi-backend:2026-10-21-01-00-00','id':'sha256:'+'a'*64}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'images.tar'
            with tarfile.open(path, 'w') as archive:
                for name, content in [('manifest.json',json.dumps([dict(Config='config.json',RepoTags=[image['name']])]).encode()),('config.json',config)]:
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            archive_image_identities(path, {'backend':image})
        self.assertEqual(image['id'], expected)
        self.assertEqual(image['localImageId'], 'sha256:'+'a'*64)

    def test_missing_archive_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'images.tar'
            with tarfile.open(path, 'w'):
                pass
            with self.assertRaises((ValueError,KeyError)):
                archive_image_identities(path, {'backend':{'name':'unknown','id':'local'}})

    def test_exact_archive_is_copied_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'package'
            folder.mkdir()
            (folder/'release.tar').write_bytes(b'original sealed archive')
            (folder/'manifest.json').write_text('{}')
            manifest = {'releaseTag':'2026-10-21-01-00-00'}
            destination = Path(copy_original_package(folder, manifest, root/'storage'))
            self.assertEqual(digest(folder/'release.tar'), digest(destination/'release.tar'))
            with self.assertRaises(FileExistsError):
                copy_original_package(folder, manifest, root/'storage')


class HistoryContractTests(unittest.TestCase):
    def test_sealed_rollback_bytes_can_be_archived_but_not_adopted_as_applied(self):
        identity = '20260817_mes_pqc_item_level_task_identity_rollback'
        row = dict(migrationId=identity, sha256='a'*64)
        reference = dict(file=identity+'.sql', sha256=row['sha256'], kind='rollback-only')
        previous = dict(migrations=[row])
        before = copy.deepcopy(previous)
        historical_package_integrity([], [reference], previous)
        self.assertEqual(previous, before)
        with self.assertRaisesRegex(ValueError, 'source missing'):
            historical_integrity([], [dict(row, status='APPLIED')])
        with self.assertRaisesRegex(ValueError, 'checksum changed'):
            historical_package_integrity([], [dict(reference, sha256='b'*64)], previous)
        with self.assertRaisesRegex(ValueError, 'source missing'):
            historical_package_integrity([], [], previous)

    def test_general_reference_cannot_hide_missing_forward_migration(self):
        row = dict(migrationId='20260817_forward_schema', sha256='a'*64)
        for kind in ('replacement', 'review-only'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'source missing'):
                historical_package_integrity([], [dict(file=row['migrationId']+'.sql',
                    sha256=row['sha256'], kind=kind)], dict(migrations=[row]))
        with self.assertRaisesRegex(ValueError, 'rollback-only archive identity'):
            historical_package_integrity([], [dict(file=row['migrationId']+'.sql',
                sha256=row['sha256'], kind='rollback-only')], dict(migrations=[row]))

    def test_archived_rollback_remains_protected_in_subsequent_candidates(self):
        reference = dict(file='20260817_item_identity_rollback.sql', sha256='a'*64, kind='rollback-only')
        previous = dict(migrations=[], sourceReferences=[reference])
        historical_package_integrity([], [reference], previous)
        with self.assertRaisesRegex(ValueError, 'source missing'):
            historical_package_integrity([], [], previous)
        with self.assertRaisesRegex(ValueError, 'checksum changed'):
            historical_package_integrity([], [dict(reference, sha256='b'*64)], previous)

    def test_restored_failure_requires_exact_healthy_original_origin(self):
        observation = dict(fingerprint='a'*64, schemaSha256='b'*64, releaseTag='original', ledgerRecords=[],
                           images={'backend':'sha256:'+'c'*64, 'frontend':'sha256:'+'d'*64},
                           backendHealth={'status':'UP'}, frontendHttpStatus=200, maintenance=False,
                           readOnly={'read_only':False, 'super_read_only':False})
        original = dict(effectsStarted=True, action='publish-test', originFingerprint='a'*64,
                        originState={'releaseTag':'original'})
        validate_restored_origin(original, observation)
        for change in (dict(fingerprint='e'*64), dict(backendHealth={'status':'DOWN'}),
                       dict(frontendHttpStatus=503), dict(maintenance=True), dict(readOnly={}),
                       dict(releaseTag='candidate')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_restored_origin(original, dict(copy.deepcopy(observation), **change))
        with self.assertRaisesRegex(ValueError, 'acceptance cannot be abandoned'):
            validate_restored_origin(dict(original, action='reject-acceptance'), observation)

    def test_low_risk_seed_preflight_survives_planning_and_remote_validation(self):
        check = dict(reference='sql/mysql/target-preflight/seed.preflight.sql', sha256='b'*64, readOnly=True)
        migration = dict(migrationId='seed', sha256='a'*64, file='sql/mysql/seed.sql', type='seed',
                         allowedEnvironments=['test'], dependsOn=[], requiresTargetPreflight=False,
                         targetPreflight=check)
        plan = target_input_plan([migration], [], 'test')
        manifest = dict(migrations=[migration], publishScope='app-release', executionPlans={'test':plan})
        self.assertEqual(migration_plan({'environment':'test'}, manifest, {'ledgerRecords':[]})[0]['targetPreflight'], check)
        plan['items'][0]['targetPreflight']['sha256'] = 'c'*64
        self.assertEqual(migration['targetPreflight']['sha256'], 'b'*64)
        with self.assertRaisesRegex(RuntimeBlocked, 'differs from immutable manifest'):
            migration_plan({'environment':'test'}, manifest, {'ledgerRecords':[]})

    def test_pending_data_requires_check_but_applied_data_is_not_replayed(self):
        migration = dict(migrationId='data', sha256='a'*64, type='data', allowedEnvironments=['test','prod','backup'], dependsOn=[])
        with self.assertRaisesRegex(ValueError, 'required target preflight missing'):
            target_input_plan([migration], [], 'test')
        plan = target_input_plan([migration], [dict(migrationId='data', sha256='a'*64, status='SKIPPED_ALREADY_APPLIED')], 'test')
        self.assertEqual(plan['items'][0]['action'], 'SKIP_ALREADY_APPLIED')
        plan = target_input_plan([dict(migration, targetPreflight={'reference':'checked.sql'})], [], 'test')
        self.assertEqual(plan['items'][0]['action'], 'APPLY')

    def test_environment_exclusion_does_not_require_irrelevant_check(self):
        migration = dict(migrationId='data', sha256='a'*64, type='data', allowedEnvironments=['test'], dependsOn=[])
        plan = target_input_plan([migration], [], 'prod')
        self.assertEqual(plan['items'][0]['action'], 'SKIP_ENV_NOT_ALLOWED')

    def test_missing_version_metadata_is_never_replaced_with_a_made_up_tag(self):
        value = dict(schemaSha256='a'*64,fingerprint='b'*64,ledgerRecords=[],
                     backendHealth={'status':'UP'},frontendHttpStatus=200,
                     images={'backend':'sha256:'+'c'*64,'frontend':'sha256:'+'d'*64},releaseTag=None)
        with self.assertRaisesRegex(ValueError,'version identity is missing'):
            validate_origin(value)
        self.assertIsNone(value['releaseTag'])
        self.assertNotIn('baselineId', value)
        value['releaseTag'] = 'proved-historical-version'
        validate_origin(value)

    def test_same_identity_requires_original_bytes(self):
        history = [dict(migrationId='old',sha256='a'*64,status='APPLIED')]
        historical_integrity([dict(migrationId='old',sha256='a'*64)], history)
        with self.assertRaisesRegex(ValueError,'checksum changed'):
            historical_integrity([dict(migrationId='old',sha256='b'*64)], history)
        with self.assertRaisesRegex(ValueError,'source missing'):
            historical_integrity([], history)

    def test_failed_history_is_never_adopted(self):
        with self.assertRaisesRegex(ValueError,'Unresolved baseline'):
            historical_integrity([dict(migrationId='old',sha256='a'*64)],
                                 [dict(migrationId='old',sha256='a'*64,status='FAILED')])

    def test_runtime_baseline_is_target_specific_and_does_not_mutate_package(self):
        executor = IntRuoyiExecutor.__new__(IntRuoyiExecutor)
        executor.state = {'environments':{'test':{'releaseTag':'current','schemaSha256':'a'*64}}}
        manifest = {'releaseTag':'candidate'}
        runtime = executor.runtime_manifest('test', manifest)
        self.assertEqual(runtime['baselines']['test']['releaseTag'], 'current')
        self.assertNotIn('baselines', manifest)
        runtime['baselines']['test']['releaseTag'] = 'mutated'
        self.assertEqual(executor.state['environments']['test']['releaseTag'], 'current')
        with self.assertRaisesRegex(ValueError,'Current registered'):
            executor.runtime_manifest('backup', manifest)


if __name__ == '__main__':
    unittest.main()
