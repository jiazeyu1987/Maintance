"""Actual loopback HTTP protocol tests; these are not backup/E2E acceptance."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

import main_program_control_staging as subject


BODY = json.dumps({'state': 'READY', 'sourceConfigRef': subject.SOURCES[0]}).encode('utf-8')


@contextmanager
def http_response(mode):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Connection', 'close')
            if mode in ('length', 'truncated'):
                self.send_header('Content-Length', str(len(BODY) + (10 if mode == 'truncated' else 0)))
            elif mode == 'chunked':
                self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            if mode == 'chunked':
                self.wfile.write(format(len(BODY), 'x').encode('ascii') + b'\r\n' + BODY + b'\r\n0\r\n\r\n')
            else:
                self.wfile.write(BODY)
            self.wfile.flush()
            self.close_connection = True

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


@pytest.mark.parametrize('mode', ['length', 'close', 'chunked'])
def test_actual_complete_http_response_preserves_budget_and_pid_checks(mode):
    checks = []
    process = {'pid': 51}
    with http_response(mode) as (port, requests):
        actual = subject.fetch_source_plan({'listenPort': port}, process, checks.append, {})
    assert actual == json.loads(BODY)
    assert checks == [process, process]
    assert requests == ['/incremental-plan?sourceConfigRef=' + subject.SOURCES[0]]


def test_actual_content_length_truncation_is_rejected():
    checks = []
    with http_response('truncated') as (port, requests):
        with pytest.raises(ValueError, match='SOURCE_HTTP_INCOMPLETE'):
            subject.fetch_source_plan({'listenPort': port}, {'pid': 51}, checks.append, {})
    assert requests == ['/incremental-plan?sourceConfigRef=' + subject.SOURCES[0]]
    assert len(checks) == 1
