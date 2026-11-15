"""Local task persistence contracts; no server readiness is simulated as E2E."""
import tempfile
from pathlib import Path
import unittest
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

    def test_completed_restore_reuses_existing_terminal_without_refresh(self):
        import smallapp_entry as entry
        import prepare_target_registration as registration
        entries=Path(self.temp.name)/'entry';entries.mkdir()
        journal=Path(self.temp.name)/'journal';journal.mkdir()
        original=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='old-restore',action='RESTORE',
            sourceConfigRef='source',targetConfigRef='target59',recoveryPointRef='point',parentChainRef=None)
        p.adapter.write_json(entries/'old.json',dict(request=original,dispatchState='DISPATCHED'))
        p.adapter.write_json(journal/(p.hashlib.sha256(b'old-restore').hexdigest()+'.json'),
                             dict(lastResult={'state':'FAILED'}))
        config=dict(applicationId='app',sourceConfigRef='source',stateRoot=str(Path(self.temp.name)/'tasks'))
        with patch.object(p,'configuration',return_value=config),patch.object(entry,'ENTRIES',entries), \
             patch.object(p.adapter,'RECORDS',journal),patch.object(p,'target_refs',return_value={'target59'}), \
             patch.object(p.adapter,'request_bridge'),patch.object(p.adapter,'execute',return_value={'state':'FAILED'}) as query, \
             patch.object(entry,'original_result',side_effect=AssertionError('terminal remote refresh')), \
             patch.object(registration,'preflight'),patch.object(p.threading,'Thread'):
            self.assertEqual(p.submit(self.request,1)['state'],'PENDING')
            self.assertIs(query.call_args.kwargs['refresh_terminal'],False)

if __name__=='__main__':unittest.main()
