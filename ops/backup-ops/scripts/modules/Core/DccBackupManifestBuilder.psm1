Set-StrictMode -Version Latest

$script:DccBackupUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Get-DccBuilderProperty {
    param(
        $Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function ConvertTo-DccBuilderArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Read-DccBuilderJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-DccBuilderJson {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth 60
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, $script:DccBackupUtf8NoBom)
}

function New-DccBuilderDiagnostic {
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

function Add-DccBuilderDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    [void]$Errors.Add((New-DccBuilderDiagnostic -Code $Code -Scope $Scope -Message $Message -Impact $Impact -NextStep $NextStep))
}

function Get-DccBuilderString {
    param($Value)

    if ($null -eq $Value) {
        return ''
    }
    return ([string]$Value).Trim()
}

function ConvertTo-DccBuilderSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return 'sha256:' + ([System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant())
}

function New-DccObjectByPathMap {
    param($ObjectInventory)

    $map = @{}
    foreach ($object in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $ObjectInventory -Name 'objects'))) {
        $path = Get-DccBuilderString (Get-DccBuilderProperty -Object $object -Name 'path')
        if (-not [string]::IsNullOrWhiteSpace($path)) {
            $map[$path] = $object
        }
    }
    return $map
}

function Get-DccLastRestorePointId {
    param($Manifest)

    $last = ''
    foreach ($segment in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $Manifest -Name 'incrementalChain'))) {
        $to = Get-DccBuilderString (Get-DccBuilderProperty -Object $segment -Name 'to')
        if (-not [string]::IsNullOrWhiteSpace($to)) {
            $last = $to
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($last)) {
        return $last
    }
    $baseline = Get-DccBuilderProperty -Object $Manifest -Name 'fullBaseline'
    return Get-DccBuilderString (Get-DccBuilderProperty -Object $baseline -Name 'restorePointId')
}

function New-DccRecordMapForRestorePoint {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId
    )

    $map = @{}
    foreach ($record in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $Manifest -Name 'databaseRecords'))) {
        if ((Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'restorePointId')) -ne $RestorePointId) {
            continue
        }
        $fileKey = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'fileKey')
        if (-not [string]::IsNullOrWhiteSpace($fileKey)) {
            $map[$fileKey] = $record
        }
    }
    return $map
}

function New-DccObjectMapForRestorePoint {
    param(
        $Manifest,
        [Parameter(Mandatory = $true)][string]$RestorePointId
    )

    $map = @{}
    foreach ($inventory in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $Manifest -Name 'objectInventories'))) {
        if ((Get-DccBuilderString (Get-DccBuilderProperty -Object $inventory -Name 'restorePointId')) -ne $RestorePointId) {
            continue
        }
        foreach ($object in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $inventory -Name 'objects'))) {
            $fileKey = Get-DccBuilderString (Get-DccBuilderProperty -Object $object -Name 'fileKey')
            if (-not [string]::IsNullOrWhiteSpace($fileKey)) {
                $map[$fileKey] = $object
            }
        }
    }
    return $map
}

function Get-DccRecordState {
    param($Record)

    $state = (Get-DccBuilderString (Get-DccBuilderProperty -Object $Record -Name 'state')).ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($state)) {
        return 'active'
    }
    return $state
}

