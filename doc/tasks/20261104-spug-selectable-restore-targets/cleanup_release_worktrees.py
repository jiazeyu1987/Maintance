"""Remove only the two verified, committed-input release checkouts owned here."""
import json
import subprocess
from pathlib import Path

TASK = Path(__file__).resolve().parent
MAIN = Path('C:/Users/D01021/Documents/ChatGPT/Maintance')
EXPECTED = 'e1389aa621bc92bc2f2e02ebdbc249d3c3086808'
WORKTREE_ROOT = Path('C:/Users/D01021/.codex/worktrees').resolve()
OWNED = {
    'spug-restore-install-20261104': 'f36ff55a6588cb11822dd7611699a2ad76c7207b',
    'spug-restore-install-20261104-v2': '45b4e3e4267183306dcc087e0c52659b6df5d463',
}


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True).stdout.decode('utf-8').strip()


assert git(MAIN, 'rev-parse', 'HEAD') == EXPECTED, 'MAIN_HEAD_CHANGED'
assert not git(MAIN, 'diff', '--cached', '--name-only'), 'MAIN_INDEX_NOT_EMPTY'
receipt = json.loads((TASK / 'implementation-integration.json').read_text(encoding='utf-8'))
receipt['verification'] = 'PASS'
receipt['mergedResultTests'] = {
    'pythonContracts': {'passed': 137, 'windowsPosixSkips': 7},
    'posixEvidence': 'storage-execution-log.md: same committed storage implementation, Linux 98 passed, zero skipped',
    'spugContracts': {'passed': 45},
    'javascriptContracts': {'passed': 42},
}
(TASK / 'implementation-integration.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

paths = [WORKTREE_ROOT / name / 'Maintance' for name in OWNED]
for path in paths:
    assert path.resolve().is_relative_to(WORKTREE_ROOT)
    assert path.resolve() == path, 'CHECKOUT_PATH_REDIRECTED'
    assert git(path, 'rev-parse', 'HEAD') == OWNED[path.parent.name]
    assert not git(path, 'status', '--porcelain'), 'RELEASE_CHECKOUT_DIRTY'
    git(MAIN, 'merge-base', '--is-ancestor', OWNED[path.parent.name], EXPECTED)

# Never print process command lines, which can contain unrelated credentials.
ps = r"""
$ErrorActionPreference='Stop'
$paths=@('C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104/Maintance','C:/Users/D01021/.codex/worktrees/spug-restore-install-20261104-v2/Maintance')
$rows=foreach($path in $paths){
 $matches=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.Name -notmatch '^(powershell|pwsh)\.exe$' -and $_.CommandLine -and $_.CommandLine.Replace('\','/').Contains($path)})
 @{path=$path;referencingProcesses=$matches.Count}
}
ConvertTo-Json -InputObject @($rows) -Compress
"""
observed = json.loads(subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps],
                                    capture_output=True, check=True).stdout)
assert len(observed) == 2 and all(row['referencingProcesses'] == 0 for row in observed)

log = TASK / 'execution-log.md'
with log.open('a', encoding='utf-8', newline='\n') as stream:
    stream.write('\n## 合并验证与临时发布目录收尾\n'
                 '- REGRESSION: int_main=e1389aa，Python 合同 137 PASS；Windows 的 7 项 POSIX 检查已由相同已提交实现的 Linux 98 PASS/0 skip 覆盖；Spug 45 PASS、JS 42 PASS。\n'
                 '- GREEN: experience-preflight -> PASS（仅本任务两个临时发布 checkout 清理）：目标路径精确位于 Codex worktrees 根目录，HEAD 分别 f36ff55/45b4e3e，无未提交改动、无新提交，均为已验证 int_main 的祖先；无引用这些路径的业务/构建进程，稳定控制通道不使用这些目录。使用 git worktree remove，不使用 force，不处理其它任务目录、进程或 NAS；本任务开发 worktree 为正式服准入后续保留。\n')

results = []
for path in paths:
    git(MAIN, 'worktree', 'remove', str(path))
    registered = git(MAIN, 'worktree', 'list', '--porcelain').replace('\\', '/')
    assert str(path).replace('\\', '/') not in registered
    assert not path.exists(), 'RELEASE_PHYSICAL_PATH_REMAINS'
    # Remove the now empty task-owned wrapper only, never recursively.
    if path.parent.exists() and not any(path.parent.iterdir()):
        path.parent.rmdir()
    results.append({'path': path.as_posix(), 'targetCommit': OWNED[path.parent.name],
                    'newCommits': False, 'ancestorOfVerifiedMain': True,
                    'gitRegistrationRemoved': True, 'physicalCheckoutRemoved': True})

(TASK / 'release-worktree-cleanup.json').write_text(
    json.dumps({'status': 'PASS', 'worktrees': results, 'developmentWorktreeRetained': True}, indent=2) + '\n',
    encoding='utf-8')
with log.open('a', encoding='utf-8', newline='\n') as stream:
    stream.write('- GREEN: release-worktree-cleanup -> PASS；两个临时发布 checkout 的 Git 注册与物理路径均已移除，无新提交需合回。详见 release-worktree-cleanup.json。未清理开发 worktree 或任何并发任务资源。\n')
print(json.dumps({'status': 'PASS', 'removedReleaseWorktrees': len(results)}))
