"""Activate one committed Spug adapter. Default prepare never calls Docker.

Explicit observe reads the exact existing instance. Apply has one exclusive
attempt, preserves original bytes, and signals only its proved entry process.
An interrupted or failed attempt is retained and is never resumed or rolled back.
"""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

import main_program_spug_publication as publication
import main_program_spug_resource_observation as observation_lifecycle

TASK=Path(__file__).resolve().parent
PRIVATE=publication.PRIVATE
ADAPTER='smallapp_adapter.py'
DEPLOYMENT_FILES=(ADAPTER,'smallapp-ui/app.js','smallapp-ui/simple.js')
REMOTE='/opt/intruoyi-spug/'
canonical=publication.canonical
file_pin=publication.file_pin
exclusive_bytes=publication.exclusive_bytes


def need(value,code):
    if not value: raise ValueError('MAIN_RESOURCE_'+code)


def validate_observation(value,resource,*,deployment_delta=None):
    fields={'schemaVersion','sourceCommit','spug','entryIdentity','supervisorPin','nginxPin','modulePins',
            'credentialPins','routeFingerprints','catalogueSourceRef','catalogueSha256','historySha256','ledgerPins'}
    need(set(value)==fields and value['schemaVersion']=='MainProgramSpugResourceActivationObservation/v1' and
         value['sourceCommit']==resource['sourceCommit'],'OBSERVATION_INVALID')
    spug=value['spug']
    need(set(spug)=={'containerId','containerSnapshot','protectedContainerId','protectedContainerSnapshot',
        'entryPid','settings','connections','productPins','taskSnapshotSha256'} and
        spug['containerId']==publication.CONTAINER and publication.contract.sha(spug['protectedContainerId']) and
        spug['protectedContainerId']!=publication.CONTAINER and
        set(spug['settings'])==set(publication.SETTINGS),'INSTANCE_OBSERVATION_INVALID')
    for key,path in publication.SETTINGS.items():
        publication.contract.remote_pin(spug['settings'][key]);need(spug['settings'][key]['path']==path,'SETTINGS_PATH_CHANGED')
    identity=value['entryIdentity']
    need(set(identity)=={'pid','startTicks','argv','parentPid','cwd','executable','supervisorStartTicks'} and
        type(identity['pid']) is int and identity['pid']>1 and spug['entryPid']==identity['pid'] and
        identity['parentPid']==1 and identity['argv']==['python3','-B',REMOTE+'smallapp_entry.py'] and
        identity['cwd']=='/data/spug/spug_api' and re.fullmatch('[0-9]+',identity['startTicks']) and
        re.fullmatch('[0-9]+',identity['supervisorStartTicks']) and identity['executable'].startswith('/'), 'ENTRY_IDENTITY_INVALID')
    files=publication.resource_files(resource)
    need(len(spug['productPins'])==11,'ELEVEN_RESOURCES_REQUIRED')
    for name,reference in zip(publication.PRODUCT_FILES,spug['productPins']):
        publication.contract.remote_pin(reference);need(reference['path']==REMOTE+name,'RESOURCE_PATH_CHANGED')
        if deployment_delta is not None and name in DEPLOYMENT_FILES:
            row=next(row for row in deployment_delta['changes'] if row['relativePath']==name)
            need(reference==row['beforePin'],'DEPLOYMENT_BEFORE_OBSERVATION_CHANGED')
        elif name!=ADAPTER:
            need(all(reference[k]==files['ops/spug/'+name][k] for k in ('bytes','sha256')),'NON_ADAPTER_RESOURCE_CHANGED')
    for name,reference in spug['connections'].items():
        need(re.fullmatch('[A-Za-z0-9_.-]+[.]json',name) and reference['path']=='/run/intruoyi-spug/'+name,'CONNECTION_PATH_INVALID')
        publication.contract.remote_pin(reference)
    for key,path in (('supervisorPin','/etc/supervisord.conf'),('nginxPin','/etc/nginx/nginx.conf')):
        publication.contract.remote_pin(value[key]);need(value[key]['path']==path,'CONTROL_PATH_INVALID')
    for key in ('modulePins','credentialPins','ledgerPins'):
        need(type(value[key]) is list and len({p['path'] for p in value[key]})==len(value[key]),'PIN_SET_INVALID')
        for reference in value[key]:publication.contract.remote_pin(reference)
    modules={p['path']:p for p in value['modulePins']}
    need(set(modules)=={REMOTE+n for n in ('smallapp_entry.py',ADAPTER,'smallapp_simple.py')},'MODULE_ORIGINS_REQUIRED')
    for reference in spug['productPins']:
        if reference['path'] in modules:need(modules[reference['path']]==reference,'MODULE_PIN_CHANGED')
    need(all(p['path'].startswith('/run/intruoyi-spug/') and p['path'].endswith('.json') for p in value['credentialPins']) and
        all(p['path'].startswith('/var/lib/intruoyi-spug/smallapp/') and p['path'].endswith('.json') for p in value['ledgerPins']),
        'PRESERVATION_PATH_INVALID')
    need(type(value['catalogueSourceRef']) is str and value['catalogueSourceRef'] and
        all(publication.contract.sha(value[k]) for k in ('catalogueSha256','historySha256')) and
        publication.contract.sha(spug['taskSnapshotSha256']) and type(value['routeFingerprints']) is dict and
        'root' in value['routeFingerprints'] and all(publication.contract.sha(v) for v in value['routeFingerprints'].values()),
        'BUSINESS_OBSERVATION_INVALID')
    return value


