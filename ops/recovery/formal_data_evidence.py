"""Full typed row multisets for the observed MySQL 8.0 source type inventory.

Every occurrence is retained. Nested JSON includes native type and path tokens.
SQL/raw values never leave the private client; hashes use bounded disk streams.
Caller exclusion is mandatory throughout, and remains the runner's obligation.
"""
import hashlib
import heapq
import math
import os
from pathlib import Path
import re
import shutil
import time

from formal_schema_evidence import SchemaMySql, _bounded_process, identifier, observe_schema, compare_schema
from formal_snapshot_linux import require, _canonical_bytes, FormalSnapshotError, observation_deadline

SHA = re.compile('[0-9a-f]{64}')
UUID = re.compile('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}')
ENCODING = 'mysql8-typed-row-multiset-sha256/v1'
SCOPED_ENCODING = 'mysql8-affected-table-row-multiset-sha256/v1'


def validate_limits(value):
    require(type(value) is dict and set(value)=={'max_rows','max_nodes','max_bytes','seconds'} and
        all(type(v) is int for v in value.values()) and
        0<value['max_rows']<=10000000 and 0<value['max_nodes']<=100000000 and
        0<value['max_bytes']<=16*1024**3 and 0<value['seconds']<=7200,
        'FORMAL_DATA_LIMITS_REQUIRED')
    return dict(value)


def source_binding(claim_raw, before, after, sql_sha):
    """Bind observations to the exact owning claim and captured SQL bytes."""
    from formal_s3_export import _strict_json
    claim=_strict_json(claim_raw)
    compare_data(before,after)
    require(before==after and type(claim) is dict and
        type(claim.get('operationId')) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',claim['operationId']) and
        type(claim.get('sourceFingerprint')) is str and SHA.fullmatch(claim['sourceFingerprint']) and
        before['observationIdentity']['databaseUuid']==claim.get('databaseUuid') and
        type(sql_sha) is str and SHA.fullmatch(sql_sha),'FORMAL_DATA_SOURCE_CHANGED')
    return {'schemaVersion':'release-formal-source-data/v1','operationId':claim['operationId'],
        'claimBindingSha256':hashlib.sha256(claim_raw).hexdigest(),
        'sourceFingerprint':claim['sourceFingerprint'],'databaseUuid':claim['databaseUuid'],
        'mysqlContainerId':before['observationIdentity']['containerId'],
        'database':before['schema']['database'],'sqlSha256':sql_sha,
        'sourceBeforeFileSha256':hashlib.sha256(_canonical_bytes(before)).hexdigest(),
        'sourceAfterFileSha256':hashlib.sha256(_canonical_bytes(after)).hexdigest(),
        'sourceObservationSha256':before['observationSha256'],'schemaSha256':before['schema']['schemaSha256']}


def read_source_data(root, claim_raw, sql_sha, reference):
    """Validate retained source bytes; callers recheck before/after each mutation."""
    from formal_capture_producer import read_private
    from formal_s3_export import _strict_json
    names=('011-source-data.json','012-source-data-after.json','015-source-data-binding.json')
    try:
        raw=[read_private(Path(root)/name,64*1024*1024 if i<2 else 16384) for i,name in enumerate(names)]
        before,after,binding=(_strict_json(value) for value in raw)
        expected=source_binding(claim_raw,before,after,sql_sha)
        require(binding==expected and raw==[_canonical_bytes(v) for v in (before,after,binding)] and
            reference=={'bindingSha256':hashlib.sha256(raw[2]).hexdigest(),
                        'sourceObservationSha256':before['observationSha256']},'FORMAL_DATA_SOURCE_CHANGED')
        return before,dict(zip(names,raw))
    except (FormalSnapshotError,OSError,KeyError,TypeError,ValueError):
        raise FormalSnapshotError('FORMAL_DATA_SOURCE_CHANGED') from None


