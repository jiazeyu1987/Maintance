param(
    [ValidateSet('frontend', 'backend', 'full', 'website')]
    [string]$Component,
    [string]$WorktreeName,
    [string]$OperationRecordPath
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'worktree-port-map.ps1')

$InitialRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$EffectiveWorktreeName = if ([string]::IsNullOrWhiteSpace($WorktreeName)) { 'int_main' } else { $WorktreeName }
$PortContext = Get-IntRuoyiWorktreePortContext -WorktreeName $EffectiveWorktreeName -CurrentBackendRepoRoot $InitialRepoRoot
$RepoRoot = $PortContext.BackendPath
$FrontendDir = $PortContext.FrontendPath
$BackendDir = Join-Path $RepoRoot 'yudao-server'
$RuntimeDir = Join-Path $PortContext.WorkspaceRoot "output\runtime\$($PortContext.Name)"
$RuntimeControlStateDir = Join-Path $RepoRoot 'runtime\runtime-control'
$FrontendPort = [int]$PortContext.FrontendPort
$BackendPort = [int]$PortContext.BackendPort
$OnlyOfficeBaseUrl = 'http://127.0.0.1:8080'
$OnlyOfficePublicFileBaseUrl = "http://host.docker.internal:$BackendPort"
$DccSignatureEvidenceHmacSecret = 'CODEX-DCC-E2E-HMAC-SECRET-20260526'
$DccSignatureEvidenceKeyVersion = 'dcc-hmac-v1'
$ShowroomWebsiteReadbackOrigin = 'http://127.0.0.1:4173'
$ShowroomReadbackProbeSiteKey = 'yingtai-showroom'
$ShowroomReadbackProbeStage = 'TEST'
$WebsiteScript = 'D:\ProjectPackage\Website\run-website.bat'
$LocalMysqlContainer = 'int-ruoyi-mysql'
$LocalMysqlDatabase = 'ruoyi-vue-pro'
$LocalMysqlUser = 'root'
$LocalMysqlPassword = '123456'
$LocalMinioContainer = 'docker-minio-1'
$LocalDockerRuntimeHost = '127.0.0.2'
$ProtectedShowroomFileConfigId = 28
$ProtectedShowroomBucket = 'yudao'
$ProtectedShowroomEndpoint = 'http://127.0.0.1:9000'
$ProtectedShowroomDomain = 'http://127.0.0.1:9000/yudao'
$ShowroomMediaSampleObjects = @(
    'showroom/product/cover/20260530/product-product_001-cover.png',
    'showroom/narration/20260522/company-1-zh-ruoxi.wav'
)
$RequiredLocalMySqlMigrations = @(
    [PSCustomObject]@{
        Name = 'System NAS management menu titles'
        ProbeSql = @'
SELECT CASE WHEN (
  SELECT COUNT(*)
  FROM `system_menu`
  WHERE `id` IN (5900, 5901, 5902, 5903)
    AND `deleted` = b'0'
    AND (
      (`id` = 5900 AND `name` = _utf8mb4 0x4e415320e7aea1e79086 AND `component` = 'system/nas/index')
      OR (`id` = 5901 AND `name` = _utf8mb4 0x4e415320e9858de7bdaee69fa5e8afa2 AND `permission` = 'infra:nas:query')
      OR (`id` = 5902 AND `name` = _utf8mb4 0x4e415320e9858de7bdaee4bf9de5ad98 AND `permission` = 'infra:nas:update')
      OR (`id` = 5903 AND `name` = _utf8mb4 0x4e415320e8bf9ee68ea5e6b58be8af95 AND `permission` = 'infra:nas:test')
    )
) = 4 THEN 1 ELSE 0 END;
'@
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260520_system_nas_management_menu.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC NAS transfer async task tables'
        ProbeTable = 'dcc_controlled_file_nas_transfer_task'
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260523_dcc_nas_transfer_task.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC master directory identity'
        ProbeSql = @"
SELECT CASE WHEN
  EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file_master'
      AND COLUMN_NAME = 'directory_id'
  )
  AND EXISTS (
    SELECT 1
    FROM (
      SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS INDEX_COLUMNS
      FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
        AND TABLE_NAME = 'dcc_controlled_file_master'
        AND INDEX_NAME = 'uk_dcc_controlled_file_master_chain'
    ) master_chain_index
    WHERE INDEX_COLUMNS = 'category_id,directory_id,file_name'
  )
THEN 1 ELSE 0 END;
"@
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260614_dcc_master_directory_identity.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC exact NAS identifier collation'
        ProbeSql = @"
SELECT CASE WHEN
  EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file_nas_transfer_task_item'
      AND COLUMN_NAME = 'nas_path'
      AND COLLATION_NAME = 'utf8mb4_bin'
  )
  AND EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file_master'
      AND COLUMN_NAME = 'file_name'
      AND COLLATION_NAME = 'utf8mb4_bin'
  )
  AND EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file'
      AND COLUMN_NAME = 'file_name'
      AND COLLATION_NAME = 'utf8mb4_bin'
  )
