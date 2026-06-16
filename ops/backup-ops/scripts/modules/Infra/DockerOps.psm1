Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Import-BackupOpsSshDependency {
    if (Get-Command -Name 'Invoke-BackupSshCommand' -ErrorAction SilentlyContinue) {
        return
    }

    $sshModulePath = Join-Path $PSScriptRoot 'SshOps.psm1'
    if (-not (Test-Path -LiteralPath $sshModulePath)) {
        throw "SSH module not found: $sshModulePath"
    }

    Import-Module $sshModulePath -Force -DisableNameChecking -ErrorAction Stop | Out-Null
}

function Import-BackupOpsDccChainValidatorDependency {
    if (Get-Command -Name 'Test-DccBackupChainManifest' -ErrorAction SilentlyContinue) {
        return
    }

    $modulesRoot = Split-Path -Parent $PSScriptRoot
    $validatorModulePath = Join-Path $modulesRoot 'Core\DccBackupChainValidator.psm1'
    if (-not (Test-Path -LiteralPath $validatorModulePath)) {
        throw "DCC backup chain validator module not found: $validatorModulePath"
    }

    Import-Module $validatorModulePath -Force -DisableNameChecking -ErrorAction Stop | Out-Null
}

function Test-BackupOpsRemoteDccBackupManifestContract {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Import-BackupOpsDccChainValidatorDependency
    try {
        $dccManifest = (Get-BackupOpsRemoteFileText -SshRequest $SshRequest -Path $Path) | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        return [pscustomobject]([ordered]@{
                status = 'blocked'
                errorCodes = @('dcc_backup_manifest_unreadable')
                message = [string]$_.Exception.Message
            })
    }

    try {
        $validation = Test-DccBackupChainManifest -Manifest $dccManifest
    }
    catch {
        return [pscustomobject]([ordered]@{
                status = 'blocked'
                errorCodes = @('dcc_backup_manifest_validation_error')
                message = [string]$_.Exception.Message
            })
    }

    $errorCodes = @()
    foreach ($error in @($validation.errors)) {
        if ($null -ne $error -and $null -ne $error.PSObject.Properties['code']) {
            $errorCodes += [string]$error.code
        }
    }

    return [pscustomobject]([ordered]@{
            status = [string]$validation.status
            errorCodes = @($errorCodes)
            message = if ($errorCodes.Count -gt 0) { $errorCodes -join ', ' } else { 'passed' }
        })
}

function New-BackupOpsOperatorBlockedMessage {
    param(
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    return "原因：$Reason`n建议动作：$Action"
}

function Merge-BackupOpsDockerRequest {
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

function New-BackupOpsDockerException {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
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

function Get-BackupDockerFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code = 'INTBK-5002'
    )

    if (-not $Request.ContainsKey($Name)) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message "Missing Docker request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message "Docker request field '$Name' cannot be empty.")
    }

    return [string]$value
}

function Get-BackupOpsConfigValueSafe {
    param(
        [Parameter(Mandatory)]
        [object]$InputObject,
        [Parameter(Mandatory)]
        [string[]]$Path
    )

    $current = $InputObject
    foreach ($segment in $Path) {
        if ($null -eq $current) {
            return $null
        }

        if ($current -is [System.Collections.IDictionary]) {
            if (-not $current.Contains($segment)) {
                return $null
            }
            $current = $current[$segment]
            continue
        }

        $property = $current.PSObject.Properties[$segment]
        if ($null -eq $property) {
            return $null
        }

        $current = $property.Value
    }

    return $current
}

function Get-BackupOpsRequiredConfigValue {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string[]]$Path,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    $value = Get-BackupOpsConfigValueSafe -InputObject $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
    }

    return $value
}

function ConvertTo-BackupBashSingleQuotedString {
    param(
        [Parameter(Mandatory)]
        [string]$Value
    )

    return "'" + ($Value -replace "'", "'""'""'") + "'"
}

function Get-BackupOpsRootPath {
    return (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
}

function Get-BackupOpsTempPath {
    param(
        [Parameter(Mandatory)]
        [string[]]$Segments
    )

    $path = Join-Path (Get-BackupOpsRootPath) 'tmp'
    foreach ($segment in $Segments) {
        if (-not [string]::IsNullOrWhiteSpace($segment)) {
            $path = Join-Path $path $segment
        }
    }

    [void][System.IO.Directory]::CreateDirectory($path)
    return $path
}

function Get-BackupOpsRemoteParentPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $trimmed = $Path.TrimEnd('/')
    $index = $trimmed.LastIndexOf('/')
    if ($index -lt 1) {
        return '/'
    }

    return $trimmed.Substring(0, $index)
}

function Get-BackupOpsDotEnvValue {
    param(
        [Parameter(Mandatory)]
        [string[]]$Lines,
        [Parameter(Mandatory)]
        [string]$Key
    )

    foreach ($line in $Lines) {
        if ($line -like "$Key=*") {
            return $line.Substring($Key.Length + 1)
        }
    }

    return ''
}

function Set-BackupOpsDotEnvValue {
    param(
        [Parameter(Mandatory)]
        [string[]]$Lines,
        [Parameter(Mandatory)]
        [string]$Key,
        [Parameter(Mandatory)]
        [string]$Value
    )

    $updated = New-Object System.Collections.Generic.List[string]
    $replaced = $false
    foreach ($line in $Lines) {
        if ($line -like "$Key=*") {
            $updated.Add("$Key=$Value")
            $replaced = $true
        }
        else {
            $updated.Add($line)
        }
    }

    if (-not $replaced) {
        $updated.Add("$Key=$Value")
    }

    return $updated.ToArray()
}

function Save-BackupOpsDotEnvFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [string[]]$Lines
    )

    $content = ($Lines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($Path, $content, $script:BackupOpsUtf8NoBom)
}

function Get-BackupOpsRuntimeFileMap {
    param(
        [Parameter(Mandatory)]
        [string]$AppDir
    )

    $runtimeDir = $AppDir.TrimEnd('/')
    return [pscustomobject]([ordered]@{
            AppDir = $runtimeDir
            ComposeFile = "$runtimeDir/docker-compose.yml"
            EnvFile = "$runtimeDir/.env"
        })
}

function New-BackupOpsSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string[]]$HostPath,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$HostReason,
        [Parameter(Mandatory)]
        [string]$HostAction
    )

    return @{
        Host = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path $HostPath -Code $Code -Reason $HostReason -Action $HostAction)
        User = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('ssh', 'user') -Code $Code -Reason '缺少 SSH 操作用户配置。' -Action '请在 secrets 描述文件中补齐 ssh.user 后再重试。')
        KeyPath = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('auth', 'sshKeyPath') -Code $Code -Reason '缺少 SSH 私钥路径配置。' -Action '请在操作机 secrets 文件中配置 auth.sshKeyPath，并确保私钥文件存在。')
        Port = if ($Config.ssh.PSObject.Properties['port']) { [int]$Config.ssh.port } else { 22 }
        KnownHostsPath = if ($Config.auth.PSObject.Properties['knownHostsPath']) { [string]$Config.auth.knownHostsPath } else { '' }
    }
}

function Get-BackupOpsProductionSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code = 'INTBK-5002'
    )

    return New-BackupOpsSshRequest -Config $Config -HostPath @('servers', 'production', 'host') -Code $Code -HostReason '缺少正式服务器地址配置。' -HostAction '请在 runtime 配置中补齐 servers.production.host 后再重试。'
}

function Get-BackupOpsTestSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code = 'INTBK-7001'
    )

    return New-BackupOpsSshRequest -Config $Config -HostPath @('servers', 'test', 'host') -Code $Code -HostReason '缺少测试服务器地址配置。' -HostAction '请在 runtime 配置中补齐 servers.test.host 后再重试。'
}

function Get-BackupOpsRuntimeEnvLines {
    param(
        [Parameter(Mandatory)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory)]
        [string]$EnvFile,
        [ValidateSet('INTBK-5001', 'INTBK-5002', 'INTBK-5003', 'INTBK-7001', 'INTBK-7002')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$MissingReason,
        [Parameter(Mandatory)]
        [string]$MissingAction
    )

    Import-BackupOpsSshDependency
    $command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $EnvFile)
    try {
        $result = Invoke-BackupSshCommand -Request ($SshRequest + @{
                Command = $command
                TimeoutSeconds = 60
            })
    }
    catch {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason $MissingReason -Action $MissingAction))
    }

    $lines = @($result.output -split "`r?`n")
    if (@($lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count -eq 0) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason $MissingReason -Action $MissingAction))
    }

    return $lines
}

function Get-BackupOpsRequiredRuntimePort {
    param(
        [Parameter(Mandatory)]
        [string[]]$EnvLines,
        [Parameter(Mandatory)]
        [string]$Key,
        [ValidateSet('INTBK-5003', 'INTBK-7002')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    $value = Get-BackupOpsDotEnvValue -Lines $EnvLines -Key $Key
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
    }

    $parsed = 0
    if (-not [int]::TryParse($value, [ref]$parsed)) {
        throw (New-BackupOpsDockerException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "运行时端口配置无效：$Key=$value" -Action '请修正 .env 中的端口配置为整数后再重试。'))
    }

    return $parsed
}

function Get-BackupOpsBackupIdFromArtifactPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [string]$ChildDirectory
    )

    $parts = $Path.Trim('/') -split '/'
    for ($index = 0; $index -lt ($parts.Count - 1); $index++) {
        if ($parts[$index + 1] -eq $ChildDirectory) {
            return $parts[$index]
        }
    }

    return ''
}

