"""Use Docker's supported orphan endpoint deletion, then restore the same backend."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,json,pathlib,subprocess
backend='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c'
network='intruoyi-runtime_intruoyi_net'
root=pathlib.Path('/root/spug-postboot-repair-20261105')
def run(args,timeout=20):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:raise RuntimeError('DOCKER_REPAIR_FAILED '+repr(args[:3])+' '+p.stderr.decode('utf-8','replace')[:1000])
 return p.stdout.decode().strip()
def inspect(ids):return json.loads(run(['docker','inspect']+ids))
before=inspect([backend])[0]
assert before['Name']=='/intruoyi-backend' and not before['State']['Running'] and before['NetworkSettings']['Networks']=={}
net=json.loads(run(['docker','network','inspect',network]))[0]
assert backend not in net['Containers'] and all(v['EndpointID']!='0574b25ab2cd5ccbe2e0aa5d84af921ebb8e263a83bc0898e8bdb774f412b4e4' for v in net['Containers'].values())
assert all(v['IPv4Address'].split('/')[0]!='172.21.0.11' for v in net['Containers'].values()),'REPAIR_IP_ALREADY_USED'
running=run(['docker','ps','-q']).split();others=inspect(running)
assert all('48081/tcp' not in (c['HostConfig']['PortBindings'] or {}) for c in others)
marker=root/'orphan-removal-started.json';assert not marker.exists(),'ALREADY_ATTEMPTED'
marker.write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'backendId':backend,'orphanEndpoint':'0574b25ab2cd5ccbe2e0aa5d84af921ebb8e263a83bc0898e8bdb774f412b4e4'}),encoding='utf-8')
run(['docker','rename',backend,'intruoyi-backend-postboot-repair-20261105'])
try:
 run(['docker','network','disconnect','--force',network,'intruoyi-backend'])
finally:
 run(['docker','rename',backend,'intruoyi-backend'])
listeners=run(['ss','-lntp'])
assert not any(':48081 ' in l for l in listeners.splitlines()),'ORIGINAL_PORT_NOT_RELEASED'
run(['docker','network','connect','--ip','172.21.0.11','--alias','backend','--alias','intruoyi-backend',network,backend])
run(['docker','start',backend],timeout=30)
after=inspect([backend])[0]
def identity(c):return (c['Id'],c['Name'],c['Image'],c['Config'],sorted(c['Mounts'],key=lambda v:v['Destination']))
assert identity(before)==identity(after) and after['State']['Running'],'ORIGINAL_BACKEND_IDENTITY_OR_STATE_CHANGED'
assert after['NetworkSettings']['Networks'][network]['IPAddress']=='172.21.0.11'
now={c['Id']:c for c in inspect(running)}
for c in others:assert now[c['Id']]['State']['StartedAt']==c['State']['StartedAt'] and now[c['Id']]['State']['Running'],'OTHER_APP_CHANGED'
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'backendId':backend,'name':after['Name'],'image':after['Image'],'state':after['State']['Status'],'networkIp':'172.21.0.11','originalOrphanPortReleased':True,'otherRunningUnchanged':True}
(root/'orphan-removal-result.json').write_text(json.dumps(out),encoding='utf-8');print(json.dumps(out))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT,timeout=100)
 (TASK/'original-backend-restored.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r))
