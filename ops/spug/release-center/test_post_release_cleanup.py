"""Lifecycle contracts and real temporary-file deletion; no server deployment."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import artifact_files as files
import post_release_cleanup as cleanup

OLD = '2026-10-30-01-00-00'
CURRENT = '2026-11-01-01-00-00'
PATCH = '2026-11-02-01-00-00'
JOB = 'JOB-0123456789'


class CleanupTests(unittest.TestCase):
    def test_only_final_successful_acceptance_triggers_cleanup(self):
        e = Mock()
        e.state = dict(packages=[dict(releaseTag=CURRENT, stage='completed')], frontendPatches=[])
        for action, status in [('publish-test','succeeded'), ('accept-prod','succeeded'),
                               ('accept-backup','failed'), ('frontend-patch-deploy','succeeded')]:
            job = dict(id=JOB, action=action, status=status, releaseTag=CURRENT)
            cleanup.run(e, job)
            self.assertNotIn('postReleaseCleanup', job)
        with patch.object(cleanup, 'perform', return_value=dict(status='succeeded', environments={})) as perform:
            job = dict(id=JOB, action='accept-backup', status='succeeded', releaseTag=CURRENT)
            cleanup.run(e, job)
            cleanup.run(e, job)
            perform.assert_called_once()

    def test_cleanup_failure_is_visible_without_falsifying_deployment(self):
        e = Mock(); e.password = 'secret'
        e.state = dict(packages=[dict(releaseTag=CURRENT, stage='completed')])
        job = dict(id=JOB, action='accept-backup', status='succeeded', releaseTag=CURRENT)
        with patch.object(cleanup, 'perform', side_effect=ValueError('secret disk failure')):
            cleanup.run(e, job)
        self.assertEqual(job['status'], 'succeeded')
        self.assertEqual(job['postReleaseCleanup']['status'], 'failed')
        self.assertNotIn('secret', job['postReleaseCleanup']['error'])
        self.assertTrue(e.log.called)

    def test_protect_current_rehearsal_pending_origin_and_unfinished_packages(self):
        state = dict(packages=[dict(releaseTag=t, stage='completed') for t in (OLD,CURRENT)],
                     environments={'test':dict(releaseTag=CURRENT), 'rehearsal':dict(releaseTag=OLD)},
                     jobs=[], frontendPatches=[])
        self.assertIn(OLD, cleanup.protected_tags(state))
        del state['environments']['rehearsal']
        self.assertNotIn(OLD, cleanup.protected_tags(state))
        state['jobs'] = [dict(id='failed', status='failed', action='publish-test',
                             releaseTag=CURRENT, originState=dict(releaseTag=OLD))]
        self.assertIn(OLD, cleanup.protected_tags(state))
        state['jobs'][0]['resolution'] = {'decision':'restored'}
        state['packages'][0]['stage'] = 'test-deployed'
        self.assertIn(OLD, cleanup.protected_tags(state))

    def test_patch_completion_is_supported_and_does_not_trigger_at_prod_acceptance(self):
        e=Mock(); e.state=dict(frontendPatches=[dict(releaseTag=PATCH,stage='completed')])
        job=dict(id=JOB,action='frontend-patch-accept',target='prod',releaseTag=PATCH,status='succeeded')
        with patch.object(cleanup,'perform',return_value=dict(status='succeeded')) as perform:
            cleanup.run(e,job);perform.assert_not_called()
            job['target']='backup';cleanup.run(e,job);perform.assert_called_once()

    def executor(self):
        e=Mock(); e.password='secret'
        self.images=dict(backend='sha256:'+'a'*64,frontend='sha256:'+'b'*64)
        observation=dict(releaseTag=CURRENT,images=self.images,maintenance=False,schemaSha256='schema',
                         fingerprint='fingerprint',ledgerRecords=[],backendHealth={'status':'UP'},frontendHttpStatus=200)
        e.runtime.observe.side_effect=lambda env:copy.deepcopy(observation)
        e.runtime.call.return_value=dict(status='succeeded',removed=[],retained=[],bytes=0)
        e.manifest.side_effect=lambda tag:(dict(releaseTag=tag),dict(releaseTag=tag,images={r:dict(id=v) for r,v in self.images.items()}))
        e.c=dict(targets={env:dict(stagingRoot='/data/releases') for env in cleanup.ENVS})
        e.state=dict(packages=[dict(releaseTag=OLD,stage='completed',manifestSha256='a'*64,packageSha256='b'*64),
                               dict(releaseTag=CURRENT,stage='completed')],frontendPatches=[],
                     jobs=[],environments={env:copy.deepcopy(observation) for env in cleanup.ENVS})
        return e

    def test_all_three_runtime_checks_precede_any_deletion_and_plan_is_remote_only(self):
        e=self.executor();job=dict(id=JOB,action='accept-backup',releaseTag=CURRENT,status='succeeded')
        result=cleanup.perform(e,job)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(e.runtime.call.call_count,3)
        for call in e.runtime.call.call_args_list:
            self.assertEqual(call.args[1],'artifact-auto-clean')
            self.assertEqual([r['manifest']['releaseTag'] for r in call.kwargs['entries']],[OLD])
            self.assertIn(CURRENT,call.kwargs['protectedTags'])
        e=self.executor()
        e.runtime.observe.side_effect=[e.state['environments']['test'],e.state['environments']['prod'],{}]
        with self.assertRaises(ValueError):cleanup.perform(e,job)
        e.runtime.call.assert_not_called()

    def test_environment_failure_is_visible_and_other_servers_are_processed(self):
        e=self.executor();job=dict(id=JOB,action='accept-backup',releaseTag=CURRENT,status='succeeded')
        e.runtime.call.side_effect=[ValueError('secret failure'),dict(status='succeeded'),dict(status='succeeded')]
        cleanup.run(e,job)
        self.assertEqual(job['status'],'succeeded')
        self.assertEqual(job['result']['postReleaseCleanup']['status'],'failed')
        self.assertEqual(e.runtime.call.call_count,3)
        self.assertNotIn('secret',str(job['result']))

    def test_full_executor_calls_cleanup_only_after_execution_has_returned(self):
        from intruoyi_executor import IntRuoyiExecutor
        e=object.__new__(IntRuoyiExecutor);e.runtime=Mock();e.password='secret'
        e.log=Mock(); e.save=Mock();e.state=dict(packages=[dict(releaseTag=CURRENT,stage='completed')])
        job=dict(id=JOB,action='accept-backup',status='running',releaseTag=CURRENT)
        e.execute_bound=Mock(side_effect=lambda j:j.update(status='succeeded'))
        with patch.object(cleanup,'perform',return_value=dict(status='succeeded')) as perform:
            e.execute(job)
            perform.assert_called_once()
        self.assertEqual(job['status'],'succeeded')

    def test_concurrent_controller_job_blocks_before_runtime_calls(self):
        e=self.executor();e.state['jobs']=[dict(id='other',action='publish-test',status='running')]
        with self.assertRaisesRegex(ValueError,'运行任务'):
            cleanup.perform(e,dict(id=JOB,action='accept-backup',releaseTag=CURRENT))
        e.runtime.observe.assert_not_called()

    def test_frontend_final_acceptance_invokes_cleanup_after_recording_success(self):
        from frontend_patch import FrontendPatchMixin
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'release.tar').write_bytes(b'patch bytes')
            p=dict(releaseTag=PATCH,directory=folder,packageSha256=files.sha(root/'release.tar'),manifestSha256='a'*64,accepted={})
            e=FrontendPatchMixin();e.step=Mock();e.frontend_gate=Mock();e.frontend_package=Mock(return_value=(p,{}))
            e.frontend_call=Mock(return_value={});e.record_frontend=Mock();e.log=Mock();e.save=Mock()
            e.runtime=SimpleNamespace(operation_context=SimpleNamespace(binding=None))
            e.state=dict(frontendPatches=[p]);e.password='secret'
            job=dict(id=JOB,action='frontend-patch-accept',target='backup',releaseTag=PATCH,
                     payload=dict(target='backup',releaseTag=PATCH,note='真实页面验收通过'),actor='operator')
            with patch.object(cleanup,'perform',return_value=dict(status='succeeded')) as perform:
                e.frontend_job(job)
            perform.assert_called_once()
            self.assertEqual(p['stage'],'completed')
            self.assertEqual(job['status'],'succeeded')
            self.assertIn('backup',p['accepted'])

    def test_invalid_remote_receipt_cannot_change_release_success(self):
        e=self.executor();e.runtime.call.return_value=None
        job=dict(id=JOB,action='accept-backup',releaseTag=CURRENT,status='succeeded')
        cleanup.run(e,job)
        self.assertEqual(job['status'],'succeeded')
        self.assertEqual(job['postReleaseCleanup']['status'],'failed')
        self.assertTrue(all(r['status']=='failed' for r in job['postReleaseCleanup']['environments'].values()))


class RealFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.root=self.base/OLD; self.root.mkdir()
        for name in ('release.tar','images.tar','recovery.sql.gz','recovery-volume-0.tar'):
            (self.root/name).write_bytes(('real '+name).encode())
        self.manifest=dict(releaseTag=OLD, files=[dict(name='images.tar',sha256=files.sha(self.root/'images.tar'))])
        (self.root/'manifest.json').write_text(json.dumps(self.manifest),'utf-8')
        self.entry=dict(manifest=self.manifest,manifestSha256=files.sha(self.root/'manifest.json'),
                        packageSha256=files.sha(self.root/'release.tar'),ownerJobIds=[JOB])
        record=dict(releaseTag=OLD,jobId=JOB,manifestSha256=self.entry['manifestSha256'],
                    packageSha256=self.entry['packageSha256'],path=str(self.root/'recovery.sql.gz'),
                    sha256=files.sha(self.root/'recovery.sql.gz'),resources=[dict(artifact=dict(
                    path=str(self.root/'recovery-volume-0.tar'),sha256=files.sha(self.root/'recovery-volume-0.tar')))])
        (self.root/'recovery-record.private.json').write_text(json.dumps(record),'utf-8')
        (self.root/'credentials.private.json').write_bytes(b'private')
        self.profile=dict(stagingRoot=str(self.base),backend='app',frontend='web')
        self.payload=dict(action='artifact-auto-clean',workflowJobId=JOB,entries=[self.entry],
                          expectedImages=dict(backend='b',frontend='f'),currentReleaseTag=CURRENT,
                          protectedTags=[CURRENT],currentPatchTag=None)

    def run_cleanup(self, **changes):
        payload=dict(self.payload,**changes)
        with patch.object(files,'docker_inventory',return_value=({},set(),[])), \
             patch.object(files,'assert_cleanup_idle'), \
             patch.object(files,'verify_cleanup_runtime'):
            return files.remote(self.profile,payload)

    def test_delete_owned_old_payloads_keep_records_private_and_current_checkpoint(self):
        current=self.base/CURRENT; current.mkdir(); (current/'recovery.sql.gz').write_bytes(b'current checkpoint')
        result=self.run_cleanup()
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(len(result['removed']),4)
        self.assertTrue((current/'recovery.sql.gz').exists())
        for name in ('manifest.json','recovery-record.private.json','credentials.private.json'):
            self.assertTrue((self.root/name).exists())
        self.assertEqual(self.run_cleanup()['removed'],[])

    def test_retained_current_root_unknown_recovery_and_mounted_files(self):
        result=self.run_cleanup(protectedTags=[OLD,CURRENT])
        self.assertEqual(result['removed'],[])
        with patch.object(files,'docker_inventory',return_value=({},set(),[str(self.root)])), \
             patch.object(files,'assert_cleanup_idle'), patch.object(files,'verify_cleanup_runtime'):
            result=files.remote(self.profile,self.payload)
        self.assertEqual(result['removed'],[])
        (self.root/'recovery-record.private.json').write_text('{}','utf-8')
        result=self.run_cleanup()
        self.assertTrue(result['retained'])
        self.assertTrue((self.root/'release.tar').exists())

    def test_wrong_hash_and_partial_failure_are_recorded_and_retriable(self):
        (self.root/'images.tar').write_bytes(b'changed')
        result=self.run_cleanup()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(result['removed']),1)
        self.assertTrue((self.root/'images.tar').exists())
        self.assertTrue((self.root/'recovery.sql.gz').exists())
        report=self.base/'.cleanup'/(JOB+'.json')
        self.assertEqual(json.loads(report.read_text('utf-8'))['status'],'failed')

    def test_patch_old_attempt_files_are_deleted_without_database_commands(self):
        patchroot=self.base/'frontend-patches'/OLD/JOB;patchroot.mkdir(parents=True)
        for name in ('manifest.json','release.tar','images.tar'):
            (patchroot/name).write_bytes((self.root/name).read_bytes())
        entry=dict(self.entry,kind='frontend-patch',deploymentJobId=JOB)
        result=self.run_cleanup(entries=[entry])
        self.assertEqual(len(result['removed']),2)
        self.assertTrue((patchroot/'manifest.json').exists())
        self.assertTrue((self.root/'recovery.sql.gz').exists())

    def test_path_traversal_and_cross_device_file_refused(self):
        entry=dict(self.entry,attempt='../other')
        with self.assertRaises(ValueError):self.run_cleanup(entries=[entry])
        row=files.inventory(self.root,self.manifest,self.entry['manifestSha256'],self.entry['packageSha256'])[0]
        with patch.object(files,'same_device',return_value=False):
            result=self.run_cleanup()
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['removed'],[])

    def test_recovery_files_without_record_and_hardlinks_are_not_deleted(self):
        (self.root/'recovery-record.private.json').unlink()
        self.assertEqual(self.run_cleanup()['removed'],[])
        self.assertTrue((self.root/'recovery.sql.gz').exists())

    def test_symlink_and_nas_root_rejected_before_mutation(self):
        original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda p: p==self.base or original(p)):
            with self.assertRaisesRegex(ValueError,'链接'):self.run_cleanup()
        with self.assertRaisesRegex(ValueError,'NAS'):
            files.automatic_cleanup(dict(stagingRoot='/mnt/nas'),self.payload)


if __name__=='__main__': unittest.main()
