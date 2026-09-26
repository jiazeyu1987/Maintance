"""One immutable migration package, three real isolated MySQL starting points.

Application payloads and platform prerequisites are contract fixtures, not a
deployed product. Database collection, plans, lease/fence SQL and migrations
below run the production implementation against the task-owned MySQL engine.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

from ops.release.release_preflight_plan import build_target_bound_plan
from release_test_runtime import mysql_runtime, run_mysql, application_backend_root, runtime_settings
from test_release_full_package_contract import ROOT, SCRIPT, _functions, write_complete_package, rebind_package
from test_scheduler_smoke_linux_payload_integration import ps


def checked_sql(sql, database=None):
    result = run_mysql(sql, database)
    assert result.returncode == 0, result.stderr
    return result.stdout


def file_bytes(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def transport(runtime, database):
    return _functions() + f"""
[Console]::InputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);$OutputEncoding=[Text.UTF8Encoding]::new($false)
foreach($fn in @($ast.EndBlock.Statements|Where-Object{{$_ -is [Management.Automation.Language.FunctionDefinitionAst]}})){{Invoke-Expression $fn.Extent.Text}}
function Info([string]$Message) {{}}
$script:TargetMySqlDatabase='{database}';$script:ReleaseErrorMessageMaxLength=2048
$script:ReleaseOperationExecutorHost='task';$script:ReleaseOperationExecutorPid='1';$script:ReleaseOperationExecutorIdentity='task-integration'
$script:ReleaseOperationLockHeld=$false;$script:ReleaseOperationLegacyLockHeld=$false;$script:ReleaseOperationLockReleasing=$false
$script:ReleaseMigrationFailureErrors=@();$script:executed=@()
function Invoke-SshCapture {{param([string]$Command,[switch]$IgnoreExitCode)
 if($Command -match "test -f '[^']*/(m[1-4]\\.sql)'"){{$script:executed+=$Matches[1]}}
 $bridge='docker() {{ [ "$1" = exec ] && [ "$2" = -i ] && [ "$3" = intruoyi-mysql ] || return 94; shift 3; "$@"; }}' + "`n"
 $r=Invoke-ProcessCaptureWithInput -FilePath docker -ArgumentList @('exec','-i','{runtime.container_id}','sh','-s') -StandardInput (($bridge+$Command) -replace "`r`n","`n")
 @{{Ok=($r.ExitCode -eq 0);Output=(($r.StdOut+"`n"+$r.StdErr).Trim());ExitCode=$r.ExitCode}}
}}
function Invoke-SshCommand {{param($Command) $r=Invoke-SshCapture $Command;if(-not $r.Ok){{throw (Protect-ReleaseSensitiveText $r.Output)}}}}
function Invoke-SshCommandWithInput {{param($Command,$StandardInput) Invoke-SshCommand ("cat <<'TASK_INPUT' | "+$Command+"`n"+$StandardInput+"`nTASK_INPUT")}}
"""


def collector(runtime, database, environment, mount):
    encoded = base64.b64encode(json.dumps(mount).encode()).decode()
    # Host identity is the real isolated container identity. The empty platform
    # list explicitly scopes this test to DB integration, not server readiness.
    return transport(runtime, database) + f"""
