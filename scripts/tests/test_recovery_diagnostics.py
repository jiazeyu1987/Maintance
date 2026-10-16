"""Local contract/behavior checks. No NAS, recovery, clock or shared services.

Controlled file fixtures exercise consumer rejection; only the local subprocess
scenario below is original execution evidence. These are not real DR acceptance.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
from diagnostics_cli import run
from recovery_diagnostics_evidence import ExecutionRecorder, summarize_execution
from recovery_diagnostics_io import (Budget, Contracts, DiagnosticError, Reader, atomic_json,
                                    digest, pin_file, state_lock, utc_now)

SCHEMA = ROOT / 'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json'


def ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z')


class Files:
    def __init__(self, root, monkeypatch):
        self.root, self.number, self.monkeypatch = root, 0, monkeypatch
        self.state = root / 'state'
        self.evidence = root / 'evidence'
        self.state.mkdir()
        self.evidence.mkdir()
        self.leaf = self.put({'scope': 'local-contract-fixture'})
        self.scope = self.put({'schemaVersion': 'RecoverySourceScope/v1', 'sourceIdentityPin': self.leaf})
        self.target = self.put({'schemaVersion': 'RecoveryTargetIdentity/v1', 'targetId': 'local-contract-target'})
        self.environment_policy = self.put({'schemaVersion': 'RecoveryEnvironmentPolicy/v1'})
        self.target_config = self.put({'schemaVersion': 'RecoveryEnvironmentConfig/v1',
                                      'targetIdentityPin': self.target, 'sourceScopePin': self.scope})
        self.config = {'schemaPin': pin_file(SCHEMA), 'stateRoot': str(self.state),
                       'evidenceRoot': str(self.evidence), 'clockGuardMilliseconds': 2000,
                       'statusStaleAfterMilliseconds': 10_000, 'scheduleId': 'local-schedule',
                       'freshnessMaximumAgeMilliseconds': 60_000,
                       'rehearsalIntervalMilliseconds': 60_000}
        self.context = {'sourceScopePin': self.scope, 'targetIdentityPin': self.target,
                        'toolAndVersionPins': [self.leaf], 'sideEffectPolicyPin': self.environment_policy}
        self.config['currentContext'] = self.context
        self.catalog = []
        self.contracts = Contracts(json.loads(SCHEMA.read_text(encoding='utf-8')))

    def put(self, value):
        self.number += 1
        path = self.root / ('input-' + str(self.number) + '.json')
        atomic_json(path, value)
        return pin_file(path)

    def bytes(self, value):
        self.number += 1
        path = self.root / ('stream-' + str(self.number) + '.bin')
        path.write_bytes(value)
        return pin_file(path)

    def point(self, parents=None, completed_at=None, eligible=True):
        generation = json.loads(Path(parents[0]['path']).read_bytes())['generationId'] if parents else 'generation-' + str(self.number)
        point = {'schemaVersion': 'RepositoryPoint/v1', 'backupId': 'point-' + str(self.number),
                 'generationId': generation,
                 'pointType': 'INCREMENTAL' if parents else 'FULL', 'parentPointPins': parents or [],
                 'commonRecoveryPoint': 'producer-checkpoint-' + str(self.number),
                 'manifestPin': self.leaf, 'payloadRefs': [self.leaf], 'readbackEvidencePin': self.leaf,
                 'ownerCloseEvidencePin': self.leaf, 'originalExitEvidencePin': self.leaf,
                 'integrityState': 'COMPLETE', 'blockedReason': None if eligible else 'BLOCKED',
                 'rehearsalEligible': eligible, 'controlledRestoreEligible': False}
        point['manifestPin'] = self.put({'schemaVersion': 'RepositoryManifest/v1',
            **{k: point[k] for k in ('backupId', 'generationId', 'pointType', 'parentPointPins',
                                     'commonRecoveryPoint', 'payloadRefs')},
            'sourceIdentityPin': self.leaf, 'createdAt': completed_at or ago(1)})
        pin = self.put(point)
        self.catalog.append({'pointPin': pin, 'completedAt': completed_at or ago(1)})
        self.config['catalogPin'] = self.put({'schemaVersion': 'recovery-diagnostics-catalog/v1',
                                             'sourceScopePin': self.scope, 'points': self.catalog})
        return pin

    def request(self, action, inputs, selected=None, request_id=None, operation_id='diagnostic-op'):
        if 'executionEvidence' in inputs:
            envelope = json.loads(Path(inputs['executionEvidence']['path']).read_bytes())
            if envelope.get('schemaVersion') == 'recovery-execution-evidence/v1' and hasattr(self, 'native_binding'):
                binding = deepcopy(self.native_binding)
                binding['executionEvidencePin'] = inputs['executionEvidence']
                self.config['executionSubjectBindingPin'] = self.put(binding)
        if action == 'PLAN_REHEARSAL' and 'approvedRehearsalTemplatePin' not in self.config:
            template = {'schemaVersion': 'backup-restore-operation/v1', 'operationId': 'template-op',
                'requestId': 'template-request', 'action': 'REHEARSAL', 'mode': 'REHEARSAL',
                'selectedPointPin': selected, 'sourceOrTargetRef': self.target_config,
                'policyPin': self.environment_policy, 'authorizationRefs': [self.leaf], 'leaseRef': self.leaf,
                'inputPins': {'repositoryPoint': selected}, 'deadlineMilliseconds': 12345}
            self.config['approvedRehearsalTemplatePin'] = self.put(template)
            self.config['rehearsalTemplateApprovalPin'] = self.put({
                'schemaVersion': 'RecoveryRehearsalTemplateApproval/v1',
                'templatePin': self.config['approvedRehearsalTemplatePin'],
                'permittedPointPins': [e['pointPin'] for e in self.catalog],
                'currentContext': deepcopy(self.context), 'validFrom': ago(100), 'validUntil': ago(-100)})
        policy_pin = self.put({'diagnostics': deepcopy(self.config)})
        return {'schemaVersion': 'backup-restore-operation/v1', 'operationId': operation_id,
                'requestId': request_id or 'request-' + str(self.number), 'action': action,
                'mode': 'REHEARSAL', 'selectedPointPin': selected, 'sourceOrTargetRef': self.target,
                'policyPin': policy_pin, 'authorizationRefs': [], 'leaseRef': None,
                'inputPins': inputs, 'deadlineMilliseconds': 30_000}

    def invoke(self, request, external=False, provision_trust=True):
        if provision_trust:
            config = json.loads(Path(request['policyPin']['path']).read_bytes())['diagnostics']
            trust = self.put({'schemaVersion': 'RecoveryDiagnosticsTrust/v1',
                'diagnosticsPolicyPin': request['policyPin'],
                **{name: config.get(name) for name in ('executionSubjectBindingPin',
                    'approvedRehearsalTemplatePin', 'rehearsalTemplateApprovalPin')}})
            self.monkeypatch.setenv('RECOVERY_DIAGNOSTICS_TRUST_FILE', trust['path'])
            self.monkeypatch.setenv('RECOVERY_DIAGNOSTICS_TRUST_SHA256', trust['sha256'])
        request_pin = self.put(request)
        output = self.root / ('output-' + str(self.number) + '.json')
        if external:
            process = subprocess.run([sys.executable, '-B', str(ROOT / 'ops/recovery/diagnostics_cli.py'),
                                      '--request', request_pin['path'], '--output', str(output)],
                                     capture_output=True, timeout=35)
            exit_code = process.returncode
        else:
            exit_code = run(request_pin['path'], str(output))
        result = json.loads(output.read_text(encoding='utf-8'))
        self.contracts.validate('OperationResult', result)
        return exit_code, result

    def execution(self, executor=0, resource=True, timed_out=False, complete=True, samples=None,
                  child_exit='same', action='REHEARSAL', **original_options):
        samples = samples or [sample(1_000_000_000, 10_000_000_000, 'CAPTURE'),
                              sample(2_000_000_000, 11_000_000_000, 'TRANSFER', 10, 1),
                              sample(3_000_000_000, 12_000_000_000, 'FINISH', 20, 2)]
        record = {'schemaVersion': 'recovery-execution-evidence/v1', 'operationId': 'diagnostic-op',
                'attemptId': 'local-attempt', 'observerEpoch': 'epoch-1',
                'clockDomain': {'hostId': 'local-test', 'bootId': 'local-boot'}, 'samples': samples,
                'exits': {'executor': executor, 'runner': 124 if timed_out else executor, 'test': None},
                'timedOut': timed_out, 'timeoutLayer': 'RUNNER' if timed_out else None, 'complete': complete,
                'processTerminal': executor is not None, 'resourceTerminal': resource,
                'streamRefs': {'stdout': self.bytes(b'raw-private-stdout'),
                               'stderr': self.bytes(b'raw-private-stderr')}, 'originalPins': []}
        identity = {'operationId': 'diagnostic-op', 'requestId': 'observed-request', 'action': action,
                    'attemptId': 'local-attempt', 'pid': 101, 'processStartedAt': 'linux:local-boot:1001',
                    'hostId': 'local-test', 'bootId': 'local-boot', 'observerEpoch': 'epoch-1'}
        self.bind_execution(record, identity, executor if child_exit == 'same' else child_exit,
                            **original_options)
        return record

    def bind_execution(self, record, identity, child_exit, *, host_os='Linux',
                       profile_change=None, registration_change=None, source_change=None,
                       entry_change=None, entry_count=1):
        # Offline protocol fixtures follow the current producer's exact v2 shape.
        # Their namespace/PID values do not prove actual privileged execution.
        subject = {'schemaVersion': 'backup-restore-operation/v1', 'operationId': identity['operationId'],
            'requestId': identity['requestId'], 'action': identity['action'], 'mode': 'REHEARSAL',
            'selectedPointPin': None, 'sourceOrTargetRef': self.target, 'policyPin': self.environment_policy,
            'authorizationRefs': [], 'leaseRef': None, 'inputPins': {}, 'deadlineMilliseconds': 30000}
        subject_pin = self.put(subject)
        daemon_executable = self.root / 'dockerd'
        daemon_executable.write_bytes(b'offline-daemon-pin-only')
        registration = {'schemaVersion': 'RecoveryControlNamespaceRegistration/v1',
            'taskId': '20261010-backup-restore-modular-development', 'hostId': identity['hostId'],
            'bootId': identity['bootId'], 'uid': 0,
            'daemon': {'pid': 201, 'startTimeTicks': 2001, 'executablePin': pin_file(daemon_executable)},
            'namespaces': {'net': {'path': '/proc/201/ns/net', 'device': 4, 'inode': 100},
                           'mount': {'path': '/proc/201/ns/mnt', 'device': 4, 'inode': 101}}}
        if registration_change:
            registration_change(registration)
        registration_pin = self.put(registration) if host_os == 'Linux' else None
        source = {'schemaVersion': 'RecoveryLocalEnvironmentRegistration/v1', 'usableForExecution': True,
                  'host': {'selectedExecutionHost': 'offline-protocol-host',
                           'namespaceRegistrationPin': registration_pin}}
        if source_change:
            source_change(source)
        source_pin = self.put(source)
        profile_record = {'schemaVersion': 'RecoveryControlExecutionHost/v2', 'transport': 'LOCAL',
            'hostOs': host_os, 'hostId': identity['hostId'], 'bootId': identity['bootId'],
            'uid': 0 if host_os == 'Linux' else None, 'sourceProfilePin': source_pin,
            'pythonPin': self.leaf, 'dispatcherPin': self.leaf, 'scriptPin': self.leaf,
            'workingDirectory': str(self.root), 'evidenceRoot': str(self.evidence),
            'launcherPin': None, 'launcherArguments': [], 'environment': {'OFFLINE_PROTOCOL_ONLY': '1'},
            'resourceObserverPin': self.leaf, 'namespaceRegistrationPin': registration_pin}
        if profile_change:
            profile_change(profile_record)
        profile = self.put(profile_record)
        common = {k: identity[k] for k in ('operationId', 'requestId', 'attemptId', 'observerEpoch')}
        common.update(requestPin=subject_pin, clockDomain=record['clockDomain'])
        entry_pins = []
        if host_os == 'Linux':
            entry = {'schemaVersion': 'RecoveryControlNamespaceEntry/v1',
                'namespaceRegistrationPin': registration_pin, 'hostId': identity['hostId'],
                'bootId': identity['bootId'], 'daemon': deepcopy(registration['daemon']),
                'namespaces': deepcopy(registration['namespaces']),
                'enteredMonotonicNs': max(0, record['samples'][0]['monotonicNs'] - 1),
                **{k: common[k] for k in ('operationId', 'requestId', 'requestPin', 'attemptId')},
                'profilePin': profile}
            if entry_change:
                entry_change(entry)
            entry_pins = [self.put(entry) for _ in range(entry_count)]
        record['samples'][0]['phase'] = 'DISPATCH'
        record['samples'][-1]['phase'] = 'ORIGINAL_EXIT'
        record['samples'][-1]['bytes'] = sum(p['bytes'] for p in record['streamRefs'].values())
        intent = self.put({'schemaVersion': 'RecoveryControlNativeIntent/v1', **common, 'profilePin': profile,
            'pythonPin': self.leaf, 'scriptPin': self.leaf, 'startedMonotonicNs': record['samples'][0]['monotonicNs']})
        native = {'schemaVersion': 'RecoveryControlObservationBinding/v1', **common,
                  'pid': identity['pid'], 'processStartedAt': identity['processStartedAt'],
                  'intentPin': intent, 'profilePin': profile}
        native_pin = self.put(native)
        observed = {**common, 'pid': identity['pid'], 'processStartedAt': identity['processStartedAt']}
        cli_exit = None if record['exits']['executor'] is None else 0 if record['exits']['executor'] == 0 else 1
        record['exits'] = {'executor': cli_exit, 'runner': None, 'test': None}
        exit_pin = self.put({'schemaVersion': 'RecoveryControlNativeExit/v1', **observed, 'intentPin': intent,
            'cliExitCode': cli_exit, 'processTerminal': record['processTerminal'], 'timedOut': record['timedOut'],
            'observedMonotonicNs': record['samples'][-1]['monotonicNs'],
            'observedWallNs': record['samples'][-1]['wallNs']})
        resource = self.put({'schemaVersion': 'RecoveryControlResourceObservation/v1', **observed,
            'originalExitPin': exit_pin, 'resourceTerminal': record['resourceTerminal'], 'originalPins': [self.leaf]})
        record['originalPins'] = [subject_pin, profile, source_pin, intent, exit_pin, resource, *entry_pins,
                                 *record['streamRefs'].values()]
        result = result_record('SUCCEEDED' if cli_exit == 0 else 'FAILED_RETAINED', child_exit,
                               action=identity['action'], operation=identity['operationId'])
        self.native_binding = {'schemaVersion': 'RecoveryDiagnosticSubjectBinding/v1',
            'nativeProcessBindingPin': native_pin, 'executionEvidencePin': None,
            'operationResultPin': self.put(result)}
        self.native_exit_pin = exit_pin
        self.native_identity = identity
        self.native_profile_pin = profile
        self.native_registration_pin = registration_pin
        self.native_entry_pins = entry_pins

    def status(self, state='RUNNING', result_pin=None, when=None):
        return {'operationId': 'diagnostic-op', 'requestId': 'observed-request', 'action': 'REHEARSAL',
                'phase': 'CAPTURE', 'state': state, 'originalResultPins': [] if result_pin is None else [result_pin],
                'nextAction': 'RECONCILE', 'waitReason': None, 'failureCode': None,
                'updatedAt': when or utc_now()}

    def report(self, point, chain=None, verdict='PASSED', finished_at=None):
        chain = chain or [point]
        plan = {'schemaVersion': 'RestorePlan/v1', 'operationId': 'verified-op', 'restoreId': 'restore-1',
                'mode': 'REHEARSAL', 'candidatePin': point, 'orderedChainPins': chain,
                'recoveryPoint': 'producer-checkpoint', 'targetRef': self.target_config,
                'supportedVersionPins': [self.leaf], 'toolPins': [self.leaf], 'plannedWrites': [],
                'sideEffectPolicyPin': self.environment_policy, 'authorizationRefs': [self.leaf],
                'leaseRef': self.leaf, 'immutableInputsSha256': '0' * 64}
        plan_pin = self.put(plan)
        restored = {'schemaVersion': 'RestoreExecutionResult/v1', 'operationId': 'verified-op',
                    'restoreId': 'restore-1', 'planPin': plan_pin, 'targetIdentityPin': self.target,
                    'recoveryPoint': 'producer-checkpoint', 'dbStepEvidencePins': [self.leaf],
                    'objectStepEvidencePins': [self.leaf], 'consistencyEvidencePin': self.leaf,
                    'originalInvocationPins': [self.leaf], 'state': 'SUCCEEDED', 'writeProtectionState': 'ENFORCED'}
        restore_pin = self.put(restored)
        isolation = self.put({'schemaVersion': 'RecoverySideEffectIsolation/v1', 'operationId': 'verified-op',
            'targetIdentityPin': self.target, 'state': 'ENFORCED', 'policyPin': self.environment_policy,
            'writeProtectionState': 'ENFORCED', 'sourceWritesPerformed': False})
        app = {'schemaVersion': 'ApplicationStartResult/v1', 'operationId': 'verified-op',
               'restoreId': 'restore-1', 'targetIdentityPin': self.target, 'restoreResultPin': restore_pin,
               'imagePins': [self.leaf], 'configurationPin': self.leaf, 'sideEffectIsolationPin': isolation,
               'originalStartResultPins': [self.leaf], 'healthEvidencePin': self.leaf, 'state': 'SUCCEEDED'}
        observation = {'state': 'MEASURED', 'observedMilliseconds': 10, 'objectiveMilliseconds': 100,
                       'evidencePins': [self.leaf]}
        report = {'schemaVersion': 'RecoveryVerificationReport/v1', 'reportId': 'report-1',
                  'operationId': 'verified-op', 'restoreId': 'restore-1', 'mode': 'REHEARSAL',
                  'backupAndChainPins': chain, 'planPin': plan_pin, 'targetIdentityPin': self.target,
                  'sourceScopePin': self.scope, 'toolAndVersionPins': [self.leaf], 'restoreResultPin': restore_pin,
                  'applicationStartPin': self.put(app), 'dataEvidencePins': [self.leaf],
                  'playwrightEvidencePins': [self.leaf], 'rtoObservation': observation,
                  'rpoObservation': observation, 'targetApprovalRefs': [self.leaf], 'verdict': verdict,
                  'invalidatedBy': []}
        report_pin = self.put(report)
        wrapper = result_record('SUCCEEDED', 0, action='VERIFY_RECOVERY', operation='verified-op', data=report)
        wrapper['finishedAt'] = finished_at or utc_now()
        self.config['verificationResultPin'] = self.put(wrapper)
        return report_pin


def sample(mono, wall, phase, size=0, count=0):
    return {'monotonicNs': mono, 'wallNs': wall, 'phase': phase, 'bytes': size, 'count': count,
            'cpuNanoseconds': mono // 10, 'residentBytes': 1024, 'stopWrites': phase == 'CAPTURE'}


def result_record(state='SUCCEEDED', actual=0, action='REHEARSAL', operation='diagnostic-op', data=None):
    return {'schemaVersion': 'backup-restore-operation-result/v1', 'operationId': operation,
            'requestId': 'observed-request', 'action': action, 'state': state,
            'failureCode': None if state == 'SUCCEEDED' else 'ORIGINAL_FAILURE', 'message': 'local fixture',
            'data': {'terminal': True} if data is None else data, 'originalResultPins': [],
            'startedAt': utc_now(), 'finishedAt': utc_now(), 'actualExitCode': actual}


@pytest.fixture
def files(tmp_path, monkeypatch):
    monkeypatch.delenv('RECOVERY_DIAGNOSTICS_TRUST_FILE', raising=False)
    monkeypatch.delenv('RECOVERY_DIAGNOSTICS_TRUST_SHA256', raising=False)
    return Files(tmp_path, monkeypatch)


def test_real_exit7_preserves_separate_private_streams_and_monotonic_elapsed(files):
    path = files.root / 'recorded-execution.json'
    recorder = ExecutionRecorder(path, 'diagnostic-op', 'real-local-attempt', 'epoch-local', 'host-local', 'boot-local')
    recorder.sample('CAPTURE', stop_writes=True)
    process_start = utc_now()
    child = subprocess.Popen([sys.executable, '-B', '-c',
                              "import sys; sys.stdout.buffer.write(b'private-stdout'); "
                              "sys.stderr.buffer.write(b'private-stderr'); sys.exit(7)"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = child.communicate(timeout=10)
    process = subprocess.CompletedProcess(child.args, child.returncode, stdout, stderr)
    recorder.sample('FINISH', bytes_processed=len(process.stdout) + len(process.stderr), count=1)
    recorder.finish(process.returncode, process.returncode, None, False, None, True, True,
                    {'stdout': files.bytes(process.stdout), 'stderr': files.bytes(process.stderr)}, [])
    summary = summarize_execution(recorder.record, 2_000_000_000)
    assert summary['actualExitCode'] == 7 and summary['elapsedNs'] > 0
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': pin_file(path)})
    exit_code, result = files.invoke(request, external=True)
    assert exit_code == 2 and result['actualExitCode'] is None
    assert result['failureCode'] == 'CURRENT_EXECUTION_BINDING_MISSING'
    assert summary['bytes'] == 28 and summary['count'] == 1
    assert 'private-stdout' not in json.dumps(result) and 'private-stderr' not in json.dumps(result)
    assert pin_file(path) in result['originalResultPins']


@pytest.mark.parametrize('executor,resource,timed_out,complete,expected,code', [
    (0, True, False, True, 0, None),
    (None, True, False, True, 2, 'NATIVE_ORIGINAL_EXIT_UNKNOWN'),
    (0, None, False, True, 2, 'RESOURCE_OBSERVATION_BINDING_INVALID'),
    (7, True, False, True, 1, 'ORIGINAL_EXECUTION_FAILED'),
    (9, True, True, True, 1, 'EXECUTION_TIMEOUT'),
    (0, True, False, False, 2, 'EXECUTOR_TERMINAL_UNKNOWN'),
])
def test_diagnosis_never_maps_failure_unknown_or_timeout_to_success(files, executor, resource,
                                                                  timed_out, complete, expected, code):
    evidence = files.execution(executor, resource, timed_out, complete)
    exit_code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert exit_code == expected and result['failureCode'] == code
    assert result['actualExitCode'] == (executor if expected != 2 or complete is False else None)
    assert result['data']['timedOut'] == (None if expected == 2 and executor is None or
                                       expected == 2 and resource is None else timed_out)
    assert result['data']['clockSetter'] == 'UNKNOWN'


def test_wall_reversal_and_cumulative_drift_fail_without_setter_attribution(files):
    evidence = files.execution(samples=[sample(1_000_000_000, 10_000_000_000, 'CAPTURE'),
                                       sample(2_000_000_000, 9_000_000_000, 'TRANSFER'),
                                       sample(3_000_000_000, 9_000_000_000, 'FINISH')])
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 1
    assert result['data']['elapsedNs'] == 2_000_000_000
    assert result['data']['cumulativeWallMinusMonotonicNs'] == -3_000_000_000
    assert 'WALL_CLOCK_REVERSED' in result['data']['clockProblems']
    assert 'CUMULATIVE_CLOCK_GUARD_REJECTED' in result['data']['clockProblems']
    assert result['data']['systemClockModified'] is False


def test_monotonic_regression_is_not_elapsed_success(files):
    record = files.execution(samples=[sample(2, 3, 'CAPTURE'), sample(1, 4, 'FINISH')])
    summary = summarize_execution(record, 2)
    assert summary['state'] == 'FAILED_RETAINED' and summary['elapsedNs'] is None
    assert 'MONOTONIC_REGRESSION' in summary['clockProblems']


def test_stream_tamper_and_unknown_schema_fail(files):
    evidence = files.execution()
    Path(evidence['streamRefs']['stderr']['path']).write_bytes(b'different')
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] in ('PIN_SIZE_MISMATCH', 'PIN_CONTENT_MISMATCH')


def test_unknown_input_key_and_relative_path_fail(files):
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(files.execution())})
    request['inputPins']['madeUp'] = files.leaf
    code, result = files.invoke(request)
    assert code == 1 and result['failureCode'] == 'SCHEMA_OPERATIONREQUEST_INVALID'
    request['inputPins'].pop('madeUp')
    request['sourceOrTargetRef']['path'] = 'relative.json'
    request_pin = files.put(request)
    output = files.root / 'relative-output.json'
    assert run(request_pin['path'], str(output)) == 1 and not output.exists()


def test_idempotency_reuses_exact_result_and_rejects_changed_request(files):
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(files.execution())}, request_id='same')
    first_code, first = files.invoke(request)
    second_code, second = files.invoke(request)
    assert first_code == second_code == 0 and first == second
    request['deadlineMilliseconds'] += 1
    code, result = files.invoke(request)
    assert code == 1 and result['failureCode'] == 'REQUEST_ID_CONTENT_CONFLICT'


@pytest.mark.parametrize('observed_state,actual,expected', [('SUCCEEDED', 0, 2), ('SUCCEEDED', None, 2),
                                                         ('FAILED_RETAINED', 7, 1), ('TERMINAL_UNKNOWN', None, 2)])
def test_observation_retains_original_exit(files, observed_state, actual, expected):
    original = files.put(result_record(observed_state, actual))
    status = files.put(files.status(observed_state, original))
    code, result = files.invoke(files.request('OBSERVE_OPERATION', {'operationStatus': status}))
    assert code == expected and result['actualExitCode'] == actual
    assert result['data']['restartObservation']['automaticRetryPerformed'] is False


def test_observed_success_requires_matching_original_resource_terminal(files):
    original = files.put(result_record())
    status = files.put(files.status('SUCCEEDED', original))
    evidence = files.put(files.execution())
    code, result = files.invoke(files.request('OBSERVE_OPERATION', {'operationStatus': status,
                                                                   'executionEvidence': evidence}))
    assert code == 0 and result['data']['restartObservation']['resourcesTerminal'] is True


def test_stale_running_restart_is_unknown_and_never_releases_resource(files):
    evidence = files.execution(executor=None, resource=None, complete=False)
    status = files.put(files.status(when=ago(30)))
    code, first = files.invoke(files.request('OBSERVE_OPERATION',
                                            {'operationStatus': status, 'executionEvidence': files.put(evidence)}))
    assert code == 2
    evidence['observerEpoch'] = 'epoch-2'
    code, second = files.invoke(files.request('OBSERVE_OPERATION',
                                             {'operationStatus': status, 'executionEvidence': files.put(evidence)}))
    restart = second['data']['restartObservation']
    assert code == 2 and second['failureCode'] == 'ORIGINAL_CURRENT_IDENTITY_MISMATCH'
    assert restart['reconciliationRequired'] is True and restart['resourceReleasePerformed'] is False


def test_unresolved_local_lock_is_unknown_and_is_not_deleted(files):
    lock = files.state / '.diagnostics.lock'
    lock.write_text('retained-crash-lock', encoding='utf-8')
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(files.execution())}))
    assert code == 2 and result['failureCode'] == 'LOCAL_STATE_LOCK_UNRESOLVED'
    assert lock.read_text(encoding='utf-8') == 'retained-crash-lock'


def test_latest_point_longest_chain_requests_and_round_dedup(files):
    full = files.point(completed_at=ago(30))
    incremental = files.point([full], completed_at=ago(20))
    longest = files.point([full, incremental], completed_at=ago(10))
    latest = files.point(completed_at=ago(1))
    code, first = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': latest}, latest))
    assert code == 0 and first['data']['latestCompletePointPin'] == latest
    assert first['data']['longestSupportedChainPin'] == longest
    assert len(first['data']['requests']) == 2 and first['data']['recoveryExecuted'] is False
    for entry in first['data']['requests']:
        generated = json.loads(Path(entry['requestPin']['path']).read_text(encoding='utf-8'))
        files.contracts.validate('OperationRequest', generated)
        assert generated['action'] == 'REHEARSAL' and generated['leaseRef'] == files.leaf
        assert generated['policyPin'] == files.environment_policy
        assert generated['sourceOrTargetRef'] == files.target_config
        assert generated['authorizationRefs'] == [files.leaf] and generated['deadlineMilliseconds'] == 12345
    # Same pinned policy, a fresh observation request; no duplicate executor request.
    original_request = next(p for p in first['originalResultPins']
                            if json.loads(Path(p['path']).read_text(encoding='utf-8')).get('action') == 'PLAN_REHEARSAL')
    another = json.loads(Path(original_request['path']).read_text(encoding='utf-8'))
    another['requestId'] = 'another-observation'
    code, second = files.invoke(another)
    assert code == 0 and all(r['deduplicated'] for r in second['data']['requests'])
    assert [r['requestPin'] for r in first['data']['requests']] == [r['requestPin'] for r in second['data']['requests']]


def test_stale_complete_point_alert_is_distinct_from_recovery_proof(files):
    point = files.point(completed_at=ago(120))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point}, point))
    assert code == 0 and result['data']['latestProvenRecovery'] is None
    assert {'LATEST_COMPLETE_POINT_STALE', 'RECOVERY_VERIFICATION_MISSING'} <= \
        {a['code'] for a in result['data']['alerts']}
    assert all(a['externalNotificationSent'] is False for a in result['data']['alerts'])


def test_old_selected_point_and_ineligible_chain_fail(files):
    old = files.point(completed_at=ago(20))
    latest = files.point(completed_at=ago(1))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': old}, old))
    assert code == 1 and result['failureCode'] == 'REQUEST_NOT_LATEST_COMPLETE_POINT'
    bad = files.point([latest], eligible=False, completed_at=utc_now())
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': bad}, bad))
    assert code == 1


def test_report_binds_current_context_and_changed_inputs_invalidate(files):
    point = files.point()
    report = files.report(point)
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point,
                                                               'recoveryVerificationReport': report}, point))
    assert code == 0 and result['data']['latestProvenRecovery']['current'] is True
    assert not result['data']['invalidatedBy']
    files.config['currentContext']['toolAndVersionPins'] = [files.target]
    approval = json.loads(Path(files.config['rehearsalTemplateApprovalPin']['path']).read_bytes())
    approval['currentContext'] = deepcopy(files.config['currentContext'])
    files.config['rehearsalTemplateApprovalPin'] = files.put(approval)
    code, changed = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point,
                                                                'recoveryVerificationReport': report}, point))
    assert code == 0 and changed['data']['latestProvenRecovery']['current'] is False
    assert 'TOOLANDVERSIONPINS_CHANGED' in changed['data']['invalidatedBy']
    assert changed['data']['requests'][0]['deduplicated'] is False


def test_old_recovery_report_does_not_cover_new_point(files):
    old = files.point(completed_at=ago(10))
    report = files.report(old)
    latest = files.point(completed_at=ago(1))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': latest,
                                                               'recoveryVerificationReport': report}, latest))
    assert code == 0 and 'BACKUP_CHAIN_CHANGED' in result['data']['invalidatedBy']
    assert result['data']['latestProvenRecovery']['current'] is False


def test_expired_report_needs_new_acceptance(files):
    point = files.point()
    report = files.report(point, finished_at=ago(100))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point,
                                                               'recoveryVerificationReport': report}, point))
    assert code == 0 and 'VERIFICATION_EXPIRED' in result['data']['invalidatedBy']


def test_future_point_unknown_does_not_generate_request(files):
    point = files.point(completed_at=ago(-60))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point}, point))
    assert code == 2 and result['failureCode'] == 'BACKUP_WALL_TIME_IN_FUTURE'
    assert result['data']['requests'] == []


def test_output_collision_keeps_input_original(files):
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(files.execution())})
    pin = files.put(request)
    original = Path(pin['path']).read_bytes()
    assert run(pin['path'], pin['path']) == 1
    assert Path(pin['path']).read_bytes() == original


def test_deadline_expires_without_child_or_default_success():
    budget = Budget(1, time.monotonic_ns() - 10_000_000)
    with pytest.raises(DiagnosticError, match='DIAGNOSTIC_DEADLINE_EXCEEDED') as error:
        budget.check()
    assert error.value.unknown is True


def test_existing_original_timeout_envelope_is_read_only_unknown(files):
    path = ROOT / 'doc/tasks/20261010-backup-diagnostic-interface-implementation/actual-timeout-v2/carrier/diagnostic-evidence.json'
    pin = pin_file(path)
    envelope = json.loads(path.read_bytes())
    runner = json.loads(Path(envelope['runnerResultReference']['path']).read_bytes())
    files.config['legacySchemaPin'] = pin_file(ROOT / 'doc/tasks/20261010-backup-cross-thread-interfaces/schemas.json')
    files.config['legacyDiagnosticBinding'] = {'subjectOperationId': 'historical-operation', 'evidencePin': pin,
                                               'attemptId': runner['attempt'],
                                               'toolResultProfile': 'exec-command-result'}
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': pin}))
    assert code == 2 and result['state'] == 'TERMINAL_UNKNOWN'
    assert result['data']['toolExitCode'] == 124 and result['data']['exits']['runner'] == 124
    assert result['data']['observedClientExitCode'] == runner['clientReturncode']
    assert result['data']['timedOut'] is True and result['data']['clockSetter'] == 'UNKNOWN'
    assert pin_file(path) == pin


def test_schedule_clock_reversal_unknown_and_periodic_new_round(files):
    point = files.point()
    request = files.request('PLAN_REHEARSAL', {'repositoryPoint': point}, point)
    code, first = files.invoke(request)
    assert code == 0
    ledger = next(files.state.glob('schedule-*.json'))
    history = json.loads(ledger.read_bytes())
    history['rounds'][0]['plannedAt'] = ago(-60)
    atomic_json(ledger, history)
    request['requestId'] = 'future-schedule-observation'
    code, future = files.invoke(request)
    assert code == 2 and future['failureCode'] == 'SCHEDULE_WALL_CLOCK_REVERSED'
    assert not future['data']['requests']
    history['rounds'][0]['plannedAt'] = ago(120)
    atomic_json(ledger, history)
    request['requestId'] = 'due-schedule-observation'
    code, due = files.invoke(request)
    assert code == 0 and due['data']['requests'][0]['deduplicated'] is False
    assert due['data']['requests'][0]['requestPin'] != first['data']['requests'][0]['requestPin']


def test_report_missing_original_wrapper_fails_instead_of_accepting_passed_label(files):
    point = files.point()
    report = files.report(point)
    files.config.pop('verificationResultPin')
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point,
                                                               'recoveryVerificationReport': report}, point))
    assert code == 1 and result['failureCode'] == 'DIAGNOSTICS_CONFIG_VERIFICATIONRESULTPIN_INVALID'


def test_same_request_rejects_changed_original_after_cache(files):
    evidence_pin = files.put(files.execution())
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': evidence_pin})
    code, _ = files.invoke(request)
    assert code == 0
    Path(evidence_pin['path']).write_bytes(b'{}')
    code, result = files.invoke(request)
    assert code == 1 and result['failureCode'] == 'PIN_CONTENT_MISMATCH'


def test_cli_budget_includes_import_and_startup_before_request(files):
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(files.execution())})
    request['deadlineMilliseconds'] = 1
    code, result = files.invoke(request, external=True)
    assert code == 2 and result['failureCode'] == 'DIAGNOSTIC_DEADLINE_EXCEEDED'


def test_longest_chain_cannot_include_point_from_unbound_source_catalog(files):
    foreign_parent = files.point(completed_at=ago(20))
    files.catalog.clear()
    selected = files.point([foreign_parent], completed_at=ago(1))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': selected}, selected))
    assert code == 1 and result['failureCode'] == 'CHAIN_OUTSIDE_SOURCE_CATALOG'


def test_diagnostic_invocation_is_distinct_from_bound_subject(files):
    evidence = files.put(files.execution())
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': evidence},
                                             operation_id='independent-diagnostic-call'))
    assert code == 0
    assert result['operationId'] == 'independent-diagnostic-call'
    assert result['data']['subjectIdentity']['operationId'] == 'diagnostic-op'
    assert result['data']['diagnosticInvocation']['operationId'] == 'independent-diagnostic-call'


def test_null_child_exit_with_actual_cli_success_and_resource_proof(files):
    original = files.put(result_record(actual=None, action='VERIFY_RECOVERY'))
    status = files.status('SUCCEEDED', original)
    status['action'] = 'VERIFY_RECOVERY'
    evidence = files.put(files.execution(child_exit=None, action='VERIFY_RECOVERY'))
    code, result = files.invoke(files.request('OBSERVE_OPERATION',
        {'operationStatus': files.put(status), 'executionEvidence': evidence}, operation_id='observer-call'))
    assert code == 0 and result['actualExitCode'] is None
    assert result['data']['execution']['cliExitCode'] == 0
    assert result['data']['execution']['childExecutorExitCode'] is None


@pytest.mark.parametrize('name,value', [('operationId', 'other-op'), ('requestId', 'other-request'), ('action', 'LIST_POINTS'),
    ('attemptId', 'other-attempt'), ('pid', 102), ('processStartedAt', '2026-01-01T00:00:00Z'),
    ('hostId', 'other-host'), ('bootId', 'other-boot'), ('observerEpoch', 'other-epoch')])
def test_wrong_current_execution_identity_is_unknown(files, name, value):
    evidence = files.execution()
    if name in ('hostId', 'bootId'):
        evidence['clockDomain'][name] = value
    elif name == 'action':
        original = json.loads(Path(files.native_binding['operationResultPin']['path']).read_bytes())
        original['action'] = value
        files.native_binding['operationResultPin'] = files.put(original)
    elif name in ('requestId', 'pid', 'processStartedAt'):
        original = json.loads(Path(files.native_exit_pin['path']).read_bytes())
        original[name] = value
        changed = files.put(original)
        evidence['originalPins'] = [changed if p == files.native_exit_pin else p for p in evidence['originalPins']]
    else:
        evidence[name] = value
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == ('SUBJECT_RESULT_IDENTITY_MISMATCH' if name == 'action' else
                                                 'ORIGINAL_CURRENT_IDENTITY_MISMATCH')
    assert result['data']['currentOriginalsVerified'] is False


def test_observer_wrong_subject_operation_remains_unknown(files):
    status = files.put(files.status('SUCCEEDED', files.put(result_record())))
    evidence = files.execution()
    evidence['operationId'] = 'other-operation'
    code, result = files.invoke(files.request('OBSERVE_OPERATION',
        {'operationStatus': status, 'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'ORIGINAL_CURRENT_IDENTITY_MISMATCH'


def test_empty_originals_cannot_settle_an_envelope(files):
    evidence = files.execution()
    evidence['originalPins'] = []
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'CURRENT_EXECUTION_ORIGINALS_MISSING'


def test_original_exit_semantics_override_false_success_claim(files):
    evidence = files.execution()
    original = json.loads(Path(files.native_exit_pin['path']).read_bytes())
    original['cliExitCode'] = 7
    changed = files.put(original)
    evidence['originalPins'] = [changed if p == files.native_exit_pin else p for p in evidence['originalPins']]
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'ORIGINAL_ENVELOPE_FACT_MISMATCH'


def test_missing_current_binding_never_infers_terminal(files):
    evidence = files.put(files.execution())
    del files.native_binding
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': evidence}))
    assert code == 2 and result['failureCode'] == 'CURRENT_EXECUTION_BINDING_MISSING'


def test_unreadable_original_is_unknown(files):
    evidence = files.execution()
    Path(files.native_exit_pin['path']).unlink()
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'PIN_UNREADABLE'


def test_observer_rejects_subject_request_of_another_action(files):
    status = files.put(files.status('SUCCEEDED', files.put(result_record())))
    evidence = files.put(files.execution(action='LIST_POINTS'))
    code, result = files.invoke(files.request('OBSERVE_OPERATION',
        {'operationStatus': status, 'executionEvidence': evidence}))
    assert code == 2 and result['failureCode'] == 'OBSERVED_CURRENT_IDENTITY_MISMATCH'


def test_cli_success_does_not_hide_mismatched_child_exit(files):
    status = files.put(files.status('SUCCEEDED', files.put(result_record(actual=None))))
    evidence = files.put(files.execution(child_exit=7))
    code, result = files.invoke(files.request('OBSERVE_OPERATION',
        {'operationStatus': status, 'executionEvidence': evidence}))
    assert code == 2 and result['failureCode'] == 'SUBJECT_SUCCESS_RESULT_INVALID'


def test_first_rehearsal_accepts_complete_cumulative_ancestors(files):
    full = files.point(completed_at=ago(30))
    first = files.point([full], completed_at=ago(20))
    second = files.point([full, first], completed_at=ago(10))
    updated = {}
    for old in (full, first, second):
        point = json.loads(Path(old['path']).read_bytes())
        point['parentPointPins'] = [updated[digest(p)] for p in point['parentPointPins']]
        point['blockedReason'] = 'REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED'
        manifest = json.loads(Path(point['manifestPin']['path']).read_bytes())
        manifest['parentPointPins'] = point['parentPointPins']
        point['manifestPin'] = files.put(manifest)
        updated[digest(old)] = files.put(point)
    files.catalog = [{'pointPin': updated[digest(p)], 'completedAt': ago(30 - index * 10)}
                     for index, p in enumerate((full, first, second))]
    files.config['catalogPin'] = files.put({'schemaVersion': 'recovery-diagnostics-catalog/v1',
                                           'sourceScopePin': files.scope, 'points': files.catalog})
    selected = updated[digest(second)]
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': selected}, selected))
    assert code == 0 and result['data']['latestCompletePointPin'] == selected
    assert result['data']['requests'] and result['data']['recoveryAcceptanceVerdict'] == 'UNKNOWN'


def test_direct_parent_expression_is_rejected_after_first_incremental(files):
    full = files.point(completed_at=ago(30))
    first = files.point([full], completed_at=ago(20))
    second = files.point([first], completed_at=ago(10))
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': second}, second))
    assert code == 1 and result['failureCode'] == 'REPOSITORY_ANCESTOR_PREFIX_INVALID'


@pytest.mark.parametrize('reason', ['REPOSITORY_RECOVERY_REPORT_MISMATCH', 'ORIGINAL_EXIT_UNKNOWN', 'CORRUPT'])
def test_rehearsal_keeps_real_blocked_reasons(files, reason):
    pin = files.point()
    point = json.loads(Path(pin['path']).read_bytes())
    point['blockedReason'] = reason
    selected = files.put(point)
    files.catalog[0]['pointPin'] = selected
    files.config['catalogPin'] = files.put({'schemaVersion': 'recovery-diagnostics-catalog/v1',
                                           'sourceScopePin': files.scope, 'points': files.catalog})
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': selected}, selected))
    assert code == 1 and result['failureCode'] == 'LATEST_COMPLETE_POINT_MISSING'


@pytest.mark.parametrize('field,value', [('operationId', 'other-op'), ('state', 'UNKNOWN'),
    ('policyPin', 'different-policy'), ('writeProtectionState', 'RELEASED'), ('sourceWritesPerformed', True)])
def test_isolation_proof_checks_policy_and_target_facts(files, field, value):
    point = files.point()
    report_pin = files.report(point)
    report = json.loads(Path(report_pin['path']).read_bytes())
    app = json.loads(Path(report['applicationStartPin']['path']).read_bytes())
    proof = json.loads(Path(app['sideEffectIsolationPin']['path']).read_bytes())
    proof[field] = files.leaf if field == 'policyPin' else value
    app['sideEffectIsolationPin'] = files.put(proof)
    report['applicationStartPin'] = files.put(app)
    report_pin = files.put(report)
    wrapper = result_record(action='VERIFY_RECOVERY', operation='verified-op', data=report)
    files.config['verificationResultPin'] = files.put(wrapper)
    code, result = files.invoke(files.request('PLAN_REHEARSAL', {'repositoryPoint': point,
        'recoveryVerificationReport': report_pin}, point))
    assert code == 0 and 'VERIFICATION_APPLICATION_BINDING_INVALID' in result['data']['invalidatedBy']
    assert result['data']['latestProvenRecovery']['current'] is False


@pytest.mark.parametrize('defect', ['missing', 'no-lease', 'diagnostic-policy', 'unapproved-point', 'expired'])
def test_approved_rehearsal_template_prerequisites_fail_fast(files, defect):
    point = files.point()
    request = files.request('PLAN_REHEARSAL', {'repositoryPoint': point}, point)
    config = deepcopy(files.config)
    if defect == 'missing':
        config.pop('approvedRehearsalTemplatePin')
    elif defect in ('no-lease', 'diagnostic-policy'):
        template = json.loads(Path(config['approvedRehearsalTemplatePin']['path']).read_bytes())
        template['leaseRef' if defect == 'no-lease' else 'policyPin'] = None if defect == 'no-lease' else request['policyPin']
        config['approvedRehearsalTemplatePin'] = files.put(template)
        approval = json.loads(Path(config['rehearsalTemplateApprovalPin']['path']).read_bytes())
        approval['templatePin'] = config['approvedRehearsalTemplatePin']
        config['rehearsalTemplateApprovalPin'] = files.put(approval)
    else:
        approval = json.loads(Path(config['rehearsalTemplateApprovalPin']['path']).read_bytes())
        if defect == 'expired':
            approval['validUntil'] = ago(1)
        else:
            approval['permittedPointPins'] = []
        config['rehearsalTemplateApprovalPin'] = files.put(approval)
    request['policyPin'] = files.put({'diagnostics': config})
    code, result = files.invoke(request)
    assert code == 1 and result['state'] == 'FAILED_RETAINED'
    assert not list(files.evidence.glob('rehearsal-request-*.json'))


def test_self_nominated_subject_without_external_trust_is_unknown(files):
    evidence = files.put(files.execution())
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': evidence})
    code, result = files.invoke(request, provision_trust=False)
    assert code == 2 and result['failureCode'] == 'DIAGNOSTICS_TRUST_NOT_CONFIGURED'


def test_self_nominated_rehearsal_template_without_external_trust_is_blocked(files):
    point = files.point()
    request = files.request('PLAN_REHEARSAL', {'repositoryPoint': point}, point)
    code, result = files.invoke(request, provision_trust=False)
    assert code == 1 and result['failureCode'] == 'DIAGNOSTICS_TRUST_NOT_CONFIGURED'


def test_cached_subject_cannot_bypass_changed_independent_binding(files):
    evidence = files.put(files.execution())
    request = files.request('DIAGNOSE_EXECUTION', {'executionEvidence': evidence}, request_id='trust-cached')
    assert files.invoke(request)[0] == 0
    trust_path = Path(os.environ['RECOVERY_DIAGNOSTICS_TRUST_FILE'])
    trust = json.loads(trust_path.read_bytes())
    trust['executionSubjectBindingPin'] = files.leaf
    pin = files.put(trust)
    files.monkeypatch.setenv('RECOVERY_DIAGNOSTICS_TRUST_FILE', pin['path'])
    files.monkeypatch.setenv('RECOVERY_DIAGNOSTICS_TRUST_SHA256', pin['sha256'])
    code, result = files.invoke(request, provision_trust=False)
    assert code == 1 and result['failureCode'] == 'CACHED_INPUT_NOT_IN_PROVISIONED_TRUST'


@pytest.mark.parametrize('host_os', ['Linux', 'Windows'])
@pytest.mark.parametrize('action', ['DIAGNOSE_EXECUTION', 'OBSERVE_OPERATION'])
def test_current_v2_producer_shape_reconciles_without_version_unknown(files, host_os, action):
    import importlib.util
    source = ROOT / 'backend/src/main/resources/recovery_control_executor.py'
    spec = importlib.util.spec_from_file_location('w01_v2_shape_validator', source)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    evidence = files.execution(host_os=host_os)
    profile = json.loads(Path(files.native_profile_pin['path']).read_bytes())
    host = {k: profile[k] for k in ('hostOs', 'hostId', 'bootId', 'uid')}
    # Invoke only the actual producer's pure profile/registration validators.
    # Do not enter namespaces, spawn Linux processes or infer real acceptance.
    # Producer Pins use forward slashes on Windows; normalize the fixture and
    # repin its registration before the pure producer check, leaving consumer
    # originals untouched for their independent original-byte verification.
    def producer_pin(value):
        if type(value) is dict:
            if set(value) == {'path', 'bytes', 'sha256'}:
                return producer.pin(value['path'])
            return {k: producer_pin(v) for k, v in value.items()}
        return value
    checked_profile = producer_pin(profile)
    if host_os == 'Linux':
        registration = json.loads(Path(files.native_registration_pin['path']).read_bytes())
        checked_registration = producer_pin(registration)
        registration_path = files.root / 'producer-shape-registration.json'
        atomic_json(registration_path, checked_registration)
        checked_profile['namespaceRegistrationPin'] = producer.pin(str(registration_path.resolve()))
    assert producer.execution_profile(checked_profile, host) == checked_profile
    inputs = {'executionEvidence': files.put(evidence)}
    if action == 'OBSERVE_OPERATION':
        inputs['operationStatus'] = files.put(files.status('SUCCEEDED', files.put(result_record())))
    code, result = files.invoke(files.request(action, inputs))
    summary = result['data']['execution'] if action == 'OBSERVE_OPERATION' else result['data']
    assert code == 0 and result['failureCode'] is None
    assert summary['currentOriginalsVerified'] is True
    assert summary['subjectIdentity']['pid'] == 101
    assert files.native_profile_pin in result['originalResultPins']
    if host_os == 'Linux':
        assert files.native_registration_pin in result['originalResultPins']
        assert files.native_entry_pins[0] in result['originalResultPins']


@pytest.mark.parametrize('field,value,expected', [
    ('schemaVersion', 'RecoveryControlExecutionHost/v1', 'NATIVE_HOST_PROFILE_MISMATCH'),
    ('schemaVersion', 'RecoveryControlExecutionHost/v3', 'NATIVE_HOST_PROFILE_MISMATCH'),
    ('hostId', 'another-host', 'NATIVE_HOST_PROFILE_MISMATCH'),
    ('bootId', 'another-boot', 'NATIVE_HOST_PROFILE_MISMATCH'),
    ('uid', True, 'NAMESPACE_NATIVE_ROOT_REQUIRED'),
])
def test_current_v2_profile_version_and_host_mismatches_remain_unknown(files, field, value, expected):
    evidence = files.execution(profile_change=lambda p: p.update({field: value}))
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == expected
    assert result['data']['currentOriginalsVerified'] is False


@pytest.mark.parametrize('defect,expected', [
    ('version', 'NAMESPACE_REGISTRATION_VERSION_INVALID'),
    ('task', 'NAMESPACE_REGISTRATION_VERSION_INVALID'),
    ('host', 'NAMESPACE_HOST_IDENTITY_MISMATCH'),
    ('boot', 'NAMESPACE_HOST_IDENTITY_MISMATCH'),
    ('daemon-start', 'NAMESPACE_DAEMON_IDENTITY_REQUIRED'),
    ('namespace-path', 'NAMESPACE_FD_IDENTITY_REQUIRED'),
    ('namespace-inode', 'NAMESPACE_FD_IDENTITY_REQUIRED'),
])
def test_current_v2_registration_mismatch_is_not_terminal_success(files, defect, expected):
    def change(registration):
        if defect == 'version':
            registration['schemaVersion'] = 'RecoveryControlNamespaceRegistration/v2'
        elif defect == 'task':
            registration['taskId'] = 'another-task'
        elif defect in ('host', 'boot'):
            registration['hostId' if defect == 'host' else 'bootId'] = 'another-identity'
        elif defect == 'daemon-start':
            registration['daemon']['startTimeTicks'] = True
        else:
            registration['namespaces']['net']['path' if defect == 'namespace-path' else 'inode'] = (
                '/proc/999/ns/net' if defect == 'namespace-path' else 0)
    evidence = files.execution(registration_change=change)
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == expected
    assert result['data']['resourceTerminal'] is None


@pytest.mark.parametrize('defect,expected', [
    ('version', 'NAMESPACE_ENTRY_VERSION_INVALID'),
    ('host', 'NAMESPACE_ENTRY_HOST_MISMATCH'),
    ('boot', 'NAMESPACE_ENTRY_HOST_MISMATCH'),
    ('registration', 'NAMESPACE_ENTRY_HOST_MISMATCH'),
    ('attempt', 'NAMESPACE_ENTRY_SUBJECT_MISMATCH'),
    ('request', 'NAMESPACE_ENTRY_SUBJECT_MISMATCH'),
    ('profile', 'NAMESPACE_ENTRY_SUBJECT_MISMATCH'),
    ('daemon-pid', 'NAMESPACE_ENTRY_IDENTITY_MISMATCH'),
    ('daemon-start', 'NAMESPACE_ENTRY_IDENTITY_MISMATCH'),
    ('namespace-inode', 'NAMESPACE_ENTRY_IDENTITY_MISMATCH'),
    ('clock', 'NAMESPACE_ENTRY_CLOCK_BINDING_INVALID'),
])
def test_current_v2_namespace_entry_independently_matches_originals(files, defect, expected):
    def change(entry):
        if defect == 'version':
            entry['schemaVersion'] = 'RecoveryControlNamespaceEntry/v2'
        elif defect in ('host', 'boot'):
            entry['hostId' if defect == 'host' else 'bootId'] = 'another-identity'
        elif defect == 'attempt':
            entry['attemptId'] = 'another-attempt'
        elif defect in ('registration', 'request', 'profile'):
            entry[{'registration': 'namespaceRegistrationPin', 'request': 'requestPin',
                   'profile': 'profilePin'}[defect]] = files.leaf
        elif defect.startswith('daemon-'):
            entry['daemon']['pid' if defect == 'daemon-pid' else 'startTimeTicks'] += 1
        elif defect == 'namespace-inode':
            entry['namespaces']['mount']['inode'] += 1
        else:
            entry['enteredMonotonicNs'] = 4_000_000_000
    evidence = files.execution(entry_change=change)
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == expected
    assert result['data']['currentOriginalsVerified'] is False


@pytest.mark.parametrize('count', [0, 2])
def test_current_v2_namespace_entry_missing_or_ambiguous_remains_unknown(files, count):
    evidence = files.execution(entry_count=count)
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'NAMESPACE_ENTRY_MISSING_OR_AMBIGUOUS'


@pytest.mark.parametrize('original', ['profile', 'registration', 'entry'])
def test_current_v2_original_pin_content_changes_are_refused(files, original):
    evidence = files.execution()
    reference = {'profile': files.native_profile_pin, 'registration': files.native_registration_pin,
                 'entry': files.native_entry_pins[0]}[original]
    Path(reference['path']).write_bytes(b'changed-original')
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] in ('PIN_SIZE_MISMATCH', 'PIN_CONTENT_MISMATCH')
    assert result['data']['currentOriginalsVerified'] is False


def test_current_v2_registration_requires_independent_source_anchor(files):
    evidence = files.execution(source_change=lambda s: s['host'].update(namespaceRegistrationPin=files.leaf))
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': files.put(evidence)}))
    assert code == 2 and result['failureCode'] == 'NAMESPACE_REGISTRATION_NOT_SOURCE_ANCHORED'


@pytest.mark.skipif(sys.platform != 'win32', reason='Local Windows dispatcher check; no Linux namespace operations')
def test_actual_w01_native_producer_records_are_consumed_without_fake_resource_terminal(files):
    import importlib.util
    from types import SimpleNamespace
    source = ROOT / 'backend/src/main/resources/recovery_control_executor.py'
    before = pin_file(source)
    spec = importlib.util.spec_from_file_location('w01_actual_native_producer', source)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    script = files.root / 'local-read-only-child.py'
    script.write_text('''import argparse,json
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()
r=json.loads(Path(a.request).read_bytes());now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
o=dict(schemaVersion='backup-restore-operation-result/v1',operationId=r['operationId'],requestId=r['requestId'],action=r['action'],state='SUCCEEDED',failureCode=None,message='Local file consumer completed',data={'localSubprocessOnly':True},originalResultPins=[],startedAt=now,finishedAt=now,actualExitCode=None)
Path(a.output).write_text(json.dumps(o),encoding='utf-8')
''', encoding='utf-8')
    native_root = files.root / 'native-evidence'
    execution_root = native_root / 'operations' / 'observed-request'
    execution_root.mkdir(parents=True)
    profile = {'schemaVersion': 'RecoveryControlExecutionHost/v2', **producer.identity(), 'transport': 'LOCAL',
        'sourceProfilePin': producer.pin(files.leaf['path']), 'pythonPin': producer.pin(str(Path(sys.executable).resolve())),
        'dispatcherPin': producer.pin(str(source.resolve())), 'scriptPin': producer.pin(str(script.resolve())),
        'evidenceRoot': str(native_root.resolve()), 'workingDirectory': str(files.root.resolve()),
        'environment': {'PYTHONIOENCODING': 'utf-8'}, 'resourceObserverPin': None,
        'launcherPin': None, 'launcherArguments': [], 'namespaceRegistrationPin': None}
    profile_pin = files.put(profile)
    subject = result_record(action='LIST_POINTS')
    request = {'schemaVersion': 'backup-restore-operation/v1', 'operationId': subject['operationId'],
        'requestId': subject['requestId'], 'action': 'LIST_POINTS', 'mode': 'REHEARSAL', 'selectedPointPin': None,
        'sourceOrTargetRef': files.target, 'policyPin': files.environment_policy, 'authorizationRefs': [],
        'leaseRef': None, 'inputPins': {}, 'deadlineMilliseconds': 30000}
    request_pin = files.put(request)
    output = execution_root / 'result.json'
    args = SimpleNamespace(profile=profile_pin['path'], profile_sha256=profile_pin['sha256'],
        request=request_pin['path'], request_sha256=request_pin['sha256'], output=str(output.resolve()),
        attempt='actual-local-attempt', epoch='actual-local-epoch', verification_binding=None)
    assert producer.run(args) == 0
    envelope_pin = pin_file(execution_root / 'execution-evidence.json')
    envelope = json.loads(Path(envelope_pin['path']).read_bytes())
    assert envelope['exits']['executor'] == 0 and envelope['resourceTerminal'] is None
    files.native_binding = {'schemaVersion': 'RecoveryDiagnosticSubjectBinding/v1',
        'nativeProcessBindingPin': pin_file(execution_root / 'native-process-binding.json'),
        'executionEvidencePin': envelope_pin, 'operationResultPin': pin_file(output)}
    code, result = files.invoke(files.request('DIAGNOSE_EXECUTION', {'executionEvidence': envelope_pin},
                                             operation_id='separate-native-diagnostic'))
    assert code == 2 and result['failureCode'] == 'RESOURCE_TERMINAL_EVIDENCE_MISSING'
    assert result['data']['clockSetter'] == 'UNKNOWN' and result['data']['systemClockModified'] is False
    assert before == pin_file(source)
