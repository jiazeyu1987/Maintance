"""Bounded read-only resource, writer and archive installation dependencies."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
from collect_install_preflight import PRIVATE

REMOTE = r'''
import glob,hashlib,json,os,pathlib,re,subprocess,urllib.request
out={'host':HOST,'documents':{},'files':{},'queries':{},'errors':{}}
def raw(path):return pathlib.Path(path).read_bytes()
def pin(path):
    b=raw(path);return {'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def run(args,input=None):
    p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    if p.returncode:raise ValueError('READONLY_COMMAND_FAILED')
    return p.stdout.decode('utf-8')
control=CONTROL
if HOST.endswith('.57'):
    c=json.loads(raw(control));headers=json.loads(raw(c['authCredentialRef']['path']))['headers']
    req=urllib.request.Request('http://127.0.0.1:'+str(c['listenPort'])+'/selections',headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=15) as response:out['sourceSelections']=json.load(response)
    except Exception as e:out['errors']['sourceSelections']=type(e).__name__
archives=ARCHIVES
points=sorted(glob.glob(archives+'/*/.repository/point.json'),key=os.path.getmtime)
out['pointCount']=len(points)
if points:
    path=points[-1];out['documents'][path]=json.loads(raw(path));out['latestPointPin']=pin(path)
    side=pathlib.Path(path).parent
    for name in ['recovery-material.json','recovery-repository-binding.json','manifest.json']:
        p=str(side/name)
        try:out['documents'][p]=json.loads(raw(p))
        except (OSError,ValueError) as e:out['errors'][p]=type(e).__name__
    material=out['documents'].get(str(side/'recovery-material.json'),{})
    refs=material.get('versionPins',[])+material.get('configurationPins',[])
    for reference in refs:
        path=reference['path']
        try:
            out['files'][path]=pin(path)
            if path.endswith('.json'):out['documents'][path]=json.loads(raw(path))
        except (OSError,ValueError) as e:out['errors'][path]=type(e).__name__
if not HOST.endswith('.57'):
    root=TARGETROOT
    try:
        query='SELECT @@server_uuid,@@GLOBAL.log_bin; SELECT USER,HOST,DB,COMMAND FROM information_schema.PROCESSLIST; SELECT User,Host FROM mysql.user;'
        out['queries']['mysql']=run(['/usr/bin/docker','exec',MYSQL,'/usr/bin/mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names','-e',query])
    except Exception as e:out['errors']['mysql']=type(e).__name__
    try:
        conf=pathlib.Path(root+'/private/redis.conf').read_text()
        password=re.search(r'^requirepass\s+(.*?)\s*$',conf,re.M).group(1).strip('"')
        shell='IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
        out['queries']['redisClients']=run(['/usr/bin/docker','exec','-i',REDIS,'sh','-ec',shell,'readonly-redis','/usr/local/bin/redis-cli','--raw','CLIENT','LIST'],(password+'\n').encode())
    except Exception as e:out['errors']['redisClients']=type(e).__name__
    for path in [root+'/private/mysql-root',root+'/private/redis.conf',root+'/private/minio-root-user',root+'/private/minio-root-password',root+'/private/application-target.properties',NGINX]:
        try:out['files'][path]=pin(path)
        except OSError as e:out['errors'][path]=type(e).__name__
    for path in WRITERFILES:
        try:
            text=pathlib.Path(path).read_text(encoding='utf-8')
            out['files'][path]={'pin':pin(path),'referencedResourceEndpoints':sorted(set(re.findall(r'172\.29\.(?:235|239)\.(?:22|23|24)',text))),
                'databaseMention':'ruoyi-vue-pro' in text,'directClientKeywords':sorted(set(re.findall(r'(?i)mysql|jdbc|redis|s3|MINIO_ROOT_PASSWORD',text)))}
        except OSError as e:out['errors'][path]=type(e).__name__
    out['connections']=run(['ss','-ntp'])
    out['hostServices']=run(['systemctl','list-units','--type=service','--state=running','--no-pager','--plain'])
print(json.dumps(out))
'''

def collect(profile):
    host=profile['host'];suffix=host.split('.')[-1]
    root={'57':'','58':'/var/lib/docker/intruoyi-data/prod-nas-restore-test58-20261020/target-r3','59':'/mnt/intruoyi-data/prod-nas-restore-prep-20261020/restore-target-r1'}[suffix]
    params={'HOST':host,'CONTROL':'/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/control.json',
        'ARCHIVES':'/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives',
        'TARGETROOT':root,'MYSQL':{'57':'','58':'brlab-prod57-nas-test58-20261020-r3-mysql','59':'intruoyi-prod-nas-restore59-20261020-native-mysql'}[suffix],
        'REDIS':{'57':'','58':'brlab-prod57-nas-test58-20261020-r3-redis','59':'intruoyi-prod-nas-restore59-20261020-native-redis'}[suffix],
        'NGINX':('/var/lib/docker/intruoyi-data/20261020-three-server-july-unification/nginx.conf' if suffix=='58' else '/mnt/intruoyi-data/20261020-three-server-july-unification/nginx.conf'),
        'WRITERFILES':[]}
    script='\n'.join(name+'='+repr(value) for name,value in params.items())+'\n'+REMOTE
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+host,profile['python']+' -B -']
    p=subprocess.run(args,input=script.encode('utf-8'),capture_output=True,timeout=70)
    if p.returncode:
        (PRIVATE/(host+'-dependencies-error.private.txt')).write_bytes(p.stderr)
        raise RuntimeError('DEPENDENCIES_QUERY_FAILED '+host)
    v=json.loads(p.stdout);(PRIVATE/(host+'-dependencies.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'host':host,'pointCount':v['pointCount'],'latestPoint':v.get('latestPointPin'),'errors':v['errors'],
        'queries':v['queries'],'sourceSelections':v.get('sourceSelections')}

if __name__=='__main__':
    profiles=json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for future in concurrent.futures.as_completed([pool.submit(collect,p) for p in profiles]):print(json.dumps(future.result(),ensure_ascii=False))
