import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config = json.loads((root / 'target-configuration.json').read_bytes())
result = json.loads((root / 'result.json').read_bytes())
def load(pin):
    raw = Path(pin['path']).read_bytes()
    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    return json.loads(raw)
pin = result['data']['orderedChainPins'][-1]
load(pin)
material = json.loads(Path(pin['path']).with_name('recovery-material.json').read_bytes())
source = load(material['database']['expectedDataPin'])['schema']
sys.path.insert(0, '/mnt/intruoyi-data/recovery-tools/engine/formal')
from formal_schema_evidence import _meta_query, _decode_metadata, _canonical_schema_body, parse_rows, identifier
container = next(s['id'] for s in config['services'] if s['role'] == 'mysql')
inspect = json.loads(subprocess.check_output(['docker', 'inspect', container], timeout=10))[0]
assert inspect['Name'] == '/spug-empty59-a029c09a7b8b-mysql' and inspect['State']['Running']
catalogs = {'TABLES': 'SHOW FULL TABLES;', 'ROUTINES': _meta_query('ROUTINES',['ROUTINE_NAME','ROUTINE_TYPE'],'CAST(ROUTINE_NAME AS BINARY)'), 'TRIGGERS': _meta_query('TRIGGERS',['TRIGGER_NAME','EVENT_OBJECT_TABLE','EVENT_MANIPULATION','ACTION_TIMING','ACTION_ORDER'],'CAST(TRIGGER_NAME AS BINARY)'), 'EVENTS': _meta_query('EVENTS',['EVENT_NAME'],'CAST(EVENT_NAME AS BINARY)'), 'COLUMNS': _meta_query('COLUMNS',['TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','COLUMN_TYPE','CHARACTER_SET_NAME','COLLATION_NAME','IS_NULLABLE','COLUMN_DEFAULT','EXTRA','GENERATION_EXPRESSION'],'CAST(TABLE_NAME AS BINARY),ORDINAL_POSITION')}
queries = ["USE `ruoyi-vue-pro`; SET SESSION time_zone='+00:00'; SET SESSION MAX_EXECUTION_TIME=20000; START TRANSACTION READ ONLY;", "SELECT 'IDENTITY',@@server_uuid;"]
for kind, query in catalogs.items():
    queries.extend(["SELECT 'CATALOG','" + kind + "';", query])
for kind, values in source['definitions'].items():
    for name in values:
        queries.extend(["SELECT 'DEFINITION','" + kind + "','" + name + "';", 'SHOW CREATE ' + kind + ' ' + identifier(name) + ';'])
queries.extend(["SELECT 'END',@@server_uuid;", 'COMMIT;'])
p = subprocess.run(['docker','exec','-i',container,'timeout','40s','mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names','--default-character-set=utf8mb4','--binary-as-hex'],input='\n'.join(queries).encode(),capture_output=True,timeout=45)
assert p.returncode == 0 and not p.stderr, 'READ_ONLY_SCHEMA_QUERY_FAILED'
rows = parse_rows(p.stdout)
assert rows[0] == ['IDENTITY','f6ccd898-e207-11f1-bd88-0242ac1dee20'] and rows[-1] == ['END','f6ccd898-e207-11f1-bd88-0242ac1dee20']
target = {k:v for k,v in source.items() if k not in ['catalog','definitions']}
target['catalog'] = {}
target['definitions'] = {k:{} for k in source['definitions']}
current = None
def flush():
    if current is not None:
        if current[0] == 'CATALOG':
            target['catalog'][current[1]] = sorted(pending) if current[1] == 'TABLES' else _decode_metadata(pending)
        else:
            assert len(pending) == 1
            target['definitions'][current[1]][current[2]] = pending[0][:-1] if current[1]=='TRIGGER' else pending[0]
for row in rows[1:]:
    if row[0] in ['CATALOG','DEFINITION','END']:
        flush()
        current = row if row[0] != 'END' else None
        pending = []
    else:
        pending.append(row)
source_body = _canonical_schema_body(source)
target_body = _canonical_schema_body(target)
catalog_differences = {k: {'sourceRows':len(source['catalog'][k]),'targetRows':len(v)} for k,v in target['catalog'].items() if v != source['catalog'][k]}
definition_differences = {k: [name for name,v in values.items() if v != source_body['definitions'][k][name]] for k,values in target_body['definitions'].items()}
import re
auto_increment_only = {}
for name in definition_differences.get('TABLE',[]):
    left = source_body['definitions']['TABLE'][name][1]
    right = target_body['definitions']['TABLE'][name][1]
    auto_increment_only[name] = re.sub(r' AUTO_INCREMENT=[0-9]+','',left) == re.sub(r' AUTO_INCREMENT=[0-9]+','',right)
print(json.dumps({'serverWrites':False,'observedAt':datetime.now(timezone.utc).isoformat(),'catalogEqual':not catalog_differences,'catalogDifferences':catalog_differences,'objectCounts':{k:len(v) for k,v in target['definitions'].items()},'canonicalDefinitionDifferences':{k:v for k,v in definition_differences.items() if v},'autoIncrementOnlyDifferences':auto_increment_only,'excludedHistoricalFields':source['excludedHistoricalFields']}))
