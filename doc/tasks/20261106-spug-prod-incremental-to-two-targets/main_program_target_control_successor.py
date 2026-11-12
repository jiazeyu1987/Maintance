"""Pinned target successors with immutable v1 and reviewed repeated v2 protocols.

Pure configuration and file plans do not establish installation or runtime health.
The original 147->153 contracts and their historical evidence remain unchanged.
"""
from copy import deepcopy
import base64
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
from types import SimpleNamespace

import main_program_control_upgrade_plan as planner
import main_program_target_control_candidate as binding
import main_program_target_control_staging as staging
import main_program_target_control_runtime as transition
import main_program_target_control_activated as activated
import main_program_installation_selection as contract

HOSTS=('57','58','59')
PREDECESSOR_COMMIT='a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e'
READER='common/recovery_backup_epoch.py'
SELECTION_SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v1'
REPEAT_SELECTION_SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v2'
MAX_SUCCESSOR_DEPTH=16
PARTIAL_SCHEMA='TaskMainProgramTargetControlPartialPredecessor/v1'
MIXED_SELECTION_SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v3'
PACKAGE_DELTA_PROFILES={
    'MAIN_TARGET_CAPTURE_PREPARATION_COMPATIBILITY/v1':frozenset((
        'common/recovery_capture_materials.py','common/recovery_resource_admission.py',
        'common/recovery_retained_retry.py','common/recovery_target_capture.py')),
}
RETAINED_RETRY_CHANGED=frozenset((
    'common/recovery_main_target.py','common/recovery_program_activation.py','common/recovery_program_execution.py',
    'common/recovery_program_evidence.py','common/recovery_program_restore.py','common/recovery_program_targets.py','common/recovery_program_native.py',
    'control/recovery_control_target_availability.py'))
RETAINED_RETRY_ADDED=frozenset(('common/recovery_program_retry.py',))
PACKAGE_GROWTH_PROFILES={
    'MAIN_TARGET_RETAINED_RETRY_FROM_PREPARATION/v1':RETAINED_RETRY_CHANGED,
    'MAIN_TARGET_RETAINED_RETRY_FROM_READER/v1':RETAINED_RETRY_CHANGED|
        PACKAGE_DELTA_PROFILES['MAIN_TARGET_CAPTURE_PREPARATION_COMPATIBILITY/v1'],
}
PACKAGE_SAME_154_PROFILES={
    'MAIN_TARGET_RELEASED_STATE_PROJECTION/v1':frozenset(('control/recovery_control_smallapp_native.py',)),
}


def need(condition,code):
    if not condition:raise ValueError('MAIN_TARGET_SUCCESSOR_'+code)


def _content_pin(location,raw):
    return dict(path=str(location),bytes=len(raw),sha256=planner.digest(raw))


def _official_package(raw,build,*,payload_count=153):
    need(type(build) is dict and build.get('status')=='PASS' and build.get('exactCommittedInput') is True and
        build.get('allFilesShaAndCompileVerified') is True and build.get('newCommits') is False and
        build.get('mergeRequired') is False and type(build.get('targetCommit')) is str and
        re.fullmatch('[0-9a-f]{40}',build['targetCommit']) is not None,'OFFICIAL_BUILD_REQUIRED')
    return staging._target_package(raw,build,payload_count=payload_count)


def _delta_payload_count(review):
    """Only source-reviewed profiles, never a caller count, authorize 154."""
    if type(review) is dict and review.get('schemaVersion')=='MainProgramTargetControlPackageDeltaReview/v2':
        need(review.get('profileId') in PACKAGE_GROWTH_PROFILES,'PACKAGE_DELTA_PROFILE_REQUIRED')
        return 154
    if type(review) is dict and review.get('schemaVersion')=='MainProgramTargetControlPackageDeltaReview/v3':
        need(review.get('profileId') in PACKAGE_SAME_154_PROFILES,'PACKAGE_DELTA_PROFILE_REQUIRED')
        return 154
    return 153


def _delta_previous_payload_count(review):
    if type(review) is dict and review.get('schemaVersion')=='MainProgramTargetControlPackageDeltaReview/v3':
        _delta_payload_count(review)
        return 154
    return 153


def _pinned_document(reference,raw,expected):
    planner.local_pin(reference)
    need(type(raw) is bytes and 0<len(raw)<=16*1024*1024 and reference['bytes']==len(raw) and
        reference['sha256']==planner.digest(raw),'ORIGINAL_DOCUMENT_BYTES')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=planner.document)
    need(type(value) is dict and value==expected,'ORIGINAL_DOCUMENT_VALUE')


def _private_input_pin(reference):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
        type(reference['path']) is str and type(reference['bytes']) is int and reference['bytes']>0 and
        type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}',reference['sha256']) is not None,
        'PRIVATE_INPUT_PIN')
    name=reference['path'];location=PureWindowsPath(name) if PureWindowsPath(name).drive else PurePosixPath(name)
    need(location.is_absolute() and str(location)==name and '..' not in location.parts and
        not any(ord(c)<32 for c in name),'PRIVATE_INPUT_PATH')
    return reference


def _predecessor(value,reference,selection_raw,build,build_raw,raw,host):
    need(type(value) is dict and value.get('status')=='ACTIVATED' and value.get('installationVerified') is True and
        value.get('runtimeVerified') is False and host in HOSTS,'FORMAL_PREDECESSOR_REQUIRED')
    selection=value.get('selection')
    need(type(selection) is dict and set(selection)=={'schemaVersion','baseSourceSelectionPin','buildPin',
        'standardPackagePin','targetActivationEvidencePins'} and
        selection['schemaVersion']=='TaskMainProgramTargetControlSelection/v1','PREDECESSOR_SELECTION')
    _pinned_document(reference,selection_raw,selection)
    need(value.get('selectionPin')==reference,'PREDECESSOR_SELECTION_PIN')
    build_pin=planner.local_pin(selection['buildPin'])
    _pinned_document(build_pin,build_raw,build)
    need(build.get('targetCommit')==PREDECESSOR_COMMIT,'PREDECESSOR_BUILD_PIN')
    _private_input_pin(selection['standardPackagePin'])
    need(selection['standardPackagePin']==_content_pin(selection['standardPackagePin']['path'],raw),
        'PREDECESSOR_PACKAGE_PIN')
    need(type(selection['targetActivationEvidencePins']) is dict and
        set(selection['targetActivationEvidencePins'])==set(HOSTS),'PREDECESSOR_ACTIVATION_HOSTS')
    for p in selection['targetActivationEvidencePins'].values():_private_input_pin(p)
    rows=value.get('effectiveControllersByHost',{}).get(host)
    need(type(rows) is list and rows and all(type(r) is dict for r in rows),'PREDECESSOR_CONTROLLERS')
    targets=[r for r in rows if r.get('role')=='target']
    need(len(targets)==1,'PREDECESSOR_TARGET_COUNT');core=targets[0]
    need(core.get('schemaVersion')=='MainProgramControlActivation/v1' and core.get('status')=='PASS' and
        core.get('host')=='172.30.30.'+host and core.get('sourceCommit')==PREDECESSOR_COMMIT and
        core.get('fileCount')==153 and type(core.get('service')) is str and
        re.fullmatch(r'[A-Za-z0-9_.@-]+\.service',core['service']) is not None,'PREDECESSOR_CONTROLLER')
    role=value.get('controllerBuildBindings',{}).get(host,{}).get('target')
    need(role==dict(buildPin=build_pin,sourceCommit=PREDECESSOR_COMMIT),'PREDECESSOR_ROLE_BUILD')
    return core,build_pin


def _repeat_predecessor(value,reference,selection_raw,build,build_raw,raw,host,*,payload_count=153):
    partial=type(value) is dict and value.get('status')=='PARTIALLY_ACTIVATED'
    formal_partial=(partial and value.get('installationVerified') is False and
        value.get('activationVerifiedHosts')==['57'] and value.get('retainedBaseHosts')==['58','59'])
    need(type(value) is dict and ((value.get('status')=='ACTIVATED' and value.get('installationVerified') is True) or formal_partial) and
        value.get('runtimeVerified') is False and host in HOSTS,'FORMAL_PREDECESSOR_REQUIRED')
    selection=value.get('selection');need(type(selection) is dict,'PREDECESSOR_SELECTION')
    version=selection.get('schemaVersion')
    if partial:
        need(version==PARTIAL_SCHEMA,'PREDECESSOR_SELECTION')
        fields={'schemaVersion','baseSelectionPin','buildPin','standardPackagePin','packageDeltaReviewPin','targetActivationEvidencePins'}
    elif version==activated.SCHEMA:
        fields=activated.FIELDS
    else:
        need(version in (SELECTION_SCHEMA,REPEAT_SELECTION_SCHEMA,MIXED_SELECTION_SCHEMA),'PREDECESSOR_SELECTION')
        fields={'schemaVersion','predecessorSelectionPin','buildPin','standardPackagePin','targetActivationEvidencePins'}
        if version==REPEAT_SELECTION_SCHEMA:fields=fields|{'packageDeltaReviewPin'}
        if version==MIXED_SELECTION_SCHEMA:
            fields=fields|{'packageDeltaReviewPinsByHost'}
            if 'archiveOwnerVerificationPinsByHost' in selection:
                refs=selection['archiveOwnerVerificationPinsByHost']
                need(type(refs) is dict and set(refs)=={'58'},'ARCHIVE_OWNER_VERIFICATION_HOST')
                _private_input_pin(refs['58'])
                fields=fields|{'archiveOwnerVerificationPinsByHost'}
    need(set(selection)==fields,'PREDECESSOR_SELECTION')
    _pinned_document(reference,selection_raw,selection)
    need(value.get('selectionPin')==reference,'PREDECESSOR_SELECTION_PIN')
    artifacts=_predecessor_artifacts(value,host)
    build_pin=planner.local_pin(artifacts['buildPin']);_pinned_document(build_pin,build_raw,build)
    _private_input_pin(artifacts['standardPackagePin'])
    need(artifacts['standardPackagePin']==_content_pin(artifacts['standardPackagePin']['path'],raw),'PREDECESSOR_PACKAGE_PIN')
    evidence=selection['targetActivationEvidencePins']
    need(type(evidence) is dict and set(evidence)==({'57'} if partial else set(HOSTS)),'PREDECESSOR_ACTIVATION_HOSTS')
    for p in evidence.values():_private_input_pin(p)
    rows=value.get('effectiveControllersByHost',{}).get(host)
    need(type(rows) is list and [r.get('role') for r in rows]==(['source','target'] if host=='57' else ['target']),
        'PREDECESSOR_CONTROLLERS')
    core=rows[-1];commit=build.get('targetCommit')
    need(core.get('schemaVersion')=='MainProgramControlActivation/v1' and core.get('status')=='PASS' and
        core.get('host')=='172.30.30.'+host and core.get('sourceCommit')==commit and
        payload_count in (153,154) and core.get('fileCount')==payload_count and
        type(core.get('service')) is str and re.fullmatch(r'[A-Za-z0-9_.@-]+\.service',core['service']) is not None,
        'PREDECESSOR_CONTROLLER')
    need(value.get('controllerBuildBindings',{}).get(host,{}).get('target')==dict(buildPin=build_pin,sourceCommit=commit),
        'PREDECESSOR_ROLE_BUILD')
    specs=value.get('targetRuntimeSpecs',{}).get(host)
    need(type(specs) is dict and set(specs)=={'original','successor'},'PREDECESSOR_RUNTIME_BINDING')
    runtime_rows=specs['successor']['current']['controllers']
    # The original source loader omits this derived mode in its effective row;
    # its admitted current runtime records CONFIG_EXACT. No target or other
    # source field may be projected away, and the reverse difference is invalid.
    source_projection=(host=='57' and type(runtime_rows) is list and len(runtime_rows)==2 and
        type(runtime_rows[0]) is dict and 'environmentMode' not in rows[0] and
        runtime_rows[0].get('environmentMode')=='CONFIG_EXACT' and
        {k:v for k,v in runtime_rows[0].items() if k!='environmentMode'}==rows[0] and runtime_rows[-1]==rows[-1])
    need(runtime_rows==rows or source_projection,'PREDECESSOR_RUNTIME_BINDING')
    return core,build_pin


