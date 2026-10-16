"""Strict local evidence primitives. Trust is selected by the invoking caller."""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import time


class VerificationError(ValueError):
    def __init__(self, code, verdict="BLOCKED"):
        super().__init__(code)
        self.code, self.verdict = code, verdict


def need(condition, code, verdict="BLOCKED"):
    if not condition:
        raise VerificationError(code, verdict)


def fields(record, names, schema=None):
    need(type(record) is dict and set(record) == set(names.split()), "RECORD_FIELDS")
    if schema is not None:
        need(record["schemaVersion"] == schema, "RECORD_VERSION")


def text(value):
    need(type(value) is str and bool(value.strip()) and "\x00" not in value, "TEXT_REQUIRED")
    return value


def integer(value, minimum=0):
    need(type(value) is int and value >= minimum, "INTEGER_REQUIRED")
    return value


def sha(value):
    need(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "SHA256_REQUIRED")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    def invalid(_):
        raise VerificationError("NONFINITE_JSON")
    try:
        need(not raw.startswith(b"\xef\xbb\xbf"), "JSON_BOM_FORBIDDEN")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=invalid)
        def finite(item):
            if type(item) is float:
                need(math.isfinite(item), "NONFINITE_JSON")
            elif type(item) is dict:
                for child in item.values():
                    finite(child)
            elif type(item) is list:
                for child in item:
                    finite(child)
        finite(value)
        return value
    except (UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError("INVALID_JSON") from error


def absolute(value):
    text(value)
    need(Path(value).is_absolute() and not (os.name == "nt" and value.startswith("/")),
         "HOST_ABSOLUTE_PATH_REQUIRED")
    return Path(value)


CHUNK_BYTES = 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024


def checked_file(value, deadline=None, content=True, expected=None, max_bytes=None):
    path = absolute(value)
    limit = MAX_JSON_BYTES if max_bytes is None else integer(max_bytes, 1)
    limit_code = "JSON_INPUT_LIMIT" if max_bytes is None else "RAW_INPUT_LIMIT"
    try:
        for ancestor in (path, *path.parents):
            info = ancestor.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not
                 (getattr(info, "st_file_attributes", 0) & 1024), "LINK_FORBIDDEN")
        before = path.stat()
        need(stat.S_ISREG(before.st_mode), "REGULAR_FILE_REQUIRED")
        if content:
            need(before.st_size <= limit, limit_code)
        checksum, total, chunks = hashlib.sha256(), 0, []
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            while True:
                if deadline is not None:
                    deadline.remaining()
                chunk = stream.read(min(CHUNK_BYTES, limit - total + 1) if content else CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                checksum.update(chunk)
                if content:
                    need(total <= limit, limit_code)
                    chunks.append(chunk)
            finished = os.fstat(stream.fileno())
        after = path.stat()
        def identity(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
        need(identity(before) == identity(opened) == identity(finished) == identity(after)
             and before.st_ctime_ns == after.st_ctime_ns
             and opened.st_ctime_ns == finished.st_ctime_ns, "FILE_CHANGED_DURING_READ", "STALE")
        need(total == before.st_size, "FILE_CHANGED_DURING_READ", "STALE")
        if deadline is not None:
            deadline.remaining()
        observed = {"path": str(path), "bytes": total, "sha256": checksum.hexdigest()}
        if expected is not None:
            need(total == expected["bytes"] and observed["sha256"] == expected["sha256"], "PIN_MISMATCH", "STALE")
        return b"".join(chunks) if content else observed
    except OSError as error:
        raise VerificationError("ORIGINAL_UNAVAILABLE") from error


def raw_file(value, deadline=None):
    return checked_file(value, deadline, content=True)


def file_pin(value, deadline=None):
    return checked_file(value, deadline, content=False)


def pin_key(pin):
    fields(pin, "path bytes sha256")
    path = absolute(pin["path"])
    integer(pin["bytes"])
    sha(pin["sha256"])
    return os.path.normcase(str(path)), pin["bytes"], pin["sha256"]


def read_pin(pin, deadline=None, content=True, max_bytes=None):
    pin_key(pin)
    return checked_file(pin["path"], deadline, content=content, expected=pin, max_bytes=max_bytes)


def json_pin(pin, deadline=None):
    return parse(read_pin(pin, deadline))


def frozen_schema(pin):
    # The storage path is explicit; the bytes/version are frozen by the execution contract.
    need(pin["bytes"] == 22254 and pin["sha256"] ==
         "ed38d1ea14aa1f0019aed08bffad3e40db91c47c28b07c5c8eb5df668c2cd3cb", "FROZEN_RECORD_SCHEMA_REQUIRED")
    return json_pin(pin)


def same(left, right, code):
    need(pin_key(left) == pin_key(right), code, "STALE")


def pins(values, nonempty=True):
    need(type(values) is list and (bool(values) or not nonempty), "PIN_LIST_REQUIRED")
    keys = [pin_key(value) for value in values]
    need(len(keys) == len(set(keys)), "DUPLICATE_PIN")
    return keys


def timestamp(value):
    text(value)
    need(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", value), "UTC_REQUIRED")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise VerificationError("INVALID_TIMESTAMP") from error


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Deadline:
    def __init__(self, milliseconds):
        self.end = time.monotonic() + integer(milliseconds, 1) / 1000

    def remaining(self):
        remaining = self.end - time.monotonic()
        need(remaining > 0, "DEADLINE_EXCEEDED", "UNKNOWN")
        return remaining


def write_atomic(path, record):
    path = absolute(str(path))
    need(path.parent.is_dir(), "OUTPUT_DIRECTORY_REQUIRED")
    raw = canonical(record) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    # Preserve an incomplete temporary if writing fails; never erase evidence on failure.
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    # Linking a fully flushed same-directory file publishes atomically without replacing
    # an existing evidence original, including a competing operation's new output.
    os.link(temporary, path)
    os.unlink(temporary)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def validate(definitions, name, record):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = {"$defs": definitions["$defs"], "$ref": "#/$defs/" + name}
    need(not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record)),
         "SCHEMA_" + name)
    # JSON Schema's integer accepts integral floats; the transport explicitly forbids them.
    def strict(item):
        if type(item) is dict:
            if set(item) == {"path", "bytes", "sha256"}:
                pin_key(item)
            for key, child in item.items():
                if key in ("deadlineMilliseconds", "actualExitCode", "observedMilliseconds",
                           "objectiveMilliseconds") and child is not None:
                    need(type(child) is int, "INTEGER_REQUIRED")
                strict(child)
        elif type(item) is list:
            for child in item:
                strict(child)
    strict(record)
