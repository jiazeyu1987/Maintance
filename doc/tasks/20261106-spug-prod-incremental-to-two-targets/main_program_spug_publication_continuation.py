"""One explicit failed publication continuation; never infer or retry a write.

The original control generation and v2 records remain immutable. Only exact
configuration files are installed; product files and host selectors are not.
"""
import argparse
import base64
from copy import deepcopy
import ctypes
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

import main_program_installation_selection as contract
import main_program_spug_publication as reader
import main_program_spug_publication_v2 as original

TASK, PRIVATE = reader.TASK, reader.PRIVATE
BIND_ROOT = 'C:/Spug/runtime/private'
RUN_ROOT = '/run/intruoyi-spug'
VOLUME_ROOT = '/var/lib/intruoyi-spug'


def need(value, code):
    if not value: raise ValueError('MAIN_SPUG_'+code)


def classify_writes(writes, mounts):
    need(type(mounts) is list and all(type(m) is dict and set(m)==
        {'Type','Source','Destination','RW','Name'} for m in mounts),'CONTINUATION_MOUNTS_INVALID')
    paths=[m['Destination'] for m in mounts]
    need(len(set(paths))==len(paths),'CONTINUATION_MOUNT_DUPLICATE')
    selected={}
    for root in (RUN_ROOT,'/opt/intruoyi-spug',VOLUME_ROOT):
        rows=[m for m in mounts if m['Destination']==root]
        need(len(rows)==1 and not any(p.startswith(root+'/') for p in paths),'CONTINUATION_MOUNT_SHADOW')
        selected[root]=rows[0]
    for root,source in ((RUN_ROOT,BIND_ROOT),('/opt/intruoyi-spug',reader.RUNTIME)):
        row=selected[root]
        need(row==dict(Type='bind',Source=source,Destination=root,RW=False,Name=None),
             'CONTINUATION_BIND_IDENTITY_CHANGED')
    volume=selected[VOLUME_ROOT]
    need(volume['Type']=='volume' and volume['RW'] is True and type(volume['Name']) is str and
         re.fullmatch('[A-Za-z0-9_.-]+',volume['Name']) and type(volume['Source']) is str and
         volume['Source']=='/var/lib/docker/volumes/'+volume['Name']+'/_data','CONTINUATION_VOLUME_INVALID')
    need(type(writes) is list and len(writes)==7,'CONTINUATION_WRITE_SET_INVALID')
    result=[];seen=set()
    for index,row in enumerate(writes):
        need(type(row) is dict and set(row)=={'path','expected','value'},'CONTINUATION_WRITE_INVALID')
        path=row['path'];p=PurePosixPath(path)
        need(type(path) is str and p.is_absolute() and str(p)==path and '..' not in p.parts and
             path.lower() not in seen,'CONTINUATION_PATH_ALIAS')
        seen.add(path.lower())
        if index<4:
            need(p.parent==PurePosixPath(RUN_ROOT) and re.fullmatch('[A-Za-z0-9_.-]+[.]json',p.name) and
                 path!=reader.SETTINGS['bridge'] and row['expected'] is None,'CONTINUATION_NEW_CONNECTION_INVALID')
        else:
            need(path==reader.SETTINGS[('simple','entry','bridge')[index-4]] and
                 type(row['expected']) is dict and row['expected'].get('path')==path,
                 'CONTINUATION_SETTING_ORDER_CHANGED')
            contract.remote_pin(row['expected'])
        host=p.parent==PurePosixPath(RUN_ROOT)
        result.append(dict(index=index,path=path,executor='HOST_BIND' if host else 'CONTAINER_VOLUME',
                           hostPath=BIND_ROOT+'/'+p.name if host else None))
    return result


def safe_path(path):
    path=Path(path)
    need(path.is_absolute() and path.parent.resolve(strict=True)==path.parent,'CONTINUATION_PATH_ALIAS')
    for part in (path,*path.parents):
        if not part.exists() and not part.is_symlink():continue
        info=part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info,'st_file_attributes',0)&1024),
             'CONTINUATION_PATH_REPARSE')
        if part==path and part.is_file():need(info.st_nlink==1,'CONTINUATION_FILE_HARDLINK')
    return path


def atomic_move(source, target, *, replace):
    """Windows is the host writer; POSIX volume replacement only uses replace."""
    source,target=map(Path,(source,target))
    if replace:os.replace(source,target)
    elif os.name=='nt':os.rename(source,target)  # Windows rename refuses existing destinations.
    else:
        # No POSIX new-file fallback: all supported new configurations are on the
        # exact Windows bind. Never turn rename's overwrite semantics into a race.
        need(False,'CONTINUATION_NO_CLOBBER_PLATFORM_UNSUPPORTED')


def replace_after_custody(active, staged, expected, raw, custody):
    active,staged=safe_path(active),safe_path(staged)
    need(active.parent==staged.parent and active!=staged and type(raw) is bytes,
         'CONTINUATION_TRANSITION_SCOPE')
    need(not staged.exists() and not staged.is_symlink(),'CONTINUATION_STAGED_EXISTS')
    if expected is None:
        need(custody is None and not active.exists() and not active.is_symlink(),'CONTINUATION_EXPECTED_ABSENT')
    else:
        need(type(custody) is dict,'CONTINUATION_CUSTODY_REQUIRED')
        reader.verify_bytes(custody)
        need(all(custody[k]==expected[k] for k in ('bytes','sha256')) and reader.file_pin(active)==expected,
             'CONTINUATION_ORIGINAL_CHANGED')
    reader.exclusive_bytes(staged,raw)
    need(staged.stat().st_dev==active.parent.stat().st_dev,'CONTINUATION_VOLUME_CHANGED')
    if expected is None:need(not active.exists() and not active.is_symlink(),'CONTINUATION_EXPECTED_ABSENT')
    else:need(reader.file_pin(active)==expected,'CONTINUATION_ORIGINAL_CHANGED')
    safe_path(active);safe_path(staged)
    atomic_move(staged,active,replace=expected is not None)
    reader.sync_parent(active)
    installed=reader.file_pin(active)
    need(installed['bytes']==len(raw) and installed['sha256']==hashlib.sha256(raw).hexdigest(),
         'CONTINUATION_INSTALLED_READBACK_FAILED')
    return dict(installedPin=installed,fileFsyncCompleted=True,atomicMoveCompleted=True,
                powerLossDurabilityVerified=False)


def private_raw(private, reference, pins):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
         type(reference['bytes']) is int and reference['bytes']>=0 and contract.sha(reference['sha256']),
         'CONTINUATION_PRIVATE_PIN_INVALID')
    path=safe_path(reference['path']);root=Path(private).resolve(strict=True)
    need(path.is_relative_to(root),'CONTINUATION_PRIVATE_SCOPE')
    raw=reader.verify_bytes(reference);pins.append(reference)
    return raw


def private_json(private, reference, pins):
    return json.loads(private_raw(private,reference,pins).decode('utf-8'),object_pairs_hook=contract.document)


