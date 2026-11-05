"""Only update the already authorized .59 control; never start business services."""
import base64
import hashlib
import json
from pathlib import Path
from resume_readonly import PRIVATE, TASK, remote

COMMIT='04f5f9ce958b52479c0c729fe32dbb69669e73fb'
PACKAGE=PRIVATE/'review-control-release-04f5f9ce/backup-restore-standard.tgz'
SCRIPT=r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
engine=root/'engine-readback-04f5f9ce'
def need(v,code):
 if not v:raise AssertionError(code)
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def pin(p):
 p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):
 need(pin(p['path'])==p,'INSTALLED_PIN_CHANGED');return json.loads(pathlib.Path(p['path']).read_bytes())
def append(p,d,raw=False):
 b=d if raw else canonical(d)
 with p.open('xb') as f:os.chmod(p,0o600);f.write(b);f.flush();os.fsync(f.fileno())
 need(p.read_bytes()==b,'INSTALL_READBACK_FAILED');return pin(p)
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=35);need(p.returncode==0,'CONTROL_QUERY_FAILED');return p.stdout
def business():
 ids=run(['docker','ps','--all','--no-trunc','--format','{{.ID}}']).decode().split()
 rows=json.loads(run(['docker','inspect',*ids]))
 return {r['Id']:{'name':r['Name'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],
   'running':r['State']['Running'],'image':r['Image'],
   'configurationSha256':hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','Config','HostConfig')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()}
   for r in rows}
receiptpath=root/'target-installation.json'
need(pin(receiptpath)==EXPECTED_RECEIPT_PIN,'RECEIPT_DRIFT')
receipt=json.loads(receiptpath.read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
need(receipt['ownerConfigurationPin']==EXPECTED_OWNER_PIN and receipt['controlConfigurationPin']==EXPECTED_CONTROL_PIN,'CONTROL_GENERATION_DRIFT')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
from formal_data_evidence import validate_limits
oldrejection=None
try:validate_limits(owner['dataLimits'])
except Exception as e:oldrejection=getattr(e,'code',str(e))
need(oldrejection=='FORMAL_DATA_LIMITS_REQUIRED','EXPECTED_INVALID_OLD_DATA_LIMITS')
oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
oldversion=json.loads((oldengine/'package.json').read_bytes())
need(all(pin(oldengine/n)['sha256']==h for n,h in oldversion['files'].items()),'OLD_PACKAGE_DRIFT')
unit=pathlib.Path('/etc/systemd/system')/receipt['service'];unitbefore=unit.read_bytes()
need(hashlib.sha256(unitbefore).hexdigest()==EXPECTED_UNIT_SHA,'UNIT_DRIFT')
before=business();need(before==EXPECTED_BUSINESS,'BUSINESS_DRIFT')
lockpath=pathlib.Path(owner['targets'][receipt['targetConfigRef']]['replacement']['lockPath'])
need(lockpath.is_file() and not lockpath.is_symlink(),'EXISTING_RESOURCE_LOCK_REQUIRED')
fd=os.open(lockpath,os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESTORE_RESERVATION')
 for name in ('ledger','operations','recovery-operations'):
  need(not [p for p in (root/name).rglob('*') if p.is_file() and p.name!='service.lock'],'EXISTING_OPERATION_RECORDS')
 need(not [p for p in (root/'replacement-state').rglob('*') if p.is_file()],'EXISTING_REPLACEMENT_RECORDS')
 need(not engine.exists(),'GENERATION_EXISTS')
 raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_DRIFT')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  version=json.load(archive.extractfile('package.json'))
  need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_REQUIRED')
  need(set(archive.getnames())==set(version['files'])|{'package.json'},'PACKAGE_FILES_INVALID')
  need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256'],'MANIFEST_DRIFT')
  for item in archive.getmembers():
   need(item.isfile() and not pathlib.PurePosixPath(item.name).is_absolute() and '..' not in pathlib.PurePosixPath(item.name).parts,'UNSAFE_PACKAGE_PATH')
   data=archive.extractfile(item).read()
   if item.name!='package.json':
    need(hashlib.sha256(data).hexdigest()==version['files'][item.name],'PACKAGE_CONTENT_DRIFT');compile(data,item.name,'exec')
  engine.mkdir(mode=0o700)
  for item in archive.getmembers():
   path=engine/item.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   append(path,archive.extractfile(item).read(),raw=True)
 newowner=copy.deepcopy(owner);newowner['formalModuleDirectory']=str(engine/'formal');newowner['dataLimits']['max_bytes']=16*1024**3
 need(validate_limits(newowner['dataLimits'])==newowner['dataLimits'],'NEW_DATA_LIMITS_INVALID')
 need(newowner['targets']==owner['targets'] and newowner['sources']==owner['sources'] and newowner['maxExpandedBytes']==owner['maxExpandedBytes'],'TARGET_OR_SOURCE_CHANGED')
 ownerpin=append(root/'configuration/main-recovery-readback-04f5f9ce.json',newowner)
 newcontrol=copy.deepcopy(control)
 newcontrol['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(str(oldengine)+'/',str(engine)+'/')
 need(newcontrol['environment']['PYTHONPATH']!=control['environment']['PYTHONPATH'],'CONTROL_PATH_NOT_UPDATED')
 for role in newcontrol['programPins']:newcontrol['programPins'][role]=pin(engine/(role+'_entry.py'))
 source='intruoyi-57-safe-20261024-v1';target=receipt['targetConfigRef']
 need(newcontrol['restoreConfigurations'][source][target]==receipt['ownerConfigurationPin'],'OWNER_REFERENCE_DRIFT')
 newcontrol['restoreConfigurations'][source][target]=ownerpin
 controlpin=append(root/'configuration/control-33659-readback-04f5f9ce.json',newcontrol)
 env=dict(os.environ,**newcontrol['environment'])
 verify=subprocess.run([control['pythonPin']['path'],'-B','-c',
  'import json,pathlib,sys; from recovery_control_smallapp_native import Native; from formal_data_evidence import validate_limits; p=json.loads(sys.argv[1]); c=Native(p).configuration(); o=json.loads(pathlib.Path(c["restoreConfigurations"]["intruoyi-57-safe-20261024-v1"][sys.argv[2]]["path"]).read_bytes()); validate_limits(o["dataLimits"]); print("VALID")',
  canonical(controlpin).decode(),target],env=env,capture_output=True,timeout=25)
 need(verify.returncode==0 and verify.stdout.strip()==b'VALID','ACTUAL_NEW_CONTROL_CONFIGURATION_INVALID')
 need(unitbefore.count(canonical(receipt['controlConfigurationPin']))==1 and unitbefore.count((str(oldengine)+'/control_entry.py').encode())==1,'UNIT_BINDING_INVALID')
 append(root/'configuration/readback-04f5f9ce-receipt-before.json',receipt)
 append(root/'configuration/readback-04f5f9ce-unit-before.service',unitbefore,raw=True)
 updated=unitbefore.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)).replace((str(oldengine)+'/').encode(),(str(engine)+'/').encode())
 need(pin(receiptpath)==EXPECTED_RECEIPT_PIN and business()==before,'PRE_ACTIVATION_DRIFT')
 unit.write_bytes(updated)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 receipt.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 temp=receiptpath.with_name('target-installation.readback-04f5f9ce.tmp');append(temp,receipt);temp.replace(receiptpath)
 need(business()==before,'BUSINESS_STATE_CHANGED')
 need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'INSTALLED_PACKAGE_DRIFT')
 out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceCommit':COMMIT,
  'packageSha256':PACKAGE_SHA,'fileManifestSha256':version['packageSha256'],'fileCount':len(version['files']),
  'engine':str(engine),'ownerConfigurationPin':ownerpin,'controlConfigurationPin':controlpin,
  'oldDataLimitsRejection':oldrejection,'dataLimits':newowner['dataLimits'],'maxExpandedBytes':newowner['maxExpandedBytes'],
  'actualControlConfigurationValidated':True,'serviceActive':True,'targetAndSourceUnchanged':True,
  'allBusinessIdsPidsStartTimesConfigurationUnchanged':True,'business':before,'restoreDispatched':False,
  'activeReservation':False,'operationCount':0,'claimCount':0}
 append(root/'configuration/readback-04f5f9ce-installation.json',out)
 print(json.dumps(out))
