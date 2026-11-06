"""Inspect actual MySQL 8.0 ROW events before exporting executable binlog SQL.

SHOW BINLOG EVENTS is read in bounded pages over the exact retained positions.
No event is filtered or skipped. Only bounded table/column/index DDL in the
registered database is accepted alongside ROW transactions. Account/privilege
SQL and unknown events remain refused. Current tables are not scope evidence.
"""
import hashlib
import math
import re
import time

import formal_snapshot_linux as snapshot


def require(value, code='FORMAL_CAPTURE_BINLOG_SCOPE_UNPROVEN'):
    snapshot.require(value, code)


def scoped_database_ddl(sql, database):
    """A reset changes every table, but may only name the registered database."""
    identifier = r'(?:`([A-Za-z0-9_-]+)`|([A-Za-z_][A-Za-z0-9_-]*))'
    match = re.fullmatch(r'(?:CREATE|DROP|ALTER)\s+DATABASE\s+'+identifier+r'(.*)', sql, re.I | re.S)
    if match is None:
        return False
    require((match[1] or match[2]) == database, 'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
    action = sql.split(None, 1)[0].upper()
    options = match[3]
    option = (r'(?:(?:DEFAULT\s+)?CHARACTER\s+SET\s*(?:=\s*)?[A-Za-z0-9_]+'
              r'|(?:DEFAULT\s+)?COLLATE\s*(?:=\s*)?[A-Za-z0-9_]+'
              r"|DEFAULT\s+ENCRYPTION\s*=\s*'[YN]')")
    require((not options.strip()) if action == 'DROP' else
            re.fullmatch(r'(?:\s+'+option+r')*\s*', options, re.I) is not None,
            'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN')
    return True


def mask_sql_literals(sql):
    """Ignore literal contents for lexical checks, retaining every SQL boundary."""
    require('\\' not in sql, 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN')
    result = []; offset = 0
    literal = re.compile(r"'(?:[^']|'')*'")
    for match in literal.finditer(sql):
        result.extend((sql[offset:match.start()], "''")); offset = match.end()
    result.append(sql[offset:])
    masked = ''.join(result)
    require("'" not in masked.replace("''", ''), 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN')
    return masked


def local_table_expression(expression, *, aliases=(), variables=(), functions=()):
    """Scope proof for server-produced CHECK/generated expressions.

    Only local quoted columns, constants, operators and named pure MySQL
    builtins are accepted. No qualified names, user functions, variables,
    subqueries or executable comments can pass this token allowlist.
    MySQL has already parsed the original statement in the retained binlog.
    """
    code = 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN'
    text = mask_sql_literals(expression)
    identifier=r'(?:`[A-Za-z0-9_$-]+`|[A-Za-z_][A-Za-z0-9_$]*)'
    for alias in aliases:
        text=re.sub(r'\b'+re.escape(alias)+rf'\s*\.\s*({identifier})',
                    lambda m:'`'+m[1].strip('`')+'`',text,flags=re.I)
    for variable in variables:
        text=re.sub(r'\b'+re.escape(variable)+r'\b','`'+variable+'`',text,flags=re.I)
    token = re.compile(r"\s+|''|`[A-Za-z0-9_$-]+`|0x[0-9a-f]+|\d+(?:\.\d+)?|"
                       r"[A-Za-z_][A-Za-z0-9_]*|<=>|<>|!=|<=|>=|[(),=<>+*/%-]", re.I)
    tokens=[];cursor=0
    for match in token.finditer(text):
        require(match.start()==cursor,code);cursor=match.end()
        if not match[0].isspace():tokens.append(match[0])
    require(cursor==len(text) and bool(tokens),code)
    functions=set(functions)|{'regexp_like','char_length','trim','json_valid','json_type','json_length',
               'concat_ws','concat','convert','left','coalesce','cast','json_unquote',
               'json_extract','if'}
    keywords={'case','when','then','else','end','null','true','false','and','or',
              'not','in','is','between','like','as','using','binary','char','signed','unsigned','charset','utf8mb4','utf8mb3'}
    depth=0
    for index,value in enumerate(tokens):
        if value.startswith('`'):
            require(index+1==len(tokens) or tokens[index+1]!='(',code)
        if value=='(':depth+=1
        elif value==')':depth-=1;require(depth>=0,code)
        elif re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',value):
            name=value.lower();following=tokens[index+1] if index+1<len(tokens) else None
            if name in functions:require(following=='(',code)
            else:
                require(name in keywords or name in {'_utf8mb4','_utf8mb3','_ascii','_binary','b'} and following=="''",code)
                # Charset/type names are operands in CAST, never arbitrary
                # callable identifiers. CHAR/BINARY are bounded builtins;
                # the other names below introduce SQL expression groups.
                if following=='(':
                    require(name in {'char','binary','case','when','then','else',
                                     'and','or','not','in','is','between','as'},code)
    require(depth==0,code)


def scoped_table_ddl(sql, database, default_database):
    """Recognize a deliberately bounded DDL grammar, not arbitrary SQL.

    CREATE-AS/LIKE, cross-database references, partitions, routines, external
    storage, executable comments and multiple statements remain refused.
    CHECK/generated expressions use a separate local builtin token allowlist.
    Every table target must resolve to the originally registered database.
    """
    code = 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN'
    # mysqldump emits only this exact executable wrapper for index rebuilds.
    keys = re.fullmatch(r'/\*!40000 (ALTER TABLE .+ (?:DISABLE|ENABLE) KEYS) \*/', sql, re.I)
    if keys is not None:
        sql = keys[1]
    require(not any(x in mask_sql_literals(sql) for x in (';', '/*', '--', '#', '"')), code)
    ident = r'(?:`[A-Za-z0-9_$-]+`|[A-Za-z_][A-Za-z0-9_$]*)'
    table = rf'({ident})(?:\s*\.\s*({ident}))?'
    column_type = (r'(?:TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT|'
                   r'CHAR|VARCHAR|BINARY|VARBINARY|DECIMAL|NUMERIC|FLOAT|DOUBLE|'
                   r'DATE|DATETIME|TIMESTAMP|TIME|YEAR|TEXT|TINYTEXT|MEDIUMTEXT|'
                   r'LONGTEXT|BLOB|TINYBLOB|MEDIUMBLOB|LONGBLOB|JSON|BOOLEAN|BOOL|BIT)'
                   r'(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?')
    literal = r"(?:NULL|[+-]?\d+(?:\.\d+)?|[bB]'[01]+'|'(?:[^'\\]|'')*'|CURRENT_TIMESTAMP(?:\(\d*\))?|\(json_object\(\)\))"
    definition = (rf'{ident}\s+{column_type}'
                  rf'(?:\s+(?:UNSIGNED|ZEROFILL|NOT\s+NULL|NULL|AUTO_INCREMENT|'
                  rf'PRIMARY\s+KEY|UNIQUE(?:\s+KEY)?|DEFAULT\s+{literal}|'
                  rf'COMMENT\s+\'(?:[^\'\\]|\'\')*\'|'
                  rf'ON\s+UPDATE\s+CURRENT_TIMESTAMP(?:\(\d*\))?|'
                  rf'CHARACTER\s+SET\s+{ident}|COLLATE\s+{ident}))*')
    columns = rf'\(\s*{ident}(?:\s*\(\d+\))?(?:\s+(?:ASC|DESC))?(?:\s*,\s*{ident}(?:\s*\(\d+\))?(?:\s+(?:ASC|DESC))?)*\s*\)'
    index = (rf'(?:(?:UNIQUE\s+)?(?:INDEX|KEY)(?:\s+{ident})?|PRIMARY\s+KEY)\s*{columns}'
             rf"(?:\s+USING\s+BTREE)?(?:\s+COMMENT\s+'(?:[^'\\]|'')*')?")
    foreign_columns = rf'\(\s*{ident}(?:\s*,\s*{ident})*\s*\)'
    referential_action = r'(?:CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION)'
    on_delete = rf'ON\s+DELETE\s+{referential_action}'
    on_update = rf'ON\s+UPDATE\s+{referential_action}'
    # Each action may appear once, in either MySQL order. The referenced
    # database is still checked independently below, including CASCADE targets.
    foreign_actions = rf'(?:\s+(?:{on_delete}(?:\s+{on_update})?|{on_update}(?:\s+{on_delete})?))?'
    foreign_key = (rf'(?:CONSTRAINT(?:\s+{ident})?\s+)?FOREIGN\s+KEY(?:\s+{ident})?\s*'
                   rf'{foreign_columns}\s+REFERENCES\s+{table}\s*{foreign_columns}{foreign_actions}')

    def matches(pattern, value):
        return re.fullmatch(pattern, value.strip(), re.I | re.S) is not None

    def target(match):
        first, second = match[1].strip('`'), match[2]
        resolved = first if second else default_database
        require(resolved == database, 'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
        return second.strip('`') if second else first

    def parts(value):
        # Split only top-level commas, respecting literals and type/index sizes.
        pieces = []; start = depth = 0; quoted = False; i = 0
        while i < len(value):
            c = value[i]
            if c == "'":
                if quoted and i+1 < len(value) and value[i+1] == "'":
                    i += 2; continue
                quoted = not quoted
            elif not quoted:
                if c == '(': depth += 1
                elif c == ')': depth -= 1
                elif c == ',' and depth == 0:
                    pieces.append(value[start:i].strip()); start = i+1
                require(depth >= 0, code)
            i += 1
        require(not quoted and depth == 0, code)
        return pieces + [value[start:].strip()]

    match = re.fullmatch(rf'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{table}\s*\((.*)\)'
                         rf'(?:\s+(?:ENGINE\s*=?\s*InnoDB|AUTO_INCREMENT\s*=\s*[1-9][0-9]{{0,19}}|(?:DEFAULT\s+)?CHARSET\s*=?\s*{ident}|'
                         rf'(?:DEFAULT\s+)?CHARACTER\s+SET\s*=?\s*{ident}|COLLATE\s*=?\s*{ident}|'
                         rf'ROW_FORMAT\s*=\s*(?:DYNAMIC|COMPACT|REDUNDANT|COMPRESSED)|'
                         rf"COMMENT\s*=\s*'(?:[^'\\]|'')*'))*\s*", sql, re.I | re.S)
    if match:
        name = target(match)
        for part in parts(match[3]):
            if matches(rf'(?:{definition}|{index})', part):
                continue
            check=re.fullmatch(rf'(?:CONSTRAINT\s+{ident}\s+)?CHECK\s*\((.*)\)',part,re.I|re.S)
            generated=re.fullmatch(rf'({definition})\s+GENERATED\s+ALWAYS\s+AS\s*\((.*)\)\s+(?:STORED|VIRTUAL)'
                                   rf"(?:\s+COMMENT\s+'(?:[^'\\]|'')*')?",part,re.I|re.S)
            if check is not None or generated is not None:
                local_table_expression(check[1] if check else generated[2]);continue
            reference = re.fullmatch(foreign_key, part, re.I | re.S)
            require(reference is not None, code)
            # Unqualified REFERENCES resolves in the created table's database,
            # including CREATE TABLE db.name with no selected default database.
            referenced_database = reference[1].strip('`') if reference[2] else database
            require(referenced_database == database, 'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
        return name
    match = re.fullmatch(rf'ALTER\s+TABLE\s+{table}\s+(.+)', sql, re.I | re.S)
    if match:
        name = target(match)
        position = rf'(?:\s+(?:FIRST|AFTER\s+{ident}))?'
        action = (rf'(?:(?:ADD|MODIFY)\s+(?:COLUMN\s+)?{definition}{position}|'
                  rf'CHANGE\s+(?:COLUMN\s+)?{ident}\s+{definition}{position}|'
                  rf'RENAME\s+COLUMN\s+{ident}\s+TO\s+{ident}|'
                  rf'DROP\s+(?:COLUMN\s+)?{ident}|ADD\s+{index}|'
                  rf'DROP\s+(?:INDEX|KEY)\s+{ident}|DROP\s+PRIMARY\s+KEY|(?:DISABLE|ENABLE)\s+KEYS)')
        require(all(matches(action, p) for p in parts(match[3])), code)
        return name
    match = re.fullmatch(rf'CREATE\s+(?:UNIQUE\s+)?INDEX\s+{ident}\s+ON\s+{table}\s*{columns}', sql, re.I | re.S)
    if not match:
        match = re.fullmatch(rf'DROP\s+INDEX\s+{ident}\s+ON\s+{table}', sql, re.I | re.S)
    if not match:
        match = re.fullmatch(rf'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?{table}', sql, re.I | re.S)
    require(match is not None, code)
    return target(match)


def scoped_trigger_ddl(sql, database, default_database):
    """Bounded integrity triggers: local checks/reads and assignments to NEW.

    No table mutation statements, calls, dynamic SQL or session variables are
    allowed. Every SELECT/JOIN table is independently resolved to this database.
    """
    code='FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN'
    ident=r'(?:`[A-Za-z0-9_$-]+`|[A-Za-z_][A-Za-z0-9_$]*)'
    qualified=rf'{ident}(?:\s*\.\s*{ident})?'
    match=re.fullmatch(rf'CREATE\s+DEFINER=`root`@`localhost`\s+TRIGGER\s+({qualified})\s+'
                       rf'(?:BEFORE|AFTER)\s+(?:INSERT|UPDATE|DELETE)\s+ON\s+({qualified})\s+'
                       rf'FOR\s+EACH\s+ROW\s+BEGIN\s+(.*)\s+END',sql,re.I|re.S)
    require(match is not None,code)
    def local_name(value):
        pieces=re.split(r'\s*\.\s*',value)
        require((pieces[0].strip('`') if len(pieces)==2 else default_database)==database,
                'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
        return pieces[-1].strip('`')
    local_name(match[1]);target=local_name(match[2]);body=match[3]
    mask_sql_literals(body)
    masked=re.sub(r"'(?:[^']|'')*'",lambda m:"'"+' '*(len(m[0])-2)+"'",body)
    require(not any(v in masked for v in ('/*','--','#','"','@')),code)
    variables=set();cursor=0;conditions=0
    def expression(value,aliases=('OLD','NEW'),extra=()):
        local_table_expression(value,aliases=aliases,variables=variables,functions=extra)
    while cursor<len(body):
        whitespace=re.match(r'\s*',body[cursor:]);cursor+=whitespace.end()
        if cursor==len(body):break
        head=masked[cursor:]
        if re.match(r'IF\s',head,re.I):
            end=re.search(r'\bTHEN\b',head,re.I);require(end is not None,code)
            expression(body[cursor+2:cursor+end.start()]);conditions+=1;cursor+=end.end();continue
        end_if=re.match(r'END\s+IF\s*;',head,re.I)
        if end_if:
            require(conditions>0,code);conditions-=1;cursor+=end_if.end();continue
        alternative=re.match(r'ELSE\b',head,re.I)
        if alternative:require(conditions>0,code);cursor+=alternative.end();continue
        end=masked.find(';',cursor);require(end>=0,code)
        statement=body[cursor:end].strip();cursor=end+1
        declare=re.fullmatch(rf'DECLARE\s+({ident})\s+varchar\([1-9][0-9]*\)',statement,re.I)
        if declare:
            name=declare[1].strip('`');require(name not in variables,code);variables.add(name);continue
        signal=re.fullmatch(r"SIGNAL\s+SQLSTATE\s+'45000'\s+SET\s+MESSAGE_TEXT\s*=\s*'(?:[^']|'')*'",statement,re.I|re.S)
        if signal:continue
        assignment=re.fullmatch(rf'SET\s+NEW\.({ident})\s*=\s*(.+)',statement,re.I|re.S)
        if assignment:expression(assignment[2],extra={'uuid'});continue
        select=re.fullmatch(rf'SELECT\s+(.+?)\s+INTO\s+({ident})\s+FROM\s+({qualified})'
                            rf'(?:\s+(?:AS\s+)?({ident}))?'
                            rf'(?:\s+JOIN\s+({qualified})(?:\s+(?:AS\s+)?({ident}))?\s+ON\s+(.+?))?'
                            rf'\s+WHERE\s+(.+)',statement,re.I|re.S)
        require(select is not None and select[2].strip('`') in variables,code)
        first=local_name(select[3]);aliases=['OLD','NEW',first]
        if select[4]:aliases.append(select[4].strip('`'))
        if select[5]:
            aliases.append(local_name(select[5]))
            if select[6]:aliases.append(select[6].strip('`'))
            expression(select[7],aliases=aliases)
        # Bare projected columns are local to the explicitly checked FROM.
        projection=select[1]
        if re.fullmatch(ident,projection):projection='`'+projection.strip('`')+'`'
        expression(projection,aliases=aliases);expression(select[8],aliases=aliases)
    require(conditions==0,code)
    return target


class RowEventScope:
    def __init__(self, database, log_mode='GTID'):
        require(type(database) is str and
                re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', database))
        require(log_mode in ('GTID', 'FILE_POSITION'), 'FORMAL_CAPTURE_LOG_MODE_INVALID')
        self.database = database
        self.log_mode = log_mode
        self.tables = {}
        self.affected_tables = set()
        self.transaction = self.gtid = False
        self.row_count = self.event_count = self.ddl_count = 0

    def observe(self, event_type, info):
        require(type(info) is str and '\0' not in info)
        self.event_count += 1
        if event_type in {'Format_desc', 'Previous_gtids', 'Rotate', 'Stop'}:
            require(not self.transaction and not self.gtid)
        elif event_type in {'Gtid', 'Anonymous_Gtid'}:
            require(event_type == ('Gtid' if self.log_mode == 'GTID' else 'Anonymous_Gtid'),
                    'FORMAL_CAPTURE_BINLOG_LOG_MODE_CHANGED')
            require(not self.transaction and not self.gtid)
            self.gtid = True
        elif event_type == 'Query':
            # Query_log_event::pack_info prepends its original default DB.
            match = re.fullmatch(r'(?:use `([A-Za-z0-9_-]+)`; )?'
                                 r'(BEGIN|COMMIT|ROLLBACK)', info)
            if match is None:
                ddl = re.fullmatch(r'(?:use `([A-Za-z0-9_-]+)`; )?(.+)', info, re.S)
                require(ddl is not None, 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN')
                require(ddl[1] in (None, self.database),
                        'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
                # SHOW BINLOG EVENTS appends the atomic-DDL transaction ID.
                # Remove only that exact nonexecuting suffix, never SQL comments
                # in general. The original event is still hashed/exported whole.
                statement = re.sub(r' /\* xid=[0-9]+ \*/$', '', ddl[2])
                # MySQL adds this exact nonexecuting marker to DROP TABLE.
                # Validate the remaining complete statement with the same grammar.
                if re.match(r'DROP\s+TABLE\s', statement, re.I):
                    statement = re.sub(r' /\* generated by server \*/$', '', statement)
                if re.match(r'CREATE\s+DEFINER=',statement,re.I):
                    self.affected_tables.add(scoped_trigger_ddl(statement,self.database,ddl[1]))
                elif scoped_database_ddl(statement, self.database):
                    self.affected_tables.add('*')
                else:
                    self.affected_tables.add(scoped_table_ddl(statement, self.database, ddl[1]))
                require(self.gtid and not self.transaction)
                self.gtid = False
                self.tables.clear()
                self.ddl_count += 1
                return
            require(match[1] in (None, self.database),
                    'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
            if match[2] == 'BEGIN':
                require(self.gtid and not self.transaction)
                self.transaction = True
            else:
                require(self.gtid and self.transaction)
                self.transaction = self.gtid = False
                self.tables.clear()
        elif event_type == 'Table_map':
            require(self.gtid and self.transaction)
            match = re.fullmatch(r'table_id: ([0-9]+) '
                                 r'\(([A-Za-z0-9_-]+)\.([A-Za-z0-9_$-]+)\)', info)
            require(match is not None)
            require(match[2] == self.database,
                    'FORMAL_CAPTURE_BINLOG_DATABASE_OUT_OF_SCOPE')
            self.tables[int(match[1])] = (match[2], match[3])
        elif event_type in {'Write_rows', 'Update_rows', 'Delete_rows'}:
            require(self.gtid and self.transaction)
            match = re.fullmatch(r'table_id: ([0-9]+)(?: flags: STMT_END_F)?', info)
            require(match is not None and int(match[1]) in self.tables)
            self.affected_tables.add(self.tables[int(match[1])][1])
            self.row_count += 1
        elif event_type == 'Rows_query':
            # This annotation is not executable SQL; the actual table/row events
            # still have to prove every affected database independently.
            require(self.gtid and self.transaction)
        elif event_type == 'Xid':
            require(self.gtid and self.transaction)
            require(re.fullmatch(r'COMMIT /\* xid=[0-9]+ \*/', info) is not None)
            self.transaction = self.gtid = False
            self.tables.clear()
        else:
            # Includes statement DML helpers, load-data and
            # Transaction_payload (whose inner events are not exposed here).
            require(False, 'FORMAL_CAPTURE_BINLOG_EVENT_SCOPE_UNPROVEN')

    def complete(self):
        require(not self.transaction and not self.gtid,
                'FORMAL_CAPTURE_BINLOG_TRANSACTION_INCOMPLETE')


def event_rows(raw, filename):
    """The raw mysql client preserves newlines inside a Query event's DDL."""
    require(raw.endswith('\n'))
    rows = []
    for line in raw[:-1].split('\n'):
        if line.startswith(filename+'\t'):
            require(len(line.split('\t', 5)) == 6)
            rows.append(line)
        else:
            require(bool(rows))
            rows[-1] += '\n'+line
    return rows


def inspect_binlog_scope(mysql, segments, database, *, guard, deadline):
    """Retain a digest of all original event rows, never log their SQL text."""
    require(callable(guard) and type(deadline) in (int, float) and math.isfinite(deadline))
    require(type(segments) is list)
    mode = getattr(mysql, 'database_log_mode', 'GTID')
    RowEventScope(database, mode)
    proof = []
    for segment in segments:
        require(type(segment) is dict and set(segment) ==
                {'file', 'startPosition', 'stopPosition'} and
                type(segment['file']) is str and
                re.fullmatch(r'[A-Za-z0-9_-]+\.[0-9]{6}', segment['file']) and
                type(segment['startPosition']) is int and
                type(segment['stopPosition']) is int and
                4 <= segment['startPosition'] < segment['stopPosition'])
        cursor = segment['startPosition']
        scope = RowEventScope(database, mode)
        checksum = hashlib.sha256()
        while cursor < segment['stopPosition']:
            guard()
            require(time.monotonic() < deadline, 'FORMAL_CAPTURE_BINLOG_SCOPE_DEADLINE')
            # Identifiers/positions are strictly validated before SQL assembly.
            rows = mysql.query("SHOW BINLOG EVENTS IN '" + segment['file'] +
                               "' FROM " + str(cursor) + " LIMIT 256;")
            require(type(rows) is str and 0 < len(rows.encode('utf-8')) <= 1048576)
            page = event_rows(rows, segment['file'])
            require(0 < len(page) <= 256)
            for row in page:
                if cursor == segment['stopPosition']:
                    break
                guard()
                require(time.monotonic() < deadline, 'FORMAL_CAPTURE_BINLOG_SCOPE_DEADLINE')
                values = row.split('\t', 5)
                require(len(values) == 6 and values[0] == segment['file'] and
                        all(re.fullmatch(r'[0-9]+', values[i]) for i in (1, 3, 4)))
                event_position, end_position = int(values[1]), int(values[4])
                require(event_position == cursor and
                        cursor < end_position <= segment['stopPosition'],
                        'FORMAL_CAPTURE_BINLOG_EVENT_RANGE_CHANGED')
                scope.observe(values[2], values[5])
                checksum.update(snapshot._canonical_bytes(values))
                cursor = end_position
        scope.complete()
        proof.append(dict(segment=segment, eventRowsSha256=checksum.hexdigest(),
                          eventCount=scope.event_count, rowEventCount=scope.row_count,
                          ddlEventCount=scope.ddl_count, affectedTables=sorted(scope.affected_tables)))
    guard()
    require(time.monotonic() < deadline, 'FORMAL_CAPTURE_BINLOG_SCOPE_DEADLINE')
    return dict(schemaVersion='backup-binlog-event-scope/v3', databaseScope=[database],
                policy='MYSQL80_ROW_AND_SCOPED_DATABASE_DDL', logMode=mode, segments=proof)
