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
                -DccSnapshotPath $snapshotPath `
                -ObjectInventoryPath $inventoryPath `
                -OutputPath $manifestPath

            $result.ExitCode | Should Be 0
            $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $manifest.targetEnvironment | Should Be 'backup'
            $manifest.targetHost | Should Be '172.30.30.59'

            $validation = Test-DccBackupChainManifest -Manifest $manifest
            $validation.status | Should Be 'passed'
        }
        finally {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
