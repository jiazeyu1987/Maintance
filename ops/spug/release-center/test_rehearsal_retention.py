"""Completed isolation handover unit contracts; never remote acceptance evidence."""
import copy
import unittest
from unittest.mock import Mock

from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime import Runtime, rehearsal_profile
from rehearsal_retention import registered_rehearsal_profile


class RehearsalRetentionTests(unittest.TestCase):
    def setUp(self):
        def profile(prefix, port):
            p = {key: prefix+'-'+key for key in
                 ('frontend','backend','database','redis','minio','acceptanceFrontend','network','gateway')}
            return dict(p, host='172.30.30.58', python='/usr/bin/python3', environment='rehearsal',
                        entryUrl='http://172.30.30.58:'+str(port),
                        acceptanceUrl='http://172.30.30.58:'+str(port+1),
                        isolatedMinioPublicUrl='http://172.30.30.58:'+str(port+2))
        self.c = dict(targets={'rehearsal':profile('intruoyi-release-rehearsal-new',38094)},
                      rehearsalStagingRoots={'prod':'/workflow/new/packages'})
        old_c = dict(targets={'rehearsal':profile('intruoyi-release-rehearsal-old',38090)},
                     rehearsalStagingRoots={'prod':'/workflow/old/packages'})
        self.old_profile = rehearsal_profile(old_c,'prod')
        self.old = dict(releaseTag='old', fingerprint='old-fingerprint', sourceEnvironment='prod',
                        entryUrl=self.old_profile['entryUrl'],host='172.30.30.58',
                        images={'backend':'sha256:'+'a'*64,'frontend':'sha256:'+'b'*64},
                        schemaSha256='schema', ledgerSha256='ledger', ledgerRecords=[],
                        backendHealth={'status':'UP'},frontendHttpStatus=200)
        old_record = dict(id='old-capture',jobId='old-capture',source='prod',status='passed',
                          packageSha256='old-package',technical={'status':'passed'})
        self.old_package = dict(releaseTag='old',packageSha256='old-package',stage='completed',
                                activeRehearsal='old-capture',rehearsals=[old_record])
        self.package = dict(releaseTag='new',packageSha256='new-package',stage='tested')
        self.c['rehearsalRetention'] = dict(rehearsalId='old-capture',releaseTag='old',
                                           fingerprint='old-fingerprint',profile=self.old_profile)
        e = self.e = object.__new__(IntRuoyiExecutor)
        e.c=self.c
        e.state=dict(environments={'rehearsal':copy.deepcopy(self.old),'prod':{'releaseTag':'old'}},
                     packages=[self.old_package,self.package],jobs=[])
        e.runtime=Runtime(self.c)
        e.runtime.targets['rehearsal']=copy.deepcopy(self.old_profile)
        origin=dict(self.old,fingerprint='prod-fingerprint')
        e.runtime.observe=Mock(side_effect=lambda env:copy.deepcopy(self.old if env=='rehearsal' else origin))
        e.runtime.prepare_rehearsal=Mock(return_value=dict(origin,originFingerprint='prod-fingerprint',
                                      verifiedOrigin=True,entryUrl=self.c['targets']['rehearsal']['entryUrl'],
                                      remotePreparationProgress={'status':'completed'}))
        e.runtime.reset_rehearsal=Mock()
        e.manifest=Mock(return_value=(self.package,{}))
        e.save=Mock()
        e.step=Mock()
        e.log=Mock()
        self.job=dict(id='new-capture',payload={'source':'prod'},releaseTag='new')

    def test_prepare_preserves_old_resources_history_and_profile_before_new_registration(self):
        old_package=copy.deepcopy(self.old_package)
        config=copy.deepcopy(self.c)
        self.e.prepare(self.package,self.job)
        self.assertEqual(self.old_package,old_package)
        self.assertEqual(self.c,config)
        retained=self.e.state['retainedRehearsals']
        self.assertEqual(len(retained),1)
        self.assertEqual(retained[0]['environment'],self.old)
        self.assertEqual(retained[0]['profile'],self.old_profile)
        self.assertEqual(retained[0]['rehearsalId'],'old-capture')
        self.assertEqual(self.e.state['environments']['rehearsal']['resourceProfile'],
                         rehearsal_profile(self.c,'prod'))
        self.e.runtime.reset_rehearsal.assert_not_called()
        self.e.runtime.prepare_rehearsal.assert_called_once()

    def test_unbound_or_incomplete_or_drifted_old_isolation_blocks_before_state_change(self):
        for variant in ('missing','id','package','stage','status','fingerprint','live'):
            with self.subTest(variant=variant):
                self.setUp()
                if variant=='missing':self.c.pop('rehearsalRetention')
                elif variant=='id':self.c['rehearsalRetention']['rehearsalId']='other'
                elif variant=='package':self.old_package['rehearsals'][0]['packageSha256']='other'
                elif variant=='stage':self.old_package['stage']='prod-deployed'
                elif variant=='status':self.old_package['rehearsals'][0]['status']='upgraded'
                elif variant=='fingerprint':self.c['rehearsalRetention']['fingerprint']='other'
                else:self.old['fingerprint']='live-drift'
                before=copy.deepcopy(self.e.state)
                with self.assertRaises((ValueError,RuntimeError)):self.e.prepare(self.package,self.job)
                self.assertEqual(self.e.state,before)
                self.e.runtime.prepare_rehearsal.assert_not_called()
                self.e.runtime.reset_rehearsal.assert_not_called()

    def test_resource_port_and_staging_overlap_blocks_before_handover(self):
        for key in ('backend','network','gateway','entryUrl','acceptanceUrl','isolatedMinioPublicUrl','staging'):
            with self.subTest(key=key):
                self.setUp()
                if key=='staging':self.c['rehearsalStagingRoots']['prod']='/workflow/old/packages/new'
                else:self.c['targets']['rehearsal'][key]=self.old_profile[key]
                before=copy.deepcopy(self.e.state)
                with self.assertRaises((ValueError,RuntimeError)):self.e.prepare(self.package,self.job)
                self.assertEqual(self.e.state,before)
                self.e.runtime.prepare_rehearsal.assert_not_called()

    def test_failed_new_preparation_keeps_retained_evidence_and_never_resets_old_resources(self):
        old_package=copy.deepcopy(self.old_package)
        self.e.runtime.prepare_rehearsal.side_effect=RuntimeError('real preparation failed')
        with self.assertRaisesRegex(RuntimeError,'real preparation failed'):
            self.e.prepare(self.package,self.job)
        self.assertEqual(self.old_package,old_package)
        self.assertEqual(self.e.state['retainedRehearsals'][0]['environment'],self.old)
        self.assertNotIn('rehearsal',self.e.state['environments'])
        self.e.runtime.reset_rehearsal.assert_not_called()

    def test_explicitly_retained_active_environment_cannot_be_reset(self):
        with self.assertRaisesRegex((ValueError,RuntimeError),'retain|preserv'):
            self.e.reset_rehearsal(self.job)
        self.e.runtime.reset_rehearsal.assert_not_called()
        self.assertEqual(self.e.state['environments']['rehearsal'],self.old)

    def test_runtime_profile_selection_does_not_mutate_configuration(self):
        before=copy.deepcopy(self.c)
        self.e.runtime.targets['rehearsal']['entryUrl']='http://172.30.30.58:39000'
        self.assertEqual(self.c,before)

    def test_registered_profile_remains_old_until_new_registration_survives_restart(self):
        self.assertEqual(registered_rehearsal_profile(self.c,self.old),self.old_profile)
        self.e.prepare(self.package,self.job)
        environment=self.e.state['environments']['rehearsal']
        self.assertEqual(registered_rehearsal_profile(self.c,environment),rehearsal_profile(self.c,'prod'))
        environment['entryUrl']='http://172.30.30.58:39999'
        with self.assertRaisesRegex(RuntimeError,'resource profile differs'):
            registered_rehearsal_profile(self.c,environment)

    def test_new_environment_without_old_registration_uses_existing_prepare_flow(self):
        self.e.state['environments'].pop('rehearsal')
        self.c.pop('rehearsalRetention')
        self.e.prepare(self.package,self.job)
        self.assertNotIn('retainedRehearsals',self.e.state)
        self.assertEqual(self.package['activeRehearsal'],self.job['id'])
        self.e.runtime.observe.assert_any_call('prod')


if __name__=='__main__':unittest.main()
