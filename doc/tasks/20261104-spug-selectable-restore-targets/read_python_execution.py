import json
from install_controls import PRIVATE,PROFILES,ssh
REMOTE=r'''
import json,pathlib,subprocess
out={}
for name,args in {'journal':['journalctl','--no-pager','-n','160','-u','spug-main-restore-58-20261104-v3.service'], 'mode':['ls','-lZ',PYTHON,str(pathlib.Path(PYTHON).resolve())], 'security':['getenforce'], 'audit':['ausearch','-m','AVC','-ts','recent'], 'labels':['matchpathcon','/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12'], 'runtimeSize':['du','-sb',str(pathlib.Path(PYTHON).parent.parent)]}.items():
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE);out[name]={'status':p.returncode,'text':p.stdout.decode(errors='replace')}
print(json.dumps(out))
'''
p=next(p for p in PROFILES if p['host'].endswith('.58'))
result=ssh(p,'PYTHON='+repr('/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/installed/python/bin/python3.12')+'\n'+REMOTE)
(PRIVATE/'58-python-execution.private.json').write_text(json.dumps(result),encoding='utf-8')
print(json.dumps({'mode':result['mode'],'security':result['security'],'labels':result['labels'],'runtimeSize':result['runtimeSize']}))
