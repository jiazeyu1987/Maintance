"""Append-only source restore boundaries, independent of archived backup formats.

Reads never initialize history. Writers require the caller's actual exclusive
Linux flock on the fixed capture/replacement lock before publishing any event.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


POLICY_FIELDS = {'schemaVersion', 'root', 'sourceIdentity', 'databaseUuid', 'sourceLockPath'}
EVENT_FIELDS = {'schemaVersion', 'sequence', 'kind', 'policySha256', 'sourceIdentity',
                'databaseUuid', 'sourceLockPath', 'operationId', 'state', 'previousSha256',
                'epochId', 'recordedAt', 'evidencePin'}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _path(value):
    _require(type(value) is str and Path(value).is_absolute(), 'BACKUP_EPOCH_ABSOLUTE_PATH_REQUIRED')
    result = Path(value)
    _require('..' not in result.parts and value in (str(result), result.as_posix()),
             'BACKUP_EPOCH_PATH_ALIAS_REJECTED')
    for component in (*reversed(result.parents), result):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        _require(not stat.S_ISLNK(info.st_mode) and
                 not getattr(info, 'st_file_attributes', 0) & 0x400,
                 'BACKUP_EPOCH_PATH_ALIAS_REJECTED')
        if component != result and os.name == 'posix':
            _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.geteuid()) and
                     (not info.st_mode & 0o022 or info.st_uid == 0 and info.st_mode & stat.S_ISVTX),
                     'BACKUP_EPOCH_WRITABLE_PARENT_REJECTED')
    return result


def validate_policy(policy):
    _require(type(policy) is dict and set(policy) == POLICY_FIELDS and
             policy.get('schemaVersion') == 'SourceBackupEpochPolicy/v1', 'BACKUP_EPOCH_POLICY_INVALID')
    _require(type(policy['sourceIdentity']) is str and
             re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,255}', policy['sourceIdentity']) and
             type(policy['databaseUuid']) is str and
             re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', policy['databaseUuid']),
             'BACKUP_EPOCH_POLICY_INVALID')
    root, lock = _path(policy['root']), _path(policy['sourceLockPath'])
    _require(root != Path(root.anchor) and root.is_dir() and lock.parent.is_dir() and
             lock != root and not lock.is_relative_to(root), 'BACKUP_EPOCH_POLICY_PATH_INVALID')
    if os.name == 'posix':
        info = root.stat()
        _require(info.st_uid == os.geteuid() and not info.st_mode & 0o077,
                 'BACKUP_EPOCH_PRIVATE_DIRECTORY_REQUIRED')
    if lock.exists():
        _regular(lock.stat(), private=True)
    return policy


def _regular(info, *, private=False):
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
             'BACKUP_EPOCH_REGULAR_SINGLE_LINK_REQUIRED')
    if os.name == 'posix':
        _require(info.st_uid == os.geteuid() and not info.st_mode & (0o077 if private else 0o022),
                 'BACKUP_EPOCH_FILE_PERMISSIONS_INVALID')


def _signature(info):
    stamp = info.st_birthtime_ns if os.name == 'nt' else info.st_ctime_ns
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp


def _read_file(path, limit=16384):
    path = _path(str(path)); before = path.stat(); _regular(before)
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    try:
        opened = os.fstat(fd); _regular(opened)
        _require(_signature(opened) == _signature(before), 'BACKUP_EPOCH_FILE_CHANGED')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        _require(_signature(opened) == _signature(after) == _signature(path.stat()),
                 'BACKUP_EPOCH_FILE_CHANGED')
    finally:
        os.close(fd)
    _require(len(raw) <= limit, 'BACKUP_EPOCH_INPUT_LIMIT')
    return raw, dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _parse(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result, 'BACKUP_EPOCH_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: _require(False, 'BACKUP_EPOCH_NONFINITE_JSON'))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('BACKUP_EPOCH_JSON_INVALID') from error


def _pinned_document(pin, kind):
    _require(type(pin) is dict and set(pin) == {'path', 'bytes', 'sha256'} and
             type(pin['bytes']) is int and pin['bytes'] >= 0 and type(pin['sha256']) is str and
             re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'BACKUP_EPOCH_' + kind + '_INVALID')
    try:
        raw, observed = _read_file(pin['path'], 65536)
    except OSError as error:
        raise ValueError('BACKUP_EPOCH_' + kind + '_UNAVAILABLE') from error
    _require(observed == pin, 'BACKUP_EPOCH_' + kind + '_CHANGED')
    return _parse(raw)


def _intent(pin, policy, operation):
    intent = _pinned_document(pin, 'INTENT')
    _require(type(intent) is dict and intent.get('schemaVersion') == 'ReplacementBackupEpochIntent/v1' and
             intent.get('operationId') == operation and intent.get('databaseUuid') == policy['databaseUuid'] and
             type(intent.get('targetConfigRef')) is str and 0 < len(intent['targetConfigRef']) <= 256 and
             type(intent.get('replacementReceiptPath')) is str, 'BACKUP_EPOCH_INTENT_INVALID')
    receipt = _path(intent['replacementReceiptPath'])
    _require(receipt.name == 'replacement-result.json' and receipt.parent.name == operation and
             not receipt.is_relative_to(Path(policy['root'])), 'BACKUP_EPOCH_RECEIPT_BINDING_INVALID')
    return intent


def _evidence(pin, operation, state, intent=None):
    receipt = _pinned_document(pin, 'EVIDENCE')
    _require(type(receipt) is dict and receipt.get('operationId') == operation and
             receipt.get('state') == ('SUCCEEDED' if state == 'READY' else 'FAILED_RETAINED'),
             'BACKUP_EPOCH_EVIDENCE_INVALID')
    if intent is not None:
        _require(_path(pin['path']) == _path(intent['replacementReceiptPath']) and
                 receipt.get('targetConfigRef') == intent['targetConfigRef'] and
                 receipt.get('databaseUuid') == intent['databaseUuid'], 'BACKUP_EPOCH_RECEIPT_BINDING_INVALID')


def _journal(policy):
    validate_policy(policy)
    root = Path(policy['root']); before = root.stat(); names = sorted(p.name for p in root.iterdir())
    _require(len(names) <= 50000 and all(re.fullmatch('[0-9]{20}\\.json', n) for n in names),
             'BACKUP_EPOCH_JOURNAL_INVALID')
    _require(names == ['%020d.json' % i for i in range(len(names))], 'BACKUP_EPOCH_CHAIN_INVALID')
    previous = None; previous_pin = None; operations = set()
    for sequence, name in enumerate(names):
        raw, pin = _read_file(root / name); event = _parse(raw)
        _require(type(event) is dict and set(event) == EVENT_FIELDS and
                 event['schemaVersion'] == 'SourceBackupEpochEvent/v1' and
                 type(event['sequence']) is int and event['sequence'] == sequence,
                 'BACKUP_EPOCH_EVENT_INVALID')
        _require(event['policySha256'] == _digest(policy) and
                 all(event[k] == policy[k] for k in ('sourceIdentity', 'databaseUuid', 'sourceLockPath')),
                 'BACKUP_EPOCH_POLICY_CHANGED')
        _require(raw == _canonical(event) and event['previousSha256'] ==
                 (None if previous_pin is None else previous_pin['sha256']), 'BACKUP_EPOCH_CHAIN_INVALID')
        _require(type(event['recordedAt']) is str and
                 re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z', event['recordedAt']),
                 'BACKUP_EPOCH_EVENT_INVALID')
        operation = event['operationId']
        if sequence == 0:
            _require(event['kind'] == 'INITIALIZED' and event['state'] == 'READY' and
                     operation is None and event['evidencePin'] is None, 'BACKUP_EPOCH_TRANSITION_INVALID')
        elif event['kind'] == 'RESTORE_STARTED':
            _require(previous['state'] in ('READY', 'FAILED_RETAINED') and event['state'] == 'REPLACING' and
                     type(operation) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}', operation) and
                     operation not in operations,
                     'BACKUP_EPOCH_TRANSITION_INVALID')
            if event['evidencePin'] is not None:
                _intent(event['evidencePin'], policy, operation)
            operations.add(operation)
        else:
            _require(event['kind'] == 'RESTORE_FINISHED' and previous['state'] == 'REPLACING' and
                     event['state'] in ('READY', 'FAILED_RETAINED') and operation == previous['operationId'] and
                     event['epochId'] == previous['epochId'], 'BACKUP_EPOCH_TRANSITION_INVALID')
            intent = None if previous['evidencePin'] is None else _intent(previous['evidencePin'], policy, operation)
            _evidence(event['evidencePin'], operation, event['state'], intent)
        if event['kind'] in ('INITIALIZED', 'RESTORE_STARTED'):
            _require(event['epochId'] == _digest({k:v for k,v in event.items() if k != 'epochId'}),
                     'BACKUP_EPOCH_EPOCH_INVALID')
        previous, previous_pin = event, pin
    validate_policy(policy)
    _require(_signature(root.stat()) == _signature(before) and
             sorted(p.name for p in root.iterdir()) == names, 'BACKUP_EPOCH_CHANGED')
    return previous, previous_pin


def _snapshot(event, pin):
    return dict(schemaVersion='SourceBackupEpoch/v1', policySha256=event['policySha256'],
                epochId=event['epochId'], state=event['state'], operationId=event['operationId'], eventPin=pin)


def read_current(policy):
    try:
        event, pin = _journal(policy)
    except OSError as error:
        raise ValueError('BACKUP_EPOCH_JOURNAL_UNAVAILABLE') from error
    _require(event is not None, 'BACKUP_EPOCH_UNINITIALIZED')
    return _snapshot(event, pin)


def _assert_lock(policy, lock_fd):
    validate_policy(policy)
    _require(sys.platform.startswith('linux') and type(lock_fd) is int,
             'BACKUP_EPOCH_LINUX_LOCK_REQUIRED')
    info = os.fstat(lock_fd); expected = _path(policy['sourceLockPath']).stat()
    _regular(info, private=True)
    _require((info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino),
             'BACKUP_EPOCH_SOURCE_LOCK_MISMATCH')
    # fdinfo reports locks held by this descriptor, not merely a lock somewhere
    # on the inode. A different or unlocked descriptor cannot authorize writes.
    lines = Path('/proc/self/fdinfo/' + str(lock_fd)).read_text(encoding='ascii').splitlines()
    locks = [line.split() for line in lines if line.startswith('lock:')]
    _require(any(len(parts) >= 7 and parts[2:5] == ['FLOCK', 'ADVISORY', 'WRITE'] and
                 parts[5] == str(os.getpid()) and parts[6].split(':')[-1] == str(info.st_ino)
                 for parts in locks), 'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED')


def _append(policy, previous, previous_pin, kind, state, operation, evidence, lock_fd):
    _assert_lock(policy, lock_fd)
    current, current_pin = _journal(policy)
    _require(current == previous and current_pin == previous_pin, 'BACKUP_EPOCH_CHANGED')
    event = dict(schemaVersion='SourceBackupEpochEvent/v1', sequence=0 if previous is None else previous['sequence']+1,
                 kind=kind, policySha256=_digest(policy), sourceIdentity=policy['sourceIdentity'],
                 databaseUuid=policy['databaseUuid'], sourceLockPath=policy['sourceLockPath'], operationId=operation,
                 state=state, previousSha256=None if previous_pin is None else previous_pin['sha256'],
                 recordedAt=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), evidencePin=evidence)
    event['epochId'] = previous['epochId'] if kind == 'RESTORE_FINISHED' else _digest(event)
    raw = _canonical(event); root = _path(policy['root'])
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = '.pending-' + os.urandom(16).hex()
    name = '%020d.json' % event['sequence']
    try:
        _require(_signature(os.fstat(directory)) == _signature(root.stat()), 'BACKUP_EPOCH_CHANGED')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        # link is an exclusive publication: no existing journal record can be
        # replaced. An interrupted publication stays visibly blocked.
        os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(directory)
    return read_current(policy)


def initialize(policy, lock_fd):
    """Explicit installation step; never called by read_current or backup planning."""
    _assert_lock(policy, lock_fd)
    previous, pin = _journal(policy)
    _require(previous is None, 'BACKUP_EPOCH_ALREADY_INITIALIZED')
    return _append(policy, None, None, 'INITIALIZED', 'READY', None, None, lock_fd)


def begin_restore(policy, operation_id, lock_fd, *, intent_pin=None):
    _assert_lock(policy, lock_fd)
    previous, pin = _journal(policy)
    _require(previous is not None, 'BACKUP_EPOCH_UNINITIALIZED')
    _require(previous['state'] != 'REPLACING', 'BACKUP_EPOCH_RESTORE_IN_PROGRESS')
    _require(type(operation_id) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}', operation_id),
             'BACKUP_EPOCH_OPERATION_INVALID')
    if intent_pin is not None:
        _intent(intent_pin, policy, operation_id)
    # All preceding operation identifiers are immutable; replay is rejected
    # before publication rather than poisoning the journal with a duplicate.
    for path in Path(policy['root']).iterdir():
        event = _parse(_read_file(path)[0])
        _require(event['operationId'] != operation_id, 'BACKUP_EPOCH_OPERATION_REUSED')
    return _append(policy, previous, pin, 'RESTORE_STARTED', 'REPLACING', operation_id, intent_pin, lock_fd)


def complete_restore(policy, operation_id, epoch_id, state, evidence_pin, lock_fd):
    _assert_lock(policy, lock_fd)
    previous, pin = _journal(policy)
    _require(previous is not None and previous['state'] == 'REPLACING' and
             previous['operationId'] == operation_id and previous['epochId'] == epoch_id and
             state in ('READY', 'FAILED_RETAINED'), 'BACKUP_EPOCH_TRANSITION_INVALID')
    intent = None if previous['evidencePin'] is None else _intent(previous['evidencePin'], policy, operation_id)
    _evidence(evidence_pin, operation_id, state, intent)
    return _append(policy, previous, pin, 'RESTORE_FINISHED', state, operation_id, evidence_pin, lock_fd)


def reconcile_completed_restore(policy, lock_fd):
    """Finalize only the original pinned intent's proven terminal receipt.

    This performs no restore, service restart, failure clearance, or inference
    from process liveness. FAILED_RETAINED remains ineligible for source backup.
    """
    _assert_lock(policy, lock_fd)
    previous, pin = _journal(policy)
    _require(previous is not None, 'BACKUP_EPOCH_UNINITIALIZED')
    if previous['state'] != 'REPLACING':
        return _snapshot(previous, pin)
    _require(previous['evidencePin'] is not None, 'BACKUP_EPOCH_RESTORE_INTENT_REQUIRED')
    intent = _intent(previous['evidencePin'], policy, previous['operationId'])
    try:
        raw, evidence = _read_file(intent['replacementReceiptPath'], 65536)
    except OSError as error:
        raise ValueError('BACKUP_EPOCH_TERMINAL_RECEIPT_UNAVAILABLE') from error
    receipt = _parse(raw)
    _require(type(receipt) is dict and receipt.get('state') in ('SUCCEEDED', 'FAILED_RETAINED'),
             'BACKUP_EPOCH_TERMINAL_RECEIPT_INVALID')
    state = 'READY' if receipt['state'] == 'SUCCEEDED' else 'FAILED_RETAINED'
    _evidence(evidence, previous['operationId'], state, intent)
    return complete_restore(policy, previous['operationId'], previous['epochId'], state, evidence, lock_fd)


def try_reconcile_current(policy):
    """Nonblocking metadata maintenance on a normal source-planning request.

    A busy physical source lock means the restore is still active; all other
    errors remain explicit. No new lock or epoch is implicitly initialized.
    """
    current = read_current(policy)
    if current['state'] != 'REPLACING':
        return current
    _require(sys.platform.startswith('linux'), 'BACKUP_EPOCH_LINUX_LOCK_REQUIRED')
    import fcntl
    try:
        fd = os.open(policy['sourceLockPath'], os.O_RDWR | os.O_NOFOLLOW)
    except OSError as error:
        raise ValueError('BACKUP_EPOCH_SOURCE_LOCK_UNAVAILABLE') from error
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return current
        return reconcile_completed_restore(policy, fd)
    finally:
        os.close(fd)
