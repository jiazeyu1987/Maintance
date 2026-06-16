Set-StrictMode -Version Latest

$script:RequiredResourceFields = @('storageProfileId', 'bucket', 'objectKey', 'size', 'sha256')

function ConvertTo-ResourceDeltaExecutorArray {
    param([object]$Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Get-ResourceDeltaExecutorProperty {
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

function Read-ResourceDeltaExecutorJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $text = [System.IO.File]::ReadAllText($fullPath, [System.Text.UTF8Encoding]::new($false))
    return $text | ConvertFrom-Json -ErrorAction Stop
}

function Write-ResourceDeltaExecutorJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not [string]::IsNullOrWhiteSpace($directory) -and -not (Test-Path -LiteralPath $directory -PathType Container)) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 80
    [System.IO.File]::WriteAllText($fullPath, $json + [System.Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    return $fullPath
}

function New-ResourceDeltaExecutorDiagnostic {
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

function New-ResourceDeltaExecutorObject {
    param([Parameter(Mandatory = $true)][object]$Item)

    return [ordered]@{
        storageProfileId = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'storageProfileId')
        bucket = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'bucket')
        objectKey = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'objectKey')
        size = Get-ResourceDeltaExecutorProperty -Object $Item -Name 'size'
        sha256 = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'sha256')
    }
}

function Get-ResourceDeltaExecutorSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $hashBytes = $sha.ComputeHash($stream)
        return 'sha256:' + [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
}

function Get-ResourceDeltaExecutorSize {
    param([Parameter(Mandatory = $true)][string]$Path)

    return (Get-Item -LiteralPath $Path).Length
}

function Resolve-ResourceDeltaObjectPath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][object]$Item
    )

    $bucket = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'bucket')
    $objectKey = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'objectKey')
    $relativeObjectKey = $objectKey.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $rootFullPath = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $combined = [System.IO.Path]::Combine($rootFullPath, $bucket, $relativeObjectKey)
    $fullPath = [System.IO.Path]::GetFullPath($combined)
    $rootPrefix = $rootFullPath + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Resolved object path '$fullPath' is outside object root '$rootFullPath'."
    }
    return $fullPath
}

function Find-ResourceDeltaExecutorMissingFieldDiagnostic {
    param(
        [array]$Items = @(),
        [Parameter(Mandatory = $true)][string]$Scope
    )

    for ($index = 0; $index -lt $Items.Count; $index++) {
        $item = $Items[$index]
        $missing = @()
        foreach ($field in $script:RequiredResourceFields) {
            $value = Get-ResourceDeltaExecutorProperty -Object $item -Name $field
            if ($null -eq $value -or ($value -is [string] -and [string]::IsNullOrWhiteSpace($value))) {
                $missing += $field
            }
        }
        if ($missing.Count -gt 0) {
            return New-ResourceDeltaExecutorDiagnostic `
                -Code 'RESOURCE_DELTA_OBJECT_FIELD_MISSING' `
                -Message "$Scope[$index] is missing required field(s): $($missing -join ', ')." `
                -Impact 'The local executor cannot resolve or verify object identity and integrity.' `
                -NextStep 'Regenerate the resource delta plan with storageProfileId, bucket, objectKey, size, and sha256 for every object.'
        }
    }
    return $null
}

function New-ResourceDeltaExecutorProof {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Mode,
        [array]$CopiedObjects = @(),
        [array]$VerifiedObjects = @(),
        [array]$TombstoneObjects = @(),
        [array]$Errors = @()
    )

    return [ordered]@{
        schemaVersion = '1.0'
        status = $Status
        mode = $Mode
        completedAt = [DateTime]::UtcNow.ToString('o')
        summary = [ordered]@{
            copyObjects = @($CopiedObjects).Count
            verifyOnlyObjects = @($VerifiedObjects).Count
            conflictObjects = 0
            tombstoneObjects = @($TombstoneObjects).Count
        }
        copiedObjects = @($CopiedObjects)
        verifiedObjects = @($VerifiedObjects)
        tombstoneObjects = @($TombstoneObjects)
        errors = @($Errors)
    }
}

function Test-ResourceDeltaFileMatches {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Item
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }
    $expectedSize = [int64](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'size')
    $expectedSha256 = [string](Get-ResourceDeltaExecutorProperty -Object $Item -Name 'sha256')
    $actualSize = Get-ResourceDeltaExecutorSize -Path $Path
    if ($actualSize -ne $expectedSize) {
        return $false
    }
    $actualSha256 = Get-ResourceDeltaExecutorSha256 -Path $Path
    return $actualSha256 -eq $expectedSha256
}

