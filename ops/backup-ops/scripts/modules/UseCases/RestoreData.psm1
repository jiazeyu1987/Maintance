Set-StrictMode -Version Latest

function New-RestoreDataTargetEnvironmentException {
    param(
        [string]$Message
    )

    $exception = New-Object System.Exception($Message)
    $exception.Data['BackupOpsCode'] = 'INTBK-3002'
    $exception.Data['BackupOpsStatus'] = 'blocked'
    return $exception
}

function Assert-RestoreDataTargetEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    $environment = ''
    if ($Config.PSObject.Properties['environment']) {
        $environment = [string]$Config.environment
    }

    if ($environment -notin @('test', 'backup')) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'restore-data only supports TargetEnvironment test or backup; production restore-data is forbidden.')
    }
}

function Get-RestoreDataCandidateField {
    param(
        [object]$Candidate,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if ($null -eq $Candidate -or -not $Candidate.PSObject.Properties[$Name]) {
        return ''
    }

    return ([string]$Candidate.PSObject.Properties[$Name].Value).Trim()
}

function Assert-RestoreDataRecoverySetCompatibility {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [object]$Candidate,

        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    if ($null -eq $Candidate) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Selected restore candidate metadata is missing; restore-data cannot prove recoverySet compatibility.')
    }

    $rehearsalStatus = Get-RestoreDataCandidateField -Candidate $Candidate -Name 'rehearsalStatus'
    $lastRehearsedAt = Get-RestoreDataCandidateField -Candidate $Candidate -Name 'lastRehearsedAt'
    if (@('PASSED', 'passed', 'pass') -notcontains $rehearsalStatus -or [string]::IsNullOrWhiteSpace($lastRehearsedAt)) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before restore-data.')
    }

    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'backupStrategyMode'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest backupStrategy.mode is missing.')
    }
    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'mysqlBackupMode'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest backupStrategy.mysqlBackupMode is missing.')
    }

    $candidateImageTag = Get-RestoreDataCandidateField -Candidate $Candidate -Name 'imageTag'
    if ([string]::IsNullOrWhiteSpace($candidateImageTag)) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.program.imageTag is missing.')
    }

    $currentImageTag = ([string](Get-BackupOpsCurrentImageTag -Config $Config -LogSession $LogSession)).Trim()
    if ([string]::IsNullOrWhiteSpace($currentImageTag)) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Current runtime IMAGE_TAG is missing; restore-data cannot prove program compatibility.')
    }
    if ($candidateImageTag -ne $currentImageTag) {
        throw (New-RestoreDataTargetEnvironmentException -Message ("Restore manifest recoverySet.program.imageTag {0} does not match current runtime IMAGE_TAG {1}." -f $candidateImageTag, $currentImageTag))
    }

    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'redisPolicy'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.redis.policy is missing.')
    }
    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'configurationManifestPath'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.configuration.manifestPath is missing.')
    }
    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'configurationComposePath'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.configuration.composePath is missing.')
    }
    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'checksumsSha256'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.checksums.sha256 is missing.')
    }
    if ([string]::IsNullOrWhiteSpace((Get-RestoreDataCandidateField -Candidate $Candidate -Name 'dccBackupManifestPath'))) {
        throw (New-RestoreDataTargetEnvironmentException -Message 'Restore manifest recoverySet.dcc.manifestPath is missing.')
    }
}

