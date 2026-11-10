"""Complete the pinned c772 runtime dependencies; never republish configuration.

Local preparation is the default. Activation has one permitted resource change
and one exact supervised entry reload. All original publication evidence stays.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation
import main_program_spug_resource_activation as activation
import main_program_installation_selection as contract

TASK, PRIVATE = publication.TASK, publication.PRIVATE
ADDITIONS = ('smallapp_simple.py','smallapp_progress_remote.py','smallapp-ui/preview/style.css')
ROOTS = ('smallapp_entry.py','smallapp-entry.locations.conf','smallapp-ui/index.html')
PLATFORM = ('apps','django','libs')
ALLOWED = frozenset(publication.PRODUCT_FILES) | frozenset(ADDITIONS)


def need(condition, code):
    if not condition:raise ValueError('SPUG_DEPENDENCY_'+code)


def relative_path(value):
    need(type(value) is str and value and '\\' not in value,'PATH_INVALID')
    path=PurePosixPath(value)
    need(str(path)==value and not path.is_absolute() and '..' not in path.parts and
         not any(c in value for c in ':?#\x00'),'PATH_ALIAS')
    return path


def source_file(root,name):
    path=Path(root)/str(relative_path(name))
    need(path.is_file(),'FILE_MISSING')
    continuation.safe_path(path)
    need(path.resolve(strict=True)==path,'FILE_ALIAS')
    return path


def content_pin(path):
    actual=publication.file_pin(path)
    return {key:actual[key] for key in ('bytes','sha256')}


class WebReferences(HTMLParser):
    def __init__(self):super().__init__();self.references=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='script' and 'src' in values:self.references.append(values['src'])
        if tag=='link' and values.get('rel')=='stylesheet':self.references.append(values.get('href'))


def inspect_runtime_dependencies(root=None, *, sources=None):
    """Inspect real lazy imports, the executable carrier and browser resources.

    This is a deliberately bounded product contract, not an import fallback.
    Unreviewed dynamic loading or a new local resource requires a new contract.
    """
    need((root is None)!=(sources is None),'SOURCE_MODE_INVALID')
    if sources is None:root=Path(root).resolve(strict=True)
    else:need(type(sources) is dict and set(sources)==ALLOWED and all(type(raw) is bytes for raw in sources.values()),'SOURCE_CUSTODY_SET_INVALID')
    pending=list(ROOTS);files={};edges=set();platform=set()
    def edge(origin,kind,target):
        target=str(relative_path(target));edges.add((origin,kind,target));pending.append(target)
    while pending:
        name=pending.pop(0)
        if name in files:continue
        need(name in ALLOWED,'UNREVIEWED_LOCAL_RESOURCE')
        raw=source_file(root,name).read_bytes() if sources is None else sources[name]
        text=raw.decode('utf-8-sig');files[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        if name.endswith('.py'):
            tree=ast.parse(text)
            for node in ast.walk(tree):
                modules=[]
                if isinstance(node,ast.Import):modules=[a.name for a in node.names]
                elif isinstance(node,ast.ImportFrom):
                    need(node.level==0 and node.module,'RELATIVE_IMPORT_UNREVIEWED');modules=[node.module]
                for module in modules:
                    first=module.split('.')[0];local=first+'.py'
                    need(first!='importlib','DYNAMIC_IMPORT_UNREVIEWED')
                    if (local in sources if sources is not None else (root/local).is_file()):edge(name,'LOCAL_IMPORT',local)
                    elif first in PLATFORM:platform.add(first)
                    else:need(first in sys.stdlib_module_names,'IMPORT_UNRESOLVED')
                if isinstance(node,ast.Call):
                    call=ast.unparse(node.func)
                    need(call not in ('__import__','importlib.import_module','importlib.util.spec_from_file_location'),
                         'DYNAMIC_IMPORT_UNREVIEWED')
                    if (isinstance(node.func,ast.Attribute) and node.func.attr=='with_name' and
                            any(isinstance(n,ast.Name) and n.id=='__file__' for n in ast.walk(node.func.value))):
                        need(ast.unparse(node.func.value)=='Path(__file__)' and len(node.args)==1 and
                             isinstance(node.args[0],ast.Constant) and type(node.args[0].value) is str,
                             'EXECUTED_FILE_UNREVIEWED')
                        edge(name,'EXECUTED_FILE',node.args[0].value)
        elif name.endswith('.html'):
            parsed=WebReferences();parsed.feed(text)
            for target in parsed.references:edge(name,'WEB_RESOURCE',str(PurePosixPath(name).parent/relative_path(target)))
        elif name.endswith('.css'):
            # Current product has no further CSS loads. New ones need explicit
            # parser/coverage work instead of silently leaving the release.
            need(not re.search(r'url\s*\(|@import\b',text,re.I),'CSS_RESOURCE_UNREVIEWED')
        elif name.endswith('.js'):
            need(not re.search(r'\bimport\s*(?:\(|[^\n]*\bfrom\s*)',text),'JS_IMPORT_UNREVIEWED')
    need(set(files)==ALLOWED,'MANIFEST_INCOMPLETE')
    return dict(roots=list(ROOTS),edges=[dict(zip(('from','kind','to'),row)) for row in sorted(edges)],
        files={name:files[name] for name in sorted(files)},additionalFiles=sorted(ADDITIONS),
        externalPlatformRoots=sorted(platform))


def validate_manifest_coverage(root,files):
    graph=inspect_runtime_dependencies(root)
    need(type(files) is dict and set(files)=={'ops/spug/'+name for name in graph['files']},'MANIFEST_INCOMPLETE')
    need(files=={'ops/spug/'+name:pin for name,pin in graph['files'].items()},'MANIFEST_CHANGED')
    return graph


def deployment_difference(runtime,graph):
    need(set(graph['files'])==ALLOWED,'MANIFEST_INCOMPLETE');changes=[]
    for name,expected in graph['files'].items():
        path=source_file(Path(runtime),name);actual=content_pin(path)
        if actual==expected:continue
        need(name=='smallapp_simple.py','UNRELATED_RUNTIME_CHANGED')
        changes.append(dict(relativePath=name,beforePin=publication.file_pin(path),afterPin=dict(path=str(path),**expected)))
    need(len(changes)==1,'SIMPLE_TRANSITION_REQUIRED')
    return changes


def validate_checkout_observation(private,reference,source_commit,workspace):
    pins=[];value=continuation.private_json(private,reference,pins)
    need(set(value)=={'schemaVersion','status','sourceCommit','workspace','commands','workingTreeClean','indexClean','sourceWrites'} and
         value['schemaVersion']=='SpugDependencyCheckoutObservation/v1' and value['status']=='OBSERVED' and
         value['sourceCommit']==source_commit and Path(value['workspace'])==Path(workspace) and
         value['workingTreeClean'] is True and value['indexClean'] is True and value['sourceWrites'] is False,
         'CHECKOUT_OBSERVATION_INVALID')
    commands={'head':['git','rev-parse','HEAD'],'status':['git','status','--porcelain=v1','--untracked-files=all'],
              'worktree-diff':['git','diff','--exit-code','--quiet'],'index-diff':['git','diff','--cached','--exit-code','--quiet']}
    need([r.get('label') for r in value['commands']]==list(commands),'CHECKOUT_COMMANDS_INVALID')
    for row in value['commands']:
        request=continuation.private_json(private,row['requestPin'],pins)
        need(row['actualExitCode']==0 and type(row['actualExitCode']) is int and
             request==dict(argv=commands[row['label']],cwd=str(workspace),gitOptionalLocks='0'),'CHECKOUT_NATIVE_INVALID')
        stdout=continuation.private_raw(private,row['stdoutPin'],pins);stderr=continuation.private_raw(private,row['stderrPin'],pins)
        need(stderr==b'' and (stdout.decode('utf-8').strip()==source_commit if row['label']=='head' else stdout==b''),
             'CHECKOUT_NOT_CLEAN')
    return pins


def validate_failed_continuation(prepared,private,failure,pins,*,historical_source_custody=None):
    """Read the real successful prefix and the failed native final verification.

    No success object is synthesized for the frozen v3 full-success reader.
    """
    c=continuation;binding=c.continuation_binding(prepared)
    need(failure.get('schemaVersion')=='MainProgramSpugPublicationFailure/v3' and failure.get('status')=='FAILED' and
         failure.get('stage')=='spug-verify' and failure.get('errorCode')=='MAIN_SPUG_CONTINUATION_CONTAINER_PROGRAM_FAILED' and
         failure.get('retryPermitted') is False and all(failure.get(k)==v for k,v in binding.items()) and
         failure.get('originalStages')==prepared['originalFailure']['stages'],'C1_FAILURE_BINDING_INVALID')
    attempt=c.private_json(private,failure['attemptPin'],pins)
    need(attempt.get('schemaVersion')=='MainProgramSpugPublicationAttempt/v3' and
         all(attempt.get(k)==v for k,v in binding.items()) and attempt.get('stageOrder')==c.continuation_schedule() and
         attempt.get('originalAttemptPin')==prepared['inputs']['originalAttemptPin'] and attempt.get('retryPermitted') is False,
         'C1_ATTEMPT_INVALID')
    mapped=None
    if historical_source_custody is not None:
        custody=historical_source_custody
        need(type(custody) is dict and set(custody)=={'schemaVersion','continuationAttemptPin','dependencyAttemptPin','entries'} and
             custody['schemaVersion']=='MainProgramSpugVerificationSourceCustody/v1' and
             custody['continuationAttemptPin']==failure['attemptPin'] and
             type(custody['entries']) is list and len(custody['entries'])==1 and
             set(custody['entries'][0])=={'originalPin','preservedPin'},'C1_HISTORICAL_SOURCE_CUSTODY_INVALID')
        mapped=custody['entries'][0];old=mapped['originalPin'];kept=mapped['preservedPin']
        dependency_attempt=c.private_json(private,custody['dependencyAttemptPin'],pins)
        need(dependency_attempt.get('schemaVersion')=='MainProgramSpugRuntimeDependencyAttempt/v1' and
             dependency_attempt.get('continuationFailurePin') is not None and
             c.private_json(private,dependency_attempt['continuationFailurePin'],pins)==failure and
             old in attempt['inputPins'] and old in dependency_attempt['inputPins'] and
             Path(old['path']).is_absolute() and Path(old['path']).parts[-4:]==
             ('doc','tasks','20261106-spug-prod-incremental-to-two-targets','main_program_installation_selection.py') and
             old['path']!=kept['path'] and all(old[k]==kept[k] for k in ('bytes','sha256')),
             'C1_HISTORICAL_SOURCE_MAPPING_INVALID')
        c.private_raw(private,kept,pins)
    for pin in attempt['inputPins']:
        if mapped is not None and pin==mapped['originalPin']:continue
        publication.verify_bytes(pin);pins.append(pin)
    for key in ('claimPin','gatePin'):
        value=c.private_json(private,attempt[key],pins)
        need(all(value.get(k)==v for k,v in binding.items()),'C1_CLAIM_CHANGED')
    need([r.get('stage') for r in failure['stages']]==c.continuation_schedule() and
         len({r['resultPin']['path'] for r in failure['stages']})==7,'C1_STAGE_SET_CHANGED')
    custody=None;published=None
    for row in failure['stages']:
        raw=c.private_json(private,row['resultPin'],pins);name=row['stage'];result=raw['result']
        need(set(raw)=={'schemaVersion',*binding,'stage','requestPin','result','nativeReceiptPins'} and
             raw['schemaVersion']=='MainProgramSpugPublicationStage/v3' and raw['stage']==name and
             all(raw.get(k)==v for k,v in binding.items()),'C1_STAGE_BINDING_INVALID')
        request=c.private_json(private,raw['requestPin'],pins)
        need(set(request)=={'schemaVersion',*binding,'stage','programPin','retryPermitted'} and
             request['schemaVersion']=='MainProgramSpugPublicationDispatch/v3' and request['stage']==name and
             request['retryPermitted'] is False and all(request.get(k)==v for k,v in binding.items()),'C1_DISPATCH_INVALID')
        native=c.validate_native_receipts(private,raw['nativeReceiptPins'],pins);c.validate_native_targets(prepared,native)
        program=None
        if name=='spug-configuration-publish':
            need(result.get('status')=='PASS' and custody is not None,'C1_PUBLISH_NOT_SUCCESSFUL')
            c.validate_write_results(prepared,private,result,pins);c.validate_publish_native(prepared,private,result,native,pins)
            published=result;need(request['programPin'] is None,'C1_PUBLISH_PROGRAM_UNEXPECTED')
        elif name.startswith('host-verify-'):
            host=name.rsplit('-',1)[1];program=c.original.program('host',host,'verify',prepared['originalSpec']['hostSpecs'][host])
            need(result.get('status')=='PASS','C1_HOST_NOT_SUCCESSFUL')
            publication.validate_verify_stage(prepared['context'],prepared['context']['generation'],host,result)
        elif name=='spug-custody':
            need(result.get('status')=='PASS','C1_CUSTODY_NOT_SUCCESSFUL')
            custody=result['rows'];c.check_custody_barrier(custody,7);program=c.container_program(prepared,'custody')
            for kept in custody:
                if kept['custody'] is not None:c.private_raw(private,kept['custody'],pins)
        else:
            need(name in ('spug-continuation-preflight','spug-verify'),'C1_STAGE_UNKNOWN')
            program=c.original.program('spug',None,'verify' if name=='spug-verify' else 'preflight',prepared['originalSpec']['spugSpec'])
            if name=='spug-continuation-preflight':
                need(result.get('status')=='PASS','C1_PREFLIGHT_NOT_SUCCESSFUL')
                commands=[(v,q,o) for v,q,o in native if v['label']!='inspect']
                need([v['label'] for v,q,o in commands]==['guard-before-custody','spug-continuation-preflight'],
                     'C1_PREFLIGHT_GUARD_MISSING')
                v,q,o=commands[0]
                need(c.private_raw(private,v['stdinPin'],pins)==c.container_program(prepared,'guard-before-custody').encode() and
                     o.get('status')=='PASS' and o.get('entryIdentity')==prepared['mountObservation']['entryIdentity'],
                     'C1_PREFLIGHT_GUARD_CHANGED')
            else:
                need(result==dict(status='UNKNOWN',errorType='ValueError',errorCode='MAIN_SPUG_CONTINUATION_CONTAINER_PROGRAM_FAILED'),
                     'C1_FAILURE_WRAPPER_CHANGED')
        if program is not None:
            encoded=program.encode('utf-8')
            need(c.private_raw(private,request['programPin'],pins)==encoded,'C1_PROGRAM_CHANGED')
            matches=[(v,o) for v,q,o in native if v['stdinPin'] is not None and c.private_raw(private,v['stdinPin'],pins)==encoded]
            need(len(matches)==1,'C1_NATIVE_PROGRAM_MISSING');v,out=matches[0]
            if name=='spug-verify':
                need(out.get('status')=='FAILED' and out.get('phase')=='verify' and
                     out.get('errorCode')=='SIMPLE_CONFIGURATION_INVALID' and out.get('errorType')=='Refused' and
                     out.get('sourceCommit')==binding['sourceCommit'] and out.get('completedWrites')==[] and
                     out.get('backupDispatched') is False and out.get('restoreDispatched') is False,'C1_LAST_NATIVE_FAILURE_CHANGED')
            elif name=='spug-custody':c.validate_container_custody(prepared,custody,out)
            else:
                actual=dict(out)
                if name.startswith('spug-'):actual['protectedSpugUnchanged']=True
                need(actual==result,'C1_NATIVE_RESULT_CHANGED')
    need(published is not None and failure.get('writeStates')==published['writeResults'] and
         failure.get('stateRecords')==published['stateRecords'] and failure.get('custody')==custody,'C1_APPLIED_SUMMARY_CHANGED')
    return dict(appliedCount=7,hostVerifications=3,lastNativeError='SIMPLE_CONFIGURATION_INVALID',lastNativeExitCode=0)


def validate_runner_exit(private,observation,prepared,pins):
    c=continuation;value=observation
    need(set(value)=={'schemaVersion','status','completionPin','dispatchPin','originalRunnerPid','originalRunnerAbsent',
                     'query','configurationWrites','remoteServerCalls'} and
         value['schemaVersion']=='SpugContinuationRunnerTerminalObservation/v1' and value['status']=='OBSERVED' and
         type(value['originalRunnerPid']) is int and value['originalRunnerAbsent'] is True and
         value['configurationWrites'] is False and value['remoteServerCalls']==0,'RUNNER_OBSERVATION_INVALID')
    completion=c.private_json(private,value['completionPin'],pins);dispatch=c.private_json(private,value['dispatchPin'],pins)
    pid=value['originalRunnerPid']
    need(completion.get('hostPid')==dispatch.get('hostPid')==pid and completion.get('terminal') is True and
         completion.get('actualExitCode')==1 and completion.get('status')=='FAILED' and completion.get('corePin') is None and
         completion.get('sourcesAndProofsUnchanged') is True and completion.get('automaticRetryPermitted') is False,
         'RUNNER_COMPLETION_INVALID')
    argv=dispatch['argv'];expected=[str(Path(continuation.__file__)),'--task',str(TASK),'--private',str(private),
                                   '--inputs',prepared['inputPin']['file'],'--apply']
    need(argv[1:4]==['-X','utf8','-B'] and argv[4:]==expected and dispatch.get('automaticRetryPermitted') is False,
         'RUNNER_DISPATCH_CHANGED')
    for key in ('stdoutPin','stderrPin'):c.private_raw(private,completion[key],pins)
    query=value['query'];need(query['actualExitCode']==0,'RUNNER_QUERY_FAILED')
    request=c.private_json(private,query['requestPin'],pins)
    program=c.private_raw(private,request['programPin'],pins)
    validate_runner_query_request(request,program,pid,value['completionPin'],value['dispatchPin'])
    need(c.private_json(private,query['stdoutPin'],pins)==dict(pid=pid,count=0) and
         c.private_raw(private,query['stderrPin'],pins)==b'','RUNNER_STILL_PRESENT')


def validate_runner_query_request(request,program,pid,completion_pin,dispatch_pin):
    expected=("$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
              "$spugOwnedProcesses=@(Get-CimInstance Win32_Process -Filter 'ProcessId = "+str(pid)+"'); "
              "[Console]::Write((ConvertTo-Json -Compress -InputObject @{pid="+str(pid)+"; count=$spugOwnedProcesses.Count}));")
    need(set(request)=={'argv','completionPin','dispatchPin','programPin'} and request['completionPin']==completion_pin and
         request['dispatchPin']==dispatch_pin and program==expected.encode('utf-8') and
         request['argv']==['powershell.exe','-NoProfile','-Command',expected],'RUNNER_QUERY_COMMAND_CHANGED')


def load_source_custody(private,reference,base,base_pin,*,verify_checkout):
    pins=[];value=continuation.private_json(private,reference,pins)
    need(set(value)=={'schemaVersion','baseResourceBuildPin','entries'} and
         value['schemaVersion']=='MainProgramSpugRuntimeDependencySourceCustody/v1' and
         value['baseResourceBuildPin']==base_pin,'SOURCE_CUSTODY_INVALID')
    root=Path(base['worktree'])/'ops/spug'
    rows=value['entries'];need(type(rows) is list and len(rows)==16 and
        all(type(r) is dict and set(r)=={'originalPin','preservedPin'} and type(r['originalPin']) is dict and
            set(r['originalPin'])=={'path','bytes','sha256'} and type(r['originalPin']['path']) is str for r in rows),
        'SOURCE_CUSTODY_SET_INVALID')
    originals={r['originalPin']['path'] for r in rows}
    if verify_checkout:
        helpers={str(Path(__file__)),str(Path(__file__).with_name('test_spug_runtime_dependency_completion.py'))}
    else:
        helpers=historical_helper_paths(originals)
    required={str(root/name) for name in ALLOWED}|helpers
    need(
        {r['originalPin']['path'] for r in rows}==required and len({r['preservedPin']['path'] for r in rows})==16,
        'SOURCE_CUSTODY_SET_INVALID')
    mapping={}
    for row in rows:
        original=row['originalPin'];raw=continuation.private_raw(private,row['preservedPin'],pins)
        need(set(original)=={'path','bytes','sha256'} and original['bytes']==len(raw) and
             original['sha256']==hashlib.sha256(raw).hexdigest() and original['path']!=row['preservedPin']['path'],
             'SOURCE_CUSTODY_BYTES_CHANGED')
        if verify_checkout:publication.verify_bytes(original);pins.append(original)
        mapping[original['path']]=dict(originalPin=original,raw=raw)
    graph=inspect_runtime_dependencies(sources={name:mapping[str(root/name)]['raw'] for name in ALLOWED})
    return graph,mapping,pins


def historical_helper_paths(paths):
    """The original two roles are rooted by custody, never by this reader's location."""
    names={'spug_runtime_dependency_completion.py','test_spug_runtime_dependency_completion.py'}
    selected={path for path in paths if Path(path).name in names}
    need(len(selected)==2 and len({Path(path).parent for path in selected})==1 and
         {Path(path).name for path in selected}==names and
         all(Path(path).is_absolute() and Path(path).parts[-4:-1]==('doc','tasks','20261106-spug-prod-incremental-to-two-targets')
             for path in selected),'SOURCE_CUSTODY_HELPER_ROLES_INVALID')
    return selected


