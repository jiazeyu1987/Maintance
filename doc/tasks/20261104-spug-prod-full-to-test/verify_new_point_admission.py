"""Verify that the authenticated live source admits this task's NEW point."""
import json
from repair_preflight import remote, TASK

SCRIPT=r'''
import datetime,json,pathlib,urllib.request
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
control=json.loads((root/'configuration/control-postboot-20261105.json').read_bytes())
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request('http://127.0.0.1:32657/selections',headers=headers),timeout=35) as response:
 status=response.status;document=json.load(response)
rows=[a for a in document['applications'] if a['sourceConfigRef']=='intruoyi-57-safe-20261024-v1']
assert status==200 and len(rows)==1
row=rows[0]
assert row.get('historyErrorCode') is None and OPERATION_LITERAL in row['recoveryPointRefs']
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'httpStatus':status,'sourceConfigRef':row['sourceConfigRef'],'newRecoveryPointRef':OPERATION_LITERAL,'newPointAdmitted':True,'historyErrorCode':row.get('historyErrorCode')}))
'''
if __name__=='__main__':
    operation=json.loads((TASK/'full-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote('172.30.30.57',SCRIPT.replace('OPERATION_LITERAL',repr(operation)),timeout=50)
    (TASK/'new-full-admission.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
