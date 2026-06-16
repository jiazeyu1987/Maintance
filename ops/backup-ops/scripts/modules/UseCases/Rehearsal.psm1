Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function New-RehearsalEvidenceException {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code,
        [Parameter(Mandatory = $true)]
        [ValidateSet('blocked', 'fail')]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsCode'] = $Code
    $exception.Data['BackupOpsStatus'] = $Status
    return $exception
}

function Get-RehearsalConfigValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$InputObject,
        [Parameter(Mandatory = $true)]
        [string[]]$Path
    )

    $current = $InputObject
    foreach ($segment in $Path) {
        if ($null -eq $current) {
            return $null
        }

        if ($current -is [System.Collections.IDictionary]) {
            if (-not $current.Contains($segment)) {
                return $null
            }
            $current = $current[$segment]
            continue
        }

        $property = $current.PSObject.Properties[$segment]
        if ($null -eq $property) {
            return $null
        }
        $current = $property.Value
    }

    return $current
}

function Get-RehearsalRequiredConfigValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string[]]$Path,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $value = Get-RehearsalConfigValue -InputObject $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw (New-RehearsalEvidenceException -Code 'INTBK-7002' -Status 'blocked' -Message "缺少恢复演练证据写回所需配置：$FieldName")
    }

    return $value
}

function Get-RehearsalTestSshRequest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    $request = @{
        Host = [string](Get-RehearsalRequiredConfigValue -Config $Config -Path @('servers', 'test', 'host') -FieldName 'servers.test.host')
        User = [string](Get-RehearsalRequiredConfigValue -Config $Config -Path @('ssh', 'user') -FieldName 'ssh.user')
        KeyPath = [string](Get-RehearsalRequiredConfigValue -Config $Config -Path @('auth', 'sshKeyPath') -FieldName 'auth.sshKeyPath')
    }

    $port = Get-RehearsalConfigValue -InputObject $Config -Path @('ssh', 'port')
    $request['Port'] = if ($null -eq $port) { 22 } else { [int]$port }

    $knownHostsPath = Get-RehearsalConfigValue -InputObject $Config -Path @('auth', 'knownHostsPath')
    if ($null -ne $knownHostsPath -and -not [string]::IsNullOrWhiteSpace([string]$knownHostsPath)) {
        $request['KnownHostsPath'] = [string]$knownHostsPath
    }

    return $request
}

function Get-RehearsalTempPath {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Segments
    )

    $root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
    $path = Join-Path $root 'tmp'
    foreach ($segment in $Segments) {
        if (-not [string]::IsNullOrWhiteSpace($segment)) {
            $path = Join-Path $path $segment
        }
    }

    [void][System.IO.Directory]::CreateDirectory($path)
    return $path
}

function ConvertTo-BackupOpsRehearsalCheckSummary {
    param(
        [object]$Checks
    )

    if ($null -eq $Checks) {
        return @()
    }

    $items = @()
    if ($Checks -is [System.Collections.IDictionary]) {
        foreach ($key in $Checks.Keys) {
            $items += ('{0}: {1}' -f $key, $Checks[$key])
        }
        return $items
    }

    foreach ($property in $Checks.PSObject.Properties) {
        $items += ('{0}: {1}' -f $property.Name, $property.Value)
    }

    return $items
}

