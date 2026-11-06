"""MAIN-only scheduler custody; failures must not enable imported events."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import load, pin

UUID = '11111111-1111-1111-1111-111111111111'


@pytest.fixture
def model(tmp_path):
    state = dict(scheduler='ON', uuid=UUID, readonly='0', superreadonly='0',
                 workers='0', transactions='0', databases={'mysql', 'sys', 'information_schema', 'performance_schema', 'app'})
    calls = []
    def query(statement, *, mutation=False):
        calls.append((statement, mutation))
        if statement.startswith('SET GLOBAL event_scheduler='):
            assert mutation
            state['scheduler'] = statement.split('=')[1].rstrip(';')
            return b''
        assert not mutation
        if statement == 'SHOW DATABASES;':
            return ('\n'.join(sorted(state['databases']))+'\n').encode()
        if '@@server_uuid' in statement:
            return ('\t'.join(state[k] for k in ('uuid', 'readonly', 'superreadonly', 'scheduler'))+'\n').encode()
        if 'PROCESSLIST' in statement: return (state['workers']+'\n').encode()
        if 'innodb_trx' in statement: return (state['transactions']+'\n').encode()
        raise AssertionError(statement)
    target = dict(database='app', mainApplication={'schemaVersion': 'RegisteredMainApplication/v2'},
                  services=[dict(role='mysql', id='a'*64, imageId='sha256:'+'b'*64)],
                  replacement=dict(databaseUuid=UUID))
    def create(operation='operation-1', inherited=None):
        module = importlib.import_module('recovery_mysql_scheduler')
        return module.MainMysqlScheduler(target, operation, tmp_path/operation, query, inherited=inherited)
    return SimpleNamespace(state=state, calls=calls, target=target, create=create, root=tmp_path)


@pytest.mark.parametrize('original', ['ON', 'OFF', 'DISABLED'])
def test_original_state_is_captured_paused_and_exactly_restored(model, original):
    model.state['scheduler'] = original
    scheduler = model.create()
    scheduler.preflight()
    assert not model.calls[-1][1] and not scheduler.journal.exists()
    scheduler.install()
    assert model.state['scheduler'] == ('DISABLED' if original == 'DISABLED' else 'OFF')
    intent = pin(scheduler.journal/'intent.json')
    active = pin(scheduler.journal/'active.json')
    scheduler.verify()
    release = scheduler.release()
    assert model.state['scheduler'] == original
    assert load(Path(release['path']))['originalState'] == original
    assert pin(scheduler.journal/'intent.json') == intent
    assert pin(scheduler.journal/'active.json') == active
    assert sum(m for _, m in model.calls) == (2 if original == 'ON' else 0)


@pytest.mark.parametrize('key,value', [('uuid', 'different'), ('readonly', '1'),
    ('superreadonly', '1'), ('scheduler', 'UNKNOWN')])
def test_invalid_identity_or_global_state_never_mutates(model, key, value):
    model.state[key] = value
    with pytest.raises(Exception, match='MAIN_SCHEDULER_'):
        model.create().install()
    assert not any(m for _, m in model.calls)


def test_other_application_schema_blocks_global_scheduler_control(model):
    model.state['databases'].add('another_business')
    with pytest.raises(Exception, match='MAIN_SCHEDULER_DATABASE_SCOPE_CHANGED'):
        model.create().install()
    assert not any(m for _, m in model.calls)


@pytest.mark.parametrize('key', ['workers', 'transactions'])
def test_running_work_blocks_destructive_continuation_and_retains_pause(model, key, monkeypatch):
    monkeypatch.setattr(importlib.import_module('recovery_mysql_scheduler'), 'DRAIN_TIMEOUT_SECONDS', 0)
    model.state[key] = '1'
    scheduler = model.create()
    with pytest.raises(Exception, match='MAIN_SCHEDULER_NOT_QUIESCED'):
        scheduler.install()
    assert model.state['scheduler'] == 'OFF'
    assert (scheduler.journal/'intent.json').is_file()
    assert not (scheduler.journal/'active.json').exists()
    assert not (scheduler.journal/'released.json').exists()


def test_failed_restore_has_no_implicit_scheduler_release(model):
    scheduler = model.create(); scheduler.install()
    del scheduler
    assert model.state['scheduler'] == 'OFF'
    assert not (model.root/'operation-1/released.json').exists()


def test_state_drift_and_journal_replacement_are_rejected(model):
    scheduler = model.create(); scheduler.install()
    model.state['scheduler'] = 'ON'
    with pytest.raises(Exception, match='MAIN_SCHEDULER_STATE_CHANGED'): scheduler.verify()
    model.state['scheduler'] = 'OFF'
    other = model.create('different-operation')
    other.journal = scheduler.journal
    with pytest.raises(Exception, match='MAIN_SCHEDULER_IDENTITY_CHANGED'): other.verify()


def test_paused_retained_failure_preserves_first_original_state_across_retry(model):
    first = model.create(); first.install()
    custody = first.recovery_custody()
    assert model.state['scheduler'] == 'OFF'
    second = model.create('retry-2', inherited=custody)
    second.install()
    assert load(second.journal/'intent.json')['originalState'] == 'ON'
    second.release()
    assert model.state['scheduler'] == 'ON'
    assert not (first.journal/'released.json').exists()


def test_disabled_dedicated_sql_validator_is_not_relaxed_for_on_scheduler():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/backup_engine/formal'))
    import formal_sql_restore as sql
    mysql = SimpleNamespace(query=lambda _: UUID+'\t0\t0\t0\tON\n')
    with pytest.raises(Exception, match='FORMAL_SQL_DATABASE_CHANGED'):
        sql.database_state(mysql, dict(databaseUuid=UUID, database='app'))


def test_main_quiescence_invokes_scheduler_before_sql_and_redis_checks():
    import recovery_main_target as main
    calls = []
    native = main.guarded_type(object)()
    native.config = dict(mainApplication={'schemaVersion': 'RegisteredMainApplication/v2'}, database='app')
    native.mysql = SimpleNamespace(query=lambda _: calls.append('sql') or '0')
    scheduler = SimpleNamespace(install=lambda: calls.append('pause'))
    with patch.object(main, 'mysql_scheduler', return_value=scheduler, create=True), \
         patch.object(main, 'archive_view', return_value=None), patch.object(main, 'published_fence', return_value=None), \
         patch.object(main, 'redis_command', return_value=b'addr=127.0.0.1:1234\n'):
        native.replacement_quiescence()
    assert calls == ['pause', 'sql', 'sql']


def test_main_scheduler_is_released_only_after_other_protections():
    import recovery_main_target as main
    calls=[]; native=main.guarded_type(object)(); native.config={'mainApplication': {}}
    def protection(name): return SimpleNamespace(release=lambda: calls.append(name) or {'path': name})
    with patch.object(main, 'mysql_scheduler', return_value=protection('scheduler'), create=True), \
         patch.object(main, 'archive_view', return_value=protection('archive')), \
         patch.object(main, 'published_fence', return_value=protection('ports')):
        result=native.replacement_finish()
    assert calls == ['archive', 'ports', 'scheduler']
    assert result['mysqlSchedulerReleasePin'] == {'path': 'scheduler'}


def test_protection_release_error_never_enables_scheduler():
    import recovery_main_target as main
    scheduler=SimpleNamespace(release=lambda: pytest.fail('must remain paused'))
    native=main.guarded_type(object)();native.config={'mainApplication': {}}
    archive=SimpleNamespace(release=lambda: (_ for _ in ()).throw(ValueError('archive drift')))
    with patch.object(main, 'mysql_scheduler', return_value=scheduler, create=True), \
         patch.object(main, 'archive_view', return_value=archive), pytest.raises(ValueError, match='archive drift'):
        native.replacement_finish()


def test_release_transport_error_repauses_before_propagating(model):
    scheduler=model.create();scheduler.install();original_query=scheduler.query
    def lost_response(statement, *, mutation=False):
        response=original_query(statement,mutation=mutation)
        if statement=='SET GLOBAL event_scheduler=ON;':raise RuntimeError('response lost')
        return response
    scheduler.query=lost_response
    with pytest.raises(RuntimeError,match='response lost'):scheduler.release()
    assert model.state['scheduler']=='OFF'
    assert not (scheduler.journal/'released.json').exists()


def test_pause_waits_for_actual_mysql_event_thread_exit(model):
    scheduler=model.create();original_query=scheduler.query;observations=[]
    def asynchronous_thread_exit(statement, *, mutation=False):
        if 'PROCESSLIST' in statement:
            observations.append(statement)
            return b'1\n' if len(observations)==1 else b'0\n'
        return original_query(statement,mutation=mutation)
    scheduler.query=asynchronous_thread_exit
    scheduler.install()
    assert len(observations)>=2 and model.state['scheduler']=='OFF'


def test_retained_protection_handoff_verifies_every_protection_before_release(tmp_path,monkeypatch):
    import recovery_main_target as main
    import recovery_retained_retry as retry
    from recovery_engine import write
    calls=[];claim=tmp_path/'failed';claim.mkdir()
    target=dict(mainApplication={'schemaVersion':'RegisteredMainApplication/v2'},
        dataPolicy={},secrets={},services=[dict(role=r,id=r) for r in ('mysql','redis','backend','frontend','minio')])
    class Observation:
        def __init__(self,*args):self.config_services={r['role']:r for r in target['services']};self.policy={}
        def inspect(self,role):return {'State':{'Running':role in ('mysql','redis')}}
    monkeypatch.setattr(retry,'ReadOnlyTarget',Observation)
    def protection(name):
        journal=claim/name;journal.mkdir();write(journal/'active.json',{'owner':'failed'})
        def verify():calls.append('verify-'+name)
        def release():
            calls.append('release-'+name)
            return write(journal/'released.json',dict(operationId='failed',originalMountRestored=True))
        return SimpleNamespace(journal=journal,verify=verify,release=release)
    archive,ports=protection('archive'),protection('ports')
    monkeypatch.setattr(main,'archive_view',lambda _:archive)
    monkeypatch.setattr(main,'published_fence',lambda _:ports)
    before=[pin(p.journal/'active.json') for p in (archive,ports)]
    result=main.release_retained_protections(dict(targets={'target':target},environmentMysqlClientPath='/usr/bin/mysql'),
        dict(operationId='failed',targetConfigRef='target'),tmp_path,claim)
    assert calls==['verify-archive','verify-ports','release-archive','release-ports']
    proof=load(Path(result['mainProtectionRecoveryPin']['path']))
    assert proof['originalPins']==before and len(proof['releasePins'])==2
    assert [pin(p.journal/'active.json') for p in (archive,ports)]==before
