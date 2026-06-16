param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('backup-now', 'backup-scheduled', 'rollback-app', 'restore-data', 'rehearsal')]
    [string]$Mode,

    [string]$ConfigPath,

    [string]$SecretsPath,

    [string]$SelectedBackupId,

    [string]$SelectedImageTag,

    [string]$ProductionBackupConfirmText,

    [ValidateSet('prod', 'test', 'backup')]
    [string]$TargetEnvironment = 'prod',

    [switch]$NonInteractive,

    [string]$OperatorName = $env:USERNAME
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$script:BackupOpsStartedAt = Get-Date
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backupOpsRoot = Split-Path -Parent $scriptRoot
$modulesRoot = Join-Path $scriptRoot 'modules'

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $backupOpsRoot 'config\backup-ops.config.json'
}

if ([string]::IsNullOrWhiteSpace($SecretsPath)) {
    $SecretsPath = Join-Path $backupOpsRoot 'config\backup-ops.secrets.json'
}

$requiredModulePaths = @(
    'Core\Config.psm1',
    'Core\Logging.psm1',
    'Core\ResultModel.psm1',
    'Core\Validation.psm1',
    'Infra\SshOps.psm1',
    'Infra\DockerOps.psm1',
    'Infra\MySqlOps.psm1',
    'Infra\ObjectOps.psm1',
    'Infra\FileOps.psm1',
    'Infra\ReportOps.psm1',
    'Infra\NotifyOps.psm1',
    'UseCases\BackupNow.psm1',
    'UseCases\BackupScheduled.psm1',
    'UseCases\RollbackApp.psm1',
    'UseCases\RestoreData.psm1',
    'UseCases\Rehearsal.psm1',
    'Ui\ConsoleMenu.psm1',
    'Ui\ConsolePrompt.psm1'
)

function New-LauncherResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Status,

        [Parameter(Mandatory = $true)]
        [string]$Code,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [hashtable]$Context = @{}
    )

    [pscustomobject]@{
        action = $Mode
        status = $Status
        code = $Code
        message = $Message
        startedAt = $script:BackupOpsStartedAt.ToString('o')
        completedAt = (Get-Date).ToString('o')
        logPath = $null
        reportPath = $null
        context = $Context
    }
}

function New-BackupOpsLauncherException {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [ValidateSet('blocked', 'fail')]
        [string]$Status = 'fail',

        [string]$Code = 'INTBK-2003'
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsStatus'] = $Status
    $exception.Data['BackupOpsCode'] = $Code
    return $exception
}

function Show-LauncherResult {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    switch ($Result.status) {
        'success' {
            Write-Host '操作完成：成功' -ForegroundColor Green
        }
        'blocked' {
            Write-Host '操作未执行：需人工介入' -ForegroundColor Yellow
        }
        default {
            Write-Host '操作完成：失败' -ForegroundColor Red
        }
    }

    Write-Host ("动作类型：{0}" -f $Result.action)
    Write-Host ("结果代码：{0}" -f $Result.code)
    Write-Host ("结果说明：{0}" -f $Result.message)

    if ($Result.logPath) {
        Write-Host ("日志路径：{0}" -f $Result.logPath)
    }

    if ($Result.reportPath) {
        Write-Host ("报告路径：{0}" -f $Result.reportPath)
    }
}

function Resolve-BackupOpsExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    switch ($Result.status) {
        'success' { return 0 }
        'blocked' { return 2 }
        default { return 1 }
    }
}

function Get-BackupOpsLauncherConfigValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [Parameter(Mandatory = $true)]
        [string[]]$Path
    )

    $current = $Config
    foreach ($segment in $Path) {
        if ($null -eq $current -or -not $current.PSObject.Properties[$segment]) {
            return $null
        }
        $current = $current.$segment
    }
    return $current
}

function Get-BackupOpsRequiredLauncherConfigValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [Parameter(Mandatory = $true)]
        [string[]]$Path,

        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $value = Get-BackupOpsLauncherConfigValue -Config $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw "Required configuration is missing: $FieldName"
    }
    return $value
}

