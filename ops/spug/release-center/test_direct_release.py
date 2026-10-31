"""Direct workflow contracts at explicit runtime boundaries; no live acceptance implied."""
import copy
import json
from pathlib import Path
import tempfile
from types import MethodType
import unittest
from unittest.mock import Mock, patch

import test_technical_verification as fixtures
from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime import package_identity, release_workflow, runtime_recovery_policy, RuntimeBlocked, sha
import intruoyi_runtime_agent as agent
from interruption import reconcile


POLICY = dict(version='direct-three-server-v1', productionRecovery='external',
              externalRecoveryConfirmed=True, note='Operator confirmed independent production backup and recovery')


class DirectReleaseTest(unittest.TestCase):
    setUp = fixtures.TechnicalVerificationTest.setUp
    observation = fixtures.TechnicalVerificationTest.observation
    run_action = fixtures.TechnicalVerificationTest.run_action

    def configure(self):
        self.executor.c['releaseWorkflow'] = copy.deepcopy(POLICY)
        self.package['directory'] = str(self.executor.root)
        self.executor.deploy = MethodType(IntRuoyiExecutor.deploy, self.executor)
        def deployed(env, manifest, callback, job_id):
            callback('runtime-deployment-effects', effects=True)
            return self.observation(maintenance=env != 'test')
        self.executor.runtime.deploy.side_effect = deployed

    def test_same_tested_package_can_complete_three_targets_without_rehearsal(self):
        self.configure()
        for action, payload in [('publish-test', {}), ('mark-tested', {}), ('promote-prod', {}),
                                ('accept-prod', {'note':'Approved read-only release acceptance'}),
                                ('promote-backup', {}), ('accept-backup', {'note':'Approved read-only release acceptance'})]:
            job = self.run_action(action, **payload)
            self.assertEqual(job['status'], 'succeeded', job.get('error'))
        self.assertEqual(self.package['stage'], 'completed')
        self.assertEqual(self.package['rehearsals'], [])
        self.assertNotIn('validatedProductionRehearsal', self.package)
        calls = self.executor.runtime.deploy.call_args_list
        self.assertEqual([call.args[0] for call in calls], ['test', 'prod', 'backup'])
        self.assertEqual([call.args[1]['workflowPolicy']['recoveryMode'] for call in calls],
                         ['checkpoint', 'external', 'checkpoint'])
        for env in ('test', 'prod', 'backup'):
            self.assertTrue(self.executor.technical_passed(self.package, env))
        basis = self.package['outcomes']['prod']['deployment']['validationBasis']
        self.assertEqual(basis['sourceEnvironment'], 'test')
        self.assertEqual(basis['packageSha256'], self.package['packageSha256'])

    def test_another_package_test_evidence_cannot_authorize_production(self):
        self.configure()
        self.assertEqual(self.run_action('publish-test')['status'], 'succeeded')
        self.package['outcomes']['test']['technical']['packageSha256'] = 'd'*64
        with self.assertRaisesRegex(ValueError, 'technical verification'):
            self.run_action('promote-prod')
        self.assertEqual(self.executor.runtime.deploy.call_count, 1)

    def test_successful_test_technical_retry_authorizes_same_package_without_redeploy(self):
        self.configure()
        self.login.side_effect=fixtures.LoginVerificationError('Real login failed')
        original=self.run_action('publish-test')
        self.assertEqual(original['status'],'failed')
        self.login.side_effect=lambda c,u,e,b:dict(status='passed',authenticated=True,binding=b)
        retried=self.run_action('mark-tested')
        self.assertEqual(retried['status'],'succeeded',retried.get('error'))
        production=self.run_action('promote-prod')
        self.assertEqual(production['status'],'succeeded',production.get('error'))
        self.assertEqual(self.executor.runtime.deploy.call_count,2)

    def test_each_target_uses_its_own_registered_origin_and_upgraded_schema(self):
        self.configure()
        self.assertEqual(self.run_action('publish-test')['status'], 'succeeded')
        self.executor.state['environments']['prod']['schemaSha256'] = 'different-schema'
        self.executor.state['environments']['prod']['ledgerSha256'] = 'different-ledger'
        def deployed(env,manifest,callback,job_id):
            callback('runtime-deployment-effects',effects=True)
            return dict(self.observation(maintenance=True),schemaSha256='prod-upgraded-schema')
        self.executor.runtime.deploy.side_effect=deployed
        job = self.run_action('promote-prod')
        self.assertEqual(job['status'], 'succeeded',job.get('error'))
        basis=self.package['outcomes']['prod']['deployment']['validationBasis']
        self.assertEqual(basis['targetOrigin']['schemaSha256'],'different-schema')
        self.assertEqual(basis['upgradedSchemaSha256'],'prod-upgraded-schema')
        self.assertNotIn('expectedSchemaSha256',self.executor.runtime.deploy.call_args.args[1])

    def test_failed_or_unaccepted_production_cannot_advance_backup(self):
        self.configure()
        self.run_action('publish-test')
        deployed = self.run_action('promote-prod')
        self.assertEqual(deployed['status'], 'succeeded', deployed.get('error'))
        with self.assertRaisesRegex(ValueError, 'business acceptance'):
            self.run_action('promote-backup')

    def test_tampered_bound_schema_cannot_open_production(self):
        self.configure()
        self.run_action('publish-test')
        deployed = self.run_action('promote-prod')
        self.assertEqual(deployed['status'], 'succeeded', deployed.get('error'))
        self.package['outcomes']['prod']['deployment']['validationBasis']['upgradedSchemaSha256'] = 'tampered'
        accepted = self.run_action('accept-prod', note='Approved read-only release acceptance')
        self.assertEqual(accepted['status'], 'failed')
        self.executor.maintenance.assert_not_called()

    def test_external_recovery_requires_explicit_operator_confirmation(self):
        self.configure()
        self.executor.c['releaseWorkflow']['externalRecoveryConfirmed'] = False
        with self.assertRaisesRegex((ValueError, RuntimeError), 'external recovery'):
            self.executor.runtime_manifest('prod', self.manifest)

    def test_runtime_workflow_adoption_preserves_original_package_identity(self):
        self.configure()
        self.manifest['legacyReadiness'] = {'fullDataRehearsalRequired':True}
        original = copy.deepcopy(self.manifest)
        runtime = self.executor.runtime_manifest('prod', self.manifest)
        self.assertIn('workflowPolicy', runtime)
        self.assertEqual(package_identity(runtime), package_identity(original))
        self.assertEqual(self.manifest, original)

    def test_external_production_cannot_invoke_spug_checkpoint_restore(self):
        self.configure()
        self.run_action('publish-test')
        deployed = self.run_action('promote-prod')
        self.assertEqual(deployed['status'], 'succeeded', deployed.get('error'))
        with self.assertRaisesRegex(ValueError, 'external recovery'):
            self.run_action('recover-release', jobId=deployed['id'], note='Restore using the independent mechanism')

    def test_retained_optional_rehearsal_does_not_become_a_required_stage(self):
        self.configure()
        self.run_action('publish-test')
        record = {'id':'retained', 'status':'passed', 'source':'prod', 'originalEvidence':'preserved'}
        self.package['rehearsals'] = [copy.deepcopy(record)]
        self.package['stage'] = 'rehearsal-passed'
        deployed = self.run_action('promote-prod')
        self.assertEqual(deployed['status'], 'succeeded', deployed.get('error'))
        self.assertEqual(self.package['rehearsals'], [record])

    def test_lost_production_reply_reconciles_same_receipt_without_rehearsal_or_redeploy(self):
        self.configure()
        self.run_action('publish-test')
        original=self.run_action('promote-prod')
        self.assertEqual(original['status'],'succeeded',original.get('error'))
        original['status']='interrupted'
        self.package['stage']='tested'
        deployment=self.package['outcomes']['prod']['deployment']
        deployment['status']='running'
        for key in ('upgradedSchemaSha256','upgradedLedgerSha256'):
            original['validationBasis'].pop(key)
            deployment['validationBasis'].pop(key)
        job=dict(id='reconcile-prod',requestId='reconcile-prod',action='reconcile-interruption',actor='operator',releaseTag=self.tag,
                 status='running',payload={'note':'Verify the original successful remote receipt'},logs=[])
        self.executor.state['jobs'].append(job)
        observed=copy.deepcopy(self.executor.state['environments']['prod'])
        evidence=dict(disposition='verify-deployment',observation=observed,detail='Original receipt succeeded',
                      deploymentReceipt={'result':observed})
        reconcile(self.executor,original,evidence,job)
        job['status']='succeeded'
        self.assertEqual(self.package['stage'],'prod-deployed')
        self.assertNotIn('rehearsalId',deployment)
        self.assertEqual(deployment['validationBasis']['upgradedSchemaSha256'],observed['schemaSha256'])
        accepted=self.run_action('accept-prod',note='Approved read-only release acceptance')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        backup=self.run_action('promote-backup')
        self.assertEqual(backup['status'],'succeeded',backup.get('error'))
        self.assertEqual(self.executor.runtime.deploy.call_count,3)


