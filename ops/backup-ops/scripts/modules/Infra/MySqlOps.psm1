Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)
$script:BackupMySqlDumpArguments = @(
    '--single-transaction',
    '--routines',
    '--triggers',
    '--hex-blob',
    '--default-character-set=utf8mb4'
)

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

function Merge-BackupOpsRequest {
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

function New-BackupOpsOperatorBlockedMessage {
    param(
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    return "原因：$Reason`n建议动作：$Action"
}

function New-BackupOpsMySqlException {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('INTBK-3001', 'INTBK-3002', 'INTBK-3003')]
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

function Get-BackupMySqlFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name,
        [ValidateSet('INTBK-3001', 'INTBK-3002', 'INTBK-3003')]
        [string]$Code = 'INTBK-3001'
    )

    if (-not $Request.ContainsKey($Name)) {
        throw (New-BackupOpsMySqlException -Code $Code -Status 'blocked' -Message "Missing MySQL request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw (New-BackupOpsMySqlException -Code $Code -Status 'blocked' -Message "MySQL request field '$Name' cannot be empty.")
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
        [ValidateSet('INTBK-3001', 'INTBK-3002', 'INTBK-3003')]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    $value = Get-BackupOpsConfigValueSafe -InputObject $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw (New-BackupOpsMySqlException -Code $Code -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
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

function Get-BackupOpsRestoreStageRoot {
    param(
        [Parameter(Mandatory)]
        [string]$BackupId
    )

    $root = Get-BackupOpsRootPath
    return Join-Path $root ("tmp\restore-data\" + $BackupId + "\mysql")
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

function Get-BackupOpsProductionSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config
    )

    return @{
        Host = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'host') -Code 'INTBK-3001' -Reason '缺少正式服务器地址配置。' -Action '请在 runtime 配置中补齐 servers.production.host 后再执行 MySQL 备份或恢复。')
        User = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('ssh', 'user') -Code 'INTBK-3001' -Reason '缺少 SSH 操作用户配置。' -Action '请在 secrets 描述文件中补齐 ssh.user 后再重试。')
        KeyPath = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('auth', 'sshKeyPath') -Code 'INTBK-3001' -Reason '缺少 SSH 私钥路径配置。' -Action '请在操作机 secrets 文件中配置 auth.sshKeyPath，并确保私钥文件存在。')
        Port = if ($Config.ssh.PSObject.Properties['port']) { [int]$Config.ssh.port } else { 22 }
        KnownHostsPath = if ($Config.auth.PSObject.Properties['knownHostsPath']) { [string]$Config.auth.knownHostsPath } else { '' }
    }
}

function Get-BackupOpsTestSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config
    )

    $request = Get-BackupOpsProductionSshRequest -Config $Config
    $request['Host'] = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'host') -Code 'INTBK-3002' -Reason '缺少测试服务器地址配置。' -Action '请在 runtime 配置中补齐 servers.test.host 后再执行恢复。')
    return $request
}

function Get-BackupOpsRuntimeEnvLines {
    param(
        [Parameter(Mandatory)]
        [object]$Config
    )

    Import-BackupOpsSshDependency
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config
    $appDir = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-3001' -Reason '缺少正式运行目录配置。' -Action '请在 runtime 配置中补齐 servers.production.appDir 后再执行。')
    $envPath = ($appDir.TrimEnd('/')) + '/.env'
    $command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $envPath)
    $result = Invoke-BackupSshCommand -Request ($sshRequest + @{
        Command = $command
        TimeoutSeconds = 60
    })
    $lines = @($result.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -eq 0) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "正式环境运行时配置为空或无法读取：$envPath" -Action '请确认正式环境 runtime/.env 存在且 SSH 账号具备读取权限后再重试。'))
    }

    return $lines
}

function Get-BackupOpsMySqlRootPassword {
    param(
        [Parameter(Mandatory)]
        [object]$Config
    )

    $envLines = Get-BackupOpsRuntimeEnvLines -Config $Config
    $password = Get-BackupOpsDotEnvValue -Lines $envLines -Key 'MYSQL_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($password)) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason '正式环境 runtime/.env 中缺少 MYSQL_ROOT_PASSWORD。' -Action '请先补齐正式环境 MySQL 凭据来源，再执行备份或恢复。'))
    }

    return $password
}

function Get-BackupOpsMySqlDumpFileName {
    param(
        [Parameter(Mandatory)]
        [string]$DatabaseName
    )

    return "$DatabaseName.sql.gz"
}

