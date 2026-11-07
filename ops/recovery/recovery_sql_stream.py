"""Bounded marker inspection of already expanded binlog SQL.

This is a format gate, not SQL authorization or digest verification. Capture
scope, archive pins and the importer's complete digest checks remain mandatory.
"""
import os
from pathlib import Path
import re
import time

from recovery_engine import require, signature


CHUNK_BYTES = 1024 * 1024
PREFIX = b'-- IntRuoyi binlog incremental;'
GTID_PREFIX = b'SET @@SESSION.GTID_NEXT'
SPACE = re.compile(rb'\s*')
IDENTIFIER = re.compile(rb'[0-9a-fA-F-]+')
NUMBER = re.compile(rb'[0-9]+')


class _GtidMarker:
    """The original GTID regex, with finite state for unbounded token lengths."""
    def __init__(self):
        self.state = 'search'
        self.tail = b''

    def feed(self, chunk):
        data = self.tail + chunk
        self.tail = b''
        offset = 0
        while offset < len(data):
            if self.state == 'search':
                found = data.find(GTID_PREFIX, offset)
                if found < 0:
                    self.tail = data[-(len(GTID_PREFIX) - 1):]
                    return False
                offset = found + len(GTID_PREFIX)
                self.state = 'equals'
            elif self.state in ('equals', 'quote'):
                offset = SPACE.match(data, offset).end()
                if offset == len(data):
                    return False
                expected = ord('=') if self.state == 'equals' else ord("'")
                if data[offset] == expected:
                    offset += 1
                    self.state = 'quote' if self.state == 'equals' else 'first-id'
                else:
                    self.state = 'search'
            elif self.state in ('first-id', 'first-number'):
                pattern = IDENTIFIER if self.state == 'first-id' else NUMBER
                matched = pattern.match(data, offset)
                if matched is None:
                    self.state = 'search'
                else:
                    offset = matched.end()
                    self.state = 'id' if self.state == 'first-id' else 'number'
            else:
                pattern = IDENTIFIER if self.state == 'id' else NUMBER
                matched = pattern.match(data, offset)
                if matched is not None:
                    offset = matched.end()
                if offset == len(data):
                    return False
                if self.state == 'id' and data[offset] == ord(':'):
                    offset += 1
                    self.state = 'first-number'
                elif self.state == 'number' and data[offset] == ord("'"):
                    return True
                else:
                    self.state = 'search'
        return False


def inspect_incremental_sql(path, *, mode, has_segments, guard, seconds):
    """Preserve the prefix/BINLOG/GTID gates without loading the SQL payload."""
    require(callable(guard), 'INCREMENTAL_SQL_SCAN_GUARD_REQUIRED')
    require(type(seconds) is int and 0 < seconds <= 7200, 'INCREMENTAL_SQL_SCAN_TIMEOUT_INVALID')
    deadline = time.monotonic() + seconds

    def current():
        require(time.monotonic() < deadline, 'INCREMENTAL_SQL_SCAN_TIMEOUT')
        guard()
        require(time.monotonic() < deadline, 'INCREMENTAL_SQL_SCAN_TIMEOUT')

    current()
    path = Path(path)
    before = signature(path.lstat())
    with path.open('rb') as stream:
        require(signature(os.fstat(stream.fileno())) == before, 'INCREMENTAL_SQL_SOURCE_CHANGED')
        prefix = stream.read(len(PREFIX))
        current()
        require(prefix == PREFIX, 'CAPTURED_BINLOG_SQL_REQUIRED')
        require(mode in ('GTID', 'FILE_POSITION'), 'CAPTURED_BINLOG_LOG_MODE_INVALID')
        if mode == 'GTID' and has_segments:
            marker = _GtidMarker()
            tail = b''
            found = False
            while True:
                chunk = stream.read(CHUNK_BYTES)
                current()
                if not chunk:
                    break
                if b'BINLOG ' in tail + chunk or marker.feed(chunk):
                    found = True
                    break
                tail = (tail + chunk)[-(len(b'BINLOG ') - 1):]
            require(found, 'CAPTURED_BINLOG_SQL_REQUIRED')
        current()
        require(signature(os.fstat(stream.fileno())) == before and signature(path.lstat()) == before,
                'INCREMENTAL_SQL_SOURCE_CHANGED')
