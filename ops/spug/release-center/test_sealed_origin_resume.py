"""Bound checkpoint continuation with real local artifact integrity checks."""
import copy
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import intruoyi_runtime_agent as agent
from intruoyi_runtime import file_sha, package_identity, runtime_config_snapshot, sha


class SealedOriginResumeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.tag='2026-11-03-12-15-42'; self.original='JOB-1111111111'; self.retry='JOB-2222222222'
        self.profile=dict(environment='test',backend='backend',frontend='frontend',database='database',
                          redis='redis',minio='minio',writers=['backend'],writerInventoryConfirmed=True,
                          recoveryInventoryConfirmed=True,stagingRoot=str(self.root.parent),
                          recoveryDataMounts=[dict(role=r,destination='/data') for r in ('redis','minio')])
        self.plan=[dict(migrationId='one',sha256='a'*64,action='SKIP_ALREADY_APPLIED')]
        self.origin=dict(fingerprint='origin-fingerprint',schemaSha256='s'*64,ledgerSha256='l'*64,
                         images=dict(backend='old-backend',frontend='old-frontend'),releaseTag='old',
                         ledgerRecords=[dict(migrationId='one',sha256='a'*64,status='APPLIED')])
        self.obs=dict(self.origin,releaseTag=None,frontendHttpStatus=None)
        self.manifest=dict(releaseTag=self.tag,maintenanceProtocol=agent.PROTOCOL,files=[],
                           migrations=[dict(migrationId='one',sha256='a'*64,type='schema',allowedEnvironments=['test'])],
                           releaseSettings=dict(gxpAuditMode='DEVELOPMENT_DISABLED'),baselines=dict(test=self.origin),
                           images=dict(backend=dict(id='new-backend'),frontend=dict(id='new-frontend')),
                           executionPlans=dict(test=dict(status='passed',targetEnvironment='test',items=self.plan)))
        self.containers={}
        for role in ('backend','frontend','database','redis','minio'):
            self.containers[role]=dict(Id='original-'+role,Name='/'+role,Image='old-'+role,
                State=dict(Running=role in ('database','redis','minio'),StartedAt='original'),
                Config=dict(Env=[],Image='old-'+role,Labels={}),HostConfig={},Mounts=[],NetworkSettings=dict(Networks={}))
        resources=[]
        for i,role in enumerate(('redis','minio')):
            source=self.root/('data-'+role); source.mkdir(); (source/'data').write_bytes(role.encode())
            mount=dict(Type='bind',Source=str(source),Destination='/data',RW=True)
            self.containers[role]['Mounts']=[mount]
            archive=self.root/('recovery-volume-'+str(i)+'.tar')
            with tarfile.open(archive,'w') as stream: stream.add(source/'data',arcname='data')
            resources.append(dict(role=role,containerId='original-'+role,mount=mount,
                                  artifact=dict(path=str(archive),sha256=file_sha(archive),bytes=archive.stat().st_size)))
        self.write('manifest.json',self.manifest)
        (self.root/'release.tar').write_bytes(b'original sealed release')
        (self.root/'recovery.sql').write_bytes(b'full bound database checkpoint')
        self.write('recovery-containers.private.json',self.containers)
        self.recovery=dict(version=1,jobId=self.original,releaseTag=self.tag,origin=copy.deepcopy(self.origin),
                           packageIdentity=package_identity(self.manifest),packageSha256=file_sha(self.root/'release.tar'),
                           manifestSha256=file_sha(self.root/'manifest.json'),path=str(self.root/'recovery.sql'),
                           sha256=file_sha(self.root/'recovery.sql'),includes=['data','schema','triggers','events','routines'],
                           containersSha256=file_sha(self.root/'recovery-containers.private.json'),
                           databaseContainerId='original-database',resources=resources,tableChecksums={'one':'42'})
        self.write('recovery-record.private.json',self.recovery)
        self.write('deployment-progress.private.json',dict(jobId=self.original,releaseTag=self.tag,phase='failed',pid=999999,processStart='gone'))
        self.write('stage-verified.json',dict(manifestSha256=package_identity(self.manifest),files=[],archive=dict(
            archiveSha256=self.recovery['packageSha256'],manifestSha256=self.recovery['manifestSha256'])))
        self.payload=dict(manifest=self.manifest,originalJobId=self.original,retryJobId=self.retry,
                          originalPlan=self.plan,packageSha256=self.recovery['packageSha256'],manifestSha256=self.recovery['manifestSha256'])
        self.result=dict(self.origin,images=dict(backend='new-backend',frontend='new-frontend'),
                         maintenance=False,frontendHttpStatus=200,releaseTag=self.tag)
        self.mocks={}
        functions={
            (agent,'directory'):dict(return_value=self.root),
            (agent,'check_fence'):{},(agent,'observe'):dict(return_value=self.obs),
            (agent,'migration_plan'):dict(return_value=self.plan),
            (agent.remote,'inspect'):dict(side_effect=lambda name:self.containers[name]),
            (agent.remote,'sql'):dict(side_effect=lambda p,q: '' if q.startswith('SELECT migration_id') else 'DEVELOPMENT_DISABLED\t1\t1' if 'system.gxp.audit-mode' in q else '0'),
            (agent.remote,'run'):dict(side_effect=lambda args:args[-1].encode()),
            (agent,'replace'):{},(agent,'docker'):{},(agent,'acceptance_frontend'):{},
            (agent,'terminal_snapshot_readiness'):{},(agent,'health'):dict(return_value={'maintenance':True}),
            (agent,'reopen'):dict(return_value=self.result),(agent,'apply_migration_plan'):{},
            (agent,'persist_gxp_release_mode'):{},(agent,'backup'):{}}
        for (module,name),kwargs in functions.items():
            item=patch.object(module,name,**kwargs);self.mocks[name]=item.start();self.addCleanup(item.stop)
        for target,kwargs in [
            ('intruoyi_rehearsal_agent.process_start_identity',dict(side_effect=lambda pid:'self' if pid==os.getpid() else None)),
            ('intruoyi_recovery_agent.checksums',dict(return_value={'one':'42'}))]:
            item=patch(target,**kwargs);self.mocks[target.rsplit('.',1)[-1]]=item.start();self.addCleanup(item.stop)

    def write(self,name,value): (self.root/name).write_text(json.dumps(value),encoding='utf-8')
    def invoke(self): return agent.resume_test_tail_locked(self.profile,self.payload,self.root)

    def test_sealed_origin_switches_program_only_and_keeps_original_failure(self):
        failed=(self.root/'deployment-progress.private.json').read_bytes()
        result=self.invoke()
        self.assertEqual(result['resumeReceipt']['status'],'completed')
        self.assertEqual(result['resumeReceipt']['resumeMode'],'sealed-origin-program-switch')
        self.assertEqual(self.mocks['replace'].call_count,2)
        for name in ('backup','apply_migration_plan','persist_gxp_release_mode'):
            self.mocks[name].assert_not_called()
        self.assertEqual((self.root/'deployment-progress.private.json').read_bytes(),failed)

    def test_corrupt_volume_origin_drift_live_writer_or_changed_data_blocks_before_switch(self):
        for failure in ('volume','container','writer','data','origin','migration'):
            with self.subTest(failure=failure):
                volume=self.root/'recovery-volume-0.tar'; original=volume.read_bytes()
                if failure=='volume': volume.write_bytes(b'corrupt')
                elif failure=='container': self.containers['backend']['Id']='replacement'
                elif failure=='writer': self.containers['backend']['State']['Running']=True
                elif failure=='data': self.mocks['checksums'].return_value={'one':'43'}
                elif failure=='origin': self.obs['fingerprint']='drift'
                else: self.payload['originalPlan']=[dict(self.plan[0],action='APPLY')]
                with self.assertRaises((ValueError,agent.RuntimeBlocked)): self.invoke()
                self.mocks['replace'].assert_not_called()
                volume.write_bytes(original); self.containers['backend']['Id']='original-backend'
                self.containers['backend']['State']['Running']=False
                self.mocks['checksums'].return_value={'one':'42'}; self.obs['fingerprint']='origin-fingerprint'
                self.payload['originalPlan']=self.plan

    def test_pending_switch_evidence_or_foreign_checkpoint_blocks(self):
        self.write('deployment-pending.json',{'releaseTag':self.tag})
        with self.assertRaises(agent.RuntimeBlocked): self.invoke()
        (self.root/'deployment-pending.json').unlink()
        self.recovery['jobId']='JOB-3333333333'; self.write('recovery-record.private.json',self.recovery)
        with self.assertRaises(agent.RuntimeBlocked): self.invoke()
        self.mocks['replace'].assert_not_called()


if __name__=='__main__': unittest.main()
