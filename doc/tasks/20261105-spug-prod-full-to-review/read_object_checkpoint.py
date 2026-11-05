"""Read the completed pinned physical object comparison without object names."""
import json
from preflight import COMMON, TASK, remote

SCRIPT=r'''
op=root/'recovery-operations'/OPERATION
reference=pin(op/'objects/result.json');result=read(reference);comparison=read(result['comparisonPin'])
need(result['originalVersionIdsPreserved'] is True,'OBJECT_IDENTITIES_CHANGED')
need(comparison['state']=='PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF' and comparison['exactVersionIdentityVerified'] is True,'OBJECT_COMPARISON_FAILED')
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',operationId=OPERATION,
 resultPin=reference,comparisonPin=result['comparisonPin'],wholeRestoreStillPending=True,
 objects={k:comparison[k] for k in ('exactVersionIdentityVerified','versionCount','deleteMarkerCount','totalVersionBytes','uniqueContentCount','versionHistorySha256')})))
'''

if __name__=='__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+'\nOPERATION='+repr(operation)+'\n'+SCRIPT,30)
    (TASK/'objects-phase-checkpoint.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