$Environment='{environment}'
function Read-ReleaseTargetSnapshot {{param([switch]$Verify)
 $db=Get-ReleaseTargetDatabaseSnapshot
 @{{schemaVersion='release-deploy-target-state/v1';capturedAt=[DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.fffZ');targetEnvironment=$Environment;
 hostIdentity=@{{host='{runtime.container_name}';machineId='{runtime.container_id}'}};
 databaseIdentity=$db.databaseIdentity;schemaEvidence=$db.schemaEvidence;migrationLedgerComplete=$true;migrationLedger=@($db.migrationLedger);
 nonSecretConfig=@{{MYSQL_DATABASE='{database}';IMAGE_TAG='task-historical'}};
 persistentMounts=@([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))|ConvertFrom-Json);platformPrerequisites=@()}}
}}
"""


def test_same_immutable_package_upgrades_three_real_baselines_without_rewriting_history(tmp_path):
    runtime = mysql_runtime()
    config = runtime_settings()
    outer = json.loads(subprocess.run(['docker', 'inspect', runtime.container_id], capture_output=True,
        text=True, encoding='utf-8', check=True).stdout)[0]
    mounts_before = outer['Mounts']
    actual = mounts_before[0]
    mount = dict(role='mysql', type=actual['Type'], source=actual['Name'],
                 destination=actual['Destination'], identity=actual['Source'])
    root = tmp_path / 'release-t7-m1-m4'
    manifest = write_complete_package(root)
    (root / 'required-sql/001.sql').unlink()
    entries = []
    for n in range(1, 5):
        content = (f'-- release-migration: type=schema; allowedEnvironments=test,prod,backup; dependsOn={"" if n == 1 else "m"+str(n-1)}\n'
                   f'CREATE TABLE task_m{n}(id BIGINT PRIMARY KEY, revision INT NOT NULL);\n'
                   f'INSERT INTO task_m{n} VALUES({n},{n});\n').encode()
        path = f'required-sql/m{n}.sql'
        (root / path).write_bytes(content)
        entries.append(dict(migrationId=f'm{n}', file=path, type='schema', sha256=hashlib.sha256(content).hexdigest(),
                            allowedEnvironments=['test','prod','backup'], dependsOn=[] if n == 1 else [f'm{n-1}']))
    manifest.update(requiredSql=copy.deepcopy(entries), migrationPlan=copy.deepcopy(entries), database={'schemaMigrations':entries},
                    targetRequirements={'platformPrerequisites':[]})
    rebind_package(root, manifest)
    before = file_bytes(root)
    package_identities = set()
    summaries = []
    for environment, applied in [('test', 3), ('prod', 1), ('backup', 2)]:
        database = 'release_t7_' + environment + '_' + uuid.uuid4().hex[:8]
        remote = '/tmp/' + config.prefix + 't7-' + uuid.uuid4().hex
        control = tmp_path / environment
        control.mkdir()
        checked_sql(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4;')
        try:
            for name in ['20260613_infra_release_migration_state.sql','20260921_infra_release_operation_lock_lease_fencing.sql']:
                checked_sql((application_backend_root()/'sql/mysql'/name).read_text(encoding='utf-8'), database)
            checked_sql("""CREATE TABLE task_tenant(id BIGINT PRIMARY KEY,name VARCHAR(50),code VARCHAR(40),enabled BOOLEAN);
CREATE TABLE historical_orders(id BIGINT PRIMARY KEY,tenant_id BIGINT,number VARCHAR(40),amount DECIMAL(12,2),memo TEXT,created_at DATETIME);
CREATE TABLE historical_attachments(id BIGINT PRIMARY KEY,tenant_id BIGINT,order_id BIGINT,url VARCHAR(255),sha256 CHAR(64),bytes BIGINT);
INSERT INTO task_tenant VALUES(122,'task tenant','t7-preserve',1);
INSERT INTO historical_orders VALUES(401,122,'t7-original-order',123.45,'original complete row','2026-01-02 03:04:05');
INSERT INTO historical_attachments VALUES(901,122,401,'task://original/attachment','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',1234);""", database)
            for entry in entries[:applied]:
                checked_sql((root/entry['file']).read_text(encoding='utf-8'), database)
                checked_sql(f"INSERT INTO infra_release_migration(release_tag,migration_id,file_name,sha256,target_environment,status,operation_id) VALUES('historical','{entry['migrationId']}','{entry['file']}','{entry['sha256']}','{environment}','APPLIED','original-operation');", database)
            history_query = 'SELECT * FROM task_tenant ORDER BY id; SELECT * FROM historical_orders ORDER BY id; SELECT * FROM historical_attachments ORDER BY id;'
            historical = checked_sql(history_query, database)
            ids = ','.join("'"+e['migrationId']+"'" for e in entries[:applied])
            skip_query = f'SELECT * FROM infra_release_migration WHERE migration_id IN ({ids}) ORDER BY id;'
            original_ledger = checked_sql(skip_query, database)
            code = collector(runtime, database, environment, mount)
            observed = ps(code+'Read-ReleaseTargetSnapshot|ConvertTo-Json -Depth 50 -Compress', timeout=120)
            assert observed.returncode == 0, observed.stderr
            snapshot = json.loads(observed.stdout)
            plans = [build_target_bound_plan(root/'manifest.json', snapshot, executor_path=SCRIPT,
                     target_environment=environment, publish_scope='app-release') for _ in range(2)]
            assert plans[0] == plans[1] and plans[0]['status'] == 'passed'
            plan = plans[0]
            expected = [f'm{n}' for n in range(applied+1,5)]
            assert [e['migrationId'] for e in plan['items'] if e['action']=='APPLY'] == expected
            package_identities.add((plan['binding']['packageDigest'],plan['binding']['manifestDigest']))
            snapshot_path = control/'input.json'
            snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
            plan_path = control/'preflight-plan.json'
            for _ in range(2):
                result = subprocess.run([sys.executable,'-X','utf8',str(ROOT/'ops/release/release_preflight_plan.py'),
                    '--manifest',str(root/'manifest.json'),'--target-state',str(snapshot_path),'--executor',str(SCRIPT),
                    '--target-environment',environment,'--publish-scope','app-release','--output',str(plan_path)],
                    capture_output=True,text=True,encoding='utf-8',timeout=60)
                assert result.returncode == 0, result.stderr
                assert json.loads(plan_path.read_text(encoding='utf-8')) == plan
            # Provision only the task transport's SQL fixture; payload bytes are unchanged.
            uploaded = subprocess.run(['docker','exec','-i',runtime.container_id,'sh','-s'],
                input=(f"set -eu\nmkdir '{remote}'\n"+''.join(f"printf %s '{base64.b64encode((root/e['file']).read_bytes()).decode()}' | base64 -d >'{remote}/{e['migrationId']}.sql'\n" for e in entries)).encode(),
                capture_output=True,timeout=30)
            assert uploaded.returncode == 0, uploaded.stderr.decode()
            execute = ps(code+f"""
