"""Local task persistence contracts; no server readiness is simulated as E2E."""
import tempfile
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import prepare_target as p


class TaskContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = p.Tasks(Path(self.temp.name))
        self.request = dict(operationId='prepare-test-1234', applicationId='app', recoveryPointRef='point',
                            planDigest='a'*64, confirmed=True)

    def test_repeat_returns_original_and_changed_request_refused(self):
        first, created = self.store.reserve(self.request, 1)
        self.assertTrue(created)
        second, created = self.store.reserve(self.request, 1)
        self.assertFalse(created)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(p.Refused, 'REQUEST_CHANGED'):
            self.store.reserve(dict(self.request, recoveryPointRef='changed'), 1)

    def test_second_operation_cannot_bypass_active_task(self):
        self.store.reserve(self.request, 1)
        with self.assertRaisesRegex(p.Refused, 'TARGET_BUSY'):
            self.store.reserve(dict(self.request, operationId='prepare-test-5678'), 1)

    def test_ready_unconsumed_target_ignores_only_other_target_restore_history(self):
        import smallapp_entry as entry
        config_file=Path(self.temp.name)/'private.conf';config_file.write_text('{}',encoding='utf-8')
        cfg=dict(applicationId='app',sourceConfigRef='source',stateRoot=str(self.store.root))
        request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='first-fresh-restore',action='RESTORE',
                     sourceConfigRef='source',targetConfigRef='new-target',recoveryPointRef='point',parentChainRef=None)
        bridge=SimpleNamespace(fingerprint='binding');bridge.for_request=lambda original:bridge
        app=dict(applicationId='app',registrationSha256='a'*64)
        for scenario in ('fresh','same-target','not-ready','source-backup'):
            with self.subTest(scenario=scenario):
                ui=Path(self.temp.name)/scenario;ui.mkdir();journal=ui/'journal';journal.mkdir()
                old=dict(request,operationId='smallapp-1fd7a5899db54511bee4daec85e271f8',targetConfigRef='old-58')
                if scenario=='same-target':old['targetConfigRef']='new-target'
                if scenario=='source-backup':old.update(action='FULL',targetConfigRef=None,recoveryPointRef=None)
                p.adapter.write_json(entry.record_path(old['operationId'],ui),dict(request=old,bridgeFingerprint='binding'))
                row=dict(operationId='preparation-ready',state='READY' if scenario!='not-ready' else 'FAILED',
                         targetConfigRef='new-target',host=p.HOST,applicationId='app',startedAt=p.now(),
                         stages=[dict(name=name,state='SUCCEEDED') for name in p.STAGES])
                self.store.save(row)
                with patch.object(p,'CONFIG',config_file),patch.object(p,'configuration',return_value=cfg), \
                     patch.object(p,'target_refs',return_value={'new-target'}),patch.object(p.adapter,'RECORDS',journal), \
                     patch.object(entry,'admit_selection',return_value=app) as admission:
                    if scenario=='fresh':
                        record,created=entry.reserve(request,{'tasks':{'RESTORE':1}},bridge,1,ui)
                        self.assertTrue(created);self.assertEqual(record['request'],request)
                        admission.assert_called_once_with(request,{'tasks':{'RESTORE':1}},bridge)
                    else:
                        with self.assertRaisesRegex(p.Refused,'ORIGINAL_OPERATION_STILL_UNRESOLVED'):
                            entry.reserve(request,{'tasks':{'RESTORE':1}},bridge,1,ui)
                        admission.assert_not_called()

    def test_failed_initialization_never_ready_and_does_not_publish(self):
        self.store.reserve(self.request, 1)
        calls=[]
        def remote(action, request, emit):
            emit(dict(type='stage',stage=dict(name='dependencies',state='SUCCEEDED')))
            raise RuntimeError('private password must not leak')
        p.run_task(self.store, self.request, {}, remote, lambda *a:calls.append(a))
        row=self.store.get(self.request['operationId'])
        self.assertEqual(row['state'], 'UNKNOWN')
        self.assertEqual(row['errorCode'], 'PREPARATION_CONNECTION_LOST')
        self.assertNotIn('password', str(row))
        self.assertEqual(calls, [])

    def test_ready_requires_registration_and_all_three_stages(self):
        self.store.reserve(self.request, 1)
        def remote(action, request, emit):
            for name in ('dependencies','cleanup','initialize'):
                emit(dict(type='stage',stage=dict(name=name,state='SUCCEEDED')))
            return dict(state='INITIALIZED',targetConfigRef='fresh-target')
        p.run_task(self.store,self.request,{},remote,lambda *a:dict(targetConfigRef='fresh-target'))
        self.assertEqual(self.store.get(self.request['operationId'])['state'],'READY')

    def test_registration_failure_is_visible(self):
        self.store.reserve(self.request,1)
        def publish(*a):raise p.Refused('REGISTRATION_FAILED')
        p.run_task(self.store,self.request,{},lambda *a:dict(state='INITIALIZED'),publish)
        row=self.store.get(self.request['operationId'])
        self.assertEqual(row['state'],'FAILED')
        self.assertEqual(row['errorCode'],'REGISTRATION_FAILED')

    def test_native_command_failure_is_visible_in_public_record_and_stopped(self):
        self.store.reserve(self.request,1)
        failure=dict(action='DOCKER_VOLUME_RM',object='old-minio',exitCode=1,reason='RESOURCE_BUSY')
        stage=dict(name='cleanup',state='FAILED',errorCode='PREPARE_NATIVE_COMMAND_FAILED',failure=failure)
        result=dict(state='FAILED',errorCode='PREPARE_NATIVE_COMMAND_FAILED',failure=failure,stages=[stage])
        p.run_task(self.store,self.request,{},lambda *a:result,lambda *a:self.fail('must not publish'))
        row=p.public_record(self.store.get(self.request['operationId']))
        self.assertEqual(row['state'],'FAILED')
        self.assertEqual(row['failure'],failure)
        self.assertEqual(row['stages'][1]['failure'],failure)
        self.assertTrue(self.store.reserve(dict(self.request,operationId='prepare-again-1234'),1)[1])

    def test_configuration_missing_is_explicit(self):
        self.assertEqual(p.public_configuration(Path(self.temp.name)/'absent.json'),
                         dict(configured=False,host='172.30.30.59',errorCode='PREPARATION_NOT_CONFIGURED'))

    def test_preparation_only_blocks_restores_to_this_host(self):
        self.store.reserve(self.request,1)
        config=Path(self.temp.name)/'config'
        config.write_text('{}',encoding='utf-8')
        with patch.object(p,'CONFIG',config), patch.object(p,'configuration',return_value={
            'stateRoot':str(self.store.root),'sourceConfigRef':'source'}), patch.object(
                p,'target_refs',return_value={'target59','historical59'}):
            for action,target in [('FULL',None),('RESTORE','target58')]:
                p.block_while_preparing(dict(action=action,sourceConfigRef='source',targetConfigRef=target))
            with self.assertRaisesRegex(p.Refused,'TARGET_BUSY'):
                p.block_while_preparing(dict(action='RESTORE',sourceConfigRef='source',targetConfigRef='historical59'))

    def test_submission_queues_without_repeating_source_or_remote_preview(self):
        import smallapp_entry as entry
        import prepare_target_registration as registration
        entries=Path(self.temp.name)/'entry'
        entries.mkdir()
        config=dict(applicationId='app',sourceConfigRef='source',stateRoot=str(Path(self.temp.name)/'tasks'))
        with patch.object(p,'configuration',return_value=config), patch.object(entry,'ENTRIES',entries), \
             patch.object(p,'target_refs',return_value={'target59'}), \
             patch.object(p,'preview',side_effect=AssertionError('duplicate preview')), \
             patch.object(registration,'preflight') as preflight, patch.object(p.threading,'Thread') as worker:
            row=p.submit(self.request,1)
            self.assertEqual(row['state'],'PENDING')
            preflight.assert_called_once_with(config,self.request)
            worker.return_value.start.assert_called_once()

    def test_preview_uses_selected_application_in_multi_application_catalogue(self):
        import smallapp_entry as entry
        import prepare_target_registration as registration
        selection=dict(applicationId='app',recoveryPointRef='point')
        plan=dict(host=p.HOST,**selection,planDigest='a'*64,cleanupSummary=['old'],
                  preserveSummary=['nas'],stages=list(p.STAGES))
        apps=[dict(applicationId='other',validated=None),
              dict(applicationId='app',validated={'recoveryPointRefs':['point']})]
        with patch.object(p,'configuration',return_value={'applicationId':'app'}), \
             patch.object(registration,'preflight'),patch.object(entry,'settings'), \
             patch.object(entry,'application_catalogue',return_value=apps), \
             patch.object(p,'remote',return_value=plan) as remote:
            self.assertEqual(p.preview(selection),plan)
            remote.assert_called_once()

    def test_old_restore_history_cannot_block_new_preparation(self):
        import smallapp_entry as entry
        import prepare_target_registration as registration
        entries=Path(self.temp.name)/'entry';entries.mkdir()
        journal=Path(self.temp.name)/'journal';journal.mkdir()
        original=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='old-restore',action='RESTORE',
            sourceConfigRef='source',targetConfigRef='target59',recoveryPointRef='point',parentChainRef=None)
        p.adapter.write_json(entries/'old.json',dict(request=original,dispatchState='DISPATCHED'))
        config=dict(applicationId='app',sourceConfigRef='source',stateRoot=str(Path(self.temp.name)/'tasks'))
        with patch.object(p,'configuration',return_value=config),patch.object(entry,'ENTRIES',entries), \
             patch.object(p.adapter,'RECORDS',journal),patch.object(p,'target_refs',return_value={'target59'}), \
             patch.object(p.adapter,'request_bridge'),patch.object(p.adapter,'execute',side_effect=AssertionError('old history query')) as query, \
             patch.object(entry,'original_result',side_effect=AssertionError('terminal remote refresh')), \
             patch.object(registration,'preflight'),patch.object(p.threading,'Thread'):
            self.assertEqual(p.submit(self.request,1)['state'],'PENDING')
            query.assert_not_called()

    def test_unknown_query_unlocks_only_after_remote_confirms_stopped(self):
        self.store.reserve(self.request,1)
        row=self.store.get(self.request['operationId']);row.update(state='UNKNOWN')
        self.store.save(row)
        config={'stateRoot':str(self.store.root)}
        remote=dict(operationId=self.request['operationId'],state='FAILED',workerStopped=False,
                    errorCode='PREPARE_INTERRUPTED',stages=[])
        with patch.object(p,'configuration',return_value=config),patch.object(p,'remote',return_value=remote) as query:
            self.assertEqual(p.query(self.request['operationId'])['state'],'UNKNOWN')
            remote['workerStopped']=True
            self.assertEqual(p.query(self.request['operationId'])['state'],'FAILED')
            self.assertEqual(query.call_args.args[1],'query')
        self.assertTrue(self.store.reserve(dict(self.request,operationId='new-prepare-id'),1)[1])

    def test_unknown_query_connection_failure_does_not_unlock(self):
        self.store.reserve(self.request,1)
        row=self.store.get(self.request['operationId']);row.update(state='UNKNOWN');self.store.save(row)
        with patch.object(p,'configuration',return_value={'stateRoot':str(self.store.root)}), \
             patch.object(p,'remote',side_effect=p.Refused('PREPARATION_REMOTE_FAILED')):
            with self.assertRaises(p.Refused):p.query(self.request['operationId'])
        self.assertEqual(self.store.get(self.request['operationId'])['state'],'UNKNOWN')

if __name__=='__main__':unittest.main()
