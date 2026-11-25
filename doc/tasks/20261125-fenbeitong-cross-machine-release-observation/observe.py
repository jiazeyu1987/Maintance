"""Read-only remote assistant inspection; never instantiate a release executor."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess

TASK = Path(__file__).resolve().parent
CONFIG = Path('C:/SpugHandoff/release/executor.private.json')

REMOTE = r'''
import datetime,hashlib,json,os,stat,subprocess,urllib.request,urllib.error
NAME='fenbeitong-assistant'
ROOT='/var/lib/docker/fenbeitong-release'
def run(args):
 p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 out,err=p.communicate(timeout=25)
 if p.returncode: raise RuntimeError('READ_COMMAND_FAILED_'+str(p.returncode))
 return out
def select(value,keys):
 return dict((k,value[k]) for k in keys if k in value)
def read(path):
 st=os.lstat(path)
 if not stat.S_ISREG(st.st_mode) or st.st_size>2097152: raise RuntimeError('UNSAFE_OR_OVERSIZE_METADATA')
 with open(path,'rb') as f: raw=f.read()
 return json.loads(raw.decode('utf-8')),hashlib.sha256(raw).hexdigest()
out={'observedAtUtc':datetime.datetime.utcnow().isoformat()+'Z','root':ROOT}
names=run(['docker','ps','-a','--format','{{.Names}}']).decode('utf-8').splitlines()
out['assistantContainers']=[n for n in names if n.startswith(NAME)]
if NAME not in names:
 out['installed']=False
 print(json.dumps(out));raise SystemExit(0)
info=json.loads(run(['docker','inspect',NAME]).decode('utf-8'))[0]
labels=info['Config'].get('Labels') or {}
out['installed']=True
out['applicationLabelVerified']=labels.get('release.application')=='fenbeitong'
out['container']=dict(id=info['Id'],imageId=info['Image'],imageReference=info['Config']['Image'],
 created=info['Created'],state=select(info['State'],['Status','Running','Restarting','ExitCode','StartedAt','FinishedAt']),
 restartPolicy=info['HostConfig']['RestartPolicy'],labels=dict((k,v) for k,v in labels.items() if k.startswith('release.')),
 portBindings=info['HostConfig'].get('PortBindings'),
 dataMounts=[select(m,['Type','Source','Destination','RW']) for m in info['Mounts'] if m['Destination']=='/data'])
if not out['applicationLabelVerified']: raise RuntimeError('ASSISTANT_NAME_OWNED_BY_OTHER_APPLICATION')
image=json.loads(run(['docker','image','inspect',info['Image']]).decode('utf-8'))[0]
out['image']=select(image,['Id','RepoTags','Created'])
try:
 code='process.stdout.write(require("fs").readFileSync("/app/release-info.json","utf8"))'
 raw=run(['docker','exec',NAME,'node','-e',code])
 value=json.loads(raw.decode('utf-8'))
 out['releaseInfo']=select(value,['applicationId','releaseTag','version','sourceSha256','sourceKind','commit','builtAt','imageId'])
 out['releaseInfoSha256']=hashlib.sha256(raw).hexdigest()
except Exception as error: out['releaseInfoError']=type(error).__name__
try:
 request=urllib.request.Request('http://127.0.0.1:18734/api/health')
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=8) as response:
  raw=response.read(65537)
  if len(raw)>65536: raise RuntimeError('HEALTH_RESPONSE_TOO_LARGE')
  value=json.loads(raw.decode('utf-8'))
  out['health']=dict(httpStatus=response.status,body=select(value,['success','status','version','releaseTag']))
except urllib.error.HTTPError as error: out['health']=dict(httpStatus=error.code)
except Exception as error: out['health']=dict(errorType=type(error).__name__)
out['receipts']=[]
folder=os.path.join(ROOT,'jobs')
if os.path.isdir(folder):
 paths=[os.path.join(folder,n) for n in os.listdir(folder) if n.endswith('.json')]
 for path in sorted(paths,key=os.path.getmtime,reverse=True)[:30]:
  value,sha=read(path)
  row=select(value,['jobId','status','action','effectsStarted','phase','packageSha256','recovery','previousContainer'])
  row.update(path=path,sha256=sha,modifiedAtUtc=datetime.datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat()+'Z')
  row['environment']=select(value.get('environment',{}),['status','releaseTag','imageId','containerId','packageSha256'])
  out['receipts'].append(row)
out['matchingManifests']=[]
uploads=os.path.join(ROOT,'uploads')
if os.path.isdir(uploads):
 dirs=[os.path.join(uploads,n) for n in os.listdir(uploads) if n.startswith('JOB-')]
 for folder in sorted(dirs,key=os.path.getmtime,reverse=True)[:40]:
  path=os.path.join(folder,'manifest.json')
  if not os.path.isfile(path): continue
  value,sha=read(path)
  if value.get('imageId')!=info['Image'] and value.get('releaseTag')!=labels.get('release.version'): continue
  row=select(value,['applicationId','releaseTag','sourceSha256','image','imageId','createdAt','builtAt'])
  archive=os.path.join(folder,'release.tar')
  row.update(path=path,manifestSha256=sha,archiveExists=os.path.isfile(archive),
             archiveBytes=os.path.getsize(archive) if os.path.isfile(archive) else None)
  out['matchingManifests'].append(row)
lock=os.path.join(ROOT,'release.lock')
out['releaseLock']={'exists':os.path.isfile(lock)}
if os.path.isfile(lock):
 st=os.stat(lock); suffix=':%x:%d'%(os.minor(st.st_dev),st.st_ino)
 with open('/proc/locks','r') as f: locks=f.read().splitlines()
 out['releaseLock'].update(inode=st.st_ino,held=any(suffix in row for row in locks))
out['recentRunningReceipts']=[r['jobId'] for r in out['receipts'] if r.get('status')=='running']
again=json.loads(run(['docker','inspect',NAME]).decode('utf-8'))[0]
out['stableDuringObservation']=again['Id']==info['Id'] and again['Image']==info['Image'] and again['State']['StartedAt']==info['State']['StartedAt']
print(json.dumps(out))
'''


def observe(env, config):
    target = config['targets'][env]
    expected = {'test': '172.30.30.58', 'prod': '172.30.30.57'}[env]
    assert target['host'] == expected and target['python'] == 'python3'
    for field in ('sshIdentityFile', 'sshKnownHostsFile'):
        assert Path(config[field]).is_file()
    encoded = base64.b64encode(REMOTE.encode('utf-8')).decode('ascii')
    command = 'python3 -c ' + shlex.quote('import base64;exec(compile(base64.b64decode("' + encoded + '"),"read_only_fenbeitong_observation","exec"))')
    args = ['ssh', '-i', config['sshIdentityFile'], '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + config['sshKnownHostsFile'],
            '-o', 'ConnectTimeout=10', 'root@' + expected, command]
    result = subprocess.run(args, capture_output=True, timeout=100)
    if result.returncode:
        # No raw stderr or inspect/env/credentials are persisted.
        return dict(environment=env, host=expected, observed=False, sshExitCode=result.returncode,
                    errorType='SSH_OR_REMOTE_READ_FAILED', diagnosticType=(
                        'CONNECTION_TIMEOUT' if b'timed out' in result.stderr.lower() else
                        'AUTHENTICATION_FAILED' if b'permission denied' in result.stderr.lower() else
                        'HOST_KEY_REJECTED' if b'host key verification failed' in result.stderr.lower() else 'OTHER'))
    value = json.loads(result.stdout.decode('utf-8'))
    value.update(environment=env, host=expected, observed=True)
    return value


def main():
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    assert config['applicationId'] == 'intruoyi'
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda e: observe(e, config), ('test', 'prod')))
    report = dict(collectedAtUtc=datetime.now(timezone.utc).isoformat(),
                  authorization='read-only test/prod Fenbeitong release observation',
                  transportConfig=str(CONFIG), results=results)
    (TASK / 'remote-observation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
