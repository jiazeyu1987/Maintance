"""Stop only storage proven to have been started by the terminated failed restore."""
import hashlib
import json
from install_prod_control import TASK,ROOT,TARGET,UNIT,LOCK,PRIVATE,remote

GUARDS=r'''
def validate_started_storage(operation,row,invocations,finished):
 from datetime import datetime,timezone
 def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
 expected=digest([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','start',row['Id']])
 matches=[(reference,item) for reference,item in invocations if item.get('schemaVersion')=='RecoveryDataInvocation/v1' and
  item.get('operationId')==operation and item.get('argvSha256')==expected and item.get('mutation') is True and
  item.get('state')=='SUCCEEDED' and item.get('actualExitCode')==0]
 need(len(matches)==1,'FAILED_STORAGE_START_NOT_PROVEN')
 reference,item=matches[0]
 started=stamp(row['State']['StartedAt'])
 need(stamp(item['startedAt'])<=started<=stamp(item['finishedAt'])<=stamp(finished),'FAILED_STORAGE_START_TIME_CHANGED')
 need(row['State']['Running'] and row['State']['Pid']>0 and not row['State']['Paused'] and not row['State']['Restarting'],
  'FAILED_STORAGE_NOT_STABLE')
 return reference
'''

SCRIPT=r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path(ROOT)
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def original_pins():
 for ref in PINS:need(pin(ref['path'])==ref,'ORIGINAL_FAILURE_CHANGED')
 need(pin('/var/lib/spug-restore-resources/active.json')==ACTIVE_POINTER,'RETAINED_POINTER_CHANGED')
original_pins()
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['sourceCommit']==COMMIT and receipt['targetConfigRef']==TARGET,'CONTROL_GENERATION_CHANGED')
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_engine import pin as strict_pin
from recovery_retained_retry import ReadOnlyTarget,append,observe
from recovery_resource_admission import _host_lock,_verify_reservation
from recovery_main_target import verify_runtime,archive_view,published_fence,mysql_scheduler
from recovery_replace import verify_services
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
target=configuration['targets'][TARGET];claim=pathlib.Path(target['replacement']['stateRoot'])/OPERATION
need(target==json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())['targets'][TARGET], 'RETAINED_TARGET_CHANGED')
result=json.loads((operation/'worker-result.json').read_bytes());exited=json.loads((operation/'child-exit.json').read_bytes())
need(result['state']=='FAILED_RETAINED' and result['failureCode']=='ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED' and result['actualExitCode']==1 and
 result['data']['mutationDispatched'] is True and exited['actualExitCode']==1 and exited['timedOut'] is False,'ORIGINAL_FAILURE_CHANGED')
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:command=(proc/'cmdline').read_bytes()
 except OSError:continue
 need(not (OPERATION.encode() in command and any(name in command for name in
  (b'recovery_minimal_worker.py',b'recovery_entry.py',b'recovery_control_smallapp.py\x00worker'))),'ORIGINAL_WORKER_RUNNING')
native=ReadOnlyTarget(configuration,request,operation);native.original=request
native.command=lambda args,**kwargs: subprocess.check_output(args,timeout=20) if not kwargs.get('mutation') else need(False,'READ_ONLY_COMMAND_REQUIRED')
def scheduler_query(statement,*,mutation=False):
 need(not mutation,'READ_ONLY_COMMAND_REQUIRED');return (native.query(statement)+'\n').encode()
fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 original_pins();_verify_reservation(configuration,request,operation)
 verify_services(native,target['replacement']);verify_runtime(native,states=False)
 rows={role:native.inspect(service['id']) for role,service in native.config_services.items()}
 need(all(row['State']['Running'] is (role in ('mysql','redis','minio')) for role,row in rows.items()),'BUSINESS_WRITER_NOT_QUIESCED')
 archive_view(native).verify();published_fence(native).verify();mysql_scheduler(native,query=scheduler_query).verify()
 invocations=[]
 for reference in PINS:
  if reference['path'].endswith('.json'):
   value=json.loads(pathlib.Path(reference['path']).read_bytes())
   if isinstance(value,dict):invocations.append((reference,value))
 startpin=validate_started_storage(OPERATION,rows['minio'],invocations,result['finishedAt'])
 def business():
  ids=subprocess.check_output(['docker','ps','-aq','--no-trunc'],timeout=15).decode().split()
  values=json.loads(subprocess.check_output(['docker','inspect',*ids],timeout=20))
  return {r['Id']:dict(image=r['Image'],configDigest=digest(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination']))),
    state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')}) for r in values}
 before=business();need(len(before)==195,'BUSINESS_SET_CHANGED')
 journal=claim/'health-recovery';journal.mkdir(mode=0o700)
 arguments=[target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','stop','--time','20',rows['minio']['Id']]
 intent=append(journal/'stop-intent.json',dict(schemaVersion='RetainedMainStorageQuiescenceIntent/v1',operationId=OPERATION,
  authorization='Existing user authorization: successful Spug restore to original PROD MAIN57, fixing restoration defects.',
  arguments=arguments,originalStartPin=startpin,originalFailureResultPin=strict_pin(operation/'worker-result.json'),
  activePointerPin=ACTIVE_POINTER,originalMinioState=rows['minio']['State'],startedAt=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 process=subprocess.Popen(arguments,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:out,err=process.communicate(timeout=35)
 except subprocess.TimeoutExpired:
  append(journal/'stop-unknown.json',dict(intentPin=intent,pid=process.pid,state='TERMINAL_UNKNOWN'))
  raise ValueError('STORAGE_STOP_TERMINAL_UNKNOWN')
 stop=append(journal/'stop-exit.json',dict(intentPin=intent,actualExitCode=process.returncode,
  stdoutSha256=hashlib.sha256(out).hexdigest(),stderrSha256=hashlib.sha256(err).hexdigest(),
  finishedAt=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 need(process.returncode==0 and not err and out.strip().decode()==rows['minio']['Id'],'STORAGE_STOP_FAILED')
 observation=observe(configuration,request,operation,885)
 after=business();identity=rows['minio']['Id']
 need(set(after)==set(before) and all(after[k]==v for k,v in before.items() if k!=identity),'OTHER_RUNTIME_CHANGED')
 need(after[identity]['image']==before[identity]['image'] and after[identity]['configDigest']==before[identity]['configDigest'] and
  not after[identity]['state']['Running'] and after[identity]['state']['Pid']==0 and
  after[identity]['state']['StartedAt']==before[identity]['state']['StartedAt'],'STORAGE_IDENTITY_CHANGED')
 archive_view(native).verify();published_fence(native).verify();mysql_scheduler(native,query=scheduler_query).verify();original_pins()
 report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,
  intentPin=intent,stopExitPin=stop,originalStartPin=startpin,originalFailurePinsUnchanged=len(PINS),
  originalMinioStopped=True,other194RuntimeUnchanged=True,protectionAndReservationRetained=True,
  schedulerRemainsPaused=True,databaseTableCount=observation['tableCount'],restoreDispatched=False)
 append(journal/'quiescence.json',report);print(json.dumps(report))
os.close(fd)
'''

if __name__=='__main__':
    assert not (TASK/'health-storage-quiescence.json').exists(),'QUIESCENCE_ALREADY_RECORDED'
    failure=json.loads((TASK/'healthcheck-failure-diagnosis.json').read_text(encoding='utf-8'))
    old=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    assert failure['status']=='PASS' and len(failure['evidencePins'])==703 and old['actualExitCode']==1 and len(old['evidencePins'])==205
    values=dict(ROOT=ROOT,TARGET=TARGET,UNIT=UNIT,LOCK=LOCK,COMMIT=failure['sourceCommit'],
        OPERATION=failure['operationId'],PINS=failure['evidencePins']+old['evidencePins'],ACTIVE_POINTER=failure['activePointerPin'])
    script='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+GUARDS+'\n'+SCRIPT
    report=remote(script,180)
    (TASK/'health-storage-quiescence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
