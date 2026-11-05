"""Restore the registered destination's original read-only archive mount."""
import json
from repair_preflight import remote, TASK

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
def run(args,timeout=30):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:raise RuntimeError('COMMAND_FAILED '+repr(args[:3]))
 return p.stdout.decode().strip()
source=pathlib.Path('/mnt/intruoyi-backup-nas')
target=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
relative='Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives/prod-standard-197d8fd4ced92df64f0c152e9c6d470596ec343532e3b2dd82ebbef680114bcb/.repository/point.json'
expected='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128'
assert hashlib.sha256((source/relative).read_bytes()).hexdigest()==expected
def mounts():return pathlib.Path('/proc/self/mountinfo').read_text().splitlines()
rows=[l for l in mounts() if l.split()[4]==str(source) and ' - cifs ' in l]
assert len(rows)==1 and rows[0].split(' - ')[1].split()[1]=='//172.30.30.4/IT共享' and rows[0].split()[3]=='/'
assert target.is_dir() and target.resolve()==target and not target.is_symlink() and not any(target.iterdir())
assert not any(l.split()[4]==str(target) for l in mounts())
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
assert not any((root/'replacement-state').iterdir())
failed=root/'ledger/smallapp-ba0bca490ac243768c8b759fa14a8bbd'
assert sorted(p.name for p in failed.iterdir())==['admission-error.json','intent.json','request.json','selection.json']
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
ids=[s['id'] for s in owner['targets'][receipt['targetConfigRef']]['services']]
def states():
 rows=json.loads(run(['docker','inspect']+ids))
 return {r['Id']:{'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],'running':r['State']['Running']} for r in rows}
before=states();assert all(v['running'] for v in before.values())
unit=run(['systemd-escape','--path','--suffix=mount',str(target)])
unitPath=pathlib.Path('/etc/systemd/system')/unit
drop=pathlib.Path('/etc/systemd/system/spug-main-restore-58-20261104-v3.service.d/archive-mount.conf')
assert not unitPath.exists() and not drop.exists()
body='[Unit]\nDescription=Registered IntRuoyi original read-only archive mount\nRequiresMountsFor='+str(source)+'\nAfter=network-online.target\n\n[Mount]\nWhat='+str(source)+'\nWhere='+str(target)+'\nType=none\nOptions=bind,ro\nTimeoutSec=25\n\n[Install]\nWantedBy=multi-user.target\n'
unitPath.write_text(body,encoding='utf-8');unitPath.chmod(0o644)
drop.parent.mkdir(exist_ok=True)
drop.write_text('[Unit]\nRequiresMountsFor='+str(target)+'\n',encoding='utf-8');drop.chmod(0o644)
run(['systemctl','daemon-reload'])
run(['systemctl','enable','--now',unit])
rows=[l for l in mounts() if l.split()[4]==str(target)]
assert len(rows)==1 and rows[0].split()[5].split(',')[0]=='ro' and rows[0].split()[3]=='/'
assert rows[0].split(' - ')[1].split()[:2]==['cifs','//172.30.30.4/IT共享']
assert hashlib.sha256((target/relative).read_bytes()).hexdigest()==expected
after=states();assert after==before
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unit':unit,'active':run(['systemctl','is-active',unit]),'enabled':run(['systemctl','is-enabled',unit]),'target':str(target),'source':str(source),'mode':'ro','pointSha256':expected,'businessServicesUnchanged':True,'businessServices':after,'controlActive':run(['systemctl','is-active','spug-main-restore-58-20261104-v3.service'])}))
'''
if __name__=='__main__':
 result=remote('172.30.30.58',SCRIPT,70)
 (TASK/'target-archive-mount-restored.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