function New-DccCurrentRecordModels {
    param(
        [Parameter(Mandatory = $true)]$Snapshot,
        [Parameter(Mandatory = $true)]$ObjectInventory,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)]$PreviousRecordMap,
        [Parameter(Mandatory = $true)]$PreviousObjectMap,
        [Parameter(Mandatory = $true)]$Errors
    )

    $objectByPath = New-DccObjectByPathMap -ObjectInventory $ObjectInventory
    $currentRecordMap = @{}
    $currentObjectMap = @{}
    $databaseRecords = [System.Collections.Generic.List[object]]::new()
    $inventoryObjects = [System.Collections.Generic.List[object]]::new()

    foreach ($record in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $Snapshot -Name 'controlledFiles'))) {
        $fileKey = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'fileKey')
        if ([string]::IsNullOrWhiteSpace($fileKey)) {
            Add-DccBuilderDiagnostic -Errors $Errors -Code 'dcc_file_key_missing' -Scope 'controlledFiles' `
                -Message 'DCC snapshot record is missing fileKey.' `
                -Impact 'The backup manifest cannot bind database records to object inventory.' `
                -NextStep 'Regenerate the DCC snapshot with fileKey for every controlled file.'
            continue
        }

        $state = Get-DccRecordState -Record $record
        $objectRefs = [System.Collections.Generic.List[object]]::new()
        $hashParts = [System.Collections.Generic.List[string]]::new()
        foreach ($ref in (ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $record -Name 'objects'))) {
            $path = Get-DccBuilderString (Get-DccBuilderProperty -Object $ref -Name 'path')
            if ([string]::IsNullOrWhiteSpace($path)) {
                continue
            }
            $inventoryObject = $null
            if ($objectByPath.ContainsKey($path)) {
                $inventoryObject = $objectByPath[$path]
            }
            if ($null -eq $inventoryObject -and $state -ne 'deleted') {
                Add-DccBuilderDiagnostic -Errors $Errors -Code 'dcc_object_inventory_missing' -Scope "controlledFiles.$fileKey.objects" `
                    -Message "DCC file $fileKey references object $path but the object inventory does not contain it." `
                    -Impact 'The backup would restore a database record without the required file object.' `
                    -NextStep 'Regenerate the object inventory from the target bucket before building the DCC backup manifest.'
                continue
            }
            if ($null -ne $inventoryObject) {
                $sha = Get-DccBuilderString (Get-DccBuilderProperty -Object $inventoryObject -Name 'sha256')
                if ([string]::IsNullOrWhiteSpace($sha)) {
                    $sha = Get-DccBuilderString (Get-DccBuilderProperty -Object $inventoryObject -Name 'etag')
                }
                $repositoryKey = Get-DccBuilderString (Get-DccBuilderProperty -Object $inventoryObject -Name 'repositoryKey')
                if ([string]::IsNullOrWhiteSpace($repositoryKey)) {
                    $repositoryKey = $sha
                }
                $role = Get-DccBuilderString (Get-DccBuilderProperty -Object $ref -Name 'role')
                if ([string]::IsNullOrWhiteSpace($role)) {
                    $role = 'file'
                }
                $hashParts.Add("$role|$path|$sha") | Out-Null
                $objectRefs.Add([pscustomobject]([ordered]@{
                    role = $role
                    path = $path
                    sha256 = $sha
                    repositoryKey = $repositoryKey
                    size = Get-DccBuilderProperty -Object $inventoryObject -Name 'size'
                    lastModified = Get-DccBuilderString (Get-DccBuilderProperty -Object $inventoryObject -Name 'lastModified')
                })) | Out-Null
            }
        }

        $databaseDigest = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'databaseDigest')
        $permissionDigest = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'permissionDigest')
        $hashInput = ($fileKey + '|' + $databaseDigest + '|' + (($hashParts | Sort-Object) -join ';'))
        $contentHash = ConvertTo-DccBuilderSha256 -Value $hashInput
        $present = $state -ne 'deleted' -and $objectRefs.Count -gt 0

        $databaseRecord = [pscustomobject]([ordered]@{
            restorePointId = $RestorePointId
            fileKey = $fileKey
            controlledFileId = Get-DccBuilderProperty -Object $record -Name 'controlledFileId'
            tenantId = Get-DccBuilderProperty -Object $record -Name 'tenantId'
            fileNumber = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'fileNumber')
            versionNo = Get-DccBuilderString (Get-DccBuilderProperty -Object $record -Name 'versionNo')
            state = $state
            databaseDigest = $databaseDigest
            permissionDigest = $permissionDigest
            permissionChanged = $false
        })
        $inventoryObject = [pscustomobject]([ordered]@{
            fileKey = $fileKey
            state = $state
            contentHash = $contentHash
            storedHash = $contentHash
            present = $present
            objectRefs = @($objectRefs)
        })
        $currentRecordMap[$fileKey] = $databaseRecord
        $currentObjectMap[$fileKey] = $inventoryObject
        $databaseRecords.Add($databaseRecord) | Out-Null
        $inventoryObjects.Add($inventoryObject) | Out-Null
    }

    foreach ($previousKey in @($PreviousRecordMap.Keys)) {
        if ($currentRecordMap.ContainsKey($previousKey)) {
            continue
        }
        $previousRecord = $PreviousRecordMap[$previousKey]
        $previousObject = if ($PreviousObjectMap.ContainsKey($previousKey)) { $PreviousObjectMap[$previousKey] } else { $null }
        if ((Get-DccRecordState -Record $previousRecord) -eq 'deleted') {
            continue
        }
        $contentHash = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousObject -Name 'contentHash')
        if ([string]::IsNullOrWhiteSpace($contentHash)) {
            $contentHash = ConvertTo-DccBuilderSha256 -Value ($previousKey + '|deleted')
        }
        $deletedRecord = [pscustomobject]([ordered]@{
            restorePointId = $RestorePointId
            fileKey = $previousKey
            controlledFileId = Get-DccBuilderProperty -Object $previousRecord -Name 'controlledFileId'
            tenantId = Get-DccBuilderProperty -Object $previousRecord -Name 'tenantId'
            fileNumber = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousRecord -Name 'fileNumber')
            versionNo = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousRecord -Name 'versionNo')
            state = 'deleted'
            databaseDigest = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousRecord -Name 'databaseDigest')
            permissionDigest = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousRecord -Name 'permissionDigest')
            permissionChanged = $false
        })
        $deletedObject = [pscustomobject]([ordered]@{
            fileKey = $previousKey
            state = 'deleted'
            contentHash = $contentHash
            storedHash = $contentHash
            present = $false
            objectRefs = @()
        })
        $currentRecordMap[$previousKey] = $deletedRecord
        $currentObjectMap[$previousKey] = $deletedObject
        $databaseRecords.Add($deletedRecord) | Out-Null
        $inventoryObjects.Add($deletedObject) | Out-Null
    }

    return [pscustomobject]@{
        DatabaseRecords = @($databaseRecords | Sort-Object fileKey)
        InventoryObjects = @($inventoryObjects | Sort-Object fileKey)
        RecordMap = $currentRecordMap
        ObjectMap = $currentObjectMap
    }
}