def _cell(column):
    name=identifier(column[1]);kind=column[3]
    if kind in ('tinyint','smallint','int','bigint','decimal','date','datetime','timestamp','time'):
        value='CAST('+name+' AS CHAR CHARACTER SET ascii)'
    elif kind=='bit':value='CAST(CAST('+name+' AS UNSIGNED) AS CHAR CHARACTER SET ascii)'
    elif kind=='double':
        # Casting to DOUBLE removes legacy DOUBLE(M,D) display rounding before dtoa.
        value='CAST(CAST('+name+' AS DOUBLE) AS CHAR CHARACTER SET ascii)'
    elif kind in ('varchar','text','mediumtext','longtext','blob','longblob'):
        value='CAST('+name+' AS BINARY)'
    elif kind=='enum':
        # Hash the label in a fixed charset, never the ENUM internal index.
        value='CAST(CAST('+name+' AS CHAR CHARACTER SET utf8mb4) AS BINARY)'
    elif kind=='binary':
        length=re.fullmatch(r'binary\(([1-9][0-9]*)\)',column[4])
        require(length is not None,'FORMAL_DATA_TYPE_UNSUPPORTED')
        value='CAST('+name+' AS BINARY('+length[1]+'))'
    elif kind=='char':
        length=re.fullmatch(r'char\(([1-9][0-9]*)\)',column[4])
        require(length is not None,'FORMAL_DATA_TYPE_UNSUPPORTED')
        value='CAST(RPAD('+name+','+length[1]+",' ') AS BINARY)"
    elif kind=='json':value='CAST('+name+' AS CHAR CHARACTER SET utf8mb4)'
    else:require(False,'FORMAL_DATA_TYPE_UNSUPPORTED')
    return "CAST(IF("+name+" IS NULL,'N',CONCAT('V',SHA2("+value+',256))) AS BINARY)'


def table_sql(table,columns):
    identifier(table)
    require(type(columns) is list and 0<len(columns)<=4096 and
        all(type(c) is list and len(c)==11 and c[0]==table and c[2]==str(i+1)
            for i,c in enumerate(columns)) and len({c[1] for c in columns})==len(columns),
        'FORMAL_DATA_COLUMNS_INVALID')
    cells=[_cell(c) for c in columns]
    row_hash="SHA2(CONCAT('row/v1:',"+','.join(cells)+'),256)'
    json_columns=[(i+1,c) for i,c in enumerate(columns) if c[3]=='json']
    base='base AS (SELECT ROW_NUMBER() OVER () AS rid,'+row_hash+' AS token'
    for i,c in json_columns:base+=','+identifier(c[1])+' AS j'+str(i)
    base+=' FROM '+identifier(table)+')'
    if not json_columns:
        return 'WITH '+base+' SELECT rid,0,token FROM base ORDER BY rid;'
    anchors=["SELECT rid,"+str(i)+" AS col,SHA2('root',256) AS path,j"+str(i)+
        ' AS doc FROM base WHERE j'+str(i)+' IS NOT NULL' for i,_ in json_columns]
    key="JSON_EXTRACT(JSON_KEYS(n.doc),CONCAT('$[',jt.ord-1,']'))"
    suffix="IF(JSON_TYPE(n.doc)='ARRAY',CONCAT('[',jt.ord-1,']'),CONCAT('.',"+key+'))'
    component="IF(JSON_TYPE(n.doc)='ARRAY',CONCAT('A',jt.ord-1),CONCAT('O',HEX(JSON_UNQUOTE("+key+'))))'
    nodes='nodes(rid,col,path,doc) AS ('+' UNION ALL '.join(anchors)+\
        ' UNION ALL SELECT n.rid,n.col,SHA2(CONCAT(CAST(n.path AS BINARY),\':\','+component+'),256),'+\
        "JSON_EXTRACT(n.doc,CONCAT('$',"+suffix+')) FROM nodes n JOIN JSON_TABLE('+\
        "CASE JSON_TYPE(n.doc) WHEN 'OBJECT' THEN JSON_KEYS(n.doc) WHEN 'ARRAY' THEN n.doc "+\
        "ELSE JSON_ARRAY() END,'$[*]' COLUMNS(ord FOR ORDINALITY)) jt)"
    node="SHA2(CONCAT(CAST(n.path AS BINARY),':',JSON_TYPE(n.doc),':',IF(JSON_TYPE(n.doc) IN ('OBJECT','ARRAY'),"+\
        'CAST(JSON_LENGTH(n.doc) AS CHAR CHARACTER SET ascii),HEX(CAST(n.doc AS CHAR CHARACTER SET utf8mb4)))),256)'
    node="CASE WHEN JSON_TYPE(n.doc) IN ('OBJECT','ARRAY','NULL','STRING','BOOLEAN','INTEGER','DOUBLE',"+\
        "'UNSIGNED INTEGER','DECIMAL','DATE','TIME','DATETIME') THEN "+node+" ELSE CONCAT('UNSUPPORTED:',JSON_TYPE(n.doc)) END"
    return 'WITH RECURSIVE '+base+','+nodes+' SELECT rid,col,token FROM ('+\
        'SELECT rid,0 AS col,token FROM base UNION ALL SELECT rid,col,'+node+\
        ' AS token FROM nodes n) tokens ORDER BY rid,col,CAST(token AS BINARY);'


