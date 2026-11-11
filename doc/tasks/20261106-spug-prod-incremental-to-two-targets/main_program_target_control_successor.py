"""Explicit single-reader successor of the activated a3121c6 target generation.

Pure configuration and file plans do not establish installation or runtime health.
The original 147->153 contracts and their historical evidence remain unchanged.
"""
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
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


def need(condition,code):
    if not condition:raise ValueError('MAIN_TARGET_SUCCESSOR_'+code)


def _content_pin(location,raw):
    return dict(path=str(location),bytes=len(raw),sha256=planner.digest(raw))


def _official_package(raw,build):
    need(type(build) is dict and build.get('status')=='PASS' and build.get('exactCommittedInput') is True and
        build.get('allFilesShaAndCompileVerified') is True and build.get('newCommits') is False and
        build.get('mergeRequired') is False and type(build.get('targetCommit')) is str and
        re.fullmatch('[0-9a-f]{40}',build['targetCommit']) is not None,'OFFICIAL_BUILD_REQUIRED')
    return staging._target_package(raw,build)


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


def build_target_control_successor_candidate(*,predecessor,predecessor_selection_pin,predecessor_build,build,
        predecessor_selection_raw,predecessor_build_raw,predecessor_package_raw,package_raw,host,
        preservation_documents,configuration_root,new_engine,retained_failure_pins):
    """Bind exactly four successor documents; never read or mutate a filesystem."""
    core,old_build_pin=_predecessor(predecessor,predecessor_selection_pin,predecessor_selection_raw,
        predecessor_build,predecessor_build_raw,predecessor_package_raw,host)
    previous=_official_package(predecessor_package_raw,predecessor_build);package=_official_package(package_raw,build)
    files=package['payloadFiles'];old_files=previous['payloadFiles'];commit=build['targetCommit']
    need(commit[:7]!=PREDECESSOR_COMMIT[:7] and set(files)==set(old_files) and
        {name for name in files if files[name]!=old_files[name]}=={READER},'UNREVIEWED_PACKAGE_DELTA')
    need(core.get('fileManifestSha256')==previous['fileManifestSha256'],'PREDECESSOR_MANIFEST')
    old_engine=str(binding.path(core['engine']));parent=binding.path(old_engine).parent;root=binding.path(configuration_root)
    need(binding.path(new_engine)==parent/('engine-main-program-'+commit[:7]) and
        binding.path(old_engine).name=='engine-main-program-'+PREDECESSOR_COMMIT[:7],'ENGINE_LOCATION')
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
    retained=binding.preservation_graph(preservation_documents,old_root,ref,owner['targets'][ref],program,old_engine,old_files)
    need(owner.get('targetPreservationPolicies',{}).get(ref)==preservation_documents['policyPin'] and
        program.get('captureConfigurationPins',{}).get(preservation_documents['captureRef'])==preservation_documents['capturePin'],
        'CURRENT_PRESERVATION_BINDING')
    need(type(retained_failure_pins) is list,'FAILURE_PIN_SET')
    for p in retained_failure_pins:binding.pin(p)
    need(len({p['path'] for p in retained_failure_pins})==len(retained_failure_pins),'DUPLICATE_FAILURE_PIN')
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
    return dict(schemaVersion='MainProgramTargetControlSuccessorCandidate/v1',status='BOUND_NOT_INSTALLED',host=core['host'],
        targetConfigRef=ref,sourceCommit=commit,predecessorSelectionPin=deepcopy(predecessor_selection_pin),
        predecessorBuildPin=deepcopy(old_build_pin),previousController=deepcopy(core),
        controller=dict(role='target',service=core['service'],engine=new_engine,
            previousControlPin=deepcopy(core['controlConfigurationPin']),previousOwnerPin=deepcopy(core['ownerConfigurationPin']),
            controlPin=control_pin,ownerPin=owner_pin),newDocuments=docs,retainedPreservationDocuments=retained,
        package=dict(fileCount=153,fileManifestSha256=package['fileManifestSha256'],packageSha256=package['packageSha256']),
        previousPackage=dict(fileCount=153,fileManifestSha256=previous['fileManifestSha256'],packageSha256=previous['packageSha256']),
        retainedFailurePins=deepcopy(retained_failure_pins),retainedSourceConfigurationUnchanged=True,
        installationPerformed=False,restoreDispatched=False)