def validate_failure_records(inputs, input_pin, failure, attempt, stages):
    fields=('sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin','publicationObservationPin')
    binding={k:inputs[k] for k in fields};binding['publicationInputsPin']=input_pin
    need(inputs.get('schemaVersion')=='MainProgramSpugPublicationInputs/v2' and
         failure.get('schemaVersion')=='MainProgramSpugPublicationFailure/v2' and
         failure.get('status')=='FAILED' and failure.get('stage')=='spug-publish' and
         failure.get('retryPermitted') is False and attempt.get('schemaVersion')=='MainProgramSpugPublicationAttempt/v2' and
         attempt.get('retryPermitted') is False and attempt.get('stageOrder')==reader.publication_schedule() and
         all(failure.get(k)==v==attempt.get(k) for k,v in binding.items()),'CONTINUATION_ORIGINAL_BINDING_INVALID')
    need(len(stages)==8 and len(failure['stages'])==8 and
         [r['stage'] for r in failure['stages']]==reader.publication_schedule()[:8],
         'CONTINUATION_ORIGINAL_STAGE_SET_INVALID')
    counts=[]
    for index,(raw,row) in enumerate(zip(stages,failure['stages'])):
        need(set(raw)=={'schemaVersion','stage','result',*binding} and
             raw['schemaVersion']=='MainProgramSpugPublicationStage/v2' and raw['stage']==row['stage'] and
             all(raw.get(k)==v for k,v in binding.items()),'CONTINUATION_ORIGINAL_STAGE_BINDING_INVALID')
        result=raw['result'];phase='preflight' if index<4 else 'publish'
        need(result.get('status')==('FAILED' if index==7 else 'PASS') and result.get('phase')==phase and
             result.get('sourceCommit')==inputs['sourceCommit'] and result.get('backupDispatched') is False and
             result.get('restoreDispatched') is False and type(result.get('completedWrites')) is list,
             'CONTINUATION_ORIGINAL_STAGE_NOT_PROVEN')
        size=len(result['completedWrites'])
        need(size==(6 if index==4 else 3 if index in (5,6) else 0),
             'CONTINUATION_ORIGINAL_PARTIAL_OR_UNKNOWN')
        if index in (4,5,6):counts.append(size)
    need(stages[-1]['result'].get('errorType')=='OSError' and
         '[Errno 30]' in stages[-1]['result'].get('errorCode',''), 'CONTINUATION_NOT_READONLY_BIND_FAILURE')
    return dict(successfulStages=reader.publication_schedule()[:7],failedStage='spug-publish',hostWriteCounts=counts)


def mount_rows(rows):
    return [{key:row.get(key) for key in ('Type','Source','Destination','RW','Name')} for row in rows]


def verify_instances(rows, observation):
    need(type(rows) is list and len(rows)==2,'CONTINUATION_INSTANCE_COUNT')
    for index,(row,port,key) in enumerate(zip(rows,('18080','18081'),('containerSnapshot','protectedContainerSnapshot'))):
        need(row['Id']==observation['containerId' if index==0 else 'protectedContainerId'] and
             row['State']['Running'] is True and row['HostConfig']['PortBindings'].get('80/tcp')==
             [{'HostIp':'127.0.0.1','HostPort':port}] and reader.container_snapshot(row)==observation[key],
             'CONTINUATION_INSTANCE_CHANGED')
    need(rows[0]['Id']==reader.CONTAINER and rows[0]['Name']=='/intruoyi-spug-transfer-spug-1',
         'CONTINUATION_INSTANCE_IDENTITY')


def load_mount_observation(records, private, reference, original_input_pin, failure_pin, spug):
    value=records.pinned(reference);pins=[]
    fields={'schemaVersion','status','observedAt','originalPublicationInputsPin','originalFailurePin',
        'originalRunnerDispatchPin','originalRunnerCompletionPin','originalRunnerPid','originalRunnerAbsent',
        'inspectBefore','inspectAfter','runnerQuery','entryQuery','runnerQueryProgramPin','entryQueryProgramPin',
        'containerId','containerSnapshot','protectedContainerId','protectedContainerSnapshot','mounts','entryIdentity',
        'remoteServerCalls','runtimeWrites','inputPins'}
    need(set(value)==fields and value['schemaVersion']=='SpugReadonlyBindMountObservation/v1' and
         value['status']=='OBSERVED' and value['originalPublicationInputsPin']==original_input_pin and
         value['originalFailurePin']==failure_pin and value['originalRunnerAbsent'] is True and
         type(value['originalRunnerPid']) is int and value['originalRunnerPid']>1 and
         value['remoteServerCalls']==0 and value['runtimeWrites'] is False,'CONTINUATION_MOUNT_OBSERVATION_INVALID')
    outputs={}
    for name in ('inspectBefore','inspectAfter','runnerQuery','entryQuery'):
        receipt=value[name]
        need(set(receipt)=={'requestPin','actualExitCode','stdoutPin','stderrPin'} and
             type(receipt['actualExitCode']) is int and receipt['actualExitCode']==0,
             'CONTINUATION_OBSERVATION_NATIVE_EXIT')
        private_json(private,receipt['requestPin'],pins)
        need(private_raw(private,receipt['stderrPin'],pins)==b'','CONTINUATION_OBSERVATION_STDERR')
        outputs[name]=private_json(private,receipt['stdoutPin'],pins)
    for key in ('runnerQueryProgramPin','entryQueryProgramPin'):private_raw(private,value[key],pins)
    for reference in value['inputPins']:
        # The observation also explicitly pins task-local inputs, outside PRIVATE.
        reader.verify_bytes(reference);pins.append(reference)
    dispatch=private_json(private,value['originalRunnerDispatchPin'],pins)
    completion=private_json(private,value['originalRunnerCompletionPin'],pins)
    need(dispatch.get('hostPid')==value['originalRunnerPid'] and dispatch.get('automaticRetryPermitted') is False and
         completion.get('terminal') is True and completion.get('status')=='FAILED' and
         type(completion.get('actualExitCode')) is int and completion['actualExitCode']!=0 and
         completion.get('corePin') is None and completion.get('backupDispatched') is False and
         completion.get('restoreDispatched') is False,'CONTINUATION_ORIGINAL_RUNNER_NOT_TERMINAL')
    for key in ('stdoutPin','stderrPin'):private_raw(private,completion[key],pins)
    need(outputs['runnerQuery']==dict(pid=value['originalRunnerPid'],count=0),
         'CONTINUATION_ORIGINAL_RUNNER_NOT_ABSENT')
    identity=value['entryIdentity']
    need(set(identity)=={'pid','startTicks','exe'} and outputs['entryQuery']==identity and
         identity['pid']==spug['entryPid'] and type(identity['startTicks']) is int and identity['startTicks']>0 and
         type(identity['exe']) is str and identity['exe'].startswith('/'),'CONTINUATION_ENTRY_IDENTITY_INVALID')
    for key in ('containerId','containerSnapshot','protectedContainerId','protectedContainerSnapshot'):
        need(value[key]==spug[key],'CONTINUATION_ORIGINAL_INSTANCE_CHANGED')
    for name in ('inspectBefore','inspectAfter'):
        verify_instances(outputs[name],value)
        selected=[m for m in mount_rows(outputs[name][0]['Mounts']) if m['Destination'] in
                  (RUN_ROOT,'/opt/intruoyi-spug',VOLUME_ROOT)]
        need(sorted(selected,key=lambda r:r['Destination'])==sorted(value['mounts'],key=lambda r:r['Destination']),
             'CONTINUATION_MOUNT_ORIGINAL_CHANGED')
        # Keep shadowing mounts in the independent classification check.
        classify_writes_placeholder=mount_rows(outputs[name][0]['Mounts'])
        for root in (RUN_ROOT,'/opt/intruoyi-spug',VOLUME_ROOT):
            need(not any(m['Destination'].startswith(root+'/') for m in classify_writes_placeholder),
                 'CONTINUATION_MOUNT_SHADOW')
    return dict(value=value,pins=pins)


def check_custody_barrier(rows, expected_count):
    need(type(rows) is list and len(rows)==expected_count and
         [r.get('index') for r in rows]==list(range(expected_count)),'CONTINUATION_CUSTODY_SET_INVALID')
    for row in rows:
        expected,custody=row['expected'],row['custody']
        if expected is None:need(custody is None,'CONTINUATION_ABSENCE_CUSTODY_INVALID')
        else:
            need(type(custody) is dict,'CONTINUATION_CUSTODY_REQUIRED')
            reader.verify_bytes(custody)
            need(all(custody[k]==expected[k] for k in ('bytes','sha256')),'CONTINUATION_CUSTODY_BYTES_CHANGED')


