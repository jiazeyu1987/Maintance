"""Complete schema observation, not row equality or application acceptance.

Callers must maintain their actual source/target exclusion guards throughout.
Private client output is bounded and escaped; errors never echo SQL or secrets.
"""
import hashlib
import json
import math
import re
import subprocess
import threading
import time

from formal_snapshot_linux import PrivateDockerMySql, FormalSnapshotError, require, _canonical_bytes


def parse_rows(raw):
    require(type(raw) is bytes and (not raw or raw.endswith(b'\n')) and
            not any(c in raw for c in (b'\0',b'\r')), 'FORMAL_SCHEMA_TRANSPORT_INVALID')
    try:
        rows=[]
        for line in (raw.decode('utf-8',errors='strict')[:-1].split('\n') if raw else []):
            row=[]
            for part in line.split('\t'):
                if part=='\\N':row.append(None);continue
                value=[];i=0
                while i<len(part):
                    char=part[i];i+=1
                    if char=='\\':
                        require(i<len(part) and part[i] in '0nrtZ\\','FORMAL_SCHEMA_TRANSPORT_INVALID')
                        char={'0':'\0','n':'\n','r':'\r','t':'\t','Z':'\x1a','\\':'\\'}[part[i]];i+=1
                    value.append(char)
                row.append(''.join(value))
            rows.append(row)
        return rows
    except UnicodeError:raise FormalSnapshotError('FORMAL_SCHEMA_TRANSPORT_INVALID') from None


def _bounded_process(command, input_bytes, limit, seconds, *, sink=None):
    """Deadline includes blocked stdin; remote coreutils timeout is also required."""
    try:process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except OSError:raise FormalSnapshotError('FORMAL_SCHEMA_CLIENT_UNAVAILABLE') from None
    output=bytearray();failed=threading.Event();errors=[];stderr_seen=[]
    def read_output():
        try:
            total=0
            while True:
                chunk=process.stdout.read(65536)
                if not chunk:break
                total+=len(chunk)
                if total>limit:
                    failed.set();return
                if sink is None:output.extend(chunk)
                else:sink.write(chunk)
        except OSError:errors.append('READ');failed.set()
    def read_error():
        try:
            while True:
                chunk=process.stderr.read(65536)
                if not chunk:break
                if not stderr_seen:stderr_seen.append(True)
        except OSError:errors.append('STDERR');failed.set()
    def send():
        try:process.stdin.write(input_bytes);process.stdin.close()
        except OSError:errors.append('WRITE');failed.set()
    threads=[threading.Thread(target=f,daemon=True) for f in (read_output,read_error,send)]
    for thread in threads:thread.start()
    deadline=time.monotonic()+seconds;reason=None
    while process.poll() is None:
        if failed.is_set():reason='FORMAL_SCHEMA_STREAM_LIMIT_OR_IO';break
        if time.monotonic()>=deadline:reason='FORMAL_SCHEMA_QUERY_TIMEOUT';break
        try:process.wait(timeout=min(.05,max(.001,deadline-time.monotonic())))
        except subprocess.TimeoutExpired:pass
    if reason:
        process.kill()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:raise FormalSnapshotError('FORMAL_SCHEMA_CLIENT_TERMINATION_UNCERTAIN') from None
    for thread in threads:thread.join(timeout=5)
    require(not any(t.is_alive() for t in threads),'FORMAL_SCHEMA_STREAM_TERMINATION_UNCERTAIN')
    for stream in (process.stdin,process.stdout,process.stderr):stream.close()
    require(reason is None,reason or 'FORMAL_SCHEMA_QUERY_FAILED')
    require(not failed.is_set() and not errors,'FORMAL_SCHEMA_STREAM_LIMIT_OR_IO')
    require(process.returncode==0 and not stderr_seen,'FORMAL_SCHEMA_QUERY_FAILED_OR_WARNING')
    return bytes(output)


def identifier(name):
    require(type(name) is str and 0<len(name)<=64 and not any(c in name for c in '\0\r\n'),
            'FORMAL_SCHEMA_IDENTIFIER_INVALID')
    return '`'+name.replace('`','``')+'`'


