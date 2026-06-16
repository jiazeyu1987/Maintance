Set-StrictMode -Version Latest

function Get-FlowProperty {
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

function ConvertTo-FlowArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Read-FlowJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-FlowJson {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth 40
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function New-FlowDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        status = if ($Code -eq 'CHILD_OPERATION_FAILED') { 'failed' } else { 'blocked' }
        scope = $Scope
        message = $Message
        impact = $Impact
        nextStep = $NextStep
    })
}

function New-FlowStep {
    param([Parameter(Mandatory = $true)][string]$Id)

    return [pscustomobject]([ordered]@{
        id = $Id
        execution = 'planned'
    })
}

function Get-DefaultFlowSteps {
    param([Parameter(Mandatory = $true)][string]$Flow)

    $stepIds = switch ($Flow) {
        'publish-only' { @('validate-release-manifest', 'schema-preflight', 'deploy-backend', 'deploy-admin-frontend', 'apply-schema-migration', 'apply-required-sql', 'health-check') }
        'restore-only' { @('validate-backup-manifest', 'restore-database', 'restore-dcc-objects', 'restore-health-check') }
        'restore-then-publish' { @('validate-backup-manifest', 'restore-database', 'restore-dcc-objects', 'validate-release-manifest', 'schema-preflight', 'deploy-backend', 'deploy-admin-frontend', 'apply-schema-migration', 'apply-required-sql', 'health-check') }
        'publish-then-restore' { @('validate-release-manifest', 'schema-preflight', 'deploy-backend', 'deploy-admin-frontend', 'apply-schema-migration', 'apply-required-sql', 'validate-backup-manifest', 'restore-database', 'restore-dcc-objects', 'health-check') }
        default { @() }
    }
    return @($stepIds | ForEach-Object { New-FlowStep -Id $_ })
}

function Test-FlowValueMissing {
    param($Value)

    if ($null -eq $Value) {
        return $true
    }
    if ($Value -is [string]) {
        return [string]::IsNullOrWhiteSpace($Value)
    }
    if ($Value -is [System.Array]) {
        return $Value.Count -eq 0
    }
    return $false
}

function Add-MissingFieldDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string[]]$Fields,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    foreach ($field in $Fields) {
        if (Test-FlowValueMissing -Value (Get-FlowProperty -Object $Object -Name $field)) {
            [void]$Errors.Add((New-FlowDiagnostic `
                -Code $Code `
                -Scope $Scope `
                -Message "Missing required field: $field" `
                -Impact "The $Scope contract is incomplete, so the flow cannot prove version and data compatibility." `
                -NextStep "Regenerate or fix the $Scope manifest with field '$field', then rerun flow preflight."))
        }
    }
}

function Add-FlowContractMissingDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Field
    )

    [void]$Errors.Add((New-FlowDiagnostic `
        -Code $Code `
        -Scope $Scope `
        -Message "Missing required field: $Field" `
        -Impact "The $Scope contract is incomplete, so the flow cannot prove version and data compatibility." `
        -NextStep "Regenerate or fix the manifest with field '$Field', then rerun flow preflight."))
}

function Add-FlowNestedMissingDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        $Object,
        [Parameter(Mandatory = $true)][string[]]$Fields,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    foreach ($field in $Fields) {
        if (Test-FlowValueMissing -Value (Get-FlowProperty -Object $Object -Name $field)) {
            Add-FlowContractMissingDiagnostic -Errors $Errors -Code $Code -Scope $Scope -Field $field
        }
    }
}

