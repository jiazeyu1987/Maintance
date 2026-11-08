import json
from install_controls import PRIVATE,PROFILES,ROOTS,ssh
REMOTE=r'''
import json,pathlib,subprocess
out={}
for name in ['systemctl','journalctl']:
 cmd=([name,'status','--no-pager',UNIT] if name=='systemctl' else [name,'--no-pager','-n','24','-u',UNIT])
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 out[name]={'status':p.returncode,'text':p.stdout.decode(errors='replace')}
print(json.dumps(out))
'''
for profile in PROFILES:
 suffix=profile['host'].split('.')[-1]
 if suffix=='57':continue
 unit='spug-main-restore-'+suffix+'-20261104-v3.service'
 result=ssh(profile,'UNIT='+repr(unit)+'\n'+REMOTE)
 (PRIVATE/(suffix+'-own-control-status.private.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'host':profile['host'],'journal':result['journalctl']['text'][-4200:]}))
