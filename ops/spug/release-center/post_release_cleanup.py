"""Release lifecycle collection: remote payloads only, retaining all metadata."""
import copy
import time
from executor import require, stamp

ENVS = ('test', 'prod', 'backup')
DIAGNOSTICS = ('check-prerequisites', 'scan-artifacts', 'clean-artifacts','retry-release-cleanup')


def protected_tags(state):
    held = set()
    def hold(value):
        if value: held.add(value)
    for group in ('environments', 'frontendPatchEnvironments','backendPatchEnvironments'):
        for current in state.get(group, {}).values():
            hold(current.get('releaseTag')); hold(current.get('frontendPatchTag'))
            hold(current.get('backendPatchTag'))
    for p in state.get('packages', []) + state.get('frontendPatches', []) + state.get('backendPatches',[]):
        if (p.get('stage') not in ('built', 'completed') and not p.get('artifactsPruned') and not p.get('abandoned')):
            hold(p['releaseTag'])
        if p.get('activeRehearsal'): hold(p['releaseTag'])
    for job in state.get('jobs', []):
        if job['action'] in DIAGNOSTICS: continue
        if (job.get('status') in ('running', 'failed', 'interrupted')
                and not job.get('resolution') and not job.get('reconciledBy')):
            hold(job.get('releaseTag'))
            for key in ('originState', 'frontendOrigin','backendOrigin'):
                hold(job.get(key, {}).get('releaseTag')); hold(job.get(key, {}).get('frontendPatchTag'))
                hold(job.get(key, {}).get('backendPatchTag'))
        plan = job.get('rollbackPlan', {})
        if plan.get('expiresAt', 0) > time.time():
            hold(plan.get('currentReleaseTag')); hold(plan.get('targetReleaseTag'))
    return held


def eligible(executor, job):
    if job.get('status') != 'succeeded': return False
    action=job.get('cleanupAction',job['action'])
    if action == 'accept-backup': group = 'packages'
    elif action == 'frontend-patch-accept' and job.get('target') == 'backup': group = 'frontendPatches'
    elif action == 'backend-patch-accept' and job.get('target') == 'backup': group = 'backendPatches'
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
                  and not j['action'].startswith(('frontend-patch-','backend-patch-'))]
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
    for p in state.get('backendPatches',[]):
        if p['releaseTag'] in held:continue
        _,manifest=executor.backend_package(p['releaseTag'])
        for owner in state['jobs']:
            if owner['action']=='backend-patch-deploy' and owner.get('releaseTag')==p['releaseTag'] and owner.get('target')==env:
                result.append(dict(kind='backend-patch',manifest=manifest,manifestSha256=p['manifestSha256'],
                    packageSha256=p['packageSha256'],deploymentJobId=owner['id'],acceptedDeployment=bool(p['accepted'].get(env))))
    return result


def resource_entries(executor,state,env):
    """Include current evidence to protect the latest real recovery point."""
    rows=entries(executor,state,env,set())
    for entry in rows:
        tag=entry['manifest']['releaseTag']
        if entry.get('kind') in ('frontend-patch','backend-patch'):continue
        entry['ownerJobIds']=[identity for identity in entry['ownerJobIds'] if
            any(j['id']==identity and bool(j.get('runtimeStagingRoots',{}).get(env))==bool(entry.get('attempt'))
                and (not entry.get('attempt') or j['runtimeStagingRoots'][env].endswith('/'+entry['attempt']))
                for j in state['jobs'])]
        package=next(p for p in state.get('packages',[]) if p['releaseTag']==tag)
        outcome=package.get('outcomes',{}).get(env,{})
        entry['acceptedDeployment']=outcome.get('acceptance',{}).get('status')=='passed' or (
            env=='test' and package.get('stage') in ('tested','prod-deployed','prod-accepted','backup-deployed','completed'))
        resolved=[]
        for original in state.get('jobs',[]):
            resolution=original.get('resolution',{})
            if original['id'] not in entry['ownerJobIds'] or resolution.get('decision')!='restored':continue
            accepted=next((j for j in state['jobs'] if j['id']==resolution.get('jobId') and
                j.get('status')=='succeeded' and j['action']=='accept-recovery' and j.get('target')==env
                and j.get('originalDeploymentJobId')==original['id']),None)
            receipt=(accepted or {}).get('result',{}).get('receipt',{})
            if (accepted and receipt.get('jobId') and receipt.get('openingJobId')
                    and receipt.get('confirmedByJobId',receipt['openingJobId'])==accepted['id']):
                resolved.append(dict(originalJobId=original['id'],recoveryJobId=receipt['jobId'],
                    acceptanceJobId=accepted['id'],openingJobId=receipt['openingJobId']))
        entry['resolvedRecoveries']=resolved
    return rows


