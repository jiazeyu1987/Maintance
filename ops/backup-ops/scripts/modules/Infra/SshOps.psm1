Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)
$script:BackupOpsDefaultSshTimeoutSeconds = 300
$script:BackupOpsDefaultScpTimeoutSeconds = 300

function New-BackupOpsSshException {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('INTBK-2001', 'INTBK-2002', 'INTBK-2003')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Message,
        [ValidateSet('blocked', 'fail')]
        [string]$Status = 'fail'
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsCode'] = $Code
    $exception.Data['BackupOpsStatus'] = $Status
    return $exception
}

function New-BackupOpsSshOperatorBlockedMessage {
    param(
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    return "原因：$Reason`n建议动作：$Action"
}

function Get-BackupSshFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name,
        [ValidateSet('INTBK-2001', 'INTBK-2002', 'INTBK-2003')]
        [string]$Code = 'INTBK-2001'
    )

    if (-not $Request.ContainsKey($Name)) {
        throw (New-BackupOpsSshException -Code $Code -Status 'blocked' -Message "Missing SSH request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw (New-BackupOpsSshException -Code $Code -Status 'blocked' -Message "SSH request field '$Name' cannot be empty.")
    }

    return [string]$value
}

function Remove-BackupSshNoise {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ''
    }

    return (($Text -split "`r?`n") | Where-Object {
            $_ -and $_ -notlike 'close - IO is still pending on closed socket.*'
        }) -join "`n"
}

function Resolve-BackupSshPath {
    param(
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ''
    }

    return [System.Environment]::ExpandEnvironmentVariables($Path)
}

function Assert-BackupSshExecutable {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not (Get-Command -Name $Name -ErrorAction SilentlyContinue)) {
        throw (New-BackupOpsSshException -Code 'INTBK-2001' -Status 'blocked' -Message "Missing required command on operator machine: $Name")
    }
}

function ConvertTo-BackupNativeArgumentString {
    param(
        [string[]]$ArgumentList = @()
    )

    return (@($ArgumentList) | ForEach-Object {
            $argument = if ($null -eq $_) { '' } else { [string]$_ }
            '"' + ($argument -replace '\\', '\\' -replace '"', '\"') + '"'
        }) -join ' '
}

function Merge-BackupSshRequest {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [hashtable]$Extra
    )

    $merged = @{}
    foreach ($key in $Request.Keys) {
        $merged[$key] = $Request[$key]
    }
    foreach ($key in $Extra.Keys) {
        $merged[$key] = $Extra[$key]
    }

    return $merged
}

function Get-BackupSshCommonArguments {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$ForScp
    )

    $arguments = @(
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        '-o', 'ServerAliveInterval=15',
        '-o', 'ServerAliveCountMax=2'
    )
    if (-not $ForScp) {
        $arguments += '-n'
    }

    if ($Request.ContainsKey('KnownHostsPath') -and -not [string]::IsNullOrWhiteSpace([string]$Request['KnownHostsPath'])) {
        $knownHostsPath = Resolve-BackupSshPath -Path ([string]$Request['KnownHostsPath'])
        $arguments += @('-o', "UserKnownHostsFile=$knownHostsPath")
    }

    if ($Request.ContainsKey('KeyPath') -and -not [string]::IsNullOrWhiteSpace([string]$Request['KeyPath'])) {
        $keyPath = Resolve-BackupSshPath -Path ([string]$Request['KeyPath'])
        if (-not (Test-Path -LiteralPath $keyPath)) {
            throw (New-BackupOpsSshException -Code 'INTBK-2001' -Status 'blocked' -Message (New-BackupOpsSshOperatorBlockedMessage -Reason "SSH 私钥文件不存在：$keyPath" -Action '请在操作机 secrets 文件中配置 auth.sshKeyPath，并确认该私钥文件存在且可被当前用户读取。'))
        }
        $arguments += @('-i', $keyPath)
    }

    if ($Request.ContainsKey('Port') -and -not [string]::IsNullOrWhiteSpace([string]$Request['Port'])) {
        $port = [int]$Request['Port']
        if ($ForScp) {
            $arguments += @('-P', [string]$port)
        } else {
            $arguments += @('-p', [string]$port)
        }
    }

    return $arguments
}

