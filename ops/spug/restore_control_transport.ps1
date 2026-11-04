param([Parameter(Mandatory=$true)][ValidateSet('57','58','59')][string]$Target)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$runtimeRoot = 'C:\Spug\runtime\private\restore-targets-20261104'
$identityFile = 'C:/SpugHandoff/release/private/sshIdentityFile'
$knownHostsFile = 'C:/SpugHandoff/release/private/sshKnownHostsFile'
$sshExecutable = 'C:\Windows\System32\OpenSSH\ssh.exe'
$controlPort = switch ($Target) { '57' { '42657' } '58' { '43658' } '59' { '33659' } }
$sshPort = '185' + $Target
$mutex = [System.Threading.Mutex]::new($false, 'Local\SpugMainRestoreTransport20261104_' + $Target)
if (-not $mutex.WaitOne(0)) { throw 'RESTORE_TRANSPORT_ALREADY_RUNNING' }
try {
    $transportArguments = @('-F','NUL','-N','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
        '-o','IdentitiesOnly=yes','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=20',
        '-o','ServerAliveCountMax=3','-o','ConnectTimeout=8','-o',('UserKnownHostsFile='+$knownHostsFile),
        '-i',$identityFile,'-L',('127.0.0.1:'+$controlPort+':127.0.0.1:'+$(if ($Target -eq '57') { '32657' } else { $controlPort })))
    if ($Target -ne '57') {
        $transportArguments += @('-L',('127.0.0.1:'+$sshPort+':127.0.0.1:22'),'-R','127.0.0.1:34657:127.0.0.1:42657')
    }
    $transportArguments += ('root@172.30.30.'+$Target)
    while ($true) {
        $child = Start-Process -FilePath $sshExecutable -ArgumentList $transportArguments -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput ($runtimeRoot+'\transport-'+$Target+'.stdout.log') `
            -RedirectStandardError ($runtimeRoot+'\transport-'+$Target+'.stderr.log')
        $receipt = @{ target=('172.30.30.'+$Target); supervisorPid=$PID; sshPid=$child.Id; controlPort=$controlPort; startedAt=[DateTime]::UtcNow.ToString('o') }
        [IO.File]::WriteAllText(($runtimeRoot+'\transport-'+$Target+'.json'), ($receipt | ConvertTo-Json -Compress), [Text.UTF8Encoding]::new($false))
        $child.WaitForExit()
        Start-Sleep -Seconds 10
    }
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
