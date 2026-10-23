"""Finite SQL import into an approved empty isolated target, never UI proof.

No target creation, source writes, service switching, SQL repair or replay.
Failed import leaves its intent and partial target for explicit investigation.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import threading
import time
from datetime import datetime, timezone

from formal_capture_producer import read_private
from formal_data_evidence import DataMySql, observe_data, compare_data, read_source_data, validate_limits
from formal_source_migration_ledger import observe_migration_ledger, read_source_ledger, compare_restored_ledger
from formal_filesystem_watchdog import require_native_runtime, WatchdogError
from formal_replica_gate import _private_docker_json, _guarded_run
from formal_s3_export import _strict_json
from formal_snapshot_linux import (FormalSnapshotError, PrivateDockerMySql, require,
                                  _existing_file, _hash_object, _canonical_bytes, _sync_directory, observation_timeout,
                                  observation_deadline)

SHA = re.compile('[0-9a-f]{64}')
UUID = re.compile('[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}')
NAME = re.compile('[A-Za-z_][A-Za-z0-9_-]{0,63}')
SYSTEM_DATABASES = {'information_schema', 'mysql', 'performance_schema', 'sys'}


class IsolatedTargetMySql(DataMySql):
    def _command(self, program, arguments):
        script = ('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
                  'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
                  'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec '+program+' "$@"')
        return ['docker','exec','-i',self.container,'sh','-ec',script,'formal-isolated-mysql',
                '--no-defaults','--protocol=SOCKET',*arguments]


def private_record(root, name, value):
    with (root/name).open('xb') as output:
        os.chmod(output.name, 0o600)
        output.write(_canonical_bytes(value)); output.flush(); os.fsync(output.fileno())
    if os.name == 'posix': _sync_directory(root)


def bound_target(target, operation, *, guard):
    row = _private_docker_json(['inspect', target['containerId']], guard=guard)
    state = row.get('State', {}); host = row.get('HostConfig', {})
    require(row.get('Id') == target['containerId'] and row.get('Image') == target['imageId'] and
            state.get('Running') is True and state.get('Paused') is False and state.get('Restarting') is False and
            host.get('Privileged') is False and host.get('PortBindings') in (None,{}) and
            row.get('Config', {}).get('Labels', {}).get('intruoyi.formal-sql-restore-operation') == operation,
            'FORMAL_SQL_TARGET_CHANGED')
    networks = row.get('NetworkSettings', {}).get('Networks')
    require(target['networkId'] == 'none' and host.get('NetworkMode') == 'none' and
            type(networks) is dict and set(networks) == {'none'} and
            type(networks['none']) is dict and all(networks['none'].get(k) == '' for k in
                ('IPAddress','GlobalIPv6Address','Gateway','IPv6Gateway')),
            'FORMAL_SQL_NETWORK_INVALID')
    mounts = row.get('Mounts', [])
    data = [v for v in mounts if v.get('Destination') == '/var/lib/mysql']
    require(type(mounts) is list and all(v.get('Type') != 'bind' for v in mounts), 'FORMAL_SQL_MOUNT_INVALID')
    if target['dataVolume'] is None:
        require(not data and type(host.get('Tmpfs')) is dict and
                type(host['Tmpfs'].get('/var/lib/mysql')) is str and
                set(host['Tmpfs']['/var/lib/mysql'].split(',')).intersection({'rw'}) == {'rw'} and
                'ro' not in host['Tmpfs']['/var/lib/mysql'].split(','), 'FORMAL_SQL_MOUNT_INVALID')
    else:
        require(len(data) == 1 and data[0].get('Type') == 'volume' and data[0].get('Name') == target['dataVolume'],
                'FORMAL_SQL_MOUNT_INVALID')
        volume = _private_docker_json(['volume', 'inspect', target['dataVolume']], guard=guard)
        require(volume.get('Name') == target['dataVolume'] and volume.get('Driver') == 'local' and
                volume.get('Options') in (None, {}) and
                volume.get('Labels', {}).get('intruoyi.formal-sql-restore-operation') == operation and
                volume.get('Mountpoint') == data[0].get('Source'), 'FORMAL_SQL_MOUNT_INVALID')
        try:
            result = _guarded_run(['docker','ps','--all','--no-trunc','--format','{{.ID}}'],
                guard=guard, timeout=30, code='FORMAL_SQL_VOLUME_INVENTORY_FAILED')
        except (OSError, subprocess.TimeoutExpired):
            raise FormalSnapshotError('FORMAL_SQL_VOLUME_INVENTORY_FAILED') from None
        require(result.returncode == 0, 'FORMAL_SQL_VOLUME_INVENTORY_FAILED')
        ids = result.stdout.decode('ascii').splitlines()
        require(target['containerId'] in ids and len(ids) == len(set(ids)) and
                all(SHA.fullmatch(v) for v in ids), 'FORMAL_SQL_VOLUME_INVENTORY_FAILED')
        for identity in ids:
            if identity != target['containerId']:
                other = _private_docker_json(['inspect', identity], guard=guard)
                require(other.get('Id') == identity and all(v.get('Name') != target['dataVolume'] and
                        v.get('Source') != data[0]['Source'] for v in other.get('Mounts', [])),
                        'FORMAL_SQL_VOLUME_SHARED')


def database_state(mysql, target):
    observed = mysql.query('SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only, '
                          '(SELECT COUNT(*) FROM information_schema.innodb_trx), @@GLOBAL.event_scheduler;')
    require(observed in (target['databaseUuid']+'\t0\t0\t0\tOFF\n',
                         target['databaseUuid']+'\t0\t0\t0\tDISABLED\n'), 'FORMAL_SQL_DATABASE_CHANGED')
    databases = mysql.query('SHOW DATABASES;').splitlines()
    require(len(databases) == len(set(databases)) and target['database'] in databases and
            set(databases) == SYSTEM_DATABASES | {target['database']}, 'FORMAL_SQL_DATABASE_SCOPE_INVALID')


def import_database_state(mysql, target):
    """Current import identity; the importer's own transactions are permitted.

    This is not writer exclusion. The complete pre/post-import state check still
    requires zero transactions; target isolation and source checks stay separate.
    """
    observed = mysql.query('SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only, '
                           '@@GLOBAL.event_scheduler;')
    require(observed in (target['databaseUuid']+'\t0\t0\tOFF\n',
                         target['databaseUuid']+'\t0\t0\tDISABLED\n'), 'FORMAL_SQL_DATABASE_CHANGED')


def empty_database(mysql, target):
    require(mysql.query('SHOW FULL TABLES FROM `'+target['database']+'`;') == '', 'FORMAL_SQL_TARGET_NONEMPTY')
    name=target['database']
    counts=mysql.query("SELECT (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema='"+name+
        "'), (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='"+name+
        "'), (SELECT COUNT(*) FROM information_schema.events WHERE event_schema='"+name+"');")
    require(counts == '0\t0\t0\n', 'FORMAL_SQL_TARGET_NONEMPTY')


def expand_checked(source, destination, expected_digest, max_bytes, seconds):
    deadline = time.monotonic()+seconds
    path = _existing_file(source); before = path.stat()
    require(os.name != 'posix' or stat.S_IMODE(before.st_mode) == 0o600, 'FORMAL_SQL_SOURCE_NOT_PRIVATE')
    # ponytail: lightweight expands directly; gzip decoding errors still fail.
    expanded_sha = hashlib.sha256(); total = 0
    with path.open('rb') as raw, destination.open('xb') as output:
        os.chmod(destination, 0o600)
        with gzip.GzipFile(fileobj=raw, mode='rb') as compressed:
            while True:
                require(time.monotonic() < deadline, 'FORMAL_SQL_EXPANSION_TIMEOUT')
                chunk = compressed.read(min(1024*1024, max_bytes-total+1))
                if not chunk: break
                total += len(chunk); require(total <= max_bytes, 'FORMAL_SQL_EXPANSION_LIMIT')
                output.write(chunk); expanded_sha.update(chunk)
        output.flush(); os.fsync(output.fileno())
    return expanded_sha.hexdigest(), total


def stream_import(mysql, expanded, expected_sha, seconds, *, database, guard=None):
    require(type(database) is str and NAME.fullmatch(database), 'FORMAL_SQL_DATABASE_INVALID')
    require(callable(guard), 'FORMAL_SQL_IMPORT_GUARD_REQUIRED')
    require(type(seconds) is int and 0 < seconds <= 7200, 'FORMAL_SQL_IMPORT_TIMEOUT_INVALID')
    deadline = time.monotonic()+observation_timeout(seconds)
    def current():
        require(time.monotonic() < deadline, 'FORMAL_SQL_IMPORT_TIMEOUT')
        token = observation_deadline.set(min(deadline, time.monotonic()+5))
        try: guard()
        finally: observation_deadline.reset(token)
        require(time.monotonic() < deadline, 'FORMAL_SQL_IMPORT_TIMEOUT')
    current()
    # The deadline covers both a blocked stdin writer and process completion.
    command = mysql._command('timeout --signal=TERM --kill-after=5 '+str(seconds)+'s mysql',
                             ['-uroot','--binary-mode=1','--default-character-set=utf8mb4',database])
    shell = command.index('sh')+2
    require(command[shell-2:shell] == ['sh','-ec'], 'FORMAL_SQL_IMPORT_COMMAND_INVALID')
    # The remote shell, not a possibly disconnected Docker client, confirms exit.
    command[shell] = ('set +e; (set -e; '+command[shell]+') >/dev/null; recovery_exit=$?; '
        'printf "RECOVERY_SQL_EXIT=%s\\n" "$recovery_exit"; exit "$recovery_exit"')
    # Missing coreutils timeout is a hard failure, and a timed-out Docker client
    # is never interpreted as confirmation that the remote importer stopped.
    errors = []; aborted = threading.Event(); requested = threading.Event(); permitted = threading.Event()
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        raise FormalSnapshotError('FORMAL_SQL_IMPORT_UNAVAILABLE') from None
    def send():
        try:
            def write(raw):
                requested.set()
                # Only the owner/main thread executes guard and permits one
                # next write. A blocked pipe never blocks current observations.
                while not permitted.wait(.05):
                    if aborted.is_set(): return False
                permitted.clear()
                if aborted.is_set(): return False
                process.stdin.write(raw)
                return True
            with expanded.open('rb') as source:
                if not write((mysql._password+'\n').encode()): return
                while True:
                    chunk = source.read(1024*1024)
                    if not chunk: break
                    if not write(chunk): return
        except Exception as error:
            errors.append(error)
        finally:
            try: process.stdin.close()
            except OSError as error: errors.append(error)
    writer = threading.Thread(target=send, daemon=True); writer.start()
    try:
        while process.poll() is None or writer.is_alive():
            current()
            if errors: break
            if requested.is_set():
                requested.clear(); permitted.set()
            # Wake as soon as the writer requests the next block. Waiting on
            # the long-lived mysql process imposed 50 ms on every MiB.
            requested.wait(timeout=min(.05, max(.001, deadline-time.monotonic())))
            if process.poll() is not None and writer.is_alive():
                writer.join(timeout=.05)
        current()
    except BaseException:
        aborted.set(); permitted.set()
        if process.poll() is None: process.kill()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            raise FormalSnapshotError('FORMAL_SQL_IMPORT_CLIENT_TERMINATION_UNCERTAIN') from None
        writer.join(timeout=5)
        require(not writer.is_alive(), 'FORMAL_SQL_IMPORT_WRITER_UNCERTAIN')
        raise
    aborted.set(); permitted.set()
    if errors and process.poll() is None: process.kill()
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        raise FormalSnapshotError('FORMAL_SQL_IMPORT_CLIENT_TERMINATION_UNCERTAIN') from None
    writer.join(timeout=5); require(not writer.is_alive(), 'FORMAL_SQL_IMPORT_WRITER_UNCERTAIN')
    if errors:
        if isinstance(errors[0], FormalSnapshotError): raise errors[0]
        raise FormalSnapshotError('FORMAL_SQL_IMPORT_STREAM_FAILED') from None
    acknowledgement = process.stdout.read(128)
    confirmed = acknowledgement == ('RECOVERY_SQL_EXIT='+str(process.returncode)+'\n').encode()
    if process.returncode != 0 or not confirmed:
        error = FormalSnapshotError('FORMAL_SQL_IMPORT_FAILED' if confirmed else 'FORMAL_SQL_IMPORT_EXIT_UNPROVEN')
        error.unknown = not confirmed or process.returncode in (124, 137, 143)
        raise error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    args = parser.parse_args(argv); evidence = None; stage = 'PREFLIGHT'
    try:
        require_native_runtime()
        require(SHA.fullmatch(args.expected_request_sha256), 'FORMAL_SQL_REQUEST_APPROVAL_REQUIRED')
        raw = read_private(args.request, 16384)
        require(hashlib.sha256(raw).hexdigest() == args.expected_request_sha256, 'FORMAL_SQL_REQUEST_CHANGED')
        request = _strict_json(raw)
        require(type(request) is dict and request.get('schemaVersion') in
            ('release-formal-sql-restore-request/v1','release-formal-sql-restore-request/v2'),'FORMAL_SQL_REQUEST_INVALID')
        source_aware=request['schemaVersion']=='release-formal-sql-restore-request/v2'
        fields={'schemaVersion','operationId','sourceCapture',
                'sourceCaptureReceiptSha256','sourceSqlSha256','sourceDatabaseUuid','sourceClaimBindingSha256','evidenceRoot',
                'maxExpandedBytes','timeoutSeconds','dataLimits','target'}
        if source_aware:fields.add('sourceScope')
        require(set(request) == fields and
                type(request['operationId']) is str and re.fullmatch('[A-Za-z0-9_-]{1,128}',request['operationId']) and
                all(type(request[k]) is str and request[k] for k in ('sourceCapture','evidenceRoot')) and
                all(type(request[k]) is str and SHA.fullmatch(request[k]) for k in
                    ('sourceCaptureReceiptSha256','sourceSqlSha256','sourceClaimBindingSha256')) and
                type(request['sourceDatabaseUuid']) is str and UUID.fullmatch(request['sourceDatabaseUuid']) and
                type(request['timeoutSeconds']) is int and 0 < request['timeoutSeconds'] <= 7200 and
                type(request['maxExpandedBytes']) is int and 0 < request['maxExpandedBytes'] <= 1024**4,
                'FORMAL_SQL_REQUEST_INVALID')
        data_limits=validate_limits(request['dataLimits'])
        target = request['target']
        require(type(target) is dict and set(target) == {'containerId','imageId','database','databaseUuid',
                'credentialFile','networkId','dataVolume'} and
                all(type(target[k]) is str for k in ('containerId','imageId','database','databaseUuid','credentialFile','networkId')) and
                SHA.fullmatch(target['containerId']) and re.fullmatch('sha256:[0-9a-f]{64}',target['imageId']) and
                NAME.fullmatch(target['database']) and target['database'] not in SYSTEM_DATABASES and
                UUID.fullmatch(target['databaseUuid']) and target['databaseUuid'] != request['sourceDatabaseUuid'] and
                target['networkId'] == 'none' and
                (target['dataVolume'] is None or type(target['dataVolume']) is str and
                 re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',target['dataVolume'])), 'FORMAL_SQL_TARGET_INVALID')
        source = Path(request['sourceCapture']).absolute()
        source_binding_raw=read_private(source.parent/'binding.json',16384)
        source_binding=_strict_json(source_binding_raw)
        require(hashlib.sha256(source_binding_raw).hexdigest() == request['sourceClaimBindingSha256'] and
                type(source_binding) is dict and source_binding.get('databaseUuid') == request['sourceDatabaseUuid'] and
                type(source_binding.get('sourceFingerprint')) is str and SHA.fullmatch(source_binding['sourceFingerprint']),
                'FORMAL_SQL_SOURCE_BINDING_CHANGED')
        capture_raw = read_private(source/'040-payload.json', 1024*1024)
        capture = _strict_json(capture_raw)
        require(hashlib.sha256(capture_raw).hexdigest() == request['sourceCaptureReceiptSha256'] and
                type(capture) is dict and capture.get('state') == 'CAPTURED_PENDING_FULL_BARRIER_PROOF' and
                capture.get('database',{}).get('sha256') == request['sourceSqlSha256'] and
                _hash_object(source/'database.sql.gz') == ('sha256:'+request['sourceSqlSha256'],capture['database'].get('bytes')),
                'FORMAL_SQL_SOURCE_CHANGED')
        source_data,source_files=read_source_data(source,source_binding_raw,request['sourceSqlSha256'],
                                                capture.get('sourceDataEvidence'))
        if source_aware:
            require(type(request['sourceScope']) is dict and request['sourceScope'] == capture.get('sourceScope'),
                'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
            source_ledger,source_ledger_files=read_source_ledger(source,source_binding_raw,request['sourceSqlSha256'],
                capture.get('sourceMigrationEvidence'),source_data,request['sourceScope'])
        else:
            require('sourceScope' not in capture and 'sourceMigrationEvidence' not in capture,
                'FORMAL_SQL_EXPLICIT_SOURCE_ROUTE_REQUIRED')
        require(source_data['schema']['database']==target['database'], 'FORMAL_SQL_SOURCE_DATABASE_CHANGED')
        def source_guard():
            require(read_private(args.request,16384)==raw and
                read_private(source/'040-payload.json',1024*1024)==capture_raw and
                read_private(source.parent/'binding.json',16384)==source_binding_raw,
                'FORMAL_SQL_SOURCE_CHANGED')
            require(read_source_data(source,source_binding_raw,request['sourceSqlSha256'],
                capture['sourceDataEvidence'])[1]==source_files,'FORMAL_DATA_SOURCE_CHANGED')
            if source_aware:
                require(read_source_ledger(source,source_binding_raw,request['sourceSqlSha256'],
                    capture['sourceMigrationEvidence'],source_data,request['sourceScope'])[1]==source_ledger_files,
                    'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
        bound_target(target, request['operationId'], guard=source_guard)
        credential = read_private(target['credentialFile'],16384).decode('utf-8')
        require(credential.endswith('\n') and credential.count('\n') == 1, 'FORMAL_SQL_CREDENTIAL_INVALID')
        mysql = IsolatedTargetMySql(target['containerId'],credential[:-1],timeout=request['timeoutSeconds'])
        def target_guard():
            bound_target(target,request['operationId'],guard=source_guard);database_state(mysql,target)
            source_guard()
        def import_guard():
            source_guard();bound_target(target,request['operationId'],guard=source_guard);import_database_state(mysql,target)
            source_guard()
        database_state(mysql,target)
        empty_database(mysql,target)
        root = Path(request['evidenceRoot']).absolute()
        for parent in root.parents:
            require(parent.is_dir() and not parent.is_symlink() and parent.resolve() == parent, 'FORMAL_SQL_EVIDENCE_INVALID')
        require(not root.exists() and not root.is_symlink(), 'FORMAL_SQL_EVIDENCE_EXISTS')
        root.mkdir(mode=0o700); evidence = root
        if os.name == 'posix': _sync_directory(root.parent)
        stage = 'EXPANSION'
        expanded = root/'expanded.sql'
        expanded_sha, expanded_bytes = expand_checked(source/'database.sql.gz',expanded,request['sourceSqlSha256'],
            request['maxExpandedBytes'],request['timeoutSeconds'])
        require(read_private(args.request,16384) == raw and read_private(source/'040-payload.json',1024*1024) == capture_raw,
                'FORMAL_SQL_REQUEST_CHANGED')
        bound_target(target,request['operationId'],guard=source_guard); database_state(mysql,target)
        empty_database(mysql,target)
        source_guard()
        private_record(root,'010-import-intent.json',{'operationId':request['operationId'],
            'requestSha256':args.expected_request_sha256,'sourceSqlSha256':request['sourceSqlSha256'],
            'targetContainerId':target['containerId'],'targetDatabaseUuid':target['databaseUuid'],
            'expandedSqlSha256':expanded_sha,'expandedBytes':expanded_bytes})
        stage = 'IMPORT'
        stream_import(mysql,expanded,expanded_sha,request['timeoutSeconds'],database=target['database'],guard=import_guard)
        stage = 'READBACK'
        target_guard()
        target_data=observe_data(mysql,target['database'],target['databaseUuid'],guard=target_guard,
                                 scratch=root/'target-data',**data_limits)
        require(target_data['observationIdentity']=={'containerId':target['containerId'],
            'databaseUuid':target['databaseUuid']},'FORMAL_SQL_TARGET_CHANGED')
        private_record(root,'020-target-data.json',target_data)
        comparison=compare_data(source_data,target_data)
        private_record(root,'030-data-comparison.json',comparison)
        if source_aware:
            target_ledger=observe_migration_ledger(mysql,target['database'],target['databaseUuid'],
                source_environment=request['sourceScope']['environment'],full_data=target_data,
                guard=target_guard,max_rows=data_limits['max_rows'])
            ledger_comparison=compare_restored_ledger(source_ledger,target_ledger)
            private_record(root,'024-target-migration-ledger.json',target_ledger)
            private_record(root,'035-migration-comparison.json',ledger_comparison)
            target_ledger_bytes=_canonical_bytes(target_ledger);ledger_comparison_bytes=_canonical_bytes(ledger_comparison)
        target_bytes=_canonical_bytes(target_data);comparison_bytes=_canonical_bytes(comparison)
        tables=[{'name':name,'type':kind,**({'rows':target_data['tables'][name]['rows']}
                if kind=='BASE TABLE' else {})} for name,kind in target_data['schema']['catalog']['TABLES']]
        target_guard()
        require(_hash_object(expanded)[0] == 'sha256:'+expanded_sha and
                _hash_object(source/'database.sql.gz')[0] == 'sha256:'+request['sourceSqlSha256'] and
                read_private(args.request,16384) == raw and read_private(source/'040-payload.json',1024*1024) == capture_raw and
                read_private(source.parent/'binding.json',16384) == source_binding_raw,
                'FORMAL_SQL_SOURCE_CHANGED')
        require(read_private(root/'020-target-data.json',64*1024*1024)==target_bytes and
                read_private(root/'030-data-comparison.json',64*1024*1024)==comparison_bytes,
                'FORMAL_SQL_TARGET_EVIDENCE_CHANGED')
        if source_aware:
            require(read_private(root/'024-target-migration-ledger.json',64*1024*1024)==target_ledger_bytes and
                read_private(root/'035-migration-comparison.json',16384)==ledger_comparison_bytes,
                'FORMAL_SOURCE_LEDGER_TARGET_EVIDENCE_CHANGED')
        receipt = {'schemaVersion':'release-formal-sql-restore/v2' if source_aware else 'release-formal-sql-restore/v1','state':'SQL_RESTORED_PENDING_APPLICATION_PROOF',
            'operationId':request['operationId'],'requestSha256':args.expected_request_sha256,
            'sourceCaptureReceiptSha256':request['sourceCaptureReceiptSha256'],'sourceSqlSha256':request['sourceSqlSha256'],
            'sourceClaimBindingSha256':request['sourceClaimBindingSha256'],'sourceFingerprint':source_binding['sourceFingerprint'],
            'sourceDatabaseUuid':request['sourceDatabaseUuid'],'targetContainerId':target['containerId'],
            'targetDatabaseUuid':target['databaseUuid'],'targetDatabase':target['database'],
            'sourceDataEvidence':capture['sourceDataEvidence'],
            'sourceObservationSha256':source_data['observationSha256'],
            'targetObservationSha256':target_data['observationSha256'],'schemaSha256':comparison['schemaSha256'],
            'schemaComparisonEncoding':comparison['schemaComparisonEncoding'],
            'sourceSchemaSha256':comparison['sourceSchemaSha256'],'targetSchemaSha256':comparison['targetSchemaSha256'],
            'canonicalSchemaSha256':comparison['canonicalSchemaSha256'],
            'targetDataFileSha256':hashlib.sha256(target_bytes).hexdigest(),
            'dataComparisonFileSha256':hashlib.sha256(comparison_bytes).hexdigest(),
            'expandedSqlSha256':expanded_sha,'expandedBytes':expanded_bytes,'tables':sorted(tables,key=lambda v:v['name']),
            'restoredAt':datetime.now(timezone.utc).isoformat(),'fullSchemaDataEquivalenceVerified':True,
            'applicationVerified':False,'productionEvidence':False}
        if source_aware:
            receipt.update(sourceScope=request['sourceScope'],sourceMigrationEvidence=capture['sourceMigrationEvidence'],
                sourceMigrationObservationSha256=source_ledger['observationSha256'],
                targetMigrationObservationSha256=target_ledger['observationSha256'],
                targetMigrationFileSha256=hashlib.sha256(target_ledger_bytes).hexdigest(),
                migrationComparisonFileSha256=hashlib.sha256(ledger_comparison_bytes).hexdigest())
        private_record(root,'restore-receipt.json',receipt)
        print(json.dumps(receipt)); return 0
    except Exception as error:
        code = getattr(error,'code','FORMAL_SQL_RESTORE_ENTRY_FAILED')
        if type(code) is not str or not re.fullmatch('(?:FORMAL|WATCHDOG)_[A-Z_]+',code): code = 'FORMAL_SQL_RESTORE_ENTRY_FAILED'
        result = {'state':'FAILED_RETAINED','code':code,'stage':stage,'productionEvidence':False,
                  'targetReconciliationRequired':stage in ('IMPORT','READBACK'),
                  'remoteImportStopConfirmed':False}
        if evidence is not None:
            try: private_record(evidence,'900-failed.json',result)
            except OSError: result['code'] = 'FORMAL_SQL_FAILURE_JOURNAL_FAILED'
        print(json.dumps(result)); return 1


if __name__ == '__main__':
    raise SystemExit(main())
