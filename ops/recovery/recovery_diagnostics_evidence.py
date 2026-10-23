"""Record real monotonic/wall observations; summarize facts without running recovery."""
import re
import time

from recovery_diagnostics_io import (DiagnosticError, atomic_json, exact, require)


class ExecutionRecorder:
    """Executor instrumentation API. The caller supplies its real identity and facts.

    No process is started, killed, retried or inferred terminal by this recorder.
    stdout/stderr are pinned private originals, never copied into public evidence.
    """
    def __init__(self, path, operation_id, attempt_id, observer_epoch, host_id, boot_id):
        require(all(type(v) is str and v for v in
                    (operation_id, attempt_id, observer_epoch, host_id, boot_id)), 'IDENTITY_REQUIRED')
        self.path = path
        self.record = {'schemaVersion': 'recovery-execution-evidence/v1',
                       'operationId': operation_id, 'attemptId': attempt_id,
                       'observerEpoch': observer_epoch,
                       'clockDomain': {'hostId': host_id, 'bootId': boot_id}, 'samples': [],
                       'exits': {'executor': None, 'runner': None, 'test': None},
                       'timedOut': False, 'timeoutLayer': None, 'complete': False,
                       'processTerminal': None, 'resourceTerminal': None,
                       'streamRefs': {'stdout': None, 'stderr': None}, 'originalPins': []}

    def sample(self, phase, bytes_processed=0, count=0, cpu_nanoseconds=None,
               resident_bytes=None, stop_writes=False):
        require(not self.record['complete'], 'EVIDENCE_ALREADY_FINISHED')
        sample = {'monotonicNs': time.monotonic_ns(), 'wallNs': time.time_ns(),
                  'phase': phase, 'bytes': bytes_processed, 'count': count,
                  'cpuNanoseconds': cpu_nanoseconds, 'residentBytes': resident_bytes,
                  'stopWrites': stop_writes}
        validate_sample(sample)
        self.record['samples'].append(sample)
        atomic_json(self.path, self.record)

    def finish(self, executor_exit, runner_exit, test_exit, timed_out, timeout_layer,
               process_terminal, resource_terminal, stream_refs, original_pins):
        require(not self.record['complete'], 'EVIDENCE_ALREADY_FINISHED')
        self.record.update(exits={'executor': executor_exit, 'runner': runner_exit, 'test': test_exit},
                           timedOut=timed_out, timeoutLayer=timeout_layer,
                           processTerminal=process_terminal, resourceTerminal=resource_terminal,
                           streamRefs=stream_refs, originalPins=original_pins, complete=True)
        validate_execution(self.record)
        atomic_json(self.path, self.record)


def validate_sample(sample):
    exact(sample, ('monotonicNs', 'wallNs', 'phase', 'bytes', 'count', 'cpuNanoseconds',
                   'residentBytes', 'stopWrites'), 'SAMPLE_SHAPE_INVALID')
    for key in ('monotonicNs', 'wallNs', 'bytes', 'count'):
        require(type(sample[key]) is int and sample[key] >= 0, 'SAMPLE_NUMBER_INVALID')
    for key in ('cpuNanoseconds', 'residentBytes'):
        require(sample[key] is None or type(sample[key]) is int and sample[key] >= 0,
                'SAMPLE_RESOURCE_INVALID')
    require(type(sample['phase']) is str and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,80}', sample['phase']),
            'SAMPLE_PHASE_INVALID')
    require(type(sample['stopWrites']) is bool, 'SAMPLE_STOP_WRITES_INVALID')


