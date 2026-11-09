"""Pure, explicit control-generation upgrade planning. Never reads or writes files.

The caller supplies a validated predecessor bundle and pinned report bytes plus
both actual standard package member maps. Returned values are candidates only;
staging, current-process observation and installation remain separate gates.
"""
import ast
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


HOSTS = ('57','58','59')
APPROVED_SEMANTIC_FILES = ('control/recovery_control_restore_catalogue.py',)
PRIVATE_FIELDS = {'archiveViewDependencies','bridgeSettings','build','controllers','currentSelections',
    'documentsByHost','entrySettings','newConnections','originalMetadata','originalSpug','registrations',
    'requiredBeforeActivation','schemaVersion','simpleSettings','sourceArchiveProtections','sourceCommit',
    'sourceProgramArchivePolicies','sourceRegistrationSelectors'}
V2_FIELDS = {'revisionId','predecessorGenerationPin','previousPlanPin','buildPin','packageDeltaPin',
    'newDocumentsByHost','retainedDocumentsByHost'}


def need(condition,code):
    if not condition: raise ValueError('MAIN_UPGRADE_'+code)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def document(items):
    value = {}
    for key,item in items:
        need(key not in value,'DUPLICATE_JSON_KEY');value[key] = item
    return value


def local_pin(pin):
    need(type(pin) is dict and set(pin) == {'file','bytes','sha256'} and type(pin['file']) is str and
         re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',pin['file']) is not None and '..' not in pin['file'] and
         type(pin['bytes']) is int and pin['bytes'] > 0 and type(pin['sha256']) is str and
         re.fullmatch('[0-9a-f]{64}',pin['sha256']) is not None,'LOCAL_PIN_INVALID')
    return pin


def remote_pin(path,value):
    parsed = PurePosixPath(path)
    need(type(path) is str and parsed.is_absolute() and str(parsed) == path and '..' not in parsed.parts,'REMOTE_PATH_INVALID')
    raw = canonical(value)
    return dict(path=path,bytes=len(raw),sha256=digest(raw))


def private_content_pin(path,value):
    need(type(path) is str and Path(path).is_absolute() and '..' not in Path(path).parts,'PRIVATE_PATH_INVALID')
    raw = canonical(value)
    return dict(path=path,bytes=len(raw),sha256=digest(raw))


def load_material(material,name):
    need(type(material) is dict and set(material) == {'pin','raw'} and type(material['raw']) is bytes,'REPORT_MATERIAL_INVALID')
    pin = local_pin(material['pin']);raw = material['raw']
    need(pin['file'] == name and pin['bytes'] == len(raw) and pin['sha256'] == digest(raw),'REPORT_PIN_CHANGED')
    value = json.loads(raw.decode('utf-8'),object_pairs_hook=document)
    need(type(value) is dict,'REPORT_DOCUMENT_REQUIRED')
    return value


def manifest(files,build,commit):
    need(type(files) is dict and len(files) == 147 and type(build) is dict and build.get('status') == 'PASS' and
         build.get('targetCommit') == commit and type(build.get('fileCount')) is int and build['fileCount'] == 147 and
         build.get('allFilesShaAndCompileVerified') is True,'PACKAGE_BUILD_REQUIRED')
    hashes = {}
    for name,raw in files.items():
        path = PurePosixPath(name)
        need(type(name) is str and not path.is_absolute() and str(path) == name and '..' not in path.parts and
             name != 'package.json' and type(raw) is bytes and bool(raw),'PACKAGE_MEMBER_INVALID')
        hashes[name] = digest(raw)
        if name.endswith('.py'): ast.parse(raw.decode('utf-8'),filename=name)
    need(digest(canonical(hashes)) == build['fileManifestSha256'],'PACKAGE_MANIFEST_CHANGED')
    return hashes


