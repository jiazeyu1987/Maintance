"""Local Linux evidence tests, not a Docker or business rehearsal."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend/src/main/resources'))
import recovery_control_executor as executor
from recovery_control_smallapp import canonical, fingerprint
from recovery_control_smallapp_native import Native

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='actual Linux proc evidence required')


def put(path, value):
    path.write_bytes(canonical(value))
    path.chmod(0o600)
    return executor.pin(path)


@pytest.fixture
def evidence(tmp_path):
    operation = tmp_path / 'control'
    execute = operation / 'execute'
    execute.mkdir(parents=True, mode=0o700)
    root = tmp_path / 'owner'
    root.mkdir(mode=0o700)
    value = {'operationId': 'test-import', 'action': 'RESTORE'}
    request = put(operation / 'request.json', value)
    intent = put(execute / 'native-intent.json', dict(operationId=value['operationId'],
        requestId=value['operationId'], requestPin=request))
    child = subprocess.Popen([sys.executable, '-c', 'pass'])
    child.wait(timeout=10)
    pid = child.pid
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    put(execute / 'native-process.json', dict(operationId=value['operationId'],
        requestId=value['operationId'], intentPin=intent, pid=pid, bootId=boot))
    put(execute / 'native-original-exit.json', dict(operationId=value['operationId'],
        requestId=value['operationId'], requestPin=request, intentPin=intent,
        pid=pid, actualExitCode=2))
    child_pin = put(root / 'child-exit.json', dict(actualExitCode=2, timedOut=False))
    call = dict(schemaVersion='RecoveryDataInvocation/v1', operationId=value['operationId'],
        argvSha256=fingerprint(['test-inactive-command']), actualExitCode=0,
        finishedAt='2026-10-25T00:00:00Z', mutation=True)
    importer = dict(schemaVersion='RecoverySqlImporter/v1',
        argvSha256=fingerprint(['test-inactive-importer']), actualExitCode=137,
        finishedAt='2026-10-25T00:00:01Z')
    refs = [put(root / 'native-001.json', call), child_pin, put(root / 'importer-002.json', importer)]
    output = dict(actualExitCode=2, originalResultPins=refs)
    return Native.__new__(Native), value, operation, root, output


def check(evidence):
    native, value, operation, root, output = evidence
    return native.stopped_import_processes(value, operation, root, output)


def test_complete_exit_evidence_preserves_files(evidence):
    root = evidence[2].parent
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    pins = check(evidence)
    assert pins and all(executor.verify(ref).is_file() for ref in pins)
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('change', ['boot', 'pid', 'request', 'intent', 'child', 'child_unpinned', 'pending', 'pin', 'unlisted'])
def test_incomplete_or_changed_evidence_cannot_release_operation(evidence, change):
    _, _, operation, root, output = evidence
    path = operation / 'execute/native-process.json'
    row = executor.document(executor.pin(path))
    if change == 'boot':
        row['bootId'] = 'another-boot'
    elif change == 'pid':
        row['pid'] = os.getpid()
        exited_path = operation / 'execute/native-original-exit.json'
        exited = executor.document(executor.pin(exited_path))
        exited['pid'] = os.getpid()
        put(exited_path, exited)
    elif change in ('request', 'intent'):
        put(operation / ('request.json' if change == 'request' else 'execute/native-intent.json'), {})
    elif change == 'child':
        put(root / 'child-exit.json', dict(actualExitCode=-9, timedOut=True))
    elif change == 'child_unpinned':
        output['originalResultPins'].pop(1)
    elif change in ('pending', 'pin', 'unlisted'):
        call = executor.document(output['originalResultPins'][0])
        call['actualExitCode'] = None
        reference = put(root / 'native-001.json', call)
        if change == 'pending':
            output['originalResultPins'][0] = reference
        if change == 'unlisted':
            put(root / 'native-003.json', call)
    put(path, row)
    with pytest.raises(RuntimeError):
        check(evidence)


def test_live_detached_writer_blocks_even_with_completed_receipt(evidence):
    argv = [sys.executable, '-c', 'import time; time.sleep(30)']
    child = subprocess.Popen(argv, start_new_session=True)
    try:
        reference = evidence[4]['originalResultPins'][0]
        row = executor.document(reference)
        row['argvSha256'] = fingerprint(argv)
        evidence[4]['originalResultPins'][0] = put(Path(reference['path']), row)
        with pytest.raises(RuntimeError, match='ORIGINAL_NATIVE_CALL_STILL_RUNNING'):
            check(evidence)
    finally:
        child.terminate()
        child.wait(timeout=10)


@pytest.mark.parametrize('action', ['FULL', 'RESTORE'])
def test_owner_records_boot_before_real_child_exit(tmp_path, action):
    program = tmp_path / 'owner.py'
    program.write_text("import pathlib,sys\npathlib.Path(sys.argv[-1]).write_bytes(b'{}')\n", encoding='utf-8')
    program.chmod(0o600)
    config = put(tmp_path / 'config.json', {})
    request = put(tmp_path / 'request.json', {'operationId': 'test-owner', 'action': action,
                                           'targetConfigRef': 'target'})
    before_pin = None
    if action == 'RESTORE':
        before_pin = put(tmp_path / 'restore-target-before.json', dict(operationId='test-owner',
            targetConfigRef='target', configurationPin=config))
    work = tmp_path / 'execute'
    work.mkdir(mode=0o700)
    terminal = executor.run_owner(executor.pin(Path(sys.executable).resolve()), executor.pin(program),
        config, request, work / 'result.json', environment={'PATH': '/usr/bin:/bin'},
        working_directory=str(tmp_path), deadline_milliseconds=10000)
    receipt = executor.document(executor.pin(work / 'native-process.json'))
    assert terminal['actualExitCode'] == 0
    assert receipt.get('bootId') == Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert not (Path('/proc') / str(receipt['pid'])).exists()
    intent = executor.document(receipt['intentPin'])
    assert intent['restoreTargetPin'] == before_pin
