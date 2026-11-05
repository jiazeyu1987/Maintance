"""Read only the current operation's registered database identity and table count."""
import json
from repair_preflight import remote,TASK

SCRIPT=r'''
import json,pathlib,sys,datetime
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import ReadOnlyTarget
op=root/'recovery-operations'/OPERATION
c=json.loads((op/'configuration.json').read_bytes());r=json.loads((op/'request.json').read_bytes())
n=ReadOnlyTarget(c,r,op)
count=int(n.query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+n.config['database']+"';"))
identity=n.database_uuid()
assert identity==n.config['replacement']['databaseUuid']
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'operationId':OPERATION,'tableCount':count,'databaseUuid':identity,'businessWritesPerformed':False}))
'''

if __name__=='__main__':
 operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
 result=remote('172.30.30.58','OPERATION='+repr(operation)+'\n'+SCRIPT,75)
 (TASK/'restore-database-import-progress.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result))
