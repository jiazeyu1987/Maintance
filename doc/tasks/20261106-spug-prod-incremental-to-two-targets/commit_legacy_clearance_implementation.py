"""Commit only the verified closed legacy history compatibility change."""
import hashlib,json,subprocess,sys
from common import TASK,now,write
from commit_allocator_implementation import git

ROOT=TASK.parents[2]
FILES=['ops/recovery/recovery_retained_retry.py','scripts/tests/test_legacy_main_clearance.py',
       'docs/release-agent-checklist.md','docs/experience-index.md']
if __name__=='__main__':
    output=TASK/'legacy-clearance-implementation-commit.json';assert not output.exists()
    before=git('rev-parse','HEAD');assert before=='701b4422426d517f00aad23e71732b54c8b19724'
    assert not git('diff','--cached','--name-only')
    for name in ('legacy-clearance-red-1.json','legacy-clearance-green-1.json','legacy-clearance-regression-1.json'):
        report=json.loads((TASK/name).read_text(encoding='utf8'))
        assert report['expectedResultObserved'] and report['containerRemoved'] and report['inputFilesUnchanged']
    for name,sha in report['testedInputSha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'TESTED_INPUT_CHANGED'
    actual=json.loads((TASK/'legacy-candidate-native-selections-58.json').read_text(encoding='utf8'))
    assert actual['status']=='PASS' and actual['serverWrites'] is False
    assert actual['candidateSha256']==report['testedInputSha256']['ops/recovery/recovery_retained_retry.py']
    subprocess.run([sys.executable,'-X','utf8',str(TASK/'verify_task_records.py')],check=True)
    inputs={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES}
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    subprocess.run(['git','add','--',*FILES],cwd=ROOT,check=True)
    assert set(git('diff','--cached','--name-only').splitlines())==set(FILES)
    subprocess.run(['git','commit','-m','任务: 兼容已闭合的旧MAIN续恢复记录'],cwd=ROOT,check=True)
    after=git('rev-parse','HEAD');assert git('rev-parse',after+'^')==before
    assert set(git('diff-tree','--no-commit-id','--name-only','-r',after).splitlines())==set(FILES)
    result=dict(status='PASS',observedAt=now(),previousCommit=before,implementationCommit=after,
                files=FILES,testedInputSha256=inputs,taskAcceptanceComplete=False)
    write(output,result);print(json.dumps(result))
