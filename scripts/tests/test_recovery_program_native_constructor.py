"""Actual constructor boundaries, real metadata/locks, no database dispatch.

The only native-I/O seam raises at the first database method. Its callback
examines the actually constructed object while SAFE's real archive lease is
still held. It neither fakes database success nor bypasses __init__.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import sys
import tarfile

import pytest

from test_recovery_program_generation import case, switched, write
from test_recovery_program_execution import bind, resolve
from test_recovery_program_activation import locked, start, stage
from test_recovery_program_packaging import program_packages
from recovery_engine import Budget, RecoveryError, pin
import recovery_resource_admission as admission
import recovery_minimal_runtime as runtime
from recovery_program_native import MainNativeExecutionContext

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux constructor/lock contracts')

SCENARIOS = (
    'preparation', 'restore', 'missing-context', 'wrong-context-type', 'stale-phase',
    'configuration-mismatch', 'request-mismatch', 'target-mismatch', 'expired-before', 'unlocked-before',
    'config-drift', 'original-drift', 'budget-drift', 'lock-drift', 'metadata-drift', 'stage-drift',
    'payload-content-drift', 'payload-pin-mismatch', 'legacy',
)


def constructor_case(root, formal, seam):
    """Complete private owner before its real immutable reservation is issued."""
    c = case.__wrapped__(root)
    tool = root/'registered-tool'; tool.write_bytes(b'never executed constructor tool')
    target = c['target']
    target.update(dataPolicy={'businessInvariants': []}, dockerPin=pin(tool), iptablesPin=pin(tool),
        machineId='constructor-unit-machine', dataRoot=str(root), resourceBudget=dict(
            schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=1,
            hostAvailableMemoryBytes=1, diskBytesByPath={str(root): 1}))
    target['mainApplication']['schemaVersion'] = 'RegisteredMainApplication/v1'
    candidate, capture, switch = switched(c, root)
    operations = root/'operations'; operations.mkdir(mode=0o700)
    operation = operations/'restore-1'; operation.mkdir(mode=0o700)
    host = root/'resource-host'; host.mkdir(mode=0o700)
    machine = root/'machine-id'; machine.write_text(target['machineId'], encoding='ascii')
    seam.setattr(admission, 'HOST_ROOT', host)
    seam.setattr(admission, 'MACHINE_ID', machine)
    # This unit seam asserts no capacity or real host admission result. The
    # durable reservation, operation documents, epochs and locks below are real.
    seam.setattr(admission, 'observe_resources', lambda *_: dict(mysqlMemoryLimitBytes=10,
        hostAvailableMemoryBytes=10, disks=[dict(path=str(root), device=1, freeBytes=10)]))
    owner = dict(operationsRoot=str(operations), targets={'target57': deepcopy(target), 'other': {'keep': True}},
        sources={'source57': {'keep': True}}, targetProgramPolicies={'target57': deepcopy(c['policy'])},
        targetBackupEpochPolicies={'target57': deepcopy(c['epoch'])}, unrelated={'keep': ['exact']},
        environmentMysqlClientPath='/usr/bin/mysql', maxExpandedBytes=64*1024**3,
        formalModuleDirectory=str(formal), deadlineMilliseconds=120000,
        dataLimits=dict(max_rows=10000000, max_nodes=100000000, max_bytes=16*1024**3, seconds=7200),
        frontendReadiness={'target57': {'address': '192.0.2.57', 'port': 18081}})
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-1', action='RESTORE',
        sourceConfigRef='source57', parentChainRef=None, recoveryPointRef='point1', targetConfigRef='target57')
    owner_pin = write(operation/'configuration.json', owner)
    request_pin = write(operation/'request.json', request)
    reservation = admission.reserve(owner, request, operation)
    claim = Path(target['replacement']['stateRoot'])/request['operationId']; claim.mkdir(mode=0o700)
    payload = root/'archive-payload'; payload.write_bytes(b'actual constructor archive boundary bytes')
    reference = pin(payload)
    material = dict(recoveryPoint='point1', sourceDatabaseUuid=c['epoch']['databaseUuid'],
        objects={'method': 'PHYSICAL_FILES'}, payloadPins=[reference], versionPins=[])
    chain = [(reference, None, material, reference)]
    return SimpleNamespace(case=c, owner=owner, request=request, root=operation, claim=claim,
        owner_pin=owner_pin, request_pin=request_pin, reservation=reservation, candidate=candidate,
        capture=capture, switch=switch, chain=chain, payload=payload)


class DatabaseBoundary(Exception):
    pass


def exercise_constructor(work, formal, variant, scenario):
    import fcntl
    with pytest.MonkeyPatch.context() as seam:
        e = constructor_case(work, formal, seam)
        original_bytes = {p['path']: Path(p['path']).read_bytes()
                          for p in (e.owner_pin, e.request_pin, e.reservation)}
        seen = []
        with locked(e.case) as fd:
            saved, binding = bind(e, fd)
            start(e.case, e.claim, fd)
            shared = Budget(120000)
            with MainNativeExecutionContext(e.owner, e.request, e.root,
                    binding_pin=binding, lock_fd=fd, budget=shared) as ctx:
                configuration, request = deepcopy(e.owner), deepcopy(e.request)
                view = ctx.preparation(configuration)

                def publish():
                    generation = stage(e.case, saved, fd, target_pin=write(e.claim/'target.json', e.candidate),
                        capture_pins={'source57': write(e.claim/'capture.json', e.capture)}, switch_result_pin=e.switch)
                    ctx.stage(generation)
                    return generation

                if scenario == 'restore':
                    generation = publish()
                    (e.claim/'runtime').mkdir(mode=0o700)
                    configuration, _ = resolve(e, binding, fd, generation_pin=generation, runtime=True)
                    view = ctx.restore(configuration)
                elif scenario == 'stale-phase':
                    publish()
                target = deepcopy(configuration['targets']['target57'])
                keywords = {'native_context': view}
                failure = None
                if scenario == 'legacy':
                    configuration.pop('targetProgramPolicies')
                    keywords = {}
                elif scenario == 'missing-context':
                    keywords = {}; failure = 'PROGRAM_NATIVE_CONTEXT_REQUIRED'
                elif scenario == 'wrong-context-type':
                    keywords = {'native_context': object()}; failure = 'PROGRAM_NATIVE_CONTEXT_INVALID'
                elif scenario == 'configuration-mismatch':
                    configuration['unrelated'] = {}; failure = 'PROGRAM_NATIVE_CONFIGURATION_CHANGED'
                elif scenario == 'request-mismatch':
                    request['recoveryPointRef'] = 'another-point'; failure = 'PROGRAM_NATIVE_REQUEST_CHANGED'
                elif scenario == 'target-mismatch':
                    target['database'] = 'other'; failure = 'PROGRAM_NATIVE_TARGET_CHANGED'
                elif scenario == 'stale-phase':
                    failure = 'PROGRAM_NATIVE_PHASE_CHANGED'
                elif scenario == 'expired-before':
                    shared.deadline = 0; failure = 'DEADLINE_EXCEEDED'
                elif scenario == 'unlocked-before':
                    fcntl.flock(fd, fcntl.LOCK_UN); failure = 'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'
                elif scenario == 'payload-pin-mismatch':
                    e.payload.write_bytes(b'changed archive bytes')
                    if variant == 'standard': failure = 'PIN_'

                def before_database(native):
                    seen.append(native)
                    assert getattr(type(native), 'supports_registered_main_targets', False), 'MAIN_WRAPPER_REQUIRED'
                    assert native.original == request and native.config == target
                    assert native.frontend_readiness == configuration['frontendReadiness']['target57']
                    if scenario != 'legacy':
                        assert native.native_context is view
                        assert native.budget is shared, 'ORIGINAL_SHARED_BUDGET_REQUIRED'
                    else:
                        assert isinstance(native.budget, Budget)
                    native.guard()
                    code = None
                    if scenario == 'config-drift':
                        native.config = dict(native.config, database='other')
                        code = 'PROGRAM_NATIVE_TARGET_CHANGED'
                    elif scenario == 'original-drift':
                        native.original = dict(native.original, sourceConfigRef='other')
                        code = 'PROGRAM_NATIVE_REQUEST_CHANGED'
                    elif scenario == 'budget-drift':
                        native.budget = Budget(120000)
                        code = 'PROGRAM_NATIVE_BUDGET_CHANGED'
                    elif scenario == 'lock-drift':
                        fcntl.flock(fd, fcntl.LOCK_UN)
                        code = 'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'
                    elif scenario == 'metadata-drift':
                        path = Path(e.owner_pin['path']); raw = path.read_bytes()
                        path.write_bytes(b'{}'); path.write_bytes(raw)
                        code = 'ARCHIVED_PAYLOAD_CHANGED'
                    elif scenario == 'stage-drift':
                        publish(); code = 'PROGRAM_NATIVE_PHASE_CHANGED'
                    elif scenario == 'payload-content-drift':
                        raw = e.payload.read_bytes(); e.payload.write_bytes(raw)
                        if variant == 'standard': code = 'ARCHIVED_PAYLOAD_CHANGED'
                    if code is not None:
                        with pytest.raises((RecoveryError, ValueError), match=code):
                            native.guard()
                    else:
                        native.guard()
                    if variant == 'standard':
                        assert native.archive_guard is not None
                    else:
                        assert getattr(native, 'archive_guard', None) is None

                class Boundary(runtime.MinimalData):
                    def database_uuid(self):
                        before_database(self)
                        raise DatabaseBoundary('stop before real database I/O')

                log = e.root/'preparation'; log.mkdir(mode=0o700)
                if failure is not None:
                    with pytest.raises((RecoveryError, ValueError), match=failure):
                        Boundary(configuration, request, None, {}, e.chain, target, log, [], **keywords)
                    assert not seen, 'rejected constructor reached database boundary'
                else:
                    with pytest.raises(DatabaseBoundary, match='stop before real database I/O'):
                        Boundary(configuration, request, None, {}, e.chain, target, log, [], **keywords)
                    assert len(seen) == 1
                    if variant == 'standard':
                        assert seen[0].archive_guard.fd == -1, 'SAFE constructor exception did not close archive lease'
        assert all(Path(path).read_bytes() == data for path, data in original_bytes.items())


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_actual_source_constructor_binds_native_context_before_database(tmp_path, scenario):
    exercise_constructor(tmp_path, ROOT/'ops/backup_engine/formal', 'lightweight', scenario)


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_actual_delivered_constructor_and_guard_run_in_new_process(program_packages, tmp_path, variant):
    engine = tmp_path/'engine'
    with tarfile.open(program_packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(engine, filter='data')
    script = r'''
from pathlib import Path
import sys
engine,tests,work=map(Path,sys.argv[1:4]);variant=sys.argv[4]
sys.path[:0]=[str(engine/'common'),str(engine/'formal'),str(tests)]
import recovery_minimal_runtime as runtime
import recovery_program_native as native
import recovery_program_execution as execution
import recovery_program_generation as generation
import recovery_program_activation as activation
import recovery_resource_admission as admission
import recovery_main_target as main
modules=(runtime,native,execution,generation,activation,admission,main)
assert all(Path(m.__file__).resolve().parent == (engine/'common').resolve() for m in modules)
from test_recovery_program_native_constructor import SCENARIOS,exercise_constructor
for index,scenario in enumerate(SCENARIOS):
 root=work/str(index);root.mkdir(mode=0o700)
 exercise_constructor(root,engine/'formal',variant,scenario)
 print('ACTUAL_CONSTRUCTOR_SCENARIO_PASS '+scenario,flush=True)
assert all(Path(m.__file__).resolve().parent == (engine/'common').resolve() for m in modules)
print('PACKAGED_NATIVE_CONSTRUCTOR_PASS')
'''
    work = tmp_path/'cases'; work.mkdir(mode=0o700)
    result = subprocess.run([sys.executable, '-B', '-c', script, str(engine), str(ROOT/'scripts/tests'),
        str(work), variant], capture_output=True, timeout=180,
        env={**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)})
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert result.stdout.count(b'ACTUAL_CONSTRUCTOR_SCENARIO_PASS ') == len(SCENARIOS)
    assert result.stdout.rstrip().endswith(b'PACKAGED_NATIVE_CONSTRUCTOR_PASS')
