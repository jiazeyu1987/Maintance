"""Show only redacted fixture context for a blocked exact-value match."""
import json
from pathlib import Path
import re
import subprocess

root=Path('C:/SpugHandoff/release')
c=json.loads((root/'executor.private.json').read_text('utf-8-sig'))
secrets={}
def collect(value,prefix):
    if isinstance(value,dict):
        for k,v in value.items():
            if re.search('password|token|secret',k,re.I) and isinstance(v,str) and len(v)>=6:
                secrets.setdefault(v,[]).append(prefix+'.'+k)
            collect(v,prefix+'.'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value): collect(v,prefix+'.'+str(i))
collect(c,'executor')
collect(json.loads(Path(c['loginVerification']['credentialsFile']).read_text('utf-8-sig')),'app-login')
collect(json.loads((root/'private/spug-login.private.json').read_text('utf-8-sig')),'spug-login')
repo='C:/Users/D01021/Documents/spug-handoff-work-20261030/code/Maintance'
path='ops/spug/release-center/test_intruoyi_rehearsal.py'
content=subprocess.check_output(['git','-C',repo,'show','codex/three-server-schema-20261101:'+path]).decode('utf-8')
lines=content.splitlines()
for i,line in enumerate(lines):
    matches=[s for s in secrets if s in line]
    if not matches: continue
    context='\n'.join(lines[max(0,i-2):i+3])
    for s in sorted(secrets,key=len,reverse=True): context=context.replace(s,'<REDACTED>')
    print(json.dumps(dict(line=i+1,matchingPrivateFields=[k for s in matches for k in secrets[s]],redactedContext=context),ensure_ascii=False))
