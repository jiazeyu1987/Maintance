"""Retention unit contracts, including actual temporary-file deletion.

Remote responses are controlled unit boundaries, not deployment/E2E evidence.
"""
import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import artifact_files as files
import artifact_retention as retention
from executor import Executor
from intruoyi_executor import IntRuoyiExecutor
from release_order import deployment_block

TAGS=['2026-10-2'+str(i)+'-01-00-00' for i in range(1,6)]


class FileTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'package';self.root.mkdir()
        (self.root/'release.tar').write_bytes(b'archive content')
        (self.root/'images.tar').write_bytes(b'image content')
        self.manifest=dict(releaseTag=TAGS[0],files=[dict(name='images.tar',sha256=files.sha(self.root/'images.tar'))])
        (self.root/'manifest.json').write_text(json.dumps(self.manifest),'utf-8')
        self.digest=files.sha(self.root/'manifest.json');self.archive=files.sha(self.root/'release.tar')

    def rows(self):return files.inventory(self.root,self.manifest,self.digest,self.archive)

    def test_remove_only_selected_declared_file_preserves_metadata_and_unknown_file(self):
        other=self.root/'keep.private.json';other.write_text('keep','utf-8')
        rows=self.rows();files.remove_file(self.root,rows[0])
        self.assertFalse((self.root/'release.tar').exists())
        self.assertTrue((self.root/'images.tar').exists())
        self.assertEqual(files.sha(self.root/'manifest.json'),self.digest)
        self.assertEqual(other.read_text('utf-8'),'keep')
        self.assertEqual(len(self.rows()),1)

    def test_changed_bytes_cannot_be_deleted(self):
        row=self.rows()[0];(self.root/row['relative']).write_bytes(b'new content')
        with self.assertRaisesRegex(ValueError,'变化'):files.remove_file(self.root,row)
        self.assertTrue((self.root/row['relative']).exists())

    def test_wrong_registered_hash_cannot_be_deleted_even_with_matching_stat(self):
        row=self.rows()[0];row['sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'摘要'):files.remove_file(self.root,row)

    def test_path_escape_and_symlink_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'路径'):files.safe_file(self.root,'../outside')
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaisesRegex(ValueError,'链接'):files.safe_file(self.root,'release.tar')

    def test_nas_only_original_archive(self):
        rows=files.inventory(self.root,self.manifest,self.digest,self.archive,archive_only=True)
        self.assertEqual([r['relative'] for r in rows],['release.tar'])

    def test_mismatched_manifest_is_classified_as_retained_not_deletable(self):
        rows=files.inventory(self.root,self.manifest,'0'*64,self.archive)
        self.assertEqual(len(rows),1)
        self.assertIn('清单与登记包身份不一致',rows[0]['retainedReason'])
        with self.assertRaisesRegex(ValueError,'禁止删除'):files.remove_file(self.root,rows[0])

    def test_missing_manifest_directory_is_unknown_and_retained(self):
        (self.root/'manifest.json').unlink()
        rows=self.rows()
        self.assertIsNone(rows[0]['bytes'])
        self.assertTrue(rows[0]['unmeasured'])
        with self.assertRaisesRegex(ValueError,'禁止删除'):files.remove_file(self.root,rows[0])

    def test_recovery_ownership_required_and_records_preserved(self):
        (self.root/'recovery.sql').write_bytes(b'owned snapshot')
        record=dict(releaseTag=TAGS[0],jobId='JOB-owner',manifestSha256=self.digest,packageSha256=self.archive,path=str(self.root/'recovery.sql'),sha256=files.sha(self.root/'recovery.sql'),resources=[])
        marker=self.root/'recovery-record.private.json';marker.write_text(json.dumps(record),'utf-8')
        rows=files.inventory(self.root,self.manifest,self.digest,self.archive,recovery=True,recovery_jobs=['JOB-owner'])
        recovery=next(r for r in rows if r['relative']=='recovery.sql');files.remove_file(self.root,recovery)
        self.assertTrue(marker.exists())
        record['releaseTag']=TAGS[1];marker.write_text(json.dumps(record),'utf-8')
        with self.assertRaisesRegex(ValueError,'恢复点'):files.inventory(self.root,self.manifest,self.digest,self.archive,recovery=True,recovery_jobs=['JOB-owner'])

    def test_legacy_recovery_is_visible_but_never_deletable(self):
        (self.root/'recovery.sql').write_bytes(b'legacy')
        (self.root/'recovery-record.private.json').write_text(json.dumps(dict(path=str(self.root/'recovery.sql'),sha256=files.sha(self.root/'recovery.sql'))),'utf-8')
        rows=files.inventory(self.root,self.manifest,self.digest,self.archive,recovery=True)
        self.assertTrue(all(row.get('retainedReason') for row in rows))
        with self.assertRaisesRegex(ValueError,'禁止删除'):files.remove_file(self.root,rows[-1])

    def test_image_remove_uses_named_tag_without_force_or_prune(self):
        with patch.object(files,'docker_inventory',return_value=({'app:old':'sha256:old'},set(),[])),patch.object(files,'docker') as command:
            files.remove_image('app:old','sha256:old')
            command.assert_called_once_with(['image','rm','--','app:old'])
        with patch.object(files,'docker_inventory',return_value=({'app:old':'sha256:old'},{'sha256:old'},[])),patch.object(files,'docker') as command:
            with self.assertRaisesRegex(ValueError,'引用'):files.remove_image('app:old','sha256:old')
            command.assert_not_called()

    def test_remote_delete_uses_registered_root_and_rechecks_actual_images(self):
        tagged=self.root.parent/TAGS[0];self.root.rename(tagged);self.root=tagged
        entry=dict(manifest=self.manifest,manifestSha256=self.digest,packageSha256=self.archive)
        profile=dict(stagingRoot=str(tagged.parent),backend='app',frontend='web')
        item=dict(kind='file',root=str(tagged),releaseTag=TAGS[0],file=self.rows()[0])
        payload=dict(action='artifact-remove',entries=[entry],item=item,expectedImages=dict(backend='backend-id',frontend='frontend-id'))
        with patch.object(files,'docker_inventory',return_value=({},set(),[])),patch.object(files,'docker',return_value=b'changed-backend\nfrontend-id\n'):
            with self.assertRaisesRegex(ValueError,'版本'):files.remote(profile,payload)
        self.assertTrue((tagged/'release.tar').exists())
        with patch.object(files,'docker_inventory',return_value=({},set(),[])),patch.object(files,'docker',return_value=b'backend-id\nfrontend-id\n'):
            self.assertEqual(files.remote(profile,payload),{'removed':True})
        self.assertFalse((tagged/'release.tar').exists())
        self.assertTrue((tagged/'manifest.json').exists())

    def test_remote_delete_refuses_container_mounted_files(self):
        tagged=self.root.parent/TAGS[0];self.root.rename(tagged);self.root=tagged
        entry=dict(manifest=self.manifest,manifestSha256=self.digest,packageSha256=self.archive)
        item=dict(kind='file',root=str(tagged),releaseTag=TAGS[0],file=self.rows()[0])
        with patch.object(files,'docker_inventory',return_value=({},set(),[str(tagged)])),patch.object(files,'docker',return_value=b'b\nf\n'):
            with self.assertRaisesRegex(ValueError,'挂载'):
                files.remote(dict(stagingRoot=str(tagged.parent),backend='app',frontend='web'),dict(action='artifact-remove',entries=[entry],item=item,expectedImages=dict(backend='b',frontend='f')))
        self.assertTrue((tagged/'release.tar').exists())


