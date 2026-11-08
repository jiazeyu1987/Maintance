"""Native context contracts over actual metadata, inotify and Linux flock.

No Docker/SQL dispatch is performed. Invocation documents exercise only the
evidence protocol, and must not be reported as real server execution evidence.
"""
from copy import deepcopy
from pathlib import Path
import os
import sys

import pytest

from test_recovery_program_execution import execution, bind, resolve
from test_recovery_program_generation import case, write
from test_recovery_program_activation import locked, start, stage, finish, claim
from recovery_engine import Budget, RecoveryError, pinned_json

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux flock required')


def module():
    import recovery_program_native
    return recovery_program_native


def context(e, binding, fd, **kwargs):
    return module().MainNativeExecutionContext(e.owner, e.request, e.root,
        binding_pin=binding, lock_fd=fd, budget=kwargs.pop('budget', Budget(120000)), **kwargs)


def started(e, fd):
    saved, binding = bind(e, fd)
    epoch = start(e.case, e.claim, fd)
    return saved, binding, epoch


def publish(e, saved, fd):
    return stage(e.case, saved, fd, target_pin=write(e.claim/'target.json', e.candidate),
        capture_pins={'source57': write(e.claim/'capture.json', e.capture)}, switch_result_pin=e.switch)


def invocation(e, name='native-000.json', **changes):
    value = dict(schemaVersion='RecoveryDataInvocation/v1', operationId=e.request['operationId'],
        action='RESTORE', argvSha256='a'*64, mutation=True, startedAt='2026-11-08T00:00:00Z',
        finishedAt=None, actualExitCode=None, state='TERMINAL_UNKNOWN')
    value.update(changes)
    return write(e.root/name, value)


def terminal(reference, **changes):
    value = pinned_json(reference)
    value.update(finishedAt='2026-11-08T00:00:01Z', actualExitCode=0, state='SUCCEEDED')
    value.update(changes)
    return write(Path(reference['path']), value)


