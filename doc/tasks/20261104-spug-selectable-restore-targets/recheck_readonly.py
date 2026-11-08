"""Recheck fixed server states and canonical source metadata. Never mutate remote files."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

REMOTE=r'''
import http.client,json,os,socket
class Docker(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(3)
        self.sock.connect('/var/run/docker.sock')
out={'host':HOST,'load':open('/proc/loadavg').read().strip(),'containers':[],'canonicalPaths':{}}
names=NAMES
for name in names:
    c=Docker('localhost',timeout=3)
    try:
        c.request('GET','/containers/'+name+'/json');response=c.getresponse()
        if response.status!=200:out['containers'].append({'name':name,'error':'HTTP_'+str(response.status)});continue
        v=json.loads(response.read());s=v['State']
        out['containers'].append({'name':name,'id':v['Id'],'imageId':v['Image'],
            'running':s['Running'],'restarting':s['Restarting'],'exitCode':s['ExitCode'],
            'health':s.get('Health',{}).get('Status'),'mountTypes':[m['Type'] for m in v['Mounts']]})
    except (OSError,ValueError,http.client.HTTPException) as e:
        out['containers'].append({'name':name,'error':type(e).__name__})
    finally:c.close()
for path in PATHS:out['canonicalPaths'][path]={'exists':os.path.exists(path),'directory':os.path.isdir(path)}
print(json.dumps(out))
'''

def collect(profile,paths):
    names={'172.30.30.57':['intruoyi-backend','intruoyi-mysql','ragflow_compose-minio-1'],
           '172.30.30.58':['brlab-prod57-nas-test58-20261020-r3-backend','intruoyi-july-unified-58-frontend'],
           '172.30.30.59':['intruoyi-prod-nas-restore59-20261020-backend','intruoyi-july-unified-59-frontend-r2']}[profile['host']]
    script=REMOTE.replace('HOST',repr(profile['host'])).replace('NAMES',repr(names)).replace('PATHS',repr(paths))
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
          '-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile',
          '-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8',
          'root@'+profile['host'],profile['python']+' -B -']
    completed=subprocess.run(args,input=script.encode('utf-8'),capture_output=True,timeout=20)
    if completed.returncode:raise RuntimeError('READONLY_RECHECK_FAILED '+profile['host'])
    return json.loads(completed.stdout)

if __name__=='__main__':
    private=Path('C:/Spug/runtime/private/restore-targets-20261104')
    docs=json.loads((private/'172.30.30.57.json').read_text(encoding='utf-8'))
    repository=next(v for v in docs.values() if v.get('schemaVersion')=='RepositoryMinimumConfiguration/v1')
    source=next(iter(repository['sources'].values()))
    capture=docs[source['configurationPath']]
    paths=[capture['archiveRoot'],next(p for p in docs if p.endswith('/source-scope.json')),
           source['sourceIdentityPath']]
    profiles=json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(lambda p:collect(p,paths),profiles))
    destination=Path(__file__).with_name('readonly-recheck.json')
    destination.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows,ensure_ascii=False))
