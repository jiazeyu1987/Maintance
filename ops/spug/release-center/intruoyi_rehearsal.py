"""Full-data rehearsal orchestration. Only explicitly registered resources are used."""
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import time
from intruoyi_runtime import require, audit_ledger


def can_reuse_images(source_profile, target_profile, source_daemon, target_daemon):
    return (source_profile['host'] == target_profile['host']
            and source_daemon.get('daemonId')
            and source_daemon['daemonId'] == target_daemon.get('daemonId'))


def active_remote_progress(state, config, runtime):
    from intruoyi_runtime import Runtime, rehearsal_profile
    changed = False
    for job in state.get('jobs', []):
        if job.get('action') != 'prepare-rehearsal' or not job.get('remoteStatusRequired'):
            continue
        source, phase = job.get('sourceEnv'), job.get('remotePhase')
        if source not in ('test','prod','backup') or phase not in ('capture-starting','capture-complete','restore-starting'):
            continue
        if job.get('status') not in ('running','failed','interrupted') or job.get('resolution'):
            continue
        if time.time() - job.get('remoteCheckedAt',0) < 15:
            continue
        # Read-only polling must never mutate the active deployment's target profile.
        poll_config = dict(config, operationTimeout=15, targets=dict(runtime.targets))
        poll_config['targets']['rehearsal'] = rehearsal_profile(config,source)
        observer = Runtime(poll_config)
        try:
            env = 'rehearsal' if phase == 'restore-starting' else source
            progress = observer.call(env,'rehearsal-job-status',jobId=job['id'])
            job['remoteProgress'] = progress
            job.pop('remoteStatusError',None)
        except Exception as error:
            job['remoteStatusError'] = type(error).__name__
            job.pop('remoteProgress',None)
        job['remoteCheckedAt'] = time.time()
        changed = True
    return changed


def transfer(runtime, source, destination, artifact, destination_path, callback, job_id):
    """Encrypted streaming SSH relay; no private artifact is materialized locally."""
    first = runtime.profile(source)
    second = runtime.profile(destination)
    source_path = artifact['path']
    callback('transfer-private-full-data-artifact:' + Path(source_path).name, effects=True)
    if first['host'] == second['host']:
        return runtime.call(destination,'rehearsal-local-copy',sourceProfile=first,sourcePath=source_path,
                            destinationPath=destination_path,sha256=artifact['sha256'],jobId=job_id)
    if artifact['name']=='minio.tar':
        index=runtime.call(source,'rehearsal-transfer-index',sourcePath=source_path,sha256=artifact['sha256'],jobId=job_id)
        request=dict(index,destinationPath=destination_path,jobId=job_id)
        plan=runtime.call(destination,'rehearsal-transfer-plan',**request)
        if plan['missing']:
            sender=runtime.call(source,'rehearsal-transfer-sender',sourcePath=source_path,chunks=plan['missing'],jobId=job_id)
            first_command=shlex.quote(first['python'])+' '+shlex.quote(sender['script'])
            second_command=shlex.quote(second['python'])+' '+shlex.quote(plan['receiver'])
            stream_commands(runtime,first,second,first_command,second_command)
        callback('verify-complete-media-snapshot-after-incremental-transfer',effects=True)
        return runtime.call(destination,'rehearsal-transfer-assemble',**request)
    stream_commands(runtime,first,second,'cat -- '+shlex.quote(source_path),
                    'umask 077; set -C; cat > '+shlex.quote(destination_path))


def stream_commands(runtime, first, second, first_command, second_command):
    with tempfile.TemporaryFile() as errors:
        reader = subprocess.Popen(['ssh', *runtime.ssh_options(), 'root@' + first['host'],
                                   first_command], stdout=subprocess.PIPE, stderr=errors)
        writer = subprocess.Popen(['ssh', *runtime.ssh_options(), 'root@' + second['host'],
                                   second_command],
                                  stdin=reader.stdout, stdout=subprocess.PIPE, stderr=errors)
        reader.stdout.close()
        try:
            writer.communicate(timeout=runtime.config.get('operationTimeout', 14400))
            code = reader.wait(timeout=60)
            require(code == 0 and writer.returncode == 0, 'Private full-data artifact transfer failed; partial target retained for investigation')
        finally:
            for process in (reader, writer):
                if process.poll() is None:
                    process.kill()
                    process.wait()


