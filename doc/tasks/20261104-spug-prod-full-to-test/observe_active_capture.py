"""Bounded observation of this exact operation and its live process handles."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import datetime,hashlib,json,pathlib,os
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1');op='smallapp-73cd541a95d84d6a86f9d693e4053c75'
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':op,'files':[],'processes':[],'scratchDirectoryEntries':{},'events':[]}
data_path=root/'capture-staging'/op/'payload/011-source-data.json'
if data_path.is_file():
 data=json.loads(data_path.read_bytes());out['databaseEvidenceShape']={k:{'type':type(v).__name__,'keys':sorted(v) if isinstance(v,dict) and len(v)<=20 else None,'count':len(v) if isinstance(v,(dict,list)) else None} for k,v in data.items()}
for p in sorted((root/'capture-staging'/op).glob('event-*.json'))[-5:]:
 event=json.loads(p.read_bytes());out['events'].append({k:event[k] for k in ('at','stage','elapsedSeconds') if k in event})
for base in [root/'repository-operations'/hashlib.sha256(op.encode()).hexdigest(),root/'capture-staging'/op]:
 if base.exists():
  for p in list(base.iterdir()):
   if p.is_file() and not p.name.startswith('capture-query-'):s=p.stat();out['files'].append({'path':str(p.relative_to(root)),'bytes':s.st_size,'modifiedAt':s.st_mtime})
   elif p.is_dir():
    if p.name.startswith('scratch-'):out['scratchDirectoryEntries'][p.name]=len(list(p.iterdir()))
    for q in list(p.iterdir())[:30]:
     if q.is_file():s=q.stat();out['files'].append({'path':str(q.relative_to(root)),'bytes':s.st_size,'modifiedAt':s.st_mtime})
rows={}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes();status=(p/'status').read_text();parent=int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')))
  rows[int(p.name)]=(p,cmd,status,parent)
 except (OSError,StopIteration):continue
chosen={pid for pid,(_,cmd,_,_) in rows.items() if op.encode() in cmd and b'-B -' not in cmd}
worker_path=root/'repository-operations'/hashlib.sha256(op.encode()).hexdigest()/'worker-process.json'
if worker_path.is_file():
 worker=json.loads(worker_path.read_bytes())
 if isinstance(worker.get('pid'),int) and worker['pid'] in rows:chosen.add(worker['pid'])
for _ in range(8):chosen.update(pid for pid,(_,_,_,parent) in rows.items() if parent in chosen)
for pid in sorted(chosen):
 p,cmd,status,parent=rows[pid]
 try:out['processes'].append({'pid':pid,'ppid':parent,'executable':pathlib.Path(cmd.split(b'\0')[0].decode()).name,'state':next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('State:')),'wchan':(p/'wchan').read_text(),'io':dict(l.split(':',1) for l in (p/'io').read_text().splitlines()),'openFiles':len(list((p/'fd').iterdir()))})
 except OSError:pass
print(json.dumps(out))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT,timeout=25)
 (TASK/'active-capture.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'observedAt':r['observedAt'],'events':r['events'],'scratchDirectoryEntries':r['scratchDirectoryEntries'],'processes':[{'pid':p['pid'],'executable':p['executable'],'state':p['state'],'readCharacters':int(p['io'].get('rchar','0')),'writtenBytes':int(p['io'].get('write_bytes','0'))} for p in r['processes']],'payloadFiles':[{'name':f['path'].rsplit('/',1)[-1],'bytes':f['bytes']} for f in r['files'] if '/payload/' in f['path']]}))
