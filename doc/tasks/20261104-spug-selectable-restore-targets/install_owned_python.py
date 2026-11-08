"""Copy the verified Python into an owned executable location; do not relabel shared runtime."""
import json
from install_controls import PRIVATE,PROFILES,ROOTS,ssh
REMOTE=r'''
import hashlib,json,os,pathlib,shutil,subprocess
src=pathlib.Path('/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/installed/python')
dst=pathlib.Path('/usr/local/libexec/spug-main-restore-20261104/python')
root=pathlib.Path(ROOT);unit=pathlib.Path('/etc/systemd/system/spug-main-restore-58-20261104-v3.service')
assert unit.is_file() and not unit.is_symlink() and str(root/'engine/control_entry.py') in unit.read_text()
before=unit.read_bytes();assert str(src/'bin/python3.12').encode() in before
subprocess.run(['systemctl','stop',unit.name],check=True,timeout=15)
assert not dst.exists() and not dst.parent.exists(),'OWNED_RUNTIME_ALREADY_EXISTS'
if not dst.parent.parent.exists():dst.parent.parent.mkdir(mode=0o755)
assert dst.parent.parent.resolve()==dst.parent.parent
for p in src.rglob('*'):
 if p.is_symlink():assert p.resolve().is_relative_to(src),'PYTHON_EXTERNAL_LINK_REFUSED'
dst.parent.mkdir(mode=0o755)
shutil.copytree(src,dst,symlinks=True)
manifest={}
for p in src.rglob('*'):
 q=dst/p.relative_to(src)
 if p.is_symlink():assert q.is_symlink() and os.readlink(p)==os.readlink(q)
 elif p.is_file():
  checksum=hashlib.sha256(p.read_bytes()).hexdigest();assert hashlib.sha256(q.read_bytes()).hexdigest()==checksum
  manifest[str(p.relative_to(src))]=checksum
subprocess.run(['restorecon','-RF',str(dst.parent)],check=True,timeout=40,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
subprocess.run([str(dst/'bin/python3.12'),'-B','-c','import sys,json,ssl;assert sys.version_info[:2]==(3,12)'],check=True,timeout=10)
backup=root/'configuration/failed-old-python-unit.service'
assert not backup.exists();backup.write_bytes(before);backup.chmod(0o600)
assert unit.read_bytes()==before;unit.unlink()
result={'host':'172.30.30.58','source':str(src),'installed':str(dst),'python':str(dst/'bin/python3.12'),'filesVerified':len(manifest),'manifestSha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'priorOwnedServiceStopped':True,'sharedRuntimeChanged':False}
(root/'configuration/owned-python-installation.json').write_text(json.dumps(result),encoding='utf-8')
print(json.dumps(result))
'''
p=next(p for p in PROFILES if p['host'].endswith('.58'))
p=dict(p,python='/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/installed/python/bin/python3.12')
result=ssh(p,'ROOT='+repr(ROOTS['58'])+'\n'+REMOTE,timeout=90)
(PRIVATE/'58-owned-python-installation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
