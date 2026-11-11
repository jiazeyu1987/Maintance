"""Early actual-package API contracts; the complete producer still runs later.

These checks bind the delivered caller's real arguments to the delivered strict
callee. They do not execute a capture, replace a method, or prove a restoration.
"""
import ast
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path

import pytest


@pytest.mark.parametrize('edge', ['stream', 'verify', 'assemble_readback_bindings', 'repository_binding'])
def test_actual_standard_preservation_calls_bind_to_strict_apis(edge):
    assert os.name == 'posix'
    root = Path(os.environ['RECOVERY_TEST_FORMAL_DIRECTORY']).parent
    manifest = json.loads((root / 'package.json').read_bytes())
    assert manifest['variant'] == 'standard' and manifest['candidateOnly'] is True
    caller = importlib.import_module('recovery_target_preservation')
    path = root / 'common/recovery_target_preservation.py'
    assert Path(caller.__file__).resolve() == path.resolve()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][
        'common/recovery_target_preservation.py']
    if edge == 'stream':
        from repository_minimal import CapturedPublisher
        callee, implicit, expected = CapturedPublisher.stream, 1, 1
    elif edge == 'verify':
        from repository_native_readback import PreservationReadback
        callee, implicit, expected = PreservationReadback.verify, 1, 1
    elif edge == 'assemble_readback_bindings':
        from repository_binding import assemble_readback_bindings
        callee, implicit, expected = assemble_readback_bindings, 0, 2
    else:
        from repository_binding import repository_binding
        callee, implicit, expected = repository_binding, 0, 2
    calls = [node for node in ast.walk(ast.parse(path.read_bytes()))
        if isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name) and node.func.id == edge or
            isinstance(node.func, ast.Attribute) and node.func.attr == edge)]
    assert len(calls) == expected, 'PUBLICATION_CALL_SET_CHANGED'
    for call in calls:
        assert not any(isinstance(arg, ast.Starred) for arg in call.args)
        assert all(keyword.arg is not None for keyword in call.keywords)
        keywords = {keyword.arg: object() for keyword in call.keywords}
        assert len(keywords) == len(call.keywords)
        inspect.signature(callee).bind(*[object() for _ in range(implicit + len(call.args))], **keywords)