def validate_coverage(private,reference,root,graph,pins,*,source_custody=None):
    need(type(reference) is dict,'COVERAGE_REQUIRED')
    value=continuation.private_json(private,reference,pins)
    need(set(value)=={'schemaVersion','status','actualExitCode','actualPassed','actualSkipped','inputPins','logPin'} and
         value['schemaVersion']=='MainProgramSpugRuntimeDependencyCoverage/v1' and value['status']=='PASS' and
         type(value['actualExitCode']) is int and value['actualExitCode']==0 and type(value['actualPassed']) is int and
         value['actualPassed']>0 and value['actualSkipped']==0,'COVERAGE_NOT_SUCCESSFUL')
    need(type(value['inputPins']) is list and len({p['path'] for p in value['inputPins']})==len(value['inputPins']),
         'COVERAGE_INPUTS_INVALID')
    indexed={str(Path(p['path'])):p for p in value['inputPins']}
    helpers={str(Path(__file__)),str(Path(__file__).with_name('test_spug_runtime_dependency_completion.py'))} if source_custody is None else historical_helper_paths(source_custody)
    required=[Path(root)/name for name in graph['files']]+[Path(path) for path in helpers]
    need(set(indexed)=={str(path) for path in required},'COVERAGE_INPUT_SET_INVALID')
    for path in required:
        actual=publication.file_pin(path) if source_custody is None else source_custody[str(path)]['originalPin']
        need(indexed.get(str(path))==actual,'COVERAGE_INPUT_MISSING_OR_CHANGED')
    if source_custody is None:
        for reference in value['inputPins']:publication.verify_bytes(reference);pins.append(reference)
    log=continuation.private_raw(private,value['logPin'],pins).decode('utf-8')
    counts=re.findall(r'\b(\d+) passed\b',log)
    need(counts and int(counts[-1])==value['actualPassed'] and not re.search(r'\b[1-9][0-9]* (failed|errors?|skipped)\b',log),
         'COVERAGE_NATIVE_LOG_CHANGED')


