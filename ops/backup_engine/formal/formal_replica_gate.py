"""Bind actual dependency observations to copied metadata; no formal finality."""
import hashlib,json,os,re,stat,time,subprocess,threading,sys
from pathlib import Path
from formal_snapshot_linux import (FormalSnapshotError,require,_hash_object,_canonical_bytes,_existing_file,observation_timeout,
    verify_physical_minio_tree,prepare_minio_replica_copy,safe_file,_sync_directory,current_owner_guard)
from formal_s3_export import observe_replica_bucket_dependencies

def _metadata_scope(root,buckets,*,guard=None):
    root=Path(root).absolute();started=time.monotonic()
    def budget():
        require(time.monotonic()-started<120,'FORMAL_REPLICA_METADATA_TIMEOUT')
        if guard is not None:current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    budget()
    for part in [root,*root.parents]:
        require(part.is_dir() and not part.is_symlink() and part.resolve()==part,'FORMAL_REPLICA_PATH_INVALID')
    sys=root/'.minio.sys'
    require(sys.is_dir() and not sys.is_symlink(),'FORMAL_REPLICA_METADATA_MISSING')
    require(type(buckets) is list and buckets and len(buckets)<=1000 and
      all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',b) for b in buckets) and len(set(buckets))==len(buckets),
      'FORMAL_REPLICA_BUCKET_SCOPE_INVALID')
    for relative in ('batch-jobs','config/tier-config.bin'):
        p=sys/relative
        for part in [p,*p.parents]:
            require(not part.is_symlink(),'FORMAL_REPLICA_PATH_INVALID')
            if part==root:break
        require(not p.exists(),'FORMAL_REPLICA_INTERNAL_DEPENDENCY_PRESENT')
    bucket_root=sys/'buckets'
    require(bucket_root.is_dir() and not bucket_root.is_symlink(),'FORMAL_REPLICA_METADATA_MISSING')
    # Exact pinned data-usage.go names, not bucket policy/lifecycle metadata.
    # Whole physical receipt still includes and verifies these cache bytes.
    caches={'.usage.json','.usage.json.bkp','.usage-cache.bin','.bloomcycle.bin'}
    heal=bucket_root/'.heal'
    if heal.exists() or heal.is_symlink():
        require(heal.is_dir() and not heal.is_symlink(),'FORMAL_REPLICA_HEAL_PENDING')
        entries={p.relative_to(heal).as_posix() for p in heal.rglob('*')}
        require(entries=={'mrf','mrf/list.bin'} and (heal/'mrf').is_dir() and not (heal/'mrf').is_symlink(),
                'FORMAL_REPLICA_HEAL_PENDING')
        pending=_existing_file(heal/'mrf/list.bin')
        require(pending.stat().st_size==4 and pending.read_bytes()==b'\x01\x00\x01\x00',
                'FORMAL_REPLICA_HEAL_PENDING')
    require(all(p.name in buckets or p.name in caches or p.name=='.heal' for p in bucket_root.iterdir()) and
            sorted(p.name for p in bucket_root.iterdir() if p.is_dir() and p.name not in caches and p.name!='.heal')==sorted(buckets),
            'FORMAL_REPLICA_BUCKET_SCOPE_CHANGED')
    rows=[]
    for directory in (sys/'config',*(bucket_root/b for b in sorted(buckets))):
        require(directory.is_dir() and not directory.is_symlink(),'FORMAL_REPLICA_METADATA_MISSING')
        for current,dirs,files in os.walk(directory,followlinks=False):
            budget()
            if Path(current)==directory and directory.parent==bucket_root:
                dirs[:]=[name for name in dirs if name not in caches]
                files=[name for name in files if name not in caches]
            for name in sorted(dirs+files):
                budget()
                p=Path(current)/name;info=p.lstat()
                require(not p.is_symlink() and (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)),
                        'FORMAL_REPLICA_PATH_INVALID')
                relative=p.relative_to(root).as_posix()
                if stat.S_ISDIR(info.st_mode):rows.append([relative,'directory'])
                else:
                    require(info.st_size<=16*1024*1024,'FORMAL_REPLICA_METADATA_TOO_LARGE')
                    digest,size=_hash_object(p,guard=budget);rows.append([relative,digest,size])
                require(len(rows)<=10000,'FORMAL_REPLICA_METADATA_TOO_LARGE')
    require(rows,'FORMAL_REPLICA_METADATA_MISSING')
    budget()
    return {'buckets':sorted(buckets),'entryCount':len(rows),'mrfPendingEntries':0,
            'metadataScopeSha256':hashlib.sha256(_canonical_bytes(sorted(rows))).hexdigest()}

