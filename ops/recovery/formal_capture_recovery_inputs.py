"""Bind captured payload originals to repository paths and recovery materials.

The capture index is archived before source restoration. Repository material
binding happens only after the caller has the original manifest and verified
archived file pins. Missing business/object/classification evidence fails
explicitly; an index alone never declares a recoverable repository point.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat

from formal_normal_owner import canonical, pin, require, strict_document
from formal_capture_incremental import validate_file_inventory, validate_position, canonical as capture_canonical

SUPPLEMENT_FIELDS = {'sourceFingerprint', 'sourceScopePin', 'versionPins', 'referenceInventoryPin',
                     'derivedInventoryPin', 'objectInventoryPin', 'objectExportReceiptPin'}


def original_bytes(reference, *, limit=64*1024*1024, allow_empty=False):
    pin(reference)
    path = Path(reference['path'])
    require(path.is_absolute() and all(not node.is_symlink() and node.resolve() == node for node in
            (path, *path.parents)), 'BACKUP_INTERFACE_SOURCE_CHANGED')
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
            (0 if allow_empty else 1) <= before.st_size <= limit,
            'BACKUP_INTERFACE_SOURCE_CHANGED')
    with path.open('rb') as stream:
        require(identity(os.fstat(stream.fileno())) == identity(before), 'BACKUP_INTERFACE_SOURCE_CHANGED')
        raw = stream.read(limit+1)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'BACKUP_INTERFACE_SOURCE_CHANGED')
    require(identity(path.lstat()) == identity(before) and len(raw) == reference['bytes'] and
            hashlib.sha256(raw).hexdigest() == reference['sha256'], 'BACKUP_INTERFACE_SOURCE_CHANGED')
    return raw


def file_pin(root, entries, name):
    require(type(root) is str and root.startswith('/') and '\\' not in root and
            str(PurePosixPath(root)) == root and type(name) is str and name and
            '\\' not in name and all(part not in ('', '.', '..') for part in name.split('/')) and
            not PurePosixPath(name).is_absolute(), 'BACKUP_INTERFACE_SCHEMA_INVALID')
    marker = entries.get(name)
    require(type(marker) is str and re.fullmatch(r'file\|(?:0|[1-9][0-9]*)\|[0-9a-f]{64}', marker),
            'BACKUP_INTERFACE_COMPONENT_FAILED')
    _, size, digest = marker.split('|')
    return pin(dict(path=str(PurePosixPath(root)/name), bytes=int(size), sha256=digest))


def capture_recovery_inputs(point, *, source_root, entries, supplemental):
    require(type(point) is dict and point['schemaVersion'] == 'backup-capture-point/v1' and
            point['pointType'] in ('FULL', 'INCREMENTAL') and point['sourceRestored'] is False and
            point['disasterRecoveryVerified'] is False and type(entries) is dict,
            'BACKUP_INTERFACE_BINDING_INVALID')
    validate_position(point['databaseEnd'])
    inventory = validate_file_inventory(point['fileInventory'])
    recovery_point = 'sha256:'+hashlib.sha256(capture_canonical(dict(database=point['databaseEnd'], files=inventory))).hexdigest()
    require(point['commonRecoveryPoint'] == recovery_point, 'BACKUP_INTERFACE_BINDING_INVALID')
    files = {name: file_pin(source_root, entries, name) for name, marker in entries.items() if marker != 'directory'}
    require({'payload/capture-content-point.json', 'payload/capture-file-inventory.json',
        'payload/database.sql.gz', 'recovery-materials/index.json',
        'payload/original-application-images.tar', 'original-configs/config-capture-stage.json'} <= set(files),
        'BACKUP_INTERFACE_COMPONENT_FAILED')
    capture_pin = files['payload/capture-content-point.json']
    inventory_pin = files['payload/capture-file-inventory.json']
    for reference, document in ((capture_pin, point), (inventory_pin, inventory)):
        raw = capture_canonical(document)
        require(reference['bytes'] == len(raw) and reference['sha256'] == hashlib.sha256(raw).hexdigest(),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
    changed = point['fileDelta']['changedPaths']
    require(type(changed) is list and len(changed) == len(set(changed)) and
            set(changed) <= set(inventory), 'BACKUP_INTERFACE_BINDING_INVALID')
    physical = {name: files['payload/minio-physical/'+name] for name in changed if inventory[name]['kind'] == 'file'}
    require({name.removeprefix('payload/minio-physical/') for name in files if
            name.startswith('payload/minio-physical/')} == set(physical), 'BACKUP_INTERFACE_BINDING_INVALID')
    for name, reference in physical.items():
        require(all(reference[key] == inventory[name][key] for key in ('bytes', 'sha256')),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
    delta = point['databaseDelta']
    observation = delta.get('dataObservation')
    require(observation in (None, 'AFFECTED_TABLES_V1') and
        (observation is None or point['pointType'] == 'INCREMENTAL'), 'BACKUP_INTERFACE_BINDING_INVALID')
    data_name = 'payload/011-source-data.json' if observation is None else 'payload/source-affected-data.json'
    require(data_name in files, 'BACKUP_INTERFACE_COMPONENT_FAILED')
    if observation is not None:
        require('payload/database.sql.incremental-scope.json' in files and
            not {'payload/011-source-data.json', 'payload/012-source-data-after.json'} & set(files),
            'BACKUP_INTERFACE_BINDING_INVALID')
    if point['pointType'] == 'FULL':
        require(delta == dict(kind='SQL_FULL', segments=[]) and point['parentPointPin'] is None and
                point['parentRepositoryPointPin'] is None, 'BACKUP_INTERFACE_BINDING_INVALID')
        start = raw_sql = None
    else:
        require(delta['kind'] == 'BINLOG_SQL' and point['parentPointPin'] is not None and
                point['parentRepositoryPointPin'] is not None, 'BACKUP_INTERFACE_BINDING_INVALID')
        start = validate_position(delta['parentPosition'])
        require('payload/database.sql.incremental.raw' in files, 'BACKUP_INTERFACE_COMPONENT_FAILED')
        raw_sql = files['payload/database.sql.incremental.raw']
        require(all(raw_sql[key] == pin(delta['rawPin'])[key] for key in ('bytes', 'sha256')),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
    require(type(supplemental) is dict and set(supplemental) == SUPPLEMENT_FIELDS and
            all(supplemental[key] in files.values() for key in ('referenceInventoryPin',
                'derivedInventoryPin', 'objectInventoryPin', 'objectExportReceiptPin')) and
            {'semantic-capture/supplement.json', 'semantic-capture/object-content-index.json',
                'semantic-capture/multipart-observations.json'} <= set(files), 'BACKUP_INTERFACE_COMPONENT_FAILED')
    return dict(schemaVersion='backup-capture-recovery-inputs/v1', backupId=point['backupId'],
        generationId=point['generationId'], pointType=point['pointType'], sourceIdentity=point['sourceIdentity'],
        recoveryPoint=recovery_point, sourceDatabaseUuid=point['databaseEnd']['databaseUuid'],
        parentRepositoryPointPin=point['parentRepositoryPointPin'], capturePointPin=capture_pin,
        fileInventoryPin=inventory_pin, filePayloadPins=physical,
        database=dict(method='FORMAL_SQL_FULL' if start is None else 'BINLOG_SQL', startPosition=start,
            endPosition=point['databaseEnd'], sqlPin=files['payload/database.sql.gz'], rawSqlPin=raw_sql,
            expectedDataPin=files[data_name]),
        materialIndexPin=files['recovery-materials/index.json'],
        configurationPins=[files[name] for name in sorted(files) if name.startswith('original-configs/')],
        imagePins=[files['payload/original-application-images.tar']], archiveFilePins=files,
        semanticSupplement=supplemental, objectContentIndexPin=files['semantic-capture/object-content-index.json'])


def bind_repository_recovery_material(inputs, manifest, *, manifest_pin, archived_file_pins):
    return bind_repository_capture_records(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins)['recoveryMaterial']


def bind_repository_capture_records(inputs, manifest, *, manifest_pin, archived_file_pins):
    """W03 calls with actual NAS readback pins and W02-generated input records.

    The supplemental records are explicit provisioned source scope, supported
    versions and real same-point logical/reference/derived inventories. This
    function reads their pinned original files, without manufacturing evidence.
    """
    from formal_filesystem_watchdog import require_native_runtime
    require_native_runtime()
    supplemental = inputs['semanticSupplement']
    require(type(supplemental) is dict and set(supplemental) == SUPPLEMENT_FIELDS and
            type(supplemental['versionPins']) is list and supplemental['versionPins'],
            'BACKUP_INTERFACE_COMPONENT_FAILED')
    records = {}
    for reference in (supplemental['sourceScopePin'], *supplemental['versionPins']):
        pin(reference)
        require(reference['path'] not in records, 'BACKUP_INTERFACE_BINDING_INVALID')
        records[reference['path']] = original_bytes(reference)
    source = strict_document(records[supplemental['sourceScopePin']['path']], 64*1024*1024)
    identity = pin(source['sourceIdentityPin'])
    require(identity['path'] not in records, 'BACKUP_INTERFACE_BINDING_INVALID')
    records[identity['path']] = original_bytes(identity)
    # Read generated records from verified NAS files, never reopen expired
    # source-host claim paths after archive close/source restoration.
    database_records = []
    if inputs['database']['expectedDataPin']['path'].endswith('/payload/source-affected-data.json'):
        database_records = [inputs['capturePointPin'], inputs['database']['expectedDataPin'],
            inputs['archiveFilePins']['payload/database.sql.incremental-scope.json']]
    for reference in (*(supplemental[key] for key in ('referenceInventoryPin', 'derivedInventoryPin',
            'objectInventoryPin', 'objectExportReceiptPin')), inputs['objectContentIndexPin'], *database_records):
        names = [name for name, value in inputs['archiveFilePins'].items() if value == reference]
        require(len(names) == 1, 'BACKUP_INTERFACE_BINDING_INVALID')
        archived = pin(archived_file_pins[names[0]])
        require(all(archived[key] == reference[key] for key in ('bytes', 'sha256')),
            'BACKUP_INTERFACE_SOURCE_CHANGED')
        records[reference['path']] = original_bytes(archived,
            allow_empty=reference == supplemental['objectInventoryPin'])
    index = strict_document(records[inputs['objectContentIndexPin']['path']], 64*1024*1024)
    parent = None if index['parentExportIndexPin'] is None else strict_document(
        original_bytes(index['parentExportIndexPin']), 64*1024*1024)
    return assemble_repository_capture_records(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins, original_records=records, parent_object_index=parent)


def assemble_repository_object_index(inputs, manifest, *, manifest_pin, archived_file_pins,
                                      source_index, parent_object_index):
    """Rebase changed content; retain only exact verified parent content pins.

    The returned record is published beside RecoveryMaterial after the original
    manifest. Including its own manifest pin inside that manifest would create
    a circular hash. Its explicit pin is the next point's parentExportIndexPin.
    """
    raw = capture_canonical(source_index); expected = pin(inputs['objectContentIndexPin'])
    require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'] and
        type(source_index) is dict and set(source_index) == {'schemaVersion', 'backupId', 'generationId',
            'sourceIdentity', 'recoveryPoint', 'pointType', 'parentExportIndexPin', 'inventoryPin',
            'exportReceiptPin', 'contentPins', 'changedContentSha256', 'repositoryBound', 'manifestPin'} and
        source_index['schemaVersion'] == 'backup-capture-object-index/v1' and
        source_index['repositoryBound'] is False and source_index['manifestPin'] is None and
        all(source_index[key] == inputs[key] for key in
            ('backupId', 'generationId', 'pointType', 'sourceIdentity', 'recoveryPoint')) and
        source_index['inventoryPin'] == inputs['semanticSupplement']['objectInventoryPin'] and
        source_index['exportReceiptPin'] == inputs['semanticSupplement']['objectExportReceiptPin'] and
        type(source_index['contentPins']) is dict and type(source_index['changedContentSha256']) is list and
        len(source_index['changedContentSha256']) == len(set(source_index['changedContentSha256'])) and
        set(source_index['changedContentSha256']) <= set(source_index['contentPins']),
        'BACKUP_INTERFACE_BINDING_INVALID')
    require(hashlib.sha256(canonical(manifest)).hexdigest() == pin(manifest_pin)['sha256'] and
        len(canonical(manifest)) == manifest_pin['bytes'] and
        manifest['backupId'] == inputs['backupId'] and manifest['generationId'] == inputs['generationId'] and
        manifest['commonRecoveryPoint'] == inputs['recoveryPoint'], 'BACKUP_INTERFACE_BINDING_INVALID')
    changed = set(source_index['changedContentSha256']); parent_reference = source_index['parentExportIndexPin']
    if inputs['pointType'] == 'FULL':
        require(parent_reference is None and parent_object_index is None and changed == set(source_index['contentPins']),
            'BACKUP_INTERFACE_BINDING_INVALID')
    else:
        require(parent_reference is not None and type(parent_object_index) is dict and
            len(canonical(parent_object_index)) == pin(parent_reference)['bytes'] and
            hashlib.sha256(canonical(parent_object_index)).hexdigest() == parent_reference['sha256'] and
            parent_object_index['schemaVersion'] == 'backup-capture-object-index/v1' and
            parent_object_index['repositoryBound'] is True and
            parent_object_index['generationId'] == inputs['generationId'] and
            parent_object_index['sourceIdentity'] == inputs['sourceIdentity'] and
            parent_object_index['backupId'] != inputs['backupId'], 'BACKUP_INTERFACE_BINDING_INVALID')
    def archived(reference):
        names = [name for name, value in inputs['archiveFilePins'].items() if value == reference]
        require(len(names) == 1 and names[0] in archived_file_pins, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        result = pin(archived_file_pins[names[0]])
        require(all(result[key] == reference[key] for key in ('bytes', 'sha256')) and
            result in manifest['payloadRefs'], 'BACKUP_INTERFACE_SOURCE_CHANGED')
        return result
    archive_shas = {name.rsplit('/', 1)[1].removesuffix('.bin') for name in inputs['archiveFilePins']
        if name.startswith('semantic-capture/objects/sha256/')}
    require(archive_shas == changed, 'BACKUP_INTERFACE_BINDING_INVALID')
    contents = {}
    for sha, reference in source_index['contentPins'].items():
        require(type(sha) is str and re.fullmatch('[0-9a-f]{64}', sha) and pin(reference)['sha256'] == sha,
            'BACKUP_INTERFACE_BINDING_INVALID')
        if sha in changed:
            name = 'semantic-capture/objects/sha256/'+sha[:2]+'/'+sha+'.bin'
            require(inputs['archiveFilePins'].get(name) == reference, 'BACKUP_INTERFACE_SOURCE_CHANGED')
            contents[sha] = archived(reference)
        else:
            require(reference == parent_object_index['contentPins'].get(sha), 'BACKUP_INTERFACE_SOURCE_CHANGED')
            contents[sha] = reference
    return {**source_index, 'inventoryPin': archived(source_index['inventoryPin']),
        'exportReceiptPin': archived(source_index['exportReceiptPin']), 'contentPins': contents,
        'repositoryBound': True, 'manifestPin': manifest_pin}


def assemble_repository_capture_records(inputs, manifest, *, manifest_pin, archived_file_pins,
                                        original_records, parent_object_index):
    """W03 handoff: pure assembly from actual bytes read back from NAS.

    Caller publishes both returned documents using its existing metadata writer
    and allocation guard. This function performs no NAS acceptance or restore.
    """
    material = assemble_repository_recovery_material(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins, supplemental=inputs['semanticSupplement'], original_records=original_records)
    reference = pin(inputs['objectContentIndexPin']); raw = original_records[reference['path']]
    require(type(raw) is bytes and len(raw) == reference['bytes'] and
        hashlib.sha256(raw).hexdigest() == reference['sha256'], 'BACKUP_INTERFACE_SOURCE_CHANGED')
    source_index = strict_document(raw, 64*1024*1024)
    inventory_raw = original_records[inputs['semanticSupplement']['objectInventoryPin']['path']]
    objects = [strict_document(line, 1048576) for line in inventory_raw.splitlines()]
    require({r['sha256'] for r in objects if r['kind'] == 'version'} == set(source_index['contentPins']) and
        all(source_index['contentPins'][r['sha256']]['bytes'] == r['size'] for r in objects if r['kind'] == 'version'),
        'BACKUP_INTERFACE_BINDING_INVALID')
    index = assemble_repository_object_index(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins, source_index=source_index, parent_object_index=parent_object_index)
    return dict(recoveryMaterial=material, objectContentIndex=index)


def assemble_repository_recovery_material(inputs, manifest, *, manifest_pin, archived_file_pins,
                                          supplemental, original_records):
    """Validate metadata and bytes. Native custody/acceptance belongs to callers."""
    pin(manifest_pin)
    raw = canonical(manifest)
    require(manifest_pin['bytes'] == len(raw) and manifest_pin['sha256'] == hashlib.sha256(raw).hexdigest() and
            inputs['schemaVersion'] == 'backup-capture-recovery-inputs/v1' and
            manifest['schemaVersion'] == 'RepositoryManifest/v1' and
            all(inputs[key] == manifest[key] for key in ('backupId', 'generationId', 'pointType')) and
            inputs['recoveryPoint'] == manifest['commonRecoveryPoint'], 'BACKUP_INTERFACE_BINDING_INVALID')
    originals = dict(inputs['archiveFilePins'])
    require(inputs['capturePointPin']['path'].endswith('/payload/capture-content-point.json'),
            'BACKUP_INTERFACE_BINDING_INVALID')
    inputs_raw = capture_canonical(inputs)
    originals['capture-recovery-inputs.json'] = dict(
        path=str(PurePosixPath(inputs['capturePointPin']['path']).parents[1]/'capture-recovery-inputs.json'),
        bytes=len(inputs_raw), sha256=hashlib.sha256(inputs_raw).hexdigest())
    require(type(archived_file_pins) is dict and set(archived_file_pins) == set(originals) and
            type(manifest['payloadRefs']) is list and len(manifest['payloadRefs']) == len(archived_file_pins) and
            len({pin(reference)['path'] for reference in archived_file_pins.values()}) == len(archived_file_pins),
            'BACKUP_INTERFACE_BINDING_INVALID')
    for name, reference in archived_file_pins.items():
        pin(reference)
        require(reference in manifest['payloadRefs'] and
                all(reference[key] == pin(originals[name])[key] for key in ('bytes', 'sha256')),
                'BACKUP_INTERFACE_SOURCE_CHANGED')
    require(len({reference['path'] for reference in originals.values()}) == len(originals),
            'BACKUP_INTERFACE_BINDING_INVALID')
    by_source_path = {reference['path']: archived_file_pins[name] for name, reference in originals.items()}
    def archived(reference):
        pin(reference)
        require(reference['path'] in by_source_path and
                any(reference == value for value in originals.values()), 'BACKUP_INTERFACE_SOURCE_CHANGED')
        return by_source_path[reference['path']]
    require(type(supplemental) is dict and set(supplemental) == SUPPLEMENT_FIELDS and
            type(supplemental['sourceFingerprint']) is str and supplemental['sourceFingerprint'] and
            type(supplemental['versionPins']) is list and supplemental['versionPins'] and
            supplemental['versionPins'] == manifest['versionPins'], 'BACKUP_INTERFACE_COMPONENT_FAILED')
    require(inputs['semanticSupplement'] == supplemental, 'BACKUP_INTERFACE_BINDING_INVALID')
    require(type(original_records) is dict, 'BACKUP_INTERFACE_COMPONENT_FAILED')
    def raw_original(reference):
        pin(reference)
        require(reference['path'] in original_records, 'BACKUP_INTERFACE_COMPONENT_FAILED')
        raw = original_records[reference['path']]
        require(type(raw) is bytes and len(raw) == reference['bytes'] and
                hashlib.sha256(raw).hexdigest() == reference['sha256'], 'BACKUP_INTERFACE_SOURCE_CHANGED')
        return raw
    def original_document(reference):
        return strict_document(raw_original(reference), 64*1024*1024)
    if inputs['database']['expectedDataPin']['path'].endswith('/payload/source-affected-data.json'):
        capture = original_document(inputs['capturePointPin'])
        expected = original_document(inputs['database']['expectedDataPin'])
        require(capture['databaseEnd'] == inputs['database']['endPosition'] and
            capture['commonRecoveryPoint'] == inputs['recoveryPoint'] and
            capture['pointType'] == inputs['pointType'], 'BACKUP_INTERFACE_BINDING_INVALID')
        from formal_data_evidence import incremental_observation_tables
        scope = original_document(inputs['archiveFilePins']['payload/database.sql.incremental-scope.json'])
        incremental_observation_tables(expected, scope, capture, expected['schema']['database'])
    source = original_document(supplemental['sourceScopePin'])
    identity = original_document(source['sourceIdentityPin'])
    require(source['sourceIdentityPin'] == manifest['sourceIdentityPin'] and
            type(source['endpointHosts']) is list and source['endpointHosts'] and
            all(type(endpoint) is str and endpoint for endpoint in source['endpointHosts']) and
            identity['sourceFingerprint'] == supplemental['sourceFingerprint'] and
            identity['databaseUuid'] == inputs['sourceDatabaseUuid'], 'BACKUP_INTERFACE_BINDING_INVALID')
    reference = original_document(supplemental['referenceInventoryPin'])
    derived = original_document(supplemental['derivedInventoryPin'])
    require(reference['schemaVersion'] == 'RecoveryReferenceInventory/v1' and reference['complete'] is True and
            reference['recoveryPoint'] == inputs['recoveryPoint'] and
            derived['schemaVersion'] == 'RecoveryDerivedInventory/v1' and derived['complete'] is True and
            derived['recoveryPoint'] == inputs['recoveryPoint'] and set(derived['classes']) == {'redis', 'queue'},
            'BACKUP_INTERFACE_BINDING_INVALID')
    require(type(reference['databaseRows']) is list and type(reference['objectReferences']) is list,
            'BACKUP_INTERFACE_SCHEMA_INVALID')
    for item in derived['classes'].values():
        require(type(item) is dict and item['classification'] in ('REBUILD', 'NOT_PRESENT', 'RESTORE') and
                type(item['requiredForBusiness']) is bool and type(item['payloadPins']) is list,
                'BACKUP_INTERFACE_SCHEMA_INVALID')
        if item['classification'] == 'NOT_PRESENT':
            require(item['requiredForBusiness'] is False and item['payloadPins'] == [] and item['executorKey'] is None,
                    'BACKUP_INTERFACE_BINDING_INVALID')
        else:
            require(type(item['executorKey']) is str and item['executorKey'] and
                    (item['payloadPins'] and item['executorKey'] == 'REDIS_DUMP_ABSOLUTE_EXPIRY'
                        if item['classification'] == 'RESTORE' else item['rebuildFrom'] in ('DATABASE', 'OBJECTS')) and
                    all(archived(value) in manifest['payloadRefs'] for value in item['payloadPins']),
                    'BACKUP_INTERFACE_BINDING_INVALID')
    object_raw = raw_original(supplemental['objectInventoryPin'])
    receipt = original_document(supplemental['objectExportReceiptPin'])
    receipt_fields = {'buckets', 'state', 'inventoryBytes', 'inventorySha256', 'versionCount',
        'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount', 'multipartObservationsSha256'}
    require(type(receipt) is dict and set(receipt) == receipt_fields and
            receipt['state'] == 'S3_EXPORTED_PENDING_RESTORE_PROOF' and
            receipt['inventoryBytes'] == len(object_raw) and
            receipt['inventorySha256'] == supplemental['objectInventoryPin']['sha256'] and
            all(type(receipt[key]) is int and receipt[key] >= 0 for key in
                ('inventoryBytes', 'versionCount', 'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount')) and
            type(receipt['multipartObservationsSha256']) is str and
            re.fullmatch('[0-9a-f]{64}', receipt['multipartObservationsSha256']) and
            type(receipt['buckets']) is list and receipt['buckets'] and
            all(type(bucket) is str and bucket for bucket in receipt['buckets']),
            'BACKUP_INTERFACE_BINDING_INVALID')
    # MinIO inventory is JSONL, including valid empty-bucket inventories. It
    # must not be interpreted as a single JSON object or invented by the index.
    for line in object_raw.splitlines():
        require(type(strict_document(line, 1048576)) is dict, 'BACKUP_INTERFACE_SCHEMA_INVALID')
    for value in supplemental['versionPins']:
        original_document(value)

    database = dict(inputs['database'])
    for key in ('sqlPin', 'expectedDataPin'):
        database[key] = archived(database[key])
    if database['rawSqlPin'] is not None:
        database['rawSqlPin'] = archived(database['rawSqlPin'])
    database['capturePointPin'] = archived(inputs['capturePointPin'])
    material = dict(schemaVersion='RecoveryMaterial/v1', manifestPin=manifest_pin,
        pointType=inputs['pointType'], recoveryPoint=inputs['recoveryPoint'],
        sourceFingerprint=supplemental['sourceFingerprint'], sourceDatabaseUuid=inputs['sourceDatabaseUuid'],
        sourceScopePin=supplemental['sourceScopePin'], versionPins=supplemental['versionPins'],
        payloadPins=manifest['payloadRefs'], database=database,
        objects=dict(method='PHYSICAL_FILES', capturePointPin=archived(inputs['capturePointPin']),
            fileInventoryPin=archived(inputs['fileInventoryPin']),
            filePayloadPins={name: archived(value) for name, value in inputs['filePayloadPins'].items()},
            inventoryPin=archived(supplemental['objectInventoryPin']),
            exportReceiptPin=archived(supplemental['objectExportReceiptPin'])),
        referenceInventoryPin=archived(supplemental['referenceInventoryPin']),
        derivedInventoryPin=archived(supplemental['derivedInventoryPin']))
    return material
