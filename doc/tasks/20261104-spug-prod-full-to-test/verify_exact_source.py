"""Verify exact configured source containers and baseline HTTP, read-only."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE=r'''
import concurrent.futures,json,os,pathlib,subprocess,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
capture=json.loads((root/'configuration/capture.json').read_bytes());source=capture['source']
roles={'mysql':source['mysqlContainerId'],'minio':source['minioContainerId'],'redis':source['redisSnapshot']['containerId']}
roles.update({'writer'+str(i):value for i,value in enumerate(source['writerContainerIds'])})
out={'containers':[],'http':{},'sourceLock':{}}
def inspect(pair):
 role,cid=pair;row={'role':role,'id':cid}
 persisted=pathlib.Path('/var/lib/docker/containers')/cid/'config.v2.json'
 if persisted.is_file():
  old=json.loads(persisted.read_bytes());row['persistedName']=old.get('Name');row['persistedState']={k:old.get('State',{}).get(k) for k in ('Running','Restarting','Pid','ExitCode','StartedAt','FinishedAt')}
 try:
  result=subprocess.run(['docker','inspect',cid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
  if result.returncode:row['observation']='EXIT_'+str(result.returncode)
  else:
   current=json.loads(result.stdout)[0];row.update(observation='LIVE_INSPECT_OK',name=current['Name'],image=current['Image'],state={k:current['State'].get(k) for k in ('Running','Restarting','Pid','ExitCode','StartedAt','FinishedAt')},health=current['State'].get('Health',{}).get('Status'),ports=current.get('NetworkSettings',{}).get('Ports'))
 except subprocess.TimeoutExpired:row['observation']='EXACT_ID_INSPECT_TIMEOUT_5S'
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out['containers']=list(pool.map(inspect,roles.items()))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,url in [('backend','http://127.0.0.1:48081/actuator/health'),('frontend','http://127.0.0.1:8081/')]:
 try:
  with opener.open(url,timeout=3) as response:
   row={'httpStatus':response.status};raw=response.read(8192)
   if name=='backend':row['healthStatus']=json.loads(raw).get('status')
   out['http'][name]=row
 except Exception as error:out['http'][name]={'error':type(error).__name__}
lock=pathlib.Path(capture['sourceLockPath']);out['sourceLock']['path']=str(lock)
if lock.exists():
 st=lock.stat();out['sourceLock'].update(inode=st.st_ino,device=st.st_dev)
 out['sourceLock']['kernelOwners']=[l for l in pathlib.Path('/proc/locks').read_text().splitlines() if str(st.st_ino) in l.split()[5].split(':')[-1:]]
print(json.dumps(out))
'''
profile=next(p for p in PROFILES if p['host']=='172.30.30.57')
args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+profile['host'],profile['python']+' -B -']
p=subprocess.run(args,input=REMOTE.encode('utf-8'),capture_output=True,timeout=35)
if p.returncode:
    (PRIVATE/'exact-source-error.private.txt').write_bytes(p.stderr+p.stdout)
    raise RuntimeError('EXACT_SOURCE_OBSERVATION_FAILED')
report=json.loads(p.stdout)
(TASK/'exact-source.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
