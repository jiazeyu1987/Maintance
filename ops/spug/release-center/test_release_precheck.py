"""Diagnostic contracts with isolated unit boundaries; not remote acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from executor import Executor
from intruoyi_executor import IntRuoyiExecutor
from intruoyi_runtime import RuntimeBlocked
import intruoyi_runtime_agent as agent
import release_precheck as checks


class PrecheckTest(unittest.TestCase):
    def setUp(self):
        self.e = object.__new__(IntRuoyiExecutor)
        self.e.c = dict(applicationId='intruoyi', runtimeKind='remote-intruoyi', repo='repo', executionMode='console')
        self.e.password = 'unit-private-value'
        self.e.lock = threading.RLock()
        self.e.worker = None
        self.e.draining = False
        self.e.save = Mock()
        self.e.step = Mock()
        self.e.log = Mock()
        self.obs = dict(releaseTag='2026-10-24-01-00-00', images={'backend':'sha256:'+'a'*64,'frontend':'sha256:'+'b'*64},
                        ledgerRecords=[], schemaSha256='schema', ledgerSha256='ledger', fingerprint='origin',
                        baselineStatus='registered', backendHealth={'status':'UP'}, frontendHttpStatus=200,
                        maintenance=False, readOnly={'read_only':False,'super_read_only':False})
        self.package = dict(releaseTag='2026-10-24-02-00-00', stage='built', baseline=False,
                            packageSha256='archive', manifestSha256='manifest', rehearsals=[])
        self.manifest = dict(migrations=[], images={'backend':{'id':'sha256:'+'c'*64},'frontend':{'id':'sha256:'+'d'*64}})
        self.e.state = dict(jobs=[], packages=[self.package], environments={e:copy.deepcopy(self.obs) for e in ('test','prod','backup')})
        self.e.package = Mock(return_value=(self.package,self.manifest))

    def job(self, operation='publish-test'):
        payload = dict(applicationId='intruoyi', requestId='check-request-01', operation=operation)
        if operation=='build-release': payload['commit']='a'*40
        else: payload['releaseTag']=self.package['releaseTag']
        with patch('release_precheck.threading.Thread'):
            return self.e.submit(checks.ACTION,payload,'unit')

    def run_check(self, job, *, observe_error=None, nas_error=None):
        remote = Mock()
        remote.observe.return_value = copy.deepcopy(self.obs)
        if observe_error:remote.observe.side_effect=observe_error
        remote.call.return_value={'checks':[{'id':'storage','label':'空间','status':'passed','detail':'检查通过','evidence':{}}]}
        with patch('release_precheck.Runtime',return_value=remote), patch('release_precheck.nas_storage',side_effect=nas_error) as nas:
            if not nas_error:nas.return_value={'writeReadRenameDelete':True}
            checks.execute(self.e,job)
        return remote

    def test_request_is_idempotent_and_bound_to_operation(self):
        job=self.job()
        self.assertIs(self.e.submit(checks.ACTION,dict(job['payload']),'unit'),job)
        with self.assertRaisesRegex(ValueError,'binding'):
            self.e.submit(checks.ACTION,dict(job['payload'],operation='promote-prod'),'unit')
        with self.assertRaisesRegex(ValueError,'其他任务'):
            self.e.submit(checks.ACTION,dict(job['payload'],requestId='other-request'),'unit')

    def test_pass_never_changes_package_or_environment(self):
        before=copy.deepcopy((self.e.state['packages'],self.e.state['environments']))
        job=self.job();remote=self.run_check(job)
        self.assertEqual(job['status'],'succeeded')
        self.assertEqual(job['result']['status'],'passed')
        self.assertEqual(job['result']['packageSha256'],'archive')
        self.assertEqual((self.e.state['packages'],self.e.state['environments']),before)
        self.assertEqual(remote.call.call_args.args,('test','prerequisite-resources'))
        remote.stage.assert_not_called();remote.deploy.assert_not_called()
        self.assertFalse(job.get('effectsStarted',False))

    def test_failed_nas_does_not_hide_independent_target_checks_or_lock_release(self):
        job=self.job();remote=self.run_check(job,nas_error=RuntimeError('NAS connection error 53'))
        self.assertEqual(job['status'],'failed')
        self.assertEqual(next(r for r in job['result']['checks'] if r['id']=='nas')['status'],'failed')
        remote.observe.assert_called_once_with('test')
        self.assertFalse(self.e.failed_task_blocks(job,'publish-test',{},self.package))
        self.e.worker = None
        with patch('release_precheck.threading.Thread'):
            again=self.e.submit(checks.ACTION,dict(job['payload'],requestId='new-check-request'),'unit')
        self.assertNotEqual(again['id'],job['id'])

    def test_unreachable_target_marks_dependent_plan_unchecked(self):
        job=self.job();self.run_check(job,observe_error=RuntimeBlocked('SSH timeout'))
        rows={r['id']:r for r in job['result']['checks']}
        self.assertEqual(rows['test-ssh']['status'],'failed')
        self.assertEqual(rows['test-health']['status'],'blocked')
        self.assertEqual(rows['target-plan']['status'],'blocked')
        self.assertEqual(job['result']['status'],'failed')

    def test_invalid_package_never_gets_passed_workflow_or_plan(self):
        self.e.package.side_effect=ValueError('Release archive checksum mismatch')
        job=self.job();self.run_check(job)
        rows={r['id']:r for r in job['result']['checks']}
        self.assertEqual(rows['package']['status'],'failed')
        self.assertEqual(rows['workflow']['status'],'blocked')
        self.assertNotIn('packageSha256',job['result'])

    def test_prod_without_rehearsal_cannot_pass(self):
        job=self.job('promote-prod');self.run_check(job)
        self.assertEqual(job['result']['status'],'failed')
        self.assertEqual(next(r for r in job['result']['checks'] if r['id']=='workflow')['status'],'failed')

    def test_changed_actual_baseline_is_reported_without_overwriting_it(self):
        job=self.job();self.obs['schemaSha256']='changed'
        self.run_check(job)
        row=next(r for r in job['result']['checks'] if r['id']=='target-plan')
        self.assertEqual(row['status'],'failed')
        self.assertIn('schemaSha256',row['detail'])
        self.assertEqual(self.e.state['environments']['test']['schemaSha256'],'schema')

    def test_real_probe_preserves_other_files_and_removes_only_own_file(self):
        with tempfile.TemporaryDirectory() as path:
            other=Path(path)/'keep.txt';other.write_text('keep')
            self.assertTrue(checks.probe_directory(path)['writeReadRenameDelete'])
            self.assertEqual(list(Path(path).iterdir()),[other])
            self.assertEqual(other.read_text(),'keep')

    def test_credentials_do_not_enter_error_text(self):
        error=RuntimeError('password=abc token:xyz '+self.e.password+' https://name:secret@example.test/repo')
        result=checks.safe_error(error,self.e)
        for value in ('abc','xyz',self.e.password,'name:secret'):self.assertNotIn(value,result)

    def test_build_missing_docker_blocks_images_but_checks_each_server(self):
        job=self.job('build-release')
        def version(executor,name,args):
            if name=='docker':raise ValueError('Docker unavailable')
            return {'commandCompleted':True}
        with patch.object(checks,'source_commit',return_value={'commit':'a'*40}), \
             patch.object(checks,'local_storage',return_value=[]), \
             patch.object(checks,'tool',side_effect=version), \
             patch.object(checks,'base_images') as images, \
             patch.object(checks,'rehearsal_profile',return_value={}):
            remote=self.run_check(job)
        rows={r['id']:r for r in job['result']['checks']}
        self.assertEqual(rows['docker']['status'],'failed')
        self.assertEqual(rows['base-images']['status'],'blocked')
        images.assert_not_called()
        self.assertEqual([c.args for c in remote.observe.call_args_list],[('test',),('prod',),('backup',)])
        self.assertEqual(job['status'],'failed')

    def test_source_commit_is_exact_and_never_checks_out_worktree(self):
        self.e.run=Mock(return_value=('a'*40+'\n').encode())
        self.assertEqual(checks.source_commit(self.e,'a'*40)['commit'],'a'*40)
        self.assertEqual(len(self.e.run.call_args_list),4)
        self.assertTrue(all(c.args[0][3] in ('rev-parse','cat-file') for c in self.e.run.call_args_list))
        self.e.run.return_value=('b'*40+'\n').encode()
        with self.assertRaisesRegex(ValueError,'提交'):
            checks.source_commit(self.e,'a'*40)

    def test_remote_resource_failure_remains_visible_and_continues_other_checks(self):
        profile=dict(backend='app',frontend='web',writers=['app'],writerInventoryConfirmed=True)
        with patch.object(agent,'check_storage',side_effect=RuntimeBlocked('disk full')), \
             patch.object(agent.remote,'inspect',return_value={'State':{'Running':True}}), \
             patch('intruoyi_recovery_agent.inventory',return_value=[]), \
             patch.object(agent,'startup_timeout',return_value=120), \
             patch.object(agent,'acceptance_spec',return_value={'network':'host'}):
            result=agent.prerequisite_resources(profile)
        self.assertFalse(result['businessMutations'])
        self.assertEqual(result['checks'][0]['status'],'failed')
        self.assertEqual([r['status'] for r in result['checks'][1:]],['passed']*4)


if __name__=='__main__':unittest.main()
