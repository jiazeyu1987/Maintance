import json
from install_controls import PRIVATE, PROFILES, ROOTS, ssh
REMOTE=r'''
import json,pathlib,subprocess
out={'root':ROOT,'listeners':subprocess.check_output(['ss','-lntp']).decode(),'units':{},'process':pathlib.Path('/proc/32696/cmdline').read_bytes().decode().replace('\x00',' ')}
for name in ('spug-main-restore-58-20261104-v1.service','spug-main-restore-58-20261104-v2.service','spug-main-restore-58-20261104-v3.service'):
 p=pathlib.Path('/etc/systemd/system')/name
 if p.exists():out['units'][name]=p.read_text()
print(json.dumps(out))
'''
if __name__=='__main__':
 p=next(p for p in PROFILES if p['host'].endswith('.58'))
 result=ssh(p,'ROOT='+repr(ROOTS['58'])+'\n'+REMOTE)
 (PRIVATE/'58-port-review.private.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'listeners':[l for l in result['listeners'].splitlines() if 'python3.12' in l or '34657' in l],'unitNames':list(result['units'])}))
