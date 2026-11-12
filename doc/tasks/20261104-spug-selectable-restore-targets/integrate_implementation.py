"""Fast-forward verified owned implementation only; never stage unrelated main edits."""
import json,subprocess
from pathlib import Path
TASK=Path(__file__).resolve().parent
ROOT=TASK.parents[2]
MAIN=Path('C:/Users/D01021/Documents/ChatGPT/Maintance')
def git(root,*args):
 p=subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True);return p.stdout.decode('utf-8').strip()
target=git(ROOT,'rev-parse','HEAD');base=git(MAIN,'rev-parse','HEAD')
assert git(MAIN,'branch','--show-current')=='int_main'
assert not git(MAIN,'diff','--cached','--name-only'),'MAIN_INDEX_NOT_EMPTY'
git(ROOT,'merge-base','--is-ancestor',base,target)
paths=set(git(ROOT,'diff','--name-only',base,target).splitlines())
status=git(MAIN,'status','--porcelain','-z')
dirty=[s[3:] for s in status.split('\x00') if s]
overlap=[p for p in paths for d in dirty if p==d or d.rstrip('/')+'/'==p[:len(d.rstrip('/'))+1]]
assert not overlap,'MAIN_OWN_IMPLEMENTATION_OVERLAP'
assert all(p.startswith(('backend/src/main/resources/recovery_control_','ops/backup_engine/','ops/recovery/','ops/spug/','scripts/tests/')) for p in paths)
result=git(MAIN,'merge','--ff-only',target)
assert git(MAIN,'rev-parse','HEAD')==target
receipt={'before':base,'after':target,'mergedFiles':sorted(paths),'unrelatedDirtyPathsPreserved':len(dirty),'newMergeCommit':False,'verification':'PENDING'}
(TASK/'implementation-integration.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'before':base,'after':target,'files':len(paths),'unrelatedDirtyPathsPreserved':len(dirty)}))
