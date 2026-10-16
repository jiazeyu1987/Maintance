"""R3 actual local write/child protocol faults; no native recovery acceptance."""
import hashlib
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
import recovery_cli as cli
import recovery_engine as engine
from recovery_engine import load, pin, pinned_json, write
from recovery_engine_read_guard import RepositoryReadGuard
from test_recovery_static_repair_r4 import local_executor, repository_fixture


@pytest.fixture
def local_cli_protocol(tmp_path, monkeypatch):
    # Keep the secondary receipt temporary path below the Windows path limit;
    # its intended injected os.replace fault must be reached, not masked by it.
    tmp_path = tmp_path.parent / ('p'+hashlib.sha256(tmp_path.name.encode()).hexdigest()[:8])
    tmp_path.mkdir(mode=0o700)
    request, _, policy = repository_fixture(tmp_path)
    evidence = tmp_path/'evidence'; evidence.mkdir(mode=0o700)
    identity = write(tmp_path/'identity.json', {'protocolOnly':'target'})
    policy.update(evidenceRoot=str(evidence),
        dataTargetPin=write(tmp_path/'target.json', {'targetIdentityPin':identity}),
        recordSchemasPin=write(tmp_path/'schema.json', {}))
    input_ref = write(tmp_path/'input.json', {'protocolOnly':True})
    request.update(action='RESTORE_EXECUTE', deadlineMilliseconds=5000,
        inputPins={'restorePlan':input_ref,'recoveryTarget':input_ref})
    request_pin = write(tmp_path/'request.json', request)
    output = tmp_path/'public-result.json'
    # These existing prerequisite fixtures are isolated state protocol, never
    # real authority or restore evidence. Journal/write/cache remain actual.
    monkeypatch.setattr(cli, 'trusted_configuration', lambda request:({},policy,{}))
    monkeypatch.setattr(cli, 'authorities', lambda *args:None)
    monkeypatch.setattr(cli, 'validate_record', lambda value,*args:value)
    if os.name != 'posix':
        monkeypatch.setattr(RepositoryReadGuard, 'child_options', lambda self,env,fds=():dict(env=env))
    python, script = local_executor(tmp_path, 'SUCCEEDED')
    operations = []
    def harmless_protocol_operation(operation):
        operations.append(operation)
        operation.runner.run(python, script, dict(operationId='op',requestId='req',action='PROTOCOL'), guard=lambda:None)
        return {'protocolOnly':True}
    monkeypatch.setattr(cli.RecoveryOperation, 'run', harmless_protocol_operation)
    return request, request_pin, evidence, output, operations