def summarize_tokens(path,expected_uuid,scratch,*,max_rows,max_nodes,chunk_rows=65536,deadline=None):
    """Bounded external sort of every complete row digest, including duplicates."""
    require(type(expected_uuid) is str and UUID.fullmatch(expected_uuid),'FORMAL_DATA_TRANSPORT_INVALID')
    require(all(type(v) is int and v>=0 for v in (max_rows,max_nodes)) and type(chunk_rows) is int and chunk_rows>0 and
        chunk_rows<=65536 and max_rows<=10000000 and max_nodes<=100000000,'FORMAL_DATA_LIMIT')
    def check_time():
        require(deadline is None or time.monotonic()<deadline,'FORMAL_DATA_DEADLINE')
    check_time()
    chunks=[];pending=[];rows=0;nodes=0;current=None;last_key=None
    def spill():
        check_time()
        target=Path(scratch)/('rows-'+str(len(chunks))+'.bin')
        require(len(chunks)<256,'FORMAL_DATA_LIMIT')
        from formal_capture_budget import active_budget
        budget=active_budget.get()
        with (target.open('xb') if budget is None else budget.open(target,'scratch')) as out:
            os.chmod(target,0o600)
            for token in sorted(pending):out.write(token)
            out.flush();os.fsync(out.fileno())
        check_time()
        chunks.append(target);pending.clear()
    def finish():
        if current is not None:
            pending.append(current.digest())
            if len(pending)>=chunk_rows:spill()
    with Path(path).open('rb') as stream:
        require(stream.readline(128)==(expected_uuid+'\n').encode(),'FORMAL_DATA_TRANSPORT_INVALID')
        while True:
            check_time()
            line=stream.readline(160)
            require(line and line.endswith(b'\n') and len(line)<160,'FORMAL_DATA_TRANSPORT_INVALID')
            if b'\t' not in line:
                require(line==b'0\n' and stream.readline(128)==(expected_uuid+'\n').encode() and not stream.read(1),
                        'FORMAL_DATA_TRANSPORT_INVALID')
                break
            parts=line[:-1].split(b'\t')
            require(not (len(parts)==3 and parts[2].startswith(b'UNSUPPORTED:')),
                    'FORMAL_DATA_JSON_TYPE_UNSUPPORTED')
            require(len(parts)==3 and re.fullmatch(b'[1-9][0-9]{0,9}',parts[0]) and
                re.fullmatch(b'0|[1-9][0-9]{0,3}',parts[1]) and re.fullmatch(b'[0-9a-f]{64}',parts[2]),
                'FORMAL_DATA_TOKEN_INVALID')
            rid,col=int(parts[0]),int(parts[1]);token=parts[2]
            if col==0:
                require(rid==rows+1,'FORMAL_DATA_TOKEN_INVALID')
                finish();rows+=1
                require(rows<=max_rows,'FORMAL_DATA_LIMIT')
                current=hashlib.sha256(b'complete-row/v1:'+token+b'\n');last_key=(0,token)
            else:
                require(current is not None and rid==rows and (col,token)>=last_key,'FORMAL_DATA_TOKEN_INVALID')
                nodes+=1;require(nodes<=max_nodes,'FORMAL_DATA_LIMIT')
                current.update(str(col).encode()+b':'+token+b'\n');last_key=(col,token)
    finish()
    if pending:spill()
    readers=[]
    try:
        for chunk in chunks:readers.append(chunk.open('rb'))
        def records(stream):
            while True:
                check_time()
                value=stream.read(32)
                if not value:break
                require(len(value)==32,'FORMAL_DATA_SORT_CHANGED');yield value
        checksum=hashlib.sha256(b'row-multiset/v1\n');count=0
        for value in heapq.merge(*(records(reader) for reader in readers)):
            check_time()
            count+=1;checksum.update(value)
        require(count==rows,'FORMAL_DATA_SORT_CHANGED')
    finally:
        for reader in readers:reader.close()
    return {'rows':rows,'jsonNodes':nodes,'multisetSha256':checksum.hexdigest()}


