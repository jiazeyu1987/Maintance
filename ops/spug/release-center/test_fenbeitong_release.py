import hashlib
import json
from pathlib import Path
import tempfile
import tarfile
import io
import unittest
from unittest.mock import patch

from fenbeitong_build import source_files, source_identity, exported_image_id
from fenbeitong_executor import FenbeitongExecutor
import fenbeitong_agent as agent


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, value in {'server.js': 'console.log(1)', 'package.json': json.dumps({'name': 'fenbeitong-kingdee-expense-reimbursement'}),
                            'package-lock.json': '{}', 'backend/src/main.js': 'export const x=1',
                            'frontend/src/index.html': '<html></html>', '.env': 'PASSWORD=secret',
                            'runtime-data/private.sqlite': 'secret', 'dist/private.json': 'secret'}.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_source_enters_snapshot(self):
        result = source_files(self.root)
        self.assertEqual(len(result), 5)
        self.assertFalse(any('.env' in x or 'private' in x for x in result))

    def test_source_change_changes_identity(self):
        before = source_identity(source_files(self.root))
        (self.root / 'server.js').write_text('console.log(2)')
        self.assertNotEqual(before, source_identity(source_files(self.root)))

    def test_runtime_dependency_requires_explicit_build_change(self):
        (self.root / 'package.json').write_text(json.dumps({'name': 'fenbeitong-kingdee-expense-reimbursement', 'dependencies': {'x': '1'}}))
        with self.assertRaisesRegex(ValueError, '运行依赖'):
            source_files(self.root)

    def test_unexpected_file_in_source_fails(self):
        (self.root / 'backend/src/secrets.pem').write_text('private')
        with self.assertRaisesRegex(ValueError, '类型'):
            source_files(self.root)

    def test_export_identity_uses_config_not_manifest_index(self):
        data = b'{"architecture":"amd64","config":{"Cmd":["node","server.js"]}}'
        path = self.root / 'image.tar'
        with tarfile.open(path, 'w') as archive:
            for name, content in [('manifest.json', json.dumps([{'RepoTags': ['assistant:1'], 'Config': 'blobs/sha256/abc'}]).encode()), ('blobs/sha256/abc', data)]:
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        self.assertEqual(exported_image_id(path, 'assistant:1'), 'sha256:' + hashlib.sha256(data).hexdigest())


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config = json.loads(Path(__file__).with_name('fenbeitong.config.example.json').read_text('utf-8'))
        config['stateDir'] = self.tmp.name
        self.e = FenbeitongExecutor(config)
        folder = Path(self.tmp.name) / 'package'
        folder.mkdir()
        raw = b'{"applicationId":"fenbeitong"}'
        (folder / 'manifest.json').write_bytes(raw)
        self.p = dict(releaseTag='2026-10-27-12-00-00', directory=str(folder), manifestSha256=hashlib.sha256(raw).hexdigest(), packageSha256='package', stage='built')
        self.e.state['packages'].append(self.p)
        self.payload = dict(applicationId='fenbeitong', requestId='test-request-0001', releaseTag=self.p['releaseTag'])

    def tearDown(self):
        self.e.process_lock.close()
        self.tmp.cleanup()

    def test_production_requires_test_acceptance_and_rehearsal(self):
        with self.assertRaisesRegex(ValueError, '测试服'):
            self.e.gate('promote-prod', self.payload)
        self.p['accepted'] = {'test': {'note': 'passed'}}
        with self.assertRaisesRegex(ValueError, '演练'):
            self.e.gate('promote-prod', self.payload)
        self.p['rehearsal'] = {'accepted': True}
        self.e.gate('promote-prod', self.payload)

    def test_review_requires_actual_registered_production_package(self):
        self.p['accepted'] = {'prod': True}
        self.e.state['environments']['prod'] = {'packageSha256': 'different'}
        with self.assertRaisesRegex(ValueError, '同一个包'):
            self.e.gate('promote-backup', self.payload)

    def test_old_package_cannot_replace_newer(self):
        self.e.state['environments']['test'] = {'releaseTag': '2026-10-28-01-00-00'}
        with self.assertRaisesRegex(ValueError, '更新版本'):
            self.e.gate('publish-test', self.payload)

    def test_acceptance_binds_actual_deployed_package(self):
        self.e.state['environments']['test'] = {'packageSha256': 'other'}
        with self.assertRaisesRegex(ValueError, '实际部署包'):
            self.e.gate('mark-tested', self.payload)

    def test_duplicate_request_never_starts_second_worker(self):
        with patch('threading.Thread.start') as start:
            first = self.e.submit('publish-test', self.payload, '1')
            second = self.e.submit('publish-test', dict(self.payload), '1')
            self.assertEqual(first['id'], second['id'])
            self.assertEqual(start.call_count, 1)

    def test_request_cannot_cross_application(self):
        with self.assertRaisesRegex(ValueError, '应用'):
            self.e.submit('build-release', dict(self.payload, applicationId='intruoyi'), '1')

    def test_failed_remote_effect_blocks_new_release(self):
        self.e.state['jobs'].append(dict(status='failed', remoteStarted=True))
        with self.assertRaisesRegex(ValueError, '远端失败'):
            self.e.gate('publish-test', self.payload)

    def test_rejected_candidate_cannot_be_reaccepted(self):
        self.p['rejected'] = True
        with self.assertRaisesRegex(ValueError, '验收失败'):
            self.e.gate('mark-tested', self.payload)