def build_target_successor_staging_plan(*,candidate,**inputs):
    """Return exclusive writes and original pins; the caller enforces IO gates."""
    rebuilt=build_target_control_successor_candidate(**inputs);need(candidate==rebuilt,'CANDIDATE_REBUILD')
    package=_official_package(inputs['package_raw'],inputs['build'])
    previous=_official_package(inputs['predecessor_package_raw'],inputs['predecessor_build'])
    writes=[dict(pin=_content_pin(binding.path(candidate['controller']['engine'])/name,raw),raw=raw,mode=0o400,exclusive=True)
        for name,raw in sorted(package['files'].items())]
    writes.extend(dict(pin=deepcopy(row['pin']),raw=planner.canonical(row['value']),mode=0o400,exclusive=True)
        for row in candidate['newDocuments'])
    retained=[_content_pin(binding.path(candidate['previousController']['engine'])/name,raw)
        for name,raw in sorted(previous['files'].items())]
    retained.extend(deepcopy(row['pin']) for row in candidate['retainedPreservationDocuments'])
    retained.extend(deepcopy(candidate['previousController'][key]) for key in ('ownerConfigurationPin','controlConfigurationPin'))
    locations={r['pin']['path'] for r in writes};originals={p['path'] for p in retained}
    need(len(writes)==len(locations)==158 and len(retained)==len(originals)==170 and not locations&originals,'PATH_COLLISION')
    return dict(schemaVersion='MainProgramTargetSuccessorStagingPlan/v1',status='PLANNED_NOT_STAGED',
        payloadFileCount=153,packageFileCount=154,documentCount=4,writes=writes,retainedPins=retained,
        installationPerformed=False,restoreDispatched=False,serverWrites=False)


class _PureTransition(transition.TargetControlRuntimeTransition):
    """Reuse only row/comparison semantics, without constructing a runtime gate."""
    def __init__(self,*,current_spec,retained_history_spec,candidate,dropin_pin):
        fields={'current','unit','environmentBaseline','targetConfigRef','previousCustody','oldReceiptPin',
            'originalInventory','historyPins','sourceEvidencePins','newDocuments','retainedDocuments'}
        need(type(current_spec) is dict and set(current_spec)==fields and
            type(retained_history_spec) is dict and set(retained_history_spec)==fields,'RUNTIME_SPEC_SHAPE')
        need(candidate.get('schemaVersion')=='MainProgramTargetControlSuccessorCandidate/v1' and
            candidate.get('status')=='BOUND_NOT_INSTALLED' and len(candidate.get('newDocuments',[]))==4 and
            candidate.get('installationPerformed') is False and candidate.get('restoreDispatched') is False,
            'RUNTIME_CANDIDATE')
        host=candidate['host'];suffix=host.rsplit('.',1)[-1];rows=current_spec['current']['controllers']
        need(suffix in HOSTS and current_spec['current']['host']==host and current_spec['current']['suffix']==suffix and
            [r['role'] for r in rows]==(['source','target'] if suffix=='57' else ['target']) and
            current_spec['targetConfigRef']==retained_history_spec['targetConfigRef']==candidate['targetConfigRef'],
            'RUNTIME_SCOPE')
        self.index=len(rows)-1;self.old=deepcopy(rows[self.index])
        need(self.old==candidate['previousController'] and self.old.get('fileCount')==153 and
            self.old.get('sourceCommit')==PREDECESSOR_COMMIT,'RUNTIME_CURRENT_BINDING')
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
        self.dropin=deepcopy(binding.pin(dropin_pin));location=PurePosixPath(self.dropin['path'])
        need(str(location.parent)==self.old_unit['directory'] and location.name.endswith('.conf') and
            location.name not in self.retained_names and all(location.name>name for name in self.retained_names),
            'RUNTIME_NEW_DROPIN')
        self.dependencies=dict(Requires=[],After=[]);self.candidate=deepcopy(candidate)
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
        additions=[deepcopy(r['pin']) for r in self.candidate['newDocuments']]
        refs=result['retainedDocuments']+result['newDocuments']+additions
        for p in refs:binding.pin(p)
        need(len({p['path'] for p in refs})==len(refs),'RUNTIME_DOCUMENT_COLLISION')
        result['retainedDocuments'].extend(additions)
        return result


