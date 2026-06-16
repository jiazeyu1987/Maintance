Set-StrictMode -Version Latest

function New-BackupScheduledFailureResult {
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
            -Action 'backup-scheduled' `
            -Status $status `
            -Summary ("计划备份失败。{0}" -f $message) `
            -Context $Context `
            -LogSession $LogSession
        Set-BackupOpsNotificationContext -Context $Context -NotificationResult $notificationResult
        $message = $message + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)
    }

    return Complete-BackupOpsOutcome `
        -Config $Config `
        -Action 'backup-scheduled' `
        -Status $status `
        -Code $code `
        -Message $message `
        -StartedAt $StartedAt `
        -CompletedAt (Get-Date) `
        -Context $Context `
        -LogSession $LogSession
}

function Invoke-BackupScheduledUseCase {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$OperatorName = 'scheduler'
    )

    $startedAt = Get-Date
    $logSession = $null
    $resultContext = @{
        backupId = $null
        imageTag = $null
        cleanup = [ordered]@{
            localRetention = [ordered]@{
                status = 'pending'
            }
            remoteRetention = [ordered]@{
                status = 'pending'
            }
        }
    }
    $successMessage = '计划备份完成。'

    try {
        $logSession = Start-BackupOpsLogSession -Config $Config -Action 'backup-scheduled' -OperatorName $OperatorName -StartedAt $startedAt

        Show-BackupOpsProgress -Current 1 -Total 11 -Message '校验 NAS 挂载...'
        $null = Assert-BackupOpsRemoteNasMounted -Config $Config -LogSession $logSession

        Show-BackupOpsProgress -Current 2 -Total 11 -Message '创建备份工作目录...'
        $workspace = New-BackupOpsBackupWorkspace -Config $Config -Action 'backup-scheduled' -BackupType 'scheduled'
        $workspace.ImageTag = Get-BackupOpsCurrentImageTag -Config $Config -LogSession $logSession
        $resultContext.backupId = $workspace.BackupId
        $resultContext.imageTag = $workspace.ImageTag

        Show-BackupOpsProgress -Current 3 -Total 11 -Message '读取当前部署元数据...'
        $null = Save-BackupOpsDeployMetadata -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 4 -Total 11 -Message '导出 MySQL...'
        $null = Export-BackupOpsMySqlDump -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 5 -Total 11 -Message '备份 MinIO 对象...'
        $null = Backup-BackupOpsObjectBucket -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 6 -Total 11 -Message '生成 checksums 与 manifest...'
        $null = New-BackupOpsDccBackupManifest -Config $Config -Workspace $workspace -LogSession $logSession
        $null = Assert-BackupOpsDccBackupManifestReady -Config $Config -Workspace $workspace -LogSession $logSession
        $null = New-BackupOpsChecksums -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 7 -Total 11 -Message '同步到测试服务器...'
        $null = Sync-BackupOpsBackupToTestServer -Config $Config -Workspace $workspace -LogSession $logSession

        $null = New-BackupOpsManifest -Config $Config -Workspace $workspace -BackupType 'scheduled' -Status 'success' -Validation @{
            mysqlDumpCreated = $true
            objectBackupCreated = $true
            checksumsGenerated = $true
            syncedToTestServer = $true
        } -OperatorName $OperatorName -LogSession $logSession
        $null = Sync-BackupOpsManifestToTestServer -Config $Config -Workspace $workspace -LogSession $logSession

        Show-BackupOpsProgress -Current 8 -Total 11 -Message '清理正式机临时副本...'
        try {
            $localRetentionResult = Invoke-BackupOpsLocalRetention -Config $Config -LogSession $logSession
            $resultContext.cleanup.localRetention = [ordered]@{
                status = 'success'
                detail = if ($null -ne $localRetentionResult) { [string]$localRetentionResult } else { '清理完成。' }
            }
        }
        catch {
            $resultContext.cleanup.localRetention = [ordered]@{
                status = 'fail'
                detail = $_.Exception.Message
            }
            $cleanupFailureNotification = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'backup-scheduled' `
                -Status 'fail' `
                -Summary ("清理任务失败；正式机临时副本={0}，测试机过期备份={1}。" -f $resultContext.cleanup.localRetention.status, $resultContext.cleanup.remoteRetention.status) `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $cleanupFailureNotification -Prefix 'cleanup'
            throw
        }

        Show-BackupOpsProgress -Current 9 -Total 11 -Message '清理测试机过期备份...'
        try {
            $remoteRetentionResult = Invoke-BackupOpsRemoteRetention -Config $Config -LogSession $logSession
            $resultContext.cleanup.remoteRetention = [ordered]@{
                status = 'success'
                detail = if ($null -ne $remoteRetentionResult) { [string]$remoteRetentionResult } else { '清理完成。' }
            }
        }
        catch {
            $resultContext.cleanup.remoteRetention = [ordered]@{
                status = 'fail'
                detail = $_.Exception.Message
            }
            $cleanupFailureNotification = Invoke-BackupOpsNotificationCapture `
                -Config $Config `
                -Action 'backup-scheduled' `
                -Status 'fail' `
                -Summary ("清理任务失败；正式机临时副本={0}，测试机过期备份={1}。" -f $resultContext.cleanup.localRetention.status, $resultContext.cleanup.remoteRetention.status) `
                -Context $resultContext `
                -LogSession $logSession
            Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $cleanupFailureNotification -Prefix 'cleanup'
            throw
        }

        $cleanupNotification = Invoke-BackupOpsNotificationCapture `
            -Config $Config `
            -Action 'backup-scheduled' `
            -Status 'success' `
            -Summary ("清理任务完成；正式机临时副本={0}，测试机过期备份={1}。" -f $resultContext.cleanup.localRetention.status, $resultContext.cleanup.remoteRetention.status) `
            -Context $resultContext `
            -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $cleanupNotification -Prefix 'cleanup'

        Show-BackupOpsProgress -Current 10 -Total 11 -Message '生成报告...'
        $report = Publish-BackupOpsReport -Config $Config -Action 'backup-scheduled' -Status 'success' -StartedAt $startedAt -CompletedAt (Get-Date) -Summary '计划备份已完成并同步到测试服务器。' -Context $resultContext -LogSession $logSession
        $logSession.LogPath = $report.LogPath
        $logSession.ReportPath = $report.ReportPath

        Show-BackupOpsProgress -Current 11 -Total 11 -Message '发送通知...'
        $notificationResult = Send-BackupOpsNotification -Config $Config -Action 'backup-scheduled' -Status 'success' -Summary ("计划备份完成；已导出正式库 MySQL、备份 MinIO yudao 桶对象并同步到测试服务器备份仓库。清理状态：正式机临时副本={0}，测试机过期备份={1}。" -f $resultContext.cleanup.localRetention.status, $resultContext.cleanup.remoteRetention.status) -Context $resultContext -LogSession $logSession
        Set-BackupOpsNotificationContext -Context $resultContext -NotificationResult $notificationResult
        $successMessage = '计划备份完成。' + (Get-BackupOpsNotificationOutcomeMessage -NotificationResult $notificationResult)

        $successParams = @{
            Action = 'backup-scheduled'
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
        return New-BackupScheduledFailureResult -Config $Config -StartedAt $startedAt -LogSession $logSession -Context $resultContext -ErrorRecord $_
    }
}

Export-ModuleMember -Function 'Invoke-BackupScheduledUseCase'
