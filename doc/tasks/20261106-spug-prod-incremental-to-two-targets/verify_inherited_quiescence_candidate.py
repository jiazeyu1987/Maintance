"""Read actual consumed 368 -> 369 custody; never authorize or mutate."""
import json
from common import TASK,remote,write
SCRIPT=r'''
import datetime,hashlib,json,pathlib,sys,types
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
def read(p):return json.loads(pathlib.Path(p).read_bytes())
receipt=read(root/'target-installation.json');control=read(receipt['controlConfigurationPin']['path'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
module=types.ModuleType('recovery_retained_retry');sys.modules['recovery_retained_retry']=module
exec(compile(CODE,'candidate_retained_retry','exec'),module.__dict__)
op=root/'recovery-operations/smallapp-b4f35606e4854516960050a76473038b'
configuration=read(op/'configuration.json');request=read(op/'request.json');target=configuration['targets'][request['targetConfigRef']]
from recovery_engine import pin,pinned_json
refs={k:pin(op/name) for k,name in [('requestPin','request.json'),('resultPin','worker-result.json'),('exitPin','child-exit.json')]}
module.verify_no_mutation(configuration,request,op,refs,pin(op/'resource-no-mutation-release.json'))
previous_ref,previous=module.inherited_quiescence(target,request)
assert previous['operationId']=='smallapp-c21bb7ce9f5b4668b850c37a80964786'
observed=module.observe(configuration,request,op,885,False)
module.compare_quiescence(observed,pinned_json(previous['observationPin']))
if 'schedulerCustodyPin' in previous:
 from recovery_main_target import mysql_scheduler
 native=module.ReadOnlyTarget(configuration,request,op);native.original=request
 mysql_scheduler(native,query=lambda sql,mutation=False:(native.query(sql)+'\n').encode()).preflight()
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceSha256=hashlib.sha256(CODE.encode()).hexdigest(),
 operationId=request['operationId'],previousOperationId=previous['operationId'],inheritedQuiescencePin=previous_ref,
 previousObservationPin=previous['observationPin'],schedulerCustodyPin=previous.get('schedulerCustodyPin'),
 tableCount=observed['tableCount'],services=observed['services'],serverWrites=False,clearanceIssued=False)))
'''
if __name__=='__main__':
 code=(TASK.parents[2]/'ops/recovery/recovery_retained_retry.py').read_text(encoding='utf8')
 result=remote('172.30.30.58','CODE='+repr(code)+'\n'+SCRIPT,90)
 write(TASK/'inherited-quiescence-candidate-58.json',result);print(json.dumps(result))