function Add-BackupManifestReadinessDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Backup
    )

    $backupStrategy = Get-FlowProperty -Object $Backup -Name 'backupStrategy'
    if ($null -eq $backupStrategy) {
        Add-FlowContractMissingDiagnostic -Errors $Errors -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest' -Field 'backupStrategy'
    } else {
        Add-FlowNestedMissingDiagnostics `
            -Errors $Errors `
            -Object $backupStrategy `
            -Fields @('mode', 'mysqlBackupMode', 'mysqlBaseline', 'mysqlIncrementalPlan') `
            -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' `
            -Scope 'backupManifest.backupStrategy'
        $mysqlIncrementalPlan = Get-FlowProperty -Object $backupStrategy -Name 'mysqlIncrementalPlan'
        if ($null -ne $mysqlIncrementalPlan) {
            $binlog = Get-FlowProperty -Object $mysqlIncrementalPlan -Name 'binlog'
            $xtrabackup = Get-FlowProperty -Object $mysqlIncrementalPlan -Name 'xtrabackup'
            Add-FlowNestedMissingDiagnostics -Errors $Errors -Object $binlog -Fields @('status') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.backupStrategy.mysqlIncrementalPlan.binlog'
            Add-FlowNestedMissingDiagnostics -Errors $Errors -Object $xtrabackup -Fields @('status') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.backupStrategy.mysqlIncrementalPlan.xtrabackup'
        }
    }

    $recoverySet = Get-FlowProperty -Object $Backup -Name 'recoverySet'
    if ($null -eq $recoverySet) {
        Add-FlowContractMissingDiagnostic -Errors $Errors -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest' -Field 'recoverySet'
        return
    }

    Add-FlowNestedMissingDiagnostics `
        -Errors $Errors `
        -Object $recoverySet `
        -Fields @('id', 'status', 'program', 'mysql', 'minio', 'businessFiles', 'dcc', 'checksums') `
        -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' `
        -Scope 'backupManifest.recoverySet'
    if ([string](Get-FlowProperty -Object $recoverySet -Name 'status') -ne 'COMPLETE') {
        [void]$Errors.Add((New-FlowDiagnostic `
            -Code 'BACKUP_RECOVERY_SET_INCOMPLETE' `
            -Scope 'backupManifest.recoverySet.status' `
            -Message 'backupManifest recoverySet.status must be COMPLETE before restore planning.' `
            -Impact 'The restore flow could use a backup point whose database, object inventory, checksums, or DCC manifest are incomplete.' `
            -NextStep 'Regenerate the backup after all required artifacts and checksums are complete, then rerun restore preflight.'))
    }
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'program') -Fields @('imageTag') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.program'
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'mysql') -Fields @('dumpPath') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.mysql'
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'minio') -Fields @('snapshotPath') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.minio'
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'businessFiles') -Fields @('snapshotPath') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.businessFiles'
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'dcc') -Fields @('manifestPath') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.dcc'
    Add-FlowNestedMissingDiagnostics -Errors $Errors -Object (Get-FlowProperty -Object $recoverySet -Name 'checksums') -Fields @('path', 'sha256') -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.checksums'

    $validation = Get-FlowProperty -Object $Backup -Name 'validation'
    $rehearsalStatus = [string](Get-FlowProperty -Object $validation -Name 'rehearsalStatus')
    $lastRehearsedAt = [string](Get-FlowProperty -Object $validation -Name 'lastRehearsedAt')
    if (@('PASSED', 'passed', 'pass') -notcontains $rehearsalStatus -or [string]::IsNullOrWhiteSpace($lastRehearsedAt)) {
        [void]$Errors.Add((New-FlowDiagnostic `
            -Code 'BACKUP_RESTORE_REHEARSAL_MISSING' `
            -Scope 'backupManifest.validation' `
            -Message 'backupManifest validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before restore planning.' `
            -Impact 'The restore flow could use a backup point that has not proven database and object recovery.' `
            -NextStep 'Run a restore rehearsal for the selected backup point and attach validation.rehearsalStatus=PASSED plus lastRehearsedAt before restore preflight.'))
    }
}

function Test-FlowContains {
    param(
        $Values,
        [Parameter(Mandatory = $true)][string]$Expected
    )

    foreach ($value in (ConvertTo-FlowArray -Value $Values)) {
        if ([string]$value -eq $Expected) {
            return $true
        }
    }
    return $false
}