def prepare(task,private,inputs_file,*,allow_unobserved=False):
    records=publication.contract.Records(task);inputs=records.read(inputs_file)
    is_v2=inputs.get('schemaVersion')=='MainProgramSpugResourceActivationInputs/v2'
    fields={'schemaVersion','resourceBuildPin','observationPin'}|({'deploymentDeltaPin'} if is_v2 else set())
    need(set(inputs)==fields and inputs['schemaVersion'] in
        ('MainProgramSpugResourceActivationInputs/v1','MainProgramSpugResourceActivationInputs/v2'),'INPUTS_INVALID')
    resource,pins=publication.validate_resource_build(records,inputs['resourceBuildPin'],private)
    delta=validate_deployment_delta(records.pinned(inputs['deploymentDeltaPin']),resource,inputs['resourceBuildPin']) if is_v2 else None
    observation=None
    if inputs['observationPin'] is not None:
        observation=publication.private_document(private,inputs['observationPin'])
        validate_observation(observation,resource,deployment_delta=delta);pins.append(inputs['observationPin'])
    else:need(allow_unobserved,'OBSERVATION_REQUIRED')
    adapter=Path(resource['worktree'])/'ops/spug'/ADAPTER
    compile(adapter.read_bytes(),str(adapter),'exec')
    pins+=records.path_pins()+[file_pin(Path(__file__).resolve()),file_pin(Path(publication.__file__).resolve()),
        file_pin(Path(publication.contract.__file__).resolve()),file_pin(Path(observation_lifecycle.__file__).resolve())]
    result=dict(inputs=inputs,resource=resource,observation=observation,runtime=publication.RUNTIME,
        inputPins=list({p['path']:p for p in pins}.values()))
    if is_v2:result['deploymentDelta']=delta
    return result


def validate_deployment_delta(value,resource,build_pin):
    need(type(value) is dict and set(value)=={'schemaVersion','sourceCommit','resourceBuildPin','changes'} and
         value['schemaVersion']=='MainProgramSpugResourceDeploymentDelta/v1' and
         value['sourceCommit']==resource['sourceCommit'] and value['resourceBuildPin']==build_pin,
         'DEPLOYMENT_DELTA_INVALID')
    rows=value['changes']
    need(type(rows) is list and len(rows)==3 and all(type(row) is dict and
         set(row)=={'relativePath','beforePin','afterPin'} for row in rows) and
         [row['relativePath'] for row in rows]==list(DEPLOYMENT_FILES),'DEPLOYMENT_FILE_SET_INVALID')
    for row in rows:
        name=row['relativePath'];before=publication.contract.remote_pin(row['beforePin'])
        after=publication.contract.remote_pin(row['afterPin'])
        need(before['path']==after['path']==REMOTE+name and
             after==dict(path=REMOTE+name,**resource['files']['ops/spug/'+name]) and
             (before['bytes'],before['sha256'])!=(after['bytes'],after['sha256']),
             'DEPLOYMENT_FILE_PIN_INVALID')
    return value


def unchanged_inputs(spec):
    for reference in spec['inputPins']:
        need(file_pin(reference['path'])==reference,'INPUT_CHANGED')


def expected_after(spec,new_identity):
    # Only the proved entry identity and installed adapter bytes may change.
    value=json.loads(canonical(spec['observation']))
    old=value['entryIdentity']
    need(set(new_identity)==set(old) and type(new_identity['pid']) is int and new_identity['pid']>1 and
        new_identity['pid']!=old['pid'] and new_identity['startTicks']!=old['startTicks'] and
        all(new_identity[k]==old[k] for k in old if k not in ('pid','startTicks')),'NEW_ENTRY_IDENTITY_INVALID')
    value['entryIdentity']=new_identity;value['spug']['entryPid']=new_identity['pid']
    changed=DEPLOYMENT_FILES if 'deploymentDelta' in spec else (ADAPTER,)
    for references in (value['spug']['productPins'],value['modulePins']):
        for reference in references:
            for name in changed:
                if reference['path']==REMOTE+name:reference.update(spec['resource']['files']['ops/spug/'+name])
    return value


def check_runtime(spec,*,installed=False):
    root=Path(spec['runtime']);need(root.is_absolute() and root.resolve(strict=True)==root,'RUNTIME_ALIAS')
    for name,old in zip(publication.PRODUCT_FILES,spec['observation']['spug']['productPins']):
        wanted=spec['resource']['files']['ops/spug/'+name] if installed else old
        actual=file_pin(root/name)
        need(all(actual[k]==wanted[k] for k in ('bytes','sha256')),'RUNTIME_RESOURCE_CHANGED')


