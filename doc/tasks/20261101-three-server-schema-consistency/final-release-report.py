"""Verify one complete release chain and actual full table metadata consistency."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from publication_proof import verify_publication

task=Path(__file__).parent
root=Path('C:/SpugHandoff/release')
candidate=json.loads((task/'candidate.json').read_text('utf-8'))
tag=candidate['releaseTag']
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
package=next(p for p in state['packages'] if p['releaseTag']==tag)
assert package['stage']=='completed'
assert package['gitCommit']=='fb88105af40e4ee6366a20dae2df721f1de2dcb0'
assert not any(j['status']=='running' for j in state['jobs'])
folder=Path(package['directory'])
manifest=json.loads((folder/'manifest.json').read_text('utf-8'))
assert manifest['releaseSettings']['gxpAuditMode']=='DEVELOPMENT_DISABLED'
assert manifest['IMAGE_TAG']==manifest['releaseTag']==tag

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

for base in (folder,Path(package['nasDirectory'])):
    assert digest(base/'release.tar')==package['packageSha256']
    assert digest(base/'manifest.json')==package['manifestSha256']
schema=json.loads((task/'schema-after.json').read_text('utf-8'))
assert all(not diff for diff in schema['differences'].values())
expected=schema['environments']['test']['schema']
assert len(expected['tables'])==885
targets={}
for env in ('test','prod','backup'):
    proof=json.loads((task/('deployed-phase-'+env+'-open.json')).read_text('utf-8'))
    gxp=json.loads((task/('target-gxp-'+env+'-'+tag+'.json')).read_text('utf-8'))
    assert proof['status']==gxp['status']=='PASS' and proof['releaseTag']==gxp['releaseTag']==tag
    assert proof['packageSha256']==package['packageSha256'] and proof['maintenance'] is False
    assert gxp['savedMode']==gxp['runtimeMode']=='DEVELOPMENT_DISABLED'
    assert gxp['auditEnabled'] is False and gxp['pendingRestart'] is False and gxp['realPlaywrightLogin'] is True
    assert schema['environments'][env]['schema']==expected
    forward=schema['environments'][env]['forwardMigration']
    assert forward and all(row.split('\t')==['20261101_dcc_source_governance_all_environments','0a5c2494efe4b2dd41497180b9b52a3a045137e1b63743593512f5717d9fc7d5','APPLIED'] for row in forward)
    outcome=package['outcomes'][env]
    assert outcome['technical']['status']=='passed'
    job=next(j for j in state['jobs'] if j['id']==outcome['deployment']['jobId'])
    assert job['status']=='succeeded' and job['releaseTag']==tag
    if env=='test':
        tested=next(j for j in state['jobs'] if j['id']==outcome['technical']['jobId'])
        assert tested['action']=='mark-tested' and tested['status']=='succeeded'
    else:
        assert outcome['acceptance']['status']=='passed'
        basis=outcome['deployment']['validationBasis']
        assert basis['sourceVerifiedSchemaSha256']==basis['upgradedSchemaSha256']==proof['schemaSha256']
    operations=[op for op in job['remoteOperations'] if op['action']=='deploy']
    assert len(operations)==1
    receipt=json.loads((task/('remote-'+job['id']+'-latest.json')).read_text('utf-8'))
    assert receipt['operationId']==operations[0]['operationId']
    assert receipt['status']=='succeeded' and receipt['originalWorkerAlive'] is False
    assert receipt['checkpointRecordExists'] is (env!='prod')
    if env=='prod':
        assert receipt['externalRecovery']['mode']=='external' and receipt['externalRecovery']['operatorConfirmed'] is True
    assert state['environments'][env]['releaseTag']==tag and state['environments'][env]['maintenance'] is False
    targets[env]=dict(proof,tableCount=885,fullTableMetadataSha256=schema['environments'][env]['sha256'],
        operationStatus='SUCCESS',deploymentOperationId=operations[0]['operationId'],savedGxpMode=gxp['savedMode'],
        runtimeGxpMode=gxp['runtimeMode'],auditEnabled=False,forwardMigrationApplied=True)
assert len({p['schemaSha256'] for p in targets.values()})==1
assert all(p['images']==targets['test']['images'] for p in targets.values())
local=json.loads((task/'target-gxp-local-local.json').read_text('utf-8'))
assert local['status']=='PASS' and local['savedMode']==local['runtimeMode']=='DEVELOPMENT_DISABLED'
assert local['auditEnabled'] is False and local['pendingRestart'] is False
build=next(j for j in state['jobs'] if j['id']==candidate['buildJobId'])
verify_publication(state,candidate,package)
result=dict(status='PASS',time=datetime.now().astimezone().isoformat(),releaseTag=tag,sourceCommit=package['gitCommit'],
    maintenanceCommit=candidate['maintenanceCommit'],packageBytes=(folder/'release.tar').stat().st_size,
    packageSha256=package['packageSha256'],manifestSha256=package['manifestSha256'],localAndNasOriginalMatch=True,
    tablesColumnsIndexesConstraintsMatch=True,targets=targets,localGxpClosed=True,rehearsalRequired=False,
    productionFullCheckpointCaptured=False,businessWriteRegressionPerformed=False,intMainMerged=False,gitPushed=False,
    windowsServiceInstalled=False,buildWorktreeCleanup=build.get('buildWorktreeCleanup'))
(task/'release-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