def make_dependency_completion(task,private,base_resource_build_pin,coverage_evidence_pin,source_checkout_evidence_pin,
                               source_custody_pin=None,*,verify_checkout=True):
    records=contract.Records(task);base=records.pinned(base_resource_build_pin)
    publication.resource_files(base);root=Path(base['worktree'])/'ops/spug'
    need(type(coverage_evidence_pin) is dict,'COVERAGE_REQUIRED')
    need(type(source_custody_pin) is dict,'SOURCE_CUSTODY_REQUIRED')
    graph,mapping,pins=load_source_custody(private,source_custody_pin,base,base_resource_build_pin,verify_checkout=verify_checkout)
    validate_coverage(private,coverage_evidence_pin,root,graph,pins,source_custody=mapping)
    validate_checkout_observation(private,source_checkout_evidence_pin,base['sourceCommit'],Path(base['worktree']))
    for name,pin in base['files'].items():need(graph['files'][name.removeprefix('ops/spug/')]==pin,'BASE_ELEVEN_CHANGED')
    return dict(schemaVersion='MainProgramSpugRuntimeDependencyCompletion/v1',status='PASS',sourceCommit=base['sourceCommit'],
        baseResourceBuildPin=base_resource_build_pin,**graph,coverageEvidencePin=coverage_evidence_pin,
        sourceCheckoutEvidencePin=source_checkout_evidence_pin,sourceCustodyPin=source_custody_pin)


