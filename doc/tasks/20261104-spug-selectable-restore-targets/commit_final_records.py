"""Verify and commit only owning task records, preserving unrelated dirty work."""
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent
MAIN = Path('C:/Users/D01021/Documents/ChatGPT/Maintance')
REL = 'doc/tasks/20261104-spug-selectable-restore-targets/'
EXPECTED = 'e1389aa621bc92bc2f2e02ebdbc249d3c3086808'
REQUEST_LOG = 'docs/request-command-log.md'


def git(*args, input_bytes=None):
    return subprocess.run(['git', '-C', str(MAIN), *args], input=input_bytes,
                          capture_output=True, check=True).stdout


def constant(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError('MISSING_OWN_RECORD_CONSTANT')


def collect_secrets(value, output):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r'password|token|secret|authorization', key, re.I) and isinstance(item, str):
                if len(item) >= 8 and '/' not in item and '\\' not in item and not re.fullmatch(r'[a-f0-9]{64}', item):
                    output.add(item)
            collect_secrets(item, output)
    elif isinstance(value, list):
        for item in value:
            collect_secrets(item, output)


def dirty_paths():
    fields = git('status', '--porcelain', '-z', '--untracked-files=all').decode('utf-8').split('\0')
    result = set()
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if not field:
            continue
        result.add(field[3:])
        if 'R' in field[:2] or 'C' in field[:2]:
            result.add(fields[index])
            index += 1
    return result


def snapshot_unrelated():
    result = {}
    for relative in dirty_paths():
        if relative.startswith(REL) or relative == REQUEST_LOG:
            continue
        path = MAIN / relative
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'ABSENT_OR_DIRECTORY'
    return result


assert git('rev-parse', 'HEAD').decode().strip() == EXPECTED, 'MAIN_HEAD_CHANGED'
assert git('branch', '--show-current').decode().strip() == 'int_main'
assert not git('diff', '--cached', '--name-only'), 'MAIN_INDEX_NOT_EMPTY'
files = sorted(path for path in TASK.iterdir() if path.is_file() and path.suffix in {'.md', '.json', '.py', '.ps1', '.cjs', '.png'})
assert all(path.parent == TASK and (MAIN / REL / path.name).read_bytes() == path.read_bytes() for path in files), 'OWN_MIRROR_DIFFERS'

known_secrets = set()
private_root = Path('C:/Spug/runtime/private/restore-targets-20261104')
private_files = [path for path in private_root.rglob('*.json') if path.stat().st_size < 2000000]
private_files.append(Path('C:/SpugHandoff/release/private/spug-login.private.json'))
for path in private_files:
    collect_secrets(json.loads(path.read_text(encoding='utf-8-sig')), known_secrets)
findings = []
for path in files:
    if path.suffix == '.png':
        continue
    content = path.read_text(encoding='utf-8')
    assert '\ufffd' not in content and not content.startswith('\ufeff'), 'TEXT_ENCODING_INVALID'
    if path.suffix == '.py':
        ast.parse(content)
    if re.search(r'(?m)^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$', content):
        findings.append({'file': path.name, 'kind': 'private-key'})
    if any(secret in content for secret in known_secrets):
        findings.append({'file': path.name, 'kind': 'known-private-value'})
    for match in re.finditer(r'''(?i)(?:password|token|secret)\s*[:=]\s*(['"])([A-Za-z0-9_!@#$%^&*+=-]{8,})\1''', content):
        findings.append({'file': path.name, 'kind': 'literal-credential-candidate'})
assert not findings, json.dumps({'secretScanFindings': findings})

head_log = git('show', 'HEAD:' + REQUEST_LOG).decode('utf-8')
working_log = (MAIN / REQUEST_LOG).read_text(encoding='utf-8')
for entry in (constant(TASK / 'record_local_result.py', 'ENTRY'), constant(TASK / 'finalize_records.py', 'ENTRY')):
    assert entry.strip() in working_log, 'OWN_REQUEST_ENTRY_MISSING'
    if entry.strip() not in head_log:
        head_log += entry

scope = [REL + path.name for path in files] + [REQUEST_LOG]
print(json.dumps({'verification': 'PASS', 'ownTaskFileCount': len(files),
                  'privateCredentialValueCountChecked': len(known_secrets),
                  'unrelatedWorkingLogContentPreserved': True, 'commitRequested': '--commit' in sys.argv}))
if '--commit' not in sys.argv:
    sys.exit(0)

before = snapshot_unrelated()
working_log_bytes = (MAIN / REQUEST_LOG).read_bytes()
git('add', '--', *[path for path in scope if path != REQUEST_LOG])
blob = git('hash-object', '-w', '--stdin', input_bytes=head_log.encode('utf-8')).decode().strip()
git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + REQUEST_LOG)
staged = set(git('diff', '--cached', '--name-only').decode('utf-8').splitlines())
assert staged == set(scope), 'STAGED_SCOPE_CHANGED'
git('diff', '--cached', '--check')
assert snapshot_unrelated() == before, 'UNRELATED_WORK_CHANGED_BEFORE_COMMIT'
assert (MAIN / REQUEST_LOG).read_bytes() == working_log_bytes, 'WORKING_REQUEST_LOG_CHANGED'
git('commit', '-m', '任务: 记录恢复目标安装及正式服准入阻塞')
commit = git('rev-parse', 'HEAD').decode().strip()
assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()) == set(scope)
assert not git('diff', '--cached', '--name-only'), 'INDEX_NOT_EMPTY_AFTER_COMMIT'
assert snapshot_unrelated() == before, 'UNRELATED_WORK_CHANGED_AFTER_COMMIT'
assert (MAIN / REQUEST_LOG).read_bytes() == working_log_bytes
print(json.dumps({'status': 'PASS', 'recordsCommit': commit, 'committedFiles': len(scope),
                  'unrelatedDirtyFilesPreserved': len(before), 'formalTargetStillBlocked': True}))
