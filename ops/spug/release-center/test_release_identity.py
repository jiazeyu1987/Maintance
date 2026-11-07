"""Real local Executor/SQLite/HTTP and explicit transport-boundary faults."""
import contextlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from application_registry import ApplicationRegistry, RegistryError
from executor import Executor, create_server


@contextlib.contextmanager
def real_executor():
    with tempfile.TemporaryDirectory(prefix='release-identity-') as directory:
        config = dict(applicationId='identity-test', displayName='Identity test', repo=directory,
                      stateDir=directory, mysqlImage='mysql:8.0.39', bridgeKey='test-private-key',
                      ports={}, listenHost='127.0.0.1', port=0)
        executor = Executor(config)
        server = create_server(executor, config)
        paths = []
        original = server.RequestHandlerClass.do_GET

        def record(handler):
            paths.append(handler.path)
            return original(handler)

        server.RequestHandlerClass.do_GET = record
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        app = dict(id=config['applicationId'], name='Identity test', repo=directory, scope='local test',
                   status='ready', executorUrl='http://127.0.0.1:' + str(server.server_port),
                   bridgeKey=config['bridgeKey'])
        try:
            yield executor, app, paths
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)
            executor.process_lock.close()


def registry_for(app, **kwargs):
    return ApplicationRegistry(dict(defaultApplication=app['id'], applications=[app]), **kwargs)


def direct(app, route, *, authorized=True):
    headers = {'X-Release-Key': app['bridgeKey']} if authorized else {}
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with client.open(urllib.request.Request(app['executorUrl'] + route, headers=headers), timeout=2) as response:
        return response.status, response.read()


class ReleaseIdentityTests(unittest.TestCase):
    def test_identity_is_authenticated_small_and_independent_of_history_lock(self):
        with real_executor() as (executor, app, paths):
            executor.state['jobs'].append(dict(id='preserved-job', status='succeeded', logs=['history' * 600000]))
            executor.save()
            before = executor.store.load()
            with self.assertRaises(urllib.error.HTTPError) as denied:
                direct(app, '/identity', authorized=False)
            self.assertEqual(denied.exception.code, 409)
            with executor.lock:
                started = time.monotonic()
                status, raw = direct(app, '/identity')
                self.assertLess(time.monotonic() - started, 1.0)
            value = json.loads(raw)
            self.assertEqual(status, 200)
            self.assertEqual(value['schemaVersion'], 'ReleaseExecutorIdentity/v1')
            self.assertEqual(value['application'], {'id': app['id'], 'repo': app['repo']})
            self.assertLess(len(raw), 512)
            self.assertNotIn(app['bridgeKey'].encode(), raw)
            self.assertEqual(executor.store.load(), before)

    def test_catalogue_uses_identity_without_state_and_state_remains_compatible(self):
        with real_executor() as (executor, app, paths):
            executor.state['jobs'].append(dict(id='preserved-job', status='succeeded', logs=['history' * 600000]))
            executor.save()
            registry = registry_for(app)
            status, raw = registry.request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['schemaVersion'], 'PackageCatalog/v1')
            self.assertEqual(paths, ['/identity', '/package-catalog'])
            status, raw = registry.request(app, '/state', 'GET', None, 'test')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)['jobs'], executor.state['jobs'])
            self.assertEqual(paths[-2:], ['/identity', '/state'])

    def test_wrong_actual_identity_refuses_action_without_mutating_history(self):
        with real_executor() as (executor, app, paths):
            wrong = dict(app, id='wrong-application')
            registry = registry_for(wrong)
            with self.assertRaises(RegistryError) as error:
                registry.request(wrong, '/actions/build-release', 'POST', {'applicationId': wrong['id']}, 'test')
            self.assertEqual(error.exception.status, 409)
            self.assertEqual(paths, ['/identity'])
            self.assertEqual(executor.store.load()['jobs'], [])


