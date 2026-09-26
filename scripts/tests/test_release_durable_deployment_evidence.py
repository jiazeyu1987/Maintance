"""T6 actual PowerShell, durable filesystem and task MySQL contracts."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import pytest

from test_release_full_package_contract import ROOT, SCRIPT, _functions, _ps
from release_test_runtime import mysql_runtime, run_mysql, application_backend_root, classic_configuration, classic_runtime, runtime_settings, mysql_flock_directory
from test_scheduler_smoke_linux_payload_integration import ps as long_ps
from test_release_runtime_identity import engine as classic_images, docker as classic_docker
from test_release_operation_lock_mysql_behavior import _setup as setup_lock_database

MODULE = ROOT / "ops/release/lib/ReleaseDeploymentEvidence.psm1"
RECOVERY = ROOT / "ops/deploy/recover-release-operation-lock.ps1"
_SETTINGS=runtime_settings()
ENGINE=classic_configuration().container_id
SCOPE={"environment":"test","host":"task-host","machineId":"a"*32,"database":"release-task",
       "serverUuid":"11111111-1111-1111-1111-111111111111"}


def shell(command):
    result=subprocess.run(["docker","exec","-i",ENGINE,"sh","-s"],input=command.encode(),capture_output=True,timeout=40)
    assert result.returncode==0,result.stderr.decode()
    return result.stdout.decode()


@pytest.fixture
def state_root():
    assert classic_runtime().container_id==ENGINE
    root="/var/lib/docker/task-inputs/"+_SETTINGS.prefix+"t6-"+uuid.uuid4().hex
    gate={"schemaVersion":"release-deployment-gate/v1","scope":SCOPE,"revision":0,"state":"READY",
          "attemptId":None,"operationDigest":None,"receiptDigest":None}
    shell(f"set -eu\nmkdir -m 700 '{root}'\nmkdir '{root}/operations'\n: >'{root}/gate.lock'\nprintf %s '{base64.b64encode(json.dumps(gate).encode()).decode()}' | base64 -d >'{root}/gate.json'\n")
    yield root
    assert root.startswith('/var/lib/docker/task-inputs/'+_SETTINGS.prefix+'t6-')
    shell(f"rm -rf -- '{root}'")


def durable(root,code,extra=""):
    encoded=base64.b64encode(json.dumps(SCOPE).encode()).decode()
    return long_ps(_functions("Invoke-ProcessCaptureWithInput","ConvertTo-ProcessArgumentString")+f"""
Import-Module '{MODULE}' -Force
$scope=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$root='{root}'
$capture={{param($Command)
 $r=Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList @('exec','-i','{ENGINE}','sh','-s') -StandardInput ($Command -replace "`r`n","`n")
 @{{Ok=($r.ExitCode -eq 0);Output=(($r.StdOut+"`n"+$r.StdErr).Trim())}}
}}
{extra}
{code}
""",timeout=120)


def new_operation():
    return """
$operation=New-ReleaseDeploymentOperation -Scope $scope -LockOperationId 'test-release-task' -ReleaseTag 'release-task' -LeaseToken 'lease-a' -PackageDigest ('1'*64) -ManifestDigest ('2'*64) -PlanDigest ('3'*64) -Before @{imageTag='old'} -Target @{imageTag='new'}
"""


def test_durable_attempt_identity_and_real_atomic_roundtrip(state_root):
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
$read=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
$read|ConvertTo-Json -Depth 30 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    state=json.loads(result.stdout)
    assert state["gate"]["state"]=="PREPARED"
    assert state["operation"]["attemptId"]==hashlib.sha256(b"test-release-task\nlease-a").hexdigest()
    assert state["operation"]["binding"]["leaseTokenDigest"]==hashlib.sha256(b"lease-a").hexdigest()
    assert state["operation"]["writeAttempted"] is False
    assert "lease-a" not in shell(f"cat '{state_root}/gate.json' '{state_root}/operations/'*.json")


@pytest.mark.parametrize("fault",["missing","empty","truncated","same-key","different-key","unknown-schema","wrong-environment","orphan"])
def test_gate_corruption_is_never_ready(state_root,fault):
    path=f"{state_root}/gate.json"
    original=json.loads(shell(f"cat '{path}'"))
    if fault=="missing":shell(f"rm '{path}'")
    elif fault=="orphan":shell(f"printf '{{}}' >'{state_root}/operations/orphan.json'")
    else:
        payload={"empty":"","truncated":"{","same-key":'{"schemaVersion":"release-deployment-gate/v1","schemaVersion":"release-deployment-gate/v1"}',
                 "different-key":'{"schemaVersion":"release-deployment-gate/v1","schemaVersion":"evil"}'}.get(fault)
        if payload is None:
            if fault=="unknown-schema":original["schemaVersion"]="future/v9"
            if fault=="wrong-environment":original["scope"]["environment"]="prod"
            payload=json.dumps(original)
        shell(f"printf %s '{base64.b64encode(payload.encode()).decode()}' | base64 -d >'{path}'")
    result=durable(state_root,"Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture")
    assert result.returncode!=0
    assert "RELEASE_DEPLOYMENT_EVIDENCE" in result.stderr,result.stderr


def prepare_state(root,with_receipt=False):
    code="""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
$operation=$state.operation;$operation.state='STARTED';$operation.writeAttempted=$true;$operation.phase='migrating'
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    if with_receipt:
        code+="""
$operation=$state.operation;$operation.state='FINALIZING'
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
$receipt=[pscustomobject]@{schemaVersion='release-deployment-receipt/v1';attemptId=$operation.attemptId;binding=$operation.binding;verification=@{};history=@{status='not-required'}}
$operation=$state.operation;$operation.receiptDigest=Write-ReleaseDeploymentReceipt -Root $root -State $state -Receipt $receipt -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    result=durable(root,code+"$state|ConvertTo-Json -Depth 40 -Compress")
    assert result.returncode==0,result.stdout+result.stderr
    return json.loads(result.stdout)


def put_remote(path,payload):
    shell(f"printf %s '{base64.b64encode(payload.encode()).decode()}' | base64 -d >'{path}'")


@pytest.mark.parametrize("field",["lockOperationId","releaseTag","leaseTokenDigest","packageDigest","manifestDigest","planDigest"])
def test_gate_and_operation_bindings_cannot_disagree(state_root,field):
    state=prepare_state(state_root)
    assert state["gate"]["binding"]==state["operation"]["binding"]
    state["operation"]["binding"][field]="f"*64 if field.endswith("Digest") else "other"
    payload=json.dumps(state["operation"])
    put_remote(f"{state_root}/operations/{state['gate']['attemptId']}.json",payload)
    state["gate"]["operationDigest"]=hashlib.sha256(payload.encode()).hexdigest()
    put_remote(f"{state_root}/gate.json",json.dumps(state["gate"]))
    result=durable(state_root,"Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture")
    assert result.returncode!=0


@pytest.mark.parametrize("fault",["false-only","zero-write-state","old-context"])
def test_persisted_write_attempt_is_monotonic_even_with_mutated_caller_context(state_root,fault):
    prepare_state(state_root)
    mutation="$operation.writeAttempted=$false"
    if fault=="zero-write-state":mutation+=";$operation.state='ZERO_WRITE_FAILED'"
    if fault=="old-context":mutation+=";$state.operation.writeAttempted=$false"
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
$operation=$state.operation
"""+mutation+"""
Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
""")
    assert result.returncode!=0 and "WRITE_FLAG_REGRESSION" in result.stderr
    actual=json.loads(shell(f"cat '{state_root}/operations/'*.json"))
    assert actual["writeAttempted"] is True and actual["state"]=="STARTED"


@pytest.mark.parametrize("kind",["operation","receipt"])
@pytest.mark.parametrize("fault",["missing","empty","truncated","same-key","different-key","unknown-schema"])
def test_operation_and_receipt_corruption_blocks_fresh_process(state_root,kind,fault):
    state=prepare_state(state_root,with_receipt=True)
    suffix='.json' if kind=='operation' else '.receipt.json'
    path=f"{state_root}/operations/{state['gate']['attemptId']}{suffix}"
    if fault=='missing':shell(f"rm '{path}'")
    else:
        raw=state[kind]
        values={"empty":"","truncated":"{","same-key":'{"x":1,"x":1}',"different-key":'{"x":1,"x":2}'}
        if fault=='unknown-schema':raw['schemaVersion']='future/v9'
        payload=values.get(fault,json.dumps(raw))
        put_remote(path,payload)
        state['gate']['operationDigest' if kind=='operation' else 'receiptDigest']=hashlib.sha256(payload.encode()).hexdigest()
        put_remote(f"{state_root}/gate.json",json.dumps(state['gate']))
    result=durable(state_root,"$s=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture;Assert-ReleaseDeploymentGate -State $s")
    assert result.returncode!=0


@pytest.mark.parametrize('part',['root','operations','lock'])
def test_preflight_rejects_writable_symlink_evidence_paths(state_root,part):
    path={'root':state_root,'operations':state_root+'/operations','lock':state_root+'/gate.lock'}[part]
    target=path+'-target'
    shell(f"mv '{path}' '{target}'; ln -s '{target}' '{path}'")
    try:
        result=durable(state_root,"Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture")
        assert result.returncode!=0,'writable symlink must not be a prepared evidence root'
    finally:
        if part=='root':shell(f"rm '{path}';mv '{target}' '{path}'")


@pytest.mark.parametrize('kind',['gate','operation','receipt'])
def test_evidence_top_level_array_cannot_impersonate_object(state_root,kind):
    state=prepare_state(state_root,with_receipt=True)
    path=state_root+'/gate.json' if kind=='gate' else f"{state_root}/operations/{state['gate']['attemptId']}"+('.json' if kind=='operation' else '.receipt.json')
    payload=json.dumps([state[kind]])
    put_remote(path,payload)
    if kind!='gate':
        state['gate']['operationDigest' if kind=='operation' else 'receiptDigest']=hashlib.sha256(payload.encode()).hexdigest()
        put_remote(state_root+'/gate.json',json.dumps(state['gate']))
    result=durable(state_root,"Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture")
    assert result.returncode!=0,'a single-element JSON array is not an evidence object'


@pytest.mark.parametrize('value',[False,0.0,'0'])
def test_ready_revision_requires_json_integer(state_root,value):
    gate=json.loads(shell(f"cat '{state_root}/gate.json'"));gate['revision']=value
    put_remote(state_root+'/gate.json',json.dumps(gate))
    result=durable(state_root,"Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture")
    assert result.returncode!=0,'coercible revision is invalid'


