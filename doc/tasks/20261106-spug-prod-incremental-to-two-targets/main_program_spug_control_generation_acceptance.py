"""Read-only acceptance of published Spug configuration against completed r7.

Default preparation reads local originals only. No publication writer, reload,
backup or restore entry is exposed. Historical success is read, never rewritten.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import main_program_installation_selection as contract
import main_program_control_generation as generation
import main_program_spug_historical_custody as history
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation
import main_program_spug_publication_verify_only as verify

TASK,PRIVATE=publication.TASK,publication.PRIVATE
INPUT_SCHEMA='MainProgramSpugControlGenerationAcceptanceInputs/v1'
SCHEMA='MainProgramSpugControlGenerationAcceptance/v1'
EFFECTS=dict(configurationWrites=False,backupDispatched=False,restoreDispatched=False,
    newConnectionFilesPublished=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)


def need(value,code):
    if not value:raise ValueError('SPUG_CONTROL_ACCEPTANCE_'+code)


def configuration_equivalence(base,secret):
    old=base['c1']['context']['generation']['privatePlan']
    need(type(secret) is dict and secret.get('schemaVersion')=='MainProgramConfigurationInstallationPlan/v2',
         'PLAN_SCHEMA_INVALID')
    for name in ('entrySettings','simpleSettings','originalSpug','originalMetadata','registrations','sourceRegistrationSelectors'):
        need(secret.get(name)==old[name],'PUBLISHED_'+name.upper()+'_CHANGED')
    retained=secret.get('retainedDocumentsByHost')
    need(type(retained) is dict and set(retained)==set(contract.HOSTS) and
         all(type(retained[h]) is list and len(retained[h])==9 for h in contract.HOSTS) and
         retained==old['retainedDocumentsByHost'],'RETAINED_REGISTRATIONS_CHANGED')
    connections=secret.get('newConnections');old_connections=old['newConnections']
    need(type(connections) is dict and len(connections)==len(old_connections)==4,'CONNECTION_SET_CHANGED')
    bridge=deepcopy(secret.get('bridgeSettings'));old_bridge=old['bridgeSettings'];mapping={}
    need(type(bridge) is dict and set(bridge)==set(old_bridge),'BRIDGE_FIELDS_CHANGED')
    for lane in ('sourceConnections','targetConnections','selectionConnections'):
        routes=bridge.get(lane,{});before=old_bridge.get(lane,{})
        need(type(routes) is dict and set(routes)==set(before),'BRIDGE_REFERENCE_SET_CHANGED')
        for ref,name in routes.items():
            if name in connections:
                published=before[ref]
                need(published in old_connections and connections[name]==old_connections[published],
                     'CONNECTION_PAYLOAD_CHANGED')
                need(name not in mapping or mapping[name]==published,'CONNECTION_ROLE_AMBIGUOUS')
                mapping[name]=published
            else:need(name==before[ref],'EXISTING_CONNECTION_REFERENCE_CHANGED')
        if lane in bridge:bridge[lane]={ref:mapping.get(name,name) for ref,name in routes.items()}
    need(set(mapping)==set(connections) and len(set(mapping.values()))==4 and bridge==old_bridge,
         'CONNECTION_MAPPING_INCOMPLETE')
    writes=base['spec']['spugSpec']['writes']
    need(len(writes)==7 and {Path(r['path']).name:r['value'] for r in writes
         if r['path'] not in publication.SETTINGS.values()}==old_connections,'PUBLISHED_CONNECTION_ORIGINALS_CHANGED')
    return dict(newToPublished=mapping,configurationCount=7,retainedRegistrationCount=27,newConnectionFilesPublished=False)


def value_pin(path,value):
    raw=publication.canonical(value)
    return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def project_published_configuration(base,candidate,observation):
    """Pure protocol projection; prepare owns actual generation validation."""
    configuration_equivalence(base,candidate['privatePlan'])
    need(type(observation) is dict and set(observation)=={'schemaVersion','sourceCommit','revisionId',
        'controlGenerationPin','spugResourceBuildPin','selectorsByHost','hostPreservationByHost','spug'} and
        observation['schemaVersion']=='MainProgramSpugPublicationObservation/v2','OBSERVATION_INVALID')
    need(set(observation['selectorsByHost'])==set(observation['hostPreservationByHost'])==set(contract.HOSTS),
         'OBSERVATION_HOST_SET_CHANGED')
    view=deepcopy(base);spec=view['spec'];old_spug=base['spec']['spugSpec'];spug=observation['spug']
    need(type(spug) is dict and set(spug)==set(old_spug['observation']),'SPUG_OBSERVATION_FIELDS_CHANGED')
    for name in ('containerId','containerSnapshot','protectedContainerId','protectedContainerSnapshot','taskSnapshotSha256','productPins'):
        need(spug[name]==old_spug['observation'][name],'SPUG_'+name.upper()+'_CHANGED')
    need(spug['entryPid']==base['resourceTransition']['entryAfter']['pid'],'SPUG_ENTRY_CHANGED')
    settings={};connections=deepcopy(old_spug['observation']['connections'])
    for row in old_spug['writes']:
        reference=value_pin(row['path'],row['value'])
        if row['path'] in publication.SETTINGS.values():
            key=next(k for k,v in publication.SETTINGS.items() if v==row['path']);settings[key]=reference
        else:connections[Path(row['path']).name]=reference
    need(spug['settings']==settings and spug['connections']==connections,'PUBLISHED_CONFIGURATION_PINS_CHANGED')
    current=candidate['generation']['sourceCommit']
    selectors=publication.selector_rows(dict(candidate['privatePlan'],programTargets=candidate['plan']['programTargets']),
                                        candidate['controllersByHost'])
    for host in contract.HOSTS:
        original=base['spec']['hostSpecs'][host]
        need(selectors[host]==[{k:r[k] for k in ('path','value','registrationPin')} for r in original['selectors']],
             'PUBLISHED_SELECTOR_VALUES_CHANGED')
        expected=[dict(path=r['path'],pin=value_pin(r['path'],r['value'])) for r in original['selectors']]
        need(observation['selectorsByHost'][host]==expected,'CURRENT_SELECTOR_PIN_CHANGED')
        baseline=observation['hostPreservationByHost'][host]
        need(type(baseline) is dict and set(baseline)=={'containers','fstabPin','mountinfoSha256'} and
             type(baseline['containers']) is dict and baseline['containers'] and contract.sha(baseline['mountinfoSha256']),
             'HOST_PRESERVATION_INVALID')
        contract.remote_pin(baseline['fstabPin'])
        spec['hostSpecs'][host].update(sourceCommit=current,controllers=deepcopy(candidate['controllersByHost'][host]),
            targetConfigRef=candidate['targets'][host],baseline=deepcopy(baseline))
        need(spec['hostSpecs'][host]['targetConfigRef']==original['targetConfigRef'],'TARGET_IDENTITY_CHANGED')
    spec['spugSpec'].update(sourceCommit=current,observation=deepcopy(spug))
    context=view['verificationContext'];context['generation']=deepcopy(candidate);context['observation']=deepcopy(observation)
    view['inputs'].update(sourceCommit=current,revisionId=candidate['plan']['revisionId'],controlGenerationPin=candidate['generationPin'])
    need(len(view['resourceTransition']['afterFiles'])==14,'COMPLETE_565_RESOURCES_REQUIRED')
    return view


def prepare(task,private,inputs_file,*,source_roles=None):
    records=contract.Records(task);private=Path(private);inputs=records.read(inputs_file)
    fields={'schemaVersion','historicalReadCustodyPin','controlGenerationPin','observationPin','verificationId','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and inputs['schemaVersion']==INPUT_SCHEMA and
         type(inputs['verificationId']) is str and re.fullmatch('[a-z][a-z0-9-]{0,39}',inputs['verificationId']),
         'INPUTS_INVALID')
    if source_roles is None:context=history.load_context(records.task,private,inputs['historicalReadCustodyPin'])
    else:
        need(type(source_roles) is history.SourceRoles and source_roles.value['acceptanceInputsPin']==
             records.references[inputs_file],'SOURCE_CUSTODY_INPUT_CHANGED')
        context=history.load_context(records.task,private,inputs['historicalReadCustodyPin'],source_roles=source_roles)
    verified=verify.validate_publication_v4(records,private,context.selected,historical=context)
    base_inputs=records.pinned(context.selected['verificationInputsPin'])
    base=verify.prepare_value(records,private,base_inputs,context.selected['verificationInputsPin'],historical=context)
    candidate=generation.load_control_generation(records.task,private,inputs['controlGenerationPin'])
    need(candidate['plan'].get('revisionId')=='r7' and candidate['plan']['predecessorGenerationPin']==
         context.selected['controlGenerationPin'] and candidate['generationPin']!=context.selected['controlGenerationPin'],
         'COMPLETED_R7_SUCCESSOR_REQUIRED')
    commit=candidate['generation']['sourceCommit'];name='main-program-spug-control-acceptance-'+commit[:7]+'-r7-'+inputs['verificationId']+'.json'
    need(inputs['outputFile']==name,'OUTPUT_CHANGED')
    pins=[];observation=continuation.private_json(private,inputs['observationPin'],pins)
    transition_wrapper=records.pinned(context.value['resourceTransitionReferencePin'])
    transition=records.pinned(transition_wrapper['transitionCorePin'])
    transition_inputs=records.pinned(transition['transitionInputsPin'])
    need(observation.get('sourceCommit')==commit and observation.get('revisionId')=='r7' and
         observation.get('controlGenerationPin')==inputs['controlGenerationPin'] and
         observation.get('spugResourceBuildPin')==transition_inputs['resourceBuildPin'],
         'OBSERVATION_BINDING_CHANGED')
    equivalent=configuration_equivalence(base,candidate['privatePlan'])
    view=project_published_configuration(base,candidate,observation)
    view['inputs'].update(outputFile=name,verificationId=inputs['verificationId'])
    all_pins=verify.unique_pins(records.path_pins()+pins+context.finish()+verified['inputPins']+
        base['inputPins']+candidate['inputPins']+[publication.file_pin(__file__)])
    if source_roles is not None:all_pins=verify.unique_pins(all_pins+source_roles.finish())
    prepared=dict(inputs=inputs,inputPin=records.references[inputs_file],inputPins=all_pins,generation=candidate,
        programView=view,equivalence=equivalent,sourceCommit=commit,revisionId='r7')
    if source_roles is not None:prepared['sourceRoles']=source_roles
    unchanged(prepared)
    return prepared


def unchanged(prepared):
    for reference in prepared['inputPins']:publication.verify_bytes(reference)


def schedule():return verify.schedule()


def stage_program(prepared,stage):return verify.stage_program(prepared['programView'],stage)


def command_arguments(prepared,stage):return verify.command_arguments(prepared['programView'],stage)


def validate_stage_result(prepared,stage,result):return verify.validate_stage_result(prepared['programView'],stage,result)


def validate_stage_native(prepared,private,stage,references,result,pins):
    return verify.validate_stage_native(prepared['programView'],private,stage,references,result,pins)


class AcceptanceTransport(verify.VerificationTransport):
    def __init__(self,private,prepared):super().__init__(private,prepared['programView'])

    def execute(self,stage):
        # Record the returned object before local result/native validators run.
        program=verify.stage_program(self.prepared,stage)
        argv,timeout=verify.command_arguments(self.prepared,stage)
        is_host=stage.startswith('host-verify-')
        if not is_host:self._recorder.inspect_current()
        return self._recorder.command(stage,argv,program,timeout)

    def finish_stage(self,stage,result):
        if not stage.startswith('host-verify-'):
            self._recorder.inspect_current()
            if stage=='spug-verify':result['protectedSpugUnchanged']=True
        return result


def binding(prepared):
    return dict(acceptanceInputsPin=prepared['inputPin'],sourceCommit=prepared['sourceCommit'],revisionId=prepared['revisionId'],
        **{k:prepared['inputs'][k] for k in ('historicalReadCustodyPin','controlGenerationPin','observationPin','verificationId')})


def summary(prepared):
    return dict(status='PASS',controlGenerationAccepted=True,configurationCount=7,retainedRegistrationCount=27,
        selectorCount=12,controlCount=4,productResourceCount=14,applicationCount=33,taskCount=3,
        newToPublished=prepared['equivalence']['newToPublished'],**EFFECTS)


def validate_completed(prepared,private,rich,pins):
    bound=binding(prepared)
    need(type(rich) is dict and set(rich)=={'schemaVersion','recordType',*bound,*summary(prepared),'stage','attemptPin','stages'} and
         rich['schemaVersion']==SCHEMA and rich['recordType']=='result' and rich['stage']=='complete' and
         all(rich[k]==v for k,v in {**bound,**summary(prepared)}.items()),'RESULT_CHANGED')
    attempt=continuation.private_json(private,rich['attemptPin'],pins)
    need(set(attempt)=={'schemaVersion','recordType',*bound,'inputPins','stageOrder','claimPin','retryPermitted'} and
         attempt['schemaVersion']==SCHEMA and attempt['recordType']=='attempt' and attempt['retryPermitted'] is False and
         all(attempt[k]==v for k,v in bound.items()) and
         attempt['stageOrder']==schedule(),'ATTEMPT_CHANGED')
    if 'sourceRoles' in prepared:prepared['sourceRoles'].verify_acceptance_inputs(attempt['inputPins'],prepared['inputPins'])
    else:need(attempt['inputPins']==prepared['inputPins'],'ATTEMPT_CHANGED')
    claim=continuation.private_json(private,attempt['claimPin'],pins)
    need(claim==dict(schemaVersion=SCHEMA,recordType='claim',**bound,retryPermitted=False),'CLAIM_CHANGED')
    rows=rich['stages']
    need(type(rows) is list and [r.get('stage') for r in rows]==schedule() and
         all(type(r) is dict and set(r)=={'stage','resultPin'} for r in rows) and
         len({r['resultPin']['path'] for r in rows})==6,'STAGES_INCOMPLETE')
    stem=prepared['inputs']['outputFile'][:-5]
    for row in rows:
        stage=row['stage'];value=continuation.private_json(private,row['resultPin'],pins)
        need(row['resultPin']['path']==str(Path(private)/(stem+'.'+stage+'.private.json')) and
             set(value)=={'schemaVersion','recordType',*bound,'stage','requestPin','result','nativeReceiptPins','validationError'} and
             value['schemaVersion']==SCHEMA and value['recordType']=='stage' and value['stage']==stage and
             value['validationError'] is None and all(value[k]==v for k,v in bound.items()),'STAGE_CHANGED')
        request=continuation.private_json(private,value['requestPin'],pins)
        need(set(request)=={'schemaVersion','recordType',*bound,'stage','programPin','retryPermitted'} and
             request['schemaVersion']==SCHEMA and request['recordType']=='dispatch' and request['stage']==stage and
             request['retryPermitted'] is False and all(request[k]==v for k,v in bound.items()),'DISPATCH_CHANGED')
        need(continuation.private_raw(private,request['programPin'],pins)==stage_program(prepared,stage).encode('utf-8'),
             'PROGRAM_CHANGED')
        validate_stage_result(prepared,stage,value['result'])
        validate_stage_native(prepared,private,stage,value['nativeReceiptPins'],value['result'],pins)
    unchanged(prepared)


def load_completed_acceptance(task,private,result_pin,*,source_roles=None):
    records=contract.Records(task);core=records.pinned(result_pin)
    need(type(core) is dict and core.get('schemaVersion')==SCHEMA and core.get('recordType')=='result' and
         core.get('status')=='PASS','COMPLETED_RESULT_REQUIRED')
    inputs=records.pinned(core['acceptanceInputsPin'])
    need(result_pin['file']==inputs['outputFile'],'COMPLETED_OUTPUT_CHANGED')
    if source_roles is None:prepared=prepare(task,private,core['acceptanceInputsPin']['file'])
    else:prepared=prepare(task,private,core['acceptanceInputsPin']['file'],source_roles=source_roles)
    pins=[]
    need(prepared['inputPin']==core['acceptanceInputsPin'],'COMPLETED_INPUT_CHANGED')
    rich=continuation.private_json(private,core['privateEvidencePin'],pins)
    need(core==dict({k:v for k,v in rich.items() if k!='stages'},privateEvidencePin=core['privateEvidencePin']),
         'CORE_CHANGED')
    validate_completed(prepared,private,rich,pins)
    pins=verify.unique_pins(prepared['inputPins']+records.path_pins()+pins)
    for pin in pins:publication.verify_bytes(pin)
    if source_roles is not None:source_roles.finish()
    return dict(generation=prepared['generation'],inputPins=pins)


def _record_stage(prepared,private,current,bound,transport,rows):
    """One exact dispatch journal; the caller owns generation admission."""
    private=Path(private);stem=prepared['inputs']['outputFile'][:-5]
    program=publication.exclusive_bytes(private/(stem+'.'+current+'.program.private.py'),stage_program(prepared,current).encode('utf-8'))
    request=publication.exclusive_bytes(private/(stem+'.'+current+'.request.private.json'),publication.canonical(
        dict(schemaVersion=SCHEMA,recordType='dispatch',**bound,stage=current,programPin=program,retryPermitted=False)))
    start=len(transport.receipts);result=dict(status='UNKNOWN',errorCode='NOT_RETURNED')
    returned=False;validation_error=None
    try:
        result=transport.execute(current);returned=True
        if isinstance(transport,AcceptanceTransport):result=transport.finish_stage(current,result)
        validate_stage_result(prepared,current,result)
        validate_stage_native(prepared,private,current,transport.receipts[start:],result,[])
    except BaseException as error:
        validation_error=dict(errorType=type(error).__name__,errorCode=str(error))
        if not returned:result=dict(status='UNKNOWN',**validation_error)
        raise
    finally:
        reference=publication.exclusive_bytes(private/(stem+'.'+current+'.private.json'),publication.canonical(
            dict(schemaVersion=SCHEMA,recordType='stage',**bound,stage=current,requestPin=request,
                 result=result,validationError=validation_error,nativeReceiptPins=deepcopy(transport.receipts[start:]))))
        rows.append(dict(stage=current,resultPin=reference))


def execute_acceptance(task,private,prepared,*,transport=None):
    task=Path(task);private=Path(private);stem=prepared['inputs']['outputFile'][:-5];bound=binding(prepared)
    core_path=task/prepared['inputs']['outputFile'];rich_path=private/(stem+'.private.json')
    attempt_path=private/(stem+'.attempt.private.json')
    claim_path=private/('spug-control-acceptance-generation-'+prepared['inputs']['controlGenerationPin']['sha256']+'.claim.private.json')
    need(not any(p.exists() or p.is_symlink() for p in (core_path,rich_path,attempt_path,claim_path)),'ALREADY_ATTEMPTED')
    unchanged(prepared)
    claim=publication.exclusive_bytes(claim_path,publication.canonical(dict(schemaVersion=SCHEMA,recordType='claim',**bound,retryPermitted=False)))
    attempt=publication.exclusive_bytes(attempt_path,publication.canonical(dict(schemaVersion=SCHEMA,recordType='attempt',**bound,
        inputPins=prepared['inputPins'],stageOrder=schedule(),claimPin=claim,retryPermitted=False)))
    rows=[];current=None
    try:
        transport=transport or AcceptanceTransport(private,prepared)
        for current in schedule():
            unchanged(prepared)
            _record_stage(prepared,private,current,bound,transport,rows)
        rich=dict(schemaVersion=SCHEMA,recordType='result',**bound,**summary(prepared),stage='complete',attemptPin=attempt,stages=rows)
        validate_completed(prepared,private,rich,[])
        rich_pin=publication.exclusive_bytes(rich_path,publication.canonical(rich))
        core=dict({k:v for k,v in rich.items() if k!='stages'},privateEvidencePin=rich_pin)
        publication.exclusive_bytes(core_path,publication.canonical(core))
        return dict(status='PASS',report=prepared['inputs']['outputFile'],controlGenerationAccepted=True,**EFFECTS)
    except BaseException as error:
        failure=dict(schemaVersion=SCHEMA,recordType='failure',**bound,status='FAILED',stage=current,
            attemptPin=attempt,stages=rows,errorType=type(error).__name__,errorCode=str(error),retryPermitted=False,**EFFECTS)
        failure_path=private/(stem+('.finalization-failure.private.json' if rich_path.exists() else '.private.json'))
        publication.exclusive_bytes(failure_path,publication.canonical(failure))
        raise ValueError('SPUG_CONTROL_ACCEPTANCE_FAILED_CHECK_PRIVATE_EVIDENCE') from None


def run_request(task,private,inputs_file,*,verify=False,transport=None):
    prepared=prepare(task,private,inputs_file)
    if not verify:return dict(status='PREPARED_NOT_VERIFIED',remoteDispatched=False,configurationWrites=False,
        newConnectionFilesPublished=False,configurationCount=7,retainedRegistrationCount=27)
    return execute_acceptance(task,private,prepared,transport=transport)


def parser():
    value=argparse.ArgumentParser(description=__doc__);value.add_argument('--inputs',required=True)
    value.add_argument('--verify',action='store_true');value.add_argument('--task',type=Path,default=TASK)
    value.add_argument('--private',type=Path,default=PRIVATE);return value


if __name__=='__main__':
    args=parser().parse_args()
    try:print(json.dumps(run_request(args.task,args.private,args.inputs,verify=args.verify)))
    except (OSError,ValueError,KeyError,TypeError) as error:
        code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'LOCAL_INPUTS_MISSING_OR_INVALID'
        print(json.dumps(dict(status='REFUSED',errorCode=code,verifyRequested=args.verify)));raise SystemExit(1)
