"""Independent stage and Docker filesystem budgets; no remote operations."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked


class StorageBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.stage = self.base/'stage'
        self.docker = self.base/'docker'
        self.stage.mkdir()
        self.docker.mkdir()
        self.profile = dict(stagingRoot=str(self.stage), minimumStagingFreeBytes=6400,
                            minimumDockerFreeBytes=400)

    def filesystem(self, free):
        return SimpleNamespace(f_bavail=free, f_frsize=1)

    def test_large_stage_space_does_not_hide_docker_disk_exhaustion(self):
        with patch.object(agent.os, 'statvfs', create=True, side_effect=[self.filesystem(10000), self.filesystem(399)]), \
                patch.object(agent.remote, 'run', return_value=str(self.docker).encode()) as run:
            with self.assertRaisesRegex(RuntimeBlocked, 'Insufficient Docker image storage before staging'):
                agent.check_storage(self.profile)
        run.assert_called_once_with(['docker','info','--format','{{.DockerRootDir}}'])
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_docker_budget_is_independent_from_recovery_budget(self):
        with patch.object(agent.os, 'statvfs', create=True, side_effect=[self.filesystem(6400), self.filesystem(400)]) as stat, \
                patch.object(agent.remote, 'run', return_value=str(self.docker).encode()):
            agent.check_storage(self.profile)
        self.assertEqual([call.args[0] for call in stat.call_args_list], [str(self.stage),str(self.docker)])

    def test_missing_or_invalid_docker_budget_fails_without_default(self):
        for minimum in (None,True,0,-1,'400'):
            with self.subTest(minimum=minimum), patch.object(agent.os, 'statvfs', create=True, return_value=self.filesystem(10000)), \
                    patch.object(agent.remote, 'run') as run:
                self.profile['minimumDockerFreeBytes'] = minimum
                with self.assertRaisesRegex(RuntimeBlocked, 'Explicit Docker image storage'):
                    agent.check_storage(self.profile)
                run.assert_not_called()

    def test_unknown_docker_root_does_not_use_stage_filesystem(self):
        with patch.object(agent.os, 'statvfs', create=True, return_value=self.filesystem(10000)) as stat, \
                patch.object(agent.remote, 'run', return_value=str(self.base/'missing').encode()):
            with self.assertRaisesRegex(RuntimeBlocked, 'DockerRootDir'):
                agent.check_storage(self.profile)
        stat.assert_called_once_with(str(self.stage))

    def test_stage_dispatch_checks_docker_budget_before_creating_directory(self):
        with patch.object(agent, 'check_fence'), \
                patch.object(agent.os, 'statvfs', create=True, side_effect=[self.filesystem(10000),self.filesystem(399)]), \
                patch.object(agent.remote, 'run', return_value=str(self.docker).encode()):
            with self.assertRaisesRegex(RuntimeBlocked, 'Insufficient Docker image storage'):
                agent.dispatch(dict(profile=self.profile,action='stage-directory',directory=str(self.stage/'2026-10-23-16-51-17')))
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_verify_stage_rechecks_budget_before_extracting_or_loading(self):
        with patch.object(agent, 'check_fence'), patch.object(agent, 'unpack_original_package') as unpack, \
                patch.object(agent.os, 'statvfs', create=True, side_effect=[self.filesystem(10000),self.filesystem(399)]), \
                patch.object(agent.remote, 'run', return_value=str(self.docker).encode()) as run:
            with self.assertRaisesRegex(RuntimeBlocked, 'Insufficient Docker image storage'):
                agent.dispatch(dict(profile=self.profile,action='verify-stage'))
        unpack.assert_not_called()
        run.assert_called_once_with(['docker','info','--format','{{.DockerRootDir}}'])


if __name__ == '__main__':
    unittest.main()
