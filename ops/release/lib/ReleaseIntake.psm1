Set-StrictMode -Version Latest

function Get-ReleaseIntakeTimestamp {
    return [DateTime]::UtcNow.ToString('o')
}

function ConvertTo-ReleaseIntakeArray {
    param([object]$Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Get-ReleaseIntakeProperty {
    param(
        [object]$Object,
        [string]$Name,
        [object]$Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }
    if ($Object -is [System.Collections.IDictionary] -and $Object.Contains($Name)) {
        return $Object[$Name]
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $Default
    }
    return $property.Value
}

function Test-ReleaseIntakeBlank {
    param([string]$Value)

    return [string]::IsNullOrWhiteSpace($Value)
}

function Read-ReleaseIntakeJson {
    param([string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path
    $text = [System.IO.File]::ReadAllText($resolved.Path, [System.Text.Encoding]::UTF8)
    return $text | ConvertFrom-Json
}

function Write-ReleaseIntakeJson {
    param(
        [string]$Path,
        [object]$Value
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 100
    [System.IO.File]::WriteAllText($Path, "$json`n", [System.Text.UTF8Encoding]::new($false))
}

function Get-ReleaseIntakeSha256 {
    param([string]$Text)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
        $hash = [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
        return "sha256:$hash"
    } finally {
        $sha.Dispose()
    }
}

function ConvertTo-ReleaseIntakeCanonicalJson {
    param([object]$Value)

    return ($Value | ConvertTo-Json -Depth 100 -Compress)
}

function New-ReleaseIntakeBaseResult {
    param(
        [string]$Status,
        [string]$CreatedAt,
        [array]$Errors = @(),
        [array]$Warnings = @()
    )

    return [ordered]@{
        status = $Status
        mode = 'report-only'
        buildBehavior = 'build-release'
        createdAt = $CreatedAt
        schemaDriftCount = 0
        requiredDataChangeCount = 0
        unclassifiedLocalChangeCount = 0
        resourceReferenceCount = 0
        blockingCandidateCount = 0
        reports = [ordered]@{
            changeSet = 'change-set.json'
            schemaFingerprint = 'local-schema-fingerprint.json'
            schemaChangeReport = 'schema-change-report.json'
            dataChangeManifest = 'data-change-manifest.json'
            resourceReferenceManifest = 'resource-reference-manifest.json'
        }
        errors = @($Errors)
        warnings = @($Warnings)
    }
}

function Write-ReleaseIntakeFailure {
    param(
        [string]$OutputDir,
        [string]$CreatedAt,
        [string]$Code,
        [string]$Message,
        [array]$Details = @()
    )

    $errorObject = [ordered]@{
        code = $Code
        message = $Message
    }
    if ($Details.Count -gt 0) {
        $errorObject.details = @($Details)
    }
    $result = New-ReleaseIntakeBaseResult -Status 'failed' -CreatedAt $CreatedAt -Errors @($errorObject)
    Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'intake-result.json') -Value $result
    Write-Output "Release intake failed: $Code"
    return [pscustomobject]@{
        ExitCode = 2
        Result = $result
    }
}

function Assert-ReleaseIntakePath {
    param(
        [string]$Path,
        [string]$Code,
        [string]$Message,
        [string]$OutputDir,
        [string]$CreatedAt
    )

    if (Test-ReleaseIntakeBlank $Path) {
        return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $CreatedAt -Code $Code -Message $Message
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $CreatedAt -Code $Code -Message $Message
    }
    return $null
}

function Invoke-ReleaseIntakeGit {
    param(
        [string]$RepoRoot,
        [string[]]$Arguments
    )

    $output = & git -C $RepoRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $output"
    }
    return @($output)
}

function New-ReleaseIntakeChangeSet {
    param(
        [string]$RepoRoot,
        [string]$CapturedAt
    )

    $resolvedRepo = (Resolve-Path -LiteralPath $RepoRoot).Path
    $commit = (Invoke-ReleaseIntakeGit -RepoRoot $resolvedRepo -Arguments @('rev-parse', 'HEAD') | Select-Object -First 1)
    $branch = (Invoke-ReleaseIntakeGit -RepoRoot $resolvedRepo -Arguments @('branch', '--show-current') | Select-Object -First 1)
    $dirtyFiles = @(Invoke-ReleaseIntakeGit -RepoRoot $resolvedRepo -Arguments @('status', '--short'))
    $sourceHashInput = "$commit`n$branch`n$($dirtyFiles -join "`n")"
    $sourceHash = Get-ReleaseIntakeSha256 -Text $sourceHashInput

    return [ordered]@{
        repoRoot = $resolvedRepo
        capturedAt = $CapturedAt
        sourceRepos = @(
            [ordered]@{
                name = 'ruoyi-vue-pro'
                commit = $commit
                branch = $branch
                dirtyFiles = @($dirtyFiles)
                sourceHash = $sourceHash
            }
        )
        components = @(
            [ordered]@{
                componentName = 'backend-app'
                changed = ($dirtyFiles.Count -gt 0)
                changeReasons = $(if ($dirtyFiles.Count -gt 0) { @('source-dirty') } else { @() })
            }
        )
    }
}

function Get-ReleaseIntakeTableMap {
    param([object]$SchemaFingerprint)

    $map = @{}
    foreach ($table in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $SchemaFingerprint -Name 'tables' -Default @()))) {
        $name = [string](Get-ReleaseIntakeProperty -Object $table -Name 'tableName' -Default '')
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $map[$name.ToLowerInvariant()] = $table
        }
    }
    return $map
}

function Get-ReleaseIntakeColumnMap {
    param([object]$Table)

    $map = @{}
    foreach ($column in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $Table -Name 'columns' -Default @()))) {
        $name = [string](Get-ReleaseIntakeProperty -Object $column -Name 'columnName' -Default '')
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $map[$name.ToLowerInvariant()] = $column
        }
    }
    return $map
}

function Get-ReleaseIntakeDefinitionHash {
    param([object]$Definition)

    $definitionHash = Get-ReleaseIntakeProperty -Object $Definition -Name 'definitionHash' -Default ''
    if (-not [string]::IsNullOrWhiteSpace([string]$definitionHash)) {
        return [string]$definitionHash
    }
    return Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value $Definition)
}

function New-ReleaseIntakeSchemaChangeReport {
    param(
        [object]$BaselineManifest,
        [object]$LocalSchemaFingerprint
    )

    $baselineFingerprint = Get-ReleaseIntakeProperty -Object (Get-ReleaseIntakeProperty -Object $BaselineManifest -Name 'database') -Name 'schemaFingerprint'
    if ($null -eq $baselineFingerprint) {
        throw 'Baseline manifest is missing database.schemaFingerprint.'
    }

    $changes = @()
    $baselineTables = Get-ReleaseIntakeTableMap -SchemaFingerprint $baselineFingerprint
    $localTables = Get-ReleaseIntakeTableMap -SchemaFingerprint $LocalSchemaFingerprint
    foreach ($tableKey in ($localTables.Keys | Sort-Object)) {
        $localTable = $localTables[$tableKey]
        if (-not $baselineTables.ContainsKey($tableKey)) {
            $changes += [ordered]@{
                changeType = 'added-table'
                objectType = 'table'
                tableName = [string]$localTable.tableName
                currentDefinitionHash = Get-ReleaseIntakeDefinitionHash -Definition $localTable
                baselineDefinitionHash = $null
                migrationBinding = $null
                blockingCandidate = $true
                message = 'Table exists locally but no migration binding was found.'
            }
            continue
        }

        $baselineColumns = Get-ReleaseIntakeColumnMap -Table $baselineTables[$tableKey]
        $localColumns = Get-ReleaseIntakeColumnMap -Table $localTable
        foreach ($columnKey in ($localColumns.Keys | Sort-Object)) {
            $localColumn = $localColumns[$columnKey]
            $localHash = Get-ReleaseIntakeDefinitionHash -Definition $localColumn
            if (-not $baselineColumns.ContainsKey($columnKey)) {
                $changes += [ordered]@{
                    changeType = 'added-column'
                    objectType = 'column'
                    tableName = [string]$localTable.tableName
                    columnName = [string]$localColumn.columnName
                    currentDefinitionHash = $localHash
                    baselineDefinitionHash = $null
                    migrationBinding = $null
                    blockingCandidate = $true
                    message = 'Column exists locally but no migration binding was found.'
                }
                continue
            }

            $baselineHash = Get-ReleaseIntakeDefinitionHash -Definition $baselineColumns[$columnKey]
            if ($baselineHash -ne $localHash) {
                $changes += [ordered]@{
                    changeType = 'changed-column'
                    objectType = 'column'
                    tableName = [string]$localTable.tableName
                    columnName = [string]$localColumn.columnName
                    currentDefinitionHash = $localHash
                    baselineDefinitionHash = $baselineHash
                    migrationBinding = $null
                    blockingCandidate = $true
                    message = 'Column definition differs from the baseline manifest.'
                }
            }
        }
    }

    foreach ($tableKey in ($baselineTables.Keys | Sort-Object)) {
        if (-not $localTables.ContainsKey($tableKey)) {
            $baselineTable = $baselineTables[$tableKey]
            $changes += [ordered]@{
                changeType = 'removed-table'
                objectType = 'table'
                tableName = [string]$baselineTable.tableName
                currentDefinitionHash = $null
                baselineDefinitionHash = Get-ReleaseIntakeDefinitionHash -Definition $baselineTable
                migrationBinding = $null
                blockingCandidate = $true
                message = 'Table exists in baseline but not in the local schema fingerprint.'
            }
            continue
        }

        $baselineColumns = Get-ReleaseIntakeColumnMap -Table $baselineTables[$tableKey]
        $localColumns = Get-ReleaseIntakeColumnMap -Table $localTables[$tableKey]
        foreach ($columnKey in ($baselineColumns.Keys | Sort-Object)) {
            if (-not $localColumns.ContainsKey($columnKey)) {
                $baselineColumn = $baselineColumns[$columnKey]
                $changes += [ordered]@{
                    changeType = 'removed-column'
                    objectType = 'column'
                    tableName = [string]$baselineTables[$tableKey].tableName
                    columnName = [string]$baselineColumn.columnName
                    currentDefinitionHash = $null
                    baselineDefinitionHash = Get-ReleaseIntakeDefinitionHash -Definition $baselineColumn
                    migrationBinding = $null
                    blockingCandidate = $true
                    message = 'Column exists in baseline but not in the local schema fingerprint.'
                }
            }
        }
    }

    $baselineManifestId = Get-ReleaseIntakeProperty -Object $BaselineManifest -Name 'manifestId' -Default (Get-ReleaseIntakeProperty -Object $BaselineManifest -Name 'packageId' -Default '')
    return [ordered]@{
        status = $(if ($changes.Count -gt 0) { 'warning' } else { 'passed' })
        baselineManifestId = $baselineManifestId
        schemaDriftCount = $changes.Count
        changes = @($changes)
    }
}

function Test-ReleaseIntakeDataRegistry {
    param([object]$Registry)

    $errors = @()
    foreach ($entry in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $Registry -Name 'entries' -Default @()))) {
        $entryId = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'entryId' -Default '')
        if ([string]::IsNullOrWhiteSpace($entryId)) {
            $entryId = '<missing-entry-id>'
        }
        $tenantScope = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'tenantScope' -Default '')
        if ([string]::IsNullOrWhiteSpace($tenantScope)) {
            $errors += [ordered]@{
                code = 'DATA_REGISTRY_TENANT_SCOPE_MISSING'
                entryId = $entryId
                message = 'Registry entry is missing tenantScope.'
            }
        }

        $ownedFields = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $entry -Name 'ownedFields' -Default @()))
        $forbiddenFields = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $entry -Name 'forbiddenOverwriteFields' -Default @()))
        foreach ($field in $ownedFields) {
            if ($forbiddenFields -contains $field) {
                $errors += [ordered]@{
                    code = 'DATA_REGISTRY_FIELD_OWNERSHIP_CONFLICT'
                    entryId = $entryId
                    field = [string]$field
                    message = 'Field cannot be both owned and forbidden.'
                }
            }
        }
    }
    return @($errors)
}

function Get-ReleaseIntakeRegistryByTable {
    param([object]$Registry)

    $map = @{}
    foreach ($entry in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $Registry -Name 'entries' -Default @()))) {
        $tableName = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'tableName' -Default '')
        if (-not [string]::IsNullOrWhiteSpace($tableName)) {
            $map[$tableName.ToLowerInvariant()] = $entry
        }
    }
    return $map
}

function New-ReleaseIntakeDataManifest {
    param(
        [object]$Registry,
        [object]$LocalDataChanges
    )

    $changes = @()
    $registryByTable = Get-ReleaseIntakeRegistryByTable -Registry $Registry
    foreach ($row in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $LocalDataChanges -Name 'changes' -Default @()))) {
        $tableName = [string](Get-ReleaseIntakeProperty -Object $row -Name 'tableName' -Default '')
        $tableKey = $tableName.ToLowerInvariant()
        if ($registryByTable.ContainsKey($tableKey)) {
            $entry = $registryByTable[$tableKey]
            $changes += [ordered]@{
                classification = 'required-data'
                registryEntryId = [string]$entry.entryId
                tableName = $tableName
                naturalKeyValue = (Get-ReleaseIntakeProperty -Object $row -Name 'naturalKeyValue')
                changedFields = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $row -Name 'changedFields' -Default @()))
                tenantScope = [string]$entry.tenantScope
                migrationBinding = $null
                blockingCandidate = $true
            }
        } else {
            $changes += [ordered]@{
                classification = 'unclassified-local-change'
                tableName = $tableName
                reason = 'No registry entry owns this table.'
                blockingCandidate = $true
            }
        }
    }

    $registryVersion = [string](Get-ReleaseIntakeProperty -Object $Registry -Name 'registryVersion' -Default '1.0')
    return [ordered]@{
        status = $(if ($changes.Count -gt 0) { 'warning' } else { 'passed' })
        registryVersion = $registryVersion
        changes = @($changes)
    }
}

function Get-ReleaseIntakeResourceObjectKey {
    param([object]$Row)

    $path = [string](Get-ReleaseIntakeProperty -Object $Row -Name 'path' -Default '')
    if (-not [string]::IsNullOrWhiteSpace($path)) {
        return $path.Replace('\', '/').TrimStart('/')
    }

    $url = [string](Get-ReleaseIntakeProperty -Object $Row -Name 'url' -Default '')
    if ([string]::IsNullOrWhiteSpace($url)) {
        return ''
    }
    $uri = [System.Uri]$url
    $pathParts = $uri.AbsolutePath.TrimStart('/').Split('/')
    if ($pathParts.Length -le 1) {
        return ''
    }
    return ($pathParts[1..($pathParts.Length - 1)] -join '/')
}

function Get-ReleaseIntakeResourceUrlDomain {
    param(
        [object]$Row,
        [string]$ObjectKey
    )

    $url = [string](Get-ReleaseIntakeProperty -Object $Row -Name 'url' -Default '')
    if ([string]::IsNullOrWhiteSpace($url) -or [string]::IsNullOrWhiteSpace($ObjectKey)) {
        return $null
    }
    $normalizedUrl = $url.Replace('\', '/')
    $normalizedKey = $ObjectKey.Replace('\', '/').TrimStart('/')
    $suffix = "/$normalizedKey"
    if ($normalizedUrl.EndsWith($suffix, [StringComparison]::OrdinalIgnoreCase)) {
        return $normalizedUrl.Substring(0, $normalizedUrl.Length - $suffix.Length)
    }
    return $null
}

function Get-ReleaseIntakeResourceBucket {
    param([object]$Row)

    $bucket = [string](Get-ReleaseIntakeProperty -Object $Row -Name 'bucket' -Default '')
    if (-not [string]::IsNullOrWhiteSpace($bucket)) {
        return $bucket
    }

    $url = [string](Get-ReleaseIntakeProperty -Object $Row -Name 'url' -Default '')
    if ([string]::IsNullOrWhiteSpace($url)) {
        return ''
    }
    $uri = [System.Uri]$url
    $pathParts = @($uri.AbsolutePath.TrimStart('/').Split('/') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($pathParts.Count -eq 0) {
        return ''
    }
    return [string]$pathParts[0]
}

function New-ReleaseIntakeResourceManifest {
    param(
        [object]$ResourceRows,
        [string]$CapturedAt
    )

    $references = @()
    foreach ($row in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $ResourceRows -Name 'references' -Default @()))) {
        $objectKey = Get-ReleaseIntakeResourceObjectKey -Row $row
        $urlDomain = Get-ReleaseIntakeResourceUrlDomain -Row $row -ObjectKey $objectKey
        $requiredForRelease = Get-ReleaseIntakeProperty -Object $row -Name 'requiredForRelease' -Default $true
        $references += [ordered]@{
            sourceTable = [string](Get-ReleaseIntakeProperty -Object $row -Name 'sourceTable' -Default '')
            sourceColumn = [string](Get-ReleaseIntakeProperty -Object $row -Name 'sourceColumn' -Default '')
            rowBusinessKey = [string](Get-ReleaseIntakeProperty -Object $row -Name 'rowBusinessKey' -Default '')
            tenantCode = (Get-ReleaseIntakeProperty -Object $row -Name 'tenantCode')
            fileConfigIdReadback = (Get-ReleaseIntakeProperty -Object $row -Name 'fileConfigIdReadback')
            storageProfileId = [string](Get-ReleaseIntakeProperty -Object $row -Name 'storageProfileId' -Default '')
            bucket = Get-ReleaseIntakeResourceBucket -Row $row
            objectKey = $objectKey
            urlDomain = $urlDomain
            expectedDomainPolicy = 'target-profile-domain'
            size = (Get-ReleaseIntakeProperty -Object $row -Name 'size')
            sha256 = (Get-ReleaseIntakeProperty -Object $row -Name 'sha256')
            contentType = (Get-ReleaseIntakeProperty -Object $row -Name 'contentType')
            requiredForRelease = [bool]$requiredForRelease
            resourcePreparedStatus = 'unknown'
        }
    }

    $referenceHash = Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value @($references))
    return [ordered]@{
        manifestVersion = '1.0'
        capturedAt = $CapturedAt
        referenceSetHash = $referenceHash
        references = @($references)
    }
}

function ConvertFrom-ReleaseIntakeTsv {
    param([string[]]$Lines)

    $rows = @()
    foreach ($line in $Lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $rows += [pscustomobject]@{
            TsvFields = [string[]]($line -split "`t")
        }
    }
    return @($rows)
}

function Get-ReleaseIntakeTsvFields {
    param([object]$Row)

    $property = $Row.PSObject.Properties['TsvFields']
    if ($null -eq $property) {
        return @()
    }
    $fields = @()
    foreach ($field in ([string[]]$property.Value)) {
        $fields += [string]$field
    }
    return @($fields)
}

function ConvertFrom-ReleaseIntakeDbValue {
    param([string]$Value)

    if ($Value -eq '\N') {
        return $null
    }
    return $Value
}

function Test-ReleaseIntakeForbiddenRemoteReference {
    param([string]$Text)

    return $Text -match '(?i)\b(ssh|scp)\b|\b(?:\d{1,3}\.){3}\d{1,3}\b'
}

function Assert-ReleaseIntakeReadonlySql {
    param([string]$Sql)

    if ($Sql -match '(?i)\b(DROP|INSERT|UPDATE|DELETE|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE)\b') {
        throw 'Release intake live mode only permits readonly SELECT statements.'
    }
    if (Test-ReleaseIntakeForbiddenRemoteReference -Text $Sql) {
        throw 'Release intake live mode must not reference remote shell commands or remote server IPs.'
    }
}

function Invoke-ReleaseIntakeDockerMysqlQuery {
    param(
        [string]$DockerCliPath,
        [string]$DockerContainer,
        [string]$Database,
        [string]$Username,
        [string]$Password,
        [string]$Sql
    )

    Assert-ReleaseIntakeReadonlySql -Sql $Sql

    $dockerArgs = @(
        'exec',
        '-i',
        '--env',
        'MYSQL_PWD',
        $DockerContainer,
        'mysql',
        '--batch',
        '--raw',
        '--skip-column-names',
        '--default-character-set=utf8mb4',
        '-u',
        $Username,
        $Database
    )
    $commandText = "$DockerCliPath $($dockerArgs -join ' ')"
    if (Test-ReleaseIntakeForbiddenRemoteReference -Text $commandText) {
        throw 'Release intake live mode attempted to use a forbidden remote command target.'
    }

    $previousMysqlPwd = [Environment]::GetEnvironmentVariable('MYSQL_PWD', 'Process')
    try {
        [Environment]::SetEnvironmentVariable('MYSQL_PWD', $Password, 'Process')
        $output = $Sql | & $DockerCliPath @dockerArgs 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        [Environment]::SetEnvironmentVariable('MYSQL_PWD', $previousMysqlPwd, 'Process')
    }

    if ($exitCode -ne 0) {
        throw "Docker MySQL readonly query failed with exit code $exitCode`: $output"
    }
    return @($output)
}

function New-ReleaseIntakeLiveDbContext {
    param(
        [object]$DbConfig,
        [string]$DockerCliPath
    )

    $driver = [string](Get-ReleaseIntakeProperty -Object $DbConfig -Name 'driver' -Default '')
    if ($driver -ne 'mysql') {
        throw 'Local readonly docker mysql mode requires driver=mysql.'
    }

    $dockerContainer = [string](Get-ReleaseIntakeProperty -Object $DbConfig -Name 'dockerContainer' -Default '')
    if ([string]::IsNullOrWhiteSpace($dockerContainer)) {
        return [pscustomobject]@{
            ErrorCode = 'INTAKE_DB_DOCKER_CONTAINER_MISSING'
            ErrorMessage = 'Local readonly docker mysql mode requires dockerContainer in LocalDatabaseConfigPath.'
        }
    }

    $database = [string](Get-ReleaseIntakeProperty -Object $DbConfig -Name 'database' -Default '')
    $usernameEnv = [string](Get-ReleaseIntakeProperty -Object $DbConfig -Name 'usernameEnv' -Default '')
    $passwordEnv = [string](Get-ReleaseIntakeProperty -Object $DbConfig -Name 'passwordEnv' -Default '')
    $missingCredentialDetails = @()
    foreach ($envName in @($usernameEnv, $passwordEnv)) {
        if ([string]::IsNullOrWhiteSpace($envName) -or [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($envName, 'Process'))) {
            $missingCredentialDetails += [ordered]@{
                envName = $envName
                message = 'Required database credential environment variable is missing.'
            }
        }
    }
    if ($missingCredentialDetails.Count -gt 0) {
        return [pscustomobject]@{
            ErrorCode = 'INTAKE_DB_CREDENTIAL_ENV_MISSING'
            ErrorMessage = 'Local readonly docker mysql mode requires username/password environment variables.'
            ErrorDetails = @($missingCredentialDetails)
        }
    }

    if ([string]::IsNullOrWhiteSpace($database)) {
        throw 'Local readonly docker mysql mode requires database in LocalDatabaseConfigPath.'
    }

    return [pscustomobject]@{
        DockerCliPath = $DockerCliPath
        DockerContainer = $dockerContainer
        Database = $database
        Username = [Environment]::GetEnvironmentVariable($usernameEnv, 'Process')
        Password = [Environment]::GetEnvironmentVariable($passwordEnv, 'Process')
    }
}

function Invoke-ReleaseIntakeLiveQuery {
    param(
        [object]$DbContext,
        [string]$Sql
    )

    return Invoke-ReleaseIntakeDockerMysqlQuery `
        -DockerCliPath $DbContext.DockerCliPath `
        -DockerContainer $DbContext.DockerContainer `
        -Database $DbContext.Database `
        -Username $DbContext.Username `
        -Password $DbContext.Password `
        -Sql $Sql
}

function New-ReleaseIntakeLiveSchemaFingerprint {
    param(
        [object]$DbContext,
        [string]$CapturedAt
    )

    $tableSql = @'
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = DATABASE()
ORDER BY table_name;
'@
    $columnSql = @'
SELECT table_name, column_name, column_type, is_nullable, column_default, ordinal_position
FROM information_schema.columns
WHERE table_schema = DATABASE()
ORDER BY table_name, ordinal_position;
'@
    $indexSql = @'
SELECT table_name, index_name, column_name, non_unique, seq_in_index
FROM information_schema.statistics
WHERE table_schema = DATABASE()
ORDER BY table_name, index_name, seq_in_index;
'@
    $viewSql = @'
SELECT table_name, view_definition
FROM information_schema.views
WHERE table_schema = DATABASE()
ORDER BY table_name;
'@

    $tableRows = ConvertFrom-ReleaseIntakeTsv -Lines (Invoke-ReleaseIntakeLiveQuery -DbContext $DbContext -Sql $tableSql)
    $columnRows = ConvertFrom-ReleaseIntakeTsv -Lines (Invoke-ReleaseIntakeLiveQuery -DbContext $DbContext -Sql $columnSql)
    $indexRows = ConvertFrom-ReleaseIntakeTsv -Lines (Invoke-ReleaseIntakeLiveQuery -DbContext $DbContext -Sql $indexSql)
    $viewRows = ConvertFrom-ReleaseIntakeTsv -Lines (Invoke-ReleaseIntakeLiveQuery -DbContext $DbContext -Sql $viewSql)

    $tableMap = [ordered]@{}
    foreach ($row in $tableRows) {
        $fields = @(Get-ReleaseIntakeTsvFields -Row $row)
        if ($fields.Count -lt 2) { continue }
        $tableName = [string]$fields[0]
        $tableMap[$tableName] = [ordered]@{
            tableName = $tableName
            tableType = [string]$fields[1]
            columns = @()
            indexes = @()
        }
    }

    foreach ($row in $columnRows) {
        $fields = @(Get-ReleaseIntakeTsvFields -Row $row)
        if ($fields.Count -lt 6) { continue }
        $tableName = [string]$fields[0]
        if (-not $tableMap.Contains($tableName)) {
            $tableMap[$tableName] = [ordered]@{
                tableName = $tableName
                tableType = 'UNKNOWN'
                columns = @()
                indexes = @()
            }
        }
        $columnDefinition = [ordered]@{
            columnName = [string]$fields[1]
            columnType = [string]$fields[2]
            isNullable = [string]$fields[3]
            columnDefault = ConvertFrom-ReleaseIntakeDbValue -Value ([string]$fields[4])
            ordinalPosition = [int]$fields[5]
        }
        $columnDefinition.definitionHash = Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value $columnDefinition)
        $tableMap[$tableName].columns += $columnDefinition
    }

    foreach ($row in $indexRows) {
        $fields = @(Get-ReleaseIntakeTsvFields -Row $row)
        if ($fields.Count -lt 5) { continue }
        $tableName = [string]$fields[0]
        if (-not $tableMap.Contains($tableName)) {
            continue
        }
        $indexDefinition = [ordered]@{
            indexName = [string]$fields[1]
            columnName = [string]$fields[2]
            nonUnique = [string]$fields[3]
            seqInIndex = [int]$fields[4]
        }
        $indexDefinition.definitionHash = Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value $indexDefinition)
        $tableMap[$tableName].indexes += $indexDefinition
    }

    $views = @()
    foreach ($row in $viewRows) {
        $fields = @(Get-ReleaseIntakeTsvFields -Row $row)
        if ($fields.Count -lt 2) { continue }
        $viewDefinition = [ordered]@{
            viewName = [string]$fields[0]
            definitionHash = Get-ReleaseIntakeSha256 -Text ([string]$fields[1])
        }
        $views += $viewDefinition
    }

    $tables = @($tableMap.Values)
    $fingerprint = [ordered]@{
        databaseName = $DbContext.Database
        capturedAt = $CapturedAt
        captureSource = 'local-docker-mysql-readonly'
        dockerContainer = $DbContext.DockerContainer
        tables = @($tables)
        views = @($views)
    }
    $fingerprint.schemaHash = Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value $fingerprint)
    return $fingerprint
}

