"""Pure target-only control configuration binding; never installs or admits work.

Inputs are validated originals and both official member maps. Runtime capacity,
mount, process, source trust and restoration admission remain separate gates.
"""
import ast
from copy import deepcopy
from pathlib import PurePosixPath
import re

import main_program_control_upgrade_plan as planner


ADDED_MEMBERS=frozenset(('common/recovery_capture_materials.py','common/recovery_preservation_inputs.py',
    'common/recovery_preservation_source.py','common/recovery_restore_inputs.py',
    'common/recovery_target_capture.py','common/recovery_target_preservation.py'))
CHANGED_MEMBERS=frozenset(('common/recovery_main_target.py','common/recovery_minimal_runtime.py','common/recovery_minimal_worker.py',
    'common/recovery_mysql_scheduler.py','common/recovery_program_evidence.py','common/recovery_program_native.py',
    'common/recovery_program_protection.py','common/recovery_program_restore.py','common/recovery_replace.py',
    'common/repository_minimal.py','common/repository_native_readback.py','common/repository_retention.py',
    'control/recovery_control_restore_catalogue.py','control/recovery_control_smallapp.py',
    'control/recovery_control_smallapp_native.py','control/recovery_control_target_availability.py',
    'formal/formal_capture_semantics.py','formal/formal_data_evidence.py','formal/formal_schema_evidence.py',
    'formal/formal_snapshot_linux.py','formal/minimal_capture_support.py','formal/minimal_capture_worker.py',
    'formal/minimal_redis_snapshot.py'))
DISK_POLICY_CHANGED_MEMBERS=frozenset(('common/recovery_resource_admission.py','common/recovery_program_resources.py'))
DOCUMENT_SCHEMAS={
    'source-identity.json':None,'source-scope.json':'RecoverySourceScope/v1',
    'versions.json':'MainTargetCaptureVersion/v1','reference-recipe.json':'backup-capture-reference-recipe/v1',
    'redis-policy.json':'MainTargetDerivedCapturePolicy/v1','queue-policy.json':'MainTargetDerivedCapturePolicy/v1',
    'derived-recipe.json':'backup-capture-derived-recipe/v1',
    'object-credential.private.json':'backup-source-s3-credential/v1','objects.json':'backup-capture-object-source/v1',
    'capture.json':'MainTargetCaptureConfiguration/v1','smb-credential.private.json':'RepositorySmbCredential/v1',
    'readback-template.json':'MainTargetPreservationReadbackTemplate/v1',
    'repository.json':'MainTargetPreservationRepository/v2','policy.json':'MainTargetPreservationPolicy/v2'}


def need(condition,code):
    if not condition:raise ValueError('MAIN_TARGET_CANDIDATE_'+code)


def path(value):
    need(type(value) is str and value.startswith('/') and not value.startswith('//') and value!='/' and
        '\\' not in value and not any(ord(c)<32 for c in value) and
        str(PurePosixPath(value))==value and '..' not in PurePosixPath(value).parts,'PATH_INVALID')
    return PurePosixPath(value)


def pin(value):
    need(type(value) is dict and set(value)=={'path','bytes','sha256'} and
        type(value['bytes']) is int and value['bytes']>0 and type(value['sha256']) is str and
        re.fullmatch('[0-9a-f]{64}',value['sha256']) is not None,'PIN_INVALID')
    path(value['path']);return value


