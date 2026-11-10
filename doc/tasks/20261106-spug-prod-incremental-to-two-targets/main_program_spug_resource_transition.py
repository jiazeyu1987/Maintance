"""Explicit installed-resource transitions. Historical installers remain immutable.

Prepare is local only. Observe/apply are explicit; failures retain their claim.
The dependency guard body is reused verbatim, with a separately proved view.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation
import main_program_spug_resource_activation as activation
import spug_runtime_dependency_completion as dependency

TASK,PRIVATE=publication.TASK,publication.PRIVATE
REMOTE='/opt/intruoyi-spug/'
SCHEMA='MainProgramSpugResourceTransitionInputs/v1'


def need(value,code):
    if not value:raise ValueError('SPUG_RESOURCE_TRANSITION_'+code)


def verifier():
    import main_program_spug_publication_verify_only
    return main_program_spug_publication_verify_only


def file_set(value):
    need(type(value) is dict and set(value)==dependency.ALLOWED,'FILE_SET_INVALID')
    for pin in value.values():
        need(type(pin) is dict and set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and
             pin['bytes']>0 and contract.sha(pin['sha256']),'FILE_PIN_INVALID')
    return value


def before_files(base):
    rows=base['dependency']['core']['filePinsAfter']
    need(len(rows)==len(dependency.ALLOWED) and all(p['path'].startswith(REMOTE) for p in rows),'BEFORE_SET_INVALID')
    return file_set({p['path'][len(REMOTE):]:{k:p[k] for k in ('bytes','sha256')} for p in rows})


def validate_delta(value,before,after,build_pin):
    file_set(before);file_set(after)
    expected=[dict(relativePath=n,beforePin=dict(path=REMOTE+n,**before[n]),afterPin=dict(path=REMOTE+n,**after[n]))
              for n in sorted(before) if before[n]!=after[n]]
    need(expected and type(value) is dict and set(value)=={'schemaVersion','resourceBuildPin','changes'} and
         value['schemaVersion']=='MainProgramSpugResourceDeploymentDelta/v2' and value['resourceBuildPin']==build_pin and
         value['changes']==expected,'EXACT_NONEMPTY_DELTA_REQUIRED')
    return expected


def selection_budget(raw):
    values=[]
    for node in ast.parse(raw.decode('utf-8-sig')).body:
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='SELECTION_TOTAL_SECONDS' for n in node.targets):
            need(isinstance(node.value,ast.Constant) and type(node.value.value) is int,'SELECTION_BUDGET_LITERAL_REQUIRED')
            values.append(node.value.value)
    need(len(values)==1 and 1<=values[0]<=60,'SELECTION_BUDGET_INVALID')
    return values[0]


def validate_build(records,private,reference,*,verify_checkout):
    report=records.pinned(reference);pins=[]
    fields={'schemaVersion','status','sourceCommit','worktree','fileCount','files','dependencyGraph',
            'testEvidencePin','sourceCustodyPin','selectionReadBudgetSeconds'}
    need(type(report) is dict and set(report)==fields and report['schemaVersion']=='MainProgramSpugResourceBuild/v2' and
         report['status']=='PASS' and re.fullmatch('[0-9a-f]{40}',report['sourceCommit']) is not None and
         report['fileCount']==len(dependency.ALLOWED) and type(report['fileCount']) is int,'BUILD_INVALID')
    root=Path(report['worktree']);need(root.is_absolute(),'WORKTREE_REQUIRED')
    need(type(report['files']) is dict and set(report['files'])=={'ops/spug/'+n for n in dependency.ALLOWED},'BUILD_FILES_INVALID')
    files=file_set({n:report['files']['ops/spug/'+n] for n in dependency.ALLOWED})
    proof=records.pinned(report['testEvidencePin'])
    need(type(proof) is dict and set(proof)=={'schemaVersion','status','actualExitCode','actualPassed','actualSkipped','inputPins','logPin'} and
         proof['schemaVersion']=='TaskSpugResourceValidation/v2' and proof['status']=='PASS' and
         type(proof['actualExitCode']) is int and proof['actualExitCode']==0 and type(proof['actualPassed']) is int and
         proof['actualPassed']>0 and type(proof['actualSkipped']) is int and proof['actualSkipped']==0 and
         type(proof['inputPins']) is dict and set(report['files'])<set(proof['inputPins']),'TEST_EVIDENCE_INVALID')
    custody=continuation.private_json(private,report['sourceCustodyPin'],pins)
    need(type(custody) is dict and set(custody)=={'schemaVersion','entries'} and
         custody['schemaVersion']=='MainProgramSpugResourceSourceCustody/v1' and type(custody['entries']) is list and
         len(custody['entries'])==len(proof['inputPins']),'SOURCE_CUSTODY_INVALID')
    rows=custody['entries'];need(all(type(r) is dict and set(r)=={'relativePath','originalPin','preservedPin'} for r in rows) and
         len({r['relativePath'] for r in rows})==len(rows) and {r['relativePath'] for r in rows}==set(proof['inputPins']),
         'SOURCE_CUSTODY_SET_CHANGED')
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(args,raw=None):
        result=subprocess.run(['git','-C',str(root),*args],input=raw,capture_output=True,env=env,timeout=30)
        need(result.returncode==0,'BUILD_GIT_FAILED');return result.stdout.decode('utf-8').strip()
    if verify_checkout:
        need((root/'.git').is_file() and not (root/'.git').is_symlink(),'DEDICATED_WORKTREE_REQUIRED')
        need(root.resolve(strict=True)==root and git(['rev-parse','HEAD'])==report['sourceCommit'] and
             git(['status','--porcelain','--untracked-files=all'])=='','BUILD_CHECKOUT_NOT_CLOSED')
    sources={}
    for row in rows:
        name=row['relativePath'];dependency.relative_path(name);old=row['originalPin']
        need(old['path']==str(root/name) and old['sha256']==proof['inputPins'][name],'SOURCE_BINDING_CHANGED')
        raw=continuation.private_raw(private,row['preservedPin'],pins)
        need(len(raw)==old['bytes'] and hashlib.sha256(raw).hexdigest()==old['sha256'],'SOURCE_BYTES_CHANGED')
        if verify_checkout:
            need(publication.verify_bytes(old)==raw and git(['hash-object','--path='+name,'--stdin'],raw)==
                 git(['rev-parse','HEAD:'+name]),'COMMITTED_SOURCE_CHANGED');pins.append(old)
        if name in report['files']:
            local=name[len('ops/spug/'):];need(local in files and files[local]=={k:old[k] for k in ('bytes','sha256')},'SOURCE_FILE_CHANGED')
            sources[local]=raw
    graph=dependency.inspect_runtime_dependencies(sources=sources)
    need(graph==report['dependencyGraph'] and graph['files']==files,'DEPENDENCY_GRAPH_CHANGED')
    need(type(report['selectionReadBudgetSeconds']) is int and
         report['selectionReadBudgetSeconds']==selection_budget(sources['smallapp_adapter.py']),'SELECTION_BUDGET_CHANGED')
    log=continuation.private_raw(private,proof['logPin'],pins).decode('utf-8')
    summaries=re.findall(r'(?m)^\s*(?:=+\s*)?([0-9]+) passed(?:, [0-9]+ warnings?)? in [0-9.]+s[^\r\n]*\r?$',log)
    need(summaries and int(summaries[-1])==proof['actualPassed'] and
         not re.search(r'\b[0-9]+ (?:failed|skipped|errors?|xfailed|xpassed|deselected)\b',log),'TEST_LOG_NOT_PASSED')
    for pin in pins:publication.verify_bytes(pin)
    return report,pins


def runtime_view(base,files,identity,environment):
    """A detached guard input, never serialized as an altered A completion."""
    file_set(files);need(contract.sha(environment),'ENVIRONMENT_REQUIRED')
    value=deepcopy(base['dependency']['prepared'])
    value['completion']=dict(files={n:deepcopy(files[n]) for n in sorted(files)})
    return value


def guard_program(prepared,files,identity):
    view=runtime_view(prepared['base'],files,identity,prepared['environment'])
    return dependency.runtime_program(view,'after',identity,prepared['environment'])


def validate_guard(prepared,result,files,identity):
    view=runtime_view(prepared['base'],files,identity,prepared['environment'])
    return dependency.validate_runtime_result(view,result,'after',identity,prepared['environment'])


def mixed_files(prepared,replaced):
    names={r['relativePath'] for r in prepared['changes']}
    need(type(replaced) is set and replaced<=names,'MIXED_STATE_INVALID')
    return {n:prepared['afterFiles'][n] if n in replaced else p for n,p in prepared['beforeFiles'].items()}


def unchanged(prepared):
    for pin in prepared['inputPins']:publication.verify_bytes(pin)


def check_runtime(prepared,replaced):
    for name,pin in mixed_files(prepared,replaced).items():
        path=dependency.source_file(Path(prepared['runtime']),name)
        need(dependency.content_pin(path)==pin,'RUNTIME_FILE_CHANGED')


def replace_files(prepared,private,guard):
    """Real local bind-mount files; archive every changed original first."""
    private=Path(private);audit=private/(prepared['stem']+'-originals')
    need(not audit.exists() and not audit.is_symlink(),'ORIGINALS_EXIST');audit.mkdir(mode=0o700)
    originals=[];candidates={};pending={}
    for index,row in enumerate(prepared['changes']):
        name=row['relativePath'];active=dependency.source_file(Path(prepared['runtime']),name)
        old=publication.file_pin(active)
        need({k:old[k] for k in ('bytes','sha256')}==prepared['beforeFiles'][name],'BEFORE_CHANGED')
        archived=publication.exclusive_bytes(audit/(str(index)+'-before'+active.suffix),publication.verify_bytes(old))
        original=dict(relativePath=name,beforePin=old,archivedPin=archived);originals.append(original)
        candidate=dependency.source_file(Path(prepared['build']['worktree'])/'ops/spug',name)
        raw=candidate.read_bytes();need(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==prepared['afterFiles'][name],'CANDIDATE_CHANGED')
        candidates[name]=raw;pending[name]=active.with_name(active.name+'.'+prepared['stem']+'.pending')
        need(not pending[name].exists() and not pending[name].is_symlink(),'PENDING_EXISTS')
    publication.exclusive_bytes(audit/'originals.json',publication.canonical(originals))
    replaced=set();results=[]
    def verify():
        unchanged(prepared);check_runtime(prepared,replaced)
        for row in originals:publication.verify_bytes(row['archivedPin'])
        guard(set(replaced))
    verify()
    for index,original in enumerate(originals):
        name=original['relativePath'];active=Path(prepared['runtime'])/name
        publication.exclusive_bytes(audit/('dispatch-'+str(index)+'.json'),publication.canonical(dict(relativePath=name,state='DISPATCHED_OUTCOME_UNKNOWN')))
        result=activation.replace_archived(active,original['archivedPin'],pending[name],original['beforePin'],candidates[name])
        result=dict(relativePath=name,**result);results.append(result);replaced.add(name)
        publication.exclusive_bytes(audit/('replacement-'+str(index)+'.json'),publication.canonical(result));verify()
    return results


def _prepare(records,private,inputs,input_pin,*,verify_checkout,allow_unobserved=False,base=None):
    # A caller may already have read later publications. Their unrelated pins
    # must not enter this transition's immutable input set.
    records=contract.Records(records.task)
    need(records.pinned(input_pin)==inputs,'INPUT_DOCUMENT_CHANGED')
    fields={'schemaVersion','baseVerificationInputsPin','resourceBuildPin','deploymentDeltaPin','observationPin','operationId','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and inputs['schemaVersion']==SCHEMA and
         type(inputs['operationId']) is str and re.fullmatch('r[1-9][0-9]*',inputs['operationId']),'INPUTS_INVALID')
    base_inputs=records.pinned(inputs['baseVerificationInputsPin'])
    need(base_inputs['schemaVersion']==verifier().INPUT_SCHEMA,'BASE_VERIFICATION_V1_REQUIRED')
    if base is None:base=verifier().prepare_value(records,private,base_inputs,inputs['baseVerificationInputsPin'])
    else:
        # The caller already read the full A/c1 closure. Recheck its immutable
        # physical inputs and exact input document, without reinterpreting it.
        need(base['inputs']==base_inputs and base['inputPin']==inputs['baseVerificationInputsPin'],'BASE_CHANGED')
        for pin in base['inputPins']:publication.verify_bytes(pin)
    build,pins=validate_build(records,private,inputs['resourceBuildPin'],verify_checkout=verify_checkout)
    before=before_files(base);after={n:build['files']['ops/spug/'+n] for n in sorted(dependency.ALLOWED)}
    changes=validate_delta(records.pinned(inputs['deploymentDeltaPin']),before,after,inputs['resourceBuildPin'])
    stem='main-program-spug-resource-transition-'+build['sourceCommit'][:7]+'-'+inputs['operationId']
    need(inputs['outputFile']==stem+'.json','OUTPUT_NAME_INVALID')
    core=base['dependency']['core']
    value=dict(inputs=inputs,inputPin=input_pin,base=base,build=build,beforeFiles=before,afterFiles=after,changes=changes,
        stem=stem,runtime=publication.RUNTIME,entryBefore=core['entryAfter'],environment=core['entryEnvironmentSha256'])
    value['inputPins']=verifier().unique_pins(pins+base['inputPins']+records.path_pins()+
        [publication.file_pin(__file__),publication.file_pin(verifier().__file__)])
    observation=None
    if inputs['observationPin'] is not None:
        observation=continuation.private_json(private,inputs['observationPin'],value['inputPins'])
        need(set(observation)=={'schemaVersion','binding','result','nativeReceiptPins'} and
             observation['schemaVersion']=='MainProgramSpugResourceTransitionObservation/v1' and
             observation['binding']==observation_binding(value),'OBSERVATION_BINDING_CHANGED')
        validate_guard(value,observation['result'],before,value['entryBefore'])
        validate_native(value,private,'observation',guard_program(value,before,value['entryBefore']),
                        observation['result'],observation['nativeReceiptPins'],value['inputPins'])
    else:need(allow_unobserved,'OBSERVATION_REQUIRED')
    value['observation']=observation;value['inputPins']=verifier().unique_pins(value['inputPins']);unchanged(value)
    return value


def prepare_transition(task,private,inputs_file,*,allow_unobserved=False):
    records=contract.Records(task);inputs=records.read(inputs_file)
    return _prepare(records,Path(private),inputs,records.references[inputs_file],verify_checkout=True,allow_unobserved=allow_unobserved)


def observation_binding(prepared):
    return {k:prepared['inputs'][k] for k in ('baseVerificationInputsPin','resourceBuildPin','deploymentDeltaPin','operationId')}


def binding(prepared):
    return dict(**observation_binding(prepared),transitionInputsPin=prepared['inputPin'])


def argv(prepared):
    return [publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-',prepared['stem']]


def validate_native(prepared,private,label,program,result,references,pins):
    rows=continuation.validate_native_receipts(private,references,pins)
    need([r[0]['label'] for r in rows]==['inspect',label,'inspect'],'NATIVE_SET_CHANGED')
    for row in (rows[0],rows[2]):
        verifier().validate_inspect(prepared['base']['dependency']['prepared'],row[1],row[2])
        need(continuation.private_raw(private,row[0]['stderrPin'],pins)==b'','INSPECT_STDERR')
    verifier().validate_native_command(private,rows[1],argv(prepared),program,result,pins,timeout=120)


class ActualTransport:
    def __init__(self,private,prepared,*,observation=False):
        context=deepcopy(prepared['base']['c1']);context['inputs']['outputFile']=prepared['inputs']['outputFile']
        if observation:context['inputs']['outputFile']=prepared['stem']+'.observation.json'
        self.native=continuation.ActualContinuationTransport(private,context);self.prepared=prepared
    @property
    def receipts(self):return self.native.receipts
    def command(self,label,program):
        self.native.inspect_current();result=self.native.command(label,argv(self.prepared),program,120)
        self.native.inspect_current();return result


def observe_transition(private,prepared,*,transport=None):
    need(prepared['observation'] is None,'OBSERVATION_ALREADY_BOUND');unchanged(prepared)
    transport=transport or ActualTransport(private,prepared,observation=True);start=len(transport.receipts)
    program=guard_program(prepared,prepared['beforeFiles'],prepared['entryBefore'])
    result=transport.command('observation',program)
    validate_guard(prepared,result,prepared['beforeFiles'],prepared['entryBefore'])
    validate_native(prepared,private,'observation',program,result,transport.receipts[start:],[]);unchanged(prepared)
    return publication.exclusive_bytes(Path(private)/(prepared['stem']+'.observation.private.json'),publication.canonical(dict(
        schemaVersion='MainProgramSpugResourceTransitionObservation/v1',binding=observation_binding(prepared),result=result,
        nativeReceiptPins=transport.receipts[start:])))


def reload_program(prepared):
    guard=guard_program(prepared,prepared['afterFiles'],prepared['entryBefore'])
    view=runtime_view(prepared['base'],prepared['afterFiles'],prepared['entryBefore'],prepared['environment'])
    # Reuse the original combined guard/reload builder, with an explicit new view.
    return dependency.reload_program(view,prepared['entryBefore'],prepared['environment'])


def execute_transition(task,private,prepared,*,transport=None):
    task,private=Path(task),Path(private);stem=prepared['stem'];bound=binding(prepared)
    need(prepared['observation'] is not None,'OBSERVATION_REQUIRED');unchanged(prepared)
    gate=private/('spug-resource-transition-'+publication.CONTAINER+'.gate.private.json')
    other=private/('spug-verification-container-'+publication.CONTAINER+'.gate.private.json')
    rich_path=private/(stem+'.private.json');attempt_path=private/(stem+'.attempt.private.json');output=task/(stem+'.json')
    need(not any(p.exists() or p.is_symlink() for p in (gate,other,rich_path,attempt_path,output)),'ALREADY_ATTEMPTED')
    gate_pin=publication.exclusive_bytes(gate,publication.canonical(dict(**bound,retryPermitted=False)))
    attempt=publication.exclusive_bytes(attempt_path,publication.canonical(dict(schemaVersion='MainProgramSpugResourceTransitionAttempt/v1',
        **bound,gatePin=gate_pin,inputPins=prepared['inputPins'],retryPermitted=False)))
    transport=transport or ActualTransport(private,prepared);events=[];stage='before';replacements=[]
    def invoke(label,program,files=None,identity=None):
        nonlocal stage
        stage=label;unchanged(prepared);start=len(transport.receipts)
        result=transport.command(label,program)
        validate_native(prepared,private,label,program,result,transport.receipts[start:],[])
        if files is not None:validate_guard(prepared,result,files,identity)
        ref=publication.exclusive_bytes(private/(stem+'.'+label+'.private.json'),publication.canonical(dict(
            label=label,result=result,nativeReceiptPins=transport.receipts[start:])))
        events.append(dict(label=label,pin=ref));return result
    try:
        before=invoke('before',guard_program(prepared,prepared['beforeFiles'],prepared['entryBefore']),prepared['beforeFiles'],prepared['entryBefore'])
        need(before==prepared['observation']['result'],'FRESH_OBSERVATION_CHANGED')
        def guard(replaced):
            files=mixed_files(prepared,replaced)
            invoke('guard-'+str(len(replaced)),guard_program(prepared,files,prepared['entryBefore']),files,prepared['entryBefore'])
        replacements=replace_files(prepared,private,guard)
        publication.exclusive_bytes(private/(stem+'.reload-intent.private.json'),publication.canonical(dict(**bound,entryBefore=prepared['entryBefore'])))
        after_identity=invoke('reload',reload_program(prepared))
        dependency.validate_reload_identity(prepared['entryBefore'],after_identity)
        after=invoke('after',guard_program(prepared,prepared['afterFiles'],after_identity),prepared['afterFiles'],after_identity)
        unchanged(prepared);check_runtime(prepared,{r['relativePath'] for r in prepared['changes']})
        rich=dict(schemaVersion='MainProgramSpugResourceTransition/v1',status='PASS',**bound,attemptPin=attempt,
            entryBefore=prepared['entryBefore'],entryAfter=after_identity,entryEnvironmentSha256=prepared['environment'],
            beforeFiles=prepared['beforeFiles'],afterFiles=prepared['afterFiles'],replacements=replacements,events=events,
            selectionReadBudgetSeconds=prepared['build']['selectionReadBudgetSeconds'],configurationWrites=False,
            backupDispatched=False,restoreDispatched=False,retryPermitted=False)
        richpin=publication.exclusive_bytes(rich_path,publication.canonical(rich));core=dict(rich,privateEvidencePin=richpin)
        raw=publication.canonical(core);pin=dict(file=output.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        pending=continuation.original.PendingCoreRecords(task,pin,core)
        load_completed_transition(pending,private,pin,prepared['base'])
        publication.exclusive_bytes(output,raw)
        return dict(status='PASS',report=output.name,configurationWrites=False,backupDispatched=False,restoreDispatched=False)
    except BaseException as error:
        failure=dict(schemaVersion='MainProgramSpugResourceTransitionFailure/v1',status='FAILED',**bound,attemptPin=attempt,
            stage=stage,events=events,replacements=replacements,nativeReceiptPins=deepcopy(transport.receipts),
            errorType=type(error).__name__,errorCode=str(error),retryPermitted=False)
        publication.exclusive_bytes(private/(stem+('.finalization-failure.private.json' if rich_path.exists() else '.private.json')),publication.canonical(failure))
        raise ValueError('SPUG_RESOURCE_TRANSITION_FAILED_CHECK_PRIVATE_EVIDENCE') from None


def load_completed_transition(records,private,reference,base):
    core=records.pinned(reference);pins=[]
    need(type(core) is dict and core.get('schemaVersion')=='MainProgramSpugResourceTransition/v1' and core.get('status')=='PASS','COMPLETED_TRANSITION_REQUIRED')
    inputs=records.pinned(core['transitionInputsPin'])
    prepared=_prepare(records,private,inputs,core['transitionInputsPin'],verify_checkout=False,base=base)
    need(reference['file']==inputs['outputFile'],'TRANSITION_OUTPUT_CHANGED')
    rich=continuation.private_json(private,core['privateEvidencePin'],pins)
    fields={'schemaVersion','status',*binding(prepared),'attemptPin','entryBefore','entryAfter','entryEnvironmentSha256',
            'beforeFiles','afterFiles','replacements','events','selectionReadBudgetSeconds','configurationWrites','backupDispatched','restoreDispatched','retryPermitted'}
    need(set(rich)==fields and core==dict(rich,privateEvidencePin=core['privateEvidencePin']) and
         all(rich[k]==v for k,v in binding(prepared).items()) and all(rich[k] is False for k in
         ('configurationWrites','backupDispatched','restoreDispatched','retryPermitted')),'TRANSITION_EVIDENCE_CHANGED')
    need(rich['entryBefore']==prepared['entryBefore'] and rich['entryEnvironmentSha256']==prepared['environment'] and
         rich['beforeFiles']==prepared['beforeFiles'] and rich['afterFiles']==prepared['afterFiles'] and
         rich['selectionReadBudgetSeconds']==prepared['build']['selectionReadBudgetSeconds'],'TRANSITION_STATE_CHANGED')
    dependency.validate_reload_identity(rich['entryBefore'],rich['entryAfter'])
    attempt=continuation.private_json(private,rich['attemptPin'],pins)
    need(set(attempt)=={'schemaVersion',*binding(prepared),'gatePin','inputPins','retryPermitted'} and
         attempt['schemaVersion']=='MainProgramSpugResourceTransitionAttempt/v1' and attempt['retryPermitted'] is False and
         all(attempt[k]==v for k,v in binding(prepared).items()),'ATTEMPT_CHANGED')
    need(continuation.private_json(private,attempt['gatePin'],pins)==dict(**binding(prepared),retryPermitted=False),'GATE_CHANGED')
    # Historical candidate checkout pins are resolved only through this build's exact custody.
    custody=continuation.private_json(private,prepared['build']['sourceCustodyPin'],pins)
    mapping={r['originalPin']['path']:r for r in custody['entries']}
    expected=verifier().unique_pins(prepared['inputPins']+[r['originalPin'] for r in custody['entries']])
    need(type(attempt['inputPins']) is list and len({p['path'] for p in attempt['inputPins']})==len(attempt['inputPins']) and
         {p['path']:p for p in attempt['inputPins']}=={p['path']:p for p in expected},'ATTEMPT_INPUT_SET_CHANGED')
    verifier().verify_historical_inputs(private,attempt['inputPins'],mapping,pins)
    names=[r['relativePath'] for r in prepared['changes']];audit=Path(private)/(prepared['stem']+'-originals')
    originals=continuation.private_json(private,publication.file_pin(audit/'originals.json'),pins)
    need(type(originals) is list and len(originals)==len(names) and len(rich['replacements'])==len(names),'ORIGINAL_SET_CHANGED')
    for index,(name,original,result) in enumerate(zip(names,originals,rich['replacements'])):
        need(set(original)=={'relativePath','beforePin','archivedPin'} and original['relativePath']==name and
             original['beforePin']==dict(path=str(Path(prepared['runtime'])/name),**prepared['beforeFiles'][name]),'ORIGINAL_BINDING_CHANGED')
        raw=continuation.private_raw(private,original['archivedPin'],pins)
        need(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==prepared['beforeFiles'][name],'ORIGINAL_BYTES_CHANGED')
        actual=continuation.private_json(private,publication.file_pin(audit/('replacement-'+str(index)+'.json')),pins)
        need(actual==result and set(result)=={'relativePath','previousPin','installedPin'} and result['relativePath']==name and
             result['previousPin']==original['archivedPin'] and
             result['installedPin']==dict(path=str(Path(prepared['runtime'])/name),**prepared['afterFiles'][name]),'REPLACEMENT_CHANGED')
        need(continuation.private_json(private,publication.file_pin(audit/('dispatch-'+str(index)+'.json')),pins)==
             dict(relativePath=name,state='DISPATCHED_OUTCOME_UNKNOWN'),'DISPATCH_CHANGED')
    need(continuation.private_json(private,publication.file_pin(Path(private)/(prepared['stem']+'.reload-intent.private.json')),pins)==
         dict(**binding(prepared),entryBefore=prepared['entryBefore']),'RELOAD_INTENT_CHANGED')
    labels=['before',*['guard-'+str(i) for i in range(len(names)+1)],'reload','after']
    need(type(rich['events']) is list and [r.get('label') for r in rich['events']]==labels and
         all(set(r)=={'label','pin'} for r in rich['events']),'EVENT_SET_CHANGED')
    for row in rich['events']:
        label=row['label'];event=continuation.private_json(private,row['pin'],pins)
        need(set(event)=={'label','result','nativeReceiptPins'} and event['label']==label,'EVENT_CHANGED')
        if label=='reload':program=reload_program(prepared);need(event['result']==rich['entryAfter'],'RELOAD_RESULT_CHANGED')
        else:
            count=int(label.split('-')[1]) if label.startswith('guard-') else (len(names) if label=='after' else 0)
            files=mixed_files(prepared,set(names[:count]));identity=rich['entryAfter'] if label=='after' else rich['entryBefore']
            validate_guard(prepared,event['result'],files,identity);program=guard_program(prepared,files,identity)
            if label=='before':need(event['result']==prepared['observation']['result'],'OBSERVATION_RESULT_CHANGED')
        validate_native(prepared,private,label,program,event['result'],event['nativeReceiptPins'],pins)
    pins=verifier().unique_pins(prepared['inputPins']+records.path_pins()+pins)
    for pin in pins:publication.verify_bytes(pin)
    return dict(afterFiles=rich['afterFiles'],entryAfter=rich['entryAfter'],entryEnvironmentSha256=rich['entryEnvironmentSha256'],
        selectionReadBudgetSeconds=rich['selectionReadBudgetSeconds'],inputPins=pins)


def parser():
    value=argparse.ArgumentParser(description=__doc__);value.add_argument('--inputs',required=True)
    group=value.add_mutually_exclusive_group();group.add_argument('--observe',action='store_true');group.add_argument('--apply',action='store_true')
    value.add_argument('--task',type=Path,default=TASK);value.add_argument('--private',type=Path,default=PRIVATE);return value


def run_request(task,private,inputs_file,*,observe=False,apply=False):
    need(not(observe and apply),'MODE_CONFLICT')
    prepared=prepare_transition(task,private,inputs_file,allow_unobserved=observe)
    if observe:return dict(status='OBSERVED',observationPin=observe_transition(private,prepared))
    if apply:return execute_transition(task,private,prepared)
    return dict(status='PREPARED_NOT_APPLIED',runtimeWrites=False,transportCalled=False)


if __name__=='__main__':
    args=parser().parse_args()
    try:print(json.dumps(run_request(args.task,args.private,args.inputs,observe=args.observe,apply=args.apply)))
    except Exception as error:print(json.dumps(dict(status='FAILED',errorType=type(error).__name__,errorCode=str(error))));raise SystemExit(1)
