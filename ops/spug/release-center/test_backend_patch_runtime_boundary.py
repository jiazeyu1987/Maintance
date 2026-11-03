"""User approved readonly maintenance proof, followed by original normal runtime."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import backend_patch_agent as agent
from test_backend_patch import manifest
from backend_patch_contract import validate_manifest


class RuntimeBoundaryTests(unittest.TestCase):
    def test_unknown_policy_cannot_change_the_startup_contract(self):
        value=manifest();value['databasePolicy']='unknown'
        with self.assertRaises(ValueError):validate_manifest(value)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.profile=dict(stagingRoot=self.temp.name,environment='prod',database='db',backend='backend',frontend='front',writers=['backend'],writerInventoryConfirmed=True)
        self.value=manifest();self.value['databasePolicy']='no-migrations-readonly-probe-normal-runtime-v2'
        self.before=dict(releaseTag=self.value['baseReleaseTag'],backendJarSha256='c'*64)
        self.value['baseline']={'origins':{'prod':self.before}}
        self.job='JOB-1234567890'
        self.root=Path(self.temp.name)/'backend-patches'/self.value['releaseTag']/self.job
        self.root.mkdir(parents=True)
        (self.root/'manifest.json').write_text(json.dumps(self.value),encoding='utf-8')
        self.events=[];self.readonly=False
        self.snapshot=dict(Id='old',Image='image',Config={'WorkingDir':'/yudao-server','Cmd':['sh','-c','java -jar app.jar']},State={'Running':True,'ExitCode':0})
        self.remote=Mock();self.remote.inspect.side_effect=lambda name:dict(Id='database-id') if name=='db' else self.snapshot
        self.remote.sql.side_effect=lambda p,q:'' if q.startswith('SHOW ') else '0\t0'
        self.remote.run.return_value=b'backend\nfront\n'
        self.api=dict(remote=self.remote,verify_files=Mock(),private_json=Mock(),stop_writers=Mock(),clone_config=Mock(return_value={'HostConfig':{}}))
        self.payload=dict(action='backend-patch-deploy',workflowJobId=self.job,manifest=self.value,origin=self.before,archive={'sha256':'c'*64})

    def run_deploy(self, failure=None):
        def acquire(*args):
            self.readonly=True;self.events.append('acquire')
        def release(*args):
            self.assertTrue(self.readonly);self.readonly=False;self.events.append('release')
        def health(profile,api,tag,maintenance):
            self.events.append('probe-health' if maintenance else 'normal-health')
            self.assertEqual(self.readonly,maintenance or self.value['databasePolicy']=='no-migrations-readonly-startup-v1',
                             'V2 normal startup uses original write path; V1 keeps its original contract')
            if failure==('probe' if maintenance else 'normal'):raise RuntimeError('startup failed')
        def unchanged(*args):self.events.append('unchanged')
        def reclose(*args):self.readonly=True;self.events.append('reclose')
        with patch.object(agent,'observation',return_value=dict(self.before,backendJarSha256='c'*64)),patch.object(agent,'acquire_fence',side_effect=acquire),patch.object(agent,'release_fence',side_effect=release),patch.object(agent,'replace_backend'),patch.object(agent,'wait_backend',side_effect=health),patch.object(agent,'check_startup_writes',side_effect=lambda *a:self.events.append('logs')),patch.object(agent,'database_program_observation',return_value=dict(self.before,backendJarSha256='c'*64)),patch.object(agent,'verify_unchanged',side_effect=unchanged),patch.object(agent,'reclose_owned_fence',side_effect=reclose):
            return agent.execute(self.profile,self.payload,self.api)

    def test_probe_is_checked_before_owned_release_and_normal_start(self):
        result=self.run_deploy()
        self.assertLess(self.events.index('probe-health'),self.events.index('unchanged'))
        self.assertLess(self.events.index('unchanged'),self.events.index('release'))
        self.assertLess(self.events.index('release'),self.events.index('normal-health'))
        self.assertEqual(self.events.count('release'),1)
        self.assertTrue(result['readonlyProbeVerified'])
        self.assertTrue(result['normalRuntimeWritesAllowed'])
        self.assertFalse(result['databaseSchemaChanged'])
        self.assertFalse(result['migrationsExecuted'])
        self.assertNotIn('databaseChanged',result,'Do not claim zero runtime database writes')

    def test_old_sealed_v1_keeps_strict_normal_startup(self):
        self.value['databasePolicy']='no-migrations-readonly-startup-v1'
        (self.root/'manifest.json').write_text(json.dumps(self.value),encoding='utf-8')
        result=self.run_deploy()
        self.assertLess(self.events.index('normal-health'),self.events.index('release'))
        self.assertFalse(result['databaseChanged'])
        self.assertNotIn('normalRuntimeWritesAllowed',result)

    def test_probe_failure_never_releases_or_enters_normal_start(self):
        with self.assertRaisesRegex(RuntimeError,'startup failed'):self.run_deploy('probe')
        self.assertTrue(self.readonly)
        self.assertNotIn('release',self.events);self.assertNotIn('normal-health',self.events)

    def test_normal_failure_reprotects_and_does_not_open_frontend(self):
        with self.assertRaisesRegex(RuntimeError,'startup failed'):self.run_deploy('normal')
        self.assertTrue(self.readonly);self.assertIn('reclose',self.events)
        self.assertFalse(any(c.args[0][:2]==['docker','start'] and c.args[0][-1]=='front' for c in self.remote.run.call_args_list))
        self.assertEqual(json.loads((self.root/'deployment.json').read_text())['status'],'failed')

    def test_reclose_stops_owned_writers_and_checks_identity_before_global_write(self):
        (self.root/'database-fence.json').write_text(json.dumps(dict(status='released',databaseId='database-id')),encoding='utf-8')
        self.remote.inspect.side_effect=lambda name:dict(Id='database-id') if name=='db' else dict(State={'Running':False,'ExitCode':1})
        self.remote.sql.side_effect=['0','0\t0','','1\t1']
        agent.reclose_owned_fence(self.profile,self.root,self.api)
        self.assertEqual(json.loads((self.root/'database-fence.json').read_text())['status'],'owned')
        self.assertEqual([c.args[1] for c in self.remote.sql.call_args_list if c.args[1].startswith('SET ')],['SET GLOBAL super_read_only=ON;'])

    def test_reclose_refuses_external_protection_and_changed_database(self):
        for identity,readonly in [('different','0\t0'),('database-id','1\t1')]:
            with self.subTest(identity=identity,readonly=readonly):
                (self.root/'database-fence.json').write_text(json.dumps(dict(status='released',databaseId=identity)),encoding='utf-8')
                self.remote.inspect.side_effect=lambda name:dict(Id='database-id') if name=='db' else dict(State={'Running':False,'ExitCode':0})
                self.remote.sql.side_effect=None
                self.remote.sql.side_effect=lambda p,q: '0' if 'COUNT(*)' in q else readonly
                with self.assertRaises(ValueError):agent.reclose_owned_fence(self.profile,self.root,self.api)
                self.assertFalse(any(c.args[1].startswith('SET ') for c in self.remote.sql.call_args_list))

if __name__=='__main__':unittest.main()
