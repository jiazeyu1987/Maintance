Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function New-BackupOpsObjectException {
    param(
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Message
    )

    $exception = [System.InvalidOperationException]::new($Message)
    $exception.Data['BackupOpsCode'] = $Code
    $exception.Data['BackupOpsStatus'] = 'blocked'
    return $exception
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

function Get-BackupObjectFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Request.ContainsKey($Name)) {
        throw [System.ArgumentException]::new("INTBK-4001: missing object request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw [System.ArgumentException]::new("INTBK-4001: object request field '$Name' cannot be empty.")
    }

    return $value
}

function New-BackupObjectBlockedPlan {
    param(
        [Parameter(Mandatory)]
        [string]$Operation,
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Message
    )

    return [pscustomobject]([ordered]@{
            operation = $Operation
            status    = 'blocked'
            code      = $Code
            message   = $Message
            bucket    = $Request['Bucket']
            target    = $Request['TargetPath']
            phase     = 'phase-1'
        })
}

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

function Get-BackupOpsObjectConfigValueSafe {
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

function Get-BackupOpsRequiredObjectConfigValue {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string[]]$Path,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    $value = Get-BackupOpsObjectConfigValueSafe -InputObject $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw (New-BackupOpsObjectException -Code $Code -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
    }

    return $value
}

function Get-BackupOpsObjectSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [ValidateSet('production', 'test')]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    return @{
        Host = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('servers', $Environment, 'host') -Code $Code -Reason $Reason -Action $Action)
        User = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('ssh', 'user') -Code $Code -Reason '缺少 SSH 操作用户配置。' -Action '请先在 secrets 文件中补齐 ssh.user 后再重试。')
        KeyPath = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('auth', 'sshKeyPath') -Code $Code -Reason '缺少 SSH 私钥路径配置。' -Action '请先在 secrets 文件中补齐 auth.sshKeyPath，并确保私钥文件存在。')
        Port = if ($Config.ssh.PSObject.Properties['port']) { [int]$Config.ssh.port } else { 22 }
        KnownHostsPath = if ($Config.auth.PSObject.Properties['knownHostsPath']) { [string]$Config.auth.knownHostsPath } else { '' }
    }
}

function ConvertTo-BackupBashSingleQuotedString {
    param(
        [Parameter(Mandatory)]
        [string]$Value
    )

    return "'" + ($Value -replace "'", "'""'""'") + "'"
}

function Assert-BackupOpsObjectBackupPackageRoot {
    param(
        [Parameter(Mandatory)]
        [string]$BackupPointsRoot
    )

    $normalized = $BackupPointsRoot.TrimEnd('/').Replace('\', '/')
    if ($normalized -ne '/mnt/nas/Backup/BackupPackage') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复备份根目录不是受保护的测试服 BackupPackage：$BackupPointsRoot" -Action '请确认 servers.test.backupPointsRoot 固定为 /mnt/nas/Backup/BackupPackage 后再执行对象恢复。'))
    }
}

function Assert-BackupOpsObjectRestoreTestHost {
    param(
        [Parameter(Mandatory)]
        [string]$Host,
        [Parameter(Mandatory)]
        [string]$Label
    )

    if ($Host -eq '172.30.30.57') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复${Label}禁止指向正式服务器 172.30.30.57。" -Action '停止恢复，修正 TargetEnvironment 和运行配置，恢复目标只能是测试服务器 172.30.30.58。'))
    }
    if ($Host -ne '172.30.30.58') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复${Label}无法证明为测试服务器 172.30.30.58：$Host" -Action '请显式使用 targetEnvironment=test，并确认目标主机和备份仓库主机均为 172.30.30.58。'))
    }
}

function Assert-BackupOpsObjectBackupId {
    param(
        [Parameter(Mandatory)]
        [string]$BackupId
    )

    if ($BackupId -notmatch '^\d{8}-\d{6}$') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复备份点 ID 非法：$BackupId" -Action '请只选择 BackupPackage 下 yyyyMMdd-HHmmss 格式的合法备份点。'))
    }
}

function Assert-BackupOpsObjectRestoreStageRoot {
    param(
        [Parameter(Mandatory)]
        [string]$RemoteTempRoot
    )

    $normalized = $RemoteTempRoot.TrimEnd('/').Replace('\', '/')
    if (-not $normalized.StartsWith('/mnt/nas/Backup/BackupPackage/.restore-stage/', [System.StringComparison]::Ordinal)) {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复 stage 目录不在测试服 BackupPackage 受控 restore stage 下：$RemoteTempRoot" -Action '请使用 /mnt/nas/Backup/BackupPackage/.restore-stage/<backupId>/objects 作为对象恢复 stage。'))
    }
    if ($normalized -match '(^|/)\.\.($|/)') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复 stage 目录包含非法上级目录引用：$RemoteTempRoot" -Action '请只使用 BackupPackage 下合法 restore stage 路径。'))
    }
    if ($normalized -like '*/ReleasePackage/*') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复 stage 指向 ReleasePackage：$RemoteTempRoot" -Action 'ReleasePackage 只保存程序发布包，数据恢复 stage 只能位于 BackupPackage。'))
    }
}

function Get-BackupOpsRemoteContainerEnvValue {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [ValidateSet('production', 'test')]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$ContainerName,
        [Parameter(Mandatory)]
        [string]$Key,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    Import-BackupOpsSshDependency
    $sshRequest = Get-BackupOpsObjectSshRequest -Config $Config -Environment $Environment -Code $Code -Reason $Reason -Action $Action
    $command = "docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' $ContainerName"
    $result = Invoke-BackupSshCommand -Request ($sshRequest + @{ Command = $command })
    foreach ($line in ($result.output -split "`r?`n")) {
        if ($line -like "$Key=*") {
            return $line.Substring($Key.Length + 1)
        }
    }

    throw (New-BackupOpsObjectException -Code $Code -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
}

function Get-BackupOpsMinioCredentials {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [ValidateSet('production', 'test')]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Code
    )

    $containerName = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('containers', 'minio') -Code $Code -Reason '缺少 MinIO 容器名配置。' -Action '请先在配置文件中补齐 containers.minio 后再重试。')
    $reason = if ($Environment -eq 'production') { '无法读取正式环境 MinIO 凭据。' } else { '无法读取测试环境 MinIO 凭据。' }
    $action = if ($Environment -eq 'production') { '请先确认正式环境 MinIO 容器和凭据来源可读。' } else { '请先确认测试环境 MinIO 容器和凭据来源可读。' }

    $accessKey = Get-BackupOpsRemoteContainerEnvValue -Config $Config -Environment $Environment -ContainerName $containerName -Key 'MINIO_ROOT_USER' -Code $Code -Reason $reason -Action $action
    $secretKey = Get-BackupOpsRemoteContainerEnvValue -Config $Config -Environment $Environment -ContainerName $containerName -Key 'MINIO_ROOT_PASSWORD' -Code $Code -Reason $reason -Action $action

    return [pscustomobject]@{
        ContainerName = $containerName
        AccessKey = $accessKey
        SecretKey = $secretKey
    }
}

