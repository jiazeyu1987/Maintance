param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('build-release', 'deploy-release', 'mark-tested')]
    [string]$Mode,
    [ValidateSet('full', 'intruoyi')]
    [string]$Component = 'full',
    [string]$ReleaseTag = '',
    [string]$NasConfigPath = '',
    [string]$NasReleaseRoot = 'Backup/ReleasePackage',
    [string]$NasServer = '172.30.30.4',
    [string]$NasShare = '',
    [string]$OperatorName = $env:USERNAME,
    [ValidateSet('', 'PASS', 'FAIL')]
    [string]$TestResult = '',
    [string]$TestConclusion = '',
    [string]$TestOperationId = '',
    [string]$TestOperationEvidencePath = '',
    [string]$ExpectedPackageDigest = '',
    [string]$ExpectedManifestDigest = '',
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
    # Platform floor only; review migration-specific temporary/log growth separately.
    [ValidateRange(1073741824, 9223372036854775807)]
    [int64]$DatabaseCapacityReserveBytes = 1073741824,
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
    [string]$ExpectedMaintenanceCommit = $env:INT_RUOYI_EXPECTED_MAINTENANCE_COMMIT,
    [string]$ExpectedApplicationCommit = $env:INT_RUOYI_EXPECTED_APPLICATION_COMMIT,
    [string]$ExpectedFrontendCommit = $env:INT_RUOYI_EXPECTED_FRONTEND_COMMIT,
    [string]$SourceSelectionId = $env:INT_RUOYI_SOURCE_SELECTION_ID,
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
    [string]$DccProjectCodeRecognitionVersion = $env:DCC_PROJECT_CODE_RECOGNITION_VERSION,
    [string]$DccProjectCodeRecognitionWorkerCount = $env:DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT,
    [string]$ShowroomCodexCliCommand = $env:SHOWROOM_CODEX_CLI_COMMAND,
    [string]$LocalCacheRoot = $env:INTRUOYI_LOCAL_CACHE_ROOT,
    [ValidateSet('offline-tar')]
    [string]$BackendRuntimeBaseMode = $env:INTRUOYI_BACKEND_RUNTIME_BASE_MODE,
    [string]$BackendRuntimeBaseTarPath = $env:INTRUOYI_BACKEND_RUNTIME_BASE_TAR,
    [string]$BackendRuntimeBaseTarSha256 = $env:INTRUOYI_BACKEND_RUNTIME_BASE_TAR_SHA256,
    [string]$BackendRuntimeBaseImage = $env:INTRUOYI_BACKEND_RUNTIME_BASE_IMAGE,
    [string]$BackendRuntimeBaseDigest = $env:INTRUOYI_BACKEND_RUNTIME_BASE_DIGEST,
    [string]$BackendRuntimeBaseVersion = $env:INTRUOYI_BACKEND_RUNTIME_BASE_VERSION,
    [switch]$IncludeOnlyOffice,
    [ValidateSet('app-release')]
    [string]$PublishScope = 'app-release',
    [switch]$SkipDatabaseSync,
    [switch]$SkipMinioSync,
    [switch]$EnableSmartReleaseReport,
    [string]$SmartReleaseBaselineManifestPath = $env:INTRUOYI_SMART_RELEASE_BASELINE_MANIFEST_PATH,
    [string]$SmartReleaseLocalDatabaseConfigPath = $env:INTRUOYI_SMART_RELEASE_LOCAL_DATABASE_CONFIG_PATH,
    [string]$SmartReleaseDataOwnershipRegistryPath = $env:INTRUOYI_SMART_RELEASE_DATA_OWNERSHIP_REGISTRY_PATH,
    [string]$SmartReleaseTargetConfigPath = $env:INTRUOYI_SMART_RELEASE_TARGET_CONFIG_PATH
)

$ErrorActionPreference = 'Stop'
$releaseConsoleEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $releaseConsoleEncoding
[Console]::OutputEncoding = $releaseConsoleEncoding
$OutputEncoding = $releaseConsoleEncoding
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
$PSNativeCommandUseErrorActionPreference = $false
}
Import-Module -Force (Join-Path $PSScriptRoot '..\release\lib\ReleasePackageGovernance.psm1')
Import-Module -Force (Join-Path $PSScriptRoot '..\release\lib\ReleaseManifestValidator.psm1')
Import-Module -Force (Join-Path $PSScriptRoot '..\release\lib\ReleaseDeploymentEvidence.psm1')
$script:DeploymentState = $null
$script:DeploymentOperation = $null
$script:DeploymentGateBeforeLock = $null
$script:ReleaseMigrationFailureErrors = @()
$script:ReleaseHistoryFailureErrors = @()
if ($Mode -eq 'deploy-release' -and $PSBoundParameters.ContainsKey('Component')) {
    throw 'DEPLOY_COMPONENT_OVERRIDE_FORBIDDEN: component selection is fixed by the complete package'
}
if ($Mode -eq 'deploy-release' -and $PSBoundParameters.ContainsKey('IncludeOnlyOffice')) {
    throw 'DEPLOY_ONLYOFFICE_OVERRIDE_FORBIDDEN: OnlyOffice selection is fixed by the complete package'
}
$script:ReleaseOperationLockHeld = $false
$script:ReleaseOperationLegacyLockHeld = $false
$script:ReleaseOperationLockReleasing = $false
$script:ReleaseOperationLeaseToken = ''
$script:ReleaseOperationExecutorHost = [string]$env:COMPUTERNAME
$script:ReleaseOperationExecutorPid = [string]$PID
$script:ReleaseOperationExecutorIdentity = "$([string]$env:USERNAME)@$([string]$env:COMPUTERNAME)"
$script:BuildReleaseRuntimeRestartGuardCreated = $false
$script:ReleasePackageArtifactCache = @()
$script:ReleaseErrorMessageMaxLength = 2048
$releaseMigrationExecutableTypes = @('schema', 'data', 'menu', 'config', 'permission', 'seed')
$releaseMigrationEvidenceOnlyTypes = @('preflight', 'backfill', 'postflight', 'rollback-dry-run')
$releaseMigrationAllowedTypes = @($releaseMigrationExecutableTypes + $releaseMigrationEvidenceOnlyTypes)

function Fail([string]$Message) {
    # All failures must reach the deployment catch so durable evidence is kept.
    # An in-memory flag is never proof that the remote lease was released.
    throw $Message
}

function Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Write-ReleaseWorkflowStage {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('TESTING', 'BUILDING')]
        [string]$State,
        [Parameter(Mandatory = $true)]
        [string]$Evidence
    )

    if ([string]::IsNullOrWhiteSpace($Evidence)) {
        Fail 'Release workflow stage evidence is required.'
    }
    $safeEvidence = ([string]$Evidence).Trim() -replace '[^A-Za-z0-9._:/=-]', '_'
    Write-Host "RELEASE_WORKFLOW_STAGE=$State evidence=$safeEvidence"
}

function Invoke-ReleaseStage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock
    )

    $stageStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $stageCompleted = $false
    Info "Starting release stage: $Name"
    try {
        & $ScriptBlock
        $stageCompleted = $true
    } finally {
        $stageStopwatch.Stop()
        if ($stageCompleted) {
            Info ("Completed release stage: {0} ({1:n1}s)" -f $Name, $stageStopwatch.Elapsed.TotalSeconds)
        } else {
            Info ("Failed release stage: {0} ({1:n1}s)" -f $Name, $stageStopwatch.Elapsed.TotalSeconds)
        }
    }
}

function Resolve-EffectiveBuildReleasePublishScope {
    if ($Mode -ne 'build-release') {
        return ''
    }

    if ($PublishScope -ne 'app-release') {
        Fail 'Standard release workflow requires PublishScope=app-release'
    }
    $script:SkipDatabaseSync = $true
    $script:SkipMinioSync = $true
    Info 'Standard build-release is app-release; database and MinIO snapshots are excluded.'
    return 'app-release'
}

function Set-ReleasePackageArtifactCache {
    param(
        [Parameter(Mandatory = $true)]
        [array]$Artifacts
    )
    $script:ReleasePackageArtifactCache = @($Artifacts)
}

function Get-ReleasePackageArtifactCache {
    if ($null -eq $script:ReleasePackageArtifactCache) {
        return @()
    }
    return @($script:ReleasePackageArtifactCache)
}

function Write-ReleasePackageSizeSummary {
    param(
        [Parameter(Mandatory = $true)]
        [array]$Artifacts
    )

    $summaryFiles = @($Artifacts)
    $summaryBytes = [int64](($summaryFiles | Measure-Object -Property bytes -Sum).Sum)
    Info ("Release package size summary: files={0}, bytes={1:n0}, gib={2:n2}" -f $summaryFiles.Count, $summaryBytes, ($summaryBytes / 1GB))
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
        Copy-ReleaseDirectoryTree -SourceDirectory $frontendDistSource -DestinationDirectory (Join-Path $frontendRepoTarget 'dist-intruoyi-test')
    }
}

function Copy-ReleaseDirectoryTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDirectory,
        [Parameter(Mandatory = $true)]
        [string]$DestinationDirectory
    )

    if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
        Fail "Release directory copy source missing: $SourceDirectory"
    }
    Require-Command 'robocopy'

    if (Test-Path -LiteralPath $DestinationDirectory) {
        Remove-Item -LiteralPath $DestinationDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null

    $robocopyArgs = @(
        $SourceDirectory,
        $DestinationDirectory,
        '/E',
        '/MT:32',
        '/NFL',
        '/NDL',
        '/NJH',
        '/NJS',
        '/NP',
        '/R:2',
        '/W:1'
    )
    Info ("Run: robocopy {0} {1} /E /MT:32 /NFL /NDL /NJH /NJS /NP /R:2 /W:1" -f $SourceDirectory, $DestinationDirectory)
    & robocopy @robocopyArgs | Out-Null
    $robocopyExitCode = $LASTEXITCODE
    if ($robocopyExitCode -ge 8) {
        Fail "Release directory copy failed with robocopy exit code $robocopyExitCode`: $SourceDirectory -> $DestinationDirectory"
    }
    if (-not (Test-Path -LiteralPath $DestinationDirectory -PathType Container)) {
        Fail "Release directory copy destination missing after robocopy: $DestinationDirectory"
    }
    $sourceFiles = @(Get-ChildItem -LiteralPath $SourceDirectory -Recurse -File -Force)
    $destinationFiles = @(Get-ChildItem -LiteralPath $DestinationDirectory -Recurse -File -Force)
    $sourceBytes = [int64](($sourceFiles | Measure-Object -Property Length -Sum).Sum)
    $destinationBytes = [int64](($destinationFiles | Measure-Object -Property Length -Sum).Sum)
    if ($sourceFiles.Count -ne $destinationFiles.Count -or $sourceBytes -ne $destinationBytes) {
        Fail (
            "Release directory copy incomplete: source files=$($sourceFiles.Count), bytes=$sourceBytes; " +
            "destination files=$($destinationFiles.Count), bytes=$destinationBytes"
        )
    }
    Info ("Release directory copy summary: sourceFiles={0}, destinationFiles={1}, bytes={2:n0}, gib={3:n2}" -f $sourceFiles.Count, $destinationFiles.Count, $sourceBytes, ($sourceBytes / 1GB))
}

function Remove-ReleaseDockerBuildContextFromPackage {
    foreach ($path in @($localTempRoot, $releaseDir, $dockerBuildContextRoot)) {
        if ([string]::IsNullOrWhiteSpace($path) -or -not [System.IO.Path]::IsPathRooted($path)) {
            throw 'Release Docker build context cleanup requires absolute, non-empty paths'
        }
    }
    $temporaryPath = [System.IO.Path]::GetFullPath($localTempRoot).TrimEnd('\')
    $packagePath = [System.IO.Path]::GetFullPath($releaseDir).TrimEnd('\')
    $contextPath = [System.IO.Path]::GetFullPath($dockerBuildContextRoot).TrimEnd('\')
    if ([string]::IsNullOrWhiteSpace($packageDirectoryName) -or
        [System.IO.Path]::GetFileName($packagePath) -ne $packageDirectoryName -or
        [System.IO.Path]::GetDirectoryName($packagePath) -ne $temporaryPath -or
        $contextPath -ne [System.IO.Path]::Combine($packagePath, 'docker-build-context')) {
        throw "Release Docker build context cleanup target is outside the expected package: $contextPath"
    }
    # Windows PowerShell 5.1 uses .NET Framework: unprefixed recursive Delete
    # reports DirectoryNotFoundException for existing descendants beyond MAX_PATH.
    $extendedPath = if ($contextPath.StartsWith('\\')) {
        '\\?\UNC\' + $contextPath.Substring(2)
    } else {
        '\\?\' + $contextPath
    }
    try {
        try {
            $attributes = [System.IO.File]::GetAttributes($extendedPath)
        } catch [System.IO.FileNotFoundException] {
            return
        } catch [System.IO.DirectoryNotFoundException] {
            return
        }
        if (-not ($attributes -band [System.IO.FileAttributes]::Directory)) {
            throw "Cleanup target is not a directory: $contextPath"
        }
        # A junction in the target or its ancestors could redirect a valid text
        # path outside the package. Reject it before any recursive deletion.
        $ancestor = $contextPath
        while ($ancestor) {
            if ([System.IO.File]::GetAttributes($ancestor) -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Cleanup path contains a reparse point: $ancestor"
            }
            $ancestor = [System.IO.Path]::GetDirectoryName($ancestor)
        }
        Info 'Removing Docker build context from final release package'
        [System.IO.Directory]::Delete($extendedPath, $true)
        if ([System.IO.Directory]::Exists($extendedPath)) {
            throw "Release package still contains docker-build-context: $contextPath"
        }
    } catch {
        throw "Release Docker build context cleanup failed: $($_.Exception.Message)"
    }
}

function Copy-ReleasePackageDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDirectory,
        [Parameter(Mandatory = $true)][string]$DestinationDirectory
    )
    if (-not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
        Fail "Release package copy source missing: $SourceDirectory"
    }
    Require-Command 'robocopy'
    New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
    $robocopyArgs = @(
        $SourceDirectory, $DestinationDirectory,
        '/E', '/PURGE', '/Z', '/MT:16', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:3', '/W:5'
    )
    Info ("Run: robocopy {0} {1} /E /PURGE /Z /MT:16 /NFL /NDL /NJH /NJS /NP /R:3 /W:5" -f $SourceDirectory, $DestinationDirectory)
    & robocopy @robocopyArgs | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Fail "robocopy failed with exit code $LASTEXITCODE"
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

function New-SshArgumentListWithInput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    return (Get-SshCommonOptions) + @(
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
        [string]$WorkingDirectory = $null,
        [int]$TimeoutSeconds = 0
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
        $startProcessParameters = @{
            FilePath = $effectiveFilePath
            ArgumentList = $effectiveArguments
            WorkingDirectory = $effectiveWorkingDirectory
            RedirectStandardOutput = $stdoutPath
            RedirectStandardError = $stderrPath
            NoNewWindow = $true
            PassThru = $true
        }
        if ($TimeoutSeconds -le 0) {
            $startProcessParameters['Wait'] = $true
        }

        $process = Start-Process @startProcessParameters
        $null = $process.Handle
        $timedOut = $false
        if ($TimeoutSeconds -gt 0) {
            if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
                $timedOut = $true
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                $process.WaitForExit()
            } else {
                $process.WaitForExit()
            }
        }
        $process.Refresh()
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        $stdout = if (Test-Path $stdoutPath) { [System.IO.File]::ReadAllText($stdoutPath, $utf8NoBom) } else { '' }
        $stderr = if (Test-Path $stderrPath) { [System.IO.File]::ReadAllText($stderrPath, $utf8NoBom) } else { '' }
        if ($timedOut) {
            $timeoutMessage = "Process timed out after $TimeoutSeconds seconds."
            if ($stderr) {
                $stderr = $stderr.TrimEnd() + "`n" + $timeoutMessage + "`n"
            } else {
                $stderr = $timeoutMessage + "`n"
            }
        }
        $exitCode = if ($timedOut) { -1 } else { $process.ExitCode }
        return @{
            ExitCode = $exitCode
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

function Resolve-MaintenanceRepoRelativeFilePath {
    param(
        [AllowNull()]
        [string]$PathValue,
        [Parameter(Mandatory = $true)]
        [string]$ArgumentName
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        Fail "Missing $ArgumentName; release package modes require an explicit file path."
    }

    $trimmedPath = $PathValue.Trim()
    if ([System.IO.Path]::IsPathRooted($trimmedPath)) {
        $candidatePath = $trimmedPath
    } else {
        $maintenanceRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
        $candidatePath = Join-Path $maintenanceRoot $trimmedPath
    }

    $fullPath = [System.IO.Path]::GetFullPath($candidatePath)
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

    $reportRoot = $packageFullPath
    if ($Mode -eq 'deploy-release') {
        $reportRoot = [IO.Path]::GetFullPath($deployControlLocalRoot)
        if ($reportRoot -eq $packageFullPath -or $reportRoot.StartsWith($packageFullPath.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            Fail 'PACKAGE_CONTROL_PATH_INVALID: deployment reports must be outside the immutable package'
        }
    }
    $reportDirectory = Join-Path $reportRoot 'smart-release-report'
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
    $releaseScriptRoot = $maintenanceReleaseScriptRoot

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

function Invoke-CheckedMavenCommand {
    param(
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = $null
    )

    $requiredJdkOption = '-Djdk.net.URLClassPath.disableClassPathURLCheck=true'
    $previousJdkJavaOptions = $env:JDK_JAVA_OPTIONS
    try {
        $currentJdkJavaOptions = if ($null -eq $previousJdkJavaOptions) { '' } else { $previousJdkJavaOptions.Trim() }
        if ([string]::IsNullOrWhiteSpace($currentJdkJavaOptions)) {
            $env:JDK_JAVA_OPTIONS = $requiredJdkOption
        } elseif ($currentJdkJavaOptions -notmatch [regex]::Escape($requiredJdkOption)) {
            $env:JDK_JAVA_OPTIONS = "$currentJdkJavaOptions $requiredJdkOption"
        }
        Invoke-CheckedCommand -FilePath 'mvn' -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory
    } finally {
        $env:JDK_JAVA_OPTIONS = $previousJdkJavaOptions
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

function Assert-FrontendBuildPreflight {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FrontendDir
    )

    foreach ($requiredInput in @('package.json', 'pnpm-lock.yaml')) {
        $inputPath = Join-Path $FrontendDir $requiredInput
        if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
            Fail "Frontend build input missing before backend build: $inputPath"
        }
    }
    Require-Command 'node'
    Require-Command 'pnpm'
    foreach ($binaryName in @('cross-env.cmd', 'vite.cmd', 'vue-tsc.cmd')) {
        $binaryPath = Join-Path $FrontendDir (Join-Path 'node_modules\.bin' $binaryName)
        if (-not (Test-Path -LiteralPath $binaryPath -PathType Leaf)) {
            Fail "Frontend build dependency binary missing before backend build: $binaryPath"
        }
    }
    $ignoredBuildsResult = Invoke-ProcessCapture `
        -FilePath 'pnpm' `
        -ArgumentList @('ignored-builds') `
        -WorkingDirectory $FrontendDir
    if ($ignoredBuildsResult.ExitCode -ne 0) {
        Fail "Frontend dependency ignored-builds check failed with exit code $($ignoredBuildsResult.ExitCode)"
    }
    $ignoredBuildLines = @(
        (($ignoredBuildsResult.StdOut + "`n" + $ignoredBuildsResult.StdErr) -split "`r?`n") |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
    )
    $ignoredBuildsIsNone = ($ignoredBuildLines.Count -eq 1 -and $ignoredBuildLines[0] -eq 'None') -or
        ($ignoredBuildLines.Count -eq 1 -and $ignoredBuildLines[0] -eq 'Automatically ignored builds during installation: None') -or
        ($ignoredBuildLines.Count -eq 2 -and
            $ignoredBuildLines[0] -eq 'Automatically ignored builds during installation:' -and
            $ignoredBuildLines[1] -eq 'None')
    if (-not $ignoredBuildsIsNone) {
        Fail "Frontend dependency ignored-builds must report exactly None before backend build: $($ignoredBuildLines -join ' | ')"
    }
    Info "Frontend dependency preflight passed: $FrontendDir"
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
        [string]$PackageTag,
        [Parameter(Mandatory = $true)]
        [array]$SourceRepos
    )

    $releasePackageLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(21457, 24067, 21253)
    $componentScopeLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(32452, 20214, 33539, 22260)
    $fullWidthColon = ConvertTo-ReleaseUnicodeText -CodePoints @(65306)
    $commitChanges = New-ReleaseSourceCommitChangeEntries -SourceRepos $SourceRepos
    $items = @(
        ('{0}{1}{2}' -f $releasePackageLabel, $fullWidthColon, $PackageTag)
        ('{0}{1}{2}' -f $componentScopeLabel, $fullWidthColon, $Component)
    )
    $items += @($commitChanges.items)

    return [ordered]@{
        summary = (@($commitChanges.subjects) -join ' | ')
        component = $Component
        items = @($items)
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
        publishScope = $PublishScope
        changeSet = New-ReleaseChangeSetManifest -PackageTag $PackageTag -SourceRepos $SourceRepos
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

function Assert-BackendRuntimeBaseTarIntegrity {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Config
    )

    $actualTarSha256 = ConvertTo-ReleaseFileSha256Hex -Path $config.TarPath
    if ($actualTarSha256 -ne $config.TarSha256) {
        Fail "Backend runtime base tar sha256 mismatch: expected $($config.TarSha256), got $actualTarSha256 ($($config.TarPath))"
    }
}

function Assert-BackendRuntimeBaseImageAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Config
    )

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

function Get-DockerImageIdentity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ImageReference
    )

    $inspectResult = Invoke-ProcessCapture -FilePath 'docker' -ArgumentList @(
        'image', 'inspect', $ImageReference
    )
    if ($inspectResult.ExitCode -ne 0) {
        $safeOutput = Protect-ReleaseSensitiveText (($inspectResult.StdOut + "`n" + $inspectResult.StdErr).Trim())
        Fail "Cannot inspect Docker image identity: $ImageReference`n$safeOutput"
    }
    $json = ([string]$inspectResult.StdOut).Trim()
    if ([string]::IsNullOrWhiteSpace($json)) {
        Fail "Docker image inspect returned blank output: $ImageReference"
    }
    try {
        $parsedImages = $json | ConvertFrom-Json
    } catch {
        Fail "Docker image inspect returned invalid JSON for ${ImageReference}: $($_.Exception.Message)"
    }
    $images = @($parsedImages)
    if ($images.Count -ne 1) {
        Fail "Docker image inspect must return exactly one image for ${ImageReference}: $($images.Count)"
    }
    $image = $images[0]
    $imageId = ([string]$image.Id).Trim().ToLowerInvariant()
    if ($imageId -notmatch '^sha256:[0-9a-f]{64}$') {
        Fail "Docker image inspect returned invalid image id for ${ImageReference}: $imageId"
    }
    return [ordered]@{
        reference = $ImageReference
        id = $imageId
        sizeBytes = [int64]$image.Size
        repoDigests = @($image.RepoDigests | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Sort-Object)
    }
}

function New-DockerBuildEvidenceSpec {
    $components = @()
    if ($publishBackend) {
        if ($null -eq $backendRuntimeBaseConfig) {
            Fail 'Backend runtime base config is required for Docker build evidence.'
        }
        $backendBaseIdentity = Get-DockerImageIdentity -ImageReference $backendRuntimeBaseConfig.Image
        if ($backendBaseIdentity.id -ne $backendRuntimeBaseConfig.Digest) {
            Fail "Backend base image changed before Docker build evidence: $($backendBaseIdentity.id) != $($backendRuntimeBaseConfig.Digest)"
        }
        $components += [ordered]@{
            name = 'backend'
            dockerfile = $backendDockerfile
            contextRoot = $dockerBuildContextRoot
            buildArgs = [ordered]@{
                BACKEND_RUNTIME_BASE_IMAGE = $backendRuntimeBaseConfig.Image
            }
            baseImage = [ordered]@{
                reference = $backendRuntimeBaseConfig.Image
                digest = $backendBaseIdentity.id
            }
            imageReference = "intruoyi-backend:$packageDirectoryName"
        }
    }
    if ($publishFrontend) {
        $frontendBaseIdentity = Get-DockerImageIdentity -ImageReference $frontendRuntimeBaseImage
        $components += [ordered]@{
            name = 'frontend'
            dockerfile = $frontendDockerfile
            contextRoot = $dockerBuildContextRoot
            buildArgs = [ordered]@{}
            baseImage = [ordered]@{
                reference = $frontendRuntimeBaseImage
                digest = $frontendBaseIdentity.id
            }
            imageReference = "intruoyi-frontend:$packageDirectoryName"
        }
    }
    if ($components.Count -eq 0) {
        Fail 'Docker build evidence requires at least one application image component.'
    }
    return [ordered]@{
        schemaVersion = 'release-docker-build-spec/v1'
        components = @($components)
    }
}

function Write-DockerBuildInputEvidence {
    $runner = Join-Path $maintenanceReleaseScriptRoot 'release_docker_build_evidence.py'
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
        Fail "Docker build evidence runner missing: $runner"
    }
    $script:DockerBuildEvidenceRoot = Join-Path $localTempRoot "docker-build-evidence-$packageDirectoryName"
    if (Test-Path -LiteralPath $script:DockerBuildEvidenceRoot) {
        Remove-Item -LiteralPath $script:DockerBuildEvidenceRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $script:DockerBuildEvidenceRoot | Out-Null
    $script:DockerBuildEvidenceRunner = $runner
    $script:DockerBuildSpecPath = Join-Path $script:DockerBuildEvidenceRoot 'docker-build-spec-before.json'
    $script:DockerBuildInputEvidencePath = Join-Path $script:DockerBuildEvidenceRoot 'docker-build-input-evidence.json'
    [System.IO.File]::WriteAllText(
        $script:DockerBuildSpecPath,
        ((New-DockerBuildEvidenceSpec) | ConvertTo-Json -Depth 12),
        [System.Text.UTF8Encoding]::new($false)
    )
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8', $script:DockerBuildEvidenceRunner,
        'capture', '--spec', $script:DockerBuildSpecPath,
        '--output', $script:DockerBuildInputEvidencePath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
}

function Assert-DockerBuildInputsUnchanged {
    $script:DockerBuildAfterSpecPath = Join-Path $script:DockerBuildEvidenceRoot 'docker-build-spec-after.json'
    [System.IO.File]::WriteAllText(
        $script:DockerBuildAfterSpecPath,
        ((New-DockerBuildEvidenceSpec) | ConvertTo-Json -Depth 12),
        [System.Text.UTF8Encoding]::new($false)
    )
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8', $script:DockerBuildEvidenceRunner,
        'verify-input', '--spec', $script:DockerBuildAfterSpecPath,
        '--evidence', $script:DockerBuildInputEvidencePath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
}

function Write-FinalDockerBuildEvidence {
    $actualImages = [ordered]@{}
    if ($publishBackend) {
        $actualImages['backend'] = Get-DockerImageIdentity -ImageReference "intruoyi-backend:$packageDirectoryName"
    }
    if ($publishFrontend) {
        $actualImages['frontend'] = Get-DockerImageIdentity -ImageReference "intruoyi-frontend:$packageDirectoryName"
    }
    $actualImagesPath = Join-Path $script:DockerBuildEvidenceRoot 'actual-images.json'
    [System.IO.File]::WriteAllText(
        $actualImagesPath,
        ($actualImages | ConvertTo-Json -Depth 8),
        [System.Text.UTF8Encoding]::new($false)
    )
    $manifestDirectory = Join-Path $releaseDir 'manifest'
    New-Item -ItemType Directory -Force -Path $manifestDirectory | Out-Null
    $finalEvidencePath = Join-Path $releaseDir 'manifest\docker-build-evidence.json'
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8', $script:DockerBuildEvidenceRunner,
        'finalize', '--spec', $script:DockerBuildAfterSpecPath,
        '--evidence', $script:DockerBuildInputEvidencePath,
        '--actual-images', $actualImagesPath,
        '--output', $finalEvidencePath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
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
    $displayCommand = Protect-ReleaseSensitiveText $normalizedCommand
    Info ("Run: ssh {0}" -f ((New-SshArgumentList -Command $displayCommand) -join ' '))
    $result = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (New-SshArgumentList -Command $normalizedCommand)
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $text = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    $safeText = Protect-ReleaseSensitiveText $text
    if ($safeText) {
        Write-Host $safeText
    }
    if ($result.ExitCode -ne 0) {
        throw "Command failed with exit code $($result.ExitCode): ssh`n$safeText"
    }
}

function Invoke-SshCommandWithInput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [AllowNull()]
        [string]$StandardInput = ''
    )

    $normalizedCommand = $Command -replace "`r`n", "`n" -replace "`r", "`n"
    $normalizedInput = if ($null -ne $StandardInput) {
        $StandardInput -replace "`r`n", "`n" -replace "`r", "`n"
    } else {
        ''
    }
    $displayCommand = Protect-ReleaseSensitiveText $normalizedCommand
    Info ("Run: ssh {0} <stdin:{1} chars>" -f ((New-SshArgumentListWithInput -Command $displayCommand) -join ' '), $normalizedInput.Length)
    $result = Invoke-ProcessCaptureWithInput -FilePath 'ssh' -ArgumentList (New-SshArgumentListWithInput -Command $normalizedCommand) -StandardInput $normalizedInput
    $stdOut = if ($null -ne $result.StdOut) { $result.StdOut } else { '' }
    $stdErr = if ($null -ne $result.StdErr) { $result.StdErr } else { '' }
    $text = Remove-SshNoise (($stdOut + "`n" + $stdErr).Trim())
    $safeText = Protect-ReleaseSensitiveText $text
    if ($safeText) {
        Write-Host $safeText
    }
    if ($result.ExitCode -ne 0) {
        throw "Command failed with exit code $($result.ExitCode): ssh`n$safeText"
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
        $safeCommand = Protect-ReleaseSensitiveText $normalizedCommand
        $safeText = Protect-ReleaseSensitiveText $text
        throw "SSH command failed ($exitCode): $safeCommand`n$safeText"
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

function Resolve-TargetEdhrS3Endpoint {
    param(
        [AllowNull()]
        [string]$Endpoint,
        [Parameter(Mandatory = $true)]
        [string]$TargetServerHost,
        [bool]$TargetSpecific = $false
    )

    if ([string]::IsNullOrWhiteSpace($Endpoint)) {
        return ''
    }
    $trimmedEndpoint = $Endpoint.Trim()
    if ($TargetSpecific -or [string]::IsNullOrWhiteSpace($TargetServerHost)) {
        return $trimmedEndpoint
    }

    $uri = $null
    if ([System.Uri]::TryCreate($trimmedEndpoint, [System.UriKind]::Absolute, [ref]$uri)) {
        $builder = [System.UriBuilder]::new($uri)
        if ($builder.Host -match '^(\d{1,3}\.){3}\d{1,3}$') {
            $builder.Host = $TargetServerHost
            return $builder.Uri.AbsoluteUri.TrimEnd('/')
        }
    }
    return $trimmedEndpoint
}

function Resolve-TargetPublishRuntimeValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [AllowNull()]
        [string]$TargetServerHost = '',
        [AllowNull()]
        [string]$CurrentValue,
        [AllowNull()]
        [string]$HardcodedValue = ''
    )

    $normalizedTarget = $TargetEnvironment.Trim().ToLowerInvariant()
    $targetSpecificName = Get-TargetSpecificEdhrEnvName -TargetEnvironment $TargetEnvironment -Name $Name
    $targetSpecificValue = if ([string]::IsNullOrWhiteSpace($targetSpecificName)) {
        ''
    } else {
        Get-PublishRuntimeEnvironmentValue -Name $targetSpecificName
    }
    $genericEnvironmentValue = Get-PublishRuntimeEnvironmentValue -Name $Name
    $candidates = @(
        @{ Value = $targetSpecificValue; TargetSpecific = $true },
        @{ Value = $CurrentValue; TargetSpecific = $false },
        @{ Value = $genericEnvironmentValue; TargetSpecific = $false },
        @{ Value = $HardcodedValue; TargetSpecific = $false }
    )

    foreach ($candidate in $candidates) {
        $candidateValue = [string]$candidate.Value
        if ([string]::IsNullOrWhiteSpace($candidateValue)) {
            continue
        }
        $trimmedValue = $candidateValue.Trim()
        if ($Name -eq 'EDHR_S3_ENDPOINT') {
            return Resolve-TargetEdhrS3Endpoint `
                -Endpoint $trimmedValue `
                -TargetServerHost $TargetServerHost `
                -TargetSpecific ([bool]$candidate.TargetSpecific)
        }
        return $trimmedValue
    }
    return ''
}

function Assert-ReleaseRuntimeEnvTargetBoundary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [string]$TargetServerHost,
        [AllowNull()]
        [string]$EdhrS3Endpoint
    )

    if ([string]::IsNullOrWhiteSpace($EdhrS3Endpoint)) {
        return
    }
    $normalizedTarget = $TargetEnvironment.Trim().ToLowerInvariant()
    if ($normalizedTarget -eq 'test' -and $EdhrS3Endpoint -match '172\.30\.30\.57|172\.30\.30\.59') {
        Fail 'EDHR_S3_ENDPOINT for test runtime env must point to 172.30.30.58; actual endpoint points outside test host.'
    }
    if ($normalizedTarget -eq 'test' -and $TargetServerHost -eq '172.30.30.58' -and $EdhrS3Endpoint -match '172\.30\.30\.\d+' -and $EdhrS3Endpoint -notmatch [regex]::Escape($TargetServerHost)) {
        Fail 'EDHR_S3_ENDPOINT for test runtime env must point to 172.30.30.58; actual endpoint points outside test host.'
    }
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

    $script:EdhrS3Endpoint = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ENDPOINT' -TargetEnvironment $TargetEnvironment -TargetServerHost $TargetServerHost -CurrentValue $script:EdhrS3Endpoint
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
    $resolvedEdhrS3Endpoint = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ENDPOINT' -TargetEnvironment $TargetEnvironment -TargetServerHost $TargetServerHost -CurrentValue $EdhrS3Endpoint
    $resolvedEdhrS3Bucket = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_BUCKET' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3Bucket
    $resolvedEdhrS3Region = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REGION' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3Region
    $resolvedEdhrS3AccessKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_ACCESS_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3AccessKey
    $resolvedEdhrS3SecretKey = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_SECRET_KEY' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3SecretKey
    $resolvedEdhrS3RetentionMode = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETENTION_MODE' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RetentionMode
    $resolvedEdhrS3RetainUntilDays = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_RETAIN_UNTIL_DAYS' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RetainUntilDays
    $resolvedEdhrS3RequireLegalHold = Resolve-TargetPublishRuntimeValue -Name 'EDHR_S3_REQUIRE_LEGAL_HOLD' -TargetEnvironment $TargetEnvironment -CurrentValue $EdhrS3RequireLegalHold
    Assert-ReleaseRuntimeEnvTargetBoundary `
        -TargetEnvironment $TargetEnvironment `
        -TargetServerHost $TargetServerHost `
        -EdhrS3Endpoint $resolvedEdhrS3Endpoint

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
EDHR_S3_ENDPOINT=$resolvedEdhrS3Endpoint
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
    Info 'Skipping runtime-env secret package files; target runtime secrets are resolved from target .env or operator environment during deploy.'
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
    $timeoutSeconds = 120
    $result = Invoke-ProcessCapture -FilePath 'python' -ArgumentList @('-X', 'utf8', $verifier) -WorkingDirectory $BackendRepo -TimeoutSeconds $timeoutSeconds
    $output = Remove-SshNoise ((($result.StdOut + "`n" + $result.StdErr)).Trim())
    if ($output) {
        Write-Host $output
    }
    if ($result.ExitCode -eq -1) {
        Fail "eDHR protected storage verifier timed out after $timeoutSeconds seconds."
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

function Protect-ReleaseSensitiveText {
    param(
        [AllowNull()]
        [string]$Value,
        [string[]]$SensitiveValues = @()
    )

    if ($null -eq $Value) {
        return ''
    }

    $text = $Value
    # Lease ownership credentials must stay intact in dispatched SQL, but must
    # never enter the display command, exceptions, or persisted error evidence.
    foreach($secret in (@($script:ReleaseOperationLeaseToken)+@($SensitiveValues))) {
        if(-not [string]::IsNullOrEmpty([string]$secret)) {
            $text=$text.Replace(([string]$secret).Replace("'","''"),'<redacted>')
            $text=$text.Replace([string]$secret,'<redacted>')
        }
    }
    $text=[regex]::Replace($text,'(?i)(LOCK_(?:ACQUIRED|UPGRADED):)[A-Za-z0-9_-]+','$1<redacted>')
    $patterns = @(
        '(?i)(MYSQL_PWD=)[^\s''"`;\r\n]+'
        '(?i)(?<!-)(-p)[^\s''"`;\r\n]+'
        '(?i)((?:password|secret|access[_-]?key|private[_-]?key|hmac[_-]?secret|base64[_-]?key)\s*[=:]\s*)[^\s,;''"`\r\n]+'
    )
    foreach ($pattern in $patterns) {
        $text = [System.Text.RegularExpressions.Regex]::Replace($text, $pattern, '$1<redacted>')
    }
    return $text
}

function ConvertTo-ReleaseErrorMessage {
    param(
        [AllowNull()]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }

    $text = ($Value -replace "`r`n", "`n" -replace "`r", "`n").Trim()
    $text = Protect-ReleaseSensitiveText $text
    if ($text.Length -gt $script:ReleaseErrorMessageMaxLength) {
        $suffix = '...<truncated>'
        $text = $text.Substring(0, $script:ReleaseErrorMessageMaxLength - $suffix.Length) + $suffix
    }
    return $text
}

function ConvertTo-ReleaseErrorBase64 {
    param(
        [AllowNull()]
        [string]$Value
    )

    $text = ConvertTo-ReleaseErrorMessage -Value $Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return ''
    }
    return [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($text))
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

function Get-RemoteFileSize {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RemotePath
    )

    $sizeResult = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (New-SshArgumentList -Command "if [ -f '$RemotePath' ]; then stat -c '%s' '$RemotePath'; else echo MISSING; exit 42; fi")
    if ($sizeResult.ExitCode -ne 0) {
        $sizeOutput = (($sizeResult.StdOut + "`n" + $sizeResult.StdErr).Trim())
        Fail "Unable to read remote file size for ${RemotePath}: $sizeOutput"
    }
    $trimmed = ([string]$sizeResult.StdOut).Trim()
    $remoteSize = 0L
    if (-not [Int64]::TryParse($trimmed, [ref]$remoteSize)) {
        Fail "Unable to parse remote file size for ${RemotePath}: $trimmed"
    }
    return $remoteSize
}

function Assert-RemoteFileSize {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RemotePath,
        [Parameter(Mandatory = $true)]
        [Int64]$ExpectedBytes
    )

    $actualBytes = Get-RemoteFileSize -RemotePath $RemotePath
    if ($actualBytes -ne $ExpectedBytes) {
        Fail "Remote file size mismatch: $RemotePath expected=$ExpectedBytes actual=$actualBytes"
    }
    Info "Remote file size verified: $RemotePath bytes=$actualBytes"
}

function Copy-LargeFileToServerInChunks {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LocalPath,
        [Parameter(Mandatory = $true)]
        [string]$RemotePath,
        [Int64]$ChunkBytes = 134217728
    )

    if (-not (Test-Path -LiteralPath $LocalPath -PathType Leaf)) {
        Fail "Large file source missing: $LocalPath"
    }
    if ($ChunkBytes -le 0) {
        Fail "ChunkBytes must be positive: $ChunkBytes"
    }

    $sourceItem = Get-Item -LiteralPath $LocalPath
    $expectedBytes = [Int64]$sourceItem.Length
    $chunkRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("publish-int-ruoyi-chunks-" + [System.Guid]::NewGuid().ToString("N"))
    $remoteChunkDir = "$RemotePath.chunks.$([System.Guid]::NewGuid().ToString('N'))"
    try {
        New-Item -ItemType Directory -Force -Path $chunkRoot | Out-Null
        Invoke-SshCommand "rm -f '$RemotePath' && rm -rf '$remoteChunkDir' && mkdir -p '$remoteChunkDir'"

        $bufferSize = [int][Math]::Min([Int64]4194304, $ChunkBytes)
        $buffer = New-Object byte[] $bufferSize
        $chunkIndex = 0
        $inputStream = [System.IO.File]::Open($LocalPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        try {
            while ($true) {
                $remaining = [Int64]$ChunkBytes
                $chunkPath = Join-Path $chunkRoot ("chunk-{0:D6}.part" -f $chunkIndex)
                $outputStream = [System.IO.File]::Open($chunkPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
                $written = 0L
                try {
                    while ($remaining -gt 0) {
                        $readSize = [int][Math]::Min([Int64]$buffer.Length, $remaining)
                        $read = $inputStream.Read($buffer, 0, $readSize)
                        if ($read -le 0) {
                            break
                        }
                        $outputStream.Write($buffer, 0, $read)
                        $remaining -= [Int64]$read
                        $written += [Int64]$read
                    }
                } finally {
                    $outputStream.Close()
                }

                if ($written -eq 0) {
                    Remove-Item -LiteralPath $chunkPath -Force
                    break
                }

                $remoteChunkPath = "$remoteChunkDir/$(Split-Path -Leaf $chunkPath)"
                Info "Uploading large file chunk $chunkIndex to the $PublishTargetName server ($written bytes)"
                Invoke-CheckedCommand -FilePath 'scp' -ArgumentList (New-ScpArgumentList -LocalPath $chunkPath -RemotePath $remoteChunkPath)
                Assert-RemoteFileSize -RemotePath $remoteChunkPath -ExpectedBytes $written
                Remove-Item -LiteralPath $chunkPath -Force
                $chunkIndex++
            }
        } finally {
            $inputStream.Close()
        }

        if ($chunkIndex -eq 0 -and $expectedBytes -ne 0) {
            Fail "Large file chunking produced no chunks: $LocalPath"
        }

        Invoke-SshCommand "cat '$remoteChunkDir'/*.part > '$RemotePath' && rm -rf '$remoteChunkDir'"
        Assert-RemoteFileSize -RemotePath $RemotePath -ExpectedBytes $expectedBytes
    } finally {
        if (Test-Path -LiteralPath $chunkRoot) {
            Remove-Item -LiteralPath $chunkRoot -Recurse -Force
        }
        try {
            Invoke-SshCommand "rm -rf '$remoteChunkDir'"
        } catch {
        }
    }
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

function ConvertFrom-HexUtf8 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Hex,
        [string]$Purpose = 'UTF-8 hex text'
    )

    $normalized = $Hex.Trim()
    if ($normalized.Length -eq 0 -or ($normalized.Length % 2) -ne 0) {
        Fail "$Purpose is not valid even-length hex"
    }
    try {
        $bytes = for ($i = 0; $i -lt $normalized.Length; $i += 2) {
            [Convert]::ToByte($normalized.Substring($i, 2), 16)
        }
        return [System.Text.Encoding]::UTF8.GetString([byte[]]$bytes)
    } catch {
        Fail "$Purpose is not valid UTF-8 hex: $($_.Exception.Message)"
    }
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
SELECT CONCAT(config_id, CHAR(9), HEX(path))
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
    $decodedPath = ConvertFrom-HexUtf8 -Hex $parts[1] -Purpose 'SHOWROOM_FILE_CONTENT_SMOKE_FAILED sample image path'
    return @{
        ConfigId = $parts[0].Trim()
        Path = $decodedPath
    }
}

function Assert-RemoteShowroomSmokeImageContent {
    $asset = Get-RemoteShowroomSmokeImageAsset
    $encodedAssetPath = (($asset.Path -split '/') | ForEach-Object { [uri]::EscapeDataString([string]$_) }) -join '/'
    $smokeImageUrl = "http://${ServerHost}:$FrontendPort/admin-api/infra/file/$($asset.ConfigId)/get/$encodedAssetPath"
    # The production backend can report health before the MinIO-backed file proxy is fully warm.
    Wait-HttpContentTypeOk -Url $smokeImageUrl -ExpectedContentType 'image/' -TimeoutSeconds 420
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
data_disk_source=`$(findmnt -n -o SOURCE --target '$RemoteDataDiskMount')
if [ "`$data_disk_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteDataDiskMount to be mounted from $RemoteDataDiskDevice, got: `$data_disk_source" >&2
  exit 1
fi
test -d '$RemoteDataRoot'
test -d '$RemoteReleaseRoot'
test -d '$RemoteAppDir'
release_source=`$(df -P '$RemoteReleaseRoot' | awk 'NR==2 {print `$1}')
if [ "`$release_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteReleaseRoot to be stored on $RemoteDataDiskDevice, got: `$release_source" >&2
  exit 1
fi
if [ -e '$RemoteAppDir/data' ] && [ ! -d '$RemoteAppDir/data' ]; then
  echo "Remote runtime data path exists but is not a directory: $RemoteAppDir/data" >&2
  exit 1
fi
test -d '$RemoteAppDir/data'
mountpoint -q '$RemoteAppDir/data'
data_dir_source=`$(df -P '$RemoteAppDir/data' | awk 'NR==2 {print `$1}')
if [ "`$data_dir_source" != '$RemoteDataDiskDevice' ]; then
  echo "Expected $RemoteAppDir/data to be stored on $RemoteDataDiskDevice, got: `$data_dir_source" >&2
  exit 1
fi
test -d '$RemoteAppDir/data/mysql'
test -d '$RemoteAppDir/data/redis'
test -d '$RemoteAppDir/data/backend-logs'
test -d '$RemoteAppDir/data/minio'
"@
    Invoke-SshCommand $command
}

function Read-NasReleaseConfig {
    $resolvedNasConfigPath = Resolve-MaintenanceRepoRelativeFilePath -PathValue $NasConfigPath -ArgumentName 'NasConfigPath'
    $text = [System.IO.File]::ReadAllText($resolvedNasConfigPath, [System.Text.UTF8Encoding]::new($false))
    try {
        $config = $text | ConvertFrom-Json
    } catch {
        Fail "NAS release config must be UTF-8 JSON: $resolvedNasConfigPath"
    }
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
        $stagingPath = Join-Path $targetRoot ('.' + $packageDirectoryName + '.staging-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
        try {
            Copy-ReleaseDirectoryTree -SourceDirectory $releaseDir -DestinationDirectory $stagingPath
            $null = Test-ReleasePackageIntegrity -PackagePath $stagingPath -ExpectedReleaseTag $PackageTag -ExpectedPackageDirectoryName $packageDirectoryName -EmitProgress
            if (Test-Path -LiteralPath $targetPath) {
                Fail "NAS release package appeared during staging: $NasReleaseRoot/$packageDirectoryName"
            }
            Move-Item -LiteralPath $stagingPath -Destination $targetPath
            Info "Release package uploaded to NAS: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        } catch {
            if (Test-Path -LiteralPath $stagingPath) {
                Remove-Item -LiteralPath $stagingPath -Recurse -Force
            }
            throw
        }
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
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
        New-Item -ItemType Directory -Force -Path $localTempRoot | Out-Null
        Copy-ReleasePackageDirectory -SourceDirectory $sourcePath -DestinationDirectory $releaseDir
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        $packageIntegrity = Test-ReleasePackageIntegrity -PackagePath $releaseDir -ExpectedReleaseTag $PackageTag
        Assert-ReleaseWorkflowPackageBinding -PackageIntegrity $packageIntegrity `
            -ExpectedPackageDigest $ExpectedPackageDigest -ExpectedManifestDigest $ExpectedManifestDigest
        if ($Environment -in @('prod', 'backup')) {
            $null = Test-ReleasePromotionAttestation `
                -PackagePath $releaseDir `
                -ExpectedReleaseTag $PackageTag `
                -TargetEnvironment $Environment `
                -TestOperationId $TestOperationId `
                -TestOperationEvidencePath $TestOperationEvidencePath
        }
        Info "Release package downloaded from NAS: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        return $packageIntegrity
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
    if ($Manifest.publishScope -ne 'app-release') {
        $blockedReasons.Add("release package publishScope=$($Manifest.publishScope) is not app-release")
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
        if ($TestResult -cne 'PASS') {
            Fail 'TestResult PASS is required when marking a release package as tested.'
        }
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        $packagePath = Get-NasReleasePackagePath -NasRoot $mountInfo.Root -PackageTag $PackageTag
        if (-not (Test-Path -LiteralPath $packagePath)) {
            $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
            Fail "NAS release package not found: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
        }
        $packageDirectoryName = ConvertTo-ReleasePackageDirectoryName -ReleaseTagValue $PackageTag
        $packageIntegrity = Test-ReleasePackageIntegrity -PackagePath $packagePath -ExpectedReleaseTag $PackageTag
        Assert-ReleaseWorkflowPackageBinding -PackageIntegrity $packageIntegrity `
            -ExpectedPackageDigest $ExpectedPackageDigest -ExpectedManifestDigest $ExpectedManifestDigest
        $null = Write-ReleaseTestedAttestation `
            -PackagePath $packagePath `
            -ExpectedReleaseTag $packageIntegrity.releaseTag `
            -TestOperationId $TestOperationId `
            -TestOperationEvidencePath $TestOperationEvidencePath `
            -TestResult $TestResult `
            -TestedBy $OperatorName `
            -TestConclusion $TestConclusion
        Info "Release package marked as tested: $NasReleaseRoot/$packageDirectoryName (releaseTag=$PackageTag)"
    } finally {
        Disconnect-NasReleaseShare -MountInfo $mountInfo
    }
}

function Read-ReleaseManifest {
    $manifestPath = Join-Path $releaseDir 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        Fail "manifest.json missing in release package: $manifestPath"
    }

    try {
        $manifestText = [System.IO.File]::ReadAllText($manifestPath, [System.Text.UTF8Encoding]::new($false))
        return $manifestText | ConvertFrom-Json
    } catch {
        Fail "manifest.json parse failed: $($_.Exception.Message)"
    }
}

