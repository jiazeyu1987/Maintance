"""Explicit inspection/reconciliation. Never replay a migration after disconnect."""
import json
import secrets
import threading

from executor import require, stamp

ACTIONS = frozenset(('inspect-interruption', 'reconcile-interruption'))
DEPLOYMENTS = {'publish-test': 'test', 'upgrade-rehearsal': 'rehearsal',
               'promote-prod': 'prod', 'promote-backup': 'backup'}
READ_ONLY = frozenset(('observe', 'health', 'preflight', 'dependencies', 'acceptance-check', 'prerequisite-resources',
                       'recovery-inventory', 'inspect-release-recovery', 'rehearsal-status',
                       'rehearsal-verify-stopped', 'verify-deployment-stopped', 'verify-restoration',
                       'rehearsal-job-status', 'rehearsal-daemon-identity', 'rehearsal-runtime-images',
                       'rehearsal-check-images', 'rehearsal-media-inventory', 'rehearsal-media-column-proof',
                       'rehearsal-writer-inventory', 'rehearsal-redis-inventory', 'rehearsal-source-check',
                       'rehearsal-target-check', 'rehearsal-tail-source-proof', 'rehearsal-reset-check'))


def submit(executor, action, payload, actor):
    with executor.lock:
        existing = next((j for j in executor.state['jobs'] if j.get('requestId') == payload['requestId']), None)
        if existing:
            require(existing['action'] == action and existing['payload'] == payload, 'Request ID binding mismatch')
            return existing
        require(not any(j['status'] == 'running' for j in executor.state['jobs']), 'A task is still running')
        original = next((j for j in executor.state['jobs'] if j['id'] == payload.get('jobId')), None)
        require(original and original['status'] in ('failed', 'interrupted') and not original.get('resolution'),
                'Select an unresolved original task')
        require(original['action'] not in ACTIONS, 'Select the interrupted release task, not its inspection')
        require(payload.get('releaseTag') == original.get('releaseTag'), 'Original package binding differs')
        if action == 'reconcile-interruption':
            require(isinstance(payload.get('note'), str) and len(payload['note'].strip()) >= 5,
                    'Explicit continuation/closure note required')
        job = dict(id='JOB-' + secrets.token_hex(5), requestId=payload['requestId'], action=action,
                   payload=payload, releaseTag=original.get('releaseTag'), actor=actor, status='running',
                   createdAt=stamp(), logs=[], originalTaskId=original['id'])
        executor.state['jobs'].insert(0, job)
        executor.save()
        executor.worker = threading.Thread(target=executor.execute, args=(job,), daemon=True)
        executor.worker.start()
        return job


def local_workers(original):
    import psutil
    require(not original.get('localProcessTrackingError'), 'Local process tracking failed; process reconciliation required')
    result = []
    for item in original.get('localProcesses', []):
        try:
            process = psutil.Process(item['pid'])
            alive = process.create_time() == item['createdAt'] and process.is_running()
        except psutil.NoSuchProcess:
            alive = False
        result.append(dict(item, running=alive))
    return result


