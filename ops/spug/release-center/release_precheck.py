"""On-demand prerequisite diagnostics. Never deploy, migrate or accept a release."""
import os
from pathlib import Path
import re
import secrets
import shutil
import threading

from executor import require, stamp
from intruoyi_build import check_local_space, connect_nas, target_input_plan
from intruoyi_runtime import Runtime, audit_ledger, rehearsal_profile

ACTION = 'check-prerequisites'
TARGETS = {'build-release': None, 'publish-test': 'test', 'promote-prod': 'prod', 'promote-backup': 'backup'}
LIMITS = '只检查所列前置条件；不编译、不导入镜像、不执行迁移数据预检或迁移，不替代停写后的复查和业务验收。'
TARGET_NAMES = {'test':'测试服', 'prod':'正式服', 'backup':'备用服'}


def submit(executor, payload, actor):
    operation = payload.get('operation')
    require(operation in TARGETS, '请选择构建、测试发布、正式发布或备用发布检查')
    if operation == 'build-release':
        require(re.fullmatch('[0-9a-f]{40}', payload.get('commit', '')), '请选择完整 Git 提交号')
        require(not payload.get('releaseTag'), '构建检查绑定提交，不绑定候选包')
    else:
        require(isinstance(payload.get('releaseTag'), str) and payload['releaseTag'], '请选择待检查发布包')
    with executor.lock:
        existing = next((j for j in executor.state['jobs'] if j.get('requestId') == payload['requestId']), None)
        if existing:
            require(existing['action'] == ACTION and existing['payload'] == payload, 'Request ID binding mismatch')
            return existing
        require(not any(j['status'] == 'running' for j in executor.state['jobs'])
                and not (executor.worker and executor.worker.is_alive()), '其他任务仍在运行，请结束后再检查')
        job = dict(id='JOB-'+secrets.token_hex(5), requestId=payload['requestId'], action=ACTION,
                   payload=payload, actor=actor, status='running', releaseTag=payload.get('releaseTag'),
                   createdAt=stamp(), logs=[], target=TARGETS[operation])
        executor.state['jobs'].insert(0, job)
        executor.save()
        executor.worker = threading.Thread(target=executor.execute, args=(job,), daemon=True)
        executor.worker.start()
        return job


def safe_error(error, executor):
    # OS/subprocess exceptions may contain arguments or secret-bearing paths.
    if not isinstance(error, (ValueError, RuntimeError)):
        return type(error).__name__+'：检查未完成，请核对该项配置、连接及权限'
    text = str(error)
    for value in (executor.password, executor.c.get('bridgeKey')):
        if value:
            text = text.replace(value, '[REDACTED]')
    text = re.sub(r'(?i)(password|passwd|token|secret|authorization)([\s=:]+)[^\s;,]+', r'\1\2[REDACTED]', text)
    text = re.sub(r'://[^\s/@]+:[^\s/@]+@', '://[REDACTED]@', text)
    return text[-1500:]


def probe_directory(directory):
    """Only our random probe file is created, read, renamed and removed."""
    root = Path(directory)
    require(root.is_dir(), '检查目录不存在：'+str(root))
    source = root/('.spug-precheck-'+secrets.token_hex(12))
    renamed = source.with_suffix('.verified')
    content = secrets.token_bytes(32)
    try:
        with source.open('xb') as stream:
            stream.write(content)
        require(source.read_bytes() == content, '存储探针读回不一致')
        source.rename(renamed)
        require(renamed.read_bytes() == content, '存储探针重命名后读回不一致')
    finally:
        # A cleanup failure is a failed check, never hidden as success.
        if source.exists():
            source.unlink()
        if renamed.exists():
            renamed.unlink()
    return {'directory': str(root), 'writeReadRenameDelete': True}


def local_storage(executor):
    budgets = check_local_space(executor)
    for path in (executor.root, Path(executor.c['buildWorktreeRoot'])):
        require(path.is_dir(), '本地发布目录尚未建立：'+str(path))
        probe_directory(path)
    return budgets


def nas_storage(executor):
    connect_nas(executor.c.get('nasPath', ''), executor.c.get('nasCredentialsFile'))
    return probe_directory(executor.c['nasPath'])


def tool(executor, name, arguments):
    executable = shutil.which(name)
    require(executable, '找不到工具：'+name)
    executor.run([executable, *arguments], timeout=30)
    return {'executable': executable, 'commandCompleted': True}


