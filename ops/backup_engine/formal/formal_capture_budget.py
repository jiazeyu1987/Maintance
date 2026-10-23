"""Actual logical-output enforcement under one held claim.

Policy ceilings are enforced before writes, not estimates of compression or
image sizes. Free/allocated-space observations are NOT exclusive reservation.
Finite legacy component entry points remain separate; the new bounded owner
must explicitly activate this scope. No process-global monkeypatching.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import threading
import time

import formal_snapshot_linux as snapshot

COMPONENTS={'sql-raw','sql-gzip','physical','images','image-stderr','config','proof','scratch','control'}
active_budget=ContextVar('formal_capture_output_budget',default=None)


class CaptureBudget:
    def __init__(self,claim,policy_raw,expected_policy_sha256,*,attempt_id,
            source_context_sha256,guard,deadline):
        code='FORMAL_CAPTURE_OUTPUT_POLICY_INVALID'
        snapshot.require(type(claim) is snapshot.FormalMaintenanceClaim and os.name=='posix' and
            type(policy_raw) is bytes and 0<len(policy_raw)<=16384 and
            type(expected_policy_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_policy_sha256) and
            hashlib.sha256(policy_raw).hexdigest()==expected_policy_sha256 and
            type(attempt_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',attempt_id) and
            type(source_context_sha256) is str and re.fullmatch('[0-9a-f]{64}',source_context_sha256) and
            callable(guard) and type(deadline) in (int,float) and math.isfinite(deadline),code)
        try:policy=json.loads(policy_raw)
        except (ValueError,UnicodeError):raise snapshot.FormalSnapshotError(code) from None
        snapshot.require(type(policy) is dict and set(policy)=={'schemaVersion','componentBytes','totalBytes',
            'maxFiles','maxDirectories','maxPathBytes'} and
            policy['schemaVersion']=='release-formal-capture-output-policy/v1' and
            snapshot._canonical_bytes(policy)==policy_raw and type(policy['componentBytes']) is dict and
            set(policy['componentBytes'])==COMPONENTS and
            all(type(v) is int and 0<v<=2**50 for v in policy['componentBytes'].values()) and
            all(type(policy[k]) is int and 0<policy[k]<=2**50 for k in
                ('totalBytes','maxFiles','maxDirectories','maxPathBytes')),code)
        claim.assert_owned()
        self.claim=claim;self.root=claim.root;self.fd=claim._fd;self.plan=claim._plan
        self.lock=claim._lock;self.pid=os.getpid();self.thread=threading.get_ident()
        self.fd_identity=self._identity(os.fstat(self.fd))
        self.root_identity=self._identity(self.root.stat())
        self.policy=policy;self.raw=policy_raw;self.policy_sha=expected_policy_sha256
        self.attempt=attempt_id;self.source_sha=source_context_sha256;self.guard=guard
        outer=snapshot.observation_deadline.get()
        self.deadline=deadline if outer is None else min(deadline,outer)
        self.used={k:0 for k in COMPONENTS};self.written={k:0 for k in COMPONENTS}
        self.total=0;self.files={};self.directories=set();self.subtrees={}
        self.original_roots={self.root:(self.root_identity,None)}
        self.full_admission=None
        self.check()

    @staticmethod
    def _identity(info):return (info.st_dev,info.st_ino,info.st_uid,info.st_gid,info.st_mode)

    def _owned(self):
        code='FORMAL_CAPTURE_OUTPUT_OWNER_CHANGED'
        snapshot.require(os.getpid()==self.pid and threading.get_ident()==self.thread and
            time.monotonic()<self.deadline and self.claim._fd==self.fd and self.claim.root==self.root and
            self.claim._plan==self.plan and self.claim._lock==self.lock and
            snapshot._canonical_bytes(self.policy)==self.raw,code)
        self.claim.assert_owned()
        snapshot.require(self._identity(os.fstat(self.fd))==self.fd_identity and
            self._identity(self.lock.lstat())==self.fd_identity and
            self._identity(self.root.lstat())==self.root_identity,code)

    def check(self):
        code='FORMAL_CAPTURE_OUTPUT_OWNER_CHANGED'
        self._owned()
        for root,(identity,guard) in self.original_roots.items():
            snapshot.require(self._identity(root.lstat())==identity and not root.is_symlink(),code)
            if guard is not None:guard()
        self._owned()
        inherited=snapshot.observation_deadline.get()
        token=snapshot.observation_deadline.set(self.deadline if inherited is None else min(inherited,self.deadline))
        try:snapshot.current_owner_guard(self.guard,code=code)
        finally:snapshot.observation_deadline.reset(token)
        self._owned()

    def register_original_root(self,root,*,guard):
        """Explicit original control/registry root; never part of archive payload."""
        self.check();root=Path(root)
        snapshot.require(root.is_absolute() and root.resolve()==root and root not in self.original_roots and
            callable(guard) and not any(root in p.parents or p in root.parents for p in self.original_roots),
            'FORMAL_CAPTURE_OUTPUT_PATH_INVALID')
        info=root.lstat()
        snapshot.require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==0 and
            info.st_dev==self.root_identity[0],'FORMAL_CAPTURE_OUTPUT_DEVICE_CHANGED')
        guard();self.original_roots[root]=(self._identity(info),guard);self.check()

    def path(self,path):
        self.check();path=Path(path).absolute()
        roots=[root for root in self.original_roots if root in path.parents]
        snapshot.require(len(roots)==1,'FORMAL_CAPTURE_OUTPUT_PATH_INVALID')
        root=roots[0]
        snapshot.require(path!=root and
            len(path.relative_to(root).as_posix().encode('utf-8'))<=self.policy['maxPathBytes'],
            'FORMAL_CAPTURE_OUTPUT_PATH_INVALID')
        for parent in (path.parent,*path.parent.parents):
            snapshot.require(parent.is_dir() and not parent.is_symlink() and parent.resolve()==parent,
                'FORMAL_CAPTURE_OUTPUT_PATH_INVALID')
            if parent==root:break
        return path

    def mkdir(self,path):
        path=self.path(path)
        snapshot.require(len(self.directories)<self.policy['maxDirectories'],
            'FORMAL_CAPTURE_OUTPUT_DIRECTORY_LIMIT')
        path.mkdir(mode=0o700);self.directories.add(str(path));self.check()

    def open(self,path,component):
        path=self.path(path)
        reserved_files=sum(row['files'] for row in self.subtrees.values())
        snapshot.require(component in COMPONENTS and len(self.files)+reserved_files<self.policy['maxFiles'] and
            str(path) not in self.files,'FORMAL_CAPTURE_OUTPUT_FILE_LIMIT')
        from formal_boot_state import _directory
        with _directory(path.parent,no_atime=True) as (parent,_):
            fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
        info=os.fstat(fd)
        if info.st_dev!=self.root_identity[0]:
            os.close(fd)
            raise snapshot.FormalSnapshotError('FORMAL_CAPTURE_OUTPUT_DEVICE_CHANGED')
        self.files[str(path)]={'component':component,'bytes':0,'identity':self._identity(info)}
        return _Writer(self,path,fd,component)

    def reserve_watchdog(self,root):
        """Child author enforces 16 files, each canonical record <=16 KiB.

        Reserved worst-case bytes are never refunded or called actual writes.
        Independent watchdog lifecycle/lease still controls thaw on refusal.
        """
        path=self.path(root);size=16*16384
        snapshot.require(not os.path.lexists(path) and str(path) not in self.subtrees and
            self.used['control']+size<=self.policy['componentBytes']['control'] and
            self.total+size<=self.policy['totalBytes'] and
            len(self.files)+sum(r['files'] for r in self.subtrees.values())+16<=self.policy['maxFiles'],
            'FORMAL_CAPTURE_CONTROL_RESERVATION_LIMIT')
        row=dict(bytes=size,files=16,perFileBytes=16384)
        self.subtrees[str(path)]=row;self.used['control']+=size;self.total+=size
        return dict(row)

    def require_full_capture_admission(self):
        self.check()
        snapshot.require(self.full_admission is not None,'FORMAL_CAPTURE_COMPLETE_SPACE_ADMISSION_REQUIRED')
        self.full_admission.check_budget(self)

    def bind_full_capture_admission(self,admission):
        from formal_normal_owner import PreCaptureAdmission
        self.check()
        snapshot.require(type(admission) is PreCaptureAdmission and self.full_admission is None and
            admission.claim is self.claim and admission.budget is self,'FORMAL_CAPTURE_COMPLETE_SPACE_ADMISSION_REQUIRED')
        admission.check_budget(self);self.full_admission=admission

    def charge(self,path,component,size):
        self.check()
        snapshot.require(type(size) is int and size>=0 and self.used[component]+size<=self.policy['componentBytes'][component] and
            self.total+size<=self.policy['totalBytes'],'FORMAL_CAPTURE_OUTPUT_BYTE_LIMIT')
        self.used[component]+=size;self.total+=size;self.files[str(path)]['bytes']+=size

    def link(self,source,target):
        source=self.path(source);target=self.path(target)
        row=self.files.get(str(source))
        snapshot.require(row is not None and len(self.files)+sum(r['files'] for r in self.subtrees.values())<self.policy['maxFiles'] and
            self._identity(source.lstat())==row['identity'],'FORMAL_CAPTURE_OUTPUT_LINK_INVALID')
        os.link(source,target)
        self.files[str(target)]=dict(row)
        self.check()

    def unlink_complete(self,path):
        path=self.path(path);row=self.files.get(str(path))
        snapshot.require(row is not None and self._identity(path.lstat())==row['identity'],
            'FORMAL_CAPTURE_OUTPUT_FILE_CHANGED')
        path.unlink();row['retired']=True;self.check()

    @contextmanager
    def activate(self):
        self.check();snapshot.require(active_budget.get() is None,'FORMAL_CAPTURE_OUTPUT_SCOPE_ALREADY_ACTIVE')
        token=active_budget.set(self)
        try:yield self
        finally:active_budget.reset(token)

    def receipt(self):
        self.check();allocated=0
        allocated_identities=set()
        for path,row in self.files.items():
            if row.get('retired'):
                snapshot.require(not os.path.lexists(path),'FORMAL_CAPTURE_OUTPUT_RETIRED_FILE_CHANGED')
                continue
            info=Path(path).lstat()
            snapshot.require(self._identity(info)==row['identity'] and info.st_size<=row['bytes'],
                'FORMAL_CAPTURE_OUTPUT_FILE_CHANGED')
            if (info.st_dev,info.st_ino) not in allocated_identities:
                allocated+=info.st_blocks*512;allocated_identities.add((info.st_dev,info.st_ino))
        control_actual=0
        for name,row in self.subtrees.items():
            path=Path(name)
            if not os.path.lexists(path):continue
            info=path.lstat()
            snapshot.require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and
                stat.S_IMODE(info.st_mode)==0o700 and info.st_dev==self.root_identity[0],
                'FORMAL_CAPTURE_CONTROL_TREE_CHANGED')
            children=list(path.iterdir())
            snapshot.require(len(children)<=row['files'],'FORMAL_CAPTURE_CONTROL_TREE_CHANGED')
            for child in children:
                info=child.lstat()
                snapshot.require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==0 and
                    stat.S_IMODE(info.st_mode)==0o600 and info.st_dev==self.root_identity[0] and
                    info.st_size<=row['perFileBytes'],'FORMAL_CAPTURE_CONTROL_TREE_CHANGED')
                control_actual+=info.st_size;allocated+=info.st_blocks*512
        disk=os.statvfs(self.root)
        written=dict(self.written);written['control']+=control_actual
        return dict(schemaVersion='release-formal-capture-output-bound/v1',attemptId=self.attempt,
            sourceContextSha256=self.source_sha,policySha256=self.policy_sha,
            claimBindingSha256=hashlib.sha256(self.plan).hexdigest(),controlDevice=self.root_identity[0],
            logicalPayloadUpperBoundBytes=self.policy['totalBytes'],componentUpperBoundBytes=dict(self.policy['componentBytes']),
            writtenBytes=sum(written.values()),
            chargedOutputCeilingBytes=self.total,reservedControlUpperBoundBytes=sum(row['bytes'] for row in self.subtrees.values()),
            writtenComponentBytes=written,files=len(self.files),
            directories=len(self.directories),observedAllocatedFileBytes=allocated,
            observedFreeBytes=disk.f_bavail*disk.f_frsize,allocatedSpaceGuaranteed=False,
            allCaptureWriterPathsCovered=False,productionEvidence=False)


class _Writer:
    def __init__(self,budget,path,fd,component):
        self.budget=budget;self.path=path;self.fd=fd;self.component=component;self.position=0
    def write(self,data):
        snapshot.require(type(data) in (bytes,bytearray,memoryview),'FORMAL_CAPTURE_OUTPUT_BYTES_REQUIRED')
        self._owned()
        self.budget.charge(self.path,self.component,len(data))
        view=memoryview(data)
        while view:
            self._owned();written=os.write(self.fd,view)
            snapshot.require(written>0,'FORMAL_CAPTURE_OUTPUT_WRITE_FAILED')
            self.position+=written;self.budget.written[self.component]+=written;view=view[written:]
        self._owned();return len(data)
    def _owned(self):
        self.budget.check()
        row=self.budget.files[str(self.path)]
        snapshot.require(self.fd is not None and
            self.budget._identity(os.fstat(self.fd))==row['identity'] and
            self.budget._identity(self.path.lstat())==row['identity'] and
            os.fstat(self.fd).st_size==self.position,'FORMAL_CAPTURE_OUTPUT_FILE_CHANGED')
    def tell(self):return self.position
    def fileno(self):return self.fd
    def flush(self):self._owned();os.fsync(self.fd);self._owned()
    def __enter__(self):return self
    def __exit__(self,*args):os.close(self.fd);self.fd=None


def drain_owned_process(process,input_bytes,stdout_writer,*,guard,deadline,stderr_writer=None,stderr_limit=0):
    """All callbacks and disk writes stay on the original owner thread.

    Nonblocking stdin/stdout/stderr avoid pipe deadlocks; only the actual owned
    child is killed/reaped on refusal. This is no remote-operation stop proof.
    """
    snapshot.require(os.name=='posix' and callable(guard) and type(input_bytes) is bytes and
        type(stderr_limit) is int and stderr_limit>=0,'FORMAL_CAPTURE_PIPE_INPUT_INVALID')
    count_out=count_err=offset=0;primary=None
    selector=selectors.DefaultSelector()
    def check():
        snapshot.require(time.monotonic()<deadline,'FORMAL_CAPTURE_PIPE_DEADLINE')
        guard();snapshot.require(time.monotonic()<deadline,'FORMAL_CAPTURE_PIPE_DEADLINE')
    try:
        for stream,kind in ((process.stdout,'out'),(process.stderr,'err'),(process.stdin,'in')):
            snapshot.require(stream is not None,'FORMAL_CAPTURE_PIPE_REQUIRED')
            os.set_blocking(stream.fileno(),False)
            if kind=='in' and not input_bytes:stream.close();continue
            selector.register(stream,selectors.EVENT_WRITE if kind=='in' else selectors.EVENT_READ,kind)
        while selector.get_map():
            check()
            for key,_ in selector.select(min(.05,max(0,deadline-time.monotonic()))):
                check();stream=key.fileobj
                if key.data=='in':
                    size=os.write(stream.fileno(),input_bytes[offset:offset+65536]);offset+=size
                    if offset==len(input_bytes):selector.unregister(stream);stream.close()
                    continue
                chunk=os.read(stream.fileno(),65536)
                if not chunk:selector.unregister(stream);stream.close();continue
                if key.data=='out':stdout_writer.write(chunk);count_out+=len(chunk)
                else:
                    snapshot.require(count_err+len(chunk)<=stderr_limit,'FORMAL_CAPTURE_STDERR_LIMIT')
                    if stderr_writer is not None:stderr_writer.write(chunk)
                    count_err+=len(chunk)
                check()
        while process.poll() is None:
            check()
            try:process.wait(timeout=min(.05,max(.001,deadline-time.monotonic())))
            except subprocess.TimeoutExpired:continue
        check()
        snapshot.require(process.returncode==0,'FORMAL_CAPTURE_CHILD_FAILED')
        return dict(stdoutBytes=count_out,stderrBytes=count_err,returncode=process.returncode)
    except BaseException as error:primary=error;raise
    finally:
        selector.close();uncertain=False
        try:
            if process.poll() is None:process.kill()
            process.wait(timeout=1)
        except (OSError,subprocess.TimeoutExpired):uncertain=True
        for stream in (process.stdin,process.stdout,process.stderr):
            try:
                if stream is not None and not stream.closed:stream.close()
            except OSError:uncertain=True
        if uncertain:
            if primary is not None:primary.clientCleanupUncertain=True
            else:raise snapshot.FormalSnapshotError('FORMAL_CAPTURE_CHILD_CLEANUP_UNCERTAIN')
