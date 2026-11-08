"""Replay exact observed FULL373 metadata locally; no backup/audit is rerun."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tarfile

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import automatic_chain_audit as audit


@pytest.fixture
def original():
    private=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
    raw=(private/'automatic-full373-dispatch-contract-diagnostic.private.json').read_bytes()
    assert len(raw)==11588 and hashlib.sha256(raw).hexdigest()=='98f7f9fc579e3cb8fe59aed420b98674e2c83e77caba15d2d79d34b15234820a'
    value=json.loads(raw)
    reply=json.loads((private/'automatic-full373-launcher-reply.private.json').read_text(encoding='utf-8'))
    observed=json.loads((Path(__file__).parent/'automatic-full373-launcher-reply-diagnostic.json').read_text(encoding='utf-8'))
    assert reply==observed['originalReply']
    records=value['records']
    return dict(request=records['request.json']['value'],selection=records['selection.json']['value'],
        python_pin=value['configPythonPin'],request_pin=records['request.json']['pin'],
        intent_pin=records['execute/native-intent.json']['pin'],
        reply_pin=records['execute/native-original-exit.json']['value']['resultPin'],
        owner_root=reply['data']['operationDirectory'],owner_result=value['originalOwnerResult'],
        launched=records['execute/native-intent.json']['value'],process=records['execute/native-process.json']['value'],
        exited=records['execute/native-original-exit.json']['value'],reply=reply)


def test_actual_full373_async_reply_is_bound_to_same_successful_owner(original):
    result=audit.verify_dispatch_contract(**original)
    assert result['launcherActualExitCode']==2
    assert result['launcherState']=='TERMINAL_UNKNOWN'
    assert result['ownerActualExitCode']==0 and result['ownerState']=='SUCCEEDED'
    assert result['originalReplyPin']==original['reply_pin']
    assert result['resolution']=='ORIGINAL_OWNER_TERMINAL_AFTER_ASYNC_REPLY'


@pytest.mark.parametrize('change', ['exit3','exit1','timedout','argv','request','intent','pid','python',
    'program','configuration','reply-operation','reply-state','reply-code','reply-exit','reply-root','reply-result',
    'owner-operation','owner-state','owner-exit','owner-failure','reply-request','reply-action','reply-schema',
    'reply-pin','restore-target','process-operation','exit-request','owner-request'])
def test_original_dispatch_rejects_unrelated_or_unsupported_evidence(original,change):
    if change=='exit3':original['exited']['actualExitCode']=3
    elif change=='exit1':original['exited']['actualExitCode']=1
    elif change=='timedout':original['exited']['timedOut']=True
    elif change=='argv':original['launched']['argv'][-1]+='.other'
    elif change=='request':original['launched']['requestPin']['sha256']='0'*64
    elif change=='intent':original['process']['intentPin']['sha256']='0'*64
    elif change=='pid':original['process']['pid']+=1
    elif change=='python':original['launched']['pythonPin']['sha256']='0'*64
    elif change=='program':original['launched']['programPin']['sha256']='0'*64
    elif change=='configuration':original['launched']['configurationPin']['sha256']='0'*64
    elif change=='reply-operation':original['reply']['operationId']='other'
    elif change=='reply-state':original['reply']['state']='FAILED_RETAINED'
    elif change=='reply-code':original['reply']['failureCode']='OTHER_UNKNOWN_ERROR'
    elif change=='reply-exit':original['reply']['actualExitCode']=0
    elif change=='reply-root':original['reply']['data']['operationDirectory']+='/other'
    elif change=='reply-result':original['reply']['data']['resultRef']+='.other'
    elif change=='owner-operation':original['owner_result']['operationId']='other'
    elif change=='owner-state':original['owner_result']['state']='RUNNING'
    elif change=='owner-exit':original['owner_result']['actualExitCode']=2
    elif change=='owner-failure':original['owner_result']['failureCode']='FAILED'
    elif change=='reply-request':original['reply']['requestId']='other'
    elif change=='reply-action':original['reply']['action']='RESTORE'
    elif change=='reply-schema':original['reply']['schemaVersion']='unknown/v1'
    elif change=='reply-pin':original['reply_pin']=dict(original['reply_pin'],sha256='0'*64)
    elif change=='restore-target':original['launched']['restoreTargetPin']={'unexpected':True}
    elif change=='process-operation':original['process']['operationId']='other'
    elif change=='exit-request':original['exited']['requestId']='other'
    else:original['owner_result']['requestId']='other'
    with pytest.raises(ValueError):audit.verify_dispatch_contract(**original)


def test_synchronous_success_requires_exact_owner_result(original):
    original['exited']['actualExitCode']=0
    original['owner_result']['action']=original['request']['action']
    original['owner_result']['schemaVersion']='backup-restore-operation-result/v1'
    original['reply']=deepcopy(original['owner_result'])
    result=audit.verify_dispatch_contract(**original)
    assert result['resolution']=='OWNER_TERMINAL_RETURNED_SYNCHRONOUSLY'
    original['reply']['finishedAt']='2026-11-07T00:00:00Z'
    with pytest.raises(ValueError):audit.verify_dispatch_contract(**original)


def test_final_audit_calls_contract_and_does_not_keep_exit_allowlist():
    source=Path(audit.__file__).read_text(encoding='utf-8')
    tree=ast.parse(source)
    entry=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit')
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='verify_dispatch_contract' for n in ast.walk(entry))
    assert "exited['actualExitCode'] in (0, 3)" not in source


def test_exact_installed_standard_launcher_contract():
    archive=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/package-0d44578/backup-restore-standard.tgz')
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3d3d8a608e5a809b34cc6b5f48f5091b066bdcc5007d084459f3e333cad7010b'
    with tarfile.open(archive) as package:
        source=package.extractfile('common/repository_minimal.py').read()
    tree=ast.parse(source)
    execute=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='execute')
    returns=[node for node in ast.walk(execute) if isinstance(node,ast.Return)]
    mapping=next(node.value.value for node in returns if isinstance(node.value,ast.Subscript) and isinstance(node.value.value,ast.Dict))
    assert ast.literal_eval(mapping)=={'SUCCEEDED':0,'FAILED_RETAINED':1,'TERMINAL_UNKNOWN':2}
    query=next(node for node in ast.walk(execute) if isinstance(node,ast.Call) and
        any(key.arg=='failureCode' and isinstance(key.value,ast.Constant) and
            key.value.value=='REPOSITORY_QUERY_ORIGINAL_OPERATION' for key in node.keywords))
    assert next(key.value.value for key in query.keywords if key.arg=='state')=='TERMINAL_UNKNOWN'
