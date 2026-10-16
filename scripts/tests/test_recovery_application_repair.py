"""V4 affected engineering regressions; no business/runtime acceptance."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import json
import os
import signal
import subprocess
import sys
import time
import pytest

from test_recovery_environment_fixtures import LocalRecords, MODULE
import recovery_application_mechanism as mechanism
import recovery_application as application
import recovery_environment_runtime as runtime_module
from recovery_application_protection import observe_mechanism_failure, protect_application, validate_recovery_launch
from recovery_environment import run_operation
from recovery_environment_contract import EnvironmentFailure, read_pin, pin_file
from recovery_environment_runtime import CommandRunner, NativeDocker


def _selected_protection_operation(tmp_path, monkeypatch, program_source):
    records = LocalRecords(tmp_path)
    program = records.material / "unit-nested-failure.py"
    program.write_text(program_source, encoding="utf-8")
    app_pin = records.write("unit-protection-config.json", {"artifactSha256": "a" * 64})
    mount = {"pin": app_pin, "target": "/run/recovery/protection.json"}
    backend = next(s for s in records.services if s['role'] == 'backend')
    backend['configurationMounts'] = [mount]
    backend['env']['JAVA_TOOL_OPTIONS'] = (
        "-Dintruoyi.recovery.protection.path=" + mount['target'] +
        " -Dintruoyi.recovery.protection.sha256=" + app_pin['sha256'] +
        " -Dintruoyi.maintenance.boot.artifactSha256=" + "a" * 64)
    records.configuration['serviceEnvironment']['backend'] = deepcopy(backend['env'])
    records.config['configurationPin'] = records.write('unit-launch.json', records.configuration)
    records.config['pythonPin'] = pin_file(sys.executable)
    records.config['materialRoots'].append(str(Path(sys.executable).parent))
    spec = read_pin(records.policy['applicationWriteProtectionPin'])
    spec.update(mechanismId='INT_RUOYI_RECOVERY_PROTECTION_V3', enforceScriptPin=pin_file(program),
                observeScriptPin=pin_file(program), configurationPin=records.config['configurationPin'])
    records.policy['applicationWriteProtectionPin'] = records.write('unit-selected-protection.json', spec)
    records.approve()
    records.request['action'] = 'START_APPLICATION'
    records.request['inputPins'] = {'restoreExecutionResult': records.sample, 'recoveryTarget': records.sample}
    selected = records.write('unit-mechanism-config.json', {
        'schemaVersion': 'RecoveryApplicationMechanismConfig/v1',
        'operationId': records.request['operationId'], 'restoreId': 'unit-restore',
        'targetIdentityPin': records.config['targetIdentityPin'], 'recoveryPoint': 'unit-point',
        'policyPin': records.policy['applicationWriteProtectionPin'],
        'configurationPin': records.config['configurationPin'], 'imagePins': records.config['imagePins'],
        'applicationConfigPin': app_pin, 'mounts': [mount]})
    monkeypatch.setenv('RECOVERY_APPLICATION_MECHANISM_CONFIG_PIN', json.dumps(selected))
    class Runtime:
        def __init__(self, config, policy, runner, operation):
            self.runner = runner
            self.identities = {'redis': 'a' * 64, 'mysql': 'b' * 64, 'minio': 'c' * 64}
    def start(request, config, policy, trust, runtime, private):
        protect_application(request, config, policy, runtime,
                            {'restoreId': 'unit-restore', 'recoveryPoint': 'unit-point'}, 'AFTER_START')
        pytest.fail('failed protection must not start an application')
    monkeypatch.setattr(application, 'start_application', start)
    return records, Runtime


@pytest.mark.parametrize("unknown", [True, False])
@pytest.mark.parametrize('receipt_failure', [None, 'WRITE', 'PIN'])
def test_nested_effect_failure_reaches_outer_receipt_and_persistent_target_gate(tmp_path, monkeypatch, unknown, receipt_failure):
    records, Runtime = _selected_protection_operation(tmp_path, monkeypatch,
        "import sys,json,pathlib\n"
        f"sys.path.insert(0,{str(MODULE)!r})\n"
        "from recovery_application_mechanism import Executor,ProtectionFailure,canonical,BINDINGS\n"
        "r=json.load(sys.stdin); root=pathlib.Path(__file__).parent/'nested-originals'; root.mkdir()\n"
        "e=Executor(r,{},root)\n"
        "try:\n"
        f" e.run([sys.executable,'-I','-c','raise SystemExit(7)'],mutation=True,effect_kind={'DAEMON' if unknown else 'LOCAL'!r})\n"
        "except ProtectionFailure as f:\n"
        " result={'schemaVersion':'RecoveryApplicationProtectionFailure/v1','state':'TERMINAL_UNKNOWN' if f.unknown else 'FAILED_RETAINED',"
        "'code':f.code,'bindings':{k:r[k] for k in ('phase',*BINDINGS,'containers')},'originalInvocationPins':e.invocations,'failureEvidencePins':e.evidence_pins}\n"
        " sys.stdout.buffer.write(canonical(result)); raise SystemExit(2)\n")
    writes, pins = runtime_module.atomic_json, runtime_module.pin_file
    def write(path, value):
        if receipt_failure == 'WRITE' and path.name == 'invocation-0001.json' and value['finishedAt'] is not None:
            raise OSError('unit-outer-terminal-write')
        return writes(path, value)
    def take_pin(path):
        if receipt_failure == 'PIN' and path.name == 'invocation-0001.json':
            raise EnvironmentFailure('UNIT_OUTER_TERMINAL_PIN')
        return pins(path)
    monkeypatch.setattr(runtime_module, 'atomic_json', write)
    monkeypatch.setattr(runtime_module, 'pin_file', take_pin)
    result = run_operation(records.request, records.trust, time.monotonic() + 20, runtime_factory=Runtime)
    expected = 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED'
    assert result['state'] == expected and result['actualExitCode'] == 2
    assert result['failureCode'] == ('PROTECTION_NATIVE_EFFECT_TERMINAL_UNPROVEN' if unknown else
        'PROTECTION_NATIVE_EXECUTION_FAILED' if receipt_failure is None else 'INVOCATION_TERMINAL_' + receipt_failure + '_FAILED')
    originals = [read_pin(p) for p in result['originalResultPins']]
    if receipt_failure is None:
        receipt = next(p for p in originals if p['schemaVersion'] == 'RecoveryEnvironmentInvocation/v1')
    else:
        fault = next(p for p in originals if p['schemaVersion'] == 'RecoveryEnvironmentInvocationPersistenceFailure/v1')
        assert fault['stage'] == receipt_failure and fault['state'] == expected and fault['originalState'] == expected
        assert fault['originalFailureCode'] == ('PROTECTION_NATIVE_EFFECT_TERMINAL_UNPROVEN' if unknown else 'PROTECTION_NATIVE_EXECUTION_FAILED')
        receipt = fault['receipt']
    failure = next(p for p in originals if p['schemaVersion'] == 'RecoveryApplicationProtectionFailure/v1')
    assert receipt['state'] == expected and receipt['actualExitCode'] == 2 and receipt['pid'] > 0
    assert receipt['localProcessState'] == 'TERMINATED'
    inner = read_pin(failure['originalInvocationPins'][0])
    assert inner['pid'] > 0 and inner['actualExitCode'] == 7 and inner['localProcessTerminated'] is True
    assert inner['state'] == expected
    assert all(json.loads(p.read_text())['state'] == expected for p in (tmp_path / 'journal').glob('*.json'))
    records.request['requestId'] = 'different-request-same-target'
    if unknown:
        with pytest.raises(EnvironmentFailure, match='TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN') as refused:
            run_operation(records.request, records.trust, time.monotonic() + 20, runtime_factory=Runtime)
        assert refused.value.unknown
    else:
        # A known failure does not block admission; stop before further execution.
        monkeypatch.setattr(application, 'start_application', lambda *a: (_ for _ in ()).throw(EnvironmentFailure('UNIT_ADMITTED')))
        admitted = run_operation(records.request, records.trust, time.monotonic() + 20, runtime_factory=Runtime)
        assert admitted['failureCode'] == 'UNIT_ADMITTED' and admitted['state'] == 'FAILED_RETAINED'


@pytest.mark.parametrize('receipt_failure', ['WRITE', 'PIN'])
@pytest.mark.parametrize('local_state', ['not_started', 'terminated_failure', 'terminated_success'])
def test_outer_terminal_persistence_failure_keeps_proven_local_states_distinct(tmp_path, monkeypatch, receipt_failure, local_state):
    writes, pins = runtime_module.atomic_json, runtime_module.pin_file
    def write(path, value):
        if receipt_failure == 'WRITE' and path.name == 'invocation-0001.json' and value['finishedAt'] is not None:
            raise OSError('unit-outer-terminal-write')
        return writes(path, value)
    def take_pin(path):
        if receipt_failure == 'PIN' and path.name == 'invocation-0001.json':
            raise EnvironmentFailure('UNIT_OUTER_TERMINAL_PIN')
        return pins(path)
    monkeypatch.setattr(runtime_module, 'atomic_json', write)
    monkeypatch.setattr(runtime_module, 'pin_file', take_pin)
    runner = CommandRunner(tmp_path, time.monotonic() + 5, lambda: None)
    if local_state == 'not_started':
        monkeypatch.setattr(runtime_module.subprocess, 'Popen', lambda *a, **k: pytest.fail('invalid binding spawned'))
    options = {'environment_bindings': {'INVALID_UNIT_BINDING': 'unit'}} if local_state == 'not_started' else {}
    with pytest.raises(EnvironmentFailure) as failed:
        runner.run([sys.executable, '-I', '-c', 'raise SystemExit(0)' if local_state == 'terminated_success' else 'raise SystemExit(7)'], **options)
    assert failed.value.unknown is False
    assert failed.value.code == 'INVOCATION_TERMINAL_' + receipt_failure + '_FAILED'
    fault = read_pin(runner.pins[-1]); receipt = fault['receipt']
    assert fault['state'] == 'FAILED_RETAINED' and fault['stage'] == receipt_failure
    assert receipt['actualExitCode'] == runner.last_exit == (None if local_state == 'not_started' else 0 if local_state == 'terminated_success' else 7)
    assert receipt['localProcessState'] == ('NOT_STARTED' if local_state == 'not_started' else 'TERMINATED')


@pytest.mark.parametrize('termination_available', [True, False])
def test_readonly_inner_unproved_exit_survives_final_record_failures_and_blocks_replay(tmp_path, monkeypatch, termination_available):
    records, Runtime = _selected_protection_operation(tmp_path, monkeypatch, f"""import sys,pathlib,subprocess