function Get-FlowStepIds {
    param($PlanFixture, [Parameter(Mandatory = $true)][string]$Flow)

    if ($null -eq $PlanFixture) {
        return @((Get-DefaultFlowSteps -Flow $Flow) | ForEach-Object { [string](Get-FlowProperty -Object $_ -Name 'id') })
    }
    $fixtureSteps = ConvertTo-FlowArray -Value (Get-FlowProperty -Object $PlanFixture -Name 'steps')
    if (@($fixtureSteps).Count -gt 0) {
        return @($fixtureSteps | ForEach-Object { [string](Get-FlowProperty -Object $_ -Name 'id') })
    }
    return @((Get-DefaultFlowSteps -Flow $Flow) | ForEach-Object { [string](Get-FlowProperty -Object $_ -Name 'id') })
}

function ConvertTo-FlowSteps {
    param([Parameter(Mandatory = $true)]$StepIds)

    return @($StepIds | ForEach-Object { New-FlowStep -Id ([string]$_) })
}

function Test-FlowNeedsReleaseManifest {
    param([Parameter(Mandatory = $true)][string]$Flow)

    return $Flow -eq 'publish-only' -or $Flow -eq 'restore-then-publish' -or $Flow -eq 'publish-then-restore'
}

function Test-FlowNeedsBackupManifest {
    param([Parameter(Mandatory = $true)][string]$Flow)

    return $Flow -eq 'restore-only' -or $Flow -eq 'restore-then-publish' -or $Flow -eq 'publish-then-restore'
}