class RetentionTest(unittest.TestCase):
    def setUp(self):
        self.state=dict(packages=[dict(releaseTag=t,stage='completed') for t in TAGS],environments={},
            jobs=[dict(id='JOB-prod',action='promote-prod',releaseTag=TAGS[-1],status='succeeded',originState={'releaseTag':TAGS[2]})])
        self.obs={e:dict(releaseTag=TAGS[-1],maintenance=False) for e in ('test','prod','backup')}

    def test_current_previous_and_latest_are_protected(self):
        rows=retention.protections(self.state,self.obs,2)
        self.assertFalse(rows[TAGS[0]])
        for tag in TAGS[2:]:self.assertTrue(rows[tag])

    def test_recovery_pending_is_not_erased_by_live_observation(self):
        self.state['environments']['test']=dict(releaseTag=TAGS[-1],recoveryPending=True)
        self.assertTrue(all(retention.protections(self.state,self.obs,2).values()))

    def test_isolation_maintenance_does_not_protect_unrelated_old_artifacts(self):
        self.state['environments']['rehearsal']=dict(releaseTag=TAGS[-1],maintenance=True)
        self.assertFalse(retention.protections(self.state,self.obs,2)[TAGS[0]])

    def test_pending_and_failed_release_origins_are_kept(self):
        self.state['jobs'].append(dict(id='JOB-failed',action='publish-test',status='failed',releaseTag=TAGS[1],originState={'releaseTag':TAGS[0]}))
        rows=retention.protections(self.state,self.obs,2)
        self.assertTrue(rows[TAGS[0]]);self.assertTrue(rows[TAGS[1]])

    def test_diagnostics_do_not_reserve_versions(self):
        self.state['jobs'].append(dict(id='JOB-check',action='check-prerequisites',status='failed',releaseTag=TAGS[0]))
        self.assertFalse(retention.protections(self.state,self.obs,2)[TAGS[0]])

    def test_retired_package_cannot_redeploy_but_manifest_remains_auditable(self):
        package=dict(releaseTag=TAGS[-1],artifactsPruned={'jobId':'cleanup'})
        self.assertIn('ARTIFACTS_RETIRED',deployment_block('publish-test',package,{}))
        executor=object.__new__(Executor);executor.manifest=Mock(return_value=(package,{}))
        with self.assertRaisesRegex(ValueError,'退役'):executor.package(TAGS[-1])

    def test_confirm_scope_and_single_use_preview(self):
        executor=object.__new__(IntRuoyiExecutor)
        executor.lock=threading.RLock();executor.worker=None;executor.save=Mock()
        executor.c=dict(applicationId='intruoyi');executor.ensure_persistence=Mock()
        scan=dict(id='JOB-scan',action='scan-artifacts',status='succeeded',result=dict(complete=True,scannedEpoch=time.time(),items=[dict(id='allowed',location='nas',releaseTag='old',reasons=[]),dict(id='protected',location='nas',releaseTag='current',reasons=['current'])]))
        executor.state=dict(jobs=[scan]);payload=dict(applicationId='intruoyi',requestId='request-1',scanJobId='JOB-scan',confirmation='确认清理',groups=['nas:current'])
        with self.assertRaisesRegex(ValueError,'受保护'):retention.submit(executor,'clean-artifacts',payload,'unit')
        payload['groups']=['nas:old'];payload['confirmation']=''
        with self.assertRaisesRegex(ValueError,'确认清理'):retention.submit(executor,'clean-artifacts',payload,'unit')
        payload['confirmation']='确认清理'
        with patch.object(retention.threading,'Thread'):
            job=executor.submit('clean-artifacts',payload,'unit')
            self.assertIs(executor.submit('clean-artifacts',dict(payload),'unit'),job)
            self.assertEqual(job['selectedItems'],['allowed'])
        job['status']='failed';executor.worker=None
        with self.assertRaisesRegex(ValueError,'已用于'):retention.submit(executor,'clean-artifacts',payload,'unit')

    def test_partial_failure_records_completed_items_and_retirement(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);items=[]
            for i in range(2):
                p=root/str(i);p.write_bytes(b'owned data')
                row=dict(relative=str(i),sha256=files.sha(p),**files.file_identity(p))
                items.append(dict(id=str(i),location='nas',kind='file',root=str(root),file=row,releaseTag=TAGS[0],tags=[TAGS[0]],reasons=[],label=str(i)))
            items[1]['file']['sha256']='0'*64
            report=dict(complete=True,keepLatest=2,items=items)
            old=dict(id='JOB-scan',result=report)
            job=dict(action='clean-artifacts',id='JOB-clean',payload=dict(scanJobId='JOB-scan'),selectedItems=['0','1'])
            e=Mock();e.c={};e.state=dict(jobs=[job,old],packages=[dict(releaseTag=TAGS[0])])
            with patch.object(retention,'scan',return_value=copy.deepcopy(report)),patch.object(retention,'Runtime'):
                with self.assertRaisesRegex(ValueError,'摘要'):retention.execute(e,job)
            self.assertFalse((root/'0').exists());self.assertTrue((root/'1').exists())
            self.assertEqual(job['result']['removed'],['0']);self.assertEqual(job['result']['failedItem'],'1')
            self.assertEqual(e.state['packages'][0]['artifactsPruned']['jobId'],'JOB-clean')

    def test_changed_plan_prevents_all_deletion(self):
        old=dict(id='x',reasons=[],file={'bytes':1})
        e=Mock();e.c={};e.state=dict(jobs=[dict(id='scan',result=dict(keepLatest=2,items=[old]))])
        job=dict(action='clean-artifacts',payload=dict(scanJobId='scan'),selectedItems=['x'])
        with patch.object(retention,'scan',return_value=dict(complete=True,items=[dict(old,file={'bytes':2})])),patch.object(files,'remove_file') as remove:
            with self.assertRaisesRegex(ValueError,'发生变化'):retention.execute(e,job)
            remove.assert_not_called()


if __name__=='__main__':unittest.main()