def test_preparation_binds_full_owner_before_use_and_preserves_originals(execution):
    e = execution
    before = {p['path']: Path(p['path']).read_bytes() for p in (e.owner_pin, e.request_pin, e.reservation)}
    budget = Budget(120000)
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd, budget=budget) as ctx:
            view = ctx.preparation(e.owner)
            assert ctx.budget is budget and view.budget is budget
            assert view.configuration == e.owner and view.phase == 'PREPARATION'
            assert view.evidence['bindingPin'] == binding
            assert view.evidence['epoch']['state'] == 'REPLACING'
            view.guard()
    assert all(Path(p).read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('field', ['unrelated', 'other-target', 'database', 'credential', 'runtime'])
def test_preparation_rejects_any_full_configuration_change(execution, field):
    e = execution
    changed = deepcopy(e.owner)
    if field == 'unrelated': changed['unrelated'] = {}
    elif field == 'other-target': changed['targets']['other'] = {}
    else: changed['targets']['target57'][{'credential':'secrets','runtime':'dataRoot'}.get(field, field)] = 'wrong'
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_CONFIGURATION_CHANGED'):
                ctx.preparation(changed)


@pytest.mark.parametrize('state', ['READY', 'foreign', 'FAILED_RETAINED', 'SUCCEEDED'])
def test_constructor_requires_this_operation_replacing(execution, state):
    e = execution
    with locked(e.case) as fd:
        saved, binding = bind(e, fd)
        if state == 'foreign': start(e.case, claim(e.case, 'other'), fd, operation='other')
        elif state != 'READY':
            epoch = start(e.case, e.claim, fd)
            generation = publish(e, saved, fd)
            finish(e.case, e.claim, epoch, generation, fd, state=state)
        with pytest.raises((RecoveryError, ValueError), match='PROGRAM_'):
            context(e, binding, fd)


def test_stage_is_monotonic_and_restore_requires_exact_runtime_configuration(execution):
    e = execution
    with locked(e.case) as fd:
        saved, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_STAGE_REQUIRED'):
                ctx.restore(e.owner)
            generation = publish(e, saved, fd)
            ctx.stage(generation)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_PHASE_CHANGED'):
                prep.guard()
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_PHASE_CHANGED'):
                ctx.preparation(e.owner)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_STAGE_ALREADY_BOUND'):
                ctx.stage(generation)
            with pytest.raises(RecoveryError, match='PROGRAM_EXECUTION_RUNTIME_INVALID'):
                ctx.restore(e.owner)
            (e.claim/'runtime').mkdir(mode=0o700)
            owner, _ = resolve(e, binding, fd, generation_pin=generation, runtime=True)
            restore = ctx.restore(owner)
            restore.guard()
            assert restore.phase == 'RESTORE' and restore.evidence['generationPin'] == generation
            assert restore.configuration['targets']['target57']['dataRoot'] == str(e.claim/'runtime')
            wrong = deepcopy(owner); wrong['unrelated'] = {}
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_CONFIGURATION_CHANGED'):
                ctx.restore(wrong)


def test_published_generation_without_stage_invalidates_old_view(execution):
    e = execution
    with locked(e.case) as fd:
        saved, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            publish(e, saved, fd)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_STAGE_REQUIRED'):
                prep.guard()


@pytest.mark.parametrize('file', ['configuration.json', 'request.json', 'resource-reservation.json',
    'program-context.json', 'program-execution-binding.json', 'target.json', 'active.json'])
def test_metadata_changes_after_admission_fail_even_when_original_bytes_restored(execution, file):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            if file.startswith('program-'): path = e.claim/file
            elif file == 'target.json': path = e.case['root']/file
            elif file == 'active.json': path = e.case['root']/'resource-host'/file
            else: path = e.root/file
            raw = path.read_bytes(); path.write_bytes(b'{}'); path.write_bytes(raw)
            with pytest.raises((RecoveryError, ValueError), match='CHANGED|DRIFT'):
                prep.guard()


@pytest.mark.parametrize('change', ['released', 'replaced', 'closed', 'wrong-file'])
def test_each_view_guard_requires_original_physical_exclusive_lock(execution, change):
    import fcntl
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            if change == 'released': fcntl.flock(fd, fcntl.LOCK_UN)
            elif change == 'replaced':
                path = Path(e.case['epoch']['sourceLockPath']); path.unlink(); path.write_bytes(b'')
                path.chmod(0o600)
            else:
                # Replace the fd slot so the context cannot rely on its integer.
                path = e.case['root']/('wrong.lock' if change == 'wrong-file' else 'empty')
                other = os.open(path, os.O_RDWR|os.O_CREAT, 0o600)
                try: os.dup2(other, fd)
                finally: os.close(other)
            with pytest.raises((RecoveryError, ValueError, OSError), match='BACKUP_EPOCH_|CHANGED|DRIFT'):
                prep.guard()


def test_epoch_completion_or_new_event_blocks_all_old_commands(execution):
    e = execution
    with locked(e.case) as fd:
        saved, binding, epoch = started(e, fd)
        with context(e, binding, fd) as ctx:
            generation = publish(e, saved, fd); ctx.stage(generation)
            (e.claim/'runtime').mkdir(mode=0o700)
            owner, _ = resolve(e, binding, fd, generation_pin=generation, runtime=True)
            view = ctx.restore(owner)
            finish(e.case, e.claim, epoch, generation, fd)
            with pytest.raises((RecoveryError, ValueError), match='CHANGED|DRIFT|EPOCH'):
                view.guard()


def test_caller_cannot_mutate_fixed_input_or_returned_configuration(execution):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        original = deepcopy(e.owner)
        with context(e, binding, fd) as ctx:
            view = ctx.preparation(e.owner)
            view.configuration['unrelated'] = {}
            view.evidence['bindingPin']['sha256'] = '0'*64
            e.owner['unrelated'] = {}; e.request['operationId'] = 'changed'
            binding['sha256'] = '0'*64
            view.guard()
            assert view.configuration == original
            assert view.evidence['bindingPin']['sha256'] != '0'*64


@pytest.mark.parametrize('entry', ['constructor', 'view', 'guard', 'stage', 'begin'])
def test_same_budget_is_never_reset_or_swallowed(execution, entry):
    e = execution; budget = Budget(120000)
    with locked(e.case) as fd:
        saved, binding, _ = started(e, fd)
        if entry == 'constructor':
            budget.deadline = 0
            with pytest.raises(RecoveryError, match='DEADLINE_EXCEEDED'):
                context(e, binding, fd, budget=budget)
            return
        with context(e, binding, fd, budget=budget) as ctx:
            prep = ctx.preparation(e.owner)
            if entry == 'stage': generation = publish(e, saved, fd)
            budget.deadline = 0
            with pytest.raises(RecoveryError, match='DEADLINE_EXCEEDED'):
                if entry == 'view': ctx.preparation(e.owner)
                elif entry == 'guard': prep.guard()
                elif entry == 'stage': ctx.stage(generation)
                else: ctx.begin_invocation(prep, invocation(e))


def test_external_guard_failure_propagates_and_partial_construction_closes_leases(execution):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        count = len(os.listdir('/proc/self/fd'))
        calls = 0
        def rejected():
            nonlocal calls
            calls += 1
            if calls > 15: raise TimeoutError('explicit guard failure')
        with pytest.raises(TimeoutError, match='explicit guard failure'):
            context(e, binding, fd, guard=rejected)
        assert len(os.listdir('/proc/self/fd')) == count


def test_native_evidence_combines_phases_and_pending_unknown_without_losing_last_exit(execution):
    e = execution
    with locked(e.case) as fd:
        saved, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            first = invocation(e, mutation=False)
            token = ctx.begin_invocation(prep, first)
            pending = ctx.snapshot()
            assert pending['terminalUnknown'] and pending['lastExitCode'] is None
            first_done = terminal(first); ctx.finish_invocation(token, first_done)
            assert ctx.snapshot()['lastExitCode'] == 0
            generation = publish(e, saved, fd); ctx.stage(generation)
            (e.claim/'runtime').mkdir(mode=0o700)
            owner, _ = resolve(e, binding, fd, generation_pin=generation, runtime=True)
            restore = ctx.restore(owner)
            second = invocation(e, 'native-001.json')
            second_token = ctx.begin_invocation(restore, second)
            assert ctx.snapshot()['lastExitCode'] is None
            second_done = terminal(second, state='FAILED_RETAINED', actualExitCode=2)
            ctx.finish_invocation(second_token, second_done)
            summary = ctx.snapshot()
            assert summary['originalResultPins'] == [first_done, second_done]
            assert summary['mutationDispatched'] is True and summary['terminalUnknown'] is False
            assert summary['lastExitCode'] == 2
            assert [row['phase'] for row in summary['invocations']] == ['PREPARATION', 'RESTORE']
            summary['originalResultPins'].clear()
            assert len(ctx.snapshot()['originalResultPins']) == 2


@pytest.mark.parametrize('field', ['operationId', 'action', 'argvSha256', 'mutation', 'startedAt', 'path', 'exit'])
def test_terminal_cannot_replace_unrelated_invocation(execution, field):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            reference = invocation(e)
            token = ctx.begin_invocation(prep, reference)
            changes = {'mutation':False} if field == 'mutation' else {field:'wrong'}
            if field == 'exit': changes = dict(actualExitCode=None)
            if field == 'path':
                other = invocation(e, 'other.json'); result = terminal(other)
            else: result = terminal(reference, **changes)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_EVIDENCE_'):
                ctx.finish_invocation(token, result)
            assert ctx.snapshot()['terminalUnknown'] is True


def test_finished_evidence_cannot_be_overwritten_or_closed_twice(execution):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            reference = invocation(e); token = ctx.begin_invocation(prep, reference)
            result = terminal(reference); ctx.finish_invocation(token, result)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_EVIDENCE_ALREADY_FINISHED'):
                ctx.finish_invocation(token, result)
            Path(result['path']).write_bytes(b'{}')
            with pytest.raises(RecoveryError, match='PROGRAM_DOCUMENT_CHANGED'):
                ctx.snapshot()


def test_timeout_or_lost_execution_lock_does_not_discard_terminal_evidence(execution):
    import fcntl
    e = execution; budget = Budget(120000)
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd, budget=budget) as ctx:
            reference = invocation(e)
            token = ctx.begin_invocation(ctx.preparation(e.owner), reference)
            budget.deadline = 0; fcntl.flock(fd, fcntl.LOCK_UN)
            result = terminal(reference, state='TERMINAL_UNKNOWN', actualExitCode=-9)
            ctx.finish_invocation(token, result)
            summary = ctx.snapshot()
            assert summary['terminalUnknown'] and summary['mutationDispatched']
            assert summary['lastExitCode'] == -9 and summary['originalResultPins'] == [result]


