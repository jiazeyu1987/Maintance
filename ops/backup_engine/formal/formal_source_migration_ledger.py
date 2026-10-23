"""Full migration-history projection bound to the existing typed data multiset.

This observes data, never changes history or grants migration/restore authority.
The capture caller must supply environment from an independently approved formal
target and maintain source/claim/host exclusion throughout every observation.
"""
import hashlib
import json
from pathlib import Path
import re

from formal_data_evidence import SHA, UUID, _cell, compare_data
from formal_schema_evidence import identifier, _meta_query, _decode_metadata
from formal_snapshot_linux import FormalSnapshotError, _canonical_bytes, require
from formal_s3_export import _strict_json

TABLE = 'infra_release_migration'
KINDS = {
    'id': 'bigint', 'release_tag': 'varchar(128)', 'target_environment': 'varchar(32)',
    'status': 'varchar(32)', 'started_at': 'datetime', 'finished_at': 'datetime',
    'error_message': 'text', 'operation_id': 'varchar(128)', 'creator': 'varchar(64)',
    'create_time': 'datetime', 'updater': 'varchar(64)', 'update_time': 'datetime',
    'deleted': 'bit(1)', 'tenant_id': 'bigint', 'migration_id': 'varchar(191)',
    'file_name': 'varchar(512)', 'sha256': 'varchar(64)',
}
FIELDS = {'schemaVersion', 'sourceEnvironment', 'database', 'observationIdentity',
          'fullDataObservationSha256', 'tableMultiset', 'rows', 'observationSha256',
          'applicationVerified', 'productionEvidence'}
ROW_FIELDS = {'id', 'targetEnvironment', 'migrationId', 'fileName', 'sha256', 'status',
              'deleted', 'releaseTag', 'operationId', 'fullRowSha256'}


def _digest(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _positive_id(value):
    require(type(value) is str and re.fullmatch('[1-9][0-9]{0,18}', value) and
            int(value) <= 9223372036854775807, 'FORMAL_SOURCE_LEDGER_ROW_INVALID')
    return int(value)


def _validate(value, *, lab=False):
    require(type(value) is dict and set(value) == FIELDS and
        value['schemaVersion'] == ('backup-lab-source-migration-ledger/v1' if lab else 'release-formal-source-migration-ledger/v1') and
        value['sourceEnvironment'] == ('backup-lab' if lab else 'prod') and value['applicationVerified'] is False and
        value['productionEvidence'] is False and
        _digest({k: v for k, v in value.items() if k != 'observationSha256'}) == value['observationSha256'],
        'FORMAL_SOURCE_LEDGER_PROOF_CHANGED')
    identity = value['observationIdentity']; multiset = value['tableMultiset']; rows = value['rows']
    require(type(identity) is dict and set(identity) == {'containerId', 'databaseUuid'} and
        type(identity['containerId']) is str and SHA.fullmatch(identity['containerId']) and
        type(identity['databaseUuid']) is str and UUID.fullmatch(identity['databaseUuid']) and
        type(value['database']) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}', value['database']) and
        type(value['fullDataObservationSha256']) is str and SHA.fullmatch(value['fullDataObservationSha256']) and
        type(multiset) is dict and set(multiset) == {'rows', 'jsonNodes', 'multisetSha256'} and
        type(multiset['rows']) is int and multiset['rows'] >= 0 and
        type(multiset['jsonNodes']) is int and multiset['jsonNodes'] == 0 and
        type(multiset['multisetSha256']) is str and SHA.fullmatch(multiset['multisetSha256']) and
        type(rows) is list and len(rows) == multiset['rows'], 'FORMAL_SOURCE_LEDGER_PROOF_INVALID')
    ids = set(); keys = set(); tokens = []
    for row in rows:
        require(type(row) is dict and set(row) == ROW_FIELDS and type(row['id']) is int and
            0 < row['id'] <= 9223372036854775807 and type(row['deleted']) is bool and
            all(type(row[k]) is str and 0 < len(row[k]) <= limit and '\0' not in row[k]
                for k, limit in (('targetEnvironment', 32), ('migrationId', 191), ('fileName', 512),
                                 ('status', 32), ('releaseTag', 128), ('operationId', 128))) and
            all(type(row[k]) is str and SHA.fullmatch(row[k]) for k in ('sha256', 'fullRowSha256')),
            'FORMAL_SOURCE_LEDGER_ROW_INVALID')
        key = (row['targetEnvironment'], row['migrationId'])
        require(row['id'] not in ids and key not in keys, 'FORMAL_SOURCE_LEDGER_DUPLICATE_IDENTITY')
        ids.add(row['id']); keys.add(key); tokens.append(bytes.fromhex(row['fullRowSha256']))
    require(rows == sorted(rows, key=lambda row: row['id']), 'FORMAL_SOURCE_LEDGER_ORDER_CHANGED')
    checksum = hashlib.sha256(b'row-multiset/v1\n')
    for token in sorted(tokens): checksum.update(token)
    require(checksum.hexdigest() == multiset['multisetSha256'], 'FORMAL_SOURCE_LEDGER_MULTISET_CHANGED')
    return value