@pytest.mark.parametrize('confirmation', ['pin','linux-directory-fsync'])
@pytest.mark.parametrize('journal_correction_fails', [False, True], ids=['result-correction-fails','journal-correction-also-fails'])
def test_post_replace_success_journal_confirmation_failure_never_returns_success_cache(
        tmp_path, monkeypatch, local_cli_protocol, confirmation, journal_correction_fails):
    if confirmation == 'linux-directory-fsync' and sys.platform != 'linux':
        pytest.skip('Actual Linux directory fsync fault requires Linux; WSL/runtime execution not authorized')
    request, request_pin, evidence, output, operations = local_cli_protocol
    tmp_path = evidence.parent
    marker = tmp_path/'repo/.repository-control/recovery-read-guard.json'
    events = []
    actual_pin, actual_replace, actual_fsync = engine.pin, os.replace, os.fsync
    success = {}
    armed = True
    def confirmation_fault(path):
        journal = load(path)
        assert journal['state'] == 'SUCCEEDED'
        assert not marker.exists() and len(operations) == 1
        assert operations[0].runner.readers_terminal and operations[0].runner.actual_exit_code == 0
        # The replacement is actual and its exact result Pin is still readable.
        assert actual_pin(journal['resultPin']['path']) == journal['resultPin']
        success.update(journal=journal, result=load(journal['resultPin']['path']))
        assert success['result']['state'] == 'SUCCEEDED'
        events.append('successful-journal-replaced-confirmation-failed')
        raise OSError('ENGINEERING_POST_REPLACE_JOURNAL_CONFIRMATION_FAILURE')
    def pin_fault(path):
        if armed and confirmation == 'pin' and Path(path).name.startswith('request-') and load(path)['state'] == 'SUCCEEDED':
            return confirmation_fault(path)
        return actual_pin(path)
    def fsync_fault(fd):
        if armed and confirmation == 'linux-directory-fsync':
            actual, expected = os.fstat(fd), evidence.stat()
            if (actual.st_dev,actual.st_ino) == (expected.st_dev,expected.st_ino):
                journals = list(evidence.glob('request-*.json'))
                if journals and load(journals[0])['state'] == 'SUCCEEDED':
                    return confirmation_fault(journals[0])
        return actual_fsync(fd)
    def replace_fault(source, target):
        target = Path(target)
        if armed and success:
            if journal_correction_fails and target.name.startswith('request-') and load(source)['state'] == 'TERMINAL_UNKNOWN':
                events.append('unknown-journal-correction-failed-before-replace')
                raise OSError('ENGINEERING_UNKNOWN_JOURNAL_BEFORE_REPLACE_FAILURE')
            if target.name in ('operation-result.json','operation-result.json.recording-failure.json') and load(source)['state'] == 'TERMINAL_UNKNOWN':
                events.append('unknown-result-failed-before-replace' if target.name == 'operation-result.json' else 'unknown-secondary-receipt-failed-before-replace')
                raise OSError('ENGINEERING_UNKNOWN_RESULT_BEFORE_REPLACE_FAILURE')
        return actual_replace(source,target)
    monkeypatch.setattr(engine,'pin',pin_fault)
    monkeypatch.setattr(os,'fsync',fsync_fault)
    monkeypatch.setattr(os,'replace',replace_fault)
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 2
    armed = False
    if journal_correction_fails:
        assert events == ['successful-journal-replaced-confirmation-failed','unknown-journal-correction-failed-before-replace']
    else:
        assert events == ['successful-journal-replaced-confirmation-failed','unknown-result-failed-before-replace','unknown-secondary-receipt-failed-before-replace']
    result_path = next(evidence.glob('operation-*/operation-result.json'))
    journal_path = next(evidence.glob('request-*.json'))
    target_path = next(evidence.glob('target-*.state.json'))
    assert not marker.exists() and len(operations) == 1
    assert load(result_path) == success['result'] and load(result_path)['state'] == 'SUCCEEDED'
    assert load(target_path)['state'] == 'SUCCEEDED'  # No false claim of a completed correction.
    public = load(output)
    assert public['state'] == 'TERMINAL_UNKNOWN' and public['actualExitCode'] == 0
    assert public['originalResultPins'] == success['result']['originalResultPins']
    for ref in public['originalResultPins']: pinned_json(ref)
    receipt = load(next(result_path.parent.glob('invocation-*/exit.json')))
    assert receipt['nativePid'] > 0 and receipt['actualExitCode'] == 0
    journal = load(journal_path)
    if journal_correction_fails:
        assert journal == success['journal'] and journal['state'] == 'SUCCEEDED'
        assert pinned_json(journal['resultPin']) == success['result']
    else:
        assert journal['state'] == 'TERMINAL_UNKNOWN' and journal['resultPin'] is None
    before = result_path.read_bytes(), journal_path.read_bytes(), target_path.read_bytes()
    for new_output in (output,tmp_path/'different-public-result.json'):
        assert cli.main(['--request',request_pin['path'],'--output',str(new_output)]) == 2
        cached = load(new_output)
        assert cached['state'] == 'TERMINAL_UNKNOWN' and cached['actualExitCode'] == 0
        assert cached['failureCode'] == 'TERMINAL_PUBLICATION_RECONCILIATION_REQUIRED'
        assert cached['originalResultPins'] == public['originalResultPins']
        assert len(operations) == 1
        assert before == (result_path.read_bytes(),journal_path.read_bytes(),target_path.read_bytes())
    request['requestId'] = 'another-request-same-target'
    changed = write(tmp_path/'different-request.json',request)
    assert cli.main(['--request',changed['path'],'--output',str(output)]) == 1
    assert load(output)['failureCode'] == 'TARGET_ALREADY_RESTORED_NEW_VERSIONED_TARGET_REQUIRED'
    assert len(operations) == 1


def test_confirmed_success_cache_returns_exact_original_without_second_child(tmp_path, local_cli_protocol):
    _, request_pin, evidence, output, operations = local_cli_protocol
    tmp_path = evidence.parent
    assert cli.main(['--request',request_pin['path'],'--output',str(output)]) == 0
    result = load(output); original_public_pin = pin(output)
    journal_path = next(evidence.glob('request-*.json'))
    journal_bytes = journal_path.read_bytes(); journal = load(journal_path)
    assert result['state'] == journal['state'] == 'SUCCEEDED'
    assert journal['cacheEvidencePins'] == [journal['resultPin'],original_public_pin]
    assert result['originalResultPins'] and result['actualExitCode'] == 0
    assert not (tmp_path/'repo/.repository-control/recovery-read-guard.json').exists()
    for destination in (output,tmp_path/'new-success-output.json'):
        assert cli.main(['--request',request_pin['path'],'--output',str(destination)]) == 0
        assert load(destination) == result and len(operations) == 1
        assert journal_path.read_bytes() == journal_bytes and pin(output) == original_public_pin