def validate_dependency_completion(records,private,reference,*,verify_checkout=True):
    value=records.pinned(reference)
    need(set(value)=={'schemaVersion','status','sourceCommit','baseResourceBuildPin','roots','edges','files','additionalFiles',
                     'externalPlatformRoots','coverageEvidencePin','sourceCheckoutEvidencePin','sourceCustodyPin'},'COMPLETION_FIELDS_INVALID')
    expected=make_dependency_completion(records.task,private,value['baseResourceBuildPin'],value['coverageEvidencePin'],
                                        value['sourceCheckoutEvidencePin'],value['sourceCustodyPin'],verify_checkout=verify_checkout)
    need(value==expected,'COMPLETION_CHANGED')
    loader=publication.validate_resource_build if verify_checkout else publication.published_resource_evidence
    base,base_pins=loader(records,value['baseResourceBuildPin'],private)
    pins=list(base_pins)
    pins+=validate_checkout_observation(private,value['sourceCheckoutEvidencePin'],value['sourceCommit'],Path(base['worktree']))
    graph,mapping,kept=load_source_custody(private,value['sourceCustodyPin'],base,value['baseResourceBuildPin'],verify_checkout=verify_checkout)
    pins+=kept
    validate_coverage(private,value['coverageEvidencePin'],Path(base['worktree'])/'ops/spug',graph,pins,source_custody=mapping)
    return value,base,pins


