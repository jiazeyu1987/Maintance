Set-StrictMode -Version Latest

function Import-BackupOpsLoggingDependency {
    if (Get-Command -Name 'Write-BackupOpsLog' -ErrorAction SilentlyContinue) {
        return
    }

    $loggingModulePath = Join-Path $PSScriptRoot '..\Core\Logging.psm1'
    if (-not (Test-Path -LiteralPath $loggingModulePath)) {
        throw "Logging module not found: $loggingModulePath"
    }

    Import-Module $loggingModulePath -Force -DisableNameChecking -ErrorAction Stop | Out-Null
}

function New-BackupOpsNotifyException {
    param(
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Message,
        [ValidateSet('blocked', 'fail')]
        [string]$Status = 'blocked'
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsCode'] = $Code
    $exception.Data['BackupOpsStatus'] = $Status
    return $exception
}

function Get-BackupNotifyFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Request.ContainsKey($Name)) {
        throw [System.ArgumentException]::new("INTBK-6003: missing notify request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw [System.ArgumentException]::new("INTBK-6003: notify request field '$Name' cannot be empty.")
    }

    return [string]$value
}

function Get-BackupNotifyConfigValueSafe {
    param(
        [Parameter(Mandatory)]
        [object]$InputObject,
        [Parameter(Mandatory)]
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

function Write-BackupOpsNotificationLog {
    param(
        [AllowNull()]
        [object]$LogSession,
        [Parameter(Mandatory)]
        [string]$Message,
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO'
    )

    Import-BackupOpsLoggingDependency
    if ($null -eq $LogSession) {
        return
    }

    Write-BackupOpsLog -Session $LogSession -Message $Message -Level $Level
}

function Get-BackupOpsNotificationTitle {
    param(
        [Parameter(Mandatory)]
        [string]$Action
    )

    switch ($Action) {
        'backup-now' { return '[IntRuoyi][立即备份结果]' }
        'backup-scheduled' { return '[IntRuoyi][计划备份结果]' }
        'restore-data' { return '[IntRuoyi][恢复结果]' }
        'rehearsal' { return '[IntRuoyi][演练结果]' }
        'rollback-app' { return '[IntRuoyi][回滚结果]' }
        default { return '[IntRuoyi][备份恢复通知]' }
    }
}

function New-BackupNotificationSummary {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupNotifyFieldValue -Request $Request -Name 'Action')
    [void](Get-BackupNotifyFieldValue -Request $Request -Name 'Status')

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add((Get-BackupOpsNotificationTitle -Action $Request['Action']))

    if ($Request.ContainsKey('BackupId') -and -not [string]::IsNullOrWhiteSpace([string]$Request['BackupId'])) {
        $lines.Add("备份点: $($Request['BackupId'])")
    }

    if ($Request.ContainsKey('RestorePoint') -and -not [string]::IsNullOrWhiteSpace([string]$Request['RestorePoint'])) {
        $lines.Add("恢复点: $($Request['RestorePoint'])")
    }

    if ($Request.ContainsKey('ImageTag') -and -not [string]::IsNullOrWhiteSpace([string]$Request['ImageTag'])) {
        $lines.Add("IMAGE_TAG: $($Request['ImageTag'])")
    }

    if ($Request.ContainsKey('PreRestoreSnapshotId') -and -not [string]::IsNullOrWhiteSpace([string]$Request['PreRestoreSnapshotId'])) {
        $lines.Add("pre-restore 快照: $($Request['PreRestoreSnapshotId'])")
    }

    $lines.Add("结果: $($Request['Status'])")

    if ($Request.ContainsKey('Summary') -and -not [string]::IsNullOrWhiteSpace([string]$Request['Summary'])) {
        $lines.Add([string]$Request['Summary'])
    }

    if ($Request.ContainsKey('LogPath') -and -not [string]::IsNullOrWhiteSpace([string]$Request['LogPath'])) {
        $lines.Add("日志: $($Request['LogPath'])")
    }

    if ($Request.ContainsKey('ReportPath') -and -not [string]::IsNullOrWhiteSpace([string]$Request['ReportPath'])) {
        $lines.Add("报告: $($Request['ReportPath'])")
    }

    return ($lines -join [Environment]::NewLine)
}

function New-BackupNotificationPayload {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Summary
    )

    $payload = [ordered]@{
        title   = Get-BackupOpsNotificationTitle -Action $Request['Action']
        action  = $Request['Action']
        status  = $Request['Status']
        summary = $Summary
    }

    foreach ($key in @('BackupId', 'RestorePoint', 'ImageTag', 'PreRestoreSnapshotId', 'LogPath', 'ReportPath')) {
        if ($Request.ContainsKey($key) -and -not [string]::IsNullOrWhiteSpace([string]$Request[$key])) {
            $payload[$key.Substring(0, 1).ToLowerInvariant() + $key.Substring(1)] = $Request[$key]
        }
    }

    return [pscustomobject]$payload
}

