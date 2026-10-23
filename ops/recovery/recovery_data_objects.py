"""Compare a restored physical export with repository-indexed complete history."""
import hashlib
import os
import re
import hmac
from datetime import datetime, timezone
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from recovery_engine import RecoveryError, canonical, parse, pin, require, utc
from recovery_plan_objects import object_index_chain


def _scope(buckets):
    require(type(buckets) is list and buckets and len(buckets) <= 1000 and
        all(type(b) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', b) for b in buckets) and
        len(set(buckets)) == len(buckets), 'BUCKET_SCOPE_INVALID')


def _xml(raw, name):
    require(0 < len(raw) <= 1024*1024 and b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw,
            'BUCKET_XML_INVALID')
    root = ET.fromstring(raw)
    require(root.tag in (name, '{http://s3.amazonaws.com/doc/2006-03-01/}'+name), 'BUCKET_XML_INVALID')
    return root


def _get(client, bucket, configuration, guard, *, absence=None):
    guard()
    response = client._get(bucket, params=[] if configuration is None else [(configuration, '')], expected_absence=absence)
    if type(response) is dict:
        require(response['httpStatus'] == 404 and response['errorCode'] == absence, 'BUCKET_ABSENCE_UNPROVEN')
        guard(); return None, response
    with response:
        require(response.status == 200, 'BUCKET_OBSERVATION_HTTP_INVALID')
        raw = response.read(1024*1024+1)
    require(0 < len(raw) <= 1024*1024, 'BUCKET_OBSERVATION_LIMIT')
    guard()
    return raw, dict(httpStatus=200, rawBytes=len(raw), rawSha256=hashlib.sha256(raw).hexdigest())


def _put_bucket(client, bucket, configuration, body, headers, guard, intent, sequence):
    """Signed native S3 PUT on the already approved isolated client; no retry."""
    guard()
    path = '/'+urllib.parse.quote(bucket, safe='-_.~')
    query = '' if configuration is None else configuration+'='
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); date = stamp[:8]
    sha = hashlib.sha256(body).hexdigest()
    values = dict(headers, host=client.host, **{'x-amz-content-sha256': sha, 'x-amz-date': stamp})
    names = sorted(values); signed = ';'.join(names)
    head = ''.join(name+':'+values[name].strip()+'\n' for name in names)
    request_hash = hashlib.sha256(('PUT\n'+path+'\n'+query+'\n'+head+'\n'+signed+'\n'+sha).encode()).hexdigest()
    scope = date+'/us-east-1/s3/aws4_request'
    sign = lambda key, value: hmac.new(key, value.encode(), hashlib.sha256).digest()
    key = sign(sign(sign(sign(('AWS4'+client._secret).encode(), date), 'us-east-1'), 's3'), 'aws4_request')
    signature = hmac.new(key, ('AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+request_hash).encode(), hashlib.sha256).hexdigest()
    values['Authorization'] = 'AWS4-HMAC-SHA256 Credential='+client._access+'/'+scope+', SignedHeaders='+signed+', Signature='+signature
    request = urllib.request.Request(client.endpoint+path+('?' + query if query else ''), data=body, headers=values, method='PUT')
    record = dict(schemaVersion='RecoveryBucketPreparationInvocation/v1', bucket=bucket,
                  configuration=configuration, requestBytes=len(body), requestSha256=sha,
                  startedAt=utc(), state='NOT_DISPATCHED', actualHttpStatus=None)
    intent('bucket-prepare-%03d-intent.json' % sequence, record)
    guard()
    record['state'] = 'TERMINAL_UNKNOWN'
    try:
        with client._open(request) as response:
            record['actualHttpStatus'] = response.status
            raw = response.read(16385)
            record.update(responseBytes=len(raw), responseSha256=hashlib.sha256(raw).hexdigest())
            require(response.status == 200 and not raw, 'BUCKET_PREPARATION_RESPONSE_INVALID')
        guard()
        record['state'] = 'SUCCEEDED'
        intent('bucket-prepare-%03d-exit.json' % sequence, dict(record, finishedAt=utc()))
    except Exception as error:
        error.unknown = True
        record['state'] = 'TERMINAL_UNKNOWN'
        # Persisting a terminal receipt cannot replace uncertainty of the PUT.
        try: intent('bucket-prepare-%03d-exit.json' % sequence, dict(record, finishedAt=utc()))
        except Exception as recording:
            failure = RecoveryError('BUCKET_PREPARATION_EVIDENCE_FAILED', unknown=True)
            failure.original_code = getattr(error, 'code', type(error).__name__)
            raise failure from recording
        raise


def prepare_buckets(client, buckets, settings, *, guard, intent):
    _scope(buckets)
    require(type(settings) is dict and set(settings) == set(buckets), 'BUCKET_SETTINGS_SCOPE_INVALID')
    for bucket in buckets:
        value = settings[bucket]
        require(type(value) is dict and set(value) == {'versioning', 'objectLockEnabled'} and
            value['versioning'] == 'Enabled' and type(value['objectLockEnabled']) is bool,
            'BUCKET_SETTINGS_INVALID')
    raw, listing = _get(client, '', None, guard)
    root = _xml(raw, 'ListAllMyBucketsResult')
    nodes = [node for node in root if node.tag.split('}')[-1] == 'Buckets']
    require(len(nodes) == 1 and not list(nodes[0]), 'BUCKET_PREPARATION_REQUIRES_EMPTY_TARGET')
    evidence = []
    for index, bucket in enumerate(buckets):
        value = settings[bucket]
        headers = {'x-amz-bucket-object-lock-enabled': 'true'} if value['objectLockEnabled'] else {}
        _put_bucket(client, bucket, None, b'', headers, guard, intent, index*2)
        body = b'<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Status>Enabled</Status></VersioningConfiguration>'
        _put_bucket(client, bucket, 'versioning', body, {}, guard, intent, index*2+1)
        try:
            guard(); versioning = client.replica_configuration(bucket, 'versioning')
            guard(); lock = client.replica_configuration(bucket, 'object-lock')
            require(versioning['status'] == 'Enabled' and lock['enabled'] is value['objectLockEnabled'], 'BUCKET_SETTINGS_READBACK_MISMATCH')
            guard(); require(client.empty_versioned(bucket) is True, 'BUCKET_PREPARATION_NOT_EMPTY'); guard()
            evidence.append(dict(bucket=bucket, versioning=versioning, objectLock=lock))
        except Exception as error:
            error.unknown = True
            raise
    result = dict(schemaVersion='RecoveryBucketPreparation/v1', state='CONFIGURATION_MATCHED',
                  buckets=buckets, priorBucketListing=listing, observations=evidence)
    try: intent('bucket-prepare-readback.json', result)
    except Exception as error:
        error.unknown = True
        raise
    return result


def _policy_actions(document):
    """Ignore only IAM Action set ordering; preserve every other policy value."""
    require(type(document) is dict and type(document.get('Statement')) is list and
            document['Statement'], 'BUCKET_POLICY_INVALID')
    statements = []
    for statement in document['Statement']:
        require(type(statement) is dict, 'BUCKET_POLICY_INVALID')
        value = dict(statement)
        if type(value.get('Action')) is list:
            require(value['Action'] and all(type(action) is str for action in value['Action']),
                    'BUCKET_POLICY_INVALID')
            value['Action'] = sorted(value['Action'])
        statements.append(value)
    return dict(document, Statement=statements)


def protection(client, buckets, expected, *, guard):
    """Match explicit approved permission/configuration Pins against native GETs."""
    _scope(buckets)
    require(type(expected) is dict and set(expected) == {'schemaVersion', 'buckets'} and
            expected['schemaVersion'] in ('RecoveryBucketProtection/v1', 'RecoveryBucketProtection/v2') and
            type(expected['buckets']) is dict and set(expected['buckets']) == set(buckets), 'BUCKET_PROTECTION_SCOPE_INVALID')
    fields = {'versioning', 'objectLockEnabled', 'objectLockSha256', 'aclSha256', 'policySha256'}
    policy_content = expected['schemaVersion'] == 'RecoveryBucketProtection/v2'
    if policy_content: fields.add('policyDocument')
    for value in expected['buckets'].values():
        require(type(value) is dict and set(value) == fields and value['versioning'] in ('Enabled', 'UNVERSIONED') and
            type(value['objectLockEnabled']) is bool and
            all(type(value[k]) is str and re.fullmatch('[0-9a-f]{64}', value[k]) for k in ('aclSha256',)) and
            all(value[k] is None or (type(value[k]) is str and re.fullmatch('[0-9a-f]{64}', value[k]))
                for k in ('objectLockSha256', 'policySha256')) and
            (value['objectLockSha256'] is not None) is value['objectLockEnabled'], 'BUCKET_PROTECTION_INVALID')
        if policy_content:
            document = value['policyDocument']
            require((document is None and value['policySha256'] is None) or
                    (type(document) is str and len(document.encode('utf-8')) <= 1024*1024 and
                     hashlib.sha256(document.encode('utf-8')).hexdigest() == value['policySha256']),
                    'BUCKET_POLICY_APPROVED_DOCUMENT_MISMATCH')
            if document is not None: _policy_actions(parse(document.encode('utf-8')))
    rows = []
    for bucket in buckets:
        value = expected['buckets'][bucket]
        guard(); versioning = client.replica_configuration(bucket, 'versioning')
        guard(); lock = client.replica_configuration(bucket, 'object-lock')
        require(versioning['status'] == value['versioning'] and lock['enabled'] is value['objectLockEnabled'] and
                (not lock['enabled'] or lock['rawSha256'] == value['objectLockSha256']), 'BUCKET_PROTECTION_CONFIGURATION_MISMATCH')
        raw, acl = _get(client, bucket, 'acl', guard)
        _xml(raw, 'AccessControlPolicy')
        require(acl['rawSha256'] == value['aclSha256'], 'BUCKET_ACL_MISMATCH')
        raw, policy = _get(client, bucket, 'policy', guard, absence='NoSuchBucketPolicy' if value['policySha256'] is None else None)
        if raw is not None:
            if policy_content:
                require(value['policyDocument'] is not None and
                        canonical(_policy_actions(parse(raw))) ==
                        canonical(_policy_actions(parse(value['policyDocument'].encode('utf-8')))),
                        'BUCKET_POLICY_MISMATCH')
                policy['comparison'] = 'APPROVED_DOCUMENT_ACTION_ORDER_INSENSITIVE'
                policy['approvedRawSha256'] = value['policySha256']
            else:
                require(type(parse(raw)) is dict and policy['rawSha256'] == value['policySha256'], 'BUCKET_POLICY_MISMATCH')
        else: require(value['policySha256'] is None, 'BUCKET_POLICY_ABSENCE_UNAPPROVED')
        guard(); notification = client.replica_configuration(bucket, 'notification')
        require(notification['externalNotificationEntries'] == 0, 'BUCKET_NOTIFICATION_PRESENT')
        dependencies = []
        for configuration, code in [('lifecycle', 'NoSuchLifecycleConfiguration'), ('replication', 'ReplicationConfigurationNotFoundError'),
                                    ('encryption', 'ServerSideEncryptionConfigurationNotFoundError')]:
            guard(); dependencies.append(client.absent_configuration(bucket, configuration, code))
        guard(); multipart = client.multipart_empty(bucket); guard()
        rows.append(dict(bucket=bucket, versioning=versioning, objectLock=lock, acl=acl, policy=policy,
                         notification=notification, dependencies=dependencies, multipart=multipart))
    return dict(schemaVersion='RecoveryBucketProtectionObservation/v1', state='CONFIGURATION_MATCHED',
                buckets=buckets, observations=rows, applicationWriteProtectionVerified=False)


def compare_indexed_restore(chain, policy, restored, export, readback_module, guard):
    require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
    indexed = object_index_chain(chain, policy, guard=guard)
    _, index_ref, index, receipt, groups = indexed[-1]
    root = Path(restored).absolute()
    source_paths = [Path(ref['path']) for step in indexed for ref in step[2]['contentPins'].values()]
    require(all(root != path and root not in path.parents and path not in root.parents for path in source_paths),
            'OBJECT_READBACK_SOURCE_TARGET_OVERLAP')
    tracked = {}; restored_receipt_pin = pin(root/'export-receipt.json')
    readback, observed = readback_module._load(root, export['inventorySha256'], restored_receipt_pin['sha256'], guard, tracked)
    require(set(receipt['buckets']) == set(readback['buckets']) and groups == observed, 'OBJECT_INDEX_RESTORED_HISTORY_MISMATCH')
    for path, expected in tuple(tracked.items()):
        _, value = readback_module._read(path, expected[1], guard, tracked, keep=False)
        require(value == expected, 'OBJECT_RESTORED_READBACK_CHANGED')
    require(object_index_chain(chain, policy, guard=guard) == indexed, 'OBJECT_INDEX_SOURCE_CHANGED_DURING_READBACK')
    ordered = [row for key in sorted(groups) for row in groups[key]]
    return dict(state='PHYSICAL_VERSION_READBACK_MATCH_PENDING_FULL_RESTORE_PROOF',
        buckets=sorted(receipt['buckets']), versionCount=receipt['versionCount'], deleteMarkerCount=receipt['deleteMarkerCount'],
        totalVersionBytes=receipt['totalVersionBytes'], uniqueContentCount=receipt['uniqueContentCount'],
        exactVersionIdentityVerified=True, versionHistorySha256=hashlib.sha256(canonical(ordered)).hexdigest(),
        sourceInventorySha256=index['inventoryPin']['sha256'], sourceExportReceiptSha256=index['exportReceiptPin']['sha256'],
        sourceObjectContentIndexPin=index_ref, chainObjectContentIndexPins=[step[1] for step in indexed],
        restoredInventorySha256=export['inventorySha256'], restoredExportReceiptSha256=restored_receipt_pin['sha256'],
        physicalCaptureVerified=False, continuousHostExclusionVerified=False, applicationVerified=False, productionEvidence=False)


def create_buckets_unchecked(client, buckets, settings):
    """Lightweight: execute bucket configuration without listing or readback."""
    for index, bucket in enumerate(buckets):
        value = settings[bucket]
        headers = {'x-amz-bucket-object-lock-enabled': 'true'} if value['objectLockEnabled'] else {}
        # HTTP status/write failures still propagate from the actual PUT.
        _put_bucket(client, bucket, None, b'', headers, lambda: None, lambda *args: None, index*2)
        body = b'<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Status>Enabled</Status></VersioningConfiguration>'
        _put_bucket(client, bucket, 'versioning', body, {}, lambda: None, lambda *args: None, index*2+1)