class DataMySql(SchemaMySql):
    def data_query_to_file(self,sql,*,database,expected_uuid,path,max_bytes):
        from formal_capture_budget import active_budget,drain_owned_process
        import subprocess
        output_budget=active_budget.get()
        require(type(sql) is str and 0<len(sql.encode())<=1024*1024 and '\0' not in sql and
            type(expected_uuid) is str and UUID.fullmatch(expected_uuid) and
            type(max_bytes) is int and 0<max_bytes<=16*1024**3,'FORMAL_DATA_INPUT_INVALID')
        wrapped='USE '+identifier(database)+"; SET SESSION time_zone='+00:00'; "+\
            'SET SESSION cte_max_recursion_depth=101; SELECT @@server_uuid;\n'+sql+\
            '\nSELECT @@warning_count; SELECT @@server_uuid;\n'
        seconds=self.query_seconds()
        command=self._command('timeout --signal=TERM --kill-after=5 '+str(math.ceil(seconds))+'s mysql',
            ['-uroot','--batch','--skip-column-names','--default-character-set=utf8mb4','--quick'])
        with (Path(path).open('xb') if output_budget is None else output_budget.open(path,'scratch')) as sink:
            os.chmod(path,0o600)
            if output_budget is None:
                _bounded_process(command,(self._password+'\n'+wrapped).encode(),max_bytes,seconds,sink=sink)
            else:
                class QueryLimit:
                    total=0
                    def write(self,chunk):
                        require(self.total+len(chunk)<=max_bytes,'FORMAL_DATA_STREAM_LIMIT')
                        sink.write(chunk);self.total+=len(chunk)
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                drain_owned_process(process,(self._password+'\n'+wrapped).encode(),QueryLimit(),
                    guard=output_budget.check,deadline=min(output_budget.deadline,time.monotonic()+seconds))
            sink.flush();os.fsync(sink.fileno())


def observe_data(mysql,database,expected_uuid,*,guard,scratch,max_rows,max_nodes,max_bytes,seconds):
    return _observe(mysql,database,expected_uuid,guard=guard,scratch=scratch,max_rows=max_rows,
        max_nodes=max_nodes,max_bytes=max_bytes,seconds=seconds,affected_tables=None)


