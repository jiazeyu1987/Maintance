Set-StrictMode -Version Latest

function Get-RollbackProperty {
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

function ConvertTo-RollbackArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Read-RollbackJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-RollbackJson {
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

function Test-RollbackValueMissing {
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

function New-RollbackDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$RequiredResolution
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        scope = $Scope
        message = $Message
        impact = $Impact
        requiredResolution = $RequiredResolution
    })
}

function New-RollbackStep {
    param([Parameter(Mandatory = $true)][string]$Id)

    return [pscustomobject]([ordered]@{
        id = $Id
        execution = 'planned'
    })
}

function Get-RollbackSteps {
    param([Parameter(Mandatory = $true)][ValidateSet('code', 'data', 'combined')][string]$Mode)

    $stepIds = switch ($Mode) {
        'code' { @('validate-release-manifest', 'rollback-preflight', 'switch-program-version', 'health-check') }
        'data' { @('validate-backup-manifest', 'rollback-preflight', 'restore-database', 'restore-dcc-objects', 'restore-health-check') }
        'combined' { @('validate-release-manifest', 'validate-backup-manifest', 'rollback-preflight', 'switch-program-version', 'restore-database', 'restore-dcc-objects', 'health-check') }
    }
    return @($stepIds | ForEach-Object { New-RollbackStep -Id $_ })
}

function Add-RollbackMissingFieldDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string[]]$Fields,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    foreach ($field in $Fields) {
        if (Test-RollbackValueMissing -Value (Get-RollbackProperty -Object $Object -Name $field)) {
            [void]$Errors.Add((New-RollbackDiagnostic `
                -Code $Code `
                -Scope $Scope `
                -Message "Missing required field: $field" `
                -Impact "The $Scope contract is incomplete, so rollback preflight cannot prove version or data compatibility." `
                -RequiredResolution "Regenerate or fix the $Scope manifest with field '$field', then rerun rollback preflight."))
        }
    }
}

function Add-RollbackContractMissingDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Field
    )

    [void]$Errors.Add((New-RollbackDiagnostic `
        -Code $Code `
        -Scope $Scope `
        -Message "Missing required field: $Field" `
        -Impact "The $Scope contract is incomplete, so rollback preflight cannot prove version or data compatibility." `
        -RequiredResolution "Regenerate or fix the manifest with field '$Field', then rerun rollback preflight."))
}

function Add-RollbackNestedMissingDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        $Object,
        [Parameter(Mandatory = $true)][string[]]$Fields,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope
    )

    foreach ($field in $Fields) {
        if (Test-RollbackValueMissing -Value (Get-RollbackProperty -Object $Object -Name $field)) {
            Add-RollbackContractMissingDiagnostic -Errors $Errors -Code $Code -Scope $Scope -Field $field
        }
    }
}

function Add-RollbackBackupManifestReadinessDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Backup
    )

    $backupStrategy = Get-RollbackProperty -Object $Backup -Name 'backupStrategy'
    if ($null -eq $backupStrategy) {
        Add-RollbackContractMissingDiagnostic -Errors $Errors -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest' -Field 'backupStrategy'
    } else {
        Add-RollbackNestedMissingDiagnostics `
            -Errors $Errors `
            -Object $backupStrategy `
            -Fields @('mode', 'mysqlBackupMode', 'mysqlBaseline', 'mysqlIncrementalPlan') `
            -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' `
            -Scope 'backupManifest.backupStrategy'
        $mysqlIncrementalPlan = Get-RollbackProperty -Object $backupStrategy -Name 'mysqlIncrementalPlan'
        if ($null -ne $mysqlIncrementalPlan) {
            Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $mysqlIncrementalPlan -Name 'binlog') -Fields @('status') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.backupStrategy.mysqlIncrementalPlan.binlog'
            Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $mysqlIncrementalPlan -Name 'xtrabackup') -Fields @('status') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.backupStrategy.mysqlIncrementalPlan.xtrabackup'
        }
    }

    $recoverySet = Get-RollbackProperty -Object $Backup -Name 'recoverySet'
    if ($null -eq $recoverySet) {
        Add-RollbackContractMissingDiagnostic -Errors $Errors -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest' -Field 'recoverySet'
        return
    }

    Add-RollbackNestedMissingDiagnostics `
        -Errors $Errors `
        -Object $recoverySet `
        -Fields @('id', 'status', 'program', 'mysql', 'minio', 'businessFiles', 'dcc', 'checksums') `
        -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' `
        -Scope 'backupManifest.recoverySet'
    if ([string](Get-RollbackProperty -Object $recoverySet -Name 'status') -ne 'COMPLETE') {
        [void]$Errors.Add((New-RollbackDiagnostic `
            -Code 'ROLLBACK_RECOVERY_SET_INCOMPLETE' `
            -Scope 'backupManifest.recoverySet.status' `
            -Message 'backupManifest recoverySet.status must be COMPLETE before data rollback preflight.' `
            -Impact 'Data rollback could use a backup point whose database, object inventory, checksums, or DCC manifest are incomplete.' `
            -RequiredResolution 'Regenerate the backup after all required artifacts and checksums are complete, then rerun rollback preflight.'))
    }
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'program') -Fields @('imageTag') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.program'
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'mysql') -Fields @('dumpPath') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.mysql'
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'minio') -Fields @('snapshotPath') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.minio'
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'businessFiles') -Fields @('snapshotPath') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.businessFiles'
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'dcc') -Fields @('manifestPath') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.dcc'
    Add-RollbackNestedMissingDiagnostics -Errors $Errors -Object (Get-RollbackProperty -Object $recoverySet -Name 'checksums') -Fields @('path', 'sha256') -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' -Scope 'backupManifest.recoverySet.checksums'

    $validation = Get-RollbackProperty -Object $Backup -Name 'validation'
    $rehearsalStatus = [string](Get-RollbackProperty -Object $validation -Name 'rehearsalStatus')
    $lastRehearsedAt = [string](Get-RollbackProperty -Object $validation -Name 'lastRehearsedAt')
    if (@('PASSED', 'passed', 'pass') -notcontains $rehearsalStatus -or [string]::IsNullOrWhiteSpace($lastRehearsedAt)) {
        [void]$Errors.Add((New-RollbackDiagnostic `
            -Code 'ROLLBACK_RESTORE_REHEARSAL_MISSING' `
            -Scope 'backupManifest.validation' `
            -Message 'backupManifest validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before data rollback preflight.' `
            -Impact 'Data rollback could use a backup point that has not proven database and object recovery.' `
            -RequiredResolution 'Run a restore rehearsal for the selected backup point and attach validation.rehearsalStatus=PASSED plus lastRehearsedAt before rollback preflight.'))
    }
}

function Test-RollbackContains {
    param(
        $Values,
        [Parameter(Mandatory = $true)][string]$Expected
    )

    foreach ($value in (ConvertTo-RollbackArray -Value $Values)) {
        if ([string]$value -eq $Expected) {
            return $true
        }
    }
    return $false
}

function Test-RollbackNeedsReleaseManifest {
    param([Parameter(Mandatory = $true)][ValidateSet('code', 'data', 'combined')][string]$Mode)

    return $Mode -eq 'code' -or $Mode -eq 'combined'
}

function Test-RollbackNeedsBackupManifest {
    param([Parameter(Mandatory = $true)][ValidateSet('code', 'data', 'combined')][string]$Mode)

    return $Mode -eq 'data' -or $Mode -eq 'combined'
}

function Test-RollbackHasDowngradeMigration {
    param($Release)

    foreach ($migration in (ConvertTo-RollbackArray -Value (Get-RollbackProperty -Object $Release -Name 'migrationPlan'))) {
        if ([string](Get-RollbackProperty -Object $migration -Name 'direction') -eq 'downgrade') {
            return $true
        }
    }
    return $false
}

