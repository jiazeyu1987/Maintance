"""Read-only native query and parent-guard cost diagnosis; no business rows out."""
import json
from common import TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib,sys,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
engine=root/'engine-incremental-6319024';sys.path[:0]=[str(engine/'formal'),str(engine/'common')]
from formal_snapshot_linux import PrivateDockerMySql
from formal_capture_semantics import bounded_reference_query
from formal_capture_recovery_inputs import original_bytes
configuration=json.loads((root/'capture-staging'/OPERATION/'job-configuration.json').read_bytes());source=configuration['source']
descriptor=json.loads(original_bytes(source['objectSourcePin']))
recipe=json.loads(original_bytes(descriptor['referenceRecipePin']))
secret=original_bytes(source['passwordPin'],limit=16384).decode().removesuffix('\n')
mysql=PrivateDockerMySql(source['mysqlContainerId'],secret,timeout=120)
assert mysql.query('SELECT @@server_uuid;').strip()==source['databaseUuid']
observed=[]
for query in recipe['referenceQueries']:
 table=query['table'];columns=query['columns']
 assert set(columns)<={r.split('\t')[0] for r in mysql.query('DESCRIBE `'+source['database']+'`.`'+table+'`;').splitlines()}
 sql='SELECT '+','.join('HEX(CAST(`'+c+'` AS BINARY))' for c in columns)+' FROM `'+source['database']+'`.`'+table+'`;'
 started=time.monotonic();raw=bounded_reference_query(mysql,sql,lambda:None).encode()
 observed.append(dict(table=table,rows=len(raw.splitlines()),outputBytes=len(raw),seconds=time.monotonic()-started,diagnosticOnly=True))
 del raw
index=json.loads(original_bytes(descriptor['parentExportIndexPin']))
metadata=[descriptor['parentExportIndexPin'],index['manifestPin'],index['inventoryPin'],index['exportReceiptPin']]
started=time.monotonic()
for reference in metadata:original_bytes(reference,allow_empty=True)
metadata_seconds=time.monotonic()-started
started=time.monotonic()
for reference in index['contentPins'].values():pathlib.Path(reference['path']).lstat()
stat_seconds=time.monotonic()-started
assert mysql.query('SELECT @@server_uuid;').strip()==source['databaseUuid']
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,diagnosticOnly=True,frozenPointAcceptance=False,querySecondsLimit=120,queries=observed,parentMetadataBytes=sum(r['bytes'] for r in metadata),parentMetadataReadSeconds=metadata_seconds,parentContentFiles=len(index['contentPins']),parentContentStatSeconds=stat_seconds,noServicesChanged=True)))
'''
if __name__=='__main__':
 operation=json.loads((TASK/'incremental-2-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
 report=remote('172.30.30.57','OPERATION='+repr(operation)+'\n'+SCRIPT,240)
 write(TASK/'reference-stream-diagnosis.json',report);print(json.dumps(report))
