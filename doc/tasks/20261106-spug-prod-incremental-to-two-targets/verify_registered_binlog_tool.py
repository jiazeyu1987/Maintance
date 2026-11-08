"""Read-only completion check; never repeats the already accepted tool start."""
import hashlib,json
from common import PRIVATE,TASK,remote,write,now

SCRIPT=r'''
import hashlib,json,pathlib,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
engine=root/'engine-incremental-6319024'
sys.path[:0]=[str(engine/'common'),str(engine/'formal'),'/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/runtime/lib/python3.12/site-packages']
from minimal_capture_support import MinimalSeries
from types import SimpleNamespace
tool=json.loads(pathlib.Path(TOOL_PIN['path']).read_bytes())
assert MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=tool,mysql_source=MYSQL_ID,guard=lambda:None),None)==tool['containerId']
failure=root/'repository-operations'/hashlib.sha256(OPERATION.encode()).hexdigest()/'result.json'
result=json.loads(failure.read_bytes())
assert result==EXPECTED_RESULT,'FAILED_RESULT_CHANGED'
verified=[]
for reference in result['originalResultPins']:
 raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'FAILED_ORIGINAL_CHANGED';verified.append(reference)
files=[]
for directory in [root/'capture-staging'/OPERATION,root/'repository-operations'/hashlib.sha256(OPERATION.encode()).hexdigest(),root/'request-configurations'/OPERATION]:
 for path in directory.rglob('*'):
  if path.is_file():
   assert not path.is_symlink();raw=path.read_bytes();files.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
print(json.dumps(dict(status='PASS',strictInstalledNativeToolValidation=True,failedResultPreserved=True,failedResultOriginalPinsVerified=verified,failedOriginalFiles=len(files),failedOriginalPins=files)))
'''
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def definition(row):return {k:row[k] for k in ('Path','Args','HostConfig','Config','Image')}|dict(Mounts=sorted(row['Mounts'],key=lambda m:m['Destination']))
if __name__=='__main__':
 before=json.loads((PRIVATE/'pre-install-57.private.json').read_text(encoding='utf-8'));after=json.loads((PRIVATE/'after-tool-start-57.private.json').read_text(encoding='utf-8'))
 old={r['Id']:r for r in before['containers']};new={r['Id']:r for r in after['containers']};assert set(old)==set(new)
 tool='70c0487396f6954ec794230644cc5d01669c7c0ed217df7b6c4a35a722a5832a';deltas=[]
 for identity,row in old.items():
  current=new[identity];changed=[k for k in definition(row) if canonical(definition(row)[k])!=canonical(definition(current)[k])]
  if changed:deltas.append(dict(id=identity,changedDefinitionFields=changed))
  if identity!=tool:
   assert {k:row['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')}=={k:current['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},'OTHER_RUNTIME_CHANGED'
 assert not deltas,repr(deltas)
 oldmount=set(before['mountinfo'].splitlines());newmount=set(after['mountinfo'].splitlines())
 added=newmount-oldmount;merged=new[tool]['GraphDriver']['Data']['MergedDir']
 assert before['fstabSha256']==after['fstabSha256'] and oldmount<=newmount and len(added)==1 and next(iter(added)).split()[4]==merged,'PROTECTED_STORAGE_CHANGED'
 original=json.loads((PRIVATE/'incremental-364-failure.private.json').read_text(encoding='utf-8'));toolpin=original['tools'][0]['pin'];result=next(v for k,v in original['documents'].items() if k.endswith('/result.json'))
 variables=dict(TOOL_PIN=toolpin,MYSQL_ID='9a288d20d254366e99b265b1870466e974edf23e7aab60de2391e3a38e62fff6',OPERATION='smallapp-a690233d967d4965bf5f861dc1126961',EXPECTED_RESULT=result)
 value=remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,100)
 value.update(observedAt=now(),containerId=tool,originalContainerCount=len(old),allOriginalDefinitionsAndImagesPreserved=True,otherRuntimePreserved=True,fstabAndMountsPreserved=True,initialStartCompletionCheck='UNSORTED_MOUNT_LIST_COMPARE_FAILED',readOnlyCompletionCheck=True,restartPolicyChanged=False)
 write(TASK/'registered-binlog-tool-restored.json',value);print(json.dumps({k:v for k,v in value.items() if k not in ('failedOriginalPins','failedResultOriginalPinsVerified')}))
