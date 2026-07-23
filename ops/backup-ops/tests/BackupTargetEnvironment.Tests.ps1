$ErrorActionPreference = 'Stop'

$fileOpsModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Infra\FileOps.psm1'
$dockerOpsModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Infra\DockerOps.psm1'
$mySqlOpsModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Infra\MySqlOps.psm1'
$objectOpsModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Infra\ObjectOps.psm1'
$dccSnapshotModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Core\DccDatabaseSnapshotExporter.psm1'
$dccManifestModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Core\DccBackupManifestBuilder.psm1'
$dccChainModulePath = Join-Path $PSScriptRoot '..\scripts\modules\Core\DccBackupChainValidator.psm1'
$rehearsalModulePath = Join-Path $PSScriptRoot '..\scripts\modules\UseCases\Rehearsal.psm1'

Import-Module $fileOpsModulePath -Force -DisableNameChecking
Import-Module $dockerOpsModulePath -Force -DisableNameChecking
Import-Module $mySqlOpsModulePath -Force -DisableNameChecking
Import-Module $objectOpsModulePath -Force -DisableNameChecking
Import-Module $dccSnapshotModulePath -Force -DisableNameChecking
Import-Module $dccManifestModulePath -Force -DisableNameChecking
Import-Module $dccChainModulePath -Force -DisableNameChecking
Import-Module $rehearsalModulePath -Force -DisableNameChecking