function Invoke-BackupNativeProcess {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = '',
        [string]$StdOutPath = '',
        [string]$StdErrPath = '',
        [int]$TimeoutSeconds = 0,
        [switch]$SkipReadStdOut,
        [switch]$SkipReadStdErr
    )

    $tempDir = $null
    $createdStdOutPath = $false
    $createdStdErrPath = $false
    $timedOut = $false
    try {
        if ([string]::IsNullOrWhiteSpace($StdOutPath) -or [string]::IsNullOrWhiteSpace($StdErrPath)) {
            $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("backup-ops-ssh-" + [System.Guid]::NewGuid().ToString('N'))
            [void][System.IO.Directory]::CreateDirectory($tempDir)
            if ([string]::IsNullOrWhiteSpace($StdOutPath)) {
                $StdOutPath = Join-Path $tempDir 'stdout.log'
                $createdStdOutPath = $true
            }
            if ([string]::IsNullOrWhiteSpace($StdErrPath)) {
                $StdErrPath = Join-Path $tempDir 'stderr.log'
                $createdStdErrPath = $true
            }
        }

        foreach ($path in @($StdOutPath, $StdErrPath)) {
            if ([string]::IsNullOrWhiteSpace($path)) {
                continue
            }
            $parent = Split-Path -Parent $path
            if (-not [string]::IsNullOrWhiteSpace($parent)) {
                [void][System.IO.Directory]::CreateDirectory($parent)
            }
        }

        $effectiveWorkingDirectory = if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) { (Get-Location).Path } else { $WorkingDirectory }
        if ($TimeoutSeconds -gt 0) {
            $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
            $startInfo.FileName = $FilePath
            $startInfo.Arguments = ConvertTo-BackupNativeArgumentString -ArgumentList $ArgumentList
            $startInfo.WorkingDirectory = $effectiveWorkingDirectory
            $startInfo.UseShellExecute = $false
            $startInfo.CreateNoWindow = $true
            $startInfo.RedirectStandardOutput = $true
            $startInfo.RedirectStandardError = $true
            $process = [System.Diagnostics.Process]::new()
            $process.StartInfo = $startInfo
            [void]$process.Start()
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
                $timedOut = $true
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                $process.WaitForExit()
            }
            $stdoutText = $stdoutTask.GetAwaiter().GetResult()
            $stderrText = $stderrTask.GetAwaiter().GetResult()
            $stdout = if ($SkipReadStdOut) { '' } else { $stdoutText }
            $stderr = if ($SkipReadStdErr) { '' } else { $stderrText }
        } else {
            $process = Start-Process -FilePath $FilePath `
                -ArgumentList $ArgumentList `
                -WorkingDirectory $effectiveWorkingDirectory `
                -RedirectStandardOutput $StdOutPath `
                -RedirectStandardError $StdErrPath `
                -NoNewWindow `
                -Wait `
                -PassThru
            $process.Refresh()

            $stdout = ''
            $stderr = ''
            if (-not $SkipReadStdOut -and (Test-Path -LiteralPath $StdOutPath)) {
                $stdout = [System.IO.File]::ReadAllText($StdOutPath, $script:BackupOpsUtf8NoBom)
            }
            if (-not $SkipReadStdErr -and (Test-Path -LiteralPath $StdErrPath)) {
                $stderr = [System.IO.File]::ReadAllText($StdErrPath, $script:BackupOpsUtf8NoBom)
            }
        }
        if ($timedOut) {
            $stderr = (($stderr, "Native process timed out after $TimeoutSeconds seconds.") | Where-Object {
                    -not [string]::IsNullOrWhiteSpace($_)
                }) -join "`n"
        }

        return @{
            ExitCode = if ($timedOut) { 124 } else { $process.ExitCode }
            StdOut = $stdout
            StdErr = $stderr
            StdOutPath = $StdOutPath
            StdErrPath = $StdErrPath
        }
    } finally {
        if ($tempDir -and (Test-Path -LiteralPath $tempDir)) {
            Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        } else {
            $cleanupPaths = @()
            if ($createdStdOutPath -and $StdOutPath) {
                $cleanupPaths += $StdOutPath
            }
            if ($createdStdErrPath -and $StdErrPath) {
                $cleanupPaths += $StdErrPath
            }
            foreach ($path in $cleanupPaths) {
                if ($path -and (Test-Path -LiteralPath $path)) {
                    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
}

function New-BackupSshExecutionPlan {
    param(
        [Parameter(Mandatory)]
        [string]$Operation,
        [Parameter(Mandatory)]
        [string]$Tool,
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    return [pscustomobject]([ordered]@{
            operation = $Operation
            tool = $Tool
            arguments = @($Arguments)
            host = $Request['Host']
            user = $Request['User']
            port = if ($Request.ContainsKey('Port')) { [int]$Request['Port'] } else { 22 }
            command = $Request['Command']
            localPath = $Request['LocalPath']
            remotePath = $Request['RemotePath']
        })
}

function Test-BackupSshConnection {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $host = Get-BackupSshFieldValue -Request $Request -Name 'Host'
    $user = Get-BackupSshFieldValue -Request $Request -Name 'User'
    $arguments = Get-BackupSshCommonArguments -Request $Request
    $arguments += @("${user}@${host}", 'echo SSH_OK')
    $plan = New-BackupSshExecutionPlan -Operation 'ssh-connect' -Tool 'ssh' -Arguments $arguments -Request (Merge-BackupSshRequest -Request $Request -Extra @{ Command = 'echo SSH_OK' })
    if ($PlanOnly) {
        return $plan
    }

    Assert-BackupSshExecutable -Name 'ssh'
    $result = Invoke-BackupNativeProcess -FilePath 'ssh' -ArgumentList $arguments -TimeoutSeconds $script:BackupOpsDefaultSshTimeoutSeconds
    $output = Remove-BackupSshNoise (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($result.ExitCode -ne 0 -or $output -notmatch 'SSH_OK') {
        throw (New-BackupOpsSshException -Code 'INTBK-2001' -Status 'fail' -Message "SSH connectivity check failed for ${user}@${host}. $output")
    }

    return [pscustomobject]([ordered]@{
            operation = 'ssh-connect'
            status = 'success'
            code = 'INTBK-0000'
            host = $host
            user = $user
            output = $output
        })
}

function Invoke-BackupSshCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $host = Get-BackupSshFieldValue -Request $Request -Name 'Host'
    $user = Get-BackupSshFieldValue -Request $Request -Name 'User'
    $command = Get-BackupSshFieldValue -Request $Request -Name 'Command' -Code 'INTBK-2003'

    $arguments = Get-BackupSshCommonArguments -Request $Request
    $arguments += @("${user}@${host}", $command)
    $plan = New-BackupSshExecutionPlan -Operation 'ssh-command' -Tool 'ssh' -Arguments $arguments -Request $Request
    if ($PlanOnly) {
        return $plan
    }

    Assert-BackupSshExecutable -Name 'ssh'

    $outputPath = if ($Request.ContainsKey('OutputPath')) { [string]$Request['OutputPath'] } else { '' }
    $workingDirectory = if ($Request.ContainsKey('WorkingDirectory')) { [string]$Request['WorkingDirectory'] } else { '' }
    $timeoutSeconds = if ($Request.ContainsKey('TimeoutSeconds')) { [int]$Request['TimeoutSeconds'] } else { $script:BackupOpsDefaultSshTimeoutSeconds }
    $skipReadStdOut = -not [string]::IsNullOrWhiteSpace($outputPath)
    $result = Invoke-BackupNativeProcess `
        -FilePath 'ssh' `
        -ArgumentList $arguments `
        -WorkingDirectory $workingDirectory `
        -StdOutPath $outputPath `
        -TimeoutSeconds $timeoutSeconds `
        -SkipReadStdOut:$skipReadStdOut

    $output = Remove-BackupSshNoise (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($result.ExitCode -ne 0) {
        throw (New-BackupOpsSshException -Code 'INTBK-2003' -Status 'fail' -Message "SSH command failed for ${user}@${host}: $command`n$output")
    }

    return [pscustomobject]([ordered]@{
            operation = 'ssh-command'
            status = 'success'
            code = 'INTBK-0000'
            host = $host
            user = $user
            command = $command
            output = $output
            outputPath = if ([string]::IsNullOrWhiteSpace($outputPath)) { $null } else { $outputPath }
        })
}

function Send-BackupFileOverSsh {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $host = Get-BackupSshFieldValue -Request $Request -Name 'Host'
    $user = Get-BackupSshFieldValue -Request $Request -Name 'User'
    $localPath = Get-BackupSshFieldValue -Request $Request -Name 'LocalPath' -Code 'INTBK-2002'
    $remotePath = Get-BackupSshFieldValue -Request $Request -Name 'RemotePath' -Code 'INTBK-2002'
    if (-not (Test-Path -LiteralPath $localPath)) {
        throw (New-BackupOpsSshException -Code 'INTBK-2002' -Status 'blocked' -Message "Local file to upload was not found: $localPath")
    }

    $arguments = Get-BackupSshCommonArguments -Request $Request -ForScp
    if ($Request.ContainsKey('Recursive') -and [bool]$Request['Recursive']) {
        $arguments += '-r'
    }
    $arguments += @($localPath, "${user}@${host}:$remotePath")
    $plan = New-BackupSshExecutionPlan -Operation 'ssh-upload' -Tool 'scp' -Arguments $arguments -Request $Request
    if ($PlanOnly) {
        return $plan
    }

    Assert-BackupSshExecutable -Name 'scp'
    $timeoutSeconds = if ($Request.ContainsKey('TimeoutSeconds')) { [int]$Request['TimeoutSeconds'] } else { $script:BackupOpsDefaultScpTimeoutSeconds }
    $result = Invoke-BackupNativeProcess -FilePath 'scp' -ArgumentList $arguments -TimeoutSeconds $timeoutSeconds
    $output = Remove-BackupSshNoise (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($result.ExitCode -ne 0) {
        throw (New-BackupOpsSshException -Code 'INTBK-2002' -Status 'fail' -Message "SCP upload failed for ${user}@${host}: $localPath -> $remotePath`n$output")
    }

    return [pscustomobject]([ordered]@{
            operation = 'ssh-upload'
            status = 'success'
            code = 'INTBK-0000'
            host = $host
            user = $user
            localPath = $localPath
            remotePath = $remotePath
            output = $output
        })
}

function Receive-BackupFileOverSsh {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $host = Get-BackupSshFieldValue -Request $Request -Name 'Host'
    $user = Get-BackupSshFieldValue -Request $Request -Name 'User'
    $remotePath = Get-BackupSshFieldValue -Request $Request -Name 'RemotePath' -Code 'INTBK-2002'
    $localPath = Get-BackupSshFieldValue -Request $Request -Name 'LocalPath' -Code 'INTBK-2002'

    $arguments = Get-BackupSshCommonArguments -Request $Request -ForScp
    if ($Request.ContainsKey('Recursive') -and [bool]$Request['Recursive']) {
        $arguments += '-r'
    }
    $arguments += @("${user}@${host}:$remotePath", $localPath)
    $plan = New-BackupSshExecutionPlan -Operation 'ssh-download' -Tool 'scp' -Arguments $arguments -Request $Request
    if ($PlanOnly) {
        return $plan
    }

    Assert-BackupSshExecutable -Name 'scp'
    $localParent = Split-Path -Parent $localPath
    if (-not [string]::IsNullOrWhiteSpace($localParent)) {
        [void][System.IO.Directory]::CreateDirectory($localParent)
    }

    $timeoutSeconds = if ($Request.ContainsKey('TimeoutSeconds')) { [int]$Request['TimeoutSeconds'] } else { $script:BackupOpsDefaultScpTimeoutSeconds }
    $result = Invoke-BackupNativeProcess -FilePath 'scp' -ArgumentList $arguments -TimeoutSeconds $timeoutSeconds
    $output = Remove-BackupSshNoise (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($result.ExitCode -ne 0) {
        throw (New-BackupOpsSshException -Code 'INTBK-2002' -Status 'fail' -Message "SCP download failed for ${user}@${host}: $remotePath -> $localPath`n$output")
    }

    return [pscustomobject]([ordered]@{
            operation = 'ssh-download'
            status = 'success'
            code = 'INTBK-0000'
            host = $host
            user = $user
            remotePath = $remotePath
            localPath = $localPath
            output = $output
        })
}

Export-ModuleMember -Function Test-BackupSshConnection, Invoke-BackupSshCommand, Send-BackupFileOverSsh, Receive-BackupFileOverSsh
