"""Application routing tests, including real HTTP identity checking before writes."""
import json
import unittest

from application_registry import ApplicationRegistry, RegistryError


def config():
    return dict(defaultApplication='release-inventory', applications=[
        dict(id='release-inventory', name='Inventory', repo='D:/inventory', scope='isolated local',
             status='ready', executorUrl='http://127.0.0.1:18110', bridgeKey='unit-private-key'),
        dict(id='intruoyi', name='IntRuoyi', repo='E:/IntRuoyi', scope='not connected',
             status='pending', blockers=['Dedicated executor not configured'])])


class ApplicationsTests(unittest.TestCase):
    def test_catalog_redacts_upstream_and_secrets(self):
        registry = ApplicationRegistry(config())
        raw = json.dumps(registry.catalog())
        self.assertNotIn('unit-private-key', raw)
        self.assertNotIn('executorUrl', raw)
        self.assertEqual([a['id'] for a in registry.catalog()['applications']], ['release-inventory', 'intruoyi'])

    def test_unknown_pending_and_unscoped_routes_do_not_select_another_app(self):
        registry = ApplicationRegistry(config())
        for route, method, payload, status in [
            ('/state', 'GET', None, 404),
            ('/applications/unknown-app/state', 'GET', None, 404),
            ('/applications/intruoyi/state', 'GET', None, 409),
            ('/applications/intruoyi/actions/build-release', 'POST', {'applicationId': 'intruoyi'}, 409),
            ('/applications/release-inventory/state', 'POST', {}, 405),
            ('/applications/release-inventory/actions/build-release', 'POST', {'applicationId': 'intruoyi'}, 409),
            ('/applications/release-inventory/actions/build-release', 'POST', {}, 409),
        ]:
            with self.subTest(route=route, method=method):
                with self.assertRaises(RegistryError) as error:
                    registry.resolve(route, method, payload)
                self.assertEqual(error.exception.status, status)

    def test_registration_rejects_duplicate_ids_endpoints_and_unexplained_pending(self):
        for kind in ('identity', 'endpoint', 'pending'):
            current = config()
            if kind == 'identity':
                current['applications'].append(dict(current['applications'][0]))
            elif kind == 'endpoint':
                current['applications'].append(dict(current['applications'][0], id='second-app'))
            else:
                current['applications'][1]['blockers'] = []
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                ApplicationRegistry(current)

    def test_two_real_executor_http_endpoints_route_independently(self):
        # Actual local executor processes backed by separate real state directories.
        # No fabricated upstream responses or patched network clients.
        import subprocess
        import sys
        import tempfile
        import time
        import urllib.request
        from pathlib import Path
        from socket import socket

        with tempfile.TemporaryDirectory() as folder:
            processes = []
            current = config()
            current['applications'] = []
            try:
                for identity in ('release-inventory', 'second-app'):
                    with socket() as sock:
                        sock.bind(('127.0.0.1', 0))
                        port = sock.getsockname()[1]
                    root = Path(folder) / identity
                    root.mkdir()
                    settings = dict(applicationId=identity, displayName=identity, repo=str(root),
                                    ports={}, stateDir=str(root / 'state'), mysqlImage='mysql:8.0.39',
                                    bridgeKey='unit-private-key', listenHost='127.0.0.1', port=port)
                    private = root / 'config.json'
                    private.write_text(json.dumps(settings), encoding='utf-8')
                    process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('executor.py')), '--config', str(private)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    processes.append(process)
                    origin = f'http://127.0.0.1:{port}'
                    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    for _ in range(100):
                        try:
                            request = urllib.request.Request(origin + '/state', headers={'X-Release-Key': settings['bridgeKey']})
                            with client.open(request, timeout=1) as response:
                                self.assertEqual(json.load(response)['application']['id'], identity)
                            break
                        except OSError:
                            if process.poll() is not None:
                                self.fail('Real executor exited before readiness')
                            time.sleep(.05)
                    else:
                        self.fail('Real executor did not become ready')
                    current['applications'].append(dict(id=identity, name=identity, repo=str(root), scope='isolated unit process', status='ready', executorUrl=origin, bridgeKey=settings['bridgeKey']))
                registry = ApplicationRegistry(current)
                for app in current['applications']:
                    status, raw = registry.request(app, '/state', 'GET', None, 'unit')
                    state = json.loads(raw)
                    self.assertEqual(status, 200)
                    self.assertEqual(state['application']['id'], app['id'])
                    self.assertEqual(state['application']['repo'], app['repo'])
                wrong = dict(current['applications'][0], executorUrl=current['applications'][1]['executorUrl'])
                with self.assertRaises(RegistryError):
                    registry.request(wrong, '/actions/build-release', 'POST', {'applicationId': wrong['id']}, 'unit')
                for app in current['applications']:
                    _, raw = registry.request(app, '/state', 'GET', None, 'unit')
                    self.assertEqual(json.loads(raw)['jobs'], [])
            finally:
                for process in processes:
                    process.terminate()
                for process in processes:
                    process.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
