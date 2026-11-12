"""Real context, journals, children and host locks; no server/business restore."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

from test_recovery_program_evidence import history_factory
from test_recovery_program_resource_release import child_exit, fixed_originals
from recovery_engine import pin,pinned_json,write
from recovery_program_evidence import validate_program_evidence
from recovery_retained_retry import verify_no_mutation
import recovery_resource_admission as admission

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual Linux context and flock')


def prepared(history_factory):
    h=history_factory(outcome='retained',phases='preparation',install_protection=False)
    assert h.custody['state']=='ACTIVE'
    assert all(s['state'] in ('NOT_INSTALLED','ABSENT') for s in h.custody['protections'].values())
    return h


def test_preparation_without_installed_protections_releases_only_exact_pointer(history_factory):
    h=prepared(history_factory);exited=child_exit(h,1);originals=fixed_originals(h)
    originals.update({p:p.read_bytes() for p in (h.e.root/'worker-result.json',h.e.claim/'replacement-result.json')})
    intent=h.e.root/'replacement-preparation/replacement-intent.json'
    write(intent,dict(operationId=h.e.request['operationId'],phase='PREPARATION'))
    originals[intent]=intent.read_bytes()
    proof=validate_program_evidence(h.e.owner,h.e.request,h.e.root,result_pin=h.result_pin)
    assert proof['phase']=='PREPARATION' and not proof['mutationDispatched'] and not proof['terminalUnknown']
    receipt=admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)
    assert not (admission.HOST_ROOT/'active.json').exists()
    assert pinned_json(receipt)['reason']=='PROVEN_NO_MUTATION'
    refs=dict(resultPin=h.result_pin,exitPin=exited)
    assert verify_no_mutation(h.e.owner,h.e.request,h.e.root,refs,receipt)==h.e.reservation
    assert admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)==receipt
    write(admission.HOST_ROOT/'active.json',dict(operationId='later-operation'))
    later=(admission.HOST_ROOT/'active.json').read_bytes()
    assert admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)==receipt
    assert (admission.HOST_ROOT/'active.json').read_bytes()==later
    assert all(p.read_bytes()==raw for p,raw in originals.items())


@pytest.mark.parametrize('fault',['installed','other-reservation','unknown-call','changed-original','generation'])
def test_preparation_release_rejects_incomplete_or_mutated_history(history_factory,fault):
    h=(history_factory(outcome='retained',phases='preparation') if fault=='installed' else
       history_factory(outcome='generation-before-stage') if fault=='generation' else prepared(history_factory))
    exited=child_exit(h,1)
    if fault=='other-reservation':write(admission.HOST_ROOT/'active.json',dict(operationId='other'))
    elif fault=='unknown-call':
        write(h.e.root/'replacement-preparation/native-extra.json',dict(mutation=False,actualExitCode=None,state='TERMINAL_UNKNOWN'))
    elif fault=='changed-original':
        Path(h.context['path']).write_bytes(b'{}')
    before=(admission.HOST_ROOT/'active.json').read_bytes()
    with pytest.raises(Exception):
        admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)
    assert (admission.HOST_ROOT/'active.json').read_bytes()==before
    assert not (h.e.root/'resource-no-mutation-release.json').exists()


@pytest.mark.parametrize('fault',['phase','mutation','unknown','custody','step','missing-terminal'])
def test_clearance_consumer_revalidates_preparation_even_without_intent(history_factory,monkeypatch,fault):
    h=prepared(history_factory);exited=child_exit(h,1)
    receipt=admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)
    actual=admission._program_release_evidence;calls=[]
    def augmented(*args):
        value=deepcopy(actual(*args));calls.append(True)
        if fault=='phase':value['phase']='RESTORE'
        elif fault=='mutation':value['mutationDispatched']=True
        elif fault=='unknown':value['terminalUnknown']=True
        elif fault=='custody':value['protectionState']='FAILED_RETAINED'
        elif fault=='step':value['protectionStates']['archive']['state']='RELEASED'
        else:value['invocations'][0]['terminalPin']=None
        return value
    monkeypatch.setattr(admission,'_program_release_evidence',augmented)
    with pytest.raises(Exception):
        verify_no_mutation(h.e.owner,h.e.request,h.e.root,dict(resultPin=h.result_pin,exitPin=exited),receipt)
    assert calls==[True]


@pytest.mark.parametrize('fault',['phase','mutation','unknown','custody','step','missing-terminal'])
def test_consumer_never_accepts_unsafe_facts_after_real_validation(history_factory,monkeypatch,fault):
    """Conservative fault injection after the real validator, never a success stub."""
    h=prepared(history_factory);exited=child_exit(h,1);actual=admission._program_release_evidence;calls=[]
    def augmented(*args):
        proof=actual(*args);calls.append(True);value=deepcopy(proof)
        if fault=='phase':value['phase']='RESTORE'
        elif fault=='mutation':value['mutationDispatched']=True
        elif fault=='unknown':value['terminalUnknown']=True
        elif fault=='custody':value['protectionState']='FAILED_RETAINED'
        elif fault=='step':value['protectionStates']['scheduler']['state']='RELEASED'
        else:value['invocations'][0]['terminalPin']=None
        return value
    monkeypatch.setattr(admission,'_program_release_evidence',augmented)
    before=(admission.HOST_ROOT/'active.json').read_bytes()
    with pytest.raises(Exception):
        admission.release_no_mutation(h.e.owner,h.e.request,h.e.root,h.result_pin,exited)
    assert calls==[True] and (admission.HOST_ROOT/'active.json').read_bytes()==before
    assert not (h.e.root/'resource-no-mutation-release.json').exists()
