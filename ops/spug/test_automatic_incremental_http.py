"""Loopback HTTP contracts, not browser E2E or proof of backup execution.

Django authentication/models are explicit local fixtures. The real dispatcher
claims the temporary reservation, then its execution adapter records the command
and raises; no command, backup, restore, database or remote service is invoked.
"""
import contextlib
import copy
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import smallapp_adapter as adapter
import smallapp_entry as entry


SOURCE = 'http-contract:source'
APP = 'http-contract-app'
TOKEN = 'a' * 32  # Deliberately synthetic; only the fixture accepts this value.


def plan(parent='http-increment-1'):
    value = dict(schemaVersion='AutomaticIncrementalPlan/v1', sourceConfigRef=SOURCE,
        state='READY', reasonCode=None, parentChainRef=parent, baseFullRef='http-full-1',
        generationId='http-full-1', chainDepth=2, pointType='INCREMENTAL',
        parentPointType='INCREMENTAL', basePointType='FULL',
        finishedAt='2026-11-07T08:00:00Z', baseFinishedAt='2026-11-06T08:00:00Z',
        evidenceDigest=hashlib.sha256(b'local-http-contract-evidence').hexdigest())
    value['planDigest'] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
    return value


def module(name, **members):
    value = types.ModuleType(name)
    value.__dict__.update(members)
    return value


