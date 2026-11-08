"""Release gates over real program history, reservation files and host locks.

The shared history fixture runs real local native/SQL processes and custody
journals. MySQL, worker and Docker-switch records remain explicit protocol unit
boundaries; no test claims a restored database or a live stopped target. The
stopped callback below models only the already separate control protocol.
"""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

from test_recovery_program_evidence import history_factory, unique
import test_recovery_program_evidence as history
from test_recovery_program_activation import locked
from recovery_backup_epoch import complete_restore, read_current
from recovery_engine import RecoveryError, pin, pinned_json, utc, write
import recovery_resource_admission as admission


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux program history, reservation and flock contracts')


def child_exit(h, code):
    """Real process exit used at the worker protocol boundary, no business I/O."""
    finished = subprocess.run([sys.executable, '-B', '-c', 'import sys;sys.exit('+str(code)+')'],
        check=False, capture_output=True, timeout=10)
    assert finished.returncode == code and not finished.stdout and not finished.stderr
    return write(h.e.root/'child-exit.json', dict(operationId=h.e.request['operationId'],
        actualExitCode=finished.returncode, timedOut=False, finishedAt=utc()))


def owner_result(h, *, worker_changes=None):
    worker = pinned_json(h.result_pin)
    worker.update(worker_changes or {})
    h.result_pin = write(h.e.root/'worker-result.json', worker)
    exited = child_exit(h, worker['actualExitCode'])
    output = deepcopy(worker)
    output['originalResultPins'] = unique([*worker['originalResultPins'], h.result_pin, exited])
    return write(h.e.root/'result.json', output), exited


def fixed_originals(h):
    references = (h.e.owner_pin, h.e.request_pin, h.e.operation_pin, h.e.reservation)
    return {Path(ref['path']): Path(ref['path']).read_bytes() for ref in references}


def refused(h, invoke):
    originals = fixed_originals(h)
    active = admission.HOST_ROOT/'active.json'
    before = active.read_bytes()
    with pytest.raises((RecoveryError, admission.ResourceAdmissionError),
            match='PROGRAM_EVIDENCE|RESTORE_RESOURCE|WORKER_'):
        invoke()
    assert active.read_bytes() == before
    assert all(path.read_bytes() == data for path, data in originals.items())
    assert not any((h.e.root/name).exists() for name in (
        'resource-release.json', 'resource-no-mutation-release.json',
        'resource-retained-failure-release.json', 'resource-oom-release.json'))


def stopped_protocol(h):
    """Explicit unit callback, not a fake kernel/MySQL readiness observation."""
    proof = write(h.e.root/'stopped-protocol.json', dict(
        schemaVersion='ResourceReleaseStoppedProtocolUnit/v1',
        operationId=h.e.request['operationId'], targetConfigRef=h.e.request['targetConfigRef']))
    calls = []
    def verify():
        calls.append(True)
        assert pin(Path(proof['path'])) == proof
        return [proof]
    return verify, calls, proof


def test_program_policy_cannot_be_bypassed_by_removing_success_data_fields(history_factory):
    h = history_factory()
    worker = pinned_json(h.result_pin)
    worker['data'] = {key: value for key, value in worker['data'].items()
                      if not key.startswith('program')}
    h.result_pin = write(h.e.root/'worker-result.json', worker)
    exited = child_exit(h, 0)
    refused(h, lambda: admission.release_success(h.e.owner, h.e.request, h.e.root, h.result_pin, exited))


def test_program_history_success_without_formal_data_success_does_not_release(history_factory):
    h = history_factory()
    assert h.native['phase'] == 'RESTORE' and h.native['generationPin'] is not None
    assert not h.native['terminalUnknown']
    # A complete historical native/custody proof is not the formal worker's
    # database/object/consistency/application success structure.
    assert 'applicationStartPin' not in pinned_json(h.result_pin)['data']
    exited = child_exit(h, 0)
    refused(h, lambda: admission.release_success(h.e.owner, h.e.request, h.e.root, h.result_pin, exited))


def test_program_not_started_no_mutation_release_is_proven_and_idempotent(history_factory):
    h = history_factory(outcome='not-started')
    originals = fixed_originals(h)
    exited = child_exit(h, 1)
    receipt = admission.release_no_mutation(h.e.owner, h.e.request, h.e.root, h.result_pin, exited)
    assert not (admission.HOST_ROOT/'active.json').exists()
    assert pinned_json(receipt)['reason'] == 'PROVEN_NO_MUTATION'
    assert admission.release_no_mutation(h.e.owner, h.e.request, h.e.root, h.result_pin, exited) == receipt
    assert all(path.read_bytes() == data for path, data in originals.items())


