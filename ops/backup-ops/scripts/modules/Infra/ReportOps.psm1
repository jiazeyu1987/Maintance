Set-StrictMode -Version Latest

$script:BackupManifestFileName = 'manifest.json'
$script:BackupChecksumsFileName = 'checksums.txt'
$script:BackupReportNameMap = [ordered]@{
    backup = [ordered]@{
        json     = 'backup-report.json'
        markdown = 'backup-report.md'
    }
    'restore-data' = [ordered]@{
        jsonTemplate     = '{timestamp}_restore-data_{status}.report.json'
        markdownTemplate = '{timestamp}_restore-data_{status}.report.md'
    }
    rehearsal = [ordered]@{
        jsonTemplate     = '{timestamp}_rehearsal_{status}.report.json'
        markdownTemplate = '{timestamp}_rehearsal_{status}.report.md'
    }
}

function Get-BackupOpsUnicodeText {
    param(
        [Parameter(Mandatory)]
        [int[]]$CodePoints
    )

    return (-join ($CodePoints | ForEach-Object { [char]$_ }))
}

function Get-BackupOpsReportLabel {
    param(
        [Parameter(Mandatory)]
        [string]$Key
    )

    switch ($Key) {
        'backup-title' { return '# ' + (Get-BackupOpsUnicodeText -CodePoints @(0x5907, 0x4EFD, 0x62A5, 0x544A)) }
        'restore-title' { return '# ' + (Get-BackupOpsUnicodeText -CodePoints @(0x6570, 0x636E, 0x6062, 0x590D, 0x62A5, 0x544A)) }
        'rehearsal-title' { return '# ' + (Get-BackupOpsUnicodeText -CodePoints @(0x6062, 0x590D, 0x6F14, 0x7EC3, 0x62A5, 0x544A)) }
        'default-title' { return '# ' + (Get-BackupOpsUnicodeText -CodePoints @(0x5907, 0x4EFD, 0x64CD, 0x4F5C, 0x62A5, 0x544A)) }
        'backup-id' { return Get-BackupOpsUnicodeText -CodePoints @(0x5907, 0x4EFD, 0x70B9) }
        'restore-point' { return Get-BackupOpsUnicodeText -CodePoints @(0x6062, 0x590D, 0x70B9) }
        'image-tag' { return 'IMAGE_TAG' }
        'pre-restore-snapshot' { return 'pre-restore ' + (Get-BackupOpsUnicodeText -CodePoints @(0x5FEB, 0x7167)) }
        'status' { return Get-BackupOpsUnicodeText -CodePoints @(0x7ED3, 0x679C) }
        'started-at' { return Get-BackupOpsUnicodeText -CodePoints @(0x5F00, 0x59CB, 0x65F6, 0x95F4) }
        'completed-at' { return Get-BackupOpsUnicodeText -CodePoints @(0x7ED3, 0x675F, 0x65F6, 0x95F4) }
        'steps' { return Get-BackupOpsUnicodeText -CodePoints @(0x6B65, 0x9AA4, 0x7ED3, 0x679C) }
        'checks' { return Get-BackupOpsUnicodeText -CodePoints @(0x6821, 0x9A8C, 0x7ED3, 0x679C) }
        'artifacts' { return Get-BackupOpsUnicodeText -CodePoints @(0x4EA7, 0x7269) }
        'conclusion' { return Get-BackupOpsUnicodeText -CodePoints @(0x7ED3, 0x8BBA) }
        default { return $Key }
    }
}

function Test-BackupOpsMeaningfulValue {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return $false
    }

    $text = [string]$Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $false
    }

    return $text.Trim().ToLowerInvariant() -ne 'unknown'
}

function Get-BackupReportFieldValue {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request,
        [Parameter(Mandatory)]
        [string]$Name
    )

    if (-not $Request.ContainsKey($Name)) {
        throw [System.ArgumentException]::new("INTBK-6003: missing report request field '$Name'.")
    }

    $value = $Request[$Name]
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) {
        throw [System.ArgumentException]::new("INTBK-6003: report request field '$Name' cannot be empty.")
    }

    return $value
}

