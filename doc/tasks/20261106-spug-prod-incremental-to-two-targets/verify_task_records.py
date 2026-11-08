"""Validate owned delivery records and scan known private values without output."""
import ast
import json
from pathlib import Path
import re
import subprocess
from common import TASK, PRIVATE

ROOT=TASK.parents[2]
NODE='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
DOCS=['docs/request-command-log.md','docs/experience-index.md','docs/release-agent-checklist.md','docs/powershell-preflight-lessons.md']
SUFFIXES={'.py','.cjs','.md','.json','.log','.png','.ps1'}

def secrets(value,output,in_headers=False):
    if isinstance(value,dict):
        for key,item in value.items():
            sensitive=in_headers or re.search(r'password|token|secret|authorization|access[_-]?key|api[_-]?key',key,re.I)
            # This schema's authorization is an audit narrative, not an HTTP credential.
            # Headers and credentials collected elsewhere remain fully scanned.
            if key=='authorization' and not in_headers and value.get('schemaVersion') in (
                    'RetainedReplacementRecovery/v1','RetainedReplacementRecovery/v2'):
                sensitive=False
            reference=re.search(r'pin|ref|path|sha256|digest|schema|plan',key,re.I)
            if sensitive and not reference and isinstance(item,str) and len(item)>=6:
                if not(item.startswith(('/','C:','D:','E:')) or re.fullmatch(r'[a-f0-9]{64}',item)):
                    output.add(item)
            secrets(item,output,key.lower()=='headers')
    elif isinstance(value,list):
        for item in value:secrets(item,output)
    elif isinstance(value,str):
        match=re.fullmatch(r'[A-Z0-9_]*(?:PASSWORD|TOKEN|SECRET)[A-Z0-9_]*=(.+)',value)
        if match and len(match[1])>=6:output.add(match[1])

def selected():
    return sorted(p for p in TASK.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and (p.suffix in SUFFIXES or p.name=='.gitattributes'))+[ROOT/n for n in DOCS]

if __name__=='__main__':
    known=set()
    private_files=[p for p in PRIVATE.glob('*.json') if p.stat().st_size<32*1024*1024]
    private_files += [Path('C:/SpugHandoff/release/private')/n for n in ['spug-login.private.json','loginCredentials.json']]
    for path in private_files:secrets(json.loads(path.read_text(encoding='utf-8-sig')),known)
    assert known,'PRIVATE_VALUE_SCAN_BASELINE_MISSING'
    counts={};total=0;findings=[];embedded_python=0
    for path in selected():
        kind=path.suffix or path.name;counts[kind]=counts.get(kind,0)+1;total+=path.stat().st_size
        assert path.stat().st_size<50*1024*1024,'UNEXPECTED_LARGE_RECORD'
        if path.suffix=='.png':continue
        content=path.read_text(encoding='utf-8')
        assert '\ufffd' not in content and not content.startswith('\ufeff'),'RECORD_ENCODING_INVALID '+str(path)
        if path.suffix=='.py':
            tree=ast.parse(content)
            for statement in tree.body:
                if not isinstance(statement,ast.Assign) or not isinstance(statement.value,ast.Constant) or not isinstance(statement.value.value,str):continue
                if not any(isinstance(target,ast.Name) and target.id=='SCRIPT' for target in statement.targets):continue
                script=statement.value.value
                if script.lstrip().startswith('$'):continue
                compile(script,str(path)+'::<SCRIPT>','exec');embedded_python+=1
        if path.suffix=='.json':json.loads(content)
        if path.suffix=='.cjs':subprocess.run([NODE,'--check',str(path)],check=True,capture_output=True)
        if path.suffix=='.ps1':
            command="$ErrorActionPreference='Stop';$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile('"+str(path).replace("'","''")+"',[ref]$tokens,[ref]$errors);if($errors.Count){throw 'POWERSHELL_PARSE_FAILED'}"
            subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-Command',command],check=True,capture_output=True)
        if any(secret in content for secret in known):findings.append(dict(file=str(path.relative_to(ROOT)),kind='known-private-value'))
        if re.search(r'(?m)^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----\s*$',content):findings.append(dict(file=str(path.relative_to(ROOT)),kind='private-key'))
    assert not findings,json.dumps(dict(findings=findings))
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,capture_output=True)
    report=dict(status='PASS',fileCounts=counts,totalBytes=total,knownPrivateValuesChecked=len(known),
                utf8AndSyntaxVerified=True,embeddedPythonScriptsCompiled=embedded_python,privateValuesFound=0,diffCheck=True)
    (TASK/'records-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
