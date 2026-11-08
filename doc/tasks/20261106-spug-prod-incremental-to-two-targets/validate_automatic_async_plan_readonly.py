"""Candidate code runs only in memory, with writes/reconcile explicitly blocked."""
import json
import sys
from common import TASK,PRIVATE,SOURCE,remote,write

SCRIPT=r'''
import hashlib,json,os,pathlib,sys,time,datetime,collections,stat
control=INSTALL['controllers'][0]['control'];reference=INSTALL['controllers'][0]['controlConfigurationPin']
raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
import recovery_control_smallapp as ledger_module
import recovery_control_smallapp_native as native_module
import recovery_control_incremental_plan as planning
for module,source in ((ledger_module,LEDGER),(native_module,NATIVE)):
 exec(compile(source,module.__file__,'exec'),module.__dict__)
# Reload the unchanged installed planner against the candidate Ledger class.
exec(compile(pathlib.Path(planning.__file__).read_bytes(),planning.__file__,'exec'),planning.__dict__)
import recovery_control_executor as executor
def no_reconcile(*args,**kwargs):raise RuntimeError('DIAGNOSTIC_RECONCILE_FORBIDDEN')
native_module.Native.reconcile=no_reconcile
def audit(event,args):
 if event=='open':
  mode=args[1];flags=args[2]
  if isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
   if args[0]=='/dev/null' and not flags&(os.O_CREAT|os.O_TRUNC|os.O_APPEND):return
   if isinstance(args[0],int) and stat.S_ISFIFO(os.fstat(args[0]).st_mode):return
   raise RuntimeError('DIAGNOSTIC_SERVER_WRITE_FORBIDDEN')
 if event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.chmod','os.chown','os.symlink','os.link'):
  raise RuntimeError('DIAGNOSTIC_SERVER_WRITE_FORBIDDEN')
sys.addaudithook(audit)
native=native_module.Native(reference);reads=[];old=executor.pinned_read;phases=[]
def measured(path,*args,**kwargs):
 start=time.monotonic()
 try:
  answer=old(path,*args,**kwargs);reads.append(dict(path=str(path),bytes=answer[0]['bytes'],seconds=time.monotonic()-start));return answer
 except Exception:raise
executor.pinned_read=measured
original_closed=native.asynchronously_closed
def closed(*args,**kwargs):
 start=time.monotonic();value=original_closed(*args,**kwargs);phases.append(dict(phase='async-closure',operationId=args[1]['operationId'],closed=value,seconds=time.monotonic()-start));return value
native.asynchronously_closed=closed
for method in ('configuration','registration','source_epoch','incremental_source_observation'):
 original=getattr(native,method)
 def wrap(*args,_method=method,_original=original,**kwargs):
  start=time.monotonic()
  try:return _original(*args,**kwargs)
  finally:phases.append(dict(phase=_method,seconds=time.monotonic()-start))
 setattr(native,method,wrap)
start=time.monotonic();plan=native.incremental_plan(SOURCE);elapsed=time.monotonic()-start
print(json.dumps(dict(status='OBSERVED',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan=plan,elapsedSeconds=elapsed,phases=phases,reads=reads,
 codeSha256=dict(ledger=hashlib.sha256(LEDGER.encode()).hexdigest(),native=hashlib.sha256(NATIVE.encode()).hexdigest()),
 serverWrites=False,reconcileCalls=0,candidateLoadedInMemoryOnly=True)))
'''

if __name__=='__main__':
    attempt=sys.argv[1];assert attempt.replace('-','').isalnum()
    private=PRIVATE/('automatic-async-plan-'+attempt+'.private.json');public=TASK/('automatic-async-plan-'+attempt+'.json')
    assert not private.exists() and not public.exists()
    install=json.loads((PRIVATE/'automatic-control-installation-57.private.json').read_text(encoding='utf-8'))
    root=TASK.parents[2]/'backend/src/main/resources'
    variables=dict(INSTALL=install,SOURCE=SOURCE,LEDGER=(root/'recovery_control_smallapp.py').read_text(encoding='utf-8'),NATIVE=(root/'recovery_control_smallapp_native.py').read_text(encoding='utf-8'))
    value=remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,timeout=90)
    write(private,value);summary={k:v for k,v in value.items() if k!='reads'}
    summary.update(pinReadCalls=len(value['reads']),pinReadBytes=sum(r['bytes'] for r in value['reads']),pinReadSeconds=sum(r['seconds'] for r in value['reads']),
        readbackReads=sum(1 for r in value['reads'] if r['path'].endswith('/readback-original.json')))
    write(public,summary);print(json.dumps(summary))
