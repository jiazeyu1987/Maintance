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

function Get-ReleasePlatformPrerequisites {
    param([Parameter(Mandatory = $true)][ValidateSet('intruoyi', 'full')][string]$Component)
    $items = @([ordered]@{
        toolId = 'dcc-codex'
        pathEnv = 'DCC_PROJECT_CODE_CODEX_CLI_COMMAND'
        sha256Env = 'DCC_PROJECT_CODE_CODEX_CLI_SHA256'
    })
    if ($Component -eq 'full') {
        $items += [ordered]@{
            toolId = 'showroom-codex'
            pathEnv = 'SHOWROOM_CODEX_CLI_COMMAND'
            sha256Env = 'SHOWROOM_CODEX_CLI_SHA256'
        }
    }
    return $items
}

function Get-ReleaseManagedImageReferences {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('intruoyi', 'full')][string]$Component,
        [Parameter(Mandatory = $true)][string]$PackageId,
        [Parameter(Mandatory = $true)][bool]$OnlyOfficeIncluded
    )
    $images = [ordered]@{
        backend = "intruoyi-backend:$PackageId"
        frontend = "intruoyi-frontend:$PackageId"
        'scheduler-smoke' = 'mcr.microsoft.com/playwright:v1.60.0-noble'
    }
    if ($Component -eq 'full') { $images['website'] = 'nginx:1.27-alpine' }
    if ($OnlyOfficeIncluded) { $images['onlyoffice'] = 'onlyoffice/documentserver:latest' }
    return $images
}

function Get-ReleaseTarConfigBytes {
    param([string]$ArchivePath, [string]$EntryPath, [switch]$DigestOnly)
    if ($EntryPath -cnotmatch '^((blobs/sha256/)?[0-9a-f]{64}(\.json)?|index\.json|oci-layout)$') {
        throw 'PACKAGE_IMAGE_ARCHIVE_INVALID: unsafe Docker config path'
    }
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = (Get-Command tar -ErrorAction Stop).Source
    $startInfo.Arguments = '-xOf "' + $ArchivePath + '" "' + $EntryPath + '"'
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $bytes = [IO.MemoryStream]::new()
    try {
        [void]$process.Start()
        $stderr = $process.StandardError.ReadToEndAsync()
        if ($DigestOnly) {
            $hash = [Security.Cryptography.SHA256]::Create()
            try {
                $buffer = New-Object byte[] (1024 * 1024)
                [int64]$length = 0
                while (($count = $process.StandardOutput.BaseStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                    [void]$hash.TransformBlock($buffer, 0, $count, $null, 0)
                    $length += $count
                }
                [void]$hash.TransformFinalBlock([byte[]]@(), 0, 0)
                $digest = ([BitConverter]::ToString($hash.Hash)).Replace('-', '').ToLowerInvariant()
            } finally { $hash.Dispose() }
        } else {
            $process.StandardOutput.BaseStream.CopyTo($bytes)
        }
        $process.WaitForExit()
        [void]$stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw 'PACKAGE_IMAGE_ARCHIVE_INVALID: cannot read Docker config bytes' }
        if ($DigestOnly) { return @{ sha256 = $digest; bytes = $length } }
        return ,$bytes.ToArray()
    } finally {
        $bytes.Dispose()
        $process.Dispose()
    }
}

