"""A verified single-host receipt is never a three-host activation."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from test_main_program_target_control_successor_repeat import (
    repeated_inputs,repeat_activation,construct,delta,repin_review,PROFILE_MEMBERS,payload,local_repeated_chain)
from test_main_program_target_control_successor import subject,canonical,localpin,pin,package_build,seal_successor

PARTIAL='TaskMainProgramTargetControlPartialPredecessor/v1'
MIXED='TaskMainProgramTargetControlSuccessorSelection/v3'


def partial_inputs(k):
    inputs=repeat_activation(k);inputs['activations']={'57':inputs['activations']['57']}
    return inputs


def test_partial_verifies_real_host_without_synthesizing_other_host_pass(repeated_inputs):
    m=subject();inputs=partial_inputs(repeated_inputs);before=deepcopy(inputs)
    result=m.verify_partial_target_predecessor(**inputs)
    assert inputs==before and result['status']=='PARTIALLY_ACTIVATED' and result['installationVerified'] is False
    assert result['activationVerifiedHosts']==['57'] and result['retainedBaseHosts']==['58','59']
    assert result['effectiveControllersByHost']['57'][-1]==inputs['activations']['57']['result']['currentController']
    for h in ('58','59'):
        assert result['effectiveControllersByHost'][h]==inputs['predecessor']['effectiveControllersByHost'][h]
        assert result['targetRuntimeSpecs'][h]==inputs['predecessor']['targetRuntimeSpecs'][h]
    assert result['sourceInstallation']==inputs['predecessor']['sourceInstallation']


@pytest.mark.parametrize('problem',['missing','other_host','extra_host','prepare','failed','pid','receipt','candidate','before','native','peer'])
def test_partial_runs_same_complete_host_validator(repeated_inputs,problem):
    k=partial_inputs(repeated_inputs);w=k['activations']['57'];r=w['result']
    if problem=='missing':k['activations']={}
    elif problem=='other_host':k['activations']={'58':w}
    elif problem=='extra_host':k['activations']['58']=deepcopy(w)
    elif problem=='prepare':w['mode']='PREPARE'
    elif problem=='failed':r['status']='FAILED'
    elif problem=='pid':r['currentController']['pid']+=1
    elif problem=='receipt':r['activationReceiptPin']['sha256']='0'*64
    elif problem=='candidate':r['candidate']['newDocuments'][0]['value']['extra']=True
    elif problem=='before':r['before']['mountinfoSha256']='0'*64
    elif problem=='native':r['nativeAfter']['epoch']['state']='FAILED_RETAINED'
    else:r['after']['controllers'][0]['pid']+=1
    if problem!='receipt':seal_successor(w)
    with pytest.raises(ValueError):subject().verify_partial_target_predecessor(**k)


def test_partial_loader_and_v3_loader_are_explicit_entrypoints():
    assert callable(getattr(subject(),'load_partial_target_predecessor',None))
    assert callable(getattr(subject(),'load_mixed_target_successor_installation',None))


def test_current_installation_never_dispatches_partial_as_complete(tmp_path):
    import main_program_current_installation as current
    (tmp_path/'partial.json').write_bytes(canonical(dict(schemaVersion=PARTIAL)))
    with pytest.raises(ValueError,match='TARGET_SELECTION_SCHEMA'):
        current.load_current_target_installation(tmp_path,tmp_path,selection_file='partial.json')


@pytest.fixture
def local_partial(local_repeated_chain):
    k=local_repeated_chain;task=k['task'];e=json.loads((task/'selection-e.json').read_text(encoding='utf-8'))
    selected={key:deepcopy(e[key]) for key in ('buildPin','standardPackagePin','packageDeltaReviewPin')}
    selected.update(schemaVersion=PARTIAL,baseSelectionPin=e['predecessorSelectionPin'],
        targetActivationEvidencePins={'57':e['targetActivationEvidencePins']['57']})
    (task/'partial.json').write_bytes(canonical(selected))
    return dict(**k,partial=selected)


def test_partial_loader_verifies_actual_57_file_and_keeps_unactivated_hosts(local_partial):
    k=local_partial;result=subject().load_partial_target_predecessor(k['task'],k['private'],selection_file='partial.json')
    assert result['status']=='PARTIALLY_ACTIVATED' and result['installationVerified'] is False
    assert result['controllerBuildBindings']['57']['target']['sourceCommit']=='e'*40
    assert result['controllerBuildBindings']['58']['target']['sourceCommit'].startswith('b9caa00')
    assert result['targetPredecessorArtifactsByHost']['57']['buildPin']==k['partial']['buildPin']
    assert result['targetPredecessorArtifactsByHost']['58']['buildPin']==result['predecessorInstallation']['selection']['buildPin']
    assert 'activation-e-58.json' not in {Path(p['path']).name for p in result['inputPins']}


@pytest.mark.parametrize('problem',['activation','carrier','package','review','partial_unknown','partial_hosts'])
def test_partial_loader_rejects_each_unverified_local_original(local_partial,problem):
    k=local_partial;task=k['task'];private=k['private']
    if problem.startswith('partial'):
        value=deepcopy(k['partial'])
        if problem=='partial_unknown':value['unverified']=True
        else:value['targetActivationEvidencePins']['58']=value['targetActivationEvidencePins']['57']
        (task/'partial.json').write_bytes(canonical(value))
    else:
        file={'activation':private/'activation-e-57.json','carrier':private/'carrier-e-57.py',
            'package':private/'package-e.tgz','review':task/'review-eeeeeee.json'}[problem]
        file.write_bytes(file.read_bytes()+b' ')
    with pytest.raises(ValueError):subject().load_partial_target_predecessor(task,private,selection_file='partial.json')


def mixed_candidate_inputs(local_partial,host):
    k=local_partial;m=subject();prior=m.load_partial_target_predecessor(k['task'],k['private'],selection_file='partial.json')
    artifact=prior['targetPredecessorArtifactsByHost'][host]
    oldraw=Path(artifact['standardPackagePin']['path']).read_bytes();oldbuild=json.loads((k['task']/artifact['buildPin']['file']).read_bytes())
    files=payload(oldraw)
    for member in PROFILE_MEMBERS:files[member]+=b'\nCOMMON_NEW_GENERATION=True\n'
    build,raw,_=package_build(files,'9'*40);buildpin=localpin('mixed-build.json',build)
    inputs=dict(predecessor=prior,predecessor_selection_pin=prior['selectionPin'],predecessor_selection_raw=(k['task']/'partial.json').read_bytes(),
        predecessor_build=oldbuild,predecessor_build_raw=canonical(oldbuild),predecessor_package_raw=oldraw,build=build,build_pin=buildpin,
        build_raw=canonical(build),package_raw=raw,host=host,preservation_documents=prior['currentPreservationDocumentsByHost'][host],
        configuration_root='/control/configuration/main-target-9999999-r1',new_engine='/control/engine-main-program-9999999',
        retained_failure_pins=prior['retainedFailurePinsByHost'][host])
    review=delta(inputs);review['predecessorBuildPin']=artifact['buildPin'];review['previousPackagePin']=artifact['standardPackagePin']
    inputs['package_delta_review']=review;repin_review(inputs)
    return inputs


@pytest.mark.parametrize('host',['57','58','59'])
def test_candidate_binds_each_actual_partial_predecessor_artifact(local_partial,host):
    inputs=mixed_candidate_inputs(local_partial,host);candidate=construct(inputs)
    assert candidate['previousController']['sourceCommit']==('e'*40 if host=='57' else inputs['predecessor_build']['targetCommit'])
    assert candidate['predecessorBuildPin']==inputs['predecessor']['targetPredecessorArtifactsByHost'][host]['buildPin']


@pytest.mark.parametrize('problem',['wrong_host_build','wrong_host_package','wrong_role_binding','pretend_complete'])
def test_partial_predecessor_cannot_lie_about_old_host_version(local_partial,problem):
    inputs=mixed_candidate_inputs(local_partial,'57');prior=inputs['predecessor']
    if problem=='wrong_host_build':inputs['predecessor_build_raw']=canonical(json.loads((local_partial['task']/prior['targetPredecessorArtifactsByHost']['58']['buildPin']['file']).read_bytes()))
    elif problem=='wrong_host_package':inputs['predecessor_package_raw']=Path(prior['targetPredecessorArtifactsByHost']['58']['standardPackagePin']['path']).read_bytes()
    elif problem=='wrong_role_binding':prior['controllerBuildBindings']['57']['target']=deepcopy(prior['controllerBuildBindings']['58']['target'])
    else:prior['status']='ACTIVATED';prior['installationVerified']=True
    with pytest.raises(ValueError):construct(inputs)