class SchemaMySql(PrivateDockerMySql):
    def query_seconds(self):
        seconds=self.timeout
        deadline=getattr(self,'deadline',None)
        if deadline is not None:
            seconds=min(seconds,deadline-time.monotonic())
            require(seconds>0,'FORMAL_DATA_DEADLINE')
        return seconds

    def schema_query(self,sql,*,database,expected_uuid,max_bytes=16*1024*1024):
        require(type(sql) is str and 0<len(sql.encode('utf-8'))<=1024*1024 and '\0' not in sql,
                'FORMAL_SCHEMA_QUERY_INVALID')
        require(type(expected_uuid) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',expected_uuid)
            and type(max_bytes) is int and 0<max_bytes<=16*1024*1024,'FORMAL_SCHEMA_INPUT_INVALID')
        database=identifier(database)
        wrapped='USE '+database+"; SET SESSION time_zone='+00:00'; SELECT @@server_uuid;\n"+sql+\
            '\nSELECT @@warning_count; SELECT @@server_uuid;\n'
        seconds=self.query_seconds()
        command=self._command('timeout --signal=TERM --kill-after=5 '+str(math.ceil(seconds))+'s mysql',
            ['-uroot','--batch','--skip-column-names','--default-character-set=utf8mb4','--binary-as-hex'])
        rows=parse_rows(_bounded_process(command,(self._password+'\n'+wrapped).encode(),max_bytes,seconds))
        require(len(rows)>=3 and rows[0]==rows[-1]==[expected_uuid] and rows[-2]==['0'],
                'FORMAL_SCHEMA_IDENTITY_OR_WARNING')
        return rows[1:-2]


def _meta_query(table,fields,order):
    # Every scalar is explicitly tagged, including SQL NULL versus text 'NULL'.
    encoded=["IF("+f+" IS NULL,'N',CONCAT('V',HEX(CAST("+f+" AS CHAR CHARACTER SET utf8mb4))))" for f in fields]
    schema='TABLE_SCHEMA' if table=='COLUMNS' else 'ROUTINE_SCHEMA' if table=='ROUTINES' else 'TRIGGER_SCHEMA' if table=='TRIGGERS' else 'EVENT_SCHEMA'
    return 'SELECT '+','.join(encoded)+' FROM information_schema.'+table+' WHERE '+schema+'=DATABASE() ORDER BY '+order+';'


def _decode_metadata(rows):
    result=[]
    for row in rows:
        decoded=[]
        for value in row:
            require(type(value) is str and (value=='N' or re.fullmatch('V(?:[0-9A-F]{2})*',value)),
                    'FORMAL_SCHEMA_METADATA_INVALID')
            try:decoded.append(None if value=='N' else bytes.fromhex(value[1:]).decode('utf-8',errors='strict'))
            except UnicodeError:raise FormalSnapshotError('FORMAL_SCHEMA_METADATA_INVALID') from None
        result.append(decoded)
    return result


def observe_schema(mysql,database,expected_uuid,*,guard):
    require(callable(guard),'FORMAL_SCHEMA_GUARD_REQUIRED');identifier(database)
    require(type(mysql.container) is str and re.fullmatch('[0-9a-f]{64}',mysql.container) and
        type(expected_uuid) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',expected_uuid),
        'FORMAL_SCHEMA_IDENTITY_REQUIRED')
    def query(sql):
        guard()
        value=mysql.schema_query(sql,database=database,expected_uuid=expected_uuid,max_bytes=16*1024*1024)
        guard();return value
    for table in ('COLUMNS','ROUTINES','TRIGGERS','EVENTS'):
        require(query('DESCRIBE information_schema.'+table+';'),'FORMAL_SCHEMA_METADATA_UNAVAILABLE')
    catalogs={
        'TABLES':'SHOW FULL TABLES;',
        'ROUTINES':_meta_query('ROUTINES',['ROUTINE_NAME','ROUTINE_TYPE'],'CAST(ROUTINE_NAME AS BINARY)'),
        'TRIGGERS':_meta_query('TRIGGERS',['TRIGGER_NAME','EVENT_OBJECT_TABLE','EVENT_MANIPULATION','ACTION_TIMING','ACTION_ORDER'],'CAST(TRIGGER_NAME AS BINARY)'),
        'EVENTS':_meta_query('EVENTS',['EVENT_NAME'],'CAST(EVENT_NAME AS BINARY)'),
        'COLUMNS':_meta_query('COLUMNS',['TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','COLUMN_TYPE','CHARACTER_SET_NAME','COLLATION_NAME','IS_NULLABLE','COLUMN_DEFAULT','EXTRA','GENERATION_EXPRESSION'],'CAST(TABLE_NAME AS BINARY),ORDINAL_POSITION')}
    def catalog():
        result={}
        for kind,sql in catalogs.items():
            rows=query(sql)
            result[kind]=sorted(rows) if kind=='TABLES' else _decode_metadata(rows)
        require(len(result['TABLES'])<=5000 and all(len(r)==2 and r[1] in ('BASE TABLE','VIEW') for r in result['TABLES']),
                'FORMAL_SCHEMA_CATALOG_INVALID')
        require(len(result['TABLES'])==len({r[0] for r in result['TABLES']}) and
            all(len(r)==2 and r[1] in ('FUNCTION','PROCEDURE') for r in result['ROUTINES']) and
            all(len(r)==5 and r[4] is not None and r[4].isdigit() and int(r[4])>0 for r in result['TRIGGERS']) and
            all(len(r)==1 for r in result['EVENTS']) and all(len(r)==11 for r in result['COLUMNS']),
                'FORMAL_SCHEMA_CATALOG_INVALID')
        return result
    before=catalog()
    definitions={kind:{} for kind in ('DATABASE','TABLE','VIEW','FUNCTION','PROCEDURE','TRIGGER','EVENT')}
    entries=[('DATABASE',database,2)]
    entries += [('TABLE' if r[1]=='BASE TABLE' else 'VIEW',r[0],2 if r[1]=='BASE TABLE' else 4) for r in before['TABLES']]
    entries += [(r[1],r[0],6) for r in before['ROUTINES']]
    entries += [('TRIGGER',r[0],7) for r in before['TRIGGERS']]
    entries += [('EVENT',r[0],7) for r in before['EVENTS']]
    for kind,name,length in entries:
        rows=query('SHOW CREATE '+kind+' '+identifier(name)+';')
        require(len(rows)==1 and len(rows[0])==length and rows[0][0]==name and
            all(type(v) is str for v in rows[0]) and name not in definitions[kind], 'FORMAL_SCHEMA_DEFINITION_INVALID')
        ddl_index=3 if kind=='EVENT' else 2 if kind in ('TRIGGER','PROCEDURE','FUNCTION') else 1
        require(rows[0][ddl_index].startswith('CREATE '),'FORMAL_SCHEMA_DEFINITION_UNAVAILABLE')
        definitions[kind][name]=rows[0][:-1] if kind=='TRIGGER' else rows[0]
    require(catalog()==before,'FORMAL_SCHEMA_CATALOG_CHANGED')
    value={'database':database,'catalog':before,'definitions':definitions,
        'objectCounts':{kind:len(values) for kind,values in definitions.items()},
        'excludedHistoricalFields':['SHOW CREATE TRIGGER.Created'],
        'fullDataEquivalenceVerified':False,'productionEvidence':False}
    value['schemaSha256']=hashlib.sha256(_canonical_bytes(value)).hexdigest()
    value['observationIdentity']={'containerId':mysql.container,'databaseUuid':expected_uuid}
    value['observationSha256']=hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return value