def validate_source_custody(value, attempt_pin, originals, task, private, *, historical=None):
    need(type(value) is dict and set(value)=={'schemaVersion','originalAttemptPin','entries'} and
         value['schemaVersion']=='MainProgramSpugPublicationSourceCustody/v1' and
         value['originalAttemptPin']==attempt_pin and type(value['entries']) is list,
         'CONTINUATION_SOURCE_CUSTODY_INVALID')
    permitted={str(Path(task)/name) for name in ('main_program_spug_publication.py',
        'main_program_installation_selection.py','observe_closeout_hosts.py')}
    mapped={};pins=[]
    for row in value['entries']:
        need(type(row) is dict and set(row)=={'originalPin','preservedPin'},'CONTINUATION_SOURCE_CUSTODY_ROW')
        old,kept=row['originalPin'],row['preservedPin'];path=str(Path(old['path']))
        need(old in originals and path in permitted and path not in mapped,'CONTINUATION_SOURCE_MAPPING_SCOPE')
        private_raw(private,kept,pins)
        need(all(old[k]==kept[k] for k in ('bytes','sha256')) and
             str(Path(kept['path']))!=path,'CONTINUATION_SOURCE_CUSTODY_CHANGED')
        mapped[path]=kept
    if historical is None:
        for reference in originals:
            path=str(Path(reference['path']))
            if path not in mapped:
                reader.verify_bytes(reference);pins.append(reference)
    else:
        historical.verify_inputs('publication',attempt_pin,originals,
            {row['originalPin']['path']:row for row in value['entries']},pins)
    return pins


def load_failed_originals(records, private, inputs, spec, pins, *, historical=None):
    old=spec['inputs'];old_pin=inputs['originalPublicationInputsPin']
    failure=private_json(private,inputs['originalFailurePin'],pins)
    attempt=private_json(private,inputs['originalAttemptPin'],pins)
    stages=[private_json(private,row['resultPin'],pins) for row in failure['stages']]
    validate_failure_records(old,old_pin,failure,attempt,stages)
    custody=records.pinned(inputs['originalSourceCustodyPin'])
    pins.extend(validate_source_custody(custody,inputs['originalAttemptPin'],attempt['inputPins'],records.task,private,historical=historical))
    for index,(row,stage) in enumerate(zip(failure['stages'],stages)):
        name=row['stage'];lane,phase,*hosts=name.split('-');host=hosts[0] if hosts else None
        root=old['outputFile'][:-5]+'.'+name
        request_path=Path(private)/(root+'.request.private.json')
        request=private_json(private,reader.file_pin(request_path),pins)
        need(request.get('schemaVersion')=='MainProgramSpugPublicationDispatch/v2' and
             request.get('lane')==lane and request.get('host')==('172.30.30.'+host if host else None) and request.get('phase')==phase and
             request.get('retryPermitted') is False and all(request.get(k)==stage[k] for k in original.binding(spec)),
             'CONTINUATION_ORIGINAL_DISPATCH_CHANGED')
        raw=private_raw(private,request['programPin'],pins)
        selected=deepcopy(spec['hostSpecs'][host] if lane=='host' else spec['spugSpec'])
        selected['auditPath']+='-'+old['revisionId']
        need(raw==original.program(lane,host,phase,selected).encode('utf-8'),
             'CONTINUATION_ORIGINAL_PROGRAM_CHANGED')
        if index in (4,5,6):
            need(stage['result']['completedWrites']==[r['path'] for r in selected['selectors']],
                 'CONTINUATION_ORIGINAL_SELECTOR_WRITES_CHANGED')
    state=records.pinned(inputs['failureStatePin'])
    need(state.get('schemaVersion')=='SpugPublicationFailureState/v1' and state.get('status')=='OBSERVED' and
         state.get('failurePin')==inputs['originalFailurePin'] and state.get('actualQueryExitCode')==0 and
         state.get('hostSelectorWritesCompleted')==12 and state.get('spugConfigWritesReported')==0 and
         state.get('spugConfigsActuallyUnchanged') is True and state.get('configurationFileCount')==7 and
         state.get('auditDirectoryExists') is True and state.get('auditDirectoryEntryCount')==0 and
         state.get('protectedSpugUnchanged') is True and state.get('remoteServerCalls')==0 and
         state.get('runtimeWrites') is False,'CONTINUATION_FAILURE_STATE_NOT_PROVEN')
    observed=private_json(private,state['privateEvidencePin'],pins)
    need(observed['failurePin']==inputs['originalFailurePin'] and observed['actualQueryExitCode']==0 and
         observed['stages']==state['stages'] and state['stages']==[
             dict(stage=row['stage'],status=raw['result']['status'],
                  completedWriteCount=len(raw['result']['completedWrites']),resultPin=row['resultPin'])
             for row,raw in zip(failure['stages'],stages)],'CONTINUATION_FAILURE_STAGE_OBSERVATION_CHANGED')
    private_raw(private,observed['queryProgramPin'],pins)
    need(private_raw(private,observed['queryStderrPin'],pins)==b'','CONTINUATION_FAILURE_QUERY_STDERR')
    actual=private_json(private,observed['queryStdoutPin'],pins)
    need(actual==observed['containerObservation'] and actual['status']=='OBSERVED' and
         actual['configsUnchanged'] is True and actual['configCount']==7 and actual['runtimeWrites'] is False and
         actual['configPins']==[dict(path=r['path'],currentPin=r['expected']) for r in spec['spugSpec']['writes']] and
         actual['auditPath']==spec['spugSpec']['auditPath']+'-'+old['revisionId'] and
         actual['auditExists'] is True and actual['auditChildren']==[], 'CONTINUATION_FAILED_CONFIG_STATE_CHANGED')
    return failure


def load_resource_installation(records, private, reference, context, spug, pins):
    report=records.pinned(reference)
    need(report.get('schemaVersion')=='MainProgramSpugResourceActivation/v2' and report.get('status')=='PASS' and
         report.get('resourceBuildPin')==context['binding']['spugResourceBuildPin'] and
         report.get('sourceCommit')==context['resource']['sourceCommit'] and report.get('entryPid')==spug['entryPid'] and
         all(report.get(k) is True for k in ('oldResourcesPreserved','originalBehaviorVerified',
             'otherEightResourcesUnchanged','protectedSpugUnchanged','settingsAndConnectionsUnchanged')) and
         all(report.get(k) is False for k in ('sharedServiceRestarted','backupDispatched','restoreDispatched')),
         'CONTINUATION_RESOURCE_INSTALLATION_REQUIRED')
    rich=private_json(private,report['privateEvidencePin'],pins)
    need(rich.get('status')=='PASS' and rich.get('stage')=='complete' and
         rich.get('resourceBuildPin')==report['resourceBuildPin'] and rich.get('sourceCommit')==report['sourceCommit'] and
         rich.get('replacements')==report['replacements'] and rich.get('newEntryIdentity',{}).get('pid')==spug['entryPid'] and
         rich.get('backupDispatched') is False and rich.get('restoreDispatched') is False,
         'CONTINUATION_RESOURCE_EVIDENCE_CHANGED')
    delta=records.pinned(report['deploymentDeltaPin'])
    need(delta['resourceBuildPin']==report['resourceBuildPin'] and
         [r['relativePath'] for r in report['replacements']]==[r['relativePath'] for r in delta['changes']],
         'CONTINUATION_RESOURCE_DELTA_CHANGED')
    for change,row in zip(delta['changes'],report['replacements']):
        expected=context['resource']['files']['ops/spug/'+row['relativePath']]
        need(all(row['installedPin'][k]==expected[k] for k in ('bytes','sha256')) and
             all(row['previousPin'][k]==change['beforePin'][k] for k in ('bytes','sha256')),
             'CONTINUATION_RESOURCE_FILE_CHANGED')
        private_raw(private,row['previousPin'],pins)
    # Runtime files are read by the original container preflight/verify. Historical
    # reader validation does not require an old checkout or current live resources.
    return report


def prepare_continuation(task, private, inputs_file):
    records=contract.Records(Path(task));inputs=records.read(inputs_file);input_pin=records.references[inputs_file]
    return prepare_value(records,Path(private),inputs,input_pin)


