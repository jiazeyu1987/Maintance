param(
    [ValidateSet('direct', 'build-release', 'deploy-release', 'mark-tested')]
    [string]$Mode = 'direct',
    [ValidateSet('full', 'intruoyi', 'backend', 'frontend', 'website')]
    [string]$Component = 'full',
    [string]$ReleaseTag = '',
    [string]$NasConfigPath = '',
    [string]$NasReleaseRoot = 'Backup/ReleasePackage',
    [string]$NasServer = '172.30.30.4',
    [string]$NasShare = '',
    [switch]$RequireTested,
    [string]$OperatorName = $env:USERNAME,
    [string]$TestConclusion = '',
    [string]$SelectedRecoverySetCandidateId = '',
    [string]$RecoverySetId = '',
    [string]$RecoverySetManifestHash = '',
    [string]$RecoverySetProgramVersion = '',
    [string]$RecoverySetRedisPolicy = '',
    [ValidateSet('test', 'prod', 'backup')]
    [string]$Environment = 'test',
    [string]$ConfirmText = '',
    [string]$ProdDryRunEvidencePath = '',
    [string]$ServerHost = '',
    [string]$TestServerHost = $env:RUNTIME_CONTROL_TEST_SERVER_HOST,
    [string]$ProdServerHost = $env:RUNTIME_CONTROL_PROD_SERVER_HOST,
    [string]$BackupServerHost = $env:RUNTIME_CONTROL_BACKUP_SERVER_HOST,
    [string]$ServerUser = 'root',
    [string]$RemoteAppDir = '/opt/intruoyi/runtime',
    [string]$RemoteReleaseRoot = '/var/lib/docker/intruoyi-releases',
    [string]$RemoteDataRoot = '/var/lib/docker/intruoyi-data/runtime-data',
    [string]$RemoteDataDiskMount = '/var/lib/docker',
    [string]$RemoteDataDiskDevice = '/dev/vdb',
    [int]$FrontendPort = 8081,
    [int]$BackendPort = 48081,
    [int]$WebsiteHostPort = 8083,
    [int]$OnlyOfficeHostPort = 8080,
    [string]$ShowroomSiteKey = 'yingtai-showroom',
    [string]$ShowroomStage = 'TEST',
    [string]$LocalMySqlContainer = 'int-ruoyi-mysql',
    [string]$LocalMinioContainer = 'docker-minio-1',
    [string]$RemoteMinioContainer = '',
    [string]$WebsiteRepo = $env:INT_RUOYI_WEBSITE_REPO,
    [string]$BackendRepoRoot = $env:INT_RUOYI_BACKEND_REPO,
    [string]$FrontendRepoRoot = $env:INT_RUOYI_FRONTEND_REPO,
    [string]$Tag = '',
    [string]$DccSignatureEvidenceHmacSecret = $env:DCC_SIGNATURE_EVIDENCE_HMAC_SECRET,
    [string]$DccSignatureEvidenceKeyVersion = $env:DCC_SIGNATURE_EVIDENCE_KEY_VERSION,
    [string]$EdhrS3Endpoint = $env:EDHR_S3_ENDPOINT,
    [string]$EdhrS3Bucket = $env:EDHR_S3_BUCKET,
    [string]$EdhrS3Region = $env:EDHR_S3_REGION,
    [string]$EdhrS3AccessKey = $env:EDHR_S3_ACCESS_KEY,
    [string]$EdhrS3SecretKey = $env:EDHR_S3_SECRET_KEY,
    [string]$EdhrS3RetentionMode = $env:EDHR_S3_RETENTION_MODE,
    [string]$EdhrS3RetainUntilDays = $env:EDHR_S3_RETAIN_UNTIL_DAYS,
    [string]$EdhrS3RequireLegalHold = $env:EDHR_S3_REQUIRE_LEGAL_HOLD,
    [string]$DccViewerTokenHmacSecret = $env:DCC_VIEWER_TOKEN_HMAC_SECRET,
    [string]$DccOnlyOfficeJwtSecret = $env:DCC_ONLYOFFICE_JWT_SECRET,
    [string]$DccOnlyOfficeBaseUrl = $env:DCC_ONLYOFFICE_BASE_URL,
    [string]$DccOnlyOfficePublicFileBaseUrl = $env:DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL,
    [string]$DccDownloadEncryptionPolicyVersion = $env:DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION,
    [string]$DccDownloadEncryptionKeyId = $env:DCC_DOWNLOAD_ENCRYPTION_KEY_ID,
    [string]$DccDownloadEncryptionBase64Key = $env:DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY,
    [string]$DccDownloadEncryptionArtifactDirectory = $env:DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY,
    [string]$DccProjectCodeCodexCliCommand = $env:DCC_PROJECT_CODE_CODEX_CLI_COMMAND,
    [string]$DccProjectCodeCodexHome = $env:DCC_PROJECT_CODE_CODEX_HOME,
    [string]$DccProjectCodeCodexTimeoutSeconds = $env:DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS,
    [string]$DccProjectCodeRecognitionWorkerCount = $env:DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT,
    [string]$LocalCacheRoot = $env:INTRUOYI_LOCAL_CACHE_ROOT,
    [ValidateSet('offline-tar')]
    [string]$BackendRuntimeBaseMode = $env:INTRUOYI_BACKEND_RUNTIME_BASE_MODE,
    [string]$BackendRuntimeBaseTarPath = $env:INTRUOYI_BACKEND_RUNTIME_BASE_TAR,
    [string]$BackendRuntimeBaseTarSha256 = $env:INTRUOYI_BACKEND_RUNTIME_BASE_TAR_SHA256,
    [string]$BackendRuntimeBaseImage = $env:INTRUOYI_BACKEND_RUNTIME_BASE_IMAGE,
    [string]$BackendRuntimeBaseDigest = $env:INTRUOYI_BACKEND_RUNTIME_BASE_DIGEST,
    [string]$BackendRuntimeBaseVersion = $env:INTRUOYI_BACKEND_RUNTIME_BASE_VERSION,
    [switch]$IncludeOnlyOffice,
    [switch]$SkipDatabaseSync,
    [switch]$SkipMinioSync,
    [switch]$EnableSmartReleaseReport,
    [string]$SmartReleaseBaselineManifestPath = $env:INTRUOYI_SMART_RELEASE_BASELINE_MANIFEST_PATH,
    [string]$SmartReleaseLocalDatabaseConfigPath = $env:INTRUOYI_SMART_RELEASE_LOCAL_DATABASE_CONFIG_PATH,
    [string]$SmartReleaseDataOwnershipRegistryPath = $env:INTRUOYI_SMART_RELEASE_DATA_OWNERSHIP_REGISTRY_PATH,
    [string]$SmartReleaseTargetConfigPath = $env:INTRUOYI_SMART_RELEASE_TARGET_CONFIG_PATH
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
$PSNativeCommandUseErrorActionPreference = $false
}
$script:ReleaseOperationLockHeld = $false
$script:ReleaseOperationLockReleasing = $false
$script:BuildReleaseRuntimeRestartGuardCreated = $false

function Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
    if ($script:ReleaseOperationLockHeld -and -not $script:ReleaseOperationLockReleasing) {
        try {
            $script:ReleaseOperationLockReleasing = $true
            Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $Message
        } catch {
        } finally {
            $script:ReleaseOperationLockHeld = $false
            $script:ReleaseOperationLockReleasing = $false
        }
    }
    exit 1
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Write-Utf8LfNoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalized = ($Content -replace "`r`n", "`n" -replace "`r", "`n")
    [System.IO.File]::WriteAllText($Path, $normalized, [System.Text.UTF8Encoding]::new($false))
}

function ConvertTo-ReleaseUnicodeText {
    param(
        [Parameter(Mandatory = $true)]
        [int[]]$CodePoints
    )

    return (-join ($CodePoints | ForEach-Object { [char]$_ }))
}

function New-ReleaseDockerBuildContext {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContextRoot,
        [Parameter(Mandatory = $true)]
        [string]$BackendRepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$FrontendRepoRoot,
        [Parameter(Mandatory = $true)]
        [bool]$IncludeBackend,
        [Parameter(Mandatory = $true)]
        [bool]$IncludeFrontend,
        [Parameter(Mandatory = $true)]
        [string]$BackendJarPath
    )

    if (Test-Path -LiteralPath $ContextRoot) {
        Remove-Item -LiteralPath $ContextRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $ContextRoot | Out-Null

    if ($IncludeBackend) {
        $backendJarTargetDir = Join-Path $ContextRoot 'ruoyi-vue-pro\yudao-server\target'
        $backendJarTargetPath = Join-Path $backendJarTargetDir 'yudao-server-exec.jar'
        New-Item -ItemType Directory -Force -Path $backendJarTargetDir | Out-Null
        Copy-Item -LiteralPath $BackendJarPath -Destination (Join-Path $backendJarTargetDir 'yudao-server-exec.jar') -Force
        if (-not (Test-Path -LiteralPath $backendJarTargetPath -PathType Leaf)) {
            Fail "Backend exec jar missing from Docker build context: $backendJarTargetPath"
        }
    }

    if ($IncludeFrontend) {
        $nginxTargetDir = Join-Path $ContextRoot 'ruoyi-vue-pro\script\deploy\int-ruoyi-test'
        New-Item -ItemType Directory -Force -Path $nginxTargetDir | Out-Null
        Copy-Item -LiteralPath (Join-Path $BackendRepoRoot 'script\deploy\int-ruoyi-test\nginx.conf') -Destination (Join-Path $nginxTargetDir 'nginx.conf') -Force

        $frontendDistSource = Join-Path $FrontendRepoRoot 'dist-intruoyi-test'
        if (-not (Test-Path -LiteralPath $frontendDistSource -PathType Container)) {
            Fail "Frontend build output missing for Docker build context: $frontendDistSource"
        }
        $frontendRepoTarget = Join-Path $ContextRoot 'yudao-ui-admin-vue3'
        New-Item -ItemType Directory -Force -Path $frontendRepoTarget | Out-Null
        Copy-Item -LiteralPath $frontendDistSource -Destination $frontendRepoTarget -Recurse -Force
    }
}

function Remove-ReleaseDockerBuildContextFromPackage {
    if (-not (Test-Path -LiteralPath $dockerBuildContextRoot)) {
        return
    }

    Info 'Removing Docker build context from final release package'
    Remove-Item -LiteralPath $dockerBuildContextRoot -Recurse -Force
    if (Test-Path -LiteralPath $dockerBuildContextRoot) {
        Fail "Release package still contains docker-build-context: $dockerBuildContextRoot"
    }
}

function Resolve-LocalCacheRoot([string]$ConfiguredRoot) {
    $defaultLocalCacheRoot = 'E:\Int\CacheData\IntRuoyi'
    $effectiveRoot = if ([string]::IsNullOrWhiteSpace($ConfiguredRoot)) {
        $defaultLocalCacheRoot
    } else {
        $ConfiguredRoot.Trim()
    }

    try {
        $resolvedRoot = [System.IO.Path]::GetFullPath($effectiveRoot)
    } catch {
        Fail "Invalid local cache root: $effectiveRoot. $($_.Exception.Message)"
    }

    try {
        New-Item -ItemType Directory -Force -Path $resolvedRoot | Out-Null
    } catch {
        Fail "Local cache root is required but cannot be created: $resolvedRoot. $($_.Exception.Message)"
    }
    return $resolvedRoot
}

function Enter-BuildReleaseRuntimeRestartGuard {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GuardFile
    )

    if ($Mode -ne 'build-release') {
        return
    }
    if (Test-Path -LiteralPath $GuardFile) {
        Info "build-release runtime guard already exists: $GuardFile"
        return
    }

    $guardDir = Split-Path -Parent $GuardFile
    if (-not [string]::IsNullOrWhiteSpace($guardDir)) {
        New-Item -ItemType Directory -Force -Path $guardDir | Out-Null
    }
    $guardContent = "build-release runtime guard active: pid=$PID releaseTag=$ReleaseTag mode=$Mode"
    [System.IO.File]::WriteAllText($GuardFile, $guardContent, [System.Text.UTF8Encoding]::new($false))
    $script:BuildReleaseRuntimeRestartGuardCreated = $true
    Info "build-release runtime guard created: $GuardFile"
}

function Exit-BuildReleaseRuntimeRestartGuard {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GuardFile
    )

    if ($Mode -eq 'build-release' -and $script:BuildReleaseRuntimeRestartGuardCreated -and (Test-Path -LiteralPath $GuardFile)) {
        Remove-Item -LiteralPath $GuardFile -Force
        Info "build-release runtime guard released: $GuardFile"
    }
    $script:BuildReleaseRuntimeRestartGuardCreated = $false
}

$DCC_HARDCODED_SIGNATURE_EVIDENCE_HMAC_SECRET = 'INTRUOYI-DCC-HARDCODED-SIGNATURE-EVIDENCE-HMAC-20260601'
$DCC_HARDCODED_SIGNATURE_EVIDENCE_KEY_VERSION = 'dcc-hardcoded-signature-20260601'
$DCC_HARDCODED_VIEWER_TOKEN_HMAC_SECRET = 'INTRUOYI-DCC-HARDCODED-VIEWER-TOKEN-HMAC-20260601'
$DCC_HARDCODED_ONLYOFFICE_JWT_SECRET = 'INTRUOYI-DCC-HARDCODED-ONLYOFFICE-JWT-20260601'
$DCC_HARDCODED_DOWNLOAD_ENCRYPTION_POLICY_VERSION = 'dcc-hardcoded-policy-v1'
$DCC_HARDCODED_DOWNLOAD_ENCRYPTION_KEY_ID = 'dcc-hardcoded-key-20260601'
$DCC_HARDCODED_DOWNLOAD_ENCRYPTION_BASE64_KEY = 'MDEyMzQ1Njc4OUFCQ0RFRjAxMjM0NTY3ODlBQkNERUY='
$DCC_HARDCODED_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY = 'dcc/download-encrypted-artifacts'

function Require-ConfiguredTargetServerHost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [AllowNull()]
        [string]$Value,
        [Parameter(Mandatory = $true)]
        [string]$ArgumentName
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        Fail "Missing $ArgumentName; release target host for environment '$TargetEnvironment' must be configured and passed explicitly so package URLs and storage checks are bound to the selected publish target."
    }
    return $Value.Trim()
}

function Assert-ReleaseTargetServerHostsConfigured {
    $script:TestServerHost = Require-ConfiguredTargetServerHost -TargetEnvironment 'test' -Value $TestServerHost -ArgumentName '-TestServerHost'
    $script:BackupServerHost = Require-ConfiguredTargetServerHost -TargetEnvironment 'backup' -Value $BackupServerHost -ArgumentName '-BackupServerHost'
    if ($Environment -eq 'prod') {
        $script:ProdServerHost = Require-ConfiguredTargetServerHost -TargetEnvironment 'prod' -Value $ProdServerHost -ArgumentName '-ProdServerHost'
    } elseif (-not [string]::IsNullOrWhiteSpace($ProdServerHost)) {
        $script:ProdServerHost = $ProdServerHost.Trim()
    }
}

function Resolve-PublishTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )

    switch ($TargetEnvironment) {
        'test' {
            return @{
                ServerHost = $TestServerHost
                DisplayName = 'test'
                RemoteMinioContainer = 'ragflow_compose-minio-1'
            }
        }
        'prod' {
            return @{
                ServerHost = $ProdServerHost
                DisplayName = 'production'
                RemoteMinioContainer = 'ragflow_compose-minio-1'
            }
        }
        'backup' {
            return @{
                ServerHost = $BackupServerHost
                DisplayName = 'backup'
                RemoteMinioContainer = 'intruoyi-minio'
            }
        }
        default {
            Fail "Unsupported publish environment: $TargetEnvironment"
        }
    }
}

if ($Mode -in @('build-release', 'deploy-release')) {
    Assert-ReleaseTargetServerHostsConfigured
}

$publishTarget = Resolve-PublishTarget -TargetEnvironment $Environment
if ([string]::IsNullOrWhiteSpace($ServerHost)) {
    $ServerHost = $publishTarget.ServerHost
}
if ($Mode -ne 'mark-tested' -and [string]::IsNullOrWhiteSpace($ServerHost)) {
    Fail "Missing -ServerHost; release target host for environment '$Environment' must be configured by runtime-control or passed explicitly."
}
if (-not [string]::IsNullOrWhiteSpace($ServerHost)) {
    $ServerHost = $ServerHost.Trim()
}
if ([string]::IsNullOrWhiteSpace($RemoteMinioContainer) -and $publishTarget.ContainsKey('RemoteMinioContainer')) {
    $RemoteMinioContainer = $publishTarget.RemoteMinioContainer
}
$PublishTargetName = $publishTarget.DisplayName

if (@('prod', 'backup') -contains $Environment -and $ConfirmText -ne 'PROD') {
    Fail "Explicit confirmation required for production-grade publish: -ConfirmText PROD"
}

function Remove-SshNoise([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ''
    }
    return (($Text -split "`r?`n") | Where-Object {
        $_ -and $_ -notlike 'close - IO is still pending on closed socket.*'
    }) -join "`n"
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "Missing command: $Name"
    }
}

function Get-SshCommonOptions {
    return @(
        '-o', 'BatchMode=yes',
        '-o', 'ConnectTimeout=10',
        '-o', 'ConnectionAttempts=1',
        '-o', 'ServerAliveInterval=10',
        '-o', 'ServerAliveCountMax=3',
        '-o', 'StrictHostKeyChecking=no'
    )
}

function New-SshArgumentList {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    return @('-n') + (Get-SshCommonOptions) + @(
        "$ServerUser@$ServerHost",
        $Command
    )
}

function New-ScpArgumentList {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LocalPath,
        [Parameter(Mandatory = $true)]
        [string]$RemotePath,
        [switch]$Recursive
    )

    $args = @(Get-SshCommonOptions)
    if ($Recursive) {
        $args += '-r'
    }
    return $args + @($LocalPath, "${ServerUser}@${ServerHost}:${RemotePath}")
}

function Invoke-ProcessCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $null
    )

    $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("publish-int-ruoyi-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    $stdoutPath = Join-Path $tempDir 'stdout.log'
    $stderrPath = Join-Path $tempDir 'stderr.log'
    try {
        $effectiveWorkingDirectory = if ($WorkingDirectory) { $WorkingDirectory } else { (Get-Location).Path }
        $resolvedCommand = Get-Command $FilePath -ErrorAction SilentlyContinue
        $effectiveFilePath = $FilePath
        $effectiveArguments = @($ArgumentList)
        if ($resolvedCommand) {
            $resolvedSource = if ($resolvedCommand.Source) { $resolvedCommand.Source } else { $resolvedCommand.Path }
            if ($resolvedSource) {
                if ($resolvedSource.ToLower().EndsWith('.ps1')) {
                    $cmdSibling = [System.IO.Path]::ChangeExtension($resolvedSource, '.cmd')
                    if (Test-Path -LiteralPath $cmdSibling) {
                        $effectiveFilePath = 'cmd.exe'
                        $effectiveArguments = @('/c', $cmdSibling) + $ArgumentList
                    } else {
                        $effectiveFilePath = 'powershell.exe'
                        $effectiveArguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $resolvedSource) + $ArgumentList
                    }
                } elseif ($resolvedSource.ToLower().EndsWith('.cmd') -or $resolvedSource.ToLower().EndsWith('.bat')) {
                    $effectiveFilePath = 'cmd.exe'
                    $effectiveArguments = @('/c', $resolvedSource) + $ArgumentList
                } else {
                    $effectiveFilePath = $resolvedSource
                }
            }
        }
        $process = Start-Process -FilePath $effectiveFilePath `
            -ArgumentList $effectiveArguments `
            -WorkingDirectory $effectiveWorkingDirectory `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -NoNewWindow `
            -Wait `
            -PassThru
        $stdout = if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw -ErrorAction SilentlyContinue } else { '' }
        $stderr = if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw -ErrorAction SilentlyContinue } else { '' }
        return @{
            ExitCode = $process.ExitCode
            StdOut = $stdout
            StdErr = $stderr
        }
    } finally {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Resolve-SmartReleaseReportOnlyEnabled {
    if ($EnableSmartReleaseReport) {
        return $true
    }

    $envValue = [string]$env:INTRUOYI_SMART_RELEASE_REPORT_ONLY
    if ([string]::IsNullOrWhiteSpace($envValue)) {
        return $false
    }

    $normalizedValue = $envValue.Trim()
    if ($normalizedValue -eq '1') {
        return $true
    }
    if ($normalizedValue -eq '0') {
        return $false
    }

    Fail "Invalid INTRUOYI_SMART_RELEASE_REPORT_ONLY: $envValue. Use 1 to enable report-only or unset the variable."
}

function Resolve-SmartReleaseInputFilePath {
    param(
        [AllowNull()]
        [string]$PathValue,
        [Parameter(Mandatory = $true)]
        [string]$ArgumentName
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        Fail "Missing $ArgumentName; Smart Release report-only requires explicit local input files."
    }

    $fullPath = [System.IO.Path]::GetFullPath($PathValue.Trim())
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        Fail "$ArgumentName does not exist: $fullPath"
    }
    return $fullPath
}

function New-SmartReleaseReportDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath
    )

    if ([string]::IsNullOrWhiteSpace($PackagePath)) {
        Fail 'Missing PackagePath; Smart Release report-only requires a release package directory.'
    }

    $packageFullPath = [System.IO.Path]::GetFullPath($PackagePath)
    if (-not (Test-Path -LiteralPath $packageFullPath -PathType Container)) {
        Fail "PackagePath does not exist: $packageFullPath"
    }

    $reportDirectory = Join-Path $packageFullPath 'smart-release-report'
    New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null
    return $reportDirectory
}

function Invoke-SmartReleaseReportProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentList,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedOutputPath,
        [Parameter(Mandatory = $true)]
        [string]$ReportName
    )

    if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
        Fail "Smart Release report script missing: $ScriptPath"
    }

    $result = Invoke-ProcessCapture -FilePath 'powershell.exe' -ArgumentList (@(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        $ScriptPath
    ) + $ArgumentList)
    $cleanOutput = Remove-SshNoise (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($cleanOutput) {
        Info "Smart Release $ReportName output: $cleanOutput"
    }
    if (-not (Test-Path -LiteralPath $ExpectedOutputPath -PathType Leaf)) {
        Fail "Smart Release $ReportName did not write required report: $ExpectedOutputPath"
    }
    return $result
}

function Invoke-SmartReleaseBuildReportOnly {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath
    )

    $baselineManifestPath = Resolve-SmartReleaseInputFilePath -PathValue $SmartReleaseBaselineManifestPath -ArgumentName '-SmartReleaseBaselineManifestPath'
    $localDatabaseConfigPath = Resolve-SmartReleaseInputFilePath -PathValue $SmartReleaseLocalDatabaseConfigPath -ArgumentName '-SmartReleaseLocalDatabaseConfigPath'
    $dataOwnershipRegistryPath = Resolve-SmartReleaseInputFilePath -PathValue $SmartReleaseDataOwnershipRegistryPath -ArgumentName '-SmartReleaseDataOwnershipRegistryPath'
    $reportDirectory = New-SmartReleaseReportDirectory -PackagePath $PackagePath
    $releaseScriptRoot = Join-Path $backendRepo 'script\release'

    $manifestValidationOutputPath = Join-Path $reportDirectory 'manifest-validation-result.json'
    $manifestValidationResult = Invoke-SmartReleaseReportProcess `
        -ScriptPath (Join-Path $releaseScriptRoot 'validate-release-manifest.ps1') `
        -ArgumentList @('-PackagePath', $PackagePath, '-Mode', 'report-only', '-OutputPath', $manifestValidationOutputPath) `
        -ExpectedOutputPath $manifestValidationOutputPath `
        -ReportName 'manifest validation'
    if ($manifestValidationResult.ExitCode -ne 0) {
        Info "Smart Release manifest validation report-only completed with exit code $($manifestValidationResult.ExitCode); legacy build-release flow continues because the report was written."
    }

    $intakeOutputDir = Join-Path $reportDirectory 'intake'
    $intakeResultPath = Join-Path $intakeOutputDir 'intake-result.json'
    $intakeResult = Invoke-SmartReleaseReportProcess `
        -ScriptPath (Join-Path $releaseScriptRoot 'run-release-intake.ps1') `
        -ArgumentList @(
            '-RepoRoot', $backendRepo,
            '-BaselineManifestPath', $baselineManifestPath,
            '-LocalDatabaseConfigPath', $localDatabaseConfigPath,
            '-DataOwnershipRegistryPath', $dataOwnershipRegistryPath,
            '-OutputDir', $intakeOutputDir,
            '-Mode', 'report-only'
        ) `
        -ExpectedOutputPath $intakeResultPath `
        -ReportName 'intake'
    if ($intakeResult.ExitCode -ne 0) {
        Info "Smart Release intake report-only completed with exit code $($intakeResult.ExitCode); legacy build-release flow continues because the report was written."
    }
}

function Invoke-SmartReleaseDeployPrecheckReportOnly {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath
    )

    $targetConfigPath = Resolve-SmartReleaseInputFilePath -PathValue $SmartReleaseTargetConfigPath -ArgumentName '-SmartReleaseTargetConfigPath'
    $reportDirectory = New-SmartReleaseReportDirectory -PackagePath $PackagePath
    $deployPrecheckOutputPath = Join-Path $reportDirectory 'deploy-precheck-result.json'
    $releaseScriptRoot = Join-Path $backendRepo 'script\release'

    $precheckResult = Invoke-SmartReleaseReportProcess `
        -ScriptPath (Join-Path $releaseScriptRoot 'run-deploy-precheck-report.ps1') `
        -ArgumentList @('-PackagePath', $PackagePath, '-Environment', $Environment, '-TargetConfigPath', $targetConfigPath, '-Mode', 'report-only', '-OutputPath', $deployPrecheckOutputPath) `
        -ExpectedOutputPath $deployPrecheckOutputPath `
        -ReportName 'deploy precheck'
    if ($precheckResult.ExitCode -ne 0) {
        Fail "SMART_RELEASE_DEPLOY_PRECHECK_FAILED: deploy precheck report-only failed with exit code $($precheckResult.ExitCode). Report: $deployPrecheckOutputPath"
    }

    Write-Host "[FAIL] SMART_RELEASE_REPORT_ONLY_DEPLOY_STOP: Smart Release deploy report-only completed; real deploy was not executed. Report: $deployPrecheckOutputPath" -ForegroundColor Red
    exit 2
}

function ConvertTo-ProcessArgumentString {
    param(
        [string[]]$Arguments = @()
    )

    $escaped = New-Object System.Collections.Generic.List[string]
    foreach ($argument in @($Arguments)) {
        $value = [string]$argument
        if ($value.Length -gt 0 -and $value -notmatch '[\s"]') {
            $escaped.Add($value)
            continue
        }
        $builder = New-Object System.Text.StringBuilder
        [void]$builder.Append('"')
        $backslashes = 0
        foreach ($char in $value.ToCharArray()) {
            if ($char -eq '\') {
                $backslashes++
                continue
            }
            if ($char -eq '"') {
                [void]$builder.Append('\' * (($backslashes * 2) + 1))
                [void]$builder.Append('"')
                $backslashes = 0
                continue
            }
            if ($backslashes -gt 0) {
                [void]$builder.Append('\' * $backslashes)
                $backslashes = 0
            }
            [void]$builder.Append($char)
        }
        if ($backslashes -gt 0) {
            [void]$builder.Append('\' * ($backslashes * 2))
        }
        [void]$builder.Append('"')
        $escaped.Add($builder.ToString())
    }
    return ($escaped -join ' ')
}

function Invoke-ProcessCaptureWithInput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$StandardInput = '',
        [string]$WorkingDirectory = $null
    )

    $effectiveWorkingDirectory = if ($WorkingDirectory) { $WorkingDirectory } else { (Get-Location).Path }
    $resolvedCommand = Get-Command $FilePath -ErrorAction SilentlyContinue
    $effectiveFilePath = if ($resolvedCommand -and $resolvedCommand.Source) {
        $resolvedCommand.Source
    } elseif ($resolvedCommand -and $resolvedCommand.Path) {
        $resolvedCommand.Path
    } else {
        $FilePath
    }

    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $effectiveFilePath
    $processInfo.WorkingDirectory = $effectiveWorkingDirectory
    $processInfo.UseShellExecute = $false
    $processInfo.RedirectStandardInput = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    $processInfo.StandardOutputEncoding = $utf8NoBom
    $processInfo.StandardErrorEncoding = $utf8NoBom
    if ($null -ne $processInfo.ArgumentList) {
        foreach ($argument in @($ArgumentList)) {
            [void]$processInfo.ArgumentList.Add($argument)
        }
    } else {
        $processInfo.Arguments = ConvertTo-ProcessArgumentString -Arguments $ArgumentList
    }

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    [void]$process.Start()
    if ($null -ne $StandardInput) {
        $process.StandardInput.Write($StandardInput)
    }
    $process.StandardInput.Close()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    return @{
        ExitCode = $process.ExitCode
        StdOut = $stdout
        StdErr = $stderr
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $null
    )

    Info ("Run: {0} {1}" -f $FilePath, ($ArgumentList -join ' '))
    $previous = Get-Location
    try {
        if ($WorkingDirectory) {
            Set-Location -LiteralPath $WorkingDirectory
        }
        $result = Invoke-ProcessCapture -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory ((Get-Location).Path)
        $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
        $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
        $cleanOutput = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
        if ($cleanOutput) {
            Write-Host $cleanOutput
        }
        if ($result.ExitCode -ne 0) {
            Fail "Command failed with exit code $($result.ExitCode): $FilePath`n$cleanOutput"
        }
    } finally {
        if ($WorkingDirectory) {
            Set-Location -LiteralPath $previous
        }
    }
}

function Invoke-CheckedShell {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [string]$DisplayCommand = $null,
        [string]$WorkingDirectory = $null
    )

    $safeDisplayCommand = if ([string]::IsNullOrWhiteSpace($DisplayCommand)) { $Command } else { $DisplayCommand }
    Info "Run shell: $safeDisplayCommand"
    $previous = Get-Location
    try {
        if ($WorkingDirectory) {
            Set-Location -LiteralPath $WorkingDirectory
        }
        Invoke-Expression $Command
        if ($LASTEXITCODE -ne 0) {
            Fail "Shell command failed with exit code $LASTEXITCODE"
        }
    } finally {
        if ($WorkingDirectory) {
            Set-Location -LiteralPath $previous
        }
    }
}

