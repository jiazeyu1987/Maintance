"""Lab initialization under the actual W02 claim; no production STARTED input.

Loaded by the independently pinned owner program. Only standard libraries are
imported before the actual W02 authority and held-claim guard are available.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys


def initialize_current_owner(claim, profile, assembly, *, request_fd, response_fd, guard, deadline):
    try:
        return _initialize_current_owner(claim, profile, assembly, request_fd=request_fd,
            response_fd=response_fd, guard=guard, deadline=deadline)
    except BaseException as error:
        # Validation also runs after the acquiring owner has taken the claim.
        # Every uncertainty must retain that exact holder, including errors
        # before the first descriptor or release-binding write.
        error.retainClaim = True
        error.ownerTerminalState = 'TERMINAL_UNKNOWN'
        raise


def _initialize_current_owner(claim, profile, assembly, *, request_fd, response_fd, guard, deadline):
    import formal_snapshot_linux as snapshot
    import formal_boot_state as boot
    from formal_backup_lab import current_authority
    from formal_normal_owner import canonical, require, strict_document
    authority = current_authority()
    fields = {'schemaVersion', 'controlRoot', 'controlIdentity', 'configurationPin', 'sourceConfigPin',
              'peerConfigPin', 'assemblyTemplatePin', 'assemblyPin', 'requestPin', 'labContextPin'}
    require(type(profile) is dict and set(profile) == fields and
            profile['schemaVersion'] == 'RepositoryLabNativeInitialization/v1' and
            sys.platform == 'linux' and os.geteuid() == os.getegid() == 0 and
            type(claim) is snapshot.FormalMaintenanceClaim, 'BACKUP_LAB_INITIALIZATION_INVALID')
    require(profile['labContextPin'] == assembly['labContextPin'] == authority.context_pin and
            profile['requestPin'] == authority.context['operationRequestPin'] and
            profile['controlRoot'] == assembly['controlRoot'], 'BACKUP_LAB_INITIALIZATION_CHANGED')
    service = authority.document(profile['configurationPin'])
    source = authority.document(profile['sourceConfigPin'])
    peer = authority.signed(profile['peerConfigPin'])
    require(service['schemaVersion'] == 'RepositoryNativeServiceConfig/v1' and
            source['schemaVersion'] == 'RepositoryNativeBackupSource/v1' and
            peer['schemaVersion'] == 'RepositoryNativePeerConfig/v2' and
            authority.request['sourceOrTargetRef'] == profile['sourceConfigPin'] and
            source['nativePeerConfigPin'] == profile['peerConfigPin'] and
            peer['assemblyTemplatePin'] == profile['assemblyTemplatePin'] and
            source['bootstrapBinding']['authorityKeyPin'] == authority.key_pin,
            'BACKUP_LAB_INITIALIZATION_CHANGED')
    require(authority.document(profile['assemblyPin']) == assembly and
            assembly['inputReferences']['source_context'] == authority.context['sourceIdentityPin'] and
            assembly['inputReferences']['installed_context'] == authority.context['executionHostPin'] and
            service['repositoryId'] == source['repositoryId'] == peer['repositoryId'] == authority.scope['repositoryId'] and
            assembly['binding']['releaseTag'] == authority.context['rehearsalId'] and
            assembly['binding']['sourceContextSha256'] == authority.context['sourceIdentityPin']['sha256'] and
            assembly['binding']['installedContextSha256'] == authority.context['executionHostPin']['sha256'] and
            assembly['binding']['nasWorkspaceConfigSha256'] == source['workspacePin']['sha256'],
            'BACKUP_LAB_INITIALIZATION_CHANGED')
    capture = authority.document(assembly['captureRequestPin'])
    resume = authority.document(assembly['resumeRequestPin'])
    catalog = authority.document(assembly['catalogBindingPin'])
    plan = (json.dumps(capture['claimBinding'], sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
    require(capture['schemaVersion'] == 'backup-lab-capture-request/v1' and
            capture['labContextPin'] == capture['sourceScope']['labContextPin'] == authority.context_pin and
            capture['claimRoot'] == str(claim.root) and plan == claim._plan and
            resume == dict(schemaVersion='backup-lab-resume-request/v1', labContextPin=authority.context_pin) and
            assembly['binding']['claimBindingSha256'] == hashlib.sha256(claim._plan).hexdigest() and
            catalog['sharedScopeSha256'] == capture['sharedScopeSha256'], 'BACKUP_LAB_INITIALIZATION_CHANGED')
    held = dict(pid=os.getpid(), fd=claim._fd, device=os.fstat(claim._fd).st_dev,
                inode=os.fstat(claim._fd).st_ino, claimRoot=str(claim.root),
                claimBindingSha256=hashlib.sha256(claim._plan).hexdigest())
    def checked():
        guard(); authority.check(); claim.assert_owned()
        require(dict(pid=os.getpid(), fd=claim._fd, device=os.fstat(claim._fd).st_dev,
            inode=os.fstat(claim._fd).st_ino, claimRoot=str(claim.root),
            claimBindingSha256=hashlib.sha256(claim._plan).hexdigest()) == held and
            not any(e['step'] == 'released' for e in claim.events), 'BACKUP_LAB_INITIALIZATION_HOLDER_CHANGED')
    checked()
    control = Path(profile['controlRoot']).stat()
    require(profile['controlIdentity'] == dict(dev=control.st_dev, ino=control.st_ino,
        uid=control.st_uid, mode=control.st_mode) and control.st_uid == 0 and
        stat.S_IMODE(control.st_mode) == 0o700, 'BACKUP_LAB_INITIALIZATION_CONTROL_CHANGED')
    lock = Path(claim.root) / 'ownership.lock'
    require((lock.stat().st_dev, lock.stat().st_ino) == (held['device'], held['inode']),
            'BACKUP_LAB_INITIALIZATION_HOLDER_CHANGED')
    descriptor = dict(schemaVersion='RepositoryLabInitialized/v1', configurationPin=profile['configurationPin'],
        sourceConfigPin=profile['sourceConfigPin'], peerConfigPin=profile['peerConfigPin'],
        assemblyPin=profile['assemblyPin'], requestPin=profile['requestPin'],
        sourceContextPin=authority.context['sourceIdentityPin'],
        installedContextPin=authority.context['executionHostPin'], labContextPin=authority.context_pin, holder=held)
    try:
        release_raw=authority.read(assembly['inputReferences']['release_binding'],16384)
        from formal_backup_lab import validate_original_binding
        release = validate_original_binding(release_raw,authority,claim)
        target = catalog['approvedSourceTargetPin']; authority.read(target)
        require(release['approvedSourceTargetSha256'] == capture['sourceScope']['targetRawSha256'] == target['sha256'] and
            assembly['binding']['originalReleaseBindingSha256'] == hashlib.sha256(release_raw).hexdigest(),
            'BACKUP_LAB_INITIALIZATION_ORIGINAL_CHANGED')
        release_path=Path(claim.root)/'original-release-binding.json'
        fd=os.open(release_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(release_raw);stream.flush();os.fsync(stream.fileno())
        release_pair=boot._read_secure(release_path,0o600,16384,no_atime=True)
        require(release_pair[0]==release_raw,'BACKUP_LAB_INITIALIZATION_ORIGINAL_CHANGED')
        session = Path(peer['sessionRoot']) / hashlib.sha256(authority.request['requestId'].encode()).hexdigest()
        destination = session / 'lab-owner-initialized.json'
        with boot._directory(session, no_atime=True) as (_, chain):
            require(session.stat().st_dev == held['device'], 'BACKUP_LAB_INITIALIZATION_DEVICE_CHANGED')
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(canonical(descriptor));stream.flush();os.fsync(stream.fileno())
        pair = boot._read_secure(destination,0o600,65536,no_atime=True)
        def retained():
            checked();boot._directory_unchanged(session,chain)
            require(boot._read_secure(destination,0o600,65536,no_atime=True)==pair and
                boot._signature(destination.lstat())==pair[1] and
                boot._read_secure(release_path,0o600,16384,no_atime=True)==release_pair and
                boot._signature(release_path.lstat())==release_pair[1], 'BACKUP_LAB_INITIALIZATION_ORIGINAL_CHANGED')
        retained()
        return descriptor, retained
    except BaseException as error:
        error.retainClaim = True
        error.ownerTerminalState = 'TERMINAL_UNKNOWN'
        raise
