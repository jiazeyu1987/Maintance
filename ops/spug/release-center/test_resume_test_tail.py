"""Component checks for tail-resume boundaries; never contacts Docker or SSH."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked, file_sha, package_identity, sha


class StartupWaitTest(unittest.TestCase):
    def test_default_and_explicit_wait_cover_196_second_start(self):
        profile={'acceptanceUrl':'http://acceptance','entryUrl':'http://public','backend':'backend'}
        for timeout, succeeds in ((None,True),(240,True),(180,False)):
            with self.subTest(timeout=timeout):
                current=[0]
                configured=dict(profile)
                if timeout is not None: configured['startupTimeout']=timeout
                def fetch(url,timeout):
                    if url.endswith('/release-info.json'):
                        return io.BytesIO(json.dumps({'releaseTag':'tag'}).encode())
                    if current[0] < 196:
                        raise ConnectionRefusedError('still starting')
                    value={'status':'UP'} if url.endswith('/health') else {'status':'available','releaseTag':'tag','maintenance':False}
                    return io.BytesIO(json.dumps(value).encode())
                def response(url,timeout):
                    result=fetch(url,timeout)
                    result.status=200
                    return result
                with patch.object(agent.time,'monotonic',side_effect=lambda:current[0]), \
                        patch.object(agent.time,'sleep',side_effect=lambda seconds:current.__setitem__(0,current[0]+seconds)), \
                        patch.object(agent,'urlopen',side_effect=response), \
                        patch.object(agent.remote,'inspect',return_value={'NetworkSettings':{'Networks':{'net':{'IPAddress':'172.29.235.25'}}}}):
                    if succeeds:
                        self.assertEqual(agent.health(configured,'tag',False)['releaseTag'],'tag')
                        self.assertEqual(current[0],196)
                    else:
                        with self.assertRaisesRegex(RuntimeBlocked,'timed out'): agent.health(configured,'tag',False)

    def test_timeout_must_be_positive_finite_number(self):
        self.assertEqual(agent.startup_timeout({}),600)
        for value in (0,-1,True,None,'600',float('inf'),float('nan')):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeBlocked,'positive finite'):
                agent.startup_timeout({'startupTimeout':value})


class AcceptanceIngressTest(unittest.TestCase):
    def setUp(self):
        self.profile = dict(environment='test', acceptanceNetwork='internal-net', backend='backend',
                            frontend='frontend', host='172.30.30.58', entryUrl='http://172.30.30.58:8081',
                            acceptanceUrl='http://172.30.30.58:38084', acceptanceBindAddress='172.30.30.58',
                            acceptanceFrontend='acceptance')
        self.nginx = 'server {\n listen 172.30.30.58:8081;\n location /api/ { proxy_pass http://172.29.235.25:48081; }\n}\n'
        self.backend = {'NetworkSettings':{'Networks':{'internal-net':{'IPAddress':'172.29.235.25', 'Aliases':['backend-alias']}}}}
        self.frontend = {'Image':'frontend-image','Config':{'Env':[], 'Image':'frontend-image'},
                         'HostConfig':{'NetworkMode':'host'}, 'NetworkSettings':{'Networks':{}}}

    def archive(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w') as archive:
            entry = tarfile.TarInfo('default.conf')
            data = self.nginx.encode()
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        return output.getvalue()

    def remote_run(self, command):
        return json.dumps([{'Driver':'bridge','Internal':True}]).encode() if command[1] == 'network' else self.archive()

    def inspect(self, name):
        if name == 'backend':
            return self.backend
        return self.frontend

    def bridge_frontend(self, host_ip='', host_port='8081'):
        self.frontend['HostConfig'] = {'NetworkMode':'internal-net', 'PortBindings':{
            '80/tcp':[{'HostIp':host_ip, 'HostPort':host_port}]}}
        self.frontend['NetworkSettings']['Networks'] = {'internal-net':{}}
        self.nginx = self.nginx.replace('172.30.30.58:8081', '80')

    def test_bridge_published_port_selects_container_listener_and_registered_alias(self):
        for host_ip, host_port in (('', '8081'), ('172.30.30.58', '38081')):
            with self.subTest(host_ip=host_ip, host_port=host_port):
                self.bridge_frontend(host_ip, host_port)
                self.profile['entryUrl'] = 'http://172.30.30.58:' + host_port
                self.nginx = self.nginx.replace('172.29.235.25:48081', 'backend-alias:48081')
                with patch.object(agent.remote, 'run', side_effect=self.remote_run), patch.object(agent.remote, 'inspect', side_effect=self.inspect):
                    spec = agent.acceptance_spec(self.profile)
                self.assertIn('listen 172.30.30.58:38084;', spec['nginx'])
                self.assertIn('http://172.29.235.25:48081', spec['nginx'])
                self.assertEqual(self.profile['entryUrl'], 'http://172.30.30.58:' + host_port)

    def test_bridge_missing_wrong_host_or_ambiguous_mapping_is_rejected(self):
        for bindings in ({}, {'80/tcp':[{'HostIp':'172.30.30.99','HostPort':'8081'}]},
                         {'80/tcp':[{'HostIp':'','HostPort':'8081'}], '81/tcp':[{'HostIp':'','HostPort':'8081'}]}):
            with self.subTest(bindings=bindings):
                self.bridge_frontend()
                self.frontend['HostConfig']['PortBindings'] = bindings
                with patch.object(agent.remote, 'run', side_effect=self.remote_run), patch.object(agent.remote, 'inspect', side_effect=self.inspect):
                    with self.assertRaisesRegex(RuntimeBlocked, 'unique Docker TCP listener'):
                        agent.acceptance_spec(self.profile)

    def test_alias_requires_registered_shared_network(self):
        for shared in (False, True):
            with self.subTest(shared=shared):
                self.bridge_frontend()
                self.frontend['NetworkSettings']['Networks'] = {'other-net':{}}
                self.backend['NetworkSettings']['Networks']['other-net'] = {'Aliases':['other-alias']}
                if shared:
                    self.frontend['NetworkSettings']['Networks']['internal-net'] = {}
                alias = 'other-alias' if shared else 'backend-alias'
                self.nginx = 'server { listen 80; proxy_pass http://' + alias + ':48081; }'
                with patch.object(agent.remote, 'run', side_effect=self.remote_run), patch.object(agent.remote, 'inspect', side_effect=self.inspect):
                    with self.assertRaisesRegex(RuntimeBlocked, 'upstream is not registered'):
                        agent.acceptance_spec(self.profile)

    def test_internal_backend_network_uses_explicit_host_listener(self):
        with patch.object(agent.remote, 'run', side_effect=self.remote_run), patch.object(agent.remote, 'inspect', side_effect=self.inspect):
            spec = agent.acceptance_spec(self.profile)
        self.assertEqual(spec['network'], 'host')
        self.assertIn('listen 172.30.30.58:38084;', spec['nginx'])
        self.assertIn('http://172.29.235.25:48081', spec['nginx'])

    def test_rehearsal_keeps_bridge_80_without_host_publish(self):
        self.profile['environment'] = 'rehearsal'
        self.nginx = self.nginx.replace('172.30.30.58:8081', '80')
        with tempfile.TemporaryDirectory() as folder, patch.object(agent.remote, 'run', side_effect=self.remote_run), \
                patch.object(agent.remote, 'inspect', side_effect=self.inspect), patch.object(agent, 'docker', return_value={'Id':'created'}) as docker:
            agent.acceptance_frontend(self.profile, Path(folder))
        config = docker.call_args_list[0].args[2]
        self.assertEqual(config['HostConfig']['NetworkMode'], 'internal-net')
        self.assertEqual(config['HostConfig']['PortBindings'], {})
        self.assertEqual(config['NetworkingConfig'], {'EndpointsConfig':{'internal-net':{}}})

    def test_host_create_has_no_bridge_or_port_publish(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(agent.remote, 'run', side_effect=self.remote_run), \
                patch.object(agent.remote, 'inspect', side_effect=self.inspect), patch.object(agent, 'docker', return_value={'Id':'created'}) as docker:
            agent.acceptance_frontend(self.profile, Path(folder))
        config = docker.call_args_list[0].args[2]
        self.assertEqual(config['HostConfig']['NetworkMode'], 'host')
        self.assertEqual(config['HostConfig']['PortBindings'], {})
        self.assertNotIn('NetworkingConfig', config)

    def test_unregistered_bind_is_rejected(self):
        self.profile['acceptanceBindAddress'] = '0.0.0.0'
        with patch.object(agent.remote, 'run', side_effect=self.remote_run), patch.object(agent.remote, 'inspect', side_effect=self.inspect):
            with self.assertRaisesRegex(RuntimeBlocked, 'Registered acceptance'):
                agent.acceptance_spec(self.profile)


class AcceptanceRepairTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.attempt=self.root/'resume-JOB-2222222222'
        self.attempt.mkdir()
        self.profile=dict(acceptanceFrontend='acceptance',acceptanceNetwork='internal-net',
                          acceptanceBindAddress='172.30.30.58',acceptanceUrl='http://172.30.30.58:38084')
        self.manifest={'images':{'frontend':{'id':'frontend-image'}}}
        self.new='server { listen 172.30.30.58:38084; proxy_pass http://172.29.235.25:48081; }'
        self.old=self.new.replace('172.30.30.58:38084','80')
        (self.root/'acceptance-nginx.conf').write_text(self.old)
        self.original=dict(Id='old',Image='frontend-image',Name='/acceptance',State={'Running':False},
                           Config={'Labels':{'intruoyi.release.acceptance':'true'}},
                           Mounts=[{'Source':str(self.root/'acceptance-nginx.conf'),
                                    'Destination':'/etc/nginx/conf.d/default.conf','RW':False}],
                           HostConfig={'NetworkMode':'internal-net','PortBindings':{
                               '80/tcp':[{'HostIp':'172.30.30.58','HostPort':'38084'}]}})
        self.docker=patch.object(agent,'docker',side_effect=lambda method,path,*args:[{'Id':'old','Names':['/acceptance']}] if method=='GET' else None).start()
        self.addCleanup(patch.stopall)
        self.inspect=patch.object(agent.remote,'inspect',return_value=self.original).start()
        self.run=patch.object(agent.remote,'run').start()
        self.create=patch.object(agent,'acceptance_frontend').start()
        patch.object(agent,'acceptance_spec',return_value={'nginx':self.new}).start()

    def invoke(self,previous=None):
        return agent.repair_acceptance_frontend(self.profile,self.root,self.attempt,self.manifest,previous or [])

    def test_failed_container_is_retained_and_original_configuration_unmodified(self):
        self.invoke()
        self.assertTrue((self.attempt/'acceptance-before.private.json').is_file())
        self.assertEqual((self.root/'acceptance-nginx.conf').read_text(),self.old)
        self.docker.assert_any_call('POST','/containers/old/rename?name=acceptance-failed-JOB-2222222222')
        self.create.assert_called_once_with(self.profile,self.attempt)
        self.assertFalse(any('rm' in str(call) for call in self.run.call_args_list))

    def test_unowned_label_or_changed_config_is_rejected_before_stop(self):
        self.original['Config']['Labels']={}
        with self.assertRaisesRegex(RuntimeBlocked,'ownership/image'): self.invoke()
        self.original['Config']['Labels']={'intruoyi.release.acceptance':'true'}
        (self.root/'acceptance-nginx.conf').write_text(self.old+'changed')
        with self.assertRaisesRegex(RuntimeBlocked,'nginx bytes differ'): self.invoke()
        self.create.assert_not_called()
        self.run.assert_not_called()

    def test_arbitrary_mount_and_wrong_network_are_rejected(self):
        self.original['Mounts'][0]['RW']=True
        with self.assertRaisesRegex(RuntimeBlocked,'configuration is not owned'): self.invoke()
        self.original['Mounts'][0]['RW']=False
        self.original['HostConfig']['NetworkMode']='other'
        with self.assertRaisesRegex(RuntimeBlocked,'network/port configuration'): self.invoke()

    def test_previous_attempt_host_container_is_validated_and_preserved(self):
        previous=self.root/'resume-JOB-1111111111'
        previous.mkdir()
        (previous/'acceptance-nginx.conf').write_text(self.new)
        self.original['Mounts'][0]['Source']=str(previous/'acceptance-nginx.conf')
        self.original['HostConfig']={'NetworkMode':'host','PortBindings':{}}
        self.invoke([(previous/'receipt.private.json',{})])
        self.create.assert_called_once()

    def test_missing_acceptance_requires_real_retained_container(self):
        self.docker.side_effect=lambda *args:[]
        with self.assertRaisesRegex(RuntimeBlocked,'without retained retry evidence'): self.invoke()
        previous=self.root/'resume-JOB-1111111111'
        previous.mkdir()
        (previous/'acceptance-before.private.json').write_text(json.dumps(self.original))
        with self.assertRaisesRegex(RuntimeBlocked,'cannot be verified'):
            self.invoke([(previous/'receipt.private.json',{})])
        self.original['Name']='/acceptance-failed-JOB-1111111111'
        self.invoke([(previous/'receipt.private.json',{})])
        self.create.assert_called_once()


class ResumeTailTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tag = '2026-10-23-15-17-12'
        self.original = 'JOB-1111111111'
        self.retry = 'JOB-2222222222'
        self.profile = dict(environment='test', backend='backend', frontend='frontend', acceptanceFrontend='acceptance',
                            writerInventoryConfirmed=True, writers=['backend'])
        migration = dict(migrationId='one', sha256='a'*64, type='schema', allowedEnvironments=['test'])
        self.manifest = dict(releaseTag=self.tag, maintenanceProtocol=agent.PROTOCOL, files=[], migrations=[migration],
                             images={'backend':{'id':'candidate-backend'},'frontend':{'id':'candidate-frontend'}},
                             executionPlans={'test':dict(status='passed',targetEnvironment='test',items=[dict(migrationId='one',sha256='a'*64,action='SKIP_ALREADY_APPLIED')])})
        self.write('manifest.json', self.manifest)
        (self.root/'release.tar').write_bytes(b'immutable release package')
        (self.root/'recovery.sql').write_bytes(b'immutable full recovery snapshot')
        self.recovery = dict(path=str(self.root/'recovery.sql'),sha256=file_sha(self.root/'recovery.sql'),
                             includes=['data','schema','triggers','events','routines'])
        self.write('recovery-record.private.json', self.recovery)
        self.write('stage-verified.json', dict(manifestSha256=package_identity(self.manifest),files=[],archive={
            'archiveSha256':file_sha(self.root/'release.tar'),'manifestSha256':file_sha(self.root/'manifest.json')}))
        self.write('deployment-progress.private.json',dict(jobId=self.original,releaseTag=self.tag,phase='failed',pid=999999,processStart='gone'))
        self.containers = {}
        for role in ('backend','frontend'):
            self.containers[role] = dict(Id='candidate-'+role,Image='candidate-'+role,State={'Running':role=='backend'})
            before = dict(Id='original-'+role,Image='original-'+role,Name='/'+role,State={'Running':False})
            self.write(role+'-before-initial.private.json', before)
            self.containers[role+'-before-'+self.tag] = before
        self.obs = dict(ledgerRecords=[dict(migrationId='one',sha256='a'*64,status='APPLIED')],
                        schemaSha256='s'*64,ledgerSha256='l'*64,maintenance=True,frontendHttpStatus=None)
        self.result = dict(self.obs,maintenance=False,frontendHttpStatus=200)
        self.payload = dict(manifest=self.manifest,originalJobId=self.original,retryJobId=self.retry,
                            originalPlan=[dict(migrationId='one',sha256='a'*64,action='APPLY')],
                            packageSha256=file_sha(self.root/'release.tar'),manifestSha256=file_sha(self.root/'manifest.json'))
        mocks = {
            'check_fence':patch.object(agent,'check_fence'),
            'observe':patch.object(agent,'observe',return_value=self.obs),
            'inspect':patch.object(agent.remote,'inspect',side_effect=lambda name:self.containers[name]),
            'sql':patch.object(agent.remote,'sql',return_value='one\t'+'a'*64+'\tAPPLIED'),
            'backend':patch.object(agent,'resume_backend_health',return_value={'maintenance':True,'schedulingDisabled':True,'consumersDisabled':True}),
            'repair':patch.object(agent,'repair_acceptance_frontend'),
            'health':patch.object(agent,'health',return_value={'maintenance':True}),
            'reopen':patch.object(agent,'reopen',return_value=self.result),
            'process':patch('intruoyi_rehearsal_agent.process_start_identity',side_effect=lambda pid:'current' if pid==os.getpid() else None),
            'apply':patch.object(agent,'apply_migration_plan'),
            'backup':patch.object(agent,'backup'),
        }
        self.mock = {}
        for name, item in mocks.items():
            self.mock[name] = item.start()
            self.addCleanup(item.stop)

    def write(self, name, value):
        (self.root/name).write_text(json.dumps(value))

    def invoke(self):
        return agent.resume_test_tail_locked(self.profile,self.payload,self.root)

    def receipt(self):
        return json.loads((self.root/('resume-'+self.retry)/'receipt.private.json').read_text())

    def test_complete_tail_never_runs_sql_or_backup_and_preserves_original(self):
        original = (self.root/'deployment-progress.private.json').read_bytes()
        result = self.invoke()
        self.assertEqual(result['resumeReceipt']['status'],'completed')
        self.assertEqual(result['resumeReceipt']['completedByJobId'],self.retry)
        self.assertEqual(result['recoveryPoint'],self.recovery)
        self.mock['apply'].assert_not_called()
        self.mock['backup'].assert_not_called()
        self.mock['reopen'].assert_called_once()
        self.assertEqual((self.root/'deployment-progress.private.json').read_bytes(),original)

    def test_rejects_formal_target_active_worker_archive_or_snapshot_change(self):
        self.profile['environment']='prod'
        with self.assertRaisesRegex(RuntimeBlocked,'restricted to test'): self.invoke()
        self.profile['environment']='test'
        self.mock['process'].side_effect=lambda pid:'gone'
        with self.assertRaisesRegex(RuntimeBlocked,'worker remains active'): self.invoke()
        self.mock['process'].side_effect=lambda pid:'current' if pid==os.getpid() else None
        (self.root/'release.tar').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeBlocked,'package bytes differ'): self.invoke()
        (self.root/'release.tar').write_bytes(b'immutable release package')
        (self.root/'recovery.sql').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeBlocked,'snapshot differs'): self.invoke()
        self.mock['repair'].assert_not_called()

    def test_exact_apply_ledger_and_candidate_are_required(self):
        self.mock['sql'].return_value='one\t'+'a'*64+'\tRUNNING'
        with self.assertRaisesRegex(RuntimeBlocked,'not exactly completed'): self.invoke()
        self.mock['sql'].return_value='one\t'+'a'*64+'\tAPPLIED'
        self.containers['backend']['Image']='other'
        with self.assertRaisesRegex(RuntimeBlocked,'candidate image differs'): self.invoke()
        self.mock['repair'].assert_not_called()

    def test_remaining_apply_or_open_public_entry_is_rejected(self):
        with patch.object(agent,'migration_plan',return_value=[dict(migrationId='one',action='APPLY')]):
            with self.assertRaisesRegex(RuntimeBlocked,'remaining migrations'): self.invoke()
        self.containers['frontend']['State']['Running']=True
        with self.assertRaisesRegex(RuntimeBlocked,'Public frontend'): self.invoke()

    def test_missing_writer_controls_prevents_acceptance_mutation(self):
        self.mock['backend'].side_effect=RuntimeBlocked('Backend scheduling/consumer controls are not disabled')
        with self.assertRaisesRegex(RuntimeBlocked,'controls'): self.invoke()
        self.mock['repair'].assert_not_called()

    def test_preopening_failure_has_receipt_and_allows_new_explicit_retry(self):
        self.mock['repair'].side_effect=RuntimeBlocked('repair failed')
        with self.assertRaisesRegex(RuntimeBlocked,'repair failed'): self.invoke()
        receipt=self.receipt()
        self.assertEqual((receipt['status'],receipt['phase']),('failed','acceptance-repair'))
        receipt['pid']=999998
        self.write('resume-'+self.retry+'/receipt.private.json',receipt)
        self.payload['retryJobId']='JOB-3333333333'
        self.mock['repair'].side_effect=None
        self.assertEqual(self.invoke()['resumeReceipt']['status'],'completed')

    def test_opening_failure_is_blocked_from_second_resume(self):
        self.mock['reopen'].side_effect=RuntimeBlocked('opening failed')
        with self.assertRaisesRegex(RuntimeBlocked,'opening failed'): self.invoke()
        receipt=self.receipt()
        self.assertEqual(receipt['phase'],'opening')
        receipt['pid']=999998
        self.write('resume-'+self.retry+'/receipt.private.json',receipt)
        self.payload['retryJobId']='JOB-3333333333'
        with self.assertRaisesRegex(RuntimeBlocked,'technical restoration'): self.invoke()
        self.assertEqual(self.mock['reopen'].call_count,1)

    def prepare_opening(self):
        self.mock['reopen'].side_effect=RuntimeBlocked('normal backend startup exceeded previous deadline')
        with self.assertRaises(RuntimeBlocked): self.invoke()
        receipt=self.receipt()
        receipt['pid']=999998
        self.write('resume-'+self.retry+'/receipt.private.json',receipt)
        original_receipt=(self.root/('resume-'+self.retry)/'receipt.private.json').read_bytes()
        self.payload['retryJobId']='JOB-3333333333'
        before=dict(Id='maintenance-backend',Name='/backend',Image='candidate-backend',
                    State={'Running':False,'ExitCode':0,'Status':'exited'},
                    Config={'Image':'candidate-backend','Env':['INTRUOYI_RELEASE_MAINTENANCE=true']},
                    HostConfig={'NetworkMode':'internal-net','PortBindings':{}},Mounts=[],
                    NetworkSettings={'Networks':{'internal-net':{
                        'IPAMConfig':{'IPv4Address':'172.29.235.25'},'IPAddress':'','Aliases':['backend']}}})
        self.write('backend-before-reopen.private.json',before)
        self.containers['backend-before-'+self.tag+'-maintenance']=copy.deepcopy(before)
        backend=copy.deepcopy(before)
        backend.update(Id='normal-backend',State={'Running':True,'Status':'running'})
        backend['Config']['Env']=['INTRUOYI_RELEASE_MAINTENANCE=false']
        backend['NetworkSettings']['Networks']['internal-net']['IPAddress']='172.29.235.25'
        self.containers['backend']=backend
        self.profile['acceptanceNetwork']='internal-net'
        config_path=self.root/('resume-'+self.retry)/'acceptance-nginx.conf'
        config_path.write_text('owned host nginx')
        self.containers['acceptance']=dict(Id='acceptance-id',Image='candidate-frontend',
            State={'Running':True,'Status':'running'},Config={'Labels':{'intruoyi.release.acceptance':'true'}},
            HostConfig={'NetworkMode':'host','PortBindings':{}},
            Mounts=[{'Source':str(config_path),'Destination':'/etc/nginx/conf.d/default.conf','RW':False}])
        self.mock['observe'].side_effect=[dict(self.obs,maintenance=False),self.result]
        self.mock['health'].return_value={'maintenance':False,'releaseTag':self.tag}
        spec=patch.object(agent,'acceptance_spec',return_value={'nginx':'owned host nginx'})
        spec.start()
        self.addCleanup(spec.stop)
        return original_receipt

    def test_healthy_opening_resumes_only_entry_and_stopped_registered_writers(self):
        previous=self.prepare_opening()
        self.profile['writers']+=['worker-stopped','worker-running']
        for name,running in [('worker-stopped',False),('worker-running',True)]:
            self.containers[name]={'Id':name,'State':{'Running':running,'Status':'running' if running else 'exited'}}
        def docker(method,path,*args):
            name=path.split('/')[2]
            self.containers[name]['State']['Running']=True
        def run(command):
            if command[1]=='stop': self.containers['acceptance']['State']['Running']=False
        with patch.object(agent,'docker',side_effect=docker) as calls,patch.object(agent.remote,'run',side_effect=run), \
                patch.object(agent,'replace') as replace:
            result=self.invoke()
        self.assertEqual(result['resumeReceipt']['resumeMode'],'opening-finalization')
        self.assertEqual(result['resumeReceipt']['status'],'completed')
        self.assertEqual([call.args[1] for call in calls.call_args_list],['/containers/worker-stopped/start','/containers/frontend/start'])
        self.assertEqual((self.root/('resume-'+self.retry)/'receipt.private.json').read_bytes(),previous)
        self.assertEqual(self.mock['reopen'].call_count,1)
        self.assertEqual(self.mock['repair'].call_count,1)
        replace.assert_not_called()
        self.mock['apply'].assert_not_called()
        self.mock['backup'].assert_not_called()

    def test_opening_wrong_normal_identity_or_acceptance_is_rejected(self):
        self.prepare_opening()
        self.mock['observe'].side_effect=None
        self.mock['observe'].return_value=dict(self.obs,maintenance=False)
        self.containers['backend']['Config']['Env'].append('UNREVIEWED_CHANGE=true')
        with patch.object(agent,'docker') as calls:
            with self.assertRaisesRegex(RuntimeBlocked,'Normal backend identity/configuration'): self.invoke()
            self.containers['backend']['Config']['Env'].pop()
            self.containers['acceptance']['HostConfig']['NetworkMode']='internal-net'
            with self.assertRaisesRegex(RuntimeBlocked,'not owned by the recorded attempt'): self.invoke()
            calls.assert_not_called()

    def test_opening_requires_exact_pending_and_static_address(self):
        self.prepare_opening()
        self.mock['observe'].side_effect=None
        self.mock['observe'].return_value=dict(self.obs,maintenance=False)
        pending=json.loads((self.root/'deployment-pending.json').read_text())
        self.write('deployment-pending.json',dict(pending,releaseTag='other'))
        with self.assertRaisesRegex(RuntimeBlocked,'pending identity differs'): self.invoke()
        self.write('deployment-pending.json',pending)
        self.containers['backend']['NetworkSettings']['Networks']['internal-net']['IPAddress']='172.29.235.26'
        with self.assertRaisesRegex(RuntimeBlocked,'static address differs'): self.invoke()

    def test_completed_receipt_requires_fresh_health_and_never_reopens(self):
        self.invoke()
        receipt=self.receipt()
        receipt['pid']=999998
        self.write('resume-'+self.retry+'/receipt.private.json',receipt)
        self.payload['retryJobId']='JOB-3333333333'
        self.mock['observe'].return_value=self.result
        result=self.invoke()
        self.assertEqual(result['resumeReceipt']['completedByJobId'],self.retry)
        self.assertEqual(self.mock['reopen'].call_count,1)
        self.mock['health'].assert_called_with(self.profile,self.tag,False)
        self.mock['health'].side_effect=RuntimeBlocked('fresh health failed')
        with self.assertRaisesRegex(RuntimeBlocked,'fresh health failed'): self.invoke()


if __name__=='__main__':
    unittest.main()