function Invoke-FrontendViteBuild {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FrontendDir
    )

    Invoke-CheckedCommand -FilePath 'pnpm' -ArgumentList @('build:test') -WorkingDirectory $FrontendDir
}

function Assert-FrontendBuildStaticAssetContract {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FrontendDir
    )

    $distDir = Join-Path $FrontendDir 'dist-intruoyi-test'
    $indexPath = Join-Path $distDir 'index.html'
    if (-not (Test-Path -LiteralPath $indexPath)) {
        Fail "Frontend build output missing: $indexPath"
    }

    $html = [System.IO.File]::ReadAllText($indexPath, [System.Text.UTF8Encoding]::new($false))
    if ($html.Contains('/admin-ui-vue3/assets/') -or $html.Contains('/admin-ui-vue3/pdfjs/') -or $html.Contains('/admin-ui-vue3/favicon.ico') -or $html.Contains('/admin-ui-vue3/logo.gif')) {
        Fail 'Frontend build index must use VITE_BASE_PATH=/ for this Nginx root deployment; found /admin-ui-vue3/ static asset references.'
    }

    $references = [regex]::Matches($html, '(?:src|href)="([^"]+\.(?:js|mjs|css|ico|gif|png|svg))"')
    if ($references.Count -eq 0) {
        Fail "Frontend build index references no static JS/CSS assets: $indexPath"
    }

    foreach ($reference in $references) {
        $assetUri = $reference.Groups[1].Value
        if ($assetUri -match '^https?://') {
            continue
        }
        if (-not $assetUri.StartsWith('/')) {
            Fail "Frontend static asset reference must be root-relative: $assetUri"
        }
        $assetRelativePath = $assetUri.TrimStart('/').Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $assetPath = Join-Path $distDir $assetRelativePath
        if (-not (Test-Path -LiteralPath $assetPath)) {
            Fail "Referenced frontend static asset missing: $assetUri ($assetPath)"
        }
    }
}

function New-ReleaseChangeSetManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )

    $releasePackageLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(21457, 24067, 21253)
    $componentScopeLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(32452, 20214, 33539, 22260)
    $fullWidthColon = ConvertTo-ReleaseUnicodeText -CodePoints @(65306)

    return [ordered]@{
        summary = "Release package $PackageTag"
        component = $Component
        items = @(
            ('{0}{1}{2}' -f $releasePackageLabel, $fullWidthColon, $PackageTag)
            ('{0}{1}{2}' -f $componentScopeLabel, $fullWidthColon, $Component)
        )
        includeShowroomBuildPackage = [bool]$publishWebsite
        includeOnlyOffice = [bool]$IncludeOnlyOffice
    }
}

function Write-FrontendReleaseInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FrontendDir,
        [Parameter(Mandatory = $true)]
        [string]$PackageTag,
        [Parameter(Mandatory = $true)]
        [array]$SourceRepos
    )

    $distDir = Join-Path $FrontendDir 'dist-intruoyi-test'
    if (-not (Test-Path -LiteralPath $distDir -PathType Container)) {
        Fail "Frontend release info target dist missing: $distDir"
    }

    $releaseInfo = [ordered]@{
        releaseTag = $PackageTag
        packageId = $packageDirectoryName
        createdAt = (Get-Date).ToUniversalTime().ToString('o')
        publishScope = if ($SkipDatabaseSync -and $SkipMinioSync) { 'code-only' } else { 'with-data' }
        changeSet = New-ReleaseChangeSetManifest -PackageTag $PackageTag
        sourceRepos = $SourceRepos
    }
    $json = $releaseInfo | ConvertTo-Json -Depth 12
    $targetPath = Join-Path $distDir 'release-info.json'
    [System.IO.File]::WriteAllText($targetPath, $json, [System.Text.UTF8Encoding]::new($false))
    Info "Frontend release info written: $targetPath"
}

function Resolve-BackendRuntimeBaseConfig {
    if (-not $publishBackend -or $Mode -eq 'deploy-release' -or $Mode -eq 'mark-tested') {
        return $null
    }

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseMode)) {
        Fail 'Missing BackendRuntimeBaseMode; backend runtime base image distribution mode is required.'
    }
    $mode = $BackendRuntimeBaseMode.Trim()
    if ($mode -ne 'offline-tar') {
        Fail "Unsupported BackendRuntimeBaseMode: $mode. Only offline-tar is supported."
    }

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseTarPath)) {
        Fail 'Missing BackendRuntimeBaseTarPath; backend image packaging requires an internal runtime base image tar.'
    }
    $tarPath = $BackendRuntimeBaseTarPath.Trim()
    if (-not (Test-Path -LiteralPath $tarPath -PathType Leaf)) {
        Fail "BackendRuntimeBaseTarPath not found: $tarPath"
    }
    $resolvedTarPath = (Resolve-Path -LiteralPath $tarPath).Path

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseTarSha256)) {
        Fail 'Missing BackendRuntimeBaseTarSha256; backend runtime base tar integrity is required.'
    }
    $tarSha256 = $BackendRuntimeBaseTarSha256.Trim().ToLowerInvariant()
    if ($tarSha256 -notmatch '^[0-9a-f]{64}$') {
        Fail "BackendRuntimeBaseTarSha256 must be a 64-character SHA256 hex value: $BackendRuntimeBaseTarSha256"
    }

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseImage)) {
        Fail 'Missing BackendRuntimeBaseImage; backend Docker build requires the internal runtime base image tag.'
    }
    $image = $BackendRuntimeBaseImage.Trim()
    if ($image -notmatch '^[A-Za-z0-9][A-Za-z0-9._/:@-]*$') {
        Fail "BackendRuntimeBaseImage contains unsupported characters: $image"
    }

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseDigest)) {
        Fail 'Missing BackendRuntimeBaseDigest; backend runtime base image id is required.'
    }
    $digest = $BackendRuntimeBaseDigest.Trim().ToLowerInvariant()
    if ($digest -notmatch '^sha256:[0-9a-f]{64}$') {
        Fail "BackendRuntimeBaseDigest must be a docker image id formatted as sha256:<64 hex>: $BackendRuntimeBaseDigest"
    }

    if ([string]::IsNullOrWhiteSpace($BackendRuntimeBaseVersion)) {
        Fail 'Missing BackendRuntimeBaseVersion; backend runtime base version must be recorded in the release manifest.'
    }
    $version = $BackendRuntimeBaseVersion.Trim()
    if ($version -notmatch '^[A-Za-z0-9._-]+$') {
        Fail "BackendRuntimeBaseVersion contains unsupported characters: $version"
    }

    return [ordered]@{
        Mode = $mode
        TarPath = $resolvedTarPath
        TarSha256 = $tarSha256
        Image = $image
        Digest = $digest
        Version = $version
    }
}

function Assert-BackendRuntimeBaseImageAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Config
    )

    $actualTarSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $config.TarPath).Hash.ToLowerInvariant()
    if ($actualTarSha256 -ne $config.TarSha256) {
        Fail "Backend runtime base tar sha256 mismatch: expected $($config.TarSha256), got $actualTarSha256 ($($config.TarPath))"
    }

    Info "Loading backend runtime base image: $($config.TarPath)"
    Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('load', '-i', $config.TarPath)

    $inspectResult = Invoke-ProcessCapture -FilePath 'docker' -ArgumentList @('image', 'inspect', $config.Image, '--format', '{{.Id}}')
    $inspectOutput = Remove-SshNoise (($inspectResult.StdOut + "`n" + $inspectResult.StdErr).Trim())
    if ($inspectResult.ExitCode -ne 0) {
        Fail "Cannot inspect backend runtime base image: $($config.Image)`n$inspectOutput"
    }
    $actualImageId = (($inspectResult.StdOut -split "`r?`n") | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_)
    } | Select-Object -First 1).Trim().ToLowerInvariant()
    if ($actualImageId -ne $config.Digest) {
        Fail "Backend runtime base image id mismatch: expected $($config.Digest), got $actualImageId ($($config.Image))"
    }
}

function Get-ProcessLockHintForPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        $escapedPath = [System.Management.ManagementObjectSearcher]::new(
            "SELECT ProcessId, Name, CommandLine FROM Win32_Process"
        ).Get() | Where-Object {
            $commandLine = [string]$_.CommandLine
            -not [string]::IsNullOrWhiteSpace($commandLine) -and
                $commandLine.IndexOf($Path, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        } | Select-Object -First 5 | ForEach-Object {
            "pid=$($_.ProcessId) name=$($_.Name)"
        }
        if ($escapedPath) {
            return " Possible locking process: $($escapedPath -join '; ')."
        }
    } catch {
        return ''
    }
    return ''
}

function Assert-BackendJarAvailableForMavenClean {
    param(
        [Parameter(Mandatory = $true)]
        [string]$JarPath
    )

    if (-not (Test-Path -LiteralPath $JarPath -PathType Leaf)) {
        return
    }

    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $JarPath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
    } catch {
        $lockHint = Get-ProcessLockHintForPath -Path $JarPath
        Fail "Backend jar is locked before Maven clean: $JarPath.$lockHint Restart the local backend with restart-ruoyi-backend.bat so it runs from a copied runtime jar, then retry build-release."
    } finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function Invoke-SshCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $normalizedCommand = $Command -replace "`r`n", "`n" -replace "`r", "`n"
    Info ("Run: ssh {0}" -f ((New-SshArgumentList -Command $normalizedCommand) -join ' '))
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (New-SshArgumentList -Command $normalizedCommand)
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $text = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    if ($text) {
        Write-Host $text
    }
    if ($result.ExitCode -ne 0) {
        throw "Command failed with exit code $($result.ExitCode): ssh`n$text"
    }
}

function Invoke-SshCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [switch]$IgnoreExitCode
    )

    $normalizedCommand = $Command -replace "`r`n", "`n" -replace "`r", "`n"
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (New-SshArgumentList -Command $normalizedCommand)
    $exitCode = $result.ExitCode
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $text = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    if ($exitCode -ne 0 -and -not $IgnoreExitCode) {
        throw "SSH command failed ($exitCode): $normalizedCommand`n$text"
    }
    return @{
        Ok = ($exitCode -eq 0)
        Output = $text
        ExitCode = $exitCode
    }
}

function Test-RemoteFileExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $result = Invoke-SshCapture -Command "test -f '$Path'" -IgnoreExitCode
    return $result.Ok
}

function Get-RemoteComposeServices {
    $result = Invoke-SshCapture -Command "cd '$RemoteAppDir' && docker compose config --services"
    $services = @(
        $result.Output -split "`r?`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($services.Count -eq 0) {
        Fail "Remote compose declares no services: $remoteCompose"
    }
    return $services
}

function Get-RemoteRuntimeEnvMap {
    if (-not (Test-RemoteFileExists -Path $remoteEnv)) {
        return @{}
    }
    $result = Invoke-SshCapture -Command "cat '$remoteEnv'"
    $map = @{}
    foreach ($line in ($result.Output -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith('#')) {
            continue
        }
        $separatorIndex = $line.IndexOf('=')
        if ($separatorIndex -lt 1) {
            continue
        }
        $key = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1)
        if (-not [string]::IsNullOrWhiteSpace($key)) {
            $map[$key] = $value
        }
    }
    return $map
}

function Test-RemoteComposeService {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Services,
        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    return ($Services -contains $ServiceName)
}

function Assert-RemoteComposeService {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Services,
        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    if (-not (Test-RemoteComposeService -Services $Services -ServiceName $ServiceName)) {
        Fail "Release compose is missing required service: $ServiceName"
    }
}

function Get-LocalContainerEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContainerName,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $output = & docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $ContainerName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Fail "Unable to inspect local container env: $ContainerName`n$($output | Out-String)"
    }
    foreach ($line in $output) {
        if ($line -like "$Key=*") {
            return $line.Substring($Key.Length + 1)
        }
    }
    return ''
}

function Get-RemoteContainerEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContainerName,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $result = Invoke-SshCapture -Command "docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $ContainerName"
    foreach ($line in ($result.Output -split "`r?`n")) {
        if ($line -like "$Key=*") {
            return $line.Substring($Key.Length + 1)
        }
    }
    return ''
}

function Get-EdhrProtectedStorageSettings {
    return @{
        EDHR_S3_ENDPOINT = $EdhrS3Endpoint
        EDHR_S3_BUCKET = $EdhrS3Bucket
        EDHR_S3_REGION = $EdhrS3Region
        EDHR_S3_ACCESS_KEY = $EdhrS3AccessKey
        EDHR_S3_SECRET_KEY = $EdhrS3SecretKey
        EDHR_S3_RETENTION_MODE = $EdhrS3RetentionMode
        EDHR_S3_RETAIN_UNTIL_DAYS = $EdhrS3RetainUntilDays
        EDHR_S3_REQUIRE_LEGAL_HOLD = $EdhrS3RequireLegalHold
    }
}

function Resolve-PublishRuntimeValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [AllowNull()]
        [string]$CurrentValue,
        [AllowNull()]
        [string]$HardcodedValue = ''
    )

    if (-not [string]::IsNullOrWhiteSpace($CurrentValue)) {
        return $CurrentValue.Trim()
    }
    foreach ($target in @(
        [System.EnvironmentVariableTarget]::Process,
        [System.EnvironmentVariableTarget]::User,
        [System.EnvironmentVariableTarget]::Machine
    )) {
        $value = [Environment]::GetEnvironmentVariable($Name, $target)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($HardcodedValue)) {
        return $HardcodedValue.Trim()
    }
    return ''
}

function Get-PublishRuntimeEnvironmentValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    foreach ($target in @(
        [System.EnvironmentVariableTarget]::Process,
        [System.EnvironmentVariableTarget]::User,
        [System.EnvironmentVariableTarget]::Machine
    )) {
        $value = [Environment]::GetEnvironmentVariable($Name, $target)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
    }
    return ''
}

$script:EdhrTargetSpecificEnvironmentNames = @(
    'EDHR_S3_TEST_ENDPOINT',
    'EDHR_S3_TEST_BUCKET',
    'EDHR_S3_TEST_REGION',
    'EDHR_S3_TEST_ACCESS_KEY',
    'EDHR_S3_TEST_SECRET_KEY',
    'EDHR_S3_TEST_RETENTION_MODE',
    'EDHR_S3_TEST_RETAIN_UNTIL_DAYS',
    'EDHR_S3_TEST_REQUIRE_LEGAL_HOLD',
    'EDHR_S3_BACKUP_ENDPOINT',
    'EDHR_S3_BACKUP_BUCKET',
    'EDHR_S3_BACKUP_REGION',
    'EDHR_S3_BACKUP_ACCESS_KEY',
    'EDHR_S3_BACKUP_SECRET_KEY',
    'EDHR_S3_BACKUP_RETENTION_MODE',
    'EDHR_S3_BACKUP_RETAIN_UNTIL_DAYS',
    'EDHR_S3_BACKUP_REQUIRE_LEGAL_HOLD',
    'EDHR_S3_PROD_ENDPOINT',
    'EDHR_S3_PROD_BUCKET',
    'EDHR_S3_PROD_REGION',
    'EDHR_S3_PROD_ACCESS_KEY',
    'EDHR_S3_PROD_SECRET_KEY',
    'EDHR_S3_PROD_RETENTION_MODE',
    'EDHR_S3_PROD_RETAIN_UNTIL_DAYS',
    'EDHR_S3_PROD_REQUIRE_LEGAL_HOLD'
)

function Get-TargetSpecificEdhrEnvName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not $Name.StartsWith('EDHR_S3_')) {
        return ''
    }
    $target = $TargetEnvironment.Trim().ToUpperInvariant()
    if ($target -notin @('TEST', 'PROD', 'BACKUP')) {
        return ''
    }
    $suffix = $Name.Substring('EDHR_S3_'.Length)
    return "EDHR_S3_${target}_${suffix}"
}

function Resolve-TargetPublishRuntimeValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [AllowNull()]
        [string]$CurrentValue,
        [AllowNull()]
        [string]$HardcodedValue = ''
    )

    $targetSpecificName = Get-TargetSpecificEdhrEnvName -TargetEnvironment $TargetEnvironment -Name $Name
    $targetSpecificValue = if ([string]::IsNullOrWhiteSpace($targetSpecificName)) {
        ''
    } else {
        Get-PublishRuntimeEnvironmentValue -Name $targetSpecificName
    }
    $genericEnvironmentValue = Get-PublishRuntimeEnvironmentValue -Name $Name
    if (-not [string]::IsNullOrWhiteSpace($targetSpecificValue)) {
        if ([string]::IsNullOrWhiteSpace($CurrentValue)) {
            return $targetSpecificValue
        }
        if (-not [string]::IsNullOrWhiteSpace($genericEnvironmentValue) -and
            $CurrentValue.Trim() -eq $genericEnvironmentValue) {
            return $targetSpecificValue
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($CurrentValue)) {
        return $CurrentValue.Trim()
    }
    if (-not [string]::IsNullOrWhiteSpace($targetSpecificValue)) {
        return $targetSpecificValue
    }
    if (-not [string]::IsNullOrWhiteSpace($genericEnvironmentValue)) {
        return $genericEnvironmentValue
    }
    if (-not [string]::IsNullOrWhiteSpace($HardcodedValue)) {
        return $HardcodedValue.Trim()
    }
    return ''
}

function Set-PublishRuntimeDefaultsForTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetServerHost,
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )

    $script:DccSignatureEvidenceHmacSecret = Resolve-PublishRuntimeValue `
        -Name 'DCC_SIGNATURE_EVIDENCE_HMAC_SECRET' `
        -CurrentValue $script:DccSignatureEvidenceHmacSecret `
        -HardcodedValue $DCC_HARDCODED_SIGNATURE_EVIDENCE_HMAC_SECRET
    $script:DccSignatureEvidenceKeyVersion = Resolve-PublishRuntimeValue `
        -Name 'DCC_SIGNATURE_EVIDENCE_KEY_VERSION' `
        -CurrentValue $script:DccSignatureEvidenceKeyVersion `
        -HardcodedValue $DCC_HARDCODED_SIGNATURE_EVIDENCE_KEY_VERSION
    $script:DccViewerTokenHmacSecret = Resolve-PublishRuntimeValue `
        -Name 'DCC_VIEWER_TOKEN_HMAC_SECRET' `
        -CurrentValue $script:DccViewerTokenHmacSecret `
        -HardcodedValue $DCC_HARDCODED_VIEWER_TOKEN_HMAC_SECRET
    $script:DccOnlyOfficeJwtSecret = Resolve-PublishRuntimeValue `
        -Name 'DCC_ONLYOFFICE_JWT_SECRET' `
        -CurrentValue $script:DccOnlyOfficeJwtSecret `
        -HardcodedValue $DCC_HARDCODED_ONLYOFFICE_JWT_SECRET
    $script:DccOnlyOfficeBaseUrl = Resolve-PublishRuntimeValue `
        -Name 'DCC_ONLYOFFICE_BASE_URL' `
        -CurrentValue $script:DccOnlyOfficeBaseUrl `
        -HardcodedValue "http://${TargetServerHost}:$OnlyOfficeHostPort"
    $script:DccOnlyOfficePublicFileBaseUrl = Resolve-PublishRuntimeValue `
        -Name 'DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL' `
        -CurrentValue $script:DccOnlyOfficePublicFileBaseUrl `
        -HardcodedValue "http://host.docker.internal:$BackendPort"
    $script:DccDownloadEncryptionPolicyVersion = Resolve-PublishRuntimeValue `
        -Name 'DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION' `
        -CurrentValue $script:DccDownloadEncryptionPolicyVersion `
        -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_POLICY_VERSION
    $script:DccDownloadEncryptionKeyId = Resolve-PublishRuntimeValue `
        -Name 'DCC_DOWNLOAD_ENCRYPTION_KEY_ID' `
        -CurrentValue $script:DccDownloadEncryptionKeyId `
        -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_KEY_ID
    $script:DccDownloadEncryptionBase64Key = Resolve-PublishRuntimeValue `
        -Name 'DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY' `
        -CurrentValue $script:DccDownloadEncryptionBase64Key `
        -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_BASE64_KEY
    $script:DccDownloadEncryptionArtifactDirectory = Resolve-PublishRuntimeValue `
        -Name 'DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY' `
        -CurrentValue $script:DccDownloadEncryptionArtifactDirectory `
        -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY

    $script:EdhrS3Endpoint = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ENDPOINT' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3Endpoint
    $script:EdhrS3Bucket = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_BUCKET' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3Bucket
    $script:EdhrS3Region = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REGION' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3Region
    $script:EdhrS3AccessKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ACCESS_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3AccessKey
    $script:EdhrS3SecretKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_SECRET_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3SecretKey
    $script:EdhrS3RetentionMode = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETENTION_MODE' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3RetentionMode
    $script:EdhrS3RetainUntilDays = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETAIN_UNTIL_DAYS' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3RetainUntilDays
    $script:EdhrS3RequireLegalHold = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REQUIRE_LEGAL_HOLD' -TargetEnvironment $TargetEnvironment -CurrentValue $script:EdhrS3RequireLegalHold
}

function Read-ReleaseRuntimeEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $settings = @{}
    foreach ($rawLine in [System.IO.File]::ReadAllLines($Path, [System.Text.UTF8Encoding]::new($false))) {
        $line = $rawLine.Trim()
        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#') -or -not $line.Contains('=')) {
            continue
        }
        $pair = $line.Split('=', 2)
        $settings[$pair[0].Trim()] = $pair[1].Trim()
    }
    return $settings
}

function Set-PublishRuntimeValuesFromSettings {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Settings
    )

    if ($Settings.ContainsKey('DCC_SIGNATURE_EVIDENCE_HMAC_SECRET')) { $script:DccSignatureEvidenceHmacSecret = $Settings['DCC_SIGNATURE_EVIDENCE_HMAC_SECRET'] }
    if ($Settings.ContainsKey('DCC_SIGNATURE_EVIDENCE_KEY_VERSION')) { $script:DccSignatureEvidenceKeyVersion = $Settings['DCC_SIGNATURE_EVIDENCE_KEY_VERSION'] }
    if ($Settings.ContainsKey('DCC_VIEWER_TOKEN_HMAC_SECRET')) { $script:DccViewerTokenHmacSecret = $Settings['DCC_VIEWER_TOKEN_HMAC_SECRET'] }
    if ($Settings.ContainsKey('DCC_ONLYOFFICE_JWT_SECRET')) { $script:DccOnlyOfficeJwtSecret = $Settings['DCC_ONLYOFFICE_JWT_SECRET'] }
    if ($Settings.ContainsKey('DCC_ONLYOFFICE_BASE_URL')) { $script:DccOnlyOfficeBaseUrl = $Settings['DCC_ONLYOFFICE_BASE_URL'] }
    if ($Settings.ContainsKey('DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL')) { $script:DccOnlyOfficePublicFileBaseUrl = $Settings['DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL'] }
    if ($Settings.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION')) { $script:DccDownloadEncryptionPolicyVersion = $Settings['DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION'] }
    if ($Settings.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_KEY_ID')) { $script:DccDownloadEncryptionKeyId = $Settings['DCC_DOWNLOAD_ENCRYPTION_KEY_ID'] }
    if ($Settings.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY')) { $script:DccDownloadEncryptionBase64Key = $Settings['DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY'] }
    if ($Settings.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY')) { $script:DccDownloadEncryptionArtifactDirectory = $Settings['DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY'] }
    if ($Settings.ContainsKey('EDHR_S3_ENDPOINT')) { $script:EdhrS3Endpoint = $Settings['EDHR_S3_ENDPOINT'] }
    if ($Settings.ContainsKey('EDHR_S3_BUCKET')) { $script:EdhrS3Bucket = $Settings['EDHR_S3_BUCKET'] }
    if ($Settings.ContainsKey('EDHR_S3_REGION')) { $script:EdhrS3Region = $Settings['EDHR_S3_REGION'] }
    if ($Settings.ContainsKey('EDHR_S3_ACCESS_KEY')) { $script:EdhrS3AccessKey = $Settings['EDHR_S3_ACCESS_KEY'] }
    if ($Settings.ContainsKey('EDHR_S3_SECRET_KEY')) { $script:EdhrS3SecretKey = $Settings['EDHR_S3_SECRET_KEY'] }
    if ($Settings.ContainsKey('EDHR_S3_RETENTION_MODE')) { $script:EdhrS3RetentionMode = $Settings['EDHR_S3_RETENTION_MODE'] }
    if ($Settings.ContainsKey('EDHR_S3_RETAIN_UNTIL_DAYS')) { $script:EdhrS3RetainUntilDays = $Settings['EDHR_S3_RETAIN_UNTIL_DAYS'] }
    if ($Settings.ContainsKey('EDHR_S3_REQUIRE_LEGAL_HOLD')) { $script:EdhrS3RequireLegalHold = $Settings['EDHR_S3_REQUIRE_LEGAL_HOLD'] }
}

function New-ReleaseRuntimeEnvContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [string]$TargetServerHost
    )

    $resolvedDccSignatureEvidenceHmacSecret = Resolve-PublishRuntimeValue -Name 'DCC_SIGNATURE_EVIDENCE_HMAC_SECRET' -CurrentValue $DccSignatureEvidenceHmacSecret -HardcodedValue $DCC_HARDCODED_SIGNATURE_EVIDENCE_HMAC_SECRET
    $resolvedDccSignatureEvidenceKeyVersion = Resolve-PublishRuntimeValue -Name 'DCC_SIGNATURE_EVIDENCE_KEY_VERSION' -CurrentValue $DccSignatureEvidenceKeyVersion -HardcodedValue $DCC_HARDCODED_SIGNATURE_EVIDENCE_KEY_VERSION
    $resolvedDccViewerTokenHmacSecret = Resolve-PublishRuntimeValue -Name 'DCC_VIEWER_TOKEN_HMAC_SECRET' -CurrentValue $DccViewerTokenHmacSecret -HardcodedValue $DCC_HARDCODED_VIEWER_TOKEN_HMAC_SECRET
    $resolvedDccOnlyOfficeJwtSecret = Resolve-PublishRuntimeValue -Name 'DCC_ONLYOFFICE_JWT_SECRET' -CurrentValue $DccOnlyOfficeJwtSecret -HardcodedValue $DCC_HARDCODED_ONLYOFFICE_JWT_SECRET
    $resolvedDccOnlyOfficePublicFileBaseUrl = "http://host.docker.internal:$BackendPort"
    $resolvedDccDownloadEncryptionPolicyVersion = Resolve-PublishRuntimeValue -Name 'DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION' -CurrentValue $DccDownloadEncryptionPolicyVersion -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_POLICY_VERSION
    $resolvedDccDownloadEncryptionKeyId = Resolve-PublishRuntimeValue -Name 'DCC_DOWNLOAD_ENCRYPTION_KEY_ID' -CurrentValue $DccDownloadEncryptionKeyId -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_KEY_ID
    $resolvedDccDownloadEncryptionBase64Key = Resolve-PublishRuntimeValue -Name 'DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY' -CurrentValue $DccDownloadEncryptionBase64Key -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_BASE64_KEY
    $resolvedDccDownloadEncryptionArtifactDirectory = Resolve-PublishRuntimeValue -Name 'DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY' -CurrentValue $DccDownloadEncryptionArtifactDirectory -HardcodedValue $DCC_HARDCODED_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY
    $resolvedEdhrS3Bucket = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_BUCKET' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3Bucket
    $resolvedEdhrS3Region = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REGION' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3Region
    $resolvedEdhrS3AccessKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ACCESS_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3AccessKey
    $resolvedEdhrS3SecretKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_SECRET_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3SecretKey
    $resolvedEdhrS3RetentionMode = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETENTION_MODE' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RetentionMode
    $resolvedEdhrS3RetainUntilDays = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETAIN_UNTIL_DAYS' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RetainUntilDays
    $resolvedEdhrS3RequireLegalHold = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REQUIRE_LEGAL_HOLD' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RequireLegalHold

    return @"
DCC_SIGNATURE_EVIDENCE_HMAC_SECRET=$resolvedDccSignatureEvidenceHmacSecret
DCC_SIGNATURE_EVIDENCE_KEY_VERSION=$resolvedDccSignatureEvidenceKeyVersion
DCC_VIEWER_TOKEN_HMAC_SECRET=$resolvedDccViewerTokenHmacSecret
DCC_ONLYOFFICE_JWT_SECRET=$resolvedDccOnlyOfficeJwtSecret
DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL=$resolvedDccOnlyOfficePublicFileBaseUrl
DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION=$resolvedDccDownloadEncryptionPolicyVersion
DCC_DOWNLOAD_ENCRYPTION_KEY_ID=$resolvedDccDownloadEncryptionKeyId
DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY=$resolvedDccDownloadEncryptionBase64Key
DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY=$resolvedDccDownloadEncryptionArtifactDirectory
EDHR_S3_BUCKET=$resolvedEdhrS3Bucket
EDHR_S3_REGION=$resolvedEdhrS3Region
EDHR_S3_ACCESS_KEY=$resolvedEdhrS3AccessKey
EDHR_S3_SECRET_KEY=$resolvedEdhrS3SecretKey
EDHR_S3_RETENTION_MODE=$resolvedEdhrS3RetentionMode
EDHR_S3_RETAIN_UNTIL_DAYS=$resolvedEdhrS3RetainUntilDays
EDHR_S3_REQUIRE_LEGAL_HOLD=$resolvedEdhrS3RequireLegalHold
"@
}

function Write-ReleaseRuntimeEnvPackage {
    $runtimeEnvDir = Join-Path $releaseDir 'runtime-env'
    New-Item -ItemType Directory -Force -Path $runtimeEnvDir | Out-Null
    $runtimeEnvTargets = @(
        @{ FileName = 'test.env'; Host = $TestServerHost; ArgumentName = '-TestServerHost' },
        @{ FileName = 'backup.env'; Host = $BackupServerHost; ArgumentName = '-BackupServerHost' }
    )
    if (-not [string]::IsNullOrWhiteSpace($ProdServerHost)) {
        $runtimeEnvTargets += @{ FileName = 'prod.env'; Host = $ProdServerHost; ArgumentName = '-ProdServerHost' }
    }
    foreach ($target in $runtimeEnvTargets) {
        $targetRuntimeEnvFileName = $target.FileName
        $targetEnvironment = [System.IO.Path]::GetFileNameWithoutExtension($targetRuntimeEnvFileName)
        $targetServerHost = Require-ConfiguredTargetServerHost -TargetEnvironment $targetEnvironment -Value $target.Host -ArgumentName $target.ArgumentName
        $content = New-ReleaseRuntimeEnvContent -TargetEnvironment $targetEnvironment -TargetServerHost $targetServerHost
        Write-Utf8LfNoBomFile -Path (Join-Path $runtimeEnvDir $targetRuntimeEnvFileName) -Content $content
    }
}

function Apply-ReleaseRuntimeEnvPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )

    $runtimeEnvFile = Join-Path $releaseDir "runtime-env\$TargetEnvironment.env"
    if (-not (Test-Path -LiteralPath $runtimeEnvFile)) {
        Info "Release package runtime env not found, using operator process settings: runtime-env/$TargetEnvironment.env"
        return
    }
    $settings = Read-ReleaseRuntimeEnvFile -Path $runtimeEnvFile
    Set-PublishRuntimeValuesFromSettings -Settings $settings
    Info "Loaded release package runtime env: runtime-env/$TargetEnvironment.env"
}

