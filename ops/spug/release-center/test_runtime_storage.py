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
                            minimumDockerFreeBytes=400, minimumDockerRuntimeFreeBytes=100)

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

    def test_imported_images_use_explicit_runtime_reserve(self):
        for free,passes in ((399,True),(100,True),(99,False)):
            with self.subTest(free=free), patch.object(agent.os,'statvfs',create=True,side_effect=[self.filesystem(6400),self.filesystem(free)]), patch.object(agent.remote,'run',return_value=str(self.docker).encode()):
                if passes:agent.check_storage(self.profile,images_imported=True)
                else:
                    with self.assertRaisesRegex(RuntimeBlocked,'after verified import'):agent.check_storage(self.profile,images_imported=True)

    def test_missing_runtime_reserve_is_not_silently_defaulted(self):
        del self.profile['minimumDockerRuntimeFreeBytes']
        with patch.object(agent.os,'statvfs',create=True,return_value=self.filesystem(6400)):
            with self.assertRaisesRegex(RuntimeBlocked,'minimumDockerRuntimeFreeBytes'):agent.check_storage(self.profile,images_imported=True)

    def test_reused_stage_proves_images_before_applying_runtime_reserve(self):
        root=self.stage/'2026-10-24-03-24-24';root.mkdir()
        payload=dict(profile=self.profile,action='stage-directory',directory=str(root))
        with patch.object(agent,'check_fence'), patch.object(agent,'reuse_verified_stage',return_value={'verified':True,'reused':True}) as reuse, patch.object(agent,'check_storage') as check:
            self.assertTrue(agent.dispatch(payload)['reused'])
            reuse.assert_called_once_with(root,payload)
            check.assert_called_once_with(self.profile,images_imported=True)
        with patch.object(agent,'check_fence'), patch.object(agent,'reuse_verified_stage',side_effect=RuntimeBlocked('image missing')), patch.object(agent,'check_storage') as check:
            with self.assertRaisesRegex(RuntimeBlocked,'image missing'):agent.dispatch(payload)
            check.assert_not_called()

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
