"""Read-only epoch-stage diagnosis; never initialize or query control APIs."""
import json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import hashlib,json,pathlib,stat,subprocess,datetime
def pin(path):
 path=pathlib.Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def run(argv,env=None):
 value=subprocess.run(argv,env=env,capture_output=True,timeout=30);assert value.returncode==0,'READ_ONLY_COMMAND_FAILED';return value.stdout
unit=C['service'];root=pathlib.Path(C['previousCustody']['root']);epoch_root=pathlib.Path(C['targetBackupEpochPolicy']['root'])
pid=int(run(['systemctl','show',unit,'-p','MainPID']).decode().strip().split('=',1)[1])
argv=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
control_pin=json.loads(argv[argv.index('--config-pin')+1]);assert pin(control_pin['path'])==control_pin
control=json.loads(pathlib.Path(control_pin['path']).read_bytes());owner_pin=control['restoreConfigurations'][SOURCE][C['targetConfigRef']]
assert pin(owner_pin['path'])==owner_pin;owner=json.loads(pathlib.Path(owner_pin['path']).read_bytes());target=owner['targets'][C['targetConfigRef']]
packages=[]
for engine in (pathlib.Path(owner['formalModuleDirectory']).parent,pathlib.Path(C['engine'])):
 manifest=json.loads((engine/'package.json').read_bytes());assert all(pin(engine/name)['sha256']==sha for name,sha in manifest['files'].items())
 packages.append(dict(engine=str(engine),packagePin=pin(engine/'package.json'),fileCount=len(manifest['files']),allMembersMatch=True))
roles={}
for service in target['services']:
 rows=json.loads(run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',service['id']]))
 assert len(rows)==1 and rows[0]['Id']==service['id'];row=rows[0]
 roles[service['role']]={key:row[key] for key in ('Id','Image','State','Mounts')}
for ref in C['retainedHistoryPins']:assert pin(ref['path'])==ref,'RETAINED_HISTORY_CHANGED'
epoch_entries=[]
if epoch_root.exists():
 for path in sorted(epoch_root.rglob('*')):
  info=path.lstat();assert not stat.S_ISLNK(info.st_mode)
  epoch_entries.append(dict(path=str(path),mode=stat.S_IMODE(info.st_mode),pin=pin(path) if path.is_file() else None))
probe=r"""import json,sys,traceback
from recovery_replace import replacement_value
from recovery_backup_epoch import validate_policy,read_current
owner,target,policy=json.loads(sys.argv[1]);out={}
for name,call in [('replacement_value',lambda:replacement_value(owner,target)),('validate_policy',lambda:validate_policy(policy)),('read_current',lambda:read_current(policy))]:
 try:
  value=call();out[name]=dict(status='PASS',value=value if name=='read_current' else None)
 except Exception as e:out[name]=dict(status='FAIL',exceptionType=type(e).__name__,message=str(e),traceback=traceback.format_exc())
print(json.dumps(out))
"""
phases=json.loads(run([C['control']['pythonPin']['path'],'-B','-c',probe,json.dumps([C['owner'],C['targetConfigRef'],C['targetBackupEpochPolicy']])],env=C['control']['environment']))
stage={name:dict(exists=pathlib.Path(ref['path']).exists(),actualPin=pin(ref['path']) if pathlib.Path(ref['path']).is_file() else None) for name,ref in (
 ('candidateOwner',C['ownerConfigurationPin']),('candidateControl',C['controlConfigurationPin']),('previousReceiptArchive',C['previousReceiptPin']))}
dropins=[]
for base in ('/etc/systemd/system','/run/systemd/system','/usr/lib/systemd/system','/lib/systemd/system'):
 dropins.extend(pin(p) for p in (pathlib.Path(base)/(unit+'.d')).glob('*automatic-0d44578*.conf'))
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=C['host'],pid=pid,controlPin=control_pin,ownerPin=owner_pin,
 actualReceiptPin=pin(root/'target-installation.json'),packages=packages,roles=roles,epochRoot=str(epoch_root),epochRootExists=epoch_root.exists(),
 epochRootMode=stat.S_IMODE(epoch_root.stat().st_mode) if epoch_root.exists() else None,epochEntries=epoch_entries,readonlyPhases=phases,
 stage=stage,newDropins=dropins,allRetainedPinsMatch=True,retainedCount=len(C['retainedHistoryPins']),serverWrites=False,noControlApiCalled=True,noLedgerCalled=True)))
'''

if __name__=='__main__':
    candidate=json.loads((PRIVATE/'automatic-target-candidate-59-0d44578.private.json').read_text(encoding='utf-8'))
    value=remote('172.30.30.59','C='+repr(candidate)+'\nSOURCE='+repr('intruoyi-57-safe-20261024-v1')+'\n'+SCRIPT,timeout=120)
    write(PRIVATE/'automatic-target59-epoch-stage-failure.private.json',value)
    old=json.loads((PRIVATE/'automatic-target-closure-59.private.json').read_text(encoding='utf-8'))
    states=('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')
    public={k:v for k,v in value.items() if k not in ('roles','readonlyPhases')}
    public['rolesComparedWithPriorObservation']={role:dict(sameId=row['Id']==old['services'][role]['Id'],sameImage=row['Image']==old['services'][role]['Image'],
        sameMounts=sorted(row['Mounts'],key=lambda x:x['Destination'])==sorted(old['services'][role]['Mounts'],key=lambda x:x['Destination']),
        sameState=all(row['State'][k]==old['services'][role]['State'][k] for k in states),status=row['State']['Status']) for role,row in value['roles'].items()}
    public['readonlyPhases']={name:{k:v for k,v in row.items() if k not in ('traceback','value')} for name,row in value['readonlyPhases'].items()}
    write(TASK/'automatic-target59-epoch-stage-failure.json',public)
    print(json.dumps(public,ensure_ascii=False))