def validate_execution(record):
    exact(record, ('schemaVersion', 'operationId', 'attemptId', 'observerEpoch', 'clockDomain',
                   'samples', 'exits', 'timedOut', 'timeoutLayer', 'complete', 'processTerminal',
                   'resourceTerminal', 'streamRefs', 'originalPins'), 'EXECUTION_SHAPE_INVALID')
    require(record['schemaVersion'] == 'recovery-execution-evidence/v1', 'EXECUTION_VERSION_INVALID')
    require(all(type(record[k]) is str and record[k] for k in
                ('operationId', 'attemptId', 'observerEpoch')), 'EXECUTION_IDENTITY_INVALID')
    exact(record['clockDomain'], ('hostId', 'bootId'), 'CLOCK_DOMAIN_INVALID')
    require(all(type(v) is str and v for v in record['clockDomain'].values()), 'CLOCK_DOMAIN_INVALID')
    exact(record['exits'], ('executor', 'runner', 'test'), 'EXIT_SHAPE_INVALID')
    require(all(v is None or type(v) is int for v in record['exits'].values()), 'EXIT_TYPE_INVALID')
    exact(record['streamRefs'], ('stdout', 'stderr'), 'STREAM_SHAPE_INVALID')
    require(type(record['originalPins']) is list, 'ORIGINAL_PINS_INVALID')
    require(type(record['samples']) is list and bool(record['samples']), 'CLOCK_SAMPLES_MISSING')
    require(len(record['samples']) <= 100_000, 'CLOCK_SAMPLES_LIMIT_EXCEEDED')
    for sample in record['samples']:
        validate_sample(sample)
    for key in ('complete', 'timedOut'):
        require(type(record[key]) is bool, 'EXECUTION_BOOLEAN_INVALID')
    for key in ('processTerminal', 'resourceTerminal'):
        require(record[key] is None or type(record[key]) is bool, 'TERMINAL_TYPE_INVALID')
    require(record['timeoutLayer'] in (None, 'EXECUTOR', 'RUNNER', 'TOOL'), 'TIMEOUT_LAYER_INVALID')
    require(record['timedOut'] == (record['timeoutLayer'] is not None), 'TIMEOUT_LAYER_MISMATCH')
    require(record['processTerminal'] is not True or record['exits']['executor'] is not None,
            'TERMINAL_EXIT_MISSING')


def summarize_execution(record, guard_ns):
    validate_execution(record)
    require(type(guard_ns) is int and guard_ns > 0, 'CLOCK_GUARD_INVALID')
    samples = record['samples']
    first, last = samples[0], samples[-1]
    segments, phases, problems = [], {}, []
    for left, right in zip(samples, samples[1:]):
        mono = right['monotonicNs'] - left['monotonicNs']
        wall = right['wallNs'] - left['wallNs']
        skew = wall - mono
        if mono < 0:
            problems.append('MONOTONIC_REGRESSION')
        if wall < 0:
            problems.append('WALL_CLOCK_REVERSED')
        if abs(skew) >= guard_ns:
            problems.append('CLOCK_GUARD_REJECTED')
        for key in ('bytes', 'count', 'cpuNanoseconds'):
            if left[key] is not None and right[key] is not None and right[key] < left[key]:
                problems.append('COUNTER_REGRESSION')
        segments.append({'phase': left['phase'], 'elapsedNs': mono, 'wallDeltaNs': wall,
                         'wallMinusMonotonicNs': skew})
        phases[left['phase']] = phases.get(left['phase'], 0) + mono
    elapsed = last['monotonicNs'] - first['monotonicNs']
    cumulative = last['wallNs'] - first['wallNs'] - elapsed
    if abs(cumulative) >= guard_ns:
        problems.append('CUMULATIVE_CLOCK_GUARD_REJECTED')
    exits = record['exits']
    code = None
    state = 'SUCCEEDED'
    if not record['complete'] or record['processTerminal'] is not True or exits['executor'] is None:
        state, code = 'TERMINAL_UNKNOWN', 'EXECUTOR_TERMINAL_UNKNOWN'
    elif record['resourceTerminal'] is not True:
        state, code = 'TERMINAL_UNKNOWN', 'RESOURCE_TERMINAL_UNKNOWN'
    elif record['timedOut']:
        state, code = 'FAILED_RETAINED', 'EXECUTION_TIMEOUT'
    elif any(v is not None and v != 0 for v in exits.values()):
        state, code = 'FAILED_RETAINED', 'ORIGINAL_EXECUTION_FAILED'
    elif problems:
        state, code = 'FAILED_RETAINED', problems[0]
    return {'state': state, 'failureCode': code, 'actualExitCode': exits['executor'],
            'exits': exits, 'timedOut': record['timedOut'], 'timeoutLayer': record['timeoutLayer'],
            'clockDomain': record['clockDomain'], 'elapsedNs': elapsed if elapsed >= 0 else None,
            'wallDeltaNs': last['wallNs'] - first['wallNs'],
            'cumulativeWallMinusMonotonicNs': cumulative, 'clockProblems': sorted(set(problems)),
            'clockSetter': 'UNKNOWN', 'segments': segments, 'phaseElapsedNs': phases,
            'stopWritesElapsedNs': sum(s['elapsedNs'] for s, left in zip(segments, samples)
                                      if left['stopWrites']),
            'bytes': last['bytes'], 'count': last['count'],
            'peakResidentBytes': max((s['residentBytes'] for s in samples
                                      if s['residentBytes'] is not None), default=None),
            'cpuNanoseconds': last['cpuNanoseconds'], 'processTerminal': record['processTerminal'],
            'resourceTerminal': record['resourceTerminal']}


