"""Finite task control client and independently verifiable fresh identity pairs."""
import base64
import binascii
import datetime as dt
import os
from pathlib import Path
import socket
import stat
import struct
import uuid

from core import (canonical, fields, need, integer, text, timestamp, now, parse, pins,
                  pin_key, same, read_pin, json_pin, write_atomic, absolute, VerificationError)
from lab_boundary import REHEARSAL, ROOT
from service_identity import native_service_identity, IDENTITY_FIELDS
from evidence import NATIVE_PROCESS_FIELDS
from peer_installation import ADMISSION_VERSION, ADMISSION_FIELDS, select_admission, verify_admission

FRAME_LIMIT = 1048576
LAUNCH_FIELDS = ('schemaVersion rehearsalId operationRequestPin installationPin authorityKeyPin authorizationPin '
    'leasePin producerEntryPin signerEntryPin observationSocketPath evidenceRoot allowedCallerPin issuedAt expiresAt')
REQUEST_FIELDS = 'schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin issuedAt deadlineMilliseconds'
RESULT_FIELDS = ('schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin '
    'identityProofPin originalPins probeStartedAt probeFinishedAt issuedAt expiresAt')
CALLER_FIELDS = ('schemaVersion rehearsalId pid startTicks uid gid hostId bootId pidNamespace mountNamespace '
    'networkNamespace userNamespace rootDevice rootInode nativeRuntimeProofPin issuedAt expiresAt')
INVOCATION_FIELDS = ('schemaVersion operationId restoreId targetIdentityPin recoveryPoint stage state actualExitCode '
    'startedAt finishedAt sourcePins resultPin commandId command argv cwd processProfile processResultPin')


def authenticate(boundary, envelope):
    """Authenticate a frame before any frame-supplied Pin becomes admissible."""
    from cryptography.exceptions import InvalidSignature
    fields(envelope, 'schemaVersion keySha256 payload signature', 'RepositorySignedRecord/v1')
    key = boundary.admission['authorityKeyPin']
    need(envelope['keySha256'] == key['sha256'], 'NATIVE_OBSERVE_AUTHORITY')
    try:
        boundary.public_key(key).verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
    except (InvalidSignature, ValueError, TypeError, binascii.Error) as error:
        raise VerificationError('NATIVE_OBSERVE_SIGNATURE') from error
    return envelope['payload']


def private_path(value, *, evidence_root=None):
    from pathlib import PurePosixPath
    path=PurePosixPath(text(value))
    need(path.is_absolute() and str(path)==value and '..' not in path.parts and PurePosixPath(ROOT) in path.parents,
         'NATIVE_OBSERVE_PRIVATE_PATH')
    if evidence_root is not None:
        need(PurePosixPath(evidence_root) in path.parents, 'NATIVE_OBSERVE_ORIGINAL_ROOT')


