Set-StrictMode -Version Latest

function Get-ReleaseBytesSha256Hex {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha256.Dispose()
    }
}

function ConvertTo-ReleaseAsciiCaseFoldPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $builder = [System.Text.StringBuilder]::new($Path.Length)
    foreach ($character in $Path.ToCharArray()) {
        $code = [int][char]$character
        if ($code -ge 65 -and $code -le 90) {
            [void]$builder.Append([char]($code + 32))
        } else {
            [void]$builder.Append($character)
        }
    }
    return $builder.ToString()
}

function Get-ReleasePackageDigest {
    param([Parameter(Mandatory = $true)][array]$Artifacts)
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    $entries = @()
    foreach ($artifact in @($Artifacts)) {
        $path = [string]$artifact.path
        if ([string]::IsNullOrWhiteSpace($path) -or $path -cne $path.Trim() -or $path.Contains('\') -or
            $path.StartsWith('/') -or $path -match '^[A-Za-z]:' -or $path -match '[\x00-\x1f\x7f]') {
            throw "PACKAGE_PATH_INVALID: $path"
        }
        $segments = $path.Split('/')
        if (@($segments | Where-Object { $_ -in @('', '.', '..') }).Count -gt 0) {
            throw "PACKAGE_PATH_INVALID: $path"
        }
        if (-not $seen.Add((ConvertTo-ReleaseAsciiCaseFoldPath -Path $path))) {
            throw "PACKAGE_PATH_INVALID: case-folded path collision: $path"
        }
        $sha256 = [string]$artifact.sha256
        if ($sha256 -notmatch '^[0-9a-f]{64}$') {
            throw "PACKAGE_PATH_INVALID: invalid sha256 for $path"
        }
        $sortKey = ([System.BitConverter]::ToString([System.Text.UTF8Encoding]::new($false).GetBytes($path))).Replace('-', '')
        $entries += [pscustomobject]@{ path = $path; bytes = [int64]$artifact.bytes; sha256 = $sha256.ToLowerInvariant(); sortKey = $sortKey }
    }
    $sortedInternal = @($entries | Sort-Object -Property sortKey)
    $sorted = @($sortedInternal | ForEach-Object {
        [pscustomobject]@{ path = $_.path; bytes = $_.bytes; sha256 = $_.sha256 }
    })
    $canonical = (($sorted | ForEach-Object { "$($_.path)`t$($_.bytes)`t$($_.sha256)`n" }) -join '')
    $canonicalBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($canonical)
    return [pscustomobject]@{
        Artifacts = $sorted
        CanonicalInput = $canonicalBytes
        PackageDigest = Get-ReleaseBytesSha256Hex -Bytes $canonicalBytes
    }
}

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
        throw "PACKAGE_PATH_INVALID: $Path"
    }
    if ($Path.Contains('\') -or $Path -match '^[A-Za-z]:' -or [System.IO.Path]::IsPathRooted($Path)) {
        throw "PACKAGE_PATH_INVALID: $Path"
    }
    if ($Path -match '[\x00-\x1f]' -or $Path.Contains('|')) {
        throw "PACKAGE_PATH_INVALID: $Path"
    }

    $segments = @($Path.Split('/'))
    if ($segments.Count -eq 0 -or @($segments | Where-Object { $_ -in @('', '.', '..') }).Count -gt 0) {
        throw "PACKAGE_PATH_INVALID: $Path"
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
        if (Test-IsReleasePackageMutableMetadataPath -RelativePath $relativePath) {
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
        [switch]$ExcludeManifestJson,
        [switch]$EmitProgress
    )

    $facts = @(Get-ReleasePackageImmutableArtifactFileFacts -PackagePath $PackagePath -ExcludeManifestJson:$ExcludeManifestJson)
    $entries = [System.Collections.Generic.List[object]]::new()
    $processedFiles = 0
    $processedBytes = [int64]0
    foreach ($fact in $facts) {
        $processedFiles++
        $processedBytes += [int64]$fact.bytes
        [void]$entries.Add([pscustomobject][ordered]@{
            path = $fact.path
            sha256 = Get-ReleaseSha256Hex -Path $fact.fullName
            bytes = [int64]$fact.bytes
        })
        if ($EmitProgress -and (($processedFiles % 128 -eq 0) -or $processedFiles -eq $facts.Count)) {
            Write-Host ("[INFO] Release artifact hashing progress: files={0}/{1}, bytes={2:n0}, gib={3:n2}" -f $processedFiles, $facts.Count, $processedBytes, ($processedBytes / 1GB))
        }
    }
    return @($entries.ToArray())
}

function Test-ReleasePackageIntegrity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackagePath,
        [string]$ExpectedReleaseTag = '',
        [string]$ExpectedPackageDirectoryName = '',
        [array]$PreverifiedArtifacts = @(),
        [switch]$EmitProgress
    )

    if (-not (Test-Path -LiteralPath $PackagePath -PathType Container)) {
        throw "Release package directory missing: $PackagePath"
    }
    $root = [System.IO.Path]::GetFullPath($PackagePath)
    $rootPrefix = $root.TrimEnd([char[]]@('\', '/')) + [System.IO.Path]::DirectorySeparatorChar
    foreach ($file in Get-ChildItem -LiteralPath $root -File -Recurse -Force) {
        $relativePath = $file.FullName.Substring($rootPrefix.Length).Replace('\', '/')
        $leaf = [System.IO.Path]::GetFileName($relativePath)
        if ($relativePath -ceq 'release-manifest.json' -or
            $leaf -cin @('ruoyi-vue-pro-current.sql', 'reset-db.sql', 'post-import.sql') -or
            $relativePath.StartsWith('minio/', [System.StringComparison]::OrdinalIgnoreCase) -or
            $relativePath -ieq 'manifest/dcc-object-inventory.json' -or
            $relativePath.StartsWith('runtime/', [System.StringComparison]::OrdinalIgnoreCase) -or
            $leaf -ieq '.env' -or $leaf.StartsWith('.env.', [System.StringComparison]::OrdinalIgnoreCase) -or
            $leaf.EndsWith('.rdb', [System.StringComparison]::OrdinalIgnoreCase) -or
            $leaf.EndsWith('.dump', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "PACKAGE_CONTENT_FORBIDDEN: $relativePath"
        }
    }

    $manifestPath = Join-Path $root 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw 'manifest.json: missing manifest'
    }
    $manifestBytes = [System.IO.File]::ReadAllBytes($manifestPath)
    try {
        $manifest = ([System.Text.UTF8Encoding]::new($false, $true).GetString($manifestBytes)) | ConvertFrom-Json
    } catch {
        throw "manifest.json: invalid JSON: $($_.Exception.Message)"
    }
    foreach ($propertyName in @('releaseTag', 'packageId', 'publishScope', 'packageDigest', 'sourceRoots', 'sourceRoles', 'artifacts')) {
        if ($manifest.PSObject.Properties.Name -cnotcontains $propertyName) {
            throw "manifest.json: missing $propertyName"
        }
    }
    $releaseTag = [string]$manifest.releaseTag
    $packageDirectoryName = [string]$manifest.packageId
    $publishScope = [string]$manifest.publishScope
    if ([string]::IsNullOrWhiteSpace($releaseTag)) {
        throw 'manifest.json: invalid releaseTag'
    }
    if (-not [string]::IsNullOrWhiteSpace($ExpectedReleaseTag) -and $releaseTag -cne $ExpectedReleaseTag) {
        throw "manifest.json: releaseTag mismatch: $releaseTag != $ExpectedReleaseTag"
    }
    $actualPackageDirectoryName = Split-Path -Leaf $root
    $expectedDirectoryName = if ([string]::IsNullOrWhiteSpace($ExpectedPackageDirectoryName)) {
        $actualPackageDirectoryName
    } else {
        $ExpectedPackageDirectoryName
    }
    if ($packageDirectoryName -cne $expectedDirectoryName) {
        throw "manifest.json: packageId mismatch: $packageDirectoryName != $expectedDirectoryName"
    }
    if ($publishScope -cne 'app-release') {
        throw "manifest.json: invalid publishScope: $publishScope"
    }
    $rootRoles = @($manifest.sourceRoots | ForEach-Object { [string]$_.rootRole } | Sort-Object)
    $sourceRoles = @($manifest.sourceRoles | ForEach-Object { [string]$_.sourceRole } | Sort-Object)
    if (($rootRoles -join ',') -cne 'application,maintenance' -or
        ($sourceRoles -join ',') -cne 'backend,frontend,maintenance') {
        throw 'manifest.json: source root or role set invalid'
    }
    $rootCommits = @{}
    foreach ($sourceRoot in @($manifest.sourceRoots)) {
        foreach ($propertyName in @('rootRole', 'normalizedRoot', 'approvedCommit', 'commit', 'dirty')) {
            if ($sourceRoot.PSObject.Properties.Name -cnotcontains $propertyName) {
                throw "MANIFEST_SOURCE_ROOT_INVALID: $($sourceRoot.rootRole) missing $propertyName"
            }
        }
        $normalizedRoot = [string]$sourceRoot.normalizedRoot
        $approvedCommit = [string]$sourceRoot.approvedCommit
        $commit = [string]$sourceRoot.commit
        if ([string]::IsNullOrWhiteSpace($normalizedRoot) -or $normalizedRoot -cne $normalizedRoot.Trim() -or
            $normalizedRoot.Contains('\') -or $normalizedRoot.Contains('/../') -or $normalizedRoot.Contains('/./') -or
            $sourceRoot.dirty -isnot [bool] -or [bool]$sourceRoot.dirty -or
            $approvedCommit -cnotmatch '^[0-9a-f]{40}$' -or $commit -cnotmatch '^[0-9a-f]{40}$' -or
            $approvedCommit -cne $commit) {
            throw "MANIFEST_SOURCE_ROOT_INVALID: $($sourceRoot.rootRole)"
        }
        $rootCommits[[string]$sourceRoot.rootRole] = $commit
    }
    $expectedRoleRoots = @{ maintenance = 'maintenance'; backend = 'application'; frontend = 'application' }
    $expectedRolePaths = @{ maintenance = '.'; backend = 'IntRuoyiBackend'; frontend = 'IntRuoyiFronted' }
    foreach ($sourceRole in @($manifest.sourceRoles)) {
        foreach ($propertyName in @('sourceRole', 'rootRole', 'relativePath', 'commit')) {
            if ($sourceRole.PSObject.Properties.Name -cnotcontains $propertyName) {
                throw "MANIFEST_SOURCE_ROLE_INVALID: $($sourceRole.sourceRole) missing $propertyName"
            }
        }
        $roleName = [string]$sourceRole.sourceRole
        $rootRole = [string]$sourceRole.rootRole
        $relativePath = [string]$sourceRole.relativePath
        $commit = [string]$sourceRole.commit
        if ($rootRole -cne [string]$expectedRoleRoots[$roleName] -or
            $relativePath -cne [string]$expectedRolePaths[$roleName] -or
            $commit -cnotmatch '^[0-9a-f]{40}$' -or $commit -cne [string]$rootCommits[$rootRole]) {
            throw "MANIFEST_SOURCE_ROLE_INVALID: $roleName"
        }
    }

    $preverifiedByPath = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
    foreach ($artifact in @($PreverifiedArtifacts)) {
        if ($null -eq $artifact) {
            continue
        }
        $preverifiedPath = ConvertTo-NormalizedReleaseArtifactPath -Path ([string]$artifact.path)
        $preverifiedKey = ConvertTo-ReleaseAsciiCaseFoldPath -Path $preverifiedPath
        if ($preverifiedByPath.ContainsKey($preverifiedKey)) {
            throw "PACKAGE_PATH_INVALID: duplicate preverified artifact path: $preverifiedPath"
        }
        $preverifiedByPath.Add($preverifiedKey, $artifact)
    }

    $declaredPaths = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
    $verifiedEntries = @()
    foreach ($artifact in @($manifest.artifacts)) {
        if ($null -eq $artifact) {
            throw 'manifest.json: invalid artifact entry'
        }
        foreach ($propertyName in @('path', 'sha256', 'bytes')) {
            if ($artifact.PSObject.Properties.Name -cnotcontains $propertyName) {
                throw "manifest.json: artifact missing $propertyName"
            }
        }
        $declaredPath = [string]$artifact.path
        $relativePath = ConvertTo-NormalizedReleaseArtifactPath -Path $declaredPath
        $relativePathKey = ConvertTo-ReleaseAsciiCaseFoldPath -Path $relativePath
        if ($relativePath -ceq 'manifest.json' -or (Test-IsReleasePackageMutableMetadataPath -RelativePath $relativePath)) {
            throw "PACKAGE_PATH_INVALID: $relativePath"
        }
        if ($declaredPaths.ContainsKey($relativePathKey)) {
            throw "PACKAGE_PATH_INVALID: duplicate or case-folded artifact path: $relativePath"
        }
        $declaredPaths.Add($relativePathKey, $artifact)

        $declaredHash = [string]$artifact.sha256
        if ($declaredHash -cnotmatch '^(sha256:)?[0-9a-f]{64}$') {
            throw "${relativePath}: invalid sha256"
        }
        if ($declaredHash.StartsWith('sha256:')) {
            $declaredHash = $declaredHash.Substring(7)
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
        if ($preverifiedByPath.ContainsKey($relativePathKey)) {
            $preverified = $preverifiedByPath[$relativePathKey]
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

    if ($preverifiedByPath.Count -gt 0) {
        foreach ($actual in @(Get-ReleasePackageImmutableArtifactFileFacts -PackagePath $root -ExcludeManifestJson)) {
            if (-not $declaredPaths.ContainsKey((ConvertTo-ReleaseAsciiCaseFoldPath -Path ([string]$actual.path)))) {
                throw "$($actual.path): undeclared file"
            }
        }
    } else {
        foreach ($actual in @(Get-ReleasePackageImmutableArtifactEntries -PackagePath $root -ExcludeManifestJson -EmitProgress:$EmitProgress)) {
            if (-not $declaredPaths.ContainsKey((ConvertTo-ReleaseAsciiCaseFoldPath -Path ([string]$actual.path)))) {
                throw "$($actual.path): undeclared file"
            }
        }
    }
    if ($verifiedEntries.Count -ne $declaredPaths.Count) {
        throw 'manifest.json: artifact set mismatch'
    }

    $digest = Get-ReleasePackageDigest -Artifacts $verifiedEntries
    $packageDigest = [string]$digest.PackageDigest
    if ([string]$manifest.packageDigest -cne $packageDigest) {
        throw "manifest.json: packageDigest mismatch: $($manifest.packageDigest) != $packageDigest"
    }
    $manifestDigest = Get-ReleaseBytesSha256Hex -Bytes $manifestBytes

    return [pscustomobject][ordered]@{
        releaseTag = $releaseTag
        packageDirectoryName = $packageDirectoryName
        publishScope = $publishScope
        manifestDigest = $manifestDigest
        packageDigest = $packageDigest
        sourceRoots = @($manifest.sourceRoots)
        sourceRoles = @($manifest.sourceRoles)
        artifacts = @($digest.Artifacts)
    }
}

function Assert-ReleasePackageDeploymentScope {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('test', 'prod', 'backup')]
        [string]$TargetEnvironment,
        [Parameter(Mandatory = $true)]
        [ValidateSet('app-release')]
        [string]$PublishScope
    )

    if ($PublishScope -ne 'app-release') {
        throw "Standard workflow requires an app-release package; publishScope=$PublishScope"
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
        [string]$TestResult = '',
        [Parameter(Mandatory = $true)]
        [string]$TestedBy,
        [Parameter(Mandatory = $true)]
        [string]$TestConclusion,
        [hashtable]$RecoverySet
    )

    if ([string]::IsNullOrWhiteSpace($TestedBy)) {
        throw 'testedBy invalid: value is required'
    }
    if ($TestResult -cne 'PASS') {
        throw 'testResult invalid: PASS is required'
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
        testResult = 'PASS'
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
    if ($integrity.publishScope -cne 'app-release') {
        throw "publishScope mismatch: $($integrity.publishScope) != app-release"
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
    'Get-ReleaseBytesSha256Hex',
    'Get-ReleasePackageDigest',
    'Get-ReleasePackageImmutableArtifactEntries',
    'Test-IsReleasePackageMutableMetadataPath',
    'Test-ReleasePackageIntegrity',
    'Test-ReleasePromotionAttestation',
    'Write-ReleaseTestedAttestation'
)