@pytest.mark.parametrize('problem', ['foreign-operation', 'foreign-path', 'duplicate', 'foreign-view'])
def test_begin_rejects_unbound_or_duplicated_evidence(execution, problem):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            reference = invocation(e, operationId='other') if problem == 'foreign-operation' else invocation(e)
            if problem == 'foreign-path': reference = write(e.case['root']/'external.json', pinned_json(reference))
            if problem == 'duplicate': ctx.begin_invocation(prep, reference)
            if problem == 'foreign-view': prep = object()
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_'):
                ctx.begin_invocation(prep, reference)


def test_close_is_idempotent_releases_resources_and_disables_execution(execution):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        count = len(os.listdir('/proc/self/fd'))
        ctx = context(e, binding, fd); prep = ctx.preparation(e.owner)
        ctx.close(); ctx.close()
        assert len(os.listdir('/proc/self/fd')) == count
        with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_CLOSED'):
            prep.guard()
        assert ctx.snapshot()['originalResultPins'] == []


@pytest.mark.parametrize('state', ['pending', 'TERMINAL_UNKNOWN'])
def test_unsettled_invocation_blocks_next_dispatch_but_not_its_own_guard_or_evidence(execution, state):
    e = execution
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            prep = ctx.preparation(e.owner)
            first = invocation(e)
            token = ctx.begin_invocation(prep, first)
            if state != 'pending':
                ctx.finish_invocation(token, terminal(first, state=state, actualExitCode=-9))
            prep.guard()  # A command's post-dispatch guard must not self-lock.
            second = invocation(e, 'next.json')
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_INVOCATION_UNSETTLED'):
                ctx.begin_invocation(prep, second)
            assert len(ctx.snapshot()['invocations']) == 1
            assert ctx.snapshot()['terminalUnknown'] is True
            if state == 'pending':
                result = terminal(first)
                ctx.finish_invocation(token, result)
                assert ctx.snapshot()['originalResultPins'] == [result]
                assert ctx.snapshot()['terminalUnknown'] is False


