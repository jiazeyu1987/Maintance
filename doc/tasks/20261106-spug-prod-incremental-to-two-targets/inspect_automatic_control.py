"""Read exact active source/target configuration without publishing credentials."""
import json
from common import remote, write, PRIVATE

SCRIPT = r'''
import pathlib,json,subprocess,hashlib
out=[]
for unit in ['spug-intruoyi-source-57-20261105.service','spug-main-restore-57-20261105-v2.service']:
 txt=subprocess.check_output(['systemctl','show',unit,'-p','MainPID']).decode().strip()
 pid=int(txt.split('=',1)[1]);assert pid>1
 args=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0')
 pin=json.loads(args[args.index('--config-pin')+1])
 raw=pathlib.Path(pin['path']).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'];control=json.loads(raw)
 owners={}
 for lane in ['sourceConfigurations','restoreConfigurations']:
  for ref,p in control[lane].items():
   if 'path' not in p:
    for target_ref,target_pin in p.items():
     data=pathlib.Path(target_pin['path']).read_bytes();assert len(data)==target_pin['bytes'] and hashlib.sha256(data).hexdigest()==target_pin['sha256'];owners[target_ref]=json.loads(data)
    continue
   data=pathlib.Path(p['path']).read_bytes();assert len(data)==p['bytes'] and hashlib.sha256(data).hexdigest()==p['sha256'];owners[ref]=json.loads(data)
 out.append(dict(unit=unit,pid=pid,args=args,controlPin=pin,control=control,owners=owners))
print(json.dumps(out))
'''

if __name__ == '__main__':
    result = remote('172.30.30.57', SCRIPT)
    write(PRIVATE / 'automatic-57-installed.private.json', result)
    for item in result:
        print(item['unit'], item['pid'], item['controlPin']['path'])
        print('ownerMappings', {lane: {key: list(value) for key, value in item['control'][lane].items()}
                                for lane in ('sourceConfigurations', 'restoreConfigurations')})
        for ref, owner in item['owners'].items():
            print('owner', ref, 'keys', list(owner))
            for target_ref, target in owner.get('targets', {}).items():
                replacement = target.get('replacement', {})
                print('target', target_ref, 'keys', list(target), 'replacementKeys', list(replacement))
                print({key: replacement.get(key) for key in ('stateRoot', 'lockPath', 'databaseUuid')})
