import json
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024')
folder = root / 'recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e'
out = {'host': '172.30.30.59', 'serverWrites': False, 'exists': folder.is_dir()}
if folder.is_dir():
    out['files'] = [{'name': p.name, 'directory': p.is_dir(), 'bytes': p.stat().st_size} for p in folder.iterdir()]
    result = json.loads((folder / 'result.json').read_bytes())
    out['result'] = result
print(json.dumps(out))
