"""Execute the explicitly approved .59 original-service plan in bounded phases."""
import json
import sys
from install_review_control import SCRIPT as COMMON
from resume_readonly import PRIVATE, TASK, remote

BASELINE = PRIVATE / 'review-start-authorized-baseline.private.json'

SCRIPT = r'''
from types import SimpleNamespace
import urllib.request
receipt=read(EXPECTED_RECEIPT_PIN)
need(receipt['ownerConfigurationPin']==EXPECTED_OWNER_PIN and receipt['controlConfigurationPin']==EXPECTED_CONTROL_PIN,'CONTROL_GENERATION_CHANGED')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_resource_admission import _host_lock
from recovery_replacement_storage import verify_storage
from formal_data_evidence import validate_limits
target=owner['targets'][receipt['targetConfigRef']]
services={s['role']:s for s in target['services']}
allowed={services[r]['id'] for r in ('mysql','redis','minio','backend')}
need(pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED_BOOT,'BOOT_CHANGED')
need(pathlib.Path('/etc/machine-id').read_text().strip()==target['machineId'],'MACHINE_CHANGED')
need(json.loads(run(['docker','info','--format','{{json .}}']))['ID']==target['dockerEngineId'],'ENGINE_CHANGED')
engine=pathlib.Path(owner['formalModuleDirectory']).parent
version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'PACKAGE_CHANGED')
validate_limits(owner['dataLimits'])
for p in target['mainApplication']['configurationPins']:read_bytes=pathlib.Path(p['path']).read_bytes();need(pin(p['path'])==p,'BUSINESS_CONFIGURATION_PIN_CHANGED')
for group in target['secrets'].values():
 for p in group.values():need(pin(p['path'])==p,'CREDENTIAL_PIN_CHANGED')
state=root/'configuration/review-start-authorized-20261105'
order=['mount','start-data','data-ready','start-backend','verify']
previous=order[order.index(PHASE)-1] if PHASE in order and order.index(PHASE)>0 else None
expected=json.loads((state/(previous+'.json')).read_bytes())['business'] if previous else EXPECTED_BUSINESS
before=business();need(before==expected,'BUSINESS_DRIFT')
rows={r:json.loads(run(['docker','inspect',s['id']]))[0] for r,s in services.items()}
for role,row in rows.items():
 exp=target['replacement']['services'][role]
 need(row['Image']==services[role]['imageId']==exp['imageId'] and row['Config']['Labels']==exp['labels'] and sorted(row['Mounts'],key=lambda m:m['Destination'])==exp['mounts'],'ORIGINAL_SERVICE_CHANGED')
 need(not row['State']['Paused'] and not row['State']['Restarting'],'UNSTABLE_SERVICE')
native=SimpleNamespace(source=owner['sources'][target['sourceConfigRef']],root=root/'recovery-operations',config=target,
 docker=lambda args:run(['docker',*args]))
fd=os.open(target['replacement']['lockPath'],os.O_RDWR|os.O_NOFOLLOW)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
with _host_lock():
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESTORE')
 need(not [p for n in ('ledger','operations','recovery-operations','replacement-state') for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'RESTORE_RECORDS_PRESENT')
 verify_storage(native,target['replacement'],rows)
 mysqlmount=next(m for m in target['replacement']['storage']['mounts'] if m['role']=='mysql')
 mysqlroot=pathlib.Path(mysqlmount['source'])
 need(('server-uuid='+target['replacement']['databaseUuid']) in (mysqlroot/'auto.cnf').read_text(),'ORIGINAL_DATABASE_UUID_CHANGED')
 need(target['database']=='ruoyi-vue-pro','EXPECTED_SCHEMA_CHANGED')
 # MySQL encodes each hyphen as @002d in the existing schema directory.
 schemadir=mysqlroot/'ruoyi@002dvue@002dpro'
 need(schemadir.is_dir() and sum(1 for p in schemadir.iterdir() if p.suffix=='.ibd')>0,'EXISTING_DATABASE_REQUIRED')
 out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':PHASE,'host':'172.30.30.59',
  'targetConfigRef':receipt['targetConfigRef'],'ownerConfigurationPin':receipt['ownerConfigurationPin'],
  'controlConfigurationPin':receipt['controlConfigurationPin'],'originalStorageVerified':True,'packageFilesMatch':True,
  'operationCount':0,'claimCount':0,'restoreDispatched':False}
 source=pathlib.Path('/mnt/intruoyi-backup-nas')
 archive=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
 relative='Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives/prod-standard-197d8fd4ced92df64f0c152e9c6d470596ec343532e3b2dd82ebbef680114bcb/.repository/point.json'
 pointsha='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128'
 def mountrows(path):return [l for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if l.split()[4]==str(path)]
 def archivecheck(path,readonly):
  mr=mountrows(path);need(len(mr)==1 and mr[0].split()[3]=='/' and mr[0].split(' - ')[1].split()[:2]==['cifs','//172.30.30.4/IT共享'],'ARCHIVE_SHARE_CHANGED')
  need(not readonly or 'ro' in mr[0].split()[5].split(','),'ARCHIVE_NOT_READONLY')
  need(hashlib.sha256((path/relative).read_bytes()).hexdigest()==pointsha,'FULL_POINT_CHANGED')
 archivecheck(source,False)
 if PHASE in ('preflight','mount'):
  need(all(not rows[r]['State']['Running'] for r in ('mysql','redis','minio','backend')) and rows['frontend']['State']['Running'],'EXPECTED_ORIGINAL_STOPPED_STATE')
  need(archive.is_dir() and archive.resolve()==archive and not archive.is_symlink() and not any(archive.iterdir()) and not mountrows(archive),'CANONICAL_ARCHIVE_NOT_EMPTY_UNMOUNTED')
 if PHASE=='mount':
  state.mkdir(mode=0o700)
  append(state/'intent.json',out)
  unit=run(['systemd-escape','--path','--suffix=mount',str(archive)]).decode().strip()
  unitpath=pathlib.Path('/etc/systemd/system')/unit
  drop=pathlib.Path('/etc/systemd/system')/(receipt['service']+'.d/archive-mount.conf')
  need(not unitpath.exists() and not drop.exists(),'MOUNT_DEFINITION_EXISTS')
  body='[Unit]\nDescription=Registered IntRuoyi original read-only archive mount\nRequiresMountsFor='+str(source)+'\nAfter=network-online.target\n\n[Mount]\nWhat='+str(source)+'\nWhere='+str(archive)+'\nType=none\nOptions=bind,ro\nTimeoutSec=25\n\n[Install]\nWantedBy=multi-user.target\n'
  with unitpath.open('xb') as f:f.write(body.encode());os.chmod(unitpath,0o644)
  drop.parent.mkdir(exist_ok=True)
  with drop.open('xb') as f:f.write(('[Unit]\nRequiresMountsFor='+str(archive)+'\n').encode());os.chmod(drop,0o644)
  run(['systemctl','daemon-reload']);run(['systemctl','enable','--now',unit])
  archivecheck(archive,True)
  out.update(archiveUnit=unit,archiveActive=run(['systemctl','is-active',unit]).decode().strip(),archiveEnabled=run(['systemctl','is-enabled',unit]).decode().strip(),pointSha256=pointsha)
 elif PHASE!='preflight':archivecheck(archive,True)
 if PHASE=='start-data':
  for role in ('mysql','redis','minio'):
   need(not rows[role]['State']['Running'],'ORIGINAL_DATA_SERVICE_ALREADY_RUNNING')
   need(business()==before,'START_SEQUENCE_DRIFT')
   run(['docker','start',services[role]['id']])
   after=business();need(after.keys()==before.keys(),'CONTAINER_SET_CHANGED')
   changed={i for i in after if after[i]!=before[i]}
   need(changed=={services[role]['id']} and after[services[role]['id']]['running'],'UNEXPECTED_START_CHANGE')
   need(all(after[i]['configurationSha256']==EXPECTED_BUSINESS[i]['configurationSha256'] and after[i]['image']==EXPECTED_BUSINESS[i]['image'] for i in after),'BUSINESS_CONFIGURATION_CHANGED')
   before=after
 if PHASE=='data-ready':
  def authenticated(role,key,env,args):
   password=pathlib.Path(target['secrets'][role][key]['path']).read_text().strip()
   script='IFS= read -r '+env+'; export '+env+'; exec "$@"'
   p=subprocess.run(['docker','exec','-i',services[role]['id'],'sh','-ec',script,'review-readonly',*args],input=(password+'\n').encode(),capture_output=True,timeout=20)
   need(p.returncode==0,'ORIGINAL_'+role.upper()+'_NOT_READY');return p.stdout.decode().strip()
  sql="SELECT @@server_uuid,@@GLOBAL.log_bin; SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+target['database']+"';"
  result=authenticated('mysql','MYSQL_ROOT_PASSWORD','MYSQL_PWD',['mysql','--protocol=socket','-uroot','-N','-B','-e',sql]).splitlines()
  need(result[0].split('\t')==[target['replacement']['databaseUuid'],'1'] and int(result[1])>0,'ORIGINAL_MYSQL_IDENTITY_INVALID')
  pong=authenticated('redis','REDIS_PASSWORD','REDISCLI_AUTH',[target['redisClientPath'],'-n',str(target['redisRebuild']['database']),'PING'])
  need(pong=='PONG','ORIGINAL_REDIS_NOT_READY')
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://'+services['minio']['ip']+':9000/minio/health/live',timeout=10) as response:need(response.status==200,'ORIGINAL_MINIO_NOT_READY')
  out.update(databaseUuid=target['replacement']['databaseUuid'],databaseTableCount=int(result[1]),binaryLogging=True,redisPing=pong,minioHTTP=200)
 if PHASE=='start-backend':
  need(not rows['backend']['State']['Running'],'ORIGINAL_BACKEND_ALREADY_RUNNING')
  need(all(rows[r]['State']['Running'] for r in ('mysql','redis','minio')),'DATA_SERVICES_NOT_RUNNING')
  run(['docker','start',services['backend']['id']])
 if PHASE=='verify':
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  with opener.open('http://'+services['backend']['ip']+':48081/actuator/health',timeout=15) as response:health=json.load(response)
  need(health['status']=='UP','ORIGINAL_BACKEND_NOT_UP')
  with opener.open('http://172.30.30.59:38081',timeout=15) as response:need(response.status==200,'ORIGINAL_FRONTEND_NOT_READY')
  out.update(backendHealth='UP',frontendHTTP=200)
 after=business()
 need(after.keys()==EXPECTED_BUSINESS.keys(),'CONTAINER_SET_CHANGED')
 for identity,item in after.items():
  need(item['configurationSha256']==EXPECTED_BUSINESS[identity]['configurationSha256'] and item['image']==EXPECTED_BUSINESS[identity]['image'],'BUSINESS_CONFIGURATION_CHANGED')
  if identity not in allowed:need(item==EXPECTED_BUSINESS[identity],'UNAUTHORIZED_BUSINESS_CHANGED')
 if PHASE in ('preflight','mount','data-ready','verify'):need(after==before,'BUSINESS_CHANGED_DURING_READONLY_PHASE')
 if PHASE=='verify':need(all(after[s['id']]['running'] for s in services.values()),'ORIGINAL_SERVICES_NOT_RUNNING')
 need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_NOT_ACTIVE')
 out.update(business=after,allOriginalConfigurationsPreserved=True,otherBusinessUnchanged=True,controlActive=True)
 if PHASE!='preflight':append(state/(PHASE+'.json'),out)
 print(json.dumps(out))
os.close(fd)
'''

def execute(phase):
    baseline=json.loads(BASELINE.read_text(encoding='utf-8'))
    receipt=baseline['documents']['targetInstallation']
    def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    import hashlib
    expected={r['Id']:{'name':r['Name'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],
        'running':r['State']['Running'],'image':r['Image'],
        'configurationSha256':hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','Config','HostConfig')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()}
        for r in baseline['containers']}
    setup=dict(PHASE=phase,EXPECTED_BOOT='0fc8567e-3b8b-4e3f-902b-43e93284738d',EXPECTED_BUSINESS=expected,
        EXPECTED_RECEIPT_PIN=baseline['files']['/mnt/intruoyi-data/spug-main-restore-20261104-v3/target-installation.json'],
        EXPECTED_OWNER_PIN=receipt['ownerConfigurationPin'],EXPECTED_CONTROL_PIN=receipt['controlConfigurationPin'])
    source=COMMON.split('receiptpath=root/')[0]+'\n'.join(k+'='+repr(v) for k,v in setup.items())+'\n'+SCRIPT
    result=remote('172.30.30.59',source,timeout=100)
    (TASK/('review-authorized-'+phase+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='business'},ensure_ascii=False))
    return result

if __name__=='__main__':execute(sys.argv[1])
