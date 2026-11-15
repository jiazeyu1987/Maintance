"""Exercise the actual generated data methods; SQL boundaries are unit doubles."""
import ast
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/backup_engine'))
import build_variants as builder


@pytest.fixture(scope='module')
def standard(tmp_path_factory):
    payload = builder.safe_fixes(builder.standard_sources()[0])
    root = tmp_path_factory.mktemp('prepared-database-standard')
    for name, raw in payload.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    sys.path[:0] = [str(root/name) for name in ('common', 'formal', 'control')]
    spec = importlib.util.spec_from_file_location('prepared_database_actual', root/'common/recovery_data.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.runtime_source = payload['common/recovery_minimal_runtime.py'].decode()
    return module


def native(standard, tmp_path):
    obj = standard.NativeData.__new__(standard.NativeData)
    obj.config = dict(preparedEmptyTarget=True, targetId='prepared-target', database='test')
    obj.original = dict(operationId='restore-one')
    obj.db_uuid = '11111111-1111-1111-1111-111111111111'
    obj.material = dict(recoveryPoint='full', database=dict(method='FORMAL_SQL_FULL', endPosition={'position':4}))
    obj.root = tmp_path
    obj.bound = lambda: None
    obj.seconds = lambda: 30
    obj.queries = []
    def query(sql, **kwargs):
        obj.queries.append((sql, kwargs))
        return [['1']]
    obj.mysql = SimpleNamespace(schema_query=query)
    class NoFullObservation:
        def __getattr__(self, name):
            raise AssertionError('WHOLE_DATABASE_OBSERVATION_REACHED')
    obj.modules = {'formal_data_evidence':NoFullObservation()}
    obj.request = {}
    return obj


def assert_limited(result):
    assert result['verificationState'] == 'NOT_PERFORMED'
    assert result['databaseApplyCompleted'] is True
    assert result['databaseQueryable'] is True
    assert result['fullSchemaDataEquivalenceVerified'] is False
    assert result['incrementalReplayAndAffectedDataVerified'] is False
    assert result['applicationVerified'] is False


def test_prepared_readback_is_one_query_and_existing_target_keeps_proof(standard, tmp_path):
    obj = native(standard, tmp_path)
    result = obj.database_readback()
    assert_limited(result)
    assert result['targetId'] == obj.config['targetId']
    assert result['operationId'] == obj.original['operationId']
    assert obj.queries == [('SELECT 1;', dict(database='test', expected_uuid=obj.db_uuid))]
    obj.config.pop('preparedEmptyTarget')
    with pytest.raises(AssertionError, match='WHOLE_DATABASE_OBSERVATION_REACHED'):
        obj.database_readback()


def test_import_and_query_failures_never_emit_success(standard, tmp_path, monkeypatch):
    obj = native(standard, tmp_path)
    def failed_query(*args, **kwargs): raise RuntimeError('QUERY_FAILED')
    obj.mysql.schema_query = failed_query
    with pytest.raises(RuntimeError, match='QUERY_FAILED'): obj.database_readback()
    obj.mysql.schema_query = lambda *args, **kwargs: [['0']]
    with pytest.raises(Exception, match='PREPARED_DATABASE_NOT_QUERYABLE'): obj.database_readback()
    obj.policy = dict(maxExpandedBytes=100)
    sql_pin = dict(path=str(tmp_path/'archive.gz'), sha256='a'*64, bytes=10)
    obj.material.update(payloadPins=[sql_pin]); obj.material['database']['sqlPin'] = sql_pin
    obj.modules['formal_sql_restore'] = SimpleNamespace(empty_database=lambda *args:None,
        expand_checked=lambda *args:('b'*64,10))
    obj.db_target = {}; obj.target = dict(targetIdentityPin={})
    obj.timed_stage = lambda name:nullcontext()
    obj.restore_database_settings = lambda: {}
    monkeypatch.setattr(standard, 'stage_private_sql', lambda *args:sql_pin)
    def failed_import(*args): raise RuntimeError('IMPORT_FAILED')
    obj.import_sql = failed_import
    obj.database_readback = lambda: pytest.fail('readback after failed import')
    with pytest.raises(RuntimeError, match='IMPORT_FAILED'): obj.full_database()
    obj.root = tmp_path/'successful-import'; obj.root.mkdir()
    applied = []
    obj.import_sql = lambda *args: applied.append(True)
    obj.mysql.schema_query = lambda *args, **kwargs: [['1']]
    def after_import():
        assert applied == [True]
        return standard.NativeData.database_readback(obj)
    obj.database_readback = after_import
    assert_limited(obj.full_database())


def test_incremental_consumes_only_same_prepared_operation_and_continuous_chain(standard, tmp_path):
    obj = native(standard, tmp_path)
    previous = obj.database_readback()
    obj.material = dict(recoveryPoint='i1', database=dict(method='BINLOG_SQL',
        startPosition={'position':4}, endPosition={'position':8}))
    obj.incremental_captured_sql = lambda:obj.database_readback()
    def consume(record, name):
        obj.request['previousDatabaseResultPin'] = standard.write(tmp_path/(name+'.json'),record)
        return obj.incremental_database()
    result = consume(previous, 'full-result'); assert_limited(result)
    obj.material['database'].update(startPosition={'position':8}, endPosition={'position':12})
    result2 = consume(result, 'i1-result'); assert_limited(result2)
    obj.material['database']['startPosition'] = {'position':4}
    for field, value in [('targetId','other'), ('operationId','other'), ('databaseUuid','other'),
                         ('endPosition',{'position':3}), ('databaseApplyCompleted',False), ('databaseQueryable',False)]:
        altered = dict(previous, **{field:value})
        with pytest.raises(Exception, match='PREVIOUS_DATABASE_STEP_REQUIRED'):
            consume(altered, 'invalid-'+field)
    obj.config.pop('preparedEmptyTarget')
    with pytest.raises(Exception, match='PREVIOUS_DATABASE_STEP_REQUIRED'): consume(previous, 'old-target')


def test_consistency_and_final_runtime_keep_limited_database_evidence(standard, tmp_path):
    obj = native(standard, tmp_path)
    result = obj.database_readback(); assert_limited(result)
    database_pin = standard.write(tmp_path/'database-result.json', result)
    mapping = tmp_path/'mapping.jsonl'
    mapping.write_text(json.dumps(dict(sourceBucket='bucket',key='key',sourceVersionId='v',isLatest=True))+'\n', encoding='utf-8')
    object_pin = standard.write(tmp_path/'object-result.json', dict(recoveryPoint='full',
        versionMappingPin=standard.pin(mapping),payloadContentVerified=False))
    reference = standard.write(tmp_path/'references.json', dict(schemaVersion='RecoveryReferenceInventory/v1',
        recoveryPoint='full',complete=True,databaseRows=[],objectReferences=[]))
    obj.material['referenceInventoryPin'] = reference
    obj.plan = dict(recoveryPoint='full');obj.policy=dict(referenceQueries=[],businessInvariants=[])
    obj.request.update(databaseResultPin=database_pin, objectResultPin=object_pin)
    obj.target = dict(targetIdentityPin={});obj.object_client=lambda:None
    consistent = standard.write(tmp_path/'consistency.json',obj.consistency())
    tree=ast.parse(standard.runtime_source)
    execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute_empty')
    final=next(n for n in ast.walk(execute) if isinstance(n,ast.Return) and isinstance(n.value,ast.Tuple))
    # Execute the actual final expression: the runtime must preserve, not upgrade, evidence.
    value, returned = eval(compile(ast.Expression(final.value),'actual-runtime-result','eval'),dict(
        chain=[({},None,dict(recoveryPoint='full'))],request=dict(targetConfigRef='prepared-target'),
        db_pins=[database_pin],object_pins=[object_pin],consistent=consistent,derived={},application={},
        cleanup_pin={},native=obj))
    assert returned is obj and value['businessAcceptance']=='NOT_PERFORMED'
    assert standard.pinned_json(value['databaseResultPins'][0]) == result
    assert 'fullSchemaDataEquivalenceVerified' not in value