function New-DccBuilderEvents {
    param(
        [Parameter(Mandatory = $true)]$CurrentRecordMap,
        [Parameter(Mandatory = $true)]$CurrentObjectMap,
        [Parameter(Mandatory = $true)]$PreviousRecordMap,
        [Parameter(Mandatory = $true)]$PreviousObjectMap,
        [Parameter(Mandatory = $true)][string]$RestorePointId
    )

    $events = [System.Collections.Generic.List[object]]::new()
    foreach ($fileKey in @($CurrentRecordMap.Keys | Sort-Object)) {
        $currentRecord = $CurrentRecordMap[$fileKey]
        $currentObject = $CurrentObjectMap[$fileKey]
        $currentState = Get-DccRecordState -Record $currentRecord
        $previousRecord = if ($PreviousRecordMap.ContainsKey($fileKey)) { $PreviousRecordMap[$fileKey] } else { $null }
        $previousObject = if ($PreviousObjectMap.ContainsKey($fileKey)) { $PreviousObjectMap[$fileKey] } else { $null }
        $previousState = Get-DccRecordState -Record $previousRecord
        $eventTypes = [System.Collections.Generic.List[string]]::new()

        if ($null -eq $previousRecord) {
            if ($currentState -eq 'deleted') {
                $eventTypes.Add('delete') | Out-Null
            } else {
                $eventTypes.Add('add') | Out-Null
            }
        } elseif ($currentState -ne $previousState) {
            if ($currentState -eq 'deleted') {
                $eventTypes.Add('delete') | Out-Null
            } elseif ($currentState -eq 'voided') {
                $eventTypes.Add('void') | Out-Null
            } elseif ($currentState -eq 'archived') {
                $eventTypes.Add('archive') | Out-Null
            } else {
                $eventTypes.Add('modify') | Out-Null
            }
        }

        $currentHash = Get-DccBuilderString (Get-DccBuilderProperty -Object $currentObject -Name 'contentHash')
        $previousHash = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousObject -Name 'contentHash')
        if ($null -ne $previousRecord -and $currentState -ne 'deleted' -and $currentHash -ne $previousHash) {
            $eventTypes.Add('modify') | Out-Null
        }

        $currentPermission = Get-DccBuilderString (Get-DccBuilderProperty -Object $currentRecord -Name 'permissionDigest')
        $previousPermission = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousRecord -Name 'permissionDigest')
        if ($null -ne $previousRecord -and $currentPermission -ne $previousPermission) {
            $eventTypes.Add('permission_change') | Out-Null
            $currentRecord.permissionChanged = $true
        }

        foreach ($eventType in @($eventTypes | Select-Object -Unique)) {
            $events.Add([pscustomobject]([ordered]@{
                restorePointId = $RestorePointId
                fileKey = $fileKey
                eventType = $eventType
                contentHash = $currentHash
            })) | Out-Null
        }
    }
    return @($events)
}

