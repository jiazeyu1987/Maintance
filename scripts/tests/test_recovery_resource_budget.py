"""Resource admission decisions; these are not remote measurements or E2E."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_resource_admission import check_budget
import recovery_resource_admission as admission

GIB = 1024 ** 3


@pytest.fixture
def resources():
    policy = dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=2*GIB,
                  hostAvailableMemoryBytes=3*GIB,
                  diskBytesByPath={'/target': 4*GIB, '/staging': 6*GIB})
    observed = dict(mysqlMemoryLimitBytes=2*GIB, hostAvailableMemoryBytes=4*GIB,
                    hostSwapFreeBytes=100*GIB,
                    disks=[dict(path='/target', device=1, freeBytes=12*GIB),
                           dict(path='/staging', device=1, freeBytes=12*GIB)])
    return policy, observed


def test_resources_admitted_without_business_success_claim(resources):
    result = check_budget(*resources)
    assert result['admitted'] is True
    assert result['businessAcceptance'] == 'NOT_PERFORMED'
    assert result['diskRequirements'] == [{'device': 1, 'requiredBytes': 10*GIB, 'availableBytes': 12*GIB}]


def test_512_mib_mysql_is_rejected_despite_large_host_and_swap(resources):
    policy, observed = resources
    observed['mysqlMemoryLimitBytes'] = 512*1024**2
    with pytest.raises(RuntimeError, match='RESTORE_MYSQL_MEMORY_INSUFFICIENT'):
        check_budget(policy, observed)


def test_swap_is_not_physical_memory(resources):
    policy, observed = resources
    observed['hostAvailableMemoryBytes'] = GIB
    with pytest.raises(RuntimeError, match='RESTORE_HOST_MEMORY_INSUFFICIENT'):
        check_budget(policy, observed)


def test_shared_device_requirements_are_added(resources):
    policy, observed = resources
    for row in observed['disks']: row['freeBytes'] = 7*GIB
    with pytest.raises(RuntimeError, match='RESTORE_DISK_SPACE_INSUFFICIENT'):
        check_budget(policy, observed)


def test_distinct_devices_have_independent_budgets(resources):
    policy, observed = resources
    observed['disks'][1]['device'] = 2
    for row in observed['disks']: row['freeBytes'] = 7*GIB
    assert check_budget(policy, observed)['admitted'] is True


@pytest.mark.parametrize('bad', [None, {}, {'schemaVersion': 'unknown'}])
def test_missing_or_unknown_budget_is_rejected(resources, bad):
    with pytest.raises(RuntimeError, match='RESTORE_RESOURCE_BUDGET_INVALID'):
        check_budget(bad, resources[1])


@pytest.mark.parametrize('field', ['mysqlMemoryBytes', 'hostAvailableMemoryBytes'])
@pytest.mark.parametrize('bad', [True, 0, -1, '2147483648', 1.5])
def test_invalid_memory_budget_is_rejected(resources, field, bad):
    policy, observed = resources
    policy[field] = bad
    with pytest.raises(RuntimeError, match='RESTORE_RESOURCE_BUDGET_INVALID'):
        check_budget(policy, observed)


@pytest.mark.parametrize('change', ['missing_path', 'duplicate_path', 'negative_free', 'unknown_limit'])
def test_incomplete_measurement_is_not_admission(resources, change):
    policy, observed = resources
    if change == 'missing_path': observed['disks'].pop()
    if change == 'duplicate_path': observed['disks'].append(dict(observed['disks'][0]))
    if change == 'negative_free': observed['disks'][0]['freeBytes'] = -1
    if change == 'unknown_limit': observed['mysqlMemoryLimitBytes'] = None
    with pytest.raises(RuntimeError, match='RESTORE_RESOURCE_OBSERVATION_INVALID'):
        check_budget(policy, observed)


@pytest.mark.parametrize('version', [1, 2])
def test_parent_cgroup_limit_cannot_be_hidden_by_container_limit(tmp_path, version):
    mount = tmp_path if version == 2 else tmp_path / 'memory'
    group = mount / 'parent' / 'mysql'
    group.mkdir(parents=True)
    name = 'memory.max' if version == 2 else 'memory.limit_in_bytes'
    (group / name).write_text(str(2*GIB), encoding='ascii')
    (group.parent / name).write_text(str(512*1024**2), encoding='ascii')
    (mount / name).write_text('max' if version == 2 else str(2**63-4096), encoding='ascii')
    if version == 1:
        for path in (group, group.parent, mount):
            (path / 'memory.use_hierarchy').write_text('1', encoding='ascii')
    record = '0::/parent/mysql\n' if version == 2 else '5:memory:/parent/mysql\n'
    result = admission.cgroup_memory_limits(record, tmp_path)
    assert result['version'] == version
    assert min(result['limitsBytes']) == 512*1024**2


def test_v1_nonhierarchical_parent_does_not_limit_child(tmp_path):
    group = tmp_path / 'memory' / 'mysql'
    group.mkdir(parents=True)
    (group / 'memory.limit_in_bytes').write_text(str(2*GIB), encoding='ascii')
    (group.parent / 'memory.limit_in_bytes').write_text(str(512*1024**2), encoding='ascii')
    (group.parent / 'memory.use_hierarchy').write_text('0', encoding='ascii')
    assert admission.cgroup_memory_limits('5:memory:/mysql\n', tmp_path)['limitsBytes'] == [2*GIB]


def test_unlimited_cgroup_is_explicit_and_never_zero_capacity(tmp_path):
    group = tmp_path / 'mysql'
    group.mkdir()
    (group / 'memory.max').write_text('max', encoding='ascii')
    result = admission.cgroup_memory_limits('0::/mysql\n', tmp_path)
    assert result['limitsBytes'] == []


@pytest.mark.parametrize('record', ['0::/../outside\n', 'bad', '1:cpu:/mysql\n',
                                   '0::/mysql\n0::/other\n'])
def test_unknown_or_escaping_cgroup_record_is_rejected(tmp_path, record):
    with pytest.raises(RuntimeError, match='RESTORE_CGROUP_'):
        admission.cgroup_memory_limits(record, tmp_path)


def test_missing_intermediate_limit_is_not_silently_unlimited(tmp_path):
    group = tmp_path / 'parent' / 'mysql'
    group.mkdir(parents=True)
    (group / 'memory.max').write_text(str(2*GIB), encoding='ascii')
    with pytest.raises(RuntimeError, match='RESTORE_CGROUP_'):
        admission.cgroup_memory_limits('0::/parent/mysql\n', tmp_path)


def test_real_owner_entry_refuses_missing_budget_before_child_dispatch(tmp_path, monkeypatch):
    import recovery_minimal as owner
    from recovery_engine import pin, write
    operation_root = tmp_path / 'operations'
    request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='resource-test',
        action='RESTORE', sourceConfigRef='source', parentChainRef=None,
        recoveryPointRef='full-point', targetConfigRef='target')
    configuration = dict(operationsRoot=str(operation_root),
        pythonPin=pin(Path(sys.executable).resolve()), deadlineMilliseconds=1000,
        targets={'target': {}}, sources={})
    config_path, request_path = tmp_path / 'config.json', tmp_path / 'request.json'
    write(config_path, configuration); write(request_path, request)
    dispatched = []
    def child(*args, **kwargs):
        dispatched.append(True)
        raise RuntimeError('UNIT_DISPATCH_MUST_NOT_HAPPEN')
    monkeypatch.setattr(owner, 'run_child', child)
    result = owner.run(str(config_path), str(request_path), str(tmp_path / 'output.json'))
    assert not dispatched
    assert result['state'] == 'FAILED_RETAINED'
    assert result['failureCode'] == 'RESTORE_RESOURCE_BUDGET_INVALID'
    evidence = json.loads((operation_root / request['operationId'] / 'resource-admission-owner.json').read_bytes())
    assert evidence['admitted'] is False
    assert result['originalResultPins']


@pytest.fixture
def resource_host(tmp_path, monkeypatch):
    from recovery_engine import pin
    proc, cgroups = tmp_path / 'proc', tmp_path / 'cgroups'
    process = proc / '123'
    process.mkdir(parents=True)
    (process / 'stat').write_text('123 (mysqld) ' + ' '.join(['S'] + ['0']*18 + ['456']), encoding='ascii')
    (process / 'cgroup').write_text('0::/mysql\n', encoding='ascii')
    (proc / 'meminfo').write_text('MemTotal: 16777216 kB\nMemAvailable: 4194304 kB\nSwapFree: 104857600 kB\n', encoding='ascii')
    (cgroups / 'mysql').mkdir(parents=True)
    (cgroups / 'mysql/memory.max').write_text(str(2*GIB), encoding='ascii')
    monkeypatch.setattr(admission, 'PROC_ROOT', proc)
    monkeypatch.setattr(admission, 'CGROUP_ROOT', cgroups)
    binary = tmp_path / 'docker-fixture'
    binary.write_bytes(b'fixture never executed')
    binary.chmod(0o600)
    row = dict(Id='mysql', Image='mysql-image', Config={'Labels': {'intruoyi.recovery.target': 'target'}},
               State=dict(Running=True, Paused=False, Restarting=False, Pid=123), HostConfig={'Memory': 2*GIB})
    def observe(argv, **kwargs):
        assert argv == [str(binary), '--host', 'unix:///var/run/docker.sock', 'inspect', 'mysql']
        return SimpleNamespace(returncode=0, stdout=json.dumps([row]).encode(), stderr=b'')
    monkeypatch.setattr(admission.subprocess, 'run', observe)
    budget = dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=2*GIB,
                  hostAvailableMemoryBytes=3*GIB, diskBytesByPath={str(tmp_path): 1})
    target = dict(targetId='target', services=[dict(role='mysql', id='mysql', imageId='mysql-image')],
                  dockerPin=pin(binary), dataRoot=str(tmp_path), dataPaths=[str(tmp_path)], resourceBudget=budget)
    configuration = dict(operationsRoot=str(tmp_path), targets={'target': target})
    request = dict(operationId='resource-test', targetConfigRef='target')
    return configuration, request, budget, row, cgroups, tmp_path


def test_admission_records_actual_observations_without_mutating_target(resource_host):
    config, request, budget, _, _, root = resource_host
    decision = admission.admit(config, request, root, 'owner')
    assert decision['admitted']
    proof = json.loads((root / 'resource-admission-owner.json').read_bytes())
    assert proof['observation']['mysqlMemoryLimitBytes'] == 2*GIB
    assert proof['observation']['hostAvailableMemoryBytes'] == 4*GIB
    assert proof['elapsedSeconds'] >= 0
    assert not (root / '.recovery-operation.json').exists()


def test_kernel_limit_overrides_larger_docker_setting(resource_host):
    config, request, budget, _, cgroups, root = resource_host
    (cgroups / 'mysql/memory.max').write_text(str(512*1024**2), encoding='ascii')
    with pytest.raises(RuntimeError, match='RESTORE_MYSQL_MEMORY_INSUFFICIENT'):
        admission.admit(config, request, root, 'owner')
    proof = json.loads((root / 'resource-admission-owner.json').read_bytes())
    assert proof['admitted'] is False
    assert proof['details'] == dict(requiredBytes=2*GIB, availableBytes=512*1024**2)


@pytest.mark.parametrize('change', ['wrong_container', 'stopped', 'uncovered_path'])
def test_observation_rejects_wrong_identity_or_incomplete_disk_scope(resource_host, change):
    config, request, budget, row, _, root = resource_host
    if change == 'wrong_container': row['Id'] = 'other'
    if change == 'stopped': row['State']['Running'] = False
    if change == 'uncovered_path':
        subset = root / 'subset'
        subset.mkdir()
        budget['diskBytesByPath'] = {str(subset): 1}
    with pytest.raises(RuntimeError):
        admission.admit(config, request, root, 'owner')
    assert json.loads((root / 'resource-admission-owner.json').read_bytes())['admitted'] is False
