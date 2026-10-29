import copy
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

from executor import digest,require
from frontend_patch import FrontendPatchMixin
from frontend_patch_build import validate_source
from frontend_patch_agent import validate_origin,check_untouched,observation


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.tag='2026-10-28-12-00-00'
        self.base='2026-10-27-18-40-39'
        self.commit='a'*40
        self.folder=self.root/self.tag
        self.folder.mkdir()
        self.manifest=dict(kind='frontend-patch',releaseTag=self.tag,baseReleaseTag=self.base,images={'frontend':{'id':'sha256:new'}})
        (self.folder/'manifest.json').write_text(json.dumps(self.manifest))
        self.p=dict(releaseTag=self.tag,baseReleaseTag=self.base,directory=str(self.folder),
                    manifestSha256=digest(self.folder/'manifest.json'),stage='built',deployments={},accepted={})
        self.e=FrontendPatchMixin()
        self.e.c={'applicationId':'intruoyi','repo':str(self.root)}
        self.e.state=dict(frontendPatches=[self.p],packages=[],environments={env:dict(releaseTag=self.base) for env in ('test','prod','backup')},jobs=[])
        self.e.lock=threading.RLock()
        self.e.ensure_persistence=Mock()
        self.e.save=Mock()
        self.payload=dict(applicationId='intruoyi',requestId='request-1234',releaseTag=self.tag,target='prod',note='真实页面验证通过')

    def tearDown(self):self.temp.cleanup()

    def test_prod_requires_test_and_review_requires_current_accepted_prod(self):
        with self.assertRaisesRegex(ValueError,'测试服'):self.e.frontend_gate('frontend-patch-deploy',self.payload)
        self.p['accepted']['test']={'jobId':'test'}
        self.e.state['environments']['test']['frontendPatchTag']=self.tag
        self.e.frontend_gate('frontend-patch-deploy',self.payload)
        self.p['accepted']['prod']={'jobId':'prod'}
        review=dict(self.payload,target='backup')
        with self.assertRaisesRegex(ValueError,'同一补丁'):self.e.frontend_gate('frontend-patch-deploy',review)
        self.e.state['environments']['prod']['frontendPatchTag']=self.tag
        self.e.frontend_gate('frontend-patch-deploy',review)

    def test_duplicate_request_is_one_task_and_binds_payload(self):
        self.p['accepted']['test']=True
        self.e.state['environments']['test']['frontendPatchTag']=self.tag
        with patch('threading.Thread.start') as start:
            first=self.e.submit('frontend-patch-deploy',self.payload,'1')
            second=self.e.submit('frontend-patch-deploy',dict(self.payload),'1')
            self.assertIs(first,second)
            self.assertEqual(start.call_count,1)
            with self.assertRaisesRegex(ValueError,'请求编号'):self.e.submit('frontend-patch-deploy',dict(self.payload,note='更改请求参数'),'1')

    def test_shared_running_full_release_blocks_patch(self):
        self.e.state['jobs']=[dict(status='running',requestId='another-request')]
        with self.assertRaisesRegex(ValueError,'等待'):self.e.submit('frontend-patch-refresh',dict(self.payload),'1')

    def test_backend_source_change_is_not_a_frontend_patch(self):
        base={'gitCommit':'b'*40}
        self.e.run=Mock(side_effect=[self.commit.encode(),b'IntRuoyiBackend/sql/change.sql\n'])
        with self.assertRaisesRegex(ValueError,'后端及数据库'):validate_source(self.e,base,self.commit)
        self.e.run=Mock(side_effect=[self.commit.encode(),b'IntRuoyiFronted/src/utils/id.js\n'])
        self.assertEqual(validate_source(self.e,base,self.commit),['IntRuoyiFronted/src/utils/id.js'])

    def test_failed_effects_need_restoration_and_restoration_binds_original_target(self):
        failed=dict(id='JOB-1234567890',status='failed',effectsStarted=True,action='frontend-patch-deploy',target='prod',releaseTag=self.tag)
        self.e.state['jobs']=[failed]
        with self.assertRaisesRegex(ValueError,'未处理'):self.e.frontend_gate('frontend-patch-accept',self.payload)
        self.e.frontend_gate('frontend-patch-restore',dict(self.payload,originalJobId=failed['id']))
        with self.assertRaisesRegex(ValueError,'可恢复'):self.e.frontend_gate('frontend-patch-restore',dict(self.payload,target='test',originalJobId=failed['id']))

    def test_manifest_tampering_fails(self):
        (self.folder/'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'摘要'):self.e.frontend_package(self.tag)

    def test_reconciled_historical_failure_requires_existing_technical_proof(self):
        job=dict(id='JOB-old',status='failed',target='test',effectsStarted=True,releaseTag=self.base,reconciledBy='JOB-proof')
        self.e.state['packages']=[dict(releaseTag=self.base)]
        self.e.technical_passed=Mock(return_value=True)
        self.assertFalse(self.e.frontend_failure_blocks(job,'test'))
        self.e.technical_passed.assert_called_once_with(self.e.state['packages'][0],'test','JOB-proof')
        self.e.technical_passed.return_value=False
        self.assertTrue(self.e.frontend_failure_blocks(job,'test'))


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.actual=dict(releaseTag='base',frontendPatchTag=None,components={r:dict(containerId=r,imageId=r,startedAt='original') for r in ('frontend','backend','database')})
        self.manifest=dict(baseReleaseTag='base',releaseTag='patch',backendImageId='backend')

    def test_origin_rejects_wrong_backend_and_base_or_changed_frontend(self):
        validate_origin(self.actual,copy.deepcopy(self.actual),self.manifest,{'require':require})
        with self.assertRaisesRegex(ValueError,'起点'):validate_origin(self.actual,dict(self.actual,frontendPatchTag='other'),self.manifest,{'require':require})
        with self.assertRaisesRegex(ValueError,'主版本'):validate_origin(self.actual,self.actual,dict(self.manifest,baseReleaseTag='other'),{'require':require})
        with self.assertRaisesRegex(ValueError,'后端'):validate_origin(self.actual,self.actual,dict(self.manifest,backendImageId='other'),{'require':require})

    def test_untouched_check_rejects_backend_restart(self):
        after=copy.deepcopy(self.actual)
        after['components']['backend']['startedAt']='new'
        with self.assertRaisesRegex(ValueError,'外部变更'):check_untouched(self.actual,after,{'require':require})

    def test_observation_uses_container_metadata_and_no_database_query(self):
        remote=Mock()
        remote.inspect.side_effect=lambda name:dict(Id=name,Image=name,State={'Running':True,'StartedAt':'original'},NetworkSettings={'Networks':{'app':{'IPAddress':'172.21.0.5'}}})
        remote.run.return_value=json.dumps(dict(releaseTag='patch',baseReleaseTag='base',frontendPatchTag='patch')).encode()
        response=Mock(status=200)
        response.__enter__=Mock(return_value=response)
        response.__exit__=Mock(return_value=False)
        backend=io.BytesIO(b'{"status":"UP"}')
        backend.status=200
        with patch('frontend_patch_agent.urlopen',side_effect=[backend,response]):
            actual=observation(dict(frontend='f',backend='b',database='d',entryUrl='http://server'),{'remote':remote,'require':require})
        self.assertEqual(actual['releaseTag'],'base')
        self.assertEqual(actual['frontendPatchTag'],'patch')
        remote.sql.assert_not_called()


if __name__=='__main__':unittest.main()
