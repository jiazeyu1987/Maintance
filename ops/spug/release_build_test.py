"""Spug manual entry for the existing, pinned build -> NAS -> TEST release engine.

The UI submission only starts a durable worker. Only status=PASSED means the
original build, deployment and managed browser acceptance have all completed.
No unknown write is replayed, including after a worker/container interruption.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from release_adapter import Client, Refused, emit, origin, read_json, save_receipt, sync_directory

CONFIG = Path('/run/intruoyi-spug/build-test.private.json')
ROOT = Path('/var/lib/intruoyi-spug/build-test')
API = '/infra/runtime-control/release-workflows'
CONTEXT_KEYS = ('sourceSelectionId', 'expectedSelectionDigest', 'presetId', 'presetVersion',
                'maintenanceCommit', 'applicationCommit', 'frontendCommit', 'controlCommit',
                'applicationProfileId', 'applicationProfileVersion', 'applicationRegistrySha256',
                'applicationDescriptorSha256', 'applicationExecutionSha256',
                'applicationRegistrationSha256', 'applicationTargetSha256')
STOPPED = {'FAILED', 'RECOVERY_REQUIRED', 'CANCELED'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_config(path):
    raw = path.read_bytes()
    config = read_json(path)
    origin(config)
    if (config.get('schemaVersion') != 'spug-build-test/v1' or config.get('applicationTestTenantId') != 122
            or config.get('allowedTargets') != ['TEST'] or config.get('publishEnabled') is not True
            or config.get('productionPaused') is not True):
        raise Refused('BUILD_TEST_SCOPE_INVALID: only the approved TEST application tenant/target is enabled')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}', str(config.get('runId', ''))):
        raise Refused('BUILD_TEST_RUN_ID_REQUIRED')
    context = config.get('sourceContext')
    if not isinstance(context, dict) or any(not isinstance(context.get(k), str) or not context[k]
                                            for k in CONTEXT_KEYS):
        raise Refused('BUILD_TEST_FROZEN_CONTEXT_REQUIRED')
    for key in CONTEXT_KEYS:
        if (key.endswith('Commit') and not re.fullmatch(r'[a-f0-9]{40}', context[key])) or (
                (key.endswith('Sha256') or key.endswith('Digest'))
                and not re.fullmatch(r'[a-f0-9]{64}', context[key])):
            raise Refused('BUILD_TEST_SOURCE_IDENTITY_INVALID')
    for name in ('release_build_test.py', 'release_adapter.py'):
        if config.get('adapterSha256', {}).get(name) != digest(Path(__file__).with_name(name).read_bytes()):
            raise Refused('BUILD_TEST_ADAPTER_CHANGED')
    continuation = config.get('continuationFrom')
    if continuation is not None:
        if not isinstance(continuation, dict):
            raise Refused('BUILD_TEST_CONTINUATION_INVALID')
        for key in ('config', 'journal'):
            ref = continuation.get(key, {})
            if (not isinstance(ref.get('path'), str) or not Path(ref['path']).is_absolute()
                    or digest(Path(ref['path']).read_bytes()) != ref.get('sha256')):
                raise Refused('BUILD_TEST_CONTINUATION_ORIGINAL_CHANGED')
        original = read_json(continuation['config']['path'])
        original_receipt = read_json(continuation['journal']['path'])
        if (any(config.get(k) != original.get(k) for k in ('runId', 'sourceContext', 'baseUrl', 'tenantId',
                'username', 'password', 'applicationTestTenantId', 'publishEnabled', 'productionPaused', 'allowedTargets'))
                or original_receipt.get('configSha256') != continuation['config']['sha256']
                or original_receipt.get('state') != 'STOPPED'
                or original_receipt.get('stoppedFrom') != 'BUILD_SUBMISSION_RESERVED'):
            raise Refused('BUILD_TEST_CONTINUATION_SCOPE_INVALID')
    return config, digest(raw)


def journal_path(root, config):
    # A different runId cannot circumvent this exclusive frozen-source reservation.
    key = digest(json.dumps([origin(config), config['tenantId'],
                             config['sourceContext']['expectedSelectionDigest']],
                            separators=(',', ':')).encode())
    if config.get('continuationFrom'):
        root = root / ('continuation-' + config['continuationFrom']['journal']['sha256'])
    return root / (key + '.json')


def assert_context(actual, expected):
    if not isinstance(actual, dict) or actual != expected:
        raise Refused('BUILD_TEST_SOURCE_CONTEXT_CHANGED: no build was submitted')


def assert_workflow(value, config, receipt):
    if not isinstance(value, dict) or not re.fullmatch(r'rw-[a-zA-Z0-9_-]+', str(value.get('workflowId', ''))):
        raise Refused('BUILD_TEST_WORKFLOW_RESPONSE_INVALID')
    context = config['sourceContext']
    for key in ('maintenanceCommit', 'applicationCommit', 'frontendCommit',
                'sourceSelectionId', 'presetId', 'presetVersion'):
        if value.get(key) != context[key]:
            raise Refused('BUILD_TEST_WORKFLOW_SOURCE_CHANGED')
    if value.get('controlSource', {}).get('approvedCommit') != context['controlCommit']:
        raise Refused('BUILD_TEST_CONTROL_SOURCE_CHANGED')
    if receipt.get('workflowId') and value['workflowId'] != receipt['workflowId']:
        raise Refused('BUILD_TEST_WORKFLOW_CHANGED')
    for key in ('releaseTag', 'packageDigest', 'manifestDigest'):
        if receipt.get(key) and value.get(key) != receipt[key]:
            raise Refused('BUILD_TEST_IMMUTABLE_PACKAGE_CHANGED')
    if value.get('publishScope') != 'app-release' or value.get('state') in STOPPED:
        raise Refused('BUILD_TEST_WORKFLOW_STOPPED: ' + str(value.get('state')) + '/' + str(value.get('errorCode')))
    if not isinstance(value.get('evidenceRefs'), list):
        raise Refused('BUILD_TEST_WORKFLOW_EVIDENCE_MISSING')
    ref = 'application-profile/' + context['applicationProfileId'] + '/' + context['applicationRegistrationSha256']
    if ref not in value['evidenceRefs']:
        raise Refused('BUILD_TEST_WORKFLOW_REGISTRATION_CHANGED')


def original_operation(client, workflow, operation_id, action, config):
    operations = client.call('/infra/runtime-control/operations')
    if not isinstance(operations, list):
        raise Refused('BUILD_TEST_OPERATIONS_INVALID')
    matches = [op for op in operations if isinstance(op, dict) and op.get('operationId') == operation_id]
    if len(matches) != 1:
        raise Refused('BUILD_TEST_ORIGINAL_OPERATION_MISSING')
    op = matches[0]
    parameters = op.get('parameters')
    if (op.get('releaseWorkflowId') != workflow['workflowId'] or op.get('action') != action
            or op.get('environment') != ('release' if action == 'build-release' else 'test')
            or not isinstance(parameters, dict) or parameters.get('releaseTag') != workflow['releaseTag']):
        raise Refused('BUILD_TEST_ORIGINAL_OPERATION_CHANGED')
    if action == 'publish-test':
        for key in ('packageDigest', 'manifestDigest'):
            if parameters.get(key) != workflow.get(key):
                raise Refused('BUILD_TEST_DEPLOYED_PACKAGE_CHANGED')
    for key in ('applicationProfileId', 'applicationProfileVersion',
                'applicationTargetSha256', 'applicationRegistrationSha256'):
        if parameters.get(key) != config['sourceContext'][key]:
            raise Refused('BUILD_TEST_OPERATION_TARGET_OR_REGISTRATION_CHANGED')
    if op.get('status') in ('failed', 'blocked', 'canceled'):
        raise Refused('BUILD_TEST_ORIGINAL_OPERATION_FAILED')
    return op


def public_result(receipt):
    return {key: receipt[key] for key in ('runId', 'state', 'workflowId', 'releaseTag',
                                         'packageDigest', 'manifestDigest', 'buildOperationId',
                                         'testOperationId', 'workflowState', 'error', 'updatedAt')
            if key in receipt}


def bound_receipt(path, config, config_sha):
    receipt = read_json(path)
    if (receipt.get('configSha256') != config_sha or receipt.get('runId') != config['runId']
            or receipt.get('sourceContext') != config['sourceContext']
            or receipt.get('baseUrl') != origin(config) or receipt.get('tenantId') != config['tenantId']):
        raise Refused('BUILD_TEST_RESULT_CONFIG_CHANGED')
    return receipt


def resumable_stage(receipt):
    # Unknown writes and terminal failures cannot be turned into a new submission.
    if receipt.get('state') not in ('BUILDING', 'DEPLOYING'):
        raise Refused('BUILD_TEST_CONTINUE_STAGE_UNSAFE: unknown write or terminal state; no replay')
    if not receipt.get('workflowId') or not receipt.get('buildOperationId') or not receipt.get('releaseTag'):
        raise Refused('BUILD_TEST_CONTINUE_IDENTITY_MISSING')
    if receipt['state'] == 'DEPLOYING' and any(not receipt.get(k) for k in
            ('testOperationId', 'packageDigest', 'manifestDigest')):
        raise Refused('BUILD_TEST_CONTINUE_IDENTITY_MISSING')
    return receipt['state']


def live_originals(client, config, receipt):
    value = client.call(API + '/' + receipt['workflowId'])
    assert_workflow(value, config, receipt)
    build = original_operation(client, value, receipt['buildOperationId'], 'build-release', config)
    if build.get('reason') != 'Spug TEST build ' + config['runId']:
        raise Refused('BUILD_TEST_BUILD_REASON_CHANGED')
    deploy = None
    if receipt.get('testOperationId'):
        deploy = original_operation(client, value, receipt['testOperationId'], 'publish-test', config)
        if deploy.get('reason') != 'Spug TEST deploy ' + config['runId']:
            raise Refused('BUILD_TEST_DEPLOY_REASON_CHANGED')
    operations = client.call('/infra/runtime-control/operations')
    known = {receipt['buildOperationId'], receipt.get('testOperationId')}
    if any(not isinstance(o, dict) for o in operations) or any(o.get('releaseWorkflowId') == value['workflowId']
            and o.get('operationId') not in known for o in operations):
        raise Refused('BUILD_TEST_UNBOUND_WORKFLOW_OPERATION: cannot continue or replay')
    return value, build, deploy


def launch_worker(config_path, root, path, lock_fd=None):
    command = [sys.executable, str(Path(__file__).resolve()), '--mode', 'worker',
               '--config', str(config_path), '--records', str(root)]
    if lock_fd is not None:
        command.extend(['--lock-fd', str(lock_fd)])
    with path.with_suffix('.worker.log').open('ab') as output:
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                start_new_session=True, close_fds=True,
                                pass_fds=() if lock_fd is None else (lock_fd,))


def resume_known(config_path, root, config, config_sha):
    path = journal_path(root, config)
    with path.with_suffix('.worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused('BUILD_TEST_WORKER_ALREADY_RUNNING') from None
        receipt = bound_receipt(path, config, config_sha)
        stage = resumable_stage(receipt)
        client = Client(config)
        client.login()
        value, build, deploy = live_originals(client, config, receipt)
        if (stage == 'BUILDING' and (deploy is not None or value['state'] not in
                ('PREFLIGHTING', 'TESTING', 'BUILDING', 'READY'))):
            raise Refused('BUILD_TEST_CONTINUE_STAGE_CHANGED')
        if stage == 'DEPLOYING' and (build.get('status') != 'succeeded' or deploy is None
                or value['state'] not in ('TEST_DEPLOYING', 'TEST_DEPLOYED')):
            raise Refused('BUILD_TEST_CONTINUE_STAGE_CHANGED')
        # Pass the held flock to the worker: concurrent clicks cannot slip through startup.
        process = launch_worker(config_path, root, path, lock.fileno())
        emit('SUBMITTED_NOT_PASSED', '继续原操作；不重建，已提交部署只读回，不重放迁移。',
             workerPid=process.pid, originalBuildReissued=False, deploymentReissued=False,
             **public_result(receipt))
    return 0


def submit(config_path, root):
    config, config_sha = load_config(config_path)
    if config.get('continuationFrom'):
        raise Refused('BUILD_TEST_CONTINUATION_REQUIRES_CONTINUE: no new build permitted')
    path = journal_path(root, config)
    if path.exists():
        raise Refused('BUILD_TEST_ALREADY_RESERVED: query the original run; no build/deployment replay')
    client = Client(config)
    client.login()
    assert_context(client.call(API + '/creation-context'), config['sourceContext'])
    root.mkdir(parents=True, exist_ok=True)
    receipt = dict(schemaVersion='spug-build-test-run/v1', runId=config['runId'],
                   configSha256=config_sha, baseUrl=origin(config), tenantId=config['tenantId'],
                   sourceContext=config['sourceContext'], state='RESERVED', createdAt=now(), updatedAt=now())
    try:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(root)
    except FileExistsError:
        raise Refused('BUILD_TEST_ALREADY_RESERVED') from None
    if read_json(path) != receipt:
        raise Refused('BUILD_TEST_RESERVATION_READBACK_FAILED')
    log = path.with_suffix('.worker.log')
    with log.open('xb') as output:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--mode', 'worker',
                                    '--config', str(config_path), '--records', str(root)],
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                   start_new_session=True, close_fds=True)
    # Worker owns updates; do not overwrite a journal it may already have advanced.
    emit('SUBMITTED_NOT_PASSED', '已受理后台构建及测试服发布；尚未成功，请用本次发布结果查询。',
         runId=config['runId'], workerPid=process.pid, reservation=path.name)
    return 0


def continue_original(config_path, root):
    config, config_sha = load_config(config_path)
    continuation = config.get('continuationFrom')
    path = journal_path(root, config)
    if path.exists():
        return resume_known(config_path, root, config, config_sha)
    if continuation is None:
        raise Refused('BUILD_TEST_EXPLICIT_CONTINUATION_REQUIRED')
    client = Client(config, request_timeout=120)
    client.deadline = time.monotonic() + 150
    client.login()
    workflows = client.call(API)
    if not isinstance(workflows, list):
        raise Refused('BUILD_TEST_WORKFLOW_LIST_INVALID')
    # Explicit reason + frozen source + exact workflow/op IDs. Never select the latest record.
    matches = [w for w in workflows if isinstance(w, dict)
               and w.get('reason') == 'Spug TEST build ' + config['runId']]
    if len(matches) != 1 or matches[0].get('workflowId') != continuation.get('workflowId'):
        raise Refused('BUILD_TEST_ORIGINAL_REQUEST_AMBIGUOUS')
    value = client.call(API + '/' + continuation['workflowId'])
    assert_workflow(value, config, {'workflowId': continuation['workflowId']})
    operation_id = continuation.get('buildOperationId')
    op = original_operation(client, value, operation_id, 'build-release', config)
    if op.get('reason') != 'Spug TEST build ' + config['runId'] or value['state'] not in ('PREFLIGHTING', 'TESTING', 'BUILDING', 'READY'):
        raise Refused('BUILD_TEST_ORIGINAL_BUILD_NOT_ELIGIBLE')
    other = [o for o in client.call('/infra/runtime-control/operations')
             if o.get('releaseWorkflowId') == value['workflowId'] and o.get('operationId') != operation_id]
    if other:
        raise Refused('BUILD_TEST_ORIGINAL_WORKFLOW_HAS_OTHER_OPERATION')
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = dict(schemaVersion='spug-build-test-run/v1', runId=config['runId'], configSha256=config_sha,
                   baseUrl=origin(config), tenantId=config['tenantId'], sourceContext=config['sourceContext'],
                   state='BUILDING', workflowId=value['workflowId'], releaseTag=value['releaseTag'],
                   buildOperationId=operation_id, continuationFrom=continuation, originalBuildReissued=False,
                   createdAt=now(), updatedAt=now())
    try:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)
    except FileExistsError:
        raise Refused('BUILD_TEST_ALREADY_RESERVED') from None
    if read_json(path) != receipt:
        raise Refused('BUILD_TEST_CONTINUATION_READBACK_FAILED')
    with path.with_suffix('.worker.log').open('xb') as output:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--mode', 'worker',
                                    '--config', str(config_path), '--records', str(root)], stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=output, start_new_session=True, close_fds=True)
    emit('SUBMITTED_NOT_PASSED', '原构建已精确关联，继续等待原任务；没有重发构建，尚未发布成功。',
         workflowId=value['workflowId'], buildOperationId=operation_id, workerPid=process.pid,
         originalBuildReissued=False)
    return 0


def worker(config_path, root, lock_fd=None):
    config, config_sha = load_config(config_path)
    path = journal_path(root, config)
    lock_path = path.with_suffix('.worker.lock')
    with (lock_path.open('a') if lock_fd is None else os.fdopen(lock_fd, 'a')) as lock:
        if lock_fd is not None and (os.fstat(lock.fileno()).st_dev, os.fstat(lock.fileno()).st_ino) != (
                lock_path.stat().st_dev, lock_path.stat().st_ino):
            raise Refused('BUILD_TEST_INHERITED_LOCK_CHANGED')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refused('BUILD_TEST_WORKER_ALREADY_RUNNING') from None
        receipt = read_json(path)
        if (receipt.get('configSha256') != config_sha or receipt.get('runId') != config['runId']
                or receipt.get('sourceContext') != config['sourceContext']):
            raise Refused('BUILD_TEST_RESERVED_CONFIG_CHANGED')
        if receipt['state'] == 'PASSED':
            return 0
        if receipt['state'] in ('BUILD_SUBMISSION_RESERVED', 'DEPLOY_SUBMISSION_RESERVED', 'STOPPED'):
            raise Refused('BUILD_TEST_WRITE_RESULT_UNKNOWN_OR_STOPPED: preserve original; no POST replay')
        receipt.update(workerPid=os.getpid(), workerStartedAt=now(), updatedAt=now())
        save_receipt(path, receipt)
        client = Client(config, release_writes=True, request_timeout=120)
        client.deadline = time.monotonic() + 3300  # bounded below Spug's one-hour executor limit
        client.login()
        try:
            if receipt['state'] == 'RESERVED':
                assert_context(client.call(API + '/creation-context'), config['sourceContext'])
                receipt.update(state='BUILD_SUBMISSION_RESERVED', updatedAt=now())
                save_receipt(path, receipt)
                value = client.call(API, dict(reason='Spug TEST build ' + config['runId'],
                                               sourceSelectionId=config['sourceContext']['sourceSelectionId'],
                                               expectedSelectionDigest=config['sourceContext']['expectedSelectionDigest']))
                assert_workflow(value, config, receipt)
                # A response lacking operation identity is unknown, never retried.
                if not value.get('operationId'):
                    raise Refused('BUILD_TEST_BUILD_RECEIPT_UNKNOWN')
                receipt.update(state='BUILDING', workflowId=value['workflowId'], releaseTag=value['releaseTag'],
                               buildOperationId=value['operationId'], updatedAt=now())
                save_receipt(path, receipt)
            while time.monotonic() < client.deadline:
                value = client.call(API + '/' + receipt['workflowId'])
                assert_workflow(value, config, receipt)
                if receipt['state'] == 'BUILDING' and value['state'] == 'READY':
                    value, op, _ = live_originals(client, config, receipt)
                    if op.get('status') != 'succeeded':
                        raise Refused('BUILD_TEST_BUILD_NOT_SUCCEEDED')
                    for key in ('packageDigest', 'manifestDigest'):
                        if not re.fullmatch(r'[a-f0-9]{64}', str(value.get(key, ''))):
                            raise Refused('BUILD_TEST_NAS_PACKAGE_IDENTITY_MISSING')
                    workflows = client.call(API)
                    if not isinstance(workflows, list) or [w.get('workflowId') for w in workflows
                         if isinstance(w, dict) and w.get('active') is True] != [receipt['workflowId']]:
                        raise Refused('BUILD_TEST_SELECTED_WORKFLOW_CHANGED')
                    # Freeze the actual READY package; deployment runs through the existing publisher only.
                    receipt.update(state='DEPLOY_SUBMISSION_RESERVED', packageDigest=value['packageDigest'],
                                   manifestDigest=value['manifestDigest'], updatedAt=now())
                    save_receipt(path, receipt)
                    deployed = client.call(API + '/' + receipt['workflowId'] + '/publish-test',
                                           dict(reason='Spug TEST deploy ' + config['runId']))
                    assert_workflow(deployed, config, receipt)
                    if not deployed.get('operationId') or deployed['operationId'] == receipt['buildOperationId']:
                        raise Refused('BUILD_TEST_DEPLOY_RECEIPT_UNKNOWN')
                    receipt.update(state='DEPLOYING', testOperationId=deployed['operationId'], updatedAt=now())
                    save_receipt(path, receipt)
                elif receipt['state'] == 'DEPLOYING' and value['state'] == 'TEST_DEPLOYED':
                    op = original_operation(client, value, receipt['testOperationId'], 'publish-test', config)
                    if op.get('status') != 'succeeded':
                        raise Refused('BUILD_TEST_DEPLOYMENT_NOT_SUCCEEDED')
                    browser = [ref for ref in value['evidenceRefs'] if isinstance(ref, str)
                               and re.fullmatch(r'managed-browser/[a-f0-9]{64}', ref)]
                    if browser:
                        receipt.update(state='PASSED', workflowState=value['state'], evidenceRefs=value['evidenceRefs'],
                                       completedAt=now(), updatedAt=now())
                        save_receipt(path, receipt)
                        emit('BUILD_NAS_TEST_BROWSER_PASSED', '同包构建、NAS 上传、测试服部署及后台真实页面验收通过。',
                             **public_result(receipt))
                        return 0
                if receipt.get('workflowState') != value['state']:
                    receipt.update(workflowState=value['state'], updatedAt=now())
                    save_receipt(path, receipt)
                time.sleep(3)
            raise Refused('BUILD_TEST_WORKER_DEADLINE: query originals; no replay')
        except Refused as error:
            receipt.update(stoppedFrom=receipt['state'], state='STOPPED', error=str(error), updatedAt=now())
            save_receipt(path, receipt)
            raise


def status(config_path, root):
    config, config_sha = load_config(config_path)
    path = journal_path(root, config)
    receipt = bound_receipt(path, config, config_sha)
    observed = public_result(receipt)
    if receipt.get('workflowId') and receipt.get('buildOperationId'):
        client = Client(config)
        client.login()
        value, build, deploy = live_originals(client, config, receipt)
        observed.update(workflowState=value['state'], buildStatus=build.get('status'),
                        deploymentStatus=None if deploy is None else deploy.get('status'), readBackAt=now())
    if receipt.get('state') == 'PASSED':
        if (value['state'] != 'TEST_DEPLOYED' or build.get('status') != 'succeeded' or deploy.get('status') != 'succeeded'
                or not set(receipt['evidenceRefs']).issubset(value['evidenceRefs'])):
            raise Refused('BUILD_TEST_RESULT_NOT_CURRENTLY_VERIFIED')
        emit('BUILD_NAS_TEST_BROWSER_PASSED', '构建、上传、测试服部署及真实页面验收已通过；实时读回原任务。',
             **observed)
        return 0
    if receipt['state'] != 'STOPPED':
        with path.with_suffix('.worker.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                emit('NOT_PASSED', '已实时读回原操作，后台执行中；受理不等于发布成功。',
                     workerRunning=True, canContinue=False, **observed)
                return 3
        emit('WORKER_NOT_RUNNING', '已实时读回原操作。仅明确 BUILDING/DEPLOYING 身份可点击继续；未知写入阻塞。',
             workerRunning=False, canContinue=receipt['state'] in ('BUILDING', 'DEPLOYING'), **observed)
        return 2
    emit('NOT_PASSED', '原任务已停止；保留失败现场，不重复提交。', canContinue=False, **observed)
    return 2 if receipt.get('state') == 'STOPPED' else 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['submit', 'continue', 'status', 'worker'], required=True)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--records', type=Path, default=ROOT)
    parser.add_argument('--lock-fd', type=int)
    args = parser.parse_args()
    if args.lock_fd is not None:
        if args.mode != 'worker':
            raise Refused('BUILD_TEST_LOCK_FD_WORKER_ONLY')
        return worker(args.config, args.records, args.lock_fd)
    return {'submit': submit, 'continue': continue_original, 'status': status, 'worker': worker}[args.mode](args.config, args.records)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except Refused as error:
        emit('REFUSED_OR_STOPPED', str(error))
        sys.exit(2)
    except OSError:
        emit('LOCAL_STORAGE_OR_EXECUTION_FAILED', '持久记录或后台执行器失败；保留原件，不重发。')
        sys.exit(2)