def validate_delta(delta,build,build_pin,old_build,old_build_pin,files,previous_files,commit,previous_commit):
    need(delta.get('schemaVersion') == 'ArchiveCataloguePackageDelta/v2' and delta.get('status') == 'PASS' and
         delta.get('sourceCommit') == commit and delta.get('predecessorCommit') == previous_commit and
         delta.get('buildPin') == build_pin and delta.get('predecessorBuildPin') == old_build_pin and
         delta.get('worktreeClean') is True and delta.get('newCommitsInBuildWorktree') is False and
         delta.get('mergeRequired') is False,'PACKAGE_DELTA_IDENTITY_CHANGED')
    rows = delta.get('packages')
    need(type(rows) is list and len(rows) == 2 and {r.get('variant') for r in rows} == {'standard','lightweight'},'PACKAGE_DELTA_VARIANTS_CHANGED')
    row = next(r for r in rows if r['variant'] == 'standard');previous = row['predecessor']
    need(all(row.get(k) == build[k] and previous.get(k) == old_build[k]
             for k in ('packageSha256','fileManifestSha256','fileCount')) and previous.get('variant') == 'standard' and
         row.get('allMembersShaAndCompileVerified') is True and row.get('candidateModuleAstMatchesTestedSource') is True,
         'PACKAGE_DELTA_BUILD_CHANGED')
    need(set(files) == set(previous_files),'PACKAGE_MEMBER_SET_CHANGED')
    changed = sorted(name for name in files if files[name] != previous_files[name])
    line_only = sorted(name for name in changed if files[name].replace(b'\r\n',b'\n') == previous_files[name].replace(b'\r\n',b'\n'))
    semantic = sorted(set(changed)-set(line_only))
    need(semantic == list(APPROVED_SEMANTIC_FILES) and row.get('changedFiles') == changed and
         row.get('lineEndingOnlyChangedFiles') == line_only and row.get('semanticChangedFiles') == semantic and
         row.get('byteIdenticalFileCount') == 147-len(changed) and row.get('programUnchangedFileCount') == 147-len(semantic),
         'UNREVIEWED_PACKAGE_DELTA')
    evidence = {name:dict(oldBytes=len(previous_files[name]),newBytes=len(files[name]),
        oldSha256=digest(previous_files[name]),newSha256=digest(files[name]),lineEndingOnly=name in line_only) for name in changed}
    need(row.get('changedFileEvidence') == evidence,'PACKAGE_DELTA_MEMBER_EVIDENCE_CHANGED')
    need(row.get('candidateModuleSha256') == digest(files[APPROVED_SEMANTIC_FILES[0]]),'PACKAGE_DELTA_MODULE_CHANGED')


