"""Set a persistent measured archive budget on the two owned idle controls."""
import json
from repair_preflight import remote, TASK

SCRIPT=r'''
import datetime,json,pathlib,subprocess,os,urllib.request,time
root=pathlib.Path(ROOT);unit=SERVICE
def run(args):return subprocess.check_output(args,timeout=25).decode().strip()
props=dict(l.split('=',1) for l in run(['systemctl','show',unit,'-p','MainPID','-p','ControlGroup']).splitlines())
pid=int(props['MainPID']);assert pid>0
cg=pathlib.Path('/sys/fs/cgroup/systemd')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
if not cg.exists():cg=pathlib.Path('/sys/fs/cgroup')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
assert {int(p) for p in cg.read_text().split()}=={pid},'CONTROL_WORKERS_ACTIVE'
before=run(['docker','ps','--no-trunc','--format','{{.ID}} {{.Status}}'])
receipt=root/('configuration/source-postboot-installation.json' if SOURCE else 'target-installation.json')
meta=json.loads(receipt.read_bytes());control=json.loads(pathlib.Path(meta['controlConfigurationPin']['path']).read_bytes())
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
url='http://127.0.0.1:'+str(control['listenPort'])+'/selections'+('' if SOURCE else '?targetConfigRef='+meta['targetConfigRef'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def selections():
 with opener.open(urllib.request.Request(url,headers=headers),timeout=30) as response:return json.load(response)
pre=selections()
directory=pathlib.Path('/etc/systemd/system')/(unit+'.d');directory.mkdir(exist_ok=True)
drop=directory/'archive-budget.conf'
if drop.exists():assert drop.read_bytes()==b'[Service]\nLimitNOFILE=65536\n','BUDGET_CONFIG_CHANGED'
else:
 with drop.open('xb') as f:f.write(b'[Service]\nLimitNOFILE=65536\n')
 drop.chmod(0o644)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',unit])
assert run(['systemctl','is-active',unit])=='active'
newpid=int(run(['systemctl','show',unit,'-p','MainPID','--value']))
limit=next(l for l in pathlib.Path('/proc/'+str(newpid)+'/limits').read_text().splitlines() if l.startswith('Max open files'))
assert limit.split()[3:5]==['65536','65536'],limit
for attempt in range(10):
 try:post=selections();break
 except urllib.error.URLError:
  if attempt==9:raise
  time.sleep(0.5)
after=run(['docker','ps','--no-trunc','--format','{{.ID}}'])
assert {l.split()[0] for l in before.splitlines()}==set(after.splitlines()),'BUSINESS_RUNNING_SET_CHANGED'
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'service':unit,'dropIn':str(drop),'priorPid':pid,'currentPid':newpid,'limits':limit,'selections':post,'businessRunningSetPreserved':True,'backupOrRestoreSubmitted':False}))
'''
if __name__=='__main__':
 for host,root,service,source in [
  ('172.30.30.57','/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1','spug-intruoyi-source-57-20261105.service',True),
  ('172.30.30.58','/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3','spug-main-restore-58-20261104-v3.service',False)]:
  script='ROOT='+repr(root)+'\nSERVICE='+repr(service)+'\nSOURCE='+repr(source)+'\n'+SCRIPT
  result=remote(host,script,timeout=80)
  (TASK/('archive-budget-'+host+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps(result))
