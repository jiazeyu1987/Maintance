"""Console replacement checks; no live process is stopped by these tests."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import psutil
import win32api

from manage_executor_service import require_idle_console, control_service
import win32service
from intruoyi_executor import IntRuoyiExecutor
from executor import Executor


class ConsoleReplacementTest(unittest.TestCase):
    def setUp(self):
        self.process = Mock(pid=100)
        self.process.children.return_value = []
        self.state = {'jobs': [{'status': 'failed'}, {'status': 'success'}]}

    def child(self, name='conhost.exe', parent=100, executable=None):
        child = Mock(pid=200)
        child.name.return_value = name
        child.ppid.return_value = parent
        child.exe.return_value = str(executable or Path(win32api.GetSystemDirectory()) / 'conhost.exe')
        return child

    def test_idle_without_children(self):
        require_idle_console(self.process, self.state)

    def test_verified_console_host_is_not_a_release_worker(self):
        self.process.children.return_value = [self.child()]
        require_idle_console(self.process, self.state)

    def test_running_job_blocks_even_without_children(self):
        self.state['jobs'].append({'status': 'running'})
        with self.assertRaisesRegex(RuntimeError, 'running release jobs'):
            require_idle_console(self.process, self.state)

    def test_console_host_does_not_hide_other_worker(self):
        self.process.children.return_value = [self.child(), self.child(name='ssh.exe')]
        with self.assertRaisesRegex(RuntimeError, 'child process'):
            require_idle_console(self.process, self.state)

    def test_name_only_does_not_allow_a_different_executable(self):
        self.process.children.return_value = [self.child(executable=Path(__file__))]
        with self.assertRaisesRegex(RuntimeError, 'child process'):
            require_idle_console(self.process, self.state)

    def test_indirect_console_host_blocks(self):
        self.process.children.return_value = [self.child(parent=150)]
        with self.assertRaisesRegex(RuntimeError, 'child process'):
            require_idle_console(self.process, self.state)

    def test_unreadable_executable_blocks(self):
        child = self.child()
        child.exe.side_effect = psutil.AccessDenied(pid=200)
        self.process.children.return_value = [child]
        with self.assertRaises(psutil.AccessDenied):
            require_idle_console(self.process, self.state)


class ServiceOperatorTest(unittest.TestCase):
    def test_start_and_stop_use_only_granted_rights(self):
        for action, right in [('start', win32service.SERVICE_START), ('stop', win32service.SERVICE_STOP)]:
            with self.subTest(action=action), patch('manage_executor_service.win32service') as api:
                api.SC_MANAGER_CONNECT = win32service.SC_MANAGER_CONNECT
                api.SERVICE_START = win32service.SERVICE_START
                api.SERVICE_STOP = win32service.SERVICE_STOP
                api.SERVICE_CONTROL_STOP = win32service.SERVICE_CONTROL_STOP
                api.OpenSCManager.return_value = 'manager'
                api.OpenService.return_value = 'service'
                control_service(action)
                api.OpenSCManager.assert_called_once_with(None, None, win32service.SC_MANAGER_CONNECT)
                api.OpenService.assert_called_once_with('manager', 'IntRuoyiReleaseExecutor', right)
                if action == 'start':
                    api.StartService.assert_called_once_with('service', None)
                else:
                    api.ControlService.assert_called_once_with('service', win32service.SERVICE_CONTROL_STOP)
                self.assertEqual(api.CloseServiceHandle.call_count, 2)

    def test_git_trust_is_command_scoped_and_only_for_registered_source(self):
        executor = object.__new__(IntRuoyiExecutor)
        repository = Path(__file__).parent
        executor.c = dict(executionMode='windows-service', repo=str(repository))
        args = ['git', '-C', str(repository), 'log', '-1']
        with patch.object(Executor, 'run', return_value=b'commit') as run:
            self.assertEqual(executor.run(args), b'commit')
            self.assertEqual(run.call_args.args[0], ['git', '-c', 'safe.directory='+repository.resolve().as_posix(), *args[1:]])
        self.assertEqual(args[1], '-C')

    def test_console_git_and_non_git_commands_remain_unchanged(self):
        for mode, args in [('console', ['git', 'version']), ('windows-service', ['docker', 'version'])]:
            executor = object.__new__(IntRuoyiExecutor)
            executor.c = dict(executionMode=mode)
            with patch.object(Executor, 'run') as run:
                executor.run(args)
                self.assertEqual(run.call_args.args[0], args)


if __name__ == '__main__':
    unittest.main()
