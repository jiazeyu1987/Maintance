"""Read-only MySQL structure and effective migration comparison.

This is an observation contract, separate from deployment baseline fingerprints.
Only object identities/digests and migration metadata leave the database host.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations


SCHEMA_VERSION = 'mysql-structure-v1'
# section, metadata table, filter column, identity columns, compared attributes
SECTIONS = (
    ('tables', 'TABLES', 'TABLE_SCHEMA', ('TABLE_NAME',),
     'TABLE_NAME TABLE_TYPE ENGINE TABLE_COLLATION CREATE_OPTIONS'),
    ('columns', 'COLUMNS', 'TABLE_SCHEMA', ('TABLE_NAME', 'COLUMN_NAME'),
     'TABLE_NAME ORDINAL_POSITION COLUMN_NAME COLUMN_TYPE IS_NULLABLE COLUMN_DEFAULT EXTRA COLLATION_NAME GENERATION_EXPRESSION'),
    ('indexes', 'STATISTICS', 'TABLE_SCHEMA', ('TABLE_NAME', 'INDEX_NAME', 'SEQ_IN_INDEX'),
     'TABLE_NAME INDEX_NAME NON_UNIQUE SEQ_IN_INDEX COLUMN_NAME SUB_PART INDEX_TYPE COLLATION IS_VISIBLE EXPRESSION'),
    ('constraints', 'TABLE_CONSTRAINTS', 'TABLE_SCHEMA', ('TABLE_NAME', 'CONSTRAINT_NAME'),
     'TABLE_NAME CONSTRAINT_NAME CONSTRAINT_TYPE ENFORCED'),
    ('foreignKeys', 'KEY_COLUMN_USAGE', 'TABLE_SCHEMA', ('TABLE_NAME', 'CONSTRAINT_NAME', 'ORDINAL_POSITION'),
     'TABLE_NAME CONSTRAINT_NAME COLUMN_NAME ORDINAL_POSITION POSITION_IN_UNIQUE_CONSTRAINT REFERENCED_TABLE_NAME REFERENCED_COLUMN_NAME'),
    ('foreignKeyRules', 'REFERENTIAL_CONSTRAINTS', 'CONSTRAINT_SCHEMA', ('TABLE_NAME', 'CONSTRAINT_NAME'),
     'TABLE_NAME CONSTRAINT_NAME UNIQUE_CONSTRAINT_NAME MATCH_OPTION UPDATE_RULE DELETE_RULE REFERENCED_TABLE_NAME'),
    ('checks', 'CHECK_CONSTRAINTS', 'CONSTRAINT_SCHEMA', ('CONSTRAINT_NAME',),
     'CONSTRAINT_NAME CHECK_CLAUSE'),
    ('views', 'VIEWS', 'TABLE_SCHEMA', ('TABLE_NAME',),
     'TABLE_NAME VIEW_DEFINITION CHECK_OPTION IS_UPDATABLE SECURITY_TYPE CHARACTER_SET_CLIENT COLLATION_CONNECTION'),
    ('triggers', 'TRIGGERS', 'TRIGGER_SCHEMA', ('TRIGGER_NAME',),
     'TRIGGER_NAME EVENT_MANIPULATION EVENT_OBJECT_TABLE ACTION_ORDER ACTION_TIMING ACTION_STATEMENT SQL_MODE CHARACTER_SET_CLIENT COLLATION_CONNECTION DATABASE_COLLATION'),
    ('routines', 'ROUTINES', 'ROUTINE_SCHEMA', ('ROUTINE_NAME', 'ROUTINE_TYPE'),
     'ROUTINE_NAME ROUTINE_TYPE DATA_TYPE DTD_IDENTIFIER ROUTINE_DEFINITION IS_DETERMINISTIC SQL_DATA_ACCESS SECURITY_TYPE SQL_MODE'),
    ('parameters', 'PARAMETERS', 'SPECIFIC_SCHEMA', ('SPECIFIC_NAME', 'ORDINAL_POSITION'),
     'SPECIFIC_NAME ORDINAL_POSITION PARAMETER_MODE PARAMETER_NAME DTD_IDENTIFIER CHARACTER_SET_NAME COLLATION_NAME ROUTINE_TYPE'),
    ('events', 'EVENTS', 'EVENT_SCHEMA', ('EVENT_NAME',),
     'EVENT_NAME EVENT_TYPE EXECUTE_AT INTERVAL_VALUE INTERVAL_FIELD SQL_MODE STARTS ENDS STATUS ON_COMPLETION EVENT_DEFINITION TIME_ZONE'),
    ('databaseOptions', 'SCHEMATA', 'SCHEMA_NAME', ('SCHEMA_NAME',),
     'SCHEMA_NAME DEFAULT_CHARACTER_SET_NAME DEFAULT_COLLATION_NAME'),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(',', ':')).encode()).hexdigest()


def snapshot_query():
    statements = []
    for section, table, schema, keys, attributes in SECTIONS:
        obj = 'JSON_OBJECT(' + ','.join("'%s',%s" % (a, a) for a in attributes.split()) + ')'
        condition = schema + '=DATABASE()'
        if section == 'foreignKeys':
            condition += ' AND REFERENCED_TABLE_NAME IS NOT NULL'
        statements.append("SELECT JSON_OBJECT('section','%s','item',%s) FROM information_schema.%s WHERE %s ORDER BY %s;"
                          % (section, obj, table, condition, ','.join(keys)))
    statements.append("SELECT JSON_OBJECT('section','ledger','item',JSON_OBJECT('id',id,'migrationId',migration_id,'sha256',sha256,'status',status)) FROM infra_release_migration WHERE deleted=b'0' ORDER BY id;")
    return '\n'.join(statements)


def parse_snapshot(raw):
    rows = {section: [] for section, *_ in SECTIONS}
    history = []
    for line in raw.splitlines():
        entry = json.loads(line)
        if entry['section'] == 'ledger':
            history.append(entry['item'])
        else:
            rows[entry['section']].append(entry['item'])
    objects = {}
    for section, _, _, keys, _ in SECTIONS:
        objects[section] = {}
        for row in rows[section]:
            identity = json.dumps([row[key] for key in keys], ensure_ascii=True, separators=(',', ':'))
            if identity in objects[section]:
                raise RuntimeError('Duplicate metadata object identity: ' + section)
            objects[section][identity] = dict(name=' / '.join(str(row[key]) for key in keys), sha256=digest(row))
    latest, checksums = {}, {}
    for row in history:
        mid = row['migrationId']
        checksums.setdefault(mid, set()).add(row['sha256'])
        latest[mid] = dict(sha256=row['sha256'], status='SUCCESS' if row['status'] in
                          ('APPLIED', 'SKIPPED_ALREADY_APPLIED') else row['status'])
    conflicts = sorted(mid for mid, values in checksums.items() if len(values) != 1)
    unsuccessful = sorted(mid for mid, row in latest.items() if row['status'] != 'SUCCESS')
    # Internal definitions and data values are replaced by object digests.
    return dict(schema=dict(sha256=digest(objects), objects=objects,
                            counts={k: len(v) for k, v in rows.items()}),
                migrations=dict(sha256=digest(latest), items=latest, count=len(latest),
                                historyCount=len(history), statuses=dict(Counter(r['status'] for r in history)),
                                checksumConflicts=conflicts, unsuccessful=unsuccessful,
                                healthy=not conflicts and not unsuccessful))


def read_database(remote, profile):
    started = datetime.now(timezone.utc).isoformat()
    before = remote.inspect(profile['database'])
    if not before['State']['Running']:
        raise RuntimeError('Registered database container is stopped')
    remote.sql(profile, 'SHOW TABLES;')
    remote.sql(profile, 'DESCRIBE infra_release_migration;')
    identity = remote.sql(profile, 'SELECT DATABASE(),@@version,@@lower_case_table_names;').split('\t')
    if len(identity) != 3:
        raise RuntimeError('Database identity response is invalid')
    first = parse_snapshot(remote.sql(profile, snapshot_query()))
    second = parse_snapshot(remote.sql(profile, snapshot_query()))
    after = remote.inspect(profile['database'])
    stable = (first == second and before['Id'] == after['Id'] and
              before['State']['StartedAt'] == after['State']['StartedAt'] and after['State']['Running'])
    return dict(second, status='ok' if stable else 'changed', stable=bool(stable),
                host=profile['host'], database=identity[0], mysqlVersion=identity[1],
                lowerCaseTableNames=identity[2], algorithm=SCHEMA_VERSION,
                startedAt=started, observedAt=datetime.now(timezone.utc).isoformat(),
                error=None if stable else '采集期间数据库结构、迁移记录或容器发生变化，请重新读取。')


def compare_targets(targets, limit=50):
    pairs = []
    for left, right in combinations(('test', 'prod', 'backup'), 2):
        a, b = targets[left], targets[right]
        pair = dict(left=left, right=right, status='unknown', schemaEqual=None, migrationsEqual=None)
        if a.get('status') != 'ok' or b.get('status') != 'ok' or a.get('algorithm') != b.get('algorithm'):
            pairs.append(pair)
            continue
        pair['schemaEqual'] = (a['schema']['sha256'] == b['schema']['sha256'] and
                               a['lowerCaseTableNames'] == b['lowerCaseTableNames'])
        if a['migrations']['healthy'] and b['migrations']['healthy']:
            pair['migrationsEqual'] = a['migrations']['items'] == b['migrations']['items']
        changes = []
        for section in a['schema']['objects']:
            aa, bb = a['schema']['objects'][section], b['schema']['objects'][section]
            for key in sorted(set(aa) | set(bb)):
                if aa.get(key) != bb.get(key):
                    changes.append(dict(section=section, name=(aa.get(key) or bb[key])['name'],
                                        kind='onlyRight' if key not in aa else 'onlyLeft' if key not in bb else 'changed'))
        am, bm = a['migrations']['items'], b['migrations']['items']
        migration_changes = [dict(migrationId=mid, left=am.get(mid), right=bm.get(mid))
                             for mid in sorted(set(am) | set(bm)) if am.get(mid) != bm.get(mid)]
        pair.update(structureDifferenceCount=len(changes), structureDifferences=changes[:limit],
                    migrationDifferenceCount=len(migration_changes), migrationDifferences=migration_changes[:limit],
                    detailsLimit=limit,
                    status='different' if pair['schemaEqual'] is False or pair['migrationsEqual'] is False else
                           'identical' if pair['migrationsEqual'] is True else 'unknown')
        pairs.append(pair)
    return pairs


def public_targets(targets):
    """Object/migration maps are used for comparison, not returned twice to the UI."""
    return {env: {**value,
                  **({'schema': {k: v for k, v in value['schema'].items() if k != 'objects'}} if 'schema' in value else {}),
                  **({'migrations': {k: v for k, v in value['migrations'].items() if k != 'items'}} if 'migrations' in value else {})}
            for env, value in targets.items()}
