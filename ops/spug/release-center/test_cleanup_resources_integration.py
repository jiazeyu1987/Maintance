"""Opt-in real local Docker engine + real files; no business/remote resources."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

import artifact_files as files


@unittest.skipUnless(os.environ.get('SPUG_REAL_CLEANUP_TEST')=='1','Explicit local Docker integration invocation required')
class RealEngineTests(unittest.TestCase):
    def test_real_retired_container_image_and_files_are_removed_current_checkpoint_survives(self):
        prefix='spug-cleanup-test-'+uuid.uuid4().hex[:10]
        owned=[];reference=prefix+':retired'
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            try:
                context=base/'build';context.mkdir();(context/'payload').write_bytes(b'integration owned image')
                (context/'Dockerfile').write_text('FROM scratch\nCOPY payload /payload\nCMD ["/unused"]\n','utf-8')
                files.docker(['build','--pull=false','-q','-t',reference,str(context)])
                image=json.loads(files.docker(['image','inspect',reference]))[0]['Id']
                current='2026-11-02-01-00-00';old='2026-10-30-01-00-00';job='JOB-0123456789'
                for role in ('app','web'):
                    name=prefix+'-'+role
                    identity=files.docker(['run','-d','--pull=never','--name',name,'python:3.12-bookworm',
                        'python','-c','import time; time.sleep(300)']).decode().strip()
                    owned.append(identity)
                backend,frontend=[json.loads(files.docker(['inspect',c]))[0] for c in owned]
                metadata=base/'release-info.json';metadata.write_text(json.dumps(dict(releaseTag=current)),'utf-8')
                files.docker(['exec',frontend['Id'],'mkdir','-p','/usr/share/nginx/html'])
                files.docker(['cp',str(metadata),frontend['Id']+':/usr/share/nginx/html/release-info.json'])
                identity=files.docker(['create','--name',prefix+'-app-before-'+old,reference]).decode().strip();owned.append(identity)
                original=json.loads(files.docker(['inspect',identity]))[0];original['Name']='/'+prefix+'-app'
                root=base/old;root.mkdir()
                manifest=dict(releaseTag=old,images=dict(backend=dict(name=reference,id=image)),files=[])
                (root/'manifest.json').write_text(json.dumps(manifest),'utf-8')
                (root/'backend-before-initial.private.json').write_text(json.dumps(original),'utf-8')
                (root/'release.tar').write_bytes(b'original package bytes')
                entry=dict(manifest=manifest,manifestSha256=files.sha(root/'manifest.json'),
                    packageSha256=files.sha(root/'release.tar'),ownerJobIds=[job])
                checkpoint=base/current;checkpoint.mkdir();(checkpoint/'recovery.sql.gz').write_bytes(b'protected checkpoint')
                payload=dict(action='artifact-auto-clean',workflowJobId=job,entries=[entry],resourceEntries=[entry],
                    protectedTags=[current],currentReleaseTag=current,currentPatchTag=None,
                    expectedImages=dict(backend=backend['Image'],frontend=frontend['Image']))
                report=files.automatic_cleanup(dict(stagingRoot=str(base),backend=prefix+'-app',frontend=prefix+'-web'),payload)
                self.assertEqual(report['status'],'succeeded',report)
                self.assertNotIn(identity,files.docker(['ps','-aq','--no-trunc']).decode().split())
                self.assertNotIn(reference,files.docker_inventory()[0])
                self.assertFalse((root/'release.tar').exists())
                self.assertTrue((checkpoint/'recovery.sql.gz').exists())
                self.assertTrue((root/'manifest.json').exists())
                self.assertEqual([r['kind'] for r in report['removed']],['container','image','file'])
                self.assertTrue(report['plan']['containers'])
                retry=files.automatic_cleanup(dict(stagingRoot=str(base),backend=prefix+'-app',frontend=prefix+'-web'),payload)
                self.assertEqual(retry['status'],'succeeded',retry)
                self.assertEqual(retry['removed'],[])
            finally:
                for identity in owned:
                    # Only fixture-created IDs. No volume removal or global prune.
                    import subprocess
                    subprocess.run(['docker','stop','--time','1',identity],capture_output=True)
                    subprocess.run(['docker','rm',identity],capture_output=True)
                import subprocess
                subprocess.run(['docker','image','rm',reference],capture_output=True)


if __name__=='__main__':unittest.main()
