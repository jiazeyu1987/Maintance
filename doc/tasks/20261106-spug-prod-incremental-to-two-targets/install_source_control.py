"""Install one immutable committed source generation; preserve all businesses."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
from common import PRIVATE,TASK,SOURCE,remote,write

SCRIPT=r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
unit='spug-intruoyi-source-57-20261105.service'
generation='incremental-'+COMMIT[:7]
engine=root/('engine-'+generation)
dropin=pathlib.Path('/etc/systemd/system')/(unit+'.d')/(generation+'.conf')

def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(path):
 path=pathlib.Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def run(args,timeout=30,env=None):
 p=subprocess.run(args,capture_output=True,timeout=timeout,env=env);need(p.returncode==0,'INSTALL_COMMAND_FAILED');return p.stdout
def write_new(path,raw):
 need(path.is_absolute() and path.parent.resolve()==path.parent,'INSTALL_PATH_INVALID')
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
 need(path.read_bytes()==raw,'INSTALL_READBACK_FAILED');return pin(path)
def docker(args):return run(['/usr/bin/docker','--host','unix:///var/run/docker.sock',*args])
def snapshot():
 rows=json.loads(docker(['inspect',*docker(['ps','-aq','--no-trunc']).decode().split()]))
 return {r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():
 return sorted(' '.join(line.split()[1:]) for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in line or 'intruoyi' in line or '/mnt/nas' in line)
need(root.resolve()==root and not engine.exists() and not dropin.exists(),'GENERATION_ALREADY_EXISTS_OR_ROOT_INVALID')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if (str(root).encode() in command or b'spug-main-restore-20261104-v3' in command):
  need(b'control_entry.py' in command,'ACTIVE_SOURCE_OR_TARGET_WORKER')
lock=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
oldpath=root/'configuration/control-postboot-20261105.json'
need(pin(oldpath)==OLD_CONTROL_PIN,'OLD_CONTROL_PIN_CHANGED')
oldcontrol=json.loads(oldpath.read_bytes());oldownerpin=oldcontrol['sourceConfigurations'][SOURCE]
need(pin(oldownerpin['path'])==oldownerpin,'OLD_OWNER_PIN_CHANGED')
oldowner=json.loads(pathlib.Path(oldownerpin['path']).read_bytes())
need(pin(oldcontrol['pythonPin']['path'])==oldcontrol['pythonPin'],'PYTHON_CHANGED')
oldengine=root/'engine';oldversion=json.loads((oldengine/'package.json').read_bytes())
need(all(pin(oldengine/name)['sha256']==sha for name,sha in oldversion['files'].items()),'OLD_PACKAGE_CHANGED')
before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts()
oldpid=int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip());need(oldpid>1,'OLD_CONTROL_NOT_RUNNING')
raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED')
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 version=json.load(archive.extractfile('package.json'));names=archive.getnames()
 need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_PACKAGE_REQUIRED')
 need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
 need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256'],'PACKAGE_MANIFEST_CHANGED')
 for member in archive.getmembers():
  need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
  data=archive.extractfile(member).read()
  if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][member.name],'PACKAGE_MEMBER_CHANGED');compile(data,member.name,'exec')
 engine.mkdir(mode=0o700)
 for member in archive.getmembers():
  destination=engine/member.name;destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True);write_new(destination,archive.extractfile(member).read())
def rebind(value):
 if isinstance(value,str):return value.replace(str(oldengine)+'/',str(engine)+'/')
 if isinstance(value,list):return [rebind(v) for v in value]
 if isinstance(value,dict):
  result={k:rebind(v) for k,v in value.items()}
  if set(('path','bytes','sha256'))<=set(result) and result['path']!=value['path']:result.update(pin(result['path']))
  return result
 return value
newowner=rebind(oldowner);ownerpath=root/'configuration'/('repository-'+generation+'.json');ownerpin=write_new(ownerpath,canonical(newowner))
control=rebind(oldcontrol);control['sourceConfigurations'][SOURCE]=ownerpin
controlpath=root/'configuration'/('control-'+generation+'.json');controlpin=write_new(controlpath,canonical(control))
for role in ('repository','recovery','control'):
 answer=json.loads(run([control['pythonPin']['path'],'-B',str(engine/(role+'_entry.py')),'--check-imports'],env=dict(os.environ,**control['environment'])))
 need(answer['role']==role,'ENTRY_IMPORT_FAILED')
command=control['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(controlpin).decode()+"'"
dropin.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
text='[Service]\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n'
write_new(dropin,text.encode());dropin.chmod(0o644)
run(['systemctl','daemon-reload']);run(['systemctl','restart',unit])
need(run(['systemctl','is-active',unit]).strip()==b'active','CONTROL_NOT_ACTIVE')
pid=int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip());need(pid>1 and pid!=oldpid,'CONTROL_PID_NOT_CHANGED')
cmdline=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes();need(str(engine/'control_entry.py').encode() in cmdline and str(controlpath).encode() in cmdline,'CONTROL_GENERATION_NOT_ACTIVE')
limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_INVALID')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://127.0.0.1:'+str(control['listenPort'])+'/selections'
with opener.open(urllib.request.Request(url,headers=headers),timeout=90) as response:
 need(response.status==200,'SOURCE_SELECTIONS_UNAVAILABLE');selections=json.load(response)
need(snapshot()==before,'ORIGINAL_DOCKER_RUNTIME_CHANGED')
need(pin('/etc/fstab')==fstab and mounts()==beforemounts,'PROTECTED_STORAGE_CHANGED')
need(pin(oldpath)==OLD_CONTROL_PIN and pin(oldownerpin['path'])==oldownerpin,'OLD_CONFIGURATION_CHANGED')
need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'NEW_PACKAGE_DRIFT')
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=COMMIT,service=unit,sourceConfigRef=SOURCE,oldControlPin=OLD_CONTROL_PIN,controlConfigurationPin=controlpin,ownerConfigurationPin=ownerpin,engine=str(engine),fileCount=len(version['files']),fileManifestSha256=version['packageSha256'],packageSha256=PACKAGE_SHA,dropinPin=pin(dropin),previousPid=oldpid,pid=pid,liveMaxOpenFiles=65536,originalContainerCount=len(before),allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,sourceSelectionsHttp=200,sourceSelections=selections,backupPerformed=False,restorePerformed=False)
write_new(root/'configuration'/('installation-'+generation+'.json'),canonical(out));os.close(lock);print(json.dumps(out))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
 report=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf-8'))
 assert report['status']=='PASS' and report['targetCommit']==args.commit
 assert not (TASK/'source-control-installation.json').exists(),'INSTALLATION_RECEIPT_ALREADY_EXISTS'
 package=Path(report['worktree']).parent/('package-'+args.commit[:7])/'backup-restore-standard.tgz'
 assert hashlib.sha256(package.read_bytes()).hexdigest()==report['packageSha256']
 baseline=json.loads((PRIVATE/'baseline-57.private.json').read_text(encoding='utf-8'))
 oldpin=next(v for k,v in baseline['pins'].items() if k.endswith('configuration/control-postboot-20261105.json'))
 variables=dict(COMMIT=args.commit,SOURCE=SOURCE,OLD_CONTROL_PIN=oldpin,PACKAGE_SHA=report['packageSha256'],PACKAGE=base64.b64encode(package.read_bytes()).decode())
 payload='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT
 value=remote('172.30.30.57',payload,240)
 write(PRIVATE/'source-control-installation.private.json',value)
 public={k:v for k,v in value.items() if k!='sourceSelections'}
 write(TASK/'source-control-installation.json',public);print(json.dumps(public))
