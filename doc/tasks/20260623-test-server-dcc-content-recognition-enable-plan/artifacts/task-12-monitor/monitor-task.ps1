param(
    [string]$ServerHost = '172.30.30.58',
    [Int64]$TaskId = 12,
    [int]$IntervalSeconds = 120,
    [string]$OutputDir = 'D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-test-server-dcc-content-recognition-enable-plan\artifacts\task-12-monitor'
)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

$latestPath = Join-Path $OutputDir 'latest.json'
$historyPath = Join-Path $OutputDir 'history.ndjson'
$logPath = Join-Path $OutputDir 'poll.log'
$metaPath = Join-Path $OutputDir 'monitor-meta.json'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalized = ($Content -replace "`r`n", "`n").Replace("`r", "`n")
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
}

function Append-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $normalized = ($Content -replace "`r`n", "`n").Replace("`r", "`n")
    [System.IO.File]::AppendAllText($Path, $normalized, $utf8NoBom)
}

function Get-TaskSnapshot {
    $remote = @"
cat <<'SQL' | docker exec -i intruoyi-mysql env MYSQL_PWD=123456 mysql --default-character-set=utf8mb4 -N -B -uroot ruoyi-vue-pro
SELECT id, status, total_count, processed_count, success_count, failed_count, skipped_existing_count, remaining_count, COALESCE(last_failure_message, '')
FROM dcc_controlled_file_batch_recognition_task
WHERE id = $TaskId;
SQL
"@

    $rawOutput = & ssh "root@$ServerHost" $remote 2>$null | ForEach-Object { "$_" }
    $dataLine = $rawOutput | Where-Object { $_.StartsWith("$TaskId`t") } | Select-Object -First 1
    if (-not $dataLine) {
        throw "No task row returned for taskId=$TaskId. Raw output: $($rawOutput -join ' | ')"
    }

    $parts = $dataLine -split "`t", 9
    if ($parts.Length -lt 9) {
        throw "Unexpected task row format for taskId=${TaskId}: $dataLine"
    }

    [pscustomobject]@{
        checkedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
        taskId = [Int64]$parts[0]
        status = $parts[1]
        totalCount = [Int64]$parts[2]
        processedCount = [Int64]$parts[3]
        successCount = [Int64]$parts[4]
        failedCount = [Int64]$parts[5]
        skippedExistingCount = [Int64]$parts[6]
        remainingCount = [Int64]$parts[7]
        lastFailureMessage = $parts[8]
        diagnostics = @($rawOutput | Where-Object { $_ -ne $dataLine })
    }
}

function Format-NullableNumber($Value) {
    if ($null -eq $Value) {
        return 'null'
    }
    return [string]$Value
}

function Format-Message($Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return '-'
    }
    return $Value
}

$meta = [pscustomobject]@{
    startedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
    serverHost = $ServerHost
    taskId = $TaskId
    intervalSeconds = $IntervalSeconds
    outputDir = $OutputDir
}
Write-Utf8NoBomFile -Path $metaPath -Content (ConvertTo-Json $meta -Depth 4)

$lastProcessed = $null
$lastSuccess = $null
$lastFailed = $null

while ($true) {
    try {
        $snapshot = Get-TaskSnapshot
        $deltaProcessed = if ($null -eq $lastProcessed) { $null } else { $snapshot.processedCount - $lastProcessed }
        $deltaSuccess = if ($null -eq $lastSuccess) { $null } else { $snapshot.successCount - $lastSuccess }
        $deltaFailed = if ($null -eq $lastFailed) { $null } else { $snapshot.failedCount - $lastFailed }
        $record = [ordered]@{
            checkedAt = $snapshot.checkedAt
            taskId = $snapshot.taskId
            status = $snapshot.status
            totalCount = $snapshot.totalCount
            processedCount = $snapshot.processedCount
            successCount = $snapshot.successCount
            failedCount = $snapshot.failedCount
            skippedExistingCount = $snapshot.skippedExistingCount
            remainingCount = $snapshot.remainingCount
            deltaProcessed = $deltaProcessed
            deltaSuccess = $deltaSuccess
            deltaFailed = $deltaFailed
            lastFailureMessage = $snapshot.lastFailureMessage
            diagnostics = $snapshot.diagnostics
        }

        $json = ConvertTo-Json $record -Depth 6
        Write-Utf8NoBomFile -Path $latestPath -Content $json
        Append-Utf8NoBomFile -Path $historyPath -Content ($json + "`n")
        Append-Utf8NoBomFile -Path $logPath -Content (
            "[{0}] status={1} processed={2}/{3} success={4} failed={5} skipped={6} remaining={7} deltaProcessed={8} deltaSuccess={9} deltaFailed={10} lastFailure={11}`n" -f
            $snapshot.checkedAt,
            $snapshot.status,
            $snapshot.processedCount,
            $snapshot.totalCount,
            $snapshot.successCount,
            $snapshot.failedCount,
            $snapshot.skippedExistingCount,
            $snapshot.remainingCount,
            (Format-NullableNumber $deltaProcessed),
            (Format-NullableNumber $deltaSuccess),
            (Format-NullableNumber $deltaFailed),
            (Format-Message $snapshot.lastFailureMessage)
        )

        $lastProcessed = $snapshot.processedCount
        $lastSuccess = $snapshot.successCount
        $lastFailed = $snapshot.failedCount

        if ($snapshot.status -notin @('WAITING', 'RUNNING')) {
            break
        }
    } catch {
        $errorRecord = [ordered]@{
            checkedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz')
            taskId = $TaskId
            status = 'MONITOR_ERROR'
            message = $_.Exception.Message
        }
        $json = ConvertTo-Json $errorRecord -Depth 4
        Write-Utf8NoBomFile -Path $latestPath -Content $json
        Append-Utf8NoBomFile -Path $historyPath -Content ($json + "`n")
        Append-Utf8NoBomFile -Path $logPath -Content (
            "[{0}] status=MONITOR_ERROR message={1}`n" -f
            $errorRecord.checkedAt,
            $errorRecord.message
        )
    }

    Start-Sleep -Seconds $IntervalSeconds
}
