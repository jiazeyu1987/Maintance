"""Selected DCC table observations only; no writes, cancellation or full drain.

Counts cover every tenant and soft-deleted row in seven fixed source tables.
They are not raw row digests or accepted-root/business-row correspondence.
"""
import hashlib
import os
import re
import time

import formal_snapshot_linux as snapshot
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError, require


def _in(column, values):
    return '(BINARY '+column+' IN ('+','.join("'"+v+"'" for v in values)+'))'


def _source(table, columns, known, pending, inconsistent, failed='FALSE'):
    return {'table':table, 'columns':tuple(sorted(set(columns.split()) | {'id','tenant_id','deleted'})),
            'known':known, 'pending':pending, 'inconsistent':inconsistent, 'failed':failed}


TASK_TERMINAL = _in('s.status', ('COMPLETED','FAILED','CANCELLED'))
ITEM_TERMINAL = _in('i.status', ('COMPLETED','FAILED','CANCELLED'))
TASK_KNOWN = _in('s.status', ('UPLOADING','WAITING','RUNNING','CANCELLING','COMPLETED','FAILED','CANCELLED'))
TABLE_PREFIX = 'dcc_controlled_file_'
SOURCES = {
    'batch-recognition':_source(TABLE_PREFIX+'batch_recognition_task',
        'status completed_at total_count processed_count remaining_count',
        _in('s.status', ('WAITING','RUNNING','COMPLETED','FAILED','STOPPED')),
        _in('s.status', ('WAITING','RUNNING')),
        "("+_in('s.status', ('COMPLETED','FAILED','STOPPED'))+" AND s.completed_at IS NULL) OR "
        "s.total_count IS NULL OR s.processed_count IS NULL OR s.remaining_count IS NULL OR "
        "s.total_count<0 OR s.processed_count<0 OR s.remaining_count<0 OR s.processed_count>s.total_count OR "
        "("+_in('s.status', ('COMPLETED',))+" AND (s.processed_count<>s.total_count OR s.remaining_count<>0))",
        _in('s.status', ('FAILED',))),
    'nas-transfer':_source(TABLE_PREFIX+'nas_transfer_task',
        'status completed_at next_check_at source_type', TASK_KNOWN,
        _in('s.status', ('UPLOADING','WAITING','RUNNING','CANCELLING')),
        "("+TASK_TERMINAL+" AND (s.completed_at IS NULL OR s.next_check_at IS NOT NULL OR "
        "EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_nas_transfer_task_item` i "
        "WHERE i.task_id=s.id AND i.tenant_id=s.tenant_id AND NOT COALESCE("+ITEM_TERMINAL+",FALSE)))) OR "
        "NOT COALESCE("+_in('s.source_type', ('NAS','LOCAL_FOLDER'))+",FALSE)",
        _in('s.status', ('FAILED',))),
    'nas-item':_source(TABLE_PREFIX+'nas_transfer_task_item',
        'status completed_at task_id parent_item_id',
        _in('s.status', ('WAITING','RUNNING','COMPLETED','FAILED','CANCELLED')),
        _in('s.status', ('WAITING','RUNNING')),
        "("+_in('s.status', ('COMPLETED','FAILED','CANCELLED'))+" AND s.completed_at IS NULL) OR "
        "NOT EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_nas_transfer_task` t "
        "WHERE t.id=s.task_id AND t.tenant_id=s.tenant_id) OR "
        "(s.parent_item_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_nas_transfer_task_item` p "
        "WHERE p.id=s.parent_item_id AND p.task_id=s.task_id AND p.tenant_id=s.tenant_id AND p.id<>s.id))",
        _in('s.status', ('FAILED',))),
    'nas-audit':_source('dcc_nas_control_audit_task',
        'status completed_at report_file_id report_file_name',
        _in('s.status', ('WAITING','RUNNING','COMPLETED','FAILED')),
        _in('s.status', ('WAITING','RUNNING')),
        "("+_in('s.status', ('COMPLETED','FAILED'))+" AND s.completed_at IS NULL) OR "
        "("+_in('s.status', ('COMPLETED',))+" AND (s.report_file_id IS NULL OR s.report_file_name IS NULL "
        "OR LENGTH(TRIM(s.report_file_name))=0))", _in('s.status', ('FAILED',))),
    'upload-ticket':_source(TABLE_PREFIX+'temporary_file',
        'status cleanup_status bound_controlled_file_id bound_time cleanup_time cleanup_reason',
        "("+_in('s.status', ('AVAILABLE',))+" AND "+_in('s.cleanup_status', ('ACTIVE','CLEANING','CLEANED'))+") OR "
        "("+_in('s.status', ('BOUND',))+" AND "+_in('s.cleanup_status', ('BOUND',))+")",
        "("+_in('s.status', ('AVAILABLE',))+" AND "+_in('s.cleanup_status', ('ACTIVE','CLEANING'))+")",
        "("+_in('s.status', ('BOUND',))+" AND (s.bound_controlled_file_id IS NULL OR s.bound_time IS NULL)) OR "
        "("+_in('s.status', ('AVAILABLE',))+" AND (s.bound_controlled_file_id IS NOT NULL OR s.bound_time IS NOT NULL)) OR "
        "("+_in('s.cleanup_status', ('CLEANED',))+" AND (s.cleanup_time IS NULL OR s.cleanup_reason IS NULL "
        "OR LENGTH(TRIM(s.cleanup_reason))=0))"),
    'upload-chunk':_source(TABLE_PREFIX+'local_folder_upload_chunk',
        'status task_id chunk_index total_chunks file_size chunk_size',
        _in('s.status', ('COMPLETED',)),
        "EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_nas_transfer_task` t WHERE t.id=s.task_id "
        "AND t.tenant_id=s.tenant_id AND NOT COALESCE("+_in('t.status', ('COMPLETED','FAILED','CANCELLED'))+",FALSE))",
        "NOT EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_nas_transfer_task` t WHERE t.id=s.task_id "
        "AND t.tenant_id=s.tenant_id AND "+_in('t.source_type', ('LOCAL_FOLDER',))+") OR "
        "s.chunk_index IS NULL OR s.total_chunks IS NULL OR s.file_size IS NULL OR s.chunk_size IS NULL OR "
        "s.chunk_index<0 OR s.total_chunks<=0 OR s.chunk_index>=s.total_chunks OR s.file_size<0 OR s.chunk_size<0"),
    'recognition-claim':_source(TABLE_PREFIX+'recognition_claim',
        'claim_task_id recognition_scope claimed_at claimed_by controlled_file_id',
        _in('s.recognition_scope', ('BASIC_INFO','FILE_CATEGORY','FILE_NUMBER')), 's.deleted=0',
        "s.claimed_at IS NULL OR s.claimed_by IS NULL OR s.controlled_file_id IS NULL OR "
        "(s.claim_task_id IS NOT NULL AND (NOT EXISTS(SELECT 1 FROM {db}.`dcc_controlled_file_batch_recognition_task` t "
        "WHERE t.id=s.claim_task_id AND t.tenant_id=s.tenant_id) OR (s.deleted=0 AND EXISTS(SELECT 1 "
        "FROM {db}.`dcc_controlled_file_batch_recognition_task` t WHERE t.id=s.claim_task_id AND t.tenant_id=s.tenant_id "
        "AND "+_in('t.status', ('COMPLETED','FAILED','STOPPED'))+"))))"),
}
COUNT_FIELDS = ('total','softDeleted','pending','terminal','unknown','inconsistent','failedOutcome')