function Resolve-DeployReleasePackageScope {
    $manifest = Read-ReleaseManifest
    $publishScope = ''
    if ($null -ne $manifest.publishScope) {
        $publishScope = ([string]$manifest.publishScope).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($publishScope)) {
        Fail 'manifest.json missing publishScope'
    }
    if ($publishScope -ne 'app-release') {
        Fail "Invalid release package publishScope: $publishScope"
    }
    return $publishScope
}

function Resolve-DeployReleasePackageOnlyOfficeIncluded {
    param([bool]$IncludeOnlyOfficeExplicit = $false)
    if ($IncludeOnlyOfficeExplicit) {
        Fail 'DEPLOY_ONLYOFFICE_OVERRIDE_FORBIDDEN: OnlyOffice selection is fixed by the complete package'
    }
    $manifest = Read-ReleaseManifest
    if ($null -eq $manifest.onlyOfficeIncluded) {
        Fail 'manifest.json missing onlyOfficeIncluded; rebuild the release package'
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
        Fail 'DEPLOY_COMPONENT_OVERRIDE_FORBIDDEN: component selection is fixed by the complete package'
    }

    $manifest = Read-ReleaseManifest
    $manifestComponent = ''
    if ($null -ne $manifest.component) {
        $manifestComponent = ([string]$manifest.component).Trim()
    }

    if ([string]::IsNullOrWhiteSpace($manifestComponent)) {
        Fail 'manifest.json missing component; rebuild the complete release package'
    }
    if ($manifestComponent -cnotin @('full', 'intruoyi')) {
        Fail "PACKAGE_COMPONENT_INVALID: $manifestComponent; rebuild the complete release package"
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
        $actualHash = ConvertTo-ReleaseFileSha256Hex -Path $dccSnapshotPath
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
        $hash = ConvertTo-ReleaseFileSha256Hex -Path $snapshotFile
        $snapshotRelativePath = $snapshotFile.Substring($releaseDir.Length).TrimStart('\', '/').Replace('\', '/')
        $totalBytes += [int64]$snapshotItem.Length
        [void]$inventoryFiles.Add([ordered]@{
            fileId = $row.fileId
            objectPath = $row.objectPath
            snapshotPath = $snapshotRelativePath
            sha256 = $hash
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
    $primaryError = $null
    $evidence = $null
    try {
        Start-ReleaseDeploymentPhase -Name 'history-connect' -Finalizing
        $mountInfo = Connect-NasReleaseShare -NasConfig $nasConfig
        Complete-ReleaseDeploymentPhase
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
            attemptId = $script:DeploymentOperation.attemptId
            packageDigest = $script:DeploymentOperation.binding.packageDigest
            manifestDigest = $script:DeploymentOperation.binding.manifestDigest
        } | ConvertTo-Json -Depth 4
        $historyDirectoryName = if ($HistoryEnvironment -eq 'backup') { 'backup-deployments' } else { 'prod-deployments' }
        $latestFileName = if ($HistoryEnvironment -eq 'backup') { 'backup-latest.json' } else { 'prod-latest.json' }
        $historyDir = Join-Path $packagePath $historyDirectoryName
        Start-ReleaseDeploymentPhase -Name 'history-file' -Finalizing
        New-Item -ItemType Directory -Force -Path $historyDir | Out-Null
        $historyFileName = $script:DeploymentOperation.attemptId + '.json'
        $historyFile = Join-Path $historyDir $historyFileName
        Write-ReleaseLocalAtomicEvidence -Path $historyFile -Text $record -CreateOnly
        Complete-ReleaseDeploymentPhase
        Start-ReleaseDeploymentPhase -Name 'history-latest' -Finalizing
        Write-ReleaseLocalAtomicEvidence -Path (Join-Path $packagePath $latestFileName) -Text $record
        Complete-ReleaseDeploymentPhase
        $evidence=[pscustomobject]@{status='verified';packageTag=$PackageTag;environment=$HistoryEnvironment;historyDirectory=$historyDirectoryName;historyFile=$historyFileName;latestFile=$latestFileName;sha256=(Get-DeploymentEvidenceDigest ([Text.Encoding]::UTF8.GetBytes($record)))}
        Info "$HistoryEnvironment release history recorded: $NasReleaseRoot/$historyPackageDirectoryName/$latestFileName"
    } catch {
        $primaryError=$_
    }
    try {
        Start-ReleaseDeploymentPhase -Name 'nas-disconnect' -Finalizing
        Disconnect-NasReleaseShare -MountInfo $mountInfo
        Complete-ReleaseDeploymentPhase
    } catch {
        if($null -eq $primaryError){throw}
        $script:DeploymentOperation.finalizationErrors+=Protect-ReleaseSensitiveText $_.Exception.Message
    }
    if($null -ne $primaryError){throw $primaryError}
    return $evidence
}

function Assert-NasReleaseDeploymentHistoryEvidence {
    param($History)
    if($History.status -cne 'verified' -or $History.environment -cnotin @('prod','backup') -or
       $History.historyFile -cnotmatch '^[0-9a-f]{64}\.json$' -or $History.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
       $History.historyDirectory -cne "$($History.environment)-deployments" -or $History.latestFile -cne "$($History.environment)-latest.json") {throw 'RELEASE_DEPLOYMENT_EVIDENCE_HISTORY_INVALID'}
    $mount=$null
    $primaryError=$null
    try {
        $mount=Connect-NasReleaseShare -NasConfig (Read-NasReleaseConfig)
        $root=Get-NasReleasePackagePath -NasRoot $mount.Root -PackageTag $History.packageTag
        foreach($path in @((Join-Path (Join-Path $root $History.historyDirectory) $History.historyFile),(Join-Path $root $History.latestFile))) {
            if((ConvertTo-ReleaseFileSha256Hex -Path $path) -cne $History.sha256){throw 'RELEASE_DEPLOYMENT_EVIDENCE_HISTORY_READBACK_MISMATCH'}
        }
    }catch{$primaryError=$_}
    try {Disconnect-NasReleaseShare -MountInfo $mount}
    catch {
        $secondary=Protect-ReleaseSensitiveText $_.Exception.Message
        if($null -eq $primaryError){throw "RELEASE_DEPLOYMENT_EVIDENCE_HISTORY_DISCONNECT_FAILED: $secondary"}
        $script:ReleaseHistoryFailureErrors+= $secondary
        Write-Host "[FAIL] History verification disconnect also failed: $secondary"
    }
    if($null -ne $primaryError){throw $primaryError}
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

function ConvertTo-ReleaseFileSha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Fail "Manifest v1 file hash input missing: $Path"
    }

    $stream = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::Read
    )
    try {
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $sha256.ComputeHash($stream)
        } finally {
            $sha256.Dispose()
        }
    } finally {
        $stream.Dispose()
    }

    return [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
}

function ConvertTo-ReleaseFileSha256Digest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    return 'sha256:' + (ConvertTo-ReleaseFileSha256Hex -Path $Path)
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
    $gitArguments = @('-c', 'i18n.logOutputEncoding=UTF-8', '-C', $RepoPath) + @($Arguments)
    $result = Invoke-ProcessCapture -FilePath 'git' -ArgumentList $gitArguments -WorkingDirectory $RepoPath
    if ($result.ExitCode -ne 0) {
        Fail "Manifest v1 requires git metadata for ${Purpose}: $RepoPath"
    }
    return ([string]$result.StdOut).Trim()
}

function Get-ReleaseSourceRepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathRole
    )

    switch ($PathRole) {
        'backend' { return $backendRepo }
        'admin-frontend' { return $frontendDir }
        'website' { return $websiteRepo }
        default { Fail "Unknown source repo path role for release change notes: $PathRole" }
    }
}

