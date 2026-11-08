"""Actual MAIN producer -> runtime -> worker -> historical-consumer contracts.

Private source history, owner/admission/reservation, physical flock, epoch,
program import/switch/derivation, context and custody use their production
implementations. Every native invocation below runs NativeData.command with a
real local Python subprocess. SQL staging/gzip expansion, binary-log rewrite,
NativeData.import_sql, formal stream_import and runtime cleanup also run for
real. No result, native snapshot, custody snapshot or replacement receipt is
manufactured by this test.

The inherited finite SQL/Docker/object/mount/firewall protocol models remain
explicit external semantic boundaries. A Python stdin consumer records SQL
bytes; it is not a database. These component tests have
actualBusinessRestore=False and do not establish server or business acceptance.
"""
from copy import deepcopy
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_recovery_program_generation import case  # Independent fresh pytest fixture discovery.
from test_recovery_program_restore import restore_case, assert_inputs_unchanged
from recovery_data import NativeData, stage_private_sql
from recovery_engine import RecoveryError, canonical, digest, pin, pinned_json, require, utc, write
from recovery_program_native import MainNativeExecutionContext
import recovery_backup_epoch as epoch
import recovery_data as data_module
import recovery_minimal_runtime as runtime
import recovery_minimal_worker as worker
import recovery_program_evidence as historical


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='real Linux flock/context, SQL staging/cleanup and subprocess contracts')
ECHO = 'import base64,sys;sys.stdout.buffer.write(base64.b64decode(sys.argv[1]))'
SQL_CONSUMER = r'''
import os, pathlib, sys
destination = pathlib.Path(sys.argv[1])
password = sys.stdin.buffer.readline()
assert password.endswith(b'\n') and len(password) > 1
with destination.open('xb') as output:
    os.chmod(destination, 0o600)
    while True:
        raw = sys.stdin.buffer.read(65536)
        if not raw:
            break
        output.write(raw)
    output.flush()
    os.fsync(output.fileno())
'''


