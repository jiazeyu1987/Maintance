"""Stream-hash every original file of the exited failed restore, without target writes."""
import json
from common import PRIVATE, TASK, now, remote, write

SCRIPT = r'''
import hashlib,json,os,pathlib,stat,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation='smallapp-c21bb7ce9f5b4668b850c37a80964786'
op=root/'recovery-operations'/operation
assert json.loads((op/'worker-result.json').read_bytes())['state']=='FAILED_RETAINED'
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 try:command=(proc/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 assert not (operation.encode() in command and b'recovery_minimal_worker.py' in command),'FAILED_WORKER_STILL_RUNNING'
deadline=time.monotonic()+890
def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
paths=[]
for directory in (op,root/'ledger'/operation):
 assert directory.is_dir() and directory.resolve()==directory
 paths.extend(p for p in directory.rglob('*') if not p.is_dir())
assert len(paths)<=15000 and sum(p.lstat().st_size for p in paths)<=128*1024**3,'FAILED_ORIGINAL_BUDGET_EXCEEDED'
pins=[]
for path in sorted(paths):
 before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and path.resolve()==path,'FAILED_ORIGINAL_PATH_INVALID'
 sha=hashlib.sha256();size=0
 with path.open('rb') as stream:
  assert identity(os.fstat(stream.fileno()))==identity(before)
  while True:
   assert time.monotonic()<deadline,'FAILED_PIN_READ_DEADLINE'
   raw=stream.read(1024*1024)
   if not raw:break
   sha.update(raw);size+=len(raw)
  assert identity(os.fstat(stream.fileno()))==identity(before)
 assert identity(path.lstat())==identity(before) and size==before.st_size
 pins.append(dict(path=str(path),bytes=size,sha256=sha.hexdigest()))
indexed={p['path']:p for p in pins}
assert all(indexed.get(p['path'])==p for p in EXPECTED),'ORIGINAL_FAILURE_METADATA_CHANGED'
print(json.dumps(dict(status='PASS',operationId=operation,pins=pins,protectedFiles=len(pins),protectedBytes=sum(p['bytes'] for p in pins),allOriginalBytesRead=True,anyTargetMutation=False)))
'''

if __name__ == '__main__':
    destination = PRIVATE / 'failed-368-all-pins.private.json'
    assert not destination.exists(), 'FAILURE_BASELINE_ALREADY_EXISTS'
    prior = json.loads((TASK / 'restore-368-failure.json').read_text(encoding='utf-8'))
    value = remote('172.30.30.58', 'EXPECTED=' + repr(prior['pins']) + '\n' + SCRIPT, 910)
    value['observedAt'] = now()
    write(destination, value)
    report = {k: v for k, v in value.items() if k != 'pins'}
    write(TASK / 'failed-368-all-files-preserved.json', report)
    print(json.dumps(report))
