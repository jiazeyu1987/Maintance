"""Commit the separately reproduced minimal-entry dependency fix."""
import hashlib
import json
import subprocess
import sys
from common import TASK, now, write
from commit_allocator_implementation import git

ROOT=TASK.parents[2]
FILES=['ops/recovery/recovery_minimal_runtime.py','ops/backup_engine/standard_fixes.py',
       'scripts/tests/test_backup_variants.py','docs/release-agent-checklist.md','docs/experience-index.md']
if __name__=='__main__':
    output=TASK/'allocator-entry-implementation-commit.json';assert not output.exists()
    before=git('rev-parse','HEAD');assert before=='9a65b5a6767cbb64d3f9668aa47bcc57229f0818'
    assert not git('diff','--cached','--name-only')
    for name in ('allocator-entry-red-1.json','allocator-entry-green-1.json','allocator-regression-5.json'):
        report=json.loads((TASK/name).read_text(encoding='utf8'))
        assert report['expectedResultObserved'] and report['containerRemoved'] and report['inputFilesUnchanged']
    for name,sha in report['testedInputSha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'TESTED_INPUT_CHANGED'
    subprocess.run([sys.executable,'-X','utf8',str(TASK/'verify_task_records.py')],check=True)
    inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    subprocess.run(['git','add','--',*FILES],cwd=ROOT,check=True)
    assert set(git('diff','--cached','--name-only').splitlines())==set(FILES)
    subprocess.run(['git','commit','-m','任务: 补齐最小恢复入口的自增模块依赖'],cwd=ROOT,check=True)
    after=git('rev-parse','HEAD');assert git('rev-parse',after+'^')==before
    assert set(git('diff-tree','--no-commit-id','--name-only','-r',after).splitlines())==set(FILES)
    result=dict(status='PASS',observedAt=now(),previousCommit=before,implementationCommit=after,
                files=FILES,testedInputSha256=inputs,taskAcceptanceComplete=False)
    write(output,result);print(json.dumps(result))
