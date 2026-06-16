Set-StrictMode -Version Latest

function New-BackupNowFailureResult {
    param(
        [object]$Config,
        [datetime]$StartedAt,
        [object]$LogSession,
        [hashtable]$Context,
        [System.Management.Automation.ErrorRecord]$ErrorRecord
    )

    $status = 'fail'
    $code = 'INTBK-6003'
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
            -Action 'backup-now' `
            -Status $status `
            -Summary ("立即备份失败。{0}" -f $message) `
            -Context $Context `
            -LogSession $LogSession
        Set-BackupOpsNotificationContext -Context $Context -NotificationResult $notificationResult
        $message = $message + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)
    }

    return Complete-BackupOpsOutcome `
        -Config $Config `
        -Action 'backup-now' `
        -Status $status `
        -Code $code `
        -Message $message `
        -StartedAt $StartedAt `
        -CompletedAt (Get-Date) `
        -Context $Context `
        -LogSession $LogSession
}

function Invoke-BackupNowUseCase {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$OperatorName = $env:USERNAME,

        [switch]$NonInteractive
    )

    $startedAt = Get-Date
    $logSession = $null
    $resultContext = @{
        backupId = $null
        imageTag = $null
    }
    $successMessage = '立即备份完成。'

    try {
        $logSession = Start-BackupOpsLogSession -Config $Config -Action 'backup-now' -OperatorName $OperatorName -StartedAt $startedAt
        Show-BackupOpsBanner -Config $Config -ActionLabel '立即备份'

        if (-not $NonInteractive -and -not (Read-BackupNowConfirmation)) {
            $notificationResult = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'backup-now' `
                -Status 'blocked' `
                -Summary '立即备份已取消；操作员未确认执行。' `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
            return Complete-BackupOpsOutcome `
                -Config $Config `
                -Action 'backup-now' `
                -Status 'blocked' `
                -Code 'INTBK-1004' `
                -Message ('用户取消了立即备份。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)) `
                -StartedAt $startedAt `
                -CompletedAt (Get-Date) `
                -Context $resultContext `
                -LogSession $logSession
        }

        Show-BackupOpsProgress -Current 1 -Total 7 -Message '校验 NAS 挂载...'
        $null = Assert-BackupOpsRemoteNasMounted -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 2 -Total 7 -Message '创建备份工作目录...'
        $workspace = New-BackupOpsBackupWorkspace -Config $Config -Action 'backup-now' -BackupType 'manual'
        $workspace.ImageTag = Get-BackupOpsCurrentImageTag -Config $Config -LogSession $logSession
        $resultContext.backupId = $workspace.BackupId
        $resultContext.imageTag = $workspace.ImageTag

        Show-BackupOpsProgress -Current 3 -Total 7 -Message '导出 MySQL...'
        $null = Export-BackupOpsMySqlDump -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 4 -Total 7 -Message '备份 MinIO 对象...'
        $null = Backup-BackupOpsObjectBucket -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 5 -Total 7 -Message '生成 checksums 与 manifest...'
        $null = Save-BackupOpsDeployMetadata -Config $Config -Workspace $workspace -LogSession $logSession
        $null = New-BackupOpsDccBackupManifest -Config $Config -Workspace $workspace -LogSession $logSession
        $null = Assert-BackupOpsDccBackupManifestReady -Config $Config -Workspace $workspace -LogSession $logSession
        $null = New-BackupOpsChecksums -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 6 -Total 7 -Message '同步到测试服务器...'
        $null = Sync-BackupOpsBackupToTestServer -Config $Config -Workspace $workspace -LogSession $logSession

        $null = New-BackupOpsManifest -Config $Config -Workspace $workspace -BackupType 'manual' -Status 'success' -Validation @{
            mysqlDumpCreated = $true
            objectBackupCreated = $true
            checksumsGenerated = $true
            syncedToTestServer = $true
        } -OperatorName $OperatorName -LogSession $logSession
        $null = Sync-BackupOpsManifestToTestServer -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 7 -Total 7 -Message '写入结果并发送通知...'

        $report = Publish-BackupOpsReport -Config $Config -Action 'backup-now' -Status 'success' -StartedAt $startedAt -CompletedAt (Get-Date) -Summary '备份已完成并同步到测试服务器。' -Context $resultContext -LogSession $logSession
        $logSession.LogPath = $report.LogPath
        $logSession.ReportPath = $report.ReportPath
        $notificationResult = Send-BackupOpsNotification -Config $Config -Action 'backup-now' -Status 'success' -Summary '立即备份完成；已导出正式库 MySQL、备份 MinIO yudao 桶对象并同步到测试服务器备份仓库。' -Context $resultContext -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
        $successMessage = '立即备份完成。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)

        $successParams = @{
            Action = 'backup-now'
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
        return New-BackupNowFailureResult -Config $Config -StartedAt $startedAt -LogSession $logSession -Context $resultContext -ErrorRecord $_
    }
}

Export-ModuleMember -Function 'Invoke-BackupNowUseCase'