function Get-BackupReportFileMap {
    [CmdletBinding()]
    param()

    return [pscustomobject]([ordered]@{
            manifestJson  = "manifest/$script:BackupManifestFileName"
            checksumsFile = "manifest/$script:BackupChecksumsFileName"
            backupJson    = "manifest/$($script:BackupReportNameMap.backup.json)"
            backupMd      = "manifest/$($script:BackupReportNameMap.backup.markdown)"
            restoreJson   = $script:BackupReportNameMap['restore-data'].jsonTemplate
            restoreMd     = $script:BackupReportNameMap['restore-data'].markdownTemplate
            rehearsalJson = $script:BackupReportNameMap.rehearsal.jsonTemplate
            rehearsalMd   = $script:BackupReportNameMap.rehearsal.markdownTemplate
        })
}

function New-BackupManifestModel {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupReportFieldValue -Request $Request -Name 'BackupId')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'BackupType')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'Environment')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'StartedAt')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'CompletedAt')

    if (-not $Request.ContainsKey('Source')) {
        throw [System.ArgumentException]::new('INTBK-6001: Source is required to build manifest.json.')
    }

    if (-not $Request.ContainsKey('Deploy')) {
        throw [System.ArgumentException]::new('INTBK-6001: Deploy is required to build manifest.json.')
    }

    if (-not $Request.ContainsKey('RecoverySet') -or $null -eq $Request['RecoverySet']) {
        throw [System.ArgumentException]::new('INTBK-6001: RecoverySet is required to build manifest.json.')
    }

    $reportMap = Get-BackupReportFileMap
    $source = [ordered]@{}
    foreach ($property in $Request['Source'].PSObject.Properties) {
        $source[$property.Name] = $property.Value
    }
    if ($source.Count -eq 0 -and $Request['Source'] -is [System.Collections.IDictionary]) {
        foreach ($entry in $Request['Source'].GetEnumerator()) {
            $source[$entry.Key] = $entry.Value
        }
    }

    $deploy = [ordered]@{}
    foreach ($property in $Request['Deploy'].PSObject.Properties) {
        $deploy[$property.Name] = $property.Value
    }
    if ($deploy.Count -eq 0 -and $Request['Deploy'] -is [System.Collections.IDictionary]) {
        foreach ($entry in $Request['Deploy'].GetEnumerator()) {
            $deploy[$entry.Key] = $entry.Value
        }
    }

    $notes = if ($Request.ContainsKey('Notes')) { @($Request['Notes']) } else { @() }
    $status = if ($Request.ContainsKey('Status')) { [string]$Request['Status'] } else { 'blocked' }
    $backupStrategy = if ($Request.ContainsKey('BackupStrategy') -and $null -ne $Request['BackupStrategy']) {
        $Request['BackupStrategy']
    } else {
        [pscustomobject]@{
            mode = 'incremental-manifest'
        }
    }
    $retentionPolicy = if ($Request.ContainsKey('RetentionPolicy') -and $null -ne $Request['RetentionPolicy']) {
        $Request['RetentionPolicy']
    } else {
        [pscustomobject]@{}
    }
    $objectDeltaStats = if ($Request.ContainsKey('ObjectDeltaStats') -and $null -ne $Request['ObjectDeltaStats']) {
        $Request['ObjectDeltaStats']
    } else {
        [pscustomobject]@{
            addedCount = 0
            modifiedCount = 0
            deletedCount = 0
            reusedCount = 0
        }
    }
    $objects = if ($Request.ContainsKey('Objects') -and $null -ne $Request['Objects']) { @($Request['Objects']) } else { @() }
    $validationDefaults = [ordered]@{
        mysqlDumpCreated   = $false
        objectBackupCreated = $false
        checksumsGenerated = $false
        syncedToTestServer = $false
        rehearsalStatus    = 'unverified'
        lastRehearsedAt    = $null
    }
    $validation = [ordered]@{}
    foreach ($entry in $validationDefaults.GetEnumerator()) {
        $validation[$entry.Key] = $entry.Value
    }
    if ($Request.ContainsKey('Validation') -and $null -ne $Request['Validation']) {
        $inputValidation = $Request['Validation']
        if ($inputValidation -is [System.Collections.IDictionary]) {
            foreach ($entry in $inputValidation.GetEnumerator()) {
                $validation[$entry.Key] = $entry.Value
            }
        }
        else {
            foreach ($property in $inputValidation.PSObject.Properties) {
                $validation[$property.Name] = $property.Value
            }
        }
    }

    return [pscustomobject]([ordered]@{
            schemaVersion = 'v2'
            backupId      = $Request['BackupId']
            targetEnvironment = if ($Request.ContainsKey('TargetEnvironment')) { $Request['TargetEnvironment'] } else { $Request['Environment'] }
            targetHost    = if ($Request.ContainsKey('TargetHost')) { $Request['TargetHost'] } elseif ($source.Contains('serverHost')) { $source['serverHost'] } else { $null }
            backupType    = $Request['BackupType']
            environment   = $Request['Environment']
            status        = $status
            source        = [pscustomobject]$source
            operator      = [pscustomobject]([ordered]@{
                    mode = if ($Request.ContainsKey('OperatorMode')) { $Request['OperatorMode'] } else { 'system' }
                    name = if ($Request.ContainsKey('OperatorName')) { $Request['OperatorName'] } else { 'phase-1-skeleton' }
                })
            imageTag      = if ($deploy.Contains('imageTag')) { $deploy['imageTag'] } elseif ($Request.ContainsKey('ImageTag')) { $Request['ImageTag'] } else { $null }
            time          = [pscustomobject]([ordered]@{
                    startedAt   = $Request['StartedAt']
                    completedAt = $Request['CompletedAt']
                })
            artifacts     = [pscustomobject]([ordered]@{
                    mysqlDump      = if ($Request.ContainsKey('MySqlDumpPath')) { $Request['MySqlDumpPath'] } else { 'mysql/ruoyi-vue-pro.sql.gz' }
                    objectSnapshot = if ($Request.ContainsKey('ObjectSnapshotPath')) { $Request['ObjectSnapshotPath'] } else { 'objects/manifest-object-inventory.json' }
                    dccBackupManifest = if ($Request.ContainsKey('DccBackupManifestPath')) { $Request['DccBackupManifestPath'] } else { 'manifest/dcc-backup-manifest.json' }
                    composeFile    = if ($Request.ContainsKey('ComposeFilePath')) { $Request['ComposeFilePath'] } else { 'deploy/docker-compose.yml' }
                    runtimeEnv     = if ($Request.ContainsKey('RuntimeEnvPath')) { $Request['RuntimeEnvPath'] } else { 'deploy/runtime.env' }
                    imageTagFile   = if ($Request.ContainsKey('ImageTagFilePath')) { $Request['ImageTagFilePath'] } else { 'deploy/image-tag.txt' }
                    checksumsFile  = $reportMap.checksumsFile
            })
            deploy        = [pscustomobject]$deploy
            recoverySet   = $Request['RecoverySet']
            backupStrategy = $backupStrategy
            retentionPolicy = $retentionPolicy
            objectDeltaStats = $objectDeltaStats
            objects = @($objects)
            validation    = [pscustomobject]$validation
            notes         = @($notes)
        })
}

