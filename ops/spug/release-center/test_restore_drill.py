"""Restore drill workflow unit checks; no remote execution or claimed live E2E."""
import copy
import unittest
from unittest.mock import Mock, patch
import test_technical_verification as fixtures
from intruoyi_rehearsal_agent import drill_database_checksums
from intruoyi_runtime import require


class RestoreDrillTests(unittest.TestCase):
    observation = fixtures.TechnicalVerificationTest.observation
    run_action = fixtures.TechnicalVerificationTest.run_action

    def setUp(self):
        fixtures.TechnicalVerificationTest.setUp(self)
        self.package.update(stage='completed', activeRehearsal='drill-id',
                            outcomes={'prod':{'acceptance':{'status':'passed'}},'rehearsal':{'technical':{'old':'preserved'}}})
        self.record=dict(id='drill-id',purpose='restore-drill',status='restore-ready',captureJobId='capture-job',
                         source='prod',packageSha256=self.package['packageSha256'],
                         originFingerprint='candidate-fingerprint',originState={k:self.observation()[k] for k in ('releaseTag','images','schemaSha256','ledgerSha256')})
        self.package['rehearsals']=[self.record]
        self.executor.state['environments']['prod']=self.observation()
        self.executor.state['environments']['rehearsal']=dict(self.observation(), restoreDrillId='drill-id')
        self.executor.runtime.call.return_value={'status':'passed','tableCount':2,'encoding':'gzip'}
        self.prior_outcomes=copy.deepcopy(self.package['outcomes'])

    def test_verification_never_changes_release_or_approval(self):
        job=self.run_action('verify-restore-drill')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.package['stage'],'completed')
        self.assertEqual(self.package['outcomes'],self.prior_outcomes)
        self.assertEqual(self.record['status'],'restore-passed')
        self.executor.deploy.assert_not_called()
        self.executor.maintenance.assert_not_called()
        self.executor.runtime.prepare_rehearsal.assert_not_called()
        self.assertFalse(self.executor.verified_origin(self.package,'candidate-fingerprint'))

    def test_missing_database_proof_stops_before_login(self):
        self.executor.runtime.call.return_value={'status':'passed','tableCount':0}
        job=self.run_action('verify-restore-drill')
        self.assertEqual(job['status'],'failed')
        self.login.assert_not_called()
        self.assertEqual(self.package['outcomes'],self.prior_outcomes)

    def test_failed_login_can_retry_same_copy_without_recapture(self):
        self.login.side_effect=RuntimeError('login failed')
        original=self.run_action('verify-restore-drill')
        self.assertEqual(original['status'],'failed')
        self.login.side_effect=lambda c,u,e,b:dict(status='passed',authenticated=True,binding=b)
        retry=self.run_action('verify-restore-drill')
        self.assertEqual(retry['status'],'succeeded',retry.get('error'))
        self.assertEqual(original['resolution']['jobId'],retry['id'])
        self.executor.runtime.prepare_rehearsal.assert_not_called()

    def test_wrong_isolation_identity_rejected(self):
        self.executor.state['environments']['rehearsal']['restoreDrillId']='other'
        with self.assertRaisesRegex(ValueError,'Registered restored drill'):
            self.run_action('verify-restore-drill')

    def test_restore_drill_cannot_be_upgraded_or_used_as_upgrade_acceptance(self):
        for action in ('upgrade-rehearsal','accept-rehearsal'):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError,'cannot authorize'):
                self.run_action(action)

    def test_new_drill_requires_current_completed_production(self):
        self.executor.state['environments']['prod']['releaseTag']='another'
        with self.assertRaisesRegex(ValueError,'current completed'):
            self.run_action('prepare-rehearsal',source='prod',purpose='restore-drill')

    def test_purpose_cannot_bypass_normal_actions(self):
        with self.assertRaisesRegex(ValueError,'Unsupported operation purpose'):
            self.run_action('publish-test',purpose='restore-drill')

    def test_registration_keeps_original_outcomes(self):
        job=dict(id='new-drill',payload={'purpose':'restore-drill'})
        source=self.observation()
        result=dict(source,originFingerprint=source['fingerprint'],verifiedOrigin=True)
        self.executor.register_prepared_rehearsal(self.package,job,'prod',source,result)
        self.assertEqual(self.package['outcomes'],self.prior_outcomes)
        self.assertEqual(self.package['stage'],'completed')
        self.assertEqual(self.executor.active_rehearsal(self.package)['status'],'restore-ready')

    def test_prepare_completed_release_captures_checksums_without_deployment(self):
        self.executor.state['environments'].pop('rehearsal')
        self.package.pop('activeRehearsal')
        self.executor.runtime.targets={}
        result=dict(self.observation(),originFingerprint='candidate-fingerprint',verifiedOrigin=True,
                    remotePreparationProgress={'status':'succeeded','phase':'completed'})
        self.executor.runtime.prepare_rehearsal.return_value=result
        with patch('intruoyi_executor.rehearsal_profile',return_value={}):
            job=self.run_action('prepare-rehearsal',source='prod',purpose='restore-drill')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertTrue(self.executor.runtime.prepare_rehearsal.call_args.kwargs['verify_data'])
        self.assertEqual(self.package['stage'],'completed')
        self.assertEqual(self.package['outcomes'],self.prior_outcomes)
        self.executor.deploy.assert_not_called()


class DatabaseProofTests(unittest.TestCase):
    def test_all_tables_including_showroom_checked_in_batches(self):
        remote=Mock()
        names=['showroom_release_asset']+['table_'+str(n) for n in range(40)]
        def sql(profile, query):
            if query=='SHOW TABLES;': return '\n'.join(names)
            if query.startswith('SELECT'): return '\n'.join(names)
            batch=query[len('CHECKSUM TABLE '):-len(' EXTENDED;')].replace('`','').split(',')
            return '\n'.join('db.'+name+'\t123' for name in batch)
        remote.sql.side_effect=sql
        self.assertEqual(set(drill_database_checksums({},remote,require)),set(names))
        self.assertEqual(remote.sql.call_count,4)

    def test_unavailable_checksum_cannot_pass(self):
        remote=Mock();remote.sql.side_effect=['a','a','db.a\tNULL']
        with self.assertRaisesRegex(RuntimeError,'unavailable'):
            drill_database_checksums({},remote,require)

    def test_missing_table_cannot_pass(self):
        remote=Mock();remote.sql.side_effect=['a\nb','a\nb','db.a\t1']
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            drill_database_checksums({},remote,require)


if __name__=='__main__': unittest.main()
