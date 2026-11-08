"""Read-only actual MAIN ownership and exact archive-chain admission."""
import argparse,json
from common import PRIVATE,SOURCE,TASK,remote,write,restore_kind,allocator_installation,restore_clearance

SCRIPT=r'''
import datetime,hashlib,json,os,pathlib,subprocess,sys,urllib.request
from types import SimpleNamespace
root=pathlib.Path(ROOT)
def need(value,code):
 if not value:raise ValueError(code)
def pin(path):
 path=pathlib.Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(reference):need(pin(reference['path'])==reference,'CONFIGURATION_PIN_CHANGED');return json.loads(pathlib.Path(reference['path']).read_bytes())
def run(args,raw=None):
 p=subprocess.run(args,input=raw,capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError('READONLY_COMMAND_FAILED:'+p.stderr.decode('utf-8',errors='replace')[:240])
 return p.stdout
receipt=json.loads((root/'target-installation.json').read_bytes());owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
targetref=receipt['targetConfigRef'];target=owner['targets'][targetref]
need(targetref=='intruoyi-main-'+SUFFIX+'-safe-restore-20261104-v1','WRONG_TARGET')
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_target import verify_runtime
from recovery_replacement_storage import verify_storage
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
from formal_data_evidence import validate_limits
native_control=Native(receipt['controlConfigurationPin']);need(native_control.configuration()==control,'CONTROL_INVALID')
validate_limits(owner['dataLimits'])
rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
if RETAINED_CLEARANCE is not None:
 need(SUFFIX=='58' and ALLOCATOR_INSTALL is not None,'RETAINED_TARGET_SCOPE_INVALID')
 from recovery_retained_retry import validate_clearance,observe
 clearance=read(RETAINED_CLEARANCE['clearancePin'])
 claim=pathlib.Path(target['replacement']['stateRoot'])/clearance['operationId']
 need(validate_clearance(target,claim)==clearance and not (claim/'recovery-consumption.json').exists(),'CLEARANCE_NOT_AVAILABLE')
 need(clearance['targetConfigRef']==targetref and clearance['recoveryPointRef']==NEW_POINT,'CLEARANCE_SCOPE_CHANGED')
 oldroot=root/'recovery-operations'/clearance['operationId']
 original=json.loads((oldroot/'configuration.json').read_bytes());oldrequest=json.loads((oldroot/'request.json').read_bytes())
 need(original['targets']==owner['targets'],'RETAINED_TARGET_CHANGED')
 observe(original,oldrequest,oldroot,885)
else:
 need(all(r['State']['Running'] and not r['State']['Paused'] and not r['State']['Restarting'] for r in rows.values()),'ORIGINAL_NOT_RUNNING')
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},snapshots={},source=owner['sources'][SOURCE],root=root/'recovery-operations',inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity),docker=lambda args:run(['docker',*args]))
verify_runtime(native,states=False);verify_storage(native,target['replacement'],rows)
from recovery_main_health import preflight as health_preflight
native.frontend_readiness=owner.get('frontendReadiness',{}).get(targetref)
health_preflight(native)
engine=pathlib.Path(owner['formalModuleDirectory']).parent;version=json.loads((engine/'package.json').read_bytes())
need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_ENGINE_REQUIRED')
need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'ENGINE_CHANGED')
if ALLOCATOR_INSTALL is not None:
 need(receipt['sourceCommit']==ALLOCATOR_INSTALL['sourceCommit'] and str(engine)==ALLOCATOR_INSTALL['engine'] and
  receipt['ownerConfigurationPin']==ALLOCATOR_INSTALL['ownerConfigurationPin'] and
  receipt['controlConfigurationPin']==ALLOCATOR_INSTALL['controlConfigurationPin'] and
  version['packageSha256']==ALLOCATOR_INSTALL['fileManifestSha256'],'ALLOCATOR_INSTALLATION_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
workers=[]
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:command=(process/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in command:need(b'control_entry.py' in command,'ACTIVE_TARGET_WORKER');workers.append(int(process.name))
pid=int(run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip().split('=',1)[1])
limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_INVALID')
secretpin=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'];need(pin(secretpin['path'])==secretpin,'MYSQL_SECRET_CHANGED')
secret=pathlib.Path(secretpin['path']).read_bytes();need(secret and not any(c in secret for c in (b'\n',b'\r',b'\0')),'MYSQL_SECRET_INVALID')
sql='SELECT @@server_uuid,@@version,@@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;'
flags=run(['docker','exec','-i',rows['mysql']['Id'],'sh','-ec','IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"','read-only-admission','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],secret+b'\n').decode().strip().split('\t')
need(flags[0]==target['replacement']['databaseUuid'] and flags[3:]==['0','0'],'TARGET_DATABASE_STATE_CHANGED')
request=dict(sourceConfigRef=SOURCE,recoveryPointRef=POINT)
admitted=source_admits(native_control,owner['sources'][SOURCE],request)
resolved,binding=bind_archive_chain(owner['sources'][SOURCE],request)
need(POINT in admitted,'POINT_NOT_ADMITTED')
need(binding['pointPin']['sha256']==EXPECTED_POINT_SHA,'POINT_CHANGED')
need(len(resolved['repositoryPointPins'])==EXPECTED_CHAIN_LENGTH,'WRONG_CHAIN')
canonical_archive=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
mount=[line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(canonical_archive)]
need(len(mount)==1 and 'ro' in mount[0].split()[5].split(',') and ' - cifs //172.30.30.4/IT共享 ' in mount[0],'CANONICAL_ARCHIVE_NOT_RO')
need(hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest()==EXPECTED_FSTAB,'FSTAB_CHANGED')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
if RETAINED_CLEARANCE is None:
 with opener.open('http://'+next(s['ip'] for s in target['services'] if s['role']=='backend')+':48081/actuator/health',timeout=12) as response:need(json.load(response)['status']=='UP','BACKEND_NOT_UP')
 with opener.open('http://172.30.30.'+SUFFIX+':'+('38081' if SUFFIX=='59' else '8081')+'/',timeout=12) as response:need(response.status==200,'FRONTEND_NOT_READY')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
with opener.open(urllib.request.Request('http://127.0.0.1:'+str(control['listenPort'])+'/selections?targetConfigRef='+targetref,headers=headers),timeout=90) as response:
 need(response.status==200,'TARGET_ADMISSION_HTTP');document=json.load(response)
need(targetref in next(a for a in document['applications'] if a['sourceConfigRef']==SOURCE)['freshTargetConfigRefs'],'TARGET_NOT_ADMITTED')
free=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize;need(free>80*1024**3,'TARGET_CAPACITY_BELOW_80GIB')
memory={k:int(v.strip().split()[0])*1024 for k,v in (line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())}
if EXPECTED_RAW_SQL_BYTES is not None:
 need(memory['MemAvailable']>EXPECTED_RAW_SQL_BYTES+4*1024**3,'TARGET_NATIVE_SQL_MEMORY_HEADROOM_REQUIRED')
 need(EXPECTED_RAW_SQL_BYTES+1024*1024<owner['maxExpandedBytes'],'TARGET_NATIVE_SQL_EXPANDED_BUDGET_REQUIRED')
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host='172.30.30.'+SUFFIX,sourceConfigRef=SOURCE,targetConfigRef=targetref,recoveryPointRef=POINT,pointPin=binding['pointPin'],orderedChainPins=resolved['repositoryPointPins'],archiveEvidencePinsChecked=len(binding['evidencePins']),ownerConfigurationPin=receipt['ownerConfigurationPin'],controlConfigurationPin=receipt['controlConfigurationPin'],dataLimits=owner['dataLimits'],maxExpandedBytes=owner['maxExpandedBytes'],packageFileCount=len(version['files']),packageFilesMatch=True,runtimeAndStorageVerified=True,canonicalArchiveReadOnly=True,backendHealth='UP',frontendHttp=200,targetFreeBytes=free,activeReservation=False,liveMaxOpenFiles=65536,database=dict(uuid=flags[0],version=flags[1],eventScheduler=flags[2],readOnly=flags[3],superReadOnly=flags[4]),services=[dict(role=role,id=r['Id'],image=r['Image'],startedAt=r['State']['StartedAt']) for role,r in rows.items()])
out['nativeSqlMemoryHeadroom']=dict(availableBytes=memory['MemAvailable'],rawIncrementalSqlBytes=EXPECTED_RAW_SQL_BYTES,reservedOtherBytes=4*1024**3,verified=EXPECTED_RAW_SQL_BYTES is not None)
out['retainedQuiescedAdmission']=RETAINED_CLEARANCE is not None
if RETAINED_CLEARANCE is not None:
 out['backendHealth']=None;out['frontendHttp']=None;out['retainedClearancePin']=RETAINED_CLEARANCE['clearancePin']
print(json.dumps(out))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);parser.add_argument('--new-point',action='store_true');parser.add_argument('--allocator',action='store_true');args=parser.parse_args()
 if args.new_point:
  point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'));pointref=point['operationId'];sha=point['pointPin']['sha256'];length=len(point['parentPointPins'])+1;phase='new-point';raw_sql_bytes=point['database']['rawSqlBytes']
 else:pointref='smallapp-73cd541a95d84d6a86f9d693e4053c75';sha='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128';length=1;phase='rollback-point';raw_sql_bytes=None
 baseline=json.loads((TASK/('pre-install-'+args.suffix+'.json')).read_text(encoding='utf-8'))
 variables=dict(ROOT=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',SOURCE=SOURCE,SUFFIX=args.suffix,POINT=pointref,EXPECTED_POINT_SHA=sha,EXPECTED_CHAIN_LENGTH=length,EXPECTED_FSTAB=baseline['fstabSha256'],EXPECTED_RAW_SQL_BYTES=raw_sql_bytes)
 variables.update(RETAINED_CLEARANCE=None,ALLOCATOR_INSTALL=None,NEW_POINT=None)
 destination=TASK/('target-'+phase+'-admission-'+(restore_kind(args.suffix) if args.allocator else args.suffix)+'.json')
 assert not destination.exists(),'ADMISSION_ALREADY_RECORDED'
 if args.allocator:
  variables['ALLOCATOR_INSTALL']=allocator_installation(args.suffix)
  assert variables['ALLOCATOR_INSTALL']['status']=='PASS'
  if args.suffix=='58':
   variables['RETAINED_CLEARANCE']=restore_clearance(args.suffix)
   variables['NEW_POINT']=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf8'))['operationId']
   assert variables['RETAINED_CLEARANCE']['status']=='PASS' and variables['RETAINED_CLEARANCE']['writersRemainStopped']
 value=remote('172.30.30.'+args.suffix,'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,240)
 write(destination,value);print(json.dumps(value))