def test_save_does_not_recreate_disappeared_platform_lock(state_root):
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$normal=$capture
$broken={param($c) if($c.Contains('printf EVIDENCE_SAVED')){$null=& $normal "rm '$root/gate.lock'"};& $normal $c}
Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $broken -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
""")
    assert result.returncode!=0
    assert shell(f"if test -e '{state_root}/gate.lock'; then echo exists; else echo absent; fi").strip()=='absent'


@pytest.mark.parametrize('field',['lockApplied','historyVerified','cleanupVerified'])
@pytest.mark.parametrize('value',['True',1])
def test_completion_proof_requires_json_booleans(state_root,field,value):
    state=prepare_state(state_root,with_receipt=True)
    operation=state['operation'];operation['state']='COMMITTED'
    operation['completion']={'lockApplied':True,'historyVerified':True,'cleanupVerified':True}
    operation['completion'][field]=value
    payload=json.dumps(operation)
    put_remote(f"{state_root}/operations/{operation['attemptId']}.json",payload)
    state['gate']['state']='COMMITTED';state['gate']['operationDigest']=hashlib.sha256(payload.encode()).hexdigest()
    put_remote(state_root+'/gate.json',json.dumps(state['gate']))
    result=durable(state_root,'Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture')
    assert result.returncode!=0,'coercible success values must not authorize completion'


def test_production_fail_reaches_outer_catch_without_releasing_unknown_state():
    result=_ps(_functions()+"""
$fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Fail'},$true)
Invoke-Expression $fn.Extent.Text
$script:ReleaseOperationLockHeld=$true;$script:ReleaseOperationLockReleasing=$false;$script:releaseCalls=0
function Invoke-ReleaseOperationLockRelease {param($Status,$ErrorMessage) $script:releaseCalls++;throw 'release failed'}
function ConvertTo-ReleaseErrorMessage {param($Value) $Value}
try{Fail 'original'}catch{@{caught=$_.Exception.Message;held=$script:ReleaseOperationLockHeld;releaseCalls=$script:releaseCalls}|ConvertTo-Json -Compress}
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout.splitlines()[-1])
    assert value=={"caught":"original","held":True,"releaseCalls":0}


@pytest.mark.parametrize("database,accepted",[("ruoyi-vue-pro",True),("release-t6-safe",True),("bad;schema",False),("bad'quote",False),("../bad",False)])
def test_actual_recovery_paramblock_accepts_safe_hyphenated_database_only(database,accepted):
    result=_ps(f"""
$ErrorActionPreference='Stop';$t=$null;$e=$null
$ast=[Management.Automation.Language.Parser]::ParseFile('{RECOVERY}',[ref]$t,[ref]$e)
$bind=[scriptblock]::Create($ast.ParamBlock.Extent.Text+"`n'ACCEPTED'")
& $bind -ServerHost task -RemoteAppDir /task/runtime -DatabaseName '{database.replace("'","''")}' -ExpectedOperationId test-r -ExpectedReleaseTag r -ExpectedExecutorHost task -ExpectedExecutorPid 1 -ExpectedExecutorIdentity task -ExpectedLeaseToken token -ExecutorTerminalState TERMINATED -ConfirmText RECOVER-TEST-LOCK
""")
    assert (result.returncode==0)==accepted,result.stdout+result.stderr