function Get-BackupOpsRemotePathExists {
    param(
        [Parameter(Mandatory)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [ValidateSet('file', 'directory')]
        [string]$Kind
    )

    Import-BackupOpsSshDependency
    $flag = if ($Kind -eq 'directory') { '-d' } else { '-f' }
    try {
        Invoke-BackupSshCommand -Request ($SshRequest + @{
                Command = "test $flag {0} && echo EXISTS" -f (ConvertTo-BackupBashSingleQuotedString -Value $Path)
            }) | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Get-BackupOpsRemoteFileText {
    param(
        [Parameter(Mandatory)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory)]
        [string]$Path
    )

    Import-BackupOpsSshDependency
    $command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $Path)
    $result = Invoke-BackupSshCommand -Request ($SshRequest + @{
            Command = $command
        })
    return $result.output
}

function Invoke-BackupOpsRemoteComposeCommand {
    param(
        [Parameter(Mandatory)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory)]
        [string]$AppDir,
        [Parameter(Mandatory)]
        [string]$ComposeCommand,
        [ValidateSet('INTBK-5002', 'INTBK-7001')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    Import-BackupOpsSshDependency
    $command = "cd {0} && docker compose {1}" -f (ConvertTo-BackupBashSingleQuotedString -Value $AppDir), $ComposeCommand
    try {
        return Invoke-BackupSshCommand -Request ($SshRequest + @{ Command = $command })
    }
    catch {
        throw (New-BackupOpsDockerException -Code $Code -Status 'fail' -Message "$FailureMessage $($_.Exception.Message)")
    }
}

function Wait-BackupOpsRemoteHttpOk {
    param(
        [Parameter(Mandatory)]
        [hashtable]$SshRequest,
        [Parameter(Mandatory)]
        [string]$Url,
        [ValidateSet('INTBK-5003', 'INTBK-7002')]
        [string]$Code,
        [int]$TimeoutSeconds = 180
    )

    Import-BackupOpsSshDependency
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ''
    do {
        try {
            $remainingSeconds = [int][Math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)
            if ($remainingSeconds -le 0) {
                break
            }
            $sshTimeoutSeconds = [Math]::Min(15, [Math]::Max(1, $remainingSeconds))
            $curlMaxTimeSeconds = [Math]::Min(10, [Math]::Max(1, $sshTimeoutSeconds - 1))
            $curlConnectTimeoutSeconds = [Math]::Min(5, $curlMaxTimeSeconds)
            $command = "curl --connect-timeout $curlConnectTimeoutSeconds --max-time $curlMaxTimeSeconds -fsS {0} >/dev/null && echo OK" -f (ConvertTo-BackupBashSingleQuotedString -Value $Url)
            $result = Invoke-BackupSshCommand -Request (Merge-BackupOpsDockerRequest -Request $SshRequest -Extra @{
                    Command = $command
                    TimeoutSeconds = $sshTimeoutSeconds
                })
            if ($result.output -match 'OK') {
                return
            }
            $lastError = $result.output
        }
        catch {
            $lastError = $_.Exception.Message
        }

        if ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    throw (New-BackupOpsDockerException -Code $Code -Status 'fail' -Message "健康检查未在 ${TimeoutSeconds} 秒内通过：$Url。最后错误：$lastError")
}

function Wait-BackupOpsLocalHttpOk {
    param(
        [Parameter(Mandatory)]
        [string]$Url,
        [ValidateSet('INTBK-5003', 'INTBK-7002')]
        [string]$Code,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ''
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return
            }
            $lastError = "HTTP $($response.StatusCode)"
        }
        catch {
            $lastError = $_.Exception.Message
        }

        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    throw (New-BackupOpsDockerException -Code $Code -Status 'fail' -Message "操作机访问健康检查未在 ${TimeoutSeconds} 秒内通过：$Url。最后错误：$lastError")
}

function Get-BackupDockerComposeStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $composeFile = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeFile' -Code 'INTBK-5003'
    $appDir = Get-BackupOpsRemoteParentPath -Path $composeFile
    $services = if ($Request.ContainsKey('Services')) { @($Request['Services']) } else { @('backend', 'frontend') }
    $composeCommand = 'ps {0}' -f ($services -join ' ')

    $plan = [pscustomobject]([ordered]@{
            operation = 'docker-compose-status'
            composeFile = $composeFile
            services = $services
            composeCommand = $composeCommand
            commandPreview = "cd $appDir && docker compose $composeCommand"
        })
    if ($PlanOnly) {
        return $plan
    }

    $result = Invoke-BackupOpsRemoteComposeCommand -SshRequest $Request -AppDir $appDir -ComposeCommand $composeCommand -Code 'INTBK-5003' -FailureMessage '读取 docker compose 状态失败。'
    return [pscustomobject]([ordered]@{
            operation = 'docker-compose-status'
            status = 'success'
            code = 'INTBK-0000'
            composeFile = $composeFile
            services = $services
            output = $result.output
        })
}

function Get-BackupDockerImageTag {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $envFile = Get-BackupDockerFieldValue -Request $Request -Name 'EnvFile' -Code 'INTBK-5001'
    $variableName = Get-BackupDockerFieldValue -Request $Request -Name 'ImageTagVariable' -Code 'INTBK-5001'

    $plan = [pscustomobject]([ordered]@{
            operation = 'docker-image-tag'
            envFile = $envFile
            imageTagVariable = $variableName
            commandPreview = "cat $envFile"
        })
    if ($PlanOnly) {
        return $plan
    }

    $lines = Get-BackupOpsRuntimeEnvLines -SshRequest $Request -EnvFile $envFile -Code 'INTBK-5001' -MissingReason "无法读取运行时环境文件：$envFile" -MissingAction '请确认正式环境 runtime/.env 存在且 SSH 账号具备读取权限后再重试。'
    $imageTag = Get-BackupOpsDotEnvValue -Lines $lines -Key $variableName
    if ([string]::IsNullOrWhiteSpace($imageTag)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-5001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "运行时环境文件缺少 $variableName。" -Action '请先确认 .env 中存在 IMAGE_TAG 后再执行回滚或备份。'))
    }

    return [pscustomobject]([ordered]@{
            operation = 'docker-image-tag'
            status = 'success'
            code = 'INTBK-0000'
            envFile = $envFile
            imageTagVariable = $variableName
            imageTag = $imageTag
        })
}

function Invoke-BackupDockerCompose {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $composeFile = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeFile' -Code 'INTBK-5002'
    $composeCommand = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeCommand' -Code 'INTBK-5002'
    $appDir = Get-BackupOpsRemoteParentPath -Path $composeFile

    $plan = [pscustomobject]([ordered]@{
            operation = 'docker-compose-command'
            composeFile = $composeFile
            composeCommand = $composeCommand
            commandPreview = "cd $appDir && docker compose $composeCommand"
        })
    if ($PlanOnly) {
        return $plan
    }

    $result = Invoke-BackupOpsRemoteComposeCommand -SshRequest $Request -AppDir $appDir -ComposeCommand $composeCommand -Code 'INTBK-5002' -FailureMessage '执行 docker compose 命令失败。'
    return [pscustomobject]([ordered]@{
            operation = 'docker-compose-command'
            status = 'success'
            code = 'INTBK-0000'
            composeFile = $composeFile
            composeCommand = $composeCommand
            output = $result.output
        })
}

function Stop-BackupAppServices {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    if (-not $Request.ContainsKey('Services') -or @($Request['Services']).Count -eq 0) {
        throw (New-BackupOpsDockerException -Code 'INTBK-5002' -Status 'blocked' -Message '缺少需要停机的 docker compose 服务名。')
    }

    $composeFile = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeFile' -Code 'INTBK-5002'
    $services = @($Request['Services'])
    return Invoke-BackupDockerCompose -Request (Merge-BackupOpsDockerRequest -Request $Request -Extra @{
            ComposeFile = $composeFile
            ComposeCommand = 'stop {0}' -f ($services -join ' ')
        }) -PlanOnly:$PlanOnly
}

function Start-BackupAppServices {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    if (-not $Request.ContainsKey('Services') -or @($Request['Services']).Count -eq 0) {
        throw (New-BackupOpsDockerException -Code 'INTBK-5002' -Status 'blocked' -Message '缺少需要启动的 docker compose 服务名。')
    }

    $composeFile = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeFile' -Code 'INTBK-5002'
    $services = @($Request['Services'])
    $dependencyFlag = if ($Request.ContainsKey('NoDeps') -and [bool]$Request['NoDeps']) { '--no-deps ' } else { '' }
    return Invoke-BackupDockerCompose -Request (Merge-BackupOpsDockerRequest -Request $Request -Extra @{
            ComposeFile = $composeFile
            ComposeCommand = 'up -d {0}{1}' -f $dependencyFlag, ($services -join ' ')
        }) -PlanOnly:$PlanOnly
}

function Restart-BackupAppServices {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    if (-not $Request.ContainsKey('Services') -or @($Request['Services']).Count -eq 0) {
        throw (New-BackupOpsDockerException -Code 'INTBK-5002' -Status 'blocked' -Message '缺少需要重启的 docker compose 服务名。')
    }

    $composeFile = Get-BackupDockerFieldValue -Request $Request -Name 'ComposeFile' -Code 'INTBK-5002'
    $services = @($Request['Services'])
    return Invoke-BackupDockerCompose -Request (Merge-BackupOpsDockerRequest -Request $Request -Extra @{
            ComposeFile = $composeFile
            ComposeCommand = 'up -d {0}' -f ($services -join ' ')
        }) -PlanOnly:$PlanOnly
}

function Get-BackupOpsCurrentImageTag {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [object]$LogSession = $null
    )

    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5001' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5001'
    $result = Get-BackupDockerImageTag -Request (Merge-BackupOpsDockerRequest -Request $sshRequest -Extra @{
            EnvFile = $runtime.EnvFile
            ImageTagVariable = 'IMAGE_TAG'
        })
    if ($LogSession) {
        Write-BackupOpsLog -Session $LogSession -Message "Detected current production IMAGE_TAG: $($result.imageTag)"
    }

    return [string]$result.imageTag
}

