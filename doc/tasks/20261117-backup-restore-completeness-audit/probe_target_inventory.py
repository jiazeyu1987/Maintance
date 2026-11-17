import hashlib
import json
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config = json.loads((root / 'target-configuration.json').read_bytes())
result = json.loads((root / 'result.json').read_bytes())
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
out = {'serverWrites': False, 'minioDataMount': config['dataPolicy']['minioDataMount'], 'materials': []}
for pin in result['data']['orderedChainPins']:
    load(pin)
    material = json.loads(Path(pin['path']).with_name('recovery-material.json').read_bytes())
    inventory = load(material['objects']['fileInventoryPin'])
    point = load(material['objects']['capturePointPin'])
    out['materials'].append({'inventoryExample': list(inventory.items())[:4], 'pointInventoryExample': list(point['fileInventory'].items())[:4], 'physicalFileCount': len(material['objects']['filePayloadPins']), 'physicalBytes': sum(p['bytes'] for p in material['objects']['filePayloadPins'].values()), 'derived': material.get('derived'), 'configurationBindings': [{k: v for k, v in b.items() if k in ['role', 'kind', 'source']} for b in material.get('configurationBindings', [])]})
for name in ['physical-comparison.json', 'physical-step-000-readback.json', 'physical-step-001-readback.json', 'bucket-permissions.json']:
    out[name] = json.loads((root / 'objects' / name).read_bytes())
out['redisReadback'] = json.loads((root / 'final' / 'redis-dump-independent-readback.json').read_bytes())
print(json.dumps(out))