@pytest.fixture
def producer_case(restore_case, monkeypatch):
    """Extend only external protocols; keep all producer/result entry points real."""
    h = restore_case
    h.actualBusinessRestore = False
    h.scenario = None
    h.processes, h.sql_inputs, h.sql_received = [], [], []
    h.fixed_before_ready = {}
    h.current_dispatch = None
    h.post_guard_triggered = False
    h.output = h.root/'worker-result.json'
    # This is the original supervisor admission input, not a result envelope.
    h.operation_pin = write(h.root/'operation.json', dict(operationId=h.request['operationId'],
        requestPin=h.request_pin, configurationSha256=digest(h.owner), startedAt=utc()))
    original_type = h.native_type

    class ActualProcessProtocol(original_type, NativeData):
        """Finite external semantics; actual admitted native/SQL execution evidence."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.policy['maxExpandedBytes'] = 1024*1024
            formal = Path(os.environ.get('RECOVERY_TEST_FORMAL_DIRECTORY',
                str(ROOT/'ops/backup_engine/formal'))).resolve(strict=True)
            self.modules = runtime.modules_from(str(formal))
            assert all(Path(module.__file__).resolve().parent == formal for module in self.modules.values())
            native = self

            class LocalSqlTransport:
                # Read the pinned fixture secret; never serialize it in argv/evidence.
                _password = Path(native.config['secrets']['mysql']['MYSQL_ROOT_PASSWORD']['path']).read_text(
                    encoding='utf-8')

                def query(self, statement, *, mutation=False):
                    return native.query(statement, mutation=mutation).decode('utf-8').strip()

                def _command(self, _program, _arguments):
                    destination = native.root/'received-sql.protocol.bin'
                    h.sql_received.append(destination)
                    # stream_import retains its real shell acknowledgement and
                    # deadlines; the SQL client is this actual Python process.
                    return ['sh', '-ec', shlex.join([sys.executable, '-B', '-c',
                        SQL_CONSUMER, str(destination)])]

            self.mysql = LocalSqlTransport()

        def _invoke(self, kind, arguments, callback, mutation):
            self.guard()
            h.events.append((kind, self.native_context.phase, deepcopy(arguments), mutation))
            # The callback computes only the explicitly declared finite external
            # protocol state/reply. It writes no invocation/result evidence.
            value = callback()
            raw = canonical(value) if type(value) is dict else value
            assert type(raw) is bytes
            previous = h.current_dispatch
            h.current_dispatch = (self, kind, deepcopy(arguments), mutation)
            try:
                observed = NativeData.command(self, [sys.executable, '-B', '-c', ECHO,
                    base64.b64encode(raw).decode('ascii')], mutation=mutation)
            finally:
                h.current_dispatch = previous
            return json.loads(observed) if type(value) is dict else observed

        def database_uuid(self):
            if h.scenario == 'constructor-readonly':
                raw = self._invoke('sql', 'SELECT @@server_uuid;', lambda:b'invalid-uuid\n', False)
            else:
                raw = self.query('SELECT @@server_uuid;')
            value = raw.decode('ascii').strip()
            require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value),
                'TARGET_DATABASE_UUID_INVALID')
            self.db_uuid = value
            return value

        def bound(self, **_):
            # Keep actual custody verification and original guard. Only the
            # external SQL/object readiness semantics are the inherited model.
            return super().bound()

        def import_sql(self, path, checksum):
            from recovery_replace import preserve_binary_logging
            checksum = preserve_binary_logging(self, path, checksum)
            h.sql_inputs.append(deepcopy(pin(path)))
            return NativeData.import_sql(self, path, checksum)

        def restore_sql(self, name):
            self.bound()
            reference = self.material['database']['sqlPin']
            expanded = self.root/(name+'.sql')
            with self.timed_stage('sql-stage'):
                staged = stage_private_sql(reference, self.root/(name+'.private.gz'), self.seconds())
            with self.timed_stage('sql-expand'):
                checksum, _ = self.modules['formal_sql_restore'].expand_checked(staged['path'],
                    expanded, reference['sha256'], self.policy['maxExpandedBytes'], self.seconds())
            with self.timed_stage('sql-import'):
                self.import_sql(expanded, checksum)
            # SQL semantics/readback are a finite protocol boundary. The real
            # importer is never described as a restored or verified database.
            return dict(recoveryPoint=self.material['recoveryPoint'], databaseUuid=self.db_uuid,
                endPosition=self.material['database']['endPosition'],
                protocolBoundary='SQL_STDIN_CONSUMER', actualBusinessRestore=False)

        def full_database(self):
            h.events.append(('data-chain', 'DATABASE_FULL'))
            return self.restore_sql('full')

        def incremental_database(self):
            h.events.append(('data-chain', 'DATABASE_INCREMENTAL'))
            return self.restore_sql('incremental')

    h.native_type = ActualProcessProtocol
    monkeypatch.setattr(runtime, 'MinimalData', ActualProcessProtocol)
    real_popen = subprocess.Popen

    def observed_popen(argv, **kwargs):
        assert argv[0] in (sys.executable, 'sh'), 'only declared local subprocess protocols are permitted'
        native = h.current_dispatch[0] if h.current_dispatch is not None else h.natives[-1]
        pending = native.native_context._context.snapshot()['invocations'][-1]
        assert pending['terminalPin'] is None
        assert pending['intentObservation']['argvSha256'] == digest(argv)
        process = real_popen(argv, **kwargs)
        record = dict(process=process, argv=deepcopy(argv), phase=native.native_context.phase,
            intent=deepcopy(pending['intentObservation']), intentPin=deepcopy(pending['intentPinAtDispatch']))
        h.processes.append(record)
        dispatch = h.current_dispatch
        if (h.scenario == 'post-dispatch-guard' and dispatch is not None and dispatch[-1] and
                native.native_context.phase == 'PREPARATION' and not h.post_guard_triggered):
            original_communicate = process.communicate

            def lose_budget_after_actual_exit(*args, **kwargs):
                value = original_communicate(*args, **kwargs)
                assert process.returncode == 0
                h.post_guard_triggered = True
                native.budget.deadline = 0  # Real shared Budget fails the final production guard.
                return value

            process.communicate = lose_budget_after_actual_exit
        return process

    monkeypatch.setattr(data_module, 'subprocess', SimpleNamespace(Popen=observed_popen,
        PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL, TimeoutExpired=subprocess.TimeoutExpired))
    return h


def invoke(h):
    """The real child worker dispatches the real runtime and program producer."""
    actual_exit = worker.main(['--configuration', h.owner_pin['path'], '--request', h.request_pin['path'],
        '--output', str(h.output)])
    result = pinned_json(pin(h.output))
    assert result['actualExitCode'] == actual_exit
    assert result['operationId'] == result['requestId'] == h.request['operationId']
    assert result['action'] == 'RESTORE'
    assert h.actualBusinessRestore is False
    assert h.processes and all(item['process'].poll() == 0 for item in h.processes)
    assert not list(h.root.glob('protocol-invocation-*.json'))
    assert_inputs_unchanged(h)
    return actual_exit, result


def receipt_and_native(h, result):
    data = result['data']
    receipt = pinned_json(data['replacementReceiptPin'])
    native = pinned_json(data['programNativeEvidencePin'])
    assert data['replacementReceiptPin']['path'] == str(h.claim/'replacement-result.json')
    assert data['programNativeEvidencePin']['path'] == str(h.claim/'native-execution-evidence.json')
    assert len(native['invocations']) == len(h.processes)
    assert all(row['terminalObservation']['state'] == 'SUCCEEDED' and
        row['terminalObservation']['actualExitCode'] == 0 for row in native['invocations'])
    return receipt, native


def validate(h):
    return historical.validate_program_evidence(h.owner, h.request, h.root, result_pin=pin(h.output))


def assert_sql_was_imported_and_cleaned(h, native):
    sql = [row for row in native['invocations']
        if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2']
    assert len(sql) == len(h.sql_inputs) == len(h.sql_received) == 2
    assert [row['intentObservation']['action'] for row in sql] == ['DATABASE_FULL', 'DATABASE_INCREMENTAL']
    for row, expected, destination in zip(sql, h.sql_inputs, h.sql_received):
        assert row['intentObservation']['sqlPin'] == row['terminalObservation']['sqlPin'] == expected
        received = destination.read_bytes()
        assert len(received) == expected['bytes']
        assert hashlib.sha256(received).hexdigest() == expected['sha256']
        assert received.startswith(b'SET SESSION sql_log_bin=1;\n')
        assert not os.path.lexists(expected['path'])
    cleanup = pinned_json(pin(h.root/'staging-cleanup.json'))
    assert cleanup['state'] == 'SUCCEEDED' and cleanup['operationId'] == h.request['operationId']
    cleanup_pin = pin(h.root/'sql-staging-cleanup.json')
    sql_cleanup = pinned_json(cleanup_pin)
    assert sql_cleanup['schemaVersion'] == 'MainSqlStagingCleanup/v1'
    assert sql_cleanup['state'] == 'SUCCEEDED' and sql_cleanup['operationId'] == h.request['operationId']
    assert sql_cleanup['intentPin'] == pin(h.root/'sql-staging-cleanup-intent.json')
    intent = pinned_json(sql_cleanup['intentPin'])
    assert intent['schemaVersion'] == 'MainSqlStagingCleanupIntent/v1' and intent['state'] == 'PLANNED'
    assert intent['operationId'] == h.request['operationId'] and intent['operationRoot'] == str(h.root)
    assert intent['bindingPin'] == native['bindingPin'] and intent['generationPin'] == native['generationPin']
    assert sql_cleanup['deletedSqlPins'] == h.sql_inputs
    assert [entry['sqlPin'] for entry in intent['entries']] == h.sql_inputs
    assert [entry['importerPin'] for entry in intent['entries']] == [row['terminalPin'] for row in sql]
    assert all(entry['fileIdentity'] for entry in intent['entries'])
    result = pinned_json(pin(h.output)); receipt = pinned_json(result['data']['replacementReceiptPin'])
    assert result['data']['programSqlCleanupPin'] == receipt['programSqlCleanupPin'] == cleanup_pin
    for reference in (cleanup_pin, sql_cleanup['intentPin']):
        assert reference in result['originalResultPins'] and reference in receipt['originalResultPins']
    assert all(str(Path(row['path']).relative_to(h.root)) not in cleanup['selectedPaths'] for row in h.sql_inputs)
    # The real archived gzip sources remain original and reconstruct the exact
    # finite protocol SQL bytes consumed by the actual local importer.
    for step, destination in zip(h.natives[-1].chain, h.sql_received):
        source = Path(step[2]['database']['sqlPin']['path'])
        assert destination.read_bytes() == b'SET SESSION sql_log_bin=1;\n'+gzip.decompress(source.read_bytes())


def test_actual_success_cleanup_keeps_sql_v2_history_verifiable(producer_case):
    """BDD: real successful producer/cleanup -> history validates without live SQL staging."""
    h = producer_case
    actual_exit, result = invoke(h)
    assert actual_exit == 0 and result['state'] == 'SUCCEEDED'
    receipt, native = receipt_and_native(h, result)
    assert receipt['state'] == 'SUCCEEDED' and native['phase'] == 'RESTORE'
    assert_sql_was_imported_and_cleaned(h, native)
    proof = validate(h)
    assert proof['resultState'] == proof['replacementState'] == 'SUCCEEDED'
    assert proof['generationPin'] == result['data']['programGenerationPin']
    assert not proof['terminalUnknown'] and proof['protectionState'] == 'RELEASED'
    assert all(os.path.exists(reference['path']) for reference in proof['deferredPayloadPins'])


def test_actual_readonly_constructor_failure_does_not_infer_mutation_from_intent(producer_case):
    """BDD: ctx/intent exist, actual readonly child exits zero, bad UUID -> no mutation."""
    h = producer_case; h.scenario = 'constructor-readonly'
    actual_exit, result = invoke(h)
    assert actual_exit == 1 and result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'TARGET_DATABASE_UUID_INVALID'
    assert (h.root/'replacement-preparation/replacement-intent.json').is_file()
    receipt, native = receipt_and_native(h, result)
    assert len(native['invocations']) == 1 and native['phase'] == 'PREPARATION'
    assert native['mutationDispatched'] is native['terminalUnknown'] is False
    assert receipt['mutationDispatched'] is receipt['terminalUnknown'] is False
    assert result['data']['programProtectionCustodyPin'] is None
    assert result['data']['mutationDispatched'] is False
    assert result['data']['terminalUnknown'] is False
    assert epoch.read_current(h.case['epoch'])['state'] == 'FAILED_RETAINED'
    proof = validate(h)
    assert proof['phase'] == 'PREPARATION' and not proof['mutationDispatched']
    assert not proof['terminalUnknown'] and not (h.root/'resource-no-mutation-release.json').exists()


def test_actual_mutation_exit_zero_then_final_guard_failure_freezes_unknown_in_first_receipt(producer_case):
    """BDD: actual write child exits zero then real shared budget fails -> retain unknown."""
    h = producer_case; h.scenario = 'post-dispatch-guard'
    actual_exit, result = invoke(h)
    assert h.post_guard_triggered
    assert actual_exit == 2 and result['state'] == 'TERMINAL_UNKNOWN'
    assert result['failureCode'] == 'DEADLINE_EXCEEDED'
    receipt, native = receipt_and_native(h, result)
    assert native['lastExitCode'] == 0 and native['terminalUnknown'] is False
    assert native['invocations'][-1]['intentObservation']['mutation'] is True
    assert result['data']['mutationDispatched'] is receipt['mutationDispatched'] is True
    assert result['data']['terminalUnknown'] is receipt['terminalUnknown'] is True
    fixed = {Path(reference['path']):Path(reference['path']).read_bytes() for reference in
        (result['data']['replacementReceiptPin'],result['data']['programNativeEvidencePin'],
         result['data']['programProtectionCustodyPin'])}
    proof = validate(h)
    assert proof['terminalUnknown'] and proof['unknownCauses']['outerConservative']
    assert proof['unknownCauses']['native'] is False
    assert all(path.read_bytes() == original for path,original in fixed.items())
    assert not h.engine.actions and not h.loaded and not h.transport.releases


def test_actual_published_generation_then_context_stage_lease_failure_retains_preparation(producer_case, monkeypatch):
    """BDD: generation is real; stage's real resolver runs then lease fails -> PREPARATION retained."""
    h = producer_case
    original_stage = MainNativeExecutionContext.stage

    def stage_with_unavailable_lease(context, generation_pin):
        assert generation_pin == pin(h.claim/'generation.json')
        h.published_generation = deepcopy(generation_pin)
        h.published_generation_bytes = Path(generation_pin['path']).read_bytes()
        original_lease = context._lease_and_resolve

        def unavailable(expected, evidence, *, generation=None, runtime=False):
            if generation is not None:
                raise RecoveryError('PROTOCOL_NATIVE_STAGE_LEASE_FAILURE')
            return original_lease(expected, evidence, generation=generation, runtime=runtime)

        with monkeypatch.context() as lease_seam:
            lease_seam.setattr(context, '_lease_and_resolve', unavailable)
            return original_stage(context, generation_pin)

    monkeypatch.setattr(MainNativeExecutionContext, 'stage', stage_with_unavailable_lease)
    actual_exit, result = invoke(h)
    assert actual_exit == 1 and result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'PROTOCOL_NATIVE_STAGE_LEASE_FAILURE'
    receipt, native = receipt_and_native(h, result)
    assert result['data']['programGenerationPin'] == receipt['programGenerationPin'] == h.published_generation
    assert native['phase'] == 'PREPARATION' and native['generationPin'] is None
    assert len(h.natives) == 1 and not h.sql_received and not h.transport.releases
    assert Path(h.published_generation['path']).read_bytes() == h.published_generation_bytes
    proof = validate(h)
    assert proof['phase'] == 'PREPARATION' and proof['generationPin'] == h.published_generation
    assert not proof['terminalUnknown'] and proof['replacementState'] == 'FAILED_RETAINED'


