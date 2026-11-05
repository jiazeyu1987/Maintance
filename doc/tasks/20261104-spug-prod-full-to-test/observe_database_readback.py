"""Observe only file metadata and process counters for the active readback."""
import json
from repair_preflight import remote, TASK

SCRIPT = r'''
import datetime,json,pathlib
operation=OPERATION_LITERAL
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/recovery-operations')/operation
scratch=root/'database-000/database-readback'
parts=[p for p in scratch.iterdir() if p.is_dir()] if scratch.is_dir() else []
tokens=[p/'tokens.tsv' for p in parts if (p/'tokens.tsv').is_file()]
worker_pid=WORKER_PID_LITERAL
worker=pathlib.Path('/proc')/str(worker_pid)
children=[]
if worker.is_dir():
 command=(worker/'cmdline').read_bytes()
 assert operation.encode() in command and b'recovery_minimal_worker.py' in command,'WORKER_IDENTITY_CHANGED'
 for item in (worker/'task'/str(worker_pid)/'children').read_text().split():
  p=pathlib.Path('/proc')/item
  try:
   children.append({'pid':int(item),'program':(p/'comm').read_text().strip(),'wchan':(p/'wchan').read_text().strip()})
  except OSError:pass
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'operationId':operation,'scratchExists':scratch.is_dir(),
 'readbackTableDirectories':len(parts),'tokenFiles':len(tokens),
 'lastTokenModifiedAt':max((datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat() for p in tokens),default=None),
 'workerChildren':children,'businessWritesPerformed':False}
print(json.dumps(report))
'''

if __name__ == '__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    latest=json.loads((TASK/'restore-native-progress.json').read_text(encoding='utf-8'))
    assert latest['operationId']==operation
    workers=[p['pid'] for p in latest['processes'] if 'recovery_minimal_worker.py' in p['program']]
    assert len(workers)==1,'EXACT_ACTIVE_WORKER_REQUIRED'
    script=SCRIPT.replace('OPERATION_LITERAL',repr(operation)).replace('WORKER_PID_LITERAL',repr(workers[0]))
    report=remote('172.30.30.58',script,30)
    (TASK/'database-readback-live-summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