def source_commit(executor, commit):
    repo = executor.c['repo']
    actual = executor.run(['git', '-C', repo, 'rev-parse', commit+'^{commit}'], timeout=30).decode().strip()
    require(actual == commit, '指定源码提交不存在或不匹配')
    for relative in ('IntRuoyiBackend/pom.xml', 'IntRuoyiFronted/package.json', 'IntRuoyiFronted/pnpm-lock.yaml'):
        executor.run(['git', '-C', repo, 'cat-file', '-e', commit+':'+relative], timeout=30)
    return {'commit': actual, 'uncommittedChangesIncluded': False}


def base_images(executor):
    result = {}
    for role in ('backend', 'frontend'):
        reference = executor.c.get('localRuntimeImages', {}).get(role)
        require(reference, '缺少本地基础镜像配置：'+role)
        identity = executor.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', reference], timeout=30).decode().strip()
        require(re.fullmatch('sha256:[a-f0-9]{64}', identity), '本地基础镜像身份无效：'+role)
        result[role] = identity
    return result


def workflow(executor, job, package):
    operation = job['payload']['operation']
    blockers = [j['id'] for j in executor.state['jobs'] if j['id'] != job['id']
                and j['action'] != ACTION and j['status'] in ('running', 'interrupted') and not j.get('resolution')]
    require(not blockers, '先核对运行或中断任务：'+', '.join(blockers))
    require(not any(e.get('recoveryPending') for e in executor.state['environments'].values()), '存在待验收的恢复，请先完成原恢复任务')
    if operation == 'build-release':
        require(all(executor.state['environments'].get(e, {}).get('baselineStatus') == 'registered'
                    for e in ('test', 'prod', 'backup')), '三服基线尚未完整登记')
        rehearsal_profile(executor.c, 'prod')
        return {'registeredTargets': ['test', 'prod', 'backup']}
    require(package and not package.get('baseline') and not package.get('abandoned'), '所选包不是可发布候选包')
    retry = job['payload'].get('retryOf')
    expected = {'publish-test': ('built',), 'promote-prod': ('rehearsal-passed',), 'promote-backup': ('prod-accepted',)}[operation]
    if retry:
        require(operation == 'promote-backup', '仅备用检查可关联补发任务')
        from backup_retry import validate_retry
        validate_retry(executor, package, retry)
    else:
        require(package['stage'] in expected, '当前包阶段不满足所选操作：'+package['stage'])
    require(not any(executor.failed_task_blocks(j, operation, job['payload'], package)
                    for j in executor.state['jobs'] if j['id'] != job['id']), '该包存在未解决的失败任务')
    if operation == 'promote-prod':
        require(executor.technical_passed(package, 'test') and executor.technical_passed(package, 'rehearsal'),
                '测试及正式基线演练的技术检查尚未通过')
    if operation == 'promote-backup':
        require(package.get('outcomes', {}).get('prod', {}).get('acceptance', {}).get('status') == 'passed'
                and executor.technical_passed(package, 'prod'), '正式技术检查及开放验收尚未通过')
    return {'stage': package['stage']}


