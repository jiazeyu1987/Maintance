Set-StrictMode -Version Latest

$script:ResourceDeltaRequiredFields = @('storageProfileId', 'bucket', 'objectKey', 'size', 'sha256')

function ConvertTo-ResourceDeltaArray {
    param([object]$Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Get-ResourceDeltaProperty {
    param(
        [object]$Object,
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

function Test-ResourceDeltaRequiredValuePresent {
    param(
        [object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $value = Get-ResourceDeltaProperty -Object $Object -Name $Name
    if ($null -eq $value) {
        return $false
    }
    if ($value -is [string] -and [string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    return $true
}

function Read-ResourceDeltaJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $text = [System.IO.File]::ReadAllText($fullPath, [System.Text.UTF8Encoding]::new($false))
    return $text | ConvertFrom-Json -ErrorAction Stop
}

function Write-ResourceDeltaJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not [string]::IsNullOrWhiteSpace($directory) -and -not (Test-Path -LiteralPath $directory -PathType Container)) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 60
    [System.IO.File]::WriteAllText($fullPath, $json + [System.Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    return $fullPath
}

function New-ResourceDeltaKey {
    param([Parameter(Mandatory = $true)][object]$Item)

    $separator = [string][char]31
    return ([string](Get-ResourceDeltaProperty -Object $Item -Name 'storageProfileId')) +
        $separator +
        ([string](Get-ResourceDeltaProperty -Object $Item -Name 'bucket')) +
        $separator +
        ([string](Get-ResourceDeltaProperty -Object $Item -Name 'objectKey'))
}

function New-ResourceDeltaObjectProof {
    param([Parameter(Mandatory = $true)][object]$Item)

    return [ordered]@{
        storageProfileId = [string](Get-ResourceDeltaProperty -Object $Item -Name 'storageProfileId')
        bucket = [string](Get-ResourceDeltaProperty -Object $Item -Name 'bucket')
        objectKey = [string](Get-ResourceDeltaProperty -Object $Item -Name 'objectKey')
        size = Get-ResourceDeltaProperty -Object $Item -Name 'size'
        sha256 = [string](Get-ResourceDeltaProperty -Object $Item -Name 'sha256')
    }
}

function New-ResourceDeltaDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    return [ordered]@{
        code = $Code
        message = $Message
        impact = $Impact
        nextStep = $NextStep
    }
}

function New-ResourceDeltaProof {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)][int]$SourceReferenceCount,
        [Parameter(Mandatory = $true)][int]$TargetObjectCount,
        [array]$CopyObjects = @(),
        [array]$VerifyOnlyObjects = @(),
        [array]$ConflictObjects = @(),
        [array]$TombstoneObjects = @(),
        [array]$Errors = @()
    )

    return [ordered]@{
        schemaVersion = '1.0'
        status = $Status
        mode = $Mode
        plannedAt = [DateTime]::UtcNow.ToString('o')
        summary = [ordered]@{
            sourceReferenceCount = $SourceReferenceCount
            targetObjectCount = $TargetObjectCount
            copyObjects = @($CopyObjects).Count
            verifyOnlyObjects = @($VerifyOnlyObjects).Count
            conflictObjects = @($ConflictObjects).Count
            tombstoneObjects = @($TombstoneObjects).Count
        }
        copyObjects = @($CopyObjects)
        verifyOnlyObjects = @($VerifyOnlyObjects)
        conflictObjects = @($ConflictObjects)
        tombstoneObjects = @($TombstoneObjects)
        errors = @($Errors)
    }
}

function Find-ResourceDeltaMissingFieldDiagnostic {
    param(
        [Parameter(Mandatory = $true)][array]$Items,
        [Parameter(Mandatory = $true)][string]$ItemName,
        [Parameter(Mandatory = $true)][string]$Code
    )

    for ($index = 0; $index -lt $Items.Count; $index++) {
        $item = $Items[$index]
        $missingFields = @()
        foreach ($field in $script:ResourceDeltaRequiredFields) {
            if (-not (Test-ResourceDeltaRequiredValuePresent -Object $item -Name $field)) {
                $missingFields += $field
            }
        }
        if ($missingFields.Count -gt 0) {
            return New-ResourceDeltaDiagnostic `
                -Code $Code `
                -Message "$ItemName[$index] is missing required field(s): $($missingFields -join ', ')." `
                -Impact 'Resource delta planning cannot build a reliable storage object identity or integrity comparison.' `
                -NextStep 'Regenerate the input JSON with storageProfileId, bucket, objectKey, size, and sha256 for every resource object.'
        }
    }

    return $null
}

function Invoke-ResourceDeltaPlanner {
    param(
        [Parameter(Mandatory = $true)][string]$SourceResourceReferenceManifestPath,
        [Parameter(Mandatory = $true)][string]$TargetResourceIndexPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [ValidateSet('plan-only')][string]$Mode = 'plan-only'
    )

    $sourceManifest = Read-ResourceDeltaJson -Path $SourceResourceReferenceManifestPath
    $targetIndex = Read-ResourceDeltaJson -Path $TargetResourceIndexPath
    $sourceReferences = @(ConvertTo-ResourceDeltaArray -Value (Get-ResourceDeltaProperty -Object $sourceManifest -Name 'references'))
    $targetObjects = @(ConvertTo-ResourceDeltaArray -Value (Get-ResourceDeltaProperty -Object $targetIndex -Name 'objects'))

    $sourceMissingDiagnostic = Find-ResourceDeltaMissingFieldDiagnostic `
        -Items $sourceReferences `
        -ItemName 'references' `
        -Code 'RESOURCE_REFERENCE_FIELD_MISSING'
    if ($null -ne $sourceMissingDiagnostic) {
        $proof = New-ResourceDeltaProof `
            -Status 'failed' `
            -Mode $Mode `
            -SourceReferenceCount $sourceReferences.Count `
            -TargetObjectCount $targetObjects.Count `
            -Errors @($sourceMissingDiagnostic)
        Write-ResourceDeltaJson -Path $OutputPath -Value $proof | Out-Null
        return [pscustomobject]@{ ExitCode = 2; Proof = $proof }
    }

    $targetMissingDiagnostic = Find-ResourceDeltaMissingFieldDiagnostic `
        -Items $targetObjects `
        -ItemName 'objects' `
        -Code 'RESOURCE_INDEX_FIELD_MISSING'
    if ($null -ne $targetMissingDiagnostic) {
        $proof = New-ResourceDeltaProof `
            -Status 'failed' `
            -Mode $Mode `
            -SourceReferenceCount $sourceReferences.Count `
            -TargetObjectCount $targetObjects.Count `
            -Errors @($targetMissingDiagnostic)
        Write-ResourceDeltaJson -Path $OutputPath -Value $proof | Out-Null
        return [pscustomobject]@{ ExitCode = 2; Proof = $proof }
    }

    $targetByKey = @{}
    foreach ($targetObject in $targetObjects) {
        $targetByKey[(New-ResourceDeltaKey -Item $targetObject)] = $targetObject
    }

    $sourceKeys = @{}
    $copyObjects = New-Object System.Collections.ArrayList
    $verifyOnlyObjects = New-Object System.Collections.ArrayList
    $conflictObjects = New-Object System.Collections.ArrayList

    foreach ($sourceReference in $sourceReferences) {
        $key = New-ResourceDeltaKey -Item $sourceReference
        $sourceKeys[$key] = $true
        if (-not $targetByKey.ContainsKey($key)) {
            [void]$copyObjects.Add((New-ResourceDeltaObjectProof -Item $sourceReference))
            continue
        }

        $targetObject = $targetByKey[$key]
        $sourceSha256 = [string](Get-ResourceDeltaProperty -Object $sourceReference -Name 'sha256')
        $targetSha256 = [string](Get-ResourceDeltaProperty -Object $targetObject -Name 'sha256')
        $sourceSize = Get-ResourceDeltaProperty -Object $sourceReference -Name 'size'
        $targetSize = Get-ResourceDeltaProperty -Object $targetObject -Name 'size'
        if ($sourceSha256 -eq $targetSha256 -and [string]$sourceSize -eq [string]$targetSize) {
            [void]$verifyOnlyObjects.Add((New-ResourceDeltaObjectProof -Item $sourceReference))
        } else {
            $conflict = New-ResourceDeltaObjectProof -Item $sourceReference
            $conflict.sourceSize = $sourceSize
            $conflict.sourceSha256 = $sourceSha256
            $conflict.targetSize = $targetSize
            $conflict.targetSha256 = $targetSha256
            [void]$conflictObjects.Add($conflict)
        }
    }

    $tombstoneObjects = New-Object System.Collections.ArrayList
    foreach ($targetObject in $targetObjects) {
        $key = New-ResourceDeltaKey -Item $targetObject
        if (-not $sourceKeys.ContainsKey($key)) {
            [void]$tombstoneObjects.Add((New-ResourceDeltaObjectProof -Item $targetObject))
        }
    }

    $errors = @()
    $status = 'passed'
    if ($conflictObjects.Count -gt 0) {
        $status = 'failed'
        $errors += New-ResourceDeltaDiagnostic `
            -Code 'RESOURCE_DELTA_CONFLICT' `
            -Message "Resource delta planner found $($conflictObjects.Count) object(s) with the same storage key but different size or sha256." `
            -Impact 'The planner cannot prove whether copying would overwrite a different target object.' `
            -NextStep 'Review conflictObjects, reconcile the source reference or target index, then rerun plan-only.'
    }

    $proof = New-ResourceDeltaProof `
        -Status $status `
        -Mode $Mode `
        -SourceReferenceCount $sourceReferences.Count `
        -TargetObjectCount $targetObjects.Count `
        -CopyObjects @($copyObjects.ToArray()) `
        -VerifyOnlyObjects @($verifyOnlyObjects.ToArray()) `
        -ConflictObjects @($conflictObjects.ToArray()) `
        -TombstoneObjects @($tombstoneObjects.ToArray()) `
        -Errors @($errors)
    Write-ResourceDeltaJson -Path $OutputPath -Value $proof | Out-Null

    if ($status -eq 'failed') {
        return [pscustomobject]@{ ExitCode = 2; Proof = $proof }
    }
    return [pscustomobject]@{ ExitCode = 0; Proof = $proof }
}

Export-ModuleMember -Function Invoke-ResourceDeltaPlanner
