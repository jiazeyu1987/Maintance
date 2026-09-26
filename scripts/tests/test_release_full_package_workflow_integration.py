"""T7 real runtime configuration and existing release caller contracts.

The full runner owns C5/C6 failure and restart coverage; it is not duplicated here.
"""
from __future__ import annotations

import json
import os
import subprocess
import copy
import sys
from pathlib import Path

import pytest

from test_release_runtime_identity import engine
from test_release_full_package_contract import _ps, _functions, ROOT, SCRIPT, write_complete_package
from test_release_package_governance import _write_operation, _write_tested_attestation, _verify_promotion
from test_release_durable_deployment_evidence import flow as deployment_flow, flow_script


@pytest.fixture(scope='module')
def classic_images(engine):
    # Share the single task engine fixture; do not create a second set of tags.
    return engine


def test_explicit_rebuilt_classic_configuration_reaches_real_fixture(engine):
    # This initially fails in the old fixture's immutable one-off ID assertion.
    # It is infrastructure RED, not a newly discovered product business defect.
    config = json.loads(Path(os.environ['RELEASE_TEST_MYSQL_RUNTIME_CONFIG']).read_text(encoding='utf-8'))
    assert config['classic']['containerId'] != '1077b4a2af5f527ad2f57b99a72734d03578e256e0552f60fbaf48518d8a13fb'
    assert engine['good'].startswith('sha256:')


@pytest.mark.parametrize('fault,scope,message',[
    ('missing-classic','classic','requires classic'),
    ('empty','classic','requires task'),
    ('old-id','classic','instance identity mismatch'),
    ('mismatched-name','classic','Docker inspection failed'),
    ('wrong-task','classic','ownership mismatch'),
    ('wrong-volume','classic','data mount identity mismatch'),
    ('relative-cache','settings','taskCache'),
    ('missing-cache','settings','taskCache'),
    ('invalid-prefix','settings','prefix'),
    ('relative-archive','archive','archive path'),
    ('archive-bytes','archive','archive bytes mismatch'),
    ('archive-sha','archive','archive sha256 mismatch'),
    ('archive-content','archive','official content identity mismatch'),
])
def test_explicit_runtime_rejects_bad_configuration_before_fixture_write(tmp_path,fault,scope,message):
    from release_test_runtime import classic_runtime
    actual=classic_runtime()
    source=json.loads(Path(os.environ['RELEASE_TEST_MYSQL_RUNTIME_CONFIG']).read_text(encoding='utf-8'))
    # These consumption-scoped validation copies do not need MySQL credentials.
    config=copy.deepcopy(source)
    config['password']='REDACTED-NOT-USED'
    if fault=='missing-classic':del config['classic']
    elif fault=='empty':config={}
    elif fault=='old-id':config['classic']['containerId']='1077b4a2af5f527ad2f57b99a72734d03578e256e0552f60fbaf48518d8a13fb'
    elif fault=='mismatched-name':config['classic']['container']=source['prefix']+'nonexistent'
    elif fault=='wrong-task':config['task']='unrelated-task'
    elif fault=='wrong-volume':config['classic']['volume']=source['volume']
    elif fault=='relative-cache':config['taskCache']='relative-cache'
    elif fault=='missing-cache':config['taskCache']=str(tmp_path/'absent')
    elif fault=='invalid-prefix':config['prefix']='shared/'
    elif fault=='relative-archive':config['officialArchive']['path']='relative.tar'
    elif fault=='archive-bytes':config['officialArchive']['bytes']+=1
    elif fault=='archive-sha':config['officialArchive']['sha256']='0'*64
    elif fault=='archive-content':config['officialArchive']['configDigest']='sha256:'+'0'*64
    path=tmp_path/'redacted-runtime.json';path.write_text(json.dumps(config),encoding='utf-8')
    def inventory():
        return subprocess.run(['docker','exec',actual.container_id,'docker','ps','-a','--no-trunc','--format','{{.ID}}'],
            capture_output=True,text=True,encoding='utf-8',check=True).stdout
    before=inventory()
    environment=dict(os.environ,RELEASE_TEST_MYSQL_RUNTIME_CONFIG=str(path))
    result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/tests/release_test_runtime.py'),'--check',scope],
        env=environment,capture_output=True,text=True,encoding='utf-8',timeout=120)
    assert result.returncode!=0 and message in result.stderr, result.stderr
    secret_detected=source['password'] in result.stdout+result.stderr
    assert not secret_detected, 'runtime validation leaked a private credential'
    assert inventory()==before


