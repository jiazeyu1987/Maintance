"""Explicit cancellation receipts using real files and observed child exits."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_repository_root_identity import configured
import repository_minimal as repository
from repository_records import RepositoryError, canonical, pin_file

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Linux process observation required')


def put(path, value):
    path.write_bytes(canonical(value))


@pytest.fixture
def cancelled(configured):
    config, request, operation = configured
    request = dict(request, action='FULL')
    put(operation / 'request.json', request)
    put(operation / 'start.json', dict(configurationPin=config.pin, readbackOnly=False,
                                      startedAt='2026-10-21T00:00:00Z'))
    process = subprocess.Popen([sys.executable, '-c', 'pass'])
    pid = process.pid
    process.wait(timeout=10)
    put(operation / 'worker-process.json', dict(pid=pid, operationId=request['operationId']))
    observation = dict(pid=pid, operationId=request['operationId'], signal='SIGTERM',
        authorizedByUser=True, processStartTicks='recorded-ticks', processObservedExited=True,
        originalTerminalResultPresent=False, actualProcessExitCode=None)
    for name in ('external-stop-intent.json', 'external-stop-observation.json'):
        put(operation / name, observation)
    capture = config.staging / request['operationId']
    capture.mkdir()
    put(capture / 'worker-started.json', dict(pid=pid))
    put(capture / 'source-restoration.json', dict(schemaVersion='minimal-capture-source-restoration/v1',
        restored=True, errors=[]))
    put(capture / 'worker-completion.json', dict(schemaVersion='minimal-capture-worker-completion/v1',
        operationId=request['operationId'], data=dict(captureRoot=str(capture),
        sourceRestorationPin=pin_file(capture / 'source-restoration.json'))))
    return config, request, operation, capture


def test_explicit_cancellation_is_failure_with_unobserved_exit_and_pinned_evidence(cancelled):
    config, request, operation, capture = cancelled
    result = repository.reconcile_cancelled_worker(operation)
    assert result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'REPOSITORY_ARCHIVE_CANCELLED_BY_OPERATOR'
    assert result['actualExitCode'] is None
    assert result['data']['originalWorkerResultProduced'] is False
    assert result['data']['archiveCreated'] is False
    assert result['data']['restoreExecuted'] is False
    assert json.loads((operation / 'result.json').read_bytes()) == result
    assert (capture / 'worker-completion.json').exists()
    assert not list(config.archives.iterdir())
    for reference in result['originalResultPins']:
        assert pin_file(reference['path']) == reference


def test_actual_administrative_cli_reports_cancellation_without_backup_success(cancelled):
    _, _, operation, _ = cancelled
    command = subprocess.run([sys.executable, '-B', repository.__file__,
        '--reconcile-cancelled-worker', str(operation)], capture_output=True, timeout=15)
    assert command.returncode == 0, command.stderr.decode()
    reply = json.loads(command.stdout)
    assert reply == dict(state='FAILED_RETAINED',
        failureCode='REPOSITORY_ARCHIVE_CANCELLED_BY_OPERATOR', actualExitCode=None)


@pytest.mark.parametrize('change,code', [
    ('worker_alive', 'REPOSITORY_CANCEL_WORKER_STILL_RUNNING'),
    ('capture_alive', 'REPOSITORY_CANCEL_CAPTURE_STILL_RUNNING'),
    ('partial_archive', 'REPOSITORY_CANCEL_ARCHIVE_REQUIRES_RECONCILIATION'),
    ('existing_result', 'REPOSITORY_CANCEL_RESULT_EXISTS'),
    ('unapproved', 'REPOSITORY_CANCEL_OBSERVATION_INVALID'),
    ('wrong_operation', 'REPOSITORY_CANCEL_OBSERVATION_INVALID'),
    ('restoration_changed', 'REPOSITORY_CANCEL_SOURCE_NOT_RESTORED'),
    ('not_restored', 'REPOSITORY_CANCEL_SOURCE_NOT_RESTORED'),
])
def test_unproven_cancellation_retains_original_state(cancelled, change, code):
    config, request, operation, capture = cancelled
    def edit(path, **changes):
        value = json.loads(path.read_bytes())
        put(path, dict(value, **changes))
    if change == 'worker_alive':
        for name in ('worker-process.json', 'external-stop-intent.json', 'external-stop-observation.json'):
            edit(operation / name, pid=os.getpid())
    elif change == 'capture_alive':
        edit(capture / 'worker-started.json', pid=os.getpid())
    elif change == 'partial_archive':
        (config.archives / ('prod-' + operation.name)).mkdir()
    elif change == 'existing_result':
        put(operation / 'result.json', dict(original=True))
    elif change == 'unapproved':
        edit(operation / 'external-stop-intent.json', authorizedByUser=False)
    elif change == 'wrong_operation':
        edit(operation / 'external-stop-observation.json', operationId='another-operation')
    elif change == 'restoration_changed':
        edit(capture / 'source-restoration.json', extra='changed')
    elif change == 'not_restored':
        edit(capture / 'source-restoration.json', restored=False)
        completion = json.loads((capture / 'worker-completion.json').read_bytes())
        completion['data']['sourceRestorationPin'] = pin_file(capture / 'source-restoration.json')
        put(capture / 'worker-completion.json', completion)
    before = (operation / 'result.json').read_bytes() if (operation / 'result.json').exists() else None
    with pytest.raises(RepositoryError, match=code):
        repository.reconcile_cancelled_worker(operation)
    after = (operation / 'result.json').read_bytes() if (operation / 'result.json').exists() else None
    assert after == before
