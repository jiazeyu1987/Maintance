"""Install a new immutable SAFE generation, retaining original failed evidence."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from repair_preflight import remote,TASK,PRIVATE

SCRIPT=r'''
import base64,copy,datetime,hashlib,io,json,os,pathlib,subprocess,sys,tarfile
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
engine=root/('engine-'+GENERATION)
operation=OPERATION
oproot=root/'recovery-operations'/operation;claim=root/'replacement-state'/operation
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):
 path=pathlib.Path(p['path']);assert pin(path)==p;return json.loads(path.read_bytes())
def append(p,d):
 with p.open('xb') as f:
  os.chmod(p,0o600);f.write(canonical(d));f.flush();os.fsync(f.fileno())
 return pin(p)
def run(args,**kwargs):
 p=subprocess.run(args,capture_output=True,timeout=60,**kwargs)
 assert p.returncode==0,'OWN_COMPONENT_COMMAND_FAILED'
 return p.stdout
def original_pins():
 paths=[oproot/n for n in ('configuration.json','request.json','worker-result.json','child-exit.json','resource-reservation.json')]
 paths += [claim/'replacement-result.json']
 return [pin(p) for p in paths]
original=original_pins()
assert read(original[2])['state']=='FAILED_RETAINED' and read(original[2])['actualExitCode']==1
assert read(original[3])['actualExitCode']==1 and read(original[3])['timedOut'] is False
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bb31c4d0-bbfb-4b97-8c06-4ff11e779015'
if PHASE=='install':
 assert not engine.exists() and not (claim/'recovery-clearance.json').exists()
 active=pin(pathlib.Path('/var/lib/spug-restore-resources/active.json'))
 raw=base64.b64decode(PACKAGE)
 assert hashlib.sha256(raw).hexdigest()==PACKAGE_SHA
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  version=json.load(archive.extractfile('package.json'))
  assert version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification']
  assert set(archive.getnames())==set(version['files'])|{'package.json'}
  assert hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256']
  for name in archive.getnames():
   item=archive.getmember(name)
   assert item.isfile() and not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
   data=archive.extractfile(item).read()
   if name!='package.json':
    assert hashlib.sha256(data).hexdigest()==version['files'][name]
    compile(data,name,'exec')
  engine.mkdir(mode=0o700)
  for item in archive.getmembers():
   path=engine/item.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   with path.open('xb') as f:os.chmod(path,0o600);f.write(archive.extractfile(item).read())
 oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
 oldversion=json.loads((oldengine/'package.json').read_bytes())
 for name,checksum in oldversion['files'].items():assert pin(oldengine/name)['sha256']==checksum
 newowner=copy.deepcopy(owner)
 assert newowner['formalModuleDirectory']==str(oldengine/'formal')
 newowner['formalModuleDirectory']=str(engine/'formal')
 newowner['dataLimits']['max_bytes']=16*1024**3
 sys.path.insert(0,str(engine/'formal'))
 import formal_data_evidence
 assert pathlib.Path(formal_data_evidence.__file__).parent==engine/'formal'
 assert formal_data_evidence.validate_limits(newowner['dataLimits'])==newowner['dataLimits']
 assert newowner['maxExpandedBytes']==owner['maxExpandedBytes']
 assert newowner['targets']==owner['targets'] and newowner['sources']==owner['sources']
 ownerpin=append(root/('configuration/main-recovery-'+GENERATION+'.json'),newowner)
 newcontrol=copy.deepcopy(control)
 oldengine=str(oldengine);newengine=str(engine)
 newcontrol['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(oldengine+'/',newengine+'/')
 assert newcontrol['environment']['PYTHONPATH']!=control['environment']['PYTHONPATH']
 for role in newcontrol['programPins']:newcontrol['programPins'][role]=pin(engine/(role+'_entry.py'))
 source='intruoyi-57-safe-20261024-v1';target=receipt['targetConfigRef']
 assert newcontrol['restoreConfigurations'][source][target]==receipt['ownerConfigurationPin']
 newcontrol['restoreConfigurations'][source][target]=ownerpin
 controlpin=append(root/('configuration/control-43658-'+GENERATION+'.json'),newcontrol)
 sys.path[:0]=newcontrol['environment']['PYTHONPATH'].split(':')
 from recovery_control_smallapp_native import Native
 from recovery_retained_retry import observe
 assert Native(controlpin).configuration()==newcontrol
 observe(owner,json.loads((oproot/'request.json').read_bytes()),oproot,EXPECTED_TABLES)
 unit=pathlib.Path('/etc/systemd/system')/receipt['service'];before=unit.read_bytes()
 assert before.count(canonical(receipt['controlConfigurationPin']))==1
 assert before.count((oldengine+'/control_entry.py').encode())==1
 append(root/('configuration/'+GENERATION+'-installation-before.json'),receipt)
 backup=root/('configuration/'+GENERATION+'-unit-before.service')
 with backup.open('xb') as f:os.chmod(backup,0o600);f.write(before)
 updated=before.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)).replace((oldengine+'/').encode(),(newengine+'/').encode())
 unit.write_bytes(updated)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 assert run(['systemctl','is-active',receipt['service']]).strip()==b'active'
 receipt.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 temp=receiptpath.with_name('target-installation.retained.tmp');assert not temp.exists()
 with temp.open('xb') as f:os.chmod(temp,0o600);f.write(canonical(receipt));f.flush();os.fsync(f.fileno())
 temp.replace(receiptpath)
 assert original_pins()==original and pin(pathlib.Path(active['path']))==active
 out={'sourceCommit':COMMIT,'packageSha256':PACKAGE_SHA,'fileManifestSha256':version['packageSha256'],
  'engine':str(engine),'controlConfigurationPin':controlpin,'ownerConfigurationPin':ownerpin,
  'originalFailurePins':original,'originalFailedEvidenceUnchanged':True,'reservationUnchanged':True,
  'targetConfigurationUnchanged':True,'dataLimitsValidated':True,'dataLimits':newowner['dataLimits'],
  'maxExpandedBytes':newowner['maxExpandedBytes'],'businessServicesStarted':False,'restoreDispatched':False}
 append(root/('configuration/'+GENERATION+'-installation.json'),out)
elif PHASE=='authorize':
 version=json.loads((engine/'package.json').read_bytes())
 for name,checksum in version['files'].items():assert pin(engine/name)['sha256']==checksum
 assert owner['targets']==json.loads((oproot/'configuration.json').read_bytes())['targets']
 environment=dict(os.environ,**control['environment'])
 result=run([control['pythonPin']['path'],'-B',str(engine/'common/recovery_retained_retry.py'),
  '--operation-root',str(oproot),'--authorization',AUTHORIZATION,'--expected-table-count',str(EXPECTED_TABLES),
  '--authorize-retained-replacement'],env=environment)
 out=json.loads(result)
 assert original_pins()==original and out['originalState']=='FAILED_RETAINED' and out['restoreDispatched'] is False
 out.update(originalFailedEvidenceUnchanged=True,originalFailurePins=original)
else:raise AssertionError('PHASE_INVALID')
out['observedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(out))
'''

if __name__=='__main__':
 import subprocess,re
 parser=argparse.ArgumentParser()
 parser.add_argument('phase',choices=['install','authorize'])
 parser.add_argument('--commit',required=True)
 parser.add_argument('--package',type=Path,required=True)
 args=parser.parse_args()
 assert re.fullmatch('[0-9a-f]{40}',args.commit)
 assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==args.commit
 package=args.package.resolve();assert package.is_relative_to(PRIVATE.resolve())
 raw=package.read_bytes()
 plan=hashlib.sha256((TASK/'readback-limits-repair-plan.md').read_bytes()).hexdigest()
 authorization=('User authorized control component installation and new production FULL restore to exact test MAIN; '
                'continue same point smallapp-73cd541a95d84d6a86f9d693e4053c75 after terminated failure; plan SHA256 '+plan)
 values={'COMMIT':args.commit,'PHASE':args.phase,'PACKAGE':base64.b64encode(raw).decode(),
         'PACKAGE_SHA':hashlib.sha256(raw).hexdigest(),'AUTHORIZATION':authorization,
         'GENERATION':'readback-'+args.commit[:8],
         'OPERATION':'smallapp-91cc5c0b4b054cb38075681f1aca7d4a','EXPECTED_TABLES':885}
 script='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT
 value=remote('172.30.30.58',script,150)
 (TASK/('readback-limits-'+args.phase+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(value))
