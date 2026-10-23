"""Explicit native-root durable CLOSED transition, not live application authorization.

No OPEN generator, automatic recovery, service actions or action replay. A root
approval file and claim authorize only this finite filesystem operation. JVM
operator permission, loaded artifact identity and actual drain remain separate.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import time

import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError, require

ROLES = {'backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal'}
ORIGINALS = {'shared-container-original.json','external-callers-original.json',
             'shared-health-original.json','external-callers-health-original.json'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _absolute(path):
    require(type(path) is str and path.startswith('/') and '\0' not in path and
            str(Path(path)) == path and all(p not in ('.','..') for p in path.split('/')[1:]),
            'FORMAL_BOOT_PATH_INVALID')
    return Path(path)


@contextmanager
def _directory(path, *, no_atime=False):
    """Anchor every ancestor by descriptor, not a final-component symlink check."""
    selected=_absolute(str(path)); descriptors=[]; identities=[]
    try:
        flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
        if no_atime:flags|=os.O_NOATIME
        fd=os.open('/',flags)
        descriptors.append(fd)
        for part in ('', *selected.parts[1:]):
            if part:
                fd=os.open(part,flags,dir_fd=descriptors[-1]); descriptors.append(fd)
            info=os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not (info.st_mode & 0o022),
                    'FORMAL_BOOT_DIRECTORY_UNTRUSTED')
            identities.append((info.st_dev,info.st_ino,info.st_uid,info.st_gid,info.st_mode))
        yield descriptors[-1], tuple(identities)
    finally:
        for fd in reversed(descriptors):os.close(fd)


def _directory_unchanged(path, identity):
    with _directory(path) as (_, current):
        require(current==identity,'FORMAL_BOOT_DIRECTORY_CHANGED')


def _read_at(directory, name, mode, limit, *, no_atime=False, allow_empty=False):
    # Inspect descriptor type before any read; a FIFO must not hold the claim
    # indefinitely inside blocking open, before deadline guards can run.
    flags=os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC
    if no_atime:flags|=os.O_NOATIME
    fd=os.open(name,flags,dir_fd=directory)
    try:
        before=os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid==0 and before.st_nlink==1 and
                stat.S_IMODE(before.st_mode)==mode and (0 if allow_empty else 1)<=before.st_size<=limit,
                'FORMAL_BOOT_FILE_UNTRUSTED')
        chunks=[]; remaining=limit+1
        while remaining:
            data=os.read(fd,remaining)
            if not data:break
            chunks.append(data); remaining-=len(data)
        raw=b''.join(chunks)
        require(len(raw)==before.st_size and _signature(os.fstat(fd))==_signature(before) and
                _signature(os.stat(name,dir_fd=directory,follow_symlinks=False))==_signature(before),
                'FORMAL_BOOT_FILE_CHANGED')
        return raw, _signature(before)
    finally:os.close(fd)


def _read_secure(path, mode, limit, *, no_atime=False):
    selected=_absolute(str(path))
    with _directory(selected.parent, no_atime=no_atime) as (fd, identity):
        raw, fingerprint=_read_at(fd,selected.name,mode,limit,no_atime=no_atime)
        _directory_unchanged(selected.parent,identity)
        return raw, fingerprint


def _validate_request(value):
    require(type(value) is dict and set(value)=={'schemaVersion','action','claimRoot','claimBinding',
                'totalSeconds','hostBootId','bootBinding'} and
            value['schemaVersion']=='release-formal-capture-request/v6' and
            value['action']=='close-durable-boot-state' and type(value['totalSeconds']) is int and
            1<=value['totalSeconds']<=300,'FORMAL_BOOT_REQUEST_INVALID')
    _absolute(value['claimRoot'])
    binding=value['claimBinding']; boot=value['bootBinding']
    require(type(binding) is dict and set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'} and
            type(binding['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['operationId']) and
            all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k]) for k in ('sourceFingerprint','minioContainerId')) and
            type(binding['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['databaseUuid']),
            'FORMAL_BOOT_REQUEST_INVALID')
    require(type(boot) is dict and set(boot)=={'role','path','instanceId','artifactSha256','originalOpenSha256',
                'closedSha256','epoch','expectedIdentity'} and type(boot['role']) is str and boot['role'] in ROLES and
            type(boot['instanceId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',boot['instanceId']) and
            boot['epoch']==binding['operationId'] and all(type(boot[k]) is str and re.fullmatch('[0-9a-f]{64}',boot[k])
                for k in ('artifactSha256','originalOpenSha256','closedSha256')) and
            type(boot['expectedIdentity']) is dict and set(boot['expectedIdentity'])=={'device','inode'} and
            all(type(v) is int and v>0 for v in boot['expectedIdentity'].values()),'FORMAL_BOOT_REQUEST_INVALID')
    selected=_absolute(boot['path'])
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',selected.name), 'FORMAL_BOOT_PATH_INVALID')
    require(type(value['hostBootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',value['hostBootId']),
            'FORMAL_BOOT_REQUEST_INVALID')


def _closed_bytes(raw, binding):
    try:value=_strict_json(raw)
    except FormalSnapshotError:raise FormalSnapshotError('FORMAL_BOOT_RECORD_INVALID') from None
    require(type(value) is dict and set(value)=={'schemaVersion','instanceId','artifactSha256','state','epoch','phase'} and
            all(type(v) is str for v in value.values()) and value['schemaVersion']=='formal-maintenance-boot/v1' and
            value['instanceId']==binding['instanceId'] and value['artifactSha256']==binding['artifactSha256'] and
            value['state']=='OPEN' and value['epoch']=='' and value['phase']=='NORMAL','FORMAL_BOOT_RECORD_INVALID')
    return snapshot._canonical_bytes(dict(value,state='CLOSED',epoch=binding['epoch']))


def close_approved_boot_state(request_path, expected_sha256):
    """Finite irreversible attempt: partial state requires explicit reconciliation."""
    require_native_runtime()
    require(os.geteuid()==0,'FORMAL_BOOT_ROOT_REQUIRED')
    require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256),
            'FORMAL_BOOT_APPROVAL_REQUIRED')
    claim=None; token=None
    try:
        raw, approval_identity=_read_secure(request_path,0o600,16384)
        require(_sha(raw)==expected_sha256,'FORMAL_BOOT_APPROVAL_CHANGED')
        request=_strict_json(raw); _validate_request(request)
        selected=request['bootBinding']; target=_absolute(selected['path']); root=_absolute(request['claimRoot'])
        token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
        with _directory(root) as (_, claim_identity):
            require(stat.S_IMODE(root.stat().st_mode)==0o700,'FORMAL_BOOT_DIRECTORY_UNTRUSTED')
        # Reject untrusted pre-existing lock/binding files before claim acquisition.
        _read_secure(root/'binding.json',0o600,16384)
        lock_info=os.lstat(root/'ownership.lock')
        require(stat.S_ISREG(lock_info.st_mode) and lock_info.st_uid==0 and lock_info.st_nlink==1 and
                stat.S_IMODE(lock_info.st_mode)==0o600,'FORMAL_BOOT_FILE_UNTRUSTED')
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True)
        prefix='boot-'+selected['role']
        require(not any(e['step'].startswith(prefix+'-') for e in claim.events),
                'FORMAL_BOOT_TRANSITION_ALREADY_ATTEMPTED')
        originals=[e for e in claim.events if e['step']=='maintenance-originals-bound']
        require(len(originals)==1 and set(originals[0]['details'])=={'originalFileSha256'} and
                type(originals[0]['details']['originalFileSha256']) is dict and
                set(originals[0]['details']['originalFileSha256'])==ORIGINALS,
                'FORMAL_BOOT_ORIGINALS_REQUIRED')
        originals=originals[0]['details']['originalFileSha256']
        def guard():
            snapshot.observation_timeout(1); claim.assert_owned()
            _directory_unchanged(root,claim_identity)
            approved,current=_read_secure(request_path,0o600,16384)
            require(approved==raw and current==approval_identity,'FORMAL_BOOT_APPROVAL_CHANGED')
            require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==request['hostBootId'],
                    'FORMAL_BOOT_HOST_CHANGED')
            for name,expected in originals.items():
                require(type(expected) is str and re.fullmatch('[0-9a-f]{64}',expected) and
                        _sha(_read_secure(root/name,0o600,16384)[0])==expected,
                        'FORMAL_BOOT_ORIGINALS_CHANGED')
        guard()
        with _directory(target.parent) as (directory, directory_identity):
            lock_name=target.name+'.writer.lock'
            # Bound names before retaining original bytes or irreversible intent.
            pending='.boot-close-'+expected_sha256+'.pending'
            name_max=os.fpathconf(directory,'PC_NAME_MAX')
            require(type(name_max) is int and name_max>0 and
                    all(len(name.encode('utf-8'))<=name_max for name in (lock_name,pending)),
                    'FORMAL_BOOT_NAME_LIMIT_INVALID')
            fd=os.open(lock_name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory)
            try:
                info=os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and
                        stat.S_IMODE(info.st_mode)==0o600,'FORMAL_BOOT_LOCK_UNTRUSTED')
                try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:raise FormalSnapshotError('FORMAL_BOOT_TARGET_BUSY') from None
                os.fsync(fd); os.fsync(directory)
                lock_identity=_signature(os.fstat(fd))
                def target_guard():
                    guard(); _directory_unchanged(target.parent,directory_identity)
                    require(_signature(os.fstat(fd))==lock_identity and
                            _signature(os.stat(lock_name,dir_fd=directory,follow_symlinks=False))==lock_identity,
                            'FORMAL_BOOT_LOCK_CHANGED')
                target_guard()
                original, old_identity=_read_at(directory,target.name,0o644,4096)
                require({'device':old_identity[0],'inode':old_identity[1]}==selected['expectedIdentity'] and
                        _sha(original)==selected['originalOpenSha256'],'FORMAL_BOOT_BINDING_CHANGED')
                closed=_closed_bytes(original,selected)
                require(_sha(closed)==selected['closedSha256'],'FORMAL_BOOT_BINDING_CHANGED')
                saved=root/(prefix+'-original-open.json')
                require(not saved.exists() and not saved.is_symlink(),'FORMAL_BOOT_TRANSITION_ALREADY_ATTEMPTED')
                target_guard(); claim._write(saved,original)
                details={'requestSha256':expected_sha256,'path':str(target),'hostBootId':request['hostBootId'],
                         'binding':selected,'savedOriginalSha256':_sha(original)}
                target_guard(); claim.record(prefix+'-bound',details)
                target_guard(); claim.record(prefix+'-close-intent',details)
                temporary=os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644,dir_fd=directory)
                try:
                    os.fchmod(temporary,0o644)
                    with os.fdopen(temporary,'wb',closefd=False) as output:
                        output.write(closed); output.flush(); os.fsync(temporary)
                finally:os.close(temporary)
                target_guard()
                current, identity=_read_at(directory,target.name,0o644,4096)
                require(current==original and identity==old_identity,'FORMAL_BOOT_BINDING_CHANGED')
                os.replace(pending,target.name,src_dir_fd=directory,dst_dir_fd=directory)
                os.fsync(directory); target_guard()
                published, new_identity=_read_at(directory,target.name,0o644,4096)
                require(published==closed and new_identity[:2]!=old_identity[:2],'FORMAL_BOOT_PUBLICATION_UNCONFIRMED')
                def published_guard():
                    target_guard()
                    current, identity=_read_at(directory,target.name,0o644,4096)
                    require(current==closed and identity==new_identity,'FORMAL_BOOT_PUBLICATION_UNCONFIRMED')
                published_guard()
                claim.record(prefix+'-closed',dict(details,publishedIdentity={'device':new_identity[0],'inode':new_identity[1]}))
                published_guard()
                return {'state':'DURABLE_CLOSED_PENDING_JVM_CLOSE','durableClosedConfirmed':True,
                        'epoch':selected['epoch'],'role':selected['role'],'requestSha256':expected_sha256,
                        'originalOpenSha256':selected['originalOpenSha256'],'closedSha256':selected['closedSha256'],
                        'liveAdmissionClosed':False,'operatorPermissionVerified':False,'applicationIdentityVerified':False,
                        'productionEvidence':False,'releaseReady':False,'serviceActionsPerformed':False,'claimReleased':False}
            finally:os.close(fd)
    except OSError:raise FormalSnapshotError('FORMAL_BOOT_IO_FAILED_RETAINED') from None
    finally:
        if claim is not None:claim.close()
        if token is not None:snapshot.observation_deadline.reset(token)