def validate_runtime_observation(private,value,prepared,failure_pin,pins):
    c=continuation
    need(value.get('schemaVersion')=='SpugRuntimeDependencyObservation/v1' and value.get('status')=='OBSERVED' and
         value.get('failurePin')==failure_pin and value.get('originalAttemptPin')==prepared['inputs']['originalAttemptPin'] and
         value.get('allInstalledConfigurationsReadBack') is True and value.get('businessSpugInstancesUnchanged') is True and
         value.get('writeCount')==7 and value.get('remoteServerCalls')==0 and value.get('runtimeWrites') is False,
         'RUNTIME_OBSERVATION_INVALID')
    need([r['label'] for r in value['commands']]==['instances-before','runtime','instances-after'],'RUNTIME_COMMAND_SET_CHANGED')
    result=value['result'];outputs=[]
    for row in value['commands']:
        request=c.private_json(private,row['requestPin'],pins)
        output=c.private_json(private,row['stdoutPin'],pins);stderr=c.private_raw(private,row['stderrPin'],pins)
        need(row['actualExitCode']==0 and stderr==b'','RUNTIME_NATIVE_FAILED');outputs.append(output)
        argv=request['argv']
        if row['label']=='runtime':
            need(argv[:7]==[publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-'] and
                 len(argv)==8 and request.get('stdinPin') is not None and output==result,'RUNTIME_IMPORT_RECEIPT_CHANGED')
            c.private_raw(private,request['stdinPin'],pins)
        else:
            need(argv==[publication.DOCKER,'inspect',publication.CONTAINER,prepared['mountObservation']['protectedContainerId']],
                 'RUNTIME_INSTANCE_COMMAND_CHANGED')
            c.verify_instances(output,prepared['mountObservation'])
    need(outputs[0]==outputs[2],'RUNTIME_INSTANCES_CHANGED')
    expected=[]
    for row in prepared['originalSpec']['spugSpec']['writes']:
        raw=publication.canonical(row['value']);expected.append(dict(path=row['path'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    need(result.get('status')=='OBSERVED' and result.get('configPins')==expected and
         result.get('entryIdentity')==prepared['mountObservation']['entryIdentity'] and
         result.get('parsedConfiguration')==dict(status='FAILED',errorType='Refused',errorCode='SIMPLE_CONFIGURATION_INVALID') and
         result.get('configurationKeys')==['bindings','catalogueRestoreBindings','nas','servers'] and result.get('serverCount')==3 and
         result.get('runtimeWrites') is False and result.get('backupDispatched') is False and result.get('restoreDispatched') is False,
         'RUNTIME_STATE_CHANGED')
    imported=result['importedSources']
    need([r.get('module') for r in imported]==['smallapp_adapter','smallapp_entry','smallapp_simple'],'RUNTIME_MODULE_SET_CHANGED')
    for row in imported:
        name=row['module']+'.py';reference=row['sourcePin'];contract.remote_pin(reference)
        need(reference['path']=='/opt/intruoyi-spug/'+name,'RUNTIME_MODULE_ORIGIN_CHANGED')
        if name!='smallapp_simple.py':
            need({k:reference[k] for k in ('bytes','sha256')}==prepared['context']['resource']['files']['ops/spug/'+name],
                 'RUNTIME_BASE_MODULE_CHANGED')
    return result


def prepare_value(records,private,inputs,input_pin):
    fields={'schemaVersion','sourceCommit','dependencyCompletionPin','baseResourceActivationPin','continuationInputsPin',
            'continuationFailurePin','continuationCompletionPin','runnerExitObservationPin','runtimeObservationPin','operationId','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and
         inputs['schemaVersion']=='MainProgramSpugRuntimeDependencyActivationInputs/v1' and
         type(inputs['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',inputs['sourceCommit']) and
         type(inputs['operationId']) is str and re.fullmatch('r[1-9][0-9]*',inputs['operationId']) and
         inputs['outputFile']=='main-program-spug-runtime-dependency-activation-'+inputs['sourceCommit'][:7]+'-'+inputs['operationId']+'.json',
         'ACTIVATION_INPUTS_INVALID')
    private=Path(private);completion,base,pins=validate_dependency_completion(records,private,inputs['dependencyCompletionPin'])
    need(completion['sourceCommit']==inputs['sourceCommit'],'RESOURCE_COMMIT_CHANGED')
    c1inputs=records.pinned(inputs['continuationInputsPin'])
    c1=continuation.prepare_value(records,private,c1inputs,inputs['continuationInputsPin'])
    need(c1inputs['spugResourceBuildPin']==completion['baseResourceBuildPin'] and
         c1inputs['resourceActivationPin']==inputs['baseResourceActivationPin'],'C1_RESOURCE_BINDING_CHANGED')
    failure=continuation.private_json(private,inputs['continuationFailurePin'],pins)
    prefix=validate_failed_continuation(c1,private,failure,pins)
    runner=records.pinned(inputs['runnerExitObservationPin'])
    need(runner['completionPin']==inputs['continuationCompletionPin'],'RUNNER_COMPLETION_BINDING_CHANGED')
    validate_runner_exit(private,runner,c1,pins)
    runtime=validate_runtime_observation(private,records.pinned(inputs['runtimeObservationPin']),c1,inputs['continuationFailurePin'],pins)
    installation=records.pinned(inputs['baseResourceActivationPin'])
    need(installation==c1['resourceInstallation'],'BASE_INSTALLATION_CHANGED')
    old_observation=continuation.private_json(private,installation['observationPin'],pins)
    changes=deployment_difference(Path(publication.RUNTIME),completion)
    before=next(r['sourcePin'] for r in runtime['importedSources'] if r['module']=='smallapp_simple')
    need(all(changes[0]['beforePin'][k]==before[k] for k in ('bytes','sha256')),'SIMPLE_BEFORE_OBSERVATION_CHANGED')
    for row in failure['custody']:
        if row['custody'] is not None:continuation.private_raw(private,row['custody'],pins)
    root=Path(base['worktree'])/'ops/spug';candidate=source_file(root,'smallapp_simple.py')
    need(content_pin(candidate)==completion['files']['smallapp_simple.py'],'SIMPLE_CANDIDATE_CHANGED')
    immutable=pins+c1['inputPins']+records.path_pins()+[publication.file_pin(p) for p in
        (__file__,activation.__file__,continuation.__file__,publication.__file__,contract.__file__)]
    unique={}
    for pin in immutable:
        need(pin['path'] not in unique or unique[pin['path']]==pin,'INPUT_PIN_CONFLICT');unique[pin['path']]=pin
    return dict(inputs=inputs,inputPin=input_pin,inputPins=list(unique.values()),completion=completion,base=base,c1=c1,
        failure=failure,prefix=prefix,runtime=runtime,oldObservation=old_observation,change=changes[0],candidatePath=str(candidate))


def prepare(task,private,inputs_file):
    records=contract.Records(task);inputs=records.read(inputs_file)
    return prepare_value(records,private,inputs,records.references[inputs_file])


def unchanged(prepared):
    for reference in prepared['inputPins']:publication.verify_bytes(reference)


def replace_simple(target,candidate,before_pin,archive,pending,before_write,after_write):
    target,archive,pending=map(Path,(target,archive,pending))
    continuation.safe_path(target);need(publication.file_pin(target)==before_pin,'SIMPLE_CHANGED_BEFORE_CUSTODY')
    previous=publication.exclusive_bytes(archive,target.read_bytes())
    need(all(previous[k]==before_pin[k] for k in ('bytes','sha256')),'SIMPLE_CUSTODY_CHANGED')
    before_write()
    transition=continuation.replace_after_custody(target,pending,before_pin,candidate,previous)
    actual=after_write()
    need(actual['bytes']==len(candidate) and actual['sha256']==hashlib.sha256(candidate).hexdigest(),'SIMPLE_CONTAINER_READBACK_CHANGED')
    return dict(previousPin=previous,transition=transition,containerReadbackPin=actual)


RUNTIME_BODY = r'''
import sys,inspect
sys.path.insert(0,'/opt/intruoyi-spug')
import smallapp_entry as entry,smallapp_adapter as adapter,smallapp_simple as simple
def guarded_pin(reference):
 path=Path(reference['path'])
 need(not path.is_symlink() and path.parent.resolve(strict=True)==path.parent,'RUNTIME_FILE_ALIAS')
 actual=file_pin(path);need(actual==reference,'RUNTIME_FILE_CHANGED');return actual
out=dict(status='FAILED',phase=SPEC['phase'],configurationWrites=False,backupDispatched=False,restoreDispatched=False)
try:
 identity=process_identity();lite=dict(pid=identity['pid'],startTicks=int(identity['startTicks']),exe=identity['executable'])
 if SPEC['expectedIdentity'] is None:need(lite==SPEC['originalEntryIdentity'],'ORIGINAL_ENTRY_CHANGED')
 else:need(identity==SPEC['expectedIdentity'],'EXPECTED_ENTRY_CHANGED')
 environment=hashlib.sha256((Path('/proc')/str(identity['pid'])/'environ').read_bytes()).hexdigest()
 if SPEC['expectedEnvironment'] is not None:need(environment==SPEC['expectedEnvironment'],'ENTRY_ENVIRONMENT_CHANGED')
 for reference in SPEC['preservedPins']:guarded_pin(reference)
 for root in SPEC['emptyAudits']:
  path=Path(root);need(path.is_dir() and not path.is_symlink() and not list(path.iterdir()),'ORIGINAL_EMPTY_AUDIT_CHANGED')
 audit=Path(SPEC['continuationAudit']);need(audit.is_dir() and not audit.is_symlink(),'C1_AUDIT_MISSING')
 filepins=[guarded_pin(reference) for reference in SPEC['filePins']]
 configpins=[guarded_pin(reference) for reference in SPEC['configurationPins']]
 origins=[]
 for module in (entry,adapter,simple):
  path=Path(inspect.getsourcefile(module));expected=next(p for p in filepins if p['path']=='/opt/intruoyi-spug/'+module.__name__+'.py')
  need(str(path)==expected['path'] and file_pin(path)==expected,'RUNTIME_IMPORT_ORIGIN_CHANGED');origins.append(expected)
 entry.initialize_spug()
 from apps.schedule.models import Task
 tasks=list(Task.objects.order_by('pk').values())
 tasksha=hashlib.sha256(json.dumps(tasks,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()).hexdigest()
 need(tasksha==SPEC['taskSnapshotSha256'],'TASKS_CHANGED')
 settings=entry.settings();need(len(settings['applications'])==33 and len(settings['tasks'])==3,'APPLICATIONS_CHANGED')
 for action in ('FULL','INCREMENTAL','RESTORE'):entry.installed_task(settings,action)
 bridge=adapter.HttpBridge('/run/intruoyi-spug/smallapp-bridge.private.json')
 need(bridge.fingerprint==SPEC['rootFingerprint'],'ROOT_FINGERPRINT_CHANGED')
 for row in SPEC['historyBindings']:
  bridge=adapter.HttpBridge('/run/intruoyi-spug/smallapp-bridge.private.json',row['ref'] if row['lane']=='sourceConnections' else None,row['ref'] if row['lane']=='targetConnections' else None)
  need(bridge.fingerprint==row['fingerprint'],'HISTORY_FINGERPRINT_CHANGED')
 parsed=False
 if SPEC['phase']=='before':
  try:simple.configuration()
  except adapter.Refused as error:need(str(error)=='SIMPLE_CONFIGURATION_INVALID','ORIGINAL_SIMPLE_ERROR_CHANGED')
  else:need(False,'ORIGINAL_SIMPLE_FAILURE_REQUIRED')
 else:
  configuration=simple.configuration();public=simple.public_configuration()
  need(configuration==json.loads(simple.CONFIG.read_bytes()) and public['catalogueRestoreBindings']==configuration['catalogueRestoreBindings'],'SIMPLE_PARSER_CHANGED')
  need([r['selectable'] for r in public['bindings']]==[r['selectable'] for r in configuration['bindings']],'BINDING_SELECTION_CHANGED')
  parsed=True
 need(process_identity()==identity,'ENTRY_CHANGED_DURING_CHECK')
 for reference in SPEC['filePins']+SPEC['configurationPins']+SPEC['preservedPins']:guarded_pin(reference)
 out.update(status='PASS',entryIdentity=identity,entryEnvironmentSha256=environment,filePins=filepins,configurationPins=configpins,
  importedSourcePins=origins,taskSnapshotSha256=tasksha,applicationCount=33,taskCount=3,
  historicalRouteCount=len(SPEC['historyBindings']),historicalFingerprintsUnchanged=True,originalAuditPreserved=True,
  freshProcessConfigurationParsed=parsed,liveUiVerified=False)
except BaseException as error:out.update(errorType=type(error).__name__,errorCode=str(error))
print(json.dumps(out))
'''


def runtime_spec(prepared,phase,identity=None,environment=None):
    need(phase in ('before','installed','after'),'RUNTIME_PHASE_INVALID')
    c1=prepared['c1'];spug=c1['originalSpec']['spugSpec'];old=prepared['oldObservation']
    files=[dict(path='/opt/intruoyi-spug/'+name,**pin) for name,pin in prepared['completion']['files'].items()]
    if phase=='before':
        for row in files:
            if row['path'].endswith('/smallapp_simple.py'):
                row.update({k:prepared['change']['beforePin'][k] for k in ('bytes','sha256')})
    preserved=[old['supervisorPin'],old['nginxPin'],*old['credentialPins'],*spug['observation']['connections'].values(),
               *[r['containerArchivePin'] for r in prepared['failure']['custody'] if r['containerArchivePin'] is not None]]
    return dict(phase=phase,expectedIdentity=identity,expectedEnvironment=environment,originalEntryIdentity=prepared['runtime']['entryIdentity'],
        filePins=files,configurationPins=prepared['runtime']['configPins'],preservedPins=preserved,
        emptyAudits=[c1['originalAuditPath']],continuationAudit=spug['auditPath'],
        taskSnapshotSha256=spug['observation']['taskSnapshotSha256'],rootFingerprint=spug['rootFingerprint'],historyBindings=spug['historyBindings'])


def runtime_program(prepared,phase,identity=None,environment=None):
    spec=runtime_spec(prepared,phase,identity,environment)
    return activation.HELPERS+'SPEC=json.loads('+repr(publication.canonical(spec).decode())+')\n'+RUNTIME_BODY


def reload_program(prepared,identity,environment):
    guard=runtime_program(prepared,'installed',identity,environment)
    spec=runtime_spec(prepared,'installed',identity,environment)
    reload=activation.reload_program(identity,[*spec['filePins'],*spec['configurationPins'],*spec['preservedPins']])
    return '\n'.join(['import contextlib,io,json','namespace={"__name__":"__main__"}','captured=io.StringIO()',
        'with contextlib.redirect_stdout(captured):',
        ' exec(compile('+repr(guard)+',"dependency-before-reload","exec"),namespace)',
        'if namespace["out"].get("status")!="PASS": raise ValueError("DEPENDENCY_RELOAD_GUARD_FAILED")',
        'exec(compile('+repr(reload)+',"dependency-supervised-reload","exec"),{"__name__":"__main__"})',''])


def validate_runtime_result(prepared,result,phase,identity=None,environment=None):
    spec=runtime_spec(prepared,phase,identity,environment)
    need(type(result) is dict and result.get('status')=='PASS' and result.get('phase')==phase and
         result.get('filePins')==spec['filePins'] and result.get('configurationPins')==spec['configurationPins'] and
         result.get('taskSnapshotSha256')==spec['taskSnapshotSha256'] and result.get('applicationCount')==33 and result.get('taskCount')==3 and
         result.get('historicalRouteCount')==len(spec['historyBindings']) and result.get('historicalFingerprintsUnchanged') is True and
         result.get('originalAuditPreserved') is True and result.get('freshProcessConfigurationParsed') is (phase!='before') and
         all(result.get(k) is False for k in ('configurationWrites','backupDispatched','restoreDispatched','liveUiVerified')),
         'RUNTIME_VERIFICATION_FAILED')
    actual=result.get('entryIdentity');need(type(actual) is dict and contract.sha(result.get('entryEnvironmentSha256')),'ENTRY_PROOF_MISSING')
    if identity is not None:need(actual==identity,'ENTRY_IDENTITY_CHANGED')
    else:need(dict(pid=actual['pid'],startTicks=int(actual['startTicks']),exe=actual['executable'])==prepared['runtime']['entryIdentity'],
              'ORIGINAL_ENTRY_CHANGED')
    if environment is not None:need(result['entryEnvironmentSha256']==environment,'ENTRY_ENVIRONMENT_CHANGED')
    expected=[next(p for p in spec['filePins'] if p['path']=='/opt/intruoyi-spug/'+name+'.py')
              for name in ('smallapp_entry','smallapp_adapter','smallapp_simple')]
    need(result.get('importedSourcePins')==expected,'IMPORTED_SOURCE_PROOF_CHANGED')
    return result


class ActualTransport:
    """Only the fixed local container; there is no SSH or configuration writer."""
    def __init__(self,private,prepared):
        context=deepcopy(prepared['c1']);context['inputs']['outputFile']=prepared['inputs']['outputFile']
        self.native=continuation.ActualContinuationTransport(private,context);self.prepared=prepared
    @property
    def receipts(self):return self.native.receipts
    def command(self,label,program):
        self.native.inspect_current()
        nonce='spug-dependency-'+self.prepared['inputs']['sourceCommit'][:7]+'-'+self.prepared['inputs']['operationId']
        result=self.native.command(label,[publication.DOCKER,'exec','-i',publication.CONTAINER,'python3','-B','-',nonce],program,120)
        self.native.inspect_current();return result
    def observe(self,phase,identity=None,environment=None):
        result=self.command(phase,runtime_program(self.prepared,phase,identity,environment))
        return validate_runtime_result(self.prepared,result,phase,identity,environment)
    def reload(self,identity,environment):
        result=self.command('reload',reload_program(self.prepared,identity,environment))
        return validate_reload_identity(identity,result)


def validate_reload_identity(identity,result):
    need(type(result) is dict and set(result)==set(identity) and result['pid']!=identity['pid'] and result['startTicks']!=identity['startTicks'] and
         all(result[k]==identity[k] for k in identity if k not in ('pid','startTicks')),'RELOAD_IDENTITY_INVALID')
    return result


def run_request(task,private,inputs_file,*,activate=False,transport=None):
    prepared=prepare(task,private,inputs_file)
    if not activate:return dict(status='PREPARED_NOT_ACTIVATED',sourceCommit=prepared['inputs']['sourceCommit'],
        fileCount=14,replacementCount=1,configurationWrites=False,remoteDispatched=False)
    return activate_prepared(Path(task),Path(private),prepared,transport=transport)


def activate_prepared(task,private,prepared,*,transport=None):
    unchanged(prepared);inputs=prepared['inputs'];stem=inputs['outputFile'][:-5]
    output=task/inputs['outputFile'];rich_path=private/(stem+'.private.json');attempt_path=private/(stem+'.attempt.private.json')
    gate=private/('spug-runtime-dependency-'+publication.CONTAINER+'.gate.private.json')
    need(not any(p.exists() or p.is_symlink() for p in (output,rich_path,attempt_path,gate)),'ACTIVATION_ALREADY_ATTEMPTED')
    binding=dict(activationInputsPin=prepared['inputPin'],sourceCommit=inputs['sourceCommit'],operationId=inputs['operationId'],
        dependencyCompletionPin=inputs['dependencyCompletionPin'],continuationFailurePin=inputs['continuationFailurePin'])
    gate_pin=publication.exclusive_bytes(gate,publication.canonical(dict(**binding,retryPermitted=False)))
    attempt=publication.exclusive_bytes(attempt_path,publication.canonical(dict(schemaVersion='MainProgramSpugRuntimeDependencyAttempt/v1',
        **binding,inputPins=prepared['inputPins'],gatePin=gate_pin,retryPermitted=False)))
    transport=transport or ActualTransport(private,prepared)
    evidence=dict(schemaVersion='MainProgramSpugRuntimeDependencyActivation/v1',status='FAILED',**binding,attemptPin=attempt,
        replacementState='NOT_STARTED',configurationWrites=False,backupDispatched=False,restoreDispatched=False,retryPermitted=False)
    stage='before'
    def save_stage(name,value):
        reference=publication.exclusive_bytes(private/(stem+'.'+name+'.private.json'),publication.canonical(value))
        evidence.setdefault('stagePins',[]).append(dict(stage=name,pin=reference))
    try:
        before=validate_runtime_result(prepared,transport.observe('before'),'before');save_stage('before',before)
        identity=before['entryIdentity'];environment=before['entryEnvironmentSha256'];stage='replacement'
        def guard():
            unchanged(prepared)
            value=validate_runtime_result(prepared,transport.observe('before',identity,environment),'before',identity,environment);save_stage('before-write',value)
            evidence['replacementState']='DISPATCHED_OUTCOME_UNKNOWN'
            save_stage('replacement-dispatched',dict(state=evidence['replacementState'],path=prepared['change']['beforePin']['path']))
        def readback():
            value=validate_runtime_result(prepared,transport.observe('installed',identity,environment),'installed',identity,environment);save_stage('installed',value)
            return next(p for p in value['filePins'] if p['path']=='/opt/intruoyi-spug/smallapp_simple.py')
        target=Path(publication.RUNTIME)/'smallapp_simple.py'
        candidate=Path(prepared['candidatePath']).read_bytes()
        need(content_pin(prepared['candidatePath'])==prepared['completion']['files']['smallapp_simple.py'],'CANDIDATE_CHANGED_BEFORE_WRITE')
        replacement=replace_simple(target,candidate,prepared['change']['beforePin'],private/(stem+'.before-simple.private.py'),
                                   target.with_name(target.name+'.'+stem+'.pending'),guard,readback)
        evidence.update(replacementState='APPLIED',replacement=replacement);save_stage('replacement-applied',replacement)
        stage='reload';unchanged(prepared);new_identity=validate_reload_identity(identity,transport.reload(identity,environment));save_stage('reload',new_identity)
        stage='after';after=validate_runtime_result(prepared,transport.observe('after',new_identity,environment),'after',new_identity,environment);save_stage('after',after)
        unchanged(prepared)
        evidence.update(status='PASS',entryBefore=identity,entryAfter=new_identity,entryEnvironmentSha256=environment,
            filePinsBefore=before['filePins'],filePinsAfter=after['filePins'],configurationPins=after['configurationPins'],
            oldThirteenResourcesUnchanged=True,sevenConfigurationsUnchanged=True,historicalFingerprintsUnchanged=True,
            originalC1EvidencePreserved=True,protectedSpugUnchanged=True,entryReloaded=True,freshProcessConfigurationParsed=True,liveUiVerified=False)
    except BaseException as error:
        evidence.update(status='FAILED',stage=stage,errorType=type(error).__name__,errorCode=str(error))
    evidence['nativeReceiptPins']=deepcopy(transport.receipts)
    evidence_pin=publication.exclusive_bytes(rich_path,publication.canonical(evidence))
    if evidence['status']!='PASS':raise ValueError('SPUG_DEPENDENCY_ACTIVATION_FAILED_CHECK_PRIVATE_EVIDENCE')
    core={k:v for k,v in evidence.items() if k not in ('inputPins','nativeReceiptPins','stagePins','errorCode','errorType')}
    core.update(privateEvidencePin=evidence_pin,baseResourceActivationPin=inputs['baseResourceActivationPin'])
    publication.exclusive_bytes(output,publication.canonical(core))
    return dict(status='PASS',report=output.name,configurationWrites=False,entryReloaded=True,publicationCompleted=False)


def parser():
    value=argparse.ArgumentParser(description=__doc__);value.add_argument('--inputs',required=True)
    value.add_argument('--activate',action='store_true');value.add_argument('--task',type=Path,default=TASK)
    value.add_argument('--private',type=Path,default=PRIVATE);return value


if __name__=='__main__':
    args=parser().parse_args()
    try:result=run_request(args.task,args.private,args.inputs,activate=args.activate)
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as error:
        code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'SPUG_DEPENDENCY_INPUT_OR_EXECUTION_FAILED'
        print(json.dumps(dict(status='REFUSED',errorCode=code,activateRequested=args.activate)));raise SystemExit(1)
    print(json.dumps(result))
