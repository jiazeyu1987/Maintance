"""Check original service definitions, other business custody and stable controls."""
import json
from preflight import COMMON, PRIVATE, TASK, remote

CHECK = r'''
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['ownerConfigurationPin']==INSTALL['ownerConfigurationPin'] and receipt['controlConfigurationPin']==INSTALL['controlConfigurationPin'],'CONTROL_CHANGED')
owner=read(receipt['ownerConfigurationPin']);read(receipt['controlConfigurationPin'])
oldowner=read(BEFORE['ownerConfigurationPin'])
need({k:v for k,v in owner.items() if k!='formalModuleDirectory'}=={k:v for k,v in oldowner.items() if k!='formalModuleDirectory'},'OWNER_CONTRACT_CHANGED')
current=business();before=BEFORE['business']
need(set(current)==set(before),'CONTAINER_SET_CHANGED')
targetids={s['id'] for s in owner['targets'][receipt['targetConfigRef']]['services']}
need(len(targetids)==5,'WRONG_TARGET_SERVICE_COUNT')
for identity,old in before.items():
 now=current[identity]
 need(now['configurationSha256']==old['configurationSha256'] and now['image']==old['image'],'ORIGINAL_CONFIGURATION_OR_IMAGE_CHANGED')
 if identity not in targetids:need(now==old,'OTHER_BUSINESS_RUNTIME_CHANGED')
need(all(current[cid]['running'] for cid in targetids),'RESTORED_SERVICE_STOPPED')
control=read(receipt['controlConfigurationPin'])
engine=pathlib.Path(owner['formalModuleDirectory']).parent
version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'CONTROL_PACKAGE_CHANGED')
need(run(['systemctl','is-active',receipt['service']]).strip()==b'active' and run(['systemctl','is-enabled',receipt['service']]).strip()==b'enabled','CONTROL_NOT_STABLE')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION_REMAINS')
archive=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
mount=[line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(archive)]
need(len(mount)==1 and 'ro' in mount[0].split()[5].split(','),'READONLY_ARCHIVE_CHANGED')
need(pin(BEFORE['pointPin']['path'])==BEFORE['pointPin'],'FULL_POINT_CHANGED')
operationfiles=[p.name for p in (root/'ledger').iterdir() if p.is_dir()]
need(set(operationfiles)=={f['operationId'] for f in FAILURES}|{OPERATION},'UNEXPECTED_RESTORE_OPERATION')
for index,failure in enumerate(FAILURES):
 for reference in failure['evidencePins']:need(pin(reference['path'])==reference,'ORIGINAL_FAILURE_CHANGED')
 clearance=root/'replacement-state'/failure['operationId']
 consumed=json.loads((clearance/'recovery-consumption.json').read_bytes())
 expected=FAILURES[index+1]['operationId'] if index+1<len(FAILURES) else OPERATION
 need(consumed['replacementOperationId']==expected and consumed['clearancePin']==pin(clearance/'recovery-clearance.json'),'WRONG_RECOVERY_CONSUMPTION')
 need(json.loads((clearance/'replacement-result.json').read_bytes())['state']=='FAILED_RETAINED','ORIGINAL_FAILURE_CHANGED')
pid=int(run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip().split('=',1)[1])
limit=next(line for line in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if line.startswith('Max open files'))
need(limit.split()[3:5]==['65536','65536'],'ARCHIVE_BUDGET_CHANGED')
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','operationId':OPERATION,'originalFiveContainersAndImagesPreserved':True,'allOriginalConfigurationDigestsPreserved':True,'otherBusinessRuntimePreserved':True,'otherBusinessContainerCount':len(current)-5,'controlActiveEnabled':True,'controlPackageFileCount':len(version['files']),'controlConfigurationPinsUnchanged':True,'stableRuntimePaths':not any('worktrees' in p for p in control['environment']['PYTHONPATH'].split(':')),'archiveReadOnly':True,'fullPointPinUnchanged':True,'hostReservationReleased':True,'restoreOperationCount':len(operationfiles)}))
'''

if __name__ == '__main__':
    before=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    operation=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    install=json.loads((TASK/'retry-control-installation.json').read_text(encoding='utf-8'))
    failures=[json.loads((TASK/name).read_text(encoding='utf-8')) for name in ('archive-budget-diagnosis.json','second-failure-diagnosis.json','third-failure-diagnosis.json')]
    script=COMMON.split('receiptpath=root/')[0]+'\nBEFORE='+repr(before)+'\nOPERATION='+repr(operation)+'\nINSTALL='+repr(install)+'\nFAILURES='+repr(failures)+'\n'+CHECK
    out=remote('172.30.30.59',script,70)
    (TASK/'preservation-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out))