THEN 1 ELSE 0 END;
"@
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260530_dcc_exact_nas_identifier_collation.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC NAS local folder import source fields'
        ProbeSql = @"
SELECT CASE WHEN
  EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file_nas_transfer_task'
      AND COLUMN_NAME = 'source_type'
  )
  AND EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_controlled_file_nas_transfer_task_item'
      AND COLUMN_NAME = 'source_file_id'
  )
THEN 1 ELSE 0 END;
"@
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260613_dcc_nas_local_folder_import.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC NAS local folder resumable chunk upload table'
        ProbeTable = 'dcc_controlled_file_local_folder_upload_chunk'
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260615_dcc_local_folder_chunk_upload.sql'
    },
    [PSCustomObject]@{
        Name = 'DCC tenant-scoped code indexes'
        ProbeSql = @"
SELECT CASE WHEN
  EXISTS (
    SELECT 1
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_file_category'
      AND INDEX_NAME = 'uk_dcc_file_category_tenant_code'
  )
  AND EXISTS (
    SELECT 1
    FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = '$LocalMysqlDatabase'
      AND TABLE_NAME = 'dcc_approval_position'
      AND INDEX_NAME = 'uk_dcc_approval_position_tenant_code'
  )
THEN 1 ELSE 0 END;
"@
        ScriptPath = Join-Path $RepoRoot 'sql\mysql\20260530_dcc_tenant_scoped_code_indexes.sql'
    }
)
$RequiredDccDownloadEncryptionEnv = @(
    'DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION',
    'DCC_DOWNLOAD_ENCRYPTION_KEY_ID',
    'DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY',
    'DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY'
)

function Fail([string]$Message) {
    Update-OperationRecord -Status 'failed' -Summary $Message
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    exit 1
}

function Update-OperationRecord {
    param(
        [string]$Status,
        [string]$Summary
    )
    if ([string]::IsNullOrWhiteSpace($OperationRecordPath) -or -not (Test-Path -LiteralPath $OperationRecordPath)) {
        return
    }
    $json = Get-Content -LiteralPath $OperationRecordPath -Encoding UTF8 -Raw
    $record = $json | ConvertFrom-Json
    $record.status = $Status
    $record.summary = $Summary
    $payload = $record | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($OperationRecordPath, $payload, [System.Text.UTF8Encoding]::new($false))
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        if ($Name -eq 'npm') {
            Fail 'Missing npm command'
        }
        if ($Name -eq 'java') {
            Fail 'Missing java command'
        }
        if ($Name -eq 'mvn') {
            Fail 'Missing mvn command'
        }
        if ($Name -eq 'pnpm') {
            Fail 'Missing pnpm command'
        }
        Fail "Missing $Name command"
    }
}

function Import-PersistentEnvironmentVariable([string]$Name) {
    foreach ($target in @(
        [System.EnvironmentVariableTarget]::Process,
        [System.EnvironmentVariableTarget]::User,
        [System.EnvironmentVariableTarget]::Machine
    )) {
        $value = [Environment]::GetEnvironmentVariable($Name, $target)
        if ([string]::IsNullOrWhiteSpace($value)) {
            continue
        }
        [Environment]::SetEnvironmentVariable($Name, $value, [System.EnvironmentVariableTarget]::Process)
        return $true
    }
    return $false
}

