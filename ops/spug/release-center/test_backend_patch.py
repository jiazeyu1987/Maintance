"""Backend patch contracts; unit tests do not stand in for server acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from backend_patch_contract import validate_manifest, validate_changes, full_release_config
from backend_patch_agent import acquire_fence, release_fence, validate_baseline, verify_unchanged


def manifest():
    return dict(applicationId='intruoyi', kind='backend-patch', releaseTag='2026-11-02-10-00-00',
                baseReleaseTag='2026-11-01-10-00-00', gitCommit='a'*40, baseGitCommit='b'*40,
                databasePolicy='no-migrations-readonly-startup-v1', files=[dict(name='app.jar',sha256='c'*64),
                dict(name='release-info.json',sha256='d'*64)], releaseSettings={'gxpAuditMode':'DEVELOPMENT_DISABLED'})


class ContractTests(unittest.TestCase):
    def test_only_jar_and_metadata_no_migrations_or_images(self):
        validate_manifest(manifest())
        for field,value in [('migrations',[{'sql':'UPDATE x'}]),('images',{'backend':{}}),('sql',[])]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_manifest(dict(manifest(),**{field:value}))
        value=manifest();value['files'].append(dict(name='init.sql',sha256='e'*64))
        with self.assertRaises(ValueError):validate_manifest(value)

    def test_retired_jar_inventory_keeps_manifest_and_checks_real_bytes(self):
        import artifact_files as files
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);value=manifest()
            (root/'app.jar').write_bytes(b'immutable-program')
            (root/'release.tar').write_bytes(b'immutable-archive')
            value['files'][0]['sha256']=files.sha(root/'app.jar')
            (root/'manifest.json').write_text(json.dumps(value),'utf-8')
            rows=files.inventory(root,value,files.sha(root/'manifest.json'),files.sha(root/'release.tar'))
            self.assertEqual({r['relative'] for r in rows},{'app.jar','release.tar'})
            self.assertEqual(files.cleanup_root(root,dict(kind='backend-patch',manifest=value,deploymentJobId='JOB-1234567890')),
                             root/'backend-patches'/value['releaseTag']/'JOB-1234567890')
            (root/'app.jar').write_bytes(b'tampered-program')
            fresh=files.inventory(root,value,files.sha(root/'manifest.json'),files.sha(root/'release.tar'))
            with self.assertRaisesRegex(ValueError,'摘要'):files.remove_file(root,next(r for r in fresh if r['relative']=='app.jar'))

    def test_source_rejects_database_config_dependency_frontend_and_startup_changes(self):
        validate_changes(['IntRuoyiBackend/module/src/main/java/example/service/FixService.java'])
        for path in ['IntRuoyiBackend/sql/change.sql','IntRuoyiBackend/pom.xml',
                     'IntRuoyiBackend/module/src/main/resources/application.yml',
                     'IntRuoyiBackend/module/src/main/java/example/dal/dataobject/UserDO.java',
                     'IntRuoyiFronted/src/a.ts']:
            with self.subTest(path=path),self.assertRaises(ValueError):validate_changes([path])

    def test_full_release_removes_only_verified_owned_jar_mounts(self):
        config={'Env':['SECRET=untouched'], 'HostConfig':{'Binds':['/data:/data:rw','/patch/app.jar:/yudao-server/app.jar:ro',
              '/patch/release-info.json:/yudao-server/release-info.json:ro']},
              'Labels':{'intruoyi.backend-patch.root':'/patch','intruoyi.backend-patch.tag':'patch'}}
        result=full_release_config(copy.deepcopy(config))
        self.assertEqual(result['HostConfig']['Binds'],['/data:/data:rw'])
        self.assertEqual(result['Env'],config['Env'])
        self.assertNotIn('intruoyi.backend-patch.tag',result['Labels'])
        config['HostConfig']['Binds'][1]='/unknown/app.jar:/yudao-server/app.jar:ro'
        with self.assertRaises(ValueError):full_release_config(config)

    def test_full_release_rejects_parent_program_overrides_and_preserves_data(self):
        config={'HostConfig':{'Binds':['/data:/data:rw','/unknown:/yudao-server:ro']}}
        with self.assertRaises(ValueError):full_release_config(config)
        config={'HostConfig':{'Mounts':[{'Target':'/yudao-server','Source':'/unknown','Type':'bind'}]}}
        with self.assertRaises(ValueError):full_release_config(config)


class FenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.remote=Mock();self.remote.inspect.return_value={'Id':'database-id'};self.profile={'database':'mysql'}

    def tearDown(self):self.temp.cleanup()

    def test_external_fence_is_not_taken_or_released(self):
        self.remote.sql.return_value='1\t1'
        with self.assertRaises(ValueError):acquire_fence(self.profile,self.root,self.remote)
        self.assertEqual(self.remote.sql.call_count,1)
        with self.assertRaises((ValueError,FileNotFoundError)):release_fence(self.profile,self.root,self.remote)

    def test_only_transient_fence_sql_is_permitted_and_restored_after_validation(self):
        self.remote.sql.side_effect=['0\t0', '', '', '1\t1','1\t1','', '0\t0']
        acquire_fence(self.profile,self.root,self.remote)
        release_fence(self.profile,self.root,self.remote)
        queries=[c.args[1] for c in self.remote.sql.call_args_list]
        self.assertEqual([q for q in queries if q.startswith('SET ')],
                         ['SET GLOBAL super_read_only=ON;','SET GLOBAL super_read_only=OFF; SET GLOBAL read_only=OFF;'])
        self.assertEqual(json.loads((self.root/'database-fence.json').read_text())['status'],'released')

    def test_replica_cannot_bypass_readonly_during_program_restoration(self):
        self.remote.sql.side_effect=lambda p,q:'replica-thread-active' if q.startswith('SHOW ') else '0\t0' if q.startswith('SELECT ') else ''
        with self.assertRaisesRegex(ValueError,'复制'):
            acquire_fence(self.profile,self.root,self.remote)
        self.assertFalse((self.root/'database-fence.json').exists())
        self.assertFalse(any(c.args[1].startswith('SET ') for c in self.remote.sql.call_args_list))

    def test_database_or_frontend_drift_prevents_success(self):
        before={'schemaSha256':'schema','ledgerSha256':'ledger','databaseIdentity':'db',
                'components':{r:{'containerId':r,'imageId':r,'startedAt':'old'} for r in ('backend','frontend','database')}}
        verify_unchanged(before,copy.deepcopy(before))
        for key in ('schemaSha256','ledgerSha256','databaseIdentity'):
            with self.subTest(key=key),self.assertRaises(ValueError):verify_unchanged(before,dict(before,**{key:'other'}))

    def test_changed_database_identity_cannot_release_original_fence(self):
        (self.root/'database-fence.json').write_text(json.dumps(dict(status='owned',databaseId='original-db')),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'数据库已变化'):release_fence(self.profile,self.root,self.remote)
        self.remote.sql.assert_not_called()

    def test_baseline_must_include_actual_jar_not_only_same_image(self):
        base={e:{'releaseTag':'base','backendJarSha256':'a'*64,'backendPatchTag':None,
                 'backendMetadata':{'sourceCommit':'b'*40},'schemaSha256':'s','ledgerSha256':'d'*64,
                 'components':{r:{'imageId':r} for r in ('backend','frontend')}} for e in ('test','prod','backup')}
        self.assertEqual(validate_baseline(base),'b'*40)
        base['test']['backendJarSha256']='c'*64
        with self.assertRaises(ValueError):validate_baseline(base)

    def test_equivalent_program_and_schema_keep_each_environment_ledger(self):
        origins={env:{'releaseTag':'base','backendJarSha256':'a'*64,
                      'backendMetadata':{'sourceCommit':'b'*40},'schemaSha256':'same-schema',
                      'ledgerSha256':{'test':'c','prod':'d','backup':'e'}[env]*64,'databaseIdentity':env+'-database',
                      'components':{r:{'imageId':r,'containerId':env+'-'+r}
                                    for r in ('backend','frontend','database')}}
                 for env in ('test','prod','backup')}
        original=copy.deepcopy(origins)
        self.assertEqual(validate_baseline(origins),'b'*40)
        self.assertEqual(origins,original)
        missing=copy.deepcopy(origins);missing['test'].pop('ledgerSha256')
        with self.assertRaisesRegex(ValueError,'本环境迁移台账摘要'):validate_baseline(missing)
        for env,origin in origins.items():
            verify_unchanged(origin,copy.deepcopy(origin))
            with self.subTest(env=env),self.assertRaisesRegex(ValueError,'ledgerSha256'):
                verify_unchanged(origin,dict(origin,ledgerSha256=origins['prod' if env=='test' else 'test']['ledgerSha256']))
        origins['test']['schemaSha256']='changed-schema'
        with self.assertRaises(ValueError):validate_baseline(origins)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        from backend_patch import BackendPatchMixin
        from executor import digest
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.m=manifest()
        (root/'manifest.json').write_text(json.dumps(self.m),'utf-8')
        self.p=dict(releaseTag=self.m['releaseTag'],baseReleaseTag=self.m['baseReleaseTag'],gitCommit=self.m['gitCommit'],
                    directory=str(root),manifestSha256=digest(root/'manifest.json'),accepted={},deployments={})
        self.e=BackendPatchMixin();self.e.state=dict(backendPatches=[self.p],jobs=[],backendPatchEnvironments={
            e:dict(releaseTag=self.m['baseReleaseTag']) for e in ('test','prod','backup')})
        self.e.frontend_failure_blocks=lambda j,e:False
        self.payload=dict(releaseTag=self.m['releaseTag'],target='prod',note='真实页面验收通过',confirmation='PROD')

    def test_same_jar_sequential_promotions_and_explicit_prod_confirmation(self):
        with self.assertRaisesRegex(ValueError,'前一服'):self.e.backend_gate('backend-patch-deploy',self.payload)
        self.p['accepted']['test']={'jobId':'test'}
        self.e.state['backendPatchEnvironments']['test']['backendPatchTag']=self.p['releaseTag']
        self.e.backend_gate('backend-patch-deploy',self.payload)
        with self.assertRaisesRegex(ValueError,'PROD'):self.e.backend_gate('backend-patch-deploy',dict(self.payload,confirmation=''))
        with self.assertRaisesRegex(ValueError,'前一服'):self.e.backend_gate('backend-patch-deploy',dict(self.payload,target='backup'))

    def test_restore_binds_original_package_target_and_effects(self):
        old=dict(id='JOB-1234567890',action='backend-patch-deploy',status='failed',effectsStarted=True,
                 target='prod',releaseTag=self.p['releaseTag'])
        self.e.state['jobs']=[old]
        self.e.backend_gate('backend-patch-restore',dict(self.payload,originalJobId=old['id']))
        with self.assertRaisesRegex(ValueError,'恢复任务'):
            self.e.backend_gate('backend-patch-restore',dict(self.payload,originalJobId=old['id'],target='test'))

    def test_failed_build_can_only_retry_a_sealed_original(self):
        old=dict(id='JOB-1234567890',action='backend-patch-build',status='failed')
        self.e.state['jobs']=[old]
        payload=dict(self.payload,originalJobId=old['id'])
        with self.assertRaisesRegex(ValueError,'已封包'):self.e.backend_gate('backend-patch-retry-upload',payload)
        old['sealedPackage']={'sha256':'original'}
        self.e.backend_gate('backend-patch-retry-upload',payload)

    def test_later_full_release_must_include_active_patch_source(self):
        from backend_patch import BackendPatchMixin
        class Parent:
            def submit(self,*args):return 'admitted'
        class Combined(BackendPatchMixin,Parent):pass
        e=Combined();e.state=self.e.state;e.c={'repo':'source-repo'};e.run=Mock()
        e.state['environments']={}
        e.state['backendPatchEnvironments']['test']['backendPatchTag']=self.p['releaseTag']
        self.assertEqual(e.submit('build-release',{'commit':'f'*40},'actor'),'admitted')
        self.assertEqual(e.run.call_args.args[0][-4:],['merge-base','--is-ancestor',self.p['gitCommit'],'f'*40])
        e.run.side_effect=ValueError('patch source omitted')
        with self.assertRaisesRegex(ValueError,'omitted'):e.submit('build-release',{'commit':'e'*40},'actor')

    def test_frontend_patch_rejects_same_image_with_a_different_jar(self):
        from frontend_patch_agent import validate_origin
        from executor import require
        before=dict(releaseTag='base',components={'backend':{'imageId':'image'}},backendProgram={'backendPatchTag':'p','backendJarSha256':'a'})
        with self.assertRaisesRegex(ValueError,'JAR'):
            validate_origin(before,before,dict(baseReleaseTag='base',backendImageId='image'),{'require':require})

    def test_fault_after_fencing_keeps_database_protected_and_receipt(self):
        import backend_patch_agent as agent
        job='JOB-1234567890';root=Path(self.temp.name)/'backend-patches'/self.m['releaseTag']/job
        root.mkdir(parents=True)
        before={'releaseTag':self.m['baseReleaseTag']}
        self.m['baseline']={'origins':{'test':before}}
        (root/'manifest.json').write_text(json.dumps(self.m),'utf-8')
        snapshot=dict(Id='old',Image='image',Config={'WorkingDir':'/yudao-server','Cmd':['sh','-c','java -jar app.jar']},
                      State={'Running':True})
        remote=Mock();remote.inspect.return_value=snapshot
        remote.sql.side_effect=['','0\t0','0\t0','','','1\t1']
        a=dict(remote=remote,verify_files=Mock(),private_json=Mock(),stop_writers=Mock(),
               clone_config=Mock(return_value={'HostConfig':{}}))
        payload=dict(action='backend-patch-deploy',workflowJobId=job,manifest=self.m,origin=before,archive={'sha256':'c'*64})
        with patch.object(agent,'observation',return_value=before),patch.object(agent,'replace_backend',side_effect=RuntimeError('create failed')):
            with self.assertRaisesRegex(RuntimeError,'create failed'):
                agent.execute(dict(stagingRoot=self.temp.name,environment='test',database='db',backend='backend',frontend='front',
                                   writers=['backend'],writerInventoryConfirmed=True),payload,a)
        self.assertEqual(json.loads((root/'database-fence.json').read_text())['status'],'owned')
        self.assertEqual(json.loads((root/'deployment.json').read_text())['status'],'failed')
        self.assertFalse(any('OFF' in c.args[1] for c in remote.sql.call_args_list))


if __name__=='__main__':unittest.main()
