"""Strict file protocol, pinned inputs and retained process evidence for W04."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import stat
import time
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

import jsonschema


class RecoveryError(Exception):
    def __init__(self, code, *, unknown=False, exit_code=None):
        super().__init__(code)
        self.code, self.unknown, self.exit_code = code, unknown, exit_code


READ_GUARD = ContextVar('recovery_repository_read_guard', default=None)


def repository_guard():
    return READ_GUARD.get()


def persist_evidence(path, value, pins=None, *, unknown=False, exit_code=None):
    """Recording failure must not replace an already uncertain execution."""
    original = sys.exception()
    try:
        ref = write(path, value)
    except Exception as recording:
        error = RecoveryError('RECOVERY_EVIDENCE_PERSISTENCE_FAILED',
            unknown=unknown or bool(getattr(original, 'unknown', False)) or repository_guard() is not None,
            exit_code=exit_code if exit_code is not None else getattr(original, 'exit_code', None))
        error.original_code = getattr(original, 'code', type(original).__name__ if original else None)
        error.original_pins = list(pins or getattr(original, 'original_pins', []))
        error.native = getattr(original, 'native', None)
        error.recording_error = type(recording).__name__
        # A separate receipt never rewrites the failed original. Failure of this
        # receipt is explicit on the raised error; it cannot imply completion.
        try:
            fault = write(Path(path).with_name(Path(path).name + '.recording-failure.json'),
                dict(schemaVersion='RecoveryEvidenceRecordingFailure/v1', originalCode=error.original_code,
                     recordingError=error.recording_error, state='TERMINAL_UNKNOWN' if error.unknown else 'FAILED_RETAINED',
                     actualExitCode=error.exit_code, originalPins=error.original_pins, failedEvidence=value))
            error.original_pins.append(fault)
            if pins is not None: pins.append(fault)
        except Exception as fault_error:
            error.fault_recording_error = type(fault_error).__name__
        raise error from recording
    if pins is not None: pins.append(ref)
    return ref


def require(condition, code):
    if not condition:
        raise RecoveryError(code)


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def absolute(path):
    require(type(path) is str and Path(path).is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    result = Path(path)
    if os.name == 'posix':
        # Resolving the whole ancestry separately for EVERY ancestor performs
        # quadratic path traversal, especially costly on NAS. lstat each
        # component once; do not cache a mutable path's identity across reads.
        require(result.anchor == '/' and '..' not in result.parts, 'PATH_ALIAS_REJECTED')
        for component in (*reversed(result.parents), result):
            try: info = component.lstat()
            except FileNotFoundError: continue  # output leaves may not exist yet
            require(not stat.S_ISLNK(info.st_mode), 'PATH_ALIAS_REJECTED')
        return result
    require(all(not p.is_symlink() and p.resolve() == p for p in (result, *result.parents)),
            'PATH_ALIAS_REJECTED')
    return result


def read_bytes(path, limit=64*1024*1024, *, budget=None):
    if budget is not None: budget.remaining()
    path = absolute(str(path))
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'INPUT_LIMIT_EXCEEDED')
    if budget is not None: budget.remaining()
    return raw


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, 'NONFINITE_JSON'))


def load(path, *, budget=None):
    return parse(read_bytes(path, budget=budget))


def pin(path, *, budget=None):
    if budget is not None: budget.remaining()
    path = absolute(str(path))
    before = path.stat(); checksum = hashlib.sha256(); size = 0
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'REGULAR_SINGLE_LINK_FILE_REQUIRED')
    with path.open('rb') as stream:
        while chunk := stream.read(1024*1024):
            if budget is not None: budget.remaining()
            checksum.update(chunk); size += len(chunk)
    if budget is not None: budget.remaining()
    return dict(path=str(path), bytes=size, sha256=checksum.hexdigest())


def signature(value):
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1, 'REGULAR_SINGLE_LINK_FILE_REQUIRED')
    # Python 3.12 Windows stat reports creation time in st_ctime, while fstat
    # reports NTFS change time. Birth time has consistent native semantics.
    timestamp = value.st_birthtime_ns if os.name == 'nt' else value.st_ctime_ns
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, timestamp


def check_pin(value, *, content=True, budget=None):
    if budget is not None: budget.remaining()
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and
            type(value['bytes']) is int and value['bytes'] >= 0 and
            type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'PIN_INVALID')
    path = absolute(value['path'])
    active = repository_guard()
    if active is not None: active.check_read(path)
    # Lightweight: parse required records without comparing their bytes/digests.
    if not content:
        return None
    with path.open('rb') as stream:
        raw = stream.read(64*1024*1024 + 1)
    require(len(raw) <= 64*1024*1024, 'JSON_INPUT_LIMIT')
    return raw


def pinned_json(value, *, budget=None):
    return parse(check_pin(value, budget=budget))


def write(path, value):
    """Atomic output in an existing private evidence directory."""
    try:
        return _write(path, value)
    except Exception as error:
        # With repository consumption admitted, incomplete evidence always
        # retains exclusion even when no new child was dispatched by this write.
        if repository_guard() is not None: error.unknown = True
        raise


def _write(path, value):
    path = absolute(str(path)); raw = canonical(value)
    temporary = path.with_name(path.name + '.' + os.urandom(8).hex() + '.tmp')
    with temporary.open('xb') as stream:
        os.chmod(temporary, 0o600)
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name == 'posix':
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return pin(path)


def validate_record(value, name, schema_pin):
    schema = pinned_json(schema_pin)
    require(name in schema['$defs'], 'RECORD_SCHEMA_MISSING')
    validator = jsonschema.Draft202012Validator(
        {'$ref': '#/$defs/' + name, '$defs': schema['$defs']},
        format_checker=jsonschema.FormatChecker())
    require(not list(validator.iter_errors(value)), 'RECORD_SCHEMA_INVALID_' + name.upper())
    return value


def current_window(value):
    def timestamp(text):
        require(type(text) is str and text.endswith('Z'), 'UTC_WINDOW_REQUIRED')
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    require(timestamp(value['validFrom']) <= now < timestamp(value['validUntil']),
            'AUTHORIZATION_OR_PROOF_EXPIRED')


def authorities(request, target_identity_pin, actions, trust):
    require(request['leaseRef'] is not None, 'LEASE_REQUIRED')
    lease = pinned_json(request['leaseRef'])
    target = pinned_json(target_identity_pin)
    require(request['leaseRef']['sha256'] in trust['leaseSha256s'], 'LEASE_NOT_TRUSTED')
    require(lease['schemaVersion'] == 'RecoveryEnvironmentLease/v1' and lease['state'] == 'HELD' and
            lease['operationId'] == request['operationId'] and
            lease['targetId'] == target['targetId'] and lease['executorId'] == trust['executorId'] and
            type(lease['fenceToken']) is int and lease['fenceToken'] > 0, 'LEASE_BINDING_INVALID')
    current_window({'validFrom': lease['notBefore'], 'validUntil': lease['expiresAt']})
    allowed = set()
    for ref in request['authorizationRefs']:
        grant = pinned_json(ref)
        require(ref['sha256'] in trust['authorizationSha256s'], 'AUTHORIZATION_NOT_TRUSTED')
        require(grant['schemaVersion'] == 'RecoveryEnvironmentAuthorization/v1' and
                grant['approved'] is True and
                grant['operationId'] == request['operationId'] and
                grant['targetId'] == target['targetId'] and grant['mode'] == request['mode'] and
                grant['executorId'] == trust['executorId'], 'AUTHORIZATION_BINDING_INVALID')
        current_window({'validFrom': grant['notBefore'], 'validUntil': grant['expiresAt']})
        allowed.update(grant['actions'])
    require(set(actions) <= allowed, 'ACTION_AUTHORIZATION_REQUIRED')


class Budget:
    def __init__(self, milliseconds):
        require(type(milliseconds) is int and milliseconds > 0, 'DEADLINE_INVALID')
        self.deadline = time.monotonic() + milliseconds/1000

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, 'DEADLINE_EXCEEDED')
        return remaining

    def milliseconds(self):
        return max(1, math.floor(self.remaining()*1000))


class InvocationRunner:
    """No retries. Timeout after dispatch is unknown even if client was killed."""
    def __init__(self, root, budget):
        self.root = absolute(str(root)); self.budget = budget
        self.original_pins = []; self.actual_exit_code = None
        self.sequence = 0
        self.readers_terminal = True
        self.invocation_unknown = False

    def run(self, *args, **kwargs):
        self.invocation_unknown = False
        self.actual_exit_code = None
        try:
            return self._run(*args, **kwargs)
        except Exception as error:
            error.unknown = bool(getattr(error, 'unknown', False)) or self.invocation_unknown
            error.exit_code = self.actual_exit_code
            error.original_pins = list(self.original_pins)
            if error.unknown: self.readers_terminal = False
            raise

    def _run(self, python_pin, script_pin, request, *, style='operation', guard, lock_fd=None,
            execution_context=None, terminal_verifier=None):
        guard(); check_pin(python_pin, content=False); check_pin(script_pin, content=False)
        self.sequence += 1
        base = self.root / ('invocation-%03d' % self.sequence)
        base.mkdir(mode=0o700)
        request_pin = write(base/'request.json', request)
        argv = [python_pin['path'], script_pin['path'], '--request', request_pin['path']]
        if style == 'operation':
            argv += ['--output', str(base/'result.json')]
        else:
            argv += ['--expected-request-sha256', request_pin['sha256']]
        intent = write(base/'intent.json', dict(schemaVersion='recovery-invocation/v1',
                     scriptPin=script_pin, pythonPin=python_pin, requestPin=request_pin,
                     startedAt=utc(), style=style, executionContextPins=execution_context or {}))
        self.original_pins.extend([intent, request_pin])
        timed_out = False; actual = None
        timeout = self.budget.remaining()
        with (base/'stdout').open('xb') as stdout, (base/'stderr').open('xb') as stderr:
            os.chmod(base/'stdout', 0o600); os.chmod(base/'stderr', 0o600)
            options = {}
            environment = dict(os.environ)
            if execution_context is not None:
                require(set(execution_context) <= {'RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN'}, 'EXECUTION_CONTEXT_KEY_INVALID')
                for key, ref in execution_context.items():
                    check_pin(ref); environment[key] = canonical(ref).decode('utf-8')
                options['env'] = environment
            if lock_fd is not None:
                require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
                options.update(pass_fds=(lock_fd,), env=dict(environment, RECOVERY_DATA_LOCK_FD=str(lock_fd)))
            active = repository_guard()
            if active is not None:
                options.update(active.child_options(options.get('env', environment), options.get('pass_fds', ())))
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, **options)
            self.invocation_unknown = True
            try:
                actual = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                try:
                    actual = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    actual = None
        self.actual_exit_code = actual
        # Executors may print credentials. Retain the exact hashes and sizes,
        # never publish their raw streams as public evidence.
        terminal = persist_evidence(base/('client-exit.json' if terminal_verifier is not None else 'exit.json'), dict(schemaVersion='recovery-original-exit/v1',
                        intentPin=intent, nativePid=process.pid, processTerminated=actual is not None,
                        actualExitCode=actual, timedOut=timed_out,
                        remoteTerminalConfirmed=False if timed_out else None, finishedAt=utc()), self.original_pins,
                        unknown=self.invocation_unknown, exit_code=actual)
        streams = persist_evidence(base/'streams.json', {name: {k: v for k, v in pin(base/name).items() if k != 'path'}
                                             for name in ('stdout', 'stderr')}, self.original_pins,
                                             unknown=self.invocation_unknown, exit_code=actual)
        if style == 'operation':
            (base/'stdout').unlink(); (base/'stderr').unlink()
        if timed_out:
            raise RecoveryError('EXECUTOR_TERMINAL_UNKNOWN', unknown=True, exit_code=actual)
        require(actual is not None, 'EXECUTOR_EXIT_MISSING')
        guard(); check_pin(script_pin, content=False); check_pin(python_pin, content=False)
        if style == 'operation':
            if not (base/'result.json').is_file():
                raise RecoveryError('EXECUTOR_RESULT_MISSING', unknown=True, exit_code=actual)
            result_pin = pin(base/'result.json'); result = pinned_json(result_pin)
            self.original_pins.append(result_pin)
            require(result['operationId'] == request['operationId'] and
                    result['requestId'] == request['requestId'] and result['action'] == request['action'],
                    'EXECUTOR_RESULT_BINDING_INVALID')
            require(result['state'] in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN'), 'EXECUTOR_STATE_INVALID')
            require(actual == {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']],
                    'EXECUTOR_EXIT_STATE_MISMATCH')
            self.invocation_unknown = result['state'] == 'TERMINAL_UNKNOWN' or terminal_verifier is not None
            if result['state'] != 'SUCCEEDED':
                raise RecoveryError('EXECUTOR_RESULT_' + result['state'],
                                    unknown=result['state'] == 'TERMINAL_UNKNOWN', exit_code=actual)
        else:
            require(actual == 0, 'EXECUTOR_FAILED_RETAINED')
            raw = read_bytes(base/'stdout')
            result = parse(raw); result_pin = write(base/'result.json', result)
            (base/'stdout').unlink(); (base/'stderr').unlink()
            self.original_pins.append(result_pin)
        if terminal_verifier is not None:
            try:
                confirmed, proof_refs = terminal_verifier(result, request)
                require(confirmed in (None, True), 'REMOTE_TERMINAL_VERIFIER_RESULT_INVALID')
                for ref in proof_refs: check_pin(ref, content=False)
                # Keep the first immutable local exit. Remote proof is a new
                # terminal original, never an inference or rewriting its Pin.
                self.original_pins.extend(proof_refs)
                combined = write(base/'exit.json', dict(schemaVersion='recovery-original-exit/v1',
                    intentPin=intent, localExitPin=terminal, actualExitCode=actual, timedOut=False,
                    remoteTerminalConfirmed=confirmed, remoteTerminalProofPins=proof_refs, finishedAt=utc()))
                self.original_pins.append(combined)
                self.invocation_unknown = False
            except Exception as error:
                raise RecoveryError('EXECUTOR_REMOTE_TERMINAL_UNKNOWN', unknown=True, exit_code=actual) from error
        else:
            self.invocation_unknown = False
        return result, result_pin
