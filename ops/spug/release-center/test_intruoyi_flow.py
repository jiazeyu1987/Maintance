"""Release authorization unit contracts; no SSH, database or release is executed."""
import copy
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
from intruoyi_executor import IntRuoyiExecutor, backup_rehearsal_schema, passed_rehearsal_schema
from executor import Executor, require


class WorkflowStateTests(unittest.TestCase):
    """Exercise real state transitions with isolated unit boundaries, not remote success evidence."""
    def setUp(self):
        self.executor = object.__new__(Executor)
        self.executor.c = dict(runtimeKind='remote-intruoyi')
        self.executor.lock = threading.RLock()
        self.executor.password = 'unit-secret'
        self.package = dict(releaseTag='candidate', packageSha256='package', stage='built', baseline=False, rehearsals=[])
        self.executor.state = dict(packages=[self.package], jobs=[], environments={
            env:dict(releaseTag='old', fingerprint=env+'-origin') for env in ('test', 'prod', 'backup')})
        self.executor.save = Mock()
        self.executor.log = Mock()
        self.executor.manifest = Mock(return_value=(self.package, {}))
        self.executor.package = Mock(return_value=(self.package, {}))
        self.executor.audit_target = Mock()
        self.executor.fingerprint = lambda env:self.executor.state['environments'][env]['fingerprint']
        self.executor.maintenance = Mock()
        self.executor.health = lambda env, tag:require(self.executor.state['environments'][env]['releaseTag'] == tag, 'Actual runtime version differs')
        def prepare(package, job):
            record = dict(id=job['id'], jobId=job['id'], source='prod', status='ready',
                          originFingerprint='prod-origin', packageSha256='package')
            package['rehearsals'].append(record)
            package['activeRehearsal'] = record['id']
            self.executor.state['environments']['rehearsal'] = dict(releaseTag='old', fingerprint='isolated-origin')
        self.executor.prepare = prepare
        def deploy(env, package, manifest, job):
            if env == 'prod': job['rehearsalId'] = package['activeRehearsal']
            self.executor.state['environments'][env]['releaseTag'] = package['releaseTag']
        self.executor.deploy = deploy

    def run_action(self, action, **payload):
        with patch('executor.threading.Thread'):
            job = self.executor.submit(action, dict(requestId='request-'+str(len(self.executor.state['jobs'])),
                                       releaseTag='candidate', note='unit acceptance evidence', **payload), 'unit operator')
        self.executor.execute(job)
        return job

    def test_direct_test_production_rehearsal_and_direct_backup_complete_in_order(self):
        stages = [('publish-test', 'test-deployed'), ('mark-tested', 'tested'),
                  ('prepare-rehearsal', 'rehearsal-ready'), ('upgrade-rehearsal', 'rehearsal-upgraded'),
                  ('accept-rehearsal', 'rehearsal-passed'), ('promote-prod', 'prod-deployed'),
                  ('accept-prod', 'prod-accepted'), ('promote-backup', 'backup-deployed'), ('accept-backup', 'completed')]
        for action, stage in stages:
            job = self.run_action(action, **({'source':'prod'} if action == 'prepare-rehearsal' else {}))
            self.assertEqual(job['status'], 'succeeded', job.get('error'))
            self.assertEqual(self.package['stage'], stage)
        self.assertEqual(len(self.package['rehearsals']), 1)
        self.assertEqual(self.package['validatedProductionRehearsal'], self.package['activeRehearsal'])
        self.assertEqual(self.package['outcomes']['test']['acceptance']['status'], 'passed')

    def test_test_acceptance_checks_current_running_version(self):
        self.run_action('publish-test')
        self.executor.state['environments']['test']['releaseTag'] = 'another-candidate'
        job = self.run_action('mark-tested')
        self.assertEqual(job['status'], 'failed')
        self.assertEqual(self.package['stage'], 'test-deployed')
        self.assertEqual(self.package['outcomes']['test']['acceptance']['status'], 'failed')

    def test_test_pass_does_not_authorize_production_and_nonproduction_rehearsals_refused(self):
        self.run_action('publish-test')
        self.run_action('mark-tested')
        with self.assertRaisesRegex(ValueError, 'Workflow prerequisite'):
            self.run_action('promote-prod')
        for source in ('test', 'backup'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'Only production'):
                self.run_action('prepare-rehearsal', source=source)


class ProductionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.origin = dict(releaseTag='old', images=dict(backend='backend', frontend='frontend'),
                           schemaSha256='schema', ledgerSha256='ledger')
        self.record = dict(id='prod-proof', source='prod', status='passed', packageSha256='package',
                           originFingerprint='prod-runtime', originState=copy.deepcopy(self.origin),
                           upgradedSchemaSha256='upgraded')
        self.package = dict(packageSha256='package', validatedProductionRehearsal='prod-proof',
                            rehearsals=[self.record])

    def test_backup_uses_accepted_production_origin_despite_distinct_runtime(self):
        observation = dict(self.origin, fingerprint='backup-runtime', runtimeConfigSha256='backup-config')
        self.assertEqual(backup_rehearsal_schema(self.package, observation), 'upgraded')

    def test_each_incompatible_origin_field_blocks_backup(self):
        for key in self.origin:
            with self.subTest(key=key):
                observation = dict(self.origin, **{key: 'changed'})
                with self.assertRaisesRegex(ValueError, key):
                    backup_rehearsal_schema(self.package, observation)

    def test_unbound_or_different_package_or_unaccepted_proof_blocks_backup(self):
        variants = [dict(validatedProductionRehearsal=None), dict(packageSha256='other')]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                backup_rehearsal_schema(dict(self.package, **changes), self.origin)
        for changes in (dict(source='test'), dict(status='upgraded'), dict(originState={}), dict(upgradedSchemaSha256=None)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                backup_rehearsal_schema(dict(self.package, rehearsals=[dict(self.record, **changes)]), self.origin)

    def test_production_requires_own_exact_current_runtime_and_package(self):
        self.assertEqual(passed_rehearsal_schema(self.package, 'prod', 'prod-runtime'), 'upgraded')
        for target, fingerprint in [('prod', 'changed'), ('backup', 'prod-runtime'), ('test', 'prod-runtime')]:
            with self.subTest(target=target, fingerprint=fingerprint), self.assertRaises(ValueError):
                passed_rehearsal_schema(self.package, target, fingerprint)


class IsolationDiscardTests(unittest.TestCase):
    def setUp(self):
        self.executor = object.__new__(IntRuoyiExecutor)
        self.original = dict(id='failed', action='upgrade-rehearsal', target='rehearsal', status='failed',
                             releaseTag='candidate', effectsStarted=True)
        self.record = dict(id='capture', source='test', packageSha256='hash', status='ready',
                           deployment=dict(jobId='failed'), originFingerprint='source')
        self.package = dict(releaseTag='candidate', packageSha256='hash', stage='built',
                            activeRehearsal='capture', rehearsals=[self.record])
        self.executor.state = dict(jobs=[self.original], packages=[self.package],
                                   environments=dict(rehearsal=dict(sourceEnvironment='test')))
        self.executor.runtime = Mock()
        self.executor.runtime.call.return_value = dict(stopped=True)
        self.origin = dict(fingerprint='source', schemaSha256='schema', ledgerRecords=[],
                           backendHealth=dict(status='UP'), frontendHttpStatus=200, releaseTag='old',
                           images=dict(backend='sha256:'+'a'*64, frontend='sha256:'+'b'*64),
                           maintenance=False, readOnly=dict(read_only=False, super_read_only=False))
        self.executor.runtime.observe.return_value = self.origin
        self.executor.save = Mock()
        self.executor.log = Mock()
        self.job = dict(id='resolve', actor='operator', payload=dict(jobId='failed', decision='abandon', note='verified original source'))

    def test_historical_test_isolation_can_be_discarded_without_restoring_business_db(self):
        self.executor.resolve_task(self.job)
        self.executor.runtime.observe.assert_called_once_with('test')
        self.executor.runtime.reset_rehearsal.assert_called_once()
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.record['status'], 'abandoned')
        self.assertEqual(self.package['stage'], 'built')
        self.assertNotIn('activeRehearsal', self.package)
        self.assertNotIn('rehearsal', self.executor.state['environments'])

    def test_uncertain_worker_changed_source_and_foreign_owner_never_reset(self):
        cases = ('worker', 'source', 'owner', 'read-only', 'maintenance')
        for case in cases:
            with self.subTest(case=case):
                self.setUp()
                if case == 'worker': self.executor.runtime.call.return_value = dict(stopped=False)
                if case == 'source': self.origin['fingerprint'] = 'changed'
                if case == 'owner': self.record['deployment']['jobId'] = 'another-job'
                if case == 'read-only': self.origin['readOnly']['read_only'] = True
                if case == 'maintenance': self.origin['maintenance'] = True
                with self.assertRaises(ValueError): self.executor.resolve_task(self.job)
                self.executor.runtime.reset_rehearsal.assert_not_called()
                self.assertNotIn('resolution', self.original)

    def test_failed_test_acceptance_can_be_rechecked_without_granting_acceptance(self):
        self.original.update(action='mark-tested', target='test', effectsStarted=False)
        self.package['stage'] = 'test-deployed'
        self.executor.manifest = Mock(return_value=(self.package, {}))
        self.executor.health = Mock()
        self.executor.audit_target = Mock()
        self.executor.resolve_task(self.job)
        self.executor.health.assert_called_once_with('test', 'candidate')
        self.executor.audit_target.assert_called_once_with('test', self.package, {})
        self.assertEqual(self.package['stage'], 'test-deployed')
        self.assertEqual(self.original['status'], 'failed')
        self.assertNotIn('acceptances', self.package)

    def test_readonly_acceptance_failure_stays_blocked_when_fresh_health_fails(self):
        self.original.update(action='mark-tested', target='test', effectsStarted=False)
        self.package['stage'] = 'test-deployed'
        self.executor.manifest = Mock(return_value=(self.package, {}))
        self.executor.health = Mock(side_effect=ValueError('Actual runtime differs'))
        with self.assertRaisesRegex(ValueError, 'Actual runtime differs'):
            self.executor.resolve_task(self.job)
        self.assertNotIn('resolution', self.original)

    def test_production_acceptance_never_enters_deployment_restoration(self):
        self.original.update(action='accept-prod', target='prod')
        with self.assertRaisesRegex(ValueError, 'operational reconciliation'):
            self.executor.resolve_task(self.job)
        self.executor.runtime.call.assert_not_called()
        self.assertNotIn('resolution', self.original)