class ExternalRecoveryAgentTest(unittest.TestCase):
    def test_external_pre_migration_restoration_requires_unchanged_origin_and_no_sql(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            identity='a'*64
            observation=dict(fingerprint='origin',components={role:{'containerId':role} for role in ('backend','frontend','database')})
            record=dict(recoveryKind='external-pre-migration',restored=True,snapshotComplete=False,databaseRestored=False,
                jobId='JOB-'+ 'a'*10,restoredFingerprint='origin',operationId='OP-'+ 'b'*20,packageIdentity=identity,
                originalContainerIds={role:role for role in observation['components']})
            (root/'manual-recovery-confirmed.private.json').write_text(json.dumps(record),encoding='utf-8')
            (root/'external-recovery.private.json').write_text(json.dumps(dict(mode='external',operatorConfirmed=True,
                releaseTag='2026-10-31-22-23-14',originFingerprint='origin',packageIdentity=identity)),encoding='utf-8')
            payload=dict(action='verify-restoration',profile={'environment':'prod'},releaseTag='2026-10-31-22-23-14',jobId=record['jobId'],originFingerprint='origin')
            with patch.object(agent,'directory',return_value=root),patch.object(agent,'observe',return_value=observation), \
                    patch.object(agent.remote,'sql',return_value='0'), \
                    patch('operation_journal.inspect',return_value=dict(action='deploy',status='failed',worker='stopped')):
                self.assertEqual(agent.dispatch(payload)['recoveryEvidence'],record)
                with patch.object(agent.remote,'sql',return_value='1'),self.assertRaises(RuntimeBlocked):
                    agent.dispatch(payload)
                with patch.object(agent,'observe',return_value=dict(observation,fingerprint='drift')),self.assertRaises(RuntimeBlocked):
                    agent.dispatch(payload)
                (root/'backend-before-initial.private.json').touch()
                with self.assertRaises(RuntimeBlocked):
                    agent.dispatch(payload)

    def test_stopped_origin_uses_bound_identity_when_frontend_version_is_unavailable(self):
        original=dict(releaseTag='old',images={'backend':'a','frontend':'b'},fingerprint='origin',
                      schemaSha256='own-schema',ledgerSha256='own-ledger')
        basis=dict(targetEnvironment='prod',targetOrigin=original,migrationPlanSha256=sha([]))
        manifest={'workflowPolicy':dict(POLICY,targetEnvironment='prod',recoveryMode='external',validationBasis=basis)}
        profile=dict(environment='prod',writers=['backend'],frontend='frontend')
        stopped=dict(original,releaseTag=None)
        with patch.object(agent,'check_fence'),patch.object(agent.remote,'inspect',return_value={'State':{'Running':False}}):
            agent.validate_direct_target_origin(profile,manifest,stopped,[],quiescent=True)
            with self.assertRaisesRegex(RuntimeBlocked,'origin changed'):
                agent.validate_direct_target_origin(profile,manifest,dict(stopped,schemaSha256='drift'),[],quiescent=True)
        with patch.object(agent,'check_fence'),patch.object(agent.remote,'inspect',return_value={'State':{'Running':True}}),self.assertRaises(RuntimeBlocked):
            agent.validate_direct_target_origin(profile,manifest,stopped,[],quiescent=True)
        with self.assertRaisesRegex(RuntimeBlocked,'origin changed'):
            agent.validate_direct_target_origin(profile,manifest,stopped,[])

    def test_target_origin_or_plan_drift_is_rejected_before_migration(self):
        observed=dict(releaseTag='old',images={'backend':'a','frontend':'b'},fingerprint='origin',
                      schemaSha256='own-schema',ledgerSha256='own-ledger')
        basis=dict(targetEnvironment='prod',targetOrigin=observed,migrationPlanSha256=sha([]))
        manifest={'workflowPolicy':dict(POLICY,targetEnvironment='prod',recoveryMode='external',validationBasis=basis)}
        agent.validate_direct_target_origin({'environment':'prod'},manifest,observed,[])
        for key in observed:
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeBlocked,'origin changed'):
                agent.validate_direct_target_origin({'environment':'prod'},manifest,dict(observed,**{key:'drift'}),[])
        with self.assertRaisesRegex(RuntimeBlocked,'plan binding'):
            agent.validate_direct_target_origin({'environment':'prod'},manifest,observed,[{'action':'APPLY'}])

    def test_unknown_or_unconfirmed_external_policy_stops_before_writes(self):
        for policy in (dict(version='unknown'), dict(POLICY,externalRecoveryConfirmed=False)):
            with self.subTest(policy=policy), self.assertRaises(RuntimeBlocked):
                release_workflow({'releaseWorkflow':policy})
        for env in ('test','backup','rehearsal'):
            with self.subTest(env=env), self.assertRaises(RuntimeBlocked):
                runtime_recovery_policy(env, {'workflowPolicy':dict(POLICY,targetEnvironment=env,recoveryMode='external')})

    def test_external_migration_guard_requires_bound_ack_and_stopped_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'2026-10-31-22-23-14'
            root.mkdir()
            record=dict(mode='external',releaseTag=root.name,operatorConfirmed=True,
                        originFingerprint='origin',packageIdentity='a'*64)
            profile=dict(environment='prod',writers=['writer'])
            with patch.object(agent,'check_fence'), patch.object(agent.remote,'inspect',return_value={'State':{'Running':False}}):
                with self.assertRaises(RuntimeBlocked):
                    agent.require_migration_maintenance(profile,root,record)
                (root/'external-recovery.private.json').write_text(json.dumps(record),encoding='utf-8')
                agent.require_migration_maintenance(profile,root,record)
                with patch.object(agent.remote,'inspect',return_value={'State':{'Running':True}}), self.assertRaisesRegex(RuntimeBlocked,'Writer restarted'):
                    agent.require_migration_maintenance(profile,root,record)
                with self.assertRaises(RuntimeBlocked):
                    agent.require_migration_maintenance(dict(profile,environment='test'),root,record)

    def test_production_uses_external_recovery_without_running_full_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = dict(POLICY, recoveryMode='external', targetEnvironment='prod')
            manifest = dict(releaseTag='2026-10-31-22-23-14', migrations=[],
                            releaseSettings={'gxpAuditMode':'DEVELOPMENT_DISABLED'},
                            images={role:{'id':'sha256:'+'a'*64} for role in ('backend','frontend')},
                            expectedSchemaSha256='b'*64, workflowPolicy=policy)
            (root/'stage-verified.json').write_text(json.dumps({'manifestSha256':package_identity(manifest),'files':[]}), encoding='utf-8')
            profile = dict(environment='prod', backend='backend', frontend='frontend',writers=['backend'])
            observation = dict(releaseTag=manifest['releaseTag'], images={'backend':'sha256:'+'a'*64,'frontend':'sha256:'+'a'*64},
                               schemaSha256='b'*64,ledgerSha256='c'*64,fingerprint='origin')
            policy['validationBasis']=dict(targetEnvironment='prod',targetOrigin=observation,migrationPlanSha256=sha([]))
            names = ('preflight','verify_files','check_fence','stop_writers','apply_migration_plan',
                     'persist_gxp_release_mode','terminal_snapshot_readiness','replace','docker','acceptance_frontend')
            with patch.multiple(agent, **{name:Mock() for name in names}), \
                    patch.object(agent,'directory',return_value=root), \
                    patch.object(agent,'observe',return_value=observation), \
                    patch.object(agent,'migration_plan',return_value=[]), \
                    patch.object(agent,'health',return_value={'writerControls':{'gxpAuditMode':'DEVELOPMENT_DISABLED','configuredGxpAuditMode':'DEVELOPMENT_DISABLED'}}), \
                    patch.object(agent.remote,'run',return_value=('sha256:'+'a'*64).encode()), \
                    patch.object(agent.remote,'inspect',return_value={'State':{'Running':False}}), \
                    patch('intruoyi_recovery_agent.capture',return_value={'snapshotComplete':True}) as capture:
                result = agent.deploy(profile, manifest)
            self.assertEqual(capture.call_count, 0, 'Production must not capture a duplicate full recovery point')
            self.assertNotIn('recoveryPoint', result)
            self.assertEqual(result['externalRecovery']['mode'], 'external')
            self.assertTrue((root/'external-recovery.private.json').is_file())
            self.assertFalse((root/'recovery-record.private.json').exists())


if __name__ == '__main__':
    unittest.main()
