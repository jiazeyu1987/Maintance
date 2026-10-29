import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from executor import digest
import nas_package_retry as retry


class OriginalPackageRetryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tag = '2026-10-29-13-43-28'
        self.folder = self.root / 'packages' / self.tag
        self.folder.mkdir(parents=True)
        (self.folder / 'images.tar').write_bytes(b'original-image-content')
        self.manifest = dict(applicationId='app', releaseTag=self.tag, IMAGE_TAG=self.tag,
                             gitCommit='a'*40, files=[dict(name='images.tar', sha256=digest(self.folder/'images.tar'))])
        (self.folder / 'manifest.json').write_text(json.dumps(self.manifest), 'utf-8')
        with tarfile.open(self.folder / 'release.tar', 'w') as archive:
            for name in ('manifest.json', 'images.tar'):
                archive.add(self.folder / name, arcname=name)
        self.original = dict(id='build', action='build-release', status='failed',
                             currentStep='publish-original-package-to-nas', releaseTag=self.tag,
                             payload=dict(commit='a'*40))
        self.nas = self.root / 'nas'

    def test_complete_archive_is_verified_and_identity_is_fixed(self):
        package, _ = retry.verify_sealed_package(self.folder, 'app', self.original)
        self.assertEqual(package['packageSha256'], digest(self.folder/'release.tar'))
        self.original['payload']['commit'] = 'b'*40
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            retry.verify_sealed_package(self.folder, 'app', self.original)

    def test_tampered_local_member_is_rejected(self):
        (self.folder / 'images.tar').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Local sealed artifact'):
            retry.verify_sealed_package(self.folder, 'app', self.original)

    def test_truncated_archive_is_rejected(self):
        with tarfile.open(self.folder / 'release.tar', 'w') as archive:
            archive.add(self.folder/'manifest.json', arcname='manifest.json')
        with self.assertRaisesRegex(ValueError, 'Incomplete sealed archive'):
            retry.verify_sealed_package(self.folder, 'app', self.original)

    def test_sealed_hash_checkpoint_prevents_replacement(self):
        package, _ = retry.verify_sealed_package(self.folder, 'app', self.original)
        self.original['sealedPackage'] = dict(package, packageSha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'Original sealed package changed'):
            retry.verify_sealed_package(self.folder, 'app', self.original)

    def test_matching_partial_can_be_republished_and_completed_copy_reused(self):
        destination = self.nas / self.tag
        destination.mkdir(parents=True)
        (destination/'release.tar.partial').write_bytes((self.folder/'release.tar').read_bytes()[:1024])
        retry.republish(self.folder, self.manifest, self.nas)
        retry.republish(self.folder, self.manifest, self.nas)
        self.assertEqual(digest(destination/'release.tar'), digest(self.folder/'release.tar'))
        self.assertFalse((destination/'release.tar.partial').exists())

    def test_unrelated_partial_is_not_overwritten(self):
        destination = self.nas / self.tag
        destination.mkdir(parents=True)
        partial = destination/'release.tar.partial'
        partial.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            retry.republish(self.folder, self.manifest, self.nas)
        self.assertEqual(partial.read_bytes(), b'foreign')

    def test_only_post_seal_failed_build_is_eligible(self):
        state = dict(jobs=[self.original])
        self.assertIs(retry.original_build(state, self.original), self.original)
        self.original['currentStep'] = 'compile-backend'
        with self.assertRaisesRegex(ValueError, 'sealed before NAS'):
            retry.original_build(state, self.original)

    def test_failed_transfer_keeps_package_unregistered_and_explicit_retry_completes(self):
        job = dict(id='retry1', action='resolve-task', status='running', releaseTag=self.tag,
                   actor='operator', payload=dict(decision='retry', note='verified original package'))
        state = dict(packages=[], jobs=[job, self.original])
        executor = SimpleNamespace(root=self.root, c=dict(applicationId='app', nasPath=str(self.nas)),
                                   state=state, save=lambda: None, step=lambda *args: None, log=lambda *args: None)
        with patch.object(retry, 'connect_nas'), patch.object(retry, 'republish', side_effect=OSError(22, 'Invalid argument')):
            with self.assertRaisesRegex(RuntimeError, 'republication failed'):
                retry.resume(executor, job, self.original)
        self.assertEqual(state['packages'], [])
        self.assertNotIn('resolution', self.original)
        job['status'] = 'failed'
        next_job = dict(job, id='retry2', status='running')
        state['jobs'].insert(0, next_job)
        with patch.object(retry, 'connect_nas'):
            retry.resume(executor, next_job, job)
        self.assertEqual(len(state['packages']), 1)
        self.assertEqual(self.original['status'], 'failed')
        self.assertEqual(self.original['resolution']['jobId'], 'retry2')
        self.assertEqual(job['resolution']['jobId'], 'retry2')


if __name__ == '__main__':
    unittest.main()
