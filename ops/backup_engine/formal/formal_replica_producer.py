"""Actual finite replica/export stage for the formal producer.

This stage cannot produce formal COMPLETE, deployment acceptance or maintained
host/object barrier evidence. The actual controller still requires that chain.
"""
import os,time,subprocess,argparse,hashlib,json,re
from pathlib import Path
from formal_snapshot_linux import safe_file,verify_physical_minio_tree,_canonical_bytes,_sync_directory,require,FormalSnapshotError,_existing_file,current_owner_guard
from formal_replica_gate import (prepare_checked_minio_replica,create_and_start_checked_replica,
    observe_bound_replica_dependencies,verify_started_replica_dependencies,_guarded_run)
from formal_s3_exec_transport import ContainerReadOnlyS3
from formal_s3_export import export_s3_versions,_strict_json

def _wait_live(identity,*,guard):
    deadline=time.monotonic()+30
    while True:
        try:
            result=_guarded_run(['docker','exec',identity,'curl','--disable','--silent','--fail',
                '--noproxy','*','--max-time','5','http://127.0.0.1:9000/minio/health/live'],
                guard=guard,timeout=6,code='FORMAL_REPLICA_HEALTH_QUERY_FAILED')
        except (OSError,subprocess.TimeoutExpired):raise FormalSnapshotError('FORMAL_REPLICA_HEALTH_QUERY_FAILED') from None
        if result.returncode==0:return
        require(time.monotonic()<deadline,'FORMAL_REPLICA_NOT_LIVE')
        time.sleep(0.25)

def produce_isolated_replica_export(operation,capture,physical,observed,credential_file,access,secret,evidence,*,image_id,guard,timeout=7200):
    def current():current_owner_guard(guard,code='FORMAL_REPLICA_OWNER_GUARD_REQUIRED')
    current();target=safe_file(evidence);target.mkdir(mode=0o700);_sync_directory(target.parent)
    replica=target/'replica-data'
    proof=prepare_checked_minio_replica(capture,replica,physical,observed,guard=guard)
    started=create_and_start_checked_replica(operation,replica,physical,observed,proof,
        credential_file,target/'creator',image_id=image_id,guard=guard)
    _wait_live(started['containerId'],guard=guard)
    # No redirect, host port or bridge transport; all object bytes stream over
    # the selected replica's loopback curl process and Docker stdout.
    client=ContainerReadOnlyS3(started['containerId'],access,secret,timeout=60,guard=guard)
    dependencies=observe_bound_replica_dependencies(client,replica,observed['bucketObservations']['buckets'],guard=guard)
    current();verify_started_replica_dependencies(observed,dependencies)
    readback={'state':'REPLICA_DEPENDENCIES_READ_BACK_PENDING_RESTORE_AND_FORMAL_BARRIERS',
        'operationId':operation,'containerId':started['containerId'],'imageId':started['imageId'],
        'physicalTreeDigest':physical['physicalTreeDigest'],'sourceObservationSha256':proof['observationSha256'],
        'observation':dependencies,'productionEvidence':False}
    readback_path=safe_file(target/'replica-dependency-readback.json');readback_bytes=_canonical_bytes(readback)
    current()
    with readback_path.open('xb') as output:
        os.chmod(output.name,0o600);output.write(readback_bytes);output.flush();os.fsync(output.fileno())
    _sync_directory(target)
    exported=export_s3_versions(client,observed['metadataScope']['buckets'],target/'export',timeout=timeout,guard=guard)
    verify_physical_minio_tree(capture,physical,lease_guard=current)
    require(_existing_file(readback_path).read_bytes()==readback_bytes,'FORMAL_REPLICA_DEPENDENCY_READBACK_CHANGED')
    result={'state':'REPLICA_EXPORTED_PENDING_RESTORE_AND_FORMAL_BARRIERS','operationId':operation,
        'replica':started,'export':exported,'physicalTreeDigest':physical['physicalTreeDigest'],
        'observationSha256':proof['observationSha256'],
        'dependencyReadbackSha256':hashlib.sha256(readback_bytes).hexdigest(),'productionEvidence':False}
    current()
    with safe_file(target/'replica-export-stage.json').open('xb') as output:
        os.chmod(output.name,0o600);output.write(_canonical_bytes(result));output.flush();os.fsync(output.fileno())
    _sync_directory(target)
    current();return result

def _require_linux():
    require(os.name=='posix','FORMAL_REPLICA_LINUX_REQUIRED')

def main(argv=None):
    parser=argparse.ArgumentParser(description='Isolated replica/export stage; never a formal completion producer.')
    for name in ('operation-id','capture-root','physical-receipt','expected-physical-sha256',
                 'observations','expected-observations-sha256','credential-file','evidence-root','image-id'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    try:
        _require_linux()
        # Digests/operation IDs cannot substitute for a currently held owner.
        # Only the owner-injected API is usable until a trusted author binds it.
        raise FormalSnapshotError('FORMAL_REPLICA_CURRENT_OWNER_REQUIRED')
    except FormalSnapshotError as error:
        print(json.dumps({'state':'FAILED_RETAINED','code':error.code,'productionEvidence':False}));return 1
    except (OSError,UnicodeError,ValueError,KeyError,TypeError):
        print(json.dumps({'state':'FAILED_RETAINED','code':'FORMAL_REPLICA_ENTRY_FAILED','productionEvidence':False}));return 1

if __name__=='__main__':raise SystemExit(main())