function Get-BackupOpsRollbackTags {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $targetEnvironment = if ($Config.PSObject.Properties['environment'] -and -not [string]::IsNullOrWhiteSpace([string]$Config.environment)) { [string]$Config.environment } else { 'production' }
    $releasePackagesRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', $targetEnvironment, 'releasePackagesRoot') -Code 'INTBK-5001' -Reason "缺少${targetEnvironment}服务器发布包根目录配置 releasePackagesRoot。" -Action "请在 runtime 配置中补齐 servers.$targetEnvironment.releasePackagesRoot 后再执行应用回滚。")
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5001'
    $currentImageTag = Get-BackupOpsCurrentImageTag -Config $Config -LogSession $LogSession
    $findCommand = "find {0} -mindepth 2 -maxdepth 2 -type f -name rollback-compatibility.json | sort -r" -f (ConvertTo-BackupBashSingleQuotedString -Value $releasePackagesRoot)

    Write-BackupOpsLog -Session $LogSession -Message "Scanning rollback IMAGE_TAG candidates from compatible release packages: $releasePackagesRoot"
    $listResult = Invoke-BackupSshCommand -Request ($sshRequest + @{ Command = $findCommand })
    $paths = @($listResult.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $orderedTags = New-Object System.Collections.Generic.List[string]
    $seen = @{}

    foreach ($path in $paths) {
        try {
            $packageDirectory = Split-Path -Parent $path
            $tag = Split-Path -Leaf $packageDirectory
            if ([string]::IsNullOrWhiteSpace($tag)) {
                continue
            }
            if ($tag -eq $currentImageTag) {
                continue
            }
            if ($seen.ContainsKey($tag)) {
                continue
            }
            $compatibility = (Get-BackupOpsRemoteFileText -SshRequest $sshRequest -Path $path) | ConvertFrom-Json
            if (-not $compatibility.PSObject.Properties['status'] -or [string]$compatibility.status -ne 'COMPATIBLE') {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag $tag because rollback-compatibility.json is not COMPATIBLE."
                continue
            }
            if (-not $compatibility.PSObject.Properties['packageDirectoryName'] -or [string]::IsNullOrWhiteSpace([string]$compatibility.packageDirectoryName)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag $tag because rollback-compatibility.json is missing packageDirectoryName."
                continue
            }
            if ([string]$compatibility.packageDirectoryName -ne $tag) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag $tag because rollback-compatibility packageDirectoryName differs."
                continue
            }
            if (-not $compatibility.PSObject.Properties['checkedAt'] -or [string]::IsNullOrWhiteSpace([string]$compatibility.checkedAt)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag $tag because rollback-compatibility.json is missing checkedAt."
                continue
            }
            if (-not $compatibility.PSObject.Properties['summary'] -or [string]::IsNullOrWhiteSpace([string]$compatibility.summary)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag $tag because rollback-compatibility.json is missing summary."
                continue
            }

            $orderedTags.Add($tag)
            $seen[$tag] = $true
        }
        catch {
            Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip rollback tag candidate because rollback-compatibility.json cannot be parsed: $path"
        }
    }

    Write-BackupOpsLog -Session $LogSession -Message "Resolved $($orderedTags.Count) rollback IMAGE_TAG candidate(s)."
    return @($orderedTags.ToArray())
}

function Save-BackupOpsRuntimeEnvBackup {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行应用回滚。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    $snapshotId = Get-Date -Format 'yyyyMMdd_HHmmss'
    $stageDir = Get-BackupOpsTempPath -Segments @('rollback-app', $snapshotId)
    $localEnvPath = Join-Path $stageDir 'runtime.env'

    # 运行时 .env 备份
    Write-BackupOpsLog -Session $LogSession -Message "Backing up production runtime .env from $($runtime.EnvFile) to $localEnvPath."
    Receive-BackupFileOverSsh -Request ($sshRequest + @{
            RemotePath = $runtime.EnvFile
            LocalPath = $localEnvPath
        }) | Out-Null

    return [pscustomobject]([ordered]@{
            SnapshotId = $snapshotId
            BackupPath = $localEnvPath
        })
}

function Set-BackupOpsImageTag {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$ImageTag,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行应用回滚。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    $stageDir = Get-BackupOpsTempPath -Segments @('rollback-app', 'set-image-tag', (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $localEnvPath = Join-Path $stageDir 'runtime.env'

    Receive-BackupFileOverSsh -Request ($sshRequest + @{
            RemotePath = $runtime.EnvFile
            LocalPath = $localEnvPath
        }) | Out-Null

    # 运行时 IMAGE_TAG 更新
    $envLines = [System.IO.File]::ReadAllLines($localEnvPath, $script:BackupOpsUtf8NoBom)
    $updatedLines = Set-BackupOpsDotEnvValue -Lines $envLines -Key 'IMAGE_TAG' -Value $ImageTag
    Save-BackupOpsDotEnvFile -Path $localEnvPath -Lines $updatedLines

    Write-BackupOpsLog -Session $LogSession -Message "Updating production runtime IMAGE_TAG to $ImageTag via $($runtime.EnvFile)."
    Send-BackupFileOverSsh -Request ($sshRequest + @{
            LocalPath = $localEnvPath
            RemotePath = $runtime.EnvFile
        }) | Out-Null

    return [pscustomobject]([ordered]@{
            imageTag = $ImageTag
            envFile = $runtime.EnvFile
        })
}

function Restart-BackupOpsFrontendBackend {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行应用回滚。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    # backend/frontend 重启流程
    Write-BackupOpsLog -Session $LogSession -Message 'Restarting backend/frontend with docker compose up -d backend frontend.'

    return Restart-BackupAppServices -Request (Merge-BackupOpsDockerRequest -Request $sshRequest -Extra @{
            ComposeFile = $runtime.ComposeFile
            Services = @('backend', 'frontend')
        })
}

function Test-BackupOpsFrontendBackendHealth {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5003'
    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5003' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行健康检查。'))
    $envLines = Get-BackupOpsRuntimeEnvLines -SshRequest $sshRequest -EnvFile $runtime.EnvFile -Code 'INTBK-5003' -MissingReason "无法读取运行时环境文件：$($runtime.EnvFile)" -MissingAction '请确认正式环境 runtime/.env 存在且 SSH 账号具备读取权限后再执行健康检查。'
    $backendPort = Get-BackupOpsRequiredRuntimePort -EnvLines $envLines -Key 'BACKEND_HOST_PORT' -Code 'INTBK-5003' -Reason '正式环境 .env 缺少 BACKEND_HOST_PORT。' -Action '请补齐后端端口配置后再执行健康检查。'
    $frontendPort = Get-BackupOpsRequiredRuntimePort -EnvLines $envLines -Key 'FRONTEND_HOST_PORT' -Code 'INTBK-5003' -Reason '正式环境 .env 缺少 FRONTEND_HOST_PORT。' -Action '请补齐前端端口配置后再执行健康检查。'
    $productionHost = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'host') -Code 'INTBK-5003' -Reason '缺少正式服务器地址配置。' -Action '请在 runtime 配置中补齐 servers.production.host 后再执行健康检查。')

    $remoteBackendUrl = "http://127.0.0.1:$backendPort/actuator/health"
    $remoteFrontendUrl = "http://127.0.0.1:$frontendPort/"
    $localBackendUrl = "http://${productionHost}:$backendPort/actuator/health"
    $localFrontendUrl = "http://${productionHost}:$frontendPort/"

    Write-BackupOpsLog -Session $LogSession -Message "Running backend health check: $remoteBackendUrl"
    Wait-BackupOpsRemoteHttpOk -SshRequest $sshRequest -Url $remoteBackendUrl -Code 'INTBK-5003'
    Write-BackupOpsLog -Session $LogSession -Message "Running frontend health check: $remoteFrontendUrl"
    Wait-BackupOpsRemoteHttpOk -SshRequest $sshRequest -Url $remoteFrontendUrl -Code 'INTBK-5003'
    Write-BackupOpsLog -Session $LogSession -Message "Running operator-side backend health check: $localBackendUrl"
    Wait-BackupOpsLocalHttpOk -Url $localBackendUrl -Code 'INTBK-5003'
    Write-BackupOpsLog -Session $LogSession -Message "Running operator-side frontend health check: $localFrontendUrl"
    Wait-BackupOpsLocalHttpOk -Url $localFrontendUrl -Code 'INTBK-5003'

    return [pscustomobject]([ordered]@{
            status = 'success'
            code = 'INTBK-0000'
            backendUrl = $localBackendUrl
            frontendUrl = $localFrontendUrl
        })
}

