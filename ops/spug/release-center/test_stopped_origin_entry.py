"""Exercise the normal executor entry before deployment, without remote side effects."""
import copy
from types import MethodType
import unittest
from unittest.mock import Mock, patch

from executor import Executor
from intruoyi_executor import IntRuoyiExecutor, _IntRuoyiExecutor
from intruoyi_runtime import Runtime, RuntimeBlocked, validate_stopped_forward_origin


class StoppedOriginEntryTests(unittest.TestCase):
    def setUp(self):
        self.tag = '2026-11-19-23-41-45'
        self.old_tag = '2026-11-19-15-03-12'
        self.origin = dict(releaseTag='2026-11-18-15-49-02', fingerprint='before-migrations',
                           images=dict(backend='b', frontend='f'), schemaSha256='old-schema',
                           ledgerSha256='old-ledger', ledgerRecords=[], runtimeConfigSha256='config',
                           databaseIdentity='database', components={
                               role:dict(containerId=role, imageId=role, running=True)
                               for role in ('backend', 'frontend', 'database')})
        self.observed = dict(copy.deepcopy(self.origin), releaseTag=None, fingerprint='after-migrations',
                             schemaSha256='verified-schema', ledgerSha256='applied-ledger',
                             ledgerRecords=[dict(migrationId='m1', sha256='a'*64, status='APPLIED')])
        for role in ('backend', 'frontend'):
            self.observed['components'][role]['running'] = False
        self.original = dict(id='JOB-882bad6add', action='promote-prod', target='prod', status='failed',
                             releaseTag=self.old_tag, effectsStarted=True,
                             error='Route snapshot READINESS blocked: test fixture',
                             workflowPolicy=dict(productionRecovery='external'),
                             originState=copy.deepcopy(self.origin),
                             runtimeStagingRoots=dict(prod='/attempts/JOB-882bad6add'),
                             remoteOperations=[dict(env='prod', action='deploy',
                                                    operationId='OP-22c6275633b1aeaa3cf7')],
                             migrationPlan=dict(items=[dict(migrationId='m1', sha256='a'*64, action='APPLY')]))
        self.package = dict(releaseTag=self.tag, stage='tested', baseline=False, directory='unit-only')
        self.manifest = dict(releaseTag=self.tag, migrations=[dict(migrationId='m1', sha256='a'*64)])
        self.plan = dict(status='passed', items=[dict(migrationId='m1', sha256='a'*64,
                                                     action='SKIP_ALREADY_APPLIED')])
        self.executor = object.__new__(IntRuoyiExecutor)
        self.executor.c = dict(runtimeKind='remote-intruoyi', releaseWorkflow=dict(
            version='direct-three-server-v1', productionRecovery='external',
            externalRecoveryConfirmed=True, note='unit contract'))
        self.executor.password = 'unit-secret'
        self.executor.state = dict(jobs=[self.original], environments=dict(prod=copy.deepcopy(self.origin)))
        self.executor.save = Mock()
        self.executor.log = Mock()
        self.executor.package = Mock(return_value=(self.package, self.manifest))
        self.executor.manifest = Mock(return_value=(dict(manifestSha256='old-manifest'), {}))
        self.executor.runtime = Mock(spec=Runtime)
        self.executor.runtime.observe.side_effect = lambda env:copy.deepcopy(self.observed)
        self.executor.runtime.audit.side_effect = lambda env, manifest:Runtime.audit(
            self.executor.runtime, env, manifest)
        self.executor.runtime.call.side_effect = self.inspect
        self.executor.deploy = Mock()
        self.executor.technical_verification_enabled = lambda:False
        self.plan_patch = patch('intruoyi_executor.target_input_plan', side_effect=lambda *args:copy.deepcopy(self.plan))
        self.plan_patch.start()
        self.addCleanup(self.plan_patch.stop)

    def inspect(self, env, action, *, manifest, incident):
        self.assertEqual((env, action), ('prod', 'inspect-stopped-origin'))
        observed = copy.deepcopy(self.observed)
        observed['releaseTag'] = validate_stopped_forward_origin(
            incident, observed, manifest['executionPlans']['prod']['items'], self.tag)
        return observed

    def execute(self, action='promote-prod'):
        job = dict(id='new', action=action, releaseTag=self.tag, payload={}, logs=[], status='running')
        self.executor.state['jobs'].insert(0, job)
        # This is the common dispatch used by the normal Spug action. The remote
        # deployment boundary stays mocked until entry authorization succeeds.
        Executor.execute(self.executor, job)
        return job

    def test_normal_entry_reaches_deployment_after_strict_stopped_origin_check(self):
        before = copy.deepcopy(self.executor.state['environments'])
        job = self.execute()
        self.assertEqual(job['status'], 'succeeded', job.get('error'))
        self.executor.runtime.audit.assert_not_called()
        self.executor.deploy.assert_called_once()
        self.assertEqual(job['stoppedOriginRecovery']['originalJobId'], self.original['id'])
        self.assertEqual(job['originState']['schemaSha256'], 'verified-schema')
        self.assertEqual(job['originFingerprint'], 'after-migrations')
        self.assertEqual(self.executor.state['environments'], before)

    def test_normal_entry_and_concrete_deploy_share_the_same_checked_origin(self):
        before = copy.deepcopy(self.executor.state['environments'])
        self.executor.deploy = MethodType(_IntRuoyiExecutor.deploy, self.executor)
        self.executor.direct_validation_basis = Mock(return_value=dict(
            sourceVerifiedSchemaSha256='verified-schema'))
        def deployed(env, manifest, callback, job_id):
            self.assertEqual(self.executor.state['environments'], before)
            self.assertEqual(manifest['baselines']['prod']['schemaSha256'], 'verified-schema')
            return dict(releaseTag=self.tag, schemaSha256='verified-schema', ledgerSha256='applied-ledger')
        self.executor.runtime.deploy.side_effect = deployed
        job = self.execute()
        self.assertEqual(job['status'], 'succeeded', job.get('error'))
        self.assertEqual(self.executor.runtime.call.call_count, 2)
        incidents = [call.kwargs['incident'] for call in self.executor.runtime.call.call_args_list]
        self.assertEqual(incidents[0], incidents[1])
        self.assertEqual(self.executor.state['environments']['prod']['releaseTag'], self.tag)
        self.executor.runtime.audit.assert_not_called()

    def test_running_origin_keeps_registered_baseline_audit(self):
        self.observed = copy.deepcopy(self.origin)
        job = self.execute()
        self.assertEqual(job['status'], 'succeeded', job.get('error'))
        self.executor.runtime.audit.assert_called_once()
        self.executor.runtime.call.assert_not_called()
        self.assertNotIn('stoppedOriginRecovery', job)

    def test_running_origin_schema_drift_is_not_a_stopped_origin_exception(self):
        self.observed['releaseTag'] = self.origin['releaseTag']
        job = self.execute()
        self.assertEqual(job['status'], 'failed')
        self.assertIn('Registered baseline mismatch: prod/schemaSha256', job['error'])
        self.executor.runtime.call.assert_not_called()
        self.executor.deploy.assert_not_called()

    def test_zero_or_multiple_failed_incidents_never_authorize_deployment(self):
        for count in (0, 2):
            with self.subTest(count=count):
                self.executor.state['jobs'] = [copy.deepcopy(self.original) for _ in range(count)]
                job = self.execute()
                self.assertEqual(job['status'], 'failed')
                self.assertIn('Exactly one reviewed failed production origin', job['error'])
                self.executor.deploy.assert_not_called()

    def test_pending_sql_or_changed_physical_origin_blocks_before_deployment(self):
        for problem in ('sql', 'image'):
            with self.subTest(problem=problem):
                self.setUp()
                if problem == 'sql':
                    self.plan['items'][0]['action'] = 'APPLY'
                else:
                    self.observed['images']['backend'] = 'other'
                job = self.execute()
                self.assertEqual(job['status'], 'failed')
                self.assertIn('zero pending SQL' if problem == 'sql' else 'Stopped origin changed', job['error'])
                self.executor.deploy.assert_not_called()

    def test_remote_correction_artifact_rejection_is_not_swallowed(self):
        self.executor.runtime.call.side_effect = RuntimeBlocked('Correction report is missing')
        job = self.execute()
        self.assertEqual(job['status'], 'failed')
        self.assertIn('Correction report is missing', job['error'])
        self.executor.deploy.assert_not_called()

    def test_other_environments_cannot_use_the_production_exception(self):
        for action, env in (('publish-test', 'test'), ('promote-backup', 'backup')):
            with self.subTest(env=env):
                self.executor.state['environments'][env] = copy.deepcopy(self.origin)
                job = self.execute(action)
                self.assertEqual(job['status'], 'failed')
                self.assertIn('Registered baseline mismatch: '+env+'/schemaSha256', job['error'])
                self.executor.runtime.call.assert_not_called()
                self.executor.deploy.assert_not_called()

    def test_deploy_rechecks_the_same_incident_and_rejects_binding_drift(self):
        for change in ('operation', 'origin', 'replacement'):
            with self.subTest(change=change):
                self.setUp()
                job = dict(action='promote-prod')
                self.executor.audit_deployment_origin('prod', self.package, self.manifest, job)
                if change == 'operation':
                    self.original['remoteOperations'][0]['operationId'] = 'OP-'+'1'*20
                elif change == 'origin':
                    self.original['originState']['images']['backend'] = 'other'
                else:
                    replacement = dict(copy.deepcopy(self.original), id='JOB-'+'1'*10)
                    self.original['resolution'] = dict(decision='external')
                    self.executor.state['jobs'].append(replacement)
                with self.assertRaisesRegex(ValueError, 'Stopped-origin.*changed'):
                    _IntRuoyiExecutor.deploy(self.executor, 'prod', self.package, self.manifest, job)
                self.executor.runtime.stage.assert_not_called()
                self.executor.runtime.deploy.assert_not_called()

    def test_deploy_rechecks_schema_ledger_drift_and_program_start(self):
        for field, value in (('schemaSha256', 'other'), ('ledgerSha256', 'other'),
                             ('releaseTag', self.origin['releaseTag'])):
            with self.subTest(field=field):
                self.setUp()
                job = dict(action='promote-prod')
                self.executor.audit_deployment_origin('prod', self.package, self.manifest, job)
                self.observed[field] = value
                with self.assertRaisesRegex(ValueError, 'Stopped-origin.*changed'):
                    _IntRuoyiExecutor.deploy(self.executor, 'prod', self.package, self.manifest, job)
                self.executor.runtime.stage.assert_not_called()
                self.executor.runtime.deploy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
