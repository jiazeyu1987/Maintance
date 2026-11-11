"""Pure target candidate protocol; synthetic members are not restore acceptance."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))
FILE=TASK/'main_program_target_control_candidate.py'
ADDED=('common/recovery_capture_materials.py','common/recovery_preservation_inputs.py',
    'common/recovery_preservation_source.py','common/recovery_restore_inputs.py',
    'common/recovery_target_capture.py','common/recovery_target_preservation.py')
CHANGED=('common/recovery_main_target.py','common/recovery_minimal_runtime.py','common/recovery_minimal_worker.py',
    'common/recovery_mysql_scheduler.py','common/recovery_program_evidence.py','common/recovery_program_native.py',
    'common/recovery_program_protection.py','common/recovery_program_restore.py','common/recovery_replace.py',
    'common/repository_minimal.py','common/repository_native_readback.py','common/repository_retention.py',
    'control/recovery_control_restore_catalogue.py','control/recovery_control_smallapp.py',
    'control/recovery_control_smallapp_native.py','control/recovery_control_target_availability.py',
    'formal/formal_capture_semantics.py','formal/formal_data_evidence.py','formal/formal_schema_evidence.py',
    'formal/formal_snapshot_linux.py','formal/minimal_capture_support.py','formal/minimal_capture_worker.py',
    'formal/minimal_redis_snapshot.py')


def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def pin(path,raw):return dict(path=path,bytes=len(raw),sha256=digest(raw))
def docpin(path,value):return pin(path,canonical(value))


def build(k):
    assert FILE.exists(),'MISSING_TARGET_ONLY_CONTROL_CANDIDATE'
    spec=importlib.util.spec_from_file_location('target_control_candidate_units',FILE)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.build_target_control_candidate(**k)


def repin(k):
    for name,key in (('owner','ownerConfigurationPin'),('control','controlConfigurationPin')):
        k['current_controller'][key]=docpin(k['current_controller'][key]['path'],k[name])


def graph_repin(k):
    """Recompute all graph references so semantic mutations cannot fail on old SHA."""
    p=k['preservation'];mapping={}
    def replace(value):
        if type(value) is dict:
            if set(value)=={'path','bytes','sha256'}:return deepcopy(mapping.get(value['path'],value))
            return {a:replace(b) for a,b in value.items()}
        if type(value) is list:return [replace(v) for v in value]
        return value
    for row in p['documents']:
        row['value']=replace(row['value']);row['pin']=docpin(row['pin']['path'],row['value'])
        mapping[row['pin']['path']]=row['pin']
    for key in ('capturePin','repositoryPin','policyPin'):p[key]=deepcopy(mapping[p[key]['path']])


def rows(k):return {r['pin']['path'].rsplit('/',1)[1]:r['value'] for r in k['preservation']['documents']}


@pytest.fixture
def inputs():
    old_commit='b'*40;commit='c'*40;engine='/control/engine-main-program-bbbbbbb';new_engine='/control/engine-main-program-ccccccc'
    root='/control/configuration/main-target-ccccccc-r1';target_ref='target-58'
    previous={name:b'VALUE = 1\n' for name in (*CHANGED,'recovery_entry.py','repository_entry.py','formal/formal_capture_recovery_inputs.py')}
    while len(previous)<147:previous['common/unchanged_'+str(len(previous))+'.py']=b'UNCHANGED = True\n'
    files={name:(b'VALUE = 2\n' if name in CHANGED else raw) for name,raw in previous.items()}
    files.update({name:b'NEW = True\n' for name in ADDED})
    manifest=lambda f:digest(canonical({n:digest(raw) for n,raw in f.items()}))
    old_build=dict(status='PASS',targetCommit=old_commit,fileCount=147,allFilesShaAndCompileVerified=True,
        fileManifestSha256=manifest(previous),packageSha256='a'*64)
    new_build=dict(status='PASS',targetCommit=commit,allFilesShaAndCompileVerified=True,exactCommittedInput=True,
        newCommits=False,mergeRequired=False,packages=[dict(variant='standard',fileCount=153,
        fileManifestSha256=manifest(files),sha256='d'*64,bytes=1000),dict(variant='lightweight',fileCount=152,
        fileManifestSha256='e'*64,sha256='f'*64,bytes=900)])
    original=lambda name:pin('/original/'+name,b'original-'+name.encode())
    services=[dict(role=r,id=str(i)*64,imageId='sha256:'+str(i)*64,ip='172.20.0.'+str(i))
        for i,r in enumerate(('mysql','minio','redis','backend','frontend'),1)]
    epoch=dict(schemaVersion='SourceBackupEpochPolicy/v1',sourceIdentity='original-target-58',databaseUuid='unit-uuid',
        root='/epochs/58',sourceLockPath='/locks/58')
    target=dict(targetId='original-instance',database='app',buckets=['yudao'],services=services,
        dockerPin=original('docker'),secrets=dict(mysql=dict(MYSQL_ROOT_PASSWORD=original('mysql')),
        minio=dict(MINIO_ROOT_USER=original('user'),MINIO_ROOT_PASSWORD=original('password')),
        redis=dict(REDIS_PASSWORD=original('redis'))),redisRebuild=dict(database=1),
        mainApplication=dict(schemaVersion='RegisteredMainApplication/v1',configurationPins=[original('backend')]),
        replacement=dict(databaseUuid='unit-uuid',services=dict(minio=dict(mounts=[dict(Source='/data/minio',Destination='/data',RW=True)]))))
    program=dict(schemaVersion='RegisteredMainProgramPolicy/v1',targetConfigRef=target_ref,backupEpochPolicy=epoch,
        captureConfigurationPins={'existing-source':original('old-capture')},initialEpochPin=original('epoch'))
    owner=dict(schemaVersion='RecoveryMinimalConfiguration/v1',formalModuleDirectory=engine+'/formal',targets={target_ref:target},
        targetProgramPolicies={target_ref:program},targetBackupEpochPolicies={target_ref:epoch},sources={'existing-source':{'identity':'retained'}},
        sourceProgramArchivePolicies={'existing-source':{'trust':'retained'}},unknownFutureField={'must':'remain'})
    old_owner=docpin('/control/configuration/old/main-recovery.json',owner)
    control=dict(schemaVersion='SmallAppExecutionServiceConfig/v2',programPins={role:pin(engine+'/'+role+'_entry.py',previous[role+'_entry.py'])
        for role in ('recovery','repository')},environment=dict(PYTHONPATH=engine+'/control:'+engine+'/common:'+engine+'/formal',OTHER='retained'),
        restoreConfigurations={'existing-source':{target_ref:old_owner},'second-source':{target_ref:old_owner}},
        sourceConfigurations={'existing-source':original('source')},sourceEpochPolicies={'existing-source':epoch},
        authCredentialRef=original('auth'),workingDirectory='/original/working',unknownFutureField={'must':'remain'})
    core=dict(schemaVersion='MainProgramControlActivation/v1',status='PASS',role='target',host='172.30.30.58',
        service='spug-target-58.service',engine=engine,targetConfigRef=target_ref,sourceCommit=old_commit,
        fileCount=147,fileManifestSha256=old_build['fileManifestSha256'],packageSha256=old_build['packageSha256'],
        ownerConfigurationPin=old_owner,controlConfigurationPin=docpin('/control/configuration/old/control-target.json',control))
    docs=[]
    def add(name,value):
        reference=docpin(root+'/preservation/'+name,value);docs.append(dict(pin=reference,value=value));return reference
    identity=add('source-identity.json',dict(sourceFingerprint=epoch['sourceIdentity'],databaseUuid=epoch['databaseUuid']))
    scope=add('source-scope.json',dict(schemaVersion='RecoverySourceScope/v1',sourceIdentityPin=identity,endpointHosts=['172.20.0.2']))
    versions=add('versions.json',dict(schemaVersion='MainTargetCaptureVersion/v1',targetConfigRef=target_ref,images={s['role']:s['imageId'] for s in services}))
    reference=add('reference-recipe.json',dict(schemaVersion='backup-capture-reference-recipe/v1',sourceIdentity=epoch['sourceIdentity'],coverageScopePin=scope))
    policies={r:add(r+'-policy.json',dict(schemaVersion='MainTargetDerivedCapturePolicy/v1',targetConfigRef=target_ref,sourceIdentity=epoch['sourceIdentity'])) for r in ('redis','queue')}
    derived=add('derived-recipe.json',dict(schemaVersion='backup-capture-derived-recipe/v1',sourceIdentity=epoch['sourceIdentity'],classes={
        r:dict(configurationReferences=[p]) for r,p in policies.items()}))
    credential=add('object-credential.private.json',dict(schemaVersion='backup-source-s3-credential/v1',accessKey='unit',secretKey='unit'))
    objects=add('objects.json',dict(schemaVersion='backup-capture-object-source/v1',sourceIdentity=epoch['sourceIdentity'],credentialReference=credential,
        sourceScopePin=scope,versionPins=[versions],referenceRecipePin=reference,derivedRecipePin=derived,parentExportIndexPin=None,
        endpoint='http://172.20.0.2:9000',containerPort=9000,minioContainerId=services[1]['id'],buckets=target['buckets']))
    capture_ref=target_ref+'-pre-restore'
    capture=add('capture.json',dict(schemaVersion='MainTargetCaptureConfiguration/v1',sourceConfigRef=capture_ref,
        outputRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE',sourceLockPath=epoch['sourceLockPath'],parent=None,
        tools=dict(docker=target['dockerPin']['path'],ip='/usr/sbin/ip'),source=dict(sourceIdentity=epoch['sourceIdentity'],
        sourceFingerprint=epoch['sourceIdentity'],databaseUuid=epoch['databaseUuid'],database='app',databaseLogMode='FILE_POSITION',
        mysqlContainerId=services[0]['id'],minioContainerId=services[1]['id'],writerContainerIds=[s['id'] for s in services[3:]],
        minioDataPath='/data/minio',minioMountDestination='/data',applicationImageIds=sorted({s['imageId'] for s in services}),
        passwordPin=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'],objectSourcePin=objects,
        redisSnapshot=dict(containerId=services[2]['id'],host=services[2]['ip'],database=1,passwordPin=target['secrets']['redis']['REDIS_PASSWORD']),
        configurationPins=[dict(role='configuration-0001',reference=target['mainApplication']['configurationPins'][0])],
        materialPins=[dict(purpose='source-identity',reference=identity),dict(purpose='versions',reference=versions)])))
    smb=add('smb-credential.private.json',dict(schemaVersion='RepositorySmbCredential/v1',server='nas',share='share',username='unit',password='unit'))
    template=add('readback-template.json',dict(schemaVersion='MainTargetPreservationReadbackTemplate/v1',credentialPin=smb,
        libraryPins=[original('smb.py')],recordRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION',repositoryRoot='/preservation/view'))
    repo=add('repository.json',dict(schemaVersion='MainTargetPreservationRepository/v2',repositoryRoot='/preservation/view',sourceIdentityPin=identity,
        captureBinderPin=pin(new_engine+'/formal/formal_capture_recovery_inputs.py',files['formal/formal_capture_recovery_inputs.py']),readbackTemplatePin=template))
    policy=add('policy.json',dict(schemaVersion='MainTargetPreservationPolicy/v2',targetConfigRef=target_ref,captureRef=capture_ref,
        captureConfigurationPin=capture,repositoryConfigurationPin=repo,backupEpochPolicy=epoch))
    preservation=dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',targetConfigRef=target_ref,
        documents=docs,captureRef=capture_ref,capturePin=capture,repositoryPin=repo,policyPin=policy,
        originalCredentialPins=[*target['secrets']['minio'].values(),original('smb')])
    return dict(host='58',current_controller=core,owner=owner,control=control,package_files=files,
        previous_package_files=previous,old_build=old_build,new_build=new_build,preservation=preservation,
        configuration_root=root,new_engine=new_engine)


def test_only_target_references_change_and_inputs_are_detached(inputs):
    before=deepcopy(inputs);r=build(inputs);assert inputs==before
    assert r['schemaVersion']=='MainProgramTargetControlCandidate/v1' and r['status']=='BOUND_NOT_INSTALLED'
    assert r['retainedSourceConfigurationUnchanged'] is True and r['previousController']==inputs['current_controller']
    assert r['sourceCommit']==inputs['new_build']['targetCommit'] and len(r['newDocuments'])==16
    docs={x['pin']['path']:x['value'] for x in r['newDocuments']};c=r['controller']
    owner=deepcopy(inputs['owner']);owner['formalModuleDirectory']=inputs['new_engine']+'/formal'
    ref=r['targetConfigRef'];owner['targetProgramPolicies'][ref]['captureConfigurationPins'][inputs['preservation']['captureRef']]=inputs['preservation']['capturePin']
    owner['targetPreservationPolicies']={ref:inputs['preservation']['policyPin']}
    assert docs[c['ownerPin']['path']]==owner
    control=deepcopy(inputs['control']);control['environment']['PYTHONPATH']=control['environment']['PYTHONPATH'].replace(inputs['current_controller']['engine'],inputs['new_engine'])
    control['programPins']={role:pin(inputs['new_engine']+'/'+role+'_entry.py',inputs['package_files'][role+'_entry.py']) for role in ('recovery','repository')}
    control['restoreConfigurations']={s:{ref:c['ownerPin']} for s in control['restoreConfigurations']}
    assert docs[c['controlPin']['path']]==control and c['previousOwnerPin']==inputs['current_controller']['ownerConfigurationPin']
    for row in r['newDocuments']:assert row['pin']==docpin(row['pin']['path'],row['value'])
    r['previousController']['service']='mutated';assert inputs==before
    assert build(inputs)==build(inputs)


@pytest.mark.parametrize('problem',[
    'role','host','controller-schema','owner-schema','control-schema','owner-pin','control-pin','owner-formal','target-ref',
    'old-commit','new-commit','old-count','new-count','new-manifest','new-compile','not-committed','unknown-added','unknown-changed','deleted',
    'syntax','old-compile','unsafe-member','old-program','program-roles','pythonpath','engine-parent','engine-alias','root-parent','root-revision',
    'graph-status','graph-pin','graph-duplicate','graph-missing','graph-extra','graph-outside','graph-capture-ref','graph-policy-scope',
    'graph-epoch','graph-binding','graph-dangling','graph-binder-path','graph-binder-sha','graph-schema','graph-source-scope','graph-target-instance',
    'capture-conflict','preservation-conflict','restore-foreign','restore-empty'])
def test_rejects_unproven_inputs_without_mutation(inputs,problem):
    k=inputs;c=k['current_controller'];p=k['preservation'];v=rows(k)
    if problem=='role':c['role']='source'
    elif problem=='host':k['host']='59'
    elif problem=='controller-schema':c['schemaVersion']='Unknown/v1'
    elif problem=='owner-schema':k['owner']['schemaVersion']='Unknown/v1';repin(k)
    elif problem=='control-schema':k['control']['schemaVersion']='Unknown/v1';repin(k)
    elif problem=='owner-pin':k['owner']['unknownFutureField']['must']='changed'
    elif problem=='control-pin':k['control']['workingDirectory']='/elsewhere'
    elif problem=='owner-formal':k['owner']['formalModuleDirectory']='/foreign/formal';repin(k)
    elif problem=='target-ref':c['targetConfigRef']='foreign'
    elif problem=='old-commit':c['sourceCommit']='a'*40
    elif problem=='new-commit':k['new_build']['targetCommit']='not-a-commit'
    elif problem=='old-count':k['old_build']['fileCount']=146
    elif problem=='new-count':k['new_build']['packages'][0]['fileCount']=147
    elif problem=='new-manifest':k['new_build']['packages'][0]['fileManifestSha256']='0'*64
    elif problem=='new-compile':k['new_build']['allFilesShaAndCompileVerified']=False
    elif problem=='not-committed':k['new_build']['exactCommittedInput']=False
    elif problem=='unknown-added':k['package_files']['common/unreviewed.py']=k['package_files'].pop(ADDED[0])
    elif problem=='unknown-changed':k['package_files']['recovery_entry.py']+=b'NEW=True\n'
    elif problem=='deleted':k['package_files'].pop('repository_entry.py')
    elif problem=='syntax':k['package_files'][CHANGED[0]]=b'broken (\n'
    elif problem=='old-compile':
        k['previous_package_files'][CHANGED[0]]=b'return 1\n'
        manifest=digest(canonical({n:digest(raw) for n,raw in k['previous_package_files'].items()}))
        k['old_build']['fileManifestSha256']=c['fileManifestSha256']=manifest
    elif problem=='unsafe-member':k['package_files']['common/../escape.py']=k['package_files'].pop(ADDED[0])
    elif problem=='old-program':k['control']['programPins']['recovery']['sha256']='a'*64;repin(k)
    elif problem=='program-roles':k['control']['programPins'].pop('repository');repin(k)
    elif problem=='pythonpath':k['control']['environment']['PYTHONPATH']+=':/foreign/engine-main-program-aaaaaaa/formal';repin(k)
    elif problem=='engine-parent':k['new_engine']='/foreign/engine-main-program-ccccccc'
    elif problem=='engine-alias':k['new_engine']='/control/../control/engine-main-program-ccccccc'
    elif problem=='root-parent':k['configuration_root']='/foreign/configuration/main-target-ccccccc-r1'
    elif problem=='root-revision':k['configuration_root']='/control/configuration/main-target-ccccccc-r0'
    elif problem=='graph-status':p['status']='INSTALLED'
    elif problem=='graph-pin':p['documents'][0]['value']['sourceFingerprint']='changed'
    elif problem=='graph-duplicate':p['documents'].append(deepcopy(p['documents'][0]))
    elif problem=='graph-missing':p['documents'].pop(0)
    elif problem=='graph-extra':p['documents'].append(dict(pin=docpin(k['configuration_root']+'/preservation/extra.json',{}),value={}))
    elif problem=='graph-outside':p['documents'][0]['pin']['path']='/foreign/source-identity.json';graph_repin(k)
    elif problem=='graph-capture-ref':p['captureRef']='foreign'
    elif problem=='graph-policy-scope':v['policy.json']['targetConfigRef']='foreign';graph_repin(k)
    elif problem=='graph-epoch':v['policy.json']['backupEpochPolicy']=dict(v['policy.json']['backupEpochPolicy'],sourceIdentity='foreign');graph_repin(k)
    elif problem=='graph-binding':v['policy.json']['captureConfigurationPin']=p['repositoryPin'];graph_repin(k)
    elif problem=='graph-dangling':v['capture.json']['source']['objectSourcePin']=pin(k['configuration_root']+'/preservation/missing.json',b'missing');graph_repin(k)
    elif problem=='graph-binder-path':v['repository.json']['captureBinderPin']['path']='/foreign/binder.py';graph_repin(k)
    elif problem=='graph-binder-sha':v['repository.json']['captureBinderPin']['sha256']='a'*64;graph_repin(k)
    elif problem=='graph-schema':v['capture.json']['schemaVersion']='Unknown/v1';graph_repin(k)
    elif problem=='graph-source-scope':v['capture.json']['source']['sourceIdentity']='foreign';graph_repin(k)
    elif problem=='graph-target-instance':v['capture.json']['source']['mysqlContainerId']='f'*64;graph_repin(k)
    elif problem=='capture-conflict':k['owner']['targetProgramPolicies']['target-58']['captureConfigurationPins'][p['captureRef']]=pin('/old/conflict',b'old');repin(k)
    elif problem=='preservation-conflict':k['owner']['targetPreservationPolicies']={'target-58':pin('/old/conflict',b'old')};repin(k)
    elif problem=='restore-foreign':k['control']['restoreConfigurations']['existing-source']['target-58']=pin('/foreign/owner',b'owner');repin(k)
    else:k['control']['restoreConfigurations']={};repin(k)
    before=deepcopy(k)
    with pytest.raises(ValueError):build(k)
    assert k==before


def test_exact_existing_preservation_binding_is_idempotent(inputs):
    p=inputs['preservation'];inputs['owner']['targetPreservationPolicies']={'target-58':deepcopy(p['policyPin']),'other':pin('/retained/policy',b'other')}
    inputs['owner']['targetProgramPolicies']['target-58']['captureConfigurationPins'][p['captureRef']]=deepcopy(p['capturePin'])
    repin(inputs)
    for source in inputs['control']['restoreConfigurations'].values():source['target-58']=deepcopy(inputs['current_controller']['ownerConfigurationPin'])
    repin(inputs)
    result=build(inputs);assert result['status']=='BOUND_NOT_INSTALLED'


@pytest.mark.parametrize('problem',['rename-added','extra-changed','missing-changed'])
def test_rehashed_package_manifest_cannot_approve_unknown_delta(inputs,problem):
    files=inputs['package_files']
    if problem=='rename-added':files['common/unreviewed.py']=files.pop(ADDED[0])
    elif problem=='extra-changed':files['recovery_entry.py']+=b'UNREVIEWED=True\n'
    else:files[CHANGED[0]]=inputs['previous_package_files'][CHANGED[0]]
    inputs['new_build']['packages'][0]['fileManifestSha256']=digest(canonical({n:digest(raw) for n,raw in files.items()}))
    with pytest.raises(ValueError,match='UNREVIEWED_PACKAGE_DELTA'):build(inputs)
