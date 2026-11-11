"""MAIN output identity over real ctx/flock/files and finite external protocols.

This exercises target capture preparation only, not a business backup or CIFS
publication. The ordinary source configuration remains a separate contract.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from test_recovery_target_capture_session import (
    capture_protocol,case,restore_case,construct,claim,locked,started,context,freeze_inputs)
from recovery_engine import Budget,RecoveryError,pinned_json,write
from formal_snapshot_linux import FormalSnapshotError
import recovery_resource_admission as admission
import minimal_capture_support as support
from recovery_target_capture import MainTargetCapture


@pytest.fixture
def main_configuration_case(capture_protocol,monkeypatch):
    assert sys.platform.startswith('linux'),'TEST_REQUIRES_REAL_LINUX_NOT_A_SKIP'
    h=capture_protocol
    # Never overwrite the prior source fixture's real reservation.
    operations=h.case['root']/'main-configuration-operations';operations.mkdir(mode=0o700)
    h.root=operations/'restore-1';h.root.mkdir(mode=0o700)
    host=h.case['root']/'main-configuration-host';host.mkdir(mode=0o700)
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.owner['operationsRoot']=str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin']=write(h.case['root']/'main-configuration-target.json',
        h.owner['targets']['target57'])
    h.main_configuration=deepcopy(h.capture_config)
    h.main_configuration.pop('archiveRoot')
    h.main_configuration.update(schemaVersion='MainTargetCaptureConfiguration/v1',
        outputRootPolicy='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE')
    h.main_configuration['limits'].update(querySeconds=30,workSeconds=180)
    h.case['base_pin']=write(h.case['root']/'main-capture-configuration.json',h.main_configuration)
    h.case['policy']['captureConfigurationPins']={'source57':h.case['base_pin']}
    h.owner['targetProgramPolicies']['target57']=deepcopy(h.case['policy'])
    freeze_inputs(h)
    return h


@contextmanager
def original_context(h):
    claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=Budget(240000)) as ctx:
            yield construct(h,ctx),ctx


def test_main_configuration_prepares_independent_of_incoming_archive_membership(main_configuration_case):
    h=main_configuration_case
    before=Path(h.case['base_pin']['path']).read_bytes()
    with original_context(h) as (native,ctx):
        assert 'archiveRoot' not in h.main_configuration
        assert str(ctx._root/'target-preservation'/'capture') not in native.source['archiveRoots']
        result=MainTargetCapture.prepare(native,capture_ref='source57',reservation_pin=h.reservation)
        assert result.root==ctx._root/'target-preservation'/'capture'
        assert result.config==h.main_configuration and result._state=='PREPARED'
        intent=pinned_json(result._pins[str(result._journal/'intent.json')])
        assert intent['configurationPin']==h.case['base_pin'] and intent['executionBindingPin']==ctx._binding
        state=json.loads(h.state_path.read_bytes())
        assert state['actions']==[] and state['flags']==['0','0']
        assert all(row['running'] for row in state['containers'].values())
        assert not h.transport.releases
    assert Path(h.case['base_pin']['path']).read_bytes()==before


def test_main_shared_values_are_validated_without_enabling_ordinary_worker(main_configuration_case):
    h=main_configuration_case
    assert support.validate_main_target_config(h.main_configuration) is None
    assert support.validate_config(h.capture_config)==Path(h.capture_config['archiveRoot'])
    with pytest.raises(FormalSnapshotError,match='MINIMAL_CAPTURE_CONFIG_INVALID'):
        support.validate_config(h.main_configuration)


@pytest.mark.parametrize('problem',['schema','archive','output','parent','limits'])
def test_main_configuration_rejects_unknown_or_arbitrary_output(main_configuration_case,problem):
    config=deepcopy(main_configuration_case.main_configuration)
    if problem=='schema':config['schemaVersion']='MainTargetCaptureConfiguration/v2'
    elif problem=='archive':config['archiveRoot']='/arbitrary-output'
    elif problem=='output':config['outputRootPolicy']='USER_SELECTED'
    elif problem=='parent':config['parent']={'unregistered':True}
    else:config['limits']['workSeconds']=0
    with pytest.raises(FormalSnapshotError,match='MAIN_TARGET_CAPTURE_CONFIG_INVALID|MINIMAL_LIMITS_INVALID'):
        support.validate_main_target_config(config)


@pytest.mark.parametrize('problem',['uuid','lock','writers'])
def test_main_configuration_keeps_original_target_identity_checks(main_configuration_case,problem):
    h=main_configuration_case
    with original_context(h) as (native,_):
        config=deepcopy(h.main_configuration)
        if problem=='uuid':config['source']['databaseUuid']='11111111-1111-1111-1111-111111111111'
        elif problem=='lock':config['sourceLockPath']=str(h.case['root']/'different.lock')
        else:config['source']['writerContainerIds']=['d'*64]
        before=deepcopy(h.engine.actions)
        with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED'):
            MainTargetCapture._configuration(native,'source57',config)
        assert h.engine.actions==before and json.loads(h.state_path.read_bytes())['actions']==[]


def test_main_configuration_refuses_unregistered_native_output(main_configuration_case):
    h=main_configuration_case
    with original_context(h) as (native,_):
        native.root=h.case['root']/'unregistered-output'
        with pytest.raises(RecoveryError,match='REPLACEMENT_PROTECTED_ROOT_REQUIRED'):
            MainTargetCapture.prepare(native,capture_ref='source57',reservation_pin=h.reservation)
        assert json.loads(h.state_path.read_bytes())['actions']==[]


@pytest.mark.parametrize('problem',['material-membership','container-name-keys'])
def test_main_configuration_requires_role_keyed_version_original_in_materials(main_configuration_case,problem):
    h=main_configuration_case
    with original_context(h) as (native,_):
        config=deepcopy(h.main_configuration)
        if problem=='material-membership':config['source']['materialPins']=[]
        else:
            descriptor=pinned_json(config['source']['objectSourcePin'])
            original=pinned_json(descriptor['versionPins'][0])
            changed=dict(images={'container-name-'+role:value for role,value in original['images'].items()})
            version=write(h.case['root']/'wrong-version-role-map.json',changed)
            descriptor['versionPins']=[version]
            config['source']['objectSourcePin']=write(h.case['root']/'wrong-role-objects.json',descriptor)
            config['source']['materialPins']=[dict(purpose='versions',reference=version)]
        with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_VERSION_CHANGED'):
            MainTargetCapture._configuration(native,'source57',config)
        assert json.loads(h.state_path.read_bytes())['actions']==[]
