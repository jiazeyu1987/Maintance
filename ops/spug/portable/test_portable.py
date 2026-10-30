import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import sys
import threading
from import_local import replace_paths, verify
from disable_legacy_workers import disable
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'release-center'))
from intruoyi_runtime import Runtime, RuntimeBlocked
from intruoyi_executor import IntRuoyiExecutor


class PortableTests(unittest.TestCase):
    def test_imported_spug_does_not_replay_original_jobs(self):
        original=''.join('[program:'+name+']\ncommand = test\nautostart = true\n' for name in
                         ('nginx','spug-worker','spug-monitor','spug-scheduler','release-center-bridge'))
        result=disable(original)
        self.assertEqual(result.count('autostart = false'),3)
        self.assertEqual(result.count('autostart = true'),2)
        self.assertEqual(disable(result),result)
        with self.assertRaises(RuntimeError):disable('')

    def test_omitted_history_cannot_be_published_or_recovered(self):
        executor=IntRuoyiExecutor.__new__(IntRuoyiExecutor)
        executor.c={'applicationId':'intruoyi'}
        executor.lock=threading.RLock()
        executor.state={'jobs':[{'id':'old-job','releaseTag':'old'}],
                        'packages':[{'releaseTag':'old','portableLocalOmission':True}]}
        for action,selection in [('promote-prod',{'releaseTag':'old'}),('recover-release',{'jobId':'old-job'})]:
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'当前电脑未携带'):
                executor.submit(action,dict(applicationId='intruoyi',requestId='portable-check-1',**selection),'test')

    def test_console_uses_imported_key_and_known_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            key=Path(tmp)/'key';hosts=Path(tmp)/'known_hosts'
            key.touch();hosts.touch()
            runtime=Runtime.__new__(Runtime)
            runtime.config={'executionMode':'portable-console','sshIdentityFile':str(key),'sshKnownHostsFile':str(hosts)}
            options=runtime.ssh_options()
            self.assertEqual(options[options.index('-i')+1],str(key))
            self.assertIn('UserKnownHostsFile='+str(hosts),options)
            key.unlink()
            with self.assertRaises(RuntimeBlocked):runtime.ssh_options()

    def test_only_path_prefixes_are_rebased(self):
        source={'path':r'C:\old\packages\a', 'nested':['C:/old/b'], 'unrelated':'C:/older/b', 'log':'log C:/old/a'}
        self.assertEqual(replace_paths(source,[('C:/old','E:/new')]),
            {'path':'E:/new/packages/a','nested':['E:/new/b'],'unrelated':'C:/older/b','log':'log C:/old/a'})

    def test_state_and_checksum_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'private').mkdir()
            file=root/'private/state.snapshot.sqlite3'
            with contextlib.closing(sqlite3.connect(file)) as db:
                db.execute('CREATE TABLE release_state (id INTEGER,payload TEXT)')
                db.execute('INSERT INTO release_state VALUES(1,?)',(json.dumps({'jobs':[],'packages':[]}),))
                db.commit()
            (root/'integrity.json').write_text(json.dumps({'files':{'private/state.snapshot.sqlite3':hashlib.sha256(file.read_bytes()).hexdigest()}}))
            with contextlib.redirect_stdout(io.StringIO()): verify(root)
            with file.open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):verify(root)

    def test_active_job_is_not_transferable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'private').mkdir()
            with contextlib.closing(sqlite3.connect(root/'private/state.snapshot.sqlite3')) as db:
                db.execute('CREATE TABLE release_state (id INTEGER,payload TEXT)')
                db.execute('INSERT INTO release_state VALUES(1,?)',(json.dumps({'jobs':[{'status':'running'}],'packages':[]}),))
                db.commit()
            (root/'integrity.json').write_text(json.dumps({'files':{}}))
            with self.assertRaisesRegex(ValueError,'active'):verify(root)

    def test_manifest_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'integrity.json').write_text(json.dumps({'files':{'../outside':'invalid'}}))
            with self.assertRaisesRegex(ValueError,'escapes'):verify(root)


if __name__=='__main__':unittest.main()