function Complete-ResourceDeltaExecutorFailure {
    param(
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)]$ErrorObject
    )

    $proof = New-ResourceDeltaExecutorProof -Status 'failed' -Mode $Mode -Errors @($ErrorObject)
    Write-ResourceDeltaExecutorJson -Path $OutputPath -Value $proof | Out-Null
    return [pscustomobject]@{ ExitCode = 2; Proof = $proof }
}

function Invoke-ResourceDeltaLocalExecutor {
    param(
        [Parameter(Mandatory = $true)][string]$ResourceDeltaPlanPath,
        [Parameter(Mandatory = $true)][string]$SourceObjectRoot,
        [Parameter(Mandatory = $true)][string]$TargetObjectRoot,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [ValidateSet('local-execute')][string]$Mode = 'local-execute'
    )

    $plan = Read-ResourceDeltaExecutorJson -Path $ResourceDeltaPlanPath
    $planStatus = [string](Get-ResourceDeltaExecutorProperty -Object $plan -Name 'status')
    $planErrors = @(ConvertTo-ResourceDeltaExecutorArray -Value (Get-ResourceDeltaExecutorProperty -Object $plan -Name 'errors'))
    $planConflicts = @(ConvertTo-ResourceDeltaExecutorArray -Value (Get-ResourceDeltaExecutorProperty -Object $plan -Name 'conflictObjects'))
    if ($planStatus -ne 'passed' -or $planErrors.Count -gt 0 -or $planConflicts.Count -gt 0) {
        return Complete-ResourceDeltaExecutorFailure `
            -OutputPath $OutputPath `
            -Mode $Mode `
            -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                -Code 'RESOURCE_DELTA_PLAN_NOT_EXECUTABLE' `
                -Message "Resource delta plan status '$planStatus' is not executable or contains conflicts/errors." `
                -Impact 'The local executor cannot produce completed_verified proof from an unsafe plan.' `
                -NextStep 'Resolve plan errors and regenerate a passed plan before executing.')
    }

    $copyObjects = @(ConvertTo-ResourceDeltaExecutorArray -Value (Get-ResourceDeltaExecutorProperty -Object $plan -Name 'copyObjects'))
    $verifyOnlyObjects = @(ConvertTo-ResourceDeltaExecutorArray -Value (Get-ResourceDeltaExecutorProperty -Object $plan -Name 'verifyOnlyObjects'))
    $tombstoneObjects = @(ConvertTo-ResourceDeltaExecutorArray -Value (Get-ResourceDeltaExecutorProperty -Object $plan -Name 'tombstoneObjects'))

    foreach ($group in @(
        @{ Scope = 'copyObjects'; Items = $copyObjects },
        @{ Scope = 'verifyOnlyObjects'; Items = $verifyOnlyObjects },
        @{ Scope = 'tombstoneObjects'; Items = $tombstoneObjects }
    )) {
        $missingDiagnostic = Find-ResourceDeltaExecutorMissingFieldDiagnostic -Items @($group.Items) -Scope $group.Scope
        if ($null -ne $missingDiagnostic) {
            return Complete-ResourceDeltaExecutorFailure -OutputPath $OutputPath -Mode $Mode -ErrorObject $missingDiagnostic
        }
    }

    foreach ($copyObject in $copyObjects) {
        $sourcePath = Resolve-ResourceDeltaObjectPath -Root $SourceObjectRoot -Item $copyObject
        $targetPath = Resolve-ResourceDeltaObjectPath -Root $TargetObjectRoot -Item $copyObject
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            return Complete-ResourceDeltaExecutorFailure `
                -OutputPath $OutputPath `
                -Mode $Mode `
                -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                    -Code 'RESOURCE_DELTA_SOURCE_MISSING' `
                    -Message "Source object '$sourcePath' was not found for copy object '$([string](Get-ResourceDeltaExecutorProperty -Object $copyObject -Name 'objectKey'))'." `
                    -Impact 'The local executor cannot copy an object that is absent from source storage.' `
                    -NextStep 'Restore the source object or regenerate the resource delta plan.')
        }
        if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
            return Complete-ResourceDeltaExecutorFailure `
                -OutputPath $OutputPath `
                -Mode $Mode `
                -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                    -Code 'RESOURCE_DELTA_TARGET_ALREADY_EXISTS' `
                    -Message "Target object '$targetPath' already exists for copy object '$([string](Get-ResourceDeltaExecutorProperty -Object $copyObject -Name 'objectKey'))'." `
                    -Impact 'The local executor refuses to overwrite target objects.' `
                    -NextStep 'Regenerate the delta plan from the current target index before executing.')
        }
        if (-not (Test-ResourceDeltaFileMatches -Path $sourcePath -Item $copyObject)) {
            return Complete-ResourceDeltaExecutorFailure `
                -OutputPath $OutputPath `
                -Mode $Mode `
                -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                    -Code 'RESOURCE_DELTA_SOURCE_READBACK_MISMATCH' `
                    -Message "Source object '$sourcePath' does not match planned size or sha256." `
                    -Impact 'The local executor cannot prove copied content would match the plan.' `
                    -NextStep 'Regenerate resource hashes from source storage and rerun planning.')
        }
    }

    foreach ($verifyObject in $verifyOnlyObjects) {
        $targetPath = Resolve-ResourceDeltaObjectPath -Root $TargetObjectRoot -Item $verifyObject
        if (-not (Test-ResourceDeltaFileMatches -Path $targetPath -Item $verifyObject)) {
            return Complete-ResourceDeltaExecutorFailure `
                -OutputPath $OutputPath `
                -Mode $Mode `
                -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                    -Code 'RESOURCE_DELTA_READBACK_MISMATCH' `
                    -Message "Target verify-only object '$targetPath' does not match planned size or sha256." `
                    -Impact 'The completed proof cannot verify target resource integrity.' `
                    -NextStep 'Repair the target object or regenerate a new delta plan from the current target index.')
        }
    }

    $copiedObjects = New-Object System.Collections.ArrayList
    foreach ($copyObject in $copyObjects) {
        $sourcePath = Resolve-ResourceDeltaObjectPath -Root $SourceObjectRoot -Item $copyObject
        $targetPath = Resolve-ResourceDeltaObjectPath -Root $TargetObjectRoot -Item $copyObject
        $targetDirectory = [System.IO.Path]::GetDirectoryName($targetPath)
        if (-not (Test-Path -LiteralPath $targetDirectory -PathType Container)) {
            [System.IO.Directory]::CreateDirectory($targetDirectory) | Out-Null
        }
        [System.IO.File]::Copy($sourcePath, $targetPath, $false)
        if (-not (Test-ResourceDeltaFileMatches -Path $targetPath -Item $copyObject)) {
            return Complete-ResourceDeltaExecutorFailure `
                -OutputPath $OutputPath `
                -Mode $Mode `
                -ErrorObject (New-ResourceDeltaExecutorDiagnostic `
                    -Code 'RESOURCE_DELTA_COPY_READBACK_MISMATCH' `
                    -Message "Copied target object '$targetPath' does not match planned size or sha256 after copy." `
                    -Impact 'The completed proof cannot verify copied resource integrity.' `
                    -NextStep 'Inspect local storage and rerun the delta execution after resolving I/O issues.')
        }
        [void]$copiedObjects.Add((New-ResourceDeltaExecutorObject -Item $copyObject))
    }

    $verifiedObjects = New-Object System.Collections.ArrayList
    foreach ($verifyObject in $verifyOnlyObjects) {
        [void]$verifiedObjects.Add((New-ResourceDeltaExecutorObject -Item $verifyObject))
    }

    $tombstones = New-Object System.Collections.ArrayList
    foreach ($tombstoneObject in $tombstoneObjects) {
        [void]$tombstones.Add((New-ResourceDeltaExecutorObject -Item $tombstoneObject))
    }

    $proof = New-ResourceDeltaExecutorProof `
        -Status 'completed_verified' `
        -Mode $Mode `
        -CopiedObjects @($copiedObjects.ToArray()) `
        -VerifiedObjects @($verifiedObjects.ToArray()) `
        -TombstoneObjects @($tombstones.ToArray()) `
        -Errors @()
    Write-ResourceDeltaExecutorJson -Path $OutputPath -Value $proof | Out-Null
    return [pscustomobject]@{ ExitCode = 0; Proof = $proof }
}

Export-ModuleMember -Function Invoke-ResourceDeltaLocalExecutor
