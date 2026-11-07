"""Real-file epoch contracts; Linux-only cases exercise actual flock ownership."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from test_retained_replacement_retry import retained
from test_legacy_main_clearance import closed_main


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def policy(tmp_path):
    root = tmp_path / 'epochs'; root.mkdir(mode=0o700)
    return dict(schemaVersion='SourceBackupEpochPolicy/v1', root=str(root),
                sourceIdentity='intruoyi:production',
                databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',
                sourceLockPath=str(tmp_path / 'source.lock'))


def module():
    import recovery_backup_epoch
    return recovery_backup_epoch


def fixture_event(value, previous=None, *, kind='INITIALIZED', state='READY', operation=None,
                  evidence=None):
    record = dict(schemaVersion='SourceBackupEpochEvent/v1',
                  sequence=0 if previous is None else previous[0]['sequence'] + 1,
                  kind=kind, policySha256=hashlib.sha256(canonical(value)).hexdigest(),
                  sourceIdentity=value['sourceIdentity'], databaseUuid=value['databaseUuid'],
                  sourceLockPath=value['sourceLockPath'], operationId=operation, state=state,
                  previousSha256=None if previous is None else previous[1]['sha256'],
                  recordedAt='2026-11-07T00:00:00Z', evidencePin=evidence)
    record['epochId'] = (previous[0]['epochId'] if kind == 'RESTORE_FINISHED'
                         else hashlib.sha256(canonical(record)).hexdigest())
    path = Path(value['root']) / ('%020d.json' % record['sequence'])
    path.write_bytes(canonical(record)); path.chmod(0o600)
    return record, dict(path=path.as_posix(), bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def receipt(tmp_path, state='SUCCEEDED'):
    path = tmp_path / ('receipt-' + state + '.json')
    path.write_bytes(canonical(dict(state=state, operationId='restore-1'))); path.chmod(0o600)
    return dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def bound_intent(tmp_path, value):
    claim = tmp_path / 'restore-1'; claim.mkdir(mode=0o700)
    path = claim / 'replacement-intent.json'
    path.write_bytes(canonical(dict(schemaVersion='ReplacementBackupEpochIntent/v1',
        operationId='restore-1', targetConfigRef='target', databaseUuid=value['databaseUuid'],
        replacementReceiptPath=(claim / 'replacement-result.json').as_posix())))
    path.chmod(0o600)
    return dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def bound_receipt(intent_pin, value, state='SUCCEEDED', **changes):
    path = Path(json.loads(Path(intent_pin['path']).read_text(encoding='utf-8'))['replacementReceiptPath'])
    record = dict(operationId='restore-1', targetConfigRef='target', databaseUuid=value['databaseUuid'], state=state)
    record.update(changes); path.write_bytes(canonical(record)); path.chmod(0o600)
    return dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_fixed_restore_intent_binds_terminal_receipt_location_and_target(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value); intent = bound_intent(tmp_path, value)
    start = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1', evidence=intent)
    assert module().read_current(value)['state'] == 'REPLACING'
    completed = fixture_event(value, start, kind='RESTORE_FINISHED', state='READY', operation='restore-1',
                              evidence=bound_receipt(intent, value))
    assert module().read_current(value)['eventPin'] == completed[1]


@pytest.mark.parametrize('change', ['target', 'uuid', 'receipt-path'])
def test_started_intent_cannot_authorize_another_terminal_receipt(tmp_path, change):
    value = policy(tmp_path); initial = fixture_event(value); intent = bound_intent(tmp_path, value)
    start = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1', evidence=intent)
    if change == 'target': evidence = bound_receipt(intent, value, targetConfigRef='another-target')
    elif change == 'uuid': evidence = bound_receipt(intent, value, databaseUuid='8f7a672a-ce77-11f1-9f3a-0242ac1ca820')
    else: evidence = receipt(tmp_path)
    fixture_event(value, start, kind='RESTORE_FINISHED', state='READY', operation='restore-1', evidence=evidence)
    with pytest.raises(ValueError, match='BACKUP_EPOCH_RECEIPT_BINDING_INVALID'):
        module().read_current(value)


def test_optional_replacement_policy_is_accepted_only_for_same_database_and_lock(tmp_path):
    from recovery_replace import validate
    from test_smallapp_replacement import target
    value = target(tmp_path)
    epoch = policy(tmp_path)
    value['replacement']['backupEpoch'] = epoch
    assert validate(value)['backupEpoch'] == epoch
    epoch['sourceLockPath'] = str(tmp_path / 'another.lock')
    with pytest.raises(ValueError, match='BACKUP_EPOCH_SOURCE_LOCK_MISMATCH'):
        validate(value)


def test_owner_policy_preserves_exact_target_and_closed_legacy_history(tmp_path, closed_main):
    from recovery_replace import replacement_value
    from recovery_retained_retry import validate_clearance
    target, claim, _, clearance = closed_main
    value = policy(tmp_path); value['sourceLockPath'] = target['replacement']['lockPath']
    configuration = dict(targets=dict(target=target), targetBackupEpochPolicies=dict(target=value))
    original_target = canonical(target)
    history = {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')}
    effective = replacement_value(configuration, 'target')
    assert effective['backupEpoch'] == value and effective is not target['replacement']
    assert canonical(configuration['targets']['target']) == original_target
    assert 'backupEpoch' not in target['replacement']
    assert validate_clearance(target, claim) == clearance
    assert {str(p): p.read_bytes() for p in tmp_path.rglob('*.json')} == history


@pytest.mark.parametrize('problem', ['unknown-target', 'wrong-lock', 'wrong-database', 'conflict'])
def test_owner_policy_does_not_shadow_or_change_registered_target(tmp_path, problem):
    from recovery_replace import replacement_value
    from test_smallapp_replacement import target
    target_config = target(tmp_path); value = policy(tmp_path)
    owner = dict(targets=dict(target=target_config), targetBackupEpochPolicies=dict(target=value))
    if problem == 'unknown-target': owner['targetBackupEpochPolicies'] = dict(unknown=value)
    elif problem == 'wrong-lock': value['sourceLockPath'] = str(tmp_path / 'other.lock')
    elif problem == 'wrong-database': value['databaseUuid'] = '8f7a672a-ce77-11f1-9f3a-0242ac1ca820'
    else: target_config['replacement']['backupEpoch'] = dict(value, sourceIdentity='different-source')
    before = canonical(target_config)
    with pytest.raises(ValueError, match='BACKUP_EPOCH_'):
        replacement_value(owner, 'target')
    assert canonical(target_config) == before


def test_epoch_storage_cannot_be_inside_replacement_operation_state(tmp_path):
    from recovery_replace import validate
    from test_smallapp_replacement import target
    value = target(tmp_path); epoch = policy(tmp_path)
    Path(epoch['root']).rmdir()
    nested = Path(value['replacement']['stateRoot']) / 'epochs'; nested.mkdir(mode=0o700)
    epoch['root'] = str(nested); value['replacement']['backupEpoch'] = epoch
    with pytest.raises(ValueError, match='BACKUP_EPOCH_REPLACEMENT_STATE_OVERLAP'):
        validate(value)


def test_epoch_storage_cannot_be_erased_by_registered_volume_replacement(tmp_path):
    from recovery_replace import validate
    from test_smallapp_replacement import target
    value = target(tmp_path); epoch = policy(tmp_path)
    value['replacement']['backupEpoch'] = epoch
    value['replacement']['services']['minio'] = dict(mounts=[dict(Source=str(tmp_path), RW=True)])
    with pytest.raises(ValueError, match='BACKUP_EPOCH_REPLACEMENT_STORAGE_OVERLAP'):
        validate(value)


def test_uninitialized_policy_never_invents_ready_epoch(tmp_path):
    value = policy(tmp_path)
    with pytest.raises(ValueError, match='BACKUP_EPOCH_UNINITIALIZED'):
        module().read_current(value)
    assert list(Path(value['root']).iterdir()) == []


def test_reader_returns_pinned_genesis_and_preserves_epoch_across_completion(tmp_path):
    value = policy(tmp_path)
    initial = fixture_event(value)
    current = module().read_current(value)
    assert current['state'] == 'READY' and current['eventPin'] == initial[1]
    started = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    current = module().read_current(value)
    assert current['epochId'] != initial[0]['epochId'] and current['state'] == 'REPLACING'
    finished = fixture_event(value, started, kind='RESTORE_FINISHED', state='READY',
                             operation='restore-1', evidence=receipt(tmp_path))
    current = module().read_current(value)
    assert current['epochId'] == started[0]['epochId'] and current['eventPin'] == finished[1]


def test_failed_restore_remains_an_explicit_new_epoch(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value)
    started = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    fixture_event(value, started, kind='RESTORE_FINISHED', state='FAILED_RETAINED',
                  operation='restore-1', evidence=receipt(tmp_path, 'FAILED_RETAINED'))
    current = module().read_current(value)
    assert current['state'] == 'FAILED_RETAINED' and current['epochId'] != initial[0]['epochId']


@pytest.mark.parametrize('field,new_value', [('sourceIdentity', 'another-source'),
    ('databaseUuid', '8f7a672a-ce77-11f1-9f3a-0242ac1ca820'), ('sourceLockPath', 'other.lock')])
def test_existing_history_cannot_be_reused_for_another_source(tmp_path, field, new_value):
    value = policy(tmp_path); fixture_event(value)
    value[field] = str(tmp_path / new_value) if field == 'sourceLockPath' else new_value
    with pytest.raises(ValueError, match='BACKUP_EPOCH_POLICY_CHANGED'):
        module().read_current(value)


def test_modified_old_event_is_rejected_even_if_latest_file_is_unchanged(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value)
    fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    path = Path(initial[1]['path']); path.write_bytes(path.read_bytes().replace(b'00:00:00Z', b'00:00:01Z'))
    with pytest.raises(ValueError, match='BACKUP_EPOCH_(CHAIN|EPOCH)_INVALID'):
        module().read_current(value)


def test_missing_event_and_unknown_files_block_instead_of_resetting(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value)
    fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    Path(initial[1]['path']).unlink()
    with pytest.raises(ValueError, match='BACKUP_EPOCH_CHAIN_INVALID'):
        module().read_current(value)
    (Path(value['root']) / 'uncommitted.tmp').write_bytes(b'incomplete')
    with pytest.raises(ValueError, match='BACKUP_EPOCH_JOURNAL_INVALID'):
        module().read_current(value)


def test_terminal_evidence_cannot_be_changed_after_publication(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value)
    started = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    evidence = receipt(tmp_path)
    fixture_event(value, started, kind='RESTORE_FINISHED', state='READY', operation='restore-1', evidence=evidence)
    Path(evidence['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='BACKUP_EPOCH_EVIDENCE_CHANGED'):
        module().read_current(value)


def test_missing_terminal_evidence_is_reported_as_epoch_failure(tmp_path):
    value = policy(tmp_path); initial = fixture_event(value)
    started = fixture_event(value, initial, kind='RESTORE_STARTED', state='REPLACING', operation='restore-1')
    evidence = receipt(tmp_path)
    fixture_event(value, started, kind='RESTORE_FINISHED', state='READY', operation='restore-1', evidence=evidence)
    Path(evidence['path']).unlink()
    with pytest.raises(ValueError, match='BACKUP_EPOCH_EVIDENCE_UNAVAILABLE'):
        module().read_current(value)


@pytest.mark.parametrize('change', ['relative-root', 'parent-alias', 'lock-inside-root', 'extra-field'])
def test_unsafe_policy_paths_and_unknown_fields_are_rejected(tmp_path, change):
    value = policy(tmp_path)
    if change == 'relative-root': value['root'] = 'epochs'
    if change == 'parent-alias': value['root'] = str(tmp_path / 'other' / '..' / 'epochs')
    if change == 'lock-inside-root': value['sourceLockPath'] = str(Path(value['root']) / 'source.lock')
    if change == 'extra-field': value['allowOldBaseline'] = True
    with pytest.raises(ValueError, match='BACKUP_EPOCH_'):
        module().validate_policy(value)


@contextmanager
def locked(value):
    import fcntl
    fd = os.open(value['sourceLockPath'], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        os.close(fd)


linux = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='requires real Linux flock and file modes')


@linux
def test_real_locked_lifecycle_is_append_only_and_invalidates_old_epoch(tmp_path):
    value = policy(tmp_path)
    with locked(value) as fd:
        initial = module().initialize(value, fd)
        initial_raw = Path(initial['eventPin']['path']).read_bytes()
        started = module().begin_restore(value, 'restore-1', fd)
        with pytest.raises(ValueError, match='BACKUP_EPOCH_RESTORE_IN_PROGRESS'):
            module().begin_restore(value, 'restore-2', fd)
        finished = module().complete_restore(value, 'restore-1', started['epochId'], 'READY', receipt(tmp_path), fd)
    assert initial['epochId'] != finished['epochId'] and finished['state'] == 'READY'
    assert Path(initial['eventPin']['path']).read_bytes() == initial_raw
    assert len(list(Path(value['root']).iterdir())) == 3


@linux
def test_unlocked_and_wrong_physical_lock_are_rejected_without_events(tmp_path):
    value = policy(tmp_path)
    fd = os.open(value['sourceLockPath'], os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with pytest.raises(ValueError, match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
            module().initialize(value, fd)
    finally: os.close(fd)
    other = dict(value, sourceLockPath=str(tmp_path / 'other.lock'))
    with locked(other) as wrong:
        with pytest.raises(ValueError, match='BACKUP_EPOCH_SOURCE_LOCK_MISMATCH'):
            module().initialize(value, wrong)
    assert list(Path(value['root']).iterdir()) == []


@linux
def test_shared_lock_blocks_a_real_competing_capture_process(tmp_path):
    value = policy(tmp_path)
    with locked(value) as fd:
        module().initialize(value, fd)
        probe = subprocess.run([sys.executable, '-c',
            'import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)',
            value['sourceLockPath']], capture_output=True)
    assert probe.returncode != 0 and b'BlockingIOError' in probe.stderr


@linux
@pytest.mark.parametrize('kind', ['root', 'record', 'lock'])
def test_symlinked_epoch_paths_are_rejected(tmp_path, kind):
    value = policy(tmp_path); initial = fixture_event(value)
    if kind == 'root':
        real = tmp_path / 'real'; Path(value['root']).rename(real); Path(value['root']).symlink_to(real, target_is_directory=True)
    elif kind == 'record':
        source = Path(initial[1]['path']); destination = tmp_path / 'real.json'; source.rename(destination); source.symlink_to(destination)
    else:
        destination = tmp_path / 'real.lock'; destination.touch(mode=0o600); Path(value['sourceLockPath']).symlink_to(destination)
    with pytest.raises(ValueError, match='BACKUP_EPOCH_'):
        module().read_current(value)


@linux
def test_writable_epoch_directory_is_rejected(tmp_path):
    value = policy(tmp_path); Path(value['root']).chmod(0o777)
    with pytest.raises(ValueError, match='BACKUP_EPOCH_PRIVATE_DIRECTORY_REQUIRED'):
        module().validate_policy(value)


@linux
@pytest.mark.parametrize('outcome', ['before-write-failure', 'after-write-failure', 'success', 'metadata-failure'])
@pytest.mark.parametrize('policy_location', ['embedded', 'owner'])
def test_replacement_controller_persists_boundary_before_drop_and_records_terminal(tmp_path, monkeypatch, outcome, policy_location):
    """Controller unit test: external database/container adapters are recording doubles.

    The epoch store, physical source lock, file tree, claims and receipts are real.
    This does not claim an actual database restore or E2E verification.
    """
    from contextlib import nullcontext
    from types import SimpleNamespace
    import recovery_replace
    import recovery_resource_admission
    import recovery_main_target
    from test_smallapp_replacement import target
    value = target(tmp_path); epoch = policy(tmp_path); value['replacement']['backupEpoch'] = epoch
    storage = tmp_path / 'minio'; storage.mkdir(mode=0o700)
    value['replacement']['services']['mysql'] = dict(id='recording-mysql')
    value['replacement']['services']['minio'] = dict(id='recording-minio',
        mounts=[dict(Source=str(storage), Destination='/data', RW=True)])
    value['application'] = dict(startOrder=[])
    configuration = dict(targets=dict(target=value))
    if policy_location == 'owner':
        value['replacement'].pop('backupEpoch')
        configuration['targetBackupEpochPolicies'] = dict(target=epoch)
    original_target = canonical(value)
    with locked(epoch) as fd:
        initial = module().initialize(epoch, fd)
    events = []

    class RecordingNative:
        def __init__(self, configuration, request, source, rules, chain, target_config, root, input_pins):
            self.original = request; self.config = target_config; self.root = root
            self.config_services = dict(minio=dict(id='recording-minio'))
            self.policy = dict(minioDataMount='/data'); self.mutation_dispatched = False
            self.mysql = SimpleNamespace(query=self.query)
        def guard(self): pass
        def timed_stage(self, name): return nullcontext()
        def docker(self, command, **kwargs): events.append('stop')
        def replacement_quiescence(self):
            events.append('quiescence')
            assert module().read_current(epoch)['epochId'] == initial['epochId']
            if outcome == 'before-write-failure': raise ValueError('UNIT_BEFORE_WRITE')
        def query(self, statement, **kwargs):
            if statement.startswith('DROP DATABASE'):
                current = module().read_current(epoch)
                assert current['state'] == 'REPLACING' and current['epochId'] != initial['epochId']
                assert self.mutation_dispatched
                events.append('drop')
                if outcome in ('after-write-failure', 'metadata-failure'): raise ValueError('UNIT_AFTER_WRITE')
            return '1'

    monkeypatch.setattr(recovery_replace, 'verify_services', lambda *args: None)
    monkeypatch.setattr(recovery_resource_admission, 'admit', lambda *args: None)
    monkeypatch.setattr(recovery_main_target, 'redis_command', lambda *args, **kwargs: None)
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-1', action='RESTORE',
                   sourceConfigRef='source', parentChainRef=None, recoveryPointRef='point', targetConfigRef='target')
    root = tmp_path / 'operation'; root.mkdir(mode=0o700)
    arguments = (configuration, request, root, [], lambda *args, **kwargs: ({}, {}),
                 RecordingNative, lambda *args: (dict(archiveRoots=[]), {}, [(None, None, dict(objects=dict(method='PHYSICAL_FILES')))]))
    if outcome == 'success':
        result = recovery_replace.execute(*arguments)
        assert result[0]['sourceBackupEpoch']['state'] == 'READY'
    elif outcome == 'metadata-failure':
        actual_open = os.open
        def fail_terminal_publication(path, *args, **kwargs):
            if 'drop' in events and Path(path) == Path(epoch['root']):
                raise OSError('UNIT_TERMINAL_STORAGE_FAILURE')
            return actual_open(path, *args, **kwargs)
        with monkeypatch.context() as fault:
            fault.setattr(module().os, 'open', fail_terminal_publication)
            with pytest.raises(OSError, match='UNIT_TERMINAL_STORAGE_FAILURE') as failure:
                recovery_replace.execute(*arguments)
        assert getattr(failure.value, 'native', None) is not None
        assert module().read_current(epoch)['state'] == 'REPLACING'
        assert module().try_reconcile_current(epoch)['state'] == 'FAILED_RETAINED'
    else:
        with pytest.raises(ValueError, match='UNIT_'):
            recovery_replace.execute(*arguments)
    current = module().read_current(epoch)
    assert canonical(value) == original_target
    if outcome == 'before-write-failure':
        assert current == initial and 'drop' not in events
    else:
        assert events.index('quiescence') < events.index('drop')
        assert current['epochId'] != initial['epochId']
        assert current['state'] == ('READY' if outcome == 'success' else 'FAILED_RETAINED')


@linux
def test_duplicate_initialization_and_wrong_completion_do_not_append(tmp_path):
    value = policy(tmp_path)
    with locked(value) as fd:
        module().initialize(value, fd)
        with pytest.raises(ValueError, match='BACKUP_EPOCH_ALREADY_INITIALIZED'):
            module().initialize(value, fd)
        start = module().begin_restore(value, 'restore-1', fd)
        with pytest.raises(ValueError, match='BACKUP_EPOCH_TRANSITION_INVALID'):
            module().complete_restore(value, 'wrong-operation', start['epochId'], 'READY', receipt(tmp_path), fd)
        assert module().read_current(value) == start
        assert len(list(Path(value['root']).iterdir())) == 2


@linux
@pytest.mark.parametrize('terminal', ['SUCCEEDED', 'FAILED_RETAINED'])
def test_daily_reconcile_waits_for_actual_lock_then_only_finalizes_proven_metadata(tmp_path, terminal):
    value = policy(tmp_path); intent = bound_intent(tmp_path, value)
    with locked(value) as fd:
        module().initialize(value, fd)
        started = module().begin_restore(value, 'restore-1', fd, intent_pin=intent)
        evidence = bound_receipt(intent, value, terminal)
        # A different open-file description cannot steal even this process's
        # active restore lock. No new event is created while it is held.
        assert module().try_reconcile_current(value) == started
        assert len(list(Path(value['root']).iterdir())) == 2
    result = module().try_reconcile_current(value)
    assert result['epochId'] == started['epochId']
    assert result['state'] == ('READY' if terminal == 'SUCCEEDED' else 'FAILED_RETAINED')
    assert module().try_reconcile_current(value) == result
    assert len(list(Path(value['root']).iterdir())) == 3
    assert hashlib.sha256(Path(evidence['path']).read_bytes()).hexdigest() == evidence['sha256']
