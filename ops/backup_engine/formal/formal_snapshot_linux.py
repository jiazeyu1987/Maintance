#!/usr/bin/env python3
"""Limited formal snapshot building blocks; not a legacy DCC recovery adapter.

Snapshot orchestration must hold the independently observed database/object
barrier throughout export. These primitives alone never produce COMPLETE.
"""
import gzip
from contextvars import ContextVar
import math
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import stat
import sys
import time
from datetime import datetime, timezone

observation_deadline = ContextVar('formal_observation_deadline', default=None)


def observation_timeout(seconds):
    deadline=observation_deadline.get()
    if deadline is not None:
        seconds=min(seconds,deadline-time.monotonic())
        require(seconds>0,'FORMAL_DATA_DEADLINE')
    return seconds


class FormalSnapshotError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code=code


class NativeCaptureNotStarted(FormalSnapshotError):
    """A typed refusal before loading/invoking any native acquisition code."""


def require(ok,code):
    if not ok:raise FormalSnapshotError(code)


def safe_file(path):
    path=Path(path).absolute()
    for part in [path.parent,*path.parent.parents]:
        require(part.is_dir() and not part.is_symlink() and part.resolve()==part,'FORMAL_SNAPSHOT_PATH_INVALID')
    require(not path.exists() and not path.is_symlink(),'FORMAL_SNAPSHOT_EXISTS')
    return path


