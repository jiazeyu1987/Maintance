"""Local on-disk entry/simple registration contracts; no bridge or execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import smallapp_adapter as adapter
import smallapp_entry as entry
import smallapp_simple as simple


class PreservationRegistration(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.entry_path = Path(folder) / 'entry.json'
        self.simple_path = Path(folder) / 'simple.json'
        self.enterContext(patch.object(entry, 'SETTINGS', self.entry_path))
        self.enterContext(patch.object(simple, 'CONFIG', self.simple_path))

        self.addresses = ('192.0.2.57', '192.0.2.58', '192.0.2.59')
        self.replacements = dict(zip(self.addresses, ('replace-57', 'replace-58', 'replace-59')))
        self.ordinary = dict(applicationId='ordinary', displayName='普通来源', sourceConfigRef='ordinary-source',
                             targetConfigRefs=['ordinary-target'], engineSelectionRef='ordinary-engine',
                             registrationSha256='a' * 64)
        self.preservation = dict(applicationId='preservation', displayName='覆盖前自动保全',
                                 sourceConfigRef='preservation-source', targetConfigRefs=list(self.replacements.values()),
                                 engineSelectionRef='preservation-engine', registrationSha256='b' * 64,
                                 sourceKind='TARGET_PRE_RESTORE')
        self.entry_value = dict(applications=[self.ordinary, self.preservation],
                                tasks=dict(FULL=1, INCREMENTAL=2, RESTORE=3), initialOperationIds={},
                                registrationVersions=dict(ordinary='release-v1', preservation=None))
        self.ordinary_binding = dict(applicationId='ordinary', product='intruoyi', server=self.addresses[0],
                                     mode='safe', selectable=True, targetServers={}, overwriteTargetServers={})
        self.preservation_binding = dict(self.ordinary_binding, applicationId='preservation', selectable=False,
                                         overwriteTargetServers=self.replacements, progressRoot='/private-progress',
                                         sshTransport={'host': 'private-transport'},
                                         restoreProgressBindings={'private-route': 'private-value'})
        self.simple_value = dict(nas='registered',
                                 servers=[dict(address=address, name=address) for address in self.addresses],
                                 bindings=[self.ordinary_binding, self.preservation_binding],
                                 catalogueRestoreBindings={'ordinary-point': 'ordinary'},
                                 preservationRestoreBindings={'preservation-source': 'preservation'})
        self.write(self.entry_path, self.entry_value)
        self.write(self.simple_path, self.simple_value)

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def test_entry_accepts_tagged_preservation_and_exact_legacy_registration(self):
        self.assertEqual(entry.settings(self.entry_path), self.entry_value)
        self.assertNotIn('sourceKind', entry.settings(self.entry_path)['applications'][0])

    def test_entry_rejects_unknown_tag_and_invalid_required_preservation_fields(self):
        cases = [
            ({'sourceKind': 'UNRECOGNIZED'}, 'W08_DISPLAY_PROJECTION_INVALID'),
            ({'sourceKind': None}, 'W08_DISPLAY_PROJECTION_INVALID'),
            ({'privateField': 'outside-contract'}, 'W08_DISPLAY_PROJECTION_INVALID'),
            ({'sourceConfigRef': None}, 'W08_SOURCE_INVALID'),
            ({'engineSelectionRef': None}, 'W08_ENGINE_INVALID'),
            ({'targetConfigRefs': ['one-target']}, 'W08_TARGETS_INVALID'),
            ({'sourceConfigRef': self.ordinary['sourceConfigRef']}, 'W08_DUPLICATE_SOURCE'),
        ]
        for changes, code in cases:
            with self.subTest(changes=changes):
                config = dict(self.entry_value, applications=[self.ordinary, dict(self.preservation, **changes)])
                self.write(self.entry_path, config)
                with self.assertRaisesRegex(adapter.Refused, '^' + code + '$'):
                    entry.settings(self.entry_path)

    def test_tagged_source_cannot_enter_ordinary_catalogue_plan_or_admission(self):
        with patch.object(adapter, 'HttpBridge', side_effect=AssertionError('bridge was opened')):
            with self.assertRaisesRegex(adapter.Refused, '^PRESERVATION_SELECTION_REQUIRED$'):
                entry.application_catalogue(self.entry_value, 'preservation')
            with self.assertRaisesRegex(adapter.Refused, '^PRESERVATION_SELECTION_REQUIRED$'):
                entry.automatic_incremental_plan(self.entry_value, 'preservation')
        request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='original-request-1',
                       action='FULL', sourceConfigRef='preservation-source', parentChainRef=None,
                       recoveryPointRef=None, targetConfigRef=None)
        # No bridge may be consulted to admit a preservation source on the legacy path.
        for changes in ({}, {'action': 'INCREMENTAL', 'parentChainRef': 'point'},
                        {'action': 'RESTORE', 'recoveryPointRef': 'point', 'targetConfigRef': 'replace-57'}):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(adapter.Refused, '^PRESERVATION_SELECTION_REQUIRED$'):
                    entry.admit_selection(dict(request, **changes), self.entry_value, None)

    def test_ordinary_choice_never_validates_tagged_preservation_application(self):
        def item(app):
            return {key: app[key] for key in ('applicationId', 'sourceConfigRef', 'engineSelectionRef')} | dict(
                fullReady=True, fullErrorCode=None, parentChainRefs=[], recoveryPointRefs=[],
                freshTargetConfigRefs=[], historyErrorCode=None)

        ordinary = item(self.ordinary)
        self.assertEqual(entry.validated_selections(dict(observedAt=entry.now(), applications=[ordinary]),
                                                    self.entry_value), {'ordinary': ordinary})
        with self.assertRaisesRegex(adapter.Refused, '^PRESERVATION_SELECTION_REQUIRED$'):
            entry.validated_selections(dict(observedAt=entry.now(), applications=[item(self.preservation)]),
                                       self.entry_value)

    def test_simple_public_mapping_preserves_existing_choices_and_hides_private_binding_data(self):
        value = simple.public_configuration()
        self.assertEqual(value['preservationRestoreBindings'], {'preservation-source': 'preservation'})
        self.assertEqual(value['catalogueRestoreBindings'], {'ordinary-point': 'ordinary'})
        self.assertEqual([row for row in value['bindings'] if row['selectable']], [self.ordinary_binding])
        self.assertEqual(value['bindings'][1]['overwriteTargetServers'], self.replacements)
        self.assertEqual(set(value['bindings'][1]), set(self.ordinary_binding))

    def test_legacy_public_mapping_does_not_require_entry_settings(self):
        self.entry_path.unlink()
        self.write(self.simple_path, dict(nas='registered', servers=list(self.addresses),
                                          bindings=[self.ordinary_binding],
                                          catalogueRestoreBindings={'ordinary-point': 'ordinary'}))
        value = simple.public_configuration()
        self.assertNotIn('preservationRestoreBindings', value)
        self.assertEqual(value['catalogueRestoreBindings'], {'ordinary-point': 'ordinary'})

    def test_simple_rejects_invalid_maps_and_mismatched_entry_identity(self):
        for routes in ([], {'preservation-source': 'not-registered'}, {'wrong-source': 'preservation'},
                       {'ordinary-source': 'ordinary'}, {'../invalid': 'preservation'},
                       {'preservation-source': 'preservation', 'another-source': 'preservation'},
                       {f'source-{i}': f'app-{i}' for i in range(33)}):
            with self.subTest(routes=routes):
                self.write(self.simple_path, dict(self.simple_value, preservationRestoreBindings=routes))
                with self.assertRaisesRegex(adapter.Refused, '^SIMPLE_PRESERVATION_RESTORE_BINDING_INVALID$'):
                    simple.public_configuration()

    def test_simple_rejects_conflicting_modes_ordinary_routes_and_target_maps(self):
        cases = [
            ({'mode': 'fast'}, {}),
            ({'selectable': True, 'product': 'distinct-product'}, {}),
            ({'server': 'unregistered-origin'}, {}),
            ({'overwriteTargetServers': dict(list(self.replacements.items())[:2])}, {}),
            ({'overwriteTargetServers': dict.fromkeys(self.addresses, 'replace-57')}, {}),
            ({'overwriteTargetServers': dict(self.replacements, **{self.addresses[0]: 'other-ref'})}, {}),
            ({'targetServers': {self.addresses[0]: 'replace-57'}}, {}),
            ({}, {'catalogueRestoreBindings': {'ordinary-point': 'preservation'}}),
        ]
        for binding_changes, config_changes in cases:
            with self.subTest(binding_changes=binding_changes, config_changes=config_changes):
                config = copy.deepcopy(self.simple_value)
                config['bindings'][1].update(binding_changes)
                config.update(config_changes)
                self.write(self.simple_path, config)
                with self.assertRaisesRegex(adapter.Refused, '^SIMPLE_PRESERVATION_RESTORE_BINDING_INVALID$'):
                    simple.public_configuration()

    def test_simple_mapping_requires_real_entry_settings(self):
        self.entry_path.unlink()
        with self.assertRaisesRegex(adapter.Refused, '^W08_DISPLAY_SETTINGS_REQUIRED$'):
            simple.public_configuration()


if __name__ == '__main__':
    unittest.main()