def dispatch_prepared(task,private,spec,*,apply=False,transport=None):
    if spec['inputs'].get('schemaVersion')=='MainProgramSpugResourceActivationInputs/v2':
        return dispatch_delta(task,private,spec,apply=apply,transport=transport)
    if not apply:return dict(status='PREPARED',sourceCommit=spec['resource']['sourceCommit'],runtimeWrites=False,transportCalled=False)
    task,private=Path(task).resolve(strict=True),Path(private).resolve(strict=True)
    commit=spec['resource']['sourceCommit'];stem='main-program-spug-resource-activation-'+commit[:7]
    attempt=private/(stem+'.attempt.json');rich=private/(stem+'.private.json');output=task/(stem+'.json');audit=private/(stem+'-originals')
    need(not any(p.exists() or p.is_symlink() for p in (attempt,rich,output,audit)),'ATTEMPT_EXISTS')
    unchanged_inputs(spec);check_runtime(spec)
    transport=transport or ActualTransport(private,spec)
    observed=transport.observe()
    need(observed==spec['observation'],'FRESH_OBSERVATION_CHANGED')
    active=Path(spec['runtime'])/ADAPTER;staged=active.with_name(active.name+'.main-program-'+commit[:7]+'.pending')
    need(not staged.exists() and not staged.is_symlink(),'STAGED_FILE_EXISTS')
    unchanged_inputs(spec);check_runtime(spec)
    exclusive_bytes(attempt,canonical(dict(schemaVersion='MainProgramSpugResourceAttempt/v1',sourceCommit=commit,
        inputs=spec['inputs'],beforeObservation=observed)))
    evidence=dict(schemaVersion='MainProgramSpugResourceActivation/v1',status='FAILED',sourceCommit=commit,
        stage='replace-adapter',adapterReplaced=False,entryReloadRequested=False,entryReloaded=False,
        backupDispatched=False,restoreDispatched=False)
    try:
        audit.mkdir(mode=0o700)
        raw=publication.verify_bytes(file_pin(Path(spec['resource']['worktree'])/'ops/spug'/ADAPTER))
        wanted=spec['resource']['files']['ops/spug/'+ADAPTER]
        need(len(raw)==wanted['bytes'] and hashlib.sha256(raw).hexdigest()==wanted['sha256'],'RESOURCE_INPUT_CHANGED')
        old=file_pin(active)
        need(all(old[k]==next(p for p in observed['spug']['productPins'] if p['path']==REMOTE+ADAPTER)[k]
                 for k in ('bytes','sha256')),'ADAPTER_CHANGED')
        receipt=publication.replace_once(active,audit/'adapter-before.py',staged,old,raw)
        evidence.update(adapterReplaced=True,replacement=receipt)
        exclusive_bytes(audit/'replacement.json',canonical(receipt));check_runtime(spec,installed=True)
        evidence.update(stage='reload-entry',entryReloadRequested=True)
        exclusive_bytes(audit/'reload-intent.json',canonical(dict(entryIdentity=observed['entryIdentity'],
            installedAdapterPin=receipt['installedPin'])))
        new_identity=transport.reload(observed['entryIdentity']);evidence.update(entryReloaded=True,newEntryIdentity=new_identity)
        evidence['stage']='verify-original-behavior'
        after=transport.observe();need(after==expected_after(spec,new_identity),'POST_ACTIVATION_OBSERVATION_CHANGED')
        unchanged_inputs(spec);check_runtime(spec,installed=True)
        publication.verify_bytes(receipt['previousPin'])
        need(all(receipt['previousPin'][k]==old[k] for k in ('bytes','sha256')),'ORIGINAL_BACKUP_CHANGED')
        evidence.update(status='PASS',stage='complete',afterObservation=after)
        exclusive_bytes(rich,canonical(evidence))
        core=dict(schemaVersion='MainProgramSpugResourceActivation/v1',status='PASS',sourceCommit=commit,
            resourceBuildPin=spec['inputs']['resourceBuildPin'],observationPin=spec['inputs']['observationPin'],
            previousEntryPid=observed['entryIdentity']['pid'],entryPid=new_identity['pid'],adapterPin=receipt['installedPin'],
            oldAdapterPreserved=True,otherResourcesUnchanged=True,settingsAndConnectionsUnchanged=True,
            originalBehaviorVerified=True,protectedSpugUnchanged=True,sharedServiceRestarted=False,
            backupDispatched=False,restoreDispatched=False,privateEvidencePin=file_pin(rich))
        exclusive_bytes(output,canonical(core))
        return dict(status='PASS',sourceCommit=commit,report=output.name)
    except BaseException as error:
        # A replace can succeed before its readback or receipt fails. Report
        # actual installed bytes, never infer "no write" from a raised call.
        try:
            current=file_pin(active);wanted=spec['resource']['files']['ops/spug/'+ADAPTER]
            prior=next(p for p in observed['spug']['productPins'] if p['path']==REMOTE+ADAPTER)
            evidence['adapterReplaced']=(True if all(current[k]==wanted[k] for k in ('bytes','sha256')) else
                False if all(current[k]==prior[k] for k in ('bytes','sha256')) else None)
            evidence['currentAdapterPin']=current
        except (OSError,ValueError):evidence['adapterReplaced']=None
        evidence.update(status='FAILED',errorType=type(error).__name__,errorCode=str(error))
        if not rich.exists():exclusive_bytes(rich,canonical(evidence))
        raise ValueError('MAIN_RESOURCE_ACTIVATION_FAILED_CHECK_PRIVATE_REPORT') from None


