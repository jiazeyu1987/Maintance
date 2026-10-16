"""Offline consumer contracts with real bytes/signatures; no Linux execution acceptance."""
import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_recovery_verification_native_observe_r7 import FreshPacket
from core import canonical, json_pin, pin_key, pins, read_pin, VerificationError
from evidence import native_runtime_proof, native_stream_verifier, _NATIVE_HELPERS
from native_observe import admit_response, validate_pair_times, verify_collection_evidence, verify_collection_sequence
from peer_installation import ADMISSION_VERSION, NAMESPACES
from lab_boundary import REHEARSAL


class PeerPacket(FreshPacket):
    def __init__(self,tmp_path,monkeypatch):
        super().__init__(tmp_path,monkeypatch)
        root=Path(__file__).parents[2]
        shared=Path('C:/Users/BJB110/.codex/worktrees/instance-snapshot-integration/IntRuoyiMaintance/ops/recovery')
        additions=[]
        for name in ('repository_records.py','repository_native_runtime.py','recovery_native_launcher.py','recovery_environment_supervisor.py'):
            source=(shared if name.startswith('repository_') else root/'ops/recovery')/name
            pin=self.blob('executor-source/'+name,source.read_bytes())
            # Unix literal metadata and actual Windows files use '/' in this engineering packet.
            pin['path']=Path(pin['path']).as_posix();additions.append(pin)
        self.sources=[*self.sources,*additions];self.supervisor=additions[-1]
        installation=json_pin(self.launch['installationPin'])['payload']
        installation.update(filePins=self.sources,dependencyPins=self.sources)
        self.launch['installationPin']=self.sign('executor-installation-r8.json',installation)
        self.launch.update(producerEntryPin=additions[2],signerEntryPin=additions[2])
        self.launch_pin=self.sign('control-launch-r8.json',self.launch)
        proof=json_pin(self.runtime_pin)['payload']
        self.producer=dict(schemaVersion='RepositoryLabNativeCaller/v1',rehearsalId=REHEARSAL,pid=20,startTicks=1,uid=0,gid=0,
            nativeRuntimeProofPin=self.runtime_pin,issuedAt=self.time(-20),expiresAt=self.time(300),
            **{name:proof[name] for name in ('hostId','bootId','rootDevice','rootInode',*NAMESPACES)})
        self.producer_pin=self.sign('producer-r8.json',self.producer)

    def process_for(self,call,runtime_pin):
        call['sourcePins']=self.sources
        return super().process_for(call,runtime_pin)

    def response(self,phase,sequence,start,*,collection='collection-1',variant=None):
        request,envelope,_=super().response(phase,sequence,start,collection=collection)
        selected=set(self.lab.selected);result=copy.deepcopy(envelope['payload'])
        request['issuedAt']=self.decimal_time(start-.8)
        installation=json_pin(self.launch['installationPin'])['payload'];prefix=f'{phase.lower()}{sequence}/admission/'
        manifest=self.blob(prefix+'manifest.json',canonical(installation)+(b'\n' if variant=='manifest' else b''))
        argv=[installation['pythonPin']['path'],self.launch['producerEntryPin']['path'],'admit-installation',
            '--installation-pin',canonical(self.launch['installationPin']).decode(),
            '--authority-pin',canonical(self.lab.admission['authorityKeyPin']).decode()]
        if variant=='argv':argv[2]='other-command'
        call=self.call(prefix,'NATIVE_INSTALLATION_ADMISSION',manifest,argv)
        call.update(command=canonical(argv).decode('utf-8'),
            startedAt=self.decimal_time(start-.7),finishedAt=self.decimal_time(start-.5))
        process=self.process_for(call,self.runtime_pin)
        if variant=='helper':
            call['sourcePins']=[pin for pin in self.sources if not pin['path'].endswith('/repository_native_runtime.py')]
            process['sourcePins']=call['sourcePins']
        process.update(stdoutPin=manifest,stderrPin=self.blob(prefix+'stderr.txt',b''))
        if variant=='unknown':process.update(terminationKind='UNKNOWN',waitStatus=None,actualExitCode=None,descendantState='UNKNOWN')
        parent=dict(terminal=dict(kind='TERMINAL',model='linux-owned-child-subreaper-v1',
            supervisorPid=process['supervisorPid'],workerPid=process['childPid'],unknown=False,workerDispatched=True,
            treeTerminated=True,failureCode=None,actualExitCode=0,
            supervisorIdentity=dict(pid=process['supervisorPid'],parent=self.producer['pid'],uid=0,gid=0,
                startTicks=process['supervisorStartTicks'],bootId=process['bootId'],
                namespaces={name:process[field] for field,name in NAMESPACES.items()}),
            dispatch=dict(argv=argv,cwd=process['cwd'],uid=0,gid=0),
            children=[dict(pid=process['childPid'],startTicks=process['childStartTicks'],uid=0,gid=0,reaped=True,actualWaitStatus=0)]),
            supervisorExitCode=0,failureCode=None,stdoutPin=process['stdoutPin'],stderrPin=process['stderrPin'])
        if variant=='parent':parent['terminal']['children'][0]['actualWaitStatus']=256
        if variant=='producer-parent':parent['terminal']['supervisorIdentity']['parent']=21
        self.save(prefix+'supervisor-terminal.json',parent);self.save(prefix+'process-original.json',process)
        call['processResultPin']=self.sign(prefix+'signed-process.json',process)
        invocation=self.save(prefix+'invocation.json',call)
        admission=dict(schemaVersion=ADMISSION_VERSION,rehearsalId=REHEARSAL,collectionId=collection,sequence=sequence,phase=phase,
            operationRequestPin=request['operationRequestPin'],serviceBindingPin=request['serviceBindingPin'],launchPin=self.launch_pin,
            installationPin=self.launch['installationPin'],nativeRuntimeTrustPin=installation['nativeRuntimeTrustPin'],
            nativeRuntimeProofPin=self.runtime_pin,producerIdentityPin=self.producer_pin,invocationPin=invocation,manifestResultPin=manifest,
            startedAt=call['startedAt'],finishedAt=call['finishedAt'],issuedAt=self.decimal_time(start-.4),expiresAt=self.time(250))
        if variant=='phase':admission['phase']='AFTER' if phase=='BEFORE' else 'BEFORE'
        if variant=='runtime':admission['nativeRuntimeProofPin']=json_pin(self.lab.context['installedClosurePin'])['payload']['nativeRuntimeProofPin']
        if variant=='late-admission':admission['finishedAt']=self.decimal_time(start+.1)
        if variant=='launch':admission['launchPin']=self.launch['installationPin']
        admission_pin=self.sign(prefix+'admission.json',admission,'evidence' if variant=='authority' else 'authority')
        if variant=='duplicate':self.sign(prefix+'second-admission.json',admission)
        originals=[self.pin_from_key(key) for key in self.lab.selected-selected]
        if variant=='missing':originals=[pin for pin in originals if pin_key(pin)!=pin_key(admission_pin)]
        if variant=='extra':originals.append(self.blob(prefix+'extra.txt',b'extra'))
        result['originalPins']+=originals
        response_pin=self.sign(prefix+'response.json',result);self.lab.selected=selected
        return request,json_pin(response_pin),response_pin

    def check_response(self,request,envelope):
        return admit_response(self.lab,self.launch,request,envelope,self.expected,self.sources,60000,launch_pin=self.launch_pin)


