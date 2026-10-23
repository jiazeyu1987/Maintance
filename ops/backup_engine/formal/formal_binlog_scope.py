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


def scoped_table_ddl(sql, database, default_database):
    """Recognize a deliberately bounded DDL grammar, not arbitrary SQL.

    No SELECT/LIKE, expressions, cross-database references, partitions, routines,
    external storage, executable comments or multiple statements are allowed.
    Every table target must resolve to the originally registered database.
    """
    code = 'FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN'
    # mysqldump emits only this exact executable wrapper for index rebuilds.
    keys = re.fullmatch(r'/\*!40000 (ALTER TABLE .+ (?:DISABLE|ENABLE) KEYS) \*/', sql, re.I)
    if keys is not None:
        sql = keys[1]
    require(not any(x in sql for x in (';', '/*', '--', '#', '\\', '"')), code)
    ident = r'(?:`[A-Za-z0-9_$-]+`|[A-Za-z_][A-Za-z0-9_$]*)'
    table = rf'({ident})(?:\s*\.\s*({ident}))?'
    column_type = (r'(?:TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT|'
                   r'CHAR|VARCHAR|BINARY|VARBINARY|DECIMAL|NUMERIC|FLOAT|DOUBLE|'
                   r'DATE|DATETIME|TIMESTAMP|TIME|YEAR|TEXT|TINYTEXT|MEDIUMTEXT|'
                   r'LONGTEXT|BLOB|TINYBLOB|MEDIUMBLOB|LONGBLOB|JSON|BOOLEAN|BOOL)'
                   r'(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?')
    literal = r"(?:NULL|[+-]?\d+(?:\.\d+)?|'(?:[^'\\]|'')*'|CURRENT_TIMESTAMP(?:\(\d*\))?)"
    definition = (rf'{ident}\s+{column_type}'
                  rf'(?:\s+(?:UNSIGNED|ZEROFILL|NOT\s+NULL|NULL|AUTO_INCREMENT|'
                  rf'PRIMARY\s+KEY|UNIQUE(?:\s+KEY)?|DEFAULT\s+{literal}|'
                  rf'COMMENT\s+\'(?:[^\'\\]|\'\')*\'|'
                  rf'CHARACTER\s+SET\s+{ident}|COLLATE\s+{ident}))*')
    columns = rf'\(\s*{ident}(?:\s*\(\d+\))?(?:\s+(?:ASC|DESC))?(?:\s*,\s*{ident}(?:\s*\(\d+\))?(?:\s+(?:ASC|DESC))?)*\s*\)'
    index = rf'(?:(?:UNIQUE\s+)?(?:INDEX|KEY)(?:\s+{ident})?|PRIMARY\s+KEY)\s*{columns}'
    foreign_columns = rf'\(\s*{ident}(?:\s*,\s*{ident})*\s*\)'
    foreign_key = (rf'(?:CONSTRAINT(?:\s+{ident})?\s+)?FOREIGN\s+KEY(?:\s+{ident})?\s*'
                   rf'{foreign_columns}\s+REFERENCES\s+{table}\s*{foreign_columns}')

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
                         rf'(?:DEFAULT\s+)?CHARACTER\s+SET\s*=?\s*{ident}|COLLATE\s*=?\s*{ident}))*\s*', sql, re.I | re.S)
    if match:
        name = target(match)
        for part in parts(match[3]):
            if matches(rf'(?:{definition}|{index})', part):
                continue
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
                if scoped_database_ddl(statement, self.database):
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
