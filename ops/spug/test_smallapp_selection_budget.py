"""Real loopback HTTP only: directory routing/deadlines, never backup execution."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import urllib.error
from unittest.mock import patch

import pytest
import smallapp_adapter as adapter

SOURCES = ('source-a', 'source-b', 'source-c')
TARGET = 'target-t'


def row(source):
    return dict(sourceConfigRef=source, applicationId='app-' + source,
                engineSelectionRef='engine', recoveryPointRefs=['source-point'],
                parentChainRefs=['source-parent'], freshTargetConfigRefs=[])


class Endpoint:
    def __init__(self, sources, target=False):
        self.rows = [row(s) for s in sources]
        if target:
            for item in self.rows:
                item.update(recoveryPointRefs=['target-only-point'], freshTargetConfigRefs=[TARGET])
        self.events = []
        self.mode, self.delay = None, 0
        self.closed = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                owner.events.append((self.path, self.headers.get('X-Contract-Auth')))
                if owner.delay:
                    time.sleep(owner.delay)
                try:
                    if owner.mode == 'slow-header':
                        self.connection.sendall(b'HTTP/1.1 200 OK\r\nX-Slow: ')
                        for _ in range(100):
                            self.connection.sendall(b'x'); time.sleep(.03)
                        return
                    if owner.mode == 'truncated-error':
                        self.send_response(503)
                        self.send_header('Content-Length', '100')
                        self.end_headers()
                        self.wfile.write(b'{"incomplete":')
                        return
                    status = 503 if owner.mode == 'error' else 302 if owner.mode == 'redirect' else 200
                    payload = (dict(errorCode='TARGET_CONTRACT_UNAVAILABLE') if status == 503 else
                               dict(observedAt='2026-11-10T00:00:00Z', applications=owner.rows))
                    body = json.dumps(payload).encode()
                    if owner.mode == 'large':
                        body = b'x' * 65537
                    self.send_response(status)
                    if status == 302:
                        self.send_header('Location', owner.origin + '/not-followed')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    if owner.mode == 'slow-body':
                        for byte in body:
                            self.wfile.write(bytes([byte])); self.wfile.flush(); time.sleep(.03)
                    else:
                        self.wfile.write(body)
                except (OSError, ConnectionError):
                    owner.closed.set()

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.origin = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        assert not self.thread.is_alive()

    def config(self, sources, target=False):
        return dict(sourceConfigRefs=list(sources), targetConfigRefs=[TARGET],
                    submitUrl=self.origin + '/operations', queryUrlTemplate=self.origin + '/operations/{operationId}',
                    selectionUrl=self.origin + '/selections', credentialRef='auth.json', selectedTargetPreflight=target)


@pytest.fixture
def route(tmp_path):
    endpoints = [Endpoint([source]) for source in SOURCES] + [Endpoint(SOURCES, True)]
    (tmp_path / 'auth.json').write_text(json.dumps({'headers': {'X-Contract-Auth': 'local-fixture'}}), encoding='utf-8')
    root = endpoints[0].config([SOURCES[0]])
    root['sourceConnections'] = {s: str(i) + '.json' for i, s in enumerate(SOURCES)}
    root['targetConnections'] = {TARGET: 'target.json'}
    for i, source in enumerate(SOURCES):
        (tmp_path / (str(i) + '.json')).write_text(json.dumps(endpoints[i].config([source])), encoding='utf-8')
    (tmp_path / 'target.json').write_text(json.dumps(endpoints[-1].config(SOURCES, True)), encoding='utf-8')
    path = tmp_path / 'routes.json'
    path.write_text(json.dumps(root), encoding='utf-8')
    yield path, endpoints
    for endpoint in endpoints:
        endpoint.close()


def test_selected_source_contacts_only_its_directory_and_target(route):
    path, endpoints = route
    endpoints[1].mode = endpoints[2].mode = 'error'
    result = adapter.HttpBridge(path, SOURCES[0], TARGET).selections()
    assert [r['sourceConfigRef'] for r in result['applications']] == [SOURCES[0]]
    assert result['applications'][0]['recoveryPointRefs'] == ['source-point']
    assert result['applications'][0]['freshTargetConfigRefs'] == [TARGET]
    assert [len(e.events) for e in endpoints] == [1, 0, 0, 1]
    assert endpoints[-1].events == [('/selections?targetConfigRef=' + TARGET, 'local-fixture')]


def test_unselected_source_keeps_all_directories(route):
    path, endpoints = route
    result = adapter.HttpBridge(path, target_ref=TARGET).selections()
    assert [r['sourceConfigRef'] for r in result['applications']] == list(SOURCES)
    assert [len(e.events) for e in endpoints] == [1, 1, 1, 1]


@pytest.mark.parametrize('fault', [None, 'missing', 'duplicate'])
def test_shared_source_connection_still_returns_one_exact_selected_source(route, fault):
    path, endpoints = route
    original = json.loads((path.parent / '0.json').read_text(encoding='utf-8'))
    original['sourceConfigRefs'] = list(SOURCES)
    (path.parent / '0.json').write_text(json.dumps(original), encoding='utf-8')
    endpoints[0].rows = [row(s) for s in SOURCES]
    if fault == 'missing': endpoints[0].rows.pop(0)
    if fault == 'duplicate': endpoints[0].rows.append(row(SOURCES[0]))
    bridge = adapter.HttpBridge(path, SOURCES[0], TARGET)
    if fault:
        with pytest.raises(adapter.Refused, match='^W01_(TARGET_)?SELECTION_SOURCE_AMBIGUOUS$'):
            bridge.selections()
    else:
        assert [r['sourceConfigRef'] for r in bridge.selections()['applications']] == [SOURCES[0]]
    assert not endpoints[1].events and not endpoints[2].events


@pytest.mark.parametrize('fault,expected', [('error', 'TARGET_CONTRACT_UNAVAILABLE'),
    ('redirect', 'BRIDGE_REDIRECT_REFUSED'), ('large', 'BRIDGE_RESPONSE_TOO_LARGE')])
def test_target_failure_is_not_ignored_or_retried(route, fault, expected):
    path, endpoints = route
    endpoints[-1].mode = fault
    with pytest.raises(adapter.Refused, match='^' + expected + '$'):
        adapter.HttpBridge(path, SOURCES[0], TARGET).selections()
    assert [len(e.events) for e in endpoints] == [1, 0, 0, 1]


def test_truncated_optional_error_body_preserves_proven_http_status(route):
    path, endpoints = route
    endpoints[-1].mode = 'truncated-error'
    with pytest.raises(adapter.Refused, match='^BRIDGE_HTTP_503$'):
        adapter.HttpBridge(path, SOURCES[0], TARGET).selections()
    assert [len(e.events) for e in endpoints] == [1, 0, 0, 1]


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'application', 'engine'])
def test_target_source_identity_remains_strict(route, change):
    path, endpoints = route
    rows = endpoints[-1].rows
    if change == 'missing': rows.pop(0)
    elif change == 'duplicate': rows.append(copy.deepcopy(rows[0]))
    else: rows[0]['applicationId' if change == 'application' else 'engineSelectionRef'] = 'wrong'
    with pytest.raises(adapter.Refused, match='W01_TARGET_SELECTION_'):
        adapter.HttpBridge(path, SOURCES[0], TARGET).selections()
    assert not endpoints[1].events and not endpoints[2].events


@pytest.mark.parametrize('mode', ['slow-header', 'slow-body'])
def test_continuous_bytes_cannot_reset_deadline_and_socket_closes(route, mode):
    path, endpoints = route
    endpoints[0].mode = mode
    with patch.object(adapter, 'SELECTION_SOURCE_SECONDS', .20, create=True):
        start = time.monotonic()
        with pytest.raises(adapter.Refused, match='^BRIDGE_TIMEOUT$'):
            adapter.HttpBridge(path, SOURCES[0], TARGET).selections()
        assert time.monotonic() - start < 1.2
    assert endpoints[0].closed.wait(1)
    assert [len(e.events) for e in endpoints] == [1, 0, 0, 0]


def test_all_sources_share_one_deadline_and_never_return_partial_success(route):
    path, endpoints = route
    for endpoint in endpoints: endpoint.delay = .17
    with patch.object(adapter, 'SELECTION_TOTAL_SECONDS', .28, create=True):
        start = time.monotonic()
        with pytest.raises(adapter.Refused, match='^BRIDGE_TIMEOUT$'):
            adapter.HttpBridge(path, target_ref=TARGET).selections()
        assert time.monotonic() - start < .8
    assert [len(e.events) for e in endpoints] == [1, 1, 0, 0]


def test_directory_budget_is_larger_than_old_normal_call_budget(route):
    path, endpoints = route
    # Actual source and target HTTP I/O; small test budgets keep this deterministic.
    endpoints[0].delay = .07; endpoints[-1].delay = .14
    with patch.object(adapter, 'SELECTION_SOURCE_SECONDS', .30, create=True), \
         patch.object(adapter, 'SELECTION_TARGET_SECONDS', .40, create=True), \
         patch.object(adapter, 'SELECTION_TOTAL_SECONDS', .80, create=True):
        assert adapter.HttpBridge(path, SOURCES[0], TARGET).selections()['applications'][0]['freshTargetConfigRefs'] == [TARGET]
    assert [len(e.events) for e in endpoints] == [1, 0, 0, 1]


@pytest.mark.parametrize('wrapped', [False, True])
def test_python39_distinct_socket_timeout_is_classified_by_type(wrapped):
    class Python39SocketTimeout(OSError):
        pass
    error = Python39SocketTimeout('credential-must-not-escape')
    with patch.object(socket, 'timeout', Python39SocketTimeout):
        assert adapter.bridge_failure_code(urllib.error.URLError(error) if wrapped else error) == 'BRIDGE_TIMEOUT'


def test_production_budgets_are_explicit_and_bounded():
    assert adapter.SELECTION_SOURCE_SECONDS == 20
    assert adapter.SELECTION_TARGET_SECONDS == 25
    assert adapter.SELECTION_TOTAL_SECONDS == 50


def test_real_http_receives_source_and_target_budgets_without_changing_operation_transport(route):
    path, endpoints = route
    actual = adapter.HttpBridge.read_selection
    budgets = []

    def observe(bridge, url, headers, deadline):
        budgets.append((bridge.selected_target, deadline - time.monotonic()))
        return actual(bridge, url, headers, deadline)

    bridge = adapter.HttpBridge(path, SOURCES[0], TARGET)
    fingerprint = bridge.fingerprint
    with patch.object(adapter.HttpBridge, 'read_selection', observe):
        bridge.selections()
    assert len(budgets) == 2
    assert budgets[0][0] is None and 19 < budgets[0][1] <= 20
    assert budgets[1][0] == TARGET and 24 < budgets[1][1] <= 25
    assert bridge.fingerprint == fingerprint
    assert not hasattr(bridge, '_selection_deadline')
