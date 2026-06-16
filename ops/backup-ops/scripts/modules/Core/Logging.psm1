Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function New-BackupOpsLogTimestamp {
    param(
        [object]$Timestamp = $null
    )

    if ($null -eq $Timestamp) {
        $Timestamp = [System.DateTimeOffset]::Now
    }

    return ([System.DateTimeOffset]$Timestamp).ToString('yyyyMMdd_HHmmss')
}

function New-BackupOpsSequenceId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [string]$LogRoot,
        [object]$Timestamp = $null
    )

    $baseTimestamp = New-BackupOpsLogTimestamp -Timestamp $Timestamp
    $directory = Resolve-BackupOpsLogDirectory -LogRoot $LogRoot -Timestamp $Timestamp
    $sequenceId = $baseTimestamp
    $suffix = 1

    while (
        (Test-Path -LiteralPath (Join-Path $directory "${sequenceId}_${Action}_running.log")) -or
        (Test-Path -LiteralPath (Join-Path $directory "${sequenceId}_${Action}_success.log")) -or
        (Test-Path -LiteralPath (Join-Path $directory "${sequenceId}_${Action}_fail.log")) -or
        (Test-Path -LiteralPath (Join-Path $directory "${sequenceId}_${Action}_blocked.log"))
    ) {
        $sequenceId = "{0}-{1}" -f $baseTimestamp, $suffix
        $suffix++
    }

    return $sequenceId
}

function Resolve-BackupOpsLogDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogRoot,

        [object]$Timestamp = $null
    )

    if ([string]::IsNullOrWhiteSpace($LogRoot)) {
        throw 'Log root is required.'
    }

    if ($null -eq $Timestamp) {
        $Timestamp = [System.DateTimeOffset]::Now
    }

    $monthFolder = ([System.DateTimeOffset]$Timestamp).ToString('yyyyMM')
    $monthPath = Join-Path $LogRoot $monthFolder
    New-Item -ItemType Directory -Force -Path $monthPath | Out-Null
    return $monthPath
}

function New-BackupOpsLogSession {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Action,

        [Parameter(Mandatory = $true)]
        [string]$LogRoot,

        [string]$OperatorName = 'unknown',

        [string]$Mode = '',

        [hashtable]$Context = @{},

        [object]$StartedAt = $null
    )

    if ($null -eq $StartedAt) {
        $StartedAt = [System.DateTimeOffset]::Now
    }

    $directory = Resolve-BackupOpsLogDirectory -LogRoot $LogRoot -Timestamp $StartedAt
    $timestampId = New-BackupOpsSequenceId -Action $Action -LogRoot $LogRoot -Timestamp $StartedAt
    $logPath = Join-Path $directory "${timestampId}_${Action}_running.log"
    $reportBasePath = Join-Path $directory "${timestampId}_${Action}"

    $headerLines = @(
        "operator=$OperatorName",
        "host=$env:COMPUTERNAME",
        "mode=$Mode",
        "action=$Action",
        "startedAt=$([System.DateTimeOffset]$StartedAt)"
    )
    foreach ($key in $Context.Keys) {
        $headerLines += "$key=$($Context[$key])"
    }
    [System.IO.File]::WriteAllLines($logPath, $headerLines, $script:BackupOpsUtf8NoBom)

    return [PSCustomObject][ordered]@{
        action         = $Action
        startedAt      = [System.DateTimeOffset]$StartedAt
        logRoot        = $LogRoot
        logPath        = $logPath
        reportBasePath = $reportBasePath
        reportPath     = $null
        sequenceId     = $timestampId
    }
}

function Start-BackupOpsLogSession {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [string]$OperatorName = 'unknown',
        [object]$StartedAt = $null
    )

    return New-BackupOpsLogSession `
        -Action $Action `
        -LogRoot ([string]$Config.console.logRoot) `
        -OperatorName $OperatorName `
        -Mode $Action `
        -StartedAt $StartedAt
}

function Write-BackupOpsLog {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,

        [Parameter(Mandatory = $true)]
        [string]$Message,

        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level = 'INFO',

        [object]$Timestamp = $null
    )

    if ($null -eq $Timestamp) {
        $Timestamp = [System.DateTimeOffset]::Now
    }

    $line = "[{0}] [{1}] {2}" -f ([System.DateTimeOffset]$Timestamp).ToString('yyyy-MM-dd HH:mm:ss zzz'), $Level, $Message
    [System.IO.File]::AppendAllText([string]$Session.logPath, $line + [Environment]::NewLine, $script:BackupOpsUtf8NoBom)
}

function Complete-BackupOpsLogSession {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,

        [Parameter(Mandatory = $true)]
        [ValidateSet('success', 'fail', 'blocked')]
        [string]$Status,

        [string]$Summary = ''
    )

    $directory = Split-Path -Parent ([string]$Session.logPath)
    $finalLogPath = Join-Path $directory "$($Session.sequenceId)_$($Session.action)_$Status.log"
    $reportPath = "$($Session.reportBasePath)_$Status.report.md"
    $reportJsonPath = "$($Session.reportBasePath)_$Status.report.json"
    if ($finalLogPath -ne [string]$Session.logPath) {
        Move-Item -LiteralPath ([string]$Session.logPath) -Destination $finalLogPath -Force
    }

    if ($Summary) {
        $line = "[{0}] [INFO] finalStatus={1}; summary={2}" -f [System.DateTimeOffset]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'), $Status, $Summary
        [System.IO.File]::AppendAllText($finalLogPath, $line + [Environment]::NewLine, $script:BackupOpsUtf8NoBom)
    }

    $Session.logPath = $finalLogPath
    $Session.reportPath = $reportPath
    if ($Session.PSObject.Properties['reportJsonPath']) {
        $Session.reportJsonPath = $reportJsonPath
    }
    else {
        Add-Member -InputObject $Session -NotePropertyName 'reportJsonPath' -NotePropertyValue $reportJsonPath
    }

    return [PSCustomObject][ordered]@{
        action         = $Session.action
        startedAt      = $Session.startedAt
        completedAt    = [System.DateTimeOffset]::Now
        status         = $Status
        logPath        = $finalLogPath
        reportPath     = $reportPath
        reportJsonPath = $reportJsonPath
    }
}

Export-ModuleMember -Function @(
    'Complete-BackupOpsLogSession',
    'New-BackupOpsLogSession',
    'New-BackupOpsLogTimestamp',
    'New-BackupOpsSequenceId',
    'Resolve-BackupOpsLogDirectory',
    'Start-BackupOpsLogSession',
    'Write-BackupOpsLog'
)
