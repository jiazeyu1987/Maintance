"""Real Linux invocation integration at the admitted constructor boundary.

Private owner/request/reservation/epoch files, flock and native constructors are
real. Commands and formal stream_import run actual local subprocesses. The SQL
transport consumes stdin into a test file; it does not claim database restoration
or Docker readiness. The constructor always stops explicitly at its first DB
method instead of manufacturing a successful database identity.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from test_recovery_program_native_constructor import constructor_case, DatabaseBoundary
from test_recovery_program_execution import bind, resolve
from test_recovery_program_activation import locked, start, stage
from test_recovery_program_generation import write
from recovery_engine import Budget, RecoveryError, pin, pinned_json
from recovery_program_native import MainNativeExecutionContext
from recovery_data import NativeData
import recovery_data as data_module
import recovery_minimal_runtime as runtime

ROOT = Path(__file__).resolve().parents[2]
RESTORE_ACTIONS = ('RESTORE', 'DATABASE_FULL', 'DATABASE_INCREMENTAL', 'OBJECT_CHAIN_PHYSICAL',
                   'OBJECT_FULL', 'OBJECT_INCREMENTAL', 'CONSISTENCY', 'START_APPLICATION')
pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux invocation/flock contracts')


class InvocationCase:
    def __init__(self, root, seam, *, formal_directory=None):
        formal = ROOT/'ops/backup_engine/formal' if formal_directory is None else formal_directory
        self.e = constructor_case(root, formal, seam)
        self.seam = seam
        self.sequence = 0

    @contextmanager
    def opened(self):
        e = self.e
        with locked(e.case) as fd:
            saved, binding = bind(e, fd)
            start(e.case, e.claim, fd)
            with MainNativeExecutionContext(e.owner, e.request, e.root, binding_pin=binding,
                    lock_fd=fd, budget=Budget(120000)) as ctx:
                self.fd, self.saved, self.binding, self.ctx = fd, saved, binding, ctx
                self.configuration = deepcopy(e.owner)
                self.view = ctx.preparation(self.configuration)
                yield self

    def restore(self):
        e = self.e
        generation = stage(e.case, self.saved, self.fd, target_pin=write(e.claim/'target.json', e.candidate),
            capture_pins={'source57':write(e.claim/'capture.json', e.capture)}, switch_result_pin=e.switch)
        self.ctx.stage(generation)
        (e.claim/'runtime').mkdir(mode=0o700)
        self.configuration, _ = resolve(e, self.binding, self.fd, generation_pin=generation, runtime=True)
        self.view = self.ctx.restore(self.configuration)

    def at_native(self, callback, *, legacy=False):
        """Run a real method inside __init__, then refuse any DB identity claim."""
        e = self.e
        configuration = deepcopy(self.configuration)
        if legacy:
            configuration.pop('targetProgramPolicies')
        target = deepcopy(configuration['targets']['target57'])
        self.sequence += 1
        log = e.root/('invocations-%02d' % self.sequence)
        log.mkdir(mode=0o700)
        seen = []

        class Boundary(runtime.MinimalData):
            def database_uuid(native):
                seen.append(native)
                callback(native)
                raise DatabaseBoundary('invocation test stops before database identity')

        kwargs = {} if legacy else {'native_context':self.view}
        with pytest.raises(DatabaseBoundary, match='invocation test stops before database identity'):
            Boundary(configuration, deepcopy(e.request), None, {}, e.chain, target, log, [], **kwargs)
        assert len(seen) == 1
        return seen[0]


@pytest.fixture
def invocation_case(tmp_path, monkeypatch):
    return InvocationCase(tmp_path, monkeypatch)


def command(marker=None, *, code=0, delay=0):
    script = 'import pathlib,sys,time;'
    if delay: script += 'time.sleep('+repr(delay)+');'
    if marker is not None: script += 'pathlib.Path('+repr(str(marker))+').write_bytes(b"dispatched");'
    script += 'sys.stdout.write("actual-child");sys.exit('+repr(code)+')'
    return [sys.executable, '-B', '-c', script]


def observe_popen(seam, callback):
    """Observe dispatch and pass through to the real OS process, never fake it."""
    real = subprocess.Popen
    def observed(argv, **kwargs):
        return callback(real, argv, kwargs)
    seam.setattr(data_module, 'subprocess', SimpleNamespace(Popen=observed,
        PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired))


def sql_transport(native, destination, *, code=0, unavailable=False):
    class PipeTransport:
        _password = 'test-only-stdin-secret'
        def _command(self, _program, _arguments):
            shell = 'read -r ignored; cat > '+shlex.quote(str(destination))+'; exit '+str(code)
            return (['/no-such-invocation-executable'] if unavailable else []) + ['sh', '-ec', shell]
    native.mysql = PipeTransport()
    # Only the external Docker/database readiness boundary is replaced in this
    # local transport test. Actual ctx/native guards and stream_import stay live.
    native.bound = lambda **_: native.guard()
    sql = native.root/'input.sql'
    sql.write_bytes(b'SELECT 1;\nSELECT 2;\n'); sql.chmod(0o600)
    return sql, hashlib.sha256(sql.read_bytes()).hexdigest()


def test_preparation_and_restore_commands_share_actual_invocation_ledger(invocation_case):
    with invocation_case.opened() as c:
        def preparation(native):
            assert native.command(command(), mutation=False) == b'actual-child'
        first = c.at_native(preparation)
        c.restore()
        def restore(native):
            native.request['action'] = 'DATABASE_FULL'
            assert native.command(command(), mutation=True) == b'actual-child'
        second = c.at_native(restore)
        proof = c.ctx.snapshot()
        assert [row['phase'] for row in proof['invocations']] == ['PREPARATION', 'RESTORE']
        assert proof['originalResultPins'] == first.original_pins+second.original_pins
        assert [row['intentObservation']['action'] for row in proof['invocations']] == ['RESTORE', 'DATABASE_FULL']
        assert proof['mutationDispatched'] and not proof['terminalUnknown'] and proof['lastExitCode'] == 0


def test_command_is_registered_before_the_actual_popen(invocation_case):
    with invocation_case.opened() as c:
        observed = []
        def before(real, argv, kwargs):
            pending = c.ctx.snapshot()['invocations']
            assert len(pending) == 1 and pending[0]['terminalPin'] is None
            intent = pinned_json(pending[0]['intentPinAtDispatch'])
            assert intent == pending[0]['intentObservation'] and intent['actualExitCode'] is None
            observed.append(intent)
            return real(argv, **kwargs)
        observe_popen(c.seam, before)
        c.at_native(lambda native: native.command(command(), mutation=False))
        assert len(observed) == 1 and c.ctx.snapshot()['lastExitCode'] == 0


@pytest.mark.parametrize('action', RESTORE_ACTIONS)
def test_restore_permits_only_the_documented_finite_native_actions(invocation_case, action):
    with invocation_case.opened() as c:
        c.restore()
        def execute(native):
            native.request['action'] = action
            native.command(command(), mutation=action != 'CONSISTENCY')
        c.at_native(execute)
        rows = c.ctx.snapshot()['invocations']
        assert len(rows) == 1 and rows[0]['intentObservation']['action'] == action


@pytest.mark.parametrize('phase,action', [('PREPARATION','DATABASE_FULL'), ('PREPARATION','START_APPLICATION'),
    ('RESTORE','ARBITRARY_SHELL'), ('RESTORE','BACKUP'), ('RESTORE','restore')])
def test_invalid_action_never_reaches_a_real_process(invocation_case, phase, action):
    with invocation_case.opened() as c:
        if phase == 'RESTORE': c.restore()
        marker = c.e.root/'forbidden-dispatch'
        def execute(native):
            native.request['action'] = action
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_'):
                native.command(command(marker), mutation=True)
        c.at_native(execute)
        assert not marker.exists() and c.ctx.snapshot()['invocations'] == []


def test_operation_identity_comes_from_original_not_mutable_action_request(invocation_case):
    with invocation_case.opened() as c:
        def execute(native):
            native.request['operationId'] = 'not-the-original-operation'
            native.command(command())
        c.at_native(execute)
        proof = c.ctx.snapshot()
        assert proof['operationId'] == c.e.request['operationId']
        assert len(proof['invocations']) == 1
        assert proof['invocations'][0]['intentObservation']['operationId'] == c.e.request['operationId']


def test_changed_native_original_is_rejected_before_dispatch(invocation_case):
    with invocation_case.opened() as c:
        marker = c.e.root/'wrong-original'
        def execute(native):
            native.original = dict(native.original, operationId='foreign')
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_REQUEST_CHANGED'):
                native.command(command(marker), mutation=True)
        c.at_native(execute)
        assert not marker.exists() and c.ctx.snapshot()['invocations'] == []


@pytest.mark.parametrize('change', ['unlock', 'expire', 'close'])
def test_post_dispatch_guard_failure_still_records_actual_exit_and_blocks_next(invocation_case, change):
    import fcntl
    with invocation_case.opened() as c:
        marker = c.e.root/'first-dispatched'
        next_marker = c.e.root/'next-not-dispatched'
        def before(real, argv, kwargs):
            process = real(argv, **kwargs)
            communicate = process.communicate
            def completed(*args, **options):
                answer = communicate(*args, **options)
                assert process.returncode == 0
                if change == 'unlock': fcntl.flock(c.fd, fcntl.LOCK_UN)
                elif change == 'expire': c.ctx.budget.deadline = 0
                else: c.ctx.close()
                return answer
            process.communicate = completed
            return process
        observe_popen(c.seam, before)
        def execute(native):
            with pytest.raises((RecoveryError, ValueError), match='LOCK|DEADLINE|CLOSED'):
                native.command(command(marker), mutation=True)
            proof = c.ctx.snapshot()
            assert len(proof['invocations']) == 1 and proof['lastExitCode'] == 0
            assert proof['invocations'][0]['terminalObservation']['actualExitCode'] == 0
            with pytest.raises((RecoveryError, ValueError), match='LOCK|DEADLINE|CLOSED'):
                native.command(command(next_marker), mutation=True)
        c.at_native(execute)
        assert marker.read_bytes() == b'dispatched' and not next_marker.exists()


def test_phase_change_blocks_existing_native_before_its_next_dispatch(invocation_case):
    with invocation_case.opened() as c:
        marker = c.e.root/'old-phase'
        def execute(native):
            native.command(command())
            c.restore()
            with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_PHASE_CHANGED'):
                native.command(command(marker), mutation=True)
        c.at_native(execute)
        assert not marker.exists() and len(c.ctx.snapshot()['invocations']) == 1


def test_actual_timeout_retains_killed_child_and_blocks_another_dispatch(invocation_case):
    with invocation_case.opened() as c:
        marker = c.e.root/'timed-out-not-reached'
        def execute(native):
            c.ctx.budget.deadline = time.monotonic()+2
            with pytest.raises(RecoveryError, match='NATIVE_EXECUTOR_TIMEOUT'):
                native.command(command(marker, delay=30), mutation=True)
            proof = c.ctx.snapshot()
            assert len(proof['invocations']) == 1 and proof['lastExitCode'] == -9
            assert proof['terminalUnknown'] is True
            with pytest.raises(RecoveryError, match='DEADLINE_EXCEEDED'):
                native.command(command(marker), mutation=True)
        c.at_native(execute)
        assert not marker.exists()


@pytest.mark.parametrize('path', ['command', 'sql'])
def test_dispatch_failure_retains_unknown_intent_without_inventing_a_child_exit(invocation_case, path):
    with invocation_case.opened() as c:
        if path == 'sql': c.restore()
        def execute(native):
            if path == 'command':
                with pytest.raises(OSError): native.command(['/no-such-invocation-executable'], mutation=True)
            else:
                native.request['action'] = 'DATABASE_FULL'
                sql, checksum = sql_transport(native, native.root/'not-written', unavailable=True)
                with pytest.raises(Exception, match='FORMAL_SQL_IMPORT_UNAVAILABLE'):
                    NativeData.import_sql(native, sql, checksum)
            proof = c.ctx.snapshot()
            assert len(proof['invocations']) == 1 and proof['terminalUnknown']
            assert proof['lastExitCode'] is None and proof['originalResultPins']
        c.at_native(execute)


def test_program_sql_importer_v2_is_registered_before_actual_stream_process(invocation_case):
    with invocation_case.opened() as c:
        c.restore()
        observed = []
        def before(real, argv, kwargs):
            rows = c.ctx.snapshot()['invocations']
            assert len(rows) == 1 and rows[0]['terminalPin'] is None
            value = pinned_json(rows[0]['intentPinAtDispatch'])
            assert value['schemaVersion'] == 'RecoverySqlImporter/v2'
            assert value['operationId'] == c.e.request['operationId'] and value['action'] == 'DATABASE_FULL'
            assert value['mutation'] is True and value['finishedAt'] is None
            observed.append(value)
            return real(argv, **kwargs)
        observe_popen(c.seam, before)
        def execute(native):
            native.request['action'] = 'DATABASE_FULL'
            destination = native.root/'actual-stdin'
            sql, checksum = sql_transport(native, destination)
            NativeData.import_sql(native, sql, checksum)
            assert destination.read_bytes() == sql.read_bytes()
        native = c.at_native(execute)
        proof = c.ctx.snapshot()
        assert len(observed) == 1 and proof['originalResultPins'] == native.original_pins
        assert proof['lastExitCode'] == 0 and not proof['terminalUnknown']


def test_sql_terminal_is_closed_before_post_stream_bound_dispatches_real_native_command(invocation_case):
    with invocation_case.opened() as c:
        c.restore()
        at_dispatch = []
        def before(real, argv, kwargs):
            at_dispatch.append(c.ctx.snapshot())
            return real(argv, **kwargs)
        observe_popen(c.seam, before)
        def execute(native):
            native.request['action'] = 'DATABASE_FULL'
            sql, checksum = sql_transport(native, native.root/'actual-stdin')
            observations = []
            def bound(**_):
                native.guard()
                marker = native.root/('bound-%d' % len(observations))
                assert native.command(command(marker), mutation=False) == b'actual-child'
                observations.append(marker)
            # MAIN's actual bound performs native commands before and after the
            # stream. These two real local commands exercise that nesting;
            # leaving the SQL row pending until import_sql's final finally
            # would prohibit the post-stream command despite SQL success.
            native.bound = bound
            NativeData.import_sql(native, sql, checksum)
            assert len(observations) == 2 and all(p.read_bytes() == b'dispatched' for p in observations)
        c.at_native(execute)
        rows = c.ctx.snapshot()['invocations']
        assert [row['intentObservation']['schemaVersion'] for row in rows] == [
            'RecoveryDataInvocation/v1', 'RecoverySqlImporter/v2', 'RecoveryDataInvocation/v1']
        assert len(at_dispatch) == 3
        assert at_dispatch[2]['invocations'][1]['terminalObservation']['state'] == 'SUCCEEDED'
        assert at_dispatch[2]['invocations'][1]['terminalPin'] is not None
        assert all(row['terminalObservation']['actualExitCode'] == 0 for row in rows)


@pytest.mark.parametrize('scenario', ['confirmed-failure', 'guard-after-import'])
def test_actual_sql_process_result_survives_failure_or_lost_guard(invocation_case, scenario):
    with invocation_case.opened() as c:
        c.restore()
        def execute(native):
            native.request['action'] = 'DATABASE_INCREMENTAL'
            sql, checksum = sql_transport(native, native.root/'actual-stdin', code=7 if scenario=='confirmed-failure' else 0)
            if scenario == 'guard-after-import':
                calls = []
                def bound(**_):
                    calls.append(True)
                    if len(calls) == 2: c.ctx.close()
                    native.guard()
                native.bound = bound
            with pytest.raises(Exception, match='FORMAL_SQL_IMPORT_FAILED|PROGRAM_NATIVE_CLOSED'):
                NativeData.import_sql(native, sql, checksum)
            proof = c.ctx.snapshot()
            assert len(proof['invocations']) == 1
            assert proof['lastExitCode'] == (7 if scenario=='confirmed-failure' else 0)
            assert proof['invocations'][0]['terminalObservation']['schemaVersion'] == 'RecoverySqlImporter/v2'
            assert proof['terminalUnknown'] is False
        c.at_native(execute)


def test_legacy_commands_and_sql_keep_existing_v1_without_program_ledger(invocation_case):
    with invocation_case.opened() as c:
        def execute(native):
            assert native.native_context is None
            native.command(command())
            sql, checksum = sql_transport(native, native.root/'legacy-stdin')
            NativeData.import_sql(native, sql, checksum)
        native = c.at_native(execute, legacy=True)
        records = [pinned_json(reference) for reference in native.original_pins]
        assert [row['schemaVersion'] for row in records] == ['RecoveryDataInvocation/v1', 'RecoverySqlImporter/v1']
        assert 'operationId' not in records[1] and 'action' not in records[1] and 'mutation' not in records[1]
        assert c.ctx.snapshot()['invocations'] == []


def test_program_context_rejects_unbound_legacy_sql_importer_evidence(invocation_case):
    with invocation_case.opened() as c:
        reference = write(c.e.root/'legacy-importer.json', dict(schemaVersion='RecoverySqlImporter/v1',
            argvSha256='a'*64, sqlPin=c.e.owner_pin, startedAt='2026-11-08T00:00:00Z',
            actualExitCode=None, state='TERMINAL_UNKNOWN'))
        with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_EVIDENCE_INTENT_INVALID'):
            c.ctx.begin_invocation(c.view, reference)


def test_sql_terminal_cannot_change_the_dispatched_sql_pin(invocation_case):
    with invocation_case.opened() as c:
        c.restore()
        sql = c.e.root/'actual-sql-input'; sql.write_bytes(b'SELECT 1;\n'); sql.chmod(0o600)
        other = c.e.root/'other-sql-input'; other.write_bytes(b'SELECT 2;\n'); other.chmod(0o600)
        value = dict(schemaVersion='RecoverySqlImporter/v2', operationId=c.e.request['operationId'],
            action='DATABASE_FULL', argvSha256='a'*64, mutation=True, sqlPin=pin(sql),
            startedAt='2026-11-08T00:00:00Z', finishedAt=None, actualExitCode=None, state='TERMINAL_UNKNOWN')
        intent = write(c.e.root/'importer-identity.json', value)
        token = c.ctx.begin_invocation(c.view, intent)
        # The process is only an OS-exit fixture, not a claimed SQL restore.
        process = subprocess.run([sys.executable, '-B', '-c', 'pass'], check=False)
        assert process.returncode == 0
        terminal = write(Path(intent['path']), dict(value, sqlPin=pin(other),
            finishedAt='2026-11-08T00:00:01Z', actualExitCode=process.returncode, state='SUCCEEDED'))
        with pytest.raises(RecoveryError, match='PROGRAM_NATIVE_EVIDENCE_IDENTITY_INVALID'):
            c.ctx.finish_invocation(token, terminal)
        assert c.ctx.snapshot()['terminalUnknown'] is True