function New-BackupOperationReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupReportFieldValue -Request $Request -Name 'ReportType')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'Status')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'StartedAt')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'CompletedAt')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'Summary')

    $steps = if ($Request.ContainsKey('Steps')) { @($Request['Steps']) } else { @() }
    $artifacts = if ($Request.ContainsKey('Artifacts')) { $Request['Artifacts'] } else { [ordered]@{} }

    $report = [ordered]@{
        reportType  = $Request['ReportType']
        status      = $Request['Status']
        startedAt   = $Request['StartedAt']
        completedAt = $Request['CompletedAt']
        steps       = @($steps)
        artifacts   = [pscustomobject]$artifacts
        summary     = $Request['Summary']
    }

    if ($Request.ContainsKey('BackupId')) {
        $report['backupId'] = $Request['BackupId']
    }

    if ($Request.ContainsKey('RestorePoint')) {
        $report['restorePoint'] = $Request['RestorePoint']
    }

    if ($Request.ContainsKey('ImageTag')) {
        $report['imageTag'] = $Request['ImageTag']
    }

    if ($Request.ContainsKey('PreRestoreSnapshotId')) {
        $report['preRestoreSnapshotId'] = $Request['PreRestoreSnapshotId']
    }

    if ($Request.ContainsKey('Checks')) {
        $report['checks'] = [pscustomobject]$Request['Checks']
    }

    return [pscustomobject]$report
}

