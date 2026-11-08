$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$transportRoot = 'C:/Spug/runtime/private/restore-targets-20261104'
$transportDestination = $transportRoot + '/restore_control_transport.ps1'
$sourcePath = Join-Path $PSScriptRoot '../../../ops/spug/restore_control_transport.ps1'
if (@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -eq 42657}).Count -gt 0) { throw 'RESTORE_SOURCE_PORT_USED' }
foreach ($suffix in @('58','59')) {
    $receipt = Get-Content -LiteralPath ($transportRoot+'/transport-'+$suffix+'.json') -Encoding utf8 | ConvertFrom-Json
    $supervisor = Get-CimInstance Win32_Process -Filter ('ProcessId = '+$receipt.supervisorPid)
    $ssh = Get-CimInstance Win32_Process -Filter ('ProcessId = '+$receipt.sshPid)
    if ($supervisor.CommandLine -notlike '*restore-targets-20261104/restore_control_transport.ps1*' -or $supervisor.CommandLine -notlike ('*-Target '+$suffix+'*')) { throw 'TRANSPORT_SUPERVISOR_OWNER_CHANGED' }
    if ($ssh.CommandLine -notlike ('*root@172.30.30.'+$suffix+'*') -or $ssh.CommandLine -notlike '*127.0.0.1:34657:127.0.0.1:32657*') { throw 'TRANSPORT_SSH_OWNER_CHANGED' }
    Stop-Process -Id $receipt.supervisorPid -ErrorAction Stop
    Stop-Process -Id $receipt.sshPid -ErrorAction Stop
}
Copy-Item -LiteralPath $sourcePath -Destination $transportDestination
if ((Get-FileHash -LiteralPath $sourcePath).Hash -ne (Get-FileHash -LiteralPath $transportDestination).Hash) { throw 'TRANSPORT_COPY_CHANGED' }
$taskUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$results = @()
foreach ($suffix in @('57','58','59')) {
    $taskName = 'SpugMainRestoreTransport'+$suffix+'-20261104'
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'TRANSPORT_STARTUP_TASK_ALREADY_EXISTS' }
    $arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File '+$transportDestination+' -Target '+$suffix
    $action = New-ScheduledTaskAction -Execute 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
    $null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Owned Spug main restore control transport; no backup or restore execution.'
    Start-ScheduledTask -TaskName $taskName
    $results += @{target=('172.30.30.'+$suffix);taskName=$taskName;startup='current-user-logon';runsBackupOrRestore=$false}
}
[IO.File]::WriteAllText(($transportRoot+'/transport-startup.json'),($results | ConvertTo-Json -Depth 4),[Text.UTF8Encoding]::new($false))
$results | ConvertTo-Json -Compress
