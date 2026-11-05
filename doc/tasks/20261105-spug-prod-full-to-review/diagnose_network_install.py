"""Read the inactive new generation's exact failed validation, without installing."""
import json
from preflight import COMMON, PRIVATE, TASK, remote

CHECK = r'''
receipt=json.loads((root/'target-installation.json').read_bytes())
ownerpin=pin(root/'configuration/main-recovery-retry-76bb60bd.json')
controlpin=pin(root/'configuration/control-33659-retry-76bb60bd.json')
owner=read(ownerpin);control=read(controlpin)
op=root/'recovery-operations/smallapp-a732505e94bc4863b568e2b2a8c17d57'
code='import json,sys;from pathlib import Path;from recovery_control_smallapp_native import Native;Native(json.loads(sys.argv[1])).configuration();from recovery_retained_retry import observe;print(json.dumps(observe(json.loads(Path(sys.argv[2]).read_bytes()),json.loads((Path(sys.argv[3])/"request.json").read_bytes()),Path(sys.argv[3]),0)))'
result=subprocess.run([control['pythonPin']['path'],'-B','-c',code,canonical(controlpin).decode(),ownerpin['path'],str(op)],env=dict(os.environ,**control['environment']),capture_output=True,timeout=55)
target=owner['targets'][receipt['targetConfigRef']]
frontend=next(s for s in target['services'] if s['role']=='frontend')
row=json.loads(run(['docker','inspect',frontend['id']]))[0]
print(json.dumps(dict(returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),frontendEndpoint=frontend['ip'],portBindings=row['HostConfig']['PortBindings'],attachments={n:{k:v.get(k) for k in ('NetworkID','IPAddress','IPAMConfig')} for n,v in row['NetworkSettings']['Networks'].items()},activeControlPin=receipt['controlConfigurationPin'],candidateOwnerPin=ownerpin,candidateControlPin=controlpin)))
'''

if __name__=='__main__':
    out=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+'\n'+CHECK,75)
    (PRIVATE/'network-install-validation.private.json').write_text(json.dumps(out),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('stdout','stderr')},ensure_ascii=False))
    print('\n'.join(out['stderr'].splitlines()[-5:]))
