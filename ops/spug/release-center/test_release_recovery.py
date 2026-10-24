"""Recovery boundaries. Real files exercise archive replacement; runtime fakes
only isolate orchestration and are not evidence of a live database recovery.
"""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

import intruoyi_recovery_agent as agent
from intruoyi_runtime import RuntimeBlocked
import test_technical_verification as technical


class RecoveryConfigurationTest(unittest.TestCase):
    def test_generated_rehearsal_registers_owned_data_volumes_and_rejects_conflicting_mounts(self):
        from intruoyi_runtime import rehearsal_profile
        config=dict(targets={'rehearsal':dict(host='host',stagingRoot='/copy/prod')},
                    rehearsalStagingRoots={'prod':'/copy/prod'})
        profile=rehearsal_profile(config,'prod')
        self.assertTrue(profile['recoveryInventoryConfirmed'])
        self.assertEqual(profile['recoveryDataMounts'],[dict(role='redis',destination='/data'),dict(role='minio',destination='/data')])
        self.assertNotIn('recoveryInventoryConfirmed',config['targets']['rehearsal'])
        config['targets']['rehearsal']['recoveryDataMounts']=[dict(role='minio',destination='/other')]
        with self.assertRaisesRegex(RuntimeBlocked,'conflicts'):
            rehearsal_profile(config,'prod')

    def test_docker_unset_oom_override_is_equivalent_but_disabled_killer_is_not(self):
        profile={role:role for role in ('frontend','backend','database')}
        original={role:dict(Config={'Image':'old:tag','Env':[],'Labels':{}},
                            Image='sha256:original',HostConfig={'OomKillDisable':None},
                            Mounts=[],NetworkSettings={'Networks':{}}) for role in profile}
        recreated=copy.deepcopy(original)
        recreated['frontend']['HostConfig']['OomKillDisable']=False
        expected=agent.recovery_runtime_config_sha(profile,original,True)
        self.assertEqual(expected,agent.recovery_runtime_config_sha(profile,recreated,True))
        self.assertIsNone(original['frontend']['HostConfig']['OomKillDisable'])
        recreated['frontend']['HostConfig']['OomKillDisable']=True
        self.assertNotEqual(expected,agent.recovery_runtime_config_sha(profile,recreated,True))


class DataRestoreTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data=self.root/'data';self.data.mkdir()
        self.archive=self.root/'origin.tar'

    def test_replaces_modified_and_added_files_and_retains_failed_data(self):
        (self.data/'bucket').mkdir()
        (self.data/'bucket'/'old.txt').write_bytes(b'original bytes')
        (self.data/'removed.txt').write_bytes(b'restore this')
        agent.archive_data(self.data,self.archive)
        (self.data/'bucket'/'old.txt').write_bytes(b'partial migration')
        (self.data/'removed.txt').unlink()
        (self.data/'new.txt').write_bytes(b'failed candidate')
        retained=Path(agent.restore_data(self.data,self.archive,'JOB-a123456789'))
        self.assertEqual((self.data/'bucket'/'old.txt').read_bytes(),b'original bytes')
        self.assertEqual((self.data/'removed.txt').read_bytes(),b'restore this')
        self.assertFalse((self.data/'new.txt').exists())
        self.assertEqual((retained/'bucket'/'old.txt').read_bytes(),b'partial migration')
        self.assertEqual((retained/'new.txt').read_bytes(),b'failed candidate')
        self.assertEqual(agent.restore_data(self.data,self.archive,'JOB-a123456789'),str(retained))

    def test_worker_interruption_at_each_rename_resumes_without_losing_failed_data(self):
        rename=agent.os.rename
        for interrupted_at in range(1,5):
            with self.subTest(interrupted_at=interrupted_at), tempfile.TemporaryDirectory() as directory:
                source=Path(directory)/'data';source.mkdir()
                archive=Path(directory)/'origin.tar'
                (source/'a').write_bytes(b'old A');(source/'b').write_bytes(b'old B')
                agent.archive_data(source,archive)
                (source/'a').write_bytes(b'failed A');(source/'b').unlink()
                (source/'c').write_bytes(b'failed C')
                count=0
                def interrupted_rename(*args):
                    nonlocal count
                    rename(*args)
                    count+=1
                    if count==interrupted_at:
                        raise KeyboardInterrupt('Worker stopped after atomic rename')
                with patch.object(agent.os,'rename',side_effect=interrupted_rename):
                    with self.assertRaises(KeyboardInterrupt):
                        agent.restore_data(source,archive,'JOB-a123456789')
                retained=Path(agent.restore_data(source,archive,'JOB-a123456789'))
                self.assertEqual({p.name:p.read_bytes() for p in source.iterdir()}, {'a':b'old A','b':b'old B'})
                self.assertEqual({p.name:p.read_bytes() for p in retained.iterdir()}, {'a':b'failed A','c':b'failed C'})

    def test_recovery_retry_rejects_changed_archive_and_post_restore_writes(self):
        (self.data/'a').write_bytes(b'origin')
        agent.archive_data(self.data,self.archive)
        (self.data/'a').write_bytes(b'failed')
        retained=Path(agent.restore_data(self.data,self.archive,'JOB-a123456789'))
        (self.data/'a').write_bytes(b'new business write')
        with self.assertRaisesRegex(RuntimeBlocked,'checksum differs'):
            agent.restore_data(self.data,self.archive,'JOB-a123456789')
        self.assertEqual((self.data/'a').read_bytes(),b'new business write')
        self.assertEqual((retained/'a').read_bytes(),b'failed')
        self.archive.unlink()
        agent.archive_data(self.data,self.archive)
        with self.assertRaisesRegex(RuntimeBlocked,'binding changed'):
            agent.restore_data(self.data,self.archive,'JOB-a123456789')

    def test_invalid_archive_rejected_before_moving_data(self):
        for name,kind in [('../outside',tarfile.REGTYPE),('link',tarfile.SYMTYPE),('/absolute',tarfile.REGTYPE)]:
            with self.subTest(name=name):
                (self.data/'keep').write_bytes(b'current')
                with tarfile.open(self.archive,'w:') as archive:
                    member=tarfile.TarInfo(name);member.type=kind;member.linkname='/outside';member.size=0
                    archive.addfile(member,io.BytesIO())
                with self.assertRaisesRegex(RuntimeBlocked,'Unsafe'):
                    agent.restore_data(self.data,self.archive,'JOB-a123456789')
                self.assertEqual((self.data/'keep').read_bytes(),b'current')
                self.assertFalse((self.root/'data.failed-JOB-a123456789').exists())

    def test_space_refusal_keeps_original_files(self):
        (self.data/'keep').write_bytes(b'12345')
        agent.archive_data(self.data,self.archive)
        with patch.object(agent.shutil,'disk_usage',return_value=Mock(free=1)):
            with self.assertRaisesRegex(RuntimeBlocked,'Insufficient space'):
                agent.restore_data(self.data,self.archive,'JOB-a123456789')
        self.assertEqual((self.data/'keep').read_bytes(),b'12345')


