"""Close only this task's clean merged checkout and labelled Docker resources."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

task = Path(__file__).resolve().parent
repo = task.parents[2]
root = repo.parent / 'Maintance-worktrees'
worktree = root / 'bounded-service-recovery'
commit = '43ee6e7dba8d72429df936fd6779cebc577fdbba'
assert worktree.resolve().parent == root.resolve() and worktree.resolve() != repo.resolve()
command = [sys.executable, '-B', str(repo / 'ops/spug/release-center/integration_worktree_cleanup.py'),
           '--repo', str(repo), '--worktree', str(worktree), '--root', str(root),
           '--commit', commit, '--branch', 'codex/bounded-service-recovery', '--merged-into', 'int_main',
           '--proof', str(task / 'worktree-closeout.json')]
subprocess.run(command, check=True)
assert not worktree.exists()
label = '20261124-bounded-service-recovery'
network = 'maint-recovery-20261124-net'
volume = 'maint-recovery-20261124-volume'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, encoding='utf-8')


net = json.loads(docker('network', 'inspect', network))[0]
vol = json.loads(docker('volume', 'inspect', volume))[0]
assert net['Labels']['task'] == label and vol['Labels']['task'] == label
assert not net.get('Containers'), 'Active test containers; preserve network and volume'
assert not docker('ps', '-aq', '--filter', 'volume=' + volume).strip(), 'Volume still in use'
subprocess.run(['docker', 'network', 'rm', network], check=True)
subprocess.run(['docker', 'volume', 'rm', volume], check=True)
archive = task / 'baseline-recovery.tar'
assert archive.resolve().parent == task.resolve()
expected = '9568fe41c1603cdf3e6f6c2b52748daafa248ed7a819a34dce8a9fe6aba09a47'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
archive.unlink()
result = dict(worktreeRemoved=True, mergedCommit=commit, networkRemoved=network,
              volumeRemoved=volume, archiveRemoved=True, archiveSha256=expected,
              remoteOperations=False, consolesStarted=False)
(task / 'resource-closeout.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
