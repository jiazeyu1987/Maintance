import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../..')
const script = fs.readFileSync(path.join(root, 'ops/deploy/publish-int-ruoyi.ps1'), 'utf8').replace(/\r\n/g, '\n')

test('frontend-only deploy-release does not require database SQL entries', () => {
  const deployBlockStart = script.indexOf("if ($Mode -eq 'deploy-release') {")
  assert.notEqual(deployBlockStart, -1)
  const deployBlockEnd = script.indexOf('Set-PublishRuntimeDefaultsForTarget', deployBlockStart)
  assert.notEqual(deployBlockEnd, -1)
  const deployBlock = script.slice(deployBlockStart, deployBlockEnd)

  const componentIndex = deployBlock.indexOf('$Component = Resolve-DeployReleasePackageComponent')
  const backendFlagIndex = deployBlock.indexOf("$publishBackend = $Component -in @('full', 'intruoyi', 'backend')")
  const sqlReadIndex = deployBlock.indexOf('$requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts')
  const backendGuardIndex = deployBlock.indexOf("if ($publishBackend) {\n        $requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts\n        Assert-RequiredDatabaseSqlScriptsInRelease")

  assert.ok(componentIndex >= 0)
  assert.ok(backendFlagIndex > componentIndex)
  assert.ok(sqlReadIndex > backendFlagIndex)
  assert.ok(backendGuardIndex >= 0)
  assert.ok(sqlReadIndex > backendGuardIndex)
})