def test_explicit_mysql_flock_directory_is_required_and_rejects_missing_tool(tmp_path,monkeypatch):
    from release_test_runtime import mysql_runtime,mysql_flock_directory
    runtime=mysql_runtime()
    source=json.loads(Path(os.environ['RELEASE_TEST_MYSQL_RUNTIME_CONFIG']).read_text(encoding='utf-8'))
    source['password']='REDACTED-NOT-USED'
    path=tmp_path/'redacted-tools.json'
    for directory in ['relative','/tmp/'+source['prefix']+'missing-tools']:
        source['mysqlFlockDirectory']=directory
        path.write_text(json.dumps(source),encoding='utf-8')
        monkeypatch.setenv('RELEASE_TEST_MYSQL_RUNTIME_CONFIG',str(path))
        with pytest.raises(RuntimeError,match='flock'):
            mysql_flock_directory(runtime)


@pytest.mark.parametrize('environment', ['test','prod','backup'])
@pytest.mark.parametrize('component,office', [('intruoyi',False),('intruoyi',True),('full',False),('full',True)])
def test_real_parameter_binding_preserves_complete_scope_environment_and_source_inputs(environment,component,office):
    result = _ps(_functions()+f"""
$body=@'
@{{mode=$Mode;component=$Component;environment=$Environment;office=[bool]$IncludeOnlyOffice;selection=$SourceSelectionId;maintenance=$ExpectedMaintenanceCommit;application=$ExpectedApplicationCommit;frontend=$ExpectedFrontendCommit;scope=$PublishScope}}|ConvertTo-Json -Compress
'@
$bind=[scriptblock]::Create($ast.ParamBlock.Extent.Text+"`n"+$body)
& $bind -Mode build-release -Component '{component}' -Environment '{environment}' -IncludeOnlyOffice:${str(office).lower()} -SourceSelectionId 'task-t7-selection' -ExpectedMaintenanceCommit '{'a'*40}' -ExpectedApplicationCommit '{'b'*40}' -ExpectedFrontendCommit '{'b'*40}' -PublishScope app-release
""")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == dict(mode='build-release',component=component,environment=environment,
        office=office,selection='task-t7-selection',maintenance='a'*40,application='b'*40,frontend='b'*40,scope='app-release')


@pytest.mark.parametrize('environment,confirmation,accepted', [('test','',True),('prod','',False),('backup','',False),('prod','PROD',True),('backup','PROD',True)])
def test_actual_production_grade_authorization_statement_runs_before_external_action(environment,confirmation,accepted):
    # Execute the actual top-level AST statement, without booting the deployment.
    result = _ps(_functions()+f"""
$Environment='{environment}';$ConfirmText='{confirmation}';$script:externalActions=0
$guard=@($ast.EndBlock.Statements|Where-Object{{$_.Extent.Text.StartsWith("if (@('prod', 'backup') -contains")}})
if($guard.Count -ne 1){{throw 'production authorization statement missing'}}
try{{Invoke-Expression $guard[0].Extent.Text;$script:externalActions++;$outcome='accepted'}}catch{{$outcome=$_.Exception.Message}}
@{{outcome=$outcome;externalActions=$script:externalActions}}|ConvertTo-Json -Compress
""")
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value['externalActions'] == int(accepted)
    assert value['outcome']=='accepted' if accepted else 'Explicit confirmation required' in value['outcome']


@pytest.mark.parametrize('fault', [None,'status','targetEnvironment','releaseTag','mode','writeActions'])
def test_actual_prod_dry_run_gate_accepts_only_readonly_matching_evidence(tmp_path,fault):
    evidence = dict(status='passed',targetEnvironment='prod',releaseTag='release-t7',mode='preflight-release',writeActions=[])
    if fault:
        evidence[fault] = ['runtime-write'] if fault=='writeActions' else 'invalid'
    path = tmp_path/'dryrun.json'
    path.write_text(json.dumps(evidence),encoding='utf-8')
    result = _ps(_functions('Assert-ProdDryRunEvidence')+f"""
$Environment='prod';$Mode='deploy-release';$ReleaseTag='release-t7';$ProdDryRunEvidencePath='{path.as_posix()}'
Assert-ProdDryRunEvidence
'accepted'
""")
    assert (result.returncode==0) == (fault is None)
    if fault: assert 'dry-run' in result.stderr