function Require-EnvironmentVariable([string]$Name) {
    if (-not (Import-PersistentEnvironmentVariable $Name)) {
        Fail "Missing $Name; DCC controlled download encryption is fail-fast and requires explicit runtime configuration."
    }
}

function Require-RunningContainer([string]$Name) {
    $running = docker inspect -f '{{.State.Running}}' $Name 2>$null
    if ($LASTEXITCODE -ne 0 -or $running.Trim() -ne 'true') {
        Fail "Required Docker container is not running: $Name"
    }
}

function Wait-WebsiteReadbackReady {
    param(
        [int]$TimeoutSeconds = 180
    )

    $WebsiteCurrentUrl = "$ShowroomWebsiteReadbackOrigin/showroom/sites/$ShowroomReadbackProbeSiteKey/stages/$ShowroomReadbackProbeStage/release/current"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = 'unknown error'

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $WebsiteCurrentUrl -TimeoutSec 5 -Headers @{
                Accept = 'application/json'
                'Cache-Control' = 'no-cache'
            }
            $contentType = [string]$response.Headers['Content-Type']
            if ($response.StatusCode -eq 200 -and $contentType.ToLowerInvariant().Contains('application/json')) {
                return
            }
            $lastError = "unexpected response status/content-type: $($response.StatusCode) / $contentType"
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Seconds 2
    }

    Fail "$WebsiteCurrentUrl did not become ready within $TimeoutSeconds seconds. Last error: $lastError"
}

function Invoke-ProcessWithCapture {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$InputText
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.CreateNoWindow = $true
    $startInfo.Arguments = [string]::Join(' ', ($Arguments | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + ($_ -replace '"', '\"') + '"'
        } else {
            $_
        }
    }))

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    try {
        if ($null -ne $InputText) {
            $inputBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($InputText)
            $process.StandardInput.BaseStream.Write($inputBytes, 0, $inputBytes.Length)
        }
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        $exitCode = $process.ExitCode
    } finally {
        $process.Dispose()
    }

    return [PSCustomObject]@{
        ExitCode = $exitCode
        StdOut = $stdout
        StdErr = $stderr
    }
}

function Invoke-LocalMySqlCommand {
    param(
        [string[]]$MySqlArguments,
        [string]$InputText
    )

    Require-Command 'docker'
    Require-RunningContainer $LocalMysqlContainer
    $dockerArguments = @('exec')
    if ($null -ne $InputText) {
        $dockerArguments += '-i'
    }
    $dockerArguments += @(
        $LocalMysqlContainer,
        'mysql',
        "-u$LocalMysqlUser",
        "-p$LocalMysqlPassword",
        '--default-character-set=utf8mb4',
        '-D',
        $LocalMysqlDatabase
    ) + $MySqlArguments

    $result = Invoke-ProcessWithCapture -FilePath 'docker' -Arguments $dockerArguments -InputText $InputText
    if ($result.ExitCode -ne 0) {
        $errorText = if ($result.StdErr) { $result.StdErr.Trim() } else { $result.StdOut.Trim() }
        Fail "Local MySQL command failed: $errorText"
    }
    return $result.StdOut
}

function Test-LocalTableExists([string]$TableName) {
    $sql = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$LocalMysqlDatabase' AND table_name='$TableName';"
    $stdout = Invoke-LocalMySqlCommand -MySqlArguments @('-N', '-e', $sql)
    return $stdout.Trim() -eq '1'
}

function Test-LocalSqlProbe([string]$Sql) {
    $stdout = Invoke-LocalMySqlCommand -MySqlArguments @('-N', '-B') -InputText $Sql
    $probeLines = @($stdout -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    return $probeLines -contains '1'
}

function Invoke-LocalSqlScript([string]$ScriptPath) {
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        Fail "Missing local SQL migration: $ScriptPath"
    }
    $sqlText = [System.IO.File]::ReadAllText($ScriptPath, [System.Text.UTF8Encoding]::new($false))
    [void](Invoke-LocalMySqlCommand -MySqlArguments @() -InputText $sqlText)
}

