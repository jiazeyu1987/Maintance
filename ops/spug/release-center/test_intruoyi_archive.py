"""Actual archive extraction and integrity checks; no SSH or target deployment."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from intruoyi_runtime import Runtime, RuntimeBlocked, file_sha
from intruoyi_runtime_agent import unpack_original_package


class OriginalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'stage'
        self.root.mkdir()

    def package(self, artifacts=None, extra=None, change=None, omit=None):
        artifacts = artifacts or {'images.tar': b'original image archive', 'sql/a.sql': b'SELECT 1;'}
        manifest = {'releaseTag': '2026-10-22-21-00-00', 'files': [
            {'name': name, 'sha256': hashlib.sha256(data).hexdigest()} for name, data in artifacts.items()]}
        manifest_bytes = json.dumps(manifest, ensure_ascii=False).encode()
        members = {'manifest.json': manifest_bytes, **artifacts}
        with tarfile.open(self.root / 'release.tar', 'w') as archive:
            for name, data in members.items():
                if name == omit:
                    continue
                member = tarfile.TarInfo(name)
                member.size = len(data)
                if change:
                    member, data = change(member, data)
                archive.addfile(member, io.BytesIO(data) if member.isfile() else None)
            if extra:
                member, data = extra
                archive.addfile(member, io.BytesIO(data))
        return manifest, {'sha256': file_sha(self.root / 'release.tar'),
                          'manifestSha256': hashlib.sha256(manifest_bytes).hexdigest()}

    def test_original_870_artifacts_extract_with_exact_content_and_identity(self):
        artifacts = {'sql/migration-%04d.sql' % index: ('SELECT %d;' % index).encode() for index in range(869)}
        artifacts['images.tar'] = b'immutable original images'
        manifest, evidence = self.package(artifacts)
        result = unpack_original_package(self.root, manifest, evidence)
        self.assertEqual(result['fileCount'], 871)
        self.assertEqual(result['archiveSha256'], evidence['sha256'])
        self.assertEqual(json.loads((self.root / 'manifest.json').read_text()), manifest)
        for name, content in artifacts.items():
            self.assertEqual((self.root / name).read_bytes(), content)
        self.assertEqual(file_sha(self.root / 'release.tar'), evidence['sha256'])

    def test_stage_uploads_exact_original_archive_once(self):
        manifest, evidence = self.package()
        # Supply the already verified local package contents used by stage validation.
        unpack_original_package(self.root, manifest, evidence)
        runtime = Runtime({'targets': {'test': dict(host='example.invalid', python='/usr/bin/python3',
                          entryUrl='http://example.invalid', frontend='front', backend='back',
                          database='db', stagingRoot='/release')}})
        with patch.object(runtime, 'call', return_value={'verified': True}) as remote_call, \
                patch('intruoyi_runtime.subprocess.run', return_value=subprocess.CompletedProcess('scp', 0)) as transfer:
            self.assertEqual(runtime.stage('test', str(self.root), manifest), {'verified': True})
        transfer.assert_called_once()
        self.assertEqual(transfer.call_args.args[0][-2], str(self.root / 'release.tar'))
        self.assertEqual(remote_call.call_args_list[0].kwargs['files'], [])
        self.assertEqual(remote_call.call_args_list[-1].args, ('test', 'verify-stage'))
        self.assertEqual(remote_call.call_args_list[-1].kwargs['archive'], evidence)

    def test_transport_corruption_blocks_before_extraction(self):
        manifest, evidence = self.package()
        with (self.root / 'release.tar').open('ab') as output:
            output.write(b'changed')
        with self.assertRaisesRegex(RuntimeBlocked, 'archive checksum'):
            unpack_original_package(self.root, manifest, evidence)
        self.assertFalse((self.root / 'manifest.json').exists())

    def test_manifest_identity_mismatch_blocks_before_extraction(self):
        manifest, evidence = self.package()
        manifest['releaseTag'] = '2026-10-22-22-00-00'
        with self.assertRaisesRegex(RuntimeBlocked, 'manifest identity'):
            unpack_original_package(self.root, manifest, evidence)
        self.assertFalse((self.root / 'manifest.json').exists())

    def test_artifact_corruption_never_produces_verified_stage(self):
        def change(member, data):
            return member, (b'x' * len(data) if member.name == 'images.tar' else data)
        manifest, evidence = self.package(change=change)
        with self.assertRaisesRegex(RuntimeBlocked, 'artifact checksum'):
            unpack_original_package(self.root, manifest, evidence)
        self.assertFalse((self.root / 'stage-verified.json').exists())

    def test_missing_member_blocks_before_extraction(self):
        manifest, evidence = self.package(omit='sql/a.sql')
        with self.assertRaisesRegex(RuntimeBlocked, 'member list'):
            unpack_original_package(self.root, manifest, evidence)
        self.assertFalse((self.root / 'manifest.json').exists())

    def test_extra_duplicate_absolute_and_traversal_members_are_rejected(self):
        for name in ('unexpected', 'images.tar', '../escaped', '/absolute'):
            with self.subTest(name=name):
                extra = tarfile.TarInfo(name)
                extra.size = 1
                manifest, evidence = self.package(extra=(extra, b'x'))
                with self.assertRaisesRegex(RuntimeBlocked, 'member list'):
                    unpack_original_package(self.root, manifest, evidence)
                self.assertFalse((self.root / 'manifest.json').exists())

    def test_manifest_cannot_authorize_unsafe_paths(self):
        for name in ('../escaped', '/absolute', './noncanonical', 'a//b', 'release.tar'):
            with self.subTest(name=name):
                manifest, evidence = self.package(artifacts={name: b'x'})
                with self.assertRaisesRegex(RuntimeBlocked, 'Unsafe'):
                    unpack_original_package(self.root, manifest, evidence)
                self.assertFalse((self.root / 'manifest.json').exists())

    def test_links_directories_and_special_files_are_rejected_before_extraction(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            def change(member, data):
                if member.name == 'images.tar':
                    member.type, member.size, member.linkname = kind, 0, '../escaped'
                return member, data
            with self.subTest(kind=kind):
                manifest, evidence = self.package(change=change)
                with self.assertRaises(RuntimeBlocked):
                    unpack_original_package(self.root, manifest, evidence)
                self.assertFalse((self.root / 'manifest.json').exists())


if __name__ == '__main__':
    unittest.main()