@pytest.mark.parametrize('fault',[None,'selection','commit','dirty'])
def test_real_source_freeze_consumes_approved_selection_and_actual_git(tmp_path,fault):
    paths = [tmp_path/'maintenance',tmp_path/'application']
    commits=[]
    for path in paths:
        path.mkdir()
        for args in [('init',),('config','user.email','release-task@example.invalid'),('config','user.name','release task')]:
            subprocess.run(['git','-C',str(path),*args],capture_output=True,check=True)
        (path/'tracked.txt').write_text('task-only source',encoding='utf-8')
        subprocess.run(['git','-C',str(path),'add','tracked.txt'],capture_output=True,check=True)
        subprocess.run(['git','-C',str(path),'commit','-m','task source'],capture_output=True,check=True)
        commits.append(subprocess.run(['git','-C',str(path),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip())
    backend=paths[1]/'IntRuoyiBackend';frontend=paths[1]/'IntRuoyiFronted'
    backend.mkdir();frontend.mkdir()
    if fault=='dirty':(paths[0]/'tracked.txt').write_text('changed',encoding='utf-8')
    result = _ps(_functions('Assert-ReleaseSourceFreeze','Get-ReleaseGitValue','Invoke-ProcessCapture','ConvertTo-ProcessArgumentString')+f"""
$Mode='build-release';$scriptDir='{paths[0].as_posix()}';$backendRepo='{backend.as_posix()}';$frontendDir='{frontend.as_posix()}'
$ExpectedMaintenanceCommit='{'f'*40 if fault=='commit' else commits[0]}';$ExpectedApplicationCommit='{commits[1]}';$ExpectedFrontendCommit='{commits[1]}'
$SourceSelectionId='{'invalid selection' if fault=='selection' else 'task-t7-selection'}'
Assert-ReleaseSourceFreeze -VerificationPoint before-build|ConvertTo-Json -Depth 10 -Compress
""")
    assert (result.returncode==0) == (fault is None), result.stderr
    if fault:
        expected={'selection':'SOURCE_SELECTION_INVALID','commit':'SOURCE_APPROVED_COMMIT_MISMATCH','dirty':'SOURCE_DIRTY'}
        assert expected[fault] in result.stderr
    else:
        value=json.loads(result.stdout)
        assert [r['commit'] for r in value['sourceRoots']] == commits


def test_full_package_tested_v2_remains_bound_across_both_promotion_targets(tmp_path):
    root=tmp_path/'release-p3-fixture'
    write_complete_package(root,profile='full',only_office=True)
    operation=tmp_path/'operation.json';_write_operation(operation)
    created=_write_tested_attestation(root,operation)
    assert created.returncode==0,created.stderr
    attestation=json.loads((root/'tested.json').read_text(encoding='utf-8'))
    assert attestation['schemaVersion']=='v2'
    for target in ['prod','backup']:
        accepted=_verify_promotion(root,operation,target)
        assert accepted.returncode==0,accepted.stderr
    manifest=root/'manifest.json'
    value=json.loads(manifest.read_text(encoding='utf-8'))
    value['sourceRoots'][0]['approvedCommit']=value['sourceRoots'][0]['commit']='c'*40
    value['sourceRoles'][0]['commit']='c'*40
    manifest.write_text(json.dumps(value),encoding='utf-8')
    for target in ['prod','backup']:
        rejected=_verify_promotion(root,operation,target)
        assert rejected.returncode!=0 and 'manifestDigest mismatch' in rejected.stderr+rejected.stdout


def test_deployment_function_ast_has_no_database_object_import_or_protected_data_path():
    result=_ps(_functions()+"""
$fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-ReleaseDeploymentExecution'},$true)
if($null -eq $fn){throw 'deployment function missing'}
$commands=@($fn.FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]},$true)|ForEach-Object{$_.Extent.Text})
ConvertTo-Json -InputObject $commands -Compress
""")
    assert result.returncode==0,result.stderr
    commands='\n'.join(json.loads(result.stdout)).lower()
    for forbidden in ['mysqldump','import-remote','reset-db','post-import','mc mirror','infra_file_config','dcc_review_matrix','docker compose down','docker volume rm']:
        assert forbidden not in commands
    assert 'invoke-requireddatabasesqlscripts' in commands


def test_actual_app_release_dispatch_excludes_data_replacement_and_platform_rebuild(deployment_flow):
    """Observe real main-chain calls; fixture-only auxiliary bodies stay explicit.

    SQL, lease fences, durable files, env switch and inner Docker run for real.
    Preprovided uploads, platform prerequisite checks and HTTP/NAS transport
    remain the C6 fixture boundaries, not proof of their internal implementation
    or a real product rollout. No raw command, SQL or lease is serialized.
    """
    flow=deployment_flow
    boundaries=['Write-ReleasePreflightPlan','Assert-RemoteRuntimeDataOnDataDisk','Prepare-RemoteReleaseTree',
        'Copy-DeployControlFilesToServer','Copy-SchedulerSmokeRunnerToServer','Copy-LargeFileToServerInChunks',
        'Copy-RequiredDatabaseSqlScriptsToServer','Copy-ReleaseOpsRuntimePackage','Assert-RemoteRuntimeEnvEdhrEndpoint',
        'Assert-RemoteQuartzSchemaReady','Assert-RemoteShowroomAwardSchemaReady','Assert-RemoteFileStorageConfigRebound',
        'Assert-RemoteBackendContainerMinioReachable','Assert-RemoteSchedulerSmokeRuntime','Wait-RemoteHttpOk',
        'Assert-RemoteBackendHealthStatus','Wait-HttpOk','Wait-HttpContentTypeOk','Read-NasReleaseConfig',
        'Connect-NasReleaseShare','Get-NasReleasePackagePath','Disconnect-NasReleaseShare']
    wrappers='\n'.join(f"$script:t7Auxiliary['{name}']=(Get-Item function:{name}).ScriptBlock\nfunction {name} {{ $script:t7Boundaries+='{name}'; & $script:t7Auxiliary['{name}'] @args }}" for name in boundaries)
    extra=r'''
$script:t7Boundaries=@();$script:t7Sql=@();$script:t7Categories=@();$script:t7Denied=@();$script:t7Auxiliary=@{}
function Assert-T7TransportBoundary {param([string]$Command)
 $category=$null
 if($Command -match '(?i)\bmysqldump\b'){$category='source-database-dump'}
 elseif($Command -match '(?i)\bmc\s+(mirror|cp|rm|mb)\b|docker\s+cp[^\r\n]*minio[^\r\n]*:/data|\bmysql\b[^\r\n]*<[^\r\n]*(db\.sql|reset-db|post-import)|\bcat\b[^\r\n]*(db\.sql|reset-db|post-import)[^\r\n]*\|[^\r\n]*\bmysql\b'){$category='database-or-object-import'}
 elseif($Command -match '(?is)\b(insert\s+into|update|delete\s+from|replace\s+into)\s+`?(infra_file(_config)?|dcc_[a-z_]*(matrix|approval|review)[a-z_]*)\b'){$category='protected-data-write'}
 elseif($Command -match '(?i)\b(mount|umount)\b|docker\s+volume\s+rm|docker\s+compose\s+down|docker\s+compose\s+up[^\r\n]*(\bmysql\b|\bredis\b|\bminio\b)'){$category='platform-rebuild'}
 if($category){$script:t7Denied+=$category;throw ('T7_FORBIDDEN_DISPATCH:'+ $category)}
 if($Command -match "test -f '[^']*/([0-9]{3}\.sql)'"){$script:t7Sql+=$Matches[1]}
 if($Command -match 'docker compose up'){$script:t7Categories+='application-compose'}
}
$script:t7Capture=(Get-Item function:Invoke-SshCapture).ScriptBlock
function Invoke-SshCapture {param([string]$Command,[switch]$IgnoreExitCode)
 Assert-T7TransportBoundary $Command
 & $script:t7Capture -Command $Command -IgnoreExitCode:$IgnoreExitCode
}
$script:t7Command=(Get-Item function:Invoke-SshCommand).ScriptBlock
function Invoke-SshCommand {param([string]$Command)
 # The production call is checked even where the C6 image-upload boundary does
 # not dispatch a docker load: its real content is already in the task engine.
 if($Command.StartsWith('docker load ')){$script:t7Boundaries+='preloaded-image-archive';Assert-T7TransportBoundary $Command}
 & $script:t7Command -Command $Command
}
function Start-Process {throw 'T7_FORBIDDEN_DISPATCH:unexpected-local-process'}
function Write-TargetBoundPostImportSql {throw 'T7_FORBIDDEN_DISPATCH:post-import-builder'}
function New-EdhrProtectedStoragePostImportSql {throw 'T7_FORBIDDEN_DISPATCH:protected-storage-builder'}
function New-ShowroomFileStoragePostImportSql {throw 'T7_FORBIDDEN_DISPATCH:showroom-storage-builder'}
$Mode='build-release';$PublishScope='app-release';$SkipDatabaseSync=$false;$SkipMinioSync=$false
$buildScope=Resolve-EffectiveBuildReleasePublishScope
$script:t7BuildFlags=@([bool]$SkipDatabaseSync,[bool]$SkipMinioSync)
$exportStatements=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and (
 $n.Extent.Text.StartsWith('if ($publishBackend -and -not $SkipDatabaseSync)') -or
 $n.Extent.Text.StartsWith('if ($publishBackend -and $Mode -eq ''build-release'' -and -not $SkipMinioSync)'))
},$true)|Where-Object{
 $parent=$_.Parent;$insideFunction=$false
 while($null -ne $parent){if($parent -is [Management.Automation.Language.FunctionDefinitionAst]){$insideFunction=$true};$parent=$parent.Parent}
 -not $insideFunction
})
if($exportStatements.Count -ne 2){throw 'T7 production data export guards missing'}
foreach($statement in $exportStatements){Invoke-Expression $statement.Extent.Text}
$Mode='deploy-release';$SkipDatabaseSync=$false;$SkipMinioSync=$false
$scopeStatements=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst] -and $n.Extent.Text.StartsWith('if ($releasePublishScope -eq ''app-release'')')},$true))
if($scopeStatements.Count -ne 1){throw 'T7 production deployment scope statement missing'}
Invoke-Expression $scopeStatements[0].Extent.Text
$script:t7DeployFlags=@([bool]$SkipDatabaseSync,[bool]$SkipMinioSync)
foreach($statement in $exportStatements){Invoke-Expression $statement.Extent.Text}
'''+wrappers
    action="""Invoke-ReleaseDeploymentExecution
'T7_CALL_EVIDENCE='+(@{buildFlags=$script:t7BuildFlags;deployFlags=$script:t7DeployFlags;sql=@($script:t7Sql);denied=@($script:t7Denied);categories=@($script:t7Categories);auxiliaryBoundaries=@($script:t7Boundaries)}|ConvertTo-Json -Depth 5 -Compress)
"""
    carrier=flow['package'].parent/'t7-dispatch-carrier.ps1'
    carrier.write_text(flow_script(flow,extra=extra,action=action),encoding='utf-8-sig')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(carrier)],
        capture_output=True,text=True,encoding='utf-8',timeout=240)
    assert result.returncode==0, 'actual deployment call harness failed; inspect redacted task evidence'
    result_lines=result.stdout.splitlines()
    value=json.loads(result_lines[-1])
    assert value['outcome']=='passed', value['outcome']
    trace_lines=[line.removeprefix('T7_CALL_EVIDENCE=') for line in result_lines if line.startswith('T7_CALL_EVIDENCE=')]
    assert len(trace_lines)==1
    trace=json.loads(trace_lines[0])
    assert trace['buildFlags']==trace['deployFlags']==[True,True]
    assert trace['denied']==[]
    assert trace['sql']==[Path(item['file']).name for item in flow['plan']['items'] if item['action']=='APPLY']
    assert trace['categories']==['application-compose']
    assert 'Copy-RequiredDatabaseSqlScriptsToServer' in trace['auxiliaryBoundaries']
    assert 'Assert-RemoteFileStorageConfigRebound' in trace['auxiliaryBoundaries']
    from release_test_runtime import run_mysql
    rows=run_mysql('SELECT value FROM t6_business ORDER BY id;',flow['database'])
    assert rows.returncode==0 and rows.stdout.split()==['first-committed','second-committed']
    (flow['package'].parent/'t7-dispatch-boundary-evidence.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
