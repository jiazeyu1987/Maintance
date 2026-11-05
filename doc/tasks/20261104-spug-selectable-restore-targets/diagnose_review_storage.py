"""Locate exact original-volume/backing drift without mounting or starting anything."""
import json
from resume_readonly import TASK,remote
SCRIPT=r'''
import datetime,json,pathlib,subprocess,sys
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes());sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_replacement_storage import observe_directory,parse_mountinfo
target=owner['targets'][receipt['targetConfigRef']]
def current(p,backing=None):
 p=pathlib.Path(p)
 if not p.is_dir():return {'exists':False}
 s=p.stat();o={'exists':True,'device':s.st_dev,'inode':s.st_ino,'entryCount':sum(1 for _ in p.iterdir())}
 try:o['observed']=observe_directory(str(p),backing=backing)
 except Exception as e:o['observationError']=getattr(e,'code',str(e))
 return o
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mounts':[],'archives':[],'remoteMutation':False}
for item in target['replacement']['storage']['mounts']:
 row={'role':item['role'],'source':item['source'],'expectedDevice':item['device'],'expectedInode':item['inode'],'expectedMount':item['mountIdentity'],'current':current(item['source'],item.get('volume',{}).get('backing'))}
 if item.get('volume'):
  row['volumeDefinition']=json.loads(subprocess.check_output(['docker','volume','inspect',item['volume']['name']],timeout=10))[0]
  backing=item['volume'].get('backing')
  if backing:row['backing']={'expected':backing,'current':current(backing['source'])}
 out['mounts'].append(row)
for source in owner['sources'].values():
 for p in source['archiveRoots']:out['archives'].append({'path':p,'current':current(p)})
out['fstabBindTargets']=[line.split()[1] for line in pathlib.Path('/etc/fstab').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#') and len(line.split())>3 and 'bind' in line.split()[3].split(',')]
print(json.dumps(out))
'''
if __name__=='__main__':
    out=remote('172.30.30.59',SCRIPT,timeout=60)
    (TASK/'review-storage-diagnosis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'mounts':[{'role':r['role'],'source':r['source'],'identityMatches':r['current'].get('device')==r['expectedDevice'] and r['current'].get('inode')==r['expectedInode'],'entryCount':r['current'].get('entryCount'),'backing':r.get('backing')} for r in out['mounts']], 'archives':out['archives'],'remoteMutation':False},ensure_ascii=False))
