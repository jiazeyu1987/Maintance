"""Verify actual mount protection coexists with a retained archive path lease."""
import subprocess
from pathlib import Path

SCRIPT=r'''
import json,pathlib,subprocess,sys,tempfile
sys.path.insert(0,'/source/ops/recovery')
from recovery_archive_view import ArchiveViewProtection
from recovery_archive_guard import ArchivePathGuard
from recovery_engine import pin
from recovery_replacement_storage import parse_mountinfo
def command(args,**kwargs):return subprocess.check_output(args,stderr=subprocess.PIPE)
with tempfile.TemporaryDirectory(prefix='spug-archive-lease-',dir='/work') as temporary:
 root=pathlib.Path(temporary);view=root/'view';view.mkdir()
 command(['mount','-t','tmpfs','-o','size=1m','spug-owned-archive-lease',str(view)])
 try:
  file=view/'archived';file.write_bytes(b'immutable-payload')
  lease=ArchivePathGuard.capture([file])
  try:
   observed=next(m for m in parse_mountinfo(pathlib.Path('/proc/self/mountinfo').read_text()) if m['mountPoint']==str(view))
   protection=ArchiveViewProtection(dict(schemaVersion='RegisteredArchiveViewProtection/v1',mountIdentity=observed,mountProgramPin=pin(str(pathlib.Path('/usr/bin/mount').resolve()))),'lease-integration',root/'journal',command)
   lease.check();protection.install();lease.check();protection.verify();protection.release();lease.check()
   assert file.read_bytes()==b'immutable-payload'
  finally:lease.close()
 finally:command(['umount',str(view)])
print(json.dumps(dict(status='PASS',realMountProtection=True,archivePathLeaseHeldAcrossInstallAndRelease=True,originalPayloadPreserved=True)))
'''

if __name__=='__main__':
    result=subprocess.run(['C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe','exec','-i','spug-prod-published-network-env-20261105','python','-B','-'],input=SCRIPT.encode('utf-8'),capture_output=True)
    Path(__file__).with_suffix('.log').write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8')[-1500:]);print(result.stderr.decode('utf-8')[-1500:]);raise SystemExit(result.returncode)
