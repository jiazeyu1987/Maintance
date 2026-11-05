"""Append the formal post-mutation clearance; never dispatch data restoration."""
import hashlib
import json
from preflight import COMMON, PRIVATE, SOURCE, POINT, TASK, remote

CHECK=r'''
import urllib.request
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['ownerConfigurationPin']==INSTALL['ownerConfigurationPin'] and receipt['controlConfigurationPin']==INSTALL['controlConfigurationPin'],'CONTROL_DRIFT')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
need(business()==BEFORE_BUSINESS,'BUSINESS_DRIFT')
for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
operation=FAILURE['operationId'];op=root/'recovery-operations'/operation
need(pin('/var/lib/spug-restore-resources/active.json')==FAILURE['activePointerPin'],'RESERVATION_CHANGED')
env=dict(os.environ,**control['environment'])
command=[control['pythonPin']['path'],'-B',str(pathlib.Path(owner['formalModuleDirectory']).parent/'common/recovery_retained_retry.py'),
 '--operation-root',str(op),'--authorization',AUTHORIZATION,'--expected-table-count','0','--authorize-retained-replacement']
result=subprocess.run(command,env=env,capture_output=True,timeout=65)
need(result.returncode==0,'EXPLICIT_RETAINED_AUTHORIZATION_FAILED')
report=json.loads(result.stdout)
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import validate_clearance
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
target=receipt['targetConfigRef'];claim=root/'replacement-state'/operation
clearance=validate_clearance(owner['targets'][target],claim)
need(clearance['schemaVersion']=='RetainedReplacementRecovery/v1' and clearance['sourceConfigRef']==SOURCE and clearance['recoveryPointRef']==POINT,'WRONG_CLEARANCE')
need(business()==BEFORE_BUSINESS,'BUSINESS_RUNTIME_CHANGED')
for reference in PINS:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request('http://127.0.0.1:33659/selections?targetConfigRef='+target,headers=headers),timeout=35) as response:document=json.load(response)
need(target in document['applications'][0]['freshTargetConfigRefs'],'TARGET_NOT_ADMITTED_AFTER_CLEARANCE')
native=Native(receipt['controlConfigurationPin']);request={'sourceConfigRef':SOURCE,'recoveryPointRef':POINT}
need(POINT in source_admits(native,owner['sources'][SOURCE],request),'SOURCE_POINT_NOT_ADMITTED')
resolved,binding=bind_archive_chain(owner['sources'][SOURCE],request)
need(binding['pointPin']==POINT_PIN,'FULL_POINT_CHANGED')
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',failedOperationId=operation,report=report,clearanceSchema=clearance['schemaVersion'],failurePhase='AFTER_MUTATION',authorizationPlanSha256=PLAN_SHA,targetConfigRef=target,sourceConfigRef=SOURCE,recoveryPointRef=POINT,protectedOriginalFailurePinsUnchanged=len(PINS),allBusinessIdsPidsStartTimesConfigurationUnchanged=True,freshTargetAdmitted=True,sourcePointAdmitted=True,pointPin=binding['pointPin'],archiveEvidencePinsChecked=len(binding['evidencePins']),activeReservation=False,restoreDispatched=False)))
'''

if __name__=='__main__':
    plan=hashlib.sha256((TASK/'dynamic-network-recovery-plan.md').read_bytes()).hexdigest()
    baseline=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    failure=json.loads((TASK/'third-failure-diagnosis.json').read_text(encoding='utf-8'))
    pins=[]
    for name in ('archive-budget-diagnosis.json','second-failure-diagnosis.json','third-failure-diagnosis.json'):
        pins+=json.loads((TASK/name).read_text(encoding='utf-8'))['evidencePins']
    values=dict(INSTALL=json.loads((TASK/'retry-control-installation.json').read_text(encoding='utf-8')),
        BEFORE_BUSINESS=json.loads((PRIVATE/'third-failure.private.json').read_text(encoding='utf-8'))['business'],
        FAILURE=failure,PINS=pins,SOURCE=SOURCE,POINT=POINT,POINT_PIN=baseline['pointPin'],PLAN_SHA=plan,
        AUTHORIZATION='User explicitly authorized actual Spug production FULL restore to original 172.30.30.59 and repair of failures. Continue same source, point and target after terminated post-mutation History358. Approved-scope plan sha256:'+plan)
    script=COMMON.split('receiptpath=root/')[0]+'\n'+'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+CHECK
    out=remote('172.30.30.59',script,160)
    (TASK/'retained-clearance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out))
