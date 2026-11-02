Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$taskDirectory = $PSScriptRoot
$closeout = [System.IO.File]::ReadAllText((Join-Path $taskDirectory 'worktree-closeout.json'),[System.Text.Encoding]::UTF8) | ConvertFrom-Json
if ($closeout.status -ne 'PASS') { throw 'Worktree closeout must pass first' }
$target = 'C:\SpugHandoff\schema-push-src-20261101'
if (Test-Path -LiteralPath $target) { throw 'Worktree still exists' }
$registry = 'C:\Users\D01021\Documents\ChatGPT\IntRuoyi\.git\intrruoyi-runtime\worktree-ports.json'
$hash = [System.Security.Cryptography.SHA256]::Create()
try { $identity = [System.BitConverter]::ToString($hash.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($registry.ToUpperInvariant()))).Replace('-','').Substring(0,24) }
finally { $hash.Dispose() }
$mutex = [System.Threading.Mutex]::new($false,"IntRuoyiWorktreePorts-$identity")
$locked = $false
try {
    try { $locked = $mutex.WaitOne([TimeSpan]::FromSeconds(30)) }
    catch [System.Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Registry lock unavailable' }
    $before = [System.IO.File]::ReadAllText($registry,[System.Text.Encoding]::UTF8)
    $document = $before | ConvertFrom-Json
    if ($document.contractVersion -ne '2026-08-24-branch-runtime-v7') { throw 'Registry contract changed' }
    $own = @($document.worktrees | Where-Object { $_.path -eq $target })
    if ($own.Count -ne 1 -or $own[0].branch -ne 'codex/three-server-schema-20261101' -or $own[0].slot -ne 3 -or $own[0].frontendPort -ne 8084 -or $own[0].backendPort -ne 48084 -or $own[0].active -ne $true) { throw 'Exact active allocation required' }
    $others = @($document.worktrees | Where-Object { $_.path -ne $target }) | ConvertTo-Json -Depth 12 -Compress
    $now = [DateTimeOffset]::Now.ToString('o')
    $own[0].active = $false
    $own[0].updatedAt = $now
    $document.updatedAt = $now
    $after = ($document | ConvertTo-Json -Depth 12) + "`r`n"
    $temp = "$registry.schema-$PID.tmp"
    $backup = "$registry.schema-$PID.bak"
    if ((Test-Path -LiteralPath $temp) -or (Test-Path -LiteralPath $backup)) { throw 'Existing task registry files require review' }
    [System.IO.File]::AppendAllText((Join-Path $taskDirectory 'execution-log.md'),"`nGREEN: experience-preflight -> PASS (release owned slot). Exact checkout absent; mutex, contract, branch, slot3, 8084/48084 verified. Preserve all other entries; mark only this task allocation inactive.`n",[System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($temp,$after,[System.Text.UTF8Encoding]::new($false))
    if ([System.IO.File]::ReadAllText($registry,[System.Text.Encoding]::UTF8) -ne $before) { throw 'Registry changed while locked' }
    [System.IO.File]::Replace($temp,$registry,$backup)
    $verified = [System.IO.File]::ReadAllText($registry,[System.Text.Encoding]::UTF8) | ConvertFrom-Json
    $peers = @($verified.worktrees | Where-Object { $_.path -ne $target }) | ConvertTo-Json -Depth 12 -Compress
    if ($peers -cne $others -or @($verified.worktrees | Where-Object { $_.path -eq $target -and $_.active -eq $false }).Count -ne 1) { throw 'Registry readback failed; backup preserved' }
    [System.IO.File]::Delete($backup)
    $report = [ordered]@{status='PASS';path=$target;slot=3;frontendPort=8084;backendPort=48084;active=$false;otherEntriesPreserved=$true;time=$now}
    $json = $report | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText((Join-Path $taskDirectory 'slot-closeout.json'),$json+"`n",[System.Text.UTF8Encoding]::new($false))
    Write-Output $json
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
