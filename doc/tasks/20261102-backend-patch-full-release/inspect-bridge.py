"""Measure local executor and container connectivity without exposing credentials."""
import json,subprocess,time,urllib.request
from pathlib import Path
c=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8'))
headers={'X-Release-Key':c['bridgeKey']}
for route in ('state','commits'):
    start=time.monotonic()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18112/'+route,headers=headers),timeout=25) as response:
        raw=response.read();value=json.loads(raw)
    print(json.dumps(dict(surface='windows',route=route,httpStatus=response.status,bytes=len(raw),seconds=round(time.monotonic()-start,2),
                         targetAvailable=any(r.get('commit')=='da3851751451ea75ce82f4ecb9e0364000505909' for r in value) if route=='commits' else None)))
code='''import json,sys,time,urllib.request
headers=json.load(sys.stdin)
start=time.monotonic()
with urllib.request.urlopen(urllib.request.Request('http://host.docker.internal:18112/state',headers=headers),timeout=25) as response:
 raw=response.read()
print(json.dumps(dict(surface='spug-container',httpStatus=response.status,bytes=len(raw),seconds=round(time.monotonic()-start,2))))
'''
r=subprocess.run(['docker','exec','-i','intruoyi-spug-handoff-20261030-spug-1','python3','-c',code],input=json.dumps(headers).encode('ascii'),capture_output=True,timeout=40)
assert r.returncode==0,'Container bridge inspection failed; diagnostic withheld'
print(r.stdout.decode('ascii'))
