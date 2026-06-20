Set-StrictMode -Version Latest

$script:SupportedTargetConfigSchemaVersion = '1.0'
$script:AllowedEnvironments = @('test', 'prod', 'backup')
$script:Sha256Pattern = '^sha256:[a-fA-F0-9]{64}$'
$script:Ipv4Pattern = '(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])'
$script:RequiredTargetConfigFields = @(
    'schemaVersion',
    'targetConfigId',
    'environmentCode',
    'hostRef',
    'dockerProfileId',
    'storageProfileIds',
    'artifactCacheProfiles',
    'remoteReadOnlyProbe'
)

function New-DeployPrecheckDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        status = $Status
        scope = $Scope
        message = $Message
        impact = $Impact
        nextStep = $NextStep
    })
}

function Add-DeployDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Collection,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    [void]$Collection.Add((New-DeployPrecheckDiagnostic `
        -Code $Code `
        -Status $Status `
        -Scope $Scope `
        -Message $Message `
        -Impact $Impact `
        -NextStep $NextStep))
}

function Add-ManifestDiagnosticCopy {
    param(
        [Parameter(Mandatory = $true)]$Collection,
        [Parameter(Mandatory = $true)]$Diagnostic
    )

    Add-DeployDiagnostic `
        -Collection $Collection `
        -Code ([string]$Diagnostic.code) `
        -Status ([string]$Diagnostic.status) `
        -Scope ([string]$Diagnostic.scope) `
        -Message ([string]$Diagnostic.message) `
        -Impact ([string]$Diagnostic.impact) `
        -NextStep ([string]$Diagnostic.nextStep)
}

function Get-ObjectPropertyValue {
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

function Test-PropertyPresent {
    param(
        $Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object) {
        return $false
    }

    $propertyExists = $false
    if ($Object -is [System.Collections.IDictionary]) {
        $propertyExists = $Object.Contains($Name)
    } else {
        $propertyExists = $null -ne $Object.PSObject.Properties[$Name]
    }
    if (-not $propertyExists) {
        return $false
    }

    $value = Get-ObjectPropertyValue -Object $Object -Name $Name
    if (($value -is [string]) -and [string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    return $true
}

function ConvertTo-ObjectArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function ConvertTo-StringArray {
    param($Value)

    $items = @()
    foreach ($item in @(ConvertTo-ObjectArray -Value $Value)) {
        if ($null -ne $item -and -not [string]::IsNullOrWhiteSpace([string]$item)) {
            $items += [string]$item
        }
    }
    return $items
}

function Read-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return [System.IO.File]::ReadAllText($Path, [System.Text.UTF8Encoding]::new($false))
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    $raw = Read-Utf8Text -Path $Path
    return $raw | ConvertFrom-Json -ErrorAction Stop
}

function Get-Sha256Prefixed {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return 'sha256:' + (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Resolve-PackageFilePath {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $combined = [System.IO.Path]::Combine($PackagePath, $RelativePath)
    return [System.IO.Path]::GetFullPath($combined)
}

function Test-PathInsidePackage {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$CandidatePath
    )

    $packageFullPath = [System.IO.Path]::GetFullPath($PackagePath).TrimEnd('\', '/')
    $candidateFullPath = [System.IO.Path]::GetFullPath($CandidatePath)
    $packagePrefix = $packageFullPath + [System.IO.Path]::DirectorySeparatorChar
    return $candidateFullPath.StartsWith($packagePrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-DiagnosticCodePresent {
    param(
        [Parameter(Mandatory = $true)]$Collection,
        [Parameter(Mandatory = $true)][string]$Code
    )

    foreach ($item in @($Collection.ToArray())) {
        if ([string]$item.code -eq $Code) {
            return $true
        }
    }
    return $false
}

function Get-ArtifactCacheProfileId {
    param($ArtifactCacheUri)

    if ($null -eq $ArtifactCacheUri -or [string]::IsNullOrWhiteSpace([string]$ArtifactCacheUri)) {
        return $null
    }

    $cacheUri = [string]$ArtifactCacheUri
    if ($cacheUri -match '^cache://([^/]+)/') {
        return $Matches[1]
    }
    if ($cacheUri -match '^([^:/]+)://') {
        return $Matches[1]
    }
    if ($cacheUri -match '^profile:([^/]+)(?:/|$)') {
        return $Matches[1]
    }
    return $null
}

function Add-ForbiddenTargetSectionDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors
    )

    $sections = @(
        @{ Name = 'targetRequirements'; Value = Get-ObjectPropertyValue -Object $Manifest -Name 'targetRequirements' },
        @{ Name = 'deployContract'; Value = Get-ObjectPropertyValue -Object $Manifest -Name 'deployContract' }
    )

    foreach ($section in $sections) {
        if ($null -eq $section.Value) {
            continue
        }
        $text = $section.Value | ConvertTo-Json -Depth 30 -Compress
        $matches = [regex]::Matches($text, $script:Ipv4Pattern)
        if ($matches.Count -eq 0) {
            continue
        }

        $matchedValues = @()
        foreach ($match in $matches) {
            $matchedValues += $match.Value
        }
        $uniqueMatches = @($matchedValues | Sort-Object -Unique)
        $message = "Manifest $($section.Name) contains concrete target IP value(s): $($uniqueMatches -join ', ')."
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'FORBIDDEN_HARDCODED_TARGET_IP' `
            -Status 'failed' `
            -Scope $section.Name `
            -Message $message `
            -Impact 'Deploy precheck cannot prove logical target compatibility when the package embeds concrete target addresses.' `
            -NextStep 'Remove concrete target addresses from the manifest and bind the target through server-side Runtime Control configuration.'
    }
}

