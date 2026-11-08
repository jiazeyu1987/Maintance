"""Local file contracts for explicit stage selection; no runtime or network."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from automatic_stage_deployment import load_stage_deployment, SPUG_FILES, HISTORICAL_COMMIT

SOURCE = 'intruoyi-57-safe-20261024-v1'
NEW = 'f13d8a2'+'c'*33


def put(root, name, value):
    raw = (json.dumps(value, sort_keys=True)+'\n').encode('utf-8')
    (root/name).write_bytes(raw)
    return dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def fixture(tmp_path):
    task, private = tmp_path/'task', tmp_path/'private'
    task.mkdir();private.mkdir()
    build = dict(status='PASS', targetCommit=HISTORICAL_COMMIT, packageSha256='a'*64, fileManifestSha256='b'*64, fileCount=130)
    build_pin = put(task, 'release-build-0d44578.json', build)
    controls = [dict(service='source', engine='/engine/source-0d', pid=1), dict(service='target', engine='/engine/target-0d', pid=2)]
    old = dict(status='PASS', sourceCommit=HISTORICAL_COMMIT, packageSha256='a'*64, fileManifestSha256='b'*64,
               fileCount=130, controllers=controls, policy={'sourceConfigRef':SOURCE}, epoch={'state':'READY'})
    old_pin = put(task, 'automatic-control-installation-57.json', old)
    old_private = copy.deepcopy(old)
    for controller in old_private['controllers']:controller['control']={'privateConfigurationFixture':True}
    private_pin = put(private, 'automatic-control-installation-57.private.json', old_private)
    spug = dict(status='PASS', sourceCommit=HISTORICAL_COMMIT, runtime=str(tmp_path/'runtime'),
                files={name:dict(bytes=1, installedSha256='d'*64) for name in SPUG_FILES})
    spug_pin = put(task, 'automatic-spug-installation-0d44578.json', spug)
    stage = dict(schemaVersion='AutomaticStageDeployment/v1', kind='FULL', sourceConfigRef=SOURCE,
                 sourceCommit=HISTORICAL_COMMIT, spugCommit=HISTORICAL_COMMIT, sourceInstallationPin=old_pin,
                 sourcePrivateInstallationPin=private_pin, sourceBuildPin=build_pin, spugInstallationPin=spug_pin)
    put(task, 'automatic-full-deployment-selection.json', stage)
    return task, private, stage, old, old_private, build


def upgrade(fixture):
    task, private, stage, old, old_private, build = fixture
    newbuild = dict(build, targetCommit=NEW, packageSha256='e'*64, fileManifestSha256='f'*64)
    newbuildpin = put(task, 'release-build-f13d8a2.json', newbuild)
    new = copy.deepcopy(old)
    new.update(schemaVersion='AutomaticSourceControlUpgrade/v1', sourceCommit=NEW, packageSha256='e'*64,
               fileManifestSha256='f'*64, buildPin=newbuildpin, predecessorInstallationPin=stage['sourceInstallationPin'],
               retainedTargetControlUnchanged=True, epochUnchanged=True, noBackupDispatched=True,
               noRestoreDispatched=True, previousGenerationsRetained=True)
    new['controllers'][0].update(engine='/engine/source-new', pid=3, previousPid=1)
    new['controllerGenerations']=[dict(role='SOURCE', sourceCommit=NEW, packageSha256='e'*64,
        fileManifestSha256='f'*64, fileCount=130, buildPin=newbuildpin), dict(role='MAIN_TARGET',
        sourceCommit=HISTORICAL_COMMIT, packageSha256='a'*64, fileManifestSha256='b'*64,
        fileCount=130, buildPin=stage['sourceBuildPin'], installationPin=stage['sourceInstallationPin'])]
    newpin = put(task, 'automatic-source-control-installation-f13d8a2.json', new)
    privileged = copy.deepcopy(new)
    for controller in privileged['controllers']:controller['control']={'privateConfigurationFixture':True}
    newprivatepin = put(private, 'automatic-source-control-installation-f13d8a2.private.json', privileged)
    selected = dict(stage, kind='I1', sourceCommit=NEW, sourceInstallationPin=newpin,
                    sourcePrivateInstallationPin=newprivatepin, sourceBuildPin=newbuildpin)
    put(task, 'automatic-i1-deployment-selection.json', selected)
    return selected, new, privileged


def test_historical_full_explicit_selection_preserves_original_bytes(fixture):
    task, private, stage, *_ = fixture
    original=(task/stage['sourceInstallationPin']['file']).read_bytes()
    result=load_stage_deployment(task, private, 'FULL')
    assert result['sourceCommit']==result['spugCommit']==HISTORICAL_COMMIT
    assert [v['role'] for v in result['controllerGenerations']]==['SOURCE','MAIN_TARGET']
    assert (task/stage['sourceInstallationPin']['file']).read_bytes()==original


def test_new_source_with_historical_target_and_spug_is_supported(fixture):
    task, private, *_=fixture;upgrade(fixture)
    value=load_stage_deployment(task,private,'I1')
    assert value['sourceCommit']==NEW and value['spugCommit']==HISTORICAL_COMMIT
    assert value['controllerGenerations'][0]['fileManifestSha256']=='f'*64
    assert value['controllerGenerations'][1]['fileManifestSha256']=='b'*64


def test_missing_selection_does_not_choose_latest(fixture):
    task,private,*_=fixture
    with pytest.raises(FileNotFoundError):load_stage_deployment(task,private,'I1')


@pytest.mark.parametrize('field,value', [('kind','I2'),('sourceCommit','2'*40),('spugCommit','2'*40),('sourceConfigRef','other')])
def test_stage_identity_mismatch_rejected(fixture,field,value):
    task,private,*_=fixture;stage,_,_=upgrade(fixture);stage[field]=value
    put(task,'automatic-i1-deployment-selection.json',stage)
    with pytest.raises(ValueError):load_stage_deployment(task,private,'I1')


@pytest.mark.parametrize('change', ['schema','status','generation','private','spug','previous-pid','epoch'])
def test_unproved_or_changed_installation_rejected(fixture,change):
    task,private,*_=fixture;stage,new,privileged=upgrade(fixture)
    if change=='schema':new['schemaVersion']='Unknown/v1'
    if change=='status':new['status']='PREPARED'
    if change=='generation':new['controllerGenerations'][1]['fileManifestSha256']='f'*64
    if change=='previous-pid':new['controllers'][0]['previousPid']=999
    if change=='epoch':new['epoch']={'state':'READY','differentEpoch':True}
    if change in ('schema','status','generation','previous-pid','epoch'):
        stage['sourceInstallationPin']=put(task,stage['sourceInstallationPin']['file'],new)
        private_changed=copy.deepcopy(new)
        for controller in private_changed['controllers']:controller['control']={'privateConfigurationFixture':True}
        stage['sourcePrivateInstallationPin']=put(private,stage['sourcePrivateInstallationPin']['file'],private_changed)
    if change=='private':(private/stage['sourcePrivateInstallationPin']['file']).write_text('{}',encoding='utf-8')
    if change=='spug':
        spug=json.loads((task/stage['spugInstallationPin']['file']).read_text(encoding='utf-8'))
        spug['files'].pop(next(iter(spug['files'])))
        stage['spugInstallationPin']=put(task,stage['spugInstallationPin']['file'],spug)
    put(task,'automatic-i1-deployment-selection.json',stage)
    with pytest.raises(ValueError):load_stage_deployment(task,private,'I1')
