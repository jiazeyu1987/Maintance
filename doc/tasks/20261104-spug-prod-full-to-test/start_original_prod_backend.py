"""Terminate only proven original stale port proxies, start the same backend."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,json,os,pathlib,signal,subprocess,time
backend='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c';network='intruoyi-runtime_intruoyi_net'
root=pathlib.Path('/root/spug-postboot-repair-20261105')
def run(args,timeout=20):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:raise RuntimeError('REPAIR_COMMAND_FAILED '+repr(args[:3])+' '+p.stderr.decode('utf-8','replace')[:1000])
 return p.stdout.decode().strip()
def inspect(ids):return json.loads(run(['docker','inspect']+ids))
before=inspect([backend])[0];assert before['Name']=='/intruoyi-backend' and not before['State']['Running'] and before['NetworkSettings']['Networks']=={}
running=run(['docker','ps','-q']).split();others=inspect(running)
assert all('48081/tcp' not in (c['HostConfig']['PortBindings'] or {}) for c in others)
net=json.loads(run(['docker','network','inspect',network]))[0]
assert all(v['IPv4Address'].split('/')[0]!='172.21.0.11' for v in net['Containers'].values())
for pid,start,ip in [(6860,'2699','0.0.0.0'),(6868,'2700','::')]:
 p=pathlib.Path('/proc')/str(pid);cmd=(p/'cmdline').read_bytes().decode().split('\x00')[:-1];stat=(p/'stat').read_text().split()
 assert cmd==['/usr/bin/docker-proxy','-proto','tcp','-host-ip',ip,'-host-port','48081','-container-ip','172.21.0.7','-container-port','48081'] and stat[21]==start and stat[3]=='4374','STALE_PROXY_IDENTITY_CHANGED'
marker=root/'exact-proxy-repair-started.json';assert not marker.exists(),'ALREADY_ATTEMPTED';marker.write_text(json.dumps({'backendId':backend,'proxyPids':[6860,6868]}),encoding='utf-8')
for pid in [6860,6868]:os.kill(pid,signal.SIGTERM)
for _ in range(20):
 if not any(':48081 ' in l for l in run(['ss','-lntp']).splitlines()):break
 time.sleep(0.1)
else:raise RuntimeError('ORIGINAL_PROXY_PORT_STILL_LISTENING')
run(['docker','network','connect','--ip','172.21.0.11','--alias','backend','--alias','intruoyi-backend',network,backend])
run(['docker','start',backend],timeout=30)
after=inspect([backend])[0]
assert after['Id']==before['Id'] and after['Name']==before['Name'] and after['Image']==before['Image'] and after['Config']==before['Config'] and sorted(after['Mounts'],key=lambda x:x['Destination'])==sorted(before['Mounts'],key=lambda x:x['Destination'])
assert after['State']['Running']
now={c['Id']:c for c in inspect(running)}
for c in others:assert now[c['Id']]['State']['StartedAt']==c['State']['StartedAt'] and now[c['Id']]['State']['Running'],'OTHER_APP_CHANGED'
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'backendId':backend,'name':after['Name'],'state':after['State']['Status'],'image':after['Image'],'networkIp':after['NetworkSettings']['Networks'][network]['IPAddress'],'otherRunningUnchanged':True}
(root/'exact-proxy-repair-result.json').write_text(json.dumps(out),encoding='utf-8');print(json.dumps(out))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT,timeout=90)
 (TASK/'original-backend-restored.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r))