def test_generated_lock_release_shell_rejects_success_text_followed_by_exit_17():
    result=_ps(_functions("Invoke-ReleaseOperationLockRelease","Get-ReleaseTargetMySqlCommand","ConvertTo-ShellSingleQuotedLiteral")+"""
$Environment='test';$ReleaseTag='task';$script:TargetMySqlDatabase='release_task'
$script:ReleaseOperationLegacyLockHeld=$false;$script:ReleaseOperationLockHeld=$true
$script:ReleaseOperationLeaseToken='token';$script:ReleaseOperationExecutorHost='host';$script:ReleaseOperationExecutorPid='123';$script:ReleaseOperationExecutorIdentity='task'
function ConvertTo-ReleaseErrorBase64 {param($Value) ''}
function Invoke-SshCommand {param($Command) $script:command=$Command}
Invoke-ReleaseOperationLockRelease -Status APPLIED
$script:command|ConvertTo-Json -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    shell=json.loads(result.stdout)
    runtime=mysql_runtime()
    probe="docker() { cat >/dev/null; printf 'LOCK_RELEASED\\n'; return 17; }\n"+shell
    execution=subprocess.run(["docker","exec","-i",runtime.container_id,"sh","-s"],input=probe.encode(),capture_output=True,timeout=30)
    assert execution.returncode!=0,"real generated shell hid docker exit 17"


def test_task_runtime_accepts_real_hyphenated_schema_and_rejects_injection():
    database="release-t6-"+uuid.uuid4().hex[:10]
    created=run_mysql(f"CREATE DATABASE `{database}`;")
    assert created.returncode==0,created.stderr
    try:
        value=run_mysql("SELECT DATABASE();",database)
        assert value.returncode==0 and value.stdout.strip()==database
        with pytest.raises(ValueError,match="unsafe"):
            run_mysql("SELECT 1;","bad;schema")
    finally:
        removed=run_mysql(f"DROP DATABASE `{database}`;")
        assert removed.returncode==0,removed.stderr


@pytest.fixture
def flow(tmp_path,classic_images,request):
    runtime=mysql_runtime();environment=getattr(request,'param','test')
    flock_directory=mysql_flock_directory(runtime)
    database='release-t6-'+uuid.uuid4().hex[:10]
    remote='/var/lib/docker/task-inputs/'+_SETTINGS.prefix+'t6-'+uuid.uuid4().hex
    config_root=tmp_path/'control';config_root.mkdir()
    package=tmp_path/'package';package.mkdir();(package/'docker-compose.yml').write_text('services: {}',encoding='utf-8')
    nas=tmp_path/'nas';nas.mkdir()
    created=run_mysql(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4;');assert created.returncode==0,created.stderr
    def drop_schema():
        removed=run_mysql(f'DROP DATABASE `{database}`;');assert removed.returncode==0,removed.stderr
    request.addfinalizer(drop_schema)
    scripts=application_backend_root()/'sql/mysql'
    for filename in ['20260613_infra_release_migration_state.sql','20260921_infra_release_operation_lock_lease_fencing.sql']:
        value=run_mysql((scripts/filename).read_text(encoding='utf-8'),database);assert value.returncode==0,value.stderr
    uuid_value=run_mysql('SELECT @@server_uuid;',database).stdout.strip()
    # This transport is an isolated container, not a server with machine-id.
    # Its immutable container identity is the explicit host fixture identity.
    machine=runtime.container_id[:32]
    scope=dict(SCOPE,environment=environment,database=database,serverUuid=uuid_value,machineId=machine)
    root=remote+'/.release-state/'+environment
    gate={'schemaVersion':'release-deployment-gate/v1','scope':scope,'revision':0,'state':'READY','attemptId':None,'operationDigest':None,'receiptDigest':None}
    def execute(command):
        result=subprocess.run(['docker','exec','-i',runtime.container_id,'sh','-s'],input=command.encode(),capture_output=True,timeout=30)
        assert result.returncode==0,result.stderr.decode();return result.stdout.decode()
    request.addfinalizer(lambda:execute(f"rm -rf -- '{remote}'"))
    request.addfinalizer(lambda:shell(f"rm -rf -- '{remote}'"))
    def put(path,data):
        encoded=base64.b64encode(data.encode()).decode();execute(f"printf %s '{encoded}' | base64 -d >'{path}'")
    execute(f"set -eu\nmkdir -p '{root}/operations' '{remote}/sql' '{remote}/release'\n: >'{root}/gate.lock'\n")
    put(root+'/gate.json',json.dumps(gate))
    put(remote+'/machine-id',machine)
    config_suffix='MYSQL_DATABASE='+database+'\nEDHR_S3_ENDPOINT=http://127.0.0.1:9000\nEDHR_S3_BUCKET=task\nEDHR_S3_REGION=us-east-1\nBACKEND_HOST_PORT=48080\nFRONTEND_HOST_PORT=8081\n'
    put(remote+'/.env','IMAGE_TAG=old\n'+config_suffix)
    put(remote+'/.env.next','IMAGE_TAG=release-t6\n'+config_suffix)
    put(remote+'/sql/001.sql',"CREATE TABLE t6_business(id INT PRIMARY KEY,value VARCHAR(32)); INSERT INTO t6_business VALUES(1,'first-committed');\n")
    put(remote+'/sql/002.sql',"INSERT INTO t6_business VALUES(2,'second-committed');\n")
    items=[{'migrationId':'t6-'+n,'file':'required-sql/'+n+'.sql','sha256':str(i)*64,'type':'schema','action':'APPLY'} for i,n in enumerate(['001','002'],1)]
    plan={'schemaVersion':'release-deploy-plan/v1','planKind':'deploy','publishScope':'app-release','status':'passed','planDigest':'3'*64,'items':items,
          'binding':{'hostIdentity':{'host':scope['host'],'machineId':machine},'databaseIdentity':{'name':database,'serverUuid':uuid_value}}}
    (config_root/'preflight-plan.json').write_text(json.dumps(plan),encoding='utf-8')
    # Actual compose in the separate task engine. These are sleep containers,
    # not a counterfeit backend/HTTP service. Health is a declared I/O contract.
    composition='services:\n'
    for component in ['backend','frontend']:
        composition+=f"  {component}:\n    image: {classic_images['refs'][component]}\n    container_name: intruoyi-{component}\n    command: [sleep, '600']\n    network_mode: none\n    labels:\n      codex.task: {_SETTINGS.task}\n"
    shell(f"mkdir -p '{remote}'")
    old_composition=composition
    for component in ['backend','frontend']:
        old_composition=old_composition.replace(classic_images['refs'][component],classic_images['wrong'])
    put_remote(remote+'/docker-compose.yml',old_composition)
    owned=[]
    def remove_containers():
        existing=classic_docker('ps','-a','--format','{{.Names}}').splitlines()
        for name in owned:
            if name not in existing:continue
            assert classic_docker('inspect','--format','{{index .Config.Labels "codex.task"}}',name)==_SETTINGS.task
            classic_docker('rm','-f',name)
    request.addfinalizer(remove_containers)
    owned.extend(['intruoyi-backend','intruoyi-frontend'])
    classic_docker('compose','-f',remote+'/docker-compose.yml','up','-d','--no-deps','--pull','never','backend','frontend')
    put_remote(remote+'/docker-compose.yml',composition)
    value={'runtime':runtime,'database':database,'remote':remote,'root':root,'scope':scope,'control':config_root,'package':package,'nas':nas,'images':classic_images,'put':put,'execute':execute,'plan':plan,'flock':flock_directory}
    yield value


def flow_script(flow,fault='',extra='',action='Invoke-ReleaseDeploymentExecution'):
    remote=flow['remote'];runtime=flow['runtime'];images=flow['images'];environment=flow['scope']['environment']
    verified=[{'name':name,'reference':images['refs'][name],'buildImageId':'sha256:'+'a'*64,'configDigest':images['good'],'platform':{'os':'linux','architecture':'amd64'}} for name in ['backend','frontend','scheduler-smoke']]
    data=base64.b64encode(json.dumps(verified).encode()).decode()
    return _functions()+f"""
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$OutputEncoding=[Text.UTF8Encoding]::new($false)
foreach($fn in @($ast.EndBlock.Statements|Where-Object{{$_ -is [Management.Automation.Language.FunctionDefinitionAst]}})){{Invoke-Expression $fn.Extent.Text}}
Import-Module '{MODULE}' -Force
$Mode='deploy-release';$Environment='{environment}';$ReleaseTag='release-t6';$packageDirectoryName='release-t6';$ServerHost='task-host';$PublishTargetName='task'
$RemoteAppDir='{remote}';$releaseDir='{flow['package'].as_posix()}';$deployControlLocalRoot='{flow['control'].as_posix()}';$releasePublishScope='app-release'
$remoteReleaseDir='{remote}/release';$remoteEnv='{remote}/.env';$remoteEnvNext='{remote}/.env.next';$remoteRequiredSqlDir='{remote}/sql'
$remoteImageTar='{remote}/image.tar';$remoteDbDump='{remote}/db.sql';$remoteResetDbSql='{remote}/reset.sql';$remotePostImportSql='{remote}/post.sql';$imageTar='unused-fixture'
$publishBackend=$true;$publishFrontend=$true;$publishWebsite=$false;$IncludeOnlyOffice=$false;$SkipMinioSync=$true;$requiresReleaseOperationLock=$true
$BackendPort=48080;$FrontendPort=8081;$OperatorName='task';$script:ReleaseErrorMessageMaxLength=2048
$script:TargetMySqlDatabase='{flow['database']}';$script:ReleaseOperationLockHeld=$false;$script:ReleaseOperationLegacyLockHeld=$false;$script:ReleaseOperationLockReleasing=$false;$script:ReleaseOperationLeaseToken=''
$script:ReleaseOperationExecutorHost=$env:COMPUTERNAME;$script:ReleaseOperationExecutorPid=[string]$PID;$script:ReleaseOperationExecutorIdentity=$env:USERNAME+'@'+$env:COMPUTERNAME
$script:DeploymentState=$null;$script:DeploymentOperation=$null;$script:DeploymentGateBeforeLock=$null
$script:ReleaseMigrationFailureErrors=@()
$script:ReleaseHistoryFailureErrors=@()
$parsed=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{data}'))|ConvertFrom-Json
$script:ReleaseVerifiedImageContent=@($parsed);$script:ReleaseRuntimeImages=@($parsed|ForEach-Object{{@{{name=$_.name;reference=$_.reference;id=$_.buildImageId}}}})
$script:ReleaseRuntimeVerification=[ordered]@{{loadedImages=@();images=@();website=$null;checks=@()}}
$releasePackageIntegrity=@{{packageDigest=('1'*64);manifestDigest=('2'*64)}}
$script:fault='{fault}';$script:faultTriggered=$false;$script:mutations=0
$script:io=@()
function Invoke-SshCapture {{param([string]$Command,[switch]$IgnoreExitCode)
 $script:io+=$Command
 if($Command -ceq 'cat /etc/machine-id'){{$Command="cat '{remote}/machine-id'"}}
 if($script:fault -eq 'observation' -and $script:faultTriggered -and $Command.Contains('docker container inspect')){{return @{{Ok=$false;Output='observer unavailable'}}}}
 if($script:fault -eq 'db-applied-before' -and $Command.Contains("SET status = 'APPLIED'") -and $Command.Contains('infra_release_operation_lock')){{return @{{Ok=$false;Output='database terminal write rejected'}}}}
 if($script:fault -eq 'release-failed' -and $Command.Contains("SET status = 'FAILED'") -and $Command.Contains('infra_release_operation_lock')){{return @{{Ok=$false;Output='lease release rejected'}}}}
 if($script:fault -eq 'failed-ledger' -and $Command.Contains('INSERT INTO infra_release_migration') -and $Command.Contains(", 'FAILED', NOW(), CASE WHEN 'FAILED'")){{return @{{Ok=$false;Output='FAILED ledger write rejected'}}}}
 $classic=$Command.Contains('docker container inspect') -or $Command.StartsWith('docker image inspect') -or $Command.StartsWith('docker info') -or $Command.Contains('docker compose up')
 if($classic){{$arguments=@('exec','-i','{ENGINE}','sh','-s');$payload=$Command}}
 else{{
  $arguments=@('exec','-i','{runtime.container_id}','sh','-s')
  $bridge='export PATH={flow['flock']}:$PATH' + "`n" + 'docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}' + "`n"
  $payload=$bridge+$Command
 }}
 $r=Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList $arguments -StandardInput ($payload -replace "`r`n","`n")
 if($script:fault -eq 'db-applied-ack' -and $Command.Contains("SET status = 'APPLIED'") -and $Command.Contains('infra_release_operation_lock')){{return @{{Ok=$false;Output='terminal acknowledgement lost'}}}}
 if($script:fault -eq 'env-switch' -and $Command.Contains("mv '{remote}/.env.next'")){{$script:faultTriggered=$true;return @{{Ok=$false;Output='env switch acknowledgement lost'}}}}
 @{{Ok=($r.ExitCode -eq 0);Output=(($r.StdOut+"`n"+$r.StdErr).Trim())}}
}}
function Invoke-SshCommand {{param([string]$Command) $r=Invoke-SshCapture -Command $Command;if(-not $r.Ok){{throw $r.Output}}}}
function Invoke-SshCommandWithInput {{param($Command,$StandardInput) Invoke-SshCommand ("cat <<'TASK_INPUT' | "+$Command+"`n"+$StandardInput+"`nTASK_INPUT")}}
# The planner, upload, schema-specific app checks and HTTP network are explicit
# transport boundaries. Durable functions, lease SQL, migrations, env switch,
# actual compose/images, NAS file writer and finalization execute real code.
function Write-ReleasePreflightPlan {{param([switch]$Verify)}}
function Assert-RemoteRuntimeDataOnDataDisk {{}}
function Prepare-RemoteReleaseTree {{$script:mutations++;Invoke-SshCommand "printf prepared >'{remote}/runtime-mutation'"}}
function Copy-DeployControlFilesToServer {{param($ComposeLocal)}}
function Assert-RemoteRuntimeEnvEdhrEndpoint {{}}
function Copy-SchedulerSmokeRunnerToServer {{}}
function Copy-LargeFileToServerInChunks {{param($LocalPath,$RemotePath)}}
function Copy-RequiredDatabaseSqlScriptsToServer {{}}
function Copy-ReleaseOpsRuntimePackage {{}}
function Get-RemoteComposeServices {{@('mysql','redis','backend','frontend')}}
function Assert-RemoteQuartzSchemaReady {{}}
function Assert-RemoteShowroomAwardSchemaReady {{}}
function Assert-RemoteFileStorageConfigRebound {{}}
function Assert-RemoteBackendContainerMinioReachable {{}}
function Assert-RemoteSchedulerSmokeRuntime {{}}
function Wait-RemoteHttpOk {{param($Url,$TimeoutSeconds) if($script:fault -eq 'health'){{$script:faultTriggered=$true;throw 'health HTTP503'}}}}
function Assert-RemoteBackendHealthStatus {{@{{status='UP'}}}}
function Wait-HttpOk {{param($Url,$TimeoutSeconds)}}
function Wait-HttpContentTypeOk {{param($Url,$ExpectedContentType,$TimeoutSeconds)}}
function Read-NasReleaseConfig {{@{{fixture=$true}}}}
function Connect-NasReleaseShare {{param($NasConfig) @{{Root='{flow['nas'].as_posix()}'}}}}
function Get-NasReleasePackagePath {{param($NasRoot,$PackageTag) $NasRoot}}
function Disconnect-NasReleaseShare {{param($MountInfo) if($script:fault -eq 'nas-disconnect'){{throw 'NAS disconnect rejected'}}}}
$actualSsh=(Get-Item function:Invoke-SshCommand).ScriptBlock
function Invoke-SshCommand {{param([string]$Command)
 if($Command.StartsWith('docker load ')){{return}}
 if($script:fault -in @('fail','throw','release-failed','observation') -and $Command.Contains('docker compose up')){{
  $script:faultTriggered=$true
  if($script:fault -eq 'fail'){{Fail 'original password=PRIVATE_SENTINEL'}}else{{throw 'original password=PRIVATE_SENTINEL'}}
 }}
 & $actualSsh -Command $Command
}}
{extra}
try{{{action};$outcome='passed'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=(Protect-ReleaseSensitiveText $outcome);mutations=$script:mutations;held=$script:ReleaseOperationLockHeld;state=$script:DeploymentState;operation=$script:DeploymentOperation}}|ConvertTo-Json -Depth 70 -Compress
"""


def run_flow(flow,fault='',extra='',action='Invoke-ReleaseDeploymentExecution'):
    result=long_ps(flow_script(flow,fault,extra,action),timeout=240)
    assert result.returncode==0,result.stdout+result.stderr
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.parametrize('flow',['test','prod','backup'],indirect=True)
def test_f00_actual_deployment_lifecycle_commits_after_real_sql_env_images_and_receipt(flow):
    value=run_flow(flow)
    assert value['outcome']=='passed',value
    assert value['state']['gate']['state']=='COMMITTED'
    assert value['operation']['before']['config']['values']['IMAGE_TAG']=='old'
    assert all(i['imageId']==flow['images']['wrong'] for i in value['operation']['before']['images'])
    assert all(i['actualImageId']==flow['images']['good'] for i in value['state']['receipt']['verification']['images'])
    rows=run_mysql('SELECT value FROM t6_business ORDER BY id;SELECT status FROM infra_release_operation_lock;',flow['database'])
    assert rows.returncode==0 and rows.stdout.split()==['first-committed','second-committed','APPLIED']
    assert not flow['control'].exists()
    # The local plan is intentionally recreated as caller input; its deletion
    # must not erase the remote durable authority.
    flow['control'].mkdir()
    (flow['control']/'preflight-plan.json').write_text(json.dumps(flow['plan']),encoding='utf-8')
    reread=run_flow(flow,action='Assert-ReleasePersistentDeploymentGate')
    assert reread['outcome']=='passed',reread


@pytest.mark.parametrize('fault',['fail','throw','release-failed','observation','env-switch','health','db-applied-before','db-applied-ack','container-switch','content-identity'])
def test_f05_f06_f09_actual_failures_keep_unknown_writes_blocked(flow,fault):
    extra=''
    if fault in ['container-switch','content-identity']:
        injected=("$Command=$Command.Replace(' backend frontend',' backend')" if fault=='container-switch' else f"$Command=\"docker tag {flow['images']['wrong']} {flow['images']['refs']['backend']}\"+\"`n\"+$Command")
        after="return @{Ok=$false;Output='partial container switch rejected'}" if fault=='container-switch' else 'return $result'
        extra=f"""
$normalCapture=(Get-Item function:Invoke-SshCapture).ScriptBlock
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 if($Command.Contains('docker compose up')){{{injected};$result=& $normalCapture -Command $Command -IgnoreExitCode;{after}}}
 & $normalCapture -Command $Command -IgnoreExitCode
}}
"""
    try:value=run_flow(flow,fault=fault,extra=extra)
    finally:
        if fault=='content-identity':classic_docker('tag',flow['images']['good'],flow['images']['refs']['backend'])
    assert value['outcome']!='passed',value
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    operation=json.loads(flow['execute'](f"cat '{flow['root']}/operations/{gate['attemptId']}.json'"))
    assert gate['state']=='RECOVERY_REQUIRED' and operation['writeAttempted'] is True
    assert operation['originalError']
    assert 'PRIVATE_SENTINEL' not in json.dumps(operation)
    if fault=='observation':
        assert operation['observationErrors']
        assert all(row['status']=='unknown' and row['imageId'] is None for row in operation['observation']['images'])
    if fault=='release-failed':
        assert value['held'] is True and operation['finalizationErrors']
    if fault=='env-switch':
        assert operation['before']['config']['values']['IMAGE_TAG']=='old'
        assert operation['observation']['config']['values']['IMAGE_TAG']=='release-t6'
    if fault=='db-applied-ack':
        assert run_mysql('SELECT status FROM infra_release_operation_lock;',flow['database']).stdout.strip()=='APPLIED'
    if fault=='container-switch':
        actual={row['name']:row['imageId'] for row in operation['observation']['images']}
        assert actual['backend']==flow['images']['good'] and actual['frontend']==flow['images']['wrong']
    if fault=='content-identity':assert 'RELEASE_RUNTIME_IMAGE_MISMATCH' in operation['originalError']
    if not flow['control'].exists():flow['control'].mkdir()
    (flow['control']/'preflight-plan.json').write_text(json.dumps(flow['plan']),encoding='utf-8')
    fresh=run_flow(flow,action='Assert-ReleasePersistentDeploymentGate')
    assert 'RECOVERY_REQUIRED' in fresh['outcome'],fresh
    assert fresh['mutations']==0


@pytest.mark.parametrize('fault',['sql','failed-ledger','sql-observation'])
def test_f04_actual_partial_mysql_preserves_original_error_and_ledger_observation(flow,fault):
    flow['put'](flow['remote']+'/sql/002.sql','SELECT * FROM t6_missing_table;\n')
    extra=''
    if fault=='sql-observation':
        extra="""
