import collections
import hashlib
import json
import subprocess
from pathlib import Path

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
def command(args):
    return subprocess.check_output(args, timeout=20).decode('utf-8')
def shape(v):
    if isinstance(v, dict): return {'keys': list(v), 'count': len(v)}
    if isinstance(v, list): return {'count': len(v), 'example': shape(v[0]) if v else None}
    return v
out = {'serverWrites': False, 'operations': []}
for op in ['smallapp-8d9db80d8f1e4531ba9a0234335d0dcb', 'smallapp-bf67a867d3ec4e369ca31657c45e62c6']:
    folder = base / 'repository-operations' / hashlib.sha256(op.encode()).hexdigest()
    result = json.loads((folder / 'result.json').read_bytes())
    material = load(result['data']['recoveryMaterialPin'])
    point = load(material['database']['capturePointPin'])
    data = load(material['database']['expectedDataPin'])
    inventory = load(material['objects']['fileInventoryPin'])
    versions_path = Path(material['objects']['inventoryPin']['path'])
    versions_raw = versions_path.read_bytes()
    assert hashlib.sha256(versions_raw).hexdigest() == material['objects']['inventoryPin']['sha256']
    versions = [json.loads(line) for line in versions_raw.splitlines() if line]
    readback = load(result['data']['readbackPin'])
    original = load(readback['originalRecordsPin'])
    out['operations'].append({
        'operation': op,
        'pointSelected': {'databaseDelta': point['databaseDelta'], 'fileDelta': {k: len(v) if isinstance(v, list) else v for k,v in point['fileDelta'].items()}, 'sourceRestored': point.get('sourceRestored')},
        'schemaObjectCounts': data['schema']['objectCounts'],
        'schemaCatalogCounts': {k: len(v) for k, v in data['schema']['catalog'].items()},
        'schemaHistoricalExclusions': data['schema'].get('excludedHistoricalFields'),
        'inventoryBucketsByPhysicalPath': dict(collections.Counter(k.split('/')[0] for k in point.get('fileInventory', {}))),
        'versionsCount': len(versions), 'versionsShape': shape(versions[0]) if versions else None,
        'versionBucketCounts': dict(collections.Counter(x.get('bucket', '?') for x in versions)),
        'originalRecordsScalars': {k: v for k, v in original.items() if isinstance(v, (bool, int, type(None)))},
        'originalRecordCount': len(original.get('files', original.get('records', []))),
        'folderFiles': [p.name for p in folder.iterdir() if p.suffix == '.json' and ('config' in p.name or 'request' in p.name)],
    })
ids = command(['docker', 'ps', '-aq']).split()
containers = json.loads(command(['docker', 'inspect', *ids]))
out['containers'] = [{'name': x['Name'], 'id': x['Id'], 'image': x['Config']['Image'], 'running': x['State']['Running'],
                      'mounts': [{k: m.get(k) for k in ['Type', 'Source', 'Destination', 'RW']} for m in x['Mounts']]} for x in containers if x['State']['Running']]
for name in ['source-identity.json', 'object-source.json', 'reference-recipe.json']:
    doc = json.loads((base / 'configuration' / name).read_bytes())
    out[name] = {k: v for k, v in doc.items() if not any(x in k.lower() for x in ['secret', 'password', 'token', 'credential'])}
print(json.dumps(out))