def _predecessor_artifacts(value,host):
    if value.get('status')=='PARTIALLY_ACTIVATED':
        mapping=value.get('targetPredecessorArtifactsByHost')
        need(type(mapping) is dict and set(mapping)==set(HOSTS),'PARTIAL_PREDECESSOR_ARTIFACTS')
        row=mapping[host]
        need(type(row) is dict and set(row)=={'buildPin','standardPackagePin','sourceCommit'} and
            value['controllerBuildBindings'][host]['target']==dict(buildPin=row['buildPin'],sourceCommit=row['sourceCommit']) and
            value['effectiveControllersByHost'][host][-1]['sourceCommit']==row['sourceCommit'],'PARTIAL_PREDECESSOR_ARTIFACT_BINDING')
        return row
    return dict(buildPin=value['selection']['buildPin'],standardPackagePin=value['selection']['standardPackagePin'],
        sourceCommit=value['controllerBuildBindings'][host]['target']['sourceCommit'])


def _review_delta(review,reference,raw,*,predecessor,old_build,build,build_pin,build_raw,previous,package,host):
    fields={'schemaVersion','status','profileId','predecessorSelectionPin','predecessorCommit','sourceCommit',
        'predecessorBuildPin','buildPin','previousPackagePin','standardPackagePin','changedMembers'}
    count=_delta_payload_count(review);previous_count=_delta_previous_payload_count(review)
    growth=type(review) is dict and review.get('schemaVersion')=='MainProgramTargetControlPackageDeltaReview/v2'
    same_154=previous_count==154
    need(type(review) is dict and set(review)==fields|({'addedMembers'} if growth else set()) and
        review['schemaVersion']=='MainProgramTargetControlPackageDeltaReview/'+('v3' if same_154 else ('v2' if growth else 'v1')) and review['status']=='REVIEWED',
        'PACKAGE_DELTA_REVIEW_REQUIRED')
    profiles=PACKAGE_SAME_154_PROFILES if same_154 else (PACKAGE_GROWTH_PROFILES if growth else PACKAGE_DELTA_PROFILES)
    need(type(review['profileId']) is str and review['profileId'] in profiles,
        'PACKAGE_DELTA_PROFILE_REQUIRED')
    _pinned_document(reference,raw,review);_pinned_document(build_pin,build_raw,build)
    artifacts=_predecessor_artifacts(predecessor,host)
    need(review['predecessorSelectionPin']==predecessor['selectionPin'] and
        review['predecessorCommit']==old_build['targetCommit'] and review['sourceCommit']==build['targetCommit'] and
        review['predecessorBuildPin']==artifacts['buildPin'] and review['buildPin']==build_pin and
        review['previousPackagePin']==artifacts['standardPackagePin'],'PACKAGE_DELTA_REVIEW_BINDING')
    _private_input_pin(review['standardPackagePin'])
    need(review['standardPackagePin']['bytes']==package['rawBytes'] and
        review['standardPackagePin']['sha256']==package['packageSha256'],'PACKAGE_DELTA_REVIEW_PACKAGE')
    old=previous['payloadFiles'];new=package['payloadFiles']
    need(len(old)==previous_count and len(new)==count and
        (set(new)==set(old)|RETAINED_RETRY_ADDED if growth else set(old)==set(new)),
        'UNREVIEWED_PACKAGE_DELTA')
    changes=[dict(member=n,previousSha256=planner.digest(old[n]),sha256=planner.digest(new[n]))
        for n in sorted(old) if old[n]!=new[n]]
    need({row['member'] for row in changes}==profiles[review['profileId']],
        'PACKAGE_DELTA_PROFILE_MEMBERS')
    need(bool(changes) and review['changedMembers']==changes,'UNREVIEWED_PACKAGE_DELTA')
    if growth:
        need(review['addedMembers']==[dict(member=n,sha256=planner.digest(new[n])) for n in sorted(RETAINED_RETRY_ADDED)],
            'UNREVIEWED_PACKAGE_ADDITIONS')


def _graph_pins(graph):
    need(type(graph) is dict and type(graph.get('documents')) is list,'PREDECESSOR_GRAPH_REQUIRED')
    rows=graph['documents'];names={PurePosixPath(r['pin']['path']).name:r['pin'] for r in rows}
    need(len(rows)==len(names)==14 and set(names)==set(binding.DOCUMENT_SCHEMAS),'PREDECESSOR_PRESERVATION_SET')
    return names