function Assert-BackupOpsProductionBackupConfirmation {
    param(
        [AllowEmptyString()]
        [string]$ConfirmText,

        [Parameter(Mandatory = $true)]
        [switch]$NonInteractive
    )

    $expectedConfirmText = 'PROD-BACKUP-172.30.30.57'
    $resolvedConfirmText = [string]$ConfirmText
    if ([string]::IsNullOrWhiteSpace($resolvedConfirmText) -and -not $NonInteractive) {
        $resolvedConfirmText = Read-Host "请输入正式备份确认文本（必须完全一致：$expectedConfirmText）"
    }

    if ([string]::IsNullOrWhiteSpace($resolvedConfirmText)) {
        throw (New-BackupOpsLauncherException -Status 'blocked' -Code 'INTBK-1003' -Message "原因：Production backup confirmation is required before running backup-now or backup-scheduled against TargetEnvironment prod.`n建议动作：请显式传入 -ProductionBackupConfirmText '$expectedConfirmText' 后重试。")
    }

    if ($resolvedConfirmText.Trim() -ne $expectedConfirmText) {
        throw (New-BackupOpsLauncherException -Status 'blocked' -Code 'INTBK-1003' -Message "原因：正式备份确认文本不正确，必须完全匹配 '$expectedConfirmText'，当前值为 '$resolvedConfirmText'.`n建议动作：请重新输入 -ProductionBackupConfirmText '$expectedConfirmText' 后重试。")
    }
}

function Resolve-BackupOpsTargetEnvironmentConfig {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    if ($Mode -eq 'restore-data' -and $TargetEnvironment -eq 'prod') {
        throw (New-BackupOpsLauncherException -Status 'blocked' -Code 'INTBK-1003' -Message "原因：restore-data only supports TargetEnvironment test or backup; production restore-data is forbidden.`n建议动作：请显式传入 -TargetEnvironment test 或 backup 后再执行恢复。")
    }

    if ($Mode -in @('backup-now', 'backup-scheduled') -and $TargetEnvironment -eq 'prod') {
        Assert-BackupOpsProductionBackupConfirmation -ConfirmText $ProductionBackupConfirmText -NonInteractive:$NonInteractive
    }

    if ($TargetEnvironment -eq 'prod') {
        return $Config
    }

    $supportedTargetEnvironments = @('test', 'backup')
    if ($TargetEnvironment -notin $supportedTargetEnvironments) {
        throw 'TargetEnvironment must be prod, test, or backup.'
    }

    $supportedTestTargetModes = @('backup-now', 'backup-scheduled', 'rollback-app', 'restore-data')
    if ($Mode -notin $supportedTestTargetModes) {
        throw 'TargetEnvironment test/backup is only supported for backup-now, backup-scheduled, rollback-app and restore-data.'
    }

    $targetHost = [string](Get-BackupOpsRequiredLauncherConfigValue -Config $Config -Path @('servers', $TargetEnvironment, 'host') -FieldName "servers.$TargetEnvironment.host")
    $targetRuntimeDir = [string](Get-BackupOpsRequiredLauncherConfigValue -Config $Config -Path @('servers', $TargetEnvironment, 'runtimeDir') -FieldName "servers.$TargetEnvironment.runtimeDir")
    $targetTmpRoot = [string](Get-BackupOpsRequiredLauncherConfigValue -Config $Config -Path @('servers', $TargetEnvironment, 'tmpRoot') -FieldName "servers.$TargetEnvironment.tmpRoot")
    $targetMinioContainer = [string](Get-BackupOpsRequiredLauncherConfigValue -Config $Config -Path @('servers', $TargetEnvironment, 'minioContainer') -FieldName "servers.$TargetEnvironment.minioContainer")
    $clone = $Config | ConvertTo-Json -Depth 32 | ConvertFrom-Json
    $clone.environment = $TargetEnvironment
    $clone.servers.production.host = $targetHost
    $clone.servers.production.appDir = $targetRuntimeDir
    if (-not $clone.servers.production.PSObject.Properties['tmpRoot']) {
        Add-Member -InputObject $clone.servers.production -MemberType NoteProperty -Name 'tmpRoot' -Value ''
    }
    $clone.servers.production.tmpRoot = $targetTmpRoot
    $clone.containers.minio = $targetMinioContainer
    return $clone
}