def _catalog(database):
    require(type(database) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}',database),
            'FORMAL_PERSISTED_DATABASE_INVALID')
    return '`'+database+'`'


def snapshot_sql(database, millis):
    db=_catalog(database)
    require(type(millis) is int and 1<=millis<=60000,'FORMAL_PERSISTED_DEADLINE_INVALID')
    rows=[]
    for name,source in SOURCES.items():
        known='COALESCE((('+source['known'].format(db=db)+') AND s.tenant_id IS NOT NULL AND s.tenant_id>=0 AND s.deleted IN (0,1)),FALSE)'
        pending='COALESCE(('+source['pending'].format(db=db)+'),FALSE)'
        inconsistent='COALESCE(('+source['inconsistent'].format(db=db)+'),FALSE)'
        expressions=['COUNT(*)', 'COALESCE(SUM(s.deleted=1),0)',
                     'COALESCE(SUM('+known+' AND '+pending+'),0)',
                     'COALESCE(SUM('+known+' AND NOT '+pending+'),0)',
                     'COALESCE(SUM(NOT '+known+'),0)',
                     'COALESCE(SUM('+inconsistent+'),0)',
                     'COALESCE(SUM(COALESCE(('+source['failed']+'),FALSE)),0)']
        rows.append("SELECT /*+ MAX_EXECUTION_TIME("+str(millis)+") */ '"+name+"',"+','.join(expressions)+
                    ' FROM '+db+'.`'+source['table']+'` s;')
    return ('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ; SET TRANSACTION READ ONLY; '
            'START TRANSACTION WITH CONSISTENT SNAPSHOT;\n'
            "SELECT 'PERSISTED_BEGIN',@@server_uuid,'"+database+"';\n"+'\n'.join(rows)+
            "\nSELECT 'PERSISTED_END',@@server_uuid,'"+database+"'; COMMIT;\n")


