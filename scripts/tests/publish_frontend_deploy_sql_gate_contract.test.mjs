import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'

const root = path.resolve(import.meta.dirname, '../..')
const script = fs.readFileSync(path.join(root, 'ops/deploy/publish-int-ruoyi.ps1'), 'utf8').replace(/\r\n/g, '\n')

test('complete-core deployment resolves the fixed profile before mandatory database SQL collection', () => {
  const deployBlockStart = script.indexOf('Info "Deploying release package: $ReleaseTag"')
  assert.notEqual(deployBlockStart, -1)
  const deployBlockEnd = script.indexOf('Set-PublishRuntimeDefaultsForTarget', deployBlockStart)
  assert.notEqual(deployBlockEnd, -1)
  const deployBlock = script.slice(deployBlockStart, deployBlockEnd)

  const componentIndex = deployBlock.indexOf('$Component = Resolve-DeployReleasePackageComponent')
  const backendFlagIndex = deployBlock.indexOf("$publishBackend = $Component -in @('full', 'intruoyi')")
  const sqlReadIndex = deployBlock.indexOf('$requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts')
  const backendGuardIndex = deployBlock.indexOf("if ($publishBackend) {\n        $requiredDatabaseSqlScripts = Get-ReleasePackageDatabaseSqlScripts\n        Assert-RequiredDatabaseSqlScriptsInRelease")

  assert.ok(componentIndex >= 0)
  assert.ok(backendFlagIndex > componentIndex)
  assert.ok(sqlReadIndex > backendFlagIndex)
  assert.ok(backendGuardIndex >= 0)
  assert.ok(sqlReadIndex > backendGuardIndex)
  assert.ok(script.includes('DEPLOY_COMPONENT_OVERRIDE_FORBIDDEN'))
  assert.ok(script.includes("[ValidateSet('full', 'intruoyi')]"))
})
