"""Remove only this task's clean, merged worktrees with durable ownership proofs."""
import json
from pathlib import Path
import sys

TASK=Path(__file__).resolve().parent
REPO=TASK.parents[2]
sys.path.insert(0,str(REPO/'ops/spug/release-center'))
from build_worktree_cleanup import cleanup_build_worktree

commits=json.loads((TASK/'implementation-commits.json').read_text(encoding='utf-8'))
for key,repo,worktree in [
    ('source','C:/Users/D01021/Documents/ChatGPT/IntRuoyi','C:/SpugHandoff/release/fenbeitong-runtime-url-20261125'),
    ('maintenance',str(REPO),'C:/SpugHandoff/release/fenbeitong-runtime-url-maint-20261125')]:
    proof=TASK/(key+'-cleanup-proof.json')
    def save(value):
        proof.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    prior=json.loads(proof.read_text(encoding='utf-8')) if proof.exists() else None
    result=cleanup_build_worktree(repo,worktree,'C:/SpugHandoff/release',commits[key]['commit'],
        integration_branch='codex/fenbeitong-runtime-url-20261125',merged_into='int_main',
        prior_proof=prior,before_remove=save)
    save(result)
    print(key,json.dumps(result),flush=True)
