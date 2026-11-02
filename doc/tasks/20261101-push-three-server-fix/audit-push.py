"""Audit outgoing Git objects; never emit private configuration or secret values."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

task=Path(__file__).parent
inspection=json.loads((task/'repository-inspection.json').read_text('utf-8'))
private=Path('C:/SpugHandoff/release')
config=json.loads((private/'executor.private.json').read_text('utf-8-sig'))
secrets=set()
def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if re.search('password|token|secret',key,re.I) and not re.search('(file|path|name)$',key,re.I) and isinstance(item,str) and len(item)>=6:
                secrets.add(item.encode('utf-8'))
            collect(item)
    elif isinstance(value,list):
        for item in value: collect(item)
for item in (config,json.loads(Path(config['loginVerification']['credentialsFile']).read_text('utf-8-sig')),
             json.loads((private/'private/spug-login.private.json').read_text('utf-8-sig'))):
    collect(item)

def git(repo,*args,data=None,env=None):
    completed=subprocess.run(['git','-C',str(repo),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    if completed.returncode: raise RuntimeError('Git audit command failed: '+args[0])
    return completed.stdout

result={}
for name,info in inspection.items():
    repo=info['repository']
    assert git(repo,'rev-parse',info['branch']).decode().strip()==info['commit']
    advertised=sorted(set(info['remoteHeads'].values()))
    local_env=dict(os.environ,GIT_NO_LAZY_FETCH='1')
    check=git(repo,'cat-file','--batch-check=%(objectname) %(objecttype)',data=('\n'.join(advertised)+'\n').encode(),env=local_env).decode().splitlines()
    exclusions=[line.split()[0] for line in check if line.endswith(' commit')]
    assert exclusions,'No known remote ancestry; refuse unbounded history scan'
    listing=git(repo,'rev-list','--objects','--missing=print',info['commit'],'--not',*exclusions).decode().splitlines()
    missing=[line[1:] for line in listing if line.startswith('?')]
    assert not missing,'Missing outgoing objects must be restored before pushing'
    objects={line.split(' ',1)[0]:line.split(' ',1)[1] if ' ' in line else '' for line in listing}
    sizes=git(repo,'cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)',data=('\n'.join(objects)+'\n').encode()).decode().splitlines()
    blobs=[];violations=[]
    for line in sizes:
        oid,kind,size=line.split();size=int(size)
        if kind!='blob': continue
        path=objects[oid]
        blobs.append(dict(oid=oid,path=path,bytes=size))
        if size>100_000_000:
            violations.append(dict(path=path,reason='GitHub blob exceeds 100 MB'))
            continue
        content=git(repo,'cat-file','blob',oid)
        if any(secret in content for secret in secrets):
            violations.append(dict(path=path,reason='Exact private credential value found'))
        if re.search(rb'(?m)^-----BEGIN (?:RSA |OPENSSH |EC |ENCRYPTED )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{20,}',content):
            violations.append(dict(path=path,reason='Private key body found'))
        if re.search(r'(^|/)(executor\.private\.json|sshIdentityFile|sshKnownHostsFile|spug-login\.private\.json|state\.sqlite3)$',path,re.I):
            violations.append(dict(path=path,reason='Private runtime material found'))
    commits=git(repo,'rev-list','--count',info['commit'],'--not',*exclusions).decode().strip()
    result[name]=dict(status='PASS' if not violations else 'BLOCKER',commit=info['commit'],branch=info['branch'],
        remote=info['remote'],knownAdvertisedHeads=len(exclusions),outgoingCommitCount=int(commits),
        outgoingBlobCount=len(blobs),outgoingBytes=sum(b['bytes'] for b in blobs),
        largestBlobs=sorted(blobs,key=lambda b:b['bytes'],reverse=True)[:5],violations=violations)
    print(json.dumps(dict(repository=name,**result[name]),ensure_ascii=False),flush=True)
(task/'push-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(info['status']=='PASS' for info in result.values()),'Push blocked by content audit'
