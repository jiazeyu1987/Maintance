"""Unit boundaries only; these tests do not certify remote connectivity."""
import copy
import json
import threading
import unittest
from unittest.mock import Mock, patch

from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime_agent import read_versions
from application_registry import ApplicationRegistry, RegistryError


def container(role, running=True):
    return dict(Id=role+'-container', Image='sha256:'+role,
                Config={'Image':role+':tag', 'Env':['PRIVATE_SECRET=not-for-response']},
                State={'Running':running, 'StartedAt':'2026-10-31T00:00:00Z'})


class CurrentVersionTests(unittest.TestCase):
    def setUp(self):
        self.profile = dict(host='test-host', frontend='frontend', backend='backend')

    def test_reads_live_patch_metadata_and_images_without_sql_or_secrets(self):
        with patch('intruoyi_runtime_agent.remote.inspect', side_effect=container), \
             patch('intruoyi_runtime_agent.remote.run', return_value=json.dumps(dict(
                 releaseTag='patch-tag', baseReleaseTag='restored-base', frontendPatchTag='patch-tag')).encode()) as run, \
             patch('intruoyi_runtime_agent.remote.sql', side_effect=AssertionError('SQL forbidden')):
            result = read_versions(self.profile)
        self.assertEqual(result['version']['releaseTag'], 'restored-base')
        self.assertEqual(result['version']['frontendPatchTag'], 'patch-tag')
        self.assertEqual(result['components']['backend']['imageId'], 'sha256:backend')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(run.call_args.args[0][:2], ['docker', 'exec'])
        self.assertNotIn('PRIVATE_SECRET', json.dumps(result))

    def test_stopped_frontend_reports_unknown_without_historical_substitution(self):
        with patch('intruoyi_runtime_agent.remote.inspect', side_effect=lambda role:container(role, role!='frontend')), \
             patch('intruoyi_runtime_agent.remote.run') as run:
            result = read_versions(self.profile)
        self.assertEqual(result['status'], 'partial')
        self.assertIsNone(result['version'])
        run.assert_not_called()

    def test_invalid_metadata_is_explicit_failure(self):
        with patch('intruoyi_runtime_agent.remote.inspect', side_effect=container), \
             patch('intruoyi_runtime_agent.remote.run', return_value=b'<html>not JSON</html>'):
            result = read_versions(self.profile)
        self.assertIsNone(result['version'])
        self.assertEqual(result['status'], 'partial')
        self.assertIn('release-info.json', result['errors'][0])

    def executor(self):
        e=object.__new__(IntRuoyiExecutor)
        e.lock=threading.RLock()
        e.c={'applicationId':'intruoyi'}
        e.state={'environments':{env:dict(releaseTag='last-deployed', images=dict(
            backend='sha256:backend', frontend='sha256:frontend')) for env in ('test','prod','backup')}}
        e.runtime=Mock()
        e.save=Mock(side_effect=AssertionError('Live reads must not persist baselines'))
        return e

    def test_concurrent_container_replacement_cannot_produce_a_confirmed_version(self):
        seen={}
        def inspect(role):
            seen[role]=seen.get(role,0)+1
            value=container(role)
            if role=='frontend' and seen[role]>1:value['Id']='replaced-container'
            return value
        with patch('intruoyi_runtime_agent.remote.inspect',side_effect=inspect), \
             patch('intruoyi_runtime_agent.remote.run',return_value=b'{"releaseTag":"old"}'):
            result=read_versions(self.profile)
        self.assertEqual(result['status'],'partial')
        self.assertIsNone(result['version'])

    def test_restore_and_connection_failure_do_not_rewrite_baselines(self):
        e=self.executor()
        before=copy.deepcopy(e.state)
        def result(env, action):
            self.assertEqual(action,'read-versions')
            if env=='backup':raise RuntimeError('SSH timed out')
            return dict(status='ok', components={role:{'imageId':'sha256:'+role} for role in ('backend','frontend')},
                        version=dict(releaseTag='restored-old' if env=='prod' else 'last-deployed'),
                        observedAt='2026-10-31T00:00:00Z')
        e.runtime.call.side_effect=result
        actual=e.current_versions()['targets']
        self.assertTrue(actual['test']['matchesRecorded'])
        self.assertFalse(actual['prod']['matchesRecorded'])
        self.assertEqual(actual['prod']['version']['releaseTag'],'restored-old')
        self.assertEqual(actual['backup']['status'],'error')
        self.assertIsNone(actual['backup']['version'])
        self.assertEqual(e.state,before)
        e.save.assert_not_called()

    def test_same_frontend_tag_with_different_backend_is_not_a_match(self):
        e=self.executor()
        e.runtime.call.return_value=dict(status='ok', version={'releaseTag':'last-deployed'},
            components={'frontend':{'imageId':'sha256:frontend'},'backend':{'imageId':'sha256:restored'}})
        self.assertTrue(all(v['matchesRecorded'] is False for v in e.current_versions()['targets'].values()))

    def test_route_is_read_only_and_application_scoped(self):
        registry=ApplicationRegistry(dict(defaultApplication='intruoyi', applications=[dict(
            id='intruoyi',name='IntRuoyi',status='ready',repo='repo',scope='test',
            executorUrl='http://127.0.0.1:18112',bridgeKey='unit')]))
        _,route=registry.resolve('/applications/intruoyi/current-versions','GET')
        self.assertEqual(route,'/current-versions')
        with self.assertRaises(RegistryError):
            registry.resolve('/applications/intruoyi/current-versions','POST',{'applicationId':'intruoyi'})


if __name__=='__main__':
    unittest.main()