class AutomaticIncrementalHttp(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.temporary = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temporary) / 'entries'
        self.journal = Path(self.temporary) / 'journal'
        self.value = plan()
        self.bridge_requests = []
        self.execution_attempts = []
        self.dispatch_errors = []
        self.dispatch_done = threading.Event()
        self.original_queries = []
        self.auth_requests = []
        self.permission_checks = []
        self.fail_plan = False
        self.tasks = {index: types.SimpleNamespace(id=index, is_active=False,
            command=entry.PREFIX + action, interpreter='sh', targets='["local"]')
            for index, action in enumerate(('FULL', 'INCREMENTAL', 'RESTORE'), 1)}
        self.config = dict(applications=[dict(applicationId=APP, displayName='HTTP contract',
            sourceConfigRef=SOURCE, targetConfigRefs=[], engineSelectionRef='http-engine',
            registrationSha256='b' * 64)], tasks=dict(FULL=1, INCREMENTAL=2, RESTORE=3),
            initialOperationIds={}, registrationVersions={APP: 'http-version'})
        self.intent = dict(schemaVersion='AutomaticIncrementalRequest/v1',
            operationId='http-contract-operation-1', applicationId=APP,
            planDigest=self.value['planDigest'])
        self._install_django_fixtures()
        self.bridge_server = self._serve(self._bridge_handler())
        origin = 'http://127.0.0.1:' + str(self.bridge_server.server_port)
        self.binding_path = Path(self.temporary) / 'bridge.json'
        self.binding = dict(sourceConfigRefs=[SOURCE], targetConfigRefs=[],
            submitUrl=origin + '/operations', queryUrlTemplate=origin + '/operations/{operationId}',
            selectionUrl=origin + '/selections', credentialRef='credential.json')
        self.binding_path.write_text(json.dumps(self.binding), encoding='utf-8')
        (Path(self.temporary) / 'credential.json').write_text(json.dumps(
            {'headers': {'X-Contract-Fixture': 'local-only'}}), encoding='utf-8')
        self.bridge_type = adapter.HttpBridge
        self.stack.enter_context(patch.object(adapter, 'HttpBridge', self._new_bridge))
        self.stack.enter_context(patch.object(adapter, 'RECORDS', self.journal))
        self.stack.enter_context(patch.object(entry, 'ENTRIES', self.root))
        self.stack.enter_context(patch.object(entry, 'settings', lambda: copy.deepcopy(self.config)))
        self.reserve_real = getattr(entry, 'reserve_automatic_incremental', None)
        self.stack.enter_context(patch.object(entry, 'reserve_automatic_incremental',
            self._reserve, create=True))
        original_real, record_path_real = entry.original_result, entry.record_path

        def original_result(operation_id):
            self.original_queries.append(operation_id)
            return original_real(operation_id, self.root, self.journal)

        self.stack.enter_context(patch.object(entry, 'original_result', original_result))
        self.stack.enter_context(patch.object(entry, 'record_path',
            lambda operation_id, root=None: record_path_real(operation_id, self.root if root is None else root)))
        claim_real, dispatch_real = entry.claim_dispatch, entry.dispatch
        self.stack.enter_context(patch.object(entry, 'claim_dispatch',
            lambda record: claim_real(record, self.root)))

        def dispatch(record, config):
            try:
                dispatch_real(record, config)
            except BaseException as error:
                self.dispatch_errors.append(error)
            finally:
                self.dispatch_done.set()

        self.stack.enter_context(patch.object(entry, 'dispatch', dispatch))
        self.server = self._serve(entry.handler())

    def _serve(self, handler):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()

        def close():
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive(), 'local HTTP server did not exit')

        self.addCleanup(close)
        return server

    def _new_bridge(self, path=None, source_ref=None, target_ref=None):
        return self.bridge_type(self.binding_path if path is None else path, source_ref, target_ref)

    def _reserve(self, intent, config, bridge, user_id, **kwargs):
        # Product defaults capture ENTRIES at import time. Pass the actual test
        # root explicitly rather than redirecting only the module constant.
        return self.reserve_real(intent, config, bridge, user_id, self.root, **kwargs)

    def _install_django_fixtures(self):
        owner = self

        class RequestFactory:
            def get(self, path, **headers):
                owner.auth_requests.append((path, headers))
                return types.SimpleNamespace(META=headers)

        class AuthenticationMiddleware:
            def __init__(self, next_handler):
                self.next_handler = next_handler

            def process_request(self, request):
                if request.META.get('HTTP_X_TOKEN') != TOKEN:
                    return object()

                def has_perms(perms):
                    owner.permission_checks.append(tuple(perms))
                    return set(perms) <= {'schedule.schedule.view', 'schedule.schedule.edit'}

                request.user = types.SimpleNamespace(id=41, is_deleted=False, has_perms=has_perms)
                return None

        class TaskManager:
            def filter(self, pk):
                return types.SimpleNamespace(first=lambda: owner.tasks.get(pk))

        def dispatch_job(host, interpreter, command):
            owner.execution_attempts.append((host, interpreter, command))
            raise RuntimeError('LOCAL_HTTP_CONTRACT_BUSINESS_EXECUTION_DISABLED')

        def forbidden_history(**kwargs):
            raise AssertionError('fixture must never claim a successful business execution')

        modules = {
            'django': module('django'),
            'django.test': module('django.test', RequestFactory=RequestFactory),
            'django.db': module('django.db', close_old_connections=lambda: None),
            'libs': module('libs', human_datetime=lambda: 'local-contract'),
            'libs.middleware': module('libs.middleware', AuthenticationMiddleware=AuthenticationMiddleware),
            'apps': module('apps'), 'apps.schedule': module('apps.schedule'),
            'apps.schedule.models': module('apps.schedule.models',
                Task=types.SimpleNamespace(objects=TaskManager()),
                History=types.SimpleNamespace(objects=types.SimpleNamespace(create=forbidden_history))),
            'apps.schedule.executors': module('apps.schedule.executors', dispatch_job=dispatch_job),
            'smallapp_simple': module('smallapp_simple', display_context=lambda request, app:
                dict(server='loopback-fixture', mode='safe', restoreMode=None)),
        }
        self.stack.enter_context(patch.dict(sys.modules, modules))

    def _bridge_handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_GET(self):
                owner.bridge_requests.append(self.path)
                parsed = urlsplit(self.path)
                if parsed.path == '/incremental-plan' and parse_qs(parsed.query) == {'sourceConfigRef': [SOURCE]}:
                    status, value = (409, {'errorCode': 'CONTRACT_PLAN_UNAVAILABLE'}) if owner.fail_plan else (200, copy.deepcopy(owner.value))
                elif self.path == '/selections':
                    status, value = 200, dict(observedAt=entry.now(), applications=[dict(
                        applicationId=APP, sourceConfigRef=SOURCE, engineSelectionRef='http-engine',
                        fullReady=True, fullErrorCode=None, parentChainRefs=['http-full-1', 'http-increment-1', 'http-increment-2'],
                        recoveryPointRefs=['http-full-1'], freshTargetConfigRefs=[], historyErrorCode=None)])
                else:
                    status, value = 409, {'errorCode': 'CONTRACT_UNEXPECTED_ENDPOINT'}
                raw = json.dumps(value).encode('utf-8')
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        return Handler

    def request(self, method, path, body=None, token=TOKEN):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            headers = {'X-Token': token, 'Origin': 'http://127.0.0.1:18080'}
            raw = None
            if body is not None:
                raw = json.dumps(body).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            connection.request(method, path, body=raw, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode('utf-8')), dict(response.getheaders())
        finally:
            connection.close()

    def accepted(self):
        status, value, _ = self.request('POST', '/automatic-incremental', self.intent)
        self.assertEqual(status, 202, value)
        self.assertTrue(self.dispatch_done.wait(timeout=5), 'real dispatch did not reach the isolated execution adapter')
        self.assertEqual(self.dispatch_errors, [])
        return value

    def test_get_plan_routes_to_only_the_registered_source_endpoint(self):
        status, value, headers = self.request('GET', '/incremental-plan?applicationId=' + APP)
        self.assertEqual(status, 200, value)
        self.assertEqual(value, dict(applicationId=APP, plan=self.value))
        self.assertEqual(self.bridge_requests, ['/incremental-plan?sourceConfigRef=http-contract%3Asource'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.permission_checks, [('schedule.schedule.view',)])
        self.assertEqual(self.execution_attempts, [])
        self.assertFalse(self.root.exists())

    def test_expired_post_returns_exact_unaccepted_proof_without_a_reservation(self):
        self.value = plan('http-increment-2')
        status, value, _ = self.request('POST', '/automatic-incremental', self.intent)
        self.assertEqual(status, 409, value)
        self.assertEqual(value, dict(errorCode='INCREMENTAL_PLAN_CHANGED', accepted=False,
            operationId=self.intent['operationId'], applicationId=APP))
        self.assertFalse(entry.record_path(self.intent['operationId']).exists())
        self.assertEqual(self.execution_attempts, [])

    def test_first_post_durably_reserves_and_real_dispatch_claims_once_without_business_execution(self):
        value = self.accepted()
        durable = adapter.read_json(entry.record_path(self.intent['operationId']))
        self.assertEqual(durable['automaticIncrementalIntent'], self.intent)
        self.assertEqual(durable['request']['parentChainRef'], 'http-increment-1')
        self.assertEqual(durable['ownerUserId'], 41)
        self.assertEqual([audit['state'] for audit in durable['dispatchAudit']], ['RESERVED', 'DISPATCHING'])
        self.assertEqual(durable['dispatchState'], 'DISPATCHING')
        self.assertEqual(durable['dispatchErrorCode'], 'SPUG_DISPATCH_OR_HISTORY_FAILED')
        self.assertIsNone(durable['spugHistoryId'])
        self.assertEqual(len(self.execution_attempts), 1)
        self.assertIn('--prepared-operation ' + self.intent['operationId'], self.execution_attempts[0][2])
        self.assertEqual(value['result']['state'], 'RUNNING')
        self.assertFalse(value['repeatSubmissionAllowed'])
        self.assertNotIn('automaticIncrementalIntent', value)

    def test_repeat_id_only_queries_original_when_new_plan_endpoint_is_unavailable(self):
        first = self.accepted()
        self.fail_plan = True
        before = list(self.bridge_requests)
        status, value, _ = self.request('POST', '/automatic-incremental', self.intent)
        self.assertEqual(status, 200, value)
        self.assertEqual(value['request'], first['request'])
        self.assertEqual(value['automaticIncrementalPlan'], first['automaticIncrementalPlan'])
        self.assertEqual(self.bridge_requests, before)
        self.assertEqual(self.original_queries, [self.intent['operationId']])
        self.assertEqual(len(self.execution_attempts), 1)

    def test_repeat_id_queries_original_even_when_manual_task_configuration_changes(self):
        first = self.accepted()
        self.fail_plan = True
        self.tasks[1].is_active = True
        self.tasks[2].command = 'unrelated-changed-template'
        before = list(self.bridge_requests)
        status, value, _ = self.request('POST', '/automatic-incremental', self.intent)
        self.assertEqual(status, 200, value)
        self.assertEqual(value['request'], first['request'])
        self.assertEqual(self.bridge_requests, before)
        self.assertEqual(self.original_queries, [self.intent['operationId']])
        self.assertEqual(len(self.execution_attempts), 1)

    def test_reused_id_with_changed_intent_never_claims_not_accepted(self):
        self.accepted()
        status, value, _ = self.request('POST', '/automatic-incremental', dict(self.intent, planDigest='c' * 64))
        self.assertEqual(status, 409, value)
        self.assertEqual(value, {'errorCode': 'OPERATION_ID_REQUEST_REUSE_REJECTED'})
        self.assertNotIn('accepted', value)
        self.assertEqual(len(self.execution_attempts), 1)

    def test_unknown_exception_before_or_after_publication_never_proves_unaccepted(self):
        for publish in (False, True):
            with self.subTest(published=publish):
                intent = dict(self.intent, operationId='http-unknown-' + str(publish).lower())

                def unknown(*args, **kwargs):
                    if publish:
                        self._reserve(*args, **kwargs)
                    raise RuntimeError('CONTRACT_UNKNOWN_OUTCOME')

                with patch.object(entry, 'reserve_automatic_incremental', unknown):
                    status, value, _ = self.request('POST', '/automatic-incremental', intent)
                self.assertEqual(status, 500, value)
                self.assertEqual(value, dict(errorCode='ENTRY_SUBMISSION_OUTCOME_UNKNOWN', retryAllowed=False))
                self.assertNotIn('accepted', value)
                self.assertEqual(entry.record_path(intent['operationId']).exists(), publish)
        self.assertEqual(self.execution_attempts, [])

    def test_handler_still_rejects_a_missing_login_token(self):
        status, value, _ = self.request('GET', '/incremental-plan?applicationId=' + APP, token='')
        self.assertEqual(status, 401)
        self.assertEqual(value, {'errorCode': 'SPUG_LOGIN_REQUIRED'})
        self.assertEqual(self.bridge_requests, [])

    def test_http_bridge_refuses_unbound_source_and_target_without_network(self):
        bridge = self._new_bridge(source_ref=SOURCE)
        with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
            bridge.incremental_plan('another-source')
        bridge.selected_target = 'registered-target'
        with self.assertRaisesRegex(adapter.Refused, 'SOURCE_NOT_IN_CURRENT_BINDING'):
            bridge.incremental_plan(SOURCE)
        self.assertEqual(self.bridge_requests, [])

    def test_http_bridge_refuses_other_origin_path_query_fragment_and_credentials(self):
        bridge = self._new_bridge(source_ref=SOURCE)
        origin = 'http://127.0.0.1:' + str(self.bridge_server.server_port)
        for endpoint in ('http://127.0.0.1:1/selections', origin + '/different',
                origin + '/selections?sourceConfigRef=another', origin + '/selections#fragment',
                origin.replace('http://', 'http://user:password@') + '/selections', None):
            with self.subTest(endpoint=endpoint):
                bridge.selection_url = endpoint
                with self.assertRaisesRegex(adapter.Refused, 'W01_SELECTION_ENDPOINT_OUTSIDE_BINDING'):
                    bridge.incremental_plan(SOURCE)
        self.assertEqual(self.bridge_requests, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