def _canonical_bytes(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')


def _sync_directory(path):
    descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


class FormalMaintenanceClaim:
    """Linux task ownership and retained journal, not a host/storage hard fence.

    Explicit resume verifies the old binding and chain, never repeats actions or
    restores flags. Callers must reconcile actual state after interrupted intent.
    Other host administrators do not automatically honor this advisory lock.
    """
    restorationAutomaticallyPerformed=False
    _steps={'container-scope','db-fence-intent','db-fenced','backend-stop-intent','backend-stopped',
            'minio-stop-intent','minio-stopped','capture-intent','captured',
            'db-probe-before-intent','db-probe-before','db-probe-after-intent','db-probe-after',
            'minio-restore-intent','minio-restored','db-restore-intent','db-restored',
            'backend-restore-intent','backend-restored','released','failed-retained',
            'shared-container-scope','split-sql-intent','split-sql-captured',
            'split-raw-intent','split-native-not-requested','split-captured','shared-recovery-intent',
            'shared-db-restore-intent','shared-db-restored',
            'external-caller-scope','external-recovery-intent','maintenance-originals-bound',
            'split-db-probe-before-intent','split-db-probe-before',
            'split-db-probe-after-intent','split-db-probe-after',
            'ingress-scope','ingress-install-intent','ingress-installed',
            'ingress-release-intent','ingress-released','shared-health-scope','external-health-scope',
            'ingress-recovery-intent','ingress-recovery-permitted','shared-dependencies-ready','host-originals-bound',
            'host-derived-originals-bound','production-a-resume-intent','production-a-resume-consumed'} | {
                'host-'+unit+suffix for unit in ('crond','dnf-makecache','systemd-tmpfiles-clean','unbound-anchor','cockpit')
                for suffix in ('-mask-intent','-masked','-stop-intent','-closed','-restore-intent','-restored')} | {
                'boot-'+role+suffix for role in
                ('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal')
                for suffix in ('-bound','-close-intent','-closed','-open-intent',
                               '-open-approval-consumed','-open-restored')} | {
                'live-'+role+suffix for role in
                ('backend','test-backend','test-rehearsal','backup-backend','backup-rehearsal')
                for suffix in ('-close-intent','-closed')} | {
                'external-'+role+suffix for role in
                ('test-backend','test-rehearsal','backup-backend','backup-rehearsal')
                for suffix in ('-stop-intent','-stopped','-restore-intent','-restored')} | {
                'shared-'+role+suffix for role in
                ('mysql','frontend','backend','showroom','onlyoffice','redis','minio')
                for suffix in ('-stop-intent','-stopped','-restore-intent','-restored')}
    def __init__(self,root,binding,*,resume=False):
        self._fd=None
        require(os.name=='posix','FORMAL_MAINTENANCE_LINUX_REQUIRED')
        import fcntl
        require(type(resume) is bool and type(binding) is dict and
            set(binding)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'},
            'FORMAL_MAINTENANCE_BINDING_INVALID')
        require(type(binding['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['operationId']),
            'FORMAL_MAINTENANCE_BINDING_INVALID')
        require(all(type(binding[k]) is str and re.fullmatch('[0-9a-f]{64}',binding[k])
                    for k in ('sourceFingerprint','minioContainerId')) and
            type(binding['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',binding['databaseUuid']),
            'FORMAL_MAINTENANCE_BINDING_INVALID')
        self.root=Path(root).absolute();self._pid=os.getpid();self._plan=_canonical_bytes(binding)
        try:
            if not resume:
                safe_file(self.root);self.root.mkdir(mode=0o700);_sync_directory(self.root.parent)
            require(self.root.is_dir() and not self.root.is_symlink() and self.root.resolve()==self.root,
                    'FORMAL_MAINTENANCE_PATH_INVALID')
            require(stat.S_IMODE(self.root.stat().st_mode)==0o700,'FORMAL_MAINTENANCE_PATH_INVALID')
            self._root_identity=(self.root.stat().st_dev,self.root.stat().st_ino)
            self._lock=self.root/'ownership.lock'
            flags=os.O_RDWR|os.O_NOFOLLOW|(0 if resume else os.O_CREAT|os.O_EXCL)
            self._fd=os.open(self._lock,flags,0o600)
            info=os.fstat(self._fd)
            require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600,
                    'FORMAL_MAINTENANCE_LOCK_INVALID')
            self._lock_identity=(info.st_dev,info.st_ino)
            try:fcntl.flock(self._fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise FormalSnapshotError('FORMAL_MAINTENANCE_BUSY') from None
            self._plan_path=self.root/'binding.json'
            if not resume:self._write(self._plan_path,self._plan)
            require(self._read(self._plan_path)==self._plan,'FORMAL_MAINTENANCE_BINDING_CHANGED')
            self.events=self._read_events()
            require(not self.events or self.events[-1]['step']!='released','FORMAL_MAINTENANCE_ALREADY_RELEASED')
        except FormalSnapshotError:self.close();raise
        except OSError:self.close();raise FormalSnapshotError('FORMAL_MAINTENANCE_IO_FAILED') from None

    def _write(self,path,raw):
        from formal_capture_budget import active_budget
        budget=active_budget.get()
        if budget is not None:
            with budget.open(path,'proof') as output:output.write(raw);output.flush()
            _sync_directory(self.root)
            return
        with path.open('xb') as output:
            os.chmod(path,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
        _sync_directory(self.root)

    def _read(self,path):
        path=_existing_file(path)
        require(path.stat().st_size<=16384,'FORMAL_MAINTENANCE_RECORD_INVALID')
        return path.read_bytes()

    def _read_events(self):
        records=((path.name,self._read(path)) for path in sorted(self.root.glob('event-*')))
        return _parse_maintenance_events(self._plan,records,self._steps)

    def assert_owned(self):
        require(self._fd is not None and self._pid==os.getpid(),'FORMAL_MAINTENANCE_OWNER_INVALID')
        require(self.root.is_dir() and not self.root.is_symlink() and self.root.resolve()==self.root and
            (self.root.stat().st_dev,self.root.stat().st_ino)==self._root_identity,
            'FORMAL_MAINTENANCE_PATH_CHANGED')
        require(not self._lock.is_symlink() and
            (self._lock.stat().st_dev,self._lock.stat().st_ino)==self._lock_identity,
            'FORMAL_MAINTENANCE_LOCK_CHANGED')
        require(self._read(self._plan_path)==self._plan,'FORMAL_MAINTENANCE_BINDING_CHANGED')
        require(self._read_events()==self.events,'FORMAL_MAINTENANCE_JOURNAL_CHANGED')

    def record(self,step,details):
        self.assert_owned()
        require(type(step) is str and step in self._steps and type(details) is dict,
                'FORMAL_MAINTENANCE_EVENT_INVALID')
        require(not any(e['step']==step or e['step']=='released' for e in self.events),
                'FORMAL_MAINTENANCE_STEP_ALREADY_RECORDED')
        previous=self._plan if not self.events else self._read(self.root/f'event-{len(self.events):06d}.json')
        event={'sequence':len(self.events)+1,'step':step,'details':details,
               'previousDigest':hashlib.sha256(previous).hexdigest()}
        raw=_canonical_bytes(event)
        require(len(raw)<=16384,'FORMAL_MAINTENANCE_EVENT_INVALID')
        try:self._write(self.root/f'event-{event["sequence"]:06d}.json',raw)
        except OSError:raise FormalSnapshotError('FORMAL_MAINTENANCE_JOURNAL_WRITE_FAILED') from None
        # Detach caller-owned dictionaries: subsequent mutations must not change
        # the in-memory view used to compare immutable on-disk records.
        self.events.append(json.loads(raw))
        self.assert_owned()
        return hashlib.sha256(raw).hexdigest()

    def close(self):
        if self._fd is not None:
            os.close(self._fd);self._fd=None


def _parse_maintenance_events(plan, records, allowed_steps):
    """Pure journal validation shared by owner and explicitly read-only observer."""
    previous=hashlib.sha256(plan).hexdigest();events=[];seen=set()
    for index,(name,raw) in enumerate(records,1):
        require(name==f'event-{index:06d}.json','FORMAL_MAINTENANCE_JOURNAL_INVALID')
        try:value=json.loads(raw.decode('utf-8'))
        except (ValueError,UnicodeError,RecursionError):raise FormalSnapshotError('FORMAL_MAINTENANCE_JOURNAL_INVALID') from None
        try:canonical=_canonical_bytes(value)
        except RecursionError:raise FormalSnapshotError('FORMAL_MAINTENANCE_JOURNAL_INVALID') from None
        require(type(value) is dict and set(value)=={'sequence','step','details','previousDigest'} and
            type(value['sequence']) is int and value['sequence']==index and
            type(value['step']) is str and value['step'] in allowed_steps and value['step'] not in seen and
            type(value['details']) is dict and value['previousDigest']==previous and raw==canonical,
            'FORMAL_MAINTENANCE_JOURNAL_INVALID')
        require(not events or events[-1]['step']!='released','FORMAL_MAINTENANCE_JOURNAL_INVALID')
        seen.add(value['step']);events.append(value);previous=hashlib.sha256(raw).hexdigest()
    return events


def observe_database_barrier(mysql,*,dump_in_progress=False):
    """Readonly observation only; callers must actually acquire and retain fence.

    Not sufficient for FINALIZED: object credential/write rejection, writer
    inventory and barrier lifetime must still be proven by orchestration.
    """
    observed=mysql.query('SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only, '
                         '(SELECT COUNT(*) FROM information_schema.innodb_trx);')
    require(type(dump_in_progress) is bool and type(observed) is str and
        re.fullmatch(r'1\t1\t(?:0|[1-9][0-9]*)\n',observed) is not None and
        (dump_in_progress or observed=='1\t1\t0\n'),'FORMAL_DATABASE_NOT_QUIESCENT')
    # The exporter itself owns a read transaction. Retain the actual count;
    # every normal pre/post observation still requires zero transactions.
    return {'readOnly':True,'superReadOnly':True,'activeDatabaseTransactions':int(observed.split('\t')[2])}


def _database_flags(mysql,expected_uuid):
    require(type(expected_uuid) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',expected_uuid),
            'FORMAL_DATABASE_UUID_INVALID')
    value=mysql.query('SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only;')
    require(value in (expected_uuid+'\t0\t0\n',expected_uuid+'\t1\t0\n',expected_uuid+'\t1\t1\n'),
            'FORMAL_DATABASE_IDENTITY_OR_FLAGS_INVALID')
    parts=value.strip().split('\t')
    return {'serverUuid':expected_uuid,'readOnly':int(parts[1]),'superReadOnly':int(parts[2])}


def acquire_database_fence(mysql,expected_uuid,intent_path):
    """Explicit state change; invoke only within approved exclusive maintenance.

    Intent remains on every failure. This function never auto-restores/retries.
    Flags alone do not prove write rejection or the object/host writer fence.
    """
    intent=safe_file(intent_path);original=_database_flags(mysql,expected_uuid)
    require(original['superReadOnly']==0,'FORMAL_DATABASE_FENCE_ALREADY_HELD')
    raw=(json.dumps(original,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    with intent.open('xb') as output:
        os.chmod(intent,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
    mysql.query('SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;')
    require(_database_flags(mysql,expected_uuid)=={'serverUuid':expected_uuid,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_FENCE_ACQUIRE_FAILED')
    observe_database_barrier(mysql)
    require(_existing_file(intent).read_bytes()==raw,'FORMAL_DATABASE_FENCE_INTENT_CHANGED')
    return original


def restore_database_fence(mysql,expected_uuid,intent_path):
    """Explicit restore to recorded flags; caller must prove claim ownership."""
    intent=_existing_file(intent_path)
    require(intent.stat().st_size<=256,'FORMAL_DATABASE_FENCE_INTENT_INVALID')
    raw=intent.read_bytes()
    try:data=json.loads(raw.decode('utf-8',errors='strict'))
    except (ValueError,UnicodeError):raise FormalSnapshotError('FORMAL_DATABASE_FENCE_INTENT_INVALID') from None
    require(type(data) is dict and set(data)=={'serverUuid','readOnly','superReadOnly'} and
            data['serverUuid']==expected_uuid and type(data['readOnly']) is int and data['readOnly'] in (0,1) and
            type(data['superReadOnly']) is int and data['superReadOnly']==0,
            'FORMAL_DATABASE_FENCE_INTENT_INVALID')
    canonical=(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
    require(raw==canonical,'FORMAL_DATABASE_FENCE_INTENT_INVALID')
    require(_database_flags(mysql,expected_uuid)=={'serverUuid':expected_uuid,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_FENCE_RESTORE_STATE_AMBIGUOUS')
    require(_existing_file(intent).read_bytes()==raw,'FORMAL_DATABASE_FENCE_INTENT_CHANGED')
    mysql.query('SET GLOBAL super_read_only=OFF; SET GLOBAL read_only='+('ON' if data['readOnly'] else 'OFF')+';')
    require(_database_flags(mysql,expected_uuid)==data,'FORMAL_DATABASE_FENCE_RESTORE_FAILED')
    require(_existing_file(intent).read_bytes()==raw,'FORMAL_DATABASE_FENCE_INTENT_CHANGED')
    return data


def _claim_database_identity(claim):
    require(isinstance(claim,FormalMaintenanceClaim),'FORMAL_MAINTENANCE_OWNER_INVALID')
    claim.assert_owned()
    return json.loads(claim._plan)['databaseUuid']


def _claim_event(claim,step):
    matches=[event for event in claim.events if event['step']==step]
    require(len(matches)==1,'FORMAL_DATABASE_CLAIM_STAGE_INVALID')
    return matches[0]


def _claimed_database_original(claim):
    identity=_claim_database_identity(claim)
    event=_claim_event(claim,'db-fence-intent')
    raw=claim._read(claim.root/'database-original.json')
    details=event['details']
    require(set(details)=={'originalFlags','originalSha256'} and
        details['originalSha256']==hashlib.sha256(raw).hexdigest() and
        raw==_canonical_bytes(details['originalFlags']),
        'FORMAL_DATABASE_CLAIM_ORIGINAL_CHANGED')
    original=details['originalFlags']
    require(type(original) is dict and set(original)=={'serverUuid','readOnly','superReadOnly'} and
        original['serverUuid']==identity and type(original['readOnly']) is int and original['readOnly'] in (0,1) and
        type(original['superReadOnly']) is int and original['superReadOnly']==0,
        'FORMAL_DATABASE_CLAIM_ORIGINAL_INVALID')
    return identity,original,details['originalSha256']


def acquire_claimed_database_fence(claim,mysql,*,guard):
    """Explicit approved acquire; durable claim/original-state intent before SET.

    Failure leaves the intent. Repeated acquire is refused even when flags look
    unchanged; reconcile an interrupted intent explicitly before restoration.
    """
    require(callable(guard),'FORMAL_DATABASE_MUTATION_GUARD_REQUIRED')
    def checked():
        observation_timeout(1);claim.assert_owned();guard();claim.assert_owned();observation_timeout(1)
    checked();identity=_claim_database_identity(claim)
    require(not any(e['step'].startswith('db-') or e['step']=='released' for e in claim.events),
            'FORMAL_DATABASE_CLAIM_STAGE_INVALID')
    original=_database_flags(mysql,identity)
    require(original['superReadOnly']==0,'FORMAL_DATABASE_FENCE_ALREADY_HELD')
    raw=_canonical_bytes(original)
    try:claim._write(safe_file(claim.root/'database-original.json'),raw)
    except OSError:raise FormalSnapshotError('FORMAL_DATABASE_CLAIM_INTENT_WRITE_FAILED') from None
    digest=hashlib.sha256(raw).hexdigest()
    claim.record('db-fence-intent',{'originalFlags':original,'originalSha256':digest})
    require(_database_flags(mysql,identity)==original,'FORMAL_DATABASE_CLAIM_ORIGINAL_DRIFT')
    _claimed_database_original(claim)
    checked()
    mysql.query('SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;')
    checked()
    require(_database_flags(mysql,identity)=={'serverUuid':identity,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_FENCE_ACQUIRE_FAILED')
    observe_database_barrier(mysql);_claimed_database_original(claim);checked()
    claim.record('db-fenced',{'originalSha256':digest,'reconciled':False})
    checked()
    return original


def reconcile_claimed_database_fence(claim,mysql,*,guard):
    """Guarded readonly reconciliation; records evidence, never replays SET.

    A retained SET effect does not establish the other maintenance boundaries.
    The same live exclusion guard must approve observations and completion.
    """
    require(callable(guard),'FORMAL_DATABASE_MUTATION_GUARD_REQUIRED')
    def checked():
        observation_timeout(1);claim.assert_owned();guard();claim.assert_owned();observation_timeout(1)
    checked();identity,original,digest=_claimed_database_original(claim)
    require(not any(e['step'] in ('db-fenced','db-restore-intent','db-restored','released') for e in claim.events),
            'FORMAL_DATABASE_CLAIM_STAGE_INVALID')
    require(_database_flags(mysql,identity)=={'serverUuid':identity,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_CLAIM_RECONCILIATION_REQUIRED')
    observe_database_barrier(mysql);_claimed_database_original(claim);checked()
    claim.record('db-fenced',{'originalSha256':digest,'reconciled':True})
    checked()
    return original


def restore_claimed_database_fence(claim,mysql):
    """Explicit original-state restore, never retries an interrupted restore."""
    identity,original,digest=_claimed_database_original(claim)
    held=_claim_event(claim,'db-fenced')
    require(held['details'].get('originalSha256')==digest and
        not any(e['step'] in ('db-restore-intent','db-restored','released') for e in claim.events),
        'FORMAL_DATABASE_CLAIM_STAGE_INVALID')
    require(_database_flags(mysql,identity)=={'serverUuid':identity,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_FENCE_RESTORE_STATE_AMBIGUOUS')
    claim.record('db-restore-intent',{'originalSha256':digest})
    result=restore_database_fence(mysql,identity,claim.root/'database-original.json')
    require(result==original,'FORMAL_DATABASE_CLAIM_ORIGINAL_CHANGED')
    _claimed_database_original(claim)
    claim.record('db-restored',{'originalSha256':digest,'reconciled':False})
    return result


def reconcile_claimed_database_restore(claim,mysql):
    """Confirm already restored original flags after interruption; no SQL SET.

    Any partial/mismatched state remains ambiguous and is not auto-corrected.
    """
    identity,original,digest=_claimed_database_original(claim)
    _claim_event(claim,'db-fenced');intent=_claim_event(claim,'db-restore-intent')
    require(intent['details']=={'originalSha256':digest} and
        not any(e['step'] in ('db-restored','released') for e in claim.events),
        'FORMAL_DATABASE_CLAIM_STAGE_INVALID')
    require(_database_flags(mysql,identity)==original,'FORMAL_DATABASE_CLAIM_RECONCILIATION_REQUIRED')
    _claimed_database_original(claim)
    claim.record('db-restored',{'originalSha256':digest,'reconciled':True})
    return original


CONTAINER_INSPECT_TEMPLATE = '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"mounts":{{json .Mounts}},"restartPolicy":{{json .HostConfig.RestartPolicy}},"state":{"Running":{{json .State.Running}},"Paused":{{json .State.Paused}},"Restarting":{{json .State.Restarting}},"Dead":{{json .State.Dead}},"OOMKilled":{{json .State.OOMKilled}},"ExitCode":{{json .State.ExitCode}},"StartedAt":{{json .State.StartedAt}},"FinishedAt":{{json .State.FinishedAt}}}}'


def inspect_formal_container(identity):
    require(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity),'FORMAL_CONTAINER_ID_INVALID')
    # Exclude command/env and health-check output; store only runtime identities.
    template=CONTAINER_INSPECT_TEMPLATE
    try:
        result=subprocess.run(['docker','inspect','--format',template,identity],stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=observation_timeout(30),check=False)
        require(result.returncode==0 and len(result.stdout)<=65536,'FORMAL_CONTAINER_INSPECT_FAILED')
        record=json.loads(result.stdout.decode('utf-8'))
        require(record.get('id')==identity,'FORMAL_CONTAINER_BINDING_MISMATCH')
        return record
    except (OSError,subprocess.TimeoutExpired,ValueError,UnicodeError):
        raise FormalSnapshotError('FORMAL_CONTAINER_INSPECT_FAILED') from None


def run_formal_container_action(action,identity):
    require(action in ('stop','start') and type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity),
            'FORMAL_CONTAINER_ACTION_INVALID')
    # Maintenance accepts normal shutdown only. Explicit SIGTERM overrides an
    # image's StopSignal; -1 prevents the daemon from escalating to SIGKILL.
    # The bounded client can still time out: retain its journal intent, never
    # claim completion or retry an action whose server-side effect is unknown.
    command=['docker','stop','--signal','SIGTERM','--timeout','-1',identity] if action=='stop' else ['docker','start',identity]
    try:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=observation_timeout(90),check=False)
        observation_timeout(90)
        require(result.returncode==0 and result.stdout.decode('utf-8').strip()==identity,
                'FORMAL_CONTAINER_ACTION_FAILED')
    except (OSError,subprocess.TimeoutExpired,UnicodeError):
        raise FormalSnapshotError('FORMAL_CONTAINER_ACTION_FAILED') from None


def _container_stable(record):
    require(type(record) is dict and set(record)=={'id','name','image','mounts','restartPolicy','state'},
            'FORMAL_CONTAINER_RECORD_INVALID')
    state=record['state']
    require(type(state) is dict and set(state)=={'Running','Paused','Restarting','Dead','OOMKilled','ExitCode','StartedAt','FinishedAt'} and
        all(type(state[k]) is bool for k in ('Running','Paused','Restarting','Dead','OOMKilled')) and
        type(state['ExitCode']) is int and all(type(state[k]) is str and state[k] for k in ('StartedAt','FinishedAt')) and
        not any(state[k] for k in ('Paused','Restarting','Dead','OOMKilled')),
        'FORMAL_CONTAINER_RUNTIME_INVALID')
    require(type(record['image']) is str and re.fullmatch('sha256:[0-9a-f]{64}',record['image']) and
        type(record['mounts']) is list and type(record['restartPolicy']) is dict,
        'FORMAL_CONTAINER_RECORD_INVALID')
    return {key:value for key,value in record.items() if key!='state'}


def bind_claimed_container_scope(claim,backend_id,backend_name,minio_name):
    _claim_database_identity(claim)
    require(not any(e['step']=='container-scope' or '-stop-' in e['step'] for e in claim.events),
            'FORMAL_CONTAINER_CLAIM_STAGE_INVALID')
    binding=json.loads(claim._plan);minio_id=binding['minioContainerId']
    require(type(backend_id) is str and re.fullmatch('[0-9a-f]{64}',backend_id) and backend_id!=minio_id,
            'FORMAL_CONTAINER_ID_INVALID')
    for name in (backend_name,minio_name):
        require(type(name) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}',name),
                'FORMAL_CONTAINER_BINDING_MISMATCH')
    scope={}
    for role,identity,name in (('backend',backend_id,backend_name),('minio',minio_id,minio_name)):
        record=inspect_formal_container(identity);_container_stable(record)
        require(record['id']==identity and record['name']=='/'+name and record['state']['Running'],
                'FORMAL_CONTAINER_BINDING_MISMATCH')
        scope[role]=record
    raw=_canonical_bytes(scope)
    require(len(raw)<=16384,'FORMAL_CONTAINER_RECORD_INVALID')
    try:claim._write(safe_file(claim.root/'container-original.json'),raw)
    except OSError:raise FormalSnapshotError('FORMAL_CONTAINER_SCOPE_WRITE_FAILED') from None
    claim.record('container-scope',{'scopeSha256':hashlib.sha256(raw).hexdigest()})


def _claimed_container(claim,role):
    _claim_database_identity(claim)
    require(role in ('backend','minio'),'FORMAL_CONTAINER_ACTION_INVALID')
    event=_claim_event(claim,'container-scope');raw=claim._read(claim.root/'container-original.json')
    require(event['details']=={'scopeSha256':hashlib.sha256(raw).hexdigest()},'FORMAL_CONTAINER_SCOPE_CHANGED')
    try:scope=json.loads(raw)
    except ValueError:raise FormalSnapshotError('FORMAL_CONTAINER_SCOPE_CHANGED') from None
    require(type(scope) is dict and set(scope)=={'backend','minio'} and _canonical_bytes(scope)==raw,
            'FORMAL_CONTAINER_SCOPE_CHANGED')
    original=scope[role];current=inspect_formal_container(original['id'])
    require(_container_stable(current)==_container_stable(original),'FORMAL_CONTAINER_IDENTITY_CHANGED')
    require(scope['minio']['id']==json.loads(claim._plan)['minioContainerId'],'FORMAL_CONTAINER_BINDING_MISMATCH')
    return original,current,event['details']['scopeSha256']


def _completed_container_action(original,current,action,before):
    state=current['state']
    if action=='stop':
        require(not state['Running'] and state['ExitCode']==0 and
            state['StartedAt']==original['state']['StartedAt'] and state['FinishedAt']!=original['state']['FinishedAt'],
            'FORMAL_CONTAINER_NOT_GRACEFULLY_STOPPED')
    else:
        require(state['Running'] and state['StartedAt']!=before['StartedAt'],
                'FORMAL_CONTAINER_NOT_RESTORED')


def _container_action_intent(claim,role,action):
    original,current,digest=_claimed_container(claim,role)
    prefix=role+('-stop' if action=='stop' else '-restore')
    require(not any(e['step'] in (prefix+'-intent',role+'-stopped' if action=='stop' else role+'-restored','released') for e in claim.events),
            'FORMAL_CONTAINER_CLAIM_STAGE_INVALID')
    if action=='stop':
        _claim_event(claim,'db-fenced')
        if role=='minio':_claim_event(claim,'backend-stopped')
        require(current['state']['Running'] and current['state']['StartedAt']==original['state']['StartedAt'],
                'FORMAL_CONTAINER_RUNTIME_CHANGED')
    else:
        stopped=_claim_event(claim,role+'-stopped')
        require(not current['state']['Running'] and current['state']==stopped['details']['runtime'],
                'FORMAL_CONTAINER_RUNTIME_CHANGED')
        if role=='backend':_claim_event(claim,'minio-restored');_claim_event(claim,'db-restored')
    claim.record(prefix+'-intent',{'scopeSha256':digest,'before':current['state']})
    return original,current


def reconcile_claimed_container(claim,role,action):
    require(action in ('stop','start'),'FORMAL_CONTAINER_ACTION_INVALID')
    original,current,digest=_claimed_container(claim,role)
    prefix=role+('-stop' if action=='stop' else '-restore');intent=_claim_event(claim,prefix+'-intent')
    require(intent['details'].get('scopeSha256')==digest,'FORMAL_CONTAINER_SCOPE_CHANGED')
    _completed_container_action(original,current,action,intent['details']['before'])
    claim.record(role+('-stopped' if action=='stop' else '-restored'),
                 {'scopeSha256':digest,'runtime':current['state']})
    return current['state']


def stop_claimed_container(claim,role):
    original,current=_container_action_intent(claim,role,'stop')
    _,fresh,_=_claimed_container(claim,role)
    require(fresh['state']==current['state'],'FORMAL_CONTAINER_RUNTIME_CHANGED')
    run_formal_container_action('stop',original['id'])
    return reconcile_claimed_container(claim,role,'stop')


def restore_claimed_container(claim,role):
    original,current=_container_action_intent(claim,role,'start')
    _,fresh,_=_claimed_container(claim,role)
    require(fresh['state']==current['state'],'FORMAL_CONTAINER_RUNTIME_CHANGED')
    run_formal_container_action('start',original['id'])
    return reconcile_claimed_container(claim,role,'start')


def observe_stopped_object_containers(records,source_root,bound_container_id):
    """Validate captured Docker records only; host/admin writers remain unproven.

    A caller must independently obtain, bind and reread actual Docker records
    throughout capture, retain its exclusive maintenance ownership, and fence
    host processes before declaring a complete barrier. This never stops actors.
    """
    def path(value):
        require(type(value) is str and value.startswith('/') and '\\' not in value and
                '\0' not in value and all(p not in ('.','..') for p in value.split('/')),
                'FORMAL_CONTAINER_MOUNT_INVALID')
        return PurePosixPath(value)
    root=path(source_root)
    require(type(bound_container_id) is str and re.fullmatch('[0-9a-f]{64}',bound_container_id),
            'FORMAL_CONTAINER_ID_INVALID')
    require(type(records) is list and records,'FORMAL_CONTAINER_INVENTORY_MISSING')
    seen=set();bound=None
    for record in records:
        require(type(record) is dict,'FORMAL_CONTAINER_RECORD_INVALID')
        identity=record.get('id');state=record.get('state');mounts=record.get('mounts')
        require(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity) and identity not in seen,
                'FORMAL_CONTAINER_ID_INVALID');seen.add(identity)
        require(type(state) is dict and type(state.get('Running')) is bool and
                type(state.get('ExitCode')) is int and type(state.get('OOMKilled')) is bool and
                type(mounts) is list and type(record.get('privileged')) is bool,
                'FORMAL_CONTAINER_RECORD_INVALID')
        caps=record.get('capAdd')
        require(caps is None or (type(caps) is list and all(type(c) is str for c in caps)),
                'FORMAL_CONTAINER_RECORD_INVALID')
        if identity==bound_container_id:
            require(record.get('name')=='/ragflow_compose-minio-1','FORMAL_CONTAINER_BINDING_MISMATCH')
            require(not state['Running'] and state['ExitCode']==0 and not state['OOMKilled'],
                    'FORMAL_MINIO_NOT_GRACEFULLY_STOPPED')
            require(any(m.get('Source')==source_root and m.get('Destination')=='/data' and m.get('RW') is True
                        for m in mounts if type(m) is dict),'FORMAL_CONTAINER_BINDING_MISMATCH')
            bound=identity
        if state['Running']:
            require(not record['privileged'] and not any(c.upper() in ('SYS_ADMIN','ALL') for c in (caps or [])),
                    'FORMAL_PRIVILEGED_WRITER_RUNNING')
        for mount in mounts:
            require(type(mount) is dict and type(mount.get('RW')) is bool,'FORMAL_CONTAINER_MOUNT_INVALID')
            mounted=path(mount.get('Source'))
            if state['Running']:
                # Socket access permits restarting source writers even if the
                # socket bind itself is read-only.
                require(mounted not in (PurePosixPath('/var/run/docker.sock'),PurePosixPath('/run/docker.sock')),
                        'FORMAL_DOCKER_CONTROL_WRITER_RUNNING')
                overlap=mounted==root or mounted in root.parents or root in mounted.parents
                require(not (mount['RW'] and overlap),'FORMAL_OBJECT_MOUNT_WRITER_RUNNING')
    require(bound is not None,'FORMAL_BOUND_CONTAINER_MISSING')
    return {'boundContainerId':bound,'sourceRoot':source_root,'observedContainers':len(records),
            'hostWritersVerified':False}


def collect_docker_barrier_records():
    """Collect only non-secret Docker fields, never Config.Env or command args."""
    def command(args):
        try:result=subprocess.run(['docker',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=observation_timeout(30),check=False)
        except (OSError,subprocess.TimeoutExpired):raise FormalSnapshotError('FORMAL_DOCKER_OBSERVATION_FAILED') from None
        observation_timeout(30)
        require(result.returncode==0 and len(result.stdout)<=1024*1024,'FORMAL_DOCKER_OBSERVATION_FAILED')
        return result.stdout.decode('utf-8',errors='strict')
    try:
        ids=command(['ps','-aq','--no-trunc']).splitlines()
        require(ids and len(ids)<=1000 and all(re.fullmatch('[0-9a-f]{64}',identity) for identity in ids),
                'FORMAL_DOCKER_INVENTORY_INVALID')
        template='{"id":{{json .Id}},"name":{{json .Name}},"state":{{json .State}},"mounts":{{json .Mounts}},"privileged":{{json .HostConfig.Privileged}},"capAdd":{{json .HostConfig.CapAdd}}}'
        rows=command(['inspect','--format',template,*ids]).splitlines()
        records=[json.loads(row) for row in rows]
        require(len(records)==len(ids) and set(r.get('id') for r in records)==set(ids),
                'FORMAL_DOCKER_INVENTORY_INVALID')
        require(set(command(['ps','-aq','--no-trunc']).splitlines())==set(ids),'FORMAL_DOCKER_INVENTORY_CHANGED')
        return records
    except (UnicodeError,ValueError,TypeError,AttributeError):
        raise FormalSnapshotError('FORMAL_DOCKER_INVENTORY_INVALID') from None


def observe_claimed_capture_barrier(claim,mysql,*,dump_in_progress=False):
    def stage():
        claim.assert_owned()
        require(not any(e['step'].endswith('-restore-intent') or e['step'].endswith('-restored') or
            e['step'] in ('released','shared-recovery-intent','ingress-recovery-intent','ingress-recovery-permitted')
            for e in claim.events),'FORMAL_CAPTURE_CLAIM_STAGE_INVALID')
    stage()
    identity,original,digest=_claimed_database_original(claim)
    held=_claim_event(claim,'db-fenced')
    require(held['details'].get('originalSha256')==digest and
        not any(e['step'].endswith('-restore-intent') or e['step'].endswith('-restored') or
                e['step']=='released' for e in claim.events),'FORMAL_CAPTURE_CLAIM_STAGE_INVALID')
    require(_database_flags(mysql,identity)=={'serverUuid':identity,'readOnly':1,'superReadOnly':1},
            'FORMAL_DATABASE_NOT_QUIESCENT')
    stage()
    observe_database_barrier(mysql,dump_in_progress=dump_in_progress)
    stage()
    for role in ('backend','minio'):
        stopped=_claim_event(claim,role+'-stopped')
        original_container,current,scope_digest=_claimed_container(claim,role)
        require(stopped['details'].get('scopeSha256')==scope_digest and
            current['state']==stopped['details'].get('runtime') and not current['state']['Running'],
            'FORMAL_CAPTURE_CONTAINER_CHANGED')
        stage()


def probe_claimed_database_rejection(claim,mysql,database,table,column,*,phase):
    """Durable before/after probe; interruption cannot replay a SQL action.

    This finite evidence remains pending object/host lifetime writer proof.
    """
    require(phase in ('before','after'),'FORMAL_DATABASE_PROBE_PHASE_INVALID')
    claim.assert_owned();binding=json.loads(claim._plan);step='db-probe-'+phase
    require(not any(e['step'] in (step,step+'-intent','released') for e in claim.events),
            'FORMAL_DATABASE_PROBE_ALREADY_STARTED')
    require(all(type(value) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',value)
        for value in (database,table,column)),'FORMAL_MYSQL_PROBE_IDENTIFIER_INVALID')
    payload_digest=None
    if phase=='before':
        require(not any(e['step'] in ('capture-intent','captured') for e in claim.events),
                'FORMAL_DATABASE_PROBE_PHASE_INVALID')
    else:
        before=_claim_event(claim,'db-probe-before')
        before_raw=_existing_file(claim.root/'database-rejection-before.json').read_bytes()
        require(len(before_raw)<=16384 and hashlib.sha256(before_raw).hexdigest()==before['details'].get('receiptSha256'),
                'FORMAL_DATABASE_PROBE_RECEIPT_CHANGED')
        before_receipt=json.loads(before_raw)
        require(all(before_receipt.get(k)==v for k,v in {'database':database,'table':table,'column':column,
            'databaseUuid':binding['databaseUuid'],'operationId':binding['operationId'],
            'sourceFingerprint':binding['sourceFingerprint']}.items()),'FORMAL_DATABASE_PROBE_BINDING_CHANGED')
        captured=_claim_event(claim,'captured')
        payload=_existing_file(claim.root/'payload/040-payload.json').read_bytes()
        require(len(payload)<=16384,'FORMAL_CAPTURE_RECEIPT_INVALID')
        payload_digest=hashlib.sha256(payload).hexdigest()
        require(captured['details'].get('payloadReceiptSha256')==payload_digest,'FORMAL_CAPTURE_RECEIPT_CHANGED')
    observe_claimed_capture_barrier(claim,mysql)
    scope={'phase':phase,'database':database,'table':table,'column':column,'operationId':binding['operationId'],
        'databaseUuid':binding['databaseUuid'],'sourceFingerprint':binding['sourceFingerprint'],
        'payloadReceiptSha256':payload_digest}
    claim.record(step+'-intent',scope)
    observe_claimed_capture_barrier(claim,mysql)
    probe_started=datetime.now(timezone.utc)
    probe=mysql.probe_rejected_zero_row_update(database,table,column)
    probe_finished=datetime.now(timezone.utc)
    require(type(probe) is dict and set(probe)=={'result','mysqlErrorNumber','statementSha256','observedAt'} and
        probe['result']=='REJECTED' and type(probe['mysqlErrorNumber']) is int and probe['mysqlErrorNumber']==1290 and
        type(probe['statementSha256']) is str and re.fullmatch('[0-9a-f]{64}',probe['statementSha256']) and
        type(probe['observedAt']) is str,'FORMAL_DATABASE_PROBE_RESULT_INVALID')
    expected_sql='UPDATE `'+database+'`.`'+table+'` SET `'+column+'`=`'+column+'` WHERE 1=0;'
    require(probe['statementSha256']==hashlib.sha256(expected_sql.encode()).hexdigest(),
            'FORMAL_DATABASE_PROBE_STATEMENT_CHANGED')
    try:
        observed_at=datetime.fromisoformat(probe['observedAt'])
    except ValueError as error:
        raise FormalSnapshotError('FORMAL_DATABASE_PROBE_TIME_INVALID') from error
    require(observed_at.tzinfo is not None and observed_at.utcoffset() is not None,
            'FORMAL_DATABASE_PROBE_TIME_INVALID')
    require(probe_started<=observed_at<=probe_finished,'FORMAL_DATABASE_PROBE_TIME_INVALID')
    observe_claimed_capture_barrier(claim,mysql)
    raw=_canonical_bytes(dict(scope,probe=probe,state='DATABASE_REJECTED_PENDING_HOST_OBJECT_PROOF'))
    path=safe_file(claim.root/('database-rejection-'+phase+'.json'))
    with path.open('xb') as output:
        os.chmod(path,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
    _sync_directory(claim.root)
    observe_claimed_capture_barrier(claim,mysql)
    claim.record(step,{'receiptSha256':hashlib.sha256(raw).hexdigest()})
    return json.loads(raw)


def capture_claimed_formal_payload(claim,mysql,database,source_root,*,filesystem_fence=None):
    """Bind retained claim throughout finite capture; no full consistency claim."""
    claim.assert_owned()
    require(not any(e['step'] in ('ingress-recovery-intent','ingress-recovery-permitted')
                    for e in claim.events),'FORMAL_CAPTURE_CLAIM_STAGE_INVALID')
    _claim_database_identity(claim)
    if filesystem_fence is not None:
        require(type(filesystem_fence) is dict and set(filesystem_fence)=={'mount','binding','seconds'} and
            type(filesystem_fence['binding']) is dict,'FORMAL_CAPTURE_FILESYSTEM_SCOPE_INVALID')
        require(filesystem_fence['binding'].get('operationId')==json.loads(claim._plan)['operationId'],
                'FORMAL_CAPTURE_FILESYSTEM_OPERATION_CHANGED')
        _require_native_physical_runtime()
    for step in ('db-fenced','backend-stopped','minio-stopped'):_claim_event(claim,step)
    require(not any(e['step'] in ('capture-intent','captured','released') or
                    e['step'].endswith('-restore-intent') for e in claim.events),
            'FORMAL_CAPTURE_CLAIM_STAGE_INVALID')
    observe_claimed_capture_barrier(claim,mysql)
    target=safe_file(claim.root/'payload');identity=json.loads(claim._plan)['minioContainerId']
    claim.record('capture-intent',{'database':database,'sourceRoot':str(Path(source_root).absolute()),
                                 'destination':'payload','minioContainerId':identity})
    options={'barrier_guard':lambda:observe_claimed_capture_barrier(claim,mysql,dump_in_progress=True),
        'native_guard':claim.assert_owned}
    if filesystem_fence is not None:options['filesystem_fence']=filesystem_fence
    result=capture_formal_payload(mysql,database,source_root,target,identity,**options)
    observe_claimed_capture_barrier(claim,mysql)
    receipt=target/'040-payload.json';raw=_existing_file(receipt).read_bytes()
    require(len(raw)<=16384,'FORMAL_CAPTURE_RECEIPT_INVALID')
    claim.record('captured',{'payloadReceiptSha256':hashlib.sha256(raw).hexdigest(),
                            'state':'CAPTURED_PENDING_FULL_BARRIER_PROOF'})
    return result


def _capture_native_physical(control,mount,binding,source_root,destination,seconds,*,guard=None):
    import importlib.util
    require(callable(guard),'FORMAL_CAPTURE_NATIVE_OWNER_REQUIRED')
    deadline=observation_deadline.get()
    if deadline is not None:
        if deadline-time.monotonic()<=seconds+20:
            raise NativeCaptureNotStarted('FORMAL_DATA_DEADLINE')
    spec=importlib.util.spec_from_file_location('formal_capture_native_watchdog',
        Path(__file__).with_name('formal_filesystem_watchdog.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    options={'guard':guard}
    if deadline is not None:options['deadline']=deadline
    try:return module.capture_physical_with_native_fence(control,mount,binding,source_root,destination,seconds,**options)
    except Exception as error:
        # Dynamically loaded WatchdogError has a distinct class identity.
        if isinstance(error,module.WatchdogError):
            code=error.code
            require(type(code) is str and re.fullmatch('WATCHDOG_[A-Z_]+',code),'FORMAL_CAPTURE_NATIVE_FAILED')
            raise FormalSnapshotError(code) from None
        raise


def _require_native_physical_runtime():
    import importlib.util
    spec=importlib.util.spec_from_file_location('formal_capture_runtime_preflight',
        Path(__file__).with_name('formal_filesystem_watchdog.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    try:module.require_native_runtime()
    except module.WatchdogError as error:raise FormalSnapshotError(error.code) from None


def capture_formal_payload(mysql,database,source_root,destination,bound_container_id,*,barrier_guard=None,filesystem_fence=None,native_guard=None):
    """Finite sequential capture under externally retained maintenance barriers.

    No barrier acquisition/release or restart is implicit. Partial output cannot
    be consumed as recoveryManifest/consistency/producer-completion evidence.
    """
    require(barrier_guard is None or callable(barrier_guard),'FORMAL_CAPTURE_GUARD_INVALID')
    require(filesystem_fence is None or (type(filesystem_fence) is dict and
        set(filesystem_fence)=={'mount','binding','seconds'} and type(filesystem_fence['mount']) is str and
        type(filesystem_fence['binding']) is dict and type(filesystem_fence['seconds']) is int and
        1<=filesystem_fence['seconds']<=300),'FORMAL_CAPTURE_FILESYSTEM_SCOPE_INVALID')
    if filesystem_fence is not None:
        require(callable(native_guard),'FORMAL_CAPTURE_NATIVE_OWNER_REQUIRED')
        try:_require_native_physical_runtime()
        except Exception as error:
            code=getattr(error,'code',None)
            if type(code) is str and re.fullmatch('WATCHDOG_[A-Z_]+',code):
                raise FormalSnapshotError(code) from None
            raise
    if barrier_guard is not None:barrier_guard()
    target=safe_file(destination)
    require(Path(source_root).absolute()!=target and Path(source_root).absolute() not in target.parents,
            'FORMAL_PHYSICAL_DESTINATION_INVALID')
    target.mkdir(mode=0o700)
    stage='START'
    def journal(name,data):
        file=safe_file(target/name)
        with file.open('xb') as output:
            os.chmod(file,0o600)
            output.write((json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8'))
            output.flush();os.fsync(output.fileno())
    def observe(*,dump_in_progress=False):
        if barrier_guard is not None:barrier_guard()
        db=observe_database_barrier(mysql,dump_in_progress=dump_in_progress)
        records=collect_docker_barrier_records()
        containers=observe_stopped_object_containers(records,str(Path(source_root).absolute()),bound_container_id)
        frozen=[]
        for record in sorted(records,key=lambda r:r['id']):
            item=dict(record)
            # Exclude live health-log entries, retain container lifetime/state.
            item['state']={key:record['state'].get(key) for key in
                ('Running','ExitCode','OOMKilled','Pid','Restarting','Dead','StartedAt','FinishedAt')}
            frozen.append(item)
        digest=hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
        return {'database':db,'containers':containers,'dockerRecordsDigest':digest}
    try:
        journal('000-started.json',{'state':'CAPTURING','observedAt':datetime.now(timezone.utc).isoformat()})
        stage='INITIAL_BARRIER';initial=observe();journal('010-initial-barrier.json',initial)
        stage='SQL_DUMP'
        if barrier_guard is not None:barrier_guard()
        def dump_guard():
            current=observe(dump_in_progress=True)
            require(current['containers']==initial['containers'] and
                current['dockerRecordsDigest']==initial['dockerRecordsDigest'],
                'FORMAL_CAPTURE_BARRIER_CHANGED')
        sql=target/'database.sql.gz';dump=mysql.dump(database,sql,guard=dump_guard)
        actual,size=_hash_object(sql,guard=dump_guard)
        require(type(dump) is dict and dump.get('sha256')==actual[7:] and dump.get('bytes')==size,
                'FORMAL_CAPTURE_SQL_DIGEST_MISMATCH')
        stage='POST_SQL_BARRIER';post_sql=observe();require(post_sql==initial,'FORMAL_CAPTURE_BARRIER_CHANGED')
        journal('020-sql.json',{'dump':dump,'barrier':post_sql})
        stage='PHYSICAL_COPY'
        if barrier_guard is not None:barrier_guard()
        native=None
        if filesystem_fence is None:
            physical=copy_physical_minio_tree(source_root,target/'minio-physical')
        else:
            # No DB/Docker calls occur inside the explicit native lifecycle.
            # Their own data files may be on the same frozen block device.
            native=_capture_native_physical(target/'native-fence',filesystem_fence['mount'],
                filesystem_fence['binding'],source_root,target/'minio-physical',filesystem_fence['seconds'],guard=native_guard)
            require(type(native) is dict and native.get('state')=='RAW_CAPTURED_AND_THAWED_PENDING_FORMAL_BARRIERS' and
                    native.get('productionEvidence') is False,'FORMAL_CAPTURE_NATIVE_NOT_VERIFIED')
            physical=native['physical']
        stage='FINAL_BARRIER';final=observe();require(final==initial,'FORMAL_CAPTURE_BARRIER_CHANGED')
        journal('030-final-barrier.json',final)
        final_digest,final_size=_hash_object(sql,guard=dump_guard)
        require(final_digest==actual and final_size==size,'FORMAL_CAPTURE_SQL_CHANGED')
        result={'state':'CAPTURED_PENDING_FULL_BARRIER_PROOF','database':dump,'physical':physical,
                'hostWritersVerified':False,'capturedAt':datetime.now(timezone.utc).isoformat()}
        if native is not None:result['nativeCapture']=native
        if barrier_guard is not None:barrier_guard()
        journal('040-payload.json',result)
        return result
    except Exception as error:
        native_code=getattr(error,'code',None)
        code=error.code if isinstance(error,FormalSnapshotError) else (
            native_code if type(native_code) is str and re.fullmatch('WATCHDOG_[A-Z_]+',native_code)
            else 'FORMAL_CAPTURE_UNEXPECTED_FAILURE')
        try:journal('900-failed.json',{'state':'FAILED_RETAINED','stage':stage,'code':code})
        except OSError:raise FormalSnapshotError('FORMAL_CAPTURE_FAILURE_JOURNAL_IO_FAILED') from None
        raise FormalSnapshotError(code) from None


def _existing_file(path):
    path=Path(path).absolute()
    for part in [path,*path.parents]:
        require(not part.is_symlink() and part.resolve()==part,'FORMAL_OBJECT_PATH_INVALID')
    require(path.is_file(),'FORMAL_OBJECT_FILE_MISSING')
    return path


def current_owner_guard(guard,*,code):
    """Owner-thread assertion, with a five-second observation budget.

    The trusted owner supplies the callback. This is no independent grant or
    host fence; callback implementations must honor bounded observation calls.
    """
    require(callable(guard),code)
    now=time.monotonic();existing=observation_deadline.get()
    deadline=min(now+5,existing) if existing is not None else now+5
    require(now<deadline,'FORMAL_OBSERVATION_DEADLINE_EXCEEDED')
    token=observation_deadline.set(deadline)
    try:guard()
    finally:observation_deadline.reset(token)
    require(time.monotonic()<deadline,'FORMAL_OBSERVATION_DEADLINE_EXCEEDED')


def _hash_object(path,*,guard=None):
    require(guard is None or callable(guard),'FORMAL_PHYSICAL_LEASE_GUARD_INVALID')
    def budget():
        observation_timeout(7200)
        if guard is not None:guard()
    budget()
    path=_existing_file(path);before=path.stat();digest=hashlib.sha256();size=0
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            budget()
            digest.update(chunk);size+=len(chunk)
    after=_existing_file(path).stat()
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),
            'FORMAL_OBJECT_CHANGED')
    budget()
    return 'sha256:'+digest.hexdigest(),size


def copy_physical_minio_tree(source_root,destination,*,timeout=7200,lease_guard=None):
    """Copy private raw MinIO bytes, retaining failed artifacts.

    Requires independently retained stopped-container/host barriers. Content
    stability checks are observations, not proof of a hard host-writer fence.
    No source deletion, overwrite, automatic resume or success attestation.
    Optional lease guard is called during traversal/chunk copy and before
    returning. It is an expiry refusal, never a kernel-fence success proof.
    """
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    def directory(value):
        value=Path(value).absolute()
        for part in [value,*value.parents]:
            require(part.is_dir() and not part.is_symlink() and part.resolve()==part,
                    'FORMAL_PHYSICAL_PATH_INVALID')
        return value
    require(type(timeout) is int and 0<timeout<=7200,'FORMAL_PHYSICAL_TIMEOUT_INVALID')
    require(lease_guard is None or callable(lease_guard),'FORMAL_PHYSICAL_LEASE_GUARD_INVALID')
    started=time.monotonic()
    def budget():
        require(time.monotonic()-started<timeout,'FORMAL_PHYSICAL_COPY_TIMEOUT')
        if lease_guard is not None:lease_guard()
    def fingerprint(file):
        info=file.lstat()
        require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),'FORMAL_PHYSICAL_ENTRY_INVALID')
        return (info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns)
    def scan(root):
        result={}
        for current,dirs,files in os.walk(root,followlinks=False):
            budget();directory(current)
            for name in sorted(dirs+files):
                file=Path(current)/name;result[file.relative_to(root).as_posix()]=fingerprint(file)
                require(len(result)<=500000,'FORMAL_PHYSICAL_TREE_TOO_LARGE')
        return result
    try:
        budget()
        source=directory(source_root);target=safe_file(destination)
        require(source!=target and source not in target.parents and target not in source.parents,
                'FORMAL_PHYSICAL_DESTINATION_INVALID')
        before=scan(source)
        require(before and any(stat.S_ISREG(v[2]) for v in before.values()),'FORMAL_PHYSICAL_TREE_EMPTY')
        if output_budget is None:target.mkdir(mode=0o700)
        else:output_budget.mkdir(target)
        rows=[];count=0;total=0
        for relative,identity in sorted(before.items()):
            budget();original=source/relative;copy=target/relative
            require(fingerprint(original)==identity,'FORMAL_PHYSICAL_SOURCE_CHANGED')
            if stat.S_ISDIR(identity[2]):
                if output_budget is None:copy.mkdir(mode=0o700)
                else:output_budget.mkdir(copy)
                continue
            digest=hashlib.sha256();size=0
            with _existing_file(original).open('rb') as input_file, \
                    (copy.open('xb') if output_budget is None else output_budget.open(copy,'physical')) as output:
                os.chmod(copy,0o600)
                for chunk in iter(lambda:input_file.read(1024*1024),b''):
                    budget();output.write(chunk);digest.update(chunk);size+=len(chunk)
                output.flush();os.fsync(output.fileno())
            require(fingerprint(original)==identity and size==identity[3],'FORMAL_PHYSICAL_SOURCE_CHANGED')
            expected='sha256:'+digest.hexdigest()
            # The complete destination readback below validates these written bytes.
            rows.append((relative,expected,size));count+=1;total+=size
        require(scan(source)==before,'FORMAL_PHYSICAL_SOURCE_CHANGED')
        copied=scan(target)
        require(set(copied)==set(before) and all(
                stat.S_IFMT(copied[name][2])==stat.S_IFMT(identity[2]) and
                (not stat.S_ISREG(identity[2]) or copied[name][3]==identity[3])
                for name,identity in before.items()),'FORMAL_PHYSICAL_COPY_MISMATCH')
        chain=hashlib.sha256()
        for relative,identity in sorted(before.items()):
            if stat.S_ISDIR(identity[2]):
                chain.update((json.dumps(['directory',relative],ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
        # Rehash the source after all copy operations, including earlier files.
        for relative,expected,size in rows:
            budget();actual,actual_size=_hash_object(source/relative,guard=budget)
            require(actual==expected and actual_size==size,'FORMAL_PHYSICAL_SOURCE_CHANGED')
            chain.update((json.dumps([relative,expected,size],ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
        require(scan(source)==before,'FORMAL_PHYSICAL_SOURCE_CHANGED')
        # A previously copied file may change while later files are copied or
        # the source is reread. Reopen every destination byte after that work;
        # counts and lengths alone are not a full readback.
        require(scan(target)==copied,'FORMAL_PHYSICAL_COPY_MISMATCH')
        for relative,expected,size in rows:
            budget();actual,actual_size=_hash_object(target/relative,guard=budget)
            require(actual==expected and actual_size==size,'FORMAL_PHYSICAL_COPY_MISMATCH')
        require(scan(target)==copied,'FORMAL_PHYSICAL_COPY_MISMATCH')
        require(scan(source)==before,'FORMAL_PHYSICAL_SOURCE_CHANGED')
        directory(source);directory(target)
        budget()
        return {'physicalTreeDigest':chain.hexdigest(),'fileCount':count,'totalBytes':total,
                'hostWritersVerified':False}
    except OSError:raise FormalSnapshotError('FORMAL_PHYSICAL_COPY_IO_FAILED') from None


def verify_physical_minio_tree(root,expected,*,timeout=7200,lease_guard=None):
    """Verify retained raw capture bytes; no host-writer/finality assertion."""
    require(type(expected) is dict and set(expected)=={'physicalTreeDigest','fileCount','totalBytes','hostWritersVerified'} and
        type(expected['physicalTreeDigest']) is str and re.fullmatch('[0-9a-f]{64}',expected['physicalTreeDigest']) and
        type(expected['fileCount']) is int and expected['fileCount']>0 and
        type(expected['totalBytes']) is int and expected['totalBytes']>=0 and expected['hostWritersVerified'] is False,
        'FORMAL_PHYSICAL_RECEIPT_INVALID')
    require(type(timeout) is int and 0<timeout<=7200,'FORMAL_PHYSICAL_TIMEOUT_INVALID')
    require(lease_guard is None or callable(lease_guard),'FORMAL_PHYSICAL_LEASE_GUARD_INVALID')
    root=Path(root).absolute();started=time.monotonic()
    def budget():
        observation_timeout(timeout)
        require(time.monotonic()-started<timeout,'FORMAL_PHYSICAL_VERIFY_TIMEOUT')
        if lease_guard is not None:lease_guard()
    def scan():
        for part in [root,*root.parents]:
            require(part.is_dir() and not part.is_symlink() and part.resolve()==part,'FORMAL_PHYSICAL_PATH_INVALID')
        result={}
        for current,dirs,files in os.walk(root,followlinks=False):
            budget()
            for name in sorted(dirs+files):
                path=Path(current)/name;value=path.lstat()
                require(stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode),'FORMAL_PHYSICAL_ENTRY_INVALID')
                result[path.relative_to(root).as_posix()]=(value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
                require(len(result)<=500000,'FORMAL_PHYSICAL_TREE_TOO_LARGE')
        return result
    try:
        before=scan();digest=hashlib.sha256();count=total=0
        for relative,value in sorted(before.items()):
            if stat.S_ISDIR(value[2]):
                digest.update((json.dumps(['directory',relative],ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
        for relative,value in sorted(before.items()):
            if stat.S_ISREG(value[2]):
                budget();sha,size=_hash_object(root/relative,guard=budget);count+=1;total+=size
                digest.update((json.dumps([relative,sha,size],ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
        require(scan()==before,'FORMAL_PHYSICAL_SOURCE_CHANGED')
        actual={'physicalTreeDigest':digest.hexdigest(),'fileCount':count,'totalBytes':total,'hostWritersVerified':False}
        require(actual==expected,'FORMAL_PHYSICAL_CAPTURE_CHANGED');budget();return actual
    except OSError:raise FormalSnapshotError('FORMAL_PHYSICAL_VERIFY_IO_FAILED') from None


def prepare_minio_replica_copy(capture_root,replica_root,expected,*,timeout=7200,lease_guard=None):
    """Raw capture remains unmounted; only this new disposable copy may start."""
    verify_physical_minio_tree(capture_root,expected,timeout=timeout,lease_guard=lease_guard)
    actual=copy_physical_minio_tree(capture_root,replica_root,timeout=timeout,lease_guard=lease_guard)
    require(actual==expected,'FORMAL_PHYSICAL_REPLICA_MISMATCH')
    verify_physical_minio_tree(capture_root,expected,timeout=timeout,lease_guard=lease_guard)
    verify_physical_minio_tree(replica_root,expected,timeout=timeout,lease_guard=lease_guard)
    return actual


def verify_object_inventory(inventory_path,repository_root,bucket):
    """Hash actual local recovery bytes, including reused objects.

    This cannot prove live MinIO fencing or generate COMPLETE/FINALIZED.
    The caller must hold the source/object barrier throughout collection.
    """
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,'FORMAL_INVENTORY_DUPLICATE_KEY');value[key]=item
        return value
    try:
        path=_existing_file(inventory_path)
        require(path.stat().st_size<=1024*1024,'FORMAL_INVENTORY_TOO_LARGE')
        with path.open('rb') as source:raw=source.read(1024*1024+1)
        require(len(raw)<=1024*1024,'FORMAL_INVENTORY_TOO_LARGE')
        inventory=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=pairs)
        require(type(inventory) is dict,'FORMAL_INVENTORY_INVALID')
        root=Path(repository_root).absolute()
        for part in [root,*root.parents]:
            require(part.is_dir() and not part.is_symlink() and part.resolve()==part,'FORMAL_OBJECT_PATH_INVALID')
        require(inventory.get('objectStoreRoot')==str(root),'FORMAL_INVENTORY_ROOT_MISMATCH')
        require(type(bucket) is str and bucket and inventory.get('bucket')==bucket,'FORMAL_INVENTORY_BUCKET_MISMATCH')
        objects=inventory.get('objects')
        require(type(objects) is list and objects,'FORMAL_INVENTORY_EMPTY')
        seen=set();verified=[];total=0
        for item in objects:
            require(type(item) is dict,'FORMAL_INVENTORY_OBJECT_INVALID')
            name=item.get('path')
            require(type(name) is str and name and '\\' not in name and
                    not name.startswith('/') and all(p not in ('','.', '..') for p in name.split('/')) and
                    ':' not in name and '\0' not in name,'FORMAL_OBJECT_PATH_INVALID')
            require(name not in seen,'FORMAL_OBJECT_DUPLICATE');seen.add(name)
            status=item.get('status')
            require(status in ('active','deleted'),'FORMAL_OBJECT_STATUS_INVALID')
            if status=='deleted':continue
            expected=item.get('sha256');size=item.get('size')
            require(type(expected) is str and re.fullmatch(r'sha256:[0-9a-f]{64}',expected),'FORMAL_OBJECT_DIGEST_INVALID')
            digest=expected[7:];relative=f'sha256/{digest[:2]}/{digest}'
            require(item.get('repositoryPath')==relative and item.get('repositoryKey')==expected,'FORMAL_OBJECT_REPOSITORY_INVALID')
            require(type(size) is int and size>=0,'FORMAL_OBJECT_SIZE_INVALID')
            actual,observed_size=_hash_object(root/relative)
            require(actual==expected and observed_size==size,'FORMAL_OBJECT_CONTENT_MISMATCH')
            total+=size;verified.append({'path':name,'sha256':actual,'bytes':size,'repositoryPath':relative})
        require(verified,'FORMAL_INVENTORY_EMPTY')
        with _existing_file(path).open('rb') as source:current=source.read(1024*1024+1)
        require(current==raw,'FORMAL_INVENTORY_CHANGED')
        for part in [root,*root.parents]:
            require(part.is_dir() and not part.is_symlink() and part.resolve()==part,'FORMAL_OBJECT_PATH_INVALID')
        return {'inventorySha256':hashlib.sha256(raw).hexdigest(),'objectCount':len(verified),
                'totalBytes':total,'objects':verified}
    except (UnicodeError,ValueError,TypeError):raise FormalSnapshotError('FORMAL_INVENTORY_INVALID') from None
    except OSError:raise FormalSnapshotError('FORMAL_INVENTORY_IO_FAILED') from None


class PrivateDockerMySql:
    """Password enters the container over stdin, never argv or returned errors."""
    def __init__(self,container,password,*,timeout=1800):
        require(type(container) is str and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}',container),'FORMAL_MYSQL_CONTAINER_INVALID')
        require(type(password) is str and password and not any(c in password for c in '\r\n\0'),'FORMAL_MYSQL_CREDENTIAL_INVALID')
        require(type(timeout) is int and 0<timeout<=7200,'FORMAL_MYSQL_TIMEOUT_INVALID')
        self.container=container;self._password=password;self.timeout=timeout

    def _command(self,program,arguments):
        # Fixed shell entry, credential read with backslash interpretation disabled.
        script=('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
                'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
                'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec '+program+' "$@"')
        return ['docker','exec','-i',self.container,'sh','-ec',script,'formal-mysql',
                '--no-defaults','--protocol=SOCKET',*arguments]

    def ready(self):
        """Read-only startup probe; only explicit missing/refused socket is pending."""
        seconds=observation_timeout(min(self.timeout,5))
        program='timeout --signal=TERM --kill-after=1 '+str(math.ceil(seconds))+'s mysql'
        try:
            result=subprocess.run(self._command(program,['-uroot','--batch','--raw','--skip-column-names']),
                input=(self._password+'\nSELECT 1;').encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=seconds,check=False)
        except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_MYSQL_READINESS_TIMEOUT') from None
        except OSError:raise FormalSnapshotError('FORMAL_MYSQL_EXECUTABLE_UNAVAILABLE') from None
        if result.returncode==0:
            require(result.stdout==b'1\n' and result.stderr==b'','FORMAL_MYSQL_READINESS_FAILED')
            return True
        pending=result.stdout==b'' and re.fullmatch(
            rb"ERROR 2002 \(HY000\): Can't connect to local MySQL server through socket '/[^'\r\n]+' \((?:2|111)\)\r?\n?",
            result.stderr)
        require(pending is not None and pending is not False,'FORMAL_MYSQL_READINESS_FAILED')
        return False

    def query(self,sql):
        require(type(sql) is str and sql and '\0' not in sql,'FORMAL_MYSQL_QUERY_INVALID')
        seconds=observation_timeout(self.timeout)
        program=('timeout --signal=TERM --kill-after=5 '+str(math.ceil(seconds))+'s mysql'
                 if observation_deadline.get() is not None else 'mysql')
        try:
            result=subprocess.run(self._command(program,['-uroot','--batch','--raw','--skip-column-names',
                '--default-character-set=utf8mb4']),
                input=(self._password+'\n'+sql).encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=seconds,check=False)
        except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_MYSQL_QUERY_TIMEOUT') from None
        except OSError:raise FormalSnapshotError('FORMAL_MYSQL_EXECUTABLE_UNAVAILABLE') from None
        require(result.returncode==0,'FORMAL_MYSQL_QUERY_FAILED')
        try:return result.stdout.decode('utf-8',errors='strict')
        except UnicodeError:raise FormalSnapshotError('FORMAL_MYSQL_QUERY_ENCODING_INVALID') from None

    def probe_rejected_zero_row_update(self,database,table,column):
        """No affected rows/triggers; only exact read-only error proves rejection.

        Caller retains UUID/read_only/super_read_only ownership across probe;
        this result alone does not prove ongoing fencing or snapshot finality.
        """
        require(all(type(name) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',name)
                    for name in (database,table,column)),'FORMAL_MYSQL_PROBE_IDENTIFIER_INVALID')
        description=self.query('DESCRIBE `'+database+'`.`'+table+'`;')
        require(column in [line.split('\t')[0] for line in description.splitlines()],
                'FORMAL_MYSQL_PROBE_COLUMN_MISSING')
        sql='UPDATE `'+database+'`.`'+table+'` SET `'+column+'`=`'+column+'` WHERE 1=0;'
        # Pinned MySQL8.0.39 has no --no-login-paths option. Refuse login-file
        # inputs explicitly instead of allowing them to override stdin auth.
        seconds=observation_timeout(self.timeout)
        program=('timeout --signal=TERM --kill-after=5 '+str(math.ceil(seconds))+'s mysql'
                 if observation_deadline.get() is not None else 'mysql')
        script='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec '+program+' "$@"'
        command=['docker','exec','-i',self.container,'sh','-ec',script,'formal-mysql-probe',
            '--no-defaults','-uroot','--batch','--raw','--skip-column-names']
        try:
            result=subprocess.run(command,
                input=(self._password+'\n'+sql).encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=seconds,check=False)
        except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_MYSQL_PROBE_TIMEOUT') from None
        except OSError:raise FormalSnapshotError('FORMAL_MYSQL_EXECUTABLE_UNAVAILABLE') from None
        observation_timeout(self.timeout)
        require(result.returncode!=0,'FORMAL_MYSQL_WRITE_PROBE_ACCEPTED')
        require(result.stdout==b'' and len(result.stderr)<=16384 and
            re.fullmatch(rb'ERROR 1290 \(HY000\) at line 1: The MySQL server is running with the --(?:super-read-only|read-only) option so it cannot execute this statement\r?\n?',result.stderr),
            'FORMAL_MYSQL_REJECTION_NOT_PROVEN')
        return {'result':'REJECTED','mysqlErrorNumber':1290,'statementSha256':hashlib.sha256(sql.encode()).hexdigest(),
                'observedAt':datetime.now(timezone.utc).isoformat()}

    def dump(self,database,destination,*,guard=None):
        # Existing finite standalone entry; normal admitted capture uses dump_until.
        return self.dump_until(database,destination,guard=guard,
            deadline=time.monotonic()+observation_timeout(self.timeout))

    def dump_until(self,database,destination,*,guard,deadline):
        require(callable(guard),'FORMAL_MYSQL_DUMP_GUARD_REQUIRED')
        require(type(database) is str and re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}',database),'FORMAL_MYSQL_DATABASE_INVALID')
        require(type(deadline) in (int,float) and math.isfinite(deadline),
            'FORMAL_MYSQL_DUMP_DEADLINE_REQUIRED')
        outer=observation_deadline.get()
        if outer is not None:deadline=min(deadline,outer)
        from formal_capture_budget import active_budget
        output_budget=active_budget.get()
        if output_budget is not None:deadline=min(deadline,output_budget.deadline)
        require(time.monotonic()<deadline,'FORMAL_MYSQL_DUMP_TIMEOUT')
        token=observation_deadline.set(deadline)
        def remaining():
            seconds=deadline-time.monotonic()
            require(seconds>0,'FORMAL_MYSQL_DUMP_TIMEOUT')
            current_owner_guard(guard,code='FORMAL_MYSQL_DUMP_GUARD_REQUIRED')
            seconds=deadline-time.monotonic()
            require(seconds>0,'FORMAL_MYSQL_DUMP_TIMEOUT')
            return seconds
        try:
            return self._dump_current(database,destination,remaining)
        finally:observation_deadline.reset(token)

    def _dump_current(self,database,destination,remaining):
        """Compress the owned dump stream directly; publish only on real exit 0."""
        from formal_capture_budget import active_budget,drain_owned_process
        output_budget=active_budget.get()
        remaining()
        destination=safe_file(destination)
        pending=safe_file(destination.with_name(destination.name+'.pending'))
        checksum=hashlib.sha256();compressed_bytes=raw_bytes=0
        try:
            with (pending.open('xb') if output_budget is None else output_budget.open(pending,'sql-gzip')) as output:
                os.chmod(pending,0o600)
                class HashedOutput:
                    def write(self,block):
                        nonlocal compressed_bytes
                        remaining();size=output.write(block)
                        require(size==len(block),'FORMAL_MYSQL_DUMP_SHORT_WRITE')
                        checksum.update(block);compressed_bytes+=size
                        return size
                with gzip.GzipFile(fileobj=HashedOutput(),mode='wb',mtime=0,compresslevel=1) as compressed:
                    class DumpOutput:
                        def write(self,block):
                            nonlocal raw_bytes
                            remaining();size=compressed.write(block);raw_bytes+=size
                            return size
                    seconds=remaining()
                    end=time.monotonic()+seconds
                    program='timeout --signal=TERM --kill-after=5 '+str(math.ceil(seconds))+'s mysqldump'
                    process=subprocess.Popen(self._command(program,['-uroot','--single-transaction',
                        '--routines','--triggers','--events','--hex-blob','--set-gtid-purged=OFF',
                        '--default-character-set=utf8mb4',database]),
                        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    # The drain owns and reaps this exact client on every failure.
                    drain_owned_process(process,(self._password+'\n').encode('utf-8'),DumpOutput(),
                        guard=remaining,deadline=end)
                    require(process.returncode==0,'FORMAL_MYSQL_DUMP_FAILED')
                require(raw_bytes>0,'FORMAL_MYSQL_DUMP_EMPTY')
                output.flush();os.fsync(output.fileno());remaining()
            require(not destination.exists(),'FORMAL_SNAPSHOT_EXISTS')
            if output_budget is None:os.link(pending,destination)
            else:output_budget.link(pending,destination)
            if os.name=='posix':_sync_directory(destination.parent)
            remaining()
            if output_budget is None:pending.unlink()
            else:output_budget.unlink_complete(pending)
            remaining()
            return {'sha256':checksum.hexdigest(),'bytes':compressed_bytes}
        except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_MYSQL_DUMP_TIMEOUT') from None
        except OSError:raise FormalSnapshotError('FORMAL_MYSQL_DUMP_IO_FAILED') from None