function Write-BackupOpsRehearsalEvidence {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [hashtable]$Context,
        [Parameter(Mandatory = $true)]
        [object]$StartedAt,
        [Parameter(Mandatory = $true)]
        [object]$CompletedAt,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $backupPointsRoot = [string](Get-RehearsalRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -FieldName 'servers.test.backupPointsRoot')
    $testSshRequest = Get-RehearsalTestSshRequest -Config $Config
    $remoteManifestDir = "$($backupPointsRoot.TrimEnd('/'))/$BackupId/manifest"
    $localEvidenceDir = Get-RehearsalTempPath -Segments @('rehearsal', $BackupId, 'evidence')
    $localReportPath = Join-Path $localEvidenceDir 'rehearsal-report.json'
    $localSnapshotPath = Join-Path $localEvidenceDir '现场快照.md'
    $verifiedAt = ([System.DateTimeOffset]$CompletedAt).ToString('o')
    $checkSummary = ConvertTo-BackupOpsRehearsalCheckSummary -Checks $Context['checks']

    $report = [pscustomobject]([ordered]@{
            status = 'PASSED'
            lastVerifiedAt = $verifiedAt
            backupId = $BackupId
            imageTag = $Context['imageTag']
            startedAt = ([System.DateTimeOffset]$StartedAt).ToString('o')
            completedAt = $verifiedAt
            checks = $Context['checks']
            checkSummary = $checkSummary
        })
    [System.IO.File]::WriteAllText($localReportPath, ($report | ConvertTo-Json -Depth 10), $script:BackupOpsUtf8NoBom)

    $snapshotLines = @(
        '# 现场快照',
        '',
        "- 演练对象: 恢复演练",
        "- 备份点: $BackupId",
        "- 时间: $verifiedAt",
        "- 镜像: $($Context['imageTag'])",
        '',
        '## 关键校验摘要'
    )
    if ($checkSummary.Count -eq 0) {
        $snapshotLines += '- 未返回明细校验项'
    } else {
        foreach ($item in $checkSummary) {
            $snapshotLines += "- $item"
        }
    }
    [System.IO.File]::WriteAllLines($localSnapshotPath, $snapshotLines, $script:BackupOpsUtf8NoBom)

    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localSnapshotPath
            RemotePath = "$remoteManifestDir/现场快照.md"
        }) | Out-Null
    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localReportPath
            RemotePath = "$remoteManifestDir/rehearsal-report.json"
        }) | Out-Null
    Write-BackupOpsLog -Session $LogSession -Message "Wrote rehearsal evidence files for backup $BackupId."
}

function Test-RehearsalScheduledOperator {
    param(
        [string]$OperatorName
    )

    return ([string]$OperatorName).Trim().Equals('scheduler', [System.StringComparison]::OrdinalIgnoreCase)
}

