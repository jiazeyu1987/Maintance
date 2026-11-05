"""Read-only exact port ownership and recovery-controller startup evidence."""
import concurrent.futures
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE=r'''
import datetime,json,pathlib,subprocess,urllib.request,urllib.error
out={'host':HOST,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'proxies':[], 'units':[], 'logs':{},'errors':{}}
def run(args,timeout=10):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 return {'exitCode':p.returncode,'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace')}
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  cmd=(process/'cmdline').read_bytes().split(b'\0')
  if not cmd or not cmd[0].endswith(b'docker-proxy') or b'48081' not in cmd:continue
  status=(process/'status').read_text()
  out['proxies'].append({'pid':int(process.name),'argv':[s.decode() for s in cmd if s],
   'parentPid':int(next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('PPid:')))})
 except OSError:pass
if HOST.endswith('.57'):
 out['network']=run(['docker','network','inspect','intruoyi-runtime_intruoyi_net'])
 for name in ('intruoyi-backend','intruoyi-frontend'):out['logs'][name]=run(['docker','logs','--tail','45',name])
 roots=[pathlib.Path('/etc/systemd/system'),pathlib.Path('/usr/lib/systemd/system')]
 for root in roots:
  for path in root.glob('*.service'):
   try:
    text=path.read_text()
    if 'spug-intruoyi-57-safe-20261024-v1' in text or '32657' in text:out['units'].append({'path':str(path),'text':text})
   except OSError:pass
else:
 root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
 receipt=json.loads((root/'target-installation.json').read_bytes())
 control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
 headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
 req=urllib.request.Request('http://127.0.0.1:43658/selections?targetConfigRef='+receipt['targetConfigRef'],headers=headers)
 try:
  with urllib.request.urlopen(req,timeout=15) as response:out['targetSelections']=json.load(response)
 except urllib.error.HTTPError as error:out['targetSelections']={'httpStatus':error.code,'body':error.read().decode('utf-8','replace')}
print(json.dumps(out))
'''

def observe(profile):
 host=profile['host']
 args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=10','root@'+host,profile['python']+' -B -']
 result=subprocess.run(args,input=('HOST='+repr(host)+'\n'+REMOTE).encode(),capture_output=True,timeout=40)
 if result.returncode:
  (PRIVATE/(host+'-boot-conflicts-error.private.txt')).write_bytes(result.stderr+result.stdout)
  raise RuntimeError('BOOT_CONFLICTS_READ_FAILED_'+host)
 raw=json.loads(result.stdout)
 (PRIVATE/(host+'-boot-conflicts.private.json')).write_text(json.dumps(raw),encoding='utf-8')
 report={k:v for k,v in raw.items() if k not in ('logs','units','network')}
 report['unitPaths']=[r['path'] for r in raw['units']]
 if 'network' in raw and raw['network']['exitCode']==0:
  networks=json.loads(raw['network']['stdout'])
  report['networkContainers']={cid:{k:row.get(k) for k in ('Name','IPv4Address')} for network in networks for cid,row in (network.get('Containers') or {}).items()}
 # Expose only known frontend startup signatures, never application log content.
 report['logSignatures']={name:{term:(row['stdout']+row['stderr']).lower().count(term) for term in ('host not found in upstream','bind()','connection refused','error','exception','started yudao')} for name,row in raw['logs'].items()}
 (TASK/(host+'-boot-conflicts.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 return report

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for report in pool.map(observe,[p for p in PROFILES if p['host'] in ('172.30.30.57','172.30.30.58')]):print(json.dumps(report,ensure_ascii=False))
