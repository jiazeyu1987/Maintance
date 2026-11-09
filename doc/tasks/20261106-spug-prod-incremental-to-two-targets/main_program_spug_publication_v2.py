"""Publish one explicit control generation; default to local preparation only.

No retry or recovery is implicit. A failed/unknown request is retained and needs
an independently reviewed observation before a different attempt is designed.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import main_program_installation_selection as contract
import main_program_spug_publication as reader


def need(value, code):
    if not value: raise ValueError('MAIN_SPUG_'+code)


def program(lane, host, phase, spec):
    need(lane in ('host','spug') and phase in ('preflight','publish','verify') and
         (host in contract.HOSTS if lane=='host' else host is None),'V2_PROGRAM_SCOPE_INVALID')
    original=reader.payload(reader.HOST_PROGRAM if lane=='host' else reader.SPUG_PROGRAM,spec,phase)
    # Execute the exact frozen guard program in its own namespace. Capturing its
    # one JSON print prevents a second JSON document; no guard is rewritten.
    # Additional identity fields come only after that real program succeeds.
    return '\n'.join([
        'import contextlib,io,json',
        'namespace={"__name__":"__main__"}',
        'captured=io.StringIO()',
        'with contextlib.redirect_stdout(captured):',
        ' exec(compile('+repr(original)+',"frozen-publication-program","exec"),namespace)',
        'result=namespace["out"]',
        'if result.get("status")=="PASS" and result.get("phase")=="verify":',
        (' result["host"]='+repr('172.30.30.'+host)+'\n'
         ' result["controllers"]=[row for row,control,owner in namespace["verify_controls"]()]'
         if lane=='host' else
         ' result["productPins"]=[namespace["file_pin"](row["path"]) for row in namespace["SPEC"]["observation"]["productPins"]]'),
        'print(json.dumps(result))',''])


def binding(spec):
    value={k:spec['inputs'][k] for k in ('sourceCommit','revisionId','controlGenerationPin',
        'spugResourceBuildPin','publicationObservationPin')}
    value['publicationInputsPin']=spec['publicationInputsPin']
    return value


def check_inputs(spec):
    for reference in spec['inputPins']:
        need(reader.file_pin(reference['path'])==reference,'V2_INPUT_CHANGED')


def stage_result(spec, stage, result):
    lane,phase,*hosts=stage.split('-')
    need(type(result) is dict and result.get('status')=='PASS' and result.get('phase')==phase and
         result.get('sourceCommit')==spec['inputs']['sourceCommit'] and
         result.get('backupDispatched') is False and result.get('restoreDispatched') is False,
         'V2_ACTUAL_STAGE_FAILED')
    if phase!='verify':return
    if lane=='host':
        host=hosts[0];selected=spec['hostSpecs'][host]
        need(result.get('host')=='172.30.30.'+host and result.get('controllers')==selected['controllers'] and
             type(result.get('selectorCount')) is int and result['selectorCount']==(6 if host=='57' else 3) and
             all(result.get(k) is True for k in ('selectorsReadBack','actualNativeSelectionsVerified',
                 'oldFilesPreserved','businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')),
             'V2_ACTUAL_HOST_VERIFICATION_FAILED')
    else:
        need(type(result.get('applicationCount')) is int and result['applicationCount']==33 and
             type(result.get('taskCount')) is int and result['taskCount']==3 and
             result.get('productPins')==spec['spugSpec']['observation']['productPins'] and
             all(result.get(k) is True for k in ('productSettingsReadBack','historicalFingerprintsUnchanged',
                 'oldFilesPreserved','protectedSpugUnchanged','oldTasksUnchanged','productFilesUnchanged')),
             'V2_ACTUAL_SPUG_VERIFICATION_FAILED')


def aggregate(spec, rows):
    need([r['stage'] for r in rows]==reader.publication_schedule(),'V2_ACTUAL_STAGE_SET_INCOMPLETE')
    hosts=[r['result'] for r in rows if r['stage'].startswith('host-verify-')]
    spug=rows[-1]['result']
    return dict(status='PASS',sourceCommit=spec['inputs']['sourceCommit'],publicationCompleted=True,
        selectorCount=sum(r['selectorCount'] for r in hosts),applicationCount=spug['applicationCount'],taskCount=spug['taskCount'],
        selectorsReadBack=all(r['selectorsReadBack'] is True for r in hosts),
        actualNativeSelectionsVerified=all(r['actualNativeSelectionsVerified'] is True for r in hosts),
        productSettingsReadBack=spug['productSettingsReadBack'],historicalFingerprintsUnchanged=spug['historicalFingerprintsUnchanged'],
        oldFilesPreserved=all(r['oldFilesPreserved'] is True for r in hosts) and spug['oldFilesPreserved'] is True,
        protectedSpugUnchanged=spug['protectedSpugUnchanged'],
        businessContainersUnchanged=all(r['businessContainersUnchanged'] is True for r in hosts),
        fstabAndMountsUnchanged=all(r['fstabAndMountsUnchanged'] is True for r in hosts),
        oldTasksUnchanged=spug['oldTasksUnchanged'],productFilesUnchanged=spug['productFilesUnchanged'],
        controlIdentityVerified=all(r['controlIdentityVerified'] is True for r in hosts),
        backupDispatched=False,restoreDispatched=False)


class PendingCoreRecords:
    """Validate an in-memory core projection before making it a public receipt.

    Only that one projected core is virtual. Every generation, build, input,
    observation and phase is read from its actual pinned original by the frozen
    reader. No full-installation selection or public success file is fabricated.
    """
    def __init__(self, task, reference, core):
        self.original=contract.Records(task);self.task=self.original.task
        self.reference=reference;self.core=deepcopy(core)

    def pinned(self, reference):
        if reference==self.reference:return deepcopy(self.core)
        return self.original.pinned(reference)

    def path_pins(self):return self.original.path_pins()


def _execute_prepared(task, private, spec, *, transport=None):
    """Internal runner: the public run_request always performs strict prepare."""
    task,private=Path(task).resolve(strict=True),Path(private).resolve(strict=True)
    need(spec['inputs'].get('schemaVersion')=='MainProgramSpugPublicationInputs/v2' and
         set(spec['hostSpecs'])==set(contract.HOSTS),'V2_PREPARED_INPUTS_REQUIRED')
    name=contract.local_name(spec['inputs']['outputFile']);stem=name.removesuffix('.json')
    output=task/name;rich=private/(stem+'.private.json');attempt=private/(stem+'.attempt.private.json')
    failure=private/(stem+'.finalization-failure.private.json')
    names=[output,rich,attempt,failure]
    for stage in reader.publication_schedule():
        names.extend(private/(stem+'.'+stage+ending) for ending in
            ('.program.private.py','.request.private.json','.private.json'))
    need(not any(p.exists() or p.is_symlink() for p in names),'V2_ATTEMPT_EXISTS')
    check_inputs(spec)
    pins=deepcopy(spec['inputPins'])+[reader.file_pin(Path(__file__).resolve())]
    spec=dict(spec,inputPins=list({p['path']:p for p in pins}.values()))
    identity=binding(spec)
    reader.exclusive_bytes(attempt,reader.canonical(dict(schemaVersion='MainProgramSpugPublicationAttempt/v2',
        **identity,inputPins=spec['inputPins'],stageOrder=reader.publication_schedule(),retryPermitted=False)))
    stages=[];results=[];current='local-inputs'
    try:
        if transport is None:transport=reader.ActualTransport(private,spec['spugSpec'])
        for current in reader.publication_schedule():
            check_inputs(spec)
            lane,phase,*hosts=current.split('-');host=hosts[0] if hosts else None
            selected=deepcopy(spec['hostSpecs'][host] if lane=='host' else spec['spugSpec'])
            # A revision owns a distinct audit directory; no earlier failed
            # revision's originals can be overwritten by the same commit.
            selected['auditPath']=selected['auditPath']+'-'+spec['inputs']['revisionId']
            rendered=program(lane,host,phase,selected)
            prefix=stem+'.'+current
            program_pin=reader.exclusive_bytes(private/(prefix+'.program.private.py'),rendered.encode('utf-8'))
            reader.exclusive_bytes(private/(prefix+'.request.private.json'),reader.canonical(dict(
                schemaVersion='MainProgramSpugPublicationDispatch/v2',stage=current,**identity,programPin=program_pin,
                lane=lane,host=None if host is None else '172.30.30.'+host,phase=phase,retryPermitted=False)))
            try:
                observed=transport(lane,host,phase,rendered)
            except BaseException as error:
                observed=dict(status='UNKNOWN',phase=phase,sourceCommit=spec['inputs']['sourceCommit'],
                    errorType=type(error).__name__,errorCode=str(error))
                envelope=dict(schemaVersion='MainProgramSpugPublicationStage/v2',stage=current,**identity,result=observed)
                reference=reader.exclusive_bytes(private/(prefix+'.private.json'),reader.canonical(envelope))
                stages.append(dict(stage=current,resultPin=reference))
                raise
            envelope=dict(schemaVersion='MainProgramSpugPublicationStage/v2',stage=current,**identity,result=observed)
            reference=reader.exclusive_bytes(private/(prefix+'.private.json'),reader.canonical(envelope))
            stages.append(dict(stage=current,resultPin=reference));results.append(dict(stage=current,result=observed))
            stage_result(spec,current,observed)
        check_inputs(spec)
        observed=aggregate(spec,results);core=reader.project_core(spec,observed)
        evidence=dict(observed,schemaVersion='MainProgramSpugPublicationEvidence/v2',stage='complete',**identity,
            resourceSourceCommit=spec['resourceSourceCommit'],stages=stages)
        reader.exclusive_bytes(rich,reader.canonical(evidence))
        raw=reader.canonical(core);core_pin=dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        candidate=dict(schemaVersion='TaskMainProgramInstallations/v2',sourceCommit=identity['sourceCommit'],
            controlGenerationPin=identity['controlGenerationPin'],spugInstallationPin=core_pin)
        reader.validate_publication_v2(PendingCoreRecords(task,core_pin,core),private,candidate)
        check_inputs(spec)
        reader.exclusive_bytes(output,raw)
        return dict(status='PASS',report=name,sourceCommit=identity['sourceCommit'],
                    revisionId=identity['revisionId'],remoteDispatched=True)
    except BaseException as error:
        evidence=dict(schemaVersion='MainProgramSpugPublicationFailure/v2',status='FAILED',stage=current,
            **identity,stages=stages,errorType=type(error).__name__,errorCode=str(error),retryPermitted=False)
        # If all twelve phases really passed but final local proof validation
        # failed, retain their immutable evidence and add a separate failure.
        reader.exclusive_bytes(failure if rich.exists() else rich,reader.canonical(evidence))
        raise ValueError('MAIN_SPUG_V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT') from None


def run_request(task, private, inputs_file, *, apply=False, transport=None):
    spec=reader.prepare(task,private,inputs_file)
    need(spec['inputs']['schemaVersion']=='MainProgramSpugPublicationInputs/v2','V2_INPUTS_REQUIRED')
    if not apply:
        return dict(status='PREPARED_NOT_APPLIED',sourceCommit=spec['inputs']['sourceCommit'],
                    revisionId=spec['inputs']['revisionId'],remoteDispatched=False)
    return _execute_prepared(task,private,spec,transport=transport)


def parser():
    value=argparse.ArgumentParser(description=__doc__)
    value.add_argument('--inputs',required=True)
    value.add_argument('--apply',action='store_true')
    value.add_argument('--task',type=Path,default=reader.TASK)
    value.add_argument('--private',type=Path,default=reader.PRIVATE)
    return value


if __name__=='__main__':
    args=parser().parse_args()
    try:result=run_request(args.task,args.private,args.inputs,apply=args.apply)
    except BaseException as error:
        print(json.dumps(dict(status='FAILED',errorType=type(error).__name__,
            errorCode='MAIN_SPUG_V2_FAILED_CHECK_PRIVATE_EVIDENCE')))
        raise SystemExit(1) from None
    print(json.dumps(result))
