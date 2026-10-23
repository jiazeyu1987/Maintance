"""Spug -> the existing release API. Never retry a deployment POST.

Exit 0: read-only query completed (inspect outcome, not Spug's generic green icon).
Exit 2: refused, failed, or unavailable. Exit 3: submission accepted, not yet accepted.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path('/run/intruoyi-spug/backend.private.json')
SELECTION = Path('/run/intruoyi-spug/candidate.private.json')
RECORDS = Path('/var/lib/intruoyi-spug')
PREFIX = '/infra/runtime-control/release-workflows/'
BINDINGS = ('workflowId', 'releaseTag', 'packageDigest', 'manifestDigest', 'applicationCommit')
ROUTES = {'TEST': 'publish-test', 'BACKUP': 'promote-backup', 'PROD': 'promote-prod'}
ENVIRONMENTS = {'TEST': 'test', 'BACKUP': 'backup', 'PROD': 'prod'}
HELD = {'FAILED', 'RECOVERY_REQUIRED', 'CANCELED'}
STATES = {'SOURCE_FREEZING', 'PREFLIGHTING', 'TESTING', 'BUILDING', 'READY',
          'TEST_DEPLOYING', 'TEST_DEPLOYED', 'TEST_MARKING', 'TESTED', 'PROD_PREVIEW',
          'PROMOTING_PROD', 'PROD_DEPLOYED', 'PROMOTING_BACKUP', 'BACKUP_DEPLOYED',
          'COMPLETED'} | HELD


class Refused(Exception):
    pass


def emit(outcome, message, **fields):
    print(json.dumps(dict(outcome=outcome, message=message, **fields), ensure_ascii=False), flush=True)


def read_json(path):
    try:
        with Path(path).open(encoding='utf-8-sig') as stream:
            result = json.load(stream)
        if not isinstance(result, dict):
            raise ValueError()
        return result
    except (OSError, ValueError):
        raise Refused('LOCAL_INPUT_INVALID：配置或原任务记录缺失/无效；不执行发布。') from None


def origin(config):
    base = config.get('baseUrl', '')
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path != '/admin-api'
            or (parsed.scheme == 'http' and parsed.hostname not in
                ('host.docker.internal', '127.0.0.1', 'localhost'))):
        raise Refused('BACKEND_ORIGIN_REFUSED：需要明确的发布后端 /admin-api 地址。')
    if type(config.get('tenantId')) is not int or config['tenantId'] <= 0:
        raise Refused('TENANT_ID_REQUIRED：需要已核实的控制台登录租户编号。')
    if any(not isinstance(config.get(k), str) or not config[k] for k in ('username', 'password')):
        raise Refused('BACKEND_CREDENTIAL_REQUIRED：缺少合法私密登录配置。')
    if type(config.get('publishEnabled')) is not bool or type(config.get('productionPaused')) is not bool:
        raise Refused('PUBLISH_POLICY_INVALID：发布开关和正式暂停必须为明确布尔值。')
    return base


def validate_selection(selection):
    if any(not isinstance(selection.get(k), str) or not selection[k] for k in BINDINGS):
        raise Refused('CANDIDATE_REQUIRED：必须明确选择现有工作流、版本、包/manifest 摘要和源码提交。')
    for key in ('workflowId', 'releaseTag'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', selection[key]):
            raise Refused('CANDIDATE_ID_INVALID：候选编号格式无效。')
    for key in ('packageDigest', 'manifestDigest'):
        if not re.fullmatch(r'[a-f0-9]{64}', selection[key]):
            raise Refused('CANDIDATE_DIGEST_INVALID：包及 manifest 必须为完整 SHA256。')
    if not re.fullmatch(r'[a-f0-9]{40}', selection['applicationCommit']):
        raise Refused('CANDIDATE_SOURCE_INVALID：需要完整源码提交身份。')
    if selection.get('observedTestOperationId') is not None and not re.fullmatch(
            r'[a-zA-Z0-9-]{1,80}', str(selection['observedTestOperationId'])):
        raise Refused('ORIGINAL_OPERATION_ID_INVALID：明确原操作编号无效。')
    return selection


def verify_binding(record, selection):
    if any(record.get(k) != selection[k] for k in BINDINGS):
        raise Refused('CANDIDATE_CHANGED：后端固定包、manifest 或源码身份与明确选择不符。')
    if record.get('state') not in STATES or type(record.get('stateVersion')) is not int:
        raise Refused('BACKEND_STATE_INVALID：未知状态/版本，不能判定发布通过。')
    if not isinstance(record.get('evidenceRefs'), list):
        raise Refused('BACKEND_EVIDENCE_INVALID：缺少后端验收证据引用。')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Refused('BACKEND_REDIRECT_REFUSED：不向其他地址转交凭据或发布请求。')


class Client:
    def __init__(self, config, release_writes=False, request_timeout=10):
        self.base = origin(config)
        self.config = config
        self.token = None
        self.release_writes = release_writes
        if type(request_timeout) is not int or not 1 <= request_timeout <= 180:
            raise Refused('BACKEND_REQUEST_TIMEOUT_INVALID')
        self.request_timeout = request_timeout
        self.requests = []
        self.deadline = time.monotonic() + 55
        self.opener = urllib.request.build_opener(NoRedirect())

    def call(self, path, body=None):
        if body is not None and path != '/system/auth/login' and not self.release_writes:
            raise Refused('RELEASE_WRITE_DISABLED：本入口仅检查/查询，禁止发布写请求。')
        self.requests.append(dict(method='GET' if body is None else 'POST', path=path))
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Refused('QUERY_DEADLINE：本次查询已超时；原任务未重发。')
        headers = {'Content-Type': 'application/json', 'tenant-id': str(self.config['tenantId'])}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        raw = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
        try:
            req = urllib.request.Request(self.base + path, data=raw, headers=headers)
            with self.opener.open(req, timeout=min(self.request_timeout, remaining)) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise Refused('BACKEND_HTTP_REFUSED：后端 HTTP ' + str(error.code) + '；不重复提交。') from None
        except (urllib.error.URLError, TimeoutError, socket.timeout, ValueError, OSError):
            raise Refused('BACKEND_UNAVAILABLE：后端不可达或响应无效；待联调，未重复提交。') from None
        if not isinstance(result, dict) or type(result.get('code')) is not int:
            raise Refused('BACKEND_RESPONSE_INVALID：响应不符合真实 CommonResult 契约。')
        if result['code'] != 0:
            # Only expose safe symbolic errors, not upstream exceptions or secret-bearing text.
            codes = re.findall(r'\b(?:RELEASE_WORKFLOW|RUNTIME_CONTROL|TEST_ACCEPTANCE|PRODUCTION)_[A-Z0-9_]+\b',
                               str(result.get('msg', '')))
            raise Refused('BACKEND_REFUSED：' + path + ' 错误编号 ' + str(result['code']) +
                          (' / ' + ','.join(codes[:3]) if codes else '') + '；不重复提交。')
        if 'data' not in result:
            raise Refused('BACKEND_DATA_MISSING：缺少真实响应数据。')
        return result['data']

    def login(self):
        auth = self.call('/system/auth/login', dict(username=self.config['username'],
                                                  password=self.config['password'], captchaVerification=''))
        if not isinstance(auth, dict) or not isinstance(auth.get('accessToken'), str) or not auth['accessToken']:
            raise Refused('BACKEND_LOGIN_INVALID：没有合法访问凭据。')
        self.token = auth['accessToken']


def journal_path(root, config, selection, target):
    # The attempt is deliberately NOT part of this key: a new attempt cannot bypass the reservation.
    scope = [origin(config), config['tenantId'], selection['workflowId'], target]
    key = hashlib.sha256(json.dumps(scope, separators=(',', ':')).encode()).hexdigest()
    return Path(root) / (key + '.json')


def reserve(path, config, selection, target, attempt):
    if not isinstance(attempt, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', attempt):
        raise Refused('ATTEMPT_REQUIRED：需为本轮明确配置 submissionId；不能使用固定重复任务号。')
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = dict(**{k: selection[k] for k in BINDINGS}, target=target, attempt=attempt,
                   baseUrl=origin(config), tenantId=config['tenantId'], state='SUBMISSION_RESERVED',
                   reservedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), operationId=None)
    try:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)
        if read_json(path) != receipt:
            raise Refused('JOURNAL_READBACK_FAILED：原预留写入读回不一致；不提交。')
    except FileExistsError:
        raise Refused('SUBMISSION_ALREADY_RESERVED：本候选/目标已提交或结果未知；只能查询原任务。') from None
    return receipt


def sync_directory(path):
    if os.name != 'nt':
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def save_receipt(path, receipt):
    # Unique temporary file + replace keeps the original reservation valid across interruptions.
    temporary = path.with_name(path.name + '.' + str(os.getpid()) + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(path.parent)
    if read_json(path) != receipt:
        raise Refused('JOURNAL_READBACK_FAILED：原受理回执读回不一致；不重复提交。')


def load_receipt(path, config, selection, target):
    if not path.exists():
        return None
    receipt = read_json(path)
    if (any(receipt.get(k) != selection[k] for k in BINDINGS)
            or receipt.get('target') != target or receipt.get('baseUrl') != origin(config)
            or receipt.get('tenantId') != config['tenantId']):
        raise Refused('JOURNAL_BINDING_CHANGED：原提交身份与所选候选不符；禁止复用或重发。')
    return receipt


def matching_operation(operations, selection, target, receipt=None):
    if not isinstance(operations, list):
        raise Refused('OPERATION_RESPONSE_INVALID：真实操作列表不可用。')
    matches = []
    for op in operations:
        if not isinstance(op, dict):
            raise Refused('OPERATION_RESPONSE_INVALID：真实操作记录无效。')
        if op.get('releaseWorkflowId') != selection['workflowId'] or op.get('action') != ROUTES[target]:
            continue
        params = op.get('parameters')
        if (op.get('environment') != ENVIRONMENTS[target] or not isinstance(params, dict)
                or any(params.get(k) != selection[k] for k in ('releaseTag', 'packageDigest', 'manifestDigest'))):
            raise Refused('OPERATION_BINDING_CHANGED：目标操作与固定包身份不符。')
        if target == 'TEST' and any(selection.get(k) is not None and params.get(k) != selection[k]
                                     for k in ('testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest')):
            raise Refused('OPERATION_TARGET_CHANGED：原测试部署目标与已核定目标不符。')
        matches.append(op)
        if not isinstance(op.get('operationId'), str) or not op['operationId']:
            raise Refused('OPERATION_ID_INVALID：真实操作缺少持久编号。')
    if receipt and receipt.get('operationId'):
        matches = [op for op in matches if op.get('operationId') == receipt['operationId']]
        if not matches:
            raise Refused('ORIGINAL_OPERATION_MISSING：原持久操作不可查；保留记录，不重发。')
    elif receipt:
        # If the POST timed out, identify only this exact reserved request, never adopt another publisher's operation.
        matches = [op for op in matches if op.get('reason') == 'Spug ' + target + ' ' + receipt['attempt']]
    elif target == 'TEST' and selection.get('observedTestOperationId'):
        matches = [op for op in matches if op.get('operationId') == selection['observedTestOperationId']]
        if not matches:
            raise Refused('ORIGINAL_OPERATION_MISSING：明确核对的历史部署操作不可查；不换成最新操作。')
    if len(matches) > 1:
        raise Refused('OPERATION_AMBIGUOUS：存在多个匹配操作；不能猜测或重发。')
    return matches[0] if matches else None


def progress(record, target, operation, receipt):
    if record is None:
        if operation and operation.get('status') == 'succeeded':
            return 'DEPLOYED_ACCEPTANCE_UNAVAILABLE', '原部署操作成功；当前工作流详情不可查询，完整验收状态未证实。查询失败，不重发。'
        return 'WORKFLOW_QUERY_FAILED', '当前工作流详情不可查询；原操作单独显示，不能判定完整验收。'
    state = record['state']
    status = operation.get('status') if operation else None
    op_id = operation.get('operationId') if operation else None
    evidence = record['evidenceRefs']
    if status is not None and status not in ('running', 'succeeded', 'failed', 'blocked', 'canceled'):
        return 'UNVERIFIED', '操作状态未识别；不能记为完整验收通过。'
    if status in ('failed', 'blocked', 'canceled'):
        return 'FINAL_FAILED', '原部署操作失败/停止；保留原任务，不重发。'
    if not operation:
        if receipt:
            return 'SUBMISSION_UNKNOWN', '提交结果尚未关联；保留原预留记录，只能查询。'
        return 'NOT_SUBMITTED', '此目标没有可核对部署记录；只读检查通过不代表发布成功。'
    if status == 'running':
        return 'RUNNING', '原任务进行中；查询进度，不重复提交。'
    if state in HELD:
        if target == 'TEST' and record.get('failedStage') == 'TEST_ACCEPTANCE' and status == 'succeeded':
            return 'DEPLOYED_ACCEPTANCE_FAILED', '部署已成功；后续完整业务验收失败，未标记已测试。原失败工作流只读，不重发。'
        return 'DEPLOYED_WORKFLOW_HELD', '原部署操作已成功；工作流失败/暂停，完整验收未通过。'
    tested = any(isinstance(item, str) and re.fullmatch(r'acceptance/[a-f0-9]{64}', item) for item in evidence)
    test_states = {'TESTED', 'PROD_PREVIEW', 'PROMOTING_PROD', 'PROD_DEPLOYED',
                   'PROMOTING_BACKUP', 'BACKUP_DEPLOYED', 'COMPLETED'}
    passed = (status == 'succeeded' and (
        (target == 'TEST' and tested and state in test_states)
        or (target == 'BACKUP' and 'backup-deployed/' + op_id in evidence
            and state in {'BACKUP_DEPLOYED', 'PROD_PREVIEW', 'PROMOTING_PROD', 'PROD_DEPLOYED', 'COMPLETED'})
        or (target == 'PROD' and record.get('productionOperationId') == op_id
            and 'operation/' + op_id + '.json' in evidence
            and state in {'PROD_DEPLOYED', 'COMPLETED'})))
    if passed:
        return 'FINAL_ACCEPTED', '后端原任务及对应完整验收阶段有证据通过。'
    return 'ACCEPTANCE_PENDING', '部署操作结束，但完整验收尚无充分后端证据。'


def query(client, config, selection, target, root):
    # Operation and acceptance are independent reads. Failure of one is surfaced, never replaced with the other.
    operations = client.call('/infra/runtime-control/operations')
    failure = None
    record = None
    try:
        value = client.call(PREFIX + selection['workflowId'])
        if not isinstance(value, dict):
            raise Refused('WORKFLOW_RESPONSE_INVALID：缺少真实工作流。')
        verify_binding(value, selection)
        record = value
    except Refused as error:
        failure = str(error)
    targets = list(ROUTES) if target == 'ALL' else [target]
    snapshot = dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    baseUrl=origin(config), tenantId=config['tenantId'], records=[], deploymentSubmitted=False)
    for item in targets:
        path = journal_path(root, config, selection, item)
        receipt = load_receipt(path, config, selection, item)
        op = matching_operation(operations, selection, item, receipt)
        outcome, message = progress(record, item, op, receipt)
        value = dict(outcome=outcome, message=message, target=item, **{k: selection[k] for k in BINDINGS},
             phase=record['state'] if record else None, stateVersion=record['stateVersion'] if record else None,
             failedStage=record.get('failedStage') if record else None, errorCode=record.get('errorCode') if record else None,
             workflowQueryError=failure,
             operationId=op.get('operationId') if op else (receipt or {}).get('operationId'),
             operationStatus=op.get('status') if op else None,
             requestedAt=op.get('requestedAt') if op else None,
             association='SPUG_ORIGINAL_REQUEST' if receipt else 'EXISTING_BACKEND_RECORD',
             submissionState=receipt.get('state') if receipt else None,
             deploymentResult='已成功' if op and op.get('status') == 'succeeded' else '未成功或未提交',
             acceptanceResult='失败，未标记已测试' if outcome == 'DEPLOYED_ACCEPTANCE_FAILED'
                 else '当前详情不可查，未证实；不判通过' if record is None
                 else '完整验收通过' if outcome == 'FINAL_ACCEPTED' else '尚未通过完整验收',
             **({k: op['parameters'].get(k) for k in ('testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest')}
                if item == 'TEST' and op else {}))
        snapshot['records'].append(value)
        print('目标：' + item + '；版本：' + selection['releaseTag'], flush=True)
        print('部署：' + value['deploymentResult'] + '；完整验收：' + value['acceptanceResult'], flush=True)
        print('原操作：' + (value['operationId'] or '无') + '；工作流：' + (value['phase'] or '查询失败'), flush=True)
        print('关联：' + ('Spug 原请求' if receipt else '读取既有后端记录，非 Spug 新发布'), flush=True)
        snapshot['requests'] = client.requests
        # Spug's native local executor waits before reading stdout: keep multi-target output below a pipe buffer.
        if target == 'ALL' and item != 'TEST':
            emit(outcome, message, target=item, phase=value['phase'], operationId=value['operationId'],
                 deploymentResult=value['deploymentResult'], acceptanceResult=value['acceptanceResult'])
        else:
            emit(**value)
    snapshot_path = Path(root) / 'queries' / (hashlib.sha256(
        json.dumps([origin(config), config['tenantId'], selection['workflowId'], target]).encode()).hexdigest() + '.json')
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    save_receipt(snapshot_path, snapshot)
    if failure:
        emit('WORKFLOW_QUERY_FAILED', failure, requests=client.requests, persistentQuery=str(snapshot_path))
        raise Refused(failure)
    emit('READ_ONLY_QUERY_COMPLETE', '查询完成；Spug 查询步骤的成功不代表三服发布通过。',
         publishEnabled=config['publishEnabled'], productionPaused=config['productionPaused'],
         persistentQuery=str(snapshot_path), requests=client.requests)
    return record


CONTEXT_FIELDS = ('sourceSelectionId', 'expectedSelectionDigest', 'existingPackageBindingSha256',
                  'executorPublisherSha256', 'applicationCommit', 'frontendCommit',
                  'testTargetProfileId', 'testTargetFingerprint', 'testDeploymentBindingDigest')


def check_context(context, selection):
    expected = selection.get('admission')
    if not isinstance(context, dict) or not isinstance(expected, dict):
        raise Refused('EXISTING_PACKAGE_APPROVAL_REQUIRED：缺少明确确认的已有包批准输入。')
    if any(not isinstance(expected.get(k), str) or not expected[k] or context.get(k) != expected[k]
           for k in CONTEXT_FIELDS):
        raise Refused('EXISTING_PACKAGE_APPROVAL_CHANGED：已有包批准、成功发布器或目标身份变化；不自动追最新。')
    for key in ('expectedSelectionDigest', 'existingPackageBindingSha256', 'executorPublisherSha256',
                'testTargetFingerprint', 'testDeploymentBindingDigest'):
        if not re.fullmatch(r'[a-f0-9]{64}', expected[key]):
            raise Refused('EXISTING_PACKAGE_APPROVAL_INVALID：批准身份摘要无效。')
    if expected['applicationCommit'] != selection['applicationCommit']:
        raise Refused('EXISTING_PACKAGE_SOURCE_CHANGED：批准的应用源码与所选包不符。')
    if not re.fullmatch(r'[a-f0-9]{40}', expected['frontendCommit']):
        raise Refused('EXISTING_PACKAGE_SOURCE_INVALID：前端源码身份无效。')
    return {k: context[k] for k in CONTEXT_FIELDS}


def manual_check(client, config, selection, root):
    record = None
    query_error = None
    context_error = None
    context = None
    # Existing-package approval applies only to admission, never to login or the original operation query.
    try:
        context = client.call('/infra/runtime-control/release-workflows/creation-context')
        if not isinstance(context, dict):
            raise Refused('CREATION_CONTEXT_INVALID：当前正常入口上下文不可读。')
    except Refused as error:
        context_error = str(error)
    try:
        record = query(client, config, selection, 'TEST', root)
    except Refused as error:
        query_error = str(error)
    admitted = False
    approval = 'UNAVAILABLE'
    if context is not None:
        if context.get('existingPackageBindingSha256') is None and context.get('executorPublisherSha256') is None:
            approval = 'NOT_CONFIGURED_IN_NORMAL_BUILD_MODE'
            print('已有包接纳：当前正常构建模式不提供旧批准；仅接纳动作关闭，不影响原操作查询。', flush=True)
        else:
            try:
                check_context(context, selection)
                admitted = True
                approval = 'EXPLICIT_EXISTING_PACKAGE_BINDING_MATCHED'
            except Refused as error:
                approval = 'CHANGED_OR_INVALID'
                context_error = str(error)
    emit('MANUAL_TEST_CHECK_ONLY', 'TEST 手动入口仅检查/查询；未接入新工作流、未部署。',
         workflowId=selection['workflowId'], releaseTag=selection['releaseTag'],
         target='TEST', mode='check', workflowPublishable=record is not None and record['state'] == 'READY',
         publishEnabled=config['publishEnabled'], deploymentSubmitted=False,
         existingPackageApprovalVerified=admitted, admissionStatus=approval,
         sourceSelectionId=(context or {}).get('sourceSelectionId'),
         publisherSha256=(context or {}).get('executorPublisherSha256'),
         targetProfile=(context or {}).get('testTargetProfileId'), contextQueryError=context_error,
         requests=client.requests,
         nextAction='当前失败工作流只读。由正常后端产生合法 READY 候选并显式绑定后，才能另行明确手动部署；已有包接纳还需其独立批准。')
    if query_error:
        raise Refused(query_error)
    if context_error:
        raise Refused(context_error)


def admit_existing(client, config, selection, root, attempt):
    context = check_context(client.call('/infra/runtime-control/release-workflows/creation-context'), selection)
    workflows = client.call('/infra/runtime-control/release-workflows')
    if not isinstance(workflows, list):
        raise Refused('WORKFLOW_LIST_INVALID：无法核对服务端当前选择。')
    if any(isinstance(item, dict) and item.get('active') is True for item in workflows):
        raise Refused('EXISTING_WORKFLOW_SELECTED：已有活动工作流；查询或由正常主链处置，不重复接入。')
    # Reserve admission independently of deployment. An unknown response must never create a second workflow.
    scope = [origin(config), config['tenantId'], selection['packageDigest'], context['expectedSelectionDigest'], 'admit']
    path = Path(root) / ('admit-' + hashlib.sha256(json.dumps(scope).encode()).hexdigest() + '.json')
    receipt = reserve(path, config, selection, 'TEST', attempt)
    receipt.update(state='ADMISSION_RESERVED', admission=context)
    save_receipt(path, receipt)
    response = client.call('/infra/runtime-control/release-workflows/admit-existing-package',
                           dict(reason='Spug TEST ' + attempt, sourceSelectionId=context['sourceSelectionId'],
                                expectedSelectionDigest=context['expectedSelectionDigest']))
    if not isinstance(response, dict) or not isinstance(response.get('workflowId'), str):
        raise Refused('ADMISSION_RECEIPT_UNKNOWN：接入响应无效；保留原预留，不重发。')
    admitted = dict(selection, workflowId=response['workflowId'])
    verify_binding(response, admitted)
    if response['state'] != 'READY':
        raise Refused('ADMISSION_NOT_READY：后端未返回可发布候选；保留记录，不部署。')
    receipt.update(state='ADMITTED', admittedWorkflowId=response['workflowId'],
                   receivedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save_receipt(path, receipt)
    emit('EXISTING_PACKAGE_ADMITTED', '已有包接入已受理；未部署。显式核定新工作流后另行手动发布。',
         workflowId=response['workflowId'], releaseTag=response['releaseTag'], deploymentSubmitted=False)
    return 3


def publish_guard(config, target):
    if target == 'ALL':
        raise Refused('SINGLE_TARGET_REQUIRED：发布必须一次明确选择一服。')
    if target == 'PROD' and config['productionPaused']:
        raise Refused('PRODUCTION_PAUSED：正式维护仍暂停，未提交部署。')
    if target in ('BACKUP', 'PROD'):
        raise Refused('TARGET_PUBLISH_DISABLED：本轮只接入 TEST；备份服/正式服发布保持关闭，未提交部署。')
    if not config['publishEnabled']:
        raise Refused('PUBLISH_HOLD：默认检查/查询，实际发布开关关闭，未提交部署。')


def publish(client, config, selection, target, root, attempt):
    if not isinstance(attempt, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', attempt):
        raise Refused('ATTEMPT_REQUIRED：需要当前候选明确配置的 submissionId；未提交。')
    path = journal_path(root, config, selection, target)
    if path.exists():
        raise Refused('SUBMISSION_ALREADY_RESERVED：原操作已预留；执行状态查询，不重复 POST。')
    # A list response identifies the backend's selected workflow. Detail.active is false by DTO design.
    workflows = client.call('/infra/runtime-control/release-workflows')
    if not isinstance(workflows, list):
        raise Refused('WORKFLOW_LIST_INVALID：无法核对服务端当前选择。')
    selected = [item for item in workflows if isinstance(item, dict) and item.get('active') is True]
    if len(selected) != 1 or selected[0].get('workflowId') != selection['workflowId']:
        raise Refused('WORKFLOW_NOT_SELECTED：服务端当前选择与配置不符；不自动切换候选。')
    record = client.call(PREFIX + selection['workflowId'])
    if not isinstance(record, dict):
        raise Refused('WORKFLOW_RESPONSE_INVALID：缺少真实工作流。')
    verify_binding(record, selection)
    if record['state'] in HELD:
        raise Refused('WORKFLOW_HELD：失败原件待处置；不创建新任务。')
    ready = {'TEST': {'READY'}, 'BACKUP': {'TESTED'}, 'PROD': {'BACKUP_DEPLOYED'}}
    if record['state'] not in ready[target]:
        raise Refused('STAGE_NOT_READY：按 TEST → BACKUP → PROD 顺序核对前阶段，未提交。')
    previous = matching_operation(client.call('/infra/runtime-control/operations'), selection, target)
    if previous:
        raise Refused('EXISTING_OPERATION：该目标已有真实操作；查询原记录，不再创建部署。')
    receipt = reserve(path, config, selection, target, attempt)
    payload = dict(reason='Spug ' + target + ' ' + attempt)
    if target in ('BACKUP', 'PROD'):
        payload.update(expectedStateVersion=record['stateVersion'], idempotencyKey=attempt, prodConfirmText='PROD')
    if target == 'PROD':
        preview = client.call(PREFIX + selection['workflowId'] + '/production-preview',
                              dict(expectedStateVersion=record['stateVersion']))
        if not isinstance(preview, dict) or preview.get('eligible') is not True or not preview.get('previewId'):
            raise Refused('PRODUCTION_NOT_ELIGIBLE：后端正式预检未通过；保留预留，不提交部署。')
        verify_authorization_binding(preview, selection, record['stateVersion'])
        grant = client.call(PREFIX + selection['workflowId'] + '/production-authorization',
                            dict(previewId=preview['previewId'], expectedStateVersion=record['stateVersion']))
        if not isinstance(grant, dict) or not grant.get('grantId'):
            raise Refused('PRODUCTION_GRANT_INVALID：没有合法正式授权；保留预留。')
        verify_authorization_binding(grant, selection, record['stateVersion'])
        if grant.get('previewId') != preview['previewId']:
            raise Refused('PRODUCTION_PREVIEW_CHANGED：正式授权与原预检不符；保留预留。')
        payload.update(previewId=preview['previewId'], authorizationGrantId=grant['grantId'])
    response = client.call(PREFIX + selection['workflowId'] + '/' + ROUTES[target], payload)
    if not isinstance(response, dict):
        raise Refused('SUBMISSION_RECEIPT_UNKNOWN：受理响应无效；保留原预留，不重发。')
    verify_binding(response, selection)
    receipt.update(state='SUBMITTED', operationId=response.get('operationId'),
                   receivedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
    # A response without its actual operation ID stays reserved and cannot be retried.
    if not isinstance(receipt['operationId'], str) or not receipt['operationId']:
        raise Refused('SUBMISSION_RECEIPT_UNKNOWN：后端未返回原操作编号；只能查询，不重发。')
    save_receipt(path, receipt)
    emit('SUBMISSION_ACCEPTED', '已受理，尚未完整验收；执行发布状态查询，不重复点击发布。',
         target=target, **{k: selection[k] for k in BINDINGS}, operationId=receipt['operationId'])
    return 3


def verify_authorization_binding(value, selection, version):
    if (any(value.get(k) != selection[k] for k in ('workflowId', 'releaseTag', 'packageDigest', 'manifestDigest'))
            or value.get('targetEnvironment') != 'prod' or value.get('expectedStateVersion') != version):
        raise Refused('PRODUCTION_AUTHORIZATION_CHANGED：正式预检/授权与固定包、目标或状态不符。')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--selection', type=Path, default=SELECTION)
    parser.add_argument('--records', type=Path, default=RECORDS)
    parser.add_argument('--target', required=True, choices=[*ROUTES, 'ALL'])
    parser.add_argument('--mode', required=True, choices=['status', 'check', 'admit', 'publish'])
    parser.add_argument('--attempt', default='')
    args = parser.parse_args(argv)
    config = read_json(args.config)
    origin(config)
    targets = list(ROUTES) if args.target == 'ALL' else [args.target]
    if not isinstance(config.get('allowedTargets'), list) or any(t not in config['allowedTargets'] for t in targets):
        raise Refused('TARGET_REFUSED：目标未明确配置。')
    if args.mode in ('publish', 'admit'):
        # Hard hold is independent of an unavailable backend and precedes ANY request or local reservation.
        publish_guard(config, args.target)
    if args.mode in ('check', 'admit') and args.target != 'TEST':
        raise Refused('TEST_ONLY_ENTRY：手动检查/接入已有包仅支持 TEST。')
    selection = validate_selection(read_json(args.selection))
    client = Client(config, release_writes=args.mode in ('publish', 'admit'))
    client.login()
    if args.mode == 'status':
        query(client, config, selection, args.target, args.records)
        return 0
    if args.mode == 'check':
        manual_check(client, config, selection, args.records)
        return 0
    if args.mode == 'admit':
        return admit_existing(client, config, selection, args.records,
                              args.attempt or selection.get('submissionId', ''))
    return publish(client, config, selection, args.target, args.records,
                   args.attempt or selection.get('submissionId', ''))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except Refused as error:
        emit('REFUSED_OR_UNAVAILABLE', str(error))
        sys.exit(2)
    except OSError:
        emit('LOCAL_STORAGE_FAILED', '原任务持久记录写入/读回失败；不重发，不声明发布通过。')
        sys.exit(2)
