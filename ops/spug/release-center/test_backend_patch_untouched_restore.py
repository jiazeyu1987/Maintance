"""Explicit restoration when transport ended before the switch receipt existed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import backend_patch_agent as agent


class UntouchedRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)/'backend-patches';self.tag='2026-11-03-08-23-17'
        self.original=self.base/self.tag/'JOB-1111111111';self.original.mkdir(parents=True)
        self.root=self.base/self.tag/'JOB-2222222222'
        self.before={'backendJarSha256':'original','components':{'backend':{'containerId':'original'}}}
        self.manifest={'releaseTag':self.tag,'baseline':{'origins':{'test':self.before}},'files':[]}
        (self.original/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')
        (self.original/'release.tar').write_bytes(b'sealed archive')
        self.payload=dict(originalJobId='JOB-1111111111',workflowJobId='JOB-2222222222',manifest=self.manifest,
                          archive={'sha256':hashlib.sha256(b'sealed archive').hexdigest()})
        self.profile={'environment':'test','backend':'backend','writers':['backend']}
        self.remote=Mock();self.remote.sql.return_value='0\t0'
        self.a={'remote':self.remote,'verify_files':Mock(),
                'file_sha':lambda p:hashlib.sha256(p.read_bytes()).hexdigest()}
        self.payload['archive']['manifestSha256']=self.a['file_sha'](self.original/'manifest.json')

    def test_exact_untouched_origin_records_verification_without_container_or_database_changes(self):
        with patch.object(agent,'require_no_other_stdin_workers'),patch.object(agent,'observation',return_value=self.before):
            result=agent.restore(self.profile,self.payload,self.a,self.base,self.root)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(result['mode'],'verified-untouched-origin')
        self.assertFalse(result['databaseRestored'])
        self.remote.run.assert_not_called()
        self.assertEqual(self.remote.sql.call_args.args[1],'SELECT @@global.read_only,@@global.super_read_only;')
        self.assertEqual(json.loads((self.root/'restoration.json').read_text('utf-8')),result)

    def test_unknown_worker_or_origin_drift_cannot_be_closed_as_untouched(self):
        for reason in ('worker','origin','fence','archive','manifest'):
            with self.subTest(reason=reason):
                worker=ValueError('Other agent may still execute') if reason=='worker' else None
                actual=dict(self.before,backendJarSha256='different') if reason=='origin' else self.before
                self.remote.sql.return_value='1\t1' if reason=='fence' else '0\t0'
                self.payload['archive']['sha256']='f'*64 if reason=='archive' else hashlib.sha256(b'sealed archive').hexdigest()
                self.payload['archive']['manifestSha256']='f'*64 if reason=='manifest' else self.a['file_sha'](self.original/'manifest.json')
                with patch.object(agent,'require_no_other_stdin_workers',side_effect=worker),patch.object(agent,'observation',return_value=actual):
                    with self.assertRaises(ValueError):agent.restore(self.profile,self.payload,self.a,self.base,self.root)
                self.assertFalse(self.root.exists())
                self.remote.run.assert_not_called()

    def test_partial_switch_evidence_cannot_enter_the_untouched_path(self):
        for name in ('database-fence.json','backend-origin.private.json','unknown.json'):
            with self.subTest(name=name):
                path=self.original/name;path.write_text('{}',encoding='utf-8')
                with patch.object(agent,'require_no_other_stdin_workers'),patch.object(agent,'observation',return_value=self.before):
                    with self.assertRaises(ValueError):agent.restore(self.profile,self.payload,self.a,self.base,self.root)
                path.unlink()
                self.assertFalse(self.root.exists())


class WorkerInventoryTests(unittest.TestCase):
    def test_only_current_python_stdin_worker_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for pid,command in ((101,b'/usr/bin/python3\0-\0'),(102,b'/usr/bin/java\0-jar\0app.jar\0')):
                (root/str(pid)).mkdir();(root/str(pid)/'cmdline').write_bytes(command)
            agent.require_no_other_stdin_workers(root,current_pid=101)
            (root/'103').mkdir();(root/'103/cmdline').write_bytes(b'/usr/bin/python3\0-\0')
            with self.assertRaises(ValueError):agent.require_no_other_stdin_workers(root,current_pid=101)


if __name__=='__main__':unittest.main()
