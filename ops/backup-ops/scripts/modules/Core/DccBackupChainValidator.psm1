Set-StrictMode -Version Latest

function Get-DccProperty {
    param(
        $Object,
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

function ConvertTo-DccArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Read-DccBackupJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-DccBackupJson {
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

function New-DccBackupDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        status = 'blocked'
        scope = $Scope
        message = $Message
        impact = $Impact
        nextStep = $NextStep
    })
}

function Add-DccDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    [void]$Errors.Add((New-DccBackupDiagnostic -Code $Code -Scope $Scope -Message $Message -Impact $Impact -NextStep $NextStep))
}

function New-DccInventoryMap {
    param($Manifest)

    $map = @{}
    foreach ($inventory in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'objectInventories'))) {
        $restorePointId = [string](Get-DccProperty -Object $inventory -Name 'restorePointId')
        if (-not [string]::IsNullOrWhiteSpace($restorePointId)) {
            $map[$restorePointId] = $inventory
        }
    }
    return $map
}

function Test-DccEventExists {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)][string]$FileKey,
        [Parameter(Mandatory = $true)][string]$EventType
    )

    foreach ($event in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'dccEvents'))) {
        if ([string](Get-DccProperty -Object $event -Name 'restorePointId') -eq $RestorePointId `
                -and [string](Get-DccProperty -Object $event -Name 'fileKey') -eq $FileKey `
                -and [string](Get-DccProperty -Object $event -Name 'eventType') -eq $EventType) {
            return $true
        }
    }
    return $false
}

function Test-DccSha256Value {
    param([string]$Value)

    return $Value -match '^sha256:[0-9a-fA-F]{64}$'
}

function Get-DccObjectAtRestorePoint {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)][string]$FileKey
    )

    $inventoryMap = New-DccInventoryMap -Manifest $Manifest
    if (-not $inventoryMap.ContainsKey($RestorePointId)) {
        return $null
    }
    foreach ($object in (ConvertTo-DccArray -Value (Get-DccProperty -Object $inventoryMap[$RestorePointId] -Name 'objects'))) {
        if ([string](Get-DccProperty -Object $object -Name 'fileKey') -eq $FileKey) {
            return $object
        }
    }
    return $null
}

function Get-DccInventoryAtRestorePoint {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId
    )

    foreach ($inventory in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'objectInventories'))) {
        if ([string](Get-DccProperty -Object $inventory -Name 'restorePointId') -eq $RestorePointId) {
            return $inventory
        }
    }
    return $null
}

function Get-DccDatabaseRecordsAtRestorePoint {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId
    )

    $records = New-Object System.Collections.ArrayList
    foreach ($record in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'databaseRecords'))) {
        if ([string](Get-DccProperty -Object $record -Name 'restorePointId') -eq $RestorePointId) {
            [void]$records.Add($record)
        }
    }
    return @($records.ToArray())
}

