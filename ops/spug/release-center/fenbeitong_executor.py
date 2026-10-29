"""Independent Spug application executor for the standalone Fenbeitong assistant."""
import base64
import json
from pathlib import Path
import re
import secrets
import shlex
import threading

from executor import Executor, digest, main, require, stamp
from state_store import StateStore, process_lock
from fenbeitong_build import build, source_files, source_identity

DEPLOY = {'publish-test': 'test', 'promote-prod': 'prod', 'promote-backup': 'backup'}
ACCEPT = {'mark-tested': 'test', 'accept-prod': 'prod', 'accept-backup': 'backup'}
ACTIONS = set(DEPLOY) | set(ACCEPT) | {'build-release', 'register-targets', 'check-prerequisites',
    'prepare-rehearsal', 'accept-rehearsal', 'reject-acceptance', 'resolve-task'}


class FenbeitongExecutor(Executor):
    def __init__(self, config):
        require(config['applicationId'] == 'fenbeitong', 'Application identity must be fenbeitong')
        require(set(config['targets']) == {'test', 'prod', 'backup'}, 'All three targets must be configured')
        for env, target in config['targets'].items():
            require(re.fullmatch(r'[0-9.]+', target['host']) and target['python'] in ('python', 'python3'), 'Invalid target transport')
            require(target['container'] == 'fenbeitong-assistant' and target['port'] == 18734, 'Target contract differs')
            require(re.fullmatch(r'[A-Za-z0-9_.-]+', target['integrationNetwork'])
                    and re.fullmatch(r'[A-Za-z0-9_.-]+', target['intRuoyiBackend']), 'Explicit IntRuoyi container network required')
            require(target['ticketValidateUrl'] == 'http://' + target['intRuoyiBackend'] + ':48081/admin-api/system/auth/fenbeitong-assistant-ticket/validate',
                    'Ticket validation must use this target IntRuoyi')
        self.c, self.root = config, Path(config['stateDir']).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock, self.worker, self.draining = threading.RLock(), None, False
        self.process_lock = process_lock(self.root)
        self.store = StateStore(self.root)
        self.state = self.store.load()
        self.password = secrets.token_hex(32)
        for job in self.state['jobs']:
            if job['status'] == 'running':
                job.update(status='interrupted', error='执行器重启；请核对原任务，禁止盲目重复发布。')
        self.save()

    def snapshot(self):
        with self.lock:
            self.ensure_persistence()
            app = dict(id='fenbeitong', name='分贝通费用报销助手', repo=self.c['repo'], runtimeKind='node-assistant',
                       targets={k: {n: v[n] for n in ('label', 'host', 'port', 'entryUrl')} for k, v in self.c['targets'].items()},
                       packageStoragePath=str(self.root / 'packages'), nodeImage=self.c['nodeImage'],
                       executorSourceSha256=self.c.get('executorSourceSha256'))
            return json.loads(json.dumps(dict(self.state, application=app)))

    def commits(self):
        files = source_files(self.c['repo'])
        return [dict(commit=source_identity(files), sourceKind='local-snapshot', fileCount=len(files),
                     message='当前本地源码快照（不是 Git 提交）')]

    def ssh(self, env):
        c = self.c
        return ['ssh', '-i', c['sshIdentityFile'], '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + c['sshKnownHostsFile'],
                '-o', 'ConnectTimeout=10', 'root@' + c['targets'][env]['host']]

    def remote(self, env, action, job, package=None, **extra):
        target = self.c['targets'][env]
        payload = dict(target, action=action, jobId=job['id'], requiredBytes=512 * 1024 * 1024, **extra)
        if package:
            payload.update({k: package[k] for k in ('releaseTag', 'sourceSha256', 'packageSha256', 'manifestSha256', 'imageId')})
            payload['requiredBytes'] += (Path(package['directory']) / 'release.tar').stat().st_size * 2
        agent = Path(__file__).with_name('fenbeitong_agent.py').read_bytes()
        encoded = base64.b64encode(agent).decode('ascii')
        command = target['python'] + ' -c ' + shlex.quote('import base64;exec(compile(base64.b64decode("' + encoded + '"),"fenbeitong_agent","exec"))')
        raw = self.run(self.ssh(env) + [command], data=json.dumps(payload).encode(), timeout=1200)
        return json.loads(raw)

    def transfer(self, env, p, job):
        directory = self.c['targets'][env]['root'] + '/uploads/' + job['id']
        require(self.c['targets'][env]['root'] in ('/var/lib/docker/fenbeitong-release', '/mnt/intruoyi-data/fenbeitong-release'), 'Invalid staging root')
        self.run(self.ssh(env) + ['mkdir -p ' + shlex.quote(directory)], timeout=30)
        # SSH stream avoids version-specific scp/SFTP availability on the three servers.
        path = Path(p['directory']) / 'release.tar'
        import subprocess
        with path.open('rb') as stream:
            process = subprocess.run(self.ssh(env) + ['cat > ' + shlex.quote(directory + '/release.tar')],
                                     stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200)
        require(process.returncode == 0, '发布包传输失败，目标尚未部署；请查看原任务。')

    def gate(self, action, payload):
        if action in ('build-release', 'register-targets', 'check-prerequisites', 'resolve-task'):
            return
        p, unused = self.manifest(payload.get('releaseTag'))
        require(not p.get('rejected'), '本包验收失败；请修复并构建新包')
        for failed in self.state['jobs']:
            require(not (failed['status'] in ('failed', 'interrupted') and failed.get('remoteStarted') and not failed.get('resolution')),
                    '存在未处理的远端失败或中断，请先核对原任务')
        if action in DEPLOY:
            env = DEPLOY[action]
            current = self.state['environments'].get(env, {})
            require(not current.get('releaseTag') or current['releaseTag'] < p['releaseTag'], '目标已安装相同或更新版本')
            if env == 'prod':
                require(p.get('accepted', {}).get('test'), '请先验收测试服当前版本')
                require(p.get('rehearsal', {}).get('accepted'), '请先完成正式起点演练及确认')
            if env == 'backup':
                require(p.get('accepted', {}).get('prod') and self.state['environments'].get('prod', {}).get('packageSha256') == p['packageSha256'],
                        '审查服只能发布正式服当前已验收的同一个包')
        if action in ACCEPT:
            require(self.state['environments'].get(ACCEPT[action], {}).get('packageSha256') == p['packageSha256'], '所选包不是目标实际部署包')
        if action == 'prepare-rehearsal':
            require(p.get('accepted', {}).get('test'), '必须先通过测试服功能验收')
        if action == 'accept-rehearsal':
            require(p.get('rehearsal', {}).get('status') == 'succeeded', '尚无成功的正式起点演练')

    def submit(self, action, payload, actor):
        with self.lock:
            self.ensure_persistence()
            require(action in ACTIONS and payload.get('applicationId') == 'fenbeitong', '应用或操作不匹配')
            require(re.fullmatch(r'[a-zA-Z0-9-]{8,80}', str(payload.get('requestId', ''))), 'requestId required')
            existing = next((j for j in self.state['jobs'] if j['requestId'] == payload['requestId']), None)
            if existing:
                require(existing['action'] == action and existing['payload'] == payload, 'requestId 已绑定另一个操作')
                return existing
            require(not any(j['status'] == 'running' for j in self.state['jobs']), '请等待当前任务完成')
            require(action == 'resolve-task' or not any(j['status'] == 'interrupted' and not j.get('resolution') for j in self.state['jobs']), '请先核对中断任务')
            if action in set(ACCEPT) | {'accept-rehearsal', 'reject-acceptance', 'resolve-task'}:
                require(len(str(payload.get('note', '')).strip()) >= 5, '请填写至少5字的实际验收或核对依据')
            self.gate(action, payload)
            job = dict(id='JOB-' + secrets.token_hex(5), requestId=payload['requestId'], action=action,
                       payload=payload, releaseTag=payload.get('releaseTag'), actor=actor, status='running', createdAt=stamp(), logs=[])
            self.state['jobs'].insert(0, job)
            self.save()
            self.worker = threading.Thread(target=self.execute, args=(job,), daemon=True)
            self.worker.start()
            return job

    def execute(self, job):
        try:
            action = job['action']
            self.step(job, action)
            self.gate(action, job['payload'])
            if action == 'build-release':
                build(self, job)
            elif action in ('register-targets', 'check-prerequisites'):
                results = {}
                for env in ('test', 'prod', 'backup'):
                    self.step(job, action + '-' + env)
                    result = self.remote(env, 'precheck' if action == 'check-prerequisites' else 'observe', job)
                    self.state['environments'][env] = dict(result['environment'], observedAt=stamp())
                    results[env] = result
                    job['result'] = results
                    self.save()
            elif action == 'resolve-task':
                self.resolve(job)
            else:
                p, unused = self.package(job['releaseTag'])
                if action in DEPLOY:
                    env = DEPLOY[action]
                    if env == 'backup':
                        actual = self.remote('prod', 'observe', job)['environment']
                        require(actual.get('packageSha256') == p['packageSha256'] and actual['status'] == 'running', '正式实际版本已变化')
                    result = self.deploy(env, p, job)
                    p['stage'] = env + '-deployed'
                    p.setdefault('accepted', {}).pop(env, None)
                elif action == 'prepare-rehearsal':
                    result = self.deploy('prod', p, job, rehearsal=True)
                    p['rehearsal'] = result
                    p['stage'] = 'rehearsed'
                elif action == 'accept-rehearsal':
                    p['rehearsal'].update(accepted=True, note=job['payload']['note'], actor=job['actor'])
                    p['stage'] = 'rehearsal-passed'
                elif action == 'reject-acceptance':
                    p.update(rejected=True, rejection=job['payload']['note'])
                elif action in ACCEPT:
                    env = ACCEPT[action]
                    job['target'] = env
                    result = self.remote(env, 'verify', job, p)
                    self.state['environments'][env] = dict(result['environment'], observedAt=stamp())
                    p.setdefault('accepted', {})[env] = dict(actor=job['actor'], note=job['payload']['note'], time=stamp(), jobId=job['id'])
                    p['stage'] = {'test': 'tested', 'prod': 'prod-accepted', 'backup': 'completed'}[env]
            job.update(status='succeeded', finishedAt=stamp())
            self.log(job, '操作完成；部署技术检查和人工业务验收分别记录。')
        except Exception as error:
            job.update(status='failed', error=str(error), finishedAt=stamp())
            self.log(job, '操作失败：' + str(error))
        finally:
            self.save()

    def deploy(self, env, p, job, rehearsal=False):
        job['target'] = env
        self.step(job, 'precheck-' + env)
        result = self.remote(env, 'precheck', job, p)
        origin = result['environment']
        if not rehearsal:
            require(not origin['releaseTag'] or origin['releaseTag'] < p['releaseTag'], '实际目标已安装同版或更新版本')
        self.step(job, 'transfer-original-package')
        self.transfer(env, p, job)
        self.step(job, 'rehearse-production-origin' if rehearsal else 'deploy-' + env, effects=True)
        job['remoteStarted'] = True
        self.save()
        extra = {}
        if env == 'prod' and not rehearsal:
            extra['expectedOrigin'] = p['rehearsal']['origin']
        result = self.remote(env, 'rehearse' if rehearsal else 'deploy', job, p, **extra)
        job['result'] = result
        if not rehearsal:
            self.state['environments'][env] = dict(result['environment'], observedAt=stamp())
        self.save()
        return result

    def resolve(self, job):
        original = next((j for j in self.state['jobs'] if j['id'] == job['payload'].get('jobId')), None)
        require(original and original['status'] in ('failed', 'interrupted') and not original.get('resolution'), '原失败任务不存在或已处理')
        if original.get('remoteStarted'):
            receipt = self.remote(original['target'], 'receipt', job, originalJobId=original['id'])
            job['result'] = receipt
            require(receipt['status'] != 'running', '远端任务仍运行，请等待')
            if receipt['status'] == 'succeeded':
                p, unused = self.package(original['releaseTag'])
                require(receipt['packageSha256'] == p['packageSha256'], '远端回执包身份不符')
                if original['action'] in DEPLOY:
                    actual = self.remote(original['target'], 'observe', job)['environment']
                    require(actual == receipt['environment'] and actual['status'] == 'running', '远端实际状态已改变')
                    self.state['environments'][original['target']] = dict(actual, observedAt=stamp())
                    p['stage'] = original['target'] + '-deployed'
                    p.setdefault('accepted', {}).pop(original['target'], None)
                elif original['action'] == 'prepare-rehearsal':
                    p['rehearsal'] = receipt
                    p['stage'] = 'rehearsed'
                else:
                    raise ValueError('此原任务类型不能自动登记回执')
                original['resolution'] = dict(jobId=job['id'], note=job['payload']['note'], time=stamp(), decision='verified-remote-completion')
                return
            require(receipt['status'] == 'failed' and not receipt.get('effectsStarted'),
                    '远端已产生影响或已完成，需技术人员核对并处理；此按钮不会重放或伪造发布结果')
        original['resolution'] = dict(jobId=job['id'], note=job['payload']['note'], time=stamp(), decision='close-pre-effect')


if __name__ == '__main__':
    main(FenbeitongExecutor)
