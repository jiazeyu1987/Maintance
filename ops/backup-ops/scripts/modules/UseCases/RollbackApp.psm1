Set-StrictMode -Version Latest

function New-RollbackAppBlockedException {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Code,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsCode'] = $Code
    $exception.Data['BackupOpsStatus'] = 'blocked'
    return $exception
}

function New-RollbackAppFailureResult {
    param(
        [object]$Config,
        [datetime]$StartedAt,
        [object]$LogSession,
        [hashtable]$Context,
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $status = 'fail'
    $code = 'INTBK-5003'
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
            -Action 'rollback-app' `
            -Status $status `
            -Summary ("应用回滚失败。{0}" -f $message) `
            -Context $Context `
            -LogSession $LogSession
        Set-BackupOpsNotificationContext -Context $Context -NotificationResult $notificationResult
        $message = $message + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)
    }

    return Complete-BackupOpsOutcome `
        -Config $Config `
        -Action 'rollback-app' `
        -Status $status `
        -Code $code `
        -Message $message `
        -StartedAt $StartedAt `
        -CompletedAt (Get-Date) `
        -Context $Context `
        -LogSession $LogSession
}

function Invoke-RollbackAppUseCase {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$SelectedImageTag,

        [string]$OperatorName = $env:USERNAME,

        [switch]$NonInteractive
    )

    $startedAt = Get-Date
    $logSession = $null
    $resultContext = @{
        backupId = $null
        imageTag = $null
    }
    $successMessage = '应用回滚完成。'

    try {
        $logSession = Start-BackupOpsLogSession -Config $Config -Action 'rollback-app' -OperatorName $OperatorName -StartedAt $startedAt
        Show-BackupOpsBanner -Config $Config -ActionLabel '回滚应用版本'

        Show-BackupOpsProgress -Current 1 -Total 5 -Message '读取可回滚 IMAGE_TAG...'
        [object[]]$candidateTags = Get-BackupOpsRollbackTags -Config $Config -LogSession $logSession
        $imageTag = Select-BackupOpsImageTag -Candidates $candidateTags -SelectedImageTag $SelectedImageTag
        if ([string]::IsNullOrWhiteSpace($imageTag)) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'rollback-app' `
                -Status 'blocked' `
                -Summary '应用回滚未执行；当前未找到任何可回滚的 IMAGE_TAG 候选。' `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'rollback-app' `
                -Status 'blocked' `
                -Code 'INTBK-5001' `
                -Message @'
原因：当前未找到任何可回滚的 IMAGE_TAG 候选。
建议动作：请先完成一次备份或同步备份元数据，确认存在可回滚 IMAGE_TAG 后再重试。
'@ + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        $resultContext.imageTag = $imageTag
        if ($candidateTags -notcontains $imageTag) {
            throw (New-RollbackAppBlockedException -Code 'INTBK-5001' -Message "原因：回滚目标缺少兼容性证据或未通过 rollback-compatibility.json 校验：$imageTag`n建议动作：请先生成并确认 rollback-compatibility.json status=COMPATIBLE 后再执行应用回滚。")
        }

        if (-not $NonInteractive -and -not (Read-RollbackAppConfirmation -ImageTag $imageTag)) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'rollback-app' `
                -Status 'blocked' `
                -Summary ("应用回滚已取消；目标 IMAGE_TAG: {0}。" -f $imageTag) `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'rollback-app' `
                -Status 'blocked' `
                -Code 'INTBK-1004' `
                -Message ('用户取消了应用回滚。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        Show-BackupOpsProgress -Current 2 -Total 5 -Message '备份当前 .env...'
        $null = Save-BackupOpsRuntimeEnvBackup -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 3 -Total 5 -Message '更新 IMAGE_TAG...'
        $null = Set-BackupOpsImageTag -Config $Config -ImageTag $imageTag -LogSession $logSession

        Show-BackupOpsProgress -Current 4 -Total 5 -Message '重启 backend / frontend...'
        $null = Restart-BackupOpsFrontendBackend -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 5 -Total 5 -Message '运行健康检查...'
        $null = Test-BackupOpsFrontendBackendHealth -Config $Config -LogSession $logSession
        $report = Publish-BackupOpsReport -Config $Config -Action 'rollback-app' -Status 'success' -StartedAt $startedAt -CompletedAt (Get-Date) -Summary 'Application rollback completed successfully.' -Context $resultContext -LogSession $logSession
        $logSession.LogPath = $report.LogPath
        $logSession.ReportPath = $report.ReportPath
        $notificationResult = Send-BackupOpsNotification -Config $Config -Action 'rollback-app' -Status 'success' -Summary '应用回滚完成；已更新正式环境 IMAGE_TAG、重启 backend / frontend 并完成健康检查。' -Context $resultContext -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
        $successMessage = '应用回滚完成。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)

        $successParams = @{
            Action = 'rollback-app'
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
        return New-RollbackAppFailureResult -Config $Config -StartedAt $startedAt -LogSession $logSession -Context $resultContext -ErrorRecord $_
    }
}

Export-ModuleMember -Function 'Invoke-RollbackAppUseCase'
