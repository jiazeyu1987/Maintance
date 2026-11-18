"""Independently bind current original program to this deployment's successful restoration."""
from pathlib import Path
import json,sqlite3,sys,subprocess
root=Path('C:/SpugHandoff/release');live=root/'source/ops/spug/release-center';sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
from backend_patch_agent import verify_unchanged
job_id=sys.argv[1]
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==job_id)
assert job['action']=='backend-patch-restore' and job['status']=='succeeded'
original=next(j for j in state['jobs'] if j['id']==job['payload']['originalJobId'])
assert original['backendRestoredBy']==job_id and original['resolution']['jobId']==job_id
r=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))
actual=r.call(job['target'],'backend-patch-observe')
assert actual==job['result']['observation']
before=original['backendOrigin'];verify_unchanged(before,actual)
assert actual['backendJarSha256']==before['backendJarSha256']
assert actual['backendMetadata']==before['backendMetadata'] and actual['backendPatchTag']==before['backendPatchTag']
assert actual['backendHealth']=='UP' and actual['frontendHttpStatus']==200
assert actual['gxpAuditMode']=='DEVELOPMENT_DISABLED'
p=r.profile(job['target'])
source=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=source+'\np='+repr(p)+'''\nprint(json.dumps(dict(readOnly=sql(p,'SELECT @@global.read_only,@@global.super_read_only;'))))\n'''
v=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert v.returncode==0 and json.loads(v.stdout)['readOnly']=='0\t0'
report=dict(status='PASS',restorationJobId=job_id,originalDeploymentId=original['id'],releaseTag=actual['releaseTag'],
            jarSha256=actual['backendJarSha256'],schemaSha256=actual['schemaSha256'],ledgerSha256=actual['ledgerSha256'],
            backendHealth='UP',frontendHttpStatus=200,readOnly='0/0',gxpAuditMode=actual['gxpAuditMode'])
output=Path(__file__).with_name('restoration-'+job_id+'.json');assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
