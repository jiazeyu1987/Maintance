"""Finite comparison of pinned GET exports, never physical restore authority.

Whole raw capture (including .minio.sys), approved independent target, started
bucket protection and continuous exclusion remain separate owner obligations.
No S3 writes, version mapping, standalone CLI or formal completion is provided.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

from formal_s3_export import _strict_json, _require_empty_multipart_observation
from formal_snapshot_linux import require, FormalSnapshotError, current_owner_guard, _canonical_bytes

SHA = re.compile('[0-9a-f]{64}')
BUCKET = re.compile('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]')
RECEIPT_FIELDS = {'buckets', 'state', 'inventoryBytes', 'inventorySha256', 'versionCount',
                  'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount', 'multipartObservationsSha256'}
BASE_FIELDS = {'bucket', 'key', 'kind', 'versionId', 'isLatest', 'lastModified'}
CONTENT_FIELDS = {'size', 'etag', 'sha256', 'repositoryPath', 'headers'}


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_nlink, info.st_uid, info.st_gid)


def _path(path):
    path = Path(path).absolute()
    require(all(not part.is_symlink() and part.resolve() == part for part in (path, *path.parents)),
            'FORMAL_PHYSICAL_READBACK_PATH_INVALID')
    return path


def _read(path, limit, current, tracked, *, keep=True):
    current(); path = _path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
            stat.S_IMODE(before.st_mode) == 0o600 and before.st_size <= limit,
            'FORMAL_PHYSICAL_READBACK_PRIVATE_FILE_REQUIRED')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    chunks = []; size = 0; digest = hashlib.sha256()
    try:
        require(_identity(os.fstat(descriptor)) == _identity(before), 'FORMAL_PHYSICAL_READBACK_FILE_CHANGED')
        while True:
            current(); chunk = os.read(descriptor, 1024*1024); current()
            if not chunk: break
            size += len(chunk)
            require(size <= limit, 'FORMAL_PHYSICAL_READBACK_FILE_TOO_LARGE')
            digest.update(chunk)
            if keep: chunks.append(chunk)
        current()
        require(_identity(os.fstat(descriptor)) == _identity(before) == _identity(_path(path).stat()) and
                size == before.st_size, 'FORMAL_PHYSICAL_READBACK_FILE_CHANGED')
    finally:
        os.close(descriptor)
    fingerprint = (digest.hexdigest(), size, _identity(before))
    require(path not in tracked or tracked[path] == fingerprint, 'FORMAL_PHYSICAL_READBACK_FILE_CHANGED')
    tracked[path] = fingerprint
    return b''.join(chunks) if keep else None, fingerprint


def _load(root, inventory_sha, receipt_sha, current, tracked):
    root = _path(root)
    require(root.is_dir(), 'FORMAL_PHYSICAL_READBACK_PATH_INVALID')
    raw, fingerprint = _read(root/'export-receipt.json', 16384, current, tracked)
    require(fingerprint[0] == receipt_sha, 'FORMAL_PHYSICAL_READBACK_APPROVED_EXPORT_CHANGED')
    receipt = _strict_json(raw)
    require(type(receipt) is dict and set(receipt) == RECEIPT_FIELDS and
            receipt['state'] == 'S3_EXPORTED_PENDING_RESTORE_PROOF' and
            all(type(receipt[key]) is int and receipt[key] >= 0 for key in
                ('inventoryBytes', 'versionCount', 'deleteMarkerCount', 'totalVersionBytes', 'uniqueContentCount')) and
            all(type(receipt[key]) is str and SHA.fullmatch(receipt[key]) for key in
                ('inventorySha256', 'multipartObservationsSha256')),
            'FORMAL_PHYSICAL_READBACK_RECEIPT_INVALID')
    buckets = receipt['buckets']
    require(type(buckets) is list and buckets and all(type(bucket) is str and BUCKET.fullmatch(bucket) for bucket in buckets) and
            len(buckets) == len(set(buckets)), 'FORMAL_PHYSICAL_READBACK_BUCKETS_INVALID')
    raw, fingerprint = _read(root/'versions.jsonl', 256*1024*1024, current, tracked)
    require(fingerprint[:2] == (inventory_sha, receipt['inventoryBytes']) and receipt['inventorySha256'] == inventory_sha,
            'FORMAL_PHYSICAL_READBACK_APPROVED_EXPORT_CHANGED')
    lines = raw.splitlines()
    require(len(lines) <= 500000*len(buckets) and all(lines), 'FORMAL_PHYSICAL_READBACK_INVENTORY_INVALID')
    groups = {}; identities = set(); contents = set()
    counts = dict(versionCount=0, deleteMarkerCount=0, totalVersionBytes=0, uniqueContentCount=0)
    for line in lines:
        current(); row = _strict_json(line)
        require(type(row) is dict and row.get('kind') in ('version', 'delete-marker'),
                'FORMAL_PHYSICAL_READBACK_INVENTORY_INVALID')
        require(set(row) == BASE_FIELDS | (CONTENT_FIELDS if row['kind'] == 'version' else set()) and
                all(type(row[key]) is str and row[key] and '\0' not in row[key] for key in
                    ('bucket', 'key', 'versionId', 'lastModified')) and
                row['bucket'] in buckets and type(row['isLatest']) is bool and
                re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z', row['lastModified']),
                'FORMAL_PHYSICAL_READBACK_INVENTORY_INVALID')
        identity = (row['bucket'], row['key'], row['versionId'])
        require(identity not in identities, 'FORMAL_PHYSICAL_READBACK_DUPLICATE_VERSION')
        identities.add(identity); groups.setdefault(identity[:2], []).append(row)
        if row['kind'] == 'delete-marker':
            counts['deleteMarkerCount'] += 1
            continue
        require(type(row['size']) is int and 0 <= row['size'] <= 1024**4 and
                type(row['etag']) is str and row['etag'] and '\0' not in row['etag'] and
                type(row['sha256']) is str and SHA.fullmatch(row['sha256']) and
                row['repositoryPath'] == 'objects/sha256/'+row['sha256'][:2]+'/'+row['sha256']+'.bin' and
                type(row['headers']) is dict and all(type(key) is str and type(value) is str and
                    not any(c in key+value for c in '\r\n\0') and
                    (key.startswith(('x-amz-meta-', 'x-amz-object-lock-', 'x-amz-server-side-encryption', 'x-amz-storage-class')) or
                     key in ('content-type', 'content-encoding', 'content-disposition', 'cache-control', 'expires'))
                    for key, value in row['headers'].items()), 'FORMAL_PHYSICAL_READBACK_CONTENT_INVALID')
        content = root/row['repositoryPath']
        if row['sha256'] not in contents:
            _, value = _read(content, 1024**4, current, tracked, keep=False)
            require(value[:2] == (row['sha256'], row['size']), 'FORMAL_PHYSICAL_READBACK_CONTENT_CHANGED')
            contents.add(row['sha256'])
        else:
            require(tracked[content][:2] == (row['sha256'], row['size']), 'FORMAL_PHYSICAL_READBACK_CONTENT_CHANGED')
        counts['versionCount'] += 1; counts['totalVersionBytes'] += row['size']
    counts['uniqueContentCount'] = len(contents)
    require(all(receipt[key] == value for key, value in counts.items()) and
            all(sum(row['isLatest'] for row in history) == 1 and history[0]['isLatest'] for history in groups.values()),
            'FORMAL_PHYSICAL_READBACK_COUNTS_OR_HISTORY_INVALID')
    raw, fingerprint = _read(root/'multipart-observations.json', 2*1024*1024, current, tracked)
    require(fingerprint[0] == receipt['multipartObservationsSha256'], 'FORMAL_PHYSICAL_READBACK_MULTIPART_CHANGED')
    multipart = _strict_json(raw)
    require(type(multipart) is dict and set(multipart) == {'state', 'before', 'after'} and
            multipart['state'] == 'MULTIPART_EMPTY_POINT_OBSERVATIONS', 'FORMAL_PHYSICAL_READBACK_MULTIPART_INVALID')
    for name in ('before', 'after'):
        observations = multipart[name]
        require(type(observations) is list and len(observations) == len(buckets), 'FORMAL_PHYSICAL_READBACK_MULTIPART_INVALID')
        for bucket, value in zip(buckets, observations):
            current(); _require_empty_multipart_observation(value, bucket)
    return receipt, groups


def compare_physical_restore_exports(source, restored, *, source_inventory_sha256,
        source_export_receipt_sha256, restored_inventory_sha256, restored_export_receipt_sha256, guard):
    """Exact finite readback only; injected current checks are not new approval."""
    def current(): current_owner_guard(guard, code='FORMAL_PHYSICAL_READBACK_OWNER_REQUIRED')
    current()
    require(os.name == 'posix', 'FORMAL_PHYSICAL_READBACK_NATIVE_LINUX_REQUIRED')
    pins = (source_inventory_sha256, source_export_receipt_sha256,
            restored_inventory_sha256, restored_export_receipt_sha256)
    require(all(type(value) is str and SHA.fullmatch(value) for value in pins), 'FORMAL_PHYSICAL_READBACK_PINS_REQUIRED')
    source = _path(source); restored = _path(restored)
    require(source != restored and source not in restored.parents and restored not in source.parents,
            'FORMAL_PHYSICAL_READBACK_PATH_OVERLAP')
    tracked = {}
    original, source_groups = _load(source, *pins[:2], current, tracked)
    readback, restored_groups = _load(restored, *pins[2:], current, tracked)
    require(set(original['buckets']) == set(readback['buckets']) and source_groups == restored_groups,
            'FORMAL_PHYSICAL_READBACK_VERSION_HISTORY_MISMATCH')
    for path, expected in tuple(tracked.items()):
        _, value = _read(path, expected[1], current, tracked, keep=False)
        require(value == expected, 'FORMAL_PHYSICAL_READBACK_FILE_CHANGED')
    current()
    ordered = [row for key in sorted(source_groups) for row in source_groups[key]]
    result = dict(state='PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF',
        buckets=sorted(original['buckets']), versionCount=original['versionCount'],
        deleteMarkerCount=original['deleteMarkerCount'], totalVersionBytes=original['totalVersionBytes'],
        uniqueContentCount=original['uniqueContentCount'], exactVersionIdentityVerified=True,
        versionHistorySha256=hashlib.sha256(_canonical_bytes(ordered)).hexdigest(),
        sourceInventorySha256=pins[0], sourceExportReceiptSha256=pins[1],
        restoredInventorySha256=pins[2], restoredExportReceiptSha256=pins[3],
        physicalCaptureVerified=False, continuousHostExclusionVerified=False,
        applicationVerified=False, productionEvidence=False)
    current(); return result