function Assert-BackupOpsDockerExecutable {
    if (-not (Get-Command -Name 'docker' -ErrorAction SilentlyContinue)) {
        throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason '当前操作机缺少 docker 命令。' -Action '请先在操作机安装并验证 Docker CLI 后再执行对象备份或恢复。'))
    }
}

function Get-BackupOpsMinioClientImage {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string]$Code
    )

    return [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('tools', 'minioClientImage') -Code $Code -Reason '缺少 MinIO 客户端镜像配置。' -Action '请在配置文件中补齐 tools.minioClientImage 后再执行对象备份或恢复。')
}

function Get-BackupOpsArchiveImage {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string]$Code
    )

    return [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('tools', 'archiveImage') -Code $Code -Reason '缺少对象归档镜像配置。' -Action '请在配置文件中补齐 tools.archiveImage 后再执行对象备份或恢复。')
}

function New-BackupOpsDockerException {
    param(
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action,
        [string]$Detail = ''
    )

    $effectiveReason = $Reason
    if (-not [string]::IsNullOrWhiteSpace($Detail)) {
        $effectiveReason = "$Reason 详细信息：$($Detail.Trim())"
    }
    return New-BackupOpsObjectException -Code $Code -Message (New-BackupOpsOperatorBlockedMessage -Reason $effectiveReason -Action $Action)
}

function ConvertTo-BackupOpsProcessArgument {
    param(
        [AllowEmptyString()]
        [Parameter(Mandatory)]
        [string]$Argument
    )

    if ($Argument.Length -gt 0 -and $Argument -notmatch '[\s"]') {
        return $Argument
    }

    $builder = [System.Text.StringBuilder]::new()
    [void]$builder.Append('"')
    $backslashCount = 0
    foreach ($char in $Argument.ToCharArray()) {
        if ($char -eq '\') {
            $backslashCount++
            continue
        }
        if ($char -eq '"') {
            if ($backslashCount -gt 0) {
                [void]$builder.Append('\' * ($backslashCount * 2))
                $backslashCount = 0
            }
            [void]$builder.Append('\"')
            continue
        }
        if ($backslashCount -gt 0) {
            [void]$builder.Append('\' * $backslashCount)
            $backslashCount = 0
        }
        [void]$builder.Append($char)
    }
    if ($backslashCount -gt 0) {
        [void]$builder.Append('\' * ($backslashCount * 2))
    }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function Invoke-BackupOpsLocalProcessCapture {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$ArgumentList = @()
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = (($ArgumentList | ForEach-Object { ConvertTo-BackupOpsProcessArgument -Argument $_ }) -join ' ')
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()

    return @{
        ExitCode = $process.ExitCode
        StdOut = $stdoutTask.Result
        StdErr = $stderrTask.Result
    }
}

function Invoke-BackupOpsMcShell {
    param(
        [Parameter(Mandatory)]
        [string]$Command,
        [Parameter(Mandatory)]
        [string]$Image,
        [string[]]$VolumeArgs = @()
    )

    $arguments = @('run', '--rm', '--entrypoint', '/bin/sh')
    $arguments += $VolumeArgs
    $arguments += @($Image, '-c', $Command)
    $result = Invoke-BackupOpsDocker -ArgumentList $arguments -Code 'INTBK-4001' -Reason 'MinIO 客户端容器执行失败。' -Action '请确认 Docker、MinIO 客户端镜像和挂载目录可用后再重试。'

    return [pscustomobject]@{
        ExitCode = 0
        Output = (($result.StdOut + "`n" + $result.StdErr).Trim())
        Command = $Command
    }
}

function Invoke-BackupOpsDocker {
    param(
        [Parameter(Mandatory)]
        [string[]]$ArgumentList,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    Assert-BackupOpsDockerExecutable
    $result = Invoke-BackupOpsLocalProcessCapture -FilePath 'docker' -ArgumentList $ArgumentList
    $output = (($result.StdOut + "`n" + $result.StdErr).Trim())
    if ($result.ExitCode -ne 0) {
        throw (New-BackupOpsDockerException -Code $Code -Reason $Reason -Action $Action -Detail $output)
    }
    return $result
}

function Remove-BackupOpsDockerVolumeBestEffort {
    param(
        [Parameter(Mandatory)]
        [string]$VolumeName
    )

    $cleanup = $null
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        $cleanup = Invoke-BackupOpsLocalProcessCapture -FilePath 'docker' -ArgumentList @('volume', 'rm', '-f', $VolumeName)
        if ($cleanup.ExitCode -eq 0) {
            return
        }
        if ($attempt -lt 5) {
            Start-Sleep -Seconds 2
        }
    }

    $detail = (($cleanup.StdOut + "`n" + $cleanup.StdErr).Trim())
    Write-Warning "Docker volume cleanup failed: $VolumeName $detail"
}

function New-BackupObjectSyncPlan {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupObjectFieldValue -Request $Request -Name 'Bucket')
    [void](Get-BackupObjectFieldValue -Request $Request -Name 'TargetPath')

    return [pscustomobject]([ordered]@{
            bucket            = $Request['Bucket']
            targetPath        = $Request['TargetPath']
            sourcePath        = $Request['SourcePath']
            mode              = if ($Request.ContainsKey('Mode')) { $Request['Mode'] } else { 'snapshot' }
            checksumInventory = if ($Request.ContainsKey('ChecksumInventory')) { $Request['ChecksumInventory'] } else { $null }
        })
}

function Test-BackupObjectAccess {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '正式环境' }
    $alias = if ($Request.ContainsKey('Alias') -and -not [string]::IsNullOrWhiteSpace([string]$Request['Alias'])) { [string]$Request['Alias'] } else { 'src' }

    $command = "mc alias set $alias $endpoint $accessKey $secretKey && mc ls $alias/$bucket >/dev/null"
    $plan = [pscustomobject]@{
        operation = 'object-health-check'
        status = 'planned'
        code = 'INTBK-0000'
        bucket = $bucket
        endpoint = $endpoint
        command = $command
    }
    if ($PlanOnly) {
        return $plan
    }

    try {
        $result = Invoke-BackupOpsMcShell -Command $command -Image $clientImage
        return [pscustomobject]@{
            operation = 'object-health-check'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            endpoint = $endpoint
            output = $result.Output
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "无法验证${environmentLabel}对象桶可访问。" -Action "请先确认${environmentLabel} MinIO 地址、容器凭据和操作机 Docker 可用后再执行对象备份。"))
    }
}

function Export-BackupObjectSnapshot {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $syncPlan = New-BackupObjectSyncPlan -Request $Request
    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $targetPath = Get-BackupObjectFieldValue -Request $Request -Name 'TargetPath'
    $archivePath = Get-BackupObjectFieldValue -Request $Request -Name 'ArchivePath'
    $archiveImage = Get-BackupObjectFieldValue -Request $Request -Name 'ArchiveImage'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '正式环境' }

    $command = "mc alias set src $endpoint $accessKey $secretKey && mc ls src/$bucket >/dev/null"
    $plan = [pscustomobject]@{
        operation = 'object-backup'
        status = 'planned'
        code = 'INTBK-0000'
        syncPlan = $syncPlan
        command = $command
        archivePath = $archivePath
    }
    if ($PlanOnly) {
        return $plan
    }

    [void][System.IO.Directory]::CreateDirectory($targetPath)
    $archiveDir = Split-Path -Parent $archivePath
    $archiveFile = Split-Path -Leaf $archivePath
    [void][System.IO.Directory]::CreateDirectory($archiveDir)
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    $volumeSuffix = [System.Text.RegularExpressions.Regex]::Replace(([System.Guid]::NewGuid().ToString('N')), '[^A-Za-z0-9_.-]', '_')
    $volumeName = "intruoyi_backup_objects_$volumeSuffix"
    try {
        Invoke-BackupOpsDocker -ArgumentList @('volume', 'create', $volumeName) -Code 'INTBK-4001' -Reason '无法创建对象备份临时 Docker volume。' -Action '请确认操作机 Docker volume 可用后再重试。' | Out-Null
        $mirrorCommand = "set -eu; rm -rf /objects/$bucket; mkdir -p /objects; $command && mc mirror --overwrite src/$bucket /objects/$bucket"
        Invoke-BackupOpsMcShell -Command $mirrorCommand -Image $clientImage -VolumeArgs @('-v', "${volumeName}:/objects") | Out-Null
        $archiveCommand = "set -eu; test -d /objects/$bucket; tar -cf /backup-out/$archiveFile -C /objects $bucket"
        Invoke-BackupOpsDocker -ArgumentList @(
            'run',
            '--rm',
            '--entrypoint',
            '/bin/sh',
            '-v',
            "${volumeName}:/objects:ro",
            '-v',
            "${archiveDir}:/backup-out",
            $archiveImage,
            '-c',
            $archiveCommand
        ) -Code 'INTBK-4001' -Reason "${environmentLabel}对象桶归档执行失败。" -Action "请先确认操作机 Docker、对象归档镜像和本地归档目录可用后再重试。" | Out-Null
        if (-not (Test-Path -LiteralPath $archivePath)) {
            throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象归档文件未生成：$archivePath" -Action '请确认 Docker volume 到本地归档目录的挂载可写后再重试。'))
        }
        return [pscustomobject]@{
            operation = 'object-backup'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            targetPath = $targetPath
            archivePath = $archivePath
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "${environmentLabel}对象桶备份执行失败。" -Action "请先确认操作机 Docker、${environmentLabel} MinIO 访问和目标目录挂载是否正常后再重试。"))
    } finally {
        Remove-BackupOpsDockerVolumeBestEffort -VolumeName $volumeName
    }
}