class AgentTests(unittest.TestCase):
    def test_receipt_roundtrip_preserves_unicode_and_atomic_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'receipt.json')
            value = {'status':'failed', 'message':'回执', 'effectsStarted':False}
            agent.write_json(path, value)
            self.assertEqual(agent.read_json(path), value)
            self.assertFalse(Path(path + '.new').exists())

    def test_network_address_preserves_stopped_frontend_reservation(self):
        network = {'Id': '123456789012abcdef', 'IPAM': {'Config': [{'Subnet':'172.21.0.0/29','Gateway':'172.21.0.1'}]},
                   'Containers': {'redis': {'IPv4Address':'172.21.0.2/29'}}}
        stopped = {'NetworkSettings': {'Networks': {'app': {'IPAMConfig': {'IPv4Address':'172.21.0.3'}}}}}
        with patch.object(agent, 'run', side_effect=[json.dumps([network]), '2: br inet 172.21.0.1/29', 'stopped', json.dumps([stopped])]):
            self.assertEqual(agent.available_network_address('app'), '172.21.0.4')

    def test_internal_network_without_gateway_excludes_bridge_address(self):
        network = {'Id': '123456789012abcdef', 'IPAM': {'Config': [{'Subnet':'172.21.0.0/29'}]},
                   'Containers': {'backend': {'IPv4Address':'172.21.0.2/29'}}}
        with patch.object(agent, 'run', side_effect=[json.dumps([network]), '2: br inet 172.21.0.1/29', '']) as run:
            self.assertEqual(agent.available_network_address('app'), '172.21.0.3')
            self.assertEqual(run.call_args_list[1].args[0], ['ip','-o','-4','addr','show','dev','br-123456789012'])

    def test_network_address_exhaustion_fails_before_container_creation(self):
        network = {'Id': '123456789012abcdef', 'IPAM': {'Config': [{'Subnet':'172.21.0.0/30','Gateway':'172.21.0.1'}]},
                   'Containers': {'backend': {'IPv4Address':'172.21.0.2/30'}}}
        with patch.object(agent, 'run', side_effect=[json.dumps([network]), '2: br inet 172.21.0.1/30', '']):
            with self.assertRaisesRegex(ValueError, 'No unreserved'):
                agent.available_network_address('app')

    def test_refuse_foreign_container(self):
        with patch.object(agent, 'run', side_effect=['fenbeitong-assistant\n', '[{"Config":{"Labels":{"release.application":"other"}}}]']):
            with self.assertRaisesRegex(ValueError, 'another application'):
                agent.info('fenbeitong-assistant')

    def test_rehearsal_has_no_network_and_independent_data(self):
        config = {'packageSha256': 'abc', 'ticketValidateUrl': 'http://host/validate', 'port': 18734}
        with patch.object(agent, 'run') as run:
            agent.start(config, 'rehearsal', {'releaseTag': '1', 'imageId': 'sha256:abc'}, '/own/copy', True)
            args = run.call_args.args[0]
            self.assertEqual(args[args.index('--network') + 1], 'none')
            self.assertNotIn('-p', args)
            self.assertIn('type=bind,source=/own/copy,target=/data', args)
            self.assertIn('FENBEITONG_MODE=real', args)

    def test_unknown_root_fails_before_any_docker_operation(self):
        with patch.object(agent, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Unregistered'):
                agent.execute({'root': '/opt/intruoyi', 'action': 'deploy'})
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
