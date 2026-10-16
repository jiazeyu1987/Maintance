"""Offline engineering contracts, real temporary bytes/Ed25519; no Linux or business acceptance.

Only the Linux-private trust Pin path predicate is isolated for Windows temporary
storage. It is separately checked with literal Linux strings; no product path
translation, supervisor, Docker, network, database or browser is used.
"""
import base64
import copy
import datetime as dt
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_recovery_verification_lab import fixture, admit
from core import canonical, file_pin, json_pin, pin_key, read_pin, VerificationError
from lab_boundary import REHEARSAL, ROOT
from evidence import EvidenceContext, native_process_result, native_runtime_proof, native_private_path
from service_identity import native_service_identity, probe_service, IDENTITY_PROFILE, native_identity_argv
import evidence


class Packet:
    def __init__(self, tmp_path, monkeypatch):
        self.root, self.roles = tmp_path, {}
        self.values=fixture(tmp_path, key_roles=self.roles)
        self.lab=admit(self.values)
        self.clock=dt.datetime.now(dt.timezone.utc)
        self.sources=[]
        self.python=self.blob('python.bin',Path(sys.executable).read_bytes())
        self.supervisor=self.blob('supervisor.py', (Path(__file__).parents[2]/'ops/recovery/recovery_environment_supervisor.py').read_bytes())
        self.docker=self.blob('docker.bin', b'engineering opaque executable identity, never executed')
        self.sources=[self.python,self.supervisor,self.docker]
        self.target=self.lab.admission['targetIdentityPin']
        self.result=self.save('observation.json',{'engineeringOnly':True})
        self.stdout=self.blob('stdout.txt',b'')
        self.stderr=self.blob('stderr.txt',b'')
        self.trust_pins=set()
        original_path_check=evidence.native_private_path
        def temporary_trust_path(value):
            if value not in self.trust_pins:
                original_path_check(value)
        monkeypatch.setattr(evidence,'native_private_path',temporary_trust_path)
        self.runtime=self.runtime_for('VERIFIER')
        installed=self.sign('installation-r6.json',dict(schemaVersion='RepositoryNativeInstallation/v2', root=ROOT,
            sourceToolkitPin=self.supervisor,filePins=self.sources,pythonPin=self.python,dependencyPins=self.sources,
            nativeRuntimeTrustPin=self.runtime['nativeRuntimeTrustPin'],nativeRuntimeProofPin=self.runtime_pin))
        host=json_pin(self.lab.admission['executionHostPin'])
        host.update(pythonPin=self.python, installationManifestPin=installed)
        host_pin=self.save('host-r6.json',host)
        self.rebind(installedClosurePin=installed,executionHostPin=host_pin)
        self.invocation=self.call('CALL','COLLECT_DATA',self.result,[self.python['path'],self.supervisor['path']])
        self.process=self.process_for(self.invocation,self.runtime_pin)
        self.process_pin=self.sign('process.json',self.process)
        self.invocation['processResultPin']=self.process_pin

    def time(self,delta):
        return (self.clock+dt.timedelta(seconds=delta)).isoformat().replace('+00:00','Z')

    def blob(self,name,raw):
        path=self.root/name
        path.write_bytes(raw)
        value=file_pin(str(path))
        self.lab.selected.add(pin_key(value))
        return value

    def save(self,name,value):
        return self.blob(name,canonical(value))

    def sign(self,name,payload,role='authority'):
        key,key_pin=self.roles[role]
        return self.save(name,dict(schemaVersion='RepositorySignedRecord/v1',keySha256=key_pin['sha256'],payload=payload,
            signature=base64.b64encode(key.sign(canonical(payload))).decode()))

    def rebind(self,**values):
        context=copy.deepcopy(self.lab.context)
        context.update({k:v for k,v in values.items() if k in context})
        new_context=self.sign('context-r6-'+str(len(self.lab.selected))+'.json',context)
        self.lab.selected.remove(pin_key(new_context))
        self.lab.context_pin=new_context
        os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_PATH']=new_context['path']
        os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_SHA256']=new_context['sha256']
        self.lab.launch_selection=(new_context['path'],new_context['sha256'])
        admission=copy.deepcopy(self.lab.admission)
        admission.update({k:v for k,v in values.items() if k in admission})
        self.lab.admission_pin=self.save('admission-r6-'+str(len(self.lab.selected))+'.json',admission)
        self.lab.recheck()

    def runtime_for(self,role):
        vendor=self.blob(role+'-vendor.bin',b'engineering provenance bytes, not native runtime')
        trust=dict(schemaVersion='RepositoryLabNativeRuntimeTrust/v1', rehearsalId=REHEARSAL,labRoot=ROOT,
            runtimeId='engineering-'+role,runtimeRole=role,backingRootPath=ROOT+'/engineering/'+role,
            literalRoots=['/lib64','/usr/lib64'],immutableRuntimeArtifactDigest='sha256:'+'a'*64,
            vendorArtifactPins=[vendor],nativeFilePins=[dict(pin=self.python,roles=['native-interpreter'],vendorArtifactPins=[vendor])])
        trust_pin=self.sign(role+'-trust.json',trust)
        self.trust_pins.add(trust_pin['path'])
        raw=self.save(role+'-raw.json',dict(engineeringOnly='no native filesystem attestation'))
        host=json_pin(self.lab.admission['executionHostPin'])
        proof=dict(schemaVersion='RepositoryLabNativeRuntimeProof/v1',rehearsalId=REHEARSAL,runtimeId=trust['runtimeId'],
            nativeRuntimeTrustPin=trust_pin,issuedAt=self.time(-30),expiresAt=self.time(600),hostId=host['hostId'],
            bootId=host['bootId'],managerPid=2,managerStartTicks=1,pidNamespace=host['pidNamespace'],
            mountNamespace=host['mountNamespace'],networkNamespace='engineering-netns',userNamespace='engineering-userns',
            rootDevice=1,rootInode=2,immutableRuntimeArtifactDigest=trust['immutableRuntimeArtifactDigest'],
            readOnlyMountEvidencePin=raw,managerIdentityEvidencePin=raw,nativeLinkageEvidencePin=raw)
        self.runtime_pin=self.sign(role+'-runtime.json',proof)
        return proof

    def call(self,name,stage,result,argv):
        return dict(schemaVersion='RecoveryInvocation/v1',operationId='engineering-op',restoreId='restore-r6',
            targetIdentityPin=self.target,recoveryPoint='point-r6',stage=stage,state='SUCCEEDED',actualExitCode=0,
            startedAt=self.time(-10),finishedAt=self.time(-9),sourcePins=self.sources,resultPin=result,
            commandId=name,command='literal engineering '+name,argv=argv,cwd=str(self.root),
            processProfile='linux-owned-child-subreaper-v1',processResultPin=self.result)

    def process_for(self,call,runtime_pin):
        runtime=json_pin(runtime_pin)['payload']
        return dict(schemaVersion='RecoveryNativeProcessResult/v1',rehearsalId=REHEARSAL,
            **{k:call[k] for k in ('operationId','restoreId','targetIdentityPin','recoveryPoint','stage','commandId','command',
                                  'argv','cwd','sourcePins','startedAt','finishedAt','actualExitCode','resultPin')},
            supervisorPin=self.supervisor,pythonPin=self.python,nativeRuntimeProofPin=runtime_pin,
            **{k:runtime[k] for k in ('hostId','bootId','pidNamespace','mountNamespace','networkNamespace','userNamespace')},
            supervisorPid=3,supervisorStartTicks=2,childPid=4,childStartTicks=3,uid=0,gid=0,
            terminationKind='EXITED',waitStatus=0,descendantState='REAPED',stdoutPin=self.stdout,stderrPin=self.stderr)

    def check(self):
        return native_process_result(self.lab,self.process_pin,self.invocation,self.sources,60000)

    def service(self):
        source_identity=self.save('business-source.json',{})
        source=self.save('source-scope.json',dict(schemaVersion='RecoverySourceScope/v1',sourceIdentityPin=source_identity,
            containerIds=['protected-container'],containerNames=['protected-minio'],endpointHosts=['10.0.0.1']))
        self.target=self.save('service-target.json',dict(schemaVersion='RecoveryTargetIdentity/v1',targetId='engineering-target',
            machineId='actual-native-host',dockerEngineId='engine-target'))
        self.rebind(targetIdentityPin=self.target)
        configuration=self.save('service-config.json',dict(schemaVersion='RecoveryEnvironmentConfig/v1',
            targetIdentityPin=self.target,sourceScopePin=source,dockerPin=self.docker,
            services=[dict(role='minio',name='target-minio',health=dict(port=9000))]))
        net=dict(NetworkID='net-target',EndpointID='endpoint-target',IPAddress='10.254.0.3')
        service=dict(id='container-target',imageId='image-target',name='/target-minio',networks={'network':net})
        resources=self.save('resources.json',dict(schemaVersion='RecoveryEnvironmentProof/v1',targetIdentityPin=self.target,
            configurationRef=configuration,operationId='engineering-op',resources=dict(machineId='actual-native-host',
            dockerEngineId='engine-target'),services=[service],network=dict(networkId='net-target')))
        endpoint=dict(Name='target-minio',EndpointID='endpoint-target',IPv4Address='10.254.0.3/24')
        launch=self.save('launch.json',dict(schemaVersion='RecoveryApplicationLaunch/v1',network=dict(networkId='net-target',
            containers={'container-target':endpoint})))
        start=self.save('start.json',dict(schemaVersion='ApplicationStartResult/v1',state='SUCCEEDED',operationId='engineering-op',
            targetIdentityPin=self.target,originalStartResultPins=[launch]))
        info=self.save('info.json',dict(ID='engine-target'))
        self.raw_inspect=[dict(Id=service['id'],Image=service['imageId'],Name=service['name'],State=dict(Running=True),
            Config=dict(Labels={'intruoyi.recovery.target':'engineering-target','intruoyi.recovery.operation':'engineering-op'}),
            NetworkSettings=dict(Networks={'network':net}))]
        inspect=self.save('inspect.json',self.raw_inspect)
        network=self.save('network.json',[dict(Id='net-target',Containers={'container-target':endpoint})])
        self.runtime_for('EXECUTOR')
        executor=self.runtime_pin
        calls=[]
        for name,result in [('info',info),('inspect',inspect),('network',network)]:
            call=self.call(name,'NATIVE_'+name.upper(),result,native_identity_argv(self.docker['path'],name,'container-target','net-target'))
            process=self.process_for(call,executor)
            process['stdoutPin']=result
            call['processResultPin']=self.sign(name+'-process.json',process)
            calls.append(self.save(name+'-invocation.json',call))
        proof=dict(schemaVersion='RecoveryNativeServiceIdentity/v1',rehearsalId=REHEARSAL,operationId='engineering-op',
            restoreId='restore-r6',targetIdentityPin=self.target,sourceScopePin=source,environmentConfigPin=configuration,
            resourcesProofPin=resources,applicationStartPin=start,role='minio',endpointUrl='http://10.254.0.3:9000',
            dockerPin=self.docker,probeSourcePin=self.supervisor,probeRuntimeProofPin=executor,infoResultPin=info,
            inspectResultPin=inspect,networkResultPin=network,invocationPins=calls,machineId='actual-native-host',
            dockerEngineId='engine-target',containerId='container-target',imageId='image-target',networkId='net-target',
            endpointId='endpoint-target',ipAddress='10.254.0.3',issuedAt=self.time(-8),expiresAt=self.time(500))
        self.identity_proof=proof
        self.binding=dict(schemaVersion='RecoveryServiceBinding/v2',targetIdentityPin=self.target,sourceScopePin=source,
            environmentConfigPin=configuration,resourcesProofPin=resources,dockerPin=self.docker,machineIdPath='/etc/machine-id',
            role='minio',endpointUrl=proof['endpointUrl'],applicationStartPin=start,identityProfile=IDENTITY_PROFILE,
            nativeIdentityProofPin=self.sign('native-identity.json',proof))
        self.binding_pin=self.save('binding-v2.json',self.binding)
        self.expected=dict(operationId='engineering-op',restoreId='restore-r6',recoveryPoint='point-r6',
            targetIdentityPin=self.target,sourceScopePin=source,environmentConfigPin=configuration,applicationStartPin=start)
        return self.binding_pin

    def check_service(self):
        return native_service_identity(self.binding_pin,self.lab,self.expected,self.sources,60000)

    def replace_service_raw(self, verb, value, *, process_change=None):
        """Re-pin and A-sign the entire engineering chain, preserving raw stdout."""
        result_name={'info':'infoResultPin','inspect':'inspectResultPin','network':'networkResultPin'}[verb]
        old=self.identity_proof[result_name]
        replacement=self.save('changed-'+verb+'-raw.json',value)
        self.identity_proof[result_name]=replacement
        for index, reference in enumerate(self.identity_proof['invocationPins']):
            call=copy.deepcopy(json_pin(reference))
            if call['resultPin'] != old:
                continue
            process=copy.deepcopy(json_pin(call['processResultPin'])['payload'])
            call['resultPin']=replacement
            process.update(resultPin=replacement,stdoutPin=replacement)
            if process_change:
                process_change(call,process)
            call['processResultPin']=self.sign('changed-'+verb+'-process.json',process)
            self.identity_proof['invocationPins'][index]=self.save('changed-'+verb+'-invocation.json',call)
        self.binding['nativeIdentityProofPin']=self.sign('changed-identity.json',self.identity_proof)
        self.binding_pin=self.save('changed-binding.json',self.binding)