def summarize_legacy(envelope, reader, legacy_contracts, binding):
    """Consume the frozen diagnostic-evidence/v1 with its pinned original runner.

    This is an explicit existing interface, not a guessed alternate data source.
    Raw streams are hashed; no raw text, argv or exception contents are published.
    """
    legacy_contracts.validate('diagnosticEvidence', envelope)
    reader.verify_nested(envelope)
    runner = reader.read(envelope['runnerResultReference'])
    for key in ('runnerClassificationCode', 'timedOut', 'classificationIsSynthetic'):
        require(key in runner and runner[key] == envelope[key], 'LEGACY_ORIGINAL_RESULT_MISMATCH')
    for key in ('clientReturncode', 'pytestReturncode'):
        require(envelope[key] is None or runner[key] == envelope[key], 'LEGACY_ORIGINAL_RESULT_MISMATCH')
    require(runner['attempt'] == binding.get('attemptId'), 'LEGACY_ATTEMPT_BINDING_INVALID')
    original_tool = reader.read(envelope['originalProcessReference'])
    profile = binding.get('toolResultProfile')
    if profile == 'exec-command-result':
        require(type(original_tool.get('result')) is dict and 'exit_code' in original_tool['result'],
                'LEGACY_TOOL_RESULT_REQUIRED')
        tool_exit = original_tool['result']['exit_code']
    elif profile == 'codex-command-event':
        event = original_tool['payload']['item']
        require(event['type'] == 'CommandExecution' and event['status'] in ('completed', 'inProgress'),
                'LEGACY_TOOL_EVENT_INVALID')
        tool_exit = event.get('exitCode') if event['status'] == 'completed' else None
    else:
        raise DiagnosticError('LEGACY_TOOL_RESULT_PROFILE_REQUIRED')
    require(tool_exit is None or type(tool_exit) is int, 'LEGACY_TOOL_EXIT_INVALID')
    require(tool_exit is None or tool_exit == envelope['runnerClassificationCode'], 'LEGACY_TOOL_EXIT_MISMATCH')
    start, end = runner['hostStartMonotonicNs'], runner['hostRunEndMonotonicNs']
    require(type(start) is int and type(end) is int and 0 <= start <= end,
            'LEGACY_MONOTONIC_EVIDENCE_INVALID')
    elapsed = end - start
    if 'hostElapsedNs' in runner:
        require(runner['hostElapsedNs'] == elapsed, 'LEGACY_MONOTONIC_EVIDENCE_MISMATCH')
    for name, field in (('stdout', 'stdoutReference'), ('stderr', 'stderrReference')):
        stream = runner['streams'][name]
        require(stream['bytes'] == envelope[field]['bytes'] and
                stream['sha256'] == envelope[field]['sha256'], 'LEGACY_STREAM_MISMATCH')
    actual = envelope['clientReturncode']
    state, code = 'TERMINAL_UNKNOWN', 'RESOURCE_TERMINAL_UNKNOWN'
    if not envelope['evidenceComplete'] or actual is None or not runner['ownedClientTerminalConfirmed']:
        code = 'ORIGINAL_EVIDENCE_INCOMPLETE'
    # The frozen envelope deliberately cannot prove tree/container termination.
    require(type(runner['instrumentationErrors']) is list and
            all(type(code) is str and re.fullmatch(r'[A-Z0-9_]{1,100}', code)
                for code in runner['instrumentationErrors']), 'LEGACY_ERROR_CODES_INVALID')
    return {'state': state, 'failureCode': code, 'actualExitCode': actual,
            'exits': {'executor': actual, 'runner': envelope['runnerClassificationCode'],
                      'test': envelope['pytestReturncode']}, 'timedOut': envelope['timedOut'],
            'toolExitCode': tool_exit, 'observedClientExitCode': runner['clientReturncode'],
            'timeoutLayer': 'RUNNER' if envelope['timedOut'] else None,
            'classificationIsSynthetic': envelope['classificationIsSynthetic'],
            'elapsedNs': elapsed, 'clockProblems': [], 'clockSetter': 'UNKNOWN',
            'wallDeltaNs': None, 'processTerminal': runner['ownedClientTerminalConfirmed'],
            'resourceTerminal': None, 'streams': runner['streams'],
            'pytestEvidence': None if runner['pytestEvidence'] is None else {
                k: runner['pytestEvidence'][k] for k in
                ('eventStreamValid', 'sessionFinished', 'sessionExit', 'completedCount')},
            'instrumentationErrors': list(runner['instrumentationErrors'])}
