"""Ordering contracts. Mocked transports here are unit boundaries, not E2E evidence."""
import copy
import threading
import unittest
from unittest.mock import Mock, patch

from executor import Executor
from intruoyi_executor import IntRuoyiExecutor
from release_order import deployment_block, deployment_blocks, release_order

OLD = '2026-10-24-01-00-00'
CANDIDATE = '2026-10-24-02-00-00'
NEW = '2026-10-24-03-00-00'


class OrderingTests(unittest.TestCase):
    def setUp(self):
        self.package = dict(releaseTag=CANDIDATE, stage='built', baseline=False,
                            outcomes={'prod': {'acceptance': {'status': 'passed'}}})
        self.environments = {env: dict(releaseTag=OLD, maintenance=False) for env in ('test', 'prod', 'backup')}

    def test_target_old_new_and_same(self):
        for action, target in [('publish-test', 'test'), ('promote-prod', 'prod'), ('promote-backup', 'backup')]:
            with self.subTest(action=action):
                environments = copy.deepcopy(self.environments)
                if target == 'backup': environments['prod']['releaseTag'] = CANDIDATE
                self.assertIsNone(deployment_block(action, self.package, environments))
                environments[target]['releaseTag'] = NEW
                self.assertIn('STALE_RELEASE', deployment_block(action, self.package, environments))
                environments[target]['releaseTag'] = CANDIDATE
                self.assertIn('RELEASE_ALREADY_DEPLOYED', deployment_block(action, self.package, environments))

    def test_bad_version_never_gets_lexical_order(self):
        for invalid in [None, '', 'R1', '2026-2-01-00-00-00', '2026-02-30-00-00-00', '2026-10-24-25-00-00']:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError): release_order(invalid)
                self.environments['prod']['releaseTag'] = invalid
                self.assertIn('RELEASE_ORDER_UNKNOWN', deployment_block('promote-prod', self.package, self.environments))
        self.assertIn('RELEASE_ORDER_UNKNOWN', deployment_block('promote-prod', self.package, {}))

    def test_new_build_and_list_reordering_do_not_retire_candidate(self):
        state = dict(environments=self.environments, packages=[dict(releaseTag=NEW), self.package])
        original = copy.deepcopy(state)
        self.assertNotIn('promote-prod', deployment_blocks(state)[CANDIDATE])
        self.assertEqual(state, original)
        state['packages'].reverse()
        self.assertNotIn('promote-prod', deployment_blocks(state)[CANDIDATE])

    def test_test_can_lead_production_without_retiring_formal_candidate(self):
        self.environments['test']['releaseTag'] = NEW
        self.assertIsNone(deployment_block('promote-prod', self.package, self.environments))

    def test_backup_rejects_historical_production_acceptance(self):
        self.environments['prod']['releaseTag'] = NEW
        self.assertIn('PRODUCTION_PACKAGE_CHANGED', deployment_block('promote-backup', self.package, self.environments))

    def test_backup_requires_current_acceptance_and_open_admission(self):
        self.environments['prod']['releaseTag'] = CANDIDATE
        self.package['outcomes']['prod']['acceptance']['status'] = 'failed'
        self.assertIn('PRODUCTION_NOT_ACCEPTED', deployment_block('promote-backup', self.package, self.environments))
        self.package['outcomes']['prod']['acceptance']['status'] = 'passed'
        for changes in [dict(maintenance=True), dict(maintenance=None), dict(maintenanceUnknown=True)]:
            with self.subTest(changes=changes):
                self.environments['prod'] = dict(releaseTag=CANDIDATE, maintenance=False, **{k:v for k,v in changes.items() if k!='maintenance'})
                self.environments['prod'].update(changes)
                self.assertIn('PRODUCTION_NOT_OPEN', deployment_block('promote-backup', self.package, self.environments))

    def test_recovery_and_continuations_not_treated_as_normal_deployments(self):
        self.environments['prod']['releaseTag'] = NEW
        for action in ['recover-release', 'accept-recovery', 'resolve-task', 'upgrade-rehearsal', 'accept-prod']:
            self.assertIsNone(deployment_block(action, self.package, self.environments))


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.executor = object.__new__(Executor)
        self.executor.c = {}
        self.executor.lock = threading.RLock()
        self.package = dict(releaseTag=CANDIDATE, stage='built', baseline=False)
        self.executor.state = dict(packages=[self.package], jobs=[], environments={'test': dict(releaseTag=NEW)})
        self.executor.manifest = Mock(return_value=(self.package, {}))
        self.executor.save = Mock()
        self.payload = dict(requestId='request-order-001', releaseTag=CANDIDATE)

    def test_stale_request_creates_no_job_or_worker(self):
        with patch('executor.threading.Thread') as thread:
            with self.assertRaisesRegex(ValueError, 'STALE_RELEASE'):
                self.executor.submit('publish-test', self.payload, 'unit')
            thread.assert_not_called()
        self.assertEqual(self.executor.state['jobs'], [])
        self.executor.save.assert_not_called()

    def test_fresh_request_still_creates_one_task(self):
        self.executor.state['environments']['test']['releaseTag'] = OLD
        with patch('executor.threading.Thread') as thread:
            job = self.executor.submit('publish-test', self.payload, 'unit')
            thread.return_value.start.assert_called_once()
        self.assertEqual(job['releaseTag'], CANDIDATE)

    def test_duplicate_request_returns_original_after_new_version_deployed(self):
        job = dict(action='publish-test', payload=self.payload, requestId=self.payload['requestId'], status='succeeded')
        self.executor.state['jobs'] = [job]
        self.assertIs(self.executor.submit('publish-test', self.payload, 'unit'), job)
        self.executor.manifest.assert_not_called()

    def test_remote_duplicate_does_not_repeat_changed_prerequisites(self):
        remote = object.__new__(IntRuoyiExecutor)
        remote.c = dict(applicationId='intruoyi')
        remote.lock = threading.RLock()
        payload = dict(self.payload, applicationId='intruoyi')
        job = dict(action='promote-backup', payload=payload, requestId=payload['requestId'], status='succeeded')
        remote.state = dict(jobs=[job], packages=[], environments={})
        self.assertIs(remote.submit('promote-backup', payload, 'unit'), job)

    def test_worker_rechecks_when_target_changed_after_submission(self):
        self.executor.state['environments']['test']['releaseTag'] = OLD
        self.executor.password = 'private'
        self.executor.package = self.executor.manifest
        self.executor.log = Mock()
        self.executor.audit_target = Mock()
        self.executor.fingerprint = Mock(return_value='current')
        self.executor.deploy = Mock()
        with patch('executor.threading.Thread'):
            job = self.executor.submit('publish-test', self.payload, 'unit')
        self.executor.state['environments']['test']['releaseTag'] = NEW
        self.executor.execute(job)
        self.assertEqual(job['status'], 'failed')
        self.assertIn('STALE_RELEASE', job['error'])
        self.executor.deploy.assert_not_called()
        self.assertFalse(job.get('effectsStarted'))

    def test_remote_observation_overrides_stale_registered_version(self):
        remote = object.__new__(IntRuoyiExecutor)
        remote.state = self.executor.state
        remote.state['environments']['test']['releaseTag'] = OLD
        remote.step = Mock()
        remote.runtime = Mock()
        remote.runtime.observe.return_value = dict(releaseTag=NEW)
        with self.assertRaisesRegex(ValueError, 'STALE_RELEASE'):
            remote.deploy('test', self.package, {}, dict(action='publish-test'))
        remote.runtime.stage.assert_not_called()
        remote.runtime.deploy.assert_not_called()


if __name__ == '__main__': unittest.main()