def test_complete_signed_native_result_and_existing_invocation_consumer(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch)
    assert p.check()['actualExitCode']==0
    policy=p.save('native-policy.json',dict(maxAgeMilliseconds=60000))
    context=EvidenceContext.__new__(EvidenceContext)
    context.lab=p.lab;context.source_pins=p.sources;context.source_keys=set(map(pin_key,p.sources))
    context.request=dict(operationId='engineering-op',policyPin=policy)
    context.plan=dict(restoreId='restore-r6',recoveryPoint='point-r6');context.target_pin=p.target
    context.record=p.lab.original;context.read=lambda pin:read_pin(pin,content=False)
    context.trace=dict(startedAt=p.time(-11),finishedAt=p.time(-7))
    call=p.save('native-call.json',p.invocation)
    assert context.invocation(call,'COLLECT_DATA',[p.result])==p.invocation


@pytest.mark.parametrize('name,value,verdict',[
    ('operationId','wrong','STALE'),('restoreId','wrong','STALE'),('recoveryPoint','wrong','STALE'),
    ('stage','wrong','STALE'),('commandId','wrong','STALE'),('argv',['wrong'],'STALE'),
    ('pidNamespace','wrong','STALE'),('mountNamespace','wrong','STALE'),('networkNamespace','wrong','STALE'),
    ('userNamespace','wrong','STALE'),('bootId','wrong','STALE'),('hostId','wrong','STALE'),
    ('uid',True,'BLOCKED'),('uid',1,'BLOCKED'),('childPid',3,'BLOCKED'),('childStartTicks',1,'BLOCKED'),
    ('terminationKind','UNKNOWN','UNKNOWN'),('descendantState','UNKNOWN','UNKNOWN'),('waitStatus',None,'UNKNOWN'),
    ('actualExitCode',None,'UNKNOWN'),('waitStatus',True,'BLOCKED'),('waitStatus',128,'BLOCKED'),
    ('actualExitCode',False,'FAILED'),('extra',True,'BLOCKED')])