$actualObserver=(Get-Item function:Get-ReleaseTargetDatabaseSnapshot).ScriptBlock
function Get-ReleaseTargetDatabaseSnapshot {if($null -ne $script:DeploymentOperation -and $script:DeploymentOperation.state -eq 'RECOVERY_REQUIRED'){throw 'SQL observation rejected'};& $actualObserver}
"""
    value=run_flow(flow,fault=fault,extra=extra)
    assert 't6_missing_table' in value['outcome'],value
    rows=run_mysql('SELECT value FROM t6_business; SELECT status FROM infra_release_migration ORDER BY migration_id;',flow['database'])
    assert rows.returncode==0 and rows.stdout.split()[0]=='first-committed'
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    operation=json.loads(flow['execute'](f"cat '{flow['root']}/operations/{gate['attemptId']}.json'"))
    assert gate['state']=='RECOVERY_REQUIRED' and operation['writeAttempted'] is True
    assert 't6_missing_table' in operation['originalError']
    if fault=='failed-ledger':
        assert any('ledger' in error for error in operation['observationErrors'])
        assert rows.stdout.split()[-1]=='RUNNING'
    if fault=='sql-observation':
        assert operation['observation']['database']['status']=='unknown'
        assert any('observation' in error for error in operation['observationErrors'])


@pytest.mark.parametrize('fault',['local-cleanup','remote-cleanup','history-file','history-latest','nas-disconnect','receipt-temp','receipt-replace'])
@pytest.mark.parametrize('flow',['prod'],indirect=True)
def test_f08_every_finalization_failure_keeps_a_persistent_block(flow,fault):
    extra='';action='Invoke-ReleaseDeploymentExecution'
    if fault=='local-cleanup':
        locked=flow['control']/'locked.txt';locked.write_text('task owned',encoding='utf-8')
        extra=f"$locked=[IO.File]::Open('{locked.as_posix()}',[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)"
        action='try{Invoke-ReleaseDeploymentExecution}finally{$locked.Dispose()}'
    if fault=='remote-cleanup':flow['execute'](f"mkdir '{flow['remote']}/image.tar'")
    if fault=='history-latest':(flow['nas']/'prod-latest.json').mkdir()
    if fault=='history-file':
        extra=f"""
$actualPhase=(Get-Item function:Start-ReleaseDeploymentPhase).ScriptBlock
function Start-ReleaseDeploymentPhase {{param($Name,[switch]$Finalizing)
 & $actualPhase -Name $Name -Finalizing:$Finalizing
 if($Name -eq 'history-file'){{
  $path='{flow['nas'].as_posix()}/prod-deployments';[IO.Directory]::CreateDirectory($path)|Out-Null
  [IO.File]::WriteAllText(($path+'/'+$script:DeploymentOperation.attemptId+'.json'),'existing task collision',[Text.UTF8Encoding]::new($false))
 }}
}}
"""
    if fault.startswith('receipt-'):
        tool='base64' if fault=='receipt-temp' else 'mv'
        extra=f"""
$normalCapture=(Get-Item function:Invoke-SshCapture).ScriptBlock
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 if($Command.Contains('printf RECEIPT_SAVED')){{$Command='{tool}() {{ return 73; }}'+"`n"+$Command}}
 & $normalCapture -Command $Command -IgnoreExitCode
}}
"""
    value=run_flow(flow,fault=fault,extra=extra,action=action)
    assert value['outcome']!='passed',value
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    assert gate['state']=='RECOVERY_REQUIRED'
    operation=json.loads(flow['execute'](f"cat '{flow['root']}/operations/{gate['attemptId']}.json'"))
    assert operation['writeAttempted'] is True and operation['originalError']
    failed_phase={'local-cleanup':'cleanup-local','remote-cleanup':'cleanup-remote','history-file':'history-file','history-latest':'history-latest','nas-disconnect':'nas-disconnect','receipt-temp':'receipt','receipt-replace':'receipt'}[fault]
    assert any(p['name']==failed_phase and p['status']=='STARTED' for p in operation['phases']),operation
    if not flow['control'].exists():flow['control'].mkdir()
    (flow['control']/'preflight-plan.json').write_text(json.dumps(flow['plan']),encoding='utf-8')
    fresh=run_flow(flow,action='Assert-ReleasePersistentDeploymentGate')
    assert 'RECOVERY_REQUIRED' in fresh['outcome'] and fresh['mutations']==0,fresh


@pytest.mark.parametrize('fault',['temporary-create','atomic-replace'])
def test_f03_first_started_persistence_failure_prevents_runtime_writes(flow,fault):
    tool='base64' if fault=='temporary-create' else 'mv'
    extra=f"""
$normalCapture=(Get-Item function:Invoke-SshCapture).ScriptBlock
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 if($Command.Contains('printf EVIDENCE_SAVED') -and $script:DeploymentOperation.phase -eq 'preparing'){{$Command='{tool}() {{ return 73; }}'+"`n"+$Command}}
 & $normalCapture -Command $Command -IgnoreExitCode
}}
"""
    value=run_flow(flow,extra=extra)
    assert 'EVIDENCE_WRITE_FAILED' in value['outcome'],value
    assert value['mutations']==0
    assert flow['execute'](f"if test -e '{flow['remote']}/runtime-mutation';then echo wrote;else echo clean;fi").strip()=='clean'
    assert run_mysql('SELECT COUNT(*) FROM infra_release_migration;',flow['database']).stdout.strip()=='0'


def test_f07_outer_transport_nonzero_rejects_success_marker_and_preserves_held_lock():
    result=_ps(_functions('Invoke-ReleaseOperationLockRelease','Get-ReleaseTargetMySqlCommand','ConvertTo-ShellSingleQuotedLiteral')+"""
$Environment='test';$ReleaseTag='r';$script:TargetMySqlDatabase='release_task'
$script:ReleaseOperationLegacyLockHeld=$false;$script:ReleaseOperationLockHeld=$true
$script:ReleaseOperationLeaseToken='token';$script:ReleaseOperationExecutorHost='task';$script:ReleaseOperationExecutorPid='1';$script:ReleaseOperationExecutorIdentity='task'
function ConvertTo-ReleaseErrorBase64 {param($Value) ''}
function Invoke-SshCommand {param($Command) throw 'SSH exit 17 after LOCK_RELEASED'}
try{Invoke-ReleaseOperationLockRelease -Status APPLIED;$outcome='passed'}catch{$outcome=$_.Exception.Message}
@{outcome=$outcome;held=$script:ReleaseOperationLockHeld}|ConvertTo-Json -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout);assert value['held'] is True and 'exit 17' in value['outcome']


