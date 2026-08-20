import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = process.cwd()
const script = fs.readFileSync(path.join(root, 'ops/deploy/publish-int-ruoyi.ps1'), 'utf8')

test('publish script writes release-info.json into frontend dist', () => {
  assert.match(script, /Write-FrontendReleaseInfo/)
  assert.match(script, /release-info\.json/)
  assert.match(script, /dist-intruoyi-test/)
  assert.match(script, /Assert-FrontendBuildStaticAssetContract/)
})

test('release-info contains the same manifest-level release metadata', () => {
  assert.match(script, /releaseTag\s*=\s*\$PackageTag/)
  assert.match(
    script,
    /changeSet\s*=\s*New-ReleaseChangeSetManifest -PackageTag \$PackageTag -SourceRepos \$SourceRepos/
  )
  assert.match(script, /sourceRepos\s*=\s*\$SourceRepos/)
})

test('release change-set is derived from the exact frozen source commits', () => {
  assert.match(script, /function Get-ReleaseSourceRepoPath/)
  assert.match(script, /function New-ReleaseSourceCommitChangeEntries/)
  assert.match(script, /function Get-ReleaseGitValue/)
  assert.match(script, /Invoke-ProcessCapture -FilePath 'git'/)
  assert.match(script, /i18n\.logOutputEncoding=UTF-8/)
  assert.match(script, /Manifest v1 requires git metadata for \$\{Purpose\}/)
  assert.doesNotMatch(script, /& git -C \$RepoPath @Arguments/)
  assert.match(script, /\[array\]\$SourceRepos/)
  assert.match(script, /'show', '-s', '--format=%s', '--no-show-signature', \$commit/)
  assert.match(script, /Missing source commit for release change notes/)
  assert.match(script, /Missing commit subject for release change notes/)
  assert.match(script, /shortCommit\s*=\s*\$commit\.Substring\(0, 12\)/)
  assert.match(script, /summary\s*=\s*\(@\(\$commitChanges\.subjects\) -join ' \| '\)/)
  assert.match(script, /\$items \+= @\(\$commitChanges\.items\)/)
  assert.match(script, /items\s*=\s*@\(\$items\)/)
  assert.match(
    script,
    /changeSet\s*=\s*New-ReleaseChangeSetManifest -PackageTag \$PackageTag -SourceRepos \$sourceRepos/
  )
})

test('release change-set labels use unicode-safe concatenation for manifest and release-info', () => {
  assert.match(script, /\$fullWidthColon\s*=\s*ConvertTo-ReleaseUnicodeText -CodePoints @\(65306\)/)
  assert.match(script, /\('\{0\}\{1\}\{2\}' -f \$releasePackageLabel, \$fullWidthColon, \$PackageTag\)/)
  assert.match(script, /\('\{0\}\{1\}\{2\}' -f \$componentScopeLabel, \$fullWidthColon, \$Component\)/)
  assert.match(script, /\('\{0\}\{1\}\{2\} \{3\}' -f \$commitLabel, \$fullWidthColon, \$shortCommit, \$subject\)/)
})