def test_signed_wrong_binding_status_namespace_and_shape_rejected(tmp_path,monkeypatch,name,value,verdict):
    p=Packet(tmp_path,monkeypatch);p.process[name]=value
    p.process_pin=p.sign('bad-process.json',p.process)
    with pytest.raises(VerificationError) as error:p.check()
    assert error.value.verdict==verdict


@pytest.mark.parametrize('kind,status,exit_code',[('EXITED',256,1),('SIGNALED',9,-9),('SIGNALED',137,-9)])
def test_nonzero_or_signal_is_failed_not_success(tmp_path,monkeypatch,kind,status,exit_code):
    p=Packet(tmp_path,monkeypatch)
    p.process.update(terminationKind=kind,waitStatus=status,actualExitCode=exit_code)
    p.invocation.update(state='FAILED_RETAINED',actualExitCode=exit_code)
    p.process_pin=p.sign('failed-process.json',p.process)
    with pytest.raises(VerificationError) as error:p.check()
    assert error.value.verdict=='FAILED'


def test_no_lab_wrong_authority_tamper_missing_original_and_bool_invocation(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch)
    with pytest.raises(VerificationError,match='NATIVE_PROFILE_LAB_ONLY'):
        native_process_result(None,p.process_pin,p.invocation,p.sources,60000)
    p.process_pin=p.sign('wrong-key.json',p.process,'evidence')
    with pytest.raises(VerificationError,match='LAB_SIGNING_KEY_NOT_SELECTED'):p.check()
    p.process_pin=p.sign('tampered.json',p.process)
    raw=json_pin(p.process_pin);raw['payload']['uid']=1
    p.process_pin=p.save('tampered-signed.json',raw)
    with pytest.raises(VerificationError,match='LAB_SIGNATURE_INVALID'):p.check()
    p.process_pin=p.sign('missing-stdout.json',p.process)
    p.lab.selected.remove(pin_key(p.stdout))
    with pytest.raises(VerificationError,match='LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED'):p.check()
    p.lab.selected.add(pin_key(p.stdout));p.invocation['actualExitCode']=False
    with pytest.raises(VerificationError,match='NATIVE_PROCESS_INVOCATION_EXIT_INTEGER'):p.check()


