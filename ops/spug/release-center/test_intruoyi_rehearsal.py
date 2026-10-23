"""Real media-origin rewrite policy tests; no remote success is substituted."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from intruoyi_rehearsal_agent import rewrite_media_urls, isolated_backend_environment, redis_config_password, source_redis_auth, apply_checked_batches
from intruoyi_rehearsal import can_reuse_images
from intruoyi_rehearsal_agent import source_active_profiles, isolated_nginx_config


class BaselineStartupTest(unittest.TestCase):
    def test_source_dev_profile_is_preserved(self):
        info = {'Config': {'Env': ['ARGS=--spring.profiles.active=dev --other=value'], 'Cmd': ['sh', '-c', 'exec java ${ARGS}']}}
        self.assertEqual(source_active_profiles(info), 'dev')
        info['Config']['Env'].append('SPRING_PROFILES_ACTIVE=prod')
        with self.assertRaises(ValueError):
            source_active_profiles(info)

    def test_listener_and_both_internal_upstreams_are_relocated(self):
        original = 'server { listen 172.30.30.58:8081; listen 172.30.30.58:28081; proxy_pass http://172.29.1.2:48081; }\nserver { listen 172.30.30.58:48081; proxy_pass http://172.29.1.3:9000; }'
        result = isolated_nginx_config(original, 8081, ['172.29.1.2'], 'isolated-backend', ['172.29.1.3'], 'isolated-minio')
        self.assertIn('listen 80;', result)
        self.assertIn('listen 28081;', result)
        self.assertIn('listen 48081;', result)
        self.assertIn('http://isolated-backend:48081', result)
        self.assertIn('http://isolated-minio:9000', result)
        self.assertNotIn('172.', result)


class MediaUrlRewriteTest(unittest.TestCase):
    def setUp(self):
        self.source = {'minioLocalEndpointHosts': ['172.30.30.57', '127.0.0.1', 'host.docker.internal'],
                       'minioBuckets': ['yudao', 'edhr-protected-storage-20260601']}
        self.target = 'http://172.30.30.58:39082'

    def rewrite(self, value):
        return rewrite_media_urls(value, self.source, self.target)

    def test_keeps_protected_object_key_and_encoding_exact(self):
        key = '/yudao/showroom/%E5%B1%95%E5%8E%85/a%20b.mp4?versionId=abc%2F123'
        changed, count = self.rewrite('http://127.0.0.1:9000' + key)
        self.assertEqual(changed, self.target + key)
        self.assertEqual(count, 1)

    def test_embedded_json_retains_logic_object_and_other_business_content(self):
        original = json.dumps({'id': 28, 'url': 'http://172.30.30.57:9000/yudao/showroom/a.png', 'other': 'unchanged'})
        changed, count = self.rewrite(original)
        self.assertEqual(json.loads(changed), {'id': 28, 'url': self.target + '/yudao/showroom/a.png', 'other': 'unchanged'})
        self.assertEqual(count, 1)

    def test_slash_escaped_editor_json_remains_valid(self):
        original = '{"url":"http:\\/\\/host.docker.internal:9000\\/yudao\\/showroom\\/a.png"}'
        changed, count = self.rewrite(original)
        self.assertEqual(json.loads(changed)['url'], self.target + '/yudao/showroom/a.png')
        self.assertIn('http:\\/\\/', changed)
        self.assertEqual(count, 1)

    def test_does_not_rewrite_other_bucket_host_or_prefix_collision(self):
        for value in ['http://172.30.30.57:9000/ragflow/a', 'http://other:9000/yudao/a',
                      'http://172.30.30.57:9000/yudao-other/a', '/yudao/showroom/a.png']:
            with self.subTest(value=value):
                self.assertEqual(self.rewrite(value), (value, 0))

    def test_signed_local_url_cannot_be_blindly_repointed(self):
        with self.assertRaisesRegex(ValueError, 're-signing'):
            self.rewrite('http://172.30.30.57:9000/yudao/a?X-Amz-Signature=redacted')

    def test_unrelated_signed_url_does_not_block_plain_local_object(self):
        value = json.dumps({'local': 'http://127.0.0.1:9000/yudao/a', 'external': 'https://outside/a?Signature=value'})
        changed, count = self.rewrite(value)
        self.assertEqual(count, 1)
        self.assertEqual(json.loads(changed)['external'], 'https://outside/a?Signature=value')

    def test_requires_exact_isolated_origin(self):
        with self.assertRaisesRegex(ValueError, '39082'):
            rewrite_media_urls('http://127.0.0.1:9000/yudao/a', self.source, 'http://172.30.30.57:9000')

    def test_edhr_keeps_real_retention_and_uses_isolated_public_domain(self):
        source = dict(self.source, edhrProperties={'EDHR_S3_BUCKET': 'edhr-protected-storage-20260601',
            'EDHR_S3_REGION': 'us-east-1', 'EDHR_S3_RETENTION_MODE': 'COMPLIANCE',
            'EDHR_S3_RETAIN_UNTIL_DAYS': '7', 'EDHR_S3_REQUIRE_LEGAL_HOLD': 'true'})
        profile = {'minio': 'intruoyi-release-rehearsal-minio', 'isolatedMinioPublicUrl': self.target}
        environment = dict(value.split('=', 1) for value in isolated_backend_environment(profile, source, 'isolated-only'))
        self.assertEqual(environment['EDHR_S3_DOMAIN'], self.target + '/edhr-protected-storage-20260601')
        self.assertEqual(environment['EDHR_S3_ENDPOINT'], 'http://intruoyi-release-rehearsal-minio:9000')
        self.assertEqual(environment['EDHR_S3_RETENTION_MODE'], 'COMPLIANCE')
        self.assertEqual(environment['EDHR_S3_REQUIRE_LEGAL_HOLD'], 'true')
        self.assertEqual(environment['INTRUOYI_RELEASE_MAINTENANCE'], 'false')

    def test_missing_real_edhr_settings_cannot_silently_disable_protected_media(self):
        with self.assertRaisesRegex(ValueError, 'Verified EDHR'):
            isolated_backend_environment({'minio': 'isolated', 'isolatedMinioPublicUrl': self.target},
                                         dict(self.source, edhrProperties={}), 'isolated-only')

    def test_image_reuse_requires_same_registered_docker_daemon(self):
        source={'host':'172.30.30.58'}
        target={'host':'172.30.30.58'}
        self.assertTrue(can_reuse_images(source,target,{'daemonId':'A1'},{'daemonId':'A1'}))
        self.assertFalse(can_reuse_images(source,dict(target,host='172.30.30.59'),{'daemonId':'A1'},{'daemonId':'A1'}))
        self.assertFalse(can_reuse_images(source,target,{'daemonId':'A1'},{'daemonId':'B2'}))
        self.assertFalse(can_reuse_images(source,target,{},{}))


class RedisAuthenticationTest(unittest.TestCase):
    def test_registered_native_config_handles_quotes_and_comments(self):
        self.assertEqual(redis_config_password('bind 0.0.0.0\nrequirepass "component # secret" # note\n'), 'component # secret')

    def test_missing_empty_ambiguous_or_malformed_config_fails_without_echoing_values(self):
        for content in ('bind 0.0.0.0', 'requirepass ""', 'requirepass first\nrequirepass second', 'requirepass "unfinished'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                redis_config_password(content)

    def test_conflicting_registration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Exactly one'):
            source_redis_auth({'redisNoAuth':True,'redisPasswordConfigFile':'/run/recovery/redis.conf'},None)

    def test_native_config_requires_explicit_absolute_path(self):
        for path in ('redis.conf', '/run/../other/redis.conf'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'absolute'):
                source_redis_auth({'redisPasswordConfigFile':path},None)



class IncrementalSnapshotTransferTest(unittest.TestCase):
    """Real disk and subprocess tests, without SSH or a simulated deployment result."""
    def test_complete_snapshot_and_next_round_only_send_changed_blocks(self):
        import tempfile,subprocess,hashlib
        from intruoyi_rehearsal_agent import transfer_dispatch, PREFIX, TRANSFER_BLOCK_BYTES
        from intruoyi_runtime import require,file_sha
        with tempfile.TemporaryDirectory() as root:
            root=Path(root).resolve()
            source={'host':'source','stagingRoot':str(root/'source')}
            target={'host':'target','stagingRoot':str(root/'target')}
            api={'require':require,'file_sha':file_sha}
            def seed(profile,tag):
                folder=Path(profile['stagingRoot'])/'rehearsal-seed'/tag
                folder.mkdir(parents=True)
                (folder/'rehearsal-owned.json').write_text(json.dumps({'owner':PREFIX}))
                return folder/'minio.tar'
            def call(profile,action,**fields):
                return transfer_dispatch(dict(profile=profile,action=action,**fields),api)
            first=b'a'*TRANSFER_BLOCK_BYTES+b'b'*TRANSFER_BLOCK_BYTES+b'last'
            for round_number,content in enumerate((first,b'a'*TRANSFER_BLOCK_BYTES+b'c'*TRANSFER_BLOCK_BYTES+b'last')):
                tag='2026-10-22-20-00-0'+str(round_number)
                src,dst=seed(source,tag),seed(target,tag)
                src.write_bytes(content)
                job='JOB-'+str(round_number)*10
                index=call(source,'rehearsal-transfer-index',sourcePath=str(src),sha256=hashlib.sha256(content).hexdigest(),jobId=job)
                request=dict(index,destinationPath=str(dst),jobId=job)
                plan=call(target,'rehearsal-transfer-plan',**request)
                self.assertEqual(len(plan['missing']),3 if round_number==0 else 1)
                sender=call(source,'rehearsal-transfer-sender',sourcePath=str(src),chunks=plan['missing'],jobId=job)
                exported=subprocess.run([sys.executable,sender['script']],stdout=subprocess.PIPE,check=True).stdout
                self.assertEqual(len(exported),len(content) if round_number==0 else TRANSFER_BLOCK_BYTES)
                subprocess.run([sys.executable,plan['receiver']],input=exported,check=True)
                call(target,'rehearsal-transfer-assemble',**request)
                self.assertEqual(dst.read_bytes(),content)
            # Corrupt cache content must be rejected rather than reused or silently replaced.
            bad=Path(target['stagingRoot'])/'rehearsal-transfer-cache'/index['chunks'][0]['sha256']
            bad.write_bytes(b'corrupted')
            with self.assertRaisesRegex(RuntimeError,'corrupt'):
                call(target,'rehearsal-transfer-plan',**request)

    def test_transfer_refuses_paths_outside_owned_snapshot(self):
        from intruoyi_rehearsal_agent import transfer_artifact_path
        for path in ('/etc/passwd','/data/rehearsal-seed/2026-10-22-20-00-00/other.tar'):
            with self.assertRaises(ValueError):
                transfer_artifact_path({'stagingRoot':'/data'},path)

if __name__ == '__main__':
    unittest.main()
