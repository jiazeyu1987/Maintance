"""Changed-path checks with real ledger files; no successful backup is simulated."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_smallapp import Ledger, fingerprint, local_read, persist
from recovery_control_smallapp_native import Native


def request():
    return dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='smallapp-' + 'a' * 32,
        action='FULL', sourceConfigRef='contract-source', parentChainRef=None,
        recoveryPointRef=None, targetConfigRef=None)


class OriginalOperationChecks(unittest.TestCase):
    def test_real_admission_failure_is_queryable_without_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            configuration = root / 'unconfigured.json'
            persist(configuration, {})
            ledger = Ledger(root, Native(executor.pin(configuration)))
            value = request()
            observed = ledger.submit(value)
            self.assertEqual(observed['state'], 'FAILED')
            self.assertEqual(ledger.status(value['operationId']), observed)
            self.assertEqual(ledger.submit(value), observed)
            self.assertEqual(local_read(ledger.directory(value['operationId']) / 'admission-error.json'),
                             {'errorCode': observed['errorCode']})
            self.assertFalse((ledger.directory(value['operationId']) / 'worker-process.json').exists())
            self.assertEqual(ledger.active, set())

    def test_real_zero_exit_without_owner_output_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            configuration = root / 'configuration.json'
            request_path = root / 'request.json'
            persist(configuration, {})
            value = request()
            persist(request_path, value)
            # A real standard-library module exits normally without producing
            # an owner result. This is an invalid configured entry, never a
            # substitute capture or a simulated successful backup.
            terminal = executor.run_owner(executor.pin(Path(sys.executable).resolve()),
                executor.pin(Path(os.__file__).resolve()), executor.pin(configuration), executor.pin(request_path),
                root / 'result.json', environment=dict(os.environ), working_directory=str(root),
                deadline_milliseconds=10000)
            self.assertEqual(terminal['actualExitCode'], 0)
            self.assertIsNone(terminal['resultPin'])
            observed = Native(executor.pin(configuration)).owner_result(value, terminal)
            self.assertEqual(observed['state'], 'RUNNING')
            self.assertEqual(observed['errorCode'], 'OWNER_RESULT_MISSING')

    def test_real_child_argument_failure_retains_original_exit_and_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            configuration = root / 'configuration.json'
            persist(configuration, {})
            value = request()
            native = Native(executor.pin(configuration))
            ledger = Ledger(root, native)
            selection = {'configurationPin': executor.pin(configuration)}
            ledger.reserve(value, selection)
            operation_directory = ledger.directory(value['operationId'])
            execute = operation_directory / 'execute'
            execute.mkdir()
            request_path = operation_directory / 'request.json'
            output = execute / 'result.json'
            # The actual control CLI refuses owner-adapter arguments. This
            # exercises a real child failure without fabricating backup data.
            program = Path(__file__).resolve().parents[1] / 'backend/src/main/resources/recovery_control_smallapp.py'
            terminal = executor.run_owner(executor.pin(Path(sys.executable).resolve()),
                executor.pin(program), executor.pin(configuration), executor.pin(request_path), output,
                environment=dict(os.environ), working_directory=str(root), deadline_milliseconds=10000)
            self.assertEqual(terminal['operationId'], value['operationId'])
            self.assertEqual(terminal['requestId'], value['operationId'])
            self.assertEqual(terminal['actualExitCode'], 2)
            self.assertIsNone(terminal['resultPin'])
            self.assertIn('CLI_ARGUMENTS_INVALID', (execute / 'native-stderr').read_text())
            self.assertEqual(local_read(execute / 'native-original-exit.json'), terminal)
            self.assertEqual(local_read(execute / 'native-intent.json')['requestPin'], executor.pin(request_path))
            observed = native.owner_result(value, terminal)
            self.assertEqual(observed['state'], 'FAILED')
            persist(operation_directory / 'completion.json', dict(operationId=value['operationId'],
                uiRequestSha256=fingerprint(value), selection=selection, result=observed, terminal=terminal))
            # HTTP supervisor loss must not hide the worker's already-retained
            # real owner exit or create another dispatch after restart.
            self.assertFalse((operation_directory / 'worker-terminal.json').exists())
            restarted = Ledger(root, Native(executor.pin(configuration)))
            self.assertEqual(restarted.status(value['operationId']), observed)
            self.assertEqual(restarted.submit(value), observed)
            self.assertEqual(len(list(execute.glob('native-process.json'))), 1)

    def test_existing_intent_only_queries_after_restart_even_without_ready_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = root / 'unconfigured.json'
            persist(config, {})
            native = Native(executor.pin(config))
            ledger = Ledger(root, native)
            value = request()
            ledger.reserve(value, {'configurationPin': executor.pin(config)})
            before = {p.name: p.read_bytes() for p in ledger.directory(value['operationId']).iterdir()}
            for _ in range(2):
                # Resolving a new operation would fail on the actual missing
                # configuration. Reusing the durable ID must not try to run it.
                restarted = Ledger(root, Native(executor.pin(config)))
                self.assertEqual(restarted.submit(value)['state'], 'RUNNING')
            after = {p.name: p.read_bytes() for p in ledger.directory(value['operationId']).iterdir()}
            self.assertEqual(before, after)

    def test_real_missing_prerequisite_before_spawn_is_failed_and_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            config = root / 'unconfigured.json'
            persist(config, {})
            native = Native(executor.pin(config))
            ledger = Ledger(root, native)
            value = request()
            selection = {'configurationPin': executor.pin(config)}
            ledger.reserve(value, selection)
            ledger.active.add(value['operationId'])
            ledger.execute(value, ledger.directory(value['operationId']), selection)
            fault = local_read(ledger.directory(value['operationId']) / 'transport-error.json')
            self.assertIs(fault['dispatchStarted'], False)
            observed = ledger.status(value['operationId'])
            self.assertEqual(observed['state'], 'FAILED')
            self.assertEqual(observed['errorCode'], fault['errorCode'])
            self.assertFalse((ledger.directory(value['operationId']) / 'worker-process.json').exists())

    def test_unknown_owner_result_keeps_original_running_and_preserves_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            output = root / 'result.json'
            value = request()
            persist(output, dict(schemaVersion='backup-restore-operation-result/v1',
                operationId=value['operationId'], requestId=value['operationId'], action='FULL',
                state='TERMINAL_UNKNOWN', failureCode='CAPTURE_TERMINAL_UNKNOWN', message='Retained',
                data=None, originalResultPins=[], startedAt='2026-10-15T00:00:00Z',
                finishedAt='2026-10-15T00:00:01Z', actualExitCode=None))
            native = Native(executor.pin(output))
            observed = native.owner_result(value, {'resultPin': executor.pin(output), 'actualExitCode': 2})
            self.assertEqual(observed['state'], 'RUNNING')
            self.assertEqual(observed['errorCode'], 'CAPTURE_TERMINAL_UNKNOWN')
            # The real pinned bytes are checked again on every read.
            terminal = {'resultPin': executor.pin(output), 'actualExitCode': 2}
            output.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'NATIVE_PIN_CHANGED'):
                native.owner_result(value, terminal)

    def test_nonzero_actual_exit_cannot_accept_success_shaped_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder).resolve() / 'result.json'
            value = request()
            persist(output, dict(schemaVersion='backup-restore-operation-result/v1',
                operationId=value['operationId'], requestId=value['operationId'], action='FULL',
                state='SUCCEEDED', failureCode=None, message='Rejected fixture', data={},
                originalResultPins=[], startedAt='2026-10-15T00:00:00Z',
                finishedAt='2026-10-15T00:00:01Z', actualExitCode=0))
            observed = Native(executor.pin(output)).owner_result(value,
                {'resultPin': executor.pin(output), 'actualExitCode': 7})
            self.assertEqual(observed['state'], 'FAILED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