function New-DccBuilderChangeSummary {
    param(
        [Parameter(Mandatory = $true)]$CurrentRecordMap,
        [Parameter(Mandatory = $true)]$CurrentObjectMap,
        [Parameter(Mandatory = $true)]$PreviousObjectMap,
        [Parameter(Mandatory = $true)]$CurrentEvents
    )

    $addedRecords = New-Object System.Collections.Generic.HashSet[string]
    $changedRecords = New-Object System.Collections.Generic.HashSet[string]
    $deletedRecords = New-Object System.Collections.Generic.HashSet[string]
    $invalidatedRecords = New-Object System.Collections.Generic.HashSet[string]
    foreach ($event in (ConvertTo-DccBuilderArray -Value $CurrentEvents)) {
        $fileKey = Get-DccBuilderString (Get-DccBuilderProperty -Object $event -Name 'fileKey')
        $eventType = Get-DccBuilderString (Get-DccBuilderProperty -Object $event -Name 'eventType')
        if ([string]::IsNullOrWhiteSpace($fileKey)) {
            continue
        }
        if ($eventType -eq 'add') {
            [void]$addedRecords.Add($fileKey)
        } elseif ($eventType -eq 'delete') {
            [void]$deletedRecords.Add($fileKey)
        } elseif ($eventType -in @('modify', 'permission_change', 'archive')) {
            [void]$changedRecords.Add($fileKey)
        } elseif ($eventType -eq 'void') {
            [void]$invalidatedRecords.Add($fileKey)
        }
    }

    $addedObjects = 0
    $changedObjects = 0
    $reusedObjects = 0
    $tombstoneObjects = 0
    foreach ($fileKey in @($CurrentObjectMap.Keys)) {
        $currentObject = $CurrentObjectMap[$fileKey]
        $currentState = Get-DccRecordState -Record $currentObject
        if ($currentState -eq 'deleted') {
            $tombstoneObjects++
            continue
        }
        $previousObject = if ($PreviousObjectMap.ContainsKey($fileKey)) { $PreviousObjectMap[$fileKey] } else { $null }
        if ($null -eq $previousObject) {
            $addedObjects++
            continue
        }
        $currentHash = Get-DccBuilderString (Get-DccBuilderProperty -Object $currentObject -Name 'contentHash')
        $previousHash = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousObject -Name 'contentHash')
        if ($currentHash -eq $previousHash) {
            $reusedObjects++
        } else {
            $changedObjects++
        }
    }

    return [pscustomobject]([ordered]@{
        addedRecords = $addedRecords.Count
        changedRecords = $changedRecords.Count
        deletedRecords = $deletedRecords.Count
        invalidatedRecords = $invalidatedRecords.Count
        addedObjects = $addedObjects
        changedObjects = $changedObjects
        reusedObjects = $reusedObjects
        tombstoneObjects = $tombstoneObjects
    })
}

