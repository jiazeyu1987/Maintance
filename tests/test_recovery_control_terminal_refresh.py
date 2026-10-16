"""Temporary query-contract records only; never backup/runtime acceptance evidence."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_smallapp import Ledger, canonical, fingerprint, local_read, persist, result
from recovery_control_smallapp_native import Native


def no_dispatch(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'socket.connect'):
        raise AssertionError('QUERY_STARTED_PROCESS_OR_NETWORK')


sys.addaudithook(no_dispatch)


class TerminalRefreshChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.value = dict(schemaVersion='SmallAppBackupUiRequest/v1',
            operationId='smallapp-' + 'a' * 32, action='FULL', sourceConfigRef='query-contract-source',
            parentChainRef=None, recoveryPointRef=None, targetConfigRef=None)
        registry = self.root / 'registry'
        (registry / 'points').mkdir(parents=True)
        service = self.root / 'service.json'
        persist(service, dict(schemaVersion='SmallAppExecutionServiceConfig/v2', registryRoot=str(registry)))
        owner = self.root / 'owner.json'
        operations = self.root / 'owner-operations'
        operations.mkdir()
        persist(owner, dict(schemaVersion='RepositoryMinimumConfiguration/v1', operationRoot=str(operations)))
        self.selection = dict(configurationPin=executor.pin(service), ownerConfigurationPin=executor.pin(owner),
            ownerProgramPin=executor.pin(Path(__file__).resolve()))
        self.native = Native(executor.pin(service))
        self.ledger = Ledger(self.root, self.native)
        self.ledger.reserve(self.value, self.selection)
        self.control = self.ledger.directory(self.value['operationId'])
        execute = self.control / 'execute'
        execute.mkdir()
        request_pin = executor.pin(self.control / 'request.json')
        persist(execute / 'native-intent.json', dict(operationId=self.value['operationId'],
            requestId=self.value['operationId'], requestPin=request_pin,
            configurationPin=self.selection['ownerConfigurationPin'], programPin=self.selection['ownerProgramPin']))
        (execute / 'stdout').write_bytes(b'')
        (execute / 'stderr').write_bytes(b'')
        snapshot = self.output('TERMINAL_UNKNOWN', None, 'REPOSITORY_QUERY_ORIGINAL_OPERATION')
        persist(execute / 'result.json', snapshot)
        terminal = dict(operationId=self.value['operationId'], requestId=self.value['operationId'],
            requestPin=request_pin, actualExitCode=2, resultPin=executor.pin(execute / 'result.json'),
            stdoutPin=executor.pin(execute / 'stdout'), stderrPin=executor.pin(execute / 'stderr'))
        persist(execute / 'native-original-exit.json', terminal)
        persist(self.control / 'worker-terminal.json', dict(operationId=self.value['operationId'],
            uiRequestSha256=fingerprint(self.value), actualExitCode=2))
        persist(self.control / 'completion.json', dict(operationId=self.value['operationId'],
            uiRequestSha256=fingerprint(self.value), selection=self.selection,
            result=result(self.value, 'RUNNING', 'REPOSITORY_QUERY_ORIGINAL_OPERATION'), terminal=terminal))
        self.authority = operations / hashlib.sha256(self.value['operationId'].encode()).hexdigest()
        self.authority.mkdir()
        persist(self.authority / 'request.json', self.value)
        persist(self.authority / 'start.json', dict(configurationPin=self.selection['ownerConfigurationPin'],
            requestSha256=fingerprint(self.value), readbackOnly=False))
        self.proof = self.root / 'protocol-original.json'
        persist(self.proof, dict(scope='Temporary control-query protocol fixture, not a backup.', actualExitCode=0))
        self.preserved = {p: p.read_bytes() for p in self.control.rglob('*') if p.is_file()}

    def output(self, state, exit_code, code=None, data=None):
        return dict(schemaVersion='backup-restore-operation-result/v1', operationId=self.value['operationId'],
            requestId=self.value['operationId'], action=self.value['action'], state=state, failureCode=code,
            message='Isolated query-contract fixture; no backup was executed.', data=data,
            originalResultPins=[] if not hasattr(self, 'proof') else [executor.pin(self.proof)],
            startedAt='2026-10-15T00:00:00Z', finishedAt='2026-10-15T00:00:01Z', actualExitCode=exit_code)

    def publish(self, output):
        path = self.authority / 'result.json'
        # Only test-owned temporary query records transition; real originals
        # and the retained initial control snapshot are never edited.
        path.write_bytes(canonical(output))
        if sys.platform != 'win32':
            path.chmod(0o600)

    def assert_originals_retained(self):
        for path, raw in self.preserved.items():
            self.assertEqual(path.read_bytes(), raw)
        self.assertFalse(any(self.authority.glob('*process*')))
        self.assertEqual(self.ledger.active, set())

    def test_unknown_then_failure_refreshes_real_owner_code_without_dispatch(self):
        self.assertEqual(self.ledger.status(self.value['operationId'])['state'], 'RUNNING')
        self.publish(self.output('FAILED_RETAINED', 1, 'MINIMAL_SOURCE_RESTORATION_FAILED'))
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'FAILED')
        self.assertEqual(observed['errorCode'], 'MINIMAL_SOURCE_RESTORATION_FAILED')
        self.assertEqual(self.ledger.submit(self.value), observed)  # Existing-ID query branch only.
        observations = [local_read(p) for p in (self.control / 'queries').glob('*.json')]
        self.assertTrue(any(p['ownerActualExitCode'] == 1 and p['result'] == observed for p in observations))
        self.assert_originals_retained()

    def test_unknown_then_success_is_bound_to_latest_original_and_material(self):
        self.assertEqual(self.ledger.status(self.value['operationId'])['state'], 'RUNNING')
        self.publish(self.output('SUCCEEDED', 0, data={'materialPin': executor.pin(self.proof)}))
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'SUCCEEDED')
        binding = local_read(self.control / 'point-binding.json')
        self.assertEqual(binding['resultPin'], executor.pin(self.authority / 'result.json'))
        self.assertEqual(self.ledger.status(self.value['operationId']), observed)
        self.assert_originals_retained()

    def test_missing_or_still_unknown_authority_remains_unknown(self):
        self.assertEqual(self.ledger.status(self.value['operationId'])['errorCode'], 'ORIGINAL_OWNER_RESULT_NOT_READY')
        self.publish(self.output('TERMINAL_UNKNOWN', None, 'REPOSITORY_QUERY_ORIGINAL_OPERATION'))
        for _ in range(2):
            observed = self.ledger.status(self.value['operationId'])
            self.assertEqual(observed['state'], 'RUNNING')
            self.assertEqual(observed['errorCode'], 'REPOSITORY_QUERY_ORIGINAL_OPERATION')
        self.assertFalse((self.control / 'point-binding.json').exists())
        self.assert_originals_retained()

    def test_success_without_material_or_with_changed_original_is_unresolved(self):
        self.publish(self.output('SUCCEEDED', 0, data={'note': 'No material reference'}))
        self.assertEqual(self.ledger.status(self.value['operationId'])['state'], 'RUNNING')
        self.publish(self.output('SUCCEEDED', 0, data={'materialPin': executor.pin(self.proof)}))
        self.proof.write_bytes(b'changed protocol original')
        self.assertEqual(self.ledger.status(self.value['operationId'])['state'], 'RUNNING')
        self.assertFalse((self.control / 'point-binding.json').exists())
        self.assert_originals_retained()

    def test_changed_material_cannot_be_published_as_success(self):
        material = self.root / 'protocol-material.json'
        persist(material, {'scope': 'Temporary protocol material only'})
        self.publish(self.output('SUCCEEDED', 0, data={'materialPin': executor.pin(material)}))
        material.write_bytes(b'changed material, separate from original exit proof')
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'RUNNING')
        self.assertEqual(observed['errorCode'], 'NATIVE_PIN_CHANGED')
        self.assertFalse((self.control / 'point-binding.json').exists())
        self.assert_originals_retained()

    def test_missing_admission_does_not_create_an_owner_operation(self):
        self.authority.rename(self.authority.with_name('retained-test-admission'))
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'RUNNING')
        self.assertEqual(observed['errorCode'], 'ORIGINAL_OWNER_ADMISSION_NOT_FOUND')
        self.assertFalse(self.authority.exists())
        self.assert_originals_retained()

    def test_changed_request_or_admission_cannot_supply_a_terminal(self):
        self.publish(self.output('FAILED_RETAINED', 1, 'MINIMAL_SOURCE_RESTORATION_FAILED'))
        (self.authority / 'request.json').write_bytes(canonical({**self.value, 'sourceConfigRef': 'different-source'}))
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'RUNNING')
        self.assertEqual(observed['errorCode'], 'ORIGINAL_OWNER_REQUEST_CHANGED')
        self.assert_originals_retained()

    def test_control_exit_alone_never_becomes_owner_success(self):
        for code, expected in ((None, 'ORIGINAL_SUCCESS_INCOMPLETE'),
                               ('0', 'ORIGINAL_ACTUAL_EXIT_INVALID'), (False, 'ORIGINAL_ACTUAL_EXIT_INVALID')):
            with self.subTest(actualExitCode=code):
                self.publish(self.output('SUCCEEDED', code, data={'materialPin': executor.pin(self.proof)}))
                observed = self.ledger.status(self.value['operationId'])
                self.assertEqual(observed['state'], 'RUNNING')
                self.assertEqual(observed['errorCode'], expected)
        self.assert_originals_retained()

    def test_original_owner_exit_without_control_completion_can_be_queried(self):
        completion = self.control / 'completion.json'
        completion.unlink()  # Simulated loss of this test-owned control snapshot only.
        self.preserved.pop(completion)
        self.publish(self.output('FAILED_RETAINED', 1, 'MINIMAL_SOURCE_RESTORATION_FAILED'))
        observed = self.ledger.status(self.value['operationId'])
        self.assertEqual(observed['state'], 'FAILED')
        self.assertEqual(observed['errorCode'], 'MINIMAL_SOURCE_RESTORATION_FAILED')
        self.assertFalse(completion.exists())
        self.assert_originals_retained()

    def test_restore_admission_uses_existing_configuration_and_request(self):
        value = {**self.value, 'action': 'RESTORE', 'recoveryPointRef': 'query-contract-point',
                 'targetConfigRef': 'query-contract-target'}
        operations = self.root / 'restore-operations'
        root = operations / value['operationId']
        root.mkdir(parents=True)
        config = dict(schemaVersion='RecoveryMinimalConfiguration/v1', operationsRoot=str(operations))
        path = self.root / 'restore-owner.json'
        persist(path, config)
        persist(root / 'request.json', value)
        admission = dict(operationId=value['operationId'], requestPin=executor.pin(root / 'request.json'),
            configurationSha256=fingerprint(config))
        persist(root / 'operation.json', admission)
        selection = {**self.selection, 'ownerConfigurationPin': executor.pin(path)}
        self.assertEqual(self.native.accepted_operation(value, selection), root)
        (root / 'operation.json').write_bytes(canonical({**admission, 'configurationSha256': '0' * 64}))
        with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_OWNER_ADMISSION_CHANGED'):
            self.native.accepted_operation(value, selection)
        self.assert_originals_retained()


if __name__ == '__main__':
    unittest.main(verbosity=2)