function Add-TargetConfigDiagnostics {
    param(
        [Parameter(Mandatory = $true)][string]$TargetConfigPath,
        [Parameter(Mandatory = $true)][string]$Environment,
        [Parameter(Mandatory = $true)][bool]$EnvironmentValid,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $state = [ordered]@{
        Config = $null
        TargetConfigId = $null
        IsUsable = $false
        Path = $null
    }

    if ([string]::IsNullOrWhiteSpace($TargetConfigPath)) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_TARGET_CONFIG_MISSING' `
            -Status 'failed' `
            -Scope 'TargetConfigPath' `
            -Message 'TargetConfigPath is required for deploy precheck report-only.' `
            -Impact 'The deploy target cannot be resolved from server-side configuration.' `
            -NextStep 'Provide the server-side target config path for the selected logical environment.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_TARGET_CONFIG_MISSING' `
            -Status 'failed' `
            -Scope 'targetConfig.presence' `
            -Message 'Target config path was not provided.' `
            -Impact 'No default target is inferred by deploy precheck.' `
            -NextStep 'Pass -TargetConfigPath and rerun.'
        return [pscustomobject]$state
    }

    $targetConfigFullPath = [System.IO.Path]::GetFullPath($TargetConfigPath)
    $state.Path = $targetConfigFullPath
    if (-not (Test-Path -LiteralPath $targetConfigFullPath -PathType Leaf)) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_TARGET_CONFIG_MISSING' `
            -Status 'failed' `
            -Scope 'TargetConfigPath' `
            -Message "Target config file was not found: $targetConfigFullPath." `
            -Impact 'The deploy target cannot be resolved from server-side configuration.' `
            -NextStep 'Create or select an existing target config for the logical environment.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_TARGET_CONFIG_MISSING' `
            -Status 'failed' `
            -Scope 'targetConfig.presence' `
            -Message 'Target config file is missing.' `
            -Impact 'No default target is inferred by deploy precheck.' `
            -NextStep 'Provide a valid target config file.'
        return [pscustomobject]$state
    }

    try {
        $targetConfig = Read-JsonFile -Path $targetConfigFullPath
        $state.Config = $targetConfig
        $state.TargetConfigId = Get-ObjectPropertyValue -Object $targetConfig -Name 'targetConfigId'
    } catch {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_TARGET_CONFIG_INVALID' `
            -Status 'failed' `
            -Scope 'targetConfig.json' `
            -Message ('Target config JSON is invalid: ' + $_.Exception.Message) `
            -Impact 'Deploy precheck cannot inspect target capabilities.' `
            -NextStep 'Fix the target config JSON syntax and rerun.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_TARGET_CONFIG_INVALID' `
            -Status 'failed' `
            -Scope 'targetConfig.parse' `
            -Message 'Target config JSON parsing failed.' `
            -Impact 'Target capability checks cannot continue.' `
            -NextStep 'Fix JSON syntax in the target config.'
        return [pscustomobject]$state
    }

    $missingFields = @()
    foreach ($field in $script:RequiredTargetConfigFields) {
        if (-not (Test-PropertyPresent -Object $targetConfig -Name $field)) {
            $missingFields += $field
        }
    }
    if ($missingFields.Count -gt 0) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_TARGET_CONFIG_INVALID' `
            -Status 'failed' `
            -Scope 'targetConfig.required' `
            -Message "Target config is missing required field(s): $($missingFields -join ', ')." `
            -Impact 'Deploy precheck cannot determine target capability coverage.' `
            -NextStep 'Add the missing target config fields and rerun.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_TARGET_CONFIG_INVALID' `
            -Status 'failed' `
            -Scope 'targetConfig.required' `
            -Message 'Target config required field validation failed.' `
            -Impact 'Target config capability checks cannot be trusted.' `
            -NextStep 'Fix the target config contract.'
        return [pscustomobject]$state
    }

    $schemaVersion = [string](Get-ObjectPropertyValue -Object $targetConfig -Name 'schemaVersion')
    if ($schemaVersion -ne $script:SupportedTargetConfigSchemaVersion) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_TARGET_CONFIG_SCHEMA_UNSUPPORTED' `
            -Status 'failed' `
            -Scope 'targetConfig.schemaVersion' `
            -Message "Target config schemaVersion '$schemaVersion' is not supported." `
            -Impact 'Deploy precheck cannot rely on an unknown target config contract.' `
            -NextStep "Use schemaVersion '$script:SupportedTargetConfigSchemaVersion' target config."
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_TARGET_CONFIG_SCHEMA_UNSUPPORTED' `
            -Status 'failed' `
            -Scope 'targetConfig.schemaVersion' `
            -Message 'Target config schema version is unsupported.' `
            -Impact 'Target capability checks cannot continue.' `
            -NextStep 'Set target config schemaVersion and rerun.'
        return [pscustomobject]$state
    }

    Add-DeployDiagnostic `
        -Collection $Checks `
        -Code 'DEPLOY_TARGET_CONFIG_VALID' `
        -Status 'passed' `
        -Scope 'targetConfig' `
        -Message 'Target config parsed and matched schemaVersion 1.0.' `
        -Impact 'Deploy precheck can compare manifest target requirements against declared target capabilities.' `
        -NextStep 'Continue deploy precheck report-only target compatibility checks.'

    if ($EnvironmentValid) {
        $targetEnvironment = [string](Get-ObjectPropertyValue -Object $targetConfig -Name 'environmentCode')
        if ($targetEnvironment -ne $Environment) {
            Add-DeployDiagnostic `
                -Collection $Errors `
                -Code 'DEPLOY_TARGET_CONFIG_ENVIRONMENT_MISMATCH' `
                -Status 'failed' `
                -Scope 'targetConfig.environmentCode' `
                -Message "Target config environmentCode '$targetEnvironment' does not match selected environment '$Environment'." `
                -Impact 'The selected logical environment may resolve to the wrong target configuration.' `
                -NextStep 'Select a target config whose environmentCode matches the command environment.'
            Add-DeployDiagnostic `
                -Collection $Checks `
                -Code 'DEPLOY_TARGET_CONFIG_ENVIRONMENT_MISMATCH' `
                -Status 'failed' `
                -Scope 'targetConfig.environmentCode' `
                -Message 'Target config environment mismatch detected.' `
                -Impact 'Target config compatibility failed.' `
                -NextStep 'Use a matching target config.'
        } else {
            Add-DeployDiagnostic `
                -Collection $Checks `
                -Code 'DEPLOY_TARGET_CONFIG_ENVIRONMENT_MATCHED' `
                -Status 'passed' `
                -Scope 'targetConfig.environmentCode' `
                -Message 'Target config environmentCode matches the selected environment.' `
                -Impact 'Deploy precheck can continue with this logical target.' `
                -NextStep 'Continue target requirement checks.'
        }
    }

    $state.IsUsable = $true
    return [pscustomobject]$state
}

