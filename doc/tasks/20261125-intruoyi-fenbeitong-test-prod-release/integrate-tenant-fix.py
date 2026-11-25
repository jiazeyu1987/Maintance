"""Commit only the validated tenant fix, then integrate without touching user edits."""
import hashlib,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
base=Path('C:/SpugHandoff/release'); out=base/'private/intruoyi-fenbeitong-test-prod-20261125'
work=base/'fenbeitong-ticket-tenant-20261126'; main=Path('C:/Users/D01021/Documents/ChatGPT/IntRuoyi')
java='IntRuoyiBackend/yudao-module-system/src/'
package='cn/iocoder/yudao/module/system/'
files=[java+'main/java/'+package+'controller/admin/auth/AuthController.java',
       java+'main/java/'+package+'service/fenbeitongassistant/FenbeitongAssistantTicketPayload.java',
       java+'test/java/'+package+'controller/admin/auth/AuthControllerTest.java']
env=dict(os.environ); env['PATH']='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python;C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell;'+env['PATH'];env['PYTHONUTF8']='1'
def git(root,*args):
    q=subprocess.run(['git','-c','core.longpaths=true','-C',str(root),*args],env=env,capture_output=True)
    if q.returncode:
        (out/'tenant-integration-error.private.log').write_bytes(q.stdout+q.stderr)
        raise RuntimeError('Git step failed; private diagnostic retained')
    return q.stdout
counts={}
for name in ('AuthControllerTest','FenbeitongAssistantServiceImplTest','InvoiceVoucherPrintAssistantServiceImplTest'):
    found=list((work/'IntRuoyiBackend/yudao-module-system/target/surefire-reports').glob('TEST-*.'+name+'.xml'))
    assert len(found)==1
    x=ET.parse(found[0]).getroot()
    counts[name]={k:int(x.attrib[k]) for k in ('tests','failures','errors','skipped')}
    assert not any(counts[name][k] for k in ('failures','errors','skipped'))
    (out/('tenant-green-'+name+'.private.xml')).write_bytes(found[0].read_bytes())
assert counts['AuthControllerTest']['tests']==44
assert git(main,'rev-parse','HEAD').decode().strip()=='6a099294a0b045f59b4f3896e06c20f1486a35e3'
assert git(work,'branch','--show-current').strip()==b'codex/fenbeitong-ticket-tenant-20261126'
before=git(main,'status','--porcelain','--untracked-files=all')
dirty=git(main,'diff','--binary')
assert not git(work,'diff','--cached','--name-only').strip()
git(work,'add','--',*files);git(work,'diff','--cached','--check')
assert set(git(work,'diff','--cached','--name-only').decode().splitlines())==set(files)
log=git(work,'commit','-m','任务: 修复分贝通票据租户上下文')
(out/'tenant-commit.private.log').write_bytes(log)
commit=git(work,'rev-parse','HEAD').decode().strip()
assert not git(work,'status','--porcelain','--untracked-files=all').strip()
assert git(main,'status','--porcelain','--untracked-files=all')==before
git(main,'merge','--ff-only',commit)
assert git(main,'status','--porcelain','--untracked-files=all')==before and git(main,'diff','--binary')==dirty
assert all(git(main,'show','HEAD:'+f)==git(work,'show','HEAD:'+f) for f in files)
v=dict(status='PASS',commit=commit,files=files,mainMerged=True,unrelatedChangesPreserved=True,worktree=str(work),newCommit=True,tests=counts)
(out/'tenant-integration.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'build-r3.json').write_text(json.dumps(dict(requestId='intruoyi-fenbeitong-20261126-build-3',commit=commit)),encoding='utf-8')
print(json.dumps(v,ensure_ascii=False))
