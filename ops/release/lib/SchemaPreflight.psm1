Set-StrictMode -Version Latest

function Get-SchemaProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function ConvertTo-SchemaArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function New-SchemaFinding {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$ObjectType,
        [Parameter(Mandatory = $true)][string]$ObjectName,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$RequiredResolution
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        severity = 'blocked'
        objectType = $ObjectType
        objectName = $ObjectName
        impact = $Impact
        requiredResolution = $RequiredResolution
    })
}

function New-SchemaWarning {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$ObjectType,
        [Parameter(Mandatory = $true)][string]$ObjectName,
        [Parameter(Mandatory = $true)][string]$RequiredResolution
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        severity = 'warning'
        objectType = $ObjectType
        objectName = $ObjectName
        requiredResolution = $RequiredResolution
    })
}

function New-TableMap {
    param($Tables)

    $map = @{}
    foreach ($table in (ConvertTo-SchemaArray -Value $Tables)) {
        $name = [string](Get-SchemaProperty -Object $table -Name 'name')
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $map[$name.ToLowerInvariant()] = $table
        }
    }
    return $map
}

function New-FieldMap {
    param($Table)

    $map = @{}
    foreach ($field in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $Table -Name 'fields'))) {
        $name = [string](Get-SchemaProperty -Object $field -Name 'name')
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $map[$name.ToLowerInvariant()] = $field
        }
    }
    return $map
}

function Test-TableExists {
    param(
        [Parameter(Mandatory = $true)]$TableMap,
        [Parameter(Mandatory = $true)][string]$TableName
    )

    return $TableMap.ContainsKey($TableName.ToLowerInvariant())
}

function Test-FieldExists {
    param(
        [Parameter(Mandatory = $true)]$TableMap,
        [Parameter(Mandatory = $true)][string]$Reference
    )

    $parts = $Reference.Split('.', 2)
    if ($parts.Count -ne 2) {
        return $false
    }
    if (-not (Test-TableExists -TableMap $TableMap -TableName $parts[0])) {
        return $false
    }
    $table = $TableMap[$parts[0].ToLowerInvariant()]
    $fields = New-FieldMap -Table $table
    return $fields.ContainsKey($parts[1].ToLowerInvariant())
}

