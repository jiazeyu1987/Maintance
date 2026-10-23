"""Isolated adapter contracts; these tests do not connect to deployed servers."""
import unittest
import subprocess
from unittest.mock import Mock, patch

from intruoyi_build import target_input_plan
from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime import Runtime, RuntimeBlocked, RuntimeUncertain, package_identity


class TestTailAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tag = '2026-10-23-15-17-12'
        self.migration = dict(migrationId='reviewed-schema', sha256='a'*64, type='schema',
                              allowedEnvironments=['test', 'prod', 'backup'], dependsOn=[])
        self.manifest = dict(releaseTag=self.tag, migrations=[self.migration], publishScope='app-release',
                             images={role: dict(id='sha256:'+char*64) for role, char in [('backend','b'),('frontend','c')]})
        self.original = dict(id='JOB-original', action='publish-test', target='test', status='failed',
                             releaseTag=self.tag, effectsStarted=True, error='acceptance host port unavailable',
                             originFingerprint='original-fingerprint',
                             originState=dict(releaseTag='old', ledgerRecords=[]),
                             migrationPlan=target_input_plan([self.migration], [], 'test'))
        self.job = dict(id='JOB-retry', action='resolve-task', status='running', releaseTag=self.tag,
                        actor='operator', payload=dict(jobId=self.original['id'], decision='retry', note='verified original evidence'))
        self.package = dict(releaseTag=self.tag, packageSha256='d'*64, manifestSha256='e'*64, stage='built',
                            outcomes=dict(test=dict(deployment=dict(jobId=self.original['id'],status='failed'))))
        self.observation = dict(releaseTag=self.tag, fingerprint='runtime', schemaSha256='f'*64,
                                ledgerSha256='1'*64, ledgerRecords=[dict(self.migration, status='APPLIED')],
                                images={role: image['id'] for role,image in self.manifest['images'].items()},
                                backendHealth=dict(status='UP'), frontendHttpStatus=503, maintenance=True)
        self.receipt = dict(status='completed', phase='complete', originalJobId=self.original['id'],
                            releaseTag=self.tag, packageIdentity=package_identity(self.manifest),
                            packageSha256=self.package['packageSha256'], manifestSha256=self.package['manifestSha256'],
                            completedByJobId=self.job['id'])
        self.result = dict(self.observation, frontendHttpStatus=200, maintenance=False,
                           readOnly=dict(read_only=False,super_read_only=False), resumeReceipt=self.receipt)
        self.executor = object.__new__(IntRuoyiExecutor)
        self.executor.state = dict(jobs=[self.job,self.original], packages=[self.package],
                                    environments=dict(test=dict(maintenanceUnknown=True)))
        self.executor.package = Mock(return_value=(self.package,self.manifest))
        self.executor.save = Mock()
        self.executor.log = Mock()
        self.executor.runtime = Mock()
        self.executor.runtime.observe.return_value = self.observation
        self.executor.runtime.resume_test_deployment_tail.return_value = self.result
        self.executor.verify_technical = Mock(side_effect=lambda env,package,manifest,job:package.update(stage='tested'))

    def run_retry(self):
        self.executor.resolve_task(self.job)

    def test_success_retains_failed_original_and_runs_technical_verification(self):
        self.run_retry()
        self.assertEqual(self.package['stage'], 'tested')
        self.executor.verify_technical.assert_called_once_with('test',self.package,self.manifest,self.job)
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.original['error'], 'acceptance host port unavailable')
        self.assertEqual(self.original['resolution']['decision'], 'retry')
        self.assertNotIn('acceptance', self.package['outcomes']['test'])
        self.assertEqual(self.package['outcomes']['test']['deployment']['jobId'], self.job['id'])
        args = self.executor.runtime.resume_test_deployment_tail.call_args.args
        self.assertEqual(args[:1], ('test',))
        self.assertEqual(args[1]['baselines']['test'], self.original['originState'])
        self.assertEqual(args[2], self.original['migrationPlan']['items'])
        self.assertEqual(args[3:7], (self.original['id'],self.job['id'],'d'*64,'e'*64))
        self.executor.runtime.deploy.assert_not_called()
        self.executor.runtime.stage.assert_not_called()

    def test_prod_or_backup_and_non_deployment_retries_are_rejected(self):
        for action,target in [('promote-prod','prod'),('promote-backup','backup'),('mark-tested','test')]:
            with self.subTest(action=action):
                self.original.update(action=action,target=target)
                with self.assertRaisesRegex(ValueError,'original test deployment'):
                    self.run_retry()
        self.executor.runtime.resume_test_deployment_tail.assert_not_called()

    def test_different_package_or_outcome_owner_is_rejected(self):
        self.job['releaseTag']='another'
        with self.assertRaisesRegex(ValueError,'original immutable package'):
            self.run_retry()
        self.job['releaseTag']=self.tag
        self.package['outcomes']['test']['deployment']['jobId']='JOB-another'
        with self.assertRaisesRegex(ValueError,'no longer owns'):
            self.run_retry()
        self.executor.runtime.resume_test_deployment_tail.assert_not_called()

    def test_missing_or_failed_original_apply_blocks_without_side_effects(self):
        self.observation['ledgerRecords']=[]
        with self.assertRaisesRegex(ValueError,'not all APPLIED'):
            self.run_retry()
        self.observation['ledgerRecords']=[dict(self.migration,status='FAILED')]
        with self.assertRaisesRegex(RuntimeBlocked,'Unresolved target migration'):
            self.run_retry()
        self.executor.runtime.resume_test_deployment_tail.assert_not_called()

    def test_pending_migration_and_wrong_installed_image_block(self):
        self.manifest['migrations'].append(dict(self.migration,migrationId='new-schema',sha256='9'*64))
        with self.assertRaisesRegex(ValueError,'Original full migration plan differs'):
            self.run_retry()
        self.manifest['migrations'].pop()
        self.observation['images']['backend']='sha256:'+'0'*64
        with self.assertRaisesRegex(ValueError,'original candidate'):
            self.run_retry()
        self.executor.runtime.resume_test_deployment_tail.assert_not_called()

    def test_omitted_original_apply_item_or_changed_origin_is_rejected(self):
        self.original['migrationPlan']['items'][0]['reason']='changed persisted evidence'
        with self.assertRaisesRegex(ValueError,'Original full migration plan differs'):
            self.run_retry()
        self.original['migrationPlan']=target_input_plan([self.migration], [], 'test')
        self.original['originState']['ledgerRecords']=[dict(self.migration,status='APPLIED')]
        with self.assertRaisesRegex(ValueError,'Original full migration plan differs'):
            self.run_retry()
        self.executor.runtime.resume_test_deployment_tail.assert_not_called()

    def test_bad_receipt_or_unopened_business_never_resolves_original(self):
        for changes in [dict(packageIdentity='wrong'),dict(manifestSha256='wrong'),dict(completedByJobId='JOB-unrelated'),dict(phase='opening')]:
            with self.subTest(changes=changes):
                self.result['resumeReceipt']=dict(self.receipt,**changes)
                with self.assertRaisesRegex(ValueError,'completed test continuation receipt'):
                    self.run_retry()
                self.assertNotIn('resolution',self.original)
                self.assertEqual(self.package['stage'],'built')
        self.result['resumeReceipt']=self.receipt
        self.result['maintenance']=True
        with self.assertRaisesRegex(ValueError,'open for functional verification'):
            self.run_retry()
        self.assertNotIn('resolution',self.original)

    def test_opening_failure_preserves_blocked_original(self):
        self.executor.runtime.resume_test_deployment_tail.side_effect=ValueError('opening failed; technical restoration required')
        with self.assertRaisesRegex(ValueError,'technical restoration'):
            self.run_retry()
        self.assertNotIn('resolution',self.original)
        self.assertEqual(self.package['stage'],'built')

    def add_failed_retry(self):
        attempt = dict(id='JOB-prior-retry', action='resolve-task', status='interrupted',target='test',
                       releaseTag=self.tag, originalDeploymentJobId=self.original['id'],effectsStarted=True,
                       payload=dict(decision='retry'), error='SSH response lost')
        self.executor.state['jobs'].append(attempt)
        self.job['payload']['jobId']=attempt['id']
        return attempt

    def test_completed_previous_receipt_can_resolve_retry_family(self):
        attempt=self.add_failed_retry()
        self.receipt['completedByJobId']=attempt['id']
        self.run_retry()
        self.assertEqual(attempt['status'],'interrupted')
        self.assertEqual(attempt['resolution']['jobId'],self.job['id'])
        self.assertEqual(self.original['resolution']['jobId'],self.job['id'])

    def test_verified_restoration_abandon_closes_failed_retry_family(self):
        attempt=self.add_failed_retry()
        self.job['payload']['decision']='abandon'
        restored=dict(self.result,releaseTag='old',fingerprint='original-fingerprint')
        self.executor.runtime.call.return_value=dict(observation=restored,recoveryEvidence={'verified':True})
        self.run_retry()
        self.executor.runtime.call.assert_called_once_with('test','verify-restoration',releaseTag=self.tag,
                                                           jobId=self.original['id'],originFingerprint='original-fingerprint')
        self.assertEqual(attempt['resolution']['decision'],'abandon')
        self.assertEqual(self.original['resolution']['decision'],'abandon')
        self.assertEqual(self.package['stage'],'built')