def prepare_value(records, private, inputs, input_pin, *, historical=None):
    fields={'schemaVersion','sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin',
        'originalPublicationInputsPin','originalAttemptPin','originalFailurePin','originalSourceCustodyPin',
        'failureStatePin','mountObservationPin','resourceActivationPin','continuationId','outputFile'}
    need(type(inputs) is dict and set(inputs)==fields and inputs['schemaVersion']=='MainProgramSpugPublicationInputs/v3' and
         type(inputs['continuationId']) is str and re.fullmatch('c[1-9][0-9]*',inputs['continuationId']),
         'CONTINUATION_INPUTS_INVALID')
    old=records.pinned(inputs['originalPublicationInputsPin'])
    need(all(inputs[k]==old[k] for k in ('sourceCommit','revisionId','controlGenerationPin','spugResourceBuildPin')) and
         inputs['outputFile']==old['outputFile'][:-5]+'-continuation-'+inputs['continuationId']+'.json',
         'CONTINUATION_GENERATION_OR_OUTPUT_CHANGED')
    context=reader.v2_context(records,private,old,inputs['originalPublicationInputsPin'])
    bundle=context['generation'];secret=dict(bundle['privatePlan'],programTargets=bundle['plan']['programTargets'])
    spec=reader._prepare_publication_graph(records,old,private,bundle['plan'],secret,bundle['controllersByHost'],
        bundle['targets'],[],[],context['resource'],context['resourcePins'],extra_pins=bundle['inputPins'])
    spec.update(publicationInputsPin=inputs['originalPublicationInputsPin'],
                generationPins={k:bundle['generation'][k] for k in ('buildPin','planPin')})
    pins=[];failure=load_failed_originals(records,private,inputs,spec,pins,historical=historical)
    mount=load_mount_observation(records,private,inputs['mountObservationPin'],inputs['originalPublicationInputsPin'],
                                 inputs['originalFailurePin'],spec['spugSpec']['observation']);pins.extend(mount['pins'])
    routes=classify_writes(spec['spugSpec']['writes'],mount['value']['mounts'])
    resource=load_resource_installation(records,private,inputs['resourceActivationPin'],context,
                                       spec['spugSpec']['observation'],pins)
    original_audit=spec['spugSpec']['auditPath']+'-'+old['revisionId']
    for value in spec['hostSpecs'].values():value['auditPath']+='-'+old['revisionId']
    spec['spugSpec']['auditPath']=original_audit+'-continuation-'+inputs['continuationId']
    pins=spec['inputPins']+records.path_pins()+pins+[reader.file_pin(__file__),reader.file_pin(original.__file__)]
    unique={}
    for pin in pins:
        key=str(Path(pin['path']))
        need(key not in unique or unique[key]==pin,'CONTINUATION_INPUT_CONFLICT');unique[key]=pin
    result=dict(originalSpec=spec,inputs=inputs,inputPin=input_pin,inputPins=list(unique.values()),context=context,
        originalFailure=failure,mountObservation=mount['value'],routes=routes,resourceInstallation=resource,
        originalAuditPath=original_audit)
    import common
    profile=Path('C:/Spug/runtime/private/runtime-versions.private.json')
    profiles=json.loads(profile.read_bytes())['profiles'];commands={}
    for host in contract.HOSTS:
        executable=next(p['python'] for p in profiles if p['host']=='172.30.30.'+host)
        if host=='58':executable='/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12'
        elif host=='57':executable='/usr/local/libexec/spug-source-control-20261105/python/bin/python3.12'
        commands[host]=[*common.SSH,'root@172.30.30.'+host,executable+' -B -']
    result['hostCommands']=commands
    result['inputPins'] += [reader.file_pin(common.__file__),reader.file_pin(profile)]
    unchanged(result)
    return result


def unchanged(prepared):
    for reference in prepared['inputPins']:reader.verify_bytes(reference)


def execute_write_batch(writes, custody, states, install, readback, record):
    check_custody_barrier(custody,len(writes))
    need(not states,'CONTINUATION_BATCH_ALREADY_STARTED')
    states.extend(dict(index=i,path=row['path'],state='NOT_STARTED') for i,row in enumerate(writes))
    for index,row in enumerate(writes):
        state=states[index];state['state']='DISPATCHED_OUTCOME_UNKNOWN';record(index,state)
        state['nativeResult']=install(index)
        actual=readback(index);expected=reader.canonical(row['value'])
        need(actual==dict(path=row['path'],bytes=len(expected),sha256=hashlib.sha256(expected).hexdigest()),
             'CONTINUATION_CONTAINER_READBACK_CHANGED')
        state.update(state='APPLIED',containerReadbackPin=actual);record(index,state)
    return states


CONTAINER_BODY = r'''
import base64,types,stat,sys
reader=types.SimpleNamespace(file_pin=file_pin,verify_bytes=verify_bytes,
 exclusive_bytes=exclusive_bytes,sync_parent=sync_parent)
SPEC=json.loads(__SPEC_JSON__)
out=dict(status='FAILED',phase=SPEC['phase'],sourceCommit=SPEC['sourceCommit'],
 backupDispatched=False,restoreDispatched=False)
try:
 identity=SPEC['entryIdentity'];process=Path('/proc')/str(identity['pid'])
 actual=dict(pid=identity['pid'],startTicks=int((process/'stat').read_text().rsplit(')',1)[1].split()[19]),
  exe=str((process/'exe').resolve(strict=True)))
 need(actual==identity,'CONTINUATION_ENTRY_CHANGED')
 old=safe_path(SPEC['originalAuditPath'])
 need(old.is_dir() and not old.is_symlink() and not list(old.iterdir()),'CONTINUATION_OLD_AUDIT_CHANGED')
 audit=Path(SPEC['auditPath']);safe_path(audit)
 if SPEC['phase']=='custody':
  need(not audit.exists(),'CONTINUATION_AUDIT_EXISTS')
  for row in SPEC['writes']:
   path=safe_path(row['path'])
   if row['expected'] is None:need(not path.exists(),'CONTINUATION_EXPECTED_ABSENT')
   else:need(file_pin(path)==row['expected'],'CONTINUATION_ORIGINAL_CHANGED')
  audit.mkdir(mode=0o700);rows=[]
  for index,row in enumerate(SPEC['writes']):
   expected=row['expected'];raw=None;archive=None
   if expected is not None:
    raw=verify_bytes(expected);archive=exclusive_bytes(audit/('before-'+str(index)+'.private.json'),raw)
    need(all(archive[k]==expected[k] for k in ('bytes','sha256')),'CONTINUATION_CUSTODY_CHANGED')
   rows.append(dict(index=index,path=row['path'],expected=expected,archivePin=archive,
    rawBase64=None if raw is None else base64.b64encode(raw).decode('ascii')))
  exclusive_bytes(audit/'custody.private.json',canonical(rows))
  out.update(status='PASS',rows=rows)
 elif SPEC['phase'] in ('guard','guard-before-custody'):
  before_custody=SPEC['phase']=='guard-before-custody'
  index=0 if before_custody else SPEC['index'];need(index in (0,1,2,3,6),'CONTINUATION_HOST_GUARD_SCOPE')
  if before_custody:need(not audit.exists(),'CONTINUATION_AUDIT_EXISTS')
  for i,row in enumerate(SPEC['writes']):
   target=safe_path(row['path']);expected=row['expected']
   if i<index:
    raw=canonical(row['value']);expected=dict(path=row['path'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   if expected is None:need(not target.exists(),'CONTINUATION_EXPECTED_ABSENT')
   else:need(file_pin(target)==expected,'CONTINUATION_BEFORE_WRITE_CHANGED')
   if row['expected'] is not None and not before_custody:
    kept=file_pin(audit/('before-'+str(i)+'.private.json'))
    need(all(kept[k]==row['expected'][k] for k in ('bytes','sha256')),'CONTINUATION_CUSTODY_CHANGED')
  out.update(status='PASS',index=index,entryIdentity=actual)
 elif SPEC['phase']=='write':
  index=SPEC['index'];row=SPEC['writes'][index]
  need(index in (4,5) and row['path'] in ('/var/lib/intruoyi-spug/smallapp-simple-settings.json',
       '/var/lib/intruoyi-spug/smallapp-entry-settings.json'),'CONTINUATION_VOLUME_WRITE_SCOPE')
  archive=file_pin(audit/('before-'+str(index)+'.private.json'))
  target=Path(row['path']);pending=target.with_name(target.name+'.'+SPEC['nonce']+'.pending')
  out.update(status='PASS',transition=replace_after_custody(target,pending,row['expected'],canonical(row['value']),archive))
 elif SPEC['phase']=='readback':
  row=SPEC['writes'][SPEC['index']];out.update(status='PASS',installedPin=file_pin(row['path']))
 else:need(False,'CONTINUATION_COMMAND_SCOPE')
except BaseException as error:out.update(errorType=type(error).__name__,errorCode=str(error))
print(json.dumps(out));sys.exit(0 if out['status']=='PASS' else 1)
'''