def delta_suffix(spec):
    return '-delta-'+spec['inputs']['deploymentDeltaPin']['sha256'][:12]


def delta_file_states(spec):
    """Read actual disk state, including after replace succeeded but readback failed."""
    result=[]
    for row in spec['deploymentDelta']['changes']:
        state=dict(relativePath=row['relativePath'],state='UNKNOWN',currentPin=None)
        try:
            current=file_pin(Path(spec['runtime'])/row['relativePath']);state['currentPin']=current
            if all(current[k]==row['afterPin'][k] for k in ('bytes','sha256')):state['state']='REPLACED'
            elif all(current[k]==row['beforePin'][k] for k in ('bytes','sha256')):state['state']='UNCHANGED'
        except (OSError,ValueError) as error:
            state['observationErrorType']=type(error).__name__
        result.append(state)
    return result


def check_delta_runtime(spec,replaced):
    root=Path(spec['runtime']);need(root.is_absolute() and root.resolve(strict=True)==root,'RUNTIME_ALIAS')
    for name,old in zip(publication.PRODUCT_FILES,spec['observation']['spug']['productPins']):
        wanted=spec['resource']['files']['ops/spug/'+name] if name in replaced else old
        actual=file_pin(root/name)
        need(all(actual[k]==wanted[k] for k in ('bytes','sha256')),'RUNTIME_RESOURCE_CHANGED')


def replace_archived(active,archived,staged,before,raw):
    """The full original set is already durable; replace one exact local path."""
    active,staged=Path(active),Path(staged)
    need(not staged.exists() and not staged.is_symlink() and staged.parent.resolve(strict=True)==staged.parent,
         'STAGED_FILE_EXISTS')
    need(file_pin(active)==before,'DEPLOYMENT_BEFORE_RUNTIME_CHANGED')
    publication.verify_bytes(archived)
    need(all(archived[k]==before[k] for k in ('bytes','sha256')),'ORIGINAL_BACKUP_CHANGED')
    exclusive_bytes(staged,raw)
    need(file_pin(active)==before,'DEPLOYMENT_BEFORE_RUNTIME_CHANGED')
    os.replace(staged,active);publication.sync_parent(active)
    installed=file_pin(active)
    need(installed['bytes']==len(raw) and installed['sha256']==hashlib.sha256(raw).hexdigest(),
         'INSTALLED_READBACK_FAILED')
    return dict(previousPin=archived,installedPin=installed)


def observe_with_evidence(private,spec,transport,*,exact=False):
    value=None
    try:
        value=transport.observe()
        validate_observation(value,spec['resource'],deployment_delta=spec.get('deploymentDelta'))
        if exact:need(value==spec['observation'],'FRESH_OBSERVATION_CHANGED')
        unchanged_inputs(spec)
        return value
    except BaseException as error:
        suffix=delta_suffix(spec) if 'deploymentDelta' in spec else ''
        path=Path(private).resolve(strict=True)/('main-program-spug-resource-observation-'+
            spec['resource']['sourceCommit'][:7]+suffix+'.failure-'+uuid.uuid4().hex+'.private.json')
        exclusive_bytes(path,canonical(dict(schemaVersion='MainProgramSpugResourceObservationFailure/v1',
            status='FAILED',sourceCommit=spec['resource']['sourceCommit'],inputs=spec['inputs'],
            rawObservation=value,errorType=type(error).__name__,errorCode=str(error),
            validObservation=False,installationAttempted=False)))
        raise