function New-RestoreDataFailureResult {
    param(
        [object]$Config,
        [datetime]$StartedAt,
        [object]$LogSession,
        [hashtable]$Context,
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $status = 'fail'
    $code = 'INTBK-3002'
    $message = $ErrorRecord.Exception.Message
    if ($ErrorRecord.Exception.Data.Contains('BackupOpsStatus')) {
        $status = [string]$ErrorRecord.Exception.Data['BackupOpsStatus']
    }

    if ($ErrorRecord.Exception.Data.Contains('BackupOpsCode')) {
        $code = [string]$ErrorRecord.Exception.Data['BackupOpsCode']
    }

    if ($null -ne $LogSession) {
        $notificationResult = Invoke-BackupOpsNotificationCapture `
            -Config $Config `
            -Action 'restore-data' `
            -Status $status `
            -Summary ("数据恢复失败。{0}" -f $message) `
            -Context $Context `
            -LogSession $LogSession
        Set-BackupOpsNotificationContext -Context $Context -NotificationResult $notificationResult
        $message = $message + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)
    }

    return Complete-BackupOpsOutcome `
        -Config $Config `
        -Action 'restore-data' `
        -Status $status `
        -Code $code `
        -Message $message `
        -StartedAt $StartedAt `
        -CompletedAt (Get-Date) `
        -Context $Context `
        -LogSession $LogSession
}

function Invoke-RestoreDataUseCase {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$SelectedBackupId,

        [string]$OperatorName = $env:USERNAME,

        [switch]$NonInteractive
    )

    $startedAt = Get-Date
    $logSession = $null
    $resultContext = @{
        backupId = $null
        restorePoint = $null
        imageTag = $null
        preRestoreSnapshotId = $null
        startNotification = $null
    }
    $successMessage = '数据恢复完成。'

    try {
        Assert-RestoreDataTargetEnvironment -Config $Config

        $logSession = Start-BackupOpsLogSession -Config $Config -Action 'restore-data' -OperatorName $OperatorName -StartedAt $startedAt
        Show-BackupOpsBanner -Config $Config -ActionLabel '恢复数据'

        [object[]]$restoreCandidates = Get-BackupOpsRestoreCandidates -Config $Config -LogSession $logSession -SelectedBackupId $SelectedBackupId
        $backupId = Select-BackupOpsRestorePoint -Candidates $restoreCandidates -SelectedBackupId $SelectedBackupId
        if ([string]::IsNullOrWhiteSpace($backupId)) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Summary '数据恢复未执行；当前未找到任何可用恢复点候选。' `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Code 'INTBK-1004' `
                -Message @'
原因：当前未找到任何可用恢复点候选。
建议动作：请先完成一次可恢复备份或同步备份元数据，确认存在恢复点后再重试。
'@ + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        $resultContext.backupId = $backupId
        $resultContext.restorePoint = $backupId
        $selectedCandidate = @($restoreCandidates | Where-Object { $_ -and $_.PSObject.Properties['backupId'] -and $_.backupId -eq $backupId } | Select-Object -First 1)
        $selectedRestoreCandidate = $null
        if ($selectedCandidate.Count -gt 0 -and $selectedCandidate[0].PSObject.Properties['imageTag']) {
            $selectedRestoreCandidate = $selectedCandidate[0]
            $resultContext.imageTag = [string]$selectedCandidate[0].imageTag
        }
        elseif ($selectedCandidate.Count -gt 0) {
            $selectedRestoreCandidate = $selectedCandidate[0]
        }
        if ($null -eq $selectedRestoreCandidate) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Summary ("数据恢复未执行；已选恢复点不可用: {0}。" -f $backupId) `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Code 'INTBK-1004' `
                -Message (("原因：已选恢复点 {0} 不存在、恢复文件不完整，或 recoverySet 元数据未通过候选校验。`n建议动作：请重新执行一次测试服立即备份，或在运行控制台选择一个完整的可恢复备份点后再重试。" -f $backupId) + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        Assert-RestoreDataRecoverySetCompatibility -Config $Config -Candidate $selectedRestoreCandidate -LogSession $logSession

        if (-not $NonInteractive -and -not (Read-RestoreDataConfirmation -BackupId $backupId)) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Summary ("数据恢复已取消；目标恢复点: {0}。" -f $backupId) `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'restore-data' `
                -Status 'blocked' `
                -Code 'INTBK-1004' `
                -Message ('用户取消了数据恢复。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        $startNotificationResult = Send-BackupOpsNotification `
            -Config $Config `
            -Action 'restore-data' `
            -Status 'started' `
            -Summary ("数据恢复即将开始；目标恢复点: {0}。后续将停止 backend / frontend 并覆盖数据库与对象文件。" -f $backupId) `
            -Context $resultContext `
            -LogSession $logSession
        $resultContext.startNotification = [ordered]@{
            status = [string]$startNotificationResult.status
            channel = [string]$startNotificationResult.channel
            message = [string]$startNotificationResult.message
        }

        Show-BackupOpsProgress -Current 1 -Total 8 -Message '生成 pre-restore 保护快照...'
        $snapshot = New-BackupOpsPreRestoreSnapshot -Config $Config -BackupId $backupId -LogSession $logSession
        $resultContext.preRestoreSnapshotId = $snapshot.SnapshotId

        Show-BackupOpsProgress -Current 2 -Total 8 -Message '停止 backend / frontend...'
        $null = Stop-BackupOpsFrontendBackend -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 3 -Total 8 -Message '恢复 MySQL...'
        $null = Import-BackupOpsMySqlDump -Config $Config -BackupId $backupId -LogSession $logSession

        Show-BackupOpsProgress -Current 4 -Total 8 -Message '恢复对象文件...'
        $null = Restore-BackupOpsObjectBucket -Config $Config -BackupId $backupId -LogSession $logSession

        Show-BackupOpsProgress -Current 5 -Total 8 -Message '恢复附属配置/依赖数据（如有）...'
        $null = Restore-BackupOpsDependentAssets -Config $Config -BackupId $backupId -LogSession $logSession

        Show-BackupOpsProgress -Current 6 -Total 8 -Message '启动 backend / frontend...'
        $null = Start-BackupOpsFrontendBackend -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 7 -Total 8 -Message '执行健康检查与文件抽样验证...'
        $null = Test-BackupOpsRestoreValidation -Config $Config -BackupId $backupId -LogSession $logSession

        Show-BackupOpsProgress -Current 8 -Total 8 -Message '输出恢复报告并发送通知...'
        $report = Publish-BackupOpsReport -Config $Config -Action 'restore-data' -Status 'success' -StartedAt $startedAt -CompletedAt (Get-Date) -Summary 'Restore completed and health checks passed.' -Context $resultContext -LogSession $logSession
        $logSession.LogPath = $report.LogPath
        $logSession.ReportPath = $report.ReportPath
        $notificationResult = Send-BackupOpsNotification -Config $Config -Action 'restore-data' -Status 'success' -Summary '数据恢复完成；已按恢复点恢复 MySQL、对象文件并完成健康检查。' -Context $resultContext -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
        $successMessage = '数据恢复完成。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)

        $successParams = @{
            Action = 'restore-data'
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
        return New-RestoreDataFailureResult -Config $Config -StartedAt $startedAt -LogSession $logSession -Context $resultContext -ErrorRecord $_
    }
}

Export-ModuleMember -Function 'Invoke-RestoreDataUseCase'
