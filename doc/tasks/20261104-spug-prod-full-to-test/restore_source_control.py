"""Install an owned executable Python copy and persistent original source control."""
import json
from repair_preflight import remote,TASK,PRIVATE
SCRIPT=r'''
import copy,datetime,hashlib,json,os,pathlib,shutil,subprocess
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
control=json.loads((root/'configuration/control.json').read_bytes())
def pin(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def run(args,timeout=25):return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=timeout).stdout.decode().strip()
assert pin(pathlib.Path(control['pythonPin']['path']))==control['pythonPin']
assert hashlib.sha256((root/'engine/control_entry.py').read_bytes()).hexdigest()=='de1a6731b95e4497bab1cc5ff26865a4a22c2fca45e2e59650caeccba2451ec0','SOURCE_ENTRY_CHANGED'
unit=pathlib.Path('/etc/systemd/system/spug-intruoyi-source-57-20261105.service');assert not unit.exists()
assert not any(':32657 ' in l for l in run(['ss','-lntp']).splitlines()),'SOURCE_CONTROL_ALREADY_LISTENING'
assert any(l.split()[4]=='/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas' and ' - cifs ' in l for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines()),'NAS_MISSING'
src=pathlib.Path(control['pythonPin']['path']).parent.parent;dst=pathlib.Path('/usr/local/libexec/spug-source-control-20261105/python')
assert not dst.parent.exists()
for p in src.rglob('*'):
 if p.is_symlink():p.resolve().relative_to(src)
dst.parent.mkdir(mode=0o755,parents=True);shutil.copytree(str(src),str(dst),symlinks=True)
manifest={}
for p in src.rglob('*'):
 q=dst/p.relative_to(src)
 if p.is_symlink():assert q.is_symlink() and os.readlink(p)==os.readlink(q)
 elif p.is_file():
  checksum=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(q.read_bytes()).hexdigest()==checksum;manifest[str(p.relative_to(src))]=checksum
run(['restorecon','-RF',str(dst.parent)],timeout=50)
python=dst/'bin/python3.12';run([str(python),'-B','-c','import json,ssl,sys;assert sys.version_info[:2]==(3,12)'])
newcontrol=copy.deepcopy(control);newcontrol['pythonPin']=pin(python)
configpath=root/'configuration/control-postboot-20261105.json'
with configpath.open('xb') as f:f.write(canonical(newcontrol))
configpath.chmod(0o600);configpin=pin(configpath)
command=str(python)+' -B '+str(root/'engine/control_entry.py')+' serve --config-pin '+"'"+canonical(configpin).decode('utf-8')+"'"
text='[Unit]\nDescription=Spug original IntRuoyi production source control\nAfter=network-online.target docker.service\nWants=network-online.target\nRequiresMountsFor=/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas\n\n[Service]\nType=simple\nUser=root\nUMask=0077\nWorkingDirectory='+str(root)+'\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart='+command+'\nRestart=on-failure\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\n'
with unit.open('xb') as f:f.write(text.encode('utf-8'))
unit.chmod(0o644)
run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',unit.name]);assert run(['systemctl','is-active',unit.name])=='active'
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'service':unit.name,'sourceConfigRef':next(iter(newcontrol['sourceConfigurations'])),'controlConfigurationPin':configpin,'pythonPin':pin(python),'pythonFilesVerified':len(manifest),'pythonManifestSha256':hashlib.sha256(canonical(manifest)).hexdigest(),'sharedRuntimeChanged':False,'state':'active','fullSubmitted':False}
(root/'configuration/source-postboot-installation.json').write_bytes(canonical(out));print(json.dumps(out))
'''
if __name__=='__main__':
 r=remote('172.30.30.57',SCRIPT,timeout=140)
 (TASK/'source-control-restored.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r))
