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

function New-BackupOpsOperatorBlockedMessage {
    param(
        [Parameter(Mandatory)]
        [string]$Reason,
        [Parameter(Mandatory)]
        [string]$Action
    )

    return "原因：$Reason`n建议动作：$Action"
}

function Assert-BackupOpsTarExecutable {
    if (-not (Get-Command -Name 'tar' -ErrorAction SilentlyContinue)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2002' -Message (New-BackupOpsOperatorBlockedMessage -Reason '当前操作机缺少 tar 命令，无法打包对象目录。' -Action '请先在操作机安装或启用 tar 后再执行备份同步。'))
    }
}

function ConvertTo-BackupBashSingleQuotedString {
    param(
        [Parameter(Mandatory)]
        [string]$Value
    )

    return "'" + ($Value -replace "'", "'""'""'") + "'"
}

function Get-BackupOpsFileConfigValueSafe {
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

function Get-BackupOpsRequiredFileConfigValue {
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

    $value = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path $Path
    if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
        throw (New-BackupOpsInfraBlockedException -Code $Code -Message (New-BackupOpsOperatorBlockedMessage -Reason $Reason -Action $Action))
    }

    return $value
}

function Get-BackupOpsOptionalFileConfigString {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string[]]$Path,
        [string]$DefaultValue = ''
    )

    $value = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path $Path
    if ($null -eq $value) {
        return $DefaultValue
    }
    $text = ([string]$value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $DefaultValue
    }
    return $text
}

function Test-BackupOpsTruthyConfigValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $false
    }
    if ($Value -is [bool]) {
        return [bool]$Value
    }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    return $text -in @('1', 'true', 'yes', 'on')
}

function Resolve-BackupOpsMySqlBackupMode {
    param(
        [Parameter(Mandatory)]
        [object]$Config
    )

    $explicitMode = Get-BackupOpsOptionalFileConfigString -Config $Config -Path @('backup', 'mysqlBackupMode') -DefaultValue ''
    if (-not [string]::IsNullOrWhiteSpace($explicitMode)) {
        return $explicitMode.ToLowerInvariant()
    }

    $incrementalEnabled = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'mysqlIncremental', 'enabled')
    if (Test-BackupOpsTruthyConfigValue -Value $incrementalEnabled) {
        $strategy = Get-BackupOpsOptionalFileConfigString -Config $Config -Path @('backup', 'mysqlIncremental', 'strategy') -DefaultValue 'incremental'
        return $strategy.ToLowerInvariant()
    }

    return 'full-dump-baseline'
}

function Assert-BackupOpsMySqlBackupModeSupported {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [string]$Status
    )

    $mode = Resolve-BackupOpsMySqlBackupMode -Config $Config
    $allowedModes = @('full-dump-baseline', 'full-dump', 'logical-full-dump')
    if ($Status -eq 'success' -and $mode -notin $allowedModes) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL incremental backup requested: mysqlBackupMode=$mode. Current backup flow only supports a full-dump baseline and records binlog/xtrabackup as requires-prerequisite. No silent full dump fallback is allowed for an incremental MySQL backup request." -Action '保持 mysqlBackupMode=full-dump-baseline，或先实现并验证 binlog/xtrabackup 增量链、权限、依赖、锁、恢复演练和 manifest 证据后再启用 MySQL 增量模式。'))
    }

    return $mode
}

function Get-BackupOpsFileDotEnvValue {
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

function Get-BackupOpsRequiredManifestRuntimePort {
    param(
        [Parameter(Mandatory)]
        [string]$RuntimeEnvPath,
        [Parameter(Mandatory)]
        [string]$Key
    )

    if (-not (Test-Path -LiteralPath $RuntimeEnvPath)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "备份点缺少 deploy/runtime.env：$RuntimeEnvPath。" -Action '请先完成部署元数据采集后再生成 manifest。'))
    }

    $lines = [System.IO.File]::ReadAllLines($RuntimeEnvPath, [System.Text.Encoding]::UTF8)
    $value = Get-BackupOpsFileDotEnvValue -Lines $lines -Key $Key
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "deploy/runtime.env 缺少 $Key。" -Action '请补齐运行时端口配置后再生成 manifest。'))
    }

    $parsed = 0
    if (-not [int]::TryParse($value, [ref]$parsed)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "deploy/runtime.env 端口配置无效：$Key=$value。" -Action '请修正端口为整数后再生成 manifest。'))
    }

    return $parsed
}

function Get-BackupOpsFileSshRequest {
    param(
        [Parameter(Mandatory)]
        [object]$Config,
        [Parameter(Mandatory)]
        [ValidateSet('production', 'test')]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Code
    )

    return @{
        Host = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', $Environment, 'host') -Code $Code -Reason "缺少${Environment}服务器地址配置。" -Action '请先补齐服务器地址配置后再重试。')
        User = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('ssh', 'user') -Code $Code -Reason '缺少 SSH 操作用户配置。' -Action '请先补齐 ssh.user 后再重试。')
        KeyPath = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('auth', 'sshKeyPath') -Code $Code -Reason '缺少 SSH 私钥路径配置。' -Action '请先补齐 auth.sshKeyPath 并确保文件存在。')
        Port = if ($Config.ssh.PSObject.Properties['port']) { [int]$Config.ssh.port } else { 22 }
        KnownHostsPath = if ($Config.auth.PSObject.Properties['knownHostsPath']) { [string]$Config.auth.knownHostsPath } else { '' }
    }
}

