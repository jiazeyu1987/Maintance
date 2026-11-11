"""Explicit installation binding; synthetic packages are not live acceptance."""
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_main_program_target_control_candidate import inputs, build, repin, canonical, digest
import main_program_target_control_staging as staging


EXTRA_CHANGED = ('common/recovery_resource_admission.py', 'common/recovery_program_resources.py')


@pytest.fixture
def policy_inputs(inputs):
    k = inputs
    for name in EXTRA_CHANGED:
        replacement = next(n for n in k['previous_package_files'] if n.startswith('common/unchanged_'))
        for key in ('previous_package_files', 'package_files'):
            k[key].pop(replacement)
        k['previous_package_files'][name] = b'OLD = True\n'
        k['package_files'][name] = b'NEW = True\n'
    old_sha = digest(canonical({n: digest(raw) for n, raw in k['previous_package_files'].items()}))
    k['old_build']['fileManifestSha256'] = k['current_controller']['fileManifestSha256'] = old_sha
    k['new_build']['packages'][0]['fileManifestSha256'] = digest(
        canonical({n: digest(raw) for n, raw in k['package_files'].items()}))
    target = k['owner']['targets'][k['current_controller']['targetConfigRef']]
    target['resourceBudget'] = dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=2*1024**3,
        hostAvailableMemoryBytes=3*1024**3, diskBytesByPath={'/data/mysql': 8*1024**3, '/data/minio': 32*1024**3})
    repin(k)
    for targets in k['control']['restoreConfigurations'].values():
        targets[k['current_controller']['targetConfigRef']] = deepcopy(k['current_controller']['ownerConfigurationPin'])
    repin(k)
    return k


@pytest.mark.parametrize('mode', ['OBSERVE_ONLY', 'RESERVE'])
def test_explicit_mode_changes_only_the_registered_target_budget(policy_inputs, mode):
    k = policy_inputs
    k['disk_admission_mode'] = mode
    before = deepcopy(k)
    result = build(k)
    assert k == before
    assert result['diskAdmissionMode'] == mode
    owner = next(r['value'] for r in result['newDocuments'] if r['pin'] == result['controller']['ownerPin'])
    target = result['targetConfigRef']
    expected = deepcopy(k['owner']['targets'][target]['resourceBudget'])
    expected.update(schemaVersion='RestoreResourceBudget/v2', diskAdmissionMode=mode)
    assert owner['targets'] == k['owner']['targets']
    assert owner['targetResourceAdmissionPolicies'] == {target: expected}
    assert owner['sources'] == k['owner']['sources']
    assert owner['sourceProgramArchivePolicies'] == k['owner']['sourceProgramArchivePolicies']


@pytest.mark.parametrize('mode', ['', 'IGNORE', True, 0, {}])
def test_unknown_modes_are_rejected(policy_inputs, mode):
    policy_inputs['disk_admission_mode'] = mode
    with pytest.raises(ValueError, match='DISK_ADMISSION_MODE_INVALID'):
        build(policy_inputs)


def test_additional_resource_module_changes_require_explicit_binding(policy_inputs):
    with pytest.raises(ValueError, match='UNREVIEWED_PACKAGE_DELTA'):
        build(policy_inputs)


@pytest.mark.parametrize('problem', ['unknown-field', 'unknown-version', 'empty-disks', 'bad-memory'])
def test_invalid_original_budget_is_not_silently_replaced(policy_inputs, problem):
    k = policy_inputs
    p = k['owner']['targets'][k['current_controller']['targetConfigRef']]['resourceBudget']
    if problem == 'unknown-field': p['unknown'] = True
    elif problem == 'unknown-version': p['schemaVersion'] = 'unknown'
    elif problem == 'empty-disks': p['diskBytesByPath'] = {}
    elif problem == 'bad-memory': p['mysqlMemoryBytes'] = True
    repin(k)
    k['disk_admission_mode'] = 'OBSERVE_ONLY'
    with pytest.raises(ValueError, match='DISK_BUDGET_INVALID'):
        build(k)


def test_installation_capacity_uses_the_runtime_admission_policy(tmp_path, monkeypatch):
    import recovery_resource_admission as admission
    policy = dict(schemaVersion='RestoreResourceBudget/v2', diskAdmissionMode='OBSERVE_ONLY',
        mysqlMemoryBytes=1, hostAvailableMemoryBytes=1, diskBytesByPath={str(tmp_path): 112*1024**3})
    calls = []
    def enforce(p, required, available, code, **kwargs):
        calls.append((p, required, available, code, kwargs))
        return dict(diskAdmissionMode='OBSERVE_ONLY', forecastReservationsEnforced=False,
            requiredBytes=required, availableBytes=available, minimumFreeBytes=kwargs['minimum_free_bytes'])
    monkeypatch.setattr(admission, 'enforce_disk_capacity', enforce, raising=False)
    monkeypatch.setattr(admission, 'disk_admission_mode', lambda p: p['diskAdmissionMode'], raising=False)
    result = staging.check_target_staging_capacity(resource_budget=policy, capture_root=str(tmp_path),
        capture_limits=dict(maxWrittenBytes=64*1024**3, minimumFreeBytes=2*1024**3))
    assert result['diskAdmissionMode'] == 'OBSERVE_ONLY'
    assert len(calls) == 1
    p, required, available, code, kwargs = calls[0]
    assert p == policy and required == 178*1024**3 and available >= 0
    assert kwargs['minimum_free_bytes'] == 2*1024**3
    assert code == 'TARGET_CAPACITY_NOT_AVAILABLE'


