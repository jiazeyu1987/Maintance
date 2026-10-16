"""Offline genuine bytes/Ed25519 contract tests; no native/service/business claim."""
import copy
import datetime as dt
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_recovery_verification_native_contract_r6 import Packet
from core import canonical, json_pin, pin_key, pins, read_pin, VerificationError
from lab_boundary import REHEARSAL, ROOT
import native_observe as module
from native_observe import (admit_response, current_launch, collection_evidence, validate_pair_times,
                            verify_collection_evidence, verify_collection_sequence, authenticate)


class FreshPacket(Packet):
    def blob(self,name,raw):
        (self.root/name).parent.mkdir(parents=True,exist_ok=True)
        return super().blob(name,raw)
    def __init__(self,tmp_path,monkeypatch):
        super().__init__(tmp_path,monkeypatch);self.service()
        # Windows originals exercise signed admission only. Actual Linux custody/peer
        # checks are not bypassed in product and are not claimed by these tests.
        def temporary_path(value,**kwargs):
            normalized_root=os.path.normcase(str(tmp_path))
            normalized_value=os.path.normcase(value)
            if normalized_root in normalized_value:
                assert os.path.commonpath([normalized_root,normalized_value])==normalized_root
            else:
                assert value.startswith(ROOT+'/')
        monkeypatch.setattr(module,'private_path',temporary_path)
        verifier=json_pin(self.lab.context['installedClosurePin'])['payload']
        caller=self.sign('caller.json',dict(schemaVersion='RepositoryLabNativeCaller/v1',rehearsalId=REHEARSAL,pid=1,startTicks=1,
            uid=0,gid=0,nativeRuntimeProofPin=verifier['nativeRuntimeProofPin'],hostId='engineering-host',bootId='engineering-boot',
            pidNamespace='engineering-pidns',mountNamespace='engineering-mntns',networkNamespace='engineering-netns',
            userNamespace='engineering-userns',rootDevice=1,rootInode=2,issuedAt=self.time(-20),expiresAt=self.time(400)))
        executor=self.sign('executor-installation.json',dict(verifier,nativeRuntimeProofPin=self.runtime_pin,
            nativeRuntimeTrustPin=json_pin(self.runtime_pin)['payload']['nativeRuntimeTrustPin']))
        self.launch=dict(schemaVersion='RepositoryLabNativeLaunch/v1',rehearsalId=REHEARSAL,
            operationRequestPin=self.lab.context['operationRequestPin'],installationPin=executor,
            authorityKeyPin=self.lab.admission['authorityKeyPin'],authorizationPin=self.lab.context['authorizationPin'],
            leasePin=self.lab.context['leasePin'],producerEntryPin=self.supervisor,signerEntryPin=self.supervisor,
            observationSocketPath=ROOT+'/engineering/observe.sock',evidenceRoot=ROOT+'/engineering/evidence',
            allowedCallerPin=caller,issuedAt=self.time(-20),expiresAt=self.time(400))
        self.launch_pin=self.sign('control-launch.json',self.launch)
        current_launch(self.lab,self.launch_pin,60000)

    def decimal_time(self,seconds):
        return (self.clock+dt.timedelta(seconds=seconds)).isoformat().replace('+00:00','Z')

    def response(self,phase,sequence,start,*,collection='collection-1'):
        prefix=phase.lower()+str(sequence);old_selected=set(self.lab.selected)
        proof=copy.deepcopy(self.identity_proof);calls=[]
        for index,verb in enumerate(('info','inspect','network')):
            original=json_pin(proof['invocationPins'][index])
            path=prefix+'/'+verb+'/'
            raw=self.blob(path+'stdout.json',read_pin(original['resultPin']))
            call=copy.deepcopy(original);call.update(resultPin=raw,commandId=prefix+'-'+verb,
                startedAt=self.decimal_time(start+index*.1),finishedAt=self.decimal_time(start+index*.1+.05))
            process=self.process_for(call,proof['probeRuntimeProofPin'])
            process.update(stdoutPin=raw,stderrPin=self.blob(path+'stderr.txt',b''))
            call['processResultPin']=self.sign(path+'signed-process.json',process)
            self.save(path+'process-original.json',process)
            self.save(path+'supervisor-terminal.json',dict(terminal=dict(model='linux-owned-child-subreaper-v1',
                supervisorPid=process['supervisorPid'],workerPid=process['childPid']),supervisorExitCode=0,failureCode=None,
                stdoutPin=process['stdoutPin'],stderrPin=process['stderrPin']))
            calls.append(self.save(path+'invocation.json',call))
            proof[{'info':'infoResultPin','inspect':'inspectResultPin','network':'networkResultPin'}[verb]]=raw
        proof.update(invocationPins=calls,issuedAt=self.decimal_time(start+.30),expiresAt=self.time(300))
        identity=self.sign(prefix+'-identity.json',proof)
        originals=[self.pin_from_key(key) for key in self.lab.selected-old_selected]
        request=dict(schemaVersion='RepositoryLabNativeObserveRequest/v1',rehearsalId=REHEARSAL,collectionId=collection,
            sequence=sequence,phase=phase,operationRequestPin=self.launch['operationRequestPin'],serviceBindingPin=self.binding_pin,
            issuedAt=self.decimal_time(start-.1),deadlineMilliseconds=30000)
        result=dict(schemaVersion='RepositoryLabNativeObserveResult/v1',rehearsalId=REHEARSAL,collectionId=collection,
            sequence=sequence,phase=phase,operationRequestPin=request['operationRequestPin'],serviceBindingPin=self.binding_pin,
            identityProofPin=identity,originalPins=originals,probeStartedAt=self.decimal_time(start),
            probeFinishedAt=self.decimal_time(start+.25),issuedAt=self.decimal_time(start+.35),expiresAt=self.time(300))
        response_pin=self.sign(prefix+'-response.json',result)
        envelope=json_pin(response_pin)
        self.lab.selected=old_selected
        return request,envelope,response_pin

    def pin_from_key(self,key):return dict(path=key[0],bytes=key[1],sha256=key[2])

    def check_response(self,request,envelope):
        return admit_response(self.lab,self.launch,request,envelope,self.expected,self.sources,60000)

    def pair(self):
        entries=[]
        for phase,sequence,start in [('BEFORE',1,-10),('AFTER',2,-5)]:
            request,envelope,response_pin=self.response(phase,sequence,start)
            payload,observed=self.check_response(request,envelope)
            self.lab.selected.update(pins(payload['originalPins']))
            self.lab.selected.add(pin_key(response_pin))
            entries.append(dict(launchPin=self.launch_pin,responsePin=response_pin,request=request,observation=observed))
        return collection_evidence(*entries,self.time(-8),self.time(-6))


