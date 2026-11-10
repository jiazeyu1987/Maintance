"""Real temporary Git component roots; no installed runtime, Docker or network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_main_program_ui_preflight as ui
from prepare_automatic_ui_preflight import verify_stage_deployment_inputs
from test_automatic_ui_preflight_git import git, put, commit


@pytest.fixture
def roots(tmp_path, monkeypatch):
    dev = tmp_path / 'development'; dev.mkdir()
    task = tmp_path / 'task'; task.mkdir()
    git(dev, 'init', '-q'); git(dev, 'config', 'core.autocrlf', 'false')
    mapping = {'backend/capture.py': 'control/capture.py'}
    put(dev, 'ops/backup_engine/files.json', json.dumps(mapping))
    for name in [*mapping, 'ops/recovery/epoch.py', 'ops/spug/smallapp-ui/app.js']:
        put(dev, name)
    spug_commit = commit(dev, 'installed Spug')
    put(dev, 'backend/capture.py', 'source generation\n')
    put(dev, 'ops/spug/smallapp-ui/app.js', 'later uninstalled UI\n')
    source_commit = commit(dev, 'installed source with independent UI change')
    source = tmp_path / 'source-release'; spug = tmp_path / 'spug-release'
    git(dev, 'worktree', 'add', '--detach', str(source), source_commit)
    git(dev, 'worktree', 'add', '--detach', str(spug), spug_commit)
    source_build = dict(status='PASS', targetCommit=source_commit, worktree=str(source),
                        allFilesShaAndCompileVerified=True)
    spug_build = dict(schemaVersion='MainProgramSpugResourceBuild/v2', status='PASS',
                      sourceCommit=spug_commit, worktree=str(spug), fileCount=1,
                      files={'ops/spug/smallapp-ui/app.js': {'bytes': 9, 'sha256': 'a'*64}})
    pins = []
    def save(name, value):
        path = task / name; raw = json.dumps(value).encode('utf-8'); path.write_bytes(raw)
        ref = dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        pins.append(dict(path=str(path), bytes=ref['bytes'], sha256=ref['sha256']))
        return ref
    build_pin = save('source-build.json', source_build)
    spug_pin = save('spug-build.json', spug_build)
    verified = dict(selection={'sourceCommit': source_commit},
                    generation={'generation': {'buildPin': build_pin}, 'build': source_build},
                    spugRuntime={'resourceBuildPin': spug_pin, 'resourceBuild': spug_build}, inputPins=pins)
    monkeypatch.setattr(ui, 'TASK', task)
    return SimpleNamespace(dev=dev, task=task, source=source, spug=spug, verified=verified,
                           source_commit=source_commit, spug_commit=spug_commit)


def check(r, **changes):
    args = dict(source_deployment_root=str(r.source), spug_deployment_root=str(r.spug))
    args.update(changes)
    return ui.verify_main_deployment_inputs(r.verified, r.dev, **args)


def test_two_registered_roots_keep_real_different_heads_and_full_scopes(roots):
    put(roots.dev, 'backend/capture.py', 'uncommitted development\n')
    before = (roots.dev / 'backend/capture.py').read_bytes()
    value = check(roots)
    assert value['source']['headCommit'] == roots.source_commit
    assert value['spug']['headCommit'] == roots.spug_commit != roots.source_commit
    assert 'backend/capture.py' in value['source']['deploymentInputScopes']
    assert value['spug']['deploymentInputScopes'] == ['ops/spug/smallapp-ui/app.js']
    for component, root, ref in [('source', roots.source, roots.verified['generation']['generation']['buildPin']),
                                  ('spug', roots.spug, roots.verified['spugRuntime']['resourceBuildPin'])]:
        binding = value['deploymentRootBindings'][component]
        assert binding == dict(schemaVersion='MainProgramDeploymentRoot/v1', mode='PINNED_BUILD_WORKTREE',
                               path=root.as_posix(), buildPin=ref, targetCommit=value[component]['installedCommit'],
                               headCommit=value[component]['headCommit'], registeredWorktreeMatched=True, clean=True)
    assert (roots.dev / 'backend/capture.py').read_bytes() == before


def test_default_and_original_shared_root_still_reject_real_app_js_drift(roots):
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        ui.verify_main_deployment_inputs(roots.verified, roots.source)
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        verify_stage_deployment_inputs(roots.source, roots.source_commit, roots.spug_commit, ['smallapp-ui/app.js'])


@pytest.mark.parametrize('missing', ['source_deployment_root', 'spug_deployment_root'])
def test_only_one_explicit_root_is_rejected(roots, missing):
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_ROOT_PAIR_REQUIRED'):
        check(roots, **{missing: None})


@pytest.mark.parametrize('kind', ['relative', 'missing', 'alias', 'other', 'swapped'])
def test_explicit_root_must_be_exact_registered_directory(roots, kind):
    value = {'relative': 'source-release', 'missing': str(roots.task/'missing'),
             'alias': str(roots.source/'..'/'source-release'), 'other': str(roots.dev),
             'swapped': str(roots.spug)}[kind]
    with pytest.raises((ValueError, FileNotFoundError), match='MAIN_DEPLOYMENT_ROOT|No such file|cannot find'):
        check(roots, source_deployment_root=value)


@pytest.mark.parametrize('component', ['source', 'spug'])
@pytest.mark.parametrize('state', ['unstaged', 'staged', 'untracked', 'head'])
def test_each_root_rejects_dirty_or_other_head(roots, component, state):
    root = getattr(roots, component)
    name = 'backend/capture.py' if component == 'source' else 'ops/spug/smallapp-ui/app.js'
    if state == 'untracked': name = 'untracked-evidence.txt'
    put(root, name, 'uninstalled change\n')
    if state == 'staged': git(root, 'add', name)
    if state == 'head': commit(root, 'other checkout generation')
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_ROOT_(DIRTY|HEAD_CHANGED)'):
        check(roots)


@pytest.mark.parametrize('component', ['source', 'spug'])
def test_full_build_object_not_only_its_path_is_bound(roots, component):
    container = roots.verified['generation'] if component == 'source' else roots.verified['spugRuntime']
    key = 'build' if component == 'source' else 'resourceBuild'
    container[key] = dict(container[key], unexpected=True)
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_BUILD_CHANGED'):
        check(roots)


def test_build_bytes_changed_is_rejected(roots):
    with (roots.task/'spug-build.json').open('ab') as handle: handle.write(b' ')
    with pytest.raises((ValueError, AssertionError)):
        check(roots)


def test_final_recheck_rejects_a_real_change_after_initial_proof(roots):
    check(roots)
    put(roots.spug, 'ops/spug/smallapp-ui/app.js', 'changed after observation\n')
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_ROOT_DIRTY'):
        check(roots)


def test_git_root_must_be_top_level_even_if_build_registers_subdirectory(roots):
    build = roots.verified['generation']['build']; build['worktree'] = str(roots.source/'backend')
    raw = json.dumps(build).encode('utf-8'); (roots.task/'source-build.json').write_bytes(raw)
    ref = dict(file='source-build.json', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    roots.verified['generation']['generation']['buildPin'] = ref
    roots.verified['inputPins'][0] = dict(path=str(roots.task/'source-build.json'), bytes=len(raw), sha256=ref['sha256'])
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_ROOT_NOT_GIT_ROOT'):
        check(roots, source_deployment_root=build['worktree'])


def test_invalid_roots_fail_before_any_external_observation(roots, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['preflight', '--cycle', 'local-test', '--kind', 'I1', '--phase',
        'preview', '--observation', 'once', '--selection', 'selection.json',
        '--source-deployment-root', str(roots.dev), '--spug-deployment-root', str(roots.spug)])
    monkeypatch.setattr(ui, 'load_current_installation', lambda *a, **k: dict(roots.verified, selectionPin={}))
    def forbidden(*a, **k): pytest.fail('external observation must not be reached')
    monkeypatch.setattr(ui, 'spug_observation', forbidden); monkeypatch.setattr(ui, 'remote', forbidden)
    with pytest.raises(ValueError, match='MAIN_DEPLOYMENT_ROOT'):
        ui.main()
