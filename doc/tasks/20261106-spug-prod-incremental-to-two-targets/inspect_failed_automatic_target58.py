"""Read-only post-failure observation; never calls mutating query/reconcile APIs."""
import json
from common import PRIVATE, TASK, remote, write

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess
def pin(path):
 p=pathlib.Path(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):
 assert pin(ref['path'])==ref,'PIN_CHANGED';return json.loads(pathlib.Path(ref['path']).read_bytes())
def command(argv):
 result=subprocess.run(argv,capture_output=True,timeout=30);assert result.returncode==0,'READ_ONLY_COMMAND_FAILED';return result.stdout
root=pathlib.Path(C['previousCustody']['root']);unit=C['service']
raw=command(['systemctl','show',unit,'-p','MainPID']).decode().strip();assert raw.startswith('MainPID=');pid=int(raw.split('=',1)[1])
argv=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
actualpin=json.loads(argv[argv.index('--config-pin')+1]);control=read(actualpin)
ownerpin=control['restoreConfigurations'][SOURCE][C['targetConfigRef']];owner=read(ownerpin);target=owner['targets'][C['targetConfigRef']]
oldengine=pathlib.Path(owner['formalModuleDirectory']).parent
def package_state(folder):
 folder=pathlib.Path(folder);manifest=json.loads((folder/'package.json').read_bytes())
 matches=all(pin(folder/name)['sha256']==sha for name,sha in manifest['files'].items())
 return dict(engine=str(folder),packagePin=pin(folder/'package.json'),fileCount=len(manifest['files']),allMembersMatch=matches)
roles={}
for service in target['services']:
 values=json.loads(command([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',service['id']]))
 assert len(values)==1 and values[0]['Id']==service['id'];item=values[0]
 roles[service['role']]={key:item[key] for key in ('Id','Image','Mounts','State')}
retained=[]
for ref in C['retainedHistoryPins']:
 actual=pin(ref['path']);assert actual==ref,'RETAINED_ORIGINAL_CHANGED';retained.append(actual)
queries=[]
for path in pathlib.Path(control['ledgerRoot']).glob('*/queries/*.json'):
 if path.stat().st_mtime < SINCE:continue
 value=json.loads(path.read_bytes());refs=[]
 for name in ('ownerResultPin','resolutionPins'):
  selected=value.get(name,[]);selected=selected if isinstance(selected,list) else [selected]
  for ref in selected:
   if isinstance(ref,dict) and set(('path','bytes','sha256'))<=set(ref):
    refs.append(dict(field=name,pin=ref,matches=pin(ref['path'])==ref))
 queries.append(dict(pin=pin(path),mtime=path.stat().st_mtime,document=value,references=refs))
constructor=root/'configuration'/'constructor-preactivation-automatic-0d44578'/'constructor-verification.json'
proof=json.loads(constructor.read_bytes()) if constructor.exists() else None
constructor_native=[]
if proof:
 for ref in proof['nativeInvocationPins']:
  document=read(ref);constructor_native.append(dict(pin=ref,mutation=document['mutation'],actualExitCode=document['actualExitCode']))
dropins=[]
for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system','/lib/systemd/system'):
 folder=pathlib.Path(base)/(unit+'.d')
 if folder.exists():dropins.extend(pin(path) for path in folder.glob('*automatic-0d44578*.conf'))
stage={name:dict(exists=pathlib.Path(ref['path']).exists(),actualPin=pin(ref['path']) if pathlib.Path(ref['path']).exists() else None,expectedPin=ref) for name,ref in (
 ('candidateOwner',C['ownerConfigurationPin']),('candidateControl',C['controlConfigurationPin']),('oldOwner',C['oldOwnerPin']),('oldControl',C['oldControlPin']),
 ('activeReceipt',C['oldActiveReceiptPin']),('previousReceiptArchive',C['previousReceiptPin']))}
stage['previousUnitExists']=(root/'configuration'/'automatic-0d44578-previous-unit.txt').exists()
stage['newReceiptTemporaryExists']=(root/'target-installation.automatic-0d44578.tmp').exists()
stage['completedInstallationExists']=(root/'configuration'/'installation-automatic-0d44578.json').exists()
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=C['host'],unit=unit,pid=pid,argv=argv,controlPin=actualpin,ownerPin=ownerpin,
 oldPackage=package_state(oldengine),stagedPackage=package_state(C['engine']),stage=stage,newDropins=dropins,roles=roles,
 retainedOriginalCount=len(retained),allRetainedOriginalPinsMatch=True,queriesSinceCutoff=queries,cutoff=SINCE,
 constructorEvidencePin=pin(constructor) if proof else None,constructorEvidence=proof,constructorNativeInvocations=constructor_native,
 activeReservationExists=pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),
 fstabPin=pin('/etc/fstab'),mountinfo=pathlib.Path('/proc/self/mountinfo').read_text(),
 noControlQueryExecuted=True,serverWrites=False)
print(json.dumps(out))
'''

if __name__ == '__main__':
    candidate=json.loads((PRIVATE/'automatic-target-candidate-58-0d44578.private.json').read_text(encoding='utf-8'))
    script='C='+repr(candidate)+'\nSOURCE='+repr('intruoyi-57-safe-20261024-v1')+'\nSINCE=1794074400\n'+SCRIPT
    result=remote('172.30.30.58',script,timeout=180)
    write(PRIVATE/'automatic-target58-failed-activation-diagnosis.private.json',result)
    old=json.loads((PRIVATE/'automatic-target-closure-58.private.json').read_text(encoding='utf-8'))
    states=('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')
    roles={role:dict(sameId=row['Id']==old['services'][role]['Id'],sameImage=row['Image']==old['services'][role]['Image'],
        sameMounts=sorted(row['Mounts'],key=lambda x:x['Destination'])==sorted(old['services'][role]['Mounts'],key=lambda x:x['Destination']),sameState=all(row['State'][k]==old['services'][role]['State'][k] for k in states),status=row['State']['Status']) for role,row in result['roles'].items()}
    public={key:result[key] for key in ('observedAt','host','unit','pid','controlPin','ownerPin','oldPackage','stagedPackage','stage','newDropins','retainedOriginalCount','allRetainedOriginalPinsMatch','activeReservationExists','constructorEvidencePin','constructorNativeInvocations','noControlQueryExecuted','serverWrites')}
    public['rolesComparedWith173744Utc']=roles
    public['queriesSince1800Utc']=[dict(pin=q['pin'],mtime=q['mtime'],operationId=q['document'].get('operationId'),observedAt=q['document'].get('observedAt'),keys=list(q['document']),resultState=q['document'].get('result',{}).get('state'),referencesMatch=all(r['matches'] for r in q['references'])) for q in result['queriesSinceCutoff']]
    public['originalAttemptTreeSnapshotUnavailable']=True
    write(TASK/'automatic-target58-failed-activation-diagnosis.json',public)
    print(json.dumps(public,ensure_ascii=False))
