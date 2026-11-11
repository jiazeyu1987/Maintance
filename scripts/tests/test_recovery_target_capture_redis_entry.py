"""Actual configuration gate over real files and finite target declarations.

No MAIN execution context, external command, backup or restore is claimed here.
The complete target lifecycle is covered by separate Linux protocol tests.
"""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
import recovery_target_capture as capture
from recovery_engine import RecoveryError,pin,write


@pytest.fixture
def capture_gate(tmp_path,monkeypatch):
    assert sys.platform.startswith('linux'),'REAL_LINUX_REQUIRED_NOT_A_SKIP'
    roles=('mysql','minio','redis','backend','frontend')
    services={role:dict(role=role,id=str(index)*64,imageId='sha256:'+str(index)*64,
        ip='172.20.0.'+str(index+2)) for index,role in enumerate(roles,1)}
    credentials={}
    for name in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD','MYSQL_ROOT_PASSWORD','REDIS_PASSWORD'):
        path=tmp_path/name;path.write_bytes(('finite-contract-'+name).encode());path.chmod(0o600)
        credentials[name]=pin(path)
    s3=write(tmp_path/'objects-credentials.private.json',dict(
        accessKey=Path(credentials['MINIO_ROOT_USER']['path']).read_text(),
        secretKey=Path(credentials['MINIO_ROOT_PASSWORD']['path']).read_text()))
    versions=write(tmp_path/'versions.json',dict(images={role:value['imageId'] for role,value in services.items()}))
    objects=write(tmp_path/'objects.json',dict(sourceIdentity='target58',minioContainerId=services['minio']['id'],
        endpoint='http://'+services['minio']['ip']+':9000',buckets=['finite-contract'],
        parentExportIndexPin=None,credentialReference=s3,versionPins=[versions]))
    tools={}
    for name in ('docker','ip'):
        path=tmp_path/name;path.write_bytes(b'#!/bin/sh\nexit 80\n');path.chmod(0o700);tools[name]=str(path)
    monkeypatch.setenv('PATH',str(tmp_path));monkeypatch.delenv('DOCKER_CONTEXT',raising=False)
    monkeypatch.delenv('DOCKER_TLS_VERIFY',raising=False);monkeypatch.setenv('DOCKER_HOST','unix:///var/run/docker.sock')
    epoch=dict(sourceIdentity='target58',databaseUuid='11111111-1111-1111-1111-111111111111',
        root=str(tmp_path/'epoch'),sourceLockPath=str(tmp_path/'source.lock'))
    replacement=dict(databaseUuid=epoch['databaseUuid'],stateRoot=str(tmp_path/'state'),
        services={role:dict(mounts=[]) for role in roles})
    replacement['services']['minio']['mounts']=[dict(Source=str(tmp_path/'objects-data'),Destination='/data',RW=True)]
    target=dict(mainApplication=dict(schemaVersion='RegisteredMainApplication/v1',configurationPins=[]),
        replacement=replacement,database='finite_contract',dataPaths=[str(tmp_path/'data')],dataRoot=str(tmp_path/'data'),
        dockerPin=pin(tools['docker']),buckets=['finite-contract'],redisRebuild=dict(database=1),
        secrets=dict(mysql=dict(MYSQL_ROOT_PASSWORD=credentials['MYSQL_ROOT_PASSWORD']),
            minio={key:credentials[key] for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')},
            redis=dict(REDIS_PASSWORD=credentials['REDIS_PASSWORD'])))
    source=dict(sourceIdentity='target58',sourceFingerprint='target58',databaseUuid=epoch['databaseUuid'],
        database=target['database'],mysqlContainerId=services['mysql']['id'],minioContainerId=services['minio']['id'],
        minioMountDestination='/data',minioDataPath=str(tmp_path/'objects-data'),
        writerContainerIds=[services[role]['id'] for role in ('backend','frontend')],
        applicationImageIds=[value['imageId'] for value in services.values()],
        passwordPin=credentials['MYSQL_ROOT_PASSWORD'],configurationPins=[],objectSourcePin=objects,
        materialPins=[dict(purpose='versions',reference=versions)],redisSnapshot=dict(containerId=services['redis']['id'],
            host=services['redis']['ip'],database=1,passwordPin=credentials['REDIS_PASSWORD']))
    config=dict(schemaVersion='MainTargetCaptureConfiguration/v1',
        outputRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE',sourceConfigRef='target58',parent=None,
        sourceLockPath=epoch['sourceLockPath'],tools=tools,source=source)
    native=SimpleNamespace(config=target,config_services=services,source=dict(archiveRoots=[str(tmp_path/'archive')]),
        native_context=SimpleNamespace(_context=SimpleNamespace(_root=tmp_path/'operations'/'restore1',
            _policy=dict(backupEpochPolicy=epoch))))
    return native,config


@pytest.mark.parametrize('version,mode',[('v1','PASSWORD'),('v2','PASSWORD'),('v2','NONE')])
def test_actual_configuration_gate_accepts_registered_redis_contract(capture_gate,version,mode):
    native,config=capture_gate
    native.config['mainApplication']['schemaVersion']='RegisteredMainApplication/'+version
    if version=='v2':
        native.config['mainApplication']['redisAuthentication']=dict(mode=mode)
        if mode=='NONE':
            native.config['mainApplication']['redisAuthentication']['aclSha256']='c'*64
            native.config['secrets'].pop('redis');config['source']['redisSnapshot'].pop('passwordPin')
    before=deepcopy((native.config,config))
    assert capture.MainTargetCapture._configuration(native,'target58',config) is None
    assert (native.config,config)==before


def test_actual_configuration_gate_rejects_missing_v1_password(capture_gate):
    native,config=capture_gate;config['source']['redisSnapshot'].pop('passwordPin')
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED'):
        capture.MainTargetCapture._configuration(native,'target58',config)


def test_actual_configuration_gate_rejects_unknown_v2_authentication(capture_gate):
    native,config=capture_gate
    native.config['mainApplication'].update(schemaVersion='RegisteredMainApplication/v2',
        redisAuthentication=dict(mode='AUTO'))
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_REDIS_AUTHENTICATION_INVALID'):
        capture.MainTargetCapture._configuration(native,'target58',config)
