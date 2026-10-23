from state_store import StateStore, migrate
"""Real filesystem/process invariant checks; no deployment or network actions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from executor import Executor, digest


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='release-state-')
        self.root = Path(self.temp.name)
        self.config = dict(applicationId='release-state-test', mysqlImage='mysql:8.0.39', stateDir=str(self.root))
        self.executor = None

    def tearDown(self):
        if self.executor:
            self.executor.process_lock.close()
        self.temp.cleanup()

    def test_restart_interrupts_and_duplicate_returns_original(self):
        payload = dict(requestId='request-12345678', commit='a' * 40)
        original = dict(id='original', requestId=payload['requestId'], action='build-release', payload=payload, status='running')
        (self.root / 'state.json').write_text(json.dumps(dict(packages=[], environments={}, jobs=[original])), 'utf-8')
        migrate(self.root)
        self.executor = Executor(self.config)
        job = self.executor.submit('build-release', payload, 'different-actor')
        self.assertEqual(job['id'], 'original')
        self.assertEqual(job['status'], 'interrupted')
        self.assertEqual(len(self.executor.state['jobs']), 1)
        with self.assertRaisesRegex(ValueError, 'binding mismatch'):
            self.executor.submit('build-release', dict(payload, commit='b' * 40), 'actor')
        with self.assertRaisesRegex(ValueError, 'interrupted task blocks'):
            self.executor.submit('build-release', dict(payload, requestId='other-request-123'), 'actor')

    def test_cross_process_single_executor_lock(self):
        self.executor = Executor(self.config)
        script = 'import json,sys;from executor import Executor;Executor(json.loads(sys.argv[1]))'
        result = subprocess.run([sys.executable, '-c', script, json.dumps(self.config)], cwd=Path(__file__).parent, capture_output=True)
        self.assertNotEqual(result.returncode, 0, 'Second process must not acquire active state lock')

    def test_loopback_client_reaches_real_server_without_system_proxy(self):
        class LocalHandler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                # Proxy-form requests deliberately fail; direct local requests work.
                self.send_response(502 if self.path.startswith('http://') else 200)
                self.end_headers()
                self.wfile.write(b'{"local":"reachable"}')

        server = ThreadingHTTPServer(('127.0.0.1', 0), LocalHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        proxy_env = {key:os.environ.get(key) for key in ('http_proxy', 'HTTP_PROXY', 'no_proxy', 'NO_PROXY')}
        previous_opener = urllib.request._opener
        try:
            os.environ['http_proxy'] = os.environ['HTTP_PROXY'] = 'http://127.0.0.1:' + str(server.server_port)
            os.environ['no_proxy'] = os.environ['NO_PROXY'] = ''
            urllib.request.install_opener(urllib.request.build_opener())
            self.executor = Executor(self.config)
            url = 'http://127.0.0.1:' + str(server.server_port) + '/status'
            with self.assertRaises(urllib.error.HTTPError) as failure:
                urllib.request.urlopen(url, timeout=3)
            self.assertEqual(failure.exception.code, 502)
            with self.executor.local_http.open(url, timeout=3) as response:
                self.assertEqual(json.load(response), {'local':'reachable'})
        finally:
            urllib.request._opener = previous_opener
            for key, value in proxy_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_actual_artifact_tamper_stops_package(self):
        self.executor = Executor(self.config)
        folder = self.root / 'package'
        folder.mkdir()
        artifact = folder / 'release-info.json'
        artifact.write_text('{"releaseTag":"2026-10-21-00-00-00"}', 'utf-8')
        archive = folder / 'release.tar'
        archive.write_bytes(b'artifact integrity test archive')
        manifest = folder / 'manifest.json'
        manifest.write_text(json.dumps(dict(files=[dict(name=artifact.name, sha256=digest(artifact))])), 'utf-8')
        record = dict(releaseTag='2026-10-21-00-00-00', directory=str(folder), manifestSha256=digest(manifest), packageSha256=digest(archive))
        self.executor.state['packages'] = [record]
        self.assertEqual(self.executor.package(record['releaseTag'])[0], record)
        artifact.write_text('{"releaseTag":"tampered"}', 'utf-8')
        with self.assertRaisesRegex(ValueError, 'artifact checksum mismatch'):
            self.executor.package(record['releaseTag'])

    def test_passed_origins_are_bound_to_the_exact_package(self):
        self.executor = Executor(self.config)
        p = dict(packageSha256='immutable-one', baselineFingerprint='old-single-value', rehearsals=[
            dict(status='passed', originFingerprint='production-origin', packageSha256='immutable-one'),
            dict(status='passed', originFingerprint='backup-origin', packageSha256='immutable-one'),
            dict(status='upgraded', originFingerprint='not-accepted', packageSha256='immutable-one'),
            dict(status='passed', originFingerprint='different-package', packageSha256='immutable-two')])
        self.assertTrue(self.executor.verified_origin(p, 'production-origin'))
        self.assertTrue(self.executor.verified_origin(p, 'backup-origin'))
        self.assertFalse(self.executor.verified_origin(p, 'not-accepted'))
        self.assertFalse(self.executor.verified_origin(p, 'different-package'))
        self.assertFalse(self.executor.verified_origin(p, 'old-single-value'))

    def test_precheck_refuses_mutating_or_multiple_statements(self):
        valid = dict(query='SELECT COUNT(*) FROM demo_item WHERE quantity > 1000000', expected='0', message='Quantity would violate the new constraint')
        Executor.validate_precheck(valid)
        for query in ('UPDATE demo_item SET quantity=0', 'SELECT 1; DELETE FROM demo_item',
                      "SELECT * FROM demo_item INTO OUTFILE '/tmp/x'", 'SELECT SLEEP(20)',
                      'SELECT 1 /* hidden statement */'):
            with self.subTest(query=query), self.assertRaisesRegex(ValueError, 'single read-only SELECT'):
                Executor.validate_precheck(dict(valid, query=query))

    def test_interrupted_build_requires_explicit_abandon_and_keeps_evidence(self):
        payload = dict(requestId='old-build-request', commit='a' * 40)
        original = dict(id='old-build', requestId=payload['requestId'], action='build-release', payload=payload, status='running', logs=[])
        (self.root / 'state.json').write_text(json.dumps(dict(packages=[], environments={}, jobs=[original])), 'utf-8')
        migrate(self.root)
        self.executor = Executor(self.config)
        original = self.executor.state['jobs'][0]
        retry = dict(id='resolve-1', payload=dict(jobId='old-build', decision='retry', note='Investigated unfinished build'), logs=[])
        with self.assertRaisesRegex(ValueError, 'must be abandoned'):
            self.executor.resolve_task(retry)
        self.assertNotIn('resolution', original)
        abandon = dict(id='resolve-2', actor='technician', payload=dict(jobId='old-build', decision='abandon', note='Investigated unfinished build'), logs=[])
        self.executor.resolve_task(abandon)
        self.executor.save()
        self.assertEqual(original['status'], 'interrupted')
        self.assertEqual(original['resolution']['jobId'], 'resolve-2')
        saved = StateStore(self.root).load()
        self.assertEqual(saved['jobs'][0]['resolution']['decision'], 'abandon')

    def test_real_git_duplicate_migration_numbers_stop_before_build(self):
        repo = self.root / 'source'
        repo.mkdir()
        migrations = repo / 'migrations'
        migrations.mkdir()
        (migrations / 'M000001__one.sql').write_text('CREATE TABLE one(id INT);', 'utf-8')
        (migrations / 'M000001__two.sql').write_text('CREATE TABLE two(id INT);', 'utf-8')
        for args in (['init'], ['config', 'user.email', 'test@example.invalid'], ['config', 'user.name', 'Release invariant test'], ['add', 'migrations'], ['commit', '-m', 'Numbering conflict fixture']):
            subprocess.run(['git', '-C', str(repo)] + args, check=True, capture_output=True)
        commit = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
        self.config.update(repo=str(repo), migrations='migrations')
        self.executor = Executor(self.config)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.executor.build(dict(id='duplicate-test', payload=dict(commit=commit), logs=[]))
        self.assertFalse(self.executor.state['packages'])


if __name__ == '__main__':
    unittest.main()
