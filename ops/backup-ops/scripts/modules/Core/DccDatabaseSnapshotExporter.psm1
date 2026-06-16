Set-StrictMode -Version Latest

$script:DccSnapshotUtf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Get-DccSnapshotProperty {
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

function ConvertTo-DccSnapshotArray {
    param($Value)

    if ($null -eq $Value) {
        return @()
    }
    if ($Value -is [System.Array]) {
        return @($Value)
    }
    return @($Value)
}

function Get-DccSnapshotString {
    param($Value)

    if ($null -eq $Value) {
        return ''
    }
    return ([string]$Value).Trim()
}

function ConvertTo-DccSnapshotSha256 {
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

function Read-DccSnapshotJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
}

function Write-DccSnapshotJson {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )

    $parent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $json = $Payload | ConvertTo-Json -Depth 80
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, $script:DccSnapshotUtf8NoBom)
}

function New-DccSnapshotDiagnostic {
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

function Add-DccSnapshotDiagnostic {
    param(
        [Parameter(Mandatory = $true)]$Errors,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $true)][string]$Impact,
        [Parameter(Mandatory = $true)][string]$NextStep
    )

    [void]$Errors.Add((New-DccSnapshotDiagnostic -Code $Code -Scope $Scope -Message $Message -Impact $Impact -NextStep $NextStep))
}

function New-DccSnapshotBlockedPayload {
    param(
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][long]$TenantId,
        [Parameter(Mandatory = $true)]$Errors
    )

    return [pscustomobject]([ordered]@{
        operationId = 'op-dcc-snapshot-export-' + [guid]::NewGuid().ToString()
        schemaVersion = 'dcc-snapshot-export-diagnostic-v1'
        status = 'blocked'
        targetEnvironment = $TargetEnvironment
        targetHost = $TargetHost
        tenantId = $TenantId
        checkedAt = [System.DateTimeOffset]::Now.ToString('o')
        errors = @($Errors.ToArray())
    })
}

