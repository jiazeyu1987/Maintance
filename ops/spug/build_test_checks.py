"""Real filesystem/locking refusal checks; no release HTTP requests or fake server."""
import copy
import fcntl
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

import release_build_test as adapter


def hold_lock(path, ready, finish):
    with Path(path).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ready.set()
        finish.wait(10)


class BuildTestChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='spug-build-test-check-')
        self.root = Path(self.folder.name)
        self.config = copy.deepcopy(adapter.read_json(adapter.CONFIG))
        # The submitted original is immutable. Validate current code with a separate test-only input.
        self.config.pop('continuationFrom', None)
        self.config['adapterSha256'] = {name: adapter.digest(Path(adapter.__file__).with_name(name).read_bytes())
                                      for name in ('release_build_test.py', 'release_adapter.py')}
        self.path = self.root / 'config.private.json'
        self.write_config()

    def tearDown(self):
        self.folder.cleanup()

    def write_config(self):
        self.path.write_text(json.dumps(self.config), encoding='utf-8')
        self.path.chmod(0o600)

    def reserve(self, state):
        path = adapter.journal_path(self.root, self.config)
        value = dict(runId=self.config['runId'], configSha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                     sourceContext=self.config['sourceContext'], state=state,
                     baseUrl=self.config['baseUrl'], tenantId=self.config['tenantId'])
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_disabled_or_wrong_target_is_rejected_before_io_or_network(self):
        for key, value in [('allowedTargets', ['TEST', 'PROD']), ('publishEnabled', False),
                           ('productionPaused', False), ('applicationTestTenantId', 1)]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.config)
                changed[key] = value
                self.path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_SCOPE_INVALID'):
                    adapter.submit(self.path, self.root)
                self.assertEqual([], list(self.root.glob('*.worker*')))

    def test_full_source_identity_and_actual_adapter_hash_are_required(self):
        for key in ('applicationCommit', 'applicationTargetSha256', 'applicationRegistrationSha256'):
            changed = copy.deepcopy(self.config)
            changed['sourceContext'][key] = 'short'
            self.path.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_SOURCE_IDENTITY_INVALID'):
                adapter.load_config(self.path)
        self.config['adapterSha256']['release_build_test.py'] = '0' * 64
        self.write_config()
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_ADAPTER_CHANGED'):
            adapter.load_config(self.path)

    def test_different_run_id_cannot_bypass_reserved_sources(self):
        path = self.reserve('BUILDING')
        original = path.read_bytes()
        self.config['runId'] = 'another-run-id'
        self.write_config()
        self.assertEqual(path, adapter.journal_path(self.root, self.config))
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_ALREADY_RESERVED'):
            adapter.submit(self.path, self.root)
        self.assertEqual(original, path.read_bytes())

    def test_unknown_post_and_stopped_states_never_reauthenticate_or_replay(self):
        for state in ('BUILD_SUBMISSION_RESERVED', 'DEPLOY_SUBMISSION_RESERVED', 'STOPPED'):
            path = self.reserve(state)
            original = path.read_bytes()
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_WRITE_RESULT_UNKNOWN_OR_STOPPED'):
                adapter.worker(self.path, self.root)
            self.assertEqual(original, path.read_bytes())

    def test_reserved_configuration_cannot_be_replaced_even_before_submission(self):
        path = self.reserve('RESERVED')
        original = path.read_bytes()
        self.config['sourceContext']['applicationCommit'] = 'a' * 40
        self.write_config()
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_RESERVED_CONFIG_CHANGED'):
            adapter.worker(self.path, self.root)
        self.assertEqual(original, path.read_bytes())

    def test_real_concurrent_worker_lock_rejects_second_executor(self):
        path = self.reserve('RESERVED')
        original = path.read_bytes()
        ready, finish = multiprocessing.Event(), multiprocessing.Event()
        process = multiprocessing.Process(target=hold_lock, args=(str(path.with_suffix('.worker.lock')), ready, finish))
        process.start()
        try:
            self.assertTrue(ready.wait(5))
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_WORKER_ALREADY_RUNNING'):
                adapter.worker(self.path, self.root)
            self.assertEqual(original, path.read_bytes())
        finally:
            finish.set()
            process.join(5)
        self.assertEqual(0, process.exitcode)

    def test_creation_context_requires_entire_confirmed_mapping(self):
        changed = copy.deepcopy(self.config['sourceContext'])
        changed['failedBuildReference'] = 'changed-parent-evidence'
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_SOURCE_CONTEXT_CHANGED'):
            adapter.assert_context(changed, self.config['sourceContext'])

    def test_continue_unknown_writes_does_not_login_or_create_another_worker(self):
        for state in ('RESERVED', 'BUILD_SUBMISSION_RESERVED', 'DEPLOY_SUBMISSION_RESERVED', 'STOPPED', 'PASSED'):
            path = self.reserve(state)
            original = path.read_bytes()
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_CONTINUE_STAGE_UNSAFE'):
                adapter.continue_original(self.path, self.root)
            self.assertEqual(original, path.read_bytes())
            self.assertFalse(path.with_suffix('.worker.log').exists())

    def test_continue_known_stage_requires_explicit_original_operation_identity(self):
        for state in ('BUILDING', 'DEPLOYING'):
            path = self.reserve(state)
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_CONTINUE_IDENTITY_MISSING'):
                adapter.continue_original(self.path, self.root)

    def test_continue_refuses_a_live_worker_under_real_process_lock(self):
        path = self.reserve('BUILDING')
        original = path.read_bytes()
        ready, finish = multiprocessing.Event(), multiprocessing.Event()
        process = multiprocessing.Process(target=hold_lock, args=(str(path.with_suffix('.worker.lock')), ready, finish))
        process.start()
        try:
            self.assertTrue(ready.wait(5))
            with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_WORKER_ALREADY_RUNNING'):
                adapter.continue_original(self.path, self.root)
            self.assertEqual(original, path.read_bytes())
        finally:
            finish.set()
            process.join(5)
        self.assertEqual(0, process.exitcode)

    def test_continuation_is_bound_to_unchanged_original_bytes_and_cannot_submit_build(self):
        original_config = self.root / 'original.private.json'
        original_config.write_bytes(self.path.read_bytes())
        original_journal = self.reserve('STOPPED')
        value = adapter.read_json(original_journal)
        value['stoppedFrom'] = 'BUILD_SUBMISSION_RESERVED'
        original_journal.write_text(json.dumps(value), encoding='utf-8')
        self.config['continuationFrom'] = {
            'config': {'path': str(original_config), 'sha256': adapter.digest(original_config.read_bytes())},
            'journal': {'path': str(original_journal), 'sha256': adapter.digest(original_journal.read_bytes())}}
        self.write_config()
        adapter.load_config(self.path)
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_CONTINUATION_REQUIRES_CONTINUE'):
            adapter.submit(self.path, self.root)
        original_journal.write_bytes(original_journal.read_bytes() + b' ')
        with self.assertRaisesRegex(adapter.Refused, 'BUILD_TEST_CONTINUATION_ORIGINAL_CHANGED'):
            adapter.load_config(self.path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
