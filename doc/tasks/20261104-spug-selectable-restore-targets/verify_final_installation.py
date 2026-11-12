"""Final read-only package/runtime evidence and bounded production observation."""
import concurrent.futures,json
from install_controls import PRIVATE,PROFILES,ROOTS,ssh
REMOTE=r'''
import hashlib,json,pathlib,subprocess,time
root=pathlib.Path(ROOT);package=json.loads((root/'engine/package.json').read_bytes())
for name,checksum in package['files'].items():assert hashlib.sha256((root/'engine'/name).read_bytes()).hexdigest()==checksum
out={'host':HOST,'root':ROOT,'filesVerified':len(package['files']),'sourceCommit':json.loads((root/'installation.json').read_bytes())['sourceCommit'],'restorePerformed':False}
if HOST.endswith('.57'):
 out.update(targetEnabled=False,loadAverage=pathlib.Path('/proc/loadavg').read_text().split()[:3])
 try:
  p=subprocess.run(['docker','inspect','intruoyi-backend'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=4)
  if p.returncode==0:
   rows=json.loads(p.stdout);out['mainState']={k:rows[0]['State'].get(k) for k in ('Running','Restarting','ExitCode','OOMKilled')}
  else:out['mainObservation']='EXACT_BACKEND_NOT_VERIFIED'
 except subprocess.TimeoutExpired:out['mainObservation']='EXACT_BACKEND_INSPECT_TIMEOUT_4S'
 out['controllerInstalled']=(root/'target-installation.json').exists()
else:
 receipt=json.loads((root/'target-installation.json').read_bytes());out.update(service=receipt['service'],targetConfigRef=receipt['targetConfigRef'])
 out['serviceState']=subprocess.check_output(['systemctl','is-active',receipt['service']]).decode().strip();assert out['serviceState']=='active'
 for key in ('controlConfigurationPin','ownerConfigurationPin','registrationPin','preflightEvidencePin'):
  p=receipt[key];raw=pathlib.Path(p['path']).read_bytes();assert len(raw)==p['bytes'] and hashlib.sha256(raw).hexdigest()==p['sha256']
 out['pinsVerified']=True
 out['operationCount']=len([p for p in (root/'ledger').iterdir() if p.name!='service.lock'])
 out['claimCount']=len(list((root/'replacement-state').iterdir()))
 assert out['operationCount']==out['claimCount']==0
 owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes());target=owner['targets'][receipt['targetConfigRef']]
 rows=json.loads(subprocess.check_output(['docker','inspect',*[s['id'] for s in target['services']]],timeout=12))
 out['mainServices']=[{'id':r['Id'],'running':r['State']['Running'],'restarting':r['State']['Restarting'],'startedAt':r['State']['StartedAt'],'health':r['State'].get('Health',{}).get('Status')} for r in rows]
 assert all(r['running'] and not r['restarting'] for r in out['mainServices'])
print(json.dumps(out))
'''
def verify(profile):
 suffix=profile['host'].split('.')[-1]
 result=ssh(profile,'ROOT='+repr(ROOTS[suffix])+'\nHOST='+repr(profile['host'])+'\n'+REMOTE,timeout=45)
 if suffix!='57':
  inv=json.loads((PRIVATE/(profile['host']+'-install-preflight.json')).read_text(encoding='utf-8'))
  byid={r['Id']:r for r in inv['containers'].values()}
  for service in result['mainServices']:assert service['startedAt']==byid[service['id']]['State']['StartedAt'],'BUSINESS_CONTAINER_RESTARTED'
  result['businessStartTimesUnchanged']=True
 return result
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(verify,PROFILES))
 target=__import__('pathlib').Path(__file__).with_name('installation-status.json')
 target.write_text(json.dumps({'schemaVersion':'SpugMainRestoreInstallationVerification/v1','servers':results,'actualRestorePerformed':False},ensure_ascii=False,indent=2),encoding='utf-8')
 for result in results:print(json.dumps({k:v for k,v in result.items() if k!='mainServices'}))
