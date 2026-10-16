"""Legacy journal guard engineering checks; no business runtime is invoked."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from test_recovery_environment_fixtures import LocalRecords, MODULE
from test_w05_static_repair_r5 import runtime, fail_operation
import recovery_environment as environment
from recovery_environment_contract import EnvironmentFailure, atomic_json, digest, pin_file, read_pin


def target_key(records):
    identity = read_pin(records.config['targetIdentityPin'])
    return digest({'targetId': records.config['targetId'], 'machineId': identity['machineId'],
                   'dockerEngineId': identity['dockerEngineId']})


def snapshot(records):
    return {str(path): path.read_bytes() for name in ('evidence', 'journal', 'private')
            for path in (records.root / name).rglob('*.json')}


def prohibit_dispatch(monkeypatch):
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        pytest.fail('Journal rejection must precede runner/runtime construction')
    monkeypatch.setattr(environment, 'CommandRunner', forbidden)
    return forbidden, calls


def assert_guard(records, monkeypatch, code):
    before = snapshot(records)
    forbidden, calls = prohibit_dispatch(monkeypatch)
    with pytest.raises(EnvironmentFailure) as error:
        environment.run_operation(records.request, records.trust, time.monotonic() + 20,
                                  runtime_factory=forbidden)
    assert error.value.code == code and error.value.unknown is True
    assert not calls and snapshot(records) == before
    return error.value


@pytest.mark.parametrize('state', ['RUNNING', 'TERMINAL_UNKNOWN'])
@pytest.mark.parametrize('request_id', [None, 'earlier-request'])
def test_same_target_uncertain_request_blocks_before_identity_lookup_or_dispatch(tmp_path, monkeypatch, state, request_id):
    records = LocalRecords(tmp_path)
    prior = {'targetKey': target_key(records), 'state': state}
    if request_id is not None:
        prior['requestId'] = request_id
    atomic_json(Path(records.config['journalRoot']) / 'request-earlier.json', prior)
    assert_guard(records, monkeypatch, 'TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN')
    assert not list((tmp_path / 'evidence').iterdir()) and not list((tmp_path / 'private').iterdir())


@pytest.mark.parametrize('state', ['RUNNING', 'TERMINAL_UNKNOWN', 'SUCCEEDED'])
@pytest.mark.parametrize('identity', ['missing', None, '', 0, True, [], 'not-a-target', 'A' * 64, 'a' * 63])
def test_unbound_or_invalid_prior_target_identity_never_admits(tmp_path, monkeypatch, state, identity):
    records = LocalRecords(tmp_path)
    prior = {'requestId': 'earlier-request', 'state': state}
    if identity != 'missing':
        prior['targetKey'] = identity
    atomic_json(Path(records.config['journalRoot']) / 'request-earlier.json', prior)
    code = 'LEGACY_UNCERTAIN_TARGET_IDENTITY_REQUIRED' if identity == 'missing' else 'LEGACY_JOURNAL_TARGET_IDENTITY_INVALID'
    assert_guard(records, monkeypatch, code)


@pytest.mark.parametrize('state', ['RUNNING', 'TERMINAL_UNKNOWN'])
def test_valid_other_target_uncertainty_does_not_block_this_target(tmp_path, monkeypatch, state):
    records = LocalRecords(tmp_path)
    other_target = digest({'independentTarget': 'other-target'})
    assert other_target != target_key(records)
    prior = Path(records.config['journalRoot']) / 'request-other.json'
    atomic_json(prior, {'targetKey': other_target, 'state': state})
    before = prior.read_bytes()
    calls = []
    class ReachedRunner(Exception):
        pass
    def runner(*args, **kwargs):
        calls.append(True)
        raise ReachedRunner()
    monkeypatch.setattr(environment, 'CommandRunner', runner)
    with pytest.raises(ReachedRunner):
        environment.run_operation(records.request, records.trust, time.monotonic() + 20)
    assert calls == [True] and prior.read_bytes() == before
    assert not list((tmp_path / 'evidence').rglob('invocation-*.json'))


@pytest.mark.parametrize('state', ['RUNNING', 'TERMINAL_UNKNOWN'])
def test_real_cli_reports_typed_unknown_for_missing_prior_request_id(tmp_path, state):
    records = LocalRecords(tmp_path)
    atomic_json(Path(records.config['journalRoot']) / 'request-earlier.json',
                {'targetKey': target_key(records), 'state': state})
    before = snapshot(records)
    request_pin = records.write('cli-request.json', records.request)
    output = tmp_path / 'cli-result.json'
    child = subprocess.run([sys.executable, '-I', str(MODULE / 'environment_cli.py'),
                            '--request', request_pin['path'], '--output', str(output)],
        capture_output=True, timeout=20, env={**os.environ,
            'RECOVERY_ENVIRONMENT_TRUST_FILE': records.trust_pin['path'],
            'RECOVERY_ENVIRONMENT_TRUST_SHA256': records.trust_pin['sha256'], 'PYTHONDONTWRITEBYTECODE': '1'})
    result = json.loads(output.read_text(encoding='utf-8'))
    assert child.returncode == 2 and child.stdout == child.stderr == b''
    assert result['state'] == 'TERMINAL_UNKNOWN' and result['failureCode'] == 'TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN'
    assert result['actualExitCode'] is None and result['data'] is None and result['originalResultPins'] == []
    records.trust.schemas.validate(result, 'OperationResult')
    assert snapshot(records) == before
    assert not list((tmp_path / 'evidence').iterdir()) and not list((tmp_path / 'private').iterdir())
    atomic_json(tmp_path / 'cli-process-receipt.json', {'argv': child.args, 'actualExitCode': child.returncode,
        'stdout': child.stdout.decode(), 'stderr': child.stderr.decode(), 'resultPin': pin_file(output),
        'businessDispatchObserved': False})


def completed_prior_request(tmp_path, monkeypatch):
    records = LocalRecords(tmp_path)
    # Existing engineering seam yields a real FAILED_RETAINED commit, with no
    # business process or daemon. The actual journal/confirmation code runs.
    monkeypatch.setattr(environment, 'prepare_target', fail_operation)
    first = environment.run_operation(records.request, records.trust, time.monotonic() + 20,
                                      runtime_factory=runtime)
    assert first['state'] == 'FAILED_RETAINED' and first['failureCode'] == 'UNIT_PRE_DISPATCH_FAILURE'
    key = hashlib.sha256(records.request['requestId'].encode()).hexdigest()
    journal = Path(records.config['journalRoot']) / ('request-' + key + '.json')
    operation = Path(records.config['evidenceRoot']) / ('request-' + key)
    # Deliberately model the legacy installation without the newer target
    # journal; preserve all request-level terminal original proofs.
    (Path(records.config['journalRoot']) / ('target-' + target_key(records) + '.json')).unlink()
    records.request['requestId'] = 'next-request'
    return records, journal, operation


def test_valid_terminal_legacy_request_checks_confirmation_before_next_operation(tmp_path, monkeypatch):
    records, journal, operation = completed_prior_request(tmp_path, monkeypatch)
    prior_files = {str(path): path.read_bytes() for path in operation.rglob('*.json')}
    prior_files[str(journal)] = journal.read_bytes()
    confirmed = environment.confirmed_terminal
    calls = []
    def observe(*args):
        calls.append(args[0]['requestId'])
        return confirmed(*args)
    monkeypatch.setattr(environment, 'confirmed_terminal', observe)
    result = environment.run_operation(records.request, records.trust, time.monotonic() + 20,
                                       runtime_factory=runtime)
    assert result['state'] == 'FAILED_RETAINED' and calls == ['unit-request']
    assert all(Path(path).read_bytes() == raw for path, raw in prior_files.items())


@pytest.mark.parametrize('fault', ['missing-confirmation', 'missing-intent', 'tampered-original',
                                  'missing-original', 'terminal-failure-file'])
def test_terminal_or_fault_originals_remain_strict_before_new_dispatch(tmp_path, monkeypatch, fault):
    records, journal, operation = completed_prior_request(tmp_path, monkeypatch)
    expected = 'TERMINAL_COMMIT_CONFIRMATION_MISSING'
    if fault == 'missing-confirmation':
        (operation / 'commit-confirmed.json').unlink()
    elif fault == 'missing-intent':
        (operation / 'commit-intent.json').unlink()
    elif fault in ('tampered-original', 'missing-original'):
        result = read_pin(read_pin(pin_file(journal))['resultPin'])
        original = Path(result['originalResultPins'][0]['path'])
        if fault == 'missing-original':
            original.unlink()
            expected = 'REQUIRED_PATH_MISSING'
        else:
            original.write_bytes(b'{"explicitEngineeringTamper":true}\n')
            expected = 'ARCHIVE_PIN_MISMATCH'
    else:
        (operation / 'terminal-commit-failure.json').write_bytes(b'{"unconfirmedFaultOriginal":true}\n')
        expected = 'TARGET_TERMINAL_COMMIT_NOT_CONFIRMED'
    assert_guard(records, monkeypatch, expected)
