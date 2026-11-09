"""Finalize immutable historical stage receipts locally, without any transport."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import main_program_control_activation as activation
import main_program_control_staging as staging
import main_program_installation_selection as contract

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
SSH_CLOSE=re.compile(rb'close - IO is still pending on closed socket\. read:1, write:0, io:[0-9A-Fa-f]{16}\r\n')
LIMIT=64*1024*1024


def need(value,code):
    if not value:raise ValueError('MAIN_STAGING_FINALIZE_'+code)


def read_json(raw):
    def constant(value):raise ValueError('MAIN_STAGING_FINALIZE_JSON_CONSTANT_INVALID')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=contract.document,parse_constant=constant)
    need(type(value) is dict,'DOCUMENT_OBJECT_REQUIRED')
    return value


def path_pin(path):
    path=Path(path)
    need(not path.is_symlink() and path.resolve(strict=True)==path,'FILE_ALIAS')
    before=path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'FILE_ALIAS')
    return activation.file_pin(path)


def read_pinned(reference,*,limit=LIMIT):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
        type(reference['path']) is str and type(reference['bytes']) is int and
        0<=reference['bytes']<=limit and contract.sha(reference['sha256']),'PIN_INVALID')
    path=Path(reference['path'])
    need(path.is_absolute() and str(path)==reference['path'] and path_pin(path)==reference,'PIN_CHANGED')
    raw=path.read_bytes()
    need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'] and
        path_pin(path)==reference,'PIN_CHANGED')
    return raw


def local_reference(root,reference):
    need(type(reference) is dict and set(reference)=={'file','bytes','sha256'} and
        type(reference['file']) is str and re.fullmatch('[A-Za-z0-9_.-]+',reference['file']) is not None and
        reference['file'] not in ('.','..'),'LOCAL_PIN_INVALID')
    return dict(path=str(root/reference['file']),bytes=reference['bytes'],sha256=reference['sha256'])


def pin_map(references):
    need(type(references) is list and references,'INPUT_PIN_SET_REQUIRED')
    result={}
    for reference in references:
        need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
            type(reference['bytes']) is int and reference['bytes']>0 and contract.sha(reference['sha256']),'INPUT_PIN_INVALID')
        previous=result.setdefault(reference['path'],reference)
        need(previous==reference,'INPUT_PIN_CONFLICT')
        need(path_pin(reference['path'])==reference,'INPUT_PIN_CHANGED')
    return result


def prepare(task,private,inputs):
    """Verify the original complete execution and all local dependencies; no I/O writes."""
    task,private=Path(task).resolve(strict=True),Path(private).resolve(strict=True)
    need(type(inputs) is dict and set(inputs)=={'schemaVersion','attemptPin','transportPin','resultPin'} and
        inputs['schemaVersion']=='MainProgramControlStagingFinalizeInputs/v1','INPUTS_INVALID')
    references={key:local_reference(private,inputs[key]) for key in ('attemptPin','transportPin','resultPin')}
    attempt=read_json(read_pinned(references['attemptPin']))
    fields={'schemaVersion','status','inputs','prepared','executionInputPins','payloadBytes','payloadSha256',
        'remoteHost','backupDispatched','restoreDispatched'}
    need(set(attempt)==fields and attempt['schemaVersion']=='MainProgramControlStagingAttempt/v1' and
        attempt['status']=='ATTEMPT_RESERVED' and attempt['backupDispatched'] is False and
        attempt['restoreDispatched'] is False,'ATTEMPT_INVALID')
    original=attempt['prepared'];selected=attempt['inputs'];staging.validate_inputs(selected)
    suffix,short,revision=selected['suffix'],selected['sourceCommit'][:7],selected['revisionId']
    stem='main-program-control-staging-'+suffix+'-'+short+'-'+revision
    for key,tail in (('attemptPin','attempt'),('transportPin','transport'),('resultPin','result')):
        need(inputs[key]['file']==stem+'-'+tail+'.private.json','ORIGINAL_NAME_CHANGED')
    need(original['schemaVersion']=='MainProgramControlStagingPreparation/v1' and
        original['status']=='PREPARED_NOT_STAGED' and original['remoteExecutable'] is False and
        original['inputs']==selected and attempt['remoteHost']==original['filesystemSpec']['host']=='172.30.30.'+suffix,
        'ATTEMPT_BINDING_CHANGED')
    names=dict(engine='main-program-engine-staged-'+suffix+'-'+short+'-'+revision+'.json',
        configuration='main-program-configuration-staged-'+suffix+'-'+short+'-'+revision+'.json')
    need(original['engineReportFile']==names['engine'] and original['configurationReportFile']==names['configuration'],
        'OUTPUT_NAME_CHANGED')
    need(not any(os.path.lexists(task/name) for name in names.values()),'OUTPUT_EXISTS')

    transport=read_json(read_pinned(references['transportPin']))
    need(set(transport)=={'schemaVersion','actualExitCode','timedOut','filesMayHaveBeenCreated','automaticRetryAllowed','stdoutPin','stderrPin'} and
        transport['schemaVersion']=='MainProgramControlStagingTransport/v1' and
        type(transport['actualExitCode']) is int and transport['actualExitCode']==0 and
        transport['timedOut'] is False and transport['filesMayHaveBeenCreated'] is True and
        transport['automaticRetryAllowed'] is False,'TRANSPORT_NOT_COMPLETE')
    for key,tail in (('stdoutPin','stdout'),('stderrPin','stderr')):
        need(transport[key].get('path')==str(private/(stem+'-'+tail+'.private.log')),'TRANSPORT_LOG_SCOPE_CHANGED')
    stdout=read_pinned(transport['stdoutPin']);stderr=read_pinned(transport['stderrPin'],limit=1024)
    need(stderr==b'' or SSH_CLOSE.fullmatch(stderr) is not None,'STDERR_UNRECOGNIZED')
    terminal=read_json(stdout);result_raw=read_pinned(references['resultPin'])
    need(result_raw==staging.canonical(terminal),'RESULT_BYTES_DIVERGE')
    fields={'status','stage','reports','actual','createdPaths','filesMayHaveBeenCreated','backupDispatched',
        'restoreDispatched','controlServicesReloaded'}
    need(set(terminal)==fields and terminal['status']=='STAGED_NOT_ACTIVATED' and terminal['stage']=='complete' and
        terminal['filesMayHaveBeenCreated'] is True and all(terminal[key] is False for key in
        ('backupDispatched','restoreDispatched','controlServicesReloaded')),'TERMINAL_NOT_COMPLETE')
    created=terminal['createdPaths'];files=terminal['actual']['files'];spec=original['filesystemSpec']
    need(type(created) is list and created and all(type(p) is str for p in created) and len(set(created))==len(created) and
        files['createdPaths']==created and files['activationReportEligible'] is False and
        all(files[key]==spec[key] for key in ('sourceCommit','revisionId','host')) and
        files['newDocuments']==[row['pin'] for row in spec['newDocuments']] and
        files['retainedDocuments']==[row['pin'] for row in spec['retainedDocuments']] and
        files['requiredRuntimeGates']==list(staging.RUNTIME_GATES) and
        all(row['path'] in created for row in spec['engines']) and
        all(row['pin']['path'] in created for row in spec['newDocuments']),'FILES_NOT_COMPLETE')

    original_pins=pin_map(original['inputPins']);execution_pins=pin_map(attempt['executionInputPins'])
    # Re-run the original pure reader, including both actual package tars,
    # generation, full coverage, planner and bound host observations.
    input_files=[]
    for reference in original_pins.values():
        path=Path(reference['path'])
        if path.parent==task and path.suffix=='.json':
            raw=path.read_bytes()
            if b'MainProgramControlStagingInputs/v1' in raw and read_json(raw)==selected:input_files.append(path.name)
    need(len(input_files)==1,'ORIGINAL_EXPLICIT_INPUT_REQUIRED')
    records=contract.Records(task);ordered_inputs=records.read(input_files[0])
    fresh=staging.prepare_materials_from_records(records,private,ordered_inputs)
    need({k:v for k,v in fresh.items() if k!='inputPins'}=={k:v for k,v in original.items() if k!='inputPins'},
        'PREPARATION_CHANGED')
    fresh_pins=pin_map(fresh['inputPins'])
    need(fresh_pins==original_pins,'PREPARATION_PIN_SET_CHANGED')
    # canonical attempt JSON does not retain insertion order used by the original
    # repr payload. Rebuild from its pinned explicit input and original reader.
    envelope=staging.execution_bundle(fresh)
    need(pin_map(envelope['prepared']['executionInputPins'])==execution_pins,'EXECUTION_PIN_SET_CHANGED')
    payload=staging.render_bootstrap(envelope).encode('utf-8')
    need(type(attempt['payloadBytes']) is int and len(payload)==attempt['payloadBytes'] and
        hashlib.sha256(payload).hexdigest()==attempt['payloadSha256'],'EXECUTION_PAYLOAD_CHANGED')
    reports=terminal['reports']
    need(reports==staging.project_stage_reports(original,terminal['actual']),'CORE_PROJECTION_CHANGED')
    plan=records.pinned(selected['planPin']);build=records.pinned(selected['buildPin'])
    need(build==spec['build'],'BUILD_CHANGED')
    activation.validate_generation_staging(selected,plan,build,reports['engine'],reports['configuration'])
    evidence=[*references.values(),transport['stdoutPin'],transport['stderrPin'],*original_pins.values(),*execution_pins.values()]
    for reference in evidence:need(path_pin(reference['path'])==reference,'INPUT_PIN_CHANGED')
    outputs={key:dict(reports[key],privateSnapshotPin=references['resultPin'],transportEvidencePin=references['transportPin'])
        for key in ('engine','configuration')}
    return dict(status='READY_TO_FINALIZE',sourceCommit=selected['sourceCommit'],host=attempt['remoteHost'],revisionId=revision,
        stderrClassification='EMPTY' if not stderr else 'WINDOWS_SSH_CLOSE_PENDING_IO',
        outputFiles=names,reports=outputs,evidencePins=evidence,remoteDispatched=False,historicalStageOnly=True)


def finalize(task,private,inputs):
    ready=prepare(task,private,inputs);task=Path(task).resolve(strict=True)
    for reference in ready['evidencePins']:need(path_pin(reference['path'])==reference,'INPUT_PIN_CHANGED')
    need(not any(os.path.lexists(task/name) for name in ready['outputFiles'].values()),'OUTPUT_EXISTS')
    output={}
    for key in ('engine','configuration'):
        name=ready['outputFiles'][key]
        reference=staging._exclusive_local(task/name,staging.canonical(ready['reports'][key]))
        output[key+'StagedPin']=dict(file=name,bytes=reference['bytes'],sha256=reference['sha256'])
    return dict(status='STAGED_NOT_ACTIVATED',**output,stderrClassification=ready['stderrClassification'],
        remoteDispatched=False,historicalStageOnly=True,activationPerformed=False)


def run_request(task,private,inputs_file,*,finalize_output=False):
    records=contract.Records(task);inputs=records.read(inputs_file)
    return finalize(task,private,inputs) if finalize_output else prepare(task,private,inputs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',required=True)
    parser.add_argument('--task',type=Path,default=TASK)
    parser.add_argument('--private',type=Path,default=PRIVATE)
    parser.add_argument('--finalize',action='store_true')
    args=parser.parse_args()
    try:result=run_request(args.task,args.private,args.inputs,finalize_output=args.finalize)
    except (OSError,ValueError,KeyError,TypeError) as error:
        code=str(error) if isinstance(error,ValueError) and str(error).startswith('MAIN_STAGING_FINALIZE_') else 'MAIN_STAGING_FINALIZE_ORIGINALS_INVALID'
        print(json.dumps(dict(status='REFUSED',errorCode=code)));return 1
    if not args.finalize:result={key:result[key] for key in
        ('status','sourceCommit','host','revisionId','stderrClassification','remoteDispatched','historicalStageOnly')}
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