function New-BackupOpsInfraBlockedException {
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

function Get-BackupOpsRemoteNasMountRoot {
    param(
        [Parameter(Mandatory)]
        [string]$BackupPointsRoot
    )

    $normalized = $BackupPointsRoot.Replace('\', '/').TrimEnd('/')
    if ($normalized -eq '/mnt/nas' -or $normalized.StartsWith('/mnt/nas/')) {
        return '/mnt/nas'
    }

    throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2003' -Message (New-BackupOpsOperatorBlockedMessage -Reason "测试服务器备份目录不在 NAS 挂载路径下：$BackupPointsRoot。" -Action '请将 servers.test.backupPointsRoot 配置为 /mnt/nas 下的 Backup/BackupPackage 路径后再执行备份。'))
}

function Get-BackupOpsExpectedBackupTargetHost {
    param(
        [Parameter(Mandatory)]
        [string]$Environment
    )

    switch ($Environment) {
        'test' { return '172.30.30.58' }
        'production' { return '172.30.30.57' }
        'prod' { return '172.30.30.57' }
        default { return '' }
    }
}

function Test-BackupOpsKnownBackupTarget {
    param(
        [Parameter(Mandatory)]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Host
    )

    $expectedHost = Get-BackupOpsExpectedBackupTargetHost -Environment $Environment
    return (-not [string]::IsNullOrWhiteSpace($expectedHost)) -and $Host -eq $expectedHost
}

function Assert-BackupOpsKnownBackupTarget {
    param(
        [Parameter(Mandatory)]
        [string]$Environment,
        [Parameter(Mandatory)]
        [string]$Host,
        [Parameter(Mandatory)]
        [string]$Code,
        [Parameter(Mandatory)]
        [string]$Scope
    )

    if (Test-BackupOpsKnownBackupTarget -Environment $Environment -Host $Host) {
        return
    }

    throw (New-BackupOpsInfraBlockedException -Code $Code -Message (New-BackupOpsOperatorBlockedMessage -Reason "$Scope 目标证明无效：targetEnvironment=$Environment targetHost=$Host；仅允许 test/172.30.30.58 或 production/172.30.30.57。" -Action '请修正 TargetEnvironment 与运行配置，禁止生成无法证明来源环境的数据备份。'))
}

function Assert-BackupOpsRemoteNasMounted {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $testRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'test' -Code 'INTBK-2003'
    $targetEnvironment = if ($Config.PSObject.Properties['environment']) { [string]$Config.environment } else { 'test' }
    $backupPointsRoot = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-2003' -Reason '缺少测试服务器备份根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行备份。')
    $remoteTargetRoot = $backupPointsRoot.TrimEnd('/')
    $mountRoot = Get-BackupOpsRemoteNasMountRoot -BackupPointsRoot $remoteTargetRoot
    $escapedMountRoot = ConvertTo-BackupBashSingleQuotedString -Value $mountRoot
    $escapedTargetRoot = ConvertTo-BackupBashSingleQuotedString -Value $remoteTargetRoot
    $command = "test -d $escapedMountRoot && mountpoint -q $escapedMountRoot && mkdir -p $escapedTargetRoot && test -w $escapedTargetRoot"
    $checkRequests = New-Object System.Collections.Generic.List[object]
    $checkRequests.Add([pscustomobject]@{ Request = $testRequest; Label = 'backup-repository' })
    if ($targetEnvironment -in @('production', 'prod')) {
        $productionRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'production' -Code 'INTBK-2003'
        Assert-BackupOpsKnownBackupTarget -Environment $targetEnvironment -Host ([string]$productionRequest.Host) -Code 'INTBK-2003' -Scope '备份源'
        if ([string]$productionRequest.Host -ne [string]$testRequest.Host) {
            $checkRequests.Add([pscustomobject]@{ Request = $productionRequest; Label = 'backup-source' })
        }
    }

    foreach ($entry in $checkRequests) {
        try {
            Invoke-BackupSshCommand -Request ($entry.Request + @{ Command = $command }) | Out-Null
        } catch {
            throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2003' -Message (New-BackupOpsOperatorBlockedMessage -Reason "$($entry.Label) NAS 未就绪或不可写：$remoteTargetRoot。" -Action '请先确认 /mnt/nas 已挂载公司共享盘，并且当前 SSH 用户可写 Backup/BackupPackage 后再执行备份。'))
        }
    }

    Write-BackupOpsLog -Session $LogSession -Message "Verified remote NAS mount $mountRoot and writable backup root $remoteTargetRoot on hosts $(@($checkRequests | ForEach-Object { $_.Request.Host }) -join ',')."
    return [pscustomobject]@{
        operation = 'remote-nas-check'
        status = 'success'
        code = 'INTBK-0000'
        mountRoot = $mountRoot
        backupPointsRoot = $remoteTargetRoot
        host = $testRequest.Host
        checkedHosts = @($checkRequests | ForEach-Object { $_.Request.Host })
    }
}

function Get-BackupFileFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Request.ContainsKey($Name)) {
        throw [System.ArgumentException]::new("INTBK-6002: missing file request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw [System.ArgumentException]::new("INTBK-6002: file request field '$Name' cannot be empty.")
    }

    return [string]$value
}

function New-BackupDirectoryLayout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    $backupId = Get-BackupFileFieldValue -Request $Request -Name 'BackupId'

    return [pscustomobject]([ordered]@{
            backupId = $backupId
            mysql    = "mysql"
            objects  = "objects"
            deploy   = "deploy"
            manifest = "manifest"
        })
}

function New-BackupWorkingDirectory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$CreateOnDisk
    )

    $backupId = Get-BackupFileFieldValue -Request $Request -Name 'BackupId'
    $rootPath = Get-BackupFileFieldValue -Request $Request -Name 'RootPath'
    $layout = New-BackupDirectoryLayout -Request @{ BackupId = $backupId }
    $backupRoot = Join-Path -Path $rootPath -ChildPath $backupId

    $result = [ordered]@{
        backupRoot = $backupRoot
        mysql      = Join-Path -Path $backupRoot -ChildPath $layout.mysql
        objects    = Join-Path -Path $backupRoot -ChildPath $layout.objects
        deploy     = Join-Path -Path $backupRoot -ChildPath $layout.deploy
        manifest   = Join-Path -Path $backupRoot -ChildPath $layout.manifest
    }

    if ($CreateOnDisk) {
        foreach ($path in $result.Values) {
            [void][System.IO.Directory]::CreateDirectory($path)
        }
    }

    return [pscustomobject]$result
}

function New-BackupChecksumsText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [object[]]$Entries
    )

    $lines = foreach ($entry in $Entries) {
        $sha256Property = $entry.PSObject.Properties['Sha256']
        $relativePathProperty = $entry.PSObject.Properties['RelativePath']
        $sha256 = if ($sha256Property) { $sha256Property.Value } else { $null }
        $relativePath = if ($relativePathProperty) { $relativePathProperty.Value } else { $null }
        if ([string]::IsNullOrWhiteSpace([string]$sha256) -or [string]::IsNullOrWhiteSpace([string]$relativePath)) {
            throw [System.ArgumentException]::new('INTBK-6002: checksum entries require Sha256 and RelativePath.')
        }

        "{0}  {1}" -f $sha256, $relativePath
    }

    return ($lines -join [Environment]::NewLine)
}

function New-BackupChecksumsFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    $path = Get-BackupFileFieldValue -Request $Request -Name 'Path'
    if (-not $Request.ContainsKey('Entries') -or @($Request['Entries']).Count -eq 0) {
        throw [System.ArgumentException]::new('INTBK-6002: Entries is required to build checksums.txt.')
    }

    $content = New-BackupChecksumsText -Entries @($Request['Entries'])
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($path, $content + [Environment]::NewLine, $encoding)

    return [pscustomobject]([ordered]@{
            path       = $path
            lineCount  = @($Request['Entries']).Count
            fileName   = 'checksums.txt'
            characters = $content.Length
        })
}

function Remove-ExpiredBackupDirectories {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [switch]$AllowDelete
    )

    $rootPath = Get-BackupFileFieldValue -Request $Request -Name 'RootPath'
    if (-not $Request.ContainsKey('KeepDays')) {
        throw [System.ArgumentException]::new('INTBK-6002: KeepDays is required for backup cleanup planning.')
    }

    $keepDays = [int]$Request['KeepDays']
    $cutoff = (Get-Date).AddDays(-1 * $keepDays)
    $directories = @(Get-ChildItem -LiteralPath $rootPath -Directory -ErrorAction SilentlyContinue)
    $candidates = @(
        $directories | Where-Object {
            $_.LastWriteTime -lt $cutoff -and $_.Name -match '^\d{8}-\d{6}$'
        }
    )

    if (-not $AllowDelete) {
        return [pscustomobject]([ordered]@{
                operation = 'cleanup-backups'
                status    = 'planned'
                code      = 'INTBK-0000'
                rootPath  = $rootPath
                keepDays  = $keepDays
                count     = $candidates.Count
                targets   = @($candidates | ForEach-Object { $_.FullName })
            })
    }

    foreach ($directory in $candidates) {
        Remove-Item -LiteralPath $directory.FullName -Recurse -Force
    }

    return [pscustomobject]([ordered]@{
            operation = 'cleanup-backups'
            status    = 'success'
            code      = 'INTBK-0000'
            rootPath  = $rootPath
            keepDays  = $keepDays
            count     = $candidates.Count
        })
}

function Assert-BackupOpsRemoteRetentionRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    $normalized = $RootPath.TrimEnd('/')
    if ($normalized -ne '/mnt/nas/Backup/BackupPackage') {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2003' -Message (New-BackupOpsOperatorBlockedMessage -Reason "远端保留策略根目录必须是 /mnt/nas/Backup/BackupPackage，当前为：$RootPath" -Action '停止清理；请先修正 backupPointsRoot，禁止清理 ReleasePackage、/mnt/nas 根目录或其他业务目录。'))
    }
}

