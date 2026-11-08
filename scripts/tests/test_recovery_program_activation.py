"""Actual Linux source locks, immutable files and real epoch transitions."""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

from test_recovery_program_generation import case, switched, write
from recovery_backup_epoch import begin_restore, complete_restore, read_current
from recovery_engine import pinned_json

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux flock required')


def module():
    import recovery_program_activation
    return recovery_program_activation


@contextmanager
def locked(case, *, held=True):
    import fcntl
    fd = os.open(case['epoch']['sourceLockPath'], os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if held:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        os.close(fd)


def claim(case, operation='restore-1'):
    root = Path(case['target']['replacement']['stateRoot'])/operation
    root.mkdir(mode=0o700)
    return root


def start(case, root, fd, *, operation='restore-1'):
    intent = write(root/'intent.json', dict(schemaVersion='ReplacementBackupEpochIntent/v1',
        operationId=operation, targetConfigRef='target57', databaseUuid=case['epoch']['databaseUuid'],
        replacementReceiptPath=(root/'replacement-result.json').as_posix()))
    return begin_restore(case['epoch'], operation, fd, intent_pin=intent)


def snapshot(case, fd, operation='restore-1'):
    return module().snapshot_restore(case['policy'], operation, fd)


def stage(case, context, fd, **kwargs):
    return module().stage_generation(case['policy'], context,
        target_pin=kwargs.pop('target_pin', case['policy']['baselineTargetPin']),
        capture_pins=kwargs.pop('capture_pins', {'source57': case['base_pin']}),
        switch_result_pin=kwargs.pop('switch_result_pin', None), lock_fd=fd, **kwargs)


def finish(case, root, epoch, generation, fd, *, state='SUCCEEDED'):
    receipt = write(root/'replacement-result.json', dict(state=state, operationId=root.name,
        targetConfigRef='target57', databaseUuid=case['epoch']['databaseUuid'], programGenerationPin=generation))
    return complete_restore(case['epoch'], root.name, epoch['epochId'],
        'READY' if state=='SUCCEEDED' else 'FAILED_RETAINED', receipt, fd)


def test_locked_snapshot_and_stage_activate_only_after_real_success(case):
    root = claim(case)
    before = (case['root']/'target.json').read_bytes()
    with locked(case) as fd:
        context = snapshot(case, fd)
        assert Path(context['path']) == root/'program-context.json'
        captured = module().document(context)
        assert captured['readyEpoch'] == read_current(case['epoch'])
        epoch = start(case, root, fd)
        generation = stage(case, context, fd)
        from recovery_program_generation import resolve_target
        with pytest.raises(Exception, match='PROGRAM_EPOCH_NOT_READY'):
            resolve_target(case['policy'])
        finish(case, root, epoch, generation, fd)
        target, target_pin, evidence = resolve_target(case['policy'])
    assert target == case['target'] and target_pin == case['policy']['baselineTargetPin']
    assert generation in evidence and before == (case['root']/'target.json').read_bytes()


def test_switched_generation_produced_from_real_replacement_epoch(case, tmp_path):
    target, capture, switch = switched(case, tmp_path)
    root = claim(case)
    target_pin = write(root/'new-target.json', target)
    capture_pin = write(root/'new-capture.json', capture)
    with locked(case) as fd:
        context = snapshot(case, fd)
        epoch = start(case, root, fd)
        generation = stage(case, context, fd, target_pin=target_pin,
            capture_pins={'source57': capture_pin}, switch_result_pin=switch)
        finish(case, root, epoch, generation, fd)
    from recovery_program_generation import resolve_capture
    assert resolve_capture(case['policy'], 'source57', case['base_pin'])[0] == capture_pin


def test_second_restore_continues_exact_parent_generation(case):
    with locked(case) as fd:
        root = claim(case)
        context = snapshot(case, fd)
        epoch = start(case, root, fd)
        first = stage(case, context, fd)
        finish(case, root, epoch, first, fd)
        second_root = claim(case, 'restore-2')
        context = snapshot(case, fd, 'restore-2')
        start(case, second_root, fd, operation='restore-2')
        second = stage(case, context, fd)
    assert module().document(second)['parentGenerationPin'] == first


@pytest.mark.parametrize('phase', ['snapshot', 'stage'])
def test_real_exclusive_lock_required_before_any_metadata_write(case, phase):
    root = claim(case)
    with locked(case) as fd:
        if phase == 'stage':
            context = snapshot(case, fd)
            start(case, root, fd)
    with locked(case, held=False) as fd:
        with pytest.raises(Exception, match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
            snapshot(case, fd) if phase=='snapshot' else stage(case, context, fd)
    assert not (root/('program-context.json' if phase=='snapshot' else 'generation.json')).exists()


@pytest.mark.parametrize('phase', ['snapshot', 'stage'])
def test_existing_metadata_is_immutable_and_replay_refused(case, phase):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        if phase == 'stage':
            start(case, root, fd)
            stage(case, context, fd)
        path = root/('program-context.json' if phase=='snapshot' else 'generation.json')
        original = path.read_bytes()
        with pytest.raises(Exception, match='PROGRAM_METADATA_ALREADY_EXISTS'):
            snapshot(case, fd) if phase=='snapshot' else stage(case, context, fd)
    assert path.read_bytes() == original


def test_stage_requires_same_operation_as_current_epoch(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        other = claim(case, 'other')
        start(case, other, fd, operation='other')
        with pytest.raises(Exception, match='PROGRAM_RESTORE_EPOCH_CHANGED'):
            stage(case, context, fd)
    assert not (root/'generation.json').exists()


def test_stage_requires_started_state_and_exact_previous_ready_event(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        with pytest.raises(Exception, match='PROGRAM_RESTORE_EPOCH_CHANGED'):
            stage(case, context, fd)
        current = start(case, root, fd)
        finish(case, root, current, None, fd, state='FAILED_RETAINED')
        with pytest.raises(Exception, match='PROGRAM_RESTORE_EPOCH_CHANGED'):
            stage(case, context, fd)
    assert not (root/'generation.json').exists()


@pytest.mark.parametrize('field', ['database', 'writer', 'credential', 'lock'])
def test_stage_cannot_change_target_scope_without_program_switch(case, field):
    root = claim(case)
    target = deepcopy(case['target'])
    if field=='database': target['database']='other'
    elif field=='writer': target['mainApplication']['writerAdmission']['approvedWriterContainerIds']=[]
    elif field=='credential': target['secrets']={}
    else: target['replacement']['lockPath']='/other.lock'
    candidate = write(root/'candidate.json', target)
    with locked(case) as fd:
        context = snapshot(case, fd)
        start(case, root, fd)
        with pytest.raises(Exception, match='PROGRAM_TARGET_SCOPE_CHANGED'):
            stage(case, context, fd, target_pin=candidate)
    assert not (root/'generation.json').exists()


@pytest.mark.parametrize('field', ['writer', 'database', 'image', 'source'])
def test_stage_cannot_reassign_capture_scope(case, field):
    root = claim(case)
    capture = deepcopy(case['capture'])
    if field=='writer': capture['source']['writerContainerIds']=[]
    elif field=='database': capture['source']['database']='other'
    elif field=='image': capture['source']['applicationImageIds']=[]
    else: capture['sourceConfigRef']='other'
    candidate = write(root/'candidate.json', capture)
    with locked(case) as fd:
        context = snapshot(case, fd)
        start(case, root, fd)
        with pytest.raises(Exception, match='PROGRAM_CAPTURE_SCOPE_CHANGED'):
            stage(case, context, fd, capture_pins={'source57': candidate})
    assert not (root/'generation.json').exists()


def test_capture_source_set_must_match_policy_exactly(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        start(case, root, fd)
        with pytest.raises(Exception, match='PROGRAM_CAPTURE_BINDINGS_INVALID'):
            stage(case, context, fd, capture_pins={})
    assert not (root/'generation.json').exists()


def test_policy_cannot_change_after_snapshot(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        start(case, root, fd)
        case['policy'] = dict(case['policy'], targetConfigRef='other')
        with pytest.raises(Exception, match='PROGRAM_RESTORE_CONTEXT_INVALID'):
            stage(case, context, fd)
    assert not (root/'generation.json').exists()


def test_context_original_bytes_are_required(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        start(case, root, fd)
        Path(context['path']).write_bytes(b'{}')
        with pytest.raises(Exception, match='PROGRAM_DOCUMENT_CHANGED'):
            stage(case, context, fd)
    assert not (root/'generation.json').exists()


@pytest.mark.parametrize('phase', ['snapshot', 'stage'])
def test_shared_budget_exhaustion_never_creates_metadata(case, phase):
    root = claim(case)
    def expired(): raise RuntimeError('shared restore budget expired')
    with locked(case) as fd:
        if phase=='stage':
            context = snapshot(case, fd)
            start(case, root, fd)
        with pytest.raises(RuntimeError, match='shared restore budget expired'):
            if phase=='snapshot': module().snapshot_restore(case['policy'], 'restore-1', fd, guard=expired)
            else: stage(case, context, fd, guard=expired)
    assert not (root/('program-context.json' if phase=='snapshot' else 'generation.json')).exists()


def test_epoch_change_during_validation_blocks_generation(case):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        current = start(case, root, fd)
        changed=[]
        def reader(reference):
            value = module().document(reference)
            if reference == case['policy']['baselineTargetPin'] and not changed:
                changed.append(True)
                finish(case, root, current, None, fd, state='FAILED_RETAINED')
            return value
        with pytest.raises(Exception, match='PROGRAM_RESTORE_EPOCH_CHANGED'):
            stage(case, context, fd, reader=reader)
    assert changed and not (root/'generation.json').exists()


@pytest.mark.parametrize('field', ['targetPin', 'parentGenerationPin', 'capturePins'])
def test_context_fields_must_come_from_actual_previous_ready_receipt(case, field):
    root = claim(case)
    with locked(case) as fd:
        context = snapshot(case, fd)
        value = module().document(context)
        if field == 'targetPin':
            value[field] = write(root/'same-target.json', case['target'])
            value['evidencePins'].append(value[field])
        elif field == 'parentGenerationPin':
            value[field] = case['policy']['baselineTargetPin']
        else:
            value[field] = {'source57': write(root/'same-capture.json', case['capture'])}
            value['evidencePins'].append(value[field]['source57'])
        # Fault injection supplies a newly pinned but semantically altered
        # context. SHA validity cannot replace binding to the original epoch.
        changed = write(Path(context['path']), value)
        start(case, root, fd)
        with pytest.raises(Exception, match='PROGRAM_RESTORE_CONTEXT_INVALID'):
            stage(case, changed, fd)
    assert not (root/'generation.json').exists()