def validate_predecessor(bundle):
    need(type(bundle) is dict and set(HOSTS) == set(bundle['controllersByHost']) == set(bundle['selections']) ==
         set(bundle['targets']),'PREDECESSOR_HOSTS_CHANGED')
    local_pin(bundle['generationPin']);generation = bundle['generation'];local_pin(generation['buildPin']);local_pin(generation['planPin'])
    old = bundle['privatePlan'];public = bundle['plan'];commit = generation['sourceCommit']
    need(type(commit) is str and re.fullmatch('[0-9a-f]{40}',commit) is not None and
         old['sourceCommit'] == public['sourceCommit'] == commit and old['build'] == bundle['build'] and
         old['status'] == public['status'] == 'PLAN_ONLY_NOT_ACTIVATED','PREDECESSOR_PLAN_CHANGED')
    schema = old['schemaVersion']
    need(schema in ('MainProgramConfigurationInstallationPlan/v1','MainProgramConfigurationInstallationPlan/v2') and
         set(old) == PRIVATE_FIELDS | ({'status'} if schema.endswith('/v1') else {'status',*V2_FIELDS}),
         'PREDECESSOR_PLAN_FIELDS_CHANGED')
    need(public['privatePlanPin'] == private_content_pin(public['privatePlanPin']['path'],old),'PREDECESSOR_PRIVATE_PIN_CHANGED')
    need(set(old['documentsByHost']) == set(old['controllers']) == set(HOSTS),'PREDECESSOR_DOCUMENT_HOSTS_CHANGED')
    indices = {}
    for host in HOSTS:
        docs = old['documentsByHost'][host]
        need(type(docs) is list and len(docs) == (13 if host == '57' else 11),'PREDECESSOR_DOCUMENT_COUNT_CHANGED')
        index = {}
        for row in docs:
            need(type(row) is dict and set(row) == {'pin','value'} and row['pin'] == remote_pin(row['pin']['path'],row['value']) and
                 row['pin']['path'] not in index,'PREDECESSOR_DOCUMENT_PIN_CHANGED')
            index[row['pin']['path']] = row
        indices[host] = index
        cores = bundle['controllersByHost'][host];selection = bundle['selections'][host]
        roles = ['source','target'] if host == '57' else ['target']
        need([r['role'] for r in cores] == [r['role'] for r in old['controllers'][host]] == roles and
             len(selection['controllers']) == len(cores) and selection['host'] == '172.30.30.'+host and
             selection['suffix'] == host and selection['sourceCommit'] == selection['currentSourceCommit'] == commit and
             selection['currentControlGenerationPin'] == bundle['generationPin'] and
             selection['targetConfigRef'] == bundle['targets'][host],'PREDECESSOR_SELECTION_CHANGED')
        for core,planned,current in zip(cores,old['controllers'][host],selection['controllers']):
            need(core['host'] == selection['host'] and core['sourceCommit'] == commit and
                 core['planPin'] == generation['planPin'] and core['buildPin'] == generation['buildPin'] and
                 all(core[k] == planned[k] for k in ('role','service','engine')) and
                 core['controlConfigurationPin'] == planned['controlPin'] and core['ownerConfigurationPin'] == planned['ownerPin'] and
                 all(core[k] == current[k] for k in ('role','service','engine','pid','controlConfigurationPin','ownerConfigurationPin','dropinPin')),
                 'PREDECESSOR_CONTROLLER_CHANGED')
            need(index[planned['controlPin']['path']]['pin'] == planned['controlPin'] and
                 index[planned['ownerPin']['path']]['pin'] == planned['ownerPin'],'PREDECESSOR_CONTROLLER_DOCUMENT_CHANGED')
        if schema.endswith('/v2'):
            need(old['documentsByHost'][host] == [*old['newDocumentsByHost'][host],*old['retainedDocumentsByHost'][host]] and
                 public['newDocumentsByHost'][host] == [r['pin'] for r in old['newDocumentsByHost'][host]] and
                 public['retainedDocumentsByHost'][host] == [r['pin'] for r in old['retainedDocumentsByHost'][host]],
                 'PREDECESSOR_GROUP_CLOSURE_CHANGED')
    return old,indices


def program_pin(old_pin,old_engine,new_engine,files,previous_files):
    path = PurePosixPath(old_pin['path']);root = PurePosixPath(old_engine)
    need(path.is_relative_to(root),'PROGRAM_OUTSIDE_ENGINE')
    name = str(path.relative_to(root))
    need(name in files and name in previous_files and old_pin == dict(path=str(path),bytes=len(previous_files[name]),
         sha256=digest(previous_files[name])),'PREVIOUS_PROGRAM_PIN_CHANGED')
    return dict(path=str(PurePosixPath(new_engine)/name),bytes=len(files[name]),sha256=digest(files[name]))


