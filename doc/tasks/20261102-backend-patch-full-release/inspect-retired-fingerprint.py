"""Read repeated Docker snapshots; compare semantic mount sets without deletion."""
from pathlib import Path
import json,subprocess,sys
root=Path('C:/SpugHandoff/release');task=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')));profile=runtime.profile('prod')
code=r'''
import hashlib,json,subprocess
identity='071d2f104de8b98251402915e7f869c0d3be03f900e2e1cbcd25e6361cff950d'
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
snapshots=[]
for _ in range(8):
    value=json.loads(subprocess.check_output(['docker','inspect',identity]))[0]
    fields={k:value.get(k) for k in ('Id','Image','Config','HostConfig','Mounts')}
    normalized=dict(fields,Mounts=sorted(fields['Mounts'],key=lambda m:json.dumps(m,sort_keys=True,separators=(',',':'))))
    snapshots.append(dict(fields={k:digest(v) for k,v in fields.items()},raw=digest(fields),canonical=digest(normalized),
        stopped=not any(value['State'].get(k) for k in ('Running','Paused','Restarting'))))
print(json.dumps(dict(samples=len(snapshots),rawIdentities=len({v['raw'] for v in snapshots}),canonicalIdentities=len({v['canonical'] for v in snapshots}),
    differingFields=[k for k in snapshots[0]['fields'] if len({v['fields'][k] for v in snapshots})>1],allStopped=all(v['stopped'] for v in snapshots))))
'''
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=60)
assert result.returncode==0,'Docker identity evidence unavailable'
proof=json.loads(result.stdout);(task/'retired-fingerprint-evidence.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');print(json.dumps(proof))