def observe_affected_data(mysql,database,expected_uuid,*,affected_tables,guard,scratch,
                          max_rows,max_nodes,max_bytes,seconds,lower_case_table_names=0):
    require(type(affected_tables) is list and affected_tables == sorted(set(affected_tables)) and
        all(type(t) is str and (t == '*' or re.fullmatch(r'[A-Za-z0-9_$-]{1,64}', t)) for t in affected_tables),
        'FORMAL_DATA_AFFECTED_TABLES_INVALID')
    return _observe(mysql,database,expected_uuid,guard=guard,scratch=scratch,max_rows=max_rows,
        max_nodes=max_nodes,max_bytes=max_bytes,seconds=seconds,affected_tables=affected_tables,lower_case_table_names=lower_case_table_names)


def affected_table_scope(schema, changed):
    if '*' in changed:
        return sorted(name for name, kind in schema['catalog']['TABLES'] if kind != 'VIEW')
    # Include FK dependants: InnoDB cascades need not have their own ROW events.
    # Reading definitions is metadata-only; rows of unrelated tables are never read.
    from formal_schema_evidence import _ddl_tokens
    selected=set(changed)
    references={}
    for table, definition in schema['definitions']['TABLE'].items():
        tokens=_ddl_tokens(definition[1]); parents=set()
        for i, token in enumerate(tokens):
            if token[0] != 'word' or token[1].upper() != 'REFERENCES': continue
            require(i+1 < len(tokens) and tokens[i+1][0] == 'identifier', 'FORMAL_DATA_FK_INVALID')
            name=tokens[i+1][1][1:-1].replace('``','`')
            if i+2 < len(tokens) and tokens[i+2][1] == '.':
                require(name == schema['database'] and i+3 < len(tokens) and
                    tokens[i+3][0] == 'identifier', 'FORMAL_DATA_FK_OUT_OF_SCOPE')
                name=tokens[i+3][1][1:-1].replace('``','`')
            parents.add(name)
        references[table]=parents
    while True:
        extended=selected | {table for table, parents in references.items() if parents & selected}
        if extended == selected: return sorted(selected)
        selected=extended


def incremental_observation_tables(expected, scope, capture, database):
    """Bind affected endpoint rows to the exact archived transaction range."""
    delta=capture['databaseDelta']
    require(capture['pointType'] == 'INCREMENTAL' and delta['kind'] == 'BINLOG_SQL' and
        delta['dataObservation'] == 'AFFECTED_TABLES_V1' and
        delta['logMode'] in ('GTID', 'FILE_POSITION') and
        (scope['schemaVersion'], scope['policy']) in (
            ('backup-binlog-event-scope/v2', 'MYSQL80_ROW_AND_SCOPED_TABLE_DDL'),
            ('backup-binlog-event-scope/v3', 'MYSQL80_ROW_AND_SCOPED_DATABASE_DDL')) and
        scope['databaseScope'] == [database] and scope['logMode'] == delta['logMode'] and
        scope['parentPosition'] == delta['parentPosition'] and
        scope['endPosition'] == capture['databaseEnd'] and
        scope['rawSqlPin'] == delta['rawPin'] and
        [s['segment'] for s in scope['segments']] == delta['segments'],
        'FORMAL_DATA_BINLOG_BINDING_INVALID')
    for segment in scope['segments']:
        tables=segment['affectedTables']
        require(type(tables) is list and all(type(t) is str and
            (t == '*' and scope['schemaVersion'] == 'backup-binlog-event-scope/v3' or
             re.fullmatch(r'[A-Za-z0-9_$-]{1,64}', t)) for t in tables) and
            tables == sorted(set(tables)) and
            all(type(segment[k]) is int and segment[k] >= 0 for k in
                ('eventCount', 'rowEventCount', 'ddlEventCount')) and
            bool(tables) == bool(segment['rowEventCount']+segment['ddlEventCount']),
            'FORMAL_DATA_BINLOG_SCOPE_INVALID')
    changed=sorted({t for segment in scope['segments'] for t in segment['affectedTables']})
    case=delta['lowerCaseTableNames']
    require(type(case) is int and case in (0, 1, 2), 'FORMAL_DATA_CASE_INVALID')
    if case:
        names={name.lower():name for name, _ in expected['schema']['catalog']['TABLES']}
        changed=sorted({names.get(t.lower(),t.lower()) for t in changed})
    require(expected['encoding'] == SCOPED_ENCODING and expected['schema']['database'] == database and
        expected['observationIdentity']['databaseUuid'] == capture['databaseEnd']['databaseUuid'] and
        expected['affectedTables'] == affected_table_scope(expected['schema'],changed),
        'FORMAL_DATA_BINLOG_SCOPE_MISMATCH')
    compare_data(expected,expected)
    return changed