def repository_value(old,old_engine,new_engine,files,previous_files):
    value = deepcopy(old);seen = set()
    def rebind(path):
        need(type(path) is str,'REPOSITORY_PROGRAM_PATH_INVALID')
        candidate = PurePosixPath(path);root = PurePosixPath(old_engine)
        if candidate.is_relative_to(root):
            name = str(candidate.relative_to(root))
            need(name in files and name in previous_files,'REPOSITORY_MEMBER_UNKNOWN');seen.add(name)
            return str(PurePosixPath(new_engine)/name)
        need('/engine-main-program-' not in path,'REPOSITORY_FOREIGN_ENGINE')
        return path
    value['captureBinderPath'] = rebind(old['captureBinderPath'])
    for source in value['sources'].values():
        for key in ('captureCommand','toolPaths'):
            need(type(source[key]) is list,'REPOSITORY_TOOL_LIST_INVALID')
            source[key] = [rebind(path) for path in source[key]]
    need(seen == {'formal/formal_capture_recovery_inputs.py','formal/minimal_capture_entry.py'},'REPOSITORY_PROGRAM_SET_CHANGED')
    return value


def python_path(value,old_engine,new_engine):
    need(type(value) is str,'PYTHONPATH_INVALID');parts = value.split(':');seen = []
    for index,path in enumerate(parts):
        if path.startswith(old_engine+'/'):
            relative = path[len(old_engine)+1:]
            need(relative in ('control','common','formal'),'PYTHONPATH_ENGINE_MEMBER_UNKNOWN')
            seen.append(relative);parts[index] = new_engine+'/'+relative
        else: need('/engine-main-program-' not in path,'PYTHONPATH_FOREIGN_ENGINE')
    need(seen == ['control','common','formal'],'PYTHONPATH_ENGINE_SET_CHANGED')
    return ':'.join(parts)


def replace_references(value,replacements):
    if type(value) is dict:
        if set(value) == {'path','bytes','sha256'}:
            return deepcopy(replacements.get(canonical(value),value))
        return {key:replace_references(item,replacements) for key,item in value.items()}
    if type(value) is list:return [replace_references(item,replacements) for item in value]
    return deepcopy(value)


def rebind_connections(old,commit,revision):
    need(len(old['newConnections']) == 4 and len(old['bridgeSettings']['sourceConnections']) == 31,'CONNECTION_BASELINE_CHANGED')
    bridge = deepcopy(old['bridgeSettings']);mapping = {};connections = {}
    for host in HOSTS:
        targets = [bundle['targetConfigRef'] for suffix,bundle in old['currentSelections'].items() if suffix == host]
        need(len(targets) == 1,'CONNECTION_TARGET_CHANGED')
        name = bridge['targetConnections'][targets[0]]
        need(name in old['newConnections'] and name not in mapping,'CONNECTION_SCOPE_CHANGED')
        mapping[name] = 'intruoyi-main-'+host+'-program-'+commit[:7]+'-'+revision+'.private.json'
    directory = set(bridge['selectionConnections'].values())
    need(len(bridge['selectionConnections']) == 3 and len(directory) == 1,'DIRECTORY_SCOPE_CHANGED')
    name = next(iter(directory));need(name in old['newConnections'] and name not in mapping,'DIRECTORY_CONNECTION_CHANGED')
    mapping[name] = 'intruoyi-program-selections-'+commit[:7]+'-'+revision+'.private.json'
    protected = set(old['newConnections']) | set(old['originalSpug']['connections']) | set(bridge['sourceConnections'].values())
    need(not set(mapping.values()) & protected and len(set(mapping.values())) == 4,'CONNECTION_NAME_COLLISION')
    for old_name,new_name in mapping.items():connections[new_name] = deepcopy(old['newConnections'][old_name])
    for key in ('targetConnections','selectionConnections'):
        bridge[key] = {ref:mapping.get(name,name) for ref,name in bridge[key].items()}
    return bridge,connections