function ConvertFrom-BackupOpsRemoteInventoryOutput {
    param(
        [string]$Output
    )

    $items = @()
    foreach ($line in ($Output -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $parts = $line -split "`t"
        if ($parts.Count -lt 4) {
            continue
        }
        $items += [pscustomobject]@{
            path = [string]$parts[0]
            sha256 = [string]$parts[1]
            size = [long]$parts[2]
            lastModified = [string]$parts[3]
            status = 'active'
            repositoryKey = [string]$parts[1]
        }
    }
    return @($items)
}

function ConvertFrom-BackupOpsRemoteObjectMetadataJson {
    param(
        [Parameter(Mandatory)]
        [string]$Output
    )

    $items = [System.Collections.Generic.List[object]]::new()
    foreach ($line in ($Output -split "`r?`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $entry = $line | ConvertFrom-Json
        if ([string]$entry.type -ne 'file' -or [string]::IsNullOrWhiteSpace([string]$entry.key)) {
            continue
        }
        $etag = [string]$entry.etag
        if ([string]::IsNullOrWhiteSpace($etag)) {
            throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason ("对象元数据缺少 etag，无法为对象建立增量仓库键：{0}" -f [string]$entry.key) -Action '请先确认测试环境 MinIO 返回稳定 etag 后再执行增量备份。'))
        }
        $items.Add([pscustomobject]@{
                path = [string]$entry.key
                etag = $etag
                sha256 = $etag
                size = [long]$entry.size
                lastModified = [string]$entry.lastModified
                status = 'active'
                repositoryKey = $etag
            }) | Out-Null
    }
    return @($items)
}

function Get-BackupOpsPreviousManifestObjects {
    param(
        [Parameter(Mandatory)]
        [string]$BackupPointsRoot,
        [Parameter(Mandatory)]
        [string]$CurrentBackupId,
        [Parameter(Mandatory)]
        [hashtable]$SshRequest
    )

    Import-BackupOpsSshDependency
    $listTimeoutSeconds = 300
    $shortReadTimeoutSeconds = 60
    $escapedRoot = ConvertTo-BackupBashSingleQuotedString -Value $BackupPointsRoot
    $listCommand = "find $escapedRoot -mindepth 1 -maxdepth 1 -regextype posix-extended -type d -regex '.*/[0-9]{8}-[0-9]{6}$' | sort -r"
    $listResult = Invoke-BackupSshCommand -Request ($SshRequest + @{
        Command = $listCommand
        TimeoutSeconds = $listTimeoutSeconds
    })
    foreach ($path in @($listResult.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })) {
        if ($path.TrimEnd('/').EndsWith("/$CurrentBackupId")) {
            continue
        }
        $manifestPath = $path.TrimEnd('/') + '/manifest/manifest.json'
        try {
            $manifestText = (Invoke-BackupSshCommand -Request ($SshRequest + @{
                Command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $manifestPath)
                TimeoutSeconds = $shortReadTimeoutSeconds
            })).output
            $manifest = $manifestText | ConvertFrom-Json
            if ($manifest.PSObject.Properties['objects']) {
                return @($manifest.objects)
            }
        } catch {
            continue
        }
    }
    return @()
}