def _observe(mysql,database,expected_uuid,*,guard,scratch,max_rows,max_nodes,max_bytes,seconds,affected_tables,lower_case_table_names=0):
    require(callable(guard),'FORMAL_DATA_GUARD_REQUIRED')
    require(type(max_bytes) is int and 0<max_bytes<=16*1024**3 and
        type(seconds) is int and 0<seconds<=7200 and
        type(max_rows) is int and 0<max_rows<=10000000 and
        type(max_nodes) is int and 0<max_nodes<=100000000 and
        getattr(mysql,'deadline',None) is None,'FORMAL_DATA_INPUT_INVALID')
    deadline=time.monotonic()+seconds
    outer=observation_deadline.get()
    if outer is not None:deadline=min(deadline,outer)
    require(time.monotonic()<deadline,'FORMAL_DATA_DEADLINE')
    def bounded_guard():
        require(time.monotonic()<deadline,'FORMAL_DATA_DEADLINE');guard()
        require(time.monotonic()<deadline,'FORMAL_DATA_DEADLINE')
    mysql.deadline=deadline
    token=observation_deadline.set(deadline)
    try:
        return _observe_data(mysql,database,expected_uuid,guard=bounded_guard,scratch=scratch,
            max_rows=max_rows,max_nodes=max_nodes,max_bytes=max_bytes,deadline=deadline,affected_tables=affected_tables,lower_case_table_names=lower_case_table_names)
    finally:
        observation_deadline.reset(token)
        mysql.deadline=None


def _observe_data(mysql,database,expected_uuid,*,guard,scratch,max_rows,max_nodes,max_bytes,deadline,affected_tables,lower_case_table_names=0):
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    guard()
    root=Path(scratch).absolute()
    require(not root.exists() and not root.is_symlink() and root.parent.is_dir() and
        root.parent.resolve()==root.parent,'FORMAL_DATA_SCRATCH_INVALID')
    # Stream plus fixed-size external-sort files; full reservation belongs to runner preflight.
    require(shutil.disk_usage(root.parent).free>=max_bytes+max_rows*32,'FORMAL_DATA_SPACE_REQUIRED')
    if output_budget is None:root.mkdir(mode=0o700)
    else:output_budget.mkdir(root)
    before=observe_schema(mysql,database,expected_uuid,guard=guard)
    if affected_tables is not None and lower_case_table_names:
        names={name.lower():name for name, _ in before['catalog']['TABLES']}
        affected_tables=sorted({names.get(t.lower(),t.lower()) for t in affected_tables})
    selected=None if affected_tables is None else affected_table_scope(before,affected_tables)
    tables={};total_bytes=0;total_rows=0;total_nodes=0
    for index,(table,kind) in enumerate(before['catalog']['TABLES']):
        if kind=='VIEW' or selected is not None and table not in selected:continue
        columns=[c for c in before['catalog']['COLUMNS'] if c[0]==table]
        sql=table_sql(table,columns)
        part=root/str(index)
        if output_budget is None:part.mkdir(mode=0o700)
        else:output_budget.mkdir(part)
        path=part/'tokens.tsv'
        guard()
        mysql.data_query_to_file(sql,database=database,expected_uuid=expected_uuid,path=path,
                                max_bytes=max_bytes-total_bytes)
        guard();total_bytes+=path.stat().st_size
        tables[table]=summarize_tokens(path,expected_uuid,part,max_rows=max_rows-total_rows,
                                      max_nodes=max_nodes-total_nodes,deadline=deadline)
        total_rows+=tables[table]['rows'];total_nodes+=tables[table]['jsonNodes']
        guard()
        count=mysql.schema_query('SELECT COUNT(*) FROM '+identifier(table)+';',database=database,
                                 expected_uuid=expected_uuid)
        guard()
        require(count==[[str(tables[table]['rows'])]],'FORMAL_DATA_ROW_COUNT_CHANGED')
    after=observe_schema(mysql,database,expected_uuid,guard=guard)
    require(after==before,'FORMAL_DATA_SCHEMA_CHANGED')
    result={'encoding':ENCODING,'schema':before,'tables':tables,'observationIdentity':before['observationIdentity'],
        'applicationVerified':False,'productionEvidence':False}
    if selected is not None:
        result.update(encoding=SCOPED_ENCODING,affectedTables=selected)
    result['observationSha256']=hashlib.sha256(_canonical_bytes(result)).hexdigest()
    return result


