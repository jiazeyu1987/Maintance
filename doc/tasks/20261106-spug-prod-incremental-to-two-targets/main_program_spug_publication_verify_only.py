"""Verify the completed c1 writes without republishing any configuration.

The historical failures remain immutable. Default preparation is local only.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation
import spug_runtime_dependency_completion as dependency

TASK,PRIVATE=publication.TASK,publication.PRIVATE
INPUT_SCHEMA='MainProgramSpugPublicationVerificationInputs/v1'
EVIDENCE_SCHEMA='MainProgramSpugPublicationVerification/v1'


def need(value,code):
    if not value:raise ValueError('MAIN_SPUG_VERIFICATION_'+code)


def unique_pins(pins):
    result={}
    for pin in pins:
        need(pin['path'] not in result or result[pin['path']]==pin,'INPUT_CONFLICT')
        result[pin['path']]=pin
    return list(result.values())


def schedule():
    return ['spug-guard-before','host-verify-57','host-verify-58','host-verify-59','spug-verify','spug-guard-after']


def verify_historical_inputs(private,originals,mappings,pins):
    need(type(originals) is list and len({p['path'] for p in originals})==len(originals),'ORIGINAL_INPUT_SET_INVALID')
    indexed={p['path']:p for p in originals}
    need(all(key in indexed and row['originalPin']==indexed[key] for key,row in mappings.items()),'HISTORICAL_MAPPING_NOT_REFERENCED')
    for old in originals:
        if old['path'] in mappings:
            row=mappings[old['path']];raw=continuation.private_raw(private,row['preservedPin'],pins)
            need(len(raw)==old['bytes'] and hashlib.sha256(raw).hexdigest()==old['sha256'],'HISTORICAL_BYTES_CHANGED')
        else:publication.verify_bytes(old);pins.append(old)


def validate_inspect(prepared,request,result):
    original=prepared['c1'];mount=original['mountObservation']
    need(request['argv']==[publication.DOCKER,'inspect',publication.CONTAINER,mount['protectedContainerId']] and
         request['stdinPin'] is None,'INSPECT_COMMAND_CHANGED')
    continuation.verify_instances(result,mount)
    chosen=[row for row in result if row['Id']==publication.CONTAINER]
    need(len(chosen)==1,'INSPECT_CONTAINER_CHANGED')
    actual=[m for m in continuation.mount_rows(chosen[0]['Mounts']) if m['Destination'] in
            (continuation.RUN_ROOT,'/opt/intruoyi-spug',continuation.VOLUME_ROOT)]
    need(sorted(actual,key=lambda r:r['Destination'])==sorted(mount['mounts'],key=lambda r:r['Destination']),'INSPECT_MOUNTS_CHANGED')


def validate_native_command(private,native,argv,program,output,pins,*,timeout):
    receipt,request,result=native
    need(request['argv']==argv and request['timeoutSeconds']==timeout and request['stdinPin'] is not None and
         continuation.private_raw(private,request['stdinPin'],pins)==program.encode('utf-8') and result==output,
         'NATIVE_COMMAND_CHANGED')
    # Historical native contract retains diagnostics; exit and complete stdout
    # determine its result. Do not retroactively require an empty warning stream.
    continuation.private_raw(private,receipt['stderrPin'],pins)


def load_completed_dependency_activation(records,private,reference,c1,failure,source_custody,*,historical=None):
    """Read the real A seven-stage / fifteen-native proof, never A's pre-install gate."""
    pins=[];core=records.pinned(reference)
    need(core.get('schemaVersion')=='MainProgramSpugRuntimeDependencyActivation/v1' and core.get('status')=='PASS' and
         core.get('replacementState')=='APPLIED' and core.get('continuationFailurePin')==
         c1_failure_pin(private,c1) and core.get('baseResourceActivationPin')==c1['inputs']['resourceActivationPin'],
         'DEPENDENCY_ACTIVATION_REQUIRED')
    rich=continuation.private_json(private,core['privateEvidencePin'],pins)
    expected_core={k:v for k,v in rich.items() if k not in ('inputPins','nativeReceiptPins','stagePins','errorCode','errorType')}
    expected_core.update(privateEvidencePin=core['privateEvidencePin'],baseResourceActivationPin=c1['inputs']['resourceActivationPin'])
    need(core==expected_core and all(core.get(k) is False for k in
         ('configurationWrites','backupDispatched','restoreDispatched','retryPermitted','liveUiVerified')) and
         all(core.get(k) is True for k in ('entryReloaded','freshProcessConfigurationParsed','historicalFingerprintsUnchanged',
             'oldThirteenResourcesUnchanged','sevenConfigurationsUnchanged','originalC1EvidencePreserved','protectedSpugUnchanged')),
         'DEPENDENCY_CORE_CHANGED')
    inputs=records.pinned(core['activationInputsPin'])
    need(inputs['dependencyCompletionPin']==core['dependencyCompletionPin'] and inputs['sourceCommit']==core['sourceCommit'] and
         inputs['continuationInputsPin']==c1['inputPin'] and inputs['continuationFailurePin']==core['continuationFailurePin'] and
         inputs['baseResourceActivationPin']==core['baseResourceActivationPin'] and inputs['operationId']==core['operationId'] and
         inputs['outputFile']==reference['file'],'DEPENDENCY_INPUT_BINDING_CHANGED')
    completion,base,kept=dependency.validate_dependency_completion(records,private,core['dependencyCompletionPin'],verify_checkout=False)
    pins+=kept
    need(completion['baseResourceBuildPin']==c1['inputs']['spugResourceBuildPin'] and completion['sourceCommit']==core['sourceCommit'],
         'DEPENDENCY_RESOURCE_CHANGED')
    custody=continuation.private_json(private,completion['sourceCustodyPin'],pins)
    attempt=continuation.private_json(private,core['attemptPin'],pins)
    binding={k:core[k] for k in ('activationInputsPin','sourceCommit','operationId','dependencyCompletionPin','continuationFailurePin')}
    need(set(attempt)=={'schemaVersion',*binding,'inputPins','gatePin','retryPermitted'} and
         attempt['schemaVersion']=='MainProgramSpugRuntimeDependencyAttempt/v1' and attempt['retryPermitted'] is False and
         all(attempt[k]==v for k,v in binding.items()) and source_custody['dependencyAttemptPin']==core['attemptPin'],
         'DEPENDENCY_ATTEMPT_CHANGED')
    gate=continuation.private_json(private,attempt['gatePin'],pins)
    need(gate==dict(**binding,retryPermitted=False),'DEPENDENCY_GATE_CHANGED')
    mapping={r['originalPin']['path']:r for r in custody['entries']}
    old=source_custody['entries'][0];need(old['originalPin']['path'] not in mapping,'SOURCE_CUSTODY_OVERLAP')
    mapping[old['originalPin']['path']]=old
    if historical is None:verify_historical_inputs(private,attempt['inputPins'],mapping,pins)
    else:historical.verify_inputs('dependency',core['attemptPin'],attempt['inputPins'],mapping,pins)
    runtime=dependency.validate_runtime_observation(private,records.pinned(inputs['runtimeObservationPin']),c1,
                                                    core['continuationFailurePin'],pins)
    runner=records.pinned(inputs['runnerExitObservationPin'])
    need(runner['completionPin']==inputs['continuationCompletionPin'],'C1_RUNNER_COMPLETION_CHANGED')
    dependency.validate_runner_exit(private,runner,c1,pins)
    old_observation=continuation.private_json(private,c1['resourceInstallation']['observationPin'],pins)
    previous=core['replacement']['previousPin'];continuation.private_raw(private,previous,pins)
    target=str(Path(publication.RUNTIME)/'smallapp_simple.py')
    prepared=dict(c1=c1,failure=failure,completion=completion,runtime=runtime,oldObservation=old_observation,
                  change=dict(beforePin=dict(path=target,bytes=previous['bytes'],sha256=previous['sha256'])))
    stages=rich['stagePins'];names=['before','before-write','replacement-dispatched','installed','replacement-applied','reload','after']
    need(type(stages) is list and all(set(r)=={'stage','pin'} for r in stages) and [r['stage'] for r in stages]==names and
         len({r['pin']['path'] for r in stages})==7,'DEPENDENCY_STAGE_SET_CHANGED')
    stage={r['stage']:continuation.private_json(private,r['pin'],pins) for r in stages}
    identity=core['entryBefore'];new=core['entryAfter'];environment=core['entryEnvironmentSha256']
    dependency.validate_reload_identity(identity,new)
    for name,phase,expected in [('before','before',None),('before-write','before',identity),
                                ('installed','installed',identity),('after','after',new)]:
        dependency.validate_runtime_result(prepared,stage[name],phase,expected,None if name=='before' else environment)
    need(stage['before']['entryIdentity']==identity and stage['before']['entryEnvironmentSha256']==environment and
         stage['reload']==new and core['filePinsBefore']==stage['before']['filePins'] and
         core['filePinsAfter']==stage['after']['filePins'] and core['configurationPins']==stage['after']['configurationPins'],
         'DEPENDENCY_RUNTIME_SUMMARY_CHANGED')
    need(stage['replacement-dispatched']==dict(state='DISPATCHED_OUTCOME_UNKNOWN',path=target) and
         stage['replacement-applied']==core['replacement'],'DEPENDENCY_TRANSITION_CHANGED')
    installed=next(p for p in core['filePinsAfter'] if p['path']=='/opt/intruoyi-spug/smallapp_simple.py')
    oldpin=next(p for p in core['filePinsBefore'] if p['path']==installed['path'])
    need(all(previous[k]==oldpin[k] for k in ('bytes','sha256')) and core['replacement']['containerReadbackPin']==installed and
         core['replacement']['transition']==dict(atomicMoveCompleted=True,fileFsyncCompleted=True,
             installedPin=dict(path=target,bytes=installed['bytes'],sha256=installed['sha256']),powerLossDurabilityVerified=False),
         'DEPENDENCY_REPLACEMENT_CHANGED')
    native=continuation.validate_native_receipts(private,rich['nativeReceiptPins'],pins)
    need([v['label'] for v,q,o in native]==['inspect','before','inspect','inspect','before','inspect',
         'inspect','installed','inspect','inspect','reload','inspect','inspect','after','inspect'],'DEPENDENCY_NATIVE_SET_CHANGED')
    # The original reload builder used repr(dict), so preserve the native JSON's
    # insertion order, not the canonical stage/core object's sorted key order.
    generated_identity=native[1][2]['entryIdentity'];need(generated_identity==identity,'DEPENDENCY_NATIVE_IDENTITY_CHANGED')
    commands=[('before',dependency.runtime_program(prepared,'before')),('before-write',dependency.runtime_program(prepared,'before',identity,environment)),
              ('installed',dependency.runtime_program(prepared,'installed',identity,environment)),
              ('reload',dependency.reload_program(prepared,generated_identity,environment)),('after',dependency.runtime_program(prepared,'after',new,environment))]
    nonce='spug-dependency-'+core['sourceCommit'][:7]+'-'+core['operationId']
    argv=[publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-',nonce]
    for index,(name,program) in enumerate(commands):
        for offset in (0,2):
            receipt,request,result=native[index*3+offset];validate_inspect(prepared,request,result)
            need(continuation.private_raw(private,receipt['stderrPin'],pins)==b'','DEPENDENCY_INSPECT_STDERR')
        validate_native_command(private,native[index*3+1],argv,program,stage[name],pins,timeout=120)
    return dict(core=core,rich=rich,attempt=attempt,inputs=inputs,prepared=prepared,inputPins=unique_pins(pins),
                nativeDiagnosticPins=[v['stderrPin'] for v,q,o in native if v['stderrPin']['bytes']])


def c1_failure_pin(private,c1):
    return publication.file_pin(Path(private)/(c1['inputs']['outputFile'][:-5]+'.private.json'))


def prepare_value(records,private,inputs,input_pin,*,historical=None):
    if type(inputs) is dict and inputs.get('schemaVersion')=='MainProgramSpugPublicationVerificationInputs/v2':
        need(set(inputs)=={'schemaVersion','baseVerificationInputsPin','resourceTransitionPin','verificationId','outputFile'} and
             type(inputs['verificationId']) is str and re.fullmatch('v[1-9][0-9]*',inputs['verificationId']),'INPUTS_INVALID')
        base_inputs=records.pinned(inputs['baseVerificationInputsPin'])
        need(base_inputs.get('schemaVersion')==INPUT_SCHEMA,'BASE_VERIFICATION_V1_REQUIRED')
        base=prepare_value(records,private,base_inputs,inputs['baseVerificationInputsPin'],historical=historical)
        return prepare_transition_verification(records,private,inputs,input_pin,base,historical=historical)
    fields={'schemaVersion','sourceCommit','revisionId','controlGenerationPin','continuationInputsPin','continuationAttemptPin',
            'continuationFailurePin','continuationCompletionPin','dependencyActivationPin','historicalSourceCustodyPin','verificationId','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and inputs['schemaVersion']==INPUT_SCHEMA and
         type(inputs['verificationId']) is str and re.fullmatch('v[1-9][0-9]*',inputs['verificationId']),
         'INPUTS_INVALID')
    c1inputs=records.pinned(inputs['continuationInputsPin'])
    need(all(inputs[k]==c1inputs[k] for k in ('sourceCommit','revisionId','controlGenerationPin')) and
         inputs['outputFile']==c1inputs['outputFile'][:-5]+'-verification-'+inputs['verificationId']+'.json','GENERATION_OR_OUTPUT_CHANGED')
    c1=continuation.prepare_value(records,Path(private),c1inputs,inputs['continuationInputsPin'],historical=historical);pins=[]
    need(inputs['continuationFailurePin']==c1_failure_pin(private,c1),'C1_FAILURE_FILE_CHANGED')
    failure=continuation.private_json(private,inputs['continuationFailurePin'],pins)
    need(failure['attemptPin']==inputs['continuationAttemptPin'],'C1_ATTEMPT_CHANGED')
    custody=records.pinned(inputs['historicalSourceCustodyPin'])
    prefix=dependency.validate_failed_continuation(c1,private,failure,pins,historical_source_custody=custody,historical=historical)
    completed=load_completed_dependency_activation(records,private,inputs['dependencyActivationPin'],c1,failure,custody,historical=historical)
    need(completed['inputs']['continuationCompletionPin']==inputs['continuationCompletionPin'],'C1_COMPLETION_CHANGED')
    spec=deepcopy(c1['originalSpec']);spec['spugSpec']['observation']['entryPid']=completed['core']['entryAfter']['pid']
    expected=deepcopy(c1['originalSpec']);expected['spugSpec']['observation']['entryPid']=completed['core']['entryAfter']['pid']
    need(spec==expected,'VERIFICATION_SPEC_CHANGED')
    pins+=completed['inputPins']+c1['inputPins']+records.path_pins()
    pins+=[publication.file_pin(p) for p in (__file__,dependency.__file__,contract.__file__)]
    return dict(inputs=inputs,inputPin=input_pin,c1=c1,failure=failure,prefix=prefix,dependency=completed,
                spec=spec,inputPins=unique_pins(pins))


def apply_transition_view(base,completed):
    from main_program_spug_resource_transition import runtime_view
    value=deepcopy(base);identity=completed['entryAfter'];files=completed['afterFiles']
    products=[dict(path='/opt/intruoyi-spug/'+name,**files[name]) for name in publication.PRODUCT_FILES]
    value['spec']['spugSpec']['observation']['entryPid']=identity['pid']
    value['spec']['spugSpec']['observation']['productPins']=deepcopy(products)
    context=deepcopy(base['c1']['context'])
    context['resource']['files']={'ops/spug/'+name:deepcopy(files[name]) for name in publication.PRODUCT_FILES}
    context['observation']['spug']['productPins']=deepcopy(products)
    value['verificationContext']=context
    value['runtimeView']=runtime_view(base,files,identity,completed['entryEnvironmentSha256'])
    value['resourceTransition']=deepcopy(completed)
    return value


def prepare_transition_verification(records,private,inputs,input_pin,base,*,historical=None):
    """Consume a fully read A/c1 baseline and an actual transition closure."""
    from main_program_spug_resource_transition import load_completed_transition
    need(type(inputs) is dict and set(inputs)=={'schemaVersion','baseVerificationInputsPin','resourceTransitionPin','verificationId','outputFile'} and
         inputs['schemaVersion']=='MainProgramSpugPublicationVerificationInputs/v2' and
         type(inputs['verificationId']) is str and re.fullmatch('v[1-9][0-9]*',inputs['verificationId']),'INPUTS_INVALID')
    base_inputs=records.pinned(inputs['baseVerificationInputsPin'])
    need(base_inputs==base['inputs'] and base['inputPin']==inputs['baseVerificationInputsPin'] and
         base_inputs['schemaVersion']==INPUT_SCHEMA,'BASE_VERIFICATION_CHANGED')
    expected=base_inputs['outputFile'].rsplit('-verification-',1)[0]+'-verification-'+inputs['verificationId']+'.json'
    need(inputs['outputFile']==expected and inputs['outputFile']!=base_inputs['outputFile'],'OUTPUT_CHANGED')
    completed=load_completed_transition(records,private,inputs['resourceTransitionPin'],base,historical=historical)
    value=apply_transition_view(base,completed)
    value['inputs']=dict(base_inputs,schemaVersion=inputs['schemaVersion'],verificationId=inputs['verificationId'],
        outputFile=inputs['outputFile'],baseVerificationInputsPin=inputs['baseVerificationInputsPin'],resourceTransitionPin=inputs['resourceTransitionPin'])
    value['inputPin']=input_pin
    value['inputPins']=unique_pins(base['inputPins']+completed['inputPins']+records.path_pins())
    return value


def prepare_verification(task,private,inputs_file):
    records=contract.Records(task);value=records.read(inputs_file)
    return prepare_value(records,Path(private),value,records.references[inputs_file])


def stage_program(prepared,stage):
    need(stage in schedule(),'STAGE_NOT_ALLOWED')
    if stage in ('spug-guard-before','spug-guard-after'):
        if 'resourceTransition' in prepared:
            completed=prepared['resourceTransition']
            return dependency.runtime_program(prepared['runtimeView'],'after',completed['entryAfter'],completed['entryEnvironmentSha256'])
        completed=prepared['dependency'];core=completed['core']
        return dependency.runtime_program(completed['prepared'],'after',core['entryAfter'],core['entryEnvironmentSha256'])
    if stage.startswith('host-verify-'):
        host=stage.rsplit('-',1)[1]
        return continuation.original.program('host',host,'verify',prepared['spec']['hostSpecs'][host])
    return continuation.original.program('spug',None,'verify',prepared['spec']['spugSpec'])


def command_arguments(prepared,stage):
    need(stage in schedule(),'STAGE_NOT_ALLOWED')
    if stage.startswith('host-verify-'):return prepared['c1']['hostCommands'][stage.rsplit('-',1)[1]],600
    nonce='spug-verification-'+prepared['inputs']['continuationFailurePin']['sha256'][:24]
    timeout=120
    if stage=='spug-verify' and 'resourceTransition' in prepared:
        budget=prepared['resourceTransition']['selectionReadBudgetSeconds']
        need(type(budget) is int and 1<=budget<=60,'READ_BUDGET_INVALID')
        timeout=len(contract.HOSTS)*len(publication.SOURCES)*budget+120
    return [publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-',nonce],timeout


def validate_stage_result(prepared,stage,result):
    need(stage in schedule() and type(result) is dict and result.get('status')=='PASS','STAGE_NOT_SUCCESSFUL')
    if stage.startswith('spug-guard-'):
        if 'resourceTransition' in prepared:
            completed=prepared['resourceTransition']
            dependency.validate_runtime_result(prepared['runtimeView'],result,'after',completed['entryAfter'],completed['entryEnvironmentSha256'])
        else:
            completed=prepared['dependency'];core=completed['core']
            dependency.validate_runtime_result(completed['prepared'],result,'after',core['entryAfter'],core['entryEnvironmentSha256'])
    else:
        need(result.get('phase')=='verify' and result.get('sourceCommit')==prepared['inputs']['sourceCommit'] and
             result.get('backupDispatched') is False and result.get('restoreDispatched') is False,'VERIFY_RESULT_CHANGED')
        host=stage.rsplit('-',1)[1] if stage.startswith('host-verify-') else None
        context=prepared.get('verificationContext',prepared['c1']['context'])
        publication.validate_verify_stage(context,context['generation'],host,result)
    return result


class VerificationTransport:
    """Only exact inspect, guard and verify commands. No configuration writer."""
    def __init__(self,private,prepared):
        context=deepcopy(prepared['c1']);context['inputs']['outputFile']=prepared['inputs']['outputFile']
        self._recorder=continuation.ActualContinuationTransport(private,context);self.prepared=prepared
    @property
    def receipts(self):return self._recorder.receipts
    def execute(self,stage):
        program=stage_program(self.prepared,stage);argv,timeout=command_arguments(self.prepared,stage)
        is_host=stage.startswith('host-verify-')
        if not is_host:self._recorder.inspect_current()
        result=self._recorder.command(stage,argv,program,timeout)
        if not is_host:
            self._recorder.inspect_current()
            if stage=='spug-verify':result['protectedSpugUnchanged']=True
        return validate_stage_result(self.prepared,stage,result)


def binding(prepared):
    inputs=prepared['inputs']
    value=dict(verificationInputsPin=prepared['inputPin'],**{k:inputs[k] for k in
        ('sourceCommit','revisionId','controlGenerationPin','continuationFailurePin','dependencyActivationPin','verificationId')})
    if 'resourceTransition' in prepared:value['resourceTransitionPin']=inputs['resourceTransitionPin']
    return value


def aggregate(prepared,stages):
    need([r.get('stage') for r in stages]==schedule(),'STAGE_SET_INCOMPLETE')
    for row in stages:validate_stage_result(prepared,row['stage'],row['result'])
    hosts=[r['result'] for r in stages[1:4]];spug=stages[4]['result']
    return dict(status='PASS',sourceCommit=prepared['inputs']['sourceCommit'],publicationCompleted=True,
        selectorCount=sum(r['selectorCount'] for r in hosts),applicationCount=spug['applicationCount'],taskCount=spug['taskCount'],
        backupDispatched=False,restoreDispatched=False,
        **{key:all(r.get(key) is True for r in hosts) for key in ('selectorsReadBack','actualNativeSelectionsVerified',
            'businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')},
        **{key:spug[key] for key in ('productSettingsReadBack','historicalFingerprintsUnchanged',
            'protectedSpugUnchanged','oldTasksUnchanged','productFilesUnchanged')},
        oldFilesPreserved=all(r['oldFilesPreserved'] is True for r in hosts) and spug['oldFilesPreserved'] is True)


def validate_stage_native(prepared,private,stage,native_references,result,pins):
    native=continuation.validate_native_receipts(private,native_references,pins)
    is_host=stage.startswith('host-verify-');labels=[v['label'] for v,q,o in native]
    need(labels==([stage] if is_host else ['inspect',stage,'inspect']),'VERIFY_NATIVE_SET_CHANGED')
    if not is_host:
        for value,request,output in (native[0],native[2]):
            validate_inspect(prepared['dependency']['prepared'],request,output)
            need(continuation.private_raw(private,value['stderrPin'],pins)==b'','INSPECT_STDERR')
    command=native[0 if is_host else 1];output=deepcopy(command[2])
    if stage=='spug-verify':output['protectedSpugUnchanged']=True
    need(output==result,'VERIFY_NATIVE_RESULT_CHANGED')
    argv,timeout=command_arguments(prepared,stage)
    validate_native_command(private,command,argv,stage_program(prepared,stage),command[2],pins,timeout=timeout)
    return [v['stderrPin'] for v,q,o in native if v['stderrPin']['bytes']]


EFFECTS=dict(configurationWrites=False,businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)


def validate_publication_v4(records,private,selected,*,historical=None):
    need(type(selected) is dict and set(selected)=={'schemaVersion','sourceCommit','controlGenerationPin','spugInstallationPin','verificationInputsPin'} and
         selected['schemaVersion']=='TaskMainProgramInstallations/v4','SELECTION_INVALID')
    inputs=records.pinned(selected['verificationInputsPin'])
    prepared=prepare_value(records,private,inputs,selected['verificationInputsPin'],historical=historical);bound=binding(prepared);pins=[]
    inputs=prepared['inputs']
    need(selected['sourceCommit']==inputs['sourceCommit'] and selected['controlGenerationPin']==inputs['controlGenerationPin'] and
         selected['spugInstallationPin']['file']==inputs['outputFile'],'SELECTION_BINDING_CHANGED')
    core=records.pinned(selected['spugInstallationPin']);stem=inputs['outputFile'][:-5]
    rich_pin=publication.file_pin(Path(private)/(stem+'.private.json'));rich=continuation.private_json(private,rich_pin,pins)
    aggregate_fields={'status','sourceCommit','publicationCompleted','selectorCount','applicationCount','taskCount',
                      'backupDispatched','restoreDispatched',*publication.TRUE_CHECKS}
    need(set(rich)=={'schemaVersion',*aggregate_fields,*bound,'stage','attemptPin','stages','originalStages',
         'originalFailedStagePin','nativeDiagnosticPins',*EFFECTS} and rich['schemaVersion']==EVIDENCE_SCHEMA and
         rich['stage']=='complete' and all(rich[k]==v for k,v in bound.items()) and all(rich[k]==v for k,v in EFFECTS.items()),
         'EVIDENCE_INVALID')
    attempt=continuation.private_json(private,rich['attemptPin'],pins)
    need(set(attempt)=={'schemaVersion',*bound,'inputPins','stageOrder','gatePin','claimPin','retryPermitted'} and
         attempt['schemaVersion']=='MainProgramSpugVerificationAttempt/v1' and attempt['stageOrder']==schedule() and
         attempt['retryPermitted'] is False and all(attempt[k]==v for k,v in bound.items()),'ATTEMPT_INVALID')
    if historical is None:
        for reference in attempt['inputPins']:publication.verify_bytes(reference);pins.append(reference)
    else:historical.verify_inputs('verification',rich['attemptPin'],attempt['inputPins'],{},pins)
    gate=continuation.private_json(private,attempt['gatePin'],pins)
    need(gate==dict(**bound,automaticRetryPermitted=False),'GATE_CHANGED')
    claim=continuation.private_json(private,attempt['claimPin'],pins)
    need(claim==dict(**bound,gatePin=attempt['gatePin']),'CLAIM_CHANGED')
    need(rich['originalStages']==prepared['failure']['stages'][:6] and
         rich['originalFailedStagePin']==prepared['failure']['stages'][6]['resultPin'],'ORIGINAL_STAGE_BINDING_CHANGED')
    need(type(rich['stages']) is list and len(rich['stages'])==6 and
         all(set(r)=={'stage','resultPin'} for r in rich['stages']) and [r['stage'] for r in rich['stages']]==schedule() and
         len({r['resultPin']['path'] for r in rich['stages']})==6,'STAGE_SET_INCOMPLETE')
    stages=[];diagnostics=[]
    for row in rich['stages']:
        raw=continuation.private_json(private,row['resultPin'],pins)
        need(set(raw)=={'schemaVersion',*bound,'stage','requestPin','result','nativeReceiptPins'} and
             raw['schemaVersion']=='MainProgramSpugVerificationStage/v1' and raw['stage']==row['stage'] and
             all(raw[k]==v for k,v in bound.items()),'STAGE_BINDING_CHANGED')
        request=continuation.private_json(private,raw['requestPin'],pins)
        need(set(request)=={'schemaVersion',*bound,'stage','programPin','retryPermitted'} and
             request['schemaVersion']=='MainProgramSpugVerificationDispatch/v1' and request['stage']==row['stage'] and
             request['retryPermitted'] is False and all(request[k]==v for k,v in bound.items()) and
             continuation.private_raw(private,request['programPin'],pins)==stage_program(prepared,row['stage']).encode(),'DISPATCH_CHANGED')
        validate_stage_result(prepared,row['stage'],raw['result'])
        diagnostics+=validate_stage_native(prepared,private,row['stage'],raw['nativeReceiptPins'],raw['result'],pins)
        stages.append(dict(stage=row['stage'],result=raw['result']))
    observed=aggregate(prepared,stages)
    need(all(rich[k]==v for k,v in observed.items()) and rich['nativeDiagnosticPins']==diagnostics and
         core==publication.project_core(prepared['spec'],observed),'CORE_NOT_PROVEN')
    pins=unique_pins(prepared['inputPins']+records.path_pins()+pins)
    for reference in pins:publication.verify_bytes(reference)
    return dict(generation=prepared['c1']['context']['generation'],inputPins=pins)


def execute_prepared(task,private,prepared,*,transport=None):
    task,private=Path(task),Path(private);inputs=prepared['inputs'];stem=inputs['outputFile'][:-5];bound=binding(prepared)
    core_path=task/inputs['outputFile'];rich_path=private/(stem+'.private.json');attempt_path=private/(stem+'.attempt.private.json')
    gate=private/('spug-verification-container-'+publication.CONTAINER+'.gate.private.json')
    claim=private/('spug-verification-failure-'+inputs['continuationFailurePin']['sha256']+'.claim.private.json')
    need(not any(path.exists() or path.is_symlink() for path in (core_path,rich_path,attempt_path,gate,claim)),
         'ALREADY_ATTEMPTED')
    for reference in prepared['inputPins']:publication.verify_bytes(reference)
    gate_pin=publication.exclusive_bytes(gate,publication.canonical(dict(**bound,automaticRetryPermitted=False)))
    claim_pin=publication.exclusive_bytes(claim,publication.canonical(dict(**bound,gatePin=gate_pin)))
    attempt_pin=publication.exclusive_bytes(attempt_path,publication.canonical(dict(schemaVersion='MainProgramSpugVerificationAttempt/v1',
        **bound,inputPins=prepared['inputPins'],stageOrder=schedule(),gatePin=gate_pin,claimPin=claim_pin,retryPermitted=False)))
    transport=transport or VerificationTransport(private,prepared);rows=[];diagnostics=[];current=None
    try:
        for current in schedule():
            for reference in prepared['inputPins']:publication.verify_bytes(reference)
            program_pin=publication.exclusive_bytes(private/(stem+'.'+current+'.program.private.py'),stage_program(prepared,current).encode())
            request_pin=publication.exclusive_bytes(private/(stem+'.'+current+'.request.private.json'),publication.canonical(
                dict(schemaVersion='MainProgramSpugVerificationDispatch/v1',**bound,stage=current,programPin=program_pin,retryPermitted=False)))
            start=len(transport.receipts);result=dict(status='UNKNOWN',errorCode='NOT_RETURNED')
            try:
                result=transport.execute(current);validate_stage_result(prepared,current,result)
                diagnostics+=validate_stage_native(prepared,private,current,transport.receipts[start:],result,[])
            except BaseException as error:
                result=dict(status='UNKNOWN',errorType=type(error).__name__,errorCode=str(error));raise
            finally:
                pin=publication.exclusive_bytes(private/(stem+'.'+current+'.private.json'),publication.canonical(
                    dict(schemaVersion='MainProgramSpugVerificationStage/v1',**bound,stage=current,requestPin=request_pin,
                         result=result,nativeReceiptPins=deepcopy(transport.receipts[start:]))))
                rows.append(dict(stage=current,resultPin=pin,result=result))
        observed=aggregate(prepared,rows);core=publication.project_core(prepared['spec'],observed)
        rich=dict(schemaVersion=EVIDENCE_SCHEMA,**observed,**{k:v for k,v in bound.items() if k!='sourceCommit'},**EFFECTS,
            stage='complete',attemptPin=attempt_pin,stages=[{k:r[k] for k in ('stage','resultPin')} for r in rows],
            originalStages=prepared['failure']['stages'][:6],originalFailedStagePin=prepared['failure']['stages'][6]['resultPin'],
            nativeDiagnosticPins=diagnostics)
        publication.exclusive_bytes(rich_path,publication.canonical(rich))
        raw=publication.canonical(core);core_pin=dict(file=inputs['outputFile'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        selected=dict(schemaVersion='TaskMainProgramInstallations/v4',sourceCommit=inputs['sourceCommit'],
                      controlGenerationPin=inputs['controlGenerationPin'],spugInstallationPin=core_pin,verificationInputsPin=prepared['inputPin'])
        pending=continuation.original.PendingCoreRecords(task,core_pin,core)
        validate_publication_v4(pending,private,selected)
        publication.exclusive_bytes(core_path,raw)
        return dict(status='PASS',report=inputs['outputFile'],publicationCompleted=True,**EFFECTS)
    except BaseException as error:
        failure=dict(schemaVersion='MainProgramSpugVerificationFailure/v1',**bound,status='FAILED',stage=current,attemptPin=attempt_pin,
            stages=[{k:r[k] for k in ('stage','resultPin')} for r in rows],errorType=type(error).__name__,errorCode=str(error),retryPermitted=False,**EFFECTS)
        publication.exclusive_bytes(private/(stem+('.finalization-failure.private.json' if rich_path.exists() else '.private.json')),publication.canonical(failure))
        raise ValueError('MAIN_SPUG_VERIFICATION_FAILED_CHECK_PRIVATE_EVIDENCE') from None


def run_request(task,private,inputs_file,*,verify=False,transport=None):
    prepared=prepare_verification(task,private,inputs_file)
    if not verify:return dict(status='PREPARED_NOT_VERIFIED',remoteDispatched=False,configurationWrites=False)
    return execute_prepared(task,private,prepared,transport=transport)


def parser():
    value=argparse.ArgumentParser(description=__doc__);value.add_argument('--inputs',required=True)
    value.add_argument('--verify',action='store_true');value.add_argument('--task',type=Path,default=TASK)
    value.add_argument('--private',type=Path,default=PRIVATE);return value


if __name__=='__main__':
    args=parser().parse_args()
    try:print(json.dumps(run_request(args.task,args.private,args.inputs,verify=args.verify)))
    except Exception as error:print(json.dumps(dict(status='FAILED',errorType=type(error).__name__,errorCode=str(error))));raise SystemExit(1)
