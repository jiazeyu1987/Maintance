"""Read existing JSON configurations into a private local analysis directory."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

REMOTE=r'''
import glob,json,os
host=HOST
base='/mnt/intruoyi-data' if host.endswith('.59') else '/var/lib/docker/intruoyi-data'
out={}
patterns=[base+'/spug-intruoyi-'+host.split('.')[-1]+'-safe-20261024-v1/configuration/*.json']
if host.endswith('.58'):patterns+=[base+'/spug-retest-20261024-executor-cross57-safe-full-r2/configuration/*.json',base+'/spug-intruoyi-58-retest-safe-from57-20261024-r1/configuration/*.json']
for pattern in patterns:
    for p in glob.glob(pattern):
        if 'private' in os.path.basename(p):continue
        try:out[p]=json.load(open(p))
        except (OSError,ValueError):continue
for p,c in list(out.items()):
    if 'sources' in c and isinstance(c['sources'],dict):
        for s in c['sources'].values():
            if isinstance(s,dict) and isinstance(s.get('configurationPath'),str):
                path=s['configurationPath']
                if os.path.isfile(path):out[path]=json.load(open(path))
    if 'registryRoot' in c:
        for sel in glob.glob(c['registryRoot']+'/points/*.pin.json')[-1:]:
            pin=json.load(open(sel));binding=json.load(open(pin['path']));out[pin['path']]=binding
            result=json.load(open(binding['resultPin']['path']));out[binding['resultPin']['path']]=result
print(json.dumps(out,ensure_ascii=True))
'''

def collect(host,python):
    argv=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+host,python+' -B -']
    p=subprocess.run(argv,input=REMOTE.replace('HOST',repr(host)).encode('utf-8'),capture_output=True,timeout=25)
    if p.returncode:raise RuntimeError('CONFIG_QUERY_FAILED '+host)
    return host,json.loads(p.stdout)

if __name__=='__main__':
    profiles=json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
    private=Path('C:/Spug/runtime/private/restore-targets-20261104');private.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for host,docs in pool.map(lambda p:collect(p['host'],p['python']),profiles):
            (private/(host+'.json')).write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'host':host,'documents':[{"path":p,"schema":v.get('schemaVersion'),"keys":list(v)} for p,v in docs.items()]},ensure_ascii=False))
