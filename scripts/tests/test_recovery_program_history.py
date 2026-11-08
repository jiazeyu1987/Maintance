"""Historical READY proofs over a real complete journal, never write authority."""
from pathlib import Path

import pytest

from test_backup_epoch import fixture_event
from test_recovery_program_generation import case, complete, write
import recovery_program_generation as program


def resolve(case, ready, **kwargs):
    return program._resolve_at_ready(case['policy'], ready, kwargs.pop('reader', program.document), **kwargs)


def unfinished(case, *, failed=False):
    started = fixture_event(case['epoch'], case['event'], kind='RESTORE_STARTED',
        state='REPLACING', operation='unfinished')
    if not failed:
        return started
    receipt = write(case['root']/'failure.json', dict(state='FAILED_RETAINED', operationId='unfinished'))
    return fixture_event(case['epoch'], started, kind='RESTORE_FINISHED',
        state='FAILED_RETAINED', operation='unfinished', evidence=receipt)


@pytest.mark.parametrize('failed', [False, True])
def test_historical_ready_does_not_open_nonready_global_state(case, failed):
    ready = case['event'][1]
    current = unfinished(case, failed=failed)
    original = {p:p.read_bytes() for p in case['root'].rglob('*.json')}
    selected = resolve(case, ready)
    assert selected['target'] == case['target']
    assert selected['targetPin'] == case['policy']['baselineTargetPin']
    assert selected['captures'] == case['policy']['captureConfigurationPins']
    assert selected['generationPin'] is None
    assert selected['epoch']['eventPin'] == ready and selected['epoch']['state'] == 'READY'
    assert ready in selected['evidence'] and current[1] in selected['evidence']
    with pytest.raises(Exception, match='PROGRAM_EPOCH_NOT_READY'):
        program.resolve_target(case['policy'])
    assert {p:p.read_bytes() for p in case['root'].rglob('*.json')} == original


def test_historical_completed_generation_is_revalidated_behind_failed_tail(case):
    first, first_pin, receipt = complete(case)
    ready = case['event'][1]
    current = unfinished(case, failed=True)
    selected = resolve(case, ready)
    assert selected['targetPin'] == first['targetPin'] and selected['generationPin'] == first_pin
    assert all(pin in selected['evidence'] for pin in (receipt, ready, current[1], first_pin))


def test_explicit_ready_prefix_does_not_select_later_success(case):
    first, first_pin, _ = complete(case)
    ready = case['event'][1]
    complete(case, 'restore-2')
    selected = resolve(case, ready)
    assert selected['generationPin'] == first_pin and selected['targetPin'] == first['targetPin']
    assert selected['epoch']['eventPin'] == ready and selected['epoch']['eventPin'] != case['event'][1]


@pytest.mark.parametrize('failed', [False, True])
def test_nonready_event_cannot_be_selected_as_success(case, failed):
    current = unfinished(case, failed=failed)
    with pytest.raises(Exception, match='PROGRAM_HISTORY_READY_INVALID'):
        resolve(case, current[1])


def test_ready_copy_outside_actual_journal_is_rejected(case):
    copied = write(case['root']/'copied.json', program.document(case['event'][1]))
    with pytest.raises(Exception, match='PROGRAM_HISTORY_READY_INVALID'):
        resolve(case, copied)


def test_wrong_ready_original_pin_is_rejected(case):
    forged = dict(case['event'][1], sha256='0'*64)
    with pytest.raises(Exception, match='PROGRAM_DOCUMENT_PIN_CONFLICT'):
        resolve(case, forged)


def test_corrupt_current_tail_blocks_even_an_intact_ready_prefix(case):
    ready = case['event'][1]
    current = unfinished(case)
    Path(current[1]['path']).write_bytes(b'{}')
    with pytest.raises(Exception, match='BACKUP_EPOCH_EVENT_INVALID'):
        resolve(case, ready)


def test_current_epoch_change_during_prefix_read_is_rejected(case):
    ready = case['event'][1]
    current = unfinished(case)
    changed = []
    def reader(reference):
        value = program.document(reference)
        if reference == case['policy']['baselineTargetPin'] and not changed:
            changed.append(True)
            receipt = write(case['root']/'late-failure.json', dict(state='FAILED_RETAINED', operationId='unfinished'))
            fixture_event(case['epoch'], current, kind='RESTORE_FINISHED', state='FAILED_RETAINED',
                operation='unfinished', evidence=receipt)
        return value
    with pytest.raises(Exception, match='PROGRAM_EPOCH_CHANGED'):
        resolve(case, ready, reader=reader)


def test_shared_guard_failure_is_not_swallowed(case):
    before = {p:p.read_bytes() for p in case['root'].rglob('*.json')}
    def guard():
        raise RuntimeError('shared budget exhausted')
    with pytest.raises(RuntimeError, match='shared budget exhausted'):
        resolve(case, case['event'][1], guard=guard)
    assert {p:p.read_bytes() for p in case['root'].rglob('*.json')} == before
