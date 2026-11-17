import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[2]/'ops/spug/release-center/runtime_env_metadata.py'
spec=importlib.util.spec_from_file_location('runtime_env_metadata',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RuntimeEnvMetadataTest(unittest.TestCase):
    def test_preserves_other_bytes_and_line_endings(self):
        raw=b'# runtime\r\nMYSQL_PASSWORD=private-value\r\nIMAGE_TAG=old-tag\r\nOTHER=1\r\n'
        actual=module.aligned_bytes(raw,'old-tag','2026-11-17-23-51-44')
        self.assertEqual(actual,raw.replace(b'IMAGE_TAG=old-tag',b'IMAGE_TAG=2026-11-17-23-51-44'))
    def test_rejects_concurrent_tag_change(self):
        with self.assertRaises(module.MetadataBlocked):module.aligned_bytes(b'IMAGE_TAG=unexpected\n','old-tag','2026-11-17-23-51-44')
    def test_rejects_missing_or_duplicate_tag(self):
        for raw in [b'OTHER=1\n',b'IMAGE_TAG=old-tag\nIMAGE_TAG=old-tag\n']:
            with self.assertRaises(module.MetadataBlocked):module.aligned_bytes(raw,'old-tag','2026-11-17-23-51-44')
    def test_rejects_invalid_release_tag(self):
        with self.assertRaises(module.MetadataBlocked):module.aligned_bytes(b'IMAGE_TAG=old-tag\n','old-tag','not-a-release')
    def test_refuses_image_or_tag_or_running_mismatch(self):
        expected={'id':'sha256:'+'a'*64,'name':'intruoyi-backend:2026-11-17-23-51-44'}
        good={'State':{'Running':True},'Image':expected['id']}
        module.validate_image(good,{'Id':expected['id'],'RepoTags':[expected['name']]},expected)
        for container,image in [(dict(good,Image='sha256:'+'b'*64),{'Id':expected['id'],'RepoTags':[expected['name']]}),(good,{'Id':expected['id'],'RepoTags':[]}),(dict(good,State={'Running':False}),{'Id':expected['id'],'RepoTags':[expected['name']]})]:
            with self.assertRaises(module.MetadataBlocked):module.validate_image(container,image,expected)

if __name__=='__main__':unittest.main()
