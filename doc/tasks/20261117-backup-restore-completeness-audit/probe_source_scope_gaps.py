import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

base = Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
config = json.loads((base / 'configuration/capture.json').read_bytes())
source = config['source']
op = 'smallapp-bf67a867d3ec4e369ca31657c45e62c6'
result = json.loads((base / 'repository-operations' / hashlib.sha256(op.encode()).hexdigest() / 'result.json').read_bytes())
material = json.loads(Path(result['data']['recoveryMaterialPin']['path']).read_bytes())
expected = json.loads(Path(material['database']['expectedDataPin']['path']).read_bytes())['schema']['catalog']['TABLES']
container = source['mysqlContainerId']
inspect = json.loads(subprocess.check_output(['docker','inspect',container],timeout=5))[0]
assert inspect['Name'] == '/intruoyi-mysql'
password = Path(source['passwordPin']['path']).read_text().strip()
query = "SELECT TABLE_NAME,TABLE_TYPE,CREATE_TIME FROM information_schema.TABLES WHERE TABLE_SCHEMA='ruoyi-vue-pro' ORDER BY TABLE_NAME;"
cmd = ['docker','exec','-i',container,'sh','-c','read -r MYSQL_PWD; export MYSQL_PWD; exec mysql -uroot --batch --skip-column-names --default-character-set=utf8mb4']
p = subprocess.run(cmd,input=(password+'\n'+query).encode(),capture_output=True,timeout=15)
assert p.returncode == 0 and not p.stderr
tables = [line.split('\t') for line in p.stdout.decode().splitlines()]
expected_names = {r[0] for r in expected}
out = {'serverWrites':False,'observedAt':datetime.now(timezone.utc).isoformat(),'sourceCurrentTablesNotInFrozenPoint':[r for r in tables if r[0] not in expected_names],'frozenTablesNotInCurrentSource':sorted(expected_names-{r[0] for r in tables}),'configurationReferences':source['configurationPins'],'capturedRedisDatabase':source['redisSnapshot']['database']}
redis_container = source['redisSnapshot']['containerId']
p = subprocess.run(['docker','exec',redis_container,'redis-cli','INFO','keyspace'],capture_output=True,timeout=10)
assert p.returncode == 0 and not p.stderr
out['currentRedisKeyspace'] = p.stdout.decode().splitlines()
backend = json.loads(subprocess.check_output(['docker','inspect','intruoyi-backend'],timeout=5))[0]
out['currentBackendRedisDatabaseEnv'] = [v for v in backend['Config'].get('Env',[]) if re.match(r'(SPRING_(DATA_)?REDIS_DATABASE|REDIS_DATABASE)=',v)]
paths = ['/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/runtime','/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/uploads','/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/results','/var/lib/docker/fenbeitong-release/data','/opt/intruoyi/runtime/website/dist']
out['externalMountedData'] = []
for text in paths:
    path = Path(text)
    rows = [p for p in path.rglob('*') if p.is_file()] if path.is_dir() else []
    out['externalMountedData'].append({'path':text,'files':len(rows),'bytes':sum(p.stat().st_size for p in rows)})
print(json.dumps(out))
