"""Repository side originals and content ownership across complete ancestry."""
from pathlib import Path
import re

from recovery_engine import canonical, check_pin, parse, pin, pinned_json, require, repository_guard

BINDING_FIELDS = {'schemaVersion', 'backupId', 'generationId', 'repositoryPointPin', 'manifestPin',
                  'sourceScopePin', 'recoveryMaterialPin', 'objectContentIndexPin'}
INDEX_FIELDS = {'schemaVersion', 'backupId', 'generationId', 'sourceIdentity', 'recoveryPoint', 'pointType',
                'parentExportIndexPin', 'inventoryPin', 'exportReceiptPin', 'contentPins',
                'changedContentSha256', 'repositoryBound', 'manifestPin'}
BASE_FIELDS = {'bucket', 'key', 'kind', 'versionId', 'isLatest', 'lastModified'}
CONTENT_FIELDS = {'size', 'etag', 'sha256', 'repositoryPath', 'headers'}
RECEIPT_FIELDS = {'buckets', 'state', 'inventoryBytes', 'inventorySha256', 'versionCount',
                 'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount', 'multipartObservationsSha256'}


def repository_binding(point_pin, point, policy):
    refs = policy.get('repositoryBindingPinsByManifestSha256')
    require(type(refs) is dict and point['manifestPin']['sha256'] in refs, 'RECOVERY_REPOSITORY_BINDING_REQUIRED')
    ref = refs[point['manifestPin']['sha256']]
    active = repository_guard()
    if active is not None: active.archive_pins(point_pin, [ref])
    raw = check_pin(ref); value = parse(raw)
    require(type(value) is dict and set(value) == BINDING_FIELDS and raw == canonical(value) and
            value['schemaVersion'] == 'RecoveryRepositoryBinding/v1' and
            value['repositoryPointPin'] == point_pin and value['manifestPin'] == point['manifestPin'] and
            value['backupId'] == point['backupId'] and value['generationId'] == point['generationId'] and
            value['sourceScopePin'] == policy['sourceScopePin'], 'RECOVERY_REPOSITORY_BINDING_INVALID')
    if active is not None:
        active.archive_pins(point_pin, [value['recoveryMaterialPin'], value['objectContentIndexPin']])
    for name in ('recoveryMaterialPin', 'objectContentIndexPin', 'sourceScopePin'): check_pin(value[name])
    return ref, value