def test_private_paths_runtime_role_and_stale_proof(tmp_path,monkeypatch):
    native_private_path(ROOT+'/native/trust.json')
    for path in ['/etc/trust.json',ROOT+'/../other',ROOT+'//native/trust.json','C:/trust.json']:
        with pytest.raises(VerificationError):native_private_path(path)
    p=Packet(tmp_path,monkeypatch)
    with pytest.raises(VerificationError,match='NATIVE_RUNTIME_ROLE_OR_SCOPE'):
        native_runtime_proof(p.lab,p.runtime_pin,'EXECUTOR',60000)
    bad=copy.deepcopy(p.runtime);bad['issuedAt']=p.time(-70)
    with pytest.raises(VerificationError,match='NATIVE_RUNTIME_PROOF_STALE'):
        native_runtime_proof(p.lab,p.sign('stale-runtime.json',bad),'VERIFIER',60000)


@pytest.mark.parametrize('original',['supervisor','runtime','process'])
def test_lost_native_original_has_unknown_terminal_state(tmp_path,monkeypatch,original):
    p=Packet(tmp_path,monkeypatch)
    pin={'supervisor':p.supervisor,'runtime':p.runtime_pin,'process':p.process_pin}[original]
    Path(pin['path']).unlink()
    with pytest.raises(VerificationError,match='NATIVE_PROCESS_ORIGINAL_UNAVAILABLE') as error:p.check()
    assert error.value.verdict=='UNKNOWN'