function Assert-BackupOpsMySqlRestoreTestHost {
    param(
        [Parameter(Mandatory)]
        [string]$Host,
        [Parameter(Mandatory)]
        [string]$Label
    )

    if ($Host -eq '172.30.30.57') {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复${Label}禁止指向正式服务器 172.30.30.57。" -Action '停止恢复，修正 TargetEnvironment 和运行配置，恢复目标只能是测试服务器 172.30.30.58。'))
    }
    if ($Host -ne '172.30.30.58') {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复${Label}无法证明为测试服务器 172.30.30.58：$Host" -Action '请显式使用 targetEnvironment=test，并确认目标主机和备份仓库主机均为 172.30.30.58。'))
    }
}

function Get-BackupOpsMySqlExpectedBackupSourceHost {
    param(
        [Parameter(Mandatory)]
        [string]$Environment
    )

    switch ($Environment) {
        'production' { return '172.30.30.57' }
        'prod' { return '172.30.30.57' }
        'test' { return '172.30.30.58' }
        'backup' { return '172.30.30.59' }
        default { return '' }
    }
}

function Assert-BackupOpsMySqlBackupSourceHost {
    param(
        [Parameter(Mandatory)]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Host
    )

    $expectedHost = Get-BackupOpsMySqlExpectedBackupSourceHost -Environment $Environment
    if ([string]::IsNullOrWhiteSpace($expectedHost)) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 备份源环境未知：$Environment。" -Action '请显式使用 test、backup、prod 或 production 之一后再执行备份。'))
    }
    if ($Host -ne $expectedHost) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 备份源主机与目标环境不匹配：environment=$Environment host=$Host expected=$expectedHost。" -Action '请修正 TargetEnvironment 与运行配置，确保备份源主机可被明确证明。'))
    }
}

function Assert-BackupOpsMySqlBackupRepositoryHost {
    param(
        [Parameter(Mandatory)]
        [string]$Host
    )

    if ($Host -ne '172.30.30.58') {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 备份仓库主机必须是测试服务器 172.30.30.58：$Host。" -Action '请确认 BackupPackage 仓库仍由测试服务器挂载的 /mnt/nas/Backup/BackupPackage 承载。'))
    }
}

function Assert-BackupMySqlRemoteBackupPackageDumpPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $normalized = $Path.Replace('\', '/')
    if (-not $normalized.StartsWith('/mnt/nas/Backup/BackupPackage/', [System.StringComparison]::Ordinal)) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复 dump 不在测试服 BackupPackage 目录下：$Path" -Action '请确认恢复点来自测试服务器 /mnt/nas/Backup/BackupPackage 后再执行恢复。'))
    }
    if ($normalized -match '(^|/)\.\.($|/)') {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复 dump 路径包含非法上级目录引用：$Path" -Action '请使用 BackupPackage 下的合法备份点路径。'))
    }
    if ($normalized -like '*/ReleasePackage/*') {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复 dump 指向 ReleasePackage：$Path" -Action '数据恢复只能读取 BackupPackage 下的数据备份。'))
    }
}

function Get-BackupMySqlRemoteDumpDirectory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $normalized = $Path.Replace('\', '/')
    $lastSlash = $normalized.LastIndexOf('/')
    if ($lastSlash -le 0) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'blocked' -Message "MySQL remote dump path is invalid: $Path")
    }
    return $normalized.Substring(0, $lastSlash)
}

