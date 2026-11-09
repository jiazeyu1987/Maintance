"""One complete read-only Spug observation; private custody and bounded progress.

This is task tooling, not a job scheduler. Unknown executions retain the single
container gate. Query never restarts a worker or interprets absence as success.
"""
import json
from contextlib import contextmanager
import math
import os
from pathlib import Path
import re
import subprocess
from subprocess import Popen
import time
import uuid

import main_program_spug_publication as publication

PREFIX=b'SPUG_OBSERVATION_PROGRESS '
PHASES=('configuration','routes','catalogue','history','ledger','auxiliary','modules','complete')


def need(value,code):
    if not value:raise ValueError('MAIN_RESOURCE_OBSERVATION_'+code)


def save(path,value):return publication.exclusive_bytes(path,publication.canonical(value))


def read(path):
    publication.file_pin(path)
    return json.loads(Path(path).read_bytes())


@contextmanager
def gate_guard(private):
    """Serialize only local gate transitions; an interrupted guard fails closed."""
    path=Path(private)/('resource-observation-'+publication.CONTAINER+'.mutex.private.json')
    try:reference=save(path,dict(owner=os.getpid(),nonce=uuid.uuid4().hex))
    except FileExistsError:raise ValueError('MAIN_RESOURCE_OBSERVATION_GATE_BUSY') from None
    try:yield
    finally:
        need(publication.file_pin(path)==reference,'GATE_MUTEX_CHANGED')
        path.unlink()


def worker_program(program,nonce,hard_seconds):
    # The nonce is an argv argument, independently visible through /proc/cmdline.
    prelude=r'''
import json,os,sys,time,signal,warnings
from pathlib import Path
_observation_seq=0
if os.name=='nt':
 import ctypes
 from ctypes import wintypes
 class _FT(ctypes.Structure):_fields_=[('low',wintypes.DWORD),('high',wintypes.DWORD)]
 _times=[_FT() for _ in range(4)]
 _kernel=ctypes.windll.kernel32
 _kernel.GetCurrentProcess.restype=wintypes.HANDLE
 _kernel.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(_FT)]*4
 if not _kernel.GetProcessTimes(_kernel.GetCurrentProcess(),*[ctypes.byref(t) for t in _times]):raise OSError('PROCESS_IDENTITY')
 _ticks=str((_times[0].high<<32)|_times[0].low)
 _argv=[sys.executable,'-B','-',sys.argv[-1]]
else:
 _ticks=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19]
 _argv=Path('/proc/self/cmdline').read_bytes().decode().rstrip('\0').split('\0')
 def _expired(signum,frame):raise TimeoutError('OBSERVATION_HARD_DEADLINE')
 signal.signal(signal.SIGALRM,_expired);signal.alarm(HARD_SECONDS)
_observation_identity=dict(pid=os.getpid(),startTicks=_ticks,argv=_argv)
_observation_last=dict(phase='configuration',completedFiles=0,completedBytes=0)
def _observation_emit(event,**values):
 global _observation_seq
 _observation_seq+=1
 row=dict(schemaVersion='SpugObservationProgress/v1',operationNonce=NONCE,event=event,
          sequence=_observation_seq,identity=_observation_identity,**values)
 sys.stderr.write('SPUG_OBSERVATION_PROGRESS '+json.dumps(row,separators=(',',':'))+'\n');sys.stderr.flush()
def _observation_progress(phase,files=None,bytes_count=None):
 global _observation_last
 if files is None:files=_observation_last['completedFiles']
 if bytes_count is None:bytes_count=_observation_last['completedBytes']
 _observation_last=dict(phase=phase,completedFiles=files,completedBytes=bytes_count)
 _observation_emit('PROGRESS',**_observation_last)
_observation_emit('START')
def _observation_showwarning(message,category,filename,lineno,file=None,line=None):
 _observation_emit('WARNING',warningCategory=dict(module=category.__module__,name=category.__name__),
     formattedWarning=warnings.formatwarning(message,category,filename,lineno,line))
warnings.showwarning=_observation_showwarning
'''
    return ('NONCE='+repr(nonce)+'\nHARD_SECONDS='+str(max(1,math.ceil(hard_seconds)))+'\n'+prelude+
            '\nexec(compile('+repr(program)+",'<complete-spug-observation>','exec'),globals())\n"+
            "_observation_emit('DONE',**_observation_last)\n").encode('utf-8')