def test_fresh_distinct_signed_originals_and_actual_historical_time(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch);record=p.pair()
    validate_pair_times(record,p.lab)
    assert record['before']['observation']['observedAt']==p.decimal_time(-9.75)
    assert record['after']['observation']['observedAt']==p.decimal_time(-4.75)
    context=SimpleNamespace(lab=p.lab,request=dict(operationId='engineering-op',sourceOrTargetRef=p.expected['environmentConfigPin'],
        inputPins=dict(applicationStartResult=p.expected['applicationStartPin']),policyPin=p.save('policy-r7.json',{'maxAgeMilliseconds':60000})),
        plan=dict(restoreId='restore-r6',recoveryPoint='point-r6'),target_pin=p.target,source_pin=p.expected['sourceScopePin'],
        source_pins=p.sources,record=p.lab.original,read=lambda pin:read_pin(pin,content=False))
    assert verify_collection_evidence(context,record,p.binding_pin)==record['after']['observation']
    verify_collection_sequence(context,[record])


@pytest.mark.parametrize('change',['wrong-key','tamper','phase','sequence','request','binding','stale','fake-interval','missing','extra','upstream'])
def test_untrusted_or_inexact_dynamic_closure_rejected_atomically(tmp_path,monkeypatch,change):
    p=FreshPacket(tmp_path,monkeypatch);request,envelope,_=p.response('BEFORE',1,-10)
    result=copy.deepcopy(envelope['payload']);initial=set(p.lab.selected)
    if change=='wrong-key':
        envelope=json_pin(p.sign('wrong-authority.json',result,'evidence'));p.lab.selected=initial
    elif change=='tamper':envelope['payload']['sequence']=2
    else:
        if change=='phase':result['phase']='AFTER'
        elif change=='sequence':result['sequence']=2
        elif change=='request':result['operationRequestPin']=p.target
        elif change=='binding':result['serviceBindingPin']=p.target
        elif change=='stale':result['expiresAt']=p.time(-1)
        elif change=='fake-interval':result['probeFinishedAt']=p.time(-9)
        elif change=='missing':result['originalPins']=result['originalPins'][1:]
        elif change=='extra':result['originalPins'].append(p.blob('extra.txt',b'extraneous'))
        elif change=='upstream':
            identity=json_pin(result['identityProofPin'])['payload'];identity['probeRuntimeProofPin']=p.save('new-runtime.json',{})
            replacement=p.sign('new-identity.json',identity)
            result['originalPins']=[pin for pin in result['originalPins'] if pin!=result['identityProofPin']]+[replacement]
            result['identityProofPin']=replacement
        envelope=json_pin(p.sign('bad-response.json',result));p.lab.selected=initial
    with pytest.raises(VerificationError):p.check_response(request,envelope)
    assert p.lab.selected==initial