function Test-DccSnapshotRowHasField {
    param(
        [Parameter(Mandatory = $true)]$Row,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($Row -is [System.Collections.IDictionary]) {
        return $Row.Contains($Name)
    }
    return $null -ne $Row.PSObject.Properties[$Name]
}

function ConvertTo-DccSnapshotRowsFromJson {
    param([Parameter(Mandatory = $true)][string]$Path)

    $payload = Read-DccSnapshotJson -Path $Path
    $rows = ConvertTo-DccSnapshotArray -Value (Get-DccSnapshotProperty -Object $payload -Name 'rows')
    return @($rows)
}

function ConvertTo-DccSnapshotRowsFromCsv {
    param([Parameter(Mandatory = $true)][string]$Path)

    return @(Import-Csv -LiteralPath $Path -Encoding UTF8)
}

function ConvertTo-DccSnapshotRowsFromTsv {
    param([Parameter(Mandatory = $true)][string]$Path)

    $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $lines = @($text -split "`r?`n" | Where-Object {
            -not [string]::IsNullOrWhiteSpace($_) -and
            ($_ -notmatch '^mysql:\s+\[Warning\]\s+Using a password on the command line interface can be insecure\.?$')
        })
    if ($lines.Count -eq 0) {
        return @()
    }
    $headers = @($lines[0] -split "`t")
    $rows = [System.Collections.Generic.List[object]]::new()
    for ($index = 1; $index -lt $lines.Count; $index++) {
        $columns = @($lines[$index] -split "`t", $headers.Count)
        if ($columns.Count -ne $headers.Count) {
            throw "DCC MySQL CLI output row $($index + 1) has $($columns.Count) columns; expected $($headers.Count)."
        }
        $row = [ordered]@{}
        for ($columnIndex = 0; $columnIndex -lt $headers.Count; $columnIndex++) {
            $row[$headers[$columnIndex]] = $columns[$columnIndex]
        }
        $rows.Add([pscustomobject]$row) | Out-Null
    }
    return @($rows)
}

function New-DccDatabaseSnapshotSql {
    param([Parameter(Mandatory = $true)][long]$TenantId)

    return @"
SELECT
  cf.id AS controlledFileId,
  cf.tenant_id AS tenantId,
  cf.file_number AS fileNumber,
  cf.version_no AS versionNo,
  cf.status AS status,
  COALESCE(DATE_FORMAT(cf.update_time, '%Y-%m-%dT%H:%i:%s+08:00'), '') AS updatedAt,
  refs.object_role AS objectRole,
  refs.object_file_id AS objectFileId,
  COALESCE(REPLACE(REPLACE(REPLACE(f.path, CHAR(9), ' '), CHAR(13), ''), CHAR(10), ''), '') AS objectPath,
  '' AS objectSha256,
  COALESCE(
    CONCAT('sha256:', SHA2(GROUP_CONCAT(DISTINCT CONCAT_WS(':', pr.action_type, pr.subject_type, pr.subject_id, pr.active) ORDER BY pr.action_type, pr.subject_type, pr.subject_id SEPARATOR '|'), 256)),
    CONCAT('sha256:', SHA2('no-permission', 256))
  ) AS permissionDigest
FROM dcc_controlled_file cf
LEFT JOIN (
  SELECT id AS controlled_file_id, 'source' AS object_role, source_file_id AS object_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND source_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'original', original_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND original_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'drawing_pdf', drawing_pdf_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND drawing_pdf_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'training_record', training_record_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND training_record_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'published', published_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND published_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'stamped', stamped_file_id FROM dcc_controlled_file WHERE tenant_id = $TenantId AND stamped_file_id IS NOT NULL AND deleted = b'0'
) refs ON refs.controlled_file_id = cf.id
LEFT JOIN infra_file f ON f.id = refs.object_file_id AND f.deleted = b'0'
LEFT JOIN dcc_file_category_permission_rule pr
  ON pr.category_id = cf.category_id
 AND pr.tenant_id = cf.tenant_id
 AND pr.deleted = b'0'
 AND pr.active = 1
WHERE cf.tenant_id = $TenantId
  AND cf.deleted = b'0'
GROUP BY
  cf.id, cf.tenant_id, cf.file_number, cf.version_no, cf.status, cf.update_time,
  refs.object_role, refs.object_file_id, f.path
ORDER BY cf.id, refs.object_role, refs.object_file_id
"@
}

function Invoke-DccSnapshotNativeProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    foreach ($argument in $Arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.UseShellExecute = $false
    $startInfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $startInfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = $stdout
        Stderr = $stderr
    }
}

