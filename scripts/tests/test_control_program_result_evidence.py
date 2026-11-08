"""Control projections over real MAIN history, locks and local child processes.

This reuses the production-context history fixture. Owner/launcher envelopes and
Docker inspect replies are explicit external protocol fixtures, not claims of
a database restore or real Docker admission. No validator, context, reservation
or historical resolver is replaced by a successful stub. The Docker seam only
answers read-only inspect/info; DB probes and live resolution must never occur.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend/src/main/resources'))
sys.path.insert(0, str(ROOT/'ops/recovery'))
import recovery_control_smallapp_native as control
import recovery_main_target as main
from recovery_backup_epoch import complete_restore, read_current
from recovery_engine import RecoveryError, pin, pinned_json
from recovery_program_evidence import validate_program_evidence
from test_recovery_program_activation import locked, claim, snapshot, start, stage, finish
from test_recovery_program_containers import original
from test_recovery_program_evidence import history_factory, evidence_files, COMMON
from test_recovery_program_generation import write
from test_native_import_process_evidence import evidence as legacy_process
from test_native_oom_target import target as legacy_target
import test_recovery_program_evidence as history_fixture
import test_recovery_program_native_constructor as constructor_fixture

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='real private metadata, flock and Linux process identities')


def closed_process(code):
    child = subprocess.Popen([sys.executable, '-B', '-c', 'import sys; sys.exit('+str(code)+')'])
    assert child.wait(timeout=10) == code
    return child.pid


@pytest.fixture
def control_history(history_factory, monkeypatch):
    """Complete the *input fixture* before original reservation/binding exist."""
    actual_case = constructor_fixture.case.__wrapped__
    actual_write = constructor_fixture.write
    rows_by_root = {}

    def case(root):
        value = actual_case(root)
        target = value['target']
        target.update(dockerEngineId='control-test-engine', buckets=['yudao'],
            redisRebuild={'database': 0}, application={'startOrder': ['backend', 'frontend']})
        target['replacement']['schemaVersion'] = 'RegisteredApplicationReplacement/v2'
        registered = target['mainApplication']
        registered.update(schemaVersion='RegisteredMainApplication/v1', configurationPins=[])
        registered['archiveImageBindings'] = [entry for entry in registered['archiveImageBindings']
            if entry['role'] in ('backend', 'frontend')]
        registered['writerAdmission'].update(schemaVersion='RegisteredMainWriterCustody/v1',
            exclusiveResources=dict(database=True, objects=True, redis=True))
        rows = {}
        for service in target['services']:
            row = original()
            row.update(Id=service['id'], Image=service['imageId'], Name='/control-'+service['role'])
            attachment = row['NetworkSettings']['Networks']['task-network']
            attachment.update(IPAddress=service['ip'], IPAMConfig={'IPv4Address': service['ip']},
                Aliases=[service['role'], service['id'][:12]])
            rows[row['Id']] = row
            registered['serviceConfigurationDigests'][service['role']] = main.service_configuration_digest(row)
            registered['networkAttachments'][service['role']] = main.network_attachments(row)
            target['replacement']['services'][service['role']].update(
                labels=deepcopy(row['Config']['Labels']), mounts=deepcopy(row['Mounts']))
        network = dict(Id='f'*64, Name='task-network', Driver='bridge', Internal=False,
            EnableIPv6=False, IPAM={'Driver': 'default', 'Config': []}, Options={}, Labels={}, Containers={})
        registered['networks'] = [main.network_configuration(network, list(rows))]
        rows_by_root[root] = (rows, network)
        return value

    def owner_write(path, value):
        if path.name == 'configuration.json':
            # This is the fixture's first owner write, before reserve() is real.
            value['schemaVersion'] = 'RecoveryMinimalConfiguration/v1'
        return actual_write(path, value)

    monkeypatch.setattr(constructor_fixture, 'case', SimpleNamespace(__wrapped__=case))
    monkeypatch.setattr(constructor_fixture, 'write', owner_write)

    def build(**kwargs):
        h = history_factory(**kwargs)
        main.validate(h.e.owner['targets']['target57'])
        main.validate(h.e.candidate)
        directory = h.e.case['root']/'control-ledger'
        execute = directory/'execute'; execute.mkdir(mode=0o700, parents=True)
        directory.chmod(0o700)
        selection = dict(ownerConfigurationPin=h.e.owner_pin,
            ownerProgramPin=pin(ROOT/'ops/recovery/recovery_minimal_worker.py'),
            configurationPin=h.e.owner_pin)
        request_pin = write(directory/'request.json', h.e.request)
        output = pinned_json(h.result_pin)
        output['message'] = 'Explicit local owner-result protocol fixture'
        if output['state'] == 'SUCCEEDED':
            # The control/resource adapter needs the complete owner envelope.
            # These are labelled producer protocol inputs, never DB/UI success.
            materials = {name: write(directory/(name+'.json'), dict(
                schemaVersion='ControlOwnerMaterialProtocolFixture/v1',
                operationId=h.e.request['operationId'], boundary=name, actualBusinessRestore=False))
                for name in ('database', 'objects', 'consistency', 'derived', 'application-start')}
            output['data'].update(targetConfigRef='target57', orderedChainPins=[h.e.chain[0][0]],
                databaseResultPins=[materials['database']], objectResultPins=[materials['objects']],
                consistencyPin=materials['consistency'], derivedPin=materials['derived'],
                applicationStartPin=materials['application-start'])
            output['originalResultPins'].extend(materials.values())
        child_pin = write(h.e.root/'child-exit.json', dict(operationId=h.e.request['operationId'],
            actualExitCode=output['actualExitCode'], timedOut=False))
        output['originalResultPins'].append(child_pin)
        write(h.e.root/'worker-result.json', output)
        result_pin = write(h.e.root/'result.json', output)
        intent_pin = write(execute/'native-intent.json', dict(operationId=h.e.request['operationId'],
            requestId=h.e.request['operationId'], requestPin=request_pin,
            configurationPin=selection['ownerConfigurationPin'], programPin=selection['ownerProgramPin']))
        pid = closed_process(output['actualExitCode'])
        write(execute/'native-process.json', dict(operationId=h.e.request['operationId'],
            requestId=h.e.request['operationId'], intentPin=intent_pin, pid=pid,
            bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip()))
        write(execute/'native-original-exit.json', dict(operationId=h.e.request['operationId'],
            requestId=h.e.request['operationId'], requestPin=request_pin, intentPin=intent_pin,
            pid=pid, actualExitCode=output['actualExitCode'], timedOut=False, resultPin=result_pin))
        rows, network = rows_by_root[h.e.case['root']]
        h.result_pin = result_pin
        proof = validate_program_evidence(h.e.owner, h.e.request, h.e.root, result_pin=result_pin)
        return SimpleNamespace(h=h, value=h.e.request, output=output, selection=selection,
            directory=directory, result_pin=result_pin, proof=proof, rows=rows, network=network,
            native=control.Native.__new__(control.Native))
    return build


def no_live_resolution(monkeypatch):
    import recovery_program_execution as execution
    import recovery_program_generation as generation
    import recovery_program_targets as targets
    def forbidden(*args, **kwargs):
        raise AssertionError('historical query attempted live resolution or DB probe')
    monkeypatch.setattr(execution, 'resolve_execution_configuration', forbidden)
    monkeypatch.setattr(generation, 'resolve_target', forbidden)
    monkeypatch.setattr(targets, 'resolve_configuration', forbidden)
    monkeypatch.setattr(main, 'mysql_query', forbidden)
    monkeypatch.setattr(main, 'verify_redis_authentication', forbidden)


def load(c):
    return c.native.operation_output(c.value, c.result_pin, selection=c.selection)


def physical_protocol(c, monkeypatch):
    """Docker snapshots only: all control checks remain production code."""
    no_live_resolution(monkeypatch)
    rows = deepcopy(c.rows)
    generation = pinned_json(c.proof['generationPin'])
    switched = pinned_json(generation['switchResultPin'])
    retained, created = [], []
    originals = {}
    for role, reference in switched['applicationPins'].items():
        entry = pinned_json(reference)
        originals[entry['original']['Id']] = entry['original']
        for kind, identities in (('retained', retained), ('created', created)):
            row = deepcopy(entry[kind]); rows[row['Id']] = row; identities.append(row['Id'])
    for row in rows.values():
        row['State'].update(Pid=0, Running=False, Paused=False, Restarting=False,
            OOMKilled=False, ExitCode=0)
        row['ExecIDs'] = None
    seen = []
    target = c.h.e.owner['targets']['target57']
    read_text = Path.read_text
    def text(path, *args, **kwargs):
        if path == Path('/etc/machine-id'): return target['machineId']
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', text)
    def run(argv, **kwargs):
        assert argv[:3] == [target['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock']
        command = argv[3:]
        if command == ['info', '--format', '{{json .}}']:
            value = {'ID': target['dockerEngineId']}
        elif command[:1] == ['inspect']:
            assert command[1:] and all(identity in rows for identity in command[1:])
            seen.extend(command[1:]); value = [deepcopy(rows[identity]) for identity in command[1:]]
        elif command[:2] == ['network', 'inspect']:
            assert command[2:] in (['f'*64], ['task-network'])
            value = [deepcopy(c.network)]
        else:
            raise AssertionError('only read-only Docker identity protocol is allowed: '+repr(command))
        return SimpleNamespace(returncode=0, stdout=json.dumps(value).encode('utf-8'), stderr=b'')
    monkeypatch.setattr(control, 'subprocess', SimpleNamespace(run=run, PIPE=subprocess.PIPE))
    before_rows = {identity: deepcopy(row) for identity, row in rows.items() if identity not in created}
    before_rows.update(deepcopy(originals))
    observed = {}
    for service in target['services']:
        row = before_rows[service['id']]
        networks = {name: item['networkId'] for name, item in main.network_attachments(row).items()}
        observed[service['id']] = dict(role=service['role'], imageId=row['Image'],
            labels=row['Config']['Labels'], mounts=row['Mounts'], networks=networks,
            networkAttachments=networks, configuredNetworkMode=row['HostConfig']['NetworkMode'],
            configurationDigest=main.service_configuration_digest(row), state=row['State'], execIds=None)
    before = write(c.directory/'restore-target-before.json', dict(operationId=c.value['operationId'],
        targetConfigRef='target57', configurationPin=c.selection['ownerConfigurationPin'],
        targetId=target['targetId'], machineId=target['machineId'], dockerEngineId=target['dockerEngineId'],
        bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(), services=observed))
    path = c.directory/'execute/native-intent.json'
    intent = pinned_json(pin(path)); intent['restoreTargetPin'] = before; intent_pin = write(path, intent)
    for name in ('native-process.json', 'native-original-exit.json'):
        path = c.directory/'execute'/name
        row = pinned_json(pin(path)); row['intentPin'] = intent_pin; write(path, row)
    return rows, seen, retained, created


def test_success_history_after_real_reservation_release_needs_no_live_context(control_history, monkeypatch):
    c = control_history()
    from recovery_resource_admission import release_success
    release_success(c.h.e.owner, c.value, c.h.e.root,
        pin(c.h.e.root/'worker-result.json'), pin(c.h.e.root/'child-exit.json'))
    assert not (c.h.e.case['root']/'resource-host/active.json').exists()
    before = evidence_files(c.h.e.case['root'])
    no_live_resolution(monkeypatch)
    output = load(c)
    assert output == c.output
    assert c.native.operation_result(c.value, output)['state'] == 'SUCCEEDED'
    assert evidence_files(c.h.e.case['root']) == before


def test_known_program_failure_is_read_from_complete_two_phase_originals(control_history, monkeypatch):
    c = control_history(outcome='sql-failure')
    before = evidence_files(c.h.e.case['root'])
    no_live_resolution(monkeypatch)
    output = load(c)
    assert output == c.output and c.native.operation_result(c.value, output)['state'] == 'FAILED'
    assert any(Path(row['terminalPin']['path']).is_relative_to(c.h.e.claim/'runtime')
        for row in c.proof['invocations'] if row['terminalPin'] is not None)
    assert evidence_files(c.h.e.case['root']) == before


def test_original_program_policy_cannot_be_bypassed_by_deleted_fields_or_missing_selection(control_history):
    c = control_history()
    for field in COMMON: c.output['data'].pop(field)
    c.result_pin = write(c.h.e.root/'result.json', c.output)
    before = evidence_files(c.h.e.case['root'])
    with pytest.raises((RuntimeError, RecoveryError), match='PROGRAM_|ORIGINAL_'):
        load(c)
    with pytest.raises((RuntimeError, RecoveryError), match='PROGRAM_|ORIGINAL_'):
        c.native.operation_output(c.value, c.result_pin)
    assert evidence_files(c.h.e.case['root']) == before


def test_equivalent_result_outside_fixed_original_directory_is_rejected(control_history):
    c = control_history()
    copied = write(c.directory/'copied-result.json', c.output)
    before = evidence_files(c.h.e.case['root'])
    with pytest.raises((RuntimeError, RecoveryError), match='PROGRAM_.*(LOCATION|RESULT)|ORIGINAL_'):
        c.native.operation_output(c.value, copied, selection=c.selection)
    assert evidence_files(c.h.e.case['root']) == before


def test_later_generation_does_not_replace_old_operation_target(control_history, monkeypatch):
    c = control_history()
    e = c.h.e; original_generation = pinned_json(c.proof['generationPin'])
    with locked(e.case) as fd:
        root = claim(e.case, 'restore-2'); context = snapshot(e.case, fd, 'restore-2')
        epoch = start(e.case, root, fd, operation='restore-2')
        successor_target = write(root/'target.json', pinned_json(original_generation['targetPin']))
        generation = stage(e.case, context, fd, target_pin=successor_target,
            capture_pins={name: row['capturePin'] for name, row in original_generation['captureBindings'].items()},
            switch_result_pin=None)
        finish(e.case, root, epoch, generation, fd)
    before = evidence_files(e.case['root'])
    no_live_resolution(monkeypatch)
    assert c.native.operation_result(c.value, load(c))['state'] == 'SUCCEEDED'
    proof = validate_program_evidence(e.owner, c.value, e.root, result_pin=c.result_pin)
    assert proof['targetPin'] == c.proof['targetPin'] and proof['targetPin'] != successor_target
    assert evidence_files(e.case['root']) == before


def test_published_generation_in_preparation_checks_both_retained_and_created_apps(control_history, monkeypatch):
    c = control_history(outcome='generation-before-stage')
    assert c.proof['phase'] == 'PREPARATION' and c.proof['generationPin'] is not None
    rows, seen, retained, created = physical_protocol(c, monkeypatch)
    before = evidence_files(c.h.e.case['root'])
    observed = c.native.stopped_retained_target(c.value, c.directory, c.selection, result_pin=c.result_pin)
    assert observed['partialTargetRetained'] is True
    assert set(retained+created) <= set(seen)
    for identity in (retained[0], created[0]):
        rows[identity]['State'].update(Running=True, Pid=os.getpid())
        with pytest.raises((RuntimeError, RecoveryError), match='WRITER|STOPPED|RUNNING|UNRESOLVED'):
            c.native.stopped_retained_target(c.value, c.directory, c.selection, result_pin=c.result_pin)
        rows[identity]['State'].update(Running=False, Pid=0)
    assert evidence_files(c.h.e.case['root']) == before


def test_program_unknown_never_uses_legacy_timeout_or_releases_reservation(control_history, monkeypatch):
    c = control_history(outcome='unknown')
    c.output['failureCode'] = 'ORIGINAL_CHILD_TIMEOUT'
    c.result_pin = write(c.h.e.root/'result.json', c.output)
    before = evidence_files(c.h.e.case['root'])
    called = []
    def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError('program unknown cannot use legacy timeout/release')
    import recovery_resource_admission as admission
    monkeypatch.setattr(c.native, 'restore_timeout_stopped', forbidden)
    monkeypatch.setattr(admission, 'release_retained_failure', forbidden)
    monkeypatch.setattr(admission, 'release_proven_oom', forbidden)
    no_live_resolution(monkeypatch)
    reply = c.native.refresh_original(c.value, c.directory, c.selection)
    assert reply['state'] == 'RUNNING' and reply['errorCode'] == 'ORIGINAL_CHILD_TIMEOUT'
    assert called == [] and (c.h.e.case['root']/'resource-host/active.json').exists()
    assert all(Path(path).read_bytes() == raw for path, raw in before.items())


def test_live_detached_process_blocks_program_stop_despite_completed_records(control_history, monkeypatch, tmp_path):
    marker = tmp_path/'hold-next-identical-command'
    argv = [sys.executable, '-B', '-c',
        'import pathlib,time; p=pathlib.Path('+repr(str(marker))+'); '
        'exec("while p.exists(): time.sleep(0.05)")']
    monkeypatch.setattr(history_fixture, 'command', lambda: list(argv))
    c = control_history(outcome='sql-failure')
    marker.write_bytes(b'hold'); marker.chmod(0o600)
    child = subprocess.Popen(argv, start_new_session=True)
    try:
        assert child.poll() is None
        before = evidence_files(c.h.e.case['root'])
        no_live_resolution(monkeypatch)
        with pytest.raises((RuntimeError, RecoveryError), match='ORIGINAL_NATIVE_CALL_STILL_RUNNING'):
            c.native.stopped_import_processes(c.value, c.directory, c.h.e.root, c.output,
                expected_exit=1, selection=c.selection, result_pin=c.result_pin)
        assert evidence_files(c.h.e.case['root']) == before
    finally:
        child.terminate(); child.wait(timeout=10)


def test_worker_failure_preserves_successful_replacement_receipt(control_history, monkeypatch):
    c = control_history(complete_epoch=False)
    e = c.h.e; receipt_before = Path(c.h.receipt_pin['path']).read_bytes()
    with locked(e.case, held=False) as fd:
        current = read_current(e.case['epoch'])
        with pytest.raises(ValueError, match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
            complete_restore(e.case['epoch'], c.value['operationId'], current['epochId'],
                'READY', c.h.receipt_pin, fd)
    c.output.update(state='FAILED_RETAINED', failureCode='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED', actualExitCode=1)
    c.output['data'].update(partialTargetRetained=True, retryPermitted=False)
    c.result_pin = write(e.root/'result.json', c.output)
    no_live_resolution(monkeypatch)
    reply = c.native.operation_result(c.value, load(c))
    assert reply['state'] == 'FAILED' and reply['errorCode'] == 'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'
    assert Path(c.h.receipt_pin['path']).read_bytes() == receipt_before
    assert pinned_json(c.h.receipt_pin)['state'] == 'SUCCEEDED'


def test_legacy_v1_process_branch_keeps_pin_and_live_pid_rejections(legacy_process, legacy_target):
    native, value, directory, root, output = legacy_process
    value['targetConfigRef'] = 'target'
    request_pin = write(directory/'request.json', value)
    intent_path = directory/'execute/native-intent.json'
    intent = pinned_json(pin(intent_path)); intent['requestPin'] = request_pin
    intent_pin = write(intent_path, intent)
    for name in ('native-process.json', 'native-original-exit.json'):
        path = directory/'execute'/name
        row = pinned_json(pin(path)); row['intentPin'] = intent_pin
        if name == 'native-original-exit.json': row['requestPin'] = request_pin
        write(path, row)
    selection = legacy_target[2]
    assert 'targetProgramPolicies' not in control.executor.document(selection['ownerConfigurationPin'])
    original_result = write(root/'result.json', output)
    assert native.stopped_import_processes(value, directory, root, output,
        selection=selection, result_pin=original_result)
    process_path = directory/'execute/native-process.json'
    process = control.executor.document(control.executor.pin(process_path))
    process['pid'] = os.getpid(); write(process_path, process)
    exit_path = directory/'execute/native-original-exit.json'
    exited = control.executor.document(control.executor.pin(exit_path))
    exited['pid'] = os.getpid(); write(exit_path, exited)
    with pytest.raises(RuntimeError, match='ORIGINAL_OWNER_PROCESS_STILL_PRESENT'):
        native.stopped_import_processes(value, directory, root, output,
            selection=selection, result_pin=original_result)