class Observation:
    def __init__(self,private,identity,*,operation_id=None,idle_seconds=900,hard_seconds=1800):
        need(type(idle_seconds) in (int,float) and type(hard_seconds) in (int,float) and
             0<idle_seconds<=900 and idle_seconds<=hard_seconds<=1800,'BUDGET_INVALID')
        need(type(identity) is dict and set(identity)=={'sourceCommit','inputPins'} and
             re.fullmatch('[0-9a-f]{40}',identity['sourceCommit']) and type(identity['inputPins']) is list,'INPUT_IDENTITY_INVALID')
        self.private=Path(private).resolve(strict=True);self.identity=identity
        self.operation_id=operation_id or uuid.uuid4().hex
        need(re.fullmatch('[0-9a-f]{32}',self.operation_id),'OPERATION_ID_INVALID')
        self.nonce='spug-observation-'+self.operation_id
        self.directory=self.private/('resource-observation-'+self.operation_id)
        self.gate=self.private/('resource-observation-'+publication.CONTAINER+'.gate.private.json')
        self.idle_seconds=idle_seconds;self.hard_seconds=hard_seconds
        self.started=None;self.last_work=None;self.worker_identity=None;self.last_progress=None
        self.sequence=0;self.phase_index=-1;self.files=0;self.bytes=0;self.done=False
        self.warning_records=[];self.warning_categories={}
        self.dispatched=False;self.remote_exit=False;self.exit_code=None;self.process=None
        self.stdout_path=self.directory/'stdout.private.log';self.stderr_path=self.directory/'stderr.private.log'

    def __enter__(self):
        self.started=self.last_work=time.monotonic()
        with gate_guard(self.private):
            need(not self.gate.exists(),'PREVIOUS_UNRESOLVED')
            need(not self.directory.exists(),'OPERATION_EXISTS')
            gate=dict(schemaVersion='SpugObservationGate/v1',containerId=publication.CONTAINER,operationId=self.operation_id)
            try:self.gate_pin=save(self.gate,gate)
            except FileExistsError:raise ValueError('MAIN_RESOURCE_OBSERVATION_PREVIOUS_UNRESOLVED') from None
            # If local receipt creation fails, retain the gate rather than silently dispatch.
            self.directory.mkdir()
            save(self.directory/'request.private.json',dict(schemaVersion='SpugObservationRequest/v1',
                operationId=self.operation_id,containerId=publication.CONTAINER,nonce=self.nonce,
                identity=self.identity,idleSeconds=self.idle_seconds,hardSeconds=self.hard_seconds))
        return self

    def remaining(self):
        now=time.monotonic()
        need(now-self.started<self.hard_seconds,'HARD_DEADLINE')
        need(now-self.last_work<self.idle_seconds,'STALLED')
        return min(self.hard_seconds-(now-self.started),self.idle_seconds-(now-self.last_work))

    def short_command(self,command,*args,**kwargs):
        remaining=self.remaining();maximum=min(240,remaining)
        # Existing CLI wrapper accepts integer budgets; tests use subsecond bounds.
        budget=math.floor(maximum) if maximum>=1 else maximum
        result=command(*args,timeout=budget,**kwargs)
        self.remaining();self.last_work=time.monotonic()
        return result

    def progress(self,raw):
        need(raw.startswith(PREFIX),'STDERR_UNEXPECTED')
        try:row=json.loads(raw[len(PREFIX):])
        except (ValueError,UnicodeError):raise ValueError('MAIN_RESOURCE_OBSERVATION_PROTOCOL_INVALID') from None
        basic={'schemaVersion','operationNonce','event','sequence','identity'}
        need(type(row) is dict and row.get('schemaVersion')=='SpugObservationProgress/v1' and
             row.get('operationNonce')==self.nonce and type(row.get('sequence')) is int and row['sequence']==self.sequence+1,
             'PROTOCOL_INVALID')
        ident=row.get('identity')
        need(type(ident) is dict and set(ident)=={'pid','startTicks','argv'} and type(ident['pid']) is int and ident['pid']>1 and
             type(ident['startTicks']) is str and re.fullmatch('[0-9]+',ident['startTicks']) and
             type(ident['argv']) is list and len(ident['argv'])==4 and ident['argv'][-3:]==['-B','-',self.nonce],
             'WORKER_IDENTITY_INVALID')
        if row['event']=='START':
            need(set(row)==basic and self.worker_identity is None and self.sequence==0,'PROTOCOL_INVALID')
            self.worker_identity=ident
            save(self.directory/'worker.private.json',ident)
        elif row['event']=='WARNING':
            need(ident==self.worker_identity,'WORKER_IDENTITY_CHANGED')
            need(set(row)==basic|{'warningCategory','formattedWarning'},'WARNING_PROTOCOL_INVALID')
            category=row['warningCategory'];formatted=row['formattedWarning']
            need(type(category) is dict and set(category)=={'module','name'} and
                 all(type(category[key]) is str and 0<len(category[key])<=256 for key in ('module','name')) and
                 all(part.isidentifier() for part in category['module'].split('.')) and category['name'].isidentifier(),
                 'WARNING_CATEGORY_INVALID')
            need(type(formatted) is str and 0<len(formatted.encode('utf-8'))<=8192,'WARNING_TEXT_INVALID')
            reference=save(self.directory/('warning-'+str(row['sequence'])+'.private.json'),row)
            self.warning_records.append(reference)
            key=category['module']+'.'+category['name']
            self.warning_categories[key]=self.warning_categories.get(key,0)+1
            # Diagnostics never count as completed work or modify last progress.
        else:
            need(ident==self.worker_identity and not self.done,'WORKER_IDENTITY_CHANGED')
            need(set(row)==basic|{'phase','completedFiles','completedBytes'} and row['phase'] in PHASES and
                 type(row['completedFiles']) is int and type(row['completedBytes']) is int,'PROTOCOL_INVALID')
            phase=PHASES.index(row['phase']);files=row['completedFiles'];size=row['completedBytes']
            need(phase>=self.phase_index and files>=self.files and size>=self.bytes,'PROGRESS_REGRESSED')
            need(files!=self.files or size==self.bytes,'PROGRESS_COUNTS_INVALID')
            need(row['event'] in ('PROGRESS','DONE'),'PROTOCOL_INVALID')
            if row['event']=='DONE':
                need(row['phase']=='complete' and self.phase_index==len(PHASES)-1,'RESULT_INCOMPLETE')
                self.done=True
            elif phase>self.phase_index or files>self.files:
                self.last_work=time.monotonic()
            self.phase_index=phase;self.files=files;self.bytes=size;self.last_progress=row
        self.sequence=row['sequence']

    def run(self,program):
        need(not self.dispatched,'ALREADY_DISPATCHED');self.remaining()
        raw=worker_program(program,self.nonce,self.hard_seconds-(time.monotonic()-self.started))
        program_path=self.directory/'program.private.py'
        program_pin=publication.exclusive_bytes(program_path,raw)
        argv=[publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-',self.nonce]
        save(self.directory/'dispatch.private.json',dict(operationId=self.operation_id,argv=argv,programPin=program_pin,
            gatePin=self.gate_pin,remainingHardSeconds=self.hard_seconds-(time.monotonic()-self.started)))
        pending=b'';self.dispatched=True;exit_seen=False
        # Regular files avoid blocking stdin writes, reader threads, or pipe backpressure.
        with program_path.open('rb') as source,self.stdout_path.open('xb') as out,self.stderr_path.open('xb') as err:
            self.remaining()
            self.process=Popen(argv,stdin=source,stdout=out,stderr=err)
            with self.stderr_path.open('rb') as incoming:
                try:
                    while True:
                        self.remaining()
                        chunk=incoming.read(65537)
                        if chunk:
                            pending+=chunk
                            while b'\n' in pending:
                                line,pending=pending.split(b'\n',1)
                                self.remaining()
                                need(len(line)<65536,'PROTOCOL_INVALID');self.progress(line+b'\n')
                            need(len(pending)<=65536,'PROTOCOL_INVALID')
                            continue
                        code=self.process.poll()
                        if code is not None:
                            if not exit_seen:exit_seen=True;continue
                            self.exit_code=code
                            need(not pending,'PROTOCOL_INVALID')
                            need(code==0,'EXIT_FAILED');need(self.done,'RESULT_INCOMPLETE')
                            break
                        time.sleep(min(.02,self.remaining()))
                finally:
                    if self.process.poll() is None:
                        # Only the local Docker CLI is stopped. Remote exit remains unproved.
                        self.process.kill();self.process.wait(timeout=5)
        self.remaining()
        value=self.stdout_path.read_bytes()
        try:json.loads(value)
        except (ValueError,UnicodeError):raise ValueError('MAIN_RESOURCE_OBSERVATION_RESULT_INVALID') from None
        # A Docker client exit alone is never the gate-release proof.
        proof=inspect_worker(publication.CONTAINER,self.worker_identity,self.nonce,timeout=min(30,self.remaining()))
        self.remaining()
        save(self.directory/'worker-exit.private.json',proof)
        need(proof.get('status')=='EXITED','WORKER_EXIT_UNPROVEN')
        self.remote_exit=True
        return value

    def __exit__(self,kind,error,traceback):
        successful=kind is None and self.dispatched and self.remote_exit and self.exit_code==0 and self.done
        diagnostics=None
        if self.warning_records:
            diagnostics=save(self.directory/'warning-diagnostics.private.json',dict(schemaVersion='SpugObservationWarnings/v1',
                operationId=self.operation_id,count=len(self.warning_records),categories=self.warning_categories,
                records=self.warning_records))
        terminal=dict(schemaVersion='SpugObservationTerminal/v1',operationId=self.operation_id,
            status='SUCCEEDED' if successful else 'FAILED',actualExitCode=self.exit_code,
            remoteExitVerified=self.remote_exit,dispatched=self.dispatched,workerIdentity=self.worker_identity,
            warningDiagnostics=dict(count=len(self.warning_records),categories=self.warning_categories,diagnosticsPin=diagnostics),
            lastProgress=self.last_progress,elapsedSeconds=time.monotonic()-self.started,
            errorCode=None if error is None else str(error) if type(error) is ValueError and
                re.fullmatch('[A-Z0-9_]+',str(error)) else 'LOCAL_OR_CHANNEL_FAILURE',
            stdoutPin=publication.file_pin(self.stdout_path) if self.stdout_path.exists() else None,
            stderrPin=publication.file_pin(self.stderr_path) if self.stderr_path.exists() else None)
        save(self.directory/'terminal.private.json',terminal)
        if not self.dispatched or self.remote_exit:
            with gate_guard(self.private):
                need(publication.file_pin(self.gate)==self.gate_pin,'GATE_CHANGED')
                self.gate.unlink()
        return False


def inspect_worker(container,expected,nonce,*,timeout=30):
    need(container==publication.CONTAINER,'QUERY_CONTAINER_INVALID')
    program="""import json,os
from pathlib import Path
p=Path('/proc')/str(EXPECTED['pid'])
try:
 ticks=(p/'stat').read_text().rsplit(') ',1)[1].split()[19]
 argv=(p/'cmdline').read_bytes().decode().rstrip('\\0').split('\\0')
 identity=dict(pid=EXPECTED['pid'],startTicks=ticks,argv=argv)
 status='ALIVE' if identity==EXPECTED and argv[-1]==NONCE else 'IDENTITY_CHANGED'
except FileNotFoundError:identity=None;status='EXITED'
print(json.dumps(dict(status=status,identity=identity)))
"""
    raw=('EXPECTED='+repr(expected)+'\nNONCE='+repr(nonce)+'\n'+program).encode()
    result=subprocess.run([publication.DOCKER,'exec','-i',container,'python3','-B','-'],input=raw,capture_output=True,timeout=timeout)
    need(result.returncode==0 and not result.stderr,'QUERY_FAILED')
    return json.loads(result.stdout)


def query_observation(private,operation_id,*,release_exited=False):
    need(type(operation_id) is str and re.fullmatch('[0-9a-f]{32}',operation_id),'OPERATION_ID_INVALID')
    root=Path(private).resolve(strict=True);directory=root/('resource-observation-'+operation_id)
    request=read(directory/'request.private.json');terminal_path=directory/'terminal.private.json'
    need(request['operationId']==operation_id and request['containerId']==publication.CONTAINER and
         request['nonce']=='spug-observation-'+operation_id,'QUERY_IDENTITY_INVALID')
    gate=root/('resource-observation-'+publication.CONTAINER+'.gate.private.json')
    gate_pin=publication.file_pin(gate) if gate.exists() else None
    if gate_pin:need(read(gate)['operationId']==operation_id,'GATE_OWNERSHIP_CHANGED')
    worker=directory/'worker.private.json'
    terminal=read(terminal_path) if terminal_path.exists() else None
    expected=read(worker) if worker.exists() else terminal.get('workerIdentity') if terminal else None
    if terminal is not None:need(expected==terminal['workerIdentity'],'QUERY_WORKER_CHANGED')
    if expected is None:result=dict(status='UNKNOWN_PID',identity=None)
    else:result=inspect_worker(publication.CONTAINER,expected,request['nonce'])
    need(result.get('status') in ('UNKNOWN_PID','ALIVE','IDENTITY_CHANGED','UNKNOWN','EXITED'),'QUERY_RESULT_INVALID')
    report=dict(schemaVersion='SpugObservationQuery/v1',operationId=operation_id,workerIdentity=expected,
        status='EXITED_OUTCOME_UNAVAILABLE' if result['status']=='EXITED' else result['status'],
        actualQuery=result,gateReleased=False,observationSucceeded=False)
    if release_exited and result['status']=='EXITED' and gate_pin:
        with gate_guard(root):
            need(publication.file_pin(gate)==gate_pin,'GATE_CHANGED')
            save(directory/('release-'+uuid.uuid4().hex+'.private.json'),report)
            gate.unlink();report['gateReleased']=True
    save(directory/('query-'+uuid.uuid4().hex+'.private.json'),report)
    return report
