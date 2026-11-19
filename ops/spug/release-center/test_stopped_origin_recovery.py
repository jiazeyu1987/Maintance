"""A reviewed, zero-SQL forward recovery cannot become a general stopped-writer bypass."""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from intruoyi_runtime import RuntimeBlocked
import intruoyi_runtime as contract
import intruoyi_runtime_agent as agent


class StoppedOriginRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.origin = dict(releaseTag='2026-11-18-15-49-02', images={'backend':'b','frontend':'f'},
                           runtimeConfigSha256='c', databaseIdentity='db',
                           components={role:dict(containerId=role, imageId=role)
                                       for role in ('backend','frontend','database')})
        self.incident = dict(version='stopped-origin-forward/v1', originalJobId='JOB-882bad6add',
                             originalOperationId='OP-22c6275633b1aeaa3cf7',
                             failedReleaseTag='2026-11-19-15-03-12', origin=self.origin,
                             appliedMigrations=[dict(migrationId='m1',sha256='a'*64)])
        self.observation = dict(self.origin, releaseTag=None, fingerprint='fingerprint',
            components={role:dict(value, running=role=='database')
                        for role,value in self.origin['components'].items()},
            ledgerRecords=[dict(migrationId='m1',sha256='a'*64,status='APPLIED')])
        self.plan = [dict(migrationId='m1',sha256='a'*64,action='SKIP_ALREADY_APPLIED')]

    def test_exact_stopped_origin_and_already_applied_sql_are_required(self):
        result = contract.validate_stopped_forward_origin(self.incident, self.observation,
                                                          self.plan, '2026-11-20-01-01-01')
        self.assertEqual(result, self.origin['releaseTag'])

    def test_every_drift_or_pending_mutation_is_blocked(self):
        for path,value in ((('images','backend'),'other'),
                           (('components','backend','containerId'),'other'),
                           (('components','backend','running'),True),
                           (('components','frontend','running'),True),
                           (('runtimeConfigSha256',),'other'),(('databaseIdentity',),'other'),
                           (('ledgerRecords',),[])):
            observed=copy.deepcopy(self.observation)
            node=observed
            for part in path[:-1]: node=node[part]
            node[path[-1]]=value
            with self.subTest(path=path), self.assertRaises(RuntimeBlocked):
                contract.validate_stopped_forward_origin(self.incident,observed,self.plan,'2026-11-20-01-01-01')
        for action in ('APPLY','BLOCKED','SKIP_NOT_APPLICABLE'):
            with self.subTest(action=action), self.assertRaises(RuntimeBlocked):
                contract.validate_stopped_forward_origin(self.incident,self.observation,
                    [dict(self.plan[0],action=action)],'2026-11-20-01-01-01')
        with self.assertRaises(RuntimeBlocked):
            contract.validate_stopped_forward_origin(self.incident,self.observation,self.plan,self.incident['failedReleaseTag'])

    def test_remote_origin_requires_dead_worker_no_program_switch_and_correction_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            common=Path(temporary).resolve()
            staging=common/'attempts'/self.incident['originalJobId']
            root=staging/self.incident['failedReleaseTag']
            root.mkdir(parents=True)
            manifest_path=root/'manifest.json'
            manifest_path.write_text('{}',encoding='utf-8')
            incident=dict(self.incident,stagingRoot=str(staging),manifestSha256=contract.file_sha(manifest_path))
            profile=dict(environment='prod',stagingRoot=str(common),backend='backend',frontend='frontend',
                         writerInventoryConfirmed=True,writers=['backend'])
            manifest=dict(releaseTag='2026-11-20-01-01-01')
            receipt=dict(action='deploy',status='failed',worker='stopped')
            repair=root/'route-import-index-correction-v1'
            repair.mkdir()
            plan_path=repair/'plan.private.json'
            plan_path.write_text(json.dumps(dict(contract='mes-route-import-index-correction/v1',corrections=[
                dict(id=str(i),originalSha256='a'*64,correctedSha256='b'*64) for i in range(1,6)])),encoding='utf-8')
            (repair/'report.private.json').write_text(json.dumps(dict(status='CORRECTED',rowCount=5,indexCount=74,
                updatedCount=5,planSha256=contract.file_sha(plan_path))),encoding='utf-8')
            raw=io.BytesIO()
            metadata=json.dumps(dict(releaseTag=self.origin['releaseTag'])).encode()
            with tarfile.open(fileobj=raw,mode='w') as archive:
                entry=tarfile.TarInfo('release-info.json');entry.size=len(metadata)
                archive.addfile(entry,io.BytesIO(metadata))
            def sql(profile,text):
                return '0' if 'INNODB_TRX' in text else '1'
            with patch.object(agent,'observe',return_value=self.observation), \
                    patch.object(agent,'migration_plan',return_value=self.plan), \
                    patch.object(agent,'runtime_recovery_policy',return_value='external'), \
                    patch.object(agent,'check_fence'), \
                    patch('operation_journal.inspect',return_value=receipt), \
                    patch.object(agent.remote,'sql',side_effect=sql), \
                    patch.object(agent.remote,'run',return_value=raw.getvalue()) as run:
                result=agent.inspect_stopped_origin(profile,manifest,incident)
                self.assertEqual(result['releaseMetadataSource'],'verified-stopped-container')
                self.assertEqual(result['releaseTag'],self.origin['releaseTag'])
                self.assertEqual(run.call_args.args[0][:2],['docker','cp'])
                for mutation in ('live-worker','program-switched','audit-missing'):
                    with self.subTest(mutation=mutation):
                        if mutation=='live-worker': receipt['worker']='running'
                        elif mutation=='program-switched': (root/'backend-before-initial.private.json').write_text('{}')
                        else: (repair/'report.private.json').unlink()
                        with self.assertRaises((RuntimeBlocked,FileNotFoundError)):
                            agent.inspect_stopped_origin(profile,manifest,incident)
                        receipt['worker']='stopped'
                        (root/'backend-before-initial.private.json').unlink(missing_ok=True)

    def test_correction_cannot_run_without_the_journal_lock(self):
        with self.assertRaisesRegex(RuntimeBlocked,'Journalled maintenance'):
            agent.correct_imported_snapshots({},dict(manifest={},incident={}))
