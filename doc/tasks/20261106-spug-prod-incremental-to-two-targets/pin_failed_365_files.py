"""Freeze all retained failure bytes, keeping the detailed pins private."""
import argparse,json

from common import PRIVATE, TASK, now, remote, write


SCRIPT = r'''
import hashlib,json,os,pathlib,stat,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION'
deadline=time.monotonic()+170
def identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
def pin(path):
 before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and path.resolve()==path,'FAILED_ORIGINAL_PATH_INVALID'
 sha=hashlib.sha256();size=0
 with path.open('rb') as stream:
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
  while True:
   assert time.monotonic()<deadline,'FAILED_PIN_READ_DEADLINE'
   raw=stream.read(1024*1024)
   if not raw:break
   sha.update(raw);size+=len(raw)
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
 assert identity(path.lstat())==identity(before) and size==before.st_size,'FAILED_ORIGINAL_CHANGED'
 return dict(path=str(path),bytes=size,sha256=sha.hexdigest())
paths=[]
for directory in [root/'capture-staging'/OPERATION,root/'repository-operations'/hashlib.sha256(OPERATION.encode()).hexdigest(),root/'request-configurations'/OPERATION]:
 assert directory.is_dir() and directory.resolve()==directory,'FAILED_ORIGINAL_DIRECTORY_REQUIRED'
 paths.extend(p for p in directory.rglob('*') if not p.is_dir())
# Read-only footprint inspection found 9047 tiny native query receipts plus
# 39 capture files and four request files; preserve every original receipt.
assert len(paths)<=10000 and sum(p.lstat().st_size for p in paths)<=3*1024**3,'FAILED_ORIGINAL_BUDGET_EXCEEDED'
pins=[pin(p) for p in sorted(paths)]
by_path={p['path']:p for p in pins}
assert all(by_path.get(p['path'])==p for p in EXPECTED),'FAILED_ORIGINAL_CHANGED'
print(json.dumps(dict(status='PASS',operationId=OPERATION,pins=pins,protectedFiles=len(pins),protectedBytes=sum(p['bytes'] for p in pins))))
'''


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--history',choices=['365','366'],default='365');args=parser.parse_args()
    destination = PRIVATE / ('failed-'+args.history+'-all-pins.private.json')
    assert not destination.exists(), 'FAILURE_BASELINE_ALREADY_EXISTS'
    prior = json.loads((TASK / ('incremental-'+args.history+'-failure.json')).read_text(encoding='utf-8'))
    value = remote('172.30.30.57', 'OPERATION=' + repr(prior['operationId']) + '\nEXPECTED=' + repr(prior['pins']) + '\n' + SCRIPT, 185)
    value['observedAt'] = now()
    write(destination, value)
    public = {key: val for key, val in value.items() if key != 'pins'}
    public.update(priorMetadataPinsVerified=len(prior['pins']), payloadBytesReadOnly=True)
    write(TASK / ('failed-'+args.history+'-all-files-preserved.json'), public)
    print(json.dumps(public))