def container_program(prepared,phase,index=None):
    spug=prepared['originalSpec']['spugSpec'];inputs=prepared['inputs']
    spec=dict(sourceCommit=inputs['sourceCommit'],phase=phase,writes=spug['writes'],auditPath=spug['auditPath'],
        originalAuditPath=prepared['originalAuditPath'],entryIdentity=prepared['mountObservation']['entryIdentity'],
        nonce=inputs['sourceCommit'][:7]+'-'+inputs['revisionId']+'-'+inputs['continuationId'],index=index)
    functions=''.join(inspect.getsource(fn)+'\n' for fn in (safe_path,atomic_move,replace_after_custody))
    return reader.embedded_helpers()+'\n'+functions+CONTAINER_BODY.replace('__SPEC_JSON__',repr(reader.canonical(spec).decode('utf-8')))


class ActualContinuationTransport:
    """Capture each native invocation privately, including every nonzero exit."""
    def __init__(self,private,prepared):
        self.private,self.prepared=Path(private),prepared
        self.stem=prepared['inputs']['outputFile'][:-5];self.counter=0;self.receipts=[]

    def command(self,label,argv,program=None,timeout=240):
        self.counter+=1;stem=self.stem+'.native-'+str(self.counter)+'-'+label
        source=None
        if program is not None:
            source=reader.exclusive_bytes(self.private/(stem+'.program.private.py'),program.encode('utf-8'))
        request=reader.exclusive_bytes(self.private/(stem+'.request.private.json'),reader.canonical(
            dict(argv=argv,stdinPin=source,timeoutSeconds=timeout,automaticRetryPermitted=False)))
        outpath=self.private/(stem+'.stdout.private.log');errpath=self.private/(stem+'.stderr.private.log')
        result=dict(schemaVersion='MainProgramSpugContinuationNative/v1',label=label,requestPin=request,
            actualExitCode=None,status='UNKNOWN',hostPid=None,stdinPin=source)
        self.receipts.append(dict(path=str(self.private/(stem+'.receipt.private.json')),bytes=0,sha256='0'*64))
        try:
            with (open(source['path'],'rb') if source else open(os.devnull,'rb')) as inp, \
                    outpath.open('xb') as stdout,errpath.open('xb') as stderr:
                child=subprocess.Popen(argv,stdin=inp,stdout=stdout,stderr=stderr)
                result['hostPid']=child.pid
                reader.exclusive_bytes(self.private/(stem+'.dispatch.private.json'),reader.canonical(result))
                try:result['actualExitCode']=child.wait(timeout)
                except subprocess.TimeoutExpired:
                    # Killing only the local CLI cannot prove the remote worker
                    # stopped. The persistent publication claim remains held.
                    child.kill();child.wait(10);raise
                result['status']='EXITED'
            result.update(stdoutPin=reader.file_pin(outpath),stderrPin=reader.file_pin(errpath))
            need(type(result['actualExitCode']) is int and result['actualExitCode']==0,
                 'CONTINUATION_NATIVE_EXIT_FAILED')
            return json.loads(outpath.read_bytes().decode('utf-8'),object_pairs_hook=contract.document)
        except BaseException as error:
            result.update(errorType=type(error).__name__,errorCode=str(error))
            if outpath.is_file():result['stdoutPin']=reader.file_pin(outpath)
            if errpath.is_file():result['stderrPin']=reader.file_pin(errpath)
            raise
        finally:
            reference=reader.exclusive_bytes(self.private/(stem+'.receipt.private.json'),reader.canonical(result))
            self.receipts[-1]=reference

    def inspect_current(self):
        observation=self.prepared['mountObservation']
        rows=self.command('inspect',[reader.DOCKER,'inspect',reader.CONTAINER,observation['protectedContainerId']])
        verify_instances(rows,observation)
        actual=mount_rows(rows[0]['Mounts']);classify_writes(self.prepared['originalSpec']['spugSpec']['writes'],actual)
        selected=[r for r in actual if r['Destination'] in (RUN_ROOT,'/opt/intruoyi-spug',VOLUME_ROOT)]
        need(sorted(selected,key=lambda r:r['Destination'])==sorted(observation['mounts'],key=lambda r:r['Destination']),
             'CONTINUATION_LIVE_MOUNT_CHANGED')

    def container(self,label,program):
        self.inspect_current()
        nonce='spug-continuation-'+self.prepared['inputs']['originalFailurePin']['sha256'][:24]
        result=self.command(label,[reader.DOCKER,'exec','-i',reader.CONTAINER,'python3','-B','-',nonce],program)
        self.inspect_current();result['protectedSpugUnchanged']=True
        need(result.get('status')=='PASS','CONTINUATION_CONTAINER_PROGRAM_FAILED')
        return result

    def host_verify(self,host,program):
        need(host in contract.HOSTS,'CONTINUATION_HOST_SCOPE')
        # Same exact SSH profile selection as the established publication helper,
        # with actual stdout/stderr and native exit retained for this invocation.
        result=self.command('host-verify-'+host,self.prepared['hostCommands'][host],program,600)
        need(result.get('status')=='PASS','CONTINUATION_HOST_VERIFY_FAILED')
        return result

    def prepare_custody(self):
        result=self.container('custody',container_program(self.prepared,'custody'));rows=result['rows'];local=[]
        writes=self.prepared['originalSpec']['spugSpec']['writes']
        need(type(rows) is list and len(rows)==len(writes),'CONTINUATION_CUSTODY_SET_INVALID')
        for index,(row,planned) in enumerate(zip(rows,writes)):
            need(set(row)=={'index','path','expected','archivePin','rawBase64'} and row['index']==index and
                 row['path']==planned['path'] and row['expected']==planned['expected'],'CONTINUATION_CUSTODY_BINDING')
            kept=None
            if planned['expected'] is None:need(row['archivePin'] is None and row['rawBase64'] is None,'CONTINUATION_ABSENCE_INVALID')
            else:
                raw=base64.b64decode(row['rawBase64'],validate=True)
                need(len(raw)==planned['expected']['bytes'] and hashlib.sha256(raw).hexdigest()==planned['expected']['sha256'] and
                     all(row['archivePin'][k]==planned['expected'][k] for k in ('bytes','sha256')),
                     'CONTINUATION_CUSTODY_BYTES_CHANGED')
                kept=reader.exclusive_bytes(self.private/(self.stem+'.before-'+str(index)+'.private.json'),raw)
            local.append(dict(index=index,expected=planned['expected'],custody=kept,containerArchivePin=row['archivePin']))
        check_custody_barrier(local,len(writes))
        validate_container_custody(self.prepared,local,result)
        return local

    def install(self,index,custody):
        unchanged(self.prepared);route=self.prepared['routes'][index]
        writes=self.prepared['originalSpec']['spugSpec']['writes'];row=writes[index]
        if route['executor']=='CONTAINER_VOLUME':
            return self.container('write-'+str(index),container_program(self.prepared,'write',index))['transition']
        self.container('guard-'+str(index),container_program(self.prepared,'guard',index))
        target=Path(route['hostPath']);expected=None if row['expected'] is None else dict(row['expected'],path=str(target))
        pending=target.with_name(target.name+'.'+self.stem+'.pending')
        result=replace_after_custody(target,pending,expected,reader.canonical(row['value']),custody[index]['custody'])
        self.inspect_current();return result

    def readback(self,index):
        return self.container('readback-'+str(index),container_program(self.prepared,'readback',index))['installedPin']


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',required=True);p.add_argument('--apply',action='store_true')
    p.add_argument('--task',type=Path,default=TASK);p.add_argument('--private',type=Path,default=PRIVATE)
    return p