function New-BackupOpsRemoteRetentionPythonScript {
    return @'
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

EXPECTED_ROOT = "/mnt/nas/Backup/BackupPackage"
BACKUP_POINT_RE = re.compile(r"^\d{8}-\d{6}$")
OBJECT_INVENTORY_RELATIVE_PATH = "objects/manifest-object-inventory.json"
BACKUP_MANIFEST_RELATIVE_PATH = "manifest/manifest.json"

def emit(payload, exit_code=0):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    sys.exit(exit_code)

def blocked(message):
    emit({
        "operation": "remote-cleanup",
        "status": "blocked",
        "code": "INTBK-2003",
        "message": message
    }, 2)

root = Path(os.environ["BACKUP_ROOT"]).resolve()
if str(root) != EXPECTED_ROOT:
    blocked(f"Remote retention root must be {EXPECTED_ROOT}; got {root}")
if not root.is_dir():
    blocked(f"Remote retention root does not exist or is not a directory: {root}")

keep_days = int(os.environ["KEEP_DAYS"])
keep_last = int(os.environ.get("KEEP_LAST_POINTS", "0") or "0")
max_nas_used_percent = int(os.environ.get("MAX_NAS_USED_PERCENT", "0") or "0")
action = os.environ.get("RETENTION_ACTION", "delete")
if keep_days < 0:
    blocked("KEEP_DAYS must be non-negative")
if keep_last < 0:
    blocked("KEEP_LAST_POINTS must be non-negative")
if action not in {"plan", "delete"}:
    blocked(f"Unsupported RETENTION_ACTION: {action}")

def capacity_snapshot():
    stat = os.statvfs(str(root))
    total = stat.f_blocks * stat.f_frsize
    available = stat.f_bavail * stat.f_frsize
    used = total - available
    used_percent = None if total <= 0 else round((used * 100.0) / total, 4)
    return {
        "totalBytes": total,
        "availableBytes": available,
        "usedBytes": used,
        "usedPercent": used_percent,
        "thresholdExceeded": bool(max_nas_used_percent and used_percent is not None and used_percent >= max_nas_used_percent)
    }

def backup_points():
    points = []
    for item in root.iterdir():
        if item.is_dir() and BACKUP_POINT_RE.match(item.name):
            points.append(item)
    return sorted(points, key=lambda p: p.name, reverse=True)

def object_blobs():
    store = root / "object-store"
    if not store.exists():
        return []
    return [p for p in store.rglob("*") if p.is_file()]

def repository_key(value):
    if not value:
        return None
    key = str(value).replace("\\", "/").strip("/")
    if not key or key.startswith("/") or "\x00" in key or ".." in key.split("/"):
        return None
    return key

def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        blocked(f"Invalid manifest JSON: {path}: {exc}")

def referenced_repository_keys(retained_points):
    keys = set()
    for point in retained_points:
        for relative_path in (OBJECT_INVENTORY_RELATIVE_PATH, BACKUP_MANIFEST_RELATIVE_PATH):
            manifest_path = point / relative_path
            manifest = load_json(manifest_path)
            if not manifest:
                continue
            for item in manifest.get("objects", []) or []:
                if not isinstance(item, dict):
                    continue
                key = repository_key(item.get("repositoryKey") or item.get("sha256"))
                if key:
                    keys.add(key)
    return keys

def state_snapshot():
    blobs = object_blobs()
    return {
        "backupPointCount": len(backup_points()),
        "objectBlobCount": len(blobs),
        "objectStoreBytes": sum(p.stat().st_size for p in blobs)
    }

before = state_snapshot()
capacity_before = capacity_snapshot()
points = backup_points()
recent_retained = {p.name for p in points[:keep_last]} if keep_last > 0 else set()
cutoff = datetime.now().timestamp() - (keep_days * 86400)
time_retained = {p.name for p in points if p.stat().st_mtime >= cutoff}
retained_names = recent_retained | time_retained
retained_points = [p for p in points if p.name in retained_names]
delete_points = [p for p in points if p.name not in retained_names]
referenced = referenced_repository_keys(retained_points)
store = root / "object-store"
delete_blobs = []
for blob in object_blobs():
    relative = blob.relative_to(store).as_posix()
    if relative not in referenced:
        delete_blobs.append(blob)

if action == "delete":
    for point in delete_points:
        shutil.rmtree(point)
    for blob in delete_blobs:
        blob.unlink()
    if store.exists():
        for directory in sorted([p for p in store.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass

after = state_snapshot()
capacity_after = capacity_snapshot()
deleted_object_blob_names = [p.relative_to(store).as_posix() for p in delete_blobs]
emit({
    "operation": "remote-cleanup",
    "status": "success",
    "code": "INTBK-0000",
    "action": action,
    "rootPath": str(root),
    "keepDays": keep_days,
    "keepLast": keep_last,
    "maxNasUsedPercent": max_nas_used_percent,
    "before": before,
    "after": after,
    "capacityBefore": capacity_before,
    "capacityAfter": capacity_after,
    "retainedBackupPoints": sorted(retained_names, reverse=True),
    "deletedBackupPoints": [p.name for p in delete_points],
    "deletedObjectBlobCount": len(deleted_object_blob_names),
    "deletedObjectBlobSample": deleted_object_blob_names[:50],
    "referencedObjectCount": len(referenced)
})
'@
}

function Get-BackupOpsWorkspaceRoot {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config
    )

    return [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'localWorkspaceRoot') -Code 'INTBK-2002' -Reason '缺少本地备份工作目录配置。' -Action '请先补齐 backup.localWorkspaceRoot 后再执行备份。')
}

function New-BackupOpsBackupWorkspace {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [string]$BackupType
    )

    $backupId = Get-Date -Format 'yyyyMMdd-HHmmss'
    $layout = New-BackupWorkingDirectory -Request @{
        BackupId = $backupId
        RootPath = (Get-BackupOpsWorkspaceRoot -Config $Config)
    } -CreateOnDisk

    return [pscustomobject]@{
        BackupId     = $backupId
        BackupType   = $BackupType
        Action       = $Action
        ImageTag     = 'unknown'
        BackupRoot   = $layout.backupRoot
        MySqlPath    = $layout.mysql
        ObjectsPath  = $layout.objects
        DeployPath   = $layout.deploy
        ManifestPath = $layout.manifest
    }
}

function Save-BackupOpsDeployMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $prodRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'production' -Code 'INTBK-2003'
    $appDir = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-2003' -Reason '缺少正式运行目录配置。' -Action '请先补齐 servers.production.appDir 后再执行备份。')
    $composePath = ($appDir.TrimEnd('/')) + '/docker-compose.yml'
    $envPath = ($appDir.TrimEnd('/')) + '/.env'

    Receive-BackupFileOverSsh -Request ($prodRequest + @{
        RemotePath = $composePath
        LocalPath = (Join-Path $Workspace.DeployPath 'docker-compose.yml')
    }) | Out-Null
    Receive-BackupFileOverSsh -Request ($prodRequest + @{
        RemotePath = $envPath
        LocalPath = (Join-Path $Workspace.DeployPath 'runtime.env')
    }) | Out-Null

    [System.IO.File]::WriteAllText((Join-Path $Workspace.DeployPath 'image-tag.txt'), $Workspace.ImageTag + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Write-BackupOpsLog -Session $LogSession -Message "Fetched deploy metadata from production runtime into $($Workspace.DeployPath)."
}

function Read-BackupOpsObjectInventoryMarker {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Workspace
    )

    if (-not $Workspace.PSObject.Properties['ObjectsPath'] -or [string]::IsNullOrWhiteSpace([string]$Workspace.ObjectsPath)) {
        return $null
    }
    $inventoryPath = Join-Path $Workspace.ObjectsPath 'manifest-object-inventory.json'
    if (-not (Test-Path -LiteralPath $inventoryPath -PathType Leaf)) {
        return $null
    }
    return [System.IO.File]::ReadAllText($inventoryPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
}

function Assert-BackupOpsManifestRemoteMySqlDumpPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Replace('\', '/')
    if (-not $normalized.StartsWith('/mnt/nas/Backup/BackupPackage/', [System.StringComparison]::Ordinal)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 远端 dump 不在测试服 BackupPackage 目录下：$Path。" -Action '请确认 MySQL dump 直接写入 /mnt/nas/Backup/BackupPackage/<backupId>/mysql 后再生成 manifest。'))
    }
    if ($normalized -match '(^|/)\.\.($|/)') {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 远端 dump 路径包含非法上级目录引用：$Path。" -Action '请使用 BackupPackage 下的合法备份点路径。'))
    }
    if ($normalized -like '*/ReleasePackage/*') {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "MySQL 远端 dump 指向 ReleasePackage：$Path。" -Action '数据备份 manifest 只能引用 BackupPackage 下的数据备份。'))
    }
}

function Test-BackupOpsMySqlDumpAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [string]$LocalRelativePath
    )

    $backupRoot = if ($Workspace.PSObject.Properties['BackupRoot'] -and -not [string]::IsNullOrWhiteSpace([string]$Workspace.BackupRoot)) {
        [string]$Workspace.BackupRoot
    } else {
        Split-Path -Parent ([string]$Workspace.DeployPath)
    }
    if (Test-Path -LiteralPath (Join-Path $backupRoot $LocalRelativePath) -PathType Leaf) {
        return $true
    }

    if (-not $Workspace.PSObject.Properties['RemoteMySqlDumpPath'] -or [string]::IsNullOrWhiteSpace([string]$Workspace.RemoteMySqlDumpPath)) {
        return $false
    }

    $remoteDumpPath = [string]$Workspace.RemoteMySqlDumpPath
    Assert-BackupOpsManifestRemoteMySqlDumpPath -Path $remoteDumpPath
    Import-BackupOpsSshDependency
    $testRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'test' -Code 'INTBK-6001'
    if ([string]$testRequest.Host -ne '172.30.30.58') {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "无法证明 MySQL 远端 dump 位于测试服务器 172.30.30.58：$($testRequest.Host)。" -Action '请显式使用 targetEnvironment=test，并确认测试服务器主机固定为 172.30.30.58。'))
    }
    try {
        Invoke-BackupSshCommand -Request ($testRequest + @{
            Command = "test -s {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteDumpPath)
        }) | Out-Null
    } catch {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "无法证明 MySQL 远端 dump 已写入且非空：$remoteDumpPath。" -Action '请重新执行测试服备份，确保 dump 写入 BackupPackage 后再生成 manifest。'))
    }
    return $true
}

function New-BackupOpsManifest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [string]$BackupType,
        [string]$Status = 'success',
        [hashtable]$Validation = $null,
        [string]$OperatorName = '',
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    if ($null -eq $Validation) {
        $Validation = if ($Status -eq 'success') {
            @{
                mysqlDumpCreated = $true
                objectBackupCreated = $true
                checksumsGenerated = $true
                syncedToTestServer = $false
            }
        } else {
            @{
                mysqlDumpCreated = $false
                objectBackupCreated = $false
                checksumsGenerated = $false
                syncedToTestServer = $false
            }
        }
    }

    $targetEnvironment = if ($Config.PSObject.Properties['environment']) { [string]$Config.environment } else { '' }
    $targetHost = if ($Config.PSObject.Properties['servers'] -and $Config.servers.PSObject.Properties['production'] -and $Config.servers.production.PSObject.Properties['host']) {
        [string]$Config.servers.production.host
    } else {
        ''
    }
    if ($Status -eq 'success') {
        Assert-BackupOpsKnownBackupTarget -Environment $targetEnvironment -Host $targetHost -Code 'INTBK-1003' -Scope '成功 manifest'
    }

    $runtimeEnvPath = Join-Path $Workspace.DeployPath 'runtime.env'
    $backendPort = Get-BackupOpsRequiredManifestRuntimePort -RuntimeEnvPath $runtimeEnvPath -Key 'BACKEND_HOST_PORT'
    $frontendPort = Get-BackupOpsRequiredManifestRuntimePort -RuntimeEnvPath $runtimeEnvPath -Key 'FRONTEND_HOST_PORT'
    $backupRoot = if ($Workspace.PSObject.Properties['BackupRoot'] -and -not [string]::IsNullOrWhiteSpace([string]$Workspace.BackupRoot)) {
        [string]$Workspace.BackupRoot
    } else {
        Split-Path -Parent ([string]$Workspace.DeployPath)
    }
    $databaseName = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-6001' -Reason '缺少 MySQL 数据库配置，无法生成恢复集 manifest。' -Action '请先补齐 backup.mysqlDatabase 后再生成 manifest。')
    $bucket = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'objectBucket') -Code 'INTBK-6001' -Reason '缺少对象桶配置，无法生成恢复集 manifest。' -Action '请先补齐 backup.objectBucket 后再生成 manifest。')
    $mysqlBackupMode = Assert-BackupOpsMySqlBackupModeSupported -Config $Config -Status $Status
    $mysqlDumpRelativePath = "mysql/$databaseName.sql.gz"
    $objectInventoryRelativePath = 'objects/manifest-object-inventory.json'
    $dccBackupManifestRelativePath = 'manifest/dcc-backup-manifest.json'
    $minioSnapshotRelativePath = $objectInventoryRelativePath
    $businessFilesRelativePath = $objectInventoryRelativePath
    $configurationManifestRelativePath = 'deploy/runtime.env'
    $configurationComposeRelativePath = 'deploy/docker-compose.yml'
    $checksumsRelativePath = 'manifest/checksums.txt'
    $requiredRecoveryFiles = @(
        $configurationManifestRelativePath,
        $configurationComposeRelativePath,
        $dccBackupManifestRelativePath,
        $checksumsRelativePath
    )
    $dccBackupManifestFullPath = Join-Path $backupRoot $dccBackupManifestRelativePath
    if ($Status -eq 'success' -and -not (Test-Path -LiteralPath $dccBackupManifestFullPath -PathType Leaf)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 不存在：$dccBackupManifestFullPath。" -Action '请先生成 manifest/dcc-backup-manifest.json，证明 DCC 数据库记录、对象 inventory、增量事件和恢复点语义后再生成成功备份 manifest。'))
    }
    $objectInventory = Read-BackupOpsObjectInventoryMarker -Workspace $Workspace
    $inventoryObjects = @()
    $objectDeltaStats = [pscustomobject]@{
        addedCount = 0
        modifiedCount = 0
        deletedCount = 0
        reusedCount = 0
    }
    $incrementalObjectSnapshotComplete = $false
    if ($null -ne $objectInventory) {
        try {
            $inventoryObjects = @($objectInventory.objects)
            if ($objectInventory.PSObject.Properties['stats'] -and $null -ne $objectInventory.stats) {
                $objectDeltaStats = $objectInventory.stats
            }
            $incrementalObjectSnapshotComplete = [string]$objectInventory.mode -eq 'incremental-manifest' `
                -and [string]$objectInventory.bucket -eq $bucket `
                -and -not [string]::IsNullOrWhiteSpace([string]$objectInventory.objectStoreRoot)
        } catch {
            $incrementalObjectSnapshotComplete = $false
        }
    }
    $recoverySetComplete = $true
    foreach ($relativePath in $requiredRecoveryFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $backupRoot $relativePath) -PathType Leaf)) {
            $recoverySetComplete = $false
        }
    }
    if (-not (Test-BackupOpsMySqlDumpAvailable -Config $Config -Workspace $Workspace -LocalRelativePath $mysqlDumpRelativePath)) {
        $recoverySetComplete = $false
    }
    if (-not $incrementalObjectSnapshotComplete) {
        $recoverySetComplete = $false
    }
    $checksumsHash = ''
    $checksumsFullPath = Join-Path $backupRoot $checksumsRelativePath
    if (Test-Path -LiteralPath $checksumsFullPath -PathType Leaf) {
        $checksumsHash = (Get-FileHash -LiteralPath $checksumsFullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    $model = New-BackupManifestModel -Request @{
        BackupId      = $Workspace.BackupId
        BackupType    = $BackupType
        Environment   = $targetEnvironment
        TargetEnvironment = $targetEnvironment
        TargetHost    = $targetHost
        Status        = $Status
        ObjectSnapshotPath = $objectInventoryRelativePath
        DccBackupManifestPath = $dccBackupManifestRelativePath
        StartedAt     = ([System.DateTimeOffset]$LogSession.startedAt).ToString('o')
        CompletedAt   = ([System.DateTimeOffset]::Now).ToString('o')
        Source        = [pscustomobject]@{
            serverHost = $targetHost
            appDir     = $Config.servers.production.appDir
            minioBucket = $Config.backup.objectBucket
        }
        Deploy        = [pscustomobject]@{
            imageTag     = $Workspace.ImageTag
            backendPort  = $backendPort
            frontendPort = $frontendPort
        }
        RecoverySet   = [pscustomobject]@{
            id = $Workspace.BackupId
            status = if ($recoverySetComplete) { 'COMPLETE' } else { 'BLOCKED' }
            program = [pscustomobject]@{
                imageTag = $Workspace.ImageTag
            }
            mysql = [pscustomobject]@{
                dumpPath = $mysqlDumpRelativePath
            }
            minio = [pscustomobject]@{
                bucket = $bucket
                snapshotPath = $minioSnapshotRelativePath
            }
            businessFiles = [pscustomobject]@{
                snapshotPath = $businessFilesRelativePath
            }
            dcc = [pscustomobject]@{
                manifestPath = $dccBackupManifestRelativePath
            }
            redis = [pscustomobject]@{
                policy = 'CLEAR_AND_REBUILD'
            }
            configuration = [pscustomobject]@{
                manifestPath = $configurationManifestRelativePath
                composePath = $configurationComposeRelativePath
            }
            checksums = [pscustomobject]@{
                path = $checksumsRelativePath
                sha256 = $checksumsHash
            }
        }
        BackupStrategy = [pscustomobject]@{
            mode = 'incremental-manifest'
            mysqlBackupMode = $mysqlBackupMode
            mysqlBaseline = 'full-dump'
            mysqlIncrementalPlan = [pscustomobject]@{
                binlog = [pscustomobject]@{
                    status = 'requires-prerequisite'
                    required = @('log_bin=ON', 'ROW binlog_format', 'REPLICATION CLIENT or equivalent binlog read permission', 'mysqlbinlog available')
                    failFastRule = 'Do not claim binlog incremental backup until every prerequisite is proven on the target environment.'
                }
                xtrabackup = [pscustomobject]@{
                    status = 'requires-prerequisite'
                    required = @('Percona XtraBackup installed', 'physical backup volume path available', 'backup user has required privileges', 'restore rehearsal storage sized for physical backup')
                    failFastRule = 'Do not claim physical incremental backup until dependency and privilege checks pass.'
                }
                noFallbackRule = 'No silent full dump fallback is allowed for an incremental MySQL backup request.'
            }
        }
        RetentionPolicy = [pscustomobject]@{
            keepDays = if ($Config.backup.PSObject.Properties['keepDaysRemote']) { [int]$Config.backup.keepDaysRemote } else { $null }
            keepLast = if ($Config.backup.PSObject.Properties['keepLastPoints']) { [int]$Config.backup.keepLastPoints } else { $null }
            maxNasUsedPercent = if ($Config.backup.PSObject.Properties['maxNasUsedPercent']) { [int]$Config.backup.maxNasUsedPercent } else { $null }
        }
        ObjectDeltaStats = $objectDeltaStats
        Objects = @($inventoryObjects)
        Validation    = $Validation
        OperatorMode  = 'system'
        OperatorName  = $(if ([string]::IsNullOrWhiteSpace($OperatorName)) { 'operator' } else { $OperatorName })
    }
    $manifestPath = Join-Path $Workspace.ManifestPath 'manifest.json'
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($manifestPath, ($model | ConvertTo-Json -Depth 8), $encoding)
    Write-BackupOpsLog -Session $LogSession -Message "Generated manifest.json at $manifestPath with status $Status."
    return $manifestPath
}

function Import-BackupOpsDccManifestDependencies {
    foreach ($moduleName in @('DccDatabaseSnapshotExporter.psm1', 'DccBackupManifestBuilder.psm1')) {
        $modulePath = Join-Path (Join-Path $PSScriptRoot '..\Core') $moduleName
        if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
            throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "缺少 DCC 备份依赖模块：$modulePath。" -Action '请确认 backup-ops Core 模块完整后再执行备份。'))
        }
        Import-Module $modulePath -Force -DisableNameChecking -ErrorAction Stop | Out-Null
    }
}