function Get-MissingBackupOpsPrerequisites {
    $missing = New-Object System.Collections.Generic.List[string]

    foreach ($relativePath in $requiredModulePaths) {
        $modulePath = Join-Path $modulesRoot $relativePath
        if (-not (Test-Path -LiteralPath $modulePath)) {
            $missing.Add($modulePath)
        }
    }

    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        $missing.Add($ConfigPath)
    }

    if (-not (Test-Path -LiteralPath $SecretsPath)) {
        $missing.Add($SecretsPath)
    }

    return @($missing.ToArray())
}

function Import-BackupOpsModules {
    foreach ($relativePath in $requiredModulePaths) {
        $modulePath = Join-Path $modulesRoot $relativePath
        Import-Module -Name $modulePath -Force -DisableNameChecking
    }
}

function Invoke-BackupOpsMode {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    switch ($Mode) {
        'backup-now' {
            return Invoke-BackupNowUseCase -Config $Config -OperatorName $OperatorName -NonInteractive:$NonInteractive
        }
        'backup-scheduled' {
            return Invoke-BackupScheduledUseCase -Config $Config -OperatorName $OperatorName
        }
        'rollback-app' {
            return Invoke-RollbackAppUseCase -Config $Config -SelectedImageTag $SelectedImageTag -OperatorName $OperatorName -NonInteractive:$NonInteractive
        }
        'restore-data' {
            return Invoke-RestoreDataUseCase -Config $Config -SelectedBackupId $SelectedBackupId -OperatorName $OperatorName -NonInteractive:$NonInteractive
        }
        'rehearsal' {
            return Invoke-RehearsalUseCase -Config $Config -SelectedBackupId $SelectedBackupId -OperatorName $OperatorName
        }
        default {
            throw "Unsupported mode: $Mode"
        }
    }
}

try {
    $missingPrerequisites = Get-MissingBackupOpsPrerequisites
    if (@($missingPrerequisites).Count -gt 0) {
        $missingMessage = "缺少启动所需文件:`n- {0}" -f ($missingPrerequisites -join "`n- ")
        $blockedResult = New-LauncherResult -Status 'blocked' -Code 'INTBK-1001' -Message $missingMessage -Context @{
            missingPaths = $missingPrerequisites
            configPath = $ConfigPath
            secretsPath = $SecretsPath
        }
        Show-LauncherResult -Result $blockedResult
        exit 2
    }

    Import-BackupOpsModules

    $config = Import-BackupOpsConfiguration -ConfigPath $ConfigPath -SecretsPath $SecretsPath
    Assert-BackupOpsSupportedMode -Mode $Mode
    $config = Resolve-BackupOpsTargetEnvironmentConfig -Config $config
    $result = Invoke-BackupOpsMode -Config $config

    if ($null -eq $result) {
        $result = New-BackupOpsResult `
            -Action $Mode `
            -Status 'fail' `
            -Code 'INTBK-1004' `
            -Message 'Use case returned no result object.' `
            -StartedAt $script:BackupOpsStartedAt `
            -CompletedAt (Get-Date) `
            -LogPath $null `
            -ReportPath $null `
            -Context @{}
    }

    Show-BackupOpsOperationResult -Result $result

    $exitCode = Resolve-BackupOpsExitCode -Result $result
    switch ($exitCode) {
        0 { exit 0 }
        1 { exit 1 }
        2 { exit 2 }
        default { exit 1 }
    }
}
catch {
    $status = if ($_.Exception.Data.Contains('BackupOpsStatus')) { [string]$_.Exception.Data['BackupOpsStatus'] } else { 'fail' }
    $code = if ($_.Exception.Data.Contains('BackupOpsCode')) { [string]$_.Exception.Data['BackupOpsCode'] } else { 'INTBK-2003' }
    $failedResult = New-LauncherResult -Status $status -Code $code -Message $_.Exception.Message -Context @{
        mode = $Mode
        configPath = $ConfigPath
        secretsPath = $SecretsPath
    }
    Show-LauncherResult -Result $failedResult
    if ($status -eq 'blocked') {
        exit 2
    }
    exit 1
}