def parse_snapshot(raw, database, expected_uuid):
    _catalog(database)
    require(type(expected_uuid) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',expected_uuid),
            'FORMAL_PERSISTED_DATABASE_INVALID')
    require(type(raw) is str and len(raw.encode('utf-8'))<=16384,'FORMAL_PERSISTED_RESULT_INVALID')
    lines=raw.splitlines()
    require(len(lines)==len(SOURCES)+2 and lines[0]=='PERSISTED_BEGIN\t'+expected_uuid+'\t'+database and
        lines[-1]=='PERSISTED_END\t'+expected_uuid+'\t'+database,'FORMAL_PERSISTED_IDENTITY_OR_SET_INVALID')
    counts={}
    for name,line in zip(SOURCES,lines[1:-1]):
        cells=line.split('\t')
        require(len(cells)==8 and cells[0]==name and all(re.fullmatch('0|[1-9][0-9]{0,18}',v) for v in cells[1:]),
                'FORMAL_PERSISTED_RESULT_INVALID')
        values=dict(zip(COUNT_FIELDS,map(int,cells[1:])))
        total=values['total']
        require(total<2**63 and all(v<=total for v in values.values()) and
            values['pending']+values['terminal']+values['unknown']==total,'FORMAL_PERSISTED_COUNT_INVALID')
        require(values['unknown']==0,'FORMAL_PERSISTED_UNKNOWN_STATE')
        counts[name]=values
    confirmed=all(v['pending']==0 and v['inconsistent']==0 for v in counts.values())
    return {'schemaVersion':'release-selected-persisted-observation/v1','database':database,'databaseUuid':expected_uuid,
        'sourceTables':{name:source['table'] for name,source in SOURCES.items()},'counts':counts,
        'countsSha256':hashlib.sha256(snapshot._canonical_bytes(counts)).hexdigest(),
        'selectedTablesTerminalConfirmed':confirmed,'failedOutcomeCount':sum(v['failedOutcome'] for v in counts.values()),
        'allTenantsIncluded':True,'softDeletedIncluded':True,'fullDrain':False,'releaseReady':False,
        'hostWritersVerified':False,'productionEvidence':False}


def _schema(mysql, database):
    db=_catalog(database); seen=mysql.query('SHOW TABLES FROM '+db+';').splitlines()
    require(len(seen)==len(set(seen)) and all(s['table'] in seen for s in SOURCES.values()),
            'FORMAL_PERSISTED_TABLE_REQUIRED')
    result={}
    for source in SOURCES.values():
        raw=mysql.query('DESCRIBE '+db+'.`'+source['table']+'`;')
        require(len(raw.encode('utf-8'))<=16384,'FORMAL_PERSISTED_SCHEMA_INVALID')
        rows=[line.split('\t') for line in raw.splitlines()]
        names=[r[0] for r in rows]
        require(rows and all(len(r)==6 for r in rows) and len(names)==len(set(names)) and
                set(source['columns']).issubset(names),'FORMAL_PERSISTED_COLUMN_REQUIRED')
        result[source['table']]=raw
    names=','.join("'"+s['table']+"'" for s in SOURCES.values())
    engines=mysql.query("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA='"+
                        database+"' AND TABLE_NAME IN ("+names+") ORDER BY TABLE_NAME;")
    rows=[line.split('\t') for line in engines.splitlines()]
    require(len(rows)==len(SOURCES) and all(len(r)==2 and r[1]=='InnoDB' for r in rows) and
            {r[0] for r in rows}=={s['table'] for s in SOURCES.values()},'FORMAL_PERSISTED_INNODB_REQUIRED')
    return {'descriptions':result,'engines':engines}


def observe_selected_work(mysql, database, expected_uuid, *, guard, seconds):
    require(callable(guard) and type(seconds) is int and 1<=seconds<=60,'FORMAL_PERSISTED_GUARD_REQUIRED')
    token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(seconds))
    try:
        guard(); before=_schema(mysql,database); guard()
        millis=max(1,int(snapshot.observation_timeout(seconds)*1000))
        raw=mysql.query(snapshot_sql(database,millis))
        result=parse_snapshot(raw,database,expected_uuid)
        guard(); require(_schema(mysql,database)==before,'FORMAL_PERSISTED_SCHEMA_CHANGED')
        snapshot.observation_timeout(1)
        return result
    finally:
        snapshot.observation_deadline.reset(token)