def observe_migration_ledger(mysql, database, expected_uuid, *, source_environment, full_data, guard, max_rows):
    require(source_environment == 'prod', 'FORMAL_SOURCE_LEDGER_INPUT_INVALID')
    return _observe_migration_ledger(mysql, database, expected_uuid, source_environment=source_environment,
        full_data=full_data, guard=guard, max_rows=max_rows, lab=False)


def observe_lab_migration_ledger(mysql, database, expected_uuid, *, source_scope, full_data, guard, max_rows):
    from formal_backup_lab import require_authority
    authority = require_authority(source_scope)
    require(source_scope['database'] == database and source_scope['databaseUuid'] == expected_uuid,
            'FORMAL_SOURCE_LEDGER_INPUT_INVALID')
    def checked(): authority.check(); guard(); authority.check()
    return _observe_migration_ledger(mysql, database, expected_uuid, source_environment='backup-lab',
        full_data=full_data, guard=checked, max_rows=max_rows, lab=True)


def _observe_migration_ledger(mysql, database, expected_uuid, *, source_environment, full_data, guard, max_rows, lab):
    require(source_environment == ('backup-lab' if lab else 'prod') and type(source_environment) is str and callable(guard) and
        type(max_rows) is int and 0 < max_rows <= 10000000 and
        type(expected_uuid) is str and UUID.fullmatch(expected_uuid), 'FORMAL_SOURCE_LEDGER_INPUT_INVALID')
    try:
        compare_data(full_data, full_data)
        columns = [c for c in full_data['schema']['catalog']['COLUMNS'] if c[0] == TABLE]
        require([TABLE, 'BASE TABLE'] in full_data['schema']['catalog']['TABLES'] and
            TABLE in full_data['tables'] and len(columns) == len(KINDS) and
            {c[1] for c in columns} == set(KINDS) and
            all(len(c) == 11 and c[2] == str(i + 1) and c[4] == KINDS[c[1]] and
                c[3] == KINDS[c[1]].split('(')[0] and c[10] == '' for i, c in enumerate(columns)) and
            full_data['observationIdentity'] == {'containerId': mysql.container, 'databaseUuid': expected_uuid} and
            full_data['schema']['database'] == database and
            full_data['tables'][TABLE]['rows'] <= max_rows and full_data['tables'][TABLE]['jsonNodes'] == 0,
            'FORMAL_SOURCE_LEDGER_SOURCE_INVALID')
    except (KeyError, TypeError, IndexError, FormalSnapshotError):
        raise FormalSnapshotError('FORMAL_SOURCE_LEDGER_SOURCE_INVALID') from None
    def query(sql):
        guard()
        result = mysql.schema_query(sql, database=database, expected_uuid=expected_uuid, max_bytes=16 * 1024 * 1024)
        guard()
        return result
    description = query('DESCRIBE ' + identifier(TABLE) + ';')
    require(type(description) is list and len(description) == len(columns) and
        all(type(r) is list and len(r) == 6 and all(type(v) is str for v in r) and
            r[0] == c[1] and r[1] == c[4] and r[2] == c[7] and r[5] == c[9]
            for r, c in zip(description, columns)),
        'FORMAL_SOURCE_LEDGER_SCHEMA_CHANGED')
    # DESCRIBE's untyped "NULL" cannot distinguish SQL NULL from literal text.
    # Keep the existing typed metadata encoding and verify every catalog field
    # freshly, including defaults, extra attributes and generated expressions.
    fields=['TABLE_NAME','COLUMN_NAME','ORDINAL_POSITION','DATA_TYPE','COLUMN_TYPE',
        'CHARACTER_SET_NAME','COLLATION_NAME','IS_NULLABLE','COLUMN_DEFAULT','EXTRA','GENERATION_EXPRESSION']
    current=_decode_metadata(query(_meta_query('COLUMNS',fields,'CAST(TABLE_NAME AS BINARY),ORDINAL_POSITION')))
    require([c for c in current if c[0] == TABLE] == columns, 'FORMAL_SOURCE_LEDGER_SCHEMA_CHANGED')
    selected = ['CAST(`id` AS CHAR)', '`target_environment`', '`migration_id`', '`file_name`',
                '`sha256`', '`status`', 'CAST(`deleted` AS UNSIGNED)', '`release_tag`', '`operation_id`']
    selected.append("SHA2(CONCAT('row/v1:'," + ','.join(_cell(c) for c in columns) + '),256)')
    physical = query('SELECT ' + ','.join(selected) + ' FROM ' + identifier(TABLE) + ' ORDER BY `id`;')
    require(type(physical) is list and len(physical) == full_data['tables'][TABLE]['rows'] and
        len(physical) <= max_rows, 'FORMAL_SOURCE_LEDGER_ROW_COUNT_CHANGED')
    rows = []
    for r in physical:
        require(type(r) is list and len(r) == 10 and r[6] in ('0', '1') and
            type(r[-1]) is str and SHA.fullmatch(r[-1]), 'FORMAL_SOURCE_LEDGER_ROW_INVALID')
        rows.append(dict(id=_positive_id(r[0]), targetEnvironment=r[1], migrationId=r[2], fileName=r[3],
            sha256=r[4], status=r[5], deleted=r[6] == '1', releaseTag=r[7], operationId=r[8],
            fullRowSha256=hashlib.sha256(b'complete-row/v1:' + r[-1].encode() + b'\n').hexdigest()))
    value = dict(schemaVersion='backup-lab-source-migration-ledger/v1' if lab else 'release-formal-source-migration-ledger/v1', sourceEnvironment=source_environment,
        database=database, observationIdentity=dict(full_data['observationIdentity']),
        fullDataObservationSha256=full_data['observationSha256'], tableMultiset=dict(full_data['tables'][TABLE]),
        rows=sorted(rows, key=lambda row: row['id']), applicationVerified=False, productionEvidence=False)
    value['observationSha256'] = _digest(value)
    return _validate(value, lab=lab)