@contextlib.contextmanager
def fault_server(mode):
    """Inject only wire failures; successful product behavior uses real_executor."""
    paths = []
    identities = dict(schemaVersion='ReleaseExecutorIdentity/v1', application=dict(id='identity-test', repo='test-root'))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            paths.append(self.path)
            if mode == 'header-drip':
                try:
                    self.wfile.write(b'HTTP/1.0 200 OK\r\nX-Slow: ')
                    for _ in range(30):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        time.sleep(.025)
                    raw = json.dumps(identities).encode()
                    self.wfile.write(b'\r\nContent-Length: ' + str(len(raw)).encode() + b'\r\n\r\n' + raw)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                return
            if mode == 'delay-both':
                time.sleep(.12)
            if mode == 'missing' and self.path == '/identity':
                self.send_response(404)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if mode == 'redirect':
                self.send_response(302)
                self.send_header('Location', '/redirected')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            self.send_response(503 if mode == 'http-error' and self.path != '/identity' else 200)
            if mode == 'oversized-length' and self.path == '/identity':
                self.send_header('Content-Length', str(1024 * 1024))
                self.end_headers()
                return
            raw = json.dumps(identities if self.path in ('/identity', '/state') else {'error': 'EXPLICIT_TEST_FAULT'}).encode()
            if mode == 'oversized-body' and self.path == '/identity':
                raw = b'x' * 8192
            if mode == 'drip' and self.path == '/identity':
                raw = b' ' * 50 + raw
            if mode != 'oversized-body':
                self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            try:
                if mode == 'drip' and self.path == '/identity':
                    for byte in raw:
                        self.wfile.write(bytes([byte]))
                        self.wfile.flush()
                        time.sleep(.025)
                else:
                    self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app = dict(id='identity-test', name='test', repo='test-root', scope='wire fault', status='ready',
               executorUrl='http://127.0.0.1:' + str(server.server_port), bridgeKey='test-private-key')
    try:
        yield app, paths
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


class ReleaseTransportTests(unittest.TestCase):
    def test_missing_identity_never_falls_back_to_state(self):
        with fault_server('missing') as (app, paths):
            with self.assertRaises(RegistryError) as error:
                registry_for(app).request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(error.exception.status, 502)
            self.assertEqual(paths, ['/identity'])

    def test_redirect_never_follows_or_forwards_action(self):
        with fault_server('redirect') as (app, paths):
            with self.assertRaises(RegistryError) as error:
                registry_for(app).request(app, '/actions/build-release', 'POST', {'applicationId': app['id']}, 'test')
            self.assertEqual(error.exception.status, 502)
            self.assertEqual(paths, ['/identity'])

    def test_identity_content_length_and_stream_size_are_bounded(self):
        for mode in ('oversized-length', 'oversized-body'):
            with self.subTest(mode=mode), fault_server(mode) as (app, paths):
                with self.assertRaises(RegistryError) as error:
                    registry_for(app).request(app, '/package-catalog', 'GET', None, 'test')
                self.assertEqual(error.exception.status, 502)
                self.assertIn('RESPONSE_TOO_LARGE', str(error.exception))
                self.assertEqual(paths, ['/identity'])

    def test_identity_and_route_share_total_deadline(self):
        with fault_server('delay-both') as (app, paths):
            started = time.monotonic()
            with self.assertRaises(RegistryError) as error:
                registry_for(app, request_timeout=.2).request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(error.exception.status, 504)
            self.assertLess(time.monotonic() - started, .4)
            self.assertEqual(paths, ['/identity', '/package-catalog'])

    def test_trickled_body_cannot_reset_total_deadline(self):
        with fault_server('drip') as (app, paths):
            started = time.monotonic()
            with self.assertRaises(RegistryError) as error:
                registry_for(app, request_timeout=.2).request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(error.exception.status, 504)
            self.assertLess(time.monotonic() - started, .4)
            self.assertEqual(paths, ['/identity'])

    def test_trickled_header_cannot_reset_total_deadline(self):
        with fault_server('header-drip') as (app, paths):
            started = time.monotonic()
            with self.assertRaises(RegistryError) as error:
                registry_for(app, request_timeout=.2).request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(error.exception.status, 504)
            self.assertLess(time.monotonic() - started, .4)
            self.assertEqual(paths, ['/identity'])

    def test_route_http_error_remains_an_error(self):
        with fault_server('http-error') as (app, paths):
            status, raw = registry_for(app).request(app, '/package-catalog', 'GET', None, 'test')
            self.assertEqual(status, 503)
            self.assertEqual(json.loads(raw), {'error': 'EXPLICIT_TEST_FAULT'})
            self.assertEqual(paths, ['/identity', '/package-catalog'])


if __name__ == '__main__':
    unittest.main()
