"""Explicit archived role bindings, immutable input bytes and MAIN admission."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
sys.path.insert(0, str(ROOT / 'scripts/tests'))
from recovery_engine import RecoveryError, pin
from recovery_archive_versions import resolve_archive_images
import test_main_restore_target as main_tests
import recovery_main_target as main


BACKEND = 'sha256:' + 'a' * 64
FRONTEND = 'sha256:' + 'b' * 64
UNSET = object()


class ArchiveVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bindings = [dict(role='backend', versionPath=['images', 'old-backend']),
                         dict(role='frontend', versionPath=['images', 'old-frontend'])]
        self.reference = self.document('original.json',
            dict(images={'old-backend': BACKEND, 'old-frontend': FRONTEND}))

    def document(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return pin(path)

    def resolve(self, pins=UNSET, bindings=UNSET, **kwargs):
        return resolve_archive_images([self.reference] if pins is UNSET else pins,
            self.bindings if bindings is UNSET else bindings, **kwargs)

    def test_explicit_historical_names_return_bound_images_and_original_pins(self):
        self.assertEqual({binding['role']: dict(imageId=image,
            versionPin=self.reference, versionPath=binding['versionPath'])
            for binding, image in zip(self.bindings, (BACKEND, FRONTEND))}, self.resolve())

    def test_roles_can_come_from_separate_original_documents(self):
        backend = self.document('backend.json', dict(images={'old-backend': BACKEND}))
        frontend = self.document('frontend.json', dict(images={'old-frontend': FRONTEND}))
        result = self.resolve([backend, frontend])
        self.assertEqual(backend, result['backend']['versionPin'])
        self.assertEqual(frontend, result['frontend']['versionPin'])

    def test_array_path_uses_explicit_nonnegative_integer(self):
        reference = self.document('array.json', dict(images=[BACKEND, FRONTEND]))
        bindings = [dict(role='backend', versionPath=['images', 0]),
                    dict(role='frontend', versionPath=['images', 1])]
        result = self.resolve([reference], bindings)
        self.assertEqual(BACKEND, result['backend']['imageId'])
        self.assertEqual(FRONTEND, result['frontend']['imageId'])

    def test_matching_value_at_another_name_is_not_guessed(self):
        bindings = deepcopy(self.bindings)
        bindings[0]['versionPath'] = ['images', 'current-backend']
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve(bindings=bindings)

    def test_duplicate_matching_documents_fail_even_when_images_are_equal(self):
        other = self.document('duplicate.json', dict(images={'old-backend': BACKEND}))
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve([self.reference, other])

    def test_duplicate_pin_is_not_deduplicated_into_success(self):
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve([self.reference, self.reference])

    def test_nonmatching_document_is_still_verified(self):
        other = self.document('other.json', dict(release='metadata'))
        Path(other['path']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_VERSION_PIN_CHANGED'):
            self.resolve([self.reference, other])

    def test_original_sha_change_is_rejected(self):
        Path(self.reference['path']).write_text(json.dumps(
            dict(images={'old-backend': FRONTEND, 'old-frontend': FRONTEND})), encoding='utf-8')
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_VERSION_PIN_CHANGED'):
            self.resolve()

    def test_original_size_change_is_rejected(self):
        reference = dict(self.reference, bytes=self.reference['bytes'] + 1)
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_VERSION_PIN_CHANGED'):
            self.resolve([reference])

    def test_original_json_duplicate_keys_are_rejected(self):
        path = self.root/'duplicates.json'
        path.write_text('{"images":{},"images":{}}', encoding='utf-8')
        with self.assertRaisesRegex(RecoveryError, 'DUPLICATE_JSON_KEY'):
            self.resolve([pin(path)])

    def test_sha256_image_id_requires_exact_string_shape(self):
        for invalid in (None, True, 123, [], {}, 'latest', 'sha256:' + 'A'*64,
                        'sha256:' + 'a'*63, BACKEND + '\n'):
            with self.subTest(value=invalid):
                reference = self.document('invalid.json',
                    dict(images={'old-backend': invalid, 'old-frontend': FRONTEND}))
                with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
                    self.resolve([reference])

    def test_paths_reject_boolean_and_negative_indexes(self):
        for invalid in (True, False, -1, 1.0, None, {}):
            with self.subTest(value=invalid):
                bindings = deepcopy(self.bindings)
                bindings[0]['versionPath'] = ['images', invalid]
                with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDINGS_INVALID'):
                    self.resolve(bindings=bindings)

    def test_string_digit_does_not_index_array(self):
        reference = self.document('array.json', dict(images=[BACKEND, FRONTEND]))
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve([reference], [dict(role='backend', versionPath=['images', '0'])])

    def test_scalar_intermediate_does_not_turn_into_string_index(self):
        reference = self.document('scalar.json', dict(images=BACKEND))
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve([reference], [dict(role='backend', versionPath=['images', 0])])

    def test_missing_array_element_fails_with_binding_error(self):
        reference = self.document('short.json', dict(images=[]))
        with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDING_MISMATCH'):
            self.resolve([reference], [dict(role='backend', versionPath=['images', 0])])

    def test_duplicate_roles_and_unexpected_binding_keys_are_rejected(self):
        invalid_bindings = [[], {}, None,
            [self.bindings[0], self.bindings[0]],
            [dict(self.bindings[0], imageId=BACKEND)],
            [dict(role='', versionPath=['images', 'old-backend'])],
            [dict(role='backend', versionPath=[])],
            [dict(role='backend', versionPath=('images', 'old-backend'))],
            [dict(versionPath=['images', 'old-backend'])]]
        for bindings in invalid_bindings:
            with self.subTest(bindings=bindings):
                with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_IMAGE_BINDINGS_INVALID'):
                    self.resolve(bindings=bindings)

    def test_empty_or_non_list_pin_collection_is_rejected(self):
        for pins in ([], {}, (self.reference,)):
            with self.subTest(pins=pins):
                with self.assertRaisesRegex(RecoveryError, 'ARCHIVED_VERSION_PINS_INVALID'):
                    self.resolve(pins=pins)

    def test_pins_and_bindings_are_not_modified_or_returned_as_mutable_aliases(self):
        pins = [deepcopy(self.reference)]
        bindings = deepcopy(self.bindings)
        before = deepcopy((pins, bindings))
        result = self.resolve(pins, bindings)
        result['backend']['versionPath'].append('changed')
        result['backend']['versionPin']['sha256'] = 'c'*64
        self.assertEqual(before, (pins, bindings))

    def test_caller_reader_failure_is_not_caught(self):
        def fail(_):
            raise RecoveryError('ORIGINAL_ARCHIVE_LEASE_LOST')
        with self.assertRaisesRegex(RecoveryError, 'ORIGINAL_ARCHIVE_LEASE_LOST'):
            self.resolve(reader=fail)

    def test_each_original_document_is_read_once_per_resolution(self):
        reads = []
        def read(reference):
            reads.append(reference)
            return json.loads(Path(reference['path']).read_bytes())
        self.resolve(reader=read)
        self.assertEqual([self.reference], reads)

    def main_fixture(self):
        fixture = main_tests.MainContractTests('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_main_missing_archive_path_keeps_original_mismatch_code(self):
        fixture = self.main_fixture()
        fixture.target['mainApplication']['archiveImageBindings'][0]['versionPath'] = ['missing']
        with self.assertRaisesRegex(RecoveryError, 'MAIN_ARCHIVED_IMAGE_MISMATCH'):
            main.application_inputs(fixture.native)

    def test_main_duplicate_archive_match_keeps_original_mismatch_code(self):
        fixture = self.main_fixture()
        fixture.material['versionPins'] *= 2
        with self.assertRaisesRegex(RecoveryError, 'MAIN_ARCHIVED_IMAGE_MISMATCH'):
            main.application_inputs(fixture.native)

    def test_main_changed_original_keeps_main_pin_failure(self):
        fixture = self.main_fixture()
        Path(fixture.material['versionPins'][0]['path']).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(RecoveryError, 'MAIN_PIN_CHANGED'):
            main.application_inputs(fixture.native)

    def test_main_current_service_cannot_differ_from_registered_image(self):
        fixture = self.main_fixture()
        fixture.native.config_services['backend']['imageId'] = 'sha256:' + '0'*64
        with self.assertRaisesRegex(RecoveryError, 'MAIN_ARCHIVED_IMAGE_MISMATCH'):
            main.application_inputs(fixture.native)


if __name__ == '__main__':
    unittest.main()
