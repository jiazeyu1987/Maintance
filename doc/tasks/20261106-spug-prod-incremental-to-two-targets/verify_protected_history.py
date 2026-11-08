"""Record/verify old native metadata; never changes or deletes earlier history."""
import argparse,json
from common import TASK,remote,write
from installation_history_custody import inputs as custody_inputs,SCRIPT as CUSTODY_SCRIPT

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
custody=verify_installation_receipt_custody(RECEIPT_CUSTODY) if RECEIPT_CUSTODY is not None else None
original_count=len(pins)+(1 if custody is not None else 0)
original_bytes=sum(p['bytes'] for p in pins)+(RECEIPT_CUSTODY['originalActiveReceiptPin']['bytes'] if custody is not None else 0)
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,
 protectedFiles=original_count,protectedBytes=original_bytes,evidencePins=pins,
 originalProtectedFileCount=original_count,immutableOriginalPathsVerified=len(pins),
 allImmutableOriginalPathsUnchanged=True,allOriginalBytesPreserved=True,installationReceiptCustody=custody)))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['57','58','59']);parser.add_argument('--verify',action='store_true');parser.add_argument('--custody-preflight',action='store_true');args=parser.parse_args()
 assert not args.custody_preflight or (args.verify and args.suffix in ('58','59'))
 path=TASK/('protected-history-'+args.suffix+'.json')
 receipt_custody=None
 if args.verify:
  expected=json.loads(path.read_text(encoding='utf-8'))['evidencePins']
  if args.suffix in ('58','59'):
   immutable,receipt_custody=custody_inputs(args.suffix)
   assert len(immutable)+1==len(expected) and all(p in expected for p in immutable)
   expected=immutable
 else:assert not path.exists(),'BASELINE_EXISTS';expected=None
 host='172.30.30.'+args.suffix;root=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
 script='ROOT='+repr(root)+'\nHOST='+repr(host)+'\nEXPECTED='+repr(expected)+'\nRECEIPT_CUSTODY='+repr(receipt_custody)+'\n'+CUSTODY_SCRIPT+'\n'+SCRIPT
 value=remote(host,script,90)
 prefix='protected-history-custody-preflight-' if args.custody_preflight else ('protected-history-verified-' if args.verify else 'protected-history-')
 destination=TASK/(prefix+args.suffix+'.json')
 if args.custody_preflight:assert not destination.exists()
 write(destination,value)
 summary={k:v for k,v in value.items() if k not in ('evidencePins','installationReceiptCustody')}
 if value['installationReceiptCustody'] is not None:
  summary['installationReceiptCustody']={k:v for k,v in value['installationReceiptCustody'].items() if k!='verifiedPins'}
 print(json.dumps(summary))