function Assert-BackupOpsDccBackupManifestReady {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $backupRoot = if ($Workspace.PSObject.Properties['BackupRoot'] -and -not [string]::IsNullOrWhiteSpace([string]$Workspace.BackupRoot)) {
        [string]$Workspace.BackupRoot
    } else {
        Split-Path -Parent ([string]$Workspace.DeployPath)
    }
    $relativePath = 'manifest/dcc-backup-manifest.json'
    $manifestPath = Join-Path $backupRoot $relativePath
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 不存在：$manifestPath。" -Action '请先根据 DCC 数据库快照和对象 inventory 生成 manifest/dcc-backup-manifest.json，再生成 checksums 或同步备份点。'))
    }

    try {
        $manifest = [System.IO.File]::ReadAllText($manifestPath, $script:BackupOpsUtf8NoBom) | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 不是合法 JSON：$manifestPath。" -Action '请重新生成 DCC backup manifest，禁止用空文件或手工占位文件继续备份。'))
    }

    if ([string]$manifest.schemaVersion -ne 'dcc-backup-manifest-v1' -or [string]$manifest.status -ne 'success') {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 状态无效：schemaVersion=$($manifest.schemaVersion), status=$($manifest.status)。" -Action '请先修复 DCC backup manifest 生成失败原因，必须得到 dcc-backup-manifest-v1 success 后再继续。'))
    }
    Assert-BackupOpsKnownBackupTarget -Environment ([string]$manifest.targetEnvironment) -Host ([string]$manifest.targetHost) -Code 'INTBK-6001' -Scope 'DCC 备份 manifest'
    $recordCount = if ($manifest.PSObject.Properties['databaseRecords'] -and $null -ne $manifest.databaseRecords) { @($manifest.databaseRecords).Count } else { 0 }
    if ($recordCount -le 0) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 未包含数据库记录：$manifestPath。" -Action '请先通过真实测试租户前端路径产生或选择 DCC 受控文件数据，再重新导出 DCC 快照并生成 manifest。'))
    }

    Write-BackupOpsLog -Session $LogSession -Message "DCC backup manifest ready at $manifestPath."
    return $manifestPath
}

