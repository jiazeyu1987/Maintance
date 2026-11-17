import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
config = json.loads((base / 'configuration/capture.json').read_bytes())
source = config['source']
container = source['mysqlContainerId']
inspect = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=10))[0]
assert inspect['Name'] == '/intruoyi-mysql' and inspect['State']['Running']
password = Path(source['passwordPin']['path']).read_text().strip()
query = "SELECT @@server_uuid; SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME; SELECT TABLE_SCHEMA,COUNT(*) FROM information_schema.TABLES WHERE TABLE_TYPE='BASE TABLE' GROUP BY TABLE_SCHEMA;"
cmd = ['docker', 'exec', '-i', container, 'sh', '-c', 'read -r MYSQL_PWD; export MYSQL_PWD; exec mysql -uroot --batch --skip-column-names --default-character-set=utf8mb4']
p = subprocess.run(cmd, input=(password + '\n' + query).encode(), capture_output=True, timeout=15)
assert p.returncode == 0 and not p.stderr, 'READ_ONLY_SCHEMA_LIST_FAILED'
lines = p.stdout.decode().splitlines()
assert lines[0] == source['databaseUuid']
out = {'serverWrites': False, 'observedAt': datetime.now(timezone.utc).isoformat(), 'schemaListAndTableCounts': lines[1:], 'minioTopLevelDirectories': sorted(p.name for p in Path(source['minioDataPath']).iterdir() if p.is_dir()), 'configuredPhysicalScopes': source['minioPhysicalScopes'], 'operations': []}
for name in ['source-scope.json', 'derived-recipe.json']:
    path = base / 'configuration' / name
    if name == 'derived-recipe.json':
        path = Path(json.loads((base / 'configuration/object-source.json').read_bytes())['derivedRecipePin']['path'])
    out[name] = json.loads(path.read_bytes())
for op in ['smallapp-8d9db80d8f1e4531ba9a0234335d0dcb', 'smallapp-bf67a867d3ec4e369ca31657c45e62c6']:
    result = json.loads((base / 'repository-operations' / hashlib.sha256(op.encode()).hexdigest() / 'result.json').read_bytes())
    manifest = json.loads(Path(result['data']['manifestPin']['path']).read_bytes())
    pins = manifest['payloadRefs']
    missing = []
    sizes = []
    started = time.monotonic()
    for pin in pins:
        path = Path(pin['path'])
        if not path.is_file():
            missing.append(pin['path'])
        elif path.stat().st_size != pin['bytes']:
            sizes.append({'path': pin['path'], 'expected': pin['bytes'], 'actual': path.stat().st_size})
    out['operations'].append({'operation': op, 'payloadRefsChecked': len(pins), 'expectedBytes': sum(p['bytes'] for p in pins), 'missingPayloads': missing, 'sizeDifferences': sizes, 'statSeconds': round(time.monotonic()-started,2)})
print(json.dumps(out))
