"""Independent review reproductions; file protocols, not database/E2E success.

History tests use actual pinned metadata, terminal ledger files and loopback HTTP.
The observation fixture deliberately does not claim a live MySQL observation.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import subprocess
import threading
import time
import urllib.request

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'backend/src/main/resources'), str(ROOT/'ops/recovery'),
               str(ROOT/'ops/spug'), str(Path(__file__).resolve().parent)]
import recovery_control_executor as executor
from recovery_control_smallapp import Ledger, canonical, fingerprint, local_read, persist, result
from recovery_control_smallapp_http import handler
from test_automatic_incremental_plan import MetadataFixture, ui_request
import smallapp_adapter


def overwrite_fixture(path, value):
    """Construct consistent immutable test originals before starting the reader."""
    path.write_bytes(canonical(value)); path.chmod(0o600)
    return executor.pin(path)


def completed_history(root, count=24):
    fixture = MetadataFixture(root)
    ledger = Ledger(root/'ledger', fixture.native)
    # A readback record pins a payload list, not the payload contents. Using a
    # shared real file makes repeated verification measurable without large disk
    # usage. No source SQL/image archive is ever passed as an originalResultPin.
    metadata = fixture.write('readback-original.json', dict(schemaVersion='RepositoryMinimumReadback/v1',
        payloadRefs=[], testPadding='x'*(1024*1024)))
    payload = root/'payload.sql'; payload.write_bytes(b'not-read-by-planner')
    payload_pin = executor.pin(payload)
    program = root/'recording-noop.py'; program.write_text('pass\n', encoding='utf-8'); program.chmod(0o600)
    python_pin, program_pin = executor.pin(Path(sys.executable).resolve()), executor.pin(program)
    owner_pin = fixture.native.configuration()['sourceConfigurations']['source-A']
    refs = []
    for index in range(count):
        ref = 'history-full-%04d' % index; refs.append(ref)
        stamp = datetime(2026, 11, 6, tzinfo=timezone.utc) + timedelta(minutes=index)
        fixture.point(ref, finished=stamp.isoformat().replace('+00:00', 'Z'))
        output_path = root/ref/'operation.json'
        output = local_read(output_path)
        output['startedAt'] = '2026-11-06T00:00:00Z'
        output['originalResultPins'].append(metadata)
        # A nested payload reference confirms that ordinary terminal reconcile
        # does not recursively re-hash SQL/tar content.
        point_path = root/ref/'point.json'
        point = local_read(point_path); point['payloadRefs'] = [payload_pin]
        point_pin = overwrite_fixture(point_path, point)
        repository_path = root/ref/'repository-binding.json'
        repository = local_read(repository_path); repository['repositoryPointPin'] = point_pin
        output['data']['repositoryBindingPin'] = overwrite_fixture(repository_path, repository)
        output['data']['pointPin'] = point_pin
        output_pin = overwrite_fixture(output_path, output)
        binding_path = root/ref/'control-binding.json'
        binding = local_read(binding_path); binding['resultPin'] = output_pin
        binding_pin = overwrite_fixture(binding_path, binding)
        overwrite_fixture(root/'registry/points'/(ref+'.pin.json'), binding_pin)
        value = ui_request(ref)
        selection = dict(ownerConfigurationPin=owner_pin, ownerProgramPin=program_pin,
                         configurationPin=fixture.native.config_pin)
        ledger.reserve(value, selection)
        directory = root/'ledger'/ref
        execute = directory/'execute'; execute.mkdir(mode=0o700)
        stdout, stderr = execute/'native-stdout', execute/'native-stderr'
        request_pin = executor.pin(directory/'request.json')
        argv = [python_pin['path'], program_pin['path'], '--configuration', owner_pin['path'],
                '--request', request_pin['path'], '--output', str(output_path)]
        intent = dict(operationId=ref, requestId=ref, requestPin=request_pin, configurationPin=owner_pin,
            pythonPin=python_pin, programPin=program_pin, argv=argv, restoreTargetPin=None)
        persist(execute/'native-intent.json', intent)
        intent_pin = executor.pin(execute/'native-intent.json')
        # The actual child is an explicit no-op, proving only the process/exit
        # protocol. The backup metadata above remains a unit-test fixture.
        with stdout.open('xb') as out, stderr.open('xb') as err:
            stdout.chmod(0o600); stderr.chmod(0o600)
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            persist(execute/'native-process.json', dict(operationId=ref, requestId=ref,
                intentPin=intent_pin, pid=child.pid,
                bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()
                    if sys.platform == 'linux' else None))
            code = child.wait(timeout=10)
        assert code == 0
        terminal = dict(operationId=ref, requestId=ref, actualExitCode=0,
            requestPin=request_pin, resultPin=output_pin, intentPin=intent_pin, pid=child.pid,
            timedOut=False, stdoutPin=executor.pin(stdout), stderrPin=executor.pin(stderr))
        persist(execute/'native-original-exit.json', terminal)
        persist(directory/'completion.json', dict(operationId=ref, uiRequestSha256=fingerprint(value),
            selection=selection, result=result(value, 'SUCCEEDED'), terminal=terminal))
    return fixture, ledger, metadata, payload, refs


def measure_http_plan(root, monkeypatch):
    fixture, ledger, metadata, payload, refs = completed_history(root)
    calls = Counter(); sizes = Counter(); elapsed = Counter()
    read = executor.pinned_read
    def measured(path, *args, **kwargs):
        started = time.monotonic()
        answer = read(path, *args, **kwargs)
        key = str(Path(path))
        calls[key] += 1; sizes[key] += answer[0]['bytes']
        elapsed[key] += time.monotonic() - started
        return answer
    monkeypatch.setattr(executor, 'pinned_read', measured)
    authorization = 'Bearer ' + 'a'*48
    auth = root/'http-auth.json'; persist(auth, dict(headers=dict(Authorization=authorization)))
    config = dict(authCredentialRef=dict(path=str(auth), uid=0, gid=0, mode=0o600),
                  allowedClientAddresses=['127.0.0.1'])
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(ledger, config))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    bridge = smallapp_adapter.HttpBridge.__new__(smallapp_adapter.HttpBridge)
    bridge.headers = dict(Authorization=authorization); bridge.requests = []
    bridge.source_refs = {'source-A'}; bridge.selected_target = None
    bridge.origin = ('http', '127.0.0.1', server.server_port)
    bridge.selection_url = 'http://127.0.0.1:%s/selections' % server.server_port
    real_opener = urllib.request.build_opener()
    timeouts = []
    class ObservedOpener:
        def open(self, request, *, timeout):
            timeouts.append(timeout)
            return real_opener.open(request, timeout=timeout)
    bridge.opener = ObservedOpener()
    started = time.monotonic()
    try:
        plan = bridge.incremental_plan('source-A')
    finally:
        duration = time.monotonic()-started
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    assert plan['state'] == 'READY', plan
    assert plan['parentChainRef'] == refs[-1]
    assert calls[str(payload)] == 0, 'review must not confuse metadata hashing with SQL payload hashing'
    return dict(historyCount=len(refs), pinReadCalls=sum(calls.values()),
        readBytes=sum(sizes.values()), readbackReads=calls[str(Path(metadata['path']))],
        readbackBytes=sizes[str(Path(metadata['path']))], elapsedSeconds=duration,
        pinnedReadSeconds=sum(elapsed.values()), bridgeTimeout=timeouts[0])


def test_planning_does_not_repeat_terminal_readback_for_every_old_generation(tmp_path, monkeypatch):
    measured = measure_http_plan(tmp_path, monkeypatch)
    print(json.dumps(measured, sort_keys=True))
    # Only the selected current generation needs expensive original readback
    # validation at admission; previously certified terminal generations must
    # not cause unbounded synchronous re-hashing on every button preview.
    assert measured['readbackReads'] <= 2, measured


def test_http_budget_leaves_time_after_metadata_for_the_supported_live_probe(tmp_path, monkeypatch):
    measured = measure_http_plan(tmp_path, monkeypatch)
    print(json.dumps(measured, sort_keys=True))
    # The production probe permits a 10-second query budget. This test measures
    # real history IO and the real bridge budget, without sleeping or fabricating
    # a network timeout. Equal inner/outer budgets cannot cover both stages.
    maximum_live_probe_seconds = 10
    assert measured['bridgeTimeout'] > maximum_live_probe_seconds + measured['elapsedSeconds'], measured


@pytest.mark.skipif(sys.platform != 'linux', reason='actual flock and epoch publication require Linux')
@pytest.mark.parametrize('interruption', ['directory-open-failure', 'process-exit'])
@pytest.mark.parametrize('terminal_state', ['SUCCEEDED', 'FAILED_RETAINED'])
def test_terminal_receipt_survives_epoch_publication_interruption_without_restore_replay(
        tmp_path, monkeypatch, interruption, terminal_state):
    """Fault only the real store's terminal publication; never execute a restore."""
    from test_backup_epoch import policy, locked
    import recovery_backup_epoch as epoch
    value = policy(tmp_path)
    operation = 'restore-review-001'
    claim = tmp_path/'replacement-state'/operation
    claim.mkdir(parents=True, mode=0o700)
    receipt_path = claim/'replacement-result.json'
    intent_path = tmp_path/'replacement-intent.json'
    persist(intent_path, dict(schemaVersion='ReplacementBackupEpochIntent/v1', operationId=operation,
        databaseUuid=value['databaseUuid'], targetConfigRef='target-review',
        replacementReceiptPath=str(receipt_path)))
    intent_pin = executor.pin(intent_path)
    with locked(value) as fd:
        epoch.initialize(value, fd)
        started = epoch.begin_restore(value, operation, fd, intent_pin=intent_pin)
        # This is an immutable terminal-evidence fixture, not proof that this
        # unit test performed a real database or container restore.
        persist(receipt_path, dict(state=terminal_state, operationId=operation,
            targetConfigRef='target-review', databaseUuid=value['databaseUuid']))
        receipt_pin = executor.pin(receipt_path)
        intended = 'READY' if terminal_state == 'SUCCEEDED' else 'FAILED_RETAINED'
        if interruption == 'directory-open-failure':
            actual_open = epoch.os.open
            def fail_terminal_directory(path, *args, **kwargs):
                if Path(path) == Path(value['root']):
                    raise OSError('INJECTED_TERMINAL_PUBLICATION_FAILURE')
                return actual_open(path, *args, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(epoch.os, 'open', fail_terminal_directory)
                with pytest.raises(OSError, match='INJECTED_TERMINAL_PUBLICATION_FAILURE'):
                    epoch.complete_restore(value, operation, started['epochId'], intended, receipt_pin, fd)
    if interruption == 'process-exit':
        script = '''
import fcntl, json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import recovery_backup_epoch as epoch
policy, operation, epoch_id, state, receipt = json.loads(sys.argv[2])
fd = os.open(policy['sourceLockPath'], os.O_RDWR)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
actual_open = os.open
def interrupted_open(path, *args, **kwargs):
    if Path(path) == Path(policy['root']):
        os._exit(73)
    return actual_open(path, *args, **kwargs)
epoch.os.open = interrupted_open
epoch.complete_restore(policy, operation, epoch_id, state, receipt, fd)
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT/'ops/recovery'),
            json.dumps([value, operation, started['epochId'], intended, receipt_pin])],
            capture_output=True, timeout=15)
        assert child.returncode == 73, child.stderr.decode('utf-8', errors='replace')
    assert epoch.read_current(value)['state'] == 'REPLACING'
    # A restarted process must safely finalize proven originals while holding
    # the same physical lock. It must not replay the operation or rewrite data.
    with locked(value) as fd:
        recovered = epoch.reconcile_completed_restore(value, fd)
        assert recovered['state'] == intended
        assert recovered['epochId'] == started['epochId']
        assert recovered == epoch.reconcile_completed_restore(value, fd)
    assert executor.pin(intent_path) == intent_pin
    assert executor.pin(receipt_path) == receipt_pin
    assert len(list(Path(value['root']).iterdir())) == 3


@pytest.mark.skipif(sys.platform != 'linux', reason='actual flock and epoch publication require Linux')
@pytest.mark.parametrize('evidence', ['missing', 'wrong-target', 'wrong-database'])
def test_epoch_reconcile_never_guesses_missing_or_unbound_terminal(tmp_path, evidence):
    from test_backup_epoch import policy, locked
    import recovery_backup_epoch as epoch
    value = policy(tmp_path); operation = 'restore-review-002'
    claim = tmp_path/'replacement-state'/operation; claim.mkdir(parents=True, mode=0o700)
    receipt_path = claim/'replacement-result.json'
    intent_path = tmp_path/'replacement-intent.json'
    persist(intent_path, dict(schemaVersion='ReplacementBackupEpochIntent/v1', operationId=operation,
        databaseUuid=value['databaseUuid'], targetConfigRef='target-review',
        replacementReceiptPath=str(receipt_path)))
    with locked(value) as fd:
        epoch.initialize(value, fd)
        started = epoch.begin_restore(value, operation, fd, intent_pin=executor.pin(intent_path))
        if evidence != 'missing':
            persist(receipt_path, dict(state='SUCCEEDED', operationId=operation,
                targetConfigRef='other-target' if evidence == 'wrong-target' else 'target-review',
                databaseUuid='00000000-0000-0000-0000-000000000000' if evidence == 'wrong-database' else value['databaseUuid']))
        try:
            observed = epoch.reconcile_completed_restore(value, fd)
            assert observed['state'] == 'REPLACING'
        except ValueError as error:
            assert str(error).startswith('BACKUP_EPOCH_')
        assert epoch.read_current(value) == started
        assert len(list(Path(value['root']).iterdir())) == 2
