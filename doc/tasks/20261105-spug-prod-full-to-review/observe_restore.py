"""Bounded read-only observation of the submitted restore, without payload IO."""
import json
from preflight import remote,TASK
SCRIPT=r'''
import datetime,json,pathlib,subprocess
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION_LITERAL
ledger=root/'ledger'/operation
op=root/'recovery-operations'/operation
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'ledgerFiles':[p.name for p in ledger.iterdir()],'processes':[],'evidenceFiles':[]}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  command=(p/'cmdline').read_bytes()
  if operation.encode() in command:
   numbers={line.split(':')[0]:int(line.split(':')[1]) for line in (p/'io').read_text().splitlines()}
   limit=next(line for line in (p/'limits').read_text().splitlines() if line.startswith('Max open files'))
   out['processes'].append({'pid':int(p.name),'program':command.split(b'\0')[1:3][0].decode(errors='replace'),'rchar':numbers['rchar'],'wchar':numbers['wchar'],'readBytes':numbers['read_bytes'],'writeBytes':numbers['write_bytes'],'wchan':(p/'wchan').read_text(),'openFileLimits':limit.split()[3:5]})
 except (OSError,IndexError):pass
for p in op.rglob('*.json'):
 relative=str(p.relative_to(op))
 if any(x in relative.lower() for x in ('result','progress','step','receipt','readback','comparison','cleanup','consistency')):
  out['evidenceFiles'].append({'path':relative,'bytes':p.stat().st_size})
 if len(out['evidenceFiles'])>=50:break
for name in ('worker-terminal.json','admission-error.json'):
 if (ledger/name).is_file():out[name]=json.loads((ledger/name).read_bytes())
out['nativeTimings']=[]
for p in sorted(op.rglob('timing-*.json')):
 if p.stat().st_size<=2048:out['nativeTimings'].append(dict(path=str(p.relative_to(op)),value=json.loads(p.read_bytes())))
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
ids=[s['id'] for s in owner['targets'][receipt['targetConfigRef']]['services']]
rows=json.loads(subprocess.check_output(['docker','inspect']+ids,timeout=15))
out['services']=[{'id':r['Id'],'running':r['State']['Running'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt']} for r in rows]
scratch=op/'database-000/database-readback'
parts=[p for p in scratch.iterdir() if p.is_dir()] if scratch.is_dir() else []
out['readback']={'tableDirectories':len(parts),'tokenFiles':sum((p/'tokens.tsv').is_file() for p in parts)}
print(json.dumps(out))
'''
if __name__=='__main__':
 import sys
 operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
 result=remote('172.30.30.59',SCRIPT.replace('OPERATION_LITERAL',repr(operation)),45)
 (TASK/'restore-native-progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 if '--compact' in sys.argv:
  ui=json.loads((TASK/'restore-live-progress.json').read_text(encoding='utf-8')) if (TASK/'restore-live-progress.json').exists() else {}
  stages={}
  for row in result['nativeTimings']:
   value=row['value'];stage=value['stage']
   if 'completed' in value:stages[stage]='DONE' if value['completed'] else 'FAILED'
   else:stages.setdefault(stage,'RUNNING')
  print(json.dumps({'observedAt':result['observedAt'],'operationId':operation,
   'state':ui.get('state'),'errorCode':ui.get('errorCode'),'stages':stages,
   'workers':[{'pid':p['pid'],'readGiB':round(p['rchar']/1024**3,2),'writeGiB':round(p['wchar']/1024**3,2),'wchan':p['wchan'],'openFileLimits':p['openFileLimits']}
              for p in result['processes'] if 'recovery_minimal_worker.py' in p['program']],
   'evidenceFileCount':len(result['evidenceFiles']),
   'readback':result['readback'],
   'runningServiceCount':sum(s['running'] for s in result['services'])}))
 else:print(json.dumps(result))
