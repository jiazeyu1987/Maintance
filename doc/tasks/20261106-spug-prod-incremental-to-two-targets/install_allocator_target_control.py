"""Install only a verified committed immutable target control generation."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from common import TASK, PRIVATE, now, remote, write

SCRIPT = r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile,time
root=pathlib.Path(ROOT);generation='allocator-'+COMMIT[:7];engine=root/('engine-'+generation)
def need(value,code):
 if not value:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(p):
 p=pathlib.Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):need(pin(ref['path'])==ref,'PIN_CHANGED');return json.loads(pathlib.Path(ref['path']).read_bytes())
def run(args,env=None,timeout=45):
 p=subprocess.run(args,capture_output=True,env=env,timeout=timeout);need(p.returncode==0 and not p.stderr,'CONTROL_INSTALL_COMMAND_FAILED');return p.stdout
def create(p,raw):
 need(p.resolve()==p and p.parent.resolve()==p.parent,'INSTALL_PATH_ALIAS')
 with os.fdopen(os.open(p,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600),'wb') as f:
  f.write(raw);f.flush();os.fsync(f.fileno())
 need(p.read_bytes()==raw,'INSTALL_READBACK_FAILED');return pin(p)
def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
original_states={}
def verify_failure(full):
 deadline=time.monotonic()+890
 for ref in FAILURE_PINS:
  p=pathlib.Path(ref['path']);before=p.lstat()
  need(p.resolve()==p and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'FAILURE_PATH_INVALID')
  if full:
   sha=hashlib.sha256();size=0
   with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
    need(identity(os.fstat(stream.fileno()))==identity(before),'FAILURE_IDENTITY_CHANGED')
    while True:
     need(time.monotonic()<deadline,'FAILURE_READ_DEADLINE');raw=stream.read(1024*1024)
     if not raw:break
     sha.update(raw);size+=len(raw)
    need(identity(os.fstat(stream.fileno()))==identity(before),'FAILURE_IDENTITY_CHANGED')
   need(size==ref['bytes'] and sha.hexdigest()==ref['sha256'],'ORIGINAL_FAILURE_CHANGED')
   original_states[str(p)]=identity(before)
  else:
   need(identity(before)==original_states[str(p)],'ORIGINAL_FAILURE_IDENTITY_CHANGED')
   if ref['bytes']<1024*1024:need(pin(p)==ref,'ORIGINAL_FAILURE_CHANGED')
  need(identity(p.lstat())==identity(before),'ORIGINAL_FAILURE_CHANGED')
def snapshot():
 ids=run(['docker','ps','-aq','--no-trunc']).decode().split()
 rows=json.loads(run(['docker','inspect',*ids]))
 return {r['Id']:dict(state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},
  definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Config','HostConfig','Path','Args','Image')},
   Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():
 paths=['/mnt/nas','/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas']
 return sorted(' '.join(l.split()[1:]) for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines()
  if any(p==l.split()[4] or p.startswith(l.split()[4].rstrip('/')+'/') or l.split()[4].startswith(p.rstrip('/')+'/') for p in paths))
need(root.resolve()==root and not engine.exists(),'GENERATION_EXISTS_OR_ROOT_ALIAS')
receiptpath=root/'target-installation.json';need(pin(receiptpath)==PREFLIGHT['receiptPin'],'OLD_RECEIPT_CHANGED')
receipt=json.loads(receiptpath.read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
need(receipt['targetConfigRef']==TARGET,'WRONG_TARGET');target=owner['targets'][TARGET]
oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
oldversion=json.loads((oldengine/'package.json').read_bytes())
need(all(pin(oldengine/name)['sha256']==sha for name,sha in oldversion['files'].items()),'OLD_ENGINE_CHANGED')
lock=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
from recovery_retained_retry import observe
activepath=pathlib.Path('/var/lib/spug-restore-resources/active.json')
def reservation():
 if SUFFIX=='58' and CLEARANCE is not None:
  from recovery_retained_retry import validate_clearance
  claim=pathlib.Path(target['replacement']['stateRoot'])/FAILED_OPERATION
  need(not activepath.exists() and not (claim/'recovery-consumption.json').exists(),'CLEARED_TARGET_STATE_CHANGED')
  need(read(CLEARANCE['clearancePin'])==validate_clearance(target,claim) and CLEARANCE['clearancePin']==PREFLIGHT['retainedClearancePin'],'RETAINED_CLEARANCE_CHANGED')
 elif SUFFIX=='58':need(pin(activepath)==PREFLIGHT['activePointerPin'],'RETAINED_POINTER_CHANGED')
 else:need(not activepath.exists(),'ACTIVE_RESERVATION')
def workers():
 pid_row=run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip()
 need(pid_row.startswith('MainPID=') and pid_row.count('=')==1,'CONTROL_PID_PROPERTY_INVALID')
 pid=int(pid_row.split('=',1)[1])
 found=[]
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdecimal():continue
  try:cmd=(proc/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  if str(root).encode() in cmd:
   need(b'control_entry.py' in cmd and int(proc.name)==pid,'ACTIVE_TARGET_WORKER');found.append(pid)
 need(found==[pid] and pid>1,'CONTROL_PROCESS_CHANGED');return pid
with _host_lock():
 reservation();oldpid=workers();before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts()
 if SUFFIX=='58':
  oldroot=root/'recovery-operations'/FAILED_OPERATION
  original=json.loads((oldroot/'configuration.json').read_bytes());request=json.loads((oldroot/'request.json').read_bytes())
  need(original['targets']==owner['targets'] and request['recoveryPointRef']==POINT,'RETAINED_BINDING_CHANGED')
  observe(original,request,oldroot,885)
 verify_failure(True)
 custody_pin=create(root/'configuration'/('failure-custody-'+generation+'.json'),canonical(dict(
  schemaVersion='TaskFailureCustody/v1',operationId=FAILED_OPERATION,originalPins=FAILURE_PINS,
  identities=original_states,fullShaRead=True))) if FAILURE_PINS else None
 raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  version=json.load(archive.extractfile('package.json'));names=archive.getnames()
  need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_REQUIRED')
  need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
  need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256']==MANIFEST_SHA,'PACKAGE_MANIFEST_CHANGED')
  for member in archive.getmembers():
   need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
   data=archive.extractfile(member).read()
   if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][member.name],'PACKAGE_FILE_CHANGED');compile(data,member.name,'exec')
  engine.mkdir(mode=0o700)
  for member in archive.getmembers():
   p=engine/member.name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(p,archive.extractfile(member).read())
 newowner=copy.deepcopy(owner);newowner['formalModuleDirectory']=str(engine/'formal')
 need(newowner['targets']==owner['targets'] and newowner['sources']==owner['sources'],'TARGET_OR_SOURCE_CHANGED')
 ownerpin=create(root/'configuration'/('main-recovery-'+generation+'.json'),canonical(newowner))
 newcontrol=copy.deepcopy(control)
 newcontrol['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(str(oldengine)+'/',str(engine)+'/')
 need(newcontrol['environment']['PYTHONPATH']!=control['environment']['PYTHONPATH'],'PYTHONPATH_NOT_REBOUND')
 for role in newcontrol['programPins']:newcontrol['programPins'][role]=pin(engine/(role+'_entry.py'))
 need(newcontrol['restoreConfigurations'][APP][TARGET]==receipt['ownerConfigurationPin'],'OWNER_BINDING_CHANGED')
 newcontrol['restoreConfigurations'][APP][TARGET]=ownerpin
 controlpin=create(root/'configuration'/('control-'+SUFFIX+'-'+generation+'.json'),canonical(newcontrol))
 code='import json,sys;from recovery_control_smallapp_native import Native;from recovery_minimal_runtime import modules_from;modules=modules_from(sys.argv[2]);assert callable(modules["formal_schema_evidence"].restore_frozen_auto_increment);native=Native(json.loads(sys.argv[1]));native.configuration();print("VALID")'
 if LEGACY_VERIFIED:
  code=code.replace('print("VALID")','document=native.selections(selected_target=sys.argv[3]);assert sys.argv[3] in next(a for a in document["applications"] if a["sourceConfigRef"]==sys.argv[4])["freshTargetConfigRefs"];print("VALID")')
 need(run([newcontrol['pythonPin']['path'],'-B','-c',code,canonical(controlpin).decode(),str(engine/'formal'),TARGET,APP],env=dict(os.environ,**newcontrol['environment']),timeout=120).strip()==b'VALID','NEW_CONFIGURATION_INVALID')
 archive_receipt=create(root/'configuration'/(generation+'-previous-target-installation.json'),receiptpath.read_bytes())
 create(root/'configuration'/(generation+'-previous-unit.txt'),run(['systemctl','cat',receipt['service']]))
 dropin=pathlib.Path('/etc/systemd/system')/(receipt['service']+'.d')/({None:'zz-','r2':'zzz-','r3':'zzzz-'}[REVISION]+generation+'.conf')
 dropin.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
 command=newcontrol['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(controlpin).decode()+"'"
 text='[Service]\nEnvironment=PYTHONPATH='+newcontrol['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n'
 dropinpin=create(dropin,text.encode());dropin.chmod(0o644)
 need(snapshot()==before and pin('/etc/fstab')==fstab and mounts()==beforemounts,'PRE_ACTIVATION_BUSINESS_CHANGED')
 workers();reservation();verify_failure(False)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 pid=workers();need(pid!=oldpid,'CONTROL_NOT_RELOADED')
 cmd=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes()
 need(str(engine/'control_entry.py').encode() in cmd and str(controlpin['path']).encode() in cmd,'WRONG_ACTIVE_GENERATION')
 limit=next(l for l in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if l.startswith('Max open files'))
 need(limit.split()[3:5]==['65536','65536'],'LIVE_FD_LIMIT_CHANGED')
 need(snapshot()==before and pin('/etc/fstab')==fstab and mounts()==beforemounts,'ORIGINAL_RUNTIME_CHANGED')
 reservation();verify_failure(False)
 need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'INSTALLED_ENGINE_CHANGED')
 need(pin(receipt['ownerConfigurationPin']['path'])==receipt['ownerConfigurationPin'] and pin(receipt['controlConfigurationPin']['path'])==receipt['controlConfigurationPin'],'OLD_CONFIGURATION_CHANGED')
 updated=dict(receipt,sourceCommit=COMMIT,engine=str(engine),ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 tmp=receiptpath.with_name('target-installation.'+generation+'.tmp');create(tmp,canonical(updated));tmp.replace(receiptpath)
 out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=COMMIT,
  host='172.30.30.'+SUFFIX,service=receipt['service'],engine=str(engine),fileCount=len(version['files']),
  packageSha256=PACKAGE_SHA,fileManifestSha256=version['packageSha256'],ownerConfigurationPin=ownerpin,
  controlConfigurationPin=controlpin,previousReceiptPin=archive_receipt,currentReceiptPin=pin(receiptpath),dropinPin=pin(dropin),
  oldControlPid=oldpid,controlPid=pid,liveMaxOpenFiles=65536,originalContainerCount=len(before),
  allBusinessDefinitionsAndRuntimeUnchanged=True,fstabAndProtectedMountsUnchanged=True,
  targetAndSourceConfigurationUnchanged=True,failedOriginalFilesPreserved=len(FAILURE_PINS),
  failedOriginalBytesRead=sum(p['bytes'] for p in FAILURE_PINS),retainedReservationUnchanged=SUFFIX=='58' and CLEARANCE is None,
  retainedClearanceUnchanged=CLEARANCE is not None,actualSelectionVerifiedBeforeActivation=LEGACY_VERIFIED,
  failureCustodyPin=custody_pin,previousGenerationsRetained=True,restoreDispatched=False)
 create(root/'configuration'/('installation-'+generation+'.json'),canonical(out))
 print(json.dumps(out))
os.close(lock)
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);parser.add_argument('--commit',required=True);parser.add_argument('--revision',choices=['r2','r3']);args=parser.parse_args()
    kind='allocator-target-installation-'+args.suffix+('-'+args.revision if args.revision else '')
    assert not (TASK/(kind+'.json')).exists()
    build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf8'))
    assert build['status']=='PASS' and build['targetCommit']==args.commit and not build['newCommits']
    regression=json.loads((TASK/'allocator-regression-5.json').read_text(encoding='utf8'))
    assert regression['expectedResultObserved'] and regression['inputFilesUnchanged'] and regression['isolatedProcesses']
    assert json.loads((TASK/'allocator-real-green-3.json').read_text(encoding='utf8'))['status']=='PASS'
    legacy=json.loads((TASK/'legacy-clearance-implementation-commit.json').read_text(encoding='utf8')) if (TASK/'legacy-clearance-implementation-commit.json').exists() else None
    if legacy is not None:
        assert legacy['implementationCommit']==args.commit and legacy['status']=='PASS'
        report=json.loads((TASK/'legacy-clearance-regression-1.json').read_text(encoding='utf8'))
        assert report['expectedResultObserved'] and report['inputFilesUnchanged'] and report['containerRemoved']
    preflight=json.loads((TASK/('allocator-upgrade-preflight-'+args.suffix+('-'+args.revision if args.revision else '')+'.json')).read_text(encoding='utf8'))
    raw=(PRIVATE/('package-'+args.commit[:7])/'backup-restore-standard.tgz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
    failure=json.loads((PRIVATE/'failed-368-all-pins.private.json').read_text(encoding='utf8')) if args.suffix=='58' else dict(pins=[])
    variables=dict(ROOT=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',
        SUFFIX=args.suffix,COMMIT=args.commit,REVISION=args.revision,TARGET='intruoyi-main-'+args.suffix+'-safe-restore-20261104-v1',APP='intruoyi-57-safe-20261024-v1',
        FAILED_OPERATION='smallapp-c21bb7ce9f5b4668b850c37a80964786',POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',
        PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'],MANIFEST_SHA=build['fileManifestSha256'],
        PREFLIGHT=preflight,FAILURE_PINS=failure['pins'],LEGACY_VERIFIED=legacy is not None,
        CLEARANCE=json.loads((TASK/'allocator-retained-recovery-clearance-58.json').read_text(encoding='utf8')) if args.suffix=='58' and args.revision=='r3' else None)
    result=remote('172.30.30.'+args.suffix,'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,1000)
    write(TASK/(kind+'.json'),result);print(json.dumps(result))
