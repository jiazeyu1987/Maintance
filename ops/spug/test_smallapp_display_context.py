"""Local reservation/display contracts; no remote backup or restore."""
import tempfile
import unittest
from unittest.mock import patch

import smallapp_adapter as adapter
import smallapp_entry as entry
import smallapp_simple as simple
from smallapp_checks import full


class DisplayContext(unittest.TestCase):
    def binding(self):
        return dict(applicationId='app', product='smallapp', server='source-host', mode='fast',
                    targetServers={'target-host': 'fresh'},
                    overwriteTargetServers={'target-host': 'replace'}, password='never-public')

    def test_snapshot_is_whitelisted_and_rejects_ambiguous_target_semantics(self):
        binding = self.binding()
        request = dict(full(), action='RESTORE', targetConfigRef='replace', recoveryPointRef='point')
        with patch.object(simple, 'configuration', return_value={'bindings': [binding]}):
            value = simple.display_context(request, 'app')
            self.assertEqual(value, dict(server='source-host', mode='fast', restoreMode='replace'))
            binding['targetServers']['target-host'] = 'replace'
            with self.assertRaisesRegex(adapter.Refused, 'DISPLAY_TARGET_SEMANTICS_AMBIGUOUS'):
                simple.display_context(request, 'app')

    def test_unknown_binding_is_explicitly_unrecorded_for_advanced_entry(self):
        with patch.object(simple, 'configuration', return_value={'bindings': []}):
            self.assertIsNone(simple.display_context(full(), 'advanced-app'))

    def test_reservation_retains_snapshot_on_repeat_and_public_projection(self):
        from types import SimpleNamespace
        bridge = SimpleNamespace(fingerprint='fingerprint')
        app = dict(applicationId='app', registrationSha256='a' * 64)
        snapshot = dict(server='source-host', mode='fast', restoreMode=None)
        with tempfile.TemporaryDirectory() as root, patch.object(entry, 'admit_selection', return_value=app):
            first, created = entry.reserve(full(), {'tasks': {'FULL': 1}}, bridge, 7, root,
                                          display_context_factory=lambda request, app_id: snapshot)
            self.assertTrue(created)
            second, created = entry.reserve(full(), {}, bridge, 7, root,
                                           display_context_factory=lambda *args: self.fail('recomputed history'))
            self.assertFalse(created)
            self.assertEqual(second['displayContext'], snapshot)
            self.assertEqual(entry.public_record(second)['displayContext'], snapshot)
            self.assertNotIn('bridgeFingerprint', entry.public_record(second))

    def test_snapshot_failure_does_not_publish_a_dispatchable_reservation(self):
        from pathlib import Path
        from types import SimpleNamespace
        app = dict(applicationId='app', registrationSha256='a' * 64)
        def refuse(*args):
            raise adapter.Refused('DISPLAY_TARGET_SEMANTICS_AMBIGUOUS')
        with tempfile.TemporaryDirectory() as root, patch.object(entry, 'admit_selection', return_value=app):
            with self.assertRaisesRegex(adapter.Refused, 'DISPLAY_TARGET_SEMANTICS_AMBIGUOUS'):
                entry.reserve(full(), {'tasks': {'FULL': 1}}, SimpleNamespace(fingerprint='f'), 7, root,
                              display_context_factory=refuse)
            self.assertEqual(list(Path(root).glob('*.json')), [])


if __name__ == '__main__':
    unittest.main()
