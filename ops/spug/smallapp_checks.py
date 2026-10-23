"""Focused wire/real durable IO checks. No fake execution bridge or backup success."""
import concurrent.futures
import contextlib
import hashlib
import io
import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
import smallapp_adapter as adapter
import smallapp_entry as entry
SOURCE = 'smallapp-20261014-source-r1'
TARGET = 'smallapp-20261014-target-r1'


def full():
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='smallapp-check-full-r1',
                action='FULL', sourceConfigRef=SOURCE, parentChainRef=None,
                recoveryPointRef=None, targetConfigRef=None)


class ContractAndDurability(unittest.TestCase):
    def test_host_catalogue_is_scoped_to_explicit_connection(self):
        bridge = adapter.HttpBridge.__new__(adapter.HttpBridge)
        bridge.selection_url = "http://127.0.0.1:18183/selections"
        bridge.origin = ("http", "127.0.0.1", 18183)
        bridge.source_refs = ["source-real"]
        bridge.selected_target = None
        bridge.connections = {}
        bridge.target_connections = {}
        bridge.call = lambda url: dict(observedAt="now", applications=[
            dict(applicationId="old", sourceConfigRef="source-old"),
            dict(applicationId="real", sourceConfigRef="source-real")])
        rows = bridge.selections()["applications"]
        self.assertEqual([row["applicationId"] for row in rows], ["real"])

    def test_explicit_source_connection_preserves_original_fingerprint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            adapter.write_json(root / 'auth.json', {'headers': {}})
            original = dict(sourceConfigRefs=[SOURCE], targetConfigRefs=[TARGET],
                submitUrl='http://127.0.0.1:18083/operations',
                queryUrlTemplate='http://127.0.0.1:18083/operations/{operationId}',
                selectionUrl='http://127.0.0.1:18083/selections', credentialRef='auth.json')
            adapter.write_json(root / 'original.json', original)
            second = {**original, 'sourceConfigRefs': ['separate-source'],
                'submitUrl': 'http://127.0.0.1:18183/operations',
                'queryUrlTemplate': 'http://127.0.0.1:18183/operations/{operationId}',
                'selectionUrl': 'http://127.0.0.1:18183/selections'}
            adapter.write_json(root / 'second.json', second)
            adapter.write_json(root / 'routes.json', {**original,
                'sourceConnections': {'separate-source': 'second.json'}})
            old = adapter.HttpBridge(root / 'original.json')
            unchanged = adapter.HttpBridge(root / 'routes.json', SOURCE)
            selected = adapter.HttpBridge(root / 'routes.json', 'separate-source')
            self.assertEqual(old.fingerprint, unchanged.fingerprint)
            self.assertNotEqual(old.fingerprint, selected.fingerprint)
            self.assertEqual(selected.submit_url, second['submitUrl'])
            with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
                adapter.HttpBridge(root / 'routes.json', 'unknown-source')
            with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
                selected.validate_binding(full())

    def test_w01_choices_require_exact_registration_and_current_observation(self):
        # Pure malformed-contract checks; no installed/accepted registry is simulated.
        config = {'applications': [{'applicationId': 'contract-app', 'sourceConfigRef': SOURCE,
                   'targetConfigRefs': [TARGET], 'engineSelectionRef': None}]}
        pending = dict(applicationId='contract-app', sourceConfigRef=SOURCE, engineSelectionRef=None,
                       fullReady=False, fullErrorCode='SOURCE_NOT_INSTALLED', parentChainRefs=[],
                       recoveryPointRefs=[], freshTargetConfigRefs=[], historyErrorCode=None)
        payload = {'observedAt': entry.now(), 'applications': [pending]}
        self.assertFalse(entry.validated_selections(payload, config)['contract-app']['fullReady'])
        for delta, error in [({'sourceConfigRef': 'unregistered-source'}, 'W01_SOURCE_REGISTRATION_MISMATCH'),
                             ({'freshTargetConfigRefs': ['unregistered-target']}, 'W01_TARGET_NOT_REGISTERED'),
                             ({'fullReady': True}, 'W01_SOURCE_READINESS_INVALID'),
                             ({'password': 'must-never-export'}, 'W01_SELECTION_ITEM_INVALID')]:
            with self.assertRaisesRegex(adapter.Refused, error):
                entry.validated_selections({**payload, 'applications': [{**pending, **delta}]}, config)
        with self.assertRaisesRegex(adapter.Refused, 'W01_SELECTION_OBSERVATION_STALE'):
            entry.validated_selections({**payload, 'observedAt': '2020-01-01T00:00:00Z'}, config)
        # The common engine is selected by W01; display metadata is not a
        # second per-application approval or signed version prerequisite.
        accepted = entry.validated_selections({**payload, 'applications': [{**pending,
            'fullReady': True, 'fullErrorCode': None, 'engineSelectionRef': 'contract-common-engine'}]}, config)
        self.assertTrue(accepted['contract-app']['fullReady'])
        # Historical read failure stays explicit and does not change source
        # readiness for FULL. No unverified parent or recovery choice is usable.
        failed_history = {**accepted['contract-app'], 'historyErrorCode': 'NATIVE_PIN_CHANGED'}
        observed = entry.validated_selections({**payload, 'applications': [failed_history]}, config)
        self.assertTrue(observed['contract-app']['fullReady'])
        self.assertEqual(observed['contract-app']['historyErrorCode'], 'NATIVE_PIN_CHANGED')
        with self.assertRaisesRegex(adapter.Refused, 'W01_HISTORY_REFERENCES_UNVERIFIED'):
            entry.validated_selections({**payload, 'applications': [{**failed_history,
                'parentChainRefs': ['unverified-point']}]}, config)

    def test_display_metadata_revision_does_not_gate_prepared_source(self):
        with tempfile.TemporaryDirectory(prefix='spug-registration-binding-') as folder:
            root = Path(folder)
            adapter.write_json(root / 'auth.json', {'headers': {}}, exclusive=True)
            config = {'submitUrl': 'http://127.0.0.1:1/operations',
                'queryUrlTemplate': 'http://127.0.0.1:1/operations/{operationId}', 'credentialRef': 'auth.json',
                'sourceConfigRefs': [SOURCE], 'targetConfigRefs': []}
            adapter.write_json(root / 'bridge.json', config)
            bridge = adapter.HttpBridge(root / 'bridge.json')
            record = {'request': full(), 'applicationId': 'contract-app',
                      'registrationSha256': 'a' * 64, 'bridgeFingerprint': bridge.fingerprint}
            adapter.write_json(entry.record_path(full()['operationId'], folder), record, exclusive=True)
            entry.validate_prepared_binding(full()['operationId'], bridge, {'applications': [
                {'applicationId': 'contract-app', 'sourceConfigRef': SOURCE,
                 'registrationSha256': 'b' * 64, 'engineSelectionRef': None}]}, folder)
            self.assertEqual(bridge.requests, [])

    def test_prepared_original_rejects_changed_source_before_dispatch(self):
        with tempfile.TemporaryDirectory(prefix='spug-prepared-version-') as folder:
            record = {'request': full(), 'applicationId': 'contract-app', 'registrationSha256': 'a' * 64}
            adapter.write_json(entry.record_path(full()['operationId'], folder), record, exclusive=True)
            config = {'applications': [{'applicationId': 'contract-app', 'sourceConfigRef': 'changed-source',
                                       'registrationSha256': 'b' * 64}]}
            with self.assertRaisesRegex(adapter.Refused, 'PREPARED_SOURCE_CHANGED'):
                entry.validate_prepared_binding(full()['operationId'], None, config, folder)

    def test_durable_page_original_is_reused_without_admission_or_dispatch(self):
        with tempfile.TemporaryDirectory(prefix='spug-entry-original-') as folder:
            request = full()
            record = {'request': request, 'dispatchReserved': True}
            adapter.write_json(entry.record_path(request['operationId'], folder), record, exclusive=True)
            for _ in range(2):
                original, first = entry.reserve(request, None, None, 1, folder)
                self.assertEqual(original, record)
                self.assertFalse(first)
            # A legacy UI reservation alone proves no dispatch claim. Repeated
            # submissions remain queries, but the CLI must not initiate it.
            with self.assertRaisesRegex(adapter.Refused, 'SPUG_DISPATCH_CLAIM_REQUIRED'):
                entry.prepared_request(request['operationId'], 'FULL', folder)
            with self.assertRaisesRegex(adapter.Refused, 'PREPARED_OPERATION_MISMATCH'):
                entry.prepared_request(request['operationId'], 'RESTORE', folder)
            with self.assertRaisesRegex(adapter.Refused, 'OPERATION_ID_REQUEST_REUSE_REJECTED'):
                entry.reserve({**request, 'sourceConfigRef': 'changed-source'}, None, None, 1, folder)
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_STILL_UNRESOLVED'):
                entry.reserve({**request, 'operationId': 'new-id-cannot-bypass-unknown'}, None, None, 1, folder)

    def test_full_binding_does_not_wait_for_a_restore_target(self):
        with tempfile.TemporaryDirectory(prefix='spug-full-no-target-') as folder:
            root = Path(folder)
            adapter.write_json(root / 'auth.json', {'headers': {}}, exclusive=True)
            adapter.write_json(root / 'bridge.json', {'submitUrl': 'http://127.0.0.1:1/operations',
                'queryUrlTemplate': 'http://127.0.0.1:1/operations/{operationId}', 'credentialRef': 'auth.json',
                'sourceConfigRefs': [SOURCE], 'targetConfigRefs': []}, exclusive=True)
            bridge = adapter.HttpBridge(root / 'bridge.json')
            bridge.validate_binding(full())
            with self.assertRaisesRegex(adapter.Refused, 'W01_SELECTION_ENDPOINT_REQUIRED'):
                bridge.selections()
            self.assertEqual(bridge.requests, [])

    def test_current_batch_and_action_inputs(self):
        self.assertEqual(adapter.validate_request(full()), full())
        for key, value, code in [('sourceConfigRef', '/unapproved/source', 'SOURCE_CONFIG_REF_INVALID'),
                                  ('targetConfigRef', TARGET, 'FULL_REFERENCE_CONFLICT'),
                                  ('operationId', 'http://host/private', 'OPERATION_ID_INVALID')]:
            with self.assertRaisesRegex(adapter.Refused, code):
                adapter.validate_request({**full(), key: value})
        for extra in ('password', 'credentials', 'shell', 'path'):
            with self.assertRaisesRegex(adapter.Refused, 'REQUEST_FIELDS_INVALID'):
                adapter.validate_request({**full(), extra: 'unapproved-input'})

    def test_parent_and_fresh_target_required(self):
        inc = {**full(), 'action': 'INCREMENTAL'}
        with self.assertRaisesRegex(adapter.Refused, 'AUTHENTIC_PARENT_CHAIN_REF_REQUIRED'):
            adapter.validate_request(inc)
        adapter.validate_request({**inc, 'parentChainRef': 'contract-input-only-parent'})
        restore = {**full(), 'action': 'RESTORE', 'recoveryPointRef': 'contract-input-only-point'}
        with self.assertRaisesRegex(adapter.Refused, 'FRESH_TASK_TARGET_REQUIRED'):
            adapter.validate_request(restore)
        adapter.validate_request({**restore, 'targetConfigRef': TARGET})

    def test_result_identity_and_secret_text_refusal(self):
        value = adapter.running(full(), 'CHECK_UNAVAILABLE')
        self.assertEqual(adapter.validate_result(value, full())['state'], 'RUNNING')
        for delta, code in [({'operationId': 'another-operation'}, 'BRIDGE_ORIGINAL_OPERATION_MISMATCH'),
                            ({'state': 'DEFAULT_SUCCESS'}, 'BRIDGE_STATE_INVALID'),
                            ({'logRefs': ['mysql://unapproved-connection']}, 'BRIDGE_LOG_REFERENCES_UNSAFE'),
                            ({'errorCode': 'upstream raw private text'}, 'BRIDGE_ERROR_CODE_UNSAFE'),
                            ({'state': 'SUCCEEDED', 'errorCode': None}, 'BRIDGE_SUCCESS_EVIDENCE_MISSING')]:
            with self.assertRaisesRegex(adapter.Refused, code):
                adapter.validate_result({**value, **delta}, full())

    def test_exclusive_reservation_with_real_concurrent_io(self):
        with tempfile.TemporaryDirectory(prefix='spug-smallapp-io-') as folder:
            path = Path(folder) / 'reservation.json'
            def compete(index):
                try:
                    adapter.write_json(path, {'winner': index}, exclusive=True)
                    return index
                except FileExistsError:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                winners = [v for v in pool.map(compete, range(8)) if v is not None]
            self.assertEqual(len(winners), 1)
            self.assertEqual(adapter.read_json(path), {'winner': winners[0]})
            adapter.write_json(path, {'winner': winners[0], 'updated': True})
            self.assertTrue(adapter.read_json(path)['updated'])

    def test_unknown_original_only_queries_actual_unavailable_transport(self):
        # Reserve a real original journal, then use an actually closed loopback port.
        # No fake server/result, capture, restore or submission is used in this check.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix='spug-smallapp-query-') as folder:
            root = Path(folder)
            adapter.write_json(root / 'auth.json', {'headers': {}}, exclusive=True)
            adapter.write_json(root / 'bridge.json', {
                'submitUrl': f'http://127.0.0.1:{port}/smallapp-submit',
                'queryUrlTemplate': f'http://127.0.0.1:{port}/smallapp-query/{{operationId}}',
                'sourceConfigRefs': [SOURCE], 'targetConfigRefs': [TARGET],
                'credentialRef': 'auth.json'}, exclusive=True)
            bridge = adapter.HttpBridge(root / 'bridge.json')
            request = full()
            with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
                adapter.execute({**request, 'sourceConfigRef': 'unregistered-source'}, bridge, root)
            self.assertEqual(bridge.requests, [])
            path = root / (hashlib.sha256(request['operationId'].encode()).hexdigest() + '.json')
            adapter.write_json(path, {'request': request, 'bridgeFingerprint': bridge.fingerprint,
                                      'lastResult': None}, exclusive=True)
            for _ in range(2):
                result = adapter.execute(request, bridge, root)
                self.assertEqual(result['state'], 'RUNNING')
                self.assertEqual(result['errorCode'], 'BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID')
            self.assertEqual(bridge.requests, ['GET', 'GET'])
            self.assertEqual(len(list((root / 'observations').glob('*.json'))), 2)
            changed = {**request, 'action': 'INCREMENTAL', 'parentChainRef': 'contract-input-only-parent'}
            with self.assertRaisesRegex(adapter.Refused, 'OPERATION_ID_REQUEST_REUSE_REJECTED'):
                adapter.execute(changed, bridge, root)
            self.assertEqual(bridge.requests, ['GET', 'GET'])

    def test_missing_bridge_fails_before_any_execution(self):
        with tempfile.TemporaryDirectory(prefix='spug-smallapp-missing-') as folder:
            with self.assertRaisesRegex(adapter.Refused, 'W01_TRANSPORT_BINDING_REQUIRED'):
                adapter.HttpBridge(Path(folder) / 'absent.json')

    def test_lost_first_submission_queries_original_without_second_post(self):
        # A genuinely closed endpoint exercises the transport failure. No fake
        # server or successful backup result is substituted.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix='spug-submit-query-') as folder:
            root = Path(folder)
            adapter.write_json(root / 'auth.json', {'headers': {}}, exclusive=True)
            adapter.write_json(root / 'bridge.json', {
                'submitUrl': f'http://127.0.0.1:{port}/operations',
                'queryUrlTemplate': f'http://127.0.0.1:{port}/operations/{{operationId}}',
                'sourceConfigRefs': [SOURCE], 'targetConfigRefs': [],
                'credentialRef': 'auth.json'}, exclusive=True)
            bridge = adapter.HttpBridge(root / 'bridge.json')
            first = adapter.execute(full(), bridge, root)
            self.assertEqual(first['state'], 'RUNNING')
            self.assertEqual(bridge.requests, ['POST', 'GET'])
            second = adapter.execute(full(), bridge, root)
            self.assertEqual(second['operationId'], full()['operationId'])
            self.assertEqual(bridge.requests, ['POST', 'GET', 'GET'])

    def test_argument_errors_do_not_echo_unapproved_values(self):
        parser = adapter.Parser()
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer), self.assertRaisesRegex(adapter.Refused, 'CLI_ARGUMENTS_INVALID'):
            parser.parse_args(['--unapproved=do-not-echo-parameter'])
        self.assertNotIn('do-not-echo-parameter', buffer.getvalue())

    def test_retained_old_full_task_cannot_submit_when_activated(self):
        # Exercise the actual child entry used by the still-retained task 7 command.
        # This fails before constructing a bridge or creating a submission journal.
        import subprocess
        result = subprocess.run([sys.executable, '-B', str(Path(adapter.__file__).resolve()),
            '--action', 'FULL', '--operation-id', 'smallapp-20261014-full-r1',
            '--source-config-ref', SOURCE], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout.splitlines()[0]),
            {'outcome': 'REFUSED', 'errorCode': 'BUSINESS_PAGE_SELECTION_REQUIRED', 'submissionIssued': False})


if __name__ == '__main__':
    unittest.main(verbosity=2)