os.close(fd)
'''

if __name__=='__main__':
    observed=json.loads((PRIVATE/'resume-59.private.json').read_text(encoding='utf-8'))
    receipt=observed['documents']['targetInstallation']
    def canon(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    business={r['Id']:{'name':r['Name'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],
      'running':r['State']['Running'],'image':r['Image'],
      'configurationSha256':hashlib.sha256(canon(dict({k:r[k] for k in ('Path','Args','Config','HostConfig')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()}
      for r in observed['containers']}
    raw=PACKAGE.read_bytes()
    values={'COMMIT':COMMIT,'PACKAGE':base64.b64encode(raw).decode(),'PACKAGE_SHA':hashlib.sha256(raw).hexdigest(),
      'EXPECTED_RECEIPT_PIN':observed['files']['/mnt/intruoyi-data/spug-main-restore-20261104-v3/target-installation.json'],
      'EXPECTED_OWNER_PIN':receipt['ownerConfigurationPin'],'EXPECTED_CONTROL_PIN':receipt['controlConfigurationPin'],
      'EXPECTED_UNIT_SHA':observed['files']['/etc/systemd/system/'+receipt['service']]['sha256'],
      'EXPECTED_BUSINESS':business}
    out=remote('172.30.30.59','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,timeout=150)
    (TASK/'review-control-install.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='business'},ensure_ascii=False))
