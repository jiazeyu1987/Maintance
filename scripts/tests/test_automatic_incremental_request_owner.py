"""Original request-derived owners must close without a browser operation query."""
from copy import deepcopy
from pathlib import Path

import pytest

import recovery_control_executor as executor
from recovery_control_smallapp import local_read
from test_automatic_incremental_plan import LocalNative
from test_automatic_incremental_unpolled import UnpolledFixture


def test_request_derived_owner_closes_and_selects_original_incremental(tmp_path):
    f = UnpolledFixture(tmp_path, request_bound_owner=True)
    try:
        f.finish()
        inputs_pin = executor.pin(f.request_root / 'request-inputs.json')
        plan = LocalNative(f.native.config_pin).incremental_plan('source-A')
        assert (plan['state'], plan['parentChainRef'], plan['baseFullRef'], plan['chainDepth']) == (
            'READY', f.reference, 'full-root', 2), plan
        assert all(p.is_file() for p in f.registration_paths)
        assert executor.pin(f.directory / 'completion.json') == f.completion_pin
        assert executor.pin(f.owner_root / 'result.json') == f.result_pin
        assert executor.pin(f.request_root / 'request-inputs.json') == inputs_pin
        assert not (f.directory / 'queries').exists()
        assert LocalNative(f.native.config_pin).incremental_plan('source-A') == plan
    finally:
        f.close()


def bad_owner(case):
    def change(owner, inputs, f):
        if case == 'request':
            inputs['request'] = dict(inputs['request'], operationId='different-operation')
        elif case == 'template':
            inputs['ownerConfigurationPin'] = inputs['captureConfigurationPin']
        elif case == 'parent-binding':
            inputs['pointBindingPin'] = inputs['captureConfigurationPin']
        elif case == 'parent-reference':
            owner['parentChains'] = {'different-parent': f.metadata.points['full-root']['pointPin']}
        elif case == 'parent-point':
            owner['parentChains'] = {'full-root': inputs['captureConfigurationPin']}
        elif case == 'capture-path':
            owner['sources']['source-A']['configurationPath'] = str(f.root / 'unrelated-capture.json')
        elif case == 'extra-owner-field':
            owner['unapproved'] = True
        elif case == 'other-source':
            owner['sources']['source-B'] = deepcopy(owner['sources']['source-A'])
        elif case == 'operation-root':
            owner['operationRoot'] = str(f.root / 'different-owners')
        elif case == 'inputs-field':
            inputs['unapproved'] = True
        else:
            raise AssertionError(case)
    return change


@pytest.mark.parametrize('case', ['request', 'template', 'parent-binding', 'parent-reference',
    'parent-point', 'capture-path', 'extra-owner-field', 'other-source', 'operation-root', 'inputs-field'])
def test_request_owner_derivation_rejects_unbound_evidence(tmp_path, case):
    f = UnpolledFixture(tmp_path, request_bound_owner=True, mutate_owner=bad_owner(case))
    try:
        f.finish()
        plan = LocalNative(f.native.config_pin).incremental_plan('source-A')
        assert plan['state'] == 'BLOCKED', plan
        assert plan['reasonCode'] == ('ORIGINAL_OWNER_ADMISSION_NOT_FOUND' if case == 'operation-root'
            else 'SOURCE_POINT_OWNER_BINDING_INVALID'), plan
        assert not any(p.exists() for p in f.registration_paths)
        assert executor.pin(f.directory / 'completion.json') == f.completion_pin
        assert executor.pin(f.owner_root / 'result.json') == f.result_pin
        assert not (f.directory / 'queries').exists()
    finally:
        f.close()


def test_request_owner_missing_inputs_never_publishes_partial_point(tmp_path):
    f = UnpolledFixture(tmp_path, request_bound_owner=True)
    try:
        f.finish()
        (f.request_root / 'request-inputs.json').unlink()
        plan = LocalNative(f.native.config_pin).incremental_plan('source-A')
        assert plan['state'] == 'BLOCKED', plan
        assert not any(p.exists() for p in f.registration_paths)
    finally:
        f.close()


@pytest.mark.parametrize('changed', ['capture', 'objects', 'both'])
def test_closed_request_uses_frozen_owner_after_shared_templates_upgrade(tmp_path, changed):
    f = UnpolledFixture(tmp_path, request_bound_owner=True)
    try:
        f.finish()
        inputs_pin = executor.pin(f.request_root / 'request-inputs.json')
        frozen_capture = executor.pin(f.request_root / 'capture.json')
        for name in ('capture', 'objects'):
            if changed in (name, 'both'):
                (tmp_path / (name + '-template.json')).write_text('{"generation":"later"}\n', encoding='utf-8')
        plan = LocalNative(f.native.config_pin).incremental_plan('source-A')
        assert (plan['state'], plan['parentChainRef']) == ('READY', f.reference), plan
        assert all(p.is_file() for p in f.registration_paths)
        assert executor.pin(f.request_root / 'request-inputs.json') == inputs_pin
        assert executor.pin(f.request_root / 'capture.json') == frozen_capture
        assert executor.pin(f.directory / 'completion.json') == f.completion_pin
        assert executor.pin(f.owner_root / 'result.json') == f.result_pin
        assert not (f.directory / 'queries').exists()
    finally:
        f.close()