def safe_error(executor, error):
    message = str(error); password = getattr(executor, 'password', None)
    return message.replace(password, '[REDACTED]') if isinstance(password, str) and password else message


def perform(executor, job):
    from intruoyi_executor import validate_origin
    state = copy.deepcopy(executor.state)
    require(not any(j['id'] != job['id'] and j.get('status') == 'running' for j in state['jobs']),
            '存在其他运行任务，自动清理停止')
    cleanup_action=job.get('cleanupAction',job['action'])
    patch_release = cleanup_action.startswith('frontend-patch-')
    backend_release = cleanup_action.startswith('backend-patch-')
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
        elif backend_release:
            _,manifest=executor.backend_package(job['releaseTag'])
            actual=executor.backend_call(job,env,'verify',manifest=manifest)
            require(current['backendJarSha256']==actual['backendJarSha256'] and current['backendPatchTag']==job['releaseTag'],
                    env+': 完整状态与后端补丁身份不同')
        else:
            _, manifest = executor.manifest(job['releaseTag'])
            require(current['releaseTag'] == job['releaseTag'] and
                    current['images'] == {r:manifest['images'][r]['id'] for r in ('backend','frontend')},
                    env+': 当前版本已偏离验收包')
        held.add(current['releaseTag'])
        if current.get('frontendPatchTag'): held.add(current['frontendPatchTag'])
        if current.get('backendPatchTag'):held.add(current['backendPatchTag'])
        observations[env] = current
    report = dict(status='running', environments={}); job['postReleaseCleanup'] = report; executor.save()
    for env in ENVS:
        try:
            current = observations[env]
            result = executor.runtime.call(env, 'artifact-auto-clean',
                entries=entries(executor, state, env, held), protectedTags=sorted(held),
                resourceEntries=resource_entries(executor,state,env),
                expectedImages=current['images'], currentReleaseTag=current['releaseTag'],
                currentPatchTag=current.get('frontendPatchTag'),
                **(dict(currentBackendPatchTag=current['backendPatchTag'],currentBackendJarSha256=current['backendJarSha256'])
                   if current.get('backendPatchTag') else {}))
            # Actual backend identity is also checked remotely before deletion.
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
        executor.log(job, env+': 发布资源清理 '+result['status']+'，删除 '+str(len(result.get('removed', [])))+
                     ' 项；文件字节 '+str(result.get('bytes', 0))+'；保留 '+str(len(result.get('retained',[])))+' 项'+
                     ('；'+result['error'] if result.get('error') else ''))
    if job['postReleaseCleanup'].get('error'):
        executor.log(job, '旧载荷清理未完成：'+job['postReleaseCleanup']['error'])
    executor.log(job, '发布验收后的旧载荷自动清理：'+job['postReleaseCleanup']['status']+
                 '；发布验收结果独立保留，详情见 postReleaseCleanup。')
    executor.save()


def submit_retry(executor,payload,actor):
    import secrets
    import threading
    with executor.lock:
        require(not any(j.get('status')=='running' for j in executor.state['jobs'])
                and not (executor.worker and executor.worker.is_alive()),'其他任务正在执行')
        original=next((j for j in executor.state['jobs'] if j['id']==payload.get('jobId')),None)
        require(original and original['action'] in ('accept-backup','frontend-patch-accept','backend-patch-accept')
                and eligible(executor,original),'需要三服最终验收成功的原任务')
        job=dict(id='JOB-'+secrets.token_hex(5),requestId=payload['requestId'],action='retry-release-cleanup',
            cleanupAction=original['action'],cleanupOf=original['id'],payload=payload,target='backup',
            releaseTag=original['releaseTag'],actor=actor,status='running',createdAt=stamp(),logs=[])
        executor.state['jobs'].insert(0,job);executor.save()
        executor.worker=threading.Thread(target=executor.execute,args=(job,),daemon=True)
        executor.worker.start()
        return job
