"""Remote installer template, dispatched only by explicit --activate.

No module-level network operation. The parent task must review the prepared
candidate and complete its experience-preflight before dispatching this text.
"""

GATE = r'''
import json,pathlib,sys,time
import recovery_minimal_runtime as runtime
from recovery_control_smallapp_native import Native
from recovery_engine import pin,pinned_json,write
from recovery_main_health import endpoint,preflight,probe,ROLES
from recovery_replace import replacement_value
control_pin,owner_pin,target_ref,source_ref,root_text,policy=json.loads(sys.argv[1])
native=Native(control_pin);control=native.configuration();owner=pinned_json(owner_pin)
target=owner['targets'][target_ref];effective=replacement_value(owner,target_ref)
assert effective.get('backupEpoch')==policy,'TARGET_EPOCH_POLICY_NOT_BOUND'
assert 'sourceEpochPolicies' not in control,'TARGET_EPOCH_MISBOUND_TO_SOURCE57'
if policy is not None:
 from recovery_backup_epoch import read_current
 assert read_current(policy)['state']=='READY','TARGET_EPOCH_NOT_READY'
selection=native.selections(target_ref)
assert target_ref in next(row for row in selection['applications'] if row['sourceConfigRef']==source_ref)['freshTargetConfigRefs'],'CANDIDATE_TARGET_UNAVAILABLE'
root=pathlib.Path(root_text);root.mkdir(mode=0o700)
request=dict(operationId='installation-constructor-boundary',action='RESTORE',targetConfigRef=target_ref)
chain=[(owner_pin,None,dict(recoveryPoint='INSTALLATION_CONSTRUCTOR_BOUNDARY_NOT_RESTORE',
 objects=dict(method='PHYSICAL_FILES'),payloadPins=[],versionPins=[]),owner_pin)]
class BeforeDatabaseIO(Exception):pass
class Boundary(runtime.MinimalData):
 def database_uuid(self):
  assert self.frontend_readiness==owner.get('frontendReadiness',{}).get(target_ref),'FRONTEND_PROFILE_NOT_PROPAGATED'
  assert self.mutation_dispatched is False
  preflight(self)
  health={role:dict(url=endpoint(self,role),result=probe(endpoint(self,role),role,10)) for role in ROLES}
  assert all(item['result']['ready'] and item['result']['httpStatus']==200 for item in health.values()),'CANDIDATE_SEMANTIC_HEALTH_FAILED'
  records=[ref for ref in self.original_pins if pathlib.Path(ref['path']).name.startswith('native-')]
  assert len(records)>=3 and all(pinned_json(ref)['mutation'] is False and pinned_json(ref)['actualExitCode']==0 for ref in records),'CONSTRUCTOR_INVOCATIONS_NOT_READ_ONLY'
  write(root/'constructor-verification.json',dict(schemaVersion='TaskPackagedConstructorBoundary/v1',
   ownerConfigurationPin=owner_pin,targetConfigRef=target_ref,constructorModulePath=runtime.__file__,
   exactProfileFromActualOwner=True,healthEndpoints={role:item['url'] for role,item in health.items()},
   semanticHealth=health,nativeInvocationPins=records,noDatabaseIO=True,restoreDispatched=False))
  raise BeforeDatabaseIO()
subject=Boundary.__new__(Boundary)
try:subject.__init__(owner,request,None,{},chain,target,root,[])
except BeforeDatabaseIO:pass
else:raise AssertionError('ACTUAL_DATABASE_BOUNDARY_NOT_REACHED')
assert subject.archive_guard.fd==-1 and not subject.archive_guard.path_fds,'CONSTRUCTOR_GUARD_NOT_CLOSED'
assert callable(subject.modules['formal_schema_evidence'].restore_frozen_auto_increment)
assert callable(__import__('recovery_sql_stream').inspect_incremental_sql)
print(json.dumps(dict(status='PASS',selection=selection,constructorEvidencePin=pin(root/'constructor-verification.json'),
 actualSelectionVerifiedBeforeActivation=True,actualHealthContractVerified=True,actualPackagedConstructorVerified=True,
 constructorStopsBeforeDatabaseIO=True,backupEpochEnabled=policy is not None)))
'''

