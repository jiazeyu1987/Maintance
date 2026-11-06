$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$sourcePath = Join-Path $PSScriptRoot 'production_control_transport.ps1'
$destination = 'C:/Spug/runtime/private/full-to-prod-20261105/production_control_transport.ps1'
$taskName = 'SpugProdMainRestoreTransport57-20261105'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) { throw 'PRODUCTION_TRANSPORT_TASK_EXISTS' }
if (Get-NetTCPConnection -State Listen -LocalPort 43657 -ErrorAction SilentlyContinue) { throw 'PRODUCTION_TRANSPORT_PORT_USED' }
$tokens = $null; $parseErrors = $null
$null = [Management.Automation.Language.Parser]::ParseFile($sourcePath,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'PRODUCTION_TRANSPORT_PARSE_FAILED' }
if (Test-Path -LiteralPath $destination) { throw 'PRODUCTION_TRANSPORT_FILE_EXISTS' }
Copy-Item -LiteralPath $sourcePath -Destination $destination
if ((Get-FileHash -LiteralPath $sourcePath).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) { throw 'PRODUCTION_TRANSPORT_COPY_CHANGED' }
$taskUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File '+$destination)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$null = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Owned production MAIN restore control transport only.'
Start-ScheduledTask -TaskName $taskName
$receipt = @{ taskName=$taskName; sourcePath=$sourcePath; stablePath=$destination; sha256=(Get-FileHash -LiteralPath $destination).Hash.ToLower(); restorePerformed=$false }
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'transport-installation.json'),($receipt | ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
$receipt | ConvertTo-Json -Compress
