import hashlib
import unittest
from recovery_version_copies import archived_version_pin

class VersionCopyTests(unittest.TestCase):
    def test_missing_source_path_uses_exact_captured_copy(self):
        source=dict(path='/missing/source/images.json',bytes=2,sha256=hashlib.sha256(b'{}').hexdigest())
        archive=dict(source,path='/archive/semantic-capture/provided-'+hashlib.sha256(source['path'].encode()).hexdigest()+'.bin')
        self.assertEqual(archived_version_pin(source,[archive]),archive)
        with self.assertRaises(Exception):archived_version_pin(source,[])
        with self.assertRaises(Exception):archived_version_pin(source,[dict(archive,bytes=3)])
        with self.assertRaises(Exception):archived_version_pin(source,[archive,archive])

if __name__=='__main__':unittest.main()