function Assert-EdhrProtectedStorageConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Context,
        [Parameter(Mandatory = $true)]
        [hashtable]$Settings
    )

    foreach ($key in @(
        'EDHR_S3_ENDPOINT',
        'EDHR_S3_BUCKET',
        'EDHR_S3_REGION',
        'EDHR_S3_ACCESS_KEY',
        'EDHR_S3_SECRET_KEY',
        'EDHR_S3_RETENTION_MODE',
        'EDHR_S3_RETAIN_UNTIL_DAYS',
        'EDHR_S3_REQUIRE_LEGAL_HOLD'
    )) {
        if ([string]::IsNullOrWhiteSpace([string]$Settings[$key])) {
            Fail "Missing $key for $Context; eDHR protected storage/Object Lock is fail-fast and cannot be bypassed."
        }
    }

    $mode = ([string]$Settings['EDHR_S3_RETENTION_MODE']).Trim().ToUpperInvariant()
    if ($mode -notin @('GOVERNANCE', 'COMPLIANCE')) {
        Fail 'Invalid EDHR_S3_RETENTION_MODE; expected GOVERNANCE or COMPLIANCE for eDHR protected storage/Object Lock.'
    }

    $days = 0
    if (-not [int]::TryParse(([string]$Settings['EDHR_S3_RETAIN_UNTIL_DAYS']).Trim(), [ref]$days) -or $days -le 0) {
        Fail 'Invalid EDHR_S3_RETAIN_UNTIL_DAYS; expected a positive integer for eDHR protected storage/Object Lock.'
    }

    $legalHold = ([string]$Settings['EDHR_S3_REQUIRE_LEGAL_HOLD']).Trim().ToLowerInvariant()
    if ($legalHold -notin @('1', 'true', 'yes', 'y', 'on', '0', 'false', 'no', 'n', 'off')) {
        Fail 'Invalid EDHR_S3_REQUIRE_LEGAL_HOLD; expected true or false for eDHR protected storage/Object Lock.'
    }
}

function Set-EdhrStorageVerifierEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Settings
    )

    foreach ($key in $Settings.Keys) {
        [System.Environment]::SetEnvironmentVariable($key, [string]$Settings[$key], 'Process')
    }
}

function Invoke-EdhrStorageRetentionVerifier {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackendRepo
    )

    $verifier = Join-Path $BackendRepo 'tool\edhr-storage-retention-verifier\verify.py'
    if (-not (Test-Path -LiteralPath $verifier)) {
        Fail "Missing eDHR storage retention verifier: $verifier"
    }

    Info 'Verifying eDHR protected storage/Object Lock target before publish'
    $result = Invoke-ProcessCapture -FilePath 'python' -ArgumentList @('-X', 'utf8', $verifier) -WorkingDirectory $BackendRepo
    $output = Remove-SshNoise ((($result.StdOut + "`n" + $result.StdErr)).Trim())
    if ($output) {
        Write-Host $output
    }
    if ($result.ExitCode -ne 0) {
        Fail "eDHR protected storage verifier failed with exit code $($result.ExitCode)."
    }
    try {
        $json = $result.StdOut | ConvertFrom-Json
    } catch {
        Fail "eDHR protected storage verifier did not return valid JSON: $($_.Exception.Message)"
    }
    if ($json.status -ne 'PASS') {
        Fail "eDHR protected storage verifier status is $($json.status), expected PASS."
    }
}

function ConvertTo-SqlStringLiteral {
    param(
        [AllowNull()]
        [string]$Value
    )

    if ($null -eq $Value) {
        return 'NULL'
    }
    return "'" + $Value.Replace("'", "''") + "'"
}

function New-EdhrProtectedStoragePostImportSql {
    return @"
SELECT 'SHOWROOM_FILE_CONFIG_28_PROTECTED: infra_file_config.id=28 is protected from publish-time mutation; eDHR storage uses runtime EDHR_S3_* configuration only' AS intruoyi_publish_guard;
"@
}

function New-ShowroomFileStoragePostImportSql {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetServerHost,
        [string]$MinioAccessKey = '',
        [string]$MinioAccessSecret = ''
    )

    return @"
DROP PROCEDURE IF EXISTS intruoyi_assert_showroom_file_storage_target;
DELIMITER `$`$
CREATE PROCEDURE intruoyi_assert_showroom_file_storage_target()
BEGIN
    IF EXISTS (
        SELECT 1
        FROM infra_file_config
        WHERE id = 28
          AND deleted = b'0'
          AND config LIKE '%127.0.0.1:9000%'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'SHOWROOM_FILE_CONFIG_28_PROTECTED: infra_file_config.id=28 is protected from publish-time mutation and still points to 127.0.0.1:9000';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM infra_file
        WHERE config_id = 28
          AND deleted = b'0'
          AND path LIKE 'showroom/%'
          AND url LIKE '%127.0.0.1:9000%'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'SHOWROOM_FILE_CONFIG_28_PROTECTED: protected showroom infra_file.url still points to 127.0.0.1:9000';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM infra_file_config
        WHERE id = 28
          AND deleted = b'0'
          AND config LIKE '%http://host.docker.internal:9000%'
          AND config LIKE '%http://${TargetServerHost}:9000/yudao%'
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'SHOWROOM_FILE_CONFIG_UNBOUND: infra_file_config.id=28 is not bound to target MinIO endpoint/domain';
    END IF;
END `$`$
DELIMITER ;
CALL intruoyi_assert_showroom_file_storage_target();
DROP PROCEDURE IF EXISTS intruoyi_assert_showroom_file_storage_target;
"@
}

function Copy-ToServer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LocalPath,
        [Parameter(Mandatory = $true)]
        [string]$RemotePath,
        [switch]$Recursive
    )

    Invoke-CheckedCommand -FilePath 'scp' -ArgumentList (New-ScpArgumentList -LocalPath $LocalPath -RemotePath $RemotePath -Recursive:$Recursive)
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ''
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Info "$Url returned HTTP $($response.StatusCode)"
                return
            }
            $lastError = "HTTP $($response.StatusCode)"
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    Fail "$Url did not become ready within $TimeoutSeconds seconds. Last error: $lastError"
}

function Wait-HttpContentTypeOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedContentType,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ''
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Head -TimeoutSec 5 -Headers @{
                'Cache-Control' = 'no-cache'
            }
            $contentType = [string]$response.Headers['Content-Type']
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400 -and $contentType -like "$ExpectedContentType*") {
                Info "$Url returned HTTP $($response.StatusCode) $contentType"
                return
            }
            $lastError = "HTTP $($response.StatusCode), expected $ExpectedContentType but got $contentType"
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    Fail "$Url did not return $ExpectedContentType within $TimeoutSeconds seconds. Last error: $lastError"
}

function Read-JsonEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$Purpose
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 10 -Headers @{
            Accept = 'application/json'
            'Cache-Control' = 'no-cache'
        }
        if ($response.StatusCode -ne 200) {
            Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: $Purpose returned HTTP $($response.StatusCode): $Url"
        }
        $contentType = [string]$response.Headers['Content-Type']
        if ($contentType -notmatch 'application/json') {
            Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: $Purpose returned non-JSON content-type '$contentType': $Url"
        }
        return $response.Content | ConvertFrom-Json
    } catch {
        Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: $Purpose request failed: $Url. $($_.Exception.Message)"
    }
}

function Assert-PublicWebsiteEntryReadback {
    $websiteEntryUrl = "http://${ServerHost}:$WebsiteHostPort/"
    $expectedCacheControl = 'no-store, no-cache, must-revalidate, max-age=0'
    $expectedBundleCacheControl = 'public, max-age=31536000, immutable'

    try {
        $entryResponse = Invoke-WebRequest -UseBasicParsing -Uri $websiteEntryUrl -TimeoutSec 10 -Headers @{
            'Cache-Control' = 'no-cache'
        }
    } catch {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry request failed: $websiteEntryUrl. $($_.Exception.Message)"
    }

    if ($entryResponse.StatusCode -ne 200) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry returned HTTP $($entryResponse.StatusCode): $websiteEntryUrl"
    }

    $cacheControl = [string]$entryResponse.Headers['Cache-Control']
    $pragma = [string]$entryResponse.Headers['Pragma']
    $expires = [string]$entryResponse.Headers['Expires']
    if ($cacheControl -ne $expectedCacheControl) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry Cache-Control expected '$expectedCacheControl' but got '$cacheControl'"
    }
    if ($pragma -ne 'no-cache') {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry Pragma expected 'no-cache' but got '$pragma'"
    }
    if ($expires -ne '0') {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry Expires expected '0' but got '$expires'"
    }

    $entryHtml = [string]$entryResponse.Content
    $scriptMatch = [regex]::Match($entryHtml, '<script[^>]+src="(?<src>[^"]+\.js)"')
    if (-not $scriptMatch.Success) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website entry did not reference a JavaScript bundle"
    }

    $scriptPath = $scriptMatch.Groups['src'].Value
    if (-not $scriptPath.StartsWith('/')) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle path is not root-relative: $scriptPath"
    }

    $bundleUrl = "http://${ServerHost}:$WebsiteHostPort$scriptPath"
    try {
        $bundleResponse = Invoke-WebRequest -UseBasicParsing -Uri $bundleUrl -TimeoutSec 20 -Headers @{
            'Cache-Control' = 'no-cache'
        }
    } catch {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle request failed: $bundleUrl. $($_.Exception.Message)"
    }

    if ($bundleResponse.StatusCode -ne 200) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle returned HTTP $($bundleResponse.StatusCode): $bundleUrl"
    }

    $bundleCacheControl = [string]$bundleResponse.Headers['Cache-Control']
    if ($bundleCacheControl -ne $expectedBundleCacheControl) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle Cache-Control expected '$expectedBundleCacheControl' but got '$bundleCacheControl'"
    }

    $bundleText = [string]$bundleResponse.Content
    foreach ($marker in @('yingtai-showroom', 'TEST', '3221225472')) {
        if (-not $bundleText.Contains($marker)) {
            Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle $bundleUrl is missing marker '$marker'"
        }
    }
    if ($bundleText.Contains('1073741824')) {
        Fail "SHOWROOM_WEBSITE_ENTRY_READBACK_FAILED: Website bundle $bundleUrl still contains stale 1GB quota marker 1073741824"
    }

    Info "Website entry verified: $websiteEntryUrl -> $scriptPath with no-store headers and current bundle markers"
}

function Assert-PublicWebsiteScopedReleaseCurrent {
    $backendCurrentUrl = "http://${ServerHost}:$BackendPort/showroom/sites/$ShowroomSiteKey/stages/$ShowroomStage/release/current"
    $websiteCurrentUrl = "http://${ServerHost}:$WebsiteHostPort/showroom/sites/$ShowroomSiteKey/stages/$ShowroomStage/release/current"

    $backendCurrent = Read-JsonEndpoint -Url $backendCurrentUrl -Purpose 'backend scoped current release'
    $websiteCurrent = Read-JsonEndpoint -Url $websiteCurrentUrl -Purpose 'Website scoped current release'

    if ([string]::IsNullOrWhiteSpace([string]$backendCurrent.releaseId)) {
        Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: backend current releaseId is missing"
    }
    if ([string]::IsNullOrWhiteSpace([string]$backendCurrent.manifestHash)) {
        Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: backend current manifestHash is missing"
    }
    if ($backendCurrent.releaseId -ne $websiteCurrent.releaseId) {
        Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: Website releaseId '$($websiteCurrent.releaseId)' does not match backend '$($backendCurrent.releaseId)'"
    }
    if ($backendCurrent.manifestHash -ne $websiteCurrent.manifestHash) {
        Fail "SHOWROOM_WEBSITE_CURRENT_READBACK_FAILED: Website manifestHash '$($websiteCurrent.manifestHash)' does not match backend '$($backendCurrent.manifestHash)'"
    }

    Info "Website scoped current release verified: $($websiteCurrent.releaseId)"
}

function Wait-RemoteContainerHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ContainerName,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastStatus = ''
    do {
        $result = Invoke-SshCapture -Command "docker inspect -f '{{.State.Health.Status}}' $ContainerName" -IgnoreExitCode
        if ($result.Ok -and $result.Output -eq 'healthy') {
            Info "Remote container $ContainerName is healthy"
            return
        }
        $lastStatus = $result.Output
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Fail "Remote container $ContainerName did not become healthy within $TimeoutSeconds seconds. Last status: $lastStatus"
}

function Wait-RemoteMySqlReady {
    param(
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastStatus = ''
    do {
        $result = Invoke-SshCapture -Command "docker exec intruoyi-mysql mysqladmin -uroot -p$mySqlRootPassword ping --silent" -IgnoreExitCode
        if ($result.Ok) {
            Info 'Remote MySQL accepts client connections'
            return
        }
        $lastStatus = $result.Output
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    Fail "Remote MySQL did not accept client connections within $TimeoutSeconds seconds. Last status: $lastStatus"
}

function Assert-RemoteQuartzSchemaReady {
    Info 'Checking remote Quartz schema'
    $command = @'
docker exec -i intruoyi-mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -D "$MYSQL_DATABASE" --default-character-set=utf8mb4 --batch --raw --skip-column-names' <<'SQL'
SELECT COUNT(*)
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('QRTZ_JOB_DETAILS', 'QRTZ_TRIGGERS');
SQL
'@
    $result = Invoke-SshCapture -Command $command
    $count = ($result.Output.Trim() -split "`r?`n" | Select-Object -Last 1)
    if ($count -ne '2') {
        Fail "Remote Quartz schema is missing required tables QRTZ_JOB_DETAILS / QRTZ_TRIGGERS after required SQL. Actual count: $count"
    }
}

function Assert-RemoteShowroomAwardSchemaReady {
    Info 'Checking remote showroom runtime schema'
    $sql = @"
SELECT CONCAT('TABLES', CHAR(9), COUNT(DISTINCT TABLE_NAME))
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('showroom_award', 'showroom_award_revision', 'showroom_hall_item', 'showroom_product_revision_attachment');
SELECT CONCAT('INDEXES', CHAR(9), COUNT(DISTINCT CONCAT(TABLE_NAME, '.', INDEX_NAME)))
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND (
       (TABLE_NAME = 'showroom_award' AND INDEX_NAME = 'uk_showroom_award_code')
    OR (TABLE_NAME = 'showroom_award_revision' AND INDEX_NAME = 'uk_showroom_award_revision_no')
    OR (TABLE_NAME = 'showroom_award_revision' AND INDEX_NAME = 'idx_showroom_award_revision_award')
    OR (TABLE_NAME = 'showroom_hall_item' AND INDEX_NAME = 'uk_showroom_hall_item')
    OR (TABLE_NAME = 'showroom_hall_item' AND INDEX_NAME = 'idx_showroom_hall_item_order')
    OR (TABLE_NAME = 'showroom_hall_item' AND INDEX_NAME = 'idx_showroom_hall_item_item')
    OR (TABLE_NAME = 'showroom_product_revision_attachment' AND INDEX_NAME = 'uk_showroom_product_revision_attachment_file')
    OR (TABLE_NAME = 'showroom_product_revision_attachment' AND INDEX_NAME = 'idx_showroom_product_revision_attachment_revision')
    OR (TABLE_NAME = 'showroom_product_revision_attachment' AND INDEX_NAME = 'idx_showroom_product_revision_attachment_product')
  );
SELECT CONCAT('COLUMNS', CHAR(9), COUNT(DISTINCT COLUMN_NAME))
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'showroom_hall'
  AND COLUMN_NAME = 'canvas_background_image_url';
"@
    $output = Invoke-RemoteMySqlRaw -Sql $sql -Purpose 'SHOWROOM_AWARD_SCHEMA_MISSING schema verification'
    $lines = @($output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $tableLine = @($lines | Where-Object { $_.StartsWith("TABLES`t") }) | Select-Object -First 1
    $indexLine = @($lines | Where-Object { $_.StartsWith("INDEXES`t") }) | Select-Object -First 1
    $columnLine = @($lines | Where-Object { $_.StartsWith("COLUMNS`t") }) | Select-Object -First 1
    $tableCount = if ($tableLine) { [int](($tableLine -split "`t")[1]) } else { 0 }
    $indexCount = if ($indexLine) { [int](($indexLine -split "`t")[1]) } else { 0 }
    $columnCount = if ($columnLine) { [int](($columnLine -split "`t")[1]) } else { 0 }
    if ($tableCount -ne 4) {
        Fail "SHOWROOM_AWARD_SCHEMA_MISSING: expected showroom_award/showroom_award_revision/showroom_hall_item/showroom_product_revision_attachment before backend start, actual table count: $tableCount"
    }
    if ($indexCount -ne 9) {
        Fail "SHOWROOM_AWARD_SCHEMA_MISSING: expected showroom award/hall item/product attachment indexes before backend start, actual index count: $indexCount"
    }
    if ($columnCount -ne 1) {
        Fail "SHOWROOM_AWARD_SCHEMA_MISSING: expected showroom_hall.canvas_background_image_url before backend start, actual column count: $columnCount"
    }
}

function Wait-RemoteHttpOk {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastStatus = ''
    do {
        $result = Invoke-SshCapture -Command "curl -fsS '$Url' >/dev/null && echo OK" -IgnoreExitCode
        if ($result.Ok -and $result.Output -match 'OK') {
            Info "Remote URL ready: $Url"
            return
        }
        $lastStatus = $result.Output
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    Fail "Remote URL did not become ready within $TimeoutSeconds seconds: $Url`n$lastStatus"
}

function Invoke-RemoteMySqlRaw {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Sql,
        [string]$Purpose = 'remote MySQL query'
    )

    $commandTemplate = @'
docker exec -i intruoyi-mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -D "$MYSQL_DATABASE" --default-character-set=utf8mb4 --batch --raw --skip-column-names' <<'SQL'
__SQL__
SQL
'@
    $command = $commandTemplate.Replace('__SQL__', $Sql)
    $result = Invoke-SshCapture -Command $command -IgnoreExitCode
    if (-not $result.Ok) {
        Fail "$Purpose failed: $($result.Output)"
    }
    return ($result.Output).Trim()
}

function Assert-RemoteFileStorageConfigRebound {
    $sql = @"
SELECT CONCAT(
    IF(COUNT(*) = 0, 'MISSING', 'FOUND'), CHAR(9),
    COALESCE(SUM(config LIKE '%127.0.0.1:9000%'), 0), CHAR(9),
    COALESCE(SUM(config LIKE '%http://host.docker.internal:9000%'), 0), CHAR(9),
    COALESCE(SUM(config LIKE '%http://${ServerHost}:9000/yudao%'), 0), CHAR(9),
    (SELECT COUNT(*) FROM infra_file WHERE config_id = 28 AND deleted = b'0' AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%')
)
FROM infra_file_config
WHERE id = 28
  AND deleted = b'0';
"@
    $output = Invoke-RemoteMySqlRaw -Sql $sql -Purpose 'SHOWROOM_FILE_CONFIG_UNBOUND config verification'
    $parts = $output -split "`t"
    if ($parts.Count -lt 5 -or $parts[0] -ne 'FOUND') {
        Fail "SHOWROOM_FILE_CONFIG_28_PROTECTED: infra_file_config.id=28 is missing after restore"
    }
    if ([int]$parts[1] -gt 0) {
        Fail "SHOWROOM_FILE_CONFIG_28_PROTECTED: infra_file_config.id=28 still contains 127.0.0.1:9000"
    }
    if ([int]$parts[2] -lt 1) {
        Fail "SHOWROOM_FILE_CONFIG_UNBOUND: infra_file_config.id=28 endpoint is not http://host.docker.internal:9000"
    }
    if ([int]$parts[3] -lt 1) {
        Fail "SHOWROOM_FILE_CONFIG_UNBOUND: infra_file_config.id=28 domain is not http://${ServerHost}:9000/yudao"
    }
    if ([int]$parts[4] -gt 0) {
        Fail "SHOWROOM_FILE_CONFIG_28_PROTECTED: protected showroom infra_file.url still contains 127.0.0.1:9000 for config 28"
    }
    Info 'Showroom file storage config 28 is protected and target-bound'
}

function Assert-RemoteBackendContainerMinioReachable {
    $result = Invoke-SshCapture -Command "docker exec intruoyi-backend sh -lc 'curl -fsS --connect-timeout 5 http://host.docker.internal:9000/minio/health/live >/dev/null && echo OK'" -IgnoreExitCode
    if (-not $result.Ok -or $result.Output -notmatch 'OK') {
        Fail "SHOWROOM_FILE_STORAGE_ENDPOINT_UNREACHABLE: backend container cannot reach http://host.docker.internal:9000/minio/health/live`n$($result.Output)"
    }
    Info 'Backend container can reach target MinIO endpoint'
}

function Get-RemoteShowroomSmokeImageAsset {
    $sql = @"
SELECT CONCAT(config_id, CHAR(9), path)
FROM infra_file
WHERE config_id = 28
  AND deleted = b'0'
  AND type LIKE 'image/%'
  AND path LIKE 'showroom/%'
ORDER BY update_time DESC, id DESC
LIMIT 1;
"@
    $output = Invoke-RemoteMySqlRaw -Sql $sql -Purpose 'SHOWROOM_FILE_CONTENT_SMOKE_FAILED sample image lookup'
    if ([string]::IsNullOrWhiteSpace($output)) {
        Fail 'SHOWROOM_FILE_CONTENT_SMOKE_FAILED: no showroom image infra_file row found for config 28'
    }
    $parts = $output -split "`t", 2
    if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[0]) -or [string]::IsNullOrWhiteSpace($parts[1])) {
        Fail "SHOWROOM_FILE_CONTENT_SMOKE_FAILED: invalid showroom image sample row: $output"
    }
    return @{
        ConfigId = $parts[0].Trim()
        Path = $parts[1].Trim()
    }
}

function Assert-RemoteShowroomSmokeImageContent {
    $asset = Get-RemoteShowroomSmokeImageAsset
    $smokeImageUrl = "http://${ServerHost}:$FrontendPort/admin-api/infra/file/$($asset.ConfigId)/get/$($asset.Path)"
    Wait-HttpContentTypeOk -Url $smokeImageUrl -ExpectedContentType 'image/' -TimeoutSeconds 180
    Info "Showroom smoke image is readable through frontend proxy: $smokeImageUrl"
}

function Assert-RemoteRuntimeDataOnDataDisk {
    if ([string]::IsNullOrWhiteSpace($RemoteReleaseRoot)) {
        Fail 'Missing RemoteReleaseRoot'
    }
    if ([string]::IsNullOrWhiteSpace($RemoteDataRoot)) {
        Fail 'Missing RemoteDataRoot'
    }
    if ([string]::IsNullOrWhiteSpace($RemoteDataDiskMount)) {
        Fail 'Missing RemoteDataDiskMount'
    }
    if ([string]::IsNullOrWhiteSpace($RemoteDataDiskDevice)) {
        Fail 'Missing RemoteDataDiskDevice'
    }

    $command = @"
set -eu
data_disk_source=`$(findmnt -n -o SOURCE --target '$RemoteDataDiskMount' 2>/dev/null || true)
if [ "`$data_disk_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteDataDiskMount to be mounted from $RemoteDataDiskDevice, got: `$data_disk_source" >&2
  exit 1
fi
mkdir -p '$RemoteDataRoot' '$RemoteReleaseRoot' '$RemoteAppDir'
release_source=`$(df -P '$RemoteReleaseRoot' | awk 'NR==2 {print `$1}')
if [ "`$release_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteReleaseRoot to be stored on $RemoteDataDiskDevice, got: `$release_source" >&2
  exit 1
fi
if [ -e '$RemoteAppDir/data' ] && [ ! -d '$RemoteAppDir/data' ]; then
  echo "Remote runtime data path exists but is not a directory: $RemoteAppDir/data" >&2
  exit 1
fi
mkdir -p '$RemoteAppDir/data'
if ! mountpoint -q '$RemoteAppDir/data'; then
  if [ -n "`$(find '$RemoteAppDir/data' -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    echo "Remote runtime data dir is not mounted and is not empty: $RemoteAppDir/data" >&2
    exit 1
  fi
  mount --bind '$RemoteDataRoot' '$RemoteAppDir/data'
fi
data_dir_source=`$(df -P '$RemoteAppDir/data' | awk 'NR==2 {print `$1}')
if [ "`$data_dir_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteAppDir/data to be stored on $RemoteDataDiskDevice, got: `$data_dir_source" >&2
  exit 1
fi
fstab_line='$RemoteDataRoot $RemoteAppDir/data none bind 0 0'
if ! grep -Fqs "`$fstab_line" /etc/fstab; then
  printf '%s\n' "`$fstab_line" >> /etc/fstab
fi
mkdir -p '$RemoteAppDir/data/mysql' '$RemoteAppDir/data/redis' '$RemoteAppDir/data/backend-logs' '$RemoteAppDir/data/minio'
"@
    Invoke-SshCommand $command
}

function Read-NasReleaseConfig {
    if ([string]::IsNullOrWhiteSpace($NasConfigPath)) {
        Fail 'Missing NasConfigPath; release package modes must use NAS Management configuration.'
    }
    if (-not (Test-Path -LiteralPath $NasConfigPath)) {
        Fail "NAS release config file not found: $NasConfigPath"
    }
    $text = [System.IO.File]::ReadAllText($NasConfigPath, [System.Text.UTF8Encoding]::new($false))
    $config = $text | ConvertFrom-Json
    foreach ($field in @('server', 'share', 'username', 'password')) {
        if ([string]::IsNullOrWhiteSpace([string]$config.$field)) {
            Fail "NAS release config missing field: $field"
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($NasServer)) {
        $config.server = $NasServer
    }
    # NAS release config share must come from the UTF-8 config file.
    if (-not [string]::IsNullOrWhiteSpace($NasShare) -and $NasShare -ne [string]$config.share) {
        Info 'Ignoring command-line NasShare; NAS release config share remains authoritative.'
    }
    return $config
}

function Join-NasRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Parts
    )
    $normalized = New-Object System.Collections.Generic.List[string]
    foreach ($part in $Parts) {
        $raw = ([string]$part).Trim().Replace('\', '/')
        if ([string]::IsNullOrWhiteSpace($raw)) {
            continue
        }
        foreach ($token in ($raw -split '/')) {
            $clean = $token.Trim()
            if ([string]::IsNullOrWhiteSpace($clean) -or $clean -eq '.') {
                continue
            }
            if ($clean -eq '..') {
                Fail "NAS release path must not contain '..': $part"
            }
            $normalized.Add($clean)
        }
    }
    if ($normalized.Count -eq 0) {
        Fail 'NAS release path is blank'
    }
    return ($normalized -join '\')
}

function ConvertTo-ReleasePackageDirectoryName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReleaseTagValue
    )
    if ([string]::IsNullOrWhiteSpace($ReleaseTagValue)) {
        Fail 'ReleaseTag is blank'
    }
    $normalizedReleaseTag = $ReleaseTagValue.Trim()
    $directoryName = $normalizedReleaseTag.Replace(' ', '_').Replace(':', '-')
    if ([System.Text.RegularExpressions.Regex]::IsMatch($directoryName, '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')) {
        return $directoryName
    }
    if ($directoryName.Contains([string][char]0xFFFD)) {
        Fail 'ReleaseTag contains Unicode replacement characters; command invocation encoding is corrupted. Re-run the build with UTF-8-safe argument passing.'
    }

    $hasNonAscii = $false
    foreach ($character in $directoryName.ToCharArray()) {
        $codePoint = [int][char]$character
        if ($codePoint -le 127) {
            if (-not [System.Text.RegularExpressions.Regex]::IsMatch([string]$character, '^[A-Za-z0-9_.-]$')) {
                Fail "ReleaseTag contains unsupported package name characters: $ReleaseTagValue"
            }
        } else {
            $hasNonAscii = $true
        }
    }
    if (-not $hasNonAscii) {
        Fail "ReleaseTag contains unsupported package name characters: $ReleaseTagValue"
    }

    $asciiStem = [System.Text.RegularExpressions.Regex]::Replace($directoryName, '[^\x00-\x7F]+', '')
    $asciiStem = [System.Text.RegularExpressions.Regex]::Replace($asciiStem, '-{2,}', '-').Trim([char[]]@('-', '_', '.'))
    if ([string]::IsNullOrWhiteSpace($asciiStem)) {
        $asciiStem = 'release'
    }
    if (-not [System.Text.RegularExpressions.Regex]::IsMatch($asciiStem, '^[A-Za-z0-9]')) {
        $asciiStem = "release-$asciiStem"
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha256.ComputeHash($utf8.GetBytes($normalizedReleaseTag))
        $hashSuffix = '-u' + (([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant().Substring(0, 12))
    } finally {
        $sha256.Dispose()
    }
    $maxStemLength = 128 - $hashSuffix.Length
    if ($asciiStem.Length -gt $maxStemLength) {
        $asciiStem = $asciiStem.Substring(0, $maxStemLength).TrimEnd([char[]]@('-', '_', '.'))
    }
    if ([string]::IsNullOrWhiteSpace($asciiStem)) {
        $asciiStem = 'release'
    }
    $directoryName = "$asciiStem$hashSuffix"
    if (-not [System.Text.RegularExpressions.Regex]::IsMatch($directoryName, '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')) {
        Fail "ReleaseTag cannot be converted to a safe package directory name: $ReleaseTagValue"
    }
    return $directoryName
}

function Assert-ReleasePackageDirectoryNameSafe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DirectoryName
    )
    if ([string]::IsNullOrWhiteSpace($DirectoryName)) {
        Fail 'Release package directory name is blank'
    }
    if (-not [System.Text.RegularExpressions.Regex]::IsMatch($DirectoryName, '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')) {
        Fail "Invalid release package directory name: $DirectoryName"
    }
}

function Connect-NasReleaseShare {
    param(
        [Parameter(Mandatory = $true)]
        $NasConfig
    )
    $root = "\\$($NasConfig.server)\$($NasConfig.share)"
    Info "Mounting NAS release repository: \\$($NasConfig.server)\$($NasConfig.share)\$NasReleaseRoot"
    $connectCommand = 'net use "{0}" /user:{1} {2}' -f $root, ([string]$NasConfig.username), ([string]$NasConfig.password)
    $displayCommand = 'net use "\\' + $NasConfig.server + '\' + $NasConfig.share + '" /user:' + $NasConfig.username + ' <redacted>'
    Invoke-CheckedShell -Command $connectCommand -DisplayCommand $displayCommand
    return @{
        Root = $root
    }
}

function Disconnect-NasReleaseShare {
    param($MountInfo)
    if ($MountInfo -and $MountInfo.Root) {
        Invoke-NasReleaseShareDisconnect -Root ([string]$MountInfo.Root)
    }
}

function Invoke-NasReleaseShareDisconnect {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $displayCommand = 'net use "' + $Root + '" /delete /y'
    Info "Run shell: $displayCommand"
    $result = Invoke-ProcessCapture -FilePath 'net.exe' -ArgumentList @('use', $Root, '/delete', '/y')
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $cleanOutput = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    if ($cleanOutput) {
        Write-Host $cleanOutput
    }
    if ($result.ExitCode -eq 0) {
        return
    }
    if ($result.ExitCode -eq 2 -and $cleanOutput -match 'NET HELPMSG 2250') {
        Info "NAS release repository mapping already absent; cleanup completed: $Root"
        return
    }
    Fail "Shell command failed with exit code $($result.ExitCode): $displayCommand`n$cleanOutput"
}

function Get-NasReleasePackagePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NasRoot,
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $relativeRoot = Join-NasRelativePath -Parts @($NasReleaseRoot)
    $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
    return Join-Path (Join-Path $NasRoot $relativeRoot) $packageDirectoryName
}

function Copy-ReleasePackageToNas {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $nasConfig = Read-NasReleaseConfig
    $mountInfo = $null
    try {
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        $targetRoot = Join-Path $mountInfo.Root (Join-NasRelativePath -Parts @($NasReleaseRoot))
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        $targetPath = Join-Path $targetRoot $packageDirectoryName
        if (Test-Path -LiteralPath $targetPath) {
            Fail "NAS release package already exists: $NasReleaseRoot/$packageDirectoryName"
        }
        New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
        Copy-Item -LiteralPath $releaseDir -Destination $targetRoot -Recurse -Force
        Info "Release package uploaded to NAS: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
}

function Should-RequireNasReleaseTestedForDeploy {
    if (-not $RequireTested) {
        return $false
    }
    if ($Environment -eq 'prod') {
        return $true
    }
    if ($Environment -eq 'backup') {
        Info 'TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED: Backup deploy recovery gate temporarily disabled by operator request; tested.json rollback compatibility evidence is not required for backup environment.'
        return $false
    }
    return $false
}

function Copy-ReleasePackageFromNas {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $nasConfig = Read-NasReleaseConfig
    $mountInfo = $null
    try {
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        $sourcePath = Get-NasReleasePackagePath -NasRoot $mountInfo.Root -PackageTag $PackageTag
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
            Fail "NAS release package not found: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        }
        if (Should-RequireNasReleaseTestedForDeploy) {
            Assert-NasReleaseTested -MountedPackagePath $sourcePath -PackageTag $PackageTag
        }
        if (Test-Path -LiteralPath $releaseDir) {
            Remove-Item -LiteralPath $releaseDir -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $localTempRoot | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $localTempRoot -Recurse -Force
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        Info "Release package downloaded from NAS: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
}

function Get-RequiredJsonPropertyValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$JsonObject,
        [Parameter(Mandatory = $true)]
        [string]$PropertyName,
        [Parameter(Mandatory = $true)]
        [string]$ArtifactName
    )

    $property = $JsonObject.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
        Fail "$ArtifactName missing $PropertyName"
    }
    return $property.Value
}

function Read-NasReleaseManifestForCompatibility {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [Parameter(Mandatory = $true)]
        [string]$PackageTag,
        [Parameter(Mandatory = $true)]
        [string]$PackageDirectoryName
    )

    $manifestPath = Join-Path $PackagePath 'release-manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        Fail "release-manifest.json missing in NAS release package: $NasReleaseRoot/$PackageDirectoryName (releaseTag=$PackageTag)"
    }

    try {
        $manifestText = [System.IO.File]::ReadAllText($manifestPath, [System.Text.UTF8Encoding]::new($false))
        $manifest = $manifestText | ConvertFrom-Json
    } catch {
        Fail "release-manifest.json parse failed in NAS release package: $($_.Exception.Message)"
    }

    $manifestPackageDirectoryName = [string](Get-RequiredJsonPropertyValue -JsonObject $manifest -PropertyName 'packageDirectoryName' -ArtifactName 'release-manifest.json')
    if ($manifestPackageDirectoryName -ne $PackageDirectoryName) {
        Fail "release-manifest.json packageDirectoryName differs from package directory: $manifestPackageDirectoryName != $PackageDirectoryName"
    }

    $publishScope = [string](Get-RequiredJsonPropertyValue -JsonObject $manifest -PropertyName 'publishScope' -ArtifactName 'release-manifest.json')
    if ($publishScope -notin @('code-only', 'with-data')) {
        Fail "Invalid release package publishScope: $publishScope"
    }

    $onlyOfficeProperty = $manifest.PSObject.Properties['onlyOfficeIncluded']
    if ($null -eq $onlyOfficeProperty) {
        Fail 'release-manifest.json missing onlyOfficeIncluded; rebuild the release package'
    }
    if ($onlyOfficeProperty.Value -isnot [bool]) {
        Fail "Invalid release package onlyOfficeIncluded: $($onlyOfficeProperty.Value)"
    }

    return $manifest
}