class PreparationPrerequisiteFailureTests(unittest.TestCase):
    def setUp(self):
        self.executor = object.__new__(IntRuoyiExecutor)
        self.executor.c = {}
        self.original = dict(id='failed-prepare', action='prepare-rehearsal', status='failed',
                             target='rehearsal', sourceEnv='prod', releaseTag='candidate',
                             currentStep='inspect-full-data-rehearsal-prerequisites',
                             error='Original package location missing')
        self.package = dict(releaseTag='candidate', stage='tested', rehearsals=[])
        self.executor.state = dict(jobs=[self.original], packages=[self.package], environments={})
        self.executor.runtime = Mock()
        self.executor.runtime.targets = {}
        self.executor.save = Mock()
        self.executor.log = Mock()
        self.job = dict(id='resolve', actor='operator', payload=dict(jobId=self.original['id'],
                        decision='abandon', note='Original package location will be restored'))

    def test_missing_metadata_package_fails_before_effect_marker_and_can_be_abandoned(self):
        from intruoyi_runtime import Runtime
        runtime = object.__new__(Runtime)
        runtime.config = {'metadataRepair': {'directory': 'missing-original-package'}}
        runtime.targets = {'rehearsal': {}}
        runtime.observe = Mock(return_value={'images': {}, 'releaseTag': 'old', 'ledgerRecords': []})
        runtime.profile = Mock(return_value={'sourceEnvironment': 'prod'})
        runtime.call = Mock()
        callback = lambda name, effects=False:self.executor.step(self.original, name, effects)
        with patch('intruoyi_metadata.reference', side_effect=ValueError('Original package location missing')):
            with self.assertRaisesRegex(ValueError, 'Original package location missing'):
                runtime.prepare_rehearsal('prod', {'migrations': []}, callback, self.original['id'])
        self.assertEqual(self.original['currentStep'], 'inspect-full-data-rehearsal-prerequisites')
        self.assertNotIn('effectsStarted', self.original)
        self.assertNotIn('remoteStatusRequired', self.original)
        runtime.call.assert_not_called()
        before = copy.deepcopy(self.package)
        self.executor.resolve_task(self.job)
        self.assertEqual(self.original['resolution']['decision'], 'abandon')
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.original['error'], 'Original package location missing')
        self.assertEqual(self.package, before)
        self.assertEqual(self.executor.runtime.mock_calls, [])

    def test_either_effect_or_uncertain_remote_marker_requires_remote_terminal_proof(self):
        for marker in ('effectsStarted', 'remoteStatusRequired'):
            with self.subTest(marker=marker):
                self.setUp()
                self.original[marker] = True
                self.executor.runtime.call.side_effect = ValueError('Remote terminal proof missing')
                with patch('intruoyi_executor.rehearsal_profile', return_value={}):
                    with self.assertRaisesRegex(ValueError, 'Remote terminal proof missing'):
                        self.executor.resolve_task(self.job)
                self.executor.runtime.call.assert_called_once_with('prod', 'rehearsal-verify-stopped', releaseTag='candidate')
                self.executor.runtime.reset_rehearsal.assert_not_called()
                self.assertNotIn('resolution', self.original)

    def test_pre_effect_failure_cannot_be_retried_via_deployment_tail(self):
        self.job['payload']['decision'] = 'retry'
        with self.assertRaisesRegex(ValueError, 'interrupted restore tail'):
            self.executor.resolve_task(self.job)
        self.assertNotIn('resolution', self.original)
        self.assertEqual(self.executor.runtime.mock_calls, [])


if __name__ == '__main__':
    unittest.main()
