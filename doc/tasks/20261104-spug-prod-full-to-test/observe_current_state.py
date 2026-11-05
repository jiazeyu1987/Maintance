"""Bounded read-only source/target state. Raw configuration stays private."""
import concurrent.futures
import datetime
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-full-to-test-20261104')
PRIVATE.mkdir(exist_ok=True)
PROFILES = json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
REMOTE = r'''
import hashlib,json,os,pathlib,subprocess,urllib.request
root=pathlib.Path(ROOT)
out={'host':HOST,'loadAverage':pathlib.Path('/proc/loadavg').read_text().split()[:3],
     'root':ROOT,'documents':{},'operationDocuments':{},'processes':[],'errors':{}}
if HOST.endswith('.57'):
 controlpath=root/'configuration/control.json'
else:
 receipt=json.loads((root/'target-installation.json').read_bytes())
 out['documents']['installation']=receipt
 controlpath=pathlib.Path(receipt['controlConfigurationPin']['path'])
 out['documents']['owner']=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
 out['serviceState']=subprocess.check_output(['systemctl','is-active',receipt['service']],timeout=8).decode().strip()
control=json.loads(controlpath.read_bytes());out['documents']['control']=control
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
url='http://127.0.0.1:'+str(control['listenPort'])+'/selections'
if not HOST.endswith('.57'):url+='?targetConfigRef='+receipt['targetConfigRef']
try:
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(urllib.request.Request(url,headers=headers),timeout=25) as response:out['selections']=json.load(response)
except Exception as e:out['errors']['selections']=type(e).__name__

# Only inspect the exact application or installed target services, never broad restart/stop.
names=['intruoyi-backend'] if HOST.endswith('.57') else [s['id'] for s in out['documents']['owner']['targets'][receipt['targetConfigRef']]['services']]
try:
 p=subprocess.run(['docker','inspect',*names],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5 if HOST.endswith('.57') else 15)
 if p.returncode:out['errors']['dockerInspect']='EXIT_'+str(p.returncode)
 else:out['containers']=json.loads(p.stdout)
except subprocess.TimeoutExpired:out['errors']['dockerInspect']='TIMEOUT'

for name in ('ledger','operations','replacement-state'):
 directory=root/name
 if not directory.is_dir():continue
 out[name+'Entries']=sorted(p.name for p in directory.iterdir())
 candidates=list(directory.glob('**/*.json'))
 if len(candidates)>300:out['errors'][name]='READ_BOUND_EXCEEDED';continue
 for path in candidates:
  if path.stat().st_size>1000000:continue
  try:out['operationDocuments'][str(path)]=json.loads(path.read_bytes())
  except (OSError,ValueError):out['errors'][str(path)]='UNREADABLE_OPERATION_DOCUMENT'
for directory in pathlib.Path('/proc').iterdir():
 if not directory.name.isdigit():continue
 try:
  cmd=(directory/'cmdline').read_bytes()
  if ROOT.encode() not in cmd:continue
  status=(directory/'status').read_text()
  out['processes'].append({'pid':int(directory.name),'state':next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('State:')),'commandSha256':hashlib.sha256(cmd).hexdigest()})
 except (OSError,StopIteration):pass
print(json.dumps(out))
'''


def summary(value):
    result={key:value[key] for key in ('host','root','loadAverage','serviceState','errors','processes','ledgerEntries','operationsEntries','replacement-stateEntries') if key in value}
    control=value.get('documents',{}).get('control',{})
    result['controlKeys']=sorted(control)
    result['controlPaths']={key:item for key,item in control.items() if isinstance(item,str) and item.startswith('/')}
    result['selections']=value.get('selections')
    result['containerStates']=[{'name':row['Name'],'id':row['Id'],'state':{key:row['State'].get(key) for key in ('Status','Running','Restarting','ExitCode','OOMKilled','StartedAt','FinishedAt')},'health':row['State'].get('Health',{}).get('Status')} for row in value.get('containers',[])]
    result['operations']=[]
    for name,doc in value.get('operationDocuments',{}).items():
        if not isinstance(doc,dict):continue
        selected={key:doc[key] for key in ('schemaVersion','operationId','action','status','state','phase','createdAt','completedAt','pid','runnerPid','errorCode') if key in doc}
        if isinstance(doc.get('request'),dict):selected['request']={k:doc['request'].get(k) for k in ('operationId','action','sourceConfigRef','targetConfigRef','recoveryPointRef')}
        result['operations'].append({'path':name,**selected})
    return result


def observe(profile):
    host=profile['host'];suffix=host.split('.')[-1]
    root='/var/lib/docker/intruoyi-data/'+('spug-intruoyi-57-safe-20261024-v1' if suffix=='57' else 'spug-main-restore-20261104-v3')
    script='HOST='+repr(host)+'\nROOT='+repr(root)+'\n'+REMOTE
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+host,profile['python']+' -B -']
    p=subprocess.run(args,input=script.encode('utf-8'),capture_output=True,timeout=55)
    if p.returncode:
        (PRIVATE/(host+'-observation-error.private.txt')).write_bytes(p.stderr+p.stdout)
        return {'host':host,'errors':{'sshObservation':'EXIT_'+str(p.returncode)}}
    raw=json.loads(p.stdout)
    (PRIVATE/(host+'-observation.private.json')).write_text(json.dumps(raw),encoding='utf-8')
    return summary(raw)


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(observe,[p for p in PROFILES if p['host'] in ('172.30.30.57','172.30.30.58')]))
    report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'readOnly':True,'hosts':results}
    (TASK/'current-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for result in results:print(json.dumps(result,ensure_ascii=False))
