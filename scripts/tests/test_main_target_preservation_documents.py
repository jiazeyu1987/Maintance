"""Pure provisioning contract units; no server or business backup acceptance."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
FILE=ROOT/'doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_target_preservation_documents.py'


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def pin(path,raw):
    return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def inputs():
    def p(name):return pin('/original/'+name,b'protocol-original-'+name.encode())
    secrets={name:pin('/original/'+name,raw) for name,raw in
        (('MINIO_ROOT_USER',b'unit-user'),('MINIO_ROOT_PASSWORD',b'unit-password'))}
    originals={v['path']:dict(pin=v,raw=raw) for v,raw in
        ((secrets['MINIO_ROOT_USER'],b'unit-user'),(secrets['MINIO_ROOT_PASSWORD'],b'unit-password'))}
    smb_raw=canonical(dict(schemaVersion='RepositorySmbCredential/v1',server='nas.example',share='share',username='unit-nas',password='unit-secret'))
    smb=pin('/original/smb-secret',smb_raw)
    originals[smb['path']]=dict(pin=smb,raw=smb_raw)
    services=[dict(role=r,id=str(i)*64,imageId='sha256:'+str(i)*64,ip='172.20.0.'+str(i))
        for i,r in enumerate(('mysql','minio','redis','backend','frontend'),1)]
    epoch=dict(schemaVersion='SourceBackupEpochPolicy/v1',sourceIdentity='target-58',
        databaseUuid='11111111-1111-1111-1111-111111111111',root='/epochs/58',sourceLockPath='/locks/58')
    config=p('backend.properties');redis=p('redis-secret')
    target=dict(targetId='original-physical-instance-58',database='app',buckets=['yudao'],services=services,
        dockerPin=pin('/usr/bin/docker',b'docker-protocol'),
        secrets=dict(minio=secrets,mysql=dict(MYSQL_ROOT_PASSWORD=p('mysql-secret')),
            redis=dict(REDIS_PASSWORD=redis)),redisRebuild=dict(database=1),
        mainApplication=dict(schemaVersion='RegisteredMainApplication/v1',configurationPins=[config]),
        replacement=dict(databaseUuid=epoch['databaseUuid'],services={'minio':dict(mounts=[
            dict(Source='/data/minio',Destination='/data',RW=True,Type='volume')])}))
    limits=dict(workSeconds=21600,cleanupSeconds=600,clientWaitSeconds=5,maxWrittenBytes=64*1024**3,
        minimumFreeBytes=2*1024**3,stopSeconds=30,querySeconds=120,readySeconds=300,
        dataMaxRows=10000000,dataMaxNodes=100000000,dataMaxBytes=16*1024**3,dataSeconds=7200)
    return dict(target_ref='target-58',target=target,program_policy=dict(targetConfigRef='target-58',backupEpochPolicy=epoch),
        configuration_root='/control/configuration/preservation-r1',capture_tools=dict(docker='/usr/bin/docker',ip='/usr/sbin/ip'),
        capture_limits=limits,database_log_mode='FILE_POSITION',smb_credential_format='RepositorySmbCredential/v1',
        originals=originals,endpoint_hosts=['172.20.0.2','host.docker.internal'],
        reference_recipe=dict(referenceQueries=[dict(table='infra_file',columns=['id','config_id','path','deleted'])],
            objectBindings=[dict(table='infra_file',bucket=dict(literal='yudao'),keyColumn='path',
                versionColumn=None,nullable=False,keyEncoding='RAW_KEY',urlPrefix=None,rowFilter=dict(config_id='28'))],
            maxRows=500000,complete=True,missingReferencePolicy='PRESERVE_SOURCE_BASELINE'),
        derived_classes=dict(redis=dict(classification='RESTORE',executorKey='REDIS_DUMP_ABSOLUTE_EXPIRY',
            requiredForBusiness=True,rebuildFrom=None),queue=dict(classification='NOT_PRESENT',executorKey=None,
            requiredForBusiness=False,rebuildFrom=None)),
        repository=dict(repositoryId='preserve-58',repositoryRoot='/control/preservation-view',
            uncRoot='\\\\nas.example\\share',repositoryRelativePath='backups/preserve-58',
            credentialPin=smb,libraryPins=[p('smbclient.py'),p('smbprotocol.py')],port=445,authProtocol='ntlm'),
        binder_pin=pin('/control/engine-abc/formal/formal_capture_recovery_inputs.py',b'binder'),
        budgets=dict(maxArchiveBytes=64*1024**3,maxReadbackRecordBytes=512*1024**2,
            maxPreservationSeconds=21600,minimumFreeBytes=2*1024**3,maximumRecordBytes=64*1024**2))


def build(**kwargs):
    assert FILE.exists(),'MISSING_TARGET_PRESERVATION_PROVISIONER'
    spec=importlib.util.spec_from_file_location('target_preservation_document_units',FILE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.build_target_preservation_documents(**kwargs)


def documents(result):
    return {r['pin']['path']:r['value'] for r in result['documents']}


def test_target_owns_capture_graph_and_original_inputs_are_unchanged(inputs):
    before=deepcopy(inputs);result=build(**inputs);rows=documents(result)
    assert inputs==before and result['status']=='BOUND_NOT_INSTALLED'
    capture=rows[result['capturePin']['path']];source=capture['source']
    assert capture['schemaVersion']=='MainTargetCaptureConfiguration/v1' and 'archiveRoot' not in capture
    assert capture['sourceLockPath']==inputs['program_policy']['backupEpochPolicy']['sourceLockPath']
    assert capture['parent'] is None and source['sourceIdentity']==source['sourceFingerprint']=='target-58'
    assert source['databaseUuid']==inputs['target']['replacement']['databaseUuid']
    assert source['databaseLogMode']=='FILE_POSITION'
    assert source['mysqlContainerId']=='1'*64 and source['minioContainerId']=='2'*64
    assert set(source['writerContainerIds'])=={'4'*64,'5'*64}
    assert source['redisSnapshot']['passwordPin']==inputs['target']['secrets']['redis']['REDIS_PASSWORD']
    assert source['configurationPins']==[dict(role='configuration-0001',reference=inputs['target']['mainApplication']['configurationPins'][0])]
    descriptor=rows[source['objectSourcePin']['path']]
    assert descriptor['endpoint']=='http://172.20.0.2:9000' and descriptor['parentExportIndexPin'] is None
    assert rows[descriptor['credentialReference']['path']]['secretKey']=='unit-password'
    assert descriptor['versionPins'][0] in [r['reference'] for r in source['materialPins']]
    assert rows[descriptor['versionPins'][0]['path']]['images']=={s['role']:s['imageId'] for s in inputs['target']['services']}
    for row in result['documents']:assert row['pin']==pin(row['pin']['path'],canonical(row['value']))
    policy=rows[result['policyPin']['path']];repo=rows[policy['repositoryConfigurationPin']['path']]
    assert policy['captureConfigurationPin']==result['capturePin']
    assert policy['backupEpochPolicy']==inputs['program_policy']['backupEpochPolicy']
    assert repo['writeView']==dict(mountPoint='/control/preservation-view',filesystem='cifs',
        mountSource='//nas.example/share',mountRoot='/backups/preserve-58')
    readback=rows[repo['readbackTemplatePin']['path']]
    assert readback['recordRootPolicy']=='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION'
    assert readback['credentialPin']['path']=='/control/configuration/preservation-r1/smb-credential.private.json'
    assert rows[readback['credentialPin']['path']]['username']=='unit-nas'
    assert build(**inputs)==result


def test_explicit_v2_none_has_no_invented_redis_password(inputs):
    inputs['target']['mainApplication'].update(schemaVersion='RegisteredMainApplication/v2',redisAuthentication=dict(mode='NONE',aclSha256='a'*64))
    inputs['target']['secrets'].pop('redis')
    r=build(**inputs)
    assert 'passwordPin' not in documents(r)[r['capturePin']['path']]['source']['redisSnapshot']


def test_explicit_mount_credential_source_is_copied_into_private_formal_document(inputs):
    raw=b'username=unit-nas\npassword=unit-secret\n';p=pin('/original/mount.credentials',raw)
    inputs['repository']['credentialPin']=p;inputs['smb_credential_format']='CIFS_MOUNT_CREDENTIAL/v1'
    inputs['originals'][p['path']]=dict(pin=p,raw=raw)
    result=build(**inputs);rows=documents(result)
    reference=rows[rows[result['repositoryPin']['path']]['readbackTemplatePin']['path']]['credentialPin']
    assert rows[reference['path']]==dict(schemaVersion='RepositorySmbCredential/v1',server='nas.example',share='share',username='unit-nas',password='unit-secret')


@pytest.mark.parametrize('problem',[
    'target-ref','uuid','duplicate-service','missing-writer','credential-pin','credential-newline',
    'unsafe-root','foreign-tool','budget','readback-budget','reference-bucket','unknown-auth','noauth-secret',
    'reference-schema','derived-policy','log-mode'])
def test_provisioning_rejects_unproven_scope_without_mutating_inputs(inputs,problem):
    if problem=='target-ref':inputs['program_policy']['targetConfigRef']='other'
    elif problem=='uuid':inputs['program_policy']['backupEpochPolicy']['databaseUuid']='22222222-2222-2222-2222-222222222222'
    elif problem=='duplicate-service':inputs['target']['services'][1]['id']='1'*64
    elif problem=='missing-writer':inputs['target']['services'].pop()
    elif problem=='credential-pin':inputs['originals']['/original/MINIO_ROOT_PASSWORD']['raw']=b'changed'
    elif problem=='credential-newline':
        raw=b'password\n';p=pin('/original/MINIO_ROOT_PASSWORD',raw)
        inputs['target']['secrets']['minio']['MINIO_ROOT_PASSWORD']=p
        inputs['originals'][p['path']]=dict(pin=p,raw=raw)
    elif problem=='unsafe-root':inputs['configuration_root']='/control/../elsewhere'
    elif problem=='foreign-tool':inputs['capture_tools']['docker']='/other/docker'
    elif problem=='budget':inputs['capture_limits']['maxWrittenBytes']=2**63-1
    elif problem=='readback-budget':inputs['budgets']['maximumRecordBytes']=inputs['budgets']['maxReadbackRecordBytes']+1
    elif problem=='reference-bucket':inputs['reference_recipe']['objectBindings'][0]['bucket']['literal']='foreign'
    elif problem=='unknown-auth':inputs['target']['mainApplication'].update(schemaVersion='RegisteredMainApplication/v2',redisAuthentication=dict(mode='UNKNOWN'))
    elif problem=='noauth-secret':inputs['target']['mainApplication'].update(schemaVersion='RegisteredMainApplication/v2',redisAuthentication=dict(mode='NONE',aclSha256='a'*64))
    elif problem=='reference-schema':inputs['reference_recipe']['referenceQueries'][0]['columns'].remove('path')
    elif problem=='log-mode':inputs['database_log_mode']='UNKNOWN'
    else:inputs['derived_classes']['queue']['classification']='ASSUME_EMPTY'
    before=deepcopy(inputs)
    with pytest.raises(ValueError,match='TARGET_PRESERVATION_'):build(**inputs)
    assert inputs==before
