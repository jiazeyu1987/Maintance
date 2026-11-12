"""Historical MAIN proof contracts over real Linux files, locks and processes.

The original execution context, generation resolver, reservation and protection
implementations run unchanged. Only the external MySQL protocol is replaced by
a finite local Python process whose state is a private file. SQL stream_import
also runs a real stdin consumer. Neither transport claims a restored database.

The worker/replacement envelopes are explicit protocol fixtures: their producer
is a separate work item. Large-history rows are explicitly metadata fixtures,
not claimed executions. No successful context/source/protection is mocked.
"""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import quote

import pytest

from test_recovery_program_native_invocations import InvocationCase, command, sql_transport
from test_recovery_program_native_constructor import DatabaseBoundary
from test_recovery_program_activation import locked, claim, snapshot, start, stage, finish
from test_recovery_program_generation import write
from recovery_backup_epoch import complete_restore, read_current
from recovery_engine import RecoveryError, canonical, digest, pin, pinned_json, utc
from recovery_data import NativeData
from recovery_program_protection import ProtectionCustody
import recovery_main_target as main
import recovery_minimal_runtime as runtime


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux context, private metadata, flock and subprocess contracts')
NATIVE_LIMIT = 64 * 1024 * 1024
COMMON = ('programExecutionPhase', 'programNativeEvidencePin',
          'programProtectionCustodyPin', 'programGenerationPin')


def module():
    # Keep the absent production module inside test calls so RED still constructs
    # actual original metadata and subprocess evidence before the missing API.
    return importlib.import_module('recovery_program_evidence')


class EvidenceCase(InvocationCase):
    def stage_switch_receipts(self):
        # Explicit external Docker receipt protocol fixture, derived from the
        # existing validated stopped-switch rows. This is not a real switch.
        # Native commands, epoch transition and generation resolution stay real.
        original_result = pinned_json(self.e.switch)
        intent = pinned_json(original_result['intentPin'])
        root = self.e.claim/'program-switch'; root.mkdir(mode=0o700)
        intent_pin = write(root/'intent.json', intent)
        applications = {}
        sequence = 0
        for role in ('frontend', 'backend'):
            application = pinned_json(original_result['applicationPins'][role])
            original, created = application['original'], application['created']
            requests = [('POST', '/containers/'+original['Id']+'/rename?name='+quote(
                original['Name'][1:]+'-retained-fixture', safe=''), None, None)]
            requests += [('POST', '/networks/'+network['NetworkID']+'/disconnect',
                dict(Container=original['Id'], Force=False), None)
                for network in original['NetworkSettings']['Networks'].values()]
            planned = intent['requests'][role]
            body = dict(planned['Config'], HostConfig=planned['HostConfig'], NetworkingConfig=planned['NetworkingConfig'])
            requests.append(('POST', '/containers/create?name='+quote(original['Name'][1:], safe=''),
                body, dict(Id=created['Id'], Warnings=[])))
            for method, path, body, result in requests:
                sequence += 1
                attempt = write(root/('%04d-intent.json' % sequence), dict(method=method, path=path,
                    bodySha256=None if body is None else digest(body), startedAt=utc()))
                write(root/('%04d-result.json' % sequence), dict(intentPin=attempt, result=result, finishedAt=utc()))
            write(root/(role+'-created-observation.json'), created)
            applications[role] = write(root/(role+'-verified.json'), application)
        self.e.switch = write(root/'result.json', dict(original_result, intentPin=intent_pin,
            applicationPins=applications))
        self.switch_pins = [pin(path) for path in sorted(root.iterdir())]

    def restore(self):
        self.stage_switch_receipts()
        super().restore()

    def at_native(self, callback):
        """Real constructor, at the explicit external database boundary."""
        self.sequence += 1
        parent = self.e.root/'replacement-preparation' if self.view.phase == 'PREPARATION' else self.e.claim/'runtime'
        parent.mkdir(mode=0o700, exist_ok=True)
        log = parent/('evidence-%03d' % self.sequence)
        log.mkdir(mode=0o700)
        seen = []

        class Boundary(runtime.MinimalData):
            def database_uuid(native):
                seen.append(native)
                callback(native)
                raise DatabaseBoundary('historical evidence test stops before DB identity')

        configuration = deepcopy(self.configuration)
        source = deepcopy(configuration['sources'][self.e.request['sourceConfigRef']])
        with pytest.raises(DatabaseBoundary, match='historical evidence test stops before DB identity'):
            Boundary(configuration, deepcopy(self.e.request), source, {}, self.e.chain,
                deepcopy(configuration['targets']['target57']), log, [], native_context=self.view)
        assert len(seen) == 1
        assert seen[0].source == source
        return seen[0]