SOURCE_IDLE = r'''
import json,sys,time
from recovery_control_smallapp_native import Native
from recovery_control_smallapp import Ledger
control_pin,source_ref=json.loads(sys.argv[1]);native=Native(control_pin);control=native.configuration()
deadline=time.monotonic()+90
def guard():assert time.monotonic()<deadline,'INSTALL_LEDGER_BUDGET_EXCEEDED'
Ledger(control['ledgerRoot'],native).require_source_idle(source_ref,guard=guard)
print(json.dumps(dict(status='PASS',sourceConfigRef=source_ref,originalTerminalStatesVerified=True)))
'''

SCRIPT = r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile,time,urllib.request
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def pin(path):
 p=pathlib.Path(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):
 need(pin(ref['path'])==ref,'PIN_CHANGED');return json.loads(pathlib.Path(ref['path']).read_bytes())
def run(argv,*,timeout=60,env=None):
 result=subprocess.run(argv,capture_output=True,timeout=timeout,env=env)
 if result.returncode:
  # Retain exact diagnostics privately on the installation host; never print argv/env.
  error_path=root/'configuration'/('install-'+generation+'-command-error-'+hashlib.sha256(result.stdout+result.stderr).hexdigest()[:16]+'.log')
  if not error_path.exists():create(error_path,result.stdout+result.stderr)
  raise ValueError('INSTALL_COMMAND_FAILED_'+str(result.returncode))
 return result.stdout
def create(path,raw):
 need(path.is_absolute() and path.resolve()==path and path.parent.resolve()==path.parent,'INSTALL_PATH_ALIAS')
 with os.fdopen(os.open(path,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_WRONLY,0o600),'wb') as output:
  output.write(raw);output.flush();os.fsync(output.fileno())
 need(path.read_bytes()==raw,'INSTALL_READBACK_FAILED');return pin(path)
def fsync_dir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def samebytes(a,b):return all(a[key]==b[key] for key in ('bytes','sha256'))
def identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
root=pathlib.Path(CANDIDATE['previousCustody']['root']);generation='automatic-'+CANDIDATE['sourceCommit'][:7]
engine=pathlib.Path(CANDIDATE['engine']);target_ref=CANDIDATE['targetConfigRef'];unit=CANDIDATE['service']
need(CANDIDATE['status']=='PLAN_ONLY_NOT_DEPLOYED' and CANDIDATE['sourceCommit']==COMMIT,'EXPLICIT_CANDIDATE_REQUIRED')
need(CANDIDATE['host']=='172.30.30.'+SUFFIX and SUFFIX in ('58','59'),'EXPLICIT_TARGET_REQUIRED')
need(engine==root/('engine-'+generation) and root.resolve()==root,'ROOT_ALIAS')
need(type(RESUME_STAGED) is bool and (not RESUME_STAGED or SUFFIX=='58'),'RESUME_TARGET_INVALID')
need(type(RESUME_EPOCH_STAGE) is bool and (not RESUME_EPOCH_STAGE or SUFFIX=='59' and not RESUME_STAGED),'EPOCH_RESUME_TARGET_INVALID')
need(engine.exists()==(RESUME_STAGED or RESUME_EPOCH_STAGE),'GENERATION_EXISTS_OR_MISSING')
attempt=generation+('-epoch-resume-1' if RESUME_EPOCH_STAGE else '-resume-1' if RESUME_STAGED else '-initial')
audit_root=root/'configuration'/('installation-audit-'+attempt)
need(not audit_root.exists(),'ATTEMPT_ALREADY_RECORDED')
receiptpath=root/'target-installation.json';receipt=read(CANDIDATE['oldActiveReceiptPin'])
oldowner=read(CANDIDATE['oldOwnerPin']);oldcontrol=read(CANDIDATE['oldControlPin'])
need(receipt['ownerConfigurationPin']==CANDIDATE['oldOwnerPin'] and receipt['controlConfigurationPin']==CANDIDATE['oldControlPin'],'RECEIPT_CONFIGURATION_CHANGED')
target=oldowner['targets'][target_ref];oldengine=pathlib.Path(oldowner['formalModuleDirectory']).parent
need(receipt['engine']==str(oldengine) and receipt['service']==unit,'RECEIPT_OWNER_CHANGED')
oldpackage=read(pin(oldengine/'package.json'))
need(all(pin(oldengine/name)['sha256']==sha for name,sha in oldpackage['files'].items()),'OLD_ENGINE_CHANGED')
need(CANDIDATE['owner']['targets']==oldowner['targets'] and CANDIDATE['owner']['sources']==oldowner['sources'],'HISTORICAL_SOURCE_OR_TARGET_CHANGED')
need(CANDIDATE['control']['sourceConfigurations']==oldcontrol['sourceConfigurations'] and 'sourceEpochPolicies' not in CANDIDATE['control'],'SOURCE57_METADATA_CHANGED')
need(CANDIDATE['owner'].get('frontendReadiness')==oldowner.get('frontendReadiness'),'FRONTEND_PROFILE_CHANGED')
policy=CANDIDATE['targetBackupEpochPolicy']
need((SUFFIX=='58' and policy is None and 'targetBackupEpochPolicies' not in CANDIDATE['owner']) or
 (SUFFIX=='59' and policy is not None and CANDIDATE['owner']['targetBackupEpochPolicies']=={target_ref:policy}),'TARGET_EPOCH_SCOPE_INVALID')
