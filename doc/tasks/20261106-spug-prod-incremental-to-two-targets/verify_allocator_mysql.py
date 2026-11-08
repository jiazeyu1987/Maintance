"""Real isolated MySQL ROW-binlog allocator reproduction; no server access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from common import TASK, PRIVATE, now, write

ROOT = TASK.parents[2]
DOCKER = 'C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
IMAGE = 'sha256:ccb8f749bb5e59f9f8f03bf7282c7ef27a93a1814a24f0a8a926fb4e19b7fb97'
LABEL = 'spug-allocator-20261107'
DB = 'allocator_proof'
os.environ['PATH'] = str(Path(DOCKER).parent) + os.pathsep + os.environ['PATH']
sys.path.insert(0, str(ROOT / 'ops/backup_engine/formal'))
from formal_schema_evidence import SchemaMySql, observe_schema, compare_schema
from formal_snapshot_linux import FormalSnapshotError


def docker(args, data=None, timeout=120):
    result = subprocess.run([DOCKER, *args], input=data, capture_output=True, timeout=timeout)
    if result.returncode or result.stderr:
        write(PRIVATE / ('allocator-error-' + now().replace(':', '-') + '.private.json'),
              dict(exitCode=result.returncode, stdout=result.stdout.decode('utf8', 'replace'),
                   stderr=result.stderr.decode('utf8', 'replace')))
        raise RuntimeError('ISOLATED_DOCKER_COMMAND_FAILED')
    return result.stdout


def client(cid, password, sql=None, program='mysql', arguments=()):
    mysql = SchemaMySql(cid, password, timeout=60)
    command = mysql._command(program, ['-uroot', *arguments])
    command[0] = DOCKER
    result = subprocess.run(command, input=(password + '\n').encode() + (sql or b''),
                            capture_output=True, timeout=90)
    if result.returncode or result.stderr:
        (PRIVATE / 'allocator-client-error.private.bin').write_bytes(result.stdout + result.stderr)
        raise RuntimeError('ISOLATED_MYSQL_COMMAND_FAILED')
    return result.stdout


def query(cid, password, sql):
    return client(cid, password, sql.encode('utf8'), arguments=['--batch', '--skip-column-names'])


def inspect(cid):
    row = json.loads(docker(['inspect', cid]))[0]
    assert row['Image'] == IMAGE and row['Config']['Labels']['codex.task'] == LABEL
    assert row['HostConfig']['NetworkMode'] == 'none' and not row['HostConfig']['PortBindings']
    assert not any(m['Type'] == 'bind' for m in row['Mounts'])
    return row


def prepare(resume=False, export_only=False):
    path = PRIVATE / 'allocator-mysql-resources.private.json'
    if resume:
        record = json.loads(path.read_text(encoding='utf8'))
        assert record['task'] == LABEL and record['image'] == IMAGE and len(record['containers']) == 2
        assert export_only or 'sqlStartedAt' not in record, 'NO_AUTOMATIC_REPLAY_OF_SQL'
        password = record['password']
        for item in record['containers']:
            inspect(item['id'])
    else:
        assert not path.exists(), 'EXPLICIT_RESOURCE_OWNERSHIP_ALREADY_EXISTS'
        password = secrets.token_hex(24)
        env = PRIVATE / 'allocator-mysql.env.private'
        env.write_text('MYSQL_ROOT_PASSWORD=' + password + '\n', encoding='utf8')
        record = dict(task=LABEL, image=IMAGE, password=password, containers=[], createdAt=now())
        write(path, record)
        for role in ('source', 'target'):
            cid = docker(['run', '--detach', '--name', LABEL + '-' + role,
                      '--label', 'codex.task=' + LABEL, '--network', 'none', '--memory', '2g',
                      '--memory-swap', '2g', '--pids-limit', '256', '--env-file', str(env),
                      '--tmpfs', '/var/lib/mysql:rw,nosuid,nodev,size=1073741824',
                      IMAGE, '--server-id=' + ('771' if role == 'source' else '772'),
                      '--log-bin=allocator-bin', '--binlog-format=ROW', '--gtid-mode=OFF',
                      '--enforce-gtid-consistency=OFF']).decode().strip()
            record['containers'].append(dict(role=role, id=cid));write(path, record)
            inspect(cid)
    deadline = time.monotonic() + 110
    for item in record['containers']:
        mysql = SchemaMySql(item['id'], password, timeout=30)
        while not mysql.ready():
            assert time.monotonic() < deadline, 'MYSQL_REAL_STARTUP_DEADLINE'
            time.sleep(.5)
    source, target = [c['id'] for c in record['containers']]
    if not export_only:
        for cid in (source, target):
            assert query(cid, password, 'SELECT @@port;').strip() == b'3306'
            assert DB.encode() not in query(cid, password, 'SHOW DATABASES;')
        record['sqlStartedAt'] = now();write(path, record)
        query(source, password, 'CREATE DATABASE ' + DB + '; USE ' + DB + '; '
          "CREATE TABLE allocated (id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY, code INT UNIQUE); "
          'INSERT INTO allocated(code) VALUES(1);')
        dump = client(source, password, program='mysqldump',
                  arguments=['--single-transaction', '--set-gtid-purged=OFF', '--databases', DB])
        client(target, password, dump)
        start = query(source, password, 'SHOW MASTER STATUS;').decode().split('\t')[:2]
        query(source, password, 'USE ' + DB + '; INSERT INTO allocated(code) VALUES(2);' +
          'INSERT IGNORE INTO allocated(code) VALUES(2);' * 8)
    end = query(source, password, 'SHOW MASTER STATUS;').decode().split('\t')[:2]
    if export_only:
        assert query(source, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;') == b'1\t1\n2\t2\n'
        assert query(target, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;') == b'1\t1\n'
        events = [line.split('\t') for line in query(source, password,
            "SHOW BINLOG EVENTS IN '" + end[0] + "';").decode().splitlines()]
        commits = [r for r in events if r[2] == 'Xid']
        assert len(commits) == 2, 'EXACT_ISOLATED_TRANSACTIONS_REQUIRED'
        start = [end[0], commits[0][4]]
    assert start[0] == end[0]
    tool = PRIVATE / 'allocator-mysqlbinlog.private'
    assert hashlib.sha256(tool.read_bytes()).hexdigest() == '8b1ed50f07233f89a3acbf3f0772267ac05c3a7b7e1d34c508fb8cb99ed6e0f5'
    docker(['cp', str(tool), source + ':/tmp/allocator-mysqlbinlog'])
    docker(['exec', source, 'chmod', '0555', '/tmp/allocator-mysqlbinlog'])
    segment = docker(['exec', source, '/tmp/allocator-mysqlbinlog', '--no-defaults', '--skip-gtids',
                      '--start-position=' + start[1], '--stop-position=' + end[1],
                      '/var/lib/mysql/' + start[0]])
    (PRIVATE / 'allocator-real-binlog.private.sql').write_bytes(segment)
    client(target, password, segment)
    srows = query(source, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;')
    trows = query(target, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;')
    assert srows == trows == b'1\t1\n2\t2\n'
    schemas = {}
    for role, cid in (('source', source), ('target', target)):
        uuid = query(cid, password, 'SELECT @@server_uuid;').decode().strip()
        schemas[role] = observe_schema(SchemaMySql(cid, password, timeout=60), DB, uuid, guard=lambda: inspect(cid))
    write(PRIVATE / 'allocator-real-schemas.private.json', schemas)
    try:
        compare_schema(schemas['source'], schemas['target'])
    except FormalSnapshotError as error:
        assert error.code == 'FORMAL_SCHEMA_MISMATCH'
    else:
        raise AssertionError('REAL_RED_NOT_REPRODUCED')
    counters = {}
    for role, cid in (('source', source), ('target', target)):
        counters[role] = int(query(cid, password,
            "SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA='" + DB +
            "' AND TABLE_NAME='allocated';").strip())
    assert counters == dict(source=11, target=3)
    report = dict(status='EXPECTED_RED', observedAt=now(), mysqlVersion='8.0.39',
                  image=IMAGE, database=DB, counters=counters, committedRowsEqual=True,
                  strictSchemaFailure='FORMAL_SCHEMA_MISMATCH', binlogBytes=len(segment),
                  binlogSha256=hashlib.sha256(segment).hexdigest(), businessServersAccessed=False,
                  resourceIds=[c['id'] for c in record['containers']])
    write(TASK / 'allocator-real-red.json', report)
    print(json.dumps(report))


def green(attempt):
    from formal_schema_evidence import restore_frozen_auto_increment
    record = json.loads((PRIVATE / 'allocator-mysql-resources.private.json').read_text(encoding='utf8'))
    assert record['task'] == LABEL and record['image'] == IMAGE
    source, target = [c['id'] for c in record['containers']]
    password = record['password']
    for cid in (source, target):inspect(cid)
    schemas = json.loads((PRIVATE / 'allocator-real-schemas.private.json').read_text(encoding='utf8'))
    target_uuid = schemas['target']['observationIdentity']['databaseUuid']
    root = PRIVATE / ('allocator-green-evidence-' + str(attempt))
    root.mkdir(exist_ok=False)
    if attempt in (2, 3):
        old = PRIVATE / 'allocator-green-evidence'
        assert (old / 'allocator-intent.json').is_file()
        old_intent = json.loads((old / 'allocator-intent.json').read_text(encoding='utf8'))
        assert old_intent['changes'][0]['before'] == 3 and old_intent['changes'][0]['after'] == 11
        assert query(target, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;') == b'1\t1\n2\t2\n'
        query(target, password, 'ALTER TABLE ' + DB + '.allocated AUTO_INCREMENT=3;')
        if attempt == 2:write(TASK / 'allocator-real-green-attempt1-failure.json', dict(status='TEST_CARRIER_FAILED',
            actualAlterCompleted=True, assertion='client header options missing', originalEvidencePreserved=True,
            isolatedTargetResetForNewGreen=True, observedAt=now()))
    def evidence(name, value):
        path = root / name
        assert not path.exists();write(path, value)
        return dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    calls = []
    def mutate(sql):
        raw = client(target, password,
            ('USE ' + DB + '; SELECT @@server_uuid; ' + sql +
             ' SELECT @@warning_count; SELECT @@server_uuid;').encode(),
             arguments=['--batch', '--skip-column-names'])
        calls.append(evidence('native-mutation-%03d.json' % len(calls),
            dict(sql=sql, actualExitCode=0, stderrBytes=0, stdoutSha256=hashlib.sha256(raw).hexdigest())))
        assert raw.decode().splitlines() == [target_uuid, '0', target_uuid]
    outcome = restore_frozen_auto_increment(SchemaMySql(target, password, timeout=60), schemas['source'],
        target_uuid, guard=lambda: inspect(target), mutate=mutate, record=evidence)
    assert len(calls) == 1
    after = observe_schema(SchemaMySql(target, password, timeout=60), DB, target_uuid, guard=lambda: inspect(target))
    compare_schema(schemas['source'], after)
    srows = query(source, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;')
    trows = query(target, password, 'SELECT * FROM ' + DB + '.allocated ORDER BY id;')
    assert srows == trows == b'1\t1\n2\t2\n'
    second = root / 'second'
    second.mkdir()
    first_count = len(calls)
    def second_record(name, value):
        path = second / name;assert not path.exists();write(path, value)
        return dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    restore_frozen_auto_increment(SchemaMySql(target, password, timeout=60), schemas['source'],
        target_uuid, guard=lambda: inspect(target), mutate=mutate, record=second_record)
    assert len(calls) == first_count
    report = dict(status='PASS', observedAt=now(), actualMysqlVersion='8.0.39',
        sourceCounter=11, targetCounter=11, actualAlterCount=len(calls), strictSchemaEqual=True,
        realRowsEqual=True, unchangedAllocatorSecondPassWrites=0, outcomePin=outcome,
        sourceBusinessServersWritten=False)
    destination = TASK / ('allocator-real-green.json' if attempt == 2 else 'allocator-real-green-' + str(attempt) + '.json')
    assert not destination.exists();write(destination, report);print(json.dumps(report))


def cleanup():
    output = TASK / 'allocator-real-resource-cleanup.json'
    assert not output.exists()
    assert json.loads((TASK / 'allocator-real-red.json').read_text(encoding='utf8'))['status'] == 'EXPECTED_RED'
    assert json.loads((TASK / 'allocator-real-green-3.json').read_text(encoding='utf8'))['status'] == 'PASS'
    record = json.loads((PRIVATE / 'allocator-mysql-resources.private.json').read_text(encoding='utf8'))
    assert record['task'] == LABEL and record['image'] == IMAGE and len(record['containers']) == 2
    ids = [c['id'] for c in record['containers']]
    assert len(set(ids)) == 2
    for item in record['containers']:
        row = inspect(item['id'])
        assert row['Name'] == '/' + LABEL + '-' + item['role']
        assert row['HostConfig']['Tmpfs']['/var/lib/mysql'] == 'rw,nosuid,nodev,size=1073741824'
    for cid in ids:
        docker(['stop', '--time', '20', cid])
        assert not inspect(cid)['State']['Running']
        docker(['rm', cid])
    remaining = set(docker(['ps', '-aq', '--no-trunc']).decode().split())
    assert not remaining.intersection(ids)
    result = dict(status='PASS', observedAt=now(), removedIds=ids, ownedIsolatedOnly=True,
                  businessServersAccessed=False, originalTestEvidencePreserved=True)
    write(output, result);print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('mode', choices=['prepare', 'resume-started-containers', 'resume-binlog-export', 'green', 'cleanup'])
    parser.add_argument('--attempt', type=int, default=1)
    args = parser.parse_args()
    if args.mode == 'cleanup':cleanup()
    elif args.mode == 'green':green(args.attempt)
    else:prepare(resume=args.mode != 'prepare', export_only=args.mode == 'resume-binlog-export')