@pytest.mark.skipif(os.name != 'posix', reason='actual POSIX policy paths')
@pytest.mark.parametrize('mode,free_gib,admitted', [
    ('OBSERVE_ONLY', 122, True), ('RESERVE', 122, False), ('OBSERVE_ONLY', 1, False)])
def test_actual_installation_capacity_respects_explicit_mode(tmp_path, monkeypatch, mode, free_gib, admitted):
    import recovery_resource_admission as admission
    policy = dict(schemaVersion='RestoreResourceBudget/v2', diskAdmissionMode=mode,
        mysqlMemoryBytes=1, hostAvailableMemoryBytes=1, diskBytesByPath={str(tmp_path): 112*1024**3})
    monkeypatch.setattr(staging.shutil, 'disk_usage', lambda p: SimpleNamespace(free=free_gib*1024**3))
    kwargs = dict(resource_budget=policy, capture_root=str(tmp_path),
        capture_limits=dict(maxWrittenBytes=64*1024**3, minimumFreeBytes=2*1024**3))
    if not admitted:
        with pytest.raises(admission.ResourceAdmissionError, match='TARGET_CAPACITY_NOT_AVAILABLE'):
            staging.check_target_staging_capacity(**kwargs)
    else:
        result = staging.check_target_staging_capacity(**kwargs)
        assert result['diskRequirements'][0]['requiredBytes'] == 178*1024**3
        assert result['diskRequirements'][0]['availableBytes'] == 122*1024**3
        assert result['diskRequirements'][0]['forecastReservationsEnforced'] is False


@pytest.mark.skipif(os.name != 'posix', reason='actual exclusive POSIX file staging')
@pytest.mark.parametrize('mode', ['OBSERVE_ONLY', 'RESERVE'])
def test_explicit_policy_is_staged_and_read_back_with_originals_retained(tmp_path, policy_inputs, mode):
    import test_main_program_target_control_candidate as units
    from test_main_program_target_control_staging import archive
    k = policy_inputs
    parent = tmp_path/'control'
    def relocate(value):
        if type(value) is str and value.startswith('/control'):
            return ':'.join(str(parent)+part[len('/control'):] if part.startswith('/control') else part
                for part in value.split(':'))
        if type(value) is dict: return {a: relocate(b) for a, b in value.items()}
        if type(value) is list: return [relocate(v) for v in value]
        return value
    k = relocate(k)
    units.graph_repin(k)
    units.repin(k)
    for targets in k['control']['restoreConfigurations'].values():
        targets[k['current_controller']['targetConfigRef']] = deepcopy(k['current_controller']['ownerConfigurationPin'])
    units.repin(k)
    old_raw, old_files = archive(k['previous_package_files'])
    raw, files = archive(k['package_files'])
    k['old_build']['packageSha256'] = k['current_controller']['packageSha256'] = digest(old_raw)
    k['new_build']['packages'][0].update(sha256=digest(raw), bytes=len(raw))
    for name, content in old_files.items():
        p = Path(k['current_controller']['engine'])/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        p.chmod(0o400)
    for value, key in ((k['owner'], 'ownerConfigurationPin'), (k['control'], 'controlConfigurationPin')):
        p = Path(k['current_controller'][key]['path'])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(canonical(value))
        p.chmod(0o400)
    k['disk_admission_mode'] = mode
    candidate = build(k)
    args = {name: value for name, value in k.items() if name not in ('package_files', 'previous_package_files')}
    args.update(candidate=candidate, package_raw=raw, previous_package_raw=old_raw)
    staging.preflight_target_filesystem(**args)
    result = staging.stage_target_filesystem(**args)
    assert result['status'] == 'FILES_STAGED_RUNTIME_UNVERIFIED'
    owner = json.loads(Path(candidate['controller']['ownerPin']['path']).read_bytes())
    assert owner['targetResourceAdmissionPolicies'][candidate['targetConfigRef']]['diskAdmissionMode'] == mode
    assert owner['targets'] == k['owner']['targets']
    assert Path(k['current_controller']['ownerConfigurationPin']['path']).read_bytes() == canonical(k['owner'])
