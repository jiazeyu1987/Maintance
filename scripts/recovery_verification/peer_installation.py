"""Consume A-authenticated EXECUTOR installation work; never self-admit that runtime."""
from pathlib import PurePosixPath

from core import canonical, fields, need, integer, timestamp, now, pin_key, pins, same, parse
from evidence import native_process_result, native_runtime_metadata

ADMISSION_VERSION = 'RepositoryLabNativeInstallationAdmission/v1'
ADMISSION_FIELDS = ('schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin '
    'launchPin installationPin nativeRuntimeTrustPin nativeRuntimeProofPin producerIdentityPin invocationPin '
    'manifestResultPin startedAt finishedAt issuedAt expiresAt')
INSTALLATION_FIELDS = 'schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins nativeRuntimeTrustPin nativeRuntimeProofPin'
NAMESPACES = {'pidNamespace':'pid', 'mountNamespace':'mnt', 'networkNamespace':'net', 'userNamespace':'user'}


def select_admission(view, originals):
    """Only scan the bounded Pins authenticated by the outer response."""
    found=[]
    for pin in originals:
        raw=view.read(pin,content=True)
        if not raw.lstrip().startswith(b'{'):continue
        record=parse(raw)
        if (type(record) is dict and record.get('schemaVersion')=='RepositorySignedRecord/v1' and
                type(record.get('payload')) is dict and record['payload'].get('schemaVersion')==ADMISSION_VERSION):
            payload=view.signed(pin,view.admission['authorityKeyPin'])
            fields(payload,ADMISSION_FIELDS,ADMISSION_VERSION)
            found.append((pin,payload))
    need(len(found)==1,'NATIVE_PEER_ADMISSION_UNIQUE_REQUIRED')
    return found[0]


def installed_source(installation, name):
    selected=[pin for pin in installation['filePins'] if PurePosixPath(pin['path']).name==name]
    need(len(selected)==1,'NATIVE_PEER_INSTALLED_SOURCE_REQUIRED')
    return selected[0]


def verify_parent(process, raw, producer=None):
    fields(raw,'terminal supervisorExitCode failureCode stdoutPin stderrPin')
    terminal=raw['terminal']
    need(type(terminal) is dict and type(raw['supervisorExitCode']) is int and raw['supervisorExitCode']==0 and
         raw['failureCode'] is None and raw['stdoutPin']==process['stdoutPin'] and raw['stderrPin']==process['stderrPin'],
         'NATIVE_PEER_PARENT_TERMINAL')
    need(terminal.get('model')=='linux-owned-child-subreaper-v1' and terminal.get('kind')=='TERMINAL' and
         terminal.get('supervisorPid')==process['supervisorPid'] and terminal.get('workerPid')==process['childPid'] and
         terminal.get('unknown') is False and terminal.get('workerDispatched') is True and
         terminal.get('treeTerminated') is True and terminal.get('failureCode') is None and
         type(terminal.get('actualExitCode')) is int and terminal['actualExitCode']==0,'NATIVE_PEER_PARENT_TERMINAL')
    parent=terminal.get('supervisorIdentity')
    need(type(parent) is dict and parent.get('pid')==process['supervisorPid'] and
         parent.get('startTicks')==process['supervisorStartTicks'] and parent.get('bootId')==process['bootId'] and
         parent.get('namespaces')=={name:process[field] for field,name in NAMESPACES.items()},'NATIVE_PEER_PARENT_IDENTITY')
    if producer is not None:
        need(parent.get('parent')==producer['pid'] and parent.get('uid')==producer['uid'] and
             parent.get('gid')==producer['gid'] and process['supervisorStartTicks']>=producer['startTicks'],
             'NATIVE_PEER_PRODUCER_PARENT')
    need(terminal.get('dispatch')==dict(argv=process['argv'],cwd=process['cwd'],uid=process['uid'],gid=process['gid']),
         'NATIVE_PEER_ACTUAL_DISPATCH')
    children=terminal.get('children')
    need(type(children) is list and children and all(type(child) is dict and child.get('reaped') is True
         and type(child.get('actualWaitStatus')) is int for child in children),'NATIVE_PEER_CHILDREN_NOT_REAPED')
    workers=[child for child in children if child.get('pid')==process['childPid']]
    need(len(workers)==1,'NATIVE_PEER_CHILD_IDENTITY')
    worker=workers[0]
    need(worker.get('startTicks')==process['childStartTicks'] and worker.get('uid')==process['uid'] and
         worker.get('gid')==process['gid'] and worker['actualWaitStatus']==process['waitStatus']==0,
         'NATIVE_PEER_CHILD_IDENTITY')


