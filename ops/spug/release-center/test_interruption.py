"""State-machine unit boundaries; real-process journal tests live in the lab."""
import copy
import threading
import unittest
from unittest.mock import Mock, patch

from backup_retry import bind_attempt_roots, validate_retry
from interruption import inspect, reconcile, execute

TAG = '2026-10-24-12-00-00'
JOB = 'JOB-1111111111'
OP = 'OP-' + 'a' * 20


class InterruptionTests(unittest.TestCase):
    def setUp(self):
        self.job = dict(id=JOB, action='promote-backup', target='backup', releaseTag=TAG,
                        status='interrupted', effectsStarted=True, payload={},
                        remoteOperations=[dict(operationId=OP, env='backup', action='deploy')])
        self.receipt = dict(operationId=OP, jobId=JOB, status='succeeded', worker='stopped', result={})
        self.executor = Mock()
        self.executor.state = dict(jobs=[self.job], environments={}, packages=[])
        self.executor.runtime.call.return_value = self.receipt
        self.executor.runtime.observe.return_value = dict(releaseTag=TAG)
        self.worker = dict(id='JOB-2222222222', action='reconcile-interruption', actor='operator',
                           payload=dict(note='核对原任务后继续'), logs=[])

    def test_still_running_does_not_observe_or_reconcile(self):
        self.receipt.update(worker='running', status='running')
        result = inspect(self.executor, self.job)
        self.assertEqual(result['disposition'], 'still-running')
        self.executor.runtime.observe.assert_not_called()
        with self.assertRaises(ValueError): reconcile(self.executor, self.job, result, self.worker)
        self.executor.verify_technical.assert_not_called()

    def test_missing_or_dead_incomplete_receipt_never_means_failed_or_safe(self):
        for worker, status in [('unknown', 'unknown'), ('stopped', 'running')]:
            self.receipt.update(worker=worker, status=status)
            self.assertEqual(inspect(self.executor, self.job)['disposition'], 'unknown')
        self.assertNotIn('resolution', self.job)

    def test_receipt_from_different_task_rejected(self):
        self.receipt['jobId'] = 'JOB-3333333333'
        with self.assertRaisesRegex(ValueError, 'binding'):
            inspect(self.executor, self.job)

    def test_partial_migration_requires_recovery(self):
        self.receipt['status'] = 'failed'
        result = inspect(self.executor, self.job)
        self.assertEqual(result['disposition'], 'recovery-required')
        with self.assertRaises(ValueError): reconcile(self.executor, self.job, result, self.worker)

    def test_completed_deployment_lost_reply_requires_checks_not_redeploy(self):
        result = inspect(self.executor, self.job)
        self.assertEqual(result['disposition'], 'verify-deployment')
        self.executor.deploy.assert_not_called()

    def test_opening_lost_reply_not_automatic_acceptance(self):
        self.job['action'] = 'accept-backup'
        self.job['remoteOperations'][0]['action'] = 'maintenance'
        result = inspect(self.executor, self.job)
        self.assertEqual(result['disposition'], 'verify-opening')
        self.executor.verify_technical.assert_not_called()
        self.assertNotIn('resolution', self.job)

    def test_legacy_side_effects_remain_explicitly_unverified(self):
        self.job['remoteOperations'] = []
        self.assertEqual(inspect(self.executor, self.job)['disposition'], 'legacy-evidence-required')

    def test_pre_effect_failure_closes_only_unchanged_origin(self):
        self.job.update(effectsStarted=False, originFingerprint='before', remoteOperations=[])
        self.executor.runtime.observe.return_value = dict(fingerprint='after')
        result = inspect(self.executor, self.job)
        self.assertEqual(result['disposition'], 'close-pre-effect')
        with self.assertRaisesRegex(ValueError, 'unchanged'):
            reconcile(self.executor, self.job, result, self.worker)
        result['observation']['fingerprint'] = 'before'
        reconcile(self.executor, self.job, result, self.worker)
        self.assertEqual(self.job['status'], 'interrupted')
        self.assertEqual(self.job['resolution']['disposition'], 'close-pre-effect')

    def test_build_requires_process_inventory(self):
        self.job.update(action='build-release', effectsStarted=False, remoteOperations=[])
        with self.assertRaisesRegex(ValueError, 'process inventory'):
            inspect(self.executor, self.job)
        self.job['localProcessTracking'] = True
        self.assertEqual(inspect(self.executor, self.job)['disposition'], 'close-build')

    def test_incomplete_preparation_reads_original_receipts_without_observing_missing_containers(self):
        self.job.update(action='prepare-rehearsal', target='rehearsal', sourceEnv='prod')
        self.job['remoteOperations'][0].update(env='rehearsal', action='rehearsal-create-stage')
        self.executor.runtime.targets={}
        with patch('intruoyi_runtime.rehearsal_profile', return_value={'stagingRoot':'/registered/prod'}) as profile:
            result=inspect(self.executor,self.job)
        profile.assert_called_once_with(self.executor.c,'prod')
        self.assertEqual(self.executor.runtime.targets['rehearsal']['stagingRoot'],'/registered/prod')
        self.assertEqual(result['disposition'],'manual-review')
        self.assertIn('副本传输',result['detail'])
        self.executor.runtime.observe.assert_not_called()

    def test_readonly_status_lost_reply_does_not_hide_completed_preparation_receipts(self):
        self.job.update(action='prepare-rehearsal',target='rehearsal')
        self.job['remoteOperations'][0]['action']='rehearsal-job-status'
        self.receipt.update(status='unknown',worker='unknown')
        self.assertEqual(inspect(self.executor,self.job)['disposition'],'manual-review')
        self.executor.runtime.observe.assert_not_called()

    def test_recovery_and_clear_inspection_do_not_require_partially_removed_application(self):
        for action,operation in [('recover-release','recover-release'),('accept-recovery','accept-recovery'),
                                 ('reset-rehearsal','rehearsal-reset')]:
            with self.subTest(action=action):
                self.job['action']=action
                self.job['remoteOperations'][0]['action']=operation
                self.assertEqual(inspect(self.executor,self.job)['disposition'],'manual-review')
        self.executor.runtime.observe.assert_not_called()

    def test_failed_reconciliation_family_is_checked_too(self):
        attempt = dict(id='JOB-3333333333', originalTaskId=JOB, action='reconcile-interruption', status='interrupted',
                       remoteOperations=[dict(operationId='OP-'+'b'*20, env='backup', action='maintenance')])
        self.executor.state['jobs'].append(attempt)
        self.executor.runtime.call.side_effect = [self.receipt, dict(operationId='OP-'+'b'*20,
            jobId=attempt['id'], status='running', worker='running')]
        self.assertEqual(inspect(self.executor, self.job)['disposition'], 'still-running')

    def test_transport_failure_is_recorded_and_original_still_blocks(self):
        self.worker.update(action='inspect-interruption', originalTaskId=JOB)
        self.executor.password = 'secret'
        self.executor.runtime.call.side_effect = RuntimeError('connection lost')
        execute(self.executor, self.worker)
        self.assertEqual(self.worker['status'], 'failed')
        self.assertEqual(self.worker['resolution']['decision'], 'inspection-failed')
        self.assertNotIn('resolution', self.job)


class BackupRetryTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(id=JOB, action='promote-backup', target='backup', releaseTag=TAG,
                             status='failed', effectsStarted=False, resolution=dict(decision='reconciled'))
        self.package = dict(releaseTag=TAG, stage='prod-accepted', outcomes={'prod':{'acceptance':{'status':'passed'}}})
        self.executor = Mock()
        self.executor.c = {'targets':{'backup':{'stagingRoot':'/releases'}}}
        self.executor.state = dict(jobs=[self.original], packages=[self.package],
                                   environments={'prod':{'releaseTag':TAG, 'maintenance':False}})

    def test_pre_effect_failure_allows_independent_backup(self):
        before = copy.deepcopy(self.executor.state)
        validate_retry(self.executor, self.package, JOB)
        self.assertEqual(self.executor.state, before)

    def test_unresolved_and_partial_failure_cannot_retry(self):
        self.original.pop('resolution')
        with self.assertRaises(ValueError): validate_retry(self.executor, self.package, JOB)
        self.original.update(resolution={'decision':'reconciled'}, effectsStarted=True)
        with self.assertRaises(ValueError): validate_retry(self.executor, self.package, JOB)

    def test_restored_backup_retries_without_changing_production_records(self):
        self.original.update(effectsStarted=True, resolution={'decision':'restored'})
        self.package.update(stage='backup-restored')
        self.package['outcomes']['backup'] = {'recovery':{'status':'accepted'}}
        before = copy.deepcopy(self.executor.state)
        validate_retry(self.executor, self.package, JOB)
        self.assertEqual(self.executor.state, before)

    def test_new_production_or_pending_backup_acceptance_blocks_redeploy(self):
        self.executor.state['environments']['prod']['releaseTag'] = '2026-10-24-13-00-00'
        with self.assertRaises(ValueError): validate_retry(self.executor, self.package, JOB)
        self.executor.state['environments']['prod']['releaseTag'] = TAG
        self.package['stage'] = 'backup-deployed'
        with self.assertRaises(ValueError): validate_retry(self.executor, self.package, JOB)

    def test_retry_owns_separate_artifacts_and_recovery_inherits_root(self):
        retry = dict(id='JOB-2222222222', action='promote-backup', releaseTag=TAG, payload={'retryOf':JOB})
        bind_attempt_roots(self.executor, retry)
        self.assertEqual(retry['runtimeStagingRoots'], {'backup':'/releases/attempts/JOB-2222222222'})
        self.executor.state['jobs'].append(retry)
        recovery = dict(id='JOB-3333333333', action='recover-release', payload={'jobId':retry['id']})
        bind_attempt_roots(self.executor, recovery)
        self.assertEqual(recovery['runtimeStagingRoots'], retry['runtimeStagingRoots'])


