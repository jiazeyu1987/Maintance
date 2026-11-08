"""Read the actual installed health contract and retained 369 failure, without mutation."""
import json
from common import PRIVATE, TASK, remote, write

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess,sys
from types import SimpleNamespace
root=pathlib.Path(ROOT)
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
receipt=read(root/'target-installation.json');owner=read(receipt['ownerConfigurationPin']['path']);control=read(receipt['controlConfigurationPin']['path'])
target=owner['targets'][receipt['targetConfigRef']]
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_health import endpoint
from recovery_main_target import service_configuration_digest
rows={}
for service in target['services']:
 p=subprocess.run(['docker','inspect',service['id']],capture_output=True,timeout=15);assert p.returncode==0
 rows[service['role']]=json.loads(p.stdout)[0]
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity))
services=[]
for role,row in rows.items():
 result=None
 if role in ('minio','backend','frontend'):
  try:result=dict(endpoint=endpoint(native,role),status='PASS')
  except Exception as e:result=dict(status='FAIL',errorCode=getattr(e,'code',type(e).__name__))
 services.append(dict(role=role,id=row['Id'],image=row['Image'],registeredIp=native.config_services[role]['ip'],exposedPorts=row['Config'].get('ExposedPorts'),portBindings=row['HostConfig'].get('PortBindings'),networkMode=row['HostConfig']['NetworkMode'],networks={k:dict(ip=v.get('IPAddress'),ipam=v.get('IPAMConfig')) for k,v in row['NetworkSettings']['Networks'].items()},running=row['State']['Running'],startedAt=row['State']['StartedAt'],configurationMatches=service_configuration_digest(row)==target['mainApplication']['serviceConfigurationDigests'][role],healthEndpoint=result))
documents={};pins=[]
if SUFFIX=='58':
 operation='smallapp-b4f35606e4854516960050a76473038b'
 for folder in (root/'recovery-operations'/operation,root/'ledger'/operation,root/'replacement-state'/operation):
  if folder.is_dir():
   for p in folder.rglob('*.json'):
    if p.stat().st_size<8*1024*1024:documents[str(p)]=read(p);pins.append(pin(p))
 for operation in ('smallapp-c21bb7ce9f5b4668b850c37a80964786',):
  for name in ('recovery-clearance.json','recovery-consumption.json'):
   p=root/'replacement-state'/operation/name
   if p.is_file():documents[str(p)]=read(p);pins.append(pin(p))
 p=pathlib.Path('/var/lib/spug-restore-resources/active.json')
 if p.is_file():documents[str(p)]=read(p);pins.append(pin(p))
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host='172.30.30.'+SUFFIX,services=services,documents=documents,pins=pins)))
'''

if __name__=='__main__':
 import sys
 suffix=sys.argv[1];assert suffix in ('58','59')
 value=remote('172.30.30.'+suffix,'ROOT='+repr(('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3')+'\nSUFFIX='+repr(suffix)+'\n'+SCRIPT,90)
 write(PRIVATE/('main-health-endpoint-'+suffix+'.private.json'),value)
 public={k:v for k,v in value.items() if k!='documents'}
 public['failureDocuments']=[dict(path=p,fields=sorted(d),**{k:v for k,v in d.items() if k in ('state','actualExitCode','failureCode','mutationDispatched','partialTargetRetained','retryPermitted','consumedByOperationId')}) for p,d in value['documents'].items()]
 write(TASK/('main-health-endpoint-'+suffix+'.json'),public)
 print(json.dumps(public))
