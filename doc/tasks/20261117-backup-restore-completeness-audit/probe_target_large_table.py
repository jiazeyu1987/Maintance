"""Read bounded row ranges from a large binary-payload table, emitting only digests."""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config = json.loads((root / 'target-configuration.json').read_bytes())
result = json.loads((root / 'result.json').read_bytes())
tables = {}
for pin in result['data']['orderedChainPins']:
    material = json.loads(Path(pin['path']).with_name('recovery-material.json').read_bytes())
    raw = Path(material['database']['expectedDataPin']['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == material['database']['expectedDataPin']['sha256']
    expected = json.loads(raw)
    tables.update(expected['tables'])
expected['tables'] = tables
name = 'showroom_release_asset'
columns = [c for c in expected['schema']['catalog']['COLUMNS'] if c[0] == name]
sys.path.insert(0,'/mnt/intruoyi-data/recovery-tools/engine/formal')
from formal_data_evidence import _cell
container = next(s['id'] for s in config['services'] if s['role']=='mysql')
inspect = json.loads(subprocess.check_output(['docker','inspect',container],timeout=5))[0]
assert inspect['Name'] == '/spug-empty59-a029c09a7b8b-mysql' and inspect['State']['Running']
queries = ["USE `ruoyi-vue-pro`; SET SESSION time_zone='+00:00'; SET SESSION MAX_EXECUTION_TIME=40000; START TRANSACTION WITH CONSISTENT SNAPSHOT,READ ONLY;", "SELECT 'IDENTITY',@@server_uuid;"]
start = AUDIT_BATCH*1000
end = min(start+1000,expected['tables'][name]['rows'])
if 'AUDIT_START' in globals():
    start = AUDIT_START
    end = AUDIT_END
assert not any(c[3]=='json' for c in columns)
cells=[_cell(c) for c in columns]
sql="SELECT SHA2(CONCAT('row/v1:',"+','.join(cells)+'),256) FROM `'+name+'` ORDER BY `id` LIMIT '+str(start)+','+str(end-start)+';'
queries.extend([sql,"SELECT 'WARNING',@@warning_count;"])
queries.extend(["SELECT 'IDENTITY',@@server_uuid;",'COMMIT;'])
started = time.monotonic()
p = subprocess.run(['docker','exec','-i',container,'timeout','48s','mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names','--default-character-set=utf8mb4','--quick'],input='\n'.join(queries).encode(),capture_output=True,timeout=52)
assert p.returncode==0 and not p.stderr,'READ_ONLY_RANGE_QUERY_FAILED exit='+str(p.returncode)+' errorCodes='+str(re.findall(rb'ERROR [0-9]+',p.stderr))
digests=[];current=None;rows=start;nodes=0
for line in p.stdout.splitlines():
    parts=line.split(b'\t')
    if parts[0]==b'IDENTITY':assert parts[1]==b'f6ccd898-e207-11f1-bd88-0242ac1dee20'
    elif parts[0]==b'WARNING':assert parts[1]==b'0'
    else:
        assert len(parts)==1 and re.fullmatch(b'[0-9a-f]{64}',parts[0])
        rows+=1
        digests.append(hashlib.sha256(b'complete-row/v1:'+parts[0]+b'\n').hexdigest())
assert rows==end
print(json.dumps({'serverWrites':False,'table':name,'batch':AUDIT_BATCH,'start':start,'end':end,'jsonNodes':nodes,'expected':expected['tables'][name],'rowDigests':digests,'seconds':round(time.monotonic()-started,2)}))
