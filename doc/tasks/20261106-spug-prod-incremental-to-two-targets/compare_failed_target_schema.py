"""Read actual fenced MySQL metadata in a bounded batch; preserve all raw differences privately."""
import json
from common import PRIVATE, TASK, remote, write

SCRIPT = r'''
import datetime,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
def read(pin):
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 return json.loads(raw)
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=read(receipt['ownerConfigurationPin']);target=owner['targets'][receipt['targetConfigRef']]
sys.path.insert(0,owner['formalModuleDirectory'])
from formal_schema_evidence import SchemaMySql,identifier,_meta_query,_decode_metadata,_canonical_bytes,_canonical_schema_body,compare_schema
rows=json.loads(subprocess.check_output(['docker','inspect',*[s['id'] for s in target['services']]],timeout=15))
roles={s['role']:next(r for r in rows if r['Id']==s['id']) for s in target['services']}
assert all(not roles[k]['State']['Running'] for k in ('backend','frontend','minio')),'WRITERS_NOT_STOPPED'
assert roles['mysql']['State']['Running']
secret=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'];raw=pathlib.Path(secret['path']).read_bytes()
assert len(raw)==secret['bytes'] and hashlib.sha256(raw).hexdigest()==secret['sha256'] and not any(c in raw for c in (b'\n',b'\r',b'\0'))
mysql=SchemaMySql(roles['mysql']['Id'],raw.decode('utf-8'),timeout=120)
database=target['database'];uuid=target['replacement']['databaseUuid']
def query(sql):return mysql.schema_query(sql,database=database,expected_uuid=uuid)
flags=query('SELECT @@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;')
assert flags==[['OFF','0','0']],'FENCED_TARGET_STATE_CHANGED'
catalogs={
 'TABLES':'SHOW FULL TABLES;',
 'ROUTINES':_meta_query('ROUTINES',['ROUTINE_NAME','ROUTINE_TYPE'],'CAST(ROUTINE_NAME AS BINARY)'),
 'TRIGGERS':_meta_query('TRIGGERS',['TRIGGER_NAME','EVENT_OBJECT_TABLE','EVENT_MANIPULATION','ACTION_TIMING','ACTION_ORDER'],'CAST(TRIGGER_NAME AS BINARY)'),
 'EVENTS':_meta_query('EVENTS',['EVENT_NAME'],'CAST(EVENT_NAME AS BINARY)'),
 'COLUMNS':_meta_query('COLUMNS',['TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','COLUMN_TYPE','CHARACTER_SET_NAME','COLLATION_NAME','IS_NULLABLE','COLUMN_DEFAULT','EXTRA','GENERATION_EXPRESSION'],'CAST(TABLE_NAME AS BINARY),ORDINAL_POSITION')}
def catalog():return {k:sorted(query(q)) if k=='TABLES' else _decode_metadata(query(q)) for k,q in catalogs.items()}
before=catalog();entries=[('DATABASE',database,2)]
entries += [('TABLE' if r[1]=='BASE TABLE' else 'VIEW',r[0],2 if r[1]=='BASE TABLE' else 4) for r in before['TABLES']]
entries += [(r[1],r[0],6) for r in before['ROUTINES']]
entries += [('TRIGGER',r[0],7) for r in before['TRIGGERS']]
entries += [('EVENT',r[0],7) for r in before['EVENTS']]
actual=query('\n'.join('SHOW CREATE '+kind+' '+identifier(name)+';' for kind,name,_ in entries))
assert len(actual)==len(entries),'METADATA_BATCH_ROW_COUNT_CHANGED'
definitions={kind:{} for kind in ('DATABASE','TABLE','VIEW','FUNCTION','PROCEDURE','TRIGGER','EVENT')}
for (kind,name,length),row in zip(entries,actual):
 assert len(row)==length and row[0]==name,'METADATA_BATCH_ROW_IDENTITY_CHANGED'
 definitions[kind][name]=row[:-1] if kind=='TRIGGER' else row
assert catalog()==before and query('SELECT @@GLOBAL.event_scheduler,@@GLOBAL.read_only,@@GLOBAL.super_read_only;')==flags,'TARGET_METADATA_CHANGED'
value=dict(database=database,catalog=before,definitions=definitions,objectCounts={k:len(v) for k,v in definitions.items()},excludedHistoricalFields=['SHOW CREATE TRIGGER.Created'],fullDataEquivalenceVerified=False,productionEvidence=False)
value['schemaSha256']=hashlib.sha256(_canonical_bytes(value)).hexdigest()
value['observationIdentity']=dict(containerId=mysql.container,databaseUuid=uuid)
value['observationSha256']=hashlib.sha256(_canonical_bytes(value)).hexdigest()
expected=read(EXPECTED_PIN)['schema']
differences=[]
for kind in before:
 if expected['catalog'][kind]!=before[kind]:
  left={json.dumps(x,ensure_ascii=False) for x in expected['catalog'][kind]};right={json.dumps(x,ensure_ascii=False) for x in before[kind]}
  differences.append(dict(type='catalog',kind=kind,sourceOnly=sorted(left-right),targetOnly=sorted(right-left)))
left=_canonical_schema_body(expected)['definitions'];right=_canonical_schema_body(value)['definitions']
for kind in left:
 for name in sorted(set(left[kind])|set(right[kind])):
  if left[kind].get(name)!=right[kind].get(name):differences.append(dict(type='definition',kind=kind,name=name,source=left[kind].get(name),target=right[kind].get(name)))
try:comparison=compare_schema(expected,value)
except Exception as error:comparison=dict(errorCode=getattr(error,'code',type(error).__name__))
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),expectedPin=EXPECTED_PIN,expectedSchema=expected,actualSchema=value,differences=differences,comparison=comparison,actualTargetQueries=True,actualTargetMutation=False)))
'''

if __name__ == '__main__':
    point = json.loads((TASK / 'new-incremental-point-verified.json').read_text(encoding='utf-8'))
    value = remote('172.30.30.58', 'EXPECTED_PIN=' + repr(point['database']['expectedDataPin']) + '\n' + SCRIPT, 180)
    write(PRIVATE / 'restore-368-schema-comparison.private.json', value)
    report = {k: value[k] for k in ('observedAt', 'expectedPin', 'comparison', 'actualTargetQueries', 'actualTargetMutation')}
    report['catalogEqual'] = value['expectedSchema']['catalog'] == value['actualSchema']['catalog']
    report['differences'] = [{k: v for k, v in row.items() if k in ('type', 'kind', 'name')} |
                             ({'sourceOnlyCount': len(row['sourceOnly']), 'targetOnlyCount': len(row['targetOnly'])} if row['type'] == 'catalog' else {})
                             for row in value['differences']]
    write(TASK / 'restore-368-schema-difference-summary.json', report)
    print(json.dumps(report))
