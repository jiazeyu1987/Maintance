"""Install explicit main-target contracts after real read-only admission checks."""
import base64
import concurrent.futures
import hashlib
import json
from pathlib import Path
from install_controls import COMMIT, PRIVATE, PROFILES, ROOTS, ssh

REMOTE=r'''
import base64,copy,hashlib,json,os,pathlib,re,socket,stat,subprocess,sys
root=pathlib.Path(ROOT);engine=root/'engine';sys.path[:0]=[str(engine/'control'),str(engine/'common'),str(engine/'formal'),DEPENDENCIES]
from recovery_engine import pin,digest
from recovery_replacement_storage import snapshot_mounts
from recovery_main_target import capture_main_application,application_inputs,observe_main_target
from types import SimpleNamespace
def need(value,code):
    if not value:raise ValueError(code)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def write(path,value,raw=False):
    path=pathlib.Path(path);data=value if raw else canonical(value)
    need(path.is_absolute() and path.parent.resolve()==path.parent,'INSTALL_DESTINATION_INVALID')
    if path.exists():
        need(path.read_bytes()==data,'INSTALL_EXISTING_BYTES_CHANGED');return pin(str(path))
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
    need(path.read_bytes()==data,'INSTALL_READBACK_FAILED');return pin(str(path))
def docker(args,input_bytes=None):
    p=subprocess.run(['/usr/bin/docker','--host','unix:///var/run/docker.sock',*args],input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    need(p.returncode==0 and not p.stderr,'INSTALL_DOCKER_QUERY_FAILED');return p.stdout
def inspect(identity):
    rows=json.loads(docker(['inspect',identity]));need(len(rows)==1,'INSTALL_CONTAINER_IDENTITY_INVALID');return rows[0]
need(root.is_dir() and (root/'installation.json').is_file(),'STAGED_COMPONENT_REQUIRED')
need(json.loads((root/'installation.json').read_bytes())['sourceCommit']==COMMIT,'INSTALL_COMPONENT_VERSION_CHANGED')
names=NAMES;rows={role:inspect(name) for role,name in names.items()};ids={r['Id'] for r in rows.values()}
for role,row in rows.items():
    need(row['Id']==EXPECTED_IDS[role] and row['Image']==EXPECTED_IMAGES[role],'INSTALL_MAIN_IDENTITY_CHANGED')
    need(row['State']['Running'] and not row['State']['Restarting'] and not row['State']['Paused'],'INSTALL_MAIN_UNSTABLE')
    if role in ('backend','frontend'):need(row['State'].get('Health',{}).get('Status')=='healthy','INSTALL_MAIN_UNHEALTHY')
    need(not row['HostConfig']['Privileged'],'INSTALL_PRIVILEGED_REJECTED')
allids=docker(['ps','--all','--no-trunc','--format','{{.ID}}']).decode().splitlines()
allrows=json.loads(docker(['inspect',*allids]));need({r['Id'] for r in allrows}==set(allids),'INSTALL_CONSUMER_INVENTORY_CHANGED')
ips={role:next(a['IPAddress'] for a in row['NetworkSettings']['Networks'].values() if a['IPAddress']) for role,row in rows.items() if role!='frontend'}
resource_addresses=[ips[r] for r in ('mysql','minio','redis')]
outside=[];configscan=[]
for row in allrows:
    if row['Id'] in ids:continue
    text='\n'.join((row['Config'].get('Env') or [])+(row['Config'].get('Cmd') or [])+(row['Config'].get('Entrypoint') or []))
    paths=[]
    for mount in row['Mounts']:
        p=pathlib.Path(mount['Source'])
        if mount['Type']=='bind' and p.is_file() and p.stat().st_size<=2*1024*1024 and (p.suffix.lower() in ('.json','.yml','.yaml','.properties','.env','.conf') or p.name.endswith('-config')):
            text+='\n'+p.read_text(encoding='utf-8');paths.append(str(p))
    configscan.append({'containerId':row['Id'],'running':row['State']['Running'],'configurationFiles':paths})
    if any(ip in text for ip in resource_addresses):outside.append({'containerId':row['Id'],'name':row['Name'],'running':row['State']['Running']})
if outside:
    write(root/'configuration/external-references.json',outside)
need(not any(row['running'] for row in outside),'INSTALL_EXTERNAL_DIRECT_RESOURCE_REFERENCE')
targetroot=pathlib.Path(TARGETROOT)
query='SELECT @@server_uuid,@@GLOBAL.log_bin; SELECT HOST,DB FROM information_schema.PROCESSLIST WHERE USER NOT IN (\'root\',\'mysql.infoschema\',\'mysql.session\',\'mysql.sys\');'
mysql=docker(['exec',rows['mysql']['Id'],'/usr/bin/mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names','-e',query]).decode().strip().splitlines()
uuid,logbin=mysql[0].split('\t');need(logbin=='1','INSTALL_BINARY_LOGGING_REQUIRED')
need(all(line.split('\t')[0].rsplit(':',1)[0]==ips['backend'] and line.split('\t')[1]=='ruoyi-vue-pro' for line in mysql[1:]),'INSTALL_EXTERNAL_DATABASE_WRITER')
redisconf=(targetroot/'private/redis.conf').read_text(encoding='utf-8')
password=re.search(r'^requirepass\s+(.*?)\s*$',redisconf,re.M).group(1).strip('"')
redis=docker(['exec','-i',rows['redis']['Id'],'sh','-ec','IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"','readonly-redis','/usr/local/bin/redis-cli','--raw','CLIENT','LIST'],(password+'\n').encode()).decode()
clients=[dict(t.split('=',1) for t in line.split() if '=' in t) for line in redis.splitlines()]
need(all(c['addr'].rsplit(':',1)[0] in (ips['backend'],'127.0.0.1') and (c['addr'].startswith('127.') or c['db']=='1') for c in clients),'INSTALL_EXTERNAL_REDIS_WRITER')
for role in ('mysql','minio','redis'):need(not rows[role]['HostConfig'].get('PortBindings'),'INSTALL_PUBLISHED_DATA_SERVICE_REJECTED')
miniomount=next(m for m in rows['minio']['Mounts'] if m['Destination']=='/data')
minioroot=pathlib.Path(miniomount['Source'])
bucketnames=sorted(p.name for p in minioroot.iterdir() if p.is_dir() and not p.name.startswith('.'))
need(bucketnames==sorted(TEMPLATE_TARGET['buckets']),'INSTALL_UNREGISTERED_OBJECT_BUCKET')
iam=minioroot/'.minio.sys/config/iam'
iamusers=[str(p.relative_to(iam)) for section in ('users','service-accounts') for p in (iam/section).glob('*/identity.json')]
identities={}
for name in iamusers:
    p=iam/name;files=[p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file())
    identities[name]={str(x.relative_to(iam)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
policies={str(p.relative_to(iam)):hashlib.sha256(p.read_bytes()).hexdigest() for section in ('policies','policydb') for p in (iam/section).rglob('*') if p.is_file()}
need(identities==WRITER_LOCK_EVIDENCE['iamIdentities'] and policies==WRITER_LOCK_EVIDENCE['iamPolicyFiles'],'INSTALL_OBJECT_IDENTITY_OR_POLICY_CHANGED')
need(set(iamusers)==set(ATTESTED_IDENTITIES),'INSTALL_UNATTESTED_OBJECT_IDENTITY')
placeholder=root/'replacement-state/runtime'
if placeholder.exists():
    need(placeholder.is_dir() and not placeholder.is_symlink() and not list(placeholder.iterdir()),'INSTALL_PLACEHOLDER_NOT_EMPTY')
    placeholder.rmdir()
networkids={a['NetworkID'] for row in rows.values() for a in row['NetworkSettings']['Networks'].values()}
networks=[json.loads(docker(['network','inspect',n]))[0] for n in sorted(networkids)]
configurationpins=[]
for role in ('backend','frontend'):
    for mount in rows[role]['Mounts']:
        need(mount['Type']=='bind' and not mount['RW'] and pathlib.Path(mount['Source']).is_file(),'INSTALL_APPLICATION_CONFIGURATION_NOT_PINNABLE')
        configurationpins.append(pin(mount['Source']))
evidence={'schemaVersion':'SpugMainRestoreInstallationPreflight/v1','host':HOST,'sourceCommit':COMMIT,
    'containerIds':{r:v['Id'] for r,v in rows.items()},'configurationDigests':{r:digest({k:v[k] for k in ('Path','Args','HostConfig','Config')}) for r,v in rows.items()},
    'allContainerCount':len(allrows),'otherConfigurationScan':configscan,'stoppedHistoricalResourceReferences':outside,
    'databaseUuid':uuid,'databaseClientAddresses':sorted({line.split('\t')[0].rsplit(':',1)[0] for line in mysql[1:]}),
    'redisClientAddresses':sorted({c['addr'].rsplit(':',1)[0] for c in clients}),
    'dataServicePublishedPorts':False,'objectBuckets':bucketnames,'additionalObjectIdentities':iamusers,
    'objectWriterAttestation':{'source':'user-confirmation-20261104','statement':'这些账号仅供 IntRuoyi 主程序使用','identities':identities,'policyFileSha256':policies,'databaseConfigurationMatches':DATABASE_IDENTITY_MATCHES},
    'sourceLockEvidence':WRITER_LOCK_EVIDENCE['matchingCaptures'],'targetLockPath':LOCKPATH,'restorePerformed':False}
preflightpin=write(root/('configuration/preflight-evidence-'+ATTEMPT+'.json'),evidence)
for path,item in VERSION_FILES.items():
    need(path.startswith('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/') and path.endswith('/images.json'),'CANONICAL_METADATA_PATH_INVALID')
    p=pathlib.Path(path);data=base64.b64decode(item['base64'])
    need(len(data)==item['pin']['bytes'] and hashlib.sha256(data).hexdigest()==item['pin']['sha256'],'CANONICAL_METADATA_CHANGED')
    need(not p.exists() or pin(path)==item['pin'],'CANONICAL_METADATA_CONFLICT')
    p.parent.mkdir(parents=True,mode=0o700,exist_ok=True);need(p.parent.resolve()==p.parent,'CANONICAL_METADATA_ALIAS_REJECTED')
    write(p,data,raw=True);need(pin(path)==item['pin'],'CANONICAL_METADATA_READBACK_FAILED')
owner=copy.deepcopy(TEMPLATE_OWNER);target=copy.deepcopy(TEMPLATE_TARGET)
source=copy.deepcopy(SOURCE)
source.update(archiveRoots=[ARCHIVES],parentChains={},recoveryPoints={},repositoryPointPins=[],repositoryBindingPinsByManifestSha256={})
need(pathlib.Path(ARCHIVES).resolve()==pathlib.Path(ARCHIVES) and pathlib.Path(ARCHIVES).is_dir(),'CANONICAL_ARCHIVE_UNAVAILABLE')
sourcecontrol=SOURCE_CONTROL
headerdoc={'headers':SOURCE_HEADERS}
sourceauth=write(root/'private/source-headers.json',headerdoc)
access={'schemaVersion':'SmallAppSourceCatalogueAccess/v1','selectionUrl':'http://127.0.0.1:34657/selections',
    'authCredentialRef':{'path':sourceauth['path'],'uid':0,'gid':0,'mode':0o600},'applicationId':APP,'engineSelectionRef':sourcecontrol['engineSelectionRef']}
accesspin=write(root/'configuration/source-access.json',access)
source['archiveCatalogue']={'schemaVersion':'RecoveryArchiveCatalogue/v1','maximumPointFiles':10000,'maximumMetadataBytes':67108864,'sourceAdmissionPin':accesspin}
target.update(targetId=rows['mysql']['Config']['Labels']['intruoyi.recovery.target'],sourceConfigRef=APP,
    machineId=pathlib.Path('/etc/machine-id').read_text().strip(),dockerEngineId=json.loads(docker(['info','--format','{{json .}}']))['ID'],
    dockerPin=pin('/usr/bin/docker'),dataRoot=str(root/'runtime'),
    dataPaths=[m['Source'] for r,row in rows.items() for m in row['Mounts'] if m['RW']],
    networkId=next(iter(rows['backend']['NetworkSettings']['Networks'].values()))['NetworkID'],
    services=[{'role':role,'id':row['Id'],'imageId':row['Image'],'ip':ips.get(role,'127.0.0.1')} for role,row in rows.items()])
if not (root/'runtime').exists():(root/'runtime').mkdir(mode=0o700)
target['application']={'startOrder':['backend','frontend'],'imageBindings':[],'configurationBindings':[],'artifactBindings':[]}
target['secrets']={'mysql':{'MYSQL_ROOT_PASSWORD':pin(str(targetroot/'private/mysql-root'))},
    'minio':{'MINIO_ROOT_USER':pin(str(targetroot/'private/minio-root-user')),'MINIO_ROOT_PASSWORD':pin(str(targetroot/'private/minio-root-password'))},
    'redis':{'REDIS_PASSWORD':write(root/'private/redis-password',password.encode(),raw=True)}}
for secrets in target['secrets'].values():
    for ref in secrets.values():need(stat.S_IMODE(pathlib.Path(ref['path']).stat().st_mode)==0o600,'SECRET_CUSTODY_INVALID')
lockpath=LOCKPATH
need(pathlib.Path(lockpath).parent.is_dir() and pathlib.Path(lockpath).parent.resolve()==pathlib.Path(lockpath).parent,'INSTALL_LOCK_PARENT_INVALID')
need(all(d['locks'].get('sourceLockPath',lockpath)==lockpath for d in WRITER_LOCK_EVIDENCE['matchingCaptures']),'INSTALL_SOURCE_LOCK_MISMATCH')
target['replacement']={'schemaVersion':'RegisteredApplicationReplacement/v2','stateRoot':str(root/'replacement-state'),
    'lockPath':lockpath,'databaseUuid':uuid,'services':{role:{'id':row['Id'],'imageId':row['Image'],'labels':row['Config']['Labels'],'mounts':sorted(row['Mounts'],key=lambda m:m['Destination'])} for role,row in rows.items()},
    'storage':None}
def inspect_volume(name):
    volume=json.loads(docker(['volume','inspect',name]));need(type(volume) is list and len(volume)==1,'INSTALL_VOLUME_IDENTITY_INVALID');return volume[0]
target['replacement']['storage']=snapshot_mounts(rows,['/mnt/nas',ARCHIVES,str(root)],volume_inspector=inspect_volume,volume_backing_paths=VOLUME_BACKINGS)
writer={'schemaVersion':'RegisteredMainWriterEvidence/v1','database':target['database'],'redisDatabase':target['redisRebuild']['database'],
    'objectBuckets':target['buckets'],'writerContainerIds':[rows['backend']['Id']],
    'exclusiveResources':{'database':True,'objects':True,'redis':True}}
writerpin=write(root/'configuration/writer-evidence.json',writer)
target['mainApplication']=capture_main_application(target,rows,networks,
    [{'role':role,'versionPath':['images','intruoyi-'+role],'imageId':rows[role]['Image']} for role in ('backend','frontend')],configurationpins,writerpin)
target['resourceBudget']={'schemaVersion':'RestoreResourceBudget/v1','mysqlMemoryBytes':2147483648,'hostAvailableMemoryBytes':2147483648,
    'diskBytesByPath':{str(root):68719476736,**{m['Source']:(34359738368 if role=='minio' else 8589934592) for role,row in rows.items() for m in row['Mounts'] if m['RW']}}}
owner.update(sources={APP:source},targets={REF:target},operationsRoot=str(root/'recovery-operations'),formalModuleDirectory=str(engine/'formal'),
    pythonPin=pin(PYTHON),maxExpandedBytes=68719476736,deadlineMilliseconds=21600000,
    dataLimits={'max_bytes':68719476736,'max_nodes':100000000,'max_rows':10000000,'seconds':7200})
ownerpin=write(root/('configuration/main-recovery-runtime-r1.json' if HOST.endswith('.58') else 'configuration/main-recovery.json'),owner)
repositorypin=write(root/'configuration/source-repository.json',REPOSITORY)
registration={'schemaVersion':'ApplicationRegistration/v1','applicationId':APP,'sourceConfigRef':APP,'displayName':'IntRuoyi 正式服备份',
    'allowedRestoreTargets':[{'configRef':REF}]}
registrationpin=write(root/'configuration/registration.json',registration)
write(root/'registry/applications'/(APP+'.pin.json'),registrationpin)
auth=write(root/'private/control-headers.json',TARGET_HEADERS)
control={'schemaVersion':'SmallAppExecutionServiceConfig/v2','taskRoot':str(root),'ledgerRoot':str(root/'ledger'),'registryRoot':str(root/'registry'),
    'listenAddress':'127.0.0.1','listenPort':PORT,'authCredentialRef':{'path':auth['path'],'uid':0,'gid':0,'mode':0o600},
    'allowedClientAddresses':['127.0.0.1'],'pythonPin':pin(PYTHON),'programPins':{role:pin(str(engine/(role+'_entry.py'))) for role in ('repository','recovery')},
    'workingDirectory':str(root),'environment':{'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':':'.join([str(engine/'control'),str(engine/'common'),str(engine/'formal'),DEPENDENCIES])},
    'deadlineMilliseconds':21600000,'engineSelectionRef':sourcecontrol['engineSelectionRef'],
    'sourceConfigurations':{APP:repositorypin},'restoreConfigurations':{APP:{REF:ownerpin}}}
controlpin=write(root/('configuration/control-'+str(PORT)+'-runtime-r1.json'),control)
from recovery_control_smallapp_native import Native
native=Native(controlpin);need(native.configuration()==control,'CONTROL_CONFIGURATION_NOT_READABLE')
from recovery_control_restore_catalogue import bind_archive_chain
request={'sourceConfigRef':APP,'targetConfigRef':REF,'operationId':'installation-preflight','recoveryPointRef':LATEST_POINT}
resolved,binding=bind_archive_chain(source,request)
point=json.loads(pathlib.Path(binding['pointPin']['path']).read_bytes())
bindingdoc=json.loads(pathlib.Path(point['manifestPin']['path']).with_name('recovery-repository-binding.json').read_bytes())
material=json.loads(pathlib.Path(bindingdoc['recoveryMaterialPin']['path']).read_bytes())
appnative=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},material=material,inspect=inspect)
application_inputs(appnative)
observation=observe_main_target(native,dict(request,operationId='installation-preflight'),{'ownerConfigurationPin':ownerpin})
from recovery_resource_admission import observe_resources,check_budget
resource=check_budget(target['resourceBudget'],observe_resources(owner,request,target['resourceBudget']))
hostroot=pathlib.Path('/var/lib/spug-restore-resources')
if not hostroot.exists():hostroot.mkdir(mode=0o700)
need(hostroot.resolve()==hostroot and stat.S_IMODE(hostroot.stat().st_mode)==0o700 and hostroot.stat().st_uid==0,'HOST_RESOURCE_CUSTODY_INVALID')
need(not (hostroot/'active.json').exists(),'HOST_RESTORE_ALREADY_RESERVED')
sock=socket.socket();sock.bind(('127.0.0.1',PORT));sock.close()
unit=pathlib.Path('/etc/systemd/system')/UNIT
need(not unit.exists(),'CONTROL_UNIT_ALREADY_EXISTS')
command=PYTHON+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(controlpin).decode()+"'"
unitdata=('[Unit]\nDescription=Spug registered main restore control '+HOST+'\nAfter=network.target docker.service\n[Service]\nType=simple\nUser=root\nUMask=0077\nWorkingDirectory='+str(root)+'\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart='+command+'\nRestart=on-failure\nRestartSec=5\n[Install]\nWantedBy=multi-user.target\n').encode()
write(unit,unitdata,raw=True)
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
subprocess.run(['systemctl','enable','--now',UNIT],check=True,timeout=20,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
status=subprocess.run(['systemctl','is-active',UNIT],stdout=subprocess.PIPE,check=True,timeout=10).stdout.decode().strip()
need(status=='active','CONTROL_SERVICE_NOT_ACTIVE')
receipt={'schemaVersion':'SpugMainRestoreTargetInstallation/v1','host':HOST,'targetConfigRef':REF,'root':str(root),
    'controlConfigurationPin':controlpin,'ownerConfigurationPin':ownerpin,'registrationPin':registrationpin,
    'preflightEvidencePin':preflightpin,'service':UNIT,'state':'INSTALLED_PENDING_SOURCE_TRANSPORT',
    'resourceAdmission':resource,'archivePointRef':LATEST_POINT,'restorePerformed':False}
write(root/'target-installation.json',receipt)
print(json.dumps(receipt))
'''

