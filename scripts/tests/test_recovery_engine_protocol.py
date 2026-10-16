"""Local protocol checks only; no database/NAS recovery is simulated."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import Budget, InvocationRunner, RecoveryError, check_pin, parse, pin, write
from recovery_engine_state import FileLock, Journal


def test_pin_rehashes_exact_bytes(tmp_path):
    path = tmp_path/'original'; path.write_bytes(b'original')
    ref = pin(path); assert check_pin(ref) == b'original'
    path.write_bytes(b'changed!')
    with pytest.raises(RecoveryError, match='PIN_CHANGED'): check_pin(ref)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_ambiguous_json_is_rejected(raw):
    with pytest.raises(RecoveryError): parse(raw)


@pytest.mark.parametrize('bytes_value', [True, -1, 1.5])
def test_pin_byte_count_is_integer_not_boolean(tmp_path, bytes_value):
    path = tmp_path/'original'; path.write_bytes(b'x'); ref = pin(path); ref['bytes'] = bytes_value
    with pytest.raises(RecoveryError, match='PIN_INVALID'): check_pin(ref)


def test_second_target_lock_conflicts_and_unlocks(tmp_path):
    path = tmp_path/'target.lock'
    with FileLock(path):
        with pytest.raises(RecoveryError, match='RESOURCE_ALREADY_EXECUTING'):
            with FileLock(path): pass
    with FileLock(path): pass


def test_journal_never_replays_interrupted_request(tmp_path):
    request = {'requestId': 'req-1', 'operationId': 'op-1', 'action': 'RESTORE_EXECUTE'}
    journal = Journal(tmp_path, request); assert journal.begin() is None
    with pytest.raises(RecoveryError) as failure: Journal(tmp_path, request).begin()
    assert failure.value.unknown
    with pytest.raises(RecoveryError, match='REQUEST_ID_CONTENT_CONFLICT'):
        Journal(tmp_path, dict(request, action='CONTROLLED_CUTOVER')).begin()


def test_journal_returns_original_terminal_result(tmp_path):
    request = {'requestId': 'req-1', 'operationId': 'op-1'}
    journal = Journal(tmp_path, request); journal.begin()
    ref = write(tmp_path/'result.json', {'state': 'FAILED_RETAINED', 'failureCode': 'EXACT_FAILURE'})
    journal.finish(ref, 'FAILED_RETAINED')
    assert Journal(tmp_path, request).begin() == {'state': 'FAILED_RETAINED', 'failureCode': 'EXACT_FAILURE'}


def executor(tmp_path, text):
    path = tmp_path/'local-executor.py'; path.write_text(text, encoding='utf-8')
    return pin(Path(sys.executable)), pin(path)


@pytest.mark.parametrize('state,exit_code', [('SUCCEEDED', 0), ('FAILED_RETAINED', 1), ('TERMINAL_UNKNOWN', 2)])
def test_real_subprocess_preserves_exit_and_state(tmp_path, state, exit_code):
    python, script = executor(tmp_path,
        "import argparse,json,sys\np=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()\n"
        "r=json.load(open(a.request));r.update(state="+repr(state)+",data={'localProtocolOnly':True})\n"
        "json.dump(r,open(a.output,'w'));print('private stdout');sys.stderr.write('private stderr');sys.exit("+str(exit_code)+")\n")
    runner = InvocationRunner(tmp_path, Budget(5000)); request = {'operationId':'op', 'requestId':'req', 'action':'LOCAL_PROTOCOL'}
    if state == 'SUCCEEDED':
        result, ref = runner.run(python, script, request, guard=lambda: None)
        assert result['state'] == state and check_pin(ref)
    else:
        with pytest.raises(RecoveryError) as failure: runner.run(python, script, request, guard=lambda: None)
        assert failure.value.unknown == (state == 'TERMINAL_UNKNOWN')
    assert runner.actual_exit_code == exit_code
    assert not (tmp_path/'invocation-001'/'stdout').exists()
    assert not (tmp_path/'invocation-001'/'stderr').exists()
    assert any(Path(ref['path']).name == 'result.json' for ref in runner.original_pins)


def test_real_subprocess_timeout_is_unknown_even_after_kill(tmp_path):
    python, script = executor(tmp_path, 'import time;time.sleep(10)\n')
    runner = InvocationRunner(tmp_path, Budget(150))
    with pytest.raises(RecoveryError) as failure:
        runner.run(python, script, {'operationId':'op','requestId':'req','action':'LOCAL_PROTOCOL'}, guard=lambda: None)
    assert failure.value.unknown and runner.actual_exit_code is not None
    exit_record = json.loads((tmp_path/'invocation-001'/'exit.json').read_text())
    assert exit_record['timedOut'] and exit_record['remoteTerminalConfirmed'] is False


def test_exit_without_result_is_unknown(tmp_path):
    python, script = executor(tmp_path, 'raise SystemExit(1)\n')
    runner = InvocationRunner(tmp_path, Budget(5000))
    with pytest.raises(RecoveryError) as failure:
        runner.run(python, script, {'operationId':'op','requestId':'req','action':'LOCAL_PROTOCOL'}, guard=lambda: None)
    assert failure.value.unknown and failure.value.exit_code == 1


def test_client_zero_exit_does_not_override_terminal_verifier_failure(tmp_path):
    python,script=executor(tmp_path,
        "import argparse,json\np=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()\n"
        "r=json.load(open(a.request));r.update(state='SUCCEEDED',data={'localProtocolOnly':True});json.dump(r,open(a.output,'w'))\n")
    runner=InvocationRunner(tmp_path,Budget(5000))
    def verify(result,request):raise RecoveryError('REMOTE_ORIGINAL_MISSING')
    with pytest.raises(RecoveryError,match='EXECUTOR_REMOTE_TERMINAL_UNKNOWN') as failure:
        runner.run(python,script,dict(operationId='op',requestId='req',action='LOCAL_PROTOCOL'),guard=lambda:None,terminal_verifier=verify)
    assert failure.value.unknown and runner.actual_exit_code == 0
    assert not (tmp_path/'invocation-001'/'exit.json').exists()
    assert (tmp_path/'invocation-001'/'client-exit.json').exists()


def test_verified_terminal_original_keeps_original_client_exit(tmp_path):
    python,script=executor(tmp_path,
        "import argparse,json\np=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()\n"
        "r=json.load(open(a.request));r.update(state='SUCCEEDED',data={'localProtocolOnly':True});json.dump(r,open(a.output,'w'))\n")
    proof=write(tmp_path/'local-protocol-proof.json',{'localProtocolOnly':True})
    runner=InvocationRunner(tmp_path,Budget(5000))
    runner.run(python,script,dict(operationId='op',requestId='req',action='LOCAL_PROTOCOL'),guard=lambda:None,
               terminal_verifier=lambda result,request:(True,[proof]))
    terminal=parse((tmp_path/'invocation-001'/'exit.json').read_bytes())
    assert terminal['remoteTerminalConfirmed'] is True and terminal['remoteTerminalProofPins'] == [proof]
    assert check_pin(terminal['localExitPin']) == (tmp_path/'invocation-001'/'client-exit.json').read_bytes()
    assert len([ref for ref in runner.original_pins if Path(ref['path']).name == 'exit.json']) == 1
