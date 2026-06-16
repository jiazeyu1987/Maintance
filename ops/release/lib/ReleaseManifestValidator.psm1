Set-StrictMode -Version Latest

$script:ValidationMode = 'manifest-v1-validation'
$script:AllowedPackageTypes = @(
    'full-release',
    'smart-release',
    'data-release',
    'resource-check-only'
)
$script:RequiredTopLevelFields = @(
    'manifestVersion',
    'packageId',
    'releaseTag',
    'packageType',
    'createdAt',
    'createdBy',
    'sourceRepos',
    'changeSet',
    'publishScope',
    'components',
    'artifacts',
    'database',
    'schemaVersion',
    'schemaDigest',
    'migrationPlan',
    'requiredSql',
    'buildModules',
    'compatibilityMatrix',
    'operationEvidencePolicy',
    'resources',
    'targetRequirements',
    'buildContract',
    'deployContract',
    'precheckPlan',
    'verifyPlan',
    'rollbackPlan',
    'forbiddenFieldsCheck',
    'manifestChecksum'
)
$script:ImplicitPackageFiles = @(
    'manifest.json',
    'release-manifest.json',
    'legacy-release-manifest.json'
)
$script:ScannableExtensions = @(
    '.json',
    '.yaml',
    '.yml',
    '.env',
    '.ps1',
    '.sql',
    '.md'
)
$script:Sha256Pattern = '^sha256:[a-fA-F0-9]{64}$'
$script:Ipv4Pattern = '(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])'
$script:SecretPattern = '(?im)(?:^|["''\s\{,;])(?:db_)?(?:password|passwd|secret_key|secretkey|access_key|accesskey|token|private_key|privatekey|ssh_password|sshpassword|nas_password|naspassword)\s*["'']?\s*[:=]\s*["'']?([^"''\s,;]+)'

function New-ReleaseManifestDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    return [pscustomobject]([ordered]@{
        status = $Status
        code = $Code
        scope = $Scope
        path = $Path
        message = $Message
        impact = $Impact
        nextStep = $NextStep
    })
}