function Merge-BackupOpsObjectInventory {
    param(
        [object[]]$CurrentObjects = @(),
        [object[]]$PreviousObjects = @()
    )

    $previousByPath = @{}
    foreach ($item in @($PreviousObjects)) {
        if ($null -ne $item -and $item.PSObject.Properties['path']) {
            $previousByPath[[string]$item.path] = $item
        }
    }

    $objects = [System.Collections.Generic.List[object]]::new()
    $stats = [ordered]@{
        addedCount = 0
        modifiedCount = 0
        deletedCount = 0
        reusedCount = 0
    }

    foreach ($current in @($CurrentObjects)) {
        $path = [string]$current.path
        $previous = $null
        $changeType = 'added'
        if ($previousByPath.ContainsKey($path)) {
            $previous = $previousByPath[$path]
            $previousByPath.Remove($path)
        }
        if ($null -eq $previous) {
            $stats.addedCount++
            $changeType = 'added'
        } elseif ([string]$previous.status -eq 'deleted') {
            $stats.addedCount++
            $changeType = 'added'
        } elseif ([string]$previous.sha256 -eq [string]$current.sha256 -and [string]$previous.status -ne 'deleted') {
            $stats.reusedCount++
            $changeType = 'reused'
        } else {
            $stats.modifiedCount++
            $changeType = 'modified'
        }
        Add-Member -InputObject $current -MemberType NoteProperty -Name 'changeType' -Value $changeType -Force
        $objects.Add($current) | Out-Null
    }

    foreach ($previous in $previousByPath.Values) {
        if ([string]$previous.status -eq 'deleted') {
            continue
        }
        $stats.deletedCount++
        $objects.Add([pscustomobject]@{
                path = [string]$previous.path
                sha256 = [string]$previous.sha256
                size = if ($previous.PSObject.Properties['size']) { [long]$previous.size } else { 0 }
                lastModified = if ($previous.PSObject.Properties['lastModified']) { [string]$previous.lastModified } else { '' }
                status = 'deleted'
                repositoryKey = if ($previous.PSObject.Properties['repositoryKey']) { [string]$previous.repositoryKey } else { [string]$previous.sha256 }
                changeType = 'deleted'
            }) | Out-Null
    }

    return [pscustomobject]@{
        objects = @($objects | Sort-Object path)
        stats = [pscustomobject]$stats
    }
}

function New-BackupOpsObjectCopyPlan {
    param(
        [Parameter(Mandatory)]
        [object]$Inventory
    )

    $plan = [System.Collections.Generic.List[object]]::new()
    foreach ($item in @($Inventory.objects)) {
        if ($null -eq $item -or [string]$item.status -eq 'deleted') {
            continue
        }
        $changeType = if ($item.PSObject.Properties['changeType']) { [string]$item.changeType } else { '' }
        if ($changeType -in @('added', 'modified')) {
            $plan.Add([pscustomobject]@{
                    path = [string]$item.path
                    repositoryKey = [string]$item.repositoryKey
                }) | Out-Null
        }
    }
    return @($plan)
}

function Write-BackupOpsObjectInventoryMarker {
    param(
        [Parameter(Mandatory)]
        [string]$TargetPath,
        [Parameter(Mandatory)]
        [string]$Bucket,
        [Parameter(Mandatory)]
        [string]$ObjectStoreRoot,
        [Parameter(Mandatory)]
        [object]$Inventory
    )

    [void][System.IO.Directory]::CreateDirectory($TargetPath)
    $markerPath = Join-Path $TargetPath 'manifest-object-inventory.json'
    $marker = [pscustomobject]([ordered]@{
            mode = 'incremental-manifest'
            bucket = $Bucket
            objectStoreRoot = $ObjectStoreRoot
            stats = $Inventory.stats
            objects = @($Inventory.objects)
            createdAt = [System.DateTimeOffset]::Now.ToString('o')
        })
    [System.IO.File]::WriteAllText($markerPath, ($marker | ConvertTo-Json -Depth 8), $script:BackupOpsUtf8NoBom)
    return $markerPath
}

function New-BackupOpsTempScriptPath {
    param(
        [Parameter(Mandatory)]
        [string]$Prefix
    )

    $fileName = '{0}-{1}.sh' -f $Prefix, ([System.Guid]::NewGuid().ToString('N'))
    return Join-Path ([System.IO.Path]::GetTempPath()) $fileName
}

function Write-BackupOpsUtf8LfFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [AllowEmptyCollection()]
        [string[]]$Lines
    )

    $content = if ($null -eq $Lines -or $Lines.Count -eq 0) {
        "`n"
    } else {
        ([string]::Join("`n", $Lines) + "`n")
    }
    [System.IO.File]::WriteAllText($Path, $content, $script:BackupOpsUtf8NoBom)
}