SQL_PROTOCOL = r'''
import json, pathlib, sys
path, statement, uuid = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
state = json.loads(path.read_text(encoding='utf-8'))
if statement.startswith('SET GLOBAL event_scheduler='):
    state['scheduler'] = statement.split('=')[1].rstrip(';')
    assert state['scheduler'] in ('ON', 'OFF')
    path.write_text(json.dumps(state), encoding='utf-8')
elif statement == 'SHOW DATABASES;':
    sys.stdout.write('app\ninformation_schema\nmysql\nperformance_schema\nsys\n')
elif statement == 'SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only, @@GLOBAL.event_scheduler;':
    sys.stdout.write(uuid+'\t0\t0\t'+state['scheduler']+'\n')
elif statement in ("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE USER='event_scheduler';",
                   'SELECT COUNT(*) FROM information_schema.innodb_trx;'):
    sys.stdout.write('0\n')
else:
    raise RuntimeError('unexpected external SQL protocol request')
'''


def unique(references):
    result = []
    for reference in references:
        if reference is not None and reference not in result:
            result.append(deepcopy(reference))
    return result


def evidence_files(root):
    return {str(path): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def validate(h, **kwargs):
    return module().validate_program_evidence(h.e.owner, h.e.request, h.e.root,
        result_pin=h.result_pin, **kwargs)


def publish_envelopes(h, *, result_changes=None, receipt_changes=None):
    """Explicit future producer protocol boundary; never a business outcome."""
    e = h.e
    native_pin = write(e.claim/'native-execution-evidence.json', h.native) if h.native is not None else None
    custody_pin = write(e.claim/'protection-custody-evidence.json', h.custody) if h.custody is not None else None
    fields = dict(programExecutionPhase=h.phase, programNativeEvidencePin=native_pin,
        programProtectionCustodyPin=custody_pin,
        programGenerationPin=getattr(h, 'generation_override', None if h.native is None else h.native['generationPin']))
    originals = unique([e.owner_pin, e.request_pin, e.operation_pin, e.reservation, h.binding, h.context,
        fields['programGenerationPin'], native_pin, custody_pin,
        *getattr(h.c, 'switch_pins', []),
        *(h.native['originalResultPins'] if h.native is not None else []),
        *(h.custody['originalResultPins'] if h.custody is not None else [])])
    unknown = bool(h.native is not None and h.native['terminalUnknown']) or getattr(h, 'http_unknown', False)
    mutation = bool(h.native is not None and h.native['mutationDispatched']) or bool(getattr(h.c, 'switch_pins', []))
    failure = None if h.state == 'SUCCEEDED' else 'PROGRAM_TEST_RETAINED'
    receipt = dict(fields, state='SUCCEEDED' if h.state == 'SUCCEEDED' else 'FAILED_RETAINED',
        operationId=e.request['operationId'], targetConfigRef=e.request['targetConfigRef'],
        databaseUuid=e.case['epoch']['databaseUuid'], finishedAt=utc(), failureCode=failure,
        mutationDispatched=mutation, terminalUnknown=unknown, originalResultPins=originals)
    receipt.update(receipt_changes or {})
    h.receipt_pin = write(e.claim/'replacement-result.json', receipt)
    data = dict(fields, replacementReceiptPin=h.receipt_pin, mutationDispatched=mutation,
        terminalUnknown=unknown, actualNativeExitCode=None if h.native is None else h.native['lastExitCode'])
    if h.state != 'SUCCEEDED': data.update(partialTargetRetained=True, retryPermitted=False)
    result = dict(schemaVersion='backup-restore-operation-result/v1', operationId=e.request['operationId'],
        requestId=e.request['operationId'], action='RESTORE', state=h.state, failureCode=failure,
        data=data, originalResultPins=unique([*originals, h.receipt_pin]), startedAt=utc(), finishedAt=utc(),
        actualExitCode=0 if h.state == 'SUCCEEDED' else 2 if unknown else 1)
    result.update(result_changes or {})
    h.result_pin = write(e.root/'worker-result.json', result)
    return h


@pytest.fixture
def history_factory(tmp_path, monkeypatch):
    def build(*, outcome='success', phases='both', complete_epoch=True, install_protection=True,
              formal_directory=None):
        c = EvidenceCase(tmp_path, monkeypatch, formal_directory=formal_directory)
        e = c.e
        e.operation_pin = write(e.root/'operation.json', dict(operationId=e.request['operationId'],
            requestPin=e.request_pin, configurationSha256=digest(e.owner), startedAt=utc()))
        protocol = tmp_path/'sql-protocol.py'; protocol.write_text(SQL_PROTOCOL, encoding='utf-8'); protocol.chmod(0o600)
        state = tmp_path/'sql-state.json'; state.write_bytes(b'{"scheduler":"ON"}'); state.chmod(0o600)

        def query(native, statement, *, mutation=False):
            return native.command([sys.executable, '-B', str(protocol), str(state), statement,
                e.case['epoch']['databaseUuid']], mutation=mutation)

        monkeypatch.setattr(main, 'mysql_query', query)
        if outcome == 'not-started':
            return publish_envelopes(SimpleNamespace(e=e, c=c, binding=None, context=None,
                native=None, custody=None, phase='NOT_STARTED', state='FAILED_RETAINED'))
        with c.opened():
            custody = []
            def prepare(native):
                value = ProtectionCustody.from_preparation(native)
                custody.append(value)
                protections = value.view_for(native)
                assert protections.archive is None and protections.fence is None
                if install_protection:protections.scheduler.install()
                native.command(command(), mutation=False)
            if outcome == 'constructor-before-custody': c.at_native(lambda native: None)
            else: c.at_native(prepare)
            generation_override = None
            if outcome == 'generation-before-stage':
                c.stage_switch_receipts()
                generation_override = stage(e.case, c.saved, c.fd,
                    target_pin=write(e.claim/'target.json', e.candidate),
                    capture_pins={'source57': write(e.claim/'capture.json', e.capture)}, switch_result_pin=e.switch)
                c.ctx.budget.deadline = 0
                with pytest.raises(RecoveryError, match='DEADLINE_EXCEEDED'):
                    c.ctx.stage(generation_override)
            elif phases == 'both' and outcome != 'constructor-before-custody':
                c.restore()
                def restore(native):
                    native.request['action'] = 'DATABASE_FULL'
                    sql, checksum = sql_transport(native, native.root/'actual-sql-stdin',
                        code=7 if outcome == 'sql-failure' else 0,
                        unavailable=outcome == 'unknown')
                    if outcome in ('sql-failure', 'unknown'):
                        with pytest.raises(Exception, match='FORMAL_SQL_IMPORT_FAILED|FORMAL_SQL_IMPORT_UNAVAILABLE'):
                            NativeData.import_sql(native, sql, checksum)
                    else:
                        NativeData.import_sql(native, sql, checksum)
                        native.request['action'] = 'CONSISTENCY'
                        native.command(command(), mutation=False)
                        if outcome == 'success': custody[0].release(native)
                c.at_native(restore)
            native, protected = c.ctx.snapshot(), custody[0].snapshot() if custody else None
            h = SimpleNamespace(e=e, c=c, binding=c.binding, context=c.saved, native=native,
                custody=protected, phase=c.view.phase,
                state='SUCCEEDED' if outcome == 'success' and phases == 'both' else
                    'TERMINAL_UNKNOWN' if outcome == 'unknown' else 'FAILED_RETAINED')
            if generation_override is not None: h.generation_override = generation_override
        publish_envelopes(h)
        if complete_epoch:
            with locked(e.case) as fd:
                current = read_current(e.case['epoch'])
                complete_restore(e.case['epoch'], e.request['operationId'], current['epochId'],
                    'READY' if h.state == 'SUCCEEDED' else 'FAILED_RETAINED', h.receipt_pin, fd)
        return h
    return build


def test_success_historical_validator_accepts_real_two_phase_native_sql_and_custody_after_close(history_factory):
    h = history_factory()
    before = evidence_files(h.e.case['root'])
    proof = validate(h)
    assert proof['operationId'] == h.e.request['operationId']
    assert proof['phase'] == 'RESTORE' and proof['generationPin'] == h.native['generationPin']
    assert proof['bindingPin'] == h.binding and proof['contextPin'] == h.context
    assert proof['invocations'] == h.native['invocations']
    assert {row['phase'] for row in proof['invocations']} == {'PREPARATION', 'RESTORE'}
    assert any(row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2' for row in proof['invocations'])
    assert any(Path(row['terminalPin']['path']).is_relative_to(h.e.claim/'runtime') for row in proof['invocations'])
    assert proof['mutationDispatched'] is True and proof['terminalUnknown'] is False
    assert proof['lastExitCode'] == 0
    assert before == evidence_files(h.e.case['root'])


def test_historical_proof_does_not_require_an_active_host_reservation(history_factory):
    h = history_factory()
    # Complete the external owner-result protocol required by release_success.
    # These private material records do not claim an actual business restore;
    # the real context, native exits, custody, epoch and reservation stay intact.
    materials = {name: write(h.e.root/('owner-protocol-'+name+'.json'), dict(
        schemaVersion='MainOwnerMaterialProtocolFixture/v1', operationId=h.e.request['operationId'],
        boundary=name, actualBusinessRestore=False))
        for name in ('database', 'objects', 'consistency', 'derived', 'application-start')}
    worker = pinned_json(h.result_pin)
    worker['message'] = 'Explicit owner-result protocol fixture; no actual business restore'
    worker['data'].update(targetConfigRef=h.e.request['targetConfigRef'],
        orderedChainPins=[h.e.chain[0][0]], databaseResultPins=[materials['database']],
        objectResultPins=[materials['objects']], consistencyPin=materials['consistency'],
        derivedPin=materials['derived'], applicationStartPin=materials['application-start'],
        actualBusinessRestore=False)
    worker['originalResultPins'].extend(materials.values())
    h.result_pin = write(h.e.root/'worker-result.json', worker)
    exited = subprocess.run([sys.executable, '-B', '-c', 'pass'], check=True)
    child = write(h.e.root/'child-exit.json', dict(operationId=h.e.request['operationId'],
        actualExitCode=exited.returncode, timedOut=False))
    from recovery_resource_admission import release_success
    release_success(h.e.owner, h.e.request, h.e.root, h.result_pin, child)
    assert not (h.e.case['root']/'resource-host/active.json').exists()
    before = evidence_files(h.e.case['root'])
    assert validate(h)['bindingPin'] == h.binding
    assert before == evidence_files(h.e.case['root'])


def test_subsequent_real_generation_does_not_replace_the_original_target_pin(history_factory):
    h = history_factory()
    original = pinned_json(h.native['generationPin'])
    with locked(h.e.case) as fd:
        root = claim(h.e.case, 'restore-2')
        context = snapshot(h.e.case, fd, 'restore-2')
        epoch = start(h.e.case, root, fd, operation='restore-2')
        new_target = write(root/'target.json', pinned_json(original['targetPin']))
        generation = stage(h.e.case, context, fd, target_pin=new_target,
            capture_pins={k: v['capturePin'] for k, v in original['captureBindings'].items()}, switch_result_pin=None)
        finish(h.e.case, root, epoch, generation, fd)
    proof = validate(h)
    assert proof['targetPin'] == original['targetPin'] and proof['targetPin'] != new_target
    assert proof['generationPin'] == h.native['generationPin']


@pytest.mark.parametrize('outcome,phases', [('retained', 'both'), ('retained', 'preparation'),
    ('sql-failure', 'both'), ('unknown', 'both')])
def test_failure_proof_preserves_actual_exits_and_unknown_without_granting_success(history_factory, outcome, phases):
    h = history_factory(outcome=outcome, phases=phases)
    proof = validate(h)
    assert proof['phase'] == h.phase and proof['lastExitCode'] == h.native['lastExitCode']
    assert proof['terminalUnknown'] == (outcome == 'unknown')
    assert proof['invocations'] == h.native['invocations']
    assert not any(key in proof for key in ('releasePermitted', 'retryPermitted', 'targetReady'))
    if outcome == 'sql-failure': assert proof['lastExitCode'] == 7


def test_not_started_requires_actual_empty_dispatch_scope_not_none_fields_alone(history_factory):
    h = history_factory(outcome='not-started')
    proof = validate(h)
    assert proof['phase'] == 'NOT_STARTED' and proof['invocations'] == []
    assert proof['mutationDispatched'] is False and proof['terminalUnknown'] is False


def test_constructor_boundary_failure_keeps_real_empty_context_without_inventing_custody(history_factory):
    h = history_factory(outcome='constructor-before-custody')
    assert h.native['invocations'] == [] and h.custody is None
    proof = validate(h)
    assert proof['phase'] == 'PREPARATION' and proof['bindingPin'] == h.binding
    assert proof['mutationDispatched'] is False and proof['terminalUnknown'] is False


@pytest.mark.parametrize('relative', ['program-context.json', 'program-execution-binding.json', 'generation.json',
    'runtime/native-000.json', 'runtime/importer-000.json', 'mysql-scheduler/intent.json',
    'archive-view/intent.json', 'published-fence/intent.json', 'program-switch/0001-intent.json',
    'program-import/load-intent.json'])
def test_not_started_refuses_existing_context_or_dispatch_in_its_exact_claim(history_factory, relative):
    h = history_factory(outcome='not-started')
    path = h.e.claim/relative; path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    write(path, {'operationId': h.e.request['operationId']})
    with pytest.raises(RecoveryError): validate(h)


def test_other_operations_private_claim_does_not_pollute_not_started_proof(history_factory):
    h = history_factory(outcome='not-started')
    other = h.e.claim.parent/'unrelated-operation'; other.mkdir(mode=0o700)
    write(other/'native-000.json', {'operationId': 'unrelated-operation'})
    assert validate(h)['phase'] == 'NOT_STARTED'


@pytest.mark.parametrize('field', COMMON)
def test_data_and_replacement_receipt_must_name_identical_phase_and_pins(history_factory, field):
    h = history_factory(complete_epoch=False)
    value = pinned_json(h.result_pin)
    value['data'][field] = 'PREPARATION' if field == 'programExecutionPhase' else None
    h.result_pin = write(Path(h.result_pin['path']), value)
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('field,value', [('operationId', 'other'), ('requestId', 'other'), ('action', 'FULL'),
    ('actualExitCode', 1), ('failureCode', 'UNEXPECTED_FAILURE')])
def test_outer_success_cannot_rebind_the_original_request_or_terminal(history_factory, field, value):
    h = history_factory()
    result = pinned_json(h.result_pin); result[field] = value
    h.result_pin = write(Path(h.result_pin['path']), result)
    with pytest.raises(RecoveryError): validate(h)


def test_equivalent_result_copy_outside_fixed_owner_paths_is_rejected(history_factory):
    h = history_factory()
    h.result_pin = write(h.e.claim/'copied-worker-result.json', pinned_json(h.result_pin))
    with pytest.raises(RecoveryError): validate(h)


def test_original_operation_admission_digest_is_not_reconstructed_from_current_owner(history_factory):
    h = history_factory()
    operation = pinned_json(h.e.operation_pin); operation['configurationSha256'] = '0'*64
    write(Path(h.e.operation_pin['path']), operation)
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('field', ['operationId', 'action', 'mutation', 'argvSha256', 'sqlPin'])
def test_sql_v2_identity_must_match_the_original_intent_even_after_repinning(history_factory, field):
    h = history_factory(complete_epoch=False)
    row = next(row for row in h.native['invocations'] if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2')
    terminal = deepcopy(row['terminalObservation'])
    terminal[field] = {'operationId': 'foreign', 'action': 'ARBITRARY_SHELL', 'mutation': False,
        'argvSha256': '0'*64, 'sqlPin': h.e.owner_pin}[field]
    row['terminalObservation'] = terminal
    row['terminalPin'] = write(Path(row['terminalPin']['path']), terminal)
    h.native['originalResultPins'] = [row['terminalPin'] for row in h.native['invocations']]
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('fault', ['intent-digest', 'sequence', 'duplicate', 'reordered', 'omit-preparation',
    'schema-v1', 'arbitrary-action', 'phase', 'mutation-summary', 'unknown-summary', 'last-exit-summary', 'terminal-observation'])
def test_repinning_aggregate_cannot_hide_invocation_identity_order_or_coverage_faults(history_factory, fault):
    h = history_factory(complete_epoch=False)
    rows = h.native['invocations']
    if fault == 'intent-digest': rows[0]['intentPinAtDispatch']['sha256'] = '0'*64
    elif fault == 'sequence': rows[0]['sequence'] = 999
    elif fault == 'duplicate': rows.append(deepcopy(rows[-1]))
    elif fault == 'reordered': rows[:] = list(reversed(rows))
    elif fault == 'omit-preparation':
        rows[:] = [row for row in rows if row['phase'] == 'RESTORE']
        for i, row in enumerate(rows): row['sequence'] = i
        h.native['originalResultPins'] = [row['terminalPin'] for row in rows]
    elif fault == 'schema-v1':
        row = next(row for row in rows if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2')
        for name in ('intentObservation', 'terminalObservation'): row[name]['schemaVersion'] = 'RecoverySqlImporter/v1'
        row['intentPinAtDispatch'].update(bytes=len(canonical(row['intentObservation'])), sha256=digest(row['intentObservation']))
        row['terminalPin'] = write(Path(row['terminalPin']['path']), row['terminalObservation'])
        h.native['originalResultPins'] = [row['terminalPin'] for row in rows]
    elif fault == 'arbitrary-action': rows[0]['intentObservation']['action'] = 'ARBITRARY_SHELL'
    elif fault == 'phase': rows[0]['phase'] = 'RESTORE'
    elif fault == 'mutation-summary': h.native['mutationDispatched'] = False
    elif fault == 'unknown-summary': h.native['terminalUnknown'] = True
    elif fault == 'last-exit-summary': h.native['lastExitCode'] = 99
    else: rows[0]['terminalObservation']['stdoutBytes'] += 1
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('field', ['configurationPin', 'requestPin', 'reservationPin', 'contextPin'])
def test_rebound_execution_metadata_cannot_substitute_equivalent_copies(history_factory, field):
    h = history_factory(complete_epoch=False)
    binding = pinned_json(h.binding)
    binding[field] = write(h.e.claim/('copied-'+field+'.json'), pinned_json(binding[field]))
    h.binding = write(Path(h.binding['path']), binding)
    h.native['bindingPin'] = h.binding
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('fault', ['scope', 'generation', 'protection-pin', 'hidden-invocation', 'legacy-owner'])
def test_only_exact_operation_generation_and_custody_can_admit_program_receipts(history_factory, fault):
    h = history_factory(complete_epoch=False)
    if fault == 'scope':
        row = h.native['invocations'][0]
        outside = h.e.claim.parent/'outside-native.json'
        row['terminalPin'] = write(outside, row['terminalObservation'])
        row['intentPinAtDispatch']['path'] = str(outside)
        h.native['originalResultPins'] = [r['terminalPin'] for r in h.native['invocations']]
    elif fault == 'generation':
        generation = pinned_json(h.native['generationPin']); generation['operationId'] = 'foreign'
        h.native['generationPin'] = write(Path(h.native['generationPin']['path']), generation)
    elif fault == 'protection-pin': h.custody['protections']['scheduler']['releasePin'] = h.e.owner_pin
    elif fault == 'hidden-invocation':
        write(h.e.claim/'runtime/native-hidden.json', h.native['invocations'][0]['terminalObservation'])
    else:
        h.e.owner.pop('targetProgramPolicies')
        h.e.owner_pin = write(h.e.root/'configuration.json', h.e.owner)
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


def test_missing_custody_is_not_success_even_when_native_commands_all_exited_zero(history_factory):
    h = history_factory(complete_epoch=False)
    h.custody = None
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


def test_custody_journal_original_bytes_are_required(history_factory):
    h = history_factory()
    Path(h.custody['protections']['scheduler']['releasePin']['path']).write_bytes(b'{}')
    with pytest.raises(RecoveryError): validate(h)


@pytest.mark.parametrize('fault', ['missing-pin', 'wrong-intent', 'missing-result', 'foreign-result'])
def test_switch_http_originals_cannot_be_omitted_or_cross_associated(history_factory, fault):
    h = history_factory(complete_epoch=False)
    root = h.e.claim/'program-switch'
    if fault == 'missing-pin':
        missing = pin(root/'0001-result.json')
        h.c.switch_pins = [p for p in h.c.switch_pins if p != missing]
    elif fault == 'missing-result':
        (root/'0001-result.json').unlink()
        h.c.switch_pins = [p for p in h.c.switch_pins if p['path'] != str(root/'0001-result.json')]
    else:
        value = pinned_json(pin(root/'0001-result.json'))
        value['intentPin'] = pin(root/'0002-intent.json') if fault == 'wrong-intent' else h.e.request_pin
        changed = write(root/'0001-result.json', value)
        h.c.switch_pins = [changed if p['path'] == changed['path'] else p for p in h.c.switch_pins]
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


def test_unreleased_custody_cannot_be_relabelled_success(history_factory):
    h = history_factory(outcome='retained', complete_epoch=False)
    h.state = 'SUCCEEDED'
    publish_envelopes(h)
    with pytest.raises(RecoveryError): validate(h)


def test_original_intent_pin_is_verified_from_embedded_bytes_not_reopened_after_replacement(history_factory):
    h = history_factory()
    for row in h.native['invocations']:
        assert Path(row['intentPinAtDispatch']['path']).read_bytes() != canonical(row['intentObservation'])
        assert row['intentPinAtDispatch']['sha256'] == digest(row['intentObservation'])
    assert validate(h)['invocations'] == h.native['invocations']


def test_published_generation_is_retained_when_real_context_stage_budget_fails(history_factory):
    h = history_factory(outcome='generation-before-stage')
    assert h.native['phase'] == 'PREPARATION' and h.native['generationPin'] is None
    assert all(row['phase'] == 'PREPARATION' for row in h.native['invocations'])
    proof = validate(h)
    assert proof['generationPin'] == h.generation_override and proof['phase'] == 'PREPARATION'


def test_successful_replacement_receipt_is_not_rewritten_when_real_epoch_publication_fails(history_factory):
    h = history_factory(complete_epoch=False)
    before = Path(h.receipt_pin['path']).read_bytes()
    with locked(h.e.case, held=False) as fd:
        current = read_current(h.e.case['epoch'])
        with pytest.raises(ValueError, match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
            complete_restore(h.e.case['epoch'], h.e.request['operationId'], current['epochId'],
                'READY', h.receipt_pin, fd)
    result = pinned_json(h.result_pin)
    result.update(state='FAILED_RETAINED', failureCode='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED', actualExitCode=1)
    result['data'].update(partialTargetRetained=True, retryPermitted=False)
    h.result_pin = write(Path(h.result_pin['path']), result)
    proof = validate(h)
    assert proof['replacementState'] == 'SUCCEEDED' and proof['resultState'] == 'FAILED_RETAINED'
    assert Path(h.receipt_pin['path']).read_bytes() == before


def expand_metadata_history(h):
    """Scale-only external receipt protocol, not thousands of claimed commands."""
    template = next(row for row in h.native['invocations'] if row['phase'] == 'RESTORE' and
        row['intentObservation']['schemaVersion'] == 'RecoveryDataInvocation/v1')
    root = h.e.claim/'runtime/metadata-scale-fixture'; root.mkdir(mode=0o700)
    for index in range(3500):
        row = deepcopy(template)
        row['sequence'] = len(h.native['invocations'])
        path = root/('native-%05d.json' % index)
        row['intentPinAtDispatch'] = dict(path=str(path), bytes=len(canonical(row['intentObservation'])),
            sha256=digest(row['intentObservation']))
        row['terminalPin'] = write(path, row['terminalObservation'])
        h.native['invocations'].append(row)
        h.native['originalResultPins'].append(row['terminalPin'])
    publish_envelopes(h)
    reference = pin(h.e.claim/'native-execution-evidence.json')
    assert 4*1024*1024 < reference['bytes'] < NATIVE_LIMIT


def test_real_native_snapshot_larger_than_four_mib_uses_dedicated_bounded_reader(history_factory):
    h = history_factory(complete_epoch=False)
    expand_metadata_history(h)
    assert len(validate(h)['invocations']) == len(h.native['invocations'])


@pytest.mark.parametrize('fault', ['oversize', 'public-mode', 'hardlink', 'symlink', 'sha'])
def test_native_reader_preserves_size_privacy_identity_and_content_limits(history_factory, fault):
    h = history_factory(complete_epoch=False)
    path = h.e.claim/'native-execution-evidence.json'
    if fault == 'oversize':
        with path.open('wb') as output: output.truncate(NATIVE_LIMIT+1)
        reference = pin(path)
    elif fault == 'public-mode': path.chmod(0o644); reference = pin(path)
    elif fault == 'hardlink':
        os.link(path, h.e.claim/'linked-evidence.json')
        reference = dict(path=str(path), bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    elif fault == 'symlink':
        real = h.e.claim/'elsewhere-evidence.json'; path.rename(real); path.symlink_to(real)
        reference = dict(path=str(path), bytes=real.stat().st_size, sha256=hashlib.sha256(real.read_bytes()).hexdigest())
    else:
        reference = pin(path); reference['sha256'] = '0'*64
    receipt = pinned_json(h.receipt_pin); receipt['programNativeEvidencePin'] = reference
    receipt['originalResultPins'] = [reference if p['path'] == str(path) else p for p in receipt['originalResultPins']]
    h.receipt_pin = write(Path(h.receipt_pin['path']), receipt)
    result = pinned_json(h.result_pin)
    result['data'].update(programNativeEvidencePin=reference, replacementReceiptPin=h.receipt_pin)
    result['originalResultPins'] = unique([p for p in result['originalResultPins']
        if p['path'] not in (str(path), str(h.e.claim/'replacement-result.json'))]+[reference,h.receipt_pin])
    h.result_pin = write(Path(h.result_pin['path']), result)
    with pytest.raises(RecoveryError): validate(h)


def test_shared_validation_budget_cannot_be_ignored(history_factory):
    h = history_factory()
    def expired(): raise RecoveryError('EVIDENCE_TEST_DEADLINE')
    with pytest.raises(RecoveryError, match='EVIDENCE_TEST_DEADLINE'):
        validate(h, guard=expired)