function New-ReleaseManifestValidationResult {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Warnings,
        [Parameter(Mandatory = $true)]$Checks
    )

    if ($Errors.Count -gt 0) {
        $primary = $Errors[0]
        $status = 'failed'
    } elseif ($Warnings.Count -gt 0) {
        $primary = $Warnings[0]
        $status = 'warning'
    } else {
        $primary = New-ReleaseManifestDiagnostic `
            -Status 'passed' `
            -Code 'MANIFEST_VALIDATION_PASSED' `
            -Scope 'manifest' `
            -Path $PackagePath `
            -Message 'Manifest v1 validation passed.' `
            -Impact 'The release package contract is structurally valid for Phase 1 report-only gates.' `
            -NextStep 'Continue build intake or deploy precheck report-only validation.'
        $status = 'passed'
    }

    return [pscustomobject]([ordered]@{
        status = $status
        mode = $Mode
        code = $primary.code
        scope = $primary.scope
        path = $primary.path
        message = $primary.message
        impact = $primary.impact
        nextStep = $primary.nextStep
        errors = @($Errors.ToArray())
        warnings = @($Warnings.ToArray())
        checks = @($Checks.ToArray())
    })
}

function Test-ManifestPropertyPresent {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $false
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $false
    }
    if ($null -eq $property.Value) {
        return $false
    }
    if (($property.Value -is [string]) -and [string]::IsNullOrWhiteSpace($property.Value)) {
        return $false
    }
    return $true
}

function Get-ManifestPropertyValue {
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

function ConvertTo-ManifestArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function ConvertTo-ManifestRelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue
    )

    $normalized = $PathValue.Trim() -replace '\\', '/'
    while ($normalized.StartsWith('./')) {
        $normalized = $normalized.Substring(2)
    }
    return $normalized.TrimStart('/')
}

function Get-RelativePackagePath {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$FullPath
    )

    $root = [System.IO.Path]::GetFullPath($PackagePath).TrimEnd([char[]]@('\', '/'))
    $file = [System.IO.Path]::GetFullPath($FullPath)
    if ($file.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return ($file.Substring($root.Length).TrimStart([char[]]@('\', '/')) -replace '\\', '/')
    }
    return ($file -replace '\\', '/')
}

function Resolve-PackageChildPath {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $nativeRelative = (ConvertTo-ManifestRelativePath -PathValue $RelativePath) -replace '/', [System.IO.Path]::DirectorySeparatorChar
    return [System.IO.Path]::GetFullPath((Join-Path -Path $PackagePath -ChildPath $nativeRelative))
}

function Read-Utf8File {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
}

function Get-ManifestSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return ('sha256:' + (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant())
}

function Add-ManifestDeclaration {
    param(
        [Parameter(Mandatory = $true)]$Declarations,
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][string]$Scope,
        [string]$Sha256
    )

    $normalized = ConvertTo-ManifestRelativePath -PathValue $RelativePath
    [void]$Declarations.Add([pscustomobject]([ordered]@{
        relativePath = $normalized
        scope = $Scope
        sha256 = $Sha256
    }))
}

function Get-ReleaseManifestDeclarations {
    param(
        [Parameter(Mandatory = $true)]$Manifest
    )

    $declarations = New-Object System.Collections.ArrayList
    $artifacts = @(ConvertTo-ManifestArray -Value (Get-ManifestPropertyValue -Object $Manifest -Name 'artifacts'))
    for ($index = 0; $index -lt $artifacts.Count; $index++) {
        $artifact = $artifacts[$index]
        $included = Get-ManifestPropertyValue -Object $artifact -Name 'includedInPackage'
        if ($included -eq $true) {
            $path = Get-ManifestPropertyValue -Object $artifact -Name 'path'
            if (-not [string]::IsNullOrWhiteSpace([string]$path)) {
                $sha256 = Get-ManifestPropertyValue -Object $artifact -Name 'sha256'
                Add-ManifestDeclaration `
                    -Declarations $declarations `
                    -RelativePath ([string]$path) `
                    -Scope "artifacts[$index].path" `
                    -Sha256 ([string]$sha256)
            }
        }
    }

    $database = Get-ManifestPropertyValue -Object $Manifest -Name 'database'
    $schemaMigrations = @(ConvertTo-ManifestArray -Value (Get-ManifestPropertyValue -Object $database -Name 'schemaMigrations'))
    for ($index = 0; $index -lt $schemaMigrations.Count; $index++) {
        $migration = $schemaMigrations[$index]
        $path = Get-ManifestPropertyValue -Object $migration -Name 'file'
        if (-not [string]::IsNullOrWhiteSpace([string]$path)) {
            $sha256 = Get-ManifestPropertyValue -Object $migration -Name 'sha256'
            Add-ManifestDeclaration `
                -Declarations $declarations `
                -RelativePath ([string]$path) `
                -Scope "database.schemaMigrations[$index].file" `
                -Sha256 ([string]$sha256)
        }
    }

    $requiredDataSets = @(ConvertTo-ManifestArray -Value (Get-ManifestPropertyValue -Object $database -Name 'requiredDataSets'))
    for ($index = 0; $index -lt $requiredDataSets.Count; $index++) {
        $dataSet = $requiredDataSets[$index]
        $path = Get-ManifestPropertyValue -Object $dataSet -Name 'file'
        if (-not [string]::IsNullOrWhiteSpace([string]$path)) {
            $sha256 = Get-ManifestPropertyValue -Object $dataSet -Name 'sha256'
            Add-ManifestDeclaration `
                -Declarations $declarations `
                -RelativePath ([string]$path) `
                -Scope "database.requiredDataSets[$index].file" `
                -Sha256 ([string]$sha256)
        }
    }

    $resources = Get-ManifestPropertyValue -Object $Manifest -Name 'resources'
    $resourceReferenceManifest = Get-ManifestPropertyValue -Object $resources -Name 'resourceReferenceManifest'
    if (-not [string]::IsNullOrWhiteSpace([string]$resourceReferenceManifest)) {
        Add-ManifestDeclaration `
            -Declarations $declarations `
            -RelativePath ([string]$resourceReferenceManifest) `
            -Scope 'resources.resourceReferenceManifest'
    }

    $resourceDeltaProofPath = Get-ManifestPropertyValue -Object $resources -Name 'resourceDeltaProofPath'
    if (-not [string]::IsNullOrWhiteSpace([string]$resourceDeltaProofPath)) {
        Add-ManifestDeclaration `
            -Declarations $declarations `
            -RelativePath ([string]$resourceDeltaProofPath) `
            -Scope 'resources.resourceDeltaProofPath'
    }

    return $declarations
}

function Add-RequiredFieldDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks,
        [Parameter(Mandatory = $true)][string]$ManifestPath
    )

    $missingFields = @()
    foreach ($field in $script:RequiredTopLevelFields) {
        if (-not (Test-ManifestPropertyPresent -Object $Manifest -Name $field)) {
            $missingFields += $field
            [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                -Status 'failed' `
                -Code 'MANIFEST_REQUIRED_FIELD_MISSING' `
                -Scope $field `
                -Path $ManifestPath `
                -Message "Manifest v1 is missing required field '$field'." `
                -Impact 'The package cannot be safely interpreted by Smart Release Phase 1 gates.' `
                -NextStep "Add '$field' to manifest.json according to manifest-v1.schema.json."))
        }
    }

    if ($missingFields.Count -eq 0) {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'passed' `
            -Code 'MANIFEST_REQUIRED_FIELDS_PRESENT' `
            -Scope 'manifest.required' `
            -Path $ManifestPath `
            -Message 'All required Manifest v1 top-level fields are present.' `
            -Impact 'Schema-level validation can continue.' `
            -NextStep 'Continue package type, baseline, file, checksum, and forbidden field checks.'))
    } else {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_REQUIRED_FIELD_MISSING' `
            -Scope 'manifest.required' `
            -Path $ManifestPath `
            -Message ('Missing required Manifest v1 fields: ' + ($missingFields -join ', ') + '.') `
            -Impact 'Manifest v1 validation failed.' `
            -NextStep 'Add the missing fields and rerun validate-release-manifest.ps1.'))
    }
}

