import copy
import threading
import unittest
from unittest.mock import patch
from intruoyi_executor import IntRuoyiExecutor

class RegistrationHistoryTest(unittest.TestCase):
    def fixture(self):
        old=dict(id='old',requestId='old-req',action='publish-test',target='test',status='failed',effectsStarted=True,releaseTag='old-tag',finishedAt='2026-01-01-12-00-00',currentStep='technical-login')
        new=dict(id='new',requestId='new-req',action='publish-test',target='test',status='succeeded',releaseTag='new-tag',createdAt='2026-01-02-12-00-00',finishedAt='2026-01-02-13-00-00')
        packages=[]
        for job in (old,new):
            proof=dict(jobId=job['id'],env='test',releaseTag=job['releaseTag'],packageSha256=job['id']+'-digest',status='failed' if job is old else 'passed',checks={k:{'status':'failed' if job is old and k=='login' else 'passed'} for k in ('version','upgrade','login')})
            job['technicalVerification']=proof
            packages.append(dict(releaseTag=job['releaseTag'],packageSha256=proof['packageSha256'],outcomes={'test':{'deployment':{'status':'succeeded','jobId':job['id']}}},technicalVerifications=[copy.deepcopy(proof)]))
        executor=IntRuoyiExecutor.__new__(IntRuoyiExecutor)
        executor.c={'applicationId':'intruoyi'};executor.lock=threading.RLock()
        executor.ensure_persistence=lambda:None;executor.save=lambda:None
        executor.state=dict(jobs=[new,old],packages=packages,environments={})
        return executor,old,new

    def submit(self,executor):
        with patch('intruoyi_executor.threading.Thread'):
            return executor.submit('register-targets',{'applicationId':'intruoyi','requestId':'history-registration','target':'test'},'actor')

    def test_later_verified_deployment_allows_registration_preserving_failure(self):
        executor,old,new=self.fixture();before=copy.deepcopy(old)
        result=self.submit(executor)
        self.assertEqual(result['status'],'running')
        self.assertEqual(old,before)

    def test_incomplete_wrong_target_wrong_identity_or_older_evidence_still_blocks(self):
        for case in ('migration','target','digest','early','unfinished','missing_package','deployment','login'):
            executor,old,new=self.fixture()
            if case=='migration':old['technicalVerification']['checks']['upgrade']['status']='failed'
            if case=='target':new['target']='prod'
            if case=='digest':new['technicalVerification']['packageSha256']='wrong'
            if case=='early':new['createdAt']='2025-01-01-00-00-00'
            if case=='unfinished':new['status']='failed'
            if case=='missing_package':executor.state['packages']=[]
            if case=='deployment':executor.state['packages'][0]['outcomes']['test']['deployment']['status']='failed'
            if case=='login':new['technicalVerification']['checks']['login']['status']='failed'
            with self.subTest(case=case),self.assertRaisesRegex(ValueError,'Failed remote effects'):
                self.submit(executor)

if __name__=='__main__':unittest.main()