function ConvertTo-BackupMarkdownReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Report
    )

    $title = switch ($Report.reportType) {
        'backup' { Get-BackupOpsReportLabel -Key 'backup-title' }
        'restore-data' { Get-BackupOpsReportLabel -Key 'restore-title' }
        'rehearsal' { Get-BackupOpsReportLabel -Key 'rehearsal-title' }
        default { Get-BackupOpsReportLabel -Key 'default-title' }
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add($title)
    $lines.Add('')

    if ($Report.PSObject.Properties['backupId']) {
        $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'backup-id') + ': `' + $Report.backupId + '`')
    }

    if ($Report.PSObject.Properties['restorePoint']) {
        $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'restore-point') + ': `' + $Report.restorePoint + '`')
    }

    if ($Report.PSObject.Properties['imageTag']) {
        $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'image-tag') + ': `' + $Report.imageTag + '`')
    }

    $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'status') + ': `' + $Report.status + '`')
    $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'started-at') + ': `' + $Report.startedAt + '`')
    $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'completed-at') + ': `' + $Report.completedAt + '`')

    if ($Report.PSObject.Properties['preRestoreSnapshotId']) {
        $lines.Add('- ' + (Get-BackupOpsReportLabel -Key 'pre-restore-snapshot') + ': `' + $Report.preRestoreSnapshotId + '`')
    }

    $lines.Add('')

    if (@($Report.steps).Count -gt 0) {
        $lines.Add('## ' + (Get-BackupOpsReportLabel -Key 'steps'))
        $lines.Add('')
        foreach ($step in @($Report.steps)) {
            $lines.Add("- $($step.name): $($step.status)")
        }
        $lines.Add('')
    }

    if ($Report.PSObject.Properties['checks']) {
        $lines.Add('## ' + (Get-BackupOpsReportLabel -Key 'checks'))
        $lines.Add('')
        foreach ($property in $Report.checks.PSObject.Properties) {
            $lines.Add("- $($property.Name): $($property.Value)")
        }
        $lines.Add('')
    }

    if ($Report.PSObject.Properties['artifacts'] -and @($Report.artifacts.PSObject.Properties).Count -gt 0) {
        $lines.Add('## ' + (Get-BackupOpsReportLabel -Key 'artifacts'))
        $lines.Add('')
        foreach ($property in $Report.artifacts.PSObject.Properties) {
            $lines.Add('- ' + $property.Name + ': `' + $property.Value + '`')
        }
        $lines.Add('')
    }

    $lines.Add('## ' + (Get-BackupOpsReportLabel -Key 'conclusion'))
    $lines.Add('')
    $lines.Add($Report.summary)

    return ($lines -join [Environment]::NewLine)
}

function Resolve-BackupReportPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$Request
    )

    [void](Get-BackupReportFieldValue -Request $Request -Name 'Action')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'Status')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'Timestamp')
    [void](Get-BackupReportFieldValue -Request $Request -Name 'RootPath')

    $map = Get-BackupReportFileMap
    $relative = switch ($Request['Action']) {
        'backup' { $map.backupJson }
        'backup-md' { $map.backupMd }
        'restore-data' { $map.restoreJson.Replace('{timestamp}', $Request['Timestamp']).Replace('{status}', $Request['Status']) }
        'restore-data-md' { $map.restoreMd.Replace('{timestamp}', $Request['Timestamp']).Replace('{status}', $Request['Status']) }
        'rehearsal' { $map.rehearsalJson.Replace('{timestamp}', $Request['Timestamp']).Replace('{status}', $Request['Status']) }
        'rehearsal-md' { $map.rehearsalMd.Replace('{timestamp}', $Request['Timestamp']).Replace('{status}', $Request['Status']) }
        default { throw [System.ArgumentException]::new("INTBK-6003: unsupported action '$($Request['Action'])' for report path resolution.") }
    }

    return [pscustomobject]([ordered]@{
            relativePath = $relative
            fullPath     = Join-Path -Path $Request['RootPath'] -ChildPath $relative
        })
}

