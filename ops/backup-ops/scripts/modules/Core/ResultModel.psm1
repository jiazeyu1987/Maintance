Set-StrictMode -Version Latest

$script:BackupOpsSuccessCode = 'INTBK-0000'
$script:BackupOpsKnownActions = @(
    'backup-now',
    'backup-scheduled',
    'rollback-app',
    'restore-data',
    'rehearsal'
)
$script:BackupOpsKnownStatuses = @(
    'success',
    'fail',
    'blocked'
)

function Test-BackupOpsKnownAction {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Action
    )

    return $script:BackupOpsKnownActions -contains $Action
}

function New-BackupOpsResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Action,

        [ValidateSet('success', 'fail', 'blocked')]
        [string]$Status = 'success',

        [string]$Code = $script:BackupOpsSuccessCode,

        [string]$Message = 'Operation completed successfully.',

        [object]$StartedAt = $null,

        [object]$CompletedAt = $null,

        [string]$LogPath = '',

        [string]$ReportPath = '',

        [hashtable]$Context = @{}
    )

    if (-not (Test-BackupOpsKnownAction -Action $Action)) {
        throw "Unsupported backup action: $Action"
    }

    if ($null -eq $StartedAt) {
        $StartedAt = [System.DateTimeOffset]::Now
    }

    if ($null -eq $CompletedAt -and $Status -eq 'success') {
        $CompletedAt = $StartedAt
    }

    return [PSCustomObject][ordered]@{
        action      = $Action
        status      = $Status
        code        = $Code
        message     = $Message
        startedAt   = $StartedAt
        completedAt = $CompletedAt
        logPath     = $LogPath
        reportPath  = $ReportPath
        context     = $Context
    }
}

function Set-BackupOpsResultOutcome {
    param(
        [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
        [object]$Result,

        [Parameter(Mandatory = $true)]
        [ValidateSet('success', 'fail', 'blocked')]
        [string]$Status,

        [Parameter(Mandatory = $true)]
        [string]$Code,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [object]$CompletedAt = $null,

        [string]$LogPath = '',

        [string]$ReportPath = '',

        [hashtable]$Context = $null
    )

    process {
        if ($null -eq $CompletedAt) {
            $CompletedAt = [System.DateTimeOffset]::Now
        }

        if (-not $LogPath) {
            $LogPath = [string]$Result.logPath
        }

        if (-not $ReportPath) {
            $ReportPath = [string]$Result.reportPath
        }

        $mergedContext = @{}
        if ($Result.context -is [System.Collections.IDictionary]) {
            foreach ($key in $Result.context.Keys) {
                $mergedContext[$key] = $Result.context[$key]
            }
        }
        if ($Context) {
            foreach ($key in $Context.Keys) {
                $mergedContext[$key] = $Context[$key]
            }
        }

        return [PSCustomObject][ordered]@{
            action      = [string]$Result.action
            status      = $Status
            code        = $Code
            message     = $Message
            startedAt   = $Result.startedAt
            completedAt = $CompletedAt
            logPath     = $LogPath
            reportPath  = $ReportPath
            context     = $mergedContext
        }
    }
}

function Get-BackupOpsExitCode {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Result
    )

    switch ([string]$Result.status) {
        'success' { return 0 }
        'fail' { return 1 }
        'blocked' { return 2 }
        default { throw "Unsupported backup result status: $($Result.status)" }
    }
}

Export-ModuleMember -Function @(
    'Get-BackupOpsExitCode',
    'New-BackupOpsResult',
    'Set-BackupOpsResultOutcome',
    'Test-BackupOpsKnownAction'
)
