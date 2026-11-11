"""Deterministic target preservation configuration graph; no I/O or activation.

Callers must supply the current validated target and original pinned bytes. This
does not grant filesystem, mount, SMB, runtime or restore admission. Secrets in
the returned graph belong only in private installation material.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re


def need(condition,code):
    if not condition:raise ValueError('TARGET_PRESERVATION_'+code)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def path(value):
    need(type(value) is str and value.startswith('/') and not value.startswith('//') and
        '\\' not in value and not any(ord(c)<32 for c in value) and value!='/' and
        str(PurePosixPath(value))==value and '..' not in PurePosixPath(value).parts,'PATH_INVALID')
    return value


def pin(value):
    need(type(value) is dict and set(value)=={'path','bytes','sha256'} and
        type(value['bytes']) is int and value['bytes']>0 and type(value['sha256']) is str and
        re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None,'PIN_INVALID')
    path(value['path']);return value


def build_target_preservation_documents(*,target_ref,target,program_policy,configuration_root,
        capture_tools,capture_limits,database_log_mode,smb_credential_format,originals,endpoint_hosts,reference_recipe,derived_classes,
        repository,binder_pin,budgets):
    """Return pinned documents, never an installed/ready/restore authorization."""
    from formal_capture_semantics import validate_reference_recipe,validate_source
    from minimal_capture_support import _configuration_values,source_config_redis
    from recovery_target_capture import _redis_authentication
    from recovery_engine import RecoveryError
    from formal_snapshot_linux import FormalSnapshotError
    need(type(target_ref) is str and bool(target_ref) and type(target.get('targetId')) is str and target['targetId'] and
        program_policy['targetConfigRef']==target_ref,'TARGET_SCOPE_CHANGED')
    root=PurePosixPath(path(configuration_root));epoch=program_policy['backupEpochPolicy']
    need(epoch['schemaVersion']=='SourceBackupEpochPolicy/v1' and
        epoch['databaseUuid']==target['replacement']['databaseUuid'],'EPOCH_CHANGED')
    path(epoch['sourceLockPath']);path(epoch['root'])
    need(database_log_mode in ('GTID','FILE_POSITION'),'DATABASE_LOG_MODE_INVALID')
    services={row['role']:row for row in target['services']}
    need(len(services)==len(target['services'])==5 and set(services)=={'mysql','minio','redis','backend','frontend'} and
        len({r['id'] for r in services.values()})==5 and all(re.fullmatch('[0-9a-f]{64}',r['id']) and
        re.fullmatch('sha256:[0-9a-f]{64}',r['imageId']) for r in services.values()),'SERVICES_CHANGED')
    need(set(capture_tools)=={'docker','ip'} and capture_tools['docker']==target['dockerPin']['path'],'TOOLS_CHANGED')
    for value in capture_tools.values():path(value)
    need(set(budgets)=={'maxArchiveBytes','maxReadbackRecordBytes','maxPreservationSeconds','minimumFreeBytes','maximumRecordBytes'} and
        all(type(v) is int and v>0 for v in budgets.values()) and
        budgets['maximumRecordBytes']<=min(64*1024**2,budgets['maxReadbackRecordBytes']) and
        0<capture_limits['maxWrittenBytes']<=budgets['maxArchiveBytes']<2**63-1 and
        capture_limits['workSeconds']<=budgets['maxPreservationSeconds'] and
        capture_limits['minimumFreeBytes']>=budgets['minimumFreeBytes'],'BUDGET_INVALID')
    need(type(endpoint_hosts) is list and endpoint_hosts and len(set(endpoint_hosts))==len(endpoint_hosts) and
        all(type(h) is str and h and not any(c in h for c in ('/','\\','\0',' ','\t','\n','\r')) for h in endpoint_hosts) and
        services['minio']['ip'] in endpoint_hosts,'ENDPOINT_SCOPE_CHANGED')
    docs=[]
    def add(name,value):
        location=str(root/name);raw=canonical(value)
        reference=dict(path=location,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        need(all(r['pin']['path']!=location for r in docs),'DOCUMENT_COLLISION')
        docs.append(dict(pin=reference,value=deepcopy(value)));return deepcopy(reference)
    def original(reference):
        pin(reference);row=originals.get(reference['path'])
        need(type(row) is dict and row.get('pin')==reference and type(row.get('raw')) is bytes,'ORIGINAL_REQUIRED')
        raw=row['raw']
        need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'ORIGINAL_CHANGED')
        need(0<len(raw)<=65536,'ORIGINAL_SIZE_INVALID')
        return raw
    def secret(reference):
        raw=original(reference)
        need(len(raw)<=16384 and not any(c in raw for c in (b'\0',b'\r',b'\n')),'SECRET_INVALID')
        try:return raw.decode('utf-8')
        except UnicodeError:raise ValueError('TARGET_PRESERVATION_SECRET_ENCODING_INVALID') from None
    identity=add('source-identity.json',dict(sourceFingerprint=epoch['sourceIdentity'],databaseUuid=epoch['databaseUuid']))
    scope=add('source-scope.json',dict(schemaVersion='RecoverySourceScope/v1',sourceIdentityPin=identity,endpointHosts=endpoint_hosts))
    versions=add('versions.json',dict(schemaVersion='MainTargetCaptureVersion/v1',
        targetConfigRef=target_ref,images={role:row['imageId'] for role,row in services.items()}))
    recipe=deepcopy(reference_recipe)
    need(set(recipe)=={'referenceQueries','objectBindings','maxRows','complete','missingReferencePolicy'} and
        all(b.get('bucket',{}).get('literal') in target['buckets'] and set(b['bucket'])=={'literal'}
            for b in recipe['objectBindings']),'REFERENCE_SCOPE_INVALID')
    recipe.update(schemaVersion='backup-capture-reference-recipe/v1',sourceIdentity=epoch['sourceIdentity'],coverageScopePin=scope)
    try:validate_reference_recipe(recipe,epoch['sourceIdentity'],scope)
    except (FormalSnapshotError,ValueError,KeyError,TypeError):raise ValueError('TARGET_PRESERVATION_REFERENCE_INVALID') from None
    recipe_pin=add('reference-recipe.json',recipe)
    need(type(derived_classes) is dict and set(derived_classes)=={'redis','queue'} and
        derived_classes['redis']==dict(classification='RESTORE',executorKey='REDIS_DUMP_ABSOLUTE_EXPIRY',requiredForBusiness=True,rebuildFrom=None) and
        derived_classes['queue']==dict(classification='NOT_PRESENT',executorKey=None,requiredForBusiness=False,rebuildFrom=None),
        'DERIVED_POLICY_INVALID')
    classes={}
    for name,row in derived_classes.items():
        policy=add(name+'-policy.json',dict(schemaVersion='MainTargetDerivedCapturePolicy/v1',
            targetConfigRef=target_ref,sourceIdentity=epoch['sourceIdentity'],**row))
        classes[name]=dict(deepcopy(row),configurationReferences=[policy])
    derived=add('derived-recipe.json',dict(schemaVersion='backup-capture-derived-recipe/v1',sourceIdentity=epoch['sourceIdentity'],classes=classes))
    credentials=add('object-credential.private.json',dict(schemaVersion='backup-source-s3-credential/v1',
        accessKey=secret(target['secrets']['minio']['MINIO_ROOT_USER']),secretKey=secret(target['secrets']['minio']['MINIO_ROOT_PASSWORD'])))
    descriptor=dict(schemaVersion='backup-capture-object-source/v1',sourceIdentity=epoch['sourceIdentity'],
        endpoint='http://'+services['minio']['ip']+':9000',containerPort=9000,minioContainerId=services['minio']['id'],
        credentialReference=credentials,buckets=deepcopy(target['buckets']),sourceScopePin=scope,versionPins=[versions],
        referenceRecipePin=recipe_pin,derivedRecipePin=derived,parentExportIndexPin=None)
    try:validate_source(descriptor,'FULL')
    except (FormalSnapshotError,ValueError,KeyError,TypeError):raise ValueError('TARGET_PRESERVATION_OBJECT_SOURCE_INVALID') from None
    objects=add('objects.json',descriptor)
    mounts=[m for m in target['replacement']['services']['minio']['mounts'] if m['RW'] and m['Destination']=='/data']
    need(len(mounts)==1,'MINIO_DATA_MOUNT_UNPROVEN')
    redis=dict(containerId=services['redis']['id'],host=services['redis']['ip'],database=target['redisRebuild']['database'])
    redis_secret=target.get('secrets',{}).get('redis',{}).get('REDIS_PASSWORD')
    if redis_secret is not None:redis['passwordPin']=deepcopy(pin(redis_secret))
    try:
        source_config_redis(dict(redisSnapshot=redis))
        _redis_authentication(target,redis)
    except (FormalSnapshotError,RecoveryError,ValueError,KeyError,TypeError):raise ValueError('TARGET_PRESERVATION_REDIS_AUTHENTICATION_INVALID') from None
    configuration_pins=target['mainApplication']['configurationPins']
    need(type(configuration_pins) is list and configuration_pins and
        len({canonical(pin(p)) for p in configuration_pins})==len(configuration_pins),'CONFIGURATION_PINS_INVALID')
    capture_ref=target_ref+'-pre-restore'
    capture=dict(schemaVersion='MainTargetCaptureConfiguration/v1',sourceConfigRef=capture_ref,
        outputRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE',sourceLockPath=epoch['sourceLockPath'],
        tools=deepcopy(capture_tools),limits=deepcopy(capture_limits),parent=None,
        source=dict(sourceIdentity=epoch['sourceIdentity'],sourceFingerprint=epoch['sourceIdentity'],databaseUuid=epoch['databaseUuid'],
            database=target['database'],databaseLogMode=database_log_mode,
            mysqlContainerId=services['mysql']['id'],minioContainerId=services['minio']['id'],
            minioDataPath=mounts[0]['Source'],minioMountDestination=mounts[0]['Destination'],
            writerContainerIds=[services[r]['id'] for r in ('backend','frontend')],
            applicationImageIds=sorted({r['imageId'] for r in services.values()}),passwordPin=deepcopy(pin(target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'])),
            objectSourcePin=objects,redisSnapshot=redis,
            configurationPins=[dict(role='configuration-'+str(i).zfill(4),reference=deepcopy(p)) for i,p in enumerate(configuration_pins,1)],
            materialPins=[dict(purpose='source-identity',reference=identity),dict(purpose='versions',reference=versions)]))
    # Filesystem path and runtime admission belong to installed prepare. This
    # pure generator reuses the same production value contract only.
    try:_configuration_values(capture)
    except (FormalSnapshotError,ValueError,KeyError,TypeError):raise ValueError('TARGET_PRESERVATION_CAPTURE_CONFIGURATION_INVALID') from None
    capture_pin=add('capture.json',capture)
    need(set(repository)=={'repositoryId','repositoryRoot','uncRoot','repositoryRelativePath','credentialPin','libraryPins','port','authProtocol'} and
        type(repository['repositoryId']) is str and repository['repositoryId'] and
        type(repository['libraryPins']) is list and 0<len(repository['libraryPins'])<=1000 and
        type(repository['port']) is int and 0<repository['port']<=65535 and
        repository['authProtocol'] in ('ntlm','kerberos'),'REPOSITORY_INVALID')
    repository_root=path(repository['repositoryRoot']);relative=repository['repositoryRelativePath'];unc=repository['uncRoot']
    need(type(relative) is str and relative and not relative.startswith('/') and
        str(PurePosixPath(relative))==relative and '..' not in PurePosixPath(relative).parts and
        '\\' not in relative and not any(ord(c)<32 for c in relative) and
        type(unc) is str and re.fullmatch(r'\\\\[^\\/:*?"<>|\x00-\x20]+\\[^\\/:*?"<>|\x00-\x1f]+',unc) is not None,
        'REPOSITORY_SCOPE_INVALID')
    for reference in [repository['credentialPin'],binder_pin,*repository['libraryPins']]:pin(reference)
    need(smb_credential_format in ('RepositorySmbCredential/v1','CIFS_MOUNT_CREDENTIAL/v1'),'SMB_CREDENTIAL_FORMAT_INVALID')
    try:
        text=original(repository['credentialPin']).decode('utf-8')
        if smb_credential_format=='RepositorySmbCredential/v1':
            def document(items):
                value={}
                for key,item in items:
                    need(key not in value,'SMB_CREDENTIAL_DUPLICATE_KEY');value[key]=item
                return value
            smb=json.loads(text,object_pairs_hook=document)
        else:
            fields={}
            for line in text.splitlines():
                if not line.strip() or line.lstrip().startswith('#'):continue
                key,separator,value=line.partition('=');key=key.strip()
                need(separator and key in ('username','password') and key not in fields,'SMB_MOUNT_CREDENTIAL_INVALID')
                fields[key]=value
            need(set(fields)=={'username','password'},'SMB_MOUNT_CREDENTIAL_INVALID')
            server,share=unc[2:].split('\\')
            smb=dict(schemaVersion='RepositorySmbCredential/v1',server=server,share=share,**fields)
    except (UnicodeError,ValueError):raise ValueError('TARGET_PRESERVATION_SMB_CREDENTIAL_INVALID') from None
    need(type(smb) is dict and set(smb)=={'schemaVersion','server','share','username','password'} and
        smb['schemaVersion']=='RepositorySmbCredential/v1' and
        [smb['server'],smb['share']]==unc[2:].split('\\') and
        all(type(smb[k]) is str and smb[k] and not any(c in smb[k] for c in ('\0','\r','\n'))
            for k in ('username','password')),'SMB_CREDENTIAL_INVALID')
    smb_pin=add('smb-credential.private.json',smb)
    template=add('readback-template.json',dict(schemaVersion='MainTargetPreservationReadbackTemplate/v1',
        uncRoot=unc,repositoryRelativePath=relative,repositoryRoot=repository_root,
        credentialPin=smb_pin,libraryPins=deepcopy(repository['libraryPins']),
        port=repository['port'],authProtocol=repository['authProtocol'],maximumRecordBytes=budgets['maximumRecordBytes'],
        maximumTotalRecordBytes=budgets['maxReadbackRecordBytes'],recordRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION'))
    repository_pin=add('repository.json',dict(schemaVersion='MainTargetPreservationRepository/v2',
        repositoryId=repository['repositoryId'],repositoryRoot=repository_root,sourceIdentityPin=identity,
        captureBinderPin=deepcopy(binder_pin),readbackTemplatePin=template,
        writeView=dict(mountPoint=repository_root,filesystem='cifs',mountSource='//'+unc[2:].replace('\\','/'),mountRoot='/'+relative)))
    policy=add('policy.json',dict(schemaVersion='MainTargetPreservationPolicy/v2',targetConfigRef=target_ref,
        captureRef=capture_ref,captureConfigurationPin=capture_pin,repositoryConfigurationPin=repository_pin,
        backupEpochPolicy=deepcopy(epoch),**{k:v for k,v in budgets.items() if k!='maximumRecordBytes'}))
    return dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',targetConfigRef=target_ref,
        documents=docs,captureRef=capture_ref,capturePin=capture_pin,repositoryPin=repository_pin,policyPin=policy,
        originalCredentialPins=[deepcopy(target['secrets']['minio'][key]) for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')]+[deepcopy(repository['credentialPin'])])
