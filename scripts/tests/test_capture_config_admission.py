"""Non-UI config admission and unchanged ordinary request contracts."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
import minimal_capture_support as support
from formal_snapshot_linux import FormalSnapshotError


@pytest.fixture
def config_case(tmp_path):
    assert Path(support.__file__).resolve()==ROOT/'ops/recovery/minimal_capture_support.py'
    archive=tmp_path/'archive';archive.mkdir()
    reference=dict(path=str(tmp_path/'input'),bytes=1,sha256='a'*64)
    source=dict(sourceIdentity='original',sourceFingerprint='original',
        databaseUuid='11111111-1111-1111-1111-111111111111',database='app',mysqlContainerId='a'*64,
        minioContainerId='b'*64,minioDataPath=str(tmp_path/'minio'),minioMountDestination='/data',
        writerContainerIds=['c'*64],applicationImageIds=['sha256:'+'d'*64],passwordPin=reference,
        objectSourcePin=reference,configurationPins=[dict(role='application',reference=reference)],
        materialPins=[dict(purpose='catalogue',reference=reference)])
    config=dict(schemaVersion='minimal-source-capture-config/v1',sourceConfigRef='registered',archiveRoot=str(archive),
        sourceLockPath=str(tmp_path/'source.lock'),tools=dict(docker='/usr/bin/docker',ip='/usr/sbin/ip'),source=source,parent=None,
        limits=dict(workSeconds=60,cleanupSeconds=10,clientWaitSeconds=0,maxWrittenBytes=1000000,minimumFreeBytes=1,
            stopSeconds=10,querySeconds=10,readySeconds=10,dataMaxRows=100,dataMaxNodes=1000,dataMaxBytes=100000,dataSeconds=10))
    request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='full-1',action='FULL',sourceConfigRef='registered',
        parentChainRef=None,recoveryPointRef=None,targetConfigRef=None)
    return config,request,reference


def test_config_admission_is_independent_of_any_fake_ui_request(config_case):
    config,request,_=config_case;before=deepcopy((config,request))
    assert support.validate_config(config)==Path(config['archiveRoot'])
    assert (config,request)==before


@pytest.mark.parametrize('action',['FULL','INCREMENTAL'])
def test_original_ui_positive_and_parent_mapping_remain_exact(config_case,action):
    config,request,reference=config_case
    if action=='INCREMENTAL':
        request.update(action=action,parentChainRef='parent-1')
        config['parent']=dict(parentChainRef='parent-1',capturePointPin=reference,
            repositoryPointPin=reference,objectContentIndexPin=reference)
    assert support.validate_job(config,request)==Path(config['archiveRoot'])/request['operationId']


@pytest.mark.parametrize('change,code',[
    ('request-extra','MINIMAL_CAPTURE_REQUEST_INVALID'),('request-schema','MINIMAL_CAPTURE_REQUEST_INVALID'),
    ('request-source','MINIMAL_CAPTURE_CONFIG_INVALID'),('config-extra','MINIMAL_CAPTURE_CONFIG_INVALID'),
    ('source-extra','MINIMAL_SOURCE_CONFIG_INVALID'),('identity','MINIMAL_SOURCE_CONFIG_INVALID'),
    ('uuid','MINIMAL_SOURCE_CONFIG_INVALID'),('log-mode','MINIMAL_DATABASE_LOG_MODE_INVALID'),
    ('writer-empty','MINIMAL_WRITER_SET_REQUIRED'),('container','MINIMAL_CONTAINER_ID_INVALID'),
    ('image','MINIMAL_IMAGE_IDS_REQUIRED'),('materials','MINIMAL_MATERIALS_REQUIRED'),
    ('material-role','MINIMAL_MATERIALS_INVALID'),('tools','MINIMAL_TOOL_PATHS_REQUIRED'),
    ('limits','MINIMAL_LIMITS_INVALID'),('full-parent','MINIMAL_FULL_PARENT_REFUSED'),
    ('incremental-parent','MINIMAL_INCREMENTAL_PARENT_REQUIRED'),
])
def test_original_ui_error_codes_and_request_first_order(config_case,change,code):
    config,request,reference=config_case
    if change=='request-extra':request['extra']=True;config.clear()
    elif change=='request-schema':request['schemaVersion']='wrong';config.clear()
    elif change=='request-source':request['sourceConfigRef']='another'
    elif change=='config-extra':config['extra']=True
    elif change=='source-extra':config['source']['extra']=True
    elif change=='identity':config['source']['sourceFingerprint']='another'
    elif change=='uuid':config['source']['databaseUuid']='wrong'
    elif change=='log-mode':config['source']['databaseLogMode']='ROW'
    elif change=='writer-empty':config['source']['writerContainerIds']=[]
    elif change=='container':config['source']['mysqlContainerId']='wrong'
    elif change=='image':config['source']['applicationImageIds']=[]
    elif change=='materials':config['source']['configurationPins']=[]
    elif change=='material-role':config['source']['configurationPins']=[dict(role='bad role',reference=reference)]
    elif change=='tools':config['tools']={}
    elif change=='limits':config['limits']['workSeconds']=0
    elif change=='full-parent':request['parentChainRef']='parent'
    else:request.update(action='INCREMENTAL',parentChainRef='parent')
    with pytest.raises(FormalSnapshotError,match=code):support.validate_job(config,request)