function Add-SchemaDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks,
        [Parameter(Mandatory = $true)][string]$ManifestPath
    )

    $schemaFailed = $false
    $manifestVersion = Get-ManifestPropertyValue -Object $Manifest -Name 'manifestVersion'
    if (-not [string]::IsNullOrWhiteSpace([string]$manifestVersion) -and [string]$manifestVersion -ne '1.0') {
        $schemaFailed = $true
        [void]$Errors.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_SCHEMA_UNSUPPORTED' `
            -Scope 'manifestVersion' `
            -Path $ManifestPath `
            -Message "Unsupported manifestVersion '$manifestVersion'." `
            -Impact 'Only Manifest v1.0 is supported by this Phase 1 validator.' `
            -NextStep "Set manifestVersion to '1.0' or route the package through an explicit legacy flow."))
    }

    $packageType = Get-ManifestPropertyValue -Object $Manifest -Name 'packageType'
    if (-not [string]::IsNullOrWhiteSpace([string]$packageType) -and $script:AllowedPackageTypes -notcontains [string]$packageType) {
        $schemaFailed = $true
        [void]$Errors.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_PACKAGE_TYPE_INVALID' `
            -Scope 'packageType' `
            -Path $ManifestPath `
            -Message "Unsupported packageType '$packageType'." `
            -Impact 'The validator will not silently downgrade unknown package types into another release mode.' `
            -NextStep ('Use one of: ' + ($script:AllowedPackageTypes -join ', ') + '.')))
    }

    if ([string]$packageType -eq 'smart-release' -and -not (Test-ManifestPropertyPresent -Object $Manifest -Name 'baselineManifestId')) {
        $schemaFailed = $true
        [void]$Errors.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_SMART_BASELINE_MISSING' `
            -Scope 'baselineManifestId' `
            -Path $ManifestPath `
            -Message 'smart-release manifest requires baselineManifestId.' `
            -Impact 'A smart release cannot calculate safe deltas without an explicit baseline manifest.' `
            -NextStep 'Add baselineManifestId or change packageType to a non-smart release type.'))
    }

    if (-not $schemaFailed) {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'passed' `
            -Code 'MANIFEST_SCHEMA_CORE_VALID' `
            -Scope 'manifest.schema' `
            -Path $ManifestPath `
            -Message 'Manifest v1 core schema checks passed.' `
            -Impact 'Package type and smart-release baseline requirements are explicit.' `
            -NextStep 'Continue file declaration and forbidden field checks.'))
    } else {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_SCHEMA_UNSUPPORTED' `
            -Scope 'manifest.schema' `
            -Path $ManifestPath `
            -Message 'Manifest v1 core schema checks failed.' `
            -Impact 'The release package cannot be accepted by Smart Release Phase 1 validation.' `
            -NextStep 'Fix the reported schema errors and rerun validation.'))
    }
}