function New-RollbackCompatibilityEvidence {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Manifest,
        [Parameter(Mandatory = $true)]
        [string]$PackageTag,
        [Parameter(Mandatory = $true)]
        [string]$PackageDirectoryName,
        [Parameter(Mandatory = $true)]
        [string]$CheckedAt,
        [Parameter(Mandatory = $true)]
        [string]$SelectedRecoverySetCandidateId,
        [Parameter(Mandatory = $true)]
        [string]$RecoverySetId,
        [Parameter(Mandatory = $true)]
        [string]$RecoverySetManifestHash,
        [Parameter(Mandatory = $true)]
        [string]$RecoverySetProgramVersion,
        [Parameter(Mandatory = $true)]
        [string]$RecoverySetRedisPolicy
    )

    $blockedReasons = New-Object System.Collections.Generic.List[string]
    if ($Manifest.publishScope -ne 'code-only') {
        $blockedReasons.Add("release package publishScope=$($Manifest.publishScope) is not code-only")
    }
    if ($RecoverySetProgramVersion -ne $PackageDirectoryName) {
        $blockedReasons.Add("recoverySet programVersion=$RecoverySetProgramVersion differs from packageDirectoryName=$PackageDirectoryName")
    }

    if ($blockedReasons.Count -eq 0) {
        $status = 'COMPATIBLE'
        $summary = "release package $PackageDirectoryName tested with recovery set $RecoverySetId; app-only rollback compatibility confirmed"
    } else {
        $status = 'BLOCKED'
        $summary = "app-only rollback blocked: " + (($blockedReasons.ToArray()) -join '; ')
    }

    return [ordered]@{
        schemaVersion = 'v1'
        packageDirectoryName = $PackageDirectoryName
        status = $status
        checkedAt = $CheckedAt
        summary = $summary
        release = [ordered]@{
            releaseTag = $PackageTag
            publishScope = [string]$Manifest.publishScope
            onlyOfficeIncluded = [bool]$Manifest.onlyOfficeIncluded
        }
        recoverySet = [ordered]@{
            selectedRecoverySetCandidateId = $SelectedRecoverySetCandidateId
            recoverySetId = $RecoverySetId
            recoverySetManifestHash = $RecoverySetManifestHash.ToLowerInvariant()
            programVersion = $RecoverySetProgramVersion
            redisPolicy = $RecoverySetRedisPolicy
        }
        compatibility = [ordered]@{
            appOnlyRollback = $status
            blockedReasons = @($blockedReasons.ToArray())
        }
    }
}

function Write-NasRollbackCompatibilityEvidence {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [Parameter(Mandatory = $true)]
        [object]$Evidence
    )

    $compatibilityPath = Join-Path $PackagePath 'rollback-compatibility.json'
    $compatibilityJson = $Evidence | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($compatibilityPath, $compatibilityJson, [System.Text.UTF8Encoding]::new($false))
}

function Mark-NasReleaseTested {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $nasConfig = Read-NasReleaseConfig
    $mountInfo = $null
    try {
        if ([string]::IsNullOrWhiteSpace($TestConclusion)) {
            Fail 'TestConclusion is required when marking a release package as tested.'
        }
        if ([string]::IsNullOrWhiteSpace($SelectedRecoverySetCandidateId)) {
            Fail 'SelectedRecoverySetCandidateId is required when marking a release package as tested.'
        }
        if ([string]::IsNullOrWhiteSpace($RecoverySetId)) {
            Fail 'RecoverySetId is required when marking a release package as tested.'
        }
        if ([string]::IsNullOrWhiteSpace($RecoverySetManifestHash)) {
            Fail 'RecoverySetManifestHash is required when marking a release package as tested.'
        }
        if ([string]::IsNullOrWhiteSpace($RecoverySetProgramVersion)) {
            Fail 'RecoverySetProgramVersion is required when marking rollback compatibility evidence.'
        }
        if ([string]::IsNullOrWhiteSpace($RecoverySetRedisPolicy)) {
            Fail 'RecoverySetRedisPolicy is required when marking rollback compatibility evidence.'
        }
        if ($RecoverySetManifestHash -notmatch '^[0-9a-fA-F]{64}$') {
            Fail 'RecoverySetManifestHash must be a SHA-256 hex value when marking rollback compatibility evidence.'
        }
        $expectedRecoverySetCandidateId = "restore:$RecoverySetId"
        if ($SelectedRecoverySetCandidateId -ne $expectedRecoverySetCandidateId) {
            Fail "SelectedRecoverySetCandidateId must match RecoverySetId when marking rollback compatibility evidence: expected $expectedRecoverySetCandidateId"
        }
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        $packagePath = Get-NasReleasePackagePath -NasRoot $mountInfo.Root -PackageTag $PackageTag
        if (-not (Test-Path -LiteralPath $packagePath)) {
            $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
            Fail "NAS release package not found: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        }
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        $manifest = Read-NasReleaseManifestForCompatibility -PackagePath $packagePath -PackageTag $PackageTag -PackageDirectoryName $packageDirectoryName
        $checkedAt = (Get-Date).ToUniversalTime().ToString('o')
        $tested = [ordered]@{
            releaseTag = $PackageTag
            packageDirectoryName = $packageDirectoryName
            testedAt = $checkedAt
            operatorName = $OperatorName
            testConclusion = $TestConclusion
            recoverySet = [ordered]@{
                selectedRecoverySetCandidateId = $SelectedRecoverySetCandidateId
                recoverySetId = $RecoverySetId
                recoverySetManifestHash = $RecoverySetManifestHash
                programVersion = $RecoverySetProgramVersion
                redisPolicy = $RecoverySetRedisPolicy
            }
        } | ConvertTo-Json -Depth 4
        $compatibility = New-RollbackCompatibilityEvidence `
            -Manifest $manifest `
            -PackageTag $PackageTag `
            -PackageDirectoryName $packageDirectoryName `
            -CheckedAt $checkedAt `
            -SelectedRecoverySetCandidateId $SelectedRecoverySetCandidateId `
            -RecoverySetId $RecoverySetId `
            -RecoverySetManifestHash $RecoverySetManifestHash `
            -RecoverySetProgramVersion $RecoverySetProgramVersion `
            -RecoverySetRedisPolicy $RecoverySetRedisPolicy
        [System.IO.File]::WriteAllText((Join-Path $packagePath 'tested.json'), $tested, [System.Text.UTF8Encoding]::new($false))
        Write-NasRollbackCompatibilityEvidence -PackagePath $packagePath -Evidence $compatibility
        Info "Release package marked as tested: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        Info "rollback-compatibility.json status=$($compatibility['status']) recorded: $NasReleaseRoot/$packageDirectoryName/rollback-compatibility.json"
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
}

function Assert-NasReleaseTested {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MountedPackagePath,
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $testedPath = Join-Path $MountedPackagePath 'tested.json'
    if (-not (Test-Path -LiteralPath $testedPath)) {
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        Fail "Release package has not been marked as tested: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
    }
}

function Read-ReleaseManifest {
    $manifestPath = Join-Path $releaseDir 'release-manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        Fail "release-manifest.json missing in release package: $manifestPath"
    }

    try {
        $manifestText = [System.IO.File]::ReadAllText($manifestPath, [System.Text.UTF8Encoding]::new($false))
        return $manifestText | ConvertFrom-Json
    } catch {
        Fail "release-manifest.json parse failed: $($_.Exception.Message)"
    }
}

function Resolve-DeployReleasePackageScope {
    $manifest = Read-ReleaseManifest
    $publishScope = ''
    if ($null -ne $manifest.publishScope) {
        $publishScope = ([string]$manifest.publishScope).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($publishScope)) {
        Fail 'release-manifest.json missing publishScope'
    }
    if ($publishScope -notin @('code-only', 'with-data')) {
        Fail "Invalid release package publishScope: $publishScope"
    }
    return $publishScope
}

function Resolve-DeployReleasePackageOnlyOfficeIncluded {
    $manifest = Read-ReleaseManifest
    if ($null -eq $manifest.onlyOfficeIncluded) {
        Fail 'release-manifest.json missing onlyOfficeIncluded; rebuild the release package'
    }
    if ($manifest.onlyOfficeIncluded -isnot [bool]) {
        Fail "Invalid release package onlyOfficeIncluded: $($manifest.onlyOfficeIncluded)"
    }
    return [bool]$manifest.onlyOfficeIncluded
}

function Resolve-DeployReleasePackageComponent {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$ComponentExplicit
    )

    if ($ComponentExplicit) {
        return $Component
    }

    $manifest = Read-ReleaseManifest
    $manifestComponent = ''
    if ($null -ne $manifest.component) {
        $manifestComponent = ([string]$manifest.component).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($manifestComponent)) {
        Fail 'release-manifest.json missing component; rebuild the release package or pass -Component explicitly'
    }
    if ($manifestComponent -notin @('full', 'intruoyi', 'backend', 'frontend', 'website')) {
        Fail "Invalid release package component: $manifestComponent"
    }
    return $manifestComponent
}

function Assert-DeployReleasePackageArtifactsForScope {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PublishScope
    )

    if (-not $publishBackend) {
        return
    }
    if ($PublishScope -ne 'with-data') {
        return
    }

    if (-not (Test-Path -LiteralPath $dbDump)) {
        Fail "with-data release package is missing MySQL dump: $dbDump"
    }
    $minioSnapshotLocal = Join-Path $releaseDir 'minio\yudao'
    if (-not (Test-Path -LiteralPath $minioSnapshotLocal)) {
        Fail "with-data release package is missing MinIO snapshot: $minioSnapshotLocal"
    }
    $dccObjectInventoryPath = Join-Path $releaseDir 'manifest\dcc-object-inventory.json'
    if (-not (Test-Path -LiteralPath $dccObjectInventoryPath)) {
        Fail "with-data release package is missing DCC object inventory: $dccObjectInventoryPath"
    }
    try {
        $dccObjectInventory = [System.IO.File]::ReadAllText($dccObjectInventoryPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    } catch {
        Fail "with-data release package DCC object inventory is not valid JSON: $($_.Exception.Message)"
    }
    if ($dccObjectInventory.schemaVersion -ne 'v1') {
        Fail "with-data release package DCC object inventory schemaVersion is invalid: $($dccObjectInventory.schemaVersion)"
    }
    foreach ($dccFile in @($dccObjectInventory.files)) {
        if ([string]::IsNullOrWhiteSpace($dccFile.snapshotPath)) {
            Fail "with-data release package DCC object inventory contains an empty snapshotPath for file id=$($dccFile.fileId)"
        }
        $dccSnapshotPath = Join-Path $releaseDir ([string]$dccFile.snapshotPath)
        if (-not (Test-Path -LiteralPath $dccSnapshotPath -PathType Leaf)) {
            Fail "DCC_OBJECT_INVENTORY_FILE_MISSING: with-data release package is missing listed DCC snapshot object file id=$($dccFile.fileId) path=$($dccFile.snapshotPath)"
        }
        if ([string]::IsNullOrWhiteSpace($dccFile.sha256)) {
            Fail "with-data release package DCC object inventory missing sha256 for file id=$($dccFile.fileId)"
        }
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dccSnapshotPath).Hash.ToLowerInvariant()
        if ($actualHash -ne ([string]$dccFile.sha256).ToLowerInvariant()) {
            Fail "DCC_OBJECT_INVENTORY_HASH_MISMATCH: with-data release package DCC snapshot object hash mismatch file id=$($dccFile.fileId) path=$($dccFile.snapshotPath)"
        }
    }
}

function Invoke-LocalMySqlRaw {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Sql,
        [string]$Purpose = 'local MySQL query'
    )

    $result = Invoke-ProcessCaptureWithInput -FilePath 'docker' -ArgumentList @(
        'exec',
        '-i',
        $LocalMySqlContainer,
        'sh',
        '-c',
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --database=ruoyi-vue-pro --default-character-set=utf8mb4 --batch --raw --skip-column-names'
    ) -StandardInput $Sql
    $cleanOutput = Remove-SshNoise ((($result.StdOut) + "`n" + ($result.StdErr)).Trim())
    if ($result.ExitCode -ne 0) {
        Fail "$Purpose failed: $cleanOutput"
    }
    return ($result.StdOut).Trim()
}

function Get-DccReleaseObjectReferenceRows {
    $sql = @'
SELECT
  REPLACE(TO_BASE64(CAST(JSON_OBJECT(
      'fileId', r.file_id,
      'objectPath', COALESCE(f.path, ''),
      'name', COALESCE(f.name, ''),
      'contentType', COALESCE(f.type, ''),
      'declaredBytes', COALESCE(f.size, -1),
      'url', COALESCE(f.url, ''),
      'references', COALESCE(GROUP_CONCAT(DISTINCT CONCAT(r.source_table, '.', r.source_column) ORDER BY r.source_table, r.source_column SEPARATOR ','), '')
    ) AS CHAR CHARACTER SET utf8mb4)
  ), '\n', '')
FROM (
  SELECT source_file_id AS file_id, 'dcc_controlled_file' AS source_table, 'source_file_id' AS source_column FROM dcc_controlled_file WHERE source_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT original_file_id, 'dcc_controlled_file', 'original_file_id' FROM dcc_controlled_file WHERE original_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT drawing_pdf_file_id, 'dcc_controlled_file', 'drawing_pdf_file_id' FROM dcc_controlled_file WHERE drawing_pdf_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT training_record_file_id, 'dcc_controlled_file', 'training_record_file_id' FROM dcc_controlled_file WHERE training_record_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT published_file_id, 'dcc_controlled_file', 'published_file_id' FROM dcc_controlled_file WHERE published_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT stamped_file_id, 'dcc_controlled_file', 'stamped_file_id' FROM dcc_controlled_file WHERE stamped_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT source_file_id, 'dcc_controlled_file_stamp', 'source_file_id' FROM dcc_controlled_file_stamp WHERE source_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT output_file_id, 'dcc_controlled_file_stamp', 'output_file_id' FROM dcc_controlled_file_stamp WHERE output_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT output_file_id, 'dcc_external_file_review', 'output_file_id' FROM dcc_external_file_review WHERE output_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT source_file_id, 'dcc_controlled_file_signature', 'source_file_id' FROM dcc_controlled_file_signature WHERE source_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT controlled_copy_file_id, 'dcc_controlled_file_signature', 'controlled_copy_file_id' FROM dcc_controlled_file_signature WHERE controlled_copy_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT template_file_id, 'dcc_approval_print_template', 'template_file_id' FROM dcc_approval_print_template WHERE template_file_id IS NOT NULL AND deleted = b'0'
) r
LEFT JOIN infra_file f ON f.id = r.file_id AND f.deleted = b'0'
GROUP BY r.file_id, f.path, f.name, f.type, f.size, f.url
ORDER BY r.file_id
'@

    $output = Invoke-LocalMySqlRaw -Sql $sql -Purpose 'DCC release object reference query'
    $rows = [System.Collections.Generic.List[object]]::new()
    if ([string]::IsNullOrWhiteSpace($output)) {
        return $rows.ToArray()
    }
    $strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
    foreach ($line in ($output -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        try {
            $jsonBytes = [Convert]::FromBase64String($line.Trim())
            $json = $strictUtf8.GetString($jsonBytes)
        } catch {
            Fail "DCC object inventory base64 row is malformed: $line"
        }
        try {
            $record = $json | ConvertFrom-Json
        } catch {
            Fail "DCC object inventory JSON row is malformed after base64 decode: $json"
        }
        $references = @((([string]$record.references) -split ',') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        [void]$rows.Add([ordered]@{
            fileId = [long]$record.fileId
            objectPath = [string]$record.objectPath
            name = [string]$record.name
            contentType = [string]$record.contentType
            declaredBytes = [long]$record.declaredBytes
            url = [string]$record.url
            references = $references
        })
    }
    return $rows.ToArray()
}

function Resolve-DccSnapshotObjectPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SnapshotRoot,
        [Parameter(Mandatory = $true)]
        [string]$ObjectPath
    )

    $normalizedObjectPath = $ObjectPath.Replace('\', '/').TrimStart('/')
    if ([string]::IsNullOrWhiteSpace($normalizedObjectPath)) {
        Fail 'DCC_OBJECT_PATH_MISSING: DCC infra_file.path is empty.'
    }
    $segments = $normalizedObjectPath.Split('/')
    $resolvedPath = $SnapshotRoot
    foreach ($segment in $segments) {
        if ([string]::IsNullOrWhiteSpace($segment) -or $segment -eq '.' -or $segment -eq '..') {
            Fail "DCC_OBJECT_PATH_UNSAFE: DCC object path contains an unsafe segment: $ObjectPath"
        }
        $resolvedPath = Join-Path $resolvedPath $segment
    }
    return $resolvedPath
}

function Write-DccObjectInventoryForReleasePackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MinioSnapshotRoot
    )

    Info 'Generating DCC object inventory for with-data release package'
    $rows = @(Get-DccReleaseObjectReferenceRows)
    $inventoryFiles = [System.Collections.Generic.List[object]]::new()
    $totalBytes = [int64]0
    $processed = 0
    $totalRows = $rows.Count
    foreach ($row in $rows) {
        $processed += 1
        if ([string]::IsNullOrWhiteSpace($row.objectPath)) {
            Fail "DCC_INFRA_FILE_MISSING: DCC file reference points to missing infra_file id=$($row.fileId)"
        }
        $snapshotFile = Resolve-DccSnapshotObjectPath -SnapshotRoot $MinioSnapshotRoot -ObjectPath $row.objectPath
        if (-not (Test-Path -LiteralPath $snapshotFile -PathType Leaf)) {
            Fail "DCC_OBJECT_SNAPSHOT_MISSING: DCC file id=$($row.fileId) object=$($row.objectPath) is missing from release MinIO snapshot."
        }
        $snapshotItem = Get-Item -LiteralPath $snapshotFile
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $snapshotFile
        $snapshotRelativePath = $snapshotFile.Substring($releaseDir.Length).TrimStart('\', '/').Replace('\', '/')
        $totalBytes += [int64]$snapshotItem.Length
        [void]$inventoryFiles.Add([ordered]@{
            fileId = $row.fileId
            objectPath = $row.objectPath
            snapshotPath = $snapshotRelativePath
            sha256 = $hash.Hash.ToLowerInvariant()
            bytes = [int64]$snapshotItem.Length
            declaredBytes = $row.declaredBytes
            name = $row.name
            contentType = $row.contentType
            references = $row.references
        })
        if ($processed -eq 1 -or ($processed % 500) -eq 0 -or $processed -eq $totalRows) {
            Info "DCC object inventory progress: $processed/$totalRows"
        }
    }

    $manifestDir = Join-Path $releaseDir 'manifest'
    New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
    $inventory = [ordered]@{
        schemaVersion = 'v1'
        generatedAt = (Get-Date).ToUniversalTime().ToString('o')
        source = [ordered]@{
            database = 'ruoyi-vue-pro'
            bucket = 'yudao'
            localMySqlContainer = $LocalMySqlContainer
            localMinioContainer = $LocalMinioContainer
        }
        counts = [ordered]@{
            referencedFiles = $inventoryFiles.Count
            bytes = $totalBytes
        }
        files = $inventoryFiles.ToArray()
    } | ConvertTo-Json -Depth 8
    $inventoryPath = Join-Path $manifestDir 'dcc-object-inventory.json'
    [System.IO.File]::WriteAllText($inventoryPath, $inventory, [System.Text.UTF8Encoding]::new($false))
    Info "DCC object inventory created: manifest/dcc-object-inventory.json ($($inventoryFiles.Count) file references)"
}

function Write-NasReleaseDeploymentHistory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag,

        [Parameter(Mandatory = $true)]
        [string]$HistoryAction,

        [Parameter(Mandatory = $true)]
        [ValidateSet('prod', 'backup')]
        [string]$HistoryEnvironment
    )
    $nasConfig = Read-NasReleaseConfig
    $mountInfo = $null
    try {
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        $packagePath = Get-NasReleasePackagePath -NasRoot $mountInfo.Root -PackageTag $PackageTag
        if (-not (Test-Path -LiteralPath $packagePath)) {
            $historyPackageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
            Fail "NAS release package not found for prod history: $NasReleaseRoot/$historyPackageDirectoryName (releaseTag=$PackageTag)"
        }
        $historyPackageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        $deployedAt = (Get-Date).ToUniversalTime()
        $record = [ordered]@{
            releaseTag = $PackageTag
            packageDirectoryName = $historyPackageDirectoryName
            imageTag = $historyPackageDirectoryName
            action = $HistoryAction
            environment = $HistoryEnvironment
            deployedAt = $deployedAt.ToString('o')
            operatorName = $OperatorName
        } | ConvertTo-Json -Depth 4
        $historyDirectoryName = if ($HistoryEnvironment -eq 'backup') { 'backup-deployments' } else { 'prod-deployments' }
        $latestFileName = if ($HistoryEnvironment -eq 'backup') { 'backup-latest.json' } else { 'prod-latest.json' }
        $historyDir = Join-Path $packagePath $historyDirectoryName
        New-Item -ItemType Directory -Force -Path $historyDir | Out-Null
        $historyFile = Join-Path $historyDir ($deployedAt.ToString('yyyyMMdd_HHmmss') + "_$HistoryAction.json")
        $encoding = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($historyFile, $record, $encoding)
        [System.IO.File]::WriteAllText((Join-Path $packagePath $latestFileName), $record, $encoding)
        Info "$HistoryEnvironment release history recorded: $NasReleaseRoot/$historyPackageDirectoryName/$latestFileName"
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
}

function ConvertTo-ReleaseStringSha256Digest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $hashBytes = $sha.ComputeHash($bytes)
        $hex = -join ($hashBytes | ForEach-Object { $_.ToString('x2') })
        return "sha256:$hex"
    } finally {
        $sha.Dispose()
    }
}

function ConvertTo-ReleaseFileSha256Digest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Fail "Manifest v1 file hash input missing: $Path"
    }
    return 'sha256:' + (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function ConvertTo-ReleaseManifestSha256Digest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HashValue
    )
    $value = $HashValue.Trim().ToLowerInvariant()
    if ($value -match '^sha256:[a-f0-9]{64}$') {
        return $value
    }
    if ($value -match '^[a-f0-9]{64}$') {
        return "sha256:$value"
    }
    Fail "Manifest v1 sha256 value is invalid: $HashValue"
}

function Get-ReleasePackageRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FullPath
    )
    return $FullPath.Substring($releaseDir.Length).TrimStart('\', '/').Replace('\', '/')
}

function Get-ReleaseGitValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$Purpose
    )
    $value = & git -C $RepoPath @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        Fail "Manifest v1 requires git metadata for ${Purpose}: $RepoPath"
    }
    return ([string]$value).Trim()
}

function New-ReleaseSourceRepoEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$PathRole,
        [Parameter(Mandatory = $true)]
        [string]$RepoPath
    )
    $commit = Get-ReleaseGitValue -RepoPath $RepoPath -Arguments @('rev-parse', 'HEAD') -Purpose "$Name commit"
    $branch = Get-ReleaseGitValue -RepoPath $RepoPath -Arguments @('rev-parse', '--abbrev-ref', 'HEAD') -Purpose "$Name branch"
    $statusText = & git -C $RepoPath status --short
    if ($LASTEXITCODE -ne 0) {
        Fail "Manifest v1 requires git status for $Name`: $RepoPath"
    }
    $dirty = -not [string]::IsNullOrWhiteSpace(($statusText -join "`n"))
    $dirtySummaryHash = if ($dirty) {
        ConvertTo-ReleaseStringSha256Digest -Value (($statusText | Sort-Object) -join "`n")
    } else {
        $null
    }

    return [ordered]@{
        name = $Name
        pathRole = $PathRole
        commit = $commit
        branch = $branch
        dirty = [bool]$dirty
        dirtySummaryHash = $dirtySummaryHash
    }
}