function Get-BackupOpsDccManifestLastRestorePointId {
    param([object]$Manifest)

    $last = ''
    if ($null -ne $Manifest -and $Manifest.PSObject.Properties['incrementalChain']) {
        foreach ($segment in @($Manifest.incrementalChain)) {
            if ($null -ne $segment -and $segment.PSObject.Properties['to'] -and -not [string]::IsNullOrWhiteSpace([string]$segment.to)) {
                $last = [string]$segment.to
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($last)) {
        return $last
    }
    if ($null -ne $Manifest -and $Manifest.PSObject.Properties['fullBaseline'] -and $null -ne $Manifest.fullBaseline -and
        $Manifest.fullBaseline.PSObject.Properties['restorePointId']) {
        return [string]$Manifest.fullBaseline.restorePointId
    }
    return ''
}

function Test-BackupOpsDccPreviousManifestUsable {
    param([Parameter(Mandatory = $true)][string]$Path)

    try {
        $manifest = [System.IO.File]::ReadAllText($Path, $script:BackupOpsUtf8NoBom) | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return $false
    }
    $schemaVersion = if ($manifest.PSObject.Properties['schemaVersion']) { [string]$manifest.schemaVersion } else { '' }
    $status = if ($manifest.PSObject.Properties['status']) { [string]$manifest.status } else { '' }
    if ($schemaVersion -ne 'dcc-backup-manifest-v1' -or $status -ne 'success') {
        return $false
    }
    $restorePointId = Get-BackupOpsDccManifestLastRestorePointId -Manifest $manifest
    return -not [string]::IsNullOrWhiteSpace($restorePointId)
}

function Resolve-BackupOpsPreviousDccBackupManifestPath {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace
    )

    $explicitPath = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccPreviousManifestPath')
    if (-not [string]::IsNullOrWhiteSpace([string]$explicitPath)) {
        if (-not (Test-Path -LiteralPath ([string]$explicitPath) -PathType Leaf)) {
            throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "显式指定的上一份 DCC backup manifest 不存在：$explicitPath。" -Action '请修正 backup.dccPreviousManifestPath，或移除该配置让备份流程自动从本地备份根目录查找上一恢复点。'))
        }
        if (-not (Test-BackupOpsDccPreviousManifestUsable -Path ([string]$explicitPath))) {
            throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "显式指定的上一份 DCC backup manifest 不可作为增量链起点：$explicitPath。" -Action '请提供 schemaVersion=dcc-backup-manifest-v1、status=success 且包含 fullBaseline 或 incrementalChain 恢复点的 manifest。'))
        }
        return [string]$explicitPath
    }

    $workspaceRoot = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'localWorkspaceRoot')
    if ($null -eq $workspaceRoot -or [string]::IsNullOrWhiteSpace([string]$workspaceRoot) -or -not (Test-Path -LiteralPath ([string]$workspaceRoot) -PathType Container)) {
        return ''
    }

    $currentBackupId = [string]$Workspace.BackupId
    $previousCandidates = @(
        Get-ChildItem -LiteralPath ([string]$workspaceRoot) -Directory -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '^\d{8}-\d{6}$' -and $_.Name -lt $currentBackupId
            } |
            Sort-Object Name -Descending
    )
    foreach ($candidate in $previousCandidates) {
        $candidateManifest = Join-Path $candidate.FullName 'manifest\dcc-backup-manifest.json'
        if ((Test-Path -LiteralPath $candidateManifest -PathType Leaf) -and (Test-BackupOpsDccPreviousManifestUsable -Path $candidateManifest)) {
            return $candidateManifest
        }
    }

    return ''
}

function Get-BackupOpsDccMySqlRootPassword {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [hashtable]$SshRequest
    )

    $appDir = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'production', 'appDir') -Code 'INTBK-6001' -Reason '缺少测试运行目录配置，无法读取 MySQL 凭据。' -Action '请补齐 servers.production.appDir，并确认当前配置指向测试服务器运行目录。')
    $envPath = ($appDir.TrimEnd('/')) + '/.env'
    $result = Invoke-BackupSshCommand -Request ($SshRequest + @{
        Command = "cat {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $envPath)
        TimeoutSeconds = 60
    })
    $lines = @($result.output -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $password = Get-BackupOpsFileDotEnvValue -Lines $lines -Key 'MYSQL_ROOT_PASSWORD'
    if ([string]::IsNullOrWhiteSpace($password)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "测试运行配置缺少 MYSQL_ROOT_PASSWORD：$envPath。" -Action '请先补齐测试环境 MySQL 凭据来源，再生成 DCC 数据库快照。'))
    }

    return $password
}

function Invoke-BackupOpsDccRemoteSnapshotQuery {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [long]$TenantId,
        [Parameter(Mandatory = $true)]
        [string]$TargetHost,
        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    Import-BackupOpsSshDependency
    $sshRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'production' -Code 'INTBK-6001'
    if ([string]$sshRequest.Host -ne $TargetHost) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 数据库快照 SSH 主机与目标主机证明不一致：sshHost=$($sshRequest.Host), targetHost=$TargetHost。" -Action '请修正测试环境运行配置，确保 DCC 查询只访问 172.30.30.58。'))
    }

    $containerName = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('containers', 'mysql') -Code 'INTBK-6001' -Reason '缺少 MySQL 容器名，无法执行 DCC 只读快照查询。' -Action '请补齐 containers.mysql 后再执行备份。')
    $databaseName = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'mysqlDatabase') -Code 'INTBK-6001' -Reason '缺少 MySQL 数据库名，无法执行 DCC 只读快照查询。' -Action '请补齐 backup.mysqlDatabase 后再执行备份。')
    $rootPassword = Get-BackupOpsDccMySqlRootPassword -Config $Config -SshRequest $sshRequest
    $sql = New-DccDatabaseSnapshotSql -TenantId $TenantId

    $command = "docker exec {0} mysql --batch --raw --default-character-set=utf8mb4 -uroot -p{1} {2} -e {3}" -f `
        (ConvertTo-BackupBashSingleQuotedString -Value $containerName), `
        (ConvertTo-BackupBashSingleQuotedString -Value $rootPassword), `
        (ConvertTo-BackupBashSingleQuotedString -Value $databaseName), `
        (ConvertTo-BackupBashSingleQuotedString -Value $sql)

    $queryResult = Invoke-BackupSshCommand -Request ($sshRequest + @{
        Command = $command
        TimeoutSeconds = 300
    })
    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [void][System.IO.Directory]::CreateDirectory($parent)
    }
    [System.IO.File]::WriteAllText($OutputPath, [string]$queryResult.output, $script:BackupOpsUtf8NoBom)
    return $OutputPath
}

function New-BackupOpsDccDatabaseSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [long]$TenantId,
        [Parameter(Mandatory = $true)]
        [string]$TargetHost,
        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    $queryJsonPath = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotQueryResultPath')
    $queryCsvPath = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotQueryCsvPath')
    $mysqlCliOutputPath = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotMySqlCliOutputPath')
    $databaseHost = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDatabaseHost')
    $databasePort = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDatabasePort')
    $databaseName = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDatabaseName')
    $mysqlPath = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotMySqlPath')
    $databaseUser = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDatabaseUser')
    $databasePassword = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDatabasePassword')
    $defaultsExtraFile = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('backup', 'dccSnapshotDefaultsExtraFile')
    $targetEnvironment = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('environment')
    if ([string]::IsNullOrWhiteSpace([string]$targetEnvironment)) {
        $targetEnvironment = 'production'
    }

    if (-not [string]::IsNullOrWhiteSpace([string]$queryJsonPath)) {
        return Invoke-DccDatabaseSnapshotExport -TargetEnvironment ([string]$targetEnvironment) -TargetHost $TargetHost -TenantId $TenantId -QueryResultJsonPath ([string]$queryJsonPath) -OutputPath $OutputPath
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$queryCsvPath)) {
        return Invoke-DccDatabaseSnapshotExport -TargetEnvironment ([string]$targetEnvironment) -TargetHost $TargetHost -TenantId $TenantId -QueryResultCsvPath ([string]$queryCsvPath) -OutputPath $OutputPath
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$mysqlCliOutputPath)) {
        return Invoke-DccDatabaseSnapshotExport -TargetEnvironment ([string]$targetEnvironment) -TargetHost $TargetHost -TenantId $TenantId -MySqlCliOutputPath ([string]$mysqlCliOutputPath) -OutputPath $OutputPath
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$databaseHost) -and
        -not [string]::IsNullOrWhiteSpace([string]$databasePort) -and
        -not [string]::IsNullOrWhiteSpace([string]$databaseName) -and
        -not [string]::IsNullOrWhiteSpace([string]$mysqlPath)) {
        return Invoke-DccDatabaseSnapshotExport `
            -TargetEnvironment ([string]$targetEnvironment) `
            -TargetHost $TargetHost `
            -TenantId $TenantId `
            -DatabaseHost ([string]$databaseHost) `
            -DatabasePort ([int]$databasePort) `
            -DatabaseName ([string]$databaseName) `
            -MySqlPath ([string]$mysqlPath) `
            -DatabaseUser ([string]$databaseUser) `
            -DatabasePassword ([string]$databasePassword) `
            -DefaultsExtraFile ([string]$defaultsExtraFile) `
            -OutputPath $OutputPath
    }

    $queryOutputPath = Join-Path (Split-Path -Parent $OutputPath) 'dcc-database-query.tsv'
    $generatedQueryPath = Invoke-BackupOpsDccRemoteSnapshotQuery -Config $Config -TenantId $TenantId -TargetHost $TargetHost -OutputPath $queryOutputPath
    return Invoke-DccDatabaseSnapshotExport -TargetEnvironment ([string]$targetEnvironment) -TargetHost $TargetHost -TenantId $TenantId -MySqlCliOutputPath $generatedQueryPath -OutputPath $OutputPath
}

function New-BackupOpsDccBackupManifest {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $targetEnvironment = Get-BackupOpsFileConfigValueSafe -InputObject $Config -Path @('environment')
    if ([string]::IsNullOrWhiteSpace([string]$targetEnvironment)) {
        $targetEnvironment = 'production'
    }

    $targetHost = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'production', 'host') -Code 'INTBK-6001' -Reason '缺少 DCC 备份源主机证明。' -Action '请补齐 servers.production.host，并确认目标环境与源主机匹配。')
    Assert-BackupOpsKnownBackupTarget -Environment ([string]$targetEnvironment) -Host $targetHost -Code 'INTBK-6001' -Scope 'DCC 备份源'

    $tenantId = [long](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'dccTenantId') -Code 'INTBK-6001' -Reason '缺少 DCC 测试租户 ID，无法限定 DCC 数据库快照范围。' -Action '请配置 backup.dccTenantId 为测试租户 ID 后再执行 DCC 备份 manifest 生成。')
    $objectInventoryPath = Join-Path $Workspace.ObjectsPath 'manifest-object-inventory.json'
    if (-not (Test-Path -LiteralPath $objectInventoryPath -PathType Leaf)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象 inventory 不存在：$objectInventoryPath。" -Action '请先完成对象增量备份并生成 objects/manifest-object-inventory.json，再生成 DCC 备份 manifest。'))
    }

    Import-BackupOpsDccManifestDependencies
    [void][System.IO.Directory]::CreateDirectory([string]$Workspace.ManifestPath)
    $snapshotPath = Join-Path $Workspace.ManifestPath 'dcc-database-snapshot.json'
    $manifestPath = Join-Path $Workspace.ManifestPath 'dcc-backup-manifest.json'
    $snapshotResult = New-BackupOpsDccDatabaseSnapshot -Config $Config -Workspace $Workspace -TenantId $tenantId -TargetHost $targetHost -OutputPath $snapshotPath
    if ([int]$snapshotResult.ExitCode -ne 0) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 数据库快照导出失败，诊断已写入：$snapshotPath。" -Action '请按 dcc-database-snapshot.json 中的 errors 修复测试租户 DCC 数据、对象路径或查询配置后再执行备份。'))
    }

    $previousManifestPath = Resolve-BackupOpsPreviousDccBackupManifestPath -Config $Config -Workspace $Workspace
    if ([string]::IsNullOrWhiteSpace($previousManifestPath)) {
        $buildResult = Invoke-DccBackupManifestBuild `
            -BackupId ([string]$Workspace.BackupId) `
            -RestorePointId ([string]$Workspace.BackupId) `
            -TargetEnvironment ([string]$targetEnvironment) `
            -TargetHost $targetHost `
            -DccSnapshotPath $snapshotPath `
            -ObjectInventoryPath $objectInventoryPath `
            -OutputPath $manifestPath
    } else {
        $buildResult = Invoke-DccBackupManifestBuild `
            -BackupId ([string]$Workspace.BackupId) `
            -RestorePointId ([string]$Workspace.BackupId) `
            -TargetEnvironment ([string]$targetEnvironment) `
            -TargetHost $targetHost `
            -DccSnapshotPath $snapshotPath `
            -ObjectInventoryPath $objectInventoryPath `
            -PreviousManifestPath $previousManifestPath `
            -OutputPath $manifestPath
    }
    if ([int]$buildResult.ExitCode -ne 0) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message (New-BackupOpsOperatorBlockedMessage -Reason "DCC 备份 manifest 构建失败，诊断已写入：$manifestPath。" -Action '请按 dcc-backup-manifest.json 中的 errors 修复对象 inventory、上一恢复点 manifest 或 DCC 数据快照后再执行备份。'))
    }

    Write-BackupOpsLog -Session $LogSession -Message "Generated DCC backup manifest at $manifestPath."
    return $manifestPath
}

function New-BackupOpsChecksums {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $entries = @()
    foreach ($relativePath in @(
        'deploy/docker-compose.yml',
        'deploy/runtime.env',
        'deploy/image-tag.txt',
        'manifest/dcc-backup-manifest.json'
    )) {
        $fullPath = Join-Path $Workspace.BackupRoot $relativePath
        if (Test-Path -LiteralPath $fullPath) {
            $entries += [pscustomobject]@{
                Sha256 = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
                RelativePath = $relativePath.Replace('/', '\')
            }
        }
    }
    if ($entries.Count -eq 0) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6002' -Message 'No checksum entries were available for phase-1 backup metadata.')
    }
    $file = New-BackupChecksumsFile -Request @{
        Path = (Join-Path $Workspace.ManifestPath 'checksums.txt')
        Entries = $entries
    }
    Write-BackupOpsLog -Session $LogSession -Message "Generated checksums.txt at $($file.path)."
    return $file
}

function Sync-BackupOpsBackupToTestServer {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $testRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'test' -Code 'INTBK-2003'
    $backupPointsRoot = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-2003' -Reason '缺少测试服务器备份根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行备份。')
    $remoteTargetRoot = $backupPointsRoot.TrimEnd('/')
    $remoteBackupRoot = $remoteTargetRoot + '/' + $Workspace.BackupId
    $remoteDirectoryTimeoutSeconds = 60
    $metadataUploadTimeoutSeconds = 300
    $mysqlUploadTimeoutSeconds = 7200

    Invoke-BackupSshCommand -Request ($testRequest + @{
        Command = "mkdir -p {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteTargetRoot)
        TimeoutSeconds = $remoteDirectoryTimeoutSeconds
    }) | Out-Null
    Invoke-BackupSshCommand -Request ($testRequest + @{
        Command = "mkdir -p {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value $remoteBackupRoot)
        TimeoutSeconds = $remoteDirectoryTimeoutSeconds
    }) | Out-Null
    foreach ($childName in @('deploy', 'manifest', 'mysql', 'objects')) {
        Invoke-BackupSshCommand -Request ($testRequest + @{
            Command = "mkdir -p {0}" -f (ConvertTo-BackupBashSingleQuotedString -Value ($remoteBackupRoot + '/' + $childName))
            TimeoutSeconds = $remoteDirectoryTimeoutSeconds
        }) | Out-Null
    }

    foreach ($file in @(Get-ChildItem -LiteralPath $Workspace.DeployPath -File -ErrorAction SilentlyContinue)) {
        Send-BackupFileOverSsh -Request ($testRequest + @{
            LocalPath = $file.FullName
            RemotePath = $remoteBackupRoot + '/deploy/'
            TimeoutSeconds = $metadataUploadTimeoutSeconds
        }) | Out-Null
    }

    foreach ($file in @(Get-ChildItem -LiteralPath $Workspace.ManifestPath -File -ErrorAction SilentlyContinue)) {
        if ($file.Name -eq 'manifest.json') {
            continue
        }
        Send-BackupFileOverSsh -Request ($testRequest + @{
            LocalPath = $file.FullName
            RemotePath = $remoteBackupRoot + '/manifest/'
            TimeoutSeconds = $metadataUploadTimeoutSeconds
        }) | Out-Null
    }

    foreach ($file in @(Get-ChildItem -LiteralPath $Workspace.MySqlPath -File -ErrorAction SilentlyContinue)) {
        Send-BackupFileOverSsh -Request ($testRequest + @{
            LocalPath = $file.FullName
            RemotePath = $remoteBackupRoot + '/mysql/'
            TimeoutSeconds = $mysqlUploadTimeoutSeconds
        }) | Out-Null
    }

    $objectInventoryPath = Join-Path $Workspace.ObjectsPath 'manifest-object-inventory.json'
    if (-not (Test-Path -LiteralPath $objectInventoryPath)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象增量清单不存在：$objectInventoryPath" -Action '请先完成对象桶 manifest 增量备份后再执行备份同步。'))
    }
    $inventory = [System.IO.File]::ReadAllText($objectInventoryPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    if ([string]$inventory.mode -ne 'incremental-manifest' -or [string]::IsNullOrWhiteSpace([string]$inventory.bucket) -or [string]::IsNullOrWhiteSpace([string]$inventory.objectStoreRoot)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象增量清单无效：$objectInventoryPath" -Action '请重新执行对象桶 manifest 增量备份，确保 inventory 包含 mode、bucket 和 objectStoreRoot。'))
    }
    if (-not ([string]$inventory.objectStoreRoot).Contains('/object-store')) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2002' -Message (New-BackupOpsOperatorBlockedMessage -Reason "对象增量清单 objectStoreRoot 非法：$($inventory.objectStoreRoot)" -Action '请确认对象仓库固定写入 /mnt/nas/Backup/BackupPackage/object-store 后再执行备份同步。'))
    }
    Send-BackupFileOverSsh -Request ($testRequest + @{
        LocalPath = $objectInventoryPath
        RemotePath = $remoteBackupRoot + '/objects/manifest-object-inventory.json'
        TimeoutSeconds = $metadataUploadTimeoutSeconds
    }) | Out-Null
    Write-BackupOpsLog -Session $LogSession -Message "Synced backup point $($Workspace.BackupId) to test server path $remoteBackupRoot."
    return [pscustomobject]@{
        operation = 'sync-backup'
        status = 'success'
        code = 'INTBK-0000'
        remoteRoot = $remoteBackupRoot
        backupId = $Workspace.BackupId
    }
}

