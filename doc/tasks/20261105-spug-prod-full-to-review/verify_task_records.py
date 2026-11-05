"""Check task records without printing private credential values."""
import ast
import json
from pathlib import Path
import re
import subprocess
from preflight import PRIVATE, TASK

NODE='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'

def secrets(value, output, in_headers=False):
    if isinstance(value,dict):
        for key,item in value.items():
            sensitive=(in_headers or re.search(r'password|token|secret|authorization',key,re.I))
            reference=re.search(r'pin|ref|path|sha256|digest|schema|plan',key,re.I)
            if sensitive and not reference and isinstance(item,str) and len(item)>=8:
                if not (item.startswith(('/', 'C:', 'D:', 'E:')) or re.fullmatch(r'[a-f0-9]{64}',item)):
                    output.add(item)
            secrets(item,output,key.lower()=='headers')
    elif isinstance(value,list):
        for item in value:secrets(item,output)
    elif isinstance(value,str):
        match=re.fullmatch(r'[A-Z0-9_]*(?:PASSWORD|TOKEN|SECRET)[A-Z0-9_]*=(.+)',value)
        if match and len(match[1])>=8:output.add(match[1])

if __name__=='__main__':
    known=set()
    private_files=[p for p in PRIVATE.glob('*.json') if p.stat().st_size<8*1024*1024]
    private_files += [Path('C:/SpugHandoff/release/private')/name for name in ('spug-login.private.json','loginCredentials.json')]
    for path in private_files:secrets(json.loads(path.read_text(encoding='utf-8-sig')),known)
    findings=[];counts={};total=0
    files=sorted(p for p in TASK.rglob('*') if p.is_file() and (p.suffix in {'.py','.cjs','.md','.json','.log','.png'} or p.name=='.gitattributes'))
    files.append(TASK.parents[2]/'docs/request-command-log.md')
    for path in files:
        kind=path.suffix or path.name
        counts[kind]=counts.get(kind,0)+1;total+=path.stat().st_size
        if path.suffix=='.png':continue
        content=path.read_text(encoding='utf-8')
        assert '\ufffd' not in content and not content.startswith('\ufeff'),str(path)+' ENCODING_INVALID'
        if path.suffix=='.py':ast.parse(content)
        if path.suffix=='.json':json.loads(content)
        if path.suffix=='.cjs':subprocess.run([NODE,'--check',str(path)],check=True,capture_output=True)
        if any(secret in content for secret in known):findings.append(dict(file=str(path.relative_to(TASK.parents[2])),kind='known-private-value'))
        if re.search(r'(?m)^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$',content):findings.append(dict(file=str(path),kind='private-key'))
    assert not findings,json.dumps(dict(findings=findings))
    subprocess.run(['git','diff','--check'],cwd=TASK.parents[2],check=True,capture_output=True)
    report=dict(status='PASS',fileCounts=counts,totalBytes=total,knownPrivateValuesChecked=len(known),utf8AndSyntaxVerified=True,privateValuesFound=0,diffCheck=True)
    (TASK/'records-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
