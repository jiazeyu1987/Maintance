"""Exercise the forward DDL on task-owned MySQL, preserving existing synthetic rows."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

TASK=Path(__file__).parent
SQL=Path('C:/SpugHandoff/schema-src-20261101/IntRuoyiBackend/sql/mysql')
NAME='int-schema-consistency-20261101'
IMAGE='mysql:8.0.39'
env=dict(os.environ,MYSQL_ROOT_PASSWORD=secrets.token_urlsafe(32))

def run(args,data=None,timeout=90):
    result=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=timeout)
    if result.returncode:
        raise RuntimeError('Task-owned MySQL check failed: '+args[0]+' exit='+str(result.returncode))
    return result.stdout.decode('utf-8').rstrip('\r\n')

def sql(query,database=None):
    script='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names'
    if database:
        assert database in ('schema_test','schema_prod','schema_backup')
        script+=' '+database
    return run(['docker','exec','-i',NAME,'sh','-c',script],query.encode('utf-8'))

existing=subprocess.run(['docker','container','inspect',NAME],capture_output=True)
assert existing.returncode!=0, 'Task container already exists; inspect before reuse'
created=run(['docker','run','-d','--name',NAME,'--label','codex.task=20261101-three-server-schema-consistency',
    '--network','none','--memory','1536m','--tmpfs','/var/lib/mysql:rw,size=512m',
    '-e','MYSQL_ROOT_PASSWORD',IMAGE])
deadline=time.monotonic()+90
while True:
    ready=subprocess.run(['docker','exec',NAME,'sh','-c','export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; mysql -uroot -Nse "SELECT 1"'],capture_output=True)
    if ready.returncode==0:
        break
    if time.monotonic()>deadline:
        raise RuntimeError('Task MySQL readiness timed out; owned container retained')
    time.sleep(2)

queries_node=next(n for n in ast.parse((TASK/'collect-schema.py').read_text('utf-8')).body
                  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='queries' for t in n.targets))
queries=ast.literal_eval(queries_node.value)
baseline=json.loads((TASK/'schema-before.json').read_text('utf-8'))['environments']['test']['schema']
names={'dcc_controlled_file_source_governance_batch','dcc_controlled_file_source_governance_item','dcc_controlled_file_source_global_claim'}
expected={key:[row for row in rows if row.split('\t')[0] in names] for key,rows in baseline.items()}
for db in ('schema_test','schema_prod','schema_backup'):
    sql('CREATE DATABASE '+db+' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
old=(SQL/'20260905_dcc_source_governance.sql').read_text('utf-8')
tenant=(SQL/'20260922_dcc_source_governance_batch_tenant_id.sql').read_text('utf-8')
new=(SQL/'20261101_dcc_source_governance_all_environments.sql').read_text('utf-8')
sql(old+'\n'+tenant,'schema_test')
sql("INSERT INTO dcc_controlled_file_source_governance_batch(task_key,tenant_scope_json,tenant_scope_sha256,snapshot_max_controlled_file_id,rule_version,schema_version,manifest_sha256,request_sha256,batch_status) VALUES('schema-contract-owned','[]',REPEAT('a',64),0,'test','test',REPEAT('b',64),REPEAT('c',64),'PREPARED');",'schema_test')
marker_before=sql('SELECT * FROM dcc_controlled_file_source_governance_batch;','schema_test')
results={}
for db in ('schema_test','schema_prod','schema_backup'):
    sql(new,db)
    first={key:sql(query,db).splitlines() for key,query in queries.items()}
    assert first==expected, 'Actual MySQL DDL differs from the approved existing test table schema: '+db
    sql(new,db)
    repeated={key:sql(query,db).splitlines() for key,query in queries.items()}
    assert repeated==first, 'Repeated forward migration changed schema: '+db
    results[db]=dict(tableCount=len(first['tables']),matchesExistingTest=True,repeatedMigrationStable=True,
                    structureSha256=hashlib.sha256(json.dumps(first,sort_keys=True).encode()).hexdigest())
marker_after=sql('SELECT * FROM dcc_controlled_file_source_governance_batch;','schema_test')
assert marker_after==marker_before, 'Forward migration changed an existing task-owned row'
info=json.loads(run(['docker','inspect',NAME]))[0]
assert info['Id']==created and info['Config']['Labels']['codex.task']=='20261101-three-server-schema-consistency'
run(['docker','rm','-f','-v',NAME])
report=dict(status='PASS',time=datetime.now(timezone.utc).isoformat(),mysqlImage=IMAGE,
            existingTaskOwnedRowPreserved=True,results=results,taskContainerRemoved=True,remoteMutations=False)
(TASK/'real-mysql-migration-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
