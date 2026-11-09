"""Request-local catalogue reads against real, pinned temporary archive files."""
from collections import Counter
from copy import deepcopy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'backend/src/main/resources'))
sys.path.insert(0, str(ROOT/'scripts/tests'))
import test_restore_archive_catalogue as fixtures
import recovery_control_restore_catalogue as catalogue
import recovery_control_executor as executor
from recovery_control_smallapp import canonical, decode


class RequestReads(unittest.TestCase):
    def setUp(self):
        self.files = fixtures.ArchiveCatalogue()
        self.files.setUp()
        self.addCleanup(self.files.doCleanups)
        self.first = self.files.point('full-first')
        self.last = self.files.point('backup-new', [self.first])
        self.native = self.files.native_with_archive_catalogue()
        self.configuration = self.native.configuration()
        reference = self.configuration['archiveRestoreCatalogues']['source-A']
        self.index = self.native.document(reference)
        self.index['pointPins'] = [self.first, self.last]
        self.set_index(self.index)
        self.manifest = Path(self.first['path']).parent/'manifest.json'
        self.marker = Path(self.configuration['registryRoot'])/'quarantined-points/full-first.json'

    def set_index(self, value):
        self.configuration['archiveRestoreCatalogues']['source-A'] = self.files.write(
            self.files.root/'native/archive-catalogue.json', value)

    def references(self):
        return catalogue.archive_references(self.native, self.configuration, 'source-A')

    def mutate_after_last_close(self, mutate):
        # The real decoder still runs; only this callback mutates on-disk originals.
        # No file validation, digest, failure or successful result is mocked.
        fired = []
        def reading(raw):
            value = decode(raw)
            if (not fired and value.get('schemaVersion') == 'RepositoryMinimumArchiveClose/v1'
                    and value.get('operationId') == 'backup-new'):
                fired.append(True)
                mutate()
            return value
        return patch.object(catalogue, 'decode', side_effect=reading), fired

    def refuse_mutation(self, mutate, error='ARCHIVE_.*CHANGED|NATIVE_PIN_CHANGED|POINT_QUARANTINED'):
        hook, fired = self.mutate_after_last_close(mutate)
        with hook, self.assertRaisesRegex(Exception, error):
            self.references()
        self.assertTrue(fired, 'real terminal evidence was never reached')

    def test_shared_metadata_is_decoded_once_and_content_read_at_most_twice(self):
        decoded, reads = Counter(), Counter()
        last_path = []
        real_read = executor.pinned_read
        def reading(path, *args, **kwargs):
            reads[str(Path(path))] += 1
            last_path[:] = [str(Path(path))]
            return real_read(path, *args, **kwargs)
        def decoding(raw):
            # Separate originals may legitimately contain identical JSON bytes.
            decoded[last_path[0]] += 1
            return decode(raw)
        with patch.object(catalogue, 'decode', side_effect=decoding), \
                patch.object(executor, 'pinned_read', side_effect=reading):
            actual = self.references()
        self.assertEqual(actual, {'full-first': self.first, 'backup-new': self.last})
        self.assertTrue(decoded)
        self.assertEqual(max(decoded.values()), 1, 'same metadata decoded repeatedly')
        self.assertEqual(set(reads.values()), {2}, 'every original needs its initial and final complete read')

    def test_archive_root_is_enumerated_once_for_shared_chains(self):
        root = Path(self.files.source['archiveRoots'][0])
        scans = []
        original = os.scandir
        def scanning(path):
            if Path(path) == root:
                scans.append(path)
            return original(path)
        with patch.object(os, 'scandir', side_effect=scanning):
            self.references()
        self.assertEqual(len(scans), 1, 'archive root rescanned for each selected point')

    def test_late_manifest_content_mutation_is_rejected(self):
        self.refuse_mutation(lambda: self.manifest.write_bytes(b'{}'))

    def test_late_same_bytes_file_replacement_is_rejected(self):
        before = self.manifest.stat()
        def replace():
            replacement = self.manifest.with_name('replacement.tmp')
            replacement.write_bytes(self.manifest.read_bytes())
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(self.manifest)
            self.assertNotEqual(before.st_ino, self.manifest.stat().st_ino)
        self.refuse_mutation(replace)

    def test_late_duplicate_id_addition_is_rejected(self):
        original = Path(self.first['path']).read_bytes()
        def duplicate():
            path = self.files.root/'archives/late-duplicate/.repository/point.json'
            path.parent.mkdir(parents=True)
            path.write_bytes(original)
        self.refuse_mutation(duplicate)

    def test_late_addition_in_existing_empty_archive_directory_is_rejected(self):
        empty = self.files.root/'archives/empty-before-request'
        empty.mkdir()
        def add():
            path = empty/'.repository/point.json'
            path.parent.mkdir()
            path.write_bytes(Path(self.first['path']).read_bytes())
        self.refuse_mutation(add)

    def test_late_addition_in_existing_empty_repository_is_rejected(self):
        empty = self.files.root/'archives/empty-before-request/.repository'
        empty.mkdir(parents=True)
        self.refuse_mutation(lambda: (empty/'point.json').write_bytes(Path(self.first['path']).read_bytes()))

    def test_late_directory_replacement_with_same_point_bytes_is_rejected(self):
        sidecar = self.manifest.parent
        def replace():
            old = sidecar.with_name('.repository-old')
            sidecar.rename(old)
            sidecar.mkdir()
            for path in old.iterdir():
                (sidecar/path.name).write_bytes(path.read_bytes())
        self.refuse_mutation(replace)

    def test_late_quarantine_of_already_checked_parent_is_rejected(self):
        def quarantine():
            self.marker.parent.mkdir(parents=True, exist_ok=True)
            self.marker.write_bytes(canonical({'preserved': 'original marker'}))
        self.refuse_mutation(quarantine, 'POINT_QUARANTINED')

    def test_quarantine_added_after_last_parent_check_is_rejected(self):
        final_marker = self.marker.with_name('backup-new.json')
        exists = Path.exists
        fired = []
        def checking(path):
            actual = exists(path)
            if path == final_marker and not fired:
                fired.append(True)
                self.marker.parent.mkdir(parents=True, exist_ok=True)
                self.marker.write_bytes(canonical({'preserved': True}))
            return actual
        with patch.object(Path, 'exists', checking), self.assertRaisesRegex(Exception, 'POINT_QUARANTINED'):
            self.references()
        self.assertTrue(fired)

    def test_transient_quarantine_change_during_request_is_rejected(self):
        self.marker.parent.mkdir(parents=True)
        def quarantine():
            self.marker.write_bytes(canonical({'preserved': True}))
            self.marker.unlink()
        self.refuse_mutation(quarantine, 'POINT_QUARANTINED')

    def test_late_immutable_index_mutation_is_rejected(self):
        index_path = Path(self.configuration['archiveRestoreCatalogues']['source-A']['path'])
        self.refuse_mutation(lambda: index_path.write_bytes(b'{}'))

    def test_mutation_at_final_sha_read_is_rejected(self):
        original = executor.pinned_read
        fired = []
        def reading(path, retain=False, **kwargs):
            if Path(path) == self.manifest and not retain and not fired:
                fired.append(True)
                # This happens after the pre-hash stat check. The native read
                # and digest still execute over the actual changed bytes.
                self.manifest.write_bytes(b'{}')
            return original(path, retain, **kwargs)
        with patch.object(executor, 'pinned_read', side_effect=reading), \
                self.assertRaisesRegex(Exception, 'ARCHIVE_METADATA_CHANGED|NATIVE_PIN_CHANGED'):
            self.references()
        self.assertTrue(fired, 'final SHA read did not run')

    def test_root_renamed_during_request_is_rejected(self):
        archive = self.files.root/'archives'
        hook, fired = self.mutate_after_last_close(lambda: archive.rename(self.files.root/'renamed-archives'))
        with hook, self.assertRaises(Exception):
            self.references()
        self.assertTrue(fired)

    def test_changes_after_first_request_are_not_cached(self):
        self.assertEqual(len(self.references()), 2)
        self.manifest.write_bytes(b'{}')
        with self.assertRaises(Exception):
            self.references()

    def test_duplicate_added_between_requests_is_not_cached(self):
        self.references()
        duplicate = self.files.root/'archives/duplicate/.repository/point.json'
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(Path(self.first['path']).read_bytes())
        with self.assertRaisesRegex(Exception, 'ARCHIVE_POINT_REFERENCE_AMBIGUOUS'):
            self.references()

    def test_quarantine_added_between_requests_is_not_cached(self):
        self.references()
        self.marker.parent.mkdir(parents=True)
        self.marker.write_bytes(canonical({'preserved': True}))
        with self.assertRaisesRegex(Exception, 'POINT_QUARANTINED'):
            self.references()

    def test_index_pin_changed_between_requests_is_rejected(self):
        self.references()
        path = Path(self.configuration['archiveRestoreCatalogues']['source-A']['path'])
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(Exception, 'NATIVE_PIN_CHANGED|ARCHIVE_METADATA_CHANGED'):
            self.references()

    def test_same_bytes_replacement_between_requests_gets_new_native_reads(self):
        self.references()
        replacement = self.manifest.with_name('replacement.tmp')
        replacement.write_bytes(self.manifest.read_bytes())
        replacement.replace(self.manifest)
        original = executor.pinned_read
        reads = []
        def reading(path, *args, **kwargs):
            if Path(path) == self.manifest:
                reads.append(path)
            return original(path, *args, **kwargs)
        with patch.object(executor, 'pinned_read', side_effect=reading):
            self.assertEqual(len(self.references()), 2)
        self.assertEqual(len(reads), 2, 'second request reused previous parsed success')

    def test_parent_not_in_index_still_rejected(self):
        changed = deepcopy(self.index)
        changed['pointPins'] = [self.last]
        self.set_index(changed)
        with self.assertRaisesRegex(Exception, 'ARCHIVE_PARENT_NOT_ADMITTED'):
            self.references()

    def test_changed_point_limit_still_rejected(self):
        changed = deepcopy(self.index)
        changed['source']['archiveCatalogue']['maximumPointFiles'] = 1
        self.set_index(changed)
        with self.assertRaisesRegex(Exception, 'ARCHIVE_POINT_LIMIT_EXCEEDED'):
            self.references()

    def test_for_request_checks_parent_eligibility_and_rejects_late_mutation(self):
        # source_admits supplies the already authenticated source response;
        # every archive file and mutation below uses the actual filesystem.
        owner = self.files.write(self.files.root/'owner.json', {'sources': {'source-A': self.files.source}})
        request = dict(sourceConfigRef='source-A', recoveryPointRef='backup-new', operationId='read-safety')
        hook, fired = self.mutate_after_last_close(lambda: self.manifest.write_bytes(b'{}'))
        with patch.object(catalogue, 'source_admits', return_value=['full-first', 'backup-new']), hook, \
                self.assertRaisesRegex(Exception, 'ARCHIVE_.*CHANGED|NATIVE_PIN_CHANGED'):
            catalogue.for_request(self.native, self.configuration, request, owner)
        self.assertTrue(fired)
        self.assertFalse((Path(self.configuration['taskRoot'])/'request-configurations').exists())

    def test_for_request_still_requires_current_source_admission_of_every_parent(self):
        owner = self.files.write(self.files.root/'owner.json', {'sources': {'source-A': self.files.source}})
        request = dict(sourceConfigRef='source-A', recoveryPointRef='backup-new', operationId='read-safety')
        with patch.object(catalogue, 'source_admits', return_value=['backup-new']), \
                self.assertRaisesRegex(Exception, 'SOURCE_PARENT_NOT_CURRENTLY_ELIGIBLE'):
            catalogue.for_request(self.native, self.configuration, request, owner)
        self.assertFalse((Path(self.configuration['taskRoot'])/'request-configurations').exists())


if __name__ == '__main__':
    unittest.main()
