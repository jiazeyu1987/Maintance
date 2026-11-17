import tempfile
import os
import stat
import unittest
from pathlib import Path
from release_backup_source import update_image_tag
from release_backup_source import synchronize
from release_backup_source import create_attempt


class EnvironmentBindingTests(unittest.TestCase):
    def test_abandoned_temporary_file_does_not_block_retry(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'.env';p.write_bytes(b'IMAGE_TAG=old\n')
            abandoned=Path(root)/'.env.release-binding.tmp'
            abandoned.write_bytes(b'previous interrupted attempt')
            update_image_tag(p,'new')
            self.assertEqual(p.read_bytes(),b'IMAGE_TAG=new\n')
            self.assertEqual(abandoned.read_bytes(),b'previous interrupted attempt')
            self.assertEqual(len(list(Path(root).iterdir())),2)
    def test_environment_permissions_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/'.env';p.write_bytes(b'IMAGE_TAG=old\n');p.chmod(0o640)
            before=p.stat()
            update_image_tag(p,'new')
            after=p.stat()
            self.assertEqual(stat.S_IMODE(after.st_mode),stat.S_IMODE(before.st_mode))
            self.assertEqual((after.st_uid,after.st_gid),(before.st_uid,before.st_gid))
    def test_incomplete_stage_is_retained_and_retry_gets_new_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            first=create_attempt(Path(root)/'v1')
            (first/'partial.json').write_text('{}',encoding='utf-8')
            second=create_attempt(Path(root)/'v1')
            self.assertNotEqual(first,second)
            self.assertTrue((first/'partial.json').exists())
            self.assertEqual(list(second.iterdir()),[])
    def test_unconfigured_release_needs_no_linux_dependencies(self):
        self.assertEqual(synchronize({}, {}, run=None, inspect=None), {'status':'NOT_CONFIGURED'})
    def test_changes_only_version_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / '.env'
            p.write_bytes(b'OTHER=keep\r\nIMAGE_TAG=old\r\nSECRET=private\r\n')
            update_image_tag(p, 'new')
            self.assertEqual(p.read_bytes(), b'OTHER=keep\r\nIMAGE_TAG=new\r\nSECRET=private\r\n')
            update_image_tag(p, 'new')
            self.assertEqual(p.read_bytes(), b'OTHER=keep\r\nIMAGE_TAG=new\r\nSECRET=private\r\n')

    def test_ambiguous_version_rejected_without_write(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / '.env'
            original = b'IMAGE_TAG=a\nIMAGE_TAG=b\n'
            p.write_bytes(original)
            with self.assertRaises(ValueError): update_image_tag(p, 'new')
            self.assertEqual(p.read_bytes(), original)


if __name__ == '__main__': unittest.main()