def test_native_installation_requires_current_authority_signature(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch)
    installed=json_pin(p.lab.context['installedClosurePin'])['payload']
    unsigned=p.save('unsigned-installation.json',installed)
    host=json_pin(p.lab.admission['executionHostPin']);host['installationManifestPin']=unsigned
    p.rebind(installedClosurePin=unsigned,executionHostPin=p.save('unsigned-host.json',host))
    with pytest.raises(VerificationError,match='RECORD_FIELDS'):p.check()


def test_signed_service_identity_uses_raw_native_host_not_manager_and_executes_nothing(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch);p.service()
    observed=p.check_service()
    assert observed['machineId']=='actual-native-host' and observed['containerId']=='container-target'
    assert observed['endpointUrl']=='http://10.254.0.3:9000'
    p.lab.deadline.native_service_context=dict(boundary=p.lab,expected=p.expected,sourcePins=p.sources,maximumAgeMilliseconds=60000)
    with pytest.raises(VerificationError,match='SERVICE_NATIVE_FRESH_CLIENT_REQUIRED'):
        probe_service(p.binding_pin,p.lab.deadline)


@pytest.mark.parametrize('name,value',[
    ('operationId','wrong'),('restoreId','wrong'),('role','redis'),('endpointUrl','http://10.254.0.4:9000'),
    ('machineId','manager-rewrite'),('dockerEngineId','wrong'),('imageId','wrong'),('networkId','wrong'),
    ('endpointId','wrong'),('ipAddress','wrong'),('issuedAt','2020-01-01T00:00:00Z'),
    ('expiresAt','2020-01-01T00:00:00Z'),('extra',True)])
