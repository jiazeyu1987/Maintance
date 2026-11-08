"""Commit only the exact implementation after its full regression passes."""
import hashlib,json,subprocess,sys
from common import TASK,now,write
from commit_allocator_implementation import git
ROOT=TASK.parents[2]
FILES=['ops/backup_engine/standard_fixes.py','scripts/tests/test_backup_variants.py',
 'scripts/tests/test_retained_replacement_retry.py','docs/experience-index.md','docs/release-agent-checklist.md']
if __name__=='__main__':
 output=TASK/'packaged-frontend-implementation-commit.json';assert not output.exists()
 before=git('rev-parse','HEAD');assert before=='9c93449e99ae0790c8678a570d78a98b61d96d87'
 assert not git('diff','--cached','--name-only')
 for name in ('packaged-frontend-red-3.json','packaged-frontend-green-1.json','frontend-health-regression-7.json'):
  report=json.loads((TASK/name).read_text(encoding='utf8'))
  assert report['expectedResultObserved'] and report['containerRemoved'] and report['inputFilesUnchanged']
 for name,sha in report['testedInputSha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'TESTED_INPUT_CHANGED'
 subprocess.run([sys.executable,'-X','utf8',str(TASK/'verify_task_records.py')],check=True)
 inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
 subprocess.run(['git','add','--',*FILES],cwd=ROOT,check=True)
 assert set(git('diff','--cached','--name-only').splitlines())==set(FILES)
 subprocess.run(['git','commit','-m','任务: 补齐标准恢复包前端配置传递'],cwd=ROOT,check=True)
 after=git('rev-parse','HEAD');assert git('rev-parse',after+'^')==before
 assert set(git('diff-tree','--no-commit-id','--name-only','-r',after).splitlines())==set(FILES)
 result=dict(status='PASS',observedAt=now(),previousCommit=before,implementationCommit=after,files=FILES,
  testedInputSha256=inputs,taskAcceptanceComplete=False)
 write(output,result);print(json.dumps(result))