function New-ReleaseSourceRepoManifestEntries {
    $entries = @()
    if ($publishBackend) {
        $entries += New-ReleaseSourceRepoEntry -Name 'ruoyi-vue-pro' -PathRole 'backend' -RepoPath $backendRepo
    }
    if ($publishFrontend) {
        $entries += New-ReleaseSourceRepoEntry -Name 'yudao-ui-admin-vue3' -PathRole 'admin-frontend' -RepoPath $frontendDir
    }
    if ($publishWebsite) {
        $entries += New-ReleaseSourceRepoEntry -Name 'Website' -PathRole 'website' -RepoPath $websiteRepo
    }
    return @($entries)
}

function Get-ReleaseDependencyHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ModuleName
    )
    switch ($ModuleName) {
        'backend' { return ConvertTo-ReleaseFileSha256Digest -Path (Join-Path $backendRepo 'pom.xml') }
        'admin-frontend' { return ConvertTo-ReleaseFileSha256Digest -Path (Join-Path $frontendDir 'pnpm-lock.yaml') }
        'website' { return ConvertTo-ReleaseFileSha256Digest -Path (Join-Path $websiteRepo 'package-lock.json') }
        'onlyoffice' { return ConvertTo-ReleaseStringSha256Digest -Value "image:$onlyOfficeImage" }
        'database-contract' { return ConvertTo-ReleaseStringSha256Digest -Value 'database-contract:required-sql' }
        'required-sql' { return ConvertTo-ReleaseStringSha256Digest -Value 'required-sql:package-files' }
        'runtime-env' { return ConvertTo-ReleaseStringSha256Digest -Value 'runtime-env:compose-env' }
        'packaging-manifest' { return ConvertTo-ReleaseStringSha256Digest -Value 'packaging-manifest:v1' }
        default { Fail "Unknown manifest v1 build module dependency hash: $ModuleName" }
    }
}

function Read-ReleaseMigrationMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SqlPath
    )

    if (-not (Test-Path -LiteralPath $SqlPath -PathType Leaf)) {
        Fail "Release migration SQL missing before metadata read: $SqlPath"
    }
    $text = [System.IO.File]::ReadAllText($SqlPath, [System.Text.UTF8Encoding]::new($false))
    $match = [regex]::Match(
        $text,
        '^\s*--\s*release-migration\s*:\s*(.+?)\s*$',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Multiline
    )
    if (-not $match.Success) {
        Fail "Release migration metadata missing: $SqlPath"
    }

    $metadata = [ordered]@{
        allowedEnvironments = @('test', 'backup', 'prod')
        dependsOn = @()
        type = 'schema'
        riskLevel = 'medium'
    }
    foreach ($segment in ($match.Groups[1].Value -split ';')) {
        $trimmed = $segment.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }
        $parts = $trimmed -split '=', 2
        if ($parts.Count -ne 2) {
            Fail "Invalid release migration metadata segment in ${SqlPath}: $trimmed"
        }
        $key = $parts[0].Trim()
        $values = @($parts[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        switch ($key) {
            'allowedEnvironments' {
                if ($values.Count -eq 0) {
                    Fail "allowedEnvironments is empty in release migration metadata: $SqlPath"
                }
                foreach ($value in $values) {
                    if ($value -notin @('test', 'backup', 'prod')) {
                        Fail "Invalid allowedEnvironments value in release migration metadata: $SqlPath -> $value"
                    }
                }
                $metadata.allowedEnvironments = @($values)
            }
            'dependsOn' {
                $metadata.dependsOn = @($values)
            }
            'type' {
                if ($values.Count -ne 1 -or $values[0] -notin @('schema', 'data', 'menu', 'config', 'permission', 'seed')) {
                    Fail "Invalid type in release migration metadata: $SqlPath"
                }
                $metadata.type = [string]$values[0]
            }
            'riskLevel' {
                if ($values.Count -ne 1 -or $values[0] -notin @('low', 'medium', 'high')) {
                    Fail "Invalid riskLevel in release migration metadata: $SqlPath"
                }
                $metadata.riskLevel = [string]$values[0]
            }
            default {
                Fail "Unknown release migration metadata key in ${SqlPath}: $key"
            }
        }
    }
    return $metadata
}

function New-ReleaseRequiredSqlManifestEntries {
    $entries = @()
    foreach ($entry in $requiredDatabaseSqlScripts) {
        $relativePath = [string]$entry.Path
        $fileName = Get-RequiredDatabaseSqlFileName -RelativePath $relativePath
        $packageSqlPath = Join-Path $requiredSqlLocalDir $fileName
        if (-not (Test-Path -LiteralPath $packageSqlPath -PathType Leaf)) {
            Fail "Manifest v1 required SQL missing from package: $packageSqlPath"
        }
        $sourceRelativePath = $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $sourcePath = Join-Path $backendRepo $sourceRelativePath
        $metadata = Read-ReleaseMigrationMetadata -SqlPath $sourcePath
        $entries += [ordered]@{
            id = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
            migrationId = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
            file = "required-sql/$fileName"
            sourcePath = $relativePath
            type = [string]$metadata.type
            allowedEnvironments = @($metadata.allowedEnvironments)
            dependsOn = @($metadata.dependsOn)
            riskLevel = [string]$metadata.riskLevel
            sha256 = ConvertTo-ReleaseFileSha256Digest -Path $packageSqlPath
            requiredPreconditions = @(
                [ordered]@{
                    type = 'schema-preflight-pass'
                    required = $true
                    resolution = 'Run schema preflight and apply the missing prerequisite migration before executing required SQL.'
                }
            )
        }
    }
    return @($entries)
}

function Invoke-ReleaseMigrationPolicyGate {
    $policyGateScript = Join-Path $maintenanceReleaseScriptRoot 'run-release-migration-policy-gate.py'
    if (-not (Test-Path -LiteralPath $policyGateScript -PathType Leaf)) {
        Fail "Migration policy gate script missing: $policyGateScript"
    }
    foreach ($root in @(Get-ReleaseDatabaseSqlRoots)) {
        $sqlRoot = [string]$root.Root
        $argumentList = @(
            '-X',
            'utf8',
            $policyGateScript,
            '--sql-root',
            $sqlRoot,
            '--file-prefix',
            ([string]$root.RelativePath)
        )
        foreach ($fileName in @($root.IncludeFiles)) {
            $argumentList += @('--sql-file', (Join-Path $sqlRoot ([string]$fileName)))
        }
        $result = Invoke-ProcessCapture -FilePath 'python' -ArgumentList $argumentList -WorkingDirectory $backendRepo
        $output = (($result.StdOut + "`n" + $result.StdErr).Trim())
        if ($output) {
            Info "Migration policy gate output: $output"
        }
        if ($result.ExitCode -ne 0) {
            Fail 'Migration policy gate failed; build-release is blocked before package manifest generation.'
        }
    }
}

function New-ReleaseMigrationPlanEntries {
    param(
        [Parameter(Mandatory = $true)]
        [array]$RequiredSqlEntries
    )
    $entries = @()
    foreach ($requiredSql in @($RequiredSqlEntries)) {
        $entries += [ordered]@{
            id = [string]$requiredSql.id
            migrationId = [string]$requiredSql.migrationId
            direction = 'forward'
            destructive = $false
            file = [string]$requiredSql.file
            sha256 = [string]$requiredSql.sha256
            type = [string]$requiredSql.type
            allowedEnvironments = @($requiredSql.allowedEnvironments)
            dependsOn = @($requiredSql.dependsOn)
            riskLevel = [string]$requiredSql.riskLevel
            requiredPreflight = $true
        }
    }
    return @($entries)
}

function Get-ReleaseSchemaDigest {
    param(
        [Parameter(Mandatory = $true)]
        [array]$RequiredSqlEntries
    )
    $schemaContract = [ordered]@{
        requiredSql = @($RequiredSqlEntries)
        publishScope = if ($SkipDatabaseSync -and $SkipMinioSync) { 'code-only' } else { 'with-data' }
    } | ConvertTo-Json -Depth 8 -Compress
    return ConvertTo-ReleaseStringSha256Digest -Value $schemaContract
}

function Get-ReleaseComponentManifestNames {
    $components = @()
    if ($publishBackend) {
        $components += @('backend', 'database-contract', 'required-sql', 'runtime-env')
    }
    if ($publishFrontend) {
        $components += 'admin-frontend'
    }
    if ($publishWebsite) {
        $components += 'website'
    }
    if ($publishBackend -and $IncludeOnlyOffice) {
        $components += 'onlyoffice'
    }
    $components += 'packaging-manifest'
    return @($components | Select-Object -Unique)
}

function Get-ReleaseModuleSourceHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ModuleName,
        [Parameter(Mandatory = $true)]
        [array]$SourceRepos
    )
    $repo = $null
    switch ($ModuleName) {
        'backend' { $repo = @($SourceRepos | Where-Object { $_.pathRole -eq 'backend' }) | Select-Object -First 1 }
        'admin-frontend' { $repo = @($SourceRepos | Where-Object { $_.pathRole -eq 'admin-frontend' }) | Select-Object -First 1 }
        'website' { $repo = @($SourceRepos | Where-Object { $_.pathRole -eq 'website' }) | Select-Object -First 1 }
    }
    if ($null -ne $repo) {
        return ConvertTo-ReleaseStringSha256Digest -Value (($repo | ConvertTo-Json -Depth 4 -Compress))
    }
    return ConvertTo-ReleaseStringSha256Digest -Value "module:$ModuleName"
}

function Get-ReleaseComponentArtifactHash {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ModuleName,
        [Parameter(Mandatory = $true)]
        [array]$LegacyArtifacts,
        [Parameter(Mandatory = $true)]
        [string]$SchemaDigest
    )
    $matchingArtifacts = @()
    switch ($ModuleName) {
        'backend' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { $_.path -like 'intruoyi-images_*' }) }
        'admin-frontend' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { $_.path -like 'intruoyi-images_*' }) }
        'onlyoffice' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { $_.path -like 'intruoyi-images_*' }) }
        'website' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { ([string]$_.path).StartsWith('website/') }) }
        'database-contract' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { ([string]$_.path).StartsWith('manifest/') -or ([string]$_.path).EndsWith('.sql') }) }
        'required-sql' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { ([string]$_.path).StartsWith('required-sql/') }) }
        'runtime-env' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { $_.path -in @('.env', 'docker-compose.yml') }) }
        'packaging-manifest' { $matchingArtifacts = @($LegacyArtifacts | Where-Object { ([string]$_.path).StartsWith('resources/') }) }
        default { Fail "Unknown manifest v1 build module artifact hash: $ModuleName" }
    }
    if ($matchingArtifacts.Count -eq 0) {
        if ($ModuleName -in @('database-contract', 'required-sql')) {
            return $SchemaDigest
        }
        return ConvertTo-ReleaseStringSha256Digest -Value "module:$ModuleName:no-package-file"
    }
    $hashInput = ($matchingArtifacts | Sort-Object path | ForEach-Object {
        "$($_.path)=$(ConvertTo-ReleaseManifestSha256Digest -HashValue ([string]$_.sha256))"
    }) -join "`n"
    return ConvertTo-ReleaseStringSha256Digest -Value $hashInput
}

function New-ReleaseBuildModuleManifestEntries {
    param(
        [Parameter(Mandatory = $true)]
        [array]$Components,
        [Parameter(Mandatory = $true)]
        [array]$LegacyArtifacts,
        [Parameter(Mandatory = $true)]
        [array]$SourceRepos,
        [Parameter(Mandatory = $true)]
        [string]$SchemaDigest
    )
    $entries = @()
    $buildParameterHash = ConvertTo-ReleaseStringSha256Digest -Value (@{
        mode = $Mode
        component = $Component
        publishTargetName = $PublishTargetName
        includeOnlyOffice = [bool]$IncludeOnlyOffice
        includeShowroomBuildPackage = [bool]$publishWebsite
        skipDatabaseSync = [bool]$SkipDatabaseSync
        skipMinioSync = [bool]$SkipMinioSync
    } | ConvertTo-Json -Depth 4 -Compress)

    foreach ($componentName in @($Components)) {
        $entries += [ordered]@{
            moduleName = $componentName
            buildAction = 'rebuilt'
            sourceHash = Get-ReleaseModuleSourceHash -ModuleName $componentName -SourceRepos $SourceRepos
            dependencyHash = Get-ReleaseDependencyHash -ModuleName $componentName
            buildParameterHash = $buildParameterHash
            contractHash = $SchemaDigest
            artifactHash = Get-ReleaseComponentArtifactHash -ModuleName $componentName -LegacyArtifacts $LegacyArtifacts -SchemaDigest $SchemaDigest
        }
    }
    return @($entries)
}

function Get-ReleaseBuildModuleByName {
    param(
        [Parameter(Mandatory = $true)]
        [array]$BuildModules,
        [Parameter(Mandatory = $true)]
        [string]$ModuleName
    )
    $module = @($BuildModules | Where-Object { $_.moduleName -eq $ModuleName }) | Select-Object -First 1
    if ($null -ne $module) {
        return $module
    }
    return @($BuildModules | Where-Object { $_.moduleName -eq 'packaging-manifest' }) | Select-Object -First 1
}

function Resolve-ReleaseArtifactComponentName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )
    if ($RelativePath.StartsWith('website/')) { return 'website' }
    if ($RelativePath.StartsWith('required-sql/')) { return 'required-sql' }
    if ($RelativePath.StartsWith('manifest/') -or $RelativePath.EndsWith('.sql')) { return 'database-contract' }
    if ($RelativePath -in @('.env', 'docker-compose.yml')) { return 'runtime-env' }
    if ($RelativePath.StartsWith('resources/')) { return 'packaging-manifest' }
    if ($RelativePath.StartsWith('intruoyi-images_')) {
        if ($publishBackend) {
            return 'backend'
        }
        return 'admin-frontend'
    }
    return 'packaging-manifest'
}

function New-ReleaseArtifactManifestEntries {
    param(
        [Parameter(Mandatory = $true)]
        [array]$LegacyArtifacts,
        [Parameter(Mandatory = $true)]
        [array]$BuildModules
    )
    $entries = @()
    foreach ($artifact in @($LegacyArtifacts)) {
        $relativePath = [string]$artifact.path
        $componentName = Resolve-ReleaseArtifactComponentName -RelativePath $relativePath
        $module = Get-ReleaseBuildModuleByName -BuildModules $BuildModules -ModuleName $componentName
        $digest = ConvertTo-ReleaseManifestSha256Digest -HashValue ([string]$artifact.sha256)
        $artifactId = (($relativePath -replace '[^A-Za-z0-9_.-]', '-') -replace '-+', '-').Trim('-')
        if ([string]::IsNullOrWhiteSpace($artifactId)) {
            $artifactId = 'package-artifact'
        }
        $entries += [ordered]@{
            artifactId = $artifactId
            componentName = $componentName
            artifactType = 'release-package-file'
            path = $relativePath
            includedInPackage = $true
            artifactCacheUri = $null
            sha256 = $digest
            artifactHash = $digest
            size = [int64]$artifact.bytes
            digest = $digest
            buildCacheKey = "$componentName`:$($module.sourceHash)`:$($module.dependencyHash)`:$($module.buildParameterHash)`:$($module.contractHash)"
            sourceHash = [string]$module.sourceHash
            dependencyHash = [string]$module.dependencyHash
            buildParameterHash = [string]$module.buildParameterHash
            contractHash = [string]$module.contractHash
            dependencyClosureHash = [string]$module.dependencyHash
            buildToolchainHash = ConvertTo-ReleaseStringSha256Digest -Value "toolchain:$componentName"
        }
    }
    return @($entries)
}

function Write-ReleaseResourceReferenceManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    $resourcesDir = Join-Path $releaseDir 'resources'
    New-Item -ItemType Directory -Force -Path $resourcesDir | Out-Null
    $dccObjectInventoryPath = Join-Path $releaseDir 'manifest\dcc-object-inventory.json'
    $resourceReference = [ordered]@{
        schemaVersion = '1.0'
        releaseTag = $PackageTag
        generatedAt = (Get-Date).ToUniversalTime().ToString('o')
        resourcePayloadMode = 'reference-check-only'
        dccObjectInventory = if (Test-Path -LiteralPath $dccObjectInventoryPath -PathType Leaf) {
            [ordered]@{
                path = 'manifest/dcc-object-inventory.json'
                sha256 = ConvertTo-ReleaseFileSha256Digest -Path $dccObjectInventoryPath
            }
        } else {
            $null
        }
    } | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText((Join-Path $resourcesDir 'resource-reference-manifest.json'), $resourceReference, [System.Text.UTF8Encoding]::new($false))
}

function Write-ReleaseManifestV1 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag,
        [Parameter(Mandatory = $true)]
        [array]$LegacyArtifacts
    )

    if ($publishBackend) {
        $requiredSqlEntries = New-ReleaseRequiredSqlManifestEntries
        $schemaDigest = Get-ReleaseSchemaDigest -RequiredSqlEntries $requiredSqlEntries
        $schemaVersion = 'schema-digest-' + $schemaDigest.Substring('sha256:'.Length, 16)
        $migrationPlan = New-ReleaseMigrationPlanEntries -RequiredSqlEntries $requiredSqlEntries
    } else {
        $requiredSqlEntries = @()
        $schemaDigest = ConvertTo-ReleaseStringSha256Digest -Value 'schema:not-included'
        $schemaVersion = 'not-included'
        $migrationPlan = @()
    }
    $components = Get-ReleaseComponentManifestNames
    $sourceRepos = New-ReleaseSourceRepoManifestEntries
    $buildModules = New-ReleaseBuildModuleManifestEntries -Components $components -LegacyArtifacts $LegacyArtifacts -SourceRepos $sourceRepos -SchemaDigest $schemaDigest
    $artifacts = New-ReleaseArtifactManifestEntries -LegacyArtifacts $LegacyArtifacts -BuildModules $buildModules
    $packageType = if ($SkipDatabaseSync -and $SkipMinioSync) { 'full-release' } else { 'data-release' }
    $publishScopeValue = if ($SkipDatabaseSync -and $SkipMinioSync) { 'code-only' } else { 'with-data' }

    $effectiveOperatorName = if ([string]::IsNullOrWhiteSpace($OperatorName)) { 'local-operator' } else { $OperatorName.Trim() }

    $targetEnvironmentCodes = @('test', 'backup')
    if ($Mode -eq 'build-release' -or $Environment -eq 'prod') {
        $targetEnvironmentCodes += 'prod'
    }
    $targetEnvironmentCodes = @($targetEnvironmentCodes | Select-Object -Unique)

    $manifestV1 = [ordered]@{
        manifestVersion = '1.0'
        packageId = $packageDirectoryName
        releaseTag = $PackageTag
        packageType = $packageType
        createdAt = (Get-Date).ToUniversalTime().ToString('o')
        createdBy = $effectiveOperatorName
        sourceRepos = $sourceRepos
        changeSet = New-ReleaseChangeSetManifest -PackageTag $PackageTag
        publishScope = $publishScopeValue
        components = $components
        artifacts = $artifacts
        database = [ordered]@{
            schemaMigrations = $migrationPlan
            requiredDataSets = $requiredSqlEntries
        }
        schemaVersion = $schemaVersion
        schemaDigest = $schemaDigest
        migrationPlan = $migrationPlan
        requiredSql = $requiredSqlEntries
        buildModules = $buildModules
        compatibilityMatrix = @(
            [ordered]@{
                frontendVersion = if ($publishFrontend) { ((@($sourceRepos | Where-Object { $_.pathRole -eq 'admin-frontend' }) | Select-Object -First 1).commit) } else { 'not-included' }
                backendVersion = if ($publishBackend) { ((@($sourceRepos | Where-Object { $_.pathRole -eq 'backend' }) | Select-Object -First 1).commit) } else { 'not-included' }
                websiteVersion = if ($publishWebsite) { ((@($sourceRepos | Where-Object { $_.pathRole -eq 'website' }) | Select-Object -First 1).commit) } else { 'not-included' }
                schemaVersion = $schemaVersion
                allowed = $true
                evidenceOperationId = "manifest-$packageDirectoryName"
            }
        )
        operationEvidencePolicy = [ordered]@{
            requiredOperationTypes = @('manifest-validation', 'schema-preflight', 'artifact-hash-check', 'health-check')
            failOnMissingOperationEvidence = $true
            failOnIntermediateFailure = $true
        }
        resources = [ordered]@{
            resourcePayloadMode = 'reference-check-only'
            resourceReferenceManifest = 'resources/resource-reference-manifest.json'
            resourceSnapshotId = $null
            resourceDeltaId = $null
            resourceDeltaPrepared = $false
            resourceDeltaProofPath = $null
        }
        targetRequirements = [ordered]@{
            environmentCodes = $targetEnvironmentCodes
            serverConfigSchemaVersion = '1.0'
            storageProfileIds = @('minio-yudao-default')
            dockerProfileId = 'intruoyi-docker-compose'
            requiresDatabaseMigrationPrecheck = [bool]$publishBackend
            requiresRequiredDataPrecheck = [bool]$publishBackend
            requiresResourceDeltaProof = $false
        }
        buildContract = [ordered]@{
            mode = 'report-only'
            intakeReportPath = 'intake/intake-result.json'
            manifestValidationResultPath = 'manifest-validation-result.json'
            changesBuildExitCode = $false
            writesDatabase = $false
            syncsResources = $false
        }
        deployContract = [ordered]@{
            mode = 'report-only'
            deployPrecheckResultPath = 'deploy-precheck-result.json'
            changesDeployExitCode = $false
            targetConfigSource = 'server-side-runtime-control-config'
            allowsRemoteMutation = $false
            allowsRemoteReadOnlyProbe = 'authorized-only'
        }
        precheckPlan = [ordered]@{
            checks = @('manifest', 'artifact-hash', 'schema-preflight', 'required-sql-preconditions')
        }
        verifyPlan = [ordered]@{
            checks = @('manifest', 'runtime-health', 'operation-evidence')
        }
        rollbackPlan = [ordered]@{
            mode = 'manual'
            requiresCompatibilityEvidence = $true
            restoresBusinessData = $false
        }
        forbiddenFieldsCheck = [ordered]@{
            status = 'pending-validation'
            hardcodedIpMatches = @()
            secretPatternMatches = @()
            packageExternalPathReferences = @()
        }
        manifestChecksum = 'sha256:0000000000000000000000000000000000000000000000000000000000000000'
    }
    $manifestWithoutChecksum = $manifestV1 | ConvertTo-Json -Depth 20 -Compress
    $manifestV1.manifestChecksum = ConvertTo-ReleaseStringSha256Digest -Value $manifestWithoutChecksum
    $manifestJson = $manifestV1 | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText((Join-Path $releaseDir 'manifest.json'), $manifestJson, [System.Text.UTF8Encoding]::new($false))
}

function Write-ReleaseManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    Write-ReleaseResourceReferenceManifest -PackageTag $PackageTag
    $gitCommit = (& git -C $backendRepo rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) {
        $gitCommit = ''
    }
    $files = @()
    foreach ($path in Get-ChildItem -LiteralPath $releaseDir -File -Recurse) {
        if ($path.Name -eq 'release-manifest.json') {
            continue
        }
        $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $path.FullName
        $files += [ordered]@{
            path = $path.FullName.Substring($releaseDir.Length).TrimStart('\', '/').Replace('\', '/')
            sha256 = $hash.Hash.ToLowerInvariant()
            bytes = $path.Length
        }
    }
    $manifest = [ordered]@{
        releaseTag = $PackageTag
        packageDirectoryName = $packageDirectoryName
        builtAt = (Get-Date).ToUniversalTime().ToString('o')
        gitCommit = ([string]$gitCommit).Trim()
        publishScope = if ($SkipDatabaseSync -and $SkipMinioSync) { 'code-only' } else { 'with-data' }
        component = $Component
        includeShowroomBuildPackage = [bool]$publishWebsite
        onlyOfficeIncluded = [bool]$IncludeOnlyOffice
        artifacts = $files
    }
    if ($publishBackend -and $null -ne $backendRuntimeBaseConfig) {
        $backendRuntimeBaseManifest = [ordered]@{
            backendRuntimeBaseMode = $backendRuntimeBaseConfig.Mode
            backendRuntimeBaseImage = $backendRuntimeBaseConfig.Image
            backendRuntimeBaseDigest = $backendRuntimeBaseConfig.Digest
            backendRuntimeBaseVersion = $backendRuntimeBaseConfig.Version
            backendRuntimeBaseTarSha256 = $backendRuntimeBaseConfig.TarSha256
        }
        foreach ($entry in $backendRuntimeBaseManifest.GetEnumerator()) {
            $manifest[$entry.Key] = $entry.Value
        }
    }
    $manifest = $manifest | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText((Join-Path $releaseDir 'release-manifest.json'), $manifest, [System.Text.UTF8Encoding]::new($false))
    $manifestV1Artifacts = @($files | Where-Object { ([string]$_.path) -ne 'manifest.json' })
    Write-ReleaseManifestV1 -PackageTag $PackageTag -LegacyArtifacts $manifestV1Artifacts
}

if ($ReleaseTag.Contains('..') -or $ReleaseTag.Contains('/') -or $ReleaseTag.Contains('\')) {
    Fail "Invalid ReleaseTag: $ReleaseTag"
}
if ([string]::IsNullOrWhiteSpace($ReleaseTag) -and [string]::IsNullOrWhiteSpace($Tag)) {
    $Tag = Get-Date -Format 'yyyyMMdd_HHmmss'
    $ReleaseTag = $Tag
} elseif ([string]::IsNullOrWhiteSpace($ReleaseTag)) {
    Assert-ReleasePackageDirectoryNameSafe -DirectoryName $Tag
    $ReleaseTag = $Tag
} else {
    $expectedPackageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $ReleaseTag
    if ([string]::IsNullOrWhiteSpace($Tag)) {
        $Tag = $expectedPackageDirectoryName
    } else {
        Assert-ReleasePackageDirectoryNameSafe -DirectoryName $Tag
        if ($Tag -ne $expectedPackageDirectoryName) {
            Fail "Tag must match encoded ReleaseTag directory name: expected $expectedPackageDirectoryName, got $Tag"
        }
    }
}
Assert-ReleasePackageDirectoryNameSafe -DirectoryName $Tag
$packageDirectoryName = $Tag
$componentExplicit = $PSBoundParameters.ContainsKey('Component')

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$maintenanceReleaseScriptRoot = Join-Path $scriptDir '..\release'
$defaultBackendRepo = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
if ([string]::IsNullOrWhiteSpace($BackendRepoRoot)) {
    $backendRepo = $defaultBackendRepo
} else {
    $backendRepo = (Resolve-Path -LiteralPath $BackendRepoRoot).Path
}
$workspaceRoot = (Resolve-Path (Join-Path $backendRepo '..')).Path
$frontendDir = if ([string]::IsNullOrWhiteSpace($FrontendRepoRoot)) {
    Join-Path $workspaceRoot 'yudao-ui-admin-vue3'
} else {
    (Resolve-Path -LiteralPath $FrontendRepoRoot).Path
}
if (-not (Test-Path -LiteralPath $frontendDir)) {
    $worktreePortMapPath = Join-Path $scriptDir 'worktree-port-map.ps1'
    if (Test-Path -LiteralPath $worktreePortMapPath) {
        . $worktreePortMapPath
        try {
            $worktreePortContext = Get-IntRuoyiWorktreePortContext -CurrentBackendRepoRoot $backendRepo
            if (-not [string]::IsNullOrWhiteSpace($worktreePortContext.WorkspaceRoot)) {
                $workspaceRoot = $worktreePortContext.WorkspaceRoot
            }
            if (-not [string]::IsNullOrWhiteSpace($worktreePortContext.FrontendPath)) {
                $frontendDir = $worktreePortContext.FrontendPath
            }
        } catch {
            # Keep the legacy sibling lookup so the later explicit frontend existence check
            # still fails with the original actionable message if worktree resolution is unavailable.
        }
    }
}
$defaultWebsiteRepo = 'D:\ProjectPackage\Website'
if ([string]::IsNullOrWhiteSpace($WebsiteRepo)) {
    $WebsiteRepo = $defaultWebsiteRepo
}
$websiteRepo = (Resolve-Path $WebsiteRepo).Path
$publishBackend = $Component -in @('full', 'intruoyi', 'backend')
$publishFrontend = $Component -in @('full', 'intruoyi', 'frontend')
$publishWebsite = $Component -in @('full', 'website')
$backendJar = Join-Path $backendRepo 'yudao-server\target\yudao-server-exec.jar'
$backendDockerfile = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\Dockerfile.backend'
$frontendDockerfile = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\Dockerfile.frontend'
$composeTemplate = Join-Path $scriptDir 'int-ruoyi-test\docker-compose.yml'
$websiteNginxTemplate = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\website.nginx.conf'
$onlyOfficeImage = 'onlyoffice/documentserver:latest'
$resolvedLocalCacheRoot = Resolve-LocalCacheRoot $LocalCacheRoot
$buildReleaseRuntimeRestartGuardFile = Join-Path $resolvedLocalCacheRoot 'runtime\local-runtime-restart.guard'
Enter-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile
$localTempRoot = Join-Path $resolvedLocalCacheRoot 'publish-int-ruoyi'
$releaseDir = Join-Path $localTempRoot $packageDirectoryName
$dockerBuildContextRoot = Join-Path $releaseDir 'docker-build-context'
$imageTar = Join-Path $releaseDir "intruoyi-images_$packageDirectoryName.tar"
$dbDump = Join-Path $releaseDir 'ruoyi-vue-pro-current.sql'
$resetDbSqlLocal = Join-Path $releaseDir 'reset-db.sql'
$postImportSqlLocal = Join-Path $releaseDir 'post-import.sql'
function Get-ReleaseDatabaseSqlSortKey {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName
    )

    switch ($FileName) {
        '20260611_mes_edhr_work_task_flow.sql' { return '20260611_000_mes_edhr_work_task_flow.sql' }
        '20260611_mes_edhr_multi_signature_approval.sql' { return '20260611_010_mes_edhr_multi_signature_approval.sql' }
        '20260611_mes_edhr_rejection_revision_flow.sql' { return '20260611_020_mes_edhr_rejection_revision_flow.sql' }
        '20260611_mes_smart_scheduling_tabs.sql' { return '20260611_100_mes_smart_scheduling_tabs.sql' }
        '20260611_mes_scheduler_workbench_smart_scheduling_tab.sql' { return '20260611_110_mes_scheduler_workbench_smart_scheduling_tab.sql' }
        '20260611_mes_smart_scheduling_extra_tabs.sql' { return '20260611_120_mes_smart_scheduling_extra_tabs.sql' }
        default { return $FileName }
    }
}