if policy is not None:
 need(policy['databaseUuid']==target['replacement']['databaseUuid'] and policy['sourceLockPath']==target['replacement']['lockPath'],'TARGET_EPOCH_PHYSICAL_BINDING_CHANGED')
 for ref in EPOCH_CAPTURE_PINS:
  capture=read(ref);source=capture['source']
  need(source['sourceIdentity']==policy['sourceIdentity'] and source['databaseUuid']==policy['databaseUuid'] and capture['sourceLockPath']==policy['sourceLockPath'],'TARGET_EPOCH_SOURCE_IDENTITY_CHANGED')
  need(all(source[field]==target['replacement']['services'][role]['id'] for field,role in (('mysqlContainerId','mysql'),('minioContainerId','minio'))),'TARGET_EPOCH_SOURCE_CONTAINERS_CHANGED')
 need(len(EPOCH_CAPTURE_PINS)==2,'TARGET_EPOCH_SOURCE_PROOFS_REQUIRED')
sys.path[:0]=oldcontrol['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
lock=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def active_pid():
 value=run(['systemctl','show',unit,'-p','MainPID']).decode().strip()
 need(value.startswith('MainPID='),'CONTROL_PID_INVALID');return int(value.split('=',1)[1])
def workers(expected_pid):
 need(active_pid()==expected_pid and expected_pid>1,'CONTROL_PID_CHANGED')
 for process in pathlib.Path('/proc').iterdir():
  if not process.name.isdecimal():continue
  try:command=(process/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  if str(root).encode() in command:
   need(b'control_entry.py' in command and int(process.name)==expected_pid,'ACTIVE_TARGET_WORKER')
def reservation():need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_TARGET_RESERVATION')
def docker(args):return run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock',*args],timeout=90)
def snapshot():
 ids=docker(['ps','-aq','--no-trunc']).decode().split();need(ids,'EMPTY_DOCKER_INVENTORY')
 rows=json.loads(docker(['inspect',*ids]))
 return {r['Id']:dict(image=r['Image'],state={key:r['State'][key] for key in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},
  definitionSha256=hashlib.sha256(canonical(dict({key:r[key] for key in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
protected_paths=['/mnt/nas',*target['dataPaths'],*oldowner['sources'][SOURCE]['archiveRoots']]
def mounts():
 return sorted(' '.join(line.split()[1:]) for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines()
  if any(path==line.split()[4] or path.startswith(line.split()[4].rstrip('/')+'/') or line.split()[4].startswith(path.rstrip('/')+'/') for path in protected_paths))
history_roots={pathlib.Path(oldcontrol['ledgerRoot']),pathlib.Path(oldcontrol['registryRoot']),pathlib.Path(oldowner['operationsRoot']),pathlib.Path(target['replacement']['stateRoot'])}
def history_identity():
 values={}
 for scope in history_roots:
  need(scope.is_dir() and scope.resolve()==scope,'HISTORY_SCOPE_CHANGED')
  for path in [scope,*scope.rglob('*')]:
   info=path.lstat();need(not stat.S_ISLNK(info.st_mode),'HISTORY_LINK_REJECTED')
   values[str(path)]=identity(info)
 return values
def verify_retained():
 for ref in CANDIDATE['retainedHistoryPins']:
  path=pathlib.Path(ref['path']);before=path.lstat();digest=hashlib.sha256();size=0
  need(path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'HISTORICAL_PATH_CHANGED')
  with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
   need(identity(os.fstat(stream.fileno()))==identity(before),'HISTORICAL_FILE_CHANGED')
   while True:
    chunk=stream.read(1024*1024)
    if not chunk:break
    size+=len(chunk);digest.update(chunk)
   need(identity(os.fstat(stream.fileno()))==identity(before),'HISTORICAL_FILE_CHANGED')
  need(identity(path.lstat())==identity(before) and size==ref['bytes'] and digest.hexdigest()==ref['sha256'],'HISTORICAL_FILE_CHANGED')
def preserved():
 need(snapshot()==before and pin('/etc/fstab')==fstab and mounts()==beforemounts,'ORIGINAL_BUSINESS_OR_MOUNTS_CHANGED')
 need(pin(CANDIDATE['oldOwnerPin']['path'])==CANDIDATE['oldOwnerPin'] and pin(CANDIDATE['oldControlPin']['path'])==CANDIDATE['oldControlPin'],'OLD_CONFIGURATION_CHANGED')
 need(all(pin(oldengine/name)['sha256']==sha for name,sha in oldpackage['files'].items()),'OLD_INSTALLED_ENGINE_CHANGED')
 need(history_identity()==history,'HISTORICAL_TREE_CHANGED');verify_retained();reservation()
def http_selection(control,ready_process=None):
 headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 url='http://127.0.0.1:'+str(control['listenPort'])+'/selections?targetConfigRef='+target_ref
 def validate(value):need(target_ref in next(row for row in value['applications'] if row['sourceConfigRef']==SOURCE)['freshTargetConfigRefs'],'TARGET_NOT_AVAILABLE')
 request=urllib.request.Request(url,headers=headers)
 if ready_process is not None:return wait_http_json(opener,request,ready_process,validate,timeout=15)
 with opener.open(request,timeout=90) as response:
  need(response.status==200,'TARGET_SELECTION_HTTP_FAILED');value=json.load(response)
 validate(value)
 return value
oldpid=CANDIDATE['oldControlPid'];workers(oldpid);reservation()
custody_before=verify_installation_receipt_custody(CANDIDATE['previousCustody'])
before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts();verify_retained()
http_selection(oldcontrol)
old_health_code="""import json,subprocess,sys
from types import SimpleNamespace
from recovery_control_smallapp_native import Native
from recovery_main_health import preflight,endpoint,probe,ROLES
control_pin,owner_pin,reference=json.loads(sys.argv[1]);n=Native(control_pin);o=n.document(owner_pin);t=o['targets'][reference]
def inspect(identity):
 p=subprocess.run([t['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',identity],capture_output=True,timeout=10)
 assert p.returncode==0 and not p.stderr
 rows=json.loads(p.stdout);assert len(rows)==1 and rows[0]['Id']==identity;return rows[0]
view=SimpleNamespace(config=t,config_services={row['role']:row for row in t['services']},inspect=inspect,
frontend_readiness=o.get('frontendReadiness',{}).get(reference))
preflight(view);results={role:dict(url=endpoint(view,role),result=probe(endpoint(view,role),role,10)) for role in ROLES}
assert all(value['result']['ready'] and value['result']['httpStatus']==200 for value in results.values())
print(json.dumps(results))
"""
before_health=json.loads(run([oldcontrol['pythonPin']['path'],'-B','-c',old_health_code,
 canonical([CANDIDATE['oldControlPin'],CANDIDATE['oldOwnerPin'],target_ref]).decode()],env=dict(os.environ,**oldcontrol['environment']),timeout=60))
raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==CANDIDATE['packageSha256'],'PACKAGE_CHANGED')
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 version=json.load(archive.extractfile('package.json'));names=archive.getnames()
 need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'STANDARD_PACKAGE_REQUIRED')
 need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'} and len(version['files'])==130,'PACKAGE_MEMBERS_INVALID')
 need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256']==CANDIDATE['fileManifestSha256'],'PACKAGE_MANIFEST_CHANGED')
 for member in archive.getmembers():
  need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
  data=archive.extractfile(member).read()
  if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][member.name],'PACKAGE_FILE_CHANGED');compile(data,member.name,'exec')
 if RESUME_STAGED or RESUME_EPOCH_STAGE:
  need(engine.resolve()==engine and {str(p.relative_to(engine)) for p in engine.rglob('*') if p.is_file()}==set(names),'RESUME_STAGE_FILE_SET_CHANGED')
  for member in archive.getmembers():
   path=engine/member.name;need(path.resolve()==path and path.read_bytes()==archive.extractfile(member).read(),'RESUME_STAGE_BYTES_CHANGED')
 if RESUME_STAGED:
  need(RESUME_PROOF and RESUME_PROOF['host']==CANDIDATE['host'] and RESUME_PROOF['pid']==oldpid
   and RESUME_PROOF['controlPin']==CANDIDATE['oldControlPin'] and RESUME_PROOF['ownerPin']==CANDIDATE['oldOwnerPin']
   and RESUME_PROOF['originalAttemptTreeSnapshotUnavailable'] is True,'RESUME_STAGE_PROOF_REQUIRED')
  evidence=read(RESUME_PROOF['constructorEvidencePin'])
  need(evidence['ownerConfigurationPin']==CANDIDATE['ownerConfigurationPin'] and evidence['targetConfigRef']==target_ref
   and evidence['noDatabaseIO'] is True and evidence['restoreDispatched'] is False,'RESUME_CONSTRUCTOR_PROOF_CHANGED')
  for ref in evidence['nativeInvocationPins']:
   invocation=read(ref);need(invocation['mutation'] is False and invocation['actualExitCode']==0,'RESUME_CONSTRUCTOR_NOT_READ_ONLY')
  for query in RESUME_PROOF['queriesSince1800Utc']:read(query['pin'])
  need(not pathlib.Path(CANDIDATE['previousReceiptPin']['path']).exists()
   and not (root/'configuration'/(generation+'-previous-unit.txt')).exists()
   and not (root/'configuration'/('installation-'+generation+'.json')).exists(),'RESUME_ACTIVATION_ALREADY_STARTED')
  for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system','/lib/systemd/system'):
   need(not list((pathlib.Path(base)/(unit+'.d')).glob('*'+generation+'*.conf')),'RESUME_DROPIN_ALREADY_EXISTS')
 elif RESUME_EPOCH_STAGE:
  epoch_resume_verification=verify_empty_epoch_stage_resume(EPOCH_RESUME_PROOF,CANDIDATE,
   epoch_stage_observation(CANDIDATE,before,fstab,beforemounts,oldpid))
 else:
  engine.mkdir(mode=0o700)
  for member in archive.getmembers():
   path=engine/member.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(path,archive.extractfile(member).read())
epoch_initialization=None;epoch_initialization_pin=None
if policy is not None:
 epoch_initialization_path=root/'configuration'/('epoch-initialization-'+attempt+'.json')
 need(not epoch_initialization_path.exists(),'EPOCH_INITIALIZATION_RECEIPT_EXISTS')
 epoch_root=pathlib.Path(policy['root']);need(epoch_root.exists()==RESUME_EPOCH_STAGE,'EPOCH_ALREADY_REGISTERED_OR_STAGE_MISSING')
 need(epoch_root.parent.parent==pathlib.Path('/mnt/intruoyi-data'),'EPOCH_DISK_SCOPE_INVALID')
 if not RESUME_EPOCH_STAGE:
  epoch_root.parent.mkdir(mode=0o700,exist_ok=True);epoch_root.mkdir(mode=0o700)
 # New package validates physical overlap before initialization or activation.
 epoch_code="import json,sys;import recovery_replace,recovery_backup_epoch;from recovery_engine import pin;v=json.loads(sys.argv[1]);recovery_replace.replacement_value(v[0],v[1]);print(json.dumps(dict(replacementModulePin=pin(recovery_replace.__file__),epochModulePin=pin(recovery_backup_epoch.__file__))))"
 validation=json.loads(run([CANDIDATE['control']['pythonPin']['path'],'-B','-c',epoch_code,canonical([CANDIDATE['owner'],target_ref]).decode()],
  env=CANDIDATE['control']['environment'],timeout=60))
 for key,basename in (('replacementModulePin','recovery_replace.py'),('epochModulePin','recovery_backup_epoch.py')):
  module_names=[name for name in version['files'] if pathlib.PurePosixPath(name).name==basename]
  need(len(module_names)==1 and validation[key]==pin(engine/module_names[0])
   and validation[key]['sha256']==version['files'][module_names[0]],'EPOCH_VALIDATION_MODULE_CHANGED')
 if RESUME_EPOCH_STAGE:
  verify_empty_epoch_stage_resume(EPOCH_RESUME_PROOF,CANDIDATE,epoch_stage_observation(CANDIDATE,snapshot(),pin('/etc/fstab'),mounts(),active_pid()))
 # The writer must run in this PID, which owns the still-held source flock.
 # Loading verified source bypasses old-package module caches without unlocking.
 epoch_initialization=initialize_epoch_in_lock_owner(validation['epochModulePin'],policy,lock)
 epoch=epoch_initialization['epoch'];need(epoch['state']=='READY','EPOCH_INITIALIZATION_NOT_READY')
 epoch_initialization_pin=create(epoch_initialization_path,canonical(epoch_initialization))
else:epoch=None
if RESUME_STAGED:
 need(policy is None,'RESUME_EPOCH_INITIALIZATION_FORBIDDEN')
 ownerpin=pin(CANDIDATE['ownerConfigurationPin']['path']);controlpin=pin(CANDIDATE['controlConfigurationPin']['path'])
else:
 ownerpin=create(pathlib.Path(CANDIDATE['ownerConfigurationPin']['path']),canonical(CANDIDATE['owner']))
 controlpin=create(pathlib.Path(CANDIDATE['controlConfigurationPin']['path']),canonical(CANDIDATE['control']))
need(ownerpin==CANDIDATE['ownerConfigurationPin'] and controlpin==CANDIDATE['controlConfigurationPin'],'CANDIDATE_BYTES_CHANGED')
newcontrol=CANDIDATE['control'];newenv=dict(newcontrol['environment'])
for role in ('repository','recovery','control'):
 checked=json.loads(run([newcontrol['pythonPin']['path'],'-B',str(engine/(role+'_entry.py')),'--check-imports'],env=newenv))
 need(checked['role']==role,'NEW_ENTRY_IMPORT_FAILED')
module_names=[name for name in version['files'] if pathlib.PurePosixPath(name).name=='recovery_control_smallapp_native.py']
need(len(module_names)==1,'CONTROL_MODULE_AMBIGUOUS')
worker_environment=observe_worker_environment(newcontrol['pythonPin']['path'],newcontrol['environment'],pin(engine/module_names[0]))
def gate(name):
 args=[controlpin,ownerpin,target_ref,SOURCE,str(root/'configuration'/(name+'-'+attempt)),policy]
 return json.loads(run([newcontrol['pythonPin']['path'],'-B','-c',GATE,canonical(args).decode()],env=newenv,timeout=180))

# This is the only ledger reconciliation. It may append native query receipts
# and acquire the host resource lock internally, so it precedes our host lock.
audit_root.mkdir(mode=0o700)
attempt_before_pin=create(audit_root/'business-before.json',canonical(dict(containers=before,fstabPin=fstab,mounts=beforemounts,
 oldControlPid=oldpid,oldOwnerPin=CANDIDATE['oldOwnerPin'],oldControlPin=CANDIDATE['oldControlPin'],oldActiveReceiptPin=CANDIDATE['oldActiveReceiptPin'])))
if RESUME_STAGED:create(audit_root/'failed-attempt-observation.json',canonical(RESUME_PROOF))
if RESUME_EPOCH_STAGE:create(audit_root/'failed-epoch-stage-observation.json',canonical(EPOCH_RESUME_PROOF))
admission_before=history_snapshot(history_roots)
admission_before_pin=create(audit_root/'history-before-source-idle.json',canonical(admission_before))
source_idle=json.loads(run([newcontrol['pythonPin']['path'],'-B','-c',SOURCE_IDLE,canonical([controlpin,SOURCE]).decode()],env=newenv,timeout=120))
need(source_idle.get('status')=='PASS' and source_idle.get('sourceConfigRef')==SOURCE,'SOURCE_IDLE_NOT_VERIFIED')
admission_after=history_snapshot(history_roots,baseline=admission_before)
admission_after_pin=create(audit_root/'history-after-source-idle.json',canonical(admission_after))
query_audit=verify_query_append(admission_before,admission_after,pathlib.Path(oldcontrol['ledgerRoot']),SOURCE)
query_audit_pin=create(audit_root/'source-idle-query-audit.json',canonical(dict(query_audit,beforePin=admission_before_pin,afterPin=admission_after_pin,sourceIdle=source_idle)))
verify_retained();workers(oldpid);reservation()
with _host_lock():
 workers(oldpid);reservation()
 history=history_identity()
 verify_saved_snapshot(admission_after,history_roots)
 history_evidence=admission_after
 strict_history_pin=create(audit_root/'strict-history-before-activation.json',canonical(history_evidence))
 preserved()
 candidate_gate=gate('constructor-preactivation')
 preserved();workers(oldpid)
 previous=create(pathlib.Path(CANDIDATE['previousReceiptPin']['path']),receiptpath.read_bytes())
 need(previous==CANDIDATE['previousReceiptPin'],'PREVIOUS_RECEIPT_ARCHIVE_CHANGED')
 create(root/'configuration'/(generation+'-previous-unit.txt'),run(['systemctl','cat',unit]))
 # The service's merged ExecStart must be this exact generation. Choose a name
 # that sorts after every existing unit drop-in, then verify the live argv too.
 names=[]
 for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system','/lib/systemd/system'):
  folder=pathlib.Path(base)/(unit+'.d')
  if folder.exists():names.extend(path.name for path in folder.glob('*.conf'))
 prefix='zzzzzz'
 while any(prefix+'-'+generation+'.conf'<=name for name in names):
  prefix+='z';need(len(prefix)<160,'DROPIN_SORT_SCOPE_INVALID')
 dropin=pathlib.Path('/etc/systemd/system')/(unit+'.d')/(prefix+'-'+generation+'.conf')
 dropin.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
 argv=[newcontrol['pythonPin']['path'],'-B',str(engine/'control_entry.py'),'serve','--config-pin',canonical(controlpin).decode()]
 need(all('\n' not in part and '\x00' not in part and '%' not in part for part in argv),'SYSTEMD_ARGV_INVALID')
 # Single-quoted JSON remains one systemd argument; embedded quotes are disallowed.
 need("'" not in argv[-1] and all(' ' not in part and "'" not in part for part in argv[:-1]),'SYSTEMD_ARGV_UNSUPPORTED')
 text='[Service]\nEnvironment=PYTHONPATH='+newcontrol['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+' '.join(argv[:-1])+" '"+argv[-1]+"'\n"
 dropinpin=create(dropin,text.encode());dropin.chmod(0o644)
 preserved();workers(oldpid)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',unit]);need(run(['systemctl','is-active',unit]).strip()==b'active','CONTROL_NOT_ACTIVE')
 newpid=active_pid();need(newpid!=oldpid,'CONTROL_NOT_RELOADED');workers(newpid)
 actual=(pathlib.Path('/proc')/str(newpid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
 need(actual==argv,'WRONG_ACTIVE_GENERATION')
 process_environment=dict(part.split('=',1) for part in (pathlib.Path('/proc')/str(newpid)/'environ').read_bytes().decode().split('\0') if '=' in part)
 runtime_environment=verify_control_runtime(process_environment,newcontrol['environment'],actual,argv)
 limits=next(line for line in pathlib.Path('/proc',str(newpid),'limits').read_text().splitlines() if line.startswith('Max open files'))
 need(limits.split()[3:5]==['65536','65536'],'LIVE_FD_LIMIT_CHANGED')
 def ready_process():
  need(active_pid()==newpid and (pathlib.Path('/proc')/str(newpid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')==argv,'CONTROL_IDENTITY_CHANGED_DURING_READINESS')
 selection=http_selection(newcontrol,ready_process);actual_gate=gate('constructor-postactivation')
 preserved();need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'NEW_INSTALLED_ENGINE_CHANGED')
 need(pin(receiptpath)==CANDIDATE['oldActiveReceiptPin'],'ACTIVE_RECEIPT_CHANGED_BEFORE_PUBLISH')
 updated=dict(receipt,sourceCommit=COMMIT,engine=str(engine),ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 need(updated==CANDIDATE['proposedReceipt'],'RECEIPT_CONTRACT_CHANGED')
 temporary=receiptpath.with_name('target-installation.'+generation+'.tmp');create(temporary,canonical(updated));os.replace(temporary,receiptpath);fsync_dir(root)
 current=pin(receiptpath);need(current==CANDIDATE['proposedCurrentReceiptPin'],'PUBLISHED_RECEIPT_CHANGED')
 step=dict(sourceCommit=COMMIT,engine=str(engine),previousReceiptPin=previous,currentReceiptPin=current,
  ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin,dropinPin=pin(dropin))
 custody=copy.deepcopy(CANDIDATE['previousCustody']);custody['steps'].append(step);custody['expectedGenerationCommits'].append(COMMIT)
 custody['selectedOwnerPin']=ownerpin;custody['selectedControlPin']=controlpin
 custody_after=verify_installation_receipt_custody(custody);preserved()
 out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=CANDIDATE['host'],
  targetConfigRef=target_ref,service=unit,**step,fileCount=130,packageSha256=CANDIDATE['packageSha256'],fileManifestSha256=CANDIDATE['fileManifestSha256'],
  oldControlPid=oldpid,controlPid=newpid,liveMaxOpenFiles=65536,epoch=epoch,epochPolicy=policy,epochStatus=CANDIDATE['epochStatus'],
  source57MetadataUnchanged=True,targetAndSourceConfigurationUnchanged=True,previousGenerationsRetained=True,
  allBusinessDefinitionsAndRuntimeUnchanged=True,originalContainerCount=len(before),fstabAndProtectedMountsUnchanged=True,
  originalHistoryIdentitiesPreserved=len(history),failedOriginalFilesPreserved=len(CANDIDATE['retainedHistoryPins']),
  resumedStagedGeneration=RESUME_STAGED,resumedEmptyEpochStage=RESUME_EPOCH_STAGE,epochInitializationPin=epoch_initialization_pin,
  sourceIdlePerformedBeforeHostLock=True,sourceIdleQueryAuditPin=query_audit_pin,
  strictHistorySnapshotPin=strict_history_pin,originalBusinessSnapshotPin=attempt_before_pin,
  controlRuntimeEnvironment=runtime_environment,workerEnvironmentObservation=worker_environment,
  actualSelectionVerifiedBeforeActivation=True,actualSelectionVerifiedAfterActivation=True,actualHealthContractVerified=True,
  actualPackagedConstructorVerified=True,constructorStopsBeforeDatabaseIO=True,constructorEvidencePin=actual_gate['constructorEvidencePin'],
  candidateConstructorEvidencePin=candidate_gate['constructorEvidencePin'],currentTargetSelection=selection,beforeSemanticHealth=before_health,
  installationReceiptCustodyBefore=custody_before,installationReceiptCustody=custody_after,extendedCustody=custody,
  noMutationReservationAbsent=True,restoreDispatched=False,backupDispatched=False)
 create(root/'configuration'/('installation-'+generation+'.json'),canonical(out));print(json.dumps(out))
os.close(lock)
'''