def configure(profile):
    host=profile['host'];suffix=host.split('.')[-1]
    inventory=json.loads((PRIVATE/(host+'-install-preflight.json')).read_text(encoding='utf-8'))
    doc57=json.loads((PRIVATE/'172.30.30.57.json').read_text(encoding='utf-8'))
    origin=next(c for c in doc57.values() if c.get('schemaVersion')=='SmallAppExecutionServiceConfig/v2')
    repository=next(c for c in doc57.values() if c.get('schemaVersion')=='RepositoryMinimumConfiguration/v1')
    templateinv=json.loads((PRIVATE/'172.30.30.58-install-preflight.json').read_text(encoding='utf-8'))
    owner=templateinv['documents']['/var/lib/docker/intruoyi-data/spug-intruoyi-58-restore-executor-20261024-r1/configuration/recovery.json']
    template=next(iter(owner['targets'].values()))
    names={'58':{'mysql':'brlab-prod57-nas-test58-20261020-r3-mysql','minio':'brlab-prod57-nas-test58-20261020-r3-minio','redis':'brlab-prod57-nas-test58-20261020-r3-redis','backend':'brlab-prod57-nas-test58-20261020-r3-backend','frontend':'intruoyi-july-unified-58-frontend'},
        '59':{'mysql':'intruoyi-prod-nas-restore59-20261020-native-mysql','minio':'intruoyi-prod-nas-restore59-20261020-native-minio','redis':'intruoyi-prod-nas-restore59-20261020-native-redis','backend':'intruoyi-prod-nas-restore59-20261020-backend','frontend':'intruoyi-july-unified-59-frontend-r2'}}[suffix]
    rows={role:next(r for r in inventory['containers'].values() if r['Name']=='/'+name) for role,name in names.items()}
    python='/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12' if suffix=='58' else profile['python']
    import secrets
    targetheaders={'headers':{'Authorization':'Bearer '+secrets.token_urlsafe(40)}}
    privateconfig=PRIVATE/(host+'-control-headers.private.json')
    if privateconfig.exists():targetheaders=json.loads(privateconfig.read_text(encoding='utf-8'))
    else:privateconfig.write_text(json.dumps(targetheaders),encoding='utf-8')
    sourceheaders=json.loads(Path('C:/Spug/runtime/private/PROD57-bridge-headers.private.json').read_text(encoding='utf-8'))['headers']
    latest=json.loads((PRIVATE/'172.30.30.57-dependencies.json').read_text(encoding='utf-8'))
    point=latest['documents'][latest['latestPointPin']['path']]['backupId']
    params={'COMMIT':COMMIT,'ROOT':ROOTS[suffix],'HOST':host,'NAMES':names,'EXPECTED_IDS':{r:v['Id'] for r,v in rows.items()},
        'EXPECTED_IMAGES':{r:v['Image'] for r,v in rows.items()},'TARGETROOT':('/var/lib/docker/intruoyi-data/prod-nas-restore-test58-20261020/target-r3' if suffix=='58' else '/mnt/intruoyi-data/prod-nas-restore-prep-20261020/restore-target-r1'),
        'TEMPLATE_OWNER':owner,'TEMPLATE_TARGET':template,'SOURCE':owner['sources']['intruoyi-57-safe-20261024-v1'],
        'SOURCE_CONTROL':origin,'REPOSITORY':repository,'SOURCE_HEADERS':sourceheaders,'TARGET_HEADERS':targetheaders,
        'APP':'intruoyi-57-safe-20261024-v1','REF':'intruoyi-main-'+suffix+'-safe-restore-20261104-v1',
        'ARCHIVES':repository['repositoryRoot']+'/archives','VERSION_FILES':json.loads((PRIVATE/'canonical-version-files.json').read_text(encoding='utf-8')),
        'PYTHON':python,'PORT':43658 if suffix=='58' else 33659,'UNIT':'spug-main-restore-'+suffix+'-20261104-v3.service','LATEST_POINT':point,
        'DEPENDENCIES':('/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/installed/runtime/lib/python3.12/site-packages' if suffix=='58' else '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07/source/smallapp-20261014-r1/installation-r2-redis/context/runtime/lib/python3.12/site-packages')}
    params['WRITER_LOCK_EVIDENCE']=json.loads((PRIVATE/(host+'-writer-lock-evidence.json')).read_text(encoding='utf-8'))
    import uuid
    params['ATTEMPT']=uuid.uuid4().hex
    params['DATABASE_IDENTITY_MATCHES']=json.loads((PRIVATE/(host+'-object-database-bindings.json')).read_text(encoding='utf-8'))['matches']
    params['ATTESTED_IDENTITIES']=['users/'+name+'/identity.json' for name in ['EDHRUCQZT8LNMQMKRFZK','EDHRHFRQFGCXYATNNSC6','EDHRCJSBJZZDMENUJE6R']+(['rag_flow'] if suffix=='59' else [])]
    params['LOCKPATH']='/var/lib/docker/intruoyi-data/prod-nas-restore-test58-20261020/target-r3/main-backup-restore.lock' if suffix=='58' else '/mnt/intruoyi-data/backup59-lightweight-20261022/source-locks/source.lock'
    params['VOLUME_BACKINGS']={} if suffix=='58' else {next(m['Name'] for m in rows[role]['Mounts'] if m['RW']):'/mnt/intruoyi-data/prod-nas-restore-prep-20261020/native-target-data/'+role for role in ('mysql','minio','redis')}
    script='\n'.join(k+'='+repr(v) for k,v in params.items())+'\n'+REMOTE
    result=ssh(dict(profile,python=python),script,timeout=150)
    (PRIVATE/(host+'-target-installation.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--host',choices=['172.30.30.58','172.30.30.59']);args=parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(configure,p) for p in PROFILES if not p['host'].endswith('.57') and (args.host is None or p['host']==args.host)]
        for future in concurrent.futures.as_completed(futures):
            try:print(json.dumps(future.result()))
            except Exception as error:print(str(error));raise
