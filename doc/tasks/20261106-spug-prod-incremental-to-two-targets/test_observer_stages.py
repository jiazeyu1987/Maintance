"""Regression against actual mixed full/incremental timings captured from History368."""
import json
import unittest

from common import TASK
from observe_restore import stage_states


class RecordedStageTests(unittest.TestCase):
    def test_full_completion_does_not_mask_current_incremental_import(self):
        evidence = json.loads((TASK / 'observer-real-timings-regression-input.json').read_text(encoding='utf-8'))
        states = stage_states(evidence['nativeTimings'])
        self.assertEqual(states['database-000/sql-import'], 'DONE')
        self.assertEqual(states['database-001/sql-import'], 'RUNNING')
        self.assertEqual(states['database-001/sql-expand'], 'DONE')
        self.assertEqual(states['operation/restore-admission'], 'DONE')

    def test_record_order_does_not_change_recorded_result(self):
        evidence = json.loads((TASK / 'observer-real-timings-regression-input.json').read_text(encoding='utf-8'))
        timings = evidence['nativeTimings']
        self.assertEqual(stage_states(timings), stage_states(list(reversed(timings))))


if __name__ == '__main__':
    unittest.main()