def dispatch_delta(task,private,spec,*,apply=False,transport=None):
    if not apply:return dict(status='PREPARED',sourceCommit=spec['resource']['sourceCommit'],runtimeWrites=False,transportCalled=False)
    task,private=Path(task).resolve(strict=True),Path(private).resolve(strict=True)
    validate_deployment_delta(spec['deploymentDelta'],spec['resource'],spec['inputs']['resourceBuildPin'])
    validate_observation(spec['observation'],spec['resource'],deployment_delta=spec['deploymentDelta'])
    commit=spec['resource']['sourceCommit'];stem='main-program-spug-resource-activation-'+commit[:7]+delta_suffix(spec)
    attempt=private/(stem+'.attempt.json');rich=private/(stem+'.private.json');output=task/(stem+'.json');audit=private/(stem+'-originals')
    need(not any(p.exists() or p.is_symlink() for p in (attempt,rich,output,audit)),'ATTEMPT_EXISTS')
    rows=spec['deploymentDelta']['changes'];staged={}
    for row in rows:
        active=Path(spec['runtime'])/row['relativePath']
        path=active.with_name(active.name+'.main-program-'+commit[:7]+delta_suffix(spec)+'.pending')
        need(not path.exists() and not path.is_symlink(),'STAGED_FILE_EXISTS');staged[row['relativePath']]=path
    unchanged_inputs(spec);check_delta_runtime(spec,set())
    transport=transport or ActualTransport(private,spec)
    observed=observe_with_evidence(private,spec,transport,exact=True)
    unchanged_inputs(spec);check_delta_runtime(spec,set())
    exclusive_bytes(attempt,canonical(dict(schemaVersion='MainProgramSpugResourceAttempt/v2',sourceCommit=commit,
        inputs=spec['inputs'],inputPins=spec['inputPins'],beforeObservation=observed,deploymentDelta=spec['deploymentDelta'])))
    evidence=dict(schemaVersion='MainProgramSpugResourceActivation/v2',status='FAILED',sourceCommit=commit,
        resourceBuildPin=spec['inputs']['resourceBuildPin'],deploymentDeltaPin=spec['inputs']['deploymentDeltaPin'],
        observationPin=spec['inputs']['observationPin'],stage='preserve-originals',originals=[],replacements=[],
        fileStates=delta_file_states(spec),entryReloadRequested=False,entryReloaded=False,
        backupDispatched=False,restoreDispatched=False)
    try:
        audit.mkdir(mode=0o700);old_pins={};new_bytes={}
        for index,row in enumerate(rows):
            name=row['relativePath'];active=Path(spec['runtime'])/name;old=file_pin(active)
            need(all(old[k]==row['beforePin'][k] for k in ('bytes','sha256')),'DEPLOYMENT_BEFORE_RUNTIME_CHANGED')
            raw=publication.verify_bytes(old)
            backup=audit/(str(index)+'-before'+Path(name).suffix)
            archived=exclusive_bytes(backup,raw);publication.verify_bytes(archived)
            need(all(archived[k]==old[k] for k in ('bytes','sha256')),'ORIGINAL_BACKUP_CHANGED')
            evidence['originals'].append(dict(relativePath=name,beforePin=old,archivedPin=archived));old_pins[name]=old
            candidate=file_pin(Path(spec['resource']['worktree'])/'ops/spug'/name)
            need(all(candidate[k]==row['afterPin'][k] for k in ('bytes','sha256')),'RESOURCE_INPUT_CHANGED')
            new_bytes[name]=publication.verify_bytes(candidate)
        # All three archives must exist, match and be durable before the first
        # running resource can change. A per-file archive is never deferred.
        for original in evidence['originals']:publication.verify_bytes(original['archivedPin'])
        need(len(evidence['originals'])==3,'ALL_ORIGINALS_REQUIRED')
        exclusive_bytes(audit/'originals.json',canonical(evidence['originals']))
        replaced=set()
        for index,row in enumerate(rows):
            name=row['relativePath'];evidence['stage']='replace-'+name
            unchanged_inputs(spec);check_delta_runtime(spec,replaced)
            for original in evidence['originals']:publication.verify_bytes(original['archivedPin'])
            receipt=replace_archived(Path(spec['runtime'])/name,evidence['originals'][index]['archivedPin'],
                staged[name],old_pins[name],new_bytes[name])
            receipt=dict(relativePath=name,**receipt);evidence['replacements'].append(receipt)
            replaced.add(name);evidence['fileStates']=delta_file_states(spec)
            exclusive_bytes(audit/('replacement-'+str(index)+'.json'),canonical(receipt))
        check_delta_runtime(spec,replaced);unchanged_inputs(spec)
        evidence.update(stage='reload-entry',entryReloadRequested=True)
        exclusive_bytes(audit/'reload-intent.json',canonical(dict(entryIdentity=observed['entryIdentity'],
            installedResourcePins=[row['installedPin'] for row in evidence['replacements']])))
        new_identity=transport.reload(observed['entryIdentity']);evidence.update(entryReloaded=True,newEntryIdentity=new_identity)
        evidence['stage']='verify-original-behavior'
        after=transport.observe();evidence['afterObservation']=after
        need(after==expected_after(spec,new_identity),'POST_ACTIVATION_OBSERVATION_CHANGED')
        unchanged_inputs(spec);check_runtime(spec,installed=True)
        for original in evidence['originals']:publication.verify_bytes(original['archivedPin'])
        evidence.update(status='PASS',stage='complete',fileStates=delta_file_states(spec))
        exclusive_bytes(rich,canonical(evidence))
        core=dict(schemaVersion='MainProgramSpugResourceActivation/v2',status='PASS',sourceCommit=commit,
            resourceBuildPin=spec['inputs']['resourceBuildPin'],deploymentDeltaPin=spec['inputs']['deploymentDeltaPin'],
            observationPin=spec['inputs']['observationPin'],previousEntryPid=observed['entryIdentity']['pid'],entryPid=new_identity['pid'],
            replacements=evidence['replacements'],oldResourcesPreserved=True,otherEightResourcesUnchanged=True,
            settingsAndConnectionsUnchanged=True,originalBehaviorVerified=True,protectedSpugUnchanged=True,
            sharedServiceRestarted=False,backupDispatched=False,restoreDispatched=False,privateEvidencePin=file_pin(rich))
        exclusive_bytes(output,canonical(core))
        return dict(status='PASS',sourceCommit=commit,report=output.name)
    except BaseException as error:
        evidence.update(status='FAILED',fileStates=delta_file_states(spec),errorType=type(error).__name__,errorCode=str(error))
        if not rich.exists():exclusive_bytes(rich,canonical(evidence))
        else:exclusive_bytes(private/(stem+'.finalization-failure.private.json'),canonical(evidence))
        raise ValueError('MAIN_RESOURCE_ACTIVATION_FAILED_CHECK_PRIVATE_REPORT') from None


