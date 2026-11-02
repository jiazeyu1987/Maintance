"""Release lifecycle collection: remote payloads only, retaining all metadata."""
import copy
import time
from executor import require, stamp

ENVS = ('test', 'prod', 'backup')
DIAGNOSTICS = ('check-prerequisites', 'scan-artifacts', 'clean-artifacts')


def protected_tags(state):
    held = set()
    def hold(value):
        if value: held.add(value)
    for group in ('environments', 'frontendPatchEnvironments'):
        for current in state.get(group, {}).values():
            hold(current.get('releaseTag')); hold(current.get('frontendPatchTag'))
    for p in state.get('packages', []) + state.get('frontendPatches', []):
        if (p.get('stage') not in ('built', 'completed') and not p.get('artifactsPruned') and not p.get('abandoned')):
            hold(p['releaseTag'])
        if p.get('activeRehearsal'): hold(p['releaseTag'])
    for job in state.get('jobs', []):
        if job['action'] in DIAGNOSTICS: continue
        if (job.get('status') in ('running', 'failed', 'interrupted')
                and not job.get('resolution') and not job.get('reconciledBy')):
            hold(job.get('releaseTag'))
            for key in ('originState', 'frontendOrigin'):
                hold(job.get(key, {}).get('releaseTag')); hold(job.get(key, {}).get('frontendPatchTag'))
        plan = job.get('rollbackPlan', {})
        if plan.get('expiresAt', 0) > time.time():
            hold(plan.get('currentReleaseTag')); hold(plan.get('targetReleaseTag'))
    return held


def eligible(executor, job):
    if job.get('status') != 'succeeded': return False
    if job['action'] == 'accept-backup': group = 'packages'
    elif job['action'] == 'frontend-patch-accept' and job.get('target') == 'backup': group = 'frontendPatches'
    else: return False
    return any(p['releaseTag'] == job.get('releaseTag') and p.get('stage') == 'completed'
               for p in executor.state.get(group, []))


def entries(executor, state, env, held):
    result = []
    for p in state.get('packages', []):
        if p['releaseTag'] in held: continue
        _, manifest = executor.manifest(p['releaseTag'])
        owners = [j for j in state['jobs'] if j.get('releaseTag') == p['releaseTag']
                  and (j.get('target') or j.get('payload', {}).get('target')) == env
                  and not j['action'].startswith('frontend-patch-')]
        entry = dict(manifest=manifest, manifestSha256=p['manifestSha256'],
                     packageSha256=p['packageSha256'], ownerJobIds=[j['id'] for j in owners])
        result.append(entry)
        for owner in owners:
            root = owner.get('runtimeStagingRoots', {}).get(env)
            if root:
                from pathlib import PurePosixPath
                path = PurePosixPath(root)
                base = PurePosixPath(executor.c['targets'][env]['stagingRoot'])/'attempts'
                require(path.parent == base, '重试暂存目录不属于登记发布根')
                candidate = dict(entry, attempt=path.name)
                if candidate not in result: result.append(candidate)
    for p in state.get('frontendPatches', []):
        if p['releaseTag'] in held: continue
        _, manifest = executor.frontend_package(p['releaseTag'])
        for owner in state['jobs']:
            if (owner['action'] == 'frontend-patch-deploy' and owner.get('releaseTag') == p['releaseTag']
                    and (owner.get('target') or owner.get('payload', {}).get('target')) == env):
                result.append(dict(kind='frontend-patch', manifest=manifest,
                    manifestSha256=p['manifestSha256'], packageSha256=p['packageSha256'], deploymentJobId=owner['id']))
    return result


def safe_error(executor, error):
    message = str(error); password = getattr(executor, 'password', None)
    return message.replace(password, '[REDACTED]') if isinstance(password, str) and password else message


def perform(executor, job):
    from intruoyi_executor import validate_origin
    state = copy.deepcopy(executor.state)
    require(not any(j['id'] != job['id'] and j.get('status') == 'running' for j in state['jobs']),
            '存在其他运行任务，自动清理停止')
    patch_release = job['action'].startswith('frontend-patch-')
    held = protected_tags(state); observations = {}
    for env in ENVS:
        recorded = state['environments'].get(env, {})
        require(not any(recorded.get(k) for k in ('recoveryPending', 'maintenanceUnknown', 'maintenance')),
                env+': 恢复或维护状态未结束，停止自动清理')
        current = validate_origin(executor.runtime.observe(env))
        require(current.get('maintenance') is False, env+': 入口尚未开放')
        if patch_release:
            _, manifest = executor.frontend_package(job['releaseTag'])
            actual = executor.frontend_call(job, env, 'verify', manifest=manifest)
            require(current['releaseTag'] == actual['releaseTag'] and
                    current['images'] == {r:actual['components'][r]['imageId'] for r in ('backend','frontend')},
                    env+': 完整状态与补丁身份不同')
            current['frontendPatchTag'] = actual['frontendPatchTag']
        else:
            _, manifest = executor.manifest(job['releaseTag'])
            require(current['releaseTag'] == job['releaseTag'] and
                    current['images'] == {r:manifest['images'][r]['id'] for r in ('backend','frontend')},
                    env+': 当前版本已偏离验收包')
        held.add(current['releaseTag'])
        if current.get('frontendPatchTag'): held.add(current['frontendPatchTag'])
        observations[env] = current
    report = dict(status='running', environments={}); job['postReleaseCleanup'] = report; executor.save()
    for env in ENVS:
        try:
            current = observations[env]
            result = executor.runtime.call(env, 'artifact-auto-clean',
                entries=entries(executor, state, env, held), protectedTags=sorted(held),
                expectedImages=current['images'], currentReleaseTag=current['releaseTag'],
                currentPatchTag=current.get('frontendPatchTag'))
            require(isinstance(result, dict) and result.get('status') in ('succeeded','failed'),
                    env+': 自动清理回执无效，需要核对原任务')
            report['environments'][env] = result
        except Exception as error:
            report['environments'][env] = dict(status='failed', error=safe_error(executor, error))
        executor.save()
    report['status'] = 'succeeded' if all(r['status'] == 'succeeded' for r in report['environments'].values()) else 'failed'
    return report


def run(executor, job):
    if not eligible(executor, job) or job.get('postReleaseCleanup', {}).get('status') == 'succeeded': return
    job['postReleaseCleanup'] = dict(status='running', startedAt=stamp()); executor.save()
    try:
        job['postReleaseCleanup'] = perform(executor, job)
    except Exception as error:
        job['postReleaseCleanup'].update(status='failed', error=safe_error(executor, error))
    job['postReleaseCleanup']['finishedAt'] = stamp()
    job.setdefault('result', {})['postReleaseCleanup'] = job['postReleaseCleanup']
    for env, result in job['postReleaseCleanup'].get('environments', {}).items():
        executor.log(job, env+': 旧载荷清理 '+result['status']+'，删除 '+str(len(result.get('removed', [])))+
                     ' 个文件；释放 '+str(result.get('bytes', 0))+' 字节'+
                     ('；'+result['error'] if result.get('error') else ''))
    if job['postReleaseCleanup'].get('error'):
        executor.log(job, '旧载荷清理未完成：'+job['postReleaseCleanup']['error'])
    executor.log(job, '发布验收后的旧载荷自动清理：'+job['postReleaseCleanup']['status']+
                 '；发布验收结果独立保留，详情见 postReleaseCleanup。')
    executor.save()