def observe_bound_replica_dependencies(client,source_root,buckets,*,guard=None):
    """Live API and raw metadata observation, pending stopped capture binding.

    The caller still owns live writer exclusion. Repeated digest equality is
    observation, not a maintained host fence or an authorization to start.
    """
    before=_metadata_scope(source_root,buckets,guard=guard)
    observations=observe_replica_bucket_dependencies(client,buckets)
    startup=[client.replica_configuration(bucket,configuration) for bucket in buckets
             for configuration in ('notification','versioning','object-lock')]
    after=_metadata_scope(source_root,buckets,guard=guard)
    require(before==after,'FORMAL_REPLICA_METADATA_CHANGED')
    return {'state':'DEPENDENCIES_OBSERVED_PENDING_CAPTURE_BINDING',
            'metadataScope':after,'bucketObservations':observations,'startupConfigurations':startup}

def verify_started_replica_dependencies(observed,current):
    """Bind a live replica readback; not sustained exclusion or restore proof.

    Absence XML has per-request identities, so retain its raw digest as evidence
    but compare the exact validated S3 absence. Successful protection responses
    keep their full raw byte binding, including retention and MFA configuration.
    """
    code='FORMAL_REPLICA_DEPENDENCY_READBACK_CHANGED'
    def binding(value):
        require(type(value) is dict and set(value)=={'state','metadataScope','bucketObservations','startupConfigurations'}
            and value['state']=='DEPENDENCIES_OBSERVED_PENDING_CAPTURE_BINDING',code)
        scope=value['metadataScope'];obs=value['bucketObservations']
        require(type(scope) is dict and type(obs) is dict and
            set(obs)=={'state','buckets','observations','replicaStartupApproved'} and
            obs['state']=='BUCKET_DEPENDENCIES_OBSERVED_PENDING_FROZEN_BINDING' and
            obs['replicaStartupApproved'] is False,code)
        buckets=obs['buckets']
        require(type(buckets) is list and 0<len(buckets)<=1000 and
            all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]',b) for b in buckets)
            and len(set(buckets))==len(buckets) and scope.get('buckets')==sorted(buckets),code)
        absent={'lifecycle':'NoSuchLifecycleConfiguration','replication':'ReplicationConfigurationNotFoundError',
            'encryption':'ServerSideEncryptionConfigurationNotFoundError'}
        rows={}
        for group,names in ((obs['observations'],set(absent)),
                            (value['startupConfigurations'],{'notification','versioning','object-lock'})):
            require(type(group) is list and len(group)==len(buckets)*3,code)
            for row in group:
                require(type(row) is dict and row.get('bucket') in buckets and row.get('configuration') in names,code)
                key=(row['bucket'],row['configuration']);configuration=key[1]
                require(key not in rows and type(row.get('httpStatus')) is int and
                    type(row.get('rawSha256')) is str and re.fullmatch('[0-9a-f]{64}',row['rawSha256']) and
                    type(row.get('rawBytes')) is int and 0<row['rawBytes']<=16384,code)
                fields={'bucket','configuration','httpStatus','rawSha256','rawBytes'}
                if configuration in absent or row['httpStatus']==404:
                    expected=absent.get(configuration,'ObjectLockConfigurationNotFoundError')
                    require(configuration in absent or configuration=='object-lock',code)
                    fields.add('errorCode')
                    require(row['httpStatus']==404 and row.get('errorCode')==expected,code)
                    if configuration=='object-lock':
                        fields.add('enabled');require(row.get('enabled') is False,code)
                    require(set(row)==fields,code)
                    rows[key]={k:v for k,v in row.items() if k not in ('rawSha256','rawBytes')}
                else:
                    require(row['httpStatus']==200,code)
                    field={'notification':'externalNotificationEntries','versioning':'status','object-lock':'enabled'}[configuration]
                    fields.add(field);require(set(row)==fields,code)
                    if configuration=='notification':require(type(row[field]) is int and row[field]==0,code)
                    elif configuration=='versioning':require(row[field] in ('Enabled','Suspended','UNVERSIONED'),code)
                    else:require(row[field] is True,code)
                    rows[key]=row
        return dict(metadataScope=scope,rows=[rows[key] for key in sorted(rows)])
    require(_canonical_bytes(binding(observed))==_canonical_bytes(binding(current)),code)

