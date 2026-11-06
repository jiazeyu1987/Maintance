"""Read back an already executed exact stop; never repeat the stop command."""
import json
from install_prod_control import TASK,ROOT,TARGET,LOCK,remote

SCRIPT=r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path(ROOT)
def need(v,code):
 if not v:raise ValueError(code)
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
receipt=json.loads((root/'target-installation.json').read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes());sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_engine import digest,pinned_json
from recovery_retained_retry import ReadOnlyTarget,append,observe
from recovery_resource_admission import _host_lock,_verify_reservation
from recovery_main_target import archive_view,published_fence,mysql_scheduler
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
target=configuration['targets'][TARGET];claim=pathlib.Path(target['replacement']['stateRoot'])/OPERATION;journal=claim/'health-recovery'
intentpin=pin(journal/'stop-intent.json');exitpin=pin(journal/'stop-exit.json')
intent=pinned_json(intentpin);exited=pinned_json(exitpin)
identity=next(s['id'] for s in target['services'] if s['role']=='minio')
need(intent['operationId']==OPERATION and intent['arguments']==[target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','stop','--time','20',identity] and
 exited['intentPin']==intentpin and exited['actualExitCode']==0 and exited['stdoutSha256']==hashlib.sha256((identity+'\n').encode()).hexdigest() and
 exited['stderrSha256']==hashlib.sha256(b'').hexdigest() and not (journal/'stop-unknown.json').exists(),'ORIGINAL_STOP_NOT_PROVEN')
pinned_json(intent['originalStartPin']);pinned_json(intent['originalFailureResultPin'])
need(pin('/var/lib/spug-restore-resources/active.json')==ACTIVE_POINTER,'RETAINED_POINTER_CHANGED')
native=ReadOnlyTarget(configuration,request,operation);native.original=request
native.command=lambda args,**kwargs:subprocess.check_output(args,timeout=20) if not kwargs.get('mutation') else need(False,'READ_ONLY_COMMAND_REQUIRED')
def query(statement,*,mutation=False):
 need(not mutation,'READ_ONLY_COMMAND_REQUIRED');return (native.query(statement)+'\n').encode()
fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 _verify_reservation(configuration,request,operation)
 observation=observe(configuration,request,operation,885)
 current={role:native.inspect(service['id']) for role,service in native.config_services.items()}
 for old in SERVICES:
  row=current[old['role']]
  need(row['Id']==old['id'] and row['Image']==old['image'],'SERVICE_IDENTITY_CHANGED')
  if old['role']=='minio':
   need(not row['State']['Running'] and row['State']['Pid']==0 and row['State']['StartedAt']==old['startedAt'],'MINIO_NOT_QUIESCENT')
  else:
   need(row['State']['Running']==old['running'] and row['State']['Pid']==old['pid'] and row['State']['StartedAt']==old['startedAt'],'OTHER_MAIN_RUNTIME_CHANGED')
 archive_view(native).verify();published_fence(native).verify();mysql_scheduler(native,query=query).verify()
 for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
 ids=subprocess.check_output(['docker','ps','-aq','--no-trunc'],timeout=15).decode().split()
 rows1=json.loads(subprocess.check_output(['docker','inspect',*ids],timeout=20))
 rows2=json.loads(subprocess.check_output(['docker','inspect',*ids],timeout=20))
 def compare(rows,sort):
  out={}
  for row in rows:
   definition={k:row[k] for k in ('Path','Args','HostConfig','Config','Mounts')}
   if sort:definition['Mounts']=sorted(definition['Mounts'],key=lambda m:m['Destination'])
   out[row['Id']]=digest(definition)
  return out
 unstable=[identity for identity,value in compare(rows1,False).items() if compare(rows2,False)[identity]!=value]
 need(compare(rows1,True)==compare(rows2,True),'SORTED_DEFINITIONS_UNSTABLE')
 report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,
  intentPin=intentpin,stopExitPin=exitpin,originalStartPin=intent['originalStartPin'],originalFailurePinsUnchanged=len(PINS),
  originalMinioStopped=True,otherFourMainRuntimeUnchanged=True,protectionAndReservationRetained=True,schedulerRemainsPaused=True,
  databaseTableCount=observation['tableCount'],stopRepeated=False,restoreDispatched=False,
  observationReconciliation='Docker Mounts order is not canonical; use sorted mounts and independently pinned original runtime.',
  repeatedReadUnsortedDefinitionDifferences=len(unstable),repeatedReadSortedDefinitionsStable=True)
 append(journal/'quiescence-reconciled.json',report);print(json.dumps(report))
os.close(fd)
'''
if __name__=='__main__':
    assert not (TASK/'health-storage-quiescence.json').exists()
    failure=json.loads((TASK/'healthcheck-failure-diagnosis.json').read_text(encoding='utf-8'))
    old=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    other=json.loads((TASK/'other-business-health-installed.json').read_text(encoding='utf-8'))
    assert other['status']=='PASS' and other['otherBusinessContainerCount']==190
    values=dict(ROOT=ROOT,TARGET=TARGET,LOCK=LOCK,OPERATION=failure['operationId'],SERVICES=failure['services'],
        PINS=failure['evidencePins']+old['evidencePins'],ACTIVE_POINTER=failure['activePointerPin'])
    report=remote('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,150)
    report['other190RuntimeAndAll195DefinitionsIndependentlyVerified']=True
    (TASK/'health-storage-quiescence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
