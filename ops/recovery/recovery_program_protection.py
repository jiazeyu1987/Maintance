"""Keep original MAIN protection custody across a proved program transition.

Only the current, same-context native supplies transport. The private original
target supplies protection identities and digest inputs; no old native command
or generic configuration exception is retained. Lifecycle evidence can still be
read after failure, without authorizing another command.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
from types import SimpleNamespace

from recovery_backup_epoch import _path, _read_file, _regular, _signature
from recovery_archive_view import select_configuration
from recovery_engine import RecoveryError, require, utc
from recovery_retained_retry import append
from recovery_program_execution import _directory
from recovery_program_generation import APPLICATIONS, _services
from recovery_program_native import _NativeView


KINDS = ('archive','fence','scheduler')
JOURNALS = {'archive':'archive-view','fence':'published-fence','scheduler':'mysql-scheduler'}
RELEASE_KEYS = {'archive':'archiveViewReleasePin','fence':'publishedWriteFenceReleasePin',
                'scheduler':'mysqlSchedulerReleasePin'}
FILES = {'archive':{'intent.json','active.json','released.json'},
         'fence':{'intent.json','active.json','ipv4-installed.json','ipv6-installed.json','released.json'},
         'scheduler':{'intent.json','active.json','release-intent.json','released.json','recovery-custody.json'}}


def _scope(target):
    """Compare every target field except the already-proved program changes."""
    value=deepcopy(target);services=_services(value)
    ids={services[role]['id'] for role in APPLICATIONS}
    value.pop('dataRoot',None)  # The context proves the exact runtime directory.
    for role in APPLICATIONS:
        services[role].pop('id');services[role].pop('imageId')
        replacement=value['replacement']['services'][role]
        for key in ('id','imageId','labels'):replacement.pop(key,None)
        replacement['mounts']=sorted(replacement['mounts'],key=lambda row:row['Destination'])
    main=value['mainApplication']
    for field in ('serviceConfigurationDigests','networkAttachments'):
        for role in APPLICATIONS:main[field].pop(role)
    for network in main['networks']:
        network['memberContainerIds']=[identity for identity in network['memberContainerIds'] if identity not in ids]
    for row in main['archiveImageBindings']:
        if row['role'] in APPLICATIONS:row.pop('imageId')
    for field in ('approvedWriterContainerIds','evidencePin'):main['writerAdmission'].pop(field)
    return value


def _references(value):
    if type(value) is dict:
        if set(value)=={'path','bytes','sha256'}:
            yield value
        else:
            for item in value.values():yield from _references(item)
    elif type(value) is list:
        for item in value:yield from _references(item)


class _Protection:
    def __init__(self,custody,native,kind):
        self._custody,self._native,self._kind=custody,native,kind

    @property
    def configuration(self):
        self._custody._validate(self._native)
        value=self._custody._construct(self._native,self._kind)
        return deepcopy(value.target if self._kind=='scheduler' else value.configuration)

    @property
    def binding(self):
        self._custody._validate(self._native)
        return self._custody._construct(self._native,self._kind).binding

    @property
    def journal(self):
        self._custody._validate(self._native)
        return self._custody._claim/JOURNALS[self._kind]

    def preflight(self):return self._custody._invoke(self._native,self._kind,'preflight')
    def install(self):return self._custody._invoke(self._native,self._kind,'install')
    def verify(self):return self._custody._invoke(self._native,self._kind,'verify')
    def release(self):return self._custody._invoke(self._native,self._kind,'release')


def _preservation_root(context):
    path=context._root/'target-preservation'
    identity=getattr(context,'_target_preservation_directory',None)
    if identity is None:
        require(not os.path.lexists(path),'PROGRAM_CAPTURE_ALREADY_CLAIMED')
        path.mkdir(mode=0o700)
        context._target_preservation_directory=_directory(path,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
    else:
        require(_directory(path,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')==identity,
                'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
    return path


class _TargetCaptureProtectionLease:
    """Narrow 1/1 capability; it never releases any original protection.

    Closing this object only ends local admission. Even a closed or failed lease
    remains attached to its context and prevents stage/release without a formal
    preservation handoff. Phase one deliberately has no successful handoff API.
    """
    def __init__(self,custody,native):
        self._custody,self._native,self._context=custody,native,custody._context
        self._state,self._closed='CLAIMED',False
        self._pins={};self._process=None;self._export_pid=None
        self._root=_preservation_root(self._context)/'protection'
        require(not os.path.lexists(self._root),'PROGRAM_CAPTURE_ALREADY_CLAIMED')
        self._root.mkdir(mode=0o700)
        self._identity=_directory(self._root,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
        self._scheduler_active=deepcopy(custody._journals['scheduler']['pins']['active.json'])
        self._scheduler_intent=deepcopy(custody._journals['scheduler']['pins']['intent.json'])

    @property
    def handed_off(self):return False

    def check(self):
        """Local immutable-file check only: no SQL, Docker or guard recursion."""
        require(not self._closed,'PROGRAM_CAPTURE_CLOSED')
        require(self._state!='FAILED_RETAINED','PROGRAM_CAPTURE_FAILED_RETAINED')
        require(_directory(self._root,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')==self._identity,
                'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
        require(_directory(self._root.parent,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')==
                self._context._target_preservation_directory,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
        require({p.name for p in self._root.iterdir()}=={Path(p).name for p in self._pins},
                'PROGRAM_CAPTURE_JOURNAL_CHANGED')
        for reference in self._pins.values():
            _,actual=_read_file(reference['path'],4*1024*1024)
            require(actual==reference,'PROGRAM_CAPTURE_JOURNAL_CHANGED')

    def _guard(self):
        self.check()
        view=self._custody._validate(self._native)
        require(view.phase=='PREPARATION' and view._context is self._context,
                'PROGRAM_CAPTURE_PREPARATION_REQUIRED')
        require(self._custody._state=='ACTIVE','PROGRAM_CAPTURE_PROTECTION_CHANGED')
        require(all(self._custody._steps[k]['state']=='INSTALLED' for k in KINDS),
                'PROGRAM_CAPTURE_PROTECTION_NOT_INSTALLED')
        require(self._custody._journals['scheduler']['pins']['active.json']==self._scheduler_active and
                self._custody._journals['scheduler']['pins']['intent.json']==self._scheduler_intent,
                'PROGRAM_CAPTURE_SCHEDULER_CHANGED')

    def _record(self,name,value):
        reference=append(self._root/name,value)
        self._pins[reference['path']]=deepcopy(reference)
        if reference not in self._native.original_pins:self._native.original_pins.append(deepcopy(reference))
        return reference

    def _scheduler_matches(self,scheduler):
        return scheduler.target==self._custody._target and scheduler.operation_id==self._context._request['operationId'] and \
            scheduler.journal==self._custody._claim/JOURNALS['scheduler'] and \
            self._custody._active==(self._native,'scheduler','capture')

    def _export_state(self):
        """Observe the owned child without stealing the original drain's reap."""
        if self._process is None:return None
        require(self._export_pid==os.getpid() and self._process.pid==self._process_identity,
                'PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED')
        if self._process.returncode is not None:return 'REAPED'
        try:
            observed=os.waitid(os.P_PID,self._process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
        except ChildProcessError as error:
            raise RecoveryError('PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED') from error
        if observed is None:return 'RUNNING'
        require(observed.si_pid==self._process.pid,'PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED')
        return 'EXITED_UNREAPED'

    def _export_in_progress(self):
        return self._export_state()=='RUNNING'

    def _register_export(self,process):
        import subprocess
        self._guard()
        require(type(process) is subprocess.Popen and self._process is None and process.poll() is None,
                'PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED')
        self._process,self._process_identity,self._export_pid=process,process.pid,os.getpid()

    def _finish_export(self,process):
        require(process is self._process and self._export_pid==os.getpid() and process.poll() is not None,
                'PROGRAM_CAPTURE_EXPORT_TERMINAL_REQUIRED')
        self._process=None;self._export_pid=None
        self.verify()

    def _scheduler(self,action):
        self._guard()
        custody=self._custody
        require(custody._active is None,'PROGRAM_PROTECTION_INVOCATION_PENDING')
        custody._active=(self._native,'scheduler','capture')
        try:
            scheduler=custody._construct(self._native,'scheduler')
            if action=='before':return scheduler.verify()
            require(action in ('begin','verify'),'PROGRAM_CAPTURE_ACTION_INVALID')
            if action=='begin':
                scheduler.query('SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;',mutation=True)
            return scheduler._verify_capture(self)
        finally:custody._active=None

    def _external_protections(self):
        self._custody._invoke(self._native,'archive','verify')
        self._custody._invoke(self._native,'fence','verify')

    def begin(self):
        self._guard()
        require(self._state=='CLAIMED','PROGRAM_CAPTURE_ALREADY_CLAIMED')
        try:
            self._external_protections();self._scheduler('before')
            intent=self._record('capture-fence-intent.json',dict(schemaVersion='MainTargetCaptureFenceIntent/v1',
                operationId=self._context._request['operationId'],bindingPin=deepcopy(self._context._binding),
                databaseUuid=self._custody._target['replacement']['databaseUuid'],originalFlags=[0,0],
                schedulerIntentPin=self._scheduler_intent,schedulerActivePin=self._scheduler_active,startedAt=utc()))
            self._state='STARTING'
            _,observation=self._scheduler('begin')
            self._record('capture-fence-active.json',dict(schemaVersion='MainTargetCaptureFenceActive/v1',
                operationId=self._context._request['operationId'],intentPin=intent,
                databaseBarrier=observation,sourceRestored=False,activatedAt=utc()))
            self._state='ACTIVE';self.verify()
        except BaseException:
            self._state='FAILED_RETAINED'
            raise

    def verify(self):
        self._guard()
        require(self._state=='ACTIVE','PROGRAM_CAPTURE_NOT_ACTIVE')
        try:
            self._external_protections();self._scheduler('verify');self._guard()
        except BaseException:
            self._state='FAILED_RETAINED'
            raise

    def handoff(self,verified_preservation):
        raise RecoveryError('PROGRAM_CAPTURE_PRESERVATION_REQUIRED')

    def snapshot(self):
        return dict(schemaVersion='MainTargetCaptureProtection/v1',operationId=self._context._request['operationId'],
            state=self._state,sourceRestored=False,schedulerIntentPin=deepcopy(self._scheduler_intent),
            schedulerActivePin=deepcopy(self._scheduler_active),
            captureFenceActivePin=deepcopy(self._pins.get(str(self._root/'capture-fence-active.json'))),
            originalResultPins=deepcopy(list(self._pins.values())))

    def close(self):
        self._closed=True


class ProtectionCustody:
    @classmethod
    def from_preparation(cls,native):
        return cls(native)

    def __init__(self,native):
        view=self._view(native)
        view.guard()
        require(view.phase=='PREPARATION','PROGRAM_PROTECTION_PREPARATION_REQUIRED')
        self._context=view._context
        self._request=deepcopy(self._context._request)
        self._target=deepcopy(view.configuration['targets'][self._request['targetConfigRef']])
        self._source,self._policy=deepcopy(native.source),deepcopy(native.policy)
        self._scope=_scope(self._target)
        self._claim=Path(self._target['replacement']['stateRoot'])/self._request['operationId']
        require(self._claim==self._context._claim,'PROGRAM_PROTECTION_JOURNAL_CHANGED')
        self._claim_identity=_directory(self._claim,'PROGRAM_PROTECTION_JOURNAL_CHANGED')
        self._state,self._active='ACTIVE',None
        self._pins,self._inputs={},{}
        self._journals={kind:dict(identity=None,pins={}) for kind in KINDS}
        self._steps={kind:dict(state='NOT_INSTALLED') for kind in KINDS}
        for reference in _references([self._target['secrets'],
                select_configuration(self._target,self._source),
                self._target['mainApplication'].get('publishedDataEndpoints',[])]):
            require(reference['path'] not in self._inputs or self._inputs[reference['path']]==reference,
                    'PROGRAM_PROTECTION_INPUT_CHANGED')
            self._inputs[reference['path']]=deepcopy(reference)
        self._validate(native)
        self._present={kind:self._construct(native,kind) is not None for kind in KINDS}
        for kind in KINDS:
            require(not (self._claim/JOURNALS[kind]).exists(),'PROGRAM_PROTECTION_ALREADY_CLAIMED')
            if not self._present[kind]:self._steps[kind]['state']='ABSENT'

    @staticmethod
    def _view(native):
        view=getattr(native,'native_context',None)
        require(type(view) is _NativeView,'PROGRAM_PROTECTION_VIEW_INVALID')
        return view

    def _input(self,reference,guard):
        require(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
                type(reference['bytes']) is int and 0<=reference['bytes']<=2**63-1 and
                type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}',reference['sha256']),
                'PROGRAM_PROTECTION_INPUT_CHANGED')
        path=_path(reference['path']);before=path.stat();_regular(before)
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        checksum=hashlib.sha256();size=0
        try:
            opened=os.fstat(descriptor);_regular(opened)
            require(_signature(opened)==_signature(before),'PROGRAM_PROTECTION_INPUT_CHANGED')
            with os.fdopen(descriptor,'rb',closefd=False) as stream:
                while True:
                    guard();chunk=stream.read(65536)
                    if not chunk:break
                    size+=len(chunk);checksum.update(chunk)
                    require(size<=reference['bytes'],'PROGRAM_PROTECTION_INPUT_CHANGED')
            require(_signature(opened)==_signature(os.fstat(descriptor))==_signature(path.stat()),
                    'PROGRAM_PROTECTION_INPUT_CHANGED')
        finally:os.close(descriptor)
        require(size==reference['bytes'] and checksum.hexdigest()==reference['sha256'],
                'PROGRAM_PROTECTION_INPUT_CHANGED')

    def _validate(self,native):
        view=self._view(native)
        require(view._context is self._context,'PROGRAM_PROTECTION_CONTEXT_CHANGED')
        view.guard()
        require(native.original==self._request and native.original==self._context._request,
                'PROGRAM_PROTECTION_REQUEST_CHANGED')
        require(native.budget is view.budget and native.budget is self._context.budget,
                'PROGRAM_PROTECTION_BUDGET_CHANGED')
        require(native.config==view.configuration['targets'][self._request['targetConfigRef']],
                'PROGRAM_PROTECTION_CONFIGURATION_CHANGED')
        require(native.source==self._source and native.policy==self._policy,'PROGRAM_PROTECTION_SOURCE_CHANGED')
        require(native.config_services==_services(native.config) and
                native.db_container==_services(self._target)['mysql']['id'],
                'PROGRAM_PROTECTION_SERVICE_CHANGED')
        require(_scope(native.config)==self._scope,'PROGRAM_PROTECTION_SCOPE_CHANGED')
        require(type(native.original_pins) is list,'PROGRAM_PROTECTION_EVIDENCE_REQUIRED')
        require(_directory(self._claim,'PROGRAM_PROTECTION_JOURNAL_CHANGED')==self._claim_identity,
                'PROGRAM_PROTECTION_JOURNAL_CHANGED')
        for reference in self._inputs.values():self._input(reference,view.guard)
        self._verify_journals()
        view.guard()
        return view

    def _verify_journals(self):
        try:
            for kind,record in self._journals.items():
                path=self._claim/JOURNALS[kind]
                working=self._active is not None and self._active[1]==kind
                if path.exists():
                    identity=_directory(path,'PROGRAM_PROTECTION_JOURNAL_CHANGED')
                    if record['identity'] is None:
                        require(working,'PROGRAM_PROTECTION_JOURNAL_CHANGED');record['identity']=identity
                    require(identity==record['identity'],'PROGRAM_PROTECTION_JOURNAL_CHANGED')
                    files={p.name for p in path.iterdir()}
                    require(files<=FILES[kind] and (working or files==set(record['pins'])),
                            'PROGRAM_PROTECTION_JOURNAL_CHANGED')
                else:
                    require(record['identity'] is None and not record['pins'],'PROGRAM_PROTECTION_JOURNAL_CHANGED')
                for name,reference in record['pins'].items():
                    _,observed=_read_file(path/name,4*1024*1024)
                    require(observed==reference,'PROGRAM_PROTECTION_JOURNAL_CHANGED')
        except (OSError,ValueError) as error:
            raise RecoveryError('PROGRAM_PROTECTION_JOURNAL_CHANGED') from error

    def _publish(self,native):
        for reference in [*self._inputs.values(),*self._pins.values()]:
            if reference not in native.original_pins:native.original_pins.append(deepcopy(reference))

    def _capture(self,native,kind):
        self._verify_journals()
        path=self._claim/JOURNALS[kind]
        if path.exists():
            for item in sorted(path.iterdir()):
                _,reference=_read_file(item,4*1024*1024)
                old=self._journals[kind]['pins'].get(item.name)
                require(old is None or old==reference,'PROGRAM_PROTECTION_JOURNAL_CHANGED')
                self._journals[kind]['pins'][item.name]=reference
                self._pins[reference['path']]=reference
        self._publish(native)

    def _construct(self,native,kind):
        import recovery_main_target as main
        def execute(arguments,**kwargs):
            require(self._active is not None and self._active[:2]==(native,kind),
                    'PROGRAM_PROTECTION_TRANSPORT_REQUIRED')
            self._validate(native)
            result=native.command(arguments,**kwargs)
            self._validate(native)
            return result
        def query(statement,*,mutation=False):
            require(self._active is not None and self._active[:2]==(native,kind),
                    'PROGRAM_PROTECTION_TRANSPORT_REQUIRED')
            self._validate(native)
            result=main.mysql_query(native,statement,mutation=mutation)
            self._validate(native)
            return result
        original=SimpleNamespace(config=deepcopy(self._target),original=deepcopy(self._request),
            source=deepcopy(self._source),command=execute)
        if kind=='archive':return main.archive_view(original)
        if kind=='fence':return main.published_fence(original)
        return main.mysql_scheduler(original,query=query)

    def view_for(self,native):
        self._validate(native);self._publish(native)
        return SimpleNamespace(**{kind:_Protection(self,native,kind) if self._present[kind] else None for kind in KINDS})

    def capture_view_for(self,native):
        view=self._validate(native)
        require(view.phase=='PREPARATION','PROGRAM_CAPTURE_PREPARATION_REQUIRED')
        require(self._state=='ACTIVE','PROGRAM_CAPTURE_PROTECTION_CHANGED')
        require(all(self._steps[k]['state']=='INSTALLED' for k in KINDS),
                'PROGRAM_CAPTURE_PROTECTION_NOT_INSTALLED')
        require(getattr(self._context,'_target_capture_lease',None) is None,'PROGRAM_CAPTURE_ALREADY_CLAIMED')
        lease=_TargetCaptureProtectionLease(self,native)
        self._context._target_capture_lease=lease
        return lease

    def _invoke(self,native,kind,method):
        view=self._validate(native)
        require(self._state!='RELEASED','PROGRAM_PROTECTION_ALREADY_RELEASED')
        require(self._state!='FAILED_RETAINED','PROGRAM_PROTECTION_FAILED_RETAINED')
        require(self._active is None,'PROGRAM_PROTECTION_INVOCATION_PENDING')
        state=self._steps[kind]['state']
        if method in ('preflight','install'):
            require(view.phase=='PREPARATION','PROGRAM_PROTECTION_INSTALL_PHASE')
            require(state=='NOT_INSTALLED','PROGRAM_PROTECTION_ALREADY_CLAIMED')
            if method=='install':
                require(all(self._steps[before]['state'] in ('INSTALLED','ABSENT') for before in KINDS[:KINDS.index(kind)]),
                        'PROGRAM_PROTECTION_INSTALL_ORDER')
        else:
            require(state=='INSTALLED','PROGRAM_PROTECTION_NOT_INSTALLED')
            if method=='release':
                lease=getattr(self._context,'_target_capture_lease',None)
                require(lease is None or lease.handed_off,'PROGRAM_TARGET_CAPTURE_PENDING')
                require(view.phase=='RESTORE','PROGRAM_PROTECTION_RELEASE_PHASE')
                require(all(self._steps[before]['state'] in ('RELEASED','ABSENT') for before in KINDS[:KINDS.index(kind)]),
                        'PROGRAM_PROTECTION_RELEASE_ORDER')
        self._active=(native,kind,method)
        try:
            result=getattr(self._construct(native,kind),method)()
            self._validate(native);self._capture(native,kind)
            if method=='install':self._steps[kind]['state']='INSTALLED'
            if method=='release':self._steps[kind].update(state='RELEASED',releasePin=deepcopy(result))
            return result
        except BaseException as error:
            self._state='FAILED_RETAINED'
            self._steps[kind].update(state='FAILED_RETAINED',failedMethod=method,
                errorCode=getattr(error,'code',type(error).__name__))
            try:self._capture(native,kind)
            except BaseException as recording:
                fault=RecoveryError('PROGRAM_PROTECTION_EVIDENCE_FAILED',unknown=True)
                fault.original_code=getattr(error,'code',type(error).__name__)
                fault.recording_error=type(recording).__name__
                raise fault from error
            raise
        finally:self._active=None

    def release(self,native):
        self._validate(native)
        lease=getattr(self._context,'_target_capture_lease',None)
        require(lease is None or lease.handed_off,'PROGRAM_TARGET_CAPTURE_PENDING')
        require(self._state!='RELEASED','PROGRAM_PROTECTION_ALREADY_RELEASED')
        result={}
        for kind in KINDS:
            if self._present[kind]:result[RELEASE_KEYS[kind]]=self._invoke(native,kind,'release')
        self._state='RELEASED'
        return result

    def snapshot(self):
        """Metadata only: no transport, guard exception, retry or release grant."""
        self._verify_journals()
        return dict(schemaVersion='MainProgramProtectionCustody/v1',operationId=self._request['operationId'],
            state=self._state,protections=deepcopy(self._steps),
            originalResultPins=deepcopy([*self._inputs.values(),*self._pins.values()]))