function Get-ReleaseDatabaseSqlRoots {
    return @(
        [ordered]@{
            RelativePath = 'sql/mysql'
            Root = Join-Path $backendRepo 'sql\mysql'
            IncludeFiles = @()
            Environments = @('test', 'prod', 'backup')
        },
        [ordered]@{
            RelativePath = 'sql/showroom'
            Root = Join-Path $backendRepo 'sql\showroom'
            IncludeFiles = @(
                '20260605_showroom_product_revision_attachment_schema.sql',
                '20260606_showroom_hall_product_canvas_layout.sql',
                '20260613_showroom_award_and_hall_item_schema.sql',
                '20260615_showroom_hall_canvas_background.sql'
            )
            Environments = @('test', 'prod', 'backup')
        }
    )
}

function Get-ReleaseDatabaseSqlScripts {
    $entries = @()
    $seenPackageFileNames = @{}
    foreach ($root in @(Get-ReleaseDatabaseSqlRoots)) {
        $sqlRoot = [string]$root.Root
        $relativeRoot = [string]$root.RelativePath
        if (-not (Test-Path -LiteralPath $sqlRoot -PathType Container)) {
            Fail "Release database SQL directory missing: $sqlRoot"
        }

        $files = @()
        if (@($root.IncludeFiles).Count -gt 0) {
            foreach ($fileName in @($root.IncludeFiles)) {
                $filePath = Join-Path $sqlRoot ([string]$fileName)
                if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
                    Fail "Release database SQL file missing: $filePath"
                }
                $files += Get-Item -LiteralPath $filePath
            }
        } else {
            $files = @(
                Get-ChildItem -LiteralPath $sqlRoot -Filter '*.sql' -File |
                    Where-Object { $_.Name -match '^20\d{6}_.+\.sql$' }
            )
        }

        foreach ($file in $files) {
            if ($seenPackageFileNames.ContainsKey($file.Name)) {
                Fail "Duplicate release database SQL file name: $($file.Name) in $($seenPackageFileNames[$file.Name]) and $($file.FullName)"
            }
            $seenPackageFileNames[$file.Name] = $file.FullName
            $metadata = Read-ReleaseMigrationMetadata -SqlPath $file.FullName
            $entries += @{
                Path = ($relativeRoot + '/' + $file.Name)
                Environments = @($metadata.allowedEnvironments)
            }
        }
    }

    $entries = @(
        $entries |
            Sort-Object @{ Expression = { Get-ReleaseDatabaseSqlSortKey -FileName ([System.IO.Path]::GetFileName(([string]$_.Path).Replace('/', [System.IO.Path]::DirectorySeparatorChar))) } }, Path
    )
    if ($entries.Count -eq 0) {
        Fail "No release database SQL scripts found under release SQL roots"
    }
    return $entries
}

$requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts
if ($publishBackend -and $Mode -eq 'build-release') {
    Invoke-ReleaseMigrationPolicyGate
}
$requiredSqlLocalDir = Join-Path $releaseDir 'required-sql'
$opsRuntimeLocalDir = Join-Path $releaseDir 'ops-runtime'
$websiteRuntimeLocal = Join-Path $releaseDir 'website'
$websiteNginxLocal = Join-Path $websiteRuntimeLocal 'nginx.conf'
$remoteReleaseDir = "$RemoteReleaseRoot/$packageDirectoryName"
$remoteImageTar = "$remoteReleaseDir/intruoyi-images_$packageDirectoryName.tar"
$remoteDbDump = "$remoteReleaseDir/ruoyi-vue-pro-current.sql"
$remoteResetDbSql = "$remoteReleaseDir/reset-db.sql"
$remotePostImportSql = "$remoteReleaseDir/post-import.sql"
$remoteRequiredSqlDir = "$remoteReleaseDir/required-sql"
$remoteOpsRuntimeDir = '/opt/intruoyi/ops/backup-ops/linux-native'
$remoteCompose = "$RemoteAppDir/docker-compose.yml"
$remoteEnv = "$RemoteAppDir/.env"
$remoteWebsiteDir = "$RemoteAppDir/website"
$remoteWebsiteStagingDir = "$remoteReleaseDir/website"
$remoteWebsitePreviousDir = "$RemoteAppDir/website.previous"
$schedulerSmokeFrontendDirectory = '/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3'
$schedulerSmokeScriptName = 'e2e:mes:smart-scheduling-smoke'
$schedulerSmokeNodeImage = 'mcr.microsoft.com/playwright:v1.60.0-noble'
$schedulerSmokeRunnerLocalDir = Join-Path $releaseDir 'smoke'
$remoteSchedulerSmokeRoot = "$RemoteAppDir/smoke"
$remoteSchedulerSmokeFrontendDir = "$remoteSchedulerSmokeRoot/yudao-ui-admin-vue3"
$remoteSchedulerSmokeBinDir = "$remoteSchedulerSmokeRoot/bin"
$remoteSchedulerSmokeNpmWrapper = "$remoteSchedulerSmokeBinDir/npm"
$backendRuntimeBaseConfig = Resolve-BackendRuntimeBaseConfig
$smartReleaseReportOnlyEnabled = Resolve-SmartReleaseReportOnlyEnabled
if ($publishBackend -and $Mode -notin @('deploy-release', 'mark-tested')) {
    Assert-BackendJarAvailableForMavenClean -JarPath $backendJar
}

function Join-ShellQuotedPathList {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    return (($Paths | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique | ForEach-Object {
        "'$_'"
    }) -join ' ')
}

function ConvertTo-ShellSingleQuotedLiteral {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value,
        [string]$Purpose = 'shell literal'
    )

    if ($Value.Contains("'")) {
        Fail "$Purpose contains unsupported single quote: $Value"
    }
    return "'$Value'"
}

function Assert-RemoteRuntimeEnvImageTag {
    $remoteEnvLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnv -Purpose 'remote runtime env path'
    $expectedImageTagLine = "IMAGE_TAG=$packageDirectoryName"
    $expectedImageTagLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $expectedImageTagLine -Purpose 'remote runtime IMAGE_TAG'
    $command = @"
set -eu
test -f $remoteEnvLiteral
grep -Fx $expectedImageTagLiteral $remoteEnvLiteral
"@
    Invoke-SshCommand $command
    Info "Remote runtime .env IMAGE_TAG verified: $packageDirectoryName"
}

function Prepare-RemoteReleaseTree {
    $directories = @(
        $RemoteAppDir,
        $remoteReleaseDir
    )
    $cleanupTargets = @()
    if ($publishWebsite) {
        $directories += $remoteWebsiteStagingDir
        $cleanupTargets += $remoteWebsiteStagingDir
        $cleanupTargets += $remoteWebsitePreviousDir
    }
    if ($publishBackend) {
        $directories += $remoteRequiredSqlDir
        $cleanupTargets += $remoteRequiredSqlDir
    }
    $mkdirArgs = Join-ShellQuotedPathList -Paths $directories
    if ($cleanupTargets.Count -gt 0) {
        $cleanupArgs = Join-ShellQuotedPathList -Paths $cleanupTargets
        Invoke-SshCommand "rm -rf $cleanupArgs && mkdir -p $mkdirArgs"
    } else {
        Invoke-SshCommand "mkdir -p $mkdirArgs"
    }
}

function New-SchedulerSmokeNpmWrapperContent {
    $envNames = @(
        'MES_SMOKE_BASE_URL',
        'MES_SMOKE_EXCEL_FILE',
        'MES_SMOKE_ARTIFACT_DIR',
        'MES_SMOKE_NODE_IMAGE',
        'MES_SMOKE_CAPACITY_MODE',
        'MES_SMOKE_PRODUCT_CODE',
        'MES_SMOKE_ERP_UNIT_NUMBER',
        'MES_SMOKE_BATCH_NUMBER',
        'MES_SMOKE_DEFAULT_PASSWORD',
        'MES_SMOKE_ERP_CREATOR_TENANT',
        'MES_SMOKE_ERP_CREATOR_USERNAME',
        'MES_SMOKE_ERP_CREATOR_PASSWORD',
        'MES_SMOKE_PLANNER_TENANT',
        'MES_SMOKE_PLANNER_USERNAME',
        'MES_SMOKE_PLANNER_PASSWORD',
        'MES_SMOKE_SUPERVISOR_TENANT',
        'MES_SMOKE_SUPERVISOR_USERNAME',
        'MES_SMOKE_FEEDBACK_APPROVER_NAME',
        'MES_SMOKE_SUPERVISOR_PASSWORD',
        'MES_SMOKE_NON_APPROVER_TENANT',
        'MES_SMOKE_NON_APPROVER_USERNAME',
        'MES_SMOKE_NON_APPROVER_PASSWORD',
        'MES_SMOKE_HEADLESS',
        'MES_SMOKE_WORK_ORDER_CODE',
        'MES_SMOKE_WORK_ORDER_QUANTITY',
        'MES_SMOKE_ERP_SOURCE_BILL_NO',
        'MES_SMOKE_ERP_PLANNED_START_TIME',
        'MES_SMOKE_ERP_PLANNED_FINISH_TIME',
        'MES_SMOKE_PROMISE_DATE',
        'MES_SMOKE_SCHEDULE_START_TIME',
        'MES_SMOKE_PRESERVE_MANUAL_LOCKED_TASKS',
        'MES_SMOKE_RUN_ID',
        'MES_SMOKE_BACKEND_RUNNER_LOG'
    )
    $envArgs = ($envNames | ForEach-Object { "  -e $_ \" }) -join "`n"
    $content = @"
#!/usr/bin/env sh
set -eu
: "`${MES_SMOKE_NODE_IMAGE:?MES_SMOKE_NODE_IMAGE is required}"
NODE_IMAGE="`${MES_SMOKE_NODE_IMAGE}"
WORKDIR="`${PWD:-$schedulerSmokeFrontendDirectory}"
exec docker run --rm --network host \
  -v /opt/intruoyi/runtime:/opt/intruoyi/runtime \
  -w "`$WORKDIR" \
$envArgs
  "`$NODE_IMAGE" npm "`$@"
"@
    return $content
}

function New-SchedulerSmokeRunnerPackage {
    if (-not $publishBackend) {
        return
    }

    $smokeTestsSourceDir = Join-Path $frontendDir 'tests\e2e'
    $realFlowSource = Join-Path $smokeTestsSourceDir 'smart-scheduling-smoke-real-flow.e2e.js'
    $staticSpecSource = Join-Path $smokeTestsSourceDir 'smart-scheduling-smoke-real-flow-static.spec.js'
    if (-not (Test-Path -LiteralPath $realFlowSource -PathType Leaf)) {
        Fail "Smart scheduling smoke E2E script missing: $realFlowSource"
    }
    if (-not (Test-Path -LiteralPath $staticSpecSource -PathType Leaf)) {
        Fail "Smart scheduling smoke static script missing: $staticSpecSource"
    }

    if (Test-Path -LiteralPath $schedulerSmokeRunnerLocalDir) {
        Remove-Item -LiteralPath $schedulerSmokeRunnerLocalDir -Recurse -Force
    }
    $localFrontendDir = Join-Path $schedulerSmokeRunnerLocalDir 'yudao-ui-admin-vue3'
    $localTestsDir = Join-Path $localFrontendDir 'tests\e2e'
    $localInputDir = Join-Path $localFrontendDir 'input'
    $localOutputDir = Join-Path $localFrontendDir 'output\artifacts'
    $localBinDir = Join-Path $schedulerSmokeRunnerLocalDir 'bin'
    New-Item -ItemType Directory -Force -Path $localTestsDir, $localInputDir, $localOutputDir, $localBinDir | Out-Null

    $packageJson = @"
{
  "name": "intruoyi-scheduler-smoke-runner",
  "private": true,
  "scripts": {
    "e2e:mes:smart-scheduling-smoke:check": "node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js",
    "e2e:mes:smart-scheduling-smoke": "node tests/e2e/smart-scheduling-smoke-real-flow.e2e.js"
  },
  "devDependencies": {
    "playwright": "1.60.0",
    "xlsx": "0.18.5"
  }
}
"@
    Write-Utf8LfNoBomFile -Path (Join-Path $localFrontendDir 'package.json') -Content $packageJson
    Copy-Item -LiteralPath $realFlowSource -Destination (Join-Path $localTestsDir 'smart-scheduling-smoke-real-flow.e2e.js') -Force
    Copy-Item -LiteralPath $staticSpecSource -Destination (Join-Path $localTestsDir 'smart-scheduling-smoke-real-flow-static.spec.js') -Force
    Write-Utf8LfNoBomFile -Path (Join-Path $localBinDir 'npm') -Content (New-SchedulerSmokeNpmWrapperContent)
}

function Get-RemoteSchedulerSmokeNodeImageBootstrapCommand {
    return @"
set -eu
MES_SMOKE_NODE_IMAGE=`$(grep -E '^MES_SMOKE_NODE_IMAGE=' '$RemoteAppDir/.env' | sed 's/^MES_SMOKE_NODE_IMAGE=//')
if [ -z "`$MES_SMOKE_NODE_IMAGE" ]; then
  echo 'MES_SMOKE_NODE_IMAGE is missing in $RemoteAppDir/.env' >&2
  exit 1
fi
export MES_SMOKE_NODE_IMAGE
"@.Trim()
}

function Copy-SchedulerSmokeRunnerToServer {
    if (-not $publishBackend) {
        return
    }

    if (-not (Test-Path -LiteralPath (Join-Path $schedulerSmokeRunnerLocalDir 'yudao-ui-admin-vue3\package.json') -PathType Leaf)) {
        New-SchedulerSmokeRunnerPackage
    }
    Info "Copying scheduler smoke runner to the $PublishTargetName server"
    Invoke-SshCommand "mkdir -p '$RemoteAppDir' '$remoteSchedulerSmokeRoot' '$remoteSchedulerSmokeFrontendDir/input' '$remoteSchedulerSmokeFrontendDir/output/artifacts' '$remoteSchedulerSmokeBinDir'"
    Copy-ToServer -LocalPath $schedulerSmokeRunnerLocalDir -RemotePath $RemoteAppDir -Recursive
    Invoke-SshCommand "chmod +x '$remoteSchedulerSmokeNpmWrapper' && test -f '$remoteSchedulerSmokeFrontendDir/package.json' && test -f '$remoteSchedulerSmokeFrontendDir/tests/e2e/smart-scheduling-smoke-real-flow.e2e.js'"
    $remoteSmokeNodeImageBootstrap = Get-RemoteSchedulerSmokeNodeImageBootstrapCommand
    Invoke-SshCommand "$remoteSmokeNodeImageBootstrap
cd '$remoteSchedulerSmokeFrontendDir'
'$remoteSchedulerSmokeNpmWrapper' install --no-audit --no-fund"
}

function Assert-RemoteSchedulerSmokeRuntime {
    if (-not $publishBackend) {
        return
    }

    Info "Checking scheduler smoke runtime on the $PublishTargetName server"
    Invoke-SshCommand "docker exec intruoyi-backend sh -lc 'test `"`${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY}`" = `"$schedulerSmokeFrontendDirectory`" && test `"`${YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME}`" = `"$schedulerSmokeScriptName`" && test `"`${MES_SMOKE_NODE_IMAGE}`" = `"$schedulerSmokeNodeImage`" && test -d `"$schedulerSmokeFrontendDirectory`" && test -f `"$schedulerSmokeFrontendDirectory/package.json`" && test -x /usr/local/bin/npm && npm --version >/dev/null'"
    $remoteSmokeNodeImageBootstrap = Get-RemoteSchedulerSmokeNodeImageBootstrapCommand
    Invoke-SshCommand "$remoteSmokeNodeImageBootstrap
cd '$remoteSchedulerSmokeFrontendDir'
'$remoteSchedulerSmokeNpmWrapper' exec -- node --check tests/e2e/smart-scheduling-smoke-real-flow.e2e.js"
}

function Get-RequiredDatabaseSqlFileName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )
    return [System.IO.Path]::GetFileName($RelativePath)
}

function Get-RequiredDatabaseSqlEntriesForEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )

    $entries = @($requiredDatabaseSqlScripts | Where-Object {
        $entry = $_
        $allowedEnvironments = @($entry.Environments)
        $allowedEnvironments -contains $TargetEnvironment
    })
    if ($entries.Count -eq 0) {
        Fail "No required database SQL scripts are allowed for environment: $TargetEnvironment"
    }
    return $entries
}

function Get-ReleasePackageDatabaseSqlScripts {
    $manifestPath = Join-Path $releaseDir 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Fail "manifest.json missing in release package for required SQL: $manifestPath"
    }
    try {
        $manifest = [System.IO.File]::ReadAllText($manifestPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    } catch {
        Fail "manifest.json parse failed for required SQL: $($_.Exception.Message)"
    }
    $manifestRequiredSql = @()
    if ($null -ne $manifest.requiredSql) {
        $manifestRequiredSql = @($manifest.requiredSql)
    } elseif ($null -ne $manifest.database -and $null -ne $manifest.database.requiredDataSets) {
        $manifestRequiredSql = @($manifest.database.requiredDataSets)
    } elseif ($null -ne $manifest.database -and $null -ne $manifest.database.schemaMigrations) {
        $manifestRequiredSql = @($manifest.database.schemaMigrations)
    }
    $entries = @($manifestRequiredSql | Where-Object {
        $artifactPath = [string]$_.file
        $artifactPath.StartsWith('required-sql/') -and $artifactPath.EndsWith('.sql')
    } | Sort-Object @{ Expression = { Get-ReleaseDatabaseSqlSortKey -FileName ([System.IO.Path]::GetFileName([string]$_.sourcePath)) } }, sourcePath | ForEach-Object {
        $sourcePath = [string]$_.sourcePath
        if ([string]::IsNullOrWhiteSpace($sourcePath)) {
            Fail "sourcePath missing in release package required SQL entry: $([string]$_.migrationId)"
        }
        $allowedEnvironments = @($_.allowedEnvironments)
        if ($allowedEnvironments.Count -eq 0) {
            Fail "required SQL entry allowedEnvironments is empty: $sourcePath"
        }
        @{
            Path = $sourcePath
            Environments = @($allowedEnvironments)
        }
    })
    if ($entries.Count -eq 0) {
        Fail "Release package contains no required SQL entries: $manifestPath"
    }
    return $entries
}

function Read-ReleasePreflightPlan {
    $preflightPlanPath = Join-Path $releaseDir 'preflight-plan.json'
    if (-not (Test-Path -LiteralPath $preflightPlanPath -PathType Leaf)) {
        Fail "preflight-plan.json missing in release package; run preflight-release before deploy-release: $preflightPlanPath"
    }
    try {
        $plan = [System.IO.File]::ReadAllText($preflightPlanPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    } catch {
        Fail "preflight-plan.json parse failed: $($_.Exception.Message)"
    }
    if ([string]$plan.status -ne 'passed') {
        Fail "preflight-plan.json status must be passed before deploy-release: $($plan.status)"
    }
    foreach ($item in @($plan.items)) {
        $action = [string]$item.action
        if ($action.StartsWith('BLOCKED_')) {
            Fail "preflight-plan.json contains blocked migration: $($item.migrationId) -> $action"
        }
        if ($action -notin @('APPLY', 'SKIP_ALREADY_APPLIED', 'SKIP_ENV_NOT_ALLOWED')) {
            Fail "preflight-plan.json contains unsupported migration action: $($item.migrationId) -> $action"
        }
    }
    return $plan
}

function Write-ReleasePreflightPlan {
    $manifestPath = Join-Path $releaseDir 'manifest.json'
    $targetStatePath = Join-Path $releaseDir "preflight-target-state-$Environment.json"
    $preflightPlanPath = Join-Path $releaseDir 'preflight-plan.json'
    $preflightScriptPath = Join-Path $backendRepo 'script\release\release_preflight_plan.py'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Fail "manifest.json missing in release package for preflight: $manifestPath"
    }
    if (-not (Test-Path -LiteralPath $preflightScriptPath -PathType Leaf)) {
        Fail "release preflight planner missing: $preflightScriptPath"
    }

    Info "Generating target-bound release preflight plan for $Environment"
    $stateSql = @"
SELECT COALESCE(
    JSON_OBJECTAGG(
        migration_id,
        JSON_OBJECT(
            'sha256', REPLACE(sha256, 'sha256:', ''),
            'status', CASE WHEN status IN ('APPLIED', 'SKIPPED_ALREADY_APPLIED') THEN 'APPLIED' ELSE status END
        )
    ),
    JSON_OBJECT()
)
FROM infra_release_migration
WHERE target_environment = '$Environment'
  AND deleted = b'0'
  AND status IN ('APPLIED', 'SKIPPED_ALREADY_APPLIED');
"@
    $capture = Invoke-SshCapture "cat <<'SQL' | docker exec -i -e MYSQL_PWD=$mySqlRootPassword intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
$stateSql
SQL"
    $targetStateJson = ([string]$capture.Output).Trim()
    if ([string]::IsNullOrWhiteSpace($targetStateJson)) {
        Fail 'Target release migration state query returned blank output'
    }
    [System.IO.File]::WriteAllText($targetStatePath, $targetStateJson, [System.Text.UTF8Encoding]::new($false))
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8',
        $preflightScriptPath,
        '--manifest', $manifestPath,
        '--target-state', $targetStatePath,
        '--target-environment', $Environment,
        '--output', $preflightPlanPath
    )
}

function Assert-ProdDryRunEvidence {
    if ($Environment -ne 'prod' -or $Mode -ne 'deploy-release') {
        return
    }
    if ([string]::IsNullOrWhiteSpace($ProdDryRunEvidencePath)) {
        Fail 'Production deploy-release requires -ProdDryRunEvidencePath from a passed preflight-release dry-run.'
    }
    if (-not (Test-Path -LiteralPath $ProdDryRunEvidencePath -PathType Leaf)) {
        Fail "Production dry-run evidence file missing: $ProdDryRunEvidencePath"
    }
    try {
        $evidence = [System.IO.File]::ReadAllText($ProdDryRunEvidencePath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    } catch {
        Fail "Production dry-run evidence JSON parse failed: $($_.Exception.Message)"
    }
    if ([string]$evidence.status -ne 'passed') {
        Fail "Production dry-run evidence status must be passed: $($evidence.status)"
    }
    if ([string]$evidence.targetEnvironment -ne 'prod') {
        Fail "Production dry-run evidence targetEnvironment must be prod: $($evidence.targetEnvironment)"
    }
    if ([string]$evidence.releaseTag -ne $ReleaseTag) {
        Fail "Production dry-run evidence releaseTag does not match deploy-release: $($evidence.releaseTag)"
    }
    if ([string]$evidence.mode -ne 'preflight-release') {
        Fail "Production dry-run evidence mode must be preflight-release: $($evidence.mode)"
    }
    if ($null -eq $evidence.writeActions -or @($evidence.writeActions).Count -gt 0) {
        Fail 'Production dry-run evidence must be read-only and include empty writeActions.'
    }
}

function Get-ReleasePreflightApplyItems {
    param(
        [Parameter(Mandatory = $true)]
        $PreflightPlan
    )
    return @($PreflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })
}

function Invoke-ReleaseMigrationStateUpdate {
    param(
        [Parameter(Mandatory = $true)]
        $Item,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )
    $migrationId = [string]$Item.migrationId
    $fileName = Get-RequiredDatabaseSqlFileName -RelativePath ([string]$Item.file)
    $sha256 = [string]$Item.sha256
    $escapedErrorMessage = $ErrorMessage.Replace("'", "''")
    $stateSql = @"
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ('$ReleaseTag', '$migrationId', '$fileName', '$sha256', '$Environment', '$Status', NOW(), CASE WHEN '$Status' IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED') THEN NOW() ELSE NULL END, NULLIF('$escapedErrorMessage', ''), '$ReleaseTag', 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
"@
    Invoke-SshCommand "cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 ruoyi-vue-pro
$stateSql
SQL"
}

function Ensure-ReleaseMigrationStateSchema {
    $stateSchemaFileName = '20260613_infra_release_migration_state.sql'
    $packageSqlPath = Join-Path $requiredSqlLocalDir $stateSchemaFileName
    if (-not (Test-Path -LiteralPath $packageSqlPath -PathType Leaf)) {
        Fail "Release state schema SQL missing from release package: $packageSqlPath"
    }

    $probeSql = @"
SELECT COUNT(*)
FROM information_schema.tables
WHERE table_schema = 'ruoyi-vue-pro'
  AND table_name IN ('infra_release_migration', 'infra_release_operation_lock');
"@
    $probeResult = Invoke-SshCapture "cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 --batch --skip-column-names information_schema
$probeSql
SQL"
    $existingCount = ([string]$probeResult.Output).Trim()
    if ($existingCount -eq '2') {
        return
    }

    Info 'Bootstrapping release migration state tables on target server'
    $remoteStateSchemaPath = "$remoteRequiredSqlDir/$stateSchemaFileName"
    if (-not (Test-Path -LiteralPath $packageSqlPath -PathType Leaf)) {
        Fail "Release state schema SQL missing locally: $packageSqlPath"
    }
    if (-not [string]::IsNullOrWhiteSpace($remoteStateSchemaPath)) {
        Invoke-SshCommand "cat '$remoteStateSchemaPath' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 ruoyi-vue-pro"
    }
}

function Invoke-ReleaseOperationLockAcquire {
    $operationId = "$Environment-$ReleaseTag"
    $lockSql = @"
INSERT INTO infra_release_operation_lock (target_environment, operation_id, release_tag, status, started_at, finished_at, error_message, creator, create_time, updater, update_time, deleted, tenant_id)
SELECT '$Environment', '$operationId', '$ReleaseTag', 'RUNNING', NOW(), NULL, NULL, 'release-system', NOW(), 'release-system', NOW(), b'0', 0
WHERE NOT EXISTS (
  SELECT 1 FROM infra_release_operation_lock WHERE target_environment = '$Environment' AND status = 'RUNNING'
)
ON DUPLICATE KEY UPDATE
  operation_id = IF(status = 'RUNNING', operation_id, VALUES(operation_id)),
  release_tag = IF(status = 'RUNNING', release_tag, VALUES(release_tag)),
  started_at = IF(status = 'RUNNING', started_at, VALUES(started_at)),
  finished_at = IF(status = 'RUNNING', finished_at, NULL),
  error_message = IF(status = 'RUNNING', error_message, NULL),
  status = IF(status = 'RUNNING', status, 'RUNNING'),
  updater = 'release-system',
  update_time = NOW(),
  deleted = b'0';
SELECT CASE WHEN operation_id = '$operationId' AND status = 'RUNNING' THEN 'LOCK_ACQUIRED' ELSE CONCAT('LOCK_HELD:', operation_id, ':', release_tag) END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    Invoke-SshCommand "cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro | grep '^LOCK_ACQUIRED$'
$lockSql
SQL"
    $script:ReleaseOperationLockHeld = $true
    $script:ReleaseOperationLockReleasing = $false
}

function Invoke-ReleaseOperationLockRelease {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )
    $operationId = "$Environment-$ReleaseTag"
    $escapedErrorMessage = $ErrorMessage.Replace("'", "''")
    $lockSql = @"
UPDATE infra_release_operation_lock
SET status = '$Status',
    finished_at = NOW(),
    error_message = NULLIF('$escapedErrorMessage', ''),
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = '$Environment'
  AND operation_id = '$operationId'
  AND status = 'RUNNING';
SELECT CASE WHEN status = '$Status' THEN 'LOCK_RELEASED' ELSE CONCAT('LOCK_RELEASE_FAILED:', operation_id, ':', status) END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    Invoke-SshCommand "cat <<'SQL' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro | grep '^LOCK_RELEASED$'
$lockSql
SQL"
    $script:ReleaseOperationLockHeld = $false
    $script:ReleaseOperationLockReleasing = $false
}

function Copy-RequiredDatabaseSqlScripts {
    if (Test-Path -LiteralPath $requiredSqlLocalDir) {
        Remove-Item -LiteralPath $requiredSqlLocalDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $requiredSqlLocalDir | Out-Null

    foreach ($entry in $requiredDatabaseSqlScripts) {
        $relativePath = [string]$entry.Path
        $sourceRelativePath = $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $sourcePath = Join-Path $backendRepo $sourceRelativePath
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            Fail "Required database SQL script missing: $sourcePath"
        }

        $targetPath = Join-Path $requiredSqlLocalDir (Get-RequiredDatabaseSqlFileName -RelativePath $relativePath)
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    }
}

function Assert-RequiredDatabaseSqlScriptsInRelease {
    $requiredSqlEntries = Get-RequiredDatabaseSqlEntriesForEnvironment -TargetEnvironment $Environment
    foreach ($entry in $requiredSqlEntries) {
        $relativePath = [string]$entry.Path
        $packageSqlPath = Join-Path $requiredSqlLocalDir (Get-RequiredDatabaseSqlFileName -RelativePath $relativePath)
        if (-not (Test-Path -LiteralPath $packageSqlPath)) {
            Fail "Release package required SQL missing: $packageSqlPath"
        }
    }
}

function Copy-RequiredDatabaseSqlScriptsToServer {
    Assert-RequiredDatabaseSqlScriptsInRelease
    $requiredSqlEntries = Get-RequiredDatabaseSqlEntriesForEnvironment -TargetEnvironment $Environment
    foreach ($entry in $requiredSqlEntries) {
        $relativePath = [string]$entry.Path
        $fileName = Get-RequiredDatabaseSqlFileName -RelativePath $relativePath
        $packageSqlPath = Join-Path $requiredSqlLocalDir $fileName
        Copy-ToServer -LocalPath $packageSqlPath -RemotePath "$remoteRequiredSqlDir/$fileName"
    }
}

