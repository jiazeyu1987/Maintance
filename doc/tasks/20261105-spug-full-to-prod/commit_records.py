"""Commit only this task's records after actual restoration and final cleanup."""
import hashlib
import json
import subprocess
import sys
from install_prod_control import TASK,PRIVATE
from verify_task_records import ROOT,DOCS,selected

PREFIX=TASK.relative_to(ROOT).as_posix()+'/'
EXPECTED_HEAD='9dce31858c7bc9196b7a0d7ee34d93fec18c9473'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()

def others():
    names=git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names
            if n and n not in DOCS and not n.startswith(PREFIX)}

if __name__=='__main__':
    assert git('branch','--show-current')=='codex/spug-selectable-restore-targets-20261104'
    assert git('rev-parse','HEAD')==EXPECTED_HEAD,'HEAD_CHANGED_REVIEW_OWNED_SCOPE'
    assert not git('diff','--cached','--name-only'),'EXISTING_STAGED_FILES'
    assert '## Current Status\ncompleted\n' in (TASK/'task.md').read_text(encoding='utf-8')
    assert json.loads((TASK/'closeout-verification.json').read_text(encoding='utf-8'))['status']=='PASS'
    subprocess.run([sys.executable,'-X','utf8','-B',str(TASK/'verify_task_records.py')],cwd=ROOT,check=True)
    untouched=others();names=sorted(p.relative_to(ROOT).as_posix() for p in selected())
    for start in range(0,len(names),30):
        subprocess.run(['git','add','-f','--',*names[start:start+30]],cwd=ROOT,check=True)
    assert set(git('diff','--cached','--name-only').splitlines())==set(names),'STAGING_SCOPE_CHANGED'
    checked=subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,capture_output=True)
    if checked.returncode:
        (PRIVATE/'records-staged-check.private.log').write_bytes(checked.stdout+checked.stderr)
        raise SystemExit('STAGED_DIFF_CHECK_FAILED_SEE_PRIVATE_LOG')
    for name in names:
        if name.startswith(PREFIX):
            attributes=subprocess.check_output(['git','check-attr','-z','text','--',name],cwd=ROOT).split(b'\x00')
            assert attributes[2]==b'unset','RECORD_BYTES_CONVERSION_ENABLED'
            assert git('hash-object','--no-filters','--',name)==git('rev-parse',':'+name),'STAGED_RECORD_BYTES_CHANGED'
    assert others()==untouched,'UNRELATED_FILES_CHANGED'
    result=subprocess.run(['git','commit','-m','任务: 完成Spug正式服恢复验收归档'],cwd=ROOT,capture_output=True)
    if result.returncode:
        (PRIVATE/'records-commit.private.log').write_bytes(result.stdout+result.stderr)
        raise SystemExit('RECORDS_COMMIT_FAILED_SEE_PRIVATE_LOG')
    commit=git('rev-parse','HEAD')
    assert set(git('diff-tree','--no-commit-id','--name-only','-r',commit).splitlines())==set(names)
    assert not git('diff','--cached','--name-only') and not git('status','--porcelain','--',PREFIX,*DOCS)
    assert others()==untouched,'UNRELATED_FILES_CHANGED'
    print(json.dumps(dict(status='PASS',commit=commit,committedFiles=len(names),unrelatedFilesPreserved=len(untouched))))
