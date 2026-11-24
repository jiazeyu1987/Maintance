"""Real Linux Docker/MySQL/HTTP integration. No business containers or mocks."""
import contextlib
import copy
import fcntl
import hashlib
import http.server
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import unittest

from service_recovery import Recovery, RecoveryBlocked, atomic_json, load_config, status
from service_recovery_docker import Docker


SERVICE = r'''
import http.server,json,os,time
from pathlib import Path
root=Path(os.environ['CASE_ROOT']); role=os.environ['ROLE']; control=root/(role+'.json')
mode=json.loads(control.read_text())['mode']
if mode=='recover': control.write_text(json.dumps({'mode':'healthy'}))
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  mode=json.loads(control.read_text())['mode']; good=mode=='healthy'
  raw=json.dumps({'status':'UP' if good else 'DOWN'}).encode()
  self.send_response(200 if good else 503); self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def log_message(self,*args): pass
http.server.ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
'''


class Receiver(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.server.deliveries.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(self.server.result)
        self.end_headers()

    def log_message(self, *args):
        pass


class RecoveryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docker = Docker(timeout=10)
        cls.prefix = 'maint-recovery-' + secrets.token_hex(5)
        cls.network = os.environ['RECOVERY_TEST_NETWORK']
        cls.volume = os.environ['RECOVERY_TEST_VOLUME']
        cls.receiver = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
        cls.receiver.result, cls.receiver.deliveries = 204, []
        cls.receiver_thread = threading.Thread(target=cls.receiver.serve_forever, daemon=True)
        cls.receiver_thread.start()
        cls.mysql = cls.prefix + '-mysql'
        secret = secrets.token_hex(24)
        value = cls.docker.request('POST', '/containers/create?name=' + cls.mysql, {
            'Image': 'mysql:8.0.39', 'Env': ['MYSQL_ROOT_PASSWORD=' + secret, 'MYSQL_DATABASE=recovery_test'],
            'HostConfig': {'NetworkMode': cls.network, 'Tmpfs': {'/var/lib/mysql': 'rw'}},
        })
        cls.mysql_id = value['Id']
        try:
            cls.docker.request('POST', '/containers/' + cls.mysql_id + '/start')
            deadline = time.monotonic() + 100
            while True:
                try:
                    cls.database_uuid, readonly = cls.docker.database_state(cls.mysql_id)
                    if readonly is False:
                        break
                except RecoveryBlocked:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(.5)
        except BaseException:
            cls.docker.request('DELETE', '/containers/' + cls.mysql_id + '?force=1&v=1')
            cls.receiver.shutdown()
            cls.receiver.server_close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.docker.request('DELETE', '/containers/' + cls.mysql_id + '?force=1&v=1')
        cls.receiver.shutdown()
        cls.receiver.server_close()
        cls.receiver_thread.join()

    def setUp(self):
        self.case = Path('/case') / (self.prefix + '-' + secrets.token_hex(4))
        self.case.mkdir(mode=0o700)
        self.names = {}
        self.containers = []
        self.addCleanup(self.remove_containers)
        for role in ('backend', 'frontend'):
            self.mode(role, 'healthy')
            name = self.case.name + '-' + role
            row = self.docker.request('POST', '/containers/create?name=' + name, {
                'Image': 'python:3.12-bookworm', 'Cmd': ['python', '-u', '-c', SERVICE],
                'Env': ['CASE_ROOT=' + str(self.case), 'ROLE=' + role,
                        'INTRUOYI_RELEASE_MAINTENANCE=false'],
                'HostConfig': {'NetworkMode': self.network,
                    'Mounts': [{'Type': 'volume', 'Source': self.volume, 'Target': '/case'}]},
            })
            self.containers.append(row['Id'])
            self.names[role] = name
            self.docker.request('POST', '/containers/' + row['Id'] + '/start')
        self.release = self.case / 'release'
        self.release.mkdir()
        (self.release / 'runtime-operation.lock').touch(mode=0o600)
        self.backup_lock = self.case / 'backup-source.lock'
        self.backup_lock.touch(mode=0o600)
        self.epoch = self.case / 'epoch.json'
        (self.case / 'epoch').mkdir(mode=0o700)
        epoch_policy = {'schemaVersion': 'SourceBackupEpochPolicy/v1',
            'sourceIdentity': self.case.name, 'databaseUuid': self.database_uuid,
            'sourceLockPath': str(self.backup_lock), 'root': str(self.case / 'epoch')}
        atomic_json(self.epoch, epoch_policy)
        self.state_dir = self.case / 'state'
        self.state_dir.mkdir(mode=0o700)
        self.config_file = self.case / 'config.json'
        self.config = {'schemaVersion': 'ServiceRecoveryConfig/v1', 'environment': 'test',
            'stateDirectory': str(self.state_dir), 'stagingRoot': str(self.release),
            'backupEpochPolicyFile': str(self.epoch), 'database': self.mysql,
            'services': {role: {'container': name, 'url': 'http://' + name + ':8080/',
                'kind': 'backend' if role == 'backend' else 'http'} for role, name in self.names.items()},
            'dependencies': [], 'intervalSeconds': 1, 'failureThreshold': 2,
            'startupGraceSeconds': 1, 'cooldownSeconds': 2, 'maxRestarts': 2, 'windowSeconds': 60,
            'requestTimeoutSeconds': 3, 'stopTimeoutSeconds': 2,
            'notification': {'url': 'http://127.0.0.1:' + str(self.receiver.server_port) + '/',
                'tokenFile': None, 'retrySeconds': 1, 'maxAttempts': 3}}
        atomic_json(self.config_file, self.config)
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        with self.backup_lock.open('r+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.recovery.epoch_module.initialize(epoch_policy, handle.fileno())
        deadline = time.monotonic() + 30
        while True:
            try:
                self.recovery.arm('real isolated test baseline')
                break
            except RecoveryBlocked:
                if time.monotonic() > deadline:
                    raise
                time.sleep(.1)
        self.now = time.time() + 5
        self.receiver.result = 204
        self.receiver.deliveries.clear()

    def remove_containers(self):
        for identity in reversed(self.containers):
            self.docker.request('DELETE', '/containers/' + identity + '?force=1&v=1')

    def mode(self, role, mode):
        atomic_json(self.case / (role + '.json'), {'mode': mode})

    def tick(self, advance=1):
        self.now += advance
        return self.recovery.cycle(now=self.now)

    def state(self):
        return json.loads((self.state_dir / 'state.json').read_text('utf-8'))

    def started(self, role):
        return self.docker.inspect(self.names[role])['State']['StartedAt']

    def fail_twice(self, role='backend', mode='unhealthy'):
        self.mode(role, mode)
        self.tick()
        return self.tick()

    def test_only_failed_service_restarts_then_reports_recovery(self):
        old_backend, old_frontend = self.started('backend'), self.started('frontend')
        self.mode('backend', 'recover')
        self.tick()
        self.assertEqual(self.started('backend'), old_backend, 'threshold not reached')
        self.tick()
        self.assertNotEqual(self.started('backend'), old_backend)
        self.assertEqual(self.started('frontend'), old_frontend)
        time.sleep(.3)
        self.tick(3)
        self.assertEqual(self.state()['services']['backend']['status'], 'HEALTHY')
        kinds = [e['kind'] for e in self.state()['events']]
        self.assertIn('RESTART_REQUESTED', kinds)
        self.assertIn('RECOVERED', kinds)
        self.assertTrue(all(e['delivery']['status'] == 'DELIVERED' for e in self.state()['events']))

    def test_frontend_has_own_failure_counter_and_restart(self):
        old = self.started('frontend')
        self.fail_twice('frontend', 'recover')
        self.assertNotEqual(self.started('frontend'), old)
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_private_fault_evidence_is_saved_before_restart(self):
        self.fail_twice(mode='recover')
        events = [e for e in self.state()['events'] if e['kind'] == 'RESTART_REQUESTED']
        evidence = events[-1]['detail']['evidence']
        path = Path(evidence['path'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), evidence['sha256'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_existing_release_lock_with_mode_644_remains_compatible(self):
        (self.release / 'runtime-operation.lock').chmod(0o644)
        self.fail_twice(mode='recover')
        self.assertEqual(len(self.state()['services']['backend']['attempts']), 1)

    def test_cli_once_refuses_an_existing_daemon_lock(self):
        lock = self.state_dir / 'daemon.lock'
        lock.touch(mode=0o600)
        with lock.open('r+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('service_recovery.py')),
                '--config', str(self.config_file), 'once'], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn('PROTECTION_LOCK_BUSY', result.stderr)

    def test_database_adapter_refuses_write_statements(self):
        with self.assertRaises(RecoveryBlocked):
            self.docker.sql(self.mysql_id, 'SET GLOBAL read_only=OFF;')

    def test_release_operation_after_arm_requires_rearm_even_after_lock_is_released(self):
        operations = self.release / '.operations'
        operations.mkdir(mode=0o700)
        atomic_json(operations / 'OP-example.json', {'status': 'succeeded'})
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_release_attempt_journal_also_invalidates_the_armed_baseline(self):
        operations = self.release / 'attempts' / 'JOB-0123456789' / '.operations'
        operations.mkdir(parents=True, mode=0o700)
        atomic_json(operations / 'OP-example.json', {'status': 'failed'})
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_unknown_dependency_health_blocks_arm_and_restarts(self):
        self.config['dependencies'] = [{'container': self.names['frontend']}]
        atomic_json(self.config_file, self.config)
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        with self.assertRaisesRegex(RecoveryBlocked, 'DEPENDENCY_NOT_HEALTHY'):
            self.recovery.arm('reject dependency without real healthcheck')

    def test_backend_maintenance_blocks_even_when_both_http_endpoints_are_healthy(self):
        old = self.docker.inspect(self.names['backend'])
        self.docker.request('DELETE', '/containers/' + old['Id'] + '?force=1&v=1')
        self.containers.remove(old['Id'])
        created = self.docker.request('POST', '/containers/create?name=' + self.names['backend'], {
            'Image': 'python:3.12-bookworm', 'Cmd': ['python', '-u', '-c', SERVICE],
            'Env': ['CASE_ROOT=' + str(self.case), 'ROLE=backend', 'INTRUOYI_RELEASE_MAINTENANCE=true'],
            'HostConfig': {'NetworkMode': self.network,
                'Mounts': [{'Type': 'volume', 'Source': self.volume, 'Target': '/case'}]}})
        self.containers.append(created['Id'])
        self.docker.request('POST', '/containers/' + created['Id'] + '/start')
        deadline = time.monotonic() + 15
        while not self.recovery.probe('backend', self.docker.inspect(created['Id']))[0]:
            self.assertLess(time.monotonic(), deadline, 'maintenance test HTTP endpoint did not start')
            time.sleep(.1)
        self.tick()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['protectionError'], 'RELEASE_MAINTENANCE_ACTIVE')
        with self.assertRaisesRegex(RecoveryBlocked, 'RELEASE_MAINTENANCE_ACTIVE'):
            self.recovery.arm('maintenance must block an explicit new baseline')

    def test_notification_exhaustion_is_visible_and_never_reported_delivered(self):
        self.receiver.result = 503
        for _ in range(4):
            self.tick(2)
        events = self.state()['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['delivery']['status'], 'EXHAUSTED')
        self.assertEqual(events[0]['delivery']['attempts'], 3)
        self.assertEqual(status(self.config, now=self.now)['notifications']['EXHAUSTED'], 1)

    def test_retained_restore_epoch_blocks_after_process_releases_lock(self):
        policy = json.loads(self.epoch.read_text('utf-8'))
        with self.backup_lock.open('r+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.recovery.epoch_module.begin_restore(policy, 'isolated-restore-intent', handle.fileno())
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_startup_grace_suppresses_failure_count(self):
        self.config['startupGraceSeconds'] = 100
        atomic_json(self.config_file, self.config)
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        self.recovery.arm('explicit startup grace test baseline')
        self.mode('backend', 'unhealthy')
        now = time.time()
        self.recovery.cycle(now=now)
        self.assertEqual(self.state()['services']['backend']['status'], 'STARTING')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_overlapping_controller_lock_refuses_a_second_cycle(self):
        with (self.state_dir / 'controller.lock').open('r+') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(RecoveryBlocked):
                self.tick()

    def test_restart_budget_survives_daemon_restart_and_a_healthy_sample(self):
        self.fail_twice()
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        self.mode('backend', 'healthy')
        self.tick(3)
        self.fail_twice()
        old = self.started('backend')
        self.tick(3)
        self.tick()
        self.assertEqual(self.started('backend'), old)
        self.assertEqual(self.state()['services']['backend']['status'], 'LIMIT_REACHED')
        self.assertEqual(len(self.state()['services']['backend']['attempts']), 2)
        self.assertEqual(sum(e['kind'] == 'LIMIT_REACHED' for e in self.state()['events']), 1)

    def test_stopped_container_is_never_started(self):
        self.docker.request('POST', '/containers/' + self.names['frontend'] + '/stop?t=1')
        self.fail_twice()
        self.assertFalse(self.docker.inspect(self.names['frontend'])['State']['Running'])
        self.assertEqual(self.state()['services']['backend']['attempts'], [])
        self.assertEqual(self.state()['status'], 'PROTECTED')

    def test_release_and_backup_locks_suppress_all_restarts(self):
        for path in (self.release / 'runtime-operation.lock', self.backup_lock):
            with self.subTest(lock=path.name), path.open('r+') as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                old = self.started('backend')
                self.fail_twice()
                self.assertEqual(old, self.started('backend'))
                self.assertEqual(self.state()['status'], 'PROTECTED')

    def test_database_write_fence_prevents_restarts(self):
        self.set_database_fence('ON')
        try:
            self.fail_twice()
            self.assertEqual(self.state()['services']['backend']['attempts'], [])
            self.assertEqual(self.state()['status'], 'PROTECTED')
        finally:
            self.set_database_fence('OFF')

    def set_database_fence(self, value):
        # Test-owned MySQL only. The production adapter intentionally has no SQL write API.
        result = self.docker.request('POST', '/containers/' + self.mysql_id + '/exec', {
            'AttachStdout': True, 'AttachStderr': True, 'Cmd': ['sh', '-c',
                'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -e "$1"', 'test-fence',
                'SET GLOBAL read_only=' + value + ';']})
        self.docker.request('POST', '/exec/' + result['Id'] + '/start', {'Detach': False, 'Tty': False}, raw=True)
        outcome = self.docker.request('GET', '/exec/' + result['Id'] + '/json')
        self.assertEqual(outcome['ExitCode'], 0)

    def test_pause_is_persistent_and_arm_requires_health(self):
        self.recovery.pause('planned manual service stop')
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PAUSED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])
        with self.assertRaises(RecoveryBlocked):
            self.recovery.arm('must not clear while unhealthy')
        self.assertTrue(self.state()['paused'])

    def test_identity_change_blocks_without_rebinding(self):
        state = self.state()
        state['services']['backend']['identity']['containerId'] = 'a' * 64
        atomic_json(self.state_dir / 'state.json', state)
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_unknown_restart_result_is_not_replayed(self):
        state = self.state()
        state['services']['backend']['pendingRestart'] = True
        atomic_json(self.state_dir / 'state.json', state)
        old = self.started('backend')
        self.fail_twice()
        self.assertEqual(self.started('backend'), old)
        self.assertEqual(self.state()['services']['backend']['status'], 'OUTCOME_UNKNOWN')

    def test_failed_delivery_is_visible_then_retry_and_recovery_are_delivered(self):
        self.receiver.result = 503
        self.fail_twice(mode='recover')
        events = self.state()['events']
        self.assertTrue(events)
        self.assertTrue(any(e['delivery']['status'] == 'FAILED' for e in events))
        self.receiver.result = 204
        time.sleep(.3)
        self.tick(3)
        events = self.state()['events']
        self.assertTrue(all(e['delivery']['status'] == 'DELIVERED' for e in events))
        self.assertTrue(any(e['delivery']['attempts'] > 1 for e in events))

    def test_missing_or_linked_protection_lock_blocks(self):
        self.backup_lock.unlink()
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.backup_lock.symlink_to(self.release / 'runtime-operation.lock')
        self.tick()
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_stale_heartbeat_and_clock_rollback_cannot_report_healthy(self):
        self.tick()
        self.assertEqual(status(self.recovery.c, now=self.now + 10)['status'], 'STALE')
        old = self.started('backend')
        self.mode('backend', 'unhealthy')
        self.recovery.cycle(now=self.now - 20)
        self.assertEqual(self.started('backend'), old)
        self.assertEqual(self.state()['status'], 'CLOCK_INVALID')

    def test_changed_config_requires_explicit_rearm(self):
        other = copy.deepcopy(self.config)
        other['maxRestarts'] = 3
        atomic_json(self.config_file, other)
        self.recovery = Recovery(load_config(self.config_file), docker=self.docker)
        self.fail_twice()
        self.assertEqual(self.state()['status'], 'PROTECTED')
        self.assertEqual(self.state()['services']['backend']['attempts'], [])

    def test_real_cli_status_and_pause(self):
        self.tick()
        command = [sys.executable, str(Path(__file__).with_name('service_recovery.py')),
                   '--config', str(self.config_file)]
        paused = subprocess.run(command + ['pause', '--reason', 'manual CLI maintenance'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(paused.returncode, 0, paused.stderr)
        result = subprocess.run(command + ['status'], capture_output=True, text=True, timeout=15)
        self.assertEqual(json.loads(result.stdout)['status'], 'PAUSED')


if __name__ == '__main__':
    unittest.main()
