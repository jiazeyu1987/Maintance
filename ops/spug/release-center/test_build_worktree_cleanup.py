"""Real disposable Git worktrees and Windows long paths; no user checkout deletion."""
from pathlib import Path
import os
import py_compile
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import intruoyi_build as builder


class BuildWorktreeCleanupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'repo'; self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Cleanup contract test')
        self.git('config', 'user.email', 'release-test@localhost')
        (self.repo/'source.txt').write_text('committed source\n', encoding='utf-8')
        (self.repo/'.gitignore').write_text('IntRuoyiFronted/node_modules/\nIntRuoyiFronted/dist-intruoyi-test/\nIntRuoyiBackend/**/target/\n__pycache__/\n*.secret\n', encoding='utf-8')
        module=self.repo/'IntRuoyiBackend/script/release/release_migration_manifest.py'
        module.parent.mkdir(parents=True)
        module.write_text('VALUE = 1\n', encoding='utf-8')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.build_root = self.root/'build'; self.build_root.mkdir()
        self.worktree = self.build_root/'candidate'
        self.git('-c', 'core.longpaths=true', 'worktree', 'add', '--detach', str(self.worktree), self.commit)
        self.sentinel = self.build_root/'keep.txt'; self.sentinel.write_text('keep', encoding='utf-8')

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.repo),*args], stderr=subprocess.PIPE)

    def clean(self):
        function = getattr(builder, 'cleanup_build_worktree', None)
        self.assertTrue(callable(function), 'Formal build is missing safe worktree cleanup')
        return function(self.repo, self.worktree, self.build_root, self.commit)

    def test_real_long_generated_path_removed_and_sibling_preserved(self):
        p = self.worktree/'IntRuoyiFronted/node_modules'
        for i in range(7): p = p/('dependency-'+str(i)+'-'+'x'*30)
        if os.name == 'nt':
            p = Path('\\\\?\\'+str(p))
            self.addCleanup(lambda: shutil.rmtree('\\\\?\\'+str(self.worktree)) if self.worktree.exists() else None)
        p.mkdir(parents=True)
        (p/'fixture.js').write_text('generated', encoding='utf-8')
        self.assertGreater(len(str(p/'fixture.js')), 260)
        result = self.clean()
        self.assertFalse(self.worktree.exists())
        self.assertNotIn(str(self.worktree).replace('\\','/'), self.git('worktree','list','--porcelain').decode())
        self.assertEqual(self.sentinel.read_text(encoding='utf-8'), 'keep')
        self.assertEqual(result['status'], 'passed')

    def test_dirty_source_and_ignored_unknown_data_are_preserved(self):
        (self.worktree/'source.txt').write_text('user change', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'modified|dirty'):
            self.clean()
        self.assertTrue(self.worktree.exists())
        (self.worktree/'source.txt').write_text('committed source\n', encoding='utf-8')
        (self.worktree/'customer.secret').write_text('private fixture', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            self.clean()
        self.assertTrue((self.worktree/'customer.secret').exists())

    def test_wrong_commit_and_root_cannot_be_deleted(self):
        self.assertTrue(callable(getattr(builder, 'cleanup_build_worktree', None)), 'Formal build is missing safe worktree cleanup')
        wrong = '0'*40
        with self.assertRaises(ValueError):
            builder.cleanup_build_worktree(self.repo, self.worktree, self.build_root, wrong)
        with self.assertRaises(ValueError):
            builder.cleanup_build_worktree(self.repo, self.build_root, self.build_root, self.commit)
        self.assertTrue(self.worktree.exists())

    def test_real_tracked_backend_release_module_bytecode_can_be_cleaned(self):
        module=self.worktree/'IntRuoyiBackend/script/release/release_migration_manifest.py'
        cache=Path(py_compile.compile(str(module),doraise=True))
        self.assertTrue(cache.exists())
        self.assertEqual(self.clean()['status'],'passed')
        self.assertFalse(self.worktree.exists())

    def test_invalid_backend_bytecode_or_missing_tracked_module_is_preserved(self):
        module=self.worktree/'IntRuoyiBackend/script/release/release_migration_manifest.py'
        cache=Path(py_compile.compile(str(module),doraise=True))
        valid=cache.read_bytes()
        cache.write_bytes(b'not-python-cache')
        with self.assertRaisesRegex(ValueError,'Unknown'):
            self.clean()
        cache.write_bytes(valid)
        unknown=cache.with_name(cache.name.replace('release_migration_manifest','untracked_module'))
        cache.rename(unknown)
        with self.assertRaisesRegex(ValueError,'Unknown'):
            self.clean()
        self.assertTrue(unknown.exists())

    def test_git_failure_with_residual_never_becomes_false_success(self):
        original = subprocess.run
        def broken(command, **kwargs):
            if 'remove' in command:
                return subprocess.CompletedProcess(command, 255, b'', b'fixture removal failed')
            return original(command, **kwargs)
        with patch('subprocess.run', side_effect=broken), self.assertRaisesRegex((ValueError, RuntimeError), 'remov|register'):
            self.clean()
        self.assertTrue(self.worktree.exists())

    def test_real_deregistered_long_path_residual_is_verified_and_removed(self):
        original = subprocess.run
        def partial(command, **kwargs):
            if 'remove' not in command:
                return original(command, **kwargs)
            holding = self.root/'held-checkout'
            self.worktree.rename(holding)
            result = original(command, **kwargs)
            self.assertEqual(result.returncode, 0)
            holding.rename(self.worktree)
            (self.worktree/'.git').unlink()
            return subprocess.CompletedProcess(command, 255, b'', b'fixture partial physical removal')
        with patch('subprocess.run', side_effect=partial):
            result = self.clean()
        self.assertTrue(result['residualRemoved'])
        self.assertEqual(result['gitRemovalExitCode'], 255)
        self.assertFalse(self.worktree.exists())

    def test_sealed_cleanup_can_resume_after_physical_removal_before_success_save(self):
        executor = SimpleNamespace(c={'repo':str(self.repo),'buildWorktreeRoot':str(self.build_root)},save=lambda:None)
        original = dict(buildWorktree=str(self.worktree),releaseTag='candidate', payload={'commit':self.commit},
                        sealedPackage={'gitCommit':self.commit}, buildWorktreeCleanup={
                            'status':'running','path':str(self.worktree),'commit':self.commit,'ownershipVerified':True})
        self.git('worktree','remove','--force',str(self.worktree))
        builder.cleanup_sealed_build(executor, original)
        self.assertEqual(original['buildWorktreeCleanup']['status'], 'passed')

    @unittest.skipUnless(os.name=='nt', 'Windows junction behavior')
    def test_generated_dependency_junction_never_deletes_external_target(self):
        import _winapi
        outside = self.root/'outside'; outside.mkdir()
        (outside/'precious.txt').write_text('preserve',encoding='utf-8')
        modules = self.worktree/'IntRuoyiFronted/node_modules'; modules.mkdir(parents=True)
        _winapi.CreateJunction(str(outside), str(modules/'linked-dependency'))
        self.clean()
        self.assertEqual((outside/'precious.txt').read_text(encoding='utf-8'), 'preserve')


if __name__ == '__main__':
    unittest.main()
