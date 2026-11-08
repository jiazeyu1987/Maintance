"""Stage and activate the committed source/physical-target pair under one lock."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from common import TASK, PRIVATE, SOURCE, remote, write

SCRIPT = r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,subprocess,sys,tarfile,time,urllib.request,urllib.error
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def document(p):
 need(pin(p['path'])==p,'PIN_CHANGED');return json.loads(pathlib.Path(p['path']).read_bytes())
def run(args,timeout=30,env=None,input=None):
 p=subprocess.run(args,capture_output=True,timeout=timeout,env=env,input=input)
 need(p.returncode==0,'INSTALL_COMMAND_FAILED_'+str(p.returncode));return p.stdout
def write_new(path,raw):
 need(path.is_absolute() and path.parent.resolve()==path.parent,'INSTALL_PATH_ALIAS')
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
 need(path.read_bytes()==raw,'INSTALL_READBACK_FAILED');return pin(path)
def docker(args):return run(['/usr/bin/docker','--host','unix:///var/run/docker.sock',*args])
def snapshot():
 rows=json.loads(docker(['inspect',*docker(['ps','-aq','--no-trunc']).decode().split()]))
 return {r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():return sorted(' '.join(line.split()[1:]) for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in line or 'intruoyi' in line or '/mnt/nas' in line)
def active_pid(unit):return int(run(['systemctl','show',unit,'-p','MainPID']).decode().strip().split('=',1)[1])
def http(control,path,timeout=40):
 headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(urllib.request.Request('http://127.0.0.1:'+str(control['listenPort'])+path,headers=headers),timeout=timeout) as response:
  need(response.status==200,'HTTP_STATUS_INVALID');return json.load(response)
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
old=INSTALLED
for item in old:
 need(active_pid(item['unit'])==item['pid'],'CONTROL_PID_CHANGED')
 need(document(item['controlPin'])==item['control'],'CONTROL_CONFIGURATION_CHANGED')
 previous=pathlib.Path(item['args'][item['args'].index('-B')+1]).parent
 old_manifest=json.loads((previous/'package.json').read_bytes())
 need(all(pin(previous/name)['sha256']==sha for name,sha in old_manifest['files'].items()),'OLD_INSTALLED_PACKAGE_CHANGED')
 root=pathlib.Path(item['control']['workingDirectory'])
 for process in pathlib.Path('/proc').iterdir():
  if not process.name.isdecimal():continue
  try:command=(process/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  if str(root).encode() in command:need(b'control_entry.py' in command,'ACTIVE_SOURCE_OR_TARGET_WORKER')
source_owner=old[0]['owners'][SOURCE]
capture=json.loads(pathlib.Path(source_owner['sources'][SOURCE]['configurationPath']).read_bytes())
policy=dict(schemaVersion='SourceBackupEpochPolicy/v1',root='/var/lib/spug-backup-epochs/intruoyi-main-57',sourceIdentity=capture['source']['sourceIdentity'],databaseUuid=capture['source']['databaseUuid'],sourceLockPath=capture['sourceLockPath'])
target_owner=old[1]['owners'][TARGET]
need(document(old[0]['control']['sourceConfigurations'][SOURCE])==source_owner,'SOURCE_OWNER_CHANGED')
need(document(old[1]['control']['restoreConfigurations'][SOURCE][TARGET])==target_owner,'TARGET_OWNER_CHANGED')
replacement=target_owner['targets'][TARGET]['replacement']
need(replacement['lockPath']==policy['sourceLockPath'] and replacement['databaseUuid']==policy['databaseUuid'],'PHYSICAL_SOURCE_TARGET_MISMATCH')
lock=os.open(policy['sourceLockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts()
def verify_retained():
 for retained in RETAINED_PINS:
  path=pathlib.Path(retained['path']);first=path.lstat();digest=hashlib.sha256();size=0
  def identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
  need(path.resolve()==path and first.st_nlink==1,'FAILED_ORIGINAL_PATH_CHANGED')
  with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
   need(identity(os.fstat(stream.fileno()))==identity(first),'FAILED_ORIGINAL_CHANGED')
   while True:
    chunk=stream.read(1024*1024)
    if not chunk:break
    digest.update(chunk);size+=len(chunk)
   need(identity(os.fstat(stream.fileno()))==identity(first),'FAILED_ORIGINAL_CHANGED')
  need(identity(path.lstat())==identity(first) and size==retained['bytes'] and digest.hexdigest()==retained['sha256'],'FAILED_ORIGINAL_CHANGED')
verify_retained()
raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED')
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 version=json.load(archive.extractfile('package.json'));names=archive.getnames()
 need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'STANDARD_PACKAGE_REQUIRED')
 need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
 need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256']==MANIFEST_SHA,'PACKAGE_MANIFEST_CHANGED')
 for member in archive.getmembers():
  need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
  data=archive.extractfile(member).read()
  if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][member.name],'PACKAGE_MEMBER_CHANGED');compile(data,member.name,'exec')
 engines=[]
 for item in old:
  engine=pathlib.Path(item['control']['workingDirectory'])/('engine-automatic-'+COMMIT[:7])
  need(not engine.exists(),'GENERATION_ALREADY_EXISTS');engine.mkdir(mode=0o700)
  for member in archive.getmembers():
   destination=engine/member.name;destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700);write_new(destination,archive.extractfile(member).read())
  engines.append(engine)
def rebind(value,previous,engine):
 if isinstance(value,str):return value.replace(str(previous)+'/',str(engine)+'/')
 if isinstance(value,list):return [rebind(v,previous,engine) for v in value]
 if isinstance(value,dict):
  result={k:rebind(v,previous,engine) for k,v in value.items()}
  if set(('path','bytes','sha256'))<=set(result) and result['path']!=value['path']:result.update(pin(result['path']))
  return result
 return value
parent=pathlib.Path(policy['root']).parent
if not parent.exists():parent.mkdir(mode=0o700)
epoch_root=pathlib.Path(policy['root'])
if not epoch_root.exists():epoch_root.mkdir(mode=0o700)
sys.path.insert(0,str(engines[0]/'common'))
from recovery_backup_epoch import initialize,read_current
if any(epoch_root.iterdir()):
 need(REUSE_INITIALIZED_EPOCH,'EPOCH_ALREADY_INITIALIZED')
 epoch=read_current(policy);event=document(epoch['eventPin'])
 need(epoch['state']=='READY' and event['kind']=='INITIALIZED' and event['operationId'] is None,'ONLY_INITIALIZED_EPOCH_REUSABLE')
else:epoch=initialize(policy,lock)
need(epoch['state']=='READY','EPOCH_INITIALIZATION_FAILED')
new=[]
for index,item in enumerate(old):
 engine=engines[index];previous=pathlib.Path(item['args'][item['args'].index('-B')+1]).parent
 control=rebind(item['control'],previous,engine)
 root=pathlib.Path(control['workingDirectory']);generation='automatic-'+COMMIT[:7]
 if index==0:
  owner=rebind(source_owner,previous,engine)
  owner_pin=write_new(root/'configuration'/('repository-'+generation+'.json'),canonical(owner))
  control['sourceConfigurations'][SOURCE]=owner_pin
 else:
  owner=rebind(target_owner,previous,engine)
  need(owner['targets']==target_owner['targets'],'HISTORICAL_TARGET_CHANGED')
  need(owner['sources']==target_owner['sources'],'HISTORICAL_TARGET_SOURCE_CHANGED')
  owner['targetBackupEpochPolicies']={TARGET:policy}
  owner_pin=write_new(root/'configuration'/('recovery-'+generation+'.json'),canonical(owner))
  control['restoreConfigurations'][SOURCE][TARGET]=owner_pin
  control['sourceConfigurations'][SOURCE]=new[0]['ownerConfigurationPin']
 control['sourceEpochPolicies']={SOURCE:policy}
 control_pin=write_new(root/'configuration'/('control-'+generation+'.json'),canonical(control))
 for role in ('repository','recovery','control'):
  answer=json.loads(run([control['pythonPin']['path'],'-B',str(engine/(role+'_entry.py')),'--check-imports'],env=dict(os.environ,**control['environment'])))
  need(answer['role']==role,'ENTRY_IMPORT_FAILED')
 new.append(dict(service=item['unit'],engine=str(engine),ownerConfigurationPin=owner_pin,controlConfigurationPin=control_pin,control=control,previousPid=item['pid'],oldControlPin=item['controlPin']))
probe="import json,sys;from recovery_control_smallapp_native import Native;print(json.dumps(Native(json.loads(sys.argv[1])).incremental_plan(sys.argv[2])))"
plan=json.loads(run([new[0]['control']['pythonPin']['path'],'-B','-c',probe,canonical(new[0]['controlConfigurationPin']).decode(),SOURCE],timeout=40,env=dict(os.environ,**new[0]['control']['environment'])))
need(plan['state']=='BASELINE_REQUIRED','NEW_EPOCH_BASELINE_EXPECTED')
target_probe="import json,sys;from recovery_control_smallapp_native import Native;print(json.dumps(Native(json.loads(sys.argv[1])).selections(sys.argv[2])))"
target_selection=json.loads(run([new[1]['control']['pythonPin']['path'],'-B','-c',target_probe,canonical(new[1]['controlConfigurationPin']).decode(),TARGET],timeout=90,env=dict(os.environ,**new[1]['control']['environment'])))
need(any(TARGET in row['freshTargetConfigRefs'] for row in target_selection['applications']),'TARGET_CANDIDATE_NOT_AVAILABLE')
health_probe="""import json,subprocess,sys
from types import SimpleNamespace
from recovery_control_smallapp_native import Native
from recovery_replace import replacement_value
from recovery_main_health import preflight,endpoint,probe
n=Native(json.loads(sys.argv[1]));c=n.configuration();o=n.document(c['restoreConfigurations'][sys.argv[2]][sys.argv[3]]);t=o['targets'][sys.argv[3]]
r=replacement_value(o,sys.argv[3]);assert r['backupEpoch']==c['sourceEpochPolicies'][sys.argv[2]]
def inspect(identity):
 p=subprocess.run([t['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',identity],capture_output=True,timeout=10);assert p.returncode==0 and not p.stderr;rows=json.loads(p.stdout);assert len(rows)==1;return rows[0]
native=SimpleNamespace(config=t,config_services={s['role']:s for s in t['services']},inspect=inspect,frontend_readiness=o.get('frontendReadiness',{}).get(sys.argv[3]))
preflight(native);out={role:dict(url=endpoint(native,role),result=probe(endpoint(native,role),role,10)) for role in ('minio','backend','frontend')};assert all(v['result']['ready'] and v['result']['httpStatus']==200 for v in out.values());print(json.dumps(out))
"""
health=json.loads(run([new[1]['control']['pythonPin']['path'],'-B','-c',health_probe,canonical(new[1]['controlConfigurationPin']).decode(),SOURCE,TARGET],timeout=50,env=dict(os.environ,**new[1]['control']['environment'])))
staged=dict(status='STAGED',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=COMMIT,policy=policy,epoch=epoch,plan=plan,targetSemanticHealth=health,controllers=new,originalContainerCount=len(before),packageSha256=PACKAGE_SHA,fileManifestSha256=MANIFEST_SHA,fileCount=len(version['files']))
stagepath=pathlib.Path(old[0]['control']['workingDirectory'])/'configuration'/('staged-automatic-'+COMMIT[:7]+'.json')
write_new(stagepath,canonical(staged))
if not ACTIVATE:
 print(json.dumps(staged));sys.exit(0)
for item in reversed(new):
 control=item['control'];engine=pathlib.Path(item['engine'])
 directory=pathlib.Path('/etc/systemd/system')/(item['service']+'.d')
 existing=[path.name for path in directory.glob('*.conf')]
 leading=max([len(name)-len(name.lstrip('z')) for name in existing]+[0])+1
 dropin=directory/('z'*leading+'-automatic-'+COMMIT[:7]+'.conf')
 need(all(dropin.name>name for name in existing),'SERVICE_OVERRIDE_ORDER_INVALID')
 dropin.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
 command=control['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(item['controlConfigurationPin']).decode()+"'"
 text='[Service]\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n'
 write_new(dropin,text.encode());dropin.chmod(0o644)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',item['service']])
 need(run(['systemctl','is-active',item['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 pid=active_pid(item['service']);need(pid>1 and pid!=item['previousPid'],'NEW_CONTROL_PID_REQUIRED')
 args=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes();need(str(engine/'control_entry.py').encode() in args and item['controlConfigurationPin']['path'].encode() in args,'ACTIVATED_GENERATION_MISMATCH')
 limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_INVALID')
 item.update(pid=pid,dropinPin=pin(dropin))
 for attempt in range(21):
  try:selections=http(control,'/selections',90);break
  except urllib.error.URLError as error:
   if not isinstance(error.reason,ConnectionRefusedError) or attempt==20:raise
   time.sleep(1)
 item['selectionsHttp']=200
actual_plan=http(new[0]['control'],'/incremental-plan?sourceConfigRef='+SOURCE)
need(actual_plan['state']=='BASELINE_REQUIRED','ACTUAL_PLAN_INVALID')
need(snapshot()==before,'ORIGINAL_DOCKER_RUNTIME_CHANGED')
verify_retained()
need(pin('/etc/fstab')==fstab and mounts()==beforemounts,'PROTECTED_STORAGE_CHANGED')
for item in old:need(document(item['controlPin'])==item['control'],'OLD_CONTROL_CHANGED')
for engine in engines:need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'INSTALLED_PACKAGE_CHANGED')
result=dict(staged,status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=new,plan=actual_plan,allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,retainedFailureFilesPreserved=len(RETAINED_PINS),backupPerformed=False,restorePerformed=False)
write_new(pathlib.Path(old[0]['control']['workingDirectory'])/'configuration'/('installation-automatic-'+COMMIT[:7]+'.json'),canonical(result))
print(json.dumps(result))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--reuse-initialized-epoch', action='store_true')
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    build = json.loads((TASK / ('release-build-' + args.commit[:7] + '.json')).read_text(encoding='utf-8'))
    assert build['targetCommit'] == args.commit
    assert build['status'] == 'PASS' and build['fileCount'] == 130
    installed = json.loads((PRIVATE / 'automatic-57-installed.private.json').read_text(encoding='utf-8'))
    raw = (PRIVATE / ('package-' + args.commit[:7]) / 'backup-restore-standard.tgz').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == build['packageSha256']
    values = dict(INSTALLED=installed, COMMIT=build['targetCommit'], SOURCE=SOURCE,
                  TARGET='intruoyi-main-57-safe-restore-20261105-v2',
                  PACKAGE=base64.b64encode(raw).decode(), PACKAGE_SHA=build['packageSha256'],
                  MANIFEST_SHA=build['fileManifestSha256'], ACTIVATE=args.activate,
                  REUSE_INITIALIZED_EPOCH=args.reuse_initialized_epoch)
    retained = []
    first = json.loads((TASK / 'registered-binlog-tool-restored.json').read_text(encoding='utf-8'))
    retained.extend(first['failedOriginalPins'])
    for number in ('365', '366'):
        retained.extend(json.loads((PRIVATE / ('failed-' + number + '-all-pins.private.json')).read_text(encoding='utf-8'))['pins'])
    assert len(retained) == len({item['path'] for item in retained}) == 10044
    values['RETAINED_PINS'] = retained
    payload = '\n'.join(key + '=' + repr(value) for key, value in values.items()) + '\n' + SCRIPT
    compile(payload, '<automatic-57-installation>', 'exec')
    if args.prepare_only:
        print(json.dumps(dict(status='PASS', preparedOnly=True, remoteWrites=False,
                             scriptSha256=hashlib.sha256(payload.encode()).hexdigest())))
        raise SystemExit(0)
    output = PRIVATE / 'automatic-control-installation-57.private.json'
    assert not output.exists(), 'INSTALLATION_ALREADY_RECORDED'
    result = remote('172.30.30.57', payload, 400)
    write(output, result)
    public = {key: value for key, value in result.items() if key != 'controllers'}
    public['controllers'] = [{key: value for key, value in item.items() if key != 'control'}
                             for item in result['controllers']]
    write(TASK / 'automatic-control-installation-57.json', public)
    print(json.dumps(public))
