"""Start only the original production application after the approved daemon repair."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,json,pathlib,subprocess
backend='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c'
frontend='1210f97cf7653c5f74a7981bf4d4bec8d7462af873d53695d47a59a7ce38a479'
def run(args,timeout=20):return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout).stdout.decode().strip()
repair=pathlib.Path('/root/spug-postboot-repair-20261105')
assert json.loads((repair/'docker-management-repair/restart-result.json').read_bytes())['status']=='PASS'
before=json.loads((repair/'backend-before-disconnect.private.json').read_bytes())
baseline={c['Id']:c for c in [before['backend']]+before['others']}
out=[]
for cid in [backend,frontend]:
 c=json.loads(run(['docker','inspect',cid]))[0];b=baseline[cid]
 assert c['Image']==b['Image'] and c['Config']==b['Config'] and sorted(c['Mounts'],key=lambda x:x['Destination'])==sorted(b['Mounts'],key=lambda x:x['Destination']),'ORIGINAL_APPLICATION_CHANGED'
 if not c['State']['Running'] and not c['State']['Restarting']:run(['docker','start',cid],timeout=30)
 c=json.loads(run(['docker','inspect',cid]))[0]
 out.append({'id':c['Id'],'name':c['Name'],'state':c['State']['Status'],'health':c['State'].get('Health',{}).get('Status'),'image':c['Image'],'startedAt':c['State']['StartedAt']})
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'containers':out}))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT,timeout=80)
 (TASK/'prod-start-after-daemon.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
