"""Real Git history/worktree tests; no server, Docker or installed runtime calls."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_automatic_ui_preflight import verify_deployment_inputs, verify_submission_identity


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()


def put(root, name, data='original\n'):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding='utf-8')


def commit(root, message):
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Task Test', '-c', 'user.email=task@example.invalid',
        'commit', '-m', message)
    return git(root, 'rev-parse', 'HEAD')


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'core.autocrlf', 'false')
    mapping = {'backend/src/main/resources/recovery_control_incremental_plan.py':
               'control/recovery_control_incremental_plan.py'}
    put(tmp_path, 'ops/backup_engine/files.json', json.dumps(mapping))
    for name in [*mapping, 'ops/backup_engine/standard_fixes.py',
                 'ops/recovery/recovery_backup_epoch.py', 'ops/spug/smallapp_entry.py',
                 'ops/spug/release-center/package_catalog.py']:
        put(tmp_path, name)
    installed = commit(tmp_path, 'installed source')
    return tmp_path, installed, ['smallapp_entry.py']


def test_unrelated_real_commit_is_allowed(repository):
    root, installed, files = repository
    put(root, 'ops/spug/release-center/package_catalog.py', 'catalogue correction\n')
    head = commit(root, 'independent catalogue correction')
    result = verify_deployment_inputs(root, installed, files)
    assert head != installed
    assert result['headCommit'] == head and result['installedCommit'] == installed
    assert result['installedCommitIsAncestor'] and result['deploymentInputsUnchanged']


@pytest.mark.parametrize('name', [
    'ops/backup_engine/standard_fixes.py',
    'ops/recovery/recovery_backup_epoch.py',
    'backend/src/main/resources/recovery_control_incremental_plan.py',
    'ops/spug/smallapp_entry.py',
])
@pytest.mark.parametrize('state', ['committed', 'unstaged', 'staged'])
def test_changed_deployment_input_is_rejected(repository, name, state):
    root, installed, files = repository
    put(root, name, 'changed deployed source\n')
    if state == 'committed':
        commit(root, 'changed deployment input')
    elif state == 'staged':
        git(root, 'add', name)
        # A reverted working file must not hide a changed staged input.
        put(root, name)
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        verify_deployment_inputs(root, installed, files)


def test_new_untracked_deployment_input_is_rejected(repository):
    root, installed, files = repository
    put(root, 'ops/backup_engine/new_transform.py')
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        verify_deployment_inputs(root, installed, files)


def test_unrelated_working_changes_are_allowed(repository):
    root, installed, files = repository
    put(root, 'ops/spug/release-center/new_catalogue.py')
    put(root, 'doc/tasks/notes.md')
    assert verify_deployment_inputs(root, installed, files)['deploymentInputsUnchanged']


def test_installed_commit_must_exist(repository):
    root, installed, files = repository
    with pytest.raises(RuntimeError, match='INSTALLED_COMMIT_NOT_FOUND'):
        verify_deployment_inputs(root, '1' * 40, files)


def test_installed_commit_must_be_head_ancestor(repository):
    root, installed, files = repository
    put(root, 'ops/spug/release-center/other.py')
    sibling = commit(root, 'separate history')
    git(root, 'checkout', '--detach', installed)
    with pytest.raises(RuntimeError, match='INSTALLED_COMMIT_NOT_HEAD_ANCESTOR'):
        verify_deployment_inputs(root, sibling, files)


def test_committed_input_cannot_be_hidden_by_local_revert(repository):
    root, installed, files = repository
    name = 'ops/recovery/recovery_backup_epoch.py'
    put(root, name, 'changed\n')
    commit(root, 'changed code')
    put(root, name)
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        verify_deployment_inputs(root, installed, files)


def test_spug_paths_cannot_escape_component(repository):
    root, installed, files = repository
    with pytest.raises(RuntimeError, match='DEPLOYMENT_INPUT_PATH_INVALID'):
        verify_deployment_inputs(root, installed, ['../release-center/file.py'])


def test_real_full_submission_identity_contract():
    value = json.loads(Path(__file__).with_name('automatic-full-ui-submission.json').read_text(encoding='utf-8'))
    assert verify_submission_identity(value, 'FULL', value['implementationCommit']) == value['request']['operationId']
    value['intent']['operationId'] = 'smallapp-' + '0' * 32
    with pytest.raises(AssertionError):
        verify_submission_identity(value, 'FULL', value['implementationCommit'])


def test_new_source_and_unchanged_spug_have_independent_git_scopes(repository):
    from prepare_automatic_ui_preflight import verify_stage_deployment_inputs
    root, spug_commit, files = repository
    put(root, 'ops/backup_engine/standard_fixes.py', 'actual source-only upgrade\n')
    source_commit = commit(root, 'source-only upgrade')
    result = verify_stage_deployment_inputs(root, source_commit, spug_commit, files)
    assert result['source']['installedCommit'] == source_commit
    assert result['spug']['installedCommit'] == spug_commit
    assert result['source']['headCommit'] == result['spug']['headCommit'] == source_commit
    assert 'ops/backup_engine' not in result['spug']['deploymentInputScopes']
    assert 'ops/spug/smallapp_entry.py' not in result['source']['deploymentInputScopes']


@pytest.mark.parametrize('name', ['ops/backup_engine/standard_fixes.py', 'ops/spug/smallapp_entry.py'])
@pytest.mark.parametrize('state', ['committed', 'staged', 'unstaged'])
def test_split_generation_still_rejects_each_component_drift(repository, name, state):
    from prepare_automatic_ui_preflight import verify_stage_deployment_inputs
    root, spug_commit, files = repository
    put(root, 'ops/backup_engine/standard_fixes.py', 'actual source-only upgrade\n')
    source_commit = commit(root, 'source-only upgrade')
    put(root, name, 'later uninstalled change\n')
    if state == 'committed':commit(root, 'later uninstalled change')
    if state == 'staged':git(root, 'add', name)
    with pytest.raises(RuntimeError, match='AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED'):
        verify_stage_deployment_inputs(root, source_commit, spug_commit, files)