function Get-DccReplayPointIds {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)]$Errors
    )

    $fullBaseline = Get-DccProperty -Object $Manifest -Name 'fullBaseline'
    $baselineRestorePointId = [string](Get-DccProperty -Object $fullBaseline -Name 'restorePointId')
    $points = New-Object System.Collections.ArrayList
    if ([string]::IsNullOrWhiteSpace($baselineRestorePointId)) {
        Add-DccDiagnostic -Errors $Errors -Code 'full_baseline_missing' -Scope 'fullBaseline' `
            -Message 'fullBaseline.restorePointId is required before replay planning.' `
            -Impact 'The restore chain has no baseline to replay from.' `
            -NextStep 'Create a full baseline manifest before planning chain restore.'
        return @()
    }
    [void]$points.Add($baselineRestorePointId)
    if ($RestorePointId -eq $baselineRestorePointId) {
        return @($points.ToArray())
    }

    $current = $baselineRestorePointId
    foreach ($segment in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'incrementalChain'))) {
        $from = [string](Get-DccProperty -Object $segment -Name 'from')
        $to = [string](Get-DccProperty -Object $segment -Name 'to')
        if ($from -ne $current) {
            break
        }
        [void]$points.Add($to)
        $current = $to
        if ($to -eq $RestorePointId) {
            return @($points.ToArray())
        }
    }
    return @()
}

function New-DccFinalFilesFromReplay {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string[]]$ReplayPointIds,
        $TargetInventory
    )

    $fileState = [ordered]@{}
    foreach ($pointId in $ReplayPointIds) {
        foreach ($record in (Get-DccDatabaseRecordsAtRestorePoint -Manifest $Manifest -RestorePointId $pointId)) {
            $fileKey = [string](Get-DccProperty -Object $record -Name 'fileKey')
            if ([string]::IsNullOrWhiteSpace($fileKey)) {
                continue
            }
            $fileState[$fileKey] = $record
        }
    }

    $objectsByFile = @{}
    foreach ($object in (ConvertTo-DccArray -Value (Get-DccProperty -Object $TargetInventory -Name 'objects'))) {
        $fileKey = [string](Get-DccProperty -Object $object -Name 'fileKey')
        $objectState = [string](Get-DccProperty -Object $object -Name 'state')
        if ([string]::IsNullOrWhiteSpace($fileKey) -or $objectState -ne 'active') {
            continue
        }
        if (-not $objectsByFile.ContainsKey($fileKey)) {
            $objectsByFile[$fileKey] = New-Object System.Collections.ArrayList
        }
        [void]$objectsByFile[$fileKey].Add($object)
    }

    $finalFiles = New-Object System.Collections.ArrayList
    foreach ($fileKey in $fileState.Keys) {
        $record = $fileState[$fileKey]
        $objects = if ($objectsByFile.ContainsKey($fileKey)) { @($objectsByFile[$fileKey].ToArray()) } else { @() }
        [void]$finalFiles.Add([pscustomobject]([ordered]@{
                    fileKey = $fileKey
                    state = [string](Get-DccProperty -Object $record -Name 'state')
                    versionNo = [string](Get-DccProperty -Object $record -Name 'versionNo')
                    permissionDigest = [string](Get-DccProperty -Object $record -Name 'permissionDigest')
                    restorePointId = [string](Get-DccProperty -Object $record -Name 'restorePointId')
                    objects = @($objects)
                }))
    }
    return @($finalFiles.ToArray())
}

function New-DccRestoreReplayPlan {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)]$Errors
    )

    $fullBaseline = Get-DccProperty -Object $Manifest -Name 'fullBaseline'
    $baselineRestorePointId = [string](Get-DccProperty -Object $fullBaseline -Name 'restorePointId')
    if ([string]::IsNullOrWhiteSpace($RestorePointId)) {
        Add-DccDiagnostic -Errors $Errors -Code 'restore_point_missing' -Scope 'restorePoint' `
            -Message 'RestorePoint is required for plan-restore.' `
            -Impact 'The chain replay target is ambiguous.' `
            -NextStep 'Select an explicit DCC restore point and rerun plan-restore.'
        return $null
    }
    if ($RestorePointId -eq $baselineRestorePointId) {
        $targetInventory = Get-DccInventoryAtRestorePoint -Manifest $Manifest -RestorePointId $RestorePointId
        $replayPointIds = @(Get-DccReplayPointIds -Manifest $Manifest -RestorePointId $RestorePointId -Errors $Errors)
        return [pscustomobject]([ordered]@{
            baselineRestorePointId = $baselineRestorePointId
            targetRestorePointId = $RestorePointId
            replayPointIds = @($replayPointIds)
            segments = @()
            databaseRecords = @(Get-DccDatabaseRecordsAtRestorePoint -Manifest $Manifest -RestorePointId $RestorePointId)
            objectInventory = $targetInventory
            finalFiles = @(New-DccFinalFilesFromReplay -Manifest $Manifest -ReplayPointIds $replayPointIds -TargetInventory $targetInventory)
        })
    }

    $segments = New-Object System.Collections.ArrayList
    $current = $baselineRestorePointId
    foreach ($segment in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'incrementalChain'))) {
        $from = [string](Get-DccProperty -Object $segment -Name 'from')
        $to = [string](Get-DccProperty -Object $segment -Name 'to')
        if ($from -ne $current) {
            break
        }
        [void]$segments.Add($segment)
        $current = $to
        if ($to -eq $RestorePointId) {
            $targetInventory = Get-DccInventoryAtRestorePoint -Manifest $Manifest -RestorePointId $RestorePointId
            if ($null -eq $targetInventory) {
                Add-DccDiagnostic -Errors $Errors -Code 'object_inventory_missing' -Scope 'objectInventories' `
                    -Message "Missing object inventory for restore point $RestorePointId." `
                    -Impact 'The chain replay plan cannot materialize target objects.' `
                    -NextStep 'Regenerate the target restore point object inventory.'
                return $null
            }
            return [pscustomobject]([ordered]@{
                baselineRestorePointId = $baselineRestorePointId
                targetRestorePointId = $RestorePointId
                replayPointIds = @(Get-DccReplayPointIds -Manifest $Manifest -RestorePointId $RestorePointId -Errors $Errors)
                segments = @($segments.ToArray())
                databaseRecords = @(Get-DccDatabaseRecordsAtRestorePoint -Manifest $Manifest -RestorePointId $RestorePointId)
                objectInventory = $targetInventory
                finalFiles = @(New-DccFinalFilesFromReplay -Manifest $Manifest -ReplayPointIds @(Get-DccReplayPointIds -Manifest $Manifest -RestorePointId $RestorePointId -Errors $Errors) -TargetInventory $targetInventory)
            })
        }
    }

    Add-DccDiagnostic -Errors $Errors -Code 'restore_point_unreachable' -Scope 'incrementalChain' `
        -Message "Restore point $RestorePointId is not reachable from baseline $baselineRestorePointId." `
        -Impact 'The restore chain cannot replay to the requested point without skipping or inventing segments.' `
        -NextStep 'Select a restore point listed in the manifest chain or rebuild the incremental chain from the last valid baseline.'
    return $null
}

function Test-DccChainContract {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors
    )

    if ([string](Get-DccProperty -Object $Manifest -Name 'targetEnvironment') -ne 'test') {
        Add-DccDiagnostic -Errors $Errors -Code 'target_environment_invalid' -Scope 'targetEnvironment' `
            -Message 'DCC chain validation only accepts targetEnvironment test.' `
            -Impact 'The validator cannot prove the backup belongs to the protected test environment.' `
            -NextStep 'Regenerate the backup manifest with targetEnvironment test and target host proof.'
    }

    if ([string](Get-DccProperty -Object $Manifest -Name 'schemaVersion') -ne 'dcc-backup-manifest-v1') {
        Add-DccDiagnostic -Errors $Errors -Code 'schema_version_invalid' -Scope 'schemaVersion' `
            -Message 'schemaVersion must be dcc-backup-manifest-v1 before restore preflight can pass.' `
            -Impact 'The restore code cannot prove it understands the DCC backup manifest contract.' `
            -NextStep 'Regenerate the DCC backup manifest with the supported schemaVersion or add an explicit compatibility adapter.'
    }

    if ([string](Get-DccProperty -Object $Manifest -Name 'chainStatus') -ne 'COMPLETE') {
        Add-DccDiagnostic -Errors $Errors -Code 'chain_status_incomplete' -Scope 'chainStatus' `
            -Message 'chainStatus must be COMPLETE before a DCC restore chain is selectable.' `
            -Impact 'Restore could start from an incomplete or partially written incremental chain.' `
            -NextStep 'Rebuild the backup point after all manifest, object inventory, database snapshot, and checksum steps complete.'
    }

    if ([string](Get-DccProperty -Object $Manifest -Name 'backupMode') -eq 'incremental') {
        if ([string]::IsNullOrWhiteSpace([string](Get-DccProperty -Object $Manifest -Name 'baselineBackupId')) `
                -or [string]::IsNullOrWhiteSpace([string](Get-DccProperty -Object $Manifest -Name 'baselineRestorePointId')) `
                -or [string]::IsNullOrWhiteSpace([string](Get-DccProperty -Object $Manifest -Name 'previousBackupId')) `
                -or [string]::IsNullOrWhiteSpace([string](Get-DccProperty -Object $Manifest -Name 'previousRestorePointId'))) {
            Add-DccDiagnostic -Errors $Errors -Code 'previous_pointer_missing' -Scope 'incrementalPointers' `
                -Message 'Incremental DCC manifest must declare baseline and previous backup/restore point pointers.' `
                -Impact 'Restore replay cannot prove which baseline and previous segment the selected point depends on.' `
                -NextStep 'Regenerate the incremental manifest from the last valid manifest and preserve baseline/previous pointers.'
        }
    }

    if ((Get-DccProperty -Object $Manifest -Name 'restoreVerified') -eq $true) {
        $rehearsal = Get-DccProperty -Object $Manifest -Name 'restoreRehearsal'
        if ([string](Get-DccProperty -Object $rehearsal -Name 'status') -ne 'passed') {
            Add-DccDiagnostic -Errors $Errors -Code 'restore_rehearsal_missing' -Scope 'restoreRehearsal' `
                -Message 'restoreVerified cannot be true without passed restore rehearsal evidence.' `
                -Impact 'A backup could be presented as recoverable without any restore proof.' `
                -NextStep 'Run a restore rehearsal and attach passed evidence before setting restoreVerified true.'
        }
    }

    $fullBaseline = Get-DccProperty -Object $Manifest -Name 'fullBaseline'
    $expectedFrom = [string](Get-DccProperty -Object $fullBaseline -Name 'restorePointId')
    $baselineChecksum = [string](Get-DccProperty -Object $fullBaseline -Name 'checksum')
    if (-not (Test-DccSha256Value -Value $baselineChecksum)) {
        Add-DccDiagnostic -Errors $Errors -Code 'baseline_checksum_invalid' -Scope 'fullBaseline.checksum' `
            -Message 'fullBaseline.checksum must be a sha256 digest.' `
            -Impact 'The restore chain cannot prove that the baseline manifest is intact.' `
            -NextStep 'Recompute the baseline checksum and regenerate the manifest.'
    }
    if ([string]::IsNullOrWhiteSpace($expectedFrom)) {
        Add-DccDiagnostic -Errors $Errors -Code 'full_baseline_missing' -Scope 'fullBaseline' `
            -Message 'fullBaseline.restorePointId is required.' `
            -Impact 'The incremental chain has no baseline to start from.' `
            -NextStep 'Create a full baseline manifest before creating incremental segments.'
        return
    }

    $seenTargets = New-Object System.Collections.Generic.HashSet[string]
    foreach ($segment in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'incrementalChain'))) {
        $from = [string](Get-DccProperty -Object $segment -Name 'from')
        $to = [string](Get-DccProperty -Object $segment -Name 'to')
        $checksum = [string](Get-DccProperty -Object $segment -Name 'checksum')
        if (-not (Test-DccSha256Value -Value $checksum)) {
            Add-DccDiagnostic -Errors $Errors -Code 'segment_checksum_invalid' -Scope 'incrementalChain.checksum' `
                -Message "Incremental segment $from to $to has an invalid checksum." `
                -Impact 'Restore replay cannot prove that the incremental segment is intact.' `
                -NextStep 'Recompute the segment checksum from database records and object inventory, then regenerate the manifest.'
            return
        }
        if ($from -ne $expectedFrom -or [string]::IsNullOrWhiteSpace($to) -or [string]::IsNullOrWhiteSpace($checksum) -or $seenTargets.Contains($to)) {
            Add-DccDiagnostic -Errors $Errors -Code 'incremental_chain_broken' -Scope 'incrementalChain' `
                -Message "Incremental segment expected from $expectedFrom but found from $from to $to." `
                -Impact 'Restore replay would skip, reorder, or duplicate an incremental segment.' `
                -NextStep 'Rebuild the chain from the last valid restore point and verify segment checksums.'
            return
        }
        [void]$seenTargets.Add($to)
        $expectedFrom = $to
    }

    $inventoryMap = New-DccInventoryMap -Manifest $Manifest
    foreach ($restorePoint in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'restorePoints'))) {
        $restorePointId = [string](Get-DccProperty -Object $restorePoint -Name 'id')
        if ([string]::IsNullOrWhiteSpace($restorePointId)) {
            continue
        }
        if ([string](Get-DccProperty -Object $restorePoint -Name 'databaseRestorePointId') -ne $restorePointId `
                -or [string](Get-DccProperty -Object $restorePoint -Name 'objectInventoryRestorePointId') -ne $restorePointId) {
            Add-DccDiagnostic -Errors $Errors -Code 'restore_point_inconsistent' -Scope 'restorePoints' `
                -Message "Restore point $restorePointId does not bind database and object inventory to the same point." `
                -Impact 'Database records and object files may restore to different points in time.' `
                -NextStep 'Regenerate the backup manifest so database and object inventory share one restorePointId.'
        }
        if (-not $inventoryMap.ContainsKey($restorePointId)) {
            Add-DccDiagnostic -Errors $Errors -Code 'object_inventory_missing' -Scope 'objectInventories' `
                -Message "Missing object inventory for restore point $restorePointId." `
                -Impact 'Restore cannot prove which object files belong to the restore point.' `
                -NextStep 'Generate object inventory for every restore point.'
        }
    }

    foreach ($inventory in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'objectInventories'))) {
        $restorePointId = [string](Get-DccProperty -Object $inventory -Name 'restorePointId')
        foreach ($object in (ConvertTo-DccArray -Value (Get-DccProperty -Object $inventory -Name 'objects'))) {
            $fileKey = [string](Get-DccProperty -Object $object -Name 'fileKey')
            $state = [string](Get-DccProperty -Object $object -Name 'state')
            $contentHash = [string](Get-DccProperty -Object $object -Name 'contentHash')
            $storedHash = [string](Get-DccProperty -Object $object -Name 'storedHash')
            if ($state -eq 'active') {
                if ((Get-DccProperty -Object $object -Name 'present') -ne $true) {
                    Add-DccDiagnostic -Errors $Errors -Code 'object_missing' -Scope 'objectInventories' `
                        -Message "Active object $fileKey is missing at restore point $restorePointId." `
                        -Impact 'The database record would restore but the file object would be unavailable.' `
                        -NextStep 'Copy the missing object into the content-addressed object store and regenerate inventory.'
                }
                if ($contentHash -ne $storedHash) {
                    Add-DccDiagnostic -Errors $Errors -Code 'object_hash_mismatch' -Scope 'objectInventories' `
                        -Message "Object $fileKey hash mismatch at restore point $restorePointId." `
                        -Impact 'The restored file content would not match the recorded database state.' `
                        -NextStep 'Recompute object checksums and replace the corrupted object entry.'
                }
            }
            if ($state -eq 'deleted' -and -not (Test-DccEventExists -Manifest $Manifest -RestorePointId $restorePointId -FileKey $fileKey -EventType 'delete')) {
                Add-DccDiagnostic -Errors $Errors -Code 'dcc_delete_event_missing' -Scope 'dccEvents' `
                    -Message "Deleted file $fileKey at restore point $restorePointId has no delete event." `
                    -Impact 'A later restore could make a deleted file visible again.' `
                    -NextStep 'Record the delete event in the incremental segment before marking the point recoverable.'
            }
            if ($state -eq 'voided' -and -not (Test-DccEventExists -Manifest $Manifest -RestorePointId $restorePointId -FileKey $fileKey -EventType 'void')) {
                Add-DccDiagnostic -Errors $Errors -Code 'void_event_missing' -Scope 'dccEvents' `
                    -Message "Voided file $fileKey at restore point $restorePointId has no void event." `
                    -Impact 'A restore could lose the business visibility state for a voided document.' `
                    -NextStep 'Record the void event in the incremental segment.'
            }
            if ($state -eq 'archived' -and -not (Test-DccEventExists -Manifest $Manifest -RestorePointId $restorePointId -FileKey $fileKey -EventType 'archive')) {
                Add-DccDiagnostic -Errors $Errors -Code 'archive_event_missing' -Scope 'dccEvents' `
                    -Message "Archived file $fileKey at restore point $restorePointId has no archive event." `
                    -Impact 'A restore could lose the archive visibility state for a document.' `
                    -NextStep 'Record the archive event in the incremental segment.'
            }
        }
    }

    foreach ($record in (ConvertTo-DccArray -Value (Get-DccProperty -Object $Manifest -Name 'databaseRecords'))) {
        if ((Get-DccProperty -Object $record -Name 'permissionChanged') -eq $true) {
            $restorePointId = [string](Get-DccProperty -Object $record -Name 'restorePointId')
            $fileKey = [string](Get-DccProperty -Object $record -Name 'fileKey')
            if (-not (Test-DccEventExists -Manifest $Manifest -RestorePointId $restorePointId -FileKey $fileKey -EventType 'permission_change')) {
                Add-DccDiagnostic -Errors $Errors -Code 'permission_event_missing' -Scope 'dccEvents' `
                    -Message "Permission change for file $fileKey at restore point $restorePointId has no event." `
                    -Impact 'A restore could apply the wrong DCC permissions.' `
                    -NextStep 'Record permission_change in the incremental segment and rerun validation.'
            }
        }
    }
}

function Test-DccBackupChainManifest {
    param(
        [Parameter(Mandatory = $true)]$Manifest
    )

    $errors = New-Object System.Collections.ArrayList
    Test-DccChainContract -Manifest $Manifest -Errors $errors

    return [pscustomobject]([ordered]@{
            status = if ($errors.Count -gt 0) { 'blocked' } else { 'passed' }
            errors = @($errors.ToArray())
            checks = @([pscustomobject]([ordered]@{
                        code = 'dcc_backup_chain_contract'
                        status = if ($errors.Count -gt 0) { 'blocked' } else { 'passed' }
                    }))
        })
}

function Invoke-DccBackupChainValidation {
    param(
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)][string]$BackupManifestPath,
        [string]$RestorePoint,
        [string]$ExpectFile,
        [string]$ExpectState,
        [string]$ExpectContentHash,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    try {
        $manifest = Read-DccBackupJson -Path $BackupManifestPath
    } catch {
        $payload = [pscustomobject]([ordered]@{
            operationId = 'op-dcc-backup-chain-' + [guid]::NewGuid().ToString()
            mode = $Mode
            backupId = ''
            restorePoint = $RestorePoint
            status = 'failed'
            checkedAt = (Get-Date).ToString('o')
            errors = @((New-DccBackupDiagnostic -Code 'backup_manifest_input_invalid' -Scope 'input' -Message ([string]$_.Exception.Message) -Impact 'The backup manifest cannot be read.' -NextStep 'Fix JSON input and rerun validation.'))
            checks = @()
        })
        Write-DccBackupJson -Payload $payload -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $payload; ExitCode = 1 }
    }

    $validation = Test-DccBackupChainManifest -Manifest $manifest
    $errors = New-Object System.Collections.ArrayList
    foreach ($error in (ConvertTo-DccArray -Value $validation.errors)) {
        [void]$errors.Add($error)
    }

    if ($Mode -eq 'validate-point') {
        if ([string]::IsNullOrWhiteSpace($RestorePoint) -or [string]::IsNullOrWhiteSpace($ExpectFile) -or [string]::IsNullOrWhiteSpace($ExpectState)) {
            Add-DccDiagnostic -Errors $errors -Code 'restore_point_expectation_missing' -Scope 'expectation' `
                -Message 'RestorePoint, ExpectFile, and ExpectState are required for validate-point.' `
                -Impact 'The validator cannot prove the requested restore semantics.' `
                -NextStep 'Provide restore point expectations and rerun validation.'
        } else {
            $object = Get-DccObjectAtRestorePoint -Manifest $manifest -RestorePointId $RestorePoint -FileKey $ExpectFile
            if ($null -eq $object) {
                Add-DccDiagnostic -Errors $errors -Code 'restore_point_file_missing' -Scope 'objectInventories' `
                    -Message "Expected file $ExpectFile is missing from restore point $RestorePoint." `
                    -Impact 'The requested restore point cannot recreate the expected DCC file state.' `
                    -NextStep 'Regenerate object inventory for the restore point.'
            } else {
                $actualState = [string](Get-DccProperty -Object $object -Name 'state')
                $actualHash = [string](Get-DccProperty -Object $object -Name 'contentHash')
                if ($actualState -ne $ExpectState) {
                    Add-DccDiagnostic -Errors $errors -Code 'restore_point_state_mismatch' -Scope 'restorePoint' `
                        -Message "Expected $ExpectFile state $ExpectState at $RestorePoint but found $actualState." `
                        -Impact 'The restore point does not match the expected DCC visibility state.' `
                        -NextStep 'Choose the correct restore point or regenerate the backup manifest.'
                }
                if (-not [string]::IsNullOrWhiteSpace($ExpectContentHash) -and $actualHash -ne $ExpectContentHash) {
                    Add-DccDiagnostic -Errors $errors -Code 'restore_point_hash_mismatch' -Scope 'restorePoint' `
                        -Message "Expected $ExpectFile hash $ExpectContentHash at $RestorePoint but found $actualHash." `
                        -Impact 'The restore point would restore different file content.' `
                        -NextStep 'Choose the correct restore point or repair object inventory.'
                }
            }
        }
    }
    $restorePlan = $null
    if ($Mode -eq 'plan-restore') {
        $restorePlan = New-DccRestoreReplayPlan -Manifest $manifest -RestorePointId $RestorePoint -Errors $errors
    }

    $status = if ($errors.Count -gt 0) { 'blocked' } else { 'passed' }
    $payload = [pscustomobject]([ordered]@{
        operationId = 'op-dcc-backup-chain-' + [guid]::NewGuid().ToString()
        mode = $Mode
        backupId = [string](Get-DccProperty -Object $manifest -Name 'backupId')
        restorePoint = $RestorePoint
        status = $status
        checkedAt = (Get-Date).ToString('o')
        errors = @($errors.ToArray())
        restorePlan = $restorePlan
        checks = @([pscustomobject]([ordered]@{
            code = 'dcc_backup_chain_contract'
            status = if ($errors.Count -gt 0) { 'blocked' } else { 'passed' }
        }))
    })
    Write-DccBackupJson -Payload $payload -OutputPath $OutputPath
    $exitCode = if ($errors.Count -gt 0) { 2 } else { 0 }
    return [pscustomobject]@{ Payload = $payload; ExitCode = $exitCode }
}

Export-ModuleMember -Function Invoke-DccBackupChainValidation, Test-DccBackupChainManifest