sys.path.insert(0,{str(MODULE)!r})
import recovery_application_mechanism as m
real_popen=m.subprocess.Popen; real_write=m.write_json; children=[]
class UnobservedProcess:
 def __init__(self,*a,**k):
  self.child=real_popen(*a,**k); self.pid=self.child.pid; children.append(self.child)
 @property
 def returncode(self): return self.child.returncode
 def poll(self): return self.child.poll()
 def kill(self): return self.child.kill()
 def communicate(self,*a,**k): raise subprocess.TimeoutExpired('unit-unobserved-child',0)
def injected_write(path,value):
 if path.name.startswith('invocation-') or ({not termination_available!r} and path.name.startswith('termination-')):
  raise OSError('unit-inner-final-record')
 return real_write(path,value)
def execute(request,context):
 root=pathlib.Path(__file__).parent/'nested-originals'; root.mkdir()
 executor=m.Executor(request,{{}},root); context['executor']=executor
 m.subprocess.Popen=UnobservedProcess; m.write_json=injected_write
 try:
  executor.run([sys.executable,'-I','-c','import time; time.sleep(30)'],mutation=False,effect_kind='DAEMON')
 finally:
  m.subprocess.Popen=real_popen; m.write_json=real_write
  for child in children:
   if child.poll() is None: child.kill()
   child.communicate(timeout=5)
  # Test-only cleanup occurs after Executor's failed terminal observation.
  real_write(root/'unit-test-cleanup.json',{{'actualPid':children[0].pid,'actualExitCode':children[0].returncode}})
