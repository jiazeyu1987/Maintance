"""Run the candidate endpoint resolver against actual original pinned configurations."""
import json
from common import PRIVATE,TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess,sys,types
from types import SimpleNamespace
root=pathlib.Path(ROOT)
def read(p):return json.loads(pathlib.Path(p).read_bytes())
receipt=read(root/'target-installation.json');owner=read(receipt['ownerConfigurationPin']['path']);control=read(receipt['controlConfigurationPin']['path']);target=owner['targets'][receipt['targetConfigRef']]
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
candidate=types.ModuleType('candidate_readiness');exec(compile(CODE,'candidate_readiness','exec'),candidate.__dict__)
rows={}
for s in target['services']:
 p=subprocess.run(['docker','inspect',s['id']],capture_output=True,timeout=20);assert p.returncode==0
 rows[s['role']]=json.loads(p.stdout)[0]
profile=None
if SUFFIX=='58':
 row=rows['frontend'];mount=next(m for m in row['Mounts'] if m['Destination']=='/etc/nginx/conf.d/default.conf')
 reference=next(p for p in target['mainApplication']['configurationPins'] if p['path']==mount['Source'])
 profile=dict(schemaVersion='RegisteredMainFrontendReadiness/v1',mode='HOST_NGINX',containerId=row['Id'],
  serviceConfigurationDigest=target['mainApplication']['serviceConfigurationDigests']['frontend'],
  address='172.30.30.58',port=8081,configurationPin=reference)
def docker(args):
 p=subprocess.run(['docker',*args],capture_output=True,timeout=20);assert p.returncode==0;return p.stdout
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},frontend_readiness=profile,
 inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity),docker=docker)
endpoints={role:candidate.endpoint(native,role) for role in candidate.ROLES}
probes={role:candidate.probe(url,role,10) for role,url in endpoints.items()} if SUFFIX=='59' else {}
assert not probes or all(p['ready'] for p in probes.values())
from recovery_main_target import verify_runtime
native.snapshots={};verify_runtime(native,states=False)
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host='172.30.30.'+SUFFIX,
 sourceSha256=hashlib.sha256(CODE.encode()).hexdigest(),targetConfigRef=receipt['targetConfigRef'],
 ownerConfigurationPin=receipt['ownerConfigurationPin'],endpoints=endpoints,actualProtocolProbes=probes,
 stoppedServicesProbed=False,profile=profile,actualRuntimeContractVerified=True,serverWrites=False)
print(json.dumps(out))
'''
if __name__=='__main__':
 import sys
 suffix=sys.argv[1];assert suffix in ('58','59')
 values=dict(ROOT=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',
  SUFFIX=suffix,CODE=(TASK.parents[2]/'ops/recovery/recovery_main_health.py').read_text(encoding='utf8'))
 result=remote('172.30.30.'+suffix,'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,90)
 write(TASK/('frontend-readiness-candidate-'+suffix+'.json'),result);print(json.dumps(result))
