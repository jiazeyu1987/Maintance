"""Rollback jobs share the existing executor queue, durable state and actor audit."""
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import threading
import time
from executor import require, stamp


def compatibility(current, origin):
    blockers = []
    if current['schemaSha256'] != origin['schemaSha256']:
        blockers.append('数据库结构与上一稳定版本不同；禁止仅回退程序镜像')
    if current['ledgerSha256'] != origin['ledgerSha256']:
        blockers.append('数据库迁移记录已改变；需要独立兼容验证或明确的数据恢复方案')
    return blockers


class RollbackMixin:
    def snapshot(self):
        value = super().snapshot()
        value['application']['capabilities']['productionRollback'] = True
        return value

    def rollback_remote(self, action, **args):
        profile = self.runtime.profile('prod')
        root = Path(__file__).parent
        pieces = ['import types,sys,json\n']
        for name in ('intruoyi_remote', 'intruoyi_runtime', 'intruoyi_rehearsal_agent', 'intruoyi_runtime_agent', 'rollback_agent'):
            text = (root / (name + '.py')).read_text('utf-8-sig')
            pieces.append("m=types.ModuleType(%r);m.__file__=%r;sys.modules[%r]=m;exec(compile(%r,%r,'exec'),m.__dict__)\n" %
                          (name, str(root / (name + '.py')), name, text, name + '.py'))
        pieces.append('a=sys.modules["intruoyi_runtime_agent"];r=sys.modules["rollback_agent"]\n')
        pieces.append('p=' + repr(profile) + '\nv=' + repr(args) + '\n')
        call = {'capture': "r.capture(a,p,v['tag'],v['origin'])",
                'inspect': "r.inspect_snapshot(a,p,v['tag'],v['origin'])",
                'execute': "r.execute(a,p,v['plan'],v['jobId'])"}[action]
        pieces.append('try:\n result=' + call + '\n print(json.dumps({"ok":True,"result":result}))\n'
                      'except Exception as e:\n print(json.dumps({"ok":False,"error":str(e) if isinstance(e,a.RuntimeBlocked) else type(e).__name__}))\n')
        try:
            result = subprocess.run(['ssh', *self.runtime.ssh_options(), 'root@' + profile['host'],
                                     shlex.quote(profile['python']) + ' -'], input=''.join(pieces).encode(),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200 if action == 'execute' else 120)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Rollback remote timeout; execution outcome unknown, inspect original job') from None
        require(result.returncode == 0, 'Rollback remote connection failed; inspect original job before any retry')
        value = json.loads(result.stdout)
        require(value.get('ok') is True, value.get('error', 'Invalid rollback response'))
        return value['result']

    def deploy(self, env, package, manifest, job):
        if env == 'prod':
            origin = self.runtime.observe(env)
            require(origin['backendHealth'].get('status') == 'UP' and origin['frontendHttpStatus'] == 200,
                    'Healthy production origin required for pre-release rollback snapshot')
            self.step(job, 'capture-rollback-config')
            job['rollbackSnapshot'] = self.rollback_remote('capture', tag=package['releaseTag'], origin=origin)
            self.save()
        return super().deploy(env, package, manifest, job)

    def submit(self, action, payload, actor):
        if action not in ('rollback-preview', 'rollback-prod'):
            return super().submit(action, payload, actor)
        with self.lock:
            self.ensure_persistence()
            require(not getattr(self, 'draining', False), 'Executor is draining')
            require(payload.get('applicationId') == self.c['applicationId'], 'Application identity mismatch')
            request_id = payload.get('requestId', '')
            require(isinstance(request_id, str) and re.fullmatch('[a-zA-Z0-9-]{8,80}', request_id), 'requestId required')
            for original in self.state['jobs']:
                if original['requestId'] == request_id:
                    require(original['action'] == action and original['payload'] == payload, 'Request identity mismatch')
                    return original
            require(not any(j['status'] == 'running' or (j['status'] == 'interrupted' and not j.get('resolution'))
                            for j in self.state['jobs']), 'Running/interrupted release job blocks rollback')
            if action == 'rollback-prod':
                require(not any(j.get('effectsStarted') and j['status'] in ('failed', 'interrupted') and not j.get('resolution')
                                and j.get('target') == 'prod' for j in self.state['jobs']),
                        'Unresolved production effects require investigation before rollback')
                previews = [j for j in self.state['jobs'] if j['id'] == payload.get('previewJobId') and j['action'] == 'rollback-preview']
                require(len(previews) == 1 and previews[0]['status'] == 'succeeded', 'Completed rollback preview required')
                plan = previews[0]['rollbackPlan']
                require(plan['ready'] and time.time() < plan['expiresAt'], 'Rollback preview blocked or expired')
                require(payload.get('confirm') == 'PROD ' + plan['targetReleaseTag'], 'Explicit production rollback confirmation required')
                require(not any(j.get('payload', {}).get('previewJobId') == previews[0]['id'] for j in self.state['jobs']), 'Rollback preview already consumed')
            job = dict(id='JOB-' + secrets.token_hex(5), requestId=request_id, action=action, payload=payload,
                       actor=actor, target='prod', releaseTag=None, status='running', createdAt=stamp(), logs=[])
            self.state['jobs'].insert(0, job)
            self.save()
            self.worker = threading.Thread(target=self.rollback_job, args=(job,), daemon=True)
            self.worker.start()
            return job

    def rollback_plan(self):
        current = self.runtime.observe('prod')
        # Container image identities, not a working frontend, identify the release.
        # An unavailable frontend must not prevent diagnosis of a rollback target.
        identities = []
        deployed_tags = {j['releaseTag'] for j in self.state['jobs'] if j['action'] == 'promote-prod' and j.get('originState')}
        for tag in sorted(deployed_tags):
            _, manifest = self.manifest(tag)
            if {role: manifest['images'][role]['id'] for role in ('frontend', 'backend')} == current['images']:
                identities.append(tag)
        require(len(identities) == 1, 'Running image pair does not identify exactly one immutable release')
        current_tag = identities[0]
        matches = [j for j in self.state['jobs'] if j['action'] == 'promote-prod' and j.get('target') == 'prod'
                   and j.get('releaseTag') == current_tag and j.get('originState')]
        require(matches, 'Current version has no recorded production deployment origin')
        origin = matches[0]['originState']
        candidate, _ = self.manifest(origin['releaseTag'])
        require(self.technical_passed(candidate, 'prod'), 'Previous version has no successful production technical acceptance')
        proof = self.rollback_remote('inspect', tag=current_tag, origin=origin)
        blockers = compatibility(current, origin) + proof['blockers']
        return dict(ready=not blockers, blockers=blockers, currentReleaseTag=current_tag,
                    targetReleaseTag=origin['releaseTag'], currentFingerprint=current['fingerprint'],
                    snapshotSha256=proof['snapshotSha256'], origin=origin, expiresAt=time.time() + 300,
                    dataPolicy='保留当前业务数据；不执行SQL回退或数据覆盖',
                    impact='停止正式前后端，切回已固定的原镜像及配置，验证健康和真实登录；失败保留现场')

    def rollback_job(self, job):
        try:
            if job['action'] == 'rollback-preview':
                self.step(job, 'rollback-preflight')
                job['rollbackPlan'] = self.rollback_plan()
                job['releaseTag'] = job['rollbackPlan']['targetReleaseTag']
            else:
                preview = next(j for j in self.state['jobs'] if j['id'] == job['payload']['previewJobId'])
                plan = preview['rollbackPlan']
                self.step(job, 'rollback-revalidate')
                fresh = self.rollback_plan()
                require(fresh['ready'] and fresh['currentFingerprint'] == plan['currentFingerprint'] and
                        fresh['snapshotSha256'] == plan['snapshotSha256'] and time.time() < plan['expiresAt'],
                        'Production or rollback evidence changed after preview')
                candidate, manifest = self.package(plan['targetReleaseTag'])
                require({r:manifest['images'][r]['id'] for r in ('frontend','backend')} == plan['origin']['images'], 'Rollback package images differ')
                job['releaseTag'] = plan['targetReleaseTag']
                self.step(job, 'rollback-switch', effects=True)
                self.state['environments']['prod']['maintenanceUnknown'] = True
                self.save()
                result = self.rollback_remote('execute', plan=plan, jobId=job['id'])
                self.step(job, 'rollback-login')
                from intruoyi_login import verify_login
                binding = dict(jobId=job['id'], env='prod', releaseTag=plan['targetReleaseTag'], packageSha256=candidate['packageSha256'])
                receipt = verify_login(self.c, self.runtime.profile('prod')['entryUrl'], self.root/'technical-evidence'/job['id']/'prod', binding)
                require(receipt.get('status') == 'passed' and receipt.get('binding') == binding and receipt.get('authenticated') is True,
                        'Rollback real browser login verification failed')
                job['rollbackVerification'] = dict(observation=result, login=receipt, dataPolicy=plan['dataPolicy'])
                self.state['environments']['prod'] = dict(result, observedAt=stamp(), baselineStatus='registered', maintenanceUnknown=False)
            job.update(status='succeeded', finishedAt=stamp())
            self.save()
        except Exception as error:
            job.update(status='failed', finishedAt=stamp(), error=str(error))
            self.save()
