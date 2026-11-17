import collections
import hashlib
import json
from pathlib import Path

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
ids = ['smallapp-8d9db80d8f1e4531ba9a0234335d0dcb', 'smallapp-bf67a867d3ec4e369ca31657c45e62c6']
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
def shape(value):
    if isinstance(value, dict):
        return {'type': 'dict', 'count': len(value), 'keys': list(value)[:25]}
    if isinstance(value, list):
        return {'type': 'list', 'count': len(value), 'firstShape': shape(value[0]) if value else None}
    return value
out = {'operations': [], 'configurationFiles': [p.name for p in (base / 'configuration').iterdir()]}
for op in ids:
    result = json.loads((base / 'repository-operations' / hashlib.sha256(op.encode()).hexdigest() / 'result.json').read_bytes())
    material = load(result['data']['recoveryMaterialPin'])
    refs = load(material['referenceInventoryPin'])
    point = load(result['data']['pointPin'])
    manifest = load(result['data']['manifestPin'])
    readback = load(result['data']['readbackPin'])
    objects = material['objects']
    database = material['database']
    data = load(database['expectedDataPin'])
    entry = {
        'operation': op, 'database': database,
        'dataShape': {k: shape(v) for k, v in data.items()},
        'tableNames': sorted(data.get('tables', {})),
        'tableRowsTotal': sum(t.get('rows', 0) for t in data.get('tables', {}).values()),
        'tableExample': {k: v for k, v in list(data.get('tables', {}).items())[:1]},
        'objectsShape': {k: shape(v) for k, v in objects.items()},
        'referenceShape': {k: shape(v) for k, v in refs.items()},
        'referenceBucketCounts': dict(collections.Counter(x['bucket'] for x in refs.get('objectReferences', []))),
        'missingReferences': refs.get('sourceMissingObjectReferences'),
        'pointParentPins': point['parentPointPins'],
        'manifestShape': {k: shape(v) for k, v in manifest.items()},
        'readbackShape': {k: shape(v) for k, v in readback.items()},
        'readbackPayloadsEqualManifest': readback['payloadRefs'] == manifest['payloadRefs'],
    }
    if isinstance(refs.get('sourceMissingObjectReferences'), list):
        entry['missingReferences'] = {'count': len(refs['sourceMissingObjectReferences'])}
    out['operations'].append(entry)
print(json.dumps(out))