def test_native_service_wrong_identity_or_stale_shape_rejected(tmp_path,monkeypatch,name,value):
    p=Packet(tmp_path,monkeypatch);p.service();p.identity_proof[name]=value
    p.binding['nativeIdentityProofPin']=p.sign('bad-identity.json',p.identity_proof)
    p.binding_pin=p.save('bad-binding.json',p.binding)
    with pytest.raises(VerificationError):p.check_service()


def test_native_service_raw_running_address_and_source_are_not_attested_defaults(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch);p.service()
    p.raw_inspect[0]['State']['Running']=False
    # Changing bytes under a selected Pin is caught before any raw result can pass.
    Path(p.identity_proof['inspectResultPin']['path']).write_bytes(canonical(p.raw_inspect))
    with pytest.raises(VerificationError,match='PIN_MISMATCH'):p.check_service()


def test_native_service_not_selected_or_wrong_source_fails_before_any_socket(tmp_path,monkeypatch):
    p=Packet(tmp_path,monkeypatch);p.service()
    with pytest.raises(VerificationError,match='SERVICE_NATIVE_CALLER_SELECTION_REQUIRED'):
        probe_service(p.binding_pin,p.lab.deadline)
    p.expected['sourceScopePin']=p.target
    with pytest.raises(VerificationError,match='SERVICE_NATIVE_CURRENT_SOURCE'):p.check_service()


@pytest.mark.parametrize('case,expected_error',[
    ('stopped','SERVICE_INSTANCE_IDENTITY_MISMATCH'),
    ('image','SERVICE_INSTANCE_IDENTITY_MISMATCH'),
    ('label','SERVICE_INSTANCE_IDENTITY_MISMATCH'),
    ('address','SERVICE_NETWORK_IDENTITY_MISMATCH'),
    ('network-endpoint','SERVICE_NATIVE_NETWORK_ENDPOINT'),
    ('engine','SERVICE_DOCKER_ENGINE_MISMATCH'),
    ('credential-field','RECORD_FIELDS'),
])
def test_resigned_raw_identity_must_match_protected_launch(tmp_path,monkeypatch,case,expected_error):
    p=Packet(tmp_path,monkeypatch);p.service()
    verb='inspect';raw=copy.deepcopy(p.raw_inspect)
    if case=='stopped':raw[0]['State']['Running']=False
    elif case=='image':raw[0]['Image']='different-image'
    elif case=='label':raw[0]['Config']['Labels']['intruoyi.recovery.operation']='different-operation'
    elif case=='address':raw[0]['NetworkSettings']['Networks']['network']['IPAddress']='10.254.0.4'
    elif case=='network-endpoint':
        verb='network';raw=json_pin(p.identity_proof['networkResultPin'])
        raw[0]['Containers']['container-target']['EndpointID']='different-endpoint'
    elif case=='engine':verb='info';raw={'ID':'different-engine'}
    elif case=='credential-field':raw[0]['Config']['Env']=['SECRET=engineering-only']
    p.replace_service_raw(verb,raw)
    with pytest.raises(VerificationError,match=expected_error):p.check_service()


@pytest.mark.parametrize('case,expected_error',[
    ('unsafe-argv','SERVICE_NATIVE_READONLY_ARGV'),
    ('rewritten-stdout','SERVICE_NATIVE_RAW_STDOUT_MISMATCH'),
    ('stderr','SERVICE_NATIVE_RAW_STDOUT_MISMATCH'),
])
def test_resigned_native_process_must_keep_literal_readonly_command_and_stdout(tmp_path,monkeypatch,case,expected_error):
    p=Packet(tmp_path,monkeypatch);p.service()
    def mutate(call,process):
        if case=='unsafe-argv':
            call['argv']=[p.docker['path'],'rm','container-target'];process['argv']=call['argv']
        elif case=='rewritten-stdout':process['stdoutPin']=p.result
        elif case=='stderr':process['stderrPin']=p.blob('error.txt',b'actual warning')
    p.replace_service_raw('info',json_pin(p.identity_proof['infoResultPin']),process_change=mutate)
    with pytest.raises(VerificationError,match=expected_error):p.check_service()
