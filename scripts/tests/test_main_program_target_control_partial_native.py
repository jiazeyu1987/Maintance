"""FAILED target retry is explicit and cannot widen source authorization."""
from copy import deepcopy
import pytest
from test_main_program_target_control_successor import subject, canonical, pin, digest
from test_main_program_target_control_successor_repeat import unavailable_api_case


def retry_native_case():
    r,owner,context=unavailable_api_case();r['candidate']['schemaVersion']='MainProgramTargetControlSuccessorCandidate/v3'
    r['originalApi']={'errorCode':'RECOVERY_NO_MUTATION_NOT_PROVEN'}
    context['predecessorApiObservation'].update(httpStatus=500,api=deepcopy(r['originalApi']))
    request=__import__('json').loads(__import__('base64').b64decode(context['originalsPacket']['originals']['request']['rawBase64']))
    native=deepcopy(r['nativeBefore']);policy=owner['targetProgramPolicies'][r['targetConfigRef']]
    ready=deepcopy(native['epoch']);ready['eventPin']=pin(policy['backupEpochPolicy']['root']+'/00000000000000000000.json',b'ready')
    failed=dict(ready,state='FAILED_RETAINED',operationId=request['operationId'],epochId='a'*64,
        eventPin=pin(policy['backupEpochPolicy']['root']+'/00000000000000000002.json',b'failed'))
    auth=dict(schemaVersion='MainProgramRetainedRetryAuthorization/v1',predecessorOperationId=request['operationId'],
        sourceConfigRef=request['sourceConfigRef'],recoveryPointRef=request['recoveryPointRef'],targetConfigRef=request['targetConfigRef'],
        configurationPin=context['originalsPacket']['originals']['configuration']['pin'],
        requestPin=context['originalsPacket']['originals']['request']['pin'],
        resultPin=context['originalsPacket']['originals']['workerResult']['pin'],
        **{n:pin('/proof/'+n+'.json',n.encode()) for n in ('exitPin','replacementResultPin','contextPin','readyPin','noMutationReleasePin','observationPin')},
        clearancePin=context['clearanceResult']['clearancePin'],recoveryReleasePin=context['clearanceResult']['releasePin'],consumptionPin=None)
    targetpin=pin('/baseline/target.json',b'target')
    captures=policy.get('captureConfigurationPins',{'target-pre':pin('/baseline/capture.json',b'capture')})
    evidence=[failed['eventPin'],ready['eventPin'],targetpin,*captures.values(),*[p for n,p in auth.items() if n.endswith('Pin') and p is not None]]
    admission=dict(schemaVersion='MainProgramRetainedRetryAdmission/v1',state='FAILED_RETAINED_RETRY_ADMITTED',
        sourceConfigRef=request['sourceConfigRef'],targetConfigRef=request['targetConfigRef'],recoveryPointRef=request['recoveryPointRef'],
        predecessorOperationId=request['operationId'],epoch=failed,readyEpoch=ready,targetPin=targetpin,
        parentGenerationPin=None,capturePins=captures,authorization=auth,evidencePins=evidence,serverWrites=False)
    native.update(epoch=failed,directlyAdmittedSources=[request['sourceConfigRef']],retainedRetryAdmission=admission,
        rejectedSources={s:'PROGRAM_RETRY_SOURCE_NOT_AUTHORIZED' for s in subject().activated.activation.SOURCES if s!=request['sourceConfigRef']})
    r['nativeBefore']=native;r['nativeAfter']=deepcopy(native)
    for a in r['apiSelection']['applications']:
        a['freshTargetConfigRefs']=[r['targetConfigRef']] if a['sourceConfigRef']==request['sourceConfigRef'] else []
    return r,owner,context


def test_v3_retry_preserves_failed_epoch_and_only_authorized_source_selectable():
    r,owner,context=retry_native_case();before=deepcopy(r)
    subject()._verify_repeat_api(r,owner,owner,context)
    assert r==before and r['nativeBefore']['epoch']['state']=='FAILED_RETAINED'


@pytest.mark.parametrize('problem',['old_v2','fake_ready','epoch','missing_proof','consumed','source','point','operation',
    'clearance','request_pin','evidence','rejected_source','generic_error','unauthorized_api','authorized_api','unknown_native','no_retained_context'])
def test_retry_does_not_relax_old_or_new_gates(problem):
    r,o,c=retry_native_case();n=r['nativeBefore'];a=n['retainedRetryAdmission'];auth=a['authorization']
    if problem=='old_v2':r['candidate']['schemaVersion']='MainProgramTargetControlSuccessorCandidate/v2'
    elif problem=='fake_ready':n['epoch']['state']='READY'
    elif problem=='epoch':a['epoch']=deepcopy(a['epoch']);a['epoch']['eventPin']['sha256']='0'*64
    elif problem=='missing_proof':del n['retainedRetryAdmission']
    elif problem=='consumed':auth['consumptionPin']=pin('/used.json',b'used')
    elif problem in ('source','point','operation'):
        key={'source':'sourceConfigRef','point':'recoveryPointRef','operation':'predecessorOperationId'}[problem]
        a[key]=auth[key]='foreign'
    elif problem=='clearance':auth['clearancePin']=pin('/foreign.json',b'foreign')
    elif problem=='request_pin':auth['requestPin']=pin('/foreign.json',b'foreign')
    elif problem=='evidence':a['evidencePins']=[]
    elif problem=='rejected_source':n['rejectedSources'].pop(next(iter(n['rejectedSources'])))
    elif problem=='generic_error':n['rejectedSources']={s:'PROGRAM_RETRY_CLEARANCE_INVALID' for s in n['rejectedSources']}
    elif problem=='unauthorized_api':r['apiSelection']['applications'][1]['freshTargetConfigRefs']=[r['targetConfigRef']]
    elif problem=='authorized_api':r['apiSelection']['applications'][0]['freshTargetConfigRefs']=[]
    elif problem=='no_retained_context':
        r.update(beforeApiState='AVAILABLE',retainedFailureAdmission=None,originalApi=deepcopy(r['apiSelection']))
        for app in r['originalApi']['applications']:app['freshTargetConfigRefs']=[r['targetConfigRef']]
        c=None
    else:n['fallback']=True
    r['nativeAfter']=deepcopy(n)
    with pytest.raises(ValueError):subject()._verify_repeat_api(r,o,o,c)