def current_launch(boundary, launch_pin, maximum_age_ms):
    boundary.recheck()
    launch=boundary.signed(launch_pin,boundary.admission['authorityKeyPin'])
    fields(launch,LAUNCH_FIELDS,'RepositoryLabNativeLaunch/v1')
    need(launch['rehearsalId']==REHEARSAL,'NATIVE_OBSERVE_LAUNCH_SCOPE')
    for name,context_name in [('operationRequestPin','operationRequestPin'),
        ('authorityKeyPin','authorityKeyPin'),('authorizationPin','authorizationPin'),('leasePin','leasePin')]:
        same(launch[name],boundary.context[context_name],'NATIVE_OBSERVE_LAUNCH_BINDING')
    for name in ('producerEntryPin','signerEntryPin','allowedCallerPin'):
        boundary.original(launch[name],False)
    from evidence import native_runtime_metadata
    runtime,_=native_runtime_metadata(boundary,
        boundary.signed(launch['installationPin'],boundary.admission['authorityKeyPin'])['nativeRuntimeProofPin'],
        'EXECUTOR',maximum_age_ms)
    installation=boundary.signed(launch['installationPin'],boundary.admission['authorityKeyPin'])
    need(installation.get('schemaVersion')=='RepositoryNativeInstallation/v2','NATIVE_OBSERVE_INSTALLATION_V2')
    need({pin_key(launch[name]) for name in ('producerEntryPin','signerEntryPin')}<=set(pins(installation['filePins'])),
         'NATIVE_OBSERVE_ENTRY_NOT_INSTALLED')
    caller=boundary.signed(launch['allowedCallerPin'],boundary.admission['authorityKeyPin'])
    fields(caller,CALLER_FIELDS,'RepositoryLabNativeCaller/v1')
    need(caller['rehearsalId']==REHEARSAL,'NATIVE_OBSERVE_CALLER_SCOPE')
    for name in ('pid','startTicks','rootInode'):integer(caller[name],1)
    for name in ('uid','gid','rootDevice'):integer(caller[name])
    verifier=boundary.signed(boundary.context['installedClosurePin'],boundary.admission['authorityKeyPin'])
    same(caller['nativeRuntimeProofPin'],verifier['nativeRuntimeProofPin'],'NATIVE_OBSERVE_CALLER_RUNTIME')
    for name in ('observationSocketPath','evidenceRoot'):
        private_path(launch[name])
    current=timestamp(now())
    need(timestamp(launch['issuedAt'])<=current<timestamp(launch['expiresAt'])<=timestamp(boundary.context['expiresAt']),
         'NATIVE_OBSERVE_LAUNCH_EXPIRED','STALE')
    need(timestamp(caller['issuedAt'])<=current<timestamp(caller['expiresAt']), 'NATIVE_OBSERVE_CALLER_EXPIRED','STALE')
    boundary.window(caller['expiresAt'])
    boundary.window(launch['expiresAt'])
    return launch


def live_caller(boundary,launch,maximum_age_ms):
    """Recheck the actual verifier runtime; W05 checks the selected peer original."""
    from evidence import native_runtime_proof
    need(os.name=='posix','NATIVE_OBSERVE_LINUX_REQUIRED')
    boundary.original(launch['allowedCallerPin'],False)
    caller=boundary.signed(launch['allowedCallerPin'],boundary.admission['authorityKeyPin'])
    host=boundary.original(boundary.admission['executionHostPin'])
    need(host['uid']==os.getuid() and host['gid']==os.getgid(),'NATIVE_OBSERVE_CALLER_CHANGED','STALE')
    proof,_=native_runtime_proof(boundary,caller['nativeRuntimeProofPin'],'VERIFIER',maximum_age_ms,selected_installation=True)
    stat_text=Path('/proc/self/stat').read_text(encoding='ascii')
    root_stat=Path('/proc/self/root').stat()
    need(caller['pid']==os.getpid() and caller['startTicks']==int(stat_text[stat_text.rfind(')')+2:].split()[19]) and
         caller['uid']==os.getuid() and caller['gid']==os.getgid() and caller['rootDevice']==root_stat.st_dev and
         caller['rootInode']==root_stat.st_ino,'NATIVE_OBSERVE_CALLER_CHANGED','STALE')
    need(caller['hostId']==proof['hostId'] and caller['bootId']==proof['bootId'],'NATIVE_OBSERVE_CALLER_HOST')
    for key,name in [('pidNamespace','pid'),('mountNamespace','mnt'),('networkNamespace','net'),('userNamespace','user')]:
        need(caller[key]==proof[key]==os.readlink('/proc/self/ns/'+name),'NATIVE_OBSERVE_CALLER_NAMESPACE','STALE')


