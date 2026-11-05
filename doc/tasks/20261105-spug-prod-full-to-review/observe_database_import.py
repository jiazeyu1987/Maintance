"""Observe only original UUID/table count and MySQL process IO during import."""
import json
from preflight import TASK, ROOT, remote

SCRIPT=r'''
import datetime,json,pathlib,subprocess,sys
root=pathlib.Path(ROOT)
receipt=json.loads((root/'target-installation.json').read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import ReadOnlyTarget
op=root/'recovery-operations'/OPERATION
configuration=json.loads((op/'configuration.json').read_bytes());request=json.loads((op/'request.json').read_bytes())
target=ReadOnlyTarget(configuration,request,op)
count=int(target.query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+target.config['database']+"';"))
identity=target.database_uuid();assert identity==target.config['replacement']['databaseUuid']
mysql=next(service for service in target.config['services'] if service['role']=='mysql')
row=json.loads(subprocess.check_output(['docker','inspect',mysql['id']],timeout=10))[0]
assert row['Id']==mysql['id'] and row['Image']==mysql['imageId'] and row['State']['Running']
pid=row['State']['Pid'];proc=pathlib.Path('/proc')/str(pid)
numbers={line.split(':')[0]:int(line.split(':')[1]) for line in (proc/'io').read_text().splitlines()}
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,
 tableCount=count,databaseUuid=identity,mysqlPid=pid,mysqlIO=numbers,businessWritesPerformed=False)))
'''

if __name__=='__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    result=remote('172.30.30.59','ROOT='+repr(ROOT)+'\nOPERATION='+repr(operation)+'\n'+SCRIPT,35)
    (TASK/'restore-database-import-progress.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
