"""Read-only native progress of this one accepted incremental operation."""
import ast,hashlib,json,sys
from common import TASK,PRIVATE,remote,write

tree=ast.parse((TASK.parent/'20261105-spug-full-to-prod/observe_preservation_backup.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='SCRIPT' for x in n.targets))
kind=sys.argv[1] if len(sys.argv)>1 else 'incremental'
assert kind in ('incremental','incremental-2','incremental-3','incremental-4','automatic-full','automatic-i1','automatic-i2')
operation=json.loads((TASK/(kind+'-ui-submission.json')).read_text(encoding='utf-8'))['request']['operationId']
repository_id=hashlib.sha256(operation.encode()).hexdigest()
script=script.replace('smallapp-7fec29a3e132463096aec915c08acab3',operation).replace('433710bb8eb93e78351878966cb06caec1c420e87ef3d5c8dff9c493dc085eb9',repository_id)
for before,after in (
 ("for name in ['scratch-before','scratch-after']:","for name in ['scratch-before','scratch-after','scratch-affected']:"),
 ("for name in ['database.sql.gz','011-source-data.json','012-source-data-after.json','capture-content-point.json']:","for name in ['database.sql.gz','database.sql.incremental.raw','database.sql.incremental-scope.json','source-affected-data.json','011-source-data.json','012-source-data-after.json','capture-content-point.json']:"),
):
 assert script.count(before)==1,'PROGRESS_TEMPLATE_CHANGED'
 script=script.replace(before,after)
phase=r'''
import os,stat
capture=root/'capture-staging'/operation
queries=root/'ledger'/operation/'queries'
query_files=[p for p in queries.iterdir() if p.is_file()] if queries.is_dir() else []
report['operationQuerySnapshots']=dict(files=len(query_files),latestMtime=max((p.stat().st_mtime for p in query_files),default=None),databaseProgressEvidence=False)
report['semanticTopLevel']=[]
for path in sorted((capture/'semantic-capture').glob('*'))[:32]:
 info=path.lstat()
 report['semanticTopLevel'].append(dict(name=path.name,bytes=info.st_size,isDirectory=stat.S_ISDIR(info.st_mode)))
report['nativeCaptureEvents']=[]
for event in sorted(capture.glob('event-*.json'))[-5:]:
 if event.stat().st_size<=65536:
  value=json.loads(event.read_bytes());report['nativeCaptureEvents'].append({k:value[k] for k in ('at','stage') if k in value})
for worker in report['workers']:
 worker['activeArchiveReads']=[]
 process=pathlib.Path('/proc')/str(worker['pid'])
 try:
  arguments=(process/'cmdline').read_bytes().decode().split('\0')
  worker['program']=next((arg for arg in arguments if arg.startswith('/') and arg.endswith('.py')),None)
  for fd in list((process/'fd').iterdir())[:128]:
   name=os.readlink(fd)
   if '/archives/' not in name and str(capture) not in name:continue
   values=dict(line.split(':',1) for line in (process/'fdinfo'/fd.name).read_text().splitlines() if ':' in line)
   if int(values.get('flags','0').strip(),8)&os.O_PATH:continue
   info=fd.stat()
   if not stat.S_ISREG(info.st_mode):continue
   worker['activeArchiveReads'].append(dict(category='CURRENT_CAPTURE' if str(capture) in name else 'ARCHIVE',fileName=pathlib.Path(name).name,bytes=info.st_size,position=int(values.get('pos','0'))))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
'''
script=script.replace('print(json.dumps(report))',phase+'\nprint(json.dumps(report))')
if '--nas' in sys.argv[2:]:
 nas=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='NAS' for x in n.targets))
 nas=nas.replace('exact-original-360-archive-only','exact-current-operation-archive-only')
 script=script.replace('print(json.dumps(report))',nas+'\nprint(json.dumps(report))')
value=remote('172.30.30.57',script,65)
write(PRIVATE/(kind+'-progress-'+hashlib.sha256(value['observedAt'].encode()).hexdigest()[:12]+'.private.json'),value)
write(PRIVATE/(kind+'-progress.private.json'),value);write(TASK/(kind+'-native-progress.json'),value)
if '--brief' in sys.argv[2:]:
 workers=[]
 for worker in value['workers']:
  counters=dict(line.split(':',1) for line in worker['io'].splitlines())
  workers.append(dict(pid=worker['pid'],role=worker['role'],state=worker['state'],readGiB=round(int(counters['rchar'])/1024**3,2),writeGiB=round(int(counters['wchar'])/1024**3,2),observedStderrFiles=[dict(name=f['fileName'],bytes=f['bytes']) for f in worker['activeArchiveReads'] if f['category']=='CURRENT_CAPTURE' and f['fileName'].endswith('stderr.log')]))
 print(json.dumps({k:value[k] for k in ('observedAt','operationId','nativeCaptureEvents','staging','dataObservationScratch','knownCaptureFiles','semanticTopLevel','nativeReadbackRecords','operationQuerySnapshots')}|dict(workers=workers)|({'nas':value['nas']} if 'nas' in value else {})))
else:print(json.dumps({k:v for k,v in value.items() if k not in ('directories','workers')}|dict(workers=value['workers'])))
