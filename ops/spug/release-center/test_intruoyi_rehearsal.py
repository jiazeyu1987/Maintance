"""Real media-origin rewrite policy tests; no remote success is substituted."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from intruoyi_rehearsal_agent import rewrite_media_urls, isolated_backend_environment, redis_config_password, source_redis_auth, apply_checked_batches
from intruoyi_rehearsal import can_reuse_images
from intruoyi_rehearsal_agent import source_active_profiles, isolated_nginx_config
from intruoyi_rehearsal_agent import explicit_http_origin, rehearsal_endpoints, rehearsal_gateway_ingress, dispatch, PREFIX
from intruoyi_runtime import require, RuntimeBlocked
from unittest.mock import Mock, MagicMock, patch
from intruoyi_rehearsal_agent import source_backend_startup, isolated_backend_startup, source_upstream_hosts
from intruoyi_rehearsal_agent import validate_source_release_metadata


class SourceReleaseMetadataTest(unittest.TestCase):
    def test_full_release_and_frontend_patch_keep_separate_identities(self):
        validate_source_release_metadata({'releaseTag': 'base'}, {'releaseTag': 'base'})
        metadata = dict(releaseTag='patch', baseReleaseTag='base', frontendPatchTag='patch')
        observed = dict(releaseTag='base', frontendPatchTag='patch')
        validate_source_release_metadata(metadata, observed)
        for key in metadata:
            for value in ('other', '', None):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    validate_source_release_metadata(dict(metadata, **{key: value}), observed)
            incomplete = dict(metadata)
            incomplete.pop(key)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                validate_source_release_metadata(incomplete, observed)
        with self.assertRaises(ValueError):
            validate_source_release_metadata({'releaseTag': 'base'}, observed)
        with self.assertRaises(ValueError):
            validate_source_release_metadata(metadata, dict(observed, frontendPatchTag='other'))
        with self.assertRaises(ValueError):
            validate_source_release_metadata({'releaseTag': 'other'}, {'releaseTag': 'base'})


class FailedCaptureAbandonmentTest(unittest.TestCase):
    def test_incomplete_capture_requires_stopped_workers_and_unchanged_open_source(self):
        origin = 'a' * 64
        observed = dict(fingerprint=origin, backendHealth={'status': 'UP'}, frontendHttpStatus=200,
                        maintenance=False, readOnly=dict(read_only=False, super_read_only=False))
        request = dict(action='rehearsal-verify-stopped', profile={}, expectedOriginFingerprint=origin)
        api = dict(remote=Mock(), require=require, RuntimeBlocked=RuntimeBlocked,
                   observe=Mock(return_value=observed))
        with patch('intruoyi_rehearsal_agent.Path.iterdir', return_value=[]):
            result = dispatch(request, api)
            self.assertEqual(result, dict(stopped=True, originFingerprint=origin, sourceHealthy=True))
            for changes in [dict(fingerprint='b'*64), dict(backendHealth={'status':'DOWN'}),
                            dict(frontendHttpStatus=503), dict(maintenance=True),
                            dict(readOnly=dict(read_only=True, super_read_only=False))]:
                api['observe'].return_value = dict(observed, **changes)
                with self.subTest(changes=changes), self.assertRaises(RuntimeBlocked):
                    dispatch(request, api)
            with self.assertRaises(RuntimeBlocked):
                dispatch(dict(request, expectedOriginFingerprint=None), api)
        worker = MagicMock()
        worker.name = '999999'
        (worker / 'cmdline').read_bytes.return_value = b'python\0-\0'
        (worker / 'comm').read_text.return_value = 'python'
        with patch('intruoyi_rehearsal_agent.Path.iterdir', return_value=[worker]):
            with self.assertRaises(RuntimeBlocked):
                dispatch(request, api)


class SourceStartupContractTest(unittest.TestCase):
    def setUp(self):
        self.info={'Config':{'Env':[
            'ARGS=--spring.profiles.active=dev --spring.datasource.dynamic.datasource.master.url=jdbc:mysql://source/db --feature.key=preserved',
            'JAVA_OPTS=-Xms512m -Xmx2g -Djava.security.egd=file:/dev/./urandom',
            'SPRING_DATASOURCE_DYNAMIC_DATASOURCE_MASTER_URL=jdbc:mysql://source-env/db',
            'SPRING_DATA_REDIS_HOST=source-redis','CODEX_HOME=/host-only/codex','CUSTOM_SETTING=keep-me'],
            'Cmd':['sh','-c','exec java ${JAVA_OPTS} -jar app.jar ${ARGS}'], 'WorkingDir':'/app'},
            'Mounts':[{'Destination':'/host-only','Type':'bind'}, {'Destination':'/var/run/docker.sock','Type':'bind'}]}
        self.remote=Mock()
        def running_args(command):
            env=dict(v.split('=',1) for v in self.info['Config']['Env'])
            return ('\0'.join(['java',*env['JAVA_OPTS'].split(),'-jar','app.jar',*env['ARGS'].split()])+'\0').encode()
        self.remote.run.side_effect=running_args

    def test_observed_cli_format_preserves_arguments_environment_and_jvm_without_reading_a_file(self):
        startup=source_backend_startup(self.info,self.remote,'source')
        self.assertEqual(startup['format'],'shell-args-v1')
        self.assertEqual(startup['properties'],'')
        self.assertEqual(startup['jvmArguments'],['-Xms512m','-Xmx2g','-Djava.security.egd=file:/dev/./urandom'])
        self.assertIn('--feature.key=preserved',startup['arguments'])
        self.assertEqual(startup['environment']['CUSTOM_SETTING'],'keep-me')
        self.assertNotIn('ARGS',startup['environment'])
        self.assertNotIn('JAVA_OPTS',startup['environment'])
        self.assertEqual(startup['workingDirectory'],'/app')
        differences=startup['mountDifferences']
        self.assertEqual(differences['copiedSourceMountCount'],0)
        self.assertTrue(differences['dockerSocketExcluded'])
        self.assertEqual(differences['sourceMountReferenceCount'],1)
        self.assertNotIn('/host-only',json.dumps(differences))
        self.remote.run.assert_called_once_with(['docker','exec','source','cat','/proc/1/cmdline'])

    def test_isolation_cli_wins_over_source_arguments_environment_and_property_file(self):
        startup=source_backend_startup(self.info,self.remote,'source')
        startup['properties']='spring.data.redis.host=source-file\n'
        props={'spring.datasource.dynamic.datasource.master.url':'jdbc:mysql://isolated/db','spring.data.redis.host':'isolated-redis'}
        profile={'backendCommand':['java','-jar','app.jar','--spring.profiles.active=prod',
                                  '--spring.config.additional-location=file:/run/release/application.properties']}
        with patch('intruoyi_rehearsal_agent.isolated_backend_environment',return_value=['EDHR_S3_ENDPOINT=http://isolated-minio','INTRUOYI_RELEASE_MAINTENANCE=false']):
            command,environment=isolated_backend_startup(profile,startup,props,'dev',{},'private-fixture')
        self.assertEqual(command[:6],['java',*startup['jvmArguments'],'-jar','app.jar'])
        self.assertIn('--feature.key=preserved',command)
        self.assertIn('--spring.profiles.active=dev',command)
        self.assertNotIn('--spring.datasource.dynamic.datasource.master.url=jdbc:mysql://source/db',command)
        self.assertEqual(command[-2:],['--'+k+'='+v for k,v in sorted(props.items())])
        self.assertIn('SPRING_DATA_REDIS_HOST=source-redis',environment)
        self.assertIn('CUSTOM_SETTING=keep-me',environment)
        self.assertFalse(any(v.startswith(('ARGS=','JAVA_OPTS=')) for v in environment))
        self.assertEqual(sum(v.startswith('--spring.config.additional-location=') for v in command),1)

    def test_observed_assistant_host_jvm_property_is_preserved_and_isolation_override_wins(self):
        host = '-Dyudao.erp.fenbeitong-assistant.assistant-host=172.30.30.57'
        self.info['Config']['Env'][1] += ' ' + host
        startup = source_backend_startup(self.info, self.remote, 'source')
        self.assertIn(host, startup['jvmArguments'])
        props = {'yudao.erp.fenbeitong-assistant.assistant-host': 'isolated-assistant'}
        profile = {'backendCommand': ['java', '-jar', 'app.jar']}
        with patch('intruoyi_rehearsal_agent.isolated_backend_environment', return_value=[]):
            command, _ = isolated_backend_startup(profile, startup, props, 'dev', {}, '')
        self.assertIn(host, command)
        self.assertEqual(command[-1], '--yudao.erp.fenbeitong-assistant.assistant-host=isolated-assistant')
        self.remote.run.return_value = b'java\0-jar\0app.jar\0'
        self.remote.run.side_effect = None
        with self.assertRaisesRegex(ValueError, 'Running Java arguments differ'):
            source_backend_startup(self.info, self.remote, 'source')

    def test_registered_mounted_property_format_still_reads_exact_bind(self):
        self.info['Config']['Env'][0]+=' --spring.config.additional-location=file:/config/source.properties'
        self.info['Mounts'].append({'Destination':'/config/source.properties','Type':'bind'})
        self.remote.run.side_effect=None
        self.remote.run.return_value=b'feature.exact=original\n'
        startup=source_backend_startup(self.info,self.remote,'source')
        self.assertEqual(startup['format'],'mounted-properties-v1')
        self.assertEqual(startup['properties'],'feature.exact=original\n')
        self.assertFalse(any(arg.startswith('--spring.config.additional-location=') for arg in startup['arguments']))
        self.remote.run.assert_called_once_with(['docker','exec','source','cat','/config/source.properties'])

    def test_ambiguous_or_unobserved_loaders_and_jvm_are_rejected(self):
        cases=[('ARGS','--spring.profiles.active=dev --x=1 --x=2'),
               ('ARGS','--spring.profiles.active=dev --spring.config.import=file:/extra'),
               ('ARGS','--spring.profiles.active=dev --spring.config.additional-location=optional:file:/extra'),
               ('ARGS','--spring.profiles.active=dev --x="two words"'),
               ('JAVA_OPTS','-Dspring.data.redis.host=source'),
               ('SPRING_APPLICATION_JSON','{}'),('SPRING_CONFIG_LOCATION','file:/extra')]
        for key,value in cases:
            with self.subTest(key=key,value=value):
                self.setUp()
                self.info['Config']['Env']=[v for v in self.info['Config']['Env'] if not v.startswith(key+'=')]+[key+'='+value]
                with self.assertRaises(ValueError):source_backend_startup(self.info,self.remote,'source')
                self.remote.run.assert_not_called()

    def test_unobserved_shell_command_is_not_treated_as_cli_only(self):
        self.info['Config']['Cmd'][-1]+=' --spring.data.redis.host=source'
        with self.assertRaisesRegex(ValueError,'inspected shell argument contract'):
            source_backend_startup(self.info,self.remote,'source')
        self.remote.run.assert_not_called()

    def test_literal_argument_bytes_are_preserved_from_verified_process_argv(self):
        self.info['Config']['Env'][0]+=r' --source.path=C:\original\archive --source.literal="quoted"'
        startup=source_backend_startup(self.info,self.remote,'source')
        self.assertIn(r'--source.path=C:\original\archive',startup['arguments'])
        self.assertIn('--source.literal="quoted"',startup['arguments'])

    def test_changed_running_java_arguments_are_rejected(self):
        self.remote.run.side_effect=None
        self.remote.run.return_value=b'java\0-jar\0different.jar\0'
        with self.assertRaisesRegex(ValueError,'Running Java arguments differ'):
            source_backend_startup(self.info,self.remote,'source')


class RehearsalIngressTest(unittest.TestCase):
    def setUp(self):
        self.profile=dict(host='172.30.30.58',environment='rehearsal',
                          entryUrl='http://172.30.30.58:38092',acceptanceUrl='http://172.30.30.58:38093',
                          isolatedMinioPublicUrl='http://172.30.30.58:39092',backendEntrypoint=None,
                          backendCommand=['--spring.config.additional-location=file:/run/release/application.properties'],
                          minioDataPath='/data')
        self.profile.update({key:PREFIX+'-'+key for key in ('frontend','backend','database','redis','minio','network','acceptanceFrontend')})

    def test_registered_ports_drive_gateway_listener_bindings_and_exposure(self):
        result=rehearsal_gateway_ingress(self.profile)
        for port,upstream in ((38092,self.profile['frontend']+':80'),
                              (38093,self.profile['acceptanceFrontend']+':80'),
                              (39092,self.profile['minio']+':9000')):
            self.assertIn('listen '+str(port)+';',result['nginx'])
            self.assertIn('set $upstream "'+upstream+'";',result['nginx'])
            self.assertEqual(result['portBindings'][str(port)+'/tcp'],[{'HostIp':'172.30.30.58','HostPort':str(port)}])
        self.assertEqual(set(result['portBindings']),set(result['exposedPorts']))
        self.assertEqual(len(result['exposedPorts']),3)
        for port in ('38082','38083','39082'):
            self.assertNotIn(port,result['nginx'])

    def test_duplicate_ports_or_unregistered_host_fail(self):
        for key,value in (('acceptanceUrl',self.profile['entryUrl']),
                          ('isolatedMinioPublicUrl','http://172.30.30.57:39092')):
            with self.subTest(key=key),self.assertRaises(ValueError):
                rehearsal_endpoints(dict(self.profile,**{key:value}))

    def test_origin_requires_explicit_safe_host_port_without_extra_url_parts(self):
        for value in ('http://172.30.30.58','http://172.30.30.58:0','http://172.30.30.58:65536',
                      'http://0.0.0.0:38092','http://224.0.0.1:38092','http://host;command:38092',
                      'http://user:secret@172.30.30.58:38092','https://172.30.30.58:38092',
                      'http://172.30.30.58:38092/','http://172.30.30.58:38092?q=1','http://172.30.30.58:38092#fragment'):
            with self.subTest(value=value),self.assertRaises(ValueError): explicit_http_origin(value)
        self.assertEqual(explicit_http_origin('http://172.30.30.58:39092'),{'host':'172.30.30.58','port':39092})

    def test_target_check_binds_only_registered_addresses(self):
        remote=Mock()
        remote.run.return_value=b''
        api={'remote':remote,'require':require,'RuntimeBlocked':RuntimeBlocked,'check_storage':Mock()}
        with patch('intruoyi_rehearsal_agent.socket.socket') as socket:
            result=dispatch({'profile':self.profile,'action':'rehearsal-target-check'},api)
        self.assertEqual(result,{'ready':True,'mutations':False})
        self.assertEqual([call.args[0] for call in socket.return_value.bind.call_args_list],
                         [('172.30.30.58',38092),('172.30.30.58',38093),('172.30.30.58',39092)])
        self.assertEqual(socket.return_value.close.call_count,3)

    def test_bound_port_fails_without_trying_another_port(self):
        remote=Mock()
        remote.run.return_value=b''
        api={'remote':remote,'require':require,'RuntimeBlocked':RuntimeBlocked,'check_storage':Mock()}
        with patch('intruoyi_rehearsal_agent.socket.socket') as socket:
            socket.return_value.bind.side_effect=OSError('occupied')
            with self.assertRaisesRegex(RuntimeBlocked,'38092'):
                dispatch({'profile':self.profile,'action':'rehearsal-target-check'},api)
        socket.return_value.bind.assert_called_once_with(('172.30.30.58',38092))
        socket.return_value.close.assert_called_once()


class BaselineStartupTest(unittest.TestCase):
    def test_capture_includes_source_alias_only_on_frontend_shared_network(self):
        source={'NetworkSettings':{'Networks':{
            'shared':{'IPAddress':'172.29.1.2','Aliases':['intruoyi-backend','backend']},
            'private':{'IPAddress':'172.28.1.2','Aliases':['private-service']}}}}
        frontend={'NetworkSettings':{'Networks':{'shared':{}}}}
        self.assertEqual(source_upstream_hosts(source,frontend,'intruoyi-backend'),
                         ['172.28.1.2','172.29.1.2','backend','intruoyi-backend'])

    def test_exact_proxy_host_rewrite_preserves_paths_and_unrelated_names(self):
        original=('server { listen 172.30.30.57:8081; '
                  'proxy_pass http://backend:48081/admin-api/; '
                  'proxy_pass http://minio:9000/yudao/; '
                  'proxy_pass http://backend-other:48081/; '
                  'proxy_pass http://backend.example:48081/; '
                  'proxy_pass http://backend/; '
                  'add_header X-Reference http://backend:48081; }')
        result=isolated_nginx_config(original,8081,['backend'],'isolated-backend',['minio'],'isolated-minio')
        self.assertIn('proxy_pass http://isolated-backend:48081/admin-api/;',result)
        self.assertIn('proxy_pass http://isolated-minio:9000/yudao/;',result)
        self.assertIn('proxy_pass http://isolated-backend/;',result)
        self.assertIn('proxy_pass http://backend-other:48081/;',result)
        self.assertIn('proxy_pass http://backend.example:48081/;',result)
        self.assertIn('add_header X-Reference http://backend:48081;',result)

    def test_ambiguous_role_alias_cannot_be_rewritten(self):
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            isolated_nginx_config('listen 8081; proxy_pass http://shared:48081;',8081,
                                  ['shared'],'backend',['shared'],'minio')

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
        with self.assertRaisesRegex(ValueError, 'source media origin'):
            rewrite_media_urls('http://127.0.0.1:9000/yudao/a', self.source, 'http://172.30.30.57:9000')

    def test_explicit_new_media_port_preserves_object_bytes(self):
        original='http://127.0.0.1:9000/yudao/showroom/%E5%B1%95%E5%8E%85/a%20b.png'
        changed,count=rewrite_media_urls(original,self.source,'http://172.30.30.58:39092')
        self.assertEqual(count,1)
        self.assertEqual(changed,original.replace('http://127.0.0.1:9000','http://172.30.30.58:39092'))

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
                subprocess.run([sys.executable,plan['batches'][0]['receiver']],input=exported,check=True)
                call(target,'rehearsal-transfer-assemble',**request)
                self.assertEqual(dst.read_bytes(),content)
            # Corrupt cache content must be rejected rather than reused or silently replaced.
            bad=Path(target['stagingRoot'])/'rehearsal-transfer-cache'/index['chunks'][0]['sha256']
            bad.write_bytes(b'corrupted')
            with self.assertRaisesRegex(RuntimeError,'corrupt'):
                call(target,'rehearsal-transfer-plan',**request)

    def test_interrupted_large_artifacts_keep_verified_blocks_and_resume(self):
        import tempfile, subprocess, hashlib, struct
        from unittest.mock import patch
        from intruoyi_rehearsal_agent import transfer_dispatch, PREFIX
        from intruoyi_runtime import require, file_sha
        for name in ('recovery.sql','recovery.sql.gz','origin-images.tar','minio.tar'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory, patch('intruoyi_rehearsal_agent.TRANSFER_BLOCK_BYTES',8):
                root=Path(directory).resolve()
                source=dict(stagingRoot=str(root/'source'),host='source')
                target=dict(stagingRoot=str(root/'target'),host='target')
                paths=[]
                for profile in (source,target):
                    folder=Path(profile['stagingRoot'])/'rehearsal-seed'/'2026-10-24-03-24-24'
                    folder.mkdir(parents=True)
                    (folder/'rehearsal-owned.json').write_text(json.dumps(dict(owner=PREFIX)))
                    paths.append(folder/name)
                src,dst=paths
                content=b''.join(struct.pack('Q',i) for i in range(67))
                src.write_bytes(content)
                api=dict(require=require,file_sha=file_sha)
                def call(profile,action,**kwargs):
                    return transfer_dispatch(dict(profile=profile,action=action,jobId='JOB-1234567890',**kwargs),api)
                index=call(source,'rehearsal-transfer-index',sourcePath=str(src),sha256=hashlib.sha256(content).hexdigest())
                request=dict(index,destinationPath=str(dst))
                plan=call(target,'rehearsal-transfer-plan',**request)
                self.assertEqual([len(x['chunks']) for x in plan['batches']],[64,3])
                first=plan['batches'][0]
                sender=call(source,'rehearsal-transfer-sender',sourcePath=str(src),chunks=first['chunks'])
                exported=subprocess.check_output([sys.executable,sender['script']])
                subprocess.run([sys.executable,first['receiver']],input=exported,check=True)
                # Simulate a real EOF midway through the second batch.
                failed=subprocess.run([sys.executable,plan['batches'][1]['receiver']],input=content[512:524],capture_output=True)
                self.assertNotEqual(failed.returncode,0)
                resumed=call(target,'rehearsal-transfer-plan',**request)
                self.assertEqual(len(resumed['missing']),2)
                for batch in resumed['batches']:
                    sender=call(source,'rehearsal-transfer-sender',sourcePath=str(src),chunks=batch['chunks'])
                    data=subprocess.check_output([sys.executable,sender['script']])
                    subprocess.run([sys.executable,batch['receiver']],input=data,check=True)
                call(target,'rehearsal-transfer-assemble',**request)
                self.assertEqual(dst.read_bytes(),content)

    def test_transfer_refuses_paths_outside_owned_snapshot(self):
        from intruoyi_rehearsal_agent import transfer_artifact_path
        for path in ('/etc/passwd','/data/rehearsal-seed/2026-10-22-20-00-00/other.tar'):
            with self.assertRaises(ValueError):
                transfer_artifact_path({'stagingRoot':'/data'},path)

if __name__ == '__main__':
    unittest.main()