m.execute_protection=execute
raise SystemExit(m.main())
""")
    result = run_operation(records.request, records.trust, time.monotonic() + 20, runtime_factory=Runtime)
    assert result['state'] == 'TERMINAL_UNKNOWN' and result['actualExitCode'] == 2
    assert result['failureCode'] == ('PROTECTION_FINAL_EVIDENCE_NOT_PERSISTED' if termination_available else 'PROTECTION_TERMINATION_EVIDENCE_NOT_PERSISTED')
    originals = [read_pin(p) for p in result['originalResultPins']]
    failure = next(p for p in originals if p['schemaVersion'] == 'RecoveryApplicationProtectionFailure/v1')
    assert failure['state'] == 'TERMINAL_UNKNOWN' and failure['originalInvocationPins'] == []
    evidence = {Path(p['path']).name: read_pin(p) for p in failure['failureEvidencePins']}
    assert set(evidence) == {'intention-000.json', 'running-000.json'} | ({'termination-000.json'} if termination_available else set())
    running = evidence['running-000.json']
    assert running['mutation'] is False and running['pid'] > 0 and running['actualExitCode'] is None
    if termination_available:
        terminal = evidence['termination-000.json']
        assert terminal['state'] == 'TERMINAL_UNKNOWN' and terminal['actualExitCode'] is None
        assert terminal['localProcessTerminated'] is False and terminal['pid'] == running['pid']
    cleanup = json.loads((records.material / 'nested-originals' / 'unit-test-cleanup.json').read_text())
    assert cleanup['actualPid'] == running['pid'] and type(cleanup['actualExitCode']) is int
    assert all(json.loads(p.read_text())['state'] == 'TERMINAL_UNKNOWN' for p in (tmp_path / 'journal').glob('*.json'))
    records.request['requestId'] = 'different-request-same-target'
    with pytest.raises(EnvironmentFailure, match='TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN') as refused:
        run_operation(records.request, records.trust, time.monotonic() + 20, runtime_factory=Runtime)
    assert refused.value.unknown


@pytest.mark.parametrize('point', ['connect', 'request', 'response', 'read', 'refused'])
def test_http_worker_distinguishes_predispatch_response_loss_and_confirmed_refusal(monkeypatch, point):
    calls = []
    class Response:
        status = 403
        def read(self, bound):
            if point == 'read': raise ConnectionResetError('unit-only')
            return mechanism.canonical({'code': 403, 'msg': 'RECOVERY_WRITE_DENIED', 'scope': 'APPLICATION_MUTATIONS'})
    class Connection:
        def __init__(self, *a, **k): pass
        def connect(self):
            calls.append('connect')
            if point == 'connect': raise ConnectionRefusedError('unit-only')
        def request(self, *a, **k):
            calls.append('POST')
            if point == 'request': raise ConnectionResetError('unit-only')
        def getresponse(self):
            if point == 'response': raise ConnectionResetError('unit-only')
            return Response()
        def close(self): calls.append('close')
    output = BytesIO()
    spec = {'host': '172.29.240.4', 'port': 8080, 'path': '/admin-api/infra/file/upload',
            'body': {}, 'secret': None, 'seconds': 2}
    monkeypatch.setattr(mechanism.http.client, 'HTTPConnection', Connection)
    monkeypatch.setattr(mechanism.sys, 'stdin', SimpleNamespace(buffer=BytesIO(mechanism.canonical(spec))))
    monkeypatch.setattr(mechanism.sys, 'stdout', SimpleNamespace(buffer=output))
    exit_code = mechanism.http_worker()
    result = mechanism.decode(output.getvalue())
    assert calls.count('POST') == (0 if point == 'connect' else 1)
    if point == 'refused': assert exit_code == 0 and result['status'] == 403
    else:
        assert exit_code == 2
        assert result['state'] == ('FAILED_RETAINED' if point == 'connect' else 'TERMINAL_UNKNOWN')
        assert 'beforeFingerprints' not in result and 'denied' not in result


@pytest.mark.parametrize('unknown', [True, False])
def test_http_failure_retains_real_local_exit_and_effect_state(tmp_path, unknown):
    executor = mechanism.Executor({'deadlineMilliseconds': 5000}, {}, tmp_path)
    observation = {'schemaVersion': 'RecoveryProtectionHttpFailure/v1',
        'state': 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED',
        'code': 'PROTECTION_HTTP_EFFECT_TERMINAL_UNPROVEN' if unknown else 'PROTECTION_HTTP_PRE_DISPATCH_FAILED',
        'dispatchState': 'MAY_HAVE_DISPATCHED' if unknown else 'NOT_DISPATCHED'}
    program = "import json; print(" + repr(json.dumps(observation)) + "); raise SystemExit(2)"
    with pytest.raises(mechanism.ProtectionFailure) as failed:
        executor.run([sys.executable, '-I', '-c', program], mutation=True, effect_kind='HTTP',
                     failure_observer=lambda raw: mechanism.decode(raw))
    assert failed.value.unknown is unknown
    receipt = mechanism.read_pin(executor.invocations[-1])
    assert receipt['actualExitCode'] == 2 and receipt['localProcessTerminated']
    assert receipt['state'] == observation['state'] and receipt['failureObservation'] == observation


@pytest.mark.parametrize('name', ['JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'JAVA_OPTS'])
def test_secret_jvm_options_rejected_before_env_material_or_container_creation(tmp_path, name):
    config_pin = tmp_path / 'application.json'
    config_pin.write_bytes(mechanism.canonical({'artifactSha256': 'a' * 64}))
    app = pin_file(config_pin); mount = {'pin': app, 'target': '/run/recovery/protection.json'}
    secret_value = 'UNIT_PRIVATE_OPTION_VALUE'
    reference = tmp_path / 'secret-reference.json'
    reference.write_bytes(mechanism.canonical({'service': 'backend', 'environment': name,
                                               'filePin': {'path': secret_value}}))
    backend = {'role': 'backend', 'configurationMounts': [mount], 'command': [], 'env': {'JAVA_TOOL_OPTIONS':
        '-Dintruoyi.recovery.protection.path=' + mount['target'] +
        ' -Dintruoyi.recovery.protection.sha256=' + app['sha256'] +
        ' -Dintruoyi.maintenance.boot.artifactSha256=' + 'a' * 64}}
    config = {'services': [backend], 'secretRefs': []}
    validate_recovery_launch(config, {'mounts': [mount], 'applicationConfigPin': app})
    config['secretRefs'] = [pin_file(reference)]
    with pytest.raises(EnvironmentFailure, match='APPLICATION_PROTECTION_SECRET_JVM_OPTIONS_REJECTED') as failure:
        validate_recovery_launch(config, {'mounts': [mount], 'applicationConfigPin': app})
    assert secret_value not in str(failure.value)
    native = object.__new__(NativeDocker); native.config = config
    with pytest.raises(EnvironmentFailure, match='APPLICATION_PROTECTION_SECRET_JVM_OPTIONS_REJECTED'):
        native.private_env(backend, tmp_path)
    assert not (tmp_path / 'backend.env').exists()


@pytest.mark.parametrize('alias', ['redis', '172.29.240.4', 'operation-redis'])
def test_redis_alias_same_selected_native_domain_rejected_and_distinct_database_admitted(alias):
    config = {'businessRedis': {'host': 'redis', 'port': 6379, 'database': 0},
              'temporaryRedis': {'host': alias, 'port': 6379, 'database': 0}}
    hosts = {'redis', '172.29.240.4', 'operation-redis'}
    with pytest.raises(mechanism.ProtectionFailure, match='PROTECTION_TEMP_REDIS_NATIVE_DOMAIN_ALIAS'):
        mechanism.validate_redis_domains(config, 'a' * 64, hosts)
    config['temporaryRedis']['database'] = 1
    mechanism.validate_redis_domains(config, 'a' * 64, hosts)


@pytest.mark.parametrize('expiry_point', ['before', 'after_intention'])
def test_expired_deadline_does_not_spawn(tmp_path, monkeypatch, expiry_point):
    executor = mechanism.Executor({'deadlineMilliseconds': 1}, {}, tmp_path)
    if expiry_point == 'before':
        executor.deadline = time.monotonic() - 1
    else:
        executor.deadline = time.monotonic() + 5
        original_write = mechanism.write_json
        def slow_intention(path, value):
            pin = original_write(path, value)
            if path.name.startswith('intention-'):
                executor.deadline = time.monotonic() - 1
            return pin
        monkeypatch.setattr(mechanism, 'write_json', slow_intention)
    monkeypatch.setattr(mechanism.subprocess, 'Popen', lambda *a, **k: pytest.fail('expired executor spawned'))
    with pytest.raises(mechanism.ProtectionFailure, match='PROTECTION_DEADLINE_EXPIRED') as failure:
        executor.run([sys.executable, '-I', '-c', 'pass'], mutation=True, effect_kind='DAEMON')
    assert not failure.value.unknown
    receipt = mechanism.read_pin(executor.invocations[-1])
    assert receipt['pid'] is None and receipt['actualExitCode'] is None


def test_claimed_known_failure_requires_original_local_termination(tmp_path):
    bindings = {key: 'unit-only' for key in ('phase', *mechanism.BINDINGS, 'containers')}
    now = mechanism.utc()
    original = mechanism.write_json(tmp_path / 'original.json', {
        'schemaVersion': 'RecoveryEnvironmentInvocation/v1', 'state': 'FAILED_RETAINED',
        'startedAt': now, 'finishedAt': now, 'pid': 123, 'actualExitCode': None,
        'localProcessTerminated': False})
    executor = tmp_path / 'selected.py'; executor.write_text('unit-only', encoding='utf-8')
    failure = {'schemaVersion': 'RecoveryApplicationProtectionFailure/v1',
        'state': 'FAILED_RETAINED', 'code': 'PROTECTION_NATIVE_EXECUTION_FAILED',
        'bindings': bindings, 'originalInvocationPins': [original], 'failureEvidencePins': []}
    runner = SimpleNamespace(guard=lambda: None, root=tmp_path, pins=[])
    with pytest.raises(EnvironmentFailure, match='APPLICATION_PROTECTION_FAILURE_EVIDENCE_UNPROVEN') as refused:
        observe_mechanism_failure(mechanism.canonical(failure),
            {'startedAt': now, 'actualExitCode': 2, 'pid': 456}, bindings, pin_file(executor), runner)
    assert refused.value.unknown and runner.pins == []


@pytest.mark.parametrize('failure_point', ['deadline', 'running_record', 'final_record'])
def test_every_postspawn_error_reaps_local_child_without_claiming_daemon_effect(tmp_path, monkeypatch, failure_point):
    executor = mechanism.Executor({'deadlineMilliseconds': 5000}, {}, tmp_path)
    real_popen = subprocess.Popen; processes = []
    def spawn(*a, **k):
        process = real_popen(*a, **k); processes.append(process)
        if failure_point == 'deadline': executor.deadline = time.monotonic() - 1
        return process
    monkeypatch.setattr(mechanism.subprocess, 'Popen', spawn)
    original_write = mechanism.write_json
    def write(path, value):
        if (failure_point == 'running_record' and path.name.startswith('running-')) or (
                failure_point == 'final_record' and path.name.startswith('invocation-')):
            raise OSError('unit-record-failure')
        return original_write(path, value)
    monkeypatch.setattr(mechanism, 'write_json', write)
    script = 'import time; time.sleep(30)' if failure_point != 'final_record' else 'raise SystemExit(7)'
    with pytest.raises(mechanism.ProtectionFailure) as failed:
        executor.run([sys.executable, '-I', '-c', script], mutation=True, effect_kind='DAEMON')
    assert failed.value.unknown and processes[0].poll() is not None
    assert failed.value.executor is executor
    if executor.invocations:
        receipt = mechanism.read_pin(executor.invocations[-1])
        assert receipt['pid'] == processes[0].pid and receipt['actualExitCode'] == processes[0].returncode
        assert receipt['state'] == 'TERMINAL_UNKNOWN' and receipt['localProcessTerminated']
    else:
        terminal = next(mechanism.read_pin(p) for p in executor.evidence_pins if Path(p['path']).name.startswith('termination-'))
        assert terminal['pid'] == processes[0].pid and terminal['actualExitCode'] == processes[0].returncode
        assert terminal['localProcessTerminated'] and terminal['state'] == 'TERMINAL_UNKNOWN'


def test_ordinary_native_mutation_nonzero_persists_unknown_and_blocks_new_target_request(tmp_path, monkeypatch):
    """Python is a harmless failing CLI here, never a stand-in for daemon success."""
    records = LocalRecords(tmp_path)
    records.config['dockerPin'] = pin_file(sys.executable)
    records.config['materialRoots'].append(str(Path(sys.executable).parent))
    records.approve()
    records.request['action'] = 'START_APPLICATION'
    records.request['inputPins'] = {'restoreExecutionResult': records.sample, 'recoveryTarget': records.sample}
    def failing_start(request, config, policy, trust, native, private):
        native.docker(['start', 'a' * 64], mutation=True)
        pytest.fail('a real nonzero CLI must not reach a start result')
    monkeypatch.setattr(application, 'start_application', failing_start)
    result = run_operation(records.request, records.trust, time.monotonic() + 15)
    assert result['state'] == 'TERMINAL_UNKNOWN' and result['failureCode'] == 'EXECUTOR_NONZERO_EXIT'
    receipt = next(read_pin(pin) for pin in result['originalResultPins']
                   if read_pin(pin).get('schemaVersion') == 'RecoveryEnvironmentInvocation/v1')
    assert receipt['mutation'] is True and receipt['pid'] > 0 and receipt['actualExitCode'] != 0
    assert receipt['state'] == 'TERMINAL_UNKNOWN' and receipt['localProcessState'] == 'TERMINATED'
    assert receipt['effectState'] == 'TERMINAL_UNPROVEN'
    assert all(json.loads(p.read_text())['state'] == 'TERMINAL_UNKNOWN' for p in (tmp_path/'journal').glob('*.json'))
    previous_invocations = sorted((tmp_path/'evidence').rglob('invocation-*.json'))
    records.request['requestId'] = 'unit-new-request-same-uncertain-target'
    with pytest.raises(EnvironmentFailure, match='TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN') as failed:
        run_operation(records.request, records.trust, time.monotonic() + 15)
    assert failed.value.unknown and sorted((tmp_path/'evidence').rglob('invocation-*.json')) == previous_invocations


@pytest.mark.parametrize('point', ['nonzero', 'stderr', 'running_receipt', 'observer_exception', 'guard_after_exit'])
def test_ordinary_dispatched_mutation_errors_never_prove_effect_failure(tmp_path, monkeypatch, point):
    real_write = runtime_module.atomic_json
    def write(path, value):
        if point == 'running_receipt' and value.get('pid') is not None and value.get('finishedAt') is None:
            raise OSError('unit-running-receipt-failed')
        return real_write(path, value)
    monkeypatch.setattr(runtime_module, 'atomic_json', write)
    processes = []
    original_spawn = runtime_module.subprocess.Popen
    def spawn(*args, **options):
        process = original_spawn(*args, **options)
        processes.append(process)
        return process
    monkeypatch.setattr(runtime_module.subprocess, 'Popen', spawn)
    def guard():
        if point == 'guard_after_exit' and processes and processes[0].poll() is not None:
            raise EnvironmentFailure('UNIT_AUTHORIZATION_REVOKED')
    runner = CommandRunner(tmp_path, time.monotonic() + 5, guard)
    script = 'import time; time.sleep(20)' if point == 'running_receipt' else (
        "import sys; sys.stderr.write('unit-error')" if point == 'stderr' else
        'raise SystemExit(0)' if point == 'guard_after_exit' else 'raise SystemExit(7)')
    def failed_observer(*args):
        raise ValueError('unit-unreadable-proof')
    options = {'failure_observer': failed_observer} if point == 'observer_exception' else {}
    with pytest.raises(EnvironmentFailure) as failed:
        runner.run([sys.executable, '-I', '-c', script], mutation=True, **options)
    assert failed.value.unknown
    receipt = read_pin(runner.pins[-1])
    assert receipt['state'] == 'TERMINAL_UNKNOWN' and receipt['effectState'] == 'TERMINAL_UNPROVEN'
    assert receipt['pid'] > 0 and type(receipt['actualExitCode']) is int


def test_unspawned_mutation_failure_is_known_and_does_not_claim_daemon_dispatch(tmp_path):
    runner = CommandRunner(tmp_path, time.monotonic() + 5, lambda: None)
    with pytest.raises(EnvironmentFailure) as failed:
        runner.run([str(tmp_path/'missing-unit-executable')], mutation=True)
    assert not failed.value.unknown
    receipt = read_pin(runner.pins[-1])
    assert receipt['pid'] is None and receipt['actualExitCode'] is None and receipt['state'] == 'FAILED_RETAINED'
    assert receipt['dispatchState'] == 'NOT_STARTED' and receipt['effectState'] == 'NO_MUTATION_DISPATCHED'


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux native process-group/pidfd/subreaper observation required; WSL/Docker prohibited')
@pytest.mark.parametrize('cancel', ['guard', 'deadline', 'receipt_io'])
def test_outer_cancel_terminates_supervised_nested_task_group_and_preserves_other_task(tmp_path, monkeypatch, cancel):
    ready = tmp_path/'owned-pids.json'
    script = tmp_path/'nested-task.py'
    grandchild_source = ("import os,json,pathlib,time\n"
        f"pathlib.Path({str(ready)!r}).write_text(json.dumps({{'pid':os.getpid(),'group':os.getpgrp(),'session':os.getsid(0)}}))\n"
        "time.sleep(30)\n")
    child_source = ("import subprocess,sys,time\n"
        f"p=subprocess.Popen([sys.executable,'-I','-c',{grandchild_source!r}])\n"
        "p.wait()\n")
    script.write_text("import sys,pathlib\n"
        f"sys.path.insert(0,{str(MODULE)!r})\n"
        "from recovery_application_mechanism import Executor\n"
        f"root=pathlib.Path({str(tmp_path/'inner')!r}); root.mkdir()\n"
        "e=Executor({'deadlineMilliseconds':30000},{},root)\n"
        f"e.run([sys.executable,'-I','-c',{child_source!r}],mutation=True,effect_kind='DAEMON')\n", encoding='utf-8')
    sentinel = subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(30)'], start_new_session=True)
    real_write = runtime_module.atomic_json
    def guard():
        if cancel == 'guard' and ready.exists():
            raise EnvironmentFailure('UNIT_LEASE_REVOKED')
    def write(path, value):
        if cancel == 'receipt_io' and value.get('pid') is not None and value.get('finishedAt') is None:
            until = time.monotonic() + 3
            while not ready.exists() and time.monotonic() < until:
                time.sleep(0.01)
            assert ready.exists(), 'test child did not reach its finite wait'
            raise OSError('unit-outer-running-record-io')
        return real_write(path, value)
    monkeypatch.setattr(runtime_module, 'atomic_json', write)
    runner = CommandRunner(tmp_path, time.monotonic() + (1 if cancel == 'deadline' else 10), guard)
    try:
        with pytest.raises(EnvironmentFailure) as failed:
            runner.run([sys.executable, '-I', str(script)], mutation=True)
        assert failed.value.unknown and ready.exists()
        receipt = read_pin(runner.pins[-1])
        pid_record = json.loads(ready.read_text())
        assert pid_record['group'] == pid_record['session'] == receipt['pid']
        assert receipt['localTaskTreeState'] == 'TERMINATED' and receipt['state'] == 'TERMINAL_UNKNOWN'
        assert len(receipt['localTaskProcesses']) >= 3
        assert all(item['state'] == 'TERMINATED' and not Path('/proc', str(item['pid'])).exists()
                   for item in receipt['localTaskProcesses'])
        assert not Path('/proc', str(pid_record['pid'])).exists() and sentinel.poll() is None
    finally:
        # Only the separate sentinel this test actually created is controlled.
        sentinel.kill(); sentinel.communicate(timeout=5)
