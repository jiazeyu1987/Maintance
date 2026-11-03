"""Verify one completed deployment's journal, owned fence and both real starts."""
from pathlib import Path
import json,sqlite3,subprocess,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
environment,identity=sys.argv[1:]
root=Path('C:/SpugHandoff/release')
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))
selection=json.loads(Path(__file__).with_name('selected-release.json').read_text('utf-8'))
with sqlite3.connect('file:'+str(root/'state/state.sqlite3')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']==identity)
assert job['action']=='backend-patch-deploy' and job['target']==environment and job['status']=='succeeded'
assert job['releaseTag']==selection['backendPatchTag']
for key,value in dict(readonlyProbeVerified=True,normalRuntimeWritesAllowed=True,databaseSchemaChanged=False,migrationsExecuted=False).items():assert job['result'][key] is value
operation=next(o for o in reversed(job['remoteOperations']) if o['action']=='backend-patch-deploy')
receipt=runtime.call(environment,'inspect-operation',originalOperationId=operation['operationId'],originalJobId=identity)
assert receipt['status']=='succeeded' and receipt['worker']=='stopped'
assert receipt['result']['readonlyProbeVerified'] is True and receipt['result']['databaseSchemaChanged'] is False
profile=runtime.profile(environment)
inspector=(live/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
code=inspector+'\nfrom pathlib import Path\np='+repr(profile)+'\njob='+repr(identity)+'\ntag='+repr(job['releaseTag'])+r'''
folder=Path(p['stagingRoot'])/'backend-patches'/tag/job
fence=json.loads((folder/'database-fence.json').read_text('utf-8'))
deployment=json.loads((folder/'deployment.json').read_text('utf-8'))
assert fence['status']=='released' and deployment['status']=='succeeded'
assert deployment['readonlyProbeVerified'] is True and deployment['databaseSchemaChanged'] is False
assert deployment['migrationsExecuted'] is False and deployment['normalRuntimeWritesAllowed'] is True
assert fence['databaseId']==inspect(p['database'])['Id']
marker=b'IntRuoyi backend startup completed; release metadata: /actuator/release'
starts={}
for phase,name in [('probe',p['backend']+'-probe-'+job),('normal',p['backend'])]:
    container=inspect(name)
    values=dict(v.split('=',1) for v in container['Config']['Env'])
    maintenance=values.get('INTRUOYI_RELEASE_MAINTENANCE')=='true'
    result=subprocess.run(['docker','logs',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert result.returncode==0
    count=(result.stdout+result.stderr).count(marker)
    assert count==1
    assert maintenance==(phase=='probe')
    assert container['State']['Running']==(phase=='normal')
    assert container['State']['ExitCode']!=137
    starts[phase]=dict(startupLogCount=count,maintenance=maintenance,running=container['State']['Running'])
print(json.dumps(dict(fenceStatus=fence['status'],readonlyProbeVerified=True,databaseSchemaChanged=False,migrationsExecuted=False,normalRuntimeWritesAllowed=True,starts=starts)))
'''
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert result.returncode==0,'Remote proof failed; original deployment is not replayed'
proof=json.loads(result.stdout)
report=dict(status='PASS',environment=environment,releaseTag=job['releaseTag'],jobId=identity,
            operationId=operation['operationId'],operationStatus=receipt['status'],worker=receipt['worker'],**proof)
output=Path(__file__).with_name('patch-remote-proof-'+identity+'.json');assert not output.exists()
output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