function New-ReleaseSourceCommitChangeEntries {
    param(
        [Parameter(Mandatory = $true)]
        [array]$SourceRepos
    )

    if ($SourceRepos.Count -eq 0) {
        Fail 'Missing source repositories for release change notes.'
    }

    $commitLabel = ConvertTo-ReleaseUnicodeText -CodePoints @(25552, 20132)
    $fullWidthColon = ConvertTo-ReleaseUnicodeText -CodePoints @(65306)
    $seenCommits = @{}
    $items = @()
    $subjects = @()

    foreach ($sourceRepo in $SourceRepos) {
        $commit = ([string]$sourceRepo.commit).Trim()
        if ($commit -notmatch '^[a-fA-F0-9]{40}$') {
            Fail "Missing source commit for release change notes: $($sourceRepo.name)"
        }
        if ($seenCommits.ContainsKey($commit)) {
            continue
        }

        $repoPath = Get-ReleaseSourceRepoPath -PathRole ([string]$sourceRepo.pathRole)
        $subject = Get-ReleaseGitValue `
            -RepoPath $repoPath `
            -Arguments @('show', '-s', '--format=%s', '--no-show-signature', $commit) `
            -Purpose "$($sourceRepo.name) commit subject"
        if ([string]::IsNullOrWhiteSpace($subject)) {
            Fail "Missing commit subject for release change notes: $($sourceRepo.name)@$commit"
        }

        $shortCommit = $commit.Substring(0, 12)
        $items += ('{0}{1}{2} {3}' -f $commitLabel, $fullWidthColon, $shortCommit, $subject)
        $subjects += $subject
        $seenCommits[$commit] = $true
    }

    if ($items.Count -eq 0) {
        Fail 'Missing commit change entries for release change notes.'
    }

    return [ordered]@{
        items = @($items)
        subjects = @($subjects)
    }
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

function Test-ReleaseRollbackMigrationMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SqlPath
    )

    if (-not (Test-Path -LiteralPath $SqlPath -PathType Leaf)) {
        Fail "Release migration SQL missing before rollback metadata read: $SqlPath"
    }
    $text = [System.IO.File]::ReadAllText($SqlPath, [System.Text.UTF8Encoding]::new($false))
    return [regex]::IsMatch(
        $text,
        '^\s*--\s*rollback-migration\s*:',
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase -bor [System.Text.RegularExpressions.RegexOptions]::Multiline
    )
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
        requiresTargetPreflight = $false
        supersedes = @()
        allowedPublishScopes = @()
        applyOrder = $null
        sessionProfile = ''
        approvedHook = ''
        resultAssertion = ''
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
            'supersedes' {
                if ($values.Count -eq 0) {
                    Fail "Invalid supersedes in release migration metadata: $SqlPath"
                }
                $metadata.supersedes = @($values)
            }
            'allowedPublishScopes' {
                if ($values.Count -eq 0) {
                    Fail "Invalid allowedPublishScopes in release migration metadata: $SqlPath"
                }
                foreach ($value in $values) {
                    if ($value -notin @('app-release', 'code-only', 'with-data')) {
                        Fail "Invalid allowedPublishScopes value in release migration metadata: $SqlPath -> $value"
                    }
                }
                $metadata.allowedPublishScopes = @($values)
            }
            'type' {
                if ($values.Count -ne 1 -or $values[0] -notin $releaseMigrationAllowedTypes) {
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
            'requiresTargetPreflight' {
                if ($values.Count -ne 1 -or $values[0].ToLowerInvariant() -notin @('true', 'false')) {
                    Fail "Invalid requiresTargetPreflight in release migration metadata: $SqlPath"
                }
                $metadata.requiresTargetPreflight = $values[0].ToLowerInvariant() -eq 'true'
            }
            'applyOrder' {
                if ($values.Count -ne 1 -or $values[0] -notmatch '^[0-9]+$') {
                    Fail "Invalid applyOrder in release migration metadata: $SqlPath"
                }
                $metadata.applyOrder = [int]$values[0]
            }
            'sessionProfile' {
                if ($values.Count -ne 1 -or $values[0] -notmatch '^[a-z0-9][a-z0-9._-]{0,63}$') {
                    Fail "Invalid sessionProfile in release migration metadata: $SqlPath"
                }
                $metadata.sessionProfile = [string]$values[0]
            }
            'approvedHook' {
                if ($values.Count -ne 1 -or $values[0] -notmatch '^[a-z0-9][a-z0-9._-]{0,63}$') {
                    Fail "Invalid approvedHook in release migration metadata: $SqlPath"
                }
                $metadata.approvedHook = [string]$values[0]
            }
            'resultAssertion' {
                if ($values.Count -ne 1 -or $values[0] -notmatch '^[a-z0-9][a-z0-9._-]{0,63}$') {
                    Fail "Invalid resultAssertion in release migration metadata: $SqlPath"
                }
                $metadata.resultAssertion = [string]$values[0]
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
        $migrationId = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
        $targetPreflightPath = Join-Path $backendRepo (Join-Path 'sql\mysql\target-preflight' "$migrationId.preflight.sql")
        $hasTargetPreflight = Test-Path -LiteralPath $targetPreflightPath -PathType Leaf
        if ([bool]$metadata.requiresTargetPreflight -and -not $hasTargetPreflight) {
            Fail "Release migration requires target preflight but contract is missing: $targetPreflightPath"
        }
        $targetPreflight = $null
        if ($hasTargetPreflight) {
            $reference = "target-preflight/$migrationId.preflight.sql"
            $packagedCheck = Join-Path (Split-Path -Parent $requiredSqlLocalDir) $reference
            if (-not (Test-Path -LiteralPath $packagedCheck -PathType Leaf)) {
                Fail "PACKAGE_TARGET_PREFLIGHT_INVALID: missing staged $reference"
            }
            $targetPreflight = [ordered]@{ reference = $reference; sha256 = ConvertTo-ReleaseFileSha256Digest -Path $packagedCheck; readOnly = $true }
        }
        $entries += [ordered]@{
            id = $migrationId
            migrationId = $migrationId
            file = "required-sql/$fileName"
            sourcePath = $relativePath
            type = [string]$metadata.type
            allowedEnvironments = @($metadata.allowedEnvironments)
            dependsOn = @($metadata.dependsOn)
            riskLevel = [string]$metadata.riskLevel
            requiresTargetPreflight = ([bool]$metadata.requiresTargetPreflight -or $hasTargetPreflight)
            targetPreflight = $targetPreflight
            supersedes = @($metadata.supersedes)
            allowedPublishScopes = @($metadata.allowedPublishScopes)
            applyOrder = $metadata.applyOrder
            sessionProfile = [string]$metadata.sessionProfile
            approvedHook = [string]$metadata.approvedHook
            resultAssertion = [string]$metadata.resultAssertion
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

function Invoke-BackendSpringConstructorGate {
    $gateScript = Join-Path $maintenanceReleaseScriptRoot 'spring_constructor_contract_gate.py'
    if (-not (Test-Path -LiteralPath $gateScript -PathType Leaf)) {
        Fail "Spring constructor contract gate script missing: $gateScript"
    }
    $result = Invoke-ProcessCapture `
        -FilePath 'python' `
        -ArgumentList @('-X', 'utf8', $gateScript, '--source-root', $backendRepo) `
        -WorkingDirectory $backendRepo
    $output = (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($output) {
        Info "Spring constructor gate output: $output"
    }
    if ($result.ExitCode -ne 0) {
        Fail 'Spring constructor contract gate failed; backend build is blocked before package generation.'
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
            requiresTargetPreflight = [bool]$requiredSql.requiresTargetPreflight
            targetPreflight = $requiredSql.targetPreflight
            supersedes = @($requiredSql.supersedes)
            allowedPublishScopes = @($requiredSql.allowedPublishScopes)
            applyOrder = $requiredSql.applyOrder
            sessionProfile = [string]$requiredSql.sessionProfile
            approvedHook = [string]$requiredSql.approvedHook
            resultAssertion = [string]$requiredSql.resultAssertion
            requiredPreflight = $true
        }
    }
    return @($entries)
}

function Invoke-BuildReleaseTargetPreflight {
    if ($Mode -ne 'build-release' -or -not $publishBackend) {
        return
    }

    $targetEnvironment = 'test'
    $publishScope = $PublishScope
    $preflightRunner = Join-Path $maintenanceReleaseScriptRoot 'release_build_preflight.py'
    if (-not (Test-Path -LiteralPath $preflightRunner -PathType Leaf)) {
        Fail "Build preflight runner missing: $preflightRunner"
    }

    $evidenceRoot = Join-Path $localTempRoot "build-preflight-$packageDirectoryName"
    if (Test-Path -LiteralPath $evidenceRoot) {
        Remove-Item -LiteralPath $evidenceRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
    $prospectiveManifestPath = Join-Path $evidenceRoot 'prospective-manifest.json'
    $targetStatePath = Join-Path $evidenceRoot 'target-state-test.json'
    $evidencePath = Join-Path $evidenceRoot 'build-preflight-evidence.json'

    $requiredSqlEntries = New-ReleaseRequiredSqlManifestEntries
    $prospectiveManifest = [ordered]@{
        schemaVersion = 'release-build-prospective/v1'
        releaseTag = $ReleaseTag
        sourceRepos = @(New-ReleaseSourceRepoManifestEntries)
        publishScope = $publishScope
        database = [ordered]@{
            schemaMigrations = @(New-ReleaseMigrationPlanEntries -RequiredSqlEntries $requiredSqlEntries)
        }
        requiredSql = @($requiredSqlEntries)
    }
    [System.IO.File]::WriteAllText(
        $prospectiveManifestPath,
        ($prospectiveManifest | ConvertTo-Json -Depth 12),
        [System.Text.UTF8Encoding]::new($false)
    )

    $collectionId = [System.Guid]::NewGuid().ToString()
    $collectedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
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
WHERE target_environment = 'test'
  AND deleted = b'0'
  AND status IN ('APPLIED', 'SKIPPED_ALREADY_APPLIED');
"@
    $stateSqlBase64 = [Convert]::ToBase64String([System.Text.UTF8Encoding]::new($false).GetBytes($stateSql))
    $remoteCommand = @"
set -e
mysql_password=`$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' intruoyi-mysql | sed -n 's/^MYSQL_ROOT_PASSWORD=//p' | tail -n 1)
test -n "`$mysql_password"
printf '%s' '$stateSqlBase64' | base64 -d | docker exec -i -e MYSQL_PWD="`$mysql_password" intruoyi-mysql mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names ruoyi-vue-pro
"@
    $normalizedRemoteCommand = $remoteCommand -replace "`r`n", "`n" -replace "`r", "`n"
    $sshArgs = @('-n') + (Get-SshCommonOptions) + @("$ServerUser@$TestServerHost", $normalizedRemoteCommand)
    Info "Collecting fresh read-only migration ledger from test server: $TestServerHost (collectionId=$collectionId)"
    $capture = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList $sshArgs
    if ($capture.ExitCode -ne 0) {
        $safeError = Protect-ReleaseSensitiveText (Remove-SshNoise ([string]$capture.StdErr))
        Fail "Build preflight target-state collection failed: $safeError"
    }
    $ledgerJson = ([string]$capture.StdOut).Trim()
    if ([string]::IsNullOrWhiteSpace($ledgerJson)) {
        Fail 'Build preflight target-state collection returned blank output'
    }
    try {
        $ledger = $ledgerJson | ConvertFrom-Json
    } catch {
        Fail "Build preflight target-state collection returned invalid JSON: $($_.Exception.Message)"
    }
    if ($null -eq $ledger -or $ledger -isnot [pscustomobject]) {
        Fail 'Build preflight target-state migration ledger must be a JSON object'
    }
    $targetState = [ordered]@{
        schemaVersion = 'release-target-state/v1'
        collectionId = $collectionId
        collectedAt = $collectedAt
        targetEnvironment = $targetEnvironment
        migrationLedger = $ledger
    }
    [System.IO.File]::WriteAllText(
        $targetStatePath,
        ($targetState | ConvertTo-Json -Depth 12),
        [System.Text.UTF8Encoding]::new($false)
    )

    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8',
        $preflightRunner,
        'run',
        '--prospective-manifest', $prospectiveManifestPath,
        '--target-state', $targetStatePath,
        '--target-environment', $targetEnvironment,
        '--publish-scope', $publishScope,
        '--package-root', $releaseDir,
        '--output', $evidencePath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8',
        $preflightRunner,
        'verify',
        '--prospective-manifest', $prospectiveManifestPath,
        '--target-state', $targetStatePath,
        '--target-environment', $targetEnvironment,
        '--publish-scope', $publishScope,
        '--package-root', $releaseDir,
        '--output', $evidencePath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
    Info "Migration ledger plan passed: $evidencePath"
}

function Invoke-BuildReleaseTargetDataPreflight {
    if ($Mode -ne 'build-release' -or -not $publishBackend) { return }
    $runner = Join-Path $maintenanceReleaseScriptRoot 'release_target_data_preflight.py'
    $planRoot = Join-Path $localTempRoot "build-preflight-$packageDirectoryName"
    if (-not (Test-Path -LiteralPath $planRoot -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $planRoot | Out-Null
    }
    $reportPath = Join-Path $planRoot 'target-data-preflight.json'
    if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
        Fail "Target data preflight runner missing: $runner"
    }
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8', $runner,
        '--prospective-manifest', (Join-Path $planRoot 'prospective-manifest.json'),
        '--target-state', (Join-Path $planRoot 'target-state-test.json'),
        '--build-evidence', (Join-Path $planRoot 'build-preflight-evidence.json'),
        '--package-root', $releaseDir,
        '--checks-root', (Join-Path $releaseDir 'target-preflight'),
        '--server', $TestServerHost, '--user', $ServerUser,
        '--output', $reportPath
    ) -WorkingDirectory $maintenanceReleaseScriptRoot
    Info "Target read-only data preflight passed: $reportPath"
}

function Invoke-BuildReleaseSchemaOnlyMigrationRehearsal {
    if ($Mode -ne 'build-release' -or -not $publishBackend) {
        return
    }
    $rehearsalRunner = Join-Path $maintenanceReleaseScriptRoot 'release_schema_rehearsal.py'
    if (-not (Test-Path -LiteralPath $rehearsalRunner -PathType Leaf)) {
        Fail "Schema-only migration rehearsal runner missing: $rehearsalRunner"
    }

    $imageCommand = @'
set -e
image_ref=$(docker inspect -f '{{.Config.Image}}' intruoyi-mysql)
docker image inspect --format '{{index .RepoDigests 0}}' "$image_ref"
'@
    $imageCapture = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (@('-n') + (Get-SshCommonOptions) + @(
        "$ServerUser@$TestServerHost", (($imageCommand -replace "`r`n", "`n") -replace "`r", "`n")
    ))
    if ($imageCapture.ExitCode -ne 0) {
        Fail "Schema-only rehearsal could not resolve the test MySQL image digest: $(Protect-ReleaseSensitiveText ([string]$imageCapture.StdErr))"
    }
    $mysqlImage = ([string]$imageCapture.StdOut).Trim()
    if ($mysqlImage -notmatch '^[^\s@]+@sha256:[0-9a-f]{64}$') {
        Fail "Schema-only rehearsal requires a digest-pinned test MySQL image: $mysqlImage"
    }

    $schemaCommand = @'
set -e
mysql_password=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' intruoyi-mysql | sed -n 's/^MYSQL_ROOT_PASSWORD=//p' | tail -n 1)
test -n "$mysql_password"
docker exec -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysqldump -uroot --default-character-set=utf8mb4 --no-data --routines --events --triggers --single-transaction --skip-lock-tables ruoyi-vue-pro
'@
    $schemaCapture = Invoke-ProcessCapture -FilePath 'ssh' -ArgumentList (@('-n') + (Get-SshCommonOptions) + @(
        "$ServerUser@$TestServerHost", (($schemaCommand -replace "`r`n", "`n") -replace "`r", "`n")
    ))
    if ($schemaCapture.ExitCode -ne 0) {
        Fail "Schema-only snapshot collection failed: $(Protect-ReleaseSensitiveText ([string]$schemaCapture.StdErr))"
    }
    $schemaPath = Join-Path $localTempRoot "schema-only-$packageDirectoryName.sql"
    [System.IO.File]::WriteAllText($schemaPath, [string]$schemaCapture.StdOut, [System.Text.UTF8Encoding]::new($false))
    $evidenceDirectory = Join-Path $releaseDir 'evidence'
    New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
    $evidencePath = Join-Path $evidenceDirectory 'schema-only-migration-rehearsal.json'
    $buildPreflightEvidencePath = Join-Path (Join-Path $localTempRoot "build-preflight-$packageDirectoryName") 'build-preflight-evidence.json'
    if (-not (Test-Path -LiteralPath $buildPreflightEvidencePath -PathType Leaf)) {
        Fail "Schema-only migration rehearsal requires build preflight evidence: $buildPreflightEvidencePath"
    }
    $migrationListPath = Join-Path $localTempRoot "schema-only-migrations-$packageDirectoryName.json"
    $migrationPaths = @(
        foreach ($entry in @(New-ReleaseRequiredSqlManifestEntries)) {
            Join-Path $releaseDir ([string]$entry.file).Replace('/', '\')
        }
    )
    $migrationListJson = ConvertTo-Json -InputObject ([object[]]$migrationPaths) -Compress
    [System.IO.File]::WriteAllText($migrationListPath, $migrationListJson, [System.Text.UTF8Encoding]::new($false))
    $argumentList = @(
        '-X', 'utf8', $rehearsalRunner,
        '--mysql-image', $mysqlImage,
        '--schema', $schemaPath,
        '--migration-list', $migrationListPath,
        '--preflight-evidence', $buildPreflightEvidencePath,
        '--output', $evidencePath
    )
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList $argumentList -WorkingDirectory $maintenanceReleaseScriptRoot
    Info "Schema-only migration rehearsal passed: $evidencePath"
}

function Assert-ReleaseSourceFreeze {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('before-build', 'before-package')]
        [string]$VerificationPoint,
        [AllowNull()]
        [object]$ExpectedEvidence
    )

    $maintenanceRoot = Get-ReleaseGitValue -RepoPath $scriptDir -Arguments @('rev-parse', '--show-toplevel') -Purpose 'maintenance git root'
    $applicationRoot = Get-ReleaseGitValue -RepoPath $backendRepo -Arguments @('rev-parse', '--show-toplevel') -Purpose 'application git root'
    $frontendRoot = Get-ReleaseGitValue -RepoPath $frontendDir -Arguments @('rev-parse', '--show-toplevel') -Purpose 'frontend git root'
    if ($Mode -eq 'build-release') {
        foreach ($approval in @(
            @{ name = 'ExpectedMaintenanceCommit'; value = $ExpectedMaintenanceCommit },
            @{ name = 'ExpectedApplicationCommit'; value = $ExpectedApplicationCommit },
            @{ name = 'ExpectedFrontendCommit'; value = $ExpectedFrontendCommit },
            @{ name = 'SourceSelectionId'; value = $SourceSelectionId }
        )) {
            if ([string]::IsNullOrWhiteSpace([string]$approval.value)) {
                Fail "SOURCE_APPROVAL_REQUIRED: $($approval.name)"
            }
        }
        if ($SourceSelectionId -notmatch '^[a-z0-9][a-z0-9.-]{2,63}$') {
            Fail "SOURCE_SELECTION_INVALID: $SourceSelectionId"
        }
        foreach ($approval in @(
            @{ name = 'ExpectedMaintenanceCommit'; value = $ExpectedMaintenanceCommit },
            @{ name = 'ExpectedApplicationCommit'; value = $ExpectedApplicationCommit },
            @{ name = 'ExpectedFrontendCommit'; value = $ExpectedFrontendCommit }
        )) {
            if ([string]$approval.value -notmatch '^[0-9a-fA-F]{40}$') {
                Fail "SOURCE_COMMIT_INVALID: $($approval.name)"
            }
        }
    }
    if ($applicationRoot -cne $frontendRoot) {
        Fail "SOURCE_ROOT_MISMATCH: backend and frontend must share one IntRuoyi git root"
    }

    $rootFacts = @(
        [ordered]@{ rootRole = 'maintenance'; path = $maintenanceRoot },
        [ordered]@{ rootRole = 'application'; path = $applicationRoot }
    )
    $sourceRoots = @()
    foreach ($rootFact in $rootFacts) {
        $head = Get-ReleaseGitValue -RepoPath $rootFact.path -Arguments @('rev-parse', 'HEAD') -Purpose "$($rootFact.rootRole) source HEAD"
        $normalizedRoot = ([System.IO.Path]::GetFullPath([string]$rootFact.path)).Replace('\', '/').ToLowerInvariant()
        $status = & git -C $rootFact.path status --porcelain --untracked-files=all
        if ($LASTEXITCODE -ne 0) {
            Fail "SOURCE_STATUS_FAILED: $($rootFact.rootRole)"
        }
        if (-not [string]::IsNullOrWhiteSpace(($status -join "`n"))) {
            Fail "SOURCE_DIRTY: $($rootFact.rootRole)"
        }
        $approvedCommit = $head
        $expectedCommit = switch ([string]$rootFact.rootRole) {
            'maintenance' { $ExpectedMaintenanceCommit }
            'application' { $ExpectedApplicationCommit }
        }
        if ($Mode -eq 'build-release' -and $head -cne [string]$expectedCommit) {
            Fail "SOURCE_APPROVED_COMMIT_MISMATCH: $($rootFact.rootRole) expected=$expectedCommit actual=$head"
        }
        if ($null -ne $ExpectedEvidence) {
            $expectedRoot = @($ExpectedEvidence.sourceRoots | Where-Object { $_.rootRole -eq $rootFact.rootRole }) | Select-Object -First 1
            if ($null -eq $expectedRoot) {
                Fail "SOURCE_ROOT_MISSING: $($rootFact.rootRole)"
            }
            if ($normalizedRoot -cne [string]$expectedRoot.normalizedRoot) {
                Fail "SOURCE_ROOT_PATH_DRIFT: $($rootFact.rootRole) expected=$($expectedRoot.normalizedRoot) actual=$normalizedRoot"
            }
            $approvedCommit = [string]$expectedRoot.approvedCommit
            if ($head -cne $approvedCommit) {
                Fail "SOURCE_HEAD_DRIFT: $($rootFact.rootRole) expected=$approvedCommit actual=$head"
            }
        }
        $sourceRoots += [ordered]@{
            rootRole = [string]$rootFact.rootRole
            normalizedRoot = $normalizedRoot
            approvedCommit = $approvedCommit
            commit = $head
            dirty = $false
        }
    }

    $maintenanceCommit = [string](@($sourceRoots | Where-Object { $_.rootRole -eq 'maintenance' })[0].commit)
    $applicationCommit = [string](@($sourceRoots | Where-Object { $_.rootRole -eq 'application' })[0].commit)
    $sourceRoles = @(
        [ordered]@{ sourceRole = 'maintenance'; rootRole = 'maintenance'; relativePath = '.'; commit = $maintenanceCommit },
        [ordered]@{ sourceRole = 'backend'; rootRole = 'application'; relativePath = 'IntRuoyiBackend'; commit = $applicationCommit },
        [ordered]@{ sourceRole = 'frontend'; rootRole = 'application'; relativePath = 'IntRuoyiFronted'; commit = $applicationCommit }
    )
    if ($Mode -eq 'build-release' -and $ExpectedFrontendCommit -cne $applicationCommit) {
        Fail "SOURCE_APPROVED_COMMIT_MISMATCH: frontend expected=$ExpectedFrontendCommit actual=$applicationCommit"
    }
    if ($null -ne $ExpectedEvidence) {
        foreach ($sourceRole in $sourceRoles) {
            $expectedRole = @($ExpectedEvidence.sourceRoles | Where-Object { $_.sourceRole -eq $sourceRole.sourceRole }) | Select-Object -First 1
            if ($null -eq $expectedRole) {
                Fail "SOURCE_ROLE_SET_DRIFT: $($sourceRole.sourceRole)"
            }
            if ([string]$expectedRole.rootRole -cne [string]$sourceRole.rootRole) {
                Fail "SOURCE_ROLE_ROOT_DRIFT: $($sourceRole.sourceRole)"
            }
            if ([string]$expectedRole.relativePath -cne [string]$sourceRole.relativePath) {
                Fail "SOURCE_ROLE_PATH_DRIFT: $($sourceRole.sourceRole)"
            }
            if ([string]$expectedRole.commit -cne [string]$sourceRole.commit) {
                Fail "SOURCE_ROLE_COMMIT_DRIFT: $($sourceRole.sourceRole)"
            }
        }
    }
    return [pscustomobject][ordered]@{
        verificationPoint = $VerificationPoint
        sourceRoots = $sourceRoots
        sourceRoles = $sourceRoles
    }
}

function Invoke-StandardReleaseContractTests {
    $maintenanceRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

    Write-ReleaseWorkflowStage -State 'TESTING' -Evidence 'standard-release-contract-tests'
    Info 'Running backend contract tests'
    Invoke-CheckedMavenCommand -ArgumentList @(
        '-f', (Join-Path $backendRepo 'pom.xml'),
        '-pl', 'yudao-module-infra', '-am',
        '-Dtest=ReleaseWorkflowContractTest,ReleaseSourceFreezeTest,ReleaseWorkflowGateOrderTest,ReleaseDigestVectorTest',
        '-Dsurefire.failIfNoSpecifiedTests=false', 'test'
    )
    Info 'Running frontend contract tests'
    Invoke-CheckedCommand -FilePath 'node' -ArgumentList @((Join-Path $frontendDir 'tests\e2e\runtime-control-one-button-static.spec.cjs'))
    Invoke-CheckedCommand -FilePath 'corepack' -ArgumentList @('pnpm', '--dir', $frontendDir, 'ts:check')
    Info 'Discovering application migration tests from the frozen source diff'
    $applicationTestFiles = Assert-ApplicationMigrationTestsDiscovered
    $applicationPytestFiles = @($applicationTestFiles | Where-Object { $_ -match '\.py$' })
    $applicationNodeTestFiles = @($applicationTestFiles | Where-Object { $_ -match '\.test\.mjs$' })
    if ($applicationPytestFiles.Count -gt 0) {
        $applicationPytestRoot = Join-Path $resolvedLocalCacheRoot "release-application-test-temp\$packageDirectoryName"
        $applicationPytestParent = Split-Path -Parent $applicationPytestRoot
        New-Item -ItemType Directory -Force -Path $applicationPytestParent | Out-Null
        Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
            '-X', 'utf8', '-m', 'pytest', '-q',
            $applicationPytestFiles,
            '--basetemp', $applicationPytestRoot
        )
    }
    foreach ($applicationNodeTestFile in $applicationNodeTestFiles) {
        Invoke-CheckedCommand -FilePath 'node' -ArgumentList @($applicationNodeTestFile)
    }
    Info 'Running release script tests'
    $pytestRoot = Join-Path $resolvedLocalCacheRoot "release-workflow-test-temp\$packageDirectoryName"
    $pytestParent = Split-Path -Parent $pytestRoot
    New-Item -ItemType Directory -Force -Path $pytestParent | Out-Null
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList @(
        '-X', 'utf8', '-m', 'pytest', '-q',
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_workflow_preflight.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_digest_vectors.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_app_release_package_governance.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_docker_context_cleanup.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_target_data_preflight.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_migration_preflight_matrix.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_schema_rehearsal.py'),
        (Join-Path $scriptDir '..\..\scripts\tests\test_release_build_preflight_cache.py'),
        '--basetemp', $pytestRoot
    ) -WorkingDirectory $maintenanceRoot
    Invoke-CheckedCommand -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        (Join-Path $scriptDir '..\..\scripts\tests\verify-release-digest-vector.ps1')
    ) -WorkingDirectory $maintenanceRoot
}

