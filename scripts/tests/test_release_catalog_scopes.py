import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from ops.release.release_source_catalog import SourceCatalogError, release_paths
from ops.release.release_migration_manifest import build_migration_manifest
from ops.release.release_preflight_plan import build_preflight_plan


def fixture(tmp_path, *, declared_scope=''):
    root = tmp_path/'backend/sql/mysql'
    root.mkdir(parents=True)
    name = '20260811_site_equipment.sql'
    sql = ('-- release-migration: allowedEnvironments=test,backup,prod; type=data; riskLevel=low'
           + declared_scope + '\nSELECT 1;\n').encode()
    (root/name).write_bytes(sql)
    scope = dict(file=name,sha256=hashlib.sha256(sql).hexdigest(),allowedPublishScopes=['with-data'],
                 reason='One-time site equipment configuration; requires separate business-data approval.')
    catalog = dict(schemaVersion='release-sql-sources/v2',migrations=[name],sourceReferences=[],migrationScopes=[scope])
    save(root,catalog)
    return root,catalog


def save(root,catalog):
    (root/'release-sources.json').write_text(json.dumps(catalog),'utf-8')


def collect(root):
    paths,_=release_paths(root)
    return build_migration_manifest(root,sql_paths=paths)


def plan(migrations,ledger=None):
    return build_preflight_plan(migrations,ledger or {},target_environment='test',publish_scope='app-release')


def test_scoped_sql_remains_packaged_with_original_hash_and_visible_skip_reason(tmp_path):
    root,catalog=fixture(tmp_path)
    migrations=collect(root)
    assert migrations[0]['sha256']==catalog['migrationScopes'][0]['sha256']
    result=plan(migrations)
    assert result['status']=='passed'
    assert result['items'][0]['action']=='SKIP_SCOPE_EXCLUDED'
    assert catalog['migrationScopes'][0]['reason'] in result['items'][0]['reason']
    assert result['items'][0]['scopeReason']==catalog['migrationScopes'][0]['reason']


@pytest.mark.parametrize('change,match',[
    ({'file':'20260101_unknown.sql'},'Unknown/duplicate'),
    ({'sha256':'0'*64},'missing or changed'),
    ({'allowedPublishScopes':['app-release']},'explicitly with-data'),
    ({'reason':''},'reason required'),
])
def test_invalid_or_widening_scope_registry_fails(tmp_path,change,match):
    root,catalog=fixture(tmp_path)
    catalog['migrationScopes'][0].update(change)
    save(root,catalog)
    with pytest.raises(SourceCatalogError,match=match):collect(root)


def test_catalog_cannot_widen_explicit_sql_scope(tmp_path):
    root,_=fixture(tmp_path,declared_scope='; allowedPublishScopes=app-release')
    with pytest.raises(SourceCatalogError,match='cannot widen'):collect(root)


def test_generic_schema_consumer_cannot_treat_excluded_data_as_satisfied(tmp_path):
    root,catalog=fixture(tmp_path)
    data=collect(root)[0]
    schema=dict(data,migrationId='20260812_generic_schema',type='schema',allowedPublishScopes=[],
                dependsOn=[data['migrationId']],scopeReason='')
    result=plan([data,schema])
    assert result['status']=='blocked'
    assert [item['action'] for item in result['items']]==['SKIP_SCOPE_EXCLUDED','BLOCKED_SCOPE_DEPENDENCY']
    # A separately classified site-data consumer may also be excluded; it does
    # not become an APPLIED dependency or authorize a new execution path.
    schema.update(type='data',allowedPublishScopes=['with-data'])
    assert [item['action'] for item in plan([data,schema])['items']]==['SKIP_SCOPE_EXCLUDED','SKIP_SCOPE_EXCLUDED']


@pytest.mark.parametrize('status,checksum,action',[
    ('APPLIED',None,'SKIP_ALREADY_APPLIED'),('APPLIED','0'*64,'BLOCKED_CHECKSUM_MISMATCH'),
    ('FAILED',None,'BLOCKED_LEDGER_STATE'),('RUNNING',None,'BLOCKED_LEDGER_STATE'),
])
def test_scope_does_not_hide_historical_checksum_or_partial_failure(tmp_path,status,checksum,action):
    root,_=fixture(tmp_path)
    migrations=collect(root)
    row=migrations[0]
    result=plan(migrations,{row['migrationId']:{'status':status,'sha256':checksum or row['sha256']}})
    assert result['items'][0]['action']==action


