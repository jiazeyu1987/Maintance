"""Read installed lineage and restore contracts without changing server state."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from common import PRIVATE,TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
root=pathlib.Path(ROOT)
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
engine=pathlib.Path(owner['formalModuleDirectory']).parent
out=dict(host=HOST,observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),engines={})
engines={'target':engine}
if HOST.endswith('.57'):engines['source']=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/engine')
for name,base in engines.items():
 files={}
 for rel in ['common/recovery_replace.py','formal/formal_binlog_scope.py','formal/formal_capture_incremental.py','formal/formal_sql_importer.py','formal/formal_snapshot_linux.py']:
  p=base/rel
  if not p.exists():continue
  raw=p.read_bytes();lines=raw.decode().splitlines()
  files[rel]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),matches=[dict(line=i+1,text=line) for i,line in enumerate(lines) if any(k in line for k in ('sql_log_bin','scoped_database_ddl','MYSQL80_ROW','disable-log-bin','binlogDatabaseScope','event_scheduler','scope/v'))])
 packagepath=base/'package.json'
 package=json.loads(packagepath.read_bytes())
 out['engines'][name]=dict(path=str(base),packageKeys=list(package),fileCount=len(package['files']),filesMatch=all(hashlib.sha256((base/n).read_bytes()).hexdigest()==v for n,v in package['files'].items()),files=files)
print(json.dumps(out))
'''

def collect(suffix):
    root=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
    value=remote('172.30.30.'+suffix,'HOST='+repr('172.30.30.'+suffix)+'\nROOT='+repr(root)+'\n'+SCRIPT)
    write(TASK/('runtime-contract-'+suffix+'.json'),value)
    return value

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(collect,['57','58','59']):
            print(json.dumps(result))