def run_approved_persisted_observation(path, expected_sha256):
    """Explicit v9 observation, bracketed by actual v8 OBSERVE; never CLOSE."""
    import formal_boot_state as boot
    from formal_filesystem_watchdog import require_native_runtime
    from formal_live_control import _validate_request, run_approved_live_control
    from formal_capture_producer import read_credential
    require_native_runtime(); snapshot.require(os.geteuid()==0,'FORMAL_PERSISTED_ROOT_REQUIRED')
    require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256),
            'FORMAL_PERSISTED_APPROVAL_REQUIRED')
    raw,identity=boot._read_secure(path,0o600,16384); request=_strict_json(raw)
    require(hashlib.sha256(raw).hexdigest()==expected_sha256 and type(request) is dict and set(request)==
        {'schemaVersion','action','claimRoot','claimBinding','totalSeconds','database','mysqlContainerId',
         'mysqlCredentialFile','liveObservationRequestFile','liveObservationRequestSha256'} and
        request['schemaVersion']=='release-formal-capture-request/v9' and
        request['action']=='observe-selected-persisted-work' and type(request['totalSeconds']) is int and
        1<=request['totalSeconds']<=60,'FORMAL_PERSISTED_REQUEST_INVALID')
    _catalog(request['database'])
    require(type(request['mysqlContainerId']) is str and re.fullmatch('[0-9a-f]{64}',request['mysqlContainerId']) and
            type(request['liveObservationRequestSha256']) is str and
            re.fullmatch('[0-9a-f]{64}',request['liveObservationRequestSha256']),'FORMAL_PERSISTED_REQUEST_INVALID')
    live_raw,live_identity=boot._read_secure(request['liveObservationRequestFile'],0o600,16384)
    require(hashlib.sha256(live_raw).hexdigest()==request['liveObservationRequestSha256'],
            'FORMAL_PERSISTED_LIVE_APPROVAL_CHANGED')
    live=_strict_json(live_raw); _validate_request(live)
    require(live['action']=='observe-live-admission' and live['claimRoot']==request['claimRoot'] and
            live['claimBinding']==request['claimBinding'],'FORMAL_PERSISTED_LIVE_BINDING_CHANGED')
    credential_raw,credential_identity=boot._read_secure(request['mysqlCredentialFile'],0o600,16384)
    token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(request['totalSeconds']))
    claim=None
    try:
        def inputs():
            require(boot._read_secure(path,0o600,16384)==(raw,identity) and
                boot._read_secure(request['liveObservationRequestFile'],0o600,16384)==(live_raw,live_identity) and
                boot._read_secure(request['mysqlCredentialFile'],0o600,16384)==(credential_raw,credential_identity),
                'FORMAL_PERSISTED_INPUT_CHANGED')
            snapshot.observation_timeout(1)
        def live_observe():
            inputs(); value=run_approved_live_control(request['liveObservationRequestFile'],request['liveObservationRequestSha256'])
            require(value['liveAdmissionClosed'] is True and value['closeCompletionConfirmed'] is True and
                    value['observation']['outstandingWork']==0 and value['observation']['unresolvedCodeCount']==0,
                    'FORMAL_PERSISTED_TRACKED_WORK_PENDING')
            inputs(); return value
        root=boot._absolute(request['claimRoot'])
        with boot._directory(root): pass
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True)
        journal=snapshot._canonical_bytes(claim.events)
        root_identity=claim._root_identity; lock_identity=claim._lock_identity
        def same_claim():
            claim.assert_owned()
            require(claim._root_identity==root_identity and claim._lock_identity==lock_identity and
                snapshot._canonical_bytes(claim.events)==journal,'FORMAL_PERSISTED_CLAIM_CHANGED')
        allowed={'shared-container-scope','external-caller-scope','shared-health-scope','external-health-scope',
            'maintenance-originals-bound','ingress-scope'} | {
            'boot-'+role+suffix for role in boot.ROLES for suffix in ('-bound','-close-intent','-closed')} | {
            'live-'+role+suffix for role in boot.ROLES for suffix in ('-close-intent','-closed')}
        require(all(e['step'] in allowed for e in claim.events),'FORMAL_PERSISTED_STAGE_INVALID')
        originals=_strict_json(claim._read(root/'shared-container-original.json'))
        original=originals['mysql']
        require(original['id']==request['mysqlContainerId'],'FORMAL_PERSISTED_CONTAINER_CHANGED')
        original_raw=claim._read(root/'shared-container-original.json')
        require(snapshot._claim_event(claim,'shared-container-scope')['details']==
                {'scopeSha256':hashlib.sha256(original_raw).hexdigest()},'FORMAL_PERSISTED_CONTAINER_CHANGED')
        hashes=snapshot._claim_event(claim,'maintenance-originals-bound')['details']['originalFileSha256']
        require(type(hashes) is dict and set(hashes)==boot.ORIGINALS,'FORMAL_PERSISTED_ORIGINALS_REQUIRED')
        pins={}
        for name,digest in hashes.items():
            pair=boot._read_secure(root/name,0o600,16384)
            require(hashlib.sha256(pair[0]).hexdigest()==digest,'FORMAL_PERSISTED_ORIGINALS_CHANGED')
            pins[root/name]=(0o600,16384,pair)
        closed=snapshot._claim_event(claim,'boot-'+live['role']+'-closed')['details']
        current_path=boot._absolute(closed['path']); pair=boot._read_secure(current_path,0o644,4096)
        require(hashlib.sha256(pair[0]).hexdigest()==closed['binding']['closedSha256'] and
            {'device':pair[1][0],'inode':pair[1][1]}==closed['publishedIdentity'],'FORMAL_PERSISTED_CLOSED_CHANGED')
        pins[current_path]=(0o644,4096,pair)
        saved=root/('live-'+live['role']+'-close-response.json'); pair=boot._read_secure(saved,0o600,8192)
        require(hashlib.sha256(pair[0]).hexdigest()==snapshot._claim_event(claim,'live-'+live['role']+'-closed')
            ['details']['responseSha256'],'FORMAL_PERSISTED_COMPLETION_CHANGED')
        pins[saved]=(0o600,8192,pair)
        saved=root/('boot-'+live['role']+'-original-open.json'); pair=boot._read_secure(saved,0o600,4096)
        require(hashlib.sha256(pair[0]).hexdigest()==closed['savedOriginalSha256'],'FORMAL_PERSISTED_ORIGINALS_CHANGED')
        pins[saved]=(0o600,4096,pair)
        grant_path=boot._absolute(live['control']['grantFile']); pair=boot._read_secure(grant_path,0o600,16384)
        require(hashlib.sha256(pair[0]).hexdigest()==live['control']['grantSha256'],'FORMAL_PERSISTED_GRANT_CHANGED')
        pins[grant_path]=(0o600,16384,pair)
        def pinned_files():
            for selected_path,(mode,limit,pair) in pins.items():
                require(boot._read_secure(selected_path,mode,limit)==pair,'FORMAL_PERSISTED_ORIGINALS_CHANGED')
            same_claim(); snapshot.observation_timeout(1)
        pinned_files(); inputs(); same_claim()
        claim.close(); claim=None
        before_live=live_observe()
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True)
        pinned_files()
        def guard():
            same_claim(); inputs()
            observed=snapshot.inspect_formal_container(request['mysqlContainerId'])
            snapshot._container_stable(observed)
            require(observed==original,'FORMAL_PERSISTED_CONTAINER_CHANGED')
            require(claim._read(root/'shared-container-original.json')==original_raw,'FORMAL_PERSISTED_CONTAINER_CHANGED')
            inputs(); pinned_files()
        guard()
        mysql=snapshot.PrivateDockerMySql(request['mysqlContainerId'],read_credential(request['mysqlCredentialFile']),timeout=5)
        selected=observe_selected_work(mysql,request['database'],request['claimBinding']['databaseUuid'],
                                       guard=guard,seconds=request['totalSeconds'])
        guard(); claim.close(); claim=None
        after_live=live_observe()
        require(before_live['epoch']==after_live['epoch'] and before_live['observation']['identity']==after_live['observation']['identity'],
                'FORMAL_PERSISTED_LIVE_IDENTITY_CHANGED')
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True); guard(); inputs(); pinned_files()
        snapshot.observation_timeout(1)
        return {'state':'SELECTED_PERSISTED_WORK_OBSERVED_ONLY','epoch':after_live['epoch'],'selectedObservation':selected,
                'liveBeforeSha256':before_live['responseSha256'],'liveAfterSha256':after_live['responseSha256'],
                'fullDrain':False,'releaseReady':False,'hostWritersVerified':False,'productionEvidence':False,
                'claimReleased':False,'serviceActionsPerformed':False}
    except OSError:
        raise FormalSnapshotError('FORMAL_PERSISTED_IO_FAILED_RETAINED') from None
    finally:
        if claim is not None: claim.close()
        snapshot.observation_deadline.reset(token)