function Assert-ApplicationMigrationTestsDiscovered {
    $applicationRoot = Get-ReleaseGitValue -RepoPath $backendRepo -Arguments @('rev-parse', '--show-toplevel') -Purpose 'application git root'
    $diffFiles = @(Get-ReleaseGitValue -RepoPath $applicationRoot -Arguments @('diff', '--name-only', 'HEAD^', 'HEAD', '--', 'IntRuoyiBackend/sql/mysql') -Purpose 'application migration source diff' |
        Where-Object { ([string]$_).Replace('\', '/') -notmatch '(^|/)target-preflight/' } |
        Where-Object { [string]$_ -match '(^|/)20[0-9]{6}_[A-Za-z0-9_.-]+\.sql$' })
    $migrationIds = @($diffFiles | ForEach-Object {
        $name = Split-Path -Leaf ([string]$_)
        if ($name -match '^(20[0-9]{6}_[A-Za-z0-9_.-]+)\.sql$') { $Matches[1] }
    } | Select-Object -Unique)
    if ($migrationIds.Count -eq 0) {
        return @()
    }
    $testRoots = @(
        (Join-Path $backendRepo 'script\tests'),
        (Join-Path $applicationRoot 'scripts\tests')
    )
    $testFiles = @($testRoots | Where-Object { Test-Path -LiteralPath $_ -PathType Container } |
        ForEach-Object {
            Get-ChildItem -LiteralPath $_ -File -Recurse |
                Where-Object {
                    $_.FullName -notmatch '[\\/](?:__pycache__|\.pytest_cache)(?:[\\/]|$)' -and
                    $_.Name -notmatch '\.pyc$' -and
                    ($_.Name -match '^test_.*\.py$' -or $_.Name -match '\.test\.mjs$')
                }
        })
    $discovered = @()
    foreach ($migrationId in $migrationIds) {
        $matches = @($testFiles | Select-String -SimpleMatch -Pattern $migrationId | Select-Object -ExpandProperty Path -Unique)
        if ($matches.Count -eq 0) {
            Fail "MIGRATION_TEST_MISSING: $migrationId"
        }
        $discovered += $matches
    }
    return @($discovered | Select-Object -Unique)
}

function Get-ReleaseSchemaDigest {
    param(
        [Parameter(Mandatory = $true)]
        [array]$RequiredSqlEntries
    )
    $schemaContract = [ordered]@{
        requiredSql = @($RequiredSqlEntries)
        publishScope = $PublishScope
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
            bytes = [int64]$artifact.bytes
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

function Write-AuthoritativeReleaseManifest {
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
    $packageType = 'release-code'
    $publishScopeValue = 'app-release'
    $packageDigest = (Get-ReleasePackageDigest -Artifacts $LegacyArtifacts).PackageDigest

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
        sourceRoots = @($script:ReleaseSourceFreezeEvidence.sourceRoots)
        sourceRoles = @($script:ReleaseSourceFreezeEvidence.sourceRoles)
        changeSet = New-ReleaseChangeSetManifest -PackageTag $PackageTag -SourceRepos $sourceRepos
        publishScope = $publishScopeValue
        packageDigest = $packageDigest
        packageRole = $packageType
        relatedReleaseTag = $PackageTag
        components = $components
        component = $Component
        onlyOfficeIncluded = [bool]$IncludeOnlyOffice
        installationContractVersion = 'full-app-release/v1'
        runtimeImages = @($script:ReleaseRuntimeImages)
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
            platformPrerequisites = @(Get-ReleasePlatformPrerequisites -Component $Component)
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
    $manifestJson = (($manifestV1 | ConvertTo-Json -Depth 20) -replace "`r`n", "`n").TrimEnd("`r", "`n") + "`n"
    [System.IO.File]::WriteAllText((Join-Path $releaseDir 'manifest.json'), $manifestJson, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-ReleaseManifestValidationGate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath
    )

    $planRoot = Join-Path $localTempRoot "build-preflight-$packageDirectoryName"
    if (-not (Test-Path -LiteralPath $planRoot -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $planRoot | Out-Null
    }
    $reportPath = Join-Path $planRoot 'manifest-validation-result.json'
    $result = Invoke-ReleaseManifestValidation -PackagePath $PackagePath -Mode 'report-only'
    $resultJson = ($result | ConvertTo-Json -Depth 20)
    [System.IO.File]::WriteAllText($reportPath, $resultJson + [System.Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    if ($result.status -eq 'failed') {
        Fail "Release manifest validation failed: $($result.code). Report: $reportPath"
    }
    Info "Release manifest validation passed: $reportPath"
}

function Write-ReleaseManifest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageTag
    )
    Write-ReleaseResourceReferenceManifest -PackageTag $PackageTag
    $artifacts = @(Get-ReleasePackageImmutableArtifactEntries -PackagePath $releaseDir -ExcludeManifestJson -EmitProgress)
    Write-AuthoritativeReleaseManifest -PackageTag $PackageTag -LegacyArtifacts $artifacts
    Set-ReleasePackageArtifactCache -Artifacts $artifacts
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
$backendRepo = $defaultBackendRepo
$workspaceRoot = Split-Path -Parent $backendRepo
$frontendDir = ''
if ($Mode -eq 'build-release') {
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
}
$defaultWebsiteRepo = 'D:\ProjectPackage\Website'
if ([string]::IsNullOrWhiteSpace($WebsiteRepo)) {
    $WebsiteRepo = $defaultWebsiteRepo
}
$websiteRepo = ''
if ($Mode -eq 'build-release' -and $Component -eq 'full') {
    $websiteRepo = (Resolve-Path -LiteralPath $WebsiteRepo).Path
}
$publishBackend = $Component -in @('full', 'intruoyi')
$publishFrontend = $Component -in @('full', 'intruoyi')
$publishWebsite = $Component -eq 'full'
$effectiveBuildPublishScope = Resolve-EffectiveBuildReleasePublishScope
$backendJar = Join-Path $backendRepo 'yudao-server\target\yudao-server-exec.jar'
$backendDockerfile = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\Dockerfile.backend'
$frontendDockerfile = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\Dockerfile.frontend'
$composeTemplate = Join-Path $scriptDir 'int-ruoyi-test\docker-compose.yml'
$websiteNginxTemplate = Join-Path $backendRepo 'script\deploy\int-ruoyi-test\website.nginx.conf'
$onlyOfficeImage = 'onlyoffice/documentserver:latest'
$frontendRuntimeBaseImage = 'nginx:1.27-alpine'
$resolvedLocalCacheRoot = Resolve-LocalCacheRoot $LocalCacheRoot
$buildReleaseRuntimeRestartGuardFile = Join-Path $resolvedLocalCacheRoot 'runtime\local-runtime-restart.guard'
Enter-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile
$localTempRoot = Join-Path $resolvedLocalCacheRoot 'publish-int-ruoyi'
$releaseDir = Join-Path $localTempRoot $packageDirectoryName
$deployControlLocalRoot = Join-Path $localTempRoot ('.deploy-control-' + $packageDirectoryName)
$dockerBuildContextRoot = Join-Path $releaseDir 'docker-build-context'
$imageTar = Join-Path $releaseDir "intruoyi-images_$packageDirectoryName.tar"
$dbDump = Join-Path $releaseDir 'ruoyi-vue-pro-current.sql'
$resetDbSqlLocal = Join-Path $releaseDir 'reset-db.sql'
$postImportSqlLocal = Join-Path $deployControlLocalRoot 'post-import.sql'
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
            if (Test-ReleaseRollbackMigrationMetadata -SqlPath $file.FullName) {
                Info "Excluding rollback-only release SQL from required migrations: $($file.Name)"
                continue
            }
            $metadata = Read-ReleaseMigrationMetadata -SqlPath $file.FullName
            if ([string]$metadata.type -in $releaseMigrationEvidenceOnlyTypes) {
                Info "Excluding evidence-only release SQL from required migrations: $($file.Name) [$($metadata.type)]"
                continue
            }
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

$script:ReleaseSourceFreezeEvidence = $null
if ($Mode -eq 'build-release') {
    $null = Read-NasReleaseConfig
    $script:ReleaseSourceFreezeEvidence = Assert-ReleaseSourceFreeze -VerificationPoint 'before-build'
}

$requiredDatabaseSqlScripts = @()
if ($Mode -notin @('deploy-release', 'mark-tested')) {
    $requiredDatabaseSqlScripts = Get-ReleaseDatabaseSqlScripts
}
if ($publishBackend -and $Mode -eq 'build-release') {
    Invoke-ReleaseMigrationPolicyGate
}
$requiredSqlLocalDir = Join-Path $releaseDir 'required-sql'
$opsRuntimeLocalDir = Join-Path $releaseDir 'ops-runtime'
$websiteRuntimeLocal = Join-Path $releaseDir 'website'
$websiteNginxLocal = Join-Path $deployControlLocalRoot 'website\nginx.conf'
$remoteReleaseDir = "$RemoteReleaseRoot/$packageDirectoryName"
$remoteImageTar = "$remoteReleaseDir/intruoyi-images_$packageDirectoryName.tar"
$remoteDbDump = "$remoteReleaseDir/ruoyi-vue-pro-current.sql"
$remoteResetDbSql = "$remoteReleaseDir/reset-db.sql"
$remotePostImportSql = "$remoteReleaseDir/post-import.sql"
$remoteRequiredSqlDir = "$remoteReleaseDir/required-sql"
$remoteOpsRuntimeDir = '/opt/intruoyi/ops/backup-ops/linux-native'
$remoteCompose = "$RemoteAppDir/docker-compose.yml"
$remoteEnv = "$RemoteAppDir/.env"
$remoteEnvNext = "$RemoteAppDir/.env.next"
$remoteWebsiteDir = "$RemoteAppDir/website"
$remoteWebsiteStagingDir = "$remoteReleaseDir/website"
$remoteWebsitePreviousDir = "$RemoteAppDir/website.previous"
$schedulerSmokeFrontendDirectory = '/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3'
$schedulerSmokeScriptName = 'e2e:mes:smart-scheduling-smoke'
$schedulerSmokeNodeImage = 'mcr.microsoft.com/playwright:v1.60.0-noble'
$script:ReleaseRuntimeVerification = [ordered]@{ loadedImages=@(); images=@(); website=$null; checks=@() }
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
    param(
        [string]$Path = $remoteEnv,
        [string]$Label = 'Remote runtime .env'
    )
    $remoteEnvLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $Path -Purpose 'remote runtime env path'
    $expectedImageTagLine = "IMAGE_TAG=$packageDirectoryName"
    $expectedImageTagLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $expectedImageTagLine -Purpose 'remote runtime IMAGE_TAG'
    $command = @"
set -eu
test -f $remoteEnvLiteral
grep -Fx $expectedImageTagLiteral $remoteEnvLiteral
"@
    Invoke-SshCommand $command
    Info "$Label IMAGE_TAG verified: $packageDirectoryName"
}

function Switch-RemoteRuntimeEnvNext {
    $remoteEnvLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnv -Purpose 'remote runtime env path'
    $remoteEnvNextLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnvNext -Purpose 'remote runtime env.next path'
    $remoteEnvBackupLiteral = ConvertTo-ShellSingleQuotedLiteral -Value "$remoteReleaseDir/.env.before-switch" -Purpose 'remote runtime env backup path'
    $command = @"
set -eu
test -f $remoteEnvNextLiteral
if [ -f $remoteEnvLiteral ]; then
  cp $remoteEnvLiteral $remoteEnvBackupLiteral
fi
mv $remoteEnvNextLiteral $remoteEnvLiteral
"@
    Invoke-SshCommand $command
    Assert-RemoteRuntimeEnvImageTag
}

function Assert-RemoteActualApplicationImages {
    $script:ReleaseRuntimeVerification.images = @()
    foreach ($image in @(Get-ReleaseTargetImageIdentities | Where-Object { $_.name -cne 'scheduler-smoke' })) {
        $container = 'intruoyi-' + $image.name
        $literal = ConvertTo-ShellSingleQuotedLiteral -Value $container -Purpose 'managed container'
        $capture = Invoke-SshCapture -IgnoreExitCode -Command "docker container inspect --format '{{.Image}}|{{.State.Running}}' $literal"
        $facts = @(([string]$capture.Output).Trim() -split '\|')
        $actual = if ($capture.Ok -and $facts.Count -eq 2) { $facts[0] } else { $null }
        $running = $capture.Ok -and $facts.Count -eq 2 -and $facts[1] -ceq 'true'
        $matched = $running -and $actual -ceq $image.configDigest
        $script:ReleaseRuntimeVerification.images += [pscustomobject][ordered]@{
            name=$image.name; reference=$image.reference; container=$container; buildImageId=$image.buildImageId
            expectedImageId=$image.configDigest; actualImageId=$actual; running=$running; matched=$matched
        }
        if (-not $matched) { Fail "RELEASE_RUNTIME_IMAGE_MISMATCH: $($image.name); expected $($image.configDigest), actual $actual, running=$running" }
    }
    Info "Remote application content identities verified: $packageDirectoryName"
}

function Assert-RemoteWebsitePayloadIdentity {
    param([AllowNull()][AllowEmptyCollection()][object[]]$ExpectedReceiptFiles,[switch]$BindCurrentPackage)
    $fromReceipt=$PSBoundParameters.ContainsKey('ExpectedReceiptFiles')
    if (-not $publishWebsite -and -not $fromReceipt) { return }
    $expected = @()
    if($fromReceipt) {
        $paths=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach($item in @($ExpectedReceiptFiles)) {
            if($null -eq $item -or [string]::IsNullOrWhiteSpace([string]$item.path) -or
               ($item.path -cne 'nginx.conf' -and -not ([string]$item.path).StartsWith('dist/',[StringComparison]::Ordinal)) -or
               $item.path -match '(^|/)\.\.?(?:/|$)' -or $item.path.Contains('\') -or
               ($item.bytes -isnot [int] -and $item.bytes -isnot [long]) -or $item.bytes -lt 0 -or
               $item.sha256 -cnotmatch '^[0-9a-f]{64}$' -or -not $paths.Add([string]$item.path)) {Fail 'RELEASE_WEBSITE_RECEIPT_INVALID: exact regular-file evidence is required'}
            $expected+=[ordered]@{path=[string]$item.path;bytes=[int64]$item.bytes;sha256=[string]$item.sha256}
        }
        if($expected.Count -lt 2 -or -not $paths.Contains('nginx.conf')){Fail 'RELEASE_WEBSITE_RECEIPT_INVALID: complete static content and configuration are required'}
        if($BindCurrentPackage) {
            $artifacts=@($releasePackageIntegrity.artifacts|Where-Object{$_.path.StartsWith('website/dist/',[StringComparison]::Ordinal)})
            if($artifacts.Count -ne $expected.Count-1){Fail 'RELEASE_WEBSITE_RECEIPT_INVALID: package artifact set differs'}
            foreach($artifact in $artifacts) {
                $match=@($expected|Where-Object{$_.path -ceq ([string]$artifact.path).Substring(8)})
                if($match.Count -ne 1 -or $match[0].bytes -ne $artifact.bytes -or $match[0].sha256 -cne $artifact.sha256){Fail 'RELEASE_WEBSITE_RECEIPT_INVALID: package artifact binding differs'}
            }
        }
    } else {
        foreach ($artifact in @($releasePackageIntegrity.artifacts | Where-Object { $_.path.StartsWith('website/dist/', [StringComparison]::Ordinal) })) {
            $expected += [ordered]@{ path=([string]$artifact.path).Substring(8); bytes=[int64]$artifact.bytes; sha256=[string]$artifact.sha256 }
        }
        if ($expected.Count -eq 0 -or -not (Test-Path -LiteralPath $websiteNginxLocal -PathType Leaf)) {
            Fail 'RELEASE_WEBSITE_CONTENT_MISMATCH: verified static artifacts and rendered nginx configuration are required'
        }
        $config = Get-Item -LiteralPath $websiteNginxLocal
        $expected += [ordered]@{ path='nginx.conf'; bytes=$config.Length; sha256=(ConvertTo-ReleaseFileSha256Hex -Path $websiteNginxLocal) }
    }
    $rootLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteWebsiteDir -Purpose 'website runtime root'
    # Each external command is checked by set -e. The only pipe has a shell
    # builtin producer and base64 as its final (and only external) command.
    $probe = @'
set -eu
test -d __ROOT__ && test ! -L __ROOT__
cd __ROOT__
find . -mindepth 1 -exec sh -c '
set -eu
for file do
  encoded=$(printf "%s" "$file" | base64 -w 0)
  if [ -L "$file" ]; then
    printf "INVALID\t%s\n" "$encoded"
  elif [ -d "$file" ]; then
    :
  elif [ -f "$file" ]; then
    size=$(stat -c %s -- "$file")
    digest=$(sha256sum < "$file")
    digest=${digest%% *}
    printf "FILE\t%s\t%s\t%s\n" "$size" "$digest" "$encoded"
  else
    printf "INVALID\t%s\n" "$encoded"
  fi
done
' sh {} +
printf 'WEBSITE_SCAN_COMPLETE\n'
'@
    $capture = Invoke-SshCapture -IgnoreExitCode -Command $probe.Replace('__ROOT__', $rootLiteral)
    if (-not $capture.Ok) {
        $script:ReleaseRuntimeVerification.website = @{status='unknown';expected=$expected;actual=$null;errors=@('remote observation failed')}
        Fail 'RELEASE_WEBSITE_CONTENT_MISMATCH: remote content observation failed'
    }
    $actualMap = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $errors = @()
    $lines = @(([string]$capture.Output).TrimEnd("`r","`n") -split "`r?`n")
    if ($lines.Count -eq 0 -or $lines[-1] -cne 'WEBSITE_SCAN_COMPLETE') { $errors += 'incomplete observation' }
    foreach ($line in @($lines | Select-Object -SkipLast 1)) {
        if ($line.StartsWith("INVALID`t", [StringComparison]::Ordinal)) { $errors += 'non-regular or linked entry'; continue }
        if ($line -cnotmatch '^FILE\t([0-9]+)\t([0-9a-f]{64})\t([A-Za-z0-9+/=]+)$') { $errors += 'malformed file observation'; continue }
        $sizeText=$Matches[1];$hash=$Matches[2];$encodedPath=$Matches[3]
        try {
            $path = [Text.UTF8Encoding]::new($false,$true).GetString([Convert]::FromBase64String($encodedPath))
            if (-not $path.StartsWith('./',[StringComparison]::Ordinal)) { throw 'relative path required' }
            $path=$path.Substring(2)
            $actualMap.Add($path, [ordered]@{path=$path;bytes=[int64]$sizeText;sha256=$hash})
        } catch { $errors += 'invalid or duplicate file observation' }
    }
    if ($actualMap.Count -ne $expected.Count) { $errors += 'file set mismatch' }
    foreach ($item in $expected) {
        if (-not $actualMap.ContainsKey($item.path) -or $actualMap[$item.path].bytes -ne $item.bytes -or $actualMap[$item.path].sha256 -cne $item.sha256) {
            $errors += "file size or digest mismatch: $($item.path)"
        }
    }
    [string[]]$paths = @($actualMap.Keys)
    [Array]::Sort($paths,[StringComparer]::Ordinal)
    $actual = @($paths | ForEach-Object { $actualMap[$_] })
    $evidence = [pscustomobject]@{status=$(if($errors.Count){'failed'}else{'passed'});expected=@($expected | Sort-Object {$_.path});actual=$actual;errors=$errors}
    $script:ReleaseRuntimeVerification.website = $evidence
    if ($evidence.status -cne 'passed') { Fail ('RELEASE_WEBSITE_CONTENT_MISMATCH: ' + (@($evidence.errors) -join '; ')) }
}

function Assert-ReleaseWebsiteVerificationPrerequisites {
    if (-not $publishWebsite) { return }
    $command = @'
set -eu
for tool in find stat sha256sum base64; do
  command -v "$tool" >/dev/null || { printf 'WEBSITE_VERIFICATION_TOOL_MISSING:%s\n' "$tool"; exit 41; }
done
base64 -w 0 </dev/null >/dev/null
printf 'WEBSITE_VERIFICATION_TOOLS_READY'
'@
    $result = Invoke-SshCapture -IgnoreExitCode -Command $command
    if (-not $result.Ok -or ([string]$result.Output).Trim() -cne 'WEBSITE_VERIFICATION_TOOLS_READY') {
        Fail 'TARGET_WEBSITE_VERIFICATION_NOT_READY: require find, GNU-compatible stat/sha256sum/base64 before deployment'
    }
}

function Invoke-ReleaseRuntimeVerificationCheck {
    param([Parameter(Mandatory=$true)][string]$Name, [Parameter(Mandatory=$true)][scriptblock]$Action)
    $record = [pscustomobject][ordered]@{ name=$Name; status='started'; actual=$null; error=$null }
    $script:ReleaseRuntimeVerification.checks += $record
    try {
        $record.actual = & $Action
        $record.status = 'passed'
    } catch {
        $record.status = 'failed'
        $record.error = $_.Exception.Message
        throw
    }
}

function Assert-RemoteBackendHealthStatus {
    $url = "http://127.0.0.1:$BackendPort/actuator/health"
    $capture = Invoke-SshCapture -IgnoreExitCode -Command "curl -fsS '$url'"
    if (-not $capture.Ok) { Fail 'RELEASE_BACKEND_HEALTH_NOT_UP: backend health request failed' }
    try { $health = ([string]$capture.Output) | ConvertFrom-Json }
    catch { Fail 'RELEASE_BACKEND_HEALTH_NOT_UP: backend health response is not JSON' }
    if ($null -eq $health -or $health.status -cne 'UP') { Fail 'RELEASE_BACKEND_HEALTH_NOT_UP: backend health status must be UP' }
    return [pscustomobject]@{ url=$url; status=[string]$health.status }
}

function Assert-RemoteRuntimeEnvEdhrEndpoint {
    if ([string]::IsNullOrWhiteSpace($EdhrS3Endpoint)) {
        Fail 'EDHR_S3_ENDPOINT is required before writing the target runtime environment.'
    }
    $remoteEnvNextLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnvNext -Purpose 'remote runtime env.next path'
    $expectedEndpointLine = "EDHR_S3_ENDPOINT=$EdhrS3Endpoint"
    $expectedEndpointLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $expectedEndpointLine -Purpose 'remote runtime EDHR endpoint'
    $command = @"
set -eu
test -f $remoteEnvNextLiteral
grep -Fx $expectedEndpointLiteral $remoteEnvNextLiteral
"@
    Invoke-SshCommand $command
    Info "Remote runtime .env.next EDHR_S3_ENDPOINT verified: $EdhrS3Endpoint"
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
exec docker run --rm --pull=never --network host \
  -v /opt/intruoyi/runtime:/opt/intruoyi/runtime \
  -w "`$WORKDIR" \
$envArgs
  "`$NODE_IMAGE" npm "`$@"
"@
    return $content
}

function New-SchedulerSmokeRunnerPackage {
    param([Parameter(Mandatory = $true)][ValidatePattern('^sha256:[0-9a-f]{64}$')][string]$RuntimeImageId)
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

    $smokeDependencyRoot = Join-Path $maintenanceReleaseScriptRoot 'smoke'
    foreach ($fileName in @('package.json', 'package-lock.json')) {
        $source = Join-Path $smokeDependencyRoot $fileName
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
            Fail "Smoke dependency contract missing: $source"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $localFrontendDir $fileName) -Force
    }
    Copy-Item -LiteralPath $realFlowSource -Destination (Join-Path $localTestsDir 'smart-scheduling-smoke-real-flow.e2e.js') -Force
    Copy-Item -LiteralPath $staticSpecSource -Destination (Join-Path $localTestsDir 'smart-scheduling-smoke-real-flow-static.spec.js') -Force
    Write-Utf8LfNoBomFile -Path (Join-Path $localBinDir 'npm') -Content (New-SchedulerSmokeNpmWrapperContent)
    $containerName = 'release-smoke-' + [Guid]::NewGuid().ToString('N')
    $created = $false
    $dependencyCommand = @'
set -eu
mkdir -p /work
cp /inputs/package.json /inputs/package-lock.json /work/
cd /work
npm ci --ignore-scripts --no-audit --no-fund
node -e 'const p=require("./package.json"); for(const name of ["playwright","xlsx"]) { if(require(name+"/package.json").version!==p.devDependencies[name]) throw Error("Smoke dependency version mismatch: "+name); }'
node -e 'const {chromium}=require("playwright"); (async()=>{const browser=await chromium.launch({headless:true}); await browser.close();})().catch(error=>{console.error(error);process.exit(1)})'
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cf /tmp/dependencies.tar node_modules
'@
    $dependencyScriptPath = Join-Path $localFrontendDir '.prepare-dependencies.sh'
    Write-Utf8LfNoBomFile -Path $dependencyScriptPath -Content $dependencyCommand
    try {
        Info "Preparing Linux smoke dependencies in task container: $containerName"
        Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
            'create', '--name', $containerName, '--label', 'intruoyi.release-smoke=true',
            '--mount', "type=bind,source=$localFrontendDir,target=/inputs,readonly",
            '-e', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1', '-e', 'npm_config_cache=/tmp/npm-cache',
            $RuntimeImageId, 'sh', '/inputs/.prepare-dependencies.sh'
        )
        $created = $true
        Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('start', '--attach', $containerName)
        $containerExit = Invoke-ProcessCapture -FilePath 'docker' -ArgumentList @('inspect', '--format', '{{.State.ExitCode}}', $containerName)
        if ($containerExit.ExitCode -ne 0 -or $containerExit.StdOut.Trim() -ne '0') {
            Fail "Linux smoke dependency preparation failed in container $containerName"
        }
        $archive = Join-Path $localFrontendDir 'dependencies.tar'
        Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('cp', "${containerName}:/tmp/dependencies.tar", $archive)
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf) -or (Get-Item -LiteralPath $archive).Length -le 0) {
            Fail 'Linux smoke dependency archive missing or empty after preparation'
        }
    } finally {
        try {
            if ($created) {
                Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('rm', '--force', $containerName)
            }
        } finally {
            Remove-Item -LiteralPath $dependencyScriptPath -Force
        }
    }
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
        Fail 'PACKAGE_REQUIRED_ARTIFACT_MISSING: smoke/yudao-ui-admin-vue3/package.json; rebuild the complete package'
    }
    Info "Copying scheduler smoke runner to the $PublishTargetName server"
    Invoke-SshCommand "mkdir -p '$RemoteAppDir' '$remoteSchedulerSmokeRoot' '$remoteSchedulerSmokeFrontendDir/input' '$remoteSchedulerSmokeFrontendDir/output/artifacts' '$remoteSchedulerSmokeBinDir'"
    Copy-ToServer -LocalPath $schedulerSmokeRunnerLocalDir -RemotePath $RemoteAppDir -Recursive
    Invoke-SshCommand "chmod +x '$remoteSchedulerSmokeNpmWrapper' && test -f '$remoteSchedulerSmokeFrontendDir/package.json' && test -f '$remoteSchedulerSmokeFrontendDir/tests/e2e/smart-scheduling-smoke-real-flow.e2e.js'"
    Invoke-SshCommand "test -f '$remoteSchedulerSmokeFrontendDir/dependencies.tar' && rm -rf '$remoteSchedulerSmokeFrontendDir/node_modules' && tar -xf '$remoteSchedulerSmokeFrontendDir/dependencies.tar' -C '$remoteSchedulerSmokeFrontendDir' && test -f '$remoteSchedulerSmokeFrontendDir/node_modules/playwright/package.json' && test -f '$remoteSchedulerSmokeFrontendDir/node_modules/xlsx/package.json'"
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
            Type = [string]$_.type
            MigrationId = [string]$_.migrationId
            File = [string]$_.file
            Sha256 = [string]$_.sha256
            Supersedes = @($_.supersedes)
        }
    })
    if ($entries.Count -eq 0) {
        Fail "Release package contains no required SQL entries: $manifestPath"
    }
    return $entries
}

function Get-ReleaseCurrentDeploymentScope {
    # Completion must be recognized before migration planning. A completed
    # APPLY plan will naturally differ from a fresh SKIP plan.
    $envMap=Get-RemoteRuntimeEnvMap
    if(-not $envMap.ContainsKey('MYSQL_DATABASE') -or $envMap['MYSQL_DATABASE'] -cnotmatch '^[A-Za-z][A-Za-z0-9_-]{0,63}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_DATABASE_IDENTITY_REQUIRED'}
    $script:TargetMySqlDatabase=[string]$envMap['MYSQL_DATABASE']
    $machine=Invoke-SshCapture -IgnoreExitCode -Command 'cat /etc/machine-id'
    if(-not $machine.Ok -or ([string]$machine.Output).Trim() -cnotmatch '^[0-9a-f]{32}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_MACHINE_IDENTITY_REQUIRED'}
    $database=Get-ReleaseTargetDatabaseSnapshot
    if($database.databaseIdentity.name -cne $script:TargetMySqlDatabase){throw 'RELEASE_DEPLOYMENT_EVIDENCE_DATABASE_IDENTITY_MISMATCH'}
    return [pscustomobject]@{environment=$Environment;host=$ServerHost;machineId=([string]$machine.Output).Trim();database=$script:TargetMySqlDatabase;serverUuid=[string]$database.databaseIdentity.serverUuid}
}

