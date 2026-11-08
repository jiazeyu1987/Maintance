"""Read authenticated selections and original source catalogue; never submit operations."""
import concurrent.futures,json,time,urllib.request
from install_controls import PRIVATE,PROFILES,ROOTS,ssh
REMOTE=r'''
import json,pathlib,urllib.request
root=pathlib.Path(ROOT)
access=json.loads((root/'configuration/source-access.json').read_bytes())
headers=json.loads(pathlib.Path(access['authCredentialRef']['path']).read_bytes())['headers']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request(access['selectionUrl'],headers=headers),timeout=15) as response:source=json.load(response)
assert source['applications'] and any(r['sourceConfigRef']=='intruoyi-57-safe-20261024-v1' and r['recoveryPointRefs'] and not r['historyErrorCode'] for r in source['applications'])
result={'sourceCatalogueVerified':True,'sourcePointCount':len(next(r for r in source['applications'] if r['sourceConfigRef']=='intruoyi-57-safe-20261024-v1')['recoveryPointRefs']), 'ledgerEntries':[str(p.relative_to(root/'ledger')) for p in (root/'ledger').rglob('*')],'claimCount':len(list((root/'replacement-state').iterdir()))}
assert result['claimCount']==0 and result['ledgerEntries']==['service.lock']
result['operationCount']=0
print(json.dumps(result))
'''
def verify(profile):
 suffix=profile['host'].split('.')[-1];ref='intruoyi-main-'+suffix+'-safe-restore-20261104-v1'
 port=43658 if suffix=='58' else 33659
 headers=json.loads((PRIVATE/(profile['host']+'-control-headers.private.json')).read_text(encoding='utf-8'))['headers']
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));started=time.monotonic()
 with opener.open(urllib.request.Request('http://127.0.0.1:'+str(port)+'/selections?targetConfigRef='+ref,headers=headers),timeout=30) as response:data=json.load(response)
 duration=time.monotonic()-started
 (PRIVATE/(profile['host']+'-authenticated-selections.json')).write_text(json.dumps(data),encoding='utf-8')
 assert any(r['sourceConfigRef']=='intruoyi-57-safe-20261024-v1' and ref in r['freshTargetConfigRefs'] for r in data['applications']),'TARGET_NOT_AVAILABLE'
 source=ssh(profile,'ROOT='+repr(ROOTS[suffix])+'\n'+REMOTE)
 result={'host':profile['host'],'selectionSeconds':round(duration,3),'targetAvailable':True,**source}
 (PRIVATE/(profile['host']+'-admission-verification.json')).write_text(json.dumps(result),encoding='utf-8')
 return result
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(verify,p) for p in PROFILES if not p['host'].endswith('.57')]
  for f in concurrent.futures.as_completed(futures):print(json.dumps(f.result()))
