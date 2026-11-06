"""Append a committed MAIN/v2 generation; preserve all original businesses."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from inspect_prod import TASK, PRIVATE, ROOT, HOST
sys.path.insert(0, str(TASK.parent/'20261104-spug-prod-full-to-test'))
from repair_preflight import SSH

COMMIT=None
ENGINE=None
PYTHON='/usr/local/libexec/spug-source-control-20261105/python/bin/python3.12'
DEPENDENCIES='/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/runtime/lib/python3.12/site-packages'
APP='intruoyi-57-safe-20261024-v1'
TARGET='intruoyi-main-57-safe-restore-20261105-v2'
POINT='smallapp-73cd541a95d84d6a86f9d693e4053c75'
UNIT='spug-main-restore-57-20261105-v2.service'
LOCK='/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock'

def remote(script, timeout=100):
    p=subprocess.run(SSH+['root@'+HOST,PYTHON+' -B -'],input=script.encode('utf-8'),capture_output=True,timeout=timeout)
    if p.returncode:
        failure=p.stdout+p.stderr
        (PRIVATE/('control-installation-error-'+hashlib.sha256(failure).hexdigest()[:12]+'.private.log')).write_bytes(failure)
        (PRIVATE/'control-installation-error.private.log').write_bytes(failure)
        raise RuntimeError('PROD_CONTROL_INSTALLATION_FAILED_SEE_PRIVATE_LOG')
    return json.loads(p.stdout)

COMMON=r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,socket,stat,subprocess,sys,tarfile
root=pathlib.Path(ROOT);engine=pathlib.Path(ENGINE)
generation='mainv2-'+COMMIT[:7]
def need(v,code):
 if not v:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def pin(p):
 p=pathlib.Path(p);data=p.read_bytes();return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def write(p,value,raw=False):
 p=pathlib.Path(p);data=value if raw else canonical(value)
 need(p.is_absolute() and p.parent.resolve()==p.parent,'INSTALL_PATH_INVALID')
 if p.exists():need(p.read_bytes()==data,'INSTALL_EXISTING_FILE_CONFLICT');return pin(p)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 need(p.read_bytes()==data,'INSTALL_READBACK_FAILED');return pin(p)
def run(args,raw=None,timeout=20):
 p=subprocess.run(args,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 need(p.returncode==0,'INSTALL_COMMAND_FAILED');return p.stdout
def docker(args,**kw):return run(['/usr/bin/docker','--host','unix:///var/run/docker.sock',*args],kw.get('input_bytes'))
def allrows():return json.loads(docker(['inspect',*docker(['ps','-aq','--no-trunc']).decode().split()]))
def business(rows):return {r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},configDigest=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def inspect(identity):return json.loads(docker(['inspect',identity]))[0]
need(root.resolve()==root and root.is_dir(),'STAGED_ROOT_INVALID')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
need(not (root/'target-installation.json').exists(),'TARGET_ALREADY_INSTALLED')
need(not list((root/'replacement-state').iterdir()),'EXISTING_REPLACEMENT_STATE')
before=business(allrows());fstab=pin('/etc/fstab');oldstage=pin(root/'installation.json')
sourcecontrol=json.loads(pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/control-postboot-20261105.json').read_bytes())
need(pin(sourcecontrol['pythonPin']['path'])==sourcecontrol['pythonPin'],'PYTHON_PIN_CHANGED')
fd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
'''

STAGE=r'''
need(not engine.exists(),'ENGINE_GENERATION_EXISTS')
raw=base64.b64decode(PACKAGE);need(hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED')
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 version=json.load(archive.extractfile('package.json'));names=archive.getnames()
 need(version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification'],'SAFE_REQUIRED')
 need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
 need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256'],'PACKAGE_MANIFEST_CHANGED')
 for item in archive.getmembers():
  need(item.isfile() and not pathlib.PurePosixPath(item.name).is_absolute() and '..' not in pathlib.PurePosixPath(item.name).parts,'PACKAGE_PATH_INVALID')
  data=archive.extractfile(item).read()
  if item.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][item.name],'PACKAGE_CONTENT_CHANGED');compile(data,item.name,'exec')
 engine.mkdir(mode=0o700)
 for item in archive.getmembers():
  path=engine/item.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);write(path,archive.extractfile(item).read(),raw=True)
need(business(allrows())==before and pin('/etc/fstab')==fstab and pin(root/'installation.json')==oldstage,'ORIGINAL_RUNTIME_CHANGED')
out=dict(status='PASS',sourceCommit=COMMIT,packageSha256=PACKAGE_SHA,fileManifestSha256=version['packageSha256'],fileCount=len(version['files']),engine=str(engine),originalBusinessCount=len(before),originalRuntimePreserved=True,oldStagePreserved=True,fstabPreserved=True,restorePerformed=False)
write(root/'configuration'/(generation+'-components.json'),out);os.close(fd);print(json.dumps(out))
'''

CONFIGURE=r'''
sys.path[:0]=[str(engine/'control'),str(engine/'common'),str(engine/'formal'),DEPENDENCIES]
from recovery_engine import digest
from recovery_replacement_storage import snapshot_retained_storage,overlaps,physical_location,_same_storage,parse_mountinfo
from recovery_main_target import capture_main_application,application_inputs,observe_main_target,archive_view
from recovery_published_fence import PublishedFence
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
from recovery_resource_admission import check_budget,observe_resources
from formal_data_evidence import validate_limits
from types import SimpleNamespace
version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'ENGINE_DRIFT')
rows={r:inspect(name) for r,name in NAMES.items()}
for role,row in rows.items():
 need(row['Id']==EXPECTED[role]['id'] and row['Image']==EXPECTED[role]['image'],'ORIGINAL_SERVICE_IDENTITY_CHANGED')
 need(row['State']['Running'] and not row['State']['Paused'] and not row['State']['Restarting'],'ORIGINAL_SERVICE_NOT_RUNNING')
env={role:dict(e.split('=',1) for e in row['Config']['Env'] if '=' in e) for role,row in rows.items()}
def query(sql):
 return docker(['exec','-i',rows['mysql']['Id'],'sh','-ec','IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"','main-registration','mysql','--no-defaults','--batch','--skip-column-names','-e',sql],input_bytes=(env['mysql']['MYSQL_ROOT_PASSWORD']+'\n').encode()).decode()
uuid,logbin=query('SELECT @@server_uuid,@@GLOBAL.log_bin;').strip().split('\t')
need(uuid=='0fa6c22b-5a90-11f1-ade1-0242ac150002' and logbin=='1','DATABASE_IDENTITY_CHANGED')
need(docker(['exec',rows['redis']['Id'],'redis-cli','--raw','CONFIG','GET','requirepass'])==b'requirepass\n\n','REDIS_AUTHENTICATION_CHANGED')
acl=docker(['exec',rows['redis']['Id'],'redis-cli','--raw','ACL','LIST'])
minioroot=pathlib.Path(next(m['Source'] for m in rows['minio']['Mounts'] if m['Destination']=='/data'))
iam=minioroot/'.minio.sys/config/iam'
identities={str(p.relative_to(iam)):{str(f.relative_to(iam)):hashlib.sha256(f.read_bytes()).hexdigest() for f in ([p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file()))} for section in ('users','service-accounts') for p in (iam/section).glob('*/identity.json')}
policies={str(p.relative_to(iam)):hashlib.sha256(p.read_bytes()).hexdigest() for section in ('policies','policydb') for p in (iam/section).rglob('*') if p.is_file()}
need(identities==WRITERS['iamIdentityPins'] and policies==WRITERS['iamPolicyPins'],'IAM_IDENTITY_CHANGED')
need(set(identities)=={'users/'+n+'/identity.json' for n in ('EDHRUCQZT8LNMQMKRFZK','EDHRHFRQFGCXYATNNSC6','EDHRCJSBJZZDMENUJE6R')},'UNKNOWN_IAM_WRITER')
source=copy.deepcopy(TEMPLATE['sources'][APP]);archive=pathlib.Path(source['archiveRoots'][0])
mounts=parse_mountinfo(pathlib.Path('/proc/self/mountinfo').read_text())
view=next(m for m in mounts if m['mountPoint']=='/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
need('rw' in view['options'] and 'ro' not in view['options'] and view['filesystem']=='cifs','ARCHIVE_VIEW_UNEXPECTED')
archive_protection=dict(schemaVersion='RegisteredArchiveViewProtection/v1',mountIdentity=view,mountProgramPin=pin(pathlib.Path('/usr/bin/mount').resolve()))
sourceheaders=json.loads(pathlib.Path(sourcecontrol['authCredentialRef']['path']).read_bytes())
authpin=write(root/'private/mainv2-source-headers.json',sourceheaders)
access=write(root/'configuration/mainv2-source-access.json',dict(schemaVersion='SmallAppSourceCatalogueAccess/v1',selectionUrl='http://127.0.0.1:32657/selections',authCredentialRef=dict(path=authpin['path'],uid=0,gid=0,mode=0o600),applicationId=APP,engineSelectionRef=sourcecontrol['engineSelectionRef']))
source['archiveCatalogue']['sourceAdmissionPin']=access
ips={role:next(a['IPAddress'] for a in row['NetworkSettings']['Networks'].values() if a['IPAddress']) for role,row in rows.items()}
ips['minio']='127.0.0.1'
target=copy.deepcopy(next(iter(TEMPLATE['targets'].values())))
runtime=root/'runtime'
if not runtime.exists():runtime.mkdir(mode=0o700)
need(runtime.resolve()==runtime and runtime.is_dir() and not list(runtime.iterdir()),'RUNTIME_NOT_EMPTY')
target.update(targetId='intruoyi-main-prod57-20261105',sourceConfigRef=APP,machineId=pathlib.Path('/etc/machine-id').read_text().strip(),dockerEngineId=json.loads(docker(['info','--format','{{json .}}']))['ID'],dockerPin=pin('/usr/bin/docker'),dataRoot=str(runtime),dataPaths=[m['Source'] for role,row in rows.items() if role in ('mysql','minio','redis') for m in row['Mounts'] if m['RW']],networkId=rows['backend']['NetworkSettings']['Networks']['intruoyi-runtime_intruoyi_net']['NetworkID'],services=[dict(role=r,id=v['Id'],imageId=v['Image'],ip=ips[r]) for r,v in rows.items()])
target['iptablesPin']=pin(pathlib.Path('/usr/sbin/iptables').resolve())
target['secrets']={}
for role,fields in {'mysql':['MYSQL_ROOT_PASSWORD'],'minio':['MINIO_ROOT_USER','MINIO_ROOT_PASSWORD']}.items():
 target['secrets'][role]={field:write(root/'private'/('mainv2-'+role+'-'+field.lower()),env[role][field].encode(),raw=True) for field in fields}
data=target['dataPaths'];locations=[physical_location(p,mounts) for p in data];inactive=[]
for row in allrows():
 if row['Id'] in {r['Id'] for r in rows.values()}:continue
 if any(m.get('RW') and any(overlaps(m['Source'],p) or _same_storage(physical_location(m['Source'],mounts),loc) for p,loc in zip(data,locations)) for m in row['Mounts']):
  need(not row['State']['Running'],'FOREIGN_ACTIVE_DATA_CONSUMER');inactive.append(row)
target['replacement']=dict(schemaVersion='RegisteredApplicationReplacement/v2',stateRoot=str(root/'replacement-state'),lockPath=LOCK,databaseUuid=uuid,services={role:dict(id=r['Id'],imageId=r['Image'],labels=r['Config']['Labels'],mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])) for role,r in rows.items()},storage=snapshot_retained_storage(rows,['/mnt/nas',str(archive),str(root)],inactive))
writer=dict(schemaVersion='RegisteredMainWriterEvidence/v1',database=target['database'],redisDatabase=1,objectBuckets=target['buckets'],writerContainerIds=[rows['backend']['Id']],exclusiveResources=dict(database=True,objects=True,redis=True))
writerpin=write(root/'configuration/mainv2-writer-evidence.json',writer)
evidence=dict(schemaVersion='ProductionMainWriterInspection/v1',accountAttestation='user-confirmation-20261104: these exact accounts are exclusive to IntRuoyi',identities=identities,policyPins=policies,otherConfigurationInspection=WRITERS['referencedEndpoints'],inactiveConsumerIds=[r['Id'] for r in inactive],sourceLockPath=LOCK)
evidencepin=write(root/'configuration/mainv2-writer-inspection.json',evidence)
networkids=sorted({a['NetworkID'] for r in rows.values() for a in r['NetworkSettings']['Networks'].values()})
networks=[json.loads(docker(['network','inspect',n]))[0] for n in networkids]
configurationpins=[pin(m['Source']) for role,row in rows.items() if role not in ('mysql','minio','redis') for m in row['Mounts'] if not m['RW'] and pathlib.Path(m['Source']).is_file()]
program=pathlib.Path('/usr/sbin/iptables').resolve();ip6=pathlib.Path('/usr/sbin/ip6tables').resolve()
fence=dict(schemaVersion='PublishedHostWriteFence/v1',ports=[9000,9001],allowedWriterIPv4=[ips['backend']],programs=dict(ipv4=dict(pin=pin(program),applet='iptables'),ipv6=dict(pin=pin(ip6),applet='ip6tables')))
published=[dict(role='minio',ip='127.0.0.1',port=9000,containerPort='9000/tcp',bindings=rows['minio']['HostConfig']['PortBindings'],writeFence=fence)]
target['mainApplication']=capture_main_application(target,rows,networks,[dict(role=role,versionPath=['images','intruoyi-'+role],imageId=rows[role]['Image']) for role in ('backend','frontend')],configurationpins,writerpin,redis_authentication=dict(mode='NONE',aclSha256=hashlib.sha256(acl).hexdigest()),published_data_endpoints=published)
target['mainApplication']['archiveMountProtection']=archive_protection
archive_view(SimpleNamespace(config=target,source=source,original=dict(operationId='installation-preflight'),command=lambda a,**kw:run(a))).preflight()
target['resourceBudget']=dict(schemaVersion='RestoreResourceBudget/v1',mysqlMemoryBytes=2147483648,hostAvailableMemoryBytes=2147483648,diskBytesByPath={str(root):68719476736,**{p:(34359738368 if p.endswith('/minio') else 8589934592) for p in data}})
owner=copy.deepcopy(TEMPLATE);owner.update(sources={APP:source},targets={TARGET:target},operationsRoot=str(root/'recovery-operations'),formalModuleDirectory=str(engine/'formal'),pythonPin=pin(PYTHON),maxExpandedBytes=68719476736,deadlineMilliseconds=21600000,dataLimits=dict(max_bytes=17179869184,max_nodes=100000000,max_rows=10000000,seconds=7200))
validate_limits(owner['dataLimits'])
ownerpin=write(root/'configuration'/('main-recovery-'+generation+'.json'),owner)
repositorypin=sourcecontrol['sourceConfigurations'][APP]
registration=dict(schemaVersion='ApplicationRegistration/v1',applicationId=APP,sourceConfigRef=APP,displayName='IntRuoyi 正式服备份',allowedRestoreTargets=[dict(configRef=TARGET)])
regpin=write(root/'configuration/mainv2-registration.json',registration);write(root/'registry/applications'/(APP+'.pin.json'),regpin)
authpin=write(root/'private/mainv2-control-headers.json',TARGET_HEADERS)
control=dict(schemaVersion='SmallAppExecutionServiceConfig/v2',taskRoot=str(root),ledgerRoot=str(root/'ledger'),registryRoot=str(root/'registry'),listenAddress='127.0.0.1',listenPort=43657,authCredentialRef=dict(path=authpin['path'],uid=0,gid=0,mode=0o600),allowedClientAddresses=['127.0.0.1'],pythonPin=pin(PYTHON),programPins={r:pin(engine/(r+'_entry.py')) for r in ('repository','recovery')},workingDirectory=str(root),environment=dict(PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',LANG='C.UTF-8',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=':'.join([str(engine/'control'),str(engine/'common'),str(engine/'formal'),DEPENDENCIES])),deadlineMilliseconds=21600000,engineSelectionRef=sourcecontrol['engineSelectionRef'],sourceConfigurations={APP:repositorypin},restoreConfigurations={APP:{TARGET:ownerpin}})
controlpin=write(root/'configuration'/('control-43657-'+generation+'.json'),control)
native=Native(controlpin);need(native.configuration()==control,'CONTROL_CONFIGURATION_INVALID')
request=dict(sourceConfigRef=APP,targetConfigRef=TARGET,recoveryPointRef=POINT,operationId='installation-preflight')
need(POINT in source_admits(native,source,request),'POINT_NOT_ADMITTED')
resolved,binding=bind_archive_chain(source,request)
need(binding['pointPin']['sha256']=='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128','SELECTED_POINT_CHANGED')
point=json.loads(pathlib.Path(binding['pointPin']['path']).read_bytes())
bindingdoc=json.loads(pathlib.Path(point['manifestPin']['path']).with_name('recovery-repository-binding.json').read_bytes());material=json.loads(pathlib.Path(bindingdoc['recoveryMaterialPin']['path']).read_bytes())
application_inputs(SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},material=material,inspect=inspect))
observation=observe_main_target(native,request,dict(ownerConfigurationPin=ownerpin))
PublishedFence(fence,'installation-preflight',root/'replacement-state/installation-preflight-fence',lambda a,**kw:run(a)).preflight()
resource=check_budget(target['resourceBudget'],observe_resources(owner,request,target['resourceBudget']))
hostroot=pathlib.Path('/var/lib/spug-restore-resources')
if not hostroot.exists():hostroot.mkdir(mode=0o700)
need(hostroot.resolve()==hostroot and stat.S_IMODE(hostroot.stat().st_mode)==0o700 and hostroot.stat().st_uid==0,'HOST_RESOURCE_CUSTODY_INVALID')
need(not (hostroot/'active.json').exists(),'ACTIVE_RESERVATION')
sock=socket.socket();sock.bind(('127.0.0.1',43657));sock.close()
unit=pathlib.Path('/etc/systemd/system')/UNIT;need(not unit.exists(),'UNIT_ALREADY_EXISTS')
unitdata=('[Unit]\nDescription=Spug production original MAIN restore control\nAfter=network.target docker.service\n[Service]\nType=simple\nUser=root\nUMask=0077\nLimitNOFILE=65536\nWorkingDirectory='+str(root)+'\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart='+PYTHON+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(controlpin).decode()+"'"+'\nRestart=on-failure\nRestartSec=5\n[Install]\nWantedBy=multi-user.target\n').encode()
need(business(allrows())==before and pin('/etc/fstab')==fstab and pin(root/'installation.json')==oldstage,'ORIGINAL_RUNTIME_CHANGED')
write(unit,unitdata,raw=True);run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',UNIT])
need(run(['systemctl','is-active',UNIT]).strip()==b'active','CONTROL_NOT_ACTIVE')
pid=int(run(['systemctl','show',UNIT,'-p','MainPID','--value']).strip())
limit=next(l for l in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if l.startswith('Max open files'))
need(limit.split()[3:5]==['65536','65536'],'CONTROL_FD_BUDGET_INVALID')
need(business(allrows())==before and pin('/etc/fstab')==fstab and pin(root/'installation.json')==oldstage,'ORIGINAL_RUNTIME_CHANGED')
receipt=dict(schemaVersion='SpugMainRestoreTargetInstallation/v1',host=HOST,targetConfigRef=TARGET,root=str(root),controlConfigurationPin=controlpin,ownerConfigurationPin=ownerpin,registrationPin=regpin,preflightEvidencePin=evidencepin,service=UNIT,state='INSTALLED_PENDING_LOCAL_ROUTE',sourceCommit=COMMIT,engine=str(engine),resourceAdmission=resource,archivePointRef=POINT,inactiveConsumerCount=len(inactive),preservedMountCount=len(target['replacement']['storage']['preservedApplicationMounts']),originalBusinessCount=len(before),originalRuntimePreserved=True,liveFdLimit=limit,restorePerformed=False)
write(root/'target-installation.json',receipt);os.close(fd);print(json.dumps(receipt))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['stage','configure']);parser.add_argument('--commit',required=True);args=parser.parse_args()
    COMMIT=args.commit
    if len(COMMIT)!=40 or any(c not in '0123456789abcdef' for c in COMMIT):raise ValueError('EXACT_COMMIT_REQUIRED')
    ENGINE=ROOT+'/engine-mainv2-'+COMMIT[:7]
    values=dict(ROOT=ROOT,ENGINE=ENGINE,HOST=HOST,COMMIT=COMMIT,PYTHON=PYTHON,DEPENDENCIES=DEPENDENCIES,APP=APP,TARGET=TARGET,POINT=POINT,UNIT=UNIT,LOCK=LOCK)
    if args.action=='stage':
        raw=(PRIVATE/('package-'+COMMIT[:7])/'backup-restore-standard.tgz').read_bytes()
        values.update(PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=hashlib.sha256(raw).hexdigest())
        body=STAGE
    else:
        template=json.loads(Path('C:/Spug/runtime/private/prod-full-to-review-20261105/original-runtime-baseline.private.json').read_text(encoding='utf-8'))['documents']['owner']
        original=json.loads((PRIVATE/'original-production.private.json').read_text(encoding='utf-8'))
        names=dict(mysql='/intruoyi-mysql',minio='/ragflow_compose-minio-1',redis='/intruoyi-redis',backend='/intruoyi-backend',frontend='/intruoyi-frontend')
        expected={role:dict(id=r['Id'],image=r['Image']) for role,name in names.items() for r in original['containers'] if r['Name']==name}
        auth=PRIVATE/'target-control-headers.private.json'
        if not auth.exists():
            import secrets
            auth.write_text(json.dumps(dict(headers=dict(Authorization='Bearer '+secrets.token_urlsafe(40)))),encoding='utf-8')
        values.update(TEMPLATE=template,NAMES=names,EXPECTED=expected,TARGET_HEADERS=json.loads(auth.read_text(encoding='utf-8')),WRITERS=json.loads((PRIVATE/'writer-ownership.private.json').read_text(encoding='utf-8')))
        body=CONFIGURE
    result=remote('\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+COMMON+'\n'+body,150)
    (TASK/('control-'+args.action+'-installation.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