function New-BackupMySqlDumpCommandSpec {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    $containerName = Get-BackupMySqlFieldValue -Request $Request -Name 'ContainerName'
    $databaseName = Get-BackupMySqlFieldValue -Request $Request -Name 'DatabaseName'
    $rootPassword = Get-BackupMySqlFieldValue -Request $Request -Name 'RootPassword'

    $escapedPassword = ConvertTo-BackupBashSingleQuotedString -Value $rootPassword
    $escapedDatabase = ConvertTo-BackupBashSingleQuotedString -Value $databaseName
    $dumpArgsText = $script:BackupMySqlDumpArguments -join ' '
    $dumpCommand = "docker exec {0} mysqldump {1} -uroot -p{2} --databases {3} | gzip -c" -f $containerName, $dumpArgsText, $escapedPassword, $escapedDatabase

    if ($Request.ContainsKey('RemoteDumpPath') -and -not [string]::IsNullOrWhiteSpace([string]$Request['RemoteDumpPath'])) {
        $remoteDumpPath = Get-BackupMySqlFieldValue -Request $Request -Name 'RemoteDumpPath'
        Assert-BackupMySqlRemoteBackupPackageDumpPath -Path $remoteDumpPath
        $remoteDumpDirectory = Get-BackupMySqlRemoteDumpDirectory -Path $remoteDumpPath
        $escapedRemoteDumpDirectory = ConvertTo-BackupBashSingleQuotedString -Value $remoteDumpDirectory
        $escapedRemoteDumpPath = ConvertTo-BackupBashSingleQuotedString -Value $remoteDumpPath
        $remoteScript = "set -euo pipefail; mkdir -p $escapedRemoteDumpDirectory; $dumpCommand > $escapedRemoteDumpPath; test -s $escapedRemoteDumpPath"
        return [pscustomobject]([ordered]@{
                tool = 'mysqldump'
                databaseName = $databaseName
                container = $containerName
                arguments = @($script:BackupMySqlDumpArguments)
                outputPath = ''
                remoteDumpPath = $remoteDumpPath
                remoteCommand = "bash -lc {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteScript)
                commandPreview = "docker exec $containerName mysqldump $dumpArgsText -uroot -p<hidden> --databases $databaseName | gzip -c > $remoteDumpPath"
            })
    }

    $outputPath = Get-BackupMySqlFieldValue -Request $Request -Name 'OutputPath'

    return [pscustomobject]([ordered]@{
            tool = 'mysqldump'
            databaseName = $databaseName
            container = $containerName
            arguments = @($script:BackupMySqlDumpArguments)
            outputPath = $outputPath
            remoteDumpPath = ''
            remoteCommand = $dumpCommand
            commandPreview = "docker exec $containerName mysqldump $dumpArgsText -uroot -p<hidden> --databases $databaseName | gzip -c"
        })
}

function New-BackupMySqlRestoreCommandSpec {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    $containerName = Get-BackupMySqlFieldValue -Request $Request -Name 'ContainerName' -Code 'INTBK-3002'
    $databaseName = Get-BackupMySqlFieldValue -Request $Request -Name 'DatabaseName' -Code 'INTBK-3002'
    $remoteDumpPath = Get-BackupMySqlFieldValue -Request $Request -Name 'RemoteDumpPath' -Code 'INTBK-3002'
    $rootPassword = Get-BackupMySqlFieldValue -Request $Request -Name 'RootPassword' -Code 'INTBK-3002'

    Assert-BackupMySqlRemoteBackupPackageDumpPath -Path $remoteDumpPath

    $escapedPassword = ConvertTo-BackupBashSingleQuotedString -Value $rootPassword
    $escapedRemoteDump = ConvertTo-BackupBashSingleQuotedString -Value $remoteDumpPath
    $resetSqlArgs = @(
        ConvertTo-BackupBashSingleQuotedString -Value "DROP DATABASE IF EXISTS ``$databaseName``;"
        ConvertTo-BackupBashSingleQuotedString -Value "CREATE DATABASE ``$databaseName`` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
    ) -join ' '

    return [pscustomobject]([ordered]@{
            container = $containerName
            databaseName = $databaseName
            remoteDumpPath = $remoteDumpPath
            resetCommand = "printf '%s\n' $resetSqlArgs | docker exec -i $containerName mysql -uroot -p$escapedPassword"
            importCommand = "gzip -dc $escapedRemoteDump | docker exec -i $containerName mysql -uroot -p$escapedPassword"
            connectivityCommand = "docker exec $containerName mysqladmin -uroot -p$escapedPassword ping --silent"
            commandPreview = @(
                "printf '%s\n' '<reset database sql>' | docker exec -i $containerName mysql -uroot -p<hidden>"
                "gzip -dc $remoteDumpPath | docker exec -i $containerName mysql -uroot -p<hidden>"
            )
        })
}

function Test-BackupMySqlConnectivity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    Import-BackupOpsSshDependency
    $containerName = Get-BackupMySqlFieldValue -Request $Request -Name 'ContainerName' -Code 'INTBK-3003'
    $rootPassword = Get-BackupMySqlFieldValue -Request $Request -Name 'RootPassword' -Code 'INTBK-3003'
    $command = "docker exec {0} mysqladmin -uroot -p{1} ping --silent" -f $containerName, (ConvertTo-BackupBashSingleQuotedString -Value $rootPassword)
    $plan = [pscustomobject]([ordered]@{
            operation = 'mysql-health-check'
            host = $Request['Host']
            user = $Request['User']
            container = $containerName
            command = $command
            commandPreview = "docker exec $containerName mysqladmin -uroot -p<hidden> ping --silent"
        })
    if ($PlanOnly) {
        return $plan
    }

    try {
        $result = Invoke-BackupSshCommand -Request (Merge-BackupOpsRequest -Request $Request -Extra @{
            Command = $command
            TimeoutSeconds = 60
        })
        return [pscustomobject]([ordered]@{
                operation = 'mysql-health-check'
                status = 'success'
                code = 'INTBK-0000'
                host = $Request['Host']
                user = $Request['User']
                container = $containerName
                output = $result.output
            })
    } catch {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3003' -Status 'fail' -Message "MySQL connectivity check failed for container '$containerName'. $($_.Exception.Message)")
    }
}

