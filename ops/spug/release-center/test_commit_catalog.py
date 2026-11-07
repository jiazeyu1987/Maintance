"""Real Git coverage for committed branch choices without mutating the workspace."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from executor import Executor


class CommitCatalogTests(unittest.TestCase):
    def test_release_branch_commit_is_selectable_without_switching_dirty_main(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            def git(*args):
                return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode('utf-8').strip()
            git('init','-b','int_main')
            git('config','user.name','Release catalog test');git('config','user.email','release-test@example.invalid')
            git('config','commit.gpgsign','false')
            file=root/'program.txt';file.write_text('base\n',encoding='utf-8');git('add','program.txt');git('commit','-m','base')
            git('checkout','-b','release-isolation')
            file.write_text('committed release\n',encoding='utf-8');git('commit','-am','release')
            target=git('rev-parse','HEAD');git('checkout','int_main')
            file.write_text('uncommitted main changes\n',encoding='utf-8')
            executor=object.__new__(Executor);executor.c={'repo':str(root)}
            rows=executor.commits()
            self.assertIn(target,[row['commit'] for row in rows])
            self.assertEqual(len(rows),2)
            self.assertEqual(git('branch','--show-current'),'int_main')
            self.assertEqual(file.read_text('utf-8'),'uncommitted main changes\n')