function Copy-ReleaseOpsRuntimePackage {
    Info 'Syncing runtime-control ops scripts to the target server'
    if (Test-Path -LiteralPath $opsRuntimeLocalDir) {
        Remove-Item -LiteralPath $opsRuntimeLocalDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $opsRuntimeLocalDir | Out-Null

    foreach ($directoryName in @('linux', 'scripts', 'actions')) {
        $sourceDirectory = Join-Path $backendRepo "script\backup-ops\$directoryName"
        if (-not (Test-Path -LiteralPath $sourceDirectory -PathType Container)) {
            Fail "Runtime-control ops source directory missing: $sourceDirectory"
        }
        Copy-Item -LiteralPath $sourceDirectory -Destination (Join-Path $opsRuntimeLocalDir $directoryName) -Recurse -Force
    }

    $sourceConfigDirectory = Join-Path $backendRepo 'script\backup-ops\config'
    if (-not (Test-Path -LiteralPath $sourceConfigDirectory -PathType Container)) {
        Fail "Runtime-control ops config directory missing: $sourceConfigDirectory"
    }
    $targetConfigDirectory = Join-Path $opsRuntimeLocalDir 'config'
    New-Item -ItemType Directory -Force -Path $targetConfigDirectory | Out-Null
    Get-ChildItem -LiteralPath $sourceConfigDirectory -File |
        Where-Object { $_.Name -ne 'backup-ops.secrets.json' } |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $targetConfigDirectory $_.Name) -Force
        }
    if (Test-Path -LiteralPath (Join-Path $targetConfigDirectory 'backup-ops.secrets.json')) {
        Fail 'Runtime-control ops package must not include backup-ops.secrets.json'
    }

    $remoteRootDiskScript = Join-Path $backendRepo 'script\deploy\manage-int-ruoyi-remote-root-disk.ps1'
    if (-not (Test-Path -LiteralPath $remoteRootDiskScript -PathType Leaf)) {
        Fail "Runtime-control remote root disk script missing: $remoteRootDiskScript"
    }
    $targetDeployDirectory = Join-Path $opsRuntimeLocalDir 'script\deploy'
    New-Item -ItemType Directory -Force -Path $targetDeployDirectory | Out-Null
    Copy-Item -LiteralPath $remoteRootDiskScript -Destination (Join-Path $targetDeployDirectory 'manage-int-ruoyi-remote-root-disk.ps1') -Force

    Invoke-SshCommand "mkdir -p '$remoteOpsRuntimeDir' '$remoteOpsRuntimeDir/config' '$remoteOpsRuntimeDir/script/deploy' && rm -rf '$remoteOpsRuntimeDir/linux' '$remoteOpsRuntimeDir/scripts' '$remoteOpsRuntimeDir/actions' '$remoteOpsRuntimeDir/script/deploy/manage-int-ruoyi-remote-root-disk.ps1' && mkdir -p '$remoteOpsRuntimeDir/linux' '$remoteOpsRuntimeDir/scripts' '$remoteOpsRuntimeDir/actions'"
    Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'linux') -RemotePath $remoteOpsRuntimeDir -Recursive
    Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'scripts') -RemotePath $remoteOpsRuntimeDir -Recursive
    Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'actions') -RemotePath $remoteOpsRuntimeDir -Recursive
    Copy-ToServer -LocalPath (Join-Path $opsRuntimeLocalDir 'config') -RemotePath $remoteOpsRuntimeDir -Recursive
    Copy-ToServer -LocalPath (Join-Path $targetDeployDirectory 'manage-int-ruoyi-remote-root-disk.ps1') -RemotePath "$remoteOpsRuntimeDir/script/deploy/manage-int-ruoyi-remote-root-disk.ps1"
    Invoke-SshCommand "test -f '$remoteOpsRuntimeDir/linux/backup-ops-linux.sh' && test -f '$remoteOpsRuntimeDir/script/deploy/manage-int-ruoyi-remote-root-disk.ps1'"
}

function Write-TargetBoundPostImportSql {
    $edhrProtectedStorageSql = New-EdhrProtectedStoragePostImportSql
    $showroomFileStorageSql = New-ShowroomFileStoragePostImportSql -TargetServerHost $ServerHost -MinioAccessKey $remoteMinioAccessKey -MinioAccessSecret $remoteMinioSecretKey
$postImportSql = @"
$edhrProtectedStorageSql

$showroomFileStorageSql
"@
    [System.IO.File]::WriteAllText($postImportSqlLocal, $postImportSql, [System.Text.UTF8Encoding]::new($false))
}

function Get-RequiredDatabaseSqlSessionPreamble {
    param(
        [Parameter(Mandatory = $true)]
        $Item,

        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )
    $migrationId = [string]$Item.migrationId
    switch ($migrationId) {
        '20260624_dcc_view_matrix_independent_seed' {
            $seedTenantId = switch ($TargetEnvironment) {
                'test' { '122' }
                'prod' { '1' }
                'backup' { '1' }
                default { Fail "Unsupported DCC view matrix seed environment: $TargetEnvironment" }
            }
            $sessionLines = @(
                "SET @dcc_view_matrix_seed_tenant_id := $seedTenantId;"
            )
            if ($TargetEnvironment -in @('prod', 'backup')) {
                $sessionLines += "SET @dcc_view_matrix_seed_allow_yudao_tenant := 1;"
            } else {
                $sessionLines += "SET @dcc_view_matrix_seed_allow_yudao_tenant := NULL;"
            }
            return $sessionLines -join [Environment]::NewLine
        }
        default {
            return ''
        }
    }
}

function Sort-RequiredDatabaseSqlApplyItems {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [AllowNull()]
        [object[]]$Items,

        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )

    if ($TargetEnvironment -ne 'test') {
        return @($Items)
    }

    if ($null -eq $Items -or $Items.Count -eq 0) {
        return @()
    }

    $priorityMap = @{
        '20260624_dcc_view_matrix_test_tenant_prereq' = 10
        '20260624_dcc_view_matrix_independent_seed' = 20
    }

    $indexedItems = @()
    for ($index = 0; $index -lt $Items.Count; $index++) {
        $indexedItems += [pscustomobject]@{
            Item = $Items[$index]
            OriginalOrder = $index
        }
    }

    return @(
        $indexedItems |
            Sort-Object `
                @{ Expression = {
                    $migrationId = [string]$_.Item.migrationId
                    if ($priorityMap.ContainsKey($migrationId)) {
                        return [int]$priorityMap[$migrationId]
                    }
                    return 1000 + [int]$_.OriginalOrder
                } }, `
                @{ Expression = { [int]$_.OriginalOrder } } |
            ForEach-Object { $_.Item }
    )
}

function Invoke-RequiredDatabaseSqlScripts {
    Info 'Applying required database SQL scripts'
    $preflightPlan = Read-ReleasePreflightPlan
    foreach ($item in @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ALREADY_APPLIED' })) {
        Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'SKIPPED_ALREADY_APPLIED'
    }
    foreach ($item in @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ENV_NOT_ALLOWED' })) {
        Info "Skipping required database SQL outside target environment: $($item.migrationId)"
    }
    $applyItems = Sort-RequiredDatabaseSqlApplyItems -Items (Get-ReleasePreflightApplyItems -PreflightPlan $preflightPlan) -TargetEnvironment $Environment
    foreach ($item in $applyItems) {
        $fileName = Get-RequiredDatabaseSqlFileName -RelativePath ([string]$item.file)
        $remoteSqlPath = "$remoteRequiredSqlDir/$fileName"
        $sessionPreamble = Get-RequiredDatabaseSqlSessionPreamble -Item $item -TargetEnvironment $Environment
        Info "Applying required database SQL: $fileName"
        Invoke-SshCommand "test -f '$remoteSqlPath' && echo REQUIRED_SQL_EXISTS"
        Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'RUNNING'
        try {
            if ([string]::IsNullOrWhiteSpace($sessionPreamble)) {
                Invoke-SshCommand "cat '$remoteSqlPath' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 ruoyi-vue-pro"
            } else {
                $escapedSessionPreamble = $sessionPreamble.TrimEnd()
                Invoke-SshCommand "{
cat <<'SQL'
$escapedSessionPreamble
SQL
cat '$remoteSqlPath'
} | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword --default-character-set=utf8mb4 ruoyi-vue-pro"
            }
        } catch {
            Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'FAILED' -ErrorMessage $_.Exception.Message
            throw
        }
        Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'APPLIED'
    }
}

if ($Mode -eq 'mark-tested') {
    Mark-NasReleaseTested -PackageTag $ReleaseTag
    Write-Host "Release package marked as tested: $ReleaseTag"
    exit 0
}

if ($Mode -eq 'deploy-release') {
    Info "Deploying release package: $ReleaseTag"
    Copy-ReleasePackageFromNas -PackageTag $ReleaseTag
    Assert-ProdDryRunEvidence
    $requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts
    $Component = Resolve-DeployReleasePackageComponent -ComponentExplicit $componentExplicit
    $publishBackend = $Component -in @('full', 'intruoyi', 'backend')
    $publishFrontend = $Component -in @('full', 'intruoyi', 'frontend')
    $publishWebsite = $Component -in @('full', 'website')
    $releasePublishScope = Resolve-DeployReleasePackageScope
    $releaseOnlyOfficeIncluded = Resolve-DeployReleasePackageOnlyOfficeIncluded
    $IncludeOnlyOffice = $releaseOnlyOfficeIncluded
    Assert-DeployReleasePackageArtifactsForScope -PublishScope $releasePublishScope
    if ($publishBackend) {
        Assert-RequiredDatabaseSqlScriptsInRelease
    }
    Apply-ReleaseRuntimeEnvPackage -TargetEnvironment $Environment
    if ($releasePublishScope -eq 'code-only') {
        $SkipDatabaseSync = $true
        $SkipMinioSync = $true
    } elseif ($releasePublishScope -eq 'with-data') {
        Info 'Deploying with-data release package'
    }
    if ($smartReleaseReportOnlyEnabled -and $Mode -eq 'deploy-release') {
        Invoke-SmartReleaseDeployPrecheckReportOnly -PackagePath $releaseDir
    }
}

Set-PublishRuntimeDefaultsForTarget -TargetServerHost $ServerHost -TargetEnvironment $Environment

if ($Mode -ne 'mark-tested') {
    Require-Command 'docker'
    Require-Command 'python'
}
if ($Mode -ne 'build-release') {
    Require-Command 'ssh'
    Require-Command 'scp'
}
if ($Mode -ne 'deploy-release') {
    Require-Command 'mvn'
    Require-Command 'node'
    Require-Command 'npm'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccSignatureEvidenceHmacSecret)) {
    Fail 'Missing DCC_SIGNATURE_EVIDENCE_HMAC_SECRET; DCC electronic signature evidence is fail-fast and requires an explicit HMAC secret.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccSignatureEvidenceKeyVersion)) {
    Fail 'Missing DCC_SIGNATURE_EVIDENCE_KEY_VERSION; DCC electronic signature evidence is fail-fast and requires an explicit key version.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and ([string]::IsNullOrWhiteSpace($DccViewerTokenHmacSecret) -or $DccViewerTokenHmacSecret.Trim().Length -lt 32)) {
    Fail 'Missing DCC_VIEWER_TOKEN_HMAC_SECRET; DCC viewer tokens are fail-fast and require an explicit HMAC secret of at least 32 characters.'
}

if ($publishBackend -and $IncludeOnlyOffice -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccOnlyOfficeJwtSecret)) {
    Fail 'Missing DCC_ONLYOFFICE_JWT_SECRET; DCC OnlyOffice preview URL tokens are fail-fast and require an explicit signing secret.'
}

if ($publishBackend -and $IncludeOnlyOffice -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccOnlyOfficeBaseUrl)) {
    Fail 'Missing DCC_ONLYOFFICE_BASE_URL; DCC OnlyOffice preview requires an explicit browser-accessible document server URL.'
}

if ($publishBackend -and $IncludeOnlyOffice -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccOnlyOfficePublicFileBaseUrl)) {
    Fail 'Missing DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL; DCC OnlyOffice preview requires an explicit document-server-accessible backend URL.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccDownloadEncryptionPolicyVersion)) {
    Fail 'Missing DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION; DCC controlled download encryption is fail-fast and requires an explicit policy version.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccDownloadEncryptionKeyId)) {
    Fail 'Missing DCC_DOWNLOAD_ENCRYPTION_KEY_ID; DCC controlled download encryption is fail-fast and requires an explicit key id.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccDownloadEncryptionBase64Key)) {
    Fail 'Missing DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY; DCC controlled download encryption is fail-fast and requires an explicit AES key.'
}

if ($publishBackend -and $Mode -ne 'build-release' -and [string]::IsNullOrWhiteSpace($DccDownloadEncryptionArtifactDirectory)) {
    Fail 'Missing DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY; DCC controlled download encryption is fail-fast and requires an explicit artifact directory.'
}

$edhrProtectedStorageSettings = Get-EdhrProtectedStorageSettings
if ($publishBackend) {
    Assert-EdhrProtectedStorageConfig -Context 'target publish environment' -Settings $edhrProtectedStorageSettings
    Set-EdhrStorageVerifierEnvironment -Settings $edhrProtectedStorageSettings
    Invoke-EdhrStorageRetentionVerifier -BackendRepo $backendRepo
}

$mySqlRootPassword = ''
if ($publishBackend) {
    $mySqlRootPassword = Get-LocalContainerEnvValue -ContainerName $LocalMySqlContainer -Key 'MYSQL_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($mySqlRootPassword)) {
        Fail "Missing MYSQL_ROOT_PASSWORD in local container $LocalMySqlContainer"
    }
}

$localMinioAccessKey = ''
$localMinioSecretKey = ''
if ($publishBackend -and $Mode -ne 'deploy-release' -and -not $SkipMinioSync) {
    $localMinioAccessKey = Get-LocalContainerEnvValue -ContainerName $LocalMinioContainer -Key 'MINIO_ROOT_USER'
    if ([string]::IsNullOrWhiteSpace($localMinioAccessKey)) {
        $localMinioAccessKey = Get-LocalContainerEnvValue -ContainerName $LocalMinioContainer -Key 'MINIO_USER'
    }
    $localMinioSecretKey = Get-LocalContainerEnvValue -ContainerName $LocalMinioContainer -Key 'MINIO_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($localMinioSecretKey)) {
        $localMinioSecretKey = Get-LocalContainerEnvValue -ContainerName $LocalMinioContainer -Key 'MINIO_PASSWORD'
    }
}

$remoteMinioAccessKey = ''
$remoteMinioSecretKey = ''
$requiresRemoteMinioCredentials = $publishBackend -and $Mode -ne 'build-release'
if ($requiresRemoteMinioCredentials -and [string]::IsNullOrWhiteSpace($RemoteMinioContainer)) {
    Fail 'Missing -RemoteMinioContainer; target MinIO credentials are required for target file storage rebind.'
}
if ($requiresRemoteMinioCredentials) {
    $remoteMinioAccessKey = Get-RemoteContainerEnvValue -ContainerName $RemoteMinioContainer -Key 'MINIO_ROOT_USER'
    if ([string]::IsNullOrWhiteSpace($remoteMinioAccessKey)) {
        $remoteMinioAccessKey = Get-RemoteContainerEnvValue -ContainerName $RemoteMinioContainer -Key 'MINIO_USER'
    }
    $remoteMinioSecretKey = Get-RemoteContainerEnvValue -ContainerName $RemoteMinioContainer -Key 'MINIO_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($remoteMinioSecretKey)) {
        $remoteMinioSecretKey = Get-RemoteContainerEnvValue -ContainerName $RemoteMinioContainer -Key 'MINIO_PASSWORD'
    }
}

if ($publishBackend -and $Mode -ne 'deploy-release' -and -not $SkipMinioSync -and (
    [string]::IsNullOrWhiteSpace($localMinioAccessKey) -or
    [string]::IsNullOrWhiteSpace($localMinioSecretKey)
)) {
    Fail 'Missing local MinIO credentials from running containers'
}

if ($requiresRemoteMinioCredentials -and (
    [string]::IsNullOrWhiteSpace($remoteMinioAccessKey) -or
    [string]::IsNullOrWhiteSpace($remoteMinioSecretKey)
)) {
    Fail 'Missing remote MinIO credentials from running containers; target file storage rebind requires them'
}

Info 'Checking local Docker daemon'
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('info')
if ($null -ne $backendRuntimeBaseConfig) {
    Assert-BackendRuntimeBaseImageAvailable -Config $backendRuntimeBaseConfig
}