function Invoke-DccDatabaseSnapshotQuery {
    param(
        [Parameter(Mandatory = $true)][long]$TenantId,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][string]$DatabaseHost,
        [Parameter(Mandatory = $true)][int]$DatabasePort,
        [Parameter(Mandatory = $true)][string]$DatabaseName,
        [Parameter(Mandatory = $true)][string]$MySqlPath,
        [string]$DatabaseUser,
        [string]$DatabasePassword,
        [string]$DefaultsExtraFile
    )

    if ($TargetHost -eq 'local') {
        if ($DatabaseHost -notin @('local', 'localhost', '127.0.0.1', '::1')) {
            throw "DatabaseHost must be local/localhost/127.0.0.1/::1 when TargetHost is local; got $DatabaseHost."
        }
    } elseif ($DatabaseHost -ne $TargetHost) {
        throw "DatabaseHost must equal TargetHost $TargetHost for remote test export; got $DatabaseHost."
    }
    if ([string]::IsNullOrWhiteSpace($DefaultsExtraFile) -and ([string]::IsNullOrWhiteSpace($DatabaseUser) -or [string]::IsNullOrWhiteSpace($DatabasePassword))) {
        throw 'Database export requires either DefaultsExtraFile or explicit DatabaseUser and DatabasePassword.'
    }
    if (-not [string]::IsNullOrWhiteSpace($DefaultsExtraFile) -and -not (Test-Path -LiteralPath $DefaultsExtraFile -PathType Leaf)) {
        throw "DefaultsExtraFile does not exist: $DefaultsExtraFile"
    }

    $arguments = [System.Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($DefaultsExtraFile)) {
        $arguments.Add("--defaults-extra-file=$DefaultsExtraFile") | Out-Null
    }
    $arguments.Add('--batch') | Out-Null
    $arguments.Add('--raw') | Out-Null
    $arguments.Add('--default-character-set=utf8mb4') | Out-Null
    $arguments.Add('-h') | Out-Null
    $arguments.Add($DatabaseHost) | Out-Null
    $arguments.Add('-P') | Out-Null
    $arguments.Add([string]$DatabasePort) | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($DatabaseUser)) {
        $arguments.Add('-u') | Out-Null
        $arguments.Add($DatabaseUser) | Out-Null
    }
    if (-not [string]::IsNullOrWhiteSpace($DatabasePassword)) {
        $arguments.Add("-p$DatabasePassword") | Out-Null
    }
    $arguments.Add($DatabaseName) | Out-Null
    $arguments.Add('-e') | Out-Null
    $arguments.Add((New-DccDatabaseSnapshotSql -TenantId $TenantId)) | Out-Null

    $result = Invoke-DccSnapshotNativeProcess -FilePath $MySqlPath -Arguments @($arguments)
    if ($result.ExitCode -ne 0) {
        throw "mysql read-only DCC snapshot query failed with exit code $($result.ExitCode): $($result.Stderr)"
    }

    $tempPath = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempPath, $result.Stdout, $script:DccSnapshotUtf8NoBom)
        return @(ConvertTo-DccSnapshotRowsFromTsv -Path $tempPath)
    } finally {
        if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

function Add-DccSnapshotRequiredFieldDiagnostics {
    param(
        [Parameter(Mandatory = $true)]$Row,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)]$Errors
    )

    $requiredFields = @(
        'controlledFileId',
        'tenantId',
        'fileNumber',
        'versionNo',
        'status',
        'updatedAt',
        'objectRole',
        'objectFileId',
        'objectPath',
        'permissionDigest'
    )
    foreach ($field in $requiredFields) {
        if (-not (Test-DccSnapshotRowHasField -Row $Row -Name $field)) {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_query_field_missing' -Scope "$Scope.$field" `
                -Message "DCC database snapshot query result is missing field $field." `
                -Impact 'The exporter cannot build a deterministic dcc-snapshot-v1 record.' `
                -NextStep 'Update the query fixture or database SELECT so every required field is present.'
        }
    }
}