function New-ReleaseIntakeLiveDataManifest {
    param([object]$Registry)

    $coverage = @()
    foreach ($entry in (ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $Registry -Name 'entries' -Default @()))) {
        $coverage += [ordered]@{
            entryId = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'entryId' -Default '')
            tableName = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'tableName' -Default '')
            tenantScope = [string](Get-ReleaseIntakeProperty -Object $entry -Name 'tenantScope' -Default '')
            naturalKey = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $entry -Name 'naturalKey' -Default @()))
            ownedFieldCount = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $entry -Name 'ownedFields' -Default @())).Count
            forbiddenOverwriteFieldCount = @(ConvertTo-ReleaseIntakeArray (Get-ReleaseIntakeProperty -Object $entry -Name 'forbiddenOverwriteFields' -Default @())).Count
            resourceBindingPresent = ($null -ne (Get-ReleaseIntakeProperty -Object $entry -Name 'resourceBinding'))
        }
    }

    return [ordered]@{
        status = 'warning'
        registryVersion = [string](Get-ReleaseIntakeProperty -Object $Registry -Name 'registryVersion' -Default '1.0')
        liveDataChangeMode = 'not-yet-bound-to-baseline'
        registryCoverage = @($coverage)
        changes = @()
    }
}

function New-ReleaseIntakeLiveResourceRows {
    param([object]$DbContext)

    $resourceSql = @'
SELECT config_id, path, url, type, name
FROM infra_file
WHERE config_id IS NOT NULL
  AND path IS NOT NULL
  AND url IS NOT NULL
  AND url <> ''
ORDER BY config_id, path;
'@
    $rows = @(Invoke-ReleaseIntakeLiveQuery -DbContext $DbContext -Sql $resourceSql)
    $references = @()
    foreach ($row in $rows) {
        if ([string]::IsNullOrWhiteSpace([string]$row)) {
            continue
        }
        $fields = @([string]$row -split "`t")
        if ($fields.Count -lt 5) { continue }
        $configId = [int]$fields[0]
        $path = [string]$fields[1]
        $references += [ordered]@{
            sourceTable = 'infra_file'
            sourceColumn = 'url'
            rowBusinessKey = "config_id=$configId,path=$path"
            tenantCode = $null
            fileConfigIdReadback = $configId
            storageProfileId = 'minio-yudao-default'
            path = $path
            url = [string]$fields[2]
            type = ConvertFrom-ReleaseIntakeDbValue -Value ([string]$fields[3])
            name = ConvertFrom-ReleaseIntakeDbValue -Value ([string]$fields[4])
            size = $null
            sha256 = $null
            contentType = ConvertFrom-ReleaseIntakeDbValue -Value ([string]$fields[3])
            requiredForRelease = $true
        }
    }
    return [ordered]@{
        references = @($references)
    }
}

