"""Read pinned document shapes for final acceptance; no operation submission."""
import json
from repair_preflight import remote, TASK

SCRIPT = r'''
import hashlib,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def read(pin):
 data=pathlib.Path(pin['path']).read_bytes()
 assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256']
 return json.loads(data)
out=[]
for selector in sorted((root/'registry/points').glob('*.json')):
 point=read(json.loads(selector.read_bytes()));result=read(point['resultPin'])
 row={'reference':point['reference'],'pointKeys':sorted(point),'resultKeys':sorted(result),'state':result.get('state'),'dataKeys':sorted(result.get('data',{})),'pins':{}}
 for key,pin in result.get('data',{}).items():
  if key.endswith('Pin') and isinstance(pin,dict) and set(('path','bytes','sha256')).issubset(pin):
   value=read(pin)
   row['pins'][key]={'schemaVersion':value.get('schemaVersion'),'keys':sorted(value)}
   if isinstance(value.get('payload'),dict):row['pins'][key]['payloadKeys']=sorted(value['payload'])
   if isinstance(value.get('data'),dict):row['pins'][key]['dataKeys']=sorted(value['data'])
   if key=='captureResultPin':row['sourceRestoration']=read(value['data']['sourceRestorationPin'])
 out.append(row)
lines=(root/'engine/common/repository_minimal.py').read_text(encoding='utf-8').splitlines()
worker=(root/'engine/formal/minimal_capture_worker.py').read_text(encoding='utf-8').splitlines()
restoration=['\n'.join(worker[max(0,i-2):i+7]) for i,l in enumerate(worker) if 'minimal-capture-source-restoration/v1' in l]
print(json.dumps({'captureLimits':json.loads((root/'configuration/capture.json').read_bytes())['limits'],'points':out,'installedPublication':'\n'.join(lines[560:604]),'installedRestoration':restoration}))
'''
if __name__ == '__main__':
    result=remote('172.30.30.57',SCRIPT,timeout=25)
    (TASK/'full-evidence-shapes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'installedRestoration':result['installedRestoration']}))
