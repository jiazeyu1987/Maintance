"""Real Linux epoch/ctx/flock/custody; host/SQL replies are protocol units.

These tests do not claim a kernel firewall, real DB/MinIO or business restore.
The original protection implementations operate on actual private journals.
"""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from test_recovery_program_protection import case, protection_execution, install, frozen_journals
from recovery_engine import RecoveryError
from recovery_mysql_scheduler import MainMysqlScheduler, STATE_SQL


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux context/flock required')


@pytest.fixture
def capture_custody(protection_execution, monkeypatch):
    h = protection_execution
    original = h.transport.query
    state = dict(readonly='0', superreadonly='0', transactions=0)
    def query(native, sql, *, mutation=False):
        native.guard()
        if sql == STATE_SQL:
            h.transport.calls.append(('sql',native.native_context.phase,sql,mutation))
            return ('\t'.join([h.transport.uuid,state['readonly'],state['superreadonly'],h.transport.scheduler])+'\n').encode()
        if sql == 'SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;':
            assert mutation
            h.transport.calls.append(('sql',native.native_context.phase,sql,mutation))
            state.update(readonly='1',superreadonly='1')
            return b''
        if sql.startswith('SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only, '):
            assert not mutation
            return ('\t'.join([state['readonly'],state['superreadonly'],str(state['transactions'])])+'\n').encode()
        return original(native,sql,mutation=mutation)
    import recovery_main_target as main
    monkeypatch.setattr(main,'mysql_query',query)
    h.preparation.protection_custody = h.custody
    h.capture_state = state
    h.capture_query = query
    return h


def test_capture_lease_requires_installed_original_protections_before_first_sql(capture_custody):
    h = capture_custody; before = len(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_PROTECTION_NOT_INSTALLED'):
        h.custody.capture_view_for(h.preparation)
    assert len(h.transport.calls) == before


def test_typed_capture_fence_keeps_three_original_journals_and_paused_scheduler(capture_custody):
    h = capture_custody; install(h); before = frozen_journals(h)
    lease = h.custody.capture_view_for(h.preparation)
    lease.begin()
    lease.verify()
    assert h.capture_state['readonly'] == h.capture_state['superreadonly'] == '1'
    assert h.transport.scheduler == 'OFF' and h.transport.releases == []
    assert all(path.read_bytes() == raw for path,raw in before.items())
    snapshot = lease.snapshot()
    assert snapshot['schemaVersion'] == 'MainTargetCaptureProtection/v1'
    assert snapshot['state'] == 'ACTIVE' and snapshot['sourceRestored'] is False
    assert snapshot['operationId'] == h.e.request['operationId']
    assert snapshot['schedulerActivePin']['path'] == str(h.e.claim/'mysql-scheduler/active.json')
    assert Path(snapshot['captureFenceActivePin']['path']).is_file()
    assert not (h.e.claim/'mysql-scheduler/capture-fence-active.json').exists()


def test_ordinary_scheduler_still_refuses_one_one_flags(capture_custody):
    h = capture_custody; install(h)
    lease = h.custody.capture_view_for(h.preparation);lease.begin()
    scheduler = MainMysqlScheduler(h.preparation.config,h.e.request['operationId'],h.e.claim/'mysql-scheduler',
        lambda sql,**kwargs:h.capture_query(h.preparation,sql,**kwargs))
    with pytest.raises(RecoveryError,match='MAIN_SCHEDULER_DATABASE_CHANGED'):
        scheduler.verify()
    lease.verify()
    assert h.transport.scheduler == 'OFF' and not h.transport.releases


@pytest.mark.parametrize('change',['readonly','uuid','scheduler','transactions','journal'])
def test_active_capture_rejects_barrier_and_original_journal_drift(capture_custody,change):
    h = capture_custody;install(h)
    lease = h.custody.capture_view_for(h.preparation);lease.begin()
    if change == 'readonly':h.capture_state['readonly']='0'
    elif change == 'uuid':h.transport.uuid='22222222-2222-2222-2222-222222222222'
    elif change == 'scheduler':h.transport.scheduler='ON'
    elif change == 'transactions':h.capture_state['transactions']=1
    else:
        path=h.e.claim/'mysql-scheduler/active.json';path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_|PROGRAM_PROTECTION_|MAIN_SCHEDULER_|FORMAL_DATABASE_'):
        lease.verify()
    assert not h.transport.releases
    assert not (h.e.claim/'mysql-scheduler/released.json').exists()


def test_capture_lease_is_single_and_blocks_stage_without_preservation_proof(capture_custody):
    h=capture_custody;install(h)
    lease=h.custody.capture_view_for(h.preparation);lease.begin()
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_ALREADY_CLAIMED'):
        h.custody.capture_view_for(h.preparation)
    with pytest.raises(RecoveryError,match='PROGRAM_TARGET_CAPTURE_PENDING'):
        h.ctx.stage(None)
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_PRESERVATION_REQUIRED'):
        lease.handoff(None)
    assert h.transport.scheduler=='OFF' and h.capture_state['readonly']=='1'


def test_capture_close_never_restores_flags_or_releases_or_replays(capture_custody):
    h=capture_custody;install(h)
    lease=h.custody.capture_view_for(h.preparation);lease.begin()
    before=deepcopy(h.transport.calls)
    lease.close();lease.close()
    assert h.transport.calls==before
    assert h.capture_state['readonly']==h.capture_state['superreadonly']=='1'
    assert h.transport.scheduler=='OFF' and not h.transport.releases


def test_actual_lock_loss_blocks_capture_before_any_sql_dispatch(capture_custody):
    import fcntl
    h=capture_custody;install(h)
    lease=h.custody.capture_view_for(h.preparation)
    before=len(h.transport.calls);fcntl.flock(h.fd,fcntl.LOCK_UN)
    with pytest.raises(ValueError,match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
        lease.begin()
    assert len(h.transport.calls)==before


def test_main_session_rejects_duck_typed_view_before_output_or_transport(tmp_path):
    module=importlib.import_module('recovery_target_capture')
    probes=[]
    fake=SimpleNamespace(native_context=SimpleNamespace(phase='PREPARATION',guard=lambda:probes.append('guard')),
        command=lambda *a,**k:probes.append('command'))
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_VIEW_INVALID'):
        module.MainTargetCapture.prepare(fake,capture_ref='source57',reservation_pin=None)
    assert probes==[] and list(tmp_path.iterdir())==[]