function Add-TargetRequirementDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        $TargetConfig,
        [Parameter(Mandatory = $true)][bool]$TargetConfigUsable,
        [Parameter(Mandatory = $true)][string]$Environment,
        [Parameter(Mandatory = $true)][bool]$EnvironmentValid,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $targetRequirements = Get-ObjectPropertyValue -Object $Manifest -Name 'targetRequirements'

    if ($EnvironmentValid) {
        $environmentCodes = @(ConvertTo-StringArray -Value (Get-ObjectPropertyValue -Object $targetRequirements -Name 'environmentCodes'))
        if ($environmentCodes.Count -eq 0 -or $environmentCodes -notcontains $Environment) {
            Add-DeployDiagnostic `
                -Collection $Errors `
                -Code 'DEPLOY_TARGET_REQUIREMENT_MISMATCH' `
                -Status 'failed' `
                -Scope 'targetRequirements.environmentCodes' `
                -Message "Selected environment '$Environment' is not allowed by manifest targetRequirements." `
                -Impact 'The package may be deployed to a target it was not built or verified for.' `
                -NextStep 'Select a compatible target or rebuild the package with matching target requirements.'
            Add-DeployDiagnostic `
                -Collection $Checks `
                -Code 'DEPLOY_TARGET_REQUIREMENT_MISMATCH' `
                -Status 'failed' `
                -Scope 'targetRequirements.environmentCodes' `
                -Message 'Manifest target environment compatibility failed.' `
                -Impact 'The selected target is outside the manifest logical environment contract.' `
                -NextStep 'Use an allowed environment or rebuild the package.'
        } else {
            Add-DeployDiagnostic `
                -Collection $Checks `
                -Code 'DEPLOY_TARGET_REQUIREMENT_MATCHED' `
                -Status 'passed' `
                -Scope 'targetRequirements.environmentCodes' `
                -Message 'Selected environment is allowed by manifest targetRequirements.' `
                -Impact 'The logical environment requirement is satisfied.' `
                -NextStep 'Continue target profile compatibility checks.'
        }
    }

    if (-not $TargetConfigUsable) {
        return
    }

    $requiredDockerProfileId = [string](Get-ObjectPropertyValue -Object $targetRequirements -Name 'dockerProfileId')
    $targetDockerProfileId = [string](Get-ObjectPropertyValue -Object $TargetConfig -Name 'dockerProfileId')
    if ([string]::IsNullOrWhiteSpace($requiredDockerProfileId) -or $requiredDockerProfileId -ne $targetDockerProfileId) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_DOCKER_PROFILE_MISMATCH' `
            -Status 'failed' `
            -Scope 'targetRequirements.dockerProfileId' `
            -Message "Manifest dockerProfileId '$requiredDockerProfileId' is not provided by target config '$targetDockerProfileId'." `
            -Impact 'The target may not run the package with the required container profile.' `
            -NextStep 'Select a target config with the required docker profile or rebuild for the target profile.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_DOCKER_PROFILE_MISMATCH' `
            -Status 'failed' `
            -Scope 'targetRequirements.dockerProfileId' `
            -Message 'Docker profile compatibility failed.' `
            -Impact 'Target container profile is incompatible with the manifest.' `
            -NextStep 'Align dockerProfileId between manifest and target config.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_DOCKER_PROFILE_MATCHED' `
            -Status 'passed' `
            -Scope 'targetRequirements.dockerProfileId' `
            -Message 'Docker profile requirement is covered by target config.' `
            -Impact 'The target declares the required docker profile.' `
            -NextStep 'Continue storage profile checks.'
    }

    $requiredStorageProfiles = @(ConvertTo-StringArray -Value (Get-ObjectPropertyValue -Object $targetRequirements -Name 'storageProfileIds'))
    $targetStorageProfiles = @(ConvertTo-StringArray -Value (Get-ObjectPropertyValue -Object $TargetConfig -Name 'storageProfileIds'))
    $missingStorageProfiles = @()
    foreach ($profileId in $requiredStorageProfiles) {
        if ($targetStorageProfiles -notcontains $profileId) {
            $missingStorageProfiles += $profileId
        }
    }

    if ($missingStorageProfiles.Count -gt 0) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_STORAGE_PROFILE_MISMATCH' `
            -Status 'failed' `
            -Scope 'targetRequirements.storageProfileIds' `
            -Message "Target config does not cover required storage profile(s): $($missingStorageProfiles -join ', ')." `
            -Impact 'Resource references may resolve against the wrong storage capability.' `
            -NextStep 'Select a target config that declares all required storage profiles.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_STORAGE_PROFILE_MISMATCH' `
            -Status 'failed' `
            -Scope 'targetRequirements.storageProfileIds' `
            -Message 'Storage profile compatibility failed.' `
            -Impact 'Target storage profile coverage is incomplete.' `
            -NextStep 'Align storageProfileIds between manifest and target config.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_STORAGE_PROFILE_MATCHED' `
            -Status 'passed' `
            -Scope 'targetRequirements.storageProfileIds' `
            -Message 'All required storage profiles are covered by target config.' `
            -Impact 'Resource references can be evaluated against declared target storage profiles.' `
            -NextStep 'Continue artifact checks.'
    }
}

