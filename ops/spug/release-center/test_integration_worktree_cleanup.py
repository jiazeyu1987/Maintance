import json, subprocess, sys
from pathlib import Path
from test_build_worktree_cleanup import BuildWorktreeCleanupTest


class IntegrationCleanupTest(BuildWorktreeCleanupTest):
    def invoke(self):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('integration_worktree_cleanup.py')),
            '--repo',str(self.repo),'--worktree',str(self.worktree),'--root',str(self.build_root),
            '--commit',self.commit,'--branch','codex/integration','--merged-into','HEAD',
            '--proof',str(self.root/'cleanup-proof.json')],capture_output=True)

    def test_cli_merged_branch_long_path(self):
        self.git('-C',str(self.worktree),'switch','-c','codex/integration')
        p=self.worktree/'IntRuoyiBackend/module/target'
        for i in range(8):p=p/('generated-'+str(i)+'x'*30)
        import os
        if os.name=='nt':p=Path('\\\\?\\'+str(p))
        p.mkdir(parents=True);(p/'artifact').write_bytes(b'generated')
        result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr.decode())
        self.assertFalse(self.worktree.exists())
        self.assertEqual(json.loads(result.stdout)['mergedInto'],'HEAD')
        self.assertNotIn('producedNewCommits',json.loads(result.stdout))
        self.assertTrue(self.sentinel.exists())
        self.assertEqual(self.invoke().returncode,0)
        proof=json.loads((self.root/'cleanup-proof.json').read_text())
        proof['branch']='refs/heads/codex/other'
        (self.root/'cleanup-proof.json').write_text(json.dumps(proof))
        self.assertNotEqual(self.invoke().returncode,0)

    def test_cli_unmerged_branch_preserved(self):
        self.git('-C',str(self.worktree),'switch','-c','codex/integration')
        (self.worktree/'source.txt').write_text('new commit',encoding='utf-8')
        self.git('-C',str(self.worktree),'commit','-am','unmerged')
        self.commit=self.git('-C',str(self.worktree),'rev-parse','HEAD').decode().strip()
        self.assertNotEqual(self.invoke().returncode,0)
        self.assertTrue(self.worktree.exists())