def object_index_chain(chain, policy, *, guard=lambda: None, verify_content=True):
    result = []; previous = previous_ref = source = None
    for point_ref, point, material, material_ref in chain:
        guard(); binding_ref, binding = repository_binding(point_ref, point, policy)
        require(binding['recoveryMaterialPin'] == material_ref and binding['sourceScopePin'] == material['sourceScopePin'],
                'MATERIAL_REPOSITORY_BINDING_MISMATCH')
        index_ref = binding['objectContentIndexPin']; raw = check_pin(index_ref); index = parse(raw)
        require(type(index) is dict and set(index) == INDEX_FIELDS and raw == canonical(index) and
                index['schemaVersion'] == 'backup-capture-object-index/v1' and index['repositoryBound'] is True and
                index['manifestPin'] == point['manifestPin'] and index['backupId'] == point['backupId'] and
                index['generationId'] == point['generationId'] and index['pointType'] == point['pointType'] and
                index['recoveryPoint'] == material['recoveryPoint'] and
                index['inventoryPin'] == material['objects']['inventoryPin'] and
                index['exportReceiptPin'] == material['objects']['exportReceiptPin'] and
                type(index['sourceIdentity']) is str and index['sourceIdentity'] and
                type(index['contentPins']) is dict and type(index['changedContentSha256']) is list,
                'REPOSITORY_OBJECT_INDEX_INVALID')
        source_scope = pinned_json(binding['sourceScopePin'])
        source_identity = pinned_json(source_scope['sourceIdentityPin'])
        require(material['sourceFingerprint'] == index['sourceIdentity'] == source_identity['sourceFingerprint'],
                'OBJECT_INDEX_REPOSITORY_SOURCE_MISMATCH')
        capture = pinned_json(material['objects']['capturePointPin'])
        require(capture['sourceIdentity'] == index['sourceIdentity'] and capture['backupId'] == point['backupId'] and
                capture['generationId'] == point['generationId'] and capture['commonRecoveryPoint'] == index['recoveryPoint'],
                'OBJECT_INDEX_CAPTURE_SOURCE_BINDING_INVALID')
        if source is None: source = index['sourceIdentity']
        require(index['sourceIdentity'] == source, 'OBJECT_INDEX_CROSS_SOURCE')
        changed = index['changedContentSha256']
        require(all(type(sha) is str and re.fullmatch('[0-9a-f]{64}', sha) for sha in changed) and
                len(changed) == len(set(changed)) and set(changed) <= set(index['contentPins']),
                'OBJECT_INDEX_CHANGED_SCOPE_INVALID')
        require(index['parentExportIndexPin'] == previous_ref, 'OBJECT_INDEX_PARENT_MISMATCH')
        if previous is None:
            require(point['pointType'] == 'FULL' and set(changed) == set(index['contentPins']), 'OBJECT_INDEX_FULL_SCOPE_INVALID')
        for sha, ref in index['contentPins'].items():
            guard(); require(type(sha) is str and re.fullmatch('[0-9a-f]{64}', sha) and ref['sha256'] == sha,
                             'OBJECT_INDEX_CONTENT_INVALID')
            if sha in changed:
                expected_path = Path(point['manifestPin']['path']).parent.parent/'semantic-capture'/'objects'/'sha256'/sha[:2]/(sha+'.bin')
                require(Path(ref['path']) == expected_path and ref in point['payloadRefs'], 'OBJECT_INDEX_CURRENT_CONTENT_NOT_ARCHIVED')
            else:
                require(previous is not None and ref == previous['contentPins'].get(sha), 'OBJECT_INDEX_PARENT_CONTENT_OWNERSHIP_INVALID')
            if verify_content:
                require(pin(ref['path']) == ref, 'PIN_CHANGED')
        receipt, groups = indexed_export(index, point['payloadRefs'], guard=guard)
        result.append((binding_ref, index_ref, index, receipt, groups)); previous = index; previous_ref = index_ref
    return result