def bind_migration_ledger(claim_raw, before, after, sql_sha, source_scope):
    lab = type(source_scope) is dict and source_scope.get('schemaVersion') == 'backup-lab-source-scope/v1'
    if lab:
        from formal_backup_lab import require_authority
        require_authority(source_scope)
    _validate(before, lab=lab); _validate(after, lab=lab)
    claim = _strict_json(claim_raw)
    require(before == after and type(claim) is dict and
        set(claim) == {'operationId', 'sourceFingerprint', 'databaseUuid', 'minioContainerId'} and
        type(claim['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', claim['operationId']) and
        all(type(claim[k]) is str and SHA.fullmatch(claim[k]) for k in ('sourceFingerprint', 'minioContainerId')) and
        before['observationIdentity']['databaseUuid'] == claim['databaseUuid'] and
        type(sql_sha) is str and SHA.fullmatch(sql_sha) and type(source_scope) is dict and
        set(source_scope) == {'schemaVersion', 'environment', 'targetRawSha256', 'targetFingerprint', 'database', 'databaseUuid'} | ({'labContextPin'} if lab else set()) and
        source_scope['schemaVersion'] == ('backup-lab-source-scope/v1' if lab else 'release-formal-approved-source/v1') and
        source_scope['environment'] == before['sourceEnvironment'] == ('backup-lab' if lab else 'prod') and
        source_scope['targetFingerprint'] == claim['sourceFingerprint'] and
        source_scope['database'] == before['database'] and source_scope['databaseUuid'] == claim['databaseUuid'] and
        all(type(source_scope[k]) is str and SHA.fullmatch(source_scope[k]) for k in ('targetRawSha256', 'targetFingerprint')),
        'FORMAL_SOURCE_LEDGER_BINDING_CHANGED')
    return dict(schemaVersion='backup-lab-source-migration-binding/v1' if lab else 'release-formal-source-migration-binding/v1', sourceScope=dict(source_scope),
        operationId=claim['operationId'], claimBindingSha256=hashlib.sha256(claim_raw).hexdigest(),
        sourceFingerprint=claim['sourceFingerprint'], databaseUuid=claim['databaseUuid'],
        mysqlContainerId=before['observationIdentity']['containerId'], database=before['database'], sqlSha256=sql_sha,
        sourceBeforeFileSha256=_digest(before), sourceAfterFileSha256=_digest(after),
        ledgerObservationSha256=before['observationSha256'], tableMultiset=dict(before['tableMultiset']))


def approved_source_scope(target_raw, approved_sha, claim_raw, database):
    return _approved_source_scope(target_raw, approved_sha, claim_raw, database, lab_context_pin=None)


def approved_lab_source_scope(target_raw, approved_sha, claim_raw, database, lab_context_pin):
    from formal_backup_lab import pin, LAB_ROOT
    pin(lab_context_pin)
    target=_strict_json(target_raw)
    require(type(target) is dict and target.get('host')=='172.30.30.59' and
        target.get('project')=='brlab-20261012' and
        all(type(target.get(k)) is str and Path(LAB_ROOT) in Path(target[k]).parents
            for k in ('root','dataMount','dataRoot','releaseRoot')) and
        type(target.get('containers')) is dict and
        all(type(name) is str and name.startswith('brlab-20261012-') for name in target['containers'].values()),
        'BACKUP_LAB_TARGET_OUTSIDE_SCOPE')
    return _approved_source_scope(target_raw, approved_sha, claim_raw, database, lab_context_pin=lab_context_pin)


def _approved_source_scope(target_raw, approved_sha, claim_raw, database, *, lab_context_pin):
    """The approved digest is supplied independently, never read from the request."""
    try:
        require(type(target_raw) is bytes and 0 < len(target_raw) <= 65536 and
            type(approved_sha) is str and SHA.fullmatch(approved_sha) and
            hashlib.sha256(target_raw).hexdigest() == approved_sha, 'FORMAL_SOURCE_LEDGER_APPROVAL_REQUIRED')
        target = _strict_json(target_raw); claim = _strict_json(claim_raw)
        fields = {'schemaVersion','environment','host','machineId','project','root','dataMount','dataDevice',
                  'dataRoot','releaseRoot','frontendPort','backendPort','database','databaseServerUuid','containers'}
        require(type(target) is dict and set(target) == fields and
            target['schemaVersion'] == 'release-formal-target/v1' and target['environment'] == ('backup-lab' if lab_context_pin is not None else 'prod') and
            all(type(target[k]) is str and target[k] and '\0' not in target[k] for k in
                ('host','machineId','project','root','dataMount','dataDevice','dataRoot','releaseRoot','database','databaseServerUuid')) and
            re.fullmatch('[0-9a-f]{32}', target['machineId']) and
            target['database'] == database and UUID.fullmatch(target['databaseServerUuid']) and
            type(claim) is dict and target['databaseServerUuid'] == claim['databaseUuid'] and
            all(type(target[k]) is int and 1 <= target[k] <= 65535 for k in ('frontendPort','backendPort')) and
            target['frontendPort'] != target['backendPort'] and type(target['containers']) is dict and
            set(target['containers']) == {'mysql','redis','minio','backend','frontend'} and
            all(type(v) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',v) for v in target['containers'].values()),
            'FORMAL_SOURCE_LEDGER_APPROVED_TARGET_CHANGED')
        fingerprint=hashlib.sha256(json.dumps(target,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()
        require(set(claim)=={'operationId','sourceFingerprint','databaseUuid','minioContainerId'} and
            type(claim['operationId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',claim['operationId']) and
            type(claim['minioContainerId']) is str and SHA.fullmatch(claim['minioContainerId']) and
            claim['sourceFingerprint']==fingerprint,'FORMAL_SOURCE_LEDGER_CLAIM_SOURCE_CHANGED')
        result = dict(schemaVersion='backup-lab-source-scope/v1' if lab_context_pin is not None else 'release-formal-approved-source/v1', environment=target['environment'],
            targetRawSha256=approved_sha, targetFingerprint=fingerprint, database=database,
            databaseUuid=target['databaseServerUuid'])
        if lab_context_pin is not None: result['labContextPin'] = dict(lab_context_pin)
        return result
    except (KeyError,TypeError,ValueError):
        raise FormalSnapshotError('FORMAL_SOURCE_LEDGER_APPROVED_TARGET_CHANGED') from None


def read_source_ledger(root, claim_raw, sql_sha, reference, full_data, source_scope):
    """Original SQL/raw receipt references anchor these exclusive private files."""
    from formal_capture_producer import read_private
    names = ('013-source-migration-ledger.json','014-source-migration-ledger-after.json','016-source-migration-binding.json')
    try:
        raw = [read_private(Path(root)/name,64*1024*1024 if i < 2 else 16384) for i,name in enumerate(names)]
        before, after, binding = (_strict_json(value) for value in raw)
        expected = bind_migration_ledger(claim_raw,before,after,sql_sha,source_scope)
        compare_data(full_data,full_data)
        require(binding == expected and raw == [_canonical_bytes(v) for v in (before,after,binding)] and
            type(reference) is dict and reference == dict(bindingSha256=hashlib.sha256(raw[2]).hexdigest(),
                ledgerObservationSha256=before['observationSha256']) and
            before['fullDataObservationSha256'] == full_data['observationSha256'] and
            before['observationIdentity'] == full_data['observationIdentity'] and
            before['database'] == full_data['schema']['database'] and
            before['tableMultiset'] == full_data['tables'][TABLE], 'FORMAL_SOURCE_LEDGER_SOURCE_CHANGED')
        return before, dict(zip(names,raw))
    except (FormalSnapshotError,OSError,KeyError,TypeError,ValueError):
        raise FormalSnapshotError('FORMAL_SOURCE_LEDGER_SOURCE_CHANGED') from None


def compare_restored_ledger(source, target):
    """Full target observation is required; this never grants deployment authority."""
    _validate(source); _validate(target)
    require(source['observationIdentity']['containerId'] != target['observationIdentity']['containerId'] and
        source['observationIdentity']['databaseUuid'] != target['observationIdentity']['databaseUuid'] and
        source['database'] == target['database'] and source['rows'] == target['rows'] and
        source['sourceEnvironment'] == target['sourceEnvironment'] and
        source['tableMultiset'] == target['tableMultiset'], 'FORMAL_SOURCE_LEDGER_RESTORE_CHANGED')
    return dict(schemaVersion='release-formal-restored-migration-ledger/v1',
        sourceIdentity=dict(source['observationIdentity']),targetIdentity=dict(target['observationIdentity']),
        sourceLedgerSha256=source['observationSha256'],targetLedgerSha256=target['observationSha256'],
        tableMultiset=dict(source['tableMultiset']),rowCount=len(source['rows']),
        applicationVerified=False,productionEvidence=False)
