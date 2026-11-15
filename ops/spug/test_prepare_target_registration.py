"""Registration contract tests; these do not claim a real server was prepared."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smallapp_adapter as adapter
import smallapp_entry as entry
import smallapp_simple as simple
import prepare_target_registration as registration


class RegistrationTests(unittest.TestCase):
    def fixture(self, root):
        app = dict(applicationId='app-safe', displayName='App', sourceConfigRef='source-57',
                   targetConfigRefs=['old-58', 'old-59'], engineSelectionRef='engine-standard',
                   registrationSha256='a' * 64)
        settings = dict(applications=[app], tasks=dict(FULL=1, INCREMENTAL=2, RESTORE=3),
                        initialOperationIds={}, registrationVersions={'app-safe': '1'})
        route = dict(sourceConfigRefs=['source-57'], targetConfigRefs=['old-58', 'old-59'],
                     submitUrl='http://127.0.0.1:18001/operations',
                     queryUrlTemplate='http://127.0.0.1:18001/operations/{operationId}',
                     selectionUrl='http://127.0.0.1:18001/selections', credentialRef='auth.json',
                     targetConnections={'old-58': 'old58.json', 'old-59': 'old59.json'})
        binding = dict(applicationId='app-safe', product='app', server='172.30.30.57', mode='safe',
                       selectable=True, targetServers={'172.30.30.59': 'old-59'},
                       overwriteTargetServers={'172.30.30.59': 'main-59'}, progressRoot='/old-progress',
                       restoreProgressBindings={'old-59': {'server': '172.30.30.59',
                           'progressRoot': '/old-progress', 'pythonPath': '/old-python',
                           'sshTransport': {'host': 'host.docker.internal', 'port': 18559}}})
        values = {'entry.json': settings, 'bridge.json': route,
                  'simple.json': dict(nas={}, servers=[{}, {}, {}], bindings=[binding]),
                  'auth.json': {'headers': {}}}
        for name, value in values.items():
            adapter.write_json(root/name, value)
        config = {'publication': dict(entrySettings=str(root/'entry.json'),
                    bridgeSettings=str(root/'bridge.json'), simpleSettings=str(root/'simple.json'),
                    credentialRef='auth.json', sshTransport={'host': 'host.docker.internal', 'port': 18559})}
        request = dict(operationId='prepare-test-001', applicationId='app-safe', recoveryPointRef='point-i2')
        result = dict(state='INITIALIZED', targetConfigRef='fresh-59-001', sourceConfigRef='source-57',
                      registrationSha256='b' * 64, progressRoot='/minimal/operations',
                      pythonPath='/minimal/python/bin/python3.12', listenAddress='172.30.30.59', listenPort=18759)
        return config, request, result

    def selected(self, fresh=True):
        return dict(observedAt=entry.now(), applications=[dict(applicationId='app-safe',
            sourceConfigRef='source-57', engineSelectionRef='engine-standard', fullReady=True,
            fullErrorCode=None, parentChainRefs=[], recoveryPointRefs=['point-i2'],
            freshTargetConfigRefs=['fresh-59-001'] if fresh else [], historyErrorCode=None)])

    def test_published_target_works_with_existing_restore_admission_and_telemetry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, request, result = self.fixture(root)
            with patch.object(adapter.HttpBridge, 'selections', return_value=self.selected()) as query:
                published = registration.publish(config, request, result)
            self.assertEqual(published['targetConfigRef'], result['targetConfigRef'])
            self.assertEqual(query.call_count, 1, 'registration must not repeatedly scan selections')
            current = entry.settings(root/'entry.json')
            self.assertEqual(current['applications'][0]['targetConfigRefs'], ['old-58', 'old-59', 'fresh-59-001'])
            bridge = adapter.HttpBridge(root/'bridge.json', 'source-57', 'fresh-59-001')
            self.assertEqual(bridge.submit_url, 'http://172.30.30.59:18759/operations')
            restore = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-test-001',
                           action='RESTORE', sourceConfigRef='source-57', parentChainRef=None,
                           recoveryPointRef='point-i2', targetConfigRef='fresh-59-001')
            with patch.object(bridge, 'selections', return_value=self.selected()):
                self.assertEqual(entry.admit_selection(restore, current, bridge)['applicationId'], 'app-safe')
            document = adapter.read_json(root/'simple.json')
            binding = document['bindings'][0]
            self.assertEqual(binding['targetServers']['172.30.30.59'], 'fresh-59-001')
            self.assertEqual(binding['overwriteTargetServers']['172.30.30.59'], 'main-59')
            old = simple.progress_binding(dict(applicationId='app-safe', request=dict(action='RESTORE', targetConfigRef='old-59')), document)
            new = simple.progress_binding(dict(applicationId='app-safe', request=restore), document)
            self.assertEqual(old['progressRoot'], '/old-progress')
            self.assertEqual(new['progressRoot'], '/minimal/operations')
            self.assertEqual(adapter.read_json(root/'bridge.json')['targetConnections']['old-58'], 'old58.json')

    def test_unavailable_target_does_not_publish_live_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, request, result = self.fixture(root)
            before = {name: (root/name).read_bytes() for name in ['entry.json', 'simple.json', 'bridge.json']}
            with patch.object(adapter.HttpBridge, 'selections', return_value=self.selected(False)):
                with self.assertRaisesRegex(adapter.Refused, 'TARGET_NOT_CURRENTLY_FRESH'):
                    registration.publish(config, request, result)
            self.assertEqual(before, {name: (root/name).read_bytes() for name in before})

    def test_preflight_and_wrong_host_refuse_before_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, request, result = self.fixture(root)
            registration.preflight(config, request)
            with self.assertRaisesRegex(adapter.Refused, 'PREPARE_REGISTRATION_APPLICATION_INVALID'):
                registration.preflight(config, dict(request, applicationId='missing'))
            with self.assertRaisesRegex(adapter.Refused, 'PREPARE_REGISTRATION_TARGET_INVALID'):
                registration.publish(config, request, dict(result, listenAddress='172.30.30.57'))
            self.assertEqual(adapter.read_json(root/'simple.json')['bindings'][0]['targetServers']['172.30.30.59'], 'old-59')

    def test_concurrent_configuration_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config, request, result = self.fixture(root)
            original = registration.preflight
            def changed_after_read(*args):
                documents = original(*args)
                newer = adapter.read_json(root/'entry.json')
                newer['applications'][0]['displayName'] = 'Concurrent edit'
                adapter.write_json(root/'entry.json', newer)
                return documents
            with patch.object(registration, 'preflight', side_effect=changed_after_read), \
                    patch.object(adapter.HttpBridge, 'selections', return_value=self.selected()):
                with self.assertRaisesRegex(adapter.Refused, 'PREPARE_REGISTRATION_CONFIGURATION_CHANGED'):
                    registration.publish(config, request, result)
            self.assertEqual(adapter.read_json(root/'entry.json')['applications'][0]['displayName'], 'Concurrent edit')


if __name__ == '__main__':
    unittest.main()
