"""Actual prepare evidence-scope seam plus readonly real r7 preparation.

The AST harness executes the one original loop unchanged, preserving actual
verify_local_pin. Temporary bundle values are the already-validated loader output
protocol boundary, never substitutes for the separate real-r7 prepare test.
"""
import ast
import copy
from pathlib import Path

import pytest
import main_program_control_activation as subject


def scope(task, private, references, *, generation, bundle):
    tree = ast.parse(Path(subject.__file__).read_text(encoding='utf-8'))
    prepare = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare')
    loops = [n for n in ast.walk(prepare) if isinstance(n, ast.For) and
        isinstance(n.target, ast.Name) and n.target.id == 'item' and
        isinstance(n.iter, ast.Subscript) and isinstance(n.iter.value, ast.Name) and n.iter.value.id == 'selected' and
        isinstance(n.iter.slice, ast.Constant) and n.iter.slice.value == 'localInstallationPins']
    assert len(loops) == 1, 'The actual scope seam must remain uniquely identifiable'
    code = ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(loops[0])], type_ignores=[]))
    namespace = dict(subject.__dict__, task=task, private=private, selected=dict(localInstallationPins=references),
                     generation=generation, bundle=bundle)
    exec(compile(code, '<actual-prepare-evidence-scope>', 'exec'), namespace)


@pytest.fixture
def layout(tmp_path):
    paths = {key: tmp_path / name for key, name in [('task', 'task'), ('private', 'private'), ('source', 'main-source')]}
    for path in paths.values(): path.mkdir()
    return paths


def material(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'physical immutable input\x00\xff')
    return subject.file_pin(path)


@pytest.mark.parametrize('location', ['source', 'private-release', 'private-package'])
def test_generation_accepts_exact_verified_external_closure_member(layout, location):
    path = layout['source'] / 'backend.py' if location == 'source' else layout['private'] / location / 'package.bin'
    reference = material(path)
    scope(layout['task'], layout['private'], [reference], generation=True, bundle=dict(inputPins=[reference]))


@pytest.mark.parametrize('drift', ['missing', 'path', 'bytes', 'sha256', 'extra-field'])
def test_generation_rejects_nonmember_even_inside_old_allowed_task_directory(layout, drift):
    reference = material(layout['task'] / 'original.json')
    authorized = copy.deepcopy(reference)
    if drift == 'path': authorized['path'] = str(layout['task'] / 'same-content.json'); material(Path(authorized['path']))
    elif drift == 'bytes': authorized['bytes'] += 1
    elif drift == 'sha256': authorized['sha256'] = 'f' * 64
    elif drift == 'extra-field': authorized['unreviewed'] = True
    with pytest.raises(ValueError, match='ORIGINAL_EVIDENCE_SCOPE'):
        scope(layout['task'], layout['private'], [reference], generation=True,
            bundle=dict(inputPins=[] if drift == 'missing' else [authorized]))


def test_generation_rejects_lexical_alias_not_exact_member(layout):
    reference = material(layout['task'] / 'original.bin')
    (layout['task'] / 'sub').mkdir()
    alias = dict(reference, path=str(layout['task'] / 'sub' / '..' / 'original.bin'))
    with pytest.raises(ValueError, match='ORIGINAL_EVIDENCE_SCOPE'):
        scope(layout['task'], layout['private'], [alias], generation=True, bundle=dict(inputPins=[reference]))


def test_generation_still_verifies_actual_file_after_membership(layout):
    reference = material(layout['task'] / 'original.bin')
    Path(reference['path']).write_bytes(b'changed after generation read')
    with pytest.raises(ValueError, match='PIN_CHANGED'):
        scope(layout['task'], layout['private'], [reference], generation=True, bundle=dict(inputPins=[reference]))


def test_generation_rejects_leaf_symlink_even_if_member(layout):
    target = layout['task'] / 'target.bin'; reference = material(target)
    alias = layout['task'] / 'alias.bin'
    alias.symlink_to(target)
    reference = dict(reference, path=str(alias))
    with pytest.raises(ValueError, match='FILE_ALIAS'):
        scope(layout['task'], layout['private'], [reference], generation=True, bundle=dict(inputPins=[reference]))


def test_legacy_accepts_only_direct_task_file_without_bundle(layout):
    reference = material(layout['task'] / 'original.bin')
    scope(layout['task'], layout['private'], [reference], generation=False, bundle=None)


@pytest.mark.parametrize('location', ['task-child', 'private', 'source'])
def test_legacy_rejects_old_out_of_scope_even_with_supplied_bundle(layout, location):
    path = layout['task'] / 'nested' / 'original.bin' if location == 'task-child' else layout[location] / 'original.bin'
    reference = material(path)
    with pytest.raises(ValueError, match='ORIGINAL_EVIDENCE_SCOPE'):
        scope(layout['task'], layout['private'], [reference], generation=False, bundle=dict(inputPins=[reference]))


def test_real_r7_default_prepare_is_readonly_and_accepts_verified_generation_closure():
    task, private = subject.TASK, subject.PRIVATE
    name = 'main-program-control-activation-59-target-b5fa4c5-r7-inputs.json'
    inputs = subject.read_document(task / name)
    original = subject.file_pin(task / name)
    outputs = [task / inputs['outputFile'], private / inputs['outputFile'].replace('.json', '.attempt.private.json'),
               private / inputs['outputFile'].replace('.json', '.private.json')]
    assert not any(path.exists() or path.is_symlink() for path in outputs), 'Real r7 has already dispatched; do not treat this as a unit fixture'
    spec, payload = subject.prepare(task, private, name)
    assert spec['inputs'] == inputs
    result = subject.dispatch_prepared(task, private, spec, payload)
    assert result['status'] == 'PREPARED_NOT_ACTIVATED' and result['remoteDispatched'] is False
    assert subject.file_pin(task / name) == original
    assert not any(path.exists() or path.is_symlink() for path in outputs)