def test_powershell_metadata_collector_matches_python_scope_and_reason(tmp_path):
    shell=shutil.which('pwsh') or shutil.which('powershell')
    assert shell, 'PowerShell is required to verify both release collectors'
    root,catalog=fixture(tmp_path)
    dependency='20260810_prerequisite'
    (root/(dependency+'.sql')).write_text('-- release-migration: type=schema; riskLevel=low\nSELECT 1;\n','utf-8')
    catalog['migrations'].append(dependency+'.sql')
    catalog['migrationDependencies']=[dict(file=catalog['migrationScopes'][0]['file'],
        sha256=catalog['migrationScopes'][0]['sha256'],dependsOn=[dependency],reason='Explicit prerequisite for immutable historical SQL.')]
    hook_name='20260812_mes_route_version_snapshot_identity_enforce.sql'
    hook_bytes=b'-- release-migration: type=schema; riskLevel=high\nSELECT 1;\n'
    (root/hook_name).write_bytes(hook_bytes)
    catalog['migrations'].append(hook_name)
    catalog['migrationContracts']=[dict(file=hook_name,sha256=hashlib.sha256(hook_bytes).hexdigest(),approvedHook='route-snapshot-identity-v1',reason='Offline candidate CLI required before immutable enforcement.')]
    save(root,catalog)
    sql=root/catalog['migrationScopes'][0]['file']
    publish=Path(__file__).resolve().parents[2]/'ops/deploy/publish-int-ruoyi.ps1'
    script=tmp_path/'verify-scope.ps1'
    script.write_text('''param([string]$Publish,[string]$Backend,[string]$Sql,[string]$ReleaseScripts)
$ErrorActionPreference='Stop'
function Fail([string]$Message) { throw $Message }
$tokens=$null
$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Publish,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw 'Publish script parse failed' }
foreach ($name in @('Read-ReleaseMigrationMetadata','Get-ReleaseDatabaseSqlRoots')) {
    $function=$ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    Invoke-Expression $function.Extent.Text
}
function Invoke-ProcessCapture {
    param([string]$FilePath,[string[]]$ArgumentList,[string]$WorkingDirectory)
    $output=& $FilePath @ArgumentList
    return @{ExitCode=$LASTEXITCODE;StdOut=($output -join "`n")}
}
$releaseMigrationAllowedTypes=@('schema','data','menu','config','permission','seed')
$backendRepo=$Backend
$maintenanceReleaseScriptRoot=$ReleaseScripts
$script:ReleaseSqlSourceCatalog=''
$script:ReleaseSqlMigrationScopes=@()
$roots=@(Get-ReleaseDatabaseSqlRoots)
if ($roots.Count -ne 1 -or $roots[0].IncludeFiles.Count -ne 3) { throw 'Explicit catalog selection was not used' }
Read-ReleaseMigrationMetadata -SqlPath $Sql | ConvertTo-Json -Depth 8 -Compress
''','utf-8')
    result=subprocess.run([shell,'-NoProfile','-File',str(script),str(publish),str(root.parents[1]),str(sql),str(publish.parent.parent/'release')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    metadata=json.loads(result.stdout)
    python=next(item for item in collect(root) if item['migrationId']==sql.stem)
    assert metadata['allowedPublishScopes']==python['allowedPublishScopes']
    assert metadata['scopeReason']==python['scopeReason']
    assert metadata['dependsOn']==python['dependsOn']==[dependency]
    result=subprocess.run([shell,'-NoProfile','-File',str(script),str(publish),str(root.parents[1]),str(root/hook_name),str(publish.parent.parent/'release')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['approvedHook']==next(m for m in collect(root) if m['migrationId']==Path(hook_name).stem)['approvedHook']=='route-snapshot-identity-v1'
    successor_root,_,old_id,new_id=legacy_summary_fixture(tmp_path/'legacy')
    script.write_text(script.read_text('utf-8').replace('IncludeFiles.Count -ne 3','IncludeFiles.Count -ne 5'),'utf-8')
    result=subprocess.run([shell,'-NoProfile','-File',str(script),str(publish),str(successor_root.parents[1]),
                           str(successor_root/(new_id+'.sql')),str(publish.parent.parent/'release')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    metadata=json.loads(result.stdout)
    successor=next(m for m in collect(successor_root) if m['migrationId']==new_id)
    assert metadata['approvedHook']==successor['approvedHook']=='route-snapshot-identity-v2'
    assert metadata['supersedes']==successor['supersedes']==[old_id]
    assert metadata['dependsOn']==successor['dependsOn']



@pytest.mark.parametrize('change,match',[
    ({'dependsOn':['missing']},'Known non-self'),
    ({'dependsOn':['20260811_site_equipment']},'Known non-self'),
    ({'sha256':'0'*64},'missing or changed'),
    ({'reason':''},'reason required'),
])
def test_invalid_catalog_dependency_fails_closed(tmp_path,change,match):
    root,catalog=fixture(tmp_path)
    (root/'20260810_base.sql').write_text('-- release-migration: type=schema\nSELECT 1;\n','utf-8')
    catalog['migrations'].append('20260810_base.sql')
    entry=dict(file=catalog['migrationScopes'][0]['file'],sha256=catalog['migrationScopes'][0]['sha256'],
               dependsOn=['20260810_base'],reason='Explicit prerequisite added without rewriting SQL.')
    entry.update(change)
    catalog['migrationDependencies']=[entry]
    save(root,catalog)
    with pytest.raises(SourceCatalogError,match=match):collect(root)


def test_catalog_dependency_preserves_original_edge_and_rejects_cycle(tmp_path):
    root,catalog=fixture(tmp_path,declared_scope='; dependsOn=20260810_base')
    (root/'20260810_base.sql').write_text('-- release-migration: type=schema\nSELECT 1;\n','utf-8')
    (root/'20261022_gate.sql').write_text('-- release-migration: type=schema\nSELECT 1;\n','utf-8')
    catalog['migrations']+=['20260810_base.sql','20261022_gate.sql']
    catalog['migrationDependencies']=[dict(file='20260811_site_equipment.sql',
        sha256=catalog['migrationScopes'][0]['sha256'],dependsOn=['20261022_gate'],reason='Gate must precede old immutable schema.')]
    save(root,catalog)
    migrations=collect(root)
    target=next(x for x in migrations if x['migrationId']=='20260811_site_equipment')
    assert target['dependsOn']==['20260810_base','20261022_gate']
    gate=next(x for x in migrations if x['migrationId']=='20261022_gate')
    gate['dependsOn']=['20260811_site_equipment']
    with pytest.raises(Exception,match='[Cc]ycl'):plan(migrations)


def test_catalog_runtime_contract_binds_immutable_sql_and_collectors(tmp_path):
    root,catalog=fixture(tmp_path)
    name='20260812_mes_route_version_snapshot_identity_enforce.sql'
    body=b'-- release-migration: type=schema; riskLevel=high\nSELECT 1;\n'
    (root/name).write_bytes(body)
    catalog['migrations'].append(name)
    entry=dict(file=name,sha256=hashlib.sha256(body).hexdigest(),approvedHook='route-snapshot-identity-v1',reason='Offline candidate CLI strictly checks stored snapshot identities before enforcement.')
    catalog['migrationContracts']=[entry]
    save(root,catalog)
    assert next(m for m in collect(root) if m['migrationId']==Path(name).stem)['approvedHook']=='route-snapshot-identity-v1'
    entry['approvedHook']='unreviewed'
    save(root,catalog)
    with pytest.raises(SourceCatalogError,match='Unreviewed'):collect(root)
    entry['approvedHook']='route-snapshot-identity-v1';entry['sha256']='0'*64
    save(root,catalog)
    with pytest.raises(SourceCatalogError,match='changed'):collect(root)


def test_rollback_reference_preserves_bytes_without_forward_apply_or_ledger_entry(tmp_path):
    root,catalog=fixture(tmp_path)
    name='20260817_mes_pqc_item_level_task_identity_rollback.sql'
    body=b'-- release-migration: type=schema; riskLevel=high\nALTER TABLE task DROP COLUMN item;\n'
    (root/name).write_bytes(body)
    catalog['sourceReferences']=[dict(file=name,kind='rollback-only',sha256=hashlib.sha256(body).hexdigest(),reason='Explicit reverse-only recovery SQL must never execute in forward upgrades.')]
    save(root,catalog)
    paths,refs=release_paths(root)
    assert root/name not in paths and refs[0]['sha256']==hashlib.sha256(body).hexdigest()
    assert all(i['migrationId']!=Path(name).stem for i in plan(collect(root))['items'])
    (root/name).write_bytes(body+b'-- changed')
    with pytest.raises(SourceCatalogError,match='changed'):release_paths(root)


def legacy_summary_fixture(tmp_path, *, successor_metadata=''):
    root,catalog=fixture(tmp_path)
    old='20260812_mes_route_version_snapshot_identity_enforce'
    new='20261023_mes_route_snapshot_legacy_summary_enforce'
    prerequisites=['20260812_mes_route_version_snapshot_identity','20260718_controlled_content_lifecycle']
    bodies={mid:('-- release-migration: allowedEnvironments=test,prod,backup; type=schema; '
                 'riskLevel=high\nSELECT 1;\n').encode() for mid in [old,*prerequisites]}
    bodies[new]=('-- release-migration: allowedEnvironments=test,prod,backup; type=schema; '
                 'riskLevel=high; requiresTargetPreflight=true; applyOrder=10; supersedes='+old+'; dependsOn='
                 +','.join(prerequisites)+successor_metadata+'\nSELECT 2;\n').encode()
    for mid,body in bodies.items():
        (root/(mid+'.sql')).write_bytes(body)
        catalog['migrations'].append(mid+'.sql')
    catalog['migrationContracts']=[dict(file=mid+'.sql',sha256=hashlib.sha256(bodies[mid]).hexdigest(),
        approvedHook=hook,reason='Reviewed offline identity contract; preserve the immutable predecessor and audit exact legacy summaries.')
        for mid,hook in [(old,'route-snapshot-identity-v1'),(new,'route-snapshot-identity-v2')]]
    save(root,catalog)
    return root,catalog,old,new


def test_explicit_legacy_successor_preserves_original_and_does_not_claim_old_applied(tmp_path):
    root,catalog,old,new=legacy_summary_fixture(tmp_path)
    migrations=collect(root)
    by_id={m['migrationId']:m for m in migrations}
    assert by_id[old]['approvedHook']=='route-snapshot-identity-v1'
    assert by_id[new]['approvedHook']=='route-snapshot-identity-v2'
    assert by_id[old]['sha256']==catalog['migrationContracts'][0]['sha256']
    for ledger in [{},{old:{'status':'APPLIED','sha256':by_id[old]['sha256']}}]:
        before=json.dumps(ledger,sort_keys=True)
        actions={item['migrationId']:item['action'] for item in plan(migrations,ledger)['items']}
        assert actions[old]=='SKIP_IMMUTABLE'
        assert actions[new]=='APPLY'
        assert json.dumps(ledger,sort_keys=True)==before
    result=plan(migrations,{old:{'status':'FAILED','sha256':by_id[old]['sha256']}})
    assert next(i for i in result['items'] if i['migrationId']==old)['action']=='BLOCKED_LEDGER_STATE'
    assert result['status']=='blocked'
    later=dict(by_id[old],migrationId='20260829_later_conversion',dependsOn=[old],approvedHook='')
    ordered=plan([*migrations,later])['items']
    positions={item['migrationId']:i for i,item in enumerate(ordered)}
    assert positions['20260812_mes_route_version_snapshot_identity'] < positions[new]
    assert positions['20260718_controlled_content_lifecycle'] < positions[new]
    assert positions[new] < positions[later['migrationId']]


@pytest.mark.parametrize('field,value',[
    ('supersedes',[]),('supersedes',['20260812_mes_route_version_snapshot_identity']),
    ('requiresTargetPreflight',False),('type','data'),('dependsOn',[]),('applyOrder',None),('applyOrder',1000),
])
def test_legacy_hook_cannot_bind_without_reviewed_successor_metadata(tmp_path,field,value):
    from ops.release.release_source_catalog import apply_migration_contracts
    root,_,_,new=legacy_summary_fixture(tmp_path)
    migrations=collect(root)
    next(m for m in migrations if m['migrationId']==new)[field]=value
    with pytest.raises(SourceCatalogError,match='explicit immutable predecessor'):
        apply_migration_contracts(root,migrations)


def test_v2_contract_cannot_replace_v1_or_attach_to_other_sql(tmp_path):
    root,catalog,_,_=legacy_summary_fixture(tmp_path)
    catalog['migrationContracts'][0]['approvedHook']='route-snapshot-identity-v2'
    save(root,catalog)
    with pytest.raises(SourceCatalogError,match='Unreviewed'):collect(root)


def test_old_package_catalog_still_collects_original_v1_without_successor(tmp_path):
    root,catalog,old,new=legacy_summary_fixture(tmp_path)
    (root/(new+'.sql')).unlink()
    catalog['migrations'].remove(new+'.sql')
    catalog['migrationContracts']=catalog['migrationContracts'][:1]
    save(root,catalog)
    migrations=collect(root)
    entry=next(m for m in migrations if m['migrationId']==old)
    assert entry['approvedHook']=='route-snapshot-identity-v1'
    assert next(i for i in plan(migrations)['items'] if i['migrationId']==old)['action']=='APPLY'
