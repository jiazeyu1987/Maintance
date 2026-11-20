import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import release_runtime_metadata as metadata

TAG = '2026-11-19-23-41-45'


class MetadataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / '.env'
        self.raw = b'# config\r\nIMAGE_TAG=old\r\nPRIVATE=keep\r\n'
        self.path.write_bytes(self.raw)
        self.profile = dict(environment='test', runtimeEnvironmentFile=str(self.path), backend='b', frontend='f')
        self.images = {r: dict(id='sha256:'+c*64, name='intruoyi-'+r+':'+TAG)
                       for r,c in [('backend','a'),('frontend','b')]}
        self.candidate = dict(releaseTag=TAG, images=self.images)
        self.containers = {self.profile[r]:dict(Id=r+'-container', Image=v['id'], State=dict(Running=True))
                           for r,v in self.images.items()}
        self.evidence = self.root / 'evidence'

    def run_align(self):
        def run(args):
            expected = next(i for i in self.images.values() if i['name']==args[-1])
            return json.dumps([dict(Id=expected['id'],RepoTags=[expected['name']])]).encode()
        return metadata.align(self.profile,self.candidate,self.evidence,
                              inspect=lambda n:self.containers[n],run=run)

    def test_no_backup_binding_aligns_and_retries_without_overwriting_original(self):
        result=self.run_align()
        self.assertEqual(result['status'],'ALIGNED')
        self.assertEqual(self.path.read_bytes(),self.raw.replace(b'IMAGE_TAG=old',('IMAGE_TAG='+TAG).encode()))
        self.assertEqual((self.evidence/'runtime.env.before').read_bytes(),self.raw)
        self.assertEqual(self.run_align(),result)

    def test_each_deployed_environment_uses_same_contract(self):
        for env in ['test','prod','backup']:
            self.profile['environment']=env
            self.assertEqual(metadata.environment_path(self.profile),self.path)

    def test_missing_path_and_conflicting_binding_fail(self):
        with self.assertRaises(ValueError):metadata.environment_path(dict(environment='test'))
        self.profile['backupSourceBinding']={'environmentFile':str(self.root/'other')}
        with self.assertRaises(ValueError):metadata.environment_path(self.profile)

    def test_legacy_explicit_binding_is_supported_without_guessing(self):
        p=dict(environment='prod',backupSourceBinding={'environmentFile':str(self.path)})
        self.assertEqual(metadata.environment_path(p),self.path)

    def test_image_mismatch_does_not_write(self):
        self.containers['b']['Image']='wrong'
        with self.assertRaises(ValueError):self.run_align()
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertFalse(self.evidence.exists())

    def test_stopped_container_does_not_write(self):
        self.containers['f']['State']['Running']=False
        with self.assertRaises(ValueError):self.run_align()
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_ambiguous_env_fails_without_receipt(self):
        self.path.write_bytes(self.raw+b'IMAGE_TAG=other\n')
        with self.assertRaises(ValueError):self.run_align()
        self.assertFalse(self.evidence.exists())

    def test_retry_rejects_concurrent_change(self):
        self.run_align()
        self.path.write_bytes(self.path.read_bytes()+b'CHANGED=1\n')
        with self.assertRaises(ValueError):self.run_align()

    def test_resume_after_replace_before_receipt(self):
        original=metadata.write_json
        def fail(path,value):
            if path.name=='result.json':raise OSError('interrupted')
            return original(path,value)
        with patch.object(metadata,'write_json',side_effect=fail):
            with self.assertRaises(OSError):self.run_align()
        self.assertEqual(self.run_align()['status'],'ALIGNED')

    def test_concurrent_change_before_replace_is_preserved(self):
        original=metadata.write_json
        def race(path,value):
            original(path,value)
            if path.name=='intent.json':self.path.write_bytes(b'IMAGE_TAG=other\n')
        with patch.object(metadata,'write_json',side_effect=race):
            with self.assertRaises(ValueError):self.run_align()
        self.assertEqual(self.path.read_bytes(),b'IMAGE_TAG=other\n')

    def test_same_tag_with_different_container_is_not_same_attempt(self):
        self.run_align()
        self.containers['b']['Id']='replaced'
        with self.assertRaises(ValueError):self.run_align()

    def test_interrupted_receipt_write_leaves_no_partial_final_file(self):
        receipt=self.root/'result.json'
        with patch.object(metadata.os,'fsync',side_effect=OSError('disk error')):
            with self.assertRaises(OSError):metadata.write_json(receipt,{'status':'ALIGNED'})
        self.assertFalse(receipt.exists())


if __name__=='__main__':unittest.main()