class ReconciliationWorkflowTests(unittest.TestCase):
    def setUp(self):
        from test_technical_verification import TechnicalVerificationTest
        self.fixture=TechnicalVerificationTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture

    def lost_reply(self, original, action='deploy'):
        original.update(status='interrupted',remoteOperations=[dict(env=original['target'],action=action,operationId=OP)])
        receipt=dict(jobId=original['id'],operationId=OP,status='succeeded',worker='stopped',
                     result=copy.deepcopy(self.f.executor.state['environments'][original['target']]))
        self.f.executor.runtime.call.return_value=receipt

    def test_deploy_reconciliation_keeps_original_recovery_owner_and_closed_production(self):
        from intruoyi_recovery import original_deployment
        f=self.f;f.seed_rehearsal()
        original=f.run_action('promote-prod')
        self.assertEqual(original['status'],'succeeded',original.get('error'))
        self.lost_reply(original)
        result=f.run_action('reconcile-interruption',jobId=original['id'],note='重新核对部署完成回执')
        self.assertEqual(result['status'],'succeeded',result.get('error'))
        self.assertEqual(f.package['stage'],'prod-deployed')
        self.assertTrue(f.executor.state['environments']['prod']['maintenance'])
        self.assertEqual(f.package['outcomes']['prod']['deployment']['jobId'],original['id'])
        self.assertIs(original_deployment(f.executor,f.package,{'jobId':original['id']}),original)
        self.assertEqual(f.executor.deploy.call_count,1)
        self.assertEqual(original['status'],'interrupted')

    def test_opening_reconciliation_checks_then_records_explicit_acceptance(self):
        f=self.f;f.seed_rehearsal();f.run_action('promote-prod')
        original=f.run_action('accept-prod',note='真实业务验收通过')
        self.assertEqual(original['status'],'succeeded',original.get('error'))
        self.lost_reply(original,'maintenance')
        # The response was lost after opening; do not open it twice.
        opening_count=f.executor.maintenance.call_count
        result=f.run_action('reconcile-interruption',jobId=original['id'],note='已核对原验收开放结果')
        self.assertEqual(result['status'],'succeeded',result.get('error'))
        self.assertEqual(f.package['stage'],'prod-accepted')
        self.assertEqual(f.executor.maintenance.call_count,opening_count)
        self.assertEqual(f.executor.deploy.call_count,1)
        self.assertEqual(original['status'],'interrupted')

    def test_backup_retry_archives_backup_failure_and_preserves_production(self):
        f=self.f;f.seed_rehearsal();f.run_action('promote-prod');f.run_action('accept-prod',note='正式业务验收已通过')
        production=copy.deepcopy(f.package['outcomes']['prod'])
        environment=copy.deepcopy(f.executor.state['environments']['prod'])
        deploy=f.executor.deploy.side_effect
        f.executor.deploy.side_effect=ValueError('Before mutation prerequisite failed')
        original=f.run_action('promote-backup')
        self.assertEqual(original['status'],'failed')
        self.assertFalse(original.get('effectsStarted'))
        closed=f.run_action('reconcile-interruption',jobId=original['id'],note='核对备用失败前起点未变')
        self.assertEqual(closed['status'],'succeeded',closed.get('error'))
        f.executor.deploy.side_effect=deploy
        retried=f.run_action('promote-backup',retryOf=original['id'])
        self.assertEqual(retried['status'],'succeeded',retried.get('error'))
        self.assertEqual(f.package['stage'],'backup-deployed')
        self.assertEqual(f.package['outcomes']['prod'],production)
        self.assertEqual(f.executor.state['environments']['prod'],environment)
        self.assertEqual(f.package['backupAttemptHistory'][0]['originalJobId'],original['id'])
        self.assertEqual(original['status'],'failed')
        self.assertNotIn('acceptance',f.package['outcomes']['backup'])

    def test_partial_backup_recovery_then_retry_preserves_production_and_failure(self):
        f=self.f;f.seed_rehearsal();f.run_action('promote-prod');f.run_action('accept-prod',note='正式业务验收通过')
        production=copy.deepcopy(f.package['outcomes']['prod'])
        environment=copy.deepcopy(f.executor.state['environments']['prod'])
        deploy=f.executor.deploy.side_effect
        def partial(env, package, manifest, job):
            f.executor.step(job,'partial-backup-migration',effects=True)
            raise ValueError('Migration worker stopped after DDL')
        f.executor.deploy.side_effect=partial
        original=f.run_action('promote-backup')
        self.assertEqual(original['status'],'failed')
        self.assertTrue(original['effectsStarted'])
        self.assertEqual(f.package['stage'],'prod-accepted')
        restored=dict(observation=dict(original['originState'],maintenance=True),receipt=dict(
            originalJobId=original['id'],jobId='JOB-1234567890',phase='restored',packageSha256=f.package['packageSha256']))
        f.executor.runtime.call.return_value=restored
        recovery=f.run_action('recover-release',jobId=original['id'],note='恢复备用半执行迁移')
        self.assertEqual(recovery['status'],'succeeded',recovery.get('error'))
        with self.assertRaises(ValueError):
            f.run_action('promote-backup',retryOf=original['id'])
        def open_origin(*args,**values):
            return dict(observation=dict(original['originState'],maintenance=False),receipt=dict(
                restored['receipt'],phase='opened',openingJobId=values['jobId'],confirmedByJobId=values['jobId']))
        f.executor.runtime.call.side_effect=open_origin
        accepted=f.run_action('accept-recovery',jobId=original['id'],note='备用旧版本及数据验收通过')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        self.assertEqual(f.package['stage'],'backup-restored')
        self.assertFalse(f.package.get('abandoned'))
        f.executor.runtime.call.side_effect=None
        f.executor.deploy.side_effect=deploy
        retry=f.run_action('promote-backup',retryOf=original['id'])
        self.assertEqual(retry['status'],'succeeded',retry.get('error'))
        self.assertEqual(f.package['stage'],'backup-deployed')
        self.assertEqual(f.package['outcomes']['prod'],production)
        self.assertEqual(f.executor.state['environments']['prod'],environment)
        self.assertEqual(original['status'],'failed')
        self.assertEqual(original['resolution']['decision'],'restored')
        self.assertEqual(f.package['backupAttemptHistory'][0]['outcomes']['recovery']['status'],'accepted')
        self.assertNotIn('recovery',f.package['outcomes']['backup'])


if __name__ == '__main__': unittest.main()
