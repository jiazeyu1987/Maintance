"""Historical bytes must remain immutable while reviewed fixes move forward."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import intruoyi_build
from ops.release.release_source_catalog import SourceCatalogError, release_paths, sql_tokens


class HistoricalSourceTests(unittest.TestCase):
    def test_comments_are_ignored_but_literals_and_executable_comments_are_not(self):
        self.assertEqual(sql_tokens('-- old\r\nSELECT a /* note */ FROM t;'), sql_tokens('# new\nSELECT a FROM t;'))
        for left, right in [("SELECT 'a b';", "SELECT 'ab';"), ('SELECT a/*!80000 + 1 */;', 'SELECT a;'),
                            ('SELECT /*+ INDEX(t x) */ a;', 'SELECT a;'), ('SELECT a- -b;', 'SELECT a-b;')]:
            self.assertNotEqual(sql_tokens(left), sql_tokens(right))
        with self.assertRaises(SourceCatalogError):
            sql_tokens("SELECT 'unfinished")

    def fixture(self, root, disposition='forward-migrations'):
        original = b'-- release-migration: type=schema; risk=low\r\nSELECT 1;\r\n'
        current = b'-- release-migration: type=schema; risk=low\nSELECT 2;\n'
        name = '20260101_old.sql'
        successor = '20261022_fix.sql'
        (root/'historical').mkdir()
        (root/'historical'/name).write_bytes(original)
        (root/name).write_bytes(current)
        (root/successor).write_text('-- release-migration: type=schema; risk=low\nSELECT 2;', 'utf-8')
        entry = dict(file=name, original='historical/'+name, sha256=hashlib.sha256(current).hexdigest(),
                     originalSha256=hashlib.sha256(original).hexdigest(), disposition=disposition,
                     successors=[successor], reason='Reviewed independent forward repair covers the changed SQL.')
        catalog = dict(schemaVersion='release-sql-sources/v2', migrations=[successor], sourceReferences=[], historicalMigrations=[entry])
        self.save(root, catalog)
        return catalog

    def save(self, root, catalog):
        (root/'release-sources.json').write_text(json.dumps(catalog), 'utf-8')

    def test_uses_original_bytes_and_independent_successor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            paths, references = release_paths(root)
            self.assertEqual({p.relative_to(root).as_posix() for p in paths}, {'historical/20260101_old.sql', '20261022_fix.sql'})
            self.assertEqual(references, [])

    def test_refuses_changed_archives_or_reviewed_inputs(self):
        for relative in ['historical/20260101_old.sql', '20260101_old.sql']:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.fixture(root)
                (root/relative).write_bytes(b'changed')
                with self.assertRaisesRegex(SourceCatalogError, 'missing or changed'):
                    release_paths(root)

    def test_cannot_claim_semantic_edits_are_equivalent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog = self.fixture(root, 'equivalent')
            catalog['historicalMigrations'][0]['successors'] = []
            self.save(root, catalog)
            with self.assertRaisesRegex(SourceCatalogError, 'require forward migrations'):
                release_paths(root)

    def test_unreviewed_or_missing_or_self_referencing_successors_block(self):
        for disposition, successors in [('pending-review', []), ('forward-migrations', []),
                                        ('forward-migrations', ['20261022_missing.sql']),
                                        ('forward-migrations', ['20260101_old.sql'])]:
            with self.subTest(disposition=disposition, successors=successors), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                catalog = self.fixture(root, disposition)
                catalog['historicalMigrations'][0]['successors'] = successors
                self.save(root, catalog)
                with self.assertRaises(SourceCatalogError):
                    release_paths(root)

    def test_review_only_draft_is_preserved_without_creating_an_applied_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            name = '20260705_review_draft.sql'
            content = '-- REVIEW ONLY: UPDATE protected_data SET name=1;\n'
            (root/name).write_bytes(content.encode())
            reference = dict(file=name, kind='review-only', sha256=hashlib.sha256(content.encode()).hexdigest(),
                             reason='Commented review draft has no executable migration and must never be marked applied.')
            catalog = dict(schemaVersion='release-sql-sources/v2', migrations=[], sourceReferences=[reference])
            self.save(root, catalog)
            self.assertEqual(release_paths(root), ([], [reference]))
            for executable in ['SELECT 1;', '/*!80000 SELECT 1 */;']:
                (root/name).write_bytes(executable.encode())
                reference['sha256'] = hashlib.sha256(executable.encode()).hexdigest()
                self.save(root, catalog)
                with self.assertRaisesRegex(SourceCatalogError, 'no executable SQL'):
                    release_paths(root)

    def test_new_sql_is_blocked_even_with_release_or_rollback_metadata(self):
        for metadata in ('release-migration: allowedEnvironments=test,prod,backup; type=data',
                         'rollback-migration: type=schema'):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.fixture(root)
                (root/'20261023_unregistered.sql').write_text('-- '+metadata+'\nSELECT 1;', 'utf-8')
                with self.assertRaisesRegex(SourceCatalogError, 'unregistered: 20261023_unregistered.sql'):
                    release_paths(root)

    def test_registration_includes_sql_and_reasoned_exclusion_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog = self.fixture(root)
            included, excluded = '20261023_added.sql', '20261023_business_setup.sql'
            for name in (included, excluded):
                (root/name).write_text('SELECT 1;', 'utf-8')
            catalog['migrations'].append(included)
            catalog['excludedSources'] = [dict(file=excluded, reason='Separate one-time business configuration.')]
            self.save(root, catalog)
            paths, _ = release_paths(root)
            self.assertIn(root/included, paths)
            self.assertNotIn(root/excluded, paths)

    def test_missing_duplicate_and_conflicting_registrations_block(self):
        for change, message in (
            (dict(migrations=['20261022_fix.sql', '20261023_missing.sql']), 'missing: 20261023_missing.sql'),
            (dict(migrations=['20261022_fix.sql', '20261022_fix.sql']), 'duplicate'),
            (dict(excludedSources=[dict(file='20261022_fix.sql', reason='Not a release')]), 'conflicting'),
            (dict(migrations=None), 'Explicit migrations'),
            (dict(excludedSources=[dict(file='20261022_fix.sql', reason='')]), 'reason required'),
        ):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                catalog = self.fixture(root)
                catalog.update(change)
                self.save(root, catalog)
                with self.assertRaisesRegex(SourceCatalogError, message):
                    release_paths(root)

    def test_historical_successor_cannot_be_excluded_from_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            catalog = self.fixture(root)
            catalog['migrations'] = []
            catalog['excludedSources'] = [dict(file='20261022_fix.sql', reason='Excluded business script')]
            self.save(root, catalog)
            with self.assertRaisesRegex(SourceCatalogError, 'successors must be independently executable'):
                release_paths(root)


if __name__ == '__main__':
    unittest.main()
