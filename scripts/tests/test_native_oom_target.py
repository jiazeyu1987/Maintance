"""Target observation contract tests; Docker responses are unit fixtures only."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend/src/main/resources'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
import recovery_control_smallapp_native as module
from test_native_import_process_evidence import put, evidence


@pytest.fixture
def target(tmp_path, monkeypatch):
    read_text = Path.read_text
    monkeypatch.setattr(Path, 'read_text', lambda path, *args, **kwargs:
        'unit-test-machine' if path == Path('/etc/machine-id') else read_text(path, *args, **kwargs))
    binary = tmp_path / 'docker'
    binary.write_bytes(b'unit fixture, never executed')
    binary.chmod(0o600)
    data = tmp_path / 'data'
    data.mkdir()
    rows = []
    for role in ('mysql', 'redis', 'minio', 'backend', 'frontend'):
        rows.append(dict(Id=role, Image='image-'+role,
            Config={'Labels': {'intruoyi.recovery.target': 'isolated'}},
            Mounts=[dict(Source=str(data / role), Destination='/data', RW=True)],
            NetworkSettings={'Networks': {'isolated': {'NetworkID': 'network'}}},
            ExecIDs=None, State=dict(Running=False, Pid=0, Paused=False, Restarting=False,
                                   OOMKilled=role == 'mysql', ExitCode=137 if role == 'mysql' else 0)))
    config = dict(targets={'target': dict(targetId='isolated', dataRoot=str(data),
        machineId='unit-test-machine', dockerEngineId='engine', networkId='network', resourceBudget={},
        dataPaths=[str(data)], dockerPin=module.executor.pin(binary),
        services=[dict(role=row['Id'], id=row['Id'], imageId=row['Image']) for row in rows])})
    selection = dict(ownerConfigurationPin=put(tmp_path / 'configuration.json', config))
    def run(argv, **kwargs):
        assert argv[:3] == [str(binary), '--host', 'unix:///var/run/docker.sock']
        payload = {'ID': 'engine'} if argv[3] == 'info' else rows
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload).encode(), stderr=b'')
    monkeypatch.setattr(module.subprocess, 'run', run)
    value = dict(operationId='test-oom', targetConfigRef='target')
    native = module.Native.__new__(module.Native)
    return native, value, selection, rows, data


@pytest.mark.parametrize('field', ['machineId', 'dockerEngineId', 'networkId'])
def test_before_observation_must_match_registered_host_and_network(target, field):
    native, value, selection, _, _ = target
    reference = selection['ownerConfigurationPin']
    config = module.executor.document(reference)
    config['targets']['target'][field] = 'another-identity'
    selection['ownerConfigurationPin'] = put(Path(reference['path']), config)
    with pytest.raises(RuntimeError):
        native.restore_target_observation(value, selection)


def test_oom_target_requires_retained_claim_and_original_identity(target, tmp_path):
    native, value, selection, rows, data = target
    before = native.restore_target_observation(value, selection)
    before_pin = put(tmp_path / 'restore-target-before.json', before)
    (tmp_path / 'execute').mkdir()
    put(tmp_path / 'execute/native-intent.json', {'restoreTargetPin': before_pin})
    claim = put(data / '.recovery-operation.json', {'operationId': value['operationId']})
    proof = native.stopped_oom_target(value, tmp_path, selection)
    assert proof['beforePin'] == module.executor.pin(tmp_path / 'restore-target-before.json')
    assert proof['claimPin'] == claim
    assert module.executor.verify(claim).is_file()


@pytest.mark.parametrize('change', ['image', 'label', 'mount', 'network', 'running', 'exec',
                                  'restarting', 'not_oom', 'wrong_claim', 'no_claim'])
def test_oom_target_refuses_drift_or_writer(target, tmp_path, change):
    native, value, selection, rows, data = target
    before_pin = put(tmp_path / 'restore-target-before.json', native.restore_target_observation(value, selection))
    (tmp_path / 'execute').mkdir()
    put(tmp_path / 'execute/native-intent.json', {'restoreTargetPin': before_pin})
    if change != 'no_claim':
        put(data / '.recovery-operation.json', {'operationId': 'other' if change == 'wrong_claim' else value['operationId']})
    if change == 'image': rows[0]['Image'] = 'other'
    if change == 'label': rows[0]['Config']['Labels']['intruoyi.recovery.target'] = 'other'
    if change == 'mount': rows[0]['Mounts'][0]['Source'] = str(data / 'other')
    if change == 'network': rows[0]['NetworkSettings']['Networks']['isolated']['NetworkID'] = 'other'
    if change == 'running': rows[3]['State'].update(Running=True, Pid=123)
    if change == 'exec': rows[0]['ExecIDs'] = ['active']
    if change == 'restarting': rows[0]['State']['Restarting'] = True
    if change == 'not_oom': rows[0]['State']['OOMKilled'] = False
    with pytest.raises((RuntimeError, FileNotFoundError)):
        native.stopped_oom_target(value, tmp_path, selection)


@pytest.mark.parametrize('change', ['none', 'missing_boot', 'active_owner', 'snapshot_drift',
                                  'not_oom', 'wrong_claim', 'child_timeout', 'code124', 'code143'])
@pytest.mark.parametrize('reserved', [False, True])
def test_refresh_converges_proven_oom_without_releasing_claim(target, evidence, monkeypatch, change, reserved):
    native, value, operation, root, output = evidence
    _, target_value, selection, rows, data = target
    value['targetConfigRef'] = target_value['targetConfigRef']
    selection['ownerProgramPin'] = selection['ownerConfigurationPin']
    request_pin = put(operation / 'request.json', value)
    before = put(operation / 'restore-target-before.json', native.restore_target_observation(value, selection))
    intent = put(operation / 'execute/native-intent.json', dict(operationId=value['operationId'],
        requestId=value['operationId'], requestPin=request_pin,
        configurationPin=selection['ownerConfigurationPin'], programPin=selection['ownerProgramPin'],
        restoreTargetPin=before))
    for name in ('native-process.json', 'native-original-exit.json'):
        path = operation / 'execute' / name
        row = module.executor.document(module.executor.pin(path))
        row.update(intentPin=intent)
        if name == 'native-original-exit.json': row['requestPin'] = request_pin
        if change == 'missing_boot': row.pop('bootId', None)
        if change == 'active_owner': row['pid'] = os.getpid()
        put(path, row)
    output.update(schemaVersion='backup-restore-operation-result/v1', operationId=value['operationId'],
        requestId=value['operationId'], action='RESTORE', state='TERMINAL_UNKNOWN',
        failureCode='FORMAL_SQL_IMPORT_STREAM_FAILED', message='failure',
        data=dict(actualNativeExitCode=137, partialTargetRetained=True, retryPermitted=False),
        startedAt='2026-10-25T00:00:00Z', finishedAt='2026-10-25T00:00:01Z')
    if change == 'snapshot_drift': put(operation / 'restore-target-before.json', {})
    if change == 'not_oom': rows[0]['State']['OOMKilled'] = False
    if change == 'child_timeout': put(root / 'child-exit.json', dict(actualExitCode=-9, timedOut=True))
    if change in ('code124', 'code143'):
        code = int(change[4:])
        importer_ref = output['originalResultPins'][-1]
        importer = module.executor.document(importer_ref)
        importer['actualExitCode'] = code
        output['originalResultPins'][-1] = put(Path(importer_ref['path']), importer)
        output['data']['actualNativeExitCode'] = code
    if reserved:
        import recovery_resource_admission as admission
        host_root = root.parent / 'host-resources'; host_root.mkdir(mode=0o700)
        monkeypatch.setattr(admission, 'HOST_ROOT', host_root)
        monkeypatch.setattr(admission, 'admit', lambda *args: {'admitted': True})
        reservation = admission.reserve(module.executor.document(selection['ownerConfigurationPin']), value, root)
        output['originalResultPins'].append(reservation)
    result_pin = put(root / 'result.json', output)
    claim = put(data / '.recovery-operation.json', {'operationId': 'other' if change == 'wrong_claim' else value['operationId']})
    # The admission parser has its own tests; this test starts at its resolved root.
    monkeypatch.setattr(native, 'accepted_operation', lambda request, selected: root)
    reply = native.refresh_original(value, operation, selection)
    assert reply['state'] == ('FAILED' if change == 'none' else 'RUNNING'), reply
    if change == 'none': assert reply['errorCode'] == 'FORMAL_SQL_IMPORT_STREAM_FAILED'
    assert module.executor.verify(claim).is_file()
    assert module.executor.verify(result_pin).is_file()
    if reserved:
        assert (host_root / 'active.json').exists() is (change != 'none')
        assert module.executor.verify(reservation).is_file()
        if change == 'none':
            next_root = root.parent / 'next-operation'; next_root.mkdir()
            admission.reserve(module.executor.document(selection['ownerConfigurationPin']),
                              dict(value, operationId='next-operation'), next_root)
            active = (host_root / 'active.json').read_bytes()
            assert native.refresh_original(value, operation, selection)['state'] == 'FAILED'
            assert (host_root / 'active.json').read_bytes() == active
    from recovery_control_target_availability import unclaimed_target
    assert not unclaimed_target(dict(targetId='isolated', dataRoot=str(data), sourceConfigRef='source'),
                                'source', 'target')
    observations = [path for path in (operation / 'queries').glob('*.json') if not path.name.endswith('-oom-target.json')]
    receipt = module.executor.document(module.executor.pin(observations[0]))
    if change == 'none': assert receipt['resolutionPins']
