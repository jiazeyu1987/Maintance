Set-StrictMode -Version Latest

$script:BackupOpsUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Import-BackupOpsValidationDependency {
    if (Get-Command -Name 'Assert-BackupOpsConfiguration' -ErrorAction SilentlyContinue) {
        return
    }

    $validationModulePath = Join-Path $PSScriptRoot 'Validation.psm1'
    if (-not (Test-Path -LiteralPath $validationModulePath)) {
        throw "Validation module not found: $validationModulePath"
    }

    Import-Module $validationModulePath -Force -ErrorAction Stop | Out-Null
}

function Get-BackupOpsRootPath {
    $backupOpsRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
    return $backupOpsRoot.Path
}

function Get-BackupOpsDefaultConfigPaths {
    $root = Get-BackupOpsRootPath

    return [PSCustomObject][ordered]@{
        rootPath          = $root
        configPath        = Join-Path $root 'config\backup-ops.config.json'
        secretsPath       = Join-Path $root 'config\backup-ops.secrets.json'
        configExamplePath = Join-Path $root 'config\backup-ops.config.example.json'
        secretsExamplePath = Join-Path $root 'config\backup-ops.secrets.example.json'
    }
}

function Read-BackupOpsJsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [string]$Label = 'Configuration file'
    )

    Import-BackupOpsValidationDependency
    Assert-BackupOpsFileExists -Path $Path -Label $Label

    $content = [System.IO.File]::ReadAllText($Path, $script:BackupOpsUtf8NoBom)
    return ConvertFrom-BackupOpsJsonText -Path $Path -Text $content
}

function Merge-BackupOpsConfiguration {
    param(
        [Parameter(Mandatory = $true)]
        [object]$ConfigObject,

        [Parameter(Mandatory = $true)]
        [object]$SecretsObject,

        [Parameter(Mandatory = $true)]
        [string]$ConfigPath,

        [Parameter(Mandatory = $true)]
        [string]$SecretsPath
    )

    return [PSCustomObject][ordered]@{
        schemaVersion = $ConfigObject.schemaVersion
        environment   = $ConfigObject.environment
        servers       = $ConfigObject.servers
        containers    = $ConfigObject.containers
        tools         = $ConfigObject.tools
        backup        = $ConfigObject.backup
        rehearsal     = $ConfigObject.rehearsal
        console       = $ConfigObject.console
        notify        = $ConfigObject.notify
        ssh           = $SecretsObject.ssh
        auth          = $SecretsObject.auth
        rehearsalAuth = $SecretsObject.rehearsal
        raw           = [PSCustomObject][ordered]@{
            config  = $ConfigObject
            secrets = $SecretsObject
        }
        paths         = [PSCustomObject][ordered]@{
            configPath  = $ConfigPath
            secretsPath = $SecretsPath
            loadedAt    = [System.DateTimeOffset]::Now
        }
    }
}

function Import-BackupOpsConfiguration {
    param(
        [string]$ConfigPath = '',

        [string]$SecretsPath = ''
    )

    Import-BackupOpsValidationDependency
    $defaults = Get-BackupOpsDefaultConfigPaths

    $resolvedConfigPath = if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
        $defaults.configPath
    } else {
        $ConfigPath
    }

    $resolvedSecretsPath = if ([string]::IsNullOrWhiteSpace($SecretsPath)) {
        $defaults.secretsPath
    } else {
        $SecretsPath
    }

    $config = Read-BackupOpsJsonFile -Path $resolvedConfigPath -Label 'Backup ops config'
    $secrets = Read-BackupOpsJsonFile -Path $resolvedSecretsPath -Label 'Backup ops secrets'
    Assert-BackupOpsConfiguration -ConfigObject $config -SecretsObject $secrets

    return Merge-BackupOpsConfiguration -ConfigObject $config -SecretsObject $secrets -ConfigPath $resolvedConfigPath -SecretsPath $resolvedSecretsPath
}

function Get-BackupOpsConfig {
    param(
        [string]$ConfigPath = '',
        [string]$SecretsPath = ''
    )

    return Import-BackupOpsConfiguration -ConfigPath $ConfigPath -SecretsPath $SecretsPath
}

Export-ModuleMember -Function @(
    'Get-BackupOpsConfig',
    'Get-BackupOpsDefaultConfigPaths',
    'Get-BackupOpsRootPath',
    'Import-BackupOpsConfiguration',
    'Read-BackupOpsJsonFile'
)
