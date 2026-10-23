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
        raw = stream.read(limit+1)
    require(len(raw) <= limit, 'BACKUP_INTERFACE_RECORD_TOO_LARGE')
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
    inventory = point['fileInventory']
    recovery_point = point['commonRecoveryPoint']
    files = {name: file_pin(source_root, entries, name) for name, marker in entries.items() if marker != 'directory'}
    capture_pin = files['payload/capture-content-point.json']
    inventory_pin = files['payload/capture-file-inventory.json']
    physical = {name: files['payload/minio-physical/'+name] for name in point['fileDelta']['changedPaths']
        if inventory[name]['kind'] == 'file'}
    delta = point['databaseDelta']
    data_name = ('payload/source-affected-data.json' if delta.get('dataObservation') == 'AFFECTED_TABLES_V1'
        else 'payload/011-source-data.json')
    start = None if point['pointType'] == 'FULL' else delta['parentPosition']
    raw_sql = None if start is None else files['payload/database.sql.incremental.raw']
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
    by_source_path = {reference['path']: archived_file_pins[name]
        for name, reference in inputs['archiveFilePins'].items()}
    def archived(reference):
        return by_source_path[reference['path']]
    changed = set(source_index['changedContentSha256'])
    contents = {sha: archived(reference) if sha in changed else reference
        for sha, reference in source_index['contentPins'].items()}
    return dict(source_index, inventoryPin=archived(source_index['inventoryPin']),
        exportReceiptPin=archived(source_index['exportReceiptPin']), contentPins=contents,
        repositoryBound=True, manifestPin=manifest_pin)


def assemble_repository_capture_records(inputs, manifest, *, manifest_pin, archived_file_pins,
                                        original_records, parent_object_index):
    """W03 handoff: pure assembly from actual bytes read back from NAS.

    Caller publishes both returned documents using its existing metadata writer
    and allocation guard. This function performs no NAS acceptance or restore.
    """
    material = assemble_repository_recovery_material(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins, supplemental=inputs['semanticSupplement'], original_records=original_records)
    reference = pin(inputs['objectContentIndexPin']); raw = original_records[reference['path']]
    require(type(raw) is bytes, 'BACKUP_INTERFACE_BYTES_REQUIRED')
    source_index = strict_document(raw, 64*1024*1024)
    index = assemble_repository_object_index(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=archived_file_pins, source_index=source_index, parent_object_index=parent_object_index)
    return dict(recoveryMaterial=material, objectContentIndex=index)


def assemble_repository_recovery_material(inputs, manifest, *, manifest_pin, archived_file_pins,
                                          supplemental, original_records):
    """Validate metadata and bytes. Native custody/acceptance belongs to callers."""
    by_source_path = {reference['path']: archived_file_pins[name]
        for name, reference in inputs['archiveFilePins'].items()}
    def archived(reference):
        return by_source_path[reference['path']]
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
