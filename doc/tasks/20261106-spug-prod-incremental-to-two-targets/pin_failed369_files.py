"""Preserve every actual 369 file; confirm no mutation and exact previous consumption."""
from common import PRIVATE,TASK,remote,write
import json
SCRIPT=r'''
import datetime,hashlib,json,pathlib,stat
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3');operation='smallapp-b4f35606e4854516960050a76473038b'
op=root/'recovery-operations'/operation;claim=root/'replacement-state'/operation
def load(p):return json.loads(p.read_bytes())
result=load(op/'worker-result.json');exit=load(op/'child-exit.json')
assert result['state']=='FAILED_RETAINED' and result['failureCode']=='MAIN_HEALTH_ENDPOINT_INVALID' and result['actualExitCode']==exit['actualExitCode']==1
assert result['data']['mutationDispatched'] is False and not (op/'replacement-preparation/replacement-intent.json').exists()
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists()
release=load(op/'resource-no-mutation-release.json');assert release['reason']=='PROVEN_NO_MUTATION'
native=[load(p) for p in op.rglob('native-*.json')];assert len(native)==6 and all(p['mutation'] is False and p['actualExitCode']==0 for p in native)
previous=root/'replacement-state/smallapp-c21bb7ce9f5b4668b850c37a80964786'
consumed=load(previous/'recovery-consumption.json');assert consumed['replacementOperationId']==operation
pins=[]
for folder in (op,claim,root/'ledger'/operation):
 for p in sorted(folder.rglob('*')):
  s=p.lstat()
  if stat.S_ISDIR(s.st_mode):continue
  assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and p.resolve()==p and s.st_nlink==1
  raw=p.read_bytes();after=p.lstat();assert (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
  pins.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
 pins=pins,fileCount=len(pins),bytes=sum(p['bytes'] for p in pins),mutationDispatched=False,nativeCommands=6,
 allNativeCommandsReadOnly=True,noMutationReservationReleaseVerified=True,previousClearanceConsumedByThisOperation=True)))
'''
if __name__=='__main__':
 result=remote('172.30.30.58',SCRIPT,90)
 write(PRIVATE/'failed-369-all-pins.private.json',result)
 public={k:v for k,v in result.items() if k!='pins'};write(TASK/'failed-369-all-files-preserved.json',public);print(json.dumps(public))