function Add-ArtifactDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)][string]$PackagePath,
        $TargetConfig,
        [Parameter(Mandatory = $true)][bool]$TargetConfigUsable,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $errorCountBefore = $Errors.Count
    $artifacts = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -Object $Manifest -Name 'artifacts'))
    $targetCacheProfiles = @()
    if ($TargetConfigUsable) {
        $targetCacheProfiles = @(ConvertTo-StringArray -Value (Get-ObjectPropertyValue -Object $TargetConfig -Name 'artifactCacheProfiles'))
    }

    for ($index = 0; $index -lt $artifacts.Count; $index++) {
        $artifact = $artifacts[$index]
        $artifactId = [string](Get-ObjectPropertyValue -Object $artifact -Name 'artifactId')
        $includedInPackage = Get-ObjectPropertyValue -Object $artifact -Name 'includedInPackage'
        $artifactPath = [string](Get-ObjectPropertyValue -Object $artifact -Name 'path')

        if ($includedInPackage -eq $true) {
            if ([string]::IsNullOrWhiteSpace($artifactPath)) {
                Add-DeployDiagnostic `
                    -Collection $Errors `
                    -Code 'DEPLOY_ARTIFACT_MISSING' `
                    -Status 'failed' `
                    -Scope "artifacts[$index].path" `
                    -Message "Artifact '$artifactId' is included in package but has no path." `
                    -Impact 'Deploy precheck cannot locate the package artifact.' `
                    -NextStep 'Declare the package artifact path and rebuild the package.'
                continue
            }

            $artifactFullPath = Resolve-PackageFilePath -PackagePath $PackagePath -RelativePath $artifactPath
            if (-not (Test-Path -LiteralPath $artifactFullPath -PathType Leaf)) {
                Add-DeployDiagnostic `
                    -Collection $Errors `
                    -Code 'DEPLOY_ARTIFACT_MISSING' `
                    -Status 'failed' `
                    -Scope "artifacts[$index].path" `
                    -Message "Declared artifact '$artifactPath' was not found in the package." `
                    -Impact 'Deploy precheck cannot verify artifact integrity before deploy.' `
                    -NextStep 'Rebuild the package or restore the declared artifact file.'
                continue
            }

            $expectedSha256 = ([string](Get-ObjectPropertyValue -Object $artifact -Name 'sha256')).ToLowerInvariant()
            $actualSha256 = Get-Sha256Prefixed -Path $artifactFullPath
            if ($expectedSha256 -notmatch $script:Sha256Pattern -or $expectedSha256 -ne $actualSha256) {
                Add-DeployDiagnostic `
                    -Collection $Errors `
                    -Code 'DEPLOY_ARTIFACT_SHA256_MISMATCH' `
                    -Status 'failed' `
                    -Scope "artifacts[$index].sha256" `
                    -Message "Artifact '$artifactPath' sha256 mismatch: expected $expectedSha256 but got $actualSha256." `
                    -Impact 'The package artifact content does not match manifest integrity metadata.' `
                    -NextStep 'Rebuild the package or correct the manifest sha256 after verifying artifact content.'
            }
        } elseif ($includedInPackage -eq $false) {
            $cacheProfileId = Get-ArtifactCacheProfileId -ArtifactCacheUri (Get-ObjectPropertyValue -Object $artifact -Name 'artifactCacheUri')
            if ([string]::IsNullOrWhiteSpace($cacheProfileId) -or -not $TargetConfigUsable -or $targetCacheProfiles -notcontains $cacheProfileId) {
                Add-DeployDiagnostic `
                    -Collection $Errors `
                    -Code 'DEPLOY_ARTIFACT_CACHE_UNAVAILABLE' `
                    -Status 'failed' `
                    -Scope "artifacts[$index].artifactCacheUri" `
                    -Message "Artifact '$artifactId' is not included in package and cache profile is not available to the target." `
                    -Impact 'Deploy precheck cannot prove the target can resolve the smart-release artifact cache.' `
                    -NextStep 'Include the artifact in the package or select a target config with the required artifact cache profile.'
            }
        }
    }

    if ($Errors.Count -eq $errorCountBefore) {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_ARTIFACTS_VERIFIED' `
            -Status 'passed' `
            -Scope 'artifacts' `
            -Message 'Artifact presence, package sha256, and cache profile checks passed.' `
            -Impact 'Package artifact integrity is verified locally for report-only precheck.' `
            -NextStep 'Continue resource and plan checks.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_ARTIFACTS_VERIFIED' `
            -Status 'failed' `
            -Scope 'artifacts' `
            -Message 'Artifact checks found one or more deploy precheck failures.' `
            -Impact 'Deploy precheck cannot mark artifact integrity as passed.' `
            -NextStep 'Fix artifact declarations, package files, or cache profile bindings.'
    }
}

function Add-DatabasePlanDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $targetRequirements = Get-ObjectPropertyValue -Object $Manifest -Name 'targetRequirements'
    $database = Get-ObjectPropertyValue -Object $Manifest -Name 'database'
    $schemaMigrations = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -Object $database -Name 'schemaMigrations'))
    $requiredDataSets = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -Object $database -Name 'requiredDataSets'))

    if ((Get-ObjectPropertyValue -Object $targetRequirements -Name 'requiresDatabaseMigrationPrecheck') -eq $true -and $schemaMigrations.Count -eq 0) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_SCHEMA_PLAN_MISSING' `
            -Status 'failed' `
            -Scope 'database.schemaMigrations' `
            -Message 'Manifest requires database migration precheck but schemaMigrations is empty.' `
            -Impact 'Deploy precheck cannot prove schema plan completeness before deploy.' `
            -NextStep 'Add the schema migration plan to the manifest or set the requirement to false when no schema change exists.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_SCHEMA_PLAN_VERIFIED' `
            -Status 'passed' `
            -Scope 'database.schemaMigrations' `
            -Message 'Schema migration precheck plan is complete for Phase 1 report-only.' `
            -Impact 'No database statements are executed by this precheck.' `
            -NextStep 'Continue required data plan checks.'
    }

    if ((Get-ObjectPropertyValue -Object $targetRequirements -Name 'requiresRequiredDataPrecheck') -eq $true -and $requiredDataSets.Count -eq 0) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_REQUIRED_DATA_PLAN_MISSING' `
            -Status 'failed' `
            -Scope 'database.requiredDataSets' `
            -Message 'Manifest requires required-data precheck but requiredDataSets is empty.' `
            -Impact 'Deploy precheck cannot prove required data plan completeness before deploy.' `
            -NextStep 'Add the required data set plan to the manifest or set the requirement to false when no data change exists.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_REQUIRED_DATA_PLAN_VERIFIED' `
            -Status 'passed' `
            -Scope 'database.requiredDataSets' `
            -Message 'Required data precheck plan is complete for Phase 1 report-only.' `
            -Impact 'No database statements are executed by this precheck.' `
            -NextStep 'Continue resource checks.'
    }
}

function Add-ResourceDeltaProofDiagnostics {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$ResourceDeltaProofPath,
        [Parameter(Mandatory = $true)]$Errors
    )

    $resourceDeltaProofFullPath = Resolve-PackageFilePath -PackagePath $PackagePath -RelativePath $ResourceDeltaProofPath
    if (-not (Test-PathInsidePackage -PackagePath $PackagePath -CandidatePath $resourceDeltaProofFullPath)) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_PROOF_OUTSIDE_PACKAGE' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof path '$ResourceDeltaProofPath' resolves outside the package." `
            -Impact 'Deploy precheck cannot trust a resource proof file outside the immutable package boundary.' `
            -NextStep 'Regenerate the package with resourceDeltaProofPath pointing to a file inside the package.'
        return
    }

    if (-not (Test-Path -LiteralPath $resourceDeltaProofFullPath -PathType Leaf)) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_PROOF_MISSING' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof '$ResourceDeltaProofPath' was not found in the package." `
            -Impact 'Deploy precheck cannot verify resource delta readiness before deployment.' `
            -NextStep 'Include the verified resource delta proof JSON in the package.'
        return
    }

    try {
        $proof = Read-JsonFile -Path $resourceDeltaProofFullPath
    } catch {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_PROOF_INVALID' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof '$ResourceDeltaProofPath' is not valid JSON: $($_.Exception.Message)" `
            -Impact 'Deploy precheck cannot inspect resource delta proof content.' `
            -NextStep 'Regenerate resource delta proof JSON and include it in the package.'
        return
    }

    $proofStatus = [string](Get-ObjectPropertyValue -Object $proof -Name 'status')
    $summary = Get-ObjectPropertyValue -Object $proof -Name 'summary'
    if ([string]::IsNullOrWhiteSpace($proofStatus) -or $null -eq $summary) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_PROOF_INVALID' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof '$ResourceDeltaProofPath' must include status and summary." `
            -Impact 'Deploy precheck cannot determine whether the resource delta was verified.' `
            -NextStep 'Regenerate the proof with status, summary, and object counts.'
        return
    }

    $proofErrors = @(ConvertTo-ObjectArray -Value (Get-ObjectPropertyValue -Object $proof -Name 'errors'))
    $conflictCount = [int](Get-ObjectPropertyValue -Object $summary -Name 'conflictObjects')
    if ($proofStatus -eq 'failed' -or $conflictCount -gt 0 -or $proofErrors.Count -gt 0) {
        $proofErrorCodes = @()
        foreach ($proofError in $proofErrors) {
            $proofErrorCode = [string](Get-ObjectPropertyValue -Object $proofError -Name 'code')
            if (-not [string]::IsNullOrWhiteSpace($proofErrorCode)) {
                $proofErrorCodes += $proofErrorCode
            }
        }
        $detail = $(if ($proofErrorCodes.Count -gt 0) { " Proof errors: $($proofErrorCodes -join ', ')." } else { '' })
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_PROOF_FAILED' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof '$ResourceDeltaProofPath' is failed or contains conflicts.$detail" `
            -Impact 'Deploy precheck cannot safely deploy while resource delta conflicts are unresolved.' `
            -NextStep 'Resolve conflictObjects, regenerate a verified proof, and rerun deploy precheck.'
        return
    }

    if ($proofStatus -ne 'completed_verified') {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_NOT_VERIFIED' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProofPath' `
            -Message "Resource delta proof '$ResourceDeltaProofPath' status is '$proofStatus'; only completed_verified is accepted for deployment." `
            -Impact 'A plan-only or generated proof does not prove target resources are present and verified.' `
            -NextStep 'Run the resource delta execution and readback verification stage, then include a completed_verified proof.'
        return
    }
}

