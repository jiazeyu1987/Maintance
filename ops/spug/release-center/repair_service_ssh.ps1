param([Parameter(Mandatory=$true)][string]$Descriptor,
      [Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference = 'Stop'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator PowerShell required; nothing changed.' }
$Descriptor = (Resolve-Path -LiteralPath $Descriptor).Path
function AssertDescriptor {
    $active = & $Python -c "import win32serviceutil; print(win32serviceutil.GetServiceCustomOption('IntRuoyiReleaseExecutor','Descriptor'))"
    if ($LASTEXITCODE -ne 0 -or (Resolve-Path -LiteralPath $active).Path -ne $Descriptor) { throw 'Active service descriptor changed; nothing further applied.' }
}
AssertDescriptor
$description = Get-Content -LiteralPath $Descriptor -Raw -Encoding UTF8 | ConvertFrom-Json
$configPath = $description.config
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$headers = @{'X-Release-Key'=$config.bridgeKey}
$stateUrl = 'http://127.0.0.1:' + $config.port + '/state'
function GetIdleState {
    $current = Invoke-RestMethod -Uri $stateUrl -Headers $headers -TimeoutSec 20
    if ($current.executorRuntime.mode -ne 'windows-service' -or @($current.jobs | Where-Object { $_.status -eq 'running' }).Count -gt 0) { throw 'Expected idle Windows service before SSH configuration change.' }
    return $current
}
$before = GetIdleState
$configHash = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash
$sourceKey = (Resolve-Path -LiteralPath $config.sshIdentityFile).Path
$sourceHosts = (Resolve-Path -LiteralPath $config.sshKnownHostsFile).Path
$keyHash = (Get-FileHash -LiteralPath $sourceKey -Algorithm SHA256).Hash
$root = Split-Path -Parent $Descriptor
$suffix = [guid]::NewGuid().ToString('N')
$credentialDirectory = Join-Path $root ('service-ssh-' + $suffix)
New-Item -ItemType Directory -Path $credentialDirectory | Out-Null
function SetExactAcl([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetSecurityDescriptorSddlForm('D:P(A;;FA;;;SY)(A;;FA;;;BA)', [Security.AccessControl.AccessControlSections]::Access)
    Set-Acl -LiteralPath $Path -AclObject $acl
    & icacls.exe $Path /setowner '*S-1-5-18' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not set the service-only SSH credential permissions.' }
}
# Restrict the empty directory before copying private material.
SetExactAcl $credentialDirectory
$serviceKey = Join-Path $credentialDirectory 'id_rsa'
$serviceHosts = Join-Path $credentialDirectory 'known_hosts'
Copy-Item -LiteralPath $sourceKey -Destination $serviceKey
Copy-Item -LiteralPath $sourceHosts -Destination $serviceHosts
SetExactAcl $serviceKey
SetExactAcl $serviceHosts
if ((Get-FileHash -LiteralPath $serviceKey -Algorithm SHA256).Hash -ne $keyHash) { throw 'SSH identity copy differs.' }
# The operator can locate these files, but cannot read the private key.
& icacls.exe $credentialDirectory /grant ('*' + $description.operatorSid + ':(RX)') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not grant operator directory traversal.' }
$config.sshIdentityFile = $serviceKey
$config.sshKnownHostsFile = $serviceHosts
$candidate = Join-Path $root ('executor.ssh-' + $suffix + '.private.json')
[System.IO.File]::WriteAllText($candidate, ($config | ConvertTo-Json -Depth 100), (New-Object System.Text.UTF8Encoding($false)))
$resultPath = Join-Path $root ('ssh-probe-' + $suffix + '.json')
$probe = Join-Path $PSScriptRoot 'probe_service_ssh.py'
$taskName = 'IntRuoyiReleaseSshProbe-' + $suffix
$action = New-ScheduledTaskAction -Execute $Python -Argument ('-X utf8 "' + $probe + '" "' + $resultPath + '" "' + $candidate + '"')
$identity = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$registered = $false
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $identity -Settings $settings | Out-Null
    $registered = $true
    Start-ScheduledTask -TaskName $taskName
    $deadline = [DateTime]::UtcNow.AddSeconds(75)
    while (!(Test-Path -LiteralPath $resultPath)) {
        if ([DateTime]::UtcNow -gt $deadline) { throw 'Service identity SSH check timed out; live configuration unchanged.' }
        Start-Sleep -Seconds 1
    }
    $result = Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($result.account -ne 'SYSTEM' -or $result.error -or @($result.checks).Count -ne 3 -or @($result.checks | Where-Object { $_.exit -ne 0 }).Count -gt 0) {
        $result | ConvertTo-Json -Depth 10
        throw 'Service SSH verification failed; live configuration unchanged.'
    }
} finally {
    if ($registered) {
        if ((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') { Stop-ScheduledTask -TaskName $taskName }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
}
AssertDescriptor
$null = GetIdleState
if ((Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash -ne $configHash) { throw 'Live configuration changed while checking SSH.' }
if ((Get-FileHash -LiteralPath $sourceKey -Algorithm SHA256).Hash -ne $keyHash) { throw 'Original SSH identity changed while checking SSH.' }
$backup = Join-Path $root ('executor.before-ssh-' + $suffix + '.private.json')
[System.IO.File]::Replace($candidate, $configPath, $backup)
$manager = Join-Path $root 'source\ops\spug\release-center\manage_executor_service.py'
& $Python $manager restart --descriptor $Descriptor
if ($LASTEXITCODE -ne 0) { throw 'SSH configuration saved but executor restart failed; preserve output for diagnosis.' }
$after = GetIdleState
foreach ($name in @('artifactRetention','releasePrecheck','productionRollback')) {
    if ($before.application.capabilities.$name -eq $true -and $after.application.capabilities.$name -ne $true) { throw ('Existing capability missing after restart: ' + $name) }
}
[ordered]@{service='IntRuoyiReleaseExecutor';runtime=$after.executorRuntime;sshTargetsVerified=3;originalKeyUnchanged=$true;remoteApplicationsRestarted=$false} | ConvertTo-Json -Depth 5
