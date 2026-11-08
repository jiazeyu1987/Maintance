"""Read-only process phase evidence without exposing command arguments or SQL."""
import hashlib
import json
from common import TASK, PRIVATE, remote, write

SCRIPT = r'''
import datetime,hashlib,json,os,pathlib
rows={}
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  s=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
  cmd=(p/'cmdline').read_bytes()
  rows[int(p.name)]=dict(pid=int(p.name),ppid=int(s['PPid']),comm=(p/'comm').read_text().strip(),state=s['State'].strip(),
   wchan=(p/'wchan').read_text().strip(),io=(p/'io').read_text(),commandSha256=hashlib.sha256(cmd).hexdigest())
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
selected={WORKER}
for _ in range(8):selected|={pid for pid,value in rows.items() if value['ppid'] in selected}
out=[]
for pid in sorted(selected):
 if pid not in rows:continue
 row=rows[pid];fds=[]
 try:paths=list((pathlib.Path('/proc')/str(pid)/'fd').iterdir())
 except (FileNotFoundError,ProcessLookupError):
  row['exitedDuringObservation']=True;out.append(row);continue
 for p in paths:
  try:
   name=os.readlink(p)
   if name.startswith('pipe:') or name.startswith('socket:'):fds.append(dict(fd=p.name,kind=name.split(':',1)[0]))
   elif name.startswith('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/'):
    info=dict(line.split(':',1) for line in (p.parent.parent/'fdinfo'/p.name).read_text().splitlines() if ':' in line)
    fds.append(dict(fd=p.name,name=pathlib.Path(name).name,position=int(info.get('pos','0'))))
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 row['fds']=fds;out.append(row)
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,processes=out,serverWrites=False)))
'''

if __name__ == '__main__':
    request=json.loads((TASK/'automatic-full-ui-submission.json').read_text(encoding='utf-8'))['request']
    actual=remote('172.30.30.57','WORKER=18863\nOPERATION='+repr(request['operationId'])+'\n'+SCRIPT,40)
    destination=TASK/('automatic-full-worker-'+hashlib.sha256(actual['observedAt'].encode()).hexdigest()[:12]+'.json')
    write(destination,actual)
    print(json.dumps(actual))