def indexed_export(index, payloads, *, guard):
    """Read full logical history through exact indexed Pins, including parent bytes."""
    receipt = pinned_json(index['exportReceiptPin']); raw = check_pin(index['inventoryPin'])
    require(set(receipt) == RECEIPT_FIELDS and receipt['state'] == 'S3_EXPORTED_PENDING_RESTORE_PROOF' and
            receipt['inventorySha256'] == index['inventoryPin']['sha256'] and receipt['inventoryBytes'] == len(raw) and
            all(type(receipt[name]) is int and receipt[name] >= 0 for name in
                ('inventoryBytes', 'versionCount', 'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount')),
            'OBJECT_INDEX_EXPORT_RECEIPT_INVALID')
    buckets = receipt['buckets']
    require(type(buckets) is list and buckets and len(buckets) == len(set(buckets)) and
            all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', b) for b in buckets),
            'OBJECT_INDEX_BUCKET_SCOPE_INVALID')
    groups = {}; identities = set(); contents = set(); versions = deletes = size = 0
    for line in raw.splitlines():
        guard(); row = parse(line)
        require(type(row) is dict and row.get('kind') in ('version', 'delete-marker') and
                set(row) == BASE_FIELDS | (CONTENT_FIELDS if row['kind'] == 'version' else set()) and
                all(type(row[key]) is str and row[key] and '\0' not in row[key] for key in ('bucket', 'key', 'versionId', 'lastModified')) and
                row['bucket'] in buckets and type(row['isLatest']) is bool and
                re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z', row['lastModified']), 'OBJECT_INDEX_HISTORY_INVALID')
        identity = (row['bucket'], row['key'], row['versionId'])
        require(identity not in identities, 'OBJECT_INDEX_DUPLICATE_VERSION'); identities.add(identity)
        groups.setdefault(identity[:2], []).append(row)
        if row['kind'] == 'delete-marker': deletes += 1; continue
        sha = row['sha256']; ref = index['contentPins'].get(sha)
        require(type(row['size']) is int and 0 <= row['size'] <= 1024**4 and ref is not None and
                (ref['sha256'], ref['bytes']) == (sha, row['size']) and type(row['etag']) is str and row['etag'] and '\0' not in row['etag'] and
                row['repositoryPath'] == 'objects/sha256/'+sha[:2]+'/'+sha+'.bin' and type(row['headers']) is dict and
                all(type(k) is str and type(v) is str and not any(c in k+v for c in '\r\n\0') and
                    (k.startswith(('x-amz-meta-', 'x-amz-object-lock-', 'x-amz-server-side-encryption', 'x-amz-storage-class')) or
                     k in ('content-type', 'content-encoding', 'content-disposition', 'cache-control', 'expires'))
                    for k, v in row['headers'].items()), 'OBJECT_INDEX_CONTENT_METADATA_INVALID')
        contents.add(sha); versions += 1; size += row['size']
    require(contents == set(index['contentPins']) and
            (receipt['versionCount'], receipt['deleteMarkerCount'], receipt['totalVersionBytes'], receipt['uniqueContentCount']) ==
            (versions, deletes, size, len(contents)) and
            all(history[0]['isLatest'] and sum(row['isLatest'] for row in history) == 1 for history in groups.values()),
            'OBJECT_INDEX_COUNTS_OR_HISTORY_INVALID')
    for ref in (index['inventoryPin'], index['exportReceiptPin']):
        require(ref in payloads, 'OBJECT_INDEX_METADATA_NOT_ARCHIVED')
    multipart_refs = [ref for ref in payloads if ref['sha256'] == receipt['multipartObservationsSha256'] and
                      Path(ref['path']).name == 'multipart-observations.json']
    require(len(multipart_refs) == 1, 'OBJECT_INDEX_MULTIPART_ORIGINAL_REQUIRED')
    multipart = pinned_json(multipart_refs[0])
    require(set(multipart) == {'state', 'before', 'after'} and multipart['state'] == 'MULTIPART_EMPTY_POINT_OBSERVATIONS',
            'OBJECT_INDEX_MULTIPART_INVALID')
    for phase in ('before', 'after'):
        require(type(multipart[phase]) is list and len(multipart[phase]) == len(buckets), 'OBJECT_INDEX_MULTIPART_INVALID')
        for bucket, observation in zip(buckets, multipart[phase]):
            require(set(observation) == {'bucket', 'state', 'httpStatus', 'rawSha256', 'rawBytes', 'maxUploads', 'uploadCount', 'isTruncated', 'scope'} and
                    observation['bucket'] == bucket and observation['state'] == 'NO_MULTIPART_UPLOAD_OBSERVED' and
                    observation['scope'] == 'WHOLE_BUCKET_FROM_START' and type(observation['httpStatus']) is int and observation['httpStatus'] == 200 and
                    type(observation['rawBytes']) is int and 0 < observation['rawBytes'] <= 1024*1024 and
                    type(observation['rawSha256']) is str and re.fullmatch('[0-9a-f]{64}', observation['rawSha256']) and
                    type(observation['maxUploads']) is int and observation['maxUploads'] == 1 and
                    type(observation['uploadCount']) is int and observation['uploadCount'] == 0 and observation['isTruncated'] is False,
                    'OBJECT_INDEX_MULTIPART_INVALID')
    guard(); return receipt, groups
