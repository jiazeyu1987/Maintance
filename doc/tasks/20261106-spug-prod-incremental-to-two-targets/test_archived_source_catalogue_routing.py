"""Real localhost HTTP contracts; no Spug/server login or backup/restore execution.

Temporary documents, local HTTP fixtures and original receipts exercise the actual
HttpBridge. These tests do not simulate a successful production installation.
"""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'ops' / 'spug'))
import smallapp_adapter as adapter

CURRENT = 'intruoyi-57-safe-20261024-v1'
HISTORICAL = 'intruoyi-59-safe-20261024-v1'
LEGACY = 'intruoyi-PROD57-20261019'
TARGET = 'intruoyi-main-58-safe-restore-20261104-v1'
SOURCES = (CURRENT, HISTORICAL, LEGACY)


def request(source=HISTORICAL, action='FULL', operation='archived-routing-operation-001'):
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId=operation, action=action,
        sourceConfigRef=source, parentChainRef='original-parent' if action == 'INCREMENTAL' else None,
        recoveryPointRef='original-point' if action == 'RESTORE' else None,
        targetConfigRef=TARGET if action == 'RESTORE' else None)


def result(value):
    return dict(schemaVersion='SmallAppBackupUiResult/v1', operationId=value['operationId'],
        action=value['action'], state='SUCCEEDED', errorCode=None, logRefs=[], resultRef='original-result')


def row(source, *, new=False):
    return dict(sourceConfigRef=source, applicationId='app-' + source, engineSelectionRef='safe-engine',
        fullReady=True, fullErrorCode=None, historyErrorCode=None,
        recoveryPointRefs=[('new-point-' if new else 'old-point-') + source],
        freshTargetConfigRefs=[TARGET])


class LocalEndpoint:
    def __init__(self, name, sources, new=False):
        self.name, self.sources, self.new = name, list(sources), new
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def handle_request(self):
                size = int(self.headers.get('Content-Length', '0'))
                raw = self.rfile.read(size) if size else b''
                body = json.loads(raw) if raw else None
                owner.events.append(dict(method=self.command, path=self.path,
                    credential=self.headers.get('X-Fixture-Key'), body=body))
                route = urlsplit(self.path).path
                if self.headers.get('X-Fixture-Key') != 'fixture-' + owner.name:
                    status, payload = 401, {'errorCode': 'FIXTURE_AUTH_REJECTED'}
                elif route in owner.overrides:
                    status, payload = owner.overrides[route]
                elif route == '/selections':
                    status, payload = 200, dict(observedAt='2026-11-09T09:00:00Z', applications=copy.deepcopy(owner.rows))
                elif route == '/incremental-plan':
                    status, payload = 200, dict(state='READY', endpoint=owner.name)
                elif route == '/operations' and body is not None:
                    owner.results[body['operationId']] = result(body)
                    status, payload = 202, owner.results[body['operationId']]
                elif route.startswith('/operations/'):
                    status, payload = 200, owner.results.get(route.rsplit('/', 1)[1], {'endpoint': owner.name})
                else:
                    status, payload = 404, {'errorCode': 'FIXTURE_ROUTE_NOT_FOUND'}
                data = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
                self.send_response(status)
                if status == 302:
                    self.send_header('Location', owner.redirect_url)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.origin = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True)
        self.thread.start()
        self.reset()

    def reset(self):
        self.events, self.overrides, self.results = [], {}, {}
        self.rows = [row(source, new=self.new) for source in self.sources]
        self.redirect_url = self.origin + '/not-followed'

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise AssertionError('local fixture did not stop')

    def binding(self, sources=None, *, target=False):
        return dict(sourceConfigRefs=list(sources or self.sources), targetConfigRefs=[TARGET],
            submitUrl=self.origin + '/operations', queryUrlTemplate=self.origin + '/operations/{operationId}',
            selectionUrl=self.origin + '/selections', credentialRef=self.name + '-auth.json',
            selectedTargetPreflight=target)


class ArchivedSourceCatalogueRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.endpoints = {
            'current': LocalEndpoint('current', [CURRENT]),
            'historical': LocalEndpoint('historical', [HISTORICAL]),
            'legacy': LocalEndpoint('legacy', [LEGACY]),
            'catalogue': LocalEndpoint('catalogue', SOURCES, new=True),
            'target': LocalEndpoint('target', SOURCES),
        }

    @classmethod
    def tearDownClass(cls):
        for endpoint in cls.endpoints.values():
            endpoint.close()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for endpoint in self.endpoints.values():
            endpoint.reset()
            self.write(endpoint.name + '-auth.json', {'headers': {'X-Fixture-Key': 'fixture-' + endpoint.name}})
            self.write(endpoint.name + '.json', endpoint.binding(target=endpoint.name == 'target'))
        self.base = dict(self.endpoints['current'].binding(),
            sourceConnections={HISTORICAL: 'historical.json', LEGACY: 'legacy.json'},
            targetConnections={TARGET: 'target.json'})
        self.routes = self.root / 'routes.json'
        self.write('routes.json', self.base)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding='utf-8')

    def enable(self, mapping=None):
        value = copy.deepcopy(self.base)
        value['selectionConnections'] = mapping if mapping is not None else {source: 'catalogue.json' for source in SOURCES}
        self.write('routes.json', value)

    def bridge(self, source=None, target=None):
        return adapter.HttpBridge(self.routes, source, target)

    def catalogue_hits(self, endpoint):
        return [r for r in self.endpoints[endpoint].events if urlsplit(r['path']).path == '/selections']

    def assert_no_original_catalogue_reads(self):
        for name in ('current', 'historical', 'legacy'):
            self.assertEqual(self.catalogue_hits(name), [], name)

    def test_no_mapping_preserves_original_aggregation(self):
        payload = self.bridge().selections()
        self.assertEqual([r['sourceConfigRef'] for r in payload['applications']], list(SOURCES))
        self.assertEqual([r['recoveryPointRefs'] for r in payload['applications']],
                         [['old-point-' + source] for source in SOURCES])
        self.assertEqual(self.catalogue_hits('catalogue'), [])

    def test_shared_new_catalogue_routes_each_source_once_without_duplicate_rows(self):
        self.enable()
        payload = self.bridge().selections()
        self.assertEqual([r['sourceConfigRef'] for r in payload['applications']], list(SOURCES))
        self.assertEqual([r['recoveryPointRefs'] for r in payload['applications']],
                         [['new-point-' + source] for source in SOURCES])
        self.assert_no_original_catalogue_reads()
        self.assertTrue(self.catalogue_hits('catalogue'))
        self.assertTrue(all(r['credential'] == 'fixture-catalogue' for r in self.catalogue_hits('catalogue')))

    def test_explicit_source_gets_only_its_row_from_shared_catalogue(self):
        self.enable()
        payload = self.bridge(HISTORICAL).selections()
        self.assertEqual([r['sourceConfigRef'] for r in payload['applications']], [HISTORICAL])
        self.assertEqual(payload['applications'][0]['recoveryPointRefs'], ['new-point-' + HISTORICAL])
        self.assert_no_original_catalogue_reads()

    def test_unmapped_source_keeps_original_directory(self):
        self.enable({LEGACY: 'catalogue.json'})
        payload = self.bridge().selections()
        by_source = {r['sourceConfigRef']: r for r in payload['applications']}
        self.assertEqual(by_source[CURRENT]['recoveryPointRefs'], ['old-point-' + CURRENT])
        self.assertEqual(by_source[HISTORICAL]['recoveryPointRefs'], ['old-point-' + HISTORICAL])
        self.assertEqual(by_source[LEGACY]['recoveryPointRefs'], ['new-point-' + LEGACY])
        self.assertEqual(self.catalogue_hits('legacy'), [])

    def test_catalogue_mapping_does_not_change_execution_urls_auth_or_fingerprint(self):
        old = self.bridge(HISTORICAL)
        old_identity = (old.submit_url, old.query_template, old.selection_url, old.headers, old.fingerprint, old.origin)
        self.enable()
        updated = self.bridge(HISTORICAL)
        self.assertEqual((updated.submit_url, updated.query_template, updated.selection_url,
                          updated.headers, updated.fingerprint, updated.origin), old_identity)
        original = request()
        self.assertEqual(updated.submit(original), result(original))
        self.assertEqual(updated.query(original['operationId']), result(original))
        self.assertEqual(updated.incremental_plan(HISTORICAL), {'state': 'READY', 'endpoint': 'historical'})
        self.assertEqual([e['method'] for e in self.endpoints['historical'].events], ['POST', 'GET', 'GET'])
        self.assertEqual(self.endpoints['catalogue'].events, [])

    def test_for_request_preserves_source_and_target_dispatch_contract(self):
        original_source = self.bridge().for_request(request(LEGACY))
        original_target = self.bridge().for_request(request(HISTORICAL, 'RESTORE'))
        self.enable()
        parent = self.bridge()
        source = parent.for_request(request(LEGACY))
        target = parent.for_request(request(HISTORICAL, 'RESTORE'))
        self.assertEqual((source.submit_url, source.query_template, source.fingerprint, source.headers),
                         (original_source.submit_url, original_source.query_template, original_source.fingerprint, original_source.headers))
        self.assertEqual((target.submit_url, target.query_template, target.fingerprint, target.headers),
                         (original_target.submit_url, original_target.query_template, original_target.fingerprint, original_target.headers))
        self.assertEqual(target.selected_target, TARGET)

    def test_old_successful_history_remains_original_bytes_and_never_resubmits(self):
        original = request(LEGACY)
        before = self.bridge(LEGACY)
        records = self.root / 'records'
        terminal = adapter.execute(original, before, records)
        snapshots = {p.relative_to(records): p.read_bytes() for p in records.rglob('*.json')}
        self.enable()
        after = self.bridge(LEGACY)
        self.assertEqual(adapter.execute(original, after, records, query_only=True), terminal)
        self.assertEqual(after.fingerprint, before.fingerprint)
        self.assertEqual({p.relative_to(records): p.read_bytes() for p in records.rglob('*.json')}, snapshots)
        self.assertEqual(len([e for e in self.endpoints['legacy'].events if e['method'] == 'POST']), 1)
        self.assertEqual(self.endpoints['catalogue'].events, [])

    def test_selected_target_reads_each_explicit_source_then_target_admission(self):
        self.enable()
        self.endpoints['target'].rows[1]['freshTargetConfigRefs'] = []
        selected = self.bridge(HISTORICAL, TARGET)
        payload = selected.selections()
        self.assertEqual([r['sourceConfigRef'] for r in payload['applications']], list(SOURCES))
        self.assertEqual([r['recoveryPointRefs'] for r in payload['applications']],
                         [['new-point-' + source] for source in SOURCES])
        self.assertEqual(payload['applications'][1]['freshTargetConfigRefs'], [])
        self.assert_no_original_catalogue_reads()
        self.assertEqual([r['path'] for r in self.catalogue_hits('target')], ['/selections?targetConfigRef=' + TARGET])

    def test_selected_target_detects_new_catalogue_engine_identity_conflict(self):
        self.enable()
        self.endpoints['catalogue'].rows[1]['engineSelectionRef'] = 'different-new-engine'
        with self.assertRaisesRegex(adapter.Refused, 'W01_TARGET_SELECTION_BINDING_MISMATCH'):
            self.bridge(HISTORICAL, TARGET).selections()
        self.assert_no_original_catalogue_reads()

    def test_selected_target_detects_new_catalogue_application_identity_conflict(self):
        self.enable()
        self.endpoints['catalogue'].rows[1]['applicationId'] = 'different-application'
        with self.assertRaisesRegex(adapter.Refused, 'W01_TARGET_SELECTION_BINDING_MISMATCH'):
            self.bridge(HISTORICAL, TARGET).selections()

    def test_explicit_source_filters_unbound_extra_rows(self):
        self.enable()
        self.endpoints['catalogue'].rows.append(row('unregistered-source', new=True))
        payload = self.bridge(LEGACY).selections()
        self.assertEqual([r['sourceConfigRef'] for r in payload['applications']], [LEGACY])
        self.assertEqual(payload['applications'][0]['recoveryPointRefs'], ['new-point-' + LEGACY])

    def test_missing_mapped_source_is_rejected_without_old_directory_fallback(self):
        self.enable()
        self.endpoints['catalogue'].rows = [row(CURRENT, new=True)]
        with self.assertRaises(adapter.Refused):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_duplicate_mapped_source_is_rejected_without_old_directory_fallback(self):
        self.enable()
        self.endpoints['catalogue'].rows.append(row(HISTORICAL, new=True))
        with self.assertRaises(adapter.Refused):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_invalid_explicit_mapping_is_not_treated_as_absent(self):
        cases = [None, [], 'catalogue.json', {HISTORICAL: None}, {'bad/source': 'catalogue.json'},
                 {'unknown-source': 'catalogue.json'}, {HISTORICAL: '../catalogue.json'},
                 {HISTORICAL: '/tmp/catalogue.json'}, {HISTORICAL: 'C:\\secret.json'}]
        for mapping in cases:
            with self.subTest(mapping=mapping):
                value = copy.deepcopy(self.base); value['selectionConnections'] = mapping
                self.write('routes.json', value)
                with self.assertRaises(adapter.Refused):
                    self.bridge(HISTORICAL).selections()

    def test_missing_connection_file_is_not_replaced_with_original_directory(self):
        self.enable({HISTORICAL: 'missing-catalogue.json'})
        with self.assertRaisesRegex(adapter.Refused, 'LOCAL_INPUT_MISSING_OR_INVALID'):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_directory_connection_must_authorize_requested_source(self):
        self.enable()
        self.write('catalogue.json', self.endpoints['catalogue'].binding([CURRENT]))
        with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_directory_origin_mismatch_fails_before_any_http(self):
        self.enable()
        binding = self.endpoints['catalogue'].binding()
        binding['selectionUrl'] = self.endpoints['historical'].origin + '/selections'
        self.write('catalogue.json', binding)
        with self.assertRaisesRegex(adapter.Refused, 'W01_SELECTION_ENDPOINT_OUTSIDE_BINDING'):
            self.bridge(HISTORICAL).selections()
        self.assertTrue(all(not endpoint.events for endpoint in self.endpoints.values()))

    def test_directory_credentials_are_validated_without_fallback(self):
        self.enable()
        self.write('catalogue-auth.json', {'headers': {'Host': 'prohibited-fixture'}})
        with self.assertRaisesRegex(adapter.Refused, 'W01_PRIVATE_AUTH_HEADER_REFUSED'):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_directory_http_auth_error_does_not_use_original_credentials(self):
        self.enable()
        self.write('catalogue-auth.json', {'headers': {'X-Fixture-Key': 'fixture-wrong'}})
        with self.assertRaisesRegex(adapter.Refused, 'FIXTURE_AUTH_REJECTED'):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_directory_redirect_is_refused_without_forwarding_credentials(self):
        self.enable()
        self.endpoints['catalogue'].overrides['/selections'] = (302, b'')
        self.endpoints['catalogue'].redirect_url = self.endpoints['legacy'].origin + '/selections'
        with self.assertRaisesRegex(adapter.Refused, 'BRIDGE_REDIRECT_REFUSED'):
            self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_directory_response_validation_remains_existing_contract(self):
        cases = [(b'not-json', 'BRIDGE_RESPONSE_JSON_INVALID'),
                 (b'x' * 65537, 'BRIDGE_RESPONSE_TOO_LARGE'),
                 ({'applications': []}, 'W01_SELECTION_FIELDS_INVALID')]
        for payload, code in cases:
            with self.subTest(code=code):
                self.enable(); self.endpoints['catalogue'].overrides['/selections'] = (200, payload)
                with self.assertRaisesRegex(adapter.Refused, code):
                    self.bridge(HISTORICAL).selections()
        self.assert_no_original_catalogue_reads()

    def test_new_directory_does_not_authorize_new_source_dispatch(self):
        self.enable()
        with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
            self.bridge().for_request(request('unregistered-source'))
        self.assertTrue(all(not endpoint.events for endpoint in self.endpoints.values()))

    def test_target_connection_cannot_introduce_an_unregistered_source_via_catalogue(self):
        self.enable()
        target_binding=self.endpoints['target'].binding([*SOURCES,'unregistered-source'],target=True)
        self.write('target.json',target_binding)
        self.endpoints['catalogue'].rows.append(row('unregistered-source',new=True))
        self.endpoints['target'].rows.append(row('unregistered-source'))
        with self.assertRaisesRegex(adapter.Refused,'SOURCE_NOT_IN_CURRENT_BINDING'):
            self.bridge(HISTORICAL,TARGET).selections()
        self.assertTrue(all(event['method']=='GET' for endpoint in self.endpoints.values() for event in endpoint.events))


if __name__ == '__main__':
    unittest.main()
