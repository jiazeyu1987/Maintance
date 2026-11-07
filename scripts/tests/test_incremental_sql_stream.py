"""Real-file SQL inspection tests; database execution is outside this boundary."""
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time
import tracemalloc

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
import formal_sql_restore
from recovery_data import NativeData
from recovery_engine import RecoveryError
import recovery_sql_stream as scan

PREFIX = b'-- IntRuoyi binlog incremental;'


def file_pin(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def entrypoint(tmp_path, *, mode='FILE_POSITION', segments=False, body=None):
    """Real stage/expand/inspect, intentionally rejected before database access."""
    raw = tmp_path/'source.sql'
    with raw.open('wb') as output:
        output.write(PREFIX + b'\n')
        if body is None:
            for _ in range(24):
                output.write(b'a' * (1024 * 1024))
        else:
            output.write(body)
    archive = tmp_path/'source.sql.gz'
    with raw.open('rb') as source, gzip.open(archive, 'wb') as output:
        while chunk := source.read(65536):
            output.write(chunk)
    start = dict(file='mysql-bin.000001', position=4, databaseUuid='database', serverVersion='8.0')
    end = {**start, 'position': 8} if segments else dict(start)
    raw_pin, archive_pin = file_pin(raw), file_pin(archive)
    capture = dict(schemaVersion='backup-capture-point/v1', pointType='INCREMENTAL',
        commonRecoveryPoint='local-file-test', databaseEnd=end,
        databaseDelta=dict(kind='BINLOG_SQL', parentPosition=start, rawPin=raw_pin,
            segments=[dict(file=start['file'], startPosition=4, stopPosition=8)] if segments else [],
            logMode=mode, dataObservation='STOP_BEFORE_DATABASE'))
    capture_path = tmp_path/'capture.json'
    capture_path.write_text(json.dumps(capture), encoding='utf-8')
    native = NativeData.__new__(NativeData)
    native.root = tmp_path/'work'; native.root.mkdir()
    native.material = dict(recoveryPoint='local-file-test', payloadPins=[raw_pin, archive_pin],
        database=dict(capturePointPin=file_pin(capture_path), startPosition=start, endPosition=end,
            sqlPin=archive_pin, rawSqlPin=raw_pin))
    native.policy = dict(maxExpandedBytes=32 * 1024 * 1024)
    native.modules = dict(formal_sql_restore=formal_sql_restore)
    # These unit tests exercise files, not a provisioned database/target guard.
    native.bound = lambda: None
    native.guard = lambda: None
    native.seconds = lambda: 60
    return native


def test_incremental_entrypoint_has_bounded_memory(tmp_path, monkeypatch):
    # Windows has no O_NOFOLLOW; the real private-file staging logic still runs.
    monkeypatch.setattr(os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), raising=False)
    native = entrypoint(tmp_path)
    expand_checked = formal_sql_restore.expand_checked
    def measured_expand(*args):
        result = expand_checked(*args)
        # Measure the inspection stage, excluding the existing JSON reader's
        # fixed 64 MiB allocation and the real gzip expansion preceding it.
        tracemalloc.reset_peak()
        return result
    monkeypatch.setattr(formal_sql_restore, 'expand_checked', measured_expand)
    tracemalloc.start()
    try:
        with pytest.raises(RecoveryError, match='^CAPTURED_DATA_OBSERVATION_INVALID$'):
            native.incremental_captured_sql()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 8 * 1024 * 1024, f'SQL inspection allocated {peak} bytes'


@pytest.mark.parametrize('chunk_size', [1, 2, 5, 17, 31, 1024])
@pytest.mark.parametrize('body,valid', [
    (b'BINLOG ', True),
    (b'BINLOG', False),
    (b"SET @@SESSION.GTID_NEXT='a-0:1'", True),
    (b"SET @@SESSION.GTID_NEXT \n\r\t\v\f = \t\n 'ABC-012:123'", True),
    (b"SET @@SESSION.GTID_NEXT=':1'", False),
    (b"SET @@SESSION.GTID_NEXT='aa:'", False),
    (b"SET @@SESSION.GTID_NEXT='aa:1", False),
    (b"SET @@SESSION.GTID_NEXT='g:1'", False),
    (b"SET @@SESSION.GTID_NEXT='aa:+1'", False),
    (b"set @@SESSION.GTID_NEXT='aa:1'", False),
    (b"SET @@SESSION.GTID_NEXT='AUTOMATIC'", False),
    (b"SET @@SESSION.GTID_NEXTx SET @@SESSION.GTID_NEXT='a:1'", True),
    (b"SET @@SESSION.GTID_NEXT='bad:SET @@SESSION.GTID_NEXT='a:1'", True),
    (b"CREATE TABLE app.x (id int);", False),
])
def test_marker_boundaries_match_original_rule(tmp_path, monkeypatch, chunk_size, body, valid):
    monkeypatch.setattr(scan, 'CHUNK_BYTES', chunk_size)
    path = tmp_path/'incremental.sql'
    path.write_bytes(PREFIX + b'\n' + body)
    if valid:
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=60)
    else:
        with pytest.raises(RecoveryError, match='^CAPTURED_BINLOG_SQL_REQUIRED$'):
            scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=60)