function Test-RollbackHasDestructiveMigration {
    param($Release)

    foreach ($migration in (ConvertTo-RollbackArray -Value (Get-RollbackProperty -Object $Release -Name 'migrationPlan'))) {
        if ((Get-RollbackProperty -Object $migration -Name 'destructive') -eq $true) {
            return $true
        }
    }
    return $false
}

function Get-RollbackEvidence {
    param($Release, $Backup)

    $releaseEvidence = if ($null -eq $Release) { $null } else { Get-RollbackProperty -Object $Release -Name 'rollbackEvidence' }
    if ($null -ne $releaseEvidence) {
        return $releaseEvidence
    }
    if ($null -ne $Backup) {
        return Get-RollbackProperty -Object $Backup -Name 'rollbackEvidence'
    }
    return $null
}

function Test-RollbackEvidencePathExists {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    return [System.IO.File]::Exists($Path)
}

function Test-VerifiedRollbackEvidence {
    param(
        $Evidence,
        $Backup
    )

    if ($null -eq $Evidence) {
        return $false
    }
    $approval = Get-RollbackProperty -Object $Evidence -Name 'approval'
    if ($null -eq $approval -or (Get-RollbackProperty -Object $approval -Name 'approved') -ne $true) {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace([string](Get-RollbackProperty -Object $approval -Name 'approvedBy'))) {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace([string](Get-RollbackProperty -Object $approval -Name 'approvedAt'))) {
        return $false
    }

    $backupProof = Get-RollbackProperty -Object $Evidence -Name 'backupProof'
    if ($null -eq $backupProof) {
        return $false
    }
    if ($null -ne $Backup) {
        $backupId = [string](Get-RollbackProperty -Object $Backup -Name 'backupId')
        if ([string](Get-RollbackProperty -Object $backupProof -Name 'backupId') -ne $backupId) {
            return $false
        }
    }
    if (-not (Test-RollbackEvidencePathExists -Path ([string](Get-RollbackProperty -Object $backupProof -Name 'evidencePath')))) {
        return $false
    }

    $rehearsal = Get-RollbackProperty -Object $Evidence -Name 'rehearsal'
    if ($null -eq $rehearsal -or [string](Get-RollbackProperty -Object $rehearsal -Name 'status') -ne 'passed') {
        return $false
    }
    if (-not (Test-RollbackEvidencePathExists -Path ([string](Get-RollbackProperty -Object $rehearsal -Name 'evidencePath')))) {
        return $false
    }

    if (@(ConvertTo-RollbackArray -Value (Get-RollbackProperty -Object $Evidence -Name 'downgradeScripts')).Count -eq 0) {
        return $false
    }
    return $true
}

function Test-RollbackSchemaCompatible {
    param($Release, $Backup)

    if ($null -eq $Release -or $null -eq $Backup) {
        return $true
    }
    $releaseSchemaVersion = [string](Get-RollbackProperty -Object $Release -Name 'schemaVersion')
    $backupSchemaVersion = [string](Get-RollbackProperty -Object $Backup -Name 'schemaVersion')
    if ($releaseSchemaVersion -eq $backupSchemaVersion) {
        return $true
    }
    $compatibilityMatrix = Get-RollbackProperty -Object $Release -Name 'compatibilityMatrix'
    $supportedBackupSchemaVersions = Get-RollbackProperty -Object $compatibilityMatrix -Name 'supportedBackupSchemaVersions'
    return Test-RollbackContains -Values $supportedBackupSchemaVersions -Expected $backupSchemaVersion
}

