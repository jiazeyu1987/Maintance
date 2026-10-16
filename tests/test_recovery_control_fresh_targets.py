"""Local pinned-config and reservation checks; no restore or server access."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / 'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_smallapp import Failure, canonical, persist, public_error

SOURCE = REPOSITORY / ('doc/tasks/20261010-backup-recovery-control-dev/'
    'entry-state-repair-20261015-r1/recovery_control_smallapp_native.py')
spec = importlib.util.spec_from_file_location('fresh_target_native', SOURCE)
native_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_module)


class FreshTargetChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        source_path = self.root / 'source-owner.json'
        persist(source_path, {'schemaVersion': 'RepositoryMinimumConfiguration/v1'})
        self.source_pin = executor.pin(source_path)
        self.config = dict(sourceConfigurations={'local-source': self.source_pin},
            restoreConfigurations={'local-source': {}})
        self.registered = dict(sourceConfigRef='local-source', allowedRestoreTargets=[])
        self.native = native_module.Native(self.source_pin)

    def target(self, reference):
        root = self.root / reference
        root.mkdir()
        # Only the selected local config/root is inspected. These declared
        # service settings are never executed or treated as restore evidence.
        target = dict(targetId=reference, sourceConfigRef='local-source', dataRoot=str(root),
            dataPaths=[str(root / 'data')], machineId='local-test', dockerEngineId='local-test',
            networkId='local-test', database='local_test', buckets=[], services=[],
            dockerPin=None, iptablesPin=None, redisClientPath=None, dataPolicy={},
            secrets={}, bucketProtection={}, application={})
        owner = dict(schemaVersion='RecoveryMinimalConfiguration/v1',
            sources={'local-source': {}}, targets={reference: target})
        owner_path = self.root / (reference + '.json')
        persist(owner_path, owner)
        self.config['restoreConfigurations']['local-source'][reference] = executor.pin(owner_path)
        self.registered['allowedRestoreTargets'].append(dict(configRef=reference,
            root=str(self.root / 'metadata-is-not-the-runtime-root')))
        return root, owner_path, owner

    def update(self, reference, path, owner):
        path.write_bytes(canonical(owner))
        self.config['restoreConfigurations']['local-source'][reference] = executor.pin(path)

    def choices(self):
        return self.native.fresh_target_config_refs(self.config, self.registered)

    def test_unused_target_survives_and_metadata_root_is_not_used(self):
        root, path, _ = self.target('unused-target')
        metadata = self.root / 'metadata-is-not-the-runtime-root'
        metadata.mkdir()
        marker = metadata / '.recovery-operation.json'
        marker.write_bytes(b'old metadata location')
        before = path.read_bytes(), marker.read_bytes(), tuple(root.iterdir())
        self.assertEqual(self.choices(), ['unused-target'])
        self.assertEqual((path.read_bytes(), marker.read_bytes(), tuple(root.iterdir())), before)

    def test_success_failure_unknown_and_malformed_reservations_remain_excluded(self):
        retained = {}
        for index, state in enumerate(('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN', None)):
            root, _, _ = self.target('used-target-' + str(index))
            marker = root / '.recovery-operation.json'
            raw = canonical(dict(operationId='earlier-operation-' + str(index), state=state)) if state else b'!'
            marker.write_bytes(raw)
            retained[marker] = raw
        self.target('unused-target')
        self.assertEqual(self.choices(), ['unused-target'])
        self.assertEqual({path: path.read_bytes() for path in retained}, retained)

    def test_actual_runtime_root_reservation_excludes_target_despite_fresh_metadata(self):
        root, _, _ = self.target('occupied-target')
        (root / '.recovery-operation.json').write_bytes(b'occupied')
        self.assertEqual(self.choices(), [])

    def test_directory_at_reservation_name_also_excludes_target(self):
        root, _, _ = self.target('occupied-target')
        marker = root / '.recovery-operation.json'
        marker.mkdir()
        self.assertEqual(self.choices(), [])
        self.assertTrue(marker.is_dir())

    def test_first_full_with_no_restore_configuration_has_no_target(self):
        self.config['restoreConfigurations'] = {}
        self.assertEqual(self.choices(), [])

    def test_registered_target_without_owner_configuration_is_not_recommended(self):
        self.registered['allowedRestoreTargets'].append(dict(configRef='not-configured'))
        self.assertEqual(self.choices(), [])

    def test_malformed_restore_mapping_raises_instead_of_becoming_empty(self):
        self.config['restoreConfigurations']['local-source'] = []
        with self.assertRaisesRegex(Failure, '^NEW_TARGET_CONFIGURATION_REQUIRED$'):
            self.choices()

    def test_changed_pinned_owner_configuration_is_reported(self):
        _, path, owner = self.target('unused-target')
        path.write_bytes(canonical(dict(owner, changed=True)))
        with self.assertRaisesRegex(RuntimeError, '^NATIVE_PIN_CHANGED$'):
            self.choices()

    def test_invalid_owner_schema_is_reported(self):
        _, path, owner = self.target('unused-target')
        owner['schemaVersion'] = 'UnrelatedConfiguration/v1'
        self.update('unused-target', path, owner)
        with self.assertRaisesRegex(Failure, '^ORIGINAL_OWNER_CONFIGURATION_INVALID$'):
            self.choices()

    def test_target_missing_from_actual_owner_configuration_is_reported(self):
        _, path, owner = self.target('unused-target')
        owner['targets'] = {}
        self.update('unused-target', path, owner)
        with self.assertRaisesRegex(Failure, '^NEW_TARGET_REFERENCE_REQUIRED$'):
            self.choices()

    def test_target_bound_to_different_source_is_reported(self):
        _, path, owner = self.target('unused-target')
        owner['targets']['unused-target']['sourceConfigRef'] = 'different-source'
        self.update('unused-target', path, owner)
        with self.assertRaisesRegex(Failure, '^TARGET_SOURCE_MISMATCH$'):
            self.choices()

    def test_missing_root_propagates_through_existing_public_error_contract(self):
        _, path, owner = self.target('unused-target')
        owner['targets']['unused-target']['dataRoot'] = str(self.root / 'missing-root')
        self.update('unused-target', path, owner)
        with self.assertRaises(FileNotFoundError) as caught:
            self.choices()
        self.assertEqual(public_error(caught.exception), 'SMALLAPP_FILENOTFOUNDERROR')

    def test_relative_root_is_rejected_before_inspecting_current_directory(self):
        _, path, owner = self.target('unused-target')
        owner['targets']['unused-target']['dataRoot'] = 'relative-root'
        self.update('unused-target', path, owner)
        with self.assertRaisesRegex(Failure, '^TARGET_DATA_ROOT_INVALID$'):
            self.choices()


if __name__ == '__main__':
    unittest.main(verbosity=2)
