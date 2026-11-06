$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$transportRoot = 'C:/Spug/runtime/private/full-to-prod-20261105'
$mutex = [Threading.Mutex]::new($false, 'Local\SpugProdMainRestoreTransport20261105')
if (-not $mutex.WaitOne(0)) { throw 'PRODUCTION_RESTORE_TRANSPORT_ALREADY_RUNNING' }
try {
    $transportArguments = @('-F','NUL','-N','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
        '-o','IdentitiesOnly=yes','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=20',
        '-o','ServerAliveCountMax=3','-o','ConnectTimeout=8',
        '-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile',
        '-i','C:/SpugHandoff/release/private/sshIdentityFile',
        '-L','127.0.0.1:43657:127.0.0.1:43657','root@172.30.30.57')
    while ($true) {
        $child = Start-Process -FilePath 'C:/Windows/System32/OpenSSH/ssh.exe' -ArgumentList $transportArguments -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput ($transportRoot+'/transport-production.stdout.log') `
            -RedirectStandardError ($transportRoot+'/transport-production.stderr.log')
        $receipt = @{ target='172.30.30.57'; supervisorPid=$PID; sshPid=$child.Id; controlPort=43657; startedAt=[DateTime]::UtcNow.ToString('o') }
        [IO.File]::WriteAllText(($transportRoot+'/transport-production.json'),($receipt | ConvertTo-Json -Compress),[Text.UTF8Encoding]::new($false))
        $child.WaitForExit()
        Start-Sleep -Seconds 10
    }
} finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