def verify_admission(view, admission, launch, launch_pin, request, response, expected, source_pins, maximum_age_ms, parent):
    from native_observe import CALLER_FIELDS, INVOCATION_FIELDS
    from lab_boundary import REHEARSAL, ROOT
    fields(admission,ADMISSION_FIELDS,ADMISSION_VERSION)
    for name in ('rehearsalId','collectionId','sequence','phase','operationRequestPin','serviceBindingPin'):
        need(admission[name]==request[name],'NATIVE_PEER_PHASE_BINDING')
    need(admission['rehearsalId']==REHEARSAL,'NATIVE_PEER_REHEARSAL')
    same(admission['launchPin'],launch_pin,'NATIVE_PEER_LAUNCH_BINDING')
    same(admission['installationPin'],launch['installationPin'],'NATIVE_PEER_INSTALLATION_BINDING')
    installation=view.signed(launch['installationPin'],view.admission['authorityKeyPin'])
    fields(installation,INSTALLATION_FIELDS,'RepositoryNativeInstallation/v2')
    need(installation['root']==ROOT,'NATIVE_PEER_INSTALLATION_ROOT')
    for name in ('nativeRuntimeProofPin','nativeRuntimeTrustPin'):
        same(admission[name],installation[name],'NATIVE_PEER_RUNTIME_BINDING')
    proof,_=native_runtime_metadata(view,admission['nativeRuntimeProofPin'],'EXECUTOR',maximum_age_ms)
    same(admission['nativeRuntimeTrustPin'],proof['nativeRuntimeTrustPin'],'NATIVE_PEER_RUNTIME_BINDING')
    producer=view.signed(admission['producerIdentityPin'],view.admission['authorityKeyPin'])
    fields(producer,CALLER_FIELDS,'RepositoryLabNativeCaller/v1')
    need(producer['rehearsalId']==REHEARSAL and type(producer['uid']) is int and type(producer['gid']) is int and
         producer['uid']==producer['gid']==0,'NATIVE_PEER_PRODUCER_ROLE')
    for name in ('pid','startTicks','rootInode'):integer(producer[name],1)
    integer(producer['rootDevice'])
    same(producer['nativeRuntimeProofPin'],admission['nativeRuntimeProofPin'],'NATIVE_PEER_PRODUCER_RUNTIME')
    need(all(producer[name]==proof[name] for name in ('hostId','bootId','rootDevice','rootInode',*NAMESPACES)),
         'NATIVE_PEER_PRODUCER_IDENTITY')
    call=view.original(admission['invocationPin'])
    fields(call,INVOCATION_FIELDS,'RecoveryInvocation/v1')
    need(all(call[name]==expected[name] for name in ('operationId','restoreId','recoveryPoint')),
         'NATIVE_PEER_INVOCATION_OPERATION')
    same(call['targetIdentityPin'],expected['targetIdentityPin'],'NATIVE_PEER_INVOCATION_TARGET')
    same(call['resultPin'],admission['manifestResultPin'],'NATIVE_PEER_MANIFEST_BINDING')
    need(call['processProfile']=='linux-owned-child-subreaper-v1','NATIVE_PEER_PROCESS_PROFILE')
    launcher=installed_source(installation,'recovery_native_launcher.py')
    same(launcher,launch['producerEntryPin'],'NATIVE_PEER_LAUNCHER_BINDING')
    argv=[installation['pythonPin']['path'],launcher['path'],'admit-installation','--installation-pin',
          canonical(launch['installationPin']).decode('utf-8'),'--authority-pin',
          canonical(view.admission['authorityKeyPin']).decode('utf-8')]
    need(call['argv']==argv and call['command']==canonical(argv).decode('utf-8'),'NATIVE_PEER_FIXED_ARGV')
    helpers=[installed_source(installation,name) for name in
             ('repository_records.py','repository_native_runtime.py','recovery_environment_supervisor.py')]
    required={pin_key(pin) for pin in [launcher,installation['pythonPin'],*helpers]}
    installed=set(pins(installation['filePins'])) | set(pins(installation['dependencyPins'],False)) | {pin_key(installation['pythonPin'])}
    need(required<=set(pins(call['sourcePins']))<=installed,'NATIVE_PEER_SOURCE_INSTALLATION')
    process=native_process_result(view,call['processResultPin'],call,source_pins,maximum_age_ms,
        role='EXECUTOR',selected_installation=False,runtime_proof_pin=admission['nativeRuntimeProofPin'])
    same(process['pythonPin'],installation['pythonPin'],'NATIVE_PEER_PYTHON_BINDING')
    same(process['supervisorPin'],helpers[2],'NATIVE_PEER_SUPERVISOR_BINDING')
    need(process['uid']==producer['uid'] and process['gid']==producer['gid'],'NATIVE_PEER_PROCESS_OWNER')
    verify_parent(process,parent,producer)
    raw=view.original(admission['manifestResultPin'],False)
    need(raw==canonical(installation) and view.original(process['stdoutPin'],False)==raw and
         view.original(process['stderrPin'],False)==b'','NATIVE_PEER_MANIFEST_RESULT')
    start,finish,issued,expires=(timestamp(admission[name]) for name in ('startedAt','finishedAt','issuedAt','expiresAt'))
    need(admission['startedAt']==call['startedAt'] and admission['finishedAt']==call['finishedAt'],
         'NATIVE_PEER_ACTUAL_TIME')
    need(max(timestamp(view.context['issuedAt']),timestamp(view.grant['notBefore']))<=start and
         timestamp(response['probeFinishedAt'])<=min(timestamp(view.context['expiresAt']),
             timestamp(view.grant['expiresAt']),timestamp(view.lease['expiresAt'])),
         'NATIVE_PEER_AUTHORITY_INTERVAL','STALE')
    if view.lease['schemaVersion']=='RecoveryEnvironmentLease/v1':
        need(timestamp(view.lease['notBefore'])<=start,'NATIVE_PEER_AUTHORITY_INTERVAL','STALE')
    current=timestamp(now())
    need(timestamp(request['issuedAt'])<=start<finish<=timestamp(response['probeStartedAt']) and
         finish<=issued<=timestamp(response['issuedAt'])<=current<expires<=timestamp(launch['expiresAt']) and
         timestamp(launch['issuedAt'])<=start and timestamp(producer['issuedAt'])<=start and
         expires<=min(timestamp(proof['expiresAt']),timestamp(producer['expiresAt'])) and
         (current-start).total_seconds()*1000<=integer(maximum_age_ms,1) and
         (timestamp(response['issuedAt'])-timestamp(request['issuedAt'])).total_seconds()*1000<=integer(request['deadlineMilliseconds'],1),
         'NATIVE_PEER_ADMISSION_TIME','STALE')
    view.window(admission['expiresAt']);view.recheck()
    return admission