function Ensure-RequiredLocalMySqlSchema {
    foreach ($migration in $RequiredLocalMySqlMigrations) {
        $probePassed = $false
        if ($migration.PSObject.Properties.Name -contains 'ProbeTable') {
            $probePassed = Test-LocalTableExists $migration.ProbeTable
        } elseif ($migration.PSObject.Properties.Name -contains 'ProbeSql') {
            $probePassed = Test-LocalSqlProbe $migration.ProbeSql
        } else {
            Fail "Local schema migration has no probe: $($migration.Name)"
        }
        if ($probePassed) {
            continue
        }
        Invoke-LocalSqlScript $migration.ScriptPath
        if ($migration.PSObject.Properties.Name -contains 'ProbeTable') {
            $probePassed = Test-LocalTableExists $migration.ProbeTable
        } else {
            $probePassed = Test-LocalSqlProbe $migration.ProbeSql
        }
        if (-not $probePassed) {
            Fail "Local schema migration probe still failed after applying $($migration.Name): $($migration.ScriptPath)"
        }
    }
}

function Assert-LocalShowroomFileConfigProtected {
    $configSql = @"
SELECT
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(config, '$.bucket')), ''),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(config, '$.endpoint')), ''),
  COALESCE(JSON_UNQUOTE(JSON_EXTRACT(config, '$.domain')), '')
FROM infra_file_config
WHERE id = $ProtectedShowroomFileConfigId
  AND deleted = 0;
"@
    $configOutput = (Invoke-LocalMySqlCommand -MySqlArguments @('-N', '-B', '-e', $configSql)).Trim()
    if ([string]::IsNullOrWhiteSpace($configOutput)) {
        Fail "SHOWROOM_FILE_CONFIG_PROTECTED: infra_file_config.id=$ProtectedShowroomFileConfigId is missing"
    }
    $configColumns = $configOutput -replace "`r", '' -split "`t"
    if ($configColumns.Count -lt 3) {
        Fail "SHOWROOM_FILE_CONFIG_PROTECTED: unexpected config row for infra_file_config.id=$ProtectedShowroomFileConfigId -> $configOutput"
    }
    $actualBucket = $configColumns[0].Trim()
    $actualEndpoint = $configColumns[1].Trim()
    $actualDomain = $configColumns[2].Trim()
    if ($actualBucket -ne $ProtectedShowroomBucket -or
        $actualEndpoint -ne $ProtectedShowroomEndpoint -or
        $actualDomain -ne $ProtectedShowroomDomain) {
        Fail ("SHOWROOM_FILE_CONFIG_PROTECTED: infra_file_config.id={0} expected bucket={1}, endpoint={2}, domain={3}; actual bucket={4}, endpoint={5}, domain={6}" -f
            $ProtectedShowroomFileConfigId, $ProtectedShowroomBucket, $ProtectedShowroomEndpoint, $ProtectedShowroomDomain,
            $actualBucket, $actualEndpoint, $actualDomain)
    }

    $showroomUrlSql = @"
SELECT COUNT(*)
FROM infra_file
WHERE deleted = 0
  AND config_id = $ProtectedShowroomFileConfigId
  AND path LIKE 'showroom/%'
  AND (
    url IS NULL
    OR url = ''
    OR url NOT LIKE '$ProtectedShowroomDomain/%'
  );
"@
    $mismatchCount = (Invoke-LocalMySqlCommand -MySqlArguments @('-N', '-B', '-e', $showroomUrlSql)).Trim()
    if ([string]::IsNullOrWhiteSpace($mismatchCount)) {
        Fail "SHOWROOM_MEDIA_URL_PROTECTED: could not verify showroom media URLs for config $ProtectedShowroomFileConfigId"
    }
    if ([int]$mismatchCount -gt 0) {
        Fail ("SHOWROOM_MEDIA_URL_PROTECTED: found {0} showroom media rows outside protected domain {1}" -f
            [int]$mismatchCount, $ProtectedShowroomDomain)
    }
}

function Assert-LocalMinioObjectExists {
    param(
        [string]$Bucket,
        [string]$ObjectPath
    )
    $containerPath = "/data/$Bucket/$ObjectPath"
    & docker exec $LocalMinioContainer sh -lc "test -f '$containerPath' || test -f '$containerPath/xl.meta'" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Fail "Showroom media bucket consistency check failed: master bucket '$Bucket' is missing object '$ObjectPath' in MinIO container '$LocalMinioContainer'."
    }
}