function Export-BackupMySqlDump {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    Import-BackupOpsSshDependency
    $commandSpec = New-BackupMySqlDumpCommandSpec -Request $Request
    if ($PlanOnly) {
        return $commandSpec
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$commandSpec.outputPath)) {
        $outputParent = Split-Path -Parent $commandSpec.outputPath
        if (-not [string]::IsNullOrWhiteSpace($outputParent)) {
            [void][System.IO.Directory]::CreateDirectory($outputParent)
        }
    }

    try {
        Invoke-BackupSshCommand -Request (Merge-BackupOpsRequest -Request $Request -Extra @{
                Command = $commandSpec.remoteCommand
                OutputPath = $commandSpec.outputPath
                TimeoutSeconds = 7200
            }) | Out-Null
    } catch {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3001' -Status 'fail' -Message "MySQL dump export failed for database '$($commandSpec.databaseName)'. $($_.Exception.Message)")
    }

    return [pscustomobject]([ordered]@{
            operation = 'mysql-dump'
            status = 'success'
            code = 'INTBK-0000'
            databaseName = $commandSpec.databaseName
            container = $commandSpec.container
            outputPath = $commandSpec.outputPath
            remoteDumpPath = $commandSpec.remoteDumpPath
        })
}

function Import-BackupMySqlDump {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$PlanOnly
    )

    Import-BackupOpsSshDependency
    $restoreSpec = New-BackupMySqlRestoreCommandSpec -Request $Request
    if ($PlanOnly) {
        return $restoreSpec
    }

    try {
        Invoke-BackupSshCommand -Request (Merge-BackupOpsRequest -Request $Request -Extra @{
            Command = "test -f {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $restoreSpec.remoteDumpPath)
            TimeoutSeconds = 60
        }) | Out-Null
        Test-BackupMySqlConnectivity -Request $Request | Out-Null
        Invoke-BackupSshCommand -Request (Merge-BackupOpsRequest -Request $Request -Extra @{
            Command = $restoreSpec.resetCommand
            TimeoutSeconds = 300
        }) | Out-Null
        Invoke-BackupSshCommand -Request (Merge-BackupOpsRequest -Request $Request -Extra @{
            Command = $restoreSpec.importCommand
            TimeoutSeconds = 7200
        }) | Out-Null
    } catch {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'fail' -Message "MySQL dump import failed for database '$($restoreSpec.databaseName)'. $($_.Exception.Message)")
    }

    return [pscustomobject]([ordered]@{
            operation = 'mysql-restore'
            status = 'success'
            code = 'INTBK-0000'
            databaseName = $restoreSpec.databaseName
            container = $restoreSpec.container
            remoteDumpPath = $restoreSpec.remoteDumpPath
        })
}