@pytest.mark.parametrize('change',['static','overlap-before','overlap-after','changed-image','wrong-order','launch'])
def test_pair_requires_continuity_distinctness_and_real_collection_order(tmp_path,monkeypatch,change):
    p=FreshPacket(tmp_path,monkeypatch);record=p.pair()
    if change=='static':record['after']=copy.deepcopy(record['before'])
    elif change=='overlap-before':record['startedAt']=p.time(-11)
    elif change=='overlap-after':record['finishedAt']=p.time(-4)
    elif change=='changed-image':record['after']['observation']['imageId']='changed'
    elif change=='wrong-order':record['after']['request']['sequence']=1
    elif change=='launch':record['after']['launchPin']=p.target
    with pytest.raises(VerificationError):
        collection_evidence(record['before'],record['after'],record['startedAt'],record['finishedAt'])
        validate_pair_times(record,p.lab)


def test_total_existing_and_dynamic_graph_limit(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch);request,envelope,_=p.response('BEFORE',1,-10)
    p.lab.selected.update((str(tmp_path/f'existing-{i}'),0,'0'*64) for i in range(4090))
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_GRAPH_LIMIT'):p.check_response(request,envelope)


def test_protected_launch_wrong_request_and_unsigned_rejected(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch);bad=copy.deepcopy(p.launch);bad['operationRequestPin']=p.target
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_LAUNCH_BINDING'):
        current_launch(p.lab,p.sign('bad-launch.json',bad),60000)
    with pytest.raises(VerificationError,match='RECORD_FIELDS'):
        current_launch(p.lab,p.save('unsigned-launch.json',p.launch),60000)


def test_new_original_cannot_reuse_selected_path_with_changed_hash(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch);request,envelope,_=p.response('BEFORE',1,-10)
    selected=pin_key(envelope['payload']['originalPins'][0])
    p.lab.selected.add((selected[0],selected[1]+1,'0'*64))
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_REUSED_ORIGINAL_PATH'):
        p.check_response(request,envelope)


def test_finite_control_sequence_cannot_exceed_64(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch);request,envelope,_=p.response('BEFORE',65,-10)
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_SEQUENCE'):
        p.check_response(request,envelope)


def test_fresh_identity_must_use_current_launch_executor_runtime(tmp_path,monkeypatch):
    p=FreshPacket(tmp_path,monkeypatch)
    installation=copy.deepcopy(json_pin(p.launch['installationPin'])['payload'])
    installation['nativeRuntimeProofPin']=json_pin(p.lab.context['installedClosurePin'])['payload']['nativeRuntimeProofPin']
    p.launch['installationPin']=p.sign('wrong-launch-installation.json',installation)
    request,envelope,_=p.response('BEFORE',1,-10)
    with pytest.raises(VerificationError,match='NATIVE_OBSERVE_PRODUCER_RUNTIME'):
        p.check_response(request,envelope)
