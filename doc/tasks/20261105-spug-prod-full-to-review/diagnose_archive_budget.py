"""Read the terminated operation and live budget without changing any state."""
import json
from preflight import COMMON, PRIVATE, TASK, remote

CHECK = r'''
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import ReadOnlyTarget
unit=receipt['service']
props=dict(line.split('=',1) for line in run(['systemctl','show',unit,'-p','MainPID','-p','ControlGroup','-p','LimitNOFILE']).decode().splitlines())
pid=int(props['MainPID']);need(pid>0,'CONTROL_NOT_RUNNING')
limit=next(line for line in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if line.startswith('Max open files'))
cg=pathlib.Path('/sys/fs/cgroup/systemd')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
if not cg.exists():cg=pathlib.Path('/sys/fs/cgroup')/props['ControlGroup'].lstrip('/')/'cgroup.procs'
need({int(v) for v in cg.read_text().split()}=={pid},'CONTROL_WORKERS_ACTIVE')
files=[];documents={}
for directory in ('ledger','operations','recovery-operations','replacement-state'):
 for p in (root/directory/OPERATION).rglob('*'):
  if p.is_file():
   files.append(pin(p))
   if p.suffix=='.json' and p.stat().st_size<256*1024:documents[str(p.relative_to(root))]=json.loads(p.read_bytes())
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
if active.exists():files.append(pin(active));documents[str(active)]=json.loads(active.read_bytes())
request=json.loads((root/'ledger'/OPERATION/'request.json').read_bytes())
native=ReadOnlyTarget(owner,request,root/'recovery-operations'/OPERATION)
db={'uuid':native.database_uuid(),'tableCount':int(native.query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+native.config['database']+"';"))}
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':OPERATION,'service':unit,'properties':props,'liveLimits':limit,'idleControl':True,'evidencePins':files,'documents':documents,'database':db,'business':business(),'activeReservation':active.exists()}))
'''

if __name__ == '__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    result=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+'\nOPERATION='+repr(operation)+'\n'+CHECK,90)
    (PRIVATE/'archive-budget-failure.private.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    baseline=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    public={k:v for k,v in result.items() if k not in ('documents','business')}
    public['allBusinessBaselineUnchanged']=result['business']==baseline['business']
    public['diagnostics']={name:{k:v for k,v in value.items() if k in ('state','errorCode','actualExitCode','archiveDiagnostic','archive_diagnostic','data','replacementStarted','targetQuiesced')} for name,value in result['documents'].items() if name.endswith(('result.json','completion.json','child-exit.json','replacement-result.json'))}
    (TASK/'archive-budget-diagnosis.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(public,ensure_ascii=False))
