"""Audit and remove only this task's superseded, commit-clean build checkout."""
from pathlib import Path
import json,sqlite3,sys
root=Path('C:/SpugHandoff/release');task=Path(__file__).parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from build_worktree_cleanup import cleanup_build_worktree
config=json.loads((root/'executor.private.json').read_text('utf-8'))
with sqlite3.connect('file:C:/SpugHandoff/release/state/state.sqlite3?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
job=next(j for j in state['jobs'] if j['id']=='JOB-6c804e6c7f')
assert job['status']=='failed' and job['action']=='backend-patch-build' and not job.get('effectsStarted')
assert job['releaseTag']=='2026-11-02-21-39-33' and job['payload']['commit']=='e5934b12e46064b01c8b5ad0b4c016229286c223'
target=Path(job['buildWorktree']).absolute()
assert target==Path('C:/SpugHandoff/release/build/2026-11-02-21-39-33')
assert target.parent==Path(config['buildWorktreeRoot']).absolute()
assert json.loads((task/'sealed-full-verification.json').read_text('utf-8'))['status']=='PASS'
output=task/'failed-build-worktree-cleanup.json'
proof=json.loads(output.read_text('utf-8')) if output.exists() else None
def checkpoint(value):
    output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value),flush=True)
try:
    result=cleanup_build_worktree(config['repo'],target,config['buildWorktreeRoot'],job['payload']['commit'],prior_proof=proof,before_remove=checkpoint)
except Exception as error:
    value=json.loads(output.read_text('utf-8')) if output.exists() else {}
    value.update(status='blocked',errorCategory=type(error).__name__)
    checkpoint(value)
    raise
checkpoint(result)
