from __future__ import annotations

import base64
import io
import tarfile
import json
import os
import shlex
import hashlib
import copy
import subprocess
import uuid
from pathlib import Path

import pytest

from test_release_full_package_contract import ROOT, SCRIPT, GOVERNANCE, _functions as _production_functions, _ps, write_complete_package, rebind_package, _tar_bytes
from release_test_runtime import application_backend_root, mysql_runtime, run_mysql


def _functions(*names):
    # Execute the entry point's real UTF-8 bootstrap before exercising extracted
    # functions; Windows PowerShell otherwise creates BOM-bearing stdin writers.
    return _production_functions(*names) + """
$releaseConsoleEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $releaseConsoleEncoding
[Console]::OutputEncoding = $releaseConsoleEncoding
$OutputEncoding = $releaseConsoleEncoding
"""


def test_existing_data_mount_preflight_dispatches_no_preparation_writes():
    result = _ps(_functions("Assert-RemoteRuntimeDataOnDataDisk") + """
$RemoteReleaseRoot='/task/releases'; $RemoteDataRoot='/task/data'; $RemoteAppDir='/task/runtime'
$RemoteDataDiskMount='/task'; $RemoteDataDiskDevice='/dev/task'
$script:commands=@()
function Invoke-SshCommand { param([string]$Command) $script:commands += $Command }
Assert-RemoteRuntimeDataOnDataDisk
$script:commands | ConvertTo-Json -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    commands = json.loads(result.stdout)
    if isinstance(commands, str):
        commands = [commands]
    for command in commands:
        assert "mkdir" not in command
        assert "mount --bind" not in command
        assert ">> /etc/fstab" not in command


def test_legacy_control_schema_is_rejected_without_lock_acquire_or_upgrade():
    result = _ps(_functions("Enter-ReleaseOperationLock") + """
$script:calls=@()
function Get-ReleaseOperationLockSchemaState { 'LOCK_SCHEMA_LEGACY' }
function Invoke-ReleaseOperationLegacyLockAcquire { $script:calls += 'legacy-acquire' }
function Invoke-ReleaseOperationLockLeaseUpgrade { $script:calls += 'ddl-upgrade' }
function Assert-ReleaseOperationLockOwnership { $script:calls += 'ownership-write' }
try { Enter-ReleaseOperationLock; $outcome='accepted' } catch { $outcome=$_.Exception.Message }
@{outcome=$outcome;calls=$script:calls} | ConvertTo-Json -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(result.stdout)
    assert value["outcome"].startswith("RELEASE_OPERATION_LOCK_SCHEMA_NOT_READY")
    assert value["calls"] == []


def test_skip_actions_never_rewrite_migration_history():
    result = _ps(_functions("Invoke-RequiredDatabaseSqlScripts", "Sort-RequiredDatabaseSqlApplyItems") + """
$script:writes=@(); $releasePublishScope='app-release'; $Environment='test'
function Read-ReleasePreflightPlan {
 @{ items=@(
  @{migrationId='old-a';action='SKIP_ALREADY_APPLIED'},
  @{migrationId='old-b';action='SKIP_ENV_NOT_ALLOWED'},
  @{migrationId='old-c';action='SKIP_SCOPE_EXCLUDED'},
  @{migrationId='old-d';action='SKIP_IMMUTABLE'}
 ) }
}
function Invoke-ReleaseMigrationStateBatchUpdate { param($Items,$Status) if (@($Items).Count) { $script:writes += $Status } }
Invoke-RequiredDatabaseSqlScripts
ConvertTo-Json -InputObject @($script:writes) -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == []


def test_unbound_plan_cannot_authorize_deployment(tmp_path):
    (tmp_path / "preflight-plan.json").write_text(json.dumps({
        "publishScope": "app-release", "status": "passed", "items": [],
    }), encoding="utf-8")
    result = _ps(_functions("Read-ReleasePreflightPlan") + f"""
$deployControlLocalRoot='{tmp_path}'; $releasePublishScope='app-release'
Read-ReleasePreflightPlan
""")
    assert result.returncode != 0
    assert "TARGET_BOUND_PLAN_REQUIRED" in result.stdout + result.stderr


@pytest.mark.parametrize("website", [False, True])
@pytest.mark.parametrize("only_office", [False, True])
def test_actual_application_start_commands_never_pull_or_start_platform_dependencies(website, only_office):
    result = _ps(_functions() + f"""
$publishBackend=$true; $publishFrontend=$true; $publishWebsite=${str(website).lower()}; $IncludeOnlyOffice=${str(only_office).lower()}
$RemoteAppDir='/task/runtime'; $PublishTargetName='task'
$script:commands=@()
function Assert-ReleaseOperationWriteFence {{}}
function Complete-ReleaseDeploymentPhase {{}}
function Start-ReleaseDeploymentPhase {{param($Name,[switch]$Finalizing)}}
function Assert-RemoteActualApplicationImages {{}}
function Assert-RemoteWebsitePayloadIdentity {{}}
function Assert-ReleaseSelectedImagesLoaded {{}}
function Invoke-SshCommand {{ param([string]$Command) $script:commands += $Command }}
$source=[IO.File]::ReadAllText('{SCRIPT}')
$start=$source.IndexOf('    $runtimeServices = @()')
$finish=$source.IndexOf("    Info 'Waiting for remote HTTP readiness'",$start)
if($start -lt 0 -or $finish -lt $start) {{ throw 'actual application start block missing' }}
Invoke-Expression $source.Substring($start,$finish-$start)
ConvertTo-Json -InputObject @($script:commands) -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    commands = json.loads(result.stdout)
    assert len(commands) == (2 if website else 1)
    for command in commands:
        assert "--no-deps" in command
        assert "--pull never" in command
        assert " mysql" not in command and " redis" not in command


def test_main_deploy_observes_readonly_plan_lock_fresh_verify_before_first_runtime_write():
    result = _ps(_functions() + f"""
$Mode='deploy-release'; $publishBackend=$true; $publishFrontend=$true; $publishWebsite=$false
$requiresReleaseOperationLock=$true; $script:ReleaseOperationLockHeld=$false; $script:calls=@()
function Write-ReleasePreflightPlan {{ param([switch]$Verify) if($Verify){{$script:calls+='verify'}}else{{$script:calls+='plan'}} }}
function Enter-ReleaseOperationLock {{ $script:calls+='lock' }}
function Test-ReleaseDeploymentAlreadyCommitted {{ $script:calls+='completion-read';$false }}
function Assert-ReleasePersistentDeploymentGate {{param([switch]$Verify) if($Verify){{$script:calls+='locked-gate'}}else{{$script:calls+='gate'}}}}
function Initialize-ReleaseDeploymentEvidence {{ $script:calls+='prepared-evidence' }}
function Start-ReleaseDeploymentPhase {{param($Name,[switch]$Finalizing) $script:calls+='started-evidence'}}
function Assert-ReleaseOperationWriteFence {{}}
function Assert-RemoteRuntimeDataOnDataDisk {{ $script:calls+='platform-precheck' }}
function Prepare-RemoteReleaseTree {{ $script:calls+='FIRST_RUNTIME_WRITE'; throw 'TASK_TEST_STOP_AT_WRITE' }}
$runtime=$ast.Find({{param($n) $n -is [Management.Automation.Language.TryStatementAst] -and $n.Body.Extent.Text.Contains('Prepare-RemoteReleaseTree')}},$true)
if($null -eq $runtime){{throw 'actual main runtime block missing'}}
try{{& ([scriptblock]::Create($runtime.Body.Extent.Text.Trim().Substring(1,$runtime.Body.Extent.Text.Trim().Length-2)))}}catch{{}}
ConvertTo-Json -InputObject @($script:calls) -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = json.loads(result.stdout)
    assert calls.index("plan") < calls.index("lock") < calls.index("verify") < calls.index("FIRST_RUNTIME_WRITE")
    assert calls.index('completion-read') < calls.index('plan') < calls.index('gate') < calls.index('lock')
    assert calls.index('verify') < calls.index('locked-gate') < calls.index('prepared-evidence') < calls.index('started-evidence') < calls.index('FIRST_RUNTIME_WRITE')


def test_deploy_credential_branch_never_reads_local_business_mysql():
    result = _ps(_functions() + f"""
$Mode='deploy-release'; $publishBackend=$true; $LocalMySqlContainer='UNRELATED-SHARED'
$existingRemoteEnv=@{{MYSQL_ROOT_PASSWORD='task-target-password'}}; $script:calls=@()
function Get-LocalContainerEnvValue {{ param($ContainerName,$Key) $script:calls+='LOCAL_DATABASE_READ'; return 'wrong-local-password' }}
$source=[IO.File]::ReadAllText('{SCRIPT}'); $start=$source.IndexOf("`$mySqlRootPassword = ''",$source.IndexOf("Info 'eDHR protected storage settings validated")); $finish=$source.IndexOf("`$localMinioAccessKey = ''",$start)
Invoke-Expression $source.Substring($start,$finish-$start)
ConvertTo-Json -InputObject @($script:calls) -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == []


def test_main_target_env_render_preserves_existing_values_and_only_changes_managed_version(tmp_path):
    result = _ps(_functions("Write-Utf8LfNoBomFile", "Get-ReleasePlatformIdentityEnvironmentLines") + f"""
Import-Module '{GOVERNANCE}' -Force
$Mode='deploy-release';$Component='intruoyi';$deployControlLocalRoot='{tmp_path}';$packageDirectoryName='release-new'
$existingRemoteEnv=@{{IMAGE_TAG='release-old';MYSQL_DATABASE='task';MYSQL_ROOT_PASSWORD='task target $ '' password';EDHR_S3_ENDPOINT='http://existing-storage:9000';CUSTOM_EXISTING_FLAG='keep-me';DCC_PROJECT_CODE_CODEX_CLI_SHA256='{'a'*64}'}}
$remoteEnvContent="IMAGE_TAG=release-new`nMYSQL_DATABASE=wrong-source`nMYSQL_ROOT_PASSWORD=wrong-source`nEDHR_S3_ENDPOINT=http://wrong-source:9000";$schedulerSmokeNodeImage='sha256:{'b'*64}'
$source=[IO.File]::ReadAllText('{SCRIPT}');$start=$source.IndexOf('$remoteEnvLocal =');$finish=$source.IndexOf('$requiresReleaseOperationLock =',$start)
Invoke-Expression $source.Substring($start,$finish-$start)
""")
    assert result.returncode == 0, result.stdout + result.stderr
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "CUSTOM_EXISTING_FLAG=keep-me" in env
    assert "EDHR_S3_ENDPOINT=http://existing-storage:9000" in env
    assert "MYSQL_ROOT_PASSWORD=task target $ ' password" in env
    assert "IMAGE_TAG=release-new" in env
    assert "wrong-source" not in env


def test_main_deploy_has_no_unplanned_platform_database_or_storage_mutation():
    result = _ps(_functions() + f"""
$runtime=$ast.Find({{param($n) $n -is [Management.Automation.Language.TryStatementAst] -and $n.Body.Extent.Text.Contains('Prepare-RemoteReleaseTree')}},$true)
$commands=$runtime.Body.FindAll({{param($n) $n -is [Management.Automation.Language.CommandAst]}},$true)
@($commands | ForEach-Object {{$_.Extent.Text}}) | ConvertTo-Json -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    commands = json.loads(result.stdout)
    forbidden = ("Ensure-ReleaseMigrationStateSchema", "Write-TargetBoundPostImportSql", "post-import.sql",
                 "docker compose up -d mysql redis", "remotePostImportSql", "remoteResetDbSql",
                 "remoteDbDump", "remoteMinioAccessKey", "rm -rf '$RemoteAppDir/data/mysql'")
    assert not [c for c in commands if any(token in c for token in forbidden)]
    assert len([c for c in commands if c.startswith("Write-ReleasePreflightPlan")]) == 2


def test_deploy_package_resolution_invokes_fixed_maintenance_source_gate(tmp_path):
    result = _ps(_functions("Get-ReleaseTargetImageIdentities") + f"""
$Mode='deploy-release';$ReleaseTag='release-fixture';$Environment='test';$componentExplicit=$false
$script:calls=@()
function Copy-ReleasePackageFromNas {{param($PackageTag)
 $images=@('backend','frontend','scheduler-smoke'|ForEach-Object{{[pscustomobject]@{{name=$_;reference="task-${{_}}:release";id='sha256:{'a'*64}'}}}})
 $verified=@($images|ForEach-Object{{[pscustomobject]@{{name=$_.name;reference=$_.reference;buildImageId=$_.id;configDigest=$_.id;platform=@{{os='linux';architecture='amd64'}}}}}})
 return @{{PublishScope='app-release';runtimeImages=$images;verifiedImageContent=$verified}}
}}
function Assert-ReleaseExecutorSourceBinding {{param($PackageIntegrity) $script:calls+='source-binding'}}
function Resolve-DeployReleasePackageComponent {{param($ComponentExplicit) 'intruoyi'}}
function Assert-ReleasePackageDeploymentScope {{param($TargetEnvironment,$PublishScope)}}
function Assert-ProdDryRunEvidence {{}}
function Resolve-DeployReleasePackageOnlyOfficeIncluded {{param($IncludeOnlyOfficeExplicit) $false}}
function Assert-DeployReleasePackageArtifactsForScope {{param($PublishScope)}}
function Get-ReleasePackageDatabaseSqlScripts {{@()}}
function Assert-RequiredDatabaseSqlScriptsInRelease {{}}
function Apply-ReleaseRuntimeEnvPackage {{param($TargetEnvironment) $script:calls+='package-env-read'}}
function Require-Command {{param($Name)}}
function Import-ExistingRemoteRuntimeEnvSettings {{$script:calls+='target-env-read'}}
$smartReleaseReportOnlyEnabled=$false
$entry=$ast.EndBlock.Statements | Where-Object {{$_.Extent.Text.StartsWith("if (`$Mode -eq 'deploy-release') {{") -and $_.Extent.Text.Contains('Copy-ReleasePackageFromNas')}}
Invoke-Expression $entry.Extent.Text
ConvertTo-Json -InputObject @($script:calls) -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    calls=json.loads(result.stdout)
    assert calls[0] == "source-binding"
    assert "package-env-read" not in calls


def _real_database_snapshot(database: str):
    runtime = mysql_runtime()
    result = _ps(_functions("Get-ReleaseTargetDatabaseSnapshot", "Get-ReleaseTargetSchemaCollectionSql", "Get-ReleaseTargetMySqlCommand") + f"""
$Environment='test';$script:TargetMySqlDatabase='{database}'
function Invoke-SshCapture {{
 param([string]$Command,[switch]$IgnoreExitCode)
 $lines=@($Command -split "`r?`n")
 $first=[Array]::FindIndex($lines,[Predicate[string]]{{param($line) $line.StartsWith("cat <<'RELEASE_SQL'")}})
 $last=[Array]::FindLastIndex($lines,[Predicate[string]]{{param($line) $line -eq 'RELEASE_SQL'}})
 if($first -lt 0 -or $last -le $first){{throw 'production collection SQL carrier missing'}}
 $sql=$lines[($first+1)..($last-1)] -join "`n"
 $output=@($sql | & docker exec -i '{runtime.container_id}' sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot --default-character-set=utf8mb4 --binary-mode --batch --raw --skip-column-names "$1"' sh '{database}' 2>&1)
 $code=$LASTEXITCODE
 return @{{Ok=($code -eq 0);Output=($output -join "`n");ExitCode=$code}}
}}
Get-ReleaseTargetDatabaseSnapshot | ConvertTo-Json -Depth 30 -Compress
""")
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_actual_mysql_snapshot_retains_all_ledger_statuses_and_stable_schema():
    database="release_t4_"+uuid.uuid4().hex[:12]
    def sql(statement):
        result=run_mysql(statement,database)
        assert result.returncode==0,result.stderr
        return result.stdout
    created=run_mysql(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4;")
    assert created.returncode==0,created.stderr
    try:
        sql((application_backend_root()/"sql/mysql/20260613_infra_release_migration_state.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE historical_business(id BIGINT AUTO_INCREMENT PRIMARY KEY, value VARCHAR(30)); INSERT INTO historical_business(value) VALUES ('preserved');")
        statuses=["APPLIED","FAILED","RUNNING","SKIPPED_ALREADY_APPLIED","UNKNOWN"]
        for i,status in enumerate(statuses):
            sql(f"INSERT INTO infra_release_migration(release_tag,migration_id,file_name,sha256,target_environment,status,operation_id,deleted) VALUES('old','m{i}','m{i}.sql','{'a'*64}','test','{status}','operation',b'1');")
        first=_real_database_snapshot(database)
        assert [row["status"] for row in first["migrationLedger"]]==statuses
        assert first["databaseIdentity"]["name"]==database
        sql("INSERT INTO historical_business(value) VALUES ('second'); UPDATE infra_release_migration SET update_time=NOW();")
        second=_real_database_snapshot(database)
        assert first["schemaEvidence"]==second["schemaEvidence"]
        assert first["migrationLedger"]==second["migrationLedger"]
        assert sql("SELECT value FROM historical_business WHERE id=1;").strip()=="preserved"
    finally:
        dropped=run_mysql(f"DROP DATABASE `{database}`;")
        assert dropped.returncode==0,dropped.stderr


def test_plan_writer_recollects_snapshot_and_verifies_existing_bound_plan(tmp_path):
    root=tmp_path/"package";root.mkdir();(root/"manifest.json").write_text("{}",encoding="utf-8")
    control=tmp_path/"control";control.mkdir()
    result=_ps(_functions("Write-ReleasePreflightPlan")+f"""
$releaseDir='{root}';$deployControlLocalRoot='{control}';$Environment='test';$releasePublishScope='app-release';$scriptDir='{ROOT/'ops/deploy'}'
$maintenanceReleaseScriptRoot='{ROOT/'ops/release'}';$script:calls=@();$script:samples=0
function Read-ReleaseTargetSnapshot {{ $script:samples++; return @{{fresh=$script:samples}} }}
function Read-ReleasePreflightPlan {{return @{{items=@()}}}}
function Assert-ReleaseTargetDataPreconditions {{ param($Plan) $script:calls+='target-data-check' }}
function Invoke-CheckedCommand {{ param($FilePath,$ArgumentList) $script:calls+=@{{file=$FilePath;arguments=@($ArgumentList)}} }}
function Invoke-SshCapture {{ param($Command) $script:calls+='legacy-ledger-only';return @{{Ok=$true;Output='{{}}'}} }}
Write-ReleasePreflightPlan
Write-ReleasePreflightPlan -Verify
@{{samples=$script:samples;calls=$script:calls}}|ConvertTo-Json -Depth 8 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    evidence=json.loads(result.stdout)
    assert evidence["samples"]==2
    commands=[x for x in evidence["calls"] if isinstance(x,dict)]
    assert len(commands)==2
    for item in commands:assert "--executor" in item["arguments"]
    assert "--verify" not in commands[0]["arguments"]
    assert "--verify" in commands[1]["arguments"]


def test_executor_source_binding_checks_real_git_content_not_historical_absolute_root(tmp_path):
    repo=tmp_path/"new-location";deploy=repo/"ops/deploy";release=repo/"ops/release"
    deploy.mkdir(parents=True);release.mkdir()
    (deploy/"publish.ps1").write_text("'tracked'\n",encoding="utf-8")
    (release/"planner.py").write_text("value=1\n",encoding="utf-8")
    def git(*args):
        return subprocess.run(["git","-C",str(repo),*args],capture_output=True,text=True,encoding="utf-8",check=True).stdout.strip()
    git("init","-q");git("add","ops");git("-c","user.name=task-fixture","-c","user.email=task-fixture@example.invalid","commit","-qm","test source identity")
    head=git("rev-parse","HEAD")
    def check(expected):
        return _ps(_functions("Assert-ReleaseExecutorSourceBinding")+f"""
$scriptDir='{deploy}'
function Invoke-ProcessCapture {{param($FilePath,$ArgumentList) $output=& $FilePath @ArgumentList 2>&1;$code=$LASTEXITCODE;@{{ExitCode=$code;StdOut=($output -join "`n");StdErr=''}}}}
$integrity=@{{sourceRoots=@(@{{rootRole='maintenance';normalizedRoot='z:/historical/build-only-location';approvedCommit='{expected}';commit='{expected}'}})}}
Assert-ReleaseExecutorSourceBinding -PackageIntegrity $integrity
'SOURCE_PASSED'
""")
    assert check(head).returncode==0
    mismatch=check("0"*40)
    assert mismatch.returncode!=0 and "SOURCE_MISMATCH" in mismatch.stderr
    (release/"planner.py").write_text("value=2\n",encoding="utf-8")
    dirty=check(head)
    assert dirty.returncode!=0 and "SOURCE_DIRTY" in dirty.stderr
    git("restore","ops/release/planner.py")
    (deploy/"publish.ps1").write_text("'modified PS'\n",encoding="utf-8")
    dirty=check(head)
    assert dirty.returncode!=0 and "SOURCE_DIRTY" in dirty.stderr
    git("restore","ops/deploy/publish.ps1")
    (release/"unexpected.py").write_text("extra=1\n",encoding="utf-8")
    dirty=check(head)
    assert dirty.returncode!=0 and "SOURCE_DIRTY" in dirty.stderr


def test_missing_selected_image_is_rejected_without_any_application_start():
    result=_ps(_functions("Assert-ReleaseSelectedImagesLoaded","Get-ReleaseTargetImageIdentities")+"""
$publishWebsite=$false;$IncludeOnlyOffice=$false
$script:ReleaseRuntimeVerification=@{loadedImages=@()}
$script:ReleaseRuntimeImages=@(@{name='backend';reference='backend:v';id=('sha256:'+'a'*64)},@{name='frontend';reference='frontend:v';id=('sha256:'+'b'*64)},@{name='scheduler-smoke';reference='smoke:v';id=('sha256:'+'c'*64)})
$script:ReleaseVerifiedImageContent=@($script:ReleaseRuntimeImages | ForEach-Object { @{name=$_.name;reference=$_.reference;buildImageId=$_.id;configDigest=$_.id;platform=@{os='linux';architecture='amd64'}} })
function ConvertTo-ShellSingleQuotedLiteral {param($Value,$Purpose) "'$Value'"}
function Invoke-SshCapture {param($Command,[switch]$IgnoreExitCode) if($Command.StartsWith('docker info ')){return @{Ok=$true;Output='linux|x86_64|overlay2'}}; @{Ok=$false;Output='not found'}}
Assert-ReleaseSelectedImagesLoaded
""")
    assert result.returncode!=0
    assert "RELEASE_IMAGE_NOT_LOADED" in result.stdout+result.stderr


@pytest.mark.parametrize("missing", ["find", "stat", "sha256sum", "base64"])
def test_full_profile_missing_website_verification_tool_blocks_before_any_runtime_mutation(missing):
    result=_ps(_functions("Read-ReleaseTargetSnapshot","Assert-ReleaseWebsiteVerificationPrerequisites")+f"""
$publishWebsite=$true;$script:commands=@()
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 $script:commands+=$Command
 @{{Ok=$false;Output='WEBSITE_VERIFICATION_TOOL_MISSING:{missing}'}}
}}
function Assert-RemoteRuntimeDataOnDataDisk {{throw 'must not reach further collection'}}
try{{Read-ReleaseTargetSnapshot;$outcome='passed'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;commands=$script:commands}}|ConvertTo-Json -Depth 5 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert "TARGET_WEBSITE_VERIFICATION_NOT_READY" in value["outcome"],value
    assert len(value["commands"])==1
    assert 'command -v "$tool"' in value["commands"][0]
    assert not any(word in value["commands"][0] for word in ["mkdir", "docker load", "compose up", "CREATE TABLE"])


def test_native_mysql_command_uses_container_credentials_and_preserves_special_characters():
    runtime=mysql_runtime()
    result=_ps(_functions("Get-ReleaseTargetMySqlCommand")+"\n$script:TargetMySqlDatabase='information_schema'; Get-ReleaseTargetMySqlCommand | ConvertTo-Json -Compress")
    assert result.returncode==0,result.stdout+result.stderr
    command=shlex.split(json.loads(result.stdout))
    assert command[:4]==["docker","exec","-i","intruoyi-mysql"]
    command[3]=runtime.container_id
    actual=subprocess.run(command,input=b"SELECT 17;",capture_output=True,check=False,timeout=30)
    assert actual.returncode==0,actual.stderr.decode()
    assert actual.stdout.strip()==b"17"
    # This second probe checks shell environment propagation only; it is not a
    # simulated database success. The first invocation above used real MySQL.
    secret="synthetic space 'quote' \"double\" $dollar $(not-executed)"
    shell=command[6]
    assert "MYSQL_PWD=\"$MYSQL_ROOT_PASSWORD\"" in shell
    assert secret not in shell
    prefix=shell.split("exec mysql",1)[0]
    probe=subprocess.run(["docker","exec","-i","-e","MYSQL_ROOT_PASSWORD",runtime.container_id,
                          "sh","-lc",prefix+"exec env"],env={**os.environ,"MYSQL_ROOT_PASSWORD":secret},
                         capture_output=True,check=False,timeout=30)
    assert probe.returncode==0
    values=dict(line.split("=",1) for line in probe.stdout.decode().splitlines() if "=" in line)
    assert values["MYSQL_PWD"]==secret


@pytest.mark.parametrize("fault", ["none", "control-root", "mount", "tool", "redis-stopped", "space", "filesystem-drift", "space-after-lock"])
def test_snapshot_platform_gates_execute_before_any_runtime_write(tmp_path, fault):
    runtime=mysql_runtime();database="release_t4_"+uuid.uuid4().hex[:12]
    setup=run_mysql(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4;")
    assert setup.returncode==0,setup.stderr
    try:
        for filename in ("20260613_infra_release_migration_state.sql","20260921_infra_release_operation_lock_lease_fencing.sql"):
            setup=run_mysql((application_backend_root()/"sql/mysql"/filename).read_text(encoding="utf-8"),database)
            assert setup.returncode==0,setup.stderr
        runtime_config=os.environ["RELEASE_TEST_MYSQL_RUNTIME_CONFIG"]
        package=tmp_path/"package"; write_complete_package(package)
        control=tmp_path/"control";control.mkdir();(control/".env").write_text("IMAGE_TAG=test\n",encoding="utf-8")
        result=_ps(_functions("Read-ReleaseTargetSnapshot","Assert-RemoteRuntimeDataOnDataDisk",
                              "Get-ReleaseTargetDatabaseSnapshot","Get-ReleaseTargetSchemaCollectionSql",
                              "Get-ReleaseTargetMySqlCommand","Assert-ReleaseTargetControlSchema",*_CAPACITY_FUNCTIONS)+f"""
Import-Module '{GOVERNANCE}' -Force
$config=[IO.File]::ReadAllText('{runtime_config}')|ConvertFrom-Json
$Mode='deploy-release';$Environment='test';$Component='intruoyi';$IncludeOnlyOffice=$false;$ServerHost='task-host'
$DatabaseCapacityReserveBytes=[int64]1073741824
$RemoteAppDir='/task/runtime';$RemoteDataRoot='/task/data';$RemoteReleaseRoot='/task/releases';$RemoteDataDiskMount='/task';$RemoteDataDiskDevice='/dev/task'
$releaseDir='{package}';$packageDirectoryName='package';$releasePackageIntegrity=[IO.File]::ReadAllText('{package/'manifest.json'}')|ConvertFrom-Json
$script:ReleaseRuntimeImages=@($releasePackageIntegrity.runtimeImages);$remoteEnvLocal='{control/'.env'}';$remoteOpsRuntimeDir='/task/ops';$publishWebsite=$false
$script:commands=@();$script:phase=0
function ConvertTo-ShellSingleQuotedLiteral {{param($Value,$Purpose) "'$Value'"}}
function Get-RemoteRuntimeEnvMap {{return @{{MYSQL_DATABASE='{database}';MYSQL_ROOT_PASSWORD=$config.password;IMAGE_TAG='old';SERVER_HOST='task-host';BACKEND_HOST_PORT='48081';FRONTEND_HOST_PORT='8081';EDHR_S3_ENDPOINT='http://storage:9000';EDHR_S3_BUCKET='task';EDHR_S3_REGION='task';DCC_PROJECT_CODE_CODEX_CLI_COMMAND='/task/codex';DCC_PROJECT_CODE_CODEX_CLI_SHA256='{'d'*64}'}}}}
function Get-RemoteContainerEnvValue {{param($ContainerName,$Key) return $config.password}}
function Invoke-SshCommand {{param($Command) $script:commands+=$Command; if($Command -match 'mkdir|mount --bind|>> /etc/fstab'){{throw 'RUNTIME_WRITE_IN_READONLY_GATE'}}; if('{fault}' -eq 'mount'){{throw 'TARGET_PERSISTENT_MOUNT_INVALID'}}}}
function Invoke-SshCapture {{
 param($Command,[switch]$IgnoreExitCode)
 $script:commands+=$Command
 if($Command.StartsWith("cat <<'RELEASE_SQL'")){{
  $lines=@($Command -split "`r?`n");$sql=$lines[1..($lines.Count-2)] -join "`n"
  $output=@($sql | & docker exec -i '{runtime.container_id}' sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 --binary-mode --batch --raw --skip-column-names "$1"' sh '{database}' 2>&1)
  $code=$LASTEXITCODE;return @{{Ok=($code -eq 0);Output=($output -join "`n");ExitCode=$code}}
 }}
 if($Command -match 'CONTROL_ROOT_READY'){{return @{{Ok=('{fault}' -ne 'control-root');Output='CONTROL_ROOT_READY'}}}}
 if($Command -eq 'cat /etc/machine-id'){{return @{{Ok=$true;Output='{'a'*32}'}}}}
 if($Command -match 'json .Mounts'){{
  $role=if($Command -match 'intruoyi-mysql'){{'mysql'}}else{{'redis'}}
  $destination=if($role -eq 'mysql'){{'/var/lib/mysql'}}else{{'/data'}}
  $json=ConvertTo-Json -InputObject @(@{{Type='bind';Source="/task/runtime/data/$role";Destination=$destination}}) -Compress
  return @{{Ok=$true;Output=$json}}
 }}
 if($Command -match 'stat -Lc' -and $Command -notmatch 'RELEASE_CAPACITY'){{return @{{Ok=$true;Output="1:2`n/dev/task ext4 task-uuid"}}}}
 if($Command -match 'sha256sum'){{ $hash=if('{fault}' -eq 'tool'){{'{'e'*64}'}}else{{'{'d'*64}'}};return @{{Ok=$true;Output="$hash  /task/codex"}} }}
 if($Command -match 'State.Running|State.Health'){{return @{{Ok=$true;Output=$(if('{fault}' -eq 'redis-stopped'){{'false'}}else{{'true'}})}}}}
 if($Command -match 'DockerRootDir'){{return @{{Ok=$true;Output='{{"driver":"overlay2","root":"/task/docker","status":[]}}'}}}}
 if($Command -match 'RELEASE_CAPACITY'){{return @{{Ok=$true;Output=$(if('{fault}' -eq 'space' -or ('{fault}' -eq 'space-after-lock' -and $script:phase -eq 1)){{'1 1 1024'}}elseif('{fault}' -eq 'filesystem-drift' -and $script:phase -eq 1){{'2 999999999 4096'}}else{{'1 999999999 4096'}})}}}}
 throw 'UNEXPECTED_READONLY_TRANSPORT'
}}
try{{ $snapshot=Read-ReleaseTargetSnapshot; if('{fault}' -in @('filesystem-drift','space-after-lock')){{$script:phase=1;$snapshot=Read-ReleaseTargetSnapshot -Verify}}; $outcome='passed' }}catch{{ $outcome=$_.Exception.Message }}
@{{outcome=$outcome;commands=$script:commands;snapshot=$snapshot}}|ConvertTo-Json -Depth 50 -Compress
""")
        assert result.returncode==0,result.stdout+result.stderr
        value=json.loads(result.stdout)
        if fault=="none":
            assert value["outcome"]=="passed"
            snapshot_file=tmp_path/"target-state.json"
            snapshot_file.write_text(json.dumps(value["snapshot"]),encoding="utf-8")
            collected=subprocess.run(["python","-X","utf8","-c",
                "import sys;sys.path.insert(0,sys.argv[1]);from release_target_state_collector import collect_target_state;collect_target_state(sys.argv[2],target_environment='test')",
                str(ROOT/"ops/release"),str(tmp_path)],capture_output=True,text=True,encoding="utf-8",check=False)
            assert collected.returncode==0,collected.stdout+collected.stderr
        else:assert value["outcome"]!="passed",f"missing platform prerequisite was accepted: {fault}"
        assert all("mkdir" not in c and "mount --bind" not in c for c in value["commands"])
    finally:
        dropped=run_mysql(f"DROP DATABASE `{database}`;")
        assert dropped.returncode==0,dropped.stderr


def _mysql_snapshot_for_plan(database):
    observed=_real_database_snapshot(database)
    return {"schemaVersion":"release-deploy-target-state/v1","capturedAt":"2026-09-25T08:00:00Z",
            "targetEnvironment":"test","hostIdentity":{"host":"task-host","machineId":"a"*32},
            "databaseIdentity":observed["databaseIdentity"],"schemaEvidence":observed["schemaEvidence"],
            "migrationLedgerComplete":True,"migrationLedger":observed["migrationLedger"],
            "nonSecretConfig":{"MYSQL_DATABASE":database,"IMAGE_TAG":"old"},
            "persistentMounts":[{"role":"mysql","type":"volume","source":mysql_runtime().volume,
                                 "destination":"/var/lib/mysql","identity":mysql_runtime().container_id}],
            "platformPrerequisites":[{"toolId":"dcc-codex","path":"/task/codex","approvedSha256":"d"*64,
                                      "actualSha256":"d"*64,"executable":True}]}


@pytest.mark.parametrize("change", ["none","schema","data"])
def test_real_planner_rechecks_fresh_database_and_data_conditions_without_replacing_plan(tmp_path, change):
    runtime=mysql_runtime();database="release_t4_"+uuid.uuid4().hex[:12]
    created=run_mysql(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4;")
    assert created.returncode==0,created.stderr
    def sql(text):
        result=run_mysql(text,database);assert result.returncode==0,result.stderr;return result.stdout
    try:
        sql((application_backend_root()/"sql/mysql/20260613_infra_release_migration_state.sql").read_text(encoding="utf-8"))
        sql("CREATE TABLE task_probe(id INT PRIMARY KEY,value VARCHAR(30)); INSERT INTO task_probe VALUES(1,'historical');")
        root=tmp_path/"release-plan";manifest=write_complete_package(root)
        migration=root/"required-sql/001.sql"
        migration.write_text("-- release-migration: allowedEnvironments=test,prod,backup; dependsOn=; type=data; riskLevel=medium\nSELECT 1;\n",encoding="utf-8")
        check=root/"target-preflight/001.preflight.sql";check.parent.mkdir()
        check.write_text("-- release-target-preflight: migrationId=001; allowedEnvironments=test,prod,backup\nSELECT CASE WHEN COUNT(*)=1 THEN 'TARGET_PREFLIGHT_PASS:001' ELSE 'TARGET_PREFLIGHT_BLOCKED:001' END FROM task_probe;\n",encoding="utf-8")
        entry={"migrationId":"001","file":"required-sql/001.sql","sourcePath":"sql/mysql/001.sql","type":"data",
               "sha256":hashlib.sha256(migration.read_bytes()).hexdigest(),"allowedEnvironments":["test","prod","backup"],
               "dependsOn":[],"requiresTargetPreflight":False,
               "targetPreflight":{"reference":"target-preflight/001.preflight.sql","sha256":hashlib.sha256(check.read_bytes()).hexdigest(),"readOnly":True}}
        manifest.update(requiredSql=[entry],migrationPlan=[copy.deepcopy(entry)],database={"schemaMigrations":[copy.deepcopy(entry)]})
        rebind_package(root,manifest)
        control=tmp_path/"control";control.mkdir();snapshot_path=tmp_path/"fresh-snapshot.json"
        def invoke(verify=False):
            snapshot_path.write_text(json.dumps(_mysql_snapshot_for_plan(database)),encoding="utf-8")
            names=("Write-ReleasePreflightPlan","Read-ReleasePreflightPlan","Get-ReleaseTargetMySqlCommand",
                   "Assert-ReleaseTargetDataPreconditions","Read-ReleaseManifest","Read-ReleaseMigrationMetadata","ConvertTo-ReleaseFileSha256Hex")
            return _ps(_functions(*names)+f"""
$releaseDir='{root}';$deployControlLocalRoot='{control}';$Environment='test';$releasePublishScope='app-release';$scriptDir='{ROOT/'ops/deploy'}'
$maintenanceReleaseScriptRoot='{ROOT/'ops/release'}';$script:TargetMySqlDatabase='{database}'
$releaseMigrationAllowedTypes=@('schema','data','menu','config','permission','seed')
function Read-ReleaseTargetSnapshot {{[IO.File]::ReadAllText('{snapshot_path}')|ConvertFrom-Json}}
function Invoke-CheckedCommand {{param($FilePath,$ArgumentList) $output=& $FilePath @ArgumentList 2>&1; $code=$LASTEXITCODE; if($code -ne 0){{throw ($output -join "`n")}}}}
function Invoke-SshCapture {{
 param($Command,[switch]$IgnoreExitCode)
 $lines=@($Command -split "`r?`n");$delimiter=[regex]::Match($lines[0],"<<'([A-Z_]+)'").Groups[1].Value
 if(-not $delimiter -or $lines[-1] -ne $delimiter){{throw 'actual SQL carrier required'}}
 $sql=$lines[1..($lines.Count-2)] -join "`n"
 $output=@($sql | & docker exec -i '{runtime.container_id}' sh -lc 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 --binary-mode --batch --raw --skip-column-names "$1"' sh '{database}' 2>&1)
 $code=$LASTEXITCODE;return @{{Ok=($code -eq 0);Output=($output -join "`n");ExitCode=$code}}
}}
Write-ReleasePreflightPlan {'-Verify' if verify else ''}
""")
        first=invoke()
        assert first.returncode==0,first.stdout+first.stderr
        plan=(control/"preflight-plan.json").read_bytes()
        if change=="schema":sql("ALTER TABLE task_probe ADD COLUMN changed INT;")
        elif change=="data":sql("INSERT INTO task_probe VALUES(2,'concurrent');")
        second=invoke(True)
        if change=="none":assert second.returncode==0,second.stdout+second.stderr
        else:
            assert second.returncode!=0
            assert ("PLAN_INPUT_DRIFT" if change=="schema" else "TARGET_PREFLIGHT") in second.stdout+second.stderr
        assert (control/"preflight-plan.json").read_bytes()==plan
        assert sql("SELECT value FROM task_probe WHERE id=1;").strip()=="historical"
    finally:
        dropped=run_mysql(f"DROP DATABASE `{database}`;")
        assert dropped.returncode==0,dropped.stderr


_CAPACITY_FUNCTIONS = ("Assert-ReleaseTargetCapacity", "ConvertTo-ReleaseCapacityInteger", "Get-ReleaseCapacityReservation", "Read-ReleaseArchiveCapacity", "Invoke-ProcessCaptureWithInput", "ConvertTo-ProcessArgumentString")


def _capacity_probe(tmp_path, fault="none", shared=False, repeat=False, large=False, small_files=0):
    root=tmp_path/"package"
    manifest=write_complete_package(root,profile="full",only_office=True)
    if small_files:
        files={f"node_modules/task/file-{i}":b"x" for i in range(small_files)}
        files.update({"node_modules/playwright/package.json":b"{}","node_modules/xlsx/package.json":b"{}"})
        (root/"smoke/yudao-ui-admin-vue3/dependencies.tar").write_bytes(_tar_bytes(files))
        archive=root/f"intruoyi-images_{root.name}.tar"
        with tarfile.open(archive) as source:
            image_files={m.name:source.extractfile(m).read() for m in source if m.isfile()}
        images=json.loads(image_files["manifest.json"])
        images[0]["Layers"]=["task-layer/layer.tar"]
        image_files["manifest.json"]=json.dumps(images).encode()
        image_files["task-layer/layer.tar"]=_tar_bytes({f"usr/task/file-{i}":b"x" for i in range(small_files)})
        archive.write_bytes(_tar_bytes(image_files))
        rebind_package(root,manifest)
    if fault=="posix-name":
        (root/"smoke/yudao-ui-admin-vue3/dependencies.tar").write_bytes(_tar_bytes({r"node_modules/system-systemd\x2dcryptsetup.slice":b"x"}))
        rebind_package(root,manifest)
    if fault=="unreadable-tar":
        (root/"smoke/yudao-ui-admin-vue3/dependencies.tar").write_bytes(b"invalid tar")
        rebind_package(root,manifest)
    if fault in ("unsafe-hardlink","unsafe-symlink"):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode="w") as archive:
            entry=tarfile.TarInfo("node_modules/unsafe")
            entry.type=tarfile.LNKTYPE if fault=="unsafe-hardlink" else tarfile.SYMTYPE
            entry.linkname="../../../../host-outside";archive.addfile(entry)
        (root/"smoke/yudao-ui-admin-vue3/dependencies.tar").write_bytes(stream.getvalue())
        rebind_package(root,manifest)
    control=tmp_path/"control";control.mkdir()
    (control/".env").write_text("IMAGE_TAG=release-new\n",encoding="utf-8")
    (control/"website").mkdir()
    (control/"website/nginx.conf").write_text("server { listen 80; }",encoding="utf-8")
    return _ps(_functions(*_CAPACITY_FUNCTIONS, "ConvertTo-ShellSingleQuotedLiteral")+f"""
$releaseDir='{root}';$deployControlLocalRoot='{control}';$packageDirectoryName='package'
$releasePackageIntegrity=[IO.File]::ReadAllText('{root/'manifest.json'}')|ConvertFrom-Json
$script:ReleaseRuntimeImages=@($releasePackageIntegrity.runtimeImages)
$RemoteReleaseRoot='/task/releases';$RemoteAppDir='/task/runtime';$RemoteDataRoot='/task/data';$remoteOpsRuntimeDir='/task/ops';$Component='full';$publishWebsite=$true
$remoteEnvLocal='{control/'.env'}';$websiteNginxLocal='{control/'website/nginx.conf'}'
$script:commands=@();$script:limits=@{{}};$script:phase=0;$script:first=@()
if({'$true' if large else '$false'}){{foreach($im in $script:ReleaseRuntimeImages){{$im.sizeBytes=[int64]3221225472}}}}
switch('{fault}'){{
 'image-negative' {{$script:ReleaseRuntimeImages[0].sizeBytes=-1}}
 'image-string' {{$script:ReleaseRuntimeImages[0].sizeBytes='1024'}}
 'image-fraction' {{$script:ReleaseRuntimeImages[0].sizeBytes=1.5}}
 'image-missing' {{$script:ReleaseRuntimeImages[0].PSObject.Properties.Remove('sizeBytes')}}
 'artifact-negative' {{$releasePackageIntegrity.artifacts[0].bytes=-1}}
 'artifact-string' {{$releasePackageIntegrity.artifacts[0].bytes='1024'}}
 'artifact-overflow' {{$releasePackageIntegrity.artifacts[0].bytes=[uint64]::MaxValue}}
 'image-overflow' {{$script:ReleaseRuntimeImages[0].sizeBytes=[int64]::MaxValue}}
}}
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 $script:commands+=$Command
 if($Command -match 'DockerRootDir'){{
  if('{fault}' -eq 'containerd'){{return @{{Ok=$true;Output='{{"driver":"overlayfs","root":"/task/docker","status":[["driver-type","io.containerd.snapshotter.v1"]]}}'}}}}
  if('{fault}' -eq 'unsupported-driver'){{return @{{Ok=$true;Output='{{"driver":"unknown","root":"/task/docker","status":[]}}'}}}}
  return @{{Ok=$true;Output='{{"driver":"overlay2","root":"/task/docker","status":[]}}'}}
 }}
 if($Command -notmatch 'RELEASE_CAPACITY'){{throw 'UNEXPECTED_CAPACITY_TRANSPORT'}}
 $path=[regex]::Match($Command,"capacity_path='([^']+)'").Groups[1].Value
 $id=switch($path){{'/task/releases'{{'1'}} '/task/runtime'{{'2'}} '/task/data'{{'3'}} '/task/ops'{{'4'}} '/task/docker'{{'5'}} default{{throw 'UNEXPECTED_CAPACITY_PATH'}}}}
 if({'$true' if shared else '$false'}){{$id='1'}}
 $blocks=[int64]1000000000
 if($script:limits.ContainsKey($id)){{$blocks=[int64]($script:limits[$id]/4096)}}
 if('{fault}' -eq 'release-full' -and $path -eq '/task/releases'){{$blocks=0}}
 if('{fault}' -eq 'docker-full' -and $path -eq '/task/docker'){{$blocks=0}}
 if('{fault}' -eq 'ops-full' -and $path -eq '/task/ops'){{$blocks=0}}
 if('{fault}' -eq 'data-full' -and $path -eq '/task/data'){{$blocks=0}}
 if('{fault}' -eq 'data-tiny' -and $path -eq '/task/data'){{return @{{Ok=$true;Output="$id 1 1024"}}}}
 if('{fault}' -eq 'db-floor' -and $path -eq '/task/data'){{$blocks=262144}}
 if('{fault}' -eq 'db-under' -and $path -eq '/task/data'){{$blocks=262143}}
 if('{fault}' -eq 'runtime-full' -and $path -eq '/task/runtime'){{$blocks=0}}
 if('{fault}' -eq 'malformed'){{return @{{Ok=$true;Output='1 bad 4096'}}}}
 if('{fault}' -eq 'probe-failed'){{return @{{Ok=$false;Output='probe failed'}}}}
 if('{fault}' -eq 'late-full' -and $script:phase -gt 0 -and $path -eq '/task/docker'){{$blocks=0}}
 return @{{Ok=$true;Output="$id $blocks 4096"}}
}}
try{{
 $script:first=@(Assert-ReleaseTargetCapacity)
 if({'$true' if repeat else '$false'}){{
  foreach($item in $script:first){{$script:limits[$item.fileSystemId]=[int64]$item.requiredBytes}}
  $script:phase=1
  if('{fault}' -eq 'below-boundary'){{foreach($id in @($script:limits.Keys)){{$script:limits[$id]-=4096}}}}
  $second=@(Assert-ReleaseTargetCapacity)
 }}
 $outcome='passed'
}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;evidence=$script:first;commands=$script:commands}}|ConvertTo-Json -Depth 12 -Compress
""")


@pytest.mark.parametrize("fault",["release-full","docker-full","ops-full","data-full","runtime-full","malformed","probe-failed","containerd","unsupported-driver"])
def test_capacity_rejects_each_real_destination_filesystem_before_writes(tmp_path,fault):
    result=_capacity_probe(tmp_path,fault)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert "TARGET_CAPACITY_NOT_READY" in value["outcome"],value
    assert all("mkdir" not in c and "docker load" not in c for c in value["commands"])


@pytest.mark.parametrize("fault",["image-negative","image-string","image-fraction","image-missing","artifact-negative","artifact-string","artifact-overflow","image-overflow"])
def test_capacity_rejects_invalid_or_overflowing_verified_size_inputs(tmp_path,fault):
    result=_capacity_probe(tmp_path,fault)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert "TARGET_CAPACITY_INPUT_INVALID" in value["outcome"],value


@pytest.mark.parametrize("shared",[False,True])
def test_capacity_aggregates_destinations_and_accepts_exact_boundary_with_large_images(tmp_path,shared):
    result=_capacity_probe(tmp_path,shared=shared,repeat=True,large=True)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value["outcome"]=="passed",value
    assert len(value["evidence"])==(1 if shared else 5)
    assert sum(e["requiredBytes"] for e in value["evidence"])>3*1024**3
    assert all(e["requiredBytes"]>0 for e in value["evidence"])


@pytest.mark.parametrize("fault",["below-boundary","late-full"])
def test_capacity_rechecks_fresh_facts_and_rejects_less_than_reserved_capacity(tmp_path,fault):
    result=_capacity_probe(tmp_path,fault,repeat=True)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value["evidence"],value
    assert "TARGET_CAPACITY_NOT_READY" in value["outcome"],value


_SQL_CHAIN_FUNCTIONS = (
    "Get-ReleaseTargetMySqlCommand", "Get-ReleaseOperationLockSchemaState", "Invoke-ReleaseOperationLockAcquire",
    "Assert-ReleaseOperationLockOwnership", "Invoke-ReleaseOperationLockRelease", "New-ReleaseMigrationStateUpsertSql",
    "Invoke-RequiredDatabaseSqlScriptWithState", "Invoke-ReleaseMigrationStateBatchUpdate",
    "Get-RequiredDatabaseSqlFileName", "ConvertTo-SqlStringLiteral", "ConvertTo-ShellSingleQuotedLiteral",
    "ConvertTo-ReleaseErrorBase64", "ConvertTo-ReleaseErrorMessage", "Protect-ReleaseSensitiveText",
)


def _capture_database_commands(database,remote_sql):
    result=_ps(_functions(*_SQL_CHAIN_FUNCTIONS)+f"""
$Environment='test';$ReleaseTag='task-bound';$script:TargetMySqlDatabase='{database}'
$mySqlRootPassword='SYNTHETIC_UNSAFE_TOKEN with $ dollar '' quote';$script:ReleaseErrorMessageMaxLength=1024
$script:ReleaseOperationExecutorHost='TASK';$script:ReleaseOperationExecutorPid='1';$script:ReleaseOperationExecutorIdentity='task'
$script:ReleaseOperationLegacyLockHeld=$false;$script:commands=@()
function Assert-ReleaseOperationWriteFence {{}}
function Invoke-SshCapture {{param([string]$Command,[switch]$IgnoreExitCode)
 $script:commands+=@{{command=$Command;input=''}}
 if($Command.Contains('LOCK_SCHEMA_READY')){{$value='LOCK_SCHEMA_READY'}}
 elseif($Command.Contains('LOCK_ACQUIRED')){{$value="LOCK_ACQUIRED:$($script:ReleaseOperationLeaseToken)"}}
 elseif($Command.Contains('HEARTBEAT_RENEWED')){{$value='HEARTBEAT_RENEWED'}}
 else{{$value='LOCK_OWNED'}}
 @{{Ok=$true;Output=$value}}
}}
function Invoke-SshCommand {{param($Command) $script:commands+=@{{command=$Command;input=''}}}}
function Invoke-SshCommandWithInput {{param($Command,$StandardInput) $script:commands+=@{{command=$Command;input=$StandardInput}}}}
$item=@{{migrationId='task-probe';file='required-sql/task-probe.sql';sha256='{'a'*64}'}}
Get-ReleaseOperationLockSchemaState | Out-Null
Invoke-ReleaseOperationLockAcquire
Assert-ReleaseOperationLockOwnership
Invoke-RequiredDatabaseSqlScriptWithState -Item $item -RemoteSqlPath '{remote_sql}'
Invoke-ReleaseMigrationStateBatchUpdate -Items @($item) -Status 'APPLIED'
Invoke-ReleaseOperationLockRelease -Status 'APPLIED'
ConvertTo-Json -InputObject @($script:commands) -Depth 5 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    return json.loads(result.stdout)


def test_actual_lock_and_migration_carriers_share_bound_database_without_host_password():
    database="release_t4_bound_carrier"
    commands=_capture_database_commands(database,"/tmp/task-probe.sql")
    assert len(commands)>=7
    for item in commands:
        assert "SYNTHETIC_UNSAFE_TOKEN" not in item["command"],"host password leaked into actual SQL carrier"
        assert "ruoyi-vue-pro" not in item["command"],"SQL carrier ignores the database bound into the target plan"
        assert f"sh '{database}'" in item["command"]


def test_real_lock_schema_acquire_migration_and_release_stay_in_bound_database():
    runtime=mysql_runtime();database="release_t4_"+uuid.uuid4().hex[:12];other=database+"_other"
    remote_sql="/tmp/"+database+".sql"
    schema=(application_backend_root()/"sql/mysql/20260613_infra_release_migration_state.sql").read_text(encoding="utf-8")
    fencing=(application_backend_root()/"sql/mysql/20260921_infra_release_operation_lock_lease_fencing.sql").read_text(encoding="utf-8")
    for db in (database,other):
        created=run_mysql(f"CREATE DATABASE `{db}` CHARACTER SET utf8mb4;")
        assert created.returncode==0,created.stderr
        initialized=run_mysql(schema+"\n"+fencing,db)
        assert initialized.returncode==0,initialized.stderr
    try:
        commands=_capture_database_commands(database,remote_sql)
        # Execute the production shell/SQL unchanged. This adapter changes only
        # the Docker transport to the already-owned isolated container, never DB/SQL.
        bridge="""docker() {
  [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94
  shift 3
  "$@"
}
"""
        payload="CREATE TABLE task_bound_probe(id INT PRIMARY KEY, value VARCHAR(40)); INSERT INTO task_bound_probe VALUES(1,'real-target');\n"
        uploaded=subprocess.run(["docker","exec","-i",runtime.container_id,"sh","-c",f"cat > '{remote_sql}'"],input=payload.encode(),capture_output=True,check=False)
        assert uploaded.returncode==0,uploaded.stderr
        for item in commands:
            command=item["command"]
            assert "SYNTHETIC_UNSAFE_TOKEN" not in command,"unsafe production SQL credential carrier"
            if item["input"]:command="cat <<'TASK_SQL_INPUT' | "+command+"\n"+item["input"]+"\nTASK_SQL_INPUT"
            result=subprocess.run(["docker","exec","-i",runtime.container_id,"sh","-s"],input=(bridge+command+"\n").encode(),capture_output=True,check=False)
            assert result.returncode==0,result.stderr.decode()
        result=run_mysql("SELECT value FROM task_bound_probe; SELECT status FROM infra_release_operation_lock; SELECT status FROM infra_release_migration;",database)
        assert result.returncode==0,result.stderr
        assert result.stdout.split()==["real-target","APPLIED","APPLIED"]
        other_state=run_mysql("SELECT COUNT(*) FROM infra_release_operation_lock; SELECT COUNT(*) FROM infra_release_migration;",other)
        assert other_state.returncode==0 and other_state.stdout.split()==["0","0"]
    finally:
        cleanup=subprocess.run(["docker","exec",runtime.container_id,"rm","-f",remote_sql],capture_output=True,check=False)
        assert cleanup.returncode==0,cleanup.stderr
        for db in (database,other):
            dropped=run_mysql(f"DROP DATABASE `{db}`;")
            assert dropped.returncode==0,dropped.stderr


@pytest.mark.parametrize("environment,fault",[(e,"none") for e in ("test","prod","backup")]+[("test",f) for f in (
    "missing","hash","no-pass","multi-pass","not-readonly","unsafe-sql","wrong-reference","wrong-env","false-requires","missing-requires")])
def test_actual_builder_packages_checks_and_deployer_consumes_only_package_for_each_target(tmp_path,environment,fault):
    runtime=mysql_runtime();database="release_t4_"+uuid.uuid4().hex[:12]
    created=run_mysql(f"CREATE DATABASE `{database}`;",None)
    assert created.returncode==0,created.stderr
    try:
        setup=run_mysql("CREATE TABLE task_probe(id INT PRIMARY KEY); INSERT INTO task_probe VALUES(1);",database)
        assert setup.returncode==0,setup.stderr
        source=tmp_path/"source";checks=source/"sql/mysql/target-preflight";checks.mkdir(parents=True)
        migration=source/"sql/mysql/001.sql"
        migration.write_text("-- release-migration: allowedEnvironments=test,prod,backup; dependsOn=; type=data; riskLevel=medium\nSELECT 1;\n",encoding="utf-8")
        check=checks/"001.preflight.sql"
        header="-- release-target-preflight: migrationId=001; allowedEnvironments=test,prod,backup\n"
        check.write_text(header+"SELECT CASE WHEN COUNT(*)=1 THEN 'TARGET_PREFLIGHT_PASS:001' ELSE 'TARGET_PREFLIGHT_BLOCKED:001' END FROM task_probe;\n",encoding="utf-8")
        root=tmp_path/"package";manifest=write_complete_package(root)
        names=("Copy-RequiredDatabaseSqlScripts","New-ReleaseRequiredSqlManifestEntries","Read-ReleaseMigrationMetadata",
               "Get-RequiredDatabaseSqlFileName","ConvertTo-ReleaseFileSha256Digest","ConvertTo-ReleaseFileSha256Hex")
        build=_ps(_functions(*names)+f"""
$backendRepo='{source}';$requiredSqlLocalDir='{root/'required-sql'}';$releaseDir='{root}';$maintenanceReleaseScriptRoot='{ROOT/'ops/release'}'
$releaseMigrationAllowedTypes=@('schema','data','menu','config','permission','seed')
$requiredDatabaseSqlScripts=@(@{{Path='sql/mysql/001.sql';Environments=@('test','prod','backup')}})
function Invoke-CheckedCommand {{param($FilePath,$ArgumentList) $output=& $FilePath @ArgumentList 2>&1;if($LASTEXITCODE -ne 0){{throw ($output -join "`n")}}}}
Copy-RequiredDatabaseSqlScripts
ConvertTo-Json -InputObject @(New-ReleaseRequiredSqlManifestEntries) -Depth 12 -Compress
""")
        assert build.returncode==0,build.stdout+build.stderr
        entries=json.loads(build.stdout);entry=entries[0]
        packaged=root/entry["targetPreflight"]["reference"]
        assert packaged.read_bytes()==check.read_bytes()
        assert entry["targetPreflight"]["sha256"]=="sha256:"+hashlib.sha256(packaged.read_bytes()).hexdigest()
        assert entry["targetPreflight"]["readOnly"] is True
        # Remove the source inputs. Deployment must use the immutable package.
        migration.unlink();check.unlink()
        entry["requiresTargetPreflight"]=False
        if fault=="missing":packaged.unlink()
        elif fault=="hash":packaged.write_text(header+"SELECT 'changed';",encoding="utf-8")
        elif fault in ("no-pass","multi-pass","unsafe-sql","wrong-env"):
            body={"no-pass":"SELECT 'not-a-pass';", "multi-pass":"SELECT 'TARGET_PREFLIGHT_PASS:001' UNION ALL SELECT 'TARGET_PREFLIGHT_PASS:001';",
                  "unsafe-sql":"DELETE FROM task_probe;", "wrong-env":"SELECT 'TARGET_PREFLIGHT_PASS:001';"}[fault]
            packaged.write_text((header.replace("test,prod,backup","prod,backup") if fault=="wrong-env" else header)+body,encoding="utf-8")
            entry["targetPreflight"]["sha256"]="sha256:"+hashlib.sha256(packaged.read_bytes()).hexdigest()
        elif fault=="not-readonly":entry["targetPreflight"]["readOnly"]=False
        elif fault=="wrong-reference":entry["targetPreflight"]["reference"]="target-preflight/other.sql"
        elif fault in ("false-requires","missing-requires"):
            entry.pop("targetPreflight")
            if fault=="missing-requires":entry.pop("requiresTargetPreflight")
        manifest.update(requiredSql=[entry],migrationPlan=[copy.deepcopy(entry)],database={"schemaMigrations":[copy.deepcopy(entry)]})
        rebind_package(root,manifest)
        if fault=="none":
            artifact=next(a for a in manifest["artifacts"] if a["path"]=="target-preflight/001.preflight.sql")
            assert artifact["sha256"].removeprefix("sha256:")==hashlib.sha256(packaged.read_bytes()).hexdigest()
        names=("Assert-ReleaseTargetDataPreconditions","Read-ReleaseManifest","Read-ReleaseMigrationMetadata","ConvertTo-ReleaseFileSha256Hex","Get-ReleaseTargetMySqlCommand","Invoke-ProcessCaptureWithInput","ConvertTo-ProcessArgumentString")
        consume=_ps(_functions(*names)+f"""
$releaseDir='{root}';$backendRepo='{source}';$Environment='{environment}';$maintenanceReleaseScriptRoot='{ROOT/'ops/release'}';$script:TargetMySqlDatabase='{database}'
$releaseMigrationAllowedTypes=@('schema','data','menu','config','permission','seed');$script:commands=@()
function Invoke-CheckedCommand {{param($FilePath,$ArgumentList) $output=& $FilePath @ArgumentList 2>&1;if($LASTEXITCODE -ne 0){{throw ($output -join "`n")}}}}
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 $script:commands+=$Command
 $bridge='docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}' + "`n"
 $result=Invoke-ProcessCaptureWithInput -FilePath 'docker' -ArgumentList @('exec','-i','{runtime.container_id}','sh','-s') -StandardInput (($bridge+$Command) -replace "`r`n","`n")
 @{{Ok=($result.ExitCode -eq 0);Output=($result.StdOut+$result.StdErr)}}
}}
try{{Assert-ReleaseTargetDataPreconditions -Plan @{{items=@(@{{action='APPLY';migrationId='001'}})}};$outcome='passed'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;commands=$script:commands}}|ConvertTo-Json -Depth 5 -Compress
""")
        assert consume.returncode==0,consume.stdout+consume.stderr
        value=json.loads(consume.stdout)
        if fault=="none":
            assert value["outcome"]=="passed",value
            assert len(value["commands"])==1
        else:assert value["outcome"]!="passed",value
        for command in value["commands"]:
            assert "TRANSACTION READ ONLY" in command and f"sh '{database}'" in command
        unchanged=run_mysql("SELECT COUNT(*) FROM task_probe;",database)
        assert unchanged.returncode==0 and unchanged.stdout.strip()=="1"
    finally:
        dropped=run_mysql(f"DROP DATABASE `{database}`;")
        assert dropped.returncode==0,dropped.stderr


@pytest.mark.parametrize("fault",["data-tiny","db-under"])
def test_database_filesystem_requires_explicit_one_gib_platform_reserve(tmp_path,fault):
    result=_capacity_probe(tmp_path,fault)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert "TARGET_CAPACITY_NOT_READY" in value["outcome"],value


def test_database_reserve_boundary_and_tar_member_blocks_are_independently_accounted(tmp_path):
    result=_capacity_probe(tmp_path,"db-floor",small_files=2048)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert value["outcome"]=="passed",value
    roles={role:entry for entry in value["evidence"] for role in entry["roles"]}
    # Known 2048 one-byte files consume at least 2048 real allocation blocks;
    # this expectation does not call the production reservation calculator.
    assert roles["runtime"]["requiredBytes"]>=2048*4096
    assert roles["docker"]["requiredBytes"]>=2048*4096
    assert roles["data"]["requiredBytes"]==1024**3


@pytest.mark.parametrize("fault",["unreadable-tar","unsafe-hardlink","unsafe-symlink"])
def test_archive_capacity_cannot_ignore_unreadable_or_escaping_link_members(tmp_path,fault):
    result=_capacity_probe(tmp_path,fault)
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    assert "TARGET_CAPACITY_INPUT_INVALID" in value["outcome"],value



def test_archive_member_capacity_accepts_posix_backslash_filename_without_host_resolution(tmp_path):
    result=_capacity_probe(tmp_path,"posix-name")
    assert result.returncode==0,result.stdout+result.stderr
    assert json.loads(result.stdout)["outcome"]=="passed",result.stdout


def test_process_stdin_transport_preserves_exact_utf8_without_bom():
    payload="docker() { printf '中文'; }\n"
    encoded=base64.b64encode(payload.encode("utf-8")).decode()
    result=_ps(_functions("Invoke-ProcessCaptureWithInput","ConvertTo-ProcessArgumentString")+f"""
$inputText=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))
$result=Invoke-ProcessCaptureWithInput -FilePath 'python' -ArgumentList @('-X','utf8','-c','import hashlib,sys;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())') -StandardInput $inputText
if($result.ExitCode -ne 0){{throw $result.StdErr}}
$result.StdOut.Trim()
""")
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.strip()==hashlib.sha256(payload.encode("utf-8")).hexdigest()



_SELECTED_IMAGE_CASES = [
    (website, only_office, missing)
    for website in (False, True)
    for only_office in (False, True)
    for missing in ["none", "backend", "frontend", "scheduler-smoke"]
        + (["website"] if website else []) + (["onlyoffice"] if only_office else [])
]


@pytest.mark.parametrize("website,only_office,missing", _SELECTED_IMAGE_CASES)
def test_actual_start_segment_refuses_every_missing_selected_image_before_any_compose_start(website,only_office,missing):
    names=["backend","frontend","scheduler-smoke"]+(["website"] if website else [])+(["onlyoffice"] if only_office else [])
    images=[{"name":name,"reference":f"task-{name}:release","id":f"sha256:{index+1:064x}"} for index,name in enumerate(names)]
    encoded=base64.b64encode(json.dumps(images).encode()).decode()
    result=_ps(_functions("Assert-ReleaseSelectedImagesLoaded","Get-ReleaseTargetImageIdentities","ConvertTo-ShellSingleQuotedLiteral")+f"""
$publishBackend=$true;$publishFrontend=$true;$publishWebsite=${str(website).lower()};$IncludeOnlyOffice=${str(only_office).lower()}
$RemoteAppDir='/task/runtime';$PublishTargetName='task';$script:commands=@();$script:inspections=@()
$parsedImages=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json
$script:ReleaseRuntimeImages=@($parsedImages)
$script:ReleaseVerifiedImageContent=@($parsedImages | ForEach-Object {{ @{{name=$_.name;reference=$_.reference;buildImageId=$_.id;configDigest=$_.id;platform=@{{os='linux';architecture='amd64'}}}} }})
$script:ReleaseRuntimeVerification=@{{loadedImages=@()}}
function Assert-ReleaseOperationWriteFence {{}}
function Complete-ReleaseDeploymentPhase {{}}
function Start-ReleaseDeploymentPhase {{param($Name,[switch]$Finalizing)}}
function Assert-RemoteActualApplicationImages {{}}
function Assert-RemoteWebsitePayloadIdentity {{}}
function Invoke-SshCapture {{param($Command,[switch]$IgnoreExitCode)
 if($Command.StartsWith('docker info ')){{return @{{Ok=$true;Output='linux|x86_64|overlay2'}}}}
 if(-not $Command.StartsWith('docker image inspect ')){{throw 'UNEXPECTED_IMAGE_TRANSPORT'}}
 foreach($image in $script:ReleaseRuntimeImages){{
  if($Command.EndsWith("'$($image.reference)'")){{
   $script:inspections+=$image.name
   if($image.name -ceq '{missing}'){{return @{{Ok=$false;Output='image missing'}}}}
   return @{{Ok=$true;Output=$image.id}}
  }}
 }}
 throw 'UNDECLARED_IMAGE_INSPECTION'
}}
function Invoke-SshCommand {{param($Command) $script:commands+=$Command}}
$source=[IO.File]::ReadAllText('{SCRIPT}')
$start=$source.IndexOf('    $runtimeServices = @()');$finish=$source.IndexOf("    Info 'Waiting for remote HTTP readiness'",$start)
if($start -lt 0 -or $finish -lt $start){{throw 'actual deployment start segment missing'}}
try{{Invoke-Expression $source.Substring($start,$finish-$start);$outcome='started'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;commands=$script:commands;inspections=$script:inspections}}|ConvertTo-Json -Depth 6 -Compress
""")
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout)
    if missing=="none":
        assert value["outcome"]=="started",value
        assert value["inspections"]==names
        assert len(value["commands"])==(2 if website else 1)
        assert all("--no-deps --pull never" in command for command in value["commands"])
    else:
        assert f"RELEASE_IMAGE_NOT_LOADED: {missing}" in value["outcome"],value
        assert value["inspections"]==names[:names.index(missing)+1]
        assert value["commands"]==[],"missing image reached compose start/pull/platform mutation"
