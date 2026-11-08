"""Audit bounded original binlog events before opening the backup stop window."""
import json
import sys
from common import PRIVATE,TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,sys,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
sys.path.insert(0,str(pathlib.Path(ENGINE)/'formal'))
from formal_snapshot_linux import PrivateDockerMySql
from formal_capture_incremental import binlog_ranges,validate_position
if CANDIDATE_MODULE is not None:
 import base64,types
 candidate=types.ModuleType('formal_binlog_scope')
 candidate.__file__='<read-only-committed-candidate>'
 exec(compile(base64.b64decode(CANDIDATE_MODULE),candidate.__file__,'exec'),candidate.__dict__)
 sys.modules['formal_binlog_scope']=candidate
from formal_binlog_scope import inspect_binlog_scope,RowEventScope
diagnostic={};diagnostics=[]
original_observe=RowEventScope.observe
def observe(self,event_type,info):
 try:return original_observe(self,event_type,info)
 except Exception as error:
  diagnostic.update(eventType=event_type,info=info,infoSha256=hashlib.sha256(info.encode()).hexdigest(),eventCount=self.event_count,errorCode=str(error))
  if DIAGNOSTIC_SCAN and event_type=='Query' and str(error)=='FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN' and self.gtid and not self.transaction:
   diagnostics.append(dict(diagnostic));self.gtid=False;self.tables.clear();return
  raise
RowEventScope.observe=observe
def read(pin):
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'PIN_CHANGED'
 return json.loads(raw)
reference='smallapp-7fec29a3e132463096aec915c08acab3'
bindings=[read(json.loads(p.read_bytes())) for p in (root/'registry/points').glob('*.json')]
matches=[b for b in bindings if b['reference']==reference]
assert len(matches)==1,'PARENT_BINDING_REQUIRED'
binding=matches[0]
result=read(binding['resultPin']);point=read(result['data']['pointPin'])
capturepin=next(p for p in point['payloadRefs'] if p['path'].endswith('/capture-content-point.json'))
parent=read(capturepin)
config=json.loads((root/'configuration/capture.json').read_bytes());source=config['source']
pin=source['passwordPin'];raw=pathlib.Path(pin['path']).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
mysql=PrivateDockerMySql(source['mysqlContainerId'],raw.decode().strip(),timeout=30)
mysql.database_log_mode=source['databaseLogMode']
original_query=mysql.query
def query(sql):
 assert sql.startswith(('SELECT ','SHOW ')),'READONLY_QUERY_REQUIRED'
 return original_query(sql)
mysql.query=query
flags=mysql.query('SELECT @@server_uuid,@@version;').strip().split('\t')
master=mysql.query('SHOW MASTER STATUS;').strip('\n').split('\t')
end=dict(databaseUuid=flags[0],serverVersion=flags[1],file=master[0],position=int(master[1]),executedGtidSet=master[4])
validate_position(end)
logs=[dict(file=row.split('\t')[0],bytes=int(row.split('\t')[1])) for row in mysql.query('SHOW BINARY LOGS;').splitlines()]
segments=binlog_ranges(logs,parent['databaseEnd'],end)
out=dict(startedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),parentChainRef=reference,parentPointPin=result['data']['pointPin'],start=parent['databaseEnd'],end=end,segments=segments,binlogBytes=sum(s['stopPosition']-s['startPosition'] for s in segments))
module_path=pathlib.Path(ENGINE)/'formal/formal_binlog_scope.py';module_raw=module_path.read_bytes()
out['installedModulePin']=dict(path=str(module_path),bytes=len(module_raw),sha256=hashlib.sha256(module_raw).hexdigest())
try:
 assert parent['databaseEnd']['databaseUuid']==end['databaseUuid'],'DATABASE_UUID_CHANGED'
 def guard():
  assert time.monotonic()<deadline,'AUDIT_DEADLINE_EXCEEDED'
 deadline=time.monotonic()+600
 proof=inspect_binlog_scope(mysql,segments,source['database'],guard=guard,deadline=deadline)
 assert read(capturepin)==parent,'PARENT_CHANGED'
 out.update(status='DIAGNOSTIC_ONLY' if DIAGNOSTIC_SCAN else 'PASS',proof=proof)
except Exception as error:
 out.update(status='FAIL',errorType=type(error).__name__,errorCode=str(error) if str(error).replace('_','').isalnum() else 'BINLOG_SCOPE_AUDIT_FAILED',diagnostic=diagnostic)
out['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
out['diagnostics']=diagnostics
print(json.dumps(out))
'''

if __name__=='__main__':
    scan='--scan' in sys.argv
    candidate='--candidate' in sys.argv
    import base64
    payload=base64.b64encode((TASK.parents[2]/'ops/backup_engine/formal/formal_binlog_scope.py').read_bytes()).decode() if candidate else None
    tmpfs_candidate='--tmpfs-candidate' in sys.argv
    parent_installed='--parent-installed' in sys.argv or tmpfs_candidate
    installed='--installed' in sys.argv or parent_installed
    installation='source-control-parent-installation.json' if parent_installed else 'source-control-installation.json'
    engine=json.loads((TASK/installation).read_text(encoding='utf-8'))['engine'] if installed else '/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/engine'
    if parent_installed:
        assert not scan and not candidate
        assert not (TASK/('binlog-scope-tmpfs-candidate.json' if tmpfs_candidate else 'binlog-scope-parent-installed.json')).exists()
    value=remote('172.30.30.57','ENGINE='+repr(engine)+'\nCANDIDATE_MODULE='+repr(payload)+'\nDIAGNOSTIC_SCAN='+repr(scan)+'\n'+SCRIPT,660)
    phase='installed' if installed else 'candidate' if candidate else 'scan' if scan else 'diagnostic' if '--diagnose' in sys.argv else 'preflight'
    if parent_installed:phase='parent-installed'
    if tmpfs_candidate:phase='tmpfs-candidate'
    if '--retry-2' in sys.argv:
        assert installed and not scan and not candidate
        phase='installed-retry-2'
    write(PRIVATE/('binlog-scope-'+phase+'.private.json'),value)
    if 'diagnostic' in value:value['diagnostic'].pop('info',None)
    for item in value['diagnostics']:item.pop('info',None)
    write(TASK/('binlog-scope-'+phase+'.json'),value)
    print(json.dumps({k:v for k,v in value.items() if k not in ('proof','diagnostics','segments')}|dict(diagnosticCount=len(value['diagnostics']),segmentCount=len(value['segments']))))
    if value['status']!='PASS':raise SystemExit(1)
