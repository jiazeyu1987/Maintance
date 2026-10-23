"""Task-private Spug transport and durable small-app operation ledger.

The HTTP entry consumes Spug's existing request/result contract. No shell
command, credential parameter or backup algorithm is accepted from callers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys
import threading
import uuid

BATCH = 'SMALL_APP_REAL_FULL_INCREMENTAL_RESTORE'
ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
MAX_FRAME = 65536
REQUEST_FIELDS = 'schemaVersion operationId action sourceConfigRef parentChainRef recoveryPointRef targetConfigRef'
RESULT_FIELDS = 'schemaVersion operationId action state errorCode logRefs resultRef'


class Failure(RuntimeError):
    pass


def need(condition, code):
    if not condition:
        raise Failure(code)


def exact(value, fields, code):
    need(type(value) is dict and set(value) == set(fields.split()), code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, 'DUPLICATE_JSON_KEY')
            value[key] = item
        return value
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: need(False, 'NONFINITE_JSON_NUMBER'))
    except (ValueError, UnicodeError, RecursionError):
        raise Failure('JSON_INVALID') from None


def opaque(value):
    need(type(value) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,159}', value) and value not in ('.', '..'),
         'OPAQUE_REFERENCE_INVALID')
    return value


def operation_id(value):
    opaque(value)
    need(len(value) >= 8 and not PureWindowsPath(value).drive, 'OPERATION_ID_INVALID')
    return value


def request(value):
    exact(value, REQUEST_FIELDS, 'UI_REQUEST_FIELDS_INVALID')
    need(value['schemaVersion'] == 'SmallAppBackupUiRequest/v1', 'UI_REQUEST_VERSION_INVALID')
    operation_id(value['operationId'])
    opaque(value['sourceConfigRef'])
    action = value['action']
    need(action in ('FULL', 'INCREMENTAL', 'RESTORE'), 'ACTION_INVALID')
    parent, point, target = (value[k] for k in ('parentChainRef', 'recoveryPointRef', 'targetConfigRef'))
    if action == 'FULL':
        need(parent is point is target is None, 'FULL_REFERENCES_FORBIDDEN')
    elif action == 'INCREMENTAL':
        opaque(parent)
        need(point is target is None, 'INCREMENTAL_REFERENCES_INVALID')
    else:
        opaque(point)
        opaque(target)
        need(parent is None and target != value['sourceConfigRef'], 'RESTORE_REFERENCES_INVALID')
    return value


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def result(value, state, error=None):
    return dict(schemaVersion='SmallAppBackupUiResult/v1', operationId=value['operationId'],
                action=value['action'], state=state, errorCode=error,
                logRefs=[value['operationId'] + '-originals'], resultRef=value['operationId'] + '-result')


def public_error(error):
    code = str(error) if isinstance(error, RuntimeError) else getattr(error, 'code', None)
    if type(code) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}', code):
        return code
    return 'SMALLAPP_' + type(error).__name__.upper()


def local_read(path, limit=1048576):
    """Ledger originals are one-link private regular files, never symlink aliases."""
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, 'LEDGER_PATH_INVALID')
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)), 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
             'LEDGER_FILE_INVALID')
        if os.name == 'posix':
            need(before.st_uid == before.st_gid == 0 and stat.S_IMODE(before.st_mode) == 0o600,
                 'LEDGER_CUSTODY_INVALID')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    key = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    need(key(before) == key(after) == key(path.stat()) and before.st_ctime_ns == after.st_ctime_ns
         and len(raw) <= limit, 'LEDGER_FILE_CHANGED')
    return decode(raw)


def persist(path, value):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    sync_directory(path.parent)


def sync_directory(path):
    if os.name == 'posix':
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class Ledger:
    """A durable intent always precedes dispatch; a lost intent is never replayed."""
    def __init__(self, root, native):
        self.root, self.native = Path(root), native
        need(self.root.is_absolute() and self.root.resolve() == self.root and self.root.is_dir(),
             'LEDGER_ROOT_REQUIRED')
        self.lock = threading.RLock()
        self.active = set()

    def directory(self, operation):
        operation_id(operation)
        return self.root / operation

    def submit(self, value):
        value = request(value)
        with self.lock:
            directory = self.directory(value['operationId'])
            if directory.exists():
                saved = local_read(directory / 'request.json')
                need(saved == value, 'OPERATION_ID_REUSED')
                return self.status(value['operationId'])
            # Resolve actual source/archive configuration before reserving one dispatch.
            try:
                selection = self.native.resolve(value)
            except Exception as error:
                # Admission failed before any worker could be launched. Retain
                # this actual failure so the original GET has a definite result.
                self.reserve(value, None)
                code = public_error(error)
                persist(directory / 'admission-error.json', {'errorCode': code})
                return result(value, 'FAILED', code)
            self.reserve(value, selection)
            self.active.add(value['operationId'])
            thread = threading.Thread(target=self.execute, args=(value, directory, selection),
                                      name=value['operationId'], daemon=False)
            try:
                thread.start()
            except BaseException:
                self.active.remove(value['operationId'])
                raise
            return result(value, 'RUNNING')

    def reserve(self, value, selection):
        """Storage primitive; submit calls only after authentic native resolution."""
        value = request(value)
        with self.lock:
            directory = self.directory(value['operationId'])
            if directory.exists():
                need(local_read(directory / 'request.json') == value, 'OPERATION_ID_REUSED')
                return False
            directory.mkdir(mode=0o700)
            sync_directory(self.root)
            persist(directory / 'request.json', value)
            persist(directory / 'selection.json', selection)
            persist(directory / 'intent.json', dict(schemaVersion='SmallAppDispatchIntent/v1',
                operationId=value['operationId'], requestSha256=fingerprint(value), selection=selection))
            return True

    def execute(self, value, directory, selection):
        try:
            self.native.execute(value, directory, selection)
        except Exception as error:
            persist(directory / 'transport-error.json', {'errorCode': public_error(error),
                'dispatchStarted': getattr(error, 'dispatch_started', None)})
        finally:
            with self.lock:
                self.active.remove(value['operationId'])

    def status(self, operation):
        with self.lock:
            directory = self.directory(operation)
            need(directory.is_dir() and directory.resolve() == directory, 'OPERATION_NOT_FOUND')
            value = request(local_read(directory / 'request.json'))
            need(value['operationId'] == operation, 'LEDGER_OPERATION_MISMATCH')
            intent = directory / 'intent.json'
            if not intent.exists():
                return result(value, 'RUNNING', 'DURABLE_INTENT_INCOMPLETE')
            saved = local_read(intent)
            need(saved['requestSha256'] == fingerprint(value) and saved['operationId'] == operation,
                 'LEDGER_INTENT_MISMATCH')
            if (directory / 'admission-error.json').is_file():
                admission = local_read(directory / 'admission-error.json')
                exact(admission, 'errorCode', 'ADMISSION_ERROR_FIELDS_INVALID')
                need(type(admission['errorCode']) is str and
                     re.fullmatch('[A-Z][A-Z0-9_]{0,95}', admission['errorCode']), 'ADMISSION_ERROR_CODE_INVALID')
                return result(value, 'FAILED', admission['errorCode'])
            # Reconciliation reads only originals. It never schedules a worker.
            try:
                final = self.native.reconcile(value, directory, saved['selection'])
            except Exception as error:
                return result(value, 'RUNNING', public_error(error))
            if final is not None:
                exact(final, RESULT_FIELDS, 'UI_RESULT_FIELDS_INVALID')
                need(final['schemaVersion'] == 'SmallAppBackupUiResult/v1' and
                     final['operationId'] == operation and final['action'] == value['action'],
                     'UI_RESULT_BINDING_INVALID')
                return final
            if (directory / 'timeout-observation.json').is_file():
                return result(value, 'RUNNING', 'ORIGINAL_OPERATION_DEADLINE_EXCEEDED')
            if (directory / 'transport-error.json').is_file():
                saved_error = local_read(directory / 'transport-error.json')
                exact(saved_error, 'errorCode dispatchStarted', 'TRANSPORT_ERROR_FIELDS_INVALID')
                need(type(saved_error['errorCode']) is str and
                     re.fullmatch('[A-Z][A-Z0-9_]{0,95}', saved_error['errorCode']), 'TRANSPORT_ERROR_CODE_INVALID')
                return result(value, 'FAILED' if saved_error['dispatchStarted'] is False else 'RUNNING',
                              saved_error['errorCode'])
            if operation in self.active:
                return result(value, 'RUNNING')
            return result(value, 'RUNNING', 'ORIGINAL_TERMINAL_NOT_PROVEN')


def native_required():
    need(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0,
         'SMALLAPP_NATIVE_ROOT_REQUIRED')


def serve(config_pin):
    native_required()
    from recovery_control_smallapp_native import Native
    native = Native(config_pin)
    config = native.configuration()
    from recovery_control_smallapp_http import run_server
    run_server(config, Ledger(config['ledgerRoot'], native))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Failure('CLI_ARGUMENTS_INVALID')


def main():
    parser = Parser(description=__doc__)
    parser.add_argument('mode', choices=('new-operation-id', 'serve', 'worker', 'import-registration'))
    parser.add_argument('--operation-id')
    parser.add_argument('--config-pin')
    parser.add_argument('--registration-pin')
    parser.add_argument('--expected-registration-pin')
    try:
        args = parser.parse_args()
        if args.mode == 'new-operation-id':
            print('smallapp-' + uuid.uuid4().hex)
            return 0
        need(args.config_pin, 'SERVER_CONFIGURATION_REQUIRED')
        cp = decode(args.config_pin.encode())
        if args.mode == 'serve':
            serve(cp)
        else:
            from recovery_control_smallapp_native import Native
            native = Native(cp)
            if args.mode == 'worker':
                return native.worker(args.operation_id)
            need(args.registration_pin, 'REGISTRATION_PIN_REQUIRED')
            expected = None if args.expected_registration_pin is None else decode(args.expected_registration_pin.encode())
            print(canonical(native.import_registration(decode(args.registration_pin.encode()), expected)).decode())
        return 0
    except Exception as error:
        print(canonical({'errorCode': public_error(error)}).decode(), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.modules['recovery_control_smallapp'] = sys.modules[__name__]
    sys.exit(main())