function Assert-ReleaseCommittedRuntime {
    param($State,[switch]$SamePackage)
    $receipt=$State.receipt
    if($null -eq $receipt.runtime -or $receipt.runtime.config.status -cne 'observed' -or $receipt.runtime.database.status -cne 'observed'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_RUNTIME_REQUIRED'}
    $observed=Get-ReleaseDeploymentFailureObservation -ComponentNames @($receipt.verification.images|ForEach-Object{[string]$_.name})
    if(@($observed.errors).Count -or $observed.config.status -cne 'observed' -or $observed.database.status -cne 'observed'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_OBSERVATION_UNAVAILABLE'}
    $keys=@($receipt.runtime.config.values.PSObject.Properties.Name)
    if($keys.Count -ne $observed.config.values.Count){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_CONFIG_DRIFT'}
    foreach($key in $keys){
        if(-not $observed.config.values.Contains($key) -or [string]$receipt.runtime.config.values.$key -cne [string]$observed.config.values[$key]){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_CONFIG_DRIFT'}
    }
    if($receipt.runtime.database.databaseIdentity.name -cne $observed.database.databaseIdentity.name -or
       $receipt.runtime.database.databaseIdentity.serverUuid -cne $observed.database.databaseIdentity.serverUuid -or
       $receipt.runtime.database.schemaDigest -cne $observed.database.schemaDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_DATABASE_DRIFT'}
    $columns=@('migrationId','sha256','status','releaseTag','file','operationId','startedAt','finishedAt')
    $oldLedger=ConvertTo-Json -InputObject @($receipt.runtime.database.migrationLedger|Select-Object -Property $columns) -Depth 10 -Compress
    $newLedger=ConvertTo-Json -InputObject @($observed.database.migrationLedger|Select-Object -Property $columns) -Depth 10 -Compress
    if($oldLedger -cne $newLedger){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_MIGRATION_DRIFT'}
    $images=@($receipt.verification.images)
    $names=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    if($images.Count -lt 2){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_IMAGES_REQUIRED'}
    foreach($image in $images){
        if($image.name -cnotin @('backend','frontend','website','onlyoffice') -or -not $names.Add([string]$image.name) -or
           $image.matched -isnot [bool] -or $image.matched -ne $true -or $image.running -isnot [bool] -or $image.running -ne $true -or
           $image.actualImageId -cnotmatch '^sha256:[0-9a-f]{64}$' -or $image.actualImageId -cne $image.expectedImageId){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_IMAGES_INVALID'}
        $actual=Invoke-SshCapture -IgnoreExitCode -Command "docker container inspect --format '{{.Image}}|{{.State.Running}}' 'intruoyi-$($image.name)'"
        if(-not $actual.Ok -or ([string]$actual.Output).Trim() -cne ($image.actualImageId+'|true')){throw "RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_IMAGE_DRIFT: $($image.name)"}
        $checkName=$image.name+'-health'
        $proof=@($receipt.verification.checks|Where-Object{$_.name -ceq $checkName})
        if($proof.Count -ne 1 -or $proof[0].status -cne 'passed'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_HEALTH_PROOF_INVALID'}
        switch($image.name){
            'backend' {Wait-RemoteHttpOk -Url "http://127.0.0.1:$BackendPort/actuator/health" -TimeoutSeconds 180;$null=Assert-RemoteBackendHealthStatus;Assert-RemoteBackendContainerMinioReachable}
            'frontend' {Wait-RemoteHttpOk -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSeconds 180}
            'website' {Wait-RemoteHttpOk -Url "http://127.0.0.1:$WebsiteHostPort/showroom" -TimeoutSeconds 180}
            'onlyoffice' {Wait-RemoteHttpOk -Url "http://127.0.0.1:$OnlyOfficeHostPort/healthcheck" -TimeoutSeconds 180}
        }
    }
    if(-not $names.Contains('backend') -or -not $names.Contains('frontend')){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_IMAGES_INVALID'}
    if($names.Contains('website')){
        if($null -eq $receipt.verification.website -or $receipt.verification.website.status -cne 'passed'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_WEBSITE_REQUIRED'}
        Assert-RemoteWebsitePayloadIdentity -ExpectedReceiptFiles @($receipt.verification.website.expected) -BindCurrentPackage:$SamePackage
    }
    if($SamePackage){
        Assert-ReleaseSelectedImagesLoaded
        Assert-RemoteActualApplicationImages
        Assert-RemoteRuntimeEnvImageTag
    }
}

function Test-ReleaseDeploymentAlreadyCommitted {
    $state=Read-ReleaseDeploymentState -Root "$RemoteAppDir/.release-state/$Environment" -Scope (Get-ReleaseCurrentDeploymentScope) -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c}
    if($state.gate.state -ceq 'COMMITTED'){
        Assert-ReleaseDeploymentCompletionEvidence -State $state
        $sameTag=$state.operation.binding.releaseTag -ceq $ReleaseTag
        $samePackage=$sameTag -and $state.operation.binding.packageDigest -ceq $releasePackageIntegrity.packageDigest -and $state.operation.binding.manifestDigest -ceq $releasePackageIntegrity.manifestDigest
        if($sameTag -and -not $samePackage){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETED_PACKAGE_MISMATCH'}
        Assert-ReleaseCommittedRuntime -State $state -SamePackage:$samePackage
        # Re-read the authority after observing runtime facts. Do not report a
        # stale completion if another attempt changed the gate during reads.
        $fresh=Read-ReleaseDeploymentState -Root "$RemoteAppDir/.release-state/$Environment" -Scope $state.gate.scope -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c}
        if($fresh.gateDigest -cne $state.gateDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_GATE_DRIFT'}
        Assert-ReleaseDeploymentCompletionEvidence -State $fresh
        $script:DeploymentState=$fresh
        return $samePackage
    }
    if($state.gate.state -ceq 'ZERO_WRITE_FAILED'){Assert-ReleaseDeploymentCompletionEvidence -State $state}
    Assert-ReleaseDeploymentGate -State $state -CompletionVerified:($state.gate.state -ceq 'ZERO_WRITE_FAILED')
    return $false
}

function Get-ReleaseDeploymentScope {
    $plan=Read-ReleasePreflightPlan
    return [pscustomobject]@{environment=$Environment;host=[string]$plan.binding.hostIdentity.host;machineId=[string]$plan.binding.hostIdentity.machineId;database=[string]$plan.binding.databaseIdentity.name;serverUuid=[string]$plan.binding.databaseIdentity.serverUuid}
}

function Get-ReleaseDeploymentFenceCommand {
    param([string[]]$Statuses=@('RUNNING'))
    $op=$script:DeploymentOperation
    if($null -eq $op){throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_REQUIRED'}
    foreach($status in $Statuses){if($status -cnotin @('RUNNING','FAILED','APPLIED')){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LOCK_STATUS_INVALID'}}
    $states=($Statuses|ForEach-Object{"'$_'"}) -join ','
    $binding=$op.binding
    $command=Get-ReleaseTargetMySqlCommand
    return @"
$command <<'EVIDENCE_SQL'
SELECT CASE WHEN COUNT(*)=1 AND @@server_uuid='$($binding.scope.serverUuid)' AND DATABASE()='$($binding.scope.database)' THEN 'EVIDENCE_FENCE_OK' ELSE 'EVIDENCE_FENCE_LOST' END FROM infra_release_operation_lock WHERE target_environment='$Environment' AND operation_id='$($binding.lockOperationId)' AND release_tag='$($binding.releaseTag)' AND SHA2(lease_token,256)='$($binding.leaseTokenDigest)' AND status IN ($states);
EVIDENCE_SQL
"@
}

function Assert-ReleasePersistentDeploymentGate {
    param([switch]$Verify)
    $scope=Get-ReleaseDeploymentScope
    $root="$RemoteAppDir/.release-state/$Environment"
    $state=Read-ReleaseDeploymentState -Root $root -Scope $scope -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c}
    if($Verify) {
        if($null -eq $script:DeploymentGateBeforeLock -or $state.gateDigest -cne $script:DeploymentGateBeforeLock.gateDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LOCKED_GATE_DRIFT'}
        Assert-ReleaseOperationLockOwnership
        Assert-ReleaseDeploymentGate -State $state -CompletionVerified:($state.gate.state -cin @('COMMITTED','ZERO_WRITE_FAILED'))
    } else {
        if($state.gate.state -cin @('COMMITTED','ZERO_WRITE_FAILED')){Assert-ReleaseDeploymentCompletionEvidence -State $state}
        Assert-ReleaseDeploymentGate -State $state -CompletionVerified:($state.gate.state -cin @('COMMITTED','ZERO_WRITE_FAILED'))
        $script:DeploymentGateBeforeLock=$state
    }
    $script:DeploymentState=$state
}

function Initialize-ReleaseDeploymentEvidence {
    $plan=Read-ReleasePreflightPlan
    $before=Get-ReleaseDeploymentFailureObservation
    $script:DeploymentOperation=New-ReleaseDeploymentOperation -Scope (Get-ReleaseDeploymentScope) -LockOperationId "$Environment-$ReleaseTag" -ReleaseTag $ReleaseTag -LeaseToken $script:ReleaseOperationLeaseToken -PackageDigest $releasePackageIntegrity.packageDigest -ManifestDigest $releasePackageIntegrity.manifestDigest -PlanDigest $plan.planDigest -Before $before -Target @{imageTag=$packageDirectoryName;verifiedImageContent=$script:ReleaseVerifiedImageContent}
    $script:DeploymentState=Save-ReleaseDeploymentState -Root "$RemoteAppDir/.release-state/$Environment" -State $script:DeploymentState -Operation $script:DeploymentOperation -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c} -FenceCommand (Get-ReleaseDeploymentFenceCommand) -Create
    $script:DeploymentOperation=$script:DeploymentState.operation
}

function Save-CurrentReleaseDeploymentEvidence {
    param([string[]]$LockStatuses=@('RUNNING'))
    $script:DeploymentState=Save-ReleaseDeploymentState -Root "$RemoteAppDir/.release-state/$Environment" -State $script:DeploymentState -Operation $script:DeploymentOperation -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c} -FenceCommand (Get-ReleaseDeploymentFenceCommand -Statuses $LockStatuses)
    $script:DeploymentOperation=$script:DeploymentState.operation
}

function Start-ReleaseDeploymentPhase {
    param([string]$Name,[switch]$Finalizing)
    if($null -eq $script:DeploymentOperation){throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_REQUIRED'}
    $script:DeploymentOperation.state=if($Finalizing){'FINALIZING'}else{'STARTED'}
    $script:DeploymentOperation.phase=$Name
    $script:DeploymentOperation.writeAttempted=$true
    $script:DeploymentOperation.phases+= [pscustomobject]@{name=$Name;status='STARTED';startedAt=(Get-Date).ToUniversalTime().ToString('o');completedAt=$null}
    Save-CurrentReleaseDeploymentEvidence
}

function Complete-ReleaseDeploymentPhase {
    param([string[]]$LockStatuses=@('RUNNING'))
    $phase=@($script:DeploymentOperation.phases)[-1]
    $phase.status='COMPLETED';$phase.completedAt=(Get-Date).ToUniversalTime().ToString('o')
    $script:DeploymentOperation.verification=$script:ReleaseRuntimeVerification
    Save-CurrentReleaseDeploymentEvidence -LockStatuses $LockStatuses
}

function Get-ReleaseDeploymentFailureObservation {
    param([AllowEmptyCollection()][string[]]$ComponentNames)
    if($PSBoundParameters.ContainsKey('ComponentNames')){
        if($ComponentNames.Count -lt 2 -or @($ComponentNames|Select-Object -Unique).Count -ne $ComponentNames.Count -or @($ComponentNames|Where-Object{$_ -cnotin @('backend','frontend','website','onlyoffice')}).Count -or $ComponentNames -cnotcontains 'backend' -or $ComponentNames -cnotcontains 'frontend'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_OBSERVATION_COMPONENTS_INVALID'}
    }else{$ComponentNames=@($script:ReleaseVerifiedImageContent|Where-Object{$_.name -cne 'scheduler-smoke'}|ForEach-Object{[string]$_.name})}
    $images=@();$errors=@();$database=$null;$config=$null
    foreach($component in $ComponentNames) {
        try {
            $r=Invoke-SshCapture -IgnoreExitCode -Command "docker container inspect --format '{{.Image}}' 'intruoyi-$component'"
            if(-not $r.Ok -or ([string]$r.Output).Trim() -cnotmatch '^sha256:[0-9a-f]{64}$'){throw 'image observation unavailable'}
            $images+=[pscustomobject]@{name=$component;status='observed';imageId=([string]$r.Output).Trim()}
        }catch{$images+=[pscustomobject]@{name=$component;status='unknown';imageId=$null};$errors+=Protect-ReleaseSensitiveText $_.Exception.Message}
    }
    try {$db=Get-ReleaseTargetDatabaseSnapshot;$database=@{status='observed';databaseIdentity=$db.databaseIdentity;migrationLedger=$db.migrationLedger;schemaDigest=(Get-DeploymentEvidenceDigest ([Text.Encoding]::UTF8.GetBytes(($db.schemaEvidence|ConvertTo-Json -Depth 50 -Compress))))}}
    catch{$database=@{status='unknown'};$errors+=Protect-ReleaseSensitiveText $_.Exception.Message}
    try {
        $envMap=Get-RemoteRuntimeEnvMap
        $required=@('IMAGE_TAG','MYSQL_DATABASE','EDHR_S3_ENDPOINT','EDHR_S3_BUCKET','EDHR_S3_REGION','BACKEND_HOST_PORT','FRONTEND_HOST_PORT')
        if($ComponentNames -ccontains 'website'){$required+='WEBSITE_HOST_PORT'}
        if($ComponentNames -ccontains 'onlyoffice'){$required+='ONLYOFFICE_HOST_PORT'}
        foreach($key in $required){if(-not $envMap.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$envMap[$key])){throw "Formal runtime configuration observation missing required key: $key"}}
        $values=[ordered]@{}
        foreach($key in @('IMAGE_TAG','MYSQL_DATABASE','EDHR_S3_ENDPOINT','EDHR_S3_BUCKET','EDHR_S3_REGION','BACKEND_HOST_PORT','FRONTEND_HOST_PORT','WEBSITE_HOST_PORT','ONLYOFFICE_HOST_PORT')) {
            if($envMap.ContainsKey($key)){
                if($key -ceq 'EDHR_S3_ENDPOINT'){
                    $uri=$null
                    if(-not [Uri]::TryCreate([string]$envMap[$key],[UriKind]::Absolute,[ref]$uri) -or $uri.Scheme -cnotin @('http','https') -or $uri.UserInfo -or $uri.Query -or $uri.Fragment){throw 'Endpoint observation refused: credentials or non-endpoint URL components are not persistable'}
                }
                $values[$key]=$envMap[$key]
            }
        }
        $config=@{status='observed';values=$values}
    }catch{$config=@{status='unknown';values=$null};$errors+=Protect-ReleaseSensitiveText $_.Exception.Message}
    return @{images=$images;database=$database;config=$config;errors=$errors}
}

function Register-ReleaseDeploymentFailure {
    param([string]$OriginalError)
    $safe=Protect-ReleaseSensitiveText $OriginalError
    if($null -ne $script:DeploymentOperation) {
        try {
            $fresh=Read-ReleaseDeploymentState -Root "$RemoteAppDir/.release-state/$Environment" -Scope $script:DeploymentOperation.binding.scope -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c}
            if($fresh.gate.state -ceq 'COMMITTED') {
                Assert-ReleaseDeploymentCompletionEvidence -State $fresh
                Write-Host '[FAIL] Deployment commit exists but caller acknowledgement failed; do not replay.'
                return
            }
            if($fresh.gate.attemptId -cne $script:DeploymentOperation.attemptId){throw 'RELEASE_DEPLOYMENT_EVIDENCE_FAILURE_ATTEMPT_MISMATCH'}
            $script:DeploymentState=$fresh;$script:DeploymentOperation=$fresh.operation
            $script:DeploymentOperation.originalError=$safe
            $script:DeploymentOperation.state=if($script:DeploymentOperation.writeAttempted){'RECOVERY_REQUIRED'}else{'PREPARED'}
            $observation=Get-ReleaseDeploymentFailureObservation
            $script:DeploymentOperation.observation=$observation
            $script:DeploymentOperation.observationErrors=@($script:ReleaseMigrationFailureErrors)+@($observation.errors)
            $script:DeploymentOperation.finalizationErrors=@($script:DeploymentOperation.finalizationErrors)+@($script:ReleaseHistoryFailureErrors)
            Save-CurrentReleaseDeploymentEvidence -LockStatuses @('RUNNING','FAILED','APPLIED')
        }catch{Write-Host ('[FAIL] Persistent deployment failure observation unavailable: '+(Protect-ReleaseSensitiveText $_.Exception.Message))}
    }
    if($script:ReleaseOperationLockHeld) {
        try {
            Invoke-ReleaseOperationLockRelease -Status 'FAILED' -ErrorMessage $safe
            if($null -ne $script:DeploymentOperation -and -not $script:DeploymentOperation.writeAttempted){
                $script:DeploymentOperation.state='ZERO_WRITE_FAILED'
                Save-CurrentReleaseDeploymentEvidence -LockStatuses @('FAILED')
            }
        }
        catch {
            $cleanup=Protect-ReleaseSensitiveText $_.Exception.Message
            Write-Host "[FAIL] Release operation lock cleanup failed: $cleanup"
            if($null -ne $script:DeploymentOperation) {
                try {$script:DeploymentOperation.finalizationErrors+= $cleanup;Save-CurrentReleaseDeploymentEvidence -LockStatuses @('RUNNING','FAILED','APPLIED')}
                catch{Write-Host ('[FAIL] Lock failure evidence update unavailable: '+(Protect-ReleaseSensitiveText $_.Exception.Message))}
            }
        }
    }
}

function Remove-ReleaseDeploymentTemporaryFiles {
    Start-ReleaseDeploymentPhase -Name 'cleanup-local' -Finalizing
    if(Test-Path -LiteralPath $deployControlLocalRoot){Remove-Item -LiteralPath $deployControlLocalRoot -Recurse -Force -ErrorAction Stop}
    if(Test-Path -LiteralPath $deployControlLocalRoot){throw 'RELEASE_DEPLOYMENT_LOCAL_CLEANUP_NOT_CONFIRMED'}
    Complete-ReleaseDeploymentPhase
    Start-ReleaseDeploymentPhase -Name 'cleanup-remote' -Finalizing
    $files=@($remoteImageTar,$remoteDbDump,$remoteResetDbSql,$remotePostImportSql)
    $literal=Join-ShellQuotedPathList -Paths $files
    Invoke-SshCommand "set -eu`nrm -f -- $literal`nfor file in $literal; do test ! -e `"`$file`"; done"
    $directories=@()
    if($publishBackend){$directories+=$remoteRequiredSqlDir}
    if($publishWebsite){$directories+=$remoteWebsitePreviousDir}
    if($directories.Count){$quoted=Join-ShellQuotedPathList -Paths $directories;Invoke-SshCommand "set -eu`nrm -rf -- $quoted`nfor directory in $quoted; do test ! -e `"`$directory`"; done"}
    Complete-ReleaseDeploymentPhase
}

function Complete-ReleaseDeployment {
    Start-ReleaseDeploymentPhase -Name 'finalizing' -Finalizing
    $finalRuntime=Get-ReleaseDeploymentFailureObservation
    if(@($finalRuntime.errors).Count){throw 'RELEASE_DEPLOYMENT_EVIDENCE_FINAL_OBSERVATION_UNAVAILABLE'}
    Remove-ReleaseDeploymentTemporaryFiles
    if($Environment -cin @('prod','backup')) {
        # The history writer persists phases and replaces the current operation.
        # Bind its returned proof only after that replacement has completed.
        $history=Write-NasReleaseDeploymentHistory -PackageTag $ReleaseTag -HistoryAction deploy -HistoryEnvironment $Environment
        $script:DeploymentOperation.history=$history
    } else {
        Start-ReleaseDeploymentPhase -Name 'history-not-required' -Finalizing
        $script:DeploymentOperation.history=@{status='not-required';environment='test'}
        Complete-ReleaseDeploymentPhase
    }
    Start-ReleaseDeploymentPhase -Name 'receipt' -Finalizing
    $receipt=[ordered]@{schemaVersion='release-deployment-receipt/v1';attemptId=$script:DeploymentOperation.attemptId;binding=$script:DeploymentOperation.binding;verification=$script:ReleaseRuntimeVerification;runtime=$finalRuntime;history=$script:DeploymentOperation.history;createdAt=(Get-Date).ToUniversalTime().ToString('o')}
    $script:DeploymentOperation.receiptDigest=Write-ReleaseDeploymentReceipt -Root "$RemoteAppDir/.release-state/$Environment" -State $script:DeploymentState -Receipt $receipt -Capture {param($c) Invoke-SshCapture -IgnoreExitCode -Command $c} -FenceCommand (Get-ReleaseDeploymentFenceCommand)
    Complete-ReleaseDeploymentPhase
    Start-ReleaseDeploymentPhase -Name 'lock-applied' -Finalizing
    Assert-ReleaseOperationLockOwnership
    Invoke-ReleaseOperationLockRelease -Status APPLIED
    Assert-ReleaseDeploymentCompletionEvidence -State $script:DeploymentState -BeforeCommit
    $script:DeploymentOperation.completion=@{lockApplied=$true;historyVerified=$true;cleanupVerified=$true;completedAt=(Get-Date).ToUniversalTime().ToString('o')}
    Complete-ReleaseDeploymentPhase -LockStatuses @('APPLIED')
    $script:DeploymentOperation.state='COMMITTED';$script:DeploymentOperation.phase='complete'
    Save-CurrentReleaseDeploymentEvidence -LockStatuses @('APPLIED')
}

function Assert-ReleaseDeploymentCompletionEvidence {
    param($State,[switch]$BeforeCommit)
    $saved=$script:DeploymentOperation
    try {
        $script:DeploymentOperation=$State.operation
        $statuses=if($State.gate.state -ceq 'ZERO_WRITE_FAILED'){@('FAILED')}else{@('APPLIED')}
        $r=Invoke-SshCapture -IgnoreExitCode -Command (Get-ReleaseDeploymentFenceCommand -Statuses $statuses)
        if(-not $r.Ok -or ([string]$r.Output).Trim() -cne 'EVIDENCE_FENCE_OK'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LOCK_COMPLETION_NOT_CONFIRMED'}
        if($State.gate.state -ceq 'ZERO_WRITE_FAILED') {
            if($State.operation.writeAttempted){throw 'RELEASE_DEPLOYMENT_EVIDENCE_ZERO_WRITE_INVALID'}
            return
        }
        if($null -eq $State.receipt){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_REQUIRED'}
        if($State.operation.binding.scope.environment -cin @('prod','backup')){
            $history=$State.receipt.history
            if($null -eq $history -or $history.environment -cne $State.operation.binding.scope.environment -or
               $history.packageTag -cne $State.operation.binding.releaseTag -or $history.historyFile -cne ($State.operation.attemptId+'.json')){throw 'RELEASE_DEPLOYMENT_EVIDENCE_HISTORY_BINDING_MISMATCH'}
            Assert-NasReleaseDeploymentHistoryEvidence -History $history
        }
        elseif($State.receipt.history.status -cne 'not-required'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_HISTORY_INVALID'}
    }finally{$script:DeploymentOperation=$saved}
}

function Read-ReleasePreflightPlan {
    $preflightPlanPath = Join-Path $deployControlLocalRoot 'preflight-plan.json'
    if (-not (Test-Path -LiteralPath $preflightPlanPath -PathType Leaf)) {
        Fail "preflight-plan.json missing in deploy control directory; generate target-bound preflight plan before deploy-release: $preflightPlanPath"
    }
    try {
        $plan = [System.IO.File]::ReadAllText($preflightPlanPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    } catch {
        Fail "preflight-plan.json parse failed: $($_.Exception.Message)"
    }
    if ([string]$plan.schemaVersion -ne 'release-deploy-plan/v1' -or [string]$plan.planKind -ne 'deploy' -or
        $null -eq $plan.binding -or [string]::IsNullOrWhiteSpace([string]$plan.planDigest)) {
        Fail 'TARGET_BOUND_PLAN_REQUIRED: deployment requires a verified target-bound plan'
    }
    if ([string]$plan.publishScope -ne $releasePublishScope) {
        Fail "preflight-plan.json publishScope does not match release package: $($plan.publishScope) != $releasePublishScope"
    }
    if ([string]$plan.status -ne 'passed') {
        Fail "preflight-plan.json status must be passed before deploy-release: $($plan.status)"
    }
    foreach ($item in @($plan.items)) {
        $action = [string]$item.action
        if ($action.StartsWith('BLOCKED_')) {
            Fail "preflight-plan.json contains blocked migration: $($item.migrationId) -> $action"
        }
        if ($action -notin @('APPLY', 'SKIP_ALREADY_APPLIED', 'SKIP_ENV_NOT_ALLOWED', 'SKIP_SCOPE_EXCLUDED', 'SKIP_IMMUTABLE')) {
            Fail "preflight-plan.json contains unsupported migration action: $($item.migrationId) -> $action"
        }
    }
    return $plan
}

function Get-ReleaseTargetMySqlCommand {
    param([string]$DatabaseName = $script:TargetMySqlDatabase)
    if ($DatabaseName -notmatch '^[A-Za-z0-9_-]{1,64}$') {
        Fail 'TARGET_DATABASE_CONFIG_INVALID: MYSQL_DATABASE must be explicitly configured'
    }
    # The credential is expanded only inside the existing target container.
    return ('docker exec -i intruoyi-mysql sh -lc ''MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql --protocol=TCP -h127.0.0.1 -uroot --default-character-set=utf8mb4 --binary-mode --batch --raw --skip-column-names "$1"'' sh ''' + $DatabaseName + '''')
}

function Assert-ReleaseExecutorSourceBinding {
    param([Parameter(Mandatory = $true)]$PackageIntegrity)
    $roots = @($PackageIntegrity.sourceRoots | Where-Object { $_.rootRole -ceq 'maintenance' })
    if ($roots.Count -ne 1 -or $roots[0].approvedCommit -cne $roots[0].commit) {
        Fail 'RELEASE_EXECUTOR_SOURCE_INVALID: package maintenance source binding is missing'
    }
    $maintenanceRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir '..\..')).Path
    $head = Invoke-ProcessCapture -FilePath 'git' -ArgumentList @('-C', $maintenanceRoot, 'rev-parse', 'HEAD')
    if ($head.ExitCode -ne 0 -or $head.StdOut.Trim() -cne $roots[0].approvedCommit) {
        Fail "RELEASE_EXECUTOR_SOURCE_MISMATCH: HEAD=$($head.StdOut.Trim()); package=$($roots[0].approvedCommit)"
    }
    $status = Invoke-ProcessCapture -FilePath 'git' -ArgumentList @('-C', $maintenanceRoot, 'status', '--porcelain', '--untracked-files=all', '--', 'ops/deploy', 'ops/release')
    if ($status.ExitCode -ne 0 -or -not [string]::IsNullOrWhiteSpace($status.StdOut)) {
        Fail 'RELEASE_EXECUTOR_SOURCE_DIRTY: tracked or untracked maintenance toolchain changes must be committed and packaged'
    }
    # Git-ignored executable source can shadow an import too. Only interpreter
    # caches are excluded; ignored source is never treated as approved code.
    $ignored = Invoke-ProcessCapture -FilePath 'git' -ArgumentList @('-C', $maintenanceRoot, 'ls-files', '--others', '--ignored', '--exclude-standard', '--', 'ops/deploy', 'ops/release')
    if ($ignored.ExitCode -ne 0) { Fail 'RELEASE_EXECUTOR_SOURCE_CHECK_FAILED: cannot inventory ignored toolchain files' }
    foreach ($relative in ($ignored.StdOut -split "`r?`n")) {
        if ($relative -match '(^|/)__pycache__/' -and $relative -match '\.pyc$') { continue }
        if ($relative -match '\.(ps1|psm1|psd1|py|pyw|pyc|pyd|dll|exe|so|sh|bat|cmd|js|mjs|cjs)$') {
            Fail "RELEASE_EXECUTOR_SOURCE_DIRTY: ignored executable source $relative"
        }
    }
}

function Get-ReleaseTargetImageIdentities {
    $names = @('backend','frontend','scheduler-smoke')
    if ($publishWebsite) { $names += 'website' }
    if ($IncludeOnlyOffice) { $names += 'onlyoffice' }
    $images = @($script:ReleaseVerifiedImageContent)
    if ($images.Count -ne $names.Count -or @($script:ReleaseRuntimeImages).Count -ne $names.Count) {
        Fail 'RELEASE_IMAGE_IDENTITY_REQUIRED: complete verified image content is required'
    }
    foreach ($name in $names) {
        $items = @($images | Where-Object { $_.name -ceq $name })
        $build = @($script:ReleaseRuntimeImages | Where-Object { $_.name -ceq $name })
        if ($items.Count -ne 1 -or $build.Count -ne 1 -or $items[0].configDigest -cnotmatch '^sha256:[0-9a-f]{64}$' -or
            $items[0].reference -cne $build[0].reference -or $items[0].buildImageId -cne $build[0].id) {
            Fail "RELEASE_IMAGE_IDENTITY_REQUIRED: invalid verified content for $name"
        }
        $items[0]
    }
}

function Assert-ReleaseSelectedImagesLoaded {
    $images = @(Get-ReleaseTargetImageIdentities)
    # This release contract supports classic overlay2 only. A descriptor is a
    # build identity; it is never an alternative accepted target image ID.
    $platform = Invoke-SshCapture -IgnoreExitCode -Command "docker info --format '{{.OSType}}|{{.Architecture}}|{{.Driver}}'"
    $facts = @(([string]$platform.Output).Trim() -split '\|')
    if (-not $platform.Ok -or $facts.Count -ne 3 -or $facts[2] -cne 'overlay2') { Fail 'RELEASE_TARGET_IMAGE_STORE_UNSUPPORTED: classic overlay2 is required' }
    $architecture = $facts[1]
    # Docker daemon uses the uname spelling; OCI config uses the canonical name.
    if ($architecture -ceq 'x86_64') { $architecture = 'amd64' }
    if ($architecture -ceq 'aarch64') { $architecture = 'arm64' }
    $script:ReleaseRuntimeVerification.loadedImages = @()
    foreach ($image in $images) {
        if ($image.platform.os -cne $facts[0] -or $image.platform.architecture -cne $architecture) {
            Fail "RELEASE_TARGET_IMAGE_PLATFORM_MISMATCH: $($image.name); archive platform differs from the target daemon"
        }
        $reference = ConvertTo-ShellSingleQuotedLiteral -Value ([string]$image.reference) -Purpose 'packaged image reference'
        $capture = Invoke-SshCapture -IgnoreExitCode -Command "docker image inspect --format '{{.Id}}' $reference"
        $actual = if ($capture.Ok) { ([string]$capture.Output).Trim() } else { $null }
        $matched = $capture.Ok -and $actual -ceq $image.configDigest
        $script:ReleaseRuntimeVerification.loadedImages += [pscustomobject][ordered]@{
            name=$image.name; reference=$image.reference; buildImageId=$image.buildImageId
            expectedImageId=$image.configDigest; actualImageId=$actual; matched=$matched
        }
        if (-not $matched) {
            Fail "RELEASE_IMAGE_NOT_LOADED: $($image.name); load and verify the complete package image archive before application start"
        }
    }
}

function Get-ReleaseTargetSchemaCollectionSql {
    if ($Environment -notin @('test', 'prod', 'backup')) { Fail 'TARGET_ENVIRONMENT_INVALID' }
    $sections = @(
        @{ name='tables'; source='TABLES'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME'; fields="'name',TABLE_NAME,'type',TABLE_TYPE,'engine',ENGINE,'collation',TABLE_COLLATION,'options',CREATE_OPTIONS" },
        @{ name='columns'; source='COLUMNS'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME,ORDINAL_POSITION'; fields="'table',TABLE_NAME,'name',COLUMN_NAME,'position',ORDINAL_POSITION,'type',COLUMN_TYPE,'nullable',IS_NULLABLE,'default',COLUMN_DEFAULT,'charset',CHARACTER_SET_NAME,'collation',COLLATION_NAME,'extra',EXTRA,'expression',GENERATION_EXPRESSION" },
        @{ name='indexes'; source='STATISTICS'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX'; fields="'table',TABLE_NAME,'name',INDEX_NAME,'position',SEQ_IN_INDEX,'column',COLUMN_NAME,'unique',NON_UNIQUE,'subPart',SUB_PART,'type',INDEX_TYPE,'visible',IS_VISIBLE,'expression',EXPRESSION" },
        @{ name='constraints'; source='TABLE_CONSTRAINTS'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME,CONSTRAINT_NAME'; fields="'table',TABLE_NAME,'name',CONSTRAINT_NAME,'type',CONSTRAINT_TYPE,'enforced',ENFORCED" },
        @{ name='foreignKeys'; source='KEY_COLUMN_USAGE'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME,CONSTRAINT_NAME,ORDINAL_POSITION'; fields="'table',TABLE_NAME,'constraint',CONSTRAINT_NAME,'column',COLUMN_NAME,'position',ORDINAL_POSITION,'referencedTable',REFERENCED_TABLE_NAME,'referencedColumn',REFERENCED_COLUMN_NAME" },
        @{ name='checks'; source='CHECK_CONSTRAINTS'; filter='CONSTRAINT_SCHEMA = DATABASE()'; order='CONSTRAINT_NAME'; fields="'name',CONSTRAINT_NAME,'clause',CHECK_CLAUSE" },
        @{ name='routines'; source='ROUTINES'; filter='ROUTINE_SCHEMA = DATABASE()'; order='ROUTINE_NAME,ROUTINE_TYPE'; fields="'name',ROUTINE_NAME,'type',ROUTINE_TYPE,'definition',ROUTINE_DEFINITION,'dataType',DTD_IDENTIFIER,'deterministic',IS_DETERMINISTIC,'access',SQL_DATA_ACCESS,'security',SECURITY_TYPE,'sqlMode',SQL_MODE" },
        @{ name='triggers'; source='TRIGGERS'; filter='TRIGGER_SCHEMA = DATABASE()'; order='TRIGGER_NAME'; fields="'name',TRIGGER_NAME,'table',EVENT_OBJECT_TABLE,'event',EVENT_MANIPULATION,'timing',ACTION_TIMING,'order',ACTION_ORDER,'statement',ACTION_STATEMENT,'sqlMode',SQL_MODE" },
        @{ name='views'; source='VIEWS'; filter='TABLE_SCHEMA = DATABASE()'; order='TABLE_NAME'; fields="'name',TABLE_NAME,'definition',VIEW_DEFINITION,'checkOption',CHECK_OPTION,'security',SECURITY_TYPE" }
    )
    $sql = @(
        'SET SESSION TRANSACTION READ ONLY;',
        'START TRANSACTION READ ONLY;',
        "SELECT CONCAT('identity', CHAR(9), JSON_OBJECT('name',DATABASE(),'serverUuid',@@server_uuid));"
    )
    foreach ($section in $sections) {
        $sql += "SELECT CONCAT('count:$($section.name)', CHAR(9), COUNT(*)) FROM information_schema.$($section.source) WHERE $($section.filter);"
        $sql += "SELECT CONCAT('$($section.name)', CHAR(9), JSON_OBJECT($($section.fields))) FROM information_schema.$($section.source) WHERE $($section.filter) ORDER BY $($section.order);"
    }
    $sql += "SELECT CONCAT('count:ledger',CHAR(9),COUNT(*)) FROM infra_release_migration WHERE target_environment='$Environment';"
    $sql += "SELECT CONCAT('ledger',CHAR(9),JSON_OBJECT('migrationId',migration_id,'sha256',sha256,'status',status,'releaseTag',release_tag,'file',file_name,'operationId',operation_id,'startedAt',DATE_FORMAT(started_at,'%Y-%m-%dT%H:%i:%sZ'),'finishedAt',DATE_FORMAT(finished_at,'%Y-%m-%dT%H:%i:%sZ'))) FROM infra_release_migration WHERE target_environment='$Environment' ORDER BY migration_id,id;"
    $sql += @('ROLLBACK;', "SELECT 'COLLECTION_COMPLETE';")
    return $sql -join "`n"
}

function Get-ReleaseTargetDatabaseSnapshot {
    $mysqlCommand = Get-ReleaseTargetMySqlCommand
    $sql = Get-ReleaseTargetSchemaCollectionSql
    $capture = Invoke-SshCapture -IgnoreExitCode -Command "cat <<'RELEASE_SQL' | $mysqlCommand`n$sql`nRELEASE_SQL"
    if (-not $capture.Ok) { Fail 'TARGET_SCHEMA_COLLECTION_FAILED: read-only MySQL collection failed' }
    $sections = @{}
    $counts = @{}
    $identity = $null
    $complete = 0
    foreach ($line in ([string]$capture.Output -split "`r?`n")) {
        if ($line -eq 'COLLECTION_COMPLETE') { $complete++; continue }
        $pair = $line.Split([char]9, 2)
        if ($pair.Count -ne 2) { Fail 'TARGET_SCHEMA_COLLECTION_INVALID: malformed or truncated evidence' }
        if ($pair[0].StartsWith('count:')) {
            $key = $pair[0].Substring(6)
            if ($counts.ContainsKey($key) -or $pair[1] -notmatch '^\d+$') { Fail 'TARGET_SCHEMA_COLLECTION_INVALID: duplicate/invalid row count' }
            $counts[$key] = [int64]$pair[1]
            $sections[$key] = @()
        } elseif ($pair[0] -eq 'identity') {
            if ($null -ne $identity) { Fail 'TARGET_SCHEMA_COLLECTION_INVALID: duplicate database identity' }
            $identity = $pair[1] | ConvertFrom-Json
        } else {
            if (-not $sections.ContainsKey($pair[0])) { Fail 'TARGET_SCHEMA_COLLECTION_INVALID: undeclared evidence section' }
            $sections[$pair[0]] += ($pair[1] | ConvertFrom-Json)
        }
    }
    $expectedSections = @('tables','columns','indexes','constraints','foreignKeys','checks','routines','triggers','views','ledger')
    if ($complete -ne 1 -or $null -eq $identity -or $counts.Count -ne $expectedSections.Count) { Fail 'TARGET_SCHEMA_COLLECTION_INCOMPLETE' }
    foreach ($key in $expectedSections) {
        if (-not $counts.ContainsKey($key) -or $sections[$key].Count -ne $counts[$key]) { Fail "TARGET_SCHEMA_COLLECTION_INCOMPLETE: $key" }
    }
    $schema = [ordered]@{}
    foreach ($key in $expectedSections) { if ($key -ne 'ledger') { $schema[$key] = @($sections[$key]) } }
    return @{ databaseIdentity=$identity; schemaEvidence=$schema; migrationLedger=@($sections['ledger']) }
}

function Assert-ReleaseTargetControlSchema {
    param([Parameter(Mandatory = $true)]$DatabaseSnapshot)
    $schema = $DatabaseSnapshot.schemaEvidence
    $requiredColumns = @{
        infra_release_migration=@('id','release_tag','migration_id','file_name','sha256','target_environment','status','started_at','finished_at','error_message','operation_id','creator','create_time','updater','update_time','deleted','tenant_id')
        infra_release_operation_lock=@('id','target_environment','operation_id','release_tag','status','started_at','finished_at','error_message','creator','create_time','updater','update_time','deleted','tenant_id','executor_host','executor_pid','executor_identity','lease_token','heartbeat_at','write_fence')
    }
    foreach ($table in $requiredColumns.Keys) {
        $present = @($schema.columns | Where-Object { $_.table -ceq $table } | ForEach-Object { $_.name })
        foreach ($column in $requiredColumns[$table]) {
            if ($present -cnotcontains $column) { Fail "RELEASE_CONTROL_SCHEMA_NOT_READY: $table.$column; run approved platform preparation separately" }
        }
    }
    foreach ($entry in @(@{table='infra_release_operation_lock';columns='target_environment'}, @{table='infra_release_migration';columns='target_environment,migration_id'})) {
        $valid = $false
        foreach ($index in @($schema.indexes | Where-Object { $_.table -ceq $entry.table -and $_.unique -eq 0 } | Group-Object name)) {
            if ((@($index.Group | Sort-Object position | ForEach-Object { $_.column }) -join ',') -ceq $entry.columns) { $valid=$true }
        }
        if (-not $valid) { Fail "RELEASE_CONTROL_SCHEMA_NOT_READY: $($entry.table) unique ownership index" }
    }
}

function ConvertTo-ReleaseCapacityInteger {
    param($Value, [string]$Label, [switch]$Positive)
    $types = @([byte], [sbyte], [int16], [uint16], [int32], [uint32], [int64], [uint64])
    if ($null -eq $Value -or $types -cnotcontains $Value.GetType() -or
        [decimal]$Value -lt 0 -or [decimal]$Value -gt [int64]::MaxValue -or
        ($Positive -and [decimal]$Value -eq 0)) {
        Fail "TARGET_CAPACITY_INPUT_INVALID: $Label must be an in-range integer"
    }
    return [decimal]$Value
}

function Read-ReleaseArchiveCapacity {
    # Read members without extracting or following links on the host. Stdin and
    # the existing argument-array transport preserve Windows paths and Unicode.
    $reader = @'
import collections, json, posixpath, sys, tarfile

def safe_path(value):
    if not isinstance(value, str) or not value or chr(0) in value:
        raise ValueError('invalid archive path')
    normalized = posixpath.normpath(value)
    if normalized.startswith('/') or normalized == '..' or normalized.startswith('../'):
        raise ValueError('archive member escapes root')
    return normalized

def members(archive, image=False):
    counts, entries, directories, hardlinks = collections.Counter(), {}, set(), {}
    for member in archive:
        name = safe_path(member.name)
        if name == '.':
            continue
        if name in entries:
            raise ValueError('duplicate archive member')
        entries[name] = member
        parent = posixpath.dirname(name)
        while parent and parent != '.':
            directories.add(parent)
            parent = posixpath.dirname(parent)
        if member.isdir():
            directories.add(name)
        elif member.isfile():
            if member.size < 0:
                raise ValueError('negative member size')
            counts[max(1, member.size)] += 1
        elif member.issym():
            target = member.linkname
            if target.startswith('/'):
                if not image:
                    raise ValueError('absolute dependency symlink')
                safe_path(target.lstrip('/'))
            else:
                safe_path(posixpath.join(posixpath.dirname(name), target))
            counts[max(1, len(target.encode('utf-8')))] += 1
        elif member.islnk():
            hardlinks[name] = safe_path(member.linkname)
            counts[1] += 1
        else:
            raise ValueError('unsupported member type')
    for name, target in hardlinks.items():
        visited = {name}
        while target in hardlinks:
            if target in visited:
                raise ValueError('cyclic hardlink')
            visited.add(target)
            target = hardlinks[target]
        if target not in entries or not entries[target].isfile():
            raise ValueError('hardlink target is not a regular member')
    counts[1] += len(directories)
    return counts

def histogram(counter):
    return [{'bytes': size, 'count': count} for size, count in sorted(counter.items()) if count]

with tarfile.open(sys.argv[1], 'r:*') as archive:
    smoke = members(archive)
with tarfile.open(sys.argv[2], 'r:*') as archive:
    manifest = json.load(archive.extractfile('manifest.json'))
    docker, layers, configs = collections.Counter(), set(), set()
    for image in manifest:
        config = safe_path(image['Config'])
        if config not in configs:
            item = archive.getmember(config)
            if not item.isfile():
                raise ValueError('image config is not a file')
            docker[max(1, item.size)] += 1
            configs.add(config)
        for layer in image['Layers']:
            layer = safe_path(layer)
            if layer in layers:
                continue
            item = archive.getmember(layer)
            if not item.isfile():
                raise ValueError('image layer is not a file')
            with archive.extractfile(item) as stream:
                with tarfile.open(fileobj=stream, mode='r|*') as contents:
                    docker.update(members(contents, image=True))
            # Classic overlay2 layer directories and registration records.
            docker[1] += 8
            layers.add(layer)
print(json.dumps({'smoke': histogram(smoke), 'docker': histogram(docker)}, separators=(',', ':')))
'@
    $result = Invoke-ProcessCaptureWithInput -FilePath 'python' -ArgumentList @(
        '-X','utf8','-', (Join-Path $releaseDir 'smoke/yudao-ui-admin-vue3/dependencies.tar'),
        (Join-Path $releaseDir "intruoyi-images_$packageDirectoryName.tar")
    ) -StandardInput $reader
    if ($result.ExitCode -ne 0) { Fail ("TARGET_CAPACITY_INPUT_INVALID: archive member inspection failed: " + $result.StdErr.Trim()) }
    try { return $result.StdOut | ConvertFrom-Json } catch { Fail 'TARGET_CAPACITY_INPUT_INVALID: archive capacity evidence is invalid' }
}

function Get-ReleaseCapacityReservation {
    param([int64]$DatabaseReserveBytes = 1073741824)
    # Keep the reservation tied to the actual copy/extract lifecycle below. Existing
    # target bytes are already excluded from available space; never reclaim them here.
    $parts = @{release=@();runtime=@();ops=@();docker=@();data=@([decimal]$DatabaseReserveBytes)}
    if ($DatabaseReserveBytes -lt 1073741824) { Fail 'TARGET_CAPACITY_INPUT_INVALID: database platform reserve must be at least 1 GiB; increase it for planned migration growth' }
    $seen = @{}
    $imageArchive = "intruoyi-images_$packageDirectoryName.tar"
    $artifacts = @($releasePackageIntegrity.artifacts)
    if ($artifacts.Count -eq 0) { Fail 'TARGET_CAPACITY_INPUT_INVALID: verified artifacts are required' }
    foreach ($entry in $artifacts) {
        $path = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($path) -or $seen.ContainsKey($path)) { Fail 'TARGET_CAPACITY_INPUT_INVALID: artifact path is missing or duplicated' }
        $seen[$path] = $true
        $bytes = ConvertTo-ReleaseCapacityInteger -Value $entry.bytes -Label "artifact $path"
        # bsdtar emits a 512-byte header plus padded payload and possible PAX/name
        # records. Include every parent directory, long UTF-8 path and end padding.
        $tarMetadata = [decimal](2048 + [Text.Encoding]::UTF8.GetByteCount($path) + 512 * $path.Split('/').Count)
        if ($path -ceq $imageArchive) {
            # All chunks coexist with the merged tar; docker load later extracts
            # its import tar while registering the uncompressed image layers.
            $parts.release += @($bytes,$bytes)
            $parts.docker += $bytes
        } elseif ($path -ceq 'docker-compose.yml' -or $path.StartsWith('website/', [StringComparison]::Ordinal)) {
            $parts.release += @($bytes,$bytes,$tarMetadata)
            $parts.runtime += $bytes
        } elseif ($path.StartsWith('required-sql/', [StringComparison]::Ordinal)) {
            $parts.release += @($bytes,$bytes,$tarMetadata)
        } elseif ($path.StartsWith('ops-runtime/', [StringComparison]::Ordinal)) {
            $parts.release += @($bytes,$tarMetadata)
            $parts.ops += $bytes
        } elseif ($path.StartsWith('smoke/', [StringComparison]::Ordinal)) {
            $parts.runtime += $bytes
        }
    }
    if (-not $seen.ContainsKey($imageArchive) -or -not $seen.ContainsKey('smoke/yudao-ui-admin-vue3/dependencies.tar')) {
        Fail 'TARGET_CAPACITY_INPUT_INVALID: image/dependency archive is required'
    }
    if (@($script:ReleaseRuntimeImages).Count -eq 0) { Fail 'TARGET_CAPACITY_INPUT_INVALID: runtimeImages are required' }
    [decimal]$declaredImageBytes = 0
    foreach ($image in $script:ReleaseRuntimeImages) {
        $declaredImageBytes += ConvertTo-ReleaseCapacityInteger -Value $image.sizeBytes -Label "image $($image.name)" -Positive
        if ($declaredImageBytes -gt [int64]::MaxValue) { Fail 'TARGET_CAPACITY_INPUT_INVALID: declared image size overflow' }
    }
    $archiveMembers = Read-ReleaseArchiveCapacity
    $parts['runtimeMembers'] = @($archiveMembers.smoke)
    $parts['dockerMembers'] = @($archiveMembers.docker)
    $parts['declaredImageBytes'] = $declaredImageBytes
    $controls = @($remoteEnvLocal)
    if ($publishWebsite) { $controls += $websiteNginxLocal }
    foreach ($path in $controls) {
        if ([string]::IsNullOrWhiteSpace($path) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) { Fail 'TARGET_CAPACITY_INPUT_INVALID: rendered deployment control is missing' }
        $bytes = ConvertTo-ReleaseCapacityInteger -Value (Get-Item -LiteralPath $path).Length -Label 'rendered control' -Positive
        $parts.release += @($bytes,$bytes,[decimal]4096)
        $parts.runtime += $bytes
    }
    # Each of the three transfer archives has its own tar end padding. Keeping
    # all their reservations is conservative even though uploads are sequential.
    $parts.release += @([decimal]10240,[decimal]10240,[decimal]10240)
    foreach ($role in @('release','runtime','ops','docker','data')) {
        [decimal]$total = 0
        foreach ($bytes in $parts[$role]) { $total += $bytes }
        if ($total -gt [int64]::MaxValue) { Fail "TARGET_CAPACITY_INPUT_INVALID: $role reservation overflow" }
    }
    return $parts
}

function Assert-ReleaseTargetCapacity {
    param([int64]$DatabaseReserveBytes = 1073741824)
    $reservation = Get-ReleaseCapacityReservation -DatabaseReserveBytes $DatabaseReserveBytes
    $docker = Invoke-SshCapture -IgnoreExitCode -Command "docker info --format '{`"driver`":{{json .Driver}},`"root`":{{json .DockerRootDir}},`"status`":{{json .DriverStatus}}}'"
    if (-not $docker.Ok) { Fail 'TARGET_CAPACITY_NOT_READY: Docker storage inspection failed' }
    try { $storage = $docker.Output | ConvertFrom-Json } catch { Fail 'TARGET_CAPACITY_NOT_READY: invalid Docker storage facts' }
    # containerd image storage can be outside DockerRootDir. Only the classic
    # overlay2 layout is supported here; never guess another store's location.
    if ($storage.driver -cne 'overlay2' -or [string]::IsNullOrWhiteSpace([string]$storage.root) -or
        -not ([string]$storage.root).StartsWith('/') -or (($storage.status | ConvertTo-Json -Compress) -match 'containerd')) {
        Fail 'TARGET_CAPACITY_NOT_READY: unsupported Docker image storage; approved classic overlay2 layout is required'
    }
    $destinations = @(
        @{role='release';path=$RemoteReleaseRoot}, @{role='runtime';path=$RemoteAppDir},
        @{role='ops';path=$remoteOpsRuntimeDir}, @{role='docker';path=[string]$storage.root}, @{role='data';path=$RemoteDataRoot}
    )
    $filesystems = @{}
    foreach ($target in $destinations) {
        $path = [string]$target.path
        if ([string]::IsNullOrWhiteSpace($path) -or -not $path.StartsWith('/')) { Fail "TARGET_CAPACITY_INPUT_INVALID: $($target.role) destination" }
        $literal = ConvertTo-ShellSingleQuotedLiteral -Value $path -Purpose 'capacity destination'
        $command = @"
set -eu
# RELEASE_CAPACITY: read existing destination only; do not create or clean it.
capacity_path=$literal
test -d "`$capacity_path"
printf '%s ' "`$(stat -Lc '%d' "`$capacity_path")"
stat -f -c '%a %S' "`$capacity_path"
"@
        $capture = Invoke-SshCapture -IgnoreExitCode -Command $command
        if (-not $capture.Ok -or ([string]$capture.Output).Trim() -cnotmatch '^(\d+) (\d+) (\d+)$') { Fail "TARGET_CAPACITY_NOT_READY: invalid filesystem facts for $path" }
        $id = $Matches[1]
        [decimal]$availableBlocks = 0; [decimal]$blockSize = 0
        if (-not [decimal]::TryParse($Matches[2], [ref]$availableBlocks) -or -not [decimal]::TryParse($Matches[3], [ref]$blockSize) -or
            $blockSize -le 0 -or $blockSize -gt [int64]::MaxValue -or $availableBlocks -gt [int64]::MaxValue / $blockSize) {
            Fail "TARGET_CAPACITY_NOT_READY: invalid filesystem capacity for $path"
        }
        $available = $availableBlocks * $blockSize
        if (-not $filesystems.ContainsKey($id)) {
            $filesystems[$id] = @{fileSystemId=$id;availableBytes=[int64]$available;requiredBytes=[decimal]0;blockBytes=[int64]$blockSize;paths=@();roles=@()}
        }
        $fs = $filesystems[$id]
        if ($fs.blockBytes -ne $blockSize) { Fail "TARGET_CAPACITY_NOT_READY: inconsistent filesystem block size for $path" }
        $fs.availableBytes = [int64][Math]::Min([decimal]$fs.availableBytes,$available)
        $fs.paths += $path; $fs.roles += $target.role
        foreach ($bytes in $reservation[$target.role]) {
            $fs.requiredBytes += [Math]::Ceiling([decimal]$bytes / $blockSize) * $blockSize
            if ($fs.requiredBytes -gt [int64]::MaxValue) { Fail 'TARGET_CAPACITY_INPUT_INVALID: combined filesystem reservation overflow' }
        }
        [decimal]$expandedBytes = 0
        if ($target.role -in @('runtime','docker')) {
            foreach ($group in $reservation["$($target.role)Members"]) {
                $memberBytes = ConvertTo-ReleaseCapacityInteger -Value $group.bytes -Label 'archive member bytes' -Positive
                $memberCount = ConvertTo-ReleaseCapacityInteger -Value $group.count -Label 'archive member count' -Positive
                $expandedBytes += [Math]::Ceiling($memberBytes / $blockSize) * $blockSize * $memberCount
            }
            if ($target.role -eq 'docker') {
                $expandedBytes = [Math]::Max($expandedBytes, [Math]::Ceiling($reservation.declaredImageBytes / $blockSize) * $blockSize)
            }
        }
        $fs.requiredBytes += $expandedBytes
        if ($fs.requiredBytes -gt [int64]::MaxValue) { Fail 'TARGET_CAPACITY_INPUT_INVALID: expanded filesystem reservation overflow' }
    }
    foreach ($id in @($filesystems.Keys | Sort-Object)) {
        $fs = $filesystems[$id]
        if ($fs.availableBytes -lt $fs.requiredBytes) {
            Fail "TARGET_CAPACITY_NOT_READY: filesystem=$id paths=$($fs.paths -join ',') requiredBytes=$($fs.requiredBytes) availableBytes=$($fs.availableBytes)"
        }
    }
    foreach ($id in @($filesystems.Keys | Sort-Object)) {
        $filesystems[$id].requiredBytes = [int64]$filesystems[$id].requiredBytes
        [pscustomobject]$filesystems[$id]
    }
}

function Read-ReleaseTargetSnapshot {
    param([switch]$Verify)
    if ($publishWebsite) { Assert-ReleaseWebsiteVerificationPrerequisites }
    Assert-RemoteRuntimeDataOnDataDisk
    $freshEnv = Get-RemoteRuntimeEnvMap
    foreach ($key in @('MYSQL_DATABASE','MYSQL_ROOT_PASSWORD','IMAGE_TAG','SERVER_HOST','BACKEND_HOST_PORT','FRONTEND_HOST_PORT','EDHR_S3_ENDPOINT','EDHR_S3_BUCKET','EDHR_S3_REGION')) {
        if (-not $freshEnv.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$freshEnv[$key])) { Fail "TARGET_CONFIG_NOT_READY: $key" }
    }
    if ($freshEnv['MYSQL_DATABASE'] -notmatch '^[A-Za-z0-9_-]{1,64}$') { Fail 'TARGET_DATABASE_CONFIG_INVALID' }
    $script:TargetMySqlDatabase = [string]$freshEnv['MYSQL_DATABASE']
    $credential = Get-RemoteContainerEnvValue -ContainerName 'intruoyi-mysql' -Key 'MYSQL_ROOT_PASSWORD'
    if ([string]::IsNullOrEmpty($credential) -or $credential -cne [string]$freshEnv['MYSQL_ROOT_PASSWORD']) { Fail 'TARGET_MYSQL_CREDENTIAL_CONFIG_MISMATCH: target container and formal environment disagree' }
    if ($freshEnv['SERVER_HOST'] -cne $ServerHost) { Fail 'TARGET_HOST_CONFIG_MISMATCH: SERVER_HOST differs from requested target' }
    $controlRoot = "$RemoteAppDir/.release-state/$Environment"
    $controlLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $controlRoot -Purpose 'persistent release control root'
    $control = Invoke-SshCapture -IgnoreExitCode -Command "test -d $controlLiteral && test -w $controlLiteral && test -d $controlLiteral/operations && test -w $controlLiteral/operations && printf 'CONTROL_ROOT_READY'"
    if (-not $control.Ok -or $control.Output -ne 'CONTROL_ROOT_READY') { Fail 'RELEASE_CONTROL_ROOT_NOT_READY: complete explicit persistent-state directory preparation' }
    $machine = Invoke-SshCapture -IgnoreExitCode -Command 'cat /etc/machine-id'
    if (-not $machine.Ok -or ([string]$machine.Output).Trim() -notmatch '^[0-9a-f]{32}$') { Fail 'TARGET_MACHINE_ID_INVALID' }
    $database = Get-ReleaseTargetDatabaseSnapshot
    Assert-ReleaseTargetControlSchema -DatabaseSnapshot $database
    if ($database.databaseIdentity.name -cne $freshEnv['MYSQL_DATABASE']) { Fail 'TARGET_DATABASE_CONFIG_MISMATCH' }
    $mounts = @()
    $redisState = Invoke-SshCapture -IgnoreExitCode -Command "docker inspect --format '{{.State.Running}}' intruoyi-redis"
    if (-not $redisState.Ok -or ([string]$redisState.Output).Trim() -cne 'true') { Fail 'TARGET_PLATFORM_NOT_READY: intruoyi-redis is not running' }
    $capacity = @(Assert-ReleaseTargetCapacity -DatabaseReserveBytes $DatabaseCapacityReserveBytes)
    $script:ReleaseTargetCapacityEvidence = $capacity
    $capacityIdentity = (@($capacity | Select-Object fileSystemId,paths,roles) | ConvertTo-Json -Depth 6 -Compress)
    if ($Verify) {
        if ([string]::IsNullOrWhiteSpace($script:ReleaseTargetCapacityIdentity) -or $script:ReleaseTargetCapacityIdentity -cne $capacityIdentity) {
            Fail 'TARGET_CAPACITY_IDENTITY_DRIFT: deployment filesystem changed since the pre-lock snapshot'
        }
    } else {
        $script:ReleaseTargetCapacityIdentity = $capacityIdentity
    }
    foreach ($item in @(@{role='mysql';container='intruoyi-mysql';destination='/var/lib/mysql'}, @{role='redis';container='intruoyi-redis';destination='/data'})) {
        $capture = Invoke-SshCapture -IgnoreExitCode -Command "docker inspect --format '{{json .Mounts}}' '$($item.container)'"
        if (-not $capture.Ok) { Fail "TARGET_PLATFORM_NOT_RUNNING: $($item.role)" }
        $parsed = $capture.Output | ConvertFrom-Json
        $selected = @($parsed | Where-Object { $_.Destination -ceq $item.destination })
        if ($selected.Count -ne 1 -or $selected[0].Type -ne 'bind') { Fail "TARGET_PERSISTENT_MOUNT_INVALID: $($item.role); expected approved bind mount" }
        $source = [string]$selected[0].Source
        if ($source -cne "$RemoteAppDir/data/$($item.role)") { Fail "TARGET_PERSISTENT_MOUNT_MISMATCH: $($item.role)" }
        $literal = ConvertTo-ShellSingleQuotedLiteral -Value $source -Purpose 'persistent data source'
        $identity = Invoke-SshCapture -IgnoreExitCode -Command "test -d $literal && stat -Lc '%d:%i' $literal && findmnt -n -o SOURCE,FSTYPE,UUID --target $literal"
        if (-not $identity.Ok -or [string]::IsNullOrWhiteSpace($identity.Output)) { Fail "TARGET_PERSISTENT_MOUNT_UNREADABLE: $($item.role)" }
        $mounts += [ordered]@{role=$item.role;type='bind';source=$source;destination=$item.destination;identity=(([string]$identity.Output -split "`r?`n") -join '|')}
    }
    $tools = @()
    foreach ($prerequisite in @(Get-ReleasePlatformPrerequisites -Component $Component)) {
        $pathKey=[string]$prerequisite.pathEnv; $hashKey=[string]$prerequisite.sha256Env
        if (-not $freshEnv.ContainsKey($pathKey) -or -not $freshEnv.ContainsKey($hashKey) -or $freshEnv[$hashKey] -cnotmatch '^[0-9a-f]{64}$' -or -not ([string]$freshEnv[$pathKey]).StartsWith('/')) { Fail "PLATFORM_IDENTITY_NOT_CONFIGURED: $($prerequisite.toolId)" }
        $path=ConvertTo-ShellSingleQuotedLiteral -Value $freshEnv[$pathKey] -Purpose 'approved platform executable'
        $actual=Invoke-SshCapture -IgnoreExitCode -Command "test -f $path && test -x $path && sha256sum $path"
        $hash=([string]$actual.Output -split '\s+')[0]
        if (-not $actual.Ok -or $hash -cne $freshEnv[$hashKey]) { Fail "PLATFORM_IDENTITY_MISMATCH: $($prerequisite.toolId)" }
        $tools += [ordered]@{toolId=$prerequisite.toolId;path=$freshEnv[$pathKey];approvedSha256=$freshEnv[$hashKey];actualSha256=$hash;executable=$true}
    }
    $config=[ordered]@{MYSQL_DATABASE=$freshEnv['MYSQL_DATABASE'];IMAGE_TAG=$freshEnv['IMAGE_TAG'];REMOTE_APP_DIR=$RemoteAppDir;DATA_ROOT=$RemoteDataRoot;BACKEND_PORT=$freshEnv['BACKEND_HOST_PORT'];FRONTEND_PORT=$freshEnv['FRONTEND_HOST_PORT'];EDHR_STORAGE_ENDPOINT=$freshEnv['EDHR_S3_ENDPOINT'];EDHR_STORAGE_BUCKET=$freshEnv['EDHR_S3_BUCKET'];EDHR_STORAGE_REGION=$freshEnv['EDHR_S3_REGION']}
    if ($Component -eq 'full') { $config['WEBSITE_PORT']=[string]$freshEnv['WEBSITE_HOST_PORT'] }
    if ($IncludeOnlyOffice) { $config['ONLYOFFICE_PORT']=[string]$freshEnv['ONLYOFFICE_HOST_PORT'] }
    return [ordered]@{
        schemaVersion='release-deploy-target-state/v1';capturedAt=(Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
        targetEnvironment=$Environment;hostIdentity=@{host=$ServerHost;machineId=([string]$machine.Output).Trim()}
        databaseIdentity=$database.databaseIdentity;schemaEvidence=$database.schemaEvidence
        migrationLedgerComplete=$true;migrationLedger=@($database.migrationLedger);nonSecretConfig=$config
        persistentMounts=@($mounts);platformPrerequisites=@($tools)
    }
}

function Assert-ReleaseTargetDataPreconditions {
    param([Parameter(Mandatory = $true)]$Plan)
    $manifest = Read-ReleaseManifest
    $checks = @()
    foreach ($item in @($Plan.items | Where-Object { $_.action -ceq 'APPLY' })) {
        $matches = @($manifest.requiredSql | Where-Object { $_.migrationId -ceq $item.migrationId })
        if ($matches.Count -ne 1) { Fail "TARGET_PREFLIGHT_INPUT_INVALID: $($item.migrationId) manifest entry" }
        $entry=$matches[0]
        $sqlPath=Join-Path $releaseDir ([string]$entry.file)
        $metadata=Read-ReleaseMigrationMetadata -SqlPath $sqlPath
        if ([string]$metadata.type -cne [string]$entry.type) { Fail "TARGET_PREFLIGHT_INPUT_INVALID: $($item.migrationId) SQL type differs from manifest" }
        $required=([string]$metadata.type -cne 'schema') -or [bool]$metadata.requiresTargetPreflight -or [bool]$entry.requiresTargetPreflight
        if ($null -eq $entry.targetPreflight) {
            if ($required) { Fail "TARGET_PREFLIGHT_MISSING: $($item.migrationId) requires packaged read-only checks" }
            continue
        }
        $check=$entry.targetPreflight
        $expectedReference="target-preflight/$($item.migrationId).preflight.sql"
        if ([string]$check.reference -cne $expectedReference -or $check.readOnly -isnot [bool] -or -not $check.readOnly) { Fail "TARGET_PREFLIGHT_INPUT_INVALID: $($item.migrationId)" }
        $path=Join-Path $releaseDir $expectedReference
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { Fail "TARGET_PREFLIGHT_MISSING: $expectedReference" }
        $actual=ConvertTo-ReleaseFileSha256Hex -Path $path
        if ($actual -cne (([string]$check.sha256) -creplace '^sha256:', '')) { Fail "TARGET_PREFLIGHT_CHECKSUM_MISMATCH: $expectedReference" }
        Invoke-CheckedCommand -FilePath 'python' -ArgumentList @('-X','utf8',(Join-Path $maintenanceReleaseScriptRoot 'release_target_preflight_contract.py'),'--migration-id',[string]$item.migrationId,'--path',$path)
        $content=[IO.File]::ReadAllText($path,[Text.UTF8Encoding]::new($false))
        $match=[regex]::Match($content,'(?m)^\s*--\s*release-target-preflight:\s*migrationId=[A-Za-z0-9_.-]+;\s*allowedEnvironments=([A-Za-z0-9_,-]+)\s*$')
        if (-not $match.Success -or ($match.Groups[1].Value.Split(',')) -cnotcontains $Environment) { Fail "TARGET_PREFLIGHT_ENVIRONMENT_NOT_ALLOWED: $($item.migrationId)" }
        $checks += @{id=[string]$item.migrationId;content=$content}
    }
    foreach ($check in $checks) {
        $sql="SET SESSION TRANSACTION READ ONLY;`nSTART TRANSACTION READ ONLY;`n$($check.content)`nROLLBACK;"
        $mysql=Get-ReleaseTargetMySqlCommand
        $result=Invoke-SshCapture -IgnoreExitCode -Command "cat <<'TARGET_PREFLIGHT_SQL' | $mysql`n$sql`nTARGET_PREFLIGHT_SQL"
        if (-not $result.Ok -or ([string]$result.Output).Trim() -cne "TARGET_PREFLIGHT_PASS:$($check.id)") { Fail "TARGET_PREFLIGHT_FAILED: $($check.id); read-only data check did not produce its exact PASS marker" }
    }
}

function Write-ReleasePreflightPlan {
    param([switch]$Verify)
    $manifestPath = Join-Path $releaseDir 'manifest.json'
    $targetStatePath = Join-Path $deployControlLocalRoot "preflight-target-state-$Environment.json"
    $preflightPlanPath = Join-Path $deployControlLocalRoot 'preflight-plan.json'
    $preflightScriptPath = Join-Path $maintenanceReleaseScriptRoot 'release_preflight_plan.py'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Fail "manifest.json missing in release package for preflight: $manifestPath"
    }
    if (-not (Test-Path -LiteralPath $preflightScriptPath -PathType Leaf)) {
        Fail "release preflight planner missing: $preflightScriptPath"
    }

    Info "Collecting fresh read-only target state for $Environment"
    $snapshot = Read-ReleaseTargetSnapshot -Verify:$Verify
    $targetStateJson = $snapshot | ConvertTo-Json -Depth 50
    [System.IO.File]::WriteAllText($targetStatePath, $targetStateJson, [System.Text.UTF8Encoding]::new($false))
    $arguments = @(
        '-X', 'utf8',
        $preflightScriptPath,
        '--manifest', $manifestPath,
        '--target-state', $targetStatePath,
        '--target-environment', $Environment,
        '--publish-scope', $releasePublishScope,
        '--executor', (Join-Path $scriptDir 'publish-int-ruoyi.ps1'),
        '--output', $preflightPlanPath
    )
    if ($Verify) { $arguments += '--verify' }
    Invoke-CheckedCommand -FilePath 'python' -ArgumentList $arguments
    $plan=Read-ReleasePreflightPlan
    Assert-ReleaseTargetDataPreconditions -Plan $plan
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

function Invoke-ReleaseMigrationStateUpdate {
    param(
        [Parameter(Mandatory = $true)]
        $Item,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )
    Invoke-ReleaseMigrationStateBatchUpdate -Items @($Item) -Status $Status -ErrorMessage $ErrorMessage
}

function New-ReleaseMigrationStateUpsertSql {
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
    $encodedErrorMessage = ConvertTo-ReleaseErrorBase64 -Value $ErrorMessage
    $errorSqlExpression = if ([string]::IsNullOrWhiteSpace($encodedErrorMessage)) {
        'NULL'
    } else {
        "CONVERT(FROM_BASE64('$encodedErrorMessage') USING utf8mb4)"
    }
    $releaseTagSql = ConvertTo-SqlStringLiteral -Value $ReleaseTag
    $migrationIdSql = ConvertTo-SqlStringLiteral -Value $migrationId
    $fileNameSql = ConvertTo-SqlStringLiteral -Value $fileName
    $sha256Sql = ConvertTo-SqlStringLiteral -Value $sha256
    $environmentSql = ConvertTo-SqlStringLiteral -Value $Environment
    $statusSql = ConvertTo-SqlStringLiteral -Value $Status
    return @"
INSERT INTO infra_release_migration (release_tag, migration_id, file_name, sha256, target_environment, status, started_at, finished_at, error_message, operation_id, creator, create_time, updater, update_time, deleted)
VALUES ($releaseTagSql, $migrationIdSql, $fileNameSql, $sha256Sql, $environmentSql, $statusSql, NOW(), CASE WHEN $statusSql IN ('APPLIED', 'FAILED', 'SKIPPED_ALREADY_APPLIED', 'SKIPPED_ENV_NOT_ALLOWED', 'SKIPPED_SCOPE_EXCLUDED') THEN NOW() ELSE NULL END, $errorSqlExpression, $releaseTagSql, 'release-system', NOW(), 'release-system', NOW(), b'0')
ON DUPLICATE KEY UPDATE status = VALUES(status), file_name = VALUES(file_name), sha256 = VALUES(sha256), release_tag = VALUES(release_tag), finished_at = VALUES(finished_at), error_message = VALUES(error_message), operation_id = VALUES(operation_id), updater = VALUES(updater), update_time = NOW(), deleted = b'0';
"@
}

function Invoke-ReleaseMigrationStateBatchUpdate {
    param(
        [AllowEmptyCollection()]
        [AllowNull()]
        [object[]]$Items,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )

    if ($null -eq $Items -or $Items.Count -eq 0) {
        return
    }
    Assert-ReleaseOperationWriteFence
    Info "Batch updating release migration state: $Status ($($Items.Count))"
    $stateSql = @(
        foreach ($item in $Items) {
            New-ReleaseMigrationStateUpsertSql -Item $item -Status $Status -ErrorMessage $ErrorMessage
        }
    ) -join "`n"
    Invoke-SshCommandWithInput `
        -Command "$(Get-ReleaseTargetMySqlCommand)" `
        -StandardInput $stateSql
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
WHERE table_schema = DATABASE()
  AND table_name IN ('infra_release_migration', 'infra_release_operation_lock');
"@
    $probeResult = Invoke-SshCapture "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
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
        Invoke-SshCommand "cat '$remoteStateSchemaPath' | $(Get-ReleaseTargetMySqlCommand)"
    }
}

function Get-ReleaseOperationLockSchemaState {
    $schemaSql = @"
SELECT CASE
  WHEN (SELECT COUNT(*)
          FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME IN ('infra_release_migration', 'infra_release_operation_lock')) = 2
   AND (SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'infra_release_operation_lock'
           AND COLUMN_NAME IN (
             'id', 'target_environment', 'operation_id', 'release_tag', 'status', 'started_at',
             'finished_at', 'error_message', 'creator', 'create_time', 'updater', 'update_time',
             'deleted', 'tenant_id'
           )) = 14
   AND (SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'infra_release_operation_lock'
           AND COLUMN_NAME IN (
             'executor_host', 'executor_pid', 'executor_identity', 'lease_token',
             'heartbeat_at', 'write_fence'
           )) = 6
  THEN 'LOCK_SCHEMA_READY'
  WHEN (SELECT COUNT(*)
          FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME IN ('infra_release_migration', 'infra_release_operation_lock')) = 2
   AND (SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'infra_release_operation_lock'
           AND COLUMN_NAME IN (
             'id', 'target_environment', 'operation_id', 'release_tag', 'status', 'started_at',
             'finished_at', 'error_message', 'creator', 'create_time', 'updater', 'update_time',
             'deleted', 'tenant_id'
           )) = 14
   AND (SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'infra_release_operation_lock'
           AND COLUMN_NAME IN (
             'executor_host', 'executor_pid', 'executor_identity', 'lease_token',
             'heartbeat_at', 'write_fence'
           )) = 0
  THEN 'LOCK_SCHEMA_LEGACY'
  ELSE 'LOCK_SCHEMA_INVALID'
END;
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$schemaSql
SQL"
    $evidence = ($capture.Output -split "`r?`n" | Where-Object { $_ -match '^LOCK_SCHEMA_' } | Select-Object -Last 1)
    if (-not $capture.Ok -or $evidence -notin @('LOCK_SCHEMA_READY', 'LOCK_SCHEMA_LEGACY', 'LOCK_SCHEMA_INVALID')) {
        throw "RELEASE_OPERATION_LOCK_SCHEMA_CHECK_FAILED: $($capture.Output)"
    }
    return $evidence
}

function Assert-ReleaseOperationLockSchemaReady {
    $state = Get-ReleaseOperationLockSchemaState
    if ($state -ne 'LOCK_SCHEMA_READY') {
        throw "RELEASE_OPERATION_LOCK_SCHEMA_NOT_READY: state=$state"
    }
}

function Invoke-ReleaseOperationLegacyLockAcquire {
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
SELECT CASE WHEN operation_id = '$operationId' AND release_tag = '$ReleaseTag' AND status = 'RUNNING'
  THEN 'LEGACY_LOCK_ACQUIRED' ELSE CONCAT('LOCK_HELD:', operation_id, ':', release_tag) END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$lockSql
SQL"
    $evidence = ($capture.Output -split "`r?`n" | Where-Object { $_ -match '^(LEGACY_LOCK_ACQUIRED|LOCK_HELD:)' } | Select-Object -Last 1)
    if (-not $capture.Ok -or $evidence -ne 'LEGACY_LOCK_ACQUIRED') {
        throw "RELEASE_OPERATION_LOCK_HELD: $($capture.Output)"
    }
    $script:ReleaseOperationLockHeld = $true
    $script:ReleaseOperationLegacyLockHeld = $true
    $script:ReleaseOperationLockReleasing = $false
}

function Invoke-ReleaseOperationLockLeaseUpgrade {
    if (-not $script:ReleaseOperationLegacyLockHeld) {
        throw 'RELEASE_OPERATION_LEGACY_LOCK_NOT_HELD: lease schema upgrade refused'
    }
    $migrationFileName = '20260921_infra_release_operation_lock_lease_fencing.sql'
    $migrationPath = Join-Path $requiredSqlLocalDir $migrationFileName
    if (-not (Test-Path -LiteralPath $migrationPath -PathType Leaf)) {
        throw "RELEASE_OPERATION_LOCK_MIGRATION_MISSING: $migrationFileName"
    }
    $migrationSql = [System.IO.File]::ReadAllText($migrationPath, [System.Text.UTF8Encoding]::new($false))
    Invoke-SshCommandWithInput `
        -Command "$(Get-ReleaseTargetMySqlCommand)" `
        -StandardInput $migrationSql

    $operationId = "$Environment-$ReleaseTag"
    $leaseToken = [guid]::NewGuid().ToString('N')
    $leaseTokenSql = $leaseToken.Replace("'", "''")
    $executorHost = $script:ReleaseOperationExecutorHost.Replace("'", "''")
    $executorPid = $script:ReleaseOperationExecutorPid.Replace("'", "''")
    $executorIdentity = $script:ReleaseOperationExecutorIdentity.Replace("'", "''")
    $transitionSql = @"
UPDATE infra_release_operation_lock
SET executor_host = '$executorHost',
    executor_pid = '$executorPid',
    executor_identity = '$executorIdentity',
    lease_token = '$leaseTokenSql',
    heartbeat_at = NOW(),
    write_fence = write_fence + 1,
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = '$Environment'
  AND operation_id = '$operationId'
  AND release_tag = '$ReleaseTag'
  AND status = 'RUNNING'
  AND lease_token IS NULL;
SELECT CASE WHEN ROW_COUNT() = 1 THEN CONCAT('LOCK_UPGRADED:', '$leaseTokenSql') ELSE 'LOCK_UPGRADE_FAILED' END;
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$transitionSql
SQL"
    $evidence = ($capture.Output -split "`r?`n" | Where-Object { $_ -match '^LOCK_UPGRADE' } | Select-Object -Last 1)
    if (-not $capture.Ok -or $evidence -ne "LOCK_UPGRADED:$leaseToken") {
        throw "RELEASE_OPERATION_LOCK_UPGRADE_FAILED: $(Protect-ReleaseSensitiveText -Value $capture.Output -SensitiveValues @($leaseToken))"
    }
    $script:ReleaseOperationLeaseToken = $leaseToken
    $script:ReleaseOperationLegacyLockHeld = $false
}

function Enter-ReleaseOperationLock {
    $state = Get-ReleaseOperationLockSchemaState
    if ($state -eq 'LOCK_SCHEMA_READY') {
        Invoke-ReleaseOperationLockAcquire
        Assert-ReleaseOperationLockOwnership
        return
    }
    throw "RELEASE_OPERATION_LOCK_SCHEMA_NOT_READY: state=$state"
}

function Invoke-ReleaseOperationLockAcquire {
    $operationId = "$Environment-$ReleaseTag"
    $script:ReleaseOperationLeaseToken = [guid]::NewGuid().ToString('N')
    $leaseToken = $script:ReleaseOperationLeaseToken.Replace("'", "''")
    $executorHost = $script:ReleaseOperationExecutorHost.Replace("'", "''")
    $executorPid = $script:ReleaseOperationExecutorPid.Replace("'", "''")
    $executorIdentity = $script:ReleaseOperationExecutorIdentity.Replace("'", "''")
    $lockSql = @"
INSERT INTO infra_release_operation_lock (target_environment, operation_id, release_tag, status, started_at, finished_at, error_message, executor_host, executor_pid, executor_identity, lease_token, heartbeat_at, write_fence, creator, create_time, updater, update_time, deleted, tenant_id)
VALUES ('$Environment', '$operationId', '$ReleaseTag', 'RUNNING', NOW(), NULL, NULL, '$executorHost', '$executorPid', '$executorIdentity', '$leaseToken', NOW(), 1, 'release-system', NOW(), 'release-system', NOW(), b'0', 0)
ON DUPLICATE KEY UPDATE
  operation_id = IF(status = 'RUNNING', operation_id, VALUES(operation_id)),
  release_tag = IF(status = 'RUNNING', release_tag, VALUES(release_tag)),
  started_at = IF(status = 'RUNNING', started_at, VALUES(started_at)),
  finished_at = IF(status = 'RUNNING', finished_at, NULL),
  error_message = IF(status = 'RUNNING', error_message, NULL),
  executor_host = IF(status = 'RUNNING', executor_host, '$executorHost'),
  executor_pid = IF(status = 'RUNNING', executor_pid, '$executorPid'),
  executor_identity = IF(status = 'RUNNING', executor_identity, '$executorIdentity'),
  lease_token = IF(status = 'RUNNING', lease_token, '$leaseToken'),
  heartbeat_at = IF(status = 'RUNNING', heartbeat_at, NOW()),
  write_fence = IF(status = 'RUNNING', write_fence, write_fence + 1),
  updater = IF(status = 'RUNNING', updater, 'release-system'),
  update_time = IF(status = 'RUNNING', update_time, NOW()),
  deleted = IF(status = 'RUNNING', deleted, b'0'),
  status = IF(status = 'RUNNING', status, 'RUNNING');
SELECT CASE WHEN operation_id = '$operationId' AND status = 'RUNNING' AND lease_token = '$leaseToken' THEN CONCAT('LOCK_ACQUIRED:', lease_token) ELSE CONCAT('LOCK_HELD:', operation_id, ':', release_tag) END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$lockSql
SQL"
    $lockResult = ($capture.Output -split "`r?`n" | Where-Object { $_ -match '^(LOCK_ACQUIRED|LOCK_HELD:)' } | Select-Object -Last 1)
    if (-not $capture.Ok -or [string]::IsNullOrWhiteSpace($lockResult)) {
        throw "RELEASE_OPERATION_LOCK_ACQUIRE_FAILED: $(Protect-ReleaseSensitiveText -Value $capture.Output)"
    }
    if ($lockResult -like 'LOCK_HELD:*') {
        throw "RELEASE_OPERATION_LOCK_HELD: $(Protect-ReleaseSensitiveText -Value $lockResult)"
    }
    if ($lockResult -ne "LOCK_ACQUIRED:$($script:ReleaseOperationLeaseToken)") {
        throw "RELEASE_OPERATION_LOCK_ACQUIRE_FAILED: unexpected ownership evidence '$(Protect-ReleaseSensitiveText -Value $lockResult)'"
    }
    $script:ReleaseOperationLockHeld = $true
    $script:ReleaseOperationLockReleasing = $false
}

function Assert-ReleaseOperationLockOwnership {
    if (-not $script:ReleaseOperationLockHeld) {
        return
    }
    $operationId = "$Environment-$ReleaseTag"
    $leaseToken = $script:ReleaseOperationLeaseToken.Replace("'", "''")
    $ownershipSql = @"
SELECT CASE
  WHEN operation_id = '$operationId'
   AND release_tag = '$ReleaseTag'
   AND status = 'RUNNING'
   AND lease_token = '$leaseToken'
   AND executor_host = '$($script:ReleaseOperationExecutorHost.Replace("'", "''"))'
   AND executor_pid = '$($script:ReleaseOperationExecutorPid.Replace("'", "''"))'
   AND executor_identity = '$($script:ReleaseOperationExecutorIdentity.Replace("'", "''"))'
  THEN 'LOCK_OWNED'
  ELSE 'LOCK_LOST'
END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$ownershipSql
SQL"
    $evidence = ($capture.Output -split "`r?`n" | Where-Object { $_ -match '^(LOCK_OWNED|LOCK_LOST)$' } | Select-Object -Last 1)
    if (-not $capture.Ok -or $evidence -ne 'LOCK_OWNED') {
        $script:ReleaseOperationLockHeld = $false
        throw "RELEASE_OPERATION_LOCK_LOST: expected ownership evidence, got '$(Protect-ReleaseSensitiveText -Value $capture.Output)'"
    }
    $heartbeatSql = @"
UPDATE infra_release_operation_lock
SET heartbeat_at = NOW(),
    write_fence = write_fence + 1,
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = '$Environment'
  AND operation_id = '$operationId'
  AND release_tag = '$ReleaseTag'
  AND status = 'RUNNING'
  AND lease_token = '$leaseToken'
  AND executor_host = '$($script:ReleaseOperationExecutorHost.Replace("'", "''"))'
  AND executor_pid = '$($script:ReleaseOperationExecutorPid.Replace("'", "''"))'
  AND executor_identity = '$($script:ReleaseOperationExecutorIdentity.Replace("'", "''"))';
SELECT CASE WHEN ROW_COUNT() = 1 THEN 'HEARTBEAT_RENEWED' ELSE 'HEARTBEAT_RENEW_FAILED' END;
"@
    $heartbeat = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$heartbeatSql
SQL"
    $heartbeatEvidence = ($heartbeat.Output -split "`r?`n" | Where-Object { $_ -match '^HEARTBEAT_' } | Select-Object -Last 1)
    if (-not $heartbeat.Ok -or $heartbeatEvidence -ne 'HEARTBEAT_RENEWED') {
        $script:ReleaseOperationLockHeld = $false
        throw "RELEASE_OPERATION_LOCK_LOST: heartbeat renewal failed: $(Protect-ReleaseSensitiveText -Value $heartbeat.Output)"
    }
}

function Assert-ReleaseOperationWriteFence {
    if ($Mode -ne 'deploy-release') {
        return
    }
    if (-not $script:ReleaseOperationLockHeld) {
        throw 'RELEASE_OPERATION_LOCK_NOT_HELD: deploy-release write refused before ownership verification'
    }
    Assert-ReleaseOperationLockOwnership
}

function Invoke-ReleaseOperationLegacyLockRelease {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )
    $operationId = "$Environment-$ReleaseTag"
    $encodedErrorMessage = ConvertTo-ReleaseErrorBase64 -Value $ErrorMessage
    $errorSqlExpression = if ([string]::IsNullOrWhiteSpace($encodedErrorMessage)) {
        'NULL'
    } else {
        "CONVERT(FROM_BASE64('$encodedErrorMessage') USING utf8mb4)"
    }
    $lockSql = @"
UPDATE infra_release_operation_lock
SET status = '$Status', finished_at = NOW(), error_message = $errorSqlExpression,
    updater = 'release-system', update_time = NOW()
WHERE target_environment = '$Environment'
  AND operation_id = '$operationId'
  AND release_tag = '$ReleaseTag'
  AND status = 'RUNNING';
SELECT CASE WHEN ROW_COUNT() = 1 THEN 'LEGACY_LOCK_RELEASED' ELSE 'LEGACY_LOCK_RELEASE_FAILED' END;
"@
    $capture = Invoke-SshCapture -IgnoreExitCode "cat <<'SQL' | $(Get-ReleaseTargetMySqlCommand)
$lockSql
SQL"
    if (-not $capture.Ok -or $capture.Output -notmatch 'LEGACY_LOCK_RELEASED') {
        throw "RELEASE_OPERATION_LEGACY_LOCK_RELEASE_FAILED: $($capture.Output)"
    }
    $script:ReleaseOperationLockHeld = $false
    $script:ReleaseOperationLegacyLockHeld = $false
    $script:ReleaseOperationLockReleasing = $false
}

function Invoke-ReleaseOperationLockRelease {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [string]$ErrorMessage = ''
    )
    if ($script:ReleaseOperationLegacyLockHeld) {
        Invoke-ReleaseOperationLegacyLockRelease -Status $Status -ErrorMessage $ErrorMessage
        return
    }
    $operationId = "$Environment-$ReleaseTag"
    $encodedErrorMessage = ConvertTo-ReleaseErrorBase64 -Value $ErrorMessage
    $errorSqlExpression = if ([string]::IsNullOrWhiteSpace($encodedErrorMessage)) {
        'NULL'
    } else {
        "CONVERT(FROM_BASE64('$encodedErrorMessage') USING utf8mb4)"
    }
    $lockSql = @"
UPDATE infra_release_operation_lock
SET status = '$Status',
    finished_at = NOW(),
    error_message = $errorSqlExpression,
    updater = 'release-system',
    update_time = NOW()
WHERE target_environment = '$Environment'
  AND operation_id = '$operationId'
  AND release_tag = '$ReleaseTag'
  AND lease_token = '$($script:ReleaseOperationLeaseToken.Replace("'", "''"))'
  AND executor_host = '$($script:ReleaseOperationExecutorHost.Replace("'", "''"))'
  AND executor_pid = '$($script:ReleaseOperationExecutorPid.Replace("'", "''"))'
  AND executor_identity = '$($script:ReleaseOperationExecutorIdentity.Replace("'", "''"))'
  AND status = 'RUNNING';
SELECT CASE WHEN status = '$Status' AND lease_token = '$($script:ReleaseOperationLeaseToken.Replace("'", "''"))' THEN 'LOCK_RELEASED' ELSE CONCAT('LOCK_RELEASE_FAILED:', operation_id, ':', status) END
FROM infra_release_operation_lock
WHERE target_environment = '$Environment';
"@
    Invoke-SshCommand "set -eu
lock_result=`$($(Get-ReleaseTargetMySqlCommand) <<'SQL'
$lockSql
SQL
)
test `"`$lock_result`" = 'LOCK_RELEASED'"
    $script:ReleaseOperationLockHeld = $false
    $script:ReleaseOperationLegacyLockHeld = $false
    $script:ReleaseOperationLockReleasing = $false
    $script:ReleaseOperationLeaseToken = ''
}

function Copy-RequiredDatabaseSqlScripts {
    if (Test-Path -LiteralPath $requiredSqlLocalDir) {
        Remove-Item -LiteralPath $requiredSqlLocalDir -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $requiredSqlLocalDir | Out-Null
    $targetPreflightRoot = Join-Path $releaseDir 'target-preflight'
    if (Test-Path -LiteralPath $targetPreflightRoot) { Remove-Item -LiteralPath $targetPreflightRoot -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $targetPreflightRoot | Out-Null

    foreach ($entry in $requiredDatabaseSqlScripts) {
        $relativePath = [string]$entry.Path
        $sourceRelativePath = $relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        $sourcePath = Join-Path $backendRepo $sourceRelativePath
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            Fail "Required database SQL script missing: $sourcePath"
        }

        $targetPath = Join-Path $requiredSqlLocalDir (Get-RequiredDatabaseSqlFileName -RelativePath $relativePath)
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        $migrationId = [IO.Path]::GetFileNameWithoutExtension($targetPath)
        $checkSource = Join-Path $backendRepo "sql\mysql\target-preflight\$migrationId.preflight.sql"
        if (Test-Path -LiteralPath $checkSource -PathType Leaf) {
            Invoke-CheckedCommand -FilePath 'python' -ArgumentList @('-X', 'utf8', (Join-Path $maintenanceReleaseScriptRoot 'release_target_preflight_contract.py'), '--migration-id', $migrationId, '--path', $checkSource)
            Copy-Item -LiteralPath $checkSource -Destination (Join-Path $targetPreflightRoot "$migrationId.preflight.sql") -Force
        }
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
    $requiredSqlArchiveRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("required-sql-upload-" + [System.Guid]::NewGuid().ToString("N"))
    $requiredSqlArchivePath = Join-Path ([System.IO.Path]::GetTempPath()) "required-sql-$packageDirectoryName.tar"
    $remoteRequiredSqlArchive = "$remoteReleaseDir/required-sql.tar"
    try {
        if (Test-Path -LiteralPath $requiredSqlArchiveRoot) {
            Remove-Item -LiteralPath $requiredSqlArchiveRoot -Recurse -Force
        }
        if (Test-Path -LiteralPath $requiredSqlArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $requiredSqlArchivePath -Force
        }
        New-Item -ItemType Directory -Force -Path $requiredSqlArchiveRoot | Out-Null
        foreach ($entry in $requiredSqlEntries) {
            $relativePath = [string]$entry.Path
            $fileName = Get-RequiredDatabaseSqlFileName -RelativePath $relativePath
            $packageSqlPath = Join-Path $requiredSqlLocalDir $fileName
            Copy-Item -LiteralPath $packageSqlPath -Destination (Join-Path $requiredSqlArchiveRoot $fileName) -Force
        }
        $archiveSqlCount = @(Get-ChildItem -LiteralPath $requiredSqlArchiveRoot -File -Filter '*.sql').Count
        if ($archiveSqlCount -le 0) {
            Fail 'required SQL archive contains no files before upload'
        }
        Info "Packing required database SQL archive: $archiveSqlCount files"
        Invoke-CheckedCommand -FilePath 'tar' -ArgumentList @('-cf', $requiredSqlArchivePath, '-C', $requiredSqlArchiveRoot, '.')
        if (-not (Test-Path -LiteralPath $requiredSqlArchivePath -PathType Leaf)) {
            Fail "required SQL archive was not created: $requiredSqlArchivePath"
        }
        Copy-ToServer -LocalPath $requiredSqlArchivePath -RemotePath $remoteRequiredSqlArchive
        Info "Extracting required database SQL archive on target server: $archiveSqlCount files"
        Invoke-SshCommand "rm -rf '$remoteRequiredSqlDir' && mkdir -p '$remoteRequiredSqlDir' && tar -xf '$remoteRequiredSqlArchive' -C '$remoteRequiredSqlDir' && remote_sql_count=`$(find '$remoteRequiredSqlDir' -maxdepth 1 -type f -name '*.sql' | wc -l | tr -d ' ') && if [ `"`$remote_sql_count`" -ne $archiveSqlCount ]; then echo `"required SQL archive remote file count mismatch: expected $archiveSqlCount, actual `$remote_sql_count`"; exit 43; fi && rm -f '$remoteRequiredSqlArchive'"
    } finally {
        if (Test-Path -LiteralPath $requiredSqlArchiveRoot) {
            Remove-Item -LiteralPath $requiredSqlArchiveRoot -Recurse -Force
        }
        if (Test-Path -LiteralPath $requiredSqlArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $requiredSqlArchivePath -Force
        }
    }
}

function Write-ReleaseWebsiteDeployControl {
    $templatePath = Join-Path $websiteRuntimeLocal 'nginx.template.conf'
    if (-not (Test-Path -LiteralPath $templatePath -PathType Leaf)) {
        Fail 'PACKAGE_REQUIRED_ARTIFACT_MISSING: website/nginx.template.conf; rebuild the complete package'
    }
    $template = [IO.File]::ReadAllText($templatePath, [Text.UTF8Encoding]::new($false))
    if (-not $template.Contains('__BACKEND_ORIGIN__')) {
        Fail 'PACKAGE_WEBSITE_TEMPLATE_INVALID: missing __BACKEND_ORIGIN__'
    }
    $controlWebsiteRoot = Join-Path $deployControlLocalRoot 'website'
    New-Item -ItemType Directory -Force -Path $controlWebsiteRoot | Out-Null
    Write-Utf8LfNoBomFile -Path $websiteNginxLocal -Content ($template.Replace('__BACKEND_ORIGIN__', "${ServerHost}:$BackendPort"))
}

function Get-ReleasePlatformIdentityEnvironmentLines {
    $lines = @()
    foreach ($prerequisite in @(Get-ReleasePlatformPrerequisites -Component $Component)) {
        $key = [string]$prerequisite.sha256Env
        if (-not $existingRemoteEnv.ContainsKey($key) -or [string]$existingRemoteEnv[$key] -cnotmatch '^[0-9a-f]{64}$') {
            Fail "PLATFORM_IDENTITY_NOT_CONFIGURED: $key; complete approved target platform preparation before deployment"
        }
        $lines += "$key=$($existingRemoteEnv[$key])"
    }
    if ($Component -eq 'intruoyi' -and $existingRemoteEnv.ContainsKey('SHOWROOM_CODEX_CLI_SHA256')) {
        $lines += "SHOWROOM_CODEX_CLI_SHA256=$($existingRemoteEnv['SHOWROOM_CODEX_CLI_SHA256'])"
    }
    return $lines
}

function Copy-DeployControlFilesToServer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComposeLocal
    )

    $deployControlArchiveRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("deploy-control-upload-" + [System.Guid]::NewGuid().ToString("N"))
    $deployControlArchivePath = Join-Path ([System.IO.Path]::GetTempPath()) "deploy-control-$packageDirectoryName.tar"
    $remoteDeployControlArchive = "$remoteReleaseDir/deploy-control.tar"
    $remoteDeployControlExtractDir = "$remoteReleaseDir/deploy-control"
    $hasDeployControlFiles = $false
    try {
        if (Test-Path -LiteralPath $deployControlArchiveRoot) {
            Remove-Item -LiteralPath $deployControlArchiveRoot -Recurse -Force
        }
        if (Test-Path -LiteralPath $deployControlArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $deployControlArchivePath -Force
        }
        New-Item -ItemType Directory -Force -Path $deployControlArchiveRoot | Out-Null

        if ($publishBackend -or $publishFrontend) {
            if (-not (Test-Path -LiteralPath $ComposeLocal -PathType Leaf)) {
                Fail "Deploy compose file missing before archive upload: $ComposeLocal"
            }
            if (-not (Test-Path -LiteralPath $remoteEnvLocal -PathType Leaf)) {
                Fail "Deploy environment file missing before archive upload: $remoteEnvLocal"
            }
            $appControlRoot = Join-Path $deployControlArchiveRoot 'app'
            New-Item -ItemType Directory -Force -Path $appControlRoot | Out-Null
            Copy-Item -LiteralPath $ComposeLocal -Destination (Join-Path $appControlRoot 'docker-compose.yml') -Force
            Copy-Item -LiteralPath $remoteEnvLocal -Destination (Join-Path $appControlRoot '.env') -Force
            $hasDeployControlFiles = $true
        }

        if ($publishWebsite) {
            if (-not (Test-Path -LiteralPath $websiteRuntimeLocal -PathType Container)) {
                Fail "Website runtime directory missing before archive upload: $websiteRuntimeLocal"
            }
            Copy-Item -LiteralPath $websiteRuntimeLocal -Destination (Join-Path $deployControlArchiveRoot 'website') -Recurse -Force
            if (-not (Test-Path -LiteralPath $websiteNginxLocal -PathType Leaf)) {
                Fail "Website deploy configuration missing: $websiteNginxLocal"
            }
            Copy-Item -LiteralPath $websiteNginxLocal -Destination (Join-Path $deployControlArchiveRoot 'website\nginx.conf') -Force
            $hasDeployControlFiles = $true
        }

        if ($publishBackend -and -not $SkipDatabaseSync) {
            if (-not (Test-Path -LiteralPath $resetDbSqlLocal -PathType Leaf)) {
                Fail "Reset database SQL missing before archive upload: $resetDbSqlLocal"
            }
            $sqlControlRoot = Join-Path $deployControlArchiveRoot 'sql'
            New-Item -ItemType Directory -Force -Path $sqlControlRoot | Out-Null
            Copy-Item -LiteralPath $resetDbSqlLocal -Destination (Join-Path $sqlControlRoot 'reset-db.sql') -Force
            $hasDeployControlFiles = $true
        }


        if (-not $hasDeployControlFiles) {
            return
        }

        Info 'Packing deploy control files archive'
        Invoke-CheckedCommand -FilePath 'tar' -ArgumentList @('-cf', $deployControlArchivePath, '-C', $deployControlArchiveRoot, '.')
        if (-not (Test-Path -LiteralPath $deployControlArchivePath -PathType Leaf)) {
            Fail "deploy control archive was not created: $deployControlArchivePath"
        }
        Copy-ToServer -LocalPath $deployControlArchivePath -RemotePath $remoteDeployControlArchive

        $remoteDeployControlArchiveLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteDeployControlArchive -Purpose 'deploy control archive'
        $remoteDeployControlExtractDirLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteDeployControlExtractDir -Purpose 'deploy control extract directory'
        $remoteComposeLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteCompose -Purpose 'remote compose path'
        $remoteEnvLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnvNext -Purpose 'remote env.next path'
        $remoteWebsiteStagingDirLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteWebsiteStagingDir -Purpose 'remote website staging directory'
        $remoteResetDbSqlLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteResetDbSql -Purpose 'remote reset database SQL path'
        $remotePostImportSqlLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remotePostImportSql -Purpose 'remote post-import SQL path'
        $remoteCommands = @(
            'set -e',
            "cleanup_deploy_control() { rm -rf $remoteDeployControlExtractDirLiteral; rm -f $remoteDeployControlArchiveLiteral; }",
            'trap cleanup_deploy_control EXIT',
            "rm -rf $remoteDeployControlExtractDirLiteral",
            "mkdir -p $remoteDeployControlExtractDirLiteral",
            "tar -xf $remoteDeployControlArchiveLiteral -C $remoteDeployControlExtractDirLiteral"
        )
        if ($publishBackend -or $publishFrontend) {
            $remoteCommands += "test -f $remoteDeployControlExtractDirLiteral/app/docker-compose.yml"
            $remoteCommands += "test -f $remoteDeployControlExtractDirLiteral/app/.env"
            $remoteCommands += "cp $remoteDeployControlExtractDirLiteral/app/docker-compose.yml $remoteComposeLiteral"
            $remoteCommands += "cp $remoteDeployControlExtractDirLiteral/app/.env $remoteEnvLiteral"
        }
        if ($publishWebsite) {
            $remoteCommands += "test -f $remoteDeployControlExtractDirLiteral/website/dist/index.html"
            $remoteCommands += "test -f $remoteDeployControlExtractDirLiteral/website/nginx.conf"
            $remoteCommands += "rm -rf $remoteWebsiteStagingDirLiteral"
            $remoteCommands += "mv $remoteDeployControlExtractDirLiteral/website $remoteWebsiteStagingDirLiteral"
            $remoteCommands += "test -f $remoteWebsiteStagingDirLiteral/dist/index.html"
            $remoteCommands += "test -f $remoteWebsiteStagingDirLiteral/nginx.conf"
        }
        if ($publishBackend -and -not $SkipDatabaseSync) {
            $remoteCommands += "test -f $remoteDeployControlExtractDirLiteral/sql/reset-db.sql"
            $remoteCommands += "cp $remoteDeployControlExtractDirLiteral/sql/reset-db.sql $remoteResetDbSqlLiteral"
        }
        $remoteCommands += "rm -rf $remoteDeployControlExtractDirLiteral"
        $remoteCommands += "rm -f $remoteDeployControlArchiveLiteral"
        Invoke-SshCommand ($remoteCommands -join "`n")
    } finally {
        if (Test-Path -LiteralPath $deployControlArchiveRoot) {
            Remove-Item -LiteralPath $deployControlArchiveRoot -Recurse -Force
        }
        if (Test-Path -LiteralPath $deployControlArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $deployControlArchivePath -Force
        }
    }
}

function New-ReleaseOpsRuntimePackage {
    Info 'Preparing runtime-control ops scripts in release package'
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

    $targetConfigDirectory = Join-Path $opsRuntimeLocalDir 'config'
    New-Item -ItemType Directory -Force -Path $targetConfigDirectory | Out-Null
    Info 'Skipping runtime-control ops config files; server-side config is preserved on the target host.'
    if (Test-Path -LiteralPath (Join-Path $targetConfigDirectory 'backup-ops.secrets.json')) {
        Fail 'Runtime-control ops package must not include backup-ops.secrets.json'
    }
}

function Copy-ReleaseOpsRuntimePackage {
    Info 'Syncing runtime-control ops scripts from release package to the target server'
    if (-not (Test-Path -LiteralPath $opsRuntimeLocalDir -PathType Container)) {
        Fail "Runtime-control ops package missing in release package: $opsRuntimeLocalDir"
    }
    foreach ($requiredPath in @(
        'linux\backup-ops-linux.sh',
        'scripts\backup-ops.ps1',
        'actions'
    )) {
        $candidate = Join-Path $opsRuntimeLocalDir $requiredPath
        if (-not (Test-Path -LiteralPath $candidate)) {
            Fail "Runtime-control ops package entry missing: ops-runtime/$($requiredPath.Replace('\', '/'))"
        }
    }
    if (Test-Path -LiteralPath (Join-Path $opsRuntimeLocalDir 'config\backup-ops.secrets.json')) {
        Fail 'Runtime-control ops package must not include backup-ops.secrets.json'
    }
    $opsRuntimeArchivePath = Join-Path ([System.IO.Path]::GetTempPath()) "ops-runtime-$packageDirectoryName.tar"
    $remoteOpsRuntimeArchive = "$remoteReleaseDir/ops-runtime.tar"
    try {
        if (Test-Path -LiteralPath $opsRuntimeArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $opsRuntimeArchivePath -Force
        }
        Info 'Packing runtime-control ops package archive'
        Invoke-CheckedCommand -FilePath 'tar' -ArgumentList @('-cf', $opsRuntimeArchivePath, '-C', $opsRuntimeLocalDir, '.')
        if (-not (Test-Path -LiteralPath $opsRuntimeArchivePath -PathType Leaf)) {
            Fail "runtime-control ops archive was not created: $opsRuntimeArchivePath"
        }
        Copy-ToServer -LocalPath $opsRuntimeArchivePath -RemotePath $remoteOpsRuntimeArchive
        Info 'Extracting runtime-control ops package archive on target server'
        Invoke-SshCommand "mkdir -p '$remoteOpsRuntimeDir' '$remoteOpsRuntimeDir/config' && rm -rf '$remoteOpsRuntimeDir/linux' '$remoteOpsRuntimeDir/scripts' '$remoteOpsRuntimeDir/actions' && tar -xf '$remoteOpsRuntimeArchive' -C '$remoteOpsRuntimeDir' && rm -f '$remoteOpsRuntimeArchive' && test -f '$remoteOpsRuntimeDir/linux/backup-ops-linux.sh' && test -d '$remoteOpsRuntimeDir/config'"
    } finally {
        if (Test-Path -LiteralPath $opsRuntimeArchivePath -PathType Leaf) {
            Remove-Item -LiteralPath $opsRuntimeArchivePath -Force
        }
    }
}

function Write-TargetBoundPostImportSql {
    $edhrProtectedStorageSql = New-EdhrProtectedStoragePostImportSql
    $showroomFileStorageSql = New-ShowroomFileStoragePostImportSql -TargetServerHost $ServerHost -MinioAccessKey $remoteMinioAccessKey -MinioAccessSecret $remoteMinioSecretKey
$postImportSql = @"
$edhrProtectedStorageSql

$showroomFileStorageSql
"@
    $postImportSqlParent = Split-Path -Parent $postImportSqlLocal
    if (-not (Test-Path -LiteralPath $postImportSqlParent -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $postImportSqlParent | Out-Null
    }
    [System.IO.File]::WriteAllText($postImportSqlLocal, $postImportSql, [System.Text.UTF8Encoding]::new($false))
}

function Get-RequiredDatabaseSqlSessionPreamble {
    param(
        [Parameter(Mandatory = $true)]
        $Item,

        [Parameter(Mandatory = $true)]
        [string]$TargetEnvironment
    )
    $sessionProfile = [string]$Item.sessionProfile
    switch ($sessionProfile) {
        'dcc-view-matrix-seed' {
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
        '' {
            return ''
        }
        default {
            Fail "Unsupported migration session profile: $sessionProfile"
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

    if ($null -eq $Items -or $Items.Count -eq 0) {
        return @()
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
                    $applyOrder = $_.Item.applyOrder
                    if ($null -ne $applyOrder -and -not [string]::IsNullOrWhiteSpace([string]$applyOrder)) {
                        return [int]$applyOrder
                    }
                    return 1000 + [int]$_.OriginalOrder
                } }, `
                @{ Expression = { [int]$_.OriginalOrder } } |
            ForEach-Object { $_.Item }
    )
}

function Invoke-RouteSnapshotIdentityMigrationCommand {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('BACKFILL', 'READINESS')]
        [string]$MigrationMode,

        [Parameter(Mandatory = $true)]
        [string]$ReportFileName
    )

    $remoteReportDir = "$remoteReleaseDir/runtime-reports"
    $remoteReportFile = "$remoteReportDir/$ReportFileName"
    $remoteReportDirLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteReportDir -Purpose 'route snapshot migration report directory'
    $remoteReportFileLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteReportFile -Purpose 'route snapshot migration report file'
    $remoteAppDirLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $RemoteAppDir -Purpose 'remote app directory'
    $reportVolumeLiteral = ConvertTo-ShellSingleQuotedLiteral -Value "${remoteReportDir}:/runtime-reports" -Purpose 'route snapshot migration report volume'
    $remoteEnvNextLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $remoteEnvNext -Purpose 'remote runtime env.next path'
    $extraArgsValue = "--server.port=0 --yudao.mes.route-snapshot-migration.mode=$MigrationMode --yudao.mes.route-snapshot-migration.report-file=/runtime-reports/$ReportFileName"
    $extraArgsLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $extraArgsValue -Purpose 'route snapshot migration extra args'

    Info "Running MES route snapshot identity $MigrationMode before NOT NULL enforcement"
    $command = @"
set -u
mkdir -p $remoteReportDirLiteral
rm -f $remoteReportFileLiteral
cd $remoteAppDirLiteral
test -f $remoteEnvNextLiteral
set +e
docker compose --env-file $remoteEnvNextLiteral run --rm --no-deps -v $reportVolumeLiteral -e INTRUOYI_EXTRA_ARGS=$extraArgsLiteral backend
route_snapshot_exit=`$?
set -e
if [ -f $remoteReportFileLiteral ]; then
  cat $remoteReportFileLiteral
else
  echo 'ROUTE_SNAPSHOT_IDENTITY_REPORT_MISSING: route snapshot identity hook did not write its report'
fi
test "`$route_snapshot_exit" -eq 0
test -f $remoteReportFileLiteral
grep -q '"status" : "READY"' $remoteReportFileLiteral
grep -q '"blockerCount" : 0' $remoteReportFileLiteral
"@
    Invoke-SshCommandWithInput -Command 'bash -s' -StandardInput $command
}

function Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement {
    param(
        [Parameter(Mandatory = $true)]
        $Item
    )

    $approvedHook = [string]$Item.approvedHook
    if ($approvedHook -ne 'route-snapshot-identity') {
        return
    }

    Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'BACKFILL' -ReportFileName 'route-snapshot-identity-backfill.json'
    Invoke-RouteSnapshotIdentityMigrationCommand -MigrationMode 'READINESS' -ReportFileName 'route-snapshot-identity-readiness.json'
}

function Invoke-RequiredDatabaseSqlScriptWithState {
    param(
        [Parameter(Mandatory = $true)]
        $Item,
        [Parameter(Mandatory = $true)]
        [string]$RemoteSqlPath,
        [string]$SessionPreamble = ''
    )

    Assert-ReleaseOperationWriteFence
    $runningSql = New-ReleaseMigrationStateUpsertSql -Item $Item -Status 'RUNNING'
    $appliedSql = New-ReleaseMigrationStateUpsertSql -Item $Item -Status 'APPLIED'
    $remoteSqlPathLiteral = ConvertTo-ShellSingleQuotedLiteral -Value $RemoteSqlPath -Purpose 'required database SQL remote path'
    $mysqlCommand = Get-ReleaseTargetMySqlCommand
    if ([string]::IsNullOrWhiteSpace($SessionPreamble)) {
        $applySqlCommand = "cat $remoteSqlPathLiteral"
    } else {
        $escapedSessionPreamble = $SessionPreamble.TrimEnd()
        $applySqlCommand = @"
{
cat <<'REQUIRED_SQL_SESSION_PREAMBLE'
$escapedSessionPreamble
REQUIRED_SQL_SESSION_PREAMBLE
cat $remoteSqlPathLiteral
}
"@
    }

    $command = @"
set -e
test -f $remoteSqlPathLiteral
cat <<'RELEASE_STATE_RUNNING_SQL' | $mysqlCommand
$runningSql
RELEASE_STATE_RUNNING_SQL
$applySqlCommand | $mysqlCommand
cat <<'RELEASE_STATE_APPLIED_SQL' | $mysqlCommand
$appliedSql
RELEASE_STATE_APPLIED_SQL
"@
    Invoke-SshCommand $command
}

function Invoke-RequiredDatabaseSqlScripts {
    Info 'Applying required database SQL scripts'
    $preflightPlan = Read-ReleasePreflightPlan
    $skipAlreadyAppliedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ALREADY_APPLIED' })
    $skipEnvNotAllowedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_ENV_NOT_ALLOWED' })
    foreach ($item in $skipEnvNotAllowedItems) {
        Info "Skipping required database SQL outside target environment: $($item.migrationId)"
    }
    $skipScopeExcludedItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_SCOPE_EXCLUDED' })
    foreach ($item in $skipScopeExcludedItems) {
        Info "Skipping required database SQL excluded by publish scope ${releasePublishScope}: $($item.migrationId)"
    }
    $skipImmutableItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'SKIP_IMMUTABLE' })
    foreach ($item in $skipImmutableItems) {
        Info "Skipping superseded immutable migration without ledger mutation: $($item.migrationId)"
    }
    $preflightApplyItems = @($preflightPlan.items | Where-Object { [string]$_.action -eq 'APPLY' })
    $applyItems = @($preflightApplyItems)
    foreach ($item in $applyItems) {
        $fileName = Get-RequiredDatabaseSqlFileName -RelativePath ([string]$item.file)
        $remoteSqlPath = "$remoteRequiredSqlDir/$fileName"
        $sessionPreamble = Get-RequiredDatabaseSqlSessionPreamble -Item $item -TargetEnvironment $Environment
        Info "Applying required database SQL: $fileName"
        Assert-ReleaseOperationWriteFence
        Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement -Item $item
        try {
            Invoke-RequiredDatabaseSqlScriptWithState -Item $item -RemoteSqlPath $remoteSqlPath -SessionPreamble $sessionPreamble
        } catch {
            $migrationError=$_
            try {Invoke-ReleaseMigrationStateUpdate -Item $item -Status 'FAILED' -ErrorMessage $migrationError.Exception.Message}
            catch {$script:ReleaseMigrationFailureErrors=@($script:ReleaseMigrationFailureErrors)+(Protect-ReleaseSensitiveText $_.Exception.Message)}
            throw $migrationError
        }
    }
}

$testPublishOperationEvidence = $null
if ($Mode -eq 'mark-tested' -or ($Mode -eq 'deploy-release' -and $Environment -in @('prod', 'backup'))) {
    if ([string]::IsNullOrWhiteSpace($TestOperationId)) {
        Fail 'TestOperationId is required for mark-tested and production-grade promotion.'
    }
    if ([string]::IsNullOrWhiteSpace($TestOperationEvidencePath)) {
        Fail 'TestOperationEvidencePath is required for mark-tested and production-grade promotion.'
    }
    try {
        $testPublishOperationEvidence = Assert-PublishTestOperationEvidence `
            -EvidencePath $TestOperationEvidencePath `
            -ExpectedOperationId $TestOperationId `
            -ExpectedReleaseTag $ReleaseTag
    } catch {
        Fail $_.Exception.Message
    }
}

if ($Mode -eq 'mark-tested') {
    Mark-NasReleaseTested -PackageTag $ReleaseTag
    Write-Host "Release package marked as tested: $ReleaseTag"
    exit 0
}

$existingRemoteEnv = @{}
function Import-ExistingRemoteRuntimeEnvSettings {
    if (-not ($publishBackend -or $publishFrontend)) {
        return
    }
    if ($existingRemoteEnv.Count -gt 0) {
        return
    }

    Set-Variable -Name existingRemoteEnv -Scope Script -Value (Get-RemoteRuntimeEnvMap)
    if ($Mode -eq 'build-release') {
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
            if (-not $existingRemoteEnv.ContainsKey($key) -or [string]::IsNullOrWhiteSpace([string]$existingRemoteEnv[$key])) {
                Fail "Missing $key in remote runtime .env for build-release; eDHR protected storage verifier must use target environment secrets."
            }
        }
    }
    Set-PublishRuntimeValuesFromSettings -Settings $existingRemoteEnv
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

if ($Mode -eq 'deploy-release') {
    Info "Deploying release package: $ReleaseTag"
    $releasePackageIntegrity = Copy-ReleasePackageFromNas -PackageTag $ReleaseTag
    Assert-ReleaseExecutorSourceBinding -PackageIntegrity $releasePackageIntegrity
    $Component = Resolve-DeployReleasePackageComponent -ComponentExplicit $componentExplicit
    $publishBackend = $Component -in @('full', 'intruoyi')
    $publishFrontend = $Component -in @('full', 'intruoyi')
    $publishWebsite = $Component -eq 'full'
    $releasePublishScope = $releasePackageIntegrity.PublishScope
    Assert-ReleasePackageDeploymentScope -TargetEnvironment $Environment -PublishScope $releasePublishScope
    Assert-ProdDryRunEvidence
    $releaseOnlyOfficeIncluded = Resolve-DeployReleasePackageOnlyOfficeIncluded -IncludeOnlyOfficeExplicit $PSBoundParameters.ContainsKey('IncludeOnlyOffice')
    $IncludeOnlyOffice = $releaseOnlyOfficeIncluded
    $script:ReleaseRuntimeImages = @($releasePackageIntegrity.runtimeImages)
    $script:ReleaseVerifiedImageContent = @($releasePackageIntegrity.verifiedImageContent)
    $schedulerSmokeNodeImage = [string](@(Get-ReleaseTargetImageIdentities | Where-Object { $_.name -ceq 'scheduler-smoke' })[0].configDigest)
    Assert-DeployReleasePackageArtifactsForScope -PublishScope $releasePublishScope
    if ($publishBackend) {
        $requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts
        Assert-RequiredDatabaseSqlScriptsInRelease
    }
    Require-Command 'ssh'
    Import-ExistingRemoteRuntimeEnvSettings
    if ($releasePublishScope -eq 'app-release') {
        $SkipDatabaseSync = $true
        $SkipMinioSync = $true
    } else {
        Fail "Unsupported release package publishScope: $releasePublishScope"
    }
    if ($smartReleaseReportOnlyEnabled -and $Mode -eq 'deploy-release') {
        Invoke-SmartReleaseDeployPrecheckReportOnly -PackagePath $releaseDir
    }
}

if ($Mode -eq 'build-release' -and $publishBackend) {
    Require-Command 'ssh'
    Import-ExistingRemoteRuntimeEnvSettings
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
if ($publishBackend -and $Mode -eq 'deploy-release') {
    Require-Command 'tar'
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
if ($publishBackend -and $Mode -ne 'build-release') {
    Assert-EdhrProtectedStorageConfig -Context 'target publish environment' -Settings $edhrProtectedStorageSettings
    Info 'eDHR protected storage settings validated; app-release deploy does not write Object Lock probe objects'
}

$mySqlRootPassword = ''
if ($publishBackend) {
    if ($Mode -eq 'deploy-release') {
        if ($existingRemoteEnv.ContainsKey('MYSQL_ROOT_PASSWORD')) { $mySqlRootPassword = [string]$existingRemoteEnv['MYSQL_ROOT_PASSWORD'] }
    } else {
        $mySqlRootPassword = Get-LocalContainerEnvValue -ContainerName $LocalMySqlContainer -Key 'MYSQL_ROOT_PASSWORD'
    }
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

if ($Mode -eq 'build-release') {
    if ($null -eq $script:ReleaseSourceFreezeEvidence) {
        $script:ReleaseSourceFreezeEvidence = Assert-ReleaseSourceFreeze -VerificationPoint 'before-build'
    }
    Invoke-StandardReleaseContractTests
    Write-ReleaseWorkflowStage -State 'BUILDING' -Evidence 'application-artifact-build'
}

Info 'Checking local Docker daemon'
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @('info')
if ($null -ne $backendRuntimeBaseConfig) {
    Assert-BackendRuntimeBaseTarIntegrity -Config $backendRuntimeBaseConfig
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
if ($publishFrontend) {
Assert-FrontendBuildPreflight -FrontendDir $frontendDir
}
if ($publishBackend) {
Invoke-BackendSpringConstructorGate
}
if ($publishBackend) {
Copy-RequiredDatabaseSqlScripts
if ($Mode -eq 'build-release') {
Invoke-BuildReleaseTargetPreflight
Invoke-BuildReleaseTargetDataPreflight
Invoke-BuildReleaseSchemaOnlyMigrationRehearsal
}
}

if ($publishBackend) {
Info 'Building backend jar'
Invoke-CheckedMavenCommand -ArgumentList @(
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

Copy-Item -LiteralPath $websiteNginxTemplate -Destination (Join-Path $websiteRuntimeLocal 'nginx.template.conf') -Force
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
Assert-BackendRuntimeBaseImageAvailable -Config $backendRuntimeBaseConfig
}
if ($publishBackend -or $publishFrontend) {
Write-DockerBuildInputEvidence
}

if ($publishBackend) {
Info 'Building backend image'
Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
    'build',
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
    '-t', "intruoyi-frontend:$packageDirectoryName",
    '-f', $frontendDockerfile,
    $dockerBuildContextRoot
)
}

if ($publishBackend -or $publishFrontend) {
Assert-DockerBuildInputsUnchanged
Write-FinalDockerBuildEvidence
}

if ($publishBackend -and $IncludeOnlyOffice) {
    Info 'Checking OnlyOffice image'
    Invoke-CheckedCommand -FilePath 'docker' -ArgumentList @(
        'image',
        'inspect',
        $onlyOfficeImage
    )
}

$managedImageReferences = Get-ReleaseManagedImageReferences -Component $Component -PackageId $packageDirectoryName -OnlyOfficeIncluded ([bool]$IncludeOnlyOffice)
$releaseImages = @($managedImageReferences.Values)
$script:ReleaseRuntimeImages = @(
    foreach ($name in $managedImageReferences.Keys) {
        $identity = Get-DockerImageIdentity -ImageReference $managedImageReferences[$name]
        [ordered]@{ name = $name; reference = $identity.reference; id = $identity.id; sizeBytes = $identity.sizeBytes }
    }
)
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

if ($publishBackend) {
    $smokeRuntimeIdentity = @($script:ReleaseRuntimeImages | Where-Object { $_.name -eq 'scheduler-smoke' })[0]
    New-SchedulerSmokeRunnerPackage -RuntimeImageId $smokeRuntimeIdentity.id
}
if ($Mode -eq 'build-release' -and $publishBackend) { New-ReleaseOpsRuntimePackage }

Write-ReleaseRuntimeEnvPackage
Copy-Item -LiteralPath $composeTemplate -Destination (Join-Path $releaseDir 'docker-compose.yml') -Force
Remove-ReleaseDockerBuildContextFromPackage
Invoke-ReleaseStage -Name 'release manifest generation' -ScriptBlock {
    $script:ReleaseSourceFreezeEvidence = Assert-ReleaseSourceFreeze -VerificationPoint 'before-package' -ExpectedEvidence $script:ReleaseSourceFreezeEvidence
    Write-ReleaseManifest -PackageTag $ReleaseTag
    Write-ReleasePackageSizeSummary -Artifacts (Get-ReleasePackageArtifactCache)
}

if ($smartReleaseReportOnlyEnabled -and $Mode -eq 'build-release') {
    Invoke-SmartReleaseBuildReportOnly -PackagePath $releaseDir
    Invoke-ReleaseStage -Name 'release manifest generation' -ScriptBlock {
        Write-ReleaseManifest -PackageTag $ReleaseTag
        Write-ReleasePackageSizeSummary -Artifacts (Get-ReleasePackageArtifactCache)
    }
}
Invoke-ReleaseStage -Name 'release package integrity verification' -ScriptBlock {
    $releaseManifestArtifacts = Get-ReleasePackageArtifactCache
    $script:buildPackageIntegrity = Test-ReleasePackageIntegrity -PackagePath $releaseDir -ExpectedReleaseTag $ReleaseTag -PreverifiedArtifacts $releaseManifestArtifacts -EmitProgress
}

Invoke-ReleaseStage -Name 'release manifest validation' -ScriptBlock {
    Invoke-ReleaseManifestValidationGate -PackagePath $releaseDir
}

if ($Mode -eq 'build-release') {
    Invoke-ReleaseStage -Name 'NAS release package upload and verification' -ScriptBlock {
        Copy-ReleasePackageToNas -PackageTag $ReleaseTag
    }
    Write-Host ''
    Write-Host "Release package built: $ReleaseTag"
    Write-Host "NAS release path: $NasReleaseRoot/$packageDirectoryName"
    exit 0
}
}
} finally {
    Exit-BuildReleaseRuntimeRestartGuard -GuardFile $buildReleaseRuntimeRestartGuardFile
}


if ($Mode -eq 'deploy-release') {
    if (Test-Path -LiteralPath $deployControlLocalRoot) {
        Remove-Item -LiteralPath $deployControlLocalRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $deployControlLocalRoot | Out-Null
}

if ($Mode -eq 'deploy-release' -and $publishWebsite) {
    Write-ReleaseWebsiteDeployControl
}

Info 'Writing remote compose environment file locally'
if (($publishBackend -or $publishFrontend) -and $Mode -ne 'build-release' -and $existingRemoteEnv.Count -eq 0) {
    Import-ExistingRemoteRuntimeEnvSettings
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
$effectiveDccProjectCodeRecognitionVersion = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeRecognitionVersion)) { $DccProjectCodeRecognitionVersion } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_RECOGNITION_VERSION')) { $existingRemoteEnv['DCC_PROJECT_CODE_RECOGNITION_VERSION'] } else { 'v1' }
$effectiveDccProjectCodeRecognitionWorkerCount = if (-not [string]::IsNullOrWhiteSpace($DccProjectCodeRecognitionWorkerCount)) { $DccProjectCodeRecognitionWorkerCount } elseif ($existingRemoteEnv.ContainsKey('DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT')) { $existingRemoteEnv['DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT'] } else { '5' }
$effectiveShowroomCodexCliCommand = if (-not [string]::IsNullOrWhiteSpace($ShowroomCodexCliCommand)) { $ShowroomCodexCliCommand } elseif ($existingRemoteEnv.ContainsKey('SHOWROOM_CODEX_CLI_COMMAND')) { $existingRemoteEnv['SHOWROOM_CODEX_CLI_COMMAND'] } else { '/opt/intruoyi/runtime/tools/codex' }
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
$effectiveMesSmokeNodeImage = $schedulerSmokeNodeImage
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
$DccProjectCodeRecognitionVersion = $effectiveDccProjectCodeRecognitionVersion
$DccProjectCodeRecognitionWorkerCount = $effectiveDccProjectCodeRecognitionWorkerCount
$ShowroomCodexCliCommand = $effectiveShowroomCodexCliCommand
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
DCC_PROJECT_CODE_RECOGNITION_VERSION=$DccProjectCodeRecognitionVersion
DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT=$DccProjectCodeRecognitionWorkerCount
SHOWROOM_CODEX_CLI_COMMAND=$ShowroomCodexCliCommand
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_MODE=$BackendRuntimeBaseMode
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR=$BackendRuntimeBaseTarPath
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_TAR_SHA256=$BackendRuntimeBaseTarSha256
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_IMAGE=$BackendRuntimeBaseImage
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_DIGEST=$BackendRuntimeBaseDigest
RUNTIME_CONTROL_BACKEND_RUNTIME_BASE_VERSION=$BackendRuntimeBaseVersion
"@
$remoteEnvLocal = Join-Path $deployControlLocalRoot '.env'
if ($Mode -eq 'deploy-release') {
    if ($existingRemoteEnv.Count -eq 0) { Fail 'TARGET_CONFIG_NOT_READY: formal target environment is required' }
    $targetEnvironmentLines = @()
    foreach ($existingKey in @($existingRemoteEnv.Keys | Sort-Object)) {
        if ($existingKey -in @('IMAGE_TAG', 'MES_SMOKE_NODE_IMAGE')) { continue }
        $targetEnvironmentLines += "$existingKey=$($existingRemoteEnv[$existingKey])"
    }
    $targetEnvironmentLines += "IMAGE_TAG=$packageDirectoryName"
    $targetEnvironmentLines += "MES_SMOKE_NODE_IMAGE=$schedulerSmokeNodeImage"
    $remoteEnvContent = ($targetEnvironmentLines -join "`n") + "`n"
} else {
    $remoteEnvContent += "`n" + ((Get-ReleasePlatformIdentityEnvironmentLines) -join "`n") + "`n"
}
if (-not (Test-Path -LiteralPath $deployControlLocalRoot -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $deployControlLocalRoot | Out-Null
}
Write-Utf8LfNoBomFile -Path $remoteEnvLocal -Content $remoteEnvContent
$requiresReleaseOperationLock = ($Mode -eq 'deploy-release') -and ($publishBackend -or $publishFrontend -or $publishWebsite)

function Invoke-ReleaseDeploymentExecution {
try {
    if ($Mode -eq 'deploy-release') {
        if(Test-ReleaseDeploymentAlreadyCommitted){Info 'Existing committed deployment verified without replay';return}
        Write-ReleasePreflightPlan
        Assert-ReleasePersistentDeploymentGate
    }
    if ($requiresReleaseOperationLock) {
        Enter-ReleaseOperationLock
    }
    if ($Mode -eq 'deploy-release') {
        Write-ReleasePreflightPlan -Verify
        Assert-ReleasePersistentDeploymentGate -Verify
        Initialize-ReleaseDeploymentEvidence
    }

    Start-ReleaseDeploymentPhase -Name 'preparing'
    Assert-ReleaseOperationWriteFence
    Info 'Preparing remote runtime data disk'
    Assert-RemoteRuntimeDataOnDataDisk

    Assert-ReleaseOperationWriteFence
    Info 'Preparing remote release directories'
    Prepare-RemoteReleaseTree

    Assert-ReleaseOperationWriteFence
    Info "Copying deploy control files to the $PublishTargetName server"
$composeLocal = Join-Path $releaseDir 'docker-compose.yml'
if (-not (Test-Path -LiteralPath $composeLocal -PathType Leaf)) {
    Fail 'PACKAGE_REQUIRED_ARTIFACT_MISSING: docker-compose.yml; rebuild the complete package'
}
Copy-DeployControlFilesToServer -ComposeLocal $composeLocal
if ($publishBackend -or $publishFrontend) {
    Assert-ReleaseOperationLockOwnership
    Assert-RemoteRuntimeEnvImageTag -Path $remoteEnvNext -Label 'Remote runtime .env.next'
    if ($publishBackend) {
        Assert-RemoteRuntimeEnvEdhrEndpoint
    }
}
if ($publishBackend) {
    Assert-ReleaseOperationLockOwnership
    Copy-SchedulerSmokeRunnerToServer
}
if ($publishBackend -or $publishFrontend) {
    Assert-ReleaseOperationLockOwnership
    Copy-LargeFileToServerInChunks -LocalPath $imageTar -RemotePath $remoteImageTar
}
if ($publishBackend) {
    Assert-ReleaseOperationLockOwnership
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

Complete-ReleaseDeploymentPhase
Start-ReleaseDeploymentPhase -Name 'loading'
if ($publishBackend -or $publishFrontend) {
    Assert-ReleaseOperationLockOwnership
    Info "Loading release images on the $PublishTargetName server"
    Invoke-SshCommand "docker load -i '$remoteImageTar'"
}
Complete-ReleaseDeploymentPhase

    Start-ReleaseDeploymentPhase -Name 'migrating'
    if ($publishBackend) {
        Invoke-RequiredDatabaseSqlScripts
        Assert-RemoteQuartzSchemaReady
        Assert-RemoteShowroomAwardSchemaReady
    }

    if ($publishBackend) {
        Assert-RemoteFileStorageConfigRebound
    }
    Complete-ReleaseDeploymentPhase

    Start-ReleaseDeploymentPhase -Name 'switching'
    if ($publishWebsite) {
        Assert-ReleaseOperationWriteFence
        Info "Switching Website runtime directory on the $PublishTargetName server"
        Invoke-SshCommand "test -f '$remoteWebsiteStagingDir/dist/index.html' && test -f '$remoteWebsiteStagingDir/nginx.conf' && rm -rf '$remoteWebsitePreviousDir' && if [ -d '$remoteWebsiteDir' ]; then mv '$remoteWebsiteDir' '$remoteWebsitePreviousDir'; fi && mv '$remoteWebsiteStagingDir' '$remoteWebsiteDir'"
    }

    if ($publishBackend -or $publishFrontend) {
        Assert-ReleaseOperationWriteFence
        Info "Switching runtime .env to $packageDirectoryName on the $PublishTargetName server"
        Switch-RemoteRuntimeEnvNext
    }

    $runtimeServices = @()
    if ($IncludeOnlyOffice) { $runtimeServices += 'onlyoffice' }
    if ($publishBackend) { $runtimeServices += 'backend' }
    if ($publishFrontend) { $runtimeServices += 'frontend' }
    if ($runtimeServices.Count -gt 0) {
        Assert-ReleaseOperationWriteFence
        Assert-ReleaseSelectedImagesLoaded
        $runtimeServicesArg = $runtimeServices -join ' '
        Info "Starting application services on the $PublishTargetName server: $runtimeServicesArg"
        Invoke-SshCommand "cd '$RemoteAppDir' && docker compose up -d --force-recreate --no-deps --pull never $runtimeServicesArg"
    }

    if ($publishWebsite) {
        Assert-ReleaseOperationWriteFence
        Info "Starting Website on the $PublishTargetName server"
    }
    if ($publishWebsite) { Invoke-SshCommand "cd '$RemoteAppDir' && docker compose up -d --force-recreate --no-deps --pull never website" }
    Complete-ReleaseDeploymentPhase
    Start-ReleaseDeploymentPhase -Name 'verifying'
    Assert-RemoteActualApplicationImages
    if ($publishWebsite) { Assert-RemoteWebsitePayloadIdentity }

    Info 'Waiting for remote HTTP readiness'
    if ($publishBackend) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'backend-health' -Action { Wait-RemoteHttpOk -Url "http://127.0.0.1:$BackendPort/actuator/health" -TimeoutSeconds 180; Assert-RemoteBackendHealthStatus }
        Invoke-ReleaseRuntimeVerificationCheck -Name 'backend-minio-config' -Action { Assert-RemoteBackendContainerMinioReachable }
    }
    if ($publishFrontend) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'frontend-health' -Action { Wait-RemoteHttpOk -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSeconds 180 }
    }
    if ($publishBackend) { Invoke-ReleaseRuntimeVerificationCheck -Name 'scheduler-smoke-config' -Action { Assert-RemoteSchedulerSmokeRuntime } }
    if ($IncludeOnlyOffice) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'onlyoffice-health' -Action { Wait-RemoteHttpOk -Url "http://127.0.0.1:$OnlyOfficeHostPort/healthcheck" -TimeoutSeconds 180 }
    }
    if ($publishWebsite) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'website-health' -Action { Wait-RemoteHttpOk -Url "http://127.0.0.1:$WebsiteHostPort/showroom" -TimeoutSeconds 180 }
    }

    if ($publishBackend) { Invoke-ReleaseRuntimeVerificationCheck -Name 'backend-public-health' -Action { Wait-HttpOk -Url "http://${ServerHost}:$BackendPort/actuator/health" -TimeoutSeconds 180 } }
    if ($publishFrontend) { Invoke-ReleaseRuntimeVerificationCheck -Name 'frontend-public-health' -Action { Wait-HttpOk -Url "http://${ServerHost}:$FrontendPort/" -TimeoutSeconds 180 } }
    if ($publishFrontend) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'frontend-worker-content-type' -Action { Wait-HttpContentTypeOk -Url "http://${ServerHost}:$FrontendPort/pdfjs/pdf.worker.mjs" -ExpectedContentType 'application/javascript' -TimeoutSeconds 180 }
    }
    $verifyShowroomMediaContent = $publishWebsite -or (-not $SkipMinioSync)
    if ($publishFrontend -and $verifyShowroomMediaContent) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'showroom-media-content' -Action { Assert-RemoteShowroomSmokeImageContent }
    } elseif ($publishFrontend) {
        Info 'Skipping showroom smoke image content check for code-only deploy without Website or MinIO data sync'
    }
    if ($publishBackend -and $IncludeOnlyOffice) {
        Invoke-ReleaseRuntimeVerificationCheck -Name 'onlyoffice-public-health' -Action { Wait-HttpOk -Url "http://${ServerHost}:$OnlyOfficeHostPort/healthcheck" -TimeoutSeconds 180 }
    }
    if ($publishWebsite) { Invoke-ReleaseRuntimeVerificationCheck -Name 'website-root-public-health' -Action { Wait-HttpOk -Url "http://${ServerHost}:$WebsiteHostPort/" -TimeoutSeconds 180 } }
    if ($publishWebsite) { Invoke-ReleaseRuntimeVerificationCheck -Name 'website-public-health' -Action { Wait-HttpOk -Url "http://${ServerHost}:$WebsiteHostPort/showroom" -TimeoutSeconds 180 } }
    if ($publishWebsite) { Invoke-ReleaseRuntimeVerificationCheck -Name 'website-entry-content' -Action { Assert-PublicWebsiteEntryReadback } }
    if ($publishWebsite) { Invoke-ReleaseRuntimeVerificationCheck -Name 'website-current-release' -Action { Assert-PublicWebsiteScopedReleaseCurrent } }

    Complete-ReleaseDeploymentPhase
    Complete-ReleaseDeployment
} catch {
    $releaseErrorMessage=$_.Exception.Message
    Register-ReleaseDeploymentFailure -OriginalError $releaseErrorMessage
    throw
}
}

Invoke-ReleaseDeploymentExecution
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