$Mode='deploy-release';$ReleaseTag='{root.name}';$releaseDir='{root.as_posix()}';$releasePublishScope='app-release';$deployControlLocalRoot='{control.as_posix()}'
$scriptDir='{(ROOT/'ops/deploy').as_posix()}';$maintenanceReleaseScriptRoot='{(ROOT/'ops/release').as_posix()}';$remoteRequiredSqlDir='{remote}'
$releaseMigrationAllowedTypes=@('schema','data','menu','config','permission','seed')
function Invoke-CheckedCommand {{param($FilePath,$ArgumentList) $output=& $FilePath @ArgumentList 2>&1;if($LASTEXITCODE -ne 0){{throw ($output -join "`n")}}}}
Invoke-ReleaseOperationLockAcquire
Write-ReleasePreflightPlan -Verify
Invoke-RequiredDatabaseSqlScripts
Invoke-ReleaseOperationLockRelease -Status 'APPLIED'
@{{executed=@($script:executed);snapshot=(Read-ReleaseTargetSnapshot)}}|ConvertTo-Json -Depth 50 -Compress
""", timeout=180)
            assert execute.returncode == 0, execute.stderr
            completed = json.loads(execute.stdout)
            assert completed['executed'] == [e+'.sql' for e in expected]
            ledger = completed['snapshot']['migrationLedger']
            assert [(e['migrationId'],e['sha256'],e['status']) for e in ledger] == [(e['migrationId'],e['sha256'],'APPLIED') for e in entries]
            assert checked_sql(history_query,database) == historical
            assert checked_sql(skip_query,database) == original_ledger
            for n in range(1,5):
                assert checked_sql(f'SELECT * FROM task_m{n};',database).strip() == f'{n}\t{n}'
            assert checked_sql('SELECT status FROM infra_release_operation_lock;',database).strip() == 'APPLIED'
            assert file_bytes(root) == before
            summaries.append(dict(environment=environment, applied=expected, planDigest=plan['planDigest'],
                historicalSha256=hashlib.sha256(historical.encode()).hexdigest(), ledgerSha256=hashlib.sha256(original_ledger.encode()).hexdigest()))
        finally:
            cleaned = subprocess.run(['docker','exec',runtime.container_id,'rm','-rf','--',remote],capture_output=True,timeout=30)
            assert cleaned.returncode == 0, cleaned.stderr.decode()
            checked_sql(f'DROP DATABASE `{database}`;')
    assert len(package_identities) == 1
    final = json.loads(subprocess.run(['docker','inspect',runtime.container_id],capture_output=True,text=True,encoding='utf-8',check=True).stdout)[0]
    assert final['Mounts'] == mounts_before
    assert file_bytes(root) == before
    (tmp_path/'three-baseline-evidence.json').write_text(json.dumps({'packageDigests':list(package_identities),'targets':summaries,'mounts':mounts_before},indent=2),encoding='utf-8')
