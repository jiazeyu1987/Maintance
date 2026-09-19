$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$repo = 'D:\IntRuoyiWorktree\r260820f\a'
$branch = 'refs/heads/codex/20260821-pqc-nav-tscheck-release-fix'
$evidenceDir = 'D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260819-test-only-head-release\evidence'
$tempIndex = Join-Path $evidenceDir ('app-fix-temp-index-r260820g-' + [Guid]::NewGuid().ToString('N'))
$msgPath = Join-Path $evidenceDir 'app-fix-commit-msg-r260820g.txt'
$outPath = Join-Path $evidenceDir 'app-fix-commit-r260820g.json'
$paths = @(
  'IntRuoyiFronted/src/views/mes/pro/feedback/FrontlineFixedTemplatePanel.vue',
  'doc/tasks/20260821-pqc-nav-tscheck-release-fix/task.md',
  'doc/tasks/20260821-pqc-nav-tscheck-release-fix/execution-log.md'
)

$oldIndex = $env:GIT_INDEX_FILE
$env:GIT_INDEX_FILE = $tempIndex
try {
  git -C $repo read-tree HEAD
  if ($LASTEXITCODE -ne 0) { throw 'read-tree failed' }

  git -C $repo add -- $paths
  if ($LASTEXITCODE -ne 0) { throw 'temp-index add failed' }

  $tree = (git -C $repo write-tree).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($tree)) { throw 'write-tree failed' }

  $parent = (git -C $repo rev-parse HEAD).Trim()
  [System.IO.File]::WriteAllText($msgPath, "任务: 修复PQC工序导航类型检查`n", [System.Text.UTF8Encoding]::new($false))

  $commit = (git -C $repo commit-tree $tree -p $parent -F $msgPath).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($commit)) { throw 'commit-tree failed' }
}
finally {
  $env:GIT_INDEX_FILE = $oldIndex
}

git -C $repo update-ref $branch $commit
if ($LASTEXITCODE -ne 0) { throw 'update-ref failed' }

$summary = [ordered]@{
  branch = $branch
  parent = $parent
  commit = $commit
  tempIndexUsed = $tempIndex
  reason = 'worktree index.lock from aborted git add; used temporary index without deleting lock'
}
[System.IO.File]::WriteAllText($outPath, ($summary | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))
Get-Content -Encoding utf8 $outPath
Write-Output '--- commit files ---'
git -C $repo show --name-status --oneline --no-renames $commit
