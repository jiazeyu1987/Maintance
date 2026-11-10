"""Prepare an immutable control generation; explicitly stage without activation.

Default preparation is local and read-only. The explicit stage path holds the
original physical lock and checks shared runtime, history, epoch and factory
gates before and after exclusive writes; failed attempts are never retried.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import time
import urllib.request

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
HOSTS=('57','58','59')
SOURCES=('intruoyi-57-safe-20261024-v1','intruoyi-59-safe-20261024-v1','intruoyi-PROD57-20261019')
MAX_MEMBER_BYTES=16*1024*1024
MAX_PACKAGE_BYTES=128*1024*1024
RUNTIME_GATES=('current-controller-and-environment','no-active-worker','existing-physical-lock',
    'source-epoch-and-baseline','business-containers-nas-fstab','complete-history-and-layered-custody',
    'actual-staged-native-configuration','three-source-factory-protections','post-write-runtime-preservation')


def need(condition,reason):
    if not condition:raise ValueError('MAIN_STAGING_'+reason)


def transport_stderr_accepted(raw):
    return raw==b'' or re.fullmatch(
        rb'close - IO is still pending on closed socket\. read:1, write:0, io:[0-9A-Fa-f]{16}\r\n',raw) is not None


def exception_details(error):
    """Private diagnostics only; never project these into public CLI output."""
    import traceback
    return dict(type=type(error).__name__,module=type(error).__module__,message=str(error),
        traceback=''.join(traceback.format_exception(type(error),error,error.__traceback__,chain=True)))


def digest(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def document(items):
    result={}
    for key,value in items:
        need(key not in result,'DUPLICATE_JSON_KEY');result[key]=value
    return result


def verify_package(raw,build):
    """Verify the actual complete standard tar before any extraction or writes."""
    need(type(raw) is bytes and 0<len(raw)<=MAX_PACKAGE_BYTES and type(build) is dict and
        build.get('status')=='PASS' and re.fullmatch('[0-9a-f]{40}',build.get('targetCommit','')) and
        type(build.get('fileCount')) is int and build['fileCount']==147 and
        build.get('allFilesShaAndCompileVerified') is True and digest(raw)==build.get('packageSha256'),
        'PACKAGE_BUILD_CHANGED')
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members=archive.getmembers();names=[m.name for m in members]
        need(len(members)==148 and len(set(names))==148 and 'package.json' in names,'PACKAGE_MEMBER_CLOSURE')
        total=0
        for member in members:
            path=PurePosixPath(member.name)
            need(member.isfile() and not path.is_absolute() and str(path)==member.name and
                '..' not in path.parts and not any(c in member.name for c in ('\\',':','\x00')) and
                not any(ord(c)<32 for c in member.name) and 0<member.size<=MAX_MEMBER_BYTES,'PACKAGE_MEMBER_UNSAFE')
            total+=member.size
        need(total<=MAX_PACKAGE_BYTES,'PACKAGE_EXPANDED_LIMIT')
        files={member.name:archive.extractfile(member).read() for member in members}
    metadata=json.loads(files['package.json'].decode('utf-8'),object_pairs_hook=document)
    payload={name:content for name,content in files.items() if name!='package.json'}
    hashes={name:digest(content) for name,content in payload.items()}
    need(type(metadata) is dict and metadata.get('variant')=='standard' and
        metadata.get('fileVerification') is True and metadata.get('payloadContentVerification') is True and
        metadata.get('files')==hashes and digest(canonical(hashes))==metadata.get('packageSha256')==build['fileManifestSha256'],
        'PACKAGE_MANIFEST_CHANGED')
    for name,content in payload.items():
        if name.endswith('.py'):compile(content,name,'exec')
    return dict(files=files,payloadFiles=payload,packageSha256=digest(raw),fileManifestSha256=build['fileManifestSha256'])


def validate_inputs(inputs):
    import main_program_control_upgrade_plan as planner
    fields={'schemaVersion','sourceCommit','revisionId','suffix','previousControlGenerationPin',
        'buildPin','planPin','coveragePin','unitObservationPin','originalEnvironmentObservationPin'}
    need(type(inputs) is dict and set(inputs)==fields and
        inputs['schemaVersion']=='MainProgramControlStagingInputs/v1' and
        type(inputs['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',inputs['sourceCommit']) and
        type(inputs['revisionId']) is str and re.fullmatch('r[1-9][0-9]*',inputs['revisionId']) and
        inputs['suffix'] in HOSTS,'INPUTS_INVALID')
    for key in fields-{'schemaVersion','sourceCommit','revisionId','suffix'}:planner.local_pin(inputs[key])
    short=inputs['sourceCommit'][:7];revision=short+'-'+inputs['revisionId'];host=inputs['suffix']
    expected=dict(buildPin='release-build-'+short+'.json',planPin='main-program-configuration-plan-'+revision+'.json',
        unitObservationPin='main-program-control-units-'+host+'-'+revision+'.json',
        originalEnvironmentObservationPin='main-program-control-environment-baseline-'+host+'-'+revision+'.json')
    need(all(inputs[key]['file']==name for key,name in expected.items()),'INPUT_REVISION_CHANGED')
    return revision


def prepare_materials(*,inputs,predecessor,public,private,coverage,plan_document,build_document,
                      delta_document,package_raw,host_identity):
    """Bind explicit verified materials. Historical observations admit no write."""
    import main_program_control_generation as generation
    import main_program_control_upgrade_plan as planner
    import main_program_installation_selection as contract
    revision=validate_inputs(inputs);suffix=inputs['suffix'];commit=inputs['sourceCommit']
    need(inputs['previousControlGenerationPin']==predecessor['generationPin'] and
        inputs['buildPin']==build_document['pin'] and inputs['planPin']==plan_document['pin'],'MATERIAL_BINDING_CHANGED')
    need(planner.load_material(plan_document,inputs['planPin']['file'])==public,'PUBLIC_PLAN_BYTES_CHANGED')
    build=planner.load_material(build_document,inputs['buildPin']['file'])
    delta=planner.load_material(delta_document,public['packageDeltaPin']['file'])
    need(public['buildPin']==inputs['buildPin'] and public['packageDeltaPin']==delta_document['pin'] and
        public['predecessorGenerationPin']==inputs['previousControlGenerationPin'] and
        public['revisionId']==inputs['revisionId'] and coverage['build']==build and coverage['delta']==delta and
        coverage['coverage']['candidateBuildPin']==inputs['buildPin'] and
        coverage['coverage']['baselineBuildPin']==predecessor['generation']['buildPin'] and
        public['packageDeltaPin'] in coverage['coverage']['actualPackageEvidencePins'],'COVERAGE_BINDING_CHANGED')
    package=verify_package(package_raw,build)
    need(package['payloadFiles']==coverage['packageFiles'],'COVERED_PACKAGE_CHANGED')
    planner.validate_control_upgrade_plan(public,private,source_commit=commit,revision_id=inputs['revisionId'],
        build_document=build_document,package_delta_document=delta_document,
        package_files=package['payloadFiles'],previous_package_files=coverage['previousPackageFiles'],
        predecessor=predecessor,private_plan_path=public['privatePlanPin']['path'],observed_at=public['observedAt'])
    identity_fields={'host','previousControlGenerationPin','unitObservationPin','environmentObservationPin','controllers'}
    need(type(host_identity) is dict and set(host_identity)==identity_fields and
        host_identity['host']=='172.30.30.'+suffix and
        host_identity['previousControlGenerationPin']==inputs['previousControlGenerationPin'] and
        host_identity['unitObservationPin']==inputs['unitObservationPin'] and
        host_identity['environmentObservationPin']==inputs['originalEnvironmentObservationPin'],'HOST_IDENTITY_CHANGED')
    originals=predecessor['selections'][suffix]['controllers'];observed=host_identity['controllers']
    extra={'argvSha256','environmentSha256','systemdEnvironmentSha256','unitPin','dropinPins'}
    need(type(observed) is list and len(observed)==len(originals),'HOST_CONTROLLER_COUNT_CHANGED')
    for actual,original in zip(observed,originals):
        need(type(actual) is dict and set(actual)==set(generation.SELECTION_CONTROLLER_KEYS)|extra and
            {key:actual[key] for key in generation.SELECTION_CONTROLLER_KEYS}==original,'HOST_CONTROLLER_CHANGED')
        need(all(contract.sha(actual[key]) for key in ('argvSha256','environmentSha256','systemdEnvironmentSha256')),
            'HOST_OBSERVATION_HASH_INVALID')
        contract.remote_pin(actual['unitPin'])
        need(type(actual['dropinPins']) is list and original['dropinPin'] in actual['dropinPins'] and
            len({row['path'] for row in actual['dropinPins']})==len(actual['dropinPins']),'HOST_DROPINS_CHANGED')
        for reference in actual['dropinPins']:contract.remote_pin(reference)
    filesystem=dict(schemaVersion='MainProgramControlFilesystemStaging/v1',sourceCommit=commit,
        revisionId=inputs['revisionId'],host=host_identity['host'],suffix=suffix,build=build,
        engines=[dict(path=row['engine'],previousEngine=old['engine'])
            for row,old in zip(private['controllers'][suffix],originals)],
        newDocuments=private['newDocumentsByHost'][suffix],retainedDocuments=private['retainedDocumentsByHost'][suffix])
    return deepcopy(dict(schemaVersion='MainProgramControlStagingPreparation/v1',status='PREPARED_NOT_STAGED',
        remoteExecutable=False,inputs=inputs,filesystemSpec=filesystem,hostIdentity=host_identity,
        engineReportFile='main-program-engine-staged-'+suffix+'-'+revision+'.json',
        configurationReportFile='main-program-configuration-staged-'+suffix+'-'+revision+'.json',
        requiredRuntimeGates=list(RUNTIME_GATES)))


def read_covered_package(coverage):
    """Read the build artifact; evidence-runtime paths remain immutable."""
    from main_program_control_activation import file_pin
    delta,build=coverage['delta'],coverage['build']
    rows=[row for row in delta['packages'] if row['variant']=='standard']
    need(len(rows)==1,'STANDARD_PACKAGE_REQUIRED')
    if delta['schemaVersion']=='MainProgramChainPolicyPackageDelta/v1':
        expected=build['variants']['standard']['packagePin']
        covered=rows[0]['packagePin']
        need(type(expected) is dict and set(expected)=={'path','bytes','sha256'} and
            all(expected[key]==covered[key] for key in ('bytes','sha256')),'PACKAGE_BUILD_CHANGED')
        package_path=Path(expected['path'])
    else:
        need(delta['schemaVersion']=='ArchiveCataloguePackageDelta/v2','PACKAGE_SCHEMA_INVALID')
        expected=None
        package_path=Path(rows[0]['path'])
    actual=file_pin(package_path)
    need((expected is None or actual==expected) and actual['bytes']<=MAX_PACKAGE_BYTES and
         actual['sha256']==build['packageSha256'],'PACKAGE_BUILD_CHANGED')
    raw=package_path.read_bytes()
    need(file_pin(package_path)==actual and len(raw)==actual['bytes'] and digest(raw)==actual['sha256'],
         'PACKAGE_CHANGED_DURING_READ')
    return actual,raw


def prepare_materials_from_records(records,private,inputs):
    """Load original files through the generation, coverage and observation APIs."""
    import main_program_control_activation as activation
    import main_program_control_generation as generation
    import main_program_control_upgrade_plan as planner
    import main_program_installation_selection as contract
    revision=validate_inputs(inputs);suffix=inputs['suffix'];host='172.30.30.'+suffix
    bundle=generation.load_control_generation(records.task,private,inputs['previousControlGenerationPin'])
    coverage=activation.validate_generation_coverage(records,inputs,bundle)
    def material(reference):
        value=records.pinned(reference);raw=(records.task/reference['file']).read_bytes()
        result=dict(pin=reference,raw=raw)
        need(planner.load_material(result,reference['file'])==value,'REPORT_CHANGED_DURING_READ')
        return result
    plan_material=material(inputs['planPin']);public=json.loads(plan_material['raw'].decode('utf-8'),object_pairs_hook=contract.document)
    secret=activation.private_document(private,public['privatePlanPin'],'main-program-configuration-plan-'+revision+'.private.json')
    unit=records.pinned(inputs['unitObservationPin'])
    unit_secret=activation.private_document(private,unit['privateSnapshotPin'],'main-program-control-units-'+suffix+'-'+revision+'.private.json')
    need(unit.get('schemaVersion')=='MainControlUnitObservation/v1' and unit.get('status')=='PASS' and
        unit.get('host')==host and unit.get('historyGuardEnabledAndActive') is True and
        unit.get('originalWorkingDirectoriesHaveNoWorker') is True and
        all(unit.get(key)==inputs[key] for key in ('sourceCommit','revisionId','previousControlGenerationPin')) and
        all(unit.get(key) is False for key in activation.OBSERVATION_FALSE_FIELDS),'UNIT_OBSERVATION_INVALID')
    need({k:v for k,v in unit_secret.items() if k not in ('controllers','historyGuardProperties')}==
        {k:v for k,v in unit.items() if k not in ('controllers','privateSnapshotPin')} and
        [{k:v for k,v in row.items() if k!='properties'} for row in unit_secret['controllers']]==unit['controllers'],
        'UNIT_PRIVATE_PROJECTION_CHANGED')
    baseline=records.pinned(inputs['originalEnvironmentObservationPin'])
    originals=deepcopy(bundle['selections'][suffix]['controllers'])
    need(len(originals)==len(baseline['controllers'])==len(unit['controllers']),'HOST_CONTROLLER_COUNT_CHANGED')
    for old,observed,registered in zip(originals,baseline['controllers'],unit['controllers']):
        need(all(old[key]==observed[key]==registered[key] for key in ('service','pid')),'OBSERVED_CONTROL_CHANGED')
        old['argvSha256']=observed['argvSha256']
    # This shared API selects generation-shaped observations by its input schema.
    # It performs no activation and does not require or invent stage receipts.
    environment=activation.validate_environment_baseline(records,private,
        dict(inputs,schemaVersion='MainProgramControlActivationInputs/v4'),unit,originals)
    extra=('argvSha256','environmentSha256','systemdEnvironmentSha256','unitPin','dropinPins')
    identity=dict(host=host,previousControlGenerationPin=inputs['previousControlGenerationPin'],
        unitObservationPin=inputs['unitObservationPin'],environmentObservationPin=inputs['originalEnvironmentObservationPin'],
        controllers=[dict({key:old[key] for key in generation.SELECTION_CONTROLLER_KEYS},
            **{key:observed[key] for key in extra}) for old,observed in zip(originals,environment['controllers'])])
    build_material=material(inputs['buildPin']);delta_material=material(public['packageDeltaPin'])
    package_pin,package_raw=read_covered_package(coverage)
    prepared=prepare_materials(inputs=inputs,predecessor=bundle,public=public,private=secret,coverage=coverage,
        plan_document=plan_material,build_document=build_material,delta_document=delta_material,
        package_raw=package_raw,host_identity=identity)
    baseline=bundle['sourceBaseline']
    need(baseline.get('status')=='PASS' and baseline.get('sourceConfigRef')==activation.SOURCES[0] and
        baseline.get('pointType')=='INCREMENTAL' and baseline.get('state')=='SUCCEEDED' and
        baseline.get('actualExitCode')==0 and baseline.get('sourceRestored') is True and
        len(baseline['chain'])==3 and baseline['chain'][-1]['operationId']==baseline['operationId'],'SOURCE_BASELINE_REQUIRED')
    current=deepcopy(bundle['selections'][suffix]);current['controllers']=deepcopy(identity['controllers'])
    for row in current['controllers']:row['environmentMode']='ORIGINAL_BASELINE'
    custody=None if suffix=='57' else bundle['custodyByHost'][suffix]
    prepared['runtimeSpec']=dict(current=current,unit=unit_secret,environmentBaseline=environment,
        targetConfigRef=bundle['targets'][suffix],
        historyPins=[row['pin'] for row in secret['originalMetadata'] if row['originalHost']==host],
        sourceEvidencePins=[baseline[key] for key in ('pointPin','manifestPin','epochBindingPin')] if suffix=='57' else [],
        previousCustody=custody,originalInventory=None if custody is None else custody['originalInventory'],
        oldReceiptPin=current['activeReceiptPin'],
        retainedDocuments=[row['pin'] for row in secret['retainedDocumentsByHost'][suffix]],
        newDocuments=[row['pin'] for row in secret['newDocumentsByHost'][suffix]],
        sourceExpected=dict(baseFullRef=baseline['chain'][0]['operationId'],parentChainRef=baseline['operationId'],generationId=baseline['generationId']))
    prepared['candidateControllers']=deepcopy(public['controllers'][suffix])
    prepared['sourceArchiveProtections']=deepcopy(secret['sourceArchiveProtections'][suffix])
    prepared['packagePin']=package_pin
    original_control=next(row['value'] for row in bundle['privatePlan']['documentsByHost'][suffix]
        if row['pin']==current['controllers'][0]['controlConfigurationPin'])
    prepared['transportPythonPin']=deepcopy(original_control['pythonPin'])
    pins=[*bundle['inputPins'],*coverage['physicalPins'],*records.path_pins(),
        public['privatePlanPin'],unit['privateSnapshotPin'],environment['privatePin'],package_pin]
    for module in (__file__,activation.__file__,generation.__file__,planner.__file__,contract.__file__):
        pins.append(activation.file_pin(module))
    unique={}
    for reference in pins:
        actual=activation.file_pin(reference['path'])
        need(actual==reference,'PREPARATION_INPUT_CHANGED')
        previous=unique.setdefault(reference['path'],reference)
        need(previous==reference,'PREPARATION_INPUT_CONFLICT')
    prepared['inputPins']=list(unique.values())
    return prepared


def run_stage_steps(*,runtime_gates,write_files,candidate_gate,lock_guard):
    """Sequence actual gates and the write boundary; never issue an admission."""
    lock_guard();before=runtime_gates.before();first=candidate_gate('before')
    need(runtime_gates.preserve(before,documents_created=False)==before,'RUNTIME_ORIGINALS_CHANGED');lock_guard()
    staged=write_files();lock_guard();second=candidate_gate('after')
    need(second==first,'CANDIDATE_BINDING_CHANGED')
    need(candidate_gate('final')==first,'CANDIDATE_BINDING_CHANGED')
    after=runtime_gates.preserve(before,documents_created=True);lock_guard()
    return dict(before=before,after=after,candidate=first,files=staged)


def select_physical_lock(runtime):
    current=runtime['current'];rows=current['controllers'];target=runtime['targetConfigRef']
    suffix=current['suffix']
    need(suffix in HOSTS and current['host']=='172.30.30.'+suffix and
        [row['role'] for row in rows]==(['source','target'] if suffix=='57' else ['target']),'LOCK_CONTROLLER_SCOPE_CHANGED')
    owner=json.loads(_read_pin(rows[-1]['ownerConfigurationPin']),object_pairs_hook=document)
    target_value=owner['targets'][target];policy=owner['targetBackupEpochPolicies'][target]
    need(type(policy) is dict and policy['sourceLockPath']==target_value['replacement']['lockPath'] and
        policy['databaseUuid']==target_value['replacement']['databaseUuid'] and
        owner['targetProgramPolicies'][target]['backupEpochPolicy']==policy,'TARGET_PHYSICAL_EPOCH_CHANGED')
    if suffix=='57':
        control=json.loads(_read_pin(rows[0]['controlConfigurationPin']),object_pairs_hook=document)
        need(control['sourceEpochPolicies'][SOURCES[0]]==policy,'SOURCE_TARGET_EPOCH_MISMATCH')
    return str(_path(policy['sourceLockPath']))


class PhysicalLock:
    """Hold only the existing pinned physical scope, without creating a lock."""
    def __init__(self,path):
        self.path=_path(str(path));self.fd=None;self.identity=None

    def __enter__(self):
        import fcntl
        need(os.name=='posix','NATIVE_POSIX_REQUIRED')
        _parent_without_alias(self.path.parent);before=self.path.lstat()
        need(not self.path.is_symlink() and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'LOCK_IDENTITY_CHANGED')
        descriptor=os.open(self.path,os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
            opened=os.fstat(descriptor)
            self.identity=(before.st_dev,before.st_ino,before.st_mode,before.st_nlink,before.st_uid,before.st_gid)
            need(self.identity==(opened.st_dev,opened.st_ino,opened.st_mode,opened.st_nlink,opened.st_uid,opened.st_gid),
                'LOCK_IDENTITY_CHANGED')
            self.fd=descriptor;self.guard()
        except BaseException:
            self.fd=None;os.close(descriptor);raise
        return self

    def guard(self):
        need(self.fd is not None,'LOCK_NOT_HELD')
        _parent_without_alias(self.path.parent)
        for current in (self.path.lstat(),os.fstat(self.fd)):
            identity=(current.st_dev,current.st_ino,current.st_mode,current.st_nlink,current.st_uid,current.st_gid)
            need(identity==self.identity and stat.S_ISREG(current.st_mode) and current.st_nlink==1 and
                not self.path.is_symlink(),'LOCK_IDENTITY_CHANGED')

    def __exit__(self,*unused):
        import fcntl
        descriptor=self.fd;self.fd=None
        if descriptor is not None:
            try:fcntl.flock(descriptor,fcntl.LOCK_UN)
            finally:os.close(descriptor)


def candidate_admission(prepared,phase,programs,*,run,read,source_plan):
    need(phase in ('before','after','final'),'CANDIDATE_PHASE_INVALID')
    runtime=prepared['runtimeSpec'];old_rows=runtime['current']['controllers'];results=[]
    for old,new in zip(old_rows,prepared['candidateControllers']):
        selected=(dict(role=old['role'],engine=old['engine'],controlPin=old['controlConfigurationPin'],
            ownerPin=old['ownerConfigurationPin']) if phase=='before' else new)
        control=read(selected['controlPin'])
        for role in ('repository','recovery','control'):
            reply=json.loads(run([control['pythonPin']['path'],'-B',selected['engine']+'/'+role+'_entry.py','--check-imports'],
                timeout=90,env=dict(os.environ,**control['environment'])),object_pairs_hook=document)
            need(reply.get('role')==role,'ACTUAL_IMPORT_FAILED')
        value=dict(role=selected['role'],controlPin=selected['controlPin'],ownerPin=selected['ownerPin'],
            oldOwnerPin=old['ownerConfigurationPin'],engine=selected['engine'],targetConfigRef=runtime['targetConfigRef'],
            sources=list(SOURCES),protections=prepared['sourceArchiveProtections'],commit=prepared['filesystemSpec']['sourceCommit'])
        result=json.loads(run([control['pythonPin']['path'],'-B','-c',programs['candidate'],canonical(value).decode('utf-8')],
            timeout=180,env=dict(os.environ,**control['environment'])),object_pairs_hook=document)
        need(result.get('actualConfigurationReadPassed') is True and result.get('epoch',{}).get('state')=='READY',
            'CANDIDATE_ADMISSION_FAILED')
        if selected['role']=='target':
            need(result.get('directlyAdmittedSources')==list(SOURCES) and result.get('archiveViewsPreflightVerified') is True,
                'THREE_SOURCE_ADMISSION_REQUIRED')
        else:need(result.get('sourceCaptureVerified') is True and type(result.get('capturePin')) is dict,'SOURCE_CAPTURE_REQUIRED')
        results.append(result)
    output=dict(controllers=results)
    if runtime['current']['suffix']=='57':
        old=old_rows[0];control=read(old['controlConfigurationPin'])
        idle=json.loads(run([control['pythonPin']['path'],'-B','-c',programs['sourceIdle'],
            canonical([old['controlConfigurationPin'],SOURCES[0]]).decode('utf-8')],timeout=100,
            env=dict(os.environ,**control['environment'])),object_pairs_hook=document)
        need(idle==dict(sourceIdle=True) and callable(source_plan),'SOURCE_NOT_IDLE')
        plan=source_plan(old,control)
        need(plan.get('state')=='READY' and plan.get('sourceConfigRef')==SOURCES[0] and
            all(plan.get(key)==value for key,value in runtime['sourceExpected'].items()),'SOURCE_BASELINE_CHANGED')
        output['sourcePlan']=dict(runtime['sourceExpected'],sourceConfigRef=SOURCES[0])
    return output


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('MAIN_STAGING_SOURCE_HTTP_REDIRECT')


def control_headers(control):
    reference=control['authCredentialRef'];path=_path(reference['path']);_parent_without_alias(path.parent)
    before=path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_uid==reference['uid']==0 and
        before.st_gid==reference['gid']==0 and stat.S_IMODE(before.st_mode)==reference['mode']==0o600 and
        0<before.st_size<=2048 and not path.is_symlink(),'CREDENTIAL_IDENTITY_CHANGED')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        opened=os.fstat(fd)
        need((opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino),'CREDENTIAL_IDENTITY_CHANGED')
        raw=os.read(fd,2049)
    finally:os.close(fd)
    identity=lambda item:(item.st_dev,item.st_ino,item.st_mode,item.st_nlink,item.st_uid,item.st_gid,item.st_size,item.st_mtime_ns,item.st_ctime_ns)
    need(identity(path.lstat())==identity(before) and len(raw)==before.st_size,'CREDENTIAL_CHANGED')
    value=json.loads(raw,object_pairs_hook=document)
    need(type(value.get('headers')) is dict and all(type(k) is str and type(v) is str for k,v in value['headers'].items()),'CREDENTIAL_INVALID')
    return value['headers']


def fetch_source_plan(control,process,verify_process,headers,*,opener=None,clock=None):
    clock=time.monotonic if clock is None else clock
    deadline=clock()+10
    port=control['listenPort'];need(type(port) is int and 1<=port<=65535,'SOURCE_HTTP_PORT_INVALID')
    verify_process(process)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()) if opener is None else opener
    request=urllib.request.Request('http://127.0.0.1:'+str(port)+'/incremental-plan?sourceConfigRef='+SOURCES[0],headers=headers)
    remaining=deadline-clock();need(remaining>0,'SOURCE_HTTP_DEADLINE')
    output=bytearray()
    with opener.open(request,timeout=remaining) as response:
        need(response.status==200,'SOURCE_HTTP_STATUS')
        socket=response.fp.raw._sock
        while not response.isclosed():
            remaining=deadline-clock();need(remaining>0,'SOURCE_HTTP_DEADLINE');socket.settimeout(remaining)
            chunk=response.read1(min(65536,16*1024*1024+1-len(output)))
            if not chunk:break
            output.extend(chunk);need(len(output)<=16*1024*1024,'SOURCE_HTTP_LIMIT')
        need(response.length in (None,0),'SOURCE_HTTP_INCOMPLETE')
    need(clock()<deadline,'SOURCE_HTTP_DEADLINE');verify_process(process)
    return json.loads(output,object_pairs_hook=document)


def project_stage_reports(prepared,result):
    before,after=result['before'],result['after']
    need(before.get('documentsCreated') is False and after.get('documentsCreated') is True and
        {k:v for k,v in before.items() if k!='documentsCreated'}=={k:v for k,v in after.items() if k!='documentsCreated'},
        'RUNTIME_ORIGINALS_CHANGED')
    need(result['files']['status']=='FILES_STAGED_RUNTIME_UNVERIFIED','FILESYSTEM_STAGE_REQUIRED')
    spec=prepared['filesystemSpec'];inputs=prepared['inputs']
    common=dict(status='STAGED_NOT_ACTIVATED',sourceCommit=spec['sourceCommit'],host=spec['host'],
        **{key:inputs[key] for key in ('revisionId','previousControlGenerationPin','buildPin','planPin')},
        businessContainersUnchanged=True,configurationUnchanged=True,controlServicesReloaded=False,
        backupDispatched=False,restoreDispatched=False,containerCount=len(after['containers']),
        controls=[{key:row[key] for key in ('service','pid','argvSha256')} for row in after['controllers']],
        fstabSha256=after['fstabPin']['sha256'],mountinfoSha256=after['mountinfoSha256'])
    candidates=[];admitted=result['candidate']['controllers']
    need(len(admitted)==len(prepared['candidateControllers']),'CANDIDATE_COUNT_CHANGED')
    for row,proof in zip(prepared['candidateControllers'],admitted):
        need(proof.get('actualConfigurationReadPassed') is True and proof.get('epoch',{}).get('state')=='READY','CANDIDATE_ADMISSION_FAILED')
        if row['role']=='target':
            need(proof.get('directlyAdmittedSources')==list(SOURCES) and proof.get('archiveViewsPreflightVerified') is True,
                'THREE_SOURCE_ADMISSION_REQUIRED')
            sources=list(SOURCES)
        else:
            need(proof.get('sourceCaptureVerified') is True,'SOURCE_CAPTURE_REQUIRED');sources=[SOURCES[0]]
        candidates.append(dict(role=row['role'],controlPin=row['controlPin'],ownerPin=row['ownerPin'],
            actualConfigurationReadPassed=True,actualTargetOrCaptureBindingPassed=True,observedSourceRefs=sources,
            sourceArchiveProtections=[dict(sourceConfigRef=source,actualFactoryPreflightPassed=True,
                mountCommandExecuted=False,journalWritten=False) for source in sources] if row['role']=='target' else []))
    new=[row['pin'] for row in spec['newDocuments']];retained=[row['pin'] for row in spec['retainedDocuments']]
    return dict(engine=dict(common,engines=result['files']['engines']),configuration=dict(common,
        existingPhysicalLockAcquiredAndReleased=True,configurationStaging=dict(status='STAGED_NOT_ACTIVATED',
            documents=new+retained,newDocuments=new,retainedDocuments=retained,candidates=candidates,
            registrySelectorsPublished=False,historyMaterialsChanged=False,retainedDocumentsVerifiedUnchanged=True,
            newDocumentsCreatedExclusively=True)))


BOOTSTRAP = r'''
import base64,hashlib,json,re,shlex,sys,types
def checked(value,expected_name=None):
 raw=value['source'].encode('utf-8');reference=value['pin'] if expected_name else value
 if not raw or len(raw)>1024*1024 or len(raw)!=reference['bytes'] or hashlib.sha256(raw).hexdigest()!=reference['sha256']:
  raise ValueError('MAIN_STAGING_MODULE_SOURCE_CHANGED')
 if expected_name and reference['file']!=expected_name+'.py':raise ValueError('MAIN_STAGING_MODULE_NAME_CHANGED')
 compile(raw,expected_name or '<fixed-staging-program>','exec')
 return raw
if set(PAYLOAD)!={'schemaVersion','modules','programs','prepared','packageBase64'} or PAYLOAD['schemaVersion']!='MainProgramControlStagingExecution/v1':
 raise ValueError('MAIN_STAGING_EXECUTION_SCHEMA_CHANGED')
if [row['name'] for row in PAYLOAD['modules']]!=['main_program_control_runtime','main_program_control_staging']:
 raise ValueError('MAIN_STAGING_MODULE_SET_CHANGED')
if set(PAYLOAD['programs'])!={'environment','custody','candidate','sourceIdle'}:raise ValueError('MAIN_STAGING_PROGRAM_SET_CHANGED')
codes=[checked(row,row['name']) for row in PAYLOAD['modules']]
programs={name:checked(row).decode('utf-8') for name,row in PAYLOAD['programs'].items()}
modules=[]
for row,raw in zip(PAYLOAD['modules'],codes):
 module=types.ModuleType(row['name']);module.__file__='/__in_memory_staging__/'+row['name']+'.py'
 sys.modules[row['name']]=module;exec(compile(raw,module.__file__,'exec'),module.__dict__);modules.append(module)
environment={'need':modules[-1].need,'hashlib':hashlib,'re':re,'shlex':shlex}
exec(compile(programs['environment'],'<fixed-environment-program>','exec'),environment)
custody={};exec(compile(programs['custody'],'<fixed-custody-program>','exec'),custody)
EXPORTED=(modules[-1],programs,environment['verify_environment_values'],custody['verify_layered_receipt_custody'])
'''


def load_execution(envelope):
    scope={'PAYLOAD':envelope};exec(BOOTSTRAP,scope)
    return scope['EXPORTED']


def execution_bundle(prepared):
    import main_program_control_activation as activation
    import main_program_control_runtime as runtime
    import installation_history_custody as custody
    need('runtimeSpec' in prepared and 'packagePin' in prepared,'RUNTIME_GATES_REQUIRED')
    references=[];modules=[]
    for name,path in (('main_program_control_runtime',runtime.__file__),('main_program_control_staging',__file__)):
        reference=activation.file_pin(path);raw=Path(path).read_bytes()
        need(activation.file_pin(path)==reference and digest(raw)==reference['sha256'],'MODULE_SOURCE_CHANGED')
        references.append(reference);modules.append(dict(name=name,source=raw.decode('utf-8'),
            pin=dict(file=name+'.py',bytes=len(raw),sha256=digest(raw))))
    programs={}
    for name,source in dict(environment=activation.ENVIRONMENT_PROGRAM,custody=custody.SCRIPT,
                           candidate=activation.CANDIDATE_GATE,sourceIdle=activation.SOURCE_IDLE).items():
        raw=source.encode('utf-8');programs[name]=dict(source=source,bytes=len(raw),sha256=digest(raw))
    references.extend(activation.file_pin(path) for path in (activation.__file__,custody.__file__))
    for reference in prepared['inputPins']+references:
        need(activation.file_pin(reference['path'])==reference,'PREPARATION_INPUT_CHANGED')
    package=Path(prepared['packagePin']['path']).read_bytes()
    need(len(package)==prepared['packagePin']['bytes'] and digest(package)==prepared['packagePin']['sha256'],'PACKAGE_BUILD_CHANGED')
    envelope=dict(schemaVersion='MainProgramControlStagingExecution/v1',modules=modules,programs=programs,
        prepared=deepcopy(prepared),packageBase64=base64.b64encode(package).decode('ascii'))
    envelope['prepared']['executionInputPins']=references
    return envelope


def render_bootstrap(envelope):
    script='PAYLOAD='+repr(envelope)+'\n'+BOOTSTRAP+'''
entry,programs,verify_environment,verify_custody=EXPORTED
result=entry.remote_stage(PAYLOAD['prepared'],base64.b64decode(PAYLOAD['packageBase64'],validate=True),programs,
 verify_environment=verify_environment,verify_custody=verify_custody)
print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
'''
    compile(script,'<fixed-control-staging-bootstrap>','exec')
    return script


class CommandRunner:
    def __init__(self):self.last=None
    def __call__(self,args,timeout=90,env=None):
        import subprocess
        need(type(args) is list and all(type(value) is str for value in args) and
            type(timeout) in (int,float) and 0<timeout<=180,'COMMAND_INVALID')
        try:
            result=subprocess.run(args,capture_output=True,timeout=timeout,env=env)
        except subprocess.TimeoutExpired as error:
            self.last=dict(argv=args,timeoutSeconds=timeout,timedOut=True,stdout=base64.b64encode(error.stdout or b'').decode(),
                stderr=base64.b64encode(error.stderr or b'').decode())
            raise ValueError('MAIN_STAGING_COMMAND_TIMEOUT') from error
        self.last=dict(argv=args,timeoutSeconds=timeout,timedOut=False,actualExitCode=result.returncode,
            stdout=base64.b64encode(result.stdout).decode(),stderr=base64.b64encode(result.stderr).decode())
        need(result.returncode==0,'COMMAND_FAILED_'+str(result.returncode))
        return result.stdout


def remote_stage(prepared,package_raw,programs,*,verify_environment,verify_custody):
    """Only the fixed bootstrap calls this in the authorized native environment."""
    from main_program_control_runtime import RuntimeGates
    stage='preflight';writes=False;runner=CommandRunner();created=[]
    try:
        need(os.name=='posix','NATIVE_POSIX_REQUIRED')
        preflight_filesystem(prepared['filesystemSpec'],package_raw)
        lock_path=select_physical_lock(prepared['runtimeSpec'])
        with PhysicalLock(lock_path) as physical:
            stage='runtime-before'
            gates=RuntimeGates(prepared['runtimeSpec'],verify_environment=verify_environment,verify_custody=verify_custody,
                lock_guard=physical.guard,run=runner)
            def source_plan(process,control):
                return fetch_source_plan(control,process,gates.verify_process,control_headers(control))
            def admission(phase):
                nonlocal stage
                stage='candidate-'+phase
                return candidate_admission(prepared,phase,programs,run=runner,read=gates.read,source_plan=source_plan)
            def write():
                nonlocal stage,writes,created
                stage='write-files';writes=True
                value=stage_filesystem(prepared['filesystemSpec'],package_raw);created=value['createdPaths'];return value
            actual=run_stage_steps(runtime_gates=gates,write_files=write,candidate_gate=admission,lock_guard=physical.guard)
            physical.guard()
        stage='complete'
        return dict(status='STAGED_NOT_ACTIVATED',stage=stage,reports=project_stage_reports(prepared,actual),
            actual=actual,createdPaths=created,filesMayHaveBeenCreated=True,
            backupDispatched=False,restoreDispatched=False,controlServicesReloaded=False)
    except Exception as error:
        if isinstance(error,StagingFailure):created=list(error.created_paths)
        code=str(error) if re.fullmatch('[A-Z][A-Z0-9_]{0,160}',str(error)) else type(error).__name__
        return dict(status='FAILED',stage=stage,errorCode=code,exception=exception_details(error),createdPaths=created,filesMayHaveBeenCreated=writes,
            lastCommand=runner.last,backupDispatched=False,restoreDispatched=False,controlServicesReloaded=False)


def _path(value):
    need(type(value) is str and value and not any(ord(c)<32 for c in value),'PATH_INVALID')
    path=Path(value)
    need(path.is_absolute() and '..' not in path.parts and str(path)==value,'PATH_INVALID')
    return path


def _parent_without_alias(path):
    parent=path
    while not os.path.lexists(parent):
        need(parent!=parent.parent,'PARENT_MISSING');parent=parent.parent
    need(not parent.is_symlink() and parent.resolve(strict=True)==parent and parent.is_dir(),'PARENT_ALIAS')


def _read_pin(reference):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
        type(reference['bytes']) is int and 0<reference['bytes']<=MAX_MEMBER_BYTES and
        sha(reference['sha256']),'FILE_PIN_INVALID')
    path=_path(reference['path']);_parent_without_alias(path.parent)
    before=path.lstat()
    need(not path.is_symlink() and stat.S_ISREG(before.st_mode),'FILE_ALIAS')
    need(before.st_nlink==1,'FILE_HARDLINK')
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0))
    try:
        opened=os.fstat(fd)
        need((opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino) and opened.st_nlink==1,'FILE_CHANGED')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_MEMBER_BYTES+1)
        after=os.fstat(fd)
    finally:os.close(fd)
    identity=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
    # Windows reports ctime differently for a handle and a pathname. Compare
    # each observation through the same API; device/inode already bind the FD.
    need(identity(before)==identity(path.lstat()) and identity(opened)==identity(after), 'FILE_CHANGED')
    need(len(raw)==reference['bytes'] and digest(raw)==reference['sha256'],'FILE_PIN_CHANGED')
    return raw


def _document(row):
    need(type(row) is dict and set(row)=={'pin','value'} and type(row['value']) is dict,'DOCUMENT_INVALID')
    raw=canonical(row['value']);reference=row['pin'];path=_path(reference['path'])
    need(reference==dict(path=str(path),bytes=len(raw),sha256=digest(raw)),'DOCUMENT_PIN_CHANGED')
    return path,raw


def preflight_filesystem(spec,raw):
    """Read every preserved file and check all destinations before creating any."""
    fields={'schemaVersion','sourceCommit','revisionId','host','suffix','build','engines','newDocuments','retainedDocuments'}
    need(type(spec) is dict and set(spec)==fields and spec['schemaVersion']=='MainProgramControlFilesystemStaging/v1' and
        spec['suffix'] in HOSTS and spec['host']=='172.30.30.'+spec['suffix'] and
        re.fullmatch('[0-9a-f]{40}',spec['sourceCommit']) and re.fullmatch('r[1-9][0-9]*',spec['revisionId']) and
        spec['sourceCommit']==spec['build']['targetCommit'],'FILESYSTEM_SPEC_INVALID')
    package=verify_package(raw,spec['build']);short=spec['sourceCommit'][:7]
    count=2 if spec['suffix']=='57' else 1
    need(type(spec['engines']) is list and len(spec['engines'])==count and
        len(spec['newDocuments'])==2*count and len(spec['retainedDocuments'])==9,'FILESYSTEM_PARTITION_INVALID')
    roots=[]
    for row in spec['engines']:
        need(type(row) is dict and set(row)=={'path','previousEngine'},'ENGINE_SPEC_INVALID')
        path=_path(row['path']);previous=_path(row['previousEngine'])
        need(path.name=='engine-main-program-'+short and previous.parent==path.parent and
            re.fullmatch('engine-main-program-[0-9a-f]{7}',previous.name) and path!=previous,'ENGINE_SCOPE_CHANGED')
        _parent_without_alias(path.parent)
        need(path.parent.is_dir() and path.parent not in roots,'ENGINE_PARENT_CHANGED');roots.append(path.parent)
        need(not os.path.lexists(path),'ENGINE_EXISTS')
    config_roots=[root/'configuration'/('main-program-'+short+'-'+spec['revisionId']) for root in roots]
    for path in config_roots:
        _parent_without_alias(path.parent)
        need(path.parent.is_dir() and not os.path.lexists(path),'CONFIGURATION_EXISTS_OR_PARENT_MISSING')
    seen=set()
    for kind in ('newDocuments','retainedDocuments'):
        need(type(spec[kind]) is list,'DOCUMENT_LIST_INVALID')
        for row in spec[kind]:
            path,content=_document(row)
            need(str(path) not in seen,'DOCUMENT_PATH_DUPLICATE');seen.add(str(path))
            allowed=config_roots if kind=='newDocuments' else [root/'configuration' for root in roots]
            need(sum(path.is_relative_to(root) and path!=root for root in allowed)==1,'DOCUMENT_OUTSIDE_SCOPE')
            _parent_without_alias(path.parent)
            if kind=='newDocuments':need(not os.path.lexists(path),'NEW_DOCUMENT_EXISTS')
            else:
                need(not any(path.is_relative_to(root) for root in config_roots),'RETAINED_IN_NEW_SCOPE')
                need(_read_pin(row['pin'])==content,'RETAINED_DOCUMENT_CHANGED')
    return dict(package=package,newDocuments=deepcopy(spec['newDocuments']),retainedDocuments=deepcopy(spec['retainedDocuments']))


def verify_staging_space(spec,ready):
    import shutil
    requirements={}
    items=[(Path(row['path']).parent,sum(map(len,ready['package']['files'].values()))) for row in spec['engines']]
    items.extend((Path(row['pin']['path']).parent,row['pin']['bytes']) for row in spec['newDocuments'])
    for path,size in items:
        while not path.exists():path=path.parent
        _parent_without_alias(path);device=path.stat().st_dev;free=shutil.disk_usage(path).free
        group=requirements.setdefault(device,dict(required=64*1024*1024,available=free))
        group['required']+=size;group['available']=min(group['available'],free)
    need(all(row['available']>row['required'] for row in requirements.values()),'STAGING_CAPACITY_INSUFFICIENT')


class StagingFailure(RuntimeError):
    def __init__(self,created_paths):
        super().__init__('MAIN_STAGING_PARTIAL_FILES_RETAINED')
        self.created_paths=tuple(created_paths)


def _sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)


def _mkdir(path,created):
    path.mkdir(mode=0o700);created.append(str(path));_sync_directory(path.parent)


def _directories(path,created):
    missing=[];current=path
    while not current.exists():missing.append(current);current=current.parent
    _parent_without_alias(current)
    for directory in reversed(missing):_mkdir(directory,created)


def _write_exclusive(path,raw,created):
    _parent_without_alias(path.parent)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400)
    created.append(str(path))
    try:
        os.fchmod(fd,0o400);offset=0
        while offset<len(raw):
            wrote=os.write(fd,raw[offset:]);need(wrote>0,'WRITE_INCOMPLETE');offset+=wrote
        os.fsync(fd)
    finally:os.close(fd)
    _sync_directory(path.parent)
    reference=dict(path=str(path),bytes=len(raw),sha256=digest(raw))
    need(_read_pin(reference)==raw,'WRITE_READBACK_CHANGED');item=path.lstat()
    need(stat.S_IMODE(item.st_mode)==0o400 and item.st_nlink==1 and item.st_uid==os.geteuid(),'WRITE_IDENTITY_CHANGED')
    return reference


def stage_filesystem(spec,raw):
    """Native filesystem work only; deliberately cannot issue a stage admission."""
    need(os.name=='posix','NATIVE_POSIX_REQUIRED')
    ready=preflight_filesystem(spec,raw);verify_staging_space(spec,ready);created=[];engines=[]
    try:
        for row in spec['engines']:
            root=Path(row['path']);_mkdir(root,created)
            for name,content in ready['package']['files'].items():
                path=root/name;_directories(path.parent,created);_write_exclusive(path,content,created)
            observed={str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()}
            need(observed==set(ready['package']['files']),'ENGINE_CLOSURE_CHANGED')
            for name,content in ready['package']['files'].items():
                _read_pin(dict(path=str(root/name),bytes=len(content),sha256=digest(content)))
            engines.append(dict(path=str(root),fileCount=147,packageSha256=spec['build']['packageSha256'],
                fileManifestSha256=spec['build']['fileManifestSha256'],filesSha256Verified=True,pythonCompileVerified=True))
        for row in spec['newDocuments']:
            path,content=_document(row);_directories(path.parent,created);_write_exclusive(path,content,created)
        for row in spec['retainedDocuments']:need(_read_pin(row['pin'])==canonical(row['value']),'RETAINED_DOCUMENT_CHANGED')
    except (OSError,ValueError) as error:
        raise StagingFailure(created) from error
    return dict(status='FILES_STAGED_RUNTIME_UNVERIFIED',activationReportEligible=False,sourceCommit=spec['sourceCommit'],
        revisionId=spec['revisionId'],host=spec['host'],engines=engines,createdPaths=created,
        newDocuments=[row['pin'] for row in spec['newDocuments']],retainedDocuments=[row['pin'] for row in spec['retainedDocuments']],
        requiredRuntimeGates=list(RUNTIME_GATES))


def dispatch_remote(spec,*,transport=None):
    """Reject the obsolete unbound boundary; dispatch requires local originals."""
    raise ValueError('MAIN_STAGING_RUNTIME_GATES_REQUIRED')


def _exclusive_local(path,raw):
    path=Path(path);need(path.parent.resolve(strict=True)==path.parent and not path.is_symlink(),'OUTPUT_ALIAS')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    need(path.read_bytes()==raw,'OUTPUT_READBACK_CHANGED')
    if os.name=='posix':_sync_directory(path.parent)
    return dict(path=str(path),bytes=len(raw),sha256=digest(raw))


def native_transport(host,script,python_pin):
    import shlex
    import subprocess
    from common import SSH
    path=PurePosixPath(python_pin['path'])
    need(host in ['172.30.30.'+suffix for suffix in HOSTS] and path.is_absolute() and '..' not in path.parts and
        sha(python_pin['sha256']) and type(python_pin['bytes']) is int and python_pin['bytes']>0,'TRANSPORT_IDENTITY_CHANGED')
    command=SSH+['root@'+host,shlex.quote(str(path))+' -B -']
    try:
        result=subprocess.run(command,input=script.encode('utf-8'),capture_output=True,timeout=900)
        return dict(stdout=result.stdout,stderr=result.stderr,returncode=result.returncode,timedOut=False)
    except subprocess.TimeoutExpired as error:
        return dict(stdout=error.stdout or b'',stderr=error.stderr or b'',returncode=None,timedOut=True)


def dispatch_prepared(task,private,prepared,*,transport=None):
    import main_program_control_activation as activation
    task,private=Path(task).resolve(strict=True),Path(private).resolve(strict=True)
    need(prepared.get('status')=='PREPARED_NOT_STAGED' and 'runtimeSpec' in prepared,'RUNTIME_GATES_REQUIRED')
    spec=prepared['filesystemSpec'];stem='main-program-control-staging-'+spec['suffix']+'-'+spec['sourceCommit'][:7]+'-'+spec['revisionId']
    names=[stem+'-attempt.private.json',stem+'-stdout.private.log',stem+'-stderr.private.log',
        stem+'-transport.private.json',stem+'-result.private.json']
    destinations=[*(private/name for name in names),task/prepared['engineReportFile'],task/prepared['configurationReportFile']]
    need(not any(os.path.lexists(path) for path in destinations),'ATTEMPT_OR_REPORT_EXISTS')
    envelope=execution_bundle(prepared);script=render_bootstrap(envelope)
    attempt=dict(schemaVersion='MainProgramControlStagingAttempt/v1',status='ATTEMPT_RESERVED',inputs=prepared['inputs'],
        prepared=prepared,executionInputPins=envelope['prepared']['executionInputPins'],payloadBytes=len(script.encode('utf-8')),
        payloadSha256=digest(script.encode('utf-8')),remoteHost=spec['host'],backupDispatched=False,restoreDispatched=False)
    _exclusive_local(private/names[0],canonical(attempt))
    execute=(lambda host,body:native_transport(host,body,prepared['transportPythonPin'])) if transport is None else transport
    try:result=execute(spec['host'],script)
    except Exception as error:
        _exclusive_local(private/names[3],canonical(dict(status='UNKNOWN',errorType=type(error).__name__,exception=exception_details(error),
            filesMayHaveBeenCreated=True,automaticRetryAllowed=False)))
        raise ValueError('MAIN_STAGING_REMOTE_TRANSPORT_UNKNOWN') from error
    need(type(result) is dict and set(result)=={'stdout','stderr','returncode','timedOut'} and
        type(result['stdout']) is bytes and type(result['stderr']) is bytes and type(result['timedOut']) is bool,
        'TRANSPORT_RESULT_INVALID')
    stdout_pin=_exclusive_local(private/names[1],result['stdout']);stderr_pin=_exclusive_local(private/names[2],result['stderr'])
    transport_pin=_exclusive_local(private/names[3],canonical(dict(schemaVersion='MainProgramControlStagingTransport/v1',
        stdoutPin=stdout_pin,stderrPin=stderr_pin,actualExitCode=result['returncode'],timedOut=result['timedOut'],
        filesMayHaveBeenCreated=True,automaticRetryAllowed=False)))
    need(result['timedOut'] is False and result['returncode']==0,'REMOTE_STAGE_UNKNOWN')
    value=json.loads(result['stdout'],object_pairs_hook=document)
    private_pin=_exclusive_local(private/names[4],canonical(value))
    need(value.get('status')=='STAGED_NOT_ACTIVATED' and value.get('stage')=='complete' and transport_stderr_accepted(result['stderr']) and
        all(value.get(key) is False for key in ('backupDispatched','restoreDispatched','controlServicesReloaded')),'REMOTE_STAGE_FAILED')
    reports=value['reports'];public=prepared['inputs'];plan=activation.read_document(task/public['planPin']['file'])
    activation.validate_generation_staging(public,plan,spec['build'],reports['engine'],reports['configuration'])
    for reference in prepared['inputPins']+envelope['prepared']['executionInputPins']:
        need(activation.file_pin(reference['path'])==reference,'PREPARATION_INPUT_CHANGED')
    outputs={}
    for key,name in (('engine','engineReportFile'),('configuration','configurationReportFile')):
        reference=_exclusive_local(task/prepared[name],canonical(dict(reports[key],privateSnapshotPin=private_pin,transportEvidencePin=transport_pin)))
        outputs[key+'StagedPin']=dict(file=prepared[name],bytes=reference['bytes'],sha256=reference['sha256'])
    return dict(status='STAGED_NOT_ACTIVATED',**outputs,privateSnapshotPin=private_pin,activationPerformed=False)


def run_request(task,private,inputs_file,*,stage=False,transport=None):
    import main_program_installation_selection as contract
    records=contract.Records(task);inputs=records.read(inputs_file)
    spec=prepare_materials_from_records(records,private,inputs)
    if stage:return dispatch_prepared(task,private,spec,transport=transport)
    return spec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',required=True)
    parser.add_argument('--task',type=Path,default=TASK)
    parser.add_argument('--private',type=Path,default=PRIVATE)
    parser.add_argument('--stage',action='store_true')
    args=parser.parse_args()
    try:
        result=run_request(args.task,args.private,args.inputs,stage=args.stage)
    except (OSError,ValueError,KeyError,TypeError) as error:
        code=str(error) if isinstance(error,ValueError) and str(error).startswith('MAIN_') else 'MAIN_STAGING_INPUTS_INVALID'
        print(json.dumps(dict(status='REFUSED',errorCode=code)))
        return 1
    if args.stage:
        print(json.dumps(result));return 0
    spec=result['filesystemSpec']
    print(json.dumps(dict(status=result['status'],remoteExecutable=result['remoteExecutable'],
        sourceCommit=spec['sourceCommit'],host=spec['host'],revisionId=spec['revisionId'],
        newDocuments=len(spec['newDocuments']),retainedDocuments=len(spec['retainedDocuments']))))
    return 0


if __name__=='__main__':raise SystemExit(main())