def run_request(task,private,inputs_file,*,apply=False,observe=False,transport=None):
    need(not (apply and observe),'MODE_CONFLICT')
    spec=prepare(task,private,inputs_file,allow_unobserved=observe)
    if observe:
        need(spec['observation'] is None,'OBSERVATION_ALREADY_SUPPLIED')
        suffix=delta_suffix(spec) if 'deploymentDelta' in spec else ''
        path=Path(private).resolve(strict=True)/('main-program-spug-resource-observation-'+spec['resource']['sourceCommit'][:7]+suffix+'.private.json')
        need(not path.exists() and not path.is_symlink(),'OBSERVATION_EXISTS')
        transport=transport or ActualTransport(private,spec)
        value=observe_with_evidence(private,spec,transport)
        reference=exclusive_bytes(path,canonical(value))
        return dict(status='OBSERVED',observationPin=reference,runtimeWrites=False)
    return dispatch_prepared(task,private,spec,apply=apply,transport=transport)


def parser():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',required=True)
    modes=p.add_mutually_exclusive_group();modes.add_argument('--apply',action='store_true');modes.add_argument('--observe',action='store_true')
    p.add_argument('--task',type=Path,default=TASK);p.add_argument('--private',type=Path,default=PRIVATE)
    return p


def process_identity():
    rows=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():continue
        try:
            args=(proc/'cmdline').read_bytes().rstrip(b'\0').decode('utf-8').split('\0')
            if args!=['python3','-B','/opt/intruoyi-spug/smallapp_entry.py']:continue
            fields=(proc/'stat').read_text(encoding='utf-8').rsplit(') ',1)[1].split()
            parent=Path('/proc/1');parent_fields=(parent/'stat').read_text(encoding='utf-8').rsplit(') ',1)[1].split()
            need(b'supervisord' in (parent/'cmdline').read_bytes(),'SUPERVISOR_IDENTITY_CHANGED')
            rows.append(dict(pid=int(proc.name),argv=args,parentPid=int(fields[1]),startTicks=fields[19],
                cwd=str((proc/'cwd').resolve(strict=True)),executable=str((proc/'exe').resolve(strict=True)),
                supervisorStartTicks=parent_fields[19]))
        except (FileNotFoundError,ProcessLookupError):continue
    need(rows,'ENTRY_PROCESS_MISSING');need(len(rows)==1,'ENTRY_PROCESS_AMBIGUOUS')
    need(rows[0]['parentPid']==1 and rows[0]['cwd']=='/data/spug/spug_api','ENTRY_OWNERSHIP_CHANGED')
    return rows[0]


HELPERS='import os,json,hashlib,re\nfrom pathlib import Path\n'+''.join(inspect.getsource(f)+'\n' for f in
    (need,publication.canonical,publication.file_pin,process_identity))

