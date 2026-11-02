"""Sync five reviewed static assets to the discovered existing nginx alias."""
from pathlib import Path,PurePosixPath
import hashlib,json,re,subprocess

container='intruoyi-spug-handoff-20261030-spug-1'
private=Path('C:/SpugHandoff/release/private/backend-jar-patch-20261102')
source=private/'candidate-source/ops/spug/release-center/ui'
names=['app.js','frontend-patch.html','frontend-patch.js','backend-patch.html','backend-patch.js']

def run(args):return subprocess.check_output(args)
def execute(code,*args):return run(['docker','exec',container,'python3','-c',code,*args])

nginx=execute("from pathlib import Path;print(Path('/etc/nginx/nginx.conf').read_text())").decode()
locations=re.findall(r'include\s+(/var/lib/intruoyi-spug/releases/[^;]+/locations.conf);',nginx)
assert len(locations)==1,'Unique registered release UI include required'
location=execute('from pathlib import Path;import sys;print(Path(sys.argv[1]).read_text())',locations[0]).decode()
aliases=re.findall(r'alias\s+(/var/lib/intruoyi-spug/releases/[^;]+/ui/);',location)
assert len(aliases)==1,'Unique existing release UI alias required'
target=PurePosixPath(aliases[0])
assert target.parent.parent==PurePosixPath('/var/lib/intruoyi-spug/releases')
check='''from pathlib import Path
import sys,json,hashlib
p=Path(sys.argv[1]);assert p.is_dir() and p.resolve()==p
result=[]
for name in sys.argv[2:]:
 f=p/name;assert not f.is_symlink()
 result.append(dict(name=name,beforeSha256=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None))
print(json.dumps(result))'''
rows=json.loads(execute(check,str(target),*names))
backup=private/'original-served-ui';backup.mkdir(exist_ok=False)
for row in rows:
    if row['beforeSha256']:
        run(['docker','cp',container+':'+str(target/row['name']),str(backup/row['name'])])
        assert hashlib.sha256((backup/row['name']).read_bytes()).hexdigest()==row['beforeSha256']
for row in rows:
    path=source/row['name'];row['afterSha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    run(['docker','cp',str(path),container+':'+str(target/row['name'])])
actual=json.loads(execute(check,str(target),*names))
assert all(a['beforeSha256']==b['afterSha256'] for a,b in zip(actual,rows))
(private/'ui-code-update-plan.json').write_text(json.dumps(dict(container=container,alias=str(target),files=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(status='installed',staticFiles=len(rows),nginxConfigChanged=False,containerRestarted=False)))
