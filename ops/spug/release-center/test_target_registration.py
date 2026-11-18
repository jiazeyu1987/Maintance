import copy
import unittest
from types import SimpleNamespace

from target_registration import registration_targets, validate_registered_takeover


class TargetRegistrationTests(unittest.TestCase):
    def fixture(self):
        original = dict(id='failed', action='publish-test', target='test',
                        currentStep='check-target-origin', status='failed',
                        createdAt='2026-11-16-12-24-09', originFingerprint='old',
                        remoteOperations=[dict(action='observe', env='test')])
        observed = dict(fingerprint='new', readOnly=dict(read_only=False, super_read_only=False), maintenance=False)
        registered = dict(observed, registrationJobId='registration')
        jobs = [dict(id='registration', action='register-targets', status='succeeded',
                     createdAt='2026-11-16-13-00-00', result=dict(targets={'test': {}}))]
        return original, registered, jobs, observed

    def test_explicit_target_leaves_other_targets_out(self):
        self.assertEqual(registration_targets({'target': 'test'}), ('test',))
        self.assertEqual(registration_targets({}), ('test', 'prod', 'backup'))
        with self.assertRaises(ValueError):
            registration_targets({'target': 'unknown'})

    def test_verified_registration_closes_only_read_only_pre_effect_failure(self):
        args = self.fixture()
        proof = validate_registered_takeover(*args)
        self.assertEqual(proof['registrationJobId'], 'registration')
        self.assertEqual(args[0]['originFingerprint'], 'old')

    def test_side_effect_or_unknown_remote_action_rejected(self):
        for change in [dict(effectsStarted=True), dict(currentStep='deploy'),
                       dict(remoteOperations=[dict(action='deploy', env='test')]),
                       dict(remoteOperations=[dict(action='observe', env='prod')])]:
            args = self.fixture(); args[0].update(change)
            with self.assertRaises(ValueError): validate_registered_takeover(*args)

    def test_failed_old_or_wrong_target_registration_rejected(self):
        for change in [dict(status='failed'), dict(createdAt='2026-11-15-00-00-00'),
                       dict(result=dict(targets={'prod': {}}))]:
            args = self.fixture(); args[2][0].update(change)
            with self.assertRaises(ValueError): validate_registered_takeover(*args)

    def test_drift_or_remaining_protection_rejected(self):
        for change in [dict(fingerprint='drift'), dict(maintenance=True),
                       dict(readOnly=dict(read_only=True, super_read_only=True))]:
            args = self.fixture(); args[3].update(change)
            with self.assertRaises(ValueError): validate_registered_takeover(*args)

    def test_real_registration_method_updates_only_selected_healthy_target(self):
        from intruoyi_executor import IntRuoyiExecutor
        for healthy in (True, False):
            executor = IntRuoyiExecutor.__new__(IntRuoyiExecutor)
            executor.password = 'unused-unit-test'
            executor.state = {'environments': {'test': {'old': True}, 'prod': {'keep': 1}, 'backup': {'keep': 2}}}
            before = copy.deepcopy(executor.state)
            calls = []
            def observe(env):
                calls.append(env)
                if env != 'test': raise AssertionError('Unselected target contacted')
                return dict(schemaSha256='schema', fingerprint='fingerprint', ledgerRecords=[],
                            backendHealth={'status': 'UP' if healthy else 'DOWN'}, frontendHttpStatus=200,
                            images={role:'sha256:'+'a'*64 for role in ('backend','frontend')}, releaseTag='old-version')
            executor.runtime = SimpleNamespace(observe=observe)
            executor.save = lambda: None
            executor.step = lambda *a, **k: None
            executor.log = lambda *a, **k: None
            job = dict(id='registration', action='register-targets', payload={'target': 'test'})
            executor.execute_bound(job)
            self.assertEqual(calls, ['test'])
            self.assertEqual(executor.state['environments']['prod'], before['environments']['prod'])
            self.assertEqual(executor.state['environments']['backup'], before['environments']['backup'])
            self.assertEqual(job['status'], 'succeeded' if healthy else 'failed')
            if not healthy: self.assertEqual(executor.state, before)


if __name__ == '__main__':
    unittest.main()
