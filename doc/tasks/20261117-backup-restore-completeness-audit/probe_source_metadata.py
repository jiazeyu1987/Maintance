"""Read original metadata only; never start a capture or acquire an exclusive lock."""
import hashlib
import json
from pathlib import Path

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
operations = ['smallapp-8d9db80d8f1e4531ba9a0234335d0dcb',
              'smallapp-bf67a867d3ec4e369ca31657c45e62c6']
out = {'host': '172.30.30.57', 'serverWrites': False, 'operations': []}
for operation in operations:
    folder = base / 'repository-operations' / hashlib.sha256(operation.encode()).hexdigest()
    result = json.loads((folder / 'result.json').read_bytes())
    capture = json.loads((base / 'capture-staging' / operation / 'capture-recovery-inputs.json').read_bytes())
    records = []
    def walk(value, trail):
        if isinstance(value, dict):
            if set(value) == {'path', 'bytes', 'sha256'}:
                p = Path(value['path'])
                row = {'field': trail, 'pin': value, 'exists': p.is_file()}
                if p.is_file() and p.stat().st_size < 12 * 1024 * 1024:
                    raw = p.read_bytes()
                    row['pinVerified'] = len(raw) == value['bytes'] and hashlib.sha256(raw).hexdigest() == value['sha256']
                    if p.suffix == '.json':
                        doc = json.loads(raw)
                        row['keys'] = list(doc) if isinstance(doc, dict) else ['list', len(doc)]
                        if isinstance(doc, dict):
                            row['safeScalars'] = {k: v for k, v in doc.items() if isinstance(v, (str, int, bool, type(None))) and not any(x in k.lower() for x in ('secret', 'key', 'password', 'token', 'credential'))}
                records.append(row)
                return
            for k, v in value.items():
                walk(v, trail + '.' + k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, trail + '[' + str(i) + ']')
    walk(result, 'result')
    for key in ['capturePointPin', 'configurationPins', 'fileInventoryPin', 'materialIndexPin',
                'objectContentIndexPin', 'parentRepositoryPointPin', 'semanticSupplement']:
        walk(capture.get(key), 'capture.' + key)
    walk(capture.get('database', {}).get('expectedDataPin'), 'capture.database.expectedDataPin')
    out['operations'].append({
        'operation': operation, 'resultKeys': list(result),
        'resultState': result.get('state'), 'actualExitCode': result.get('actualExitCode'),
        'resultDataKeys': list(result.get('data', {})),
        'captureKeys': list(capture), 'database': capture.get('database'),
        'attachmentsKeys': list(capture.get('attachments', {})),
        'semanticSupplementKeys': list(capture.get('semanticSupplement', {})),
        'metadataPins': records,
    })
print(json.dumps(out))
