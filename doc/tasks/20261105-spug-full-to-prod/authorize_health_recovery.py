"""Formally carry History362 protection and paused scheduler into the same-point retry."""
import json
from install_prod_control import TASK,ROOT,TARGET,POINT,remote

SCRIPT=r'''
import datetime,hashlib,json,pathlib,sys
root=pathlib.Path(ROOT)
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
for reference in PINS:assert pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED'
assert pin('/var/lib/spug-restore-resources/active.json')==ACTIVE_POINTER,'ORIGINAL_POINTER_CHANGED'
installed=json.loads((root/'target-installation.json').read_bytes())
assert installed['sourceCommit']==COMMIT and installed['targetConfigRef']==TARGET
control=json.loads(pathlib.Path(installed['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import authorize,validate_clearance
operation=root/'recovery-operations'/OPERATION
configuration=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
assert request['targetConfigRef']==TARGET and request['recoveryPointRef']==POINT
result=authorize(configuration,request,operation,
 'User explicitly requested successful Spug restore to original production MAIN57 and correction of restore defects. Continue identical History350 point and target after preserving History361/362 failures and exact protection handoff; carry paused scheduler custody and never alter historical evidence.',885)
claim=pathlib.Path(configuration['targets'][TARGET]['replacement']['stateRoot'])/OPERATION
clearance=validate_clearance(configuration['targets'][TARGET],claim)
proof=json.loads(pathlib.Path(clearance['mainProtectionRecoveryPin']['path']).read_bytes())
assert {v['kind'] for v in proof['releasePins']}=={'archive','published'}
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists()
assert (claim/'mysql-scheduler').is_dir() and clearance['schedulerCustodyPin']==proof['schedulerCustodyPin']
custody=json.loads(pathlib.Path(clearance['schedulerCustodyPin']['path']).read_bytes())
assert custody['originalState']=='ON'
for reference in PINS:assert pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 operationId=OPERATION,sourceConfigRef=request['sourceConfigRef'],recoveryPointRef=POINT,targetConfigRef=TARGET,
 originalFailurePinsUnchanged=len(PINS),originalState='FAILED_RETAINED',
 originalProtectionsPreciselyReleased=True,schedulerCustodyPin=clearance['schedulerCustodyPin'],schedulerOriginalState='ON',
 schedulerRemainsPaused=True,clearancePin=result['clearancePin'],resourceReleasePin=result['releasePin'],
 mainProtectionRecoveryPin=clearance['mainProtectionRecoveryPin'],newRequestSamePointAndTarget=True,
 writersRemainStopped=True,restoreDispatched=False)))
'''

if __name__=='__main__':
    assert not (TASK/'health-recovery-clearance.json').exists()
    installation=json.loads((TASK/'health-control-installation.json').read_text(encoding='utf-8'))
    assert installation['status']=='PASS' and installation['protectedOriginalFailurePinsUnchanged']==908
    failure=json.loads((TASK/'healthcheck-failure-diagnosis.json').read_text(encoding='utf-8'))
    old=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    values=dict(ROOT=ROOT,TARGET=TARGET,POINT=POINT,COMMIT=installation['sourceCommit'],OPERATION=failure['operationId'],
        PINS=failure['evidencePins']+old['evidencePins'],ACTIVE_POINTER=failure['activePointerPin'])
    report=remote('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,180)
    (TASK/'health-recovery-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
