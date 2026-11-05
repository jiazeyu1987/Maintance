"""Preserve the failed original and compare registered versus stopped networks."""
import json
from preflight import COMMON, PRIVATE, TASK, remote
from diagnose_archive_budget import CHECK

EXTRA = r'''
from recovery_main_target import network_attachments
target=owner['targets'][request['targetConfigRef']]
rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
attachments={role:network_attachments(row) for role,row in rows.items()}
differences={role:dict(expected=target['mainApplication']['networkAttachments'][role],observed=value,running=rows[role]['State']['Running']) for role,value in attachments.items() if value!=target['mainApplication']['networkAttachments'][role]}
observed_networks={n['name']:json.loads(run(['docker','network','inspect',n['id']]))[0] for n in target['mainApplication']['networks']}
current=business()
protected=[p for p in files if p['path']!='/var/lib/spug-restore-resources/active.json']
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,service=unit,liveLimits=limit,idleControl=True,evidencePins=protected,documents=documents,database=db,business=current,activeReservation=active.exists(),activePointerPin=pin(active) if active.exists() else None,networkDifferences=differences,observedNetworks=observed_networks)))
'''

if __name__ == '__main__':
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    script=COMMON.split('receiptpath=root/')[0]+'\nOPERATION='+repr(operation)+'\n'+CHECK.rsplit('\nprint(',1)[0]+'\n'+EXTRA
    result=remote('172.30.30.59',script,90)
    (PRIVATE/'third-failure.private.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    before=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))['business']
    original_ids={s['id'] for s in json.loads((PRIVATE/'original-runtime-baseline.private.json').read_text(encoding='utf-8'))['documents']['owner']['targets']['intruoyi-main-59-safe-restore-20261104-v1']['services']}
    report={k:v for k,v in result.items() if k not in ('business','documents','observedNetworks')}
    report['otherBusinessRuntimePreserved']=all(result['business'][k]==v for k,v in before.items() if k not in original_ids)
    report['allContainerConfigurationsPreserved']=all(result['business'][k]['configurationSha256']==v['configurationSha256'] for k,v in before.items())
    report['originalResults']={name:doc for name,doc in result['documents'].items() if name.endswith(('result.json','child-exit.json','replacement-result.json','replacement-prepared.json')) and 'invocation' not in name}
    (TASK/'third-failure-diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('evidencePins','originalResults')},ensure_ascii=False))