def protected_socket(path):
    """Socket and every ancestor must retain the selected root/private custody."""
    target=absolute(path)
    for item in (target,*target.parents):
        info=item.lstat()
        need(not stat.S_ISLNK(info.st_mode) and info.st_uid==0 and not info.st_mode & 0o022,
             'NATIVE_OBSERVE_SOCKET_CUSTODY')
        if item==target:
            need(stat.S_ISSOCK(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600,'NATIVE_OBSERVE_SOCKET_MODE')
        else:need(stat.S_ISDIR(info.st_mode),'NATIVE_OBSERVE_SOCKET_ANCESTOR')
    return target.stat()


def exchange(path,request,deadline):
    need(os.name=='posix' and hasattr(socket,'SO_PEERCRED'),'NATIVE_OBSERVE_LINUX_REQUIRED')
    raw=canonical(request)
    need(0<len(raw)<=FRAME_LIMIT,'NATIVE_OBSERVE_FRAME_LIMIT')
    before=protected_socket(path)
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as channel:
            channel.settimeout(deadline.remaining());channel.connect(path)
            peer=struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            need(peer[0]>0 and peer[1]==0,'NATIVE_OBSERVE_SERVICE_PEER')
            channel.sendall(struct.pack('!I',len(raw))+raw)
            def receive(count):
                value=bytearray()
                while len(value)<count:
                    channel.settimeout(deadline.remaining())
                    part=channel.recv(count-len(value))
                    need(bool(part),'NATIVE_OBSERVE_FRAME_INCOMPLETE','UNKNOWN')
                    value.extend(part)
                return bytes(value)
            size=struct.unpack('!I',receive(4))[0]
            need(0<size<=FRAME_LIMIT,'NATIVE_OBSERVE_FRAME_LIMIT')
            response=receive(size)
            channel.settimeout(deadline.remaining())
            need(channel.recv(1)==b'','NATIVE_OBSERVE_EXTRA_FRAME')
            after=protected_socket(path)
            need((before.st_dev,before.st_ino,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_ctime_ns),
                 'NATIVE_OBSERVE_SOCKET_CHANGED','STALE')
    except (OSError,TimeoutError) as error:
        raise VerificationError('NATIVE_OBSERVE_TRANSPORT_UNAVAILABLE','UNKNOWN') from error
    envelope=parse(response)
    need(canonical(envelope)==response,'NATIVE_OBSERVE_NONCANONICAL_FRAME')
    return envelope


class ObservationBoundary:
    """Transactional read view; no mutation of caller admission on failed validation."""
    def __init__(self,parent,originals):
        self.parent=parent;self.selected=parent.selected | set(pins(originals,nonempty=False))
        self.admission=parent.admission;self.context=parent.context;self.operation_id=parent.operation_id
        self.deadline=parent.deadline
    def recheck(self):self.parent.recheck()
    @property
    def grant(self):return self.parent.grant
    @property
    def lease(self):return self.parent.lease
    def window(self,value):self.parent.window(value)
    def public_key(self,pin):return self.parent.public_key(pin)
    def read(self,pin,content=False):
        need(pin_key(pin) in self.selected,'NATIVE_OBSERVE_ORIGINAL_NOT_SELECTED')
        return read_pin(pin,self.deadline,content=content)
    def original(self,pin,as_json=True):
        raw=self.read(pin,content=True)
        return parse(raw) if as_json else raw
    def signed(self,pin,key_pin):
        same(key_pin,self.admission['authorityKeyPin'],'NATIVE_OBSERVE_AUTHORITY')
        return authenticate(self,self.original(pin))


def references(value):
    if type(value) is dict:
        if set(value)=={'path','bytes','sha256'}:
            pin_key(value);return [value]
        return [pin for child in value.values() for pin in references(child)]
    if type(value) is list:return [pin for child in value for pin in references(child)]
    return []


def admit_response(boundary,launch,request,envelope,expected,source_pins,maximum_age_ms,*,launch_pin):
    result=authenticate(boundary,envelope)
    fields(result,RESULT_FIELDS,'RepositoryLabNativeObserveResult/v1')
    for name in ('rehearsalId','collectionId','sequence','phase','operationRequestPin','serviceBindingPin'):
        need(result[name]==request[name],'NATIVE_OBSERVE_RESPONSE_BINDING')
    need(result['phase'] in ('BEFORE','AFTER') and result['rehearsalId']==REHEARSAL,'NATIVE_OBSERVE_PHASE')
    need(integer(result['sequence'],1)<=64,'NATIVE_OBSERVE_SEQUENCE');text(result['collectionId'])
    started,finished,issued,expires=map(timestamp,[result[k] for k in ('probeStartedAt','probeFinishedAt','issuedAt','expiresAt')])
    current=timestamp(now())
    need(timestamp(request['issuedAt'])<=started<finished<=issued<=current<expires and
         (current-started).total_seconds()*1000<=integer(maximum_age_ms,1) and
         timestamp(launch['issuedAt'])<=started and expires<=timestamp(launch['expiresAt']),
         'NATIVE_OBSERVE_NATIVE_TIME','STALE')
    declared=set(pins(result['originalPins']))
    declared_by_path={pin_key(pin)[0]:pin for pin in result['originalPins']}
    need(len(declared_by_path)==len(declared),'NATIVE_OBSERVE_DUPLICATE_PATH')
    need(not set(declared_by_path) & {key[0] for key in boundary.selected},'NATIVE_OBSERVE_REUSED_ORIGINAL_PATH')
    need(len(boundary.selected | declared)<=4096,'NATIVE_OBSERVE_GRAPH_LIMIT')
    for pin in result['originalPins']:private_path(pin['path'],evidence_root=launch['evidenceRoot'])
    view=ObservationBoundary(boundary,result['originalPins'])
    installation=boundary.signed(launch['installationPin'],boundary.admission['authorityKeyPin'])
    admission_pin,admission=select_admission(view,result['originalPins'])
    pending=[(result['identityProofPin'],'RecoveryNativeServiceIdentity/v1'),(admission_pin,ADMISSION_VERSION)]
    visited=set();new=set()
    while pending:
        pin,kind=pending.pop();key=pin_key(pin)
        if key in visited:continue
        visited.add(key)
        need(len(boundary.selected | visited)<=4096,'NATIVE_OBSERVE_GRAPH_LIMIT')
        if key in boundary.selected:continue
        need(key in declared,'NATIVE_OBSERVE_CLOSURE_MISSING')
        private_path(pin['path'],evidence_root=launch['evidenceRoot'])
        new.add(key)
        if kind=='raw':
            view.read(pin,content=False);continue
        record=view.original(pin)
        version=record.get('schemaVersion') if type(record) is dict else None
        if version=='RepositorySignedRecord/v1':
            record=authenticate(view,record);version=record.get('schemaVersion')
            need(version==kind,'NATIVE_OBSERVE_DYNAMIC_SCHEMA')
            if version=='RecoveryNativeServiceIdentity/v1':fields(record,IDENTITY_FIELDS,version)
            elif version=='RecoveryNativeProcessResult/v1':
                fields(record,NATIVE_PROCESS_FIELDS,version)
            elif version==ADMISSION_VERSION:fields(record,ADMISSION_FIELDS,version)
            else:need(False,'NATIVE_OBSERVE_DYNAMIC_SCHEMA')
        elif version==kind=='RecoveryInvocation/v1':fields(record,INVOCATION_FIELDS,version)
        elif kind in ('parent-original','unsigned-process'):
            if kind=='unsigned-process':fields(record,NATIVE_PROCESS_FIELDS,'RecoveryNativeProcessResult/v1')
            else:fields(record,'terminal supervisorExitCode failureCode stdoutPin stderrPin')
            continue
        else:need(False,'NATIVE_OBSERVE_DYNAMIC_SCHEMA')
        typed={}
        if kind=='RecoveryNativeServiceIdentity/v1':
            for name in ('infoResultPin','inspectResultPin','networkResultPin'):typed[pin_key(record[name])]='raw'
            for value in record['invocationPins']:typed[pin_key(value)]='RecoveryInvocation/v1'
        elif kind==ADMISSION_VERSION:
            typed[pin_key(record['invocationPin'])]='RecoveryInvocation/v1'
            typed[pin_key(record['manifestResultPin'])]='raw'
        elif kind=='RecoveryInvocation/v1':
            typed[pin_key(record['processResultPin'])]='RecoveryNativeProcessResult/v1'
            typed[pin_key(record['resultPin'])]='raw'
            for name,aux_kind in [('supervisor-terminal.json','parent-original'),('process-original.json','unsigned-process')]:
                exact_path=os.path.normcase(str(Path(pin['path']).parent/name))
                need(exact_path in declared_by_path,'NATIVE_OBSERVE_PARENT_ORIGINAL_MISSING')
                pending.append((declared_by_path[exact_path],aux_kind))
        elif kind=='RecoveryNativeProcessResult/v1':
            for name in ('stdoutPin','stderrPin','resultPin'):typed[pin_key(record[name])]='raw'
        for value in references(record):
            value_key=pin_key(value)
            need(value_key in typed or value_key in boundary.selected,'NATIVE_OBSERVE_UPSTREAM_NOT_SELECTED')
            pending.append((value,typed.get(value_key,'stable')))
    need(declared==new,'NATIVE_OBSERVE_CLOSURE_EXTRA_OR_STATIC')
    proof=view.signed(result['identityProofPin'],boundary.admission['authorityKeyPin'])
    same(proof['probeRuntimeProofPin'],installation['nativeRuntimeProofPin'],'NATIVE_OBSERVE_PRODUCER_RUNTIME')
    need(pin_key(proof['probeSourcePin']) in set(pins(installation['filePins'])),'NATIVE_OBSERVE_PROBE_NOT_INSTALLED')
    calls=[view.original(pin) for pin in proof['invocationPins']]
    installed_sources=set(pins(installation['filePins'])) | set(pins(installation['dependencyPins'],False)) | {pin_key(installation['pythonPin'])}
    for call_pin in [*proof['invocationPins'],admission['invocationPin']]:
        call=view.original(call_pin)
        need(set(pins(call['sourcePins']))<=installed_sources,'NATIVE_PEER_SOURCE_INSTALLATION')
        process=view.signed(call['processResultPin'],boundary.admission['authorityKeyPin'])
        def auxiliary(name):
            return view.original(declared_by_path[os.path.normcase(str(Path(call_pin['path']).parent/name))])
        need(auxiliary('process-original.json')==process,'NATIVE_OBSERVE_UNSIGNED_PROCESS_CHANGED')
        parent=auxiliary('supervisor-terminal.json');terminal=parent['terminal']
        need(type(terminal) is dict and parent['supervisorExitCode']==0 and parent['failureCode'] is None and
             parent['stdoutPin']==process['stdoutPin'] and parent['stderrPin']==process['stderrPin'] and
             terminal.get('model')=='linux-owned-child-subreaper-v1' and terminal.get('supervisorPid')==process['supervisorPid'] and
             terminal.get('workerPid')==process['childPid'],'NATIVE_OBSERVE_PARENT_BINDING')
    parent_path=os.path.normcase(str(Path(admission['invocationPin']['path']).parent/'supervisor-terminal.json'))
    verify_admission(view,admission,launch,launch_pin,request,result,expected,source_pins,maximum_age_ms,
                     view.original(declared_by_path[parent_path]))
    need(min(timestamp(call['startedAt']) for call in calls)==started and
         max(timestamp(call['finishedAt']) for call in calls)==finished,'NATIVE_OBSERVE_ACTUAL_INTERVAL')
    observed=native_service_identity(result['serviceBindingPin'],view,expected,source_pins,maximum_age_ms,
                                     identity_proof_pin=result['identityProofPin'])
    need(timestamp(observed['observedAt'])==finished,'NATIVE_OBSERVE_HISTORICAL_TIME')
    boundary.recheck()
    return result,observed


class NativeObservationClient:
    def __init__(self,boundary,launch_pin,expected,source_pins,maximum_age_ms):
        self.boundary=boundary;self.launch_pin=launch_pin;self.expected=expected
        self.sources=source_pins;self.age=maximum_age_ms;self.sequence=0;self.pairs={};self.dynamic=set()
        current_launch(boundary,launch_pin,maximum_age_ms)
    def observe(self,binding_pin,*,collection_id,sequence,phase):
        need(type(sequence) is int and sequence==self.sequence+1 and sequence<=64,'NATIVE_OBSERVE_SEQUENCE')
        need(phase in ('BEFORE','AFTER') and type(collection_id) is str and collection_id,'NATIVE_OBSERVE_PHASE')
        previous=self.pairs.get(collection_id)
        need((phase=='BEFORE' and previous is None) or (phase=='AFTER' and previous=='BEFORE'),'NATIVE_OBSERVE_REPLAY')
        launch=current_launch(self.boundary,self.launch_pin,self.age)
        self.boundary.original(binding_pin)
        live_caller(self.boundary,launch,self.age)
        operation=self.boundary.original(launch['operationRequestPin'])
        request=dict(schemaVersion='RepositoryLabNativeObserveRequest/v1',rehearsalId=REHEARSAL,
            collectionId=collection_id,sequence=sequence,phase=phase,operationRequestPin=launch['operationRequestPin'],
            serviceBindingPin=binding_pin,issuedAt=now(),deadlineMilliseconds=min(integer(operation['deadlineMilliseconds'],1),
                max(1,int(self.boundary.deadline.remaining()*1000))))
        envelope=exchange(launch['observationSocketPath'],request,self.boundary.deadline)
        result,observed=admit_response(self.boundary,launch,request,envelope,self.expected,self.sources,self.age,launch_pin=self.launch_pin)
        keys=set(pins(result['originalPins']))
        need(not keys & self.dynamic,'NATIVE_OBSERVE_REUSED_ORIGINAL')
        path=Path(launch['evidenceRoot'])/('observe-response-'+uuid.uuid4().hex+'.json')
        response_pin=write_atomic(path,envelope)
        need(len(self.boundary.selected | keys | {pin_key(response_pin)})<=4096,'NATIVE_OBSERVE_GRAPH_LIMIT')
        self.boundary.selected.update(keys);self.boundary.selected.add(pin_key(response_pin))
        self.dynamic.update(keys);self.sequence=sequence;self.pairs[collection_id]=phase
        return dict(launchPin=self.launch_pin,responsePin=response_pin,request=request,observation=observed)


def identity_values(observation):
    return {k:v for k,v in observation.items() if k!='observedAt'}


def collection_evidence(before,after,started_at,finished_at):
    b=before['request'];a=after['request']
    need(b['collectionId']==a['collectionId'] and b['phase']=='BEFORE' and a['phase']=='AFTER' and
         a['sequence']==b['sequence']+1,'NATIVE_OBSERVE_PAIR_ORDER')
    need(pin_key(before['responsePin'])!=pin_key(after['responsePin']),'NATIVE_OBSERVE_PAIR_DISTINCT')
    same(before['launchPin'],after['launchPin'],'NATIVE_OBSERVE_PAIR_LAUNCH')
    need(b['operationRequestPin']==a['operationRequestPin'] and b['serviceBindingPin']==a['serviceBindingPin'],
         'NATIVE_OBSERVE_PAIR_BINDING')
    need(identity_values(before['observation'])==identity_values(after['observation']),'SERVICE_NATIVE_COLLECTION_CHANGED','STALE')
    return dict(schemaVersion='RepositoryLabNativeCollection/v1',collectionId=b['collectionId'],
        bindingPin=b['serviceBindingPin'],startedAt=started_at,finishedAt=finished_at,before=before,after=after,
        observedAt=after['observation']['observedAt'])


def collect_service(binding_pin,deadline,collector):
    """The controlled BEFORE finishes before work; controlled AFTER starts afterward."""
    from service_identity import probe_service
    if json_pin(binding_pin,deadline).get('schemaVersion')!='RecoveryServiceBinding/v2':
        before=probe_service(binding_pin,deadline);value=collector(before);after=probe_service(binding_pin,deadline)
        need(identity_values(before)==identity_values(after),'SERVICE_COLLECTION_CHANGED','STALE')
        return value,after
    selected=getattr(deadline,'native_service_context',None)
    need(type(selected) is dict and isinstance(selected.get('client'),NativeObservationClient),'SERVICE_NATIVE_FRESH_CLIENT_REQUIRED')
    client=selected['client'];collection_id=uuid.uuid4().hex
    before=probe_service(binding_pin,deadline,collection_id=collection_id,sequence=client.sequence+1,phase='BEFORE')
    started=now();value=collector(before['observation']);finished=now()
    after=probe_service(binding_pin,deadline,collection_id=collection_id,sequence=client.sequence+1,phase='AFTER')
    record=collection_evidence(before,after,started,finished)
    validate_pair_times(record,client.boundary)
    return value,record


def validate_pair_times(record,boundary):
    b=boundary.original(record['before']['responsePin'])['payload']
    a=boundary.original(record['after']['responsePin'])['payload']
    _,after_admission=select_admission(boundary,a['originalPins'])
    need(timestamp(b['probeFinishedAt'])<=timestamp(record['startedAt'])<=timestamp(record['finishedAt'])<=timestamp(after_admission['startedAt']),
         'NATIVE_OBSERVE_COLLECTION_INTERVAL')
    need(pin_key(b['identityProofPin'])!=pin_key(a['identityProofPin']) and
         not set(pins(b['originalPins'])) & set(pins(a['originalPins'])),'NATIVE_OBSERVE_PAIR_REUSED')


def verify_collection_evidence(context,record,binding_pin):
    fields(record,'schemaVersion collectionId bindingPin startedAt finishedAt before after observedAt','RepositoryLabNativeCollection/v1')
    same(record['bindingPin'],binding_pin,'NATIVE_OBSERVE_COLLECTION_BINDING')
    boundary=context.lab
    need(boundary is not None,'NATIVE_PROFILE_LAB_ONLY')
    expected=dict(operationId=context.request['operationId'],restoreId=context.plan['restoreId'],recoveryPoint=context.plan['recoveryPoint'],
        targetIdentityPin=context.target_pin,sourceScopePin=context.source_pin,environmentConfigPin=context.request['sourceOrTargetRef'],
        applicationStartPin=context.request['inputPins']['applicationStartResult'])
    # Dynamic originals are already independently selected by the final caller. Validate the
    # exact response closure against the caller's stable subset, without online dispatch.
    all_dynamic=set()
    for phase in ('before','after'):
        item=record[phase];fields(item,'launchPin responsePin request observation')
        envelope=context.record(item['responsePin']);payload=authenticate(boundary,envelope)
        all_dynamic.update(pins(payload['originalPins']))
    stable=ObservationBoundary(boundary,[]);stable.selected=boundary.selected-all_dynamic
    stable.parent=boundary
    for phase in ('before','after'):
        item=record[phase]
        fields(item['request'],REQUEST_FIELDS,'RepositoryLabNativeObserveRequest/v1')
        need(item['request']['collectionId']==record['collectionId'],'NATIVE_OBSERVE_COLLECTION_ID')
        same(item['request']['serviceBindingPin'],binding_pin,'NATIVE_OBSERVE_COLLECTION_BINDING')
        context.read(item['launchPin'])
        launch=current_launch(boundary,item['launchPin'],context.record(context.request['policyPin'])['maxAgeMilliseconds'])
        same(item['request']['operationRequestPin'],launch['operationRequestPin'],'NATIVE_OBSERVE_CURRENT_REQUEST')
        result,observed=admit_response(stable,launch,item['request'],context.record(item['responsePin']),expected,
            context.source_pins,context.record(context.request['policyPin'])['maxAgeMilliseconds'],launch_pin=item['launchPin'])
        need(observed==item['observation'],'NATIVE_OBSERVE_OBSERVATION_CHANGED')
        for pin in result['originalPins']:context.read(pin)
    rebuilt=collection_evidence(record['before'],record['after'],record['startedAt'],record['finishedAt'])
    need(rebuilt==record,'NATIVE_OBSERVE_COLLECTION_CHANGED')
    validate_pair_times(record,boundary)
    return record['after']['observation']


def verify_collection_sequence(context,records):
    selected=[record for record in records if record.get('schemaVersion')=='RepositoryLabNativeCollection/v1']
    seen=set();ordered=[]
    for record in selected:
        for phase in ('before','after'):
            response=record[phase]['responsePin'];payload=authenticate(context.lab,context.record(response))
            need(pin_key(response) not in seen,'NATIVE_OBSERVE_COLLECTION_REPLAY')
            seen.add(pin_key(response));ordered.append(payload)
    need(len({value['sequence'] for value in ordered})==len(ordered) and
         len({record['collectionId'] for record in selected})==len(selected),'NATIVE_OBSERVE_COLLECTION_REPLAY')
    by_sequence=sorted(ordered,key=lambda value:value['sequence'])
    need([value['sequence'] for value in by_sequence]==list(range(1,len(by_sequence)+1)),
         'NATIVE_OBSERVE_SEQUENCE_GAP')
    for previous,current in zip(by_sequence,by_sequence[1:]):
        _,admission=select_admission(context.lab,current['originalPins'])
        need(timestamp(previous['probeFinishedAt'])<=timestamp(admission['startedAt']),
             'NATIVE_OBSERVE_SEQUENCE_TIME')
