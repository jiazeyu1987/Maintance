"""Register only Docker's newly explicit gateway, preserving strict identity checks."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import copy,datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def create(p,data):
 with p.open('xb') as f:f.write(canonical(data))
 p.chmod(0o600);return pin(p)
def read(p):
 path=pathlib.Path(p['path']);assert pin(path)==p;return json.loads(path.read_bytes())
def run(args):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True).stdout.decode().strip()
receiptpath=root/'target-installation.json';receipt=json.loads(receiptpath.read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
assert not any((root/'replacement-state').iterdir()) and not [p for p in (root/'ledger').iterdir() if p.name!='service.lock']
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bb31c4d0-bbfb-4b97-8c06-4ff11e779015'
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_target import network_configuration,network_attachments,service_configuration_digest,validate
newowner=copy.deepcopy(owner);target=newowner['targets'][receipt['targetConfigRef']];evidence=[]
for expected in target['mainApplication']['networks']:
 current=network_configuration(json.loads(run(['docker','network','inspect',expected['id']]))[0],expected['memberContainerIds'])
 if current==expected:continue
 assert expected['id']=='72f4b6562e02daa514b3102d4e6ce61b986e3ed60259b4e333ad14bea3d5284b'
 assert {k:v for k,v in expected.items() if k!='ipam'}=={k:v for k,v in current.items() if k!='ipam'}
 assert expected['ipam']=={'Config':[{'Subnet':'172.29.235.0/24'}],'Driver':'default','Options':{}}
 assert current['ipam']=={'Config':[{'Subnet':'172.29.235.0/24','Gateway':'172.29.235.1'}],'Driver':'default','Options':{}}
 evidence.append({'networkId':expected['id'],'internal':expected['internal'],'before':expected['ipam'],'after':current['ipam']});expected['ipam']=current['ipam']
assert len(evidence)==1
for service in target['services']:
 row=json.loads(run(['docker','inspect',service['id']]))[0];role=service['role']
 assert network_attachments(row)==target['mainApplication']['networkAttachments'][role]
 assert service_configuration_digest(row)==target['mainApplication']['serviceConfigurationDigests'][role]
validate(target)
ownerpin=create(root/'configuration/main-recovery-boot-bb31c4d0-r2.json',newowner)
newcontrol=copy.deepcopy(control);source=next(iter(newcontrol['restoreConfigurations']));newcontrol['restoreConfigurations'][source][receipt['targetConfigRef']]=ownerpin
controlpin=create(root/'configuration/control-43658-boot-bb31c4d0-r2.json',newcontrol)
unit=pathlib.Path('/etc/systemd/system')/receipt['service'];before=unit.read_bytes();assert before.count(canonical(receipt['controlConfigurationPin']))==1
create(root/'configuration/postboot-bb31c4d0-network-receipt-before.json',receipt)
backup=root/'configuration/postboot-bb31c4d0-network-unit-before.service'
with backup.open('xb') as f:f.write(before)
backup.chmod(0o600)
unit.write_bytes(before.replace(canonical(receipt['controlConfigurationPin']),canonical(controlpin)))
run(['systemctl','daemon-reload']);run(['systemctl','restart',receipt['service']]);assert run(['systemctl','is-active',receipt['service']])=='active'
updated=copy.deepcopy(receipt);updated.update(ownerConfigurationPin=ownerpin,controlConfigurationPin=controlpin)
temp=receiptpath.with_name('target-installation.network.tmp');assert not temp.exists();temp.write_bytes(canonical(updated));temp.chmod(0o600);temp.replace(receiptpath)
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attestedDifferences':evidence,'ownerConfigurationPin':ownerpin,'controlConfigurationPin':controlpin,'strictNetworkChecksPreserved':True,'serviceIdentityAndAttachmentsUnchanged':True,'restorePerformed':False}
create(root/'configuration/postboot-bb31c4d0-network-attestation.json',out);print(json.dumps(out))
'''
if __name__=='__main__':
 result=remote('172.30.30.58',SCRIPT,timeout=60)
 (TASK/'test-network-attestation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
