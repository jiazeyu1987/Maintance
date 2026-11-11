"""Static-template units with actual Linux context/flock/private originals.

The existing bounded Docker/SQL/S3/SMB protocol fixture is only input material.
These tests never admit a CIFS view or claim business restoration.  Successful
v2 prepare needs the separate real-CIFS facility; there is no skip or fallback.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from test_recovery_target_preservation import (
    publication_case, capture_protocol, case, restore_case, construct,
    claim, locked, started, context, freeze_inputs)
from recovery_engine import Budget, RecoveryError, pin, pinned_json, write
from repository_records import RepositoryError
import recovery_target_preservation as preservation


def require_linux():
    assert sys.platform.startswith('linux'), 'TEST_REQUIRES_REAL_LINUX_NOT_A_SKIP'


def register_v2(h, monkeypatch, *, template_changes=None, view_changes=None):
    """Fixture setup before immutable owner/request binding, never during use."""
    # publication_case already reserved its v1 owner. Preserve those originals;
    # the new configuration needs its own real reservation, not overwritten pins.
    operations = h.case['root']/'preservation-v2-operations'
    operations.mkdir(mode=0o700)
    h.root = operations/'restore-1'; h.root.mkdir(mode=0o700)
    host = h.case['root']/'preservation-v2-host'; host.mkdir(mode=0o700)
    import recovery_resource_admission as admission
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.owner['operationsRoot'] = str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin'] = write(h.case['root']/'preservation-v2-target.json',
        h.owner['targets']['target57'])
    capture = deepcopy(h.capture_config)
    capture.pop('archiveRoot')
    capture.update(schemaVersion='MainTargetCaptureConfiguration/v1',
        outputRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE')
    h.case['base_pin'] = write(h.case['root']/'main-preservation-capture-v1.json',capture)
    h.case['policy']['captureConfigurationPins'] = {'source57':h.case['base_pin']}
    h.owner['targetProgramPolicies']['target57'] = deepcopy(h.case['policy'])
    repository = deepcopy(pinned_json(h.repository_pin))
    template = deepcopy(pinned_json(repository.pop('readbackConfigPin')))
    template.pop('recordRoot')
    template.update(schemaVersion='MainTargetPreservationReadbackTemplate/v1',
        recordRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION')
    if template_changes:
        template.update(template_changes)
    metadata = h.case['root']/'preservation-protocol-inputs'
    h.template_pin = write(metadata/'readback-template-v2.json', template)
    view = dict(mountPoint=str(h.repository), filesystem='cifs',
        mountSource='//finite/share', mountRoot='/repository')
    if view_changes:
        view.update(view_changes)
    repository.update(schemaVersion='MainTargetPreservationRepository/v2',
        readbackTemplatePin=h.template_pin, writeView=view)
    h.v2_repository_pin = write(metadata/'repository-v2.json', repository)
    policy = deepcopy(pinned_json(h.preservation_policy))
    policy.update(schemaVersion='MainTargetPreservationPolicy/v2',
        repositoryConfigurationPin=h.v2_repository_pin,
        captureConfigurationPin=h.case['base_pin'])
    h.v2_policy_pin = write(metadata/'policy-v2.json', policy)
    h.owner['targetPreservationPolicies'] = {'target57':h.v2_policy_pin}
    freeze_inputs(h)
    return h


@contextmanager
def original_context(h):
    require_linux()
    claim(h.case)
    with locked(h.case) as fd:
        _, binding, _ = started(h, fd)
        with context(h, binding, fd, budget=Budget(240000)) as ctx:
            native = construct(h, ctx)
            yield native, ctx


def derive(h, native):
    return preservation._derive_readback_configuration(native, policy_pin=h.v2_policy_pin)


def assert_no_repository_or_business_writes(h, before):
    assert h.engine.actions == before
    assert not (h.repository/'.repository-control').exists()
    assert not (h.repository/'preservations').exists()
    state = json.loads(h.state_path.read_bytes())
    assert state['actions'] == [] and state['flags'] == ['0', '0']


def test_template_derives_private_originals_from_real_context_only(publication_case,monkeypatch):
    h = register_v2(publication_case,monkeypatch)
    original = {p['path']:Path(p['path']).read_bytes()
        for p in (h.template_pin,h.v2_repository_pin,h.v2_policy_pin,h.owner_pin,h.request_pin)}
    with original_context(h) as (native, ctx):
        before = deepcopy(h.engine.actions)
        # A mutable native output is deliberately unrelated to the fixed ctx root.
        native.root = h.case['root']/'unrelated-native-output'
        result = derive(h, native)
        assert set(result) == {'configurationPin','derivationPin'}
        expected_root = h.root/'target-preservation'/'publication'
        configuration = pinned_json(result['configurationPin'])
        template = pinned_json(h.template_pin)
        expected = {key:value for key,value in template.items()
            if key not in ('schemaVersion','recordRootPolicy')}
        expected.update(schemaVersion='RepositorySmbReadbackConfig/v1', recordRoot=str(expected_root))
        assert configuration == expected
        assert result['configurationPin']['path'] == str(expected_root/'readback-configuration.json')
        assert result['derivationPin']['path'] == str(expected_root/'readback-derivation.json')
        assert pinned_json(result['derivationPin']) == dict(
            schemaVersion='MainTargetPreservationReadbackDerivation/v1',
            operationId=h.request['operationId'], targetConfigRef='target57',
            policyPin=h.v2_policy_pin, repositoryConfigurationPin=h.v2_repository_pin,
            templatePin=h.template_pin, executionBindingPin=ctx._binding,
            operationRoot=str(h.root), configurationPin=result['configurationPin'])
        for reference in result.values():
            info = Path(reference['path']).stat()
            assert info.st_mode & 0o777 == 0o600 and info.st_nlink == 1
        assert_no_repository_or_business_writes(h, before)
    assert all(Path(path).read_bytes() == raw for path,raw in original.items())


def test_template_same_operation_never_overwrites_derived_originals(publication_case,monkeypatch):
    h = register_v2(publication_case,monkeypatch)
    with original_context(h) as (native, _):
        before = deepcopy(h.engine.actions)
        result = derive(h, native)
        originals = {p['path']:(Path(p['path']).read_bytes(),Path(p['path']).stat().st_ino,
            Path(p['path']).stat().st_mode) for p in result.values()}
        with pytest.raises((RepositoryError,RecoveryError,FileExistsError),
                match='PRESERVATION_READBACK_ALREADY_DERIVED|File exists'):
            derive(h, native)
        assert all((Path(path).read_bytes(),Path(path).stat().st_ino,
            Path(path).stat().st_mode)==value for path,value in originals.items())
        assert_no_repository_or_business_writes(h, before)


@pytest.mark.parametrize('change', [
    {'schemaVersion':'MainTargetPreservationReadbackTemplate/v9'},
    {'recordRoot':'/arbitrary-output'},
    {'command':['sh','-c','true']},
    {'recordRootPolicy':'USER_SELECTED_DIRECTORY'},
    {'repositoryRoot':'/different-repository'},
])
def test_template_rejects_unregistered_shape_or_output_before_writes(publication_case,monkeypatch,change):
    h = register_v2(publication_case,monkeypatch,template_changes=change)
    with original_context(h) as (native,_):
        before = deepcopy(h.engine.actions)
        with pytest.raises((RepositoryError,RecoveryError),match='PRESERVATION_READBACK_TEMPLATE_INVALID|PRESERVATION_READBACK_SCOPE_CHANGED'):
            derive(h,native)
        assert_no_repository_or_business_writes(h,before)
        assert not (h.root/'target-preservation'/'publication'/'readback-configuration.json').exists()


def test_template_pin_drift_is_not_accepted_by_rehashing(publication_case,monkeypatch):
    h = register_v2(publication_case,monkeypatch)
    with original_context(h) as (native,_):
        before = deepcopy(h.engine.actions)
        path = Path(h.template_pin['path'])
        path.write_bytes(path.read_bytes()+b' ')
        with pytest.raises((RepositoryError,RecoveryError,ValueError),match='PRESERVATION_.*CHANGED|PIN_|BYTES_CHANGED|INPUT_CHANGED'):
            derive(h,native)
        assert_no_repository_or_business_writes(h,before)


@pytest.mark.parametrize('change', [
    {'filesystem':'ext4'}, {'mountSource':'//other/share'},
    {'mountRoot':'/other-repository'}, {'mountId':1234},
])
def test_static_write_view_has_only_stable_cifs_mapping(publication_case,monkeypatch,change):
    h = register_v2(publication_case,monkeypatch,view_changes=change)
    with original_context(h) as (native,_):
        before = deepcopy(h.engine.actions)
        with pytest.raises((RepositoryError,RecoveryError),match='PRESERVATION_WRITE_VIEW_INVALID|PRESERVATION_READBACK_SCOPE_CHANGED'):
            derive(h,native)
        assert_no_repository_or_business_writes(h,before)
