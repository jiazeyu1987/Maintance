"""Integrate exact task commits while preserving unrelated main workspace edits."""
import json
import os
from pathlib import Path
import subprocess
import sys

TASK=Path(__file__).resolve().parent
commits=json.loads((TASK/'implementation-commits.json').read_text(encoding='utf-8'))
env=dict(os.environ)
env['PATH']=str(Path(sys.executable).parent)+';C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell;'+env['PATH']
env['PYTHONUTF8']='1'
def git(root,*args):
    result=subprocess.run(['git','-C',str(root),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if result.returncode:
        print(result.stdout.decode('utf-8',errors='replace')[-4000:],flush=True)
        raise RuntimeError('Integration command failed')
    return result.stdout

result={}
for key,root in [('source',Path('C:/Users/D01021/Documents/ChatGPT/IntRuoyi')),
                 ('maintenance',Path('C:/Users/D01021/Documents/ChatGPT/Maintance'))]:
    row=commits[key]
    assert git(root,'branch','--show-current').strip()==b'int_main'
    assert not git(root,'diff','--cached','--name-only').strip()
    assert not git(root,'diff','--name-only','--',*row['files']).strip(), 'Overlapping main edits; preserve and stop'
    prior=git(root,'rev-parse','HEAD').decode().strip()
    output=git(root,'merge','--ff-only',row['commit'])
    assert git(root,'rev-parse','HEAD').decode().strip()==row['commit']
    for name in row['files']:
        raw=(root/name).read_bytes().replace(b'\r\n',b'\n')
        assert raw==git(root,'show',row['commit']+':'+name).replace(b'\r\n',b'\n'), name
    result[key]={'before':prior,'after':row['commit'],'verifiedFiles':len(row['files'])}
    print(key,'PASS: fast-forward and main task bytes match tested commit',flush=True)
    (TASK/'integration-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
