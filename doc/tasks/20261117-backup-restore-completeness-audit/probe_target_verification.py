import hashlib
import json
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
result = json.loads((root / 'result.json').read_bytes())
def shape(v):
    if isinstance(v, list):
        return {'count': len(v), 'example': shape(v[0]) if v else None}
    if isinstance(v, dict):
        return {'keys': list(v)[:25], 'count': len(v)}
    return v
out = {'documents': [], 'rootFiles': [p.name for p in root.iterdir()], 'finalFiles': []}
for p in (root / 'final').iterdir():
    if p.is_file():
        out['finalFiles'].append({'name': p.name, 'bytes': p.stat().st_size})
for key in ['consistencyPin', 'databaseResultPins', 'objectResultPins', 'derivedPin', 'applicationStartPin']:
    pins = result['data'][key]
    if not isinstance(pins, list):
        pins = [pins]
    for pin in pins:
        raw = Path(pin['path']).read_bytes()
        assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
        doc = json.loads(raw)
        out['documents'].append({'field': key, 'pinVerified': True, 'pin': pin, 'document': doc})
for name in ['configuration.json', 'target-configuration.json']:
    doc = json.loads((root / name).read_bytes())
    out[name] = {k: shape(v) for k, v in doc.items()}
for folder in ['database-000', 'database-001', 'objects']:
    out[folder + 'Files'] = [{'name': p.name, 'bytes': p.stat().st_size} for p in (root / folder).iterdir() if p.is_file()]
print(json.dumps(out))
