param(
    [Parameter(Mandatory=$true)][string]$RuntimeConfigPath,
    [Parameter(Mandatory=$true)][string]$ApplicationBackendRoot
)
$ErrorActionPreference='Stop'
$testEncoding=[Text.UTF8Encoding]::new($false)
[Console]::InputEncoding=$testEncoding;[Console]::OutputEncoding=$testEncoding;$OutputEncoding=$testEncoding
$env:PYTHONUTF8='1'
$env:RELEASE_TEST_MYSQL_RUNTIME_CONFIG=$RuntimeConfigPath
$env:RELEASE_TEST_APPLICATION_BACKEND_ROOT=$ApplicationBackendRoot
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
Set-Location -LiteralPath $root

# Only the shared Python parser reads private configuration. Its CLI emits an
# explicit non-secret whitelist, never Docker Env, credentials or lease tokens.
$preflight=@(& python -X utf8 scripts/tests/release_test_runtime.py --preflight)
if($LASTEXITCODE -ne 0){throw 'Explicit release runtime preflight failed'}
$runtime=($preflight -join "`n")|ConvertFrom-Json
$env:RELEASE_TEST_SMOKE_PAYLOAD_ROOT=[string]$runtime.smokePayload
$evidence=Join-Path ([string]$runtime.taskCache) ('c7-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
[IO.Directory]::CreateDirectory($evidence)|Out-Null
[IO.File]::WriteAllText((Join-Path $evidence 'runtime-before.json'),($runtime|ConvertTo-Json -Depth 20),$testEncoding)
Write-Host "EVIDENCE_DIRECTORY=$evidence"

$modules=@(
 'test_release_migration_supersession_contract.py',
 'test_release_preflight_r20_regressions.py',
 'test_release_migration_preflight_matrix.py',
 'test_release_preflight_plan_order.py',
 'test_release_sql_preflight_gate.py',
 'test_release_build_preflight_cache.py',
 'test_release_schema_rehearsal.py',
 'test_release_package_governance.py',
 'test_release_operation_lock_mysql_behavior.py',
 'test_release_full_package_contract.py',
 'test_app_release_package_governance.py',
 'test_runtime_control_frontend_deploy_contract.py',
 'test_release_digest_vectors.py',
 'test_scheduler_smoke_linux_payload_integration.py',
 'test_release_target_bound_plan.py',
 'test_release_target_data_preflight.py',
 'test_release_readonly_deploy_gate.py',
 'test_release_workflow_preflight.py',
 'test_release_runtime_identity.py',
 'test_release_durable_deployment_evidence.py',
 'test_publish_release_lock_cleanup.py',
 'test_release_deployment_transaction.py',
 'test_release_full_package_mysql_integration.py',
 'test_release_full_package_workflow_integration.py'
)
if($modules.Count -ne 24 -or @($modules|Select-Object -Unique).Count -ne 24){throw 'C7 module inventory must contain exactly 24 unique modules'}
$testPaths=@($modules|ForEach-Object{Join-Path 'scripts/tests' $_})
foreach($path in $testPaths){if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Required test missing: $path"}}
$sourceScope=@('ops/deploy','ops/release','scripts/tests','docs/release-agent-checklist.md','docs/test-release-preflight.md')
$sourcePaths=@(& git -c core.quotepath=false ls-files --cached --others --exclude-standard -- @sourceScope)|Sort-Object -Unique
if($LASTEXITCODE -ne 0 -or $sourcePaths.Count -eq 0){throw 'Cannot inventory actual tracked/untracked test inputs'}
$sourceHashes=[ordered]@{}
foreach($path in $sourcePaths){$sourceHashes[$path]=(Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()}
[IO.File]::WriteAllText((Join-Path $evidence 'source-before.json'),($sourceHashes|ConvertTo-Json -Depth 5),$testEncoding)
$head=(& git rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot read tested Git HEAD'}
$diffHasher="import hashlib,subprocess,sys; print(hashlib.sha256(subprocess.check_output(['git','diff','--binary','HEAD','--',*sys.argv[1:]])).hexdigest())"
$diffBefore=(& python -X utf8 -c $diffHasher @sourceScope).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot hash task diff bytes'}
$applicationRoot=(& git -C $ApplicationBackendRoot rev-parse --show-toplevel).Trim()
if($LASTEXITCODE -ne 0){throw 'Application backend must belong to an actual Git worktree'}
$applicationHead=(& git -C $applicationRoot rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0){throw 'Cannot read application HEAD'}
$applicationStatus=@(& git -C $applicationRoot status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $applicationStatus.Count -ne 0){throw 'Application source input must be clean before C7'}
[IO.File]::WriteAllText((Join-Path $evidence 'application-before.json'),(@{root=$applicationRoot;head=$applicationHead;status=@($applicationStatus)}|ConvertTo-Json -Depth 5),$testEncoding)
$junit=Join-Path $evidence 'pytest.xml'
& python -X utf8 -m pytest -q -x --tb=short @testPaths --basetemp (Join-Path $evidence 'pytest') --junitxml $junit
if($LASTEXITCODE -ne 0){throw "C7 pytest failed; evidence: $evidence"}
if(-not (Test-Path -LiteralPath $junit -PathType Leaf)){throw 'pytest did not produce JUnit'}
[xml]$report=[IO.File]::ReadAllText($junit,$testEncoding)
$cases=@($report.SelectNodes('//testcase'))
if($cases.Count -eq 0 -or @($report.SelectNodes('//failure|//error|//skipped')).Count -ne 0){throw 'JUnit is empty or contains failure/error/skipped'}
foreach($module in $modules){
 $name=[IO.Path]::GetFileNameWithoutExtension($module)
 if(@($cases|Where-Object{[string]$_.classname -match ('(^|\.)'+[regex]::Escape($name)+'(\.|$)')}).Count -eq 0){throw "JUnit missing required module: $module"}
}

& node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs scripts/tests/publish_release_info_contract.test.mjs scripts/tests/publish_image_tar_transfer_contract.test.mjs
if($LASTEXITCODE -ne 0){throw 'Node release contracts failed'}
& powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1
if($LASTEXITCODE -ne 0){throw 'PowerShell digest vector failed'}
foreach($path in @('ops/deploy/publish-int-ruoyi.ps1','ops/deploy/recover-release-operation-lock.ps1','ops/release/lib/ReleaseDeploymentEvidence.psm1')){
 $tokens=$null;$parseErrors=$null
 [Management.Automation.Language.Parser]::ParseFile((Join-Path $root $path),[ref]$tokens,[ref]$parseErrors)|Out-Null
 if($parseErrors.Count){throw "Production AST errors: $path"}
}
& git diff --check
if($LASTEXITCODE -ne 0){throw 'git diff --check failed'}
$sourcePathsAfter=@(& git -c core.quotepath=false ls-files --cached --others --exclude-standard -- @sourceScope)|Sort-Object -Unique
if($LASTEXITCODE -ne 0 -or ($sourcePathsAfter -join "`n") -cne ($sourcePaths -join "`n")){throw 'Source path set changed during validation'}
foreach($path in $sourcePaths){if((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -cne $sourceHashes[$path]){throw "Source changed during validation: $path"}}
$headAfter=(& git rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $headAfter -cne $head){throw 'Git HEAD changed during validation'}
$diffAfter=(& python -X utf8 -c $diffHasher @sourceScope).Trim()
if($LASTEXITCODE -ne 0 -or $diffAfter -cne $diffBefore){throw 'Task diff identity changed during validation'}
$applicationHeadAfter=(& git -C $applicationRoot rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $applicationHeadAfter -cne $applicationHead){throw 'Application HEAD changed during validation'}
$applicationStatusAfter=@(& git -C $applicationRoot status --porcelain --untracked-files=all)
if($LASTEXITCODE -ne 0 -or $applicationStatusAfter.Count -ne 0){throw 'Application source state changed during validation'}
[IO.File]::WriteAllText((Join-Path $evidence 'application-after.json'),(@{root=$applicationRoot;head=$applicationHeadAfter;status=@($applicationStatusAfter)}|ConvertTo-Json -Depth 5),$testEncoding)
$after=@(& python -X utf8 scripts/tests/release_test_runtime.py --preflight)
if($LASTEXITCODE -ne 0){throw 'Final runtime identity preflight failed'}
$runtimeAfter=($after -join "`n")|ConvertFrom-Json
if($runtimeAfter.classic.containerId -cne $runtime.classic.containerId -or $runtimeAfter.mysql.containerId -cne $runtime.mysql.containerId){throw 'Runtime changed during validation'}
foreach($field in @('classicContainers','classicImages','mysqlSchemas','classicFixtureRoots','mysqlFixtureRoots')){
 if((@($runtimeAfter.$field)|Sort-Object|ConvertTo-Json -Compress) -cne (@($runtime.$field)|Sort-Object|ConvertTo-Json -Compress)){throw "Task resource inventory changed: $field"}
}
[IO.File]::WriteAllText((Join-Path $evidence 'runtime-after.json'),($runtimeAfter|ConvertTo-Json -Depth 20),$testEncoding)
$summary=[ordered]@{status='PASS';head=$head;taskDiffSha256=$diffBefore;pytestCount=$cases.Count;pytestModules=$modules;pytestFailures=0;pytestErrors=0;pytestSkipped=0;junitSha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $junit).Hash.ToLowerInvariant();nodeFiles=3;digestVector='PASS';ast='PASS';diffCheck='PASS';sourceUnchanged=$true;sourceFileCount=$sourcePaths.Count;applicationBackendRoot=$ApplicationBackendRoot;applicationGitRoot=$applicationRoot;applicationHead=$applicationHead;applicationClean=$true;javaVerification='C6-J is required separately'}
[IO.File]::WriteAllText((Join-Path $evidence 'summary.json'),($summary|ConvertTo-Json -Depth 10),$testEncoding)
Write-Host "C7 PASS: $($cases.Count) pytest cases; evidence=$evidence; C6-J must be verified separately."