def test_real_context_without_native_mutation_is_not_a_not_started_release(history_factory):
    h = history_factory(outcome='constructor-before-custody')
    assert h.binding is not None and h.context is not None and h.native['invocations'] == []
    assert h.native['mutationDispatched'] is False
    exited = child_exit(h, 1)
    refused(h, lambda: admission.release_no_mutation(h.e.owner, h.e.request, h.e.root, h.result_pin, exited))


def test_no_mutation_cannot_hide_an_unknown_invocation_in_claim_runtime(history_factory):
    h = history_factory(outcome='not-started')
    runtime = h.e.claim/'runtime'; runtime.mkdir(mode=0o700)
    # Deliberately inconsistent protocol evidence: this intent must be found,
    # never interpreted as an actual successful process or silently ignored.
    write(runtime/'native-0001.json', dict(schemaVersion='RecoveryDataInvocation/v1',
        operationId=h.e.request['operationId'], action='RESTORE', mutation=True,
        state='TERMINAL_UNKNOWN', actualExitCode=None, finishedAt=None))
    exited = child_exit(h, 1)
    refused(h, lambda: admission.release_no_mutation(h.e.owner, h.e.request, h.e.root, h.result_pin, exited))


def test_retained_release_accepts_complete_two_phase_exit_zero_without_releasing_later_operation(history_factory):
    h = history_factory(outcome='retained')
    assert {row['phase'] for row in h.native['invocations']} == {'PREPARATION', 'RESTORE'}
    assert any(row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2'
               and Path(row['terminalPin']['path']).is_relative_to(h.e.claim/'runtime')
               for row in h.native['invocations'])
    assert all(row['terminalObservation']['actualExitCode'] == 0 for row in h.native['invocations'])
    result, _ = owner_result(h)
    verify, calls, proof = stopped_protocol(h)
    originals = fixed_originals(h)
    released = admission.release_retained_failure(h.e.owner, h.e.request, h.e.root, result, verify)
    assert proof in released and calls == [True]
    assert not (admission.HOST_ROOT/'active.json').exists()
    later = h.e.root.parent/'later-operation'; later.mkdir(mode=0o700)
    admission.reserve(h.e.owner, dict(h.e.request, operationId='later-operation'), later)
    active = (admission.HOST_ROOT/'active.json').read_bytes()
    def must_not_recheck():
        raise AssertionError('historical idempotent release must not observe a later target')
    assert admission.release_retained_failure(h.e.owner, h.e.request, h.e.root, result, must_not_recheck) == released
    assert (admission.HOST_ROOT/'active.json').read_bytes() == active
    assert all(path.read_bytes() == data for path, data in originals.items())


