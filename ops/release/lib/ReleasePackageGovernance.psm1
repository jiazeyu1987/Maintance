Set-StrictMode -Version Latest

function Get-ReleaseSha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            return ([System.BitConverter]::ToString($sha256.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
        } finally {
            $sha256.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Get-ReleaseStringSha256Hex {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Value)
        return ([System.BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function ConvertTo-NormalizedReleaseArtifactPath {
    param(
        [AllowNull()]
        [string]$Path
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -cne $Path.Trim()) {
        throw "${Path}: invalid artifact path"
    }
    if ($Path.Contains('\') -or $Path -match '^[A-Za-z]:' -or [System.IO.Path]::IsPathRooted($Path)) {
        throw "${Path}: invalid artifact path"
    }
    if ($Path -match '[\x00-\x1f]' -or $Path.Contains('|')) {
        throw "${Path}: invalid artifact path"
    }

    $segments = @($Path.Split('/'))
    if ($segments.Count -eq 0 -or @($segments | Where-Object { $_ -in @('', '.', '..') }).Count -gt 0) {
        throw "${Path}: invalid artifact path"
    }
    return ($segments -join '/')
}

function Test-IsReleasePackageMutableMetadataPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    if ($RelativePath -cin @(
        'tested.json',
        'rollback-compatibility.json',
        'prod-latest.json',
        'backup-latest.json'
    )) {
        return $true
    }
    return $RelativePath.StartsWith('prod-deployments/', [System.StringComparison]::Ordinal) -or
        $RelativePath.StartsWith('backup-deployments/', [System.StringComparison]::Ordinal)
}

function Get-ReleasePackageImmutableArtifactFileFacts {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [switch]$ExcludeManifestJson
    )

    if (-not (Test-Path -LiteralPath $PackagePath -PathType Container)) {
        throw "Release package directory missing: $PackagePath"
    }
    $root = [System.IO.Path]::GetFullPath($PackagePath)
    $trimChars = [char[]]@([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $rootPrefix = $root.TrimEnd($trimChars) + [System.IO.Path]::DirectorySeparatorChar
    $entriesByPath = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
    foreach ($file in Get-ChildItem -LiteralPath $root -File -Recurse) {
        $relativePath = $file.FullName.Substring($rootPrefix.Length).Replace('\', '/')
        if ($relativePath -ceq 'release-manifest.json' -or (Test-IsReleasePackageMutableMetadataPath -RelativePath $relativePath)) {
            continue
        }
        if ($ExcludeManifestJson -and $relativePath -ceq 'manifest.json') {
            continue
        }
        $entriesByPath.Add($relativePath, [pscustomobject][ordered]@{
            path = $relativePath
            bytes = [int64]$file.Length
            fullName = $file.FullName
        })
    }
    $sortedPaths = [string[]]@($entriesByPath.Keys)
    [System.Array]::Sort($sortedPaths, [System.StringComparer]::Ordinal)
    return @($sortedPaths | ForEach-Object { $entriesByPath[$_] })
}

function Get-ReleasePackageImmutableArtifactEntries {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [switch]$ExcludeManifestJson
    )

    return @(Get-ReleasePackageImmutableArtifactFileFacts -PackagePath $PackagePath -ExcludeManifestJson:$ExcludeManifestJson | ForEach-Object {
        [pscustomobject][ordered]@{
            path = $_.path
            sha256 = Get-ReleaseSha256Hex -Path $_.fullName
            bytes = [int64]$_.bytes
        }
    })
}

function Test-ReleasePackageIntegrity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [string]$ExpectedReleaseTag = '',
        [array]$PreverifiedArtifacts = @()
    )

    if (-not (Test-Path -LiteralPath $PackagePath -PathType Container)) {
        throw "Release package directory missing: $PackagePath"
    }
    $root = [System.IO.Path]::GetFullPath($PackagePath)
    $manifestPath = Join-Path $root 'release-manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'release-manifest.json: missing manifest'
    }

    $manifestBytes = [System.IO.File]::ReadAllBytes($manifestPath)
    try {
        $manifestText = [System.Text.UTF8Encoding]::new($false, $true).GetString($manifestBytes)
        $manifest = $manifestText | ConvertFrom-Json
    } catch {
        throw "release-manifest.json: invalid JSON: $($_.Exception.Message)"
    }

    foreach ($propertyName in @('releaseTag', 'packageDirectoryName', 'publishScope', 'artifacts')) {
        if ($manifest.PSObject.Properties.Name -cnotcontains $propertyName) {
            throw "release-manifest.json: missing $propertyName"
        }
    }
    $releaseTag = [string]$manifest.releaseTag
    $packageDirectoryName = [string]$manifest.packageDirectoryName
    $publishScope = [string]$manifest.publishScope
    if ([string]::IsNullOrWhiteSpace($releaseTag)) {
        throw 'release-manifest.json: invalid releaseTag'
    }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedReleaseTag) -and $releaseTag -cne $ExpectedReleaseTag) {
        throw "release-manifest.json: releaseTag mismatch: $releaseTag != $ExpectedReleaseTag"
    }
    if ($packageDirectoryName -cne (Split-Path -Leaf $root)) {
        throw "release-manifest.json: packageDirectoryName mismatch: $packageDirectoryName != $(Split-Path -Leaf $root)"
    }
    if ($publishScope -cnotin @('code-only', 'with-data')) {
        throw "release-manifest.json: invalid publishScope: $publishScope"
    }

    $preverifiedByPath = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($artifact in @($PreverifiedArtifacts)) {
        if ($null -eq $artifact) {
            continue
        }
        $preverifiedPath = ConvertTo-NormalizedReleaseArtifactPath -Path ([string]$artifact.path)
        if ($preverifiedByPath.ContainsKey($preverifiedPath)) {
            throw "${preverifiedPath}: duplicate preverified artifact path"
        }
        $preverifiedByPath.Add($preverifiedPath, $artifact)
    }

    $declaredPaths = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $verifiedEntries = @()
    foreach ($artifact in @($manifest.artifacts)) {
        if ($null -eq $artifact) {
            throw 'release-manifest.json: invalid artifact entry'
        }
        foreach ($propertyName in @('path', 'sha256', 'bytes')) {
            if ($artifact.PSObject.Properties.Name -cnotcontains $propertyName) {
                throw "release-manifest.json: artifact missing $propertyName"
            }
        }
        $declaredPath = [string]$artifact.path
        $relativePath = ConvertTo-NormalizedReleaseArtifactPath -Path $declaredPath
        if ($relativePath -ceq 'release-manifest.json' -or (Test-IsReleasePackageMutableMetadataPath -RelativePath $relativePath)) {
            throw "${relativePath}: invalid artifact path"
        }
        if ($declaredPaths.ContainsKey($relativePath)) {
            throw "${relativePath}: duplicate artifact path"
        }
        $declaredPaths.Add($relativePath, $artifact)

        $declaredHash = [string]$artifact.sha256
        if ($declaredHash -cnotmatch '^[0-9a-f]{64}$') {
            throw "${relativePath}: invalid sha256"
        }
        $validIntegerTypes = @(
            [byte], [sbyte], [int16], [uint16], [int32], [uint32], [int64], [uint64]
        )
        if ($null -eq $artifact.bytes -or
            $validIntegerTypes -cnotcontains $artifact.bytes.GetType() -or
            [decimal]$artifact.bytes -lt 0) {
            throw "${relativePath}: invalid bytes"
        }

        $artifactPath = Join-Path $root ($relativePath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
        if (-not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
            throw "${relativePath}: missing artifact"
        }
        $actualFile = Get-Item -LiteralPath $artifactPath
        if ([int64]$actualFile.Length -ne [int64]$artifact.bytes) {
            throw "${relativePath}: bytes mismatch; declared=$($artifact.bytes) actual=$($actualFile.Length)"
        }
        $actualHash = ''
        if ($preverifiedByPath.ContainsKey($relativePath)) {
            $preverified = $preverifiedByPath[$relativePath]
            $preverifiedHash = [string]$preverified.sha256
            $preverifiedBytes = [int64]$preverified.bytes
            if ($preverifiedHash -cne $declaredHash -or $preverifiedBytes -ne [int64]$actualFile.Length) {
                throw "${relativePath}: preverified artifact mismatch"
            }
            $actualHash = $preverifiedHash
        } else {
            $actualHash = Get-ReleaseSha256Hex -Path $actualFile.FullName
        }
        if ($actualHash -cne $declaredHash) {
            throw "${relativePath}: hash mismatch; declared=$declaredHash actual=$actualHash"
        }
        $verifiedEntries += [pscustomobject][ordered]@{
            path = $relativePath
            sha256 = $actualHash
            bytes = [int64]$actualFile.Length
        }
    }

    if (-not $declaredPaths.ContainsKey('manifest.json')) {
        throw 'manifest.json: missing artifact declaration'
    }
    if ($preverifiedByPath.Count -gt 0) {
        foreach ($actual in @(Get-ReleasePackageImmutableArtifactFileFacts -PackagePath $root)) {
            if (-not $declaredPaths.ContainsKey([string]$actual.path)) {
                throw "$($actual.path): undeclared file"
            }
        }
    } else {
        foreach ($actual in @(Get-ReleasePackageImmutableArtifactEntries -PackagePath $root)) {
            if (-not $declaredPaths.ContainsKey([string]$actual.path)) {
                throw "$($actual.path): undeclared file"
            }
        }
    }
    if ($verifiedEntries.Count -ne $declaredPaths.Count) {
        throw 'release-manifest.json: artifact set mismatch'
    }

    $verifiedByPath = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
    foreach ($entry in $verifiedEntries) {
        $verifiedByPath.Add([string]$entry.path, $entry)
    }
    $sortedVerifiedPaths = [string[]]@($verifiedByPath.Keys)
    [System.Array]::Sort($sortedVerifiedPaths, [System.StringComparer]::Ordinal)
    $verifiedEntries = @($sortedVerifiedPaths | ForEach-Object { $verifiedByPath[$_] })
    $manifestDigest = 'sha256:' + (Get-ReleaseSha256Hex -Path $manifestPath)
    $canonicalRecords = "manifestDigest=$manifestDigest`n"
    foreach ($artifact in $verifiedEntries) {
        $canonicalRecords += "artifact=$($artifact.path)`tsha256:$($artifact.sha256)`t$($artifact.bytes)`n"
    }
    $packageDigest = 'sha256:' + (Get-ReleaseStringSha256Hex -Value $canonicalRecords)

    return [pscustomobject][ordered]@{
        releaseTag = $releaseTag
        packageDirectoryName = $packageDirectoryName
        publishScope = $publishScope
        manifestDigest = $manifestDigest
        packageDigest = $packageDigest
        artifacts = @($verifiedEntries)
    }
}

function Assert-ReleasePackageDeploymentScope {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('test', 'prod', 'backup')]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [ValidateSet('code-only', 'with-data')]
        [string]$PublishScope
    )

    if ($TargetEnvironment -in @('prod', 'backup') -and $PublishScope -ne 'code-only') {
        throw "Production-grade environment '$TargetEnvironment' requires a code-only release package; publishScope=$PublishScope"
    }
}

