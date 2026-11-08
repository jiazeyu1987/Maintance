"""Task-local contracts; no server snapshots or acceptance outcomes are produced."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import closeout_contracts as contracts
import test_automatic_mixed_generation as mixed_generation_tests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from observe_closeout_hosts import controller_selection, i2_binding, SCRIPT
from verify_automatic_source_restoration import read_pinned


def save(root, name, value):
    path = root / name
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.fixture
def installed(tmp_path):
    task = Path(__file__).resolve().parent
    _, receipt = mixed_generation_tests.MixedGenerationTests().fixture(tmp_path)
    receipt.update(noBackupDispatched=True,noRestoreDispatched=True)
    # Standalone local fixture: distinct manifests prove per-controller routing.
    build_name=receipt['buildPin']['file'];build=json.loads((tmp_path/build_name).read_text(encoding='utf-8'))
    build['fileManifestSha256']='f'*64;save(tmp_path,build_name,build)
    receipt['fileManifestSha256']='f'*64;receipt['buildPin']=contracts.file_pin(tmp_path,build_name)
    receipt['controllerGenerations'][0].update(fileManifestSha256='f'*64,buildPin=receipt['buildPin'])
    name='automatic-source-control-installation-'+receipt['sourceCommit'][:7]+'.json';save(tmp_path,name,receipt)
    for suffix in ('58','59'):
        (tmp_path/('automatic-target-installation-'+suffix+'.json')).write_bytes((task/('automatic-target-installation-'+suffix+'.json')).read_bytes())
    selected=dict(schemaVersion='TaskCurrentInstallations/v2',source57=contracts.file_pin(tmp_path,name),
        spug=contracts.file_pin(tmp_path,'automatic-spug-installation-0d44578.json'),
        targets={s:contracts.file_pin(tmp_path,'automatic-target-installation-'+s+'.json') for s in ('58','59')})
    save(tmp_path,'automatic-current-installations.json',selected)
    return tmp_path, receipt


def test_57_uses_exact_new_dual_root_receipt(installed):
    task, receipt = installed
    selected = controller_selection('57', task)
    assert len(selected['controllers']) == 2
    assert [r['controlConfigurationPin'] for r in selected['controllers']] == [r['controlConfigurationPin'] for r in receipt['controllers']]
    assert 'engine-automatic-0d44578' in selected['controllers'][1]['engine']
    assert selected['controllers'][0]['sourceCommit']==receipt['sourceCommit']
    assert selected['controllers'][0]['fileManifestSha256']=='f'*64
    assert selected['controllers'][1]['fileManifestSha256']!=selected['controllers'][0]['fileManifestSha256']


@pytest.mark.parametrize('suffix', ['58', '59'])
def test_target_requires_new_pass_installation_before_remote(installed, suffix):
    task, receipt = installed
    (task/('automatic-target-installation-'+suffix+'.json')).unlink()
    with pytest.raises(FileNotFoundError):
        controller_selection(suffix, task)
    target = dict(status='FAILED', host='172.30.30.' + suffix)
    save(task, 'automatic-target-installation-' + suffix + '.json', target)
    with pytest.raises((AssertionError,ValueError)):
        controller_selection(suffix, task)


def test_target_exact_commit_and_manifest_required(installed):
    task, receipt = installed
    target = dict(status='PASS', host='172.30.30.58', sourceCommit='f' * 40)
    save(task, 'automatic-target-installation-58.json', target)
    with pytest.raises((AssertionError,ValueError)):
        controller_selection('58', task)


def test_current_selection_and_source_original_are_immutable(installed):
    task,receipt=installed
    name='automatic-source-control-installation-'+receipt['sourceCommit'][:7]+'.json'
    with (task/name).open('ab') as output:output.write(b' ')
    with pytest.raises(AssertionError,match='ORIGINAL_EVIDENCE_CHANGED'):controller_selection('57',task)


def test_i2_incomplete_evidence_fails_locally(installed):
    task, _ = installed
    with pytest.raises(FileNotFoundError):
        i2_binding(task)


def test_remote_carrier_is_syntax_valid_and_has_no_control_api_or_writes():
    tree = ast.parse(SCRIPT)
    forbidden = {'write_bytes', 'write_text', 'mkdir', 'unlink', 'rename', 'selections', 'incremental_plan'}
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in forbidden for n in ast.walk(tree))
    assert '/selections' not in SCRIPT and 'Ledger' not in SCRIPT
    assert 'os.replace(' not in SCRIPT
    assert 'systemctl' in SCRIPT and "'show'" in SCRIPT


def test_host_preservation_only_changes_closeout_binding():
    source = Path(__file__).with_name('verify_host_preservation.py').read_text(encoding='utf-8')
    assert "elif args.phase=='closeout':" in source and "binding=i2_binding(TASK,after['observedAt'])" in source
    assert "else:report['backupOperationId']=json.loads((TASK/'new-incremental-point-verified.json')" in source


@pytest.fixture
def i2_evidence(installed):
    task, installation = installed
    original = Path(__file__).with_name('automatic-full-ui-submission.json')
    submission = json.loads(original.read_text(encoding='utf-8'))
    private=task/'private';private.mkdir()
    install_name='automatic-source-control-installation-'+installation['sourceCommit'][:7]+'.json'
    privileged=deepcopy(installation)
    for controller in privileged['controllers']:controller['control']={'fixtureOnly':True}
    save(private,install_name[:-5]+'.private.json',privileged)
    stage=dict(schemaVersion='AutomaticStageDeployment/v1',kind='I2',sourceConfigRef=submission['applicationId'],
        sourceCommit=installation['sourceCommit'],spugCommit=contracts.read(task,'automatic-spug-installation-0d44578.json')['sourceCommit'],
        sourceInstallationPin=contracts.file_pin(task,install_name),sourceBuildPin=installation['buildPin'],
        sourcePrivateInstallationPin=contracts.file_pin(private,install_name[:-5]+'.private.json'),
        spugInstallationPin=contracts.file_pin(task,'automatic-spug-installation-0d44578.json'))
    save(task,'automatic-i2-deployment-selection.json',stage)
    stage_pin=contracts.file_pin(task,'automatic-i2-deployment-selection.json')
    submission.update(schemaVersion='AutomaticIncrementalUiSubmission/v2',kind='I2',implementationCommit=installation['sourceCommit'],
        spugCommit=stage['spugCommit'],deploymentSelectionPin=stage_pin)
    submission['request']['action'] = 'INCREMENTAL'
    operation = submission['request']['operationId']
    audit = dict(schemaVersion='AutomaticBackupChainAudit/v1',status='PASS',state='SUCCEEDED',actualExitCode=0,
        sourceRestored=True, operationId=operation, sourceConfigRef=submission['applicationId'], pointType='INCREMENTAL',
        sourceEpoch=installation['epoch'],finishedAt='2026-11-08T01:00:00+00:00',sourceCommit=installation['sourceCommit'],
        spugCommit=stage['spugCommit'],deploymentSelectionPin=stage_pin,sourceInstallationPin=stage['sourceInstallationPin'],
        package=dict(engine=installation['controllers'][0]['engine'],variant='standard',fileCount=130,
                     fileManifestSha256=installation['fileManifestSha256']))
    terminal=dict(schemaVersion='AutomaticIncrementalUiTerminal/v1',kind='I2',applicationId=submission['applicationId'],
        request=submission['request'],operationState='SUCCEEDED',observedAt='2026-11-08T01:00:01+00:00')
    values=dict(installation=installation,submission=submission,audit=audit,terminal=terminal)
    names=dict(installation=install_name,submission='automatic-i2-ui-submission.json',
        audit='automatic-i2-audit.json',terminal='automatic-i2-ui-terminal.json')
    pins={key:read_pinned(save(task,names[key],value))[1] for key,value in values.items()}
    pins['deploymentSelection']=read_pinned(task/'automatic-i2-deployment-selection.json')[1]
    restoration=dict(schemaVersion='AutomaticSourceRestoration/v1',status='PASS',kind='I2',operationId=operation,
        sourceConfigRef=submission['applicationId'],installationCommit=installation['sourceCommit'],sourceEpoch=audit['sourceEpoch'],
        observedAt='2026-11-08T01:00:02+00:00',sourceIdle=True,workerCount=0,sourceLockVerified=True,
        sourceServicesHealthy=True,originalGlobalStateRestored=True,redisPongVerified=True,eventScheduler='ON',
        readOnly='0',superReadOnly='0',failedOriginals=dict(inventoryCount=10044,fullShaVerified=True,
        verifiedFiles=10044,mode='FULL_SHA256'),inputPins=pins,sourceCommit=stage['sourceCommit'],spugCommit=stage['spugCommit'],
        deploymentSelectionPin=stage_pin,sourceInstallationPin=stage['sourceInstallationPin'],controllerGenerations=installation['controllerGenerations'])
    save(task,'automatic-i2-source-restoration.json',restoration)
    return task, operation, private


def test_i2_bindings_use_exact_successful_evidence_after_restoration(i2_evidence):
    task, operation, private = i2_evidence
    result = i2_binding(task, '2026-11-08T01:00:03+00:00',private=private)
    assert result['backupOperationId'] == operation
    assert set(result['automaticI2EvidencePins']) == {'installation','submission','audit','terminal','restoration','deploymentSelection'}


def test_snapshot_before_or_at_i2_restoration_is_rejected(i2_evidence):
    task, _, private = i2_evidence
    for moment in ('2026-11-08T00:00:00+00:00','2026-11-08T01:00:02+00:00'):
        with pytest.raises(ValueError, match='CLOSEOUT_HOST_SNAPSHOT_BEFORE_I2'):
            i2_binding(task, moment,private=private)


def test_changed_i2_proof_cannot_reuse_restoration(i2_evidence):
    task, _, private = i2_evidence
    path=task/'automatic-i2-audit.json';value=json.loads(path.read_text(encoding='utf-8'))
    value['unrelatedMetadata']='changed original proof'
    save(task,path.name,value)
    with pytest.raises(ValueError, match='CLOSEOUT_I2_RESTORATION_INPUT_CHANGED'):
        i2_binding(task,private=private)


@pytest.mark.parametrize('corruption', [None, 'operation', 'evidence'])
def test_final_closeout_requires_i2_preservation_binding(i2_evidence, corruption,monkeypatch):
    import verify_closeout
    task, operation, private = i2_evidence
    binding = i2_binding(task,private=private)
    original=verify_closeout.i2_binding
    monkeypatch.setattr(verify_closeout,'i2_binding',lambda task,observed_at=None:original(task,observed_at,private=private))
    report = dict(status='PASS',observedAt='2026-11-08T01:00:04+00:00',backupOperationId=operation,
                  automaticI2EvidencePins=deepcopy(binding['automaticI2EvidencePins']))
    if corruption == 'operation':
        report['backupOperationId'] = 'old-367-operation'
    elif corruption == 'evidence':
        report['automaticI2EvidencePins']['audit']['sha256'] = '0' * 64
    if corruption is None:
        verify_closeout.verify_automatic_source_preservation(task, report, operation)
    else:
        with pytest.raises(AssertionError):
            verify_closeout.verify_automatic_source_preservation(task, report, operation)
