"""Local lock/durable-evidence contracts only; no backup/restore is executed."""
import concurrent.futures
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from email.message import Message
from types import SimpleNamespace
from unittest.mock import patch

import smallapp_adapter as adapter
import smallapp_entry as entry
from smallapp_checks import full


class ReservationSafety(unittest.TestCase):
    def child(self, root, body):
        code = ('import os,sys;sys.path.insert(0,sys.argv[1]);'
                'import smallapp_entry as entry,smallapp_adapter as adapter\n' + body)
        return subprocess.run([sys.executable, '-B', '-c', code,
                               str(Path(entry.__file__).parent), str(root), full()['sourceConfigRef']],
                              capture_output=True, text=True, timeout=15)

    def test_os_lock_contends_and_abrupt_exit_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            with entry.source_reservation_lock(full()['sourceConfigRef'], folder):
                child = self.child(folder,
                    "try:\n with entry.source_reservation_lock(sys.argv[3],sys.argv[2]): pass\n"
                    "except adapter.Refused as error: print(str(error));sys.exit(7)\n")
                self.assertEqual(child.returncode, 7, child.stderr)
                self.assertEqual(child.stdout.strip(), 'SOURCE_SUBMISSION_RESERVATION_BUSY')
                with self.assertRaisesRegex(adapter.Refused, 'SOURCE_SUBMISSION_RESERVATION_BUSY'):
                    with entry.source_reservation_lock(full()['sourceConfigRef'], folder):
                        self.fail('two owners in one process')
            child = self.child(folder,
                "with entry.source_reservation_lock(sys.argv[3],sys.argv[2]): os._exit(23)\n")
            self.assertEqual(child.returncode, 23, child.stderr)
            with entry.source_reservation_lock(full()['sourceConfigRef'], folder):
                self.assertEqual(len(list(Path(folder).glob('*.reserve-lock'))), 1)

    def test_legacy_directory_remains_an_explicit_blocker(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = Path(folder) / (hashlib.sha256(full()['sourceConfigRef'].encode()).hexdigest() + '.reserve-lock')
            lock.mkdir()
            with self.assertRaisesRegex(adapter.Refused, 'SOURCE_SUBMISSION_LEGACY_LOCK_PRESENT'):
                entry.reserve(full(), None, None, 1, folder)
            self.assertTrue(lock.is_dir())

    def test_released_lock_does_not_bypass_unresolved_original(self):
        with tempfile.TemporaryDirectory() as folder:
            original = full()
            adapter.write_json(entry.record_path(original['operationId'], folder), {'request': original})
            child = self.child(folder,
                "with entry.source_reservation_lock(sys.argv[3],sys.argv[2]): os._exit(23)\n")
            self.assertEqual(child.returncode, 23, child.stderr)
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_STILL_UNRESOLVED'):
                entry.reserve(dict(original, operationId='another-original-123'), None, None, 1, folder)


class TerminalEvidence(unittest.TestCase):
    def bridge(self, root):
        adapter.write_json(root / 'auth.json', {'headers': {}})
        adapter.write_json(root / 'bridge.json', dict(sourceConfigRefs=[full()['sourceConfigRef']], targetConfigRefs=[],
            submitUrl='http://127.0.0.1:1/operations', queryUrlTemplate='http://127.0.0.1:1/operations/{operationId}',
            credentialRef='auth.json'))
        return adapter.HttpBridge(root / 'bridge.json')

    def fixture(self, root, bridge):
        # Contract fixture: a persisted failed outcome, not a simulated successful backup.
        result = dict(adapter.running(full()), state='FAILED', errorCode='CONTRACT_FAILURE')
        path = root / (hashlib.sha256(full()['operationId'].encode()).hexdigest() + '.json')
        adapter.write_json(path, dict(request=full(), bridgeFingerprint=bridge.fingerprint, lastResult=result))
        return path, result

    def test_trusted_terminal_survives_unavailable_remote_without_rewriting_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = self.bridge(root)
            path, result = self.fixture(root, bridge)
            before = path.read_bytes()
            self.assertEqual(adapter.execute(full(), bridge, root, query_only=True), result)
            self.assertTrue(adapter.terminal_path(full(), root).is_file())
            self.assertEqual(adapter.execute(full(), bridge, root, query_only=True), result)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(bridge.requests, [])

    def test_cache_requires_full_request_and_bridge_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = self.bridge(root)
            path, result = self.fixture(root, bridge)
            adapter.remember_terminal(full(), bridge.fingerprint, result, root)
            cache = adapter.terminal_path(full(), root)
            value = adapter.read_json(cache)
            for delta, expected in [
                ({'request': dict(full(), sourceConfigRef='wrong-source')}, 'OPERATION_ID_REQUEST_REUSE_REJECTED'),
                ({'bridgeFingerprint': 'wrong-binding'}, 'ORIGINAL_BRIDGE_BINDING_CHANGED'),
                ({'result': dict(result, operationId='wrong-original-123')}, 'BRIDGE_ORIGINAL_OPERATION_MISMATCH')]:
                adapter.write_json(cache, dict(value, **delta))
                with self.assertRaisesRegex(adapter.Refused, expected):
                    adapter.execute(full(), bridge, root, query_only=True)
            self.assertEqual(bridge.requests, [])

    def test_concurrent_complete_publication_and_conflicting_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = self.bridge(root)
            _, result = self.fixture(root, bridge)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as workers:
                outcomes = list(workers.map(lambda _: adapter.execute(full(), bridge, root, query_only=True), range(32)))
            self.assertTrue(all(value == result for value in outcomes))
            self.assertEqual(adapter.read_json(adapter.terminal_path(full(), root))['result'], result)
            self.assertEqual(list((root / 'terminal').glob('*.tmp')), [])
            with self.assertRaisesRegex(adapter.Refused, 'TERMINAL_EVIDENCE_CONFLICT'):
                adapter.remember_terminal(full(), bridge.fingerprint, dict(result, resultRef='different-result'), root)

    def test_only_unresolved_original_is_requeried_and_then_cached(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = self.bridge(root)
            path, result = self.fixture(root, bridge)
            adapter.write_json(path, dict(request=full(), bridgeFingerprint=bridge.fingerprint,
                                         lastResult=adapter.running(full())))
            before = path.read_bytes()
            # Boundary contract injection, no E2E or actual executor success claim.
            with patch.object(bridge, 'query', return_value=result) as query:
                self.assertEqual(adapter.execute(full(), bridge, root, query_only=True), result)
                self.assertEqual(adapter.execute(full(), bridge, root, query_only=True), result)
                query.assert_called_once_with(full()['operationId'])
            self.assertEqual(path.read_bytes(), before)

    def test_reservation_checks_terminal_without_old_remote_query(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = self.bridge(root)
            self.fixture(root, bridge)
            ui = root / 'ui'
            adapter.write_json(entry.record_path(full()['operationId'], ui),
                               dict(request=full(), bridgeFingerprint=bridge.fingerprint))
            with patch.object(adapter, 'RECORDS', root), patch.object(entry, 'admit_selection',
                    side_effect=adapter.Refused('CURRENT_ADMISSION_CHECK_REACHED')):
                with self.assertRaisesRegex(adapter.Refused, 'CURRENT_ADMISSION_CHECK_REACHED'):
                    entry.reserve(dict(full(), operationId='new-operation-123'), None, bridge, 1, ui)
            self.assertEqual(bridge.requests, [])


class AtomicReservation(unittest.TestCase):
    def test_failed_serialization_and_fsync_never_publish_partial_final(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'reservation.json'
            with self.assertRaises(TypeError):
                adapter.write_json(path, {'partial': 'written', 'invalid': object()}, exclusive=True)
            self.assertFalse(path.exists())
            with patch.object(adapter.os, 'fsync', side_effect=OSError('CONTRACT_DISK_FAILURE')):
                with self.assertRaises(OSError):
                    adapter.write_json(path, {'request': full()}, exclusive=True)
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])

    def test_abrupt_writer_exit_before_publication_leaves_no_final(self):
        with tempfile.TemporaryDirectory() as folder:
            code = ('import os,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);'
                    'import smallapp_adapter as a\n'
                    'def partial(value,stream,**kwargs):\n stream.write("{\\\"partial\\\":");stream.flush();os._exit(23)\n'
                    'a.json.dump=partial\na.write_json(Path(sys.argv[2])/"reservation.json",{},exclusive=True)\n')
            child = subprocess.run([sys.executable, '-B', '-c', code,
                                    str(Path(adapter.__file__).parent), folder], capture_output=True, timeout=15)
            self.assertEqual(child.returncode, 23, child.stderr)
            self.assertFalse((Path(folder) / 'reservation.json').exists())
            self.assertEqual(len(list(Path(folder).glob('*.tmp'))), 1)

    def test_concurrent_exclusive_writers_publish_exactly_one_complete_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'reservation.json'
            def write(index):
                try:
                    adapter.write_json(path, {'writer': index, 'body': 'x' * 100000}, exclusive=True)
                    return index
                except FileExistsError:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                winners = [i for i in pool.map(write, range(32)) if i is not None]
            self.assertEqual(len(winners), 1)
            self.assertEqual(adapter.read_json(path), {'writer': winners[0], 'body': 'x' * 100000})


class DispatchRecovery(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        # Isolated failure/absence contracts; never execute Spug or a backup.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bridge = TerminalEvidence().bridge(root)
            ui = root / 'ui'
            app = dict(applicationId='contract-app', sourceConfigRef=full()['sourceConfigRef'],
                       registrationSha256='a' * 64)
            config = dict(applications=[app], tasks=dict(FULL=1, INCREMENTAL=2, RESTORE=3))
            with patch.object(adapter, 'RECORDS', root), \
                 patch.object(entry, 'operation_history_exists', return_value=False), \
                 patch.object(entry, 'admit_selection', return_value=app), \
                 patch.object(bridge, 'query', side_effect=adapter.Refused('OPERATION_NOT_FOUND')):
                yield root, ui, bridge, config

    def test_cancellation_fences_delayed_post_and_retains_evidence(self):
        with self.fixture() as (root, ui, bridge, config):
            cancelled = entry.cancel_unaccepted(full(), config, bridge, 7, ui)
            original, first = entry.reserve(full(), config, bridge, 7, ui)
            self.assertFalse(first)
            self.assertEqual(original, cancelled)
            response = entry.original_result(full()['operationId'], ui, root)
            self.assertIsNone(response['result'])
            self.assertTrue(response['cancelledUnaccepted'])
            self.assertEqual(cancelled['dispatchAudit'][0]['evidence'], 'OPERATION_NOT_FOUND')
            self.assertIsNone(entry.claim_dispatch(cancelled, ui))
            with self.assertRaisesRegex(adapter.Refused, 'SPUG_DISPATCH_RESERVATION_REQUIRED'):
                entry.prepared_request(full()['operationId'], 'FULL', ui)
            next_record, first = entry.reserve(dict(full(), operationId='corrected-original-123'), config, bridge, 7, ui)
            self.assertTrue(first)
            self.assertEqual(next_record['dispatchState'], 'RESERVED')
            self.assertEqual(adapter.read_json(entry.record_path(full()['operationId'], ui)), cancelled)

    def test_cancel_unknown_accepted_or_inflight_never_unlocks(self):
        for failure in ('BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID', 'OPERATION_RESULT_UNKNOWN'):
            with self.fixture() as (_, ui, bridge, config):
                bridge.query.side_effect = adapter.Refused(failure)
                with self.assertRaisesRegex(adapter.Refused, failure):
                    entry.cancel_unaccepted(full(), config, bridge, 7, ui)
                self.assertFalse(entry.record_path(full()['operationId'], ui).exists())
        with self.fixture() as (_, ui, bridge, config):
            entry.reserve(full(), config, bridge, 7, ui)
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_ALREADY_RECORDED'):
                entry.cancel_unaccepted(full(), config, bridge, 7, ui)

    def test_cancel_and_late_post_share_reservation_mutex(self):
        with self.fixture() as (_, ui, bridge, config):
            def native_get(_):
                with self.assertRaisesRegex(adapter.Refused, 'SOURCE_SUBMISSION_RESERVATION_BUSY'):
                    entry.reserve(full(), config, bridge, 7, ui)
                raise adapter.Refused('OPERATION_NOT_FOUND')
            bridge.query.side_effect = native_get
            entry.cancel_unaccepted(full(), config, bridge, 7, ui)
            self.assertFalse(entry.reserve(full(), config, bridge, 7, ui)[1])

    def test_post_race_returns_cancelled_original_without_dispatching(self):
        with self.fixture() as (root, ui, bridge, config):
            # HTTP route contract with isolated auth/framework seams, not E2E.
            modules = {'django.test': SimpleNamespace(RequestFactory=None),
                       'django.db': SimpleNamespace(close_old_connections=lambda: None),
                       'libs.middleware': SimpleNamespace(AuthenticationMiddleware=lambda _: None)}
            original_path = entry.record_path
            original_reserve = entry.reserve
            original_result = entry.original_result
            def cancel_during_task_check(*_):
                entry.cancel_unaccepted(full(), config, bridge, 7, ui)
            with patch.dict(sys.modules, modules), \
                 patch.object(entry, 'settings', return_value=config), \
                 patch.object(entry, 'record_path', side_effect=lambda operation, root=ui: original_path(operation, root)), \
                 patch.object(entry, 'reserve', side_effect=lambda *args: original_reserve(*args, root=ui)), \
                 patch.object(entry, 'original_result', side_effect=lambda operation: original_result(operation, ui, root)), \
                 patch.object(entry, 'installed_task', side_effect=cancel_during_task_check), \
                 patch.object(adapter, 'HttpBridge', return_value=bridge), \
                 patch.object(entry.threading, 'Thread') as thread:
                handler = object.__new__(entry.handler())
                handler.authorize = lambda edit=False: 7
                responses = []
                handler.reply = lambda status, value: responses.append((status, value))
                handler.path = '/operations'
                raw = json.dumps(full()).encode()
                handler.headers = Message()
                handler.headers['Content-Type'] = 'application/json'
                handler.headers['Content-Length'] = str(len(raw))
                handler.rfile = io.BytesIO(raw)
                handler.do_POST()
                thread.assert_not_called()
                self.assertEqual(responses[0][0], 200)
                self.assertTrue(responses[0][1]['cancelledUnaccepted'])
                self.assertIsNone(responses[0][1]['result'])

    def test_absence_rechecks_journal_after_native_get(self):
        with self.fixture() as (root, ui, bridge, config):
            def native_get(_):
                adapter.write_json(root / (hashlib.sha256(full()['operationId'].encode()).hexdigest()+'.json'),
                                   dict(request=full(), disposition='SUBMISSION_RESERVED'))
                raise adapter.Refused('OPERATION_NOT_FOUND')
            bridge.query.side_effect = native_get
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_ALREADY_RECORDED'):
                entry.cancel_unaccepted(full(), config, bridge, 7, ui)
            self.assertFalse(entry.record_path(full()['operationId'], ui).exists())

    def test_accepted_native_result_and_mismatched_request_are_refused(self):
        with self.fixture() as (_, ui, bridge, config):
            bridge.query.side_effect = None
            bridge.query.return_value = adapter.running(full())
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_ALREADY_ACCEPTED'):
                entry.cancel_unaccepted(full(), config, bridge, 7, ui)
            self.assertFalse(entry.record_path(full()['operationId'], ui).exists())
            original, _ = entry.reserve(full(), config, bridge, 7, ui)
            for operation in (entry.cancel_unaccepted, entry.recover_reserved):
                with self.assertRaisesRegex(adapter.Refused, 'OPERATION_ID_REQUEST_REUSE_REJECTED'):
                    operation(dict(full(), action='INCREMENTAL', parentChainRef='changed-parent'), config, bridge, 7, ui)
            self.assertEqual(adapter.read_json(entry.record_path(full()['operationId'], ui)), original)

    def test_recovery_revalidates_selection_without_replacing_original_on_failure(self):
        with self.fixture() as (_, ui, bridge, config):
            original, _ = entry.reserve(full(), config, bridge, 7, ui)
            with patch.object(entry, 'admit_selection', side_effect=adapter.Refused('CURRENT_ADMISSION_FAILED')):
                with self.assertRaisesRegex(adapter.Refused, 'CURRENT_ADMISSION_FAILED'):
                    entry.recover_reserved(full(), config, bridge, 7, ui)
            self.assertEqual(adapter.read_json(entry.record_path(full()['operationId'], ui)), original)

    def test_recovery_revokes_queued_token_and_claims_exactly_once(self):
        with self.fixture() as (_, ui, bridge, config):
            old, _ = entry.reserve(full(), config, bridge, 7, ui)
            with self.assertRaisesRegex(adapter.Refused, 'SPUG_DISPATCH_CLAIM_REQUIRED'):
                entry.prepared_request(full()['operationId'], 'FULL', ui)
            recovered = entry.recover_reserved(full(), config, bridge, 8, ui)
            self.assertNotEqual(old['dispatchToken'], recovered['dispatchToken'])
            self.assertEqual(recovered['dispatchAudit'][-1]['revokedToken'], old['dispatchToken'])
            before = entry.record_path(full()['operationId'], ui).read_bytes()
            self.assertIsNone(entry.claim_dispatch(old, ui))
            self.assertEqual(entry.record_path(full()['operationId'], ui).read_bytes(), before)
            claimed = entry.claim_dispatch(recovered, ui)
            self.assertEqual(claimed['dispatchState'], 'DISPATCHING')
            self.assertIsNone(entry.claim_dispatch(recovered, ui))
            self.assertEqual(entry.prepared_request(full()['operationId'], 'FULL', ui), full())
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_DISPATCH_NOT_RECOVERABLE'):
                entry.recover_reserved(full(), config, bridge, 8, ui)

    def test_reserved_adapter_unknown_legacy_and_history_are_not_recoverable(self):
        for obstruction in ('journal', 'history', 'legacy', 'unknown'):
            with self.subTest(obstruction=obstruction), self.fixture() as (root, ui, bridge, config):
                record, _ = entry.reserve(full(), config, bridge, 7, ui)
                with contextlib.ExitStack() as stack:
                    if obstruction == 'journal':
                        adapter.write_json(root / (hashlib.sha256(full()['operationId'].encode()).hexdigest()+'.json'),
                                           dict(request=full(), disposition='SUBMISSION_RESERVED'))
                    if obstruction == 'history':
                        stack.enter_context(patch.object(entry, 'operation_history_exists', return_value=True))
                    if obstruction == 'legacy':
                        del record['dispatchState']
                        adapter.write_json(entry.record_path(full()['operationId'], ui), record)
                    if obstruction == 'unknown':
                        bridge.query.side_effect = adapter.Refused('BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID')
                    before = entry.record_path(full()['operationId'], ui).read_bytes()
                    with self.assertRaises(adapter.Refused):
                        entry.recover_reserved(full(), config, bridge, 8, ui)
                    self.assertEqual(entry.record_path(full()['operationId'], ui).read_bytes(), before)

    def test_failed_claim_durable_write_never_allows_dispatch(self):
        with self.fixture() as (_, ui, bridge, config):
            record, _ = entry.reserve(full(), config, bridge, 7, ui)
            with patch.object(adapter, 'write_json', side_effect=OSError('CONTRACT_DISK_FAILURE')):
                with self.assertRaises(OSError):
                    entry.claim_dispatch(record, ui)
            self.assertEqual(adapter.read_json(entry.record_path(full()['operationId'], ui))['dispatchState'], 'RESERVED')


if __name__ == '__main__':
    print('Lock platform:', os.name, flush=True)
    unittest.main(verbosity=2)
