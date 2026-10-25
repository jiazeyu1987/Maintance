"""Real local files/processes; no server or business acceptance claims."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
import recovery_resource_admission as admission
REAL_ADMIT = admission.admit


@pytest.fixture
def host(tmp_path, monkeypatch):
    directory = tmp_path / 'host'
    directory.mkdir(mode=0o700)
    machine = tmp_path / 'machine-id'
    machine.write_text('test-host', encoding='ascii')
    monkeypatch.setattr(admission, 'HOST_ROOT', directory, raising=False)
    monkeypatch.setattr(admission, 'MACHINE_ID', machine, raising=False)
    # Only the snapshot is a fixture; reservation files and locking are real.
    monkeypatch.setattr(admission, 'admit', lambda *args: {'admitted': True})
    config = {'targets': {'target': {'machineId': 'test-host', 'resourceBudget': {}}}}
    request = {'operationId': 'first', 'targetConfigRef': 'target'}
    root = tmp_path / 'first'; root.mkdir()
    return config, request, root, directory


def test_distinct_target_cannot_overbook_host(host):
    config, request, root, directory = host
    admission.reserve(config, request, root)
    other = root.parent / 'second'; other.mkdir()
    with pytest.raises(RuntimeError, match='RESTORE_HOST_RESOURCE_RESERVED'):
        admission.reserve(config, dict(request, operationId='second'), other)
    assert json.loads((directory / 'active.json').read_bytes())['operationId'] == 'first'


def test_process_death_does_not_release_reservation(host):
    config, request, root, directory = host
    code = '''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import recovery_resource_admission as a
a.HOST_ROOT=Path(sys.argv[2]);a.MACHINE_ID=Path(sys.argv[3])
a.admit=lambda *args: {'admitted':True}
a.reserve(json.loads(sys.argv[4]),json.loads(sys.argv[5]),Path(sys.argv[6]))
print('reserved',flush=True)
import time
time.sleep(60)
'''
    process = subprocess.Popen([sys.executable, '-c', code, str(Path(admission.__file__).parent),
        str(directory), str(admission.MACHINE_ID), json.dumps(config), json.dumps(request), str(root)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        import select
        assert select.select([process.stdout], [], [], 10)[0], 'reservation child did not become ready'
        assert process.stdout.readline().strip() == 'reserved'
    finally:
        process.kill()
        process.communicate(timeout=10)
    assert process.returncode == -9
    other = root.parent / 'second'; other.mkdir()
    with pytest.raises(RuntimeError, match='RESTORE_HOST_RESOURCE_RESERVED'):
        admission.reserve(config, dict(request, operationId='second'), other)


def test_success_release_retains_immutable_reservation(host):
    from recovery_engine import pin, write
    config, request, root, directory = host
    reference = admission.reserve(config, request, root)
    result = write(root / 'worker-result.json', {'operationId': 'first', 'state': 'SUCCEEDED', 'actualExitCode': 0})
    exited = write(root / 'child-exit.json', {'actualExitCode': 0, 'timedOut': False})
    admission.release_success(config, request, root, result, exited)
    assert not (directory / 'active.json').exists()
    assert pin(Path(reference['path'])) == reference
    assert (root / 'resource-release.json').is_file()


@pytest.mark.parametrize('change', ['operation', 'configuration', 'unknown', 'timeout', 'claim'])
def test_unproven_release_keeps_host_reserved(host, change):
    from recovery_engine import write
    config, request, root, directory = host
    admission.reserve(config, request, root)
    result = {'operationId': 'first', 'state': 'SUCCEEDED', 'actualExitCode': 0}
    exited = {'actualExitCode': 0, 'timedOut': False}
    if change == 'operation': request = dict(request, operationId='other')
    if change == 'configuration': config = dict(config, extra=True)
    if change == 'unknown': result['state'] = 'TERMINAL_UNKNOWN'
    if change == 'timeout': exited['timedOut'] = True
    if change == 'claim': (directory / 'active.json').write_text('{}', encoding='utf-8')
    with pytest.raises(RuntimeError):
        admission.release_success(config, request, root,
            write(root / 'worker-result.json', result), write(root / 'child-exit.json', exited))
    assert (directory / 'active.json').exists()


def test_symlink_host_directory_rejected(host, monkeypatch):
    config, request, root, directory = host
    link = directory.parent / 'link'; link.symlink_to(directory, target_is_directory=True)
    monkeypatch.setattr(admission, 'HOST_ROOT', link)
    with pytest.raises(RuntimeError, match='RESTORE_HOST_RESOURCE_ROOT_INVALID'):
        admission.reserve(config, request, root)


@pytest.mark.parametrize('stage', ['target', 'replacement'])
def test_child_admission_cannot_bypass_host_reservation(host, monkeypatch, stage):
    config, request, root, _ = host
    observed = []
    monkeypatch.setattr(admission, 'observe_resources', lambda *args: observed.append(True))
    with pytest.raises(RuntimeError, match='RESTORE_RESOURCE_OBSERVATION_FAILED'):
        REAL_ADMIT(config, request, root, stage)
    assert not observed


def test_resource_shortage_never_creates_active_reservation(host, monkeypatch):
    config, request, root, directory = host
    def reject(*args):
        raise admission.ResourceAdmissionError('RESTORE_MYSQL_MEMORY_INSUFFICIENT')
    monkeypatch.setattr(admission, 'admit', reject)
    with pytest.raises(RuntimeError, match='RESTORE_MYSQL_MEMORY_INSUFFICIENT'):
        admission.reserve(config, request, root)
    assert not (directory / 'active.json').exists()


def test_repeated_success_query_cannot_release_new_operation(host):
    from recovery_engine import write
    config, request, root, directory = host
    admission.reserve(config, request, root)
    result = write(root / 'worker-result.json', {'operationId': 'first', 'state': 'SUCCEEDED', 'actualExitCode': 0})
    exited = write(root / 'child-exit.json', {'actualExitCode': 0, 'timedOut': False})
    released = admission.release_success(config, request, root, result, exited)
    other = root.parent / 'second'; other.mkdir()
    admission.reserve(config, dict(request, operationId='second'), other)
    before = (directory / 'active.json').read_bytes()
    assert admission.release_success(config, request, root, result, exited) == released
    assert (directory / 'active.json').read_bytes() == before


@pytest.mark.parametrize('proven', [True, False])
def test_oom_release_requires_original_reservation_and_fresh_proof(host, proven):
    from recovery_engine import write, pin
    config, request, root, directory = host
    reference = admission.reserve(config, request, root)
    result = write(root / 'result.json', dict(operationId='first', state='TERMINAL_UNKNOWN',
        failureCode='FORMAL_SQL_IMPORT_STREAM_FAILED', originalResultPins=[reference]))
    proof = write(root / 'stopped-proof.json', {'stopped': True})
    calls = []
    def check():
        calls.append(True)
        if not proven: raise RuntimeError('WRITER_STILL_ACTIVE')
        return [proof]
    if proven:
        pins = admission.release_proven_oom(config, request, root, result, check)
        assert proof in pins and len(pins) == 2
        assert not (directory / 'active.json').exists()
        assert pin(Path(reference['path'])) == reference
    else:
        with pytest.raises(RuntimeError, match='WRITER_STILL_ACTIVE'):
            admission.release_proven_oom(config, request, root, result, check)
        assert (directory / 'active.json').exists()
    assert calls


def test_replacement_admission_binds_original_configuration(host, monkeypatch):
    from copy import deepcopy
    config, request, root, _ = host
    target = config['targets']['target']
    target.update(dataRoot=str(root / 'data'), replacement={'stateRoot': str(root / 'replacement')},
        resourceBudget=dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=1,
            hostAvailableMemoryBytes=1, diskBytesByPath={str(root): 1}))
    admission.reserve(config, request, root)
    effective = deepcopy(config)
    effective['targets']['target']['dataRoot'] = str(root / 'replacement/first/runtime')
    monkeypatch.setattr(admission, 'observe_resources', lambda conf, *args: dict(
        mysqlMemoryLimitBytes=2, hostAvailableMemoryBytes=2,
        disks=[dict(path=str(root), device=1, freeBytes=2)]))
    assert REAL_ADMIT(effective, request, root, 'target', reservation_configuration=config)['admitted']
    effective['targets']['target']['machineId'] = 'other'
    with pytest.raises(RuntimeError, match='RESTORE_REPLACEMENT_CONFIGURATION_CHANGED'):
        REAL_ADMIT(effective, request, root, 'target', reservation_configuration=config)


@pytest.mark.parametrize('unsafe', ['none', 'missing_flag', 'mutation', 'importer', 'replacement', 'timeout'])
def test_only_proven_nonmutating_failure_releases_host(host, unsafe):
    from recovery_engine import write
    config, request, root, directory = host
    admission.reserve(config, request, root)
    data = {'mutationDispatched': False}
    if unsafe == 'missing_flag': data = {}
    if unsafe == 'mutation': write(root / 'native-001.json', {'mutation': True, 'actualExitCode': 0})
    if unsafe == 'importer': write(root / 'importer-001.json', {'actualExitCode': 1})
    if unsafe == 'replacement':
        (root / 'replacement-preparation').mkdir()
        write(root / 'replacement-preparation/replacement-intent.json', {})
    result = write(root / 'worker-result.json', dict(operationId='first', state='FAILED_RETAINED',
        actualExitCode=1, data=data, originalResultPins=[]))
    exited = write(root / 'child-exit.json', dict(actualExitCode=1, timedOut=unsafe == 'timeout'))
    if unsafe == 'none':
        receipt = admission.release_no_mutation(config, request, root, result, exited)
        assert not (directory / 'active.json').exists()
        assert admission.release_no_mutation(config, request, root, result, exited) == receipt
    else:
        with pytest.raises(RuntimeError):
            admission.release_no_mutation(config, request, root, result, exited)
        assert (directory / 'active.json').exists()


@pytest.mark.parametrize('replacement_started', [False, True])
def test_worker_does_not_hide_prior_replacement_mutation(tmp_path, monkeypatch, replacement_started):
    from recovery_engine import load, write
    import recovery_minimal_worker as worker
    import recovery_minimal_runtime as runtime
    from types import SimpleNamespace
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='test', action='RESTORE',
        sourceConfigRef='source', targetConfigRef='target', parentChainRef=None, recoveryPointRef='full')
    config = write(tmp_path / 'config.json', {'operationsRoot': str(tmp_path)})
    ref = write(tmp_path / 'request.json', request)
    if replacement_started:
        (tmp_path / 'replacement-preparation').mkdir()
        write(tmp_path / 'replacement-preparation/replacement-intent.json', {})
    def fail(*args):
        error = RuntimeError('UNIT_ADMISSION_FAILURE')
        error.native = SimpleNamespace(mutation_dispatched=False, last_exit=None, original_pins=[])
        raise error
    monkeypatch.setattr(runtime, 'execute', fail)
    output = tmp_path / 'worker-result.json'
    worker.main(['--configuration', config['path'], '--request', ref['path'], '--output', str(output)])
    assert load(output)['data']['mutationDispatched'] is replacement_started


def test_owner_releases_explicit_nonmutating_worker_failure(host, monkeypatch):
    from recovery_engine import pin, write
    from recovery_minimal_worker import operation_result
    import recovery_minimal as owner
    config, _, root, directory = host
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='original', action='RESTORE',
        sourceConfigRef='source', targetConfigRef='target', parentChainRef=None, recoveryPointRef='full')
    config.update(operationsRoot=str(root / 'operations'), pythonPin=pin(Path(sys.executable).resolve()),
                  deadlineMilliseconds=1000)
    def child(argv, operation, seconds):
        receipt = dict(actualExitCode=1, timedOut=False)
        value = operation_result(request, '2026-10-26T00:00:00Z', 'FAILED_RETAINED',
            'UNIT_ADMISSION_FAILURE', dict(mutationDispatched=False), [], 1)
        write(operation / 'worker-result.json', value)
        return receipt, write(operation / 'child-exit.json', receipt)
    monkeypatch.setattr(owner, 'run_child', child)  # Explicit unit worker result, no server execution.
    config_pin = write(root / 'config.json', config)
    request_pin = write(root / 'request.json', request)
    result = owner.run(config_pin['path'], request_pin['path'], str(root / 'output.json'))
    assert result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'UNIT_ADMISSION_FAILURE'
    assert not (directory / 'active.json').exists()
    assert any(Path(ref['path']).name == 'resource-no-mutation-release.json' for ref in result['originalResultPins'])
