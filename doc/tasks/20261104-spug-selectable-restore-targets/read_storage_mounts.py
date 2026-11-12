import json
from install_controls import PRIVATE, PROFILES, ssh
REMOTE=r'''
import json,pathlib
from pathlib import PurePosixPath
text=pathlib.Path('/proc/self/mountinfo').read_text()
bad=[];selected=[]
for line in text.splitlines():
 f=line.split();root,point=f[3:5]
 if any(str(PurePosixPath(v))!=v or '..' in PurePosixPath(v).parts or not PurePosixPath(v).is_absolute() for v in (root,point)):bad.append({'root':root,'mountPoint':point})
 if any(p==point or p.startswith(point.rstrip('/')+'/') for p in PATHS):selected.append(line)
print(json.dumps({'invalidCanonicalPaths':bad,'dataMounts':selected,'paths':PATHS}))
'''
for profile in PROFILES:
 if profile['host'].endswith('.57'):continue
 inv=json.loads((PRIVATE/(profile['host']+'-install-preflight.json')).read_text(encoding='utf-8'))
 prefix='brlab-prod57-nas-test58-20261020-r3-' if profile['host'].endswith('.58') else 'intruoyi-prod-nas-restore59-20261020-native-'
 rows=[v for v in inv['containers'].values() if v['Name'].lstrip('/') in [prefix+r for r in ('mysql','minio','redis')]]
 paths=[m['Source'] for r in rows for m in r['Mounts'] if m['RW']]
 result=ssh(profile,'PATHS='+repr(paths)+'\n'+REMOTE)
 (PRIVATE/(profile['host']+'-storage-mountinfo.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'host':profile['host'],**result}))