function New-DccBuilderBlockedSummary {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        $Snapshot,
        $ObjectInventory
    )

    $codeCounts = @{}
    $missingRefs = [ordered]@{}
    $missingReferenceCount = 0
    foreach ($error in $Errors) {
        $code = Get-DccBuilderString (Get-DccBuilderProperty -Object $error -Name 'code')
        if ([string]::IsNullOrWhiteSpace($code)) {
            $code = 'unknown'
        }
        if (-not $codeCounts.ContainsKey($code)) {
            $codeCounts[$code] = 0
        }
        $codeCounts[$code]++

        if ($code -ne 'dcc_object_inventory_missing') {
            continue
        }
        $missingReferenceCount++
        $scope = Get-DccBuilderString (Get-DccBuilderProperty -Object $error -Name 'scope')
        $message = Get-DccBuilderString (Get-DccBuilderProperty -Object $error -Name 'message')
        $fileKey = ''
        $path = ''
        if ($scope -match '^controlledFiles\.(.+)\.objects$') {
            $fileKey = $Matches[1]
        }
        if ($message -match ' references object (.+) but the object inventory') {
            $path = $Matches[1]
        }
        if ([string]::IsNullOrWhiteSpace($fileKey) -or [string]::IsNullOrWhiteSpace($path)) {
            continue
        }
        $key = "$fileKey|$path"
        if (-not $missingRefs.Contains($key)) {
            $missingRefs[$key] = [pscustomobject]([ordered]@{
                fileKey = $fileKey
                path = $path
            })
        }
    }

    $errorCodeSummary = [System.Collections.Generic.List[object]]::new()
    foreach ($code in @($codeCounts.Keys | Sort-Object)) {
        $errorCodeSummary.Add([pscustomobject]([ordered]@{
            code = $code
            count = $codeCounts[$code]
        })) | Out-Null
    }

    $missingReferences = [System.Collections.Generic.List[object]]::new()
    $missingSamples = [System.Collections.Generic.List[object]]::new()
    foreach ($key in @($missingRefs.Keys | Sort-Object)) {
        $missingReferences.Add($missingRefs[$key]) | Out-Null
        if ($missingSamples.Count -ge 20) {
            continue
        }
        $missingSamples.Add($missingRefs[$key]) | Out-Null
    }

    $controlledFileRecordCount = @((ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $Snapshot -Name 'controlledFiles'))).Count
    $inventoryObjectCount = @((ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $ObjectInventory -Name 'objects'))).Count

    return [pscustomobject]([ordered]@{
        errorCodes = @($errorCodeSummary)
        dccObjectInventoryCoverage = [pscustomobject]([ordered]@{
            controlledFileRecordCount = $controlledFileRecordCount
            inventoryObjectCount = $inventoryObjectCount
            missingReferenceCount = $missingReferenceCount
            uniqueMissingReferenceCount = $missingRefs.Count
            missingReferences = @($missingReferences)
            samples = @($missingSamples)
        })
    })
}

function New-DccBuilderBlockedPayload {
    param(
        [Parameter(Mandatory = $true)][string]$BackupId,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)]$Errors,
        $Snapshot,
        $ObjectInventory
    )

    return [pscustomobject]([ordered]@{
        operationId = 'op-dcc-manifest-build-' + [guid]::NewGuid().ToString()
        backupId = $BackupId
        restorePointId = $RestorePointId
        status = 'blocked'
        checkedAt = [System.DateTimeOffset]::Now.ToString('o')
        summary = New-DccBuilderBlockedSummary -Errors $Errors -Snapshot $Snapshot -ObjectInventory $ObjectInventory
        errors = @($Errors.ToArray())
    })
}

