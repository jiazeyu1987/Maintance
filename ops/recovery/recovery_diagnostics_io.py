"""Strict file contracts and durable local diagnostic state; no executor calls."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import uuid

from jsonschema import Draft202012Validator, FormatChecker


class DiagnosticError(Exception):
    def __init__(self, code, unknown=False):
        super().__init__(code)
        self.code = code
        self.unknown = unknown


def require(condition, code):
    if not condition:
        raise DiagnosticError(code)


def exact(record, keys, code):
    require(type(record) is dict and set(record) == set(keys), code)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def timestamp_ns(value):
    require(type(value) is str and value.endswith('Z'), 'UTC_TIMESTAMP_REQUIRED')
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as error:
        raise DiagnosticError('UTC_TIMESTAMP_INVALID') from error
    return int(parsed.timestamp() * 1_000_000_000)


def canonical(record):
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(record):
    return hashlib.sha256(canonical(record)).hexdigest()


def absolute_path(value):
    require(type(value) is str and Path(value).is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    path = Path(value)
    for ancestor in (path, *path.parents):
        if ancestor.exists():
            info = ancestor.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not (
                getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT),
                'LINK_PATH_FORBIDDEN')
    return path


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    def invalid_constant(_value):
        raise DiagnosticError('NON_FINITE_JSON_FORBIDDEN')

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as error:
        raise DiagnosticError('JSON_INVALID') from error


class Budget:
    def __init__(self, milliseconds, started_ns=None):
        require(type(milliseconds) is int and milliseconds > 0, 'DEADLINE_INVALID')
        self.start = time.monotonic_ns() if started_ns is None else started_ns
        self.deadline = self.start + milliseconds * 1_000_000

    def check(self):
        if time.monotonic_ns() >= self.deadline:
            raise DiagnosticError('DIAGNOSTIC_DEADLINE_EXCEEDED', unknown=True)


def pin_file(path):
    path = absolute_path(str(path))
    hasher = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b''):
            size += len(chunk)
            hasher.update(chunk)
    return {'path': str(path), 'bytes': size, 'sha256': hasher.hexdigest()}


def provisioned_inputs(reader, policy_pin):
    """A request's own policy/approval cannot nominate the independent trust root."""
    path = os.environ.get('RECOVERY_DIAGNOSTICS_TRUST_FILE')
    sha = os.environ.get('RECOVERY_DIAGNOSTICS_TRUST_SHA256')
    require(path is not None and sha is not None, 'DIAGNOSTICS_TRUST_NOT_CONFIGURED')
    selected = pin_file(absolute_path(path))
    require(selected['sha256'] == sha, 'DIAGNOSTICS_TRUST_CHANGED')
    record = reader.read(selected)
    exact(record, ('schemaVersion', 'diagnosticsPolicyPin', 'executionSubjectBindingPin',
                   'approvedRehearsalTemplatePin', 'rehearsalTemplateApprovalPin'),
          'DIAGNOSTICS_TRUST_SHAPE_INVALID')
    require(record['schemaVersion'] == 'RecoveryDiagnosticsTrust/v1' and
            record['diagnosticsPolicyPin'] == policy_pin, 'DIAGNOSTICS_POLICY_NOT_IN_PROVISIONED_TRUST')
    return record


class Reader:
    def __init__(self, budget):
        self.budget = budget
        self.pins = []
        self.json_cache = {}
        self.forbidden_paths = set()

    def read(self, pin, json_record=True):
        exact(pin, ('path', 'bytes', 'sha256'), 'PIN_SHAPE_INVALID')
        require(type(pin['bytes']) is int and pin['bytes'] >= 0, 'PIN_SIZE_INVALID')
        require(type(pin['sha256']) is str and len(pin['sha256']) == 64 and
                all(c in '0123456789abcdef' for c in pin['sha256']), 'PIN_HASH_INVALID')
        path = absolute_path(pin['path'])
        require(path not in self.forbidden_paths, 'OUTPUT_INPUT_COLLISION')
        self.budget.check()
        if json_record and digest(pin) in self.json_cache:
            return self.json_cache[digest(pin)]
        require(not json_record or pin['bytes'] <= 16_777_216, 'JSON_SIZE_LIMIT_EXCEEDED')
        hasher, size, chunks = hashlib.sha256(), 0, []
        try:
            with path.open('rb') as handle:
                require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), 'PIN_REGULAR_FILE_REQUIRED')
                for chunk in iter(lambda: handle.read(1_048_576), b''):
                    self.budget.check()
                    size += len(chunk)
                    require(size <= pin['bytes'], 'PIN_SIZE_MISMATCH')
                    hasher.update(chunk)
                    if json_record:
                        chunks.append(chunk)
        except OSError as error:
            raise DiagnosticError('PIN_UNREADABLE') from error
        require(size == pin['bytes'] and hasher.hexdigest() == pin['sha256'], 'PIN_CONTENT_MISMATCH')
        if pin not in self.pins:
            self.pins.append(pin)
        if json_record:
            record = parse_json(b''.join(chunks))
            self.json_cache[digest(pin)] = record
            return record

    def verify_nested(self, value):
        if type(value) is dict:
            if set(value) == {'path', 'bytes', 'sha256'}:
                self.read(value, json_record=False)
            else:
                for child in value.values():
                    self.verify_nested(child)
        elif type(value) is list:
            for child in value:
                self.verify_nested(child)


class Contracts:
    def __init__(self, schema):
        require(type(schema) is dict and '$defs' in schema, 'SCHEMA_DEFINITIONS_REQUIRED')
        self.schema = schema

    def validate(self, name, record):
        require(name in self.schema['$defs'], 'SCHEMA_DEFINITION_MISSING')
        schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
                  '$defs': self.schema['$defs'], '$ref': '#/$defs/' + name}
        if next(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record), None):
            raise DiagnosticError('SCHEMA_' + name.upper() + '_INVALID')


def atomic_json(path, record, replace=True):
    path = absolute_path(str(path))
    require(path.parent.is_dir(), 'OUTPUT_PARENT_MISSING')
    raw = canonical(record) + b'\n'
    temporary = path.parent / ('.write-' + uuid.uuid4().hex)
    # A failed write remains visible as an error. No catch-and-default-success.
    with temporary.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if replace:
        os.replace(temporary, path)
    else:
        # Exclusive publication avoids replacing a concurrently created input
        # or another operation's result. A collision is a real write failure.
        os.link(temporary, path)
        temporary.unlink()
    if os.name != 'nt':
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


@contextmanager
def state_lock(root):
    path = root / '.diagnostics.lock'
    try:
        handle = path.open('xb')
    except FileExistsError as error:
        raise DiagnosticError('LOCAL_STATE_LOCK_UNRESOLVED', unknown=True) from error
    try:
        with handle:
            handle.write(canonical({'pid': os.getpid(), 'createdAt': utc_now()}))
            handle.flush()
            os.fsync(handle.fileno())
            yield
    finally:
        # Windows requires the held file handle to close before unlink. A
        # crashed invocation retains the lock and requires reconciliation.
        path.unlink()