def inspect(executor, original):
    # A preparation can die before its isolation is registered. Reconstruct its
    # configured receipt location, not a deployed-candidate observation.
    if original['action'] == 'prepare-rehearsal' and original.get('sourceEnv'):
        from intruoyi_runtime import rehearsal_profile
        executor.runtime.targets['rehearsal'] = rehearsal_profile(executor.c, original['sourceEnv'])
    family = [original] + [j for j in executor.state['jobs'] if j.get('originalTaskId') == original['id']
                           and j['action'] == 'reconcile-interruption' and j['status'] in ('failed', 'interrupted')]
    local = [item for task in family for item in local_workers(task)]
    operations = []
    for task in family:
        for item in task.get('remoteOperations', []):
            receipt = executor.runtime.call(item['env'], 'inspect-operation',
                        originalOperationId=item['operationId'], originalJobId=task['id'])
            require(receipt.get('operationId') == item['operationId'] and receipt.get('jobId') == task['id'],
                    'Inspection receipt binding differs')
            operations.append(dict(item, receipt=receipt))
    evidence = dict(originalJobId=original['id'], observedAt=stamp(), localProcesses=local,
                    operations=operations, disposition='manual-review', detail='需根据原任务证据处理，未执行迁移或开放业务。')
    if any(item['running'] for item in local) or any(item['receipt'].get('worker') == 'running' for item in operations):
        evidence.update(disposition='still-running', detail='原任务进程仍在执行；等待后再次核对，不能重发。')
        return evidence
    uncertain = [item for item in operations if item['action'] not in READ_ONLY
                 and (item['receipt'].get('worker') != 'stopped' or item['receipt'].get('status') not in ('succeeded', 'failed'))]
    if uncertain:
        evidence.update(disposition='unknown', detail='部分远端操作没有可确认的终态；禁止自动续接或补发。')
        return evidence
    if original.get('effectsStarted') and not operations:
        evidence.update(disposition='legacy-evidence-required', detail='旧任务缺少统一操作回执，须使用原有迁移恢复或演练续接入口核对。')
        return evidence
    action = original['action']
    if action == 'reject-acceptance':
        evidence.update(disposition='acceptance-rejected', detail='这是明确的业务验收失败；保留失败记录，按恢复流程处理，不能核销为通过。')
        return evidence
    if action == 'build-release':
        require(original.get('localProcessTracking'), 'Historical build has no local process inventory; inspect its build process before closure')
        evidence.update(disposition='close-build', detail='构建进程已停止；核对已登记原包或关闭不完整构建，后续重新构建使用新版本号。')
        return evidence
    dedicated = {
        'prepare-rehearsal': '原准备操作回执已核对。按原任务的副本传输或启动续接入口处理；不能把未建成的隔离副本当成已部署环境。',
        'recover-release': '原恢复操作回执已核对。使用原部署的恢复入口，沿原恢复日志确认或续接，不重新采集恢复点。',
        'accept-recovery': '原恢复验收操作回执已核对。使用原部署的恢复验收入口确认开放结果，不再恢复数据。',
        'reset-rehearsal': '原隔离清除操作回执已核对。须核对剩余隔离资源及登记状态后处理；本操作不会重复删除或自动判定清除成功。',
    }
    if action in dedicated:
        evidence.update(detail=dedicated[action])
        return evidence
    env = original.get('target') or DEPLOYMENTS.get(action)
    if env:
        evidence['observation'] = executor.runtime.observe(env)
    deploy = [item['receipt'] for item in operations if item['action'] == 'deploy']
    if action in DEPLOYMENTS and deploy and deploy[-1]['status'] == 'succeeded':
        evidence.update(disposition='verify-deployment', detail='远端部署已完成；继续核对实际版本、迁移及登录，不重跑部署。')
        evidence['deploymentReceipt'] = deploy[-1]
    elif action in ('accept-prod', 'accept-backup'):
        evidence.update(disposition='verify-opening', detail='核对原包并重新技术检查；明确确认后完成业务开放，不执行迁移。')
    elif action in ('mark-tested', 'accept-rehearsal', 'verify-prod', 'verify-backup'):
        evidence.update(disposition='verify-checks', detail='继续原环境的版本、迁移和登录检查，不重跑部署或替代正式业务验收。')
    elif not original.get('effectsStarted'):
        evidence.update(disposition='close-pre-effect', detail='原任务未进入业务修改；核对起点未变后关闭失败尝试，可重新提交。')
    elif action in DEPLOYMENTS:
        evidence.update(disposition='recovery-required', detail='部署未完整成功；使用原任务迁移核对和恢复入口，不能直接重跑 SQL。')
    return evidence


