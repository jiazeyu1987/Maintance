"""Read-only parent attachment ordinal and configured capture time budget."""
import argparse,json
from common import TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,os,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
capture=root/'capture-staging'/OPERATION
configuration=json.loads((capture/'job-configuration.json').read_bytes())
def read(reference):
 assert 0<reference['bytes']<=64*1024*1024
 raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
 return json.loads(raw)
descriptor=read(configuration['source']['objectSourcePin']);index=read(descriptor['parentExportIndexPin'])
content=list(index['contentPins'].items());positions={pathlib.Path(row['path']).name:(i,sha,row) for i,(sha,row) in enumerate(content)}
active=[]
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:
  command=(process/'cmdline').read_bytes()
  if OPERATION.encode() not in command or b'python' not in command:continue
  for fd in (process/'fd').iterdir():
   path=os.readlink(fd)
   name=pathlib.Path(path).name
   if '/archives/' not in path or name not in positions:continue
   ordinal,sha,row=positions[name]
   info=dict(line.split(':',1) for line in (process/'fdinfo'/fd.name).read_text().splitlines() if ':' in line)
   if int(info['flags'].strip(),8)&os.O_PATH:continue
   if fd.stat().st_size!=row['bytes']:continue
   active.append(dict(pid=int(process.name),ordinal=ordinal+1,contentSha256=sha,bytes=row['bytes'],position=int(info['pos']),precedingContentBytes=sum(p['bytes'] for _,p in content[:ordinal])))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,captureWorkSeconds=configuration['limits']['workSeconds'],totalParentContents=len(content),totalParentContentBytes=sum(p['bytes'] for _,p in content),activeParentContentReads=active)))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['incremental-2','incremental-3'],default='incremental-2');args=parser.parse_args()
 request=json.loads((TASK/(args.kind+'-ui-submission.json')).read_text(encoding='utf-8'))['request']
 report=remote('172.30.30.57','OPERATION='+repr(request['operationId'])+'\n'+SCRIPT,45)
 write(TASK/('capture-budget-progress'+('-'+args.kind if args.kind=='incremental-3' else '')+'.json'),report);print(json.dumps(report))
