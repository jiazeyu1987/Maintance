"""Offline evidence-contract tests; real task records, no backup or cleanup."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TASK = Path(__file__).resolve().parent


class CloseoutEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('closeout_contracts', TASK / 'closeout_contracts.py')
        cls.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.api)

    def read(self, name):
        return json.loads((TASK / name).read_text(encoding='utf-8'))

    def test_real_58_observation_selected_without_overwriting_failures(self):
        request = self.read('restore-58-r4-ui-submission.json')['request']
        result = self.api.terminal_observation(TASK, 'restore-58-r4', request)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['operationId'], request['operationId'])

    def test_real_59_third_observation_preserves_both_actual_failures(self):
        request = self.read('restore-59-ui-submission.json')['request']
        result = self.api.terminal_observation(TASK, 'restore-59', request)
        self.assertEqual(result['spugHistoryId'], 372)
        self.assertEqual(result['observation'], 'r3')

    def test_actual_catalogue_http_only_observation_is_not_complete_catalogue_acceptance(self):
        observed = self.read('restore-59-ui-readonly-terminal-r3.json')
        installed = self.read('catalogue-identity-installation.json')
        with self.assertRaises(AssertionError):
            self.api.validate_catalogue_observation(observed, installed)

    def test_real_first_catalogue_failure_cannot_be_selected_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            name = 'catalogue-identity-readonly-verification.json'
            (target / name).write_bytes((TASK / name).read_bytes())
            pin = self.api.file_pin(target, name)
            value = dict(schemaVersion='TaskCatalogueReadonlySelection/v1',failed=[],selectedPin=pin)
            (target / 'catalogue-identity-readonly-selection.json').write_text(json.dumps(value),encoding='utf-8')
            with self.assertRaises(AssertionError):
                self.api.catalogue_observation_selection(target, pin)

    def test_original_367_source_health_cannot_stand_for_new_automatic_point(self):
        original = self.read('source-global-state-restored.json')
        source = self.read('automatic-control-installation-57.json')
        receipt = self.read('automatic-full-ui-submission.json')
        with self.assertRaises(AssertionError):
            self.api.validate_source_restoration(TASK, 'FULL', original, source, receipt['request'], None)

    def test_original_failed_observation_tampering_and_omission_are_rejected(self):
        names = ['restore-58-r4-terminal-observation-selection.json', 'restore-58-r4-terminal-failed-observations.json',
                 'restore-58-r4-ui-readonly-terminal.json', 'restore-58-r4-ui-readonly-terminal-r2.json',
                 'restore-58-r4-ui-readonly-terminal-r3.json', 'restore-58-r4-ui-readonly-terminal-r4.json']
        request = self.read('restore-58-r4-ui-submission.json')['request']
        for mode in ('tamper', 'omit', 'different-request', 'duplicate'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                tested_request = copy.deepcopy(request)
                target = Path(directory)
                for name in names:
                    (target / name).write_bytes((TASK / name).read_bytes())
                if mode == 'tamper':
                    with (target / names[2]).open('ab') as output:
                        output.write(b' ')
                elif mode == 'different-request':
                    tested_request['operationId'] = 'another-operation'
                else:
                    retained = self.read(names[1])
                    retained['failed'] = retained['failed'][1:] if mode == 'omit' else retained['failed'] * 2
                    (target / names[1]).write_text(json.dumps(retained), encoding='utf-8')
                with self.assertRaises((AssertionError, ValueError)):
                    self.api.terminal_observation(target, 'restore-58-r4', tested_request)

    def test_59_existing_failed_terminal_cannot_be_used_as_success(self):
        request = self.read('restore-59-ui-submission.json')['request']
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ('restore-59-ui-readonly-terminal.json', 'restore-59-ui-readonly-terminal-r2.json'):
                (target / name).write_bytes((TASK / name).read_bytes())
            with self.assertRaises((AssertionError, FileNotFoundError)):
                self.api.terminal_observation(target, 'restore-59', request)

    def test_real_new_130_member_build_can_be_explicitly_registered(self):
        report = self.read('release-build-0d44578.json')
        entry = self.api.build_entry(TASK, self.api.PRIVATE, 'release-build-0d44578.json')
        self.assertEqual(entry['targetCommit'], report['targetCommit'])
        self.assertEqual(entry['fileCount'], 130)
        self.assertEqual(entry['generation'], '0d44578')

    def test_real_source_and_spug_installation_generation_must_match(self):
        source = self.read('automatic-control-installation-57.json')
        spug = self.read('automatic-spug-installation-0d44578.json')
        self.api.validate_source_spug(TASK, source, spug)
        changed = copy.deepcopy(spug)
        changed['sourceCommit'] = 'f' * 40
        with self.assertRaises(AssertionError):
            self.api.validate_source_spug(TASK, source, changed)
        changed = copy.deepcopy(source)
        changed['allOriginalContainersUnchanged'] = False
        with self.assertRaises(AssertionError):
            self.api.validate_source_spug(TASK, changed, spug)

    def test_unfinished_real_full_cannot_be_claimed_as_completed_three_point_chain(self):
        # The real accepted FULL exists, but no successful audit/terminal chain exists yet.
        # Contract verification must stop before touching any remote resource.
        receipt = self.read('automatic-full-ui-submission.json')
        self.assertEqual(receipt['request']['action'], 'FULL')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / 'automatic-full-ui-submission.json').write_bytes((TASK / 'automatic-full-ui-submission.json').read_bytes())
            with self.assertRaises((AssertionError, FileNotFoundError)):
                self.api.automatic_chain(target)

    def test_retained_history_requires_exact_job_identity_not_just_count(self):
        spec = importlib.util.spec_from_file_location('catalogue_current', TASK / 'catalogue_current_verification.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = [{'id': 'original-a', 'status': 'failed'}, {'id': 'original-b', 'status': 'success'}]
        module.require_original_jobs(old, copy.deepcopy(old))
        for current in ([old[0]], [old[0], dict(old[1], status='failed')], [old[0], {'id': 'replacement', 'status': 'success'}]):
            with self.assertRaises(AssertionError):
                module.require_original_jobs(old, current)

    def test_build_path_escape_and_duplicate_generation_refused(self):
        entry = self.api.build_entry(TASK, self.api.PRIVATE, 'release-build-0d44578.json')
        for mode in ('escape', 'duplicate', 'commit', 'package'):
            manifest = {'schemaVersion': 'TaskOwnedBuilds/v1', 'taskId': TASK.name, 'builds': [copy.deepcopy(entry)]}
            if mode == 'escape':
                manifest['builds'][0]['worktree'] = 'C:/Spug/runtime/private/other-task/release-0d44578'
            elif mode == 'duplicate':
                manifest['builds'].append(copy.deepcopy(entry))
            elif mode == 'commit':
                manifest['builds'][0]['targetCommit'] = 'f' * 40
            else:
                manifest['builds'][0]['package'] = 'C:/Spug/runtime/private/other-task/package.tgz'
            with self.assertRaises((AssertionError, ValueError)):
                self.api.validate_build_manifest(TASK, self.api.PRIVATE, manifest)


if __name__ == '__main__':
    unittest.main()
