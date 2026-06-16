Set-StrictMode -Version Latest

function Test-BackupOpsMeaningfulValue {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return $false
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $false
    }

    return $text.Trim().ToLowerInvariant() -ne 'unknown'
}

function Show-BackupOpsResultMessage {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    if ($Result.status -eq 'blocked' -and -not [string]::IsNullOrWhiteSpace([string]$Result.message)) {
        foreach ($line in ([string]$Result.message -split "(`r`n|`n|`r)")) {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                Write-Host $line
            }
        }
        return
    }

    Write-Host ("结果说明：{0}" -f $Result.message)
}

function Show-BackupOpsKeyResult {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Result
    )

    $context = $Result.context
    if ($null -eq $context) {
        return
    }

    switch ($Result.action) {
        'backup-now' {
            if (Test-BackupOpsMeaningfulValue -Value $context.backupId) {
                Write-Host ("备份点：{0}" -f $context.backupId)
            }
        }
        'backup-scheduled' {
            if (Test-BackupOpsMeaningfulValue -Value $context.backupId) {
                Write-Host ("备份点：{0}" -f $context.backupId)
            }
        }
        'rollback-app' {
            if (Test-BackupOpsMeaningfulValue -Value $context.imageTag) {
                Write-Host ("IMAGE_TAG：{0}" -f $context.imageTag)
            }
        }
        'restore-data' {
            if (Test-BackupOpsMeaningfulValue -Value $context.backupId) {
                Write-Host ("恢复点：{0}" -f $context.backupId)
            }
        }
    }
}

function Show-BackupOpsBanner {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,

        [string]$ActionLabel = '备份恢复控制台'
    )

    $productionHost = $Config.servers.production.host
    $testHost = $Config.servers.test.host
    $title = 'IntRuoyi Backup Console - PRODUCTION'

    if ($null -ne $Config.console -and $Config.console.title) {
        $title = $Config.console.title
    }

    $Host.UI.RawUI.WindowTitle = $title

    Write-Host '========================================'
    Write-Host (" IntRuoyi {0}" -f $ActionLabel)
    Write-Host (" 正式服务器: {0}" -f $productionHost)
    Write-Host (" 测试服务器: {0}" -f $testHost)
    Write-Host (" 操作机: {0}" -f $env:COMPUTERNAME)
    Write-Host (" 当前时间: {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    Write-Host '========================================'
    Write-Host ''
}

function Show-BackupOpsMainMenu {
    [CmdletBinding()]
    param()

    Write-Host '请选择操作:'
    Write-Host '  1. 立即备份'
    Write-Host '  2. 回滚应用版本'
    Write-Host '  3. 恢复数据'
    Write-Host '  9. 查看最近日志目录'
    Write-Host '  0. 退出'
    Write-Host ''
}

function Show-BackupOpsProgress {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [int]$Current,

        [Parameter(Mandatory = $true)]
        [int]$Total,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )

    Write-Host ("[{0}/{1}] {2}" -f $Current, $Total, $Message) -ForegroundColor $Color
}

function Show-BackupOpsOperationResult {
    [CmdletBinding()]
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

    $actionLabel = $Result.action
    switch ($Result.action) {
        'backup-now' { $actionLabel = '立即备份' }
        'backup-scheduled' { $actionLabel = '计划备份' }
        'rollback-app' { $actionLabel = '回滚应用版本' }
        'restore-data' { $actionLabel = '恢复数据' }
        'rehearsal' { $actionLabel = '恢复演练' }
    }

    Write-Host ("动作类型：{0}" -f $actionLabel)
    Write-Host ("结果代码：{0}" -f $Result.code)
    Show-BackupOpsResultMessage -Result $Result
    Show-BackupOpsKeyResult -Result $Result

    if ($Result.logPath) {
        Write-Host ("日志路径：{0}" -f $Result.logPath)
    }

    if ($Result.reportPath) {
        Write-Host ("报告路径：{0}" -f $Result.reportPath)
    }
}

Export-ModuleMember -Function @(
    'Show-BackupOpsBanner',
    'Show-BackupOpsMainMenu',
    'Show-BackupOpsProgress',
    'Show-BackupOpsOperationResult'
)
