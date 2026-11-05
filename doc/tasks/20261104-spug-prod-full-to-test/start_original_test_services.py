"""Start only the four explicitly approved original test target containers."""
import json
from repair_preflight import remote,TASK,PRIVATE
SCRIPT=r'''
import datetime,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
target=owner['targets'][receipt['targetConfigRef']]
expected=['b4592b704b979f1b94ba03836985491a8f7c699d3094297bfbe3696939eedd79','98216faac1ae2fc1508bd4076962bf4cfcb3a47f2f1bd5d5e42c7ba819e83115','028bb0541d3216c283c5f1822338462545fa7cd63fad55c462ae20a01526e225','6f70e67078d086d7f08c1ae75a80bb0feab28c5a1f92c91d655ac258f34988eb']
assert all(c in [s['id'] for s in target['services']] for c in expected)
before=json.loads(subprocess.check_output(['docker','inspect']+expected,timeout=10))
def identity(c):return {'Image':c['Image'],'Config':c['Config'],'Mounts':sorted(c['Mounts'],key=lambda m:m['Destination'])}
assert all(identity(c)==BASELINE[c['Id']] and not c['State']['Restarting'] and not c['State']['Paused'] for c in before),'TARGET_IDENTITY_CHANGED'
results=[]
for container in before:
 if not container['State']['Running']:
  p=subprocess.run(['docker','start',container['Id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
  assert p.returncode==0,'EXACT_CONTAINER_START_FAILED_'+container['Id']
 after=json.loads(subprocess.check_output(['docker','inspect',container['Id']],timeout=8))[0]
 assert identity(after)==identity(container),'CONTAINER_IDENTITY_CHANGED'
 results.append({'id':after['Id'],'name':after['Name'],'state':after['State']['Status'],'image':after['Image'],'startedAt':after['State']['StartedAt']})
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'containers':results}))
'''
if __name__=='__main__':
 baseline=json.loads((PRIVATE/'172.30.30.58-post-boot.private.json').read_text(encoding='utf-8'))
 ids=['b4592b704b979f1b94ba03836985491a8f7c699d3094297bfbe3696939eedd79','98216faac1ae2fc1508bd4076962bf4cfcb3a47f2f1bd5d5e42c7ba819e83115','028bb0541d3216c283c5f1822338462545fa7cd63fad55c462ae20a01526e225','6f70e67078d086d7f08c1ae75a80bb0feab28c5a1f92c91d655ac258f34988eb']
 snapshots={c['Id']:{'Image':c['Image'],'Config':c['Config'],'Mounts':sorted(c['Mounts'],key=lambda m:m['Destination'])} for c in baseline['containers'] if c['Id'] in ids}
 assert len(snapshots)==4
 result=remote('172.30.30.58','BASELINE='+repr(snapshots)+'\n'+SCRIPT,timeout=110)
 (TASK/'original-test-started.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
