"""Process locks and durable request journals; interrupted work is never replayed."""
from __future__ import annotations

import os
from pathlib import Path

from recovery_engine import RecoveryError, absolute, digest, load, require, utc, write


class FileLock:
    def __init__(self, path):
        self.path = absolute(str(path)); self.stream = None

    def __enter__(self):
        self.stream = self.path.open('a+b'); os.chmod(self.path, 0o600)
        try:
            if os.name == 'posix':
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif os.name == 'nt':
                import msvcrt
                self.stream.seek(0); self.stream.write(b'\0'); self.stream.flush(); self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                raise RecoveryError('NATIVE_LOCK_PLATFORM_UNSUPPORTED')
        except OSError as error:
            self.stream.close(); self.stream = None
            raise RecoveryError('RESOURCE_ALREADY_EXECUTING') from error
        return self

    def __exit__(self, *args):
        if self.stream is not None:
            if os.name == 'posix':
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            else:
                import msvcrt
                self.stream.seek(0); msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close(); self.stream = None

    @property
    def fd(self):
        require(self.stream is not None, 'TARGET_LOCK_NOT_HELD')
        return self.stream.fileno()


def target_lock_path(policy, identity_pin):
    return absolute(policy['evidenceRoot']) / ('target-' + digest(identity_pin) + '.lock')


def inherited_target_lock(policy, identity_pin):
    """Worker can only mutate while its supervisor's target lock is inherited."""
    require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
    text = os.environ.get('RECOVERY_DATA_LOCK_FD')
    require(text and text.isdecimal(), 'SUPERVISOR_TARGET_LOCK_REQUIRED')
    fd = int(text); observed = os.fstat(fd); expected = target_lock_path(policy, identity_pin).stat()
    require((observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino), 'SUPERVISOR_LOCK_BINDING_INVALID')
    # A second independent open must conflict with the inherited open description.
    import fcntl
    with target_lock_path(policy, identity_pin).open('a+b') as other:
        try:
            fcntl.flock(other.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return fd
        fcntl.flock(other.fileno(), fcntl.LOCK_UN)
    raise RecoveryError('SUPERVISOR_TARGET_LOCK_NOT_HELD')


class Journal:
    def __init__(self, root, request):
        self.root = absolute(str(root)); self.request = request
        self.path = self.root/('request-' + digest(request['requestId']) + '.json')
        self.value = None

    def begin(self, *, budget=None):
        if self.path.exists():
            value = load(self.path)
            require(value['requestSha256'] == digest(self.request), 'REQUEST_ID_CONTENT_CONFLICT')
            if value['state'] == 'RUNNING':
                raise RecoveryError('INTERRUPTED_EXECUTION_RECONCILIATION_REQUIRED', unknown=True)
            require(value['state'] in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN'), 'JOURNAL_STATE_INVALID')
            if value['state'] == 'TERMINAL_UNKNOWN' and value['resultPin'] is None:
                error = RecoveryError('TERMINAL_PUBLICATION_RECONCILIATION_REQUIRED', unknown=True,
                    exit_code=value['actualExitCode'])
                error.original_pins = value['originalResultPins']
                raise error
            from recovery_engine import check_pin, pinned_json
            if value['state'] == 'SUCCEEDED':
                result = None
                try:
                    result = pinned_json(value['resultPin'], budget=budget)
                    require(result['state'] == value['state'] and value['cacheEvidencePins'],
                            'SUCCESS_CACHE_EVIDENCE_REQUIRED')
                    for ref in value['cacheEvidencePins']:
                        require(pinned_json(ref, budget=budget) == result, 'SUCCESS_CACHE_EVIDENCE_CHANGED')
                    # Summary equality does not establish that its referenced
                    # intent/request/exit/streams/result originals still exist.
                    for ref in result['originalResultPins']:
                        check_pin(ref, content=False, budget=budget)
                    if budget is not None: budget.remaining()
                except Exception as recording:
                    error = RecoveryError('TERMINAL_PUBLICATION_RECONCILIATION_REQUIRED', unknown=True,
                        exit_code=result.get('actualExitCode') if result is not None else None)
                    error.original_pins = result.get('originalResultPins', []) if result is not None else []
                    raise error from recording
            else:
                result = pinned_json(value['resultPin'])
                require(result['state'] == value['state'], 'JOURNAL_RESULT_STATE_MISMATCH')
            return result
        self.value = dict(schemaVersion='RecoveryRequestJournal/v1', requestId=self.request['requestId'],
            operationId=self.request['operationId'], requestSha256=digest(self.request), state='RUNNING',
            resultPin=None, phase='ADMITTED', phaseEvidencePins=[], updatedAt=utc())
        write(self.path, self.value)
        return None

    def phase(self, name, refs):
        require(self.value is not None and self.value['state'] == 'RUNNING', 'JOURNAL_NOT_RUNNING')
        self.value.update(phase=name, updatedAt=utc())
        self.value['phaseEvidencePins'].extend(refs); write(self.path, self.value)

    def finish(self, result_pin, state):
        self.value.update(state=state, resultPin=result_pin, phase='TERMINAL', updatedAt=utc())
        write(self.path, self.value)

    def reconcile(self, error):
        # Invalidate a possibly replaced successful journal before any fallible
        # correction of its result. This record does not assert a result Pin.
        self.value.update(state='TERMINAL_UNKNOWN', resultPin=None, phase='RECONCILIATION_REQUIRED',
            originalResultPins=error.original_pins, actualExitCode=error.exit_code, updatedAt=utc())
        write(self.path, self.value)
