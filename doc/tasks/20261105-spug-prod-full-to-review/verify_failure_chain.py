"""Read-only verification of immutable failures and each one-use clearance."""
import hashlib
import json
from preflight import COMMON, TASK, remote

CHECK=r'''
count=0;links=[]
for index,failure in enumerate(FAILURES):
 operation=failure['operationId'];claim=root/'replacement-state'/operation
 for reference in failure['evidencePins']:
  need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED');count+=1
 need(json.loads((claim/'replacement-result.json').read_bytes())['state']=='FAILED_RETAINED','FAILURE_STATE_CHANGED')
 consumed=json.loads((claim/'recovery-consumption.json').read_bytes())
 expected=FAILURES[index+1]['operationId'] if index+1<len(FAILURES) else CURRENT
 need(consumed['replacementOperationId']==expected,'WRONG_CONSUMPTION')
 need(consumed['clearancePin']==pin(claim/'recovery-clearance.json'),'CLEARANCE_CHANGED')
 clearance=read(consumed['clearancePin'])
 need(clearance['schemaVersion']==('RetainedReplacementRecovery/v1' if index==2 else 'RetainedReplacementRecovery/v2'),'WRONG_FAILURE_PHASE')
 links.append(dict(failedOperationId=operation,replacementOperationId=expected,clearanceSchema=clearance['schemaVersion'],consumptionPin=pin(claim/'recovery-consumption.json')))
need(count==203,'MISSING_ORIGINAL_FAILURES')
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
need(active.exists() and json.loads(active.read_bytes())['operationId']==CURRENT,'CURRENT_RESERVATION_MISMATCH')
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',operationId=CURRENT,protectedOriginalFailurePinsUnchanged=count,links=links,currentReservationBound=True)))
'''

if __name__=='__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    failures=[json.loads((TASK/name).read_text(encoding='utf-8')) for name in ('archive-budget-diagnosis.json','second-failure-diagnosis.json','third-failure-diagnosis.json')]
    local_count=0
    for name in ('failed-attempt-preservation.json','second-failed-attempt-preservation.json','third-failed-attempt-preservation.json'):
        for pin in json.loads((TASK/name).read_text(encoding='utf-8'))['pins']:
            path=(TASK/pin['path']).resolve()
            assert path.is_relative_to(TASK.resolve())
            raw=path.read_bytes()
            assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
            local_count+=1
    assert local_count==28
    script=COMMON.split('receiptpath=root/')[0]+'\nCURRENT='+repr(operation)+'\nFAILURES='+repr(failures)+'\n'+CHECK
    report=remote('172.30.30.59',script,40)
    report['originalLocalFailureFilesUnchanged']=local_count
    (TASK/'third-recovery-consumption.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
