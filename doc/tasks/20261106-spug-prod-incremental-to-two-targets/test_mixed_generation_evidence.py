"""Explicit local file fixtures test selection only, never claim a live upgrade."""
import ast
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import automatic_stage_deployment as stages
import verify_automatic_backup_chain as chain
import verify_automatic_source_restoration as source

ACTUAL=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
NEW='f13d8a2'+'c'*33


def put(root,name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True).encode();path.write_bytes(raw)
    return dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def installed(tmp_path):
    task,private=tmp_path/'task',tmp_path/'private';task.mkdir();private.mkdir()
    for name in ('automatic-control-installation-57.json','automatic-spug-installation-0d44578.json',
                 'release-build-0d44578.json','automatic-full-ui-submission.json','automatic-full-audit.json'):
        shutil.copyfile(ACTUAL/name,task/name)
    shutil.copyfile(PRIVATE/'automatic-control-installation-57.private.json',private/'automatic-control-installation-57.private.json')
    (private/'package-0d44578').mkdir()
    shutil.copyfile(PRIVATE/'package-0d44578/backup-restore-standard.tgz',private/'package-0d44578/backup-restore-standard.tgz')
    old=json.loads((task/'automatic-control-installation-57.json').read_text(encoding='utf-8'))
    privileged=json.loads((private/'automatic-control-installation-57.private.json').read_text(encoding='utf-8'))
    new=deepcopy(old);new['sourceCommit']=NEW
    new.update(schemaVersion='AutomaticSourceControlUpgrade/v1',retainedTargetControlUnchanged=True,epochUnchanged=True,
        noBackupDispatched=True,noRestoreDispatched=True,previousGenerationsRetained=True,
        predecessorInstallationPin=stages.file_pin(task,'automatic-control-installation-57.json'))
    controller=new['controllers'][0];oldengine=controller['engine']
    controller.update(engine=oldengine.replace('0d44578','f13d8a2'),pid=99999,previousPid=controller['pid'])
    controller['controlConfigurationPin']=dict(controller['controlConfigurationPin'],path='/local-unit-only/control-new.json',sha256='3'*64)
    with tarfile.open(private/'package-0d44578/backup-restore-standard.tgz') as archive:
        manifest=json.load(archive.extractfile('package.json'))
    # Deliberate synthetic package metadata: no fixture is an installation proof.
    manifest['files']['control/recovery_control_smallapp_native.py']='2'*64
    canonical=json.dumps(manifest['files'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    manifest['packageSha256']=new['fileManifestSha256']=hashlib.sha256(canonical).hexdigest()
    newpackage=private/'package-f13d8a2/backup-restore-standard.tgz';newpackage.parent.mkdir()
    with tarfile.open(newpackage,'w:gz') as archive:
        raw=json.dumps(manifest).encode();info=tarfile.TarInfo('package.json');info.size=len(raw)
        archive.addfile(info,io.BytesIO(raw))
    new['packageSha256']=hashlib.sha256(newpackage.read_bytes()).hexdigest()
    build=json.loads((task/'release-build-0d44578.json').read_text(encoding='utf-8'))
    build.update(targetCommit=NEW,packageSha256=new['packageSha256'],fileManifestSha256=new['fileManifestSha256'])
    new['buildPin']=put(task,'release-build-f13d8a2.json',build)
    new['controllerGenerations']=[stages.generation('SOURCE',new,new['buildPin']),
        stages.generation('MAIN_TARGET',old,stages.file_pin(task,'release-build-0d44578.json'),stages.file_pin(task,'automatic-control-installation-57.json'))]
    name='automatic-source-control-installation-f13d8a2.json';newpin=put(task,name,new)
    secret=deepcopy(new)
    for index,row in enumerate(secret['controllers']):
        row['control']=deepcopy(privileged['controllers'][index]['control'])
    secret['controllers'][0]['control']['environment']['PYTHONPATH']=secret['controllers'][0]['control']['environment']['PYTHONPATH'].replace(oldengine,controller['engine'])
    privatepin=put(private,name[:-5]+'.private.json',secret)
    selected=dict(schemaVersion='AutomaticStageDeployment/v1',kind='I1',sourceConfigRef=stages.SOURCE,sourceCommit=NEW,
        spugCommit=stages.HISTORICAL_COMMIT,sourceInstallationPin=newpin,sourcePrivateInstallationPin=privatepin,
        sourceBuildPin=new['buildPin'],spugInstallationPin=stages.file_pin(task,'automatic-spug-installation-0d44578.json'))
    selectionpin=put(task,'automatic-i1-deployment-selection.json',selected)
    submission=json.loads((task/'automatic-full-ui-submission.json').read_text(encoding='utf-8'))
    submission.update(schemaVersion='AutomaticIncrementalUiSubmission/v2',kind='I1',implementationCommit=NEW,
        spugCommit=stages.HISTORICAL_COMMIT,deploymentSelectionPin=selectionpin)
    operation='smallapp-'+'2'*32;parent=submission['request']['operationId']
    submission['request'].update(operationId=operation,action='INCREMENTAL',parentChainRef=parent)
    submission['intent']['operationId']=operation
    put(task,'automatic-i1-ui-submission.json',submission)
    return task,private,new,submission


def test_incremental_audit_uses_selected_new_source_and_old_parent(installed):
    task,private,new,_=installed
    spec=chain.prepare(task/'automatic-i1-ui-submission.json',parent_path=task/'automatic-full-audit.json',task=task,private=private)
    assert spec['engine']==new['controllers'][0]['engine']
    assert spec['controlConfigurationPin']==new['controllers'][0]['controlConfigurationPin']
    assert spec['deployment']['sourceCommit']==NEW
    assert spec['controllerFiles'][0]!=spec['controllerFiles'][1]
    assert spec['parent']==json.loads((ACTUAL/'automatic-full-audit.json').read_text(encoding='utf-8'))


def test_explicit_old_installation_is_rejected_for_new_stage(installed):
    task,private,*_=installed
    with pytest.raises(ValueError,match='AUDIT_STAGE_INSTALLATION_MISMATCH'):
        chain.prepare(task/'automatic-i1-ui-submission.json',task/'automatic-control-installation-57.json',
            task/'automatic-full-audit.json',task=task,private=private)


def test_missing_stage_does_not_reuse_original_source(installed):
    task,private,*_=installed;(task/'automatic-i1-deployment-selection.json').unlink()
    with pytest.raises(FileNotFoundError):
        chain.prepare(task/'automatic-i1-ui-submission.json',task=task,private=private)


def test_stage_request_selection_mismatch_is_rejected(installed):
    task,private,_,submission=installed
    submission['deploymentSelectionPin']['sha256']='0'*64;put(task,'automatic-i1-ui-submission.json',submission)
    with pytest.raises((ValueError,AssertionError)):
        chain.prepare(task/'automatic-i1-ui-submission.json',task=task,private=private)


def source_evidence(installed):
    task,private,new,submission=installed
    deployment=stages.load_stage_deployment(task,private,'I1')
    audit=json.loads((ACTUAL/'automatic-full-audit.json').read_text(encoding='utf-8'))
    audit.update(operationId=submission['request']['operationId'],pointType='INCREMENTAL',deploymentSelectionPin=deployment['selectionPin'],
        sourceCommit=NEW,spugCommit=stages.HISTORICAL_COMMIT,sourceInstallationPin=deployment['selection']['sourceInstallationPin'])
    audit['package'].update(engine=new['controllers'][0]['engine'],fileManifestSha256=new['fileManifestSha256'])
    terminal=json.loads((ACTUAL/'automatic-full-ui-terminal.json').read_text(encoding='utf-8'))
    terminal.update(kind='I1',request=deepcopy(submission['request']))
    return deployment,audit,terminal


def test_source_proof_accepts_bound_v2_stage_and_retained_target(installed):
    deployment,audit,terminal=source_evidence(installed)
    _,_,new,submission=installed
    value=source.validate_evidence('I1',new,submission,audit,terminal,deployment=deployment)
    assert value['failedOriginalFullShaRequired'] is False
    assert value['deploymentSelectionPin']==deployment['selectionPin']


@pytest.mark.parametrize('change',['audit-stage','audit-commit','old-package','wrong-installation','terminal-request'])
def test_source_proof_rejects_cross_generation_evidence(installed,change):
    deployment,audit,terminal=source_evidence(installed);task,_,new,submission=installed
    if change=='audit-stage':audit['deploymentSelectionPin']['sha256']='0'*64
    elif change=='audit-commit':audit['sourceCommit']=stages.HISTORICAL_COMMIT
    elif change=='old-package':audit['package']['fileManifestSha256']='0'*64
    elif change=='wrong-installation':new=json.loads((task/'automatic-control-installation-57.json').read_text(encoding='utf-8'))
    else:terminal['request']['operationId']='other'
    with pytest.raises(ValueError):source.validate_evidence('I1',new,submission,audit,terminal,deployment=deployment)


def test_remote_source_proof_uses_each_manifest_and_target_runtime():
    assert "zip(controllers,SPEC['controllerFiles'])" in source.SCRIPT
    assert 'target_runtime' in source.SCRIPT
    assert "env=target_control['environment']" in source.SCRIPT
    assert 'sourceRuntime=source_runtime,targetRuntime=target_runtime' in source.SCRIPT
    ast.parse(source.SCRIPT)


def test_actual_full_evidence_originals_stay_unchanged():
    saved=json.loads((ACTUAL/'automatic-mixed-generation-full-originals.json').read_text(encoding='utf-8'))
    for pin in saved['files'].values():
        raw=Path(pin['path']).read_bytes()
        assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']


@pytest.mark.parametrize('kind',['I1','I2'])
def test_complete_source_prepare_binds_per_controller_packages_and_runtimes(installed,kind):
    task,private,new,submission=installed
    if kind=='I2':
        selected=json.loads((task/'automatic-i1-deployment-selection.json').read_text(encoding='utf-8'))
        selected['kind']='I2'
        submission['kind']='I2'
        submission['deploymentSelectionPin']=put(task,'automatic-i2-deployment-selection.json',selected)
        put(task,'automatic-i2-ui-submission.json',submission)
    deployment=stages.load_stage_deployment(task,private,kind)
    _,audit,terminal=source_evidence(installed)
    audit.update(deploymentSelectionPin=deployment['selectionPin'])
    terminal['kind']=kind
    put(task,'automatic-'+kind.lower()+'-audit.json',audit)
    put(task,'automatic-'+kind.lower()+'-ui-terminal.json',terminal)
    for name in ('binlog-tmpfs-tool-provisioned.json','registered-binlog-tool-restored.json','automatic_chain_audit.py'):
        shutil.copyfile(ACTUAL/name,task/name)
    for name in ('failed-365-all-pins.private.json','failed-366-all-pins.private.json'):
        shutil.copyfile(PRIVATE/name,private/name)
    destination,spec=source.prepare(kind,task=task,private=private)
    assert not destination.exists()
    assert spec['controllerFiles'][0]!=spec['controllerFiles'][1]
    assert spec['deployment']['sourceInstallationPin']==deployment['selection']['sourceInstallationPin']
    assert spec['inputPins']['installation']['path'].endswith('automatic-source-control-installation-f13d8a2.json')
    assert len(spec['failedPins'])==(10044 if kind=='I2' else 0)
    compile(spec['targetRuntimeProbe'],'target-runtime','exec')
    compile((task/'automatic_chain_audit.py').read_text(encoding='utf-8')+'\nSPEC='+repr(spec)+'\n'+source.SCRIPT,
        'sourceproof-transport','exec')


@pytest.mark.parametrize('index',[0,1])
def test_drift_of_either_selected_controller_package_is_rejected(installed,index):
    task,private,*_=installed
    name='package-f13d8a2' if index==0 else 'package-0d44578'
    package=private/name/'backup-restore-standard.tgz'
    package.write_bytes(package.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='AUDIT_PACKAGE_CHANGED'):
        chain.prepare(task/'automatic-i1-ui-submission.json',task=task,private=private)


def test_selected_inputs_cannot_change_after_prepare(installed):
    task,private,*_=installed
    spec=chain.prepare(task/'automatic-i1-ui-submission.json',parent_path=task/'automatic-full-audit.json',task=task,private=private)
    chain.verify_local_inputs(spec)
    path=task/'automatic-i1-deployment-selection.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='AUDIT_LOCAL_INPUT_CHANGED'):chain.verify_local_inputs(spec)
