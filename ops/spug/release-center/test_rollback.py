"""Unit contracts only; these do not claim a real production rollback rehearsal."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import threading
import time
from unittest.mock import Mock, patch
import rollback_agent as remote
from rollback_mixin import compatibility, RollbackMixin


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


class RollbackSafetyTest(unittest.TestCase):
    def test_capture_retry_preserves_evidence_and_rejects_drift(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            profile = dict(stagingRoot=tmp, frontend='front', backend='back')
            origin = dict(fingerprint='stable', releaseTag='old', images=dict(frontend='f', backend='b'))
            config = Path(tmp) / 'config'
            config.write_text('original', encoding='utf-8')
            containers = {profile[role]: dict(Id=role, Image=image, Config={}, HostConfig={},
                State=dict(Running=True), Mounts=[dict(Type='bind', Source=str(config), Destination='/config'),
                                                dict(Type='volume', Source=tmp, Destination='/data')])
                for role, image in origin['images'].items()}
            agent = SimpleNamespace(require=require, remote=SimpleNamespace(inspect=lambda name: containers[name]),
                private_json=Mock(side_effect=lambda p, v: p.write_text(json.dumps(v), encoding='utf-8')),
                file_sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest())
            tag = '2026-10-28-23-36-26'
            first = remote.capture(agent, profile, tag, origin)
            path = remote.snapshot_path(profile, tag)
            before = path.read_bytes()
            containers['front']['State']['StartedAt'] = 'later-observation'
            containers['back']['Mounts'].reverse()
            self.assertEqual(first, remote.capture(agent, profile, tag, origin))
            agent.private_json.assert_called_once()
            for key, value in [('Id', 'replacement'), ('Image', 'changed'), ('Config', {'Env': ['changed']}),
                               ('HostConfig', {'NetworkMode': 'changed'}), ('State', {'Running': False}),
                               ('Mounts', [])]:
                with self.subTest(key=key):
                    previous = containers['front'][key]
                    containers['front'][key] = value
                    with self.assertRaises(RuntimeError): remote.capture(agent, profile, tag, origin)
                    containers['front'][key] = previous
                    self.assertEqual(before, path.read_bytes())
            with self.assertRaises(RuntimeError):
                remote.capture(agent, profile, tag, dict(origin, fingerprint='different'))
            config.write_text('modified', encoding='utf-8')
            with self.assertRaises(RuntimeError): remote.capture(agent, profile, tag, origin)
            self.assertEqual(before, path.read_bytes())
            agent.private_json.assert_called_once()

    def executor(self):
        obj=RollbackMixin()
        obj.lock=threading.RLock();obj.c={'applicationId':'intruoyi'}
        obj.state={'jobs':[]};obj.ensure_persistence=Mock();obj.save=Mock()
        return obj

    def test_concurrent_release_blocks_preview(self):
        obj=self.executor();obj.state['jobs']=[dict(requestId='existing-id',status='running')]
        with self.assertRaisesRegex(ValueError,'Running/interrupted'):
            obj.submit('rollback-preview',dict(applicationId='intruoyi',requestId='preview-id'), '1')
        obj.save.assert_not_called()

    def test_preview_request_is_idempotent_and_binding_is_checked(self):
        obj=self.executor();payload=dict(applicationId='intruoyi',requestId='preview-id')
        with patch('rollback_mixin.threading.Thread') as worker:
            first=obj.submit('rollback-preview',payload,'1')
            self.assertIs(obj.submit('rollback-preview',payload,'1'),first)
            self.assertEqual(len(obj.state['jobs']),1);worker.assert_called_once()
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                obj.submit('rollback-preview',dict(payload,note='changed'),'1')

    def test_blocked_or_expired_preview_cannot_execute(self):
        for ready,expires in [(False,time.time()+100),(True,time.time()-1)]:
            obj=self.executor();obj.state['jobs']=[dict(id='preview',requestId='old-id',status='succeeded',action='rollback-preview',
                rollbackPlan=dict(ready=ready,expiresAt=expires,targetReleaseTag='2026-10-23-16-51-17'))]
            with self.assertRaisesRegex(ValueError,'blocked or expired'):
                obj.submit('rollback-prod',dict(applicationId='intruoyi',requestId='execution-id',previewJobId='preview'),'1')
            obj.save.assert_not_called()

    def test_ready_preview_requires_exact_confirmation_and_is_consumed_once(self):
        obj=self.executor();obj.state['jobs']=[dict(id='preview',requestId='old-id',status='succeeded',action='rollback-preview',
            rollbackPlan=dict(ready=True,expiresAt=time.time()+100,targetReleaseTag='2026-10-23-16-51-17'))]
        payload=dict(applicationId='intruoyi',requestId='execution-id',previewJobId='preview',confirm='PROD wrong')
        with self.assertRaisesRegex(ValueError,'confirmation'):obj.submit('rollback-prod',payload,'1')
        payload['confirm']='PROD 2026-10-23-16-51-17'
        with patch('rollback_mixin.threading.Thread'):
            job=obj.submit('rollback-prod',payload,'1');job['status']='succeeded'
            self.assertEqual(job['actor'],'1')
            with self.assertRaisesRegex(ValueError,'consumed'):
                obj.submit('rollback-prod',dict(payload,requestId='second-execution'),'1')

    def test_database_change_cannot_be_hidden_by_same_images(self):
        stable = dict(schemaSha256='old', ledgerSha256='ledger', images={'backend':'same'})
        current = dict(stable, schemaSha256='new')
        self.assertTrue(compatibility(current, stable))
        self.assertTrue(compatibility(dict(stable, ledgerSha256='new-ledger'), stable))
        self.assertEqual(compatibility(stable, stable), [])

    def test_frontend_outage_does_not_hide_image_bound_rollback_target(self):
        obj=self.executor()
        origin=dict(releaseTag='old',schemaSha256='same',ledgerSha256='same')
        obj.state['jobs']=[dict(action='promote-prod',target='prod',releaseTag='new',originState=origin)]
        obj.runtime=SimpleNamespace(observe=Mock(return_value=dict(releaseTag=None,images={'frontend':'f','backend':'b'},
            schemaSha256='same',ledgerSha256='same',fingerprint='live')))
        obj.manifest=Mock(return_value=({},dict(images={'frontend':{'id':'f'},'backend':{'id':'b'}})))
        obj.technical_passed=Mock(return_value=True)
        obj.rollback_remote=Mock(return_value=dict(ready=True,blockers=[],snapshotSha256='snapshot'))
        plan=obj.rollback_plan()
        self.assertTrue(plan['ready']);self.assertEqual(plan['currentReleaseTag'],'new')
        self.assertEqual(plan['targetReleaseTag'],'old')

    def test_changed_database_never_stops_writers(self):
        agent = SimpleNamespace(require=require, observe=Mock(return_value=dict(fingerprint='now', schemaSha256='new', ledgerSha256='old')),
                                stop_writers=Mock(), docker=Mock())
        plan=dict(currentFingerprint='now',origin=dict(schemaSha256='old',ledgerSha256='old'))
        with self.assertRaisesRegex(RuntimeError, 'Database differs'):
            remote.execute(agent, dict(host='172.30.30.57',environment='prod',backend='backend',writers=['backend']),plan,'JOB-1234567890')
        agent.stop_writers.assert_not_called();agent.docker.assert_not_called()

    def test_preview_drift_never_stops_writers(self):
        agent=SimpleNamespace(require=require,observe=Mock(return_value=dict(fingerprint='changed')),stop_writers=Mock())
        with self.assertRaisesRegex(RuntimeError,'changed after'):
            remote.execute(agent,dict(host='172.30.30.57',environment='prod',backend='backend',writers=['backend']),
                           dict(currentFingerprint='before'),'JOB-1234567890')
        agent.stop_writers.assert_not_called()

    def test_configuration_change_during_drain_prevents_container_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=dict(host='172.30.30.57',environment='prod',backend='backend',writers=['backend'],stagingRoot=tmp)
            tag='2026-10-24-03-24-24'
            path=remote.snapshot_path(profile,tag);path.parent.mkdir();path.write_text('{}')
            observation=dict(fingerprint='now',schemaSha256='same',ledgerSha256='same')
            agent=SimpleNamespace(require=require,observe=Mock(return_value=observation),private_json=Mock(),
                                  stop_writers=Mock(),check_fence=Mock(),docker=Mock())
            plan=dict(currentFingerprint='now',currentReleaseTag=tag,snapshotSha256='pinned',
                      origin=dict(schemaSha256='same',ledgerSha256='same'))
            with patch('rollback_agent.inspect_snapshot',side_effect=[dict(ready=True,snapshotSha256='pinned'),dict(ready=False,snapshotSha256='pinned')]):
                with self.assertRaisesRegex(RuntimeError,'changed during writer drain'):
                    remote.execute(agent,profile,plan,'JOB-1234567890')
            agent.stop_writers.assert_called_once();agent.docker.assert_not_called()

    def test_missing_snapshot_is_blocked_not_synthesized(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=remote.inspect_snapshot(None,dict(stagingRoot=tmp),'2026-10-24-03-24-24',{})
            self.assertFalse(result['ready']);self.assertTrue(result['blockers'])
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_changed_secret_config_blocks_without_returning_secret(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config';config.write_text('password=VERY_SECRET')
            origin=dict(fingerprint='stable',images=dict(frontend='front',backend='back'))
            saved=dict(origin=origin,configFiles={str(config):'old-digest'},containers={})
            for role,image in origin['images'].items():
                saved['containers'][role]=dict(Id=role,Image=image,Config={},HostConfig={})
            path=remote.snapshot_path(dict(stagingRoot=tmp),'2026-10-24-03-24-24');path.parent.mkdir();path.write_text(json.dumps(saved))
            def inspect(role):return dict(saved['containers'][role],State=dict(Running=False))
            agent=SimpleNamespace(require=require,remote=SimpleNamespace(inspect=inspect),file_sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
            result=remote.inspect_snapshot(agent,dict(stagingRoot=tmp),'2026-10-24-03-24-24',origin)
            self.assertFalse(result['ready']);self.assertNotIn('VERY_SECRET',json.dumps(result))

    def test_path_traversal_refused(self):
        with self.assertRaises(ValueError):remote.snapshot_path({'stagingRoot':'/data'},'../../other')


if __name__=='__main__':unittest.main()
