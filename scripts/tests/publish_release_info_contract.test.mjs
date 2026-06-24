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
  assert.match(script, /changeSet\s*=\s*New-ReleaseChangeSetManifest/)
  assert.match(script, /sourceRepos\s*=\s*\$SourceRepos/)
})