@pytest.fixture
def recovery_fixture(request):
    runtime=mysql_runtime();database='release-t6-recover-'+uuid.uuid4().hex[:8]
    flock_directory=mysql_flock_directory(runtime)
    setup_lock_database(database)
    def drop():
        r=run_mysql(f'DROP DATABASE `{database}`;');assert r.returncode==0,r.stderr
    request.addfinalizer(drop)
    remote='/tmp/'+_SETTINGS.prefix+'t6-recover-'+uuid.uuid4().hex
    root=remote+'/.release-state/test'
    def execute(command):
        r=subprocess.run(['docker','exec','-i',runtime.container_id,'bash','-s'],input=command.encode(),capture_output=True,timeout=30)
        assert r.returncode==0,r.stderr.decode();return r.stdout.decode()
    request.addfinalizer(lambda:execute(f"rm -rf -- '{remote}'"))
    lease='task-lease-'+uuid.uuid4().hex
    host=os.environ['COMPUTERNAME'];identity=os.environ['USERNAME']+'@'+host
    r=run_mysql(f"""INSERT INTO infra_release_operation_lock(target_environment,operation_id,release_tag,status,started_at,executor_host,executor_pid,executor_identity,lease_token,heartbeat_at,creator,create_time,updater,update_time) VALUES('test','test-release-task','release-task','RUNNING',NOW(),'{host}','999999','{identity}','{lease}',DATE_SUB(NOW(),INTERVAL 1 HOUR),'task',NOW(),'task',NOW());""",database)
    assert r.returncode==0,r.stderr
    scope=dict(SCOPE,database=database,serverUuid=run_mysql('SELECT @@server_uuid;',database).stdout.strip(),machineId=runtime.container_id[:32])
    gate={'schemaVersion':'release-deployment-gate/v1','scope':scope,'revision':0,'state':'READY','attemptId':None,'operationDigest':None,'receiptDigest':None}
    execute(f"mkdir -p '{root}/operations'; : >'{root}/gate.lock'; printf %s '{scope['machineId']}' >'{remote}/machine-id'")
    encoded=base64.b64encode(json.dumps(gate).encode()).decode()
    execute(f"printf %s '{encoded}' | base64 -d >'{root}/gate.json'")
    return dict(runtime=runtime,database=database,remote=remote,root=root,lease=lease,host=host,identity=identity,scope=scope,execute=execute,flock=flock_directory)


def recovery_script(fixture,prepare=None,extra='',invoke=True):
    scope_data=base64.b64encode(json.dumps(fixture['scope']).encode()).decode()
    remote=fixture['remote'];runtime=fixture['runtime']
    script=_functions('Invoke-ProcessCaptureWithInput','ConvertTo-ProcessArgumentString')+f"""
Import-Module '{MODULE}' -Force
$scope=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{scope_data}'))|ConvertFrom-Json
$root='{fixture['root']}'
$capture={{param($c)
 $bridge='export PATH={fixture['flock']}:$PATH'+"`n"+'docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}; export -f docker'+"`n"
 $r=Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList @('exec','-i','{runtime.container_id}','bash','-s') -StandardInput ($bridge+$c)
 @{{Ok=($r.ExitCode -eq 0);Output=($r.StdOut+$r.StdErr)}}
}}
function ssh {{
 $native=[string]$args[-1]
 $mapping='cat() {{ if [ "$#" = 1 ] && [ "$1" = /etc/machine-id ]; then /bin/cat "{remote}/machine-id"; else /bin/cat "$@"; fi; }}; export -f cat'+"`n"
 $r=& $capture ($mapping+$native)
 $global:LASTEXITCODE=if($r.Ok){{0}}else{{17}}
 $r.Output
}}
"""
    if prepare:
        script+=f"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
$operation=New-ReleaseDeploymentOperation -Scope $scope -LockOperationId 'test-release-task' -ReleaseTag 'release-task' -LeaseToken '{fixture['lease']}' -PackageDigest ('1'*64) -ManifestDigest ('2'*64) -PlanDigest ('3'*64) -Before @{{}} -Target @{{}}
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
"""
        if prepare!='PREPARED':
            script+=f"""
$operation=$state.operation;$operation.state='{prepare}';$operation.writeAttempted=$true
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    script+=extra
    if invoke:
        script+=f"""
& '{RECOVERY}' -ServerHost task-host -RemoteAppDir '{remote}' -DatabaseName '{fixture['database']}' -ExpectedOperationId test-release-task -ExpectedReleaseTag release-task -ExpectedExecutorHost '{fixture['host']}' -ExpectedExecutorPid 999999 -ExpectedExecutorIdentity '{fixture['identity']}' -ExpectedLeaseToken '{fixture['lease']}' -ExecutorTerminalState TERMINATED -ConfirmText RECOVER-TEST-LOCK
"""
    return script


def test_f11_actual_recovery_main_allows_only_proven_prepared_zero_write(recovery_fixture):
    f=recovery_fixture
    result=long_ps(recovery_script(f,prepare='PREPARED'),timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    assert run_mysql('SELECT status FROM infra_release_operation_lock;',f['database']).stdout.strip()=='FAILED'
    gate=json.loads(f['execute'](f"cat '{f['root']}/gate.json'"))
    assert gate['state']=='ZERO_WRITE_FAILED'
    operation=json.loads(f['execute'](f"cat '{f['root']}/operations/{gate['attemptId']}.json'"))
    assert operation['writeAttempted'] is False


@pytest.mark.parametrize('state',['STARTED','FINALIZING','RECOVERY_REQUIRED'])
@pytest.mark.parametrize('lock_status',['RUNNING','FAILED','APPLIED'])
def test_f11_uncertain_gate_blocks_actual_recovery_update_even_with_terminal_or_stale_lock(recovery_fixture,state,lock_status):
    f=recovery_fixture
    r=run_mysql(f"UPDATE infra_release_operation_lock SET status='{lock_status}';",f['database']);assert r.returncode==0
    result=long_ps(recovery_script(f,prepare=state),timeout=120)
    assert result.returncode!=0
    assert 'RECOVERY_REQUIRED' in result.stderr,result.stderr
    assert run_mysql('SELECT status FROM infra_release_operation_lock;',f['database']).stdout.strip()==lock_status


@pytest.mark.parametrize('fault',['missing','empty','duplicate','wrong-machine','wrong-database','recent-heartbeat','lost-lease'])
def test_f01_f02_f11_recovery_input_failure_never_updates_lease(recovery_fixture,fault):
    f=recovery_fixture
    if fault=='missing':f['execute'](f"rm '{f['root']}/gate.json'")
    if fault=='empty':f['execute'](f": >'{f['root']}/gate.json'")
    if fault=='duplicate':f['execute'](f"printf '%s' '{{\"scope\":1,\"scope\":1}}' >'{f['root']}/gate.json'")
    if fault=='wrong-machine':f['execute'](f"printf '%s' '{'f'*32}' >'{f['remote']}/machine-id'")
    if fault=='wrong-database':
        gate=json.loads(f['execute'](f"cat '{f['root']}/gate.json'"));gate['scope']['serverUuid']='99999999-9999-9999-9999-999999999999'
        encoded=base64.b64encode(json.dumps(gate).encode()).decode();f['execute'](f"printf %s '{encoded}'|base64 -d >'{f['root']}/gate.json'")
    if fault=='recent-heartbeat':assert run_mysql('UPDATE infra_release_operation_lock SET heartbeat_at=NOW();',f['database']).returncode==0
    if fault=='lost-lease':assert run_mysql("UPDATE infra_release_operation_lock SET lease_token='different-owner';",f['database']).returncode==0
    result=long_ps(recovery_script(f),timeout=120)
    assert result.returncode!=0
    assert run_mysql('SELECT status FROM infra_release_operation_lock;',f['database']).stdout.strip()=='RUNNING'


def test_interrupted_operation_replace_cannot_be_overwritten_by_stale_zero_write_writer(state_root):
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
$operation=$state.operation
$normal=$capture
$raced=$false
$race={param($c)
 if($c.Contains('printf EVIDENCE_SAVED') -and -not $script:raced){
  $script:raced=$true
  $other=($operation|ConvertTo-Json -Depth 60)|ConvertFrom-Json
  $other.writeAttempted=$true;$other.state='STARTED'
  $interrupted={param($command)
    if($command.Contains('printf EVIDENCE_SAVED')){
      $command='mv() { case "$*" in *gate.json*) return 74;; *) command mv "$@";; esac; }'+"`n"+$command
    }
    & $normal $command
  }
  try{Save-ReleaseDeploymentState -Root $root -State $state -Operation $other -Capture $interrupted -FenceCommand 'printf EVIDENCE_FENCE_OK'|Out-Null;throw 'interruption did not occur'}catch{
    if($_.Exception.Message -notlike '*EVIDENCE_WRITE_FAILED*'){throw}
  }
 }
 & $normal $c
}
Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $race -FenceCommand 'printf EVIDENCE_FENCE_OK'
""")
    assert result.returncode!=0,'a stale zero-write writer must not repair a partial true-write operation'
    persisted=json.loads(shell(f"cat '{state_root}/operations/'*.json"))
    assert persisted['writeAttempted'] is True and persisted['state']=='STARTED'


def test_lock_disappearing_after_precheck_is_not_recreated_during_atomic_save(state_root):
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$normal=$capture
$fault={param($c)
 if($c.Contains('printf EVIDENCE_SAVED')){$c=$c.Replace('exec 9',("rm '$root/gate.lock'"+"`nexec 9"))}
 & $normal $c
}
Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $fault -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
""")
    assert result.returncode!=0,'opening the preprovisioned lock must never recreate it'
    assert shell(f"if test -e '{state_root}/gate.lock';then echo recreated;else echo absent;fi").strip()=='absent'


@pytest.mark.parametrize('entry',['create-after-zero','create-after-committed','receipt'])
def test_each_locked_writer_rejects_partial_previous_operation_with_unchanged_gate(state_root,entry):
    # A real completed setup is necessary for the create-from-COMMITTED branch.
    if entry=='create-after-committed':
        prepare_state(state_root,with_receipt=True)
        setup="""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
$operation=$state.operation;$operation.state='COMMITTED';$operation.completion=@{lockApplied=$true;historyVerified=$true;cleanupVerified=$true}
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    else:
        setup="""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
