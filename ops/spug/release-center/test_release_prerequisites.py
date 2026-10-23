"""Real SQLite/Windows handles and HTTP listener tests, plus fail-before-effects contracts."""
import json
from pathlib import Path
import shlex
import socket
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import acceptance_probe
from executor import Executor
from intruoyi_build import check_local_space
from intruoyi_runtime import Runtime
from state_store import StateStore, migrate


class PersistenceTests(unittest.TestCase):
    def test_explicit_import_preserves_original_even_while_old_file_is_open(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = dict(jobs=[dict(id='failed', status='failed')], packages=[], environments={})
            legacy = root/'state.json'
            legacy.write_text(json.dumps(original), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'offline'):
                StateStore(root)
            with legacy.open('rb') as held_reader:
                migrate(root)
                store = StateStore(root)
                updated = dict(original, packages=[dict(releaseTag='new')])
                store.save(updated)
                self.assertEqual(StateStore(root).load(), updated)
                self.assertEqual(json.load(held_reader), original)
            with self.assertRaises(FileExistsError):
                migrate(root)

    def test_long_read_transaction_does_not_block_durable_write(self):
        with tempfile.TemporaryDirectory() as folder:
            store = StateStore(folder)
            reader = sqlite3.connect(store.path)
            try:
                reader.execute('BEGIN')
                before = reader.execute('SELECT payload FROM release_state').fetchone()[0]
                after = dict(jobs=[dict(id='new', status='succeeded')], packages=[], environments={})
                store.save(after)
                self.assertEqual(reader.execute('SELECT payload FROM release_state').fetchone()[0], before)
                self.assertEqual(StateStore(folder).load(), after)
            finally:
                reader.close()

    def test_corrupt_database_never_falls_back_to_legacy_json(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'state.json').write_text(json.dumps(dict(jobs=[],packages=[],environments={})))
            (Path(folder)/'state.sqlite3').write_bytes(b'broken SQLite')
            with self.assertRaises(sqlite3.DatabaseError):
                StateStore(folder).load()

    def test_real_failed_commit_blocks_snapshot_and_new_tasks(self):
        with tempfile.TemporaryDirectory() as folder:
            executor = Executor(dict(stateDir=folder, applicationId='persistence-check', mysqlImage='mysql:8.0.39'))
            try:
                connection = executor.store.connect()
                connection.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON release_state BEGIN SELECT RAISE(ABORT, 'injected write failure'); END")
                connection.commit()
                connection.close()
                executor.state['packages'] = [dict(stage='built')]
                with self.assertRaises(sqlite3.IntegrityError):
                    executor.save()
                self.assertEqual(StateStore(folder).load()['packages'], [])
                with self.assertRaisesRegex(ValueError, 'persistence failed'):
                    executor.snapshot()
                with self.assertRaisesRegex(ValueError, 'persistence failed'):
                    executor.submit('build-release', {}, 'test')
            finally:
                executor.process_lock.close()

    def test_migration_refuses_live_executor_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            executor = Executor(dict(stateDir=folder, applicationId='persistence-check', mysqlImage='mysql:8.0.39'))
            try:
                with self.assertRaises(OSError):
                    migrate(folder)
            finally:
                executor.process_lock.close()


    def test_process_exit_during_transaction_preserves_last_committed_history(self):
        with tempfile.TemporaryDirectory() as folder:
            store = StateStore(folder)
            before = dict(jobs=[dict(id='original',status='failed')],packages=[],environments={})
            store.save(before)
            script = ('import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); '
                      'c.execute("BEGIN IMMEDIATE"); c.execute("UPDATE release_state SET payload=\'{}\'"); os._exit(7)')
            result = subprocess.run([sys.executable,'-c',script,str(store.path)],capture_output=True)
            self.assertEqual(result.returncode,7)
            self.assertEqual(StateStore(folder).load(),before)


class BuildStorageTests(unittest.TestCase):
    def test_same_volume_budgets_are_added_and_export_excludes_worktree(self):
        with tempfile.TemporaryDirectory() as folder:
            executor = SimpleNamespace(root=Path(folder), c=dict(buildWorktreeRoot=folder+'/future/worktrees',
                localBuildSpaceBytes=dict(worktree=300,package=200,state=100)))
            result = check_local_space(executor)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['requiredBytes'], 600)
            self.assertEqual(check_local_space(executor,'export')[0]['requiredBytes'], 300)
            self.assertFalse((Path(folder)/'future').exists())

    def test_real_insufficient_space_refuses_without_creating_worktree(self):
        with tempfile.TemporaryDirectory() as folder:
            executor = SimpleNamespace(root=Path(folder), c=dict(buildWorktreeRoot=folder+'/future',
                localBuildSpaceBytes=dict(worktree=2**63,package=1,state=1)))
            with self.assertRaisesRegex(ValueError, 'insufficient'):
                check_local_space(executor)
            self.assertFalse((Path(folder)/'future').exists())

    def test_missing_or_invalid_budget_has_no_default(self):
        with tempfile.TemporaryDirectory() as folder:
            for budget in (None, {}, dict(worktree=True,package=1,state=1),dict(worktree=1,package=-1,state=1)):
                with self.subTest(budget=budget), self.assertRaisesRegex(ValueError, 'Explicit positive'):
                    check_local_space(SimpleNamespace(root=Path(folder),c=dict(localBuildSpaceBytes=budget)))


class AcceptanceIngressTests(unittest.TestCase):
    def test_actual_nonce_listener_is_closed_after_success(self):
        with socket.socket() as allocator:
            allocator.bind(('127.0.0.1',0))
            port = allocator.getsockname()[1]
        runtime = SimpleNamespace(profile=lambda env:dict(host='127.0.0.1',python=sys.executable,
            acceptanceUrl='http://127.0.0.1:'+str(port),entryUrl='http://127.0.0.1:1'),ssh_options=lambda:[])
        real_popen = subprocess.Popen
        commands = []
        def local_transport(command, **kwargs):
            # Replace only SSH transport; execute the production HTTP server and
            # request path unchanged in a separate real Python process.
            parts = shlex.split(command[-1])
            commands.append(parts)
            return real_popen([sys.executable,'-u','-c',parts[-2],parts[-1]],**kwargs)
        with patch('acceptance_probe.subprocess.Popen',side_effect=local_transport):
            result = acceptance_probe.check(runtime,'backup')
        self.assertTrue(result['reachable'])
        self.assertEqual(len(commands),1)
        with socket.socket() as client:
            self.assertNotEqual(client.connect_ex(('127.0.0.1',port)),0)

    def test_unreachable_ingress_never_calls_preflight_or_deploy(self):
        runtime = Runtime({'targets':{}})
        steps=[]
        with patch.object(runtime,'check_acceptance_ingress',side_effect=ValueError('unreachable')), \
                patch.object(runtime,'preflight') as preflight, patch.object(runtime,'call') as remote:
            with self.assertRaisesRegex(ValueError,'unreachable'):
                runtime.deploy('backup',{},lambda *args,**kwargs:steps.append((args,kwargs)),'job')
        preflight.assert_not_called()
        remote.assert_not_called()
        self.assertEqual(steps,[(('check-executor-acceptance-ingress',),{})])


if __name__ == '__main__':
    unittest.main()
