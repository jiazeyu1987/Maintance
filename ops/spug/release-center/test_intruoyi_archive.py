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

from intruoyi_runtime import Runtime, RuntimeBlocked, file_sha, package_identity
import intruoyi_runtime_agent as agent
from intruoyi_runtime_agent import unpack_original_package


class OriginalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'stage'
        self.root.mkdir()

    def package(self, artifacts=None, extra=None, change=None, omit=None):
        artifacts = artifacts or {'images.tar': b'original image archive', 'sql/a.sql': b'SELECT 1;'}
        manifest = {'releaseTag': '2026-10-22-21-00-00', 'images':{'backend':{'id':'backend-image'}, 'frontend':{'id':'frontend-image'}}, 'files': [
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
        self.assertEqual(remote_call.call_args_list[0].kwargs['files'], manifest['files'])
        self.assertEqual(remote_call.call_args_list[-1].args, ('test', 'verify-stage'))
        self.assertEqual(remote_call.call_args_list[-1].kwargs['archive'], evidence)

    def reusable_stage(self):
        self.root = self.root.rename(self.root.with_name('2026-10-22-21-00-00'))
        manifest, evidence = self.package()
        archive = unpack_original_package(self.root, manifest, evidence)
        payload = dict(manifest=manifest, archive=evidence, files=manifest['files'], validatedPreflights=[])
        (self.root/'stage-verified.json').write_text(json.dumps(dict(manifestSha256=package_identity(manifest),
            files=manifest['files'], archive=archive, validatedPreflights=[])))
        return payload

    def test_existing_verified_stage_is_read_only_and_does_not_upload(self):
        payload = self.reusable_stage()
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        with patch.object(agent.remote, 'run', side_effect=lambda args: args[-1].encode()) as commands:
            result = agent.reuse_verified_stage(self.root, payload)
        self.assertTrue(result['verified'] and result['reused'])
        self.assertTrue(all(call.args[0][1:3] == ['image','inspect'] for call in commands.call_args_list))
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()})
        runtime = Runtime({'targets':{'test':dict(host='example.invalid', python='/usr/bin/python3',
            entryUrl='http://example.invalid', frontend='front', backend='back', database='db', stagingRoot='/release')}})
        result['directory'] = '/release/' + payload['manifest']['releaseTag']
        with patch.object(runtime, 'call', return_value=result) as calls, patch('intruoyi_runtime.subprocess.run') as transfer:
            self.assertEqual(runtime.stage('test', self.root, payload['manifest']), result)
        transfer.assert_not_called()
        calls.assert_called_once()
        self.assertEqual(calls.call_args.args, ('test','stage-directory'))

    def test_deployment_or_unknown_artifacts_refuse_reuse(self):
        payload = self.reusable_stage()
        for name in ('deployment-progress.private.json','recovery.sql','deployment-pending.json',
                     'backend-before-initial.private.json','unknown'):
            with self.subTest(name=name):
                marker = self.root/name
                marker.write_text('{}')
                with patch.object(agent.remote, 'run') as commands, self.assertRaisesRegex(RuntimeBlocked, 'deployment evidence'):
                    agent.reuse_verified_stage(self.root, payload)
                commands.assert_not_called()
                marker.unlink()

    def test_incomplete_changed_package_receipt_and_image_refuse_reuse(self):
        payload = self.reusable_stage()
        for name in ('release.tar','manifest.json','sql/a.sql','stage-verified.json'):
            with self.subTest(name=name):
                path = self.root/name
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(RuntimeBlocked, 'incomplete'):
                    agent.reuse_verified_stage(self.root, payload)
                path.write_bytes(original + b' ')
                with self.assertRaises(RuntimeBlocked):
                    if name == 'stage-verified.json':
                        altered = json.loads(original); altered['manifestSha256'] = '0'*64
                        path.write_text(json.dumps(altered))
                    agent.reuse_verified_stage(self.root, payload)
                path.write_bytes(original)
        with patch.object(agent.remote, 'run', return_value=b'wrong-image'), self.assertRaisesRegex(RuntimeBlocked, 'image identity'):
            agent.reuse_verified_stage(self.root, payload)

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
