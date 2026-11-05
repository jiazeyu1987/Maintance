"""Record proven reboot-only mount IDs, preserving all other storage identities."""
import json
from install_review_control import SCRIPT as COMMON
from resume_readonly import TASK,remote
SCRIPT=r'''
from recovery_replacement_storage import observe_directory
from recovery_resource_admission import _host_lock
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
before=business();newowner=copy.deepcopy(owner)
target=newowner['targets'][receipt['targetConfigRef']]
fd=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
 need(not [p for n in ('ledger','operations','recovery-operations','replacement-state') for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'EXISTING_OPERATION_RECORDS')
 diffs=[]
 for expected in target['replacement']['storage']['mounts']:
  backing=expected.get('volume',{}).get('backing')
  need(backing is not None,'EXPECTED_BACKING_REQUIRED')
  actualback=observe_directory(backing['source'])
  need(all(backing[k]==actualback[k] for k in ('device','inode','mountIdentity')),'BACKING_IDENTITY_CHANGED')
  current=observe_directory(expected['source'],backing=backing)
  need(all(current[k]==expected[k] for k in ('device','inode')),'DIRECTORY_IDENTITY_CHANGED')
  old=expected['mountIdentity'];now=current['mountIdentity']
  need({k:v for k,v in old.items() if k!='mountId'}=={k:v for k,v in now.items() if k!='mountId'},'SEMANTIC_MOUNT_CHANGE')
  need((old['mountId'],now['mountId'])==EXPECTED_IDS[expected['role']],'UNEXPECTED_MOUNT_ID')
  diffs.append({'role':expected['role'],'device':current['device'],'inode':current['inode'],'beforeMountId':old['mountId'],'afterMountId':now['mountId']})
  expected['mountIdentity']=now
 ownerpin=append(root/'configuration/main-recovery-readback-postboot-20261105.json',newowner)
 newcontrol=copy.deepcopy(control);source='intruoyi-57-safe-20261024-v1';ref=receipt['targetConfigRef']
 need(newcontrol['restoreConfigurations'][source][ref]==receipt['ownerConfigurationPin'],'OWNER_BINDING_CHANGED')
 newcontrol['restoreConfigurations'][source][ref]=ownerpin
 controlpin=append(root/'configuration/control-33659-readback-postboot-20261105.json',newcontrol)
 from recovery_control_smallapp_native import Native
 need(Native(controlpin).configuration()==newcontrol,'CONTROL_INVALID')
 unit=pathlib.Path('/etc/systemd/system')/receipt['service'];oldunit=unit.read_bytes()
 need(oldunit.count(canonical(receipt['controlConfigurationPin']))==1,'UNIT_BINDING_CHANGED')
 append(root/'configuration/postboot-20261105-receipt-before.json',receipt)
 append(root/'configuration/postboot-20261105-unit-before.service',oldunit,raw=True)
 need(business()==before,'BUSINESS_DRIFT')
 unit.write_bytes(oldunit.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)))
 run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 receipt.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
 temp=receiptpath.with_name('target-installation.postboot-20261105.tmp');append(temp,receipt);temp.replace(receiptpath)
 need(business()==before,'BUSINESS_CHANGED')
 out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bootId':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
  'host':'172.30.30.59','attestedDifferences':diffs,'ownerConfigurationPin':ownerpin,'controlConfigurationPin':controlpin,
  'strictStorageChecksPreserved':True,'businessUnchanged':True,'restoreDispatched':False,'serviceActive':True}
 append(root/'configuration/postboot-20261105-attestation.json',out);print(json.dumps(out))
os.close(fd)
'''
if __name__=='__main__':
    prefix=COMMON.split('receiptpath=root/')[0]
    setup="sys.path[:0]=json.loads(pathlib.Path(json.loads((root/'target-installation.json').read_bytes())['controlConfigurationPin']['path']).read_bytes())['environment']['PYTHONPATH'].split(':')\n"
    out=remote('172.30.30.59',prefix+setup+"EXPECTED_IDS={'mysql':(132,52),'minio':(136,50),'redis':(140,51)}\n"+SCRIPT,timeout=100)
    (TASK/'review-postboot-attestation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