if ($Mode -ne 'build-release') {
    Info "Checking SSH access to $ServerHost"
    Invoke-CheckedCommand -FilePath 'ssh' -ArgumentList (New-SshArgumentList -Command 'echo SSH_OK')

    Info "Checking docker compose on $ServerHost"
    Invoke-SshCommand 'docker compose version'
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

try {
if ($Mode -ne 'deploy-release') {
if ($publishBackend) {
Copy-RequiredDatabaseSqlScripts
}

if ($publishBackend) {
Info 'Building backend jar'
Invoke-CheckedCommand -FilePath 'mvn' -ArgumentList @(
    '-f', (Join-Path $backendRepo 'pom.xml'),
    '-pl', 'yudao-server',
    '-am',
    '-DskipTests',
    'clean',
    'package'
)
}

if ($publishFrontend) {
Info "Building frontend static assets for the $PublishTargetName server"
$oldNodeOptions = $env:NODE_OPTIONS
$oldBaseUrl = $env:VITE_BASE_URL
$oldBasePath = $env:VITE_BASE_PATH
$oldOutDir = $env:VITE_OUT_DIR
$viteCacheDir = Join-Path $frontendDir 'node_modules\.vite'
try {
    $env:NODE_OPTIONS = '--max-old-space-size=8192'
    if ($Mode -eq 'build-release') {
        $env:VITE_BASE_URL = ''
    } else {
        $env:VITE_BASE_URL = "http://${ServerHost}:$BackendPort"
    }
    $env:VITE_BASE_PATH = '/'
    $env:VITE_OUT_DIR = 'dist-intruoyi-test'
    if (Test-Path -LiteralPath $viteCacheDir) {
        Info "Clearing frontend Vite cache: $viteCacheDir"
        Remove-Item -LiteralPath $viteCacheDir -Recurse -Force
    }
    Invoke-FrontendViteBuild -FrontendDir $frontendDir
    $frontendReleaseInfoSourceRepos = New-ReleaseSourceRepoManifestEntries
    Write-FrontendReleaseInfo -FrontendDir $frontendDir -PackageTag $packageDirectoryName -SourceRepos $frontendReleaseInfoSourceRepos
    Assert-FrontendBuildStaticAssetContract -FrontendDir $frontendDir
} finally {
    $env:NODE_OPTIONS = $oldNodeOptions
    $env:VITE_BASE_URL = $oldBaseUrl
    $env:VITE_BASE_PATH = $oldBasePath
    $env:VITE_OUT_DIR = $oldOutDir
}
}

if ($publishWebsite) {
Info 'Building Website static assets'
$websiteDistSource = Join-Path $websiteRuntimeLocal 'dist'
if (Test-Path -LiteralPath $websiteRuntimeLocal) {
    Remove-Item -LiteralPath $websiteRuntimeLocal -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $websiteRuntimeLocal | Out-Null
Invoke-CheckedCommand -FilePath 'npm' -ArgumentList @('run', 'build', '--', '--outDir', $websiteDistSource, '--emptyOutDir') -WorkingDirectory $websiteRepo
if (-not (Test-Path -LiteralPath $websiteDistSource)) {
    Fail "Website build output missing: $websiteDistSource"
}

if ($Mode -eq 'build-release') {
    Copy-Item -LiteralPath $websiteNginxTemplate -Destination (Join-Path $websiteRuntimeLocal 'nginx.template.conf') -Force
} else {
    $websiteNginxTemplateText = [System.IO.File]::ReadAllText($websiteNginxTemplate, [System.Text.UTF8Encoding]::new($false))
    $websiteNginxText = $websiteNginxTemplateText.Replace('__BACKEND_ORIGIN__', "${ServerHost}:$BackendPort")
    [System.IO.File]::WriteAllText($websiteNginxLocal, $websiteNginxText, [System.Text.UTF8Encoding]::new($false))
}
}

if ($publishBackend -or $publishFrontend) {
    Info 'Preparing Docker build context from current worktree artifacts'
    New-ReleaseDockerBuildContext `
        -ContextRoot $dockerBuildContextRoot `
        -BackendRepoRoot $backendRepo `
        -FrontendRepoRoot $frontendDir `
        -IncludeBackend:$publishBackend `
        -IncludeFrontend:$publishFrontend `
        -BackendJarPath $backendJar
    if ($publishBackend) {
        $backendJarContextPath = Join-Path $dockerBuildContextRoot 'ruoyi-vue-pro\yudao-server\target\yudao-server-exec.jar'
        if (-not (Test-Path -LiteralPath $backendJarContextPath -PathType Leaf)) {
            Fail "Backend exec jar missing from Docker build context after preparation: $backendJarContextPath"
        }
    }
}

if ($publishBackend) {
Info 'Building backend image'
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
    'build',
    '--no-cache',
    '--build-arg', "BACKEND_RUNTIME_BASE_IMAGE=$($backendRuntimeBaseConfig.Image)",
    '-t', "intruoyi-backend:$packageDirectoryName",
    '-f', $backendDockerfile,
    $dockerBuildContextRoot
)
}

if ($publishFrontend) {
Info 'Building frontend image'
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
    'build',
    '--no-cache',
    '-t', "intruoyi-frontend:$packageDirectoryName",
    '-f', $frontendDockerfile,
    $dockerBuildContextRoot
)
}

if ($publishBackend -and $IncludeOnlyOffice) {
    Info 'Checking OnlyOffice image'
    Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
        'image',
        'inspect',
        $onlyOfficeImage
    )
}

$releaseImages = @()
if ($publishBackend) { $releaseImages += "intruoyi-backend:$packageDirectoryName" }
if ($publishFrontend) { $releaseImages += "intruoyi-frontend:$packageDirectoryName" }
if ($publishBackend -and $IncludeOnlyOffice) { $releaseImages += $onlyOfficeImage }
if ($releaseImages.Count -gt 0) {
    Info 'Exporting release images'
    Invoke-CheckedCommand -FilePath 'docker' -ArgumentList (@('save', '-o', $imageTar) + $releaseImages)
}

if ($publishBackend -and -not $SkipDatabaseSync) {
    Info 'Dumping current local MySQL database'
    $dumpErr = Join-Path $releaseDir 'mysqldump.err.log'
    $dumpProcess = Start-Process -FilePath 'docker' -ArgumentList @(
        'exec',
        'int-ruoyi-mysql',
        'mysqldump',
        '--single-transaction',
        '--routines',
        '--triggers',
        '--hex-blob',
        '--default-character-set=utf8mb4',
        '-uroot',
        "-p$mySqlRootPassword",
        '--databases',
        'ruoyi-vue-pro'
    ) -RedirectStandardOutput $dbDump -RedirectStandardError $dumpErr -NoNewWindow -Wait -PassThru
    if ($dumpProcess.ExitCode -ne 0) {
        $stderr = Get-Content -LiteralPath $dumpErr -Raw -ErrorAction SilentlyContinue
        Fail "mysqldump failed: $stderr"
    }

    $resetDbSql = @'
DROP DATABASE IF EXISTS `ruoyi-vue-pro`;
CREATE DATABASE `ruoyi-vue-pro` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
'@
    [System.IO.File]::WriteAllText($resetDbSqlLocal, $resetDbSql, [System.Text.UTF8Encoding]::new($false))
    Write-TargetBoundPostImportSql
}

if ($publishBackend -and $Mode -eq 'build-release' -and -not $SkipMinioSync) {
    Info 'Exporting local MinIO yudao bucket into release package'
    $minioSnapshotLocal = Join-Path $releaseDir 'minio\yudao'
    New-Item -ItemType Directory -Force -Path $minioSnapshotLocal | Out-Null
    $minioExportCommand = "docker run --rm --add-host host.docker.internal:host-gateway -v `"${minioSnapshotLocal}:/snapshot/yudao`" --entrypoint /bin/sh minio/mc -c 'mc alias set src http://host.docker.internal:9000 $localMinioAccessKey $localMinioSecretKey && mc mirror --overwrite --disable-multipart --retry src/yudao /snapshot/yudao'"
    Invoke-CheckedShell -Command $minioExportCommand -DisplayCommand 'docker run --rm --add-host host.docker.internal:host-gateway -v "<release>/minio/yudao:/snapshot/yudao" --entrypoint /bin/sh minio/mc -c "mc alias set src <redacted> && mc mirror --overwrite --disable-multipart --retry src/yudao /snapshot/yudao"'
    if (-not $SkipDatabaseSync) {
        Write-DccObjectInventoryForReleasePackage -MinioSnapshotRoot $minioSnapshotLocal
    }
}

if ($publishBackend) { New-SchedulerSmokeRunnerPackage }

Write-ReleaseRuntimeEnvPackage
Copy-Item -LiteralPath $composeTemplate -Destination (Join-Path $releaseDir 'docker-compose.yml') -Force
Remove-ReleaseDockerBuildContextFromPackage
Write-ReleaseManifest -PackageTag $ReleaseTag

if ($smartReleaseReportOnlyEnabled -and $Mode -eq 'build-release') {
    Invoke-SmartReleaseBuildReportOnly -PackagePath $releaseDir
}

if ($Mode -eq 'build-release') {
    Copy-ReleasePackageToNas -PackageTag $ReleaseTag
    Write-Host ''
    Write-Host "Release package built: $ReleaseTag"
    Write-Host "NAS release path: $NasReleaseRoot/$packageDirectoryName"
    exit 0
}
}
} finally {
    Exit-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile
}

if ($Mode -eq 'deploy-release' -and $publishWebsite) {
    $websiteTemplateInPackage = Join-Path $websiteRuntimeLocal 'nginx.template.conf'
    if (Test-Path -LiteralPath $websiteTemplateInPackage) {
        $websiteNginxTemplateText = [System.IO.File]::ReadAllText($websiteTemplateInPackage, [System.Text.UTF8Encoding]::new($false))
    } else {
        $websiteNginxTemplateText = [System.IO.File]::ReadAllText($websiteNginxTemplate, [System.Text.UTF8Encoding]::new($false))
    }
    $websiteNginxText = $websiteNginxTemplateText.Replace('__BACKEND_ORIGIN__', "${ServerHost}:$BackendPort")
    [System.IO.File]::WriteAllText($websiteNginxLocal, $websiteNginxText, [System.Text.UTF8Encoding]::new($false))
}

if ($Mode -eq 'deploy-release') {
    if ($publishBackend) {
        Info 'Regenerating target-bound post-import SQL for deploy-release'
        Write-TargetBoundPostImportSql
    }
} elseif ($publishBackend -and $Mode -ne 'build-release' -and -not (Test-Path -LiteralPath $postImportSqlLocal)) {
    Info 'Generating target-bound post-import SQL for deployment'
    Write-TargetBoundPostImportSql
}

Info 'Preparing remote runtime data disk'
Assert-RemoteRuntimeDataOnDataDisk

Info 'Preparing remote release directories'
Prepare-RemoteReleaseTree

Info 'Writing remote compose environment file locally'
$existingRemoteEnv = @{}
if (($publishBackend -or $publishFrontend) -and $Mode -ne 'build-release') {
    $existingRemoteEnv = Get-RemoteRuntimeEnvMap
}
function Resolve-ExistingRuntimeEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [string]$DefaultValue = ''
    )

    if ($existingRemoteEnv.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($existingRemoteEnv[$Name])) {
        return $existingRemoteEnv[$Name]
    }
    return $DefaultValue
}

$effectiveMySqlRootPassword = if ($publishBackend -and -not [string]::IsNullOrWhiteSpace($mySqlRootPassword)) { $mySqlRootPassword } elseif ($existingRemoteEnv.ContainsKey('MYSQL_ROOT_PASSWORD')) { $existingRemoteEnv['MYSQL_ROOT_PASSWORD'] } else { '' }
$effectiveDccSignatureEvidenceHmacSecret = if (-not [string]::IsNullOrWhiteSpace($DccSignatureEvidenceHmacSecret)) { $DccSignatureEvidenceHmacSecret } elseif ($existingRemoteEnv.ContainsKey('DCC_SIGNATURE_EVIDENCE_HMAC_SECRET')) { $existingRemoteEnv['DCC_SIGNATURE_EVIDENCE_HMAC_SECRET'] } else { '' }
$effectiveDccSignatureEvidenceKeyVersion = if (-not [string]::IsNullOrWhiteSpace($DccSignatureEvidenceKeyVersion)) { $DccSignatureEvidenceKeyVersion } elseif ($existingRemoteEnv.ContainsKey('DCC_SIGNATURE_EVIDENCE_KEY_VERSION')) { $existingRemoteEnv['DCC_SIGNATURE_EVIDENCE_KEY_VERSION'] } else { '' }
$effectiveEdhrS3Endpoint = if (-not [string]::IsNullOrWhiteSpace($EdhrS3Endpoint)) { $EdhrS3Endpoint } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_ENDPOINT')) { $existingRemoteEnv['EDHR_S3_ENDPOINT'] } else { '' }
$effectiveEdhrS3Bucket = if (-not [string]::IsNullOrWhiteSpace($EdhrS3Bucket)) { $EdhrS3Bucket } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_BUCKET')) { $existingRemoteEnv['EDHR_S3_BUCKET'] } else { '' }
$effectiveEdhrS3Region = if (-not [string]::IsNullOrWhiteSpace($EdhrS3Region)) { $EdhrS3Region } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_REGION')) { $existingRemoteEnv['EDHR_S3_REGION'] } else { '' }
$effectiveEdhrS3AccessKey = if (-not [string]::IsNullOrWhiteSpace($EdhrS3AccessKey)) { $EdhrS3AccessKey } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_ACCESS_KEY')) { $existingRemoteEnv['EDHR_S3_ACCESS_KEY'] } else { '' }
$effectiveEdhrS3SecretKey = if (-not [string]::IsNullOrWhiteSpace($EdhrS3SecretKey)) { $EdhrS3SecretKey } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_SECRET_KEY')) { $existingRemoteEnv['EDHR_S3_SECRET_KEY'] } else { '' }
$effectiveEdhrS3RetentionMode = if (-not [string]::IsNullOrWhiteSpace($EdhrS3RetentionMode)) { $EdhrS3RetentionMode } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_RETENTION_MODE')) { $existingRemoteEnv['EDHR_S3_RETENTION_MODE'] } else { '' }
$effectiveEdhrS3RetainUntilDays = if (-not [string]::IsNullOrWhiteSpace($EdhrS3RetainUntilDays)) { $EdhrS3RetainUntilDays } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_RETAIN_UNTIL_DAYS')) { $existingRemoteEnv['EDHR_S3_RETAIN_UNTIL_DAYS'] } else { '' }
$effectiveEdhrS3RequireLegalHold = if (-not [string]::IsNullOrWhiteSpace($EdhrS3RequireLegalHold)) { $EdhrS3RequireLegalHold } elseif ($existingRemoteEnv.ContainsKey('EDHR_S3_REQUIRE_LEGAL_HOLD')) { $existingRemoteEnv['EDHR_S3_REQUIRE_LEGAL_HOLD'] } else { '' }
$effectiveDccViewerTokenHmacSecret = if (-not [string]::IsNullOrWhiteSpace($DccViewerTokenHmacSecret)) { $DccViewerTokenHmacSecret } elseif ($existingRemoteEnv.ContainsKey('DCC_VIEWER_TOKEN_HMAC_SECRET')) { $existingRemoteEnv['DCC_VIEWER_TOKEN_HMAC_SECRET'] } else { '' }
$effectiveDccOnlyOfficeJwtSecret = if (-not [string]::IsNullOrWhiteSpace($DccOnlyOfficeJwtSecret)) { $DccOnlyOfficeJwtSecret } elseif ($existingRemoteEnv.ContainsKey('DCC_ONLYOFFICE_JWT_SECRET')) { $existingRemoteEnv['DCC_ONLYOFFICE_JWT_SECRET'] } else { '' }
$effectiveDccOnlyOfficeBaseUrl = if (-not [string]::IsNullOrWhiteSpace($DccOnlyOfficeBaseUrl)) { $DccOnlyOfficeBaseUrl } elseif ($existingRemoteEnv.ContainsKey('DCC_ONLYOFFICE_BASE_URL')) { $existingRemoteEnv['DCC_ONLYOFFICE_BASE_URL'] } else { '' }
$effectiveDccOnlyOfficePublicFileBaseUrl = if (-not [string]::IsNullOrWhiteSpace($DccOnlyOfficePublicFileBaseUrl)) { $DccOnlyOfficePublicFileBaseUrl } elseif ($existingRemoteEnv.ContainsKey('DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL')) { $existingRemoteEnv['DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL'] } else { '' }
$effectiveDccDownloadEncryptionPolicyVersion = if (-not [string]::IsNullOrWhiteSpace($DccDownloadEncryptionPolicyVersion)) { $DccDownloadEncryptionPolicyVersion } elseif ($existingRemoteEnv.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION')) { $existingRemoteEnv['DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION'] } else { '' }
$effectiveDccDownloadEncryptionKeyId = if (-not [string]::IsNullOrWhiteSpace($DccDownloadEncryptionKeyId)) { $DccDownloadEncryptionKeyId } elseif ($existingRemoteEnv.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_KEY_ID')) { $existingRemoteEnv['DCC_DOWNLOAD_ENCRYPTION_KEY_ID'] } else { '' }
$effectiveDccDownloadEncryptionBase64Key = if (-not [string]::IsNullOrWhiteSpace($DccDownloadEncryptionBase64Key)) { $DccDownloadEncryptionBase64Key } elseif ($existingRemoteEnv.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY')) { $existingRemoteEnv['DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY'] } else { '' }
$effectiveDccDownloadEncryptionArtifactDirectory = if (-not [string]::IsNullOrWhiteSpace($DccDownloadEncryptionArtifactDirectory)) { $DccDownloadEncryptionArtifactDirectory } elseif ($existingRemoteEnv.ContainsKey('DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY')) { $existingRemoteEnv['DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY'] } else { '' }
$effectiveDccProjectCodeCodexCliCommand = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeCodexCliCommand)) { $DccProjectCodeCodexCliCommand } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_CODEX_CLI_COMMAND')) { $existingRemoteEnv['DCC_PROJECT_CODE_CODEX_CLI_COMMAND'] } else { '/opt/intruoyi/runtime/tools/codex' }
$effectiveDccProjectCodeCodexHome = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeCodexHome)) { $DccProjectCodeCodexHome } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_CODEX_HOME')) { $existingRemoteEnv['DCC_PROJECT_CODE_CODEX_HOME'] } else { '/opt/intruoyi/runtime/backend-codex-home' }
$effectiveDccProjectCodeCodexTimeoutSeconds = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeCodexTimeoutSeconds)) { $DccProjectCodeCodexTimeoutSeconds } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS')) { $existingRemoteEnv['DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS'] } else { '300' }
$effectiveDccProjectCodeRecognitionWorkerCount = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeRecognitionWorkerCount)) { $DccProjectCodeRecognitionWorkerCount } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT')) { $existingRemoteEnv['DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT'] } else { '5' }
$effectiveBackendRuntimeBaseMode = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseMode)) { $BackendRuntimeBaseMode } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_MODE')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_MODE'] } else { '' }
$effectiveBackendRuntimeBaseTarPath = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseTarPath)) { $BackendRuntimeBaseTarPath } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR'] } else { '' }
$effectiveBackendRuntimeBaseTarSha256 = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseTarSha256)) { $BackendRuntimeBaseTarSha256 } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR_SHA256')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR_SHA256'] } else { '' }
$effectiveBackendRuntimeBaseImage = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseImage)) { $BackendRuntimeBaseImage } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_IMAGE')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_IMAGE'] } else { '' }
$effectiveBackendRuntimeBaseDigest = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseDigest)) { $BackendRuntimeBaseDigest } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_DIGEST')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_DIGEST'] } else { '' }
$effectiveBackendRuntimeBaseVersion = if (-not [string]::IsNullOrWhiteSpace($BackendRuntimeBaseVersion)) { $BackendRuntimeBaseVersion } elseif ($existingRemoteEnv.ContainsKey('RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_VERSION')) { $existingRemoteEnv['RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_VERSION'] } else { '' }
$effectiveSchedulerSmokeFrontendDirectory = $schedulerSmokeFrontendDirectory
$effectiveSchedulerSmokeScriptName = $schedulerSmokeScriptName
$effectiveMesSmokeBaseUrl = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_BASE_URL' -DefaultValue "http://127.0.0.1:$FrontendPort"
$effectiveMesSmokeExcelFile = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_EXCEL_FILE' -DefaultValue "$schedulerSmokeFrontendDirectory/input/smart-scheduling-smoke-feedback.xlsx"
$effectiveMesSmokeArtifactDir = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_ARTIFACT_DIR' -DefaultValue "$schedulerSmokeFrontendDirectory/output/artifacts"
$effectiveMesSmokeNodeImage = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_NODE_IMAGE' -DefaultValue $schedulerSmokeNodeImage
$mesSmokeTenantName = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('6IqL6YGT5rqQ56CB'))
$defaultMesSmokeProductCode = 'YXN.069.001.1003'
$defaultMesSmokeErpUnitNumber = 'zhi'
$legacyRouteMissingMesSmokeProductCode = 'AW.106.03.08.1007'
$effectiveMesSmokeCapacityMode = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_CAPACITY_MODE' -DefaultValue 'PLANNED'
$effectiveMesSmokeProductCode = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_PRODUCT_CODE' -DefaultValue $defaultMesSmokeProductCode
if ($effectiveMesSmokeProductCode -eq $legacyRouteMissingMesSmokeProductCode) {
    Info "Replacing legacy MES_SMOKE_PRODUCT_CODE $legacyRouteMissingMesSmokeProductCode with route-ready default $defaultMesSmokeProductCode"
    $effectiveMesSmokeProductCode = $defaultMesSmokeProductCode
}
$effectiveMesSmokeErpUnitNumber = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_ERP_UNIT_NUMBER' -DefaultValue $defaultMesSmokeErpUnitNumber
if ($effectiveMesSmokeProductCode -eq $defaultMesSmokeProductCode -and $effectiveMesSmokeErpUnitNumber -eq 'PCS') {
    Info "Replacing legacy MES_SMOKE_ERP_UNIT_NUMBER PCS with route-ready product unit $defaultMesSmokeErpUnitNumber"
    $effectiveMesSmokeErpUnitNumber = $defaultMesSmokeErpUnitNumber
}
$effectiveMesSmokeBatchNumber = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_BATCH_NUMBER' -DefaultValue 'TEST-SMOKE-BATCH'
$effectiveMesSmokeDefaultPassword = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_DEFAULT_PASSWORD' -DefaultValue '111111'
$effectiveMesSmokeErpCreatorTenant = $mesSmokeTenantName
$effectiveMesSmokeErpCreatorUsername = 'messmokeerp'
$effectiveMesSmokeErpCreatorPassword = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_ERP_CREATOR_PASSWORD' -DefaultValue $effectiveMesSmokeDefaultPassword
$effectiveMesSmokePlannerTenant = $mesSmokeTenantName
$effectiveMesSmokePlannerUsername = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_PLANNER_USERNAME' -DefaultValue 'zhaojie'
$effectiveMesSmokePlannerPassword = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_PLANNER_PASSWORD' -DefaultValue $effectiveMesSmokeDefaultPassword
$effectiveMesSmokeSupervisorTenant = $mesSmokeTenantName
$effectiveMesSmokeSupervisorUsername = 'messmokesupervisor'
$effectiveMesSmokeFeedbackApproverName = $effectiveMesSmokeSupervisorUsername
$effectiveMesSmokeSupervisorPassword = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_SUPERVISOR_PASSWORD' -DefaultValue $effectiveMesSmokeDefaultPassword
$effectiveMesSmokeNonApproverTenant = $mesSmokeTenantName
$effectiveMesSmokeNonApproverUsername = 'messmokenonapprover'
$effectiveMesSmokeNonApproverPassword = Resolve-ExistingRuntimeEnvValue -Name 'MES_SMOKE_NON_APPROVER_PASSWORD' -DefaultValue $effectiveMesSmokeDefaultPassword
$mySqlRootPassword = $effectiveMySqlRootPassword
$DccSignatureEvidenceHmacSecret = $effectiveDccSignatureEvidenceHmacSecret
$DccSignatureEvidenceKeyVersion = $effectiveDccSignatureEvidenceKeyVersion
$EdhrS3Endpoint = $effectiveEdhrS3Endpoint
$EdhrS3Bucket = $effectiveEdhrS3Bucket
$EdhrS3Region = $effectiveEdhrS3Region
$EdhrS3AccessKey = $effectiveEdhrS3AccessKey
$EdhrS3SecretKey = $effectiveEdhrS3SecretKey
$EdhrS3RetentionMode = $effectiveEdhrS3RetentionMode
$EdhrS3RetainUntilDays = $effectiveEdhrS3RetainUntilDays
$EdhrS3RequireLegalHold = $effectiveEdhrS3RequireLegalHold
$DccViewerTokenHmacSecret = $effectiveDccViewerTokenHmacSecret
$DccOnlyOfficeJwtSecret = $effectiveDccOnlyOfficeJwtSecret
$DccOnlyOfficeBaseUrl = $effectiveDccOnlyOfficeBaseUrl
$DccOnlyOfficePublicFileBaseUrl = $effectiveDccOnlyOfficePublicFileBaseUrl
$DccDownloadEncryptionPolicyVersion = $effectiveDccDownloadEncryptionPolicyVersion
$DccDownloadEncryptionKeyId = $effectiveDccDownloadEncryptionKeyId
$DccDownloadEncryptionBase64Key = $effectiveDccDownloadEncryptionBase64Key
$DccDownloadEncryptionArtifactDirectory = $effectiveDccDownloadEncryptionArtifactDirectory
$DccProjectCodeCodexCliCommand = $effectiveDccProjectCodeCodexCliCommand
$DccProjectCodeCodexHome = $effectiveDccProjectCodeCodexHome
$DccProjectCodeCodexTimeoutSeconds = $effectiveDccProjectCodeCodexTimeoutSeconds
$DccProjectCodeRecognitionWorkerCount = $effectiveDccProjectCodeRecognitionWorkerCount
$BackendRuntimeBaseMode = $effectiveBackendRuntimeBaseMode
$BackendRuntimeBaseTarPath = $effectiveBackendRuntimeBaseTarPath
$BackendRuntimeBaseTarSha256 = $effectiveBackendRuntimeBaseTarSha256
$BackendRuntimeBaseImage = $effectiveBackendRuntimeBaseImage
$BackendRuntimeBaseDigest = $effectiveBackendRuntimeBaseDigest
$BackendRuntimeBaseVersion = $effectiveBackendRuntimeBaseVersion
$remoteEnvContent = @"
IMAGE_TAG=$packageDirectoryName
SPRING_PROFILES_ACTIVE=dev
SERVER_HOST=$ServerHost
RUNTIME_CONTROL_TEST_SERVER_HOST=$TestServerHost
RUNTIME_CONTROL_PROD_SERVER_HOST=$ProdServerHost
RUNTIME_CONTROL_BACKUP_SERVER_HOST=$BackupServerHost
FRONTEND_HOST_PORT=$FrontendPort
BACKEND_HOST_PORT=$BackendPort
WEBSITE_HOST_PORT=$WebsiteHostPort
ONLYOFFICE_HOST_PORT=$OnlyOfficeHostPort
MYSQL_DATABASE=ruoyi-vue-pro
MYSQL_ROOT_PASSWORD=$mySqlRootPassword
JAVA_OPTS=-Xms1g -Xmx2g -Djava.security.egd=file:/dev/./urandom
DCC_SIGNATURE_EVIDENCE_HMAC_SECRET=$DccSignatureEvidenceHmacSecret
DCC_SIGNATURE_EVIDENCE_KEY_VERSION=$DccSignatureEvidenceKeyVersion
EDHR_S3_ENDPOINT=$EdhrS3Endpoint
EDHR_S3_BUCKET=$EdhrS3Bucket
EDHR_S3_REGION=$EdhrS3Region
EDHR_S3_ACCESS_KEY=$EdhrS3AccessKey
EDHR_S3_SECRET_KEY=$EdhrS3SecretKey
EDHR_S3_RETENTION_MODE=$EdhrS3RetentionMode
EDHR_S3_RETAIN_UNTIL_DAYS=$EdhrS3RetainUntilDays
EDHR_S3_REQUIRE_LEGAL_HOLD=$EdhrS3RequireLegalHold
YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_FRONTEND_DIRECTORY=$effectiveSchedulerSmokeFrontendDirectory
YUDAO_MES_SCHEDULER_WORKBENCH_SMOKE_TEST_SCRIPT_NAME=$effectiveSchedulerSmokeScriptName
MES_SMOKE_BASE_URL=$effectiveMesSmokeBaseUrl
MES_SMOKE_EXCEL_FILE=$effectiveMesSmokeExcelFile
MES_SMOKE_ARTIFACT_DIR=$effectiveMesSmokeArtifactDir
MES_SMOKE_NODE_IMAGE=$effectiveMesSmokeNodeImage
MES_SMOKE_CAPACITY_MODE=$effectiveMesSmokeCapacityMode
MES_SMOKE_PRODUCT_CODE=$effectiveMesSmokeProductCode
MES_SMOKE_ERP_UNIT_NUMBER=$effectiveMesSmokeErpUnitNumber
MES_SMOKE_BATCH_NUMBER=$effectiveMesSmokeBatchNumber
MES_SMOKE_DEFAULT_PASSWORD=$effectiveMesSmokeDefaultPassword
MES_SMOKE_ERP_CREATOR_TENANT=$effectiveMesSmokeErpCreatorTenant
MES_SMOKE_ERP_CREATOR_USERNAME=$effectiveMesSmokeErpCreatorUsername
MES_SMOKE_ERP_CREATOR_PASSWORD=$effectiveMesSmokeErpCreatorPassword
MES_SMOKE_PLANNER_TENANT=$effectiveMesSmokePlannerTenant
MES_SMOKE_PLANNER_USERNAME=$effectiveMesSmokePlannerUsername
MES_SMOKE_PLANNER_PASSWORD=$effectiveMesSmokePlannerPassword
MES_SMOKE_SUPERVISOR_TENANT=$effectiveMesSmokeSupervisorTenant
MES_SMOKE_SUPERVISOR_USERNAME=$effectiveMesSmokeSupervisorUsername
MES_SMOKE_FEEDBACK_APPROVER_NAME=$effectiveMesSmokeFeedbackApproverName
MES_SMOKE_SUPERVISOR_PASSWORD=$effectiveMesSmokeSupervisorPassword
MES_SMOKE_NON_APPROVER_TENANT=$effectiveMesSmokeNonApproverTenant
MES_SMOKE_NON_APPROVER_USERNAME=$effectiveMesSmokeNonApproverUsername
MES_SMOKE_NON_APPROVER_PASSWORD=$effectiveMesSmokeNonApproverPassword
DCC_VIEWER_TOKEN_HMAC_SECRET=$DccViewerTokenHmacSecret
DCC_ONLYOFFICE_JWT_SECRET=$DccOnlyOfficeJwtSecret
DCC_ONLYOFFICE_BASE_URL=$DccOnlyOfficeBaseUrl
DCC_ONLYOFFICE_PUBLIC_FILE_BASE_URL=$DccOnlyOfficePublicFileBaseUrl
DCC_DOWNLOAD_ENCRYPTION_POLICY_VERSION=$DccDownloadEncryptionPolicyVersion
DCC_DOWNLOAD_ENCRYPTION_KEY_ID=$DccDownloadEncryptionKeyId
DCC_DOWNLOAD_ENCRYPTION_BASE64_KEY=$DccDownloadEncryptionBase64Key
DCC_DOWNLOAD_ENCRYPTION_ARTIFACT_DIRECTORY=$DccDownloadEncryptionArtifactDirectory
DCC_PROJECT_CODE_CODEX_CLI_COMMAND=$DccProjectCodeCodexCliCommand
DCC_PROJECT_CODE_CODEX_HOME=$DccProjectCodeCodexHome
DCC_PROJECT_CODE_CODEX_TIMEOUT_SECONDS=$DccProjectCodeCodexTimeoutSeconds
DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT=$DccProjectCodeRecognitionWorkerCount
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_MODE=$BackendRuntimeBaseMode
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR=$BackendRuntimeBaseTarPath
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR_SHA256=$BackendRuntimeBaseTarSha256
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_IMAGE=$BackendRuntimeBaseImage
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_DIGEST=$BackendRuntimeBaseDigest
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_VERSION=$BackendRuntimeBaseVersion
"@
$remoteEnvLocal = Join-Path $releaseDir '.env'
Write-Utf8LfNoBomFile -Path $remoteEnvLocal -Content $remoteEnvContent

Info "Copying compose and environment files to the $PublishTargetName server"
$composeLocal = Join-Path $releaseDir 'docker-compose.yml'
if (-not (Test-Path -LiteralPath $composeLocal)) {
    $composeLocal = $composeTemplate
}
if ($publishBackend -or $publishFrontend) {
    Copy-ToServer -LocalPath $composeLocal -RemotePath $remoteCompose
    Copy-ToServer -LocalPath $remoteEnvLocal -RemotePath $remoteEnv
    Assert-RemoteRuntimeEnvImageTag
}
if ($publishBackend) { Copy-SchedulerSmokeRunnerToServer }
if ($publishBackend -or $publishFrontend) {
    Copy-ToServer -LocalPath $imageTar -RemotePath $remoteImageTar
}
if ($publishWebsite) {
    Copy-ToServer -LocalPath $websiteRuntimeLocal -RemotePath $remoteReleaseDir -Recursive
    Invoke-SshCommand "test -f '$remoteWebsiteStagingDir/dist/index.html' && test -f '$remoteWebsiteStagingDir/nginx.conf'"
}
if ($publishBackend) {
    Copy-RequiredDatabaseSqlScriptsToServer
    Copy-ReleaseOpsRuntimePackage
}

Info "Reading remote compose services on the $PublishTargetName server"
$remoteComposeServices = Get-RemoteComposeServices
if ($publishBackend) {
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'mysql'
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'redis'
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'backend'
}
if ($publishBackend -and $IncludeOnlyOffice) {
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'onlyoffice'
}
if ($publishFrontend) {
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'frontend'
}
if ($publishWebsite) {
    Assert-RemoteComposeService -Services $remoteComposeServices -ServiceName 'website'
}

if ($publishBackend -and -not $SkipDatabaseSync) {
    Copy-ToServer -LocalPath $dbDump -RemotePath $remoteDbDump
    Copy-ToServer -LocalPath $resetDbSqlLocal -RemotePath $remoteResetDbSql
}

if ($publishBackend -and $Mode -ne 'build-release') {
    if (-not (Test-Path -LiteralPath $postImportSqlLocal)) {
        Fail "Target-bound post-import SQL missing: $postImportSqlLocal"
    }
    Copy-ToServer -LocalPath $postImportSqlLocal -RemotePath $remotePostImportSql
}

if ($publishBackend -or $publishFrontend) {
    Info "Loading release images on the $PublishTargetName server"
    Invoke-SshCommand "docker load -i '$remoteImageTar'"
}

if ($publishBackend) {
    if (-not $SkipMinioSync) {
        if ($Mode -eq 'deploy-release') {
            $minioSnapshotLocal = Join-Path $releaseDir 'minio\yudao'
            if (-not (Test-Path -LiteralPath $minioSnapshotLocal)) {
                Fail "Release package MinIO snapshot missing: $minioSnapshotLocal"
            }
            Info "Syncing MinIO bucket yudao from release package to the $PublishTargetName server"
            $minioSyncCommand = "docker run --rm -v `"${minioSnapshotLocal}:/snapshot/yudao:ro`" --entrypoint /bin/sh minio/mc -c 'mc alias set dst http://${ServerHost}:9000 $remoteMinioAccessKey $remoteMinioSecretKey && mc mb --ignore-existing dst/yudao && mc mirror --overwrite --disable-multipart --retry /snapshot/yudao dst/yudao && mc anonymous set download dst/yudao'"
            Invoke-CheckedShell -Command $minioSyncCommand -DisplayCommand 'docker run --rm -v "<release>/minio/yudao:/snapshot/yudao:ro" --entrypoint /bin/sh minio/mc -c "mc alias set dst <redacted> && mc mb --ignore-existing dst/yudao && mc mirror --overwrite --disable-multipart --retry /snapshot/yudao dst/yudao && mc anonymous set download dst/yudao"'
        } else {
            Info "Syncing MinIO bucket yudao from local host to the $PublishTargetName server"
            $minioSyncCommand = "docker run --rm --add-host host.docker.internal:host-gateway --entrypoint /bin/sh minio/mc -c 'mc alias set src http://host.docker.internal:9000 $localMinioAccessKey $localMinioSecretKey && mc alias set dst http://${ServerHost}:9000 $remoteMinioAccessKey $remoteMinioSecretKey && mc mb --ignore-existing dst/yudao && mc mirror --overwrite --disable-multipart --retry src/yudao dst/yudao && mc anonymous set download dst/yudao'"
            Invoke-CheckedShell -Command $minioSyncCommand -DisplayCommand 'docker run --rm --add-host host.docker.internal:host-gateway --entrypoint /bin/sh minio/mc -c "mc alias set src <redacted> && mc alias set dst <redacted> && mc mb --ignore-existing dst/yudao && mc mirror --overwrite --disable-multipart --retry src/yudao dst/yudao && mc anonymous set download dst/yudao"'
        }
    }
}

if ($publishBackend -and -not $SkipDatabaseSync) {
    Info 'Resetting remote MySQL container and data directory before import'
    Invoke-SshCommand "docker rm -f intruoyi-mysql 2>/dev/null || true"
    Invoke-SshCommand "rm -rf '$RemoteAppDir/data/mysql' && mkdir -p '$RemoteAppDir/data/mysql'"
}

if ($publishBackend) {
    Info "Starting MySQL and Redis on the $PublishTargetName server"
    Invoke-SshCommand "cd '$RemoteAppDir' && docker compose up -d mysql redis"
}

if ($publishBackend) {
    Info 'Waiting for remote MySQL health'
    Wait-RemoteContainerHealth -ContainerName 'intruoyi-mysql' -TimeoutSeconds 180
    Wait-RemoteMySqlReady -TimeoutSeconds 180
}

if ($publishBackend -and -not $SkipDatabaseSync) {
    Info 'Replacing remote MySQL database with the current local dump'
    Invoke-SshCommand "cat '$remoteResetDbSql' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword"
    Invoke-SshCommand "cat '$remoteDbDump' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword"
}

if ($publishBackend -and $Mode -ne 'build-release') {
    Info 'Applying target-bound post-import SQL'
    Invoke-SshCommand "cat '$remotePostImportSql' | docker exec -i intruoyi-mysql mysql -uroot -p$mySqlRootPassword -D ruoyi-vue-pro"
}

try {
    if ($publishBackend) {
        Ensure-ReleaseMigrationStateSchema
        Invoke-ReleaseOperationLockAcquire
        Write-ReleasePreflightPlan
        Invoke-RequiredDatabaseSqlScripts
        Assert-RemoteQuartzSchemaReady
        Assert-RemoteShowroomAwardSchemaReady
    }

    if ($publishBackend) {
        Assert-RemoteFileStorageConfigRebound
    }

    if ($publishWebsite) {
        Info "Switching Website runtime directory on the $PublishTargetName server"
        Invoke-SshCommand "test -f '$remoteWebsiteStagingDir/dist/index.html' && test -f '$remoteWebsiteStagingDir/nginx.conf' && rm -rf '$remoteWebsitePreviousDir' && if [ -d '$remoteWebsiteDir' ]; then mv '$remoteWebsiteDir' '$remoteWebsitePreviousDir'; fi && mv '$remoteWebsiteStagingDir' '$remoteWebsiteDir'"
    }

    $runtimeServices = @()
    if ($IncludeOnlyOffice) { $runtimeServices += 'onlyoffice' }
    if ($publishBackend) { $runtimeServices += 'backend' }
    if ($publishFrontend) { $runtimeServices += 'frontend' }
    if ($runtimeServices.Count -gt 0) {
        $runtimeServicesArg = $runtimeServices -join ' '
        $runtimeServiceDependencyFlag = if ($IncludeOnlyOffice) { '' } else { '--no-deps ' }
        Info "Starting application services on the $PublishTargetName server: $runtimeServicesArg"
        Invoke-SshCommand "cd '$RemoteAppDir' && docker compose up -d $runtimeServiceDependencyFlag$runtimeServicesArg"
    }

    if ($publishWebsite) {
        Info "Starting Website on the $PublishTargetName server"
    }
    if ($publishWebsite) { Invoke-SshCommand "cd '$RemoteAppDir' && docker compose up -d --force-recreate website" }

    Info 'Waiting for remote HTTP readiness'
    if ($publishBackend) {
        Wait-RemoteHttpOk -Url "http://127.0.0.1:$BackendPort/actuator/health" -TimeoutSeconds 180
        Assert-RemoteBackendContainerMinioReachable
    }
    if ($publishFrontend) {
        Wait-RemoteHttpOk -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSeconds 180
    }
    if ($publishBackend) { Assert-RemoteSchedulerSmokeRuntime }
    if ($IncludeOnlyOffice) {
        Wait-RemoteHttpOk -Url "http://127.0.0.1:$OnlyOfficeHostPort/healthcheck" -TimeoutSeconds 180
    }
    if ($publishWebsite) {
        Wait-RemoteHttpOk -Url "http://127.0.0.1:$WebsiteHostPort/showroom" -TimeoutSeconds 180
    }

    if ($publishBackend) {
        Invoke-ReleaseOperationLockRelease -Status 'APPLIED'
    }

    if ($publishBackend) { Wait-HttpOk -Url "http://${ServerHost}:$BackendPort/actuator/health" -TimeoutSeconds 180 }
    if ($publishFrontend) { Wait-HttpOk -Url "http://${ServerHost}:$FrontendPort/" -TimeoutSeconds 180 }
    if ($publishFrontend) {
        Wait-HttpContentTypeOk -Url "http://${ServerHost}:$FrontendPort/pdfjs/pdf.worker.mjs" -ExpectedContentType 'application/javascript' -TimeoutSeconds 180
    }
    $verifyShowroomMediaContent = $publishWebsite -or (-not $SkipMinioSync)
    if ($publishFrontend -and $verifyShowroomMediaContent) {
        Assert-RemoteShowroomSmokeImageContent
    } elseif ($publishFrontend) {
        Info 'Skipping showroom smoke image content check for code-only deploy without Website or MinIO data sync'
    }
    if ($publishBackend -and $IncludeOnlyOffice) {
        Wait-HttpOk -Url "http://${ServerHost}:$OnlyOfficeHostPort/healthcheck" -TimeoutSeconds 180
    }
    if ($publishWebsite) { Wait-HttpOk -Url "http://${ServerHost}:$WebsiteHostPort/" -TimeoutSeconds 180 }
    if ($publishWebsite) { Wait-HttpOk -Url "http://${ServerHost}:$WebsiteHostPort/showroom" -TimeoutSeconds 180 }
    if ($publishWebsite) { Assert-PublicWebsiteEntryReadback }
    if ($publishWebsite) { Assert-PublicWebsiteScopedReleaseCurrent }

    if ($Mode -eq 'deploy-release' -and @('prod', 'backup') -contains $Environment) {
        Write-NasReleaseDeploymentHistory -PackageTag $ReleaseTag -HistoryAction 'deploy' -HistoryEnvironment $Environment
    }
} catch {
    if ($publishBackend) {
        $releaseErrorMessage = $_.Exception.Message
        try {
            Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $releaseErrorMessage
        } catch {
        }
    }
    throw
}

Info 'Cleaning remote release temp files'
Invoke-SshCommand "rm -f '$remoteImageTar' '$remoteDbDump' '$remoteResetDbSql' '$remotePostImportSql'"
$remoteCleanupDirs = @()
if ($publishBackend) {
    $remoteCleanupDirs += $remoteRequiredSqlDir
}
if ($publishWebsite) {
    $remoteCleanupDirs += $remoteWebsitePreviousDir
}
if ($remoteCleanupDirs.Count -gt 0) {
    $remoteCleanupDirsArg = Join-ShellQuotedPathList -Paths $remoteCleanupDirs
    Invoke-SshCommand "rm -rf $remoteCleanupDirsArg"
}

Write-Host ''
Write-Host "Publish completed for $PublishTargetName."
if ($publishFrontend) {
    Write-Host "IntRuoyi frontend: http://${ServerHost}:$FrontendPort"
}
if ($publishBackend) {
    Write-Host "Backend health: http://${ServerHost}:$BackendPort/actuator/health"
}
if ($publishBackend -and $IncludeOnlyOffice) {
    Write-Host "OnlyOffice health: http://${ServerHost}:$OnlyOfficeHostPort/healthcheck"
}
if ($publishWebsite) {
    Write-Host "Website root: http://${ServerHost}:$WebsiteHostPort/"
    Write-Host "Website showroom: http://${ServerHost}:$WebsiteHostPort/showroom"
}
