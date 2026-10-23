"""Finite split capture for a database sharing the raw-copy filesystem.

SQL is captured while queryable; raw capture requires all explicitly bound
shared workloads stopped. Neither phase changes services or restores flags.
An external caller exclusion guard is mandatory but does not by itself prove
the complete six-writer contract; outputs remain pending that full proof.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import formal_snapshot_linux as snapshot
from formal_data_evidence import DataMySql, observe_data, source_binding, read_source_data, validate_limits
from formal_source_migration_ledger import observe_migration_ledger, bind_migration_ledger, read_source_ledger

ROLES = {'mysql','frontend','backend','showroom','onlyoffice','redis','minio'}
STOP_ORDER = ('frontend','backend','showroom','onlyoffice','redis','minio','mysql')
RESTORE_ORDER = ('mysql','redis','minio','onlyoffice','showroom','backend','frontend')


def _observe_source_ledger(mysql, database, uuid, *, source_scope, full_data, guard, max_rows):
    if source_scope['schemaVersion'] == 'backup-lab-source-scope/v1':
        from formal_source_migration_ledger import observe_lab_migration_ledger
        return observe_lab_migration_ledger(mysql,database,uuid,source_scope=source_scope,
            full_data=full_data,guard=guard,max_rows=max_rows)
    snapshot.require(source_scope['schemaVersion'] == 'release-formal-approved-source/v1',
                     'FORMAL_SOURCE_LEDGER_BINDING_CHANGED')
    return observe_migration_ledger(mysql,database,uuid,source_environment=source_scope['environment'],
        full_data=full_data,guard=guard,max_rows=max_rows)


def _event(claim, step):
    claim.assert_owned()
    events = [event for event in claim.events if event['step'] == step]
    snapshot.require(len(events) == 1, 'FORMAL_SPLIT_STAGE_REQUIRED')
    return events[0]['details']


def _active(claim, forbidden):
    claim.assert_owned()
    snapshot.require(not any(event['step'] in forbidden or
        event['step'].endswith('-restore-intent') or event['step'].endswith('-restored') or
        event['step'] in ('released','failed-retained','capture-intent','captured','shared-recovery-intent',
                         'ingress-recovery-intent','ingress-recovery-permitted')
        for event in claim.events), 'FORMAL_SPLIT_STAGE_INVALID')


def _record(root, name, value):
    from formal_capture_budget import active_budget
    budget=active_budget.get()
    path = snapshot.safe_file(root/name)
    raw = snapshot._canonical_bytes(value)
    with (path.open('xb') if budget is None else budget.open(path,'proof')) as output:
        os.chmod(path, 0o600)
        output.write(raw); output.flush(); os.fsync(output.fileno())
    if os.name == 'posix': snapshot._sync_directory(root)
    return hashlib.sha256(raw).hexdigest()


def _failure(root, name, error):
    code = getattr(error, 'code', 'FORMAL_SPLIT_UNEXPECTED_FAILURE')
    if not (type(code) is str and re.fullmatch('(?:FORMAL|WATCHDOG)_[A-Z_]+', code)):
        code = 'FORMAL_SPLIT_UNEXPECTED_FAILURE'
    _record(root, name, {'state':'FAILED_RETAINED','code':code,'productionEvidence':False})


def bind_shared_container_scope(claim, roles):
    """Record exact original state before any shared-device service action."""
    _active(claim, {'shared-container-scope','split-sql-intent','split-raw-intent'})
    snapshot.require(type(roles) is dict and set(roles) == ROLES and
        all(type(identity) is str and re.fullmatch('[0-9a-f]{64}', identity)
            for identity in roles.values()) and len(set(roles.values())) == len(roles),
        'FORMAL_SPLIT_SHARED_SCOPE_INVALID')
    binding = json.loads(claim._plan)
    snapshot.require(roles['minio'] == binding['minioContainerId'], 'FORMAL_SPLIT_MINIO_CHANGED')
    records = {}
    for role, identity in sorted(roles.items()):
        row = snapshot.inspect_formal_container(identity)
        snapshot._container_stable(row)
        snapshot.require(row['id'] == identity, 'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
        records[role] = row
    raw = snapshot._canonical_bytes(records)
    snapshot.require(len(raw) <= 16384, 'FORMAL_SPLIT_SHARED_SCOPE_INVALID')
    claim._write(snapshot.safe_file(claim.root/'shared-container-original.json'), raw)
    claim.record('shared-container-scope', {'scopeSha256':hashlib.sha256(raw).hexdigest()})
    return records


def _scope(claim, *, stopped):
    expected = _event(claim, 'shared-container-scope')
    raw = claim._read(claim.root/'shared-container-original.json')
    snapshot.require(expected == {'scopeSha256':hashlib.sha256(raw).hexdigest()},
                     'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    originals = json.loads(raw)
    snapshot.require(type(originals) is dict and set(originals) == ROLES and
        raw == snapshot._canonical_bytes(originals), 'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    current = {}
    for role, original in sorted(originals.items()):
        row = snapshot.inspect_formal_container(original['id'])
        snapshot.require(snapshot._container_stable(row) == snapshot._container_stable(original),
                         'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
        if stopped:
            state = row['state']
            snapshot.require(state['Running'] is False and state['ExitCode'] == 0 and
                state['StartedAt'] == original['state']['StartedAt'] and
                (state['FinishedAt'] != original['state']['FinishedAt'] if original['state']['Running']
                 else state == original['state']), 'FORMAL_SPLIT_SHARED_NOT_STOPPED')
        elif role == 'mysql':
            snapshot.require(row['state']['Running'] is True and
                row['state']['StartedAt'] == original['state']['StartedAt'], 'FORMAL_SPLIT_MYSQL_CHANGED')
        current[role] = row
    snapshot.require(originals['minio']['id'] == json.loads(claim._plan)['minioContainerId'],
                     'FORMAL_SPLIT_MINIO_CHANGED')
    claim.assert_owned()
    return originals, current, expected['scopeSha256']


def _probe_result(result, database, table, column, started, finished):
    snapshot.require(type(result) is dict and set(result)==
        {'result','mysqlErrorNumber','statementSha256','observedAt'} and
        result['result']=='REJECTED' and type(result['mysqlErrorNumber']) is int and
        result['mysqlErrorNumber']==1290, 'FORMAL_SPLIT_REJECTION_NOT_PROVEN')
    statement='UPDATE `'+database+'`.`'+table+'` SET `'+column+'`=`'+column+'` WHERE 1=0;'
    snapshot.require(result['statementSha256']==hashlib.sha256(statement.encode()).hexdigest(),
        'FORMAL_SPLIT_REJECTION_STATEMENT_CHANGED')
    try:
        observed=datetime.fromisoformat(result['observedAt'])
        valid=observed.tzinfo is not None and started<=observed<=finished
    except (ValueError,TypeError):valid=False
    snapshot.require(valid,'FORMAL_SPLIT_REJECTION_TIME_INVALID')


def _split_rejection(claim,mysql,database,probe,phase,sql_sha,scope_sha,guard):
    step='split-db-probe-'+phase
    _active(claim,{step,step+'-intent','split-sql-captured','split-raw-intent','split-captured'})
    binding=json.loads(claim._plan)
    scope={'phase':phase,'database':database,**probe,'operationId':binding['operationId'],
        'sourceFingerprint':binding['sourceFingerprint'],'databaseUuid':binding['databaseUuid'],
        'claimBindingSha256':hashlib.sha256(claim._plan).hexdigest(),
        'mysqlContainerId':mysql.container,'sharedScopeSha256':scope_sha,'sqlSha256':sql_sha}
    guard();observe_split_sql_barrier(claim,mysql)
    claim.record(step+'-intent',scope)
    guard();observe_split_sql_barrier(claim,mysql)
    started=datetime.now(timezone.utc)
    result=mysql.probe_rejected_zero_row_update(database,probe['table'],probe['column'])
    finished=datetime.now(timezone.utc)
    _probe_result(result,database,probe['table'],probe['column'],started,finished)
    guard();observe_split_sql_barrier(claim,mysql)
    receipt={**scope,'probe':result,'startedAt':started.isoformat(),'finishedAt':finished.isoformat(),
        'state':'DATABASE_REJECTED_PENDING_HOST_OBJECT_PROOF'}
    digest=_record(claim.root/'payload',
        ('006' if phase=='before' else '018')+'-database-rejection-'+phase+'.json',receipt)
    guard();observe_split_sql_barrier(claim,mysql)
    claim.record(step,{'receiptSha256':digest})
    return digest


def _read_rejections(claim,sql):
    refs=sql.get('databaseRejectionEvidence');binding=json.loads(claim._plan)
    snapshot.require(type(refs) is dict and set(refs)=={'beforeSha256','afterSha256'},
        'FORMAL_SPLIT_REJECTION_REQUIRED')
    intent=_event(claim,'split-sql-intent')
    for phase,number in (('before','006'),('after','018')):
        path=snapshot._existing_file(claim.root/('payload/'+number+'-database-rejection-'+phase+'.json'))
        snapshot.require(path.stat().st_size<=16384 and (os.name!='posix' or
            stat.S_IMODE(path.stat().st_mode)==0o600),'FORMAL_SPLIT_REJECTION_CHANGED')
        raw=path.read_bytes();value=json.loads(raw);step='split-db-probe-'+phase
        digest=hashlib.sha256(raw).hexdigest()
        scope={'phase':phase,'database':intent['database'],**intent['rejectionProbe'],
            'operationId':binding['operationId'],'sourceFingerprint':binding['sourceFingerprint'],
            'databaseUuid':binding['databaseUuid'],'claimBindingSha256':hashlib.sha256(claim._plan).hexdigest(),
            'mysqlContainerId':intent['mysqlContainerId'],'sharedScopeSha256':intent['sharedScopeSha256'],
            'sqlSha256':None if phase=='before' else sql['database']['sha256']}
        snapshot.require(type(value) is dict and set(value)==set(scope)|{'probe','startedAt','finishedAt','state'} and
            raw==snapshot._canonical_bytes(value) and digest==refs[phase+'Sha256'] and
            _event(claim,step)=={'receiptSha256':digest} and _event(claim,step+'-intent')==scope and
            all(value[k]==v for k,v in scope.items()) and value['state']=='DATABASE_REJECTED_PENDING_HOST_OBJECT_PROOF',
            'FORMAL_SPLIT_REJECTION_CHANGED')
        try:
            started=datetime.fromisoformat(value['startedAt']);finished=datetime.fromisoformat(value['finishedAt'])
        except (ValueError,TypeError):
            raise snapshot.FormalSnapshotError('FORMAL_SPLIT_REJECTION_TIME_INVALID') from None
        _probe_result(value['probe'],scope['database'],scope['table'],scope['column'],started,finished)


def capture_sql_phase(claim, mysql, database, source_root, *, guard, data_limits, rejection_probe, source_scope=None):
    snapshot.require(callable(guard) and type(database) is str and
        re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',database), 'FORMAL_SPLIT_INPUT_INVALID')
    _active(claim, {'split-sql-intent','split-sql-captured','split-raw-intent','split-captured'})
    snapshot.require(type(rejection_probe) is dict and set(rejection_probe)=={'table','column'} and
        all(type(v) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',v)
            for v in rejection_probe.values()),'FORMAL_SPLIT_REJECTION_SCOPE_INVALID')
    limits=validate_limits(data_limits)
    originals, _, scope_sha = _scope(claim, stopped=False)
    snapshot.require(mysql.container == originals['mysql']['id'], 'FORMAL_SPLIT_MYSQL_CHANGED')
    source = Path(source_root).absolute()
    snapshot.require(source.is_dir() and not source.is_symlink() and source.resolve() == source,
                     'FORMAL_SPLIT_SOURCE_INVALID')
    guard(); observe_split_sql_barrier(claim, mysql)
    target = snapshot.safe_file(claim.root/'payload')
    snapshot.require(source != target and source not in target.parents and target not in source.parents,
                     'FORMAL_SPLIT_DESTINATION_INVALID')
    intent = {'database':database,'sourceRoot':str(source),
        'mysqlContainerId':mysql.container,'sharedScopeSha256':scope_sha,'dataLimits':limits,
        'rejectionProbe':rejection_probe}
    # v12 explicitly carries approved source authority; legacy finite phases do
    # not claim a source ledger and cannot qualify for normal backup deployment.
    if source_scope is not None:
        lab = source_scope.get('schemaVersion') == 'backup-lab-source-scope/v1' if type(source_scope) is dict else False
        if lab:
            from formal_backup_lab import require_authority
            require_authority(source_scope)
        snapshot.require(type(source_scope) is dict and source_scope.get('database') == database and
            source_scope.get('databaseUuid') == json.loads(claim._plan)['databaseUuid'] and
            source_scope.get('targetFingerprint') == json.loads(claim._plan)['sourceFingerprint'] and
            source_scope.get('environment') == ('backup-lab' if lab else 'prod'), 'FORMAL_SOURCE_LEDGER_BINDING_CHANGED')
        intent['sourceScope'] = source_scope
    claim.record('split-sql-intent', intent)
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    if output_budget is None:target.mkdir(mode=0o700)
    else:output_budget.mkdir(target)
    if os.name == 'posix': snapshot._sync_directory(target.parent)
    try:
        _record(target, '010-sql-started.json', {'state':'SQL_CAPTURING','sharedScopeSha256':scope_sha})
        def data_guard():
            _active(claim,set())
            guard()
            _active(claim,set())
            observe_split_sql_barrier(claim, mysql)
            _active(claim,set())
        before_rejection=_split_rejection(claim,mysql,database,rejection_probe,'before',None,scope_sha,guard)
        data_mysql=DataMySql(mysql.container,mysql._password,timeout=mysql.timeout)
        uuid=json.loads(claim._plan)['databaseUuid']
        before=observe_data(data_mysql,database,uuid,guard=data_guard,scratch=target/'source-before',**limits)
        snapshot.require(before['observationIdentity']=={'containerId':mysql.container,'databaseUuid':uuid} and
            before['schema']['database']==database,'FORMAL_DATA_SOURCE_CHANGED')
        _record(target,'011-source-data.json',before)
        if source_scope is not None:
            ledger_before=_observe_source_ledger(data_mysql,database,uuid,source_scope=source_scope,
                full_data=before,guard=data_guard,max_rows=limits['max_rows'])
            _record(target,'013-source-migration-ledger.json',ledger_before)
        data_guard()
        def dump_guard():
            _active(claim,set());guard();_active(claim,set())
            observe_split_sql_barrier(claim,mysql,dump_in_progress=True)
            _active(claim,set())
        from formal_capture_incremental import active_series
        series = active_series.get()
        if series is None:
            dump = mysql.dump(database, target/'database.sql.gz',guard=dump_guard)
        else:
            series_guard = data_guard if series.spec['pointType'] == 'INCREMENTAL' else dump_guard
            dump = series.database(mysql, database, target/'database.sql.gz', guard=series_guard)
        digest, size = snapshot._hash_object(target/'database.sql.gz',guard=data_guard)
        snapshot.require(type(dump) is dict and dump == {'sha256':digest[7:],'bytes':size},
                         'FORMAL_SPLIT_SQL_DIGEST_CHANGED')
        data_guard()
        after=observe_data(data_mysql,database,uuid,guard=data_guard,scratch=target/'source-after',**limits)
        _record(target,'012-source-data-after.json',after)
        if source_scope is not None:
            ledger_after=_observe_source_ledger(data_mysql,database,uuid,source_scope=source_scope,
                full_data=after,guard=data_guard,max_rows=limits['max_rows'])
            _record(target,'014-source-migration-ledger-after.json',ledger_after)
            ledger_binding=bind_migration_ledger(claim._plan,ledger_before,ledger_after,dump['sha256'],source_scope)
            ledger_sha=_record(target,'016-source-migration-binding.json',ledger_binding)
            ledger_reference={'bindingSha256':ledger_sha,'ledgerObservationSha256':ledger_before['observationSha256']}
            read_source_ledger(target,claim._plan,dump['sha256'],ledger_reference,before,source_scope)
        binding=source_binding(claim._plan,before,after,dump['sha256'])
        binding_sha=_record(target,'015-source-data-binding.json',binding)
        reference={'bindingSha256':binding_sha,'sourceObservationSha256':before['observationSha256']}
        read_source_data(target,claim._plan,dump['sha256'],reference)
        after_rejection=_split_rejection(claim,mysql,database,rejection_probe,'after',dump['sha256'],scope_sha,guard)
        data_guard()
        snapshot.require(_scope(claim, stopped=False)[2] == scope_sha, 'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
        result = {'state':'SQL_CAPTURED_PENDING_RAW_AND_FULL_BARRIERS','database':dump,
            'sourceRoot':str(source),'mysqlContainerId':mysql.container,'sharedScopeSha256':scope_sha,
            'databaseUuid':uuid,'sourceDataEvidence':reference,
            'databaseRejectionEvidence':{'beforeSha256':before_rejection,'afterSha256':after_rejection},
            'productionEvidence':False}
        if source_scope is not None:
            result.update(sourceScope=source_scope,sourceMigrationEvidence=ledger_reference)
        _read_rejections(claim,result)
        _active(claim,set())
        receipt_sha = _record(target, '020-sql.json', result)
        _active(claim,set())
        claim.record('split-sql-captured', {'sqlReceiptSha256':receipt_sha,'sharedScopeSha256':scope_sha})
        return result
    except Exception as error:
        _failure(target, '090-sql-failed.json', error)
        raise


def capture_raw_phase(claim, source_root, *, filesystem_fence, guard, native_guard=None):
    """No database call; Docker inspection occurs only before freeze/after thaw."""
    snapshot.require(callable(guard), 'FORMAL_SPLIT_INPUT_INVALID')
    snapshot.require(callable(native_guard), 'FORMAL_CAPTURE_NATIVE_OWNER_REQUIRED')
    _active(claim, {'split-raw-intent','split-captured'})
    sql_event = _event(claim, 'split-sql-captured')
    sql_intent = _event(claim, 'split-sql-intent')
    target = (claim.root/'payload').absolute()
    snapshot.require(target.is_dir() and not target.is_symlink() and target.resolve() == target,
                     'FORMAL_SPLIT_DESTINATION_INVALID')
    raw = snapshot._existing_file(target/'020-sql.json').read_bytes()
    snapshot.require(hashlib.sha256(raw).hexdigest() == sql_event['sqlReceiptSha256'],
                     'FORMAL_SPLIT_SQL_RECEIPT_CHANGED')
    sql = json.loads(raw)
    source = Path(source_root).absolute()
    snapshot.require(sql['sourceRoot'] == sql_intent['sourceRoot'] == str(source) and
        sql['state'] == 'SQL_CAPTURED_PENDING_RAW_AND_FULL_BARRIERS' and
        sql['databaseUuid'] == json.loads(claim._plan)['databaseUuid'] and
        sql['sharedScopeSha256'] == sql_intent['sharedScopeSha256'] == sql_event['sharedScopeSha256'],
        'FORMAL_SPLIT_SQL_RECEIPT_CHANGED')
    expected_sql = ('sha256:'+sql['database']['sha256'],sql['database']['bytes'])
    snapshot.require(snapshot._hash_object(target/'database.sql.gz') == expected_sql,
                     'FORMAL_SPLIT_SQL_CHANGED')
    source_data,source_proof_raw=read_source_data(target,claim._plan,sql['database']['sha256'],sql.get('sourceDataEvidence'))
    if 'sourceScope' in sql_intent:
        snapshot.require(sql.get('sourceScope') == sql_intent['sourceScope'], 'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
        _,ledger_raw=read_source_ledger(target,claim._plan,sql['database']['sha256'],sql.get('sourceMigrationEvidence'),
            source_data,sql_intent['sourceScope'])
    else:
        snapshot.require('sourceScope' not in sql and 'sourceMigrationEvidence' not in sql,
            'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
    _read_rejections(claim,sql)
    snapshot.require(type(filesystem_fence) is dict and set(filesystem_fence) == {'mount','binding','seconds'}
        and type(filesystem_fence['binding']) is dict and
        filesystem_fence['binding'].get('operationId') == json.loads(claim._plan)['operationId'] and
        type(filesystem_fence['mount']) is str and type(filesystem_fence['seconds']) is int and
        1 <= filesystem_fence['seconds'] <= 300, 'FORMAL_SPLIT_NATIVE_SCOPE_INVALID')
    snapshot._require_native_physical_runtime()
    guard(); _, before, scope_sha = _scope(claim, stopped=True)
    _observe_shared_actions(claim)
    for role in STOP_ORDER: _event(claim, _action_names(role, 'stop')[1])
    snapshot.require(scope_sha == sql['sharedScopeSha256'], 'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    snapshot.observe_stopped_object_containers(snapshot.collect_docker_barrier_records(),
        str(source), json.loads(claim._plan)['minioContainerId'])
    if snapshot.observation_deadline.get() is not None:
        snapshot.require(snapshot.observation_timeout(7200)>filesystem_fence['seconds']+20,'FORMAL_DATA_DEADLINE')
    claim.record('split-raw-intent', {'sqlReceiptSha256':sql_event['sqlReceiptSha256'],
        'sharedScopeSha256':scope_sha,'sourceRoot':str(source),
        'nativeBinding':filesystem_fence['binding'],'nativeMount':filesystem_fence['mount'],
        'nativeControlRoot':str(target/'native-fence')})
    try:
        # Native lifecycle owns acquisition, copy, acceptance and thaw; it uses
        # no Docker/MySQL requests while their filesystem is frozen.
        def native_owner():
            _active(claim,set())
            snapshot.current_owner_guard(native_guard,code='FORMAL_CAPTURE_NATIVE_OWNER_REQUIRED')
            _active(claim,set())
        native = snapshot._capture_native_physical(target/'native-fence',filesystem_fence['mount'],
            filesystem_fence['binding'],source,target/'minio-physical',filesystem_fence['seconds'],guard=native_owner)
        snapshot.require(type(native) is dict and
            native.get('state') == 'RAW_CAPTURED_AND_THAWED_PENDING_FORMAL_BARRIERS' and
            native.get('productionEvidence') is False, 'FORMAL_SPLIT_NATIVE_NOT_VERIFIED')
        _active(claim,set());guard();_active(claim,set())
        _, after, final_sha = _scope(claim, stopped=True)
        _observe_shared_actions(claim)
        snapshot.require(before == after and final_sha == scope_sha, 'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
        snapshot.observe_stopped_object_containers(snapshot.collect_docker_barrier_records(),
            str(source), json.loads(claim._plan)['minioContainerId'])
        from formal_capture_incremental import verify_series_physical
        verify_series_physical(target/'minio-physical', native['physical'], guard=guard)
        snapshot.require(snapshot._hash_object(target/'database.sql.gz') == expected_sql and
            snapshot._existing_file(target/'020-sql.json').read_bytes() == raw,
            'FORMAL_SPLIT_SQL_CHANGED')
        snapshot.require(read_source_data(target,claim._plan,sql['database']['sha256'],
            sql['sourceDataEvidence'])[1]==source_proof_raw,'FORMAL_DATA_SOURCE_CHANGED')
        _read_rejections(claim,sql)
        if 'sourceScope' in sql_intent:
            snapshot.require(read_source_ledger(target,claim._plan,sql['database']['sha256'],sql['sourceMigrationEvidence'],
                source_data,sql_intent['sourceScope'])[1] == ledger_raw, 'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
        result = {'state':'CAPTURED_PENDING_FULL_BARRIER_PROOF','database':sql['database'],
            'sourceDataEvidence':sql['sourceDataEvidence'],
            'physical':native['physical'],'nativeCapture':native,'hostWritersVerified':False,
            'splitSqlReceiptSha256':sql_event['sqlReceiptSha256'],'sharedScopeSha256':scope_sha,
            'capturedAt':datetime.now(timezone.utc).isoformat()}
        if 'sourceScope' in sql_intent:
            result.update(sourceScope=sql['sourceScope'],sourceMigrationEvidence=sql['sourceMigrationEvidence'])
        _active(claim,set())
        receipt_sha = _record(target, '040-payload.json', result)
        claim.record('split-captured', {'payloadReceiptSha256':receipt_sha,
            'state':'CAPTURED_PENDING_FULL_BARRIER_PROOF'})
        return result
    except Exception as error:
        if isinstance(error,snapshot.NativeCaptureNotStarted):
            control=target/'native-fence'
            snapshot.require(not control.exists() and not control.is_symlink() and
                not any(e['step']=='split-native-not-requested' for e in claim.events),
                'FORMAL_SHARED_THAW_REQUIRED')
            abort={'state':'NATIVE_NOT_REQUESTED','code':error.code,
                'nativeControlRoot':str(control),'nativeBinding':filesystem_fence['binding'],
                'rawIntentSha256':hashlib.sha256(snapshot._canonical_bytes(_event(claim,'split-raw-intent'))).hexdigest(),
                'productionEvidence':False}
            digest=_record(target,'092-native-not-requested.json',abort)
            claim.record('split-native-not-requested',{'receiptSha256':digest})
        _failure(target, '091-raw-failed.json', error)
        raise


def _has(claim, step):
    claim.assert_owned()
    return any(event['step'] == step for event in claim.events)


def _shared_role(claim, role):
    snapshot.require(role in ROLES, 'FORMAL_SHARED_ROLE_INVALID')
    event = _event(claim, 'shared-container-scope')
    raw = claim._read(claim.root/'shared-container-original.json')
    snapshot.require(event == {'scopeSha256':hashlib.sha256(raw).hexdigest()},
                     'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    scope = json.loads(raw)
    snapshot.require(type(scope) is dict and set(scope) == ROLES and
        raw == snapshot._canonical_bytes(scope) and
        len({row['id'] for row in scope.values()}) == len(ROLES) and
        scope['minio']['id'] == json.loads(claim._plan)['minioContainerId'],
        'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    original = scope[role]
    current = snapshot.inspect_formal_container(original['id'])
    snapshot.require(snapshot._container_stable(current) == snapshot._container_stable(original),
                     'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    return original, current, event['scopeSha256']


def _guards(claim, guard, thaw_guard=None):
    snapshot.require(callable(guard), 'FORMAL_SPLIT_INPUT_INVALID')
    claim.assert_owned(); guard(); claim.assert_owned()
    if thaw_guard is not None:
        snapshot.require(callable(thaw_guard), 'FORMAL_SPLIT_INPUT_INVALID')
        thaw_guard(); claim.assert_owned()


def observe_split_sql_barrier(claim, mysql, *, dump_in_progress=False):
    """Require the genuine shared journal, never synthesize legacy stop events."""
    _active(claim,set())
    identity, _, digest = snapshot._claimed_database_original(claim)
    snapshot.require(_event(claim, 'db-fenced').get('originalSha256') == digest and
        not _has(claim, 'shared-recovery-intent'), 'FORMAL_SPLIT_STAGE_INVALID')
    original, current, _ = _shared_role(claim, 'mysql')
    snapshot.require(mysql.container == original['id'] and current['state'] == original['state'] and
        current['state']['Running'], 'FORMAL_SPLIT_MYSQL_CHANGED')
    _observe_shared_actions(claim)
    for role in STOP_ORDER[:-1]:
        stopped = _event(claim, _action_names(role, 'stop')[1])
        snapshot.require(stopped['runtime']['Running'] is False, 'FORMAL_SPLIT_SHARED_NOT_STOPPED')
    snapshot.require(snapshot._database_flags(mysql, identity) ==
        {'serverUuid':identity,'readOnly':1,'superReadOnly':1}, 'FORMAL_DATABASE_NOT_QUIESCENT')
    snapshot.observe_database_barrier(mysql,dump_in_progress=dump_in_progress)
    _active(claim,set())


def _observe_native_environment(binding):
    import formal_filesystem_watchdog as native
    native.require_native_runtime()
    snapshot.require(binding.get('bootId') == Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                     'FORMAL_SHARED_THAW_REQUIRED')
    seconds=snapshot.observation_timeout(5)
    try:
        native.observe_mount(Path(binding['mount']['target']), binding['mount'],timeout=seconds)
    except native.WatchdogError:
        raise snapshot.FormalSnapshotError('FORMAL_SHARED_THAW_REQUIRED') from None
    snapshot.observation_timeout(5)


def _thaw_receipt(claim):
    """A retained native unfreeze result, never a guess from owner exit.

    A live, caller-provided thaw/exclusion guard remains required on recovery.
    This receipt alone does not exclude another administrator freezing again.
    """
    if not _has(claim, 'split-raw-intent'):
        snapshot.require(not (claim.root/'payload/native-fence').exists(),
                         'FORMAL_SHARED_THAW_REQUIRED')
        return {'nativeState':'NOT_REQUESTED'}
    raw_intent = _event(claim, 'split-raw-intent')
    binding = raw_intent.get('nativeBinding')
    snapshot.require(type(binding) is dict and
        binding.get('operationId') == json.loads(claim._plan)['operationId'],
        'FORMAL_SHARED_THAW_REQUIRED')
    if _has(claim,'split-native-not-requested'):
        try:
            path=snapshot._existing_file(claim.root/'payload/092-native-not-requested.json')
            snapshot.require(path.stat().st_size<=16384 and stat.S_IMODE(path.stat().st_mode)==0o600,
                'FORMAL_SHARED_THAW_REQUIRED')
            raw=path.read_bytes();abort=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
            control=claim.root/'payload/native-fence'
            snapshot.require(raw==snapshot._canonical_bytes(abort) and abort=={
                'state':'NATIVE_NOT_REQUESTED','code':'FORMAL_DATA_DEADLINE','nativeControlRoot':str(control),
                'nativeBinding':binding,'rawIntentSha256':hashlib.sha256(snapshot._canonical_bytes(raw_intent)).hexdigest(),
                'productionEvidence':False} and _event(claim,'split-native-not-requested')=={'receiptSha256':digest} and
                raw_intent['nativeControlRoot']==str(control) and raw_intent['nativeMount']==binding['mount']['target'] and
                not control.exists() and not control.is_symlink(),'FORMAL_SHARED_THAW_REQUIRED')
            _observe_native_environment(binding)
            return {'nativeState':'NOT_REQUESTED','nativeAbortSha256':digest}
        except (OSError,ValueError,KeyError,TypeError,snapshot.FormalSnapshotError):
            raise snapshot.FormalSnapshotError('FORMAL_SHARED_THAW_REQUIRED') from None
    try:
        root = claim.root/'payload/native-fence'
        snapshot.require(raw_intent.get('nativeControlRoot') == str(root) and
            raw_intent.get('nativeMount') == binding['mount']['target'] and
            root.resolve() == root and stat.S_IMODE(root.stat().st_mode) == 0o700,
            'FORMAL_SHARED_THAW_REQUIRED')
        ready_raw = snapshot._existing_file(root/'000-ready.json').read_bytes()
        snapshot.require(len(ready_raw) <= 16384 and
            stat.S_IMODE((root/'000-ready.json').stat().st_mode) == 0o600, 'FORMAL_SHARED_THAW_REQUIRED')
        ready = json.loads(ready_raw)
        snapshot.require(ready_raw == snapshot._canonical_bytes(ready) and ready['binding'] == binding and
            ready['bindingSha256'] == hashlib.sha256(snapshot._canonical_bytes(binding)).hexdigest(),
            'FORMAL_SHARED_THAW_REQUIRED')
        path = snapshot._existing_file(root/'020-thawed.json')
        snapshot.require(path.stat().st_size <= 16384 and stat.S_IMODE(path.stat().st_mode) == 0o600,
                         'FORMAL_SHARED_THAW_REQUIRED')
        raw = path.read_bytes(); row = json.loads(raw)
    except (OSError, ValueError, KeyError, TypeError, snapshot.FormalSnapshotError):
        raise snapshot.FormalSnapshotError('FORMAL_SHARED_THAW_REQUIRED') from None
    snapshot.require(raw == snapshot._canonical_bytes(row) and type(row) is dict and
        set(row) == {'status','bindingSha256','observedBootSeconds'} and
        row['bindingSha256'] == hashlib.sha256(snapshot._canonical_bytes(binding)).hexdigest() and
        row['status'] in ('THAWED_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS','THAWED_CAPTURE_REMAINS_INVALID') and
        type(row['observedBootSeconds']) in (int,float) and
        type(ready.get('deadlineBootSeconds')) in (int,float) and
        type(ready.get('startedBootSeconds')) in (int,float) and
        ready['startedBootSeconds'] <= row['observedBootSeconds'],
        'FORMAL_SHARED_THAW_REQUIRED')
    _observe_native_environment(binding)
    return {'nativeState':row['status'],'nativeThawSha256':hashlib.sha256(raw).hexdigest()}


def begin_shared_recovery(claim, *, guard, thaw_guard):
    """Explicit recovery selection; no service action or implicit thaw/retry."""
    snapshot.require(callable(thaw_guard) and not _has(claim, 'shared-recovery-intent') and
        not _has(claim, 'released'), 'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    _guards(claim, guard, thaw_guard)
    thaw = _thaw_receipt(claim)
    _observe_shared_actions(claim)
    _, _, digest = _shared_role(claim, 'mysql')
    claim.record('shared-recovery-intent', {'scopeSha256':digest,**thaw})
    return thaw


def _recovery(claim, guard, thaw_guard):
    snapshot.require(callable(thaw_guard), 'FORMAL_SPLIT_INPUT_INVALID')
    _guards(claim, guard, thaw_guard)
    intent = _event(claim, 'shared-recovery-intent')
    thaw = _thaw_receipt(claim)
    _, _, digest = _shared_role(claim, 'mysql')
    snapshot.require(intent == {'scopeSha256':digest,**thaw},
                     'FORMAL_SHARED_RECOVERY_CHANGED')


def _action_names(role, action):
    snapshot.require(role in ROLES and action in ('stop','start'), 'FORMAL_SHARED_ACTION_INVALID')
    prefix = 'shared-'+role+('-stop' if action == 'stop' else '-restore')
    return prefix+'-intent', 'shared-'+role+('-stopped' if action == 'stop' else '-restored')


def _observe_shared_actions(claim, *, reconciling=None):
    """Refuse the next mutation if any earlier action is unresolved or drifts."""
    for role in STOP_ORDER:
        original, current, digest = _shared_role(claim, role)
        expected = original['state']
        for action in ('stop','start'):
            intent_name, complete_name = _action_names(role, action)
            if _has(claim, intent_name) and not _has(claim, complete_name):
                snapshot.require(reconciling == (role,action), 'FORMAL_SHARED_PENDING_ACTION_REQUIRED')
                expected = None
            elif _has(claim, complete_name):
                complete = _event(claim, complete_name)
                snapshot.require(complete['scopeSha256'] == digest and
                    complete['intentSha256'] == hashlib.sha256(snapshot._canonical_bytes(_event(claim,intent_name))).hexdigest(),
                    'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
                expected = complete['runtime']
        if expected is not None:
            snapshot.require(current['state'] == expected, 'FORMAL_SHARED_RUNTIME_CHANGED')


def _action_order(claim, role, action):
    order = STOP_ORDER if action == 'stop' else RESTORE_ORDER
    for prior in order[:order.index(role)]:
        snapshot.require(_has(claim, _action_names(prior, action)[1]),
                         'FORMAL_SHARED_ACTION_ORDER_INVALID')
    if action == 'stop':
        snapshot.require(not _has(claim, 'shared-recovery-intent'), 'FORMAL_SHARED_ACTION_ORDER_INVALID')
        _event(claim, 'db-fenced')
        if role == 'mysql': _event(claim, 'split-sql-captured')
    elif role != 'mysql':
        _event(claim, 'shared-db-restored')


def _completed_shared_action(original, current, intent, action):
    state = current['state']; before = intent['before']
    required = intent['actionRequired']
    if not required:
        valid = state == before
    elif action == 'stop':
        valid = state['Running'] is False and state['ExitCode'] == 0 and \
            state['StartedAt'] == before['StartedAt'] and state['FinishedAt'] != before['FinishedAt']
    else:
        valid = state['Running'] is True and state['StartedAt'] != before['StartedAt']
    snapshot.require(valid and state['Running'] == (False if action == 'stop' else original['state']['Running']),
                     'FORMAL_SHARED_RECONCILIATION_REQUIRED')


def reconcile_shared_container(claim, role, action, *, guard, thaw_guard=None, _controlled_container_actions=None):
    """Read only actual runtime; record completion, never issue Docker action."""
    intent_name, complete_name = _action_names(role, action)
    snapshot.require(not _has(claim, complete_name) and not _has(claim, 'released'),
                     'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    if action == 'start': _recovery(claim, guard, thaw_guard)
    else: _guards(claim, guard)
    original, current, digest = _shared_role(claim, role)
    _action_order(claim, role, action)
    _observe_shared_actions(claim, reconciling=(role,action))
    intent = _event(claim, intent_name)
    snapshot.require(set(intent) == {'scopeSha256','before','actionRequired'} and
        intent['scopeSha256'] == digest and type(intent['actionRequired']) is bool,
        'FORMAL_SPLIT_SHARED_SCOPE_CHANGED')
    _completed_shared_action(original, current, intent, action)
    _guards(claim, guard, thaw_guard)
    snapshot.require(_shared_role(claim, role)[1] == current, 'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    if _controlled_container_actions is not None:
        _controlled_container_actions.assert_role(role,original,current,guard=guard,
            deadline=snapshot.observation_deadline.get())
    claim.record(complete_name, {'scopeSha256':digest,'runtime':current['state'],
        'actionPerformed':intent['actionRequired'],
        'intentSha256':hashlib.sha256(snapshot._canonical_bytes(intent)).hexdigest()})
    return current['state']


def _shared_action(claim, role, action, *, guard, thaw_guard=None, container_actions=None):
    intent_name, complete_name = _action_names(role, action)
    snapshot.require(not _has(claim, intent_name) and not _has(claim, complete_name) and
        not _has(claim, 'released'), 'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    if action == 'start': _recovery(claim, guard, thaw_guard)
    else: _guards(claim, guard)
    original, current, digest = _shared_role(claim, role)
    _action_order(claim, role, action)
    _observe_shared_actions(claim)
    if action == 'stop':
        snapshot.require(current['state'] == original['state'], 'FORMAL_SHARED_RUNTIME_CHANGED')
        required = original['state']['Running']
    elif _has(claim, _action_names(role, 'stop')[0]):
        stopped = _event(claim, _action_names(role, 'stop')[1])
        snapshot.require(stopped['scopeSha256'] == digest and current['state'] == stopped['runtime'],
                         'FORMAL_SHARED_RUNTIME_CHANGED')
        required = original['state']['Running']
    else:
        snapshot.require(current['state'] == original['state'], 'FORMAL_SHARED_RUNTIME_CHANGED')
        required = False
    if container_actions is not None:
        container_actions.assert_role(role,original,current,guard=guard,deadline=snapshot.observation_deadline.get())
    claim.record(intent_name, {'scopeSha256':digest,'before':current['state'],'actionRequired':required})
    _guards(claim, guard, thaw_guard)
    snapshot.require(_shared_role(claim, role)[1] == current, 'FORMAL_SHARED_RUNTIME_CHANGED')
    if container_actions is not None:
        container_actions.assert_role(role,original,current,guard=guard,deadline=snapshot.observation_deadline.get())
    if required:
        if container_actions is not None:
            container_actions.action(role,action,original,current,guard=guard,deadline=snapshot.observation_deadline.get())
        else:snapshot.run_formal_container_action(action, original['id'])
    return reconcile_shared_container(claim, role, action, guard=guard, thaw_guard=thaw_guard,
        _controlled_container_actions=container_actions)


def stop_shared_container(claim, role, *, guard):
    return _shared_action(claim, role, 'stop', guard=guard)


def _controlled_actions_required(container_actions):
    snapshot.require(container_actions is not None and callable(getattr(container_actions,'assert_role',None)) and
        callable(getattr(container_actions,'action',None)),'FORMAL_CONTROLLED_CONTAINER_SOURCES_REQUIRED')


def stop_controlled_capture_database(claim,role,*,guard,container_actions):
    """A SQL->MySQL stop with the same durable order and full native sources."""
    _controlled_actions_required(container_actions)
    snapshot.require(role=='mysql','FORMAL_CONTROLLED_STOP_INPUT_INVALID')
    return _shared_action(claim,role,'stop',guard=guard,container_actions=container_actions)


def _controlled_writer_scope(claim, role, expected_shared_scope_sha256):
    """A's explicit pre-fence writer phase, never a legacy gate relaxation.

    The normal owner must provide current lease/approved ingress/host/caller
    exclusion through guard; this finite phase does not certify full capture.
    Only non-MySQL writers can use it. SQL, MySQL stop and raw/thaw retain their
    existing independent database barriers.
    """
    snapshot.require(role in STOP_ORDER[:-1] and
        type(expected_shared_scope_sha256) is str and
        re.fullmatch('[0-9a-f]{64}',expected_shared_scope_sha256),
        'FORMAL_CONTROLLED_STOP_INPUT_INVALID')
    _active(claim, {'db-fence-intent','db-fenced','split-sql-intent','split-sql-captured',
                    'split-raw-intent','split-captured'})
    original,current,digest=_shared_role(claim,role)
    snapshot.require(digest==expected_shared_scope_sha256,'FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
    for prior in STOP_ORDER[:STOP_ORDER.index(role)]:
        intent_name,complete_name=_action_names(prior,'stop')
        snapshot.require(_has(claim,complete_name) and
            _event(claim,intent_name).get('stopStrategy')=='CONTROLLED_NORMAL_STOP',
            'FORMAL_CONTROLLED_STOP_ORDER_INVALID')
    return original,current,digest


def assert_controlled_prefence_stops(claim, *, expected_shared_scope_sha256, guard):
    """Read exact A completed stops. No action, replay or fence relaxation."""
    snapshot.require(type(expected_shared_scope_sha256) is str and
        re.fullmatch('[0-9a-f]{64}',expected_shared_scope_sha256),'FORMAL_CONTROLLED_STOP_INPUT_INVALID')
    def observe():
        _active(claim,{'split-sql-intent','split-sql-captured','split-raw-intent','split-captured'})
        snapshot.require(not _has(claim,'shared-mysql-stop-intent') and not _has(claim,'shared-mysql-stopped'),
            'FORMAL_CONTROLLED_STOP_ORDER_INVALID')
        _observe_shared_actions(claim)
        indices={event['step']:index for index,event in enumerate(claim.events)}
        previous=-1
        fence=[indices[step] for step in ('db-fence-intent','db-fenced') if step in indices]
        for role in STOP_ORDER[:-1]:
            original,current,digest=_shared_role(claim,role)
            snapshot.require(digest==expected_shared_scope_sha256,'FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
            intent_name,complete_name=_action_names(role,'stop')
            intent=_event(claim,intent_name);complete=_event(claim,complete_name)
            snapshot.require(type(intent) is dict and set(intent)=={'scopeSha256','before','actionRequired','stopStrategy'} and
                intent['scopeSha256']==digest and intent['before']==original['state'] and
                type(intent['actionRequired']) is bool and intent['actionRequired']==original['state']['Running'] and
                intent['stopStrategy']=='CONTROLLED_NORMAL_STOP','FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
            snapshot.require(type(complete) is dict and set(complete)=={'scopeSha256','runtime','actionPerformed','intentSha256'} and
                complete['scopeSha256']==digest and complete['runtime']==current['state'] and
                type(complete['actionPerformed']) is bool and complete['actionPerformed']==intent['actionRequired'] and
                complete['intentSha256']==hashlib.sha256(snapshot._canonical_bytes(intent)).hexdigest(),
                'FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
            snapshot.require(previous<indices[intent_name]<indices[complete_name] and
                all(indices[complete_name]<position for position in fence),'FORMAL_CONTROLLED_STOP_ORDER_INVALID')
            _completed_shared_action(original,current,intent,'stop')
            previous=indices[complete_name]
        snapshot.observation_timeout(1)
    _guards(claim,guard);observe();_guards(claim,guard);observe()
    return dict(state='CONTROLLED_PREFENCE_STOPS_OBSERVED',scopeSha256=expected_shared_scope_sha256,
        serviceActionsPerformed=False,productionEvidence=False,releaseReady=False)


def _controlled_writer_guard(claim,role,scope_sha,original,guard,*,intent=None):
    """Rebind the stage after every native adapter callback, including last."""
    original_raw=snapshot._canonical_bytes(original)
    intent_raw=None if intent is None else snapshot._canonical_bytes(intent)
    intent_name,complete_name=_action_names(role,'stop')
    def bound():
        _guards(claim,guard)
        observed,_,_=_controlled_writer_scope(claim,role,scope_sha)
        snapshot.require(snapshot._canonical_bytes(observed)==original_raw,
            'FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
        snapshot.require(not _has(claim,complete_name),'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
        if intent_raw is None:
            snapshot.require(not _has(claim,intent_name),'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
        else:
            snapshot.require(snapshot._canonical_bytes(_event(claim,intent_name))==intent_raw,
                'FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
        _observe_shared_actions(claim,reconciling=None if intent_raw is None else (role,'stop'))
    return bound


def stop_controlled_shared_writer(claim, role, *, expected_shared_scope_sha256, guard, container_actions):
    """One approved A normal stop, prior to DB fencing. No implicit retry."""
    _controlled_actions_required(container_actions);_guards(claim,guard)
    original,current,digest=_controlled_writer_scope(claim,role,expected_shared_scope_sha256)
    intent_name,complete_name=_action_names(role,'stop')
    snapshot.require(not _has(claim,intent_name) and not _has(claim,complete_name),
        'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    _observe_shared_actions(claim)
    snapshot.require(current['state']==original['state'],'FORMAL_SHARED_RUNTIME_CHANGED')
    before_guard=_controlled_writer_guard(claim,role,digest,original,guard)
    container_actions.assert_role(role,original,current,guard=before_guard,deadline=snapshot.observation_deadline.get())
    intent={'scopeSha256':digest,'before':current['state'],
        'actionRequired':original['state']['Running'],'stopStrategy':'CONTROLLED_NORMAL_STOP'}
    claim.record(intent_name,intent)
    action_guard=_controlled_writer_guard(claim,role,digest,original,guard,intent=intent)
    _guards(claim,guard)
    _controlled_writer_scope(claim,role,expected_shared_scope_sha256)
    _observe_shared_actions(claim,reconciling=(role,'stop'))
    snapshot.require(_shared_role(claim,role)[1]==current,'FORMAL_SHARED_RUNTIME_CHANGED')
    container_actions.assert_role(role,original,current,guard=action_guard,deadline=snapshot.observation_deadline.get())
    if intent['actionRequired']:
        container_actions.action(role,'stop',original,current,guard=action_guard,deadline=snapshot.observation_deadline.get())
    return reconcile_controlled_shared_writer(claim,role,
        expected_shared_scope_sha256=expected_shared_scope_sha256,guard=guard,container_actions=container_actions)


def reconcile_controlled_shared_writer(claim, role, *, expected_shared_scope_sha256, guard, container_actions):
    """Only read and record an already effected controlled stop; never retry."""
    _controlled_actions_required(container_actions);_guards(claim,guard)
    original,current,digest=_controlled_writer_scope(claim,role,expected_shared_scope_sha256)
    intent_name,complete_name=_action_names(role,'stop')
    snapshot.require(not _has(claim,complete_name),'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    _observe_shared_actions(claim,reconciling=(role,'stop'))
    intent=_event(claim,intent_name)
    snapshot.require(set(intent)=={'scopeSha256','before','actionRequired','stopStrategy'} and
        intent['scopeSha256']==digest and intent['before']==original['state'] and
        type(intent['actionRequired']) is bool and
        intent['actionRequired']==original['state']['Running'] and
        intent['stopStrategy']=='CONTROLLED_NORMAL_STOP','FORMAL_CONTROLLED_STOP_SCOPE_CHANGED')
    _completed_shared_action(original,current,intent,'stop')
    complete_guard=_controlled_writer_guard(claim,role,digest,original,guard,intent=intent)
    container_actions.assert_role(role,original,current,guard=complete_guard,deadline=snapshot.observation_deadline.get())
    _guards(claim,guard)
    _controlled_writer_scope(claim,role,expected_shared_scope_sha256)
    _observe_shared_actions(claim,reconciling=(role,'stop'))
    snapshot.require(_shared_role(claim,role)[1]==current,'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    container_actions.assert_role(role,original,current,guard=complete_guard,deadline=snapshot.observation_deadline.get())
    claim.record(complete_name,{'scopeSha256':digest,'runtime':current['state'],
        'actionPerformed':intent['actionRequired'],
        'intentSha256':hashlib.sha256(snapshot._canonical_bytes(intent)).hexdigest()})
    return current['state']


def restore_shared_container(claim, role, *, guard, thaw_guard):
    return _shared_action(claim, role, 'start', guard=guard, thaw_guard=thaw_guard)


def restore_controlled_shared_originals(claim, mysql, *, guard, thaw_guard,
                                       resume_guard, container_actions):
    """Explicit A original-state recovery; no claim acquisition or grant issuer.

    The owner supplies its already consumed signed A authority guard, held
    source/lease controls and positive thaw. Every nested native action uses
    the complete-source adapter. An uncertain intent is never retried, and
    the existing limited restoration receipt never becomes backup completion.
    """
    snapshot.require(all(callable(g) for g in (guard, thaw_guard, resume_guard)),
                     'FORMAL_PRODUCTION_A_RESUME_GUARD_REQUIRED')
    _controlled_actions_required(container_actions)

    def current():
        # The supplied source observer may inspect Docker; thaw precedes it.
        thaw_guard(); claim.assert_owned(); resume_guard()
        guard(); resume_guard(); thaw_guard(); claim.assert_owned()

    current()
    begin_shared_recovery(claim, guard=current, thaw_guard=thaw_guard)
    for role in RESTORE_ORDER:
        current()
        _shared_action(claim, role, 'start', guard=current,
                       thaw_guard=thaw_guard, container_actions=container_actions)
        current()
        if role == 'mysql':
            restore_shared_database_flags(claim, mysql, guard=current, thaw_guard=thaw_guard)
            current()
    result = verify_shared_restoration(claim, mysql, guard=current, thaw_guard=thaw_guard)
    current()
    return result


def _restored_mysql(claim, mysql, guard, thaw_guard, *, reconciling=None):
    _recovery(claim, guard, thaw_guard)
    original, current, digest = _shared_role(claim, 'mysql')
    restored = _event(claim, 'shared-mysql-restored')
    snapshot.require(mysql.container == original['id'] and restored['scopeSha256'] == digest and
        current['state'] == restored['runtime'] and current['state']['Running'] is True,
        'FORMAL_SHARED_DATABASE_RUNTIME_CHANGED')
    identity, flags, original_sha = snapshot._claimed_database_original(claim)
    _observe_shared_actions(claim,reconciling=reconciling)
    snapshot.require(_event(claim, 'db-fenced').get('originalSha256') == original_sha,
                     'FORMAL_SHARED_DATABASE_ORIGINAL_CHANGED')
    return identity, flags, original_sha, restored


def restore_shared_database_flags(claim, mysql, *, guard, thaw_guard):
    """Restore exact flags after held fence or a journal-bound MySQL restart.

    External caller exclusion must remain active even when reboot resets flags.
    No implicit fence reacquisition, legacy completion event or replay occurs.
    """
    snapshot.require(not _has(claim, 'shared-db-restore-intent') and not _has(claim, 'shared-db-restored'),
                     'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    identity, original, digest, restored = _restored_mysql(claim, mysql, guard, thaw_guard)
    before = snapshot._database_flags(mysql, identity)
    snapshot.require(before['serverUuid'] == identity, 'FORMAL_SHARED_DATABASE_IDENTITY_CHANGED')
    snapshot.require(restored['actionPerformed'] or before == {'serverUuid':identity,'readOnly':1,'superReadOnly':1},
                     'FORMAL_SHARED_DATABASE_FLAGS_AMBIGUOUS')
    intent = {'originalSha256':digest,'mysqlRuntime':restored['runtime'],
        'before':before,'actionRequired':before != original}
    claim.record('shared-db-restore-intent', intent)
    _restored_mysql(claim, mysql, guard, thaw_guard)
    snapshot.require(snapshot._database_flags(mysql, identity) == before,
                     'FORMAL_SHARED_DATABASE_FLAGS_AMBIGUOUS')
    if intent['actionRequired']:
        mysql.query('SET GLOBAL super_read_only=OFF; SET GLOBAL read_only='+
                    ('ON' if original['readOnly'] else 'OFF')+';')
    return reconcile_shared_database_flags(claim, mysql, guard=guard, thaw_guard=thaw_guard)


def reconcile_shared_database_flags(claim, mysql, *, guard, thaw_guard):
    """Read-only completion of a retained exact flag restore intent."""
    snapshot.require(not _has(claim, 'shared-db-restored'), 'FORMAL_SHARED_ACTION_REPLAY_REFUSED')
    identity, original, digest, restored = _restored_mysql(claim, mysql, guard, thaw_guard)
    intent = _event(claim, 'shared-db-restore-intent')
    snapshot.require(set(intent) == {'originalSha256','mysqlRuntime','before','actionRequired'} and
        intent['originalSha256'] == digest and intent['mysqlRuntime'] == restored['runtime'] and
        type(intent['actionRequired']) is bool and intent['actionRequired'] == (intent['before'] != original),
        'FORMAL_SHARED_DATABASE_ORIGINAL_CHANGED')
    snapshot.require(snapshot._database_flags(mysql, identity) == original,
                     'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    _restored_mysql(claim, mysql, guard, thaw_guard)
    claim.record('shared-db-restored', {'originalSha256':digest,'mysqlRuntime':restored['runtime'],
        'originalFlags':original,'actionPerformed':intent['actionRequired']})
    return original


def verify_shared_restoration(claim, mysql, *, guard, thaw_guard):
    """Fresh original-state verification; does not release the maintenance claim."""
    identity, original_flags, flags_sha, restored_mysql = _restored_mysql(claim, mysql, guard, thaw_guard)
    database = _event(claim, 'shared-db-restored')
    snapshot.require(database['originalSha256'] == flags_sha and database['originalFlags'] == original_flags and
        database['mysqlRuntime'] == restored_mysql['runtime'] and
        snapshot._database_flags(mysql, identity) == original_flags,
        'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    services = {}
    for role in RESTORE_ORDER:
        original, current, scope_sha = _shared_role(claim, role)
        recorded = _event(claim, _action_names(role, 'start')[1])
        snapshot.require(recorded['scopeSha256'] == scope_sha and recorded['runtime'] == current['state'] and
            current['state']['Running'] == original['state']['Running'], 'FORMAL_SHARED_RUNTIME_CHANGED')
        services[role] = current
    _recovery(claim, guard, thaw_guard)
    _observe_shared_actions(claim)
    snapshot.require(snapshot._database_flags(mysql, identity) == original_flags,
                     'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    return {'state':'ORIGINAL_SERVICES_RESTORED_PENDING_CALLER_PROOF','sharedScopeSha256':scope_sha,
        'originalFlagsSha256':flags_sha,'originalFlags':original_flags,'services':services,
        'native':_thaw_receipt(claim),'productionEvidence':False}


def verify_shared_dependency_restoration(claim, mysql, *, guard, thaw_guard, backend_transition=None):
    """Fresh dependencies; only an exact approved original-backend transition may run.

    Default callers still require both applications stopped. A pending backend
    intent is observed, never reconciled or dispatched by this verifier.
    """
    stage=None;reconciling=None
    if backend_transition is not None:
        from formal_original_open_writer import CompletedOriginalOpenChecks
        snapshot.require(type(backend_transition) is CompletedOriginalOpenChecks and backend_transition.claim is claim,
            'FORMAL_SHARED_APPLICATION_TRANSITION_INVALID')
        stage=backend_transition.assert_valid()['startStage']
        if stage=='INTENT_RETAINED':reconciling=('backend','start')
    identity, flags, flags_sha, restored_mysql = _restored_mysql(claim,mysql,guard,thaw_guard,reconciling=reconciling)
    database=_event(claim,'shared-db-restored')
    snapshot.require(database['originalSha256']==flags_sha and database['originalFlags']==flags and
        database['mysqlRuntime']==restored_mysql['runtime'] and
        snapshot._database_flags(mysql,identity)==flags,'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    services={};held={};backend=None
    for role in RESTORE_ORDER:
        original,current,scope_sha=_shared_role(claim,role)
        if role in ('backend','frontend'):
            if role=='backend' and backend_transition is not None:
                snapshot.require(original==backend_transition.original and scope_sha==backend_transition.scope_sha,
                    'FORMAL_SHARED_APPLICATION_TRANSITION_INVALID')
                if current['state']['Running'] is False:
                    snapshot.require(stage!='RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION' and
                        current['state']==backend_transition.start_intent['before'],
                        'FORMAL_SHARED_APPLICATION_TRANSITION_CHANGED')
                else:
                    snapshot.require(stage in ('INTENT_RETAINED','RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION'),
                        'FORMAL_SHARED_APPLICATION_TRANSITION_CHANGED')
                    _completed_shared_action(original,current,backend_transition.start_intent,'start')
                    if stage=='RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION':
                        snapshot.require(_event(claim,'shared-backend-restored')['runtime']==current['state'],
                            'FORMAL_SHARED_APPLICATION_TRANSITION_CHANGED')
                backend=current
                continue
            snapshot.require(not _has(claim,_action_names(role,'start')[0]) and
                not _has(claim,_action_names(role,'start')[1]),'FORMAL_SHARED_APPLICATION_START_REFUSED')
            expected=original['state'] if not original['state']['Running'] else _event(claim,_action_names(role,'stop')[1])['runtime']
            snapshot.require(current['state']==expected and current['state']['Running'] is False,
                'FORMAL_SHARED_APPLICATION_NOT_HELD')
            held[role]=current
        else:
            restored=_event(claim,_action_names(role,'start')[1])
            snapshot.require(restored['scopeSha256']==scope_sha and restored['runtime']==current['state'] and
                current['state']['Running']==original['state']['Running'],'FORMAL_SHARED_RUNTIME_CHANGED')
            services[role]=current
    _recovery(claim,guard,thaw_guard);_observe_shared_actions(claim,reconciling=reconciling)
    snapshot.require(snapshot._database_flags(mysql,identity)==flags,'FORMAL_SHARED_RECONCILIATION_REQUIRED')
    result=dict(sharedScopeSha256=scope_sha,originalFlagsSha256=flags_sha,originalFlags=flags,
        services=services,applicationsHeld=held,native=_thaw_receipt(claim),productionEvidence=False)
    if backend_transition is not None:
        snapshot.require(backend_transition.assert_valid()['startStage']==stage,
            'FORMAL_SHARED_APPLICATION_TRANSITION_CHANGED')
        result.update(backendCurrent=backend,backendStartStage=stage)
    return result