function Get-BackupOpsRestoreCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession,
        [string]$SelectedBackupId = '',
        [ValidateSet('restore', 'rehearsal')]
        [string]$Purpose = 'restore'
    )

    Import-BackupOpsSshDependency
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-5002' -Reason '缺少测试服务器备份点根目录配置。' -Action '请在 runtime 配置中补齐 servers.test.backupPointsRoot 后再执行恢复。')
    $databaseName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-5002' -Reason '缺少 MySQL 数据库名配置。' -Action '请在 runtime 配置中补齐 backup.mysqlDatabase 后再执行恢复。')
    $bucket = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('backup', 'objectBucket') -Code 'INTBK-5002' -Reason '缺少对象桶配置。' -Action '请在 runtime 配置中补齐 backup.objectBucket 后再执行恢复。')
    $sshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-5002'
    $selectedBackupIdValue = ''
    if (-not [string]::IsNullOrWhiteSpace($SelectedBackupId)) {
        $selectedBackupIdValue = $SelectedBackupId.Trim()
        if ($selectedBackupIdValue -notmatch '^\d{8}-\d{6}$') {
            throw (New-BackupOpsDockerException -Code 'INTBK-5002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "SelectedBackupId 格式无效：$selectedBackupIdValue。" -Action '请从运行控制台恢复点候选中重新选择一个有效备份点。'))
        }
    }

    if ([string]::IsNullOrWhiteSpace($selectedBackupIdValue)) {
        $findCommand = "find {0} -mindepth 1 -maxdepth 1 -regextype posix-extended -type d -regex '.*/[0-9]{{8}}-[0-9]{{6}}$' | sort -r" -f (ConvertTo-BackupBashSingleQuotedString -Value $backupPointsRoot)
        Write-BackupOpsLog -Session $LogSession -Message "Scanning restorable backup candidates under $backupPointsRoot."
        $listResult = Invoke-BackupSshCommand -Request ($sshRequest + @{ Command = $findCommand })
        $backupDirectories = @($listResult.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    } else {
        $selectedBackupDirectory = $backupPointsRoot.TrimEnd('/') + '/' + $selectedBackupIdValue
        Write-BackupOpsLog -Session $LogSession -Message "Resolving selected restore candidate $selectedBackupIdValue under $backupPointsRoot."
        $backupDirectories = @($selectedBackupDirectory)
    }
    $candidates = New-Object System.Collections.Generic.List[object]

    foreach ($backupDirectory in $backupDirectories) {
        $backupId = Split-Path -Leaf $backupDirectory
        $mysqlDumpPath = "$backupDirectory/mysql/$databaseName.sql.gz"
        $objectInventoryPath = "$backupDirectory/objects/manifest-object-inventory.json"
        $imageTagPath = "$backupDirectory/deploy/image-tag.txt"
        $manifestPath = "$backupDirectory/manifest/manifest.json"
        $dccBackupManifestPath = "$backupDirectory/manifest/dcc-backup-manifest.json"
        $checksumsPath = "$backupDirectory/manifest/checksums.txt"

        $hasMysqlDump = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $mysqlDumpPath -Kind 'file'
        $hasObjectInventory = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $objectInventoryPath -Kind 'file'
        $hasImageTag = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $imageTagPath -Kind 'file'
        $hasManifest = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $manifestPath -Kind 'file'
        $hasDccBackupManifest = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $dccBackupManifestPath -Kind 'file'
        $hasChecksums = Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $checksumsPath -Kind 'file'

        if (-not ($hasMysqlDump -and $hasObjectInventory -and $hasImageTag -and $hasManifest -and $hasDccBackupManifest -and $hasChecksums)) {
            Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because required artifacts are incomplete."
            continue
        }

        $imageTag = (Get-BackupOpsRemoteFileText -SshRequest $sshRequest -Path $imageTagPath).Trim()
        $backupType = 'scheduled'
        $status = 'success'
        $completedAt = $backupId
        $recoverySetRedisPolicy = ''
        $recoverySetConfigurationManifestPath = ''
        $recoverySetConfigurationComposePath = ''
        $recoverySetChecksumsSha256 = ''
        $rehearsalStatus = ''
        $lastRehearsedAt = ''
        $backupStrategyMode = ''
        $mysqlBackupMode = ''
        $dccBackupManifestRelativePath = ''

        try {
            $manifestObject = (Get-BackupOpsRemoteFileText -SshRequest $sshRequest -Path $manifestPath) | ConvertFrom-Json
            if ($manifestObject.PSObject.Properties['backupType']) {
                $backupType = [string]$manifestObject.backupType
            }
            if ($manifestObject.PSObject.Properties['status']) {
                $status = [string]$manifestObject.status
            }
            if ($manifestObject.PSObject.Properties['time'] -and $manifestObject.time.PSObject.Properties['completedAt']) {
                $completedAt = [string]$manifestObject.time.completedAt
            }
            if ($manifestObject.PSObject.Properties['deploy'] -and $manifestObject.deploy.PSObject.Properties['imageTag'] -and -not [string]::IsNullOrWhiteSpace([string]$manifestObject.deploy.imageTag)) {
                $imageTag = [string]$manifestObject.deploy.imageTag
            }
            $manifestTargetEnvironment = if ($manifestObject.PSObject.Properties['targetEnvironment']) { [string]$manifestObject.targetEnvironment } else { '' }
            $manifestTargetHost = if ($manifestObject.PSObject.Properties['targetHost']) { [string]$manifestObject.targetHost } else { '' }
            if ($manifestTargetEnvironment -ne 'test' -or $manifestTargetHost -ne '172.30.30.58') {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest target proof is missing or invalid."
                continue
            }
            if (-not $manifestObject.PSObject.Properties['backupStrategy'] -or $null -eq $manifestObject.backupStrategy) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest backupStrategy is missing."
                continue
            }
            $backupStrategyMode = if ($manifestObject.backupStrategy.PSObject.Properties['mode']) { [string]$manifestObject.backupStrategy.mode } else { '' }
            $mysqlBackupMode = if ($manifestObject.backupStrategy.PSObject.Properties['mysqlBackupMode']) { [string]$manifestObject.backupStrategy.mysqlBackupMode } else { '' }
            if ([string]::IsNullOrWhiteSpace($backupStrategyMode) -or [string]::IsNullOrWhiteSpace($mysqlBackupMode)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest backupStrategy.mode or backupStrategy.mysqlBackupMode is missing."
                continue
            }
            if (-not $manifestObject.PSObject.Properties['recoverySet'] -or $null -eq $manifestObject.recoverySet) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest recoverySet is missing."
                continue
            }
            if (-not $manifestObject.recoverySet.PSObject.Properties['status'] -or [string]$manifestObject.recoverySet.status -ne 'COMPLETE') {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because recoverySet.status is not COMPLETE."
                continue
            }
            if ($manifestObject.recoverySet.PSObject.Properties['id'] -and [string]$manifestObject.recoverySet.id -ne $backupId) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because recoverySet.id differs from backup directory."
                continue
            }
            if ($manifestObject.recoverySet.PSObject.Properties['program'] -and $manifestObject.recoverySet.program.PSObject.Properties['imageTag'] -and -not [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.program.imageTag)) {
                $imageTag = [string]$manifestObject.recoverySet.program.imageTag
            }
            if (-not $manifestObject.recoverySet.PSObject.Properties['checksums'] -or -not $manifestObject.recoverySet.checksums.PSObject.Properties['sha256'] -or [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.checksums.sha256)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because recoverySet.checksums.sha256 is missing."
                continue
            }
            $recoverySetChecksumsSha256 = [string]$manifestObject.recoverySet.checksums.sha256
            if (-not $manifestObject.recoverySet.PSObject.Properties['dcc'] -or $null -eq $manifestObject.recoverySet.dcc -or -not $manifestObject.recoverySet.dcc.PSObject.Properties['manifestPath'] -or [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.dcc.manifestPath)) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because recoverySet.dcc.manifestPath is missing."
                continue
            }
            $dccBackupManifestRelativePath = [string]$manifestObject.recoverySet.dcc.manifestPath
            if ($dccBackupManifestRelativePath -ne 'manifest/dcc-backup-manifest.json') {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because recoverySet.dcc.manifestPath must be manifest/dcc-backup-manifest.json."
                continue
            }
            if ($manifestObject.recoverySet.PSObject.Properties['redis'] -and $null -ne $manifestObject.recoverySet.redis -and $manifestObject.recoverySet.redis.PSObject.Properties['policy']) {
                $recoverySetRedisPolicy = [string]$manifestObject.recoverySet.redis.policy
            }
            if ($manifestObject.recoverySet.PSObject.Properties['configuration'] -and $null -ne $manifestObject.recoverySet.configuration) {
                if ($manifestObject.recoverySet.configuration.PSObject.Properties['manifestPath']) {
                    $recoverySetConfigurationManifestPath = [string]$manifestObject.recoverySet.configuration.manifestPath
                }
                if ($manifestObject.recoverySet.configuration.PSObject.Properties['composePath']) {
                    $recoverySetConfigurationComposePath = [string]$manifestObject.recoverySet.configuration.composePath
                }
            }
            if (-not $manifestObject.PSObject.Properties['validation'] -or $null -eq $manifestObject.validation) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest validation metadata is missing."
                continue
            }
            if (-not $manifestObject.validation.mysqlDumpCreated -or -not $manifestObject.validation.objectBackupCreated -or -not $manifestObject.validation.checksumsGenerated) {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest validation flags are incomplete."
                continue
            }
            $rehearsalStatus = if ($manifestObject.validation.PSObject.Properties['rehearsalStatus']) { [string]$manifestObject.validation.rehearsalStatus } else { '' }
            $lastRehearsedAt = if ($manifestObject.validation.PSObject.Properties['lastRehearsedAt']) { [string]$manifestObject.validation.lastRehearsedAt } else { '' }
            if ($Purpose -eq 'restore') {
                if (@('PASSED', 'passed', 'pass') -notcontains $rehearsalStatus -or [string]::IsNullOrWhiteSpace($lastRehearsedAt)) {
                    Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before restore-data."
                    continue
                }
            } else {
                if ($rehearsalStatus -eq 'pending-review') {
                    Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because rehearsalStatus is pending-review."
                    continue
                }
            }
            $dccManifestValidation = Test-BackupOpsRemoteDccBackupManifestContract -SshRequest $sshRequest -Path $dccBackupManifestPath
            if ($dccManifestValidation.status -ne 'passed') {
                Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because DCC backup manifest validation failed: $($dccManifestValidation.message)."
                continue
            }
        }
        catch {
            Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest.json cannot be parsed."
            continue
        }

        if ($status -ne 'success') {
            Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Skip backup candidate $backupId because manifest status is $status."
            continue
        }

        $candidates.Add([pscustomobject]([ordered]@{
                    backupId = $backupId
                    backupType = $backupType
                    status = $status
                    imageTag = $imageTag
                    redisPolicy = $recoverySetRedisPolicy
                    configurationManifestPath = $recoverySetConfigurationManifestPath
                    configurationComposePath = $recoverySetConfigurationComposePath
                    checksumsSha256 = $recoverySetChecksumsSha256
                    rehearsalStatus = $rehearsalStatus
                    lastRehearsedAt = $lastRehearsedAt
                    backupStrategyMode = $backupStrategyMode
                    mysqlBackupMode = $mysqlBackupMode
                    dccBackupManifestPath = $dccBackupManifestRelativePath
                    completedAt = $completedAt
                }))
    }

    Write-BackupOpsLog -Session $LogSession -Message "Resolved $($candidates.Count) restorable backup candidate(s)."
    return @($candidates.ToArray())
}

function New-BackupOpsPreRestoreSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行数据恢复。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    $snapshotId = "{0}_pre-restore" -f (Get-Date -Format 'yyyyMMdd_HHmmss')
    $snapshotDir = Get-BackupOpsTempPath -Segments @('restore-data', $BackupId, 'pre-restore', $snapshotId)
    $envBackupPath = Join-Path $snapshotDir 'runtime.env'
    $composeBackupPath = Join-Path $snapshotDir 'docker-compose.yml'
    $metadataPath = Join-Path $snapshotDir 'snapshot.json'

    Write-BackupOpsLog -Session $LogSession -Message "Creating pre-restore runtime snapshot $snapshotId for backup point $BackupId."
    Receive-BackupFileOverSsh -Request ($sshRequest + @{
            RemotePath = $runtime.EnvFile
            LocalPath = $envBackupPath
        }) | Out-Null
    Receive-BackupFileOverSsh -Request ($sshRequest + @{
            RemotePath = $runtime.ComposeFile
            LocalPath = $composeBackupPath
        }) | Out-Null

    $snapshotMetadata = [pscustomobject]([ordered]@{
            snapshotId = $snapshotId
            backupId = $BackupId
            createdAt = [System.DateTimeOffset]::Now.ToString('o')
            runtimeEnv = $envBackupPath
            composeFile = $composeBackupPath
        })
    [System.IO.File]::WriteAllText($metadataPath, ($snapshotMetadata | ConvertTo-Json -Depth 4), $script:BackupOpsUtf8NoBom)

    return [pscustomobject]([ordered]@{
            SnapshotId = $snapshotId
            SnapshotPath = $snapshotDir
        })
}

function Stop-BackupOpsFrontendBackend {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行数据恢复。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    # backend/frontend 停机流程
    Write-BackupOpsLog -Session $LogSession -Message 'Stopping backend/frontend with docker compose stop backend frontend.'

    return Stop-BackupAppServices -Request (Merge-BackupOpsDockerRequest -Request $sshRequest -Extra @{
            ComposeFile = $runtime.ComposeFile
            Services = @('backend', 'frontend')
        })
}

function Restore-BackupOpsDependentAssets {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Write-BackupOpsLog -Session $LogSession -Message "No extra dependent assets are configured for backup point $BackupId. Skip this step."
    return [pscustomobject]([ordered]@{
            status = 'success'
            code = 'INTBK-0000'
            message = '当前未配置需要额外恢复的附属资产，已跳过。'
        })
}

function Start-BackupOpsFrontendBackend {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $runtime = Get-BackupOpsRuntimeFileMap -AppDir ([string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-5002' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行恢复。'))
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-5002'
    Write-BackupOpsLog -Session $LogSession -Message 'Starting backend/frontend with docker compose up -d --no-deps backend frontend.'

    return Start-BackupAppServices -Request (Merge-BackupOpsDockerRequest -Request $sshRequest -Extra @{
            ComposeFile = $runtime.ComposeFile
            Services = @('backend', 'frontend')
            NoDeps = $true
        })
}

function Test-BackupOpsRestoreValidation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    # 恢复后的健康检查与抽样验证
    Write-BackupOpsLog -Session $LogSession -Message "Running restore validation for backup point $BackupId."
    $health = Test-BackupOpsFrontendBackendHealth -Config $Config -LogSession $LogSession
    return [pscustomobject]([ordered]@{
            status = 'success'
            code = 'INTBK-0000'
            backupId = $BackupId
            backendUrl = $health.backendUrl
            frontendUrl = $health.frontendUrl
        })
}

function New-BackupOpsRehearsalMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [string]$ImageTag
    )

    $runtimeNamePrefix = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsal', 'runtimeNamePrefix') -Code 'INTBK-7001' -Reason '缺少 rehearsal.runtimeNamePrefix 配置。' -Action '请先补齐恢复演练运行时名称前缀后再执行演练。')
    $runtimeRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'rehearsalRoot') -Code 'INTBK-7001' -Reason '缺少测试演练运行目录配置。' -Action '请先补齐 servers.test.rehearsalRoot 后再执行演练。')
    $bucket = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsal', 'bucket') -Code 'INTBK-7001' -Reason '缺少 rehearsal.bucket 配置。' -Action '请先补齐演练对象桶配置后再执行演练。')
    $backendPort = [int](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'rehearsalBackendPort') -Code 'INTBK-7001' -Reason '缺少测试演练后端端口配置。' -Action '请先补齐 servers.test.rehearsalBackendPort 后再执行演练。')
    $frontendPort = [int](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'rehearsalFrontendPort') -Code 'INTBK-7001' -Reason '缺少测试演练前端端口配置。' -Action '请先补齐 servers.test.rehearsalFrontendPort 后再执行演练。')
    $fileConfigId = [int](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsal', 'validation', 'fileConfigId') -Code 'INTBK-7001' -Reason '缺少 rehearsal.validation.fileConfigId 配置。' -Action '请先补齐演练文件配置编号后再执行演练。')
    $tenantId = [int](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsal', 'validation', 'tenantId') -Code 'INTBK-7001' -Reason '缺少 rehearsal.validation.tenantId 配置。' -Action '请先补齐演练租户编号后再执行演练。')
    $tenantName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsalAuth', 'tenantName') -Code 'INTBK-7001' -Reason '缺少 rehearsalAuth.tenantName 配置。' -Action '请先在 secrets 文件中补齐演练登录租户名后再执行演练。')
    $username = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsalAuth', 'username') -Code 'INTBK-7001' -Reason '缺少 rehearsalAuth.username 配置。' -Action '请先在 secrets 文件中补齐演练登录用户名后再执行演练。')
    $password = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('rehearsalAuth', 'password') -Code 'INTBK-7001' -Reason '缺少 rehearsalAuth.password 配置。' -Action '请先在 secrets 文件中补齐演练登录密码后再执行演练。')
    $projectName = $runtimeNamePrefix

    return [pscustomobject]([ordered]@{
            BackupId       = $BackupId
            ImageTag       = $ImageTag
            RuntimeRoot    = $runtimeRoot.TrimEnd('/')
            RuntimeMap     = Get-BackupOpsRuntimeFileMap -AppDir $runtimeRoot
            RuntimeName    = $projectName
            Bucket         = $bucket
            BackendPort    = $backendPort
            FrontendPort   = $frontendPort
            TenantId       = $tenantId
            TenantName     = $tenantName
            Username       = $username
            Password       = $password
            FileConfigId   = $fileConfigId
            ContainerMap   = [ordered]@{
                'intruoyi-mysql'    = "$projectName-mysql"
                'intruoyi-redis'    = "$projectName-redis"
                'intruoyi-backend'  = "$projectName-backend"
                'intruoyi-frontend' = "$projectName-frontend"
            }
        })
}

function Convert-BackupOpsComposeToRehearsalRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComposeText,
        [Parameter(Mandatory = $true)]
        [object]$Metadata
    )

    $lines = $ComposeText -split "`r?`n"
    $updated = New-Object System.Collections.Generic.List[string]
    $hasProjectName = $false

    foreach ($line in $lines) {
        if ($line -match '^\s*name\s*:') {
            $updated.Add("name: $($Metadata.RuntimeName)")
            $hasProjectName = $true
            continue
        }
        if ($line -match '^(\s*)container_name:\s*(\S+)\s*$') {
            $indent = $matches[1]
            $originalName = $matches[2]
            $targetName = if ($Metadata.ContainerMap.Contains($originalName)) {
                [string]$Metadata.ContainerMap[$originalName]
            }
            else {
                "$($Metadata.RuntimeName)-$originalName"
            }
            $updated.Add("$indent" + "container_name: $targetName")
            continue
        }

        $updated.Add($line)
    }

    $body = $updated -join "`n"
    if (-not $hasProjectName) {
        return "name: $($Metadata.RuntimeName)`n`n$body"
    }

    return $body
}

function New-BackupOpsRehearsalConfig {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Metadata
    )

    $clone = ($Config | ConvertTo-Json -Depth 12) | ConvertFrom-Json
    $clone.environment = 'rehearsal'
    $clone.servers.production.host = $Config.servers.test.host
    $clone.servers.production.appDir = $Metadata.RuntimeRoot
    $clone.servers.production.tmpRoot = "$($Metadata.RuntimeRoot)/tmp"
    $clone.backup.objectBucket = $Metadata.Bucket
    $clone.containers.mysql = $Metadata.ContainerMap['intruoyi-mysql']
    $clone.containers.redis = $Metadata.ContainerMap['intruoyi-redis']
    $clone.containers.backend = $Metadata.ContainerMap['intruoyi-backend']
    $clone.containers.frontend = $Metadata.ContainerMap['intruoyi-frontend']
    return $clone
}

function Ensure-BackupOpsRehearsalImageAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $testSshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-7001'
    $productionSshRequest = Get-BackupOpsProductionSshRequest -Config $Config -Code 'INTBK-7001'
    $backendImage = "intruoyi-backend:$($Metadata.ImageTag)"
    $frontendImage = "intruoyi-frontend:$($Metadata.ImageTag)"
    $inspectCommand = "docker image inspect {0} >/dev/null 2>&1 && docker image inspect {1} >/dev/null 2>&1 && echo READY" -f $backendImage, $frontendImage

    try {
        $inspectResult = Invoke-BackupSshCommand -Request ($testSshRequest + @{ Command = $inspectCommand })
        if ($inspectResult.output -match 'READY') {
            Write-BackupOpsLog -Session $LogSession -Message "Rehearsal IMAGE_TAG $($Metadata.ImageTag) already exists on test server."
            return
        }
    }
    catch {
        Write-BackupOpsLog -Session $LogSession -Level 'WARN' -Message "Rehearsal IMAGE_TAG $($Metadata.ImageTag) not found on test server. Preparing transfer from production."
    }

    $prodTmpRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'tmpRoot') -Code 'INTBK-7001' -Reason '缺少正式环境临时目录配置。' -Action '请先补齐 servers.production.tmpRoot 后再执行恢复演练。')
    $remoteProdDir = ($prodTmpRoot.TrimEnd('/')) + '/rehearsal-images'
    $remoteProdArchive = "$remoteProdDir/$($Metadata.ImageTag).tar.gz"
    $localArchiveDir = Get-BackupOpsTempPath -Segments @('rehearsal', $Metadata.BackupId, 'images')
    $localArchivePath = Join-Path $localArchiveDir "$($Metadata.ImageTag).tar.gz"
    $remoteTestArchiveDir = "$($Metadata.RuntimeRoot)/_images"
    $remoteTestArchive = "$remoteTestArchiveDir/$($Metadata.ImageTag).tar.gz"

    Write-BackupOpsLog -Session $LogSession -Message "Saving IMAGE_TAG $($Metadata.ImageTag) from production to $remoteProdArchive."
    Invoke-BackupSshCommand -Request ($productionSshRequest + @{
            Command = "mkdir -p {0} && docker image inspect {1} >/dev/null 2>&1 && docker image inspect {2} >/dev/null 2>&1 && docker save {1} {2} | gzip -c > {3}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteProdDir), $backendImage, $frontendImage, (ConvertTo-BackupBashSingleQuotedString -Value $remoteProdArchive)
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message "Downloading rehearsal image archive to operator machine: $localArchivePath"
    Receive-BackupFileOverSsh -Request ($productionSshRequest + @{
            RemotePath = $remoteProdArchive
            LocalPath = $localArchivePath
        }) | Out-Null

    Invoke-BackupSshCommand -Request ($testSshRequest + @{
            Command = "mkdir -p {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteTestArchiveDir)
        }) | Out-Null
    Write-BackupOpsLog -Session $LogSession -Message "Uploading rehearsal image archive to test server: $remoteTestArchive"
    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localArchivePath
            RemotePath = $remoteTestArchive
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message "Loading rehearsal IMAGE_TAG $($Metadata.ImageTag) on test server."
    Invoke-BackupSshCommand -Request ($testSshRequest + @{
            Command = "gunzip -c {0} | docker load && rm -f {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteTestArchive)
        }) | Out-Null
    Invoke-BackupSshCommand -Request ($productionSshRequest + @{
            Command = "rm -f {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteProdArchive)
        }) | Out-Null
}

function Initialize-BackupOpsRehearsalRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    if (-not $Metadata.RuntimeRoot.StartsWith('/backup/int-ruoyi/rehearsal/', [System.StringComparison]::Ordinal)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "测试演练目录不在预期范围内：$($Metadata.RuntimeRoot)" -Action '请先修正 servers.test.rehearsalRoot 到 /backup/int-ruoyi/rehearsal/* 范围后再执行演练。'))
    }

    $testSshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-7001'
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-7001' -Reason '缺少测试服务器备份点根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行恢复演练。')
    $remoteComposePath = "$($backupPointsRoot.TrimEnd('/'))/$($Metadata.BackupId)/deploy/docker-compose.yml"
    $remoteEnvPath = "$($backupPointsRoot.TrimEnd('/'))/$($Metadata.BackupId)/deploy/runtime.env"
    $localStageDir = Get-BackupOpsTempPath -Segments @('rehearsal', $Metadata.BackupId, 'runtime')
    $localComposePath = Join-Path $localStageDir 'docker-compose.yml'
    $localEnvPath = Join-Path $localStageDir '.env'

    Receive-BackupFileOverSsh -Request ($testSshRequest + @{
            RemotePath = $remoteComposePath
            LocalPath = $localComposePath
        }) | Out-Null
    Receive-BackupFileOverSsh -Request ($testSshRequest + @{
            RemotePath = $remoteEnvPath
            LocalPath = $localEnvPath
        }) | Out-Null

    $envLines = [System.IO.File]::ReadAllLines($localEnvPath, $script:BackupOpsUtf8NoBom)
    $envLines = Set-BackupOpsDotEnvValue -Lines $envLines -Key 'IMAGE_TAG' -Value $Metadata.ImageTag
    $envLines = Set-BackupOpsDotEnvValue -Lines $envLines -Key 'SERVER_HOST' -Value ([string]$Config.servers.test.host)
    $envLines = Set-BackupOpsDotEnvValue -Lines $envLines -Key 'BACKEND_HOST_PORT' -Value ([string]$Metadata.BackendPort)
    $envLines = Set-BackupOpsDotEnvValue -Lines $envLines -Key 'FRONTEND_HOST_PORT' -Value ([string]$Metadata.FrontendPort)
    Save-BackupOpsDotEnvFile -Path $localEnvPath -Lines $envLines

    $composeText = [System.IO.File]::ReadAllText($localComposePath, $script:BackupOpsUtf8NoBom)
    $composeText = Convert-BackupOpsComposeToRehearsalRuntime -ComposeText $composeText -Metadata $Metadata
    [System.IO.File]::WriteAllText($localComposePath, $composeText, $script:BackupOpsUtf8NoBom)

    Write-BackupOpsLog -Session $LogSession -Message "Preparing rehearsal runtime root on test server: $($Metadata.RuntimeRoot)"
    Invoke-BackupSshCommand -Request ($testSshRequest + @{
            Command = "rm -rf {0} && mkdir -p {0} {1}" -f (ConvertTo-BackupBashSingleQuotedString -Value $Metadata.RuntimeRoot), (ConvertTo-BackupBashSingleQuotedString -Value "$($Metadata.RuntimeRoot)/tmp")
        }) | Out-Null
    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localComposePath
            RemotePath = $Metadata.RuntimeMap.ComposeFile
        }) | Out-Null
    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localEnvPath
            RemotePath = $Metadata.RuntimeMap.EnvFile
        }) | Out-Null
}

function Wait-BackupOpsMySqlReady {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Request,
        [Parameter(Mandatory = $true)]
        [object]$LogSession,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = ''
    $containerName = [string]$Request['ContainerName']
    do {
        try {
            $healthResult = Invoke-BackupSshCommand -Request (Merge-BackupOpsDockerRequest -Request $Request -Extra @{
                    Command = "docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing-healthcheck{{end}}' $containerName"
                    TimeoutSeconds = 30
                })
            $healthStatus = ([string]$healthResult.output).Trim()
            if ($healthStatus -ne 'healthy') {
                $lastError = "Docker health status for container '$containerName' is '$healthStatus'."
                Start-Sleep -Seconds 3
                continue
            }

            Test-BackupMySqlConnectivity -Request $Request | Out-Null
            return
        }
        catch {
            $lastError = $_.Exception.Message
        }

        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    Write-BackupOpsLog -Session $LogSession -Level 'ERROR' -Message "MySQL readiness check did not pass within ${TimeoutSeconds}s. Last error: $lastError"
    throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'fail' -Message "演练 MySQL 未在 ${TimeoutSeconds} 秒内准备就绪。最后错误：$lastError")
}

function Update-BackupOpsRehearsalFileMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [object]$RehearsalConfig,
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $RehearsalConfig -Code 'INTBK-7001'
    $envLines = Get-BackupOpsRuntimeEnvLines -SshRequest $sshRequest -EnvFile $Metadata.RuntimeMap.EnvFile -Code 'INTBK-7001' -MissingReason "无法读取演练运行时环境文件：$($Metadata.RuntimeMap.EnvFile)" -MissingAction '请先确认测试演练环境 .env 已生成后再继续。'
    $rootPassword = Get-BackupOpsDotEnvValue -Lines $envLines -Key 'MYSQL_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($rootPassword)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason '演练运行时 .env 缺少 MYSQL_ROOT_PASSWORD。' -Action '请先确认备份点 deploy/runtime.env 完整，再执行恢复演练。'))
    }

    $domain = "http://$($RehearsalConfig.servers.test.host):9000/$($Metadata.Bucket)"
    $sqlLocalPath = Join-Path (Get-BackupOpsTempPath -Segments @('rehearsal', $Metadata.BackupId, 'sql')) 'rehearsal-post-import.sql'
    $sqlRemotePath = "$($Metadata.RuntimeRoot)/tmp/rehearsal-post-import.sql"
    $sql = @"
UPDATE infra_file_config
SET config = REPLACE(
    REPLACE(
        REPLACE(config, '""bucket"":""yudao""', '""bucket"":""$($Metadata.Bucket)""'),
        '""domain"":""http:///yudao""',
        '""domain"":""$domain""'
    ),
    '""domain"":""http://host.docker.internal:9000/yudao""',
    '""domain"":""$domain""'
)
WHERE id = $($Metadata.FileConfigId);

UPDATE infra_file
SET url = CONCAT('$domain/', path)
WHERE config_id = $($Metadata.FileConfigId);
"@
    [System.IO.File]::WriteAllText($sqlLocalPath, $sql, $script:BackupOpsUtf8NoBom)
    Send-BackupFileOverSsh -Request ($sshRequest + @{
            LocalPath = $sqlLocalPath
            RemotePath = $sqlRemotePath
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message "Patching rehearsal file metadata to bucket $($Metadata.Bucket) and domain $domain."
    Invoke-BackupSshCommand -Request ($sshRequest + @{
            Command = "cat {0} | docker exec -i {1} mysql -uroot -p{2} ruoyi-vue-pro" -f (ConvertTo-BackupBashSingleQuotedString -Value $sqlRemotePath), $Metadata.ContainerMap['intruoyi-mysql'], (ConvertTo-BackupBashSingleQuotedString -Value $rootPassword)
        }) | Out-Null
}

function Get-BackupOpsRehearsalMinioCredential {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [ValidateSet('MINIO_ROOT_USER', 'MINIO_ROOT_PASSWORD')]
        [string]$Key
    )

    Import-BackupOpsSshDependency
    $minioContainer = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('containers', 'minio') -Code 'INTBK-7001' -Reason '缺少演练 MinIO 容器配置。' -Action '请先补齐 containers.minio 后再执行恢复演练。')
    $sshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-7001'
    $result = Invoke-BackupSshCommand -Request ($sshRequest + @{
            Command = "docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $minioContainer"
        })
    foreach ($line in ($result.output -split "`r?`n")) {
        if ($line -like "$Key=*") {
            return $line.Substring($Key.Length + 1)
        }
    }

    throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "无法读取演练 MinIO 凭据 $Key。" -Action '请先确认测试服务器 MinIO 容器存在且允许读取环境变量后再执行演练。'))
}

function Restore-BackupOpsRehearsalObjectBucket {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $rehearsalConfig = New-BackupOpsRehearsalConfig -Config $Config -Metadata $Metadata
    Write-BackupOpsLog -Session $LogSession -Message "Restoring rehearsal object bucket $($Metadata.Bucket) from incremental inventory for backup $($Metadata.BackupId)."
    return Restore-BackupOpsObjectBucket -Config $rehearsalConfig -BackupId ([string]$Metadata.BackupId) -LogSession $LogSession
}

function Get-BackupOpsRehearsalSampleFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [object]$RehearsalConfig,
        [Parameter(Mandatory = $true)]
        [object]$Metadata
    )

    $sampleFilePath = [string](Get-BackupOpsRequiredConfigValue -Config $RehearsalConfig -Path @('rehearsal', 'validation', 'sampleFilePath') -Code 'INTBK-7002' -Reason '缺少 rehearsal.validation.sampleFilePath 配置。' -Action '请先补齐演练文件抽样路径后再执行演练校验。')
    if ([string]::IsNullOrWhiteSpace($sampleFilePath)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason '演练样本文件路径为空。' -Action '请先补齐 rehearsal.validation.sampleFilePath 后再执行演练校验。'))
    }

    return $sampleFilePath.Trim()
}

function Invoke-BackupOpsRehearsalLoginValidation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [string]$BackendBaseUrl,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $body = @{
        username = $Metadata.Username
        password = $Metadata.Password
    } | ConvertTo-Json
    Write-BackupOpsLog -Session $LogSession -Message "Running rehearsal login check for tenant $($Metadata.TenantName) against $BackendBaseUrl/admin-api/system/auth/login"
    $response = Invoke-RestMethod -Uri "$BackendBaseUrl/admin-api/system/auth/login" -Method Post -Headers @{ 'tenant-id' = [string]$Metadata.TenantId } -ContentType 'application/json' -Body $body
    if ($null -eq $response -or $response.code -ne 0 -or $null -eq $response.data -or [string]::IsNullOrWhiteSpace([string]$response.data.accessToken)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7002' -Status 'fail' -Message '演练环境登录校验失败，未获取到 accessToken。')
    }

    $token = [string]$response.data.accessToken
    $permission = Invoke-RestMethod -Uri "$BackendBaseUrl/admin-api/system/auth/get-permission-info" -Method Get -Headers @{ Authorization = "Bearer $token" }
    if ($null -eq $permission -or $permission.code -ne 0) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7002' -Status 'fail' -Message '演练环境关键接口校验失败，权限信息接口未返回成功。')
    }

    return [pscustomobject]([ordered]@{
            accessToken = $token
            permissionInfo = $permission.data
        })
}

function Invoke-BackupOpsRehearsalSampleDownloadValidation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Metadata,
        [Parameter(Mandatory = $true)]
        [string]$BackendBaseUrl,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$SampleFilePath,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $encodedSegments = @($SampleFilePath -split '/' | ForEach-Object { [uri]::EscapeDataString($_) })
    $encodedPath = $encodedSegments -join '/'
    $downloadUrl = "$BackendBaseUrl/admin-api/infra/file/$($Metadata.FileConfigId)/get/$encodedPath"
    Write-BackupOpsLog -Session $LogSession -Message "Running rehearsal sample file download check: $downloadUrl"
    $response = Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -Method Head -Headers @{ Authorization = "Bearer $AccessToken" } -TimeoutSec 30
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7002' -Status 'fail' -Message "演练环境文件抽样下载失败：HTTP $($response.StatusCode)")
    }

    return [pscustomobject]([ordered]@{
            sampleFilePath = $SampleFilePath
            downloadUrl = $downloadUrl
        })
}

function Get-BackupOpsLatestBackup {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $candidates = @(Get-BackupOpsRestoreCandidates -Config $Config -LogSession $LogSession -Purpose 'rehearsal')
    if ($candidates.Count -eq 0) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason '测试服务器备份仓库中没有任何可用于恢复演练的完整备份点。' -Action '请先完成一次成功备份，并确认 mysql/objects/deploy/manifest 产物完整后再执行演练。'))
    }

    return $candidates[0]
}

function Get-BackupOpsRehearsalCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-7001' -Reason '缺少测试服务器备份点根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行演练。')
    $databaseName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-7001' -Reason '缺少 MySQL 数据库名配置。' -Action '请先补齐 backup.mysqlDatabase 后再执行演练。')
    $sshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-7001'
    $backupDirectory = "$($backupPointsRoot.TrimEnd('/'))/$BackupId"
    $mysqlDumpPath = "$backupDirectory/mysql/$databaseName.sql.gz"
    $objectInventoryPath = "$backupDirectory/objects/manifest-object-inventory.json"
    $imageTagPath = "$backupDirectory/deploy/image-tag.txt"
    $manifestPath = "$backupDirectory/manifest/manifest.json"
    $dccBackupManifestPath = "$backupDirectory/manifest/dcc-backup-manifest.json"
    $checksumsPath = "$backupDirectory/manifest/checksums.txt"

    foreach ($item in @(
            @{ Path = $mysqlDumpPath; Kind = 'file' },
            @{ Path = $objectInventoryPath; Kind = 'file' },
            @{ Path = $imageTagPath; Kind = 'file' },
            @{ Path = $manifestPath; Kind = 'file' },
            @{ Path = $dccBackupManifestPath; Kind = 'file' },
            @{ Path = $checksumsPath; Kind = 'file' }
        )) {
        if (-not (Get-BackupOpsRemotePathExists -SshRequest $sshRequest -Path $item.Path -Kind $item.Kind)) {
            throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点不存在或不完整：$BackupId" -Action '请先确认测试服务器备份仓库中存在完整恢复点后再执行恢复演练。'))
        }
    }

    try {
        $manifestObject = (Get-BackupOpsRemoteFileText -SshRequest $sshRequest -Path $manifestPath) | ConvertFrom-Json
    }
    catch {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 manifest 无法解析：$BackupId" -Action '请先修复 manifest.json 后再执行恢复演练。'))
    }

    if (-not $manifestObject.PSObject.Properties['validation'] -or $null -eq $manifestObject.validation) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少 validation 元数据：$BackupId" -Action '请先补齐 manifest.validation 后再执行恢复演练。'))
    }
    if (-not $manifestObject.validation.mysqlDumpCreated -or -not $manifestObject.validation.objectBackupCreated -or -not $manifestObject.validation.checksumsGenerated) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 validation 标记不完整：$BackupId" -Action '请先修复 manifest.validation 标记后再执行恢复演练。'))
    }
    $manifestTargetEnvironment = if ($manifestObject.PSObject.Properties['targetEnvironment']) { [string]$manifestObject.targetEnvironment } else { '' }
    $manifestTargetHost = if ($manifestObject.PSObject.Properties['targetHost']) { [string]$manifestObject.targetHost } else { '' }
    if ($manifestTargetEnvironment -ne 'test' -or $manifestTargetHost -ne '172.30.30.58') {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少测试服目标证明：$BackupId。" -Action '请确认 manifest.targetEnvironment=test 且 targetHost=172.30.30.58 后再执行恢复演练。'))
    }
    if (-not $manifestObject.PSObject.Properties['backupStrategy'] -or $null -eq $manifestObject.backupStrategy) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少 backupStrategy：$BackupId。" -Action '请重新生成包含 backupStrategy.mode 和 backupStrategy.mysqlBackupMode 的完整备份 manifest 后再执行恢复演练。'))
    }
    $backupStrategyMode = if ($manifestObject.backupStrategy.PSObject.Properties['mode']) { [string]$manifestObject.backupStrategy.mode } else { '' }
    $mysqlBackupMode = if ($manifestObject.backupStrategy.PSObject.Properties['mysqlBackupMode']) { [string]$manifestObject.backupStrategy.mysqlBackupMode } else { '' }
    if ([string]::IsNullOrWhiteSpace($backupStrategyMode) -or [string]::IsNullOrWhiteSpace($mysqlBackupMode)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 backupStrategy.mode 或 backupStrategy.mysqlBackupMode 缺失：$BackupId。" -Action '请重新生成完整备份策略契约后再执行恢复演练。'))
    }
    if (-not $manifestObject.PSObject.Properties['recoverySet'] -or $null -eq $manifestObject.recoverySet) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少 recoverySet：$BackupId。" -Action '请先补齐 manifest.recoverySet 后再执行恢复演练。'))
    }
    if (-not $manifestObject.recoverySet.PSObject.Properties['status'] -or [string]$manifestObject.recoverySet.status -ne 'COMPLETE') {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 recoverySet.status 不是 COMPLETE：$BackupId。" -Action '请重新生成完整备份点或修复 recoverySet 后再执行恢复演练。'))
    }
    if ($manifestObject.recoverySet.PSObject.Properties['id'] -and [string]$manifestObject.recoverySet.id -ne $BackupId) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 recoverySet.id 与备份目录不一致：$BackupId。" -Action '请确认备份点目录与 manifest.recoverySet.id 一致后再执行恢复演练。'))
    }
    if (-not $manifestObject.recoverySet.PSObject.Properties['checksums'] -or -not $manifestObject.recoverySet.checksums.PSObject.Properties['sha256'] -or [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.checksums.sha256)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少 recoverySet.checksums.sha256：$BackupId。" -Action '请先生成完整 checksums 并写入 recoverySet 后再执行恢复演练。'))
    }
    if (-not $manifestObject.recoverySet.PSObject.Properties['dcc'] -or $null -eq $manifestObject.recoverySet.dcc -or -not $manifestObject.recoverySet.dcc.PSObject.Properties['manifestPath'] -or [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.dcc.manifestPath)) {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点缺少 recoverySet.dcc.manifestPath：$BackupId。" -Action '请重新生成包含 manifest/dcc-backup-manifest.json 的完整 DCC 备份 manifest 后再执行恢复演练。'))
    }
    $dccBackupManifestRelativePath = [string]$manifestObject.recoverySet.dcc.manifestPath
    if ($dccBackupManifestRelativePath -ne 'manifest/dcc-backup-manifest.json') {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 recoverySet.dcc.manifestPath 必须是 manifest/dcc-backup-manifest.json：$BackupId。" -Action '请重新生成标准 DCC 备份 manifest 后再执行恢复演练。'))
    }
    $dccManifestValidation = Test-BackupOpsRemoteDccBackupManifestContract -SshRequest $sshRequest -Path $dccBackupManifestPath
    if ($dccManifestValidation.status -ne 'passed') {
        throw (New-BackupOpsDockerException -Code 'INTBK-7001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "指定的演练恢复点 DCC 备份链校验失败：$BackupId，错误码：$($dccManifestValidation.message)。" -Action '请修复 DCC full baseline、增量链、对象 inventory 和删除/作废/归档/权限事件后再执行恢复演练。'))
    }
    $imageTag = if ($manifestObject.recoverySet.PSObject.Properties['program'] -and $manifestObject.recoverySet.program.PSObject.Properties['imageTag'] -and -not [string]::IsNullOrWhiteSpace([string]$manifestObject.recoverySet.program.imageTag)) {
        [string]$manifestObject.recoverySet.program.imageTag
    } elseif ($manifestObject.PSObject.Properties['deploy'] -and $manifestObject.deploy.PSObject.Properties['imageTag']) {
        [string]$manifestObject.deploy.imageTag
    } else {
        (Get-BackupOpsRemoteFileText -SshRequest $sshRequest -Path $imageTagPath).Trim()
    }

    return [pscustomobject]([ordered]@{
            backupId = $BackupId
            backupType = if ($manifestObject.PSObject.Properties['backupType']) { [string]$manifestObject.backupType } else { 'scheduled' }
            status = if ($manifestObject.PSObject.Properties['status']) { [string]$manifestObject.status } else { 'success' }
            imageTag = $imageTag
            backupStrategyMode = $backupStrategyMode
            mysqlBackupMode = $mysqlBackupMode
            dccBackupManifestPath = $dccBackupManifestRelativePath
            completedAt = if ($manifestObject.PSObject.Properties['time'] -and $manifestObject.time.PSObject.Properties['completedAt']) { [string]$manifestObject.time.completedAt } else { $BackupId }
            rehearsalStatus = if ($manifestObject.validation.PSObject.Properties['rehearsalStatus']) { [string]$manifestObject.validation.rehearsalStatus } else { 'unverified' }
        })
}

