"""Prepare exact record commits; only explicit --execute permits Git writes."""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from common import PRIVATE
from verify_task_records import DOCS, NODE, secrets

# This resolves from the executing copy, including a later copy in int_main.
TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
TASK_BRANCH = 'codex/spug-selectable-restore-targets-20261104'
TEXT_SUFFIXES = {'.py', '.cjs', '.md', '.json', '.log', '.ps1', '.txt', '.tap'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def pin(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_exclusive(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def full_sha(value):
    if not re.fullmatch('[a-f0-9]{40}', value):
        raise argparse.ArgumentTypeError('EXPLICIT_FULL_COMMIT_REQUIRED')
    return value


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=('acceptance', 'final'))
    parser.add_argument('--expected-head', required=True, type=full_sha)
    parser.add_argument('--selection', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--finalization', type=Path)
    parser.add_argument('--execute', action='store_true')
    return parser


def validate_phase(mode, text):
    match = re.search(r'(?m)^## Current Status[ \t]*\r?\n(?:[ \t]*\r?\n)*([^\r\n]+)', text)
    require(match is not None, 'TASK_CURRENT_STATUS_REQUIRED')
    actual = match[1].strip()
    expected = {'acceptance': 'ready_for_closeout', 'final': 'completed'}[mode]
    require(actual == expected, 'TASK_STATUS_NOT_' + expected.upper())
    return actual


def owned_path(root, task, relative):
    require(isinstance(relative, str) and relative and '\\' not in relative and ':' not in relative, 'INVALID_RECORD_PATH')
    pure = PurePosixPath(relative)
    require(not pure.is_absolute() and pure.as_posix() == relative and all(p not in ('.', '..') for p in pure.parts), 'INVALID_RECORD_PATH')
    prefix = task.relative_to(root).as_posix() + '/'
    require(relative.startswith(prefix) or relative in DOCS, 'UNOWNED_RECORD_PATH')
    require(not any(p.casefold() in ('private', '__pycache__', '.git') or '.private.' in p.casefold() for p in pure.parts), 'PRIVATE_OR_GENERATED_RECORD_PATH')
    path = root / relative
    require(path.is_file(), 'SELECTED_RECORD_MISSING')
    boundary = task.resolve() if relative.startswith(prefix) else root.resolve()
    require(path.resolve().is_relative_to(boundary), 'RECORD_LINK_OUTSIDE_SCOPE')
    require(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
                    for p in (path, *path.parents) if p != root and p.is_relative_to(root)), 'RECORD_LINK_NOT_ALLOWED')
    require(path.suffix in TEXT_SUFFIXES | {'.png'} or path.name == '.gitattributes', 'RECORD_TYPE_NOT_ALLOWED')
    return path


def task_input(task, path):
    path = Path(path).resolve()
    require(path.is_relative_to(task.resolve()) and path.is_file(), 'INPUT_MUST_BE_TASK_FILE')
    return path


def load_selection(root, task, selection_path, mode, expected_head):
    data = read_json(task_input(task, selection_path))
    require(data.get('schemaVersion') == 'TaskRecordSelection/v1', 'SELECTION_SCHEMA_INVALID')
    require(data.get('mode') == mode and data.get('expectedHead') == expected_head, 'SELECTION_HEAD_OR_MODE_CHANGED')
    require(isinstance(data.get('files'), list), 'SELECTION_FILES_REQUIRED')
    entries, seen = [], set()
    for row in data['files']:
        require(isinstance(row, dict), 'SELECTION_ENTRY_INVALID')
        path = owned_path(root, task, row.get('path'))
        require(row['path'].casefold() not in seen, 'DUPLICATE_RECORD_PATH')
        seen.add(row['path'].casefold())
        require(type(row.get('bytes')) is int and row['bytes'] >= 0 and isinstance(row.get('sha256'), str)
                and re.fullmatch('[a-f0-9]{64}', row['sha256']), 'SELECTION_PIN_INVALID')
        require(pin(path) == {key: row[key] for key in ('bytes', 'sha256')}, 'SELECTED_FILE_PIN_CHANGED')
        if path.suffix == '.png':
            require(row.get('binaryCredentialsReviewed') is True, 'BINARY_CREDENTIAL_REVIEW_REQUIRED')
        entries.append(row)
    require((task.relative_to(root).as_posix() + '/task.md').casefold() in seen, 'TASK_STATUS_DOCUMENT_NOT_SELECTED')
    return entries


def scan_selected_text(path, known):
    raw = path.read_bytes()
    require(len(raw) < 50 * 1024 * 1024, 'UNEXPECTED_LARGE_RECORD')
    if path.suffix == '.png':
        require(raw.startswith(b'\x89PNG\r\n\x1a\n'), 'SELECTED_PNG_INVALID')
        return
    content = raw.decode('utf-8')
    require(not content.startswith('\ufeff') and '\ufffd' not in content, 'RECORD_ENCODING_INVALID')
    require(not any(secret in content for secret in known), 'PRIVATE_VALUE_IN_SELECTED_RECORD')
    require(not re.search(r'(?m)^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$', content), 'PRIVATE_KEY_IN_SELECTED_RECORD')
    if path.suffix == '.json':
        json.loads(content)
    elif path.suffix == '.py':
        tree = ast.parse(content)
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
                if any(isinstance(target, ast.Name) and target.id == 'SCRIPT' for target in statement.targets):
                    script = statement.value.value
                    if not script.lstrip().startswith('$'):
                        compile(script, str(path) + '::<SCRIPT>', 'exec')
    elif path.suffix == '.cjs':
        checked = subprocess.run([NODE, '--check', str(path)], capture_output=True)
        require(checked.returncode == 0, 'SELECTED_JAVASCRIPT_INVALID')
    elif path.suffix == '.ps1':
        command = "$ErrorActionPreference='Stop';$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile('" + str(path).replace("'", "''") + "',[ref]$tokens,[ref]$errors);if($errors.Count){exit 1}"
        checked = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command', command], capture_output=True)
        require(checked.returncode == 0, 'SELECTED_POWERSHELL_INVALID')


def known_private_values():
    known = set()
    paths = [p for p in PRIVATE.glob('*.json') if p.stat().st_size < 32 * 1024 * 1024]
    paths += [Path('C:/SpugHandoff/release/private') / name for name in ('spug-login.private.json', 'loginCredentials.json')]
    for path in paths:
        secrets(json.loads(path.read_text(encoding='utf-8-sig')), known)
    require(known, 'PRIVATE_VALUE_SCAN_BASELINE_MISSING')
    return known


def proof_file(task, value, expected_name=None, require_pass=True):
    require(isinstance(value, dict) and isinstance(value.get('file'), str), 'PROOF_PIN_REQUIRED')
    name = value['file']
    require('/' not in name and '\\' not in name and name.endswith('.json'), 'PROOF_PATH_INVALID')
    if expected_name is not None:
        require(name == expected_name, 'PROOF_FILE_MISMATCH')
    path = task_input(task, task / name)
    require(pin(path) == {key: value.get(key) for key in ('bytes', 'sha256')}, 'PROOF_PIN_CHANGED')
    data = read_json(path)
    if require_pass:
        require(data.get('status') == 'PASS', 'PROOF_NOT_PASS')
    return data


def validate_finalization(root, task, path, expected_head, registrations, final_rows=None, state_reader=None):
    require(path is not None, 'FINALIZATION_EVIDENCE_REQUIRED')
    evidence = read_json(task_input(task, path))
    require(evidence.get('schemaVersion') == 'TaskRecordsFinalization/v2' and evidence.get('status') == 'PASS', 'FINALIZATION_SCHEMA_OR_STATUS_INVALID')
    require(evidence.get('mainHead') == expected_head, 'FINALIZATION_HEAD_CHANGED')
    require(isinstance(evidence.get('taskHead'), str) and re.fullmatch('[a-f0-9]{40}', evidence['taskHead']), 'FINALIZATION_TASK_HEAD_INVALID')
    merged = proof_file(task, evidence.get('mergeVerificationPin'))
    require(merged.get('mainHead') == expected_head and merged.get('taskHead') == evidence['taskHead']
            and merged.get('mergeVerified') is True and merged.get('targetedRegressionPassed') is True
            and merged.get('parallelChangesPreserved') is True, 'MERGE_REGRESSION_EVIDENCE_INCOMPLETE')
    closed = proof_file(task, evidence.get('closeoutPin'), 'closeout-verification.json')
    require(closed.get('ownedBuildPhysicalAndGitRegistrationAbsent') is True
            and closed.get('stableControlsVerified') is True
            and closed.get('currentControlGenerationsIndependentlyVerified') is True, 'CLOSEOUT_EVIDENCE_INCOMPLETE')
    cleanup = proof_file(task, evidence.get('cleanupPin'), 'owned-build-cleanup.json')
    stable = proof_file(task, evidence.get('stableControlsPin'), 'stable-controls-closeout.json')
    require(stable.get('currentInstallationEvidenceVerified') is True and stable.get('catalogueCurrentRuntimeVerified') is True, 'STABLE_CONTROLS_EVIDENCE_INCOMPLETE')
    require(cleanup.get('deleted') is True and isinstance(cleanup.get('builds'), list) and cleanup['builds'], 'BUILD_CLEANUP_EVIDENCE_INCOMPLETE')
    manifest = read_json(task / 'task-owned-builds.json')
    require(pin(task / 'task-owned-builds.json') == {key: cleanup.get('ownedBuildManifestPin', {}).get(key) for key in ('bytes', 'sha256')}, 'BUILD_MANIFEST_PIN_CHANGED')
    entries = manifest['builds']
    require(manifest.get('schemaVersion') == 'TaskOwnedBuilds/v1' and manifest.get('taskId') == task.name, 'BUILD_MANIFEST_IDENTITY_CHANGED')
    require(len({v['generation'] for v in entries}) == len(entries), 'DUPLICATE_BUILD_GENERATION')
    require(closed.get('ownedBuildCount') == len(entries), 'BUILD_CLEANUP_COUNT_CHANGED')
    require(len(entries) == len(cleanup['builds']) and {v['generation'] for v in entries} == {v['generation'] for v in cleanup['builds']}, 'BUILD_CLEANUP_SCOPE_CHANGED')
    registration_text = registrations.replace('\\', '/').casefold()
    for build in entries:
        done = next(v for v in cleanup['builds'] if v['generation'] == build['generation'])
        require(done.get('status') == 'PASS' and done.get('deleted') is True and done.get('newCommits') is False
                and done.get('mergeRequired') is False and done.get('physicalPathAbsent') is True
                and done.get('gitRegistrationAbsent') is True and done.get('worktree') == build['worktree']
                and done.get('targetCommit') == build['targetCommit'] and done.get('buildReportPin') == build['reportPin']
                and done.get('retainedPackageSha256') == build['packageSha256'], 'BUILD_CLEANUP_EVIDENCE_INCOMPLETE')
        owned = Path(build['worktree']).resolve()
        require(not owned.exists() and owned.as_posix().casefold() not in registration_text, 'BUILD_WORKTREE_STILL_PRESENT')
    snapshot = read_json(task / 'integration-readonly-scope.json')
    development = Path(snapshot['task']['path']).resolve()
    require(development == Path(evidence.get('taskWorktree', '')).resolve() and development != root.resolve(), 'DEVELOPMENT_WORKTREE_IDENTITY_CHANGED')
    require(evidence.get('taskWorktreeDisposition') == 'retained_with_preexisting_assets', 'EXPLICIT_CHECKOUT_RETENTION_REQUIRED')
    require(development.is_dir(), 'RETAINED_CHECKOUT_MISSING')
    registered = {Path(line[len('worktree '):]).resolve() for line in registrations.splitlines() if line.startswith('worktree ')}
    require(development in registered, 'RETAINED_CHECKOUT_NOT_REGISTERED')
    retained = proof_file(task, evidence.get('retainedAssetsPin'), 'integration-pending-scope.json', require_pass=False)
    assets = retained.get('otherTaskPending')
    require(isinstance(assets, list) and len(assets) == 42 and len({v['path'].casefold() for v in assets}) == 42, 'RETAINED_ASSET_SCOPE_CHANGED')
    for asset in assets:
        name = asset['path']
        pure = PurePosixPath(name)
        require(name.startswith('doc/tasks/20261104-spug-selectable-restore-targets/') and pure.as_posix() == name
                and '\\' not in name and ':' not in name and '..' not in pure.parts, 'RETAINED_ASSET_PATH_INVALID')
        actual = development/name
        require(actual.is_file(), 'RETAINED_ASSET_MISSING')
        require(not actual.is_symlink() and actual.resolve().is_relative_to(development), 'RETAINED_ASSET_LINK_CHANGED')
        require(pin(actual) == dict(bytes=asset['taskBytes'], sha256=asset['taskSha256']), 'RETAINED_ASSET_PIN_CHANGED')
    observe = state_reader or read_retained_checkout_state
    state = observe(development, root, task, expected_head, final_rows or [])
    require(state['head'] == evidence.get('taskWorktreeHead'), 'RETAINED_CHECKOUT_HEAD_CHANGED')
    require(state['mergedIntoMain'] is True, 'RETAINED_CHECKOUT_HEAD_NOT_MERGED')
    require(not state['pendingOwnedPaths'], 'RETAINED_CHECKOUT_PENDING_TASK_CHANGES')
    return evidence


def read_retained_checkout_state(development, root, task, main_head, final_rows):
    head = git_text(development, 'rev-parse', 'HEAD')
    merged = subprocess.run(['git', 'merge-base', '--is-ancestor', head, main_head], cwd=root,
                            capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    require(merged.returncode in (0, 1), 'RETAINED_CHECKOUT_HISTORY_QUERY_FAILED')
    prefix = task.relative_to(root).as_posix() + '/'
    raw = git_bytes(development, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', prefix, *DOCS)
    pieces, names, index = raw.decode('utf-8').split('\0'), set(), 0
    while index < len(pieces):
        entry = pieces[index]
        index += 1
        if not entry:
            continue
        names.add(entry[3:])
        if 'R' in entry[:2] or 'C' in entry[:2]:
            names.add(pieces[index])
            index += 1
    selected = {row['path']: row for row in final_rows}
    pending = []
    for name in sorted(names):
        require(name.startswith(prefix) or name in DOCS, 'RETAINED_CHECKOUT_TASK_RENAME_OUTSIDE_SCOPE')
        path = development/name
        if path.is_file() and name in selected:
            expected = {key: selected[name][key] for key in ('bytes', 'sha256')}
            if pin(path) == expected and pin(root/name) == expected:
                continue
        target = subprocess.run(['git', 'rev-parse', '--verify', main_head + ':' + name], cwd=root,
                                capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        if target.returncode == 0 and path.is_file():
            # Apply the repository's existing clean filters without writing an
            # object, so ordinary CRLF conversion is not mistaken for new work.
            source_blob = git_text(root, 'hash-object', '--path=' + name, '--', str(path))
            if source_blob == target.stdout.decode('ascii').strip():
                continue
        elif target.returncode != 0 and not path.exists():
            continue
        pending.append(name)
    return dict(head=head, mergedIntoMain=merged.returncode == 0, pendingOwnedPaths=pending)


def git_bytes(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))


def git_text(root, *args):
    return git_bytes(root, *args).decode('utf-8').strip()


def changed_paths(root):
    return {value for args in (('diff', '--name-only', '-z'), ('ls-files', '--others', '--exclude-standard', '-z'))
            for value in git_bytes(root, *args).decode('utf-8').split('\0') if value}


def unrelated_files(root, selected, ignored):
    # These files are outside this task's commit. Preserve identities without
    # reading unrelated (possibly very large or private) contents. Actual merge
    # byte preservation is proved independently by mergeVerificationPin.
    observed = {}
    for name in sorted(changed_paths(root) - selected - ignored):
        path = root/name
        try:
            state = path.lstat()
        except FileNotFoundError:
            observed[name] = {'absent': True}
        else:
            observed[name] = dict(size=state.st_size, mode=state.st_mode, device=state.st_dev,
                                  inode=state.st_ino, mtimeNs=state.st_mtime_ns, ctimeNs=state.st_ctime_ns)
    return observed


def check_git_state(root, mode, expected_head):
    require(git_text(root, 'branch', '--show-current') == (TASK_BRANCH if mode == 'acceptance' else 'int_main'), 'RECORDS_BRANCH_MISMATCH')
    require(git_text(root, 'rev-parse', 'HEAD') == expected_head, 'HEAD_CHANGED_REVIEW_OWNED_SCOPE')
    require(not git_bytes(root, 'diff', '--cached', '--name-only', '-z'), 'EXISTING_STAGED_FILES')


def check_selected_diff(root, names, runner=subprocess.run):
    for start in range(0, len(names), 30):
        checked = runner(['git', 'diff', '--check', '--', *names[start:start+30]], cwd=root,
                         capture_output=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        require(checked.returncode == 0, 'SELECTED_DIFF_CHECK_FAILED')


def acceptance_evidence(task):
    import closeout_contracts as contracts
    chain = contracts.automatic_chain(task)
    contracts.current_installations(task)
    stable = read_json(task/'stable-controls-closeout.json')
    require(stable.get('status') == 'PASS' and stable.get('automaticOperationIds') == chain['operationIds']
            and stable.get('currentInstallationEvidenceVerified') is True
            and stable.get('catalogueCurrentRuntimeVerified') is True, 'REAL_ACCEPTANCE_NOT_VERIFIED')
    return dict(automaticOperationIds=chain['operationIds'], automaticSelectionPin=contracts.file_pin(task, 'automatic-acceptance-selection.json'),
                currentInstallationPin=contracts.file_pin(task, 'automatic-current-installations.json'),
                stableControlsPin=contracts.file_pin(task, 'stable-controls-closeout.json'))


def main(argv=None):
    args = argument_parser().parse_args(argv)
    receipt = args.receipt.resolve()
    require(receipt.is_relative_to(TASK.resolve()) and receipt.suffix == '.json', 'RECEIPT_MUST_BE_TASK_JSON')
    result_path = receipt.with_name(receipt.stem + '-commit.json')
    require(not receipt.exists() and not result_path.exists(), 'RECEIPT_ALREADY_EXISTS')
    check_git_state(ROOT, args.mode, args.expected_head)
    index_path = Path(git_text(ROOT, 'rev-parse', '--git-path', 'index'))
    if not index_path.is_absolute():
        index_path = ROOT/index_path
    require(not index_path.with_name('index.lock').exists(), 'GIT_INDEX_LOCK_PRESENT')
    initial_index = pin(index_path)
    rows = load_selection(ROOT, TASK, args.selection, args.mode, args.expected_head)
    selected = {r['path'] for r in rows}
    require(args.selection.resolve().relative_to(ROOT).as_posix() not in selected, 'SELECTION_SELF_REFERENCE_NOT_ALLOWED')
    excluded = {receipt.relative_to(ROOT).as_posix(), result_path.relative_to(ROOT).as_posix()}
    require(not selected & excluded, 'RECEIPT_SELF_REFERENCE_NOT_ALLOWED')
    names = sorted(selected & changed_paths(ROOT))
    require(names, 'NO_SELECTED_RECORD_CHANGES')
    status = validate_phase(args.mode, (TASK/'task.md').read_text(encoding='utf-8'))
    require(args.mode == 'final' or args.finalization is None, 'FINALIZATION_NOT_USED_FOR_ACCEPTANCE')
    finalization = None
    if args.mode == 'final':
        finalization = validate_finalization(ROOT, TASK, args.finalization, args.expected_head,
                                            git_text(ROOT, 'worktree', 'list', '--porcelain'), final_rows=rows)
        ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', finalization['taskHead'], args.expected_head], cwd=ROOT, capture_output=True)
        require(ancestor.returncode == 0, 'TASK_COMMIT_NOT_IN_MAIN_HISTORY')
    actual_acceptance = acceptance_evidence(TASK)
    before = unrelated_files(ROOT, selected, excluded)
    known = known_private_values()
    for row in rows:
        scan_selected_text(ROOT/row['path'], known)
    check_selected_diff(ROOT, names)
    load_selection(ROOT, TASK, args.selection, args.mode, args.expected_head)
    check_git_state(ROOT, args.mode, args.expected_head)
    require(pin(index_path) == initial_index, 'INDEX_CHANGED_DURING_PREPARATION')
    require(unrelated_files(ROOT, selected, excluded) == before, 'UNSELECTED_FILES_CHANGED')
    report = dict(schemaVersion='TaskRecordPreparation/v1', status='PREPARED', mode=args.mode,
                  expectedHead=args.expected_head, taskStatus=status, selectedFiles=rows, changedFiles=names,
                  observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  selectionPin=pin(args.selection), privateValuesFound=0, knownPrivateValuesChecked=len(known),
                  actualAcceptance=actual_acceptance, finalizationPin=pin(args.finalization) if finalization else None,
                  unselectedProtection='Git changed-path set and filesystem identity; no unrelated content scan',
                  gitWritesAuthorized=args.execute, gitWritesPerformed=False)
    write_exclusive(receipt, report)
    if not args.execute:
        print(json.dumps(dict(status='PREPARED', mode=args.mode, selectedFiles=len(rows), changedFiles=len(names), gitWritesPerformed=False)))
        return
    load_selection(ROOT, TASK, args.selection, args.mode, args.expected_head)
    check_git_state(ROOT, args.mode, args.expected_head)
    require(unrelated_files(ROOT, selected, excluded) == before, 'UNSELECTED_FILES_CHANGED')
    for start in range(0, len(names), 30):
        subprocess.run(['git', 'add', '--', *names[start:start+30]], cwd=ROOT, check=True, capture_output=True)
    staged = {v for v in git_bytes(ROOT, 'diff', '--cached', '--name-only', '-z').decode('utf-8').split('\0') if v}
    require(staged == set(names), 'STAGING_SCOPE_CHANGED_REVIEW_INDEX_NO_AUTOMATIC_RESET')
    staged_check = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=ROOT, capture_output=True)
    require(staged_check.returncode == 0, 'STAGED_DIFF_CHECK_FAILED_REVIEW_INDEX')
    for name in names:
        if name.startswith(TASK.relative_to(ROOT).as_posix() + '/'):
            attr = git_bytes(ROOT, 'check-attr', '-z', 'text', '--', name).split(b'\0')
            require(attr[2] == b'unset', 'RECORD_BYTES_CONVERSION_ENABLED')
            require(git_text(ROOT, 'hash-object', '--no-filters', '--', name) == git_text(ROOT, 'rev-parse', ':'+name), 'STAGED_RECORD_BYTES_CHANGED')
    require(git_text(ROOT, 'rev-parse', 'HEAD') == args.expected_head, 'HEAD_CHANGED_BEFORE_COMMIT')
    load_selection(ROOT, TASK, args.selection, args.mode, args.expected_head)
    require(unrelated_files(ROOT, selected, excluded) == before, 'UNSELECTED_FILES_CHANGED')
    message = '任务: 记录自动增量真实验收待收尾' if args.mode == 'acceptance' else '任务: 完成自动增量融合与收尾记录'
    committed = subprocess.run(['git', 'commit', '-m', message], cwd=ROOT, capture_output=True)
    require(committed.returncode == 0, 'RECORDS_COMMIT_FAILED_REVIEW_INDEX_NO_RETRY')
    commit = git_text(ROOT, 'rev-parse', 'HEAD')
    committed_paths = {v for v in git_bytes(ROOT, 'diff-tree', '--no-commit-id', '--name-only', '-r', '-z', commit).decode('utf-8').split('\0') if v}
    require(committed_paths == set(names), 'COMMIT_SCOPE_CHANGED')
    require(not git_bytes(ROOT, 'diff', '--cached', '--name-only', '-z'), 'POST_COMMIT_INDEX_NOT_EMPTY')
    require(unrelated_files(ROOT, selected, excluded) == before, 'UNSELECTED_FILES_CHANGED')
    write_exclusive(result_path, dict(schemaVersion='TaskRecordCommit/v1', status='PASS', mode=args.mode,
                    previousHead=args.expected_head, commit=commit, committedFiles=names,
                    preparationPin=pin(receipt), unrelatedFileIdentitiesPreserved=len(before), taskStatus=status))
    print(json.dumps(dict(status='PASS', mode=args.mode, commit=commit, committedFiles=len(names))))


if __name__ == '__main__':
    main()