def test_unbounded_gtid_fields_and_candidate_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, 'CHUNK_BYTES', 127)
    body = (b"SET @@SESSION.GTID_NEXT='broken;'\n" + scan.GTID_PREFIX + b' \t\n' * 3000 + b'=' +
            b'\v\f\r' * 3000 + b"'" + b'a0-' * 3000 + b':' + b'123' * 3000 + b"'")
    path = tmp_path/'incremental.sql'; path.write_bytes(PREFIX + body)
    scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=60)
    path.write_bytes(PREFIX + body[:-1])
    with pytest.raises(RecoveryError, match='^CAPTURED_BINLOG_SQL_REQUIRED$'):
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=60)


def test_gtid_state_machine_matches_original_regex():
    rng = random.Random(731)
    original = re.compile(rb"SET @@SESSION\.GTID_NEXT\s*=\s*'[0-9a-fA-F-]+:[0-9]+'")
    atoms = [scan.GTID_PREFIX, b' ', b'\t\n', b'=', b"'", b'a-012', b'123', b':', b'?', b'SET']
    for _ in range(2000):
        raw = b''.join(rng.choice(atoms) for _ in range(rng.randrange(1, 40)))
        marker = scan._GtidMarker()
        chunks = rng.randrange(1, 24)
        actual = any(marker.feed(raw[i:i + chunks]) for i in range(0, len(raw), chunks))
        assert actual == bool(original.search(raw)), raw


@pytest.mark.parametrize('mode,segments,body,expected', [
    ('FILE_POSITION', True, b'CREATE TABLE app.x(id int);', 'CAPTURED_DATA_OBSERVATION_INVALID'),
    ('GTID', False, b'', 'CAPTURED_DATA_OBSERVATION_INVALID'),
    ('GTID', True, b"SET @@SESSION.GTID_NEXT='a:1'; CREATE TABLE app.x(id int);", 'CAPTURED_DATA_OBSERVATION_INVALID'),
    ('GTID', True, b'CREATE TABLE app.x(id int);', 'CAPTURED_BINLOG_SQL_REQUIRED'),
    ('UNRECOGNIZED', True, b'BINLOG ', 'CAPTURED_BINLOG_LOG_MODE_INVALID'),
])
@pytest.mark.parametrize('variant', ['lightweight', 'standard'])
def test_real_variant_method_preserves_preimport_gates(tmp_path, monkeypatch, mode, segments, body, expected, variant):
    monkeypatch.setattr(os, 'O_NOFOLLOW', getattr(os, 'O_NOFOLLOW', 0), raising=False)
    native = entrypoint(tmp_path, mode=mode, segments=segments, body=body)
    method = NativeData.incremental_captured_sql
    if variant == 'standard':
        sys.path.insert(0, str(ROOT/'ops/backup_engine'))
        import build_variants
        payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
        source = payload['common/recovery_data.py'].decode('utf-8')
        assert "require(checksum == database['rawSqlPin']['sha256'], 'INCREMENTAL_SQL_EXPANSION_MISMATCH')" in source
        assert payload['common/recovery_sql_stream.py'] == (ROOT/'ops/recovery/recovery_sql_stream.py').read_bytes()
        tree = ast.parse(source)
        owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'NativeData')
        definition = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == method.__name__)
        namespace = dict(method.__globals__)
        exec(compile(ast.Module(body=[definition], type_ignores=[]), '<standard-incremental-preimport>', 'exec'), namespace)
        method = namespace[method.__name__]
    with pytest.raises(RecoveryError, match='^' + expected + '$'):
        method(native)


@pytest.mark.parametrize('contents,mode,error', [
    (b'', 'GTID', 'CAPTURED_BINLOG_SQL_REQUIRED'),
    (b'wrong prefix BINLOG ', 'GTID', 'CAPTURED_BINLOG_SQL_REQUIRED'),
    (b'wrong prefix BINLOG ', 'INVALID', 'CAPTURED_BINLOG_SQL_REQUIRED'),
    (PREFIX, 'INVALID', 'CAPTURED_BINLOG_LOG_MODE_INVALID'),
])
def test_prefix_and_mode_failure_order(tmp_path, contents, mode, error):
    path = tmp_path/'input.sql'; path.write_bytes(contents)
    with pytest.raises(RecoveryError, match='^' + error + '$'):
        scan.inspect_incremental_sql(path, mode=mode, has_segments=True, guard=lambda: None, seconds=60)