def execute(executor, job):
    from intruoyi_executor import validate_origin, passed_rehearsal, backup_rehearsal_schema
    operation = job['payload']['operation']
    report = dict(operation=operation, commit=job['payload'].get('commit'), releaseTag=job.get('releaseTag'),
                  status='running', startedAt=stamp(), limits=LIMITS, checks=[],
                  executionMode=executor.c.get('executionMode', 'console'), executorPid=os.getpid())
    job['result'] = report
    executor.save()

    def check(identity, label, callback, dependency=True):
        row = dict(id=identity, label=label, status='running', startedAt=stamp())
        report['checks'].append(row)
        executor.step(job, label)
        value = None
        if not dependency:
            row.update(status='blocked', detail='依赖项未通过，未执行本项')
        else:
            try:
                value = callback()
                row.update(status='passed', detail='检查通过', evidence=value)
            except Exception as error:
                row.update(status='failed', detail=safe_error(error, executor))
        row['finishedAt'] = stamp()
        executor.save()
        return value, row['status'] == 'passed'

    package = manifest = None
    if operation == 'build-release':
        check('source', '固定源码提交', lambda: source_commit(executor, job['payload']['commit']))
        check('local-storage', '本地构建空间与读写权限', lambda: local_storage(executor))
        for name, args in [('java', ['-version']), ('mvn.cmd' if os.name == 'nt' else 'mvn', ['-version']),
                           ('node', ['--version']), ('pnpm.cmd' if os.name == 'nt' else 'pnpm', ['--version'])]:
            check('tool-'+name, '构建工具 '+name, lambda n=name, a=args: tool(executor, n, a))
        _, docker_ok = check('docker', '本机 Docker 引擎', lambda: tool(executor, 'docker', ['info', '--format', '{{.ServerVersion}}']))
        check('base-images', '本地前后端基础镜像', lambda: base_images(executor), docker_ok)
    else:
        verified = []
        def original_package():
            pair = executor.package(job['releaseTag'])
            verified.extend(pair)
            return {key:pair[0][key] for key in ('packageSha256', 'manifestSha256')}
        identity, package_ok = check('package', '发布包原件及全部摘要', original_package)
        if package_ok:
            package, manifest = verified
            report.update(identity)
    check('nas', 'NAS 发布目录认证及读写', lambda: nas_storage(executor))
    check('workflow', '所选操作的流程前置条件', lambda: workflow(executor, job, package),
          operation == 'build-release' or package is not None)
    # A separate transport has no operation binding: these inspections never create
    # remote deployment journals, staging folders, or baseline registrations.
    runtime = Runtime(dict(executor.c, operationTimeout=60))
    def transport_tools():
        paths = {name:shutil.which(name) for name in ('ssh','scp')}
        require(all(paths.values()), 'SSH 或 SCP 工具缺失')
        runtime.ssh_options()
        return paths
    check('transport-tools', 'SSH、SCP 工具及连接配置', transport_tools)
    observations = {}
    targets = ('test', 'prod', 'backup') if operation == 'build-release' else (('prod', 'backup') if operation == 'promote-backup' else (TARGETS[operation],))
    for env in targets:
        latest = []
        def observe_target(e=env):
            value = runtime.observe(e)
            latest.append(value)
            return {k:value.get(k) for k in ('releaseTag', 'fingerprint', 'observedAt')}
        _, observed = check(env+'-ssh', TARGET_NAMES[env]+'：SSH、程序版本与数据库状态读取', observe_target)
        observation = latest[0] if observed else None
        if observed:
            observations[env] = observation
        def healthy(value=observation):
            validate_origin(value)
            require(value.get('maintenance') is False and value.get('readOnly') == {'read_only':False,'super_read_only':False},
                    '目标处于维护或数据库写保护状态，请先核对原任务')
            return {k:value[k] for k in ('releaseTag','backendHealth','frontendHttpStatus','readOnly')}
        check(env+'-health', TARGET_NAMES[env]+'：前后端健康与维护状态', healthy, observed)
        # Production is only observed when preparing a backup-only deployment.
        if operation == 'promote-backup' and env == 'prod':
            continue
        remote_rows, remote_ok = check(env+'-resources', TARGET_NAMES[env]+'：发布空间与资源前置条件',
                                      lambda e=env: runtime.call(e, 'prerequisite-resources'))
        if remote_ok:
            report['checks'].pop()
            for row in remote_rows['checks']:
                report['checks'].append(dict(row, id=env+'-'+row['id'], label=TARGET_NAMES[env]+'：'+row['label']))
            executor.save()
    if package is not None:
        target = TARGETS[operation]
        def target_plan():
            obs = observations[target]
            executor.check_deployment_order(operation, package, dict(executor.state['environments'], **observations))
            for key in ('images', 'schemaSha256', 'ledgerSha256'):
                require(obs[key] == executor.state['environments'][target][key], '目标实际起点与登记基线不同：'+key)
            audit_ledger(obs, manifest)
            plan = target_input_plan(manifest['migrations'], obs['ledgerRecords'], target)
            if target == 'prod':
                passed_rehearsal(package, 'prod', obs['fingerprint'])
            elif target == 'backup':
                prod = observations['prod']
                require(prod['releaseTag'] == package['releaseTag'] and prod.get('maintenance') is False
                        and prod['images'] == {r:manifest['images'][r]['id'] for r in ('backend','frontend')},
                        '正式实际运行包或开放状态与本次备用发布不一致')
                backup_rehearsal_schema(package, obs)
            return {'target':target, 'originFingerprint':obs['fingerprint'], 'plan':plan}
        check('target-plan', '目标起点、迁移计划与已验证升级路径', target_plan,
              all(env in observations for env in targets))
    report['status'] = 'passed' if all(row['status'] == 'passed' for row in report['checks']) else 'failed'
    report['finishedAt'] = stamp()
    job.update(status='succeeded' if report['status'] == 'passed' else 'failed', finishedAt=stamp())
    if report['status'] != 'passed':
        job['error'] = '发布前检查未通过；请处理失败或未检查项后重新检查。此任务未执行发布。'
    executor.save()
