"""Observe only the original .57 restore; never dispatch or mutate remote state."""
import json
from install_prod_control import remote, TASK

SCRIPT = r'''
import datetime,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION_LITERAL
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'documents':[],'nativeInvocationCounts':{}}
configuration_path=root/'recovery-operations'/operation/'configuration.json'
if configuration_path.is_file():
 configuration=json.loads(configuration_path.read_bytes())
 report['configuredDeadlineMilliseconds']=configuration.get('deadlineMilliseconds')
for base in (root/'ledger'/operation,root/'recovery-operations'/operation,root/'replacement-state'/operation):
 if not base.exists():continue
 paths=list(base.glob('*'))
 paths += [p for directory in base.iterdir() if directory.is_dir() and not directory.is_symlink() for p in directory.glob('*.json')]
 native=[p for p in set(paths) if p.name.startswith('native-') and p.suffix=='.json' and p.name[len('native-'):-5].isdecimal()]
 report['nativeInvocationCounts'][str(base.relative_to(root))]=len(native)
 selected_native=set(sorted(native,key=lambda p:p.stat().st_mtime)[-3:])
 for p in sorted(set(paths)-set(native)|selected_native):
  if not p.is_file() or p.is_symlink():continue
  st=p.stat()
  item={'path':str(p.relative_to(root)),'bytes':st.st_size,'modifiedAt':datetime.datetime.fromtimestamp(st.st_mtime,datetime.timezone.utc).isoformat()}
  if p.suffix=='.json' and st.st_size<262144:
   try:v=json.loads(p.read_bytes())
   except (ValueError,OSError):v={}
   if isinstance(v,dict):
    item['status']={k:v[k] for k in ('schemaVersion','state','stage','phase','failureCode','errorCode','actualExitCode','startedAt','finishedAt','pid','workerPid','timedOut','completed','elapsedSeconds','originalState','pausedState','originalStateRestored','role','ready','httpStatus','semanticStatus','attempts','fullSchemaDataEquivalenceVerified') if k in v}
    if v.get('state')=='SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF' and isinstance(v.get('tables'),dict):
     item['status'].update(tableCount=len(v['tables']),totalRows=sum(t['rows'] for t in v['tables'].values()),schemaSha256=v['schemaSha256'])
    for k in ('result','terminal'):
     if isinstance(v.get(k),dict):item[k]={n:v[k][n] for n in ('state','errorCode','actualExitCode','timedOut') if n in v[k]}
  report['documents'].append(item)
process_file=root/'ledger'/operation/'execute/native-process.json'
if process_file.exists():
 original=json.loads(process_file.read_bytes())['pid']
 processes={}
 for directory in pathlib.Path('/proc').iterdir():
  if not directory.name.isdecimal():continue
  try:
   fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
   processes[int(directory.name)]={'pid':int(directory.name),'parentPid':int(fields[1]),'state':fields[0],'startTicks':fields[19],'userTicks':int(fields[11]),'systemTicks':int(fields[12])}
  except (OSError,ValueError,IndexError):continue
 selected={original}
 while True:
  expanded=selected|{p for p,v in processes.items() if v['parentPid'] in selected}
  if expanded==selected:break
  selected=expanded
 report['processes']=[]
 for pid in sorted(selected):
  if pid not in processes:continue
  value=processes[pid]
  try:
   value['ioCounters']={k:int(v) for k,v in (line.split(':',1) for line in (pathlib.Path('/proc')/str(pid)/'io').read_text().splitlines())}
   value['waitChannel']=(pathlib.Path('/proc')/str(pid)/'wchan').read_text().strip()
  except (OSError,ValueError):pass
  report['processes'].append(value)
print(json.dumps(report))
'''

if __name__=='__main__':
    request=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']
    report=remote(SCRIPT.replace('OPERATION_LITERAL',repr(request['operationId'])),timeout=50)
    (TASK/'restore-native-progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    summaries=[v for v in report['documents'] if v.get('status') and ('elapsedSeconds' in v['status'] or 'state' in v['status'] or 'originalState' in v['status'] or 'pausedState' in v['status'] or 'ready' in v['status'])]
    summaries.sort(key=lambda v:v['modifiedAt'])
    print(json.dumps(dict(observedAt=report['observedAt'],operationId=report['operationId'],
                         documentCount=len(report['documents']),recentStages=summaries[-12:],processes=report.get('processes'),
                         nativeInvocationCounts=report['nativeInvocationCounts'],configuredDeadlineMilliseconds=report.get('configuredDeadlineMilliseconds'))))