def test_guard_failure_is_preserved(tmp_path):
    path = tmp_path/'input.sql'; path.write_bytes(PREFIX + b'BINLOG ')
    expected = RecoveryError('SOURCE_GUARD_REJECTED', unknown=True)
    def guard():
        raise expected
    with pytest.raises(RecoveryError) as raised:
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=guard, seconds=60)
    assert raised.value is expected


def test_deadline_includes_guard_execution(tmp_path):
    path = tmp_path/'input.sql'; path.write_bytes(PREFIX + b'BINLOG ')
    def guard():
        time.sleep(1.05)
    with pytest.raises(RecoveryError, match='^INCREMENTAL_SQL_SCAN_TIMEOUT$'):
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=guard, seconds=1)


def test_deadline_includes_final_marker_parse(tmp_path, monkeypatch):
    path = tmp_path/'input.sql'; path.write_bytes(PREFIX + scan.GTID_PREFIX + b"='a:1'")
    feed = scan._GtidMarker.feed
    def delayed_feed(self, chunk):
        time.sleep(1.05)
        return feed(self, chunk)
    monkeypatch.setattr(scan._GtidMarker, 'feed', delayed_feed)
    with pytest.raises(RecoveryError, match='^INCREMENTAL_SQL_SCAN_TIMEOUT$'):
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=1)


def test_input_changes_and_read_failures_are_rejected(tmp_path):
    path = tmp_path/'input.sql'; path.write_bytes(PREFIX + b'BINLOG ')
    calls = 0
    def guard():
        nonlocal calls
        calls += 1
        if calls == 3:
            with path.open('ab') as output:
                output.write(b'changed')
    with pytest.raises(RecoveryError, match='^INCREMENTAL_SQL_SOURCE_CHANGED$'):
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=guard, seconds=60)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        scan.inspect_incremental_sql(path, mode='GTID', has_segments=True, guard=lambda: None, seconds=60)


def test_independent_process_scans_large_file_without_read_bytes(tmp_path):
    path = tmp_path/'large.sql'
    with path.open('wb') as stream:
        stream.write(PREFIX + b'\n')
        for _ in range(24):
            stream.write(b'x' * (1024 * 1024))
        stream.write(scan.GTID_PREFIX + b' ' * (2 * 1024 * 1024) + b"='a:1'")
    script = '''
import json, sys, tracemalloc
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from recovery_sql_stream import inspect_incremental_sql
def forbidden(*args, **kwargs):
    raise AssertionError('whole-file read_bytes is forbidden')
Path.read_bytes = forbidden
tracemalloc.start()
inspect_incremental_sql(Path(sys.argv[2]), mode='GTID', has_segments=True, guard=lambda: None, seconds=60)
print(json.dumps({'peakBytes': tracemalloc.get_traced_memory()[1]}))
'''
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', script,
        str(ROOT/'ops/recovery'), str(path)], capture_output=True, text=True, check=True, timeout=90)
    assert json.loads(result.stdout)['peakBytes'] < 8 * 1024 * 1024


@pytest.mark.skipif(sys.platform != 'linux', reason='real address-space limits require Linux')
def test_payload_larger_than_process_address_space_is_scanned_to_its_end(tmp_path):
    path = tmp_path / 'sparse-512m.sql'
    with path.open('wb') as stream:
        stream.write(PREFIX + b'\n')
        stream.seek(512 * 1024 * 1024)
        stream.write(b"SET @@SESSION.GTID_NEXT='a:1'")
    script = '''
import json, resource, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from recovery_sql_stream import inspect_incremental_sql
limit=256*1024*1024
resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
path=Path(sys.argv[2])
assert path.stat().st_size > limit*2
try:
 path.read_bytes()
except MemoryError:
 pass
else:
 raise AssertionError('whole-file allocation unexpectedly fits the enforced limit')
calls=[0]
def guard():calls[0]+=1
inspect_incremental_sql(path,mode='GTID',has_segments=True,guard=guard,seconds=60)
assert calls[0]>512
print(json.dumps({'scannedBytes':path.stat().st_size,'addressSpaceLimit':limit,'guardCalls':calls[0]}))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script,
        str(ROOT/'ops/recovery'), str(path)], capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed['scannedBytes'] > 2 * observed['addressSpaceLimit']