OBSERVE_PROGRAM=HELPERS+r'''
import sys,configparser,time
sys.path.insert(0,'/opt/intruoyi-spug')
import smallapp_entry as entry,smallapp_simple as simple,smallapp_adapter as adapter
identity=process_identity()
manager=configparser.RawConfigParser();manager.read('/etc/supervisord.conf',encoding='utf-8')
section='program:intruoyi-spug-backup-entry'
need(manager.get(section,'command')=='python3 -B /opt/intruoyi-spug/smallapp_entry.py' and
 manager.get(section,'directory')=='/data/spug/spug_api' and manager.get(section,'autorestart')=='unexpected' and
 manager.get(section,'exitcodes',fallback='0')=='0','SUPERVISOR_POLICY_CHANGED')
entry.initialize_spug()
config=entry.settings();simple.configuration()
for action in ('FULL','INCREMENTAL','RESTORE'):entry.installed_task(config,action)
if '_observation_progress' in globals():_observation_progress('configuration')
binding=adapter.read_json('/run/intruoyi-spug/smallapp-bridge.private.json')
need('selectionConnections' not in binding,'EXPECTED_ORIGINAL_ROUTING_REQUIRED')
source=ORIGINAL_SOURCE
need(source in binding.get('sourceConnections',{}),'ORIGINAL_CATALOGUE_SOURCE_NOT_REGISTERED')
root=adapter.HttpBridge();routes={'root':root.fingerprint};connections={}
for lane in ('sourceConnections','targetConnections'):
 for reference,name in sorted(binding.get(lane,{}).items()):
  bridge=adapter.HttpBridge(source_ref=reference) if lane=='sourceConnections' else adapter.HttpBridge(target_ref=reference)
  routes[lane+':'+reference]=bridge.fingerprint;connections[name]=file_pin('/run/intruoyi-spug/'+name)
if '_observation_progress' in globals():_observation_progress('routes')
matches=[a for a in config['applications'] if a['sourceConfigRef']==source]
need(len(matches)==1,'ORIGINAL_CATALOGUE_SOURCE_INVALID')
catalogue=entry.application_catalogue(config,matches[0]['applicationId'])
selected=[r for r in catalogue if r['applicationId']==matches[0]['applicationId']]
need(len(selected)==1 and selected[0]['validated'] is not None and selected[0]['readinessError'] is None,'ORIGINAL_CATALOGUE_QUERY_FAILED')
if '_observation_progress' in globals():_observation_progress('catalogue')
from apps.schedule.models import Task,History
tasks=list(Task.objects.order_by('pk').values())
# Stable database business rows; generated observation/HTTP timestamps are absent.
names={f.attname for f in History._meta.concrete_fields}
fields=sorted(names & {'id','task_id','status','command','executor','result','create_time','start_time','end_time','created_at','updated_at'})
need({'id','task_id','status'}<=set(fields),'HISTORY_FIELDS_UNPROVEN')
history=list(History.objects.order_by('pk').values(*fields))
if '_observation_progress' in globals():_observation_progress('history')
encode=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode('utf-8')
ledger=[]
ledger_bytes=0;ledger_report=time.monotonic()
need(adapter.RECORDS.is_dir() and not adapter.RECORDS.is_symlink(),'LEDGER_REQUIRED')
for path in sorted(adapter.RECORDS.rglob('*')):
 need(not path.is_symlink(),'LEDGER_ALIAS')
 if path.is_file() and path.suffix=='.json':
  ledger.append(file_pin(path));ledger_bytes+=ledger[-1]['bytes']
  if '_observation_progress' in globals() and (len(ledger)%32==0 or time.monotonic()-ledger_report>=2):
   _observation_progress('ledger',len(ledger),ledger_bytes);ledger_report=time.monotonic()
if '_observation_progress' in globals():_observation_progress('ledger',len(ledger),ledger_bytes)
aux=[]
for path in sorted(Path('/run/intruoyi-spug').glob('*.json')):
 if path.name!='smallapp-bridge.private.json' and path.name not in connections:aux.append(file_pin(path))
if '_observation_progress' in globals():_observation_progress('auxiliary')
modules=[]
for module,name in ((entry,'smallapp_entry.py'),(adapter,'smallapp_adapter.py'),(simple,'smallapp_simple.py')):
 need(str(Path(module.__file__).resolve())=='/opt/intruoyi-spug/'+name,'MODULE_ORIGIN_CHANGED');modules.append(file_pin(module.__file__))
if '_observation_progress' in globals():_observation_progress('modules')
out=dict(entryIdentity=identity,supervisorPin=file_pin('/etc/supervisord.conf'),nginxPin=file_pin('/etc/nginx/nginx.conf'),
 modulePins=modules,credentialPins=aux,routeFingerprints=routes,catalogueSourceRef=source,
 catalogueSha256=hashlib.sha256(encode(catalogue)).hexdigest(),historySha256=hashlib.sha256(encode(history)).hexdigest(),ledgerPins=ledger,
 entryPid=identity['pid'],settings={k:file_pin(p) for k,p in SETTINGS.items()},connections=connections,
 productPins=[file_pin('/opt/intruoyi-spug/'+name) for name in PRODUCT_FILES],taskSnapshotSha256=hashlib.sha256(encode(tasks)).hexdigest())
need(process_identity()==identity,'ENTRY_CHANGED_DURING_OBSERVATION')
if '_observation_progress' in globals():_observation_progress('complete')
print(json.dumps(out))
'''


