"""Pure acceptance of captured, real activation records; no simulated servers."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import unittest
import tempfile

import main_program_spug_publication as publication


TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
NAMES = ('source-only-finalize-r2.result.private.json',
         'source-request-owner-r5-activate.result.private.json',
         'source-request-owner-r6-activate.result.private.json')
BASE_PIN = dict(path=str(PRIVATE / 'source-upgrade-base-installation-20261111-r2.private.json'),
    bytes=3691660, sha256='71fec45d77f1efad18fbbd315a21f270d3c647e685d1b4d18d24f790acd1ecb2')


def subject():
    return importlib.import_module('main_program_source_control_activated')


def seal(proof):
    """For negative pure-parser tests only; never writes an original receipt."""
    proof['activationReceiptPin'] = subject().byte_pin(
        proof['activationReceiptPin']['path'], publication.canonical(
            {key: value for key, value in proof.items() if key != 'activationReceiptPin'}))


class CapturedActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(publication.verify_bytes(BASE_PIN))
        cls.steps = []
        cls.original_pins = [BASE_PIN, publication.file_pin(
            TASK / 'automatic-main-r7-20261110-i1-ui-submission.json')]
        for name in NAMES:
            pin = publication.file_pin(PRIVATE / name)
            proof = json.loads(publication.verify_bytes(pin))
            build = json.loads((TASK / proof['buildPin']['file']).read_bytes())
            cls.steps.append(dict(proof=proof, build=build))
            cls.original_pins.append(pin)

    def test_actual_three_activations_replace_source_and_keep_targets_and_spug(self):
        before = deepcopy(self.base)
        result = subject().verify_source_activations(self.base, self.steps)
        self.assertEqual(result['status'], 'ACTIVATED')
        self.assertTrue(result['installationVerified'])
        self.assertFalse(result['runtimeVerified'])
        self.assertEqual(result['baseInstallation'], before)
        self.assertEqual(self.base, before)
        rows = result['effectiveControllersByHost']
        self.assertEqual(rows['57'][0], self.steps[-1]['proof']['currentController'])
        self.assertEqual(rows['57'][0]['pid'], 25028)
        for host in ('57', '58', '59'):
            self.assertEqual(rows[host][-1], before['generation']['controllersByHost'][host][-1])
            self.assertEqual(result['controllerBuildBindings'][host]['target']['buildPin'],
                             before['generation']['generation']['buildPin'])
        self.assertEqual(result['controllerBuildBindings']['57']['source']['sourceCommit'],
                         '6968b58771c9d758290eabce176f18c456012d49')
        for pin in self.original_pins:
            publication.verify_bytes(pin)

    def test_missing_reordered_or_repeated_activation_rejected(self):
        for indices in ((), (1, 2), (0, 2), (0, 2, 1), (0, 1, 1, 2)):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                subject().verify_source_activations(self.base, [self.steps[i] for i in indices])

    def test_receipt_canonical_bytes_are_required(self):
        steps = deepcopy(self.steps)
        steps[-1]['proof']['observedAt'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'ACTIVATED_SOURCE_RECEIPT_BYTES'):
            subject().verify_source_activations(self.base, steps)

    def test_invalid_semantics_rejected_even_with_self_consistent_receipt(self):
        for case in ('status', 'extra', 'previous', 'previous-pin', 'base', 'role',
                     'pid', 'epoch', 'query', 'dispatch', 'reload', 'lock', 'created',
                     'dropin', 'package', 'target', 'container', 'mount', 'guard'):
            with self.subTest(case=case):
                steps = deepcopy(self.steps); proof = steps[-1]['proof']
                if case == 'status': proof['status'] = 'BOUND'
                elif case == 'extra': proof['runtimeVerified'] = True
                elif case == 'previous': proof['previousController']['pid'] += 1
                elif case == 'previous-pin': proof['previousControllerPin']['sha256'] = '0' * 64
                elif case == 'base': proof['baseSelectionPin']['sha256'] = '0' * 64
                elif case == 'role': proof['currentController']['role'] = 'target'
                elif case == 'pid': proof['currentController']['pid'] = None
                elif case == 'epoch': proof['sourceEpoch']['epochId'] = '0' * 64
                elif case == 'query': proof['originalI1QueryCount'] = 1
                elif case == 'dispatch': proof['backupDispatched'] = True
                elif case == 'reload': proof['targetControlReloaded'] = True
                elif case == 'lock': proof['physicalSourceLockHeld'] = False
                elif case == 'created': proof['createdPins'].pop(14)
                elif case == 'dropin': proof['currentController']['dropinPin']['sha256'] = '0' * 64
                elif case == 'package': proof['after']['packages'][0]['sha256'] = '0' * 64
                elif case == 'target': proof['after']['controllers'][1]['pid'] += 1
                elif case == 'container': proof['after']['containers'] = {}
                elif case == 'mount': proof['after']['mountinfoSha256'] = '0' * 64
                else: proof['after']['historyGuard']['LimitNOFILE'] = '1'
                seal(proof)
                with self.assertRaises(ValueError):
                    subject().verify_source_activations(self.base, steps)

    def test_changed_actual_package_build_is_rejected(self):
        steps = deepcopy(self.steps)
        steps[-1]['build']['packageSha256'] = '0' * 64
        with self.assertRaises(ValueError):
            subject().verify_source_activations(self.base, steps)

    def test_old_bound_schema_cannot_enter_activated_loader(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'bound.json').write_bytes(publication.canonical(dict(
                schemaVersion='TaskMainProgramSourceControlSelection/v1',
                baseSelectionPin=self.base['selectionPin'], sourceSuccessorReceiptPin={})))
            with self.assertRaisesRegex(ValueError, 'ACTIVATED_SOURCE_SELECTION'):
                subject().load_activated_installation(folder, PRIVATE, selection_file='bound.json')


if __name__ == '__main__':
    unittest.main()