def prepare_checked_minio_replica(capture_root,replica_root,physical_receipt,observed,*,guard):
    """Refuse before making a runnable copy if source dependencies cannot bind."""
    current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    require(type(observed) is dict and set(observed)=={'state','metadataScope','bucketObservations','startupConfigurations'} and
      observed['state']=='DEPENDENCIES_OBSERVED_PENDING_CAPTURE_BINDING','FORMAL_REPLICA_OBSERVATION_INVALID')
    scope=observed['metadataScope'];obs=observed['bucketObservations']
    require(type(scope) is dict and type(obs) is dict and set(obs)=={'state','buckets','observations','replicaStartupApproved'} and
      obs['state']=='BUCKET_DEPENDENCIES_OBSERVED_PENDING_FROZEN_BINDING' and obs['replicaStartupApproved'] is False and
      type(obs['buckets']) is list and scope.get('buckets')==sorted(obs['buckets']) and
      type(obs['observations']) is list,'FORMAL_REPLICA_OBSERVATION_INVALID')
    expected=[(b,c,code) for b in obs['buckets'] for c,code in (
      ('lifecycle','NoSuchLifecycleConfiguration'),('replication','ReplicationConfigurationNotFoundError'),
      ('encryption','ServerSideEncryptionConfigurationNotFoundError'))]
    require(len(obs['observations'])==len(expected),'FORMAL_REPLICA_OBSERVATION_INCOMPLETE')
    for row,(bucket,configuration,code) in zip(obs['observations'],expected):
        require(type(row) is dict and set(row)=={'bucket','configuration','httpStatus','errorCode','rawSha256','rawBytes'} and
          row['bucket']==bucket and row['configuration']==configuration and row['errorCode']==code and
          type(row['httpStatus']) is int and row['httpStatus']==404 and type(row['rawBytes']) is int and 0<row['rawBytes']<=16384 and
          type(row['rawSha256']) is str and re.fullmatch('[0-9a-f]{64}',row['rawSha256']),
          'FORMAL_REPLICA_OBSERVATION_INVALID')
    startup=observed['startupConfigurations']
    require(type(startup) is list and len(startup)==len(obs['buckets'])*3,'FORMAL_REPLICA_PROTECTION_OBSERVATION_REQUIRED')
    for row,(bucket,configuration) in zip(startup,[(b,c) for b in obs['buckets'] for c in ('notification','versioning','object-lock')]):
        require(type(row) is dict and row.get('bucket')==bucket and row.get('configuration')==configuration and
          type(row.get('rawSha256')) is str and re.fullmatch('[0-9a-f]{64}',row['rawSha256']) and
          type(row.get('rawBytes')) is int and 0<row['rawBytes']<=16384 and type(row.get('httpStatus')) is int,
          'FORMAL_REPLICA_PROTECTION_OBSERVATION_REQUIRED')
        if configuration=='notification':
            require(row['httpStatus']==200 and type(row.get('externalNotificationEntries')) is int and
                row['externalNotificationEntries']==0,'FORMAL_REPLICA_NOTIFICATION_PRESENT')
        elif configuration=='versioning':
            require(row['httpStatus']==200 and row.get('status') in ('Enabled','Suspended','UNVERSIONED'),
                'FORMAL_REPLICA_PROTECTION_OBSERVATION_REQUIRED')
        else:
            require((row['httpStatus']==200 and row.get('enabled') is True) or
                (row['httpStatus']==404 and row.get('enabled') is False and
                 row.get('errorCode')=='ObjectLockConfigurationNotFoundError'),
                'FORMAL_REPLICA_PROTECTION_OBSERVATION_REQUIRED')
    def current():current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    verify_physical_minio_tree(capture_root,physical_receipt,lease_guard=current)
    require(_metadata_scope(capture_root,obs['buckets'],guard=guard)==scope,'FORMAL_REPLICA_METADATA_CHANGED')
    prepare_minio_replica_copy(capture_root,replica_root,physical_receipt,lease_guard=current)
    require(_metadata_scope(replica_root,obs['buckets'],guard=guard)==scope,'FORMAL_REPLICA_METADATA_CHANGED')
    current()
    return {'state':'LOCAL_REPLICA_DEPENDENCIES_BOUND_PENDING_STARTUP_ISOLATION',
            'metadataScope':scope,'observationSha256':hashlib.sha256(_canonical_bytes(observed)).hexdigest(),
            'physicalTreeDigest':physical_receipt['physicalTreeDigest'],
            'productionEvidence':False,'protectionEquivalenceVerified':False,
            'replicaStartupApproved':False}

