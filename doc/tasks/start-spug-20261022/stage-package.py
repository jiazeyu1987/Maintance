import hashlib
import json
import zipfile
from pathlib import Path

source = Path('C:/Users/D01021/Documents/Spug-complete-20261022-151627.zip')
root = Path('C:/Spug/Spug-complete-20261022-151627')
root.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(source) as archive:
    prefix = 'Spug-complete-20261022-151627/'
    manifest = json.loads(archive.read(prefix + 'SHA256SUMS.json').decode('utf-8-sig'))
    for row in manifest:
        target = (root / row['path']).resolve()
        if not target.is_relative_to(root) or target.exists():
            raise RuntimeError('Unsafe or existing output: ' + row['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        with archive.open(prefix + row['path']) as src, target.open('xb') as dst:
            while chunk := src.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                dst.write(chunk)
        if size != row['bytes'] or digest.hexdigest() != row['sha256']:
            raise RuntimeError('Hash mismatch: ' + row['path'])
        print('PASS: ' + row['path'], flush=True)
    (root / 'SHA256SUMS.json').write_bytes(archive.read(prefix + 'SHA256SUMS.json'))
print('PASS: complete package staged and verified', flush=True)
