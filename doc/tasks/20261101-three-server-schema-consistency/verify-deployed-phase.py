"""Fresh per-target proof after the actual persisted release task succeeds."""
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

root=Path('C:/SpugHandoff/release')
task=Path(__file__).parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime, validate_gxp_runtime
env=sys.argv[1]
assert env in ('test','prod','backup')
opened=len(sys.argv)>2 and sys.argv[2]=='open'
tag=json.loads((task/'candidate.json').read_text('utf-8'))['releaseTag']
config=json.loads((root/'executor.private.json').read_text('utf-8'))
with sqlite3.connect('file:'+str(Path(config['stateDir'])/'state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
package=next(p for p in state['packages'] if p['releaseTag']==tag)
manifest=json.loads((Path(package['directory'])/'manifest.json').read_text('utf-8'))
assert manifest['IMAGE_TAG']==manifest['releaseTag']==tag
assert manifest['gitCommit']=='fb88105af40e4ee6366a20dae2df721f1de2dcb0'
outcome=package['outcomes'][env]
deployed=next(j for j in state['jobs'] if j['id']==outcome['deployment']['jobId'])
assert deployed['status']=='succeeded' and deployed['releaseTag']==tag and deployed['target']==env
proof=outcome['technical']
owner=next(j for j in state['jobs'] if j['id']==proof['jobId'])
assert owner['status']=='succeeded' and proof['status']=='passed' and proof['packageSha256']==package['packageSha256']
assert all(proof['checks'][k]['status']=='passed' for k in ('version','upgrade','login'))
if opened and env!='test':
    assert outcome['acceptance']['status']=='passed'
runtime=Runtime(config)
actual=runtime.observe(env)
health=runtime.health(env,tag)
validate_gxp_runtime(health['writerControls'],'DEVELOPMENT_DISABLED')
assert actual['releaseTag']==tag and actual['images']==proof['checks']['version']['images']
assert actual['images']=={role:manifest['images'][role]['id'] for role in ('backend','frontend')}
# The ordinary Spug runtime creates containers by immutable image ID, not compose/.env tags.
assert all(actual['components'][role]['image']==manifest['images'][role]['id'] for role in ('backend','frontend'))
assert actual['backendHealth']['status']=='UP' and actual['frontendHttpStatus']==200
assert actual['maintenance'] is (False if opened or env=='test' else True)
assert actual['schemaSha256']==proof['checks']['upgrade']['schemaSha256']
assert actual['ledgerSha256']==proof['checks']['upgrade']['ledgerSha256']
assert actual['gxpAudit']['pendingRestart'] is False
if env!='test':
    basis=outcome['deployment']['validationBasis']
    assert basis['sourceVerifiedSchemaSha256']==basis['upgradedSchemaSha256']==actual['schemaSha256'] and basis['upgradedLedgerSha256']==actual['ledgerSha256']
    assert basis['packageSha256']==package['packageSha256'] and basis['targetEnvironment']==env
if env=='prod':
    assert deployed['workflowPolicy']['recoveryMode']=='external'
    remote=json.loads((task/('remote-'+deployed['id']+'-latest.json')).read_text('utf-8'))
    assert remote['action']=='deploy' and remote['status']=='succeeded'
    assert remote['externalRecovery']['mode']=='external' and remote['externalRecovery']['operatorConfirmed'] is True
    assert remote['externalRecovery']['releaseTag']==tag and remote['checkpointRecordExists'] is False
    assert not state['environments'][env].get('recoveryPoint')
else:
    remote=json.loads((task/('remote-'+deployed['id']+'-latest.json')).read_text('utf-8'))
    assert remote['checkpointRecordExists'] is True
report=dict(status='PASS',time=datetime.now().astimezone().isoformat(),environment=env,releaseTag=tag,
    deploymentJobId=deployed['id'],technicalJobId=proof['jobId'],packageSha256=package['packageSha256'],
    images=actual['images'],schemaSha256=actual['schemaSha256'],ledgerSha256=actual['ledgerSha256'],
    effectiveImageReferences={role:actual['components'][role]['image'] for role in ('backend','frontend')},manifestImageTag=manifest['IMAGE_TAG'],
    runtimeConfigSha256=actual['runtimeConfigSha256'],backendHealth='UP',frontendHttpStatus=200,
    maintenance=actual['maintenance'],entryUrl=health['entryUrl'],realPlaywrightLogin=True,
    configuredGxpAuditMode=health['writerControls']['configuredGxpAuditMode'],gxpAuditMode=health['writerControls']['gxpAuditMode'],
    pendingRestart=False,recoveryMode='external' if env=='prod' else 'checkpoint',
    businessRegressionPerformed=False)
(task/('deployed-phase-'+env+('-open' if opened else '-maintenance')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
