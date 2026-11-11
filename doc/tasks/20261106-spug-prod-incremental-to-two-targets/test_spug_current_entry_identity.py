"""Current Spug process proof; the live case only reads this task's container."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import prepare_main_program_ui_preflight as ui


PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')


class CurrentEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((PRIVATE / 'activated-source-formal-load-r1.private.json').read_bytes())['baseInstallation']
        cls.guard = cls.base['spugRuntime']['guard']
        cls.old = cls.guard['entryIdentity']
        # Captured real current scan, no fabricated runtime success.
        scan = json.loads((PRIVATE / 'spug-current-pid-readonly-r1.native.private.json').read_bytes())
        cls.current = json.loads(scan['stdout'])['processes'][0]

    def candidate(self):
        return dict(pid=self.current['pid'], parentPid=self.current['parentPid'],
            startTicks=self.current['startTicks'], argv=self.old['argv'], cwd=self.old['cwd'],
            executable=self.old['executable'], environmentSha256=self.guard['entryEnvironmentSha256'])

    def test_same_installation_current_process_is_admitted_without_rewriting_old_identity(self):
        before = deepcopy(self.guard)
        row = self.candidate()
        self.assertNotEqual(row['pid'], self.old['pid'])
        result = ui.validate_spug_current_entry(self.guard, [row])
        self.assertEqual(result, row)
        self.assertEqual(self.guard, before)

    def test_missing_ambiguous_or_changed_identity_is_rejected(self):
        for case in ('missing', 'duplicate', 'argv', 'cwd', 'executable', 'environment', 'parent', 'pid', 'start'):
            with self.subTest(case=case):
                row = self.candidate(); rows = [row]
                if case == 'missing': rows = []
                elif case == 'duplicate': rows.append(deepcopy(row))
                elif case == 'argv': row['argv'] = row['argv'] + ['other']
                elif case == 'cwd': row['cwd'] += '-other'
                elif case == 'executable': row['executable'] += '-other'
                elif case == 'environment': row['environmentSha256'] = '0' * 64
                elif case == 'parent': row['parentPid'] += 1
                elif case == 'pid': row['pid'] = False
                else: row['startTicks'] = '-1'
                with self.assertRaises((ValueError, AssertionError)):
                    ui.validate_spug_current_entry(self.guard, rows)

    def test_actual_container_current_process_and_all_original_bytes(self):
        result, build = ui.spug_observation(self.base, self.base['selection'])
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['fileCount'], 14)
        self.assertEqual(result['configurationCount'], 7)
        self.assertEqual(result['entryPid'], self.current['pid'])
        self.assertEqual(result['previousEntryPid'], self.old['pid'])
        self.assertTrue(result['processRestarted'])
        self.assertEqual(result['entryIdentity']['argv'], self.old['argv'])


if __name__ == '__main__':
    unittest.main()
