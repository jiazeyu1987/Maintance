"""Read only small operation metadata and emit timestamps, never business payloads."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
oids = ['smallapp-bf67a867d3ec4e369ca31657c45e62c6',
        'smallapp-4c3942b0fdeb42f8b95b5db8c732d99d',
        'smallapp-9d06cdef2d6d4a589db0506193629d5c']
allowed = {'state', 'status', 'action', 'operationId', 'requestId', 'actualExitCode',
           'errorCode', 'failureCode', 'phase', 'stage', 'kind', 'backupKind',
           'elapsedSeconds', 'completed'}
date = re.compile(r'^2026-\d\d-\d\d[T ]\d\d:\d\d:\d\d')
def fields(value, trail=''):
    out = []
    if trail.count('.') > 3 or '[' in trail:
        return out
    if isinstance(value, dict):
        for key, child in value.items():
            if any(x in key.lower() for x in ['secret', 'password', 'token', 'credential']):
                continue
            name = trail + '.' + key
            if key in allowed and isinstance(child, (str, int, bool, type(None))):
                out.append({'field': name, 'value': child})
            elif isinstance(child, str) and date.match(child):
                out.append({'field': name, 'value': child})
            elif isinstance(child, (dict, list)):
                out.extend(fields(child, name))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out.extend(fields(child, trail + '[' + str(i) + ']'))
    return out

out = {'observedAt': datetime.now(timezone.utc).isoformat(), 'serverWrites': False, 'operations': []}
for oid in oids:
    root = base / 'repository-operations' / hashlib.sha256(oid.encode()).hexdigest()
    row = {'operationId': oid, 'exists': root.is_dir(), 'files': []}
    if root.is_dir():
        for file in sorted(root.iterdir()):
            if not file.is_file():
                continue
            if not (file.name.startswith('timing-') or file.name in {
                'start.json', 'result.json', 'request.json', 'worker-process.json',
                'capture-process.json', 'capture-output.json', 'capture-terminal.json',
                'readback-preflight.json'}):
                continue
            rec = {'name': file.name, 'bytes': file.stat().st_size}
            if file.suffix == '.json' and file.stat().st_size < 4 * 1024 * 1024:
                doc = json.loads(file.read_bytes())
                rec['fields'] = fields(doc)
                rec['topKeys'] = list(doc) if isinstance(doc, dict) else []
            row['files'].append(rec)
    out['operations'].append(row)
print(json.dumps(out))
