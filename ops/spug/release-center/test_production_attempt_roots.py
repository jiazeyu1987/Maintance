"""Production attempts preserve prior immutable recovery/operation evidence."""
import copy
from types import SimpleNamespace
import unittest

from backup_retry import bind_attempt_roots


class ProductionAttemptRootsTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(id='JOB-1111111111', action='promote-prod', target='prod',
                             releaseTag='v', status='failed', resolution={'decision': 'abandon'},
                             runtimeStagingRoots={'test': '/test/attempts/JOB-aaaaaaaaaa'})
        self.package = {'releaseTag': 'v', 'outcomes': {'prod': {'deployment': {'jobId': self.original['id']}}}}
        self.executor = SimpleNamespace(
            state={'jobs': [self.original], 'packages': [self.package]},
            c={'targets': {'prod': {'stagingRoot': '/prod/releases'}}}, save=lambda: None)

    def test_first_production_attempt_owns_job_directory(self):
        self.executor.state = {'jobs': [], 'packages': []}
        job = dict(id='JOB-2222222222', action='promote-prod', releaseTag='v', payload={})
        bind_attempt_roots(self.executor, job)
        self.assertEqual(job['runtimeStagingRoots'], {'prod': '/prod/releases/attempts/JOB-2222222222'})

    def test_new_attempt_preserves_original_and_inherits_other_target_roots(self):
        self.original['runtimeStagingRoots']['prod'] = '/prod/releases/attempts/JOB-1111111111'
        before = copy.deepcopy(self.original)
        job = dict(id='JOB-2222222222', action='promote-prod', releaseTag='v', payload={})
        bind_attempt_roots(self.executor, job)
        self.assertEqual(job['runtimeStagingRoots'], {
            'test': '/test/attempts/JOB-aaaaaaaaaa', 'prod': '/prod/releases/attempts/JOB-2222222222'})
        self.assertEqual(self.original, before)

    def test_resolution_and_followup_inherit_exact_deployment_directory(self):
        deployment = dict(id='JOB-2222222222', action='promote-prod', releaseTag='v', payload={})
        bind_attempt_roots(self.executor, deployment)
        self.executor.state['jobs'].insert(0, deployment)
        self.package['outcomes']['prod']['deployment']['jobId'] = deployment['id']
        resolution = dict(id='JOB-3333333333', action='resolve-task', releaseTag='v',
                          payload={'jobId': deployment['id']})
        bind_attempt_roots(self.executor, resolution)
        acceptance = dict(id='JOB-4444444444', action='accept-prod', releaseTag='v', payload={})
        bind_attempt_roots(self.executor, acceptance)
        self.assertEqual(resolution['runtimeStagingRoots'], deployment['runtimeStagingRoots'])
        self.assertEqual(acceptance['runtimeStagingRoots'], deployment['runtimeStagingRoots'])
        bind_attempt_roots(self.executor, deployment)
        self.assertEqual(deployment['runtimeStagingRoots']['prod'], '/prod/releases/attempts/JOB-2222222222')


if __name__ == '__main__':
    unittest.main()
