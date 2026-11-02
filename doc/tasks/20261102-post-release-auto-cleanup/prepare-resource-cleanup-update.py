"""Apply this task's exact Git delta over the running source, preserving other fixes."""
from pathlib import Path
import hashlib
import difflib
import json
import shutil
import subprocess

repo=Path(__file__).resolve().parents[3]
private=Path('C:/SpugHandoff/release/private/post-release-cleanup-20261102/resource-extension')
live=Path('C:/SpugHandoff/release/source')
candidate=private/'candidate-source-v3'
private.mkdir(exist_ok=True)
if candidate.exists():raise SystemExit('Candidate exists; inspect rather than overwrite')
shutil.copytree(live,candidate,ignore=shutil.ignore_patterns('__pycache__'))
relative=Path('ops/spug/release-center')
names=['artifact_files.py','intruoyi_runtime.py','intruoyi_executor.py','post_release_cleanup.py','ui/app.js','ui/frontend-patch.js']
for name in names:
    base=subprocess.run(['git','show','HEAD:'+str(relative/name).replace('\\','/')],
        cwd=repo,check=True,stdout=subprocess.PIPE).stdout.decode('utf-8').splitlines(True)
    updated=(repo/relative/name).read_text('utf-8').splitlines(True)
    path=candidate/relative/name;text=path.read_text('utf-8')
    for kind,a,b,c,d in reversed(difflib.SequenceMatcher(a=base,b=updated,autojunk=False).get_opcodes()):
        if kind=='equal':continue
        old=''.join(base[a:b]);new=''.join(updated[c:d])
        if not old:
            # Anchor insertions to one existing full line without unrelated context.
            start=a-1;old=''.join(base[start:a])
            while text.count(old)!=1 and start>0:
                start-=1;old=''.join(base[start:a])
            new=old+new
        if name=='ui/frontend-patch.js' and old.startswith("  else if(!['frontend-patch-refresh'"):
            old="  else if(action!=='frontend-patch-refresh'){payload.releaseTag=fpSelected;payload.target=target;payload.note=fpDraft(target).trim();if(payload.note.length<5)throw Error('请填写至少5字的真实操作或验收依据');}\n"
            new=old.replace("action!=='frontend-patch-refresh'","!['frontend-patch-refresh','retry-release-cleanup'].includes(action)")
        if text.count(old)!=1:raise SystemExit('Unexpected live source contract: '+name)
        text=text.replace(old,new,1)
    path.write_text(text,'utf-8')
names.append('runtime_resource_cleanup.py')
shutil.copyfile(repo/relative/names[-1],candidate/relative/names[-1])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
plan=[]
for name in names:
    path=candidate/relative/name
    if path.suffix=='.py':compile(path.read_text('utf-8'),str(path),'exec')
    plan.append(dict(name=name,beforeSha256=sha(live/relative/name),afterSha256=sha(path)))
for pattern in ('test_*.py','test_*.cjs'):
    for path in (repo/relative).glob(pattern):shutil.copyfile(path,candidate/relative/path.name)
(private/'code-update-plan.json').write_text(json.dumps(plan,indent=2),'utf-8')
print(json.dumps(dict(candidate=str(candidate/relative),codeFiles=len(plan))))
