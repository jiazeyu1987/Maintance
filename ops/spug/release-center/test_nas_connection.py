"""Private credential binding contracts; actual NAS access is verified separately."""
import json
from pathlib import Path
import tempfile
import unittest

from nas_connection import connection_parameters


class NasCredentialBindingTests(unittest.TestCase):
    def check_parameters(self, values, path=r'\\172.30.30.4\IT共享\Backup\ReleasePackage\intruoyi'):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)/'nas.private.json'
            private.write_text(json.dumps(values), 'utf-8')
            return connection_parameters(path, str(private))

    def test_unicode_share_and_domain_are_passed_explicitly(self):
        result = self.check_parameters(dict(server='172.30.30.4',share='IT共享',domain='NAS',username='publisher',password='test-only'))
        self.assertEqual(result, ('\\\\172.30.30.4\\IT共享', 'NAS\\publisher', 'test-only'))

    def test_other_share_cannot_reuse_bound_credentials(self):
        with self.assertRaisesRegex(ValueError, 'not bound'):
            self.check_parameters(dict(server='172.30.30.4',share='other',username='publisher',password='test-only'))

    def test_missing_password_is_not_replaced_by_windows_identity(self):
        with self.assertRaisesRegex(ValueError, 'password are required'):
            self.check_parameters(dict(server='172.30.30.4',share='IT共享',username='publisher'))

    def test_local_storage_is_not_a_fallback(self):
        with self.assertRaisesRegex(ValueError, 'UNC share'):
            self.check_parameters({}, 'C:/temporary')


if __name__ == '__main__':
    unittest.main()