function Export-BackupObjectSnapshotToRemoteNas {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $syncPlan = New-BackupObjectSyncPlan -Request $Request
    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $targetPath = Get-BackupObjectFieldValue -Request $Request -Name 'TargetPath'
    $remotePath = Get-BackupObjectFieldValue -Request $Request -Name 'RemotePath'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $archiveImage = Get-BackupObjectFieldValue -Request $Request -Name 'ArchiveImage'
    if (-not $Request.ContainsKey('SshRequest') -or $null -eq $Request['SshRequest']) {
        throw [System.ArgumentException]::new("INTBK-4001: object request field 'SshRequest' cannot be empty.")
    }
    $sshRequest = [hashtable]$Request['SshRequest']
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '正式环境' }

    $remotePath = $remotePath.TrimEnd('/')
    $remoteBackupRoot = $remotePath.Substring(0, $remotePath.LastIndexOf('/'))
    $backupPointsRoot = $remoteBackupRoot.Substring(0, $remoteBackupRoot.LastIndexOf('/'))
    $objectStoreRoot = $backupPointsRoot + '/object-store'
    $volumeSuffix = [System.Text.RegularExpressions.Regex]::Replace(([System.Guid]::NewGuid().ToString('N')), '[^A-Za-z0-9_.-]', '_')
    $planFileName = 'manifest-object-copy-plan.tsv'
    $copyScriptFileName = 'manifest-object-copy.sh'
    $remoteCopyPlanPath = $remotePath + '/' + $planFileName
    $remoteCopyScriptPath = $remotePath + '/' + $copyScriptFileName
    $remoteCopyPlanDir = $remotePath + ':/backup-point'
    $objectStoreVolumeArg = $objectStoreRoot + ':/object-store'
    $metadataCommand = 'set -eu; mc alias set src "$MC_ENDPOINT" "$MC_ACCESS_KEY" "$MC_SECRET_KEY" >/dev/null; mc ls --recursive --json src/' + $bucket
    $copyCommand = 'set -eu; mc alias set src "$MC_ENDPOINT" "$MC_ACCESS_KEY" "$MC_SECRET_KEY" >/dev/null; mkdir -p /object-store; plan=/backup-point/' + $planFileName + '; if [ ! -s "$plan" ]; then exit 0; fi; while IFS= read -r line; do repo=$(printf ''%s'' "$line" | cut -f1); rel=$(printf ''%s'' "$line" | cut -f2-); [ -n "$repo" ] || continue; if [ -f "/object-store/$repo" ]; then continue; fi; mc cp "src/' + $bucket + '/$rel" "/object-store/$repo"; done < "$plan"'
    $command = "set -eu; mkdir -p {0}; mkdir -p {1}; docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={2} -e MC_ACCESS_KEY={3} -e MC_SECRET_KEY={4} {5} -c {6}; docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={2} -e MC_ACCESS_KEY={3} -e MC_SECRET_KEY={4} -v {7} -v {8} {5} -c {9}" -f `
        (ConvertTo-BackupBashSingleQuotedString -Value $remotePath),
        (ConvertTo-BackupBashSingleQuotedString -Value $objectStoreRoot),
        (ConvertTo-BackupBashSingleQuotedString -Value $endpoint),
        (ConvertTo-BackupBashSingleQuotedString -Value $accessKey),
        (ConvertTo-BackupBashSingleQuotedString -Value $secretKey),
        (ConvertTo-BackupBashSingleQuotedString -Value $clientImage),
        (ConvertTo-BackupBashSingleQuotedString -Value $metadataCommand),
        (ConvertTo-BackupBashSingleQuotedString -Value $remoteCopyPlanDir),
        (ConvertTo-BackupBashSingleQuotedString -Value $objectStoreVolumeArg),
        (ConvertTo-BackupBashSingleQuotedString -Value $copyCommand)

    $plan = [pscustomobject]@{
        operation = 'object-backup-remote-nas'
        status = 'planned'
        code = 'INTBK-0000'
        syncPlan = $syncPlan
        command = $command
        remotePath = $remotePath
        objectStoreRoot = $objectStoreRoot
        inventoryFile = 'manifest-object-inventory.json'
    }
    if ($PlanOnly) {
        return $plan
    }

    Import-BackupOpsSshDependency
    try {
        $metadataTimeoutSeconds = 300
        $shortSshTimeoutSeconds = 60
        $metadataUploadTimeoutSeconds = 300
        $objectCopyTimeoutSeconds = 7200
        $localScriptPath = New-BackupOpsTempScriptPath -Prefix 'backup-ops-object-backup'
        $localCopyScriptPath = New-BackupOpsTempScriptPath -Prefix 'backup-ops-object-copy'
        $remoteScriptPath = '/tmp/' + [System.IO.Path]::GetFileName($localScriptPath)
        $metadataResult = Invoke-BackupSshCommand -Request ($sshRequest + @{
            Command = "docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={0} -e MC_ACCESS_KEY={1} -e MC_SECRET_KEY={2} {3} -c {4}" -f `
                (ConvertTo-BackupBashSingleQuotedString -Value $endpoint),
                (ConvertTo-BackupBashSingleQuotedString -Value $accessKey),
                (ConvertTo-BackupBashSingleQuotedString -Value $secretKey),
                (ConvertTo-BackupBashSingleQuotedString -Value $clientImage),
                (ConvertTo-BackupBashSingleQuotedString -Value $metadataCommand)
            TimeoutSeconds = $metadataTimeoutSeconds
        })
        [void][System.IO.Directory]::CreateDirectory($targetPath)
        $currentObjects = @(ConvertFrom-BackupOpsRemoteObjectMetadataJson -Output $metadataResult.output)
        $previousObjects = @(Get-BackupOpsPreviousManifestObjects -BackupPointsRoot $backupPointsRoot -CurrentBackupId ((Split-Path $remoteBackupRoot -Leaf)) -SshRequest $sshRequest)
        $inventory = Merge-BackupOpsObjectInventory -CurrentObjects $currentObjects -PreviousObjects $previousObjects
        $copyPlan = @(New-BackupOpsObjectCopyPlan -Inventory $inventory)
        $markerPath = Write-BackupOpsObjectInventoryMarker -TargetPath $targetPath -Bucket $bucket -ObjectStoreRoot $objectStoreRoot -Inventory $inventory
        try {
            Invoke-BackupSshCommand -Request ($sshRequest + @{
                Command = "mkdir -p {0}; mkdir -p {1}" -f `
                    (ConvertTo-BackupBashSingleQuotedString -Value $remotePath),
                    (ConvertTo-BackupBashSingleQuotedString -Value $objectStoreRoot)
                TimeoutSeconds = $shortSshTimeoutSeconds
            }) | Out-Null
            if ($copyPlan.Count -gt 0) {
                $planLines = foreach ($item in $copyPlan) {
                    "{0}`t{1}" -f ([string]$item.repositoryKey), ([string]$item.path)
                }
                Write-BackupOpsUtf8LfFile -Path $localScriptPath -Lines $planLines
                $copyScriptLines = @(
                    'set -eu',
                    'mc alias set src "$MC_ENDPOINT" "$MC_ACCESS_KEY" "$MC_SECRET_KEY" >/dev/null',
                    'mkdir -p /object-store',
                    "plan=/backup-point/$planFileName",
                    'if [ ! -s "$plan" ]; then',
                    '  exit 0',
                    'fi',
                    'while IFS= read -r line; do',
                    "  repo=`$(printf '%s' ""`$line"" | cut -f1)",
                    "  rel=`$(printf '%s' ""`$line"" | cut -f2-)",
                    '  [ -n "$repo" ] || continue',
                    '  if [ -f "/object-store/$repo" ]; then',
                    '    continue',
                    '  fi',
                    ('  mc cp "src/' + $bucket + '/$rel" "/object-store/$repo"'),
                    'done < "$plan"'
                )
                Write-BackupOpsUtf8LfFile -Path $localCopyScriptPath -Lines $copyScriptLines
                Send-BackupFileOverSsh -Request ($sshRequest + @{
                    LocalPath = $localScriptPath
                    RemotePath = $remoteCopyPlanPath
                    Recursive = $false
                    TimeoutSeconds = $metadataUploadTimeoutSeconds
                }) | Out-Null
                Send-BackupFileOverSsh -Request ($sshRequest + @{
                    LocalPath = $localCopyScriptPath
                    RemotePath = $remoteCopyScriptPath
                    Recursive = $false
                    TimeoutSeconds = $metadataUploadTimeoutSeconds
                }) | Out-Null
                Invoke-BackupSshCommand -Request ($sshRequest + @{
                    Command = "docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={0} -e MC_ACCESS_KEY={1} -e MC_SECRET_KEY={2} -v {3} -v {4} {5} /backup-point/{6}" -f `
                        (ConvertTo-BackupBashSingleQuotedString -Value $endpoint),
                        (ConvertTo-BackupBashSingleQuotedString -Value $accessKey),
                        (ConvertTo-BackupBashSingleQuotedString -Value $secretKey),
                        (ConvertTo-BackupBashSingleQuotedString -Value $remoteCopyPlanDir),
                        (ConvertTo-BackupBashSingleQuotedString -Value $objectStoreVolumeArg),
                        (ConvertTo-BackupBashSingleQuotedString -Value $clientImage),
                        (ConvertTo-BackupBashSingleQuotedString -Value $copyScriptFileName)
                    TimeoutSeconds = $objectCopyTimeoutSeconds
                }) | Out-Null
            }
        } finally {
            Remove-Item -LiteralPath $localScriptPath -Force -ErrorAction SilentlyContinue
            Remove-Item -LiteralPath $localCopyScriptPath -Force -ErrorAction SilentlyContinue
        }
        return [pscustomobject]@{
            operation = 'object-backup-remote-nas'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            targetPath = $targetPath
            remotePath = $remotePath
            objectStoreRoot = $objectStoreRoot
            markerPath = $markerPath
            stats = $inventory.stats
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        $rawMessage = [string]$_.Exception.Message
        throw (New-BackupOpsObjectException -Code 'INTBK-4001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "${environmentLabel}对象桶远端 NAS 备份执行失败。原始错误：$rawMessage" -Action "请先确认测试服务器 Docker、NAS 挂载、${environmentLabel} MinIO 访问和对象桶容量后再重试。"))
    }
}

function Import-BackupObjectSnapshotFromRemoteNas {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $remoteArchivePath = Get-BackupObjectFieldValue -Request $Request -Name 'RemoteArchivePath'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $archiveImage = Get-BackupObjectFieldValue -Request $Request -Name 'ArchiveImage'
    if (-not $Request.ContainsKey('SshRequest') -or $null -eq $Request['SshRequest']) {
        throw [System.ArgumentException]::new("INTBK-4002: object request field 'SshRequest' cannot be empty.")
    }
    $sshRequest = [hashtable]$Request['SshRequest']
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '目标环境' }

    $archiveSeparatorIndex = $remoteArchivePath.LastIndexOf('/')
    if ($archiveSeparatorIndex -le 0 -or $archiveSeparatorIndex -ge ($remoteArchivePath.Length - 1)) {
        throw [System.ArgumentException]::new("INTBK-4002: object request field 'RemoteArchivePath' must be an absolute remote file path.")
    }
    $remoteArchiveDir = $remoteArchivePath.Substring(0, $archiveSeparatorIndex)
    $archiveFile = $remoteArchivePath.Substring($archiveSeparatorIndex + 1)
    $volumeSuffix = [System.Text.RegularExpressions.Regex]::Replace(([System.Guid]::NewGuid().ToString('N')), '[^A-Za-z0-9_.-]', '_')
    $volumeName = "intruoyi_restore_objects_$volumeSuffix"
    $objectsVolumeArg = $volumeName + ':/objects'
    $objectsReadOnlyVolumeArg = $volumeName + ':/objects:ro'
    $archiveInputVolumeArg = $remoteArchiveDir + ':/backup-in:ro'
    $extractCommand = 'set -eu; rm -rf /objects/' + $bucket + '; mkdir -p /objects; tar -xf /backup-in/' + $archiveFile + ' -C /objects; test -d /objects/' + $bucket
    $restoreCommand = 'set -eu; mc alias set dst "$MC_ENDPOINT" "$MC_ACCESS_KEY" "$MC_SECRET_KEY" && mc mb --ignore-existing dst/' + $bucket + ' && mc mirror --overwrite /objects/' + $bucket + ' dst/' + $bucket
    $command = "set -eu; test -s {0}; docker volume rm -f {1} >/dev/null 2>&1 || true; docker volume create {1} >/dev/null; cleanup() {{ docker volume rm -f {1} >/dev/null 2>&1 || true; }}; trap cleanup EXIT; docker run --rm --entrypoint /bin/sh -v {2} -v {3} {4} -c {5}; docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={6} -e MC_ACCESS_KEY={7} -e MC_SECRET_KEY={8} -v {9} {10} -c {11}" -f `
        (ConvertTo-BackupBashSingleQuotedString -Value $remoteArchivePath),
        (ConvertTo-BackupBashSingleQuotedString -Value $volumeName),
        (ConvertTo-BackupBashSingleQuotedString -Value $objectsVolumeArg),
        (ConvertTo-BackupBashSingleQuotedString -Value $archiveInputVolumeArg),
        (ConvertTo-BackupBashSingleQuotedString -Value $archiveImage),
        (ConvertTo-BackupBashSingleQuotedString -Value $extractCommand),
        (ConvertTo-BackupBashSingleQuotedString -Value $endpoint),
        (ConvertTo-BackupBashSingleQuotedString -Value $accessKey),
        (ConvertTo-BackupBashSingleQuotedString -Value $secretKey),
        (ConvertTo-BackupBashSingleQuotedString -Value $objectsReadOnlyVolumeArg),
        (ConvertTo-BackupBashSingleQuotedString -Value $clientImage),
        (ConvertTo-BackupBashSingleQuotedString -Value $restoreCommand)

    $plan = [pscustomobject]@{
        operation = 'object-restore-remote-nas-archive'
        status = 'planned'
        code = 'INTBK-0000'
        bucket = $bucket
        remoteArchivePath = $remoteArchivePath
        command = $command
    }
    if ($PlanOnly) {
        return $plan
    }

    Import-BackupOpsSshDependency
    try {
        Invoke-BackupSshCommand -Request ($sshRequest + @{ Command = $command }) | Out-Null
        return [pscustomobject]@{
            operation = 'object-restore-remote-nas-archive'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            remoteArchivePath = $remoteArchivePath
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "${environmentLabel}对象桶远端归档恢复执行失败。" -Action "请先确认测试服务器 Docker、NAS 归档文件、${environmentLabel} MinIO 访问和对象桶容量后再重试。"))
    }
}

function Import-BackupObjectInventoryFromRemoteNas {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $remoteInventoryPath = Get-BackupObjectFieldValue -Request $Request -Name 'RemoteInventoryPath'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $remoteTempRoot = Get-BackupObjectFieldValue -Request $Request -Name 'RemoteTempRoot'
    Assert-BackupOpsObjectRestoreStageRoot -RemoteTempRoot $remoteTempRoot
    if (-not $Request.ContainsKey('SshRequest') -or $null -eq $Request['SshRequest']) {
        throw [System.ArgumentException]::new("INTBK-4002: object request field 'SshRequest' cannot be empty.")
    }
    $sshRequest = [hashtable]$Request['SshRequest']
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '目标环境' }

    Import-BackupOpsSshDependency
    $shortSshTimeoutSeconds = 60
    $metadataUploadTimeoutSeconds = 300
    $objectRestoreTimeoutSeconds = 7200
    $inventoryResult = Invoke-BackupSshCommand -Request ($sshRequest + @{
        Command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteInventoryPath)
        TimeoutSeconds = $shortSshTimeoutSeconds
    })
    $inventory = $inventoryResult.output | ConvertFrom-Json
    if ([string]$inventory.mode -ne 'incremental-manifest' -or [string]::IsNullOrWhiteSpace([string]$inventory.objectStoreRoot)) {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "远端对象增量清单无效：$remoteInventoryPath" -Action '请先确认备份点对象清单已按 incremental-manifest 生成后再执行恢复。'))
    }
    $objectStoreRoot = ([string]$inventory.objectStoreRoot).TrimEnd('/').Replace('\', '/')
    if ($objectStoreRoot -ne '/mnt/nas/Backup/BackupPackage/object-store') {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "远端对象增量清单引用的对象仓库不在受保护 BackupPackage object-store：$($inventory.objectStoreRoot)" -Action '请确认 manifest-object-inventory.json 由测试服标准 BackupPackage 备份流程生成后再执行恢复。'))
    }

    $localPlanPath = Join-Path ([System.IO.Path]::GetTempPath()) ('backup-ops-restore-plan-' + [System.Guid]::NewGuid().ToString('N') + '.tsv')
    try {
        $planLines = foreach ($item in @($inventory.objects | Where-Object { $_ -and [string]$_.status -ne 'deleted' })) {
            "{0}`t{1}" -f ([string]$item.repositoryKey), ([string]$item.path)
        }
        Write-BackupOpsUtf8LfFile -Path $localPlanPath -Lines $planLines
        $remotePlanPath = ($remoteTempRoot.TrimEnd('/')) + '/restore-object-plan.tsv'
        $remoteRestoreRoot = ($remoteTempRoot.TrimEnd('/')) + '/restore-objects'
        $planVolumeArg = ($remoteTempRoot.TrimEnd('/')) + ':/restore-plan'
        $restoreVolumeArg = $remoteRestoreRoot + ':/restore'
        $objectStoreVolumeArg = $objectStoreRoot + ':/object-store:ro'
        $restoreCommand = 'set -eu; rm -rf /restore/' + $bucket + '; mkdir -p /restore/' + $bucket + '; while IFS= read -r line; do sha=$(printf ''%s'' "$line" | cut -f1); rel=$(printf ''%s'' "$line" | cut -f2-); [ -n "$sha" ] || continue; dest="/restore/' + $bucket + '/$rel"; mkdir -p "$(dirname "$dest")"; cp "/object-store/$sha" "$dest"; done < /restore-plan/restore-object-plan.tsv; mc alias set dst "$MC_ENDPOINT" "$MC_ACCESS_KEY" "$MC_SECRET_KEY" && mc mb --ignore-existing dst/' + $bucket + ' && mc mirror --overwrite --remove /restore/' + $bucket + ' dst/' + $bucket + ' && rm -rf /restore/' + $bucket
        $command = "set -eu; mkdir -p {0}; mkdir -p {1}; test -s {2}; docker run --rm --entrypoint /bin/sh -e MC_ENDPOINT={3} -e MC_ACCESS_KEY={4} -e MC_SECRET_KEY={5} -v {6} -v {7} -v {8} {9} -c {10}" -f `
            (ConvertTo-BackupBashSingleQuotedString -Value $remoteTempRoot),
            (ConvertTo-BackupBashSingleQuotedString -Value $remoteRestoreRoot),
            (ConvertTo-BackupBashSingleQuotedString -Value $remotePlanPath),
            (ConvertTo-BackupBashSingleQuotedString -Value $endpoint),
            (ConvertTo-BackupBashSingleQuotedString -Value $accessKey),
            (ConvertTo-BackupBashSingleQuotedString -Value $secretKey),
            (ConvertTo-BackupBashSingleQuotedString -Value $planVolumeArg),
            (ConvertTo-BackupBashSingleQuotedString -Value $restoreVolumeArg),
            (ConvertTo-BackupBashSingleQuotedString -Value $objectStoreVolumeArg),
            (ConvertTo-BackupBashSingleQuotedString -Value $clientImage),
            (ConvertTo-BackupBashSingleQuotedString -Value $restoreCommand)

        $plan = [pscustomobject]@{
            operation = 'object-restore-incremental-manifest'
            status = 'planned'
            code = 'INTBK-0000'
            bucket = $bucket
            remoteInventoryPath = $remoteInventoryPath
            remotePlanPath = $remotePlanPath
            command = $command
        }
        if ($PlanOnly) {
            return $plan
        }

        Invoke-BackupSshCommand -Request ($sshRequest + @{
            Command = "mkdir -p {0}; mkdir -p {1}" -f `
                (ConvertTo-BackupBashSingleQuotedString -Value $remoteTempRoot),
                (ConvertTo-BackupBashSingleQuotedString -Value $remoteRestoreRoot)
            TimeoutSeconds = $shortSshTimeoutSeconds
        }) | Out-Null
        Send-BackupFileOverSsh -Request ($sshRequest + @{
            LocalPath = $localPlanPath
            RemotePath = $remotePlanPath
            Recursive = $false
            TimeoutSeconds = $metadataUploadTimeoutSeconds
        }) | Out-Null
        Invoke-BackupSshCommand -Request ($sshRequest + @{
            Command = $command
            TimeoutSeconds = $objectRestoreTimeoutSeconds
        }) | Out-Null
        return [pscustomobject]@{
            operation = 'object-restore-incremental-manifest'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            remoteInventoryPath = $remoteInventoryPath
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "${environmentLabel}对象清单恢复执行失败。" -Action "请先确认对象仓库、增量清单和目标环境 MinIO 访问正常后再重试。"))
    } finally {
        Remove-Item -LiteralPath $localPlanPath -Force -ErrorAction SilentlyContinue
    }
}

