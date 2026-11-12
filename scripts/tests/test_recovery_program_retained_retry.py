"""Real v1 history, Linux locks and v2 execution; external services are protocols."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_recovery_program_evidence import history_factory, publish_envelopes, validate
from test_recovery_program_resource_release import child_exit
from test_recovery_program_activation import locked, start
from test_recovery_program_native_invocations import command, sql_transport
from recovery_engine import Budget, digest, pin, pinned_json, utc, write
from recovery_backup_epoch import read_current, complete_restore
from recovery_program_evidence import validate_program_evidence
from recovery_program_native import MainNativeExecutionContext
from recovery_program_protection import ProtectionCustody
from recovery_data import NativeData
import recovery_resource_admission as admission

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux flock and processes')


def module():
    try:
        return importlib.import_module('recovery_program_retry')
    except ModuleNotFoundError:
        pytest.fail('MISSING_MAIN_PROGRAM_RETAINED_RETRY_CONTEXT')


def clear(h):
    """Explicit clearance envelope; real original proof and no-mutation release."""
    from recovery_retained_retry import validate_clearance
    e = h.e
    exited = child_exit(h, 1)
    released = admission.release_no_mutation(e.owner, e.request, e.root, h.result_pin, exited)
    refs = dict(configurationPin=e.owner_pin, requestPin=e.request_pin, resultPin=h.result_pin,
        exitPin=exited, replacementResultPin=h.receipt_pin, noMutationReleasePin=released)
    observation = write(e.claim/'recovery-observation.json', dict(
        schemaVersion='ExplicitExternalTargetObservationProtocolUnit/v1', actualBusinessRestore=False))
    clearance = write(e.claim/'recovery-clearance.json', dict(schemaVersion='RetainedReplacementRecovery/v2',
        operationId=e.request['operationId'], sourceConfigRef=e.request['sourceConfigRef'],
        recoveryPointRef=e.request['recoveryPointRef'], targetConfigRef=e.request['targetConfigRef'],
        targetConfigurationSha256=digest(e.owner['targets']['target57']), authorization='Explicit protocol authorization',
        failurePhase='BEFORE_MUTATION', issuedAt=utc(),
        expiresAt=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
        observationPin=observation, reservationPin=e.reservation, **refs))
    release = write(e.root/'resource-recovery-release.json', dict(clearancePin=clearance,
        reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
    write(e.claim/'recovery-ready.json', dict(clearancePin=clearance, releasePin=release))
    assert validate_clearance(e.owner['targets']['target57'], e.claim) is not None
    h.clearance = clearance
    return h


@pytest.fixture
def retained(history_factory):
    # Use the actual imported engine's formal directory. The authenticated
    # package import route and modules_from retain all their origin checks.
    names = ('formal_sql_restore', 'formal_data_evidence', 'formal_s3_export',
             'formal_physical_restore_readback', 'formal_schema_evidence')
    import recovery_minimal_runtime as runtime
    formal = Path(importlib.import_module('formal_sql_restore').__file__).resolve().parent
    modules = runtime.modules_from(str(formal))
    assert tuple(modules) == names, 'FORMAL_TEST_MODULE_SET_MISMATCH'
    roots = {Path(modules[name].__file__).resolve().parent for name in names}
    assert len(roots) == 1, 'FORMAL_TEST_MODULE_ORIGIN_MISMATCH'
    return clear(history_factory(outcome='retained', phases='preparation', install_protection=False,
        formal_directory=roots.pop()))


def retry(h, *, purpose='SOURCE_CANDIDATE', **kwargs):
    return module().resolve_retry_target(h.e.owner, 'target57', purpose=purpose,
        source_ref=kwargs.pop('source_ref', 'source57'), **kwargs)


def new_operation(h):
    e = h.e
    request = dict(e.request, operationId='restore-2')
    root = Path(e.owner['operationsRoot'])/request['operationId']; root.mkdir(mode=0o700)
    claim = e.claim.parent/request['operationId']; claim.mkdir(mode=0o700)
    values = dict(vars(e), request=request, root=root, claim=claim)
    values.update(owner_pin=write(root/'configuration.json', e.owner), request_pin=write(root/'request.json', request))
    values['operation_pin'] = write(root/'operation.json', dict(operationId=request['operationId'],
        requestPin=values['request_pin'], configurationSha256=digest(e.owner), startedAt=utc()))
    values['reservation'] = admission.reserve(e.owner, request, root)
    switch = pinned_json(e.switch)
    switch_intent = write(claim/'switch-intent-protocol.json', dict(pinned_json(switch['intentPin']), operationId='restore-2'))
    values['switch'] = write(claim/'switch-result-protocol.json', dict(switch, operationId='restore-2', intentPin=switch_intent))
    from recovery_retained_retry import bind_clearances
    bind_clearances(e.owner['targets']['target57'], request, consume=True)
    return SimpleNamespace(**values)


def test_source_candidate_keeps_failed_epoch_and_all_original_bytes(retained):
    h = retained
    before = {p:p.read_bytes() for p in h.e.case['root'].rglob('*') if p.is_file()}
    actual = retry(h)
    assert actual['startEpoch'] == read_current(h.e.case['epoch'])
    assert actual['startEpoch']['state'] == 'FAILED_RETAINED'
    assert actual['readyEpoch'] == pinned_json(h.context)['readyEpoch']
    assert actual['authorization']['clearancePin'] == h.clearance
    observed = module().observe_retry_admission(h.e.owner, 'target57', source_ref='source57')
    assert observed['state'] == 'FAILED_RETAINED_RETRY_ADMITTED'
    assert observed['epoch'] == actual['startEpoch'] and observed['serverWrites'] is False
    assert observed['recoveryPointRef'] == h.e.request['recoveryPointRef']
    assert not (h.e.claim/'recovery-consumption.json').exists()
    assert all(p.read_bytes() == raw for p,raw in before.items())


@pytest.mark.parametrize('fault', ['source', 'point', 'old-operation', 'missing-purpose', 'mixed-purpose',
    'unconsumed', 'other-consumer', 'expired', 'target', 'context', 'original'])
def test_invalid_retry_authority_is_rejected_without_new_journal_events(retained, fault):
    h = retained; args = dict(purpose='RESTORE_REQUEST', recovery_point_ref='point1', operation_id='restore-2')
    if fault == 'source': args['source_ref'] = 'other'
    elif fault == 'point': args['recovery_point_ref'] = 'different'
    elif fault == 'old-operation': args['operation_id'] = 'restore-1'
    elif fault == 'missing-purpose': args['purpose'] = None
    elif fault == 'mixed-purpose': args['purpose'] = 'SOURCE_CANDIDATE'
    elif fault == 'unconsumed': args['purpose'] = 'CONSUMED_EXECUTION'
    elif fault == 'other-consumer':
        other = h.e.claim.parent/'other'; other.mkdir(mode=0o700)
        write(h.e.claim/'recovery-consumption.json', dict(schemaVersion='RetainedReplacementConsumption/v1',
            clearancePin=h.clearance, replacementOperationId='other', consumedAt=utc()))
    elif fault == 'expired':
        value = pinned_json(h.clearance); value['expiresAt'] = '2000-01-01T00:00:00Z'
        changed = write(Path(h.clearance['path']), value)
        release = write(h.e.root/'resource-recovery-release.json', dict(clearancePin=changed,
            reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
        write(h.e.claim/'recovery-ready.json', dict(clearancePin=changed, releasePin=release))
    elif fault == 'target': h.e.owner['targets']['target57']['database'] = 'other'
    elif fault == 'context': Path(h.context['path']).write_bytes(b'{}')
    else: Path(h.result_pin['path']).write_bytes(b'{}')
    events = list(Path(h.e.case['epoch']['root']).iterdir())
    with pytest.raises(Exception, match='PROGRAM_|RECOVERY_|MINIMAL_'):
        retry(h, **args)
    assert list(Path(h.e.case['epoch']['root']).iterdir()) == events


def test_public_generation_and_unqualified_target_still_require_ready(retained):
    from recovery_program_generation import resolve_target, resolve_capture
    from recovery_program_targets import resolve_configuration
    h = retained
    for call in (lambda: resolve_target(h.e.case['policy']),
        lambda: resolve_capture(h.e.case['policy'], 'source57', h.e.case['base_pin']),
        lambda: resolve_configuration(h.e.owner, 'target57')):
        with pytest.raises(Exception, match='PROGRAM_EPOCH_NOT_READY'): call()
    assert retry(h)['startEpoch']['state'] == 'FAILED_RETAINED'


@pytest.mark.parametrize('succeed', [True, False])
def test_real_v2_context_binding_native_stage_terminal_and_history(retained, succeed):
    import recovery_program_activation as activation
    import recovery_program_execution as execution
    h = retained
    # Only the external SQL protocol's live scheduler file is mutable. Every
    # original operation/claim and the original journal prefix remain exact.
    original = {p:p.read_bytes() for directory in (h.e.root, h.e.claim, Path(h.e.case['epoch']['root']))
        for p in directory.rglob('*') if p.is_file()}
    e = new_operation(h); c = h.c; c.e = e
    with locked(e.case) as fd:
        context = activation.snapshot_restore(e.case['policy'], 'restore-2', fd, owner=e.owner, request=e.request)
        value = pinned_json(context)
        assert value['schemaVersion'] == 'MainProgramRestoreContext/v2'
        assert value['startEpoch']['state'] == 'FAILED_RETAINED'
        binding = execution.bind_execution(e.owner, e.request, e.root, context, fd)
        started = start(e.case, e.claim, fd, operation='restore-2')
        event = pinned_json(started['eventPin'])
        assert event['previousSha256'] == value['startEpoch']['eventPin']['sha256']
        with MainNativeExecutionContext(e.owner, e.request, e.root, binding_pin=binding,
                lock_fd=fd, budget=Budget(120000)) as ctx:
            c.fd, c.saved, c.binding, c.ctx = fd, context, binding, ctx
            c.configuration, proof = execution.resolve_execution_configuration(e.owner, e.request, e.root,
                binding_pin=binding, lock_fd=fd)
            assert proof['epoch'] == started
            c.view = ctx.preparation(c.configuration); custody = []
            def prepare(native):
                custody.append(ProtectionCustody.from_preparation(native))
                if succeed: custody[0].view_for(native).scheduler.install()
                native.command(command(), mutation=False)
            c.at_native(prepare)
            if succeed:
                c.stage_switch_receipts()
                generation = activation.stage_generation(e.case['policy'], context,
                    target_pin=write(e.claim/'target.json', e.candidate),
                    capture_pins={'source57': write(e.claim/'capture.json', e.capture)},
                    switch_result_pin=e.switch, lock_fd=fd, owner=e.owner, request=e.request)
                ctx.stage(generation)
                (e.claim/'runtime').mkdir(mode=0o700)
                c.configuration, _ = execution.resolve_execution_configuration(e.owner, e.request, e.root,
                    binding_pin=binding, generation_pin=generation, lock_fd=fd, runtime=True)
                c.view = ctx.restore(c.configuration)
                def restore(native):
                    native.request['action'] = 'DATABASE_FULL'
                    sql, checksum = sql_transport(native, native.root/'retry-sql-stdin')
                    NativeData.import_sql(native, sql, checksum)
                    native.request['action'] = 'CONSISTENCY'
                    native.command(command(), mutation=False)
                    custody[0].release(native)
                c.at_native(restore)
            new = SimpleNamespace(e=e, c=c, binding=binding, context=context, native=ctx.snapshot(),
                custody=custody[0].snapshot(), phase=c.view.phase,
                state='SUCCEEDED' if succeed else 'FAILED_RETAINED')
    publish_envelopes(new)
    with locked(e.case) as fd:
        complete_restore(e.case['epoch'], 'restore-2', started['epochId'],
            'READY' if succeed else 'FAILED_RETAINED', new.receipt_pin, fd)
    verified = validate(new)
    assert verified['contextPin'] == context and verified['resultState'] == new.state
    assert validate_program_evidence(h.e.owner, h.e.request, h.e.root,
        result_pin=h.result_pin)['resultState'] == 'FAILED_RETAINED'
    assert all(p.read_bytes() == raw for p,raw in original.items())
    if not succeed:
        clear(new)
        with pytest.raises(Exception, match='PROGRAM_RETRY_PREDECESSOR_V2_UNSUPPORTED'):
            module().observe_retry_admission(e.owner, 'target57', source_ref='source57')


def test_packaged_retry_module_is_registered_before_delivery():
    root = Path(__file__).resolve().parents[2]
    import json
    files = json.loads((root/'ops/backup_engine/files.json').read_text(encoding='utf-8'))
    assert files.get('ops/recovery/recovery_program_retry.py') == 'common/recovery_program_retry.py'
    assert "payload['common/recovery_program_retry.py']" in (root/'ops/backup_engine/standard_fixes.py').read_text(encoding='utf-8')


@pytest.mark.parametrize('broken', [False, True])
def test_real_available_and_three_source_selections_do_not_hide_unknown_proof(retained, monkeypatch, broken):
    """Actual UI routing/resolver; external Docker identity is an explicit seam."""
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root/'backend/src/main/resources'))
    import recovery_control_target_availability as availability
    import recovery_control_restore_catalogue as catalogue
    from recovery_control_smallapp_native import Native
    from recovery_program_targets import resolve_restore_configuration
    import recovery_main_target as main
    import recovery_minimal_runtime as runtime
    h = retained
    owner = deepcopy(h.e.owner)
    owner['sources'].update(source58={'keep': True}, source59={'keep': True})
    owner_pin = write(h.e.case['root']/'selection-owner.json', owner)
    config = dict(registryRoot=str(h.e.case['root']/'empty-registry'), sourceConfigurations={},
        archiveRestoreCatalogues={s:{} for s in owner['sources']}, engineSelectionRef='explicit-unit',
        restoreConfigurations={s:{'target57':owner_pin} for s in owner['sources']})
    native = Native(owner_pin)
    # The actual STANDARD producer sets this explicit packaged capability;
    # this source-module route unit does not build/install an engine.
    monkeypatch.setattr(runtime, 'supports_main_target_preservation', True, raising=False)
    monkeypatch.setattr(native, 'configuration', lambda: config)
    monkeypatch.setattr(native, 'registrations', lambda _: [dict(applicationId=s, sourceConfigRef=s,
        allowedRestoreTargets=[{'configRef':'target57'}]) for s in owner['sources']])
    monkeypatch.setattr(catalogue, 'archive_references', lambda *_: {})
    monkeypatch.setattr(availability, 'unclaimed_target', lambda *a,**k: True)
    seen = []
    def external_identity(control, value, selection, *, purpose):
        assert purpose == 'SOURCE_CANDIDATE'
        result = resolve_restore_configuration(control.document(selection['ownerConfigurationPin']), 'target57',
            purpose=purpose, source_ref=value['sourceConfigRef'], reader=control.document)
        seen.append(value['sourceConfigRef'])
        return result
    monkeypatch.setattr(main, 'observe_main_target', external_identity)
    if broken:
        Path(h.result_pin['path']).write_bytes(b'{}')
        with pytest.raises(Exception):
            availability.available(native, owner_pin, 'target57', 'source58')
        return
    result = native.selections(selected_target='target57')
    assert [a['freshTargetConfigRefs'] for a in result['applications']] == [['target57'], [], []]
    assert all(a['historyErrorCode'] is None for a in result['applications'])
    assert seen == ['source57']


@pytest.mark.parametrize('raw,mode,fault', [
    pytest.param(b'ordinary-private-value', 0o400, None, id='secret400'),
    pytest.param(b'ordinary-private-value', 0o400, 'content', id='secret400-content'),
    pytest.param(b'\xff\x80\x00private-bytes', 0o400, None, id='nonutf8-secret400'),
    pytest.param(b'\xff\x80\x00private-bytes', 0o400, 'content', id='nonutf8-secret400-content'),
    pytest.param(b'\x7fELF'+bytes(50316), 0o755, None, id='tool755-50320bytes'),
    pytest.param(b'\x7fELF'+bytes(50316), 0o755, 'content', id='tool-content'),
    pytest.param(b'\x7fELF'+bytes(50316), 0o755, 'replacement', id='tool-replacement'),
    pytest.param(b'\x7fELF'+bytes(50316), 0o755, 'sha', id='tool-wrong-sha'),
    pytest.param(b'{"pin":"original"}', 0o600, 'sha', id='json-wrong-sha'),
])
def test_v2_native_lease_protects_opaque_original_pins_without_json_interpretation(history_factory, request, raw, mode, fault):
    """Actual retained evidence contains secret/tool bytes as well as JSON."""
    h = history_factory(outcome='retained', phases='preparation', install_protection=False)
    opaque = h.e.case['root']/'opaque-original-tool'; opaque.write_bytes(raw)
    if fault == 'content':
        writer = os.open(opaque, os.O_WRONLY | os.O_CLOEXEC)
        request.addfinalizer(lambda: os.close(writer))
    opaque.chmod(mode)
    reference = pin(opaque)
    if fault == 'sha': reference['sha256'] = '0'*64
    worker = pinned_json(h.result_pin); worker['originalResultPins'].append(reference)
    h.result_pin = write(Path(h.result_pin['path']), worker)
    clear(h); e = new_operation(h)
    import recovery_program_activation as activation
    import recovery_program_execution as execution
    with locked(e.case) as fd:
        context = activation.snapshot_restore(e.case['policy'], 'restore-2', fd, owner=e.owner, request=e.request)
        assert reference in pinned_json(context)['evidencePins']
        binding = execution.bind_execution(e.owner, e.request, e.root, context, fd)
        start(e.case, e.claim, fd, operation='restore-2')
        descriptors = len(os.listdir('/proc/self/fd'))
        if fault == 'sha':
            with pytest.raises(Exception, match='PROGRAM_DOCUMENT_CHANGED'):
                MainNativeExecutionContext(e.owner, e.request, e.root, binding_pin=binding,
                    lock_fd=fd, budget=Budget(120000))
        else:
            with MainNativeExecutionContext(e.owner, e.request, e.root, binding_pin=binding,
                    lock_fd=fd, budget=Budget(120000)) as ctx:
                assert str(opaque) in ctx._references
                if fault == 'content':
                    # A descriptor opened before readonly permissions still
                    # writes the real inode; its inotify event must be caught.
                    os.write(writer, b'changed opaque original')
                elif fault == 'replacement':
                    replacement = opaque.with_name('replacement-tool')
                    replacement.write_bytes(raw); replacement.chmod(mode)
                    replacement.replace(opaque)
                if fault is not None:
                    with pytest.raises(Exception, match='ARCHIVED_PAYLOAD_CHANGED'): ctx._check()
                else:
                    ctx._check()
        assert len(os.listdir('/proc/self/fd')) == descriptors
