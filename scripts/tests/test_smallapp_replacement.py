"""Local admission/retained-claim checks, not UI or live recovery evidence."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_replace import available, validate, preserve_binary_logging


def target(tmp_path):
    state=tmp_path/'replacements';state.mkdir()
    return dict(database='rehearsal_smallapp', services=[dict(role='mysql'),dict(role='minio')],
                redisRebuild=dict(database=0), replacement=dict(
                    schemaVersion='RegisteredApplicationReplacement/v1', stateRoot=str(state),
                    lockPath=str(tmp_path/'source.lock'),
                    databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',
                    services=dict(mysql={},minio={})))


def test_successful_claim_permits_repeat_but_failed_or_incomplete_claim_does_not(tmp_path):
    value=target(tmp_path);root=Path(value['replacement']['stateRoot'])
    assert available(value)
    claim=root/'operation1';claim.mkdir()
    assert not available(value)
    result=claim/'replacement-result.json'
    result.write_text(json.dumps(dict(state='FAILED_RETAINED')))
    assert not available(value)
    result.write_text(json.dumps(dict(state='SUCCEEDED')))
    assert available(value)
    (root/'operation2').mkdir()
    assert not available(value)


@pytest.mark.parametrize('database',['mysql','sys','a`; DROP DATABASE mysql; --'])
def test_system_or_injected_database_is_rejected(tmp_path,database):
    value=target(tmp_path);value['database']=database
    with pytest.raises(Exception,match='REPLACEMENT_DATABASE_INVALID'):
        validate(value)


@pytest.mark.parametrize('database',[-1,16,True,'0'])
def test_bad_redis_scope_is_rejected_before_any_mutation(tmp_path,database):
    value=target(tmp_path);value['redisRebuild']['database']=database
    with pytest.raises(Exception,match='REPLACEMENT_REDIS_DATABASE_INVALID'):
        validate(value)


def test_replacement_lock_cannot_live_inside_per_operation_state(tmp_path):
    value=target(tmp_path);value['replacement']['lockPath']=str(Path(value['replacement']['stateRoot'])/'lock')
    with pytest.raises(Exception,match='REPLACEMENT_STATE_INVALID'):
        validate(value)


def test_replayed_rows_remain_visible_to_later_source_increments(tmp_path):
    import hashlib
    from types import SimpleNamespace
    sql = tmp_path/'incremental.sql'
    raw = (b'/*!32316 SET @OLD_SQL_LOG_BIN=@@SQL_LOG_BIN, SQL_LOG_BIN=0*/;\n'
           b"BINLOG 'actual-encoded-events'/*!*/;\n"
           b'/*!32316 SET SQL_LOG_BIN=@OLD_SQL_LOG_BIN*/;\n')
    sql.write_bytes(raw)
    native = SimpleNamespace(root=tmp_path, guard=lambda: None)
    digest = preserve_binary_logging(native, sql, hashlib.sha256(raw).hexdigest())
    restored = sql.read_bytes()
    assert b'SQL_LOG_BIN=0' not in restored
    assert b"BINLOG 'actual-encoded-events'/*!*/;" in restored
    assert restored.startswith(b'SET SESSION sql_log_bin=1;\n')
    assert hashlib.sha256(restored).hexdigest() == digest
    assert json.loads((tmp_path/'incremental.sql-binary-logging.json').read_text())['reenabledSegments'] == 1


def test_changed_expanded_sql_is_rejected_without_replacing_original(tmp_path):
    from types import SimpleNamespace
    sql = tmp_path/'full.sql';sql.write_bytes(b'changed')
    with pytest.raises(Exception, match='REPLACEMENT_EXPANDED_SQL_CHANGED'):
        preserve_binary_logging(SimpleNamespace(root=tmp_path,guard=lambda:None),sql,'0'*64)
    assert sql.read_bytes() == b'changed'
