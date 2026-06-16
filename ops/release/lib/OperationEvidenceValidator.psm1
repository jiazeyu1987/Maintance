Set-StrictMode -Version Latest

function Get-EvidenceProperty {
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

function ConvertTo-EvidenceArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Read-EvidenceJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-EvidenceJson {
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

function Test-EvidenceValueMissing {
    param($Value)

    if ($null -eq $Value) {
        return $true
    }
    if ($Value -is [string]) {
        return [string]::IsNullOrWhiteSpace($Value)
    }
    if ($Value -is [System.Array]) {
        return $Value.Count -eq 0
    }
    return $false
}

function New-EvidenceDiagnostic {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$RequiredResolution
    )

    return [pscustomobject]([ordered]@{
        code = $Code
        scope = $Scope
        message = $Message
        impact = $Impact
        requiredResolution = $RequiredResolution
    })
}

function Get-DefaultRequiredOperationIds {
    param([Parameter(Mandatory = $true)][string]$Gate)

    switch ($Gate) {
        'build' {
            return @('validate-release-manifest', 'build-backend', 'build-admin-frontend', 'package-manifest')
        }
        'publish' {
            return @('validate-release-manifest', 'schema-preflight', 'deploy-backend', 'deploy-admin-frontend', 'health-check')
        }
        'backup' {
            return @('validate-target-environment', 'mysql-backup', 'object-inventory', 'dcc-backup-manifest', 'checksums')
        }
        'restore' {
            return @('validate-backup-manifest', 'restore-database', 'restore-dcc-objects', 'restore-health-check')
        }
        'rollback' {
            return @('validate-release-manifest', 'rollback-preflight', 'switch-program-version', 'health-check')
        }
        default {
            return @()
        }
    }
}

function Get-RequiredOperationIds {
    param(
        [Parameter(Mandatory = $true)]$Evidence,
        [Parameter(Mandatory = $true)][string]$Gate
    )

    $declared = ConvertTo-EvidenceArray -Value (Get-EvidenceProperty -Object $Evidence -Name 'requiredOperationIds')
    if (@($declared).Count -gt 0) {
        return @($declared | ForEach-Object { [string]$_ })
    }
    return Get-DefaultRequiredOperationIds -Gate $Gate
}

function Get-OperationById {
    param(
        [Parameter(Mandatory = $true)]$Operations,
        [Parameter(Mandatory = $true)][string]$OperationId
    )

    foreach ($operation in $Operations) {
        if ([string](Get-EvidenceProperty -Object $operation -Name 'id') -eq $OperationId) {
            return $operation
        }
    }
    return $null
}

function Test-SuccessStatus {
    param([string]$Status)

    return @('success', 'pass', 'passed') -contains $Status.ToLowerInvariant()
}

function Test-FailedStatus {
    param([string]$Status)

    return @('failed', 'fail', 'blocked') -contains $Status.ToLowerInvariant()
}

function Test-ExistingLogPath {
    param([string]$LogPath)

    if ([string]::IsNullOrWhiteSpace($LogPath)) {
        return $false
    }
    return [System.IO.File]::Exists($LogPath)
}

function Add-LogPathDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Scope,
        [string]$LogPath
    )

    [void]$Errors.Add((New-EvidenceDiagnostic `
        -Code 'EVIDENCE_LOG_MISSING' `
        -Scope $Scope `
        -Message "Operation evidence logPath is missing or does not exist: $LogPath" `
        -Impact 'The operation cannot be audited, so the gate cannot prove what actually happened.' `
        -RequiredResolution 'Attach the real operation log path, keep the file available, and rerun evidence validation.'))
}

function Test-ProdAuthorization {
    param($Evidence, [Parameter(Mandatory = $true)][string]$Gate)

    $authorization = Get-EvidenceProperty -Object $Evidence -Name 'userAuthorization'
    if ($null -eq $authorization) {
        return $false
    }
    $approved = Get-EvidenceProperty -Object $authorization -Name 'approved'
    $scope = [string](Get-EvidenceProperty -Object $authorization -Name 'scope')
    $approvedAt = [string](Get-EvidenceProperty -Object $authorization -Name 'approvedAt')
    $approvedBy = [string](Get-EvidenceProperty -Object $authorization -Name 'approvedBy')
    return $approved -eq $true -and $scope -eq $Gate -and -not [string]::IsNullOrWhiteSpace($approvedAt) -and -not [string]::IsNullOrWhiteSpace($approvedBy)
}

function Invoke-OperationEvidenceValidation {
    param(
        [Parameter(Mandatory = $true)][string]$OperationEvidencePath,
        [Parameter(Mandatory = $true)][ValidateSet('build', 'publish', 'backup', 'restore', 'rollback')][string]$Gate,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    try {
        $evidence = Read-EvidenceJson -Path $OperationEvidencePath
    } catch {
        $payload = [pscustomobject]([ordered]@{
            operationId = ''
            gate = $Gate
            targetEnvironment = ''
            status = 'failed'
            finalHealthStatus = ''
            checkedAt = (Get-Date).ToString('o')
            errors = @((New-EvidenceDiagnostic `
                -Code 'OPERATION_EVIDENCE_INPUT_INVALID' `
                -Scope 'input' `
                -Message ([string]$_.Exception.Message) `
                -Impact 'The operation evidence cannot be parsed, so the gate cannot audit the operation sequence.' `
                -RequiredResolution 'Fix the evidence path and JSON syntax, then rerun validation.'))
        })
        Write-EvidenceJson -Payload $payload -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $payload; ExitCode = 1 }
    }

    $errors = New-Object System.Collections.ArrayList
    $operationId = [string](Get-EvidenceProperty -Object $evidence -Name 'operationId')
    $targetEnvironment = [string](Get-EvidenceProperty -Object $evidence -Name 'targetEnvironment')
    $evidenceGate = [string](Get-EvidenceProperty -Object $evidence -Name 'gate')
    $operations = ConvertTo-EvidenceArray -Value (Get-EvidenceProperty -Object $evidence -Name 'operations')
    $requiredOperationIds = Get-RequiredOperationIds -Evidence $evidence -Gate $Gate

    if ([string]::IsNullOrWhiteSpace($operationId)) {
        [void]$errors.Add((New-EvidenceDiagnostic `
            -Code 'OPERATION_ID_MISSING' `
            -Scope 'operationId' `
            -Message 'operationId is required.' `
            -Impact 'The evidence cannot be tied to a concrete build, publish, backup, restore, or rollback operation.' `
            -RequiredResolution 'Regenerate operation evidence with the real operationId.'))
    }

    if (-not [string]::IsNullOrWhiteSpace($evidenceGate) -and $evidenceGate -ne $Gate) {
        [void]$errors.Add((New-EvidenceDiagnostic `
            -Code 'GATE_MISMATCH' `
            -Scope 'gate' `
            -Message "Evidence gate $evidenceGate does not match requested gate $Gate." `
            -Impact 'The evidence may be from a different operation type.' `
            -RequiredResolution 'Pass the matching gate or regenerate evidence for the requested gate.'))
    }

    if ($targetEnvironment -eq 'prod' -and -not (Test-ProdAuthorization -Evidence $evidence -Gate $Gate)) {
        [void]$errors.Add((New-EvidenceDiagnostic `
            -Code 'PROD_ACCESS_NOT_AUTHORIZED' `
            -Scope 'targetEnvironment' `
            -Message 'prod operation evidence requires explicit user authorization evidence.' `
            -Impact 'A production operation could be accepted without the required explicit approval boundary.' `
            -RequiredResolution 'Attach userAuthorization.approved=true with approvedBy, approvedAt, and matching scope, or do not validate prod evidence.'))
    }

    foreach ($requiredOperationId in $requiredOperationIds) {
        $operation = Get-OperationById -Operations $operations -OperationId $requiredOperationId
        if ($null -eq $operation) {
            [void]$errors.Add((New-EvidenceDiagnostic `
                -Code 'REQUIRED_OPERATION_MISSING' `
                -Scope 'operations' `
                -Message "Required operation is missing: $requiredOperationId" `
                -Impact 'The gate cannot prove every required operation ran.' `
                -RequiredResolution 'Record the missing required operation evidence and rerun validation.'))
            continue
        }

        $logPath = [string](Get-EvidenceProperty -Object $operation -Name 'logPath')
        if (-not (Test-ExistingLogPath -LogPath $logPath)) {
            Add-LogPathDiagnostic -Errors $errors -Scope "operations.$requiredOperationId.logPath" -LogPath $logPath
        }

        $operationStatus = [string](Get-EvidenceProperty -Object $operation -Name 'status')
        if ([string]::IsNullOrWhiteSpace($operationStatus)) {
            [void]$errors.Add((New-EvidenceDiagnostic `
                -Code 'OPERATION_STATUS_MISSING' `
                -Scope "operations.$requiredOperationId.status" `
                -Message "Required operation status is missing: $requiredOperationId" `
                -Impact 'The gate cannot determine whether the operation passed, failed, or was blocked.' `
                -RequiredResolution 'Record the real operation status and rerun validation.'))
            continue
        }

        if (Test-FailedStatus -Status $operationStatus) {
            [void]$errors.Add((New-EvidenceDiagnostic `
                -Code 'REQUIRED_OPERATION_FAILED' `
                -Scope "operations.$requiredOperationId.status" `
                -Message "Required operation did not succeed: $requiredOperationId status=$operationStatus" `
                -Impact 'A later health check must not overwrite an earlier failed or blocked operation.' `
                -RequiredResolution 'Resolve the failed operation and rerun the full workflow from the required preflight step.'))

            $missingFailureFields = @()
            foreach ($field in @('failureCode', 'failedStage', 'impact', 'requiredResolution')) {
                if (Test-EvidenceValueMissing -Value (Get-EvidenceProperty -Object $operation -Name $field)) {
                    $missingFailureFields += $field
                }
            }
            if ($missingFailureFields.Count -gt 0) {
                [void]$errors.Add((New-EvidenceDiagnostic `
                    -Code 'FAILURE_REASON_MISSING' `
                    -Scope "operations.$requiredOperationId" `
                    -Message ("Failed operation is missing failure fields: " + ($missingFailureFields -join ', ')) `
                    -Impact 'The failure cannot be diagnosed or handed off safely.' `
                    -RequiredResolution 'Record failureCode, failedStage, impact, and requiredResolution for the failed operation.'))
            }
        } elseif (-not (Test-SuccessStatus -Status $operationStatus)) {
            [void]$errors.Add((New-EvidenceDiagnostic `
                -Code 'OPERATION_STATUS_UNSUPPORTED' `
                -Scope "operations.$requiredOperationId.status" `
                -Message "Unsupported required operation status: $operationStatus" `
                -Impact 'The gate cannot safely interpret the operation result.' `
                -RequiredResolution 'Use success/pass/passed for success or failed/fail/blocked for non-success evidence.'))
        }
    }

    $finalHealthCheck = Get-EvidenceProperty -Object $evidence -Name 'finalHealthCheck'
    $finalHealthStatus = ''
    if ($null -ne $finalHealthCheck) {
        $finalHealthStatus = [string](Get-EvidenceProperty -Object $finalHealthCheck -Name 'status')
        $finalHealthLogPath = [string](Get-EvidenceProperty -Object $finalHealthCheck -Name 'logPath')
        if (-not (Test-ExistingLogPath -LogPath $finalHealthLogPath)) {
            Add-LogPathDiagnostic -Errors $errors -Scope 'finalHealthCheck.logPath' -LogPath $finalHealthLogPath
        }
    }

    $status = if ($errors.Count -eq 0) { 'pass' } else { 'blocked' }
    $exitCode = if ($errors.Count -eq 0) { 0 } else { 2 }
    $payload = [pscustomobject]([ordered]@{
        operationId = $operationId
        gate = $Gate
        targetEnvironment = $targetEnvironment
        status = $status
        finalHealthStatus = $finalHealthStatus
        requiredOperationIds = @($requiredOperationIds)
        checkedAt = (Get-Date).ToString('o')
        errors = @($errors.ToArray())
    })
    Write-EvidenceJson -Payload $payload -OutputPath $OutputPath
    return [pscustomobject]@{ Payload = $payload; ExitCode = $exitCode }
}

Export-ModuleMember -Function Invoke-OperationEvidenceValidation
