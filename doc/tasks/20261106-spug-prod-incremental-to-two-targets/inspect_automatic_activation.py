"""Inspect actual service generation without replacing original install evidence."""
import json
from common import TASK, PRIVATE, remote, write

SCRIPT = r'''
import json,pathlib,subprocess
out=[]
for unit in ('spug-intruoyi-source-57-20261105.service','spug-main-restore-57-20261105-v2.service'):
 p=int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value']))
 args=(pathlib.Path('/proc')/str(p)/'cmdline').read_bytes().decode().split('\0')
 out.append(dict(unit=unit,pid=p,args=args,dropins=subprocess.check_output(['systemctl','show',unit,'-p','DropInPaths','--value']).decode()))
print(json.dumps(out))
'''
if __name__ == '__main__':
    result = remote('172.30.30.57', SCRIPT, 40)
    write(PRIVATE / 'automatic-57-actual-activation.private.json', result)
    print(json.dumps(result))