function Export-BackupOpsMySqlDump {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $sshRequest = Get-BackupOpsProductionSshRequest -Config $Config
    $testSshRequest = Get-BackupOpsTestSshRequest -Config $Config
    $targetEnvironment = if ($Config.PSObject.Properties['environment']) { [string]$Config.environment } else { 'production' }
    Assert-BackupOpsMySqlBackupSourceHost -Environment $targetEnvironment -Host ([string]$sshRequest.Host)
    Assert-BackupOpsMySqlBackupRepositoryHost -Host ([string]$testSshRequest.Host)
    $containerName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('containers', 'mysql') -Code 'INTBK-3001' -Reason '缺少 MySQL 容器名配置。' -Action '请在 runtime 配置中补齐 containers.mysql 后再执行备份。')
    $databaseName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-3001' -Reason '缺少 MySQL 数据库名配置。' -Action '请在 runtime 配置中补齐 backup.mysqlDatabase 后再执行备份。')
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-3001' -Reason '缺少测试服务器备份根目录配置。' -Action '请在 runtime 配置中补齐 servers.test.backupPointsRoot 后再执行备份。')
    $rootPassword = Get-BackupOpsMySqlRootPassword -Config $Config
    $dumpFileName = Get-BackupOpsMySqlDumpFileName -DatabaseName $databaseName
    $remoteDumpPath = ($backupPointsRoot.TrimEnd('/')) + "/$($Workspace.BackupId)/mysql/$dumpFileName"
    Assert-BackupMySqlRemoteBackupPackageDumpPath -Path $remoteDumpPath
    if ($Workspace.PSObject.Properties['RemoteMySqlDumpPath']) {
        $Workspace.RemoteMySqlDumpPath = $remoteDumpPath
    } else {
        $Workspace | Add-Member -MemberType NoteProperty -Name 'RemoteMySqlDumpPath' -Value $remoteDumpPath
    }

    Write-BackupOpsLog -Session $LogSession -Message "Checking production MySQL connectivity on $($sshRequest.Host) for container $containerName."
    Test-BackupMySqlConnectivity -Request (Merge-BackupOpsRequest -Request $sshRequest -Extra @{
            ContainerName = $containerName
            DatabaseName = $databaseName
            RootPassword = $rootPassword
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message "Exporting MySQL dump from $($sshRequest.Host) directly to test BackupPackage path $remoteDumpPath using docker exec mysqldump."
    $result = Export-BackupMySqlDump -Request (Merge-BackupOpsRequest -Request $sshRequest -Extra @{
            ContainerName = $containerName
            DatabaseName = $databaseName
            RootPassword = $rootPassword
            RemoteDumpPath = $remoteDumpPath
        })
    Write-BackupOpsLog -Session $LogSession -Message "MySQL dump exported successfully: $remoteDumpPath"
    return $result
}

function Import-BackupOpsMySqlDump {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$BackupId,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $databaseName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-3002' -Reason '缺少 MySQL 数据库名配置。' -Action '请在 runtime 配置中补齐 backup.mysqlDatabase 后再执行恢复。')
    $containerName = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('containers', 'mysql') -Code 'INTBK-3002' -Reason '缺少 MySQL 容器名配置。' -Action '请在 runtime 配置中补齐 containers.mysql 后再执行恢复。')
    $backupPointsRoot = [string](Get-BackupOpsRequiredConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-3002' -Reason '缺少测试服务器备份点根目录配置。' -Action '请在 runtime 配置中补齐 servers.test.backupPointsRoot 后再执行恢复。')
    $dumpFileName = Get-BackupOpsMySqlDumpFileName -DatabaseName $databaseName
    $testDumpPath = ($backupPointsRoot.TrimEnd('/')) + "/$BackupId/mysql/$dumpFileName"
    Assert-BackupMySqlRemoteBackupPackageDumpPath -Path $testDumpPath
    $testSshRequest = Get-BackupOpsTestSshRequest -Config $Config
    $productionSshRequest = Get-BackupOpsProductionSshRequest -Config $Config

    Assert-BackupOpsMySqlRestoreTestHost -Host ([string]$testSshRequest.Host) -Label '备份仓库主机'
    Assert-BackupOpsMySqlRestoreTestHost -Host ([string]$productionSshRequest.Host) -Label '目标主机'

    if ([string]$productionSshRequest.Host -ne [string]$testSshRequest.Host) {
        throw (New-BackupOpsMySqlException -Code 'INTBK-3002' -Status 'blocked' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 恢复目标主机 $($productionSshRequest.Host) 与测试备份仓库主机 $($testSshRequest.Host) 不一致，无法证明恢复动作只作用于测试服务器。" -Action '请显式使用 targetEnvironment=test 并确认运行配置把恢复目标固定到 172.30.30.58。'))
    }

    $rootPassword = Get-BackupOpsMySqlRootPassword -Config $Config

    Write-BackupOpsLog -Session $LogSession -Message "Checking production MySQL connectivity on $($productionSshRequest.Host) before import."
    Test-BackupMySqlConnectivity -Request (Merge-BackupOpsRequest -Request $productionSshRequest -Extra @{
            ContainerName = $containerName
            DatabaseName = $databaseName
            RootPassword = $rootPassword
        }) | Out-Null

    Write-BackupOpsLog -Session $LogSession -Message "Importing MySQL restore point $BackupId from test BackupPackage path $testDumpPath into target container $containerName via docker exec mysql."
    $result = Import-BackupMySqlDump -Request (Merge-BackupOpsRequest -Request $productionSshRequest -Extra @{
            ContainerName = $containerName
            DatabaseName = $databaseName
            RootPassword = $rootPassword
            RemoteDumpPath = $testDumpPath
        })
    Write-BackupOpsLog -Session $LogSession -Message "MySQL restore point $BackupId imported successfully from $testDumpPath."
    return $result
}

Export-ModuleMember -Function New-BackupMySqlDumpCommandSpec, New-BackupMySqlRestoreCommandSpec, Test-BackupMySqlConnectivity, Export-BackupMySqlDump, Import-BackupMySqlDump, Export-BackupOpsMySqlDump, Import-BackupOpsMySqlDump
