"""Detach only the failed original backend endpoint; preserve unrelated apps."""
import json
from repair_preflight import remote,PRIVATE,TASK
SCRIPT=r'''
import datetime,json,pathlib,subprocess
backend='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c'
network='intruoyi-runtime_intruoyi_net'
def inspect(ids):return json.loads(subprocess.check_output(['docker','inspect']+ids,timeout=12))
before=inspect([backend])[0];assert before['Name']=='/intruoyi-backend' and not before['State']['Running'] and not before['State']['Restarting']
assert before['HostConfig']['PortBindings']=={'48081/tcp':[{'HostIp':'','HostPort':'48081'}]}
assert before['NetworkSettings']['Networks'][network]['IPAMConfig']=={'IPv4Address':'172.21.0.7'}
running=subprocess.check_output(['docker','ps','-q'],timeout=10).decode().split();others=inspect(running)
assert all('48081/tcp' not in (c['HostConfig']['PortBindings'] or {}) for c in others),'OTHER_RUNNING_PORT_OWNER'
root=pathlib.Path('/root/spug-postboot-repair-20261105');root.mkdir(mode=0o700,exist_ok=True)
snapshot=root/'backend-before-disconnect.private.json';assert not snapshot.exists(),'REPAIR_ALREADY_ATTEMPTED'
snapshot.write_text(json.dumps({'backend':before,'others':others}),encoding='utf-8');snapshot.chmod(0o600)
p=subprocess.run(['docker','network','disconnect','--force',network,backend],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
after=inspect([backend])[0]
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'action':'disconnect-failed-original-backend-only','exitCode':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode(),'backendNetworksAfter':after['NetworkSettings']['Networks'],'otherRunningUnchanged':True}
now={c['Id']:c for c in inspect(running)}
for c in others:
 assert now[c['Id']]['State']['Running'] and now[c['Id']]['State']['StartedAt']==c['State']['StartedAt'],'UNRELATED_APP_STATE_CHANGED'
(root/'backend-disconnect-result.json').write_text(json.dumps(report),encoding='utf-8')
print(json.dumps(report))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT)
 (TASK/'backend-endpoint-disconnect.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r))