function Copy-ReleaseIntakeFingerprint {
    param(
        [object]$LocalSchemaFingerprint,
        [string]$CapturedAt,
        [string]$SourcePath
    )

    $copy = [ordered]@{}
    foreach ($property in $LocalSchemaFingerprint.PSObject.Properties) {
        $copy[$property.Name] = $property.Value
    }
    $copy.capturedAt = $CapturedAt
    $copy.captureSource = 'fixture-file'
    $copy.captureSourcePath = (Resolve-Path -LiteralPath $SourcePath).Path
    if (-not $copy.Contains('schemaHash')) {
        $copy.schemaHash = Get-ReleaseIntakeSha256 -Text (ConvertTo-ReleaseIntakeCanonicalJson -Value $LocalSchemaFingerprint)
    }
    return $copy
}

function Invoke-ReleaseIntake {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,

        [Parameter(Mandatory = $true)]
        [string]$BaselineManifestPath,

        [string]$LocalDatabaseConfigPath = '',

        [Parameter(Mandatory = $true)]
        [string]$DataOwnershipRegistryPath,

        [Parameter(Mandatory = $true)]
        [string]$OutputDir,

        [ValidateSet('report-only')]
        [string]$Mode = 'report-only',

        [string]$LocalSchemaFingerprintPath = '',
        [string]$LocalDataChangeRowsPath = '',
        [string]$ResourceRowsPath = '',
        [string]$DockerCliPath = 'docker'
    )

    $createdAt = Get-ReleaseIntakeTimestamp
    try {
        if (Test-ReleaseIntakeBlank $OutputDir) {
            throw 'OutputDir is required.'
        }
        if (-not (Test-Path -LiteralPath $OutputDir)) {
            New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        }

        if (Test-ReleaseIntakeBlank $LocalDatabaseConfigPath) {
            return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_DB_CONFIG_MISSING' -Message 'LocalDatabaseConfigPath is required for release intake.'
        }

        $pathFailure = Assert-ReleaseIntakePath -Path $RepoRoot -Code 'INTAKE_REPO_ROOT_MISSING' -Message 'RepoRoot does not exist.' -OutputDir $OutputDir -CreatedAt $createdAt
        if ($null -ne $pathFailure) { return $pathFailure }
        $pathFailure = Assert-ReleaseIntakePath -Path $BaselineManifestPath -Code 'INTAKE_BASELINE_MANIFEST_MISSING' -Message 'BaselineManifestPath does not exist.' -OutputDir $OutputDir -CreatedAt $createdAt
        if ($null -ne $pathFailure) { return $pathFailure }
        $pathFailure = Assert-ReleaseIntakePath -Path $LocalDatabaseConfigPath -Code 'INTAKE_DB_CONFIG_MISSING' -Message 'LocalDatabaseConfigPath does not exist.' -OutputDir $OutputDir -CreatedAt $createdAt
        if ($null -ne $pathFailure) { return $pathFailure }
        $pathFailure = Assert-ReleaseIntakePath -Path $DataOwnershipRegistryPath -Code 'INTAKE_DATA_REGISTRY_MISSING' -Message 'DataOwnershipRegistryPath does not exist.' -OutputDir $OutputDir -CreatedAt $createdAt
        if ($null -ne $pathFailure) { return $pathFailure }

        $baselineManifest = Read-ReleaseIntakeJson -Path $BaselineManifestPath
        $dbConfig = Read-ReleaseIntakeJson -Path $LocalDatabaseConfigPath
        if ((Get-ReleaseIntakeProperty -Object $dbConfig -Name 'readOnly' -Default $false) -ne $true) {
            return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_DB_READONLY_CONNECTION_FAILED' -Message 'Local database config must declare readOnly=true for release intake.'
        }

        $registry = Read-ReleaseIntakeJson -Path $DataOwnershipRegistryPath
        $registryErrors = @(Test-ReleaseIntakeDataRegistry -Registry $registry)
        if ($registryErrors.Count -gt 0) {
            return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_DATA_REGISTRY_INVALID' -Message 'Data ownership registry is invalid.' -Details $registryErrors
        }

        $snapshotPathValues = @($LocalSchemaFingerprintPath, $LocalDataChangeRowsPath, $ResourceRowsPath)
        $snapshotPathCount = @($snapshotPathValues | Where-Object { -not (Test-ReleaseIntakeBlank $_) }).Count
        $snapshotMode = ($snapshotPathCount -eq 3)
        if ($snapshotPathCount -gt 0 -and -not $snapshotMode) {
            return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_SCHEMA_CAPTURE_FAILED' -Message 'Explicit snapshot mode requires LocalSchemaFingerprintPath, LocalDataChangeRowsPath, and ResourceRowsPath together.'
        }

        $liveWarnings = @()
        if ($snapshotMode) {
            foreach ($requiredSnapshotPath in $snapshotPathValues) {
                if (-not (Test-Path -LiteralPath $requiredSnapshotPath)) {
                    return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_SCHEMA_CAPTURE_FAILED' -Message "Required local intake snapshot path does not exist: $requiredSnapshotPath"
                }
            }
            $localSchemaFingerprint = Read-ReleaseIntakeJson -Path $LocalSchemaFingerprintPath
            $localDataChanges = Read-ReleaseIntakeJson -Path $LocalDataChangeRowsPath
            $resourceRows = Read-ReleaseIntakeJson -Path $ResourceRowsPath
        } else {
            $dbContext = New-ReleaseIntakeLiveDbContext -DbConfig $dbConfig -DockerCliPath $DockerCliPath
            if ($null -ne (Get-ReleaseIntakeProperty -Object $dbContext -Name 'ErrorCode')) {
                return Write-ReleaseIntakeFailure `
                    -OutputDir $OutputDir `
                    -CreatedAt $createdAt `
                    -Code $dbContext.ErrorCode `
                    -Message $dbContext.ErrorMessage `
                    -Details @(Get-ReleaseIntakeProperty -Object $dbContext -Name 'ErrorDetails' -Default @())
            }
            try {
                $localSchemaFingerprint = New-ReleaseIntakeLiveSchemaFingerprint -DbContext $dbContext -CapturedAt $createdAt
                $resourceRows = New-ReleaseIntakeLiveResourceRows -DbContext $dbContext
                $liveWarnings += [ordered]@{
                    code = 'INTAKE_DATA_BASELINE_NOT_BOUND'
                    message = 'Live registry data change extraction is not yet bound to a baseline data snapshot.'
                }
            } catch {
                return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_DB_READONLY_CONNECTION_FAILED' -Message $_.Exception.Message
            }
        }

        $changeSet = New-ReleaseIntakeChangeSet -RepoRoot $RepoRoot -CapturedAt $createdAt
        if ($snapshotMode) {
            $fingerprintReport = Copy-ReleaseIntakeFingerprint -LocalSchemaFingerprint $localSchemaFingerprint -CapturedAt $createdAt -SourcePath $LocalSchemaFingerprintPath
        } else {
            $fingerprintReport = $localSchemaFingerprint
        }
        $schemaReport = New-ReleaseIntakeSchemaChangeReport -BaselineManifest $baselineManifest -LocalSchemaFingerprint $localSchemaFingerprint
        if ($snapshotMode) {
            $dataManifest = New-ReleaseIntakeDataManifest -Registry $registry -LocalDataChanges $localDataChanges
        } else {
            $dataManifest = New-ReleaseIntakeLiveDataManifest -Registry $registry
        }
        $resourceManifest = New-ReleaseIntakeResourceManifest -ResourceRows $resourceRows -CapturedAt $createdAt

        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'change-set.json') -Value $changeSet
        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'local-schema-fingerprint.json') -Value $fingerprintReport
        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'schema-change-report.json') -Value $schemaReport
        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'data-change-manifest.json') -Value $dataManifest
        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'resource-reference-manifest.json') -Value $resourceManifest

        $schemaBlockingCount = @(ConvertTo-ReleaseIntakeArray $schemaReport.changes | Where-Object { $_.blockingCandidate -eq $true }).Count
        $dataBlockingCount = @(ConvertTo-ReleaseIntakeArray $dataManifest.changes | Where-Object { $_.blockingCandidate -eq $true }).Count
        $blockingCandidateCount = $schemaBlockingCount + $dataBlockingCount
        $requiredDataCount = @(ConvertTo-ReleaseIntakeArray $dataManifest.changes | Where-Object { $_.classification -eq 'required-data' }).Count
        $unclassifiedCount = @(ConvertTo-ReleaseIntakeArray $dataManifest.changes | Where-Object { $_.classification -eq 'unclassified-local-change' }).Count
        $resourceReferenceCount = @(ConvertTo-ReleaseIntakeArray $resourceManifest.references).Count
        $status = $(if ($blockingCandidateCount -gt 0 -or $liveWarnings.Count -gt 0) { 'warning' } else { 'passed' })

        $intakeResult = New-ReleaseIntakeBaseResult -Status $status -CreatedAt $createdAt -Warnings $liveWarnings
        $intakeResult.schemaDriftCount = [int]$schemaReport.schemaDriftCount
        $intakeResult.requiredDataChangeCount = $requiredDataCount
        $intakeResult.unclassifiedLocalChangeCount = $unclassifiedCount
        $intakeResult.resourceReferenceCount = $resourceReferenceCount
        $intakeResult.blockingCandidateCount = $blockingCandidateCount
        Write-ReleaseIntakeJson -Path (Join-Path $OutputDir 'intake-result.json') -Value $intakeResult

        Write-Output "Release intake report-only completed: $status"
        return [pscustomobject]@{
            ExitCode = 0
            Result = $intakeResult
        }
    } catch {
        $message = $_.Exception.Message
        return Write-ReleaseIntakeFailure -OutputDir $OutputDir -CreatedAt $createdAt -Code 'INTAKE_OUTPUT_WRITE_FAILED' -Message $message
    }
}

Export-ModuleMember -Function Invoke-ReleaseIntake
