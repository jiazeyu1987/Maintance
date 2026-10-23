"""Bound protocol health for shared-service recovery, not business acceptance.

HTTP/Redis observations use the container's pinned network namespace. No host
business port is opened, no redirect/proxy is followed, and no image-specific
curl/wget fallback is selected. Requires the approved native Python >=3.12 on
the Docker host; failures leave existing ingress and recovery evidence intact.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import time

import formal_snapshot_linux as snapshot
import formal_split_capture as split

HTTP_ROLES={'backend':(48081,'/actuator/health'), 'minio':(9000,'/minio/health/live'),
    'onlyoffice':(80,'/healthcheck'), 'frontend':(80,'/'), 'showroom':(80,'/')}
MAX_BODY=65536


def _require(ok,suffix):snapshot.require(ok,'FORMAL_HEALTH_'+suffix)


def health_deadline(seconds):
    _require(type(seconds) in (int,float) and 0<seconds<=300,'DEADLINE_INVALID')
    deadline=time.monotonic()+seconds
    outer=snapshot.observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    _within(deadline)
    return deadline


def _within(deadline):
    _require(time.monotonic()<deadline,'DEADLINE_EXCEEDED')


def _strict_object(raw):
    def pairs(entries):
        value={}
        for key,item in entries:
            if key in value:raise ValueError('duplicate')
            value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))


def validate_http(role,status,body):
    _require(role in HTTP_ROLES and type(status) is int and status==200 and
        type(body) is bytes and len(body)<=MAX_BODY,'RESPONSE_INVALID')
    if role=='backend':
        try: value=_strict_object(body)
        except (ValueError,UnicodeError):
            raise snapshot.FormalSnapshotError('FORMAL_HEALTH_RESPONSE_INVALID') from None
        _require(type(value) is dict and value.get('status')=='UP','RESPONSE_INVALID')
    elif role=='onlyoffice':_require(body.strip()==b'true','RESPONSE_INVALID')
    elif role in ('frontend','showroom'):
        # The pre-stop exact bytes are also compared on recovery. A merely
        # syntactic HTML page is never alone a successful restoration proof.
        _require(b'<html' in body.lower() and b'</html>' in body.lower(),'RESPONSE_INVALID')
    return {'httpStatus':status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}


# Run in a fresh isolated native interpreter. Only this subprocess enters the
# namespace; the parent continues guarding the host and maintenance journal.
_WORKER=r'''
import base64,http.client,json,os,socket,sys,time
fd=int(sys.argv[1]);spec=json.loads(sys.argv[2]);limit=65536
assert hasattr(os,'setns')
os.setns(fd,os.CLONE_NEWNET)
deadline=time.monotonic()+spec['seconds']
def remaining():
 value=deadline-time.monotonic()
 if value<=0:raise TimeoutError()
 return value
try:
 if spec['protocol']=='http':
  connection=http.client.HTTPConnection('127.0.0.1',spec['port'],timeout=remaining())
  connection.request('GET',spec['path'],headers={'Connection':'close','Accept-Encoding':'identity'})
  response=connection.getresponse();body=bytearray()
  lengths=response.headers.get_all('Content-Length',[])
  transfers=response.headers.get_all('Transfer-Encoding',[])
  if len(lengths)>1 or (lengths and (not lengths[0].isascii() or not lengths[0].isdigit())):
   raise ValueError('content length')
  if transfers and (transfers!=['chunked'] or lengths):raise ValueError('transfer encoding')
  if lengths and int(lengths[0])>limit:raise ValueError('response size')
  while True:
   if response.fp is not None and connection.sock is not None:connection.sock.settimeout(remaining())
   chunk=response.read(min(4096,limit+1-len(body)))
   body.extend(chunk)
   if len(body)>limit:raise ValueError('response size')
   if not chunk:break
  if response.length not in (None,0):raise ValueError('incomplete response')
  if lengths and len(body)!=int(lengths[0]):raise ValueError('incomplete response')
  remaining()
  result={'httpStatus':response.status,'body':base64.b64encode(body).decode('ascii')}
  connection.close()
 elif spec['protocol']=='redis':
  connection=socket.create_connection(('127.0.0.1',6379),timeout=remaining())
  connection.sendall(b'*1\r\n$4\r\nPING\r\n')
  body=bytearray()
  while not body.endswith(b'\r\n') and len(body)<256:
   connection.settimeout(remaining());part=connection.recv(256-len(body))
   if not part:break
   body.extend(part)
  connection.close();result={'pong':body==b'+PONG\r\n'}
 else:raise ValueError('protocol')
 print(json.dumps({'state':'OBSERVED','result':result}))
except (ConnectionRefusedError,TimeoutError,socket.timeout):
 print(json.dumps({'state':'NOT_READY'}))
except Exception:
 print(json.dumps({'state':'FAILED'}));sys.exit(1)
'''


class NativeNetworkProbe:
    def __init__(self):
        _require(os.name=='posix' and sys.version_info>=(3,12) and hasattr(os,'setns'),'NATIVE_RUNTIME_REQUIRED')

    def _pid(self,identity):
        _require(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity),'IDENTITY_INVALID')
        try:
            result=subprocess.run(['docker','inspect','--format','{{.State.Pid}}',identity],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=snapshot.observation_timeout(10))
        except (OSError,subprocess.TimeoutExpired):
            raise snapshot.FormalSnapshotError('FORMAL_HEALTH_RUNTIME_OBSERVATION_FAILED') from None
        _require(result.returncode==0 and not result.stderr and re.fullmatch(rb'[1-9][0-9]*\n',result.stdout),
                 'RUNTIME_OBSERVATION_FAILED')
        return int(result.stdout)

    def observe(self,role,record,seconds):
        deadline=health_deadline(seconds)
        token=snapshot.observation_deadline.set(deadline)
        try:return self._observe(role,record,seconds,deadline)
        finally:snapshot.observation_deadline.reset(token)

    def _observe(self,role,record,seconds,deadline):
        _require(role in HTTP_ROLES or role=='redis','ROLE_INVALID')
        _require(snapshot.inspect_formal_container(record['id'])==record and record['state']['Running'],
                 'RUNTIME_CHANGED')
        pid=self._pid(record['id']);path=Path('/proc')/str(pid)/'ns/net'
        descriptor=None;stage='NAMESPACE_OPEN'
        try:
            descriptor=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
            stage='NAMESPACE_IDENTITY'
            namespace=os.fstat(descriptor).st_ino
            _require(namespace!=os.stat('/proc/self/ns/net').st_ino,'HOST_NETWORK_REFUSED')
            _require(self._pid(record['id'])==pid and snapshot.inspect_formal_container(record['id'])==record
                and path.stat().st_ino==namespace,'RUNTIME_CHANGED')
            spec={'protocol':'redis' if role=='redis' else 'http',
                  'seconds':min(deadline-time.monotonic(),snapshot.observation_timeout(seconds))}
            _require(spec['seconds']>0,'DEADLINE_EXCEEDED')
            if role in HTTP_ROLES:spec.update(zip(('port','path'),HTTP_ROLES[role]))
            stage='WORKER'
            result=subprocess.run([sys.executable,'-I','-c',_WORKER,str(descriptor),json.dumps(spec)],
                pass_fds=(descriptor,),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=snapshot.observation_timeout(spec['seconds']),check=False)
            _require(result.returncode==0 and not result.stderr and len(result.stdout)<=MAX_BODY*2,'PROBE_FAILED')
            value=_strict_object(result.stdout)
            _require(self._pid(record['id'])==pid and
                snapshot.inspect_formal_container(record['id'])==record and path.stat().st_ino==namespace,
                'RUNTIME_CHANGED')
            _within(deadline)
            _require(value.get('state') in ('NOT_READY','OBSERVED'),'PROBE_FAILED')
            if value['state']=='NOT_READY':return None
            observed=value['result']
            if role=='redis':
                _require(observed=={'pong':True},'REDIS_RESPONSE_INVALID')
                proof={'protocol':'redis','response':'PONG','authentication':'none'}
            else:
                body=base64.b64decode(observed['body'],validate=True)
                if observed['httpStatus'] in (502,503):return None
                proof=validate_http(role,observed['httpStatus'],body)
            _within(deadline)
            return {'networkNamespaceInode':namespace,'pid':pid,**proof}
        except OSError as error:
            raise snapshot.FormalSnapshotError('FORMAL_HEALTH_'+stage+'_OS_ERROR_'+str(error.errno)) from None
        except (subprocess.TimeoutExpired,ValueError,KeyError,TypeError):
            raise snapshot.FormalSnapshotError('FORMAL_HEALTH_PROBE_FAILED') from None
        finally:
            if descriptor is not None:os.close(descriptor)


def _event(claim,name):
    return next((event['details'] for event in claim.events if event['step']==name),None)


def _await_role(claim,role,record,probe,guard,deadline):
    if record['state']['Running'] is False:
        _require(snapshot.inspect_formal_container(record['id'])==record,'RUNTIME_CHANGED')
        return {'state':'ORIGINALLY_STOPPED','healthObserved':False}
    while True:
        claim.assert_owned();guard();_within(deadline)
        seconds=min(8,deadline-time.monotonic())
        _require(seconds>0,'DEADLINE_EXCEEDED')
        proof=probe.observe(role,record,seconds)
        claim.assert_owned();guard();_within(deadline)
        if proof is not None:return {'state':'HEALTHY','proof':proof}
        _require(time.monotonic()+0.2<deadline,'DEADLINE_EXCEEDED')
        time.sleep(0.2)


def _mysql_proof(mysql,record,flags):
    _require(record['id']==mysql.container and record['state']['Running'],'MYSQL_RUNTIME_CHANGED')
    _require(snapshot._database_flags(mysql,flags['serverUuid'])==flags,'MYSQL_FLAGS_CHANGED')
    return {'state':'HEALTHY','proof':{'protocol':'mysql','flags':flags}}


def _original_health(claim):
    claim.assert_owned()
    event=_event(claim,'shared-health-scope');_require(event is not None,'SCOPE_REQUIRED')
    raw=claim._read(claim.root/'shared-health-original.json')
    _require(hashlib.sha256(raw).hexdigest()==event['sha256'],'SCOPE_CHANGED')
    value=_strict_object(raw)
    _require(value['claimSha256']==hashlib.sha256(claim._plan).hexdigest() and
        value['sharedScopeSha256']==split._shared_role(claim,'mysql')[2],'SCOPE_CHANGED')
    return value


def restore_shared_services_with_health(claim,mysql,*,guard,thaw_guard,timeout=120,probe=None):
    """One explicit sequential recovery attempt, never replaying uncertain actions.

    Restore the original services only; callers and ingress remain held. The
    caller must keep actual ingress/host exclusion in guard, not a constant.
    """
    _require(callable(guard) and callable(thaw_guard),'PLAN_INVALID')
    probe=NativeNetworkProbe() if probe is None else probe
    deadline=health_deadline(timeout);token=snapshot.observation_deadline.set(deadline)
    try:
        thaw_guard();claim.assert_owned();_within(deadline);guard();_within(deadline)
        original=_original_health(claim)
        split.begin_shared_recovery(claim,guard=guard,thaw_guard=thaw_guard)
        split.restore_shared_container(claim,'mysql',guard=guard,thaw_guard=thaw_guard)
        _,record,_=split._shared_role(claim,'mysql')
        _require(record['id']==mysql.container and record['state']['Running'],'MYSQL_RUNTIME_CHANGED')
        while True:
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            _require(snapshot.inspect_formal_container(mysql.container)==record,'MYSQL_RUNTIME_CHANGED')
            ready=mysql.ready()
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            _require(snapshot.inspect_formal_container(mysql.container)==record,'MYSQL_RUNTIME_CHANGED')
            if ready:break
            _require(time.monotonic()+.2<deadline,'DEADLINE_EXCEEDED');time.sleep(.2)
        split.restore_shared_database_flags(claim,mysql,guard=guard,thaw_guard=thaw_guard)
        _mysql_proof(mysql,record,original['health']['mysql']['proof']['flags'])
        for role in split.RESTORE_ORDER[1:]:
            guard();thaw_guard();_within(deadline)
            split.restore_shared_container(claim,role,guard=guard,thaw_guard=thaw_guard)
            _,record,_=split._shared_role(claim,role)
            observed=_await_role(claim,role,record,probe,guard,deadline)
            _require(observed['state']==original['health'][role]['state'],'ORIGINAL_STATE_CHANGED')
            if role in ('frontend','showroom') and observed['state']=='HEALTHY':
                _require(observed['proof']['sha256']==original['health'][role]['proof']['sha256'],'PAGE_CHANGED')
        return observe_shared_recovery_health(claim,mysql,guard=guard,thaw_guard=thaw_guard,
            timeout=timeout,probe=probe)
    finally:snapshot.observation_deadline.reset(token)


def read_shared_dependency_receipt(claim):
    """Only this fixed receipt has a32KiB contract; ordinary claim records do not."""
    claim.assert_owned();snapshot.observation_timeout(1)
    path=snapshot._existing_file(claim.root/'shared-dependencies-health.json')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode)==0o600 and
            before.st_nlink==1 and 0<before.st_size<=32768,'RECEIPT_INVALID')
        def signature(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        chunks=[];remaining=32769
        while remaining:
            snapshot.observation_timeout(1)
            block=os.read(fd,remaining)
            if not block:break
            chunks.append(block);remaining-=len(block)
        raw=b''.join(chunks)
        _require(len(raw)==before.st_size and signature(os.fstat(fd))==signature(before) and
            signature(os.stat(path,follow_symlinks=False))==signature(before),'RECEIPT_CHANGED')
        claim.assert_owned();snapshot.observation_timeout(1)
        return raw
    finally:os.close(fd)


def restore_shared_dependencies_with_health(claim,mysql,*,guard,thaw_guard,timeout=120,probe=None):
    """Explicit first recovery stage; never restores OPEN or starts applications."""
    _require(callable(guard) and callable(thaw_guard),'PLAN_INVALID')
    probe=NativeNetworkProbe() if probe is None else probe
    deadline=health_deadline(timeout);token=snapshot.observation_deadline.set(deadline)
    try:
        thaw_guard();claim.assert_owned();_within(deadline);guard();_within(deadline)
        _require(_event(claim,'shared-dependencies-ready') is None,'ACTION_REPLAY_REFUSED')
        original=_original_health(claim)
        # Verify the held applications before the first recovery intent/action.
        split._observe_shared_actions(claim)
        for role in ('backend','frontend'):
            _,record,_=split._shared_role(claim,role)
            _require(record['state']['Running'] is False and
                _event(claim,'shared-'+role+'-restore-intent') is None,'APPLICATION_NOT_HELD')
        split.begin_shared_recovery(claim,guard=guard,thaw_guard=thaw_guard)
        split.restore_shared_container(claim,'mysql',guard=guard,thaw_guard=thaw_guard)
        _,record,_=split._shared_role(claim,'mysql')
        _require(record['id']==mysql.container and record['state']['Running'],'MYSQL_RUNTIME_CHANGED')
        while True:
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            _require(snapshot.inspect_formal_container(mysql.container)==record,'MYSQL_RUNTIME_CHANGED')
            ready=mysql.ready()
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            _require(snapshot.inspect_formal_container(mysql.container)==record,'MYSQL_RUNTIME_CHANGED')
            if ready:break
            _require(time.monotonic()+.2<deadline,'DEADLINE_EXCEEDED');time.sleep(.2)
        split.restore_shared_database_flags(claim,mysql,guard=guard,thaw_guard=thaw_guard)
        _mysql_proof(mysql,record,original['health']['mysql']['proof']['flags'])
        identity,flags,flags_sha,mysql_restored=split._restored_mysql(claim,mysql,guard,thaw_guard)
        mysql_record=split._shared_role(claim,'mysql')[1]
        database_restored=_event(claim,'shared-db-restored')
        _require(database_restored['originalSha256']==flags_sha and
            database_restored['originalFlags']==flags and
            database_restored['mysqlRuntime']==mysql_restored['runtime'] and
            flags==original['health']['mysql']['proof']['flags'],'MYSQL_FLAGS_CHANGED')
        def dependency_guard():
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            # This guard also runs between the current role's intent and its
            # completion. Global pending-action checks remain in _shared_action
            # and reconcile; here verify only the already-completed MySQL stage.
            split._recovery(claim,guard,thaw_guard)
            _require(split._shared_role(claim,'mysql')[1]==mysql_record and
                split._event(claim,'shared-mysql-restored')==mysql_restored and
                snapshot._claimed_database_original(claim)==(identity,flags,flags_sha) and
                _event(claim,'shared-db-restored')==database_restored and
                _event(claim,'db-fenced')['originalSha256']==flags_sha,'MYSQL_RUNTIME_CHANGED')
            _require(snapshot._database_flags(mysql,identity)==flags,'MYSQL_FLAGS_CHANGED')
            guard();thaw_guard();claim.assert_owned()
            _require(split._shared_role(claim,'mysql')[1]==mysql_record,'MYSQL_RUNTIME_CHANGED')
            _within(deadline)
        for role in split.RESTORE_ORDER[1:5]:
            dependency_guard()
            split.restore_shared_container(claim,role,guard=dependency_guard,thaw_guard=thaw_guard)
            _,record,_=split._shared_role(claim,role)
            observed=_await_role(claim,role,record,probe,dependency_guard,deadline)
            dependency_guard()
            _require(observed['state']==original['health'][role]['state'],'ORIGINAL_STATE_CHANGED')
            if role=='showroom' and observed['state']=='HEALTHY':
                _require(observed['proof']['sha256']==original['health'][role]['proof']['sha256'],'PAGE_CHANGED')
        restored=split.verify_shared_dependency_restoration(claim,mysql,guard=guard,thaw_guard=thaw_guard)
        _require(restored['sharedScopeSha256']==original['sharedScopeSha256'] and
            restored['originalFlags']==original['health']['mysql']['proof']['flags'],'SCOPE_CHANGED')
        health={}
        for role,record in restored['services'].items():
            dependency_guard()
            health[role]=_mysql_proof(mysql,record,restored['originalFlags']) if role=='mysql' else _await_role(claim,role,record,probe,dependency_guard,deadline)
            dependency_guard()
            _require(health[role]['state']==original['health'][role]['state'],'ORIGINAL_STATE_CHANGED')
            if role=='showroom' and health[role]['state']=='HEALTHY':
                _require(health[role]['proof']['sha256']==original['health'][role]['proof']['sha256'],'PAGE_CHANGED')
        report=dict(schemaVersion='formal-shared-dependencies-health/v1',state='DEPENDENCIES_RESTORED_PENDING_OPEN_APPROVAL',
            claimSha256=original['claimSha256'],sharedScopeSha256=restored['sharedScopeSha256'],
            originalHealthSha256=_event(claim,'shared-health-scope')['sha256'],originalFlags=restored['originalFlags'],
            runtimeSha256=hashlib.sha256(snapshot._canonical_bytes(restored['services'])).hexdigest(),
            dependencies=restored['services'],applicationsHeld=restored['applicationsHeld'],health=health,native=restored['native'],
            observedAt=datetime.now(timezone.utc).isoformat(),productionEvidence=False,releaseReady=False)
        def final_guard():
            guard();thaw_guard();claim.assert_owned();_within(deadline)
            _require(split.verify_shared_dependency_restoration(claim,mysql,guard=guard,thaw_guard=thaw_guard)==restored,'RUNTIME_CHANGED')
            _require(_original_health(claim)==original,'SCOPE_CHANGED')
            _within(deadline)
        final_guard()
        raw=snapshot._canonical_bytes(report);_require(len(raw)<=32768,'RECORD_TOO_LARGE')
        claim._write(claim.root/'shared-dependencies-health.json',raw)
        final_guard()
        _require(read_shared_dependency_receipt(claim)==raw,'RECEIPT_CHANGED')
        ready={'sha256':hashlib.sha256(raw).hexdigest()}
        claim.record('shared-dependencies-ready',ready)
        final_guard()
        _require(read_shared_dependency_receipt(claim)==raw and _event(claim,'shared-dependencies-ready')==ready,'RECEIPT_CHANGED')
        return report
    finally:snapshot.observation_deadline.reset(token)


def bind_shared_health_scope(claim,mysql,*,guard,redis_authentication,timeout=120,probe=None):
    """Capture actual original health before stop, without changing services."""
    _require(callable(guard) and redis_authentication=='none','PLAN_INVALID')
    _require(_event(claim,'shared-health-scope') is None and
        not any(e['step'].endswith('-stop-intent') for e in claim.events),'STAGE_INVALID')
    probe=NativeNetworkProbe() if probe is None else probe
    deadline=health_deadline(timeout);token=snapshot.observation_deadline.set(deadline)
    try:
        records={};health={};guard();claim.assert_owned()
        for role in split.RESTORE_ORDER:
            original,current,digest=split._shared_role(claim,role)
            _require(current==original,'RUNTIME_CHANGED');records[role]=current
            if role=='mysql':
                identity=json.loads(claim._plan)['databaseUuid']
                flags=snapshot._database_flags(mysql,identity)
                health[role]=_mysql_proof(mysql,current,flags)
            else:health[role]=_await_role(claim,role,current,probe,guard,deadline)
        for role,current in records.items():
            _require(split._shared_role(claim,role)[1]==current,'RUNTIME_CHANGED')
        report={'schemaVersion':'formal-shared-health-original/v1','sharedScopeSha256':digest,
            'claimSha256':hashlib.sha256(claim._plan).hexdigest(),'health':health,
            'redisAuthentication':redis_authentication,'observedAt':datetime.now(timezone.utc).isoformat()}
        raw=snapshot._canonical_bytes(report);_require(len(raw)<=16384,'RECORD_TOO_LARGE')
        guard();claim.assert_owned();_within(deadline)
        claim._write(claim.root/'shared-health-original.json',raw)
        _within(deadline)
        claim.record('shared-health-scope',{'sha256':hashlib.sha256(raw).hexdigest()})
        _within(deadline)
        return report
    finally:snapshot.observation_deadline.reset(token)


def observe_shared_recovery_health(claim,mysql,*,guard,thaw_guard,timeout=120,probe=None):
    """Fresh dependency guard; never releases ingress or claims browser acceptance."""
    _require(callable(guard) and callable(thaw_guard),'PLAN_INVALID')
    probe=NativeNetworkProbe() if probe is None else probe
    deadline=health_deadline(timeout);token=snapshot.observation_deadline.set(deadline)
    try:
        thaw_guard();claim.assert_owned();_within(deadline);guard();_within(deadline)
        original_event=_event(claim,'shared-health-scope');_require(original_event is not None,'SCOPE_REQUIRED')
        raw=claim._read(claim.root/'shared-health-original.json')
        _require(hashlib.sha256(raw).hexdigest()==original_event['sha256'],'SCOPE_CHANGED')
        original=_strict_object(raw)
        restored=split.verify_shared_restoration(claim,mysql,guard=guard,thaw_guard=thaw_guard)
        _require(original['sharedScopeSha256']==restored['sharedScopeSha256'] and
            original['claimSha256']==hashlib.sha256(claim._plan).hexdigest() and
            original['health']['mysql']['proof']['flags']==restored['originalFlags'],'SCOPE_CHANGED')
        health={}
        for role in split.RESTORE_ORDER:
            record=restored['services'][role]
            if role=='mysql':health[role]=_mysql_proof(mysql,record,restored['originalFlags'])
            else:health[role]=_await_role(claim,role,record,probe,guard,deadline)
            _require(health[role]['state']==original['health'][role]['state'],'ORIGINAL_STATE_CHANGED')
            if role in ('frontend','showroom') and health[role]['state']=='HEALTHY':
                _require(health[role]['proof']['sha256']==original['health'][role]['proof']['sha256'],
                         'PAGE_CHANGED')
        _require(split.verify_shared_restoration(claim,mysql,guard=guard,thaw_guard=thaw_guard)==restored,
                 'RUNTIME_CHANGED')
        _require(claim._read(claim.root/'shared-health-original.json')==raw,'SCOPE_CHANGED')
        guard();thaw_guard();claim.assert_owned();_within(deadline)
        return {'schemaVersion':'formal-shared-recovery-health/v1','state':'ORIGINAL_SERVICES_HEALTHY',
            'claimSha256':original['claimSha256'],'sharedScopeSha256':original['sharedScopeSha256'],
            'originalHealthSha256':original_event['sha256'],
            'runtimeSha256':hashlib.sha256(snapshot._canonical_bytes(restored['services'])).hexdigest(),
            'observedAt':datetime.now(timezone.utc).isoformat(),'health':health,
            'healthOnlyNotReleaseAcceptance':True,'productionEvidence':False}
    finally:snapshot.observation_deadline.reset(token)


def observe_shared_dependency_health(claim,mysql,*,expected_receipt_sha256,guard,thaw_guard,timeout=60,probe=None,
                                     open_transition=None,backend_transition=None):
    """Finite post-v7 observation, not the full pre-OPEN or ongoing writer guard.

    The owner supplies actual ingress/external/host exclusion. No OPEN, service
    action, journal write or approval consumption is performed here.
    """
    import formal_boot_state as boot
    from formal_filesystem_watchdog import require_native_runtime
    require_native_runtime()
    _require(open_transition is None or backend_transition is None,'DEPENDENCY_STAGE_INVALID')
    if open_transition is not None:
        from formal_original_open_writer import OriginalOpenHealthTransition
        _require(type(open_transition) is OriginalOpenHealthTransition and open_transition.claim is claim,
            'DEPENDENCY_STAGE_INVALID')
        open_transition.assert_valid()
    if backend_transition is not None:
        from formal_original_open_writer import CompletedOriginalOpenChecks
        _require(type(backend_transition) is CompletedOriginalOpenChecks and backend_transition.claim is claim,
            'DEPENDENCY_STAGE_INVALID')
        backend_transition.assert_valid()
    _require(os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim and
        callable(guard) and callable(thaw_guard) and type(expected_receipt_sha256) is str and
        re.fullmatch('[0-9a-f]{64}',expected_receipt_sha256),'DEPENDENCY_INPUT_INVALID')
    deadline=health_deadline(timeout);token=snapshot.observation_deadline.set(deadline)
    try:
        thaw_guard();guard();claim.assert_owned();_within(deadline)
        root=boot._absolute(str(claim.root))
        with boot._directory(root,no_atime=True) as (directory,root_identity):
            lock_pair=boot._read_at(directory,'ownership.lock',0o600,1,no_atime=True,allow_empty=True)
        _require(lock_pair[0]==b'' and lock_pair[1][:2]==claim._lock_identity,'SCOPE_CHANGED')
        journal=snapshot._canonical_bytes(claim.events)
        allowed_open=set() if open_transition is None else open_transition.assert_valid()
        if backend_transition is not None:
            backend_transition.assert_valid()
            allowed_open={'boot-backend-open-'+name for name in ('intent','approval-consumed','restored')}
        allowed_backend=set() if backend_transition is None else {'shared-backend-restore-intent','shared-backend-restored'}
        _require(not any(event['step'] in ('released','failed-retained','ingress-release-intent','ingress-released') or
            ('-open-' in event['step'] and event['step'] not in allowed_open) or
            (event['step'].startswith(('shared-backend-restore','shared-frontend-restore')) and event['step'] not in allowed_backend) or
            event['step']=='external-recovery-intent' or (event['step'].startswith('external-') and '-restore' in event['step'])
            for event in claim.events),'DEPENDENCY_STAGE_INVALID')
        pins={}
        selected=[('binding.json',16384),('shared-health-original.json',16384),('shared-dependencies-health.json',32768)]
        if backend_transition is not None:
            selected += [(name,16384) for name in sorted(boot.ORIGINALS|{'database-original.json'})]
        for name,limit in selected+[('event-%06d.json'%event['sequence'],16384) for event in claim.events]:
            pins[root/name]=(limit,boot._read_secure(root/name,0o600,limit,no_atime=True))
        _require(pins[root/'binding.json'][1][0]==claim._plan,'SCOPE_CHANGED')
        original_raw=pins[root/'shared-health-original.json'][1][0]
        receipt_raw=pins[root/'shared-dependencies-health.json'][1][0]
        try:original=_strict_object(original_raw);receipt=_strict_object(receipt_raw)
        except (ValueError,UnicodeError,RecursionError):
            raise snapshot.FormalSnapshotError('FORMAL_HEALTH_RECEIPT_INVALID') from None
        def same(a,b):return snapshot._canonical_bytes(a)==snapshot._canonical_bytes(b)
        def one(name):
            values=[event['details'] for event in claim.events if event['step']==name]
            _require(len(values)==1,'SCOPE_REQUIRED');return values[0]
        roles=set(split.RESTORE_ORDER[:5]);event_names={'event-%06d.json'%event['sequence'] for event in claim.events}
        _require(type(original) is dict and set(original)=={'schemaVersion','claimSha256','sharedScopeSha256',
            'health','redisAuthentication','observedAt'} and
            original['schemaVersion']=='formal-shared-health-original/v1' and
            original['redisAuthentication']=='none' and type(original['health']) is dict and
            set(original['health'])==split.ROLES and
            snapshot._canonical_bytes(original)==original_raw,'SCOPE_CHANGED')
        expected_fields={'schemaVersion','state','claimSha256','sharedScopeSha256','originalHealthSha256',
            'originalFlags','runtimeSha256','dependencies','applicationsHeld','health','native','observedAt',
            'productionEvidence','releaseReady'}
        _require(type(receipt) is dict and set(receipt)==expected_fields and
            receipt['schemaVersion']=='formal-shared-dependencies-health/v1' and
            receipt['state']=='DEPENDENCIES_RESTORED_PENDING_OPEN_APPROVAL' and
            receipt['productionEvidence'] is False and receipt['releaseReady'] is False and
            snapshot._canonical_bytes(receipt)==receipt_raw and hashlib.sha256(receipt_raw).hexdigest()==expected_receipt_sha256 and
            one('shared-dependencies-ready')=={'sha256':expected_receipt_sha256} and
            one('shared-health-scope')=={'sha256':hashlib.sha256(original_raw).hexdigest()} and
            receipt['originalHealthSha256']==hashlib.sha256(original_raw).hexdigest() and
            receipt['claimSha256']==original['claimSha256']==hashlib.sha256(claim._plan).hexdigest() and
            receipt['sharedScopeSha256']==original['sharedScopeSha256'] and
            one('shared-container-scope')=={'scopeSha256':receipt['sharedScopeSha256']},'RECEIPT_INVALID')
        _require(type(receipt['dependencies']) is dict and set(receipt['dependencies'])==roles and
            type(receipt['applicationsHeld']) is dict and set(receipt['applicationsHeld'])=={'backend','frontend'} and
            type(receipt['health']) is dict and set(receipt['health'])==roles and
            receipt['runtimeSha256']==hashlib.sha256(snapshot._canonical_bytes(receipt['dependencies'])).hexdigest(),
            'RECEIPT_INVALID')
        for record in list(receipt['dependencies'].values())+list(receipt['applicationsHeld'].values()):
            snapshot._container_stable(record)
        _require(all(record['state']['Running'] is False for record in receipt['applicationsHeld'].values()),'APPLICATION_NOT_HELD')
        flags=receipt['originalFlags']
        _require(type(flags) is dict and set(flags)=={'serverUuid','readOnly','superReadOnly'} and
            flags['serverUuid']==json.loads(claim._plan)['databaseUuid'] and type(flags['readOnly']) is int and flags['readOnly'] in (0,1) and
            type(flags['superReadOnly']) is int and flags['superReadOnly']==0 and
            same(flags,original['health']['mysql']['proof']['flags']),'MYSQL_FLAGS_CHANGED')
        def validate_role_health(role,value,record):
            _require(type(value) is dict,'RECEIPT_INVALID')
            if record['state']['Running'] is False:
                _require(set(value)=={'state','healthObserved'} and value['state']=='ORIGINALLY_STOPPED' and
                    value['healthObserved'] is False,'RECEIPT_INVALID');return
            _require(set(value)=={'state','proof'} and value['state']=='HEALTHY' and
                type(value['proof']) is dict,'RECEIPT_INVALID')
            proof=value['proof']
            if role=='mysql':
                _require(set(proof)=={'protocol','flags'} and proof['protocol']=='mysql' and same(proof['flags'],flags),
                    'MYSQL_FLAGS_CHANGED');return
            native_fields={'networkNamespaceInode','pid'}
            _require(all(type(proof.get(key)) is int and proof[key]>0 for key in native_fields),'RECEIPT_INVALID')
            if role=='redis':
                _require(set(proof)==native_fields|{'protocol','response','authentication'} and
                    proof['protocol']=='redis' and proof['response']=='PONG' and proof['authentication']=='none',
                    'REDIS_RESPONSE_INVALID')
            else:
                _require(set(proof)==native_fields|{'httpStatus','bytes','sha256'} and type(proof['httpStatus']) is int and
                    proof['httpStatus']==200 and type(proof['bytes']) is int and 0<=proof['bytes']<=MAX_BODY and
                    type(proof['sha256']) is str and re.fullmatch('[0-9a-f]{64}',proof['sha256']),'RECEIPT_INVALID')
        for role in split.RESTORE_ORDER[:5]:
            validate_role_health(role,original['health'][role],receipt['dependencies'][role])
            validate_role_health(role,receipt['health'][role],receipt['dependencies'][role])
        def private_guard(*,owner_checks=True):
            if owner_checks:thaw_guard();guard()
            if open_transition is not None:
                if owner_checks:open_transition.assert_valid()
                else:open_transition.assert_signatures()
            if backend_transition is not None:
                if owner_checks:backend_transition.assert_valid()
                else:backend_transition.assert_signatures()
            _within(deadline)
            _require(snapshot._canonical_bytes(claim.events)==journal,'SCOPE_CHANGED')
            if owner_checks:
                claim.assert_owned()
                for path,(limit,pair) in pins.items():
                    _require(boot._read_secure(path,0o600,limit,no_atime=True)==pair,'RECEIPT_CHANGED')
                claim.assert_owned()
            for path,(_,pair) in pins.items():
                _require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],'RECEIPT_CHANGED')
            with boot._directory(root,no_atime=True) as (fd,current):
                _require(current==root_identity and {name for name in os.listdir(fd) if name.startswith('event-')}==event_names,
                    'SCOPE_CHANGED')
            _require(boot._signature(os.stat(root/'ownership.lock',follow_symlinks=False))==lock_pair[1] and
                boot._signature(os.fstat(claim._fd))==lock_pair[1],'SCOPE_CHANGED')
            _within(deadline)
        phase_kwargs={} if backend_transition is None else {'backend_transition':backend_transition}
        restored=split.verify_shared_dependency_restoration(claim,mysql,guard=private_guard,thaw_guard=thaw_guard,**phase_kwargs)
        def checked():
            private_guard()
            if backend_transition is None:
                current=split.verify_shared_dependency_restoration(claim,mysql,guard=private_guard,thaw_guard=thaw_guard)
                _require(same(current,restored),'RUNTIME_CHANGED')
            else:
                # Initial verification binds all immutable originals and journal
                # records. private_guard pins them on every boundary; rebuilding
                # the same seven-role journal repeatedly adds no new evidence.
                # Observe actual mutable runtimes/flags/thaw on every boundary.
                for role in split.RESTORE_ORDER:
                    expected=(restored['backendCurrent'] if role=='backend' else
                        restored['services'][role] if role in roles else restored['applicationsHeld'][role])
                    _require(same(snapshot.inspect_formal_container(expected['id']),expected),'RUNTIME_CHANGED')
                    _within(deadline)
                _require(same(snapshot._database_flags(mysql,flags['serverUuid']),flags),'MYSQL_FLAGS_CHANGED')
                _require(same(split._thaw_receipt(claim),restored['native']),'SCOPE_CHANGED')
                _require(backend_transition.assert_valid()['startStage']==restored['backendStartStage'],'DEPENDENCY_STAGE_INVALID')
            private_guard()
        held_matches=same(restored['applicationsHeld'],receipt['applicationsHeld'])
        if backend_transition is not None:
            held_matches=(same(restored['applicationsHeld'],{'frontend':receipt['applicationsHeld']['frontend']}) and
                same(snapshot._container_stable(restored['backendCurrent']),snapshot._container_stable(receipt['applicationsHeld']['backend'])) and
                same(receipt['applicationsHeld']['backend']['state'],backend_transition.start_intent['before']))
        _require(same(restored['services'],receipt['dependencies']) and held_matches and
            same(restored['originalFlags'],flags) and same(restored['native'],receipt['native']) and
            restored['sharedScopeSha256']==receipt['sharedScopeSha256'],'RECEIPT_INVALID')
        probe=NativeNetworkProbe() if probe is None else probe
        health={}
        for role in split.RESTORE_ORDER[:5]:
            checked();record=restored['services'][role]
            health[role]=_mysql_proof(mysql,record,flags) if role=='mysql' else _await_role(claim,role,record,probe,checked,deadline)
            checked()
            validate_role_health(role,health[role],record)
            _require(health[role]['state']==original['health'][role]['state']==receipt['health'][role]['state'],'ORIGINAL_STATE_CHANGED')
            if role=='showroom' and health[role]['state']=='HEALTHY':
                _require(health[role]['proof']['sha256']==original['health'][role]['proof']['sha256']==receipt['health'][role]['proof']['sha256'],
                    'PAGE_CHANGED')
        result=dict(schemaVersion='formal-shared-dependency-observation/v1',state='DEPENDENCIES_HEALTH_OBSERVED_ONLY',
            receiptSha256=expected_receipt_sha256,claimSha256=receipt['claimSha256'],sharedScopeSha256=receipt['sharedScopeSha256'],
            health=health,healthOnlyNotReleaseAcceptance=True,productionEvidence=False,releaseReady=False,
            serviceActionsPerformed=False,fullRunnerCompleted=False,claimReleased=False)
        if backend_transition is not None:
            checked();record=restored['backendCurrent']
            if record['state']['Running']:
                backend_health=_await_role(claim,'backend',record,probe,checked,deadline)
                validate_role_health('backend',backend_health,record)
                _require(original['health']['backend']['state']=='HEALTHY','ORIGINAL_STATE_CHANGED')
            else:backend_health=dict(state='HELD_STOPPED_PENDING_START',healthObserved=False)
            checked()
            result.update(backendStartStage=restored['backendStartStage'],backendHealth=backend_health)
        _require(len(snapshot._canonical_bytes(result))<=16384,'RECORD_TOO_LARGE')
        checked();private_guard()
        # All owner callbacks must finish before the final native source reads.
        # Re-entering an owner callback after them would accept its late runtime
        # or DB mutation with only a filesystem sweep remaining.
        for role in split.RESTORE_ORDER:
            expected=(restored['backendCurrent'] if role=='backend' and backend_transition is not None else
                restored['services'][role] if role in roles else restored['applicationsHeld'][role])
            _require(same(snapshot.inspect_formal_container(expected['id']),expected),'RUNTIME_CHANGED')
            _within(deadline)
        _require(same(snapshot._database_flags(mysql,flags['serverUuid']),flags),'MYSQL_FLAGS_CHANGED')
        private_guard(owner_checks=False);return result
    except (OSError,KeyError,TypeError,ValueError,RecursionError):
        raise snapshot.FormalSnapshotError('FORMAL_HEALTH_DEPENDENCY_OBSERVATION_FAILED_RETAINED') from None
    finally:snapshot.observation_deadline.reset(token)
