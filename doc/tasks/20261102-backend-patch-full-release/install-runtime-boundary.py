"""Exact committed multi-file installation, only while the ordinary executor is idle."""
from pathlib import Path
import hashlib,json,subprocess,sys,urllib.request
repo=Path(__file__).resolve().parents[3]
root=Path('C:/SpugHandoff/release');private=root/'private/backend-patch-full-release-20261102/runtime-boundary'
live=root/'source/ops/spug/release-center';candidate=repo/'ops/spug/release-center'
names=['backend_patch_agent.py','backend_patch_build.py','backend_patch_contract.py','ui/backend-patch.js']
before_ref='443d0b735b3ba4025e7a58b9c8690c96edabad64'
def normalized(value):return value.decode('utf-8').replace('\r\n','\n')
def git_file(ref,name):return subprocess.check_output(['git','-C',str(repo),'show',ref+':ops/spug/release-center/'+name])
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
phase=sys.argv[1]
if phase=='prepare':
    for name in names:
        assert normalized((live/name).read_bytes())==normalized(git_file(before_ref,name)),'Unexpected live code: '+name
        assert normalized((candidate/name).read_bytes())==normalized(git_file('HEAD',name)),'Uncommitted candidate: '+name
    private.mkdir(exist_ok=False)
    (private/'code-update-plan.json').write_text(json.dumps([dict(name=n,beforeSha256=sha(live/n),afterSha256=sha(candidate/n)) for n in names],indent=2),encoding='utf-8')
    print(json.dumps(dict(status='prepared',files=len(names))))
elif phase=='ui':
    script='/var/lib/intruoyi-spug/releases/dbabf7e/ui/backend-patch.js'
    container='intruoyi-spug-handoff-20261030-spug-1'
    old=private/'served-ui-before.js';assert not old.exists()
    subprocess.run(['docker','cp',container+':'+script,str(old)],check=True,capture_output=True)
    assert normalized(old.read_bytes())==normalized(git_file(before_ref,'ui/backend-patch.js')),'Unexpected served UI'
    subprocess.run(['docker','cp',str(candidate/'ui/backend-patch.js'),container+':'+script+'.runtime-update'],check=True,capture_output=True)
    subprocess.run(['docker','exec',container,'mv',script+'.runtime-update',script],check=True,capture_output=True)
    with urllib.request.urlopen('http://127.0.0.1:18081/release-center/backend-patch.js',timeout=20) as response:served=response.read()
    assert normalized(served)==normalized(git_file('HEAD','ui/backend-patch.js'))
    print(json.dumps(dict(status='passed',servedUiSha256=hashlib.sha256(served).hexdigest())))
else:
    original=(repo/'doc/tasks/20261102-spug-backend-jar-patch/apply-runtime-update.py').read_text('utf-8')
    original=original.replace("private=root/'private/backend-jar-patch-20261102'",'private=Path('+repr(private.as_posix())+')')
    original=original.replace("candidate=private/'candidate-source/ops/spug/release-center'",'candidate=Path('+repr(candidate.as_posix())+')')
    exec(compile(original,'reviewed-idle-runtime-installer.py','exec'))