def run_request(task,private,inputs_file,*,apply=False,transport=None):
    prepared=prepare_continuation(task,private,inputs_file)
    if not apply:return dict(status='PREPARED_NOT_APPLIED',sourceCommit=prepared['inputs']['sourceCommit'],
        revisionId=prepared['inputs']['revisionId'],continuationId=prepared['inputs']['continuationId'],
        remoteDispatched=False,configurationFiles=7,hostPublishDispatched=False)
    return execute_prepared(Path(task),Path(private),prepared,transport=transport)


def continuation_binding(prepared):
    inputs=prepared['inputs']
    return dict(continuationInputsPin=prepared['inputPin'],**{k:inputs[k] for k in
        ('sourceCommit','revisionId','continuationId','controlGenerationPin','spugResourceBuildPin','originalFailurePin')})


def continuation_schedule():
    return ['spug-continuation-preflight','spug-custody','spug-configuration-publish',
            'host-verify-57','host-verify-58','host-verify-59','spug-verify']


def aggregate_final(prepared, stages):
    need([r['stage'] for r in stages]==continuation_schedule(),'CONTINUATION_STAGE_SET_INCOMPLETE')
    hosts=[r['result'] for r in stages[3:6]];spug=stages[-1]['result']
    return dict(status='PASS',sourceCommit=prepared['inputs']['sourceCommit'],publicationCompleted=True,
        selectorCount=sum(r['selectorCount'] for r in hosts),applicationCount=spug['applicationCount'],taskCount=spug['taskCount'],
        backupDispatched=False,restoreDispatched=False,
        **{key:all(r.get(key) is True for r in hosts) for key in ('selectorsReadBack','actualNativeSelectionsVerified',
            'businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')},
        **{key:spug[key] for key in ('productSettingsReadBack','historicalFingerprintsUnchanged',
            'protectedSpugUnchanged','oldTasksUnchanged','productFilesUnchanged')},
        oldFilesPreserved=all(r['oldFilesPreserved'] is True for r in hosts) and spug['oldFilesPreserved'] is True)


def execute_prepared(task,private,prepared,*,transport=None):
    unchanged(prepared);inputs=prepared['inputs'];stem=inputs['outputFile'][:-5]
    paths=[task/inputs['outputFile'],private/(stem+'.private.json'),private/(stem+'.attempt.private.json')]
    need(not any(p.exists() or p.is_symlink() for p in paths),'CONTINUATION_ATTEMPT_EXISTS')
    binding=continuation_binding(prepared)
    claim=private/('spug-publication-failure-'+inputs['originalFailurePin']['sha256']+'.claim.private.json')
    gate=private/('spug-publication-container-'+reader.CONTAINER+'.gate.private.json')
    # Both are permanent audit records; any failure/unknown outcome requires a new
    # explicit review, never deleting a claim and silently retrying this command.
    need(not claim.exists() and not gate.exists(),'CONTINUATION_PUBLICATION_ALREADY_CLAIMED')
    reader.exclusive_bytes(gate,reader.canonical(dict(**binding,automaticRetryPermitted=False)))
    reader.exclusive_bytes(claim,reader.canonical(dict(**binding,gatePin=reader.file_pin(gate))))
    attempt=reader.exclusive_bytes(paths[2],reader.canonical(dict(schemaVersion='MainProgramSpugPublicationAttempt/v3',
        **binding,inputPins=prepared['inputPins'],originalAttemptPin=inputs['originalAttemptPin'],
        stageOrder=continuation_schedule(),retryPermitted=False,gatePin=reader.file_pin(gate),claimPin=reader.file_pin(claim))))
    transport=transport or ActualContinuationTransport(private,prepared)
    rows=[];states=[];state_records=[];custody=[];current='spug-continuation-preflight'
    def stage(name,operation,program=None):
        nonlocal current
        current=name;unchanged(prepared)
        program_pin=None if program is None else reader.exclusive_bytes(private/(stem+'.'+name+'.program.private.py'),program.encode('utf-8'))
        request_pin=reader.exclusive_bytes(private/(stem+'.'+name+'.request.private.json'),reader.canonical(
            dict(schemaVersion='MainProgramSpugPublicationDispatch/v3',**binding,stage=name,programPin=program_pin,retryPermitted=False)))
        start=len(transport.receipts)
        try:
            result=operation()
            need(result.get('status')=='PASS','CONTINUATION_STAGE_NOT_PROVEN')
            return result
        except BaseException as error:
            result=dict(status='UNKNOWN',errorType=type(error).__name__,errorCode=str(error));raise
        finally:
            raw=dict(schemaVersion='MainProgramSpugPublicationStage/v3',**binding,stage=name,requestPin=request_pin,
                     result=result,nativeReceiptPins=deepcopy(transport.receipts[start:]))
            pin=reader.exclusive_bytes(private/(stem+'.'+name+'.private.json'),reader.canonical(raw))
            rows.append(dict(stage=name,resultPin=pin,result=result))
    try:
        spug=prepared['originalSpec']['spugSpec']
        code=original.program('spug',None,'preflight',spug)
        def current_preflight():
            transport.container('guard-before-custody',container_program(prepared,'guard-before-custody'))
            return transport.container('spug-continuation-preflight',code)
        stage(current,current_preflight,code)
        def save_custody():
            nonlocal custody
            custody=transport.prepare_custody();check_custody_barrier(custody,7)
            return dict(status='PASS',rows=custody)
        stage('spug-custody',save_custody,container_program(prepared,'custody'))
        def record(index,state):
            phase='dispatched' if state['state']=='DISPATCHED_OUTCOME_UNKNOWN' else 'applied'
            pin=reader.exclusive_bytes(private/(stem+'.write-'+str(index)+'-'+phase+'.private.json'),
                                       reader.canonical(dict(**binding,write=deepcopy(state))))
            state_records.append(dict(index=index,state=state['state'],pin=pin))
        def publish():
            execute_write_batch(spug['writes'],custody,states,lambda i:transport.install(i,custody),transport.readback,record)
            return dict(status='PASS',writeResults=deepcopy(states),stateRecords=deepcopy(state_records))
        stage('spug-configuration-publish',publish)
        for host in contract.HOSTS:
            code=original.program('host',host,'verify',prepared['originalSpec']['hostSpecs'][host])
            result=stage('host-verify-'+host,lambda host=host,code=code:transport.host_verify(host,code),code)
            reader.validate_verify_stage(prepared['context'],prepared['context']['generation'],host,result)
        code=original.program('spug',None,'verify',spug)
        result=stage('spug-verify',lambda:transport.container('spug-verify',code),code)
        reader.validate_verify_stage(prepared['context'],prepared['context']['generation'],None,result)
        unchanged(prepared);observed=aggregate_final(prepared,rows)
        core=reader.project_core(prepared['originalSpec'],observed)
        rich=dict(observed)
        rich.update(schemaVersion='MainProgramSpugPublicationEvidence/v3',**binding,stage='complete',
            originalStages=prepared['originalFailure']['stages'],attemptPin=attempt,
            stages=[{k:r[k] for k in ('stage','resultPin')} for r in rows])
        reader.exclusive_bytes(paths[1],reader.canonical(rich))
        core_raw=reader.canonical(core);core_pin=dict(file=inputs['outputFile'],bytes=len(core_raw),sha256=hashlib.sha256(core_raw).hexdigest())
        selection=dict(schemaVersion='TaskMainProgramInstallations/v3',sourceCommit=inputs['sourceCommit'],
            controlGenerationPin=inputs['controlGenerationPin'],spugInstallationPin=core_pin,continuationInputsPin=prepared['inputPin'])
        records=original.PendingCoreRecords(task,core_pin,core)
        validate_publication_v3(records,private,selection)
        unchanged(prepared);reader.exclusive_bytes(paths[0],core_raw)
        return core
    except BaseException as error:
        failure=dict(schemaVersion='MainProgramSpugPublicationFailure/v3',**binding,status='FAILED',stage=current,
            originalStages=prepared['originalFailure']['stages'],attemptPin=attempt,
            stages=[{k:r[k] for k in ('stage','resultPin')} for r in rows],writeStates=states,stateRecords=state_records,
            custody=custody,errorType=type(error).__name__,errorCode=str(error),retryPermitted=False)
        destination=private/(stem+('.finalization-failure.private.json' if paths[1].exists() else '.private.json'))
        reader.exclusive_bytes(destination,reader.canonical(failure))
        raise ValueError('MAIN_SPUG_CONTINUATION_FAILED_CHECK_PRIVATE_EVIDENCE') from None


