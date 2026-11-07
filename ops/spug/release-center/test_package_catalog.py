"""Real filesystem contracts for the read-only, unified NAS package catalogue."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from package_catalog import scan_catalog
from application_registry import ApplicationRegistry, RegistryError


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PackageCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backups = self.root/'backups'
        self.releases = self.root/'releases'
        self.backups.mkdir(); self.releases.mkdir()
        self.roots = [dict(category='backup', path=str(self.backups)),
                      dict(category='release', path=str(self.releases))]
        self.state = dict(packages=[], frontendPatches=[], backendPatches=[], jobs=[])

    def backup(self, name='full-id', point_type='FULL', date='2026-11-03T13:00:00Z'):
        folder = self.backups/'intruoyi'/'safe'/'57'/'archives'/name
        manifest = dict(schemaVersion='RepositoryManifest/v1', backupId=name, pointType=point_type,
                        createdAt=date, payloadRefs=[dict(path='/old/nas/'+name+'/data.bin', bytes=15, sha256='a'*64)],
                        parentPointPins=[], sourceIdentityPin={'sha256': 'b'*64})
        sha = write(folder/'.repository/manifest.json', manifest)
        write(folder/'.repository/point.json', dict(schemaVersion='RepositoryPoint/v1', backupId=name,
              pointType=point_type, manifestPin=dict(sha256=sha), integrityState='COMPLETE',
              controlledRestoreEligible=False, blockedReason='REPOSITORY_RECOVERY_NOT_RUN'))
        return folder

    def release(self, tag, kind=None):
        folder = self.releases/'intruoyi'/tag
        manifest = dict(applicationId='intruoyi', releaseTag=tag,
                        gitCommit='c'*40, files=[dict(name='images.tar', sha256='d'*64)])
        if kind: manifest['kind'] = kind
        write(folder/'manifest.json', manifest)
        (folder/'images.tar').write_bytes(b'actual-test-file')
        return folder

    def version_evidence(self, folder, tag='2026-11-03-12-15-42', image='sha256:'+'c'*64):
        manifest=json.loads((folder/'.repository/manifest.json').read_text(encoding='utf-8'))
        source='/private/archive-version/images.json'
        relative='semantic-capture/provided-'+hashlib.sha256(source.encode()).hexdigest()+'.bin'
        doc=folder/relative
        sha=write(doc,dict(releaseTag=tag,images={'intruoyi-backend':image}))
        pin=dict(path=source,bytes=doc.stat().st_size,sha256=sha)
        manifest['versionPins']=[pin]
        manifest['payloadRefs'].append(dict(pin,path='/original/archive/'+relative))
        inspects=folder/'recovery-materials/container-inspects.bin'
        sha=write(inspects,[dict(Name='/intruoyi-backend',Image='sha256:'+'c'*64,
                                Config=dict(Image='sha256:'+'c'*64,Env=['SECRET=never-expose']))])
        manifest['payloadRefs'].append(dict(path='/original/archive/recovery-materials/container-inspects.bin',
                                           bytes=inspects.stat().st_size,sha256=sha))
        self.repin(folder,manifest)
        return doc

    def repin(self, folder, manifest):
        sha=write(folder/'.repository/manifest.json',manifest)
        point=json.loads((folder/'.repository/point.json').read_text(encoding='utf-8'))
        point['manifestPin']['sha256']=sha
        write(folder/'.repository/point.json',point)

    def test_digest_backup_uses_pinned_program_version_and_retains_backup_identity(self):
        folder=self.backup('smallapp-unique')
        self.version_evidence(folder)
        row=scan_catalog(self.roots,self.state)['items'][0]
        self.assertEqual(row['version'],'2026-11-03-12-15-42')
        self.assertEqual(row['packageId'],'smallapp-unique')
        self.assertEqual(row['versionBasis'],'archive-version-pin+runtime-images')
        self.assertNotIn('never-expose',json.dumps(row))

    def test_missing_version_is_not_inferred_from_nearby_releases(self):
        self.backup();self.release('2026-11-03-12-15-42')
        row=next(x for x in scan_catalog(self.roots,self.state)['items'] if x['category']=='backup')
        self.assertIsNone(row['version'])

    def test_version_pin_tampering_and_runtime_mismatch_are_visible(self):
        for mode in ('tamper','runtime-mismatch','missing'):
            with self.subTest(mode=mode):
                folder=self.backup(mode)
                doc=self.version_evidence(folder,image='sha256:'+'d'*64 if mode=='runtime-mismatch' else 'sha256:'+'c'*64)
                if mode=='tamper':doc.write_text('{}',encoding='utf-8')
                if mode=='missing':doc.unlink()
                row=next(x for x in scan_catalog(self.roots,self.state)['items'] if x['packageId']==mode)
                self.assertIsNone(row['version'])
                self.assertEqual(row['status'],'indexed')
                self.assertEqual(row['versionStatus'],'invalid')
                self.assertTrue(row['issues'])

    def test_conflicting_archived_program_tags_are_not_silently_combined(self):
        folder=self.backup()
        write(folder/'recovery-materials/container-inspects.bin',[
            dict(Config=dict(Image='app/backend:2026-11-03-12-15-42')),
            dict(Config=dict(Image='app/frontend:2026-11-01-00-00-00'))])
        row=scan_catalog(self.roots,self.state)['items'][0]
        self.assertIsNone(row['version'])
        self.assertEqual(row['status'],'indexed')
        self.assertEqual(row['versionStatus'],'conflict')
        self.assertIn('BACKUP_PROGRAM_VERSION_CONFLICT',row['issues'])

    def test_pinned_legacy_version_without_optional_runtime_snapshot_is_explicit(self):
        folder=self.backup('legacy-version')
        self.version_evidence(folder)
        (folder/'recovery-materials/container-inspects.bin').unlink()
        manifest=json.loads((folder/'.repository/manifest.json').read_text(encoding='utf-8'))
        manifest['payloadRefs']=[p for p in manifest['payloadRefs'] if not p['path'].endswith('container-inspects.bin')]
        self.repin(folder,manifest)
        row=scan_catalog(self.roots,self.state)['items'][0]
        self.assertEqual(row['version'],'2026-11-03-12-15-42')
        self.assertEqual(row['versionBasis'],'archive-version-pin')
        self.assertEqual(row['status'],'indexed')

    def test_digest_only_source_record_is_not_a_readable_program_version(self):
        folder=self.backup('digest-only')
        self.version_evidence(folder,tag='sha256:'+'e'*64)
        row=scan_catalog(self.roots,self.state)['items'][0]
        self.assertIsNone(row['version'])
        self.assertEqual(row['status'],'indexed')
        self.assertEqual(row['versionStatus'],'unrecorded')

    def test_pinned_semver_and_historical_image_tag_are_readable_program_versions(self):
        for recorded,expected in [('v1.2.3','v1.2.3'),('intruoyi-backend:current-32ff79d-20261020','current-32ff79d-20261020')]:
            with self.subTest(recorded=recorded):
                folder=self.backup(expected);self.version_evidence(folder,tag=recorded)
                row=next(x for x in scan_catalog(self.roots,self.state)['items'] if x['packageId']==expected)
                self.assertEqual(row['version'],expected)

    def test_windows_long_archive_version_path_is_read_without_following_links(self):
        from package_catalog import backup_row
        folder=self.backup('long-version')
        self.version_evidence(folder)
        extended=self.root/('long-archive-'+'x'*140)
        native=Path('\\\\?\\'+str(extended)) if os.name=='nt' else extended
        import shutil
        shutil.copytree(folder,native)
        self.addCleanup(lambda:shutil.rmtree(native))
        self.assertEqual(backup_row(extended,{})['version'],'2026-11-03-12-15-42')

    def test_five_kinds_sorted_and_no_state_or_payload_mutation(self):
        self.backup()
        self.backup('incremental-id', 'INCREMENTAL', '2026-11-04T13:00:00Z')
        for tag, kind in [('2026-11-01-00-00-00', None), ('2026-11-02-00-00-00', 'frontend-patch'),
                          ('2026-11-03-00-00-00', 'backend-patch')]: self.release(tag, kind)
        before = copy.deepcopy(self.state)
        result = scan_catalog(self.roots, self.state)
        self.assertTrue(result['complete'])
        self.assertEqual({x['kind'] for x in result['items']},
                         {'backup-full','backup-incremental','release-full','frontend-patch','backend-patch'})
        self.assertEqual(result['items'][0]['packageId'], 'incremental-id')
        self.assertEqual(self.state, before)
        backup = next(x for x in result['items'] if x['kind']=='backup-full')
        self.assertEqual(backup['sizeBytes'],15)
        self.assertEqual(backup['verification'],'metadata-only')
        self.assertFalse(backup['restoreVerified'])
        self.assertIn('57', backup['servers'][0])

    def test_nas_packages_are_discovered_without_local_history_and_duplicate_roots_dedup(self):
        folder=self.release('2026-11-02-00-00-00')
        result=scan_catalog(self.roots+[self.roots[1]],self.state)
        self.assertEqual(len(result['items']),1)
        self.assertFalse(result['items'][0]['registered'])
        self.assertEqual(result['items'][0]['nasPaths'],[str(folder)])

    def test_missing_known_package_is_explicit_not_discarded_or_available(self):
        self.state['packages']=[dict(releaseTag='2026-11-03-00-00-00',nasDirectory=str(self.releases/'gone'),
             manifestSha256='a'*64, applicationId='intruoyi')]
        result=scan_catalog(self.roots,self.state)
        self.assertEqual(result['items'][0]['status'],'missing')
        self.assertTrue(result['items'][0]['registered'])

    def test_unavailable_root_is_visible_and_other_sources_still_reported(self):
        self.backup()
        result=scan_catalog(self.roots+[dict(category='release',path=str(self.root/'absent'))],self.state)
        self.assertFalse(result['complete'])
        self.assertTrue(result['errors'])
        self.assertEqual(len(result['items']),1)

    def test_manifest_pin_mismatch_and_missing_point_are_not_complete(self):
        a=self.backup('mismatch');b=self.backup('unpublished')
        write(a/'.repository/point.json',dict(backupId='mismatch',manifestPin={'sha256':'f'*64}))
        (b/'.repository/point.json').unlink()
        rows=scan_catalog(self.roots,self.state)['items']
        self.assertEqual({x['status'] for x in rows},{'invalid','unpublished'})

    def test_release_missing_file_and_traversal_are_rejected_without_reading_outside_root(self):
        a=self.release('2026-11-03-00-00-00');(a/'images.tar').unlink()
        b=self.release('2026-11-04-00-00-00')
        write(b/'manifest.json',dict(applicationId='intruoyi',releaseTag=b.name,
              files=[dict(name='../outside-private.json')],password='never-public'))
        result=scan_catalog(self.roots,self.state)
        self.assertEqual({x['status'] for x in result['items']},{'incomplete','invalid'})
        self.assertNotIn('never-public',json.dumps(result))

    def test_same_id_different_manifests_marks_conflict_and_retains_both_paths(self):
        a=self.release('2026-11-03-00-00-00')
        other=self.releases/'copy'
        write(other/'manifest.json',dict(applicationId='intruoyi',releaseTag=a.name,files=[]))
        result=scan_catalog(self.roots,self.state)
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['status'],'conflict')
        self.assertEqual(len(result['items'][0]['nasPaths']),2)

    def test_backup_payload_tree_is_not_traversed_and_unknown_archive_is_visible(self):
        a=self.backup()
        write(a/'payload/pretend-package/manifest.json',dict(applicationId='do-not-scan',releaseTag='hidden'))
        orphan=self.backups/'archives/orphan';orphan.mkdir(parents=True)
        (orphan/'data.tar').write_bytes(b'data')
        result=scan_catalog(self.roots,self.state)
        self.assertEqual(len(result['items']),2)
        self.assertIn('unknown',{x['kind'] for x in result['items']})
        self.assertNotIn('do-not-scan',json.dumps(result))

    def test_catalog_route_is_authenticated_application_scoped_and_get_only(self):
        registry=ApplicationRegistry(dict(defaultApplication='intruoyi',applications=[dict(id='intruoyi',
             name='IntRuoyi',repo='test',scope='read-only catalogue',status='ready',
             executorUrl='http://127.0.0.1:18112',bridgeKey='test-only')]))
        for route in ['/applications/intruoyi/package-catalog','/applications/intruoyi/package-catalog?refresh=1']:
            self.assertEqual(registry.resolve(route,'GET')[1],route.removeprefix('/applications/intruoyi'))
        for route,method in [('/applications/intruoyi/package-catalog','POST'),
                             ('/applications/intruoyi/package-catalog?path=/private','GET')]:
            with self.assertRaises(RegistryError):registry.resolve(route,method,{})

    def test_metadata_symlinks_do_not_leave_the_approved_package(self):
        import os
        import subprocess
        folder=self.backup('linked')
        private=self.root/'private'
        write(private/'manifest.json',dict(schemaVersion='RepositoryManifest/v1',backupId='private-data-must-not-appear'))
        (folder/'.repository/manifest.json').unlink()
        (folder/'.repository/point.json').unlink()
        (folder/'.repository').rmdir()
        if os.name=='nt':
            subprocess.run(['cmd','/c','mklink','/J',str(folder/'.repository'),str(private)],check=True,capture_output=True)
        else:(folder/'.repository').symlink_to(private,target_is_directory=True)
        result=scan_catalog(self.roots,self.state)
        self.assertEqual(result['items'][0]['status'],'invalid')
        self.assertNotIn('private-data-must-not-appear',json.dumps(result))

    def test_partial_metadata_does_not_claim_an_integrity_complete_restore_point(self):
        folder=self.backup('partial')
        point=json.loads((folder/'.repository/point.json').read_text(encoding='utf-8'))
        point['schemaVersion']='Unrecognized/v1'
        write(folder/'.repository/point.json',point)
        self.assertEqual(scan_catalog(self.roots,self.state)['items'][0]['status'],'invalid')

    def test_sealed_nas_release_is_not_misreported_as_missing_extracted_files(self):
        folder=self.release('2026-11-03-00-00-00')
        (folder/'images.tar').unlink()
        (folder/'release.tar').write_bytes(b'sealed archive is not read by this metadata list')
        row=scan_catalog(self.roots,self.state)['items'][0]
        self.assertEqual(row['status'],'indexed')
        self.assertEqual(row['sizeBytes'],(folder/'release.tar').stat().st_size)
        self.assertEqual(row['sizeBasis'],'sealed-archive-stat')


if __name__=='__main__':unittest.main()
