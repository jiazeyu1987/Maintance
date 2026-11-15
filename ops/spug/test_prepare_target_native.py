"""Local filesystem tests; these do not claim a remote Docker acceptance run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import prepare_target_native as native


class NativePreparationTests(unittest.TestCase):
    @contextmanager
    def retained_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);state=base/'state';state.mkdir();host=base/'host';host.mkdir()
            data=base/'data';data.mkdir();old_id='prepare-original'
            previous=state/native.hashlib.sha256(old_id.encode()).hexdigest();previous.mkdir()
            target='spug-empty59-'+previous.name[:12];(data/target).mkdir()
            native.write(previous/'request.json',dict(operationId=old_id))
            native.write(previous/'result.json',dict(operationId=old_id,state='INITIALIZED',targetConfigRef=target))
            native.write(state/'last-target.json',dict(directories=[str(data/target)],containerIds=['old-container'],
                volumeNames=[],networkIds=[],serviceNames=[]))
            restore=previous/'recovery-operations'/'restore-original';restore.mkdir(parents=True)
            native.write(restore/'request.json',dict(operationId=restore.name,action='RESTORE',targetConfigRef=target))
            binding=dict(operationId=restore.name,targetConfigRef=target,operationRoot=str(restore),machineId='machine')
            reservation=native.write(restore/'resource-reservation.json',binding)
            active=dict(binding,reservationPin=reservation);native.write(host/'active.json',active)
            result=dict(operationId=restore.name,action='RESTORE',state='FAILED_RETAINED',actualExitCode=1,
                        finishedAt='finished',data=dict(mutationDispatched=True,partialTargetRetained=True))
            worker_pin=native.write(restore/'worker-result.json',result)
            exit_pin=native.write(restore/'child-exit.json',dict(operation='W04_RESTORE_CHILD',actualExitCode=1,
                timedOut=False,finishedAt='finished'))
            native.write(restore/'result.json',dict(result,originalResultPins=[reservation,worker_pin,exit_pin]))
            worker=native.NativePreparation(dict(host=native.HOST,stateRoot=str(state),dataRoot=str(data),
                targetPrefix='spug-empty59',hostReservationRoot=str(host),machineId='machine'))
            events=[]
            @contextmanager
            def locked():
                events.append('locked')
                try:yield
                finally:events.append('unlocked')
            def dependencies(request,root):
                self.assertTrue((host/'active.json').exists());events.append('dependencies')
            def cleanup():
                self.assertFalse((host/'active.json').exists());self.assertNotIn('unlocked',events)
                events.append('cleanup')
            request=dict(operationId='prepare-reset',applicationId='app',recoveryPointRef='point',
                         planDigest='confirmed-digest',confirmed=True)
            with patch.object(worker,'host_lock',locked),patch.object(worker,'plan',return_value=dict(planDigest='confirmed-digest')), \
                 patch.object(worker,'dependencies',side_effect=dependencies),patch.object(worker,'cleanup',side_effect=cleanup), \
                 patch.object(worker,'initialize',return_value=dict(targetConfigRef='new-target')):
                yield worker,request,restore,host,events

    def test_confirmed_preparation_resets_only_exited_current_failed_target(self):
        with self.retained_restore() as (worker,request,restore,host,events):
            original=(restore/'result.json').read_bytes()
            result=worker.execute(request,lambda event:None)
            self.assertEqual(result['state'],'INITIALIZED')
            self.assertEqual(events,['locked','dependencies','cleanup','unlocked'])
            self.assertEqual((restore/'result.json').read_bytes(),original)
            root=Path(worker.config['stateRoot'])/native.hashlib.sha256(request['operationId'].encode()).hexdigest()
            receipt=native.read(root/'restore-reset.json')
            self.assertEqual(receipt['previousReservation']['operationId'],restore.name)
            self.assertEqual(receipt['reason'],'PREPARED_TARGET_REINITIALIZATION')
            self.assertFalse((host/'active.json').exists())
            self.assertEqual(worker.execute(request,lambda event:None),result)
            self.assertEqual(events,['locked','dependencies','cleanup','unlocked','locked','unlocked'])
            self.assertEqual(native.read(root/'restore-reset.json'),receipt)

    def test_running_unknown_and_other_targets_cannot_be_reset(self):
        for scenario in ('running','unknown-exit','other-target','not-current'):
            with self.subTest(scenario=scenario),self.retained_restore() as (worker,request,restore,host,events):
                if scenario=='running':
                    result=native.read(restore/'result.json');result['state']='RUNNING';native.write(restore/'result.json',result)
                elif scenario=='unknown-exit':
                    exited=native.read(restore/'child-exit.json');exited['actualExitCode']=None
                    native.write(restore/'child-exit.json',exited)
                elif scenario=='other-target':
                    active=native.read(host/'active.json');active['targetConfigRef']='other-target';native.write(host/'active.json',active)
                else:
                    native.write(Path(worker.config['stateRoot'])/'last-target.json',dict(directories=['/different-target']))
                before=(host/'active.json').read_bytes()
                with self.assertRaisesRegex(native.PreparationError,'PREPARE_RESTORE_ACTIVE'):
                    worker.execute(request,lambda event:None)
                self.assertEqual((host/'active.json').read_bytes(),before)
                self.assertEqual(events,['locked','unlocked'])

    def test_unconfirmed_or_dependency_failure_keeps_failed_reservation(self):
        for scenario in ('unconfirmed','dependencies'):
            with self.subTest(scenario=scenario),self.retained_restore() as (worker,request,restore,host,events):
                before=(host/'active.json').read_bytes()
                if scenario=='unconfirmed':
                    request['confirmed']=False
                    with self.assertRaisesRegex(native.PreparationError,'PREPARE_PLAN_CHANGED'):
                        worker.execute(request,lambda event:None)
                else:
                    with patch.object(worker,'dependencies',side_effect=native.PreparationError('DEPENDENCIES_FAILED')):
                        self.assertEqual(worker.execute(request,lambda event:None)['state'],'FAILED')
                self.assertEqual((host/'active.json').read_bytes(),before)
                self.assertNotIn('cleanup',events)

    @contextmanager
    def local_volume_bind(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'data';source=data/'old'/'minio'
            target=data/'docker'/'volumes'/'old-minio'/'_data'
            source.mkdir(parents=True);target.mkdir(parents=True)
            calls=[]
            config=dict(host=native.HOST,stateRoot=str(root/'state'),dataRoot=str(data),
                toolRoot=str(root/'tools'),dockerRoot=str(data/'docker'),archiveRoots=[str(root/'nas')],
                cleanup=dict(volumeNames=['old-minio'],bindMounts=[dict(target=str(target),source=str(source))]))
            class Local(native.NativePreparation):
                def docker(self,*args,**kwargs):
                    calls.append(args)
                    if args[:2]==('volume','ls'):return 'old-minio'
                    if args[:2]==('volume','inspect'):return json.dumps([dict(Name='old-minio',Mountpoint=str(target),Options=None)])
                    return ''
            mounts=[dict(target=str(data),root='/',device='253:2',filesystem='xfs',source='/dev/mapper/data'),
                    dict(target=str(target),root='/old/minio',device='253:2',filesystem='xfs',source='/dev/mapper/data')]
            with patch.object(native,'mount_paths',return_value=[]),patch.object(native,'mount_entries',create=True,return_value=mounts), \
                 patch.object(native,'command',side_effect=lambda argv,**kwargs:calls.append(tuple(argv)) or ''):
                yield Local(config),calls,source,target,mounts

    def test_declared_local_bind_unmounts_before_volume_deletion(self):
        with self.local_volume_bind() as (worker,calls,source,target,mounts):
            worker.cleanup()
            self.assertLess(calls.index(('umount','--',str(target))),calls.index(('volume','rm','old-minio')))
            self.assertTrue(source.is_dir())

    def test_absent_old_bind_does_not_unmount_or_prevent_new_preparation(self):
        with self.local_volume_bind() as (worker,calls,source,target,mounts):
            mounts.pop();worker.cleanup()
            self.assertIn(('volume','rm','old-minio'),calls)
            self.assertFalse(any(call[0]=='umount' for call in calls))

    def test_changed_bind_source_or_network_mount_is_refused_before_deletion(self):
        for change in ('root','filesystem','unlisted'):
            with self.subTest(change=change),self.local_volume_bind() as (worker,calls,source,target,mounts):
                if change=='root':mounts[-1]['root']='/different'
                elif change=='filesystem':mounts[0]['filesystem']=mounts[-1]['filesystem']='nfs4'
                else:worker.config['cleanup']['volumeNames']=[]
                with self.assertRaises(native.PreparationError):worker.cleanup()
                self.assertFalse(any(call[0]=='umount' or call[:2]==('volume','rm') for call in calls))

    def test_command_failure_retains_safe_action_object_and_exit_code(self):
        with patch.object(native.subprocess,'run',return_value=native.subprocess.CompletedProcess(
                [],1,b'',b'unlinkat /private-secret-token: device or resource busy')):
            with self.assertRaises(native.PreparationError) as raised:
                native.command(['docker','volume','rm','old-minio','secret-argv'],action='DOCKER_VOLUME_RM',subject='old-minio')
        self.assertEqual(raised.exception.failure,dict(action='DOCKER_VOLUME_RM',object='old-minio',exitCode=1,reason='RESOURCE_BUSY'))
        self.assertNotIn('secret',str(raised.exception)+json.dumps(raised.exception.failure))

    def test_failed_unmount_stops_before_volume_delete_and_persists_diagnostic(self):
        failure=dict(action='UNMOUNT',object='old-minio',exitCode=32,reason='RESOURCE_BUSY')
        with self.local_volume_bind() as (worker,calls,source,target,mounts),tempfile.TemporaryDirectory() as folder:
            with patch.object(worker,'dependencies'),patch.object(worker,'initialize') as initialize, \
                 patch.object(native,'command',side_effect=native.PreparationError('PREPARE_NATIVE_COMMAND_FAILED',failure)):
                result=worker.run_stages(dict(operationId='failed-unmount',applicationId='app',recoveryPointRef='point'),
                                         Path(folder),lambda event:None)
            initialize.assert_not_called()
            self.assertEqual(native.read(Path(folder)/'result.json')['failure'],failure)
            self.assertEqual(result['state'],'FAILED')
            self.assertEqual(result['stages'][-1]['failure'],failure)
            self.assertNotIn(('volume','rm','old-minio'),calls)

    def test_unknown_query_fences_stopped_operation_before_allowing_reset(self):
        with tempfile.TemporaryDirectory() as folder:
            request=dict(operationId='unknown-operation',applicationId='app',recoveryPointRef='point',confirmed=True,planDigest='a'*64)
            worker=native.NativePreparation(dict(host=native.HOST,stateRoot=folder,
                hostReservationRoot='/var/lib/spug-restore-resources'))
            @contextmanager
            def unlocked():yield
            with patch.object(worker,'host_lock',unlocked),patch.object(worker,'identity'):
                result=worker.query(request)
                self.assertEqual(worker.execute(request,lambda event:None)['state'],'FAILED')
            self.assertTrue(result['workerStopped']);self.assertEqual(result['state'],'FAILED')
            root=Path(folder)/native.hashlib.sha256(request['operationId'].encode()).hexdigest()
            self.assertEqual(native.read(root/'request.json'),request)
            self.assertEqual(native.read(root/'result.json')['state'],'FAILED')

    def test_unknown_query_never_calls_busy_worker_stopped(self):
        with tempfile.TemporaryDirectory() as folder:
            worker=native.NativePreparation(dict(host=native.HOST,stateRoot=folder,
                hostReservationRoot='/var/lib/spug-restore-resources'))
            @contextmanager
            def busy():
                raise native.PreparationError('PREPARE_TARGET_BUSY')
                yield
            with patch.object(worker,'host_lock',busy),patch.object(worker,'identity'):
                result=worker.query({'operationId':'unknown-operation'})
            self.assertFalse(result['workerStopped']);self.assertEqual(result['state'],'UNKNOWN')
    def test_cleanup_rejects_root_protected_ancestors_and_mounts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'data').mkdir(); (root/'data'/'tools').mkdir()
            (root/'data'/'old').mkdir(); (root/'data'/'old'/'nas').mkdir()
            for candidate in [root/'data', root/'data'/'tools', root/'data'/'old']:
                with self.assertRaises(native.PreparationError):
                    native.validate_cleanup_paths([str(candidate)], str(root/'data'),
                        [str(root/'data'/'tools')], [str(root/'data'/'old'/'nas')])

    def test_cleanup_rejects_parent_path_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'data').mkdir(); (root/'outside').mkdir()
            with self.assertRaises(native.PreparationError):
                native.validate_cleanup_paths([str(root/'data'/'..'/'outside')],str(root/'data'),[],[])

    def test_copy_dependencies_fails_before_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'tools').mkdir(); (root/'old').mkdir()
            with self.assertRaises(native.PreparationError):
                native.copy_dependencies([{'source':str(root/'missing'),'destination':'secret'}],root/'tools')
            self.assertTrue((root/'old').is_dir())

    def test_copy_dependencies_preserves_bytes_without_exposing_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'tools').mkdir(); (root/'source').write_bytes(b'private-value')
            result=native.copy_dependencies([{'source':str(root/'source'),'destination':'private/key'}],root/'tools')
            self.assertEqual((root/'tools'/'private'/'key').read_bytes(),b'private-value')
            self.assertNotIn('private-value',json.dumps(result))

    def test_preserved_dependencies_are_reusable_after_old_directory_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'tools').mkdir();(root/'old').mkdir()
            (root/'old'/'secret').write_bytes(b'kept-secret')
            native.write(root/'old'/'owner.json',{'sources':{'source':{}}})
            entries=[{'source':str(root/'old'/'secret'),'destination':'private/secret'}]
            templates={'owner':str(root/'old'/'owner.json')}
            first=native.retained_dependencies(entries,root/'tools',templates)
            (root/'old'/'secret').unlink();(root/'old'/'owner.json').unlink();(root/'old').rmdir()
            second=native.retained_dependencies(entries,root/'tools',templates)
            self.assertEqual(first,second)
            (root/'tools'/'private'/'secret').write_bytes(b'changed')
            with self.assertRaisesRegex(native.PreparationError,'PREPARE_RETAINED_DEPENDENCY_CHANGED'):
                native.retained_dependencies(entries,root/'tools',templates)

    def test_owner_uses_new_resource_identities(self):
        old={'targetId':'old','dataRoot':'/old','networkId':'old-network','services':[
            {'role':r,'id':'old-'+r,'imageId':'image-'+r,'ip':'172.1.1.2'} for r in native.ROLES],
            'dataPolicy':{'databaseUuid':'old-uuid'},'application':{'databaseUuid':'old-uuid',
                'container': 'old-backend', 'imageBindings':[{'role':'backend','imageId':'image-backend'}]}}
        observed={'targetId':'new','dataRoot':'/new','networkId':'new-net','databaseUuid':'new-uuid',
            'services':[{'role':r,'id':'new-'+r,'imageId':'new-image-'+r,'ip':'172.2.2.2'} for r in native.ROLES]}
        target=native.fresh_target(old,observed,{})
        self.assertEqual(target['services'],observed['services'])
        self.assertEqual(target['networkId'],'new-net')
        self.assertIs(target['preparedEmptyTarget'],True)
        self.assertEqual(target['dataPolicy']['databaseUuid'],'new-uuid')
        self.assertNotIn('old-uuid',json.dumps(target))
        self.assertEqual(target['application']['container'],'new-backend')
        self.assertEqual(target['application']['imageBindings'][0]['imageId'],'new-image-backend')

    def test_failed_stage_is_emitted_and_later_steps_do_not_run(self):
        class Failing(native.NativePreparation):
            def dependencies(self,request,root): raise native.PreparationError('PREPARE_DEPENDENCY_MISSING')
            def cleanup(self): self.fail_later_step=True
            def initialize(self,request,root): self.fail_later_step=True
        worker=Failing({'host':native.HOST});worker.fail_later_step=False
        events=[]
        with tempfile.TemporaryDirectory() as folder:
            result=worker.run_stages({'operationId':'test-failure','applicationId':'app','recoveryPointRef':'point'},
                Path(folder),lambda event:events.append(deepcopy(event)))
            saved=native.read(Path(folder)/'result.json')
        self.assertFalse(worker.fail_later_step)
        self.assertEqual(result['state'],'FAILED')
        self.assertEqual(saved,result)
        self.assertEqual([e['stage']['state'] for e in events if e['type']=='stage'],['RUNNING','FAILED'])
        self.assertEqual(events[-1]['record']['state'],'FAILED')

    def test_native_success_requires_all_stages_but_never_claims_spug_ready(self):
        calls=[]
        class Sequence(native.NativePreparation):
            def dependencies(self,request,root): calls.append('dependencies')
            def cleanup(self): calls.append('cleanup')
            def initialize(self,request,root):
                calls.append('initialize');return {'targetConfigRef':'new-target'}
        with tempfile.TemporaryDirectory() as folder:
            result=Sequence({'host':native.HOST}).run_stages(
                {'operationId':'test-success','applicationId':'app','recoveryPointRef':'point'},Path(folder),lambda event:None)
        self.assertEqual(calls,list(native.STAGES))
        self.assertEqual(result['state'],'INITIALIZED')
        self.assertEqual([s['state'] for s in result['stages']],['SUCCEEDED']*3)

    def test_invalid_host_rejected(self):
        with self.assertRaises(native.PreparationError):native.NativePreparation({'host':'172.30.30.57'})

    def test_next_preview_contains_only_explicit_and_previously_created_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            native.write(root/'last-target.json',{'directories':['/data/last'],'containerIds':['last-id'],
                'volumeNames':[],'networkIds':['last-network'],'serviceNames':['spug-prepare59-restore.service']})
            worker=native.NativePreparation({'host':native.HOST,'stateRoot':str(root),
                'cleanup':{'directories':['/data/old'],'containerIds':['old-id'],'volumeNames':['old-volume']}})
            selected=worker.cleanup_set()
            self.assertEqual(selected['directories'],['/data/old','/data/last'])
            self.assertEqual(selected['containerIds'],['old-id','last-id'])
            self.assertEqual(selected['networkIds'],['last-network'])

    def test_reinitializing_owned_container_does_not_remove_its_preserved_bind(self):
        calls=[];identity='a'*64
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'tools').mkdir();(root/'tools'/'key').write_bytes(b'keep')
            config=dict(host=native.HOST,stateRoot=str(root),dataRoot=str(root),toolRoot=str(root/'tools'),
                dockerRoot=str(root/'docker'),archiveRoots=[],cleanup={'containerIds':[identity]})
            class LocalBoundary(native.NativePreparation):
                def docker(self,*args,**kwargs):
                    calls.append(args)
                    if args[0]=='ps':return identity
                    if args[:2] in [('volume','ls'),('network','ls')]:return ''
                    if args[0]=='inspect':return json.dumps([{'Id':identity,'Mounts':[{'Source':str(root/'tools'/'key')}]}])
                    return ''
            with patch.object(native,'mount_paths',lambda:[]):LocalBoundary(config).cleanup()
            self.assertEqual((root/'tools'/'key').read_bytes(),b'keep')
        self.assertIn(('rm',identity),calls)

    def test_control_command_reaches_real_cli_serve_mode(self):
        resources=Path(__file__).resolve().parents[2]/'backend/src/main/resources'
        sys.path.insert(0,str(resources))
        import recovery_control_smallapp as control
        reference={'path':'/private/control.json','bytes':2,'sha256':'a'*64}
        args=native.control_arguments('/python','/engine',reference)
        observed=[]
        with patch.object(sys,'argv',args[2:]),patch.object(control,'serve',lambda ref:observed.append(ref)):
            self.assertEqual(control.main(),0)
        self.assertEqual(observed,[reference])

    def test_new_control_configuration_is_read_by_current_control_contract(self):
        resources=Path(__file__).resolve().parents[2]/'backend/src/main/resources'
        sys.path.insert(0,str(resources))
        import recovery_control_smallapp_native as consumer
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('ledger','registry','registry/applications','registry/points'):(root/name).mkdir()
            for role in ('recovery','repository'):(root/(role+'_entry.py')).write_bytes(role.encode())
            executable=native.pin(sys.executable)
            template=dict(schemaVersion='SmallAppExecutionServiceConfig/v2',taskRoot='/old',ledgerRoot='/old/ledger',
                registryRoot='/old/registry',listenAddress='127.0.0.1',listenPort=43059,authCredentialRef={},
                allowedClientAddresses=['127.0.0.1'],pythonPin=executable,programPins={'repository':executable,'recovery':executable},
                workingDirectory='/old',environment={'PATH':'/usr/bin'},deadlineMilliseconds=60000,
                engineSelectionRef='installed-engine',sourceConfigurations={'source':executable},restoreConfigurations={})
            setting={'listenAddress':'172.30.30.59','listenPort':43059,'pythonPath':sys.executable,'engineDirectory':str(root),
                     'allowedClientAddresses':['192.168.109.82']}
            receipt={'sourceConfigRef':'source','targetConfigRef':'fresh','ownerPin':executable}
            document=native.control_document(template,setting,root,receipt,{})
            reference=native.write(root/'control.json',document)
            # Linux custody is separately enforced in production; this is a real JSON/field-contract check on Windows.
            with patch.object(consumer,'native_required'),patch.object(consumer,'directory',lambda path,scope:Path(path)):
                actual=consumer.Native(reference).configuration()
            self.assertEqual(actual['restoreConfigurations']['source']['fresh'],executable)
            self.assertIn(Path(actual['taskRoot']),Path(actual['registryRoot']).parents)
            self.assertEqual(actual['allowedClientAddresses'],['192.168.109.82'])
            self.assertEqual(actual['authCredentialRef'],template['authCredentialRef'])

    def test_control_uses_selected_engine_entries_and_module_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);engine=root/'engine';engine.mkdir()
            for role in ('recovery','repository'):(engine/(role+'_entry.py')).write_bytes(('new-'+role).encode())
            old='/installed/old-engine'
            old_pins={role:dict(path=old+'/'+role+'_entry.py',bytes=5,sha256='a'*64)
                      for role in ('recovery','repository')}
            template=dict(programPins=old_pins,environment=dict(PATH='/usr/bin',
                PYTHONPATH=old+'/control:'+old+'/common:'+old+'/formal:/python/site-packages:'+old+'-other/common'))
            before=deepcopy(template)
            setting=dict(listenAddress=native.HOST,listenPort=43059,pythonPath=sys.executable,
                engineDirectory=str(engine),allowedClientAddresses=['127.0.0.1'])
            receipt=dict(sourceConfigRef='source',targetConfigRef='target',ownerPin={})
            actual=native.control_document(template,setting,root,receipt,{})
            for role in ('recovery','repository'):
                expected=engine/(role+'_entry.py')
                self.assertTrue(Path(actual['programPins'][role]['path']).is_absolute())
                self.assertEqual(actual['programPins'][role],native.pin(expected))
            expected_paths=[engine.as_posix()+'/'+name for name in ('control','common','formal')]
            expected_paths+=['/python/site-packages',old+'-other/common']
            self.assertEqual(actual['environment']['PYTHONPATH'],':'.join(expected_paths))
            self.assertEqual(actual['environment']['PATH'],'/usr/bin')
            self.assertEqual(actual['workingDirectory'],str(engine))
            self.assertEqual(template,before)

    def test_control_does_not_reuse_old_entry_when_selected_program_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            setting=dict(listenAddress=native.HOST,listenPort=43059,pythonPath=sys.executable,
                engineDirectory=str(root),allowedClientAddresses=['127.0.0.1'])
            receipt=dict(sourceConfigRef='source',targetConfigRef='target',ownerPin={})
            for missing in ('recovery','repository'):
                for role in ('recovery','repository'):
                    path=root/(role+'_entry.py')
                    if role==missing:path.unlink(missing_ok=True)
                    else:path.write_bytes(role.encode())
                with self.subTest(missing=missing),self.assertRaisesRegex(native.PreparationError,'PREPARE_CONTROL_PROGRAM_MISSING'):
                    native.control_document({'programPins':{'recovery':native.pin(sys.executable),'repository':native.pin(sys.executable)}},
                        setting,root,receipt,{})

    def test_control_clients_require_explicit_canonical_ip_addresses(self):
        setting=dict(listenAddress='172.30.30.59',listenPort=43059,pythonPath=sys.executable,engineDirectory='/engine')
        receipt=dict(sourceConfigRef='source',targetConfigRef='target',ownerPin={})
        for value in [None,[],['*'],['192.168.109.0/24'],['192.168.109.082']]:
            with self.subTest(value=value),self.assertRaisesRegex(native.PreparationError,'PREPARE_CONTROL_CLIENTS_INVALID'):
                native.control_document({},dict(setting,allowedClientAddresses=value),Path('/task'),receipt,{})

    def test_installed_control_service_receives_private_configuration_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);engine=root/'engine';engine.mkdir();systemd=root/'systemd';systemd.mkdir()
            executable=root/'python';executable.write_bytes(b'python')
            (engine/'control_entry.py').write_bytes(b'entry')
            for role in ('recovery','repository'):(engine/(role+'_entry.py')).write_bytes(role.encode())
            environment=dict(LANG='C.UTF-8',PATH='/usr/bin',PYTHONDONTWRITEBYTECODE='1',
                             PYTHONPATH='/kept/control:/kept/common:/kept/formal:/kept/site-packages')
            native.write(root/'control-template.json',dict(engineSelectionRef='engine',environment=environment,
                                                         authCredentialRef={'path':'/kept/auth'}))
            native.write(root/'registration-template.json',dict(applicationId='app',sourceConfigRef='source'))
            setting=dict(serviceName='spug-prepare59-restore.service',engineDirectory=str(engine),pythonPath=str(executable),
                         listenAddress=native.HOST,listenPort=43059,allowedClientAddresses=['192.168.109.82'])
            worker=native.NativePreparation(dict(host=native.HOST,toolRoot=str(root),control=setting))
            def local_path(value):return systemd if value=='/etc/systemd/system' else Path(value)
            with patch.object(native,'Path',side_effect=local_path),patch.object(native,'command',return_value='active'):
                receipt=worker.install_control(dict(applicationId='app'),root,
                    dict(sourceConfigRef='source',targetConfigRef='target',ownerPin={}),{})
            unit=(systemd/setting['serviceName']).read_text(encoding='utf-8')
            self.assertIn('EnvironmentFile=',unit)
            self.assertNotIn(environment['PYTHONPATH'],unit)
            # systemd 219 consumes this directive as a path, without stripping quotes.
            environment_file=next(line.split('=',1)[1] for line in unit.splitlines() if line.startswith('EnvironmentFile='))
            self.assertEqual(environment_file,str(root/'control.env'))
            self.assertTrue(Path(environment_file).is_absolute())
            content=Path(environment_file).read_text(encoding='utf-8')
            for key,value in environment.items():self.assertIn(key+'="'+value+'"\n',content)
            self.assertEqual(native.read(receipt['controlPin']['path'])['environment'],environment)

    def test_main_template_is_projected_to_fresh_owner_without_old_program_policies(self):
        original={'schemaVersion':'RecoveryMinimalConfiguration/v1','operationsRoot':'/old',
            'sources':{'source':{'archiveRoots':['/nas']}},'targets':{'old':{'sourceConfigRef':'source',
            'mainApplication':{'schemaVersion':'old-main'},'replacement':{'schemaVersion':'old-replace'},
            'dataPolicy':{'bucketMapping':{}},'application':{'startOrder':['backend','frontend']}}},
            'targetProgramPolicies':{'old':{}},'targetSourceAdmissions':{'targets':{'old':['source']}}}
        result=native.fresh_owner(original,'old','source')
        self.assertNotIn('mainApplication',result['targets']['old'])
        self.assertNotIn('replacement',result['targets']['old'])
        self.assertNotIn('targetProgramPolicies',result)
        self.assertNotIn('targetSourceAdmissions',result)
        self.assertEqual(result['targets']['old']['application'],original['targets']['old']['application'])
        self.assertIn('mainApplication',original['targets']['old'])


if __name__ == '__main__': unittest.main()
