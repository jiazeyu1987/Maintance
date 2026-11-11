"""Selection-context unit contract with captured actual installation materials."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import main_program_source_control_activated as activated
import prepare_main_program_ui_preflight as ui
import test_main_program_source_control_activated as captured

TASK = captured.TASK


class SourceContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        captured.CapturedActivationTests.setUpClass()
        cls.base = captured.CapturedActivationTests.base
        cls.actual = activated.verify_source_activations(cls.base, captured.CapturedActivationTests.steps)
        cls.actual['selection'] = json.loads((TASK / 'main-program-source-activated-6968b58-v2.json').read_bytes())
        cls.actual['inputPins'] = activated.unique_pins(cls.actual['inputPins'] + cls.base['inputPins'])

    def test_explicit_activation_uses_current_source_build_and_preserves_base(self):
        before = deepcopy(self.actual)
        result = ui.installation_context(self.actual, source_activation=True)
        row = self.actual['effectiveControllersByHost']['57'][0]
        self.assertEqual(result['sourceCommit'], row['sourceCommit'])
        self.assertEqual(result['buildPin'], row['buildPin'])
        self.assertEqual(result['build']['targetCommit'], row['sourceCommit'])
        self.assertEqual(result['rows'], self.actual['effectiveControllersByHost']['57'])
        self.assertEqual(result['base'], self.base)
        self.assertNotEqual(result['sourceCommit'], self.base['selection']['sourceCommit'])
        self.assertEqual(before, self.actual)

    def test_activation_needs_explicit_protocol(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_ACTIVATION'):
            ui.installation_context(self.actual)

    def test_legacy_does_not_enter_activation_protocol(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_ACTIVATION'):
            ui.installation_context(self.base, source_activation=True)

    def test_legacy_context_stays_on_original_source(self):
        result = ui.installation_context(self.base)
        self.assertEqual(result['sourceCommit'], self.base['selection']['sourceCommit'])
        self.assertEqual(result['build'], self.base['generation']['build'])

    def test_invalid_activation_identity_or_unbound_build_refused(self):
        for case in ('status', 'installation', 'runtime', 'commit', 'build-pin', 'role'):
            with self.subTest(case=case):
                value = deepcopy(self.actual)
                if case == 'status': value['status'] = 'BOUND'
                elif case == 'installation': value['installationVerified'] = False
                elif case == 'runtime': value['runtimeVerified'] = True
                elif case == 'commit': value['effectiveControllersByHost']['57'][0]['sourceCommit'] = '0' * 40
                elif case == 'build-pin': value['inputPins'] = []
                else: value['effectiveControllersByHost']['57'][0]['role'] = 'target'
                with self.assertRaises((ValueError, AssertionError)):
                    ui.installation_context(value, source_activation=True)


if __name__ == '__main__':
    unittest.main()
