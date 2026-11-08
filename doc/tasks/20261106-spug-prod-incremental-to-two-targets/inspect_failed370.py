"""Freeze all original 370 files and report only safe terminal metadata."""
import json
from common import PRIVATE,TASK,remote,write,restore_kind
operation=json.loads((TASK/(restore_kind('58')+'-ui-submission.json')).read_text(encoding='utf8'))['request']['operationId']
SCRIPT=r'''
import datetime,hashlib,json,pathlib,stat
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation=OPERATION
op=root/'recovery-operations'/operation
result=json.loads((op/'worker-result.json').read_bytes())
assert result['state']=='FAILED_RETAINED' and result['actualExitCode']==1
pins=[];documents={}
for folder in (op,root/'replacement-state'/operation,root/'ledger'/operation):
 if not folder.is_dir():continue
 for p in sorted(folder.rglob('*')):
  before=p.lstat()
  if stat.S_ISDIR(before.st_mode):continue
  assert stat.S_ISREG(before.st_mode) and not p.is_symlink() and p.resolve()==p and before.st_nlink==1
  raw=p.read_bytes();after=p.lstat()
  assert (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
  pins.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
  if p.suffix=='.json':documents[str(p)]=json.loads(raw)
native=[json.loads(p.read_bytes()) for p in op.rglob('native-*.json')]
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
release=op/'resource-no-mutation-release.json'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
 state=result['state'],actualExitCode=result['actualExitCode'],failureCode=result['failureCode'],mutationDispatched=result['data']['mutationDispatched'],
 replacementIntentExists=(op/'replacement-preparation/replacement-intent.json').exists(),activeReservation=active.exists(),
 noMutationRelease=json.loads(release.read_bytes()) if release.exists() else None,
 nativeCommands=len(native),allNativeCommandsReadOnly=all(v['mutation'] is False and v['actualExitCode']==0 for v in native),
 pins=pins,fileCount=len(pins),bytes=sum(v['bytes'] for v in pins),documents=documents)))
'''.replace('OPERATION',repr(operation))
for name in ('failed-370-all-pins.private.json','failed-370-all-files-preserved.json'):
 assert not (PRIVATE/name if name.endswith('.private.json') else TASK/name).exists(),'ORIGINAL_ALREADY_FROZEN'
value=remote('172.30.30.58',SCRIPT,90)
write(PRIVATE/'failed-370-all-pins.private.json',value)
public={k:v for k,v in value.items() if k not in ('pins','documents')}
write(TASK/'failed-370-all-files-preserved.json',public);print(json.dumps(public))
