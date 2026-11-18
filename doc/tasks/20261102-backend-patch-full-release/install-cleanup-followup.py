"""Install only committed cleanup changes while the ordinary executor is idle."""
from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path(__file__).resolve().parents[3];root=Path('C:/SpugHandoff/release')
private=root/'private/backend-patch-full-release-20261102/runtime-cleanup'
candidate=private/'candidate-source/ops/spug/release-center';live=root/'source/ops/spug/release-center'
names=['artifact_files.py','runtime_resource_cleanup.py']
legacy=len(sys.argv)>2 and sys.argv[2]=='legacy'
before_ref='5f9cf1e' if legacy else 'a93fe3e'
if legacy:
    private=root/'private/backend-patch-full-release-20261102/runtime-cleanup-legacy'
    candidate=private/'candidate-source/ops/spug/release-center'
    names=['runtime_resource_cleanup.py']
def committed(ref,name):
    return subprocess.check_output(['git','-C',str(repo),'show',ref+':ops/spug/release-center/'+name]).decode('utf-8').replace('\r\n','\n')
if sys.argv[1]=='prepare':
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()
    assert head!=subprocess.check_output(['git','-C',str(repo),'rev-parse',before_ref]).decode().strip()
    for name in names:assert (live/name).read_text('utf-8')==committed(before_ref,name),'Unexpected live source: '+name
    candidate.mkdir(parents=True,exist_ok=False)
    rows=[]
    for name in names:
        (candidate/name).write_text(committed(head,name),encoding='utf-8',newline='\n')
        rows.append(dict(name=name,beforeSha256=hashlib.sha256((live/name).read_bytes()).hexdigest(),afterSha256=hashlib.sha256((candidate/name).read_bytes()).hexdigest()))
    (private/'code-update-plan.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (private/'source-commit.json').write_text(json.dumps(dict(commit=head)),encoding='utf-8')
    print(json.dumps(dict(status='prepared',files=len(rows),sourceCommit=head)))
else:
    source=(repo/'doc/tasks/20261102-spug-backend-jar-patch/apply-runtime-update.py').read_text('utf-8')
    source=source.replace("private=root/'private/backend-jar-patch-20261102'",'private=Path('+repr(private.as_posix())+')')
    source=source.replace("candidate=private/'candidate-source/ops/spug/release-center'",'candidate=Path('+repr(candidate.as_posix())+')')
    exec(compile(source,'reviewed-idle-cleanup-installer.py','exec'))
