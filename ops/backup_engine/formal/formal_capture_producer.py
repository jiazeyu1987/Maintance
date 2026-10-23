"""Standard finite capture, explicit shared recovery and health observation.

Requires an already acquired, separately authorized maintenance claim. Does not
establish/release DB barriers, release ingress/claim, or publish to NAS. The v3
actions stop or restore only the prebound shared workloads. They do not prove
host/admin exclusion or production readiness. Explicit v4 actions recover or
observe the prebound external callers only after live shared dependency health.
Explicit v5 binds approved original scopes and health in a fresh claim. It never
installs exclusion, stops callers, acquires a database fence or starts capture.
"""
import sys
if __name__=='__main__':
    sys.dont_write_bytecode=True

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import time
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime, WatchdogError
from formal_snapshot_linux import (FormalSnapshotError, FormalMaintenanceClaim,
    PrivateDockerMySql, capture_claimed_formal_payload, require, _existing_file)
from formal_s3_export import _strict_json


def read_private(path, limit):
    path = _existing_file(path)
    require(path.stat().st_size <= limit and (os.name != 'posix' or
            stat.S_IMODE(path.stat().st_mode) == 0o600), 'FORMAL_CAPTURE_PRIVATE_INPUT_INVALID')
    return path.read_bytes()


def read_credential(path):
    credential=read_private(path,16384).decode('utf-8')
    require(credential.endswith('\n') and len(credential.splitlines())==1 and
            credential.strip() and not any(c in credential[:-1] for c in '\r\n\0'),
            'FORMAL_MYSQL_CREDENTIAL_INVALID')
    return credential[:-1]


