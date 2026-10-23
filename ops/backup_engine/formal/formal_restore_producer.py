"""Restore exported versions to one explicitly bound isolated Docker target.

Does not create buckets, select endpoints, change services, or claim application
acceptance. A request digest identifies the approved task-owned target.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from formal_capture_producer import read_private
from formal_filesystem_watchdog import require_native_runtime, WatchdogError
from formal_snapshot_linux import FormalSnapshotError, require, safe_file, _canonical_bytes, _sync_directory
from formal_replica_gate import _private_docker_json
from formal_s3_export import _strict_json, IsolatedRestoreS3, restore_s3_versions, validate_bucket_mapping


def bound_target(target, operation, *, guard):
    row = _private_docker_json(['inspect', target['containerId']], guard=guard)
    require(row.get('Id') == target['containerId'] and row.get('Image') == target['imageId'] and
            row.get('State', {}).get('Running') is True and
            row.get('HostConfig', {}).get('Privileged') is False and
            row.get('Config', {}).get('Labels', {}).get('intruoyi.formal-restore-operation') == operation,
            'FORMAL_RESTORE_TARGET_CHANGED')
    networks = row.get('NetworkSettings', {}).get('Networks', {})
    require(type(networks) is dict and len(networks) == 1,
            'FORMAL_RESTORE_NETWORK_INVALID')
    addresses = [network.get('IPAddress') for network in networks.values() if type(network) is dict]
    require(len(addresses) == 1 and type(addresses[0]) is str and addresses[0] and
            target['endpoint'] == 'http://' + addresses[0] + ':9000',
            'FORMAL_RESTORE_ENDPOINT_CHANGED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        require_native_runtime()
        require(re.fullmatch('[0-9a-f]{64}', args.expected_request_sha256),
                'FORMAL_RESTORE_REQUEST_APPROVAL_REQUIRED')
        raw = read_private(args.request, 16384)
        require(hashlib.sha256(raw).hexdigest() == args.expected_request_sha256,
                'FORMAL_RESTORE_REQUEST_CHANGED')
        request = _strict_json(raw)
        require(type(request) is dict and set(request) == {'schemaVersion', 'operationId',
                'sourceExport', 'evidenceRoot', 'target', 'bucketMapping',
                'sourceInventorySha256', 'sourceExportReceiptSha256'} and
                request['schemaVersion'] == 'release-formal-object-restore-request/v2' and
                type(request['operationId']) is str and
                re.fullmatch('[A-Za-z0-9_-]{1,128}', request['operationId']) and
                all(type(request[k]) is str and request[k] for k in ('sourceExport', 'evidenceRoot')),
                'FORMAL_RESTORE_REQUEST_INVALID')
        require(all(type(request[k]) is str and re.fullmatch('[0-9a-f]{64}', request[k])
                    for k in ('sourceInventorySha256', 'sourceExportReceiptSha256')),
                'FORMAL_RESTORE_SOURCE_BINDING_INVALID')
        export_raw = read_private(Path(request['sourceExport']) / 'export-receipt.json', 16384)
        require(hashlib.sha256(export_raw).hexdigest() == request['sourceExportReceiptSha256'],
                'FORMAL_RESTORE_SOURCE_CHANGED')
        export = _strict_json(export_raw)
        require(type(export) is dict and export.get('inventorySha256') == request['sourceInventorySha256'],
                'FORMAL_RESTORE_SOURCE_CHANGED')
        require(hashlib.sha256(read_private(Path(request['sourceExport']) / 'versions.jsonl',
                                           256*1024*1024)).hexdigest() == request['sourceInventorySha256'],
                'FORMAL_RESTORE_SOURCE_CHANGED')
        mapping = validate_bucket_mapping(request['bucketMapping'], export.get('buckets'))
        mapping_sha = hashlib.sha256(_canonical_bytes(mapping)).hexdigest()
        target = request['target']
        require(type(target) is dict and set(target) == {'containerId', 'imageId', 'endpoint', 'credentialFile'} and
                all(type(value) is str for value in target.values()) and
                re.fullmatch('[0-9a-f]{64}', target['containerId']) and
                re.fullmatch('sha256:[0-9a-f]{64}', target['imageId']),
                'FORMAL_RESTORE_TARGET_INVALID')
        def source_guard():
            require(read_private(args.request, 16384) == raw, 'FORMAL_RESTORE_REQUEST_CHANGED')
            require(read_private(Path(request['sourceExport']) / 'export-receipt.json', 16384) == export_raw and
                    hashlib.sha256(read_private(Path(request['sourceExport']) / 'versions.jsonl',
                        256*1024*1024)).hexdigest() == request['sourceInventorySha256'],
                    'FORMAL_RESTORE_SOURCE_CHANGED')
        bound_target(target, request['operationId'], guard=source_guard)
        credentials = _strict_json(read_private(target['credentialFile'], 16384))
        require(type(credentials) is dict and set(credentials) == {'access', 'secret'} and
                all(type(value) is str and value and not any(c in value for c in '\r\n\0')
                    for value in credentials.values()), 'FORMAL_RESTORE_CREDENTIAL_INVALID')
        require(read_private(args.request, 16384) == raw, 'FORMAL_RESTORE_REQUEST_CHANGED')
        bound_target(target, request['operationId'], guard=source_guard)
        client = IsolatedRestoreS3(target['endpoint'], credentials['access'], credentials['secret'],
                                   approved_endpoint=target['endpoint'])
        result = restore_s3_versions(client, request['sourceExport'], request['evidenceRoot'],
                    bucket_mapping=mapping, source_inventory_sha256=request['sourceInventorySha256'],
                    source_export_receipt_sha256=request['sourceExportReceiptSha256'])
        bound_target(target, request['operationId'], guard=source_guard)
        require(result.get('state') == 'VERSIONS_RESTORED_PENDING_APPLICATION_PROOF',
                'FORMAL_RESTORE_RESULT_INVALID')
        require(result.get('bucketMapping') == mapping and result.get('bucketMappingSha256') == mapping_sha and
                all(result.get(k) == request[k] for k in ('sourceInventorySha256', 'sourceExportReceiptSha256')),
                'FORMAL_RESTORE_RESULT_BINDING_INVALID')
        require(read_private(args.request, 16384) == raw, 'FORMAL_RESTORE_REQUEST_CHANGED')
        evidence = Path(request['evidenceRoot'])
        receipt_raw = read_private(evidence / 'restore-receipt.json', 16384)
        require(_strict_json(receipt_raw) == result, 'FORMAL_RESTORE_RECEIPT_CHANGED')
        binding = {'schemaVersion': 'release-formal-object-restore-entry/v2',
                   'operationId': request['operationId'], 'requestSha256': args.expected_request_sha256,
                   'containerId': target['containerId'], 'imageId': target['imageId'],
                   'endpoint': target['endpoint'],
                   'bucketMapping': mapping, 'bucketMappingSha256': mapping_sha,
                   'sourceInventorySha256': request['sourceInventorySha256'],
                   'sourceExportReceiptSha256': request['sourceExportReceiptSha256'],
                   'restoreReceiptSha256': hashlib.sha256(receipt_raw).hexdigest(),
                   'productionEvidence': False}
        with safe_file(evidence / 'entry-binding.json').open('xb') as output:
            os.chmod(output.name, 0o600)
            output.write(_canonical_bytes(binding)); output.flush(); os.fsync(output.fileno())
        if os.name == 'posix':
            _sync_directory(evidence)
        print(json.dumps(result)); return 0
    except (FormalSnapshotError, WatchdogError) as error:
        code = error.code
        if not (type(code) is str and re.fullmatch('(?:FORMAL|WATCHDOG)_[A-Z_]+', code)):
            code = 'FORMAL_RESTORE_ENTRY_FAILED'
        print(json.dumps({'state': 'FAILED_RETAINED', 'code': code, 'productionEvidence': False})); return 1
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        print(json.dumps({'state': 'FAILED_RETAINED', 'code': 'FORMAL_RESTORE_ENTRY_FAILED',
                          'productionEvidence': False})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