function Sync-BackupOpsManifestToTestServer {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$Workspace,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    Import-BackupOpsSshDependency
    $testRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'test' -Code 'INTBK-2003'
    $backupPointsRoot = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-2003' -Reason '缺少测试服务器备份根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再同步 manifest。')
    $remoteManifestRoot = $backupPointsRoot.TrimEnd('/') + '/' + $Workspace.BackupId + '/manifest/'
    $manifestPath = Join-Path $Workspace.ManifestPath 'manifest.json'
    $manifestUploadTimeoutSeconds = 300

    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-6001' -Message 'manifest.json 不存在，无法同步到测试服务器。')
    }

    Send-BackupFileOverSsh -Request ($testRequest + @{
        LocalPath = $manifestPath
        RemotePath = $remoteManifestRoot
        TimeoutSeconds = $manifestUploadTimeoutSeconds
    }) | Out-Null
    Write-BackupOpsLog -Session $LogSession -Message "Synced manifest.json to $remoteManifestRoot."
    return [pscustomobject]@{
        operation = 'sync-manifest'
        status = 'success'
        code = 'INTBK-0000'
        remoteRoot = $remoteManifestRoot
        backupId = $Workspace.BackupId
    }
}

function Invoke-BackupOpsLocalRetention {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $rootPath = Get-BackupOpsWorkspaceRoot -Config $Config
    $keepDays = [int](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'keepDaysLocal') -Code 'INTBK-6002' -Reason '缺少本地保留天数配置。' -Action '请先补齐 backup.keepDaysLocal 后再执行清理。')
    $result = Remove-ExpiredBackupDirectories -Request @{
        RootPath = $rootPath
        KeepDays = $keepDays
    } -AllowDelete
    Write-BackupOpsLog -Session $LogSession -Message "Local retention cleanup removed $($result.count) directories from $rootPath."
    return $result
}

function Invoke-BackupOpsRemoteRetention {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession,
        [switch]$PlanOnly
    )

    return Invoke-BackupOpsRemoteRetentionInternal -Config $Config -LogSession $LogSession -PlanOnly:$PlanOnly
}

function Invoke-BackupOpsRemoteRetentionInternal {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [object]$LogSession,
        [switch]$PlanOnly
    )

    $backupPointsRoot = [string](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('servers', 'test', 'backupPointsRoot') -Code 'INTBK-2003' -Reason '缺少测试服务器备份根目录配置。' -Action '请先补齐 servers.test.backupPointsRoot 后再执行远端清理。')
    Assert-BackupOpsRemoteRetentionRoot -RootPath $backupPointsRoot
    $keepDays = [int](Get-BackupOpsRequiredFileConfigValue -Config $Config -Path @('backup', 'keepDaysRemote') -Code 'INTBK-2003' -Reason '缺少远端保留天数配置。' -Action '请先补齐 backup.keepDaysRemote 后再执行远端清理。')
    $keepLast = if ($Config.backup.PSObject.Properties['keepLastPoints']) { [int]$Config.backup.keepLastPoints } else { 0 }
    $maxNasUsedPercent = if ($Config.backup.PSObject.Properties['maxNasUsedPercent']) { [int]$Config.backup.maxNasUsedPercent } else { 0 }
    $action = if ($PlanOnly) { 'plan' } else { 'delete' }
    $pythonScript = New-BackupOpsRemoteRetentionPythonScript
    $encodedScript = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($pythonScript))
    $command = @(
        'set -eu',
        '# retention-audit: manifest/manifest.json objects/manifest-object-inventory.json object-store repositoryKey',
        "command -v python3 >/dev/null || { echo 'python3 is required for BackupPackage retention cleanup' >&2; exit 70; }",
        "command -v base64 >/dev/null || { echo 'base64 is required for BackupPackage retention cleanup' >&2; exit 70; }",
        "export BACKUP_ROOT=$backupPointsRoot",
        "export KEEP_DAYS=$keepDays",
        "export KEEP_LAST_POINTS=$keepLast",
        "export MAX_NAS_USED_PERCENT=$maxNasUsedPercent",
        "export RETENTION_ACTION=$action",
        "printf %s $encodedScript | base64 -d | python3 -"
    ) -join "`n"

    Import-BackupOpsSshDependency
    $testRequest = Get-BackupOpsFileSshRequest -Config $Config -Environment 'test' -Code 'INTBK-2003'
    $retentionResult = Invoke-BackupSshCommand -Request ($testRequest + @{ Command = $command })
    try {
        $result = $retentionResult.output | ConvertFrom-Json
    }
    catch {
        throw (New-BackupOpsInfraBlockedException -Code 'INTBK-2003' -Message (New-BackupOpsOperatorBlockedMessage -Reason "远端保留策略未返回合法 JSON 证据：$($_.Exception.Message)" -Action '停止清理；请先确认测试服务器 python3、BackupPackage 权限和 manifest 结构。'))
    }
    $deletedObjectBlobCount = if ($result.PSObject.Properties['deletedObjectBlobCount']) { [int]$result.deletedObjectBlobCount } else { @($result.deletedObjectBlobs).Count }
    Write-BackupOpsLog -Session $LogSession -Message "Remote retention $action on test BackupPackage completed: backupPoints=$(@($result.deletedBackupPoints).Count), objectBlobs=$deletedObjectBlobCount, root=$backupPointsRoot."
    return $result
}

Export-ModuleMember -Function New-BackupDirectoryLayout, New-BackupWorkingDirectory, New-BackupChecksumsText, New-BackupChecksumsFile, Remove-ExpiredBackupDirectories, Assert-BackupOpsRemoteNasMounted, New-BackupOpsBackupWorkspace, Save-BackupOpsDeployMetadata, Read-BackupOpsObjectInventoryMarker, New-BackupOpsManifest, New-BackupOpsDccBackupManifest, Assert-BackupOpsDccBackupManifestReady, New-BackupOpsChecksums, Sync-BackupOpsBackupToTestServer, Sync-BackupOpsManifestToTestServer, Invoke-BackupOpsLocalRetention, Invoke-BackupOpsRemoteRetention
