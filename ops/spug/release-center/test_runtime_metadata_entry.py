import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import intruoyi_runtime_agent as agent
import release_runtime_metadata as metadata


class MetadataEntryTest(unittest.TestCase):
    def test_missing_environment_path_fails_preflight_before_remote_access(self):
        with patch.object(agent.remote,'sql') as sql, patch.object(agent,'stop_writers') as stop:
            with self.assertRaisesRegex(ValueError,'runtimeEnvironmentFile'):
                agent.preflight({'environment':'test'}, {})
            sql.assert_not_called()
            stop.assert_not_called()

    def test_metadata_retry_without_backup_binding_rechecks_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'candidate';root.mkdir()
            candidate=dict(releaseTag='candidate',images={'backend':{'id':'b'},'frontend':{'id':'f'}})
            (root/'deployment-pending.json').write_text(json.dumps(candidate))
            marker=root/'runtime-opening-pending.private.json'
            identity=dict(releaseTag='candidate',backendId='current',frontendId='frontend-current',images=candidate['images'])
            marker.write_text(json.dumps(identity))
            containers={'b':dict(Id='current',Image='b',Config={'Env':['INTRUOYI_RELEASE_MAINTENANCE=false']}),
                        'f':dict(Id='frontend-current',Image='f')}
            profile=dict(stagingRoot=tmp,backend='b',frontend='f')
            with patch.object(agent,'check_fence'), patch.object(agent.remote,'inspect',side_effect=lambda n:containers[n]), \
                 patch.object(agent,'health'),patch.object(agent,'gxp_release_mode'), \
                 patch.object(agent,'finish_reopen',return_value={'done':True}) as finish:
                self.assertEqual(agent.reopen(profile),{'done':True})
                containers['b']['Id']='different'
                with self.assertRaisesRegex(agent.RuntimeBlocked,'target changed'):agent.reopen(profile)
                containers['b']['Id']='current'
                containers['f']['Id']='same-image-different-container'
                with self.assertRaisesRegex(agent.RuntimeBlocked,'target changed'):agent.reopen(profile)
                self.assertEqual(finish.call_count,1)

    def test_each_normal_environment_aligns_before_source_binding_and_cleanup(self):
        for env in ['test','prod','backup']:
            with self.subTest(env=env):self.execute(env)

    def test_failure_retains_bound_tail_and_acceptance_resource(self):
        self.execute('test', fail=True)

    def execute(self, env, fail=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); events=[]
            profile=dict(environment=env,backend='b',frontend='f',acceptanceFrontend='a',writers=[])
            candidate=dict(releaseTag='2026-11-19-23-41-45',images={})
            def aligned(*args,**kwargs):
                events.append('metadata')
                if fail:raise ValueError('metadata failed')
                return dict(status='ALIGNED')
            def bound(*args,**kwargs):
                events.append('binding');return dict(status='NOT_CONFIGURED')
            def command(args,**kwargs):
                if args[:2]==['docker','rm']:events.append('cleanup')
            with patch.object(agent,'directory',return_value=root), \
                 patch.object(agent,'BACKUP_SOURCE_PROGRAM','fixture',create=True), \
                 patch.object(agent.remote,'inspect',return_value=dict(Id='actual',State=dict(Running=True),Config=dict(Labels={'intruoyi.release.acceptance':'true'}))), \
                 patch.object(agent.remote,'run',side_effect=command), \
                 patch.object(agent,'health',side_effect=lambda *a,**kw:events.append('health')), \
                 patch.object(agent,'gxp_release_mode'),patch.object(agent,'observe',return_value={}), \
                 patch.object(metadata,'align',side_effect=aligned), \
                 patch('release_backup_source.synchronize',side_effect=bound):
                if fail:
                    with self.assertRaisesRegex(ValueError,'metadata failed'):agent.finish_reopen(profile,candidate)
                    saved=json.loads((root/'runtime-opening-pending.private.json').read_text())
                    self.assertEqual(saved['backendId'],'actual')
                    self.assertEqual(saved['frontendId'],'actual')
                    self.assertNotIn('cleanup',events)
                else:
                    result=agent.finish_reopen(profile,candidate)
                    self.assertEqual(result['runtimeMetadata']['status'],'ALIGNED')
                    self.assertEqual(events,['health','metadata','binding','cleanup'])
                    self.assertFalse((root/'runtime-opening-pending.private.json').exists())


if __name__=='__main__':unittest.main()
