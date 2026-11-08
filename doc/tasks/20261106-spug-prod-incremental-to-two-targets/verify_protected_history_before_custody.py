"""Record/verify old native metadata; never changes or deletes earlier history."""
import argparse,json
from common import TASK,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path(ROOT)
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if EXPECTED is None:
 files=[]
 for name in ('ledger','recovery-operations','replacement-state','request-configurations','configuration'):
  directory=root/name
  if not directory.exists():continue
  for path in directory.rglob('*'):
   if path.is_file() and path.suffix in ('.json','.log'):
    assert not path.is_symlink() and path.stat().st_size<=64*1024*1024,'OLD_METADATA_OUT_OF_SCOPE'
    files.append(path)
 files.append(root/'target-installation.json')
 assert sum(p.stat().st_size for p in files)<=512*1024*1024,'OLD_METADATA_BUDGET_EXCEEDED'
 pins=[pin(p) for p in sorted(set(files))]
else:
 pins=EXPECTED
 for reference in pins:assert pin(pathlib.Path(reference['path']))==reference,'OLD_NATIVE_HISTORY_CHANGED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,protectedFiles=len(pins),protectedBytes=sum(p['bytes'] for p in pins),evidencePins=pins)))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['57','58','59']);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
 path=TASK/('protected-history-'+args.suffix+'.json')
 if args.verify:expected=json.loads(path.read_text(encoding='utf-8'))['evidencePins']
 else:assert not path.exists(),'BASELINE_EXISTS';expected=None
 host='172.30.30.'+args.suffix;root=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
 script='ROOT='+repr(root)+'\nHOST='+repr(host)+'\nEXPECTED='+repr(expected)+'\n'+SCRIPT
 value=remote(host,script,90)
 write(TASK/(('protected-history-verified-' if args.verify else 'protected-history-')+args.suffix+'.json'),value)
 print(json.dumps({k:v for k,v in value.items() if k!='evidencePins'}))
