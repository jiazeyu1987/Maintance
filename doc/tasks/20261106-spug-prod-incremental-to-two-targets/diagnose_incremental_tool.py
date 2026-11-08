"""Read-only original failed capture and its pinned binlog tool identity."""
import hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
operation='smallapp-a690233d967d4965bf5f861dc1126961'
repository=root/'repository-operations'/hashlib.sha256(operation.encode()).hexdigest()
capture=root/'capture-staging'/operation
documents={}
for path in [repository/'result.json',capture/'terminal-result.json',capture/'worker-failure.json',capture/'job-configuration.json']:
 if path.is_file():documents[str(path)]=json.loads(path.read_bytes())
configuration=json.loads((capture/'job-configuration.json').read_bytes())
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),documents=documents,tools=[])
def visit(value):
 if isinstance(value,dict):
  if set(value)=={'path','bytes','sha256'}:
   path=pathlib.Path(value['path'])
   if path.is_file() and path.stat().st_size<100000:
    raw=path.read_bytes()
    try:doc=json.loads(raw)
    except (ValueError,UnicodeError):return
    if isinstance(doc,dict) and 'executable' in doc and 'containerId' in doc:
     tool=dict(document=doc,pin=value,pinMatches=len(raw)==value['bytes'] and hashlib.sha256(raw).hexdigest()==value['sha256'])
     p=subprocess.run(['docker','inspect',doc['containerId']],capture_output=True,timeout=20)
     if p.returncode==0:
      row=json.loads(p.stdout)[0];tool['actualContainer']=dict(id=row['Id'],image=row['Image'],configImage=row['Config']['Image'],state=row['State'],readonlyRootfs=row['HostConfig']['ReadonlyRootfs'],networkMode=row['HostConfig']['NetworkMode'],pidMode=row['HostConfig']['PidMode'],path=row['Path'],args=row['Args'],restartPolicy=row['HostConfig']['RestartPolicy'],mounts=[dict(destination=m['Destination'],writable=m['RW']) for m in row['Mounts']])
      for args,key in [(['docker','exec',row['Id'],'sha256sum',doc['executable']],'checksum'),(['docker','exec',row['Id'],doc['executable'],'--version'],'version')]:
       result=subprocess.run(args,capture_output=True,timeout=20);tool[key]=dict(exitCode=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace'))
     else:tool['inspectError']=p.stderr.decode(errors='replace')
     out['tools'].append(tool)
  for v in value.values():visit(v)
 elif isinstance(value,list):
  for v in value:visit(v)
visit(configuration)
out['stderr']=(capture/'worker-stderr.log').read_text() if (capture/'worker-stderr.log').exists() else None
print(json.dumps(out))
'''
if __name__=='__main__':
 value=remote('172.30.30.57',SCRIPT,100)
 write(PRIVATE/'incremental-364-failure.private.json',value)
 public={k:v for k,v in value.items() if k!='documents'}
 public['terminalDocuments']=[dict(path=k,state=v.get('state'),failureCode=v.get('failureCode'),actualExitCode=v.get('actualExitCode'),dataKeys=list(v.get('data') or {})) for k,v in value['documents'].items()]
 write(TASK/'incremental-364-failure.json',public)
 print(json.dumps(public))
