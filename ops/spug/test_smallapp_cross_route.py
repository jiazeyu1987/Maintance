"""Transport routing contracts; these tests do not claim real restore success."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import smallapp_adapter as adapter
import smallapp_simple as simple
import smallapp_entry as entry


class CrossRestoreRouting(unittest.TestCase):
    def fixture(self, root):
        adapter.write_json(root/'auth.json', {'headers': {}})
        def connection(port, sources, targets):
            return dict(sourceConfigRefs=sources, targetConfigRefs=targets,
                        submitUrl=f'http://127.0.0.1:{port}/operations',
                        queryUrlTemplate=f'http://127.0.0.1:{port}/operations/{{operationId}}',
                        selectionUrl=f'http://127.0.0.1:{port}/selections',credentialRef='auth.json')
        source=connection(18557,['prod-source'],['prod-target'])
        target=connection(18558,['prod-source'],['test-target'])
        adapter.write_json(root/'source.json',source)
        adapter.write_json(root/'target.json',target)
        adapter.write_json(root/'routes.json',dict(source,sourceConnections={'prod-source':'source.json'},
                           targetConnections={'test-target':'target.json'}))
        return adapter.HttpBridge(root/'routes.json','prod-source')

    def request(self, action='FULL'):
        return dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='contract-route-001',
                    sourceConfigRef='prod-source',action=action,parentChainRef=None,
                    recoveryPointRef='point-001' if action=='RESTORE' else None,
                    targetConfigRef='test-target' if action=='RESTORE' else None)

    def test_restore_routes_target_without_changing_source_or_old_backup_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.fixture(root)
            restore=source.for_request(self.request('RESTORE'))
            self.assertEqual(restore.submit_url,'http://127.0.0.1:18558/operations')
            restore.validate_binding(self.request('RESTORE'))
            original=restore.for_request(self.request())
            self.assertEqual(original.fingerprint,source.fingerprint)
            self.assertNotEqual(restore.fingerprint,source.fingerprint)
            self.assertEqual(original.submit_url,'http://127.0.0.1:18557/operations')

    def test_wrong_source_and_unregistered_target_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.fixture(Path(folder))
            with self.assertRaisesRegex(adapter.Refused,'SOURCE_NOT_IN_CURRENT_BINDING'):
                source.for_request(dict(self.request('RESTORE'),sourceConfigRef='other-source'))
            with self.assertRaisesRegex(adapter.Refused,'TARGET_CONNECTION_NOT_REGISTERED'):
                source.for_request(dict(self.request('RESTORE'),targetConfigRef='unknown-target'))

    def test_target_catalogue_contributes_only_its_own_fresh_target(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.fixture(Path(folder))
            row=dict(applicationId='prod-source',sourceConfigRef='prod-source',engineSelectionRef='engine',
                     fullReady=True,fullErrorCode=None,parentChainRefs=['source-parent'],
                     recoveryPointRefs=['source-point'],freshTargetConfigRefs=['prod-target'],historyErrorCode=None)
            def read(bridge):
                local=dict(row)
                if bridge.selected_target:
                    local.update(parentChainRefs=['unrelated-parent'],recoveryPointRefs=['unrelated-point'],
                                 freshTargetConfigRefs=['test-target','unrouted-target'])
                return dict(observedAt='2026-10-23T00:00:00Z',applications=[local])
            with patch.object(adapter.HttpBridge,'_local_selections',read):
                actual=source.selections()['applications'][0]
            self.assertEqual(actual['recoveryPointRefs'],['source-point'])
            self.assertEqual(actual['parentChainRefs'],['source-parent'])
            self.assertEqual(actual['freshTargetConfigRefs'],['prod-target','test-target'])

    def test_telemetry_uses_target_and_refuses_missing_or_wrong_route(self):
        binding=dict(applicationId='prod-source',server='172.30.30.57',progressRoot='/prod',
                     pythonPath='/python',targetServers={'172.30.30.58':'test-target'})
        config=dict(bindings=[binding]);record=dict(applicationId='prod-source',request=self.request('RESTORE'))
        with self.assertRaisesRegex(adapter.Refused,'RESTORE_TELEMETRY_NOT_REGISTERED'):
            simple.progress_binding(record,config)
        route=dict(server='172.30.30.58',progressRoot='/test',pythonPath='/python',
                   sshTransport=dict(host='host.docker.internal',port=18558))
        binding['restoreProgressBindings']={'test-target':route}
        self.assertEqual(simple.progress_binding(record,config)['progressRoot'],'/test')
        route['server']='172.30.30.59'
        with self.assertRaisesRegex(adapter.Refused,'RESTORE_TELEMETRY_TARGET_MISMATCH'):
            simple.progress_binding(record,config)

    def test_selected_target_admission_keeps_source_point_eligibility(self):
        with tempfile.TemporaryDirectory() as folder:
            source=self.fixture(Path(folder));restore=source.for_request(self.request('RESTORE'))
            row=dict(applicationId='prod-source',sourceConfigRef='prod-source',engineSelectionRef='engine',
                     fullReady=True,fullErrorCode=None,parentChainRefs=['good-point'],
                     recoveryPointRefs=['good-point'],freshTargetConfigRefs=[],historyErrorCode=None)
            def read(bridge):
                local=dict(row)
                if bridge.selected_target:
                    local.update(parentChainRefs=['bad-point','good-point'],recoveryPointRefs=['bad-point','good-point'],
                                 freshTargetConfigRefs=['test-target','unrouted-target'])
                return dict(observedAt=entry.now(),applications=[local])
            config=dict(applications=[dict(applicationId='prod-source',sourceConfigRef='prod-source',targetConfigRefs=['test-target'])])
            with patch.object(adapter.HttpBridge,'_local_selections',read):
                actual=restore.selections()['applications'][0]
                self.assertEqual(actual['recoveryPointRefs'],['good-point'])
                self.assertEqual(actual['freshTargetConfigRefs'],['test-target'])
                with self.assertRaisesRegex(adapter.Refused,'RECOVERY_POINT_NOT_ACCEPTED'):
                    entry.admit_selection(dict(self.request('RESTORE'),recoveryPointRef='bad-point'),config,restore)
                self.assertEqual(entry.admit_selection(dict(self.request('RESTORE'),recoveryPointRef='good-point'),config,restore)['applicationId'],'prod-source')

    def test_prior_backup_and_cross_restore_keep_their_own_terminal_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=self.fixture(root);ui=root/'ui';ui.mkdir()
            backup=self.request();restore=dict(self.request('RESTORE'),operationId='contract-restore-001')
            for request in [backup,restore]:
                bridge=source.for_request(request)
                receipt=dict(request=request,bridgeFingerprint=bridge.fingerprint,
                             lastResult=dict(adapter.running(request),state='FAILED',errorCode='CONTRACT_FAILURE'))
                adapter.write_json(root/(adapter.hashlib.sha256(request['operationId'].encode()).hexdigest()+'.json'),receipt)
                adapter.write_json(entry.record_path(request['operationId'],ui),
                                   dict(request=request,bridgeFingerprint=bridge.fingerprint))
            # Reaching current admission proves both original journals were
            # checked against their own executors, without submitting a job.
            with patch.object(adapter,'RECORDS',root),patch.object(entry,'admit_selection',
                    side_effect=adapter.Refused('CURRENT_ADMISSION_REACHED')):
                with self.assertRaisesRegex(adapter.Refused,'CURRENT_ADMISSION_REACHED'):
                    entry.reserve(dict(backup,operationId='contract-next-001'),None,source,1,ui)

    def test_original_telemetry_route_survives_fresh_target_rotation(self):
        route=dict(server='172.30.30.58',progressRoot='/test/old-target',pythonPath='/python',
                   sshTransport=dict(host='host.docker.internal',port=18558))
        binding=dict(applicationId='prod-source',server='172.30.30.57',progressRoot='/prod',
                     targetServers={'172.30.30.58':'next-fresh-target'},
                     restoreProgressBindings={'test-target':route})
        record=dict(applicationId='prod-source',request=self.request('RESTORE'))
        self.assertEqual(simple.progress_binding(record,dict(bindings=[binding]))['progressRoot'],
                         '/test/old-target')
        with self.assertRaisesRegex(adapter.Refused,'RESTORE_TELEMETRY_NOT_REGISTERED'):
            simple.progress_binding(dict(record,request=dict(record['request'],targetConfigRef='unknown')),
                                    dict(bindings=[binding]))


if __name__=='__main__':unittest.main()
