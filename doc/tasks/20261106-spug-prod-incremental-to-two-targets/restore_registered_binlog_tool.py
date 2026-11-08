"""Start only the previously registered original source binlog sidecar."""
import hashlib,json
from common import PRIVATE,TASK,remote,write

SCRIPT=r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,time
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=30);need(p.returncode==0,'TOOL_COMMAND_FAILED');return p.stdout
def snapshot():
 rows=json.loads(run(['docker','inspect',*run(['docker','ps','-aq','--no-trunc']).decode().split()]))
 return {r['Id']:dict(definitionSha256=hashlib.sha256(canonical({k:r[k] for k in ('Path','Args','HostConfig','Config','Mounts','Image')})).hexdigest(),runtime={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')}) for r in rows}
operation='smallapp-a690233d967d4965bf5f861dc1126961'
failure=root/'repository-operations'/hashlib.sha256(operation.encode()).hexdigest()/'result.json'
terminal=json.loads(failure.read_bytes());need(terminal['state']=='FAILED_RETAINED' and terminal['actualExitCode']==1 and terminal['failureCode']=='MINIMAL_BINLOG_TOOL_CHANGED','ORIGINAL_NOT_TERMINAL')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in cmd:need(b'control_entry.py' in cmd,'ACTIVE_SOURCE_WORKER')
lock=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
need(pin(TOOL_PIN['path'])==TOOL_PIN,'TOOL_DOCUMENT_CHANGED');tool=json.loads(pathlib.Path(TOOL_PIN['path']).read_bytes());identity=tool['containerId']
row=json.loads(run(['docker','inspect',identity]))[0]
need(row['Id']==identity and row['Image']==tool['imageId'] and not row['State']['Running'] and row['Path']=='sleep' and row['Args']==['infinity'],'WRONG_ORIGINAL_TOOL')
need(row['HostConfig']['ReadonlyRootfs'] and row['HostConfig']['NetworkMode']=='container:'+MYSQL_ID and row['HostConfig']['PidMode']=='container:'+MYSQL_ID,'TOOL_ISOLATION_CHANGED')
need(json.loads(run(['docker','inspect',MYSQL_ID]))[0]['State']['Running'],'MYSQL_NOT_RUNNING')
fstab=pin('/etc/fstab');before=snapshot();originals={}
for directory in [root/'capture-staging'/operation,root/'repository-operations'/hashlib.sha256(operation.encode()).hexdigest(),root/'request-configurations'/operation]:
 for p in directory.rglob('*'):
  if p.is_file():need(not p.is_symlink(),'ORIGINAL_SYMLINK');originals[str(p)]=pin(p)
run(['docker','start',identity])
row=json.loads(run(['docker','inspect',identity]))[0];need(row['State']['Running'],'TOOL_NOT_RUNNING')
need(run(['docker','exec',identity,'sha256sum',tool['executable']]).decode().split()==[tool['sha256'],tool['executable']],'TOOL_EXECUTABLE_CHANGED')
version=run(['docker','exec',identity,tool['executable'],'--version']).decode().strip()
after=snapshot();need(set(after)==set(before),'CONTAINER_SET_CHANGED')
for key,old in before.items():
 need(old['definitionSha256']==after[key]['definitionSha256'],'ORIGINAL_DEFINITION_CHANGED')
 if key!=identity:need(old==after[key],'OTHER_RUNTIME_CHANGED')
need(pin('/etc/fstab')==fstab,'FSTAB_CHANGED')
need(all(pin(p)==reference for p,reference in originals.items()),'FAILED_ORIGINAL_CHANGED')
os.close(lock)
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host='172.30.30.57',containerId=identity,imageId=tool['imageId'],toolPin=TOOL_PIN,executableSha256=tool['sha256'],version=version,originalDefinitionUnchanged=True,otherRuntimePreserved=True,originalContainerCount=len(before),failedOriginalPins=list(originals.values()),failedOriginalFilesPreserved=len(originals),fstabPreserved=True,mainProgramRestarted=False,dockerRestarted=False,restartPolicyChanged=False)))
'''
if __name__=='__main__':
 value=json.loads((TASK/'incremental-364-failure.json').read_text(encoding='utf-8'));tool=value['tools'][0]
 assert tool['pinMatches'] and not tool['actualContainer']['state']['Running']
 out=remote('172.30.30.57','TOOL_PIN='+repr(tool['pin'])+'\nMYSQL_ID='+repr('9a288d20d254366e99b265b1870466e974edf23e7aab60de2391e3a38e62fff6')+'\n'+SCRIPT,120)
 write(TASK/'registered-binlog-tool-restored.json',out)
 print(json.dumps({k:v for k,v in out.items() if k!='failedOriginalPins'}))