def compare_data(source,target):
    scoped=source.get('encoding') == SCOPED_ENCODING
    require(target.get('encoding') == source.get('encoding'),'FORMAL_DATA_SCOPE_MISMATCH')
    for proof in (source,target):
        require(type(proof) is dict and set(proof)=={'encoding','schema','tables','observationIdentity',
            'applicationVerified','productionEvidence','observationSha256'} | ({'affectedTables'} if scoped else set()) and proof['encoding']==(SCOPED_ENCODING if scoped else ENCODING) and
            proof['applicationVerified'] is False and proof['productionEvidence'] is False and
            hashlib.sha256(_canonical_bytes({k:v for k,v in proof.items() if k!='observationSha256'})).hexdigest()==
            proof['observationSha256'],'FORMAL_DATA_PROOF_CHANGED')
        require(proof['observationIdentity']==proof['schema']['observationIdentity'] and
            type(proof['tables']) is dict and set(proof['tables'])==
            {r[0] for r in proof['schema']['catalog']['TABLES'] if r[1]=='BASE TABLE' and
             (not scoped or r[0] in proof['affectedTables'])},'FORMAL_DATA_PROOF_INVALID')
        for table in proof['tables'].values():
            require(type(table) is dict and set(table)=={'rows','jsonNodes','multisetSha256'} and
                type(table['rows']) is int and table['rows']>=0 and type(table['jsonNodes']) is int and
                table['jsonNodes']>=0 and type(table['multisetSha256']) is str and SHA.fullmatch(table['multisetSha256']),
                'FORMAL_DATA_PROOF_INVALID')
    if scoped:
        require(source['affectedTables'] == target['affectedTables'] and
            source['affectedTables'] == sorted(set(source['affectedTables'])), 'FORMAL_DATA_SCOPE_MISMATCH')
    schema=compare_schema(source['schema'],target['schema'])
    require(source['tables']==target['tables'],'FORMAL_DATA_MISMATCH')
    return {'state':('SCHEMA_AFFECTED_DATA_EQUAL_PENDING_APPLICATION_PROOF' if scoped else
                 'SCHEMA_DATA_EQUAL_PENDING_APPLICATION_PROOF'),'encoding':source['encoding'],
        'schemaSha256':schema['schemaSha256'],'tables':source['tables'],
        'schemaComparisonEncoding':schema['comparisonEncoding'],
        'sourceSchemaSha256':schema['sourceSchemaSha256'],'targetSchemaSha256':schema['targetSchemaSha256'],
        'canonicalSchemaSha256':schema['canonicalSchemaSha256'],
        'sourceIdentity':source['observationIdentity'],'targetIdentity':target['observationIdentity'],
        'sourceObservationSha256':source['observationSha256'],'targetObservationSha256':target['observationSha256'],
        'fullSchemaDataEquivalenceVerified':not scoped,'applicationVerified':False,'productionEvidence':False}
