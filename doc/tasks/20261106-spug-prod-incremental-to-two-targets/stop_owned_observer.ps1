param([Parameter(Mandatory=$true)][string]$RecordName)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if ($RecordName -notmatch '^restore-58-r3-observer-cleanup-[2-9]\.json$') { throw 'EXPLICIT_RECORD_REQUIRED' }
$ownedRecordPath = Join-Path $PSScriptRoot $RecordName
if (Test-Path -LiteralPath $ownedRecordPath) { throw 'CLEANUP_ALREADY_RECORDED' }
$ownedRows = @(Get-CimInstance Win32_Process)
$ownedRoots = @($ownedRows | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/watch_spug_operation\.cjs restore-58-r3' })
if ($ownedRoots.Count -ne 1) { throw 'EXACT_OBSERVER_ROOT_REQUIRED' }
$ownedIds = [System.Collections.Generic.HashSet[int]]::new()
[void]$ownedIds.Add([int]$ownedRoots[0].ProcessId)
do {
 $ownedAdded=0
 foreach ($ownedRow in $ownedRows) {
  if ($ownedIds.Contains([int]$ownedRow.ParentProcessId) -and -not $ownedIds.Contains([int]$ownedRow.ProcessId)) {
   [void]$ownedIds.Add([int]$ownedRow.ProcessId);$ownedAdded++
  }
 }
} while ($ownedAdded -gt 0)
$ownedTree = @($ownedRows | Where-Object { $ownedIds.Contains([int]$_.ProcessId) })
if (@($ownedTree | Where-Object { $_.Name -notin @('node.exe','chrome.exe','chrome_crashpad_handler.exe') }).Count) { throw 'UNKNOWN_OBSERVER_CHILD' }
$ownedEvidence = [ordered]@{ observedAt=[DateTime]::UtcNow.ToString('o'); reason='Readonly observer stalled at importing saved browser storage; exact owned tree only'; processes=@($ownedTree | Select-Object ProcessId,ParentProcessId,Name,CreationDate); stopped=$false; remoteChanges=0 }
[System.IO.File]::WriteAllText($ownedRecordPath,($ownedEvidence | ConvertTo-Json -Depth 5),[System.Text.UTF8Encoding]::new($false))
foreach ($ownedRow in ($ownedTree | Sort-Object CreationDate -Descending)) {
 $ownedCurrent = Get-CimInstance Win32_Process -Filter "ProcessId=$($ownedRow.ProcessId)"
 if ($ownedCurrent -and $ownedCurrent.CreationDate -eq $ownedRow.CreationDate) {
  try { Stop-Process -Id $ownedRow.ProcessId -Force -ErrorAction Stop }
  catch { if (Get-Process -Id $ownedRow.ProcessId -ErrorAction SilentlyContinue) { throw } }
 }
}
$ownedCurrentRows = @(Get-CimInstance Win32_Process)
foreach ($ownedRow in $ownedTree) {
 if (@($ownedCurrentRows | Where-Object { $_.ProcessId -eq $ownedRow.ProcessId -and $_.CreationDate -eq $ownedRow.CreationDate }).Count) { throw 'OWNED_OBSERVER_REMAINS' }
}
$ownedEvidence.stopped=$true
$ownedEvidence.verifiedAt=[DateTime]::UtcNow.ToString('o')
[System.IO.File]::WriteAllText($ownedRecordPath,($ownedEvidence | ConvertTo-Json -Depth 5),[System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{ status='PASS'; exactOwnedProcessesAbsent=$ownedTree.Count; remoteChanges=0 } | ConvertTo-Json