def validate_native_receipts(private,references,pins):
    need(type(references) is list and references,'CONTINUATION_NATIVE_RECEIPTS_REQUIRED')
    values=[]
    for reference in references:
        value=private_json(private,reference,pins)
        need(set(value)=={'schemaVersion','label','requestPin','actualExitCode','status','hostPid','stdinPin','stdoutPin','stderrPin'} and
             value.get('schemaVersion')=='MainProgramSpugContinuationNative/v1' and value.get('status')=='EXITED' and
             type(value.get('actualExitCode')) is int and value['actualExitCode']==0 and
             type(value.get('hostPid')) is int and value['hostPid']>1 and
             'errorType' not in value and 'errorCode' not in value,'CONTINUATION_NATIVE_NOT_SUCCESSFUL')
        request=private_json(private,value['requestPin'],pins)
        need(set(request)=={'argv','stdinPin','timeoutSeconds','automaticRetryPermitted'} and
             request.get('automaticRetryPermitted') is False and request.get('stdinPin')==value['stdinPin'],
             'CONTINUATION_NATIVE_REQUEST_CHANGED')
        if value['stdinPin'] is not None:private_raw(private,value['stdinPin'],pins)
        private_raw(private,value['stderrPin'],pins)
        output=private_json(private,value['stdoutPin'],pins)
        values.append((value,request,output))
    return values


def validate_publication_v3(records,private,selected):
    need(set(selected)=={'schemaVersion','sourceCommit','controlGenerationPin','spugInstallationPin','continuationInputsPin'} and
         selected['schemaVersion']=='TaskMainProgramInstallations/v3','CONTINUATION_SELECTION_INVALID')
    inputs=records.pinned(selected['continuationInputsPin'])
    prepared=prepare_value(records,private,inputs,selected['continuationInputsPin']);binding=continuation_binding(prepared)
    need(selected['sourceCommit']==inputs['sourceCommit'] and selected['controlGenerationPin']==inputs['controlGenerationPin'] and
         selected['spugInstallationPin']['file']==inputs['outputFile'],'CONTINUATION_SELECTION_BINDING_CHANGED')
    pins=[];path=Path(private)/(inputs['outputFile'][:-5]+'.private.json')
    rich=private_json(private,reader.file_pin(path),pins)
    expected={'schemaVersion','status','stage',*binding,'originalStages','attemptPin','stages','selectorCount','applicationCount',
              'taskCount','backupDispatched','restoreDispatched',*reader.TRUE_CHECKS}
    need(set(rich)==expected and rich['schemaVersion']=='MainProgramSpugPublicationEvidence/v3' and
         rich['status']=='PASS' and rich['stage']=='complete' and all(rich[k]==v for k,v in binding.items()) and
         rich['originalStages']==prepared['originalFailure']['stages'],'CONTINUATION_RICH_BINDING_INVALID')
    attempt=private_json(private,rich['attemptPin'],pins)
    need(set(attempt)=={'schemaVersion',*binding,'inputPins','originalAttemptPin','stageOrder','retryPermitted','gatePin','claimPin'} and
         attempt.get('schemaVersion')=='MainProgramSpugPublicationAttempt/v3' and attempt.get('retryPermitted') is False and
         attempt.get('stageOrder')==continuation_schedule() and all(attempt.get(k)==v for k,v in binding.items()) and
         attempt.get('originalAttemptPin')==inputs['originalAttemptPin'],'CONTINUATION_ATTEMPT_BINDING_CHANGED')
    for reference in attempt['inputPins']:reader.verify_bytes(reference);pins.append(reference)
    for key in ('gatePin','claimPin'):
        claim=private_json(private,attempt[key],pins)
        need(all(claim.get(k)==v for k,v in binding.items()),'CONTINUATION_CLAIM_CHANGED')
    need(type(rich['stages']) is list and [r.get('stage') for r in rich['stages']]==continuation_schedule() and
         len({r['resultPin']['path'] for r in rich['stages']})==7,'CONTINUATION_STAGE_SET_INVALID')
    rows=[];custody=[]
    for row in rich['stages']:
        need(set(row)=={'stage','resultPin'},'CONTINUATION_STAGE_ROW_INVALID')
        raw=private_json(private,row['resultPin'],pins);name=row['stage']
        need(set(raw)=={'schemaVersion',*binding,'stage','requestPin','result','nativeReceiptPins'} and
             raw['schemaVersion']=='MainProgramSpugPublicationStage/v3' and raw['stage']==name and
             all(raw[k]==v for k,v in binding.items()) and raw['result'].get('status')=='PASS',
             'CONTINUATION_STAGE_BINDING_INVALID')
        request=private_json(private,raw['requestPin'],pins)
        need(set(request)=={'schemaVersion',*binding,'stage','programPin','retryPermitted'} and
             request.get('schemaVersion')=='MainProgramSpugPublicationDispatch/v3' and request.get('stage')==name and
             request.get('retryPermitted') is False and all(request.get(k)==v for k,v in binding.items()),
             'CONTINUATION_STAGE_REQUEST_CHANGED')
        native=validate_native_receipts(private,raw['nativeReceiptPins'],pins)
        validate_native_targets(prepared,native)
        result=raw['result'];program=None
        if name.startswith('host-verify-'):
            host=name.rsplit('-',1)[1];program=original.program('host',host,'verify',prepared['originalSpec']['hostSpecs'][host])
            reader.validate_verify_stage(prepared['context'],prepared['context']['generation'],host,result)
        elif name in ('spug-verify','spug-continuation-preflight'):
            phase='verify' if name=='spug-verify' else 'preflight'
            program=original.program('spug',None,phase,prepared['originalSpec']['spugSpec'])
            if phase=='verify':reader.validate_verify_stage(prepared['context'],prepared['context']['generation'],None,result)
            else:
                commands=[(v,q,out) for v,q,out in native if v['label']!='inspect']
                need([v['label'] for v,q,out in commands]==['guard-before-custody','spug-continuation-preflight'],
                     'CONTINUATION_PREFLIGHT_GUARD_MISSING')
                value,req,out=commands[0]
                need(private_raw(private,value['stdinPin'],pins)==container_program(prepared,'guard-before-custody').encode('utf-8') and
                     out.get('status')=='PASS' and out.get('entryIdentity')==prepared['mountObservation']['entryIdentity'] and
                     out.get('phase')=='guard-before-custody','CONTINUATION_PREFLIGHT_GUARD_CHANGED')
        elif name=='spug-custody':
            program=container_program(prepared,'custody');custody=result['rows'];check_custody_barrier(custody,7)
            for index,(kept,planned) in enumerate(zip(custody,prepared['originalSpec']['spugSpec']['writes'])):
                need(kept['index']==index and kept['expected']==planned['expected'],'CONTINUATION_CUSTODY_CHANGED')
                if kept['custody'] is not None:private_raw(private,kept['custody'],pins)
        else:
            need(name=='spug-configuration-publish' and len(custody)==7,'CONTINUATION_CUSTODY_NOT_COMPLETE')
            validate_write_results(prepared,private,result,pins)
            validate_publish_native(prepared,private,result,native,pins)
        if program is not None:
            need(private_raw(private,request['programPin'],pins)==program.encode('utf-8'),
                 'CONTINUATION_STAGE_PROGRAM_CHANGED')
            candidates=[(value,output) for value,req,output in native if value['stdinPin'] is not None and
                private_raw(private,value['stdinPin'],pins)==program.encode('utf-8')]
            need(len(candidates)==1 and candidates[0][1].get('status')=='PASS','CONTINUATION_PROGRAM_NATIVE_RESULT_MISSING')
            if name=='spug-custody':validate_container_custody(prepared,custody,candidates[0][1])
            else:
                actual=dict(candidates[0][1]);actual.update(protectedSpugUnchanged=True) if name.startswith('spug-') else None
                need(actual==result,'CONTINUATION_NATIVE_RESULT_CHANGED')
        rows.append(dict(stage=name,result=result))
    aggregate=aggregate_final(prepared,rows)
    need(all(rich[k]==v for k,v in aggregate.items()) and records.pinned(selected['spugInstallationPin'])==
         reader.project_core(prepared['originalSpec'],aggregate),'CONTINUATION_CORE_NOT_PROVEN')
    all_pins=prepared['inputPins']+records.path_pins()+pins
    unique={str(Path(pin['path'])):pin for pin in all_pins}
    for reference in unique.values():reader.verify_bytes(reference)
    return dict(generation=prepared['context']['generation'],inputPins=list(unique.values()))