function ConvertTo-DccDatabaseSnapshot {
    param(
        [Parameter(Mandatory = $true)]$Rows,
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][long]$TenantId,
        [Parameter(Mandatory = $true)]$Errors
    )

    $rowArray = @(ConvertTo-DccSnapshotArray -Value $Rows)
    if ($rowArray.Count -eq 0) {
        Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_snapshot_no_records' -Scope 'rows' `
            -Message 'DCC database snapshot query returned no controlled-file records.' `
            -Impact 'The backup would carry no DCC business-chain evidence and could be mistaken for a verified DCC backup.' `
            -NextStep 'Create or select real test-tenant DCC controlled-file data through the frontend, then rerun the read-only export.'
    }

    $fileMap = @{}
    foreach ($row in $rowArray) {
        $rowScope = 'rows'
        Add-DccSnapshotRequiredFieldDiagnostics -Row $row -Scope $rowScope -Errors $Errors
        if ($Errors.Count -gt 0) {
            continue
        }

        $controlledFileIdRaw = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'controlledFileId')
        $tenantIdRaw = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'tenantId')
        try {
            $controlledFileId = [long]$controlledFileIdRaw
            $rowTenantId = [long]$tenantIdRaw
        } catch {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_query_field_invalid' -Scope 'rows.id' `
                -Message "DCC query row has invalid controlledFileId or tenantId: controlledFileId=$controlledFileIdRaw tenantId=$tenantIdRaw." `
                -Impact 'The exporter cannot bind the row to an explicit tenant-scoped controlled file.' `
                -NextStep 'Fix the query result so controlledFileId and tenantId are numeric.'
            continue
        }

        if ($rowTenantId -ne $TenantId) {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'tenant_id_mismatch' -Scope "controlledFiles.$controlledFileId.tenantId" `
                -Message "DCC query row tenantId $rowTenantId does not match requested TenantId $TenantId." `
                -Impact 'The snapshot could mix tenants and cannot be used for a test-tenant backup manifest.' `
                -NextStep 'Regenerate the query result for exactly one explicit test tenant.'
            continue
        }

        $fileKey = "controlled-file:$controlledFileId"
        if (-not $fileMap.ContainsKey($fileKey)) {
            $fileMap[$fileKey] = [ordered]@{
                fileKey = $fileKey
                controlledFileId = $controlledFileId
                tenantId = $TenantId
                fileNumber = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'fileNumber')
                versionNo = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'versionNo')
                status = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'status')
                state = 'active'
                permissionDigest = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'permissionDigest')
                updatedAt = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'updatedAt')
                objects = [System.Collections.Generic.List[object]]::new()
            }
        }

        $record = $fileMap[$fileKey]
        foreach ($metadataField in @('fileNumber', 'versionNo', 'status', 'permissionDigest', 'updatedAt')) {
            $rowValue = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name $metadataField)
            if ([string]::IsNullOrWhiteSpace($rowValue)) {
                Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_query_field_empty' -Scope "$fileKey.$metadataField" `
                    -Message "DCC query row field $metadataField is empty for $fileKey." `
                    -Impact 'The exported snapshot would not be auditable or deterministic.' `
                    -NextStep 'Fix the DCC query result so every active controlled file has complete metadata.'
                continue
            }
            if ([string]$record[$metadataField] -ne $rowValue) {
                Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_query_metadata_conflict' -Scope "$fileKey.$metadataField" `
                    -Message "DCC query rows disagree on $metadataField for $fileKey." `
                    -Impact 'The exporter cannot determine the authoritative database record state.' `
                    -NextStep 'Regenerate the query result without duplicate conflicting controlled-file rows.'
            }
        }

        $objectRole = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'objectRole')
        $objectFileIdRaw = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'objectFileId')
        $objectPath = (Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'objectPath')).Replace('\', '/').TrimStart('/')
        $objectSha256 = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $row -Name 'objectSha256')

        if ([string]::IsNullOrWhiteSpace($objectRole) -or [string]::IsNullOrWhiteSpace($objectFileIdRaw)) {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_active_object_reference_missing' -Scope "$fileKey.objects" `
                -Message "Active DCC file $fileKey is missing objectRole or objectFileId." `
                -Impact 'The manifest builder cannot associate the database record with object inventory.' `
                -NextStep 'Regenerate the query result with every active DCC file object reference.'
            continue
        }
        try {
            $objectFileId = [long]$objectFileIdRaw
        } catch {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_query_field_invalid' -Scope "$fileKey.objects.fileId" `
                -Message "DCC objectFileId is not numeric for ${fileKey}: $objectFileIdRaw." `
                -Impact 'The exported snapshot cannot prove the infra_file association.' `
                -NextStep 'Fix the query result so objectFileId is numeric.'
            continue
        }
        if ([string]::IsNullOrWhiteSpace($objectPath)) {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_active_object_path_missing' -Scope "$fileKey.objects.$objectRole.path" `
                -Message "Active DCC file $fileKey has no infra_file.path for object role $objectRole." `
                -Impact 'The backup manifest would restore a database record without its required object.' `
                -NextStep 'Repair the DCC file reference or infra_file row, then rerun the read-only export.'
            continue
        }

        $objectPayload = [ordered]@{
            role = $objectRole
            fileId = $objectFileId
            path = $objectPath
        }
        if (-not [string]::IsNullOrWhiteSpace($objectSha256)) {
            $objectPayload['sha256'] = $objectSha256
        }
        $record.objects.Add([pscustomobject]$objectPayload) | Out-Null
    }

    $controlledFiles = [System.Collections.Generic.List[object]]::new()
    foreach ($fileKey in @($fileMap.Keys | Sort-Object)) {
        $record = $fileMap[$fileKey]
        if ($record.objects.Count -eq 0) {
            Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_active_object_path_missing' -Scope "$fileKey.objects" `
                -Message "Active DCC file $fileKey has no exportable object path." `
                -Impact 'The backup manifest would restore a database record without object evidence.' `
                -NextStep 'Regenerate the query result after fixing DCC file object references.'
            continue
        }
        $objects = @($record.objects | Sort-Object role, fileId, path)
        $databaseDigestInput = ($record.fileKey + '|' + $record.tenantId + '|' + $record.fileNumber + '|' + $record.versionNo + '|' + $record.status + '|' + $record.updatedAt + '|' + $record.permissionDigest + '|' + (($objects | ConvertTo-Json -Depth 10) -join ''))
        $primaryObject = $objects[0]
        $primaryPath = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $primaryObject -Name 'path')
        $primarySha = Get-DccSnapshotString (Get-DccSnapshotProperty -Object $primaryObject -Name 'sha256')
        $recordPayload = [ordered]@{
            fileKey = $record.fileKey
            controlledFileId = $record.controlledFileId
            tenantId = $record.tenantId
            fileNumber = $record.fileNumber
            versionNo = $record.versionNo
            status = $record.status
            state = $record.state
            permissionDigest = $record.permissionDigest
            databaseDigest = ConvertTo-DccSnapshotSha256 -Value $databaseDigestInput
            updatedAt = $record.updatedAt
            objectPath = $primaryPath
            objects = @($objects)
        }
        if (-not [string]::IsNullOrWhiteSpace($primarySha)) {
            $recordPayload['objectSha256'] = $primarySha
        }
        $controlledFiles.Add([pscustomobject]$recordPayload) | Out-Null
    }
    if ($controlledFiles.Count -eq 0 -and $Errors.Count -eq 0) {
        Add-DccSnapshotDiagnostic -Errors $Errors -Code 'dcc_snapshot_no_records' -Scope 'controlledFiles' `
            -Message 'DCC database snapshot export produced no controlled-file records.' `
            -Impact 'The backup would carry no DCC business-chain evidence and could be mistaken for a verified DCC backup.' `
            -NextStep 'Create or select real test-tenant DCC controlled-file data through the frontend, then rerun the read-only export.'
    }

    return [pscustomobject]([ordered]@{
        schemaVersion = 'dcc-snapshot-v1'
        schemaVersionTag = 'dcc-database-snapshot-v1'
        snapshotId = 'dcc-snapshot-' + [guid]::NewGuid().ToString()
        targetEnvironment = $TargetEnvironment
        targetHost = $TargetHost
        tenantId = $TenantId
        capturedAt = [System.DateTimeOffset]::Now.ToString('o')
        controlledFiles = @($controlledFiles | Sort-Object fileKey)
    })
}

function Invoke-DccDatabaseSnapshotExport {
    [CmdletBinding(DefaultParameterSetName = 'QueryJson')]
    param(
        [Parameter(Mandatory = $true)][string]$TargetEnvironment,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][long]$TenantId,
        [Parameter(ParameterSetName = 'QueryJson', Mandatory = $true)][string]$QueryResultJsonPath,
        [Parameter(ParameterSetName = 'QueryCsv', Mandatory = $true)][string]$QueryResultCsvPath,
        [Parameter(ParameterSetName = 'MySqlCliOutput', Mandatory = $true)][string]$MySqlCliOutputPath,
        [Parameter(ParameterSetName = 'Database', Mandatory = $true)][string]$DatabaseHost,
        [Parameter(ParameterSetName = 'Database', Mandatory = $true)][int]$DatabasePort,
        [Parameter(ParameterSetName = 'Database', Mandatory = $true)][string]$DatabaseName,
        [Parameter(ParameterSetName = 'Database', Mandatory = $true)][string]$MySqlPath,
        [Parameter(ParameterSetName = 'Database')][string]$DatabaseUser,
        [Parameter(ParameterSetName = 'Database')][string]$DatabasePassword,
        [Parameter(ParameterSetName = 'Database')][string]$DefaultsExtraFile,
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
        Add-DccSnapshotDiagnostic -Errors $errors -Code 'target_environment_invalid' -Scope 'targetEnvironment' `
            -Message "DCC database snapshot export only accepts TargetEnvironment test, prod, or production; got $TargetEnvironment." `
            -Impact 'The exporter cannot prove the snapshot belongs to a protected backup flow.' `
            -NextStep 'Rerun with explicit TargetEnvironment test or production.'
    }
    $validTargetHost = if ($TargetEnvironment -eq 'test') {
        $TargetHost -in @('172.30.30.58', 'local')
    } elseif (-not [string]::IsNullOrWhiteSpace($expectedTargetHost)) {
        $TargetHost -eq $expectedTargetHost
    } else {
        $false
    }
    if (-not $validTargetHost) {
        Add-DccSnapshotDiagnostic -Errors $errors -Code 'target_host_invalid' -Scope 'targetHost' `
            -Message "DCC database snapshot target host is invalid for $TargetEnvironment; expected $expectedTargetHost, got $TargetHost." `
            -Impact 'The snapshot could be mistaken for an unapproved environment.' `
            -NextStep 'Rerun with TargetHost 172.30.30.58 for test data or 172.30.30.57 for production data.'
    }

    $rows = @()
    if ($errors.Count -eq 0) {
        try {
            if ($PSCmdlet.ParameterSetName -eq 'QueryJson') {
                $rows = @(ConvertTo-DccSnapshotRowsFromJson -Path $QueryResultJsonPath)
            } elseif ($PSCmdlet.ParameterSetName -eq 'QueryCsv') {
                $rows = @(ConvertTo-DccSnapshotRowsFromCsv -Path $QueryResultCsvPath)
            } elseif ($PSCmdlet.ParameterSetName -eq 'MySqlCliOutput') {
                $rows = @(ConvertTo-DccSnapshotRowsFromTsv -Path $MySqlCliOutputPath)
            } elseif ($PSCmdlet.ParameterSetName -eq 'Database') {
                $rows = @(Invoke-DccDatabaseSnapshotQuery `
                        -TenantId $TenantId `
                        -TargetHost $TargetHost `
                        -DatabaseHost $DatabaseHost `
                        -DatabasePort $DatabasePort `
                        -DatabaseName $DatabaseName `
                        -MySqlPath $MySqlPath `
                        -DatabaseUser $DatabaseUser `
                        -DatabasePassword $DatabasePassword `
                        -DefaultsExtraFile $DefaultsExtraFile)
            }
        } catch {
            Add-DccSnapshotDiagnostic -Errors $errors -Code 'dcc_query_input_invalid' -Scope 'input' `
                -Message ([string]$_.Exception.Message) `
                -Impact 'The exporter cannot read the DCC database snapshot query source.' `
                -NextStep 'Fix the explicit query result fixture, MySQL CLI output, or database query parameters and rerun.'
        }
    }

    if ($errors.Count -eq 0) {
        $snapshot = ConvertTo-DccDatabaseSnapshot `
            -Rows $rows `
            -TargetEnvironment $TargetEnvironment `
            -TargetHost $TargetHost `
            -TenantId $TenantId `
            -Errors $errors
    }

    if ($errors.Count -gt 0) {
        $blocked = New-DccSnapshotBlockedPayload -TargetEnvironment $TargetEnvironment -TargetHost $TargetHost -TenantId $TenantId -Errors $errors
        Write-DccSnapshotJson -Payload $blocked -OutputPath $OutputPath
        return [pscustomobject]@{ Payload = $blocked; ExitCode = 2 }
    }

    Write-DccSnapshotJson -Payload $snapshot -OutputPath $OutputPath
    return [pscustomobject]@{ Payload = $snapshot; ExitCode = 0 }
}

Export-ModuleMember -Function Invoke-DccDatabaseSnapshotExport, New-DccDatabaseSnapshotSql