$operation=$state.operation
"""+("$operation.state='ZERO_WRITE_FAILED'" if entry=='create-after-zero' else "$operation.state='FINALIZING';$operation.writeAttempted=$true")+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    action="""
$operation=New-ReleaseDeploymentOperation -Scope $scope -LockOperationId 'test-release-task' -ReleaseTag 'release-task' -LeaseToken 'lease-b' -PackageDigest ('1'*64) -ManifestDigest ('2'*64) -PlanDigest ('3'*64) -Before @{} -Target @{}
Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $fault -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
""" if entry!='receipt' else """
$receipt=[pscustomobject]@{schemaVersion='release-deployment-receipt/v1';attemptId=$state.operation.attemptId;binding=$state.operation.binding;verification=@{};history=@{status='not-required'}}
Write-ReleaseDeploymentReceipt -Root $root -State $state -Receipt $receipt -Capture $fault -FenceCommand 'printf EVIDENCE_FENCE_OK'
"""
    result=durable(state_root,setup+"""
$normal=$capture
$script:changed=$false
$fault={param($c)
 if(-not $script:changed -and ($c.Contains('printf EVIDENCE_SAVED') -or $c.Contains('printf RECEIPT_SAVED'))){
  $script:changed=$true
  $other=($state.operation|ConvertTo-Json -Depth 60)|ConvertFrom-Json
  $other.revision++
  $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($other|ConvertTo-Json -Depth 60 -Compress)))
  $path="$root/operations/$($state.gate.attemptId).json"
  $changed=& $normal "set -eu`nexec 9<'$root/gate.lock'`nflock -x 9`nprintf %s '$encoded' | base64 -d >'$path.task-interrupted'`nmv '$path.task-interrupted' '$path'"
  if(-not $changed.Ok){throw 'task I/O injection failed'}
 }
 & $normal $c
}
"""+action)
    assert result.returncode!=0,'every writer must CAS the previous operation inside the lock'


@pytest.mark.parametrize('kind',['gate','operation','receipt'])
def test_f01_remote_read_error_never_accepts_success_text(state_root,kind):
    state=prepare_state(state_root,with_receipt=True)
    suffix={'gate':'gate.json','operation':state['gate']['attemptId']+'.json','receipt':state['gate']['attemptId']+'.receipt.json'}[kind]
    result=durable(state_root,f"""
