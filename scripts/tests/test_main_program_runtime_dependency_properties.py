"""systemd dependency sets have order-free identity; dropin order remains exact."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys

import pytest

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))


def subject():
    module=importlib.import_module('main_program_control_runtime')
    assert hasattr(module,'canonical_dependency_properties'),'MISSING_DEPENDENCY_PROPERTIES_CANONICALIZER'
    return module


def test_only_dependency_order_is_canonicalized_on_a_copy():
    module=subject();raw=dict(MainPID='18',Requires='z.service a.service',After='z.service b.target a.service',
        DropInPaths='/dropin/z.conf /dropin/a.conf',OpaqueProperty='keep original spelling')
    original=deepcopy(raw);value=module.canonical_dependency_properties(raw)
    assert value==dict(raw,Requires='a.service z.service',After='a.service b.target z.service')
    assert raw==original and value is not raw
    reordered=dict(raw,Requires='a.service z.service',After='a.service z.service b.target')
    assert module.canonical_dependency_properties(reordered)==value


@pytest.mark.parametrize('key',['After','Requires'])
@pytest.mark.parametrize('change',['add','remove'])
def test_any_dependency_addition_or_removal_is_still_detected(key,change):
    module=subject();raw={key:'a.service b.service'}
    changed={key:'a.service b.service unknown.service' if change=='add' else 'a.service'}
    assert module.canonical_dependency_properties(raw)!=module.canonical_dependency_properties(changed)


@pytest.mark.parametrize('key',['After','Requires'])
def test_repeated_dependency_is_rejected_instead_of_deduplicated(key):
    module=subject()
    with pytest.raises(ValueError,match='DEPENDENCY_DUPLICATE'):
        module.canonical_dependency_properties({key:'a.service b.service a.service'})


def test_dropin_order_and_unknown_properties_are_not_discarded():
    module=subject();raw=dict(DropInPaths='/z.conf /a.conf',Unknown='z a',Requires='z.service a.service')
    value=module.canonical_dependency_properties(raw)
    assert value['DropInPaths']=='/z.conf /a.conf' and value['Unknown']=='z a'
    assert value!=module.canonical_dependency_properties(dict(raw,DropInPaths='/a.conf /z.conf'))
    assert value!=module.canonical_dependency_properties(dict(raw,Unknown='a z'))
    assert value['Requires']=='a.service z.service'


def test_absent_or_empty_dependencies_are_preserved_without_inventing_fields():
    module=subject()
    assert module.canonical_dependency_properties({'MainPID':'1'})=={'MainPID':'1'}
    assert module.canonical_dependency_properties({'After':''})=={'After':''}


@pytest.mark.parametrize('value',[None,[],{'After':[]},{'Requires':None}])
def test_invalid_property_or_dependency_type_is_rejected(value):
    module=subject()
    with pytest.raises(ValueError):module.canonical_dependency_properties(value)


def test_systemctl_adapter_normalizes_controller_and_guard_properties():
    module=subject();responses=[b'MainPID=18\nAfter=z.service a.service\nRequires=z.service a.service\nDropInPaths=/z.conf /a.conf\n',
        b'MainPID=18\nAfter=a.service z.service\nRequires=a.service z.service\nDropInPaths=/z.conf /a.conf\n']
    gate=module.RuntimeGates({},run=lambda argv:responses.pop(0),verify_environment=lambda *a,**k:None,
        verify_custody=lambda *a,**k:None,lock_guard=lambda:None)
    assert gate.properties('controller.service')==gate.properties('guard.service')