class RecoveryContainerJournalTest(unittest.TestCase):
    def test_opening_old_version_uses_a_separate_resumable_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            release_root=Path(directory)/'release';journal=release_root/'recovery-JOB-aaaaaaaaaa'
            journal.mkdir(parents=True)
            old_id='old-container-id';containers={old_id:{'Id':old_id,'Image':'sha256:old','Name':'/backend','Config':{
                'Image':'sha256:old','Env':['INTRUOYI_RELEASE_MAINTENANCE=false'],'Labels':{}},
                'State':{'Running':False,'Status':'exited'},'NetworkSettings':{'Networks':{}},'Mounts':[]}}
            original=copy.deepcopy(containers[old_id])

            class Remote:
                def inspect(self,identity):
                    if identity in containers:return copy.deepcopy(containers[identity])
                    for item in containers.values():
                        if item['Name']=='/'+identity:return copy.deepcopy(item)
                    raise AssertionError('unknown disposable container')

            class Docker:
                def __call__(self,method,path,value=None):
                    if method=='GET':
                        return [{'Id':item['Id'],'Names':[item['Name']]} for item in containers.values()]
                    if '/rename?' in path:
                        identity=path.split('/containers/',1)[1].split('/rename?',1)[0]
                        containers[identity]['Name']='/'+parse_qs(urlsplit(path).query)['name'][0]
                        return {}
                    if '/create?' in path:
                        identity='created-'+str(len(containers));config=copy.deepcopy(value)
                        containers[identity]={'Id':identity,'Image':config['Image'],'Name':'/backend','Config':config,
                            'State':{'Running':False,'Status':'created'},'NetworkSettings':{'Networks':{}},'Mounts':[]}
                        return {'Id':identity}
                    raise AssertionError('unexpected disposable Docker API request: '+path)

            def clone_config(source,image,maintenance=None):
                config=copy.deepcopy(source['Config']);config['Image']=image
                if maintenance is not None:
                    config['Env']=[x for x in config['Env'] if not x.startswith('INTRUOYI_RELEASE_MAINTENANCE=')]
                    config['Env'].append('INTRUOYI_RELEASE_MAINTENANCE='+str(maintenance).lower())
                return config

            api={'remote':Remote(),'docker':Docker(),'clone_config':clone_config,
                'private_json':lambda path,value:path.write_text(json.dumps(value))}
            profile={'backend':'backend'}
            maintenance_id=agent.restore_container(profile,'backend',original,'JOB-aaaaaaaaaa',api,
                maintenance=True,journal=journal,candidate_image='sha256:candidate')
            self.assertIn('INTRUOYI_RELEASE_MAINTENANCE=true',containers[maintenance_id]['Config']['Env'])
            recovery_record={'jobId':'JOB-original0000','releaseTag':'2026-10-24-03-24-24',
                'packageSha256':'c'*64,'origin':{'fingerprint':'origin'}}
            (journal/'receipt.private.json').write_text(json.dumps({'jobId':'JOB-aaaaaaaaaa',
                'originalJobId':'JOB-original0000','releaseTag':recovery_record['releaseTag'],
                'packageSha256':recovery_record['packageSha256'],'originFingerprint':'origin',
                'status':'succeeded','phase':'opening','openingJobId':'JOB-bbbbbbbbbb'}))
            opened_id=agent.restore_container(profile,'backend',original,'JOB-bbbbbbbbbb',api,
                maintenance=False,journal=journal,candidate_image='sha256:candidate',
                recovery_record=recovery_record,allowed_opening_attempt='JOB-aaaaaaaaaa')
            self.assertNotEqual(opened_id,maintenance_id)
            self.assertNotIn('INTRUOYI_RELEASE_MAINTENANCE=true',containers[opened_id]['Config']['Env'])
            self.assertTrue((journal/'backend-replacement.private.json').is_file())
            self.assertTrue((journal/'backend-opening-replacement.private.json').is_file())