def reconcile(executor, original, evidence, job):
    from intruoyi_runtime import audit_ledger
    from intruoyi_build import target_input_plan
    from intruoyi_executor import validate_origin
    decision = evidence['disposition']
    require(decision in ('close-build', 'close-pre-effect', 'verify-deployment', 'verify-opening', 'verify-checks'),
            evidence['detail'])
    env = original.get('target') or DEPLOYMENTS.get(original['action'])
    if decision == 'close-build':
        if any(p['releaseTag'] == original.get('releaseTag') for p in executor.state['packages']):
            package, _ = executor.package(original['releaseTag'])
            require(package['gitCommit'] == original['payload']['commit'], 'Completed build source differs')
            job['result'] = dict(releaseTag=package['releaseTag'], registered=True)
    elif decision == 'close-pre-effect':
        if env:
            require(original.get('originFingerprint') and
                    evidence['observation']['fingerprint'] == original['originFingerprint'],
                    'Original target origin cannot be proven unchanged')
    else:
        package, manifest = executor.package(original['releaseTag'])
        observation = validate_origin(evidence['observation'])
        expected = {role: manifest['images'][role]['id'] for role in ('backend', 'frontend')}
        require(observation['releaseTag'] == package['releaseTag'] and observation['images'] == expected,
                'Actual installed package differs')
        audit_ledger(observation, manifest)
        plan = target_input_plan(manifest['migrations'], observation['ledgerRecords'],
                                 'prod' if env == 'rehearsal' else env)
        require(plan['status'] == 'passed' and not any(item['action'] == 'APPLY' for item in plan['items']),
                'Pending migrations prevent reconciliation')
        if decision == 'verify-deployment':
            receipt = evidence['deploymentReceipt']['result']
            for key in ('releaseTag', 'images', 'schemaSha256', 'ledgerSha256'):
                require(observation[key] == receipt[key], 'Deployment receipt differs from live target: ' + key)
            require(observation['maintenance'] is (env != 'test'), 'Deployment admission changed')
            deployment = package.get('outcomes', {}).get(env, {}).get('deployment', {})
            require(deployment.get('jobId') == original['id'] or deployment.get('reconciles') == original['id'],
                    'A later deployment owns this target')
            executor.state['environments'][env] = dict(observation, baselineStatus='registered', maintenanceUnknown=False)
            package['stage'] = {'test':'test-deployed', 'rehearsal':'rehearsal-upgraded',
                                'prod':'prod-deployed', 'backup':'backup-deployed'}[env]
            if env == 'rehearsal':
                executor.active_rehearsal(package).update(status='upgraded', upgradedSchemaSha256=observation['schemaSha256'])
            job['target'] = env
            if env == 'prod':
                job['rehearsalId'] = original['rehearsalId']
            # Recovery points belong to the original deploy, never to a check.
            deployment.update(status='succeeded', jobId=original['id'], reconciledBy=job['id'])
            if env == 'prod':
                deployment['rehearsalId'] = job['rehearsalId']
            executor.save()
            executor.verify_technical(env, package, manifest, job)
        elif decision == 'verify-opening':
            require(env in ('prod', 'backup') and original.get('payload', {}).get('note'),
                    'Original business acceptance intent required')
            require(package['stage'] in (env+'-deployed', 'prod-accepted' if env == 'prod' else 'completed'),
                    'Candidate is no longer awaiting original acceptance')
            job['target'] = env
            executor.verify_technical(env, package, manifest, job, opening=True)
        else:
            job['target'] = env
            executor.verify_technical(env, package, manifest, job)
    original['resolution'] = dict(decision='reconciled', jobId=job['id'], actor=job['actor'], time=stamp(),
                                  note=job['payload']['note'], disposition=decision)
    for attempt in executor.state['jobs']:
        if attempt.get('originalTaskId') == original['id'] and attempt['status'] in ('failed', 'interrupted'):
            attempt['resolution'] = dict(original['resolution'])


def execute(executor, job):
    original = next(j for j in executor.state['jobs'] if j['id'] == job['originalTaskId'])
    try:
        executor.step(job, 'inspect-original-execution')
        evidence = inspect(executor, original)
        original['interruptionInspection'] = evidence
        job['result'] = evidence
        executor.save()
        if job['action'] == 'reconcile-interruption':
            reconcile(executor, original, evidence, job)
        job['status'] = 'succeeded'
    except Exception as error:
        job.update(status='interrupted' if getattr(error, 'remoteStatusUnknown', False) else 'failed',
                   error=str(error).replace(executor.password, '[REDACTED]'))
        executor.log(job, 'Interruption reconciliation stopped: ' + job['error'])
    finally:
        # Inspection failure is evidence, not a new deployment blocker. The
        # unresolved original remains the exclusive gate until it is reconciled.
        if job['action'] == 'inspect-interruption' and job['status'] == 'failed':
            job['resolution'] = dict(decision='inspection-failed', originalTaskId=original['id'])
        job['finishedAt'] = stamp()
        executor.save()