function Write-SchemaPreflightJson {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-SchemaPreflight {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseManifestPath,
        [Parameter(Mandatory = $true)][string]$TargetSchemaPath,
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    try {
        $release = [System.IO.File]::ReadAllText($ReleaseManifestPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
        $target = [System.IO.File]::ReadAllText($TargetSchemaPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
    } catch {
        $payload = [pscustomobject]([ordered]@{
            operationId = 'op-schema-preflight-' + [guid]::NewGuid().ToString()
            releaseTag = ''
            targetEnvironment = $TargetEnvironment
            targetSchemaVersion = ''
            currentSchemaVersion = ''
            status = 'failed'
            checkedAt = (Get-Date).ToString('o')
            failedStage = 'read-input'
            failureCode = 'schema_preflight_input_invalid'
            impact = 'schema preflight cannot inspect release manifest or target schema.'
            requiredResolution = 'Fix JSON input paths and syntax, then rerun schema preflight.'
            findings = @()
            warnings = @()
        })
        Write-SchemaPreflightJson -Payload $payload -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $payload; ExitCode = 1 }
    }

    $findings = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $targetTables = New-TableMap -Tables (Get-SchemaProperty -Object $target -Name 'tables')
    $schemaContract = Get-SchemaProperty -Object $release -Name 'schemaContract'
    $requiredTables = ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $schemaContract -Name 'tables')

    foreach ($requiredTable in $requiredTables) {
        $tableName = [string](Get-SchemaProperty -Object $requiredTable -Name 'name')
        if ([string]::IsNullOrWhiteSpace($tableName)) {
            continue
        }
        if (-not (Test-TableExists -TableMap $targetTables -TableName $tableName)) {
            [void]$findings.Add((New-SchemaFinding `
                -Code 'missing_table' `
                -ObjectType 'table' `
                -ObjectName $tableName `
                -Impact "Target database lacks required table '$tableName'." `
                -RequiredResolution 'Execute forward schema migration, rerun schema preflight, then continue release or restore.'))
            continue
        }

        $targetTable = $targetTables[$tableName.ToLowerInvariant()]
        $targetFields = New-FieldMap -Table $targetTable
        $requiredFields = New-FieldMap -Table $requiredTable
        foreach ($requiredField in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $requiredTable -Name 'fields'))) {
            $fieldName = [string](Get-SchemaProperty -Object $requiredField -Name 'name')
            if ([string]::IsNullOrWhiteSpace($fieldName)) {
                continue
            }
            $qualifiedName = "$tableName.$fieldName"
            if (-not $targetFields.ContainsKey($fieldName.ToLowerInvariant())) {
                [void]$findings.Add((New-SchemaFinding `
                    -Code 'missing_field' `
                    -ObjectType 'field' `
                    -ObjectName $qualifiedName `
                    -Impact "Target database lacks required field '$qualifiedName'." `
                    -RequiredResolution 'Execute forward schema migration, rerun schema preflight, then continue release or restore.'))
                continue
            }
            $targetField = $targetFields[$fieldName.ToLowerInvariant()]
            $requiredType = [string](Get-SchemaProperty -Object $requiredField -Name 'type')
            $targetType = [string](Get-SchemaProperty -Object $targetField -Name 'type')
            $requiredNullable = Get-SchemaProperty -Object $requiredField -Name 'nullable'
            $targetNullable = Get-SchemaProperty -Object $targetField -Name 'nullable'
            if ($requiredType -ne $targetType -or [string]$requiredNullable -ne [string]$targetNullable) {
                [void]$findings.Add((New-SchemaFinding `
                    -Code 'incompatible_type' `
                    -ObjectType 'field' `
                    -ObjectName $qualifiedName `
                    -Impact "Target field '$qualifiedName' is not compatible with the release schema contract." `
                    -RequiredResolution 'Provide an explicit migrationPlan with data verification and rollback evidence.'))
            }
        }

        foreach ($targetField in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $targetTable -Name 'fields'))) {
            $fieldName = [string](Get-SchemaProperty -Object $targetField -Name 'name')
            if (-not [string]::IsNullOrWhiteSpace($fieldName) -and -not $requiredFields.ContainsKey($fieldName.ToLowerInvariant())) {
                [void]$warnings.Add((New-SchemaWarning `
                    -Code 'extra_field' `
                    -ObjectType 'field' `
                    -ObjectName "$tableName.$fieldName" `
                    -RequiredResolution 'Keep by default and never delete automatically; only an approved cleanup migration may handle it.'))
            }
        }

        $targetIndexes = @(ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $targetTable -Name 'indexes'))
        foreach ($indexName in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $requiredTable -Name 'indexes'))) {
            if ($targetIndexes -notcontains $indexName) {
                [void]$findings.Add((New-SchemaFinding `
                    -Code 'missing_index' `
                    -ObjectType 'index' `
                    -ObjectName "$tableName.$indexName" `
                    -Impact "Target database lacks required index '$tableName.$indexName'." `
                    -RequiredResolution 'Execute index migration from migrationPlan, rerun schema preflight, then continue.'))
            }
        }
    }

    foreach ($migration in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $release -Name 'migrationPlan'))) {
        if ((Get-SchemaProperty -Object $migration -Name 'destructive') -eq $true) {
            $migrationId = [string](Get-SchemaProperty -Object $migration -Name 'id')
            [void]$findings.Add((New-SchemaFinding `
                -Code 'destructive_migration' `
                -ObjectType 'migration' `
                -ObjectName $migrationId `
                -Impact 'Destructive migration cannot run automatically.' `
                -RequiredResolution 'Require manual approval, backup proof, rollback strategy, and rehearsal evidence.'))
        }
        if ([string](Get-SchemaProperty -Object $migration -Name 'direction') -eq 'downgrade') {
            $migrationId = [string](Get-SchemaProperty -Object $migration -Name 'id')
            [void]$findings.Add((New-SchemaFinding `
                -Code 'downgrade_migration' `
                -ObjectType 'migration' `
                -ObjectName $migrationId `
                -Impact 'Downgrade migration requires explicit verified evidence.' `
                -RequiredResolution 'Provide downgrade script, compatibility matrix, and restore rehearsal evidence before continuing.'))
        }
    }

    foreach ($requiredSql in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $release -Name 'requiredSql'))) {
        $sqlId = [string](Get-SchemaProperty -Object $requiredSql -Name 'id')
        if ((Get-SchemaProperty -Object $requiredSql -Name 'destructive') -eq $true) {
            [void]$findings.Add((New-SchemaFinding `
                -Code 'destructive_migration' `
                -ObjectType 'requiredSql' `
                -ObjectName $sqlId `
                -Impact 'Destructive required SQL cannot run automatically.' `
                -RequiredResolution 'Remove destructive SQL from automatic required SQL or run it through an approved manual migration.'))
        }
        foreach ($precondition in (ConvertTo-SchemaArray -Value (Get-SchemaProperty -Object $requiredSql -Name 'preconditions'))) {
            $type = [string](Get-SchemaProperty -Object $precondition -Name 'type')
            $name = [string](Get-SchemaProperty -Object $precondition -Name 'name')
            $exists = $false
            if ($type -eq 'table') {
                $exists = Test-TableExists -TableMap $targetTables -TableName $name
            } elseif ($type -eq 'field') {
                $exists = Test-FieldExists -TableMap $targetTables -Reference $name
            }
            if (-not $exists) {
                [void]$findings.Add((New-SchemaFinding `
                    -Code 'missing_required_sql_precondition' `
                    -ObjectType $type `
                    -ObjectName $name `
                    -Impact "required SQL '$sqlId' cannot run because precondition '$name' is missing." `
                    -RequiredResolution "Fix schema/configuration prerequisite first; required SQL must not execute before preflight passes."))
            }
        }
    }

    $status = if ($findings.Count -gt 0) { 'blocked' } else { 'pass' }
    $payload = [pscustomobject]([ordered]@{
        operationId = 'op-schema-preflight-' + [guid]::NewGuid().ToString()
        releaseTag = [string](Get-SchemaProperty -Object $release -Name 'releaseTag')
        targetEnvironment = $TargetEnvironment
        targetSchemaVersion = [string](Get-SchemaProperty -Object $release -Name 'schemaVersion')
        currentSchemaVersion = [string](Get-SchemaProperty -Object $target -Name 'schemaVersion')
        status = $status
        checkedAt = (Get-Date).ToString('o')
        findings = @($findings.ToArray())
        warnings = @($warnings.ToArray())
    })
    Write-SchemaPreflightJson -Payload $payload -OutputPath $OutputPath
    $exitCode = if ($status -eq 'pass') { 0 } else { 2 }
    return [pscustomobject]@{ Payload = $payload; ExitCode = $exitCode }
}

Export-ModuleMember -Function Invoke-SchemaPreflight
