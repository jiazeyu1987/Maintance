"""Read the pinned completed database comparison without business content."""
import json
from preflight import COMMON, TASK, remote

SCRIPT=r'''
operation=OPERATION;op=root/'recovery-operations'/operation
reference=pin(op/'database-000/result.json');result=read(reference);comparison=read(result['comparisonPin'])
need(result['fullSchemaDataEquivalenceVerified'] is True and comparison['fullSchemaDataEquivalenceVerified'] is True,'DATABASE_COMPARISON_FAILED')
need(comparison['state']=='SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF','DATABASE_STATE_INVALID')
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',operationId=operation,
 databaseUuid=result['databaseUuid'],tableCount=len(comparison['tables']),totalRows=sum(v['rows'] for v in comparison['tables'].values()),
 fullSchemaDataEquivalenceVerified=True,schemaSha256=comparison['schemaSha256'],resultPin=reference,comparisonPin=result['comparisonPin'],
 wholeRestoreStillPending=True)))
'''

if __name__=='__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+'\nOPERATION='+repr(operation)+'\n'+SCRIPT,30)
    (TASK/'database-phase-checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