def validate_write_results(prepared,private,result,pins):
    writes=prepared['originalSpec']['spugSpec']['writes'];states=result.get('writeResults');records=result.get('stateRecords')
    need(type(states) is list and len(states)==7 and type(records) is list and len(records)==14,
         'CONTINUATION_WRITE_RECEIPTS_INCOMPLETE')
    binding=continuation_binding(prepared)
    for index,(row,state) in enumerate(zip(writes,states)):
        raw=reader.canonical(row['value']);expected=dict(path=row['path'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        need(state.get('index')==index and state.get('path')==row['path'] and state.get('state')=='APPLIED' and
             state.get('containerReadbackPin')==expected,'CONTINUATION_WRITE_NOT_READ_BACK')
        native=state.get('nativeResult',{})
        expected_path=prepared['routes'][index]['hostPath'] or row['path']
        need(native.get('installedPin')==dict(expected,path=str(Path(expected_path)) if prepared['routes'][index]['hostPath'] else expected_path) and
             native.get('fileFsyncCompleted') is True and native.get('atomicMoveCompleted') is True and
             native.get('powerLossDurabilityVerified') is False,'CONTINUATION_NATIVE_TRANSITION_INVALID')
        for offset,label in enumerate(('DISPATCHED_OUTCOME_UNKNOWN','APPLIED')):
            rec=records[index*2+offset]
            need(set(rec)=={'index','state','pin'} and rec['index']==index and rec['state']==label,
                 'CONTINUATION_WRITE_RECEIPT_ORDER')
            value=private_json(private,rec['pin'],pins)
            need(set(value)=={*binding,'write'} and all(value[k]==v for k,v in binding.items()) and
                 value['write'].get('state')==label and value['write'].get('index')==index,
                 'CONTINUATION_WRITE_RECEIPT_BINDING')
            if offset:need(value['write']==state,'CONTINUATION_WRITE_RECEIPT_CHANGED')


def validate_container_custody(prepared,custody,output):
    writes=prepared['originalSpec']['spugSpec']['writes'];audit=prepared['originalSpec']['spugSpec']['auditPath']
    need(type(output) is dict and output.get('status')=='PASS' and type(output.get('rows')) is list and
         len(output['rows'])==len(writes)==len(custody),'CONTINUATION_CONTAINER_CUSTODY_INCOMPLETE')
    for index,(planned,local,remote) in enumerate(zip(writes,custody,output['rows'])):
        need(remote['index']==index and remote['path']==planned['path'] and remote['expected']==planned['expected'] and
             local['containerArchivePin']==remote['archivePin'],'CONTINUATION_CONTAINER_CUSTODY_CHANGED')
        if planned['expected'] is None:
            need(remote['rawBase64'] is None and remote['archivePin'] is None and local['custody'] is None,
                 'CONTINUATION_CONTAINER_CUSTODY_ABSENCE')
        else:
            expected=dict(planned['expected'],path=audit+'/before-'+str(index)+'.private.json')
            need(remote['archivePin']==expected and
                 base64.b64decode(remote['rawBase64'],validate=True)==reader.verify_bytes(local['custody']),
                 'CONTINUATION_CONTAINER_CUSTODY_BYTES')


def validate_native_targets(prepared,native):
    nonce='spug-continuation-'+prepared['inputs']['originalFailurePin']['sha256'][:24]
    for value,request,output in native:
        label=value['label'];argv=request.get('argv')
        need(type(argv) is list,'CONTINUATION_NATIVE_ARGV_INVALID')
        if label=='inspect':
            need(argv==[reader.DOCKER,'inspect',reader.CONTAINER,prepared['mountObservation']['protectedContainerId']] and
                 value['stdinPin'] is None,'CONTINUATION_NATIVE_INSPECT_TARGET')
            verify_instances(output,prepared['mountObservation'])
        elif label.startswith('host-verify-'):
            host=label.rsplit('-',1)[1]
            need(host in contract.HOSTS and argv==prepared['hostCommands'][host],
                 'CONTINUATION_NATIVE_HOST_TARGET')
        else:
            need(argv==[reader.DOCKER,'exec','-i',reader.CONTAINER,'python3','-B','-',nonce],
                 'CONTINUATION_NATIVE_CONTAINER_TARGET')


def validate_publish_native(prepared,private,result,native,pins):
    commands=[(value,request,output) for value,request,output in native if value['label']!='inspect']
    expected_labels=[label for i in range(7) for label in
        [('write-' if i in (4,5) else 'guard-')+str(i),'readback-'+str(i)]]
    need([r[0]['label'] for r in commands]==expected_labels,'CONTINUATION_NATIVE_FILE_SET_INCOMPLETE')
    for index,state in enumerate(result['writeResults']):
        for offset,phase in enumerate(('write' if index in (4,5) else 'guard','readback')):
            value,request,output=commands[index*2+offset]
            need(private_raw(private,value['stdinPin'],pins)==container_program(prepared,phase,index).encode('utf-8') and
                 output.get('status')=='PASS' and output.get('phase')==phase and
                 output.get('sourceCommit')==prepared['inputs']['sourceCommit'] and
                 output.get('backupDispatched') is False and output.get('restoreDispatched') is False,
                 'CONTINUATION_NATIVE_FILE_PROGRAM_CHANGED')
            if phase=='readback':need(output.get('installedPin')==state['containerReadbackPin'],'CONTINUATION_NATIVE_READBACK_CHANGED')
            elif phase=='write':need(output.get('transition')==state['nativeResult'],'CONTINUATION_NATIVE_VOLUME_WRITE_CHANGED')
            else:need(output.get('index')==index and output.get('entryIdentity')==prepared['mountObservation']['entryIdentity'],
                      'CONTINUATION_NATIVE_GUARD_CHANGED')


if __name__=='__main__':
    args=parser().parse_args()
    try:result=run_request(args.task,args.private,args.inputs,apply=args.apply)
    except BaseException as error:
        print(json.dumps(dict(status='FAILED',errorType=type(error).__name__,
            errorCode='MAIN_SPUG_CONTINUATION_FAILED_CHECK_PRIVATE_EVIDENCE')));raise SystemExit(1)
    print(json.dumps(result,ensure_ascii=False))
