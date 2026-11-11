"""Finite test-carrier layout checks, never business or constructor success."""
import ast
import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

from recovery_engine import pin


ROOT = Path(__file__).resolve().parents[2]


def value_expression(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    matches = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    assert len(matches) == 1
    return matches[0]


def test_existing_producer_formal_layout_uses_actual_engine_sibling(tmp_path):
    expression = value_expression(ROOT/'scripts/tests/test_recovery_target_preservation_producer.py', 'formal')
    engine = tmp_path/'engine'
    actual_runtime = SimpleNamespace(__file__=str(engine/'common/recovery_minimal_runtime.py'))
    result = eval(compile(ast.Expression(expression), '<actual producer formal expression>', 'eval'),
        dict(Path=Path, runtime=actual_runtime))
    assert result == engine/'formal'


def test_existing_publication_binder_pin_uses_actual_loaded_original(tmp_path, monkeypatch):
    expression = value_expression(ROOT/'scripts/tests/test_recovery_target_preservation.py', 'repository_pin')
    values = [value for node in ast.walk(expression) if isinstance(node, ast.Call)
        for key, value in ((keyword.arg, keyword.value) for keyword in node.keywords)
        if key == 'captureBinderPin']
    assert len(values) == 1
    source = tmp_path/'source/ops/recovery/formal_capture_recovery_inputs.py'
    actual = tmp_path/'engine/common/formal_capture_recovery_inputs.py'
    for path, raw in ((source, b'# source input\n'), (actual, b'# actual authenticated candidate\n')):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    module = ModuleType('formal_capture_recovery_inputs')
    module.__file__ = str(actual)
    monkeypatch.setitem(__import__('sys').modules, module.__name__, module)
    result = eval(compile(ast.Expression(values[0]), '<actual publication binder expression>', 'eval'),
        dict(ROOT=tmp_path/'source', Path=Path, pin=pin, importlib=importlib))
    assert result == pin(actual)