PINNED_MINIO_TAG='quay.io/minio/minio:RELEASE.2025-06-13T11-33-47Z'

def _guarded_run(args,*,guard,timeout,code):
    """Poll only this owned client; an issued Docker effect remains uncertain."""
    current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    deadline=time.monotonic()+observation_timeout(timeout)
    process=None;reader=None;raw=[];errors=[]
    try:
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        def read():
            try:
                value=process.stdout.read(1024*1024+1)
                if len(value)>1024*1024:errors.append(code)
                else:raw.append(value)
            except OSError:errors.append(code)
        reader=threading.Thread(target=read,daemon=True);reader.start()
        while process.poll() is None or reader.is_alive():
            current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
            require(time.monotonic()<deadline,code)
            require(not errors,code)
            reader.join(timeout=min(0.05,max(0,deadline-time.monotonic())))
            if not reader.is_alive() and process.poll() is None:time.sleep(0.05)
        current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
        require(not errors and len(raw)==1,code)
        return subprocess.CompletedProcess(args,process.returncode,raw[0],b'')
    except OSError:raise FormalSnapshotError(code) from None
    finally:
        primary=sys.exc_info()[1];uncertain=False
        # Cleanup must not replace owner-loss with an alleged remote outcome.
        if process is not None:
            try:
                if process.poll() is None:process.kill()
                process.wait(timeout=5)
            except (OSError,subprocess.TimeoutExpired):uncertain=True
            if reader is not None and reader.ident is not None:
                reader.join(timeout=5)
                uncertain=uncertain or reader.is_alive()
            if reader is None or not reader.is_alive():
                try:process.stdout.close()
                except OSError:uncertain=True
            if uncertain:
                if primary is not None:primary.clientCleanupUncertain=True
                else:raise FormalSnapshotError(code)