@pytest.mark.parametrize('unknown', [False, True], ids=['known-failure', 'outer-unknown'])
def test_actual_ready_publication_failure_never_rewrites_success_receipt(producer_case, monkeypatch, unknown):
    """BDD: successful original receipt exists, READY fails -> retain immutable success plus outer facts."""
    h = producer_case
    original_complete = epoch.complete_restore

    def unavailable_ready(*args, **kwargs):
        if args[3] == 'READY':
            receipt = pinned_json(args[4])
            assert receipt['state'] == 'SUCCEEDED' and receipt['terminalUnknown'] is False
            h.fixed_before_ready = {Path(reference['path']):Path(reference['path']).read_bytes()
                for reference in (args[4],receipt['programNativeEvidencePin'],receipt['programProtectionCustodyPin'])}
            raise RecoveryError('PROTOCOL_READY_PUBLICATION_FAILURE', unknown=unknown)
        return original_complete(*args, **kwargs)

    monkeypatch.setattr(epoch, 'complete_restore', unavailable_ready)
    actual_exit, result = invoke(h)
    assert actual_exit == (2 if unknown else 1)
    assert result['state'] == ('TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED')
    assert result['failureCode'] == 'PROTOCOL_READY_PUBLICATION_FAILURE'
    receipt, native = receipt_and_native(h, result)
    assert_sql_was_imported_and_cleaned(h, native)
    assert receipt['state'] == 'SUCCEEDED' and receipt['terminalUnknown'] is False
    assert result['data']['terminalUnknown'] is unknown and native['terminalUnknown'] is False
    assert epoch.read_current(h.case['epoch'])['state'] == 'REPLACING'
    assert h.fixed_before_ready and all(path.read_bytes() == original for path,original in h.fixed_before_ready.items())
    proof = validate(h)
    assert proof['replacementState'] == 'SUCCEEDED' and proof['resultState'] == result['state']
    assert proof['terminalUnknown'] is unknown and proof['unknownCauses']['outerConservative'] is unknown
    assert all(path.read_bytes() == original for path,original in h.fixed_before_ready.items())
    assert not (h.root/'resource-release.json').exists()
