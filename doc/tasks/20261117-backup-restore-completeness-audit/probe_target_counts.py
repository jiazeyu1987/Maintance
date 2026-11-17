import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config = json.loads((root / 'target-configuration.json').read_bytes())
result = json.loads((root / 'result.json').read_bytes())
assert result['state'] == 'SUCCEEDED'
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
expected = {}
for point_pin in result['data']['orderedChainPins']:
    point = load(point_pin)
    binding = json.loads(Path(point_pin['path']).with_name('recovery-material.json').read_bytes())
    expected.update(load(binding['database']['expectedDataPin'])['tables'])
assert len(expected) == 907
container = next(s['id'] for s in config['services'] if s['role'] == 'mysql')
inspect = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=10))[0]
assert inspect['Name'] == '/spug-empty59-a029c09a7b8b-mysql'
assert inspect['State']['Running']
queries = ["SET SESSION MAX_EXECUTION_TIME=40000; START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;",
           "SELECT 'identity',@@server_uuid;",
           "SELECT 'table',TABLE_NAME,TABLE_TYPE FROM information_schema.TABLES WHERE TABLE_SCHEMA='ruoyi-vue-pro' ORDER BY TABLE_NAME;"]
for name in sorted(expected):
    assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name)
    queries.append("SELECT 'count','" + name + "',COUNT(*) FROM `ruoyi-vue-pro`.`" + name + "`;")
queries.append('COMMIT;')
p = subprocess.run(['docker', 'exec', '-i', container, 'mysql', '--defaults-extra-file=/run/recovery/mysql-client.cnf',
                    '--batch', '--skip-column-names'], input='\n'.join(queries).encode(), capture_output=True, timeout=50)
assert p.returncode == 0, 'Read-only all-table counts failed: ' + p.stderr.decode(errors='replace')[-500:]
rows = [x.split('\t') for x in p.stdout.decode('utf-8').splitlines()]
tables = {x[1] for x in rows if x[0] == 'table' and x[2] == 'BASE TABLE'}
counts = {x[1]: int(x[2]) for x in rows if x[0] == 'count'}
out = {'serverWrites': False, 'observedAt': datetime.now(timezone.utc).isoformat(),
       'expectedTableCount': len(expected), 'actualTableCount': len(tables),
       'missingTables': sorted(set(expected) - tables), 'extraTables': sorted(tables - set(expected)),
       'countChecked': len(counts), 'matchingCountTables': sum(counts[k] == expected[k]['rows'] for k in counts),
       'differentCounts': {k: {'expected': expected[k]['rows'], 'actual': counts[k]} for k in counts if counts[k] != expected[k]['rows']},
       'expectedCounts': {k: v['rows'] for k, v in expected.items()}, 'actualCounts': counts}
print(json.dumps(out))