def plan_control_upgrade(*,source_commit,revision_id,build_document,package_delta_document,package_files,
                         previous_package_files,predecessor,private_plan_path,observed_at):
    """Return detached {privatePlan, plan}; no filesystem or remote side effects."""
    need(type(source_commit) is str and re.fullmatch('[0-9a-f]{40}',source_commit) is not None,'COMMIT_INVALID')
    need(type(revision_id) is str and re.fullmatch('r[1-9][0-9]*',revision_id) is not None,'REVISION_INVALID')
    output = Path(private_plan_path)
    need(output.is_absolute() and output.name == 'main-program-configuration-plan-'+source_commit[:7]+'-'+revision_id+'.private.json' and
         '..' not in output.parts,'OUTPUT_PATH_INVALID')
    need(type(observed_at) is str and datetime.fromisoformat(observed_at).utcoffset() is not None,'OBSERVATION_TIME_INVALID')
    old,indices = validate_predecessor(predecessor);previous_commit = predecessor['generation']['sourceCommit']
    need(source_commit != previous_commit and source_commit[:7] != previous_commit[:7],'SAME_GENERATION_FORBIDDEN')
    build = load_material(build_document,'release-build-'+source_commit[:7]+'.json')
    delta = load_material(package_delta_document,package_delta_document['pin']['file'])
    manifest(package_files,build,source_commit);manifest(previous_package_files,predecessor['build'],previous_commit)
    validate_delta(delta,build,build_document['pin'],predecessor['build'],predecessor['generation']['buildPin'],
        package_files,previous_package_files,source_commit,previous_commit)
    new = {host:[] for host in HOSTS};retained = {};controllers = {};refs = {}
    def add(host,path,value):
        row = dict(pin=remote_pin(path,value),value=deepcopy(value))
        need(path not in indices[host] and all(r['pin']['path'] != path for r in new[host]),'NEW_DOCUMENT_COLLISION')
        new[host].append(row);return row['pin']
    def locations(core):
        root = PurePosixPath(core['engine']).parent
        return str(root/('engine-main-program-'+source_commit[:7])),root/'configuration'/('main-program-'+source_commit[:7]+'-'+revision_id)
    source = predecessor['controllersByHost']['57'][0];source_engine,source_config = locations(source)
    source_owner = indices['57'][source['ownerConfigurationPin']['path']]['value']
    repository = repository_value(source_owner,source['engine'],source_engine,package_files,previous_package_files)
    repository_pin = add('57',str(source_config/'repository-source.json'),repository)
    refs[canonical(source['ownerConfigurationPin'])] = repository_pin
    for host in HOSTS:
        target = predecessor['controllersByHost'][host][-1];engine,config = locations(target)
        owner = deepcopy(indices[host][target['ownerConfigurationPin']['path']]['value'])
        need(owner['formalModuleDirectory'] == target['engine']+'/formal','OWNER_FORMAL_MODULE_CHANGED')
        owner['formalModuleDirectory'] = engine+'/formal'
        refs[canonical(target['ownerConfigurationPin'])] = add(host,str(config/'main-recovery.json'),owner)
    for host in HOSTS:
        controllers[host] = []
        consumed = set()
        for core in predecessor['controllersByHost'][host]:
            engine,config = locations(core);control = deepcopy(indices[host][core['controlConfigurationPin']['path']]['value'])
            need(set(control['programPins']) == {'recovery','repository'},'CONTROL_PROGRAM_ROLES_CHANGED')
            control['programPins'] = {role:program_pin(pin,core['engine'],engine,package_files,previous_package_files)
                for role,pin in control['programPins'].items()}
            need(all(p['path'] == engine+'/'+role+'_entry.py' for role,p in control['programPins'].items()),'CONTROL_PROGRAM_ROLE_PATH_CHANGED')
            control['environment']['PYTHONPATH'] = python_path(control['environment']['PYTHONPATH'],core['engine'],engine)
            for key in ('sourceConfigurations','restoreConfigurations'):control[key] = replace_references(control[key],refs)
            control_pin = add(host,str(config/('control-'+core['role']+'.json')),control)
            owner_pin = refs[canonical(core['ownerConfigurationPin'])]
            controllers[host].append(dict(role=core['role'],service=core['service'],engine=engine,
                previousControlPin=deepcopy(core['controlConfigurationPin']),previousOwnerPin=deepcopy(core['ownerConfigurationPin']),
                controlPin=control_pin,ownerPin=deepcopy(owner_pin)))
            consumed.update((core['controlConfigurationPin']['path'],core['ownerConfigurationPin']['path']))
        retained[host] = [deepcopy(row) for row in old['documentsByHost'][host] if row['pin']['path'] not in consumed]
        need(len(retained[host]) == 9,'RETAINED_DOCUMENT_COUNT_CHANGED')
    need(sum(map(len,new.values())) == 8 and sum(map(len,retained.values())) == 27,'DOCUMENT_PARTITION_CHANGED')
    value = deepcopy(old)
    value.update(schemaVersion='MainProgramConfigurationInstallationPlan/v2',sourceCommit=source_commit,revisionId=revision_id,
        predecessorGenerationPin=deepcopy(predecessor['generationPin']),previousPlanPin=deepcopy(predecessor['generation']['planPin']),
        buildPin=deepcopy(build_document['pin']),packageDeltaPin=deepcopy(package_delta_document['pin']),build=deepcopy(build),
        currentSelections=deepcopy(predecessor['selections']),controllers=controllers,newDocumentsByHost=new,retainedDocumentsByHost=retained,
        documentsByHost={host:[*new[host],*retained[host]] for host in HOSTS})
    value['bridgeSettings'],value['newConnections'] = rebind_connections(old,source_commit,revision_id)
    need(set(value) == PRIVATE_FIELDS | {'status',*V2_FIELDS},'CANDIDATE_PRIVATE_FIELDS_CHANGED')
    public = dict(schemaVersion='MainProgramConfigurationPlan/v2',status=value['status'],observedAt=observed_at,
        sourceCommit=source_commit,revisionId=revision_id,predecessorGenerationPin=deepcopy(predecessor['generationPin']),
        previousPlanPin=deepcopy(predecessor['generation']['planPin']),buildPin=deepcopy(build_document['pin']),
        packageDeltaPin=deepcopy(package_delta_document['pin']),hosts=list(HOSTS),
        controllers={host:[{key:row[key] for key in ('role','service','engine','controlPin','ownerPin')} for row in rows]
            for host,rows in controllers.items()},documents={host:len(rows) for host,rows in value['documentsByHost'].items()},
        newDocumentsByHost={host:[row['pin'] for row in rows] for host,rows in new.items()},
        retainedDocumentsByHost={host:[row['pin'] for row in rows] for host,rows in retained.items()},
        registrationCount=sum(map(len,value['registrations'].values()))+len(value['sourceRegistrationSelectors']),
        sourceRefs=deepcopy(predecessor['plan']['sourceRefs']),programTargets=[predecessor['targets'][host] for host in HOSTS],
        applicationCount=len(value['entrySettings']['applications']),originalTaskCount=len(value['entrySettings']['tasks']),
        privatePlanPin=private_content_pin(str(output),value),
        targetObjectsUnchanged=True,restoreDispatched=False,installationPerformed=False,
        sourceArchiveProtectionCount=sum(map(len,value['sourceArchiveProtections'].values())),
        archiveViewDependencies=deepcopy(value['archiveViewDependencies']),requiredBeforeActivation=deepcopy(value['requiredBeforeActivation']))
    return dict(privatePlan=value,plan=public)


def validate_control_upgrade_plan(public,private,**materials):
    """Validate loaded candidate values by exact reconstruction, without I/O.

    The caller explicitly supplies observed_at=public['observedAt'] and
    private_plan_path=public['privatePlanPin']['path'] in the verified materials.
    This does not infer a revision, locate a plan or treat it as an installation.
    """
    expected = plan_control_upgrade(**materials)
    need(private == expected['privatePlan'],'CANDIDATE_PRIVATE_CHANGED')
    need(public == expected['plan'],'CANDIDATE_PUBLIC_CHANGED')
    return expected