def _ddl_tokens(sql):
    """Native SHOW CREATE lexer: quoted text/comments cannot be attributes."""
    require(type(sql) is str and sql.startswith('CREATE TABLE '),'FORMAL_SCHEMA_DDL_INVALID')
    tokens=[];i=0
    while i<len(sql):
        if sql[i].isspace():i+=1;continue
        start=i;char=sql[i]
        if sql.startswith('/*',i):
            end=sql.find('*/',i+2)
            require(end>=0,'FORMAL_SCHEMA_DDL_INVALID')
            i=end+2;kind='comment'
        elif char in "'\"`":
            quote=char;i+=1;closed=False
            while i<len(sql):
                if sql[i]=='\\' and quote!='`':
                    require(i+1<len(sql),'FORMAL_SCHEMA_DDL_INVALID');i+=2
                elif sql[i]==quote:
                    i+=1
                    if i<len(sql) and sql[i]==quote:i+=1
                    else:closed=True;break
                else:i+=1
            require(closed,'FORMAL_SCHEMA_DDL_INVALID')
            kind='identifier' if quote=='`' else 'literal'
        elif char.isalnum() or char=='_':
            i+=1
            while i<len(sql) and (sql[i].isalnum() or sql[i]=='_'):i+=1
            kind='word'
        else:i+=1;kind='symbol'
        tokens.append((kind,sql[start:i],start,i))
    return tokens