Describe 'backup target environment support' {
    BeforeEach {
        Import-Module $fileOpsModulePath -Force -DisableNameChecking
        Import-Module $dockerOpsModulePath -Force -DisableNameChecking
        Import-Module $mySqlOpsModulePath -Force -DisableNameChecking
        Import-Module $objectOpsModulePath -Force -DisableNameChecking
        Import-Module $dccSnapshotModulePath -Force -DisableNameChecking
        Import-Module $dccManifestModulePath -Force -DisableNameChecking
        Import-Module $dccChainModulePath -Force -DisableNameChecking
        Import-Module $rehearsalModulePath -Force -DisableNameChecking
    }

    function New-BackupTargetTestConfig {
        return [pscustomobject]@{
            environment = 'backup'
            servers = [pscustomobject]@{
                production = [pscustomobject]@{
                    host = '172.30.30.59'
                    appDir = '/opt/intruoyi/runtime'
                    tmpRoot = '/mnt/intruoyi-data/runtime-data/backup-ops/tmp'
                }
                test = [pscustomobject]@{
                    host = '172.30.30.58'
                    backupPointsRoot = '/mnt/nas/Backup/BackupPackage'
                    rehearsalRoot = '/backup/int-ruoyi/rehearsal/runtime'
                    rehearsalBackendPort = 48082
                    rehearsalFrontendPort = 18081
                }
                backup = [pscustomobject]@{
                    host = '172.30.30.59'
                    backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage'
                    rehearsalRoot = '/mnt/intruoyi-data/backup-ops/rehearsal/runtime'
                    rehearsalBackendPort = 48082
                    rehearsalFrontendPort = 18081
                }
            }
            ssh = [pscustomobject]@{
                user = 'root'
                port = 22
            }
            auth = [pscustomobject]@{
                sshKeyPath = 'C:\keys\id_rsa'
                knownHostsPath = 'C:\keys\known_hosts'
            }
        }
    }

    It 'accepts backup as a known backup target proof' {
        InModuleScope FileOps {
            Test-BackupOpsKnownBackupTarget -Environment 'backup' -Host '172.30.30.59' | Should Be $true
        }
    }

    It 'resolves backup SSH requests from FileOps' {
        InModuleScope FileOps {
            $config = [pscustomobject]@{
                servers = [pscustomobject]@{
                    backup = [pscustomobject]@{
                        host = '172.30.30.59'
                    }
                }
                ssh = [pscustomobject]@{
                    user = 'root'
                    port = 22
                }
                auth = [pscustomobject]@{
                    sshKeyPath = 'C:\keys\id_rsa'
                    knownHostsPath = 'C:\keys\known_hosts'
                }
            }

            $request = Get-BackupOpsFileSshRequest -Config $config -Environment 'backup' -Code 'INTBK-TEST'

            $request.Host | Should Be '172.30.30.59'
            $request.User | Should Be 'root'
            $request.KeyPath | Should Be 'C:\keys\id_rsa'
            $request.Port | Should Be 22
            $request.KnownHostsPath | Should Be 'C:\keys\known_hosts'
        }
    }

    It 'keeps backup restore candidates when manifest target proof is backup' {
        InModuleScope DockerOps {
            function Import-BackupOpsSshDependency {}

            function Get-BackupOpsRequiredConfigValue {
                param(
                    [object]$Config,
                    [string[]]$Path,
                    [string]$Code,
                    [string]$Reason,
                    [string]$Action
                )

                if ($Path -join '.' -eq 'servers.backup.backupPointsRoot') { return '/mnt/intruoyi-data/Backup/BackupPackage' }
                if ($Path -join '.' -eq 'backup.mysqlDatabase') { return 'ruoyi-vue-pro' }
                if ($Path -join '.' -eq 'backup.objectBucket') { return 'yudao' }
                throw "Unexpected path: $($Path -join '.')"
            }

            function Get-BackupOpsTestSshRequest {
                param([object]$Config, [string]$Code)
                return @{ Host = '172.30.30.59'; User = 'root' }
            }

            function Invoke-BackupSshCommand {
                param([hashtable]$Request)
                return [pscustomobject]@{
                    output = '/mnt/intruoyi-data/Backup/BackupPackage/20260621-123456'
                }
            }

            function Get-BackupOpsRemotePathExists {
                param($SshRequest, [string]$Path, [string]$Kind)
                return $true
            }

            function Get-BackupOpsRemoteFileText {
                param($SshRequest, [string]$Path)

                if ($Path -like '*/deploy/image-tag.txt') {
                    return "release-20260621-page-full-flow-v6`n"
                }

                if ($Path -like '*/manifest/manifest.json') {
                    return @'
{
  "backupType": "manual",
  "status": "success",
  "targetEnvironment": "backup",
  "targetHost": "172.30.30.59",
  "time": { "completedAt": "2026-06-21T12:34:56+08:00" },
  "deploy": { "imageTag": "release-20260621-page-full-flow-v6" },
  "backupStrategy": {
    "mode": "incremental-manifest",
    "mysqlBackupMode": "full-dump-baseline"
  },
  "recoverySet": {
    "id": "20260621-123456",
    "status": "COMPLETE",
    "program": { "imageTag": "release-20260621-page-full-flow-v6" },
    "dcc": { "manifestPath": "manifest/dcc-backup-manifest.json" },
    "redis": { "policy": "CLEAR_AND_REBUILD" },
    "configuration": {
      "manifestPath": "deploy/runtime.env",
      "composePath": "deploy/docker-compose.yml"
    },
    "checksums": {
      "path": "manifest/checksums.txt",
      "sha256": "abc123"
    }
  },
  "validation": {
    "mysqlDumpCreated": true,
    "objectBackupCreated": true,
    "checksumsGenerated": true,
    "rehearsalStatus": "PASSED",
    "lastRehearsedAt": "2026-06-21T13:00:00+08:00"
  }
}
'@
                }

                throw "Unexpected remote file request: $Path"
            }

            function Write-BackupOpsLog {
                param($Session, [string]$Message, [string]$Level = 'INFO')
            }

            function Test-BackupOpsRemoteDccBackupManifestContract {
                param($SshRequest, [string]$Path)
                return [pscustomobject]@{
                    status = 'passed'
                    message = 'ok'
                }
            }

            $config = [pscustomobject]@{
                environment = 'backup'
            }
            $logSession = [pscustomobject]@{}

            try {
                $candidates = @(Get-BackupOpsRestoreCandidates -Config $config -LogSession $logSession -SelectedBackupId '20260621-123456' -Purpose 'restore')

                $candidates.Count | Should Be 1
                $candidates[0].backupId | Should Be '20260621-123456'
                $candidates[0].targetEnvironment | Should Be 'backup'
                $candidates[0].targetHost | Should Be '172.30.30.59'
            }
            finally {
                Remove-Item -Path function:\Import-BackupOpsSshDependency -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Get-BackupOpsRequiredConfigValue -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Get-BackupOpsTestSshRequest -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Get-BackupOpsRemotePathExists -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Get-BackupOpsRemoteFileText -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Write-BackupOpsLog -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Test-BackupOpsRemoteDccBackupManifestContract -ErrorAction SilentlyContinue
            }
        }
    }

    It 'checks backup repository mount on the backup host without touching the test host' {
        InModuleScope FileOps {
            function Import-BackupOpsSshDependency {}

            function Invoke-BackupSshCommand {
                param([hashtable]$Request)

                $script:CapturedBackupMountHosts += @([string]$Request.Host)
                return [pscustomobject]@{
                    output = ''
                }
            }

            function Write-BackupOpsLog {
                param($Session, [string]$Message, [string]$Level = 'INFO')
            }

            $script:CapturedBackupMountHosts = @()
            $config = [pscustomobject]@{
                environment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{ host = '172.30.30.59'; appDir = '/opt/intruoyi/runtime' }
                    test = [pscustomobject]@{ host = '172.30.30.58'; backupPointsRoot = '/mnt/nas/Backup/BackupPackage' }
                    backup = [pscustomobject]@{ host = '172.30.30.59'; backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            try {
                $result = Assert-BackupOpsRemoteNasMounted -Config $config -LogSession ([pscustomobject]@{})

                $result.backupPointsRoot | Should Be '/mnt/intruoyi-data/Backup/BackupPackage'
                $script:CapturedBackupMountHosts | Should Be @('172.30.30.59')
            }
            finally {
                Remove-Item -Path function:\Import-BackupOpsSshDependency -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Write-BackupOpsLog -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedBackupMountHosts -Scope Script -ErrorAction SilentlyContinue
            }
        }
    }

    It 'does not require the production source host to mount the explicit backup repository path' {
        InModuleScope FileOps {
            function Import-BackupOpsSshDependency {}

            function Invoke-BackupSshCommand {
                param([hashtable]$Request)

                $script:CapturedProductionRepositoryChecks += @([pscustomobject]@{
                    Host = [string]$Request.Host
                    Command = [string]$Request.Command
                })

                if ([string]$Request.Host -eq '172.30.30.57' -and [string]$Request.Command -like '*/mnt/intruoyi-data/Backup/BackupPackage*') {
                    throw 'production source host must not validate the backup repository path'
                }

                return [pscustomobject]@{ output = '' }
            }

            function Write-BackupOpsLog {
                param($Session, [string]$Message, [string]$Level = 'INFO')
            }

            $script:CapturedProductionRepositoryChecks = @()
            $config = [pscustomobject]@{
                environment = 'production'
                repositoryEnvironment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{
                        host = '172.30.30.57'
                        appDir = '/opt/intruoyi/runtime'
                        tmpRoot = '/opt/intruoyi/runtime/data/backup-ops/tmp'
                    }
                    test = [pscustomobject]@{ host = '172.30.30.58'; backupPointsRoot = '/mnt/nas/Backup/BackupPackage' }
                    backup = [pscustomobject]@{ host = '172.30.30.59'; backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            try {
                $result = Assert-BackupOpsRemoteNasMounted -Config $config -LogSession ([pscustomobject]@{})

                $result.backupPointsRoot | Should Be '/mnt/intruoyi-data/Backup/BackupPackage'
                @($script:CapturedProductionRepositoryChecks | Where-Object { $_.Host -eq '172.30.30.59' -and $_.Command -like '*/mnt/intruoyi-data/Backup/BackupPackage*' }).Count | Should Be 1
                @($script:CapturedProductionRepositoryChecks | Where-Object { $_.Host -eq '172.30.30.57' -and $_.Command -like '*/opt/intruoyi/runtime/data*' }).Count | Should Be 1
                @($script:CapturedProductionRepositoryChecks | Where-Object { $_.Host -eq '172.30.30.57' -and $_.Command -like '*/mnt/intruoyi-data/Backup/BackupPackage*' }).Count | Should Be 0
            }
            finally {
                Remove-Item -Path function:\Import-BackupOpsSshDependency -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Write-BackupOpsLog -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedProductionRepositoryChecks -Scope Script -ErrorAction SilentlyContinue
            }
        }
    }

    It 'uses the backup host as the MySQL backup repository host' {
        InModuleScope MySqlOps {
            $config = [pscustomobject]@{
                environment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{ host = '172.30.30.59' }
                    test = [pscustomobject]@{ host = '172.30.30.58' }
                    backup = [pscustomobject]@{ host = '172.30.30.59' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            $request = Get-BackupOpsTestSshRequest -Config $config

            $request.Host | Should Be '172.30.30.59'
        }
    }

    It 'exports production MySQL dumps through source temp storage before uploading to the explicit backup repository' {
        InModuleScope MySqlOps {
            function Import-BackupOpsSshDependency {}
            function Get-BackupOpsMySqlRootPassword { param([object]$Config) return 'secret' }
            function Test-BackupMySqlConnectivity { param([hashtable]$Request) return [pscustomobject]@{ status = 'success' } }
            function Write-BackupOpsLog { param($Session, [string]$Message, [string]$Level = 'INFO') }
            function Invoke-BackupSshCommand {
                param([hashtable]$Request)
                $script:CapturedMySqlCrossHostCommands += @($Request)
                return [pscustomobject]@{ output = '' }
            }
            function Export-BackupMySqlDump {
                param([hashtable]$Request)
                $script:CapturedMySqlDumpExports += @($Request)
                if ([string]$Request.Host -eq '172.30.30.57' -and [string]$Request.RemoteDumpPath -like '/mnt/intruoyi-data/*') {
                    throw 'production source cannot write directly to the backup data disk repository path'
                }
                return [pscustomobject]@{ status = 'success'; remoteDumpPath = $Request.RemoteDumpPath }
            }
            function Receive-BackupFileOverSsh {
                param([hashtable]$Request)
                $script:CapturedMySqlDumpDownloads += @($Request)
                [void][System.IO.Directory]::CreateDirectory((Split-Path -Parent ([string]$Request.LocalPath)))
                [System.IO.File]::WriteAllText([string]$Request.LocalPath, 'dump', [System.Text.UTF8Encoding]::new($false))
                return [pscustomobject]@{ status = 'success' }
            }
            function Send-BackupFileOverSsh {
                param([hashtable]$Request)
                $script:CapturedMySqlDumpUploads += @($Request)
                return [pscustomobject]@{ status = 'success' }
            }

            $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('mysql-prod-backup-repo-' + [guid]::NewGuid().ToString('N'))
            [void][System.IO.Directory]::CreateDirectory($tempRoot)
            $script:CapturedMySqlCrossHostCommands = @()
            $script:CapturedMySqlDumpExports = @()
            $script:CapturedMySqlDumpDownloads = @()
            $script:CapturedMySqlDumpUploads = @()
            $config = [pscustomobject]@{
                environment = 'production'
                repositoryEnvironment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{
                        host = '172.30.30.57'
                        tmpRoot = '/opt/intruoyi/runtime/data/backup-ops/tmp'
                    }
                    test = [pscustomobject]@{
                        host = '172.30.30.58'
                        backupPointsRoot = '/mnt/nas/Backup/BackupPackage'
                    }
                    backup = [pscustomobject]@{
                        host = '172.30.30.59'
                        backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage'
                    }
                }
                containers = [pscustomobject]@{ mysql = 'intruoyi-mysql' }
                backup = [pscustomobject]@{ mysqlDatabase = 'ruoyi-vue-pro' }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }
            $workspace = [pscustomobject]@{
                BackupId = '20260723-233700'
                MySqlPath = $tempRoot
            }

            try {
                $result = Export-BackupOpsMySqlDump -Config $config -Workspace $workspace -LogSession ([pscustomobject]@{})

                $result.status | Should Be 'success'
                $script:CapturedMySqlDumpExports.Count | Should Be 1
                $script:CapturedMySqlDumpExports[0].Host | Should Be '172.30.30.57'
                $script:CapturedMySqlDumpExports[0].RemoteDumpPath | Should Match '^/opt/intruoyi/runtime/data/backup-ops/tmp/'
                $script:CapturedMySqlDumpDownloads.Count | Should Be 1
                $script:CapturedMySqlDumpDownloads[0].Host | Should Be '172.30.30.57'
                $script:CapturedMySqlDumpUploads.Count | Should Be 1
                $script:CapturedMySqlDumpUploads[0].Host | Should Be '172.30.30.59'
                $script:CapturedMySqlDumpUploads[0].RemotePath | Should Be '/mnt/intruoyi-data/Backup/BackupPackage/20260723-233700/mysql/ruoyi-vue-pro.sql.gz'
                $workspace.RemoteMySqlDumpPath | Should Be '/mnt/intruoyi-data/Backup/BackupPackage/20260723-233700/mysql/ruoyi-vue-pro.sql.gz'
            }
            finally {
                Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Import-BackupOpsSshDependency -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Get-BackupOpsMySqlRootPassword -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Test-BackupMySqlConnectivity -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Write-BackupOpsLog -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Export-BackupMySqlDump -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Receive-BackupFileOverSsh -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Send-BackupFileOverSsh -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedMySqlCrossHostCommands -Scope Script -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedMySqlDumpExports -Scope Script -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedMySqlDumpDownloads -Scope Script -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedMySqlDumpUploads -Scope Script -ErrorAction SilentlyContinue
            }
        }
    }

    It 'allows source temp MySQL dump paths only for explicit cross-host export staging' {
        InModuleScope MySqlOps {
            $sourceTempDumpPath = '/opt/intruoyi/runtime/data/backup-ops/tmp/backup-now/20260724-004458/mysql/ruoyi-vue-pro.sql.gz'
            $baseRequest = @{
                ContainerName = 'intruoyi-mysql'
                DatabaseName = 'ruoyi-vue-pro'
                RootPassword = 'secret'
                RemoteDumpPath = $sourceTempDumpPath
            }

            $defaultPathBlocked = $false
            try {
                New-BackupMySqlDumpCommandSpec -Request $baseRequest | Out-Null
            }
            catch {
                $defaultPathBlocked = $true
            }
            $defaultPathBlocked | Should Be $true

            $exportSpec = New-BackupMySqlDumpCommandSpec -Request ($baseRequest + @{
                    AllowSourceTempDumpPath = $true
                    SourceTempRoot = '/opt/intruoyi/runtime/data/backup-ops/tmp'
                })

            $exportSpec.remoteDumpPath | Should Be $sourceTempDumpPath
            $exportSpec.remoteCommand | Should Match '/opt/intruoyi/runtime/data/backup-ops/tmp/backup-now/20260724-004458/mysql/ruoyi-vue-pro.sql.gz'

            $outsideSourceTempBlocked = $false
            try {
                New-BackupMySqlDumpCommandSpec -Request ($baseRequest + @{
                        AllowSourceTempDumpPath = $true
                        SourceTempRoot = '/opt/intruoyi/runtime/data/backup-ops/tmp'
                        RemoteDumpPath = '/tmp/backup-now/20260724-004458/mysql/ruoyi-vue-pro.sql.gz'
                    }) | Out-Null
            }
            catch {
                $outsideSourceTempBlocked = $true
            }
            $outsideSourceTempBlocked | Should Be $true

            $restoreBlocked = $false
            try {
                New-BackupMySqlRestoreCommandSpec -Request $baseRequest | Out-Null
            }
            catch {
                $restoreBlocked = $true
            }
            $restoreBlocked | Should Be $true
        }
    }

    It 'preserves the backup repository proof for rehearsal MySQL restores' {
        InModuleScope MySqlOps {
            $config = [pscustomobject]@{
                environment = 'rehearsal'
                repositoryEnvironment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{ host = '172.30.30.59' }
                    test = [pscustomobject]@{ host = '172.30.30.58' }
                    backup = [pscustomobject]@{ host = '172.30.30.59' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            Get-BackupOpsMySqlRepositoryEnvironment -Config $config | Should Be 'backup'
            $request = Get-BackupOpsTestSshRequest -Config $config

            $request.Host | Should Be '172.30.30.59'
        }
    }

    It 'resolves an explicit backup repository while keeping production as the data source' {
        InModuleScope FileOps {
            $config = [pscustomobject]@{
                environment = 'production'
                repositoryEnvironment = 'backup'
                servers = [pscustomobject]@{
                    production = [pscustomobject]@{ host = '172.30.30.57' }
                    test = [pscustomobject]@{ host = '172.30.30.58'; backupPointsRoot = '/mnt/nas/Backup/BackupPackage' }
                    backup = [pscustomobject]@{ host = '172.30.30.59'; backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            Get-BackupOpsRepositoryEnvironment -Config $config | Should Be 'backup'
            $repositoryRequest = Get-BackupOpsRepositoryFileSshRequest -Config $config -Code 'INTBK-2003'
            $repositoryRequest.Host | Should Be '172.30.30.59'
            Get-BackupOpsRepositoryBackupPointsRoot -Config $config -Code 'INTBK-2003' -Reason 'missing' -Action 'fix' | Should Be '/mnt/intruoyi-data/Backup/BackupPackage'
        }
    }

    It 'uses the explicit backup repository for production object backups' {
        InModuleScope ObjectOps {
            $config = [pscustomobject]@{
                environment = 'production'
                repositoryEnvironment = 'backup'
            }

            Get-BackupOpsObjectRepositoryEnvironment -Config $config | Should Be 'backup'
            Get-BackupOpsObjectRuntimeEnvironment -Config $config | Should Be 'production'
        }
    }

    It 'accepts production DCC backup manifests for restore-chain validation' {
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('dcc-prod-chain-' + [guid]::NewGuid().ToString('N'))
        [void][System.IO.Directory]::CreateDirectory($tempRoot)
        $snapshotPath = Join-Path $tempRoot 'dcc-snapshot.json'
        $inventoryPath = Join-Path $tempRoot 'object-inventory.json'
        $manifestPath = Join-Path $tempRoot 'dcc-backup-manifest.json'

        try {
            [pscustomobject]@{
                schemaVersion = 'dcc-snapshot-v1'
                schemaVersionTag = 'dcc-database-snapshot-v1'
                targetEnvironment = 'production'
                targetHost = '172.30.30.57'
                tenantId = 122
                controlledFiles = @(
                    [pscustomobject]@{
                        fileKey = 'controlled-file:1001'
                        controlledFileId = 1001
                        tenantId = 122
                        fileNumber = 'DCC-PROD-001'
                        versionNo = 'A'
                        status = 'ACTIVE'
                        state = 'active'
                        permissionDigest = 'perm-1'
                        databaseDigest = 'db-1'
                        updatedAt = '2026-07-23T23:37:00+08:00'
                        objectPath = 'dcc/stamped/prod-sample.pdf'
                        objects = @(
                            [pscustomobject]@{
                                role = 'controlled'
                                fileId = 9001
                                path = 'dcc/stamped/prod-sample.pdf'
                            }
                        )
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $snapshotPath -Encoding UTF8

            [pscustomobject]@{
                mode = 'incremental-manifest'
                bucket = 'yudao'
                objectStoreRoot = '/mnt/intruoyi-data/Backup/BackupPackage/object-store'
                objects = @(
                    [pscustomobject]@{
                        path = 'dcc/stamped/prod-sample.pdf'
                        sha256 = 'abc123'
                        repositoryKey = 'abc123'
                        size = 12
                        lastModified = '2026-07-23T23:37:00+08:00'
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

            $result = Invoke-DccBackupManifestBuild `
                -BackupId '20260723-233700' `
                -RestorePointId '20260723-233700' `
                -TargetEnvironment 'production' `
                -TargetHost '172.30.30.57' `
                -BackupScopeType 'target-dataset' `
                -BackupScopeId 'tenant:122' `
                -DccSnapshotPath $snapshotPath `
                -ObjectInventoryPath $inventoryPath `
                -OutputPath $manifestPath

            $result.ExitCode | Should Be 0
            $result.Payload.backupScopeType | Should Be 'target-dataset'
            $result.Payload.backupScopeId | Should Be 'tenant:122'
            $validation = Test-DccBackupChainManifest -Manifest $result.Payload
            $validation.status | Should Be 'passed'
        }
        finally {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    It 'blocks DCC manifest generation when backup scope is missing' {
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('dcc-scope-block-' + [guid]::NewGuid().ToString('N'))
        [void][System.IO.Directory]::CreateDirectory($tempRoot)
        $snapshotPath = Join-Path $tempRoot 'dcc-snapshot.json'
        $inventoryPath = Join-Path $tempRoot 'object-inventory.json'
        $manifestPath = Join-Path $tempRoot 'dcc-backup-manifest.json'

        try {
            [pscustomobject]@{
                schemaVersion = 'dcc-snapshot-v1'
                schemaVersionTag = 'dcc-database-snapshot-v1'
                targetEnvironment = 'backup'
                targetHost = '172.30.30.59'
                tenantId = 122
                controlledFiles = @(
                    [pscustomobject]@{
                        fileKey = 'controlled-file:1001'
                        controlledFileId = 1001
                        tenantId = 122
                        fileNumber = 'DCC-SCOPE-001'
                        versionNo = 'A'
                        status = 'ACTIVE'
                        state = 'active'
                        permissionDigest = 'perm-1'
                        databaseDigest = 'db-1'
                        updatedAt = '2026-07-23T23:37:00+08:00'
                        objectPath = 'dcc/stamped/scope-sample.pdf'
                        objects = @(
                            [pscustomobject]@{
                                role = 'controlled'
                                fileId = 9001
                                path = 'dcc/stamped/scope-sample.pdf'
                            }
                        )
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $snapshotPath -Encoding UTF8

            [pscustomobject]@{
                mode = 'incremental-manifest'
                bucket = 'yudao'
                objectStoreRoot = '/mnt/intruoyi-data/Backup/BackupPackage/object-store'
                objects = @(
                    [pscustomobject]@{
                        path = 'dcc/stamped/scope-sample.pdf'
                        sha256 = 'abc123'
                        repositoryKey = 'abc123'
                        size = 12
                        lastModified = '2026-07-23T23:37:00+08:00'
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

            $result = Invoke-DccBackupManifestBuild `
                -BackupId '20260723-233700' `
                -RestorePointId '20260723-233700' `
                -TargetEnvironment 'backup' `
                -TargetHost '172.30.30.59' `
                -DccSnapshotPath $snapshotPath `
                -ObjectInventoryPath $inventoryPath `
                -OutputPath $manifestPath

            $result.ExitCode | Should Be 2
            @($result.Payload.errors | Where-Object { $_.code -eq 'backup_scope_missing' }).Count | Should BeGreaterThan 0
        }
        finally {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    It 'writes rehearsal evidence to the backup repository' {
        InModuleScope Rehearsal {
            function Send-BackupFileOverSsh {
                param([hashtable]$Request)
                $script:CapturedEvidenceUploads += @($Request)
                return [pscustomobject]@{ status = 'success' }
            }

            function Write-BackupOpsLog {
                param($Session, [string]$Message, [string]$Level = 'INFO')
            }

            $script:CapturedEvidenceUploads = @()
            $config = [pscustomobject]@{
                environment = 'backup'
                servers = [pscustomobject]@{
                    test = [pscustomobject]@{
                        host = '172.30.30.58'
                        backupPointsRoot = '/mnt/nas/Backup/BackupPackage'
                    }
                    backup = [pscustomobject]@{
                        host = '172.30.30.59'
                        backupPointsRoot = '/mnt/intruoyi-data/Backup/BackupPackage'
                    }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            try {
                Write-BackupOpsRehearsalEvidence `
                    -Config $config `
                    -BackupId '20260621-123456' `
                    -Context @{ imageTag = 'release-test'; checks = @{ backendHealth = 'pass'; frontendHttp200 = 'pass' } } `
                    -StartedAt ([datetimeoffset]'2026-06-21T12:00:00+08:00') `
                    -CompletedAt ([datetimeoffset]'2026-06-21T12:05:00+08:00') `
                    -LogSession ([pscustomobject]@{})

                $script:CapturedEvidenceUploads.Count | Should Be 2
                @($script:CapturedEvidenceUploads | ForEach-Object { $_.Host } | Sort-Object -Unique) | Should Be @('172.30.30.59')
                foreach ($upload in $script:CapturedEvidenceUploads) {
                    [string]$upload.RemotePath | Should Match '^/mnt/intruoyi-data/Backup/BackupPackage/20260621-123456/manifest/'
                }
            }
            finally {
                Remove-Item -Path function:\Send-BackupFileOverSsh -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Write-BackupOpsLog -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedEvidenceUploads -Scope Script -ErrorAction SilentlyContinue
            }
        }
    }

    It 'accepts backup object SSH requests and backup data-disk BackupPackage roots' {
        InModuleScope ObjectOps {
            $config = [pscustomobject]@{
                environment = 'backup'
                servers = [pscustomobject]@{
                    backup = [pscustomobject]@{ host = '172.30.30.59' }
                }
                ssh = [pscustomobject]@{ user = 'root'; port = 22 }
                auth = [pscustomobject]@{ sshKeyPath = 'C:\keys\id_rsa'; knownHostsPath = 'C:\keys\known_hosts' }
            }

            $request = Get-BackupOpsObjectSshRequest `
                -Config $config `
                -Environment 'backup' `
                -Code 'INTBK-4002' `
                -Reason 'missing backup host' `
                -Action 'configure backup host'

            $request.Host | Should Be '172.30.30.59'
            { Assert-BackupOpsObjectBackupPackageRoot -BackupPointsRoot '/mnt/intruoyi-data/Backup/BackupPackage' } | Should Not Throw
            { Assert-BackupOpsObjectRestoreStageRoot -RemoteTempRoot '/mnt/intruoyi-data/Backup/BackupPackage/.restore-stage/20260621-123456/objects' } | Should Not Throw
        }
    }

    It 'parses object metadata JSON when docker pull status lines precede mc output' {
        InModuleScope ObjectOps {
            $output = @'
Unable to find image 'quay.io/minio/mc:latest' locally
latest: Pulling from minio/mc
3f4ca61aafcd: Pulling fs layer
3f4ca61aafcd: Download complete
Digest: sha256:abc123
Status: Downloaded newer image for quay.io/minio/mc:latest
{"status":"success","type":"file","key":"dcc/sample.pdf","etag":"etag-1","size":42,"lastModified":"2026-07-24T00:54:00Z"}
'@

            $objects = @(ConvertFrom-BackupOpsRemoteObjectMetadataJson -Output $output)

            $objects.Count | Should Be 1
            $objects[0].path | Should Be 'dcc/sample.pdf'
            $objects[0].repositoryKey | Should Be 'etag-1'
        }
    }

    It 'blocks object metadata parsing when remote output is non-json and not docker status noise' {
        InModuleScope ObjectOps {
            $nonJsonBlocked = $false
            try {
                ConvertFrom-BackupOpsRemoteObjectMetadataJson -Output 'mc: <ERROR> Unable to list bucket.' | Out-Null
            }
            catch {
                $nonJsonBlocked = $true
            }
            $nonJsonBlocked | Should Be $true
        }
    }

    It 'accepts backup object inventory roots during restore replay planning' {
        InModuleScope ObjectOps {
            function Import-BackupOpsSshDependency {}

            function Invoke-BackupSshCommand {
                param([hashtable]$Request)
                return [pscustomobject]@{
                    output = @'
{
  "mode": "incremental-manifest",
  "bucket": "yudao",
  "objectStoreRoot": "/mnt/intruoyi-data/Backup/BackupPackage/object-store",
  "objects": [
    {
      "status": "active",
      "repositoryKey": "abc123",
      "path": "dcc/sample.pdf"
    }
  ]
}
'@
                }
            }

            try {
                $plan = Import-BackupObjectInventoryFromRemoteNas -PlanOnly -Request @{
                    Bucket = 'yudao'
                    RemoteInventoryPath = '/mnt/intruoyi-data/Backup/BackupPackage/20260621-123456/objects/manifest-object-inventory.json'
                    Endpoint = 'http://172.30.30.59:9000'
                    AccessKey = 'minio'
                    SecretKey = 'secret'
                    ClientImage = 'minio/mc:latest'
                    SshRequest = @{ Host = '172.30.30.59'; User = 'root' }
                    RemoteTempRoot = '/mnt/intruoyi-data/Backup/BackupPackage/.restore-stage/20260621-123456/objects'
                    EnvironmentLabel = '备份环境'
                }

                $plan.status | Should Be 'planned'
                $plan.remoteInventoryPath | Should Be '/mnt/intruoyi-data/Backup/BackupPackage/20260621-123456/objects/manifest-object-inventory.json'
            }
            finally {
                Remove-Item -Path function:\Import-BackupOpsSshDependency -ErrorAction SilentlyContinue
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
            }
        }
    }

    It 'reads MinIO credentials for the backup environment' {
        InModuleScope ObjectOps {
            function Get-BackupOpsRemoteContainerEnvValue {
                param(
                    [object]$Config,
                    [string]$Environment,
                    [string]$ContainerName,
                    [string]$Key,
                    [string]$Code,
                    [string]$Reason,
                    [string]$Action
                )

                if ($Environment -ne 'backup') { throw "Unexpected environment: $Environment" }
                if ($ContainerName -ne 'intruoyi-minio') { throw "Unexpected container: $ContainerName" }
                if ($Key -eq 'MINIO_ROOT_USER') { return 'minio' }
                if ($Key -eq 'MINIO_ROOT_PASSWORD') { return 'secret' }
                throw "Unexpected key: $Key"
            }

            $config = [pscustomobject]@{
                containers = [pscustomobject]@{
                    minio = 'intruoyi-minio'
                }
            }

            try {
                $creds = Get-BackupOpsMinioCredentials -Config $config -Environment 'backup' -Code 'INTBK-4001'

                $creds.ContainerName | Should Be 'intruoyi-minio'
                $creds.AccessKey | Should Be 'minio'
                $creds.SecretKey | Should Be 'secret'
            }
            finally {
                Remove-Item -Path function:\Get-BackupOpsRemoteContainerEnvValue -ErrorAction SilentlyContinue
            }
        }
    }

    It 'computes checksum hashes without depending on Get-FileHash' {
        InModuleScope FileOps {
            $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('backup-target-env-' + [guid]::NewGuid().ToString('N'))
            [void][System.IO.Directory]::CreateDirectory($tempRoot)
            $samplePath = Join-Path $tempRoot 'sample.txt'

            try {
                [System.IO.File]::WriteAllText($samplePath, 'abc', [System.Text.UTF8Encoding]::new($false))

                Get-BackupOpsFileSha256 -LiteralPath $samplePath | Should Be 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
            }
            finally {
                Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }

    It 'exports a DCC snapshot for backup target proof' {
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('backup-target-env-' + [guid]::NewGuid().ToString('N'))
        [void][System.IO.Directory]::CreateDirectory($tempRoot)
        $queryJsonPath = Join-Path $tempRoot 'dcc-query.json'
        $snapshotPath = Join-Path $tempRoot 'dcc-snapshot.json'

        try {
            [pscustomobject]@{
                rows = @(
                    [pscustomobject]@{
                        controlledFileId = 1001
                        tenantId = 122
                        fileNumber = 'DCC-001'
                        versionNo = 'A'
                        status = 'ACTIVE'
                        updatedAt = '2026-06-21T12:00:00+08:00'
                        objectRole = 'controlled'
                        objectFileId = 9001
                        objectPath = 'dcc/stamped/sample.pdf'
                        objectSha256 = 'abc123'
                        permissionDigest = 'perm-1'
                    }
                )
            } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $queryJsonPath -Encoding UTF8

            $result = Invoke-DccDatabaseSnapshotExport `
                -TargetEnvironment 'backup' `
                -TargetHost '172.30.30.59' `
                -TenantId 122 `
                -QueryResultJsonPath $queryJsonPath `
                -OutputPath $snapshotPath

            $result.ExitCode | Should Be 0
            $snapshot = Get-Content -LiteralPath $snapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $snapshot.targetEnvironment | Should Be 'backup'
            $snapshot.targetHost | Should Be '172.30.30.59'
        }
        finally {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    It 'builds a DCC manifest for backup target proof' {
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('backup-target-env-' + [guid]::NewGuid().ToString('N'))
        [void][System.IO.Directory]::CreateDirectory($tempRoot)
        $snapshotPath = Join-Path $tempRoot 'dcc-snapshot.json'
        $inventoryPath = Join-Path $tempRoot 'object-inventory.json'
        $manifestPath = Join-Path $tempRoot 'dcc-backup-manifest.json'

        try {
            [pscustomobject]@{
                schemaVersion = 'dcc-snapshot-v1'
                schemaVersionTag = 'dcc-database-snapshot-v1'
                targetEnvironment = 'backup'
                targetHost = '172.30.30.59'
                tenantId = 122
                controlledFiles = @(
                    [pscustomobject]@{
                        fileKey = 'controlled-file:1001'
                        controlledFileId = 1001
                        tenantId = 122
                        fileNumber = 'DCC-001'
                        versionNo = 'A'
                        status = 'ACTIVE'
                        state = 'active'
                        permissionDigest = 'perm-1'
                        databaseDigest = 'db-1'
                        updatedAt = '2026-06-21T12:00:00+08:00'
                        objectPath = 'dcc/stamped/sample.pdf'
                        objects = @(
                            [pscustomobject]@{
                                role = 'controlled'
                                fileId = 9001
                                path = 'dcc/stamped/sample.pdf'
                            }
                        )
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $snapshotPath -Encoding UTF8

            [pscustomobject]@{
                mode = 'incremental-manifest'
                bucket = 'yudao'
                objectStoreRoot = '/mnt/intruoyi-data/Backup/BackupPackage/object-store'
                objects = @(
                    [pscustomobject]@{
                        path = 'dcc/stamped/sample.pdf'
                        sha256 = 'abc123'
                        repositoryKey = 'abc123'
                        size = 12
                        lastModified = '2026-06-21T12:00:00+08:00'
                    }
                )
            } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

            $result = Invoke-DccBackupManifestBuild `
                -BackupId '20260621-123456' `
                -RestorePointId '20260621-123456' `
                -TargetEnvironment 'backup' `
                -TargetHost '172.30.30.59' `
                -BackupScopeType 'target-dataset' `
                -BackupScopeId 'tenant:122' `
                -DccSnapshotPath $snapshotPath `
                -ObjectInventoryPath $inventoryPath `
                -OutputPath $manifestPath

            $result.ExitCode | Should Be 0
            $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $manifest.targetEnvironment | Should Be 'backup'
            $manifest.targetHost | Should Be '172.30.30.59'
            $manifest.backupScopeType | Should Be 'target-dataset'
            $manifest.backupScopeId | Should Be 'tenant:122'

            $validation = Test-DccBackupChainManifest -Manifest $manifest
            $validation.status | Should Be 'passed'
        }
        finally {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
