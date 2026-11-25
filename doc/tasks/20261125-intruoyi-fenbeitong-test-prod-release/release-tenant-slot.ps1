$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$repo = 'C:\Users\D01021\Documents\ChatGPT\IntRuoyi'
$taskPath = 'C:\SpugHandoff\release\fenbeitong-ticket-tenant-20261126'
if (Test-Path -LiteralPath $taskPath) { throw 'Task worktree still exists; keep reservation.' }
Push-Location -LiteralPath $repo
try {
    . (Join-Path $repo 'scripts\runtime\branch-runtime-profile.ps1')
    $commonGit = (& git -C $repo rev-parse --path-format=absolute --git-common-dir).Trim()
    if ($LASTEXITCODE -ne 0 -or -not [System.IO.Path]::IsPathRooted($commonGit)) {
        throw 'Cannot resolve the source repository registry.'
    }
    $registry = Join-Path $commonGit 'intrruoyi-runtime\worktree-ports.json'
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = [System.BitConverter]::ToString($sha.ComputeHash(
            [System.Text.Encoding]::UTF8.GetBytes($registry.ToUpperInvariant())
        )).Replace('-', '').Substring(0, 24)
    } finally { $sha.Dispose() }
    $mutex = [System.Threading.Mutex]::new($false, "IntRuoyiWorktreePorts-$hash")
    $locked = $false
    try {
        try { $locked = $mutex.WaitOne([TimeSpan]::FromSeconds(30)) }
        catch [System.Threading.AbandonedMutexException] { $locked = $true }
        if (-not $locked) { throw 'Runtime registry lock unavailable.' }
        $document = [System.IO.File]::ReadAllText($registry, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $rows = @($document.worktrees | Where-Object { $_.name -eq 'fenbeitong-ticket-tenant-20261126' })
        if ($rows.Count -ne 1 -or $rows[0].branch -ne 'codex/fenbeitong-ticket-tenant-20261126' -or
            (Normalize-BranchRuntimePath -Path $rows[0].path) -ne (Normalize-BranchRuntimePath -Path $taskPath) -or
            $rows[0].slot -ne 10 -or $rows[0].frontendPort -ne 8091 -or $rows[0].backendPort -ne 48091) {
            throw 'Reservation identity differs; registry preserved.'
        }
        $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        if (@($listeners | Where-Object { $_.Port -in @(8091, 48091) }).Count -gt 0) {
            throw 'Task ports still have listeners; keep reservation.'
        }
        $otherBefore = @($document.worktrees | Where-Object { $_.name -ne 'fenbeitong-ticket-tenant-20261126' }) | ConvertTo-Json -Depth 10 -Compress
        $rows[0].active = $false
        $rows[0].updatedAt = [DateTimeOffset]::Now.ToString('o')
        $document.updatedAt = $rows[0].updatedAt
        Assert-BranchRuntimePortRegistryEntries -Entries @($document.worktrees) -Profiles (Get-BranchRuntimeProfiles)
        $temp = $registry + '.registration-release-' + [Guid]::NewGuid().ToString('N') + '.tmp'
        $backup = $temp + '.before'
        [System.IO.File]::WriteAllText($temp, ($document | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
        [System.IO.File]::Replace($temp, $registry, $backup)
        $actual = [System.IO.File]::ReadAllText($registry, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $otherAfter = @($actual.worktrees | Where-Object { $_.name -ne 'fenbeitong-ticket-tenant-20261126' }) | ConvertTo-Json -Depth 10 -Compress
        if ($otherBefore -cne $otherAfter -or
            @($actual.worktrees | Where-Object { $_.name -eq 'fenbeitong-ticket-tenant-20261126' })[0].active) {
            throw 'Runtime registry readback differs; inspect retained backup.'
        }
        [System.IO.File]::Delete($backup)
        Write-Output 'PASS: only task slot 10 released; ports have no listeners and other entries unchanged.'
    } finally {
        if ($locked) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
} finally { Pop-Location }