function New-BackupNotificationResult {
    param(
        [Parameter(Mandatory)]
        [string]$Status,
        [Parameter(Mandatory)]
        [string]$Channel,
        [Parameter(Mandatory)]
        [string]$Message,
        [Parameter(Mandatory)]
        [string]$Summary,
        [int]$StatusCode = 0,
        [string]$Target = ''
    )

    return [pscustomobject]([ordered]@{
            operation  = 'notify'
            status     = $Status
            code       = 'INTBK-0000'
            channel    = $Channel
            message    = $Message
            summary    = $Summary
            statusCode = if ($StatusCode -gt 0) { $StatusCode } else { $null }
            target     = if ([string]::IsNullOrWhiteSpace($Target)) { $null } else { $Target }
        })
}

function Send-BackupNotification {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupNotifyFieldValue -Request $Request -Name 'Action')
    [void](Get-BackupNotifyFieldValue -Request $Request -Name 'Status')

    $summary = New-BackupNotificationSummary -Request $Request
    $channel = if ($Request.ContainsKey('Channel')) { [string]$Request['Channel'] } else { 'pending' }
    $enabled = if ($Request.ContainsKey('Enabled')) { [bool]$Request['Enabled'] } else { $false }
    $logSession = if ($Request.ContainsKey('LogSession')) { $Request['LogSession'] } else { $null }

    if (-not $enabled) {
        $result = New-BackupNotificationResult -Status 'disabled' -Channel $channel -Message '通知未发送：当前配置为 disabled。' -Summary $summary
        Write-BackupOpsNotificationLog -LogSession $logSession -Level 'WARN' -Message "通知未发送：status=disabled；channel=$channel。"
        return $result
    }

    if ($channel -eq 'pending') {
        $result = New-BackupNotificationResult -Status 'pending' -Channel $channel -Message '通知未发送：当前通知通道仍为 pending。' -Summary $summary
        Write-BackupOpsNotificationLog -LogSession $logSession -Level 'WARN' -Message '通知未发送：status=pending；channel=pending。'
        return $result
    }

    if ($channel -ne 'webhook') {
        $result = New-BackupNotificationResult -Status 'unsupported' -Channel $channel -Message "通知未发送：不支持的通知通道 $channel。" -Summary $summary
        Write-BackupOpsNotificationLog -LogSession $logSession -Level 'ERROR' -Message "通知未发送：status=unsupported；channel=$channel。"
        return $result
    }

    if (-not $Request.ContainsKey('WebhookUrl') -or [string]::IsNullOrWhiteSpace([string]$Request['WebhookUrl'])) {
        throw (New-BackupOpsNotifyException -Code 'INTBK-6003' -Status 'blocked' -Message '通知通道已启用 webhook，但缺少 notify.webhook.url 配置。')
    }

    $webhookUrl = [string]$Request['WebhookUrl']
    $timeoutSeconds = if ($Request.ContainsKey('TimeoutSeconds') -and [int]$Request['TimeoutSeconds'] -gt 0) { [int]$Request['TimeoutSeconds'] } else { 10 }
    $payload = New-BackupNotificationPayload -Request $Request -Summary $summary
    $payloadJson = $payload | ConvertTo-Json -Depth 8 -Compress

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $webhookUrl -ContentType 'application/json; charset=utf-8' -Body $payloadJson -TimeoutSec $timeoutSeconds
        $result = New-BackupNotificationResult -Status 'sent' -Channel 'webhook' -Message 'Webhook 通知已发送。' -Summary $summary -StatusCode ([int]$response.StatusCode) -Target $webhookUrl
        Write-BackupOpsNotificationLog -LogSession $logSession -Message "通知已发送：status=sent；channel=webhook；statusCode=$($response.StatusCode)；target=$webhookUrl。"
        return $result
    }
    catch {
        $result = New-BackupNotificationResult -Status 'failed' -Channel 'webhook' -Message "通知发送失败：$($_.Exception.Message)" -Summary $summary -Target $webhookUrl
        Write-BackupOpsNotificationLog -LogSession $logSession -Level 'ERROR' -Message "通知发送失败：status=failed；channel=webhook；target=$webhookUrl；error=$($_.Exception.Message)"
        return $result
    }
}

function Set-BackupOpsNotificationContext {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Context,
        [Parameter(Mandatory = $true)]
        [object]$NotificationResult,
        [string]$Prefix = ''
    )

    $prefixKey = if ([string]::IsNullOrWhiteSpace($Prefix)) { 'notification' } else { "$Prefix" + 'Notification' }
    $statusKey = if ([string]::IsNullOrWhiteSpace($Prefix)) { 'notificationStatus' } else { "$Prefix" + 'NotificationStatus' }
    $channelKey = if ([string]::IsNullOrWhiteSpace($Prefix)) { 'notificationChannel' } else { "$Prefix" + 'NotificationChannel' }
    $messageKey = if ([string]::IsNullOrWhiteSpace($Prefix)) { 'notificationMessage' } else { "$Prefix" + 'NotificationMessage' }

    $Context[$prefixKey] = [ordered]@{
        status  = [string]$NotificationResult.status
        channel = [string]$NotificationResult.channel
        message = [string]$NotificationResult.message
        summary = [string]$NotificationResult.summary
    }
    $Context[$statusKey] = [string]$NotificationResult.status
    $Context[$channelKey] = [string]$NotificationResult.channel
    $Context[$messageKey] = [string]$NotificationResult.message
}

