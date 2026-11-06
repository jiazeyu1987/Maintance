"""Verify protected NAS submounts against the captured host baseline."""
import copy
import unittest

from verify_protection_runtime import verify_company_nas_mounts


class ProtectedNasMountVerification(unittest.TestCase):
    def setUp(self):
        self.before = [
            dict(mountPoint='/', mountId=93, source='/dev/sda2', options=['rw']),
            dict(mountPoint='/mnt/nas/Backup/BackupPackage', mountId=423,
                 source='//nas/share', options=['ro']),
            dict(mountPoint='/unrelated', mountId=500, source='tmpfs', options=['rw']),
        ]

    def test_original_submount_preserved_without_parent_mount(self):
        self.assertEqual(len(verify_company_nas_mounts(self.before, copy.deepcopy(self.before))), 2)

    def test_protected_submount_change_is_rejected(self):
        after = copy.deepcopy(self.before)
        after[1]['options'] = ['rw']
        with self.assertRaisesRegex(AssertionError, 'COMPANY_NAS_MOUNT_CHANGED'):
            verify_company_nas_mounts(self.before, after)

    def test_unexpected_protected_submount_is_rejected(self):
        after = copy.deepcopy(self.before) + [dict(mountPoint='/mnt/nas/new', mountId=600)]
        with self.assertRaisesRegex(AssertionError, 'COMPANY_NAS_MOUNT_CHANGED'):
            verify_company_nas_mounts(self.before, after)

    def test_covering_filesystem_change_is_rejected(self):
        after = copy.deepcopy(self.before)
        after[0]['source'] = '/dev/other'
        with self.assertRaisesRegex(AssertionError, 'COMPANY_NAS_MOUNT_CHANGED'):
            verify_company_nas_mounts(self.before, after)

    def test_unrelated_mount_change_does_not_change_protected_baseline(self):
        after = copy.deepcopy(self.before)
        after[2]['mountId'] = 501
        verify_company_nas_mounts(self.before, after)


if __name__ == '__main__':
    unittest.main()
