"""Parse and exercise only the offline executor rejection functions locally."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class OfflineExecutorSnapshotGateTests(unittest.TestCase):
    def test_v1_v2_cannot_silently_bypass_offline_cli_or_terminal_readiness(self):
        shell = shutil.which('powershell')
        self.assertIsNotNone(shell, 'Windows PowerShell is required for the execution gate test')
        source = Path(__file__).resolve().parents[2] / 'deploy/publish-int-ruoyi.ps1'
        script = r'''
param($source, $testRoot)
$tokens=$null
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($source,[ref]$tokens,[ref]$errors)
if ($errors.Count -ne 0) { throw 'Executor parse failed' }
foreach ($name in @('Read-ReleasePreflightPlan','Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement')) {
 $node=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
 if ($null -eq $node) {throw 'Execution gate function missing'}
 Invoke-Expression $node.Extent.Text
}
function Fail($message) { throw $message }
function Invoke-RouteSnapshotIdentityMigrationCommand {throw 'FORBIDDEN_LEGACY_CLI'}
$deployControlLocalRoot=$testRoot
$releasePublishScope='backend'
foreach ($id in @('20260812_mes_route_version_snapshot_identity_enforce','20261023_mes_route_snapshot_legacy_summary_enforce')) {
 foreach ($action in @('APPLY','SKIP_ALREADY_APPLIED')) {
  $plan=@{schemaVersion='release-deploy-plan/v1';planKind='deploy';binding=@{};planDigest='verified-elsewhere';publishScope='backend';status='passed';items=@(@{migrationId=$id;action=$action})}
  [System.IO.File]::WriteAllText((Join-Path $testRoot 'preflight-plan.json'),($plan|ConvertTo-Json -Depth 5))
  $blocked=$false
  try {Read-ReleasePreflightPlan | Out-Null} catch {
   if ($_.Exception.Message -notlike '*terminal readiness require the reviewed Spug*') {throw}
   $blocked=$true
  }
  if (-not $blocked) {throw 'Offline executor incorrectly accepted snapshot package'}
 }
}
$plan.items=@(@{migrationId='20260829_mes_old_form_template_binding_switch';action='APPLY'})
[System.IO.File]::WriteAllText((Join-Path $testRoot 'preflight-plan.json'),($plan|ConvertTo-Json -Depth 5))
$blocked=$false
try {Read-ReleasePreflightPlan | Out-Null} catch {
 if ($_.Exception.Message -notlike '*execution-time zero-scope gate*') {throw}
 $blocked=$true
}
if (-not $blocked) {throw 'Known legacy conversion bypassed zero-scope gate'}
foreach ($hook in @('route-snapshot-identity-v1','route-snapshot-identity-v2')) {
 $blocked=$false
 try {Invoke-RouteSnapshotIdentityBackfillBeforeEnforcement -Item @{approvedHook=$hook}} catch {
  if ($_.Exception.Message -notlike '*requires the reviewed Spug candidate-only CLI executor*') {throw}
  $blocked=$true
 }
 if (-not $blocked) {throw 'Hook silently bypassed the reviewed CLI'}
}
Write-Output 'OFFLINE_SNAPSHOT_GATES_PASSED'
'''
        with tempfile.TemporaryDirectory() as directory:
            runner=Path(directory)/'test.ps1'
            runner.write_text(script,'utf-8')
            run=subprocess.run([shell,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(runner),str(source),directory],capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('OFFLINE_SNAPSHOT_GATES_PASSED',run.stdout)


if __name__ == '__main__':
    unittest.main()
