"""Worker handoff only: real files, main, operation_result and output serialization.

The execute seam supplies the documented producer outcome/exception protocol.
Pinned fixture documents are real immutable files, not claimed valid recovery,
native, protection, Docker or SQL evidence. Those producer/validator paths have
their own integration tests; this file proves only worker result propagation.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
from recovery_engine import RecoveryError, load, pin, write
import recovery_minimal_runtime as runtime
import recovery_minimal_worker as worker


PROGRAM_FIELDS = ('programExecutionPhase', 'programNativeEvidencePin',
                  'programProtectionCustodyPin', 'programGenerationPin', 'replacementReceiptPin')


class NativeOutcome:
    """Only the last-native result surface accepted by the worker protocol."""
    def __init__(self, pins, *, mutation=False, last_exit=None):
        self.original_pins = deepcopy(pins)
        self.mutation_dispatched = mutation
        self.last_exit = last_exit


@pytest.fixture
def handoff(tmp_path):
    variant = os.environ.get('RECOVERY_TEST_ENGINE_VARIANT', 'lightweight')
    success_messages = dict(lightweight='RESTORE_COMMANDS_COMPLETED_WITHOUT_VERIFICATION',
                            standard='RESTORE_DATA_AND_ISOLATED_START_COMPLETED')
    assert variant in success_messages, 'unknown worker engine variant: '+variant
    expected_success_message = success_messages[variant]
    root = tmp_path/'operation'; root.mkdir(mode=0o700)
    claim = root/'claim'; claim.mkdir(mode=0o700)
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='worker-result-unit',
        action='RESTORE', sourceConfigRef='source-original', parentChainRef=None,
        recoveryPointRef='point-original', targetConfigRef='target-registered-main')
    source_path = tmp_path/'source-original'; source_path.mkdir(mode=0o700)
    archive_root = tmp_path/'archive-original'; archive_root.mkdir(mode=0o700)
    # Real strict configuration admission still runs before the external
    # producer seam; this registry does not claim an executable restore target.
    configuration = dict(schemaVersion='RecoveryMinimalConfiguration/v1', operationsRoot=str(root),
        deadlineMilliseconds=60000, sources={request['sourceConfigRef']:dict(
            sourcePaths=[str(source_path)], archiveRoots=[str(archive_root)])}, targets={},
        pythonPin=pin(Path(sys.executable).resolve()), maxChainLength=10)
    config_pin = write(root/'configuration.json', configuration)
    request_pin = write(root/'request.json', request)

    def original(name, *, state=None):
        value = dict(schemaVersion='WorkerHandoffProtocolFixture/v1',
            operationId=request['operationId'], fixtureKind=name)
        if state is not None: value['state'] = state
        return write(claim/(name+'.json'), value)

    preparation = original('preparation-native')
    restoration = original('restore-native')
    native_snapshot = original('native-execution-evidence')
    protection = original('protection-custody-evidence')
    generation = original('generation')
    receipt = original('replacement-result', state='FAILED_RETAINED')
    all_pins = [preparation, restoration, native_snapshot, protection, generation, receipt]
    evidence = dict(programExecutionPhase='RESTORE', programNativeEvidencePin=native_snapshot,
        programProtectionCustodyPin=protection, programGenerationPin=generation,
        replacementReceiptPin=receipt, originalResultPins=all_pins,
        mutationDispatched=True, terminalUnknown=False, actualNativeExitCode=7,
        partialTargetRetained=True, retryPermitted=False)
    return SimpleNamespace(root=root, claim=claim, request=request, configuration=configuration,
        config_pin=config_pin, request_pin=request_pin, output=root/'worker-result.json',
        preparation=preparation, restoration=restoration, evidence=evidence,
        expected_success_message=expected_success_message)


def invoke(h, monkeypatch, *, error=None, data=None, native=None):
    """Keep all worker I/O/result code real; isolate only the execute protocol."""
    inputs = [h.config_pin, h.request_pin]
    before = {Path(reference['path']): Path(reference['path']).read_bytes()
              for reference in [*inputs, *h.evidence['originalResultPins']]}
    calls = []

    def producer(configuration, request, root, input_pins):
        assert configuration == h.configuration and request == h.request
        assert root == h.root and input_pins == inputs
        calls.append((configuration, request, root, input_pins))
        if error is not None:
            raise error
        return data, native

    monkeypatch.setattr(runtime, 'execute', producer)
    actual_exit = worker.main(['--configuration', h.config_pin['path'],
        '--request', h.request_pin['path'], '--output', str(h.output)])
    assert len(calls) == 1 and h.output.is_file()
    result = load(h.output)
    assert pin(h.output)['bytes'] > 0
    assert all(path.read_bytes() == raw for path, raw in before.items())
    return actual_exit, result


def failure(h, *, native=None, code='PROGRAM_PROTOCOL_FAILURE', unknown=False):
    error = RecoveryError(code, unknown=unknown)
    error.native = native
    error.evidence = deepcopy(h.evidence)
    return error


def assert_identity(result, request):
    assert result['schemaVersion'] == 'backup-restore-operation-result/v1'
    assert result['operationId'] == result['requestId'] == request['operationId']
    assert result['action'] == request['action']


def test_program_failure_retains_full_aggregate_in_real_worker_output(handoff, monkeypatch):
    h = handoff
    native = NativeOutcome([h.restoration], mutation=True, last_exit=7)
    error = failure(h, native=native)
    actual_exit, result = invoke(h, monkeypatch, error=error)
    assert_identity(result, h.request)
    assert actual_exit == result['actualExitCode'] == 1
    assert result['state'] == 'FAILED_RETAINED' and result['failureCode'] == error.code
    for key in (*PROGRAM_FIELDS, 'originalResultPins', 'mutationDispatched',
                'terminalUnknown', 'actualNativeExitCode'):
        assert result['data'].get(key) == h.evidence[key], key
    assert result['originalResultPins'] == h.evidence['originalResultPins']
    assert h.preparation in result['originalResultPins'] and h.restoration in result['originalResultPins']
    for reference in result['originalResultPins']:
        assert pin(reference['path']) == reference
        assert load(reference['path'])['operationId'] == h.request['operationId']


def test_producer_unknown_is_terminal_even_when_last_native_is_known(handoff, monkeypatch):
    h = handoff
    h.evidence.update(terminalUnknown=True, actualNativeExitCode=0)
    native = NativeOutcome([h.restoration], mutation=False, last_exit=0)
    actual_exit, result = invoke(h, monkeypatch, error=failure(h, native=native))
    assert actual_exit == result['actualExitCode'] == 2
    assert result['state'] == 'TERMINAL_UNKNOWN'
    assert result['data']['terminalUnknown'] is True
    assert result['data']['mutationDispatched'] is True
    assert result['data']['actualNativeExitCode'] == 0
    assert result['originalResultPins'] == h.evidence['originalResultPins']


@pytest.mark.parametrize('unknown_source', ['exception', 'native-pending'])
def test_aggregate_false_cannot_downgrade_existing_unknown_or_dispatch(handoff, monkeypatch, unknown_source):
    h = handoff
    h.evidence.update(terminalUnknown=False, mutationDispatched=False,
        actualNativeExitCode=None if unknown_source == 'native-pending' else 0)
    native = NativeOutcome([h.restoration], mutation=True,
                           last_exit=None if unknown_source == 'native-pending' else 0)
    error = failure(h, native=native, unknown=unknown_source == 'exception')
    actual_exit, result = invoke(h, monkeypatch, error=error)
    assert actual_exit == result['actualExitCode'] == 2
    assert result['state'] == 'TERMINAL_UNKNOWN'
    assert result['data']['terminalUnknown'] is True
    assert result['data']['mutationDispatched'] is True


def test_not_started_keeps_none_snapshots_and_original_failure_receipt(handoff, monkeypatch):
    h = handoff
    h.evidence.update(programExecutionPhase='NOT_STARTED', programNativeEvidencePin=None,
        programProtectionCustodyPin=None, programGenerationPin=None,
        originalResultPins=[h.evidence['replacementReceiptPin']], mutationDispatched=False,
        actualNativeExitCode=None)
    actual_exit, result = invoke(h, monkeypatch, error=failure(h))
    assert actual_exit == result['actualExitCode'] == 1 and result['state'] == 'FAILED_RETAINED'
    assert result['data']['programExecutionPhase'] == 'NOT_STARTED'
    assert all(result['data'][key] is None for key in PROGRAM_FIELDS[1:4])
    assert result['data']['replacementReceiptPin'] == h.evidence['replacementReceiptPin']
    assert result['data']['actualNativeExitCode'] is None
    assert result['data']['mutationDispatched'] is False
    assert result['originalResultPins'] == h.evidence['originalResultPins']


def test_ready_failure_retains_success_receipt_but_worker_still_fails(handoff, monkeypatch):
    h = handoff
    old_receipt = h.evidence['replacementReceiptPin']
    receipt = write(old_receipt['path'], dict(schemaVersion='WorkerHandoffProtocolFixture/v1',
        operationId=h.request['operationId'], fixtureKind='replacement-result', state='SUCCEEDED'))
    h.evidence['replacementReceiptPin'] = receipt
    h.evidence['originalResultPins'][-1] = receipt
    h.evidence['actualNativeExitCode'] = 0
    native = NativeOutcome([h.restoration], mutation=True, last_exit=0)
    error = failure(h, native=native, code='PROGRAM_READY_PUBLICATION_FAILURE')
    error.replacement_receipt_pin = receipt
    actual_exit, result = invoke(h, monkeypatch, error=error)
    assert actual_exit == result['actualExitCode'] == 1
    assert result['state'] == 'FAILED_RETAINED' and result['failureCode'] == error.code
    assert result['data']['replacementReceiptPin'] == receipt
    assert load(receipt['path'])['state'] == 'SUCCEEDED' and pin(receipt['path']) == receipt
    for key in PROGRAM_FIELDS:
        assert result['data'][key] == h.evidence[key]
    assert result['originalResultPins'] == h.evidence['originalResultPins']


def test_evidence_cannot_overwrite_request_identity_terminal_state_or_retention(handoff, monkeypatch):
    h = handoff
    error = failure(h, native=NativeOutcome([h.restoration], mutation=True, last_exit=7))
    error.evidence.update(operationId='foreign', requestId='foreign', action='FULL', state='SUCCEEDED',
        failureCode=None, actualExitCode=0, message='FORGED_SUCCESS', errorType='ForgedType',
        partialTargetRetained=False, retryPermitted=True, data=dict(state='SUCCEEDED'))
    actual_exit, result = invoke(h, monkeypatch, error=error)
    assert_identity(result, h.request)
    assert actual_exit == result['actualExitCode'] == 1 and result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == result['message'] == error.code
    assert result['data']['errorType'] == 'RecoveryError'
    assert result['data']['partialTargetRetained'] is True and result['data']['retryPermitted'] is False
    assert not ({'operationId','requestId','action','state','failureCode','actualExitCode','message','data'}
                & set(result['data']))
    assert result['data']['programExecutionPhase'] == 'RESTORE'


@pytest.mark.parametrize('pending', [False, True])
def test_legacy_failure_keeps_original_pins_exit_unknown_and_archive_diagnostic(handoff, monkeypatch, pending):
    h = handoff
    native = NativeOutcome([h.restoration], mutation=True, last_exit=None if pending else 9)
    error = RecoveryError('ARCHIVED_PAYLOAD_CHANGED')
    error.native = native
    error.archive_diagnostic = dict(expectedSha256='a'*64, actualSha256='b'*64)
    actual_exit, result = invoke(h, monkeypatch, error=error)
    assert_identity(result, h.request)
    assert actual_exit == result['actualExitCode'] == (2 if pending else 1)
    assert result['state'] == ('TERMINAL_UNKNOWN' if pending else 'FAILED_RETAINED')
    assert result['failureCode'] == 'ARCHIVED_PAYLOAD_CHANGED'
    assert result['data']['actualNativeExitCode'] == native.last_exit
    assert result['data']['mutationDispatched'] is True
    assert result['data']['archiveDiagnostic'] == error.archive_diagnostic
    assert result['originalResultPins'] == native.original_pins
    assert all(key not in result['data'] for key in PROGRAM_FIELDS)


def test_legacy_success_uses_real_operation_result_without_new_program_claim(handoff, monkeypatch):
    h = handoff
    data = dict(recoveryPoint='original-point', explicitUnitProtocol=True)
    native = NativeOutcome([h.restoration], mutation=True, last_exit=0)
    actual_exit, result = invoke(h, monkeypatch, data=data, native=native)
    assert_identity(result, h.request)
    assert actual_exit == result['actualExitCode'] == 0
    assert result['state'] == 'SUCCEEDED' and result['failureCode'] is None
    assert result['message'] == h.expected_success_message
    assert result['data'] == data and result['originalResultPins'] == native.original_pins
    assert all(key not in result['data'] for key in PROGRAM_FIELDS)
