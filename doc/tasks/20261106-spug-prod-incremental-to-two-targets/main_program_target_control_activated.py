"""Pinned, local-only target activation overlay over the formal source chain.

Historical activation proves an installation, never current remote health. Old
receipt/custody data stays in the original source installation without rotation.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

import main_program_control_activation as activation
import main_program_control_runtime as runtime
import main_program_control_staging as legacy
import main_program_installation_selection as contract
import main_program_source_control_activated as source
import main_program_spug_publication as publication
import main_program_target_control_candidate as binding
import main_program_target_control_runtime as transition
import main_program_target_control_staging as staging


TASK=Path(__file__).resolve().parent
SCHEMA='TaskMainProgramTargetControlSelection/v1'
FIELDS={'schemaVersion','baseSourceSelectionPin','buildPin','standardPackagePin','targetActivationEvidencePins'}
HOSTS=('57','58','59')
WRAPPER_FIELDS={'status','host','mode','observedAt','elapsedSeconds','scriptPin','result'}
CONTINUATION_LOCAL={'continuationLocalFailurePin','continuationLocalPreparePin'}
CONTINUATION={'continuationFailurePin','continuationBeforePin','controlServiceRestartedInPriorAttempt'}
RESULT_FIELDS={'schemaVersion','status','host','role','stage','targetConfigRef','sourceCommit','observedAt',
    'transition','originalRuntimeSpec','candidate','currentController','addedDependencies','nativeBefore','nativeAfter',
    'apiSelection','originalApi','dropinPin','createdPaths','activationReceiptPin','activationCompleted','apiVerified',
    'controlServiceRestarted','oldReceiptPreserved','businessContainersUnchanged','fstabAndMountsUnchanged',
    'physicalLockVerified','actualImportsVerified','backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated'}
TRUE_FLAGS=('activationCompleted','apiVerified','controlServiceRestarted','oldReceiptPreserved',
    'businessContainersUnchanged','fstabAndMountsUnchanged','physicalLockVerified','actualImportsVerified')
FALSE_FLAGS=('backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated')
OBS_FIELDS={'controllers','containers','fstabPin','mountinfoSha256','historyGuard',
    'previousCustodyObservation','originalInventoryObservation','packagePins','documentsCreated'}
TRANSITION_FIELDS={'schemaVersion','status','host','targetConfigRef','service','successorController','before','after',
    'retainedEnvironmentBaseline','retainedRowEnvironment','retainedHistoryUsesOriginalSpec','serverWrites',
    'installationReceiptCreated','restoreDispatched'}


def need(value,reason):
    if not value:raise ValueError('ACTIVATED_TARGET_'+reason)


def _timestamp(value):
    need(type(value) is str,'TIMESTAMP')
    try:parsed=datetime.fromisoformat(value)
    except ValueError:raise ValueError('ACTIVATED_TARGET_TIMESTAMP') from None
    need(parsed.tzinfo is not None and parsed.utcoffset() is not None,'TIMESTAMP')


def _receipt(result):
    """Check only the two explicit original receipt publication phases."""
    reference=contract.remote_pin(result['activationReceiptPin'])
    value={k:deepcopy(v) for k,v in result.items() if k!='activationReceiptPin'}
    if source.byte_pin(reference['path'],publication.canonical(value))==reference:return
    paths=value.get('createdPaths')
    need(type(paths) is list and paths and paths[-1]==reference['path'] and paths.count(reference['path'])==1,
        'RECEIPT_PUBLICATION_PHASE')
    value['createdPaths']=paths[:-1]
    need(source.byte_pin(reference['path'],publication.canonical(value))==reference,'RECEIPT_BYTES')


def _wrapper(wrapper,host,*,mode='ACTIVATE',status='PASS'):
    need(type(wrapper) is dict,'WRAPPER')
    extra=CONTINUATION_LOCAL if CONTINUATION_LOCAL & set(wrapper) else set()
    need(type(wrapper) is dict and set(wrapper)==WRAPPER_FIELDS|extra and wrapper['status']==status and
        wrapper['mode']==mode and wrapper['host']==host and
        type(wrapper['elapsedSeconds']) in (int,float) and math.isfinite(wrapper['elapsedSeconds']) and
        wrapper['elapsedSeconds']>=0,'WRAPPER')
    _timestamp(wrapper['observedAt']);need(type(wrapper['result']) is dict,'RESULT')
    return wrapper['result']


def _continuation(wrapper,records):
    r=wrapper['result'];has=bool(CONTINUATION & set(r))
    need(bool(CONTINUATION_LOCAL & set(wrapper))==has,'CONTINUATION_REQUIRED')
    if not has:
        need(not records,'UNEXPECTED_CONTINUATION');return
    need(CONTINUATION<=set(r) and r['controlServiceRestartedInPriorAttempt'] is True and
        type(records) is dict and set(records)=={'failure','prepare'},'CONTINUATION_CONTEXT')
    host=r['host'].rsplit('.',1)[1]
    failure=_wrapper(records['failure'],host,status='FAIL')
    prepare=_wrapper(records['prepare'],host,mode='PREPARE')
    need(set(failure)=={'schemaVersion','status','host','targetConfigRef','sourceCommit','role','stage',
        *FALSE_FLAGS,'errorType','errorCode','observedAt','createdPaths','activationReceiptPin'} and
        failure['status']=='FAILED' and failure['stage']=='restart-selected-control' and
        type(failure['errorType']) is str and bool(failure['errorType']) and
        type(failure['errorCode']) is str and bool(failure['errorCode']),'CONTINUATION_FAILURE')
    _receipt(failure)
    need(set(prepare)=={'schemaVersion','status','host','targetConfigRef','sourceCommit','role','stage',
        *FALSE_FLAGS,'before','nativeGate','originalApi','proposedDropinPin','serverWrites',
        'controlServiceRestarted','observedAt','createdPaths'} and prepare['status']=='TARGET_ACTIVATION_PREPARED' and
        prepare['stage']=='prepared' and prepare['serverWrites'] is False and
        prepare['controlServiceRestarted'] is False and prepare['createdPaths']==[], 'CONTINUATION_PREPARE')
    for prior in (failure,prepare):
        need(all(prior[k]==r[k] for k in ('schemaVersion','host','targetConfigRef','sourceCommit','role')) and
            all(prior[k] is False for k in FALSE_FLAGS),'CONTINUATION_SCOPE')
        _timestamp(prior['observedAt'])
    reference=contract.remote_pin(r['continuationBeforePin'])
    need(r['continuationFailurePin']==failure['activationReceiptPin'] and
        reference['path']==str(PurePosixPath(failure['activationReceiptPin']['path']).parent/'before.private.json') and
        source.byte_pin(reference['path'],publication.canonical(prepare['before']))==reference and
        prepare['before']==r['transition']['before'] and prepare['originalApi']==r['originalApi'] and
        prepare['nativeGate']==r['nativeBefore'] and prepare['proposedDropinPin']==r['dropinPin'],
        'CONTINUATION_BINDING')


def _document(docs,reference):
    rows=[row for row in docs if row['pin']==reference]
    need(len(rows)==1,'CONFIGURATION_MISSING');return deepcopy(rows[0]['value'])


def _preservation(candidate,old_owner,spec):
    c=candidate['controller'];root=PurePosixPath(c['ownerPin']['path']).parent
    docs=[deepcopy(r) for r in candidate['newDocuments'] if PurePosixPath(r['pin']['path']).parent==root/'preservation']
    by_name={PurePosixPath(row['pin']['path']).name:row['pin'] for row in docs}
    need(set(by_name)==set(binding.DOCUMENT_SCHEMAS),'PRESERVATION_DOCUMENT_SET')
    target=old_owner['targets'][candidate['targetConfigRef']]
    # The original NAS credential is an explicitly retained remote input. Its
    # bytes were read by the native gate, rather than obtained from a new copy.
    originals=[p for p in spec['retainedDocuments'] if PurePosixPath(p['path']).name in
        ('mount.credentials','nas-smb-v1.private.json')]
    need(len(originals)==1,'PRESERVATION_ORIGINAL_CREDENTIAL')
    return dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',
        targetConfigRef=candidate['targetConfigRef'],captureRef=candidate['targetConfigRef']+'-pre-restore',
        capturePin=by_name['capture.json'],repositoryPin=by_name['repository.json'],policyPin=by_name['policy.json'],
        documents=docs,originalCredentialPins=[target['secrets']['minio'][k] for k in
        ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')]+originals)


def _original_spec(source_installation,host,r):
    base=source_installation['baseInstallation']['generation'];spec=r['originalRuntimeSpec']
    need(type(spec) is dict and set(spec)=={'current','unit','environmentBaseline','targetConfigRef','previousCustody',
        'oldReceiptPin','originalInventory','historyPins','sourceEvidencePins','newDocuments','retainedDocuments'},'ORIGINAL_SPEC')
    expected=deepcopy(base['selections'][host])
    expected['controllers']=[dict(deepcopy(row),environmentMode='CONFIG_EXACT') for row in
        source_installation['effectiveControllersByHost'][host]]
    need(spec['current']==expected and spec['targetConfigRef']==base['targets'][host] and spec['newDocuments']==[],
        'ORIGINAL_CONTROLLER_BINDING')
    custody=base['custodyByHost'].get(host)
    need(spec['previousCustody']==custody and spec['oldReceiptPin']==expected.get('activeReceiptPin') and
        spec['originalInventory']==(None if custody is None else custody['originalInventory']), 'ORIGINAL_CUSTODY_BINDING')
    need(spec['sourceEvidencePins']==(source_installation['activationReceiptPins'] if host=='57' else []),
        'ORIGINAL_SOURCE_RECEIPTS')
    for key in ('historyPins','retainedDocuments'):
        refs=spec[key]
        need(type(refs) is list and len({p['path'] for p in refs})==len(refs),'ORIGINAL_PIN_SET')
        for reference in refs:contract.remote_pin(reference)
    need(all(row['pin'] in spec['retainedDocuments'] for row in r['candidate']['newDocuments']),
        'STAGED_DOCUMENTS_NOT_RETAINED')
    return spec


def _unavailable(*args,**kwargs):
    raise RuntimeError('LOCAL_PROOF_VERIFIER_MUST_NOT_CALL_RUNTIME_BOUNDARY')


def _observations(r,gate,package,old_package,old_control,new_control):
    t=r['transition'];pid=r['currentController'].get('pid')
    need(type(t) is dict and set(t)==TRANSITION_FIELDS and
        t['schemaVersion']=='MainProgramTargetRuntimeTransition/v1' and t['status']=='TARGET_SUCCESSOR_RUNTIME_VERIFIED' and
        all(t[k]==r[k] for k in ('host','targetConfigRef')) and t['service']==gate.old['service'] and
        t['retainedHistoryUsesOriginalSpec'] is True and all(t[k] is False for k in
        ('serverWrites','installationReceiptCreated','restoreDispatched')),'TRANSITION')
    expected=gate._row(pid)
    need(r['currentController']==t['successorController']==expected and
        t['retainedEnvironmentBaseline']==gate.retained_environment and
        t['retainedRowEnvironment']==gate.retained_row_environment,'SUCCESSOR_ROW')
    before,after=t['before'],t['after']
    for observed in (before,after):
        need(type(observed) is dict and set(observed)==OBS_FIELDS and observed['documentsCreated'] is True and
            type(observed['containers']) is dict and bool(observed['containers']) and
            contract.sha(observed['mountinfoSha256']),'OBSERVATION')
        contract.remote_pin(observed['fstabPin'])
    old_pin=source.byte_pin(PurePosixPath(gate.old['engine'])/'package.json',old_package['files']['package.json'])
    new_pin=source.byte_pin(PurePosixPath(expected['engine'])/'package.json',package['files']['package.json'])
    need(before['packagePins'][gate.index]==old_pin,'OLD_PACKAGE_OBSERVATION')
    need(before['controllers'][gate.index]['properties']['DropInPaths'].split()==
        [p['path'] for p in gate.retained_dropins],'ORIGINAL_LOADED_DROPINS')
    # _compare is the existing pure transition comparison. Its package input is
    # independently derived here from the selected official tar, never the proof.
    gate._new_package_pin=new_pin
    gate._compare(before,after,pid)
    for row,observation,control in ((gate.old,before['controllers'][gate.index],old_control),
                                  (expected,after['controllers'][gate.index],new_control)):
        need(set(observation)=={'service','pid','argvSha256','executable','environmentVerification','properties'} and
            observation['service']==row['service'] and observation['pid']==row['pid'] and
            observation['executable']==control['pythonPin']['path'],'PROCESS_OBSERVATION')
        props=observation['properties']
        need(props['MainPID']==str(row['pid']) and props['FragmentPath']==gate.old_unit['unitPin']['path'] and
            props['ActiveState']=='active' and props['SubState']=='running' and props['LimitNOFILE']=='65536', 'PROCESS_PROPERTIES')
        env=observation['environmentVerification']
        need(type(env) is dict and set(env)=={'mode','environmentSha256'} and env['mode']=='CONFIG_EXACT' and
            contract.sha(env['environmentSha256']),'PROCESS_ENVIRONMENT')
        if 'argvSha256' in row:expected_sha=row['argvSha256']
        else:
            args=[control['pythonPin']['path'],'-B',row['engine']+'/control_entry.py','serve','--config-pin',
                publication.canonical(row['controlConfigurationPin']).decode('utf-8')]
            expected_sha=hashlib.sha256(('\0'.join(args)+'\0').encode()).hexdigest()
        need(observation['argvSha256']==expected_sha,'PROCESS_ARGV')


def _native_evidence(r,owner,*,allow_retained_retry=False):
    native=r['nativeBefore'];target=r['targetConfigRef']
    if allow_retained_retry and type(native) is dict and 'retainedRetryAdmission' in native:
        return _retry_native_evidence(r,owner)
    need(native==r['nativeAfter'] and type(native) is dict and set(native)=={'actualConfigurationReadPassed',
        'archiveViewsPreflightVerified','directlyAdmittedSources','epoch','epochPolicy'} and
        native['actualConfigurationReadPassed'] is True and native['archiveViewsPreflightVerified'] is True and
        native['directlyAdmittedSources']==list(activation.SOURCES),'NATIVE')
    policy=owner['targetProgramPolicies'][target]['backupEpochPolicy'];epoch=native['epoch']
    need(native['epochPolicy']==policy and type(epoch) is dict and set(epoch)=={'schemaVersion','state','operationId',
        'epochId','policySha256','eventPin'} and epoch['schemaVersion']=='SourceBackupEpoch/v1' and
        epoch['state']=='READY' and epoch['operationId'] is None and contract.sha(epoch['epochId']) and
        epoch['policySha256']==hashlib.sha256(publication.canonical(policy)).hexdigest(),'EPOCH')
    ref=contract.remote_pin(epoch['eventPin'])
    need(PurePosixPath(ref['path']).parent==PurePosixPath(policy['root']) and
        re.fullmatch(r'[0-9]{20}\.json',PurePosixPath(ref['path']).name),'EPOCH_EVENT')


def _retry_native_evidence(r,owner):
    """Validate an explicit product admission without rewriting its FAILED tail."""
    n=r['nativeBefore'];target=r['targetConfigRef'];policy=owner['targetProgramPolicies'][target]['backupEpochPolicy']
    need(n==r['nativeAfter'] and set(n)=={'actualConfigurationReadPassed','archiveViewsPreflightVerified',
        'directlyAdmittedSources','epoch','epochPolicy','retainedRetryAdmission','rejectedSources'} and
        n['actualConfigurationReadPassed'] is True and n['archiveViewsPreflightVerified'] is True and
        n['epochPolicy']==policy,'RETRY_NATIVE')
    a=n['retainedRetryAdmission'];fields={'schemaVersion','state','sourceConfigRef','targetConfigRef','recoveryPointRef',
        'predecessorOperationId','epoch','readyEpoch','targetPin','parentGenerationPin','capturePins','authorization','evidencePins','serverWrites'}
    need(type(a) is dict and set(a)==fields and a['schemaVersion']=='MainProgramRetainedRetryAdmission/v1' and
        a['state']=='FAILED_RETAINED_RETRY_ADMITTED' and a['serverWrites'] is False and a['targetConfigRef']==target and
        a['sourceConfigRef'] in activation.SOURCES and n['directlyAdmittedSources']==[a['sourceConfigRef']] and
        n['rejectedSources']=={s:'PROGRAM_RETRY_SOURCE_NOT_AUTHORIZED' for s in activation.SOURCES if s!=a['sourceConfigRef']},
        'RETRY_NATIVE_ADMISSION')
    need(type(a['predecessorOperationId']) is str and re.fullmatch('smallapp-[0-9a-f]{32}',a['predecessorOperationId']) and
        type(a['recoveryPointRef']) is str and re.fullmatch('smallapp-[0-9a-f]{32}',a['recoveryPointRef']), 'RETRY_NATIVE_REQUEST')
    epoch_fields={'schemaVersion','state','operationId','epochId','policySha256','eventPin'}
    expected_sha=hashlib.sha256(publication.canonical(policy)).hexdigest();sequences=[]
    for epoch,state,operation in ((a['readyEpoch'],'READY',None),(a['epoch'],'FAILED_RETAINED',a['predecessorOperationId'])):
        need(type(epoch) is dict and set(epoch)==epoch_fields and epoch['schemaVersion']=='SourceBackupEpoch/v1' and
            epoch['state']==state and epoch['operationId']==operation and contract.sha(epoch['epochId']) and
            epoch['policySha256']==expected_sha,'RETRY_NATIVE_EPOCH')
        ref=contract.remote_pin(epoch['eventPin']);location=PurePosixPath(ref['path'])
        need(location.parent==PurePosixPath(policy['root']) and re.fullmatch(r'[0-9]{20}\.json',location.name),'RETRY_NATIVE_EVENT')
        sequences.append(int(location.stem))
    need(a['epoch']==n['epoch'] and sequences[0]<sequences[1],'RETRY_NATIVE_EPOCH')
    auth=a['authorization'];pin_names={'configurationPin','requestPin','resultPin','exitPin','replacementResultPin','contextPin',
        'clearancePin','readyPin','noMutationReleasePin','recoveryReleasePin','observationPin','consumptionPin'}
    need(type(auth) is dict and set(auth)==pin_names|{'schemaVersion','predecessorOperationId','sourceConfigRef','recoveryPointRef','targetConfigRef'} and
        auth['schemaVersion']=='MainProgramRetainedRetryAuthorization/v1' and auth['consumptionPin'] is None and
        all(auth[k]==a[k] for k in ('predecessorOperationId','sourceConfigRef','recoveryPointRef','targetConfigRef')),'RETRY_NATIVE_AUTHORIZATION')
    required=[a['epoch']['eventPin'],a['readyEpoch']['eventPin'],contract.remote_pin(a['targetPin'])]
    if a['parentGenerationPin'] is not None:required.append(contract.remote_pin(a['parentGenerationPin']))
    captures=a['capturePins'];need(type(captures) is dict and bool(captures),'RETRY_NATIVE_CAPTURES')
    required.extend(contract.remote_pin(p) for p in captures.values())
    required.extend(contract.remote_pin(auth[k]) for k in pin_names if k!='consumptionPin')
    evidence=a['evidencePins'];need(type(evidence) is list and bool(evidence),'RETRY_NATIVE_EVIDENCE')
    by_path={}
    for p in evidence:
        contract.remote_pin(p);need(p['path'] not in by_path or by_path[p['path']]==p,'RETRY_NATIVE_EVIDENCE')
        by_path[p['path']]=p
    need(all(by_path.get(p['path'])==p for p in required),'RETRY_NATIVE_EVIDENCE')
    return a


def _api_selection(api,target,*,available=True,admitted_source=None):
    need(type(available) is bool,'HTTP_AVAILABILITY_STATE')
    need(admitted_source is None or (available and admitted_source in activation.SOURCES),'HTTP_AUTHORIZED_SOURCE')
    need(type(api) is dict and set(api)=={'applications','observedAt'},'HTTP_SHAPE')
    _timestamp(api['observedAt']);apps=api['applications']
    need(type(apps) is list and len(apps)==3 and [a.get('sourceConfigRef') for a in apps]==list(activation.SOURCES),
        'HTTP_SOURCES')
    for index,app in enumerate(apps):
        need(set(app)=={'applicationId','sourceConfigRef','engineSelectionRef','freshTargetConfigRefs','fullReady',
            'fullErrorCode','historyErrorCode','parentChainRefs','recoveryPointRefs'} and
            app['applicationId']==app['sourceConfigRef'] and type(app['engineSelectionRef']) is str and
            bool(app['engineSelectionRef']) and app['freshTargetConfigRefs']==([target] if available and
                (admitted_source is None or app['sourceConfigRef']==admitted_source) else []) and
            app['historyErrorCode'] is None and type(app['fullReady']) is bool and
            type(app['parentChainRefs']) is list and type(app['recoveryPointRefs']) is list,'HTTP_ADMISSION')
        need((index==0 and app['fullReady'] is True and app['fullErrorCode'] is None) or
            (index>0 and app['fullReady'] is False and app['fullErrorCode']=='SOURCE_RESTORE_ONLY'),'HTTP_FULL_SCOPE')


def _native_and_api(r,owner):
    _native_evidence(r,owner)
    for api in (r['originalApi'],r['apiSelection']):_api_selection(api,r['targetConfigRef'])


def verify_target_activations(source_installation,activations,*,build,build_pin,package_raw,previous_package_raw,
                              continuations=None):
    """Pure proof projection; caller first formally loads every source/base pin."""
    need(type(source_installation) is dict and source_installation.get('status')=='ACTIVATED' and
        source_installation.get('installationVerified') is True and source_installation.get('runtimeVerified') is False,
        'FORMAL_SOURCE_INSTALLATION_REQUIRED')
    need(type(activations) is dict and set(activations)==set(HOSTS),'THREE_TARGET_ACTIVATIONS_REQUIRED')
    continuations={} if continuations is None else continuations
    need(type(continuations) is dict and set(continuations)<=set(HOSTS),'CONTINUATION_HOSTS')
    base=source_installation['baseInstallation']['generation'];old_build=base['build']
    package=staging._target_package(package_raw,build);old_package=legacy.verify_package(previous_package_raw,old_build)
    rows=deepcopy(source_installation['effectiveControllersByHost']);bindings=deepcopy(source_installation['controllerBuildBindings'])
    controls={};owners={};receipts=[];specs={}
    for host in HOSTS:
        wrapper=activations[host];r=_wrapper(wrapper,host)
        extra=CONTINUATION if CONTINUATION & set(r) else set()
        need(set(r)==RESULT_FIELDS|extra and r['schemaVersion']=='MainProgramTargetControlActivation/v1' and
            r['status']=='PASS' and r['role']=='target' and r['stage']=='complete' and r['host']=='172.30.30.'+wrapper['host'] and
            r['sourceCommit']==build['targetCommit'] and r['targetConfigRef']==base['targets'][host] and
            all(r[k] is True for k in TRUE_FLAGS) and all(r[k] is False for k in FALSE_FLAGS),'RESULT_SCOPE')
        _timestamp(r['observedAt']);_receipt(r);_continuation(wrapper,continuations.get(host))
        candidate=r['candidate'];old=base['controllersByHost'][host][-1]
        dependency='spug-main-preservation-view-'+host+'-20261111-r1.service'
        need(r['addedDependencies']==dict(Requires=[dependency],After=[dependency]),'PRESERVATION_DEPENDENCY')
        need(candidate['previousController']==old,'BASE_TARGET_CHANGED')
        spec=_original_spec(source_installation,host,r)
        docs=base['privatePlan']['documentsByHost'][host]
        old_owner=_document(docs,old['ownerConfigurationPin']);old_control=_document(docs,old['controlConfigurationPin'])
        preservation=_preservation(candidate,old_owner,spec)
        rebuilt=binding.build_target_control_candidate(host=host,current_controller=old,owner=old_owner,control=old_control,
            package_files=package['payloadFiles'],previous_package_files=old_package['payloadFiles'],old_build=old_build,
            new_build=build,preservation=preservation,configuration_root=str(PurePosixPath(candidate['controller']['ownerPin']['path']).parent),
            new_engine=candidate['controller']['engine'],disk_admission_mode=candidate.get('diskAdmissionMode'))
        need(candidate==rebuilt,'CANDIDATE_REBUILD')
        gate=transition.TargetControlRuntimeTransition(spec,candidate=candidate,dropin_pin=r['dropinPin'],
            added_dependencies=r['addedDependencies'],verify_environment=_unavailable,verify_custody=_unavailable,
            lock_guard=_unavailable,run=_unavailable,pin=_unavailable,read=_unavailable)
        c=candidate['controller'];control=_document(candidate['newDocuments'],c['controlPin']);owner=_document(candidate['newDocuments'],c['ownerPin'])
        _observations(r,gate,package,old_package,old_control,control);_native_and_api(r,owner)
        location=PurePosixPath(r['activationReceiptPin']['path']);parent=PurePosixPath(old['engine']).parent
        need(location.name=='result-activate.private.json' and location.parent.parent==parent and
            re.fullmatch('control-activation-main-target-'+build['targetCommit'][:7]+r'-r[1-9][0-9]*',location.parent.name),
            'RECEIPT_PATH')
        created={str(location.parent)}
        if not extra:created|={str(location.parent/'before.private.json'),r['dropinPin']['path']}
        need(type(r['createdPaths']) is list and len(set(r['createdPaths']))==len(r['createdPaths']) and
            set(r['createdPaths']) in (created,created|{str(location)}),'CREATED_PATHS')
        rows[host][-1]=deepcopy(r['currentController'])
        bindings[host]['target']=dict(buildPin=deepcopy(build_pin),sourceCommit=build['targetCommit'])
        controls[host]=deepcopy(control);owners[host]=deepcopy(owner)
        receipts.append(deepcopy(r['activationReceiptPin']))
        specs[host]=dict(original=deepcopy(spec),successor=deepcopy(gate._successor(r['currentController']['pid']).spec))
    return dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,
        sourceInstallation=deepcopy(source_installation),baseInstallation=deepcopy(source_installation['baseInstallation']),
        effectiveControllersByHost=rows,controllerBuildBindings=bindings,targetControls=controls,targetOwners=owners,
        targetRuntimeSpecs=specs,activationReceiptPins=receipts,inputPins=[])


def _private_bytes(private,reference,pins):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'},'LOCAL_PIN')
    root=Path(private).resolve(strict=True);path=Path(reference['path'])
    need(path.is_absolute() and path.resolve(strict=True).is_relative_to(root),'PRIVATE_INPUT_SCOPE')
    raw=publication.verify_bytes(reference);pins.append(deepcopy(reference));return raw


def _private_json(private,reference,pins):
    raw=_private_bytes(private,reference,pins)
    need(len(raw)<=16*1024*1024,'LOCAL_DOCUMENT_LIMIT')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=contract.document)
    need(type(value) is dict,'LOCAL_DOCUMENT');return value


def load_activated_target_installation(task,private,*,selection_file,historical_source_custody_pin=None):
    """Read complete local pinned chains; no remote runtime boundary is called."""
    modules=(activation,runtime,legacy,contract,source,publication,binding,transition,staging)
    codepins=[publication.file_pin(Path(module.__file__).resolve()) for module in modules]
    codepins.append(publication.file_pin(Path(__file__).resolve()))
    records=contract.Records(task);selection=records.read(selection_file)
    need(set(selection)==FIELDS and selection['schemaVersion']==SCHEMA,'SELECTION')
    reference=selection['baseSourceSelectionPin'];records.pinned(reference)
    args={} if historical_source_custody_pin is None else dict(historical_source_custody_pin=historical_source_custody_pin)
    installation=source.load_activated_installation(task,private,selection_file=reference['file'],**args)
    need(installation['selectionPin']==reference,'SOURCE_SELECTION_BINDING')
    build=records.pinned(selection['buildPin']);pins=[]
    raw=_private_bytes(private,selection['standardPackagePin'],pins)
    oldref=installation['baseInstallation']['generation']['build']['variants']['standard']['packagePin']
    oldraw=_private_bytes(private,oldref,pins)
    evidence=selection['targetActivationEvidencePins']
    need(type(evidence) is dict and set(evidence)==set(HOSTS),'THREE_TARGET_EVIDENCE_PINS')
    activations={};continuations={}
    for host in HOSTS:
        wrapper=_private_json(private,evidence[host],pins);activations[host]=wrapper
        _private_bytes(private,wrapper['scriptPin'],pins)
        if CONTINUATION_LOCAL & set(wrapper):
            need(CONTINUATION_LOCAL<=set(wrapper),'CONTINUATION_LOCAL_PINS')
            context={}
            for key,name in (('continuationLocalFailurePin','failure'),('continuationLocalPreparePin','prepare')):
                prior=_private_json(private,wrapper[key],pins);context[name]=prior
                _private_bytes(private,prior['scriptPin'],pins)
            continuations[host]=context
    result=verify_target_activations(installation,activations,build=build,build_pin=selection['buildPin'],
        package_raw=raw,previous_package_raw=oldraw,continuations=continuations)
    result.update(selection=deepcopy(selection),selectionPin=records.references[selection_file])
    result['inputPins']=source.unique_pins(installation['inputPins']+records.path_pins()+pins+codepins)
    for pin in result['inputPins']:publication.verify_bytes(pin)
    return result
