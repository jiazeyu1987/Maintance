"""Read exact IAM identity evidence and configured source lock paths; never mutate data."""
import json
from install_controls import PRIVATE, PROFILES, ROOTS, ssh

REMOTE = r'''
import glob,hashlib,json,pathlib
out={'matchingCaptures':[], 'iamIdentities':{}, 'iamPolicyFiles':{}}
for pattern in PATTERNS:
 for path in glob.glob(pattern):
  p=pathlib.Path(path)
  if not p.is_file() or p.stat().st_size>2097152:continue
  try: d=json.loads(p.read_text(encoding='utf-8'))
  except (ValueError,UnicodeError):continue
  if MYSQL in json.dumps(d):
   locks={k:v for k,v in d.items() if 'lock' in k.lower()}
   out['matchingCaptures'].append({'path':path,'schema':d.get('schemaVersion'),'locks':locks})
iam=pathlib.Path(IAM)
for section in ('users','service-accounts'):
 for p in (iam/section).glob('*/identity.json'):
  files=[p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file())
  out['iamIdentities'][str(p.relative_to(iam))]={str(x.relative_to(iam)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
for section in ('policies','policydb'):
 for p in (iam/section).rglob('*'):
  if p.is_file():out['iamPolicyFiles'][str(p.relative_to(iam))]=hashlib.sha256(p.read_bytes()).hexdigest()
print(json.dumps(out))
'''
if __name__=='__main__':
 for profile in PROFILES:
  suffix=profile['host'].split('.')[-1]
  if suffix=='57':continue
  inv=json.loads((PRIVATE/(profile['host']+'-install-preflight.json')).read_text(encoding='utf-8'))
  mysqlname='brlab-prod57-nas-test58-20261020-r3-mysql' if suffix=='58' else 'intruoyi-prod-nas-restore59-20261020-native-mysql'
  mysql=next(v for v in inv['containers'].values() if v['Name']=='/'+mysqlname)
  minio=next(v for v in inv['containers'].values() if v['Name']=='/'+mysqlname.replace('mysql','minio'))
  mount=next(m['Source'] for m in minio['Mounts'] if m['Destination']=='/data')
  params={'MYSQL':mysql['Id'],'IAM':mount+'/.minio.sys/config/iam','PATTERNS':[
   '/var/lib/docker/intruoyi-data/*/configuration/*.json','/var/lib/docker/intruoyi-data/*/*/configuration/*.json',
   '/var/lib/docker/intruoyi-data/*/*/context/*.json','/mnt/intruoyi-data/*/configuration/*.json',
   '/mnt/intruoyi-data/*/*/configuration/*.json','/opt/intruoyi/*/*.json']}
  result=ssh(profile,'\n'.join(k+'='+repr(v) for k,v in params.items())+'\n'+REMOTE)
  (PRIVATE/(profile['host']+'-writer-lock-evidence.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
  print(json.dumps({'host':profile['host'],'matchingCaptures':result['matchingCaptures'],'identities':list(result['iamIdentities']),'policyFiles':len(result['iamPolicyFiles'])}))
