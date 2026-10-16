"""Temporary query-contract cases only; never live terminal or backup evidence."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest

import test_recovery_control_terminal_refresh as fixtures
import recovery_control_executor as executor
from recovery_control_smallapp import canonical, local_read, persist

SOURCE = Path(__file__).resolve().parents[1] / 'doc/tasks/20261010-backup-recovery-control-dev/entry-state-repair-20261015-r1/recovery_control_smallapp_native.py'
spec = importlib.util.spec_from_file_location('true_terminal_projection', SOURCE)
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


class TrueTerminalProjectionChecks(unittest.TestCase):
    def setUp(self):
        if sys.platform != 'linux' or os.getuid() != 0 or os.getgid() != 0:
            raise RuntimeError('LOCAL_LINUX_ROOT_REQUIRED')
        self.f = fixtures.TerminalRefreshChecks()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        owner_path = self.f.root / 'owner.json'
        old_pin = self.f.selection['ownerConfigurationPin']
        self.staging = self.f.root / 'capture-staging'
        owner = local_read(owner_path)
        owner['sources'] = {self.f.value['sourceConfigRef']: {'stagingRoot': str(self.staging)}}
        owner_path.write_bytes(canonical(owner))
        new_pin = executor.pin(owner_path)

        def replace_pin(value):
            if value == old_pin:
                return new_pin
            if type(value) is dict:
                return {key: replace_pin(item) for key, item in value.items()}
            if type(value) is list:
                return [replace_pin(item) for item in value]
            return value

        self.f.selection['ownerConfigurationPin'] = new_pin
        for name in ('selection.json', 'intent.json', 'completion.json', 'execute/native-intent.json'):
            path = self.f.control / name
            path.write_bytes(canonical(replace_pin(local_read(path))))
        start = self.f.authority / 'start.json'
        start.write_bytes(canonical(replace_pin(local_read(start))))
        for path in (self.f.authority / 'request.json', start):
            path.chmod(0o644)
        self.f.native = projection.Native(self.f.native.config_pin)
        self.f.ledger.native = self.f.native
        self.f.preserved = {path: path.read_bytes() for path in self.f.control.rglob('*') if path.is_file()}
        capture_root = self.staging / self.f.value['operationId']
        capture_root.mkdir(parents=True)
        self.capture_path = capture_root / 'terminal-result.json'
        self.copy_path = self.f.authority / 'capture-query-5-output.json'
        self.child_path = self.f.authority / 'capture-query-5-terminal.json'
        self.capture = self.f.output('FAILED_RETAINED', 1, 'MINIMAL_SOURCE_RESTORATION_FAILED')
        self.capture['originalResultPins'] = [executor.pin(self.f.authority / 'request.json'), executor.pin(self.f.proof)]
        self.child = dict(schemaVersion='RepositoryMinimumChildTerminal/v1',
            operationId=self.f.value['operationId'], state='EXITED', processTerminated=True,
            actualExitCode=1, pid=99999999, at='2026-10-15T00:00:01Z')
        self.publish()

    def publish(self, include_child=True, repository_exit=1, repository_error='MINIMAL_SOURCE_RESTORATION_FAILED'):
        for path, value in ((self.capture_path, self.capture), (self.copy_path, self.capture),
                            (self.child_path, self.child)):
            path.write_bytes(canonical(value))
            path.chmod(0o600)
        repo = self.f.output('FAILED_RETAINED', repository_exit, repository_error)
        repo['originalResultPins'] = [executor.pin(self.copy_path)]
        if include_child:
            repo['originalResultPins'].append(executor.pin(self.child_path))
        self.f.publish(repo)

    def query(self):
        return self.f.ledger.status(self.f.value['operationId'])

    def post_capture_failure(self, include_child=True):
        self.capture.update(state='SUCCEEDED', actualExitCode=0, failureCode=None)
        self.child['actualExitCode'] = 0
        self.publish(include_child=include_child, repository_exit=0,
                     repository_error='REPOSITORY_RECORD_TOO_LARGE')

    def test_repository_failure_after_capture_success_preserves_error_and_unknown_owner_exit(self):
        self.post_capture_failure()
        paths = list(self.f.authority.iterdir()) + [self.capture_path]
        retained = {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns,
                           path.stat().st_ctime_ns) for path in paths}
        observed = self.query()
        self.assertEqual(observed['state'], 'FAILED')
        self.assertEqual(observed['errorCode'], 'REPOSITORY_RECORD_TOO_LARGE')
        self.assertEqual(set(observed), set(local_read(self.f.control / 'completion.json')['result']))
        self.assertEqual(self.query(), observed)
        self.f.assert_originals_retained()
        observations = [local_read(path) for path in (self.f.control / 'queries').glob('*.json')]
        self.assertTrue(observations)
        self.assertTrue(all(item['ownerActualExitCode'] is None for item in observations))
        self.assertEqual(local_read(self.f.authority / 'result.json')['actualExitCode'], 0)
        self.assertEqual(local_read(self.child_path)['actualExitCode'], 0)
        self.assertEqual(local_read(self.f.control / 'worker-terminal.json')['actualExitCode'], 2)
        self.assertEqual(local_read(self.f.control / 'execute/native-original-exit.json')['actualExitCode'], 2)
        self.assertEqual(retained, {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns,
                                         path.stat().st_ctime_ns) for path in paths})
        self.assertFalse((self.f.control / 'point-binding.json').exists())

    def test_post_capture_unknown_or_mismatching_results_remain_protected(self):
        self.post_capture_failure()
        original = self.capture.copy()
        for change in ({'operationId': 'different-operation'}, {'requestId': 'different-operation'},
                       {'action': 'INCREMENTAL'}, {'state': 'TERMINAL_UNKNOWN'},
                       {'actualExitCode': None}, {'actualExitCode': 1}, {'actualExitCode': True},
                       {'failureCode': 'CONTRADICTORY_CAPTURE_FAILURE'},
                       {'originalResultPins': [executor.pin(self.f.proof)]}):
            with self.subTest(capture=change):
                self.capture = {**original, **change}
                self.publish(repository_exit=0, repository_error='REPOSITORY_RECORD_TOO_LARGE')
                self.assertEqual(self.query()['state'], 'RUNNING')
        self.capture = original
        self.post_capture_failure()
        for state, code, error in (('FAILED_RETAINED', None, 'REPOSITORY_RECORD_TOO_LARGE'),
                                    ('FAILED_RETAINED', 1, 'REPOSITORY_RECORD_TOO_LARGE'),
                                    ('FAILED_RETAINED', 0, None),
                                    ('TERMINAL_UNKNOWN', None, 'REPOSITORY_QUERY_ORIGINAL_OPERATION')):
            with self.subTest(repository=(state, code, error)):
                repo = self.f.output(state, code, error)
                repo['originalResultPins'] = [executor.pin(self.copy_path), executor.pin(self.child_path)]
                self.f.publish(repo)
                self.assertEqual(self.query()['state'], 'RUNNING')
        self.assertFalse((self.f.control / 'point-binding.json').exists())

    def test_post_capture_missing_or_changed_originals_cannot_project_failure(self):
        self.post_capture_failure(include_child=False)
        self.assertEqual(self.query()['state'], 'RUNNING')
        original = self.child.copy()
        for change in ({'state': 'TERMINAL_UNKNOWN'}, {'processTerminated': False},
                       {'actualExitCode': None}, {'actualExitCode': 1},
                       {'operationId': 'different-operation'}):
            with self.subTest(child=change):
                self.child = {**original, **change}
                self.publish(repository_exit=0, repository_error='REPOSITORY_RECORD_TOO_LARGE')
                self.assertEqual(self.query()['state'], 'RUNNING')
        self.child = original
        self.post_capture_failure()
        request_path = self.f.authority / 'request.json'
        request_raw = request_path.read_bytes()
        request_path.write_bytes(canonical({**self.f.value, 'sourceConfigRef': 'changed-source'}))
        self.assertEqual(self.query()['state'], 'RUNNING')
        request_path.write_bytes(request_raw)
        self.copy_path.write_bytes(b'changed pinned capture output')
        self.assertEqual(self.query()['state'], 'RUNNING')
        self.post_capture_failure()
        self.capture_path.unlink()
        self.assertEqual(self.query()['state'], 'RUNNING')
        self.assertFalse((self.f.control / 'point-binding.json').exists())

    def test_true_failure_projects_owner_exit_one_and_preserves_control_exit_two(self):
        paths = list(self.f.authority.iterdir()) + [self.capture_path]
        retained = {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns,
                           path.stat().st_ctime_ns) for path in paths}
        self.assertEqual(self.query()['state'], 'FAILED')
        self.assertEqual(self.query()['errorCode'], 'MINIMAL_SOURCE_RESTORATION_FAILED')
        self.f.assert_originals_retained()
        self.assertEqual(local_read(self.f.control / 'worker-terminal.json')['actualExitCode'], 2)
        self.assertEqual(local_read(self.f.control / 'execute/native-original-exit.json')['actualExitCode'], 2)
        observations = [local_read(path) for path in (self.f.control / 'queries').glob('*.json')]
        self.assertTrue(all(item['ownerActualExitCode'] == 1 for item in observations))
        self.assertEqual(retained, {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns,
                                         path.stat().st_ctime_ns) for path in paths})
        self.assertFalse((self.f.control / 'point-binding.json').exists())

    def test_missing_and_unknown_repository_remain_protected(self):
        capture_raw = self.capture_path.read_bytes()
        self.capture_path.unlink()
        self.assertEqual(self.query()['state'], 'RUNNING')
        self.capture_path.write_bytes(capture_raw)
        self.capture_path.chmod(0o600)
        path = self.f.authority / 'result.json'
        path.unlink()
        self.assertEqual(self.query()['state'], 'RUNNING')
        for state, code in (('TERMINAL_UNKNOWN', None), ('FAILED_RETAINED', None), ('FAILED_RETAINED', 0),
                            ('SUCCEEDED', 0)):
            with self.subTest(state=state, code=code):
                value = self.f.output(state, code, None if state == 'SUCCEEDED' else 'UNRESOLVED_TEST_CASE')
                value['originalResultPins'] = [executor.pin(self.copy_path), executor.pin(self.child_path)]
                self.f.publish(value)
                self.assertEqual(self.query()['state'], 'RUNNING')
        self.capture['failureCode'] = None
        self.publish()
        value = local_read(path)
        value['failureCode'] = None
        self.f.publish(value)
        self.assertEqual(self.query()['state'], 'RUNNING')

    def test_capture_identity_error_exit_and_request_mismatches_remain_protected(self):
        original = self.capture.copy()
        for change in ({'operationId': 'different-operation'}, {'action': 'INCREMENTAL'},
                       {'failureCode': 'DIFFERENT_FAILURE'}, {'actualExitCode': 2},
                       {'state': 'TERMINAL_UNKNOWN'}, {'originalResultPins': [executor.pin(self.f.proof)]}):
            with self.subTest(change=change):
                self.capture = {**original, **change}
                self.publish()
                self.assertEqual(self.query()['state'], 'RUNNING')

    def test_missing_or_nonterminal_child_exit_cannot_project_failure(self):
        self.publish(include_child=False)
        self.assertEqual(self.query()['state'], 'RUNNING')
        original = self.child.copy()
        for change in ({'state': 'TERMINAL_UNKNOWN'}, {'processTerminated': False},
                       {'actualExitCode': None}, {'actualExitCode': 0}, {'actualExitCode': 2},
                       {'actualExitCode': True}, {'operationId': 'different-operation'}):
            with self.subTest(change=change):
                self.child = {**original, **change}
                self.publish()
                self.assertEqual(self.query()['state'], 'RUNNING')

    def test_changed_original_request_result_pin_or_control_intent_remain_protected(self):
        request_path = self.f.authority / 'request.json'
        raw = request_path.read_bytes()
        request_path.write_bytes(canonical({**self.f.value, 'sourceConfigRef': 'changed-source'}))
        self.assertEqual(self.query()['state'], 'RUNNING')
        request_path.write_bytes(raw)
        self.copy_path.write_bytes(b'changed pinned terminal copy')
        self.assertEqual(self.query()['state'], 'RUNNING')
        self.publish()
        path = self.f.control / 'execute/native-intent.json'
        intent = local_read(path)
        intent['requestId'] = 'different-operation'
        path.write_bytes(canonical(intent))
        self.assertEqual(self.query()['state'], 'RUNNING')

    def test_unaccepted_operation_stays_not_found_without_writes(self):
        before = set(self.f.root.rglob('*'))
        with self.assertRaisesRegex(RuntimeError, 'OPERATION_NOT_FOUND'):
            self.f.ledger.status('smallapp-unaccepted-query')
        self.assertEqual(before, set(self.f.root.rglob('*')))
        self.assertEqual(self.f.ledger.active, set())


if __name__ == '__main__':
    unittest.main(verbosity=2)
