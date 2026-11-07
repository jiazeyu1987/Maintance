"""Real-file contracts for on-demand existence checks; never restore or hash payloads."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from package_catalog import scan_catalog
from package_presence import verify_package


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PackagePresenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.backups=self.root/'backups';self.releases=self.root/'releases'
        self.backups.mkdir();self.releases.mkdir()
        self.roots=[dict(category='backup',path=str(self.backups)),dict(category='release',path=str(self.releases))]

    def release(self,kind=None):
        folder=self.releases/(kind or 'full');folder.mkdir()
        manifest=dict(applicationId='intruoyi',releaseTag=kind or 'full',files=[dict(name='images.tar')])
        if kind:manifest['kind']=kind
        write(folder/'manifest.json',manifest);(folder/'release.tar').write_bytes(b'payload not opened')
        return folder

    def backup(self,point_type='FULL'):
        folder=self.backups/'archives'/point_type
        (folder/'payload').mkdir(parents=True)
        (folder/'payload/db.sql').write_bytes(b'not a real database; unit file')
        refs=[dict(path='/export/archive/payload/db.sql',bytes=29,sha256='a'*64)]
        write(folder/'.repository/payload-tree.json',dict(files=refs))
        manifest=dict(schemaVersion='RepositoryManifest/v1',backupId=point_type,pointType=point_type,
                      payloadRefs=refs,payloadTreePin=dict(path='/export/archive/.repository/payload-tree.json'))
        sha=write(folder/'.repository/manifest.json',manifest)
        write(folder/'.repository/point.json',dict(schemaVersion='RepositoryPoint/v1',backupId=point_type,
              pointType=point_type,manifestPin=dict(sha256=sha)))
        return folder

    def row(self,folder):
        return next(x for x in scan_catalog(self.roots,{})['items'] if str(folder) in x['nasPaths'])

    def test_five_package_types_check_their_declared_files_without_mutation(self):
        folders=[self.backup(),self.backup('INCREMENTAL'),self.release(),self.release('frontend-patch'),self.release('backend-patch')]
        for folder in folders:
            with self.subTest(folder=folder.name):
                before={str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
                row=self.row(folder);self.assertRegex(row['checkKey'],r'^[a-f0-9]{64}$')
                result=verify_package(row,self.roots)
                self.assertEqual(result['status'],'exists')
                self.assertGreaterEqual(result['existingFiles'],2)
                self.assertEqual(result['verification'],'file-existence-only')
                self.assertFalse(result['payloadContentVerified'])
                self.assertEqual(before,{str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()})

    def test_removed_sealed_archive_does_not_fall_back_to_other_files(self):
        folder=self.release();row=self.row(folder)
        (folder/'release.tar').unlink();(folder/'images.tar').write_bytes(b'unrelated extracted copy')
        result=verify_package(row,self.roots)
        self.assertEqual(result['status'],'missing')
        self.assertIn('release.tar',result['copies'][0]['missingFiles'])

    def test_backup_missing_payload_is_missing_even_when_directory_and_manifest_exist(self):
        folder=self.backup();row=self.row(folder);(folder/'payload/db.sql').unlink()
        result=verify_package(row,self.roots)
        self.assertEqual(result['status'],'missing')
        self.assertIn('payload/db.sql',result['copies'][0]['missingFiles'])

    def test_changed_manifest_requires_catalog_refresh(self):
        folder=self.release();row=self.row(folder)
        write(folder/'manifest.json',dict(applicationId='intruoyi',releaseTag='changed',files=[]))
        self.assertEqual(verify_package(row,self.roots)['status'],'changed')

    def test_unauthorized_path_and_manifest_traversal_are_refused(self):
        folder=self.release();row=self.row(folder);row['nasPaths']=[str(self.root/'private')]
        self.assertEqual(verify_package(row,self.roots)['status'],'error')
        folder=self.backup();manifest=json.loads((folder/'.repository/manifest.json').read_text(encoding='utf-8'))
        manifest['payloadRefs'][0]['path']='/export/archive/../private.json'
        write(folder/'.repository/manifest.json',manifest)
        self.assertEqual(verify_package(self.row(folder),self.roots)['status'],'error')

    def test_root_unavailable_is_distinct_from_missing_package(self):
        folder=self.release();row=self.row(folder);shutil.rmtree(folder)
        self.assertEqual(verify_package(row,self.roots)['status'],'missing')
        self.releases.rmdir()
        self.assertEqual(verify_package(row,self.roots)['status'],'unavailable')

    def test_every_archived_copy_is_reported(self):
        folder=self.release();row=self.row(folder)
        duplicate=self.releases/'copy';shutil.copytree(folder,duplicate);row['nasPaths'].append(str(duplicate))
        (duplicate/'release.tar').unlink()
        result=verify_package(row,self.roots)
        self.assertEqual(result['status'],'missing')
        self.assertEqual([c['status'] for c in result['copies']],['exists','missing'])

    def test_linked_payload_is_refused_without_opening_outside_files(self):
        import os
        import subprocess
        folder=self.backup();row=self.row(folder)
        (folder/'payload/db.sql').unlink();(folder/'payload').rmdir()
        outside=self.root/'outside';outside.mkdir();(outside/'db.sql').write_bytes(b'private')
        if os.name=='nt':
            subprocess.run(['cmd','/c','mklink','/J',str(folder/'payload'),str(outside)],check=True,capture_output=True)
        else:(folder/'payload').symlink_to(outside,target_is_directory=True)
        self.assertEqual(verify_package(row,self.roots)['status'],'error')