def build_target_successor_runtime_spec(*,current_spec,retained_history_spec,candidate,dropin_pin,successor_pid):
    """Describe a successor process; the caller must independently read reality."""
    return _PureTransition(current_spec=current_spec,retained_history_spec=retained_history_spec,
        candidate=candidate,dropin_pin=dropin_pin).spec(successor_pid)


ACTIVATION_FIELDS={'schemaVersion','status','stage','host','role','targetConfigRef','sourceCommit','observedAt',
    'candidate','predecessorSelectionPin','predecessorActivationReceiptPin','retainedFailurePins','failurePinsBefore',
    'failurePinsAfter','currentRuntimeSpec','retainedHistoryRuntimeSpec','successorRuntimeSpec','before','after',
    'currentController','nativeBefore','nativeAfter','originalApi','apiSelection','dropinPin','createdPaths',
    'activationReceiptPin',*activated.TRUE_FLAGS,*activated.FALSE_FLAGS}


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


def verify_target_successor_activations(*,predecessor,activations,build,build_pin,package_raw,previous_package_raw,
        predecessor_selection_raw,predecessor_build_raw):
    """Validate three original carrier results; never call a remote boundary."""
    need(type(activations) is dict and set(activations)==set(HOSTS),'THREE_SUCCESSOR_ACTIVATIONS_REQUIRED')
    planner.local_pin(build_pin);previous_build=json.loads(predecessor_build_raw.decode('utf-8'),object_pairs_hook=planner.document)
    package=_official_package(package_raw,build);previous=_official_package(previous_package_raw,previous_build)
    rows=deepcopy(predecessor['effectiveControllersByHost']);bindings=deepcopy(predecessor['controllerBuildBindings'])
    owners={};controls={};specs={};receipts=[]
    for host in HOSTS:
        wrapper=activations[host]
        need(type(wrapper) is dict and set(wrapper)==activated.WRAPPER_FIELDS,'SUCCESSOR_WRAPPER_FIELDS')
        r=activated._wrapper(wrapper,host)
        need(set(r)==ACTIVATION_FIELDS and r['schemaVersion']=='MainProgramTargetControlSuccessorActivation/v1' and
            r['status']=='PASS' and r['stage']=='complete' and r['role']=='target' and r['host']=='172.30.30.'+host and
            r['sourceCommit']==build['targetCommit'] and all(r[k] is True for k in activated.TRUE_FLAGS) and
            all(r[k] is False for k in activated.FALSE_FLAGS),'SUCCESSOR_RESULT_SCOPE')
        activated._timestamp(r['observedAt']);activated._receipt(r)
        need(r['predecessorSelectionPin']==predecessor['selectionPin'] and
            r['predecessorActivationReceiptPin']==predecessor['activationReceiptPins'][HOSTS.index(host)] and
            r['currentRuntimeSpec']==predecessor['targetRuntimeSpecs'][host]['successor'] and
            r['retainedHistoryRuntimeSpec']==predecessor['targetRuntimeSpecs'][host]['original'],'SUCCESSOR_PREDECESSOR_BINDING')
        c=r['candidate'];old=rows[host][-1]
        need(r['targetConfigRef']==old['targetConfigRef'] and c['previousController']==old,'SUCCESSOR_TARGET_BINDING')
        graph=_preservation_from_candidate(predecessor,host,c)
        rebuilt=build_target_control_successor_candidate(predecessor=predecessor,predecessor_selection_pin=r['predecessorSelectionPin'],
            predecessor_selection_raw=predecessor_selection_raw,predecessor_build=previous_build,predecessor_build_raw=predecessor_build_raw,
            build=build,predecessor_package_raw=previous_package_raw,package_raw=package_raw,host=host,preservation_documents=graph,
            configuration_root=str(PurePosixPath(c['controller']['ownerPin']['path']).parent),new_engine=c['controller']['engine'],
            retained_failure_pins=r['retainedFailurePins'])
        need(rebuilt==c,'SUCCESSOR_CANDIDATE_REBUILD')
        need(r['failurePinsBefore']==r['failurePinsAfter']==r['retainedFailurePins']==c['retainedFailurePins'] and
            (host=='58' or not r['retainedFailurePins']),'SUCCESSOR_FAILURE_ORIGINALS')
        pure=_PureTransition(current_spec=r['currentRuntimeSpec'],retained_history_spec=r['retainedHistoryRuntimeSpec'],
            candidate=c,dropin_pin=r['dropinPin'])
        pid=r['currentController'].get('pid');newspec=pure.spec(pid)
        need(newspec==r['successorRuntimeSpec'] and newspec['current']['controllers'][-1]==r['currentController'],
            'SUCCESSOR_RUNTIME_SPEC')
        owner=activated._document(c['newDocuments'],c['controller']['ownerPin'])
        control=activated._document(c['newDocuments'],c['controller']['controlPin'])
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
        activated._native_and_api(r,owner)
        receipt=PurePosixPath(r['activationReceiptPin']['path']);parent=PurePosixPath(old['engine']).parent
        need(receipt.name=='result-activate.private.json' and receipt.parent.parent==parent and
            re.fullmatch('control-activation-main-target-'+build['targetCommit'][:7]+r'-r[1-9][0-9]*',receipt.parent.name),
            'SUCCESSOR_RECEIPT_PATH')
        created={str(receipt.parent),str(receipt.parent/'before.private.json'),r['dropinPin']['path']}
        need(type(r['createdPaths']) is list and len(set(r['createdPaths']))==len(r['createdPaths']) and
            set(r['createdPaths']) in (created,created|{str(receipt)}),'SUCCESSOR_CREATED_PATHS')
        rows[host][-1]=deepcopy(r['currentController']);bindings[host]['target']=dict(buildPin=deepcopy(build_pin),sourceCommit=build['targetCommit'])
        owners[host]=owner;controls[host]=control;specs[host]=dict(original=deepcopy(r['retainedHistoryRuntimeSpec']),successor=newspec)
        receipts.append(deepcopy(r['activationReceiptPin']))
    return dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,predecessorInstallation=deepcopy(predecessor),
        sourceInstallation=deepcopy(predecessor['sourceInstallation']),baseInstallation=deepcopy(predecessor['baseInstallation']),
        effectiveControllersByHost=rows,controllerBuildBindings=bindings,targetOwners=owners,targetControls=controls,
        targetRuntimeSpecs=specs,activationReceiptPins=receipts,inputPins=[])


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
    activations={}
    for host in HOSTS:
        wrapper=activated._private_json(private,evidence[host],pins);activations[host]=wrapper
        activated._private_bytes(private,wrapper['scriptPin'],pins)
    result=verify_target_successor_activations(predecessor=predecessor,activations=activations,build=build,
        build_pin=selection['buildPin'],package_raw=raw,previous_package_raw=previous_raw,
        predecessor_selection_raw=prior_raw,predecessor_build_raw=previous_build_raw)
    result.update(selection=deepcopy(selection),selectionPin=records.references[selection_file])
    result['inputPins']=activated.source.unique_pins(predecessor['inputPins']+records.path_pins()+pins+codepins)
    for reference in result['inputPins']:publication.verify_bytes(reference)
    return result
