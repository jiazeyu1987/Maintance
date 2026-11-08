"""Read-only process classification; never emit commands, SQL or credentials."""
import argparse,hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,json,pathlib,re
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
capture=root/'capture-staging'/OPERATION
workers=[]
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if b'minimal_capture_worker.py' in command and str(capture).encode() in command:workers.append(int(process.name))
rows=[];pending=list(workers);seen=set()
while pending and len(seen)<64:
 pid=pending.pop(0)
 if pid in seen:continue
 seen.add(pid);p=pathlib.Path('/proc')/str(pid)
 try:
  command=(p/'cmdline').read_bytes();status=(p/'status').read_text();wchan=(p/'wchan').read_text().strip()
  pending.extend(int(x) for x in (p/'task'/str(pid)/'children').read_text().split())
 except (FileNotFoundError,ProcessLookupError):continue
 kind='OTHER_CAPTURE_CHILD'
 for token,label in ((b'SHOW BINLOG EVENTS','BINLOG_SCOPE_QUERY'),(b'mysqlbinlog','BINLOG_EXPORT'),(b'@@server_uuid','SOURCE_FENCE_QUERY'),(b'docker\x00inspect','CONTAINER_PROTECTION_CHECK'),(b'minimal_capture_worker.py','CAPTURE_WORKER'),(b'mysql','MYSQL_QUERY')):
  if token in command:kind=label;break
 row=dict(pid=pid,kind=kind,state=next(l.split()[1] for l in status.splitlines() if l.startswith('State:')),waitChannel=wchan)
 position=re.search(rb"SHOW BINLOG EVENTS IN ['\"]([A-Za-z0-9_-]+\.[0-9]{6})['\"] FROM ([0-9]+)",command)
 if position:row['logPosition']=dict(file=position[1].decode(),position=int(position[2]))
 rows.append(row)
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,processes=rows,readOnly=True)))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['incremental-3','incremental-4'],default='incremental-3');args=parser.parse_args()
 operation=json.loads((TASK/(args.kind+'-ui-submission.json')).read_text(encoding='utf-8'))['request']['operationId']
 value=remote('172.30.30.57','OPERATION='+repr(operation)+'\n'+SCRIPT,30)
 write(PRIVATE/('capture-step-'+hashlib.sha256(value['observedAt'].encode()).hexdigest()[:12]+'.private.json'),value)
 write(TASK/(args.kind+'-active-step.json'),value);print(json.dumps(value))
