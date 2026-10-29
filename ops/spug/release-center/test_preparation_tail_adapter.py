"""Preparation startup-tail contracts, with remote transport isolated from unit tests."""
import copy
import unittest
from unittest.mock import Mock

from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime import RuntimeBlocked


class PreparationTailAdapterTests(unittest.TestCase):
    def setUp(self):
        self.executor = object.__new__(IntRuoyiExecutor)
        self.tag = '2026-10-23-16-51-17'
        self.original = dict(id='JOB-9310b279dd', action='prepare-rehearsal', target='rehearsal', sourceEnv='prod',
                             releaseTag=self.tag, status='failed', effectsStarted=True, remoteStatusRequired=True,
                             remotePhase='restore-starting', sourceOriginFingerprint='source-fingerprint',
                             error='frontend alias unavailable', remoteProgress=dict(status='failed',phase='failed'))
        self.job = dict(id='JOB-1111111111', action='resolve-task', status='running', releaseTag=self.tag,
                        actor='operator',payload=dict(jobId=self.original['id'],decision='retry',note='verify retained original copy'))
        verified = dict(env='test',jobId='JOB-2222222222',releaseTag=self.tag,packageSha256='a'*64,status='passed',
                        checks={key:dict(status='passed') for key in ('version','upgrade','login')})
        self.package = dict(releaseTag=self.tag,packageSha256='a'*64,manifestSha256='b'*64,stage='tested',rehearsals=[],
                            outcomes=dict(test=dict(technical=verified),rehearsal=dict(preparation=dict(jobId=self.original['id'],status='failed'))))
        self.manifest = dict(releaseTag=self.tag,migrations=[])
        self.origin = dict(releaseTag='original-production',fingerprint='source-fingerprint',schemaSha256='c'*64,
                           ledgerSha256='d'*64,ledgerRecords=[],images=dict(backend='sha256:'+'e'*64,frontend='sha256:'+'f'*64),
                           backendHealth=dict(status='UP'),frontendHttpStatus=200,maintenance=False,
                           readOnly=dict(read_only=False,super_read_only=False))
        self.receipt = dict(status='completed',phase='complete',originalJobId=self.original['id'],retryJobId=self.job['id'],
                            source='prod',releaseTag=self.tag,packageSha256='a'*64,manifestSha256='b'*64)
        self.result = dict(self.origin,fingerprint='isolated-fingerprint',originFingerprint='source-fingerprint',
                           verifiedOrigin=True,resumeReceipt=self.receipt,
                           remotePreparationProgress=dict(jobId=self.job['id'],status='succeeded',phase='completed'))
        self.executor.c = dict(targets=dict(prod=dict(host='source',stagingRoot='/source'),
                                             rehearsal=dict(host='isolation',stagingRoot='/isolation')),
                               rehearsalStagingRoots=dict(prod='/prod-isolation'))
        self.executor.state = dict(packages=[self.package],environments=dict(prod=copy.deepcopy(self.origin)),
                                    jobs=[self.job,self.original,dict(id='JOB-2222222222',action='mark-tested',target='test',
                                                                    status='succeeded',releaseTag=self.tag)])
        self.executor.runtime=Mock()
        self.executor.runtime.targets=copy.deepcopy(self.executor.c['targets'])
        self.executor.runtime.profile=lambda env:self.executor.runtime.targets[env]
        self.executor.runtime.observe.return_value=self.origin
        self.executor.runtime.call.return_value=dict(state='started',mutations=False)
        self.executor.runtime.resume_rehearsal_tail.return_value=self.result
        self.executor.package=Mock(return_value=(self.package,self.manifest))
        self.executor.save=Mock()
        self.executor.log=Mock()

    def run_retry(self):
        self.executor.resolve_task(self.job)

    def test_success_registers_only_original_baseline_and_preserves_failure(self):
        original_before=copy.deepcopy(self.original)
        self.run_retry()
        self.assertEqual({key:self.original[key] for key in original_before}, original_before)
        self.assertEqual(self.original['resolution']['decision'],'retry')
        self.assertEqual(self.package['stage'],'rehearsal-ready')
        record=self.executor.active_rehearsal(self.package)
        self.assertEqual(record['id'],self.job['id'])
        self.assertEqual(record['originalPreparationJobId'],self.original['id'])
        self.assertEqual(record['status'],'ready')
        self.assertEqual(record['originState']['images'],self.origin['images'])
        self.assertEqual(self.executor.state['environments']['rehearsal']['releaseTag'],'original-production')
        self.assertNotIn('technical',self.package['outcomes']['rehearsal'])
        self.assertEqual(self.package['outcomes']['rehearsal']['preparation']['status'],'succeeded')
        args=self.executor.runtime.resume_rehearsal_tail.call_args.args
        self.assertEqual(args[:7],('prod',self.manifest,self.original['id'],self.job['id'],'a'*64,'b'*64,'source-fingerprint'))
        self.executor.runtime.prepare_rehearsal.assert_not_called()
        self.executor.runtime.deploy.assert_not_called()
        self.executor.runtime.reset_rehearsal.assert_not_called()

    def test_pre_effect_capture_phase_and_nonproduction_preparations_cannot_resume(self):
        for changes in (dict(effectsStarted=False),dict(remoteStatusRequired=False),dict(remotePhase='capture-starting'),
                        dict(sourceEnv='backup'),dict(target='test')):
            with self.subTest(changes=changes):
                self.setUp()
                self.original.update(changes)
                with self.assertRaisesRegex(ValueError,'interrupted restore tail'):
                    self.run_retry()
                self.executor.runtime.resume_rehearsal_tail.assert_not_called()

    def test_completed_capture_continues_transfer_without_recapture(self):
        self.original['remotePhase']='capture-complete'
        self.original['remoteProgress']=dict(jobId=self.original['id'],status='succeeded',phase='capture-complete')
        self.receipt.update(kind='captured-transfer',captureSha256='1'*64)
        self.result['remotePreparationProgress']['jobId']=self.original['id']
        self.executor.runtime.resume_rehearsal_transfer.return_value=self.result
        self.run_retry()
        self.executor.runtime.resume_rehearsal_transfer.assert_called_once()
        self.executor.runtime.resume_rehearsal_tail.assert_not_called()
        self.executor.runtime.prepare_rehearsal.assert_not_called()
        self.assertEqual(self.package['stage'],'rehearsal-ready')
        self.assertEqual(self.original['status'],'failed')

    def test_restore_preflight_failure_continues_verified_capture_without_recapture(self):
        self.executor.runtime.call.return_value=dict(state='not-started',mutations=False)
        self.receipt.update(kind='captured-transfer',captureSha256='1'*64)
        self.result['remotePreparationProgress']['jobId']=self.original['id']
        self.executor.runtime.resume_rehearsal_transfer.return_value=self.result
        self.run_retry()
        self.executor.runtime.resume_rehearsal_transfer.assert_called_once()
        self.executor.runtime.resume_rehearsal_tail.assert_not_called()
        self.executor.runtime.prepare_rehearsal.assert_not_called()
        self.assertEqual(self.job['restoreEntryEvidence']['state'],'not-started')
        self.assertEqual(self.package['stage'],'rehearsal-ready')

    def test_unavailable_restore_entry_proof_never_selects_reimport(self):
        self.executor.runtime.call.side_effect=RuntimeBlocked('Cannot inspect restore resources')
        with self.assertRaises(RuntimeBlocked):self.run_retry()
        self.executor.runtime.resume_rehearsal_transfer.assert_not_called()
        self.executor.runtime.resume_rehearsal_tail.assert_not_called()

    def test_foreign_package_outcome_registered_copy_and_missing_test_proof_block(self):
        cases=('tag','outcome','registered','active','test-proof','stage')
        for case in cases:
            with self.subTest(case=case):
                self.setUp()
                if case=='tag': self.job['releaseTag']='other'
                if case=='outcome': self.package['outcomes']['rehearsal']['preparation']['jobId']='another'
                if case=='registered': self.executor.state['environments']['rehearsal']={}
                if case=='active': self.package['activeRehearsal']='foreign-record'
                if case=='test-proof': self.package['outcomes']['test']['technical']['checks']['login']['status']='pending'
                if case=='stage': self.package['stage']='prod-accepted'
                with self.assertRaises(ValueError):self.run_retry()
                self.executor.runtime.resume_rehearsal_tail.assert_not_called()

    def test_changed_or_unhealthy_source_blocks_before_remote_resume(self):
        for changes in (dict(fingerprint='changed'),dict(maintenance=True),dict(frontendHttpStatus=503),
                        dict(readOnly=dict(read_only=True,super_read_only=False))):
            with self.subTest(changes=changes):
                self.setUp()
                self.origin.update(changes)
                with self.assertRaises(ValueError):self.run_retry()
                self.executor.runtime.resume_rehearsal_tail.assert_not_called()

    def test_active_or_unknown_remote_worker_leaves_failed_family_unresolved(self):
        self.executor.runtime.resume_rehearsal_tail.side_effect=RuntimeBlocked('Original remote worker is not confirmed stopped')
        with self.assertRaisesRegex(RuntimeBlocked,'not confirmed stopped'):self.run_retry()
        self.assertNotIn('resolution',self.original)
        self.assertNotIn('rehearsal',self.executor.state['environments'])
        self.assertEqual(self.package['stage'],'tested')
        self.executor.runtime.prepare_rehearsal.assert_not_called()

    def test_receipt_and_final_baseline_mismatches_never_register_ready(self):
        for field in ('originalJobId','retryJobId','source','releaseTag','packageSha256','manifestSha256','phase'):
            with self.subTest(field=field):
                self.setUp()
                self.receipt[field]='wrong'
                with self.assertRaisesRegex(ValueError,'receipt'):self.run_retry()
                self.assertNotIn('rehearsal',self.executor.state['environments'])
        for field in ('images','schemaSha256','ledgerSha256','releaseTag','originFingerprint','verifiedOrigin','frontendHttpStatus'):
            with self.subTest(field=field):
                self.setUp()
                self.result[field]={} if field=='images' else 'wrong'
                with self.assertRaises(ValueError):self.run_retry()
                self.assertNotIn('resolution',self.original)
                self.assertEqual(self.package['rehearsals'],[])

    def test_source_changed_after_tail_does_not_register_the_copy(self):
        self.executor.runtime.observe.side_effect=[self.origin,dict(self.origin,fingerprint='changed-after-resume')]
        with self.assertRaisesRegex(ValueError,'Source changed'):self.run_retry()
        self.assertNotIn('rehearsal',self.executor.state['environments'])
        self.assertNotIn('resolution',self.original)

    def add_failed_attempt(self):
        attempt=dict(id='JOB-3333333333',action='resolve-task',status='interrupted',effectsStarted=True,
                     target='rehearsal',sourceEnv='prod',releaseTag=self.tag,originalPreparationJobId=self.original['id'],
                     payload=dict(decision='retry'),error='SSH response lost')
        self.executor.state['jobs'].append(attempt)
        self.job['payload']['jobId']=attempt['id']
        return attempt

    def test_completed_previous_attempt_receipt_can_be_collected_without_replaying_import(self):
        attempt=self.add_failed_attempt()
        self.receipt['retryJobId']=attempt['id']
        self.result['remotePreparationProgress']['jobId']=attempt['id']
        self.run_retry()
        self.assertEqual(attempt['status'],'interrupted')
        self.assertEqual(attempt['resolution']['jobId'],self.job['id'])
        self.assertEqual(self.original['resolution']['jobId'],self.job['id'])
        self.assertEqual(self.executor.active_rehearsal(self.package)['id'],self.job['id'])

    def test_failed_attempt_family_can_be_explicitly_discarded_after_remote_stop_proof(self):
        attempt=self.add_failed_attempt()
        self.job['payload']['decision']='abandon'
        self.executor.runtime.call.return_value=dict(stopped=True,originFingerprint='source-fingerprint')
        self.run_retry()
        self.executor.runtime.reset_rehearsal.assert_called_once()
        self.assertEqual(self.original['resolution']['decision'],'abandon')
        self.assertEqual(attempt['resolution']['decision'],'abandon')
        self.assertEqual(attempt['status'],'interrupted')
        self.assertEqual(self.package['stage'],'tested')


if __name__ == '__main__':
    unittest.main()