def prepare(runtime, source, manifest, callback, job_id):
    before = runtime.observe(source)
    audit_ledger(before, manifest)
    src = runtime.profile(source)
    target = runtime.profile('rehearsal')
    require(target.get('sourceEnvironment') == source, 'Rehearsal source environment must be explicitly registered')
    # Known historical images use their explicitly registered original package.
    # All later images must prove their metadata from the immutable image itself.
    historical = dict(kind='image-embedded', images=before['images'], releaseTag=before['releaseTag'])
    repair = runtime.config.get('metadataRepair')
    if repair:
        from intruoyi_metadata import reference
        original_manifest, original_images, original_info = reference(repair)
        if before['images'] == {role: item['id'] for role, item in original_images.items()}:
            require(source in repair.get('directories', {}), 'Registered historical metadata source is required')
            historical = dict(kind='historical-original', manifest=original_manifest, images=original_images,
                              info=original_info, manifestSha256=repair['manifestSha256'],
                              directory=repair['directories'][source])
    runtime.call(source, 'rehearsal-source-check')
    runtime.call('rehearsal', 'rehearsal-target-check', sourceProfile=src)
    callback('create-owned-rehearsal-staging-before-side-effects', effects=True)
    target_stage = runtime.call('rehearsal', 'rehearsal-create-stage', releaseTag=manifest['releaseTag'])
    callback('stop-source-registered-writers-and-capture-real-full-data-before-side-effects', effects=True)
    source_daemon = runtime.call(source, 'rehearsal-daemon-identity')
    target_daemon = runtime.call('rehearsal', 'rehearsal-daemon-identity')
    reuse_images = can_reuse_images(src, target, source_daemon, target_daemon)
    capture_request = dict(releaseTag=manifest['releaseTag'], originFingerprint=before['fingerprint'], historicalMetadata=historical, reuseImages=reuse_images, jobId=job_id)
    if reuse_images:
        source_images = runtime.call(source, 'rehearsal-runtime-images')['images']
        target_images = runtime.call('rehearsal', 'rehearsal-check-images', images=source_images)['images']
        require(source_images == target_images, 'Same Docker daemon exposes different required image IDs; image reuse refused')
        capture_request['imageIds'] = source_images
    callback('remote-full-data-capture-starting', effects=True)
    captured = runtime.call(source, 'rehearsal-capture', **capture_request)
    callback('remote-full-data-capture-complete', effects=True)
    capture_status = runtime.call(source, 'rehearsal-job-status', jobId=job_id)
    require(capture_status.get('phase') == 'capture-complete', 'Remote full-data capture is not conclusively complete')
    require(captured['originFingerprint'] == before['fingerprint'], 'Source identity changed before snapshot')
    for artifact in captured['artifacts']:
        transfer(runtime, source, 'rehearsal', artifact, target_stage['directory'] + '/' + artifact['name'], callback, job_id)
    callback('restore-isolated-real-data-and-start-baseline-before-side-effects', effects=True)
    callback('remote-isolated-restore-starting', effects=True)
    runtime.call('rehearsal', 'rehearsal-restore', capture=captured, sourceProfile=src,
                 releaseTag=manifest['releaseTag'], jobId=job_id)
    remote_status = runtime.call('rehearsal', 'rehearsal-job-status', jobId=job_id)
    require(remote_status.get('phase') == 'completed', 'Remote isolated restore is not conclusively complete')
    obs = runtime.observe('rehearsal')
    for key in ('images', 'schemaSha256', 'ledgerSha256'):
        require(obs[key] == captured['origin'][key], 'Isolated copy does not prove source origin: ' + key)
    audit_ledger(obs, manifest)
    obs.update(originFingerprint=before['fingerprint'], verifiedOrigin=True,
               originEvidence={key: obs[key] for key in ('images', 'schemaSha256', 'ledgerSha256')},
               historicalMetadata=captured['historicalMetadata'],
               remotePreparationProgress=remote_status)
    return obs


def reset(runtime, callback):
    runtime.call('rehearsal', 'rehearsal-reset-check')
    callback('remove-only-labelled-rehearsal-resources-before-side-effects', effects=True)
    return runtime.call('rehearsal', 'rehearsal-reset')


def resume_tail(runtime, source, manifest, original_job_id, retry_job_id, package_sha256,
                manifest_sha256, expected_origin_fingerprint, callback):
    require(source == 'prod', 'Only the production baseline rehearsal tail may resume')
    require(runtime.profile('rehearsal').get('sourceEnvironment') == source, 'Registered rehearsal source differs')
    callback('verify-existing-rehearsal-capture-and-source')
    proof = runtime.call(source, 'rehearsal-tail-source-proof', releaseTag=manifest['releaseTag'],
                         originalJobId=original_job_id, expectedOriginFingerprint=expected_origin_fingerprint)
    require(proof['capture']['originFingerprint'] == expected_origin_fingerprint, 'Original rehearsal source fingerprint differs')
    audit_ledger(proof['capture']['origin'], manifest)
    callback('resume-existing-rehearsal-frontend-tail', effects=True)
    result = runtime.call('rehearsal', 'rehearsal-resume-tail', releaseTag=manifest['releaseTag'],
                          originalJobId=original_job_id, retryJobId=retry_job_id,
                          packageSha256=package_sha256, manifestSha256=manifest_sha256,
                          sourceProof=proof, sourceProfile=runtime.profile(source))
    require(runtime.observe(source)['fingerprint'] == expected_origin_fingerprint, 'Source changed during isolated tail recovery')
    audit_ledger(result, manifest)
    return result