def create_and_start_checked_replica(operation,replica_root,physical,observed,proof,credential_file,evidence,*,image_id,guard):
    """Exclusive durable creation; interrupted intent is retained, never replayed."""
    current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    require(type(operation) is str and re.fullmatch('[A-Za-z0-9-]{1,80}',operation) and
            type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}',image_id),'FORMAL_REPLICA_ID_INVALID')
    require(type(proof) is dict and proof.get('observationSha256')==hashlib.sha256(_canonical_bytes(observed)).hexdigest() and
        proof.get('physicalTreeDigest')==physical.get('physicalTreeDigest') and proof.get('replicaStartupApproved') is False,
        'FORMAL_REPLICA_START_PROOF_INVALID')
    def current():current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    root=Path(replica_root).absolute();verify_physical_minio_tree(root,physical,lease_guard=current)
    require(_metadata_scope(root,observed['bucketObservations']['buckets'],guard=guard)==proof['metadataScope'],'FORMAL_REPLICA_METADATA_CHANGED')
    credentials=_existing_file(credential_file);info=credentials.stat()
    require(info.st_size<=16384 and (os.name!='posix' or info.st_mode&0o077==0),'FORMAL_REPLICA_CREDENTIAL_FILE_INVALID')
    raw=credentials.read_bytes()
    try:lines=raw.decode('utf-8').splitlines()
    except UnicodeError:raise FormalSnapshotError('FORMAL_REPLICA_CREDENTIAL_FILE_INVALID') from None
    require(len(lines)==2 and sorted(line.partition('=')[0] for line in lines)==['MINIO_ROOT_PASSWORD','MINIO_ROOT_USER'] and
        all(line.partition('=')[2] and not any(c in line for c in '\r\n\0') for line in lines),
        'FORMAL_REPLICA_CREDENTIAL_FILE_INVALID')
    image=_private_docker_json(['image','inspect',image_id],guard=guard)
    require(image.get('Id')==image_id and PINNED_MINIO_TAG in image.get('RepoTags',[]),'FORMAL_REPLICA_IMAGE_CHANGED')
    current();target=safe_file(evidence);target.mkdir(mode=0o700);_sync_directory(target.parent)
    def record(name,value):
        current()
        with safe_file(target/name).open('xb') as output:
            os.chmod(output.name,0o600);output.write(_canonical_bytes(value));output.flush();os.fsync(output.fileno())
        _sync_directory(target)
    intent={'operationId':operation,'imageId':image_id,'replicaRoot':str(root),
        'physicalTreeDigest':physical['physicalTreeDigest'],'observationSha256':proof['observationSha256'],
        'state':'REPLICA_CREATE_INTENT_PENDING_RECONCILIATION'}
    record('intent.json',intent)
    require(credentials.read_bytes()==raw,'FORMAL_REPLICA_CREDENTIAL_FILE_CHANGED')
    name='intruoyi-formal-replica-'+hashlib.sha256(operation.encode()).hexdigest()[:24]
    args=['docker','create','--name',name,'--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--ipc','private','--tmpfs','/tmp:rw,noexec,nosuid,size=67108864',
        '--env-file',str(credentials),'--label','intruoyi.formal-replica-operation='+operation,
        '--entrypoint','/usr/bin/minio','--mount','type=bind,src='+str(root)+',dst=/data',image_id,'server','/data']
    try:
        result=_guarded_run(args,guard=guard,timeout=90,code='FORMAL_REPLICA_CREATE_UNCERTAIN')
        identity=result.stdout.decode('ascii').strip()
        require(result.returncode==0 and re.fullmatch('[0-9a-f]{64}',identity),'FORMAL_REPLICA_CREATE_UNCERTAIN')
    except (OSError,subprocess.TimeoutExpired,UnicodeError):
        raise FormalSnapshotError('FORMAL_REPLICA_CREATE_UNCERTAIN') from None
    record('created.json',dict(intent,containerId=identity,state='REPLICA_CREATED_PENDING_START'))
    started=start_checked_minio_replica(identity,operation,root,physical,observed,proof,image_id=image_id,guard=guard)
    record('started.json',started)
    return started

def _private_docker_json(args,*,guard):
    # Docker inspect may contain credentials: retain only in process memory.
    try:
        result=_guarded_run(['docker',*args],guard=guard,timeout=30,code='FORMAL_REPLICA_INSPECT_FAILED')
        require(result.returncode==0 and len(result.stdout)<=1024*1024,'FORMAL_REPLICA_INSPECT_FAILED')
        value=json.loads(result.stdout)
        require(type(value) is list and len(value)==1 and type(value[0]) is dict,'FORMAL_REPLICA_INSPECT_FAILED')
        return value[0]
    except (OSError,subprocess.TimeoutExpired,ValueError):
        raise FormalSnapshotError('FORMAL_REPLICA_INSPECT_FAILED') from None