function Invoke-ReleaseRestoreFlowPlan {
    param(
        [Parameter(Mandatory = $true)][string]$Flow,
        [string]$ReleaseManifestPath,
        [string]$BackupManifestPath,
        [string]$PlanFixturePath,
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $errors = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $release = $null
    $backup = $null
    $planFixture = $null

    try {
        if (Test-FlowNeedsReleaseManifest -Flow $Flow) {
            if ([string]::IsNullOrWhiteSpace($ReleaseManifestPath)) {
                throw "ReleaseManifestPath is required for $Flow"
            }
            $release = Read-FlowJson -Path $ReleaseManifestPath
        }
        if (Test-FlowNeedsBackupManifest -Flow $Flow) {
            if ([string]::IsNullOrWhiteSpace($BackupManifestPath)) {
                throw "BackupManifestPath is required for $Flow"
            }
            $backup = Read-FlowJson -Path $BackupManifestPath
        }
        if (-not [string]::IsNullOrWhiteSpace($PlanFixturePath)) {
            $planFixture = Read-FlowJson -Path $PlanFixturePath
        }
    } catch {
        $payload = [pscustomobject]([ordered]@{
            operationId = 'op-flow-' + [guid]::NewGuid().ToString()
            flow = $Flow
            targetEnvironment = $TargetEnvironment
            mode = $Mode
            status = 'failed'
            checkedAt = (Get-Date).ToString('o')
            steps = @()
            errors = @((New-FlowDiagnostic `
                -Code 'FLOW_INPUT_INVALID' `
                -Scope 'input' `
                -Message ([string]$_.Exception.Message) `
                -Impact 'The flow preflight cannot read the required manifest inputs.' `
                -NextStep 'Fix the input paths and JSON syntax, then rerun flow preflight.'))
            warnings = @()
        })
        Write-FlowJson -Payload $payload -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $payload; ExitCode = 1 }
    }

    $stepIds = Get-FlowStepIds -PlanFixture $planFixture -Flow $Flow

    if ($TargetEnvironment -eq 'prod') {
        [void]$errors.Add((New-FlowDiagnostic `
            -Code 'TARGET_ENVIRONMENT_FORBIDDEN' `
            -Scope 'targetEnvironment' `
            -Message 'prod is not allowed for this local dry-run flow planner.' `
            -Impact 'The flow might access or mutate production state without explicit authorization.' `
            -NextStep 'Use test or backup, or provide an explicit production authorization workflow outside this planner.'))
    }

    if ($null -ne $release) {
        Add-MissingFieldDiagnostics `
            -Errors $errors `
            -Object $release `
            -Fields @('releaseTag', 'publishScope', 'schemaVersion', 'schemaDigest', 'migrationPlan', 'requiredSql', 'schemaPreflight', 'compatibilityMatrix') `
            -Code 'RELEASE_MANIFEST_CONTRACT_MISSING' `
            -Scope 'releaseManifest'
        $schemaPreflight = Get-FlowProperty -Object $release -Name 'schemaPreflight'
        if ($null -ne $schemaPreflight -and [string](Get-FlowProperty -Object $schemaPreflight -Name 'status') -ne 'pass') {
            [void]$errors.Add((New-FlowDiagnostic `
                -Code 'SCHEMA_PREFLIGHT_REQUIRED' `
                -Scope 'releaseManifest.schemaPreflight' `
                -Message 'schemaPreflight status must be pass.' `
                -Impact 'The backend might start against a database missing required tables, fields, or required SQL prerequisites.' `
                -NextStep 'Run schema preflight and resolve all blocked findings before planning the flow.'))
        }
    }

    if ($null -ne $backup) {
        Add-MissingFieldDiagnostics `
            -Errors $errors `
            -Object $backup `
            -Fields @('backupId', 'targetEnvironment', 'releaseTag', 'schemaVersion', 'restorePointId', 'fullBaseline', 'incrementalChain', 'objectInventory', 'checksums') `
            -Code 'BACKUP_MANIFEST_CONTRACT_MISSING' `
            -Scope 'backupManifest'
        Add-BackupManifestReadinessDiagnostics -Errors $errors -Backup $backup
    }

    if ($Flow -eq 'publish-only' -and $null -ne $release) {
        if ([string](Get-FlowProperty -Object $release -Name 'publishScope') -ne 'code-only') {
            [void]$errors.Add((New-FlowDiagnostic `
                -Code 'PUBLISH_ONLY_MUST_NOT_SYNC_BUSINESS_DATA' `
                -Scope 'publishScope' `
                -Message 'publish-only requires release manifest publishScope code-only.' `
                -Impact 'Program deployment could import business data or synchronize DCC objects.' `
                -NextStep 'Build a code-only release package or choose an explicit data restore flow.'))
        }
        foreach ($forbiddenStep in @('import-business-data', 'sync-dcc-objects')) {
            if ($stepIds -contains $forbiddenStep) {
                [void]$errors.Add((New-FlowDiagnostic `
                    -Code 'PUBLISH_ONLY_MUST_NOT_SYNC_BUSINESS_DATA' `
                    -Scope 'steps' `
                    -Message "publish-only contains forbidden step: $forbiddenStep" `
                    -Impact 'Program deployment could overwrite business data or DCC object state.' `
                    -NextStep 'Remove data sync steps from publish-only and plan restore as a separate flow.'))
            }
        }
    }

    if ($Flow -eq 'restore-only') {
        foreach ($forbiddenStep in @('deploy-release', 'publish-program', 'switch-backend-image', 'replace-frontend-dist', 'deploy-backend', 'deploy-admin-frontend')) {
            if ($stepIds -contains $forbiddenStep) {
                [void]$errors.Add((New-FlowDiagnostic `
                    -Code 'RESTORE_MUST_NOT_PUBLISH_PROGRAM' `
                    -Scope 'steps' `
                    -Message "restore-only contains forbidden program deployment step: $forbiddenStep" `
                    -Impact 'Data restore could silently change the running frontend or backend version.' `
                    -NextStep 'Remove program deployment steps and run a separate publish flow if the version contract requires it.'))
            }
        }
    }

    if ($Flow -eq 'restore-then-publish' -and $null -ne $release -and $null -ne $backup) {
        $backupSchemaVersion = [string](Get-FlowProperty -Object $backup -Name 'schemaVersion')
        $releaseSchemaVersion = [string](Get-FlowProperty -Object $release -Name 'schemaVersion')
        $compatibilityMatrix = Get-FlowProperty -Object $release -Name 'compatibilityMatrix'
        $supportedSchemas = Get-FlowProperty -Object $compatibilityMatrix -Name 'supportedBackupSchemaVersions'
        if ($backupSchemaVersion -ne $releaseSchemaVersion -and -not (Test-FlowContains -Values $supportedSchemas -Expected $backupSchemaVersion)) {
            [void]$errors.Add((New-FlowDiagnostic `
                -Code 'FLOW_COMPATIBILITY_BLOCKED' `
                -Scope 'compatibilityMatrix' `
                -Message "backup schemaVersion $backupSchemaVersion is not compatible with release schemaVersion $releaseSchemaVersion." `
                -Impact 'The restored data might require a migration path the release manifest does not declare.' `
                -NextStep 'Add a verified migrationPlan and compatibility matrix entry, or choose a matching backup/release pair.'))
        }
    }

    if ($Flow -eq 'publish-then-restore' -and $null -ne $release -and $null -ne $backup) {
        $backupReleaseTag = [string](Get-FlowProperty -Object $backup -Name 'programVersion')
        if ([string]::IsNullOrWhiteSpace($backupReleaseTag)) {
            $backupReleaseTag = [string](Get-FlowProperty -Object $backup -Name 'releaseTag')
        }
        $releaseTag = [string](Get-FlowProperty -Object $release -Name 'releaseTag')
        $compatibilityMatrix = Get-FlowProperty -Object $release -Name 'compatibilityMatrix'
        $supportedReleaseTags = Get-FlowProperty -Object $compatibilityMatrix -Name 'supportedBackupReleaseTags'
        if ($backupReleaseTag -ne $releaseTag -and -not (Test-FlowContains -Values $supportedReleaseTags -Expected $backupReleaseTag)) {
            [void]$errors.Add((New-FlowDiagnostic `
                -Code 'FLOW_COMPATIBILITY_BLOCKED' `
                -Scope 'compatibilityMatrix' `
                -Message "backup programVersion $backupReleaseTag is not compatible with releaseTag $releaseTag." `
                -Impact 'The restored data may require a different frontend/backend/schema version.' `
                -NextStep 'Use the matching release package or add verified compatibility evidence.'))
        }
    }

    $childOperationFailed = $false
    $operationResults = if ($null -eq $planFixture) {
        @()
    } else {
        ConvertTo-FlowArray -Value (Get-FlowProperty -Object $planFixture -Name 'operationResults')
    }
    foreach ($operation in $operationResults) {
        $operationStatus = [string](Get-FlowProperty -Object $operation -Name 'status')
        if ($operationStatus -eq 'failed' -or $operationStatus -eq 'blocked') {
            $childOperationFailed = $true
            $operationId = [string](Get-FlowProperty -Object $operation -Name 'id')
            [void]$errors.Add((New-FlowDiagnostic `
                -Code 'CHILD_OPERATION_FAILED' `
                -Scope 'operationResults' `
                -Message "Child operation failed or blocked: $operationId" `
                -Impact 'A later health check must not overwrite an earlier failed operation.' `
                -NextStep 'Resolve the failed child operation and rerun the complete flow.'))
        }
    }

    $status = 'passed'
    $exitCode = 0
    if ($errors.Count -gt 0) {
        $status = if ($childOperationFailed) { 'failed' } else { 'blocked' }
        $exitCode = 2
    }

    $payload = [pscustomobject]([ordered]@{
        operationId = 'op-flow-' + [guid]::NewGuid().ToString()
        flow = $Flow
        targetEnvironment = $TargetEnvironment
        mode = $Mode
        status = $status
        checkedAt = (Get-Date).ToString('o')
        releaseTag = if ($null -eq $release) { '' } else { [string](Get-FlowProperty -Object $release -Name 'releaseTag') }
        backupId = if ($null -eq $backup) { '' } else { [string](Get-FlowProperty -Object $backup -Name 'backupId') }
        steps = @(ConvertTo-FlowSteps -StepIds $stepIds)
        errors = @($errors.ToArray())
        warnings = @($warnings.ToArray())
    })
    Write-FlowJson -Payload $payload -OutputPath $OutputPath
    return [pscustomobject]@{ Payload = $payload; ExitCode = $exitCode }
}

Export-ModuleMember -Function Invoke-ReleaseRestoreFlowPlan