function Import-BackupObjectSnapshot {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    $bucket = Get-BackupObjectFieldValue -Request $Request -Name 'Bucket'
    $sourcePath = Get-BackupObjectFieldValue -Request $Request -Name 'SourcePath'
    $endpoint = Get-BackupObjectFieldValue -Request $Request -Name 'Endpoint'
    $accessKey = Get-BackupObjectFieldValue -Request $Request -Name 'AccessKey'
    $secretKey = Get-BackupObjectFieldValue -Request $Request -Name 'SecretKey'
    $clientImage = Get-BackupObjectFieldValue -Request $Request -Name 'ClientImage'
    $environmentLabel = if ($Request.ContainsKey('EnvironmentLabel') -and -not [string]::IsNullOrWhiteSpace([string]$Request['EnvironmentLabel'])) { [string]$Request['EnvironmentLabel'] } else { '正式环境' }
    $bucketSourcePath = Join-Path $sourcePath $bucket
    if (-not (Test-Path -LiteralPath $bucketSourcePath)) {
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象恢复源目录不存在：$bucketSourcePath" -Action '请先确认测试服务器备份点已同步到操作机，再执行对象恢复。'))
    }

    $volumeArgs = @('-v', ($sourcePath + ':/restore'))
    $command = "mc alias set dst $endpoint $accessKey $secretKey && mc mb --ignore-existing dst/$bucket && mc mirror --overwrite /restore/$bucket dst/$bucket"
    $plan = [pscustomobject]@{
        operation = 'object-restore'
        status = 'planned'
        code = 'INTBK-0000'
        bucket = $bucket
        sourcePath = $sourcePath
        command = $command
        volumeArgs = $volumeArgs
    }
    if ($PlanOnly) {
        return $plan
    }

    try {
        $result = Invoke-BackupOpsMcShell -Command $command -Image $clientImage -VolumeArgs $volumeArgs
        return [pscustomobject]@{
            operation = 'object-restore'
            status = 'success'
            code = 'INTBK-0000'
            bucket = $bucket
            sourcePath = $sourcePath
            output = $result.Output
        }
    } catch {
        if ($_.Exception.Data.Contains('BackupOpsCode')) {
            throw
        }
        throw (New-BackupOpsObjectException -Code 'INTBK-4002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "${environmentLabel}对象桶恢复执行失败。" -Action "请先确认恢复源目录、${environmentLabel} MinIO 访问和操作机 Docker 挂载是否正常后再重试。"))
    }
}

function Backup-BackupOpsObjectBucket {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $bucket = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('backup', 'objectBucket') -Code 'INTBK-4001' -Reason '缺少对象桶配置。' -Action '请先在运行配置中补齐 backup.objectBucket 后再执行对象备份。')
    $sourceEnvironment = if ([string]$Config.environment -eq 'test') { 'test' } else { 'production' }
    $sourceLabel = if ($sourceEnvironment -eq 'test') { '测试环境' } else { '正式环境' }
    $sourceHost = if ($sourceEnvironment -eq 'test') { [string]$Config.servers.test.host } else { [string]$Config.servers.production.host }
    $clientImage = Get-BackupOpsMinioClientImage -Config $Config -Code 'INTBK-4001'
    $archiveImage = Get-BackupOpsArchiveImage -Config $Config -Code 'INTBK-4001'
    $backupPointsRoot = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-4001' -Reason '缺少测试服务器备份点根目录配置。' -Action '请先在运行配置中补齐 servers.test.backupPointsRoot 后再执行对象备份。')
    $testSshRequest = Get-BackupOpsObjectSshRequest -Config $Config -Environment 'test' -Code 'INTBK-4001' -Reason '缺少测试服务器 SSH 配置。' -Action '请先补齐测试服务器 SSH 接线后再执行对象备份。'
    $creds = Get-BackupOpsMinioCredentials -Config $Config -Environment $sourceEnvironment -Code 'INTBK-4001'

    $targetPath = $Workspace.ObjectsPath
    $remoteObjectRoot = ($backupPointsRoot.TrimEnd('/')) + "/$($Workspace.BackupId)/objects"
    Write-BackupOpsLog -Session $LogSession -Message "Exporting object bucket $bucket from $sourceEnvironment directly to NAS path $remoteObjectRoot; remote command validates bucket access before mirroring."
    return Export-BackupObjectSnapshotToRemoteNas -Request @{
        Bucket = $bucket
        TargetPath = $targetPath
        RemotePath = $remoteObjectRoot
        SourcePath = $sourceEnvironment
        Mode = 'snapshot'
        Endpoint = "http://${sourceHost}:9000"
        AccessKey = $creds.AccessKey
        SecretKey = $creds.SecretKey
        ClientImage = $clientImage
        ArchiveImage = $archiveImage
        SshRequest = $testSshRequest
        EnvironmentLabel = $sourceLabel
    }
}

