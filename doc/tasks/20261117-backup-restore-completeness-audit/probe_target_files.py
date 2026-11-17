"""Read-only physical payload coverage and bounded content hashing."""
import collections
import hashlib
import json
import stat
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config = json.loads((root / 'target-configuration.json').read_bytes())
result = json.loads((root / 'result.json').read_bytes())
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
materials = []
expected_payloads = {}
for pin in result['data']['orderedChainPins']:
    load(pin)
    material = json.loads(Path(pin['path']).with_name('recovery-material.json').read_bytes())
    point = load(material['objects']['capturePointPin'])
    for name in point['fileDelta']['deletedPaths']:
        expected_payloads.pop(name, None)
    expected_payloads.update(material['objects']['filePayloadPins'])
    inventory = load(material['objects']['fileInventoryPin'])
    materials.append(material)
files = {k: v for k, v in inventory.items() if v['kind'] == 'file'}
assert set(files) == set(expected_payloads)
assert all(v['bytes'] == expected_payloads[k]['bytes'] and v['sha256'] == expected_payloads[k]['sha256'] for k,v in files.items())
container = next(s['id'] for s in config['services'] if s['role'] == 'minio')
inspect = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=10))[0]
assert inspect['Name'] == '/spug-empty59-a029c09a7b8b-minio' and inspect['State']['Running']
data = Path(next(m['Source'] for m in inspect['Mounts'] if m['Destination'] == config['dataPolicy']['minioDataMount']))
assert data == Path('/mnt/intruoyi-data/spug-empty59-a029c09a7b8b/minio')
names = sorted(files)[AUDIT_BATCH * 2000:(AUDIT_BATCH + 1) * 2000]
if 'AUDIT_START' in globals():
    names = sorted(files)[AUDIT_START:AUDIT_END]
started = time.monotonic()
missing = []
size_differences = []
hash_differences = []
checked = 0
bytes_hashed = 0
groups = collections.Counter()
for name in names:
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    path = data / name
    try:
        observed = path.lstat()
    except FileNotFoundError:
        missing.append(name)
        continue
    if not stat.S_ISREG(observed.st_mode) or observed.st_size != files[name]['bytes']:
        size_differences.append({'name': name, 'expected': files[name]['bytes'], 'actual': observed.st_size, 'regularFile': stat.S_ISREG(observed.st_mode)})
    if not stat.S_ISREG(observed.st_mode):
        continue
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            bytes_hashed += len(chunk)
    if digest.hexdigest() != files[name]['sha256']:
        hash_differences.append(name)
    checked += 1
    groups[name.split('/')[0]] += 1
    if time.monotonic() - started > 48:
        break
print(json.dumps({'serverWrites': False, 'observedAt': datetime.now(timezone.utc).isoformat(), 'batch': AUDIT_BATCH, 'seconds': round(time.monotonic()-started,2), 'expectedTotalFiles': len(files), 'selectedFiles': len(names), 'contentChecked': checked, 'bytesHashed': bytes_hashed, 'bucketCheckedCounts': dict(groups), 'completeBatch': checked + len(missing) == len(names), 'missingFiles': missing, 'sizeDifferences': size_differences, 'hashDifferences': hash_differences, 'chainPayloadCoverageVerified': True}))
