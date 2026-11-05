"""Issue a new immutable target configuration for the verified reboot mount IDs."""
import json
from repair_preflight import remote,TASK,PRIVATE
SCRIPT=r'''
import copy,datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def pin(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):
 path=pathlib.Path(p['path']);assert pin(path)==p,'CONFIG_PIN_CHANGED';return json.loads(path.read_bytes())
def create(path,data):
 with path.open('xb') as f:f.write(canonical(data))
 path.chmod(0o600);return pin(path)
def run(args,timeout=20):return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout).stdout.decode().strip()
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes())
control=read(receipt['controlConfigurationPin']);owner=read(receipt['ownerConfigurationPin'])
assert not any((root/'replacement-state').iterdir())
assert not [p for p in (root/'ledger').iterdir() if p.name!='service.lock']
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_replacement_storage import observe_directory
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='bb31c4d0-bbfb-4b97-8c06-4ff11e779015'
newowner=copy.deepcopy(owner);diffs=[]
mounts=newowner['targets'][receipt['targetConfigRef']]['replacement']['storage']['mounts']
for expected in mounts:
 current=observe_directory(expected['source'],backing=expected.get('volume',{}).get('backing'))
 assert all(expected[k]==current[k] for k in ('device','inode')),'DATA_DIRECTORY_CHANGED'
 before=copy.deepcopy(expected['mountIdentity']);now=current['mountIdentity']
 assert before['mountId']==116 and now['mountId']==119,'UNEXPECTED_MOUNT_ID_CHANGE'
 assert {k:v for k,v in before.items() if k!='mountId'}=={k:v for k,v in now.items() if k!='mountId'},'MOUNT_IDENTITY_CHANGED'
 expected['mountIdentity']=now;diffs.append({'role':expected['role'],'device':current['device'],'inode':current['inode'],'beforeMountId':116,'afterMountId':119})
newownerpin=create(root/'configuration/main-recovery-boot-bb31c4d0.json',newowner)
newcontrol=copy.deepcopy(control)
source=next(iter(newcontrol['restoreConfigurations']));assert newcontrol['restoreConfigurations'][source][receipt['targetConfigRef']]==receipt['ownerConfigurationPin']
newcontrol['restoreConfigurations'][source][receipt['targetConfigRef']]=newownerpin
newcontrolpin=create(root/'configuration/control-43658-boot-bb31c4d0.json',newcontrol)
unit=pathlib.Path('/etc/systemd/system')/receipt['service'];beforeunit=unit.read_bytes()
oldtext=canonical(receipt['controlConfigurationPin']);assert beforeunit.count(oldtext)==1,'SERVICE_PIN_FORMAT_CHANGED'
create(root/'configuration/postboot-bb31c4d0-receipt-before.json',receipt)
backup=root/'configuration/postboot-bb31c4d0-unit-before.service'
with backup.open('xb') as f:f.write(beforeunit)
backup.chmod(0o600)
from recovery_control_smallapp_native import Native
assert Native(newcontrolpin).configuration()==newcontrol
unit.write_bytes(beforeunit.replace(oldtext,canonical(newcontrolpin)))
run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']])
assert run(['systemctl','is-active',receipt['service']])=='active'
newreceipt=copy.deepcopy(receipt);newreceipt.update(ownerConfigurationPin=newownerpin,controlConfigurationPin=newcontrolpin)
temp=receiptpath.with_name('target-installation.postboot.tmp');assert not temp.exists()
temp.write_bytes(canonical(newreceipt));temp.chmod(0o600);temp.replace(receiptpath)
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':'172.30.30.58','bootId':boot,'attestedDifferences':diffs,'ownerConfigurationPin':newownerpin,'controlConfigurationPin':newcontrolpin,'service':receipt['service'],'state':'active','strictMountChecksPreserved':True,'restorePerformed':False}
create(root/'configuration/postboot-bb31c4d0-attestation.json',out);print(json.dumps(out))
'''
if __name__=='__main__':
 result=remote('172.30.30.58',SCRIPT,timeout=60)
 (TASK/'test-postboot-attestation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 (PRIVATE/'test-postboot-attestation.private.json').write_text(json.dumps(result),encoding='utf-8');print(json.dumps(result))
