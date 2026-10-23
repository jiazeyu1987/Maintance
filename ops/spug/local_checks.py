"""Finite pure contract and real filesystem checks. No HTTP server, API mock or deployment."""
import concurrent.futures
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import release_adapter as adapter

SELECTION = dict(workflowId='rw-local-contract-check', releaseTag='release-local-contract-check',
                 packageDigest='a' * 64, manifestDigest='b' * 64, applicationCommit='c' * 40)
CONFIG = dict(baseUrl='http://127.0.0.1:48092/admin-api', tenantId=1, username='local-check',
              password='local-check-not-a-real-credential', publishEnabled=False, productionPaused=True,
              allowedTargets=['TEST', 'BACKUP', 'PROD'])


def record(state, evidence=None):
    return dict(SELECTION, state=state, stateVersion=1, evidenceRefs=evidence or [])


def operation(target='TEST', status='succeeded'):
    return dict(operationId='local-operation', releaseWorkflowId=SELECTION['workflowId'],
                action=adapter.ROUTES[target], environment=adapter.ENVIRONMENTS[target], status=status,
                reason='Spug ' + target + ' local-attempt-1',
                parameters={k: SELECTION[k] for k in ('releaseTag', 'packageDigest', 'manifestDigest')})


class LocalContractChecks(unittest.TestCase):
    def test_no_default_candidate_and_full_identity(self):
        with self.assertRaises(adapter.Refused):
            adapter.validate_selection({})
        with self.assertRaises(adapter.Refused):
            adapter.validate_selection(dict(SELECTION, applicationCommit='c' * 7))
        adapter.validate_selection(SELECTION)
        with self.assertRaises(adapter.Refused):
            adapter.verify_binding(record('READY'), dict(SELECTION, packageDigest='d' * 64))

    def test_origin_and_boolean_policy(self):
        for config in (dict(CONFIG, baseUrl='http://external.invalid/admin-api'),
                       dict(CONFIG, baseUrl='https://user:password@example.invalid/admin-api'),
                       dict(CONFIG, publishEnabled='false'), dict(CONFIG, tenantId=True)):
            with self.assertRaises(adapter.Refused):
                adapter.origin(config)

    def test_no_multi_target_publish_or_disabled_request(self):
        for target, code in [('ALL', 'SINGLE_TARGET_REQUIRED'), ('TEST', 'PUBLISH_HOLD'),
                             ('BACKUP', 'TARGET_PUBLISH_DISABLED'), ('PROD', 'PRODUCTION_PAUSED')]:
            with self.assertRaisesRegex(adapter.Refused, code):
                adapter.publish_guard(CONFIG, target)

    def test_closed_main_requires_no_candidate_or_backend_and_creates_no_records(self):
        with tempfile.TemporaryDirectory(prefix='spug-code-only-') as temp:
            root = Path(temp)
            config_file = root / 'backend.json'
            config_file.write_text(json.dumps(CONFIG), encoding='utf-8')
            run = subprocess.run([sys.executable, str(Path(adapter.__file__)), '--config', str(config_file),
                                  '--selection', str(root / 'missing.json'), '--records', str(root / 'records'),
                                  '--target', 'TEST', '--mode', 'publish'], capture_output=True, text=True,
                                 encoding='utf-8', timeout=5)
            self.assertEqual(run.returncode, 2)
            self.assertIn('PUBLISH_HOLD', run.stdout)
            self.assertFalse((root / 'records').exists())

    def test_real_io_reservation_different_attempt_cannot_replay(self):
        with tempfile.TemporaryDirectory(prefix='spug-durable-check-') as temp:
            path = adapter.journal_path(temp, CONFIG, SELECTION, 'TEST')
            receipt = adapter.reserve(path, CONFIG, SELECTION, 'TEST', 'local-attempt-1')
            self.assertEqual(adapter.load_receipt(path, CONFIG, SELECTION, 'TEST'), receipt)
            with self.assertRaisesRegex(adapter.Refused, 'SUBMISSION_ALREADY_RESERVED'):
                adapter.reserve(path, CONFIG, SELECTION, 'TEST', 'different-attempt')
            self.assertEqual(adapter.read_json(path), receipt)
            with self.assertRaisesRegex(adapter.Refused, 'JOURNAL_BINDING_CHANGED'):
                adapter.load_receipt(path, CONFIG, dict(SELECTION, releaseTag='changed'), 'TEST')

    def test_real_io_concurrent_unique_consumption(self):
        with tempfile.TemporaryDirectory(prefix='spug-concurrency-check-') as temp:
            path = adapter.journal_path(temp, CONFIG, SELECTION, 'BACKUP')

            def claim(index):
                try:
                    adapter.reserve(path, CONFIG, SELECTION, 'BACKUP', 'attempt-number-' + str(index))
                    return True
                except adapter.Refused as error:
                    self.assertIn('SUBMISSION_ALREADY_RESERVED', str(error))
                    return False

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(claim, range(12)))
            self.assertEqual(sum(results), 1)
            self.assertEqual(len(list(Path(temp).glob('*.json'))), 1)
            self.assertEqual(adapter.read_json(path)['state'], 'SUBMISSION_RESERVED')

    def test_real_io_atomic_receipt_readback_and_process_restart(self):
        with tempfile.TemporaryDirectory(prefix='spug-receipt-check-') as temp:
            path = adapter.journal_path(temp, CONFIG, SELECTION, 'TEST')
            receipt = adapter.reserve(path, CONFIG, SELECTION, 'TEST', 'local-attempt-1')
            receipt.update(state='SUBMITTED', operationId='local-operation')
            adapter.save_receipt(path, receipt)
            code = 'import json,sys; d=json.load(open(sys.argv[1])); print(d["operationId"])'
            result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), 'local-operation')
            self.assertFalse(list(Path(temp).glob('*.tmp')))

    def test_original_operation_only_not_latest(self):
        op = operation()
        receipt = dict(attempt='local-attempt-1', operationId='local-operation')
        other = dict(op, operationId='later-operation')
        self.assertEqual(adapter.matching_operation([op, other], SELECTION, 'TEST', receipt), op)
        with self.assertRaisesRegex(adapter.Refused, 'OPERATION_AMBIGUOUS'):
            adapter.matching_operation([op, other], SELECTION, 'TEST')
        with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_MISSING'):
            adapter.matching_operation([other], SELECTION, 'TEST', receipt)

    def test_unknown_submission_matches_exact_request_reason(self):
        op = operation()
        receipt = dict(attempt='local-attempt-1', operationId=None)
        self.assertEqual(adapter.matching_operation([op], SELECTION, 'TEST', receipt), op)
        self.assertIsNone(adapter.matching_operation([dict(op, reason='Another publisher')], SELECTION, 'TEST', receipt))

    def test_wrong_target_and_artifact_are_rejected(self):
        for op in [dict(operation(), environment='prod'), dict(operation(), parameters={'releaseTag': 'wrong'})]:
            with self.assertRaisesRegex(adapter.Refused, 'OPERATION_BINDING_CHANGED'):
                adapter.matching_operation([op], SELECTION, 'TEST')

    def test_deployment_success_is_not_complete_acceptance(self):
        self.assertEqual(adapter.progress(record('TEST_DEPLOYED'), 'TEST', operation(), None)[0], 'ACCEPTANCE_PENDING')
        self.assertEqual(adapter.progress(record('TESTED'), 'TEST', operation(), None)[0], 'ACCEPTANCE_PENDING')
        accepted = record('TESTED', ['acceptance/' + 'd' * 64])
        self.assertEqual(adapter.progress(accepted, 'TEST', operation(), None)[0], 'FINAL_ACCEPTED')
        self.assertEqual(adapter.progress(accepted, 'TEST', operation(status='running'), None)[0], 'RUNNING')

    def test_backup_and_production_require_bound_evidence(self):
        for target, state, evidence in [('BACKUP', 'BACKUP_DEPLOYED', 'backup-deployed/local-operation'),
                                         ('PROD', 'COMPLETED', 'operation/local-operation.json')]:
            self.assertEqual(adapter.progress(record(state), target, operation(target), None)[0], 'ACCEPTANCE_PENDING')
            bound = dict(record(state, [evidence]), productionOperationId='local-operation')
            self.assertEqual(adapter.progress(bound, target, operation(target), None)[0], 'FINAL_ACCEPTED')
            self.assertEqual(adapter.progress(record('RECOVERY_REQUIRED', [evidence]), target, operation(target), None)[0], 'DEPLOYED_WORKFLOW_HELD')

    def test_successful_deployment_with_later_failed_acceptance_is_separate(self):
        failed = dict(record('FAILED'), failedStage='TEST_ACCEPTANCE', errorCode='RELEASE_WORKFLOW_TEST_ACCEPTANCE_FAILED')
        self.assertEqual(adapter.progress(failed, 'TEST', operation(), None)[0], 'DEPLOYED_ACCEPTANCE_FAILED')
        self.assertEqual(adapter.progress(failed, 'TEST', operation(status='failed'), None)[0], 'FINAL_FAILED')
        self.assertEqual(adapter.progress(failed, 'BACKUP', None, None)[0], 'NOT_SUBMITTED')
        self.assertEqual(adapter.progress(None, 'TEST', operation(), None)[0], 'DEPLOYED_ACCEPTANCE_UNAVAILABLE')
        self.assertEqual(adapter.progress(None, 'TEST', None, None)[0], 'WORKFLOW_QUERY_FAILED')

    def test_readonly_client_cannot_send_release_write(self):
        client = adapter.Client(CONFIG)
        with self.assertRaisesRegex(adapter.Refused, 'RELEASE_WRITE_DISABLED'):
            client.call('/infra/runtime-control/release-workflows/admit-existing-package', {})
        self.assertEqual(client.requests, [])

    def test_original_historical_operation_is_explicit_and_never_claimed_as_spug(self):
        bound = dict(SELECTION, observedTestOperationId='local-operation')
        self.assertEqual(adapter.matching_operation([operation(), dict(operation(), operationId='newer-operation')],
                                                    bound, 'TEST'), operation())
        with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_MISSING'):
            adapter.matching_operation([dict(operation(), operationId='newer-operation')], bound, 'TEST')

    def test_existing_package_context_rejects_changed_publisher_or_target(self):
        context = dict(sourceSelectionId='local-source-selection', expectedSelectionDigest='d' * 64,
                       existingPackageBindingSha256='e' * 64, executorPublisherSha256='f' * 64,
                       applicationCommit=SELECTION['applicationCommit'], frontendCommit='c' * 40,
                       testTargetProfileId='local-target', testTargetFingerprint='a' * 64,
                       testDeploymentBindingDigest='b' * 64)
        bound = dict(SELECTION, admission=context)
        self.assertEqual(adapter.check_context(context, bound), context)
        for key in ('executorPublisherSha256', 'testTargetFingerprint', 'expectedSelectionDigest'):
            with self.assertRaisesRegex(adapter.Refused, 'EXISTING_PACKAGE_APPROVAL_CHANGED'):
                adapter.check_context(dict(context, **{key: '0' * 64}), bound)
        with self.assertRaisesRegex(adapter.Refused, 'EXISTING_PACKAGE_APPROVAL_REQUIRED'):
            adapter.check_context(context, SELECTION)

    def test_unknown_and_missing_are_never_success(self):
        self.assertEqual(adapter.progress(record('READY'), 'TEST', None, None)[0], 'NOT_SUBMITTED')
        self.assertEqual(adapter.progress(record('READY'), 'TEST', None, {'state': 'SUBMISSION_RESERVED'})[0], 'SUBMISSION_UNKNOWN')
        self.assertEqual(adapter.progress(record('TESTED'), 'TEST', operation(status='unexpected'), None)[0], 'UNVERIFIED')
        with self.assertRaisesRegex(adapter.Refused, 'BACKEND_STATE_INVALID'):
            adapter.verify_binding(record('UNKNOWN_NEW_STATE'), SELECTION)

    def test_production_authorization_binding(self):
        value = dict(SELECTION, expectedStateVersion=1, targetEnvironment='prod')
        adapter.verify_authorization_binding(value, SELECTION, 1)
        for changed in (dict(value, targetEnvironment='test'), dict(value, expectedStateVersion=2),
                        dict(value, packageDigest='d' * 64)):
            with self.assertRaisesRegex(adapter.Refused, 'PRODUCTION_AUTHORIZATION_CHANGED'):
                adapter.verify_authorization_binding(changed, SELECTION, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
