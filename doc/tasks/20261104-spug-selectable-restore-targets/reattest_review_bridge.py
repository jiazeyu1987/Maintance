"""Publish only the proven reboot bridge ID/frontend DHCP address differences."""
import json
from install_review_control import SCRIPT as COMMON
from resume_readonly import TASK,PRIVATE,remote

SCRIPT=r'''
receiptpath=root/'target-installation.json'
need(pin(receiptpath)==EXPECTED_RECEIPT_PIN,'RECEIPT_CHANGED')
receipt=json.loads(receiptpath.read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
need(receipt['ownerConfigurationPin']==EXPECTED_OWNER_PIN and receipt['controlConfigurationPin']==EXPECTED_CONTROL_PIN,'CONTROL_CHANGED')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
from recovery_main_target import network_attachments,network_configuration,verify_runtime
from recovery_control_smallapp_native import Native
from types import SimpleNamespace
target=owner['targets'][receipt['targetConfigRef']]
before=business();need(before==EXPECTED_BUSINESS,'BUSINESS_CHANGED')
fd=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
 need(not [p for n in ('ledger','operations','recovery-operations','replacement-state') for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'EXISTING_OPERATION_RECORDS')
 newowner=copy.deepcopy(owner);candidate=newowner['targets'][receipt['targetConfigRef']]
 rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
 need(all(row['State']['Running'] for row in rows.values()),'ORIGINAL_SERVICES_NOT_RUNNING')
 need(rows['frontend']['NetworkSettings']['Networks']==EXPECTED_FRONTEND_NETWORKS,'FRONTEND_NETWORK_CHANGED_SINCE_PRESTART')
 old='1354d4b702702a85822041e173e0c3fc621eb83c14eb1d6373d428e21945eecf'
 new='0ec083d1cb2347ff058366e03bcf617f37498906a70c4f5263ebbbcf7e34836b'
 changes=[]
 for role,row in rows.items():
  registered=candidate['mainApplication']['networkAttachments'][role]
  current=network_attachments(row)
  if role=='frontend':
   need(registered['bridge']['networkId']==old and registered['bridge']['ipAddress']=='172.17.0.5','EXPECTED_OLD_BRIDGE_CHANGED')
   registered['bridge']['networkId']=new;registered['bridge']['ipAddress']='172.17.0.2'
  need(registered==current,'UNEXPECTED_SERVICE_NETWORK_CHANGE')
 for expected in candidate['mainApplication']['networks']:
  actual=json.loads(run(['docker','network','inspect',expected['name']]))[0]
  observed=network_configuration(actual,sorted(actual['Containers']))
  if expected['name']=='bridge':
   need(expected['id']==old and observed['id']==new,'EXPECTED_BRIDGE_ID_CHANGED')
   expected['id']=new;changes.append({'network':'bridge','beforeId':old,'afterId':new,'frontendBeforeIP':'172.17.0.5','frontendAfterIP':'172.17.0.2'})
  need(observed==expected,'NETWORK_SEMANTICS_OR_MEMBERS_CHANGED')
 need(len(changes)==1,'EXACT_BRIDGE_CHANGE_REQUIRED')
 native=SimpleNamespace(config=candidate,config_services={s['role']:s for s in candidate['services']},
  inspect=lambda identity:next(row for row in rows.values() if row['Id']==identity),
  docker=lambda args:run(['docker',*args]),snapshots={})
 verify_runtime(native,states=False)
 ownerpin=append(root/'configuration/main-recovery-readback-bridge-20261105.json',newowner)
 newcontrol=copy.deepcopy(control);source=target['sourceConfigRef'];ref=receipt['targetConfigRef']
 need(newcontrol['restoreConfigurations'][source][ref]==receipt['ownerConfigurationPin'],'OWNER_BINDING_CHANGED')
 newcontrol['restoreConfigurations'][source][ref]=ownerpin
 controlpin=append(root/'configuration/control-33659-readback-bridge-20261105.json',newcontrol)
 need(Native(controlpin).configuration()==newcontrol,'CONTROL_INVALID')
 unit=pathlib.Path('/etc/systemd/system')/receipt['service'];oldunit=unit.read_bytes()
 need(oldunit.count(canonical(receipt['controlConfigurationPin']))==1,'UNIT_BINDING_CHANGED')
 append(root/'configuration/bridge-20261105-receipt-before.json',receipt)
 append(root/'configuration/bridge-20261105-unit-before.service',oldunit,raw=True)
 need(business()==before,'BUSINESS_DRIFT')
 unit.write_bytes(oldunit.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)))
 run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 receipt.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 temp=receiptpath.with_name('target-installation.bridge-20261105.tmp');append(temp,receipt);temp.replace(receiptpath)
 need(business()==before,'BUSINESS_CHANGED')
 out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':'172.30.30.59',
  'changes':changes,'ownerConfigurationPin':ownerpin,'controlConfigurationPin':controlpin,
  'mainRuntimeStrictVerification':True,'allNetworkSemanticsAndMembersPreserved':True,
  'frontendNetworkSameAsBeforeAuthorizedStarts':True,'businessUnchanged':True,'restoreDispatched':False,'controlActive':True}
 append(root/'configuration/bridge-20261105-attestation.json',out);print(json.dumps(out))
os.close(fd)
'''

if __name__=='__main__':
 baseline=json.loads((PRIVATE/'review-start-authorized-baseline.private.json').read_text(encoding='utf-8'))
 receipt=baseline['documents']['targetInstallation']
 values={'EXPECTED_RECEIPT_PIN':baseline['files']['/mnt/intruoyi-data/spug-main-restore-20261104-v3/target-installation.json'],
  'EXPECTED_OWNER_PIN':receipt['ownerConfigurationPin'],'EXPECTED_CONTROL_PIN':receipt['controlConfigurationPin'],
  'EXPECTED_BUSINESS':json.loads((TASK/'review-authorized-verify.json').read_text(encoding='utf-8'))['business'],
  'EXPECTED_FRONTEND_NETWORKS':next(r['NetworkSettings']['Networks'] for r in baseline['containers'] if r['Id']=='82b9982178e4ea002b25f8cce70b621e29f4af452df7be42d2efc699191ca193')}
 setup='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'
 result=remote('172.30.30.59',COMMON.split('receiptpath=root/')[0]+setup+SCRIPT,timeout=80)
 (TASK/'review-bridge-attestation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