function Publish-BackupOpsReport {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [object]$StartedAt,
        [Parameter(Mandatory = $true)]
        [object]$CompletedAt,
        [Parameter(Mandatory = $true)]
        [string]$Summary,
        [Parameter(Mandatory = $true)]
        [hashtable]$Context,
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    $reportType = if ($Action -eq 'backup-now' -or $Action -eq 'backup-scheduled') { 'backup' } else { $Action }
    $reportRequest = @{
        ReportType = $reportType
        Status = $Status
        StartedAt = ([System.DateTimeOffset]$StartedAt).ToString('o')
        CompletedAt = ([System.DateTimeOffset]$CompletedAt).ToString('o')
        Summary = $Summary
        Artifacts = @{}
        Steps = @()
    }
    if ($Context.ContainsKey('backupId') -and -not [string]::IsNullOrWhiteSpace([string]$Context['backupId'])) {
        $reportRequest['BackupId'] = $Context['backupId']
        if ($Action -eq 'restore-data') {
            $reportRequest['RestorePoint'] = $Context['backupId']
        }
    }
    if ($Action -eq 'rollback-app' -and (Test-BackupOpsMeaningfulValue -Value $Context['imageTag'])) {
        $reportRequest['ImageTag'] = [string]$Context['imageTag']
    }
    if ($Context.ContainsKey('preRestoreSnapshotId') -and -not [string]::IsNullOrWhiteSpace([string]$Context['preRestoreSnapshotId'])) {
        $reportRequest['PreRestoreSnapshotId'] = $Context['preRestoreSnapshotId']
    }
    if ($Context.ContainsKey('checks') -and $null -ne $Context['checks']) {
        $reportRequest['Checks'] = $Context['checks']
    }
    $report = New-BackupOperationReport -Request $reportRequest

    $completedSession = Complete-BackupOpsLogSession -Session $LogSession -Status $Status -Summary $Summary
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($completedSession.reportJsonPath, ($report | ConvertTo-Json -Depth 8), $encoding)
    [System.IO.File]::WriteAllText($completedSession.reportPath, (ConvertTo-BackupMarkdownReport -Report $report), $encoding)

    return [pscustomobject]@{
        ReportPath = $completedSession.reportPath
        ReportJsonPath = $completedSession.reportJsonPath
        LogPath = $completedSession.logPath
    }
}

function Complete-BackupOpsOutcome {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [object]$Config,
        [Parameter(Mandatory = $true)]
        [string]$Action,
        [Parameter(Mandatory = $true)]
        [ValidateSet('success', 'fail', 'blocked')]
        [string]$Status,
        [Parameter(Mandatory = $true)]
        [string]$Code,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [object]$StartedAt,
        [object]$CompletedAt = $null,
        [hashtable]$Context = @{},
        [Parameter(Mandatory = $true)]
        [object]$LogSession
    )

    if ($null -eq $CompletedAt) {
        $CompletedAt = [System.DateTimeOffset]::Now
    }

    $report = Publish-BackupOpsReport `
        -Config $Config `
        -Action $Action `
        -Status $Status `
        -StartedAt $StartedAt `
        -CompletedAt $CompletedAt `
        -Summary $Message `
        -Context $Context `
        -LogSession $LogSession

    return New-BackupOpsResult `
        -Action $Action `
        -Status $Status `
        -Code $Code `
        -Message $Message `
        -StartedAt $StartedAt `
        -CompletedAt $CompletedAt `
        -LogPath $report.LogPath `
        -ReportPath $report.ReportPath `
        -Context $Context
}

Export-ModuleMember -Function Get-BackupReportFileMap, New-BackupManifestModel, New-BackupOperationReport, ConvertTo-BackupMarkdownReport, Resolve-BackupReportPath, Publish-BackupOpsReport, Complete-BackupOpsOutcome
