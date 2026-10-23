"""Explicit same-owner live CLOSE/OBSERVE; no action replay or full drain claim.

Root owns approval/claim files. The bounded fork drops to the already pinned
application uid before connecting, as required by the existing Java UDS server.
Only the pre-close application-issued token authenticates the JVM operation.
"""
import hashlib
import os
from pathlib import Path
import re
import select
import signal
import socket
import stat
import struct
import time

import formal_boot_state as boot
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError, require

MAX_FRAME = 8192
IDENTITY_FIELDS = {'jvmInstanceId','instanceId','artifactSha256','pid','startTicks',
                   'hostBootId','pidNamespace','mountNamespace','fullIdentity'}
RESPONSE_FIELDS = {'schemaVersion','nonce','identity','operatorId','tenantId','epoch','closedSha256',
    'admissionOpen','outstandingWork','acceptedRootCount','acceptedRootsSha256','completedAcceptedRoots',
    'uncoveredProducers','unresolvedCodeCount','unresolvedCodesSha256','connectionFailures',
    'lastConnectionFailure','codeSourceArtifactBound','durableClosedConfirmed','fullIdentity','fullDrain','releaseReady'}


def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _validate_request(value):
    require(type(value) is dict and set(value)=={'schemaVersion','action','claimRoot','claimBinding',
        'totalSeconds','hostBootId','role','control'} and value['schemaVersion']=='release-formal-capture-request/v8'
        and value['action'] in ('close-live-admission','observe-live-admission') and value['role'] in boot.ROLES
        and type(value['totalSeconds']) is int and 1<=value['totalSeconds']<=60,'FORMAL_LIVE_REQUEST_INVALID')
    boot._absolute(value['claimRoot'])
    control=value['control']
    require(type(control) is dict and set(control)=={'socketPath','socketIdentity','peerPid','uid','gid',
        'identity','operatorId','tenantId','grantFile','grantSha256'},'FORMAL_LIVE_REQUEST_INVALID')
    for name in ('peerPid','operatorId','tenantId'):
        require(type(control[name]) is int and control[name]>0,'FORMAL_LIVE_REQUEST_INVALID')
    for name in ('uid','gid'):
        require(type(control[name]) is int and 0<=control[name]<2**32-1,'FORMAL_LIVE_REQUEST_INVALID')
    for name in ('socketPath','grantFile'):boot._absolute(control[name])
    require(len(os.fsencode(control['socketPath']))<108 and type(control['socketIdentity']) is dict
        and set(control['socketIdentity'])=={'device','inode'} and all(type(n) is int and n>0
        for n in control['socketIdentity'].values()),'FORMAL_LIVE_SOCKET_BINDING_INVALID')
    identity=control['identity']
    require(type(identity) is dict and set(identity)==IDENTITY_FIELDS and identity['fullIdentity'] is False,
        'FORMAL_LIVE_IDENTITY_INVALID')
    require(all(type(identity[k]) is int and identity[k]>0 for k in ('pid','startTicks')) and
        type(identity['jvmInstanceId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',identity['jvmInstanceId'])
        and type(identity['instanceId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',identity['instanceId'])
        and identity['hostBootId']==value['hostBootId'] and type(value['hostBootId']) is str and
        re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',value['hostBootId']), 'FORMAL_LIVE_IDENTITY_INVALID')
    for name in ('pidNamespace','mountNamespace'):
        require(type(identity[name]) is str and re.fullmatch(('pid' if name=='pidNamespace' else 'mnt')+r':\[[0-9]+\]',identity[name]),
            'FORMAL_LIVE_IDENTITY_INVALID')
    for digest in (identity['artifactSha256'],control['grantSha256']):
        require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest),'FORMAL_LIVE_REQUEST_INVALID')


def _peer_guard(control):
    """Independent proc/socket pins, not the server's self-asserted full identity."""
    path=boot._absolute(control['socketPath'])
    # Root/app-owned non-writable ancestors only. The actual app owns a 0700
    # socket directory; private root approvals are deliberately kept elsewhere.
    parents=[]
    for parent in (path.parent,*path.parent.parents):
        info=os.lstat(parent)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0,control['uid']) and not info.st_mode&0o022,
            'FORMAL_LIVE_SOCKET_DIRECTORY_UNTRUSTED')
        parents.append((str(parent),info.st_dev,info.st_ino,info.st_uid,info.st_gid,info.st_mode))
    info=os.lstat(path)
    require(stat.S_ISSOCK(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600 and
        (info.st_uid,info.st_gid)==(control['uid'],control['gid']) and
        {'device':info.st_dev,'inode':info.st_ino}==control['socketIdentity'] and
        stat.S_IMODE(os.lstat(path.parent).st_mode)==0o700,'FORMAL_LIVE_SOCKET_CHANGED')
    pid=control['peerPid'];root=Path('/proc')/str(pid);identity=control['identity']
    def bounded(name,limit):
        with (root/name).open('rb') as stream:raw=stream.read(limit+1)
        require(0<len(raw)<=limit,'FORMAL_LIVE_PROCESS_INVALID')
        return raw.decode('ascii')
    raw=bounded('stat',4096);closing=raw.rfind(')')
    require(closing>0 and int(raw.split(' ',1)[0])==pid and int(raw[closing+2:].split()[19])==identity['startTicks'],
        'FORMAL_LIVE_PEER_CHANGED')
    status=bounded('status',16384)
    fields={line.split(':',1)[0]:line.split(':',1)[1].split() for line in status.splitlines() if ':' in line}
    require(int(fields['NSpid'][-1])==identity['pid'] and all(int(n)==control['uid'] for n in fields['Uid'])
        and all(int(n)==control['gid'] for n in fields['Gid']) and
        os.readlink(root/'ns/pid')==identity['pidNamespace'] and os.readlink(root/'ns/mnt')==identity['mountNamespace']
        and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==identity['hostBootId'], 'FORMAL_LIVE_PEER_CHANGED')
    return tuple(parents)


def _exchange_as_owner(control,payload,deadline):
    """Exactly one connection/send. Reap only this non-spawning owned helper."""
    read_fd,write_fd=os.pipe();pid=None;reaped=False
    try:
        pid=os.fork()
        if pid==0:
            os.close(read_fd)
            try:
                os.setgroups([]);os.setgid(control['gid']);os.setuid(control['uid'])
                require((os.getuid(),os.geteuid(),os.getgid(),os.getegid())==
                    (control['uid'],control['uid'],control['gid'],control['gid']),'FORMAL_LIVE_UID_UNCONFIRMED')
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
                    def within():
                        remaining=deadline-time.monotonic()
                        require(remaining>0,'FORMAL_LIVE_DEADLINE_EXPIRED');connection.settimeout(remaining)
                    within();connection.connect(control['socketPath'])
                    peer=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    require(peer==(control['peerPid'],control['uid'],control['gid']),'FORMAL_LIVE_PEER_CHANGED')
                    within();connection.sendall(struct.pack('!I',len(payload))+payload)
                    def take(count):
                        raw=b''
                        while len(raw)<count:
                            within();chunk=connection.recv(count-len(raw))
                            require(bool(chunk),'FORMAL_LIVE_FRAME_INCOMPLETE');raw+=chunk
                        return raw
                    count=struct.unpack('!I',take(4))[0]
                    require(0<count<=MAX_FRAME,'FORMAL_LIVE_FRAME_INVALID')
                    raw=take(count)
                # Prefix distinguishes a successful response from any child failure.
                data=b'R'+raw
            except BaseException:
                # Never serialize exception text, frame contents or the grant.
                data=b'E'
            try:
                while data:
                    written=os.write(write_fd,data);data=data[written:]
            finally:
                os.close(write_fd)
                os._exit(0)
        os.close(write_fd);write_fd=None;raw=b''
        while True:
            remaining=deadline-time.monotonic()
            require(remaining>0,'FORMAL_LIVE_DEADLINE_EXPIRED')
            require(bool(select.select([read_fd],[],[],remaining)[0]),'FORMAL_LIVE_DEADLINE_EXPIRED')
            chunk=os.read(read_fd,MAX_FRAME+2-len(raw))
            if not chunk:break
            raw+=chunk;require(len(raw)<=MAX_FRAME+1,'FORMAL_LIVE_FRAME_INVALID')
        while True:
            waited,status=os.waitpid(pid,os.WNOHANG)
            if waited==pid:break
            remaining=deadline-time.monotonic()
            require(remaining>0,'FORMAL_LIVE_CHILD_EXIT_UNCONFIRMED')
            select.select([],[],[],min(0.01,remaining))
        reaped=True
        require(os.WIFEXITED(status) and os.WEXITSTATUS(status)==0 and raw.startswith(b'R') and len(raw)>1,
            'FORMAL_LIVE_DELIVERY_UNCONFIRMED')
        return raw[1:]
    finally:
        os.close(read_fd)
        if write_fd is not None:os.close(write_fd)
        if pid and not reaped:
            waited,_=os.waitpid(pid,os.WNOHANG)
            if not waited:
                try:os.kill(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0)


def _response(raw,request,nonce,closed_sha):
    try:value=_strict_json(raw)
    except FormalSnapshotError:raise FormalSnapshotError('FORMAL_LIVE_RESPONSE_INVALID') from None
    control=request['control']
    require(type(value) is dict and set(value)==RESPONSE_FIELDS and value['schemaVersion']=='formal-maintenance-control-response/v1'
        and value['nonce']==nonce and value['identity']==control['identity'] and
        all(type(value['identity'][k]) is type(control['identity'][k]) for k in IDENTITY_FIELDS) and
        value['identity']['fullIdentity'] is False and value['operatorId']==control['operatorId']
        and type(value['operatorId']) is int and value['tenantId']==control['tenantId'] and type(value['tenantId']) is int
        and value['epoch']==request['claimBinding']['operationId'] and value['closedSha256']==closed_sha
        and value['admissionOpen'] is False and value['codeSourceArtifactBound'] is True,
        'FORMAL_LIVE_RESPONSE_INVALID')
    require(all(value[k] is False for k in ('durableClosedConfirmed','fullIdentity','fullDrain','releaseReady')),
        'FORMAL_LIVE_RESPONSE_INVALID')
    require(all(type(value[k]) is int and 0<=value[k]<2**63 for k in ('outstandingWork','acceptedRootCount',
        'completedAcceptedRoots','unresolvedCodeCount','connectionFailures')),'FORMAL_LIVE_RESPONSE_INVALID')
    require(all(type(value[k]) is str and re.fullmatch('[0-9a-f]{64}',value[k]) for k in
        ('acceptedRootsSha256','unresolvedCodesSha256')),'FORMAL_LIVE_RESPONSE_INVALID')
    codes=value['uncoveredProducers']
    require(type(codes) is list and len(codes)<=64 and len(set(codes))==len(codes) and
        all(type(code) is str and re.fullmatch('[a-z][a-z0-9-]{0,127}',code) for code in codes) and
        (value['lastConnectionFailure'] is None or (type(value['lastConnectionFailure']) is str and
        re.fullmatch('MAINTENANCE_CONTROL_[A-Z0-9_]{1,128}',value['lastConnectionFailure']))),'FORMAL_LIVE_RESPONSE_INVALID')
    return value


def run_approved_live_control(request_path,expected_sha256):
    require_native_runtime();require(os.geteuid()==0,'FORMAL_LIVE_ROOT_REQUIRED')
    require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256),'FORMAL_LIVE_APPROVAL_REQUIRED')
    claim=None;token=None
    try:
        raw,approval_identity=boot._read_secure(request_path,0o600,16384)
        require(_sha(raw)==expected_sha256,'FORMAL_LIVE_APPROVAL_CHANGED')
        request=_strict_json(raw);_validate_request(request);control=request['control'];root=boot._absolute(request['claimRoot'])
        token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
        with boot._directory(root) as (_,root_identity):
            require(stat.S_IMODE(root.stat().st_mode)==0o700,'FORMAL_LIVE_CLAIM_UNTRUSTED')
        boot._read_secure(root/'binding.json',0o600,16384)
        lock=os.lstat(root/'ownership.lock')
        require(stat.S_ISREG(lock.st_mode) and lock.st_uid==0 and lock.st_nlink==1 and stat.S_IMODE(lock.st_mode)==0o600,
            'FORMAL_LIVE_CLAIM_UNTRUSTED')
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True)
        prefix='live-'+request['role'];boot_prefix='boot-'+request['role']
        closed=snapshot._claim_event(claim,boot_prefix+'-closed')['details']
        require(set(closed)=={'requestSha256','path','hostBootId','binding','savedOriginalSha256','publishedIdentity'} and
            all(type(v) is int and v>0 for v in closed['publishedIdentity'].values()) and
            set(closed['publishedIdentity'])=={'device','inode'},'FORMAL_LIVE_BOOT_BINDING_CHANGED')
        bound={k:v for k,v in closed.items() if k!='publishedIdentity'}
        require(snapshot._claim_event(claim,boot_prefix+'-bound')['details']==bound and
            snapshot._claim_event(claim,boot_prefix+'-close-intent')['details']==bound,'FORMAL_LIVE_BOOT_BINDING_CHANGED')
        selected=closed['binding']
        boot._validate_request({'schemaVersion':'release-formal-capture-request/v6','action':'close-durable-boot-state',
            'claimRoot':str(root),'claimBinding':request['claimBinding'],'totalSeconds':request['totalSeconds'],
            'hostBootId':request['hostBootId'],'bootBinding':selected})
        require(closed['path']==selected['path'] and closed['hostBootId']==request['hostBootId'] and
            selected['role']==request['role'] and selected['instanceId']==control['identity']['instanceId'] and
            selected['artifactSha256']==control['identity']['artifactSha256'],'FORMAL_LIVE_BOOT_BINDING_CHANGED')
        originals=snapshot._claim_event(claim,'maintenance-originals-bound')['details']['originalFileSha256']
        require(type(originals) is dict and set(originals)==boot.ORIGINALS,'FORMAL_LIVE_ORIGINALS_REQUIRED')
        grant_raw,grant_identity=boot._read_secure(control['grantFile'],0o600,16384)
        require(_sha(grant_raw)==control['grantSha256'],'FORMAL_LIVE_GRANT_CHANGED')
        grant=_strict_json(grant_raw)
        require(type(grant) is dict and set(grant)=={'token','jvmInstanceId','epoch','closedSha256','issuedAt','closeExpiresAt','observeExpiresAt'}
            and type(grant['token']) is str and re.fullmatch('[0-9a-f]{64}',grant['token'])
            and grant['jvmInstanceId']==control['identity']['jvmInstanceId'] and grant['epoch']==selected['epoch']
            and grant['closedSha256']==selected['closedSha256'] and all(type(grant[k]) is str and
            re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z',grant[k])
            for k in ('issuedAt','closeExpiresAt','observeExpiresAt')),'FORMAL_LIVE_GRANT_INVALID')
        initial_parents=_peer_guard(control)
        close=request['action']=='close-live-admission'
        if close:
            allowed={'shared-container-scope','external-caller-scope','shared-health-scope','external-health-scope',
                'maintenance-originals-bound','ingress-scope'} | {
                'boot-'+role+suffix for role in boot.ROLES for suffix in ('-bound','-close-intent','-closed')} | {
                'live-'+role+suffix for role in boot.ROLES for suffix in ('-close-intent','-closed')}
            require(all(e['step'] in allowed for e in claim.events),'FORMAL_LIVE_CLOSE_STAGE_INVALID')
        attempted=[e for e in claim.events if e['step']==prefix+'-close-intent']
        completed=[e for e in claim.events if e['step']==prefix+'-closed']
        require(not attempted if close else len(attempted)==1,'FORMAL_LIVE_CLOSE_ALREADY_ATTEMPTED' if close else 'FORMAL_LIVE_CLOSE_INTENT_REQUIRED')
        if not close:
            require(attempted[0]['details']['control']==control and attempted[0]['details']['closedSha256']==selected['closedSha256'],
                'FORMAL_LIVE_ATTEMPT_BINDING_CHANGED')
        saved=root/(prefix+'-close-response.json')
        original_open_snapshot=boot._read_secure(root/(boot_prefix+'-original-open.json'),0o600,4096)
        require(_sha(original_open_snapshot[0])==closed['savedOriginalSha256']==selected['originalOpenSha256'],
            'FORMAL_LIVE_BOOT_BINDING_CHANGED')
        if close:require(not saved.exists() and not saved.is_symlink(),'FORMAL_LIVE_CLOSE_ALREADY_ATTEMPTED')
        saved_snapshot=None
        if completed:
            saved_snapshot=boot._read_secure(saved,0o600,MAX_FRAME)
            require(len(completed)==1 and completed[0]['details']['responseSha256']==_sha(saved_snapshot[0]),
                'FORMAL_LIVE_COMPLETION_CHANGED')
        def guard():
            snapshot.observation_timeout(1);claim.assert_owned();boot._directory_unchanged(root,root_identity)
            require(_peer_guard(control)==initial_parents,'FORMAL_LIVE_SOCKET_CHANGED')
            # The final root file checks follow all active peer observations.
            approved,current=boot._read_secure(request_path,0o600,16384)
            require((approved,current)==(raw,approval_identity),'FORMAL_LIVE_APPROVAL_CHANGED')
            secret,current=boot._read_secure(control['grantFile'],0o600,16384)
            require((secret,current)==(grant_raw,grant_identity),'FORMAL_LIVE_GRANT_CHANGED')
            current,current_identity=boot._read_secure(selected['path'],0o644,4096)
            require(_sha(current)==selected['closedSha256'] and
                {'device':current_identity[0],'inode':current_identity[1]}==closed['publishedIdentity'], 'FORMAL_LIVE_CLOSED_CHANGED')
            for name,digest in originals.items():
                require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) and
                    _sha(boot._read_secure(root/name,0o600,16384)[0])==digest,'FORMAL_LIVE_ORIGINALS_CHANGED')
            if saved_snapshot is not None:
                require(boot._read_secure(saved,0o600,MAX_FRAME)==saved_snapshot,'FORMAL_LIVE_COMPLETION_CHANGED')
            require(boot._read_secure(root/(boot_prefix+'-original-open.json'),0o600,4096)==original_open_snapshot,
                'FORMAL_LIVE_ORIGINALS_CHANGED')
            claim.assert_owned();snapshot.observation_timeout(1)
        guard()
        nonce=os.urandom(16).hex()
        payload=snapshot._canonical_bytes({'schemaVersion':'formal-maintenance-control/v1','action':'CLOSE' if close else 'OBSERVE',
            'jvmInstanceId':grant['jvmInstanceId'],'epoch':grant['epoch'],'closedSha256':grant['closedSha256'],
            'token':grant['token'],'nonce':nonce})
        require(len(payload)<=MAX_FRAME,'FORMAL_LIVE_FRAME_INVALID')
        guard()
        if close:
            claim.record(prefix+'-close-intent',{'requestSha256':expected_sha256,'control':control,
                'closedSha256':selected['closedSha256'],'nonce':nonce})
        guard()
        response_raw=_exchange_as_owner(control,payload,snapshot.observation_deadline.get())
        require(grant['token'].encode('ascii') not in response_raw,'FORMAL_LIVE_RESPONSE_SECRET_REFUSED')
        value=_response(response_raw,request,nonce,selected['closedSha256'])
        guard()
        if close:
            claim._write(saved,response_raw)
            saved_snapshot=boot._read_secure(saved,0o600,MAX_FRAME)
            require(saved_snapshot[0]==response_raw,'FORMAL_LIVE_RESPONSE_CHANGED');guard()
            claim.record(prefix+'-closed',{'requestSha256':expected_sha256,'responseSha256':_sha(response_raw),
                'jvmInstanceId':control['identity']['jvmInstanceId'],'closedSha256':selected['closedSha256']})
            guard()
        return {'state':'LIVE_ADMISSION_CLOSED_PENDING_FULL_DRAIN' if close else 'LIVE_ADMISSION_OBSERVED_ONLY',
            'role':request['role'],'epoch':selected['epoch'],'responseSha256':_sha(response_raw),'observation':value,
            'liveAdmissionClosed':True,'durableClosedConfirmed':True,'closeCompletionConfirmed':close or bool(completed),
            'fullIdentity':False,'fullDrain':False,'productionEvidence':False,'releaseReady':False,'claimReleased':False}
    except OSError:raise FormalSnapshotError('FORMAL_LIVE_IO_FAILED_RETAINED') from None
    except (ValueError,KeyError,TypeError,IndexError,UnicodeError):
        raise FormalSnapshotError('FORMAL_LIVE_INPUT_OR_RESPONSE_INVALID') from None
    finally:
        if claim is not None:claim.close()
        if token is not None:snapshot.observation_deadline.reset(token)
