[CmdletBinding()]
param(
    [string]$ConfigPath = '',
    [string]$SecretsPath = '',
    [switch]$PlanOnly
)

Set-StrictMode -Version Latest
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backupOpsRoot = Split-Path -Parent $scriptDir
$configModulePath = Join-Path $backupOpsRoot 'scripts\modules\Core\Config.psm1'
Import-Module $configModulePath -Force -DisableNameChecking | Out-Null

function Resolve-BackupOpsScriptPath {
    return (Join-Path $backupOpsRoot 'scripts\backup-ops.ps1')
}

function ConvertTo-BackupOpsDailyTrigger {
    param(
        [Parameter(Mandatory)]
        [string]$Schedule
    )

    $hour, $minute = $Schedule.Split(':')
    $today = Get-Date
    $startBoundary = Get-Date -Year $today.Year -Month $today.Month -Day $today.Day -Hour ([int]$hour) -Minute ([int]$minute) -Second 0
    return New-ScheduledTaskTrigger -Daily -At $startBoundary
}

function ConvertTo-BackupOpsWeeklyTrigger {
    param(
        [Parameter(Mandatory)]
        [string]$Schedule
    )

    $parts = $Schedule.Split(' ', 2)
    $dayCode = $parts[0]
    $timeValue = $parts[1]
    $hour, $minute = $timeValue.Split(':')
    $dayMap = @{
        MON = 'Monday'
        TUE = 'Tuesday'
        WED = 'Wednesday'
        THU = 'Thursday'
        FRI = 'Friday'
        SAT = 'Saturday'
        SUN = 'Sunday'
    }
    $today = Get-Date
    $startBoundary = Get-Date -Year $today.Year -Month $today.Month -Day $today.Day -Hour ([int]$hour) -Minute ([int]$minute) -Second 0
    return New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dayMap[$dayCode] -At $startBoundary
}

function New-BackupOpsScheduledTaskPlan {
    param(
        [Parameter(Mandatory)]
        [string]$TaskName,
        [Parameter(Mandatory)]
        [string]$Mode,
        [Parameter(Mandatory)]
        [string]$ConfigPath,
        [Parameter(Mandatory)]
        [string]$SecretsPath,
        [Parameter(Mandatory)]
        [object]$Trigger,
        [string]$OperatorName = ''
    )

    $scriptPath = Resolve-BackupOpsScriptPath
    $argumentParts = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $scriptPath),
        '-Mode', $Mode,
        '-ConfigPath', ('"{0}"' -f $ConfigPath),
        '-SecretsPath', ('"{0}"' -f $SecretsPath),
        '-NonInteractive'
    )
    if (-not [string]::IsNullOrWhiteSpace($OperatorName)) {
        $argumentParts += @('-OperatorName', ('"{0}"' -f $OperatorName))
    }
    $arguments = $argumentParts -join ' '

    return [pscustomobject]([ordered]@{
            taskName   = $TaskName
            mode       = $Mode
            executable = 'powershell.exe'
            arguments  = $arguments
            trigger    = $Trigger
        })
}

$config = Import-BackupOpsConfiguration -ConfigPath $ConfigPath -SecretsPath $SecretsPath
$resolvedConfigPath = if ([string]::IsNullOrWhiteSpace($ConfigPath)) { (Get-BackupOpsDefaultConfigPaths).configPath } else { $ConfigPath }
$resolvedSecretsPath = if ([string]::IsNullOrWhiteSpace($SecretsPath)) { (Get-BackupOpsDefaultConfigPaths).secretsPath } else { $SecretsPath }

$backupPlan = New-BackupOpsScheduledTaskPlan `
    -TaskName 'IntRuoyi Backup Scheduled' `
    -Mode 'backup-scheduled' `
    -ConfigPath $resolvedConfigPath `
    -SecretsPath $resolvedSecretsPath `
    -Trigger (ConvertTo-BackupOpsDailyTrigger -Schedule ([string]$config.backup.schedule))

$rehearsalPlan = New-BackupOpsScheduledTaskPlan `
    -TaskName 'IntRuoyi Rehearsal' `
    -Mode 'rehearsal' `
    -ConfigPath $resolvedConfigPath `
    -SecretsPath $resolvedSecretsPath `
    -Trigger (ConvertTo-BackupOpsWeeklyTrigger -Schedule ([string]$config.rehearsal.schedule)) `
    -OperatorName 'scheduler'

$plans = @($backupPlan, $rehearsalPlan)
if ($PlanOnly) {
    $plans | Select-Object taskName, mode, executable, arguments | ConvertTo-Json -Depth 6
    exit 0
}

foreach ($plan in $plans) {
    $action = New-ScheduledTaskAction -Execute $plan.executable -Argument $plan.arguments
    Register-ScheduledTask -TaskName $plan.taskName -Action $action -Trigger $plan.trigger -Description "IntRuoyi $($plan.mode)" -Force | Out-Null
}

$plans | Select-Object taskName, mode | Format-Table -AutoSize