function Assert-LocalShowroomMediaBucketConsistency {
    Require-RunningContainer $LocalMinioContainer
    $configJson = (Invoke-LocalMySqlCommand -MySqlArguments @(
        '-N',
        '-B',
        '-e',
        'SELECT config FROM infra_file_config WHERE master = 1 AND deleted = 0 LIMIT 1'
    )).Trim()
    if ([string]::IsNullOrWhiteSpace($configJson)) {
        Fail 'Showroom media bucket consistency check failed: missing master infra_file_config row.'
    }
    try {
        $config = $configJson | ConvertFrom-Json
    } catch {
        Fail "Showroom media bucket consistency check failed: master infra_file_config config is not valid JSON. $($_.Exception.Message)"
    }
    $bucket = [string]$config.bucket
    if ([string]::IsNullOrWhiteSpace($bucket)) {
        Fail 'Showroom media bucket consistency check failed: master infra_file_config config has no bucket.'
    }

    foreach ($objectPath in $ShowroomMediaSampleObjects) {
        Assert-LocalMinioObjectExists -Bucket $bucket -ObjectPath $objectPath
    }
}

function Stop-Port([int]$Port) {
    $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($owner in $owners) {
        if ($owner -and $owner -ne $PID) {
            Stop-Process -Id ([int]$owner) -Force -ErrorAction SilentlyContinue
        }
    }
}

function Stop-MatchingProcesses([string]$Label, [string]$CommandFragment) {
    $matches = Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.CommandLine -and
            $_.CommandLine.Contains($CommandFragment)
        } |
        Sort-Object ProcessId -Unique

    foreach ($process in $matches) {
        Stop-Process -Id ([int]$process.ProcessId) -Force -ErrorAction SilentlyContinue
    }
}

function Assert-LocalDockerRuntimePortRoute {
    param(
        [string]$Name,
        [int]$Port
    )

    $connection = Test-NetConnection -ComputerName $LocalDockerRuntimeHost -Port $Port -WarningAction SilentlyContinue
    if (-not $connection.TcpTestSucceeded) {
        Fail "LOCAL_DOCKER_PORT_SHADOWED: $Name port $Port is not reachable on $LocalDockerRuntimeHost. Local backend must use the unshadowed Docker loopback host instead of 127.0.0.1."
    }
}

