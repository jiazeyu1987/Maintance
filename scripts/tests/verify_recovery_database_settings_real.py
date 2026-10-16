"""Exercise installed recovery settings against isolated real MySQL databases.

The two archived observation inputs are collected from empty test databases,
not fabricated schema dictionaries or a new application backup operation.
Requires explicit task-owned evidence root, installed recovery/formal modules,
and the exact already installed MySQL image. No published ports or host network.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', required=True, type=Path)
parser.add_argument('--recovery-modules', required=True)
parser.add_argument('--formal-modules', required=True)
parser.add_argument('--image', required=True)
args = parser.parse_args()
sys.path[:0] = [args.recovery_modules, args.formal_modules]
from recovery_data import NativeData, database_settings
from recovery_engine import Budget, RecoveryError, check_pin, pin, pinned_json, require, write
import formal_data_evidence as data
import formal_sql_restore as sql
from formal_schema_evidence import compare_schema, observe_schema

root = args.root.resolve()
require(str(root).startswith('/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07/'), 'TEST_ROOT_SCOPE')
root.mkdir(mode=0o700)
operation = 'brlab-20261012-settings-' + secrets.token_hex(5)
owned = []
password = secrets.token_hex(32)
private = root/'private'; private.mkdir(mode=0o700)
(private/'root').write_text(password); (private/'root').chmod(0o600)
(private/'client.cnf').write_text('[client]\nuser=root\npassword=' + password + '\nprotocol=SOCKET\nhost=localhost\n')
(private/'client.cnf').chmod(0o600)


def docker(arguments):
    result = subprocess.run(['docker', *arguments], capture_output=True, timeout=120)
    require(result.returncode == 0, 'TEST_DOCKER_FAILED')
    return result.stdout


def inspect(identity):
    row = json.loads(docker(['inspect', identity]))[0]
    require(row['Id'] in owned and row['Image'] == args.image and row['State']['Running'] and
        row['Config']['Labels']['intruoyi.task'] == operation and
        row['HostConfig']['NetworkMode'] == 'none' and not row['HostConfig']['PortBindings'],
        'TEST_TARGET_CHANGED')
    return row


def query(identity, statement):
    inspect(identity)
    return docker(['exec', identity, 'mysql', '--defaults-extra-file=/run/recovery/mysql-client.cnf',
        '--batch', '--skip-column-names', '-e', statement]).decode()


def create(role, database=None):
    arguments = ['run', '-d', '--pull=never', '--name', operation+'-'+role,
        '--label', 'intruoyi.task='+operation, '--network', 'none', '--memory', '512m',
        '--cpus', '0.5', '--pids-limit', '128', '--restart', 'no',
        '--security-opt', 'no-new-privileges', '--tmpfs', '/var/lib/mysql:rw,size=768m',
        '--mount', 'type=bind,src='+str(private/'root')+',dst=/run/recovery/mysql-root,readonly',
        '--mount', 'type=bind,src='+str(private/'client.cnf')+',dst=/run/recovery/mysql-client.cnf,readonly',
        '-e', 'MYSQL_ROOT_PASSWORD_FILE=/run/recovery/mysql-root']
    if database:
        arguments += ['-e', 'MYSQL_DATABASE='+database]
    identity = docker(arguments+[args.image, '--event-scheduler=OFF', '--innodb-buffer-pool-size=67108864']).decode().strip()
    owned.append(identity)
    deadline = time.monotonic()+120
    while True:
        result = subprocess.run(['docker', 'exec', identity, 'mysql',
            '--defaults-extra-file=/run/recovery/mysql-client.cnf', '-Nse', 'SELECT @@server_uuid,@@port;'], capture_output=True)
        if result.returncode == 0 and result.stdout.decode().strip().endswith('\t3306'):
            inspect(identity)
            return identity, result.stdout.decode().strip().split('\t')[0]
        require(time.monotonic() < deadline, 'TEST_MYSQL_START_FAILED')
        time.sleep(1)


class RealTarget(NativeData):
    """Use real isolated target checks; all settings logic is the installed method."""
    def __init__(self, identity, uuid, database, archive_pin, source_uuid, evidence):
        self.db_container, self.db_uuid, self.source_uuid = identity, uuid, source_uuid
        self.config = dict(database=database, dockerPin=pin('/usr/bin/docker'))
        self.policy = dict(environmentMysqlClientPath='/usr/bin/mysql')
        self.db_target = dict(database=database, databaseUuid=uuid)
        self.material = dict(database=dict(method='FORMAL_SQL_FULL', expectedDataPin=archive_pin), payloadPins=[archive_pin])
        self.modules = dict(formal_sql_restore=sql, formal_data_evidence=data)
        self.original = dict(operationId=operation)
        self.request = dict(action='DATABASE_FULL')
        self.original_pins = []; self.last_exit = None; self.mutation_dispatched = False
        self.root = evidence; evidence.mkdir(mode=0o700)
        self.budget = Budget(300000)
        self.mysql = sql.IsolatedTargetMySql(identity, password, timeout=90)

    def guard(self):
        self.budget.remaining()
        check_pin(self.config['dockerPin'], content=False)
        for reference in self.material['payloadPins']:
            check_pin(reference)

    def bound(self, **kwargs):
        self.guard(); inspect(self.db_container)
        require(self.db_uuid != self.source_uuid, 'SOURCE_DATABASE_TARGET_REJECTED')
        sql.database_state(self.mysql, self.db_target)


def rejected(call, code):
    try:
        call()
    except Exception as error:
        require(getattr(error, 'code', None) == code, 'TEST_UNEXPECTED_REJECTION')
        return code
    raise AssertionError('TEST_UNSAFE_ACTION_ACCEPTED')


try:
    source, source_uuid = create('observations')
    cases = [('settings_utf8', 'utf8mb4', 'utf8mb4_bin'), ('settings_latin', 'latin1', 'latin1_swedish_ci')]
    results = []
    for index, (database, charset, collation) in enumerate(cases):
        query(source, 'SHOW DATABASES;')
        query(source, f"CREATE DATABASE `{database}` DEFAULT CHARACTER SET {charset} COLLATE {collation} DEFAULT ENCRYPTION='N';")
        client = data.DataMySql(source, password, timeout=120)
        def source_guard():
            inspect(source)
            require(query(source, 'SELECT @@server_uuid;').strip() == source_uuid, 'TEST_SOURCE_CHANGED')
        observation = data.observe_data(client, database, source_uuid, guard=source_guard,
            scratch=root/('observation-'+str(index)), max_rows=100, max_nodes=1000, max_bytes=1048576, seconds=120)
        archive = write(root/('archived-observation-'+str(index)+'.json'), observation)
        target, target_uuid = create('target-'+str(index), database)
        native = RealTarget(target, target_uuid, database, archive, source_uuid, root/('apply-'+str(index)))
        result_pin = native.restore_database_settings()
        result = pinned_json(result_pin)
        wanted = database_settings(observation['schema']['definitions']['DATABASE'][database], database)
        require(result['changed'] and result['before'] != result['after'] and
            result['after'] == wanted, 'TEST_SETTINGS_NOT_APPLIED')
        query(target, 'DESCRIBE information_schema.SCHEMATA;')
        effective = query(target, "SELECT DEFAULT_CHARACTER_SET_NAME,DEFAULT_COLLATION_NAME FROM "
            "information_schema.SCHEMATA WHERE SCHEMA_NAME='"+database+"';")
        require(effective == charset+'\t'+collation+'\n', 'TEST_EFFECTIVE_SETTINGS_MISMATCH')
        actual = observe_schema(native.mysql, database, target_uuid, guard=native.bound)
        compare_schema(observation['schema'], actual)
        wrong = RealTarget(target, target_uuid, database, archive, source_uuid, root/('wrong-uuid-'+str(index)))
        wrong.db_target['databaseUuid'] = source_uuid
        wrong_code = rejected(wrong.restore_database_settings, 'FORMAL_SQL_DATABASE_CHANGED')
        incremental = RealTarget(target, target_uuid, database, archive, source_uuid, root/('incremental-'+str(index)))
        incremental.material['database']['method'] = 'BINLOG_SQL'
        incremental_code = rejected(incremental.restore_database_settings, 'FULL_DATABASE_SETTINGS_REQUIRED')
        query(target, 'SHOW TABLES FROM `'+database+'`;')
        query(target, 'CREATE TABLE `'+database+'`.nonempty_guard (id INT);')
        nonempty = RealTarget(target, target_uuid, database, archive, source_uuid, root/('nonempty-'+str(index)))
        nonempty_code = rejected(nonempty.restore_database_settings, 'FORMAL_SQL_TARGET_NONEMPTY')
        results.append(dict(archivePin=archive, settingsPin=result_pin, actualSchemaPin=write(root/('actual-schema-'+str(index)+'.json'),actual),
            wrongTarget=wrong_code, incrementalRejected=incremental_code, nonempty=nonempty_code))
        docker(['stop', target])
    write(root/'result.json', dict(state='SUCCEEDED', cases=results,
        scope='Real isolated empty-database observations and settings application; no new application backup.'))
    print(json.dumps(dict(state='SUCCEEDED', cases=results)))
finally:
    for identity in owned:
        row = json.loads(docker(['inspect', identity]))[0]
        require(row['Config']['Labels']['intruoyi.task'] == operation, 'TEST_CLEANUP_OWNER_CHANGED')
        docker(['stop', identity])