function Test-RollbackProdAuthorization {
    param($Release, $Backup, [Parameter(Mandatory = $true)][string]$Mode)

    $authorization = $null
    if ($null -ne $Release) {
        $authorization = Get-RollbackProperty -Object $Release -Name 'userAuthorization'
    }
    if ($null -eq $authorization -and $null -ne $Backup) {
        $authorization = Get-RollbackProperty -Object $Backup -Name 'userAuthorization'
    }
    if ($null -eq $authorization) {
        return $false
    }
    return (Get-RollbackProperty -Object $authorization -Name 'approved') -eq $true `
        -and [string](Get-RollbackProperty -Object $authorization -Name 'scope') -eq "rollback-$Mode" `
        -and -not [string]::IsNullOrWhiteSpace([string](Get-RollbackProperty -Object $authorization -Name 'approvedBy')) `
        -and -not [string]::IsNullOrWhiteSpace([string](Get-RollbackProperty -Object $authorization -Name 'approvedAt'))
}

function Invoke-RollbackPreflight {
    param(
        [string]$ReleaseManifestPath,
        [string]$BackupManifestPath,
        [Parameter(Mandatory = $true)][ValidateSet('test', 'backup', 'prod')][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][ValidateSet('code', 'data', 'combined')][string]$Mode,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $errors = New-Object System.Collections.ArrayList
    $release = $null
    $backup = $null

    try {
        if (Test-RollbackNeedsReleaseManifest -Mode $Mode) {
            if ([string]::IsNullOrWhiteSpace($ReleaseManifestPath)) {
                [void]$errors.Add((New-RollbackDiagnostic `
                    -Code 'ROLLBACK_RELEASE_MANIFEST_REQUIRED' `
                    -Scope 'releaseManifest' `
                    -Message "Release manifest is required for $Mode rollback preflight." `
                    -Impact 'Code rollback cannot prove the target program package or schema contract.' `
                    -RequiredResolution 'Pass the rollback target release manifest and rerun preflight.'))
            } else {
                $release = Read-RollbackJson -Path $ReleaseManifestPath
            }
        }
        if (Test-RollbackNeedsBackupManifest -Mode $Mode) {
            if ([string]::IsNullOrWhiteSpace($BackupManifestPath)) {
                [void]$errors.Add((New-RollbackDiagnostic `
                    -Code 'ROLLBACK_BACKUP_MANIFEST_REQUIRED' `
                    -Scope 'backupManifest' `
                    -Message "Backup manifest is required for $Mode rollback preflight." `
                    -Impact 'Data rollback cannot prove the restore point, schema version, object inventory, or checksums.' `
                    -RequiredResolution 'Pass the target backup manifest and rerun preflight.'))
            } else {
                $backup = Read-RollbackJson -Path $BackupManifestPath
            }
        }
    } catch {
        [void]$errors.Add((New-RollbackDiagnostic `
            -Code 'ROLLBACK_INPUT_INVALID' `
            -Scope 'input' `
            -Message ([string]$_.Exception.Message) `
            -Impact 'Rollback preflight cannot read the required manifest inputs.' `
            -RequiredResolution 'Fix manifest paths and JSON syntax, then rerun rollback preflight.'))
    }

    if ($TargetEnvironment -eq 'prod' -and -not (Test-RollbackProdAuthorization -Release $release -Backup $backup -Mode $Mode)) {
        [void]$errors.Add((New-RollbackDiagnostic `
            -Code 'PROD_ACCESS_NOT_AUTHORIZED' `
            -Scope 'targetEnvironment' `
            -Message 'prod rollback preflight requires explicit user authorization evidence.' `
            -Impact 'A production rollback could be accepted without the required explicit approval boundary.' `
            -RequiredResolution "Attach userAuthorization approved for scope rollback-$Mode, or run against test/backup."))
    }

    if ($null -ne $release) {
        Add-RollbackMissingFieldDiagnostics `
            -Errors $errors `
            -Object $release `
            -Fields @('releaseTag', 'schemaVersion', 'migrationPlan', 'artifactHashes', 'compatibilityMatrix') `
            -Code 'ROLLBACK_RELEASE_MANIFEST_CONTRACT_MISSING' `
            -Scope 'releaseManifest'
    }
    if ($null -ne $backup) {
        Add-RollbackMissingFieldDiagnostics `
            -Errors $errors `
            -Object $backup `
            -Fields @('backupId', 'schemaVersion', 'restorePointId', 'fullBaseline', 'incrementalChain', 'objectInventory', 'checksums') `
            -Code 'ROLLBACK_BACKUP_MANIFEST_CONTRACT_MISSING' `
            -Scope 'backupManifest'
        Add-RollbackBackupManifestReadinessDiagnostics -Errors $errors -Backup $backup
    }

    $rollbackEvidence = Get-RollbackEvidence -Release $release -Backup $backup
    $hasVerifiedRollbackEvidence = Test-VerifiedRollbackEvidence -Evidence $rollbackEvidence -Backup $backup
    $hasDowngradeMigration = $false
    $hasDestructiveMigration = $false
    if ($null -ne $release) {
        $hasDowngradeMigration = Test-RollbackHasDowngradeMigration -Release $release
        $hasDestructiveMigration = Test-RollbackHasDestructiveMigration -Release $release
    }

    if ($hasDestructiveMigration -and -not $hasVerifiedRollbackEvidence) {
        [void]$errors.Add((New-RollbackDiagnostic `
            -Code 'DESTRUCTIVE_ROLLBACK_REQUIRES_APPROVAL' `
            -Scope 'releaseManifest.migrationPlan' `
            -Message 'Destructive rollback migration requires approval, backup proof, downgrade scripts, and rehearsal evidence.' `
            -Impact 'A destructive rollback could delete tables, fields, or data without a verified recovery path.' `
            -RequiredResolution 'Attach verified rollbackEvidence with approval, backupProof, rehearsal, and downgradeScripts before rerunning preflight.'))
    }

    $schemaCompatible = Test-RollbackSchemaCompatible -Release $release -Backup $backup
    if (($hasDowngradeMigration -or -not $schemaCompatible) -and -not $hasVerifiedRollbackEvidence) {
        [void]$errors.Add((New-RollbackDiagnostic `
            -Code 'DOWNGRADE_EVIDENCE_MISSING' `
            -Scope 'rollbackEvidence' `
            -Message 'Rollback requires downgrade or compatibility evidence before code/data versions can be combined.' `
            -Impact 'The target program may not be able to read the target database schema or restored data.' `
            -RequiredResolution 'Provide verified rollbackEvidence with approved downgrade scripts, backup proof, and rehearsal evidence, or choose a compatible release/backup pair.'))
    }

    $status = if ($errors.Count -eq 0) { 'pass' } else { 'blocked' }
    $exitCode = if ($errors.Count -eq 0) { 0 } else { 2 }
    $payload = [pscustomobject]([ordered]@{
        operationId = 'op-rollback-preflight-' + [guid]::NewGuid().ToString()
        targetEnvironment = $TargetEnvironment
        mode = $Mode
        status = $status
        checkedAt = (Get-Date).ToString('o')
        releaseTag = if ($null -eq $release) { '' } else { [string](Get-RollbackProperty -Object $release -Name 'releaseTag') }
        backupId = if ($null -eq $backup) { '' } else { [string](Get-RollbackProperty -Object $backup -Name 'backupId') }
        plannedSteps = @(Get-RollbackSteps -Mode $Mode)
        rollbackEvidence = [pscustomobject]([ordered]@{
            verified = $hasVerifiedRollbackEvidence
            rehearsalStatus = if ($null -eq $rollbackEvidence) { '' } else { [string](Get-RollbackProperty -Object (Get-RollbackProperty -Object $rollbackEvidence -Name 'rehearsal') -Name 'status') }
        })
        errors = @($errors.ToArray())
    })
    Write-RollbackJson -Payload $payload -OutputPath $OutputPath
    return [pscustomobject]@{ Payload = $payload; ExitCode = $exitCode }
}

Export-ModuleMember -Function Invoke-RollbackPreflight