function Test-IsReleaseUtcInstant {
    param(
        [AllowNull()]
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value) -or
        $Value -notmatch '^(?<date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?<fraction>\.\d{1,9})?Z$') {
        return $false
    }
    $fraction = [string]$Matches['fraction']
    if ($fraction.Length -gt 8) {
        $fraction = $fraction.Substring(0, 8)
    }
    $parseValue = [string]$Matches['date'] + $fraction + 'Z'
    $parsed = [DateTimeOffset]::MinValue
    return [DateTimeOffset]::TryParse(
        $parseValue,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal,
        [ref]$parsed
    )
}

function Assert-PublishTestOperationEvidence {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$EvidencePath,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedOperationId,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedReleaseTag
    )

    if (-not (Test-Path -LiteralPath $EvidencePath -PathType Leaf)) {
        throw "operation evidence missing: $EvidencePath"
    }
    try {
        $bytes = [System.IO.File]::ReadAllBytes($EvidencePath)
        $text = [System.Text.UTF8Encoding]::new($false, $true).GetString($bytes)
        $operation = $text | ConvertFrom-Json
    } catch {
        throw "operation evidence invalid JSON: $EvidencePath`: $($_.Exception.Message)"
    }
    foreach ($propertyName in @('operationId', 'requestedAt', 'environment', 'action', 'status', 'parameters')) {
        if ($operation.PSObject.Properties.Name -cnotcontains $propertyName) {
            throw "operation evidence missing $propertyName"
        }
    }
    if ([string]$operation.operationId -cne $ExpectedOperationId) {
        throw "operationId mismatch: $($operation.operationId) != $ExpectedOperationId"
    }
    if ([string]$operation.environment -cne 'test') {
        throw "environment mismatch: $($operation.environment) != test"
    }
    if ([string]$operation.action -cne 'publish-test') {
        throw "action mismatch: $($operation.action) != publish-test"
    }
    if ([string]$operation.status -cne 'SUCCESS') {
        throw "status mismatch: $($operation.status) != SUCCESS"
    }
    if ($null -eq $operation.parameters -or
        $operation.parameters.PSObject.Properties.Name -cnotcontains 'releaseTag' -or
        [string]$operation.parameters.releaseTag -cne $ExpectedReleaseTag) {
        throw "releaseTag mismatch: $($operation.parameters.releaseTag) != $ExpectedReleaseTag"
    }
    if (-not (Test-IsReleaseUtcInstant -Value ([string]$operation.requestedAt))) {
        throw "requestedAt invalid: $($operation.requestedAt)"
    }
    return $operation
}

