"""Install a committed SAFE generation, preserving failed operation custody."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from preflight import COMMON,PRIVATE,TASK,remote

CHECK=r'''
import copy,inspect
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes())
need(receipt['ownerConfigurationPin']==BEFORE['ownerConfigurationPin'] and receipt['controlConfigurationPin']==BEFORE['controlConfigurationPin'],'CONTROL_GENERATION_DRIFT')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
oldversion=json.loads((oldengine/'package.json').read_bytes())
need(all(pin(oldengine/n)['sha256']==h for n,h in oldversion['files'].items()),'OLD_PACKAGE_DRIFT')
before=business();need(before==BEFORE['business'],'BUSINESS_DRIFT')
for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
def reservation_current():
 active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
 if RETAINED_ACTIVE is None:need(not active.exists(),'ACTIVE_RESERVATION')
 else:
  need(pin(active)==RETAINED_ACTIVE and read(RETAINED_ACTIVE)['operationId']==RETAINED_OPERATION,'RETAINED_RESERVATION_CHANGED')
  op=root/'recovery-operations'/RETAINED_OPERATION
  result=json.loads((op/'worker-result.json').read_bytes());exited=json.loads((op/'child-exit.json').read_bytes())
  need(result['state']=='FAILED_RETAINED' and result['actualExitCode']==1 and result['data']['mutationDispatched'] is True and exited['actualExitCode']==1 and exited['timedOut'] is False,'RETAINED_FAILURE_NOT_PROVEN')
reservation_current()
unit=pathlib.Path('/etc/systemd/system')/receipt['service'];oldunit=unit.read_bytes()
pid=int(run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip().split('=',1)[1])
cg=pathlib.Path('/sys/fs/cgroup/systemd/system.slice')/receipt['service']/'cgroup.procs'
need({int(v) for v in cg.read_text().split()}=={pid},'CONTROL_WORKERS_ACTIVE')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
fd=os.open(owner['targets'][receipt['targetConfigRef']]['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
engine=root/('engine-retry-'+COMMIT[:8]);generation='retry-'+COMMIT[:8]
with _host_lock():
 reservation_current()
 need(not engine.exists(),'GENERATION_ALREADY_EXISTS')
 raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_DRIFT')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  version=json.load(archive.extractfile('package.json'))
  need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_REQUIRED')
  need(set(archive.getnames())==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
  need(hashlib.sha256(json.dumps(version['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==version['packageSha256'],'MANIFEST_DRIFT')
  for item in archive.getmembers():
   need(item.isfile() and not pathlib.PurePosixPath(item.name).is_absolute() and '..' not in pathlib.PurePosixPath(item.name).parts,'UNSAFE_PACKAGE_PATH')
   data=archive.extractfile(item).read()
   if item.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][item.name],'PACKAGE_CONTENT_DRIFT');compile(data,item.name,'exec')
  engine.mkdir(mode=0o700)
  for item in archive.getmembers():
   path=engine/item.name;path.parent.mkdir(parents=True,mode=0o700,exist_ok=True);append(path,archive.extractfile(item).read(),raw=True)
 newowner=copy.deepcopy(owner);newowner['formalModuleDirectory']=str(engine/'formal')
 ownerpin=append(root/'configuration'/('main-recovery-'+generation+'.json'),newowner)
 newcontrol=copy.deepcopy(control)
 newcontrol['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(str(oldengine)+'/',str(engine)+'/')
 need(newcontrol['environment']['PYTHONPATH']!=control['environment']['PYTHONPATH'],'PATH_NOT_UPDATED')
 for role in newcontrol['programPins']:newcontrol['programPins'][role]=pin(engine/(role+'_entry.py'))
 source='intruoyi-57-safe-20261024-v1';target=receipt['targetConfigRef']
 need(newcontrol['restoreConfigurations'][source][target]==receipt['ownerConfigurationPin'],'OWNER_REFERENCE_DRIFT')
 newcontrol['restoreConfigurations'][source][target]=ownerpin
 controlpin=append(root/'configuration'/('control-33659-'+generation+'.json'),newcontrol)
 env=dict(os.environ,**newcontrol['environment'])
 code='import inspect,json,sys;from recovery_control_smallapp_native import Native;from recovery_retained_retry import authorize;Native(json.loads(sys.argv[1])).configuration();assert "no_mutation" in inspect.signature(authorize).parameters;print("VALID")'
 arguments=[canonical(controlpin).decode()]
 if RETAINED_ACTIVE is not None:
  code=code.replace(';print("VALID")',';from pathlib import Path;from recovery_retained_retry import observe;observe(json.loads(Path(sys.argv[2]).read_bytes()),json.loads((Path(sys.argv[3])/"request.json").read_bytes()),Path(sys.argv[3]),0);print("VALID")')
  arguments += [ownerpin['path'],str(root/'recovery-operations'/RETAINED_OPERATION)]
 result=subprocess.run([control['pythonPin']['path'],'-B','-c',code,*arguments],env=env,capture_output=True,timeout=55)
 need(result.returncode==0 and result.stdout.strip()==b'VALID','NEW_CONFIGURATION_OR_RETRY_INVALID')
 need(oldunit.count(canonical(receipt['controlConfigurationPin']))==1,'UNIT_BINDING_INVALID')
 append(root/'configuration'/(generation+'-receipt-before.json'),receipt)
 append(root/'configuration'/(generation+'-unit-before.service'),oldunit,raw=True)
 newunit=oldunit.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)).replace((str(oldengine)+'/').encode(),(str(engine)+'/').encode())
 need(newunit!=oldunit and business()==before,'PRE_ACTIVATION_DRIFT')
 unit.write_bytes(newunit);run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 newpid=int(run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip().split('=',1)[1])
 limit=next(line for line in pathlib.Path('/proc',str(newpid),'limits').read_text().splitlines() if line.startswith('Max open files'))
 need(limit.split()[3:5]==['65536','65536'],'FD_BUDGET_CHANGED')
 receipt.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 temp=receiptpath.with_name('target-installation.'+generation+'.tmp');append(temp,receipt);temp.replace(receiptpath)
 need(business()==before,'BUSINESS_RUNTIME_CHANGED')
 reservation_current()
 for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
 need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'INSTALLED_PACKAGE_DRIFT')
 out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','sourceCommit':COMMIT,'packageSha256':PACKAGE_SHA,'fileManifestSha256':version['packageSha256'],'fileCount':len(version['files']),'engine':str(engine),'ownerConfigurationPin':ownerpin,'controlConfigurationPin':controlpin,'targetAndSourceUnchanged':newowner['targets']==owner['targets'] and newowner['sources']==owner['sources'],'actualControlConfigurationValidated':True,'liveLimits':limit,'allBusinessIdsPidsStartTimesConfigurationUnchanged':True,'protectedOriginalFailurePinsUnchanged':len(PINS),'restoreDispatched':False}
 append(root/'configuration'/(generation+'-installation.json'),out);print(json.dumps(out))
os.close(fd)
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);parser.add_argument('--package',required=True)
    parser.add_argument('--retained-failure',type=Path)
    args=parser.parse_args();raw=Path(args.package).read_bytes()
    before=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    if (TASK/'retry-control-installation.json').exists():
        installed=json.loads((TASK/'retry-control-installation.json').read_text(encoding='utf-8'))
        for key in ('ownerConfigurationPin','controlConfigurationPin'):before[key]=installed[key]
    pins=json.loads((TASK/'archive-budget-diagnosis.json').read_text(encoding='utf-8'))['evidencePins']
    if (TASK/'second-failure-diagnosis.json').exists():pins+=json.loads((TASK/'second-failure-diagnosis.json').read_text(encoding='utf-8'))['evidencePins']
    retained_active=None;retained_operation=None
    if args.retained_failure:
        failure=json.loads(args.retained_failure.read_text(encoding='utf-8'))
        assert failure['database']['tableCount']==0 and failure['activeReservation'] is True and failure['idleControl'] is True
        retained_operation=failure['operationId']
        assert retained_operation==json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
        before['business']=failure['business'];retained_active=failure['activePointerPin'];pins+=failure['evidencePins']
    values={'BEFORE':before,'PINS':pins,
            'RETAINED_ACTIVE':retained_active,'RETAINED_OPERATION':retained_operation,
            'COMMIT':args.commit,'PACKAGE':base64.b64encode(raw).decode(),'PACKAGE_SHA':hashlib.sha256(raw).hexdigest()}
    script=COMMON.split('receiptpath=root/')[0]+'\n'+'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+CHECK
    out=remote('172.30.30.59',script,150)
    (TASK/'retry-control-installation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out))
