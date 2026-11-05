"""Read the registered destination identity, image contract, and current health."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,json,pathlib,subprocess,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes());owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
target=owner['targets'][receipt['targetConfigRef']];services={s['role']:s for s in target['services']}
rows=json.loads(subprocess.check_output(['docker','inspect']+[s['id'] for s in target['services']],timeout=15))
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targetConfigRef':receipt['targetConfigRef'],'archiveImageBindings':target['mainApplication']['archiveImageBindings'],'services':[{'id':r['Id'],'name':r['Name'],'image':r['Image'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],'running':r['State']['Running'],'health':r['State'].get('Health',{}).get('Status')} for r in rows]}
assert all(s['running'] for s in out['services'])
out['backendHealth']=json.loads(subprocess.check_output(['docker','exec',services['backend']['id'],'curl','-fsS','--max-time','5','http://127.0.0.1:48081/actuator/health'],timeout=8))['status']
assert out['backendHealth']=='UP'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://172.30.30.58:8081/',timeout=5) as r:out['frontendHTTP']=r.status
out['ledgerEntries']=[str(p.relative_to(root/'ledger')) for p in (root/'ledger').rglob('*')]
out['replacementEntries']=[str(p.relative_to(root/'replacement-state')) for p in (root/'replacement-state').rglob('*')]
assert out['ledgerEntries']==['service.lock'] and not out['replacementEntries']
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
with opener.open(urllib.request.Request('http://127.0.0.1:43658/selections?targetConfigRef='+receipt['targetConfigRef'],headers=headers),timeout=30) as r:out['admission']=json.load(r)
assert receipt['targetConfigRef'] in out['admission']['applications'][0]['freshTargetConfigRefs']
print(json.dumps(out))
'''
if __name__=='__main__':
 r=remote('172.30.30.58',SCRIPT,timeout=55)
 (TASK/'restore-target-baseline.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(r))