def read_approved_source_target(path):
    path=_existing_file(path);before=path.stat()
    require(0<before.st_size<=65536,'FORMAL_CAPTURE_SOURCE_APPROVAL_REQUIRED')
    with path.open('rb') as source:raw=source.read(65537)
    after=_existing_file(path).stat()
    require(0<len(raw)<=65536 and
        (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
        (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),
        'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
    return raw


def validate_observation_request(request):
    require(type(request) is dict and set(request)=={'schemaVersion','action','claimRoot','claimBinding',
        'mysqlContainerId','mysqlCredentialFile','healthSeconds','sharedScopeSha256','originalHealthSha256',
        'ingressRulesSha256'} and request['schemaVersion']=='release-formal-capture-request/v2' and
        request['action']=='observe-shared-health','FORMAL_CAPTURE_REQUEST_INVALID')
    binding=request['claimBinding']
    require(type(binding) is dict and set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'},
            'FORMAL_CAPTURE_REQUEST_INVALID')
    require(type(request['mysqlContainerId']) is str and re.fullmatch('[0-9a-f]{64}',request['mysqlContainerId']) and
        type(request['healthSeconds']) is int and 1<=request['healthSeconds']<=300 and
        all(type(request[k]) is str and re.fullmatch('[0-9a-f]{64}',request[k]) for k in
            ('sharedScopeSha256','originalHealthSha256','ingressRulesSha256')),'FORMAL_CAPTURE_REQUEST_INVALID')


def validate_shared_request(request):
    common={'schemaVersion','action','claimRoot','claimBinding','mysqlContainerId',
        'mysqlCredentialFile','totalSeconds','sharedScopeSha256','originalHealthSha256','ingressRulesSha256'}
    capture={'database','sourceRoot','dataLimits','rejectionProbe','filesystemFence'}
    require(type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v3' and
        request.get('action') in ('capture-shared-payload','restore-shared-services') and
        set(request)==common.union(capture if request['action']=='capture-shared-payload' else set()),
        'FORMAL_CAPTURE_REQUEST_INVALID')
    binding=request['claimBinding']
    require(type(binding) is dict and set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'} and
        type(binding['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['operationId']) and
        type(binding['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['databaseUuid']) and
        all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k]) for k in ('sourceFingerprint','minioContainerId')),
        'FORMAL_CAPTURE_REQUEST_INVALID')
    require(type(request['totalSeconds']) is int and 1<=request['totalSeconds']<=7200 and
        all(type(request[k]) is str and re.fullmatch('[0-9a-f]{64}',request[k]) for k in
            ('mysqlContainerId','sharedScopeSha256','originalHealthSha256','ingressRulesSha256')) and
        all(type(request[k]) is str and request[k] and '\0' not in request[k] for k in ('claimRoot','mysqlCredentialFile')),
        'FORMAL_CAPTURE_REQUEST_INVALID')
    if request['action']=='capture-shared-payload':
        from formal_data_evidence import validate_limits
        require(type(request['database']) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',request['database']) and
            type(request['sourceRoot']) is str and request['sourceRoot'] and '\0' not in request['sourceRoot'],
            'FORMAL_CAPTURE_REQUEST_INVALID')
        validate_limits(request['dataLimits'])
        probe=request['rejectionProbe'];fence=request['filesystemFence']
        require(type(probe) is dict and set(probe)=={'table','column'} and
            all(type(v) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',v) for v in probe.values()) and
            type(fence) is dict and set(fence)=={'mount','seconds','binding'} and
            type(fence['seconds']) is int and 1<=fence['seconds']<=300 and fence['seconds']<request['totalSeconds'] and
            type(fence['mount']) is str and fence['mount'] and '\0' not in fence['mount'] and
            type(fence['binding']) is dict and set(fence['binding'])=={'operationId','bootId','mount'} and
            fence['binding']['operationId']==binding['operationId'] and
            type(fence['binding']['bootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',fence['binding']['bootId']) and
            type(fence['binding']['mount']) is dict and set(fence['binding']['mount'])=={'source','device','fstype','target'} and
            fence['binding']['mount']['target']==fence['mount'] and fence['binding']['mount']['fstype']=='ext4' and
            type(fence['binding']['mount']['source']) is str and fence['binding']['mount']['source'].startswith('/dev/') and
            type(fence['binding']['mount']['device']) is str and re.fullmatch('[0-9]+:[0-9]+',fence['binding']['mount']['device']),
            'FORMAL_CAPTURE_REQUEST_INVALID')


def validate_source_request(request, approved_source):
    """v12 is an explicit source-aware capture, never a legacy downgrade."""
    require(type(request) is dict and request.get('schemaVersion') == 'release-formal-capture-request/v12' and
        request.get('action') == 'capture-shared-payload' and 'sourceScope' in request and
        type(request.get('claimBinding')) is dict and
        type(approved_source) is dict and request['sourceScope'] == approved_source and
        approved_source.get('environment') == 'prod' and
        approved_source.get('database') == request.get('database') and
        approved_source.get('databaseUuid') == request.get('claimBinding',{}).get('databaseUuid'),
        'FORMAL_CAPTURE_SOURCE_APPROVAL_REQUIRED')
    require(request['claimBinding'].get('sourceFingerprint')==approved_source.get('targetFingerprint'),
        'FORMAL_CAPTURE_SOURCE_CLAIM_CHANGED')
    # Reuse only the structural common-field validation. Execution keeps v12
    # and its independently derived source authority intact throughout.
    common={k:v for k,v in request.items() if k!='sourceScope'}
    common['schemaVersion']='release-formal-capture-request/v3'
    validate_shared_request(common)


def _validate_selected_source_request(request, approved_source):
    if type(request) is dict and request.get('schemaVersion') == 'backup-lab-capture-request/v1':
        from formal_backup_lab import validate_capture_request, require_authority
        validate_capture_request(request,approved_source);require_authority(approved_source)
        return
    validate_source_request(request,approved_source)


def _valid_capture_release(release, claim):
    if type(release) is dict and release.get('schemaVersion') == 'backup-lab-original-package-binding/v1':
        from formal_backup_lab import current_authority, validate_original_binding
        validate_original_binding(snapshot._canonical_bytes(release),current_authority(),claim)
        return True
    return type(release) is dict and release.get('schemaVersion') == 'release-formal-original-package-binding/v2' and release.get('claimBindingSha256') == hashlib.sha256(claim._plan).hexdigest() and release.get('productionEvidence') is False


def _valid_resume_owner(resume_checks, claim):
    if type(resume_checks) is ProductionAResumeChecks:return resume_checks.claim is claim
    from formal_backup_lab import LabResumeChecks, current_authority
    require(type(resume_checks) is LabResumeChecks,'FORMAL_PRODUCTION_A_RESUME_OWNER_INVALID')
    authority=current_authority()
    require(resume_checks.authority is authority and resume_checks.claim is claim,'BACKUP_LAB_OWNER_CHANGED')
    return True


def _observe_approved_source_storage(request,target):
    """Prove the approved primary filesystem and exact current bind subtree."""
    import formal_split_capture as split
    source=Path(request['sourceRoot']);data=Path(target['dataRoot'])
    alias=Path(target['root'])/'data';primary=Path(target['dataMount'])
    fence=request['filesystemFence'];mount=Path(fence['mount'])
    paths={source,data,data/'minio',primary,mount}
    alias_used=source!=data/'minio' or mount==alias
    if alias_used:paths.add(alias)
    def identities():
        selected={}
        for path in paths:
            require(path.is_absolute() and path.is_dir() and not path.is_symlink() and path.resolve()==path,
                'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
            info=path.stat();selected[path]=(info.st_dev,info.st_ino)
        require(selected[source]==selected[data/'minio'] and
            all(identity[0]==selected[primary][0] for identity in selected.values()),
            'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        if alias_used:require(selected[alias]==selected[data],'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        return selected
    before=identities()
    split._observe_native_environment(dict(operationId=fence['binding']['operationId'],
        bootId=fence['binding']['bootId'],mount=dict(source=target['dataDevice'],
            device=fence['binding']['mount']['device'],fstype='ext4',target=target['dataMount'])))
    # Preserve the alias's full /dev/device[/subtree] string for native findmnt.
    split._observe_native_environment(fence['binding'])
    require(identities()==before,'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
    return {str(path):identity for path,identity in before.items()}


def verify_approved_source_storage(claim,request,target_raw):
    """No alternate data tree: bind approved paths, original role names and inode."""
    try:
        claim.assert_owned();target=_strict_json(target_raw)
        def posix(value):
            require(type(value) is str and value.startswith('/') and '\\' not in value and '\0' not in value and
                all(part not in ('.','..') for part in value.split('/')) and str(PurePosixPath(value))==value,
                'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
            return PurePosixPath(value)
        data=posix(target['dataRoot']);primary=posix(target['dataMount']);alias=posix(target['root'])/'data'
        require(data==primary or primary in data.parents,'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        source=posix(request['sourceRoot']);fence=request['filesystemFence'];mount=posix(fence['mount'])
        require(source in (data/'minio',alias/'minio') and mount in (primary,alias),
            'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        expected_device=target['dataDevice'] if mount==primary or data==primary else (
            target['dataDevice']+'[/'+str(data.relative_to(primary))+']')
        require(fence['binding']['mount']['source']==expected_device and
            fence['binding']['mount']['target']==str(mount),'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        raw=claim._read(claim.root/'shared-container-original.json');shared=_strict_json(raw)
        require(hashlib.sha256(raw).hexdigest()==request['sharedScopeSha256'] and
            all(shared[role]['name']=='/'+name for role,name in target['containers'].items()),
            'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        mounts=shared['minio']['mounts']
        require(type(mounts) is list,'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        selected=[row for row in mounts if type(row) is dict and row.get('Destination')=='/data']
        require(len(selected)==1 and selected[0].get('RW') is True and
            selected[0].get('Source')==request['sourceRoot'],'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        identity=_observe_approved_source_storage(request,target)
        require(type(identity) is dict and identity and all(type(key) is str and type(value) is tuple and
            len(value)==2 and all(type(part) is int and part>0 for part in value)
            for key,value in identity.items()),'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
        claim.assert_owned()
        return identity
    except (OSError,KeyError,TypeError,ValueError):
        raise FormalSnapshotError('FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED') from None


def author_source_capture_request(claim, options, approved_target_path, approved_target_sha, *, guard):
    """Author one v12 from current owned originals; no capture or claim release.

    The caller supplies independently approved source bytes and current native
    owner. Options carry limits/paths, never original digests or source authority.
    Native phase/device/database observers remain required before persistence.
    """
    from formal_source_migration_ledger import approved_source_scope
    import formal_ingress_control as ingress
    import formal_split_capture as split
    require(callable(guard) and type(options) is dict and set(options)=={
        'database','sourceRoot','mysqlCredentialFile','totalSeconds','dataLimits','rejectionProbe','filesystemFence'},
        'FORMAL_CAPTURE_AUTHOR_INPUT_INVALID')
    try:
        claim.assert_owned()
        options_raw=snapshot._canonical_bytes(options)
        selected=_strict_json(options_raw)
        binding=_strict_json(claim._plan)
        target_path=_existing_file(approved_target_path)
        target_raw=read_approved_source_target(target_path)
        source_scope=approved_source_scope(target_raw,approved_target_sha,claim._plan,selected['database'])
        request_path=claim.root/'source-capture-request.json'
        require(not request_path.exists() and not request_path.is_symlink(),
            'FORMAL_CAPTURE_SOURCE_REQUEST_EXISTS')
        def metadata(path):
            info=_existing_file(path).stat()
            return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns
        target_identity=metadata(target_path)
        originals={}
        for name in ('shared-container-original.json','shared-health-original.json'):
            path=claim.root/name
            identity=metadata(path);raw=claim._read(path)
            require(metadata(path)==identity,'FORMAL_CAPTURE_AUTHOR_ORIGINAL_CHANGED')
            originals[name]=(raw,identity)
        shared=_strict_json(originals['shared-container-original.json'][0])
        held=ingress.assert_ingress(claim)
        require(held['phase']=='CAPTURE_RESTRICTED','FORMAL_CAPTURE_INGRESS_CHANGED')
        request=dict(selected,schemaVersion='release-formal-capture-request/v12',action='capture-shared-payload',
            claimRoot=str(claim.root),claimBinding=binding,mysqlContainerId=shared['mysql']['id'],
            sharedScopeSha256=hashlib.sha256(originals['shared-container-original.json'][0]).hexdigest(),
            originalHealthSha256=hashlib.sha256(originals['shared-health-original.json'][0]).hexdigest(),
            ingressRulesSha256=held['rulesSha256'],sourceScope=source_scope)
        validate_source_request(request,source_scope)
        credential_path=_existing_file(request['mysqlCredentialFile'])
        credential_identity=metadata(credential_path)
        credential_raw=read_private(credential_path,16384)
        credential=read_credential(credential_path)
        require(metadata(credential_path)==credential_identity and
            read_private(credential_path,16384)==credential_raw,'FORMAL_CAPTURE_AUTHOR_CREDENTIAL_CHANGED')
        deadline=time.monotonic()+request['totalSeconds']
        outer=snapshot.observation_deadline.get()
        if outer is not None:deadline=min(deadline,outer)
        token=snapshot.observation_deadline.set(deadline)
        try:
            storage_identity=None
            def current():
                nonlocal storage_identity
                guard();claim.assert_owned()
                require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
                require(snapshot._canonical_bytes(options)==options_raw,'FORMAL_CAPTURE_AUTHOR_INPUT_CHANGED')
                require(metadata(target_path)==target_identity and read_approved_source_target(target_path)==target_raw,
                    'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
                for name,(raw,identity) in originals.items():
                    require(metadata(claim.root/name)==identity and claim._read(claim.root/name)==raw,
                        'FORMAL_CAPTURE_AUTHOR_ORIGINAL_CHANGED')
                require(metadata(credential_path)==credential_identity and
                    read_private(credential_path,16384)==credential_raw,'FORMAL_CAPTURE_AUTHOR_CREDENTIAL_CHANGED')
                held_now=ingress.assert_ingress(claim)
                require(held_now['phase']=='CAPTURE_RESTRICTED' and
                    held_now['rulesSha256']==request['ingressRulesSha256'],'FORMAL_CAPTURE_INGRESS_CHANGED')
                fresh_storage=verify_approved_source_storage(claim,request,target_raw)
                if storage_identity is None:storage_identity=dict(fresh_storage)
                require(fresh_storage==storage_identity,'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
                split._thaw_receipt(claim)
                snapshot.observation_timeout(1)
            current()
            verify_shared_request_binding(claim,request)
            mysql=PrivateDockerMySql(request['mysqlContainerId'],credential,timeout=5)
            verify_shared_database_before_stop(claim,mysql)
            current()
            require(deadline-time.monotonic()>request['filesystemFence']['seconds']+20,
                'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
            raw=snapshot._canonical_bytes(request)
            require(len(raw)<=16384,'FORMAL_CAPTURE_AUTHOR_INPUT_INVALID')
            claim._write(request_path,raw)
            request_identity=metadata(request_path)
            require(read_private(request_path,16384)==raw,'FORMAL_CAPTURE_SOURCE_REQUEST_CHANGED')
            current()
            verify_shared_request_binding(claim,request)
            verify_shared_database_before_stop(claim,mysql)
            current()
            require(metadata(request_path)==request_identity and read_private(request_path,16384)==raw,
                'FORMAL_CAPTURE_SOURCE_REQUEST_CHANGED')
            return dict(state='SOURCE_CAPTURE_REQUEST_PREPARED_INGRESS_HELD',
                requestFile=str(request_path),requestSha256=hashlib.sha256(raw).hexdigest(),
                sourceScope=source_scope,productionEvidence=False,fullRunnerCompleted=False,
                serviceActionsPerformed=False,claimReleased=False)
        finally:snapshot.observation_deadline.reset(token)
    except OSError:
        raise FormalSnapshotError('FORMAL_CAPTURE_SOURCE_REQUEST_IO_FAILED') from None
    except (KeyError,TypeError,ValueError):
        raise FormalSnapshotError('FORMAL_CAPTURE_AUTHOR_INPUT_INVALID') from None


def validate_dependency_request(request):
    require(type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v7' and
        request.get('action')=='restore-shared-dependencies','FORMAL_CAPTURE_REQUEST_INVALID')
    # Reuse shared field validation only, not the old whole-service action.
    selected=dict(request,schemaVersion='release-formal-capture-request/v3',action='restore-shared-services')
    validate_shared_request(selected)


def validate_external_request(request):
    require(type(request) is dict and set(request)=={'schemaVersion','action','claimRoot','claimBinding',
        'mysqlContainerId','mysqlCredentialFile','totalSeconds','sharedScopeSha256','originalHealthSha256',
        'ingressRulesSha256','externalScopeSha256','externalOriginalHealthSha256'} and
        request['schemaVersion']=='release-formal-capture-request/v4' and
        request['action'] in ('restore-external-services','observe-external-health'),
        'FORMAL_CAPTURE_REQUEST_INVALID')
    # Reuse the exact shared recovery identity/deadline contract, without
    # selecting or running the shared recovery action.
    selected={k:v for k,v in request.items() if k not in ('externalScopeSha256','externalOriginalHealthSha256')}
    selected.update(schemaVersion='release-formal-capture-request/v3',action='restore-shared-services')
    validate_shared_request(selected)
    require(all(type(request[k]) is str and re.fullmatch('[0-9a-f]{64}',request[k]) for k in
        ('externalScopeSha256','externalOriginalHealthSha256')),'FORMAL_CAPTURE_REQUEST_INVALID')


def validate_initialization_request(request):
    import formal_split_capture as split
    import formal_external_callers as callers
    require(type(request) is dict and set(request)=={'schemaVersion','action','claimRoot','claimBinding',
        'mysqlCredentialFile','totalSeconds','sharedContainerIds','externalCallers','sourceRoot',
        'sourceMountBinding','expectedSharedScopeSha256','expectedExternalScopeSha256','expectedDatabaseFlags'} and
        request['schemaVersion']=='release-formal-capture-request/v5' and
        request['action']=='bind-maintenance-originals','FORMAL_CAPTURE_REQUEST_INVALID')
    binding=request['claimBinding'];roles=request['sharedContainerIds'];flags=request['expectedDatabaseFlags']
    require(type(binding) is dict and set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'} and
        type(binding['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['operationId']) and
        type(binding['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['databaseUuid']) and
        all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k]) for k in ('sourceFingerprint','minioContainerId')),
        'FORMAL_CAPTURE_REQUEST_INVALID')
    require(type(roles) is dict and set(roles)==split.ROLES and len(set(roles.values()))==7 and
        all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for v in roles.values()) and
        roles['minio']==binding['minioContainerId'] and type(request['totalSeconds']) is int and
        1<=request['totalSeconds']<=7200 and all(type(request[k]) is str and request[k] and '\0' not in request[k]
        for k in ('claimRoot','mysqlCredentialFile','sourceRoot')) and
        all(type(request[k]) is str and re.fullmatch('[0-9a-f]{64}',request[k]) for k in
        ('expectedSharedScopeSha256','expectedExternalScopeSha256')),'FORMAL_CAPTURE_REQUEST_INVALID')
    require(type(flags) is dict and set(flags)=={'serverUuid','readOnly','superReadOnly'} and
        flags['serverUuid']==binding['databaseUuid'] and type(flags['readOnly']) is int and flags['readOnly'] in (0,1) and
        type(flags['superReadOnly']) is int and flags['superReadOnly']==0,'FORMAL_CAPTURE_REQUEST_INVALID')
    source=request['sourceMountBinding']
    require(type(source) is dict and set(source)=={'operationId','bootId','mount'} and
        source['operationId']==binding['operationId'] and type(source['bootId']) is str and
        re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',source['bootId']) and
        type(source['mount']) is dict and set(source['mount'])=={'source','device','fstype','target'} and
        type(source['mount']['source']) is str and source['mount']['source'].startswith('/dev/') and
        type(source['mount']['device']) is str and re.fullmatch('[0-9]+:[0-9]+',source['mount']['device']) and
        source['mount']['fstype']=='ext4' and type(source['mount']['target']) is str and
        source['mount']['target'].startswith('/'),'FORMAL_CAPTURE_REQUEST_INVALID')
    callers._plan(request['externalCallers'])


def verify_initialization_devices(request):
    """Read-only bound source observation; not a thaw or writer exclusion proof."""
    import formal_split_capture as split
    source=Path(request['sourceRoot']);mount=Path(request['sourceMountBinding']['mount']['target'])
    control=Path(request['claimRoot']).parent;credential=_existing_file(request['mysqlCredentialFile'])
    require(source.is_absolute() and source.is_dir() and source.resolve()==source and not source.is_symlink() and
        mount.is_absolute() and mount.is_dir() and mount.resolve()==mount and not mount.is_symlink() and
        (source==mount or mount in source.parents) and source.stat().st_dev==mount.stat().st_dev and
        control.is_absolute() and control.is_dir() and control.resolve()==control and not control.is_symlink() and
        control.stat().st_dev!=source.stat().st_dev and credential.stat().st_dev==control.stat().st_dev,
        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
    split._observe_native_environment(request['sourceMountBinding'])
    snapshot.observation_timeout(1)


def run_initialization_request(claim,request,request_guard):
    """Only original binding. Missing host/drain controls never become PASS.

    Fresh-only semantics retain every partial file/journal on failure; the
    caller must not resume this action to repair or rebind partial originals.
    """
    import formal_split_capture as split
    import formal_service_health as health
    import formal_external_callers as callers
    request=_strict_json(snapshot._canonical_bytes(request))
    validate_initialization_request(request)
    token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
    try:
        def within():snapshot.observation_timeout(1)
        within();claim.assert_owned();request_guard();within()
        require(not claim.events and _strict_json(claim._plan)==request['claimBinding'],
            'FORMAL_CAPTURE_INITIALIZATION_STAGE_INVALID')
        bound={};mysql=None
        def guard():
            within();claim.assert_owned();request_guard();within()
            verify_initialization_devices(request)
            require(_strict_json(claim._plan)==request['claimBinding'] and
                all(e['step'] in {'shared-container-scope','external-caller-scope','shared-health-scope',
                    'external-health-scope','maintenance-originals-bound'} for e in claim.events),
                'FORMAL_CAPTURE_INITIALIZATION_STAGE_INVALID')
            for name,raw in bound.items():
                require(claim._read(claim.root/name)==raw,'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
            if 'shared-container-original.json' in bound:
                split._observe_shared_actions(claim)
                for role in split.ROLES:
                    original,current,_=split._shared_role(claim,role)
                    require(current==original,'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
            if 'external-callers-original.json' in bound:
                _,originals,current,_=callers._observe(claim,transport)
                require(current==originals,'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
            if mysql is not None:
                require(snapshot._database_flags(mysql,request['claimBinding']['databaseUuid'])==request['expectedDatabaseFlags'],
                    'FORMAL_CAPTURE_INITIALIZATION_FLAGS_CHANGED')
            # Runtime and request callbacks may run after the initial read.
            # Recheck all original bytes after the last such observation.
            for name,raw in bound.items():
                require(claim._read(claim.root/name)==raw,'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
            within()
        transport=callers.SshDockerTransport()
        guard()
        roles=request['sharedContainerIds']
        observed={role:snapshot.inspect_formal_container(identity) for role,identity in sorted(roles.items())}
        require(hashlib.sha256(snapshot._canonical_bytes(observed)).hexdigest()==request['expectedSharedScopeSha256'],
            'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
        external={role:transport.inspect(selected['connection'],selected['containerId'])
            for role,selected in request['externalCallers'].items()}
        require(hashlib.sha256(snapshot._canonical_bytes({'plan':request['externalCallers'],'originals':external})).hexdigest()==
            request['expectedExternalScopeSha256'],'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
        credential=read_credential(request['mysqlCredentialFile'])
        mysql=PrivateDockerMySql(roles['mysql'],credential,timeout=5)
        require(snapshot._database_flags(mysql,request['claimBinding']['databaseUuid'])==request['expectedDatabaseFlags'],
            'FORMAL_CAPTURE_INITIALIZATION_FLAGS_CHANGED')
        guard();split.bind_shared_container_scope(claim,roles)
        bound['shared-container-original.json']=claim._read(claim.root/'shared-container-original.json')
        require(hashlib.sha256(bound['shared-container-original.json']).hexdigest()==request['expectedSharedScopeSha256'],
            'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
        guard();callers.bind_external_callers(claim,request['externalCallers'],transport)
        bound['external-callers-original.json']=claim._read(claim.root/'external-callers-original.json')
        require(hashlib.sha256(bound['external-callers-original.json']).hexdigest()==request['expectedExternalScopeSha256'],
            'FORMAL_CAPTURE_INITIALIZATION_SCOPE_CHANGED')
        guard()
        health.bind_shared_health_scope(claim,mysql,guard=guard,redis_authentication='none',
            timeout=min(300,snapshot.observation_timeout(request['totalSeconds'])))
        bound['shared-health-original.json']=claim._read(claim.root/'shared-health-original.json')
        guard()
        require(health._original_health(claim)['health']['mysql']['proof']['flags']==request['expectedDatabaseFlags'],
            'FORMAL_CAPTURE_INITIALIZATION_FLAGS_CHANGED')
        callers.bind_external_health_scope(claim,transport,guard=guard,
            seconds=min(300,snapshot.observation_timeout(request['totalSeconds'])))
        bound['external-callers-health-original.json']=claim._read(claim.root/'external-callers-health-original.json')
        guard();callers._original_health(claim)
        require(snapshot._database_flags(mysql,request['claimBinding']['databaseUuid'])==request['expectedDatabaseFlags'],
            'FORMAL_CAPTURE_INITIALIZATION_FLAGS_CHANGED')
        digests={name:hashlib.sha256(raw).hexdigest() for name,raw in bound.items()}
        guard();claim.record('maintenance-originals-bound',{'originalFileSha256':digests})
        guard();within()
        return {'state':'MAINTENANCE_ORIGINALS_BOUND_PENDING_EXCLUSION','originalFileSha256':digests,
            'originalDatabaseFlags':request['expectedDatabaseFlags'],'serviceActionsPerformed':False,
            'hostWritersVerified':False,'ingressInstalled':False,'databaseFenceAcquired':False,
            'productionEvidence':False,'fullRunnerCompleted':False,'fullInitializationCompleted':False,'claimReleased':False}
    finally:snapshot.observation_deadline.reset(token)


def verify_shared_request_binding(claim,request):
    """Verify prebound originals before any phase mutation, never rebind them."""
    import formal_split_capture as split
    import formal_service_health as health
    require(_strict_json(claim._plan)==request['claimBinding'],'FORMAL_CAPTURE_CLAIM_CHANGED')
    shared_raw=claim._read(claim.root/'shared-container-original.json')
    shared=_strict_json(shared_raw)
    require(shared_raw==snapshot._canonical_bytes(shared) and type(shared) is dict and set(shared)==split.ROLES and
        hashlib.sha256(shared_raw).hexdigest()==request['sharedScopeSha256'] and
        snapshot._claim_event(claim,'shared-container-scope')['details']=={'scopeSha256':request['sharedScopeSha256']} and
        shared['mysql']['id']==request['mysqlContainerId'] and shared['minio']['id']==request['claimBinding']['minioContainerId'],
        'FORMAL_CAPTURE_SHARED_SCOPE_CHANGED')
    health_raw=claim._read(claim.root/'shared-health-original.json')
    require(hashlib.sha256(health_raw).hexdigest()==request['originalHealthSha256'] and
        snapshot._claim_event(claim,'shared-health-scope')['details']=={'sha256':request['originalHealthSha256']},
        'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
    original_health=health._original_health(claim)
    require(type(original_health) is dict and set(original_health)=={'schemaVersion','sharedScopeSha256',
        'claimSha256','health','redisAuthentication','observedAt'} and
        original_health['schemaVersion']=='formal-shared-health-original/v1' and
        original_health['redisAuthentication']=='none' and type(original_health['health']) is dict and
        set(original_health['health'])==split.ROLES and
        all(type(original_health['health'][role]) is dict and
            original_health['health'][role]['state']==('HEALTHY' if shared[role]['state']['Running'] else 'ORIGINALLY_STOPPED')
            for role in split.ROLES),'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
    for role in split.ROLES:
        record=original_health['health'][role]
        if record['state']=='ORIGINALLY_STOPPED':
            require(record=={'state':'ORIGINALLY_STOPPED','healthObserved':False},'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
            continue
        require(set(record)=={'state','proof'} and type(record['proof']) is dict,'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
        proof=record['proof']
        if role=='mysql':
            require(set(proof)=={'protocol','flags'} and proof['protocol']=='mysql','FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
        else:
            require(type(proof.get('networkNamespaceInode')) is int and proof['networkNamespaceInode']>0 and
                type(proof.get('pid')) is int and proof['pid']>0,'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
        if role=='redis':require(set(proof)=={'protocol','authentication','response','networkNamespaceInode','pid'} and
            proof['protocol']=='redis' and proof['authentication']=='none' and proof['response']=='PONG',
            'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
        elif role!='mysql':
            require(set(proof)=={'httpStatus','bytes','sha256','networkNamespaceInode','pid'} and proof['httpStatus']==200 and
                type(proof['bytes']) is int and 0<=proof['bytes']<=65536 and
                type(proof['sha256']) is str and re.fullmatch('[0-9a-f]{64}',proof['sha256']) and
                (role not in ('frontend','showroom') or proof['bytes']>0),'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
    _,flags,digest=snapshot._claimed_database_original(claim)
    require(snapshot._claim_event(claim,'db-fenced')['details']['originalSha256']==digest and
        original_health['health']['mysql']['proof']['flags']==flags,
        'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
    require(Path(request['mysqlCredentialFile']).stat().st_dev==claim.root.stat().st_dev,
        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
    if request['action']=='capture-shared-payload':
        source=Path(request['sourceRoot']);mount=Path(request['filesystemFence']['mount'])
        require(source.is_absolute() and source.is_dir() and source.resolve()==source and not source.is_symlink() and
            mount.is_absolute() and mount.is_dir() and mount.resolve()==mount and not mount.is_symlink() and
            (source==mount or mount in source.parents) and source.stat().st_dev==mount.stat().st_dev and
            claim.root.stat().st_dev!=source.stat().st_dev,'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
        split._observe_native_environment(request['filesystemFence']['binding'])
    return {'shared':shared_raw,'health':health_raw}


def verify_shared_database_before_stop(claim,mysql):
    """Live pre-stop check; the full split SQL barrier requires completed stops."""
    import formal_split_capture as split
    split._active(claim,set())
    identity,_,digest=snapshot._claimed_database_original(claim)
    require(snapshot._claim_event(claim,'db-fenced')['details']['originalSha256']==digest,
        'FORMAL_DATABASE_NOT_QUIESCENT')
    original,current,_=split._shared_role(claim,'mysql')
    require(mysql.container==original['id'] and current['state']==original['state'] and current['state']['Running'],
        'FORMAL_SPLIT_MYSQL_CHANGED')
    split._observe_shared_actions(claim)
    require(snapshot._database_flags(mysql,identity)=={'serverUuid':identity,'readOnly':1,'superReadOnly':1},
        'FORMAL_DATABASE_NOT_QUIESCENT')
    snapshot.observe_database_barrier(mysql)
    split._active(claim,set())


class SharedDependencySourceChecks:
    """Fixed recovery sources and five closed host entries, not full exclusion.

    Construct once before credentials or recovery intent. Never learn a new
    original inode or external scope from a later successful observation.
    """
    NAMES=('shared-container-original.json','shared-health-original.json','database-original.json',
        'external-callers-original.json','ingress-plan.json','ingress-installed.json',
        'ingress-recovery-plan.json','ingress-recovery-installed.json')

    def __init__(self,claim,request):
        import formal_external_callers as callers
        import formal_host_admission as host
        self.claim=claim;self.rules_sha256=request['ingressRulesSha256']
        self.pins={claim.root/name:self._read(claim.root/name) for name in self.NAMES}
        def original_sha(name):return hashlib.sha256(self.pins[claim.root/name][0]).hexdigest()
        self.external_sha256=original_sha('external-callers-original.json')
        require(original_sha('shared-container-original.json')==request['sharedScopeSha256'] and
            original_sha('shared-health-original.json')==request['originalHealthSha256'] and
            original_sha('ingress-recovery-installed.json')==self.rules_sha256 and
            snapshot._claim_event(claim,'external-caller-scope')['details']=={'scopeSha256':self.external_sha256} and
            snapshot._claim_event(claim,'db-fenced')['details']['originalSha256']==original_sha('database-original.json'),
            'FORMAL_SHARED_RECOVERY_REGISTERED_SOURCE_CHANGED')
        self.host=host.ClosedHostAdmissionChecks(claim)
        self.transport=callers.SshDockerTransport()
        self._inputs()

    @staticmethod
    def _read(path):
        import formal_boot_state as boot
        try:return boot._read_secure(path,0o600,16384,no_atime=True)
        except OSError as exc:
            raise FormalSnapshotError('FORMAL_SHARED_RECOVERY_REGISTERED_SOURCE_OS_ERROR_'+str(exc.errno)) from exc

    def _inputs(self,*,content=True):
        import formal_boot_state as boot
        for path,pair in self.pins.items():
            if content:
                require(self._read(path)==pair,'FORMAL_SHARED_RECOVERY_REGISTERED_SOURCE_CHANGED')
            try:current=boot._signature(os.stat(path,follow_symlinks=False))
            except OSError as exc:
                raise FormalSnapshotError('FORMAL_SHARED_RECOVERY_REGISTERED_SOURCE_OS_ERROR_'+str(exc.errno)) from exc
            require(current==pair[1],'FORMAL_SHARED_RECOVERY_REGISTERED_SOURCE_CHANGED')

    def assert_valid(self,*,guard,deadline):
        import formal_external_callers as callers
        import formal_ingress_control as ingress
        guard();self._inputs()
        self.host.prepare(guard=lambda:self._inputs(content=False),deadline=deadline)
        held=ingress.assert_ingress(self.claim)
        require(type(held) is dict and held.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
            held.get('rulesSha256')==self.rules_sha256,'FORMAL_CAPTURE_INGRESS_CHANGED')
        external=callers.guard_external_callers(self.claim,self.transport)
        require(type(external) is dict and external.get('scopeSha256')==self.external_sha256 and
            external.get('state')=='KNOWN_EXTERNAL_CALLERS_STOPPED_PENDING_FULL_EXCLUSION',
            'FORMAL_SHARED_RECOVERY_CALLERS_CHANGED')
        self._inputs()
        # All owner callbacks and private reads finish before the last native
        # host observation. Only fixed source metadata follows that observation.
        self.host.assert_native(deadline=deadline)
        self._inputs(content=False)


def run_controlled_shared_capture_request(claim,request,request_guard,*,approved_source,native_guard,container_actions):
    """Explicit A capture after completed prefence stops; never infer a skip."""
    require(type(request) is dict and request.get('schemaVersion') in ('release-formal-capture-request/v12','backup-lab-capture-request/v1') and
        request.get('action')=='capture-shared-payload','FORMAL_CONTROLLED_CAPTURE_REQUEST_REQUIRED')
    import formal_split_capture as split
    split._controlled_actions_required(container_actions)
    return run_shared_request(claim,request,request_guard,approved_source=approved_source,
        native_guard=native_guard,_controlled_prefence_stops=True,_controlled_container_actions=container_actions)


def run_shared_request(claim,request,request_guard,*,approved_source=None,native_guard=None,_controlled_prefence_stops=False,
                       _controlled_container_actions=None):
    """Run exactly one finite phase. Failure retains state, without auto recovery."""
    import formal_split_capture as split
    import formal_service_health as health
    import formal_ingress_control as ingress
    import formal_external_callers as callers
    require(type(request) is dict,'FORMAL_CAPTURE_REQUEST_INVALID')
    require(type(_controlled_prefence_stops) is bool and (not _controlled_prefence_stops or
        request.get('schemaVersion') in ('release-formal-capture-request/v12','backup-lab-capture-request/v1') and
        request.get('action')=='capture-shared-payload'),'FORMAL_CONTROLLED_CAPTURE_REQUEST_REQUIRED')
    if _controlled_prefence_stops:split._controlled_actions_required(_controlled_container_actions)
    else:require(_controlled_container_actions is None,'FORMAL_CONTROLLED_CAPTURE_REQUEST_REQUIRED')
    require(not (request.get('schemaVersion')=='release-formal-capture-request/v3' and
        request.get('action')=='restore-shared-services'),'FORMAL_CAPTURE_EXPLICIT_OPEN_STOP_REQUIRED')
    if request.get('schemaVersion') in ('release-formal-capture-request/v12','backup-lab-capture-request/v1'):
        _validate_selected_source_request(request,approved_source)
    elif request.get('schemaVersion')=='release-formal-capture-request/v7':
        require(approved_source is None,'FORMAL_CAPTURE_REQUEST_INVALID')
        validate_dependency_request(request)
    else:
        require(approved_source is None,'FORMAL_CAPTURE_REQUEST_INVALID')
        validate_shared_request(request)
    if request['action']=='capture-shared-payload':
        require(callable(native_guard),'FORMAL_CAPTURE_NATIVE_OWNER_REQUIRED')
    deadline=time.monotonic()+request['totalSeconds']
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    token=snapshot.observation_deadline.set(deadline)
    try:
        def within():require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        def thaw_guard():return split._thaw_receipt(claim)
        # No shared Docker/SQL call before positive native receipt when requested.
        thaw_guard();within();claim.assert_owned();request_guard();within()
        if request['action']=='capture-shared-payload':
            split._active(claim,{'split-sql-intent','split-sql-captured','split-raw-intent','split-captured'})
            require(deadline-time.monotonic()>request['filesystemFence']['seconds']+20,
                'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        originals=verify_shared_request_binding(claim,request)
        recovery_sources=SharedDependencySourceChecks(claim,request) if request['action']=='restore-shared-dependencies' else None
        def owner_guard():
            thaw_guard();within();claim.assert_owned();request_guard();within()
        def guard():
            if recovery_sources is not None:
                recovery_sources.assert_valid(guard=owner_guard,deadline=deadline)
                within();return
            owner_guard()
            held=ingress.assert_ingress(claim)
            require(held['rulesSha256']==request['ingressRulesSha256'],'FORMAL_CAPTURE_INGRESS_CHANGED')
            if request['action']=='capture-shared-payload':
                split._active(claim,set())
                require(held['phase']=='CAPTURE_RESTRICTED','FORMAL_CAPTURE_INGRESS_CHANGED')
            else:require(held['phase']=='RECOVERY_DEPENDENCIES_PERMITTED','FORMAL_CAPTURE_INGRESS_CHANGED')
            if any(e['step']=='external-caller-scope' for e in claim.events):
                callers.guard_external_callers(claim,callers.SshDockerTransport())
            require(claim._read(claim.root/'shared-container-original.json')==originals['shared'] and
                claim._read(claim.root/'shared-health-original.json')==originals['health'],
                'FORMAL_CAPTURE_SHARED_SCOPE_CHANGED')
            within()
        guard()
        if _controlled_prefence_stops:
            split.assert_controlled_prefence_stops(claim,
                expected_shared_scope_sha256=request['sharedScopeSha256'],guard=guard)
        credential=read_credential(request['mysqlCredentialFile'])
        mysql=PrivateDockerMySql(request['mysqlContainerId'],credential,timeout=5)
        if request['action']=='capture-shared-payload':
            guard();verify_shared_database_before_stop(claim,mysql);guard()
            if _controlled_prefence_stops:
                split.assert_controlled_prefence_stops(claim,
                    expected_shared_scope_sha256=request['sharedScopeSha256'],guard=guard)
            else:
                for role in split.STOP_ORDER[:-1]:
                    guard();split.stop_shared_container(claim,role,guard=guard);guard()
            source_arguments={'source_scope':approved_source} if request['schemaVersion'] in ('release-formal-capture-request/v12','backup-lab-capture-request/v1') else {}
            sql=split.capture_sql_phase(claim,mysql,request['database'],request['sourceRoot'],guard=guard,
                data_limits=request['dataLimits'],rejection_probe=request['rejectionProbe'],**source_arguments)
            guard()
            if _controlled_prefence_stops:
                split.stop_controlled_capture_database(claim,'mysql',guard=guard,container_actions=_controlled_container_actions)
            else:split.stop_shared_container(claim,'mysql',guard=guard)
            guard()
            require(deadline-time.monotonic()>request['filesystemFence']['seconds']+20,
                'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
            payload=split.capture_raw_phase(claim,request['sourceRoot'],guard=guard,
                filesystem_fence=request['filesystemFence'],native_guard=native_guard)
            if request['schemaVersion'] in ('release-formal-capture-request/v12','backup-lab-capture-request/v1'):
                require(sql.get('sourceScope') == payload.get('sourceScope') == approved_source and
                    type(sql.get('sourceMigrationEvidence')) is dict and
                    sql['sourceMigrationEvidence'] == payload.get('sourceMigrationEvidence'),
                    'FORMAL_CAPTURE_SOURCE_LEDGER_CHANGED')
            result={'state':'SHARED_PAYLOAD_CAPTURED_INGRESS_HELD','sql':sql,'payload':payload}
        else:
            restored=health.restore_shared_dependencies_with_health(claim,mysql,guard=guard,
                thaw_guard=thaw_guard,timeout=min(300,request['totalSeconds']))
            result={'state':'DEPENDENCIES_RESTORED_PENDING_OPEN_APPROVAL','health':restored}
        guard();native=thaw_guard();within()
        if recovery_sources is not None:guard()
        return dict(result,native=native,ingressRulesSha256=request['ingressRulesSha256'],
            productionEvidence=False,hostWritersVerified=False,externalCallerHealthVerified=False,
            serviceActionsPerformed=True,fullRunnerCompleted=False,claimReleased=False)
    finally:snapshot.observation_deadline.reset(token)


def run_external_request(claim,request,request_guard):
    """One explicit caller recovery/observation; shared and ingress stay held.

    During an unresolved caller start, the dependency guard must not inspect
    the caller journal or demand stopped callers. The caller module alone
    reconciles that action; this guard observes only bound shared dependencies.
    """
    import formal_split_capture as split
    import formal_service_health as health
    import formal_ingress_control as ingress
    import formal_external_callers as callers
    deadline=time.monotonic()+snapshot.observation_timeout(request['totalSeconds'])
    token=snapshot.observation_deadline.set(deadline)
    try:
        def within():require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        def thaw_guard():return split._thaw_receipt(claim)
        # Even the initial request/scope verification is after positive thaw.
        thaw_guard();within();claim.assert_owned();request_guard();within()
        originals=verify_shared_request_binding(claim,request)
        caller_raw=claim._read(claim.root/'external-callers-original.json')
        caller_health_raw=claim._read(claim.root/'external-callers-health-original.json')
        def bound_callers():
            require(hashlib.sha256(caller_raw).hexdigest()==request['externalScopeSha256'] and
                callers._scope(claim)[2]==request['externalScopeSha256'] and
                hashlib.sha256(caller_health_raw).hexdigest()==request['externalOriginalHealthSha256'] and
                snapshot._claim_event(claim,'external-health-scope')['details']==
                    {'sha256':request['externalOriginalHealthSha256']} and
                claim._read(claim.root/'external-callers-original.json')==caller_raw and
                claim._read(claim.root/'external-callers-health-original.json')==caller_health_raw,
                'FORMAL_CAPTURE_EXTERNAL_SCOPE_CHANGED')
            callers._original_health(claim)
        def guard():
            thaw_guard();within();claim.assert_owned();request_guard();within()
            held=ingress.assert_ingress(claim)
            require(held['rulesSha256']==request['ingressRulesSha256'] and
                held['phase']=='RECOVERY_DEPENDENCIES_PERMITTED','FORMAL_CAPTURE_INGRESS_CHANGED')
            require(claim._read(claim.root/'shared-container-original.json')==originals['shared'] and
                claim._read(claim.root/'shared-health-original.json')==originals['health'],
                'FORMAL_CAPTURE_SHARED_SCOPE_CHANGED')
            bound_callers();within()
        guard()
        credential=read_credential(request['mysqlCredentialFile'])
        mysql=PrivateDockerMySql(request['mysqlContainerId'],credential,timeout=5)
        def dependencies():
            guard()
            observed=health.observe_shared_recovery_health(claim,mysql,guard=guard,thaw_guard=thaw_guard,
                timeout=min(300,snapshot.observation_timeout(request['totalSeconds'])))
            require(observed['state']=='ORIGINAL_SERVICES_HEALTHY','FORMAL_CAPTURE_DEPENDENCY_HEALTH_REQUIRED')
            guard()
        dependencies()
        transport=callers.SshDockerTransport()
        seconds=min(300,snapshot.observation_timeout(request['totalSeconds']))
        if request['action']=='restore-external-services':
            result=callers.restore_external_services_with_health(claim,transport,dependency_guard=dependencies,seconds=seconds)
        else:
            result=callers.observe_external_restoration_health(claim,transport,dependency_guard=dependencies,seconds=seconds)
        dependencies();within()
        return {'state':'EXTERNAL_CALLERS_HEALTHY_INGRESS_HELD','externalHealth':result,
            'native':thaw_guard(),'ingressRulesSha256':request['ingressRulesSha256'],
            'externalCallerHealthVerified':True,'sharedDependencyHealthVerified':True,
            'serviceActionsPerformed':request['action']=='restore-external-services',
            'productionEvidence':False,'hostWritersVerified':False,'fullRunnerCompleted':False,'claimReleased':False}
    finally:snapshot.observation_deadline.reset(token)


def observe_shared_request(claim,request,request_guard):
    """Fresh original health under existing ingress; never changes a service.

    Request/credential/claim paths must already be on the independently bound
    control device. This observation neither installs that boundary nor proves
    administrator/host exclusion or health of restored external callers.
    """
    import formal_split_capture as split
    import formal_service_health as health
    import formal_ingress_control as ingress
    import formal_external_callers as callers
    deadline=health.health_deadline(request['healthSeconds'])
    token=snapshot.observation_deadline.set(deadline)
    try:
        thaw=split._thaw_receipt(claim)
        def thaw_guard():
            require(split._thaw_receipt(claim)==thaw,'FORMAL_SHARED_RECOVERY_CHANGED')
        def guard():
            # Always thaw before an exclusion check that may inspect Docker.
            thaw_guard();claim.assert_owned();request_guard()
            require(time.monotonic()<deadline,'FORMAL_HEALTH_DEADLINE_EXCEEDED')
            held=ingress.assert_ingress(claim)
            require(held['rulesSha256']==request['ingressRulesSha256'],'FORMAL_CAPTURE_INGRESS_CHANGED')
            if any(e['step']=='external-caller-scope' for e in claim.events):
                # Inspect the registered journal/runtime, including recovery;
                # this read-only action does not assert callers are still stopped.
                callers._observe(claim,callers.SshDockerTransport())
            require(time.monotonic()<deadline,'FORMAL_HEALTH_DEADLINE_EXCEEDED')
        guard()
        shared_raw=claim._read(claim.root/'shared-container-original.json')
        shared=_strict_json(shared_raw)
        require(shared_raw==snapshot._canonical_bytes(shared) and
            hashlib.sha256(shared_raw).hexdigest()==request['sharedScopeSha256'] and
            snapshot._claim_event(claim,'shared-container-scope')['details']=={'scopeSha256':request['sharedScopeSha256']} and
            shared['mysql']['id']==request['mysqlContainerId'] and
            shared['minio']['id']==json.loads(claim._plan)['minioContainerId'],'FORMAL_CAPTURE_SHARED_SCOPE_CHANGED')
        health_raw=claim._read(claim.root/'shared-health-original.json')
        require(hashlib.sha256(health_raw).hexdigest()==request['originalHealthSha256'] and
            snapshot._claim_event(claim,'shared-health-scope')['details']=={'sha256':request['originalHealthSha256']},
            'FORMAL_CAPTURE_HEALTH_SCOPE_CHANGED')
        credential=read_credential(request['mysqlCredentialFile'])
        require(Path(request['mysqlCredentialFile']).stat().st_dev==claim.root.stat().st_dev,
                'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
        if thaw['nativeState']!='NOT_REQUESTED':
            raw_intent=snapshot._claim_event(claim,'split-raw-intent')['details']
            device=claim.root.stat().st_dev
            require(f'{os.major(device)}:{os.minor(device)}'!=raw_intent['nativeBinding']['mount']['device'],
                    'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
        mysql=PrivateDockerMySql(request['mysqlContainerId'],credential,timeout=5)
        result=health.observe_shared_recovery_health(claim,mysql,guard=guard,
            thaw_guard=thaw_guard,timeout=request['healthSeconds'])
        guard();require(claim._read(claim.root/'shared-container-original.json')==shared_raw and
                        claim._read(claim.root/'shared-health-original.json')==health_raw,
                        'FORMAL_CAPTURE_SHARED_SCOPE_CHANGED')
        return {'state':'ORIGINAL_SERVICES_HEALTHY_INGRESS_HELD','health':result,'native':thaw,
            'ingressRulesSha256':request['ingressRulesSha256'],'productionEvidence':False,
            'hostWritersVerified':False,'externalCallerHealthVerified':False,
            'serviceActionsPerformed':False,'claimReleased':False}
    finally:snapshot.observation_deadline.reset(token)


def run_approved_host_derived_binding(request_path, expected_request_sha256):
    """Bind approved actual originals in an existing claim, before host close.

    This route performs no service action and grants no full-source authority.
    The request and control device remain pinned through native observations.
    """
    started=time.monotonic()
    import formal_boot_state as boot
    import formal_host_admission as host
    from formal_host_derived_work import _validate as validate_derived
    require_native_runtime()
    require(type(expected_request_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_request_sha256),
        'FORMAL_HOST_DERIVED_APPROVAL_REQUIRED')
    path=boot._absolute(request_path)
    raw,identity=boot._read_secure(path,0o600,16384,no_atime=True)
    require(hashlib.sha256(raw).hexdigest()==expected_request_sha256,'FORMAL_HOST_DERIVED_REQUEST_CHANGED')
    request=_strict_json(raw)
    require(type(request) is dict and set(request)=={'schemaVersion','action','claimRoot','claimBinding',
        'totalSeconds','derivedBinding'} and request['schemaVersion']=='release-formal-capture-request/v13' and
        request['action']=='bind-host-derived-originals' and type(request['totalSeconds']) is int and
        1<=request['totalSeconds']<=300,'FORMAL_HOST_DERIVED_REQUEST_INVALID')
    root=boot._absolute(request['claimRoot']);binding=request['claimBinding']
    require(type(binding) is dict and set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'} and
        type(binding['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['operationId']) and
        type(binding['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['databaseUuid']) and
        all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k]) for k in ('sourceFingerprint','minioContainerId')),
        'FORMAL_HOST_DERIVED_REQUEST_INVALID')
    derived_sha=hashlib.sha256(snapshot._canonical_bytes(request['derivedBinding'])).hexdigest()
    validate_derived(request['derivedBinding'],derived_sha)
    deadline=started+request['totalSeconds'];claim=None
    def inputs():
        require(time.monotonic()<deadline,'FORMAL_HOST_DERIVED_DEADLINE')
        require(boot._read_secure(path,0o600,16384,no_atime=True)==(raw,identity),
            'FORMAL_HOST_DERIVED_REQUEST_CHANGED')
        require(time.monotonic()<deadline,'FORMAL_HOST_DERIVED_DEADLINE')
    inputs()
    token=snapshot.observation_deadline.set(min(deadline,snapshot.observation_deadline.get() or deadline))
    try:
        claim=FormalMaintenanceClaim(str(root),binding,resume=True)
        control_device=root.stat().st_dev
        def guard():
            inputs();claim.assert_owned()
            require(root.stat().st_dev==control_device==identity[0],
                'FORMAL_HOST_DERIVED_CONTROL_DEVICE_CHANGED')
        guard()
        result=host.bind_host_derived_sources(claim,request['derivedBinding'],derived_sha,
            guard=guard,timeout=request['totalSeconds'],approved_request=(path,identity))
        return result
    finally:
        if claim is not None:claim.close()
        snapshot.observation_deadline.reset(token)


def _original_lifecycle_pre_capture_stage(claim,*,deadline,host_checks=None):
    """Accept completed preparation only; the running observer is narrower.

    Host entries already masked/inactive can close without issuing a mask or
    stop. Recorded mask/stop intents must still be completed before capture.
    This journal check grants no full exclusion or drain authority.
    """
    import formal_boot_state as boot
    claim.assert_owned()
    common={'shared-container-scope','external-caller-scope','shared-health-scope','external-health-scope',
        'maintenance-originals-bound','host-originals-bound','host-derived-originals-bound','ingress-scope',
        'ingress-install-intent','ingress-installed','db-fence-intent','db-fenced'}
    pairs={'ingress-install-intent':'ingress-installed','db-fence-intent':'db-fenced'}
    for role in boot.ROLES:
        common.add('boot-'+role+'-bound')
        for prefix in ('boot-','live-'):
            pairs[prefix+role+'-close-intent']=prefix+role+'-closed'
    for role in ('test-backend','test-rehearsal','backup-backend','backup-rehearsal'):
        pairs['external-'+role+'-stop-intent']='external-'+role+'-stopped'
    units=('crond','dnf-makecache','systemd-tmpfiles-clean','unbound-anchor','cockpit')
    for unit in units:
        pairs['host-'+unit+'-mask-intent']='host-'+unit+'-masked'
        common.update('host-'+unit+suffix for suffix in ('-stop-intent','-closed'))
    allowed=common|set(pairs)|set(pairs.values())
    names=[event['step'] for event in claim.events]
    require(len(names)==len(set(names)) and all(name in allowed for name in names) and 'db-fenced' in names,
        'FORMAL_LIFECYCLE_PRE_CAPTURE_STAGE_INVALID')
    require(all((intent in names)==(completed in names) and
        (intent not in names or names.index(intent)<names.index(completed))
        for intent,completed in pairs.items()),'FORMAL_LIFECYCLE_PRE_CAPTURE_STAGE_INVALID')
    for role in boot.ROLES:
        chain=['boot-'+role+suffix for suffix in ('-bound','-close-intent','-closed')]
        require(not any(step in names for step in chain) or
            (all(step in names for step in chain) and
             names.index(chain[0])<names.index(chain[1])<names.index(chain[2])),
            'FORMAL_LIFECYCLE_PRE_CAPTURE_STAGE_INVALID')
    for unit in units:
        closed='host-'+unit+'-closed'
        for suffix in ('-masked','-stop-intent'):
            step='host-'+unit+suffix
            require(step not in names or (closed in names and names.index(step)<names.index(closed)),
                'FORMAL_LIFECYCLE_PRE_CAPTURE_STAGE_INVALID')
    import formal_host_admission as host
    if host_checks is None:host_checks=host.ClosedHostAdmissionChecks(claim)
    host_checks.prepare(guard=claim.assert_owned,deadline=deadline)
    host_checks.assert_native(deadline=deadline)
    return host_checks


def _require_original_lifecycle_full_sources(claim):
    """No engineering source for complete exclusion/drain/sustained thaw yet.

    Finite host entries, live-control counts and thaw receipts cannot supply
    these properties. No input flag or callback grants this missing authority.
    Refuse the normal owner before any capture/recovery service action,
    and retain checks before signed OPEN consumption and start.
    """
    claim.assert_owned()
    raise FormalSnapshotError('FORMAL_LIFECYCLE_FULL_SOURCES_REQUIRED')


def _original_release_package_binding(operation_raw, claim_binding, target_raw, source,*,
        approved_package,current_input_raw,gate_raw):
    """Bind the actual normal operation, never grant capture or NAS completion."""
    code='FORMAL_LIFECYCLE_RELEASE_BINDING_INVALID'
    try:
        operation=_strict_json(operation_raw);target=_strict_json(target_raw)
        current=_strict_json(current_input_raw);gate=_strict_json(gate_raw)
        require(type(approved_package) is dict and set(approved_package)==
            {'releaseTag','packageDigest','manifestDigest','planDigest'} and
            type(approved_package['releaseTag']) is str and
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',approved_package['releaseTag']) and
            all(type(approved_package[k]) is str and re.fullmatch('[0-9a-f]{64}',approved_package[k])
                for k in ('packageDigest','manifestDigest','planDigest')),code)
        require(type(operation) is dict and set(operation)=={
            'schemaVersion','attemptId','revision','state','phase','writeAttempted','binding',
            'before','target','phases','verification','observation','originalError',
            'observationErrors','finalizationErrors','receiptDigest','history','completion'} and
            operation['schemaVersion']=='release-deployment-operation/v1' and
            type(operation['attemptId']) is str and re.fullmatch('[0-9a-f]{64}',operation['attemptId']) and
            type(operation['revision']) is int and operation['revision']>=2 and
            operation['state']=='STARTED' and operation['phase']=='production-backup' and
            operation['writeAttempted'] is True and operation['receiptDigest'] is None and
            operation['completion'] is None and operation['originalError'] is None and
            type(operation['before']) is dict and type(operation['target']) is dict and
            type(operation['phases']) is list and len(operation['phases'])>0 and
            type(operation['phases'][-1]) is dict and
            operation['phases'][-1].get('name')=='production-backup' and
            operation['phases'][-1].get('status')=='STARTED' and
            operation['phases'][-1].get('completedAt') is None,code)
        binding=operation['binding']
        require(type(binding) is dict and set(binding)=={'scope','lockOperationId','releaseTag',
            'leaseTokenDigest','packageDigest','manifestDigest','planDigest'} and
            type(binding['releaseTag']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['releaseTag']) and
            binding['lockOperationId']=='prod-'+binding['releaseTag'] and
            binding['lockOperationId']==claim_binding['operationId'] and
            all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k]) for k in
                ('leaseTokenDigest','packageDigest','manifestDigest','planDigest')),code)
        require({k:binding[k] for k in approved_package}==approved_package and
            operation['attemptId']==current['expectedAttemptId'] and
            binding['leaseTokenDigest']==current['expectedLeaseTokenDigest'],code)
        scope=binding['scope']
        expected=dict(environment=target['environment'],host=target['host'],machineId=target['machineId'],
            database=target['database'],serverUuid=target['databaseServerUuid'])
        require(type(scope) is dict and scope==expected and scope['environment']=='prod' and
            source['environment']=='prod' and scope['database']==source['database'] and
            scope['serverUuid']==source['databaseUuid']==claim_binding['databaseUuid'] and
            source['targetFingerprint']==claim_binding['sourceFingerprint'],code)
        require(type(gate) is dict and set(gate)=={'schemaVersion','scope','binding','revision','state',
            'attemptId','operationDigest','receiptDigest'} and
            gate['schemaVersion']=='release-deployment-gate/v1' and
            type(gate['revision']) is int and gate['revision']==operation['revision'] and
            gate['state']==operation['state'] and gate['attemptId']==operation['attemptId'] and
            gate['operationDigest']==hashlib.sha256(operation_raw).hexdigest() and
            gate['receiptDigest'] is None and
            snapshot._canonical_bytes(gate['scope'])==snapshot._canonical_bytes(scope) and
            snapshot._canonical_bytes(gate['binding'])==snapshot._canonical_bytes(binding),code)
        return dict(schemaVersion='release-formal-original-package-binding/v2',
            deploymentOperationSha256=hashlib.sha256(operation_raw).hexdigest(),
            deploymentGateSha256=hashlib.sha256(gate_raw).hexdigest(),
            deploymentContextSha256=hashlib.sha256(current_input_raw).hexdigest(),
            deploymentAttemptId=operation['attemptId'],
            claimBindingSha256=hashlib.sha256(snapshot._canonical_bytes(claim_binding)).hexdigest(),
            sourceFingerprint=claim_binding['sourceFingerprint'],
            approvedSourceTargetSha256=hashlib.sha256(target_raw).hexdigest(),scope=scope,
            package={k:binding[k] for k in ('releaseTag','packageDigest','manifestDigest','planDigest')},
            leaseTokenDigest=binding['leaseTokenDigest'],fullCaptureVerified=False,productionEvidence=False)
    except (KeyError,TypeError,ValueError):
        raise FormalSnapshotError(code) from None


PRODUCTION_A_SOURCE_FILES = frozenset({
    'binding.json','approved-source-target.json','original-configs.json',
    'shared-container-original.json','shared-health-original.json',
    'external-callers-original.json','external-callers-health-original.json',
    'database-prefence-original.json','host-originals.json','host-derived-originals.json','ingress-plan.json',
    *('controlled-'+r+'-inspect.json' for r in
      ('mysql','frontend','backend','showroom','onlyoffice','redis','minio')),
    *('boot-'+r+'-original.json' for r in
      ('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal'))})


def _validate_production_a_boot_source(source,role):
    code='FORMAL_PRODUCTION_A_BOOT_SOURCE_INVALID'
    require(type(role) is str and role in
        ('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal') and
        type(source) is dict and set(source)=={'schemaVersion','role','peer','machineIdSha256','bootId','path'} and
        source['schemaVersion']=='release-formal-production-a-boot-source/v1' and source['role']==role and
        type(source['peer']) is str and (source['peer']=='local' or
            source['peer']=={'test-backend':'172.30.30.58','test-rehearsal':'172.30.30.58',
                'backup-backend':'172.30.30.59','backup-rehearsal':'172.30.30.59'}.get(role)) and
        type(source['machineIdSha256']) is str and re.fullmatch('[0-9a-f]{64}',source['machineIdSha256']) and
        type(source['bootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',source['bootId']) and
        type(source['path']) is str and source['path'].startswith('/') and '\\' not in source['path'] and
        all(p not in ('','.','..') for p in source['path'].split('/')[1:]) and
        not any(ord(c)<32 for c in source['path']),code)
    return source


def _validate_production_a_boot_original(value,role):
    """An absent final file still needs an actual approved, opened parent."""
    import base64
    import binascii
    code='FORMAL_PRODUCTION_A_BOOT_ORIGINAL_INVALID'
    fields={'schemaVersion','role','peer','machineIdSha256','bootId','path',
        'sourceParentIdentity','present','originalBase64','sha256','sourceFileIdentity'}
    require(type(value) is dict and set(value)==fields and
        value['schemaVersion']=='release-formal-production-a-boot-original/v1',code)
    source={name:value[name] for name in ('role','peer','machineIdSha256','bootId','path')}
    source['schemaVersion']='release-formal-production-a-boot-source/v1'
    _validate_production_a_boot_source(source,role)
    chain=value['sourceParentIdentity']
    require(type(chain) is list and 0<len(chain)<=128 and all(type(row) is list and len(row)==5 and
        all(type(n) is int for n in row) and row[0]>=0 and row[1]>0 and row[2]==0 and row[3]>=0 and
        stat.S_ISDIR(row[4]) and not row[4]&0o022 for row in chain) and type(value['present']) is bool,code)
    if not value['present']:
        require(value['originalBase64'] is None and value['sha256'] is None and value['sourceFileIdentity'] is None,code)
        return value
    identity=value['sourceFileIdentity']
    require(type(value['originalBase64']) is str and len(value['originalBase64'])<=5464 and
        type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
        type(identity) is list and len(identity)==9 and all(type(n) is int for n in identity) and
        identity[0]==chain[-1][0] and identity[1]>0 and identity[2]==0 and identity[3]>=0 and
        identity[4]==stat.S_IFREG|0o644 and identity[5]==1 and 0<=identity[6]<=4096,code)
    try:raw=base64.b64decode(value['originalBase64'],validate=True)
    except (ValueError,binascii.Error):raise FormalSnapshotError(code) from None
    require(len(raw)==identity[6] and base64.b64encode(raw).decode('ascii')==value['originalBase64'] and
        hashlib.sha256(raw).hexdigest()==value['sha256'],code)
    return value


def _production_a_boot_local_peer(source):
    """Only the actual local machine/boot; a remote mapping cannot read locally."""
    import formal_boot_state as boot
    code='FORMAL_PRODUCTION_A_BOOT_PEER_CHANGED'
    require(os.geteuid()==0,code)
    machine=Path('/etc/machine-id')
    with boot._directory(machine.parent,no_atime=True) as (directory,chain):
        fd=os.open(machine.name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NOATIME,dir_fd=directory)
        try:
            info=os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and
                not info.st_mode&0o022 and 32<=info.st_size<=33,code)
            raw=os.read(fd,34)
            require(len(raw)==info.st_size and re.fullmatch(rb'[0-9a-f]{32}\n?',raw) and
                boot._signature(os.fstat(fd))==boot._signature(info) and
                boot._signature(os.stat(machine.name,dir_fd=directory,follow_symlinks=False))==boot._signature(info),code)
        finally:os.close(fd)
        boot._directory_unchanged(machine.parent,chain)
    require(hashlib.sha256(raw).hexdigest()==source['machineIdSha256'] and
        Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()==source['bootId'],code)


def _sample_production_a_boot_original_source(source,*,guard,deadline):
    """Read an approved unchanged final file or its actual absence; no writes."""
    require_native_runtime()
    import base64
    import math
    import formal_boot_state as boot
    code='FORMAL_PRODUCTION_A_BOOT_SOURCE_CHANGED'
    _validate_production_a_boot_source(source,source['role'] if type(source) is dict and 'role' in source else None)
    require(source['peer']=='local',code)
    saved=snapshot._canonical_bytes(source)
    require(callable(guard) and type(deadline) in (int,float) and math.isfinite(deadline),code)
    target=boot._absolute(source['path'])
    def checked():
        guard();snapshot.observation_timeout(1)
        require(time.monotonic()<deadline and snapshot._canonical_bytes(source)==saved,code)
        _production_a_boot_local_peer(source)
    try:
        checked()
        with boot._directory(target.parent,no_atime=True) as (directory,chain):
            # Only this initial lstat of the final name may establish absence.
            # A read/stat race for an initially present file must remain an error.
            try:os.stat(target.name,dir_fd=directory,follow_symlinks=False)
            except FileNotFoundError:pair=None
            else:pair=boot._read_at(directory,target.name,0o644,4096,no_atime=True,allow_empty=True)
            result=dict(schemaVersion='release-formal-production-a-boot-original/v1',
                **{k:source[k] for k in ('role','peer','machineIdSha256','bootId','path')},
                sourceParentIdentity=[list(row) for row in chain],present=pair is not None,
                originalBase64=None if pair is None else base64.b64encode(pair[0]).decode('ascii'),
                sha256=None if pair is None else hashlib.sha256(pair[0]).hexdigest(),
                sourceFileIdentity=None if pair is None else list(pair[1]))
            _validate_production_a_boot_original(result,source['role'])
            checked();boot._directory_unchanged(target.parent,chain)
            if pair is None:
                try:os.stat(target.name,dir_fd=directory,follow_symlinks=False)
                except FileNotFoundError:pass
                else:raise FormalSnapshotError(code)
            else:require(boot._read_at(directory,target.name,0o644,4096,no_atime=True,allow_empty=True)==pair,code)
            boot._directory_unchanged(target.parent,chain)
            snapshot.observation_timeout(1);require(time.monotonic()<deadline,code)
            return result
    except OSError:raise FormalSnapshotError('FORMAL_PRODUCTION_A_BOOT_SOURCE_IO_FAILED') from None


def seal_production_a_boot_original(claim,role,source,*,guard,deadline,connection=None):
    """Keep exact current bytes/absence in this held claim; never alter boot state."""
    require_native_runtime()
    import math
    import formal_boot_state as boot
    code='FORMAL_PRODUCTION_A_BOOT_ORIGINAL_CHANGED'
    require(type(claim) is FormalMaintenanceClaim and callable(guard) and
        type(deadline) in (int,float) and math.isfinite(deadline),code)
    _validate_production_a_boot_source(source,role)
    selected=snapshot._canonical_bytes(source)
    target=claim.root/('boot-'+role+'-original.json')
    if source['peer']=='local':
        require(connection is None and source['path']!=str(claim.root) and str(claim.root) not in
            tuple(str(parent) for parent in PurePosixPath(source['path']).parents),code)
        reader=_sample_production_a_boot_original_source
    else:
        require(connection is not None,code)
        reader=SshProductionABootSource(connection)
    def checked():
        claim.assert_owned();guard();claim.assert_owned();snapshot.observation_timeout(1)
        require(time.monotonic()<deadline and snapshot._canonical_bytes(source)==selected and
            not any(e['step'].startswith('boot-') or e['step']=='released' for e in claim.events),code)
    checked();require(not os.path.lexists(target),code)
    original=reader(source,guard=checked,deadline=deadline)
    _validate_production_a_boot_original(original,role)
    require(all(type(original[k]) is str and original[k]==source[k]
        for k in ('role','peer','machineIdSha256','bootId','path')),code)
    raw=snapshot._canonical_bytes(original)
    require(len(raw)<=16384 and
        reader(source,guard=checked,deadline=deadline)==original,code)
    checked();require(not os.path.lexists(target),code)
    try:claim._write(target,raw)
    except OSError:raise FormalSnapshotError('FORMAL_PRODUCTION_A_BOOT_ORIGINAL_WRITE_FAILED') from None
    pair=boot._read_secure(target,0o600,16384,no_atime=True)
    require(pair[0]==raw and pair[1][0]==claim.root.stat().st_dev,code)
    checked()
    require(reader(source,guard=checked,deadline=deadline)==original,code)
    checked();require(boot._read_secure(target,0o600,16384,no_atime=True)==pair,code)
    return dict(path=str(target),sha256=hashlib.sha256(raw).hexdigest(),identity=list(pair[1]))


def _production_a_boot_remote_body(source, seconds):
    """Fixed read-only Python carried in the existing sealed SSH shell stdin."""
    import base64
    import inspect
    import math
    import formal_boot_state as boot
    code='FORMAL_PRODUCTION_A_BOOT_REMOTE_INPUT_INVALID'
    _validate_production_a_boot_source(source,source.get('role') if type(source) is dict else None)
    require(source['peer']!='local' and type(seconds) in (int,float) and
        math.isfinite(seconds) and 0<seconds<=15,code)
    header=('from contextlib import contextmanager\nimport base64,hashlib,json,os,re,stat,sys,time\n'
        'from pathlib import Path\n'
        'class FormalSnapshotError(RuntimeError): pass\n'
        'def require(value,code):\n if not value: raise FormalSnapshotError(code)\n')
    # Reuse the actual immutable safety algorithms, with no remote import path
    # or alternate implementation selected by a request or environment variable.
    for function in (boot._signature,boot._absolute,boot._directory,boot._directory_unchanged,boot._read_at):
        header+=inspect.getsource(function)+'\n'
    peer=inspect.getsource(_production_a_boot_local_peer)
    require(peer.count('    import formal_boot_state as boot\n')==1,code)
    header+=peer.replace('    import formal_boot_state as boot\n','').replace('boot.','')+'\n'
    header+='source=json.loads(base64.b64decode('+repr(base64.b64encode(snapshot._canonical_bytes(source)).decode())+'))\n'
    header+='deadline=time.monotonic()+'+repr(seconds)+'\n'
    reader=r'''
def checked():
    require(os.name=='posix' and sys.platform=='linux' and os.geteuid()==0 and
        time.monotonic()<deadline,'FORMAL_PRODUCTION_A_BOOT_REMOTE_PEER_CHANGED')
    connection=os.environ.get('SSH_CONNECTION','').split()
    require(len(connection)==4 and connection[2]==source['peer'] and connection[3]=='22' and
        re.fullmatch('[1-9][0-9]{0,4}',connection[1]) is not None and
        1<=int(connection[1])<=65535,'FORMAL_PRODUCTION_A_BOOT_REMOTE_PEER_CHANGED')
    _production_a_boot_local_peer(source)

checked()
target=_absolute(source['path'])
with _directory(target.parent,no_atime=True) as (directory,chain):
    # Only this initial final-name stat establishes absence; failed reads do not.
    try:os.stat(target.name,dir_fd=directory,follow_symlinks=False)
    except FileNotFoundError:pair=None
    else:pair=_read_at(directory,target.name,0o644,4096,no_atime=True,allow_empty=True)
    result=dict(schemaVersion='release-formal-production-a-boot-original/v1',
        **{k:source[k] for k in ('role','peer','machineIdSha256','bootId','path')},
        sourceParentIdentity=[list(row) for row in chain],present=pair is not None,
        originalBase64=None if pair is None else base64.b64encode(pair[0]).decode('ascii'),
        sha256=None if pair is None else hashlib.sha256(pair[0]).hexdigest(),
        sourceFileIdentity=None if pair is None else list(pair[1]))
    checked();_directory_unchanged(target.parent,chain)
    if pair is None:
        try:os.stat(target.name,dir_fd=directory,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise FormalSnapshotError('FORMAL_PRODUCTION_A_BOOT_REMOTE_SOURCE_CHANGED')
    else:require(_read_at(directory,target.name,0o644,4096,no_atime=True,allow_empty=True)==pair,
        'FORMAL_PRODUCTION_A_BOOT_REMOTE_SOURCE_CHANGED')
    _directory_unchanged(target.parent,chain)
checked()
wire=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
require(0<len(wire)<=16384,'FORMAL_PRODUCTION_A_BOOT_REMOTE_OUTPUT_INVALID')
sys.stdout.buffer.write(wire);sys.stdout.buffer.flush()
'''
    body=('set -euo pipefail\numask 077\n'
        'env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LC_ALL=C SSH_CONNECTION="${SSH_CONNECTION:-}" '
        '/usr/bin/python3 -I -B - <<\'FORMAL_A_BOOT_READER\'\n'+header+reader+'\nFORMAL_A_BOOT_READER\n').encode()
    require(0<len(body)<=16384,code)
    return body


class SshProductionABootSource:
    """One exact peer/boot/key read per sample. No service action or retry."""
    def __init__(self,connection):
        import formal_external_callers as callers
        code='FORMAL_PRODUCTION_A_BOOT_REMOTE_CONNECTION_INVALID'
        require(type(connection) is dict and connection.get('host') in set(callers.HOSTS.values()),code)
        callers._connection(connection,connection['host'])
        self._connection=_strict_json(snapshot._canonical_bytes(connection))
        self._connection_pin=snapshot._canonical_bytes(self._connection)
        try:self._keys=callers._known_hosts_bytes(self._connection)
        except OSError:raise FormalSnapshotError(code) from None
        require(hashlib.sha256(self._keys).hexdigest()==self._connection['knownHostsSha256'],code)

    def __call__(self,source,*,guard,deadline):
        require_native_runtime()
        import math
        import formal_external_callers as callers
        import formal_controlled_container_sources as controlled
        code='FORMAL_PRODUCTION_A_BOOT_REMOTE_SOURCE_CHANGED'
        _validate_production_a_boot_source(source,source.get('role') if type(source) is dict else None)
        require(source['peer']!='local' and callable(guard) and type(deadline) in (int,float) and
            math.isfinite(deadline),code)
        selected=snapshot._canonical_bytes(source)
        connection=self._connection
        def checked():
            guard();snapshot.observation_timeout(1)
            require(time.monotonic()<deadline and snapshot._canonical_bytes(source)==selected and
                snapshot._canonical_bytes(connection)==self._connection_pin and
                connection['host']==source['peer'] and connection['bootId']==source['bootId'],code)
            try:keys=callers._known_hosts_bytes(connection)
            except OSError:raise FormalSnapshotError(code) from None
            require(keys==self._keys and hashlib.sha256(keys).hexdigest()==connection['knownHostsSha256'],code)
        checked()
        seconds=min(15,deadline-time.monotonic(),snapshot.observation_timeout(15))
        body=_production_a_boot_remote_body(source,seconds)
        argv=['/usr/bin/ssh','-F','/dev/null','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','UserKnownHostsFile='+connection['knownHostsFile'],'-o','GlobalKnownHostsFile=/dev/null',
            '-o','UpdateHostKeys=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',
            '-o','ConnectionAttempts=1','-p','22','root@'+connection['host'],'/bin/bash --noprofile --norc -s']
        checked()
        try:raw=controlled._execute_controlled_script(argv,body,deadline=deadline,action=False)
        except controlled.ControlledSourceError:
            raise FormalSnapshotError('FORMAL_PRODUCTION_A_BOOT_REMOTE_READ_UNCERTAIN') from None
        checked()
        require(type(raw) is bytes and 0<len(raw)<=16384,code)
        record=_strict_json(raw)
        _validate_production_a_boot_original(record,source['role'])
        require(snapshot._canonical_bytes(record)==raw and all(record[k]==source[k]
            for k in ('role','peer','machineIdSha256','bootId','path')),code)
        checked()
        return record


def _production_a_database_flags(raw, database_uuid):
    code='FORMAL_PRODUCTION_A_DATABASE_ORIGINAL_INVALID'
    require(type(raw) is bytes and 0<len(raw)<=16384 and type(database_uuid) is str and
        re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',database_uuid),code)
    flags=_strict_json(raw)
    require(type(flags) is dict and set(flags)=={'serverUuid','readOnly','superReadOnly'} and
        flags['serverUuid']==database_uuid and type(flags['readOnly']) is int and flags['readOnly'] in (0,1) and
        type(flags['superReadOnly']) is int and flags['superReadOnly']==0 and
        raw==snapshot._canonical_bytes(flags),code)
    return flags


def seal_production_a_database_prefence_original(claim,mysql,*,guard):
    """Seal actual flags separately, before any database-fence action.

    The caller must supply its live pre-stop owner guard. This operation only
    observes flags and writes a private original; it never SETs database flags,
    creates database-original.json, issues approval, or changes service state.
    """
    require_native_runtime()
    import formal_boot_state as boot
    code='FORMAL_PRODUCTION_A_DATABASE_PREFENCE_INVALID'
    require(type(claim) is FormalMaintenanceClaim and callable(guard),code)
    path=claim.root/'database-prefence-original.json'
    actual=claim.root/'database-original.json'
    def checked():
        claim.assert_owned();guard();claim.assert_owned();snapshot.observation_timeout(1)
        require(not any(event['step'].startswith('db-') or event['step']=='released'
            for event in claim.events),code)
        require(not os.path.lexists(path) and not os.path.lexists(actual),code)
    checked()
    identity=_strict_json(claim._plan)['databaseUuid']
    flags=snapshot._database_flags(mysql,identity)
    raw=snapshot._canonical_bytes(flags)
    _production_a_database_flags(raw,identity)
    checked()
    require(snapshot._database_flags(mysql,identity)==flags,code)
    checked()
    try:claim._write(path,raw)
    except OSError:raise FormalSnapshotError('FORMAL_PRODUCTION_A_DATABASE_PREFENCE_WRITE_FAILED') from None
    pair=boot._read_secure(path,0o600,16384,no_atime=True)
    require(pair[0]==raw and pair[1][0]==claim.root.stat().st_dev and
        not os.path.lexists(actual),code)
    claim.assert_owned();guard();claim.assert_owned();snapshot.observation_timeout(1)
    require(boot._read_secure(path,0o600,16384,no_atime=True)==pair and
        not os.path.lexists(actual) and not any(event['step'].startswith('db-') or event['step']=='released'
            for event in claim.events),code)
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),identity=list(pair[1]),flags=flags)


def verify_production_a_database_fence_original(prefence_raw,actual_raw,intent_details,database_uuid):
    """Bind the post-fence claim original to the sealed pre-fence source bytes."""
    code='FORMAL_PRODUCTION_A_DATABASE_ORIGINAL_CHANGED'
    flags=_production_a_database_flags(prefence_raw,database_uuid)
    require(type(actual_raw) is bytes and actual_raw==prefence_raw and
        type(intent_details) is dict and set(intent_details)=={'originalFlags','originalSha256'} and
        intent_details['originalFlags']==flags and
        snapshot._canonical_bytes(intent_details['originalFlags'])==actual_raw and
        type(intent_details['originalSha256']) is str and
        intent_details['originalSha256']==hashlib.sha256(prefence_raw).hexdigest(),code)
    actual_flags=_production_a_database_flags(actual_raw,database_uuid)
    require(actual_flags==flags,code)
    return flags





def seal_production_a_source_inventory(claim,release_binding_raw,sources,boot_sources,*,guard,deadline):
    """Bind already sealed actual originals; no approval or service action.

    All private input files must be on the held control device. The five boot
    mappings must come from the independently approved recipe. Their records
    remain read-only; their live sources are checked separately by the owner.
    Other source semantics and complete writer exclusion remain owner duties.
    """
    require_native_runtime()
    import formal_boot_state as boot
    import math
    import threading
    code='FORMAL_PRODUCTION_A_SOURCE_INVENTORY_CHANGED'
    roles={'backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal'}
    require(os.geteuid()==0 and type(claim) is FormalMaintenanceClaim and callable(guard) and
        type(deadline) in (int,float) and math.isfinite(deadline) and
        type(release_binding_raw) is bytes and 0<len(release_binding_raw)<=16384 and
        type(sources) is dict and set(sources)==PRODUCTION_A_SOURCE_FILES and
        type(boot_sources) is dict and set(boot_sources)==roles,code)
    require(all(type(p) is str and p.startswith('/') and '\\' not in p and
        all(part not in ('','.','..') for part in p.split('/')[1:]) and
        not any(ord(c)<32 for c in p) for p in sources.values()) and
        len(set(sources.values()))==len(sources),code)
    for role in roles:_validate_production_a_boot_source(boot_sources[role],role)
    source_raw=snapshot._canonical_bytes(sources);mapping_raw=snapshot._canonical_bytes(boot_sources)
    selected=_strict_json(source_raw);mappings=_strict_json(mapping_raw)
    root=claim.root;target=root/'production-a-source-inventory.json'
    paths={name:boot._absolute(path) for name,path in selected.items()}
    require(paths['database-prefence-original.json']!=root/'database-original.json' and
        target not in paths.values(),code)
    claim.assert_owned()
    owner_fd=claim._fd;owner_pid=os.getpid();owner_thread=threading.get_ident()
    fd_signature=boot._signature(os.fstat(owner_fd));lock_signature=boot._signature(os.stat(claim._lock,follow_symlinks=False))
    plan=claim._plan;events_raw=snapshot._canonical_bytes(claim.events)
    device=root.stat().st_dev;directories={};sealed=False
    with boot._directory(root,no_atime=True) as (_,chain):directories[root]=chain
    host_boot=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
    require(re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',host_boot),code)
    def secure(path,limit):
        try:
            pair=boot._read_secure(path,0o600,limit,no_atime=True)
            require(pair[1][0]==device,code)
            return pair
        except OSError:raise FormalSnapshotError('FORMAL_PRODUCTION_A_SOURCE_INVENTORY_IO_FAILED') from None
    def checked():
        claim.assert_owned();guard();claim.assert_owned();snapshot.observation_timeout(1)
        require(os.getpid()==owner_pid and threading.get_ident()==owner_thread and claim.root==root and
            claim._fd==owner_fd and boot._signature(os.fstat(owner_fd))==fd_signature and
            boot._signature(os.stat(claim._lock,follow_symlinks=False))==lock_signature and
            claim._plan==plan and snapshot._canonical_bytes(claim.events)==events_raw and
            snapshot._canonical_bytes(sources)==source_raw and
            snapshot._canonical_bytes(boot_sources)==mapping_raw and time.monotonic()<deadline,code)
        require(not any(e['step'] in ('db-fence-intent','db-fenced','released') for e in claim.events) and
            not os.path.lexists(root/'database-original.json') and (sealed or not os.path.lexists(target)),code)
        require(Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()==host_boot,code)
        for path,chain in directories.items():boot._directory_unchanged(path,chain)
    def sample():
        result={}
        for name,path in paths.items():
            snapshot.observation_timeout(1);require(time.monotonic()<deadline,code)
            with boot._directory(path.parent,no_atime=True) as (_,chain):
                if path.parent in directories:require(directories[path.parent]==chain,code)
                else:directories[path.parent]=chain
                result[name]=secure(path,16777216)
        return result
    checked()
    release_path=root/'original-release-binding.json'
    release_pair=secure(release_path,16384);require(release_pair[0]==release_binding_raw,code)
    originals=sample()
    require(originals['binding.json'][0]==plan,code)
    release=_strict_json(release_binding_raw)
    require(type(release) is dict and release.get('claimBindingSha256')==hashlib.sha256(plan).hexdigest() and
        release.get('approvedSourceTargetSha256')==hashlib.sha256(originals['approved-source-target.json'][0]).hexdigest(),code)
    _production_a_database_flags(originals['database-prefence-original.json'][0],_strict_json(plan)['databaseUuid'])
    for role in roles:
        raw=originals['boot-'+role+'-original.json'][0];record=_strict_json(raw)
        _validate_production_a_boot_original(record,role)
        require(raw==snapshot._canonical_bytes(record) and all(record[k]==mappings[role][k]
            for k in ('role','peer','machineIdSha256','bootId','path')),code)
    inventory=dict(schemaVersion='backup-lab-original-sources/v1' if release.get('schemaVersion')=='backup-lab-original-package-binding/v1' else 'release-formal-production-a-original-sources/v1',
        claimBindingSha256=hashlib.sha256(plan).hexdigest(),
        approvedSourceTargetSha256=hashlib.sha256(originals['approved-source-target.json'][0]).hexdigest(),
        hostBootId=host_boot,files={name:dict(path=selected[name],sha256=hashlib.sha256(pair[0]).hexdigest())
            for name,pair in originals.items()})
    raw=snapshot._canonical_bytes(inventory);digest=hashlib.sha256(raw).hexdigest()
    require(0<len(raw)<=65536,code)
    binding=production_a_resume_binding(release_binding_raw,raw,digest)
    checked();require(sample()==originals and secure(release_path,16384)==release_pair,code)
    checked()
    try:claim._write(target,raw)
    except OSError:raise FormalSnapshotError('FORMAL_PRODUCTION_A_SOURCE_INVENTORY_WRITE_FAILED') from None
    sealed=True
    pair=secure(target,65536);require(pair[0]==raw,code)
    checked();require(sample()==originals and secure(release_path,16384)==release_pair and secure(target,65536)==pair,code)
    checked()
    # No observer callback may run after these terminal identities.
    for name,path in paths.items():require(boot._signature(os.stat(path,follow_symlinks=False))==originals[name][1],code)
    for path,pinned in ((release_path,release_pair),(target,pair)):
        require(boot._signature(os.stat(path,follow_symlinks=False))==pinned[1],code)
    for path,chain in directories.items():boot._directory_unchanged(path,chain)
    require(time.monotonic()<deadline,code);snapshot.observation_timeout(1)
    return dict(path=str(target),sha256=digest,identity=list(pair[1]),binding=binding,
        approvalConsumed=False,productionEvidence=False)


def seal_production_a_config_originals(claim,approved_source_target_raw,expected_approved_sha256,*,guard,deadline):
    """Measure originals before independent A signing, under the held claim.

    This does not approve installed configuration or consume/sign authority.
    The sealed original is subsequently bound by the existing 23-file inventory.
    """
    require_native_runtime()
    import math
    import threading
    import formal_boot_state as boot
    from formal_selected_config_capture import observe_selected_config_originals
    from formal_backup_lab import approved_capture_source as approved_source_scope
    code='FORMAL_PRODUCTION_A_CONFIG_AUTHOR_CHANGED'
    require(type(claim) is FormalMaintenanceClaim and callable(guard) and
        type(deadline) in (int,float) and math.isfinite(deadline),code)
    target=_strict_json(approved_source_target_raw)
    approved_source_scope(approved_source_target_raw,expected_approved_sha256,claim._plan,target['database'])
    claim.assert_owned();root=claim.root;fd=claim._fd;plan=claim._plan
    pid=os.getpid();thread=threading.get_ident();events=snapshot._canonical_bytes(claim.events)
    identity=boot._signature(os.fstat(fd));lock=claim._lock
    root_identity=(root.stat().st_dev,root.stat().st_ino)
    require(not any(e['step'] in ('db-fence-intent','db-fenced','released','failed-retained',
        'production-a-resume-intent','production-a-resume-consumed') or
        e['step'].startswith('shared-') and '-stop' in e['step'] for e in claim.events),code)
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    approval_path=root/'approved-source-target.json';path=root/'original-configs.json'
    approval=boot._read_secure(approval_path,0o600,65536,no_atime=True)
    require(approval[0]==approved_source_target_raw and not os.path.lexists(path),code)
    sealed=None
    def owned():
        require(time.monotonic()<deadline and os.getpid()==pid and threading.get_ident()==thread and
            claim.root==root and claim._fd==fd and claim._plan==plan and claim._lock==lock and
            boot._signature(os.fstat(fd))==identity and
            boot._signature(os.stat(lock,follow_symlinks=False))==identity and
            (root.stat().st_dev,root.stat().st_ino)==root_identity and
            snapshot._canonical_bytes(claim.events)==events,code)
        claim.assert_owned()
        require(boot._read_secure(approval_path,0o600,65536,no_atime=True)==approval,code)
        if sealed is not None:require(boot._read_secure(path,0o600,16384,no_atime=True)==sealed,code)
    def checked():
        inherited=snapshot.observation_deadline.get()
        token=snapshot.observation_deadline.set(deadline if inherited is None else min(deadline,inherited))
        try:owned();guard();owned()
        finally:snapshot.observation_deadline.reset(token)
    token=snapshot.observation_deadline.set(deadline)
    try:
        checked();observed,recheck=observe_selected_config_originals(boot._absolute(target['root']),guard=checked)
        raw=snapshot._canonical_bytes(observed);recheck();checked()
        claim._write(path,raw)
        sealed=boot._read_secure(path,0o600,16384,no_atime=True)
        require(sealed[0]==raw,code)
        def retained():
            inherited=snapshot.observation_deadline.get()
            retained_token=snapshot.observation_deadline.set(deadline if inherited is None else min(deadline,inherited))
            try:checked();recheck();checked();recheck()
            finally:snapshot.observation_deadline.reset(retained_token)
        retained()
        return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest()),retained
    finally:snapshot.observation_deadline.reset(token)


def prepare_production_a_normal_sources(claim,*,release_binding_raw,source_refs,boot_sources,
        controlled_sources,mysql,guard,deadline,boot_connections=None,docker_sources=None):
    """Prepare originals in the normal publisher's already held native claim.

    The caller must supply the existing initialization/host/config originals,
    independently approved boot mappings and complete container selections.
    No source, approval, connection or success state is inferred here. This
    stage observes and seals originals only, before stop/fence or A consumption.
    Its retained guard ends at authority consumption: the existing signed
    consumer then pins these exact originals for action/recovery/NAS guards.
    No claim is acquired, closed or released by this function.
    """
    require_native_runtime()
    import math
    import threading
    import formal_boot_state as boot
    import formal_controlled_container_sources as controlled
    code='FORMAL_PRODUCTION_A_NORMAL_PREPARATION_CHANGED'
    roles=('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal')
    generated={'database-prefence-original.json',*('boot-'+r+'-original.json' for r in roles),
        *('controlled-'+r+'-inspect.json' for r in controlled.ControlledSharedContainerActions.ROLES)}
    required=PRODUCTION_A_SOURCE_FILES-generated
    require(os.geteuid()==0 and type(claim) is FormalMaintenanceClaim and callable(guard) and
        mysql is not None and type(deadline) in (int,float) and math.isfinite(deadline) and
        type(release_binding_raw) is bytes and 0<len(release_binding_raw)<=16384 and
        type(source_refs) is dict and set(source_refs)==required and
        type(boot_sources) is dict and set(boot_sources)==set(roles) and
        type(controlled_sources) is dict and
        set(controlled_sources)==controlled.ControlledSharedContainerActions.ROLES,code)
    for role in roles:_validate_production_a_boot_source(boot_sources[role],role)
    connections={} if boot_connections is None else boot_connections
    require(type(connections) is dict and set(connections)=={
        r for r in roles if boot_sources[r].get('peer')!='local'},code)
    for selected in controlled_sources.values():
        controlled._selection(selected);require(selected['present'] is True,code)
    release=_strict_json(release_binding_raw)
    require(_valid_capture_release(release,claim),code)
    claim.assert_owned();root=claim.root;plan=claim._plan;fd=claim._fd
    pid=os.getpid();thread=threading.get_ident();fd_pin=boot._signature(os.fstat(fd))
    lock=claim._lock;lock_pin=boot._signature(os.stat(lock,follow_symlinks=False))
    root_pin=(root.stat().st_dev,root.stat().st_ino);events=snapshot._canonical_bytes(claim.events)
    require(fd_pin==lock_pin and not any(e['step'] in ('db-fence-intent','db-fenced','released',
        'production-a-resume-intent','production-a-resume-consumed','failed-retained') or
        e['step'].startswith('shared-') and ('-stop' in e['step'] or '-restore' in e['step']) for e in claim.events),code)
    refs_raw=snapshot._canonical_bytes(source_refs);boots_raw=snapshot._canonical_bytes(boot_sources)
    selected_raw=snapshot._canonical_bytes(controlled_sources);pins={};result=None;result_raw=None
    paths={};outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    def secure(path,limit=16777216):
        try:
            pair=boot._read_secure(path,0o600,limit,no_atime=True)
            require(pair[1][0]==root_pin[0],code);return pair
        except OSError:raise FormalSnapshotError(code) from None
    for name,ref in source_refs.items():
        require(type(ref) is dict and set(ref)=={'path','sha256'} and
            type(ref['path']) is str and Path(ref['path'])==root/name and
            type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']),code)
        path=root/name;pair=secure(path)
        require(hashlib.sha256(pair[0]).hexdigest()==ref['sha256'],code)
        pins[path]=pair;paths[name]=str(path)
    require(pins[root/'binding.json'][0]==plan and
        hashlib.sha256(pins[root/'approved-source-target.json'][0]).hexdigest()==
            release.get('approvedSourceTargetSha256'),code)
    lab_release=release.get('schemaVersion')=='backup-lab-original-package-binding/v1'
    release_path=root/'original-release-binding.json'
    if lab_release:
        release_original=secure(release_path,16384)
        require(release_original[0]==release_binding_raw,code)
        pins[release_path]=release_original
    targets={root/name for name in generated}|{root/'production-a-source-inventory.json'}
    if not lab_release:targets.add(release_path)
    require(not any(os.path.lexists(path) for path in targets) and not os.path.lexists(root/'database-original.json'),code)
    def owned():
        require(time.monotonic()<deadline and os.getpid()==pid and threading.get_ident()==thread and
            claim.root==root and claim._fd==fd and claim._plan==plan and claim._lock==lock and
            boot._signature(os.fstat(fd))==fd_pin and
            boot._signature(os.stat(lock,follow_symlinks=False))==lock_pin and
            (root.stat().st_dev,root.stat().st_ino)==root_pin and
            snapshot._canonical_bytes(claim.events)==events and
            snapshot._canonical_bytes(source_refs)==refs_raw and snapshot._canonical_bytes(boot_sources)==boots_raw and
            snapshot._canonical_bytes(controlled_sources)==selected_raw and
            (result_raw is None or snapshot._canonical_bytes(result)==result_raw),code)
        claim.assert_owned();snapshot.observation_timeout(1)
        for path,pair in pins.items():require(secure(path)==pair,code)
        for path,pair in pins.items():require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],code)
        require(not os.path.lexists(root/'database-original.json'),code)
    def checked():
        inherited=snapshot.observation_deadline.get()
        retained_token=snapshot.observation_deadline.set(deadline if inherited is None else min(deadline,inherited))
        try:owned();guard();owned()
        finally:snapshot.observation_deadline.reset(retained_token)
    def pin_generated(path):
        require(path not in pins,code);pins[path]=secure(path);paths[path.name]=str(path)
    token=snapshot.observation_deadline.set(deadline)
    try:
        checked()
        if not lab_release:
            claim._write(root/'original-release-binding.json',release_binding_raw)
            pin_generated(root/'original-release-binding.json')
        require(pins[root/'original-release-binding.json'][0]==release_binding_raw,code)
        boot_originals={};controlled_originals={}
        for role in roles:
            checked()
            boot_originals[role]=seal_production_a_boot_original(claim,role,boot_sources[role],
                guard=checked,deadline=deadline,connection=connections.get(role))
            pin_generated(root/('boot-'+role+'-original.json'));checked()
        for role in sorted(controlled_sources):
            checked();path=root/('controlled-'+role+'-inspect.json')
            controlled_originals[role]=controlled.capture_controlled_container_source(path,controlled_sources[role],
                guard=checked,deadline=deadline,transport=docker_sources)
            require(controlled_originals[role].get('path')==str(path),code)
            pin_generated(path);checked()
        prefence=seal_production_a_database_prefence_original(claim,mysql,guard=checked)
        pin_generated(root/'database-prefence-original.json');checked()
        inventory=seal_production_a_source_inventory(claim,release_binding_raw,
            {name:paths[name] for name in PRODUCTION_A_SOURCE_FILES},boot_sources,guard=checked,deadline=deadline)
        pin_generated(root/'production-a-source-inventory.json');checked()
        pair=pins[root/'production-a-source-inventory.json']
        require(inventory['path']==str(root/'production-a-source-inventory.json') and
            inventory['sha256']==hashlib.sha256(pair[0]).hexdigest() and inventory['binding']==
            production_a_resume_binding(release_binding_raw,pair[0],inventory['sha256']),code)
        result=dict(state='A_ORIGINAL_SOURCES_PREPARED_PENDING_INDEPENDENT_AUTHORITY',
            inventory=inventory,bootOriginals=boot_originals,controlledOriginals=controlled_originals,
            databasePrefence=prefence,deadline=deadline,approvalConsumed=False,
            productionEvidence=False,claimReleased=False,releaseReady=False)
        result_raw=snapshot._canonical_bytes(result);checked()
        return result,checked
    finally:snapshot.observation_deadline.reset(token)


def prepare_production_a_observed_normal_sources(claim,*,release_binding_raw,source_refs,boot_sources,
        controlled_sources,mysql,guard,deadline,boot_connections=None,docker_sources=None):
    """Normal preparation adapter: nine originals plus independently read configs.

    No caller-authored config descriptor is accepted by this entry. Existing
    native ten-original preparation remains the only downstream authority
    inventory builder. This adapter performs no capture or grant consumption.
    """
    require_native_runtime()
    import math
    import formal_boot_state as boot
    import formal_controlled_container_sources as controlled
    code='FORMAL_PRODUCTION_A_OBSERVED_PREPARATION_CHANGED'
    generated={'database-prefence-original.json',
        *('boot-'+r+'-original.json' for r in
            ('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal')),
        *('controlled-'+r+'-inspect.json' for r in controlled.ControlledSharedContainerActions.ROLES)}
    required=PRODUCTION_A_SOURCE_FILES-generated-{'original-configs.json'}
    require(type(claim) is FormalMaintenanceClaim and callable(guard) and
        type(deadline) in (int,float) and math.isfinite(deadline) and
        type(source_refs) is dict and set(source_refs)==required,code)
    claim.assert_owned();root=claim.root;plan=claim._plan;refs_raw=snapshot._canonical_bytes(source_refs)
    release=_strict_json(release_binding_raw)
    require(_valid_capture_release(release,claim),code)
    pins={}
    for name,ref in source_refs.items():
        require(type(ref) is dict and set(ref)=={'path','sha256'} and ref.get('path')==str(root/name) and
            type(ref.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']),code)
        pair=boot._read_secure(root/name,0o600,16777216,no_atime=True)
        require(hashlib.sha256(pair[0]).hexdigest()==ref['sha256'],code);pins[name]=pair
    approved=pins['approved-source-target.json'][0]
    digest=source_refs['approved-source-target.json']['sha256']
    require(pins['binding.json'][0]==plan and release.get('approvedSourceTargetSha256')==digest,code)
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    def checked():
        require(snapshot._canonical_bytes(source_refs)==refs_raw and claim.root==root and claim._plan==plan and
            time.monotonic()<deadline,code)
        claim.assert_owned();guard();claim.assert_owned()
        require(snapshot._canonical_bytes(source_refs)==refs_raw and time.monotonic()<deadline,code)
        for name,pair in pins.items():require(boot._read_secure(root/name,0o600,16777216,no_atime=True)==pair,code)
    token=snapshot.observation_deadline.set(deadline)
    try:
        checked()
        config_ref,config_check=seal_production_a_config_originals(claim,approved,digest,
            guard=checked,deadline=deadline)
        # Composition must not recursively invoke the author's retained guard.
        def prepared_guard():checked();config_check();checked()
        refs=dict(source_refs,**{'original-configs.json':config_ref})
        result,retained=prepare_production_a_normal_sources(claim,release_binding_raw=release_binding_raw,
            source_refs=refs,boot_sources=boot_sources,controlled_sources=controlled_sources,mysql=mysql,
            guard=prepared_guard,deadline=deadline,boot_connections=boot_connections,docker_sources=docker_sources)
        def check():
            inherited=snapshot.observation_deadline.get()
            retained_token=snapshot.observation_deadline.set(deadline if inherited is None else min(deadline,inherited))
            try:prepared_guard();retained();prepared_guard()
            finally:snapshot.observation_deadline.reset(retained_token)
        check();return result,check
    finally:snapshot.observation_deadline.reset(token)


def production_a_resume_binding(release_binding_raw, source_inventory_raw, expected_inventory_sha256):
    """Derive grant identity from the whole approved inventory's original bytes.

    File contents and actual sources are checked by the held native owner;
    this pure binding step issues no authorization and proves no exclusion.
    """
    code='FORMAL_PRODUCTION_A_ORIGINAL_SOURCES_INVALID'
    selected=_strict_json(release_binding_raw)
    if type(selected) is dict and selected.get('schemaVersion')=='backup-lab-original-package-binding/v1':
        from formal_backup_lab import current_authority, resume_binding
        return resume_binding(release_binding_raw,source_inventory_raw,expected_inventory_sha256,current_authority())
    try:
        require(type(release_binding_raw) is bytes and 0<len(release_binding_raw)<=16384 and
            type(source_inventory_raw) is bytes and 0<len(source_inventory_raw)<=65536 and
            type(expected_inventory_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_inventory_sha256) and
            hashlib.sha256(source_inventory_raw).hexdigest()==expected_inventory_sha256,code)
        release=_strict_json(release_binding_raw);inventory=_strict_json(source_inventory_raw)
        require(type(release) is dict and release.get('schemaVersion')=='release-formal-original-package-binding/v2' and
            type(release.get('scope')) is dict and release['scope'].get('environment')=='prod' and
            type(inventory) is dict and set(inventory)=={'schemaVersion','claimBindingSha256',
                'approvedSourceTargetSha256','hostBootId','files'} and
            inventory['schemaVersion']=='release-formal-production-a-original-sources/v1' and
            type(inventory['files']) is dict and set(inventory['files'])==PRODUCTION_A_SOURCE_FILES,code)
        require(all(inventory[k]==release[k] and type(inventory[k]) is str and re.fullmatch('[0-9a-f]{64}',inventory[k])
            for k in ('claimBindingSha256','approvedSourceTargetSha256')),code)
        paths=set()
        for ref in inventory['files'].values():
            require(type(ref) is dict and set(ref)=={'path','sha256'} and type(ref['path']) is str and
                ref['path'].startswith('/') and '\\' not in ref['path'] and
                all(p not in ('','.','..') for p in ref['path'].split('/')[1:]) and
                not any(ord(c)<32 for c in ref['path']) and ref['path'] not in paths and
                type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']),code)
            paths.add(ref['path'])
        package=release['package']
        require(type(package) is dict and set(package)=={'releaseTag','packageDigest','manifestDigest','planDigest'} and
            type(package['releaseTag']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,122}',package['releaseTag']) and
            all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for k,v in package.items() if k!='releaseTag') and
            type(inventory['hostBootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',inventory['hostBootId']) and
            all(type(release[k]) is str and re.fullmatch('[0-9a-f]{64}',release[k])
                for k in ('deploymentAttemptId','leaseTokenDigest')),code)
        return dict(environment='prod',operationId='prod-'+package['releaseTag'],**package,
            attemptId=release['deploymentAttemptId'],leaseTokenDigest=release['leaseTokenDigest'],
            approvedSourceTargetSha256=inventory['approvedSourceTargetSha256'],
            sourceBindingSha256=expected_inventory_sha256,hostBootId=inventory['hostBootId'])
    except (KeyError,TypeError,ValueError,RecursionError):
        raise FormalSnapshotError(code) from None


class ProductionAResumeChecks:
    """Retain the real one-attempt grant and originals during necessary recovery.

    Construction invokes the existing signed consumer once, under the same
    native claim. Subsequent calls read its exact private marker and journal;
    they neither consume again nor write OPEN/boot state or start a service.
    The supplied source guard remains responsible for actual held protection.
    """
    def __init__(self,claim,release_binding_raw,source_inventory_raw,expected_inventory_sha256,
                 resume,*,guard,thaw_guard):
        require_native_runtime()
        import formal_boot_state as boot
        import formal_open_authorization as authorization
        code='FORMAL_PRODUCTION_A_RESUME_OWNER_INVALID'
        require(os.geteuid()==0 and type(claim) is FormalMaintenanceClaim and
            callable(guard) and callable(thaw_guard),code)
        self.claim=claim;self.guard=guard;self.thaw_guard=thaw_guard
        self.binding=production_a_resume_binding(release_binding_raw,source_inventory_raw,expected_inventory_sha256)
        self.binding_raw=authorization._production_a_binding(self.binding)
        require(type(resume) is dict and set(resume)=={'registry','approval','trustedKey'} and
            type(resume['registry']) is dict and set(resume['registry'])=={'path','identity'} and
            all(type(resume[k]) is dict and set(resume[k])=={'path','sha256'} and
                type(resume[k]['sha256']) is str and re.fullmatch('[0-9a-f]{64}',resume[k]['sha256'])
                for k in ('approval','trustedKey')),code)
        self.resume=_strict_json(snapshot._canonical_bytes(resume));self.pins={};self.directories={}
        self.registry=boot._absolute(self.resume['registry']['path'])
        identity=self.resume['registry']['identity']
        require(type(identity) is dict and set(identity)=={'dev','ino','uid','gid','mode'} and
            all(type(v) is int for v in identity.values()) and identity['dev']>=0 and identity['ino']>0 and
            identity['uid']==0 and identity['mode']==stat.S_IFDIR|0o700 and
            self.registry!=claim.root and self.registry not in claim.root.parents and claim.root not in self.registry.parents,code)
        with boot._directory(self.registry,no_atime=True) as (fd,chain):
            actual=os.fstat(fd)
            require({k:getattr(actual,'st_'+k) for k in identity}==identity and
                actual.st_dev==claim.root.stat().st_dev,code)
            self.directories[self.registry]=chain
        inventory=_strict_json(source_inventory_raw)
        self.database_prefence_raw=None
        self.database_prefence_path=None
        def pin(path,mode,limit,expected):
            path=boot._absolute(path);require(path not in self.pins,code)
            pair=boot._read_secure(path,mode,limit,no_atime=True)
            require(hashlib.sha256(pair[0]).hexdigest()==expected and pair[1][0]==identity['dev'],code)
            with boot._directory(path.parent,no_atime=True) as (_,chain):self.directories[path.parent]=chain
            self.pins[path]=(mode,limit,pair)
            return pair[0]
        for name,ref in inventory['files'].items():
            raw=pin(ref['path'],0o600,16777216,ref['sha256'])
            if name=='database-prefence-original.json':
                self.database_prefence_raw=raw
                self.database_prefence_path=boot._absolute(ref['path'])
            if name=='binding.json':require(raw==claim._plan,code)
            if name=='approved-source-target.json':require(hashlib.sha256(raw).hexdigest()==self.binding['approvedSourceTargetSha256'],code)
        require(self.database_prefence_raw is not None and
            boot._absolute(inventory['files']['database-prefence-original.json']['path'])!=
                claim.root/'database-original.json',code)
        claim_binding=_strict_json(claim._plan)
        self.database_prefence_flags=_production_a_database_flags(
            self.database_prefence_raw,claim_binding['databaseUuid'])
        self.database_original_pair=None
        self.control_device=identity['dev']
        with boot._directory(claim.root,no_atime=True) as (_,chain):
            self.database_original_directory=chain
        self.database_original_path=claim.root/'database-original.json'
        pin(str(claim.root/'original-release-binding.json'),0o600,16384,
            hashlib.sha256(release_binding_raw).hexdigest())
        for name,mode,limit in (('approval',0o600,8192),('trustedKey',0o644,4096)):
            ref=self.resume[name];pin(ref['path'],mode,limit,ref['sha256'])
        require(hashlib.sha256(claim._plan).hexdigest()==inventory['claimBindingSha256'],code)
        self.prefix=_strict_json(snapshot._canonical_bytes(claim.events));self.consumed=None
        self._current()
        result=authorization.consume_production_a_resume_approval(claim,str(self.registry),
            self.resume['approval']['path'],self.resume['trustedKey']['path'],self.resume['trustedKey']['sha256'],
            self.binding,guard=self._current)
        require(result['state']=='PRODUCTION_A_RESUME_CONSUMED_PENDING_SERVICE_ACTIONS' and
            result['approvalConsumed'] is True and result['serviceActionsPerformed'] is False and
            all(result[k]==v for k,v in self.binding.items()),code)
        marker='production-a-resume-grant-'+result['grantId']+'.json'
        pin(str(self.registry/marker),0o600,8192,result['markerSha256'])
        self.consumed=_strict_json(snapshot._canonical_bytes(result))
        self.prefix=_strict_json(snapshot._canonical_bytes(claim.events))
        self._wall=time.time();self._clock=time.monotonic()
        self._current()

    def _check_database_original(self):
        import formal_boot_state as boot
        code='FORMAL_PRODUCTION_A_DATABASE_ORIGINAL_CHANGED'
        intents=[event for event in self.claim.events if event.get('step')=='db-fence-intent']
        fenced=[event for event in self.claim.events if event.get('step')=='db-fenced']
        require(len(intents)<=1 and len(fenced)<=1 and (not fenced or len(intents)==1),code)
        boot._directory_unchanged(self.claim.root,self.database_original_directory)
        require(self.database_prefence_path in self.pins and
            self.pins[self.database_prefence_path][2][0]==self.database_prefence_raw and
            snapshot._canonical_bytes(self.database_prefence_flags)==self.database_prefence_raw,code)
        if not intents:
            try:os.stat(self.database_original_path,follow_symlinks=False)
            except FileNotFoundError:
                require(self.database_original_pair is None,code)
                return
            require(False,code)
        intent=intents[0]
        require(type(intent.get('details')) is dict and type(intent.get('sequence')) is int,code)
        pair=boot._read_secure(self.database_original_path,0o600,16384,no_atime=True)
        require(pair[1][0]==self.control_device,code)
        flags=verify_production_a_database_fence_original(self.database_prefence_raw,pair[0],
            intent['details'],self.database_prefence_flags['serverUuid'])
        if fenced:
            completed=fenced[0]
            details=completed.get('details')
            require(type(completed.get('sequence')) is int and completed['sequence']>intent['sequence'] and
                type(details) is dict and set(details)=={'originalSha256','reconciled'} and
                details['originalSha256']==hashlib.sha256(pair[0]).hexdigest() and
                type(details['reconciled']) is bool,code)
        require(flags==self.database_prefence_flags,code)
        if self.database_original_pair is None:self.database_original_pair=pair
        else:require(pair==self.database_original_pair,code)

    def _current(self):
        import formal_boot_state as boot
        import formal_open_authorization as authorization
        code='FORMAL_PRODUCTION_A_RESUME_OWNER_CHANGED'
        self.thaw_guard();self.claim.assert_owned();self.guard();snapshot.observation_timeout(1)
        require(snapshot._canonical_bytes(self.claim.events[:len(self.prefix)])==snapshot._canonical_bytes(self.prefix),code)
        require(Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()==self.binding['hostBootId'],code)
        # Check directory identity before dereferencing its pinned files.
        for path,chain in self.directories.items():boot._directory_unchanged(path,chain)
        for path,(mode,limit,pair) in self.pins.items():
            require(boot._read_secure(path,mode,limit,no_atime=True)==pair,code)
        for path,chain in self.directories.items():boot._directory_unchanged(path,chain)
        self._check_database_original()
        if self.consumed is not None:
            elapsed=time.monotonic()-self._clock;wall=time.time()
            require(elapsed>=0 and abs(wall-self._wall-elapsed)<2 and
                self.consumed['issuedAt']<=wall<self.consumed['expiresAt'] and
                self._wall+elapsed<self.consumed['expiresAt'],code)
        self.claim.assert_owned();self.thaw_guard()
        # Terminal callbacks may replace previously read originals: identities
        # are checked after the last callback, without another observer after.
        self._check_database_original()
        for path,(_,_,pair) in self.pins.items():require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],code)
        for path,chain in self.directories.items():boot._directory_unchanged(path,chain)
        require(self.binding_raw==authorization._production_a_binding(self.binding),code)
        snapshot.observation_timeout(1)

    def control_phase_guard(self, *, maintenance_end, deadline):
        """Return a same-owner guard for the finite control-device phase.

        This phase only keeps the already consumed authority and original
        control files stable while another owner performs the real stop/freeze
        work. It deliberately does not invoke SQL, service, source, or thaw
        observers and it never consumes approval or changes boot state.
        """
        # Keep unsupported hosts on the typed runtime refusal before touching
        # ``self``; this is also the only runtime capability check here.
        require_native_runtime()
        import formal_boot_state as boot
        import formal_open_authorization as authorization
        import math
        import threading
        code='FORMAL_PRODUCTION_A_RESUME_CONTROL_CHANGED'
        require(type(self) is ProductionAResumeChecks and
            type(maintenance_end) in (int, float) and math.isfinite(maintenance_end) and
            type(deadline) in (int, float) and math.isfinite(deadline) and
            maintenance_end > 0 and deadline > 0,code)
        require(os.geteuid()==0 and type(self.claim) is FormalMaintenanceClaim and
            self.consumed is not None and self.claim._fd is not None,code)
        self._check_database_original()
        claim=self.claim; owner_fd=claim._fd; plan=claim._plan
        owner_pid=os.getpid(); owner_thread=threading.get_ident()
        root=claim.root; lock=claim._lock
        binding_raw=self.binding_raw; consumed_raw=snapshot._canonical_bytes(self.consumed)
        prefix_raw=snapshot._canonical_bytes(self.prefix); prefix_length=len(self.prefix)
        issued=self.consumed['issuedAt'];expires=self.consumed['expiresAt']
        wall_origin=self._wall;clock_origin=self._clock
        authority_end=min(expires,maintenance_end)
        clock_end=min(deadline,clock_origin+authority_end-wall_origin)
        root_info=os.stat(root,follow_symlinks=False)
        root_identity=(root_info.st_dev,root_info.st_ino)
        require(root_info.st_uid==0 and root_info.st_mode==stat.S_IFDIR|0o700,code)
        fd_signature=boot._signature(os.fstat(owner_fd))
        require(fd_signature[2]==0 and fd_signature[4]==stat.S_IFREG|0o600 and
            fd_signature[5]==1,code)
        lock_signature=boot._signature(os.stat(lock,follow_symlinks=False))
        require(fd_signature==lock_signature,code)
        root_dev=root_info.st_dev
        control_directories=dict(self.directories)
        control_pins=dict(self.pins)
        with boot._directory(root,no_atime=True) as (_,chain):
            control_directories[root]=chain

        def secure(path, mode, limit):
            try:
                return boot._read_secure(path,mode,limit,no_atime=True)
            except (OSError, ValueError):
                raise snapshot.FormalSnapshotError(code) from None

        # Existing journal files are pinned by inode and content. New records
        # may be appended only through this already owned claim.
        journal={root/'binding.json':secure(root/'binding.json',0o600,16384)}
        for event in self.claim.events:
            path=root/('event-%06d.json'%event['sequence'])
            journal[path]=secure(path,0o600,16384)

        def check():
            require(os.getpid()==owner_pid and threading.get_ident()==owner_thread,code)
            require(self.claim is claim and claim._fd==owner_fd and claim.root==root and
                claim._lock==lock and claim._plan==plan and
                boot._signature(os.fstat(owner_fd))==fd_signature and
                boot._signature(os.stat(lock,follow_symlinks=False))==lock_signature,
                code)
            for path,chain in control_directories.items():
                try:boot._directory_unchanged(path,chain)
                except (OSError, ValueError):raise snapshot.FormalSnapshotError(code) from None
            current_root=os.stat(root,follow_symlinks=False)
            require((current_root.st_dev,current_root.st_ino)==root_identity and
                current_root.st_dev==root_dev,code)
            claim.assert_owned()
            require(snapshot._canonical_bytes(claim.events[:prefix_length])==prefix_raw and
                snapshot._canonical_bytes(self.prefix)==prefix_raw and
                snapshot._canonical_bytes(self.consumed)==consumed_raw and
                self.binding_raw==binding_raw==authorization._production_a_binding(self.binding),code)
            require(Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()==
                self.binding['hostBootId'],code)
            now_wall=time.time();now_clock=time.monotonic()
            elapsed=now_clock-clock_origin
            require(elapsed>=0 and abs(now_wall-wall_origin-elapsed)<2 and
                issued<=now_wall<authority_end and now_clock<clock_end,code)
            snapshot.observation_timeout(1)
            require(self.pins==control_pins and self.directories==control_directories,code)
            for path,(mode,limit,pair) in control_pins.items():
                current=secure(path,mode,limit)
                require(current==pair and current[1][0]==root_dev,code)
            for path,pair in journal.items():
                require(secure(path,0o600,16384)==pair,code)
            for event in claim.events[prefix_length:]:
                path=root/('event-%06d.json'%event['sequence'])
                if path not in journal:
                    pair=secure(path,0o600,16384)
                    require(pair[0]==snapshot._canonical_bytes(event) and pair[1][0]==root_dev,code)
                    journal[path]=pair
            claim.assert_owned()
            for path,(_,_,pair) in control_pins.items():
                require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],code)
            for path,pair in journal.items():
                require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],code)
            for path,chain in control_directories.items():
                try:boot._directory_unchanged(path,chain)
                except (OSError, ValueError):raise snapshot.FormalSnapshotError(code) from None
            self._check_database_original()
            require(time.monotonic()<clock_end and time.time()<authority_end,code)
            snapshot.observation_timeout(1)

        check()
        return check

    def __call__(self):
        require(self.consumed is not None,'FORMAL_PRODUCTION_A_RESUME_CONSUMPTION_REQUIRED')
        self._current()




def restore_production_a_original_participants(claim,mysql,shared_result,*,resume_checks,
        original_content_guard,thaw_guard,external_transport,host_native,health_probe,ingress_native,
        maintenance_end,deadline):
    """Restore original participants and return a receipt plus the retained NAS guard.

    The normal owner supplies its original capture-epoch content guard and its
    unchanged deadline. Its resume checker must observe live SQL ownership
    without a stopped-only caller/host callback. This function neither opens a
    new claim nor releases it, consumes approval again, or accepts a NAS copy.
    Uncertain effects are retained; no recovery action is replayed.
    """
    require_native_runtime()
    import math
    import formal_split_capture as split
    import formal_service_health as health
    import formal_external_callers as external
    import formal_host_admission as host
    import formal_ingress_control as ingress
    code='FORMAL_PRODUCTION_A_RESTORATION_PREREQUISITE_REQUIRED'
    require(os.geteuid()==0 and type(claim) is FormalMaintenanceClaim and
        _valid_resume_owner(resume_checks,claim) and
        resume_checks.consumed is not None and callable(original_content_guard) and callable(thaw_guard) and
        all(value is not None for value in (mysql,external_transport,host_native,health_probe,ingress_native)) and
        all(type(value) in (int,float) and math.isfinite(value) and value>0
            for value in (maintenance_end,deadline)),code)
    require(type(shared_result) is dict and shared_result.get('state')==
        'A_SHARED_CAPTURED_AND_ORIGINAL_SERVICES_RESTORED_PENDING_REMAINING_OWNER' and
        all(shared_result.get(k) is False for k in ('productionEvidence','fullRunnerCompleted','releaseReady','claimReleased')) and
        type(shared_result.get('ingressRulesSha256')) is str and
        re.fullmatch('[0-9a-f]{64}',shared_result['ingressRulesSha256']),code)
    required={'split-captured','shared-db-restored',*('shared-'+r+'-restored' for r in split.RESTORE_ORDER)}
    require(all(sum(e['step']==name for e in claim.events)==1 for name in required),code)
    require(not any(e['step'] in ('external-recovery-intent','ingress-release-intent','ingress-released',
        'released','failed-retained') or e['step'].startswith('host-') and
        ('-restore-intent' in e['step'] or e['step'].endswith('-restored')) for e in claim.events),
        'FORMAL_PRODUCTION_A_RESTORATION_REPLAY_REFUSED')
    shared_raw=snapshot._canonical_bytes(shared_result)
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    control=resume_checks.control_phase_guard(maintenance_end=maintenance_end,deadline=deadline)
    active_unit=None;released=False;held_table=None

    def private():
        control();claim.assert_owned()
        require(snapshot._canonical_bytes(shared_result)==shared_raw,code)
        require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        thaw_guard();original_content_guard();control();claim.assert_owned()

    private();host_plan=host._bound(claim);private()
    host_plan_raw=snapshot._canonical_bytes(host_plan)

    def base():
        private();resume_checks();private()
        require(snapshot._canonical_bytes(host._bound(claim))==host_plan_raw,
            'FORMAL_HOST_ORIGINAL_BINDING_CHANGED')
        require(host_native.capabilities(deadline)==host_plan['host'],'FORMAL_HOST_ORIGINAL_BINDING_CHANGED')
        restored=[u for u in host.RESTORE_ORDER if host._event(claim,host._step(u,'-restored')) is not None]
        require(restored==list(host.RESTORE_ORDER[:len(restored)]),'FORMAL_HOST_ACTION_PENDING_OR_OUT_OF_ORDER')
        host._prefix(claim,host_plan,host_native,restored,deadline,restored=True)
        pending=[u for u in host.CLOSE_ORDER if u not in restored and u!=active_unit]
        host._prefix(claim,host_plan,host_native,pending,deadline)
        if released:
            observed=ingress.observe_ingress_reconciliation(claim,native=ingress_native)
            require(observed.get('state')=='RELEASED' and observed.get('present') is False and
                observed.get('table')==held_table and observed.get('actionReplayed') is False,
                'FORMAL_PRODUCTION_A_RESTORATION_INGRESS_CHANGED')
        else:
            observed=ingress.assert_ingress(claim,native=ingress_native)
            require(observed.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
                observed.get('rulesSha256')==shared_result['ingressRulesSha256'] and
                (held_table is None or observed.get('table')==held_table),
                'FORMAL_PRODUCTION_A_RESTORATION_INGRESS_CHANGED')
        private()

    def seconds():
        private()
        return min(120,max(1,int(snapshot.observation_timeout(deadline-time.monotonic()))))

    def shared_dependency():
        nonlocal shared_health
        base()
        result=health.observe_shared_recovery_health(claim,mysql,guard=base,thaw_guard=thaw_guard,
            timeout=seconds(),probe=health_probe)
        require(type(result) is dict and result.get('state')=='ORIGINAL_SERVICES_HEALTHY' and
            result.get('productionEvidence') is False,'FORMAL_PRODUCTION_A_RESTORATION_SHARED_HEALTH_REQUIRED')
        base();shared_health=result;return result

    def external_health():
        nonlocal caller_health
        shared_dependency()
        result=external.observe_external_restoration_health(claim,external_transport,
            dependency_guard=shared_dependency,seconds=seconds())
        require(type(result) is dict and result.get('state')=='EXTERNAL_CALLERS_HEALTHY_INGRESS_HELD' and
            result.get('productionEvidence') is False and result.get('claimReleased') is False,
            'FORMAL_PRODUCTION_A_RESTORATION_EXTERNAL_HEALTH_REQUIRED')
        base();caller_health=result;return result

    def complete_dependency():
        external_health();base()

    def archive_guard():
        # Preserve the original budget after this function returns to its NAS
        # caller; a health helper must not open a fresh observation window.
        current=snapshot.observation_deadline.get()
        token=snapshot.observation_deadline.set(deadline if current is None else min(deadline,current))
        try:complete_dependency()
        finally:snapshot.observation_deadline.reset(token)

    token=snapshot.observation_deadline.set(deadline)
    try:
        base();held_table=ingress.assert_ingress(claim,native=ingress_native)['table']
        shared_health=shared_dependency()
        result=external.restore_external_services_with_health(claim,external_transport,
            dependency_guard=shared_dependency,seconds=seconds())
        require(type(result) is dict and result.get('state')=='EXTERNAL_CALLERS_HEALTHY_INGRESS_HELD' and
            result.get('productionEvidence') is False and result.get('claimReleased') is False,
            'FORMAL_PRODUCTION_A_RESTORATION_EXTERNAL_HEALTH_REQUIRED')
        caller_health=external_health()
        for unit in host.RESTORE_ORDER:
            complete_dependency();active_unit=unit
            result=host.restore_host_admission(claim,unit,guard=base,recovery_guard=complete_dependency,
                native=host_native,timeout=seconds())
            require(type(result) is dict and result.get('state')=='HOST_ENTRY_RESTORED_DERIVED_WORK_PENDING' and
                host._event(claim,host._step(unit,'-restored')) is not None,
                'FORMAL_PRODUCTION_A_RESTORATION_HOST_REQUIRED')
            active_unit=None;complete_dependency()
        complete_dependency()
        result=ingress.release_ingress(claim,complete_dependency,native=ingress_native)
        require(type(result) is dict and result.get('state')=='INGRESS_RELEASED' and
            result.get('table')==held_table,'FORMAL_PRODUCTION_A_RESTORATION_INGRESS_CHANGED')
        released=True;archive_guard()
        return (dict(state='ORIGINAL_PARTICIPANTS_RESTORED_INGRESS_RELEASED_PENDING_NAS',
            sharedHealth=shared_health,externalHealth=caller_health,hostEntries=list(host.RESTORE_ORDER),
            ingress=result,productionEvidence=False,releaseReady=False,fullRunnerCompleted=False,
            claimReleased=False,nasArchiveVerified=False),archive_guard)
    finally:snapshot.observation_deadline.reset(token)


def run_production_a_shared_lifecycle(claim,request,*,approved_source,resume_checks,
        container_actions,source_guard,maintenance_end,recovery_flows):
    """Join the real controlled phases under an already consumed A authority.

    The outer owner must establish and retain the actual host/caller/ingress
    and approved storage protection. Its source_guard observes those sources
    without SQL; this function invokes it only outside native freeze. The live
    guard retained by resume_checks checks actual SQL ownership before stop and
    after exact database restoration. Neither callback grants full exclusion.

    No new claim, approval, boot/OPEN write, automatic recovery or NAS success
    exists here. Failure preserves the real journal/effects and the held claim.
    Original configs are captured before stops; immutable old application
    images are captured after thaw and before any restoration. Both are read
    back across restoration. Return the receipt, original content guard,
    original thaw guard, MySQL observer and original deadline as a tuple. The
    outer owner must use those retained guards through remaining restoration
    and NAS acceptance; it must not reconstruct the capture's identity epoch.
    """
    require_native_runtime()
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    if output_budget is not None:
        require(output_budget.claim is claim,'FORMAL_CAPTURE_OUTPUT_OWNER_CHANGED')
        output_budget.require_full_capture_admission()
    import math
    import formal_split_capture as split
    import formal_ingress_control as ingress
    import formal_controlled_container_sources as controlled
    import formal_boot_state as boot
    import formal_selected_config_capture as config_capture
    import formal_original_launch_capture as launch_capture
    code='FORMAL_PRODUCTION_A_SHARED_OWNER_INVALID'
    require(os.geteuid()==0 and type(claim) is FormalMaintenanceClaim and
        _valid_resume_owner(resume_checks,claim) and
        resume_checks.consumed is not None and callable(source_guard) and
        type(container_actions) is controlled.ControlledSharedContainerActions and
        type(maintenance_end) in (int,float) and math.isfinite(maintenance_end),code)
    _validate_selected_source_request(request,approved_source)
    if request['schemaVersion']=='backup-lab-capture-request/v1':
        from formal_backup_lab import LabResumeChecks
        require(type(resume_checks) is LabResumeChecks,'BACKUP_LAB_RESUME_OWNER_REQUIRED')
    else:require(type(resume_checks) is ProductionAResumeChecks,'FORMAL_PRODUCTION_A_RESUME_OWNER_INVALID')
    # The signed A binding carries the whole source-inventory digest. Its
    # original claim bytes remain in the consumer's private pins, rather than
    # an extra field on the independently signed authorization contract.
    plan_pin=resume_checks.pins.get(claim.root/'binding.json')
    require(type(plan_pin) is tuple and len(plan_pin)==3 and
        type(plan_pin[2]) is tuple and len(plan_pin[2])==2 and
        plan_pin[2][0]==claim._plan,code)
    require(Path(request['claimRoot'])==claim.root and
        snapshot._canonical_bytes(request['claimBinding'])==claim._plan and
        approved_source.get('targetRawSha256')==resume_checks.binding['approvedSourceTargetSha256'] and
        request['filesystemFence']['binding']['bootId']==resume_checks.binding['hostBootId'],code)
    # An old or uncertain phase is not a request to resume/replay its actions.
    forbidden={'db-fence-intent','db-fenced','shared-recovery-intent','split-sql-intent',
        'split-sql-captured','split-raw-intent','split-captured','ingress-recovery-intent',
        'ingress-recovery-permitted','released','failed-retained'}
    require(not any(event['step'] in forbidden or
        event['step'].startswith('shared-') and ('-stop' in event['step'] or '-restore' in event['step'])
        for event in claim.events),'FORMAL_PRODUCTION_A_SHARED_REPLAY_REFUSED')
    for name,key in (('shared-container-original.json','sharedScopeSha256'),
                     ('shared-health-original.json','originalHealthSha256')):
        path=claim.root/name
        require(path in resume_checks.pins and
            hashlib.sha256(resume_checks.pins[path][2][0]).hexdigest()==request[key],code)
    request_raw=snapshot._canonical_bytes(request);source_raw=snapshot._canonical_bytes(approved_source)
    flows_raw=snapshot._canonical_bytes(recovery_flows)
    action_pin=container_actions._pin
    require(controlled.launch._canonical(container_actions._originals)==action_pin,code)
    plan=_strict_json(claim._read(claim.root/'ingress-plan.json'))
    # Validate dependency flows against the real retained plan before stops.
    ingress.render_recovery_policy(hashlib.sha256(claim._plan).hexdigest(),plan,recovery_flows)
    started=time.monotonic();deadline=started+request['totalSeconds']
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    from formal_capture_incremental import active_series
    admitted_series=active_series.get()
    if admitted_series is not None:
        admitted_series.check()
        deadline=min(deadline,started+admitted_series.catalog['stopWindowMilliseconds']/1000,
            started+maintenance_end-time.time())
        require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
    token=snapshot.observation_deadline.set(deadline)
    try:
        control=resume_checks.control_phase_guard(maintenance_end=maintenance_end,deadline=deadline)
        recovery_rules=None
        inventory_path=claim.root/'production-a-source-inventory.json'
        inventory_pair=None;config_identity=None;original_images=None;image_raw=None
        payload_identity=None;archive_identity=None;shared_receipt=None;shared_receipt_raw=None
        image_path=claim.root/'payload'/'original-application-images.tar'
        image_identity=None;image_directory=None;image_receipt_pair=None
        credential_path=boot._absolute(request['mysqlCredentialFile'])
        def secure_credential():
            try:return boot._read_secure(credential_path,0o600,16384,no_atime=True)
            except (OSError,ValueError):
                raise FormalSnapshotError('FORMAL_PRODUCTION_A_SHARED_CREDENTIAL_UNAVAILABLE') from None
        credential_pair=secure_credential()
        require(credential_pair[1][0]==claim.root.stat().st_dev,
            'FORMAL_PRODUCTION_A_SHARED_CREDENTIAL_DEVICE_CHANGED')
        with boot._directory(credential_path.parent,no_atime=True) as (_,credential_parents):pass
        def image_identity_check():
            if image_identity is not None:
                try:observed=boot._signature(os.stat(image_path,follow_symlinks=False))
                except OSError:
                    raise FormalSnapshotError('FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED') from None
                require(observed==image_identity,'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
                boot._directory_unchanged(image_path.parent,image_directory)
        def private_guard():
            control()
            boot._directory_unchanged(credential_path.parent,credential_parents)
            require(secure_credential()==credential_pair,
                'FORMAL_PRODUCTION_A_SHARED_CREDENTIAL_CHANGED')
            require(snapshot._canonical_bytes(request)==request_raw and
                snapshot._canonical_bytes(approved_source)==source_raw and
                snapshot._canonical_bytes(recovery_flows)==flows_raw and
                container_actions._pin==action_pin==controlled.launch._canonical(container_actions._originals),
                'FORMAL_PRODUCTION_A_SHARED_INPUT_CHANGED')
            require(boot._signature(os.stat(credential_path,follow_symlinks=False))==credential_pair[1],
                'FORMAL_PRODUCTION_A_SHARED_CREDENTIAL_CHANGED')
            boot._directory_unchanged(credential_path.parent,credential_parents)
            if inventory_pair is not None:
                require(boot._read_secure(inventory_path,0o600,65536,no_atime=True)==inventory_pair,
                    'FORMAL_PRODUCTION_A_ORIGINAL_INVENTORY_CHANGED')
            image_identity_check()
            if image_raw is not None:
                require(snapshot._canonical_bytes(original_images)==image_raw,
                    'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
            if image_receipt_pair is not None:
                require(boot._read_secure(image_path.parent/'050-original-images.json',0o600,16384,
                    no_atime=True)==image_receipt_pair,'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
            require(time.monotonic()<deadline,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        def thaw_guard():
            private_guard();result=split._thaw_receipt(claim);private_guard();return result
        def current():
            thaw_guard();source_guard();private_guard()
            names={event['step'] for event in claim.events}
            # Switch before the first MySQL stop action: its durable intent
            # exists before callbacks made by the actual action adapter.
            # A successful restart alone is insufficient; flags must be exact
            # and journal-completed before live ownership permits other writers.
            if 'shared-mysql-stop-intent' not in names or 'shared-db-restored' in names:
                resume_checks();private_guard()
            if recovery_rules is not None:
                held=ingress.assert_ingress(claim)
                require(held.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
                    held.get('rulesSha256')==recovery_rules,
                    'FORMAL_PRODUCTION_A_SHARED_RECOVERY_INGRESS_CHANGED')
                private_guard()
            thaw_guard()
            if config_identity is not None:config_identity()
            if payload_identity is not None:payload_identity()
            if archive_identity is not None:archive_identity()
        current()
        # Read the exact source inventory consumed by the signed A binding.
        # Caller-selected observations cannot replace those approved originals.
        try:inventory_pair=boot._read_secure(inventory_path,0o600,65536,no_atime=True)
        except (OSError,ValueError):
            raise FormalSnapshotError('FORMAL_PRODUCTION_A_ORIGINAL_INVENTORY_REQUIRED') from None
        require(inventory_pair[1][0]==claim.root.stat().st_dev and
            hashlib.sha256(inventory_pair[0]).hexdigest()==resume_checks.binding['sourceBindingSha256'],
            'FORMAL_PRODUCTION_A_ORIGINAL_INVENTORY_CHANGED')
        inventory=_strict_json(inventory_pair[0])
        def source_original(name):
            ref=inventory['files'][name];path=boot._absolute(ref['path']);pin=resume_checks.pins.get(path)
            require(type(pin) is tuple and len(pin)==3 and type(pin[2]) is tuple and len(pin[2])==2 and
                hashlib.sha256(pin[2][0]).hexdigest()==ref['sha256'] and
                pin[2][1][0]==claim.root.stat().st_dev and
                boot._read_secure(path,pin[0],pin[1],no_atime=True)==pin[2],
                'FORMAL_PRODUCTION_A_ORIGINAL_SOURCE_CHANGED')
            return _strict_json(pin[2][0])
        config_originals=source_original('original-configs.json')
        config_root=boot._absolute(source_original('approved-source-target.json')['root'])
        current()
        original_configs=config_capture.capture_selected_config_originals(config_root,config_originals,
            claim.root/'original-configs',guard=current)
        from formal_capture_incremental import active_series
        series = active_series.get()
        material_entries = {} if series is None else series.materials(claim.root/'recovery-materials', guard=current)
        if series is not None:
            require(hasattr(series, 'semantic_source'), 'FORMAL_CAPTURE_SEMANTIC_SOURCE_REQUIRED')
        semantic = None if series is None else series.semantic_source
        if series is not None:
            from formal_capture_semantics import SemanticCapture
            require(type(semantic) is SemanticCapture and semantic.series is series,
                'FORMAL_CAPTURE_SEMANTIC_SOURCE_REQUIRED')
        require(type(original_configs) is dict and original_configs.get('state')==
            'SELECTED_CONFIG_ORIGINALS_CAPTURED_PENDING_FULL_PROTECTION' and
            original_configs.get('productionEvidence') is False,
            'FORMAL_PRODUCTION_A_ORIGINAL_CONFIG_CAPTURE_REQUIRED')
        config_reference,config_identity=config_capture.verify_selected_config_originals(config_root,
            config_originals,claim.root/'original-configs',original_configs,guard=current)
        current()
        require(deadline-time.monotonic()>request['filesystemFence']['seconds']+20,
            'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
        credential=read_credential(request['mysqlCredentialFile'])
        mysql=PrivateDockerMySql(request['mysqlContainerId'],credential,timeout=5)
        for role in split.STOP_ORDER[:-1]:
            current()
            if role == 'minio' and semantic is not None:
                # All application writers are already stopped; the independent
                # source/host/ingress writer barriers remain held. Read the real
                # source before its original stop, without changing stop order.
                semantic.capture(mysql, request['database'], claim.root/'semantic-capture', current)
                current()
            split.stop_controlled_shared_writer(claim,role,
                expected_shared_scope_sha256=request['sharedScopeSha256'],
                guard=current,container_actions=container_actions)
            current()
        split.assert_controlled_prefence_stops(claim,
            expected_shared_scope_sha256=request['sharedScopeSha256'],guard=current)
        # The actual acquire seals database-original and records intent before
        # its next guard/SET. The existing authority guard compares those exact
        # bytes with the sealed pre-fence original before mutation proceeds.
        snapshot.acquire_claimed_database_fence(claim,mysql,guard=current)
        current()
        capture=run_controlled_shared_capture_request(claim,request,current,
            approved_source=approved_source,native_guard=private_guard,container_actions=container_actions)
        require(type(capture) is dict and
            capture.get('state')=='SHARED_PAYLOAD_CAPTURED_INGRESS_HELD' and
            capture.get('native',{}).get('nativeState')=='THAWED_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS',
            'FORMAL_PRODUCTION_A_SHARED_CAPTURE_REQUIRED')
        current()
        # Retain the SQL/raw epoch before image export or any original restart.
        # A later archive reader must not establish a fresh baseline for data
        # replaced after capture. Native controls remain owned by thaw_guard.
        payload_code='FORMAL_PRODUCTION_A_CAPTURED_PAYLOAD_CHANGED'
        payload_root=claim.root/'payload';raw_root=payload_root/'minio-physical'
        proof_names=('006-database-rejection-before.json','010-sql-started.json','011-source-data.json',
            '012-source-data-after.json','013-source-migration-ledger.json','014-source-migration-ledger-after.json',
            '015-source-data-binding.json','016-source-migration-binding.json','018-database-rejection-after.json')
        payload_files=('database.sql.gz','020-sql.json','040-payload.json',*proof_names)
        from formal_capture_incremental import active_series, verify_series_physical, write_record
        series = active_series.get()
        if series is not None:
            series.check()
            write_record(payload_root/'capture-content-point.json', series.point(source_restored=False))
            write_record(payload_root/'capture-file-inventory.json', series.file_inventory)
            semantic_supplement, semantic_entries = semantic.finalize(series.point(source_restored=False), current)
            material_entries.update(semantic_entries)
            payload_files += ('capture-content-point.json','capture-file-inventory.json')
            if series.spec['pointType'] == 'INCREMENTAL':
                payload_files += ('database.sql.incremental.raw','database.sql.incremental-scope.json')
        image_names={'original-application-images.tar','050-original-images.json'}
        payload_pins={};payload_pairs={}
        captured_payload_entries={'payload':'directory'}
        sql=capture.get('sql');raw_capture=capture.get('payload')
        require(type(sql) is dict and type(raw_capture) is dict and
            type(sql.get('database')) is dict and raw_capture.get('database')==sql['database'] and
            raw_capture.get('splitSqlReceiptSha256')==
                hashlib.sha256(snapshot._canonical_bytes(sql)).hexdigest(),payload_code)
        captured_raw=snapshot._canonical_bytes(dict(sql=sql,payload=raw_capture))
        with boot._directory(payload_root,no_atime=True) as (_,payload_parents):pass
        def raw_identities():
            private_guard()
            require(raw_root.resolve()==raw_root,payload_code)
            result={'payload/minio-physical':boot._signature(raw_root.lstat())}
            require(stat.S_ISDIR(result['payload/minio-physical'][4]),payload_code)
            def walk_error(error):raise error
            for directory,dirs,files in os.walk(raw_root,followlinks=False,onerror=walk_error):
                private_guard()
                for name in dirs+files:
                    path=Path(directory)/name;info=path.lstat()
                    require(not path.is_symlink() and
                        (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)) and
                        info.st_dev==claim.root.stat().st_dev and
                        (not stat.S_ISREG(info.st_mode) or info.st_nlink==1),payload_code)
                    result[path.relative_to(claim.root).as_posix()]=boot._signature(info)
                    require(len(result)<=500001,'FORMAL_PHYSICAL_TREE_TOO_LARGE')
            private_guard();return result
        try:
            payload_children={p.name for p in payload_root.iterdir() if p.name not in image_names}
            require(set(payload_files)|{'minio-physical'}<=payload_children and
                payload_children<=set(payload_files)|{'minio-physical','native-fence'},payload_code)
            for name in payload_files:
                path=payload_root/name;private_guard()
                if name in ('database.sql.gz', 'database.sql.incremental.raw'):
                    payload_pins[name]=boot._signature(path.lstat())
                    require(payload_pins[name][0]==claim.root.stat().st_dev and
                        payload_pins[name][4]==stat.S_IFREG|0o600 and payload_pins[name][5]==1,payload_code)
                    sha,size=snapshot._hash_object(path,guard=private_guard)
                    expected_database = sql['database'] if name == 'database.sql.gz' else series.database_delta['rawPin']
                    require((sha,size)==('sha256:'+expected_database['sha256'],expected_database['bytes']),payload_code)
                    sha=sha.removeprefix('sha256:')
                else:
                    pair=boot._read_secure(path,0o600,64*1024*1024,no_atime=True)
                    require(pair[1][0]==claim.root.stat().st_dev,payload_code)
                    payload_pairs[name]=pair;payload_pins[name]=pair[1]
                    sha=hashlib.sha256(pair[0]).hexdigest();size=len(pair[0])
                captured_payload_entries['payload/'+name]='file|'+str(size)+'|'+sha
            for name,value,event,key in (
                ('020-sql.json',sql,'split-sql-captured','sqlReceiptSha256'),
                ('040-payload.json',raw_capture,'split-captured','payloadReceiptSha256')):
                receipt=payload_pairs[name][0]
                require(receipt==snapshot._canonical_bytes(value) and
                    split._event(claim,event).get(key)==hashlib.sha256(receipt).hexdigest(),payload_code)
            # Rebind proof bytes to the original SQL references before retaining
            # an archive epoch; a changed proof must never become its baseline.
            private_guard()
            source_data,source_proofs=split.read_source_data(payload_root,claim._plan,
                sql['database']['sha256'],sql.get('sourceDataEvidence'))
            private_guard()
            _,ledger_proofs=split.read_source_ledger(payload_root,claim._plan,sql['database']['sha256'],
                sql.get('sourceMigrationEvidence'),source_data,approved_source)
            private_guard();split._read_rejections(claim,sql);private_guard()
            require(all(payload_pairs[name][0]==value for name,value in
                dict(source_proofs,**ledger_proofs).items()) and
                payload_pairs['010-sql-started.json'][0]==snapshot._canonical_bytes(
                    dict(state='SQL_CAPTURING',sharedScopeSha256=request['sharedScopeSha256'])),payload_code)
            raw_pins=raw_identities()
            verify_series_physical(raw_root,raw_capture.get('physical'),guard=private_guard)
            for name,pin in raw_pins.items():
                if stat.S_ISDIR(pin[4]):captured_payload_entries[name]='directory'
                else:
                    sha,size=snapshot._hash_object(claim.root/name,guard=private_guard)
                    captured_payload_entries[name]='file|'+str(size)+'|'+sha.removeprefix('sha256:')
            require(raw_identities()==raw_pins,payload_code)
        except (OSError,KeyError,TypeError,ValueError) as error:
            raise FormalSnapshotError(payload_code) from error
        payload_entries_raw=snapshot._canonical_bytes(captured_payload_entries)
        def payload_identity():
            private_guard()
            require(snapshot._canonical_bytes(dict(sql=sql,payload=raw_capture))==captured_raw and
                snapshot._canonical_bytes(captured_payload_entries)==payload_entries_raw,payload_code)
            try:
                boot._directory_unchanged(payload_root,payload_parents)
                require({p.name for p in payload_root.iterdir() if p.name not in image_names}==payload_children,payload_code)
                for name,pin in payload_pins.items():
                    require(boot._signature((payload_root/name).lstat())==pin,payload_code)
                require(raw_identities()==raw_pins,payload_code)
            except OSError as error:raise FormalSnapshotError(payload_code) from error
            private_guard()
        payload_identity();current()
        # MySQL and every original writer are still stopped and native thaw
        # has been checked. Export the original IDs before permitting starts.
        original_images=launch_capture.capture_original_application_images(claim,image_path,
            guard=current,timeout=min(7200,int(snapshot.observation_timeout(request['totalSeconds']))))
        original_shared=_strict_json(resume_checks.pins[claim.root/'shared-container-original.json'][2][0])
        require(type(original_shared) is dict and all(type(original_shared.get(role)) is dict and
            type(original_shared[role].get('image')) is str and
            re.fullmatch('sha256:[0-9a-f]{64}',original_shared[role]['image']) for role in ('backend','frontend')),
            'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_REQUIRED')
        require(type(original_images) is dict and set(original_images)==
            {'sha256','bytes','images','sharedScopeSha256','productionEvidence','hostWritersVerified'} and
            type(original_images['sha256']) is str and re.fullmatch('[0-9a-f]{64}',original_images['sha256']) and
            type(original_images['bytes']) is int and original_images['bytes']>0 and
            original_images['images']=={role:original_shared[role]['image'] for role in ('backend','frontend')} and
            original_images['sharedScopeSha256']==request['sharedScopeSha256'] and
            original_images['productionEvidence'] is False and original_images['hostWritersVerified'] is False,
            'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_REQUIRED')
        image_raw=snapshot._canonical_bytes(original_images)
        with boot._directory(image_path.parent,no_atime=True) as (_,image_directory):pass
        image_identity=boot._signature(os.stat(image_path,follow_symlinks=False))
        require(image_identity[0]==claim.root.stat().st_dev and image_identity[2]==0 and
            image_identity[4]==stat.S_IFREG|0o600 and image_identity[5]==1,
            'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_REQUIRED')
        def image_readback():
            current()
            require(snapshot._hash_object(image_path,guard=current)==
                ('sha256:'+original_images['sha256'],original_images['bytes']),
                'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
            current();image_identity_check()
        image_readback()
        split._record(image_path.parent,'050-original-images.json',original_images)
        image_receipt_pair=boot._read_secure(image_path.parent/'050-original-images.json',0o600,16384,no_atime=True)
        require(image_receipt_pair[0]==image_raw and image_receipt_pair[1][0]==claim.root.stat().st_dev,
            'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
        observed,config_identity=config_capture.verify_selected_config_originals(config_root,config_originals,
            claim.root/'original-configs',original_configs,guard=current)
        require(observed==config_reference,'FORMAL_PRODUCTION_A_ORIGINAL_CONFIG_CHANGED')
        current()
        # Complete the exposed manifest while the original capture identities
        # are still checked and before any original service is permitted to start.
        archive_code='FORMAL_PRODUCTION_A_CAPTURE_ARCHIVE_CHANGED'
        archive_entries=dict(captured_payload_entries)
        archive_entries.update(material_entries)
        archive_entries['payload/original-application-images.tar']='file|'+str(original_images['bytes'])+'|'+original_images['sha256']
        archive_entries['payload/050-original-images.json']='file|'+str(len(image_raw))+'|'+hashlib.sha256(image_raw).hexdigest()
        release_path=claim.root/'original-release-binding.json'
        release_pin=resume_checks.pins.get(release_path)
        require(type(release_pin) is tuple and len(release_pin)==3 and
            type(release_pin[2]) is tuple and len(release_pin[2])==2,archive_code)
        release_pair=release_pin[2];config_archive_pins={}
        config_archive_root=claim.root/'original-configs'
        with boot._directory(config_archive_root,no_atime=True) as (_,config_archive_parents):pass
        try:
            require(boot._read_secure(release_path,0o600,16384,no_atime=True)==release_pair,archive_code)
            archive_entries['original-release-binding.json']='file|'+str(len(release_pair[0]))+'|'+hashlib.sha256(release_pair[0]).hexdigest()
            archive_entries['original-configs']='directory'
            for name in ('config-capture-stage.json',*(role+'.bin' for role in config_capture.FILES)):
                path=config_archive_root/name
                pair=boot._read_secure(path,0o600,16777216,no_atime=True)
                config_archive_pins[name]=pair[1]
                if name=='config-capture-stage.json':
                    require(pair[0]==snapshot._canonical_bytes(original_configs) and
                        hashlib.sha256(pair[0]).hexdigest()==config_reference['configReceiptSha256'],archive_code)
                archive_entries['original-configs/'+name]='file|'+str(len(pair[0]))+'|'+hashlib.sha256(pair[0]).hexdigest()
        except (OSError,KeyError,TypeError,ValueError) as error:raise FormalSnapshotError(archive_code) from error
        recovery_inputs_pair = None
        recovery_inputs_path = claim.root/'capture-recovery-inputs.json'
        if series is not None:
            from formal_capture_recovery_inputs import capture_recovery_inputs
            recovery_inputs = capture_recovery_inputs(series.point(source_restored=False),
                source_root=str(claim.root), entries=archive_entries, supplemental=semantic_supplement)
            reference = write_record(recovery_inputs_path,recovery_inputs)
            recovery_inputs_pair = boot._read_secure(recovery_inputs_path,0o600,64*1024*1024,no_atime=True)
            require(recovery_inputs_pair[0] == snapshot._canonical_bytes(recovery_inputs),archive_code)
            archive_entries['capture-recovery-inputs.json']='file|'+str(reference['bytes'])+'|'+reference['sha256']
        archive_entries_raw=snapshot._canonical_bytes(archive_entries)
        material_pins = {name: boot._signature((claim.root/name).lstat()) for name in material_entries}
        # Verify produced bytes once before restoring writers. Exact inode,
        # size, mtime and ctime remain pinned through every archive guard;
        # rehashing all logical object blobs per streamed chunk is unbounded.
        for name in material_entries:
            if material_entries[name] != 'directory':
                marker, size, sha = material_entries[name].split('|')
                require(snapshot._hash_object(claim.root/name, guard=private_guard) ==
                    ('sha256:'+sha, int(size)) and boot._signature((claim.root/name).lstat()) == material_pins[name],
                    archive_code)
        def archive_identity():
            private_guard()
            require(snapshot._canonical_bytes(archive_entries)==archive_entries_raw and
                (shared_receipt is None or snapshot._canonical_bytes(shared_receipt)==shared_receipt_raw),archive_code)
            try:
                if recovery_inputs_pair is not None:
                    require(boot._read_secure(recovery_inputs_path,0o600,64*1024*1024,no_atime=True)==recovery_inputs_pair,
                        archive_code)
                require(boot._read_secure(release_path,0o600,16384,no_atime=True)==release_pair and
                    boot._signature(release_path.lstat())==release_pair[1],archive_code)
                boot._directory_unchanged(config_archive_root,config_archive_parents)
                require({p.name for p in config_archive_root.iterdir()}==set(config_archive_pins),archive_code)
                for name,pin in config_archive_pins.items():
                    require(boot._signature((config_archive_root/name).lstat())==pin,archive_code)
                for name, pin in material_pins.items():
                    require(boot._signature((claim.root/name).lstat()) == pin, archive_code)
            except OSError as error:raise FormalSnapshotError(archive_code) from error
            private_guard()
        config_identity();payload_identity();archive_identity();current()
        transition=ingress.permit_recovery_dependencies(claim,recovery_flows,
            guard=current,thaw_guard=thaw_guard)
        rules_raw=claim._read(claim.root/'ingress-recovery-installed.json')
        rules_sha=hashlib.sha256(rules_raw).hexdigest()
        require(type(transition) is dict and transition.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
            transition.get('rulesSha256')==rules_sha and type(transition.get('tableHandle')) is int and
            transition['tableHandle']>0 and _strict_json(rules_raw)[0]['table']['handle']==transition['tableHandle'] and
            split._event(claim,'ingress-recovery-permitted')==dict(rulesSha256=rules_sha,
                planSha256=hashlib.sha256(flows_raw).hexdigest()),
            'FORMAL_PRODUCTION_A_SHARED_TRANSITION_CHANGED')
        recovery_rules=rules_sha;current()
        restored=split.restore_controlled_shared_originals(claim,mysql,guard=current,
            thaw_guard=thaw_guard,resume_guard=private_guard,container_actions=container_actions)
        require(type(restored) is dict and restored.get('state')==
            'ORIGINAL_SERVICES_RESTORED_PENDING_CALLER_PROOF',
            'FORMAL_PRODUCTION_A_SHARED_RESTORATION_REQUIRED')
        require(any(event['step']=='shared-db-restored' for event in claim.events),
            'FORMAL_PRODUCTION_A_SHARED_RESTORATION_REQUIRED')
        current()
        observed,config_identity=config_capture.verify_selected_config_originals(config_root,config_originals,
            claim.root/'original-configs',original_configs,guard=current)
        require(observed==config_reference,'FORMAL_PRODUCTION_A_ORIGINAL_CONFIG_CHANGED')
        image_readback();current()
        config_reference_raw=snapshot._canonical_bytes(config_reference)
        def original_content_guard():
            # Retain the capture's private/image/config identities, without
            # the earlier stopped-host/caller or held-ingress observer.
            inherited=snapshot.observation_deadline.get()
            limit=deadline if inherited is None else min(deadline,inherited)
            retained_token=snapshot.observation_deadline.set(limit)
            try:
                require(time.monotonic()<limit,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
                thaw_guard();config_identity();payload_identity();archive_identity()
                require(snapshot._canonical_bytes(config_reference)==config_reference_raw,
                    'FORMAL_PRODUCTION_A_ORIGINAL_CONFIG_CHANGED')
                observed,checked=config_capture.verify_selected_config_originals(config_root,
                    config_originals,claim.root/'original-configs',original_configs,guard=private_guard)
                require(observed==config_reference,'FORMAL_PRODUCTION_A_ORIGINAL_CONFIG_CHANGED')
                config_identity();checked();private_guard()
                require(snapshot._hash_object(image_path,guard=private_guard)==
                    ('sha256:'+original_images['sha256'],original_images['bytes']),
                    'FORMAL_PRODUCTION_A_ORIGINAL_IMAGE_CHANGED')
                config_identity();checked();thaw_guard();payload_identity();archive_identity();private_guard()
                require(time.monotonic()<limit,'FORMAL_CAPTURE_DEADLINE_EXCEEDED')
            finally:snapshot.observation_deadline.reset(retained_token)
        original_content_guard()
        receipt=dict(state='A_SHARED_CAPTURED_AND_ORIGINAL_SERVICES_RESTORED_PENDING_REMAINING_OWNER',
            capture=capture,restoration=restored,ingressRulesSha256=recovery_rules,
            originalConfigs=config_reference,originalImages=original_images,
            capturedPayloadEntries=captured_payload_entries,
            capturedArchiveEntries=archive_entries,
            productionEvidence=False,fullRunnerCompleted=False,releaseReady=False,claimReleased=False)
        shared_receipt=receipt;shared_receipt_raw=snapshot._canonical_bytes(receipt);original_content_guard()
        return receipt,original_content_guard,thaw_guard,mysql,deadline
    finally:
        snapshot.observation_deadline.reset(token)

def run_production_a_original_capture_recovery(claim,request,*,approved_source,resume_checks,
        container_actions,source_guard,maintenance_end,recovery_flows,external_transport,
        host_native,health_probe,ingress_native):
    """Consume the shared capture's retained epoch in original recovery.

    Source preparation and original authority consumption belong to the outer
    normal owner. It must retain this claim and archive guard through NAS.
    This component does not acquire/release a claim or declare full success.
    """
    require_native_runtime()
    code='FORMAL_PRODUCTION_A_CAPTURE_RECOVERY_INVALID'
    require(all(value is not None for value in
        (external_transport,host_native,health_probe,ingress_native)),code)
    captured=run_production_a_shared_lifecycle(claim,request,approved_source=approved_source,
        resume_checks=resume_checks,container_actions=container_actions,source_guard=source_guard,
        maintenance_end=maintenance_end,recovery_flows=recovery_flows)
    require(type(captured) is tuple and len(captured)==5,code)
    shared,content_guard,thaw_guard,mysql,deadline=captured
    require(type(shared) is dict and callable(content_guard) and callable(thaw_guard) and mysql is not None,code)
    restored,archive_guard=restore_production_a_original_participants(claim,mysql,shared,
        resume_checks=resume_checks,original_content_guard=content_guard,thaw_guard=thaw_guard,
        external_transport=external_transport,host_native=host_native,health_probe=health_probe,
        ingress_native=ingress_native,maintenance_end=maintenance_end,deadline=deadline)
    return dict(state='A_ORIGINAL_CAPTURE_AND_RECOVERY_COMPLETED_PENDING_NAS',
        sharedCapture=shared,originalParticipants=restored,productionEvidence=False,
        releaseReady=False,fullRunnerCompleted=False,claimReleased=False,nasArchiveVerified=False),archive_guard


def run_approved_original_lifecycle_owner(request_path, expected_request_sha256,*,
        deployment_context_path,expected_deployment_context_sha256):
    """Explicit approved finite owner; never an automatic v12/v7 continuation.

    The outer SHA approves a fixed owner recipe and package, not a mutable v7
    or future operation bytes. The current publisher context has a separate
    explicit path/SHA and must bind the actual gate/operation independently. Only
    this transition's actual readback supplies its dynamic rules digest. The
    independent signed OPEN still applies, behind the missing-full-source gate.
    A single held original FD and claim span every phase; uncertainty is retained
    without automatic recovery, fresh ownership, or replay.
    """
    started=time.monotonic()
    import formal_original_launch as launch
    import formal_original_launch_capture as launch_capture
    import formal_selected_config_capture as config_capture
    import formal_original_open_writer as writer
    import formal_open_authorization as authorization
    import formal_ingress_control as ingress
    import formal_service_health as health
    import formal_split_capture as split
    from formal_source_migration_ledger import approved_source_scope
    require_native_runtime()
    require(type(deployment_context_path) is str and bool(deployment_context_path) and
        type(expected_deployment_context_sha256) is str and
        re.fullmatch('[0-9a-f]{64}',expected_deployment_context_sha256),
        'FORMAL_LIFECYCLE_RELEASE_OPERATION_REQUIRED')
    require(type(expected_request_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_request_sha256),
        'FORMAL_LIFECYCLE_APPROVAL_REQUIRED')
    pins={}
    def pin(path,limit,expected_sha):
        require(type(path) is str and type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}',expected_sha),
            'FORMAL_LIFECYCLE_APPROVAL_REQUIRED')
        selected=_existing_file(path)
        def identity():
            info=selected.stat()
            return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,
                    info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        before=identity();raw=read_private(selected,limit)
        require(identity()==before and hashlib.sha256(raw).hexdigest()==expected_sha,
            'FORMAL_LIFECYCLE_INPUT_CHANGED')
        require(selected not in pins,'FORMAL_LIFECYCLE_INPUT_INVALID')
        pins[selected]=(raw,before,limit)
        return raw
    raw=pin(request_path,16384,expected_request_sha256);owner=_strict_json(raw)
    require(type(owner) is dict and set(owner)=={'schemaVersion','action','totalSeconds','captureRequest',
        'approvedSourceTarget','originalConfigs','releasePackage','launchRequest','recoveryFlows','dependencyAuthor','openApproval'} and
        owner['schemaVersion']=='release-formal-original-lifecycle-owner-input/v4' and
        owner['action']=='capture-and-restore-original-backend' and type(owner['totalSeconds']) is int and
        1<=owner['totalSeconds']<=7200,'FORMAL_LIFECYCLE_INPUT_INVALID')
    for name in ('captureRequest','approvedSourceTarget','originalConfigs'):
        require(type(owner[name]) is dict and set(owner[name])=={'path','sha256'},'FORMAL_LIFECYCLE_INPUT_INVALID')
    cap_raw=pin(owner['captureRequest']['path'],16384,owner['captureRequest']['sha256'])
    cap=_strict_json(cap_raw)
    target_raw=pin(owner['approvedSourceTarget']['path'],65536,owner['approvedSourceTarget']['sha256'])
    config_raw=pin(owner['originalConfigs']['path'],16384,owner['originalConfigs']['sha256'])
    config_originals=_strict_json(config_raw)
    config_root=_strict_json(target_raw)['root']
    require(type(cap) is dict and type(cap.get('claimBinding')) is dict,'FORMAL_LIFECYCLE_INPUT_INVALID')
    source=approved_source_scope(target_raw,owner['approvedSourceTarget']['sha256'],
        snapshot._canonical_bytes(cap['claimBinding']),cap['database'])
    validate_source_request(cap,source)
    context_raw=pin(deployment_context_path,16384,expected_deployment_context_sha256)
    current=_strict_json(context_raw)
    require(type(current) is dict and set(current)=={'schemaVersion','operation','gate',
        'expectedAttemptId','expectedLeaseTokenDigest'} and
        current['schemaVersion']=='release-formal-current-deployment-input/v1' and
        all(type(current[k]) is str and re.fullmatch('[0-9a-f]{64}',current[k])
            for k in ('expectedAttemptId','expectedLeaseTokenDigest')),
        'FORMAL_LIFECYCLE_RELEASE_OPERATION_REQUIRED')
    for name in ('operation','gate'):
        require(type(current[name]) is dict and set(current[name])=={'path','sha256'},
            'FORMAL_LIFECYCLE_RELEASE_OPERATION_REQUIRED')
    operation_raw=pin(current['operation']['path'],1048576,current['operation']['sha256'])
    gate_raw=pin(current['gate']['path'],1048576,current['gate']['sha256'])
    release_binding=_original_release_package_binding(operation_raw,cap['claimBinding'],target_raw,source,
        approved_package=owner['releasePackage'],current_input_raw=context_raw,gate_raw=gate_raw)
    launch_request=owner['launchRequest'];launch_capture._validate(launch_request)
    require(launch_request['schemaVersion']=='release-formal-capture-request/v11' and
        launch_request['claimRoot']==cap['claimRoot'] and
        snapshot._canonical_bytes(launch_request['claimBinding'])==snapshot._canonical_bytes(cap['claimBinding']) and
        launch_request['hostBootId']==cap['filesystemFence']['binding']['bootId'],
        'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
    recipe=owner['dependencyAuthor']
    require(type(recipe) is dict and set(recipe)=={'schemaVersion','ingressRulesSource','requestFields'} and
        recipe['schemaVersion']=='release-formal-dependency-author-input/v1' and
        recipe['ingressRulesSource']=='current-transition-readback','FORMAL_LIFECYCLE_INPUT_INVALID')
    fields=recipe['requestFields']
    names={'schemaVersion','action','claimRoot','claimBinding','mysqlContainerId','mysqlCredentialFile',
        'totalSeconds','sharedScopeSha256','originalHealthSha256'}
    require(type(fields) is dict and set(fields)==names,'FORMAL_LIFECYCLE_INPUT_INVALID')
    validate_dependency_request(dict(fields,ingressRulesSha256=cap['ingressRulesSha256']))
    require(all(snapshot._canonical_bytes(fields[name])==snapshot._canonical_bytes(cap[name])
        for name in names-{'schemaVersion','action','totalSeconds'}),'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
    approved_open=owner['openApproval']
    require(type(approved_open) is dict and set(approved_open)==
        {'path','sha256','trustedKeyPath','trustedKeySha256','binding'},'FORMAL_LIFECYCLE_INPUT_INVALID')
    expected=approved_open['binding'];authorization._binding(expected,'FORMAL_LIFECYCLE_INPUT_INVALID')
    require(expected['role']=='backend' and expected['operationId']==cap['claimBinding']['operationId'] and
        expected['hostBootId']==launch_request['hostBootId'] and
        expected['launchSha256']==launch_request['expectedLaunchSha256'] and
        expected['artifactSha256']==launch_request['jvmBinding']['artifactSha256'],
        'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
    pin(approved_open['path'],8192,approved_open['sha256'])
    # Public key has its existing 0644 contract; private request helper is not
    # appropriate for it. The signed author verifies its native secure identity.
    key_path=_existing_file(approved_open['trustedKeyPath'])
    key_info=key_path.stat()
    require(0<key_info.st_size<=4096,'FORMAL_LIFECYCLE_INPUT_CHANGED')
    with key_path.open('rb') as key_file:key_raw=key_file.read(4097)
    require(0<len(key_raw)<=4096 and hashlib.sha256(key_raw).hexdigest()==approved_open['trustedKeySha256'],
        'FORMAL_LIFECYCLE_INPUT_CHANGED')
    key_identity=(key_info.st_dev,key_info.st_ino,key_info.st_mode,key_info.st_uid,key_info.st_gid,key_info.st_nlink,
        key_info.st_size,key_info.st_mtime_ns,key_info.st_ctime_ns)
    require(key_path not in pins,'FORMAL_LIFECYCLE_INPUT_INVALID')
    pins[key_path]=(key_raw,key_identity,4096)
    pin(cap['mysqlCredentialFile'],16384,hashlib.sha256(read_private(cap['mysqlCredentialFile'],16384)).hexdigest())
    credential=read_credential(cap['mysqlCredentialFile'])
    deadline=started+owner['totalSeconds']
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    token=snapshot.observation_deadline.set(deadline);claim=None
    try:
        def input_identities():
            for path,(_,identity,_) in pins.items():
                info=_existing_file(path).stat()
                require((info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,
                    info.st_size,info.st_mtime_ns,info.st_ctime_ns)==identity,'FORMAL_LIFECYCLE_INPUT_CHANGED')
        def inputs():
            require(time.monotonic()<deadline,'FORMAL_LIFECYCLE_DEADLINE_EXCEEDED')
            for path,(saved,identity,limit) in pins.items():
                if path==key_path:
                    with path.open('rb') as key_file:current=key_file.read(limit+1)
                else:current=read_private(path,limit)
                require(current==saved,'FORMAL_LIFECYCLE_INPUT_CHANGED')
            # Check every identity after the last content read, including same
            # bytes replaced under a previously read path.
            input_identities()
            require(time.monotonic()<deadline,'FORMAL_LIFECYCLE_DEADLINE_EXCEEDED')
        inputs();claim=FormalMaintenanceClaim(cap['claimRoot'],cap['claimBinding'],resume=True)
        control_device=claim.root.stat().st_dev
        storage_identity=None;retained=None;host_checks=None
        def guard():
            nonlocal storage_identity
            inputs();claim.assert_owned()
            require(claim.root.stat().st_dev==control_device and
                all(path.stat().st_dev==control_device for path in pins),
                'FORMAL_LIFECYCLE_CONTROL_DEVICE_CHANGED')
            fresh=verify_approved_source_storage(claim,cap,target_raw)
            require(all(identity[0]!=control_device for identity in fresh.values()),
                'FORMAL_LIFECYCLE_CONTROL_DEVICE_CHANGED')
            if storage_identity is None:storage_identity=fresh
            require(fresh==storage_identity,'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
            if retained is not None:retained.assert_unchanged(deadline=min(deadline,time.monotonic()+60))
            inputs();claim.assert_owned()
            if host_checks is not None:
                host_checks.prepare(guard=inputs,deadline=min(deadline,time.monotonic()+60))
                host_checks.assert_native(deadline=min(deadline,time.monotonic()+60))
        def thaw_guard():
            inputs();claim.assert_owned();result=split._thaw_receipt(claim);inputs();return result
        guard()
        shared_raw=claim._read(claim.root/'shared-container-original.json');shared=_strict_json(shared_raw)
        require(hashlib.sha256(shared_raw).hexdigest()==cap['sharedScopeSha256'] and
            type(shared) is dict and set(shared)==split.ROLES and
            shared['backend']['id']==expected['containerId'] and shared['backend']['state']['Running'] is True,
            'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
        bound=split._event(claim,'boot-backend-bound')
        boot_binding=bound.get('binding') if type(bound) is dict else None
        require(type(boot_binding) is dict and bound.get('hostBootId')==expected['hostBootId'] and
            boot_binding.get('role')=='backend' and boot_binding.get('epoch')==expected['operationId'] and
            boot_binding.get('instanceId')==launch_request['jvmBinding']['instanceId'] and
            all(boot_binding.get(name)==expected[name] for name in
                ('artifactSha256','originalOpenSha256','closedSha256')),
            'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
        # Validate the approved flow against the actual retained ingress plan
        # before capture can issue the first stop, not after capture succeeds.
        plan=_strict_json(claim._read(claim.root/'ingress-plan.json'))
        ingress.render_recovery_policy(hashlib.sha256(claim._plan).hexdigest(),plan,owner['recoveryFlows'])
        _require_original_lifecycle_full_sources(claim)
        release_binding_sha=split._record(claim.root,'original-release-binding.json',release_binding)
        pin(str(claim.root/'original-release-binding.json'),16384,release_binding_sha)
        guard()
        host_checks=_original_lifecycle_pre_capture_stage(claim,deadline=min(deadline,time.monotonic()+60))
        with launch.hold_original_launch('backend',expected['containerId'],shared['backend']['image'],
                expected['hostBootId'],deadline=min(deadline,time.monotonic()+60)) as held:
            original,retained=held
            require(original['inspect']['digests']['launchSha256']==expected['launchSha256'] and
                original['currentJar']['sha256']==expected['artifactSha256'],
                'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
            checks=launch.OriginalLaunchRecoveryChecks(original,retained,launch_request['jvmBinding']['socket'],
                launch_request['jvmBinding']['instanceId'],deadline=min(deadline,time.monotonic()+60))
            guard();_original_lifecycle_pre_capture_stage(claim,
                deadline=min(deadline,time.monotonic()+60),host_checks=host_checks)
            original_config=config_capture.capture_selected_config_originals(config_root,config_originals,
                claim.root/'original-configs',guard=guard)
            def config_readback():
                return config_capture.verify_selected_config_originals(config_root,config_originals,
                    claim.root/'original-configs',original_config,guard=guard)
            config_reference,_=config_readback()
            def native_control_guard():
                inputs();claim.assert_owned()
                require(claim.root.stat().st_dev==control_device and
                    all(path.stat().st_dev==control_device for path in pins),
                    'FORMAL_LIFECYCLE_CONTROL_DEVICE_CHANGED')
                inputs();claim.assert_owned()
            capture_result=run_shared_request(claim,cap,guard,approved_source=source,native_guard=native_control_guard)
            require(capture_result.get('state')=='SHARED_PAYLOAD_CAPTURED_INGRESS_HELD',
                'FORMAL_LIFECYCLE_CAPTURE_REQUIRED')
            thaw_guard();guard()
            original_images=launch_capture.capture_original_application_images(claim,
                claim.root/'payload'/'original-application-images.tar',guard=guard,
                timeout=min(7200,int(snapshot.observation_timeout(owner['totalSeconds']))))
            split._record(claim.root/'payload','050-original-images.json',original_images)
            guard();config_observed,_=config_readback()
            require(config_observed==config_reference,'FORMAL_LIFECYCLE_CONFIG_CHANGED')
            guard();runtime=split._event(claim,'shared-backend-stopped')['runtime']
            checks.stopped(runtime,deadline=min(deadline,time.monotonic()+60));guard();thaw_guard()
            transition=ingress.permit_recovery_dependencies(claim,owner['recoveryFlows'],guard=guard,thaw_guard=thaw_guard)
            guard();thaw_guard()
            rules_raw=claim._read(claim.root/'ingress-recovery-installed.json')
            rules_sha=hashlib.sha256(rules_raw).hexdigest()
            require(type(transition) is dict and transition.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
                transition.get('rulesSha256')==rules_sha and type(transition.get('tableHandle')) is int and
                transition['tableHandle']>0 and _strict_json(rules_raw)[0]['table']['handle']==transition['tableHandle'] and
                split._event(claim,'ingress-recovery-permitted')==dict(rulesSha256=rules_sha,
                    planSha256=hashlib.sha256(snapshot._canonical_bytes(owner['recoveryFlows'])).hexdigest()),
                'FORMAL_LIFECYCLE_TRANSITION_CHANGED')
            # New approved recipe output, never alteration of an approved v7.
            dependency=dict(fields,ingressRulesSha256=rules_sha);validate_dependency_request(dependency)
            dependency_raw=snapshot._canonical_bytes(dependency)
            def dependency_guard():
                guard();require(snapshot._canonical_bytes(dependency)==dependency_raw,
                    'FORMAL_LIFECYCLE_INPUT_CHANGED')
            dependency_result=run_shared_request(claim,dependency,dependency_guard)
            require(dependency_result.get('state')=='DEPENDENCIES_RESTORED_PENDING_OPEN_APPROVAL',
                'FORMAL_LIFECYCLE_DEPENDENCIES_REQUIRED')
            dependency_guard();thaw_guard()
            receipt=health.read_shared_dependency_receipt(claim);receipt_sha=hashlib.sha256(receipt).hexdigest()
            require(split._event(claim,'shared-dependencies-ready')=={'sha256':receipt_sha},
                'FORMAL_LIFECYCLE_RECEIPT_CHANGED')
            external_raw=claim._read(claim.root/'external-callers-original.json')
            external_sha=hashlib.sha256(external_raw).hexdigest()
            require(split._event(claim,'external-caller-scope')=={'scopeSha256':external_sha},
                'FORMAL_LIFECYCLE_SOURCE_BINDING_CHANGED')
            dependency_guard();thaw_guard()
            _require_original_lifecycle_full_sources(claim)
            mysql=PrivateDockerMySql(cap['mysqlContainerId'],credential,timeout=5)
            source_checks=writer.OriginalOpenSourceChecks(claim,expected,rules_sha,external_sha)
            def open_guard():
                dependency_guard();thaw_guard();_require_original_lifecycle_full_sources(claim);source_checks()
            writer.restore_saved_original_open_with_dependency_health(claim,mysql,approved_open['path'],
                approved_open['trustedKeyPath'],approved_open['trustedKeySha256'],expected,
                expected_receipt_sha256=receipt_sha,source_guard=open_guard,timeout=60)
            # No owner journal or CLOSED-only observer between these consumers.
            opened=writer.CompletedOriginalOpenChecks(claim,approved_open['path'],approved_open['trustedKeyPath'],
                approved_open['trustedKeySha256'],expected,deadline=min(deadline,time.monotonic()+300))
            def start_guard():
                dependency_guard();thaw_guard();_require_original_lifecycle_full_sources(claim)
            result=launch_capture.restore_original_backend_once(claim,opened,checks,mysql=mysql,
                expected_receipt_sha256=receipt_sha,expected_rules_sha256=rules_sha,
                expected_external_scope_sha256=external_sha,guard=start_guard,thaw_guard=thaw_guard,timeout=60)
            config_observed,config_identity_check=config_readback()
            require(config_observed==config_reference,'FORMAL_LIFECYCLE_CONFIG_CHANGED')
            # After the last content/claim observer, recheck both groups using
            # their held identities only. Neither terminal check invokes guards
            # or rereads contents; this remains finite integrity evidence.
            inputs();claim.assert_owned();inputs()
            config_identity_check();input_identities()
            require(time.monotonic()<deadline,'FORMAL_LIFECYCLE_DEADLINE_EXCEEDED')
            return dict(result,dependencyRequestSha256=hashlib.sha256(dependency_raw).hexdigest(),
                originalConfigReceiptSha256=config_reference['configReceiptSha256'],
                releaseBindingSha256=release_binding_sha,
                fullRunnerCompleted=False,fullHostFence=False,fullDrain=False,releaseReady=False,
                productionEvidence=False,coldStartConfirmed=False,claimReleased=False)
    except launch.LaunchObservationError:
        raise FormalSnapshotError('FORMAL_LIFECYCLE_ORIGINAL_SOURCE_UNAVAILABLE_RETAINED') from None
    finally:
        try:
            if claim is not None:claim.close()
        finally:snapshot.observation_deadline.reset(token)


def run_production_a_normal_owner(claim,*,inputs,control,guard,deadline):
    from formal_normal_owner import run_owner
    return run_owner(claim,inputs=inputs,control=control,guard=guard,deadline=deadline)

def prepare_production_a_capture_intent(claim,*,prepared,policy_raw,policy_sha256,source_context_raw,
        allocation_sources,guard,deadline):
    from formal_normal_owner import prepare_intent
    return prepare_intent(claim,prepared=prepared,policy_raw=policy_raw,policy_sha256=policy_sha256,
        source_context_raw=source_context_raw,allocation_sources=allocation_sources,guard=guard,deadline=deadline)

def verify_production_a_precapture_admission(claim,*,intent_raw,nas_admission_raw,admission_transport,
        local_admission,guard,deadline):
    from formal_normal_owner import verify_admission
    return verify_admission(claim,intent_raw=intent_raw,nas_admission_raw=nas_admission_raw,
        admission_transport=admission_transport,local_admission=local_admission,guard=guard,deadline=deadline)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    parser.add_argument('--approved-source-target')
    parser.add_argument('--expected-approved-source-target-sha256')
    parser.add_argument('--observe-boot-state', action='store_true',
                        help='Only observe an existing v6 request; no claim ownership or actions')
    parser.add_argument('--observe-original-launch', action='store_true',
                        help='Only observe approved v10 launch or v11 running JVM sources')
    parser.add_argument('--run-original-lifecycle-owner', action='store_true',
                        help='Explicit approved owner recipe; missing full sources refuses before OPEN/start')
    parser.add_argument('--run-normal-owner', action='store_true',
                        help='Explicit pinned native assembly; same control owner through archive close and exit')
    parser.add_argument('--request-fd', type=int, default=0)
    parser.add_argument('--response-fd', type=int, default=1)
    parser.add_argument('--deployment-context',
                        help='Current publisher gate/operation originals input; explicit owner route only')
    parser.add_argument('--expected-deployment-context-sha256',
                        help='Independent SHA of current publisher context; never inferred from recipe')
    parser.add_argument('--bind-host-derived-originals', action='store_true',
                        help='Only seal approved actual host originals before any host entry close')
    args = parser.parse_args(argv)
    if args.run_normal_owner:
        require(not any((args.run_original_lifecycle_owner,args.bind_host_derived_originals,args.observe_boot_state,
            args.observe_original_launch,args.approved_source_target,args.expected_approved_source_target_sha256,
            args.deployment_context,args.expected_deployment_context_sha256)),
            'BACKUP_INTERFACE_SCHEMA_INVALID')
        from formal_normal_owner_entry import main as normal_main
        return normal_main(['--request',args.request,'--expected-request-sha256',args.expected_request_sha256,
            '--request-fd',str(args.request_fd),'--response-fd',str(args.response_fd)])
    claim = None
    try:
        # Before request/credentials/claim acquisition, including standard CLI.
        require_native_runtime()
        require(re.fullmatch('[0-9a-f]{64}', args.expected_request_sha256),
                'FORMAL_CAPTURE_REQUEST_APPROVAL_REQUIRED')
        require(args.run_original_lifecycle_owner or
            (args.deployment_context is None and args.expected_deployment_context_sha256 is None),
            'FORMAL_LIFECYCLE_EXPLICIT_ROUTE_REQUIRED')
        require(not (args.observe_boot_state and args.observe_original_launch),'FORMAL_CAPTURE_REQUEST_INVALID')
        if args.bind_host_derived_originals:
            require(not args.run_original_lifecycle_owner and not args.observe_boot_state and
                not args.observe_original_launch and args.approved_source_target is None and
                args.expected_approved_source_target_sha256 is None,'FORMAL_HOST_DERIVED_EXPLICIT_ROUTE_REQUIRED')
            result=run_approved_host_derived_binding(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        if args.run_original_lifecycle_owner:
            require(not args.observe_boot_state and not args.observe_original_launch and
                args.approved_source_target is None and args.expected_approved_source_target_sha256 is None,
                'FORMAL_LIFECYCLE_EXPLICIT_ROUTE_REQUIRED')
            require(bool(args.deployment_context) and
                type(args.expected_deployment_context_sha256) is str and
                re.fullmatch('[0-9a-f]{64}',args.expected_deployment_context_sha256),
                'FORMAL_LIFECYCLE_RELEASE_OPERATION_REQUIRED')
            result=run_approved_original_lifecycle_owner(args.request,args.expected_request_sha256,
                deployment_context_path=args.deployment_context,
                expected_deployment_context_sha256=args.expected_deployment_context_sha256)
            print(json.dumps(result));return 0
        if args.observe_original_launch:
            # Explicit readonly route before any ordinary stat/read_bytes.
            from formal_original_launch_capture import run_approved_original_launch
            result=run_approved_original_launch(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        if args.observe_boot_state:
            # Route before generic file reads: the observer uses O_NOATIME and
            # accepts only the original v6 approval, never any mutation branch.
            from formal_boot_observation import observe_approved_boot_state
            result=observe_approved_boot_state(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        raw = read_private(args.request, 16384)
        require(hashlib.sha256(raw).hexdigest() == args.expected_request_sha256,
                'FORMAL_CAPTURE_REQUEST_CHANGED')
        request = _strict_json(raw)
        require(not (type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v13'),
            'FORMAL_HOST_DERIVED_EXPLICIT_ROUTE_REQUIRED')
        if not (type(request) is dict and request.get('schemaVersion') in
            ('release-formal-capture-request/v12','release-formal-capture-author-input/v1')):
            require(args.approved_source_target is None and args.expected_approved_source_target_sha256 is None,
                'FORMAL_CAPTURE_SOURCE_ROUTE_REQUIRED')
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-author-input/v1':
            from formal_source_migration_ledger import approved_source_scope
            option_names={'database','sourceRoot','mysqlCredentialFile','totalSeconds','dataLimits','rejectionProbe','filesystemFence'}
            require(set(request)==option_names.union({'schemaVersion','action','claimRoot','claimBinding'}) and
                request['action']=='prepare-source-capture' and type(request['claimRoot']) is str and
                request['claimRoot'] and '\0' not in request['claimRoot'] and
                type(args.approved_source_target) is str and
                type(args.expected_approved_source_target_sha256) is str,
                'FORMAL_CAPTURE_AUTHOR_INPUT_INVALID')
            target_path=_existing_file(args.approved_source_target)
            target_raw=read_approved_source_target(target_path)
            approved_source_scope(target_raw,args.expected_approved_source_target_sha256,
                snapshot._canonical_bytes(request['claimBinding']),request['database'])
            require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
            require(read_approved_source_target(target_path)==target_raw,'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
            claim=FormalMaintenanceClaim(request['claimRoot'],request['claimBinding'],resume=True)
            def author_guard():
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                require(Path(args.request).stat().st_dev==claim.root.stat().st_dev,
                    'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
                require(read_approved_source_target(target_path)==target_raw,'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
                snapshot.observation_timeout(1)
            author_guard()
            result=author_source_capture_request(claim,{k:request[k] for k in option_names},
                target_path,args.expected_approved_source_target_sha256,guard=author_guard)
            author_guard();print(json.dumps(result));return 0
        require(not (type(request) is dict and request.get('schemaVersion') in
            ('release-formal-capture-request/v10','release-formal-capture-request/v11')),
                'FORMAL_CAPTURE_EXPLICIT_LAUNCH_OBSERVER_REQUIRED')
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v9':
            from formal_persisted_work import run_approved_persisted_observation
            result=run_approved_persisted_observation(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v8':
            from formal_live_control import run_approved_live_control
            result=run_approved_live_control(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v6':
            # Explicit root filesystem grant only; never proceed to service actions
            # or equate it with running JVM/operator authorization.
            from formal_boot_state import close_approved_boot_state
            result=close_approved_boot_state(args.request,args.expected_request_sha256)
            print(json.dumps(result));return 0
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v5':
            validate_initialization_request(request)
            from formal_service_health import NativeNetworkProbe
            NativeNetworkProbe()
            def request_guard():
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                require(Path(args.request).stat().st_dev==Path(request['claimRoot']).parent.stat().st_dev,
                    'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
                snapshot.observation_timeout(1)
            token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
            try:
                request_guard();verify_initialization_devices(request)
                claim=FormalMaintenanceClaim(request['claimRoot'],request['claimBinding'],resume=False)
                result=run_initialization_request(claim,request,request_guard)
                request_guard();print(json.dumps(result));return 0
            finally:snapshot.observation_deadline.reset(token)
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v4':
            validate_external_request(request)
            from formal_service_health import NativeNetworkProbe
            NativeNetworkProbe()
            require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
            claim=FormalMaintenanceClaim(request['claimRoot'],request['claimBinding'],resume=True)
            def request_guard():
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                require(Path(args.request).stat().st_dev==claim.root.stat().st_dev,
                        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
            result=run_external_request(claim,request,request_guard)
            request_guard()
            print(json.dumps(result));return 0
        if type(request) is dict and request.get('schemaVersion') in ('release-formal-capture-request/v3','release-formal-capture-request/v7','release-formal-capture-request/v12'):
            approved_source=None
            if request['schemaVersion']=='release-formal-capture-request/v12':
                from formal_source_migration_ledger import approved_source_scope
                require(type(args.approved_source_target) is str and
                    type(args.expected_approved_source_target_sha256) is str,
                    'FORMAL_CAPTURE_SOURCE_APPROVAL_REQUIRED')
                target_path=_existing_file(args.approved_source_target)
                target_raw=read_approved_source_target(target_path)
                approved_source=approved_source_scope(target_raw,args.expected_approved_source_target_sha256,
                    snapshot._canonical_bytes(request['claimBinding']),request['database'])
                validate_source_request(request,approved_source)
            elif request['schemaVersion']=='release-formal-capture-request/v7':validate_dependency_request(request)
            else:
                validate_shared_request(request)
                require(request['action']!='restore-shared-services','FORMAL_CAPTURE_EXPLICIT_OPEN_STOP_REQUIRED')
            from formal_service_health import NativeNetworkProbe
            NativeNetworkProbe()
            require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
            if request['schemaVersion']=='release-formal-capture-request/v12':
                require(read_approved_source_target(target_path)==target_raw,'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
            claim=FormalMaintenanceClaim(request['claimRoot'],request['claimBinding'],resume=True)
            source_storage_identity=None
            def request_guard():
                nonlocal source_storage_identity
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                require(Path(args.request).stat().st_dev==claim.root.stat().st_dev,
                        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
                if request['schemaVersion']=='release-formal-capture-request/v12':
                    require(read_approved_source_target(target_path)==target_raw,'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
                    fresh_storage=verify_approved_source_storage(claim,request,target_raw)
                    if source_storage_identity is None:source_storage_identity=dict(fresh_storage)
                    require(fresh_storage==source_storage_identity,'FORMAL_CAPTURE_APPROVED_STORAGE_CHANGED')
            def native_control_guard():
                # Private request/claim pins only. Source storage observation
                # uses Docker and belongs exclusively before freeze/after thaw.
                claim.assert_owned()
                require(Path(args.request).stat().st_dev==claim.root.stat().st_dev,
                    'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                if request['schemaVersion']=='release-formal-capture-request/v12':
                    require(Path(target_path).stat().st_dev==claim.root.stat().st_dev,
                        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
                    require(read_approved_source_target(target_path)==target_raw,'FORMAL_CAPTURE_APPROVED_SOURCE_CHANGED')
                claim.assert_owned()
            if request['schemaVersion']=='release-formal-capture-request/v12':
                request_guard()
                result=run_shared_request(claim,request,request_guard,approved_source=approved_source,native_guard=native_control_guard)
            else:result=run_shared_request(claim,request,request_guard,native_guard=native_control_guard)
            request_guard()
            print(json.dumps(result));return 0
        if type(request) is dict and request.get('schemaVersion')=='release-formal-capture-request/v2':
            validate_observation_request(request)
            from formal_service_health import NativeNetworkProbe
            NativeNetworkProbe()
            require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
            claim=FormalMaintenanceClaim(request['claimRoot'],request['claimBinding'],resume=True)
            def request_guard():
                require(read_private(args.request,16384)==raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
                require(Path(args.request).stat().st_dev==claim.root.stat().st_dev,
                        'FORMAL_CAPTURE_CONTROL_DEVICE_CHANGED')
            result=observe_shared_request(claim,request,request_guard)
            request_guard()
            print(json.dumps(result));return 0
        require(type(request) is dict and set(request) == {'schemaVersion','claimRoot','claimBinding',
            'database','mysqlContainerId','mysqlCredentialFile','sourceRoot','filesystemFence'} and
            request['schemaVersion'] == 'release-formal-capture-request/v1', 'FORMAL_CAPTURE_REQUEST_INVALID')
        binding = request['claimBinding']; fence = request['filesystemFence']
        require(type(binding) is dict and set(binding) == {'operationId','sourceFingerprint','databaseUuid','minioContainerId'}
                and type(fence) is dict and set(fence) == {'mount','binding','seconds'} and
                type(fence['binding']) is dict and fence['binding'].get('operationId') == binding['operationId'],
                'FORMAL_CAPTURE_FILESYSTEM_OPERATION_CHANGED')
        require(type(fence['seconds']) is int and 1 <= fence['seconds'] <= 300 and type(fence['mount']) is str,
                'FORMAL_CAPTURE_FILESYSTEM_SCOPE_INVALID')
        require(type(request['database']) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',request['database']) and
                type(request['mysqlContainerId']) is str and re.fullmatch('[0-9a-f]{64}',request['mysqlContainerId']),
                'FORMAL_CAPTURE_REQUEST_INVALID')
        credential=read_credential(request['mysqlCredentialFile'])
        require(read_private(args.request,16384) == raw,'FORMAL_CAPTURE_REQUEST_CHANGED')
        claim = FormalMaintenanceClaim(request['claimRoot'],binding,resume=True)
        mysql = PrivateDockerMySql(request['mysqlContainerId'],credential)
        result = capture_claimed_formal_payload(claim,mysql,request['database'],request['sourceRoot'],
                                               filesystem_fence=fence)
        require(result.get('state') == 'CAPTURED_PENDING_FULL_BARRIER_PROOF' and
                result.get('hostWritersVerified') is False,'FORMAL_CAPTURE_ENTRY_RESULT_INVALID')
        print(json.dumps(result));return 0
    except (FormalSnapshotError, WatchdogError) as error:
        code = error.code
        if not (type(code) is str and re.fullmatch('(?:FORMAL|WATCHDOG)_[A-Z0-9_]+',code)):
            code = 'FORMAL_CAPTURE_ENTRY_FAILED'
        print(json.dumps({'state':'FAILED_RETAINED','code':code,'productionEvidence':False}));return 1
    except (OSError,UnicodeError,ValueError,KeyError,TypeError):
        print(json.dumps({'state':'FAILED_RETAINED','code':'FORMAL_CAPTURE_ENTRY_FAILED','productionEvidence':False}));return 1
    finally:
        if claim is not None:claim.close()


if __name__ == '__main__':
    raise SystemExit(main())
