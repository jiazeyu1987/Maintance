"""Independently verify current MAIN scheduler custody without changing it."""
import json
from install_prod_control import TASK, ROOT, TARGET, remote

SCRIPT=r'''
import datetime,hashlib,json,pathlib,sys
root=pathlib.Path(ROOT)
receipt=json.loads((root/'target-installation.json').read_bytes())
assert receipt['sourceCommit']==COMMIT and receipt['targetConfigRef']==TARGET
def read(reference):
 raw=pathlib.Path(reference['path']).read_bytes()
 assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
 return json.loads(raw)
control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import ReadOnlyTarget
from recovery_mysql_scheduler import MainMysqlScheduler,STATE_SQL,WORKERS_SQL
from recovery_engine import pin
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes())
request=json.loads((operation/'request.json').read_bytes())
assert request['operationId']==OPERATION and request['targetConfigRef']==TARGET
target=configuration['targets'][TARGET]
journal=pathlib.Path(target['replacement']['stateRoot'])/OPERATION/'mysql-scheduler'
assert (journal/'active.json').is_file() and not (journal/'released.json').exists(),'PAUSED_PHASE_REQUIRED'
native=ReadOnlyTarget(configuration,request,operation)
def query(statement,**kwargs):
 assert not kwargs.get('mutation'),'READ_ONLY_CHECK_REQUIRED'
 return (native.query(statement)+'\n').encode('utf-8')
intent=MainMysqlScheduler(target,OPERATION,journal,query).verify()
assert intent['originalState']=='ON' and intent['pausedState']=='OFF'
assert native.query(STATE_SQL).split('\t')==[target['replacement']['databaseUuid'],'0','0','OFF']
assert native.query(WORKERS_SQL)=='0'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 operationId=OPERATION,originalState='ON',currentState='OFF',runningSchedulerThreads=0,
 originalDatabaseIdentityVerified=True,exclusiveDatabaseScopeVerified=True,
 intentPin=pin(journal/'intent.json'),activePin=pin(journal/'active.json'),databaseMutations=0)))
'''

if __name__=='__main__':
    request=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']
    installation=json.loads((TASK/'health-control-installation.json').read_text(encoding='utf-8'))
    assert installation['status']=='PASS'
    values=dict(ROOT=ROOT,TARGET=TARGET,COMMIT=installation['sourceCommit'],OPERATION=request['operationId'])
    script='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT
    compile(script,'remote-scheduler-pause','exec')
    report=remote(script,50)
    output=TASK/('scheduler-paused-runtime-'+request['operationId']+'.json')
    assert not output.exists(),'ORIGINAL_PAUSE_RECEIPT_MUST_BE_PRESERVED'
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
