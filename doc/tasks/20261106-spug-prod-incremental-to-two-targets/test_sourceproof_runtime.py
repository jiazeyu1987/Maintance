"""Runtime binding unit tests plus replay of the exact installed configuration."""
import ast
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import verify_automatic_source_restoration as proof


@pytest.fixture
def installed():
    path=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/automatic-control-installation-57.private.json')
    value=json.loads(path.read_text(encoding='utf-8'))['controllers'][0]
    return value['control'],value['engine']


def test_runtime_uses_complete_pinned_configuration_path(installed):
    control,engine=installed
    paths=proof.source_runtime_paths(control,engine)
    assert paths==control['environment']['PYTHONPATH'].split(':')
    assert len(paths)==4
    assert paths[-1]=='/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/runtime/lib/python3.12/site-packages'


@pytest.mark.parametrize('change',['missing','relative','empty','duplicate','foreign-engine','parent','reorder','bytecode'])
def test_runtime_rejects_unbound_paths_before_import(installed,change):
    control,engine=installed
    paths=control['environment']['PYTHONPATH'].split(':')
    if change=='missing':paths=paths[:3]
    elif change=='relative':paths[-1]='relative/dependencies'
    elif change=='empty':paths.append('')
    elif change=='duplicate':paths.append(paths[-1])
    elif change=='foreign-engine':paths[0]='/unrelated/control'
    elif change=='parent':paths[-1]='/runtime/../other'
    elif change=='reorder':paths[0],paths[1]=paths[1],paths[0]
    else:control['environment']['PYTHONDONTWRITEBYTECODE']='0'
    control['environment']['PYTHONPATH']=':'.join(paths)
    with pytest.raises(ValueError):proof.source_runtime_paths(control,engine)


def test_transport_script_binds_runtime_before_product_import():
    tree=ast.parse(proof.SCRIPT)
    imported=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.ImportFrom) and n.module=='recovery_backup_epoch')
    bound=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and
        isinstance(n.value.func,ast.Name) and n.value.func.id=='bind_source_runtime')
    assert bound<imported
    assert 'sourceRuntime=source_runtime' in proof.SCRIPT


def test_runtime_probe_uses_real_installed_dependencies_and_no_business_calls():
    source=proof.SOURCE_RUNTIME
    tree=ast.parse(source)
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='import_module' for n in ast.walk(tree))
    assert not any(isinstance(n,ast.Name) and n.id in {'subprocess','remote','Native','Ledger'} for n in ast.walk(tree))
    assert 'SOURCE_RUNTIME_MODULE_CHANGED' in source and 'SOURCE_RUNTIME_PYTHON_CHANGED' in source


def test_actual_readonly_runtime_proof_includes_native_dependency_closure():
    path=Path(__file__).parent/'automatic-sourceproof-runtime-imports-complete.json'
    value=json.loads(path.read_text(encoding='utf-8'))
    assert value['status']=='PASS' and value['installedServiceModulePathVerified'] is True
    assert value['serverWrites'] is value['controlApiCalled'] is value['sqlCalled'] is value['sourceProofExecuted'] is False
    runtime=value['runtime']
    assert len(runtime['modulePins'])==3 and len(runtime['dependencyPins'])==40
    assert any(pin['path'].endswith('.so') for pin in runtime['dependencyPins'].values())
    assert set(runtime['modulePins'])=={'recovery_backup_epoch','recovery_main_target','recovery_engine'}
    for pin in runtime['dependencyPins'].values():
        assert pin['path'].startswith(runtime['modulePaths'][-1]+'/')
        assert pin['bytes']>0 and len(pin['sha256'])==64