$normal=$capture
$fault={{param($c) if($c.Contains(\"base64 -w 0 '\") -and $c.Contains('{suffix}')){{return @{{Ok=$false;Output='SUCCESS'}}}};& $normal $c}}
Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $fault
""")
    assert result.returncode!=0 and 'EVIDENCE_READ_FAILED' in result.stderr


def test_operation_receipt_digest_must_equal_gate_receipt_digest(state_root):
    state=prepare_state(state_root,with_receipt=True)
    state['operation']['receiptDigest']='f'*64
    raw=json.dumps(state['operation'])
    put_remote(f"{state_root}/operations/{state['gate']['attemptId']}.json",raw)
    state['gate']['operationDigest']=hashlib.sha256(raw.encode()).hexdigest()
    put_remote(state_root+'/gate.json',json.dumps(state['gate']))
    result=durable(state_root,'Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture')
    assert result.returncode!=0,'operation receipt digest must not contradict gate receipt digest'


@pytest.mark.parametrize('endpoint',['https://user:PRIVATE_SENTINEL@storage/task','https://storage/task?key=PRIVATE_SENTINEL','https://storage/task#PRIVATE_SENTINEL'])
def test_runtime_observation_never_persists_credentials_embedded_in_endpoint(endpoint):
    result=_ps(_functions('Get-ReleaseDeploymentFailureObservation','Protect-ReleaseSensitiveText')+f"""
$script:ReleaseVerifiedImageContent=@()
function Get-ReleaseTargetDatabaseSnapshot {{@{{databaseIdentity=@{{}};migrationLedger=@()}}}}
function Get-RemoteRuntimeEnvMap {{@{{IMAGE_TAG='task';MYSQL_DATABASE='task';EDHR_S3_BUCKET='task';EDHR_S3_REGION='task';BACKEND_HOST_PORT='48080';FRONTEND_HOST_PORT='8081';EDHR_S3_ENDPOINT='{endpoint}'}}}}
Get-ReleaseDeploymentFailureObservation|ConvertTo-Json -Depth 20 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PRIVATE_SENTINEL' not in result.stdout
    value=json.loads(result.stdout)
    assert value['config']['status']=='unknown' and value['config']['values'] is None


@pytest.mark.parametrize('fields',["@{}","@{IMAGE_TAG='task'}"])
def test_missing_formal_runtime_configuration_is_an_unknown_observation(fields):
    result=_ps(_functions('Get-ReleaseDeploymentFailureObservation','Protect-ReleaseSensitiveText')+f"""
$script:ReleaseVerifiedImageContent=@()
function Get-ReleaseTargetDatabaseSnapshot {{@{{databaseIdentity=@{{}};migrationLedger=@()}}}}
function Get-RemoteRuntimeEnvMap {{{fields}}}
Get-ReleaseDeploymentFailureObservation|ConvertTo-Json -Depth 20 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value['config']['status']=='unknown' and value['config']['values'] is None


def test_prior_completion_observation_uses_old_receipt_components_before_new_package_preflight():
    result=_ps(_functions('Get-ReleaseDeploymentFailureObservation','Protect-ReleaseSensitiveText')+f"""
Import-Module '{MODULE}' -Force
$publishWebsite=$true;$IncludeOnlyOffice=$true
$script:ReleaseVerifiedImageContent=@(@{{name='backend'}},@{{name='frontend'}},@{{name='website'}},@{{name='onlyoffice'}})
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 if($Command.Contains('website') -or $Command.Contains('onlyoffice')){{throw 'new component not installed yet'}}
 @{{Ok=$true;Output=('sha256:'+('a'*64))}}
}}
function Get-ReleaseTargetDatabaseSnapshot {{@{{databaseIdentity=@{{}};migrationLedger=@();schemaEvidence=@{{}}}}}}
function Get-RemoteRuntimeEnvMap {{@{{IMAGE_TAG='old';MYSQL_DATABASE='task';EDHR_S3_BUCKET='task';EDHR_S3_REGION='task';BACKEND_HOST_PORT='48080';FRONTEND_HOST_PORT='8081';EDHR_S3_ENDPOINT='https://storage'}}}}
Get-ReleaseDeploymentFailureObservation -ComponentNames @('backend','frontend')|ConvertTo-Json -Depth 20 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value['errors']==[] and value['config']['status']=='observed',value
    assert [item['name'] for item in value['images']]==['backend','frontend']


@pytest.mark.parametrize('fault',['none','empty','missing-artifact','duplicate','invalid-hash','unsafe-path','boolean-size'])
def test_completion_website_receipt_is_explicit_and_bound_to_complete_current_artifact_set(state_root,fault):
    files={'dist/index.html':'index','nginx.conf':'server {}'}
    shell(f"mkdir -p '{state_root}/web/dist'")
    for path,content in files.items():put_remote(state_root+'/web/'+path,content)
    expected=[{'path':path,'bytes':len(content.encode()),'sha256':hashlib.sha256(content.encode()).hexdigest()} for path,content in files.items()]
    artifacts=[dict(expected[0],path='website/dist/index.html')]
    if fault=='empty':expected=[]
    if fault=='missing-artifact':expected=expected[1:]
    if fault=='duplicate':expected.append(expected[0])
    if fault=='invalid-hash':expected[0]['sha256']='bad'
    if fault=='unsafe-path':expected[0]['path']='../index.html'
    if fault=='boolean-size':expected[0]['bytes']=True
    encoded=base64.b64encode(json.dumps(expected).encode()).decode()
    artifact_data=base64.b64encode(json.dumps(artifacts).encode()).decode()
    result=durable(state_root,_functions('Assert-RemoteWebsitePayloadIdentity','ConvertTo-ShellSingleQuotedLiteral','ConvertTo-ReleaseFileSha256Hex')+f"""
$publishWebsite=$true;$websiteNginxLocal='MISSING-REMOVED-TEMPORARY-CONTROL';$remoteWebsiteDir='{state_root}/web'
$script:ReleaseRuntimeVerification=@{{website=$null}}
$parsedExpected=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$expected=@($parsedExpected)
$parsedArtifacts=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{artifact_data}'))|ConvertFrom-Json
$releasePackageIntegrity=@{{artifacts=@($parsedArtifacts)}}
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode) & $capture $Command}}
Assert-RemoteWebsitePayloadIdentity -ExpectedReceiptFiles $expected -BindCurrentPackage
$script:ReleaseRuntimeVerification.website|ConvertTo-Json -Depth 20 -Compress
""")
    if fault=='none':
        assert result.returncode==0,result.stdout+result.stderr
        assert json.loads(result.stdout)['status']=='passed'
    else:
        assert result.returncode!=0
        assert 'RELEASE_WEBSITE_RECEIPT_INVALID' in result.stderr,result.stderr


def test_same_release_new_lease_preserves_old_attempt_and_rejects_old_recovery_identity(state_root):
    result=durable(state_root,"""
$state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture $capture
"""+new_operation()+"""
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
$operation=$state.operation;$operation.state='ZERO_WRITE_FAILED'
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK'
$oldId=$operation.attemptId
$oldDigest=$state.gate.operationDigest
$operation=New-ReleaseDeploymentOperation -Scope $scope -LockOperationId 'test-release-task' -ReleaseTag 'release-task' -LeaseToken 'lease-b' -PackageDigest ('1'*64) -ManifestDigest ('2'*64) -PlanDigest ('3'*64) -Before @{} -Target @{}
$state=Save-ReleaseDeploymentState -Root $root -State $state -Operation $operation -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
try{Assert-ReleaseDeploymentGate -State $state -Recovery -ExpectedOperationId test-release-task -ExpectedReleaseTag release-task -ExpectedLeaseToken lease-a;$outcome='passed'}catch{$outcome=$_.Exception.Message}
@{oldId=$oldId;oldDigest=$oldDigest;state=$state;outcome=$outcome}|ConvertTo-Json -Depth 60 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value['oldId']!=value['state']['gate']['attemptId']
    old=shell(f"cat '{state_root}/operations/{value['oldId']}.json'")
    assert hashlib.sha256(old.encode()).hexdigest()==value['oldDigest']
    assert 'RECOVERY_REQUIRED' in value['outcome']


def test_f10_same_committed_package_rechecks_real_facts_without_planning_or_new_lease(flow):
    completed=run_flow(flow)
    assert completed['outcome']=='passed',completed
    original=flow['execute'](f"cat '{flow['root']}/gate.json'")
    lease=run_mysql('SELECT lease_token FROM infra_release_operation_lock;',flow['database']).stdout
    block_planner="function Write-ReleasePreflightPlan {throw 'PLANNER_REPLAY_NOT_ALLOWED'}"
    retry=run_flow(flow,extra=block_planner)
    assert retry['outcome']=='passed' and retry['mutations']==0,retry
    assert run_mysql('SELECT lease_token FROM infra_release_operation_lock;',flow['database']).stdout==lease
    assert flow['execute'](f"cat '{flow['root']}/gate.json'")==original
    changed_package=run_flow(flow,extra="$releasePackageIntegrity.packageDigest='f'*64;"+block_planner)
    assert 'COMPLETED_PACKAGE_MISMATCH' in changed_package['outcome'] and changed_package['mutations']==0,changed_package

    unhealthy=run_flow(flow,fault='health',extra=block_planner)
    assert unhealthy['outcome']!='passed' and 'PLANNER_REPLAY' not in unhealthy['outcome'],unhealthy
    for race in ['gate','lease']:
        command=(f"printf '\\n' >>'{flow['root']}/gate.json'" if race=='gate' else "")
        mutation=(f'Invoke-SshCommand "{command}"' if race=='gate' else "Invoke-SshCommand ((Get-ReleaseTargetMySqlCommand)+\" <<'TASK_LEASE_SQL'`nUPDATE infra_release_operation_lock SET lease_token='task-shifted';`nTASK_LEASE_SQL\")")
        extra=block_planner+f"""
$script:raced=$false
function Wait-RemoteHttpOk {{param($Url,$TimeoutSeconds) if(-not $script:raced){{$script:raced=$true;{mutation}}}}}
"""
        moved=run_flow(flow,extra=extra)
        assert moved['outcome']!='passed' and 'PLANNER_REPLAY' not in moved['outcome'],moved
        assert moved['mutations']==0
        if race=='gate':flow['put'](flow['root']+'/gate.json',original)
        else:
            assert run_mysql("UPDATE infra_release_operation_lock SET lease_token='"+lease.strip()+"';",flow['database']).returncode==0
    original_env=flow['execute'](f"cat '{flow['remote']}/.env'")
    flow['put'](flow['remote']+'/.env',original_env.replace('IMAGE_TAG=release-t6','IMAGE_TAG=wrong'))
    drift=run_flow(flow,extra=block_planner)
    assert drift['outcome']!='passed' and 'PLANNER_REPLAY' not in drift['outcome'],drift
    flow['put'](flow['remote']+'/.env',original_env)
    changed=run_mysql("UPDATE infra_release_migration SET status='FAILED' WHERE migration_id='t6-002';",flow['database']);assert changed.returncode==0
    drift=run_flow(flow,extra=block_planner)
    assert drift['outcome']!='passed' and 'PLANNER_REPLAY' not in drift['outcome'],drift
    restored=run_mysql("UPDATE infra_release_migration SET status='APPLIED' WHERE migration_id='t6-002';",flow['database']);assert restored.returncode==0
    following=run_flow(flow,extra="$ReleaseTag='next-release';$releasePackageIntegrity.packageDigest='5'*64;$publishWebsite=$true;$IncludeOnlyOffice=$true;$script:ReleaseVerifiedImageContent+=@(@{name='website'},@{name='onlyoffice'});function Write-ReleasePreflightPlan {throw 'NEW_PLAN_REACHED'}")
    assert following['outcome']=='NEW_PLAN_REACHED',following
    assert following['mutations']==0
    assert flow['execute'](f"cat '{flow['root']}/gate.json'")==original


def test_failed_zero_write_lock_release_cannot_persist_zero_write_failed(flow):
    extra="""
$normalCapture=(Get-Item function:Invoke-SshCapture).ScriptBlock
$script:rejectedFirst=$false
function Invoke-SshCapture {param($Command,[switch]$IgnoreExitCode)
 if(-not $script:rejectedFirst -and $Command.Contains('printf EVIDENCE_SAVED') -and $script:DeploymentOperation.phase -eq 'preparing'){
  $script:rejectedFirst=$true;return @{Ok=$false;Output='first STARTED write rejected'}
 }
 & $normalCapture -Command $Command -IgnoreExitCode
}
"""
    value=run_flow(flow,fault='release-failed',extra=extra)
    assert value['outcome']!='passed' and value['mutations']==0,value
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    assert gate['state']=='PREPARED','ZERO_WRITE_FAILED requires confirmed matching DB FAILED first'
    assert run_mysql('SELECT status FROM infra_release_operation_lock;',flow['database']).stdout.strip()=='RUNNING'


def test_f00_next_legitimate_package_executes_without_overwriting_previous_attempt(flow):
    first=run_flow(flow)
    assert first['outcome']=='passed',first
    old_id=first['state']['gate']['attemptId']
    old_path=f"{flow['root']}/operations/{old_id}.json"
    old_bytes=flow['execute'](f"cat '{old_path}'")
    flow['control'].mkdir()
    plan=json.loads(json.dumps(flow['plan']));plan['planDigest']='4'*64
    for item in plan['items']:item['action']='SKIP_ALREADY_APPLIED'
    (flow['control']/'preflight-plan.json').write_text(json.dumps(plan),encoding='utf-8')
    current_env=flow['execute'](f"cat '{flow['remote']}/.env'")
    flow['put'](flow['remote']+'/.env.next',current_env.replace('IMAGE_TAG=release-t6','IMAGE_TAG=release-t6-next'))
    second=run_flow(flow,extra="$ReleaseTag='release-t6-next';$packageDirectoryName='release-t6-next';$releasePackageIntegrity.packageDigest='5'*64;$releasePackageIntegrity.manifestDigest='6'*64")
    assert second['outcome']=='passed',second
    assert second['state']['gate']['state']=='COMMITTED'
    assert second['state']['gate']['attemptId']!=old_id
    assert flow['execute'](f"cat '{old_path}'")==old_bytes
    assert run_mysql('SELECT release_tag,status FROM infra_release_operation_lock;',flow['database']).stdout.strip()=='release-t6-next\tAPPLIED'
    assert run_mysql('SELECT value FROM t6_business ORDER BY id;',flow['database']).stdout.split()==['first-committed','second-committed']


def test_f02_gate_replaced_after_first_read_blocks_before_runtime_write(flow):
    extra="""
$enterImpl=(Get-Item function:Enter-ReleaseOperationLock).ScriptBlock
function Enter-ReleaseOperationLock {
 & $enterImpl
 $root="$RemoteAppDir/.release-state/$Environment"
 $capture={param($c) Invoke-SshCapture -Command $c -IgnoreExitCode}
 $state=Read-ReleaseDeploymentState -Root $root -Scope (Get-ReleaseDeploymentScope) -Capture $capture
 $other=New-ReleaseDeploymentOperation -Scope $state.gate.scope -LockOperationId 'test-other-release' -ReleaseTag 'other-release' -LeaseToken 'other-task-lease' -PackageDigest ('4'*64) -ManifestDigest ('5'*64) -PlanDigest ('6'*64) -Before @{} -Target @{}
 # Inject a competing filesystem fact at the I/O boundary, not a second
 # database lease: the production locked re-read must refuse any such drift.
 $null=Save-ReleaseDeploymentState -Root $root -State $state -Operation $other -Capture $capture -FenceCommand 'printf EVIDENCE_FENCE_OK' -Create
}
"""
    value=run_flow(flow,extra=extra)
    assert 'LOCKED_GATE_DRIFT' in value['outcome'] and value['mutations']==0,value
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    assert gate['binding']['releaseTag']=='other-release' and gate['state']=='PREPARED'
    assert gate['attemptId']==hashlib.sha256(b'test-other-release\nother-task-lease').hexdigest()
    assert run_mysql('SELECT COUNT(*) FROM infra_release_migration;',flow['database']).stdout.strip()=='0'


@pytest.mark.parametrize('fault',['none','environment','packageTag','attempt','read-and-disconnect'])
def test_completed_history_is_bound_to_operation_and_preserves_read_error(tmp_path,fault):
    history={'status':'verified','packageTag':'release-task','environment':'prod','historyDirectory':'prod-deployments','historyFile':'a'*64+'.json','latestFile':'prod-latest.json'}
    if fault=='environment':history.update(environment='backup',historyDirectory='backup-deployments',latestFile='backup-latest.json')
    if fault=='packageTag':history['packageTag']='other-release'
    if fault=='attempt':history['historyFile']='b'*64+'.json'
    record=json.dumps({'releaseTag':history['packageTag'],'environment':history['environment'],'attemptId':history['historyFile'][:-5]})
    history['sha256']=hashlib.sha256(record.encode()).hexdigest()
    package=tmp_path/history['packageTag'];directory=package/history['historyDirectory'];directory.mkdir(parents=True)
    (directory/history['historyFile']).write_text(record,encoding='utf-8')
    (package/history['latestFile']).write_text('wrong bytes' if fault=='read-and-disconnect' else record,encoding='utf-8')
    state={'gate':{'state':'COMMITTED'},'operation':{'attemptId':'a'*64,'binding':{'scope':dict(SCOPE,environment='prod'),'lockOperationId':'prod-release-task','releaseTag':'release-task','leaseTokenDigest':'b'*64}},'receipt':{'history':history}}
    data=base64.b64encode(json.dumps(state).encode()).decode()
    definitions=_functions('Assert-ReleaseDeploymentCompletionEvidence','Assert-NasReleaseDeploymentHistoryEvidence','Get-ReleaseDeploymentFenceCommand','Get-ReleaseTargetMySqlCommand','ConvertTo-ShellSingleQuotedLiteral','ConvertTo-ReleaseFileSha256Hex','Protect-ReleaseSensitiveText')
    result=_ps(definitions+f"""
$script:TargetMySqlDatabase='release_task';$Environment='prod';$script:DeploymentOperation=$null;$script:ReleaseHistoryFailureErrors=@()
$state=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{data}'))|ConvertFrom-Json
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode) @{{Ok=$true;Output='EVIDENCE_FENCE_OK'}}}}
function Read-NasReleaseConfig {{@{{task=$true}}}}
function Connect-NasReleaseShare {{param($NasConfig) @{{Root='{tmp_path.as_posix()}'}}}}
function Get-NasReleasePackagePath {{param($NasRoot,$PackageTag) Join-Path $NasRoot $PackageTag}}
function Disconnect-NasReleaseShare {{param($MountInfo) {"throw 'NAS disconnect password=PRIVATE_SENTINEL'" if fault=='read-and-disconnect' else ''}}}
try{{Assert-ReleaseDeploymentCompletionEvidence -State $state;$outcome='passed'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;secondary=@($script:ReleaseHistoryFailureErrors)}}|ConvertTo-Json -Depth 10 -Compress
""")
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout.splitlines()[-1])
    if fault=='none':assert value['outcome']=='passed',value
    elif fault=='read-and-disconnect':
        assert 'HISTORY_READBACK_MISMATCH' in value['outcome'],value
        assert value['secondary'] and 'NAS disconnect' in value['secondary'][0]
        assert 'PRIVATE_SENTINEL' not in result.stdout+result.stderr
    else:assert 'HISTORY_BINDING_MISMATCH' in value['outcome'],value


def test_real_release_logging_redacts_lease_without_altering_dispatched_sql():
    functions=_functions('Invoke-ReleaseOperationLockRelease','Invoke-SshCommand','Protect-ReleaseSensitiveText','ConvertTo-ReleaseErrorMessage','ConvertTo-ReleaseErrorBase64','Remove-SshNoise','Get-SshCommonOptions','New-SshArgumentList','Get-ReleaseTargetMySqlCommand','ConvertTo-ShellSingleQuotedLiteral')
    result=_ps(functions+"""
$info=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Info'},$true)
Invoke-Expression $info.Extent.Text
$Environment='test';$ReleaseTag='task';$ServerHost='task';$ServerUser='task';$script:TargetMySqlDatabase='release_task'
$script:ReleaseOperationExecutorHost='task';$script:ReleaseOperationExecutorPid='1';$script:ReleaseOperationExecutorIdentity='task'
$secret='cafedead'*4;$script:ReleaseOperationLeaseToken=$secret;$script:ReleaseOperationLockHeld=$true;$script:ReleaseOperationLegacyLockHeld=$false
function Invoke-ProcessCapture {param($FilePath,$ArgumentList) $script:sent=$ArgumentList[-1];@{ExitCode=0;StdOut='';StdErr=''}}
$streams=@(Invoke-ReleaseOperationLockRelease -Status APPLIED *>&1)|Out-String
@{leaked=$streams.Contains($secret);transportContainsLease=$script:sent.Contains($secret);released=(-not $script:ReleaseOperationLockHeld);hasRealInfo=$streams.Contains('[INFO]')}|ConvertTo-Json -Compress
""")
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout)
    assert value['hasRealInfo'] and value['transportContainsLease'] and value['released'],value
    assert value['leaked'] is False,'real Info/host/output/error streams must redact the lease'


def test_acquire_confirmation_loss_redacts_lease_in_exception_and_all_output_streams():
    result=_ps(_functions('Invoke-ReleaseOperationLockAcquire','Protect-ReleaseSensitiveText','Get-ReleaseTargetMySqlCommand','ConvertTo-ShellSingleQuotedLiteral')+"""
$Environment='test';$ReleaseTag='task';$script:TargetMySqlDatabase='release_task'
$script:ReleaseOperationExecutorHost='task';$script:ReleaseOperationExecutorPid='1';$script:ReleaseOperationExecutorIdentity='task';$script:ReleaseOperationLockHeld=$false
function Invoke-SshCapture {param($Command,[switch]$IgnoreExitCode) $script:secret=$script:ReleaseOperationLeaseToken;$script:sent=$Command;@{Ok=$false;Output=('LOCK_ACQUIRED:'+$script:secret);ExitCode=17}}
$streams=@(& {try{Invoke-ReleaseOperationLockAcquire;throw 'unexpected success'}catch{$script:rawError=$_.Exception.Message;$safe=Protect-ReleaseSensitiveText $script:rawError;Write-Host $safe;Write-Output $safe;Write-Error $safe -ErrorAction Continue}} *>&1)|Out-String
@{leaked=$streams.Contains($script:secret);exceptionLeaked=$script:rawError.Contains($script:secret);transportContainsLease=$script:sent.Contains($script:secret);held=$script:ReleaseOperationLockHeld}|ConvertTo-Json -Compress
""")
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout)
    assert value['transportContainsLease'] and value['held'] is False,value
    assert value['leaked'] is False and value['exceptionLeaked'] is False,'confirmation-loss diagnostics must not expose lease ownership credentials'


@pytest.mark.parametrize('point',['started','first-ddl','receipt','db-applied','committed'])
def test_f10_killed_real_executor_is_blocked_or_readonly_completed_in_new_process(flow,point,tmp_path):
    marker=tmp_path/'kill-ready.txt'
    base=f"""
function Stop-AtTaskBoundary {{[IO.File]::WriteAllText('{marker.as_posix()}','ready',[Text.UTF8Encoding]::new($false));while($true){{Start-Sleep -Seconds 1}}}}
"""
    if point=='started':
        base+="""
$phaseImpl=(Get-Item function:Start-ReleaseDeploymentPhase).ScriptBlock
function Start-ReleaseDeploymentPhase {param($Name,[switch]$Finalizing) & $phaseImpl -Name $Name -Finalizing:$Finalizing;if($Name -eq 'preparing'){Stop-AtTaskBoundary}}
"""
    elif point=='first-ddl':
        base+="""
$sqlImpl=(Get-Item function:Invoke-RequiredDatabaseSqlScriptWithState).ScriptBlock
function Invoke-RequiredDatabaseSqlScriptWithState {param($Item,$RemoteSqlPath,$SessionPreamble) & $sqlImpl -Item $Item -RemoteSqlPath $RemoteSqlPath -SessionPreamble $SessionPreamble;Stop-AtTaskBoundary}
"""
    elif point=='receipt':
        base+="""
$phaseImpl=(Get-Item function:Complete-ReleaseDeploymentPhase).ScriptBlock
function Complete-ReleaseDeploymentPhase {param([string[]]$LockStatuses=@('RUNNING')) & $phaseImpl -LockStatuses $LockStatuses;if($script:DeploymentOperation.phase -eq 'receipt'){Stop-AtTaskBoundary}}
"""
    elif point=='db-applied':
        base+="""
$releaseImpl=(Get-Item function:Invoke-ReleaseOperationLockRelease).ScriptBlock
function Invoke-ReleaseOperationLockRelease {param($Status,$ErrorMessage) & $releaseImpl -Status $Status -ErrorMessage $ErrorMessage;if($Status -eq 'APPLIED'){Stop-AtTaskBoundary}}
"""
    else:
        base+="""
$saveImpl=(Get-Item function:Save-CurrentReleaseDeploymentEvidence).ScriptBlock
function Save-CurrentReleaseDeploymentEvidence {param([string[]]$LockStatuses=@('RUNNING')) & $saveImpl -LockStatuses $LockStatuses;if($script:DeploymentOperation.state -eq 'COMMITTED'){Stop-AtTaskBoundary}}
"""
    script=tmp_path/'kill-executor.ps1';script.write_text(flow_script(flow,extra=base),encoding='utf-8-sig')
    with (tmp_path/'executor.out').open('wb') as stdout,(tmp_path/'executor.err').open('wb') as stderr:
        process=subprocess.Popen(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script)],stdout=stdout,stderr=stderr)
        try:
            deadline=time.monotonic()+300
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.25)
            assert marker.exists(),(tmp_path/'executor.err').read_text(encoding='utf-8',errors='replace')
        finally:
            if process.poll() is None:process.kill()
            process.wait(timeout=20)
    if point=='started':
        assert run_mysql("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='t6_business';",flow['database']).stdout.strip()=='0'
    elif point=='first-ddl':
        assert run_mysql('SELECT value FROM t6_business ORDER BY id;SELECT status FROM infra_release_migration;',flow['database']).stdout.split()==['first-committed','APPLIED']
    else:
        assert run_mysql('SELECT value FROM t6_business ORDER BY id;',flow['database']).stdout.split()==['first-committed','second-committed']
    # Remove only this process's disposable controls; the authority is remote.
    import shutil
    if flow['control'].exists():shutil.rmtree(flow['control'])
    flow['control'].mkdir()
    new_plan=json.loads(json.dumps(flow['plan']))
    if point=='committed':
        new_plan['planDigest']='4'*64
        for item in new_plan['items']:item['action']='SKIP_ALREADY_APPLIED'
    (flow['control']/'preflight-plan.json').write_text(json.dumps(new_plan),encoding='utf-8')
    run_mysql("UPDATE infra_release_operation_lock SET heartbeat_at=DATE_SUB(NOW(),INTERVAL 1 HOUR);",flow['database'])
    planner="function Write-ReleasePreflightPlan {throw 'PLANNER_REPLAY_NOT_ALLOWED'}" if point=='committed' else ''
    value=run_flow(flow,extra=planner)
    if point=='committed':
        assert value['outcome']=='passed',value
        assert value['mutations']==0
    else:
        assert 'RECOVERY_REQUIRED' in value['outcome'],value
        assert value['mutations']==0
    gate=json.loads(flow['execute'](f"cat '{flow['root']}/gate.json'"))
    assert gate['state']==('COMMITTED' if point=='committed' else ('STARTED' if point in ['started','first-ddl'] else 'FINALIZING'))
    if point!='committed':
        lease=run_mysql('SELECT lease_token FROM infra_release_operation_lock;',flow['database']).stdout.strip()
        recovery=dict(flow,lease=lease,host=os.environ['COMPUTERNAME'],identity=os.environ['USERNAME']+'@'+os.environ['COMPUTERNAME'])
        entry=recovery_script(recovery).replace('-ExpectedOperationId test-release-task -ExpectedReleaseTag release-task','-ExpectedOperationId test-release-t6 -ExpectedReleaseTag release-t6').replace('-ExpectedExecutorPid 999999',f'-ExpectedExecutorPid {process.pid}')
        result=long_ps(entry,timeout=120)
        assert result.returncode!=0 and 'RECOVERY_REQUIRED' in result.stderr,result.stdout+result.stderr
        assert run_mysql('SELECT lease_token FROM infra_release_operation_lock;',flow['database']).stdout.strip()==lease