class RecoveryWorkflowTest(unittest.TestCase):
    setUp=technical.TechnicalVerificationTest.setUp
    observation=technical.TechnicalVerificationTest.observation
    run_action=technical.TechnicalVerificationTest.run_action
    seed_technical=technical.TechnicalVerificationTest.seed_technical
    seed_rehearsal=technical.TechnicalVerificationTest.seed_rehearsal
    def recovery_origin(self):
        self.seed_rehearsal()
        job=self.run_action('promote-prod')
        self.assertEqual(job['status'],'succeeded',job.get('error'))
        job['migrationPlan']={'items':[{'migrationId':'M001','sha256':'a'*64,'action':'APPLY'}]}
        return job

    def restore_result(self,original,phase='restored'):
        observation=copy.deepcopy(original['originState'])
        observation['maintenance']=phase!='opened'
        return {'observation':observation,'receipt':{
            'jobId':'JOB-abcdef0123','originalJobId':original['id'],'packageSha256':self.package['packageSha256'],
            'phase':phase,'openingJobId':'unused'}}

    def test_rejected_formal_acceptance_restores_without_accepting_failed_package(self):
        original=self.recovery_origin()
        rejected=self.run_action('reject-acceptance',note='Business data mismatch')
        self.assertEqual(rejected['status'],'failed')
        self.executor.runtime.call.return_value=self.restore_result(original)
        restored=self.run_action('recover-release',jobId=original['id'],note='Restore pre-release state')
        self.assertEqual(restored['status'],'succeeded',restored.get('error'))
        self.assertTrue(self.executor.state['environments']['prod']['recoveryPending'])
        self.assertNotIn('resolution',rejected)
        self.assertNotIn('resolution',original)
        with self.assertRaisesRegex(ValueError,'business acceptance'):
            self.run_action('promote-backup')
        result=self.restore_result(original,'opened')
        def opening(*args,**kwargs):
            result['receipt']['confirmedByJobId']=kwargs['jobId']
            return result
        self.executor.runtime.call.side_effect=opening
        accepted=self.run_action('accept-recovery',jobId=original['id'],note='Old version and data checked')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        self.assertFalse(self.executor.state['environments']['prod']['maintenance'])
        self.assertEqual(self.package['stage'],'prod-restored')
        self.assertTrue(self.package['abandoned'])
        self.assertEqual(rejected['status'],'failed')
        self.assertEqual(rejected['resolution']['decision'],'restored')
        self.assertEqual(self.package['outcomes']['prod']['acceptance']['status'],'failed')

    def test_recovery_acceptance_is_persisted_with_resolution_and_job_completion(self):
        original=self.recovery_origin()
        original.update(status='failed',error='Partial migration')
        self.executor.runtime.call.return_value=self.restore_result(original)
        restored=self.run_action('recover-release',jobId=original['id'],note='Restore partial migration')
        self.assertEqual(restored['status'],'succeeded',restored.get('error'))
        with self.assertRaisesRegex(ValueError,'Recovery already completed'):
            self.run_action('recover-release',jobId=original['id'],note='Duplicate data restoration')
        snapshots=[]
        self.executor.save.side_effect=lambda:snapshots.append(copy.deepcopy(self.executor.state))
        result=self.restore_result(original,'opened')
        def opening(*args,**kwargs):
            result['receipt']['confirmedByJobId']=kwargs['jobId']
            return result
        self.executor.runtime.call.side_effect=opening
        accepted=self.run_action('accept-recovery',jobId=original['id'],note='Restored data verified')
        self.assertEqual(accepted['status'],'succeeded',accepted.get('error'))
        accepted_states=[]
        for snapshot in snapshots:
            package=next(p for p in snapshot['packages'] if p['releaseTag']==self.tag)
            if package['outcomes']['prod']['recovery']['status']=='accepted':
                accepted_states.append(snapshot)
                self.assertEqual(package['stage'],'prod-restored')
                self.assertTrue(package['abandoned'])
                jobs={job['id']:job for job in snapshot['jobs']}
                self.assertEqual(jobs[original['id']]['resolution']['jobId'],accepted['id'])
                self.assertEqual(jobs[accepted['id']]['status'],'succeeded')
                self.assertTrue(jobs[accepted['id']]['finishedAt'])
                self.assertFalse(snapshot['environments']['prod']['recoveryPending'])
        self.assertTrue(accepted_states)

    def test_lost_opening_response_can_be_reconfirmed_without_restoring_again(self):
        original=self.recovery_origin()
        self.executor.runtime.call.return_value=self.restore_result(original)
        restored=self.run_action('recover-release',jobId=original['id'],note='Restore rejected release')
        self.assertEqual(restored['status'],'succeeded',restored.get('error'))
        error=RuntimeError('Opening worker response was lost')
        error.remoteStatusUnknown=True
        self.executor.runtime.call.side_effect=error
        first=self.run_action('accept-recovery',jobId=original['id'],note='Restored data verified')
        self.assertEqual(first['status'],'interrupted')
        self.assertTrue(self.executor.state['environments']['prod']['recoveryPending'])
        self.assertNotIn('resolution',original)
        result=self.restore_result(original,'opened')
        result['receipt']['openingJobId']=first['id']
        def opening(*args,**kwargs):
            self.assertEqual(args[1],'accept-recovery')
            result['receipt']['confirmedByJobId']=kwargs['jobId']
            return result
        self.executor.runtime.call.side_effect=opening
        retried=self.run_action('accept-recovery',jobId=original['id'],note='Confirm already opened origin')
        self.assertEqual(retried['status'],'succeeded',retried.get('error'))
        self.assertEqual(first['resolution']['jobId'],retried['id'])

    def test_partial_migration_failure_does_not_replay_sql_or_mark_it_applied(self):
        original=self.recovery_origin()
        original.update(status='failed',error='M001 stopped after DDL')
        self.package['outcomes']['prod']['deployment']['status']='failed'
        self.executor.runtime.call.return_value={'migrations':[{'migrationId':'M001','status':'failed-or-unknown'}]}
        inspected=self.run_action('inspect-release-recovery',jobId=original['id'])
        self.assertEqual(inspected['status'],'succeeded',inspected.get('error'))
        self.assertEqual(original['migrationExecution']['migrations'][0]['status'],'failed-or-unknown')
        self.executor.runtime.call.return_value=self.restore_result(original)
        restored=self.run_action('recover-release',jobId=original['id'],note='Partial SQL failure requires restore')
        self.assertEqual(restored['status'],'succeeded',restored.get('error'))
        self.assertEqual(original['status'],'failed')
        self.assertEqual(original['error'],'M001 stopped after DDL')
        self.assertEqual(self.executor.deploy.call_count,1)
        self.assertNotIn('resolution',original)

    def test_bad_restore_receipt_keeps_maintenance_unknown_and_blocks_acceptance(self):
        original=self.recovery_origin()
        result=self.restore_result(original);result['observation']['schemaSha256']='wrong'
        self.executor.runtime.call.return_value=result
        restored=self.run_action('recover-release',jobId=original['id'],note='Restore pre-release state')
        self.assertEqual(restored['status'],'failed')
        self.assertTrue(self.executor.state['environments']['prod']['maintenanceUnknown'])
        accepted=self.run_action('accept-recovery',jobId=original['id'],note='Must refuse unverified restore')
        self.assertEqual(accepted['status'],'failed')
        self.assertNotIn('resolution',original)

    def test_accepted_release_and_superseded_deployment_cannot_restore(self):
        original=self.recovery_origin()
        self.package['outcomes']['prod']['acceptance']={'status':'passed'}
        with self.assertRaisesRegex(ValueError,'Business accepted'):
            self.run_action('recover-release',jobId=original['id'],note='Attempt obsolete restore')
        self.package['outcomes']['prod'].pop('acceptance')
        self.package['outcomes']['prod']['deployment']['jobId']='newer-deployment'
        with self.assertRaisesRegex(ValueError,'newer deployment'):
            self.run_action('recover-release',jobId=original['id'],note='Attempt obsolete restore')


if __name__=='__main__':
    unittest.main()
