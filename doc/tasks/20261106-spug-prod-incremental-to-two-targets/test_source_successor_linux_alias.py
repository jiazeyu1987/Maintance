"""Targeted real Linux file identities; no network, services, or installation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from install_automatic_source_successor import local_pin,verify_staged_engine


class LinuxStagedIdentity(unittest.TestCase):
    def test_real_staged_file_aliases_and_members(self):
        self.assertEqual(os.name,'posix','This directed test requires real Linux identities')
        for mode in ('valid','file-symlink','directory-symlink','engine-symlink','file-hardlink','extra-directory','extra-file'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);engine=root/'engine';(engine/'formal').mkdir(parents=True)
                program=engine/'formal/tool.py';program.write_bytes(b'print(1)\n')
                files={'formal/tool.py':hashlib.sha256(program.read_bytes()).hexdigest()}
                metadata=dict(variant='standard',fileVerification=True,payloadContentVerification=True,files=files,
                    packageSha256=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest())
                (engine/'package.json').write_text(json.dumps(metadata),encoding='utf-8')
                package_pin=local_pin(engine/'package.json')
                if mode=='file-symlink':
                    outside=root/'actual.py';program.rename(outside);program.symlink_to(outside)
                elif mode=='directory-symlink':
                    outside=root/'actual-formal';(engine/'formal').rename(outside);(engine/'formal').symlink_to(outside,target_is_directory=True)
                elif mode=='engine-symlink':
                    outside=root/'actual-engine';engine.rename(outside);engine.symlink_to(outside,target_is_directory=True)
                elif mode=='file-hardlink':os.link(program,root/'other-link.py')
                elif mode=='extra-directory':(engine/'unexpected').mkdir()
                elif mode=='extra-file':(engine/'unexpected.py').write_bytes(b'extra')
                if mode=='valid':self.assertEqual(verify_staged_engine(engine,files,package_pin),1)
                else:
                    with self.assertRaises(AssertionError):verify_staged_engine(engine,files,package_pin)


if __name__=='__main__':unittest.main(verbosity=2)