def _catalog_bound_table_ddl(sql,columns):
    tokens=_ddl_tokens(sql)
    require(len(tokens)>=6 and tokens[0][1]=='CREATE' and tokens[1][1]=='TABLE' and
        tokens[2][0]=='identifier' and tokens[3][1]=='(','FORMAL_SCHEMA_DDL_INVALID')
    depth=0;segments=[];start=4;closed=False
    for i in range(3,len(tokens)):
        kind,text,_,_=tokens[i]
        if kind!='symbol':continue
        if text=='(':depth+=1
        elif text==')':
            depth-=1;require(depth>=0,'FORMAL_SCHEMA_DDL_INVALID')
            if depth==0:
                segments.append(tokens[start:i]);closed=True;break
        elif text==',' and depth==1:segments.append(tokens[start:i]);start=i+1
    require(closed,'FORMAL_SCHEMA_DDL_INVALID')
    seen=[];removals=[]
    for segment in segments:
        require(segment,'FORMAL_SCHEMA_DDL_INVALID')
        if segment[0][0]!='identifier':continue
        name=segment[0][1][1:-1].replace('``','`')
        require(name in columns and name not in seen,'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
        seen.append(name);column=columns[name];nested=0
        for i,token in enumerate(segment[1:],1):
            kind,text,left,_=token
            if kind=='symbol':
                if text=='(':nested+=1
                elif text==')':nested-=1
                require(nested>=0,'FORMAL_SCHEMA_DDL_INVALID');continue
            if nested or kind!='word':continue
            if text.upper() in ('DEFAULT','COMMENT','GENERATED','AS','CHECK','REFERENCES'):break
            if text=='CHARACTER' and i+4<len(segment):
                clause=segment[i:i+5]
                if all(t[0]=='word' for t in clause) and [t[1] for t in clause]==[
                    'CHARACTER','SET',column[5],'COLLATE',column[6]]:
                    require(column[5] is not None and column[6] is not None and
                        re.fullmatch('[a-z0-9_]+',column[5]) and re.fullmatch('[a-z0-9_]+',column[6]),
                        'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
                    removals.append((left,clause[3][2]))
    require(seen==list(columns),'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
    for left,right in reversed(removals):sql=sql[:left]+sql[right:]
    return sql


def _canonical_schema_body(value):
    # MySQL8 persists an explicit-collation flag outside information_schema.
    # Replaying SHOW CREATE can change that flag while preserving the column.
    # Raw observations stay untouched and individually hashed. Only a real
    # column's exact catalog-proven redundant charset clause is canonicalized.
    body={k:v for k,v in value.items() if k not in ('schemaSha256','observationIdentity','observationSha256')}
    catalog=body['catalog'];definitions=body['definitions'];columns=catalog['COLUMNS']
    require(type(columns) is list and all(type(c) is list and len(c)==11 for c in columns),
        'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
    tables={}
    for name,kind in catalog['TABLES']:
        if kind!='BASE TABLE':continue
        selected=[c for c in columns if c[0]==name]
        require(selected and len({c[1] for c in selected})==len(selected) and
            all(type(c[1]) is str and c[2]==str(i+1) for i,c in enumerate(selected)),
            'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
        require(name in definitions['TABLE'] and type(definitions['TABLE'][name]) is list and
            len(definitions['TABLE'][name])==2 and definitions['TABLE'][name][0]==name,
            'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
        tables[name]=[name,_catalog_bound_table_ddl(definitions['TABLE'][name][1],{c[1]:c for c in selected})]
    require(set(tables)==set(definitions['TABLE']),'FORMAL_SCHEMA_COLUMN_BINDING_INVALID')
    return dict(body,definitions=dict(definitions,TABLE=tables))


def compare_schema(source,target):
    for value in (source,target):
        require(type(value) is dict and type(value.get('schemaSha256')) is str,'FORMAL_SCHEMA_PROOF_CHANGED')
        require(hashlib.sha256(_canonical_bytes({k:v for k,v in value.items() if k!='observationSha256'})).hexdigest()==
                value.get('observationSha256'),'FORMAL_SCHEMA_PROOF_CHANGED')
        identity=value.get('observationIdentity')
        require(type(identity) is dict and set(identity)=={'containerId','databaseUuid'} and
            type(identity['containerId']) is str and re.fullmatch('[0-9a-f]{64}',identity['containerId']) and
            type(identity['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',identity['databaseUuid']),
            'FORMAL_SCHEMA_PROOF_IDENTITY_INVALID')
        body={k:v for k,v in value.items() if k not in ('schemaSha256','observationIdentity','observationSha256')}
        require(hashlib.sha256(_canonical_bytes(body)).hexdigest()==value['schemaSha256'], 'FORMAL_SCHEMA_PROOF_CHANGED')
    require(source['catalog']==target['catalog'],'FORMAL_SCHEMA_MISMATCH')
    source_body=_canonical_schema_body(source);target_body=_canonical_schema_body(target)
    require(source_body==target_body,'FORMAL_SCHEMA_MISMATCH')
    return {'state':'SCHEMA_EQUAL_PENDING_FULL_DATA_AND_APPLICATION_PROOF',
        'schemaSha256':source['schemaSha256'],'objectCounts':source['objectCounts'],
        'comparisonEncoding':'mysql8-catalog-bound-ddl/v1',
        'sourceSchemaSha256':source['schemaSha256'],'targetSchemaSha256':target['schemaSha256'],
        'canonicalSchemaSha256':hashlib.sha256(_canonical_bytes(source_body)).hexdigest(),
        'sourceIdentity':source['observationIdentity'],'targetIdentity':target['observationIdentity'],
        'sourceObservationSha256':source['observationSha256'],'targetObservationSha256':target['observationSha256'],
        'fullDataEquivalenceVerified':False,'productionEvidence':False}