@pytest.mark.parametrize('state', ['pending', 'TERMINAL_UNKNOWN', 'FAILED_RETAINED'])
def test_stage_requires_every_invocation_succeeded_without_discarding_failures(execution, state):
    e = execution
    with locked(e.case) as fd:
        saved, binding, _ = started(e, fd)
        with context(e, binding, fd) as ctx:
            first = invocation(e)
            token = ctx.begin_invocation(ctx.preparation(e.owner), first)
            result = None
            if state != 'pending':
                result = terminal(first, state=state, actualExitCode=2)
                ctx.finish_invocation(token, result)
            generation = publish(e, saved, fd)
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_INVOCATION_PENDING|PROGRAM_NATIVE_INVOCATION_NOT_SUCCEEDED'):
                ctx.stage(generation)
            assert ctx.phase == 'PREPARATION' and ctx.generation_pin is None
            summary = ctx.snapshot()
            assert summary['mutationDispatched']
            if result is not None:
                assert summary['originalResultPins'] == [result]
                assert summary['lastExitCode'] == 2
                assert summary['terminalUnknown'] == (state == 'TERMINAL_UNKNOWN')
            else:
                assert summary['terminalUnknown']
                result = terminal(first)
                ctx.finish_invocation(token, result)
                assert ctx.snapshot()['originalResultPins'] == [result]


def test_context_entry_failure_releases_all_leases_without_waiting_for_exit(execution):
    e = execution; budget = Budget(120000)
    with locked(e.case) as fd:
        _, binding, _ = started(e, fd)
        before = len(os.listdir('/proc/self/fd'))
        ctx = context(e, binding, fd, budget=budget)
        assert len(os.listdir('/proc/self/fd')) > before
        budget.deadline = 0
        try:
            with pytest.raises(RecoveryError, match='DEADLINE_EXCEEDED'):
                with ctx:
                    pytest.fail('expired context must not enter')
            assert len(os.listdir('/proc/self/fd')) == before
        finally:
            ctx.close()  # Test cleanup also runs for the real leaking RED.