def packages(files,previous,old_build,new_build,core,*,disk_policy_bound=False):
    commit=new_build.get('targetCommit');old_commit=old_build.get('targetCommit')
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}',commit) is not None and
        type(old_commit) is str and re.fullmatch('[0-9a-f]{40}',old_commit) is not None and
        commit[:7]!=old_commit[:7] and core.get('sourceCommit')==old_commit,'BUILD_COMMIT_CHANGED')
    planner.manifest(previous,old_build,old_commit)
    for name,raw in previous.items():
        need('\\' not in name and not any(ord(c)<32 for c in name),'PACKAGE_MEMBER_INVALID')
        if name.endswith('.py'):
            try:compile(raw,name,'exec',dont_inherit=True)
            except (SyntaxError,UnicodeError,ValueError):
                raise ValueError('MAIN_TARGET_CANDIDATE_PREVIOUS_PACKAGE_COMPILE_FAILED') from None
    need(all(core.get(k)==old_build.get(k) for k in ('fileCount','fileManifestSha256','packageSha256')) and
        type(core.get('packageSha256')) is str and re.fullmatch('[0-9a-f]{64}',core['packageSha256']) is not None,
        'PREVIOUS_BUILD_CHANGED')
    need(new_build.get('status')=='PASS' and new_build.get('allFilesShaAndCompileVerified') is True and
        new_build.get('exactCommittedInput') is True and new_build.get('newCommits') is False and
        new_build.get('mergeRequired') is False,'OFFICIAL_BUILD_REQUIRED')
    rows=new_build.get('packages')
    need(type(rows) is list and len(rows)==2 and all(type(r) is dict for r in rows) and
        {r.get('variant') for r in rows}=={'standard','lightweight'},'BUILD_VARIANTS_INVALID')
    standard=next(r for r in rows if r['variant']=='standard')
    need(type(files) is dict and len(files)==153 and standard.get('fileCount')==153 and
        type(standard.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}',standard['sha256']) is not None,
        'STANDARD_BUILD_INVALID')
    hashes={}
    for name,raw in files.items():
        need(type(name) is str and name and '\\' not in name and not any(ord(c)<32 for c in name),
            'PACKAGE_MEMBER_INVALID')
        member=PurePosixPath(name)
        need(not member.is_absolute() and str(member)==name and '..' not in member.parts and
            name!='package.json' and type(raw) is bytes and bool(raw),'PACKAGE_MEMBER_INVALID')
        hashes[name]=planner.digest(raw)
        if name.endswith('.py'):
            try:
                ast.parse(raw.decode('utf-8'),filename=name)
                compile(raw,name,'exec',dont_inherit=True)
            except (SyntaxError,UnicodeError,ValueError):
                raise ValueError('MAIN_TARGET_CANDIDATE_PACKAGE_COMPILE_FAILED') from None
    need(planner.digest(planner.canonical(hashes))==standard.get('fileManifestSha256'),'PACKAGE_MANIFEST_CHANGED')
    expected=CHANGED_MEMBERS | (DISK_POLICY_CHANGED_MEMBERS if disk_policy_bound else frozenset())
    need(set(files)-set(previous)==ADDED_MEMBERS and not set(previous)-set(files) and
        {name for name in previous if files[name]!=previous[name]}==expected,'UNREVIEWED_PACKAGE_DELTA')
    return commit,standard


def bind_disk_policy(original,mode):
    """Change only the explicitly selected admission mode, retaining all limits."""
    need(type(mode) is str and mode in ('RESERVE','OBSERVE_ONLY'),'DISK_ADMISSION_MODE_INVALID')
    fields={'schemaVersion','mysqlMemoryBytes','hostAvailableMemoryBytes','diskBytesByPath'}
    need(type(original) is dict and set(original)==fields and
        original['schemaVersion']=='RestoreResourceBudget/v1','DISK_BUDGET_INVALID')
    need(all(type(original[k]) is int and original[k]>0 for k in ('mysqlMemoryBytes','hostAvailableMemoryBytes')),
        'DISK_BUDGET_INVALID')
    disks=original['diskBytesByPath']
    need(type(disks) is dict and disks and all(type(p) is str and p.startswith('/') and
        str(PurePosixPath(p))==p and '..' not in PurePosixPath(p).parts and
        type(amount) is int and amount>=0 for p,amount in disks.items()) and sum(disks.values())>0,
        'DISK_BUDGET_INVALID')
    result=deepcopy(original)
    result.update(schemaVersion='RestoreResourceBudget/v2',diskAdmissionMode=mode)
    return result


