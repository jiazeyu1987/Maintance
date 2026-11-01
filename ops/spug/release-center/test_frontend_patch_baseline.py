import copy
import unittest
from unittest.mock import Mock

from frontend_patch import FrontendPatchMixin
from frontend_patch_agent import validate_origin
from frontend_patch_baseline import build_base, target_binding, validate_live_origin, validate_observations
from executor import require


class LiveBaselineTests(unittest.TestCase):
    def setUp(self):
        self.origins = {env: dict(releaseTag='2026-11-01-13-08-35', frontendPatchTag=None,
            metadata=dict(releaseTag='2026-11-01-13-08-35', sourceCommit='a'*40),
            components={role: dict(containerId=env+role, imageId='sha256:'+str(n)*64, startedAt='start')
                        for n, role in enumerate(('frontend','backend','database'), 1)},
            backendHealth='UP', frontendHttpStatus=200) for env in ('test','prod','backup')}
        self.e=FrontendPatchMixin()
        self.e.state=dict(packages=[],environments={},jobs=[])
        self.e.runtime=Mock()
        self.e.runtime.profile.side_effect=lambda env:dict(host=env,environment=env,entryUrl='http://'+env,
                                                          frontend='f',backend='b',database='d')
        self.e.save=Mock()
        self.e.step=Mock()
        self.e.log=Mock()
        self.e.frontend_call=Mock(side_effect=lambda job,env,action:copy.deepcopy(self.origins[env]))

    def register(self):
        job=dict(id='JOB-1234567890',action='frontend-patch-register-baseline',payload={})
        self.e.frontend_job(job)
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        return self.e.state['frontendPatchBaselines'][0]

    def test_registration_observes_twice_without_fabricating_full_release(self):
        b=self.register()
        self.assertEqual(self.e.frontend_call.call_count,6)
        self.assertEqual(b['gitCommit'],'a'*40)
        self.assertEqual(self.e.state['packages'],[])
        self.assertEqual(self.e.state['environments'],{})
        self.assertEqual(set(self.e.state['frontendPatchEnvironments']),{'test','prod','backup'})

    def test_changes_during_registration_do_not_save_baseline(self):
        original=self.e.frontend_call.side_effect
        count=0
        def observe(*args):
            nonlocal count
            count+=1
            result=original(*args)
            if count==4:result['components']['frontend']['startedAt']='new'
            return result
        self.e.frontend_call.side_effect=observe
        job=dict(id='JOB-1234567890',action='frontend-patch-register-baseline',payload={})
        self.e.frontend_job(job)
        self.assertEqual(job['status'],'failed')
        self.assertNotIn('frontendPatchBaselines',self.e.state)
        self.assertEqual(self.e.state['environments'],{})

    def test_mixed_three_server_versions_and_unknown_commit_rejected(self):
        for field,value in [('releaseTag','2026-10-01-00-00-00'),('backendHealth','DOWN')]:
            origins=copy.deepcopy(self.origins)
            origins['test'][field]=value
            with self.assertRaises(ValueError):validate_observations(origins)
        origins=copy.deepcopy(self.origins)
        origins['prod']['metadata']['sourceCommit']='unknown'
        with self.assertRaises(ValueError):validate_observations(origins)
        origins=copy.deepcopy(self.origins)
        origins['backup']['components']['backend']['imageId']='sha256:'+'f'*64
        with self.assertRaises(ValueError):validate_observations(origins)

    def test_explicit_selection_and_target_drift(self):
        b=self.register()
        self.e.manifest=Mock()
        base,context=build_base(self.e,dict(baselineId=b['id']))
        self.assertEqual(base['gitCommit'],'a'*40)
        self.e.manifest.assert_not_called()
        for payload in ({},{'baselineId':'missing'},{'baselineId':b['id'],'baseReleaseTag':b['releaseTag']}):
            with self.assertRaises(ValueError):build_base(self.e,payload)
        validate_live_origin(self.e,b,'test',self.origins['test'])
        with self.assertRaises(ValueError):validate_live_origin(self.e,b,'test',self.origins['prod'])
        b['targets']['test']['host']='another-host'
        with self.assertRaises(ValueError):validate_live_origin(self.e,b,'test',self.origins['test'])

    def test_remote_origin_is_bound_to_exact_target_at_deploy(self):
        b=self.register()
        manifest=dict(baseReleaseTag=b['releaseTag'],releaseTag='2026-11-01-20-00-00',
                      backendImageId=self.origins['test']['components']['backend']['imageId'],observedBaseline=b)
        validate_origin(self.origins['test'],self.origins['test'],manifest,dict(require=require,environment='test'))
        with self.assertRaises(ValueError):
            validate_origin(self.origins['test'],self.origins['test'],manifest,dict(require=require,environment='prod'))
        with self.assertRaises(ValueError):
            validate_origin(self.origins['test'],self.origins['test'],manifest,dict(require=require))

    def test_live_patch_records_remain_separate_from_full_release_baselines(self):
        b=self.register()
        self.e.record_frontend('test',self.origins['test'],observed=True)
        self.assertEqual(self.e.state['environments'],{})
        self.assertIs(self.e.frontend_targets(dict(observedBaseline=b)),self.e.state['frontendPatchEnvironments'])
        self.e.runtime.observe.assert_not_called()


if __name__=='__main__':unittest.main()