def reload_program(expected,pins=()):
    return HELPERS+'EXPECTED='+repr(expected)+'\nPINS='+repr(list(pins))+r'''
import signal,time
for reference in PINS:need(file_pin(reference['path'])==reference,'ORIGINAL_PIN_CHANGED_BEFORE_SIGNAL')
need(process_identity()==EXPECTED,'ENTRY_CHANGED_BEFORE_SIGNAL')
os.kill(EXPECTED['pid'],signal.SIGTERM)
deadline=time.monotonic()+30
while time.monotonic()<deadline:
 try:current=process_identity()
 except ValueError as error:
  if str(error)!='MAIN_RESOURCE_ENTRY_PROCESS_MISSING':raise
  time.sleep(.25);continue
 if current['pid']!=EXPECTED['pid']:
  need(current['startTicks']!=EXPECTED['startTicks'] and all(current[k]==EXPECTED[k] for k in EXPECTED if k not in ('pid','startTicks')),'NEW_ENTRY_IDENTITY_CHANGED')
  print(json.dumps(current));break
 time.sleep(.25)
else:raise ValueError('MAIN_RESOURCE_ENTRY_RELOAD_UNKNOWN')
'''


class ActualTransport(publication.ActualTransport):
    """Reuse the existing Docker CLI wrapper; never invoke a host/server lane."""
    def instances(self,operation=None):
        command=self.command if operation is None else lambda *args:operation.short_command(self.command,*args)
        ids=command('ps','-aq','--no-trunc').decode().split();need(ids,'SPUG_INSTANCES_MISSING')
        rows=json.loads(command('inspect',*ids))
        selected=[r for r in rows if r['Id']==publication.CONTAINER]
        protected=[r for r in rows if any(p.get('HostPort')=='18081' for ports in
            (r['HostConfig'].get('PortBindings') or {}).values() for p in ports or [])]
        need(len(selected)==len(protected)==1 and selected[0]['Id']!=protected[0]['Id'],'INSTANCE_AMBIGUOUS')
        selected=selected[0];protected=protected[0]
        need(selected['Name']=='/intruoyi-spug-transfer-spug-1','INSTANCE_NAME_CHANGED')
        for row,port in ((selected,'18080'),(protected,'18081')):
            need(row['State']['Running'] is True and row['HostConfig']['PortBindings'].get('80/tcp')==
                [{'HostIp':'127.0.0.1','HostPort':port}],'INSTANCE_PORT_CHANGED')
        mounts=[m for m in selected['Mounts'] if m['Destination']=='/opt/intruoyi-spug']
        need(len(mounts)==1 and mounts[0]['Source'].replace('\\','/').lower()==publication.RUNTIME.lower(),'RUNTIME_BINDING_CHANGED')
        return dict(containerId=selected['Id'],containerSnapshot=publication.container_snapshot(selected),
            protectedContainerId=protected['Id'],protectedContainerSnapshot=publication.container_snapshot(protected))

    def observe(self):
        identity=dict(sourceCommit=self.spec['resource']['sourceCommit'],inputPins=self.spec['inputPins'])
        with observation_lifecycle.Observation(self.private,identity) as operation:
            instances=self.instances(operation)
            program='SETTINGS='+repr(publication.SETTINGS)+'\nPRODUCT_FILES='+repr(publication.PRODUCT_FILES)+'\nORIGINAL_SOURCE='+repr(publication.SOURCES[0])+'\n'+OBSERVE_PROGRAM
            result=json.loads(operation.run(program))
            need(self.instances(operation)==instances,'INSTANCE_CHANGED_DURING_OBSERVATION')
            spug=dict(instances,**{key:result.pop(key) for key in ('entryPid','settings','connections','productPins','taskSnapshotSha256')})
            return dict(schemaVersion='MainProgramSpugResourceActivationObservation/v1',sourceCommit=self.spec['resource']['sourceCommit'],spug=spug,**result)

    def reload(self,expected):
        before=self.instances()
        need(all(before[key]==self.spec['observation']['spug'][key] for key in before),'INSTANCE_CHANGED_BEFORE_RELOAD')
        observed=self.spec['observation'];spug=observed['spug']
        pins=[observed['supervisorPin'],observed['nginxPin'],*spug['settings'].values(),*spug['connections'].values(),
            *observed['credentialPins'],*[p for p in observed['modulePins'] if p['path']!=REMOTE+ADAPTER],
            *[dict(path=REMOTE+name,**self.spec['resource']['files']['ops/spug/'+name])
                for name in publication.PRODUCT_FILES]]
        value=json.loads(self.command('exec','-i',publication.CONTAINER,'python3','-B','-',input=reload_program(expected,pins).encode('utf-8')))
        need(self.instances()==before,'INSTANCE_CHANGED_DURING_RELOAD')
        return value


if __name__=='__main__':
    args=parser().parse_args()
    try:result=run_request(args.task,args.private,args.inputs,apply=args.apply,observe=args.observe)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        code=str(error) if type(error) is ValueError and re.fullmatch('[A-Z0-9_]+',str(error)) else 'MAIN_RESOURCE_INPUTS_OR_EXECUTION_INVALID'
        print(json.dumps(dict(status='REFUSED',errorCode=code,applyRequested=args.apply)));raise SystemExit(1)
    print(json.dumps(result))
