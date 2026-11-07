"""Local automatic-plan/reservation contracts; never execute a real backup."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import smallapp_adapter as adapter
import smallapp_entry as entry


SOURCE = 'automatic-source'
APP = 'automatic-app'


def plan(state='READY', parent='increment-1', reason=None):
    ready = state == 'READY'
    value = dict(schemaVersion='AutomaticIncrementalPlan/v1', sourceConfigRef=SOURCE,
        state=state, reasonCode=reason, parentChainRef=parent if ready else None,
        baseFullRef='full-1' if ready else None, generationId='full-1' if ready else None,
        chainDepth=2 if ready else 0, pointType='INCREMENTAL' if ready else None,
        parentPointType='INCREMENTAL' if ready else None, basePointType='FULL' if ready else None,
        finishedAt='2026-11-07T08:00:00Z' if ready else None,
        baseFinishedAt='2026-11-06T08:00:00Z' if ready else None,
        evidenceDigest=hashlib.sha256(b'unit-evidence').hexdigest())
    value['planDigest'] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return value


class PlanBridge:
    """Explicit transport fixture for reservation unit tests, no execution endpoint."""
    fingerprint = 'a' * 64

    def __init__(self, value, root):
        self.value = value
        self.root = root
        self.plan_reads = 0
        self.source_refs = [SOURCE]

    def incremental_plan(self, source):
        assert source == SOURCE
        self.plan_reads += 1
        # The exact real OS reservation lock must already be held on submit.
        with unittest.TestCase().assertRaisesRegex(adapter.Refused, 'SOURCE_SUBMISSION_RESERVATION_BUSY'):
            with entry.source_reservation_lock(source, self.root):
                pass
        return copy.deepcopy(self.value)

    def validate_binding(self, request):
        if request['sourceConfigRef'] != SOURCE:
            raise adapter.Refused('SOURCE_NOT_IN_CURRENT_BINDING')

    def selections(self):
        return dict(observedAt=entry.now(), applications=[dict(applicationId=APP,
            sourceConfigRef=SOURCE, engineSelectionRef='engine-1', fullReady=True,
            fullErrorCode=None, parentChainRefs=['full-1', 'increment-1', 'increment-2'],
            recoveryPointRefs=['full-1', 'increment-1', 'increment-2'],
            freshTargetConfigRefs=[], historyErrorCode=None)])

    def for_request(self, request):
        self.validate_binding(request)
        return self


class AutomaticIncrementalEntry(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'ui'
        self.config = dict(applications=[dict(applicationId=APP, sourceConfigRef=SOURCE,
            targetConfigRefs=[], registrationSha256='b' * 64)],
            tasks=dict(FULL=1, INCREMENTAL=2, RESTORE=3))
        self.bridge = PlanBridge(plan(), self.root)
        self.intent = dict(schemaVersion='AutomaticIncrementalRequest/v1',
            operationId='automatic-operation-1', applicationId=APP,
            planDigest=self.bridge.value['planDigest'])

    def reserve(self, intent=None):
        function = getattr(entry, 'reserve_automatic_incremental', None)
        self.assertTrue(callable(function), 'automatic server-side reservation is missing')
        return function(intent or self.intent, self.config, self.bridge, 7, self.root)

    def test_history_free_request_binds_latest_increment_and_full_root(self):
        record, first = self.reserve()
        self.assertTrue(first)
        self.assertEqual(record['request'], dict(schemaVersion='SmallAppBackupUiRequest/v1',
            operationId=self.intent['operationId'], action='INCREMENTAL', sourceConfigRef=SOURCE,
            parentChainRef='increment-1', recoveryPointRef=None, targetConfigRef=None))
        self.assertEqual(record['automaticIncrementalPlan']['baseFullRef'], 'full-1')
        self.assertEqual(record['automaticIncrementalIntent'], self.intent)
        self.assertEqual(adapter.read_json(entry.record_path(self.intent['operationId'], self.root)), record)
        self.assertEqual(self.bridge.plan_reads, 1)

    def test_same_original_retry_never_replans_even_after_new_backup_completes(self):
        original, first = self.reserve()
        self.bridge.value = plan(parent='increment-2')
        returned, repeated_first = self.reserve()
        self.assertTrue(first)
        self.assertFalse(repeated_first)
        self.assertEqual(returned, original)
        self.assertEqual(self.bridge.plan_reads, 1)

    def test_changed_confirmed_plan_is_rejected_without_reservation(self):
        self.bridge.value = plan(parent='increment-2')
        with self.assertRaisesRegex(adapter.Refused, 'INCREMENTAL_PLAN_CHANGED') as caught:
            self.reserve()
        self.assertFalse(entry.record_path(self.intent['operationId'], self.root).exists())
        self.assertEqual(getattr(caught.exception, 'not_accepted', None), dict(
            accepted=False, operationId=self.intent['operationId'], applicationId=APP))

    def test_baseline_required_records_actual_full_and_reason(self):
        self.bridge.value = plan('BASELINE_REQUIRED', reason='NO_SUCCESSFUL_FULL_BASELINE')
        self.intent['planDigest'] = self.bridge.value['planDigest']
        record, first = self.reserve()
        self.assertTrue(first)
        self.assertEqual(record['request']['action'], 'FULL')
        self.assertIsNone(record['request']['parentChainRef'])
        self.assertEqual(record['spugTaskId'], 1)
        self.assertEqual(record['automaticIncrementalPlan']['reasonCode'], 'NO_SUCCESSFUL_FULL_BASELINE')

    def test_blocked_plan_cannot_be_silently_changed_to_full(self):
        self.bridge.value = plan('BLOCKED', reason='INCREMENTAL_CHAIN_FORKED')
        self.intent['planDigest'] = self.bridge.value['planDigest']
        with self.assertRaisesRegex(adapter.Refused, 'INCREMENTAL_CHAIN_FORKED'):
            self.reserve()
        self.assertFalse(entry.record_path(self.intent['operationId'], self.root).exists())

    def test_operation_id_cannot_be_reused_for_another_confirmed_plan(self):
        record, _ = self.reserve()
        changed = dict(self.intent, planDigest='c' * 64)
        with self.assertRaisesRegex(adapter.Refused, 'OPERATION_ID_REQUEST_REUSE_REJECTED') as caught:
            self.reserve(changed)
        self.assertFalse(hasattr(caught.exception, 'not_accepted'))
        self.assertEqual(adapter.read_json(entry.record_path(self.intent['operationId'], self.root)), record)

    def test_pending_original_prevents_new_id_submission(self):
        record, _ = self.reserve()
        with patch.object(adapter, 'RECORDS', Path(self.temporary.name) / 'journal'):
            with self.assertRaisesRegex(adapter.Refused, 'ORIGINAL_OPERATION_STILL_UNRESOLVED'):
                self.reserve(dict(self.intent, operationId='automatic-operation-2'))
        self.assertEqual(len(list(self.root.glob('*.json'))), 1)

    def test_other_source_plan_is_rejected(self):
        self.bridge.value['sourceConfigRef'] = 'other-source'
        with self.assertRaisesRegex(adapter.Refused, 'INCREMENTAL_PLAN_SOURCE_MISMATCH'):
            self.reserve()

    def test_public_record_preserves_automatic_plan_for_reopened_page(self):
        record, _ = self.reserve()
        public = entry.public_record(record)
        self.assertEqual(public['automaticIncrementalPlan'], self.bridge.value)
        self.assertNotIn('automaticIncrementalIntent', public)

    def test_plan_digest_cannot_hide_changed_parent(self):
        self.bridge.value['parentChainRef'] = 'increment-2'
        with self.assertRaisesRegex(adapter.Refused, 'INCREMENTAL_PLAN_DIGEST_INVALID'):
            self.reserve()


if __name__ == '__main__':
    unittest.main()