function New-RehearsalFailureResult {
    param(
        [object]$Config,
        [datetime]$StartedAt,
        [object]$LogSession,
        [hashtable]$Context,
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $status = 'fail'
    $code = 'INTBK-7002'
    $message = $ErrorRecord.Exception.Message
    if ($ErrorRecord.Exception.Data.Contains('BackupOpsStatus')) {
        $status = [string]$ErrorRecord.Exception.Data['BackupOpsStatus']
    }

    if ($ErrorRecord.Exception.Data.Contains('BackupOpsCode')) {
        $code = [string]$ErrorRecord.Exception.Data['BackupOpsCode']
    }

    if ($Context.ContainsKey('backupId') -and -not [string]::IsNullOrWhiteSpace([string]$Context['backupId'])) {
        try {
            Set-BackupOpsRehearsalVerificationState -Config $Config -BackupId ([string]$Context['backupId']) -RehearsalStatus 'pending-review' -Note $message -LogSession $LogSession
        }
        catch {
            # 演练失败后尽力降级备份点，但不要覆盖原始失败原因
        }
    }

    if ($null -ne $LogSession) {
        $notificationResult = Invoke-BackupOpsNotificationCapture `
            -Config $Config `
            -Action 'rehearsal' `
            -Status $status `
            -Summary ("恢复演练失败。{0}" -f $message) `
            -Context $Context `
            -LogSession $LogSession
        Set-BackupOpsNotificationContext -Context $Context -NotificationResult $notificationResult
        $message = $message + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)
    }

    return Complete-BackupOpsOutcome `
        -Config $Config `
        -Action 'rehearsal' `
        -Status $status `
        -Code $code `
        -Message $message `
        -StartedAt $StartedAt `
        -CompletedAt (Get-Date) `
        -Context $Context `
        -LogSession $LogSession
}

function Invoke-RehearsalUseCase {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$SelectedBackupId,

        [string]$OperatorName = ''
    )

    $startedAt = Get-Date
    $logSession = $null
    $resultContext = @{
        backupId = $SelectedBackupId
        imageTag = $null
        checks = $null
    }
    $successMessage = '恢复演练完成。'

    try {
        $logSession = Start-BackupOpsLogSession -Config $Config -Action 'rehearsal' -OperatorName $OperatorName -StartedAt $startedAt

        Show-BackupOpsProgress -Current 1 -Total 5 -Message '选择最近一次 nightly 备份...'
        if ([string]::IsNullOrWhiteSpace($SelectedBackupId)) {
            if (-not (Test-RehearsalScheduledOperator -OperatorName $OperatorName)) {
                throw (New-RehearsalEvidenceException -Code 'INTBK-7001' -Status 'blocked' -Message 'rehearsal requires explicit SelectedBackupId unless OperatorName is scheduler.')
            }
            $latestBackup = Get-BackupOpsLatestBackup -Config $Config -LogSession $logSession
            $resultContext.backupId = $latestBackup.BackupId
            $resultContext.imageTag = $latestBackup.ImageTag
        } else {
            $selectedCandidate = Get-BackupOpsRehearsalCandidate -Config $Config -BackupId $SelectedBackupId -LogSession $logSession
            $resultContext.backupId = [string]$selectedCandidate.backupId
            if ($selectedCandidate.PSObject.Properties['imageTag']) {
                $resultContext.imageTag = [string]$selectedCandidate.imageTag
            }
        }

        Show-BackupOpsProgress -Current 2 -Total 5 -Message '恢复到测试演练槽位...'
        $rehearsalRestore = Restore-BackupOpsRehearsalRuntime -Config $Config -BackupId $resultContext.backupId -LogSession $logSession
        if ($rehearsalRestore -and $rehearsalRestore.PSObject.Properties['imageTag'] -and [string]::IsNullOrWhiteSpace([string]$resultContext.imageTag)) {
            $resultContext.imageTag = [string]$rehearsalRestore.imageTag
        }

        Show-BackupOpsProgress -Current 3 -Total 5 -Message '执行 backend / frontend / login / 文件抽样校验...'
        $rehearsalValidation = Test-BackupOpsRehearsalValidation -Config $Config -BackupId $resultContext.backupId -LogSession $logSession
        if ($rehearsalValidation -and $rehearsalValidation.PSObject.Properties['checks']) {
            $resultContext.checks = $rehearsalValidation.checks
        }
        Set-BackupOpsRehearsalVerificationState -Config $Config -BackupId $resultContext.backupId -RehearsalStatus 'PASSED' -LogSession $logSession
        $evidenceCompletedAt = Get-Date
        Write-BackupOpsRehearsalEvidence -Config $Config -BackupId $resultContext.backupId -Context $resultContext -StartedAt $startedAt -CompletedAt $evidenceCompletedAt -LogSession $logSession

        Show-BackupOpsProgress -Current 4 -Total 5 -Message '生成演练报告...'
        $report = Publish-BackupOpsReport -Config $Config -Action 'rehearsal' -Status 'success' -StartedAt $startedAt -CompletedAt (Get-Date) -Summary 'Rehearsal restore completed successfully.' -Context $resultContext -LogSession $logSession
        $logSession.LogPath = $report.LogPath
        $logSession.ReportPath = $report.ReportPath

        Show-BackupOpsProgress -Current 5 -Total 5 -Message '发送通知...'
        $notificationResult = Send-BackupOpsNotification -Config $Config -Action 'rehearsal' -Status 'success' -Summary '恢复演练完成；已在测试演练槽位执行恢复并完成校验。' -Context $resultContext -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
        $successMessage = '恢复演练完成。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)

        $successParams = @{
            Action = 'rehearsal'
            Status = 'success'
            Code = 'INTBK-0000'
            Message = $successMessage
            StartedAt = $startedAt
            CompletedAt = (Get-Date)
            LogPath = $logSession.LogPath
            ReportPath = $logSession.ReportPath
            Context = $resultContext
        }

        return New-BackupOpsResult @successParams
    }
    catch {
        return New-RehearsalFailureResult -Config $Config -StartedAt $startedAt -LogSession $logSession -Context $resultContext -ErrorRecord $_
    }
}

Export-ModuleMember -Function 'Invoke-RehearsalUseCase'
