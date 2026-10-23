"""Approved claim-bound running or stopped original launch observation only.

The stopped CLI is pre-recovery. It is not the post-v7 OPEN live guard, an OPEN
author, a cold-start runner, or host/business exclusion proof.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import time
import subprocess
import tarfile
import tempfile

import formal_boot_state as boot
import formal_original_launch as launch
import formal_snapshot_linux as snapshot
import formal_split_capture as split
from formal_filesystem_watchdog import require_native_runtime
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError,require


def _image_export_process(argv,**kwargs):
    return subprocess.Popen(argv,**kwargs)


def export_bounded_original_image_bytes(image_ids,destination,*,guard,deadline):
    """Original image-save bytes are capped at the pipe-to-disk boundary."""
    from formal_capture_budget import active_budget,drain_owned_process
    output_budget=active_budget.get()
    require(output_budget is not None and type(image_ids) is list and image_ids and
        all(type(value) is str and re.fullmatch('sha256:[0-9a-f]{64}',value) for value in image_ids),
        'FORMAL_ORIGINAL_IMAGE_BOUND_REQUIRED')
    target=snapshot.safe_file(destination);errors=target.with_name(target.name+'.stderr')
    with output_budget.open(target,'images') as output,output_budget.open(errors,'image-stderr') as stderr:
        guard()
        child=_image_export_process(['/usr/bin/docker','--host','unix:///var/run/docker.sock',
            'image','save',*sorted(set(image_ids))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        row=drain_owned_process(child,b'',output,guard=guard,
            deadline=min(deadline,output_budget.deadline),stderr_writer=stderr,
            stderr_limit=output_budget.policy['componentBytes']['image-stderr'])
        require(row['stderrBytes']==0,'FORMAL_ORIGINAL_IMAGE_EXPORT_FAILED')
        output.flush();stderr.flush();guard()
    # Only successful empty diagnostics are retired, before the archive's
    # existing exact-child epoch is pinned. Failed/partial diagnostics remain.
    output_budget.unlink_complete(errors)
    return row


def capture_original_application_images(claim,destination,*,guard,timeout=7200):
    """Actual old application content; never full-source or backup authority.

    The existing owner supplies the continuously held maintenance guard. Save
    the original immutable IDs, never resolve tags or export the new package.
    This phase retains failed/partial bytes and never automatically retries.
    """
    require(callable(guard) and type(timeout) is int and 0<timeout<=7200,
            'FORMAL_ORIGINAL_IMAGE_INPUT_INVALID')
    deadline=time.monotonic()+timeout
    def budget():
        snapshot.observation_timeout(timeout)
        require(time.monotonic()<deadline,'FORMAL_ORIGINAL_IMAGE_TIMEOUT')
        guard();claim.assert_owned()
    budget()
    originals,_,scope_sha=split._scope(claim,stopped=True)
    expected={role:originals[role]['image'] for role in ('backend','frontend')}
    require(all(type(value) is str and re.fullmatch('sha256:[0-9a-f]{64}',value)
                for value in expected.values()),'FORMAL_ORIGINAL_IMAGE_INPUT_INVALID')
    expected_raw=snapshot._canonical_bytes(expected)
    shared_raw=claim._read(claim.root/'shared-container-original.json')
    def current():
        budget();bound,_,digest=split._scope(claim,stopped=True)
        require(digest==scope_sha and snapshot._canonical_bytes(expected)==expected_raw and
                {role:bound[role]['image'] for role in expected}==expected,
                'FORMAL_ORIGINAL_IMAGE_SOURCE_CHANGED')
        require(claim._read(claim.root/'shared-container-original.json')==shared_raw,
                'FORMAL_ORIGINAL_IMAGE_SOURCE_CHANGED')
        budget()
    current();target=snapshot.safe_file(destination)
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    child=None;primary=None
    try:
        if output_budget is not None:
            export_bounded_original_image_bytes(list(expected.values()),target,guard=current,deadline=deadline)
        else:
            with target.open('xb') as output,tempfile.TemporaryFile() as errors:
                os.chmod(target,0o600);current()
                child=_image_export_process(['/usr/bin/docker','--host','unix:///var/run/docker.sock',
                    'image','save',*sorted(set(expected.values()))],stdout=output,stderr=errors)
                while child.poll() is None:
                    current();time.sleep(min(0.05,max(0.001,deadline-time.monotonic())))
                current();errors.seek(0,os.SEEK_END)
                require(child.returncode==0 and errors.tell()==0,'FORMAL_ORIGINAL_IMAGE_EXPORT_FAILED')
                output.flush();os.fsync(output.fileno())
        current();initial=snapshot._hash_object(target,guard=budget)
        require(initial[1]>0,'FORMAL_ORIGINAL_IMAGE_EXPORT_EMPTY')
        with tarfile.open(target,'r:') as archive:
            members={}
            for item in archive:
                budget();name=item.name;path=PurePosixPath(name)
                require(name and not path.is_absolute() and '\\' not in name and '\0' not in name and
                        all(part not in ('','.','..') for part in name.rstrip('/').split('/')) and
                        str(path)==name.rstrip('/') and name not in members and
                        (item.isfile() or item.isdir()),'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                members[name]=item
                require(len(members)<=500000,'FORMAL_ORIGINAL_IMAGE_ARCHIVE_TOO_LARGE')
            def small(name,limit):
                item=members.get(name)
                require(item is not None and item.isfile() and 0<item.size<=limit,
                        'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                stream=archive.extractfile(item)
                require(stream is not None,'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                with stream:raw=stream.read(limit+1)
                require(len(raw)==item.size,'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                budget();return _strict_json(raw)
            manifest=small('manifest.json',1048576)
            require(type(manifest) is list and len(manifest)==len(set(expected.values())),
                    'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
            found=set()
            for entry in manifest:
                budget()
                require(type(entry) is dict and set(entry)=={'Config','RepoTags','Layers'} and
                        type(entry['Config']) is str and type(entry['Layers']) is list and
                        all(type(name) is str for name in entry['Layers']) and
                        len(entry['Layers'])==len(set(entry['Layers'])),
                        'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                config_name=entry['Config'];config=small(config_name,1048576)
                with archive.extractfile(members[config_name]) as stream:config_raw=stream.read(1048577)
                image='sha256:'+hashlib.sha256(config_raw).hexdigest()
                require(image in expected.values() and image not in found,
                        'FORMAL_ORIGINAL_IMAGE_CONTENT_CHANGED')
                require(type(config) is dict and config.get('os')=='linux' and
                        type(config.get('architecture')) is str and bool(config['architecture']) and
                        type(config.get('rootfs')) is dict and config['rootfs'].get('type')=='layers' and
                        type(config['rootfs'].get('diff_ids')) is list and
                        len(config['rootfs']['diff_ids'])==len(entry['Layers']),
                        'FORMAL_ORIGINAL_IMAGE_CONTENT_CHANGED')
                for name,diff_id in zip(entry['Layers'],config['rootfs']['diff_ids']):
                    require(type(diff_id) is str and re.fullmatch('sha256:[0-9a-f]{64}',diff_id),
                            'FORMAL_ORIGINAL_IMAGE_CONTENT_CHANGED')
                    item=members.get(name)
                    require(item is not None and item.isfile(),'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                    digest=hashlib.sha256();size=0
                    stream=archive.extractfile(item)
                    require(stream is not None,'FORMAL_ORIGINAL_IMAGE_ARCHIVE_INVALID')
                    with stream:
                        while True:
                            budget();chunk=stream.read(1048576)
                            if not chunk:break
                            size+=len(chunk);digest.update(chunk)
                    require(size==item.size and 'sha256:'+digest.hexdigest()==diff_id,
                            'FORMAL_ORIGINAL_IMAGE_CONTENT_CHANGED')
                found.add(image)
            require(found==set(expected.values()),'FORMAL_ORIGINAL_IMAGE_CONTENT_CHANGED')
        current();require(snapshot._hash_object(target,guard=budget)==initial,
                          'FORMAL_ORIGINAL_IMAGE_ARCHIVE_CHANGED');current()
        return dict(sha256=initial[0][7:],bytes=initial[1],images=expected,
                    sharedScopeSha256=scope_sha,productionEvidence=False,hostWritersVerified=False)
    except (OSError,ValueError,tarfile.TarError,subprocess.SubprocessError) as error:
        primary=FormalSnapshotError('FORMAL_ORIGINAL_IMAGE_EXPORT_UNCERTAIN')
        raise primary from None
    except Exception as error:
        primary=error;raise
    finally:
        if child is not None and child.poll() is None:
            uncertain=False
            try:
                child.terminate();child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:child.kill();child.wait(timeout=3)
                except (OSError,subprocess.SubprocessError):uncertain=True
            except (OSError,subprocess.SubprocessError):uncertain=True
            if uncertain:
                if primary is not None:primary.imageExportCleanupUncertain=True
                else:raise FormalSnapshotError('FORMAL_ORIGINAL_IMAGE_CLEANUP_UNCERTAIN') from None


def inspect_local_scope(container_id, *, deadline):
    require(type(container_id) is str and re.fullmatch('[0-9a-f]{64}',container_id),'FORMAL_LAUNCH_SCOPE_INVALID')
    try:
        raw=launch._bounded_command(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',
            '--type','container','--format',snapshot.CONTAINER_INSPECT_TEMPLATE,container_id],deadline=deadline,limit=65536)
        value=_strict_json(raw);snapshot._container_stable(value)
        require(value['id']==container_id,'FORMAL_LAUNCH_SCOPE_INVALID');return value
    except launch.LaunchObservationError:
        raise FormalSnapshotError('FORMAL_LAUNCH_SOURCE_UNAVAILABLE') from None


def restore_original_backend_once(claim,open_checks,source_checks,*,mysql,expected_receipt_sha256,
                                  expected_rules_sha256,expected_external_scope_sha256,
                                  guard,thaw_guard,timeout=60,reconcile_only=False):
    """Internal once-action integration; deliberately not a production CLI.

    Actual closed host entries, recovery ingress and registered stopped callers
    are observed here. The owner still must maintain complete trusted exclusion,
    durable drain and thaw. These finite observations prove none of those full
    properties. A retained intent is
    never dispatched again; explicit reconciliation only reads the current
    original source and uses the existing no-action journal reconciler.
    """
    from formal_original_open_writer import CompletedOriginalOpenChecks,_one
    import formal_service_health as health
    import formal_host_admission as host
    import formal_ingress_control as ingress
    import formal_external_callers as callers
    require_native_runtime()
    require(os.getuid()==os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim and
        type(open_checks) is CompletedOriginalOpenChecks and open_checks.claim is claim and
        type(source_checks) is launch.OriginalLaunchRecoveryChecks and callable(guard) and callable(thaw_guard) and
        type(timeout) is int and 1<=timeout<=300 and type(reconcile_only) is bool and
        all(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) for value in
            (expected_receipt_sha256,expected_rules_sha256,expected_external_scope_sha256)),
        'FORMAL_COLD_START_INPUT_INVALID')
    expected=open_checks.expected;original=source_checks.original
    require(original['inspect']['containerId']==expected['containerId'] and original['bootId']==expected['hostBootId'] and
        original['inspect']['digests']['launchSha256']==expected['launchSha256'] and
        source_checks.retained.original['sha256']==expected['artifactSha256'] and
        source_checks.instance==_one(claim,'boot-backend-bound')['binding']['instanceId'] and
        source_checks.phase in (('STOPPED','STARTED') if reconcile_only else ('STOPPED',)),
        'FORMAL_COLD_START_SOURCE_BINDING_CHANGED')
    token=snapshot.observation_deadline.set(time.monotonic()+snapshot.observation_timeout(timeout))
    try:
        stage=open_checks.assert_valid()['startStage']
        require(stage==('INTENT_RETAINED' if reconcile_only else 'NOT_ATTEMPTED'),
            'FORMAL_COLD_START_REPLAY_REFUSED')
        dependency_pins={claim.root/name:(limit,boot._read_secure(claim.root/name,0o600,limit,no_atime=True))
            for name,limit in (('shared-dependencies-health.json',32768),('database-original.json',16384))}
        require(hashlib.sha256(dependency_pins[claim.root/'shared-dependencies-health.json'][1][0]).hexdigest()==
            expected_receipt_sha256,'FORMAL_COLD_START_DEPENDENCY_INPUT_CHANGED')
        registered_pins={claim.root/name:boot._read_secure(claim.root/name,0o600,16384,no_atime=True)
            for name in ('external-callers-original.json','ingress-plan.json','ingress-installed.json',
                'ingress-recovery-plan.json','ingress-recovery-installed.json')}
        require(boot._sha(registered_pins[claim.root/'external-callers-original.json'][0])==expected_external_scope_sha256 and
            _one(claim,'external-caller-scope')=={'scopeSha256':expected_external_scope_sha256} and
            boot._sha(registered_pins[claim.root/'ingress-recovery-installed.json'][0])==expected_rules_sha256,
            'FORMAL_COLD_START_REGISTERED_SOURCE_CHANGED')
        host_checks=host.ClosedHostAdmissionChecks(claim)
        transport=callers.SshDockerTransport()
        def dependency_inputs(*,content=True):
            for path,(limit,pair) in dependency_pins.items():
                if content:
                    require(boot._read_secure(path,0o600,limit,no_atime=True)==pair,
                        'FORMAL_COLD_START_DEPENDENCY_INPUT_CHANGED')
                require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],
                    'FORMAL_COLD_START_DEPENDENCY_INPUT_CHANGED')
        def registered_inputs(*,content=True):
            for path,pair in registered_pins.items():
                if content:
                    require(boot._read_secure(path,0o600,16384,no_atime=True)==pair,
                        'FORMAL_COLD_START_REGISTERED_SOURCE_CHANGED')
                require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],
                    'FORMAL_COLD_START_REGISTERED_SOURCE_CHANGED')
        def registered_guard():
            guard();claim.assert_owned();snapshot.observation_timeout(1)
            registered_inputs()
            deadline=time.monotonic()+snapshot.observation_timeout(60)
            host_checks.prepare(guard=lambda:registered_inputs(content=False),deadline=deadline)
            held=ingress.assert_ingress(claim)
            require(type(held) is dict and held.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
                held.get('rulesSha256')==expected_rules_sha256,'FORMAL_COLD_START_INGRESS_CHANGED')
            external=callers.guard_external_callers(claim,transport)
            require(type(external) is dict and external.get('scopeSha256')==expected_external_scope_sha256 and
                external.get('state')=='KNOWN_EXTERNAL_CALLERS_STOPPED_PENDING_FULL_EXCLUSION',
                'FORMAL_COLD_START_CALLERS_CHANGED')
            registered_inputs()
            host_checks.assert_native(deadline=deadline)
            registered_inputs(content=False)
        def live_guard():
            registered_guard()
            dependency_inputs()
            identity,flags,_=snapshot._claimed_database_original(claim)
            # The existing observer checks actual dependencies, flags and the
            # held frontend at every once-action/reconciliation boundary. Its
            # guard is the owner guard, never this function (no recursion).
            health.observe_shared_dependency_health(claim,mysql,
                expected_receipt_sha256=expected_receipt_sha256,guard=guard,thaw_guard=thaw_guard,
                timeout=snapshot.observation_timeout(30),backend_transition=open_checks)
            dependency_inputs()
            checked=open_checks.assert_valid()
            # Re-observe the independent registered sources after all health
            # owner callbacks/private reads, before the final backend sources.
            registered_guard()
            deadline=time.monotonic()+snapshot.observation_timeout(60)
            current=inspect_local_scope(expected['containerId'],deadline=deadline)
            require(snapshot._container_stable(current)==snapshot._container_stable(open_checks.original),
                'FORMAL_COLD_START_RUNTIME_CHANGED')
            if current['state']['Running'] is False:
                require(checked['startStage']!='RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION' and
                    current['state']==open_checks.start_intent['before'],'FORMAL_COLD_START_RUNTIME_CHANGED')
                source_checks.stopped(current['state'],deadline=deadline)
            else:
                require(checked['startStage'] in ('INTENT_RETAINED','RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION'),
                    'FORMAL_COLD_START_INTENT_REQUIRED')
                split._completed_shared_action(open_checks.original,current,open_checks.start_intent,'start')
                observed=launch.observe_original_launch('backend',expected['containerId'],original['inspect']['imageId'],
                    expected['hostBootId'],deadline=deadline)
                info=os.stat(source_checks.binding['path'],follow_symlinks=False)
                binding=dict(source_checks.binding,identity=dict(device=info.st_dev,inode=info.st_ino),
                    pid=observed['inspect']['pid'])
                require(observed['inspect']['startedAt']==current['state']['StartedAt'],'FORMAL_COLD_START_RUNTIME_CHANGED')
                source_checks.started(binding,deadline=deadline)
            # All owner/private callbacks finish before the final native
            # flags read. Only metadata checks follow it.
            require(snapshot._database_flags(mysql,identity)==flags,'FORMAL_COLD_START_DATABASE_FLAGS_CHANGED')
            dependency_inputs(content=False)
            registered_inputs(content=False)
            host_checks._signatures()
            open_checks.assert_signatures()
            source_checks.retained.assert_unchanged(deadline=deadline)
            if current['state']['Running']:
                import formal_jvm_identity as jvm
                require(jvm._socket_signature(binding)==source_checks.start_socket,
                    'FORMAL_COLD_START_SOURCE_BINDING_CHANGED')
            snapshot.observation_timeout(1)
        live_guard()
        if reconcile_only:
            runtime=split.reconcile_shared_container(claim,'backend','start',guard=live_guard,thaw_guard=thaw_guard)
        else:
            runtime=split.restore_shared_container(claim,'backend',guard=live_guard,thaw_guard=thaw_guard)
        live_guard()
        return dict(state='ORIGINAL_BACKEND_RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION',
            containerId=expected['containerId'],runtime=runtime,startDispatched=not reconcile_only,
            newProcessIdentityMatched=True,durableColdStartIntentWired=True,reconciliationOnly=reconcile_only,
            dependencyHealthChecked=True,
            registeredHostIngressCallerSourcesChecked=True,
            coldStartConfirmed=False,fullPreOpenGuard=False,fullDrain=False,fullHostFence=False,
            fullColdProducerWired=False,productionEvidence=False,releaseReady=False,claimReleased=False)
    except launch.LaunchObservationError:
        raise FormalSnapshotError('FORMAL_COLD_START_SOURCE_UNAVAILABLE_RETAINED') from None
    except OSError:
        raise FormalSnapshotError('FORMAL_COLD_START_IO_FAILED_RETAINED') from None
    finally:snapshot.observation_deadline.reset(token)


def _validate(request):
    common={'schemaVersion','action','claimRoot','claimBinding','totalSeconds','hostBootId','role','expectedLaunchSha256'}
    require(type(request) is dict and request.get('schemaVersion') in
        ('release-formal-capture-request/v10','release-formal-capture-request/v11'), 'FORMAL_LAUNCH_REQUEST_INVALID')
    with_jvm=request['schemaVersion']=='release-formal-capture-request/v11'
    require(set(request)==common | ({'jvmBinding'} if with_jvm else set()) and
        request['action'] in (('observe-running-original-jvm',) if with_jvm else
            ('observe-running-original-launch','observe-stopped-original-launch')) and
        request['role']=='backend' and type(request['totalSeconds']) is int and 1<=request['totalSeconds']<=60 and
        type(request['hostBootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',request['hostBootId']) and
        type(request['expectedLaunchSha256']) is str and re.fullmatch('[0-9a-f]{64}',request['expectedLaunchSha256']),
        'FORMAL_LAUNCH_REQUEST_INVALID')
    boot._absolute(request['claimRoot'])
    if with_jvm:
        binding=request['jvmBinding']
        require(type(binding) is dict and set(binding)=={'instanceId','artifactSha256','socket'} and
            type(binding['instanceId']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',binding['instanceId']) and
            type(binding['artifactSha256']) is str and re.fullmatch('[0-9a-f]{64}',binding['artifactSha256']),
            'FORMAL_LAUNCH_JVM_BINDING_INVALID')
        wire=binding['socket']
        require(type(wire) is dict and set(wire)=={'path','identity','pid','uid','gid'} and
            type(wire['pid']) is int and wire['pid']>0 and
            all(type(wire[k]) is int and 0<=wire[k]<2**32-1 for k in ('uid','gid')) and
            type(wire['identity']) is dict and set(wire['identity'])=={'device','inode'} and
            all(type(v) is int and v>0 for v in wire['identity'].values()) and type(wire['path']) is str and
            wire['path'].startswith('/') and str(Path(wire['path']))==wire['path'] and
            '..' not in Path(wire['path']).parts and len(os.fsencode(wire['path']))<108,
            'FORMAL_LAUNCH_JVM_BINDING_INVALID')


def _stage(claim, stopped):
    common={'shared-container-scope','external-caller-scope','shared-health-scope','external-health-scope',
        'maintenance-originals-bound','ingress-scope','ingress-install-intent','ingress-installed'} | {
        'boot-'+role+suffix for role in boot.ROLES for suffix in ('-bound','-close-intent','-closed')} | {
        'live-'+role+suffix for role in boot.ROLES for suffix in ('-close-intent','-closed')}
    capture={'db-fence-intent','db-fenced','split-sql-intent','split-sql-captured','split-raw-intent',
        'split-native-not-requested','split-captured','split-db-probe-before-intent','split-db-probe-before',
        'split-db-probe-after-intent','split-db-probe-after'} | {
        'shared-'+role+suffix for role in split.ROLES for suffix in ('-stop-intent','-stopped')} | {
        'external-'+role+suffix for role in ('test-backend','test-rehearsal','backup-backend','backup-rehearsal')
        for suffix in ('-stop-intent','-stopped')}
    require(all(e['step'] in common | (capture if stopped else set()) for e in claim.events),'FORMAL_LAUNCH_STAGE_INVALID')
    names={e['step'] for e in claim.events}
    pairs={'ingress-install-intent':'ingress-installed','db-fence-intent':'db-fenced',
        'split-sql-intent':'split-sql-captured','split-raw-intent':'split-captured',
        'split-db-probe-before-intent':'split-db-probe-before','split-db-probe-after-intent':'split-db-probe-after'}
    pairs.update({'boot-'+role+'-close-intent':'boot-'+role+'-closed' for role in boot.ROLES})
    pairs.update({'live-'+role+'-close-intent':'live-'+role+'-closed' for role in boot.ROLES})
    pairs.update({'shared-'+role+'-stop-intent':'shared-'+role+'-stopped' for role in split.ROLES})
    pairs.update({'external-'+role+'-stop-intent':'external-'+role+'-stopped' for role in
        ('test-backend','test-rehearsal','backup-backend','backup-rehearsal')})
    require(all((intent in names)==(completed in names) for intent,completed in pairs.items()),
            'FORMAL_LAUNCH_PENDING_ACTION')
    if stopped:
        require('db-fenced' in names,'FORMAL_LAUNCH_STAGE_INVALID')


def run_approved_original_launch(request_path, expected_request_sha256):
    require_native_runtime();require(os.geteuid()==0,'FORMAL_LAUNCH_ROOT_REQUIRED')
    require(type(expected_request_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_request_sha256),
            'FORMAL_LAUNCH_REQUEST_INVALID')
    path=boot._absolute(request_path)
    request_pair=boot._read_secure(path,0o600,16384,no_atime=True)
    raw=request_pair[0]
    require(hashlib.sha256(raw).hexdigest()==expected_request_sha256,'FORMAL_LAUNCH_REQUEST_CHANGED')
    request=_strict_json(raw);_validate(request)
    deadline=time.monotonic()+snapshot.observation_timeout(request['totalSeconds'])
    token=snapshot.observation_deadline.set(deadline);claim=None
    try:
        root=boot._absolute(request['claimRoot'])
        with boot._directory(root) as (_,root_identity):pass
        require(path.stat().st_dev==root.stat().st_dev,'FORMAL_LAUNCH_CONTROL_DEVICE_CHANGED')
        claim=snapshot.FormalMaintenanceClaim(root,request['claimBinding'],resume=True)
        journal=snapshot._canonical_bytes(claim.events)
        stopped=request['action']=='observe-stopped-original-launch';_stage(claim,stopped)
        pins={path:(0o600,16384,request_pair)}
        binding_pair=boot._read_secure(root/'binding.json',0o600,16384,no_atime=True)
        require(binding_pair[0]==claim._plan,'FORMAL_LAUNCH_BINDING_CHANGED')
        pins[root/'binding.json']=(0o600,16384,binding_pair)
        for event in claim.events:
            event_path=root/('event-%06d.json'%event['sequence'])
            pair=boot._read_secure(event_path,0o600,16384,no_atime=True)
            require(_strict_json(pair[0])==event,'FORMAL_LAUNCH_CLAIM_CHANGED')
            pins[event_path]=(0o600,16384,pair)
        event_names={'event-%06d.json'%event['sequence'] for event in claim.events}
        with boot._directory(root,no_atime=True) as (directory,_):
            lock_pair=boot._read_at(directory,'ownership.lock',0o600,1,no_atime=True,allow_empty=True)
        require(lock_pair[0]==b'' and lock_pair[1][:2]==claim._lock_identity,'FORMAL_LAUNCH_CLAIM_CHANGED')
        hashes=snapshot._claim_event(claim,'maintenance-originals-bound')['details']
        require(type(hashes) is dict and set(hashes)=={'originalFileSha256'} and
            type(hashes['originalFileSha256']) is dict and set(hashes['originalFileSha256'])==boot.ORIGINALS,
            'FORMAL_LAUNCH_ORIGINALS_REQUIRED')
        events={'shared-container-original.json':('shared-container-scope','scopeSha256'),
            'external-callers-original.json':('external-caller-scope','scopeSha256'),
            'shared-health-original.json':('shared-health-scope','sha256'),
            'external-callers-health-original.json':('external-health-scope','sha256')}
        for name,(step,key) in events.items():
            pair=boot._read_secure(root/name,0o600,16384,no_atime=True);digest=hashlib.sha256(pair[0]).hexdigest()
            require(hashes['originalFileSha256'][name]==digest and
                snapshot._claim_event(claim,step)['details']=={key:digest},'FORMAL_LAUNCH_ORIGINALS_CHANGED')
            pins[root/name]=(0o600,16384,pair)
        shared_raw=pins[root/'shared-container-original.json'][2][0];shared=_strict_json(shared_raw)
        require(type(shared) is dict and set(shared)==split.ROLES and snapshot._canonical_bytes(shared)==shared_raw,
                'FORMAL_LAUNCH_SCOPE_INVALID')
        for value in shared.values():snapshot._container_stable(value)
        require(len({value['id'] for value in shared.values()})==len(shared) and
            shared['minio']['id']==request['claimBinding']['minioContainerId'],'FORMAL_LAUNCH_SCOPE_INVALID')
        original=shared['backend'];require(original['state']['Running'] is True,'FORMAL_LAUNCH_ORIGIN_NOT_RUNNING')
        if stopped:
            intent=snapshot._claim_event(claim,'shared-backend-stop-intent')['details']
            completed=snapshot._claim_event(claim,'shared-backend-stopped')['details']
            digest=hashlib.sha256(shared_raw).hexdigest()
            require(type(intent) is dict and set(intent)=={'scopeSha256','before','actionRequired'} and
                intent['scopeSha256']==digest and intent['actionRequired'] is True and
                snapshot._canonical_bytes(intent['before'])==snapshot._canonical_bytes(original['state']) and
                type(completed) is dict and set(completed)=={'scopeSha256','runtime','actionPerformed','intentSha256'} and
                completed['scopeSha256']==digest and completed['actionPerformed'] is True and
                completed['intentSha256']==hashlib.sha256(snapshot._canonical_bytes(intent)).hexdigest(),
                'FORMAL_LAUNCH_STOP_COMPLETION_INVALID')
            expected_runtime=completed['runtime']
        else:expected_runtime=original['state']
        # Dict equality would accept integer 0/1 as bools and false as ExitCode
        # zero. Apply the existing native runtime grammar to retained state.
        snapshot._container_stable(dict(original,state=expected_runtime))
        def private_guard():
            claim.assert_owned();snapshot.observation_timeout(1)
            boot._directory_unchanged(root,root_identity)
            require(snapshot._canonical_bytes(claim.events)==journal,'FORMAL_LAUNCH_CLAIM_CHANGED')
            require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==request['hostBootId'],'FORMAL_LAUNCH_BOOT_CHANGED')
            for selected,(mode,limit,pair) in pins.items():
                require(boot._read_secure(selected,mode,limit,no_atime=True)==pair,'FORMAL_LAUNCH_INPUT_CHANGED')
            # Claim reads can themselves occur after the secure reads. The
            # final sweep is after every byte-reading callback, not before it.
            claim.assert_owned()
            # A final callback may replace an earlier pin after its bytes were
            # returned. Recheck every signature without another content read.
            for selected,(_,_,pair) in pins.items():
                require(boot._signature(os.stat(selected,follow_symlinks=False))==pair[1],
                        'FORMAL_LAUNCH_INPUT_CHANGED')
            # The last claim read may append a valid event after its iterator
            # took a snapshot. Pin the directory's event names as well as the
            # already known files, after every content-reading callback.
            with boot._directory(root,no_atime=True) as (directory,current_identity):
                require(current_identity==root_identity and
                        {name for name in os.listdir(directory) if name.startswith('event-')}==event_names,
                        'FORMAL_LAUNCH_CLAIM_CHANGED')
            boot._directory_unchanged(root,root_identity)
            require(boot._signature(os.stat(root/'ownership.lock',follow_symlinks=False))==lock_pair[1] and
                    boot._signature(os.fstat(claim._fd))==lock_pair[1], 'FORMAL_LAUNCH_CLAIM_CHANGED')
            snapshot.observation_timeout(1)
        def runtime_guard():
            private_guard();current=inspect_local_scope(original['id'],deadline=deadline)
            require(snapshot._container_stable(current)==snapshot._container_stable(original) and
                    snapshot._canonical_bytes(current['state'])==snapshot._canonical_bytes(expected_runtime),
                    'FORMAL_LAUNCH_RUNTIME_CHANGED')
            if stopped:split._completed_shared_action(original,current,intent,'stop')
            private_guard();return current
        runtime_guard()
        try:
            if stopped:observed=launch.observe_stopped_original_launch('backend',original['id'],original['image'],
                request['hostBootId'],deadline=deadline)
            else:observed=launch.observe_original_launch('backend',original['id'],original['image'],
                request['hostBootId'],deadline=deadline)
        except launch.LaunchObservationError:
            raise FormalSnapshotError('FORMAL_LAUNCH_SOURCE_UNAVAILABLE') from None
        require(type(observed) is dict and observed.get('role')=='backend' and observed.get('bootId')==request['hostBootId'] and
            observed['inspect']['containerId']==original['id'] and observed['inspect']['imageId']==original['image'] and
            observed['inspect']['digests']['launchSha256']==request['expectedLaunchSha256'],'FORMAL_LAUNCH_SOURCE_CHANGED')
        if stopped:
            require(observed['inspect']['pid']==0 and
                    snapshot._canonical_bytes(observed['inspect']['state'])==snapshot._canonical_bytes(expected_runtime) and
                    observed['processObserved'] is False,'FORMAL_LAUNCH_RUNTIME_CHANGED')
        else:require(observed['inspect']['startedAt']==original['state']['StartedAt'],'FORMAL_LAUNCH_RUNTIME_CHANGED')
        jvm_observed=None;socket_signature=None
        if request['schemaVersion']=='release-formal-capture-request/v11':
            import formal_jvm_identity as jvm
            selected=request['jvmBinding'];artifact=observed.get('currentJar')
            require(type(artifact) is dict and artifact.get('sha256')==selected['artifactSha256'] and
                artifact.get('readOnlyFilesystem') is True and artifact.get('loadedAtStartupBytesProven') is False and
                observed['inspect']['pid']==selected['socket']['pid'], 'FORMAL_LAUNCH_JVM_SOURCE_CHANGED')
            try:
                socket_signature=jvm._socket_signature(selected['socket'])
                jvm_observed=jvm.observe_jvm_identity(selected['socket'],observed['process'],selected['instanceId'],
                    selected['artifactSha256'],request['hostBootId'],deadline=deadline)
            except jvm.JvmIdentityError:
                raise FormalSnapshotError('FORMAL_LAUNCH_JVM_SOURCE_UNAVAILABLE') from None
        runtime_guard();private_guard()
        result={'state':'ORIGINAL_LAUNCH_OBSERVED_ONLY','action':request['action'],'role':'backend',
            'operationId':request['claimBinding']['operationId'],'observation':observed,
            'fullDrain':False,'releaseReady':False,'productionEvidence':False,'serviceActionsPerformed':False,
            'claimReleased':False,'hostWritersVerified':False,'coldStartConfirmed':False,'originalLaunchVerified':False,
            'fullRunnerCompleted':False}
        if jvm_observed is not None:result['jvmObservation']=jvm_observed
        require(len(snapshot._canonical_bytes(result))<=8192,'FORMAL_LAUNCH_OUTPUT_LIMIT')
        private_guard()
        if jvm_observed is not None:
            # After private byte reads, bind the same full native launch again;
            # the tail checks only metadata, never another protocol/content read.
            try:
                final=launch.observe_original_launch('backend',original['id'],original['image'],
                    request['hostBootId'],deadline=deadline)
                launch.require_same_observation(observed,final)
                require(socket_signature==jvm._socket_signature(selected['socket']), 'FORMAL_LAUNCH_JVM_SOURCE_CHANGED')
            except (launch.LaunchObservationError,jvm.JvmIdentityError):
                raise FormalSnapshotError('FORMAL_LAUNCH_JVM_SOURCE_CHANGED') from None
            for pinned,(_,_,pair) in pins.items():
                require(boot._signature(os.stat(pinned,follow_symlinks=False))==pair[1],'FORMAL_LAUNCH_INPUT_CHANGED')
            with boot._directory(root,no_atime=True) as (directory,current_identity):
                require(current_identity==root_identity and
                    {name for name in os.listdir(directory) if name.startswith('event-')}==event_names,
                    'FORMAL_LAUNCH_CLAIM_CHANGED')
            boot._directory_unchanged(root,root_identity)
            require(boot._signature(os.stat(root/'ownership.lock',follow_symlinks=False))==lock_pair[1] and
                boot._signature(os.fstat(claim._fd))==lock_pair[1], 'FORMAL_LAUNCH_CLAIM_CHANGED')
            snapshot.observation_timeout(1)
        return result
    except OSError:
        raise FormalSnapshotError('FORMAL_LAUNCH_IO_FAILED_RETAINED') from None
    finally:
        if claim is not None:claim.close()
        snapshot.observation_deadline.reset(token)
