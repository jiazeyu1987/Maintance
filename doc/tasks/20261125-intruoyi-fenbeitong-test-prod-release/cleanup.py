"""Close only this release's verified task-owned worktrees."""
import json
import sys
from pathlib import Path

task=Path(__file__).resolve().parent
repo=task.parents[2]
base=Path('C:/SpugHandoff/release')
private=base/'private/intruoyi-fenbeitong-test-prod-20261125'
assert '\nready_for_closeout\n' in (task/'task.md').read_text(encoding='utf-8')
for env in ('test','prod'):
    verification=json.loads((private/(env+'-runtime-verification.json')).read_text(encoding='utf-8'))
    assert verification['status']=='PASS' and verification['releaseTag']=='2026-11-26-01-52-12'
    assert verification['gitCommit']=='eb866bbaf4ea1b1c6db93daa63e77576766c3684'
sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from build_worktree_cleanup import cleanup_build_worktree
entries=[
    ('failed-build','C:/Users/D01021/Documents/ChatGPT/IntRuoyi',base/'build/2026-11-25-23-53-05',base/'build','e1ccafbc6638e64f544e609f9072096f529e45b2',{}),
    ('source-fix','C:/Users/D01021/Documents/ChatGPT/IntRuoyi',base/'registration-config-release-fix-20261126',base,'6a099294a0b045f59b4f3896e06c20f1486a35e3',dict(integration_branch='codex/registration-config-release-fix-20261126',merged_into='int_main')),
    ('tenant-fix','C:/Users/D01021/Documents/ChatGPT/IntRuoyi',base/'fenbeitong-ticket-tenant-20261126',base,'eb866bbaf4ea1b1c6db93daa63e77576766c3684',dict(integration_branch='codex/fenbeitong-ticket-tenant-20261126',merged_into='int_main')),
    ('maintenance',str(repo),base/'intruoyi-fenbeitong-release-20261125',base,'ea06ce8983d2330f9fab478551209582c11582fe',{}),
]
for name,owner,worktree,parent,commit,options in entries:
    proof=task/(name+'-cleanup-proof.json')
    def save(value):
        proof.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    prior=json.loads(proof.read_text(encoding='utf-8')) if proof.exists() else None
    result=cleanup_build_worktree(owner,str(worktree),str(parent),commit,prior_proof=prior,before_remove=save,**options)
    save(result)
    print(name,json.dumps(result),flush=True)