function Add-ResourceDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Checks
    )

    $errorCountBefore = $Errors.Count
    $targetRequirements = Get-ObjectPropertyValue -Object $Manifest -Name 'targetRequirements'
    $resources = Get-ObjectPropertyValue -Object $Manifest -Name 'resources'
    $resourceReferenceManifest = [string](Get-ObjectPropertyValue -Object $resources -Name 'resourceReferenceManifest')
    if ([string]::IsNullOrWhiteSpace($resourceReferenceManifest)) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_REFERENCE_MISSING' `
            -Status 'failed' `
            -Scope 'resources.resourceReferenceManifest' `
            -Message 'Manifest resources.resourceReferenceManifest is required for deploy precheck.' `
            -Impact 'Deploy precheck cannot inspect resource reference readiness.' `
            -NextStep 'Generate resource-reference-manifest.json during release intake and include it in the package.'
    } else {
        $resourceReferenceFullPath = Resolve-PackageFilePath -PackagePath $PackagePath -RelativePath $resourceReferenceManifest
        if (-not (Test-Path -LiteralPath $resourceReferenceFullPath -PathType Leaf)) {
            Add-DeployDiagnostic `
                -Collection $Errors `
                -Code 'DEPLOY_RESOURCE_REFERENCE_MISSING' `
                -Status 'failed' `
                -Scope 'resources.resourceReferenceManifest' `
                -Message "Resource reference manifest '$resourceReferenceManifest' was not found in the package." `
                -Impact 'Deploy precheck cannot inspect resource reference readiness.' `
                -NextStep 'Include the resource reference manifest in the package.'
        }
    }

    $requiresResourceDeltaProof = (Get-ObjectPropertyValue -Object $targetRequirements -Name 'requiresResourceDeltaProof') -eq $true
    $resourceDeltaPrepared = (Get-ObjectPropertyValue -Object $resources -Name 'resourceDeltaPrepared') -eq $true
    $resourceDeltaProofPath = [string](Get-ObjectPropertyValue -Object $resources -Name 'resourceDeltaProofPath')
    $needsResourceDeltaProof = $requiresResourceDeltaProof -or $resourceDeltaPrepared
    if ($needsResourceDeltaProof -and (-not $resourceDeltaPrepared -or [string]::IsNullOrWhiteSpace($resourceDeltaProofPath))) {
        Add-DeployDiagnostic `
            -Collection $Errors `
            -Code 'DEPLOY_RESOURCE_DELTA_NOT_VERIFIED' `
            -Status 'failed' `
            -Scope 'resources.resourceDeltaProof' `
            -Message 'Resource delta proof is required or marked prepared, but no verified delta or snapshot proof is declared.' `
            -Impact 'Deploy precheck cannot prove resource reference changes are ready for the selected target profile.' `
            -NextStep 'Provide resourceDeltaId, resourceDeltaProofPath, or resourceSnapshotId before relying on resource delta deployment.'
    }
    if ($needsResourceDeltaProof -and $resourceDeltaPrepared -and -not [string]::IsNullOrWhiteSpace($resourceDeltaProofPath)) {
        Add-ResourceDeltaProofDiagnostics `
            -PackagePath $PackagePath `
            -ResourceDeltaProofPath $resourceDeltaProofPath `
            -Errors $Errors
    }

    if ($Errors.Count -eq $errorCountBefore) {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_RESOURCE_GATE_VERIFIED' `
            -Status 'passed' `
            -Scope 'resources' `
            -Message 'Resource reference and delta proof checks passed for Phase 1 report-only.' `
            -Impact 'No object storage synchronization is performed by this precheck.' `
            -NextStep 'Continue deploy report review.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_RESOURCE_GATE_VERIFIED' `
            -Status 'failed' `
            -Scope 'resources' `
            -Message 'Resource checks found one or more deploy precheck failures.' `
            -Impact 'Resource readiness cannot be marked as passed.' `
            -NextStep 'Fix resource reference or delta proof declarations.'
    }
}

function Add-RemoteProbeDiagnostics {
    param(
        $TargetConfig,
        [Parameter(Mandatory = $true)][bool]$TargetConfigUsable,
        [Parameter(Mandatory = $true)]$Warnings,
        [Parameter(Mandatory = $true)]$Checks
    )

    if (-not $TargetConfigUsable) {
        return
    }

    $probe = Get-ObjectPropertyValue -Object $TargetConfig -Name 'remoteReadOnlyProbe'
    $probeEnabled = (Get-ObjectPropertyValue -Object $probe -Name 'enabled') -eq $true
    $authorizationRef = [string](Get-ObjectPropertyValue -Object $probe -Name 'authorizationRef')
    if ($probeEnabled -and [string]::IsNullOrWhiteSpace($authorizationRef)) {
        Add-DeployDiagnostic `
            -Collection $Warnings `
            -Code 'DEPLOY_REMOTE_READONLY_PROBE_NOT_AUTHORIZED' `
            -Status 'warning' `
            -Scope 'targetConfig.remoteReadOnlyProbe' `
            -Message 'Remote read-only probe is enabled but no authorizationRef is declared.' `
            -Impact 'Phase 1 report-only will not perform remote probing without explicit authorization.' `
            -NextStep 'Disable the probe or bind an authorizationRef before enabling remote read-only probes.'
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_REMOTE_READONLY_PROBE_NOT_AUTHORIZED' `
            -Status 'warning' `
            -Scope 'targetConfig.remoteReadOnlyProbe' `
            -Message 'Remote read-only probe authorization is missing.' `
            -Impact 'Remote probing is not attempted by report-only precheck.' `
            -NextStep 'Bind authorization before using remote probes.'
    } else {
        Add-DeployDiagnostic `
            -Collection $Checks `
            -Code 'DEPLOY_REMOTE_MUTATION_DISABLED' `
            -Status 'passed' `
            -Scope 'deployContract.allowsRemoteMutation' `
            -Message 'Deploy precheck report-only performs no remote mutation.' `
            -Impact 'The tool only writes the local deploy-precheck-result.json report.' `
            -NextStep 'Review the local report before invoking any deploy-release path.'
    }
}

function New-DeployPrecheckResult {
    param(
        [Parameter(Mandatory = $true)][string]$Mode,
        [Parameter(Mandatory = $true)][string]$Environment,
        $PackageId,
        $ManifestVersion,
        $TargetConfigId,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Warnings,
        [Parameter(Mandatory = $true)]$Checks
    )

    if ($Errors.Count -gt 0) {
        $status = 'failed'
    } elseif ($Warnings.Count -gt 0) {
        $status = 'warning'
    } else {
        $status = 'passed'
    }

    return [pscustomobject]([ordered]@{
        status = $status
        mode = $Mode
        deployBehavior = 'deploy-release'
        packageId = $PackageId
        manifestVersion = $ManifestVersion
        environment = $Environment
        targetConfigId = $TargetConfigId
        checkedAt = (Get-Date).ToUniversalTime().ToString('o')
        changesDeployExitCode = $false
        errors = @($Errors.ToArray())
        warnings = @($Warnings.ToArray())
        checks = @($Checks.ToArray())
    })
}

function Invoke-DeployPrecheckReport {
    param(
        [Parameter(Mandatory = $true)][string]$PackagePath,
        [Parameter(Mandatory = $true)][string]$Environment,
        [Parameter(Mandatory = $true)][string]$TargetConfigPath,
        [ValidateSet('report-only')][string]$Mode = 'report-only'
    )

    $errors = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $checks = New-Object System.Collections.ArrayList
    $packageId = $null
    $manifestVersion = $null
    $environmentValue = $Environment

    $packageFullPath = [System.IO.Path]::GetFullPath($PackagePath)
    $environmentValid = $script:AllowedEnvironments -contains $environmentValue
    if (-not $environmentValid) {
        Add-DeployDiagnostic `
            -Collection $errors `
            -Code 'DEPLOY_ENVIRONMENT_INVALID' `
            -Status 'failed' `
            -Scope 'Environment' `
            -Message "Environment '$environmentValue' is not supported." `
            -Impact 'Deploy precheck cannot map the selected environment to a logical target.' `
            -NextStep "Use one of: $($script:AllowedEnvironments -join ', ')."
        Add-DeployDiagnostic `
            -Collection $checks `
            -Code 'DEPLOY_ENVIRONMENT_INVALID' `
            -Status 'failed' `
            -Scope 'Environment' `
            -Message 'Command environment validation failed.' `
            -Impact 'Target compatibility checks may be incomplete.' `
            -NextStep 'Rerun with a supported logical environment.'
    } else {
        Add-DeployDiagnostic `
            -Collection $checks `
            -Code 'DEPLOY_ENVIRONMENT_VALID' `
            -Status 'passed' `
            -Scope 'Environment' `
            -Message 'Command environment is supported.' `
            -Impact 'Deploy precheck can evaluate logical target compatibility.' `
            -NextStep 'Continue target config checks.'
    }

    $targetState = Add-TargetConfigDiagnostics `
        -TargetConfigPath $TargetConfigPath `
        -Environment $environmentValue `
        -EnvironmentValid $environmentValid `
        -Errors $errors `
        -Checks $checks
    $targetConfig = $targetState.Config
    $targetConfigId = $targetState.TargetConfigId

    $validatorPath = Join-Path -Path $PSScriptRoot -ChildPath 'ReleaseManifestValidator.psm1'
    Import-Module -Name $validatorPath -Force
    $manifestValidation = Invoke-ReleaseManifestValidation -PackagePath $packageFullPath -Mode $Mode
    foreach ($check in @($manifestValidation.checks)) {
        Add-ManifestDiagnosticCopy -Collection $checks -Diagnostic $check
    }
    foreach ($warning in @($manifestValidation.warnings)) {
        Add-ManifestDiagnosticCopy -Collection $warnings -Diagnostic $warning
    }
    foreach ($error in @($manifestValidation.errors)) {
        Add-ManifestDiagnosticCopy -Collection $errors -Diagnostic $error
    }

    $manifestPath = Join-Path -Path $packageFullPath -ChildPath 'manifest.json'
    $legacyManifestPath = Join-Path -Path $packageFullPath -ChildPath 'release-manifest.json'
    $manifest = $null
    if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
        try {
            $manifest = Read-JsonFile -Path $manifestPath
            $packageId = Get-ObjectPropertyValue -Object $manifest -Name 'packageId'
            $manifestVersion = Get-ObjectPropertyValue -Object $manifest -Name 'manifestVersion'
        } catch {
            return New-DeployPrecheckResult `
                -Mode $Mode `
                -Environment $environmentValue `
                -PackageId $packageId `
                -ManifestVersion $manifestVersion `
                -TargetConfigId $targetConfigId `
                -Errors $errors `
                -Warnings $warnings `
                -Checks $checks
        }
    } elseif (Test-Path -LiteralPath $legacyManifestPath -PathType Leaf) {
        try {
            $legacyManifest = Read-JsonFile -Path $legacyManifestPath
            $packageId = Get-ObjectPropertyValue -Object $legacyManifest -Name 'packageId'
        } catch {
            $packageId = $null
        }
        $manifestVersion = 'legacy-v0'
        Add-DeployDiagnostic `
            -Collection $warnings `
            -Code 'LEGACY_DEPLOY_PRECHECK_REPORT_ONLY' `
            -Status 'warning' `
            -Scope 'manifest' `
            -Message 'Legacy release package detected; Manifest v1 deploy precheck checks are not available.' `
            -Impact 'Smart Release Phase 1 can only report legacy package status and target config checks.' `
            -NextStep 'Generate Manifest v1 before relying on Smart Release deploy precheck gates.'
        Add-DeployDiagnostic `
            -Collection $checks `
            -Code 'LEGACY_DEPLOY_PRECHECK_REPORT_ONLY' `
            -Status 'warning' `
            -Scope 'manifest' `
            -Message 'Legacy package warning was recorded.' `
            -Impact 'V1 artifact, resource, and target requirement checks were skipped by design.' `
            -NextStep 'Create manifest.json v1 for full deploy precheck coverage.'
        Add-RemoteProbeDiagnostics -TargetConfig $targetConfig -TargetConfigUsable ([bool]$targetState.IsUsable) -Warnings $warnings -Checks $checks
        return New-DeployPrecheckResult `
            -Mode $Mode `
            -Environment $environmentValue `
            -PackageId $packageId `
            -ManifestVersion $manifestVersion `
            -TargetConfigId $targetConfigId `
            -Errors $errors `
            -Warnings $warnings `
            -Checks $checks
    } else {
        return New-DeployPrecheckResult `
            -Mode $Mode `
            -Environment $environmentValue `
            -PackageId $packageId `
            -ManifestVersion $manifestVersion `
            -TargetConfigId $targetConfigId `
            -Errors $errors `
            -Warnings $warnings `
            -Checks $checks
    }

    Add-ForbiddenTargetSectionDiagnostics -Manifest $manifest -Errors $errors
    Add-TargetRequirementDiagnostics `
        -Manifest $manifest `
        -TargetConfig $targetConfig `
        -TargetConfigUsable ([bool]$targetState.IsUsable) `
        -Environment $environmentValue `
        -EnvironmentValid $environmentValid `
        -Errors $errors `
        -Checks $checks
    Add-ArtifactDiagnostics `
        -Manifest $manifest `
        -PackagePath $packageFullPath `
        -TargetConfig $targetConfig `
        -TargetConfigUsable ([bool]$targetState.IsUsable) `
        -Errors $errors `
        -Checks $checks
    Add-DatabasePlanDiagnostics -Manifest $manifest -Errors $errors -Checks $checks
    Add-ResourceDiagnostics -Manifest $manifest -PackagePath $packageFullPath -Errors $errors -Checks $checks
    Add-RemoteProbeDiagnostics -TargetConfig $targetConfig -TargetConfigUsable ([bool]$targetState.IsUsable) -Warnings $warnings -Checks $checks

    return New-DeployPrecheckResult `
        -Mode $Mode `
        -Environment $environmentValue `
        -PackageId $packageId `
        -ManifestVersion $manifestVersion `
        -TargetConfigId $targetConfigId `
        -Errors $errors `
        -Warnings $warnings `
        -Checks $checks
}

Export-ModuleMember -Function Invoke-DeployPrecheckReport
