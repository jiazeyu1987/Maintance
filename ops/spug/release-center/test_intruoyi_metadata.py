import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import intruoyi_metadata


class HistoricalMetadataGitTest(unittest.TestCase):
    def test_historical_commit_lookup_trusts_only_the_registered_source_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'package'
            folder.mkdir()
            manifest = {
                'releaseTag': 'current-32ff79d-20261020',
                'sourceCommit': '32ff79dec7bee877df7a65d896c6143ae6d53523',
                'builtAt': '2026-10-20T00:00:00+08:00',
                'packageSha256': 'archive',
                'frontendImage': 'sha256:' + 'a' * 64,
                'backendImage': 'sha256:' + 'b' * 64,
            }
            (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            (folder / 'images.tar').write_bytes(b'archive')
            config = {
                'packageDirectory': str(folder),
                'manifestSha256': 'manifest-hash',
                'sourceRepository': str(root / 'repo'),
            }
            (root / 'repo').mkdir()
            completed = Mock(returncode=0, stdout=b'historical commit title', stderr=b'')
            with patch.object(intruoyi_metadata, 'digest', side_effect=['manifest-hash', 'archive']), \
                    patch.object(intruoyi_metadata, 'archive_image_identities'), \
                    patch.object(intruoyi_metadata.subprocess, 'run', return_value=completed) as run:
                unused_manifest, unused_images, info = intruoyi_metadata.reference(config)

            args = run.call_args.args[0]
            self.assertEqual(args[1], '-c')
            self.assertEqual(args[2], 'safe.directory=' + (root / 'repo').resolve().as_posix())
            self.assertEqual(args[3:5], ['-C', str((root / 'repo').resolve())])
            self.assertEqual(args[-1], manifest['sourceCommit'])
            self.assertEqual(info['changeSet']['gitChanges'], [manifest['sourceCommit'][:12] + ' historical commit title'])


if __name__ == '__main__':
    unittest.main()
