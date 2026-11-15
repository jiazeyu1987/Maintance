"""Local filesystem tests; these do not claim a remote Docker acceptance run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import prepare_target_native as native


class NativePreparationTests(unittest.TestCase):
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
            executable=native.pin(sys.executable)
            template=dict(schemaVersion='SmallAppExecutionServiceConfig/v2',taskRoot='/old',ledgerRoot='/old/ledger',
                registryRoot='/old/registry',listenAddress='127.0.0.1',listenPort=43059,authCredentialRef={},
                allowedClientAddresses=['127.0.0.1'],pythonPin=executable,programPins={'repository':executable,'recovery':executable},
                workingDirectory='/old',environment={'PATH':'/usr/bin'},deadlineMilliseconds=60000,
                engineSelectionRef='installed-engine',sourceConfigurations={'source':executable},restoreConfigurations={})
            setting={'listenAddress':'172.30.30.59','listenPort':43059,'pythonPath':sys.executable,'engineDirectory':str(root)}
            receipt={'sourceConfigRef':'source','targetConfigRef':'fresh','ownerPin':executable}
            document=native.control_document(template,setting,root,receipt,{})
            reference=native.write(root/'control.json',document)
            # Linux custody is separately enforced in production; this is a real JSON/field-contract check on Windows.
            with patch.object(consumer,'native_required'),patch.object(consumer,'directory',lambda path,scope:Path(path)):
                actual=consumer.Native(reference).configuration()
            self.assertEqual(actual['restoreConfigurations']['source']['fresh'],executable)
            self.assertIn(Path(actual['taskRoot']),Path(actual['registryRoot']).parents)

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