class TestTailWrapperTests(unittest.TestCase):
    def test_tail_transport_waits_for_archive_verification_without_replaying_uncertain_effects(self):
        runtime=Runtime(dict(operationTimeout=30, targets=dict(test=dict(host='example.invalid', python='/usr/bin/python3',
                         entryUrl='http://example.invalid',frontend='front',backend='back',database='db'))))
        for effect in (subprocess.TimeoutExpired('ssh',1800),
                       subprocess.CompletedProcess('ssh',255,b'',b''),
                       subprocess.CompletedProcess('ssh',0,b'incomplete',b'')):
            options={'side_effect':effect} if isinstance(effect,Exception) else {'return_value':effect}
            with self.subTest(effect=type(effect).__name__), patch('intruoyi_runtime.subprocess.run',**options) as command:
                with self.assertRaises(RuntimeUncertain):
                    runtime.call('test','resume-test-deployment-tail')
                self.assertEqual(command.call_count,1)
                self.assertEqual(command.call_args.kwargs['timeout'],1800)

    def test_wrapper_passes_full_evidence_once_without_normal_deploy(self):
        runtime=object.__new__(Runtime)
        runtime.call=Mock(return_value={'receipt':'fixture'})
        callback=Mock()
        runtime.resume_test_deployment_tail('test',{'releaseTag':'candidate'},[{'action':'APPLY'}],
                                             'original','retry','package','manifest',callback)
        runtime.call.assert_called_once_with('test','resume-test-deployment-tail',manifest={'releaseTag':'candidate'},
                                             originalPlan=[{'action':'APPLY'}],originalJobId='original',retryJobId='retry',
                                             packageSha256='package',manifestSha256='manifest')
        callback.assert_called_once_with('resume-original-test-deployment-tail',effects=True)
        runtime.call.reset_mock()
        with self.assertRaisesRegex(RuntimeBlocked,'restricted to test'):
            runtime.resume_test_deployment_tail('prod',{},[],'original','retry','package','manifest',callback)
        runtime.call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