function Invoke-BackupOpsNotificationCapture {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Summary,
        [Parameter(Mandatory = $true)]
        [hashtable]$Context,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $channel = [string](Get-BackupNotifyConfigValueSafe -InputObject $Config -Path @('notify', 'channel'))
    if ([string]::IsNullOrWhiteSpace($channel)) {
        $channel = 'pending'
    }

    try {
        return Send-BackupOpsNotification -Config $Config -Action $Action -Status $Status -Summary $Summary -Context $Context -LogSession $LogSession
    }
    catch {
        $result = New-BackupNotificationResult -Status 'failed' -Channel $channel -Message "通知链路执行失败：$($_.Exception.Message)" -Summary $Summary
        Write-BackupOpsNotificationLog -LogSession $LogSession -Level 'ERROR' -Message "通知链路执行失败：action=$Action；status=$Status；channel=$channel；error=$($_.Exception.Message)"
        return $result
    }
}

function Get-BackupOpsNotificationOutcomeMessage {
    param(
        [Parameter(Mandatory = $true)]
        [object]$NotificationResult
    )

    switch ([string]$NotificationResult.status) {
        'sent' { return '通知已发送。' }
        'disabled' { return '通知未发送（disabled）。' }
        'pending' { return '通知未发送（pending）。' }
        'unsupported' { return '通知未发送（unsupported）。' }
        'failed' { return '通知发送失败。' }
        default { return "通知状态未知（$($NotificationResult.status)）。" }
    }
}

function Send-BackupOpsNotification {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Summary,
        [Parameter(Mandatory = $true)]
        [hashtable]$Context,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $channel = [string](Get-BackupNotifyConfigValueSafe -InputObject $Config -Path @('notify', 'channel'))
    if ([string]::IsNullOrWhiteSpace($channel)) {
        $channel = 'pending'
    }

    $enabled = [bool](Get-BackupNotifyConfigValueSafe -InputObject $Config -Path @('notify', 'enabled'))
    $request = @{
        Action = $Action
        Status = $Status
        Summary = $Summary
        Channel = $channel
        Enabled = $enabled
        LogPath = [string]$LogSession.LogPath
        ReportPath = if ($LogSession.PSObject.Properties['ReportPath']) { [string]$LogSession.ReportPath } else { '' }
        LogSession = $LogSession
    }

    if ($Context.ContainsKey('backupId') -and -not [string]::IsNullOrWhiteSpace([string]$Context['backupId'])) {
        $request['BackupId'] = [string]$Context['backupId']
        if ($Action -eq 'restore-data' -and (-not $Context.ContainsKey('restorePoint') -or [string]::IsNullOrWhiteSpace([string]$Context['restorePoint']))) {
            $request['RestorePoint'] = [string]$Context['backupId']
        }
    }
    if ($Context.ContainsKey('restorePoint') -and -not [string]::IsNullOrWhiteSpace([string]$Context['restorePoint'])) {
        $request['RestorePoint'] = [string]$Context['restorePoint']
    }
    if ($Context.ContainsKey('imageTag') -and -not [string]::IsNullOrWhiteSpace([string]$Context['imageTag'])) {
        $request['ImageTag'] = [string]$Context['imageTag']
    }
    if ($Context.ContainsKey('preRestoreSnapshotId') -and -not [string]::IsNullOrWhiteSpace([string]$Context['preRestoreSnapshotId'])) {
        $request['PreRestoreSnapshotId'] = [string]$Context['preRestoreSnapshotId']
    }

    if ($enabled -and $channel -eq 'webhook') {
        $webhookUrl = Get-BackupNotifyConfigValueSafe -InputObject $Config -Path @('notify', 'webhook', 'url')
        if ($null -eq $webhookUrl -or [string]::IsNullOrWhiteSpace([string]$webhookUrl)) {
            throw (New-BackupOpsNotifyException -Code 'INTBK-6003' -Status 'blocked' -Message '通知通道已启用 webhook，但缺少 notify.webhook.url 配置。')
        }

        $request['WebhookUrl'] = [string]$webhookUrl
        $timeoutSeconds = Get-BackupNotifyConfigValueSafe -InputObject $Config -Path @('notify', 'webhook', 'timeoutSeconds')
        if ($null -ne $timeoutSeconds -and [int]$timeoutSeconds -gt 0) {
            $request['TimeoutSeconds'] = [int]$timeoutSeconds
        }
    }

    return Send-BackupNotification -Request $request
}

Export-ModuleMember -Function New-BackupNotificationSummary, Send-BackupNotification, Set-BackupOpsNotificationContext, Invoke-BackupOpsNotificationCapture, Get-BackupOpsNotificationOutcomeMessage, Send-BackupOpsNotification
