"""Bounded resource planning; Docker integration is a separate real-engine test."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import artifact_files as files
import runtime_resource_cleanup as resources

OLD='2026-10-30-01-00-00'
CURRENT='2026-11-01-01-00-00'
JOB='JOB-0123456789'


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.profile=dict(stagingRoot=str(self.base),backend='app',frontend='web')
        self.old=self.container('a'*64,'app-before-'+OLD,'sha256:'+'b'*64)
        self.entries=[]
        self.entry(OLD,self.old)
        self.entry(CURRENT)
        self.payload=dict(resourceEntries=self.entries,protectedTags=[CURRENT],currentReleaseTag=CURRENT,
                          currentPatchTag=None,expectedImages=dict(backend='new-b',frontend='new-f'))

    def container(self,identity,name,image,running=False):
        return dict(Id=identity,Name='/'+name,Image=image,Config=dict(Image=image,Labels={}),
                    HostConfig=dict(Binds=[]),Mounts=[],State=dict(Running=running,Paused=False,Restarting=False))

    def entry(self,tag,container=None):
        root=self.base/tag;root.mkdir()
        manifest=dict(releaseTag=tag,images=dict(backend=dict(name='app:'+tag,id='sha256:'+'b'*64)),files=[])
        (root/'manifest.json').write_text(json.dumps(manifest),'utf-8')
        entry=dict(manifest=manifest,manifestSha256=files.sha(root/'manifest.json'),packageSha256='c'*64,ownerJobIds=[JOB])
        self.entries.append(entry)
        if container:
            snapshot=copy.deepcopy(container);snapshot['Name']='/app'
            (root/'backend-before-initial.private.json').write_text(json.dumps(snapshot),'utf-8')
        return entry

    def plan(self,containers=None):
        with patch.object(resources,'containers',return_value=copy.deepcopy(containers if containers is not None else [self.old])):
            return resources.plan(self.profile,self.payload)

    def test_old_stopped_container_requires_exact_snapshot_identity(self):
        result=self.plan()
        self.assertEqual([r['id'] for r in result['containers']],[self.old['Id']])
        changed=copy.deepcopy(self.old);changed['Id']='d'*64
        self.assertEqual(self.plan([changed])['containers'],[])
        self.assertTrue(self.plan([changed])['retained'])

    def test_running_or_reconfigured_or_unknown_container_is_retained(self):
        for key,value in [('Name','/unrelated'),('Image','sha256:'+'e'*64)]:
            changed=copy.deepcopy(self.old);changed[key]=value
            self.assertEqual(self.plan([changed])['containers'],[])
        changed=copy.deepcopy(self.old);changed['State']['Running']=True
        self.assertEqual(self.plan([changed])['containers'],[])
        changed=copy.deepcopy(self.old);changed['Config']['Labels']={'changed':'true'}
        self.assertEqual(self.plan([changed])['containers'],[])

    def test_current_checkpoint_keeps_original_container_and_image(self):
        root=self.base/CURRENT
        snapshot=copy.deepcopy(self.old);snapshot['Name']='/app'
        (root/'recovery-containers.private.json').write_text(json.dumps({'app':snapshot}),'utf-8')
        result=self.plan()
        self.assertEqual(result['containers'],[])
        self.assertIn(self.old['Image'],result['protectedImages'])

    def test_mount_order_is_not_container_configuration_drift(self):
        original=copy.deepcopy(self.old)
        original['Mounts']=[dict(Type='bind',Source='/a',Destination='/a',RW=False),
                            dict(Type='bind',Source='/b',Destination='/b',RW=True)]
        reordered=copy.deepcopy(original);reordered['Mounts'].reverse()
        self.assertEqual(resources.fingerprint(original),resources.fingerprint(reordered))
        row=dict(id=original['Id'],name=original['Name'].lstrip('/'),imageId=original['Image'],fingerprint=resources.fingerprint(original))
        with patch.object(resources,'containers',return_value=[reordered]),patch.object(files,'docker',side_effect=[b'',b'[]']) as docker:
            resources.remove_container(row)
            self.assertEqual(docker.call_args_list[0].args[0],['rm','--',original['Id']])
        reordered['Mounts'][0]['RW']=False
        self.assertNotEqual(resources.fingerprint(original),resources.fingerprint(reordered))
        first=copy.deepcopy(original);first['Config']['Env']=['VALUE=1','VALUE=2']
        second=copy.deepcopy(first);second['Config']['Env'].reverse()
        self.assertNotEqual(resources.fingerprint(first),resources.fingerprint(second))

    def test_uncertain_old_restore_preserves_whole_release_and_reports_retention(self):
        recovery_id='JOB-9876543210';accepted='JOB-1111111111'
        source=self.base/'minio-data';source.mkdir()
        retained=source.with_name(source.name+'.failed-'+recovery_id);retained.mkdir()
        (retained/'object').write_bytes(b'keep old evidence')
        archive=self.base/OLD/'recovery-volume-0.tar';archive.write_bytes(b'checkpoint archive')
        record=dict(resources=[dict(role='minio',mount=dict(Source=str(source),Destination='/data'),
            artifact=dict(path=str(archive),sha256=files.sha(archive)))])
        (self.base/OLD/'recovery-record.private.json').write_text(json.dumps(record),'utf-8')
        folder=self.base/OLD/('recovery-'+recovery_id);folder.mkdir()
        dump_folder=folder/'failed-database-0';dump_folder.mkdir();dump=dump_folder/'recovery.sql.gz';dump.write_bytes(b'keep failed database')
        receipt=dict(jobId=recovery_id,originalJobId=JOB,releaseTag=OLD,packageSha256='c'*64,
            status='succeeded',phase='opened',openingStatus='succeeded',openingJobId=accepted,retainedData=[str(retained)],
            failedDatabase=dict(path=str(dump),sha256=files.sha(dump)))
        (folder/'receipt.private.json').write_text(json.dumps(receipt),'utf-8')
        journal=source.parent/(source.name+'.restore-'+recovery_id+'.json')
        journal.write_text(json.dumps(dict(phase='complete',attemptId=recovery_id,source=str(source.resolve()),archiveSha256='0'*64)),'utf-8')
        self.entries[0]['resolvedRecoveries']=[dict(recoveryJobId=recovery_id,acceptanceJobId=accepted,openingJobId=accepted,originalJobId=JOB)]
        self.profile['minio']='minio'
        service=self.container('e'*64,'minio','sha256:'+'f'*64,True)
        service['Mounts']=[dict(Source=str(source),Destination='/data')]
        payload=dict(self.payload,action='artifact-auto-clean',workflowJobId=JOB,entries=[self.entries[0]])
        with patch.object(resources,'containers',return_value=[self.old,service]),patch.object(files,'verify_cleanup_runtime'),patch.object(files,'assert_cleanup_idle'):
            result=files.automatic_cleanup(self.profile,payload)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(result['plan']['blockedReleaseTags'],[OLD])
        self.assertEqual(result['plan']['containers'],[])
        self.assertEqual(result['plan']['files'],[])
        self.assertEqual(result['plan']['directories'],[])
        self.assertTrue(any('恢复日志' in row.get('reason','') for row in result['retained']))
        self.assertTrue(archive.exists());self.assertTrue(dump.exists());self.assertTrue(retained.exists())
        other_tag='2026-10-29-01-00-00'
        other=self.container('d'*64,'app-before-'+other_tag,'sha256:'+'e'*64)
        self.entry(other_tag,other)
        independent=self.plan([self.old,service,other])
        self.assertEqual([v['id'] for v in independent['containers']],[other['Id']])

    def test_unpublished_newer_release_is_not_retired(self):
        newer='2026-11-03-01-00-00'
        future=self.container('d'*64,'app-before-'+newer,'sha256:'+'e'*64)
        self.entry(newer,future)
        self.assertNotIn(future['Id'],[row['id'] for row in self.plan([future])['containers']])

    def test_patch_recovery_point_keeps_original_frontend(self):
        tag='2026-11-02-01-00-00'
        root=self.base/'frontend-patches'/tag/JOB;root.mkdir(parents=True)
        manifest=dict(releaseTag=tag,images={},files=[])
        (root/'manifest.json').write_text(json.dumps(manifest),'utf-8')
        (root/'frontend-origin.private.json').write_text(json.dumps(self.old),'utf-8')
        self.entries.append(dict(kind='frontend-patch',manifest=manifest,manifestSha256=files.sha(root/'manifest.json'),
                                 packageSha256='c'*64,deploymentJobId=JOB))
        self.payload['protectedTags'].append(tag)
        self.assertEqual(self.plan()['containers'],[])

    def test_plan_sanitizes_snapshot_and_unknown_containers_are_reported(self):
        self.old['Config']['Env']=['PASSWORD=private-value']
        plan=self.plan()
        self.assertNotIn('private-value',json.dumps(plan))
        self.assertTrue(plan['retained'])

    def test_filesystem_identity_and_manifest_mismatch_are_not_ignored(self):
        self.entries[0]['manifestSha256']='0'*64
        with self.assertRaises(ValueError):self.plan()

    def test_missing_legacy_manifest_retains_group_but_current_missing_manifest_blocks(self):
        (self.base/OLD/'manifest.json').unlink()
        result=self.plan()
        self.assertEqual(result['blockedReleaseTags'],[OLD])
        self.assertEqual(result['containers'],[])
        self.assertTrue(any('缺少清单' in row.get('reason','') for row in result['retained']))
        (self.base/CURRENT/'manifest.json').unlink()
        with self.assertRaises(ValueError):self.plan()

    def test_execution_rechecks_identity_and_never_force_or_remove_volumes(self):
        plan=self.plan()
        changed=copy.deepcopy(self.old);changed['State']['Running']=True
        with patch.object(resources,'containers',return_value=[changed]),patch.object(files,'docker') as docker:
            with self.assertRaises(ValueError):resources.remove_container(plan['containers'][0])
            docker.assert_not_called()
        with patch.object(resources,'containers',return_value=[self.old]),patch.object(files,'docker') as docker:
            docker.side_effect=[b'',b'[]']
            resources.remove_container(plan['containers'][0])
            self.assertEqual(docker.call_args_list[0].args[0],['rm','--',self.old['Id']])

    def test_resolved_failed_database_requires_opened_receipt_and_matching_job(self):
        root=self.base/OLD; recovery_id='JOB-9876543210'; accepted='JOB-1111111111'
        folder=root/('recovery-'+recovery_id);folder.mkdir()
        failed=folder/'failed-database-0';failed.mkdir();dump=failed/'recovery.sql.gz';dump.write_bytes(b'failed sql')
        receipt=dict(jobId=recovery_id,originalJobId=JOB,releaseTag=OLD,packageSha256='c'*64,
                     phase='opened',status='succeeded',openingStatus='succeeded',openingJobId=accepted,
                     failedDatabase=dict(path=str(dump),sha256=files.sha(dump)),retainedData=[])
        (folder/'receipt.private.json').write_text(json.dumps(receipt),'utf-8')
        self.entries[0]['resolvedRecoveries']=[dict(recoveryJobId=recovery_id,acceptanceJobId=accepted,openingJobId=accepted,originalJobId=JOB)]
        result=self.plan()
        self.assertEqual([r['relative'] for r in result['files']], [str(dump.relative_to(self.base))])
        del self.entries[0]['resolvedRecoveries']
        self.assertEqual(self.plan()['files'],[])
        self.entries[0]['resolvedRecoveries']=[dict(recoveryJobId=recovery_id,acceptanceJobId='JOB-2222222222',openingJobId='JOB-2222222222',originalJobId=JOB)]
        with self.assertRaises(ValueError):self.plan()

    def test_nested_mount_refuses_failed_tree_and_never_follows_links(self):
        root=self.base/'data.failed-JOB-0123456789';root.mkdir();(root/'keep').write_bytes(b'actual')
        with self.assertRaises(ValueError):resources.tree_rows(root,[str(root/'nested-mount')])

    def test_missing_image_and_unrelated_tags_are_not_deleted(self):
        with patch.object(files,'docker_inventory',return_value=({},set(),[])),patch.object(files,'docker') as docker:
            self.assertFalse(resources.remove_image(dict(reference='app:'+OLD,imageId='sha256:'+'b'*64),[]))
            docker.assert_not_called()
        with patch.object(files,'docker_inventory',return_value=({'app:'+OLD:'sha256:'+'b'*64},set(),[])),patch.object(files,'docker') as docker:
            resources.remove_image(dict(reference='app:'+OLD,imageId='sha256:'+'b'*64),[])
            docker.assert_called_once_with(['image','rm','--','app:'+OLD])

    def test_resolved_tree_uses_registered_data_mount_journal_and_exact_files(self):
        recovery_id='JOB-9876543210';accepted='JOB-1111111111'
        source=self.base/'minio-data';source.mkdir()
        retained=source.with_name(source.name+'.failed-'+recovery_id);retained.mkdir()
        (retained/'object').write_bytes(b'failed object')
        archive=self.base/OLD/'recovery-volume-0.tar';archive.write_bytes(b'checkpoint archive')
        record=dict(resources=[dict(role='minio',mount=dict(Source=str(source),Destination='/data'),
                                   artifact=dict(path=str(archive),sha256=files.sha(archive)))])
        (self.base/OLD/'recovery-record.private.json').write_text(json.dumps(record),'utf-8')
        folder=self.base/OLD/('recovery-'+recovery_id);folder.mkdir()
        receipt=dict(jobId=recovery_id,originalJobId=JOB,releaseTag=OLD,packageSha256='c'*64,
            status='succeeded',phase='opened',openingStatus='succeeded',openingJobId=accepted,retainedData=[str(retained)])
        (folder/'receipt.private.json').write_text(json.dumps(receipt),'utf-8')
        journal=source.parent/(source.name+'.restore-'+recovery_id+'.json')
        journal.write_text(json.dumps(dict(phase='complete',attemptId=recovery_id,source=str(source.resolve()),
                           archiveSha256=files.sha(archive))),'utf-8')
        self.entries[0]['resolvedRecoveries']=[dict(recoveryJobId=recovery_id,acceptanceJobId=accepted,openingJobId=accepted,originalJobId=JOB)]
        self.profile['minio']='minio'
        service=self.container('e'*64,'minio','sha256:'+'f'*64,True)
        service['Mounts']=[dict(Source=str(source),Destination='/data')]
        result=self.plan([self.old,service])
        self.assertEqual(len(result['files']),1)
        for row in result['files']:files.remove_file(row['root'],row)
        with patch.object(files,'docker_inventory',return_value=({},set(),[str(source)])):
            for row in result['directories']:resources.remove_directory(row)
        self.assertFalse(retained.exists());self.assertTrue(source.exists());self.assertTrue(journal.exists())

    def test_container_restart_between_plan_and_delete_produces_visible_pending_receipt(self):
        payload=dict(self.payload,action='artifact-auto-clean',workflowJobId=JOB,entries=[])
        plan=self.plan()
        with (patch.object(resources,'plan',return_value=plan),patch.object(resources,'remove_container',side_effect=ValueError('changed running')),
              patch.object(files,'verify_cleanup_runtime'),patch.object(files,'assert_cleanup_idle')):
            result=files.automatic_cleanup(self.profile,payload)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['removed'],[])
        self.assertEqual(result['pendingDeletion']['kind'],'container')
        self.assertEqual(result['plan']['containers'],plan['containers'])


if __name__=='__main__':unittest.main()