function Assert-ReleaseRollbackCompatibility {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Compatibility
    )

    if ($Compatibility.PSObject.Properties.Name -cnotcontains 'status' -or
        [string]$Compatibility.status -cne 'COMPATIBLE') {
        $summary = if ($Compatibility.PSObject.Properties.Name -ccontains 'summary') {
            [string]$Compatibility.summary
        } else {
            ''
        }
        throw "rollback compatibility BLOCKED: $summary"
    }
}

function Write-ReleaseTestedAttestation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedReleaseTag,
        [Parameter(Mandatory = $true)]
        [string]$TestOperationId,
        [Parameter(Mandatory = $true)]
        [string]$TestOperationEvidencePath,
        [Parameter(Mandatory = $true)]
        [string]$TestedBy,
        [Parameter(Mandatory = $true)]
        [string]$TestConclusion,
        [hashtable]$RecoverySet
    )

    if ([string]::IsNullOrWhiteSpace($TestedBy)) {
        throw 'testedBy invalid: value is required'
    }
    if ([string]::IsNullOrWhiteSpace($TestConclusion)) {
        throw 'testConclusion invalid: value is required'
    }
    $integrity = Test-ReleasePackageIntegrity -PackagePath $PackagePath -ExpectedReleaseTag $ExpectedReleaseTag
    $operation = Assert-PublishTestOperationEvidence `
        -EvidencePath $TestOperationEvidencePath `
        -ExpectedOperationId $TestOperationId `
        -ExpectedReleaseTag $integrity.releaseTag
    $attestation = [ordered]@{
        schemaVersion = 'v2'
        releaseTag = $integrity.releaseTag
        packageDirectoryName = $integrity.packageDirectoryName
        packageDigest = $integrity.packageDigest
        manifestDigest = $integrity.manifestDigest
        testEnvironment = 'test'
        publishTestOperationId = [string]$operation.operationId
        publishTestOperationStatus = [string]$operation.status
        publishTestRequestedAt = [string]$operation.requestedAt
        testedAt = (Get-Date).ToUniversalTime().ToString('o')
        testedBy = $TestedBy.Trim()
        testConclusion = $TestConclusion.Trim()
    }
    if ($null -ne $RecoverySet) {
        $attestation.recoverySet = $RecoverySet
    }

    $testedPath = Join-Path ([System.IO.Path]::GetFullPath($PackagePath)) 'tested.json'
    $temporaryPath = "$testedPath.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        $json = $attestation | ConvertTo-Json -Depth 8
        [System.IO.File]::WriteAllText($temporaryPath, $json, [System.Text.UTF8Encoding]::new($false))
        if (Test-Path -LiteralPath $testedPath -PathType Leaf) {
            [System.IO.File]::Replace($temporaryPath, $testedPath, $null)
        } else {
            [System.IO.File]::Move($temporaryPath, $testedPath)
        }
    } finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
    }
    return [pscustomobject]$attestation
}

function Test-ReleasePromotionAttestation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedReleaseTag,
        [Parameter(Mandatory = $true)]
        [ValidateSet('prod', 'backup')]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [string]$TestOperationId,
        [Parameter(Mandatory = $true)]
        [string]$TestOperationEvidencePath
    )

    $integrity = Test-ReleasePackageIntegrity -PackagePath $PackagePath -ExpectedReleaseTag $ExpectedReleaseTag
    if ($integrity.publishScope -cne 'code-only') {
        throw "publishScope mismatch: $($integrity.publishScope) != code-only"
    }
    $operation = Assert-PublishTestOperationEvidence `
        -EvidencePath $TestOperationEvidencePath `
        -ExpectedOperationId $TestOperationId `
        -ExpectedReleaseTag $integrity.releaseTag
    $testedPath = Join-Path ([System.IO.Path]::GetFullPath($PackagePath)) 'tested.json'
    if (-not (Test-Path -LiteralPath $testedPath -PathType Leaf)) {
        throw "tested.json missing for $TargetEnvironment promotion"
    }
    try {
        $testedBytes = [System.IO.File]::ReadAllBytes($testedPath)
        $testedText = [System.Text.UTF8Encoding]::new($false, $true).GetString($testedBytes)
        $tested = $testedText | ConvertFrom-Json
    } catch {
        throw "tested.json invalid JSON: $($_.Exception.Message)"
    }
    foreach ($propertyName in @(
        'schemaVersion', 'releaseTag', 'packageDirectoryName', 'packageDigest', 'manifestDigest',
        'testEnvironment', 'publishTestOperationId', 'publishTestOperationStatus',
        'publishTestRequestedAt', 'testedAt', 'testedBy', 'testConclusion'
    )) {
        if ($tested.PSObject.Properties.Name -cnotcontains $propertyName) {
            throw "tested.json missing $propertyName"
        }
    }
    $expectedValues = [ordered]@{
        schemaVersion = 'v2'
        releaseTag = $integrity.releaseTag
        packageDirectoryName = $integrity.packageDirectoryName
        packageDigest = $integrity.packageDigest
        manifestDigest = $integrity.manifestDigest
        testEnvironment = 'test'
        publishTestOperationId = [string]$operation.operationId
        publishTestOperationStatus = 'SUCCESS'
        publishTestRequestedAt = [string]$operation.requestedAt
    }
    foreach ($entry in $expectedValues.GetEnumerator()) {
        if ([string]$tested.($entry.Key) -cne [string]$entry.Value) {
            throw "$($entry.Key) mismatch: $($tested.($entry.Key)) != $($entry.Value)"
        }
    }
    if (-not (Test-IsReleaseUtcInstant -Value ([string]$tested.testedAt))) {
        throw "testedAt invalid: $($tested.testedAt)"
    }
    if ([string]::IsNullOrWhiteSpace([string]$tested.testedBy)) {
        throw 'testedBy invalid: value is required'
    }
    if ([string]::IsNullOrWhiteSpace([string]$tested.testConclusion)) {
        throw 'testConclusion invalid: value is required'
    }
    return [pscustomobject][ordered]@{
        releaseTag = $integrity.releaseTag
        packageDigest = $integrity.packageDigest
        manifestDigest = $integrity.manifestDigest
        targetEnvironment = $TargetEnvironment
        testOperationId = [string]$operation.operationId
    }
}

Export-ModuleMember -Function @(
    'Assert-ReleasePackageDeploymentScope',
    'Assert-PublishTestOperationEvidence',
    'Assert-ReleaseRollbackCompatibility',
    'Get-ReleasePackageImmutableArtifactEntries',
    'Test-IsReleasePackageMutableMetadataPath',
    'Test-ReleasePackageIntegrity',
    'Test-ReleasePromotionAttestation',
    'Write-ReleaseTestedAttestation'
)
