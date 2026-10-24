"""Workflow components with explicit runtime/browser boundaries; no live acceptance implied."""
import copy
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).parent))
from intruoyi_executor import IntRuoyiExecutor
from intruoyi_login import LoginVerificationError


class TechnicalVerificationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.executor=object.__new__(IntRuoyiExecutor)
        self.executor.c={'runtimeKind':'remote-intruoyi','applicationId':'intruoyi','rehearsal':{'configured':True}}
        self.executor.root=Path(self.temp.name)
        self.executor.password='unit-private-value'
        self.executor.lock=threading.RLock()
        self.executor.save=Mock()
        self.executor.log=Mock()
        self.tag='2026-10-23-16-51-17'
        self.images={'backend':'sha256:'+'a'*64,'frontend':'sha256:'+'b'*64}
        self.manifest={'releaseTag':self.tag,'images':{role:{'id':value} for role,value in self.images.items()},'migrations':[]}
        self.package={'releaseTag':self.tag,'packageSha256':'c'*64,'stage':'built','baseline':False,'rehearsals':[]}
        self.executor.state={'packages':[self.package],'jobs':[],'environments':{
            env:dict(self.observation(),releaseTag='2026-10-22-00-00-00',fingerprint=env+'-origin') for env in ('test','prod','backup')}}
        self.executor.package=Mock(return_value=(self.package,self.manifest))
        self.executor.manifest=Mock(return_value=(self.package,self.manifest))
        self.executor.runtime=Mock()
        self.executor.runtime.observe.side_effect=lambda env:copy.deepcopy(self.executor.state['environments'][env])
        self.executor.runtime.profile.side_effect=lambda env:{'entryUrl':'http://172.30.30.58:8081','acceptanceUrl':'http://172.30.30.58:38084'}
        self.executor.audit_target=Mock(side_effect=lambda env,*args:{'observation':copy.deepcopy(self.executor.state['environments'][env])})
        self.executor.health=Mock(return_value={'healthy':True})
        def deploy(env,package,manifest,job):
            self.executor.state['environments'][env]=self.observation(maintenance=env!='test')
            if env=='prod':job['rehearsalId']=package['activeRehearsal']
            if env=='rehearsal': self.executor.active_rehearsal(package)['upgradedSchemaSha256']='schema'
            job['effectsStarted']=True
        self.executor.deploy=Mock(side_effect=deploy)
        self.events=[]
        def maintenance(env,enabled):
            self.events.append('open')
            self.executor.state['environments'][env]['maintenance']=enabled
        self.executor.maintenance=Mock(side_effect=maintenance)
        def login(config,target,evidence,binding):
            self.events.append('login')
            return {'status':'passed','authenticated':True,'binding':binding,'evidencePath':'sanitized.json'}
        self.login_patch=patch('intruoyi_login.verify_login',side_effect=login)
        self.login=self.login_patch.start()
        self.addCleanup(self.login_patch.stop)
        self.plan_patch=patch('intruoyi_executor.target_input_plan',return_value={'status':'passed','items':[]})
        self.plan=self.plan_patch.start()
        self.addCleanup(self.plan_patch.stop)

    def observation(self,maintenance=False):
        return dict(releaseTag=self.tag,images=self.images,schemaSha256='schema',ledgerSha256='ledger',
                    ledgerRecords=[],backendHealth={'status':'UP'},frontendHttpStatus=200,fingerprint='candidate-fingerprint',
                    maintenance=maintenance,readOnly={'read_only':False,'super_read_only':False})

    def run_action(self,action,**payload):
        with patch('executor.threading.Thread'):
            job=self.executor.submit(action,dict(applicationId='intruoyi',releaseTag=self.tag,
                requestId='request-'+str(len(self.executor.state['jobs'])),**payload),'operator')
        self.executor.execute(job)
        return job

    def seed_technical(self,env):
        job={'id':'proof-'+env,'requestId':'proof-'+env,'action':'accepted-proof','status':'succeeded','target':env,'releaseTag':self.tag}
        self.executor.state['jobs'].append(job)
        technical=dict(jobId=job['id'],env=env,releaseTag=self.tag,packageSha256=self.package['packageSha256'],status='passed',
                       checks={key:{'status':'passed'} for key in ('version','upgrade','login')})
        self.package.setdefault('outcomes',{}).setdefault(env,{})['technical']=technical
        self.package.setdefault('technicalHistory',[]).append(technical)
        return technical

    def seed_rehearsal(self):
        proof=self.seed_technical('rehearsal')
        record=dict(id='prod-copy',source='prod',status='passed',packageSha256=self.package['packageSha256'],
                    originFingerprint='prod-origin',upgradedSchemaSha256='schema',technical=proof)
        self.package['rehearsals']=[record]
        self.package['activeRehearsal']=record['id']
        self.package['stage']='rehearsal-passed'
        return record

    def test_successful_deploy_automatically_runs_all_three_and_advances(self):
        job=self.run_action('publish-test')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.package['stage'],'tested')
        self.assertEqual(self.package['outcomes']['test']['deployment']['status'],'succeeded')
        technical=self.package['outcomes']['test']['technical']
        self.assertEqual(technical['status'],'passed')
        self.assertTrue(all(check['status']=='passed' for check in technical['checks'].values()))
        self.assertEqual(self.login.call_args.args[3],dict(jobId=job['id'],env='test',releaseTag=self.tag,packageSha256='c'*64))
        self.assertNotIn('acceptances',self.package)

    def test_login_failure_keeps_true_deployment_and_retries_only_technical(self):
        self.login.side_effect=LoginVerificationError('Real browser login verification failed')
        first=self.run_action('publish-test')
        self.assertEqual(first['status'],'failed')
        self.assertTrue(first['effectsStarted'])
        self.assertEqual(self.package['stage'],'test-deployed')
        self.assertEqual(self.package['outcomes']['test']['deployment']['status'],'succeeded')
        self.assertEqual(self.package['outcomes']['test']['technical']['checks']['login']['status'],'failed')
        self.login.side_effect=lambda config,url,directory,binding:dict(status='passed',authenticated=True,binding=binding)
        retried=self.run_action('mark-tested')
        self.assertEqual(retried['status'],'succeeded',retried.get('error'))
        self.executor.deploy.assert_called_once()
        self.assertEqual(first['status'],'failed')
        self.assertEqual(first['reconciledBy'],retried['id'])
        self.assertNotIn('resolution',first)
        self.assertFalse(self.executor.failed_task_blocks(first,'prepare-rehearsal',{},self.package))

    def test_legacy_business_rejection_is_retained_and_requires_new_evidence(self):
        self.executor.state['environments']['test']=self.observation()
        self.package['stage']='test-deployed'
        self.package['outcomes']={'test':{'deployment':{'status':'succeeded','jobId':'old-deploy'},
                                        'acceptance':{'status':'failed','note':'original business details','jobId':'old-reject'}}}
        acceptance={'jobId':'old-reject','action':'reject-acceptance','env':'test','note':'original business details'}
        self.package['acceptances']=[acceptance]
        old=dict(id='old-reject',requestId='old-reject',action='reject-acceptance',status='failed',target='test',releaseTag=self.tag,
                 error='Business acceptance rejected: original business details',payload={'note':'original business details'})
        self.executor.state['jobs'].append(old)
        preserved=copy.deepcopy(self.package['outcomes']['test']['acceptance'])
        self.assertFalse(self.executor.technical_passed(self.package,'test'))
        job=self.run_action('mark-tested')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.package['outcomes']['test']['acceptance'],preserved)
        self.assertEqual(self.package['acceptances'],[acceptance])
        self.assertEqual(old['status'],'failed')
        self.assertEqual(old['error'],'Business acceptance rejected: original business details')
        self.assertEqual(old['reconciledBy'],job['id'])

    def test_wrong_image_and_pending_sql_never_reach_login_or_progress(self):
        self.executor.deploy.side_effect=lambda env,*args:self.executor.state['environments'].__setitem__(env,dict(self.observation(),images={'backend':'wrong','frontend':self.images['frontend']}))
        job=self.run_action('publish-test')
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.package['outcomes']['test']['technical']['checks']['version']['status'],'failed')
        self.login.assert_not_called()
        self.executor.state['environments']['test']=self.observation()
        self.plan.return_value={'status':'passed','items':[{'action':'APPLY'}]}
        job=self.run_action('mark-tested')
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.package['stage'],'test-deployed')
        self.login.assert_not_called()

    def test_missing_login_configuration_is_a_real_blocker(self):
        self.login_patch.stop()
        job=self.run_action('publish-test')
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.package['outcomes']['test']['technical']['checks']['login']['status'],'failed')
        self.assertNotEqual(self.package['stage'],'tested')

    def test_prod_stays_closed_until_explicit_business_acceptance(self):
        record=self.seed_rehearsal()
        job=self.run_action('promote-prod')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.events,['login'])
        self.assertEqual(self.package['stage'],'prod-deployed')
        self.assertTrue(self.executor.state['environments']['prod']['maintenance'])
        with self.assertRaisesRegex(ValueError,'business acceptance'):
            self.run_action('promote-backup')
        with self.assertRaisesRegex(ValueError,'acceptance note'):
            self.run_action('accept-prod')
        accepted=self.run_action('accept-prod',note='Actual business acceptance passed')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        self.assertEqual(self.events,['login','login','open'])
        self.assertEqual(self.login.call_args.args[1],'http://172.30.30.58:38084')
        self.assertEqual(self.package['stage'],'prod-accepted')
        self.assertEqual(self.package['validatedProductionRehearsal'],record['id'])
        self.assertEqual(self.package['outcomes']['prod']['acceptance']['jobId'],accepted['id'])
        self.assertEqual(len([row for row in self.package['acceptances'] if row['jobId']==accepted['id']]),1)

    def test_formal_acceptance_and_successful_job_are_saved_together(self):
        self.seed_rehearsal()
        self.run_action('promote-prod')
        snapshots=[]
        self.executor.save.side_effect=lambda:snapshots.append(copy.deepcopy(self.executor.state))
        accepted=self.run_action('accept-prod',note='Checked actual business data')
        committed=any(
            next((job for job in snapshot['jobs'] if job['id']==accepted['id']),{}).get('status')=='succeeded'
            and next((package for package in snapshot['packages'] if package['releaseTag']==self.tag),{})
                .get('outcomes',{}).get('prod',{}).get('acceptance',{}).get('status')=='passed'
            for snapshot in snapshots)
        self.assertTrue(committed,'Business acceptance and job success must be durably recorded in one save')

    def test_opening_failure_preserves_three_passes_but_never_accepts(self):
        self.seed_rehearsal()
        self.executor.maintenance.side_effect=ValueError('Opening health failed')
        self.run_action('promote-prod')
        job=self.run_action('accept-prod',note='Actual business acceptance passed')
        self.assertEqual(job['status'],'failed')
        technical=self.package['outcomes']['prod']['technical']
        self.assertEqual((technical['status'],technical['phase'],technical['opening']['status']),('failed','opening','failed'))
        self.assertTrue(all(item['status']=='passed' for item in technical['checks'].values()))
        self.assertEqual(self.package['stage'],'prod-deployed')
        self.assertEqual(self.package['outcomes']['prod']['deployment']['status'],'succeeded')
        with self.assertRaisesRegex(ValueError,'business acceptance'):
            self.run_action('promote-backup')

    def test_production_rehearsal_auto_passes_and_records_its_technical_evidence(self):
        self.seed_technical('test')
        record=self.seed_rehearsal()
        record['status']='ready'
        record.pop('technical')
        self.package['stage']='rehearsal-ready'
        self.executor.state['environments']['rehearsal']=dict(self.observation(),releaseTag='2026-10-22-00-00-00',fingerprint='prod-origin')
        job=self.run_action('upgrade-rehearsal')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.package['stage'],'rehearsal-passed')
        self.assertEqual(record['status'],'passed')
        self.assertEqual(record['technical']['jobId'],job['id'])
        self.assertTrue(self.executor.technical_passed(self.package,'rehearsal'))

    def test_backup_uses_same_accepted_production_then_opens_and_completes(self):
        record=self.seed_rehearsal()
        self.seed_technical('prod')
        self.executor.state['environments']['prod']=self.observation()
        self.package.update(stage='prod-accepted',validatedProductionRehearsal=record['id'])
        self.package['outcomes']['prod']['acceptance']={'status':'passed'}
        job=self.run_action('promote-backup')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        self.assertEqual(self.package['stage'],'backup-deployed')
        self.executor.maintenance.assert_not_called()
        accepted=self.run_action('accept-backup',note='Actual backup business acceptance passed')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        self.assertEqual(self.package['stage'],'completed')
        self.assertEqual(self.events,['login','login','open'])
        self.executor.maintenance.assert_called_once_with('backup',False)

    def test_formal_login_failure_never_opens_and_repeated_rechecks_remain_possible(self):
        self.seed_rehearsal()
        self.login.side_effect=LoginVerificationError('Login failed')
        original=self.run_action('promote-prod')
        retry=self.run_action('verify-prod')
        self.assertEqual((original['status'],retry['status']),('failed','failed'))
        self.executor.maintenance.assert_not_called()
        self.login.side_effect=lambda config,url,directory,binding:dict(status='passed',authenticated=True,binding=binding)
        success=self.run_action('verify-prod')
        self.assertEqual(success['status'],'succeeded',success.get('error'))
        self.executor.deploy.assert_called_once()
        self.assertEqual(original['reconciledBy'],success['id'])
        self.assertEqual(retry['reconciledBy'],success['id'])
        self.assertEqual(len(self.package['technicalHistory']),4)
        self.executor.maintenance.assert_not_called()

    def test_business_rejection_cannot_be_erased_by_technical_recheck(self):
        self.seed_rehearsal()
        self.run_action('promote-prod')
        rejected=self.run_action('reject-acceptance',note='Actual business function failed')
        self.assertEqual(rejected['status'],'failed')
        self.assertTrue(self.executor.state['environments']['prod']['maintenance'])
        with self.assertRaisesRegex(ValueError,'Unresolved failure'):
            self.run_action('verify-prod')
        with self.assertRaisesRegex(ValueError,'Failed task'):
            self.run_action('accept-prod',note='Trying to override a known rejection')
        with self.assertRaisesRegex(ValueError,'business acceptance'):
            self.run_action('promote-backup')
        self.executor.maintenance.assert_not_called()

    def test_wrong_environment_or_forged_reconciliation_is_not_technical_evidence(self):
        self.run_action('publish-test')
        proof=self.package['outcomes']['test']['technical']
        owner=self.executor.state['jobs'][0]
        owner['target']='backup'
        self.assertFalse(self.executor.technical_passed(self.package,'test'))
        blocked=dict(id='failed',status='failed',target='test',releaseTag=self.tag,reconciledBy=proof['jobId'])
        self.assertTrue(self.executor.failed_task_blocks(blocked,'prepare-rehearsal',{},self.package))

    def test_unrelated_failure_or_interruption_cannot_be_bypassed(self):
        job=self.run_action('publish-test')
        self.executor.state['jobs'].append(dict(id='unknown',requestId='unknown',status='failed',action='publish-test',releaseTag=self.tag,target='test'))
        with self.assertRaisesRegex(ValueError,'Failed task'): self.run_action('mark-tested')
        self.executor.state['jobs'][-1]['status']='interrupted'
        with self.assertRaisesRegex(ValueError,'Running/interrupted'): self.run_action('mark-tested')

    def test_old_pass_does_not_override_a_new_failed_recheck(self):
        self.run_action('publish-test')
        self.login.side_effect=LoginVerificationError('Login failed')
        job=self.run_action('mark-tested')
        self.assertEqual(job['status'],'failed')
        self.assertFalse(self.executor.technical_passed(self.package,'test'))
        with self.assertRaisesRegex(ValueError,'Passed technical'): self.run_action('prepare-rehearsal',source='prod')

    def test_completed_sql_technical_failure_cannot_enter_generic_restoration(self):
        self.login.side_effect=LoginVerificationError('Login failed')
        original=self.run_action('publish-test')
        job=dict(id='resolve',payload={'jobId':original['id'],'decision':'abandon','note':'investigated'},releaseTag=self.tag)
        with self.assertRaisesRegex(ValueError,'new technical verification action'):
            self.executor.resolve_task(job)
        self.assertNotIn('resolution',original)


if __name__=='__main__': unittest.main()
