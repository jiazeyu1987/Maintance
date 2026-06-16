Set-StrictMode -Version Latest

$script:RequiredModuleFields = @(
    'moduleName',
    'requestedBuildAction',
    'releaseTag',
    'sourceHash',
    'dependencyHash',
    'buildParameterHash',
    'contractHash',
    'artifactHash',
    'artifactPath'
)
$script:ComparableHashFields = @(
    'sourceHash',
    'dependencyHash',
    'buildParameterHash',
    'contractHash'
)
$script:Sha256Pattern = '^sha256:[a-fA-F0-9]{64}$'

function New-BuildModuleDiagnostic {
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

function Get-BuildModuleProperty {
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

function Test-BuildModulePropertyPresent {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $value = Get-BuildModuleProperty -Object $Object -Name $Name
    if ($null -eq $value) {
        return $false
    }
    if (($value -is [string]) -and [string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    return $true
}

function Get-BuildModuleFileSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    return ('sha256:' + (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant())
}

function Write-BuildModulePlanJson {
    param(
        [Parameter(Mandatory = $true)]$Plan,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $json = $Plan | ConvertTo-Json -Depth 20
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function New-BuildModulePlanResult {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$BuildAction,
        [Parameter(Mandatory = $true)]$Manifest,
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)]$Warnings,
        [Parameter(Mandatory = $true)]$Checks,
        [string[]]$RebuildReasons = @(),
        [string]$ArtifactSourceReleaseTag = ''
    )

    return [pscustomobject]([ordered]@{
        status = $Status
        buildAction = $BuildAction
        moduleName = [string](Get-BuildModuleProperty -Object $Manifest -Name 'moduleName')
        releaseTag = [string](Get-BuildModuleProperty -Object $Manifest -Name 'releaseTag')
        artifactSourceReleaseTag = $ArtifactSourceReleaseTag
        rebuildReasons = @($RebuildReasons)
        errors = @($Errors.ToArray())
        warnings = @($Warnings.ToArray())
        checks = @($Checks.ToArray())
        validation = [pscustomobject]([ordered]@{
            hashVerified = ($Status -eq 'passed' -and $BuildAction -eq 'reused')
            manifestVerified = ($Errors.Count -eq 0)
        })
    })
}

function Invoke-BuildModulePlanner {
    param(
        [Parameter(Mandatory = $true)][string]$ModuleManifestPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [ValidateSet('plan-only')][string]$Mode = 'plan-only'
    )

    $errors = New-Object System.Collections.ArrayList
    $warnings = New-Object System.Collections.ArrayList
    $checks = New-Object System.Collections.ArrayList

    if (-not (Test-Path -LiteralPath $ModuleManifestPath -PathType Leaf)) {
        [void]$errors.Add((New-BuildModuleDiagnostic `
            -Status 'blocked' `
            -Code 'BUILD_MODULE_MANIFEST_MISSING' `
            -Scope 'moduleManifest' `
            -Path $ModuleManifestPath `
            -Message 'Build module manifest is missing.' `
            -Impact 'The module cannot be planned or reused without explicit hash inputs.' `
            -NextStep 'Create a build module manifest with all required hash fields.'))
        $plan = New-BuildModulePlanResult -Status 'blocked' -BuildAction 'invalid' -Manifest ([pscustomobject]@{}) -Errors $errors -Warnings $warnings -Checks $checks
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 2 }
    }

    try {
        $manifest = [System.IO.File]::ReadAllText($ModuleManifestPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
    } catch {
        [void]$errors.Add((New-BuildModuleDiagnostic `
            -Status 'failed' `
            -Code 'BUILD_MODULE_MANIFEST_JSON_INVALID' `
            -Scope 'moduleManifest' `
            -Path $ModuleManifestPath `
            -Message ('Build module manifest is not valid JSON: ' + $_.Exception.Message) `
            -Impact 'The module planner cannot inspect hash inputs.' `
            -NextStep 'Fix JSON syntax and rerun the planner.'))
        $plan = New-BuildModulePlanResult -Status 'failed' -BuildAction 'invalid' -Manifest ([pscustomobject]@{}) -Errors $errors -Warnings $warnings -Checks $checks
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 1 }
    }

    foreach ($field in $script:RequiredModuleFields) {
        if (-not (Test-BuildModulePropertyPresent -Object $manifest -Name $field)) {
            [void]$errors.Add((New-BuildModuleDiagnostic `
                -Status 'blocked' `
                -Code 'BUILD_MODULE_REQUIRED_FIELD_MISSING' `
                -Scope $field `
                -Path $ModuleManifestPath `
                -Message "Build module manifest is missing required field '$field'." `
                -Impact 'The planner cannot safely decide rebuild or reuse.' `
                -NextStep "Add '$field' and rerun the planner."))
        }
    }

    foreach ($field in @('sourceHash', 'dependencyHash', 'buildParameterHash', 'contractHash', 'artifactHash')) {
        $value = [string](Get-BuildModuleProperty -Object $manifest -Name $field)
        if (-not [string]::IsNullOrWhiteSpace($value) -and $value -notmatch $script:Sha256Pattern) {
            [void]$errors.Add((New-BuildModuleDiagnostic `
                -Status 'blocked' `
                -Code 'BUILD_MODULE_HASH_INVALID' `
                -Scope $field `
                -Path $ModuleManifestPath `
                -Message "Hash field '$field' is not sha256:<64 hex>." `
                -Impact 'Hash inputs must be reproducible before reuse can be considered.' `
                -NextStep "Recompute '$field' and rerun the planner."))
        }
    }

    if ($errors.Count -gt 0) {
        $plan = New-BuildModulePlanResult -Status 'blocked' -BuildAction 'invalid' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 2 }
    }

    $artifactPath = [string](Get-BuildModuleProperty -Object $manifest -Name 'artifactPath')
    if (-not (Test-Path -LiteralPath $artifactPath -PathType Leaf)) {
        [void]$errors.Add((New-BuildModuleDiagnostic `
            -Status 'blocked' `
            -Code 'BUILD_MODULE_ARTIFACT_MISSING' `
            -Scope 'artifactPath' `
            -Path $artifactPath `
            -Message 'Declared build artifact file is missing.' `
            -Impact 'The module cannot be reused or validated without the artifact bytes.' `
            -NextStep 'Rebuild the module or fix artifactPath.'))
    } elseif ((Get-Item -LiteralPath $artifactPath).Length -eq 0) {
        [void]$errors.Add((New-BuildModuleDiagnostic `
            -Status 'blocked' `
            -Code 'BUILD_MODULE_ARTIFACT_EMPTY' `
            -Scope 'artifactPath' `
            -Path $artifactPath `
            -Message 'Declared build artifact file is empty.' `
            -Impact 'Empty artifacts are never valid release outputs.' `
            -NextStep 'Rebuild the module and rerun the planner.'))
    } else {
        $actualArtifactHash = Get-BuildModuleFileSha256 -Path $artifactPath
        $declaredArtifactHash = ([string](Get-BuildModuleProperty -Object $manifest -Name 'artifactHash')).ToLowerInvariant()
        if ($actualArtifactHash -ne $declaredArtifactHash) {
            [void]$errors.Add((New-BuildModuleDiagnostic `
                -Status 'blocked' `
                -Code 'BUILD_MODULE_ARTIFACT_HASH_MISMATCH' `
                -Scope 'artifactHash' `
                -Path $artifactPath `
                -Message "Artifact hash mismatch: expected $declaredArtifactHash but got $actualArtifactHash." `
                -Impact 'The artifact bytes do not match the module manifest.' `
                -NextStep 'Rebuild the module or correct the manifest only after verifying the artifact content.'))
        } else {
            [void]$checks.Add((New-BuildModuleDiagnostic `
                -Status 'passed' `
                -Code 'BUILD_MODULE_ARTIFACT_HASH_VERIFIED' `
                -Scope 'artifactHash' `
                -Path $artifactPath `
                -Message 'Artifact hash matches the module manifest.' `
                -Impact 'Artifact bytes can be considered for reuse decisions.' `
                -NextStep 'Continue cache input hash comparison.'))
        }
    }

    if ($errors.Count -gt 0) {
        $plan = New-BuildModulePlanResult -Status 'blocked' -BuildAction 'invalid' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 2 }
    }

    $candidate = Get-BuildModuleProperty -Object $manifest -Name 'candidate'
    if ($null -eq $candidate) {
        $plan = New-BuildModulePlanResult -Status 'passed' -BuildAction 'rebuilt' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks -RebuildReasons @('candidateMissing')
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 0 }
    }

    $mismatchedFields = @()
    foreach ($field in $script:ComparableHashFields) {
        $current = [string](Get-BuildModuleProperty -Object $manifest -Name $field)
        $cached = [string](Get-BuildModuleProperty -Object $candidate -Name $field)
        if ([string]::IsNullOrWhiteSpace($cached) -or $current -ne $cached) {
            $mismatchedFields += $field
        }
    }

    $requestedBuildAction = [string](Get-BuildModuleProperty -Object $manifest -Name 'requestedBuildAction')
    if ($mismatchedFields.Count -gt 0) {
        if ($requestedBuildAction -eq 'reused') {
            [void]$errors.Add((New-BuildModuleDiagnostic `
                -Status 'blocked' `
                -Code 'BUILD_MODULE_CACHE_INPUT_HASH_MISMATCH' `
                -Scope 'candidate' `
                -Path $ModuleManifestPath `
                -Message ('Forced artifact reuse is unsafe because these inputs differ: ' + ($mismatchedFields -join ', ') + '.') `
                -Impact 'Reusing this artifact would skip required rebuild after input changes.' `
                -NextStep 'Rebuild the module or provide a candidate with matching source, dependency, build parameter, and contract hashes.'))
            $plan = New-BuildModulePlanResult -Status 'blocked' -BuildAction 'invalid' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks
            Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
            return [pscustomobject]@{ Plan = $plan; ExitCode = 2 }
        }

        $plan = New-BuildModulePlanResult -Status 'passed' -BuildAction 'rebuilt' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks -RebuildReasons $mismatchedFields
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 0 }
    }

    $candidateArtifactHash = [string](Get-BuildModuleProperty -Object $candidate -Name 'artifactHash')
    $declaredManifestArtifactHash = [string](Get-BuildModuleProperty -Object $manifest -Name 'artifactHash')
    if ([string]::IsNullOrWhiteSpace($candidateArtifactHash) -or $candidateArtifactHash -ne $declaredManifestArtifactHash) {
        [void]$errors.Add((New-BuildModuleDiagnostic `
            -Status 'blocked' `
            -Code 'BUILD_MODULE_CACHE_ARTIFACT_HASH_MISMATCH' `
            -Scope 'candidate.artifactHash' `
            -Path $ModuleManifestPath `
            -Message 'Cached candidate artifactHash does not match current module artifactHash.' `
            -Impact 'The candidate artifact cannot be proven identical to the requested artifact.' `
            -NextStep 'Rebuild or select a matching candidate artifact.'))
        $plan = New-BuildModulePlanResult -Status 'blocked' -BuildAction 'invalid' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks
        Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
        return [pscustomobject]@{ Plan = $plan; ExitCode = 2 }
    }

    $candidateReleaseTag = [string](Get-BuildModuleProperty -Object $candidate -Name 'releaseTag')
    $plan = New-BuildModulePlanResult -Status 'passed' -BuildAction 'reused' -Manifest $manifest -Errors $errors -Warnings $warnings -Checks $checks -ArtifactSourceReleaseTag $candidateReleaseTag
    Write-BuildModulePlanJson -Plan $plan -OutputPath $OutputPath
    return [pscustomobject]@{ Plan = $plan; ExitCode = 0 }
}

Export-ModuleMember -Function Invoke-BuildModulePlanner
