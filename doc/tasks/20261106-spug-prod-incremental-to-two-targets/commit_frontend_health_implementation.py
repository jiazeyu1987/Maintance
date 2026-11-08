"""Commit only the final verified frontend and inherited-quiescence implementation."""
import hashlib,json,subprocess,sys
from common import TASK,now,write
from commit_allocator_implementation import git

ROOT=TASK.parents[2]
FILES=['ops/recovery/recovery_main_health.py','ops/recovery/recovery_minimal_runtime.py',
 'ops/recovery/recovery_retained_retry.py','scripts/tests/test_main_readiness.py',
 'scripts/tests/test_retained_replacement_retry.py','docs/release-agent-checklist.md','docs/experience-index.md']
if __name__=='__main__':
 output=TASK/'frontend-health-implementation-commit.json';assert not output.exists()
 before=git('rev-parse','HEAD');assert before=='7c5f0573e7e1ed7a54e42dbb614cb6e1f0a0534b'
 assert not git('diff','--cached','--name-only')
 for name in ('frontend-health-red-1.json','inherited-quiescence-red-1.json','frontend-health-green-2.json',
              'inherited-quiescence-green-1.json','frontend-health-regression-5.json'):
  report=json.loads((TASK/name).read_text(encoding='utf8'));assert report['expectedResultObserved'] and report['containerRemoved'] and report['inputFilesUnchanged']
 for name,sha in report['testedInputSha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'TESTED_INPUT_CHANGED'
 for suffix in ('58','59'):
  actual=json.loads((TASK/('frontend-readiness-candidate-'+suffix+'.json')).read_text(encoding='utf8'))
  assert actual['status']=='PASS' and actual['serverWrites'] is False and actual['sourceSha256']==report['testedInputSha256']['ops/recovery/recovery_main_health.py']
 actual=json.loads((TASK/'inherited-quiescence-candidate-58.json').read_text(encoding='utf8'))
 assert actual['status']=='PASS' and actual['serverWrites'] is False and actual['sourceSha256']==report['testedInputSha256']['ops/recovery/recovery_retained_retry.py']
 subprocess.run([sys.executable,'-X','utf8',str(TASK/'verify_task_records.py')],check=True)
 inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
 subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
 subprocess.run(['git','add','--',*FILES],cwd=ROOT,check=True)
 assert set(git('diff','--cached','--name-only').splitlines())==set(FILES)
 subprocess.run(['git','commit','-m','任务: 绑定原前端健康端点并保留续办停写状态'],cwd=ROOT,check=True)
 after=git('rev-parse','HEAD');assert git('rev-parse',after+'^')==before
 assert set(git('diff-tree','--no-commit-id','--name-only','-r',after).splitlines())==set(FILES)
 result=dict(status='PASS',observedAt=now(),previousCommit=before,implementationCommit=after,files=FILES,
  testedInputSha256=inputs,taskAcceptanceComplete=False)
 write(output,result);print(json.dumps(result))