function Set-BackupOpsRehearsalVerificationState {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [ValidateSet('PASSED', 'pending-review')]
        [string]$RehearsalStatus,
        [string]$Note = '',
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $testSshRequest = Get-BackupOpsTestSshRequest -Config $Config -Code 'INTBK-7001'
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-7001' -Reason '缺少测试服务器备份点根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行演练。')
    $remoteManifestPath = "$($backupPointsRoot.TrimEnd('/'))/$BackupId/manifest/manifest.json"
    $localManifestDir = Get-BackupOpsTempPath -Segments @('rehearsal', $BackupId, 'manifest')
    $localManifestPath = Join-Path $localManifestDir 'manifest.json'

    Receive-BackupFileOverSsh -Request ($testSshRequest + @{
            RemotePath = $remoteManifestPath
            LocalPath = $localManifestPath
        }) | Out-Null

    $manifest = [System.IO.File]::ReadAllText($localManifestPath, $script:BackupOpsUtf8NoBom) | ConvertFrom-Json
    if (-not $manifest.PSObject.Properties['validation'] -or $null -eq $manifest.validation) {
        $manifest | Add-Member -NotePropertyName validation -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $manifest.validation | Add-Member -NotePropertyName rehearsalStatus -NotePropertyValue $RehearsalStatus -Force
    $manifest.validation | Add-Member -NotePropertyName lastRehearsedAt -NotePropertyValue ([System.DateTimeOffset]::Now.ToString('o')) -Force

    if ($RehearsalStatus -eq 'pending-review') {
        $manifest.status = 'blocked'
        $notes = if ($manifest.PSObject.Properties['notes'] -and $null -ne $manifest.notes) { @($manifest.notes) } else { @() }
        if (-not [string]::IsNullOrWhiteSpace($Note)) {
            $notes += $Note
        }
        $manifest | Add-Member -NotePropertyName notes -NotePropertyValue $notes -Force
    }
    elseif ($manifest.status -eq 'blocked') {
        $manifest.status = 'success'
    }

    [System.IO.File]::WriteAllText($localManifestPath, ($manifest | ConvertTo-Json -Depth 10), $script:BackupOpsUtf8NoBom)
    Send-BackupFileOverSsh -Request ($testSshRequest + @{
            LocalPath = $localManifestPath
            RemotePath = $remoteManifestPath
        }) | Out-Null
    Write-BackupOpsLog -Session $LogSession -Message "Updated rehearsal verification state for backup $BackupId to $RehearsalStatus."
}

function Restore-BackupOpsRehearsalRuntime {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $candidate = Get-BackupOpsRehearsalCandidate -Config $Config -BackupId $BackupId -LogSession $LogSession
    $metadata = New-BackupOpsRehearsalMetadata -Config $Config -BackupId $BackupId -ImageTag ([string]$candidate.imageTag)
    $rehearsalConfig = New-BackupOpsRehearsalConfig -Config $Config -Metadata $metadata
    $rehearsalSshRequest = Get-BackupOpsProductionSshRequest -Config $rehearsalConfig -Code 'INTBK-7001'

    Ensure-BackupOpsRehearsalImageAvailable -Config $Config -Metadata $metadata -LogSession $LogSession
    Initialize-BackupOpsRehearsalRuntime -Config $Config -Metadata $metadata -LogSession $LogSession

    Write-BackupOpsLog -Session $LogSession -Message "Resetting rehearsal runtime stack under $($metadata.RuntimeRoot)."
    Invoke-BackupSshCommand -Request ($rehearsalSshRequest + @{
            Command = "cd {0} && docker compose down -v --remove-orphans || true" -f (ConvertTo-BackupBashSingleQuotedString -Value $metadata.RuntimeRoot)
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message 'Starting rehearsal mysql/redis services.'
    Invoke-BackupDockerCompose -Request (Merge-BackupOpsDockerRequest -Request $rehearsalSshRequest -Extra @{
            ComposeFile = $metadata.RuntimeMap.ComposeFile
            ComposeCommand = 'up -d mysql redis'
        }) | Out-Null

    $envLines = Get-BackupOpsRuntimeEnvLines -SshRequest $rehearsalSshRequest -EnvFile $metadata.RuntimeMap.EnvFile -Code 'INTBK-7001' -MissingReason "无法读取演练运行时环境文件：$($metadata.RuntimeMap.EnvFile)" -MissingAction '请先确认测试演练环境 .env 已生成后再继续。'
    $rootPassword = Get-BackupOpsDotEnvValue -Lines $envLines -Key 'MYSQL_ROOT_PASSWORD'
    Wait-BackupOpsMySqlReady -Request (Merge-BackupOpsDockerRequest -Request $rehearsalSshRequest -Extra @{
            ContainerName = $metadata.ContainerMap['intruoyi-mysql']
            DatabaseName = [string]$Config.backup.mysqlDatabase
            RootPassword = $rootPassword
        }) -LogSession $LogSession

    Import-BackupOpsMySqlDump -Config $rehearsalConfig -BackupId $BackupId -LogSession $LogSession | Out-Null
    Restore-BackupOpsRehearsalObjectBucket -Config $Config -Metadata $metadata -LogSession $LogSession | Out-Null
    Update-BackupOpsRehearsalFileMetadata -RehearsalConfig $rehearsalConfig -Metadata $metadata -LogSession $LogSession
    Start-BackupOpsFrontendBackend -Config $rehearsalConfig -LogSession $LogSession | Out-Null

    return [pscustomobject]([ordered]@{
            status = 'success'
            code = 'INTBK-0000'
            backupId = $BackupId
            imageTag = $metadata.ImageTag
            runtimeRoot = $metadata.RuntimeRoot
        })
}

function Test-BackupOpsRehearsalValidation {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $candidate = Get-BackupOpsRehearsalCandidate -Config $Config -BackupId $BackupId -LogSession $LogSession
    $metadata = New-BackupOpsRehearsalMetadata -Config $Config -BackupId $BackupId -ImageTag ([string]$candidate.imageTag)
    $rehearsalConfig = New-BackupOpsRehearsalConfig -Config $Config -Metadata $metadata
    $health = Test-BackupOpsFrontendBackendHealth -Config $rehearsalConfig -LogSession $LogSession
    $backendBaseUrl = ("http://{0}:{1}" -f [string]$Config.servers.test.host, $metadata.BackendPort)
    $login = Invoke-BackupOpsRehearsalLoginValidation -Metadata $metadata -BackendBaseUrl $backendBaseUrl -LogSession $LogSession
    $sampleFilePath = Get-BackupOpsRehearsalSampleFilePath -RehearsalConfig $rehearsalConfig -Metadata $metadata
    $sample = Invoke-BackupOpsRehearsalSampleDownloadValidation -Metadata $metadata -BackendBaseUrl $backendBaseUrl -AccessToken $login.accessToken -SampleFilePath $sampleFilePath -LogSession $LogSession

    return [pscustomobject]([ordered]@{
            status = 'success'
            code = 'INTBK-0000'
            backupId = $BackupId
            backendUrl = $health.backendUrl
            frontendUrl = $health.frontendUrl
            checks = [ordered]@{
                backendHealth = 'pass'
                frontendHttp200 = 'pass'
                loginReachable = 'pass'
                fileDownloadSample = 'pass'
            }
            sampleFilePath = $sample.sampleFilePath
            sampleDownloadUrl = $sample.downloadUrl
        })
}

Export-ModuleMember -Function Get-BackupDockerComposeStatus, Get-BackupDockerImageTag, Invoke-BackupDockerCompose, Stop-BackupAppServices, Start-BackupAppServices, Restart-BackupAppServices, Get-BackupOpsCurrentImageTag, Get-BackupOpsRollbackTags, Save-BackupOpsRuntimeEnvBackup, Set-BackupOpsImageTag, Restart-BackupOpsFrontendBackend, Test-BackupOpsFrontendBackendHealth, Get-BackupOpsRestoreCandidates, New-BackupOpsPreRestoreSnapshot, Stop-BackupOpsFrontendBackend, Restore-BackupOpsDependentAssets, Start-BackupOpsFrontendBackend, Test-BackupOpsRestoreValidation, Get-BackupOpsLatestBackup, Get-BackupOpsRehearsalCandidate, Set-BackupOpsRehearsalVerificationState, Restore-BackupOpsRehearsalRuntime, Test-BackupOpsRehearsalValidation