function Add-PackageFileDiagnostics {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $fileFailed = $false
    $declarations = Get-ReleaseManifestDeclarations -Manifest $Manifest
    $declaredLookup = @{}
    foreach ($declaration in $declarations) {
        $declaredLookup[$declaration.relativePath.ToLowerInvariant()] = $true
    }
    foreach ($implicit in $script:ImplicitPackageFiles) {
        $declaredLookup[$implicit.ToLowerInvariant()] = $true
    }

    $packageFiles = @()
    if (Test-Path -LiteralPath $PackagePath -PathType Container) {
        $packageFiles = @(Get-ChildItem -LiteralPath $PackagePath -Recurse -File -Force)
    }

    foreach ($file in $packageFiles) {
        $relativePath = Get-RelativePackagePath -PackagePath $PackagePath -FullPath $file.FullName
        if (-not $declaredLookup.ContainsKey($relativePath.ToLowerInvariant())) {
            $fileFailed = $true
            [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                -Status 'failed' `
                -Code 'PACKAGE_UNDECLARED_FILE' `
                -Scope 'package.files' `
                -Path $relativePath `
                -Message "Package contains undeclared file '$relativePath'." `
                -Impact 'The release package contains bytes that are not covered by manifest intent.' `
                -NextStep 'Declare the file in artifacts, database, or resources, or remove it from the package.'))
        }
    }

    foreach ($declaration in $declarations) {
        $declaredFilePath = Resolve-PackageChildPath -PackagePath $PackagePath -RelativePath $declaration.relativePath
        if (-not (Test-Path -LiteralPath $declaredFilePath -PathType Leaf)) {
            $fileFailed = $true
            [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                -Status 'failed' `
                -Code 'PACKAGE_DECLARED_FILE_MISSING' `
                -Scope $declaration.scope `
                -Path $declaration.relativePath `
                -Message "Manifest declares missing package file '$($declaration.relativePath)'." `
                -Impact 'Deploy precheck cannot prove artifact or payload integrity.' `
                -NextStep 'Add the declared file to the package or remove the declaration.'))
            continue
        }

        if (-not [string]::IsNullOrWhiteSpace([string]$declaration.sha256)) {
            $expected = ([string]$declaration.sha256).ToLowerInvariant()
            if ($expected -notmatch $script:Sha256Pattern) {
                $fileFailed = $true
                [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                    -Status 'failed' `
                    -Code 'PACKAGE_FILE_SHA256_MISMATCH' `
                    -Scope ($declaration.scope -replace '\.path$', '.sha256') `
                    -Path $declaration.relativePath `
                    -Message "Declared sha256 for '$($declaration.relativePath)' is not sha256:<64 hex>." `
                    -Impact 'The validator cannot compare file integrity with an invalid digest format.' `
                    -NextStep 'Recompute and write a sha256:<64 hex> digest for the declared file.'))
                continue
            }

            $actual = Get-ManifestSha256 -Path $declaredFilePath
            if ($actual -ne $expected) {
                $fileFailed = $true
                [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                    -Status 'failed' `
                    -Code 'PACKAGE_FILE_SHA256_MISMATCH' `
                    -Scope ($declaration.scope -replace '\.path$', '.sha256') `
                    -Path $declaration.relativePath `
                    -Message "sha256 mismatch for '$($declaration.relativePath)': expected $expected but got $actual." `
                    -Impact 'The package content differs from manifest integrity metadata.' `
                    -NextStep 'Rebuild the package or update the manifest only after verifying the file content is intended.'))
            }
        }
    }

    if (-not $fileFailed) {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'passed' `
            -Code 'PACKAGE_DECLARATIONS_VALID' `
            -Scope 'package.files' `
            -Path $PackagePath `
            -Message 'Package file declaration and sha256 checks passed.' `
            -Impact 'Every package file is declared and every declared sha256 matched.' `
            -NextStep 'Continue forbidden target and secret scanning.'))
    } else {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'PACKAGE_FILE_VALIDATION_FAILED' `
            -Scope 'package.files' `
            -Path $PackagePath `
            -Message 'Package file declaration or sha256 checks failed.' `
            -Impact 'The package cannot be safely used by Smart Release gates.' `
            -NextStep 'Fix undeclared, missing, or changed files and rerun validation.'))
    }
}

function Add-ForbiddenContentDiagnostics {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)][string]$ManifestPath,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $forbiddenFailed = $false
    foreach ($sectionName in @('targetRequirements', 'deployContract')) {
        $section = Get-ManifestPropertyValue -Object $Manifest -Name $sectionName
        if ($null -eq $section) {
            continue
        }
        $sectionJson = $section | ConvertTo-Json -Depth 20 -Compress
        $sectionIpMatches = [System.Text.RegularExpressions.Regex]::Matches($sectionJson, $script:Ipv4Pattern)
        foreach ($match in $sectionIpMatches) {
            $forbiddenFailed = $true
            [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                -Status 'failed' `
                -Code 'FORBIDDEN_HARDCODED_TARGET_IP' `
                -Scope $sectionName `
                -Path $ManifestPath `
                -Message "Forbidden hardcoded deploy target IP '$($match.Value)' found in manifest $sectionName." `
                -Impact 'Manifest v1 must declare logical target requirements, not concrete server addresses.' `
                -NextStep 'Remove the IP and resolve deployment targets through server-side Runtime Control target config.'))
        }
    }

    $packageFiles = @()
    if (Test-Path -LiteralPath $PackagePath -PathType Container) {
        $packageFiles = @(Get-ChildItem -LiteralPath $PackagePath -Recurse -File -Force)
    }

    foreach ($file in $packageFiles) {
        $extension = [System.IO.Path]::GetExtension($file.Name).ToLowerInvariant()
        if ($script:ScannableExtensions -notcontains $extension) {
            continue
        }

        $relativePath = Get-RelativePackagePath -PackagePath $PackagePath -FullPath $file.FullName
        $content = Read-Utf8File -Path $file.FullName
        if ($relativePath -ne 'manifest.json' -and -not $relativePath.StartsWith('resources/', [System.StringComparison]::OrdinalIgnoreCase)) {
            $ipMatches = [System.Text.RegularExpressions.Regex]::Matches($content, $script:Ipv4Pattern)
            foreach ($match in $ipMatches) {
                $forbiddenFailed = $true
                [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                    -Status 'failed' `
                    -Code 'FORBIDDEN_HARDCODED_TARGET_IP' `
                    -Scope 'forbiddenFieldsCheck.hardcodedIpMatches' `
                    -Path $relativePath `
                    -Message "Forbidden hardcoded deploy target IP '$($match.Value)' found in '$relativePath'." `
                    -Impact 'Release packages must use logical environment requirements, not concrete server addresses.' `
                    -NextStep 'Remove the IP from the package and use server-side Runtime Control target config.'))
            }
        }

        $secretMatches = [System.Text.RegularExpressions.Regex]::Matches($content, $script:SecretPattern)
        foreach ($match in $secretMatches) {
            $forbiddenFailed = $true
            [void]$Errors.Add((New-ReleaseManifestDiagnostic `
                -Status 'failed' `
                -Code 'FORBIDDEN_SECRET_PATTERN' `
                -Scope 'forbiddenFieldsCheck.secretPatternMatches' `
                -Path $relativePath `
                -Message "Forbidden secret-like assignment found in '$relativePath'." `
                -Impact 'Release packages must not embed passwords, tokens, private keys, or endpoint secrets.' `
                -NextStep 'Remove the secret and provide credentials through the approved runtime secret channel.'))
        }
    }

    if (-not $forbiddenFailed) {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'passed' `
            -Code 'FORBIDDEN_CONTENT_SCAN_PASSED' `
            -Scope 'forbiddenFieldsCheck' `
            -Path $PackagePath `
            -Message 'Forbidden target IP and secret scans passed.' `
            -Impact 'No hardcoded target address or secret pattern was detected in manifest-scanned package files.' `
            -NextStep 'Manifest validator has completed.'))
    } else {
        [void]$Checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'FORBIDDEN_CONTENT_SCAN_FAILED' `
            -Scope 'forbiddenFieldsCheck' `
            -Path $PackagePath `
            -Message 'Forbidden target IP or secret scan failed.' `
            -Impact 'The package violates Smart Release target and credential boundaries.' `
            -NextStep 'Remove the reported IP or secret-like values and rerun validation.'))
    }
}

function Invoke-ReleaseManifestValidation {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [ValidateSet('report-only')][string]$Mode = 'report-only'
    )

    $errors = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $checks = New-Object System.Collections.ArrayList
    $packageFullPath = [System.IO.Path]::GetFullPath($PackagePath)
    $manifestPath = Join-Path -Path $packageFullPath -ChildPath 'manifest.json'
    $legacyManifestPath = Join-Path -Path $packageFullPath -ChildPath 'release-manifest.json'

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        if (Test-Path -LiteralPath $legacyManifestPath -PathType Leaf) {
            $warning = New-ReleaseManifestDiagnostic `
                -Status 'warning' `
                -Code 'LEGACY_MANIFEST_V0' `
                -Scope 'manifest' `
                -Path $legacyManifestPath `
                -Message 'Legacy release-manifest.json found without Manifest v1 manifest.json.' `
                -Impact 'Smart Release Phase 1 can report this package but cannot apply v1 integrity and target checks.' `
                -NextStep 'Generate manifest.json v1 for Smart Release validation while keeping legacy release flow explicit.'
            [void]$warnings.Add($warning)
            [void]$checks.Add((New-ReleaseManifestDiagnostic `
                -Status 'warning' `
                -Code 'LEGACY_MANIFEST_V0' `
                -Scope 'manifest.presence' `
                -Path $legacyManifestPath `
                -Message 'Legacy v0 manifest was detected.' `
                -Impact 'Validator stopped before v1 schema checks by design.' `
                -NextStep 'Create manifest.json v1 before relying on Smart Release gates.'))
            return New-ReleaseManifestValidationResult -PackagePath $packageFullPath -Mode $Mode -Errors $errors -Warnings $warnings -Checks $checks
        }

        [void]$errors.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_MISSING' `
            -Scope 'manifest' `
            -Path $packageFullPath `
            -Message 'manifest.json is missing from the release package.' `
            -Impact 'The release package has no Manifest v1 contract to validate.' `
            -NextStep 'Add manifest.json at the package root or explicitly provide a legacy release-manifest.json.'))
        [void]$checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_MISSING' `
            -Scope 'manifest.presence' `
            -Path $packageFullPath `
            -Message 'Manifest v1 file was not found.' `
            -Impact 'Validation cannot continue without manifest.json.' `
            -NextStep 'Create manifest.json and rerun validation.'))
        return New-ReleaseManifestValidationResult -PackagePath $packageFullPath -Mode $Mode -Errors $errors -Warnings $warnings -Checks $checks
    }

    [void]$checks.Add((New-ReleaseManifestDiagnostic `
        -Status 'passed' `
        -Code 'MANIFEST_PRESENT' `
        -Scope 'manifest.presence' `
        -Path $manifestPath `
        -Message 'manifest.json was found.' `
        -Impact 'Manifest JSON parsing can continue.' `
        -NextStep 'Parse Manifest v1 JSON.'))

    $manifestRaw = Read-Utf8File -Path $manifestPath
    try {
        $manifest = $manifestRaw | ConvertFrom-Json -ErrorAction Stop
    } catch {
        [void]$errors.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_JSON_INVALID' `
            -Scope 'manifest.json' `
            -Path $manifestPath `
            -Message ('manifest.json is not valid JSON: ' + $_.Exception.Message) `
            -Impact 'The validator cannot inspect package intent or integrity metadata.' `
            -NextStep 'Fix manifest.json syntax and rerun validation.'))
        [void]$checks.Add((New-ReleaseManifestDiagnostic `
            -Status 'failed' `
            -Code 'MANIFEST_JSON_INVALID' `
            -Scope 'manifest.parse' `
            -Path $manifestPath `
            -Message 'Manifest JSON parsing failed.' `
            -Impact 'Validation stopped before schema and package checks.' `
            -NextStep 'Fix manifest.json syntax.'))
        return New-ReleaseManifestValidationResult -PackagePath $packageFullPath -Mode $Mode -Errors $errors -Warnings $warnings -Checks $checks
    }

    [void]$checks.Add((New-ReleaseManifestDiagnostic `
        -Status 'passed' `
        -Code 'MANIFEST_JSON_VALID' `
        -Scope 'manifest.parse' `
        -Path $manifestPath `
        -Message 'manifest.json parsed successfully.' `
        -Impact 'Schema and package integrity checks can continue.' `
        -NextStep 'Validate Manifest v1 required fields and package type.'))

    Add-RequiredFieldDiagnostics -Manifest $manifest -Errors $errors -Checks $checks -ManifestPath $manifestPath
    Add-SchemaDiagnostics -Manifest $manifest -Errors $errors -Checks $checks -ManifestPath $manifestPath
    Add-PackageFileDiagnostics -PackagePath $packageFullPath -Manifest $manifest -Errors $errors -Checks $checks
    Add-ForbiddenContentDiagnostics -PackagePath $packageFullPath -Manifest $manifest -ManifestPath $manifestPath -Errors $errors -Checks $checks

    return New-ReleaseManifestValidationResult -PackagePath $packageFullPath -Mode $Mode -Errors $errors -Warnings $warnings -Checks $checks
}

Export-ModuleMember -Function Invoke-ReleaseManifestValidation