def test_authenticated_peer_closure_without_executor_self_admission(tmp_path,monkeypatch):
    packet=PeerPacket(tmp_path,monkeypatch);before=dict(_NATIVE_HELPERS)
    record=packet.pair();validate_pair_times(record,packet.lab)
    assert _NATIVE_HELPERS==before
    assert record['before']['observation']['observedAt']==packet.decimal_time(-9.75)
    assert record['after']['observation']['observedAt']==packet.decimal_time(-4.75)
    context=SimpleNamespace(lab=packet.lab,request=dict(operationId='engineering-op',
        sourceOrTargetRef=packet.expected['environmentConfigPin'],
        inputPins=dict(applicationStartResult=packet.expected['applicationStartPin']),
        policyPin=packet.save('policy-r8.json',{'maxAgeMilliseconds':60000})),
        plan=dict(restoreId='restore-r6',recoveryPoint='point-r6'),target_pin=packet.target,
        source_pin=packet.expected['sourceScopePin'],source_pins=packet.sources,
        record=packet.lab.original,read=lambda pin:read_pin(pin,content=False))
    assert verify_collection_evidence(context,record,packet.binding_pin)==record['after']['observation']
    verify_collection_sequence(context,[record])
    assert _NATIVE_HELPERS==before


@pytest.mark.parametrize('variant,code',[
    ('missing','NATIVE_PEER_ADMISSION_UNIQUE_REQUIRED'),('duplicate','NATIVE_PEER_ADMISSION_UNIQUE_REQUIRED'),
    ('extra','NATIVE_OBSERVE_CLOSURE_EXTRA_OR_STATIC'),('authority','NATIVE_OBSERVE_AUTHORITY'),
    ('phase','NATIVE_PEER_PHASE_BINDING'),('runtime','NATIVE_PEER_RUNTIME_BINDING'),
    ('launch','NATIVE_PEER_LAUNCH_BINDING'),('argv','NATIVE_PEER_FIXED_ARGV'),
    ('helper','NATIVE_PEER_SOURCE_INSTALLATION'),('unknown','NATIVE_PROCESS_EXIT_UNKNOWN'),
    ('parent','NATIVE_PEER_CHILD_IDENTITY'),('producer-parent','NATIVE_PEER_PRODUCER_PARENT'),
    ('manifest','NATIVE_PEER_MANIFEST_RESULT'),('late-admission','NATIVE_PEER_ACTUAL_TIME')])
def test_peer_original_rejections_are_atomic(tmp_path,monkeypatch,variant,code):
    packet=PeerPacket(tmp_path,monkeypatch);request,envelope,_=packet.response('BEFORE',1,-10,variant=variant)
    selected=set(packet.lab.selected)
    with pytest.raises(VerificationError,match=code):packet.check_response(request,envelope)
    assert packet.lab.selected==selected


def test_after_installation_must_start_after_collection(tmp_path,monkeypatch):
    packet=PeerPacket(tmp_path,monkeypatch);record=packet.pair()
    record['finishedAt']=packet.decimal_time(-5.6)
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_COLLECTION_INTERVAL'):validate_pair_times(record,packet.lab)


def test_admission_cannot_predate_selected_authority_context(tmp_path,monkeypatch):
    packet=PeerPacket(tmp_path,monkeypatch)
    packet.rebind(issuedAt=packet.decimal_time(-10.6))
    request,envelope,_=packet.response('BEFORE',1,-10)
    with pytest.raises(VerificationError,match='NATIVE_PEER_AUTHORITY_INTERVAL'):
        packet.check_response(request,envelope)


def test_executor_never_enters_verifier_self_admission(tmp_path,monkeypatch):
    packet=PeerPacket(tmp_path,monkeypatch)
    with pytest.raises(VerificationError,match='NATIVE_SELF_VERIFIER_REQUIRED'):
        native_runtime_proof(packet.lab,packet.runtime_pin,'EXECUTOR',60000)
    with pytest.raises(VerificationError,match='NATIVE_SELF_INSTALLATION_REQUIRED'):
        native_stream_verifier(packet.lab,packet.launch['installationPin'])