function Assert-ReleaseArchiveImageIdentity {
    param([string]$ArchivePath, [array]$ArchivePaths, [object]$ArchiveImage, [object]$Identity)
    $name = [string]$Identity.name
    $configPath = [string]$ArchiveImage.Config
    foreach ($entry in (@($configPath) + @($ArchiveImage.Layers))) {
        if (@($ArchivePaths | Where-Object { $_ -ceq $entry }).Count -ne 1) {
            throw "PACKAGE_IMAGE_PAYLOAD_MISSING: $name/$entry missing or duplicated"
        }
    }
    $configBytes = Get-ReleaseTarConfigBytes -ArchivePath $ArchivePath -EntryPath $configPath
    $configDigest = Get-ReleaseBytesSha256Hex -Bytes $configBytes
    $configName = [IO.Path]::GetFileName($configPath) -replace '\.json$', ''
    if ($configName -cne $configDigest) {
        throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name Docker config content"
    }
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    $config = $utf8.GetString($configBytes) | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$config.os) -or [string]::IsNullOrWhiteSpace([string]$config.architecture) -or
        $null -eq $config.rootfs -or $config.rootfs.type -cne 'layers' -or $null -eq $config.rootfs.diff_ids) {
        throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name platform/rootfs metadata"
    }
    foreach ($diffId in @($config.rootfs.diff_ids)) {
        if ($diffId -cnotmatch '^sha256:[0-9a-f]{64}$') { throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name rootfs digest" }
    }
    $verified = [pscustomobject][ordered]@{
        name = $name
        reference = [string]$Identity.reference
        buildImageId = [string]$Identity.id
        descriptorDigest = $null
        configDigest = "sha256:$configDigest"
        platform = [pscustomobject]@{ os = [string]$config.os; architecture = [string]$config.architecture }
        rootfsDiffIds = @($config.rootfs.diff_ids)
    }
    # Classic Docker stores image identity as the config digest. Containerd's
    # content store uses an OCI/Docker manifest descriptor identity instead.
    if ($Identity.id -ceq "sha256:$configDigest") { return $verified }
    foreach ($entry in @('oci-layout', 'index.json')) {
        if (@($ArchivePaths | Where-Object { $_ -ceq $entry }).Count -ne 1) {
            throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name requires an OCI descriptor"
        }
    }
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    $layout = $utf8.GetString((Get-ReleaseTarConfigBytes -ArchivePath $ArchivePath -EntryPath 'oci-layout')) | ConvertFrom-Json
    $index = $utf8.GetString((Get-ReleaseTarConfigBytes -ArchivePath $ArchivePath -EntryPath 'index.json')) | ConvertFrom-Json
    if ($layout.imageLayoutVersion -cne '1.0.0' -or $index.schemaVersion -ne 2) {
        throw "PACKAGE_IMAGE_ARCHIVE_INVALID: $name unsupported OCI layout/index"
    }
    $descriptors = @($index.manifests | Where-Object {
        $_.digest -ceq $Identity.id -and $_.annotations.'io.containerd.image.name' -ceq $Identity.reference
    })
    if ($descriptors.Count -ne 1) { throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI reference binding" }
    $descriptor = $descriptors[0]
    $manifestTypes = @('application/vnd.oci.image.manifest.v1+json', 'application/vnd.docker.distribution.manifest.v2+json')
    if ($descriptor.mediaType -cnotin $manifestTypes -or $descriptor.digest -cnotmatch '^sha256:[0-9a-f]{64}$') {
        throw "PACKAGE_IMAGE_ARCHIVE_INVALID: $name unsupported OCI image descriptor"
    }
    $manifestPath = 'blobs/sha256/' + $descriptor.digest.Substring(7)
    if (@($ArchivePaths | Where-Object { $_ -ceq $manifestPath }).Count -ne 1) {
        throw "PACKAGE_IMAGE_PAYLOAD_MISSING: $name manifest blob"
    }
    $manifestBytes = Get-ReleaseTarConfigBytes -ArchivePath $ArchivePath -EntryPath $manifestPath
    if ($descriptor.size -isnot [ValueType] -or $descriptor.size -ne $manifestBytes.Length -or
        ('sha256:' + (Get-ReleaseBytesSha256Hex -Bytes $manifestBytes)) -cne $descriptor.digest) {
        throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI manifest bytes"
    }
    $manifest = $utf8.GetString($manifestBytes) | ConvertFrom-Json
    if ($manifest.schemaVersion -ne 2 -or $manifest.mediaType -cne $descriptor.mediaType -or
        $manifest.config.digest -cne "sha256:$configDigest" -or
        $manifest.config.size -isnot [ValueType] -or $manifest.config.size -ne $configBytes.Length -or
        $configPath -cne "blobs/sha256/$configDigest") {
        throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI config binding"
    }
    if (@($manifest.layers).Count -ne @($ArchiveImage.Layers).Count) {
        throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI layer count"
    }
    for ($i = 0; $i -lt @($manifest.layers).Count; $i++) {
        $layer = @($manifest.layers)[$i]
        if ($layer.digest -cnotmatch '^sha256:[0-9a-f]{64}$' -or $layer.size -isnot [ValueType] -or $layer.size -le 0) {
            throw "PACKAGE_IMAGE_ARCHIVE_INVALID: $name OCI layer descriptor"
        }
        $layerPath = 'blobs/sha256/' + $layer.digest.Substring(7)
        if (@($ArchiveImage.Layers)[$i] -cne $layerPath) {
            throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI ordered layer binding"
        }
        $fact = Get-ReleaseTarConfigBytes -ArchivePath $ArchivePath -EntryPath $layerPath -DigestOnly
        if ($fact.bytes -ne $layer.size -or ('sha256:' + $fact.sha256) -cne $layer.digest) {
            throw "PACKAGE_IMAGE_IDENTITY_MISMATCH: $name OCI layer bytes"
        }
    }
    $verified.descriptorDigest = [string]$descriptor.digest
    return $verified
}

function Assert-ReleaseInstallationContract {
    param([string]$PackagePath, [object]$Manifest, [array]$Artifacts)
    foreach ($field in @('installationContractVersion', 'component', 'components', 'onlyOfficeIncluded', 'runtimeImages', 'targetRequirements')) {
        if ($Manifest.PSObject.Properties.Name -cnotcontains $field) {
            throw "PACKAGE_INSTALLATION_CONTRACT_INVALID: missing $field; rebuild the complete package"
        }
    }
    if ($Manifest.installationContractVersion -cne 'full-app-release/v1') {
        throw 'PACKAGE_INSTALLATION_CONTRACT_INVALID: unsupported installation contract; rebuild the complete package'
    }
    if ($Manifest.component -cnotin @('intruoyi', 'full')) {
        throw "PACKAGE_COMPONENT_INVALID: $($Manifest.component); backend and frontend must be delivered together"
    }
    if ($Manifest.onlyOfficeIncluded -isnot [bool]) {
        throw 'PACKAGE_INSTALLATION_CONTRACT_INVALID: onlyOfficeIncluded must be a boolean'
    }
    $expectedComponents = @('backend', 'admin-frontend', 'database-contract', 'required-sql', 'runtime-env', 'packaging-manifest')
    if ($Manifest.component -eq 'full') { $expectedComponents += 'website' }
    if ($Manifest.onlyOfficeIncluded) { $expectedComponents += 'onlyoffice' }
    if ((@($Manifest.components | Sort-Object) -join ',') -cne (@($expectedComponents | Sort-Object) -join ',')) {
        throw 'PACKAGE_COMPONENT_SET_MISMATCH: manifest component set differs from the complete profile'
    }
    if ($null -eq $Manifest.targetRequirements -or $null -eq $Manifest.targetRequirements.PSObject.Properties['platformPrerequisites']) {
        throw 'PACKAGE_INSTALLATION_CONTRACT_INVALID: missing platformPrerequisites; rebuild the complete package'
    }
    $expectedPrerequisites = @(Get-ReleasePlatformPrerequisites -Component $Manifest.component)
    $prerequisites = @($Manifest.targetRequirements.platformPrerequisites)
    if ($prerequisites.Count -ne $expectedPrerequisites.Count) {
        throw 'PACKAGE_INSTALLATION_CONTRACT_INVALID: platformPrerequisites set mismatch'
    }
    foreach ($expected in $expectedPrerequisites) {
        $matches = @($prerequisites | Where-Object { $_.toolId -ceq $expected.toolId })
        if ($matches.Count -ne 1 -or $matches[0].pathEnv -cne $expected.pathEnv -or $matches[0].sha256Env -cne $expected.sha256Env) {
            throw "PACKAGE_INSTALLATION_CONTRACT_INVALID: platformPrerequisites mismatch for $($expected.toolId)"
        }
    }
    $requiredPaths = @(
        'docker-compose.yml', "intruoyi-images_$($Manifest.packageId).tar", 'manifest/docker-build-evidence.json',
        'ops-runtime/linux/backup-ops-linux.sh', 'ops-runtime/scripts/backup-ops.ps1', 'smoke/bin/npm',
        'smoke/yudao-ui-admin-vue3/package.json', 'smoke/yudao-ui-admin-vue3/package-lock.json',
        'smoke/yudao-ui-admin-vue3/dependencies.tar',
        'smoke/yudao-ui-admin-vue3/tests/e2e/smart-scheduling-smoke-real-flow.e2e.js',
        'smoke/yudao-ui-admin-vue3/tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js'
    )
    if ($Manifest.component -eq 'full') { $requiredPaths += @('website/nginx.template.conf', 'website/dist/index.html') }
    $paths = @($Artifacts | ForEach-Object { [string]$_.path })
    foreach ($path in $requiredPaths) {
        if ($paths -cnotcontains $path) { throw "PACKAGE_REQUIRED_ARTIFACT_MISSING: $path; rebuild the complete package" }
        if ([int64](@($Artifacts | Where-Object { $_.path -ceq $path })[0].bytes) -le 0) {
            throw "PACKAGE_REQUIRED_ARTIFACT_EMPTY: $path; rebuild the complete package"
        }
    }
    foreach ($prefix in @('required-sql/', 'ops-runtime/actions/')) {
        if (@($paths | Where-Object { $_.StartsWith($prefix, [StringComparison]::Ordinal) }).Count -eq 0) {
            throw "PACKAGE_REQUIRED_ARTIFACT_MISSING: $prefix"
        }
    }
    if ($paths -ccontains 'website/nginx.conf') { throw 'PACKAGE_CONTENT_FORBIDDEN: website/nginx.conf is target configuration' }
    if (-not (Get-Command tar -ErrorAction SilentlyContinue)) { throw 'PACKAGE_VALIDATION_PREREQUISITE_MISSING: tar' }
    $archivePath = Join-Path $PackagePath "intruoyi-images_$($Manifest.packageId).tar"
    $archivePaths = @(& tar -tf $archivePath 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_IMAGE_ARCHIVE_INVALID: unable to list Docker image archive' }
    $archiveManifestText = (& tar -xOf $archivePath 'manifest.json' 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_IMAGE_ARCHIVE_INVALID: missing Docker manifest.json' }
    try {
        $parsedArchiveImages = $archiveManifestText | ConvertFrom-Json
        $archiveImages = @($parsedArchiveImages)
    }
    catch { throw "PACKAGE_IMAGE_ARCHIVE_INVALID: $($_.Exception.Message)" }
    $references = Get-ReleaseManagedImageReferences -Component $Manifest.component -PackageId $Manifest.packageId -OnlyOfficeIncluded $Manifest.onlyOfficeIncluded
    if (@($Manifest.runtimeImages).Count -ne $references.Count) { throw 'PACKAGE_IMAGE_SET_MISMATCH: runtimeImages count' }
    $verifiedImageContent = @()
    foreach ($name in $references.Keys) {
        $reference = [string]$references[$name]
        $identities = @($Manifest.runtimeImages | Where-Object { $_.name -ceq $name })
        if ($identities.Count -ne 1 -or $identities[0].reference -cne $reference -or
            $identities[0].id -cnotmatch '^sha256:[0-9a-f]{64}$' -or $identities[0].sizeBytes -le 0) {
            throw "PACKAGE_IMAGE_IDENTITY_INVALID: $name"
        }
        $matches = @($archiveImages | Where-Object { @($_.RepoTags) -ccontains $reference })
        if ($matches.Count -ne 1) { throw "PACKAGE_IMAGE_MISSING: $reference" }
        $verifiedImageContent += Assert-ReleaseArchiveImageIdentity -ArchivePath $archivePath -ArchivePaths $archivePaths -ArchiveImage $matches[0] -Identity $identities[0]
    }
    foreach ($entry in $archiveImages) {
        foreach ($reference in @($entry.RepoTags)) {
            if (@($references.Values) -cnotcontains $reference) { throw "PACKAGE_IMAGE_UNDECLARED: $reference" }
        }
    }
    $buildEvidence = [IO.File]::ReadAllText((Join-Path $PackagePath 'manifest/docker-build-evidence.json'), [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    if ($buildEvidence.schemaVersion -cne 'release-docker-build-evidence/v1') { throw 'PACKAGE_BUILD_EVIDENCE_INVALID: schemaVersion' }
    foreach ($name in @('backend', 'frontend')) {
        $entries = @($buildEvidence.components | Where-Object { $_.name -ceq $name })
        $identity = @($Manifest.runtimeImages | Where-Object { $_.name -ceq $name })[0]
        if ($entries.Count -ne 1 -or $entries[0].actualImage.id -cne $identity.id -or $entries[0].actualImage.reference -cne $identity.reference) {
            throw "PACKAGE_BUILD_EVIDENCE_INVALID: $name"
        }
    }
    $dependencyArchive = Join-Path $PackagePath 'smoke/yudao-ui-admin-vue3/dependencies.tar'
    $dependencyPaths = @(& tar -tf $dependencyArchive 2>&1)
    if ($LASTEXITCODE -ne 0) { throw 'PACKAGE_SMOKE_DEPENDENCIES_INVALID: archive unreadable' }
    foreach ($entry in @('node_modules/playwright/package.json', 'node_modules/xlsx/package.json')) {
        if ($dependencyPaths -cnotcontains $entry) { throw "PACKAGE_SMOKE_DEPENDENCIES_INVALID: missing $entry" }
    }
    return $verifiedImageContent
}

function Assert-ReleaseTargetPreflightArtifacts {
    param([object]$Manifest, [array]$Artifacts)
    if ($null -eq $Manifest.PSObject.Properties['requiredSql']) { return }
    foreach ($migration in @($Manifest.requiredSql)) {
        $hasReference = $null -ne $migration.PSObject.Properties['targetPreflight'] -and $null -ne $migration.targetPreflight
        $required = $null -ne $migration.PSObject.Properties['requiresTargetPreflight'] -and $migration.requiresTargetPreflight -eq $true
        if (-not $hasReference -and -not $required) { continue }
        $id = [string]$migration.migrationId
        if (-not $hasReference) { throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id requires a packaged check" }
        $check = $migration.targetPreflight
        foreach ($field in @('reference', 'sha256', 'readOnly')) {
            if ($null -eq $check.PSObject.Properties[$field]) { throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id missing $field" }
        }
        $digest = ([string]$check.sha256) -creplace '^sha256:', ''
        if ($check.reference -cne "target-preflight/$id.preflight.sql" -or $check.readOnly -isnot [bool] -or
            -not $check.readOnly -or $digest -cnotmatch '^[0-9a-f]{64}$') {
            throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id reference/hash/readOnly contract"
        }
        $files = @($Artifacts | Where-Object { $_.path -ceq $check.reference })
        if ($files.Count -ne 1 -or $files[0].sha256 -cne $digest -or $files[0].bytes -le 0) {
            throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id missing or mismatched $($check.reference)"
        }
        if ($null -eq $Manifest.PSObject.Properties['database'] -or $null -eq $Manifest.database.PSObject.Properties['schemaMigrations'] -or
            $null -eq $Manifest.PSObject.Properties['migrationPlan']) {
            throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id requires all three migration projections"
        }
        foreach ($projection in @(@{ entries = @($Manifest.database.schemaMigrations) }, @{ entries = @($Manifest.migrationPlan) })) {
            $matches = @($projection.entries | Where-Object { $_.migrationId -ceq $id })
            if ($matches.Count -ne 1 -or $null -eq $matches[0].PSObject.Properties['targetPreflight'] -or $null -eq $matches[0].targetPreflight) {
                throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id projection missing check"
            }
            $other = $matches[0].targetPreflight
            if ($other.reference -cne $check.reference -or (([string]$other.sha256) -creplace '^sha256:', '') -cne $digest -or
                $other.readOnly -isnot [bool] -or $other.readOnly -ne $true) {
                throw "PACKAGE_TARGET_PREFLIGHT_INVALID: $id projection contract mismatch"
            }
        }
    }
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
            ($relativePath.StartsWith('runtime-env/', [System.StringComparison]::OrdinalIgnoreCase) -and $leaf.EndsWith('.env', [System.StringComparison]::OrdinalIgnoreCase)) -or
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
    $verifiedImageContent = @(Assert-ReleaseInstallationContract -PackagePath $root -Manifest $manifest -Artifacts $digest.Artifacts)
    Assert-ReleaseTargetPreflightArtifacts -Manifest $manifest -Artifacts $digest.Artifacts

    return [pscustomobject][ordered]@{
        releaseTag = $releaseTag
        packageDirectoryName = $packageDirectoryName
        publishScope = $publishScope
        manifestDigest = $manifestDigest
        packageDigest = $packageDigest
        sourceRoots = @($manifest.sourceRoots)
        sourceRoles = @($manifest.sourceRoles)
        artifacts = @($digest.Artifacts)
        component = [string]$manifest.component
        components = @($manifest.components)
        onlyOfficeIncluded = [bool]$manifest.onlyOfficeIncluded
        runtimeImages = @($manifest.runtimeImages)
        verifiedImageContent = $verifiedImageContent
        platformPrerequisites = @($manifest.targetRequirements.platformPrerequisites)
    }
}

function Assert-ReleaseWorkflowPackageBinding {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$PackageIntegrity,
        [string]$ExpectedPackageDigest,
        [string]$ExpectedManifestDigest
    )

    if ($ExpectedPackageDigest -cnotmatch '^[0-9a-f]{64}$' -or
        $ExpectedManifestDigest -cnotmatch '^[0-9a-f]{64}$') {
        throw 'RELEASE_WORKFLOW_EXPECTED_DIGEST_REQUIRED'
    }
    if ([string]$PackageIntegrity.packageDigest -cne $ExpectedPackageDigest) {
        throw 'RELEASE_WORKFLOW_PACKAGE_DIGEST_MISMATCH'
    }
    if ([string]$PackageIntegrity.manifestDigest -cne $ExpectedManifestDigest) {
        throw 'RELEASE_WORKFLOW_MANIFEST_DIGEST_MISMATCH'
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
    'Get-ReleasePlatformPrerequisites',
    'Get-ReleaseManagedImageReferences',
    'Assert-ReleaseWorkflowPackageBinding',
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