def _current_preservation_documents_for_host(installation,wrapper,host):
    r=wrapper['result'];candidate=r['candidate'];core=installation['effectiveControllersByHost'][host][-1]
    owner=installation['targetOwners'][host];ref=core['targetConfigRef'];program=owner['targetProgramPolicies'][ref]
    need(r['currentController']==core and candidate['controller']['ownerPin']==core['ownerConfigurationPin'] and
        candidate['controller']['controlPin']==core['controlConfigurationPin'] and
        planner.remote_pin(core['ownerConfigurationPin']['path'],owner)==core['ownerConfigurationPin'],
        'PREDECESSOR_CURRENT_GRAPH_BINDING')
    rows=candidate.get('retainedPreservationDocuments',[])+candidate['newDocuments']
    by_path={}
    for row in rows:
        p=binding.pin(row['pin']);need(planner.remote_pin(p['path'],row['value'])==p,'PREDECESSOR_GRAPH_ORIGINAL_CHANGED')
        if p['path'] in by_path:need(by_path[p['path']]==row,'PREDECESSOR_GRAPH_PIN_CONFLICT')
        by_path[p['path']]=deepcopy(row)
    policy_pin=owner['targetPreservationPolicies'][ref]
    seen={};pending=[policy_pin]
    def refs(value):
        if type(value) is dict:
            if set(value)=={'path','bytes','sha256'}:
                if value['path'] in by_path:yield value
            else:
                for v in value.values():yield from refs(v)
        elif type(value) is list:
            for v in value:yield from refs(v)
    while pending:
        p=pending.pop();need(p['path'] in by_path and by_path[p['path']]['pin']==p,'PREDECESSOR_GRAPH_EDGE_CHANGED')
        if p['path'] in seen:continue
        row=by_path[p['path']];seen[p['path']]=row;pending.extend(refs(row['value']))
    names={PurePosixPath(row['pin']['path']).name:row for row in seen.values()}
    need(len(seen)==len(names)==14 and set(names)==set(binding.DOCUMENT_SCHEMAS),'PREDECESSOR_PRESERVATION_SET')
    registered=installation['targetRuntimeSpecs'][host]['successor']
    admitted=registered['retainedDocuments']+registered['newDocuments']
    need(all(row['pin'] in admitted for row in seen.values()),'PREDECESSOR_GRAPH_NOT_RETAINED')
    originals=[p for p in installation['targetRuntimeSpecs'][host]['original']['retainedDocuments']
        if PurePosixPath(p['path']).name in ('mount.credentials','nas-smb-v1.private.json')]
    need(len(originals)==1,'PREDECESSOR_ORIGINAL_CREDENTIAL')
    graph=dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',targetConfigRef=ref,
        captureRef=ref+'-pre-restore',capturePin=names['capture.json']['pin'],repositoryPin=names['repository.json']['pin'],
        policyPin=policy_pin,documents=[deepcopy(names[name]) for name in binding.DOCUMENT_SCHEMAS],
        originalCredentialPins=[owner['targets'][ref]['secrets']['minio'][key]
            for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')]+deepcopy(originals))
    return graph


def bind_current_preservation_documents(installation,activations):
    """Project a graph only from wrappers already accepted by the formal verifier.

    Every row remains bound to the accepted current owner/controller/runtime.
    This does not grant unverified wrapper data any installation authority.
    """
    need(installation.get('status')=='ACTIVATED' and installation.get('installationVerified') is True and
        installation.get('runtimeVerified') is False and set(activations)==set(HOSTS),'FORMAL_PREDECESSOR_REQUIRED')
    return {host:_current_preservation_documents_for_host(installation,activations[host],host) for host in HOSTS}


def build_target_control_successor_candidate(*,predecessor,predecessor_selection_pin,predecessor_build,build,
        predecessor_selection_raw,predecessor_build_raw,predecessor_package_raw,package_raw,host,
        preservation_documents,configuration_root,new_engine,retained_failure_pins,package_delta_review=None,
        package_delta_review_pin=None,package_delta_review_raw=None,build_pin=None,build_raw=None):
    """Bind exactly four successor documents; never read or mutate a filesystem."""
    repeated=any(v is not None for v in (package_delta_review,package_delta_review_pin,package_delta_review_raw,build_pin,build_raw))
    predecessor_check=_repeat_predecessor if repeated else _predecessor
    previous_count=_delta_previous_payload_count(package_delta_review) if repeated else 153
    core,old_build_pin=predecessor_check(predecessor,predecessor_selection_pin,predecessor_selection_raw,
        predecessor_build,predecessor_build_raw,predecessor_package_raw,host,**(dict(payload_count=previous_count) if repeated else {}))
    count=_delta_payload_count(package_delta_review) if repeated else 153
    previous=_official_package(predecessor_package_raw,predecessor_build,payload_count=previous_count)
    package=_official_package(package_raw,build,payload_count=count)
    files=package['payloadFiles'];old_files=previous['payloadFiles'];commit=build['targetCommit']
    previous_commit=predecessor_build['targetCommit']
    if repeated:
        # The raw tar identity is reviewed independently of its payload manifest.
        package=dict(package,rawBytes=len(package_raw))
        _review_delta(package_delta_review,package_delta_review_pin,package_delta_review_raw,predecessor=predecessor,
            old_build=predecessor_build,build=build,build_pin=build_pin,build_raw=build_raw,previous=previous,package=package,host=host)
        need(commit[:7]!=previous_commit[:7],'UNREVIEWED_PACKAGE_DELTA')
    else:
        need(commit[:7]!=PREDECESSOR_COMMIT[:7] and set(files)==set(old_files) and
            {name for name in files if files[name]!=old_files[name]}=={READER},'UNREVIEWED_PACKAGE_DELTA')
    need(core.get('fileManifestSha256')==previous['fileManifestSha256'],'PREDECESSOR_MANIFEST')
    old_engine=str(binding.path(core['engine']));parent=binding.path(old_engine).parent;root=binding.path(configuration_root)
    need(binding.path(new_engine)==parent/('engine-main-program-'+commit[:7]) and
        binding.path(old_engine).name=='engine-main-program-'+previous_commit[:7],'ENGINE_LOCATION')
    need(root.parent==parent/'configuration' and
        re.fullmatch('main-target-'+commit[:7]+r'-r[1-9][0-9]*',root.name) is not None,'CONFIGURATION_LOCATION')
    owner=predecessor.get('targetOwners',{}).get(host);control=predecessor.get('targetControls',{}).get(host)
    need(type(owner) is dict and owner.get('schemaVersion')=='RecoveryMinimalConfiguration/v1' and
        type(control) is dict and control.get('schemaVersion')=='SmallAppExecutionServiceConfig/v2','CONFIGURATION_SCHEMA')
    for value,key in ((owner,'ownerConfigurationPin'),(control,'controlConfigurationPin')):
        p=binding.pin(core[key]);need(p==planner.remote_pin(p['path'],value),'CURRENT_CONFIGURATION_PIN')
    old_root=binding.path(core['ownerConfigurationPin']['path']).parent
    need(binding.path(core['controlConfigurationPin']['path']).parent==old_root and old_root!=root and
        owner.get('formalModuleDirectory')==old_engine+'/formal','CURRENT_CONFIGURATION_LOCATION')
    ref=core.get('targetConfigRef');need(type(ref) is str and ref and set(owner.get('targets',{}))=={ref},'TARGET_SCOPE')
    program=owner.get('targetProgramPolicies',{}).get(ref)
    need(type(program) is dict and program.get('schemaVersion')=='RegisteredMainProgramPolicy/v1' and
        program.get('targetConfigRef')==ref,'TARGET_PROGRAM_POLICY')
    graph_args={}
    if repeated:
        registered=predecessor.get('currentPreservationDocumentsByHost',{}).get(host)
        need(preservation_documents==registered,'PREDECESSOR_CURRENT_GRAPH_BINDING')
        originals=predecessor['targetRuntimeSpecs'][host]['successor']
        admitted=originals['retainedDocuments']+originals['newDocuments']
        graph_args['exact_document_pins']=_graph_pins(registered)
        need(all(p in admitted for p in graph_args['exact_document_pins'].values()),'PREDECESSOR_GRAPH_NOT_RETAINED')
    retained=binding.preservation_graph(preservation_documents,old_root,ref,owner['targets'][ref],program,old_engine,old_files,**graph_args)
    need(owner.get('targetPreservationPolicies',{}).get(ref)==preservation_documents['policyPin'] and
        program.get('captureConfigurationPins',{}).get(preservation_documents['captureRef'])==preservation_documents['capturePin'],
        'CURRENT_PRESERVATION_BINDING')
    need(type(retained_failure_pins) is list,'FAILURE_PIN_SET')
    for p in retained_failure_pins:binding.pin(p)
    need(len({p['path'] for p in retained_failure_pins})==len(retained_failure_pins),'DUPLICATE_FAILURE_PIN')
    if repeated:
        need(retained_failure_pins==predecessor.get('retainedFailurePinsByHost',{}).get(host),
            'PREDECESSOR_FAILURE_ORIGINALS')
    by_name={PurePosixPath(row['pin']['path']).name:row for row in retained}
    repository=deepcopy(by_name['repository.json']['value']);binder='formal/formal_capture_recovery_inputs.py'
    repository['captureBinderPin']=_content_pin(binding.path(new_engine)/binder,files[binder])
    repository_pin=planner.remote_pin(str(root/'preservation/repository.json'),repository)
    policy=deepcopy(by_name['policy.json']['value']);policy['repositoryConfigurationPin']=repository_pin
    policy_pin=planner.remote_pin(str(root/'preservation/policy.json'),policy)
    new_owner=deepcopy(owner);new_owner['formalModuleDirectory']=new_engine+'/formal'
    new_owner['targetPreservationPolicies'][ref]=policy_pin
    owner_pin=planner.remote_pin(str(root/'main-recovery.json'),new_owner)
    new_control=deepcopy(control)
    need(type(control.get('programPins')) is dict and set(control['programPins'])=={'recovery','repository'},'PROGRAM_ROLES')
    new_control['programPins']={role:planner.program_pin(binding.pin(p),old_engine,new_engine,files,old_files)
        for role,p in control['programPins'].items()}
    need(all(p['path']==new_engine+'/'+role+'_entry.py' for role,p in new_control['programPins'].items()),'PROGRAM_PATH')
    need(type(control.get('environment')) is dict and 'PYTHONPATH' in control['environment'],'PROGRAM_ENVIRONMENT')
    new_control['environment']['PYTHONPATH']=planner.python_path(control['environment']['PYTHONPATH'],old_engine,new_engine)
    restores=control.get('restoreConfigurations');need(type(restores) is dict and restores,'RESTORE_BINDINGS')
    need(all(type(source) is str and source and type(targets) is dict and set(targets)=={ref} and
        targets[ref]==core['ownerConfigurationPin'] for source,targets in restores.items()),'CURRENT_OWNER_BINDING')
    new_control['restoreConfigurations']=planner.replace_references(restores,
        {planner.canonical(core['ownerConfigurationPin']):owner_pin})
    control_pin=planner.remote_pin(str(root/'control-target.json'),new_control)
    docs=[dict(pin=p,value=v) for p,v in ((repository_pin,repository),(policy_pin,policy),(owner_pin,new_owner),(control_pin,new_control))]
    result=dict(schemaVersion='MainProgramTargetControlSuccessorCandidate/v1',status='BOUND_NOT_INSTALLED',host=core['host'],
        targetConfigRef=ref,sourceCommit=commit,predecessorSelectionPin=deepcopy(predecessor_selection_pin),
        predecessorBuildPin=deepcopy(old_build_pin),previousController=deepcopy(core),
        controller=dict(role='target',service=core['service'],engine=new_engine,
            previousControlPin=deepcopy(core['controlConfigurationPin']),previousOwnerPin=deepcopy(core['ownerConfigurationPin']),
            controlPin=control_pin,ownerPin=owner_pin),newDocuments=docs,retainedPreservationDocuments=retained,
        package=dict(fileCount=count,fileManifestSha256=package['fileManifestSha256'],packageSha256=package['packageSha256']),
        previousPackage=dict(fileCount=previous_count,fileManifestSha256=previous['fileManifestSha256'],packageSha256=previous['packageSha256']),
        retainedFailurePins=deepcopy(retained_failure_pins),retainedSourceConfigurationUnchanged=True,
        installationPerformed=False,restoreDispatched=False)
    if repeated:result.update(schemaVersion='MainProgramTargetControlSuccessorCandidate/'+('v3' if count==154 else 'v2'),
        packageDeltaReviewPin=deepcopy(package_delta_review_pin),buildPin=deepcopy(build_pin))
    return result


def build_target_successor_staging_plan(*,candidate,**inputs):
    """Return exclusive writes and original pins; the caller enforces IO gates."""
    rebuilt=build_target_control_successor_candidate(**inputs);need(candidate==rebuilt,'CANDIDATE_REBUILD')
    count=_delta_payload_count(inputs.get('package_delta_review'))
    previous_count=_delta_previous_payload_count(inputs.get('package_delta_review'))
    package=_official_package(inputs['package_raw'],inputs['build'],payload_count=count)
    previous=_official_package(inputs['predecessor_package_raw'],inputs['predecessor_build'],payload_count=previous_count)
    writes=[dict(pin=_content_pin(binding.path(candidate['controller']['engine'])/name,raw),raw=raw,mode=0o400,exclusive=True)
        for name,raw in sorted(package['files'].items())]
    writes.extend(dict(pin=deepcopy(row['pin']),raw=planner.canonical(row['value']),mode=0o400,exclusive=True)
        for row in candidate['newDocuments'])
    retained=[_content_pin(binding.path(candidate['previousController']['engine'])/name,raw)
        for name,raw in sorted(previous['files'].items())]
    retained.extend(deepcopy(row['pin']) for row in candidate['retainedPreservationDocuments'])
    retained.extend(deepcopy(candidate['previousController'][key]) for key in ('ownerConfigurationPin','controlConfigurationPin'))
    locations={r['pin']['path'] for r in writes};originals={p['path'] for p in retained}
    need(len(writes)==len(locations)==count+5 and len(retained)==len(originals)==previous_count+17 and not locations&originals,'PATH_COLLISION')
    version=candidate['schemaVersion'].rsplit('/',1)[-1]
    return dict(schemaVersion='MainProgramTargetSuccessorStagingPlan/'+version,status='PLANNED_NOT_STAGED',
        payloadFileCount=count,packageFileCount=count+1,documentCount=4,writes=writes,retainedPins=retained,
        installationPerformed=False,restoreDispatched=False,serverWrites=False)


class _PureTransition(transition.TargetControlRuntimeTransition):
    """Reuse only row/comparison semantics, without constructing a runtime gate."""
    def __init__(self,*,current_spec,retained_history_spec,candidate,dropin_pin,continuation_dropin_pin=None):
        fields={'current','unit','environmentBaseline','targetConfigRef','previousCustody','oldReceiptPin',
            'originalInventory','historyPins','sourceEvidencePins','newDocuments','retainedDocuments'}
        need(type(current_spec) is dict and set(current_spec)==fields and
            type(retained_history_spec) is dict and set(retained_history_spec)==fields,'RUNTIME_SPEC_SHAPE')
        repeated=candidate.get('schemaVersion') in ('MainProgramTargetControlSuccessorCandidate/v2','MainProgramTargetControlSuccessorCandidate/v3')
        need(candidate.get('schemaVersion') in ('MainProgramTargetControlSuccessorCandidate/v1','MainProgramTargetControlSuccessorCandidate/v2','MainProgramTargetControlSuccessorCandidate/v3') and
            candidate.get('status')=='BOUND_NOT_INSTALLED' and len(candidate.get('newDocuments',[]))==4 and
            candidate.get('installationPerformed') is False and candidate.get('restoreDispatched') is False,
            'RUNTIME_CANDIDATE')
        host=candidate['host'];suffix=host.rsplit('.',1)[-1];rows=current_spec['current']['controllers']
        need(suffix in HOSTS and current_spec['current']['host']==host and current_spec['current']['suffix']==suffix and
            [r['role'] for r in rows]==(['source','target'] if suffix=='57' else ['target']) and
            current_spec['targetConfigRef']==retained_history_spec['targetConfigRef']==candidate['targetConfigRef'],
            'RUNTIME_SCOPE')
        self.index=len(rows)-1;self.old=deepcopy(rows[self.index])
        previous_count=candidate['previousPackage']['fileCount']
        need(previous_count==153 or (repeated and candidate['schemaVersion']=='MainProgramTargetControlSuccessorCandidate/v3' and
            previous_count==154 and candidate['package']['fileCount']==154),'RUNTIME_PREVIOUS_PACKAGE_COUNT')
        need(self.old==candidate['previousController'] and self.old.get('fileCount')==previous_count and
            (repeated or self.old.get('sourceCommit')==PREDECESSOR_COMMIT),'RUNTIME_CURRENT_BINDING')
        if repeated:
            need(continuation_dropin_pin is None and type(self.old.get('sourceCommit')) is str and
                re.fullmatch('[0-9a-f]{40}',self.old['sourceCommit']) is not None and
                candidate.get('predecessorBuildPin') is not None and candidate.get('packageDeltaReviewPin') is not None,
                'RUNTIME_REPEATED_BINDING')
        historical=retained_history_spec['current']
        need(historical['host']==host and historical['suffix']==suffix and
            [r['role'] for r in historical['controllers']]==[r['role'] for r in rows] and
            historical['controllers'][-1]['fileCount']==147 and
            historical['controllers'][-1]['service']==self.old['service'] and
            all(current_spec[k]==retained_history_spec[k] for k in ('previousCustody','oldReceiptPin','originalInventory')),
            'RUNTIME_RETAINED_HISTORY_BINDING')
        units=[u for u in current_spec['unit']['controllers'] if u['service']==self.old['service']]
        need(len(units)==1,'RUNTIME_UNIT_BINDING');self.old_unit=deepcopy(units[0])
        self.retained_dropins=deepcopy(self.old_unit['dropinPins']);self.retained_names=list(self.old_unit['existingNames'])
        need(len({p['path'] for p in self.retained_dropins})==len(self.retained_dropins) and
            len(set(self.retained_names))==len(self.retained_names),'RUNTIME_DROPIN_SET')
        for p in self.retained_dropins:binding.pin(p)
        old_drop=binding.pin(self.old['dropinPin'])
        if old_drop not in self.retained_dropins:
            need(old_drop['path'] not in {p['path'] for p in self.retained_dropins} and
                PurePosixPath(old_drop['path']).name not in self.retained_names,'RUNTIME_OLD_DROPIN_CONFLICT')
            self.retained_dropins.append(deepcopy(old_drop));self.retained_names.append(PurePosixPath(old_drop['path']).name)
        self.continuation_dropin=deepcopy(continuation_dropin_pin)
        if continuation_dropin_pin is not None:
            failed=binding.pin(continuation_dropin_pin);failed_location=PurePosixPath(failed['path'])
            need(suffix=='58' and candidate['sourceCommit']=='b9caa00b7eeed2b915c8855a8313521e57d06f72' and
                str(failed_location.parent)==self.old_unit['directory'] and failed_location.name.endswith('.conf') and
                all(failed_location.name>name for name in self.retained_names),'RUNTIME_CONTINUATION_DROPIN')
        self.dropin=deepcopy(binding.pin(dropin_pin));location=PurePosixPath(self.dropin['path'])
        need(str(location.parent)==self.old_unit['directory'] and location.name.endswith('.conf') and
            location.name not in self.retained_names and all(location.name>name for name in self.retained_names) and
            (continuation_dropin_pin is None or location.name>PurePosixPath(continuation_dropin_pin['path']).name),
            'RUNTIME_NEW_DROPIN')
        self.dependencies=dict(Requires=[],After=[]);self.candidate=deepcopy(candidate)
        self._new_payload_count()
        self.original=SimpleNamespace(spec=deepcopy(current_spec))
        self.retained_row_environment={k:deepcopy(self.old[k]) for k in transition._BASELINE_ONLY if k in self.old}
        baseline=current_spec['environmentBaseline'];self.retained_environment=None
        if baseline is not None:
            matches=[r for r in baseline['controllers'] if r['service']==self.old['service']]
            need(len(matches)==1,'RUNTIME_ENVIRONMENT_BASELINE');self.retained_environment=deepcopy(matches[0])

    def spec(self,pid):
        result=deepcopy(self.original.spec);result['current']['controllers'][self.index]=self._row(pid)
        unit=next(u for u in result['unit']['controllers'] if u['service']==self.old['service'])
        unit['dropinPins']=deepcopy(self.retained_dropins);unit['existingNames']=list(self.retained_names)
        if self.continuation_dropin is not None:
            unit['dropinPins'].append(deepcopy(self.continuation_dropin))
            unit['existingNames'].append(PurePosixPath(self.continuation_dropin['path']).name)
        additions=[deepcopy(r['pin']) for r in self.candidate['newDocuments']]
        refs=result['retainedDocuments']+result['newDocuments']+additions
        for p in refs:binding.pin(p)
        need(len({p['path'] for p in refs})==len(refs),'RUNTIME_DOCUMENT_COLLISION')
        result['retainedDocuments'].extend(additions)
        return result

    def _compare(self,before,after,pid):
        projected=deepcopy(before)
        if self.continuation_dropin is not None:
            # This is an explicit derived comparison, never an amended before
            # record: only the pinned failed dropin is inserted in the allowed
            # predecessor sequence. Every other field is compared unchanged.
            projected['controllers'][self.index]['properties']['DropInPaths']+=' '+self.continuation_dropin['path']
        return super()._compare(projected,after,pid)


def build_target_successor_runtime_spec(*,current_spec,retained_history_spec,candidate,dropin_pin,successor_pid,
        continuation_dropin_pin=None):
    """Describe a successor process; the caller must independently read reality."""
    return _PureTransition(current_spec=current_spec,retained_history_spec=retained_history_spec,
        candidate=candidate,dropin_pin=dropin_pin,continuation_dropin_pin=continuation_dropin_pin).spec(successor_pid)


ACTIVATION_FIELDS={'schemaVersion','status','stage','host','role','targetConfigRef','sourceCommit','observedAt',
    'candidate','predecessorSelectionPin','predecessorActivationReceiptPin','retainedFailurePins','failurePinsBefore',
    'failurePinsAfter','currentRuntimeSpec','retainedHistoryRuntimeSpec','successorRuntimeSpec','before','after',
    'currentController','nativeBefore','nativeAfter','originalApi','apiSelection','dropinPin','createdPaths',
    'activationReceiptPin',*activated.TRUE_FLAGS,*activated.FALSE_FLAGS}
CONTINUATION_FIELDS={'continuationProfile','continuationFailurePin','continuationBeforePin','continuationDropinPin',
    'controlServiceRestartedInPriorAttempt','controlServiceRestartedDuringContinuation'}
CONTINUATION_LOCAL='continuationLocalEvidencePin'


def _decode_raw(value):
    need(type(value) is str and 0<len(value)<=512*1024,'CONTINUATION_RAW')
    try:return base64.b64decode(value,validate=True)
    except ValueError:raise ValueError('MAIN_TARGET_SUCCESSOR_CONTINUATION_BASE64') from None


def _dropin_argv(raw,control,engine,reference):
    text=raw.decode('utf-8');lines=text.splitlines();commands=[line[len('ExecStart='):] for line in lines if line.startswith('ExecStart=')]
    need(len(commands)==2 and commands[0]=='','CONTINUATION_EXECSTART_SHAPE')
    argv=shlex.split(commands[1],posix=True)
    need(len(argv)==6 and argv[:-1]==[control['pythonPin']['path'],'-B',engine+'/control_entry.py','serve','--config-pin'] and
        json.loads(argv[-1],object_pairs_hook=planner.document)==reference,'CONTINUATION_EXECSTART_PIN')


def verify_reader_continuation_evidence(*,result,context,staging_plan,control):
    """Validate only the two recorded reader-generation failures, without IO."""
    r=result;host=r['host'].rsplit('.',1)[-1]
    profile={'57':'TARGET57_AFTER_READBACK_ONLY/v1','58':'TARGET58_BAD_DROPIN_REPLACEMENT/v1'}
    need(host in profile and r['continuationProfile']==profile[host] and
        r['sourceCommit']=='b9caa00b7eeed2b915c8855a8313521e57d06f72' and
        r['controlServiceRestartedInPriorAttempt'] is True and
        r['controlServiceRestartedDuringContinuation'] is (host=='58'),'CONTINUATION_PROFILE')
    common={'schemaVersion','failureWrapperPin','failureWrapper','beforePin','before','prepareWrapperPin','prepareWrapper'}
    extra={'failedDropinPin','failedDropinRawBase64','correctDropinRawBase64','preContinuationObservation'} if host=='58' else {
        'dropinPin','dropinRawBase64'}
    schema='MainTarget58ReaderContinuationEvidence/v1' if host=='58' else 'MainTarget57ReaderReadbackEvidence/v1'
    need(type(context) is dict and set(context)==common|extra and context['schemaVersion']==schema,'CONTINUATION_CONTEXT')
    _private_input_pin(context['failureWrapperPin']);wrapper=context['failureWrapper']
    need(type(wrapper) is dict and set(wrapper)==activated.WRAPPER_FIELDS,'CONTINUATION_FAILED_WRAPPER')
    failure=activated._wrapper(wrapper,host,status='FAILED')
    failed_fields={'schemaVersion','status','host','role','targetConfigRef','sourceCommit','stage','errorType','errorCode',
        'observedAt','createdPaths','activationReceiptPin',*activated.FALSE_FLAGS}
    need(set(failure)==failed_fields and failure['schemaVersion']==r['schemaVersion'] and failure['status']=='FAILED' and
        failure['stage']=='new-runtime' and failure['errorType']==('ValueError' if host=='58' else 'AttributeError') and
        failure['errorCode']==('CONTROL_PROCESS_CHANGED' if host=='58' else "'_PureTransition' object has no attribute '_new_package_pin'") and
        all(failure[k]==r[k] for k in ('host','role','targetConfigRef','sourceCommit')) and
        all(failure[k] is False for k in activated.FALSE_FLAGS),'CONTINUATION_KNOWN_FAILURE')
    activated._timestamp(failure['observedAt']);activated._receipt(failure)
    beforepin=binding.pin(context['beforePin']);failed_drop=binding.pin(r['continuationDropinPin'])
    need(r['continuationFailurePin']==failure['activationReceiptPin'] and r['continuationBeforePin']==beforepin and
        context['before']==r['before'] and planner.remote_pin(beforepin['path'],context['before'])==beforepin and
        PurePosixPath(beforepin['path'])==PurePosixPath(failure['activationReceiptPin']['path']).parent/'before.private.json',
        'CONTINUATION_ORIGINAL_BEFORE')
    created=failure['createdPaths'];directory=str(PurePosixPath(failure['activationReceiptPin']['path']).parent)
    need(type(created) is list and len(set(created))==len(created) and
        set(created) in ({directory,beforepin['path'],failed_drop['path']},
            {directory,beforepin['path'],failed_drop['path'],failure['activationReceiptPin']['path']}),'CONTINUATION_FAILED_PATHS')
    _private_input_pin(context['prepareWrapperPin']);prepare_wrapper=context['prepareWrapper']
    need(set(prepare_wrapper)==activated.WRAPPER_FIELDS,'CONTINUATION_PREPARE_WRAPPER')
    prepare=activated._wrapper(prepare_wrapper,host,mode='PREPARE',status='SUCCESSOR_ACTIVATION_PREPARED')
    fields={'schemaVersion','status','host','role','targetConfigRef','sourceCommit','stage','observedAt','before','after','nativeBefore',
        'originalApi','proposedDropinPin','serverWrites','controlServiceRestarted','createdPaths',*activated.FALSE_FLAGS}
    need(set(prepare)==fields and prepare['status']=='SUCCESSOR_ACTIVATION_PREPARED' and prepare['stage']=='prepared' and
        all(prepare[k]==r[k] for k in ('schemaVersion','host','role','targetConfigRef','sourceCommit')) and
        all(prepare[k] is False for k in (*activated.FALSE_FLAGS,'serverWrites','controlServiceRestarted')) and
        prepare['createdPaths']==[] and prepare['before']==r['before'] and prepare['after']==r['before'] and
        prepare['originalApi']==r['originalApi'] and prepare['nativeBefore']==r['nativeBefore'] and
        prepare['proposedDropinPin']==failed_drop,'CONTINUATION_PREPARE_BINDING')
    activated._timestamp(prepare['observedAt'])
    if host=='57':
        need(r['dropinPin']==context['dropinPin']==failed_drop,'CONTINUATION_READBACK_DROPIN')
        raw=_decode_raw(context['dropinRawBase64'])
        need(_content_pin(failed_drop['path'],raw)==failed_drop,'CONTINUATION_DROPIN_BYTES')
        _dropin_argv(raw,control,r['candidate']['controller']['engine'],r['candidate']['controller']['controlPin'])
        return None
    badraw=_decode_raw(context['failedDropinRawBase64']);correctraw=_decode_raw(context['correctDropinRawBase64'])
    need(context['failedDropinPin']==failed_drop and _content_pin(failed_drop['path'],badraw)==failed_drop and
        _content_pin(r['dropinPin']['path'],correctraw)==r['dropinPin'],'CONTINUATION_DROPIN_BYTES')
    c=r['candidate'];correct=c['controller']['controlPin'];old=c['previousController']['controlConfigurationPin']
    wrong=dict(correct,bytes=old['bytes'],sha256=old['sha256'])
    _dropin_argv(badraw,control,c['controller']['engine'],wrong)
    _dropin_argv(correctraw,control,c['controller']['engine'],correct)
    token=planner.canonical(wrong);need(badraw.count(token)==1 and correctraw==badraw.replace(token,planner.canonical(correct)),
        'CONTINUATION_ONLY_CONFIG_PIN_CHANGED')
    pre=context['preContinuationObservation'];fields={'schemaVersion','status','serverWrites','physicalLockVerified',
        'protectedObservation','peerControllers','targetProperties','retainedPins','successorPins','failurePins','failedDropinPin'}
    need(type(pre) is dict and set(pre)==fields and pre['schemaVersion']=='MainTarget58ReaderContinuationPreflight/v1' and
        pre['status']=='PASS' and pre['serverWrites'] is False and pre['physicalLockVerified'] is True and
        pre['peerControllers']==[] and pre['protectedObservation']=={k:v for k,v in r['before'].items() if k!='controllers'} and
        pre['retainedPins']==staging_plan['retainedPins'] and pre['successorPins']==[row['pin'] for row in staging_plan['writes']] and
        pre['failurePins']==r['retainedFailurePins'] and pre['failedDropinPin']==failed_drop,'CONTINUATION_PREFLIGHT')
    props=pre['targetProperties'];activated.runtime.canonical_dependency_properties(props)
    need(props.get('MainPID')=='0' and props.get('ActiveState')=='inactive' and props.get('SubState')=='dead' and
        props.get('LimitNOFILE')=='65536' and props.get('DropInPaths','').split()==
        r['before']['controllers'][-1]['properties']['DropInPaths'].split()+[failed_drop['path']],'CONTINUATION_QUIESCENT_TARGET')
    return failed_drop


def _preservation_from_candidate(predecessor,host,candidate):
    old=predecessor['effectiveControllersByHost'][host][-1];ref=old['targetConfigRef'];owner=predecessor['targetOwners'][host]
    rows=deepcopy(candidate['retainedPreservationDocuments'])
    names={PurePosixPath(row['pin']['path']).name:row['pin'] for row in rows}
    need(set(names)==set(binding.DOCUMENT_SCHEMAS),'PREDECESSOR_PRESERVATION_SET')
    originals=[p for p in predecessor['targetRuntimeSpecs'][host]['original']['retainedDocuments']
        if PurePosixPath(p['path']).name in ('mount.credentials','nas-smb-v1.private.json')]
    need(len(originals)==1,'PREDECESSOR_ORIGINAL_CREDENTIAL')
    # Each retained graph row must be the already staged predecessor original,
    # rather than just a freshly hashed caller-provided document.
    registered=predecessor['targetRuntimeSpecs'][host]['successor']['retainedDocuments']
    need(all(row['pin'] in registered for row in rows),'PREDECESSOR_GRAPH_NOT_RETAINED')
    return dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',targetConfigRef=ref,
        captureRef=ref+'-pre-restore',capturePin=names['capture.json'],repositoryPin=names['repository.json'],
        policyPin=names['policy.json'],documents=rows,originalCredentialPins=[owner['targets'][ref]['secrets']['minio'][key]
        for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')]+deepcopy(originals))


def _verify_repeat_api(r,owner,old_owner,context,archive_owner_verification=None,*,predecessor_retry_native=None):
    """Keep unavailable predecessor HTTP evidence explicit; after stays strict."""
    state=r.get('beforeApiState');target=r['targetConfigRef'];old=r['candidate']['previousController']
    need(state in ('AVAILABLE','RETAINED_FAILURE_UNAVAILABLE'),'BEFORE_API_STATE')
    need(archive_owner_verification is None or state=='RETAINED_FAILURE_UNAVAILABLE' and
        r['candidate'].get('schemaVersion')=='MainProgramTargetControlSuccessorCandidate/v3','ARCHIVE_OWNER_EXPLICIT_V3_CONTEXT')
    retry=activated._native_evidence(r,owner,allow_retained_retry=
        r['candidate'].get('schemaVersion')=='MainProgramTargetControlSuccessorCandidate/v3')
    if predecessor_retry_native is not None:
        need(state=='AVAILABLE' and r['host']=='172.30.30.58' and
            r['candidate'].get('schemaVersion')=='MainProgramTargetControlSuccessorCandidate/v3' and
            r['candidate'].get('previousPackage',{}).get('fileCount')==154 and retry is not None and
            retry['sourceConfigRef']==activated.activation.SOURCES[0] and
            r['nativeBefore']==r['nativeAfter']==predecessor_retry_native,'PREDECESSOR_AVAILABLE_RETRY_NATIVE')
    need(retry is None or state=='RETAINED_FAILURE_UNAVAILABLE' or predecessor_retry_native is not None,
        'RETRY_RETAINED_FAILURE_REQUIRED')
    activated._api_selection(r['apiSelection'],target,admitted_source=None if retry is None else retry['sourceConfigRef'])
    if state=='AVAILABLE':
        need(r.get('retainedFailureAdmission') is None and context is None,'UNEXPECTED_FAILURE_ADMISSION')
        activated._api_selection(r['originalApi'],target,admitted_source=None if retry is None else retry['sourceConfigRef']);return
    old_error=r['originalApi']=={'errorCode':'RECOVERY_NO_MUTATION_NOT_PROVEN'}
    if not old_error:
        activated._api_selection(r['originalApi'],target,available=False)
        need([{k:v for k,v in app.items() if k!='freshTargetConfigRefs'} for app in r['originalApi']['applications']]==
            [{k:v for k,v in app.items() if k!='freshTargetConfigRefs'} for app in r['apiSelection']['applications']],
            'HTTP_SOURCE_POINT_CHANGED')
    admission=r.get('retainedFailureAdmission')
    need(type(admission) is dict and set(admission)=={'schemaVersion','originalsPacketPin',
        'predecessorApiObservationPin','clearanceResultPin'} and
        admission['schemaVersion']=='MainTargetRetainedFailureApiAdmission/v1','FAILURE_ADMISSION')
    for name in ('originalsPacketPin','predecessorApiObservationPin','clearanceResultPin'):_private_input_pin(admission[name])
    need(type(context) is dict and set(context)=={'originalsPacket','predecessorApiObservation','clearanceResult'},
        'FAILURE_ADMISSION_ORIGINALS_REQUIRED')
    packet=context['originalsPacket'];api=context['predecessorApiObservation'];clearance=context['clearanceResult']
    fields={'schemaVersion','status','serverWrites','observedAt','host','operationId','operationRoot','targetConfigRef','predecessorController','originals'}
    need(type(packet) is dict and set(packet)==fields and packet['schemaVersion']=='MainTargetRetainedFailureOriginals/v1' and
        packet['status']=='PASS' and packet['serverWrites'] is False and packet['host']==r['host'] and
        packet['targetConfigRef']==target and packet['predecessorController']==old,'FAILURE_ORIGINALS_BINDING')
    activated._timestamp(packet['observedAt']);operation=packet['operationId']
    need(type(operation) is str and re.fullmatch('smallapp-[0-9a-f]{32}',operation) is not None,'FAILURE_OPERATION')
    root=binding.path(packet['operationRoot'])
    need(root==binding.path(old_owner['operationsRoot'])/operation,'FAILURE_OPERATION_ROOT')
    originals=packet['originals'];need(type(originals) is dict and set(originals)=={'request','configuration','workerResult'},'FAILURE_ORIGINALS_SET')
    values={}
    for name,filename in (('request','request.json'),('configuration','configuration.json'),('workerResult','worker-result.json')):
        row=originals[name];need(type(row) is dict and set(row)=={'pin','rawBase64'},'FAILURE_ORIGINAL_SHAPE')
        reference=binding.pin(row['pin']);raw=_decode_raw(row['rawBase64'])
        need(reference['path']==str(root/filename) and reference==_content_pin(reference['path'],raw),'FAILURE_ORIGINAL_BYTES')
        values[name]=json.loads(raw.decode('utf-8'),object_pairs_hook=planner.document)
    request=values['request'];worker=values['workerResult']
    configuration_matches=values['configuration']==old_owner
    if archive_owner_verification is not None:
        from main_program_target_archive_owner_verification import verify_configuration_relation
        configuration_matches=verify_configuration_relation(r,old_owner,values['configuration'],request,archive_owner_verification)
    need(configuration_matches and type(request) is dict and set(request)=={'schemaVersion','operationId','action',
        'sourceConfigRef','parentChainRef','recoveryPointRef','targetConfigRef'} and request['schemaVersion']=='SmallAppBackupUiRequest/v1' and
        request['operationId']==operation and request['action']=='RESTORE' and request['sourceConfigRef'] in activated.activation.SOURCES and
        request['parentChainRef'] is None and request['targetConfigRef']==target and type(request['recoveryPointRef']) is str and
        re.fullmatch('smallapp-[0-9a-f]{32}',request['recoveryPointRef']) is not None,'FAILURE_REQUEST_CONFIGURATION')
    need(type(worker) is dict and worker.get('schemaVersion')=='backup-restore-operation-result/v1' and
        worker.get('operationId')==worker.get('requestId')==operation and worker.get('action')=='RESTORE' and
        worker.get('state')=='FAILED_RETAINED' and type(worker.get('actualExitCode')) is int and worker['actualExitCode']==1 and
        type(worker.get('data')) is dict and worker['data'].get('mutationDispatched') is False,'FAILURE_WORKER_RESULT')
    need(type(api) is dict and set(api)=={'observedAt','host','targetConfigRef','pid','controlConfigurationPin','httpStatus','api','serverWrites'} and
        api['host']==r['host'] and api['targetConfigRef']==target and api['pid']==old['pid'] and
        api['controlConfigurationPin']==old['controlConfigurationPin'] and api['httpStatus']==(500 if old_error else 200) and
        api['serverWrites'] is False and api['api']==r['originalApi'],'FAILURE_HTTP_ORIGINAL')
    activated._timestamp(api['observedAt'])
    need(type(clearance) is dict and set(clearance)=={'clearancePin','releasePin','originalState','restoreDispatched','nextRequestMustUseSamePoint'} and
        clearance['originalState']=='FAILED_RETAINED' and clearance['restoreDispatched'] is False and
        clearance['nextRequestMustUseSamePoint'] is True,'FAILURE_FORMAL_CLEARANCE')
    for name in ('clearancePin','releasePin'):binding.pin(clearance[name])
    need(clearance['clearancePin']['path']==str(binding.path(old_owner['targets'][target]['replacement']['stateRoot'])/operation/'recovery-clearance.json') and
        clearance['releasePin']['path']==str(root/'resource-recovery-release.json'),'FAILURE_CLEARANCE_OPERATION')
    if retry is not None:
        auth=retry['authorization']
        need(retry['predecessorOperationId']==operation and all(retry[k]==request[k] for k in
            ('sourceConfigRef','recoveryPointRef','targetConfigRef')) and
            all(auth[k]==originals[n]['pin'] for k,n in (('configurationPin','configuration'),('requestPin','request'),('resultPin','workerResult'))) and
            auth['clearancePin']==clearance['clearancePin'] and auth['recoveryReleasePin']==clearance['releasePin'],
            'RETRY_NATIVE_ORIGINALS_BINDING')


def _verify_target_successor_host(*,host,activation,predecessor,build,build_pin,package_raw,previous_package_raw,
        predecessor_selection_raw,predecessor_build_raw,continuations,build_raw,package_delta_review,
        package_delta_review_pin,package_delta_review_raw,retained_failure_admissions,archive_owner_verifications=None):
    need(host in HOSTS,'SUCCESSOR_HOST')
    repeated=any(v is not None for v in (build_raw,package_delta_review,package_delta_review_pin,package_delta_review_raw))
    planner.local_pin(build_pin);previous_build=json.loads(predecessor_build_raw.decode('utf-8'),object_pairs_hook=planner.document)
    count=_delta_payload_count(package_delta_review) if repeated else 153
    previous_count=_delta_previous_payload_count(package_delta_review) if repeated else 153
    package=_official_package(package_raw,build,payload_count=count)
    previous=_official_package(previous_package_raw,previous_build,payload_count=previous_count)
    wrapper=activation
    has_context=CONTINUATION_LOCAL in wrapper
    if has_context:
        ctx=continuations.get(host);need(type(ctx) is dict,'CONTINUATION_CONTEXT_REQUIRED')
        # The local wrapper pin is verified by the loader and its decoded
        # context is passed in this map; no context may be inferred.
    need(type(wrapper) is dict and set(wrapper)==activated.WRAPPER_FIELDS|({CONTINUATION_LOCAL} if has_context else set()),'SUCCESSOR_WRAPPER_FIELDS')
    r=activated._wrapper({k:v for k,v in wrapper.items() if k!=CONTINUATION_LOCAL},host)
    expected_fields=ACTIVATION_FIELDS|({'packageDeltaReviewPin','beforeApiState','retainedFailureAdmission'} if repeated else set())|(CONTINUATION_FIELDS if has_context else set())
    version='v3' if count==154 else ('v2' if repeated else 'v1')
    need(set(r)==expected_fields and r['schemaVersion']=='MainProgramTargetControlSuccessorActivation/'+version and
        r['status']=='PASS' and r['stage']=='complete' and r['role']=='target' and r['host']=='172.30.30.'+host and
        r['sourceCommit']==build['targetCommit'] and all(r[k] is True for k in activated.TRUE_FLAGS) and
        all(r[k] is False for k in activated.FALSE_FLAGS),'SUCCESSOR_RESULT_SCOPE')
    activated._timestamp(r['observedAt']);activated._receipt(r)
    need(r['predecessorSelectionPin']==predecessor['selectionPin'] and
        r['predecessorActivationReceiptPin']==predecessor['activationReceiptPins'][HOSTS.index(host)] and
        r['currentRuntimeSpec']==predecessor['targetRuntimeSpecs'][host]['successor'] and
        r['retainedHistoryRuntimeSpec']==predecessor['targetRuntimeSpecs'][host]['original'],'SUCCESSOR_PREDECESSOR_BINDING')
    c=r['candidate'];old=predecessor['effectiveControllersByHost'][host][-1]
    need(r['targetConfigRef']==old['targetConfigRef'] and c['previousController']==old,'SUCCESSOR_TARGET_BINDING')
    if repeated:
        need(not has_context and r['packageDeltaReviewPin']==package_delta_review_pin,'REPEAT_REVIEW_BINDING')
        graph=predecessor.get('currentPreservationDocumentsByHost',{}).get(host)
    else:graph=_preservation_from_candidate(predecessor,host,c)
    inputs=dict(predecessor=predecessor,predecessor_selection_pin=r['predecessorSelectionPin'],
        predecessor_selection_raw=predecessor_selection_raw,predecessor_build=previous_build,predecessor_build_raw=predecessor_build_raw,
        build=build,predecessor_package_raw=previous_package_raw,package_raw=package_raw,host=host,preservation_documents=graph,
        configuration_root=str(PurePosixPath(c['controller']['ownerPin']['path']).parent),new_engine=c['controller']['engine'],
        retained_failure_pins=r['retainedFailurePins'])
    if repeated:
        inputs.update(build_pin=build_pin,build_raw=build_raw,package_delta_review=package_delta_review,
            package_delta_review_pin=package_delta_review_pin,package_delta_review_raw=package_delta_review_raw)
    rebuilt=build_target_control_successor_candidate(**inputs)
    need(rebuilt==c,'SUCCESSOR_CANDIDATE_REBUILD')
    need(r['failurePinsBefore']==r['failurePinsAfter']==r['retainedFailurePins']==c['retainedFailurePins'] and
        (repeated or host=='58' or not r['retainedFailurePins']),'SUCCESSOR_FAILURE_ORIGINALS')
    owner=activated._document(c['newDocuments'],c['controller']['ownerPin'])
    control=activated._document(c['newDocuments'],c['controller']['controlPin'])
    continuation_dropin=None
    if has_context:
        _private_input_pin(wrapper[CONTINUATION_LOCAL])
        plan=build_target_successor_staging_plan(candidate=c,**inputs)
        continuation_dropin=verify_reader_continuation_evidence(result=r,context=continuations[host],staging_plan=plan,control=control)
    pure=_PureTransition(current_spec=r['currentRuntimeSpec'],retained_history_spec=r['retainedHistoryRuntimeSpec'],
        candidate=c,dropin_pin=r['dropinPin'],continuation_dropin_pin=continuation_dropin)
    pid=r['currentController'].get('pid');newspec=pure.spec(pid)
    need(newspec==r['successorRuntimeSpec'] and newspec['current']['controllers'][-1]==r['currentController'],
        'SUCCESSOR_RUNTIME_SPEC')
    projection=dict(r,transition=dict(schemaVersion='MainProgramTargetRuntimeTransition/v1',status='TARGET_SUCCESSOR_RUNTIME_VERIFIED',
        host=r['host'],targetConfigRef=r['targetConfigRef'],service=old['service'],successorController=r['currentController'],
        before=r['before'],after=r['after'],retainedEnvironmentBaseline=pure.retained_environment,
        retainedRowEnvironment=pure.retained_row_environment,retainedHistoryUsesOriginalSpec=True,serverWrites=False,
        installationReceiptCreated=False,restoreDispatched=False))
    for phase in ('before','after'):
        for observation in r[phase]['controllers']:
            if 'properties' in observation:
                activated.runtime.canonical_dependency_properties(observation['properties'])
    activated._observations(projection,pure,package,previous,predecessor['targetControls'][host],control)
    dependency='spug-main-preservation-view-'+host+'-20261111-r1.service'
    for phase in ('before','after'):
        props=r[phase]['controllers'][-1]['properties']
        need(all(dependency in props[key].split() for key in ('Requires','After')),'SUCCESSOR_PRESERVATION_DEPENDENCY')
    if repeated:
        previous_retry=None
        if package_delta_review.get('schemaVersion')=='MainProgramTargetControlPackageDeltaReview/v3':
            native=predecessor.get('currentRetainedRetryNativeByHost',{})
            need(type(native) is dict and set(native)<={'58'},'PREDECESSOR_AVAILABLE_RETRY_HOST')
            previous_retry=native.get(host)
        _verify_repeat_api(r,owner,predecessor['targetOwners'][host],retained_failure_admissions.get(host),
            None if archive_owner_verifications is None else archive_owner_verifications.get(host),predecessor_retry_native=previous_retry)
    else:activated._native_and_api(r,owner)
    receipt=PurePosixPath(r['activationReceiptPin']['path']);parent=PurePosixPath(old['engine']).parent
    need(receipt.name=='result-activate.private.json' and receipt.parent.parent==parent and
        re.fullmatch('control-activation-main-target-'+build['targetCommit'][:7]+r'-r[1-9][0-9]*',receipt.parent.name),
        'SUCCESSOR_RECEIPT_PATH')
    created={str(receipt.parent),str(receipt.parent/'before.private.json'),r['dropinPin']['path']}
    if has_context and host=='57':created.remove(r['dropinPin']['path'])
    need(type(r['createdPaths']) is list and len(set(r['createdPaths']))==len(r['createdPaths']) and
        set(r['createdPaths']) in (created,created|{str(receipt)}),'SUCCESSOR_CREATED_PATHS')
    return dict(controller=deepcopy(r['currentController']),owner=owner,control=control,
        runtime=dict(original=deepcopy(r['retainedHistoryRuntimeSpec']),successor=newspec),
        activationReceiptPin=deepcopy(r['activationReceiptPin']))


def verify_target_successor_activations(*,predecessor,activations,build,build_pin,package_raw,previous_package_raw,
        predecessor_selection_raw,predecessor_build_raw,continuations=None,build_raw=None,
        package_delta_review=None,package_delta_review_pin=None,package_delta_review_raw=None,retained_failure_admissions=None):
    """Validate three original carrier results; never call a remote boundary."""
    need(type(activations) is dict and set(activations)==set(HOSTS),'THREE_SUCCESSOR_ACTIVATIONS_REQUIRED')
    continuations={} if continuations is None else continuations
    need(type(continuations) is dict and set(continuations)<={'57','58'},'CONTINUATION_HOST_SET')
    repeated=any(v is not None for v in (build_raw,package_delta_review,package_delta_review_pin,package_delta_review_raw))
    if repeated:need(not continuations,'REPEAT_CONTINUATION_NOT_SUPPORTED')
    retained_failure_admissions={} if retained_failure_admissions is None else retained_failure_admissions
    need(type(retained_failure_admissions) is dict and set(retained_failure_admissions)<=set(HOSTS) and
        (repeated or not retained_failure_admissions),'FAILURE_ADMISSION_HOSTS')
    planner.local_pin(build_pin);previous_build=json.loads(predecessor_build_raw.decode('utf-8'),object_pairs_hook=planner.document)
    count=_delta_payload_count(package_delta_review) if repeated else 153
    previous_count=_delta_previous_payload_count(package_delta_review) if repeated else 153
    package=_official_package(package_raw,build,payload_count=count)
    previous=_official_package(previous_package_raw,previous_build,payload_count=previous_count)
    rows=deepcopy(predecessor['effectiveControllersByHost']);bindings=deepcopy(predecessor['controllerBuildBindings'])
    owners={};controls={};specs={};receipts=[]
    for host in HOSTS:
        result=_verify_target_successor_host(host=host,activation=activations[host],predecessor=predecessor,
            build=build,build_pin=build_pin,package_raw=package_raw,previous_package_raw=previous_package_raw,
            predecessor_selection_raw=predecessor_selection_raw,predecessor_build_raw=predecessor_build_raw,
            continuations=continuations,build_raw=build_raw,package_delta_review=package_delta_review,
            package_delta_review_pin=package_delta_review_pin,package_delta_review_raw=package_delta_review_raw,
            retained_failure_admissions=retained_failure_admissions)
        rows[host][-1]=result['controller'];bindings[host]['target']=dict(buildPin=deepcopy(build_pin),sourceCommit=build['targetCommit'])
        owners[host]=result['owner'];controls[host]=result['control'];specs[host]=result['runtime']
        receipts.append(result['activationReceiptPin'])
    return dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,predecessorInstallation=deepcopy(predecessor),
        sourceInstallation=deepcopy(predecessor['sourceInstallation']),baseInstallation=deepcopy(predecessor['baseInstallation']),
        effectiveControllersByHost=rows,controllerBuildBindings=bindings,targetOwners=owners,targetControls=controls,
        targetRuntimeSpecs=specs,activationReceiptPins=receipts,inputPins=[])


def verify_partial_target_predecessor(*,predecessor,activations,build,build_pin,package_raw,previous_package_raw,
        predecessor_selection_raw,predecessor_build_raw,build_raw,package_delta_review,
        package_delta_review_pin,package_delta_review_raw,retained_failure_admissions=None):
    """Verify the actual 57 receipt only; never manufacture other host proofs."""
    need(type(activations) is dict and set(activations)=={'57'},'PARTIAL_ACTIVATION_HOSTS')
    need(predecessor.get('status')=='ACTIVATED' and predecessor.get('installationVerified') is True and
        predecessor.get('runtimeVerified') is False,'FORMAL_PREDECESSOR_REQUIRED')
    admissions={} if retained_failure_admissions is None else retained_failure_admissions
    need(type(admissions) is dict and set(admissions)<={'57'},'FAILURE_ADMISSION_HOSTS')
    host='57';checked=_verify_target_successor_host(host=host,activation=activations[host],predecessor=predecessor,
        build=build,build_pin=build_pin,package_raw=package_raw,previous_package_raw=previous_package_raw,
        predecessor_selection_raw=predecessor_selection_raw,predecessor_build_raw=predecessor_build_raw,
        continuations={},build_raw=build_raw,package_delta_review=package_delta_review,
        package_delta_review_pin=package_delta_review_pin,package_delta_review_raw=package_delta_review_raw,
        retained_failure_admissions=admissions)
    # The complete historical chain can be tens of MB. Preserve it once and
    # copy only the host maps that this explicit overlay changes.
    result=dict(predecessor)
    for key in ('effectiveControllersByHost','controllerBuildBindings','targetOwners','targetControls',
            'targetRuntimeSpecs','activationReceiptPins','currentPreservationDocumentsByHost','retainedFailurePinsByHost'):
        result[key]=deepcopy(predecessor[key])
    result.update(status='PARTIALLY_ACTIVATED',installationVerified=False,runtimeVerified=False,
        activationVerifiedHosts=['57'],retainedBaseHosts=['58','59'],predecessorInstallation=predecessor)
    result['effectiveControllersByHost'][host][-1]=checked['controller']
    result['controllerBuildBindings'][host]['target']=dict(buildPin=deepcopy(build_pin),sourceCommit=build['targetCommit'])
    result['targetOwners'][host]=checked['owner'];result['targetControls'][host]=checked['control']
    result['targetRuntimeSpecs'][host]=checked['runtime'];result['activationReceiptPins'][0]=checked['activationReceiptPin']
    result['currentPreservationDocumentsByHost'][host]=_current_preservation_documents_for_host(result,activations[host],host)
    result['retainedFailurePinsByHost'][host]=deepcopy(activations[host]['result']['retainedFailurePins'])
    result['targetPredecessorArtifactsByHost']={h:dict(buildPin=deepcopy(predecessor['selection']['buildPin']),
        standardPackagePin=deepcopy(predecessor['selection']['standardPackagePin']),
        sourceCommit=predecessor['controllerBuildBindings'][h]['target']['sourceCommit']) for h in HOSTS}
    result['targetPredecessorArtifactsByHost'][host]=dict(buildPin=deepcopy(build_pin),
        standardPackagePin=deepcopy(package_delta_review['standardPackagePin']),sourceCommit=build['targetCommit'])
    result['inputPins']=[]
    return result


def load_activated_target_successor_installation(task,private,*,selection_file,historical_source_custody_pin=None):
    """Load pinned local originals over the complete original target selection."""
    publication=activated.publication
    modules=(planner,binding,staging,transition,activated,contract,activated.runtime,activated.source,publication)
    codepins=[publication.file_pin(Path(module.__file__).resolve()) for module in modules]
    codepins.append(publication.file_pin(Path(__file__).resolve()))
    records=contract.Records(task);selection=records.read(selection_file)
    need(set(selection)=={'schemaVersion','predecessorSelectionPin','buildPin','standardPackagePin','targetActivationEvidencePins'} and
        selection['schemaVersion']==SELECTION_SCHEMA,'SUCCESSOR_SELECTION')
    prior_reference=selection['predecessorSelectionPin'];records.pinned(prior_reference)
    args={} if historical_source_custody_pin is None else dict(historical_source_custody_pin=historical_source_custody_pin)
    predecessor=activated.load_activated_target_installation(task,private,selection_file=prior_reference['file'],**args)
    need(predecessor.get('selectionPin')==prior_reference,'SUCCESSOR_SELECTION_PREDECESSOR_PIN')
    previous_build_pin=predecessor['selection']['buildPin'];records.pinned(previous_build_pin)
    prior_raw=publication.verify_bytes(next(p for p in records.path_pins() if Path(p['path']).name==prior_reference['file']))
    previous_build_raw=publication.verify_bytes(next(p for p in records.path_pins() if Path(p['path']).name==previous_build_pin['file']))
    build=records.pinned(selection['buildPin']);pins=[]
    raw=activated._private_bytes(private,selection['standardPackagePin'],pins)
    previous_raw=activated._private_bytes(private,predecessor['selection']['standardPackagePin'],pins)
    evidence=selection['targetActivationEvidencePins']
    need(type(evidence) is dict and set(evidence)==set(HOSTS),'THREE_SUCCESSOR_EVIDENCE_PINS')
    activations={};continuations={}
    for host in HOSTS:
        wrapper=activated._private_json(private,evidence[host],pins);activations[host]=wrapper
        activated._private_bytes(private,wrapper['scriptPin'],pins)
        if CONTINUATION_LOCAL in wrapper:
            context=activated._private_json(private,wrapper[CONTINUATION_LOCAL],pins);continuations[host]=context
            for name in ('failure','prepare'):
                reference=context.get(name+'WrapperPin')
                if reference is not None:
                    original=activated._private_json(private,reference,pins)
                    need(original==context[name+'Wrapper'],'CONTINUATION_LOCAL_ORIGINAL')
                    activated._private_bytes(private,original['scriptPin'],pins)
    result=verify_target_successor_activations(predecessor=predecessor,activations=activations,build=build,
        build_pin=selection['buildPin'],package_raw=raw,previous_package_raw=previous_raw,
        predecessor_selection_raw=prior_raw,predecessor_build_raw=previous_build_raw,continuations=continuations)
    result.update(selection=deepcopy(selection),selectionPin=records.references[selection_file])
    result['inputPins']=activated.source.unique_pins(predecessor['inputPins']+records.path_pins()+pins+codepins)
    for reference in result['inputPins']:publication.verify_bytes(reference)
    return result


def _repeat_selection_chain(records,selection_file):
    """Bound ancestry before invoking a loader; never recursively trust a name."""
    chain=[];seen=set();name=selection_file;selection=records.read(name)
    while selection.get('schemaVersion')==REPEAT_SELECTION_SCHEMA:
        need(name not in seen,'SELECTION_CYCLE');seen.add(name)
        need(len(chain)<MAX_SUCCESSOR_DEPTH,'SELECTION_DEPTH')
        need(set(selection)=={'schemaVersion','predecessorSelectionPin','buildPin','standardPackagePin',
            'targetActivationEvidencePins','packageDeltaReviewPin'},'REPEAT_SELECTION')
        chain.append((name,selection));reference=planner.local_pin(selection['predecessorSelectionPin'])
        need(reference['file'] not in seen,'SELECTION_CYCLE')
        selection=records.pinned(reference);name=reference['file']
    need(selection.get('schemaVersion') in (activated.SCHEMA,SELECTION_SCHEMA,MIXED_SELECTION_SCHEMA),'PREDECESSOR_SELECTION')
    return name,list(reversed(chain))


def _bind_verified_current(result,wrappers):
    result['currentPreservationDocumentsByHost']=bind_current_preservation_documents(result,wrappers)
    result['retainedFailurePinsByHost']={host:deepcopy(wrappers[host]['result'].get('retainedFailurePins',
        [wrappers[host]['result']['continuationFailurePin']] if 'continuationFailurePin' in wrappers[host]['result'] else []))
        for host in HOSTS}
    result['currentRetainedRetryNativeByHost']={host:deepcopy(wrappers[host]['result']['nativeAfter'])
        for host in HOSTS if wrappers[host]['result'].get('nativeAfter',{}).get('retainedRetryAdmission') is not None}


def load_repeated_target_successor_installation(task,private,*,selection_file,historical_source_custody_pin=None):
    """Replay every pinned generation, preserving the historical v1 validators."""
    publication=activated.publication;records=contract.Records(task)
    _bounded_target_ancestry(records,selection_file)
    root,chain=_repeat_selection_chain(records,selection_file)
    need(bool(chain),'REPEAT_SELECTION_REQUIRED')
    args={} if historical_source_custody_pin is None else dict(historical_source_custody_pin=historical_source_custody_pin)
    root_selection=records.read(root)
    loader={activated.SCHEMA:activated.load_activated_target_installation,
        SELECTION_SCHEMA:load_activated_target_successor_installation,
        MIXED_SELECTION_SCHEMA:load_mixed_target_successor_installation}[root_selection['schemaVersion']]
    result=loader(task,private,selection_file=root,**args)
    need(result.get('selectionPin')==records.references[root],'SUCCESSOR_SELECTION_PREDECESSOR_PIN')
    pins=[];root_wrappers={}
    for host in HOSTS:
        reference=root_selection['targetActivationEvidencePins'][host]
        need(reference in result['inputPins'],'PREDECESSOR_WRAPPER_NOT_ADMITTED')
        root_wrappers[host]=activated._private_json(private,reference,pins)
    _bind_verified_current(result,root_wrappers)
    codepins=[publication.file_pin(Path(module.__file__).resolve()) for module in
        (planner,binding,staging,transition,activated,contract,activated.runtime,activated.source,publication)]
    codepins.append(publication.file_pin(Path(__file__).resolve()))
    for name,selection in chain:
        prior_reference=selection['predecessorSelectionPin']
        need(result['selectionPin']==prior_reference,'SUCCESSOR_SELECTION_PREDECESSOR_PIN')
        records.pinned(prior_reference)
        previous_build_pin=result['selection']['buildPin'];records.pinned(previous_build_pin)
        def raw_report(reference):
            records.pinned(reference)
            return publication.verify_bytes(dict(path=str(records.task/reference['file']),bytes=reference['bytes'],sha256=reference['sha256']))
        prior_raw=raw_report(prior_reference);previous_build_raw=raw_report(previous_build_pin)
        build=records.pinned(selection['buildPin']);build_raw=raw_report(selection['buildPin'])
        review=records.pinned(selection['packageDeltaReviewPin']);review_raw=raw_report(selection['packageDeltaReviewPin'])
        need(review.get('standardPackagePin')==selection['standardPackagePin'],'REPEAT_SELECTION_PACKAGE_BINDING')
        raw=activated._private_bytes(private,selection['standardPackagePin'],pins)
        previous_raw=activated._private_bytes(private,result['selection']['standardPackagePin'],pins)
        evidence=selection['targetActivationEvidencePins']
        need(type(evidence) is dict and set(evidence)==set(HOSTS),'THREE_SUCCESSOR_EVIDENCE_PINS')
        wrappers={};admissions={}
        for host in HOSTS:
            wrapper=activated._private_json(private,evidence[host],pins);wrappers[host]=wrapper
            activated._private_bytes(private,wrapper['scriptPin'],pins)
            admission=wrapper.get('result',{}).get('retainedFailureAdmission')
            if admission is not None:
                need(type(admission) is dict and set(admission)=={'schemaVersion','originalsPacketPin',
                    'predecessorApiObservationPin','clearanceResultPin'},'FAILURE_ADMISSION')
                admissions[host]={name:activated._private_json(private,admission[name+'Pin'],pins)
                    for name in ('originalsPacket','predecessorApiObservation','clearanceResult')}
        prior=result
        result=verify_target_successor_activations(predecessor=prior,activations=wrappers,build=build,
            build_pin=selection['buildPin'],build_raw=build_raw,package_raw=raw,previous_package_raw=previous_raw,
            predecessor_selection_raw=prior_raw,predecessor_build_raw=previous_build_raw,
            package_delta_review=review,package_delta_review_pin=selection['packageDeltaReviewPin'],package_delta_review_raw=review_raw,
            retained_failure_admissions=admissions)
        result.update(selection=deepcopy(selection),selectionPin=records.references[name])
        result['inputPins']=activated.source.unique_pins(prior['inputPins']+records.path_pins()+pins+codepins)
        _bind_verified_current(result,wrappers)
    for reference in result['inputPins']:publication.verify_bytes(reference)
    return result


def _bounded_target_ancestry(records,name):
    seen=set()
    for _ in range(MAX_SUCCESSOR_DEPTH+3):
        need(name not in seen,'SELECTION_CYCLE');seen.add(name);selection=records.read(name)
        schema=selection.get('schemaVersion')
        if schema==activated.SCHEMA:return
        key='baseSelectionPin' if schema==PARTIAL_SCHEMA else 'predecessorSelectionPin'
        need(schema in (SELECTION_SCHEMA,REPEAT_SELECTION_SCHEMA,MIXED_SELECTION_SCHEMA,PARTIAL_SCHEMA),'PREDECESSOR_SELECTION')
        reference=planner.local_pin(selection[key]);records.pinned(reference);name=reference['file']
    need(False,'SELECTION_DEPTH')


def _report_bytes(records,reference):
    records.pinned(reference)
    return activated.publication.verify_bytes(dict(path=str(records.task/reference['file']),bytes=reference['bytes'],sha256=reference['sha256']))


def _private_activations(private,evidence,pins):
    wrappers={};admissions={}
    for host,reference in evidence.items():
        wrapper=activated._private_json(private,reference,pins);wrappers[host]=wrapper
        activated._private_bytes(private,wrapper['scriptPin'],pins)
        admission=wrapper.get('result',{}).get('retainedFailureAdmission')
        if admission is not None:
            need(type(admission) is dict and set(admission)=={'schemaVersion','originalsPacketPin',
                'predecessorApiObservationPin','clearanceResultPin'},'FAILURE_ADMISSION')
            admissions[host]={key:activated._private_json(private,admission[key+'Pin'],pins)
                for key in ('originalsPacket','predecessorApiObservation','clearanceResult')}
    return wrappers,admissions


def load_partial_target_predecessor(task,private,*,selection_file,historical_source_custody_pin=None):
    """Load only the actual 57 PASS over its unchanged complete base chain."""
    import main_program_current_installation as current
    records=contract.Records(task);_bounded_target_ancestry(records,selection_file)
    selected=records.read(selection_file)
    need(set(selected)=={'schemaVersion','baseSelectionPin','buildPin','standardPackagePin','packageDeltaReviewPin','targetActivationEvidencePins'} and
        selected['schemaVersion']==PARTIAL_SCHEMA and type(selected['targetActivationEvidencePins']) is dict and
        set(selected['targetActivationEvidencePins'])=={'57'},'PARTIAL_SELECTION')
    base=selected['baseSelectionPin'];records.pinned(base)
    prior=current.load_current_target_installation(task,private,selection_file=base['file'],
        historical_source_custody_pin=historical_source_custody_pin)
    need(prior.get('selectionPin')==base,'PARTIAL_BASE_SELECTION_PIN')
    build=records.pinned(selected['buildPin']);review=records.pinned(selected['packageDeltaReviewPin']);pins=[]
    need(review.get('standardPackagePin')==selected['standardPackagePin'],'REPEAT_SELECTION_PACKAGE_BINDING')
    raw=activated._private_bytes(private,selected['standardPackagePin'],pins)
    previous_raw=activated._private_bytes(private,prior['selection']['standardPackagePin'],pins)
    wrappers,admissions=_private_activations(private,selected['targetActivationEvidencePins'],pins)
    result=verify_partial_target_predecessor(predecessor=prior,activations=wrappers,build=build,build_pin=selected['buildPin'],
        package_raw=raw,previous_package_raw=previous_raw,predecessor_selection_raw=_report_bytes(records,base),
        predecessor_build_raw=_report_bytes(records,prior['selection']['buildPin']),build_raw=_report_bytes(records,selected['buildPin']),
        package_delta_review=review,package_delta_review_pin=selected['packageDeltaReviewPin'],
        package_delta_review_raw=_report_bytes(records,selected['packageDeltaReviewPin']),retained_failure_admissions=admissions)
    result.update(selection=deepcopy(selected),selectionPin=records.references[selection_file])
    code=[activated.publication.file_pin(Path(__file__).resolve())]
    result['inputPins']=activated.source.unique_pins(prior['inputPins']+records.path_pins()+pins+code)
    for p in result['inputPins']:activated.publication.verify_bytes(p)
    return result


def load_mixed_target_successor_installation(task,private,*,selection_file,historical_source_custody_pin=None):
    """A complete three-host result must verify every actual mixed predecessor."""
    records=contract.Records(task);_bounded_target_ancestry(records,selection_file)
    selected=records.read(selection_file)
    base_fields={'schemaVersion','predecessorSelectionPin','buildPin','standardPackagePin','packageDeltaReviewPinsByHost','targetActivationEvidencePins'}
    need(set(selected) in (base_fields,base_fields|{'archiveOwnerVerificationPinsByHost'}) and selected['schemaVersion']==MIXED_SELECTION_SCHEMA,
        'MIXED_SELECTION')
    reference=selected['predecessorSelectionPin'];records.pinned(reference)
    prior=load_partial_target_predecessor(task,private,selection_file=reference['file'],historical_source_custody_pin=historical_source_custody_pin)
    need(prior['selectionPin']==reference,'PARTIAL_BASE_SELECTION_PIN')
    reviews=selected['packageDeltaReviewPinsByHost'];evidence=selected['targetActivationEvidencePins']
    need(type(reviews) is dict and set(reviews)==set(HOSTS) and type(evidence) is dict and set(evidence)==set(HOSTS),
        'THREE_SUCCESSOR_EVIDENCE_PINS')
    build=records.pinned(selected['buildPin']);build_raw=_report_bytes(records,selected['buildPin']);pins=[]
    package_raw=activated._private_bytes(private,selected['standardPackagePin'],pins)
    wrappers,admissions=_private_activations(private,evidence,pins)
    archive_owners={}
    if 'archiveOwnerVerificationPinsByHost' in selected:
        refs=selected['archiveOwnerVerificationPinsByHost']
        need(type(refs) is dict and set(refs)=={'58'},'ARCHIVE_OWNER_VERIFICATION_HOST')
        archive_owners['58']=activated._private_json(private,refs['58'],pins)
        from main_program_target_archive_owner_verification import verify_context
        checked=verify_context(archive_owners['58'],private=private)
        pins.extend(checked['inputPins'])
        import main_program_target_archive_owner_verification as archive_reader
        pins.append(activated.publication.file_pin(Path(archive_reader.__file__).resolve()))
    rows=deepcopy(prior['effectiveControllersByHost']);bindings=deepcopy(prior['controllerBuildBindings'])
    owners={};controls={};specs={};receipts=[]
    for host in HOSTS:
        artifact=_predecessor_artifacts(prior,host)
        previous_raw=activated._private_bytes(private,artifact['standardPackagePin'],pins)
        review=records.pinned(reviews[host])
        need(_delta_payload_count(review)==154,'MIXED_PACKAGE_GROWTH_PROFILE_REQUIRED')
        need(review.get('standardPackagePin')==selected['standardPackagePin'],'REPEAT_SELECTION_PACKAGE_BINDING')
        checked=_verify_target_successor_host(host=host,activation=wrappers[host],predecessor=prior,build=build,build_pin=selected['buildPin'],
            package_raw=package_raw,previous_package_raw=previous_raw,predecessor_selection_raw=_report_bytes(records,reference),
            predecessor_build_raw=_report_bytes(records,artifact['buildPin']),continuations={},build_raw=build_raw,
            package_delta_review=review,package_delta_review_pin=reviews[host],package_delta_review_raw=_report_bytes(records,reviews[host]),
            retained_failure_admissions=admissions,archive_owner_verifications=archive_owners)
        rows[host][-1]=checked['controller'];bindings[host]['target']=dict(buildPin=deepcopy(selected['buildPin']),sourceCommit=build['targetCommit'])
        owners[host]=checked['owner'];controls[host]=checked['control'];specs[host]=checked['runtime'];receipts.append(checked['activationReceiptPin'])
    result=dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,predecessorInstallation=prior,
        sourceInstallation=deepcopy(prior['sourceInstallation']),baseInstallation=deepcopy(prior['baseInstallation']),
        effectiveControllersByHost=rows,controllerBuildBindings=bindings,targetOwners=owners,targetControls=controls,
        targetRuntimeSpecs=specs,activationReceiptPins=receipts,selection=deepcopy(selected),selectionPin=records.references[selection_file])
    result['inputPins']=activated.source.unique_pins(prior['inputPins']+records.path_pins()+pins+
        [activated.publication.file_pin(Path(__file__).resolve())])
    _bind_verified_current(result,wrappers)
    for p in result['inputPins']:activated.publication.verify_bytes(p)
    return result
