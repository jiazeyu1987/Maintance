"""Single original native owner, bounded unified control and admission consumers.

Wire documents are not authority. Native originals and current held transport
objects stay on the acquiring thread; this module never acquires a second claim.
"""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import stat
import threading
import time

import formal_snapshot_linux as snapshot

BINDING_FIELDS={'releaseTag','attemptId','sourceContextSha256','installedContextSha256',
    'originalReleaseBindingSha256','claimBindingSha256','approvedSourceTargetSha256',
    'capturePolicySha256','nasWorkspaceConfigSha256'}
BOOTSTRAP_FIELDS={'releaseTag','attemptId','sourceContextSha256','capturePolicySha256','nasWorkspaceConfigSha256'}
CONTROL_SCHEMA='release-production-backup-control/v1'
INTERFACE_FAILURE_CODES={'BACKUP_INTERFACE_'+code for code in ('SCHEMA_INVALID','BINDING_INVALID',
    'SEQUENCE_INVALID','BUDGET_EXPIRED','SOURCE_CHANGED','ADMISSION_REQUIRED','CAPACITY_INSUFFICIENT',
    'AUTHOR_LOST','AUTHORITY_INVALID','NATIVE_PREREQUISITE_REQUIRED','STREAM_FAILED','TERMINAL_UNKNOWN','COMPONENT_FAILED')}
def require(value,code='BACKUP_INTERFACE_SCHEMA_INVALID'):snapshot.require(value,code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def strict_document(raw,limit=16384):
    require(type(raw) is bytes and 0<len(raw)<=limit and not raw.startswith(b'\xef\xbb\xbf'))
    def pairs(items):
        result={}
        for k,v in items:require(k not in result);result[k]=v
        return result
    def nonfinite(value):raise snapshot.FormalSnapshotError('BACKUP_INTERFACE_SCHEMA_INVALID')
    try:return json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=pairs,parse_constant=nonfinite)
    except (ValueError,UnicodeError,RecursionError):raise snapshot.FormalSnapshotError('BACKUP_INTERFACE_SCHEMA_INVALID') from None
def integer(value,minimum=0,maximum=2**63-1):
    require(type(value) is int and minimum<=value<=maximum);return value
def binding(value):
    require(type(value) is dict and set(value)==BINDING_FIELDS,'BACKUP_INTERFACE_BINDING_INVALID')
    require(type(value['releaseTag']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,122}',value['releaseTag']),
        'BACKUP_INTERFACE_BINDING_INVALID')
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{64}',v) for k,v in value.items() if k!='releaseTag'),
        'BACKUP_INTERFACE_BINDING_INVALID');return value
def pin(value):
    require(type(value) is dict and set(value)=={'path','bytes','sha256'} and type(value['path']) is str and
        re.match(r'^(?:/|[A-Za-z]:[\\/])',value['path']) and type(value['sha256']) is str and
        re.fullmatch('[0-9a-f]{64}',value['sha256']))
    integer(value['bytes']);return value
def remaining_deadline(milliseconds,sent,received,original):
    integer(milliseconds,1,7200000)
    require(all(type(t) in (int,float) and math.isfinite(t) for t in (sent,received,original)) and sent<=received)
    # Full round-trip, not receive time plus the peer's unspent-looking value.
    end=min(original,received+milliseconds/1000-(received-sent))
    require(time.monotonic()<end,'BACKUP_INTERFACE_BUDGET_EXPIRED');return end

def validate_manifest_read(raw,reference):
    value=strict_document(raw)
    require(type(value) is dict and set(value)=={'schemaVersion','manifestSha256','offset'} and
        value['schemaVersion']=='release-production-backup-manifest-read/v1' and
        value['manifestSha256']==reference['sha256'],'BACKUP_INTERFACE_BINDING_INVALID')
    return integer(value['offset'])

