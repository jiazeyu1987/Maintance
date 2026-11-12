from copy import deepcopy
import pytest
from test_main_program_target_control_partial_native import retry_native_case
from test_main_program_target_control_successor import subject


def available_case():
    r,owner,_=retry_native_case()
    r.update(beforeApiState='AVAILABLE',retainedFailureAdmission=None,originalApi=deepcopy(r['apiSelection']))
    r['candidate']['previousPackage']={'fileCount':154}
    return r,owner,deepcopy(r['nativeBefore'])


def test_authenticated_available_58_retry_is_unchanged_across_next_component_upgrade():
    r,owner,prior=available_case();before=deepcopy(r)
    subject()._verify_repeat_api(r,owner,owner,None,predecessor_retry_native=prior)
    assert r==before and r['nativeBefore']['epoch']['state']=='FAILED_RETAINED'


@pytest.mark.parametrize('problem',['missing','native','old_count','host','source','before_api','after_api','context','admission','old_schema','ready'])
def test_available_retry_requires_the_same_authenticated_predecessor_and_source(problem):
    r,owner,prior=available_case();context=None
    if problem=='missing':prior=None
    elif problem=='native':prior['actualConfigurationReadPassed']=False
    elif problem=='old_count':r['candidate']['previousPackage']['fileCount']=153
    elif problem=='host':r['host']='172.30.30.57'
    elif problem=='source':prior['directlyAdmittedSources']=['foreign']
    elif problem=='before_api':r['originalApi']['applications'][1]['freshTargetConfigRefs']=[r['targetConfigRef']]
    elif problem=='after_api':r['apiSelection']['applications'][1]['freshTargetConfigRefs']=[r['targetConfigRef']]
    elif problem=='context':context={}
    elif problem=='admission':r['retainedFailureAdmission']={}
    elif problem=='old_schema':r['candidate']['schemaVersion']='MainProgramTargetControlSuccessorCandidate/v2'
    else:r['nativeBefore']['epoch']['state']='READY';r['nativeAfter']=deepcopy(r['nativeBefore'])
    with pytest.raises(ValueError):subject()._verify_repeat_api(r,owner,owner,context,predecessor_retry_native=prior)


def test_default_api_does_not_infer_retained_retry_authority():
    r,owner,_=available_case()
    with pytest.raises(ValueError,match='RETRY_RETAINED_FAILURE_REQUIRED'):
        subject()._verify_repeat_api(r,owner,owner,None)