def preservation_graph(value,root,target_ref,target,program,new_engine,files):
    need(type(value) is dict and value.get('schemaVersion')=='MainTargetPreservationDocuments/v1' and
        value.get('status')=='BOUND_NOT_INSTALLED' and value.get('targetConfigRef')==target_ref,
        'PRESERVATION_IDENTITY_CHANGED')
    rows=value.get('documents');directory=root/'preservation'
    need(type(rows) is list and len(rows)==14,'PRESERVATION_DOCUMENT_COUNT_CHANGED')
    by_path={};by_name={}
    for row in rows:
        need(type(row) is dict and set(row)=={'pin','value'} and type(row['value']) is dict,'PRESERVATION_DOCUMENT_INVALID')
        reference=pin(row['pin']);location=path(reference['path']);name=location.name
        need(location.parent==directory and name in DOCUMENT_SCHEMAS and reference['path'] not in by_path and
            reference==planner.remote_pin(reference['path'],row['value']),'PRESERVATION_DOCUMENT_CHANGED')
        expected=DOCUMENT_SCHEMAS[name]
        need(row['value'].get('schemaVersion')==expected,'PRESERVATION_SCHEMA_CHANGED')
        by_path[reference['path']]=row;by_name[name]=row
    need(set(by_name)==set(DOCUMENT_SCHEMAS),'PRESERVATION_DOCUMENT_SET_CHANGED')
    def reference(name):return by_name[name]['pin']
    def doc(name):return by_name[name]['value']
    capture_ref=target_ref+'-pre-restore'
    need(value.get('captureRef')==capture_ref and
        all(value.get(key)==reference(name) for key,name in
            (('capturePin','capture.json'),('repositoryPin','repository.json'),('policyPin','policy.json'))),
        'PRESERVATION_TOP_BINDING_CHANGED')
    epoch=program['backupEpochPolicy'];policy=doc('policy.json');capture=doc('capture.json');source=capture.get('source',{})
    need(policy.get('targetConfigRef')==target_ref and policy.get('captureRef')==capture_ref and
        policy.get('captureConfigurationPin')==reference('capture.json') and
        policy.get('repositoryConfigurationPin')==reference('repository.json') and
        policy.get('backupEpochPolicy')==epoch and epoch.get('schemaVersion')=='SourceBackupEpochPolicy/v1' and
        epoch.get('databaseUuid')==target['replacement']['databaseUuid'],'PRESERVATION_POLICY_CHANGED')
    need(capture.get('sourceConfigRef')==capture_ref and capture.get('outputRootPolicy')=='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE' and
        capture.get('sourceLockPath')==epoch['sourceLockPath'] and capture.get('parent') is None and
        source.get('sourceIdentity')==source.get('sourceFingerprint')==epoch['sourceIdentity'] and
        source.get('databaseUuid')==epoch['databaseUuid'] and source.get('database')==target['database'] and
        source.get('databaseLogMode') in ('GTID','FILE_POSITION'),'PRESERVATION_CAPTURE_SCOPE_CHANGED')
    services={s['role']:s for s in target['services']}
    need(len(services)==len(target['services'])==5 and set(services)=={'mysql','minio','redis','backend','frontend'},
        'TARGET_SERVICE_SCOPE_CHANGED')
    need(source.get('mysqlContainerId')==services['mysql']['id'] and source.get('minioContainerId')==services['minio']['id'] and
        source.get('writerContainerIds')==[services[r]['id'] for r in ('backend','frontend')] and
        source.get('applicationImageIds')==sorted({s['imageId'] for s in services.values()}) and
        source.get('passwordPin')==target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'] and
        capture.get('tools',{}).get('docker')==target['dockerPin']['path'],'PRESERVATION_PHYSICAL_SCOPE_CHANGED')
    mounts=[m for m in target['replacement']['services']['minio']['mounts'] if m['RW'] and m['Destination']=='/data']
    need(len(mounts)==1 and source.get('minioDataPath')==mounts[0]['Source'] and
        source.get('minioMountDestination')==mounts[0]['Destination'],'PRESERVATION_MINIO_SCOPE_CHANGED')
    redis=dict(containerId=services['redis']['id'],host=services['redis']['ip'],database=target['redisRebuild']['database'])
    if 'REDIS_PASSWORD' in target.get('secrets',{}).get('redis',{}):
        redis['passwordPin']=target['secrets']['redis']['REDIS_PASSWORD']
    need(source.get('redisSnapshot')==redis and source.get('configurationPins')==[
        dict(role='configuration-'+str(i).zfill(4),reference=p) for i,p in enumerate(target['mainApplication']['configurationPins'],1)],
        'PRESERVATION_REGISTERED_INPUT_CHANGED')
    need(source.get('objectSourcePin')==reference('objects.json') and source.get('materialPins')==[
        dict(purpose='source-identity',reference=reference('source-identity.json')),
        dict(purpose='versions',reference=reference('versions.json'))],'PRESERVATION_CAPTURE_BINDING_CHANGED')
    need(doc('source-identity.json')==dict(sourceFingerprint=epoch['sourceIdentity'],databaseUuid=epoch['databaseUuid']) and
        doc('source-scope.json').get('sourceIdentityPin')==reference('source-identity.json') and
        doc('versions.json').get('targetConfigRef')==target_ref and
        doc('versions.json').get('images')=={r:s['imageId'] for r,s in services.items()},'PRESERVATION_SOURCE_CHANGED')
    objects=doc('objects.json')
    need(objects.get('sourceIdentity')==epoch['sourceIdentity'] and objects.get('credentialReference')==reference('object-credential.private.json') and
        objects.get('sourceScopePin')==reference('source-scope.json') and objects.get('versionPins')==[reference('versions.json')] and
        objects.get('referenceRecipePin')==reference('reference-recipe.json') and objects.get('derivedRecipePin')==reference('derived-recipe.json') and
        objects.get('parentExportIndexPin') is None and objects.get('buckets')==target['buckets'] and
        objects.get('minioContainerId')==services['minio']['id'] and objects.get('endpoint')=='http://'+services['minio']['ip']+':9000' and
        objects.get('containerPort')==9000,'PRESERVATION_OBJECT_BINDING_CHANGED')
    need(doc('reference-recipe.json').get('sourceIdentity')==epoch['sourceIdentity'] and
        doc('reference-recipe.json').get('coverageScopePin')==reference('source-scope.json') and
        doc('derived-recipe.json').get('sourceIdentity')==epoch['sourceIdentity'] and
        set(doc('derived-recipe.json').get('classes',{}))=={'redis','queue'},'PRESERVATION_RECIPE_CHANGED')
    for role in ('redis','queue'):
        need(doc(role+'-policy.json').get('targetConfigRef')==target_ref and
            doc(role+'-policy.json').get('sourceIdentity')==epoch['sourceIdentity'] and
            doc('derived-recipe.json')['classes'][role].get('configurationReferences')==[reference(role+'-policy.json')],
            'PRESERVATION_DERIVED_BINDING_CHANGED')
    repository=doc('repository.json');readback=doc('readback-template.json')
    binder_name='formal/formal_capture_recovery_inputs.py'
    need(repository.get('sourceIdentityPin')==reference('source-identity.json') and
        repository.get('readbackTemplatePin')==reference('readback-template.json') and
        binder_name in files and repository.get('captureBinderPin')==dict(path=new_engine+'/'+binder_name,
        bytes=len(files[binder_name]),sha256=planner.digest(files[binder_name])),'PRESERVATION_REPOSITORY_BINDING_CHANGED')
    need(readback.get('credentialPin')==reference('smb-credential.private.json') and
        readback.get('repositoryRoot')==repository.get('repositoryRoot') and
        readback.get('recordRootPolicy')=='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION',
        'PRESERVATION_READBACK_BINDING_CHANGED')
    originals=value.get('originalCredentialPins')
    need(type(originals) is list and len(originals)==3 and originals[:2]==[
        target['secrets']['minio'][key] for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')],
        'PRESERVATION_ORIGINAL_CREDENTIAL_CHANGED')
    for original in originals:pin(original)
    # Every in-graph edge must carry the exact content pin. Reachability from the
    # policy proves the 14 document closure; external original inputs stay pinned.
    def edges(item):
        if type(item) is dict:
            if set(item)=={'path','bytes','sha256'}:
                pin(item)
                if path(item['path']).is_relative_to(root):
                    need(item['path'] in by_path and item==by_path[item['path']]['pin'],'PRESERVATION_EDGE_CHANGED')
                    yield item['path']
            else:
                for child in item.values():yield from edges(child)
        elif type(item) is list:
            for child in item:yield from edges(child)
    for row in rows:list(edges(row['value']))
    seen=set();pending=[reference('policy.json')['path']]
    while pending:
        location=pending.pop()
        if location in seen:continue
        seen.add(location);pending.extend(edges(by_path[location]['value']))
    need(seen==set(by_path),'PRESERVATION_CLOSURE_CHANGED')
    return deepcopy(rows)


def build_target_control_candidate(*,host,current_controller,owner,control,package_files,previous_package_files,
        old_build,new_build,preservation,configuration_root,new_engine,disk_admission_mode=None):
    """Return 14 preservation documents and two target configs, all uninstalled."""
    core=current_controller
    need(host in ('57','58','59') and type(core) is dict and core.get('schemaVersion')=='MainProgramControlActivation/v1' and
        core.get('status')=='PASS' and core.get('role')=='target' and core.get('host')=='172.30.30.'+host and
        type(core.get('service')) is str and re.fullmatch(r'[A-Za-z0-9_.@-]+\.service',core['service']) is not None,
        'CONTROLLER_SCOPE_CHANGED')
    need(type(owner) is dict and owner.get('schemaVersion')=='RecoveryMinimalConfiguration/v1' and
        type(control) is dict and control.get('schemaVersion')=='SmallAppExecutionServiceConfig/v2',
        'CONFIGURATION_SCHEMA_CHANGED')
    for value,key in ((owner,'ownerConfigurationPin'),(control,'controlConfigurationPin')):
        old_pin=pin(core[key]);need(old_pin==planner.remote_pin(old_pin['path'],value),'ORIGINAL_CONFIGURATION_CHANGED')
    if disk_admission_mode is not None:
        need(type(disk_admission_mode) is str and disk_admission_mode in ('RESERVE','OBSERVE_ONLY'),
            'DISK_ADMISSION_MODE_INVALID')
    commit,standard=packages(package_files,previous_package_files,old_build,new_build,core,
        disk_policy_bound=disk_admission_mode is not None)
    old_engine=str(path(core['engine']));parent=path(old_engine).parent;root=path(configuration_root)
    need(path(new_engine)==parent/('engine-main-program-'+commit[:7]) and
        path(old_engine).name=='engine-main-program-'+old_build['targetCommit'][:7], 'ENGINE_LOCATION_CHANGED')
    need(root.parent==parent/'configuration' and re.fullmatch('main-target-'+commit[:7]+r'-r[1-9][0-9]*',root.name) is not None,
        'CONFIGURATION_LOCATION_CHANGED')
    need(owner.get('formalModuleDirectory')==old_engine+'/formal','OWNER_FORMAL_MODULE_CHANGED')
    target_ref=core.get('targetConfigRef')
    need(type(target_ref) is str and target_ref and set(owner.get('targets',{}))=={target_ref} and
        target_ref in owner.get('targetProgramPolicies',{}),'OWNER_TARGET_SCOPE_CHANGED')
    program=owner['targetProgramPolicies'][target_ref]
    need(program.get('schemaVersion')=='RegisteredMainProgramPolicy/v1' and program.get('targetConfigRef')==target_ref,
        'OWNER_PROGRAM_POLICY_CHANGED')
    docs=preservation_graph(preservation,root,target_ref,owner['targets'][target_ref],program,new_engine,package_files)
    new_owner=deepcopy(owner);new_owner['formalModuleDirectory']=new_engine+'/formal'
    if disk_admission_mode is not None:
        budget=bind_disk_policy(owner['targets'][target_ref].get('resourceBudget'),disk_admission_mode)
        admission_policies=new_owner.setdefault('targetResourceAdmissionPolicies',{})
        need(type(admission_policies) is dict and set(admission_policies)<=set(owner['targets']) and
            (target_ref not in admission_policies or admission_policies[target_ref]==budget),'DISK_POLICY_CONFLICT')
        admission_policies[target_ref]=budget
    captures=new_owner['targetProgramPolicies'][target_ref].get('captureConfigurationPins')
    need(type(captures) is dict and (preservation['captureRef'] not in captures or
        captures[preservation['captureRef']]==preservation['capturePin']),'CAPTURE_REGISTRATION_CONFLICT')
    captures[preservation['captureRef']]=deepcopy(preservation['capturePin'])
    policies=new_owner.setdefault('targetPreservationPolicies',{})
    need(type(policies) is dict and (target_ref not in policies or policies[target_ref]==preservation['policyPin']),
        'PRESERVATION_REGISTRATION_CONFLICT')
    policies[target_ref]=deepcopy(preservation['policyPin'])
    owner_pin=planner.remote_pin(str(root/'main-recovery.json'),new_owner)
    new_control=deepcopy(control)
    need(type(control.get('programPins')) is dict and set(control['programPins'])=={'recovery','repository'},'PROGRAM_ROLES_CHANGED')
    new_control['programPins']={role:planner.program_pin(pin(p),old_engine,new_engine,package_files,previous_package_files)
        for role,p in control['programPins'].items()}
    need(all(p['path']==new_engine+'/'+role+'_entry.py' for role,p in new_control['programPins'].items()),'PROGRAM_ROLE_PATH_CHANGED')
    new_control['environment']['PYTHONPATH']=planner.python_path(control['environment']['PYTHONPATH'],old_engine,new_engine)
    restores=control.get('restoreConfigurations')
    need(type(restores) is dict and bool(restores),'RESTORE_BINDINGS_REQUIRED')
    for source,targets in restores.items():
        need(type(source) is str and bool(source) and type(targets) is dict and set(targets)=={target_ref} and
            targets[target_ref]==core['ownerConfigurationPin'],'RESTORE_OWNER_BINDING_CHANGED')
    new_control['restoreConfigurations']=planner.replace_references(restores,
        {planner.canonical(core['ownerConfigurationPin']):owner_pin})
    control_pin=planner.remote_pin(str(root/'control-target.json'),new_control)
    docs.extend([dict(pin=owner_pin,value=new_owner),dict(pin=control_pin,value=new_control)])
    need(len({r['pin']['path'] for r in docs})==16 and not {core['ownerConfigurationPin']['path'],
        core['controlConfigurationPin']['path']} & {r['pin']['path'] for r in docs},'NEW_DOCUMENT_COLLISION')
    result=dict(schemaVersion='MainProgramTargetControlCandidate/v1',status='BOUND_NOT_INSTALLED',host=core['host'],
        targetConfigRef=target_ref,sourceCommit=commit,previousController=deepcopy(core),
        controller=dict(role='target',service=core['service'],engine=new_engine,previousControlPin=deepcopy(core['controlConfigurationPin']),
            previousOwnerPin=deepcopy(core['ownerConfigurationPin']),controlPin=control_pin,ownerPin=owner_pin),
        newDocuments=docs,package=dict(fileCount=153,fileManifestSha256=standard['fileManifestSha256'],packageSha256=standard['sha256']),
        retainedSourceConfigurationUnchanged=True,installationPerformed=False,restoreDispatched=False)
    if disk_admission_mode is not None:result['diskAdmissionMode']=disk_admission_mode
    return result