class OriginalOwner:
    def __init__(self,claim,*,guard,deadline):
        require(os.name=='posix' and os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim and
            callable(guard) and type(deadline) in (int,float) and math.isfinite(deadline),
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        import formal_boot_state as boot
        claim.assert_owned();self.claim=claim;self.fd=claim._fd;self.root=claim.root;self.plan=claim._plan;self.lock=claim._lock
        self.pid=os.getpid();self.thread=threading.get_ident();self.guard=guard
        outer=snapshot.observation_deadline.get();self.deadline=deadline if outer is None else min(deadline,outer)
        self.identity=boot._signature(os.fstat(self.fd))
        self.root_identity=(self.root.stat().st_dev,self.root.stat().st_ino)
        self.check()
    def owned(self):
        import formal_boot_state as boot
        require(os.getpid()==self.pid and threading.get_ident()==self.thread and self.claim._fd==self.fd and
            self.claim.root==self.root and self.claim._plan==self.plan and self.claim._lock==self.lock,
            'BACKUP_INTERFACE_AUTHOR_LOST')
        require(time.monotonic()<self.deadline,'BACKUP_INTERFACE_BUDGET_EXPIRED')
        self.claim.assert_owned()
        require(boot._signature(os.fstat(self.fd))==self.identity and boot._signature(self.lock.lstat())==self.identity and
            (self.root.stat().st_dev,self.root.stat().st_ino)==self.root_identity,'BACKUP_INTERFACE_AUTHOR_LOST')
    def check(self):
        self.owned();outer=snapshot.observation_deadline.get()
        token=snapshot.observation_deadline.set(self.deadline if outer is None else min(self.deadline,outer))
        try:self.guard();self.owned()
        finally:snapshot.observation_deadline.reset(token)

class OriginalReference:
    def __init__(self,reference,*,owner,limit=16384,mode=0o600):
        import formal_boot_state as boot
        pin(reference);require(reference['path'].startswith('/') and '\\' not in reference['path'])
        self.owner=owner;self.path=boot._absolute(reference['path']);self.limit=limit;self.mode=mode
        owner.check();self.pair=boot._read_secure(self.path,mode,limit,no_atime=True)
        require(len(self.pair[0])==reference['bytes'] and sha(self.pair[0])==reference['sha256'],
            'BACKUP_INTERFACE_SOURCE_CHANGED')
        with boot._directory(self.path.parent,no_atime=True) as (_,chain):self.parents=chain
        self.reference=dict(reference);self.raw=self.pair[0];self.check()
    def check(self):
        import formal_boot_state as boot
        self.owner.check();boot._directory_unchanged(self.path.parent,self.parents)
        require(boot._read_secure(self.path,self.mode,self.limit,no_atime=True)==self.pair,'BACKUP_INTERFACE_SOURCE_CHANGED')
        self.owner.owned()

class PreCaptureAdmission:
    """Only constructed by validated original intent/transport/local authors."""
    def check_budget(self,budget):
        require(self.budget is budget and self.claim is budget.claim,'BACKUP_INTERFACE_AUTHOR_LOST')
        self.check()

def allocated_peak(logical,files,directories,path_bytes,rule):
    """Independent approved rules supply ceilings; no logical multiplier guess."""
    for v in (logical,files,directories,path_bytes):integer(v)
    fields={'allocationUnitBytes','fileMetadataUpperBytes','directoryMetadataUpperBytes','pathByteUpperBytes','transactionPeakBytes'}
    require(type(rule) is dict and set(rule)==fields)
    for value in rule.values():integer(value,1)
    return logical+files*(rule['allocationUnitBytes']-1+rule['fileMetadataUpperBytes'])+directories*rule['directoryMetadataUpperBytes']+path_bytes*rule['pathByteUpperBytes']+rule['transactionPeakBytes']

class FixedManifest:
    """One immutable file for the original dict; serialization is streamed once."""
    def __init__(self,owner,entries,budget,path):
        import formal_boot_state as boot
        require(type(entries) is dict and entries and len(entries)<=budget.policy['maxFiles']+budget.policy['maxDirectories'])
        self.owner=owner;self.entries=entries;self.path=Path(path);self.offset=0;self.finished=False
        require(owner.root not in self.path.parents,'BACKUP_INTERFACE_SOURCE_CHANGED')
        digest=hashlib.sha256();size=0
        encoder=json.JSONEncoder(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        with budget.open(self.path,'control') as out:
            pending=bytearray()
            for part in encoder.iterencode(entries):
                raw=part.encode('utf-8');digest.update(raw);size+=len(raw);pending.extend(raw)
                while len(pending)>=65536:out.write(pending[:65536]);del pending[:65536]
            if pending:out.write(pending)
            out.flush();os.fsync(out.fileno())
        self.reference=dict(path=str(self.path),bytes=size,sha256=digest.hexdigest())
        self.identity=boot._signature(self.path.lstat());self.check()
    def check(self):
        import formal_boot_state as boot
        self.owner.check();require(boot._signature(self.path.lstat())==self.identity,'BACKUP_INTERFACE_SOURCE_CHANGED')
        digest=hashlib.sha256();size=0
        for part in json.JSONEncoder(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(self.entries):
            raw=part.encode('utf-8');digest.update(raw);size+=len(raw)
        require(size==self.reference['bytes'] and digest.hexdigest()==self.reference['sha256'],'BACKUP_INTERFACE_SOURCE_CHANGED')
    def chunk(self,offset):
        import formal_boot_state as boot
        self.check();integer(offset)
        require(not self.finished and offset==self.offset,'BACKUP_INTERFACE_SEQUENCE_INVALID')
        fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
        try:
            require(boot._signature(os.fstat(fd))==self.identity,'BACKUP_INTERFACE_SOURCE_CHANGED')
            raw=os.pread(fd,32768,offset)
            require(raw,'BACKUP_INTERFACE_SEQUENCE_INVALID')
            self.offset+=len(raw);self.finished=self.offset==self.reference['bytes']
            require(self.offset<=self.reference['bytes'],'BACKUP_INTERFACE_SOURCE_CHANGED')
        finally:os.close(fd)
        self.check();return dict(offset=offset,bytesBase64=base64.b64encode(raw).decode('ascii'),chunkSha256=sha(raw),eof=self.finished)

class ControlSequence:
    ALLOWED={'prepare':'BOUND_READONLY','admit':'PREPARED','capture':'PREFLIGHT_VALIDATED',
        'read-manifest':'ARCHIVE_READY','begin-archive':'ARCHIVE_READY'}
    def __init__(self,original_binding):self.binding=binding(original_binding);self.raw=canonical(self.binding);self.sequence=1
    def accept(self,raw,state):
        request=strict_document(raw,8192)
        require(type(request) is dict and set(request)=={'schemaVersion','binding','sequence','action','payloadReference','budget'} and
            request['schemaVersion']==CONTROL_SCHEMA)
        binding(request['binding']);require(canonical(request['binding'])==self.raw,'BACKUP_INTERFACE_BINDING_INVALID')
        require(type(request['sequence']) is int and request['sequence']==self.sequence,'BACKUP_INTERFACE_SEQUENCE_INVALID')
        action=request['action'];require(type(action) is str and action in (*self.ALLOWED,'guard'))
        require((action=='guard' and state in {'BOUND_READONLY','PREPARED','PREFLIGHT_VALIDATED','ARCHIVE_READY'}) or
            (action!='guard' and self.ALLOWED[action]==state),'BACKUP_INTERFACE_SEQUENCE_INVALID')
        if action in ('guard','begin-archive'):require(request['payloadReference'] is None)
        else:pin(request['payloadReference'])
        budget=request['budget'];require(type(budget) is dict and set(budget)=={'remainingMilliseconds','observationReference'})
        integer(budget['remainingMilliseconds'],1,7200000);pin(budget['observationReference'])
        self.sequence+=1;return request

class NativeControl:
    """Nonblocking original pipe FDs; no eager reader consumes archive frames."""
    def __init__(self,request_fd,response_fd,owner):
        import formal_boot_state as boot
        require(type(owner) is OriginalOwner and type(request_fd) is int and type(response_fd) is int and request_fd!=response_fd)
        require(stat.S_ISFIFO(os.fstat(request_fd).st_mode) and stat.S_ISFIFO(os.fstat(response_fd).st_mode),
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.request_fd=request_fd;self.response_fd=response_fd;self.owner=owner
        self.request_identity=boot._signature(os.fstat(request_fd))[:6];self.response_identity=boot._signature(os.fstat(response_fd))[:6]
        self.switched=False
        os.set_blocking(request_fd,False);os.set_blocking(response_fd,False)
    def check(self):
        import formal_boot_state as boot
        self.owner.check();require(not self.switched,'BACKUP_INTERFACE_SEQUENCE_INVALID')
        require(boot._signature(os.fstat(self.request_fd))[:6]==self.request_identity and
            boot._signature(os.fstat(self.response_fd))[:6]==self.response_identity,'BACKUP_INTERFACE_STREAM_FAILED')
    def wait(self,fd,event):
        self.check()
        with selectors.DefaultSelector() as selector:
            selector.register(fd,event)
            while not selector.select(min(.05,max(0,self.owner.deadline-time.monotonic()))):self.check()
        self.check()
    def receive(self):
        pending=bytearray()
        # One byte avoids swallowing begin-archive's first legacy request.
        while True:
            self.wait(self.request_fd,selectors.EVENT_READ)
            try:raw=os.read(self.request_fd,1)
            except BlockingIOError:continue
            require(raw,'BACKUP_INTERFACE_STREAM_FAILED')
            if raw==b'\n':require(pending);return bytes(pending)
            pending.extend(raw);require(len(pending)<=8192)
    def send(self,document):
        raw=canonical(document)+b'\n';require(len(raw)<=65536)
        offset=0
        while offset<len(raw):
            self.wait(self.response_fd,selectors.EVENT_WRITE)
            try:count=os.write(self.response_fd,raw[offset:])
            except BlockingIOError:continue
            require(count>0,'BACKUP_INTERFACE_STREAM_FAILED');offset+=count
        self.check()
    def begin_archive(self):
        self.check();os.set_blocking(self.request_fd,True);os.set_blocking(self.response_fd,True);self.switched=True

class PreparedOriginals:
    def __init__(self,owner,original_tuple,budget,inputs):
        import formal_boot_state as boot
        require(type(original_tuple) is tuple and len(original_tuple)==2 and callable(original_tuple[1]))
        self.owner=owner;self.original_tuple=original_tuple;self.budget=budget;self.inputs=inputs
        self.result=original_tuple[0];self.raw=canonical(self.result)
        require(type(self.result) is dict and self.result.get('state')=='A_ORIGINAL_SOURCES_PREPARED_PENDING_INDEPENDENT_AUTHORITY')
        inv=self.result['inventory'];path=Path(inv['path'])
        raw,pair=boot._read_secure(path,0o600,65536,no_atime=True)
        require(sha(raw)==inv['sha256'],'BACKUP_INTERFACE_SOURCE_CHANGED')
        self.inventory=OriginalReference(dict(path=str(path),sha256=sha(raw),bytes=len(raw)),owner=owner,limit=65536)
        self.check()
    def check(self):
        self.owner.check();self.original_tuple[1]();require(canonical(self.result)==self.raw,'BACKUP_INTERFACE_SOURCE_CHANGED')
        self.inventory.check()

class NativeAllocationSources:
    """Retained independently approved, target-specific allocation originals.

    A rule must contain its actual device observation and independent allocation
    proof reference. Geometry alone cannot manufacture a metadata upper bound.
    This author will refuse unsupported/unapproved allocation rules rather than
    deriving them from statvfs or a compression estimate.
    """
    def __init__(self,owner,*,binding_value,policy_reference,coverage_reference,allocation_reference,
                 source_guard_reference,control_root,registry_root,native_author):
        import formal_boot_state as boot
        self.owner=owner;self.binding=binding(binding_value);self.binding_raw=canonical(self.binding)
        self.policy=OriginalReference(policy_reference,owner=owner)
        self.coverage=OriginalReference(coverage_reference,owner=owner)
        self.allocation=OriginalReference(allocation_reference,owner=owner)
        self.source_guard=OriginalReference(source_guard_reference,owner=owner)
        self.control_root=boot._absolute(str(control_root));self.registry_root=boot._absolute(str(registry_root))
        require(type(native_author) is ApprovedNativeAuthor,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.native_author=native_author
        self.refs=[];self.issued=None;self.check()
    def check(self):
        self.owner.check();require(canonical(self.binding)==self.binding_raw,'BACKUP_INTERFACE_BINDING_INVALID')
        self.native_author.check()
        for ref in (self.policy,self.coverage,self.allocation,self.source_guard,*self.refs):ref.check()
    def observe(self,budget):
        import formal_boot_state as boot
        self.check();coverage=strict_document(self.coverage.raw)
        # Approved writer closure pins every actually imported native module.
        require(type(coverage) is dict and set(coverage)=={'schemaVersion','binding','writers','sources','roots'} and
            coverage['schemaVersion']=='release-production-backup-writer-coverage/v1' and
            coverage['binding']==self.binding and set(coverage['writers'])=={'sql-raw','sql-gzip','physical','images',
                'image-stderr','config','proof','control','data-evidence-scratch'},'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        require(coverage['roots']==[str(self.owner.root),str(self.control_root),str(self.registry_root)],
            'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        import sys
        native_dir=Path(__file__).parent
        loaded={str(Path(m.__file__).resolve()) for n,m in tuple(sys.modules.items()) if n.startswith('formal_') and
            getattr(m,'__file__',None) and Path(m.__file__).resolve().parent==native_dir.resolve()}
        require(type(coverage['sources']) is list and {p['path'] for p in coverage['sources']}==loaded,
            'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        for ref in coverage['sources']:
            pin(ref);raw=Path(ref['path']).read_bytes()
            require(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'],'BACKUP_INTERFACE_SOURCE_CHANGED')
        observed=strict_document(self.allocation.raw)
        require(type(observed) is dict and set(observed)=={'schemaVersion','binding','devices','nas','staging'} and
            observed['schemaVersion']=='release-production-backup-allocation-original/v1' and observed['binding']==self.binding and
            type(observed['devices']) is list and observed['devices'],'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        rows=[];devices=set()
        for entry in observed['devices']:
            require(type(entry) is dict and set(entry)=={'root','deviceIdentityReference','allocationProofReference','reserveBytes','budgetBytes'})
            root=boot._absolute(entry['root']);require(root in budget.original_roots,'BACKUP_INTERFACE_ADMISSION_REQUIRED')
            identity=OriginalReference(entry['deviceIdentityReference'],owner=self.owner)
            proof=OriginalReference(entry['allocationProofReference'],owner=self.owner);self.refs.extend((identity,proof))
            actual=root.lstat();disk=os.statvfs(root)
            ident=strict_document(identity.raw);rule=strict_document(proof.raw)
            require(type(ident) is dict and set(ident)=={'device','inode','fragmentBytes','blockBytes','filesystemId'} and
                ident==dict(device=actual.st_dev,inode=actual.st_ino,fragmentBytes=disk.f_frsize,blockBytes=disk.f_bsize,filesystemId=disk.f_fsid),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
            require(type(rule) is dict and set(rule)=={'schemaVersion','deviceIdentitySha256','rules','verificationReference'} and
                rule['schemaVersion']=='release-production-backup-allocation-proof/v1' and
                rule['deviceIdentitySha256']==identity.reference['sha256'],'BACKUP_INTERFACE_ADMISSION_REQUIRED')
            verified=OriginalReference(rule['verificationReference'],owner=self.owner);self.refs.append(verified)
            self.native_author.verify_allocation(root,identity,proof,verified,budget)
            require(rule['rules']['allocationUnitBytes']>=disk.f_frsize,'BACKUP_INTERFACE_ADMISSION_REQUIRED')
            logical=budget.policy['totalBytes'];files=budget.policy['maxFiles'];dirs=budget.policy['maxDirectories']
            peak=allocated_peak(logical,files,dirs,(files+dirs)*budget.policy['maxPathBytes'],rule['rules'])
            reserve=integer(entry['reserveBytes']);ceiling=integer(entry['budgetBytes'],1)
            available=disk.f_bavail*disk.f_frsize
            require(peak+reserve<=available and peak+reserve<=ceiling,'BACKUP_INTERFACE_CAPACITY_INSUFFICIENT')
            devices.add(actual.st_dev);rows.append(dict(deviceIdentityReference=identity.reference,allocationProofReference=proof.reference,
                peakAllocatedBytes=peak,availableBytes=available,reserveBytes=reserve,budgetBytes=ceiling))
        require(devices=={info[0][0] for info in budget.original_roots.values()},'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        remote=[]
        for name in ('nas','staging'):
            selected=observed[name];require(type(selected) is dict and set(selected)=={'allocatedUpperBoundBytes','verificationReference'})
            verified=OriginalReference(selected['verificationReference'],owner=self.owner);self.refs.append(verified)
            self.native_author.verify_remote_allocation(name,verified,selected['allocatedUpperBoundBytes'],budget,self.binding)
            remote.append(integer(selected['allocatedUpperBoundBytes'],1))
        self.check();return rows,remote[0],remote[1]

def write_control(budget,root,name,document):
    raw=canonical(document);require(len(raw)<=16384)
    path=Path(root)/name
    with budget.open(path,'control') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    return dict(path=str(path),sha256=sha(raw),bytes=len(raw)),raw

def write_control_document(budget,root,name,document):
    """Large evidence is streamed to a bounded private file, never a wire frame."""
    path=Path(root)/name;digest=hashlib.sha256();size=0
    with budget.open(path,'control') as output:
        for part in json.JSONEncoder(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(document):
            raw=part.encode('utf-8');output.write(raw);digest.update(raw);size+=len(raw)
        output.flush();os.fsync(output.fileno())
    return dict(path=str(path),bytes=size,sha256=digest.hexdigest())

class ReservedFailureRecord:
    """Fixed emergency evidence allowance reserved before any source effect."""
    def __init__(self,owner,budget,root):
        self.owner=owner;self.budget=budget;self.path=Path(root)/'owner-failed.json'
        self.output=budget.open(self.path,'control');self.limit=16384
        try:budget.charge(self.path,'control',self.limit)
        except BaseException:
            self.output.__exit__(None,None,None);raise
        self.identity=budget._identity(os.fstat(self.output.fileno()))
    def record(self,document):
        # Expiry cannot grant service actions. The retained FD allows only a
        # bounded failure record, under the same still-owned native claim.
        owner=self.owner;owner.claim.assert_owned()
        require(os.getpid()==owner.pid and threading.get_ident()==owner.thread and owner.claim._fd==owner.fd and
            self.budget._identity(self.path.lstat())==self.identity and
            self.budget._identity(os.fstat(self.output.fileno()))==self.identity and
            os.fstat(self.output.fileno()).st_size==0,'BACKUP_INTERFACE_AUTHOR_LOST')
        raw=canonical(document);require(len(raw)<=self.limit)
        offset=0
        while offset<len(raw):
            written=os.write(self.output.fileno(),raw[offset:]);require(written>0,'BACKUP_INTERFACE_STREAM_FAILED')
            offset+=written
        os.fsync(self.output.fileno());self.budget.written['control']+=len(raw)
    def close(self):
        self.output.__exit__(None,None,None)

class CaptureIntentOriginal:
    def check(self):
        self.owner.check();self.prepared.check();self.allocation.check();self.reference.check()
        require(canonical(self.document)==self.raw,'BACKUP_INTERFACE_SOURCE_CHANGED')

def prepare_intent(claim,*,prepared,policy_raw,policy_sha256,source_context_raw,allocation_sources,guard,deadline):
    require(type(prepared) is PreparedOriginals and type(allocation_sources) is NativeAllocationSources,
        'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    require(prepared.owner.claim is claim and allocation_sources.owner is prepared.owner and callable(guard) and
        allocation_sources.issued is None,'BACKUP_INTERFACE_AUTHOR_LOST')
    owner=prepared.owner;owner.deadline=min(owner.deadline,deadline);prepared.check();guard()
    budget=prepared.budget;original=allocation_sources
    require(budget.raw==policy_raw and budget.policy_sha==policy_sha256==original.binding['capturePolicySha256'] and
        original.policy.raw==policy_raw and sha(source_context_raw)==original.binding['sourceContextSha256'] and
        sum(budget.policy['componentBytes'].values())<=budget.policy['totalBytes']<=274877906944,
        'BACKUP_INTERFACE_BINDING_INVALID')
    rows,nas,staging=original.observe(budget)
    result=CaptureIntentOriginal();result.owner=owner;result.prepared=prepared;result.budget=budget;result.allocation=original
    result.document=dict(schemaVersion='release-production-backup-capture-intent/v1',binding=original.binding,
        sourceInventorySha256=prepared.inventory.reference['sha256'],policyReference=original.policy.reference,
        writerCoverageReference=original.coverage.reference,sourceGuardReference=original.source_guard.reference,
        logicalPayloadUpperBoundBytes=budget.policy['totalBytes'],componentUpperBoundBytes=budget.policy['componentBytes'],
        coveredWriterClasses=sorted({'sql-raw','sql-gzip','physical','images','image-stderr','config','proof','control','data-evidence-scratch'}),
        allCaptureWriterPathsCovered=True,allocationBoundVerified=True,allocationReference=original.allocation.reference,devices=rows,
        nasAllocatedUpperBoundBytes=nas,windowsStagingPeakAllocatedBytes=staging,maxFiles=budget.policy['maxFiles'],
        maxDirectories=budget.policy['maxDirectories'],maxPathBytes=budget.policy['maxPathBytes'])
    ref,result.raw=write_control(budget,original.control_root,'capture-intent.json',result.document)
    result.reference=OriginalReference(ref,owner=owner);original.issued=result;result.check();return result

class ApprovedNativeAuthor:
    """Native adapter code is an independently approved original, not JSON authority.

    No generic executable/command is taken from a wire message. The CLI recipe
    separately pins the root-private runtime author; its actual retained author
    must supply original observations and current guards. No adapter is selected
    when this prerequisite is absent.
    """
    def __init__(self,owner,program_reference,adapter):
        self.owner=owner;self.program=OriginalReference(program_reference,owner=owner,limit=1048576)
        require(adapter is not None and all(callable(getattr(adapter,k,None)) for k in
            ('check_original_owner','verify_allocation','verify_remote_allocation','observe_nas_admission',
             'observe_staging_admission','observe_control_budget')),'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        import inspect
        require(Path(inspect.getfile(type(adapter))).resolve()==self.program.path,
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.adapter=adapter;self.pid=os.getpid();self.thread=threading.get_ident();self.check()
    def check(self):
        self.program.check();require(os.getpid()==self.pid and threading.get_ident()==self.thread,'BACKUP_INTERFACE_AUTHOR_LOST')
        self.adapter.check_original_owner(self.owner.claim,self.owner.fd,self.pid,self.thread,self.owner.deadline)
        self.program.check()
    def verify_allocation(self,root,identity,proof,verification,budget):
        self.check()
        observed=self.adapter.verify_allocation(root,identity,proof,verification,budget,self.owner.deadline)
        require(type(observed) is NativeAllocationObservation and observed.owner is self.owner and observed.author is self and
            observed.rule_reference is proof and observed.device_reference is identity,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        observed.check();self.check()
    def verify_remote_allocation(self,target,reference,peak,budget,original_binding):
        self.check()
        observed=self.adapter.verify_remote_allocation(target,reference,peak,budget,original_binding,self.owner.deadline)
        require(type(observed) is NativeAllocationObservation and observed.author is self and observed.owner is self.owner and
            observed.target==target and observed.peak==peak,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        observed.check();self.check()

class NativeAllocationObservation:
    def __init__(self,owner,author,*,device_reference,rule_reference,target,peak,current_guard):
        require(type(owner) is OriginalOwner and type(author) is ApprovedNativeAuthor and author.owner is owner and
            callable(current_guard),'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.owner=owner;self.author=author;self.device_reference=device_reference;self.rule_reference=rule_reference
        self.target=target;self.peak=integer(peak,1);self.current_guard=current_guard;self.check()
    def check(self):
        self.owner.check();self.current_guard();self.owner.owned()
        for ref in (self.device_reference,self.rule_reference):
            if ref is not None:require(type(ref) is OriginalReference);ref.check()

class TrustedTransportObservation:
    def __init__(self,owner,author,*,raw,reference,sequence,sent,received,current_guard):
        require(type(owner) is OriginalOwner and type(author) is ApprovedNativeAuthor and author.owner is owner and
            type(raw) is bytes and callable(current_guard),'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        pin(reference);require(len(raw)==reference['bytes'] and sha(raw)==reference['sha256'],'BACKUP_INTERFACE_SOURCE_CHANGED')
        require(type(sent) in (int,float) and type(received) in (int,float) and math.isfinite(sent) and math.isfinite(received) and
            sent<=received<=time.monotonic(),'BACKUP_INTERFACE_BUDGET_EXPIRED')
        self.owner=owner;self.author=author;self.raw=raw;self.reference=dict(reference);self.sequence=integer(sequence,1)
        self.sent=sent;self.received=received;self.guard=current_guard;self.check()
    def check(self):
        self.owner.check();self.guard();require(sha(self.raw)==self.reference['sha256'],'BACKUP_INTERFACE_SOURCE_CHANGED');self.owner.owned()

NAS_ADMISSION_FIELDS={'schemaVersion','binding','intent','intentReference','admissionId','authorIdentityReference','resourceObservationReference',
        'allocationProofReference','workspaceUsageBytes','availableBytes','workspaceBudgetBytes','maxAttemptBytes','reserveBytes',
        'logicalPayloadUpperBoundBytes','nasAllocatedUpperBoundBytes','budget','authorHeld','preCaptureAdmitted','exclusionScope',
        'spaceGuaranteed','allWritersExcluded','nasHardQuotaConfigured','automaticDeletion'}

def validate_nas_document(raw,intent):
    document=strict_document(raw)
    if type(document) is dict and document.get('schemaVersion')=='backup-lab-nas-admission/v1':
        from formal_backup_lab import validate_nas_admission, current_authority
        return validate_nas_admission(document,intent,current_authority())
    fields=NAS_ADMISSION_FIELDS
    require(type(document) is dict and set(document)==fields and document['schemaVersion']=='release-production-backup-nas-admission/v1')
    binding(document['binding']);require(document['binding']==intent.document['binding'] and document['intent']==intent.document and
        document['intentReference']==intent.reference.reference,'BACKUP_INTERFACE_BINDING_INVALID')
    require(type(document['admissionId']) is str and re.fullmatch('[0-9a-f]{64}',document['admissionId']))
    for name in ('authorIdentityReference','resourceObservationReference','allocationProofReference'):pin(document[name])
    for name in ('workspaceUsageBytes','availableBytes'):integer(document[name])
    for name in ('logicalPayloadUpperBoundBytes','nasAllocatedUpperBoundBytes'):integer(document[name],1)
    require(document['workspaceBudgetBytes']==1099511627776 and type(document['workspaceBudgetBytes']) is int and
        document['maxAttemptBytes']==document['reserveBytes']==274877906944 and
        type(document['maxAttemptBytes']) is int and type(document['reserveBytes']) is int and
        document['logicalPayloadUpperBoundBytes']==intent.document['logicalPayloadUpperBoundBytes'] and
        document['nasAllocatedUpperBoundBytes']==intent.document['nasAllocatedUpperBoundBytes'],
        'BACKUP_INTERFACE_BINDING_INVALID')
    require(document['authorHeld'] is True and document['preCaptureAdmitted'] is True and
        document['exclusionScope']=='cooperative-workspace-writers' and all(document[k] is False for k in
            ('spaceGuaranteed','allWritersExcluded','nasHardQuotaConfigured','automaticDeletion')),'BACKUP_INTERFACE_ADMISSION_REQUIRED')
    require(document['logicalPayloadUpperBoundBytes']<=274877906944 and
        document['workspaceUsageBytes']+document['logicalPayloadUpperBoundBytes']+274877906944<=1099511627776 and
        document['availableBytes']>=document['nasAllocatedUpperBoundBytes']+274877906944,'BACKUP_INTERFACE_CAPACITY_INSUFFICIENT')
    wire=document['budget'];require(type(wire) is dict and set(wire)=={'remainingMilliseconds','observationReference'})
    integer(wire['remainingMilliseconds'],1,7200000);pin(wire['observationReference']);return document

class LocalPreCaptureAdmission:
    def __init__(self,intent,author,reference):
        require(type(intent) is CaptureIntentOriginal and type(author) is ApprovedNativeAuthor and author is intent.allocation.native_author,
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.intent=intent;self.author=author;self.reference=reference;self.owner=intent.owner;self.budget=intent.budget
        self.observation=None;self.check(prepared=True)
    def check(self,*,prepared=False):
        self.owner.check();self.author.check();self.intent.allocation.check()
        if prepared:self.intent.check()
        observed=self.author.adapter.observe_staging_admission(self.intent,self.reference,self.owner.deadline)
        require(type(observed) is TrustedTransportObservation and observed.owner is self.owner and observed.author is self.author,
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        value=strict_document(observed.raw)
        require(type(value) is dict and set(value)=={'schemaVersion','binding','intentSha256','peakAllocatedBytes','availableBytes','reserveBytes','budget'} and
            value['schemaVersion']=='release-production-backup-staging-admission/v1' and value['binding']==self.intent.document['binding'] and
            value['intentSha256']==sha(self.intent.raw) and value['peakAllocatedBytes']==self.intent.document['windowsStagingPeakAllocatedBytes'],
            'BACKUP_INTERFACE_BINDING_INVALID')
        require(integer(value['availableBytes'])>=integer(value['peakAllocatedBytes'],1)+integer(value['reserveBytes']),
            'BACKUP_INTERFACE_CAPACITY_INSUFFICIENT')
        require(type(value['budget']) is dict and set(value['budget'])=={'remainingMilliseconds','observationReference'})
        pin(value['budget']['observationReference']);self.owner.deadline=remaining_deadline(value['budget']['remainingMilliseconds'],
            observed.sent,observed.received,self.owner.deadline)
        observed.check();self.observation=observed;self.owner.check()

def verify_admission(claim,*,intent_raw,nas_admission_raw,admission_transport,local_admission,guard,deadline):
    require(type(local_admission) is LocalPreCaptureAdmission and type(admission_transport) is ApprovedNativeAuthor,
        'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    original=local_admission.intent;owner=original.owner
    require(owner.claim is claim and original.raw==intent_raw and admission_transport is original.allocation.native_author and
        callable(guard),'BACKUP_INTERFACE_AUTHOR_LOST')
    owner.deadline=min(owner.deadline,deadline);original.check();guard();local_admission.check(prepared=True)
    document=validate_nas_document(nas_admission_raw,original)
    observed=admission_transport.adapter.observe_nas_admission(original,nas_admission_raw,owner.deadline)
    require(type(observed) is TrustedTransportObservation and observed.author is admission_transport and observed.owner is owner and
        observed.raw==nas_admission_raw,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    observed.check();owner.deadline=remaining_deadline(document['budget']['remainingMilliseconds'],observed.sent,observed.received,owner.deadline)
    result=PreCaptureAdmission();result.owner=owner;result.claim=claim;result.budget=original.budget;result.intent=original
    result.transport=admission_transport;result.local=local_admission;result.observation=observed;result.document=document
    result.started=False;result.raw=canonical(document);result.deadline=owner.deadline
    def checked():
        owner.check();require(time.monotonic()<result.deadline,'BACKUP_INTERFACE_BUDGET_EXPIRED')
        original.allocation.check();original.reference.check();result.observation.check()
        require(canonical(result.document)==result.raw,'BACKUP_INTERFACE_SOURCE_CHANGED')
        if not result.started:original.check();local_admission.check(prepared=True)
        owner.check()
    result.check=checked;checked();return result


class NormalOwnerInputs:
    """Explicit approved native assembly, retained on the acquiring thread.

    The runtime author supplies real deployment-specific transport and writer
    exclusion. Its code is independently pinned; absent originals or an absent
    author is a prerequisite error. JSON is never a substitute for live custody.
    """
    def __init__(self,*,binding_value,policy_reference,source_context_reference,
            installed_context_reference,release_binding_reference,coverage_reference,
            allocation_reference,source_guard_reference,program_reference,archive_program_reference,
            staging_admission_reference,control_root,registry_root,prepare_arguments,resume_request,capture_request,
            recovery_arguments,series_specification,adapter):
        self.binding=binding(binding_value)
        self.policy_reference=policy_reference;self.source_context_reference=source_context_reference
        self.installed_context_reference=installed_context_reference;self.release_binding_reference=release_binding_reference
        self.coverage_reference=coverage_reference;self.allocation_reference=allocation_reference
        self.source_guard_reference=source_guard_reference;self.program_reference=program_reference
        self.archive_program_reference=archive_program_reference;self.control_root=control_root;self.registry_root=registry_root
        self.staging_admission_reference=pin(staging_admission_reference)
        self.prepare_arguments=prepare_arguments;self.resume_request=resume_request;self.capture_request=capture_request
        self.recovery_arguments=recovery_arguments;self.series_specification=series_specification;self.adapter=adapter
        require(type(prepare_arguments) is dict and set(prepare_arguments)=={'source_refs','boot_sources',
            'controlled_sources','mysql','boot_connections','docker_sources'} and type(recovery_arguments) is dict and
            set(recovery_arguments)=={'approved_source','container_actions','maintenance_end','recovery_flows',
                'external_transport','host_native','health_probe','ingress_native'},'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        require(adapter is not None and all(callable(getattr(adapter,k,None)) for k in
            ('bind_original_author','bind_prepared','bind_capture_result','close',
             'verify_parent_repository','verify_catalog_sources','control_guard','source_guard',
             'protect_sources','failure_restore','observe_nas_admission',
             'observe_staging_admission','observe_control_budget')),'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')

    def bind(self,owner):
        from formal_capture_budget import CaptureBudget
        from formal_capture_incremental import CaptureSeries
        self.owner=owner
        for field,limit in (('policy',16384),('source_context',16384),('installed_context',16384),
                            ('release_binding',16384),('archive_program',1048576)):
            setattr(self,field,OriginalReference(getattr(self,field+'_reference'),owner=owner,limit=limit))
        require(self.policy.reference['sha256']==self.binding['capturePolicySha256'] and
            self.source_context.reference['sha256']==self.binding['sourceContextSha256'] and
            self.installed_context.reference['sha256']==self.binding['installedContextSha256'] and
            self.release_binding.reference['sha256']==self.binding['originalReleaseBindingSha256'] and
            sha(owner.claim._plan)==self.binding['claimBindingSha256'],'BACKUP_INTERFACE_BINDING_INVALID')
        self.native=ApprovedNativeAuthor(owner,self.program_reference,self.adapter)
        self.adapter.bind_original_author(owner,self.native)
        self.native.check()
        # Only the control author runs here and in the frozen interval. No SQL,
        # Docker or stopped-only source observer is installed as budget guard.
        self.budget=CaptureBudget(owner.claim,self.policy.raw,self.policy.reference['sha256'],
            attempt_id=self.binding['attemptId'],source_context_sha256=self.binding['sourceContextSha256'],
            guard=owner.check,deadline=owner.deadline)
        for root in (self.control_root,self.registry_root):
            self.budget.register_original_root(root,guard=owner.check)
        self.allocation=NativeAllocationSources(owner,binding_value=self.binding,policy_reference=self.policy_reference,
            coverage_reference=self.coverage_reference,allocation_reference=self.allocation_reference,
            source_guard_reference=self.source_guard_reference,control_root=self.control_root,registry_root=self.registry_root,
            native_author=self.native)
        self.series=CaptureSeries(self.series_specification,guard=owner.check)
        require(self.series.catalog['sourceLogicalBytes']<=self.budget.policy['totalBytes'] and
            self.series.catalog['temporaryPeakBytes']<=self.budget.policy['totalBytes'],
            'BACKUP_INTERFACE_CAPACITY_INSUFFICIENT')
        self.adapter.verify_catalog_sources(owner,self.series,self.prepare_arguments,self.capture_request,self.recovery_arguments)
        self.parent_observation=None
        if self.series.parent is not None:
            observed=self.adapter.verify_parent_repository(owner,self.series,owner.deadline)
            require(type(observed) is TrustedTransportObservation and observed.owner is owner and observed.author is self.native and
                strict_document(observed.raw,64*1024*1024)==self.series.repository_parent,
                'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
            observed.check();self.parent_observation=observed
        self.refs=[self.policy,self.source_context,self.installed_context,self.release_binding,self.archive_program,
            self.native.program,self.allocation.coverage,self.allocation.allocation,self.allocation.source_guard]

    def check(self):
        self.owner.check();self.native.check()
        for ref in self.refs:ref.check()
        self.series.check()
        if self.parent_observation is not None:self.parent_observation.check()

    def prepare(self):
        from formal_capture_producer import prepare_production_a_observed_normal_sources
        self.check()
        arguments=dict(self.prepare_arguments,release_binding_raw=self.release_binding.raw,
            guard=self.adapter.source_guard,deadline=self.owner.deadline)
        with self.budget.activate():
            original=prepare_production_a_observed_normal_sources(self.owner.claim,**arguments)
        prepared=PreparedOriginals(self.owner,original,self.budget,self)
        self.adapter.bind_prepared(prepared)
        with self.budget.activate():
            intent=prepare_intent(self.owner.claim,prepared=prepared,policy_raw=self.policy.raw,
                policy_sha256=self.policy.reference['sha256'],source_context_raw=self.source_context.raw,
                allocation_sources=self.allocation,guard=self.owner.check,deadline=self.owner.deadline)
        return prepared,intent

    def capture(self,prepared,admission):
        from formal_capture_producer import ProductionAResumeChecks,run_production_a_original_capture_recovery
        import formal_split_capture as split
        self.check();prepared.check();admission.check_budget(self.budget)
        # From this point originals are checked by the signed phase consumer,
        # whose checks allow the actual journal to grow. No stale preparation
        # guard is called after intentional source changes.
        admission.started=True
        self.budget.bind_full_capture_admission(admission)
        self.resume_checks=None
        capture_deadline=min(self.owner.deadline,time.monotonic()+self.series.catalog['stopWindowMilliseconds']/1000)
        outer=snapshot.observation_deadline.get()
        token=snapshot.observation_deadline.set(capture_deadline if outer is None else min(capture_deadline,outer))
        try:
            with self.budget.activate(),self.series.activate():
                if self.capture_request['schemaVersion']=='backup-lab-capture-request/v1':
                    from formal_backup_lab import LabResumeChecks, current_authority
                    authority=current_authority()
                    require(self.resume_request==dict(schemaVersion='backup-lab-resume-request/v1',labContextPin=authority.context_pin),
                            'BACKUP_LAB_RESUME_REQUEST_INVALID')
                    self.resume_checks=LabResumeChecks(self.owner.claim,self.release_binding.raw,prepared.inventory.raw,
                        prepared.inventory.reference['sha256'],authority,guard=self.owner.check,
                        thaw_guard=lambda:split._thaw_receipt(self.owner.claim))
                else:
                    self.resume_checks=ProductionAResumeChecks(self.owner.claim,self.release_binding.raw,prepared.inventory.raw,
                        prepared.inventory.reference['sha256'],self.resume_request,
                        guard=self.owner.check,thaw_guard=lambda:split._thaw_receipt(self.owner.claim))
                # Both live admissions and signed authority precede protection.
                self.adapter.protect_sources(self.owner,self.resume_checks,admission)
                self.adapter.source_guard();self.check();admission.check_budget(self.budget)
                result=run_production_a_original_capture_recovery(self.owner.claim,self.capture_request,
                    resume_checks=self.resume_checks,source_guard=self.adapter.source_guard,**self.recovery_arguments)
        finally:snapshot.observation_deadline.reset(token)
        require(type(result) is tuple and len(result)==2 and callable(result[1]) and
            result[0].get('state')=='A_ORIGINAL_CAPTURE_AND_RECOVERY_COMPLETED_PENDING_NAS',
            'BACKUP_INTERFACE_COMPONENT_FAILED')
        self.adapter.bind_capture_result(result)
        result[1]();self.check()
        self.point=self.series.point(source_restored=True)
        return result

    def archive_module(self):
        import importlib.util
        self.archive_program.check()
        name='formal_owner_archive_'+self.archive_program.reference['sha256'][:16]
        spec=importlib.util.spec_from_file_location(name,str(self.archive_program.path))
        require(spec is not None and spec.loader is not None,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        module=importlib.util.module_from_spec(spec)
        import sys
        require(name not in sys.modules,'BACKUP_INTERFACE_SEQUENCE_INVALID')
        sys.modules[name]=module
        # Execute the authenticated original bytes, not a second unpinned read.
        exec(compile(self.archive_program.raw,str(self.archive_program.path),'exec'),module.__dict__)
        self.archive_program.check()
        require(callable(getattr(module,'open_production_backup_archive_for_claim',None)) and
            callable(getattr(module,'serve_production_backup_archive',None)),
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        return module


def _control_budget(inputs,request):
    owner=inputs.owner
    observed=inputs.native.adapter.observe_control_budget(request,owner.deadline)
    require(type(observed) is TrustedTransportObservation and observed.owner is owner and
        observed.author is inputs.native and observed.reference==request['budget']['observationReference'] and
        observed.sequence==request['sequence'],'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    observed.check()
    value=strict_document(observed.raw)
    require(type(value) is dict and set(value)=={'sequence','remainingMilliseconds'} and
        value['sequence']==request['sequence'] and value['remainingMilliseconds']==
        request['budget']['remainingMilliseconds'],'BACKUP_INTERFACE_BINDING_INVALID')
    owner.deadline=remaining_deadline(value['remainingMilliseconds'],observed.sent,observed.received,owner.deadline)
    inputs.budget.deadline=min(inputs.budget.deadline,owner.deadline)


def run_owner(claim,*,inputs,control,guard,deadline):
    """Same claim/FD/thread: control -> original archive -> close -> return/exit.

    NAS readback is performed by the publisher while this owner is alive.
    There is no terminal finish message to a process that has already exited.
    """
    require(type(inputs) is NormalOwnerInputs and callable(guard),
        'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    owner=OriginalOwner(claim,guard=guard,deadline=deadline)
    require(type(control) is tuple and len(control)==2,'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    io=NativeControl(control[0],control[1],owner);inputs.bind(owner)
    failure_record=ReservedFailureRecord(owner,inputs.budget,inputs.control_root)
    sequence=ControlSequence(inputs.binding);state='BOUND_READONLY';prepared=intent=admission=manifest=None
    archive=reader=recovery=None;request=None;source_restored=False
    def remaining():
        owner.check();return integer(int((owner.deadline-time.monotonic())*1000),1,7200000)
    try:
        io.send(dict(schemaVersion='release-production-backup-owner-bound/v1',state=state,
            bootstrapBinding={k:inputs.binding[k] for k in BOOTSTRAP_FIELDS},binding=inputs.binding,
            nativeOriginalReferences=[r.reference for r in inputs.refs],ownerRemainingMilliseconds=remaining()))
        while True:
            request=None
            request=sequence.accept(io.receive(),state);_control_budget(inputs,request)
            action=request['action'];reference=None;chunk=None
            if action=='prepare':
                reference_input=OriginalReference(request['payloadReference'],owner=owner)
                require(reference_input.raw==canonical(inputs.series_specification),'BACKUP_INTERFACE_BINDING_INVALID')
                prepared,intent=inputs.prepare();state='PREPARED';reference=intent.reference.reference
            elif action=='admit':
                nas=OriginalReference(request['payloadReference'],owner=owner)
                local=LocalPreCaptureAdmission(intent,inputs.native,inputs.staging_admission_reference)
                admission=verify_admission(claim,intent_raw=intent.raw,nas_admission_raw=nas.raw,
                    admission_transport=inputs.native,local_admission=local,guard=owner.check,deadline=owner.deadline)
                state='PREFLIGHT_VALIDATED';reference=nas.reference
            elif action=='capture':
                approved=OriginalReference(request['payloadReference'],owner=owner,limit=65536)
                require(approved.raw==canonical(inputs.capture_request),'BACKUP_INTERFACE_BINDING_INVALID')
                state='CAPTURING';recovery=inputs.capture(prepared,admission)
                result,archive_guard=recovery;state='SOURCE_RESTORED';source_restored=True
                entries=result['sharedCapture']['capturedArchiveEntries']
                with inputs.budget.activate():
                    manifest=FixedManifest(owner,entries,inputs.budget,Path(inputs.control_root)/'archive-manifest.json')
                    point_ref=write_control_document(inputs.budget,inputs.control_root,'capture-point.json',inputs.point)
                    recovery_result_ref=write_control_document(inputs.budget,inputs.control_root,'original-source-recovery.json',result)
                    reference,_=write_control(inputs.budget,inputs.control_root,'capture-recovery.json',
                        dict(state='SOURCE_RESTORED_PENDING_NAS',sourceRestored=True,
                            disasterRecoveryVerified=False,capturePointReference=point_ref,
                            originalRecoveryReference=recovery_result_ref))
                recovery_ref=OriginalReference(reference,owner=owner)
                archive=inputs.archive_module()
                reader=archive.open_production_backup_archive_for_claim(claim,str(claim.root),entries,
                    inputs.binding['attemptId'],inputs.binding['sourceContextSha256'],
                    release_binding_raw=inputs.release_binding.raw,source_context_raw=inputs.source_context.raw,
                    installed_context_raw=inputs.installed_context.raw,guard=archive_guard,
                    capture_layout=True,capture_recovery=recovery)
                header=dict(schemaVersion='release-production-backup-archive-header/v1',binding=inputs.binding,
                    manifestReference=manifest.reference,treeDigest=reader.tree_digest,
                    fileCount=sum(v.startswith('file|') for v in entries.values()),
                    totalBytes=sum(int(v.split('|')[1]) for v in entries.values() if v.startswith('file|')),
                    recoveryReceiptReference=recovery_ref.reference,
                    archiveRemainingBudget=dict(remainingMilliseconds=remaining(),observationReference=recovery_ref.reference))
                with inputs.budget.activate():reference,_=write_control(inputs.budget,inputs.control_root,'archive-header.json',header)
                state='ARCHIVE_READY'
            elif action=='read-manifest':
                reading=OriginalReference(request['payloadReference'],owner=owner)
                offset=validate_manifest_read(reading.raw,manifest.reference)
                chunk=manifest.chunk(offset);reference=manifest.reference
            elif action=='begin-archive':
                require(manifest.finished,'BACKUP_INTERFACE_SEQUENCE_INVALID')
                reader._current();state='ARCHIVE_SERVING';reference=manifest.reference
            else:
                inputs.check()
                if reader is not None:reader._current()
            io.send(dict(schemaVersion=CONTROL_SCHEMA,binding=inputs.binding,sequence=request['sequence'],action=action,
                state=state,resultReference=reference,chunk=chunk,ownerRemainingMilliseconds=remaining(),failureCode=None))
            if action=='begin-archive':
                io.begin_archive()
                closed=archive.serve_production_backup_archive(reader,io.request_fd,io.response_fd,
                    deadline=owner.deadline,idle_seconds=min(60,max(.001,owner.deadline-time.monotonic())))
                require(reader.closed and closed['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF',
                    'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
                owner.check()
                return dict(state='OWNER_CLOSE_CONFIRMED_PENDING_ORIGINAL_EXIT',sourceRestored=True,
                    disasterRecoveryVerified=False,close=closed,claimReleased=False,nasArchiveVerified=False)
    except BaseException as error:
        # Never replace a failure with a source restoration success. A native
        # explicit recovery author may act only on its exact signed journal;
        # uncertain action/expired authority leaves protection and bytes held.
        actual=getattr(error,'code','BACKUP_INTERFACE_COMPONENT_FAILED')
        terminal='TERMINAL_UNKNOWN' if getattr(error,'clientCleanupUncertain',False) or state=='CAPTURING' else 'FAILED_RETAINED'
        recovery_state=None
        if state in {'CAPTURING','SOURCE_RESTORED'} and time.monotonic()<owner.deadline:
            try:
                recovered=inputs.adapter.failure_restore(owner,getattr(inputs,'resume_checks',None),error)
                require(type(recovered) is tuple and len(recovered)==2 and callable(recovered[1]),
                    'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
                recovery_state=recovered[0];recovered[1]();owner.check();inputs.native.check()
                require(type(recovery_state) is dict and recovery_state.get('sourceRestored') is True and
                    recovery_state.get('disasterRecoveryVerified') is False,'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
                source_restored=True
                if not getattr(error,'clientCleanupUncertain',False):terminal='FAILED_RETAINED'
            except BaseException as recovery_error:
                terminal='TERMINAL_UNKNOWN';actual=getattr(recovery_error,'code','BACKUP_INTERFACE_TERMINAL_UNKNOWN')
                error.recoveryFailureCode=actual
        # These fixed fields contain no exception text, argv or credentials.
        failure=dict(state=terminal,failureCode=actual,sourceRestored=source_restored,
            disasterRecoveryVerified=False,claimReleased=False)
        try:
            failure_record.record(failure)
        except BaseException as recording_error:
            error.failureRecordError=getattr(recording_error,'code',type(recording_error).__name__)
        if request is not None and not io.switched and time.monotonic()<owner.deadline:
            wire_code=actual if actual in INTERFACE_FAILURE_CODES else 'BACKUP_INTERFACE_COMPONENT_FAILED'
            try:
                io.send(dict(schemaVersion=CONTROL_SCHEMA,binding=inputs.binding,sequence=request['sequence'],
                    action=request['action'],state=terminal,resultReference=None,chunk=None,
                    ownerRemainingMilliseconds=max(0,min(7200000,int((owner.deadline-time.monotonic())*1000))),
                    failureCode=wire_code))
            except BaseException as response_error:
                error.failureResponseError=getattr(response_error,'code',type(response_error).__name__)
        error.ownerTerminalState=terminal
        error.sourceRestored=source_restored
        raise
    finally:failure_record.close()
