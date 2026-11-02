"""Reviewable code-only overlay; retain the running executor's installed features."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

repo=Path(__file__).resolve().parents[3]
source=repo/'ops/spug/release-center'
baseline_commit='6fac28ef4f87d120adb573a51274a0c97040cf5a'
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center')
private=Path('C:/SpugHandoff/release/private/backend-jar-patch-20261102')
candidate=private/'candidate-source/ops/spug/release-center'
names=['artifact_files.py','frontend_patch_agent.py','frontend_patch_baseline.py','frontend_patch_build.py',
       'intruoyi_executor.py','intruoyi_runtime.py','intruoyi_runtime_agent.py','post_release_cleanup.py',
       'runtime_resource_cleanup.py','ui/app.js','ui/frontend-patch.html','backend_patch.py','backend_patch_agent.py',
       'backend_patch_build.py','backend_patch_contract.py','ui/backend-patch.html','ui/backend-patch.js',
       'frontend_patch.py','ui/frontend-patch.js']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

rows=[]
for name in names:
    path=source/name
    result=path.read_text('utf-8')
    # Frontend baseline support is required to bind a frontend patch to the
    # actual backend JAR. The installed versions have no private customizations.
    if (live/name).exists() and name not in ('frontend_patch.py','frontend_patch_agent.py','frontend_patch_build.py','ui/frontend-patch.js'):
        baseline=subprocess.run(['git','-C',str(repo),'show',baseline_commit+':ops/spug/release-center/'+name],capture_output=True)
        if baseline.returncode==0:
            with tempfile.TemporaryDirectory() as tmp:
                paths=[Path(tmp)/part for part in ('live','base','ours')]
                for target,text in zip(paths,[(live/name).read_text('utf-8'),baseline.stdout.decode('utf-8'),result]):
                    target.write_text(text,encoding='utf-8',newline='\n')
                merge=subprocess.run(['git','merge-file','-p',*map(str,paths)],capture_output=True)
                if merge.returncode not in (0,1):raise RuntimeError('Cannot merge '+name)
                result=merge.stdout.decode('utf-8')
                def resolve(match):
                    installed,incoming=match.group(1),match.group(2)
                    # These separate existing Git features have not yet been
                    # installed here. Do not silently enable unrelated routes,
                    # UI polling or reads while adding the backend patch flow.
                    if name in ('intruoyi_executor.py','intruoyi_runtime_agent.py','ui/app.js'):
                        assert not installed.strip(),name
                        return installed
                    if name=='intruoyi_runtime.py':
                        assert 'source = ' in installed
                        return '\n'.join(line for line in incoming.split('\n') if 'database_versions' not in line and '_database=' not in line)
                    raise RuntimeError('Unreviewed merge conflict: '+name)
                result=re.sub(r'^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n',resolve,result,flags=re.M|re.S)
    assert '<<<<<<<' not in result,name
    target=candidate/name;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(result,encoding='utf-8',newline='\n')
    rows.append(dict(name=name,beforeSha256=sha(live/name),afterSha256=sha(target)))
(private/'code-update-plan.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
# This full candidate permits import and test checks against the actual live
# dependencies. Only the explicit plan above is ever installed.
full=private/'test-source'
full.mkdir(exist_ok=True)
for path in live.rglob('*'):
    if path.is_file() and '__pycache__' not in path.parts:
        target=full/path.relative_to(live);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
for row in rows:
    target=full/row['name'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(candidate/row['name'],target)
for path in source.glob('test_*.py'):shutil.copyfile(path,full/path.name)
for path in source.glob('test_ui_*.cjs'):shutil.copyfile(path,full/path.name)
print(json.dumps(dict(status='prepared',codeFiles=len(rows),conflictsResolved=True,privateConfigCopied=False)))
