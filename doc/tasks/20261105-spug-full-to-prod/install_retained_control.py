"""Append a committed control generation while preserving History361 custody."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from install_prod_control import COMMON,PRIVATE,TASK,ROOT,HOST,PYTHON,DEPENDENCIES,APP,TARGET,POINT,UNIT,LOCK,remote

CHECK=r'''
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes())
need(receipt['sourceCommit']=='9b3a298ce378b3ac565792a3bc3b92f1e5208898' and receipt['targetConfigRef']==TARGET,'OLD_GENERATION_CHANGED')
need(receipt['ownerConfigurationPin']==EXPECTED_OWNER and receipt['controlConfigurationPin']==EXPECTED_CONTROL,'CONTROL_BINDING_CHANGED')
def read(reference):
 need(pin(reference['path'])==reference,'PIN_CHANGED');return json.loads(pathlib.Path(reference['path']).read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
version=json.loads((oldengine/'package.json').read_bytes())
need(len(version['files'])==124 and all(pin(oldengine/name)['sha256']==sha for name,sha in version['files'].items()),'OLD_PROGRAM_CHANGED')
for reference in FAILURE_PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
activepath=pathlib.Path('/var/lib/spug-restore-resources/active.json')
def retained():
 need(pin(activepath)==ACTIVE_POINTER,'RETAINED_POINTER_CHANGED')
 value=json.loads(activepath.read_bytes());need(value['operationId']==FAILED_OPERATION,'WRONG_RETAINED_OPERATION')
retained()
oldroot=root/'recovery-operations'/FAILED_OPERATION
original=json.loads((oldroot/'configuration.json').read_bytes());request=json.loads((oldroot/'request.json').read_bytes())
need(request['sourceConfigRef']==APP and request['targetConfigRef']==TARGET and request['recoveryPointRef']==POINT,'WRONG_RETAINED_REQUEST')
need(original['targets']==owner['targets'],'RETAINED_TARGET_CHANGED')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_control_restore_catalogue import bind_archive_chain
resolved,_binding=bind_archive_chain(owner['sources'][APP],request)
expected_sources=copy.deepcopy(owner['sources']);expected_sources[APP]=resolved
need(original['sources']==expected_sources,'RETAINED_RESOLVED_SOURCE_CHANGED')
result=json.loads((oldroot/'worker-result.json').read_bytes());exited=json.loads((oldroot/'child-exit.json').read_bytes())
need(result['state']=='FAILED_RETAINED' and result['actualExitCode']==1 and result['data']['mutationDispatched'] is True and exited['actualExitCode']==1 and exited['timedOut'] is False,'ORIGINAL_NOT_TERMINATED_FAILURE')
unit=pathlib.Path('/etc/systemd/system')/receipt['service'];oldunit=unit.read_bytes()
need(receipt['service']==UNIT,'WRONG_CONTROL_UNIT')
pid=int(run(['systemctl','show',UNIT,'-p','MainPID','--value']).strip())
cg=pathlib.Path('/sys/fs/cgroup/systemd/system.slice')/UNIT/'cgroup.procs'
need({int(v) for v in cg.read_text().split()}=={pid},'CONTROL_WORKERS_ACTIVE')
before=business(allrows());need(len(before)==195,'BUSINESS_SET_CHANGED')
fstab=pin('/etc/fstab');stage=pin(root/'installation.json')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
from recovery_retained_retry import observe
from recovery_main_target import archive_view,published_fence
from recovery_retained_retry import ReadOnlyTarget
fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 retained();observe(original,request,oldroot,0)
 native=ReadOnlyTarget(original,request,oldroot);native.original=request
 native.command=lambda arguments,**kwargs:run(arguments)
 archive_view(native).verify();published_fence(native).verify()
 need(not engine.exists(),'NEW_ENGINE_ALREADY_EXISTS')
 raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  package=json.load(archive.extractfile('package.json'))
  need(package['variant']=='standard' and package['fileVerification'] and package['payloadContentVerification'],'SAFE_REQUIRED')
  need(len(package['files'])==125 and len(archive.getnames())==126 and set(archive.getnames())==set(package['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
  need(hashlib.sha256(canonical(package['files'])).hexdigest()==package['packageSha256'],'PACKAGE_MANIFEST_CHANGED')
  for member in archive.getmembers():
   need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
   data=archive.extractfile(member).read()
   if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==package['files'][member.name],'PACKAGE_CONTENT_CHANGED');compile(data,member.name,'exec')
  engine.mkdir(mode=0o700)
  for member in archive.getmembers():
   path=engine/member.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);write(path,archive.extractfile(member).read(),raw=True)
 newowner=copy.deepcopy(owner);newowner['formalModuleDirectory']=str(engine/'formal')
 ownerpin=write(root/'configuration'/('main-recovery-'+generation+'.json'),newowner)
 newcontrol=copy.deepcopy(control)
 newcontrol['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(str(oldengine)+'/',str(engine)+'/')
 need(newcontrol['environment']['PYTHONPATH']!=control['environment']['PYTHONPATH'],'PYTHONPATH_NOT_UPDATED')
 for role in newcontrol['programPins']:newcontrol['programPins'][role]=pin(engine/(role+'_entry.py'))
 need(newcontrol['restoreConfigurations'][APP][TARGET]==receipt['ownerConfigurationPin'],'OWNER_BINDING_CHANGED')
 newcontrol['restoreConfigurations'][APP][TARGET]=ownerpin
 controlpin=write(root/'configuration'/('control-43657-'+generation+'.json'),newcontrol)
 code='import json,sys;from recovery_control_smallapp_native import Native;from recovery_mysql_scheduler import MainMysqlScheduler;Native(json.loads(sys.argv[1])).configuration();print("VALID")'
 checked=subprocess.run([PYTHON,'-B','-c',code,canonical(controlpin).decode()],env=dict(os.environ,**newcontrol['environment']),capture_output=True,timeout=55)
 need(checked.returncode==0 and checked.stdout.strip()==b'VALID','NEW_CONTROL_CONFIGURATION_INVALID')
 need(oldunit.count(canonical(receipt['controlConfigurationPin']))==1,'UNIT_BINDING_CHANGED')
 write(root/'configuration'/(generation+'-receipt-before.json'),receipt)
 write(root/'configuration'/(generation+'-unit-before.service'),oldunit,raw=True)
 newunit=oldunit.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)).replace((str(oldengine)+'/').encode(),(str(engine)+'/').encode())
 need(newunit!=oldunit and business(allrows())==before,'PRE_ACTIVATION_RUNTIME_CHANGED')
 unit.write_bytes(newunit);run(['systemctl','daemon-reload']);run(['systemctl','restart',UNIT])
 need(run(['systemctl','is-active',UNIT]).strip()==b'active','CONTROL_NOT_ACTIVE')
 newpid=int(run(['systemctl','show',UNIT,'-p','MainPID','--value']).strip())
 limit=next(v for v in pathlib.Path('/proc',str(newpid),'limits').read_text().splitlines() if v.startswith('Max open files'))
 need(limit.split()[3:5]==['65536','65536'],'LIVE_FD_BUDGET_CHANGED')
 receipt.update(sourceCommit=COMMIT,engine=str(engine),ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin,liveFdLimit=limit)
 temp=receiptpath.with_name('target-installation.'+generation+'.tmp');write(temp,receipt);temp.replace(receiptpath)
 need(business(allrows())==before and pin('/etc/fstab')==fstab and pin(root/'installation.json')==stage,'ORIGINAL_RUNTIME_CHANGED')
 retained()
 for reference in FAILURE_PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
 need(all(pin(engine/name)['sha256']==sha for name,sha in package['files'].items()),'INSTALLED_PACKAGE_CHANGED')
 out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=COMMIT,
  packageSha256=PACKAGE_SHA,fileManifestSha256=package['packageSha256'],fileCount=len(package['files']),engine=str(engine),
  ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin,targetAndSourceUnchanged=newowner['targets']==owner['targets'] and newowner['sources']==owner['sources'],
  protectedOriginalFailurePinsUnchanged=len(FAILURE_PINS),retainedPointerUnchanged=True,original195RuntimeUnchanged=True,
  fstabAndOldStageUnchanged=True,oldProtectionsStillActive=True,liveFdLimit=limit,restoreDispatched=False)
 write(root/'configuration'/(generation+'-retained-installation.json'),out);print(json.dumps(out))
os.close(fd)
'''


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    commit=args.commit;assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
    build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf-8'))
    assert build['status']=='PASS' and build['targetCommit']==commit and build['fileCount']==125
    failure=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    installed=json.loads((TASK/'control-configure-installation.json').read_text(encoding='utf-8'))
    raw=(PRIVATE/('package-'+commit[:7])/'backup-restore-standard.tgz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
    assert len(failure['evidencePins'])==205 and failure['database']['tableCount']==0
    values=dict(ROOT=ROOT,ENGINE=ROOT+'/engine-mainv2-'+commit[:7],HOST=HOST,COMMIT=commit,PYTHON=PYTHON,
        DEPENDENCIES=DEPENDENCIES,APP=APP,TARGET=TARGET,POINT=POINT,UNIT=UNIT,LOCK=LOCK,
        EXPECTED_OWNER=installed['ownerConfigurationPin'],EXPECTED_CONTROL=installed['controlConfigurationPin'],
        FAILED_OPERATION=failure['operationId'],FAILURE_PINS=failure['evidencePins'],ACTIVE_POINTER=failure['activePointerPin'],
        PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'])
    script='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+COMMON.split('need(root.resolve()==root')[0]+'\n'+CHECK
    report=remote(script,180)
    (TASK/'retained-control-installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
