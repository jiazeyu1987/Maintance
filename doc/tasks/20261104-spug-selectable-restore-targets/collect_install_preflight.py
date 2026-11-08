"""Read-only installation inventory. Raw private configurations never enter Git."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

PRIVATE = Path('C:/Spug/runtime/private/restore-targets-20261104')
REMOTE = r'''
import glob,hashlib,http.client,json,os,pathlib,socket,subprocess
class Docker(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(4)
        self.sock.connect('/var/run/docker.sock')
def get(path):
    c=Docker('localhost',timeout=4)
    try:
        c.request('GET',path);r=c.getresponse()
        if r.status!=200:raise ValueError('DOCKER_HTTP_'+str(r.status))
        return json.loads(r.read())
    finally:c.close()
def run(args,timeout=8):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:raise ValueError('READONLY_COMMAND_FAILED')
    return p.stdout.decode('utf-8')
out={'host':HOST,'load':pathlib.Path('/proc/loadavg').read_text(),'containers':{},'errors':{},'documents':{},'files':{}}
try:out['list']=get('/containers/json?all=true')
except Exception as e:out['errors']['list']=type(e).__name__
names=NAMES
if not HOST.endswith('.57'):
    names=[v['Id'] for v in out.get('list',[])]
for name in names:
    try:out['containers'][name]=get('/containers/'+name+'/json')
    except Exception as e:out['errors'][name]=type(e).__name__
try:out['info']=get('/info')
except Exception as e:out['errors']['info']=type(e).__name__
networkids={n['NetworkID'] for row in out['containers'].values() for n in row['NetworkSettings']['Networks'].values()}
out['networks']={}
for n in networkids:
    try:out['networks'][n]=get('/networks/'+n)
    except Exception as e:out['errors'][n]=type(e).__name__
out['machineId']=pathlib.Path('/etc/machine-id').read_text().strip()
out['mountinfo']=pathlib.Path('/proc/self/mountinfo').read_text()
out['listen']=run(['ss','-lntp'])
out['systemd']=run(['systemctl','list-units','--type=service','--all','--no-pager','--plain'])
base='/mnt/intruoyi-data' if HOST.endswith('.59') else '/var/lib/docker/intruoyi-data'
patterns=[base+'/spug-*/configuration/*.json',base+'/*/target*/configuration/*.json',base+'/*/restore-target*/configuration/*.json']
for pattern in patterns:
    for p in glob.glob(pattern):
        try:
            if os.path.getsize(p)>2097152:continue
            v=json.loads(pathlib.Path(p).read_text(encoding='utf-8'));out['documents'][p]=v
        except (OSError,ValueError):pass
for path in CANONICAL:
    p=pathlib.Path(path)
    try:
        if p.is_file():
            raw=p.read_bytes();out['files'][path]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        else:out['files'][path]={'exists':p.exists(),'directory':p.is_dir()}
    except OSError as e:out['files'][path]={'error':type(e).__name__}
for p in CONFIGFILES:
    try:out['files'][p]={'text':pathlib.Path(p).read_text(encoding='utf-8')}
    except OSError as e:out['files'][p]={'error':type(e).__name__}
print(json.dumps(out))
'''

def collect(profile, paths):
    host=profile['host']
    names={'57':['intruoyi-backend','intruoyi-frontend','intruoyi-mysql','intruoyi-redis','ragflow_compose-minio-1'],
           '58':[], '59':[]}[host.split('.')[-1]]
    configfiles={'57':[], '58':['/var/lib/docker/intruoyi-data/prod-nas-restore-test58-20261020/target-r3/private/application-target.properties'],
        '59':['/mnt/intruoyi-data/prod-nas-restore-prep-20261020/restore-target-r1/private/application-target.properties']}[host.split('.')[-1]]
    code=REMOTE.replace('HOST',repr(host)).replace('NAMES',repr(names)).replace('CANONICAL',repr(paths)).replace('CONFIGFILES',repr(configfiles))
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+host,profile['python']+' -B -']
    p=subprocess.run(args,input=code.encode('utf-8'),capture_output=True,timeout=180)
    if p.returncode:raise RuntimeError('INSTALL_PREFLIGHT_QUERY_FAILED '+host)
    result=json.loads(p.stdout)
    (PRIVATE/(host+'-install-preflight.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'host':host,'load':result['load'].strip(),'containerCount':len(result['containers']),'errors':result['errors'],
        'documents':[{ 'path':p,'schema':v.get('schemaVersion')} for p,v in result['documents'].items() if v.get('targets')],
        'canonicalFiles':result['files'].keys().__len__()}

if __name__=='__main__':
    docs=json.loads((PRIVATE/'172.30.30.57.json').read_text(encoding='utf-8'))
    repository=next(v for v in docs.values() if v.get('schemaVersion')=='RepositoryMinimumConfiguration/v1')
    source=next(iter(repository['sources'].values()));capture=docs[source['configurationPath']]
    paths=[source['sourceIdentityPath'],next(p for p in docs if p.endswith('/source-scope.json')),repository['repositoryRoot']]
    profiles=json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in concurrent.futures.as_completed([pool.submit(collect,p,paths) for p in profiles]):
            print(json.dumps(future.result(),ensure_ascii=False))
