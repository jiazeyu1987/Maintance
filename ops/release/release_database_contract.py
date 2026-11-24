"""Versioned, immutable application requirements; never infer them from a ledger."""
import hashlib
import json
import re
from pathlib import Path

from ops.release.release_readonly_sql import _executable_sql, FORBIDDEN_PATTERN

VERSION = 'ApplicationDatabaseContract/v1'
DIRECTORY = 'sql/mysql/database-contracts'
CATALOG = DIRECTORY + '/catalog.json'
# No stored functions/UDFs: a SELECT alone is not a read-only guarantee.
FUNCTIONS = {'COUNT', 'SUM', 'MIN', 'MAX', 'COALESCE', 'IFNULL', 'NULLIF', 'IF',
             'LOWER', 'UPPER', 'TRIM', 'LTRIM', 'RTRIM', 'CONCAT', 'CONCAT_WS',
             'LENGTH', 'CHAR_LENGTH', 'OCTET_LENGTH', 'REGEXP_REPLACE', 'REGEXP_LIKE',
             'DATABASE', 'SCHEMA', 'CAST', 'CONVERT', 'CHAR', 'LOCATE', 'GROUP_CONCAT', 'IN', 'EXISTS',
             'AS', 'AND', 'OR', 'NOT', 'WHERE', 'WHEN', 'THEN', 'ELSE', 'ON', 'HAVING'}


def require(condition, message):
    if not condition:
        raise ValueError('Database contract: ' + message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_file(root, name):
    root = Path(root).resolve()
    path = root / name
    require(path.is_file() and not path.is_symlink(), 'file missing or symbolic link: ' + name)
    require(root in path.resolve().parents, 'file escapes package: ' + name)
    require(not any(p.is_symlink() for p in path.parents if p != root and root in p.parents),
            'symbolic directory: ' + name)
    require(path.stat().st_size <= 262144, 'file too large: ' + name)
    return path, path.read_bytes()


def validate_sql(text, identity):
    require(text.count('DATABASE_CONTRACT_PASS:' + identity) == 1, 'one pass marker required: ' + identity)
    try:
        executable = _executable_sql(text)
    except RuntimeError as error:
        raise ValueError('Database contract: unsafe SQL: ' + str(error)) from error
    require(not FORBIDDEN_PATTERN.search(executable), 'write or locking SQL forbidden: ' + identity)
    statements = [s.strip() for s in executable.split(';') if s.strip()]
    require(len(statements) == 1 and re.match(r'^(SELECT|WITH)\b', statements[0], re.I),
            'one SELECT/WITH required: ' + identity)
    require(not re.search(r'[`"]\s*\(', text), 'quoted function forbidden: ' + identity)
    for match in re.finditer(r'\b([A-Za-z_][A-Za-z_0-9]*)\s*\(', executable):
        require(match.group(1).upper() in FUNCTIONS and
                not executable[:match.start()].rstrip().endswith('.'),
                'unapproved function: ' + match.group(1))


def collect(root):
    path, data = read_file(root, CATALOG)
    catalog = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    require(isinstance(catalog, dict) and set(catalog) == {'schemaVersion', 'contracts'} and
            catalog['schemaVersion'] == VERSION, 'unsupported catalog')
    entries = catalog['contracts']
    require(isinstance(entries, list) and 0 < len(entries) <= 512, 'nonempty contract collection required')
    artifacts = {CATALOG: path}
    checks, ids, filenames = [], set(), set()
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {'id', 'file'}, 'invalid catalog entry')
        identity, filename = entry['id'], entry['file']
        require(isinstance(identity, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,95}', identity), 'invalid id')
        require(isinstance(filename, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,95}\.sql', filename), 'invalid filename')
        require(identity not in ids and filename not in filenames, 'duplicate contract')
        ids.add(identity)
        filenames.add(filename)
        relative = DIRECTORY + '/' + filename
        source, content = read_file(root, relative)
        validate_sql(content.decode('utf-8'), identity)
        checks.append(dict(id=identity, file=relative, sha256=hashlib.sha256(content).hexdigest()))
        artifacts[relative] = source
    return dict(schemaVersion=VERSION, catalog=dict(file=CATALOG, sha256=hashlib.sha256(data).hexdigest()),
                checks=checks), artifacts


def validate_package(root, manifest):
    descriptor = manifest.get('databaseContract')
    require(isinstance(descriptor, dict), 'current contract missing; rebuild for forward deployment')
    # Hash before parsing, so changed source is reported as immutable-input failure.
    for entry in [descriptor.get('catalog', {})] + descriptor.get('checks', []):
        name = entry.get('file', '')
        require(isinstance(name, str) and name.startswith(DIRECTORY + '/') and
                re.fullmatch(r'[a-z0-9/-]+\.(sql|json)', name) and '..' not in name, 'unsafe contract path')
        _, data = read_file(root, name)
        require(hashlib.sha256(data).hexdigest() == entry.get('sha256'), 'checksum mismatch: ' + name)
    actual, artifacts = collect(root)
    require(descriptor == actual, 'manifest and catalog differ')
    files = manifest.get('files', [])
    for entry in [actual['catalog']] + actual['checks']:
        matches = [item for item in files if item.get('name') == entry['file']]
        require(len(matches) == 1 and matches[0].get('sha256') == entry['sha256'],
                'contract not bound to package files: ' + entry['file'])
    return actual


def verify(root, manifest, execute):
    descriptor = validate_package(root, manifest)
    for check in descriptor['checks']:
        _, data = read_file(root, check['file'])
        require(hashlib.sha256(data).hexdigest() == check['sha256'], 'checksum changed before execution: ' + check['id'])
        output = execute(data.decode('utf-8'))
        require(isinstance(output, str) and output.strip() == 'DATABASE_CONTRACT_PASS:' + check['id'],
                'requirement failed: ' + check['id'])
    return dict(schemaVersion=VERSION, status='PASS', catalogSha256=descriptor['catalog']['sha256'],
                checks=[check['id'] for check in descriptor['checks']])
