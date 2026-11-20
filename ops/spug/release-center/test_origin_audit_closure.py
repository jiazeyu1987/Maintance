"""A failed read-only origin audit may close only against its original receipt."""
import copy
import unittest
from unittest.mock import Mock, patch

from interruption import execute


class OriginAuditClosureTests(unittest.TestCase):
    def setUp(self):
        self.operation = dict(operationId='OP-'+'a'*20, env='prod', action='observe')
        self.original = dict(id='JOB-'+'1'*10, action='promote-prod', target='prod',
            releaseTag='2026-11-19-23-41-45', status='failed', payload={},
            currentStep='check-target-origin', error='Registered baseline mismatch: prod/schemaSha256',
            originFingerprint='a'*64, localProcessTracking=True, localProcesses=[],
            finishedAt='2026-11-20-09-05-55', remoteOperations=[self.operation])
        self.receipt = dict(operationId=self.operation['operationId'], jobId=self.original['id'],
            action='observe', status='succeeded', worker='stopped', result=dict(fingerprint='b'*64))
        self.executor = Mock()
        self.executor.password = 'unit-only'
        self.executor.state = dict(jobs=[self.original], environments={}, packages=[])
        self.executor.runtime.call.return_value = self.receipt
        self.executor.runtime.observe.return_value = dict(fingerprint='b'*64)
        self.job = dict(id='JOB-'+'2'*10, action='reconcile-interruption', actor='operator',
            originalTaskId=self.original['id'], payload=dict(note='Verify the exact failed read-only audit'), logs=[])
        self.workers = patch('interruption.local_workers', return_value=[])
        self.local_workers = self.workers.start()
        self.addCleanup(self.workers.stop)

    def close(self):
        execute(self.executor, self.job)

    def assert_blocked(self):
        self.close()
        self.assertEqual(self.job['status'], 'failed')
        self.assertNotIn('resolution', self.original)
        self.executor.deploy.assert_not_called()
        self.executor.verify_technical.assert_not_called()

    def test_fresh_exact_observe_receipt_closes_failed_audit_without_rewriting_origin(self):
        before = copy.deepcopy(self.original)
        self.close()
        self.assertEqual(self.job['status'], 'succeeded', self.job.get('error'))
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.original['originFingerprint'], before['originFingerprint'])
        self.assertEqual(self.original['remoteOperations'], before['remoteOperations'])
        proof = self.job['result']['preEffectOriginProof']
        self.assertEqual(proof['source'], 'original-successful-observe-receipt')
        self.assertEqual(proof['operationId'], self.operation['operationId'])
        self.assertEqual(proof['fingerprint'], 'b'*64)
        self.assertEqual(self.original['resolution']['preEffectOriginProof'], proof)
        self.executor.runtime.call.assert_called_once_with('prod', 'inspect-operation',
            originalOperationId=self.operation['operationId'], originalJobId=self.original['id'])

    def test_missing_unknown_running_wrong_action_or_unbound_receipt_blocks(self):
        for field, value in (('status', 'unknown'), ('status', 'failed'), ('worker', 'unknown'),
                             ('worker', 'running'), ('action', 'health'), ('jobId', 'JOB-'+'3'*10),
                             ('operationId', 'OP-'+'b'*20), ('result', {})):
            with self.subTest(field=field, value=value):
                self.setUp()
                self.receipt[field] = value
                self.assert_blocked()

    def test_observed_origin_drift_or_missing_fingerprint_blocks(self):
        for fingerprint in ('c'*64, None):
            with self.subTest(fingerprint=fingerprint):
                self.setUp()
                self.executor.runtime.observe.return_value = dict(fingerprint=fingerprint)
                self.assert_blocked()

    def test_missing_receipt_or_any_extra_operation_blocks(self):
        for action in (None, 'health', 'deploy'):
            with self.subTest(action=action):
                self.setUp()
                if action is None:
                    self.original['remoteOperations'] = []
                else:
                    self.original['remoteOperations'].append(dict(self.operation, action=action))
                self.assert_blocked()

    def test_wrong_target_side_effects_untracked_or_other_failure_is_not_this_contract(self):
        for field, value in (('target', 'test'), ('effectsStarted', True), ('localProcessTracking', False),
                             ('finishedAt', None), ('currentStep', 'prepare-original-package'),
                             ('error', 'Other failure'), ('localProcessTrackingError', 'unknown')):
            with self.subTest(field=field):
                self.setUp()
                self.original[field] = value
                self.assert_blocked()

    def test_live_local_worker_blocks_even_when_remote_receipt_succeeded(self):
        self.local_workers.return_value = [dict(running=True)]
        self.assert_blocked()
        self.executor.runtime.observe.assert_not_called()

    def test_cached_inspection_cannot_replace_the_fresh_receipt_read(self):
        self.original['interruptionInspection'] = dict(disposition='close-pre-effect',
            observation=dict(fingerprint='b'*64), operations=[dict(self.operation, receipt=self.receipt)])
        self.executor.runtime.call.return_value = dict(self.receipt, status='unknown', worker='unknown')
        self.assert_blocked()

    def test_inspection_transport_failure_retains_the_original_blocker(self):
        self.executor.runtime.call.side_effect = RuntimeError('Transport failed')
        self.assert_blocked()
        self.assertIn('Transport failed', self.job['error'])

    def test_reconciliation_family_operation_cannot_be_ignored(self):
        attempt = dict(id='JOB-'+'3'*10, action='reconcile-interruption', status='failed',
                       originalTaskId=self.original['id'], remoteOperations=[dict(self.operation)])
        self.executor.state['jobs'].append(attempt)
        self.executor.runtime.call.side_effect = [self.receipt, dict(self.receipt, jobId=attempt['id'])]
        self.assert_blocked()

    def test_ordinary_origin_proof_keeps_its_original_fingerprint_comparison(self):
        self.original.update(currentStep='other-step', error='Other failure', remoteOperations=[])
        self.executor.runtime.observe.return_value = dict(fingerprint='a'*64)
        self.close()
        self.assertEqual(self.job['status'], 'succeeded', self.job.get('error'))
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.job['result']['preEffectOriginProof']['source'], 'registered-origin-fingerprint')


if __name__ == '__main__':
    unittest.main()
