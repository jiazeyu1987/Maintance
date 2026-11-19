import copy
import unittest

from candidate_history import requires_candidate_history
from intruoyi_build import historical_integrity


class CandidateHistoryTests(unittest.TestCase):
    def setUp(self):
        self.package = dict(releaseTag='candidate', abandoned=True, baseline=False)
        self.original = dict(id='deploy', releaseTag='candidate', action='publish-test',
                             target='test', effectsStarted=True, status='failed',
                             resolution=dict(decision='restored', jobId='accept'))
        self.accept = dict(id='accept', action='accept-recovery', status='succeeded',
                           releaseTag='candidate', target='test', originalDeploymentJobId='deploy',
                           result=dict(maintenance=False, receipt=dict(phase='opened', originalJobId='deploy')))
        self.state = dict(jobs=[self.original, self.accept], environments=dict(test=dict(releaseTag='old')))

    def test_accepted_recovery_releases_candidate_constraint(self):
        before = copy.deepcopy((self.package, self.state))
        self.assertFalse(requires_candidate_history(self.package, self.state))
        self.assertEqual(before, (self.package, self.state))

    def test_abandonment_alone_does_not_release_constraint(self):
        self.original.pop('resolution')
        self.assertTrue(requires_candidate_history(self.package, self.state))

    def test_successful_acceptance_and_binding_required(self):
        for key, value in [('status', 'running'), ('action', 'recover-release'),
                           ('releaseTag', 'other'), ('target', 'prod'),
                           ('originalDeploymentJobId', 'other')]:
            with self.subTest(key=key):
                state = copy.deepcopy(self.state)
                state['jobs'][1][key] = value
                self.assertTrue(requires_candidate_history(self.package, state))

    def test_opened_receipt_required(self):
        for change in [dict(maintenance=True), dict(receipt=dict(phase='restored', originalJobId='deploy')),
                       dict(receipt=dict(phase='opened', originalJobId='other'))]:
            with self.subTest(change=change):
                state = copy.deepcopy(self.state)
                state['jobs'][1]['result'].update(change)
                self.assertTrue(requires_candidate_history(self.package, state))

    def test_active_target_or_unrestored_deployment_keeps_constraint(self):
        self.state['environments']['prod'] = dict(releaseTag='candidate')
        self.assertTrue(requires_candidate_history(self.package, self.state))
        self.state['environments'].pop('prod')
        self.state['jobs'].append(dict(self.original, id='other-deploy', resolution={}))
        self.assertTrue(requires_candidate_history(self.package, self.state))

    def test_baseline_nonabandoned_or_no_deployments_keeps_constraint(self):
        for patch in [dict(baseline=True), dict(abandoned=False)]:
            self.assertTrue(requires_candidate_history(dict(self.package, **patch), self.state))
        self.state['jobs'] = []
        self.assertTrue(requires_candidate_history(self.package, self.state))

    def test_executed_ledger_still_rejects_removed_or_changed_sql(self):
        ledger = [dict(migrationId='executed', sha256='a'*64, status='APPLIED')]
        for incoming in [[], [dict(migrationId='executed', sha256='b'*64)]]:
            with self.assertRaisesRegex(ValueError, 'Historical migration source conflict'):
                historical_integrity(incoming, ledger)


if __name__ == '__main__':
    unittest.main()