def test_retained_release_sees_real_nonzero_sql_in_claim_runtime(history_factory):
    h = history_factory(outcome='sql-failure')
    sql = next(row for row in h.native['invocations']
               if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2')
    assert sql['terminalObservation']['actualExitCode'] == 7
    assert Path(sql['terminalPin']['path']).is_relative_to(h.e.claim/'runtime')
    result, _ = owner_result(h)
    verify, calls, _ = stopped_protocol(h)
    refused(h, lambda: admission.release_retained_failure(h.e.owner, h.e.request, h.e.root, result, verify))
    assert calls == []


def test_retained_release_cannot_relabel_actual_unknown_as_known_failure(history_factory):
    h = history_factory(outcome='unknown')
    assert h.native['terminalUnknown']
    result, _ = owner_result(h, worker_changes={'state': 'FAILED_RETAINED', 'actualExitCode': 1})
    verify, calls, _ = stopped_protocol(h)
    refused(h, lambda: admission.release_retained_failure(h.e.owner, h.e.request, h.e.root, result, verify))
    assert calls == []


def test_oom_release_rejects_real_sql_exit_seven_despite_stopped_protocol(history_factory):
    h = history_factory(outcome='sql-failure')
    assert h.native['lastExitCode'] == 7
    result, _ = owner_result(h, worker_changes=dict(state='TERMINAL_UNKNOWN', actualExitCode=2,
        failureCode='FORMAL_SQL_IMPORT_FAILED'))
    verify, calls, _ = stopped_protocol(h)
    refused(h, lambda: admission.release_proven_oom(h.e.owner, h.e.request, h.e.root, result, verify))
    assert calls == []


def test_oom_release_requires_real_sql_137_and_keeps_original_history(history_factory, monkeypatch):
    transport = history.sql_transport
    def actual_exit_137(native, destination, **_):
        return transport(native, destination, code=137, unavailable=False)
    monkeypatch.setattr(history, 'sql_transport', actual_exit_137)
    h = history_factory(outcome='unknown', complete_epoch=False)
    sql = [row for row in h.native['invocations']
           if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2']
    assert len(sql) == 1 and sql[0]['terminalObservation']['actualExitCode'] == 137
    assert h.native['terminalUnknown']
    # Retain the exact recorded importer failure code; the shared producer
    # fixture otherwise uses its generic PROGRAM_TEST_RETAINED test marker.
    receipt = pinned_json(h.receipt_pin); receipt['failureCode'] = 'FORMAL_SQL_IMPORT_FAILED'
    h.receipt_pin = write(h.e.claim/'replacement-result.json', receipt)
    worker = pinned_json(h.result_pin); worker['failureCode'] = 'FORMAL_SQL_IMPORT_FAILED'
    worker['data']['replacementReceiptPin'] = h.receipt_pin
    worker['originalResultPins'] = [h.receipt_pin if Path(ref['path']) == h.e.claim/'replacement-result.json' else ref
                                    for ref in worker['originalResultPins']]
    h.result_pin = write(h.e.root/'worker-result.json', worker)
    with locked(h.e.case) as fd:
        epoch = read_current(h.e.case['epoch'])
        complete_restore(h.e.case['epoch'], h.e.request['operationId'], epoch['epochId'],
            'FAILED_RETAINED', h.receipt_pin, fd)
    result, _ = owner_result(h)
    verify, calls, proof = stopped_protocol(h)
    originals = fixed_originals(h)
    released = admission.release_proven_oom(h.e.owner, h.e.request, h.e.root, result, verify)
    assert proof in released and calls == [True]
    assert pinned_json(released[-1])['reason'] == 'PROVEN_STOPPED_OOM'
    assert not (admission.HOST_ROOT/'active.json').exists()
    assert all(path.read_bytes() == data for path, data in originals.items())


@pytest.mark.parametrize('additional', ['programSwitch', 'programImport', 'protectionState', 'protectionStep'])
def test_oom_release_rejects_additional_unknown_or_failed_protection_facts(history_factory, monkeypatch, additional):
    """Consumer boundary only: augmented proof is not claimed producer history.

    The native/context/SQL137 history is real and the real validator must accept
    it first. Only its returned facts are then conservatively augmented to test
    release admission. Separate validator tests prove their actual derivation.
    """
    import recovery_program_evidence as evidence
    transport = history.sql_transport
    def actual_exit_137(native, destination, **_):
        return transport(native, destination, code=137, unavailable=False)
    monkeypatch.setattr(history, 'sql_transport', actual_exit_137)
    h = history_factory(outcome='unknown')
    assert h.native['lastExitCode'] == 137 and h.native['terminalUnknown']
    # The generic history fixture records PROGRAM_TEST_RETAINED in its worker
    # envelope; OOM release requires the recorded importer failure family.
    result, _ = owner_result(h, worker_changes={'failureCode': 'FORMAL_SQL_IMPORT_FAILED'})
    actual_validator = evidence.validate_program_evidence
    validated = []
    def augmented_facts(*args, **kwargs):
        proof = actual_validator(*args, **kwargs)
        assert proof['unknownCauses'] == dict(native=True, programSwitch=False,
            programImport=False, outerConservative=False)
        assert proof['protectionState'] == 'ACTIVE'
        assert {key: value['state'] for key, value in proof['protectionStates'].items()} == {
            'archive': 'ABSENT', 'fence': 'ABSENT', 'scheduler': 'INSTALLED'}
        validated.append(True)
        augmented = deepcopy(proof)
        if additional in ('programSwitch', 'programImport'):
            augmented['unknownCauses'][additional] = True
        elif additional == 'protectionState':
            augmented['protectionState'] = 'FAILED_RETAINED'
        else:
            augmented['protectionStates']['scheduler'].update(state='FAILED_RETAINED',
                failedMethod='verify', errorCode='PROGRAM_PROTECTION_EVIDENCE_FAILED')
        return augmented
    monkeypatch.setattr(evidence, 'validate_program_evidence', augmented_facts)
    verify, calls, _ = stopped_protocol(h)
    refused(h, lambda: admission.release_proven_oom(h.e.owner, h.e.request, h.e.root, result, verify))
    assert validated == [True] and calls == []
