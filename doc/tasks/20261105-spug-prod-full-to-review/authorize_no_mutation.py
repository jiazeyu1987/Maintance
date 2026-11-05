"""Invoke the shipped explicit CLI; never dispatch a restore or remove history."""
import hashlib
import json
from preflight import COMMON,TASK,remote

CHECK=r'''
import urllib.request
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['ownerConfigurationPin']==INSTALL['ownerConfigurationPin'] and receipt['controlConfigurationPin']==INSTALL['controlConfigurationPin'],'CONTROL_DRIFT')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
before=business();need(before==BEFORE['business'],'BUSINESS_DRIFT')
for reference in FAILURE['evidencePins']:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
operation=FAILURE['operationId'];oproot=root/'recovery-operations'/operation
env=dict(os.environ,**control['environment'])
command=[control['pythonPin']['path'],'-B',str(pathlib.Path(owner['formalModuleDirectory']).parent/'common/recovery_retained_retry.py'),
 '--operation-root',str(oproot),'--authorization',AUTHORIZATION,'--expected-table-count','885','--authorize-no-mutation-replacement']
result=subprocess.run(command,env=env,capture_output=True,timeout=60)
need(result.returncode==0,'EXPLICIT_NO_MUTATION_AUTHORIZATION_FAILED')
report=json.loads(result.stdout)
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import validate_clearance
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
target=receipt['targetConfigRef'];claim=root/'replacement-state'/operation
clearance=validate_clearance(owner['targets'][target],claim)
need(clearance['failurePhase']=='BEFORE_MUTATION' and clearance['recoveryPointRef']==POINT and clearance['sourceConfigRef']==SOURCE,'WRONG_CLEARANCE')
need(business()==before,'BUSINESS_RUNTIME_CHANGED')
for reference in FAILURE['evidencePins']:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request('http://127.0.0.1:33659/selections?targetConfigRef='+target,headers=headers),timeout=35) as response:document=json.load(response)
need(target in document['applications'][0]['freshTargetConfigRefs'],'TARGET_NOT_ADMITTED_AFTER_CLEARANCE')
native=Native(receipt['controlConfigurationPin']);request={'sourceConfigRef':SOURCE,'recoveryPointRef':POINT}
need(POINT in source_admits(native,owner['sources'][SOURCE],request),'SOURCE_POINT_NOT_ADMITTED')
resolved,binding=bind_archive_chain(owner['sources'][SOURCE],request)
need(binding['pointPin']==BEFORE['pointPin'],'FULL_POINT_CHANGED')
pid=int(run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip().split('=',1)[1])
limit=next(line for line in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if line.startswith('Max open files'))
need(limit.split()[3:5]==['65536','65536'],'ARCHIVE_BUDGET_CHANGED')
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','failedOperationId':operation,'report':report,'clearanceSchema':clearance['schemaVersion'],'failurePhase':clearance['failurePhase'],'authorizationPlanSha256':PLAN_SHA,'targetConfigRef':target,'sourceConfigRef':SOURCE,'recoveryPointRef':POINT,'protectedOriginalFailurePinsUnchanged':len(FAILURE['evidencePins']),'allBusinessIdsPidsStartTimesConfigurationUnchanged':True,'freshTargetAdmitted':True,'sourcePointAdmitted':True,'pointPin':binding['pointPin'],'archiveEvidencePinsChecked':len(binding['evidencePins']),'liveLimits':limit,'activeReservation':False,'restoreDispatched':False}
print(json.dumps(out))
'''

if __name__=='__main__':
    from preflight import SOURCE,POINT
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--failure',default='archive-budget-diagnosis.json');args=parser.parse_args()
    sha=hashlib.sha256((TASK/'pre-mutation-recovery-plan.md').read_bytes()).hexdigest()
    authorization='User explicitly requested actual Spug restore of the production FULL to original 172.30.30.59 and repair of encountered failures. Same source, point and registered MAIN target only. Task 20261105-spug-prod-full-to-review; approved-scope plan sha256:'+sha
    values={'INSTALL':json.loads((TASK/'retry-control-installation.json').read_text(encoding='utf-8')),
            'BEFORE':json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8')),
            'FAILURE':json.loads((TASK/args.failure).read_text(encoding='utf-8')),
            'SOURCE':SOURCE,'POINT':POINT,'AUTHORIZATION':authorization,'PLAN_SHA':sha}
    script=COMMON.split('receiptpath=root/')[0]+'\n'+'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+CHECK
    out=remote('172.30.30.59',script,150)
    (TASK/'no-mutation-clearance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out))
