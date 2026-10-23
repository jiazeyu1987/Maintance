"""Strict W05 records, stable pinned reads and externally provisioned trust.

The request cannot nominate its own trust root. Operators provision the trust
file path and its approved SHA256 in the process environment, independently of
the operation request. No source-host lookup, credentials or defaults are used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from datetime import datetime, timezone


class EnvironmentFailure(RuntimeError):
    def __init__(self, code: str, *, unknown: bool = False, result=None):
        super().__init__(code)
        self.code = code
        self.unknown = unknown
        self.result = result


def require(condition, code):
    if not condition:
        raise EnvironmentFailure(code)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc(value):
    require(isinstance(value, str) and value.endswith("Z"), "UTC_TIMESTAMP_REQUIRED")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise EnvironmentFailure("UTC_TIMESTAMP_INVALID") from None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
                      allow_nan=False).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(entries):
    value = {}
    for key, item in entries:
        require(key not in value, "DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def decode(raw):
    def invalid(_):
        raise EnvironmentFailure("NONFINITE_JSON_NUMBER")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=invalid)
    except (UnicodeError, ValueError, RecursionError):
        raise EnvironmentFailure("JSON_INVALID") from None


def exact(value, fields, code):
    require(type(value) is dict and set(value) == set(fields), code)


def text(value, code="STRING_INVALID"):
    require(type(value) is str and bool(value) and "\x00" not in value, code)
    return value


def safe_path(value, *, exists=True, directory=False):
    path = Path(text(value, "PATH_INVALID"))
    require(path.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    # Check every ancestor, including Windows junctions; reject traversal.
    require(".." not in path.parts, "PATH_TRAVERSAL")
    for part in [*reversed(path.parents), path]:
        if not part.exists():
            require(not part.is_symlink(), "PATH_LINK_REJECTED")
            continue
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, "st_file_attributes", 0) & 0x400), "PATH_LINK_REJECTED")
    if exists:
        require(path.is_dir() if directory else path.is_file(), "REQUIRED_PATH_MISSING")
    return path


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _location(info):
    # Windows path stat and descriptor fstat expose different ctime meanings.
    # Compare ctime within each observation API; device/inode/mtime must also
    # agree across APIs. No timestamps are rounded or ignored for stability.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_bytes(value, *, limit=16 * 1024 * 1024):
    path = safe_path(value)
    path_before = path.stat()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_size <= limit, "PIN_FILE_INVALID")
        raw = stream.read(limit + 1)
        after, path_after = os.fstat(stream.fileno()), path.stat()
        require(len(raw) <= limit and _identity(before) == _identity(after) and
                _identity(path_before) == _identity(path_after) and _location(after) == _location(path_after),
                "PIN_FILE_CHANGED")
    safe_path(str(path))
    return raw


def validate_pin(pin):
    exact(pin, ("path", "bytes", "sha256"), "PIN_INVALID")
    safe_path(pin["path"])
    require(type(pin["bytes"]) is int and pin["bytes"] >= 0 and type(pin["sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]), "PIN_INVALID")


def read_pin(pin):
    validate_pin(pin)
    raw = read_bytes(pin["path"])
    require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
            "PIN_MISMATCH")
    return decode(raw)


def pin_file(value):
    path = safe_path(str(value))
    raw = read_bytes(str(path))
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def verify_large_pin(pin, guard):
    """Hash an archive without loading gigabytes into memory; no linked files."""
    validate_pin(pin)
    path = safe_path(pin["path"])
    sha = hashlib.sha256()
    size = 0
    path_before = path.stat()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        require(before.st_nlink == 1, "ARCHIVE_LINK_REJECTED")
        while chunk := stream.read(1024 * 1024):
            guard()
            size += len(chunk)
            sha.update(chunk)
        after, path_after = os.fstat(stream.fileno()), path.stat()
        require(_identity(before) == _identity(after) and _identity(path_before) == _identity(path_after)
                and _location(after) == _location(path_after),
                "ARCHIVE_CHANGED")
    require(size == pin["bytes"] and sha.hexdigest() == pin["sha256"], "ARCHIVE_PIN_MISMATCH")


def atomic_json(path, value):
    path = safe_path(str(path), exists=False)
    safe_path(str(path.parent), directory=True)
    handle, temporary = tempfile.mkstemp(prefix=".w05-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    except BaseException:
        # Keep a partial artifact for reconciliation. Never report success here.
        raise


class Schemas:
    """Validator for the frozen schema vocabulary, with no optional dependency."""
    def __init__(self, schema):
        require(type(schema) is dict and type(schema.get("$defs")) is dict, "SCHEMA_INVALID")
        self.schema = schema

    def validate(self, value, name):
        require(name in self.schema["$defs"], "SCHEMA_RECORD_MISSING")
        self._validate(value, self.schema["$defs"][name])

    def _validate(self, value, rule):
        if "anyOf" in rule:
            accepted = False
            for branch in rule["anyOf"]:
                try:
                    self._validate(value, branch)
                    accepted = True
                    break
                except EnvironmentFailure:
                    continue
            require(accepted, "SCHEMA_ANY_OF")
        if "$ref" in rule:
            ref = rule["$ref"]
            require(ref.startswith("#/$defs/"), "SCHEMA_REF_UNSUPPORTED")
            return self._validate(value, self.schema["$defs"][ref[8:]])
        if "const" in rule:
            require(type(value) is type(rule["const"]) and value == rule["const"], "SCHEMA_CONST")
        if "enum" in rule:
            require(value in rule["enum"], "SCHEMA_ENUM")
        if "type" in rule:
            types = rule["type"] if type(rule["type"]) is list else [rule["type"]]
            matches = {"object": type(value) is dict, "array": type(value) is list,
                       "string": type(value) is str, "integer": type(value) is int,
                       "boolean": type(value) is bool, "null": value is None}
            require(any(matches.get(kind, False) for kind in types), "SCHEMA_TYPE")
        if type(value) is dict:
            require(all(key in value for key in rule.get("required", [])), "SCHEMA_REQUIRED")
            props = rule.get("properties", {})
            additional = rule.get("additionalProperties", True)
            for key, item in value.items():
                if key in props:
                    self._validate(item, props[key])
                elif additional is False:
                    raise EnvironmentFailure("SCHEMA_UNKNOWN_FIELD")
                elif type(additional) is dict:
                    self._validate(item, additional)
        if type(value) is list:
            require(len(value) >= rule.get("minItems", 0), "SCHEMA_MIN_ITEMS")
            for item in value:
                if "items" in rule:
                    self._validate(item, rule["items"])
        if type(value) is str:
            require(len(value) >= rule.get("minLength", 0), "SCHEMA_MIN_LENGTH")
            if "pattern" in rule:
                require(re.search(rule["pattern"], value), "SCHEMA_PATTERN")
            if rule.get("format") == "date-time":
                utc(value)
        if type(value) is int and "minimum" in rule:
            require(value >= rule["minimum"], "SCHEMA_MINIMUM")


class Trust:
    def __init__(self, path=None, sha256=None):
        path = path if path is not None else os.environ.get("RECOVERY_ENVIRONMENT_TRUST_FILE")
        sha256 = sha256 if sha256 is not None else os.environ.get("RECOVERY_ENVIRONMENT_TRUST_SHA256")
        require(path and sha256 and re.fullmatch("[0-9a-f]{64}", sha256), "TRUST_ROOT_NOT_CONFIGURED")
        raw = read_bytes(path)
        require(hashlib.sha256(raw).hexdigest() == sha256, "TRUST_ROOT_MISMATCH")
        self.value = decode(raw)
        exact(self.value, ("schemaVersion", "executorId", "policySha256", "targetConfigSha256",
                           "recordSchemasPin", "authorizationSha256s", "leaseSha256s"), "TRUST_INVALID")
        require(self.value["schemaVersion"] == "RecoveryEnvironmentTrust/v1", "TRUST_VERSION")
        text(self.value["executorId"])
        self.schemas = Schemas(read_pin(self.value["recordSchemasPin"]))

    def trusted(self, pin, field):
        expected = self.value[field]
        require(pin["sha256"] in expected if type(expected) is list else pin["sha256"] == expected,
                "INPUT_NOT_TRUSTED")
        return read_pin(pin)


def valid_window(record):
    now = datetime.now(timezone.utc)
    require(utc(record["notBefore"]) <= now < utc(record["expiresAt"]), "AUTHORIZATION_OR_LEASE_EXPIRED")


def authorize(request, trust, target_id):
    require(request["authorizationRefs"], "WRITE_AUTHORIZATION_REQUIRED")
    permitted = False
    for pin in request["authorizationRefs"]:
        record = trust.trusted(pin, "authorizationSha256s")
        exact(record, ("schemaVersion", "operationId", "targetId", "executorId", "mode", "actions",
                       "notBefore", "expiresAt", "approved"), "AUTHORIZATION_INVALID")
        require(record["schemaVersion"] == "RecoveryEnvironmentAuthorization/v1" and
                record["approved"] is True, "AUTHORIZATION_NOT_APPROVED")
        valid_window(record)
        require(record["operationId"] == request["operationId"] and record["targetId"] == target_id
                and record["executorId"] == trust.value["executorId"] and record["mode"] == request["mode"],
                "AUTHORIZATION_SCOPE_MISMATCH")
        require(type(record["actions"]) is list, "AUTHORIZATION_ACTIONS_INVALID")
        permitted |= request["action"] in record["actions"]
    require(permitted, "ACTION_NOT_AUTHORIZED")
    require(request["leaseRef"] is not None, "LEASE_REQUIRED")
    lease = trust.trusted(request["leaseRef"], "leaseSha256s")
    exact(lease, ("schemaVersion", "operationId", "targetId", "executorId", "leaseId", "fenceToken",
                  "notBefore", "expiresAt", "state"), "LEASE_INVALID")
    valid_window(lease)
    require(lease["schemaVersion"] == "RecoveryEnvironmentLease/v1" and lease["state"] == "HELD"
            and lease["operationId"] == request["operationId"] and lease["targetId"] == target_id
            and lease["executorId"] == trust.value["executorId"] and type(lease["fenceToken"]) is int
            and lease["fenceToken"] > 0, "LEASE_SCOPE_MISMATCH")
    text(lease["leaseId"])
    return lease


def original_w04_exits(pins, guard):
    """Consume W04's original intent/exit records and pinned raw pipe files.

    W04's list intentionally contains non-JSON stdout/stderr. A success-shaped
    result is insufficient: every real invocation intent needs its observed
    terminal record with exit zero and no timeout.
    """
    require(type(pins) is list and pins, "ORIGINAL_INVOCATIONS_REQUIRED")
    intents = {}
    terminals = []
    for pin in pins:
        verify_large_pin(pin, guard)
        if Path(pin["path"]).name in ("intent.json", "exit.json"):
            record = read_pin(pin)
            if record.get("schemaVersion") == "recovery-invocation/v1":
                require(pin["sha256"] not in intents, "DUPLICATE_INVOCATION_INTENT")
                intents[pin["sha256"]] = pin
                for field in ("scriptPin", "pythonPin", "requestPin"):
                    verify_large_pin(record[field], guard)
                require(record["requestPin"] in pins, "INVOCATION_REQUEST_ORIGINAL_MISSING")
            elif record.get("schemaVersion") == "recovery-original-exit/v1":
                require(type(record.get("actualExitCode")) is int and record["actualExitCode"] == 0 and
                        record.get("timedOut") is False, "ORIGINAL_EXECUTOR_NOT_SUCCEEDED")
                terminals.append(record)
            else:
                raise EnvironmentFailure("ORIGINAL_INVOCATION_RECORD_UNSUPPORTED")
    require(intents and len(terminals) == len(intents) and len({record["intentPin"]["sha256"] for record in terminals}) == len(terminals),
            "ORIGINAL_EXECUTOR_TERMINATION_MISSING")
    require(all(intents.get(record["intentPin"]["sha256"]) == record["intentPin"] for record in terminals),
            "ORIGINAL_EXECUTOR_INTENT_MISMATCH")
    return terminals
