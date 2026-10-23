"""Owner-injected finite physical copy/start/GET readback; no standalone CLI.

Caller must provide the approved independent recovery data resource and current
owner. This API neither issues approval nor consumes a grant/starts its author.
All partial/uncertain work remains for reconciliation; no automatic rollback.
"""
import hashlib
import os
from pathlib import Path
import re
import time

from formal_snapshot_linux import (require, FormalSnapshotError, current_owner_guard,
    safe_file, _canonical_bytes, _sync_directory, verify_physical_minio_tree, observation_deadline)
from formal_replica_gate import (prepare_checked_minio_replica, create_and_start_checked_replica,
    observe_bound_replica_dependencies, verify_started_replica_dependencies)
from formal_replica_producer import _wait_live
from formal_s3_exec_transport import ContainerReadOnlyS3
from formal_s3_export import export_s3_versions
from formal_physical_restore_readback import _load, _path, SHA, compare_physical_restore_exports


def _record(root, name, value):
    with safe_file(root/name).open('xb') as output:
        os.chmod(output.name, 0o600); output.write(_canonical_bytes(value))
        output.flush(); os.fsync(output.fileno())
    _sync_directory(root)


def produce_physical_restore_readback(*, operation, capture, physical, observed, credential_file,
        access, secret, evidence, recovery_data, source_export, source_inventory_sha256,
        source_export_receipt_sha256, image_id, guard, timeout=7200):
    """Stage stays pending until trusted normal owner/full barriers are proven."""
    started_at=time.monotonic()
    current_owner_guard(guard, code='FORMAL_PHYSICAL_RESTORE_OWNER_REQUIRED')
    require(type(timeout) is int and 0 < timeout <= 7200, 'FORMAL_PHYSICAL_RESTORE_INPUT_INVALID')
    outer=observation_deadline.get()
    deadline=min(started_at+timeout,outer) if outer is not None else started_at+timeout
    token=observation_deadline.set(deadline)
    try:
        def current():
            require(time.monotonic()<deadline, 'FORMAL_PHYSICAL_RESTORE_DEADLINE_EXCEEDED')
            current_owner_guard(guard, code='FORMAL_PHYSICAL_RESTORE_OWNER_REQUIRED')
            require(time.monotonic()<deadline, 'FORMAL_PHYSICAL_RESTORE_DEADLINE_EXCEEDED')
        current()
        require(os.name == 'posix', 'FORMAL_PHYSICAL_RESTORE_NATIVE_LINUX_REQUIRED')
        require(type(operation) is str and re.fullmatch('[A-Za-z0-9-]{1,80}', operation) and
                type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}', image_id) and
                type(timeout) is int and 0 < timeout <= 7200 and
                all(type(value) is str and SHA.fullmatch(value) for value in
                    (source_inventory_sha256, source_export_receipt_sha256)), 'FORMAL_PHYSICAL_RESTORE_INPUT_INVALID')
        capture=_path(capture); source=_path(source_export)
        data=safe_file(recovery_data); root=safe_file(evidence)
        paths=(capture,source,data,root)
        require(all(left != right and left not in right.parents and right not in left.parents
                    for index,left in enumerate(paths) for right in paths[index+1:]),
                'FORMAL_PHYSICAL_RESTORE_PATH_OVERLAP')
        require(capture.is_dir() and source.is_dir(), 'FORMAL_PHYSICAL_RESTORE_SOURCE_REQUIRED')
        original,_ = _load(source,source_inventory_sha256,source_export_receipt_sha256,current,{})
        require(type(observed) is dict and set(original['buckets']) == set(observed['bucketObservations']['buckets']) ==
                set(observed['metadataScope']['buckets']), 'FORMAL_PHYSICAL_RESTORE_BUCKET_SCOPE_CHANGED')
        current();root.mkdir(mode=0o700);_sync_directory(root.parent)
        stage='COPY';started=None
        try:
            current()
            proof=prepare_checked_minio_replica(capture,data,physical,observed,guard=guard)
            stage='START';current()
            started=create_and_start_checked_replica(operation,data,physical,observed,proof,credential_file,
                root/'creator',image_id=image_id,guard=guard)
            stage='DEPENDENCIES';_wait_live(started['containerId'],guard=guard)
            client=ContainerReadOnlyS3(started['containerId'],access,secret,timeout=60,guard=guard)
            dependencies=observe_bound_replica_dependencies(client,data,original['buckets'],guard=guard)
            current();verify_started_replica_dependencies(observed,dependencies)
            current();_record(root,'physical-restore-dependencies.json',dependencies)
            stage='GET_EXPORT'
            restored=export_s3_versions(client,original['buckets'],root/'export',guard=guard,timeout=timeout)
            stage='RAW_CAPTURE_READBACK';current()
            verify_physical_minio_tree(capture,physical,lease_guard=current)
            stage='VERSION_READBACK';current()
            receipt_path=root/'export'/'export-receipt.json'
            readback=compare_physical_restore_exports(source,root/'export',
                source_inventory_sha256=source_inventory_sha256,source_export_receipt_sha256=source_export_receipt_sha256,
                restored_inventory_sha256=restored['inventorySha256'],
                restored_export_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),guard=guard)
            result=dict(state='PHYSICAL_COPY_RESTORED_READBACK_PENDING_OWNER_AND_FULL_BARRIERS',
                operationId=operation,recoveryData=str(data),replica=started,readback=readback,
                physicalTreeDigest=physical['physicalTreeDigest'],
                dependencyReadbackSha256=hashlib.sha256(_canonical_bytes(dependencies)).hexdigest(),
                normalOwnerIntegrationVerified=False,continuousHostExclusionVerified=False,
                applicationVerified=False,productionEvidence=False)
            stage='STAGE_RECORD';current();_record(root,'physical-restore-stage.json',result)
            current();return result
        except Exception as error:
            code=error.code if isinstance(error,FormalSnapshotError) else 'FORMAL_PHYSICAL_RESTORE_FAILED'
            if not (type(code) is str and re.fullmatch('FORMAL_[A-Z_]+',code)):code='FORMAL_PHYSICAL_RESTORE_FAILED'
            failure=dict(state='FAILED_RETAINED',stage=stage,code=code,targetReconciliationRequired=True,
                remoteStopConfirmed=False,productionEvidence=False,replica=started,
                clientCleanupUncertain=bool(getattr(error,'clientCleanupUncertain',False)))
            try:_record(root,'physical-restore-failed.json',failure)
            except Exception:
                error.evidenceWriteUncertain=True
            raise
    finally:
        observation_deadline.reset(token)