function Invoke-DccBackupManifestBuild {
    param(
        [Parameter(Mandatory = $true)][string]$BackupId,
        [Parameter(Mandatory = $true)][string]$RestorePointId,
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][string]$DccSnapshotPath,
        [Parameter(Mandatory = $true)][string]$ObjectInventoryPath,
        [string]$PreviousManifestPath,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $errors = New-Object System.Collections.ArrayList
    $expectedTargetHost = switch ($TargetEnvironment) {
        'test' { '172.30.30.58' }
        'production' { '172.30.30.57' }
        'prod' { '172.30.30.57' }
        default { '' }
    }
    if ([string]::IsNullOrWhiteSpace($expectedTargetHost)) {
        Add-DccBuilderDiagnostic -Errors $errors -Code 'target_environment_invalid' -Scope 'targetEnvironment' `
            -Message 'DCC backup manifest builder only accepts targetEnvironment test, prod, or production.' `
            -Impact 'The manifest cannot prove it belongs to a protected backup flow.' `
            -NextStep 'Run the builder with TargetEnvironment test or production and target host proof.'
    }
    if ([string]::IsNullOrWhiteSpace($expectedTargetHost) -or $TargetHost -ne $expectedTargetHost) {
        Add-DccBuilderDiagnostic -Errors $errors -Code 'target_host_invalid' -Scope 'targetHost' `
            -Message "DCC backup manifest target host is invalid for $TargetEnvironment; expected $expectedTargetHost, got $TargetHost." `
            -Impact 'The manifest could be mistaken for an unapproved environment.' `
            -NextStep 'Regenerate the manifest with TargetHost 172.30.30.58 for test or 172.30.30.57 for production.'
    }

    try {
        $snapshot = Read-DccBuilderJson -Path $DccSnapshotPath
        $objectInventory = Read-DccBuilderJson -Path $ObjectInventoryPath
        $previousManifest = $null
        if (-not [string]::IsNullOrWhiteSpace($PreviousManifestPath)) {
            $previousManifest = Read-DccBuilderJson -Path $PreviousManifestPath
        }
    } catch {
        Add-DccBuilderDiagnostic -Errors $errors -Code 'input_json_invalid' -Scope 'input' `
            -Message ([string]$_.Exception.Message) `
            -Impact 'The DCC backup manifest cannot be built from unreadable JSON input.' `
            -NextStep 'Fix the snapshot, object inventory, or previous manifest JSON and rerun.'
        $blocked = New-DccBuilderBlockedPayload -BackupId $BackupId -RestorePointId $RestorePointId -Errors $errors
        Write-DccBuilderJson -Payload $blocked -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $blocked; ExitCode = 2 }
    }

    $previousPoint = ''
    $previousRecords = @{}
    $previousObjects = @{}
    $fullBaseline = $null
    $incrementalChain = @()
    $restorePoints = @()
    $objectInventories = @()
    $databaseRecords = @()
    $dccEvents = @()
    if ($null -ne $previousManifest) {
        $previousPoint = Get-DccLastRestorePointId -Manifest $previousManifest
        if ([string]::IsNullOrWhiteSpace($previousPoint)) {
            Add-DccBuilderDiagnostic -Errors $errors -Code 'previous_restore_point_missing' -Scope 'previousManifest' `
                -Message 'Previous DCC manifest has no full baseline or incremental target restore point.' `
                -Impact 'The builder cannot append a deterministic incremental segment.' `
                -NextStep 'Rebuild from a valid full baseline manifest.'
        } else {
            $previousRecords = New-DccRecordMapForRestorePoint -Manifest $previousManifest -RestorePointId $previousPoint
            $previousObjects = New-DccObjectMapForRestorePoint -Manifest $previousManifest -RestorePointId $previousPoint
        }
        $fullBaseline = Get-DccBuilderProperty -Object $previousManifest -Name 'fullBaseline'
        $incrementalChain = @(ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $previousManifest -Name 'incrementalChain'))
        $restorePoints = @(ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $previousManifest -Name 'restorePoints'))
        $objectInventories = @(ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $previousManifest -Name 'objectInventories'))
        $databaseRecords = @(ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $previousManifest -Name 'databaseRecords'))
        $dccEvents = @(ConvertTo-DccBuilderArray -Value (Get-DccBuilderProperty -Object $previousManifest -Name 'dccEvents'))
    }

    $current = New-DccCurrentRecordModels `
        -Snapshot $snapshot `
        -ObjectInventory $objectInventory `
        -RestorePointId $RestorePointId `
        -PreviousRecordMap $previousRecords `
        -PreviousObjectMap $previousObjects `
        -Errors $errors
    $currentEvents = @(New-DccBuilderEvents `
            -CurrentRecordMap $current.RecordMap `
            -CurrentObjectMap $current.ObjectMap `
            -PreviousRecordMap $previousRecords `
            -PreviousObjectMap $previousObjects `
            -RestorePointId $RestorePointId)
    $changeSummary = New-DccBuilderChangeSummary `
        -CurrentRecordMap $current.RecordMap `
        -CurrentObjectMap $current.ObjectMap `
        -PreviousObjectMap $previousObjects `
        -CurrentEvents $currentEvents

    if ($errors.Count -gt 0) {
        $blocked = New-DccBuilderBlockedPayload -BackupId $BackupId -RestorePointId $RestorePointId -Errors $errors -Snapshot $snapshot -ObjectInventory $objectInventory
        Write-DccBuilderJson -Payload $blocked -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $blocked; ExitCode = 2 }
    }

    $segmentChecksum = ConvertTo-DccBuilderSha256 -Value (
        ($BackupId + '|' + $RestorePointId + '|' + (($current.DatabaseRecords | ConvertTo-Json -Depth 20) -join '') + '|' + (($current.InventoryObjects | ConvertTo-Json -Depth 20) -join ''))
    )
    $previousBackupId = ''
    $baselineBackupId = ''
    if ($null -ne $previousManifest) {
        $previousBackupId = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousManifest -Name 'backupId')
        $baselineBackupId = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousManifest -Name 'baselineBackupId')
        if ([string]::IsNullOrWhiteSpace($baselineBackupId)) {
            $baselineBackupId = Get-DccBuilderString (Get-DccBuilderProperty -Object $previousManifest -Name 'backupId')
        }
    }

    if ($null -eq $fullBaseline) {
        $fullBaseline = [pscustomobject]([ordered]@{
            backupId = $BackupId
            restorePointId = $RestorePointId
            checksum = $segmentChecksum
            schemaVersion = Get-DccBuilderString (Get-DccBuilderProperty -Object $snapshot -Name 'schemaVersionTag')
        })
        $baselineBackupId = $BackupId
    } else {
        $incrementalChain += [pscustomobject]([ordered]@{
            from = $previousPoint
            to = $RestorePointId
            backupId = $BackupId
            previousBackupId = $previousBackupId
            checksum = $segmentChecksum
            schemaFrom = Get-DccBuilderString (Get-DccBuilderProperty -Object $fullBaseline -Name 'schemaVersion')
            schemaTo = Get-DccBuilderString (Get-DccBuilderProperty -Object $snapshot -Name 'schemaVersionTag')
        })
    }
    $backupMode = if ([string]::IsNullOrWhiteSpace($previousBackupId)) { 'baseline' } else { 'incremental' }

    $restorePoints += [pscustomobject]([ordered]@{
        id = $RestorePointId
        databaseRestorePointId = $RestorePointId
        objectInventoryRestorePointId = $RestorePointId
    })
    $objectInventories += [pscustomobject]([ordered]@{
        restorePointId = $RestorePointId
        bucket = Get-DccBuilderString (Get-DccBuilderProperty -Object $objectInventory -Name 'bucket')
        objectStoreRoot = Get-DccBuilderString (Get-DccBuilderProperty -Object $objectInventory -Name 'objectStoreRoot')
        objects = @($current.InventoryObjects)
    })
    $databaseRecords += @($current.DatabaseRecords)
    $dccEvents += @($currentEvents)

    $manifest = [pscustomobject]([ordered]@{
        schemaVersion = 'dcc-backup-manifest-v1'
        backupId = $BackupId
        backupMode = $backupMode
        baselineBackupId = $baselineBackupId
        baselineRestorePointId = Get-DccBuilderString (Get-DccBuilderProperty -Object $fullBaseline -Name 'restorePointId')
        previousBackupId = if ([string]::IsNullOrWhiteSpace($previousBackupId)) { $null } else { $previousBackupId }
        previousRestorePointId = if ([string]::IsNullOrWhiteSpace($previousPoint)) { $null } else { $previousPoint }
        chainStatus = 'COMPLETE'
        changeSummary = $changeSummary
        targetEnvironment = $TargetEnvironment
        targetHost = $TargetHost
        status = 'success'
        restoreVerified = $false
        restoreRehearsal = [pscustomobject]@{ status = 'not-run' }
        fullBaseline = $fullBaseline
        incrementalChain = @($incrementalChain)
        restorePoints = @($restorePoints)
        objectInventories = @($objectInventories)
        databaseRecords = @($databaseRecords)
        dccEvents = @($dccEvents)
    })
    Write-DccBuilderJson -Payload $manifest -OutputPath $OutputPath
    return [pscustomobject]@{ Payload = $manifest; ExitCode = 0 }
}

Export-ModuleMember -Function Invoke-DccBackupManifestBuild