function Start-Frontend {
    Require-Command 'pnpm'
    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules'))) {
        Fail "Missing frontend node_modules: $FrontendDir"
    }
    if (-not (Test-Path -LiteralPath $RuntimeDir)) {
        New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
    }
    Stop-MatchingProcesses 'frontend' $FrontendDir
    Stop-Port $FrontendPort
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $frontendScript = @"
`$env:VITE_PORT = '$FrontendPort'
`$env:VITE_OPEN = 'false'
`$env:VITE_BASE_URL = 'http://127.0.0.1:$BackendPort'
`$env:VITE_PROXY_TARGET = 'http://127.0.0.1:$BackendPort'
pnpm dev -- --strictPort
"@
    $frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendScript))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-EncodedCommand', $frontendEncoded
    ) -WorkingDirectory $FrontendDir `
      -RedirectStandardOutput (Join-Path $RuntimeDir "frontend-runtime-control-$timestamp.out.log") `
      -RedirectStandardError (Join-Path $RuntimeDir "frontend-runtime-control-$timestamp.err.log") `
      -WindowStyle Hidden
}

function Start-Backend {
    Require-Command 'java'
    Require-Command 'mvn'
    foreach ($requiredEnv in $RequiredDccDownloadEncryptionEnv) {
        Require-EnvironmentVariable $requiredEnv
    }
    if (-not (Test-Path -LiteralPath (Join-Path $BackendDir 'pom.xml'))) {
        Fail "Missing backend workspace: $BackendDir"
    }
    if (-not (Test-Path -LiteralPath $RuntimeDir)) {
        New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
    }
    Ensure-RequiredLocalMySqlSchema
    Assert-LocalShowroomFileConfigProtected
    Assert-LocalShowroomMediaBucketConsistency
    Assert-LocalDockerRuntimePortRoute -Name 'MySQL' -Port 23306
    Assert-LocalDockerRuntimePortRoute -Name 'Redis' -Port 26379
    Stop-MatchingProcesses 'backend' $RuntimeDir
    Stop-Port $BackendPort
    & mvn -pl yudao-server -am -DskipTests package
    if ($LASTEXITCODE -ne 0) {
        Fail 'Backend package failed'
    }
    $sourceJar = Join-Path $BackendDir 'target\yudao-server.jar'
    if (-not (Test-Path -LiteralPath $sourceJar)) {
        Fail "Missing backend jar after package: $sourceJar"
    }
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $runtimeJar = Join-Path $RuntimeDir "backend-runtime-control-$timestamp.jar"
    Copy-Item -LiteralPath $sourceJar -Destination $runtimeJar -Force
    Stop-Port $BackendPort
    $backendScript = @"
`$env:DCC_ONLYOFFICE_BASE_URL = '$OnlyOfficeBaseUrl'
`$env:DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL = '$OnlyOfficePublicFileBaseUrl'
`$env:DCC_SIGNATURE_EVIDENCE_HMAC_SECRET = '$DccSignatureEvidenceHmacSecret'
`$env:DCC_SIGNATURE_EVIDENCE_KEY_VERSION = '$DccSignatureEvidenceKeyVersion'
`$backendArgs = @(
  "-jar"
  "$runtimeJar"
  "--server.port=$BackendPort"
  "--spring.profiles.active=local"
  "--spring.datasource.dynamic.datasource.master.url=jdbc:mysql://${LocalDockerRuntimeHost}:23306/ruoyi-vue-pro?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&nullCatalogMeansCurrent=true"
  "--spring.datasource.dynamic.datasource.master.username=root"
  "--spring.datasource.dynamic.datasource.master.password=123456"
  "--spring.datasource.dynamic.datasource.slave.url=jdbc:mysql://${LocalDockerRuntimeHost}:23306/ruoyi-vue-pro?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&rewriteBatchedStatements=true&nullCatalogMeansCurrent=true"
  "--spring.datasource.dynamic.datasource.slave.username=root"
  "--spring.datasource.dynamic.datasource.slave.password=123456"
  "--spring.data.redis.host=$LocalDockerRuntimeHost"
  "--spring.data.redis.port=26379"
  "--yudao.runtime-control.repo-root=$RepoRoot"
  "--yudao.runtime-control.state-dir=$RuntimeControlStateDir"
)
& java @backendArgs
"@
    $backendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendScript))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-EncodedCommand', $backendEncoded
    ) -WorkingDirectory $RepoRoot -RedirectStandardOutput (Join-Path $RuntimeDir "backend-runtime-control-$timestamp.out.log") `
        -RedirectStandardError (Join-Path $RuntimeDir "backend-runtime-control-$timestamp.err.log") `
        -WindowStyle Hidden
}

function Start-Website {
    Require-Command 'npm'
    if (-not (Test-Path -LiteralPath $WebsiteScript)) {
        Fail "Missing Website startup script: $WebsiteScript"
    }
    if (-not (Test-Path -LiteralPath 'D:\ProjectPackage\Website\node_modules')) {
        Fail 'Missing Website node_modules: D:\ProjectPackage\Website'
    }
    Stop-Port 4173
    $websiteScriptBlock = @"
`$env:WEBSITE_RUNTIME_MODE = 'preview'
& '$WebsiteScript'
"@
    $websiteEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($websiteScriptBlock))
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-EncodedCommand', $websiteEncoded
    ) -WorkingDirectory 'D:\ProjectPackage\Website' -WindowStyle Hidden
    Wait-WebsiteReadbackReady
}

if ([string]::IsNullOrWhiteSpace($Component)) {
    Fail 'Missing Component'
}

Update-OperationRecord -Status 'running' -Summary "Restarting local $Component for $($PortContext.Name) on $FrontendPort/$BackendPort"

switch ($Component) {
    'frontend' { Start-Frontend }
    'backend' { Start-Backend }
    'full' {
        Start-Backend
        Start-Frontend
    }
    'website' { Start-Website }
}

Update-OperationRecord -Status 'succeeded' -Summary "Restart command dispatched for local $Component ($($PortContext.Name), frontend=$FrontendPort, backend=$BackendPort)"
Write-Host "Restart command dispatched for local $Component ($($PortContext.Name), frontend=$FrontendPort, backend=$BackendPort)"