def start_checked_minio_replica(identity,operation,replica_root,physical,observed,proof,*,image_id,guard):
    """Start only a precreated restricted copy; never a live source container.

    The caller creates the container and records ownership before this entry.
    Timeout/uncertain start must be reconciled, not retried. Root-host exclusion
    and formal producer completion remain independent requirements.
    """
    current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    def current():current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    require(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}',image_id), 'FORMAL_REPLICA_IMAGE_REQUIRED')
    require(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity) and
            type(operation) is str and re.fullmatch('[a-zA-Z0-9-]{1,80}',operation),'FORMAL_REPLICA_ID_INVALID')
    require(type(proof) is dict and proof.get('state')=='LOCAL_REPLICA_DEPENDENCIES_BOUND_PENDING_STARTUP_ISOLATION' and
        proof.get('productionEvidence') is False and proof.get('replicaStartupApproved') is False and
        proof.get('protectionEquivalenceVerified') is False and
        proof.get('observationSha256')==hashlib.sha256(_canonical_bytes(observed)).hexdigest() and
        proof.get('physicalTreeDigest')==physical.get('physicalTreeDigest'), 'FORMAL_REPLICA_START_PROOF_INVALID')
    root=Path(replica_root).absolute()
    verify_physical_minio_tree(root,physical,lease_guard=current)
    require(_metadata_scope(root,observed['bucketObservations']['buckets'],guard=guard)==proof['metadataScope'],
            'FORMAL_REPLICA_METADATA_CHANGED')
    image=_private_docker_json(['image','inspect',image_id],guard=guard)
    require(image.get('Id')==image_id and PINNED_MINIO_TAG in image.get('RepoTags',[]),'FORMAL_REPLICA_IMAGE_CHANGED')
    record=_private_docker_json(['inspect',identity],guard=guard)
    config=record.get('Config',{});host=record.get('HostConfig',{});mounts=record.get('Mounts',[])
    require(record.get('Id')==identity and record.get('Image')==image_id and
        record.get('State',{}).get('Status')=='created' and record['State'].get('Running') is False and
        config.get('Entrypoint')==['/usr/bin/minio'] and config.get('Cmd')==['server','/data'] and
        config.get('Labels',{}).get('intruoyi.formal-replica-operation')==operation,
        'FORMAL_REPLICA_RESOURCE_CHANGED')
    require(host.get('NetworkMode')=='none' and host.get('ReadonlyRootfs') is True and
        host.get('Privileged') is False and host.get('CapAdd') in (None,[]) and host.get('CapDrop')==['ALL'] and
        host.get('SecurityOpt')==['no-new-privileges'] and host.get('PidMode')=='' and host.get('IpcMode')=='private' and
        host.get('Devices')==[] and host.get('PortBindings')=={} and
        host.get('RestartPolicy')=={'Name':'no','MaximumRetryCount':0} and
        host.get('Tmpfs')=={'/tmp':'rw,noexec,nosuid,size=67108864'},'FORMAL_REPLICA_ISOLATION_INVALID')
    require(type(mounts) is list and len(mounts)==1 and mounts[0].get('Type')=='bind' and
        mounts[0].get('Source')==str(root) and mounts[0].get('Destination')=='/data' and mounts[0].get('RW') is True,
        'FORMAL_REPLICA_MOUNT_INVALID')
    base=image.get('Config',{}).get('Env');env=config.get('Env')
    require(type(base) is list and type(env) is list and len(env)==len(base)+2 and
        len(set(x.partition('=')[0] for x in env))==len(env) and all(x in env for x in base),
        'FORMAL_REPLICA_ENVIRONMENT_INVALID')
    extras=[x for x in env if x not in base]
    require(sorted(x.partition('=')[0] for x in extras)==['MINIO_ROOT_PASSWORD','MINIO_ROOT_USER'] and
        all(x.partition('=')[2] and not any(c in x for c in '\r\n\0') for x in extras),
        'FORMAL_REPLICA_ENVIRONMENT_INVALID')
    # Repeat exact private inspect after potentially long tree checks; repeated
    # equality is not a defense against a separate root-level host writer.
    verify_physical_minio_tree(root,physical,lease_guard=current)
    require(_private_docker_json(['inspect',identity],guard=guard)==record,'FORMAL_REPLICA_RESOURCE_CHANGED')
    try:
        result=_guarded_run(['docker','start',identity],guard=guard,timeout=90,code='FORMAL_REPLICA_START_UNCERTAIN')
        require(result.returncode==0 and result.stdout.decode('ascii').strip()==identity,'FORMAL_REPLICA_START_FAILED')
    except (OSError,subprocess.TimeoutExpired,UnicodeError):
        raise FormalSnapshotError('FORMAL_REPLICA_START_FAILED') from None
    return {'state':'ISOLATED_REPLICA_STARTED_PENDING_READBACK','containerId':identity,'imageId':image_id,
        'operationId':operation,'physicalTreeDigest':physical['physicalTreeDigest'],
        'observationSha256':proof['observationSha256'],'productionEvidence':False}
