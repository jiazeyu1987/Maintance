"""Final read-only preservation and control checks after approved original starts."""
import json
from install_review_control import SCRIPT as COMMON
from resume_readonly import TASK,remote

SCRIPT=r'''
from types import SimpleNamespace
import urllib.request
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['ownerConfigurationPin']==EXPECTED_OWNER_PIN and receipt['controlConfigurationPin']==EXPECTED_CONTROL_PIN,'CONTROL_CHANGED')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_target import verify_runtime
from recovery_replacement_storage import verify_storage
from recovery_control_smallapp_native import Native
from formal_data_evidence import validate_limits
need(Native(receipt['controlConfigurationPin']).configuration()==control,'CONTROL_INVALID')
validate_limits(owner['dataLimits'])
target=owner['targets'][receipt['targetConfigRef']]
need(business()==EXPECTED_BUSINESS,'BUSINESS_CHANGED_AFTER_AUTHORIZED_STARTS')
rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
need(all(row['State']['Running'] for row in rows.values()),'ORIGINAL_SERVICE_STOPPED')
health={role:row['State'].get('Health',{}).get('Status') for role,row in rows.items()}
need(all(health[role]=='healthy' for role in ('backend','frontend','minio')),'ORIGINAL_HEALTH_NOT_READY')
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},snapshots={},
 source=owner['sources'][target['sourceConfigRef']],root=root/'recovery-operations',
 inspect=lambda identity:next(row for row in rows.values() if row['Id']==identity),docker=lambda args:run(['docker',*args]))
verify_runtime(native,states=False);verify_storage(native,target['replacement'],rows)
engine=pathlib.Path(owner['formalModuleDirectory']).parent;version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'PACKAGE_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
need(not [p for n in ('ledger','operations','recovery-operations','replacement-state') for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'RESTORE_RECORDS_PRESENT')
need(not [p for p in root.rglob('*claim*') if p.is_file()],'CLAIM_PRESENT')
unit=EXPECTED_ARCHIVE_UNIT;archive=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
mount=[line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(archive)]
need(len(mount)==1 and 'ro' in mount[0].split()[5].split(',') and ' - cifs //172.30.30.4/IT共享 ' in mount[0],'CANONICAL_ARCHIVE_CHANGED')
sourceunit=run(['systemd-escape','--path','--suffix=mount','/mnt/intruoyi-backup-nas']).decode().strip()
sourceproperties=run(['systemctl','show',sourceunit,'--property=ActiveState,UnitFileState,FragmentPath,SourcePath,Transient']).decode().strip()
for service in (receipt['service'],unit):
 need(run(['systemctl','is-active',service]).strip()==b'active' and run(['systemctl','is-enabled',service]).strip()==b'enabled','CONTROL_OR_MOUNT_NOT_PERSISTENT')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://'+next(s['ip'] for s in target['services'] if s['role']=='backend')+':48081/actuator/health',timeout=10) as response:need(json.load(response)['status']=='UP','BACKEND_NOT_UP')
with opener.open('http://172.30.30.59:38081',timeout=10) as response:need(response.status==200,'FRONTEND_NOT_READY')
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS',
 'host':'172.30.30.59','ownerConfigurationPin':receipt['ownerConfigurationPin'],'controlConfigurationPin':receipt['controlConfigurationPin'],
 'originalServices':{r:{'id':s['Id'],'pid':s['State']['Pid'],'startedAt':s['State']['StartedAt'],'health':health[r]} for r,s in rows.items()},
 'allOriginalConfigurationsAndImagesPreserved':True,'otherBusinessIdsPidsStartTimesPreserved':True,
 'strictNetworkAndStorageVerification':True,'packageFileCount':len(version['files']),'packageFilesMatch':True,
 'controlAndArchiveActiveEnabled':True,'archiveMode':'ro','archiveSourceMountProperties':sourceproperties,
 'hostRebootTested':False,'originalBusinessRestartPolicyChanged':False,
 'existingCifsSourceHasPersistentUnit':'FragmentPath=\n' not in sourceproperties and 'FragmentPath=' in sourceproperties,
 'backendHealth':'UP','frontendHTTP':200,'operationCount':0,'claimCount':0,'activeRestore':False,
 'restoreExecuted':False,'businessTestMutations':0,'releaseWorktreeCreated':False,'threeDestinationGoalComplete':False}))
'''

if __name__=='__main__':
 business=json.loads((TASK/'target-review-original-start-business.json').read_text(encoding='utf-8'))
 choice=json.loads((TASK/'review-authorized-browser-choice.json').read_text(encoding='utf-8'))
 assert business['status']=='PASS' and business['realLogin'] and business['businessMutations']==0
 assert business['version']=='2026-11-03-12-15-42' and business['businessPage']['visibleRows']>0
 assert choice['status']=='PASS' and choice['realLogin'] and not choice['restoreSubmitted']
 assert choice['writes']==['/api/account/login/'] and not any(choice[k] for k in ('blocked','apiErrors','pageErrors','httpFailures'))
 assert 'smallapp-73cd541a95d84d6a86f9d693e4053c75' in choice['reviewConfirmation'] and 'intruoyi-main-59-safe-restore-20261104-v1' in choice['reviewConfirmation']
 attestation=json.loads((TASK/'review-bridge-attestation.json').read_text(encoding='utf-8'))
 values={'EXPECTED_OWNER_PIN':attestation['ownerConfigurationPin'],'EXPECTED_CONTROL_PIN':attestation['controlConfigurationPin'],
  'EXPECTED_BUSINESS':json.loads((TASK/'review-authorized-verify.json').read_text(encoding='utf-8'))['business'],
  'EXPECTED_ARCHIVE_UNIT':json.loads((TASK/'review-authorized-mount.json').read_text(encoding='utf-8'))['archiveUnit']}
 result=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,timeout=80)
 result.update(realBusinessLoginAndPage='PASS',realSpugChoiceConfirmCancel='PASS',spugRestorePostCount=0)
 (TASK/'review-authorized-final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
