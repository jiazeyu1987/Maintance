"""Capture current identity, source-chain admission and host runtime read-only."""
import argparse
import hashlib
import json
from common import PRIVATE, SOURCE, TASK, active_source_installation, remote, write

SCRIPT = r'''
import datetime,hashlib,json,os,pathlib,subprocess,urllib.request
root=pathlib.Path(ROOT)
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,documents={},pins={},admissions={})
def document(path):
 p=pathlib.Path(path);raw=p.read_bytes();value=json.loads(raw)
 out['documents'][str(p)]=value
 out['pins'][str(p)]=dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 return value
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=25)
 assert p.returncode==0,'READONLY_COMMAND_FAILED'
 return p.stdout
receipt=document(root/'target-installation.json')
owner=document(receipt['ownerConfigurationPin']['path'])
control=document(receipt['controlConfigurationPin']['path'])
for field in ('ownerConfigurationPin','controlConfigurationPin'):
 assert out['pins'][receipt[field]['path']]==receipt[field],'INSTALLED_CONFIGURATION_PIN_CHANGED'
out['targetConfigRef']=receipt['targetConfigRef']
out['serviceProperties']=run(['systemctl','show',receipt['service'],'-p','ActiveState','-p','SubState','-p','MainPID','-p','LimitNOFILE']).decode()
engine=pathlib.Path(owner['formalModuleDirectory']).parent
package=document(engine/'package.json')
out['packageFilesMatch']=all(hashlib.sha256((engine/n).read_bytes()).hexdigest()==v for n,v in package['files'].items())
out['packageFileCount']=len(package['files'])
out['containers']=json.loads(run(['docker','inspect',*run(['docker','ps','-aq','--no-trunc']).decode().split()]))
out['mountinfo']=pathlib.Path('/proc/self/mountinfo').read_text(encoding='utf-8')
out['fstabSha256']=hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest()
out['capacity']={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in (str(root),'/opt/intruoyi/runtime')}
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
out['activeReservation']=document(active) if active.exists() else None
out['processes']=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  raw=(p/'cmdline').read_bytes()
  if str(root).encode() not in raw and b'spug-intruoyi-57-safe-20261024-v1' not in raw:continue
  out['processes'].append(dict(pid=int(p.name),commandSha256=hashlib.sha256(raw).hexdigest(),command=raw.decode().replace('\0',' '),stat=(p/'stat').read_text()))
 except (FileNotFoundError,ProcessLookupError):continue
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def admit(name,configuration,target=None):
 headers=json.loads(pathlib.Path(configuration['authCredentialRef']['path']).read_bytes())['headers']
 url='http://127.0.0.1:'+str(configuration['listenPort'])+'/selections'
 if target:url+='?targetConfigRef='+target
 try:
  with opener.open(urllib.request.Request(url,headers=headers),timeout=85) as response:
   out['admissions'][name]=dict(httpStatus=response.status,body=json.load(response))
 except Exception as error:out['admissions'][name]=dict(errorType=type(error).__name__)
admit('target',control,receipt['targetConfigRef'])
if HOST.endswith('.57'):
 sourcecontrol=document(SOURCE_CONTROL_PATH)
 for reference in sourcecontrol['sourceConfigurations'].values():
  sourceowner=document(reference['path'])
  for source in sourceowner['sources'].values():
   for field in ('configurationPath','sourceIdentityPath'):
    if field in source:document(source[field])
 admit('source',sourcecontrol)
out['http']={}
services=owner['targets'][receipt['targetConfigRef']]['services']
backend=next(s for s in services if s['role']=='backend')
frontend=next(s for s in services if s['role']=='frontend')
for name,url in [('backend','http://'+backend['ip']+':48081/actuator/health'),('frontend','http://'+HOST+':'+('38081' if HOST.endswith('.59') else '8081')+'/')]:
 try:
  with opener.open(url,timeout=12) as response:
   out['http'][name]=dict(httpStatus=response.status)
   if name=='backend':out['http'][name]['status']=json.load(response).get('status')
 except Exception as error:out['http'][name]=dict(errorType=type(error).__name__)
print(json.dumps(out))
'''


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['57','58','59']);parser.add_argument('--phase',default='baseline');args=parser.parse_args()
    assert args.phase.replace('-','').isalnum(),'PHASE_INVALID'
    PRIVATE.mkdir(parents=True,exist_ok=True)
    host='172.30.30.'+args.suffix
    destination=PRIVATE/(args.phase+'-'+args.suffix+'.private.json')
    assert not destination.exists(),'BASELINE_ALREADY_EXISTS'
    root=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
    sourcepath=active_source_installation()['controlConfigurationPin']['path']
    value=remote(host,'SOURCE_CONTROL_PATH='+repr(sourcepath)+'\nHOST='+repr(host)+'\nROOT='+repr(root)+'\n'+SCRIPT,240)
    write(destination,value)
    owner=next(v for v in value['documents'].values() if value['targetConfigRef'] in v.get('targets',{}))
    target=owner['targets'][value['targetConfigRef']]
    ids={s['id']:s['role'] for s in target['services']}
    roles=[dict(role=ids[r['Id']],id=r['Id'],image=r['Image'],running=r['State']['Running'],pid=r['State']['Pid'],startedAt=r['State']['StartedAt'],health=r['State'].get('Health',{}).get('Status')) for r in value['containers'] if r['Id'] in ids]
    report={k:value[k] for k in ('observedAt','host','targetConfigRef','serviceProperties','packageFilesMatch','packageFileCount','capacity','fstabSha256','http','admissions')}
    report.update(containerCount=len(value['containers']),roles=roles,activeReservation=bool(value['activeReservation']),processes=[{k:r[k] for k in ('pid','commandSha256')} for r in value['processes']],privateBaselineSha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    write(TASK/(args.phase+'-'+args.suffix+'.json'),report)
    print(json.dumps(report,ensure_ascii=False))
