"""Prepare isolated task inputs using the reviewed existing installer and UI probe."""
import hashlib
import json
import subprocess
from pathlib import Path
import psutil

base = Path('C:/SpugHandoff/release')
out = base/'private/intruoyi-fenbeitong-test-prod-20261125'
checkout = base/'intruoyi-fenbeitong-release-20261125'
source_repo = Path('C:/Users/D01021/Documents/ChatGPT/IntRuoyi')
git = lambda *args: subprocess.check_output(['git', '-C', str(source_repo), *args]).decode().strip()
target = git('rev-parse','HEAD')
subprocess.run(['git','-C',str(source_repo),'merge-base','--is-ancestor','158f4fed30dd4995b0a2501c07216ce07972d421',target],check=True)
craw = (base/'executor.private.json').read_bytes()
c = json.loads(craw)
processes = []
for connection in psutil.net_connections(kind='tcp'):
    if connection.status == psutil.CONN_LISTEN and connection.laddr.port == c['port']:
        p = psutil.Process(connection.pid)
        processes.append(dict(port=c['port'],pid=p.pid,created=p.create_time(),exe=p.exe(),cwd=p.cwd()))
assert len(processes)==1
assert Path(c['repo']).resolve()==source_repo.resolve()
summary = dict(configSha256=hashlib.sha256(craw).hexdigest(),processes=processes)
(out/'preflight-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
template = (base/'private/database-contract-gate-20261124/install.py').read_text(encoding='utf-8')
start = template.index('checkout=')
end = template.index('config_path=',start)
template = template[:start]+'checkout=Path('+repr(str(checkout))+')\nprivate=Path('+repr(str(out))+')\ncommit="ea06ce8983d2330f9fab478551209582c11582fe"\n'+template[end:]
start=template.index('files=[')
end=template.index('\n',start)
template=template[:start]+"files=['ops/spug/release-center/intruoyi_runtime_agent.py']"+template[end:]
start=template.index('assert all((source/name).read_bytes().replace')
end=template.index('\ndef state():',start)
template=template[:start]+"assert all((source/name).read_bytes().replace(b'\\r\\n',b'\\n')==git('show','87faa54^:'+name).replace(b'\\r\\n',b'\\n') for name in files)\n"+template[end:]
compile(template,'install.py','exec')
(out/'install.py').write_text(template,encoding='utf-8')
for env,host in [('test','172.30.30.58'),('prod','172.30.30.57')]:
    folder=out/env
    folder.mkdir(exist_ok=True)
    probe=(base/'private/test-prod-20261125/test/menu-page-check.cjs').read_text(encoding='utf-8')
    probe=probe.replace("const base='http://172.30.30.58:8081'", "const base='http://"+host+":8081'")
    probe=probe.replace("environment:'test'", "environment:'"+env+"'")
    (folder/'menu-page-check.cjs').write_text(probe,encoding='utf-8')
(out/'build.json').write_text(json.dumps(dict(requestId='intruoyi-fenbeitong-20261125-build-1',commit=target)),encoding='utf-8')
public=dict(sourceCommit=target,maintenanceCommit='ea06ce8983d2330f9fab478551209582c11582fe',maintenanceWorktree=str(checkout),newCommits=False,mainDirtyExcluded=True,installerSha256=hashlib.sha256(template.encode()).hexdigest(),baselineScript='menu-page-check.cjs',targets=['test','prod'])
(Path(__file__).parent/'release-inputs.json').write_text(json.dumps(public,indent=2),encoding='utf-8')
print(json.dumps(public))
