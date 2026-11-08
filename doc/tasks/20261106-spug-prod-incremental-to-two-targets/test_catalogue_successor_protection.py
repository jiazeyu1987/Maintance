"""Unit contract for an explicitly installed successor; no remote operations."""
import copy
import json
from pathlib import Path
import unittest
import catalogue_current_verification as api

TASK = Path(__file__).resolve().parent


class CatalogueSuccessorProtectionTests(unittest.TestCase):
    def setUp(self):
        self.installed = json.loads((TASK / 'catalogue-identity-installation.json').read_text(encoding='utf-8'))
        self.source = json.loads((TASK / 'automatic-source-control-installation-0dc7429.json').read_text(encoding='utf-8'))
        self.actual = copy.deepcopy(self.installed['protectedAfter'])
        self.actual['source57ServicePid'] = self.source['controllers'][0]['pid']

    def test_exact_installed_predecessor_to_successor_is_required(self):
        api.require_current_protected_processes(self.installed, self.source, self.actual)

    def test_changed_previous_pid_or_installation_status_rejected(self):
        for field in ('previousPid', 'status'):
            source = copy.deepcopy(self.source)
            if field == 'previousPid':
                source['controllers'][0][field] += 1
            else:
                source[field] = 'FAILED'
            with self.subTest(field=field), self.assertRaises(AssertionError):
                api.require_current_protected_processes(self.installed, source, self.actual)

    def test_other_current_process_or_old_source_pid_rejected(self):
        for field in ('source57ServicePid', 'smallappEntryPid'):
            actual = copy.deepcopy(self.actual)
            actual[field] += 1
            with self.subTest(field=field), self.assertRaises(AssertionError):
                api.require_current_protected_processes(self.installed, self.source, actual)

    def test_historical_protection_or_unrelated_container_change_rejected(self):
        installed = copy.deepcopy(self.installed)
        installed['protectedBefore']['smallappEntryPid'] += 1
        with self.assertRaises(AssertionError):
            api.require_current_protected_processes(installed, self.source, self.actual)
        self.actual['unrelated18081'][0]['state'] = 'exited'
        with self.assertRaises(AssertionError):
            api.require_current_protected_processes(self.installed, self.source, self.actual)
