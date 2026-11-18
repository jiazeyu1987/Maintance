"""Real Git contracts for the change notes consumed by ReleaseInfoDock."""
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

import intruoyi_build


class ReleaseInfoChangesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Release contract test')
        self.git('config', 'user.email', 'release-contract@example.invalid')
        self.executor = SimpleNamespace(run=subprocess.check_output)

    def git(self, *arguments):
        return subprocess.check_output(['git', '-C', str(self.repo), *arguments], stderr=subprocess.PIPE).decode('utf-8').strip()

    def commit(self, number, message):
        (self.repo/'source.txt').write_text(str(number), encoding='utf-8')
        self.git('add', 'source.txt')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def test_notes_are_bound_to_target_and_exclude_later_or_uncommitted_changes(self):
        target = self.commit(1, '日志: 记录后端启动完成')
        self.commit(2, 'Later commit excluded from the frozen release')
        (self.repo/'source.txt').write_text('uncommitted content', encoding='utf-8')
        (self.repo/'untracked.txt').write_text('untracked content', encoding='utf-8')

        info = intruoyi_build.build_release_info(self.executor, self.repo, 'candidate', target)

        self.assertEqual(info['releaseTag'], 'candidate')
        self.assertEqual(info['sourceCommit'], target)
        self.assertEqual(info['changeSet']['gitChanges'], [self.git('log', '-1', '--format=%h %s', target)])
        self.assertIn('启动', info['changeSet']['gitChanges'][0])
        self.assertIn('日志', info['changeSet']['gitChanges'][0])

    def test_page_receives_at_most_ten_real_commits_newest_first(self):
        for number in range(13):
            target = self.commit(number, 'Change '+str(number))

        info = intruoyi_build.build_release_info(self.executor, self.repo, 'candidate', target)

        self.assertEqual(info['changeSet']['gitChanges'], self.git('log', '-10', '--format=%h %s', target).splitlines())
        self.assertEqual(len(info['changeSet']['gitChanges']), 10)

    def test_missing_target_fails_instead_of_making_up_release_notes(self):
        self.commit(1, 'Existing source')
        with self.assertRaises(subprocess.CalledProcessError):
            intruoyi_build.build_release_info(self.executor, self.repo, 'candidate', 'f'*40)


if __name__ == '__main__':
    unittest.main()
