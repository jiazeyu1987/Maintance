"""Read-only row-multiset comparison; returns hashes and totals, never row values."""
import hashlib
import json
import re
import subprocess
import sys
import time
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
schema = None
for point_pin in result['data']['orderedChainPins']:
    load(point_pin)
    binding = json.loads(Path(point_pin['path']).with_name('recovery-material.json').read_bytes())
    data = load(binding['database']['expectedDataPin'])
    expected.update(data['tables'])
    schema = data['schema']
assert len(expected) == 907
engine = Path('/mnt/intruoyi-data/recovery-tools/engine/formal')
assert (engine / 'formal_data_evidence.py').is_file()
sys.path.insert(0, str(engine))
from formal_data_evidence import table_sql

container = next(s['id'] for s in config['services'] if s['role'] == 'mysql')
inspect = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=10))[0]
assert inspect['Name'] == '/spug-empty59-a029c09a7b8b-mysql' and inspect['State']['Running']
names = sorted(expected)[AUDIT_BATCH * 200:(AUDIT_BATCH + 1) * 200]
if 'AUDIT_START' in globals():
    names = sorted(expected)[AUDIT_START:AUDIT_END]
if globals().get('AUDIT_HISTORICAL'):
    names = ['dcc_controlled_file_access_log', 'infra_api_access_log', 'infra_api_error_log', 'system_login_log', 'system_oauth2_access_token', 'system_oauth2_refresh_token']
queries = ["USE `ruoyi-vue-pro`; SET SESSION time_zone='+00:00'; SET SESSION cte_max_recursion_depth=101; SET SESSION MAX_EXECUTION_TIME=40000; START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;", "SELECT 'IDENTITY',@@server_uuid;"]
for name in names:
    queries.append("SELECT 'TABLE','" + name + "';")
    columns = [c for c in schema['catalog']['COLUMNS'] if c[0] == name]
    sql = table_sql(name, columns)
    if globals().get('AUDIT_HISTORICAL'):
        sql = sql.replace(' FROM `' + name + '`)', ' FROM (SELECT * FROM `' + name + '` ORDER BY `id` LIMIT ' + str(expected[name]['rows']) + ') AS audit_history)')
    if any(c[3] == 'json' for c in columns) and expected[name]['rows'] > 500:
        for offset in range(0, expected[name]['rows'] + 1, 500):
            partitioned = sql.replace('ROW_NUMBER() OVER () AS rid', 'ROW_NUMBER() OVER () + ' + str(offset) + ' AS rid')
            partitioned = partitioned.replace(' FROM `' + name + '`)', ' FROM (SELECT * FROM `' + name + '` ORDER BY `id` LIMIT ' + str(offset) + ',500) AS audit_partition)')
            assert partitioned != sql
            queries.append(partitioned)
            queries.append("SELECT 'CHUNKWARNINGS',@@warning_count;")
    else:
        queries.append(sql)
    queries.append("SELECT 'WARNINGS',@@warning_count;")
queries.extend(["SELECT 'IDENTITY',@@server_uuid;", 'COMMIT;'])
started = time.monotonic()
p = subprocess.run(['docker', 'exec', '-i', container, 'timeout', '48s', 'mysql', '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--batch', '--skip-column-names', '--default-character-set=utf8mb4', '--quick'], input='\n'.join(queries).encode(), capture_output=True, timeout=52)
assert p.returncode == 0 and not p.stderr, 'READ_ONLY_DATA_QUERY_FAILED_OR_WARNING exit=' + str(p.returncode) + ' errorCodes=' + str(re.findall(rb'ERROR [0-9]+', p.stderr)) + ' lastTable=' + str(re.findall(rb'^TABLE\t([a-z0-9_]+)$', p.stdout, re.M)[-1:]) + ' seconds=' + str(round(time.monotonic()-started,2))
assert len(p.stdout) < 200 * 1024 * 1024
observations = {}
table = None
current = None
digests = []
rows = nodes = 0

def finish_row():
    if current is not None:
        digests.append(current.digest())

for line in p.stdout.splitlines():
    parts = line.split(b'\t')
    if parts[0] == b'IDENTITY':
        assert parts[1] == b'f6ccd898-e207-11f1-bd88-0242ac1dee20'
    elif parts[0] == b'CHUNKWARNINGS':
        assert parts[1] == b'0'
    elif parts[0] == b'TABLE':
        assert table is None
        table = parts[1].decode()
        rows = nodes = 0
        current = None
        digests = []
    elif parts[0] == b'WARNINGS':
        assert parts[1] == b'0' and table is not None
        finish_row()
        checksum = hashlib.sha256(b'row-multiset/v1\n')
        for digest in sorted(digests):
            checksum.update(digest)
        observations[table] = {'rows': rows, 'jsonNodes': nodes, 'multisetSha256': checksum.hexdigest()}
        table = None
        current = None
    else:
        assert table is not None and len(parts) == 3
        rid, col, token = int(parts[0]), int(parts[1]), parts[2]
        assert len(token) == 64 and all(c in b'0123456789abcdef' for c in token)
        if col == 0:
            assert rid == rows + 1
            finish_row()
            rows += 1
            current = hashlib.sha256(b'complete-row/v1:' + token + b'\n')
            last = (0, token)
        else:
            assert current is not None and rid == rows and (col, token) >= last
            nodes += 1
            current.update(str(col).encode() + b':' + token + b'\n')
            last = (col, token)
assert table is None and set(observations) == set(names)
inspect_after = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=5))[0]
assert inspect_after['State']['Running']
print(json.dumps({'serverWrites': False, 'observedAt': datetime.now(timezone.utc).isoformat(), 'batch': AUDIT_BATCH, 'seconds': round(time.monotonic() - started, 2), 'tablesChecked': len(observations), 'matchingTables': sum(observations[k] == expected[k] for k in names), 'differences': {k: {'expected': expected[k], 'actual': observations[k]} for k in names if observations[k] != expected[k]}, 'observations': observations}))