function Restore-BackupOpsObjectBucket {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $bucket = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('backup', 'objectBucket') -Code 'INTBK-4002' -Reason '缺少对象桶配置。' -Action '请先在运行配置中补齐 backup.objectBucket 后再执行对象恢复。')
    $backupPointsRoot = [string](Get-BackupOpsRequiredObjectConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-4002' -Reason '缺少测试服务器备份点根目录配置。' -Action '请先在运行配置中补齐 servers.test.backupPointsRoot 后再执行对象恢复。')
    Assert-BackupOpsObjectBackupPackageRoot -BackupPointsRoot $backupPointsRoot
    Assert-BackupOpsObjectBackupId -BackupId $BackupId
    Assert-BackupOpsObjectRestoreTestHost -Host ([string]$Config.servers.test.host) -Label '备份仓库主机'
    Assert-BackupOpsObjectRestoreTestHost -Host ([string]$Config.servers.production.host) -Label '目标主机'
    $testSshRequest = Get-BackupOpsObjectSshRequest -Config $Config -Environment 'test' -Code 'INTBK-4002' -Reason '缺少测试服务器 SSH 配置。' -Action '请先补齐测试服务器 SSH 接线后再执行对象恢复。'
    $localStageRoot = Join-Path (Split-Path -Parent ([string]$Config.paths.configPath)) '..\tmp\restore-data'
    [void][System.IO.Directory]::CreateDirectory($localStageRoot)
    $localStageRoot = (Resolve-Path $localStageRoot).Path
    $localBackupRoot = Join-Path $localStageRoot $BackupId
    $localObjectsRoot = Join-Path $localBackupRoot 'objects'
    [void][System.IO.Directory]::CreateDirectory($localObjectsRoot)
    $remoteObjectsRoot = ($backupPointsRoot.TrimEnd('/')) + "/$BackupId/objects"
    $remoteInventoryPath = $remoteObjectsRoot + '/manifest-object-inventory.json'
    $localInventoryPath = Join-Path $localObjectsRoot 'manifest-object-inventory.json'

    $repositoryKeyField = 'repositoryKey'
    Write-BackupOpsLog -Session $LogSession -Message "Downloading object inventory marker $remoteInventoryPath from test server $($Config.servers.test.host); restore will replay $repositoryKeyField mappings."
    Receive-BackupFileOverSsh -Request ($testSshRequest + @{
        RemotePath = $remoteInventoryPath
        LocalPath = $localInventoryPath
        Recursive = $false
    }) | Out-Null

    $clientImage = Get-BackupOpsMinioClientImage -Config $Config -Code 'INTBK-4002'
    $creds = Get-BackupOpsMinioCredentials -Config $Config -Environment 'production' -Code 'INTBK-4002'
    $targetEnvironmentLabel = if ([string]$Config.environment -eq 'test') { '测试环境' } elseif ([string]$Config.environment -eq 'backup') { '备份环境' } else { '目标环境' }
    $remoteTempRoot = ($backupPointsRoot.TrimEnd('/')) + "/.restore-stage/$BackupId/objects"
    Write-BackupOpsLog -Session $LogSession -Message "Restoring object bucket $bucket to $targetEnvironmentLabel from incremental inventory $remoteInventoryPath."
    return Import-BackupObjectInventoryFromRemoteNas -Request @{
        Bucket = $bucket
        RemoteInventoryPath = $remoteInventoryPath
        Endpoint = "http://$($Config.servers.production.host):9000"
        AccessKey = $creds.AccessKey
        SecretKey = $creds.SecretKey
        ClientImage = $clientImage
        SshRequest = $testSshRequest
        RemoteTempRoot = $remoteTempRoot
        EnvironmentLabel = $targetEnvironmentLabel
    }
}

Export-ModuleMember -Function New-BackupObjectSyncPlan, Test-BackupObjectAccess, Export-BackupObjectSnapshot, Export-BackupObjectSnapshotToRemoteNas, Import-BackupObjectSnapshot, Import-BackupObjectInventoryFromRemoteNas, Merge-BackupOpsObjectInventory, New-BackupOpsObjectCopyPlan, Backup-BackupOpsObjectBucket, Restore-BackupOpsObjectBucket
