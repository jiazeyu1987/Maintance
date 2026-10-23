"""Finite saved-byte OPEN author; no CLI, launcher or independent live proof.

The owner supplies the mandatory ongoing source/launch/dependency/fence guard.
This primitive verifies the independent signature and close/saved-byte lineage,
persists a one-attempt consume boundary, and never repairs interrupted actions.
"""
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time

import formal_boot_state as boot
import formal_open_authorization as authorization
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_snapshot_linux import FormalSnapshotError, require


class OriginalOpenHealthTransition:
    """One exact author suffix over a pinned journal; no independent exclusion proof.

    Used only by the internal signed integration below. Target CLOSED/OPEN locks
    and byte publication remain the author's responsibility, not this guard's.
    """
    def __init__(self,claim,expected,verified,approval_path,key_path):
        require(type(claim) is snapshot.FormalMaintenanceClaim and expected['role']=='backend',
            'FORMAL_OPEN_HEALTH_INPUT_INVALID')
        self.claim=claim;self.expected=json.loads(snapshot._canonical_bytes(expected))
        self.prefix='boot-backend';self.initial=json.loads(snapshot._canonical_bytes(claim.events))
        require(not any('-open-' in event['step'] for event in self.initial),
            'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
        self.details=dict(binding=self.expected,path=_one(claim,self.prefix+'-bound')['path'],
            savedOriginalSha256=expected['originalOpenSha256'],approvalSha256=verified['approvalSha256'],
            keySha256=verified['keySha256'],
            **{key:verified[key] for key in ('grantId','actorId','tenantId','issuedAt','expiresAt')})
        self.consumed=snapshot._canonical_bytes(dict(schemaVersion='formal-original-open-consumption/v1',**self.details))
        self.marker=claim.root/(self.prefix+'-open-approval-consumed.json')
        self.global_marker=claim.root/('original-open-grant-'+verified['grantId']+'.json')
        require(not os.path.lexists(self.marker) and not os.path.lexists(self.global_marker),
            'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
        root=boot._absolute(str(claim.root))
        with boot._directory(root,no_atime=True) as (directory,self.root_identity):
            self.lock=boot._read_at(directory,'ownership.lock',0o600,1,no_atime=True,allow_empty=True)
        require(self.lock[0]==b'' and self.lock[1][:2]==claim._lock_identity,'FORMAL_OPEN_HEALTH_CLAIM_CHANGED')
        paths=[(root/'binding.json',0o600,16384),
            (root/(self.prefix+'-original-open.json'),0o600,4096),
            (boot._absolute(approval_path),0o600,8192),(boot._absolute(key_path),0o644,4096)]
        paths += [(root/name,0o600,16384) for name in boot.ORIGINALS]
        paths.append((root/'shared-dependencies-health.json',0o600,32768))
        paths += [(root/('event-%06d.json'%event['sequence']),0o600,16384) for event in self.initial]
        self.pins={path:(mode,limit,boot._read_secure(path,mode,limit,no_atime=True)) for path,mode,limit in paths}
        require(boot._sha(self.pins[boot._absolute(approval_path)][2][0])==verified['approvalSha256'] and
            boot._sha(self.pins[boot._absolute(key_path)][2][0])==verified['keySha256'],
            'FORMAL_OPEN_APPROVAL_CHANGED')
        self.assert_valid()

    def assert_valid(self):
        claim=self.claim;claim.assert_owned();snapshot.observation_timeout(1)
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.expected['hostBootId'],
            'FORMAL_BOOT_HOST_CHANGED')
        require(snapshot._canonical_bytes(claim.events[:len(self.initial)])==snapshot._canonical_bytes(self.initial),
            'FORMAL_OPEN_HEALTH_JOURNAL_CHANGED')
        suffix=claim.events[len(self.initial):]
        steps=[self.prefix+'-'+name for name in ('open-intent','open-approval-consumed','open-restored')]
        require(len(suffix)<=3 and [event['step'] for event in suffix]==steps[:len(suffix)],
            'FORMAL_OPEN_HEALTH_STAGE_CHANGED')
        for index,event in enumerate(suffix):
            details=event['details'];expected=self.details
            if index==2:
                identity=details.get('publishedIdentity') if type(details) is dict else None
                require(type(identity) is dict and set(identity)=={'device','inode'} and
                    all(type(v) is int and v>0 for v in identity.values()),'FORMAL_OPEN_HEALTH_STAGE_CHANGED')
                expected=dict(expected,publishedIdentity=identity)
            require(snapshot._canonical_bytes(details)==snapshot._canonical_bytes(expected),
                'FORMAL_OPEN_HEALTH_STAGE_CHANGED')
            path=claim.root/('event-%06d.json'%event['sequence'])
            if path not in self.pins:
                pair=boot._read_secure(path,0o600,16384,no_atime=True)
                require(pair[0]==snapshot._canonical_bytes(event),'FORMAL_OPEN_HEALTH_JOURNAL_CHANGED')
                self.pins[path]=(0o600,16384,pair)
        for path in (self.global_marker,self.marker):
            present=os.path.lexists(path)
            require(not present or len(suffix)>0,'FORMAL_OPEN_HEALTH_STAGE_CHANGED')
            require(present or len(suffix)<2,'FORMAL_OPEN_HEALTH_CONSUMPTION_CHANGED')
            if present:
                pair=boot._read_secure(path,0o600,16384,no_atime=True)
                require(pair[0]==self.consumed,'FORMAL_OPEN_HEALTH_CONSUMPTION_CHANGED')
                if path not in self.pins:self.pins[path]=(0o600,16384,pair)
        require(not os.path.lexists(self.marker) or os.path.lexists(self.global_marker),
            'FORMAL_OPEN_HEALTH_CONSUMPTION_CHANGED')
        for path,(mode,limit,pair) in self.pins.items():
            require(boot._read_secure(path,mode,limit,no_atime=True)==pair,'FORMAL_OPEN_HEALTH_INPUT_CHANGED')
        claim.assert_owned()
        for path,(_,_,pair) in self.pins.items():
            require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],'FORMAL_OPEN_HEALTH_INPUT_CHANGED')
        self.event_names={'event-%06d.json'%event['sequence'] for event in self.initial+suffix}
        self.assert_signatures()
        return set(steps[:len(suffix)])

    def assert_signatures(self):
        """No content/owner callbacks after the health observer's native reads."""
        claim=self.claim
        for path,(_,_,pair) in self.pins.items():
            require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],'FORMAL_OPEN_HEALTH_INPUT_CHANGED')
        with boot._directory(claim.root,no_atime=True) as (directory,identity):
            require(identity==self.root_identity and
                {name for name in os.listdir(directory) if name.startswith('event-')}==self.event_names,
                'FORMAL_OPEN_HEALTH_JOURNAL_CHANGED')
        require(boot._signature(os.stat(claim.root/'ownership.lock',follow_symlinks=False))==self.lock[1] and
            boot._signature(os.fstat(claim._fd))==self.lock[1],'FORMAL_OPEN_HEALTH_CLAIM_CHANGED')
        snapshot.observation_timeout(1)


def restore_saved_original_open_with_dependency_health(claim,mysql,approval_path,trusted_key_path,
        trusted_key_sha256,expected_binding,*,expected_receipt_sha256,source_guard,timeout=60):
    """Internal signed one-attempt integration, pending actual full source guard.

    No CLI or start dispatch: a callback alone does not prove maintained host,
    ingress, original launch or accepted-work exclusion. Those are mandatory in
    the future standard runner; all full/release flags remain false here.
    """
    import formal_service_health as health
    import formal_split_capture as split
    require_native_runtime()
    require(os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim and callable(source_guard) and
        type(timeout) is int and 1<=timeout<=300,'FORMAL_OPEN_HEALTH_INPUT_INVALID')
    authorization._binding(expected_binding,'FORMAL_OPEN_HEALTH_INPUT_INVALID')
    require(expected_binding['role']=='backend','FORMAL_OPEN_HEALTH_INPUT_INVALID')
    expected=json.loads(snapshot._canonical_bytes(expected_binding))
    token=snapshot.observation_deadline.set(health.health_deadline(timeout))
    try:
        thaw=split._thaw_receipt(claim)
        def base_guard():
            require(snapshot._canonical_bytes(split._thaw_receipt(claim))==snapshot._canonical_bytes(thaw),
                'FORMAL_OPEN_HEALTH_THAW_CHANGED')
            source_guard();claim.assert_owned();snapshot.observation_timeout(1)
        verified=authorization.verify_original_open_approval(approval_path,trusted_key_path,trusted_key_sha256,
            expected,now_seconds=int(time.time()),guard=base_guard)
        transition=OriginalOpenHealthTransition(claim,expected,verified,approval_path,trusted_key_path)
        receipt_raw=transition.pins[claim.root/'shared-dependencies-health.json'][2][0]
        require(boot._sha(receipt_raw)==expected_receipt_sha256,'FORMAL_OPEN_HEALTH_RECEIPT_CHANGED')
        from formal_s3_export import _strict_json
        receipt=_strict_json(receipt_raw)
        require(type(receipt) is dict and type(receipt.get('applicationsHeld')) is dict and
            set(receipt['applicationsHeld'])=={'backend','frontend'} and
            type(receipt.get('dependencies')) is dict and set(receipt['dependencies'])==set(split.RESTORE_ORDER[:5]) and
            all(type(record) is dict and type(record.get('id')) is str for record in
                list(receipt['applicationsHeld'].values())+list(receipt['dependencies'].values())),
            'FORMAL_OPEN_HEALTH_RECEIPT_CHANGED')
        require(receipt['applicationsHeld']['backend']['id']==expected['containerId'] and
            getattr(mysql,'container',None)==receipt['dependencies']['mysql']['id'],'FORMAL_OPEN_HEALTH_CONTAINER_CHANGED')
        def live_guard():
            base_guard();transition.assert_valid()
            result=health.observe_shared_dependency_health(claim,mysql,expected_receipt_sha256=expected_receipt_sha256,
                guard=base_guard,thaw_guard=lambda:split._thaw_receipt(claim),
                timeout=min(60,snapshot.observation_timeout(60)),open_transition=transition)
            require(result['state']=='DEPENDENCIES_HEALTH_OBSERVED_ONLY','FORMAL_OPEN_HEALTH_REQUIRED')
            transition.assert_valid()
        live_guard()
        result=restore_saved_original_open(claim,approval_path,trusted_key_path,trusted_key_sha256,expected,
            live_guard=live_guard)
        require(len(claim.events)==len(transition.initial)+3,'FORMAL_OPEN_HEALTH_STAGE_CHANGED')
        return dict(result,dependencyHealthChecked=True,fullRunnerCompleted=False,fullPreOpenGuard=False,
            hostWritersVerified=False,coldStartConfirmed=False)
    except OSError:
        raise FormalSnapshotError('FORMAL_OPEN_HEALTH_IO_FAILED_RETAINED') from None
    finally:snapshot.observation_deadline.reset(token)


class OriginalOpenSourceChecks:
    """Actual registered source checks, without continuous host exclusion proof.

    No injected transport or native policy provider in production. The existing
    observers select the fixed local Docker daemon and approved SSH/nft scopes.
    This object cannot authorize a CLI, start, or full pre-OPEN release gate.
    """
    def __init__(self,claim,expected,expected_rules_sha256,expected_external_scope_sha256):
        import formal_split_capture as split
        from formal_s3_export import _strict_json
        require(type(claim) is snapshot.FormalMaintenanceClaim,'FORMAL_OPEN_SOURCE_INPUT_INVALID')
        authorization._binding(expected,'FORMAL_OPEN_SOURCE_INPUT_INVALID')
        require(expected['role']=='backend' and authorization._hex(expected_rules_sha256) and
            authorization._hex(expected_external_scope_sha256),'FORMAL_OPEN_SOURCE_INPUT_INVALID')
        self.claim=claim;self.expected=json.loads(snapshot._canonical_bytes(expected))
        self.rules_sha=expected_rules_sha256;self.external_sha=expected_external_scope_sha256
        claim.assert_owned();self.initial=json.loads(snapshot._canonical_bytes(claim.events))
        require(not any('-open-' in event['step'] for event in self.initial),'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
        # A split-source recovery cannot absorb a legacy whole-capture/start
        # attempt as ordinary history, even while its current PID is still zero.
        legacy={'container-scope','capture-intent','captured','db-probe-before-intent','db-probe-before',
            'db-probe-after-intent','db-probe-after','db-restore-intent','db-restored','released','failed-retained'}
        legacy |= {role+suffix for role in ('backend','minio')
            for suffix in ('-stop-intent','-stopped','-restore-intent','-restored')}
        require(not any(event['step'] in legacy for event in self.initial),'FORMAL_OPEN_SOURCE_STAGE_INVALID')
        root=boot._absolute(str(claim.root))
        with boot._directory(root,no_atime=True) as (directory,self.root_identity):
            self.lock=boot._read_at(directory,'ownership.lock',0o600,1,no_atime=True,allow_empty=True)
        require(self.lock[0]==b'' and self.lock[1][:2]==claim._lock_identity,'FORMAL_OPEN_SOURCE_CLAIM_CHANGED')
        names=boot.ORIGINALS | {'binding.json','ingress-plan.json','ingress-installed.json',
            'ingress-recovery-plan.json','ingress-recovery-installed.json'}
        names |= {'event-%06d.json'%event['sequence'] for event in self.initial}
        self.pins={root/name:boot._read_secure(root/name,0o600,16384,no_atime=True) for name in names}
        require(self.pins[root/'binding.json'][0]==claim._plan,'FORMAL_OPEN_SOURCE_BINDING_CHANGED')
        hashes=_one(claim,'maintenance-originals-bound')
        require(type(hashes) is dict and set(hashes)=={'originalFileSha256'} and
            type(hashes['originalFileSha256']) is dict and set(hashes['originalFileSha256'])==boot.ORIGINALS and
            all(boot._sha(self.pins[root/name][0])==hashes['originalFileSha256'][name] for name in boot.ORIGINALS),
            'FORMAL_OPEN_SOURCE_ORIGINALS_CHANGED')
        shared_raw=self.pins[root/'shared-container-original.json'][0];shared=_strict_json(shared_raw)
        require(type(shared) is dict and set(shared)==split.ROLES and snapshot._canonical_bytes(shared)==shared_raw,
            'FORMAL_OPEN_SOURCE_SHARED_CHANGED')
        for value in shared.values():snapshot._container_stable(value)
        require(len({value['id'] for value in shared.values()})==len(shared) and
            shared['minio']['id']==json.loads(claim._plan)['minioContainerId'] and
            _one(claim,'shared-container-scope')=={'scopeSha256':boot._sha(shared_raw)},
            'FORMAL_OPEN_SOURCE_SHARED_CHANGED')
        require(boot._sha(self.pins[root/'external-callers-original.json'][0])==self.external_sha and
            _one(claim,'external-caller-scope')=={'scopeSha256':self.external_sha} and
            boot._sha(self.pins[root/'ingress-recovery-installed.json'][0])==self.rules_sha,
            'FORMAL_OPEN_SOURCE_SCOPE_CHANGED')
        self.original=shared['backend'];self.intent=_one(claim,'shared-backend-stop-intent')
        completed=_one(claim,'shared-backend-stopped');digest=boot._sha(shared_raw)
        require(self.original['id']==self.expected['containerId'] and self.original['state']['Running'] is True and
            type(self.intent) is dict and set(self.intent)=={'scopeSha256','before','actionRequired'} and
            self.intent['scopeSha256']==digest and self.intent['actionRequired'] is True and
            snapshot._canonical_bytes(self.intent['before'])==snapshot._canonical_bytes(self.original['state']) and
            type(completed) is dict and set(completed)=={'scopeSha256','runtime','actionPerformed','intentSha256'} and
            completed['scopeSha256']==digest and completed['actionPerformed'] is True and
            completed['intentSha256']==boot._sha(snapshot._canonical_bytes(self.intent)),
            'FORMAL_OPEN_SOURCE_STOP_REQUIRED')
        self.runtime=completed['runtime'];stopped=dict(self.original,state=self.runtime)
        snapshot._container_stable(stopped);split._completed_shared_action(self.original,stopped,self.intent,'stop')
        self.private_guard()
        from formal_host_admission import ClosedHostAdmissionChecks
        self.host_checks=ClosedHostAdmissionChecks(claim)

    def signatures(self):
        for path,pair in self.pins.items():
            require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],'FORMAL_OPEN_SOURCE_INPUT_CHANGED')
        with boot._directory(self.claim.root,no_atime=True) as (directory,identity):
            require(identity==self.root_identity and
                {name for name in os.listdir(directory) if name.startswith('event-')}==self.event_names,
                'FORMAL_OPEN_SOURCE_JOURNAL_CHANGED')
        require(boot._signature(os.stat(self.claim.root/'ownership.lock',follow_symlinks=False))==self.lock[1] and
            boot._signature(os.fstat(self.claim._fd))==self.lock[1],'FORMAL_OPEN_SOURCE_CLAIM_CHANGED')
        snapshot.observation_timeout(1)

    def private_guard(self):
        claim=self.claim;claim.assert_owned();snapshot.observation_timeout(1)
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.expected['hostBootId'],
            'FORMAL_BOOT_HOST_CHANGED')
        for path,pair in self.pins.items():
            require(boot._read_secure(path,0o600,16384,no_atime=True)==pair,'FORMAL_OPEN_SOURCE_INPUT_CHANGED')
        claim.assert_owned()
        require(snapshot._canonical_bytes(claim.events[:len(self.initial)])==snapshot._canonical_bytes(self.initial),
            'FORMAL_OPEN_SOURCE_JOURNAL_CHANGED')
        suffix=claim.events[len(self.initial):]
        steps=['boot-backend-'+name for name in ('open-intent','open-approval-consumed','open-restored')]
        require(len(suffix)<=3 and [event['step'] for event in suffix]==steps[:len(suffix)],
            'FORMAL_OPEN_SOURCE_STAGE_CHANGED')
        # Exact signed details/consumption are checked independently by the
        # writer's health transition. Here pin each permitted native event.
        for event in suffix:
            path=claim.root/('event-%06d.json'%event['sequence'])
            pair=boot._read_secure(path,0o600,16384,no_atime=True)
            require(pair[0]==snapshot._canonical_bytes(event),'FORMAL_OPEN_SOURCE_JOURNAL_CHANGED')
            if path in self.pins:require(pair==self.pins[path],'FORMAL_OPEN_SOURCE_JOURNAL_CHANGED')
            else:self.pins[path]=pair
        self.event_names={'event-%06d.json'%event['sequence'] for event in claim.events}
        self.signatures()

    def __call__(self):
        import formal_ingress_control as ingress
        import formal_external_callers as callers
        import formal_original_launch as launch
        import formal_original_launch_capture as capture
        import formal_split_capture as split
        self.private_guard()
        deadline=time.monotonic()+snapshot.observation_timeout(60)
        self.host_checks.prepare(guard=self.signatures,deadline=deadline)
        held=ingress.assert_ingress(self.claim)
        require(type(held) is dict and held.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
            held.get('rulesSha256')==self.rules_sha,'FORMAL_OPEN_SOURCE_INGRESS_REQUIRED')
        external=callers.guard_external_callers(self.claim,callers.SshDockerTransport())
        require(type(external) is dict and external.get('scopeSha256')==self.external_sha and
            external.get('state')=='KNOWN_EXTERNAL_CALLERS_STOPPED_PENDING_FULL_EXCLUSION',
            'FORMAL_OPEN_SOURCE_CALLERS_REQUIRED')
        try:
            observed=launch.observe_stopped_original_launch('backend',self.original['id'],self.original['image'],
                self.expected['hostBootId'],deadline=deadline)
        except launch.LaunchObservationError:
            raise FormalSnapshotError('FORMAL_OPEN_SOURCE_LAUNCH_UNAVAILABLE') from None
        require(observed['inspect']['digests']['launchSha256']==self.expected['launchSha256'] and
            snapshot._canonical_bytes(observed['inspect']['state'])==snapshot._canonical_bytes(self.runtime),
            'FORMAL_OPEN_SOURCE_LAUNCH_CHANGED')
        self.private_guard()
        self.host_checks.prepare(guard=self.signatures,deadline=deadline)
        held=ingress.assert_ingress(self.claim)
        require(type(held) is dict and held.get('phase')=='RECOVERY_DEPENDENCIES_PERMITTED' and
            held.get('rulesSha256')==self.rules_sha,'FORMAL_OPEN_SOURCE_INGRESS_REQUIRED')
        external=callers.guard_external_callers(self.claim,callers.SshDockerTransport())
        require(type(external) is dict and external.get('scopeSha256')==self.external_sha and
            external.get('state')=='KNOWN_EXTERNAL_CALLERS_STOPPED_PENDING_FULL_EXCLUSION',
            'FORMAL_OPEN_SOURCE_CALLERS_REQUIRED')
        self.host_checks.assert_native(deadline=deadline)
        # Private content reads may run after the first full Docker observation.
        # Re-observe immutable launch and retained stop runtime after them; the
        # compact scope projection alone omits most HostConfig/Config fields.
        try:
            final=launch.observe_stopped_original_launch('backend',self.original['id'],self.original['image'],
                self.expected['hostBootId'],deadline=deadline)
        except launch.LaunchObservationError:
            raise FormalSnapshotError('FORMAL_OPEN_SOURCE_LAUNCH_UNAVAILABLE') from None
        require(snapshot._canonical_bytes(final)==snapshot._canonical_bytes(observed),
            'FORMAL_OPEN_SOURCE_LAUNCH_CHANGED')
        current=capture.inspect_local_scope(self.original['id'],deadline=deadline)
        require(snapshot._container_stable(current)==snapshot._container_stable(self.original) and
            snapshot._canonical_bytes(current['state'])==snapshot._canonical_bytes(self.runtime),
            'FORMAL_OPEN_SOURCE_RUNTIME_CHANGED')
        split._completed_shared_action(self.original,current,self.intent,'stop')
        self.host_checks._signatures()
        self.signatures()


def restore_saved_original_open_with_source_checks(claim,mysql,approval_path,trusted_key_path,
        trusted_key_sha256,expected_binding,*,expected_receipt_sha256,expected_rules_sha256,
        expected_external_scope_sha256,timeout=60):
    """Internal actual finite source checks; no production dispatch or start."""
    import formal_service_health as health
    require_native_runtime()
    require(os.geteuid()==0 and type(timeout) is int and 1<=timeout<=300,'FORMAL_OPEN_SOURCE_INPUT_INVALID')
    token=snapshot.observation_deadline.set(health.health_deadline(timeout))
    try:
        checks=OriginalOpenSourceChecks(claim,expected_binding,expected_rules_sha256,expected_external_scope_sha256)
        result=restore_saved_original_open_with_dependency_health(claim,mysql,approval_path,trusted_key_path,
            trusted_key_sha256,expected_binding,expected_receipt_sha256=expected_receipt_sha256,
            source_guard=checks,timeout=timeout)
        # No further content reads after the author's final locked target check.
        return dict(result,sourceChecksPerformed=True)
    except OSError:
        raise FormalSnapshotError('FORMAL_OPEN_SOURCE_IO_FAILED_RETAINED') from None
    finally:snapshot.observation_deadline.reset(token)


def _one(claim, step):
    values = [event['details'] for event in claim.events if event['step'] == step]
    require(len(values) == 1, 'FORMAL_OPEN_CLOSE_COMPLETION_REQUIRED')
    return values[0]


class CompletedOriginalOpenChecks:
    """Bind a completed signed OPEN to one exact existing backend-start suffix.

    Internal, read only and bounded to the current held claim. This does not
    establish exclusion, drain, dependency health or cold-start completion and
    never writes a journal, consumes approval or dispatches a service action.
    """
    def __init__(self,claim,approval_path,trusted_key_path,trusted_key_sha256,expected_binding,*,deadline):
        import formal_split_capture as split
        from formal_s3_export import _strict_json
        require_native_runtime()
        require(os.getuid()==os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim and
            type(deadline) in (int,float) and 0<deadline-time.monotonic()<=300,
            'FORMAL_COLD_OPEN_INPUT_INVALID')
        authorization._binding(expected_binding,'FORMAL_COLD_OPEN_INPUT_INVALID')
        require(expected_binding['role']=='backend','FORMAL_COLD_OPEN_INPUT_INVALID')
        self.claim=claim;self.deadline=deadline
        self.expected=json.loads(snapshot._canonical_bytes(expected_binding))
        self.initial=json.loads(snapshot._canonical_bytes(claim.events))
        steps=['boot-backend-'+name for name in ('open-intent','open-approval-consumed','open-restored')]
        require(len(self.initial)>=3 and [event['step'] for event in self.initial[-3:]]==steps and
            not any('-open-' in event['step'] or event['step'] in
                ('shared-backend-restore-intent','shared-backend-restored','backend-restore-intent',
                 'backend-restored','released','failed-retained') for event in self.initial[:-3]),
            'FORMAL_COLD_OPEN_COMPLETION_REQUIRED')
        root=boot._absolute(str(claim.root));self.pins={}
        token=snapshot.observation_deadline.set(min(deadline,time.monotonic()+snapshot.observation_timeout(300)))
        try:
            with boot._directory(root,no_atime=True) as (directory,self.root_identity):
                self.lock=boot._read_at(directory,'ownership.lock',0o600,1,no_atime=True,allow_empty=True)
            require(self.lock[0]==b'' and self.lock[1][:2]==claim._lock_identity,'FORMAL_COLD_OPEN_CLAIM_CHANGED')
            paths=[(root/'binding.json',0o600,16384),(root/'boot-backend-original-open.json',0o600,4096),
                (boot._absolute(approval_path),0o600,8192),(boot._absolute(trusted_key_path),0o644,4096)]
            paths += [(root/name,0o600,16384) for name in boot.ORIGINALS]
            paths += [(root/('event-%06d.json'%event['sequence']),0o600,16384) for event in self.initial]
            for path,mode,limit in paths:self.pins[path]=(mode,limit,boot._read_secure(path,mode,limit,no_atime=True))
            plan=self.pins[root/'binding.json'][2][0]
            require(plan==claim._plan and json.loads(plan)['operationId']==self.expected['operationId'],
                'FORMAL_COLD_OPEN_BINDING_CHANGED')
            self._base_guard()
            bound=_one(claim,'boot-backend-bound');closed=_one(claim,'boot-backend-closed')
            require(type(bound) is dict and set(bound)==
                {'requestSha256','path','hostBootId','binding','savedOriginalSha256'} and
                _one(claim,'boot-backend-close-intent')==bound and type(closed) is dict and
                set(closed)==set(bound)|{'publishedIdentity'} and {key:closed[key] for key in bound}==bound,
                'FORMAL_COLD_OPEN_CLOSE_REQUIRED')
            closed_identity=closed['publishedIdentity']
            require(type(closed_identity) is dict and set(closed_identity)=={'device','inode'} and
                all(type(value) is int and value>0 for value in closed_identity.values()),
                'FORMAL_COLD_OPEN_CLOSE_REQUIRED')
            selected=bound['binding']
            boot._validate_request(dict(schemaVersion='release-formal-capture-request/v6',
                action='close-durable-boot-state',claimRoot=str(root),claimBinding=json.loads(plan),
                totalSeconds=1,hostBootId=bound['hostBootId'],bootBinding=selected))
            require(bound['path']==selected['path'] and bound['hostBootId']==self.expected['hostBootId'] and
                bound['savedOriginalSha256']==self.expected['originalOpenSha256'] and
                all(selected[key]==self.expected[key] for key in
                    ('role','artifactSha256','originalOpenSha256','closedSha256')) and
                selected['epoch']==self.expected['operationId'] and authorization._hex(bound['requestSha256']),
                'FORMAL_COLD_OPEN_BINDING_CHANGED')
            saved=self.pins[root/'boot-backend-original-open.json'][2][0]
            require(boot._sha(saved)==self.expected['originalOpenSha256'] and
                boot._sha(boot._closed_bytes(saved,selected))==self.expected['closedSha256'],
                'FORMAL_COLD_OPEN_SAVED_BYTES_CHANGED')
            hashes=_one(claim,'maintenance-originals-bound')
            require(type(hashes) is dict and set(hashes)=={'originalFileSha256'} and
                type(hashes['originalFileSha256']) is dict and set(hashes['originalFileSha256'])==boot.ORIGINALS and
                all(boot._sha(self.pins[root/name][2][0])==hashes['originalFileSha256'][name] for name in boot.ORIGINALS),
                'FORMAL_COLD_OPEN_ORIGINALS_CHANGED')
            shared_raw=self.pins[root/'shared-container-original.json'][2][0];shared=_strict_json(shared_raw)
            require(type(shared) is dict and set(shared)==split.ROLES and snapshot._canonical_bytes(shared)==shared_raw,
                'FORMAL_COLD_OPEN_SHARED_CHANGED')
            for value in shared.values():snapshot._container_stable(value)
            require(all(authorization._hex(value['id']) for value in shared.values()) and
                len({value['id'] for value in shared.values()})==len(shared) and
                shared['minio']['id']==json.loads(plan)['minioContainerId'] and
                shared['backend']['id']==self.expected['containerId'] and shared['backend']['state']['Running'] is True,
                'FORMAL_COLD_OPEN_SHARED_CHANGED')
            self.original=shared['backend'];self.scope_sha=boot._sha(shared_raw)
            require(_one(claim,'shared-container-scope')=={'scopeSha256':self.scope_sha},
                'FORMAL_COLD_OPEN_SHARED_CHANGED')
            stop=_one(claim,'shared-backend-stop-intent');stopped=_one(claim,'shared-backend-stopped')
            require(stop==dict(scopeSha256=self.scope_sha,before=self.original['state'],actionRequired=True) and
                type(stop.get('actionRequired')) is bool and type(stopped) is dict and
                set(stopped)=={'scopeSha256','runtime','actionPerformed','intentSha256'} and
                stopped['scopeSha256']==self.scope_sha and stopped['actionPerformed'] is True and
                stopped['intentSha256']==boot._sha(snapshot._canonical_bytes(stop)),
                'FORMAL_COLD_OPEN_STOP_REQUIRED')
            current=dict(self.original,state=stopped['runtime']);snapshot._container_stable(current)
            split._completed_shared_action(self.original,current,stop,'stop')
            self.start_intent=dict(scopeSha256=self.scope_sha,before=current['state'],actionRequired=True)
            self.approved_wall=time.time();self.approved_monotonic=time.monotonic()
            self.verified=authorization.verify_original_open_approval(approval_path,trusted_key_path,
                trusted_key_sha256,self.expected,now_seconds=int(self.approved_wall),guard=self._base_guard)
            details=dict(binding=self.expected,path=bound['path'],savedOriginalSha256=self.expected['originalOpenSha256'],
                approvalSha256=self.verified['approvalSha256'],keySha256=self.verified['keySha256'],
                **{key:self.verified[key] for key in ('grantId','actorId','tenantId','issuedAt','expiresAt')})
            published=self.initial[-1]['details'].get('publishedIdentity')
            require(type(published) is dict and set(published)=={'device','inode'} and
                all(type(value) is int and value>0 for value in published.values()) and
                self.initial[-3]['details']==details and self.initial[-2]['details']==details and
                self.initial[-1]['details']==dict(details,publishedIdentity=published),
                'FORMAL_COLD_OPEN_COMPLETION_CHANGED')
            consumed=snapshot._canonical_bytes(dict(schemaVersion='formal-original-open-consumption/v1',**details))
            for name in ('boot-backend-open-approval-consumed.json','original-open-grant-'+self.verified['grantId']+'.json'):
                pair=boot._read_secure(root/name,0o600,16384,no_atime=True)
                require(pair[0]==consumed,'FORMAL_COLD_OPEN_CONSUMPTION_CHANGED')
                self.pins[root/name]=(0o600,16384,pair)
            self.target=boot._absolute(bound['path'])
            with boot._directory(self.target.parent,no_atime=True) as (directory,self.target_directory):
                self.target_lock=boot._read_at(directory,self.target.name+'.writer.lock',0o600,1,
                    no_atime=True,allow_empty=True)
            require(self.target_lock[0]==b'','FORMAL_COLD_OPEN_TARGET_LOCK_CHANGED')
            self.target_pair=boot._read_secure(self.target,0o644,4096,no_atime=True)
            require(self.target_pair[0]==saved and
                dict(device=self.target_pair[1][0],inode=self.target_pair[1][1])==published and
                published!=closed['publishedIdentity'],'FORMAL_COLD_OPEN_TARGET_CHANGED')
            self.assert_valid()
        except OSError:raise FormalSnapshotError('FORMAL_COLD_OPEN_IO_FAILED_RETAINED') from None
        finally:snapshot.observation_deadline.reset(token)

    def _base_guard(self):
        require(time.monotonic()<self.deadline,'FORMAL_COLD_OPEN_DEADLINE_EXPIRED')
        self.claim.assert_owned();snapshot.observation_timeout(1)
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.expected['hostBootId'] and
            snapshot._canonical_bytes(self.claim.events[:len(self.initial)])==snapshot._canonical_bytes(self.initial),
            'FORMAL_COLD_OPEN_BINDING_CHANGED')
        for path,(mode,limit,pair) in self.pins.items():
            require(boot._read_secure(path,mode,limit,no_atime=True)==pair,'FORMAL_COLD_OPEN_INPUT_CHANGED')

    def assert_valid(self):
        import formal_split_capture as split
        try:
            self._base_guard()
            suffix=self.claim.events[len(self.initial):]
            steps=('shared-backend-restore-intent','shared-backend-restored')
            require(len(suffix)<=2 and [event['step'] for event in suffix]==list(steps[:len(suffix)]),
                'FORMAL_COLD_OPEN_START_STAGE_CHANGED')
            if suffix:
                require(snapshot._canonical_bytes(suffix[0]['details'])==snapshot._canonical_bytes(self.start_intent),
                    'FORMAL_COLD_OPEN_START_INTENT_CHANGED')
            if len(suffix)==2:
                completed=suffix[1]['details']
                require(type(completed) is dict and set(completed)==
                    {'scopeSha256','runtime','actionPerformed','intentSha256'} and
                    completed['scopeSha256']==self.scope_sha and completed['actionPerformed'] is True and
                    completed['intentSha256']==boot._sha(snapshot._canonical_bytes(self.start_intent)),
                    'FORMAL_COLD_OPEN_START_COMPLETION_CHANGED')
                current=dict(self.original,state=completed['runtime']);snapshot._container_stable(current)
                split._completed_shared_action(self.original,current,self.start_intent,'start')
            for event in suffix:
                path=self.claim.root/('event-%06d.json'%event['sequence'])
                pair=boot._read_secure(path,0o600,16384,no_atime=True)
                require(pair[0]==snapshot._canonical_bytes(event),'FORMAL_COLD_OPEN_JOURNAL_CHANGED')
                if path in self.pins:require(pair==self.pins[path][2],'FORMAL_COLD_OPEN_JOURNAL_CHANGED')
                else:self.pins[path]=(0o600,16384,pair)
            now=time.time();elapsed=time.monotonic()-self.approved_monotonic
            require(elapsed>=0 and self.verified['issuedAt']<=now<self.verified['expiresAt'] and
                self.approved_wall+elapsed<self.verified['expiresAt'],'FORMAL_COLD_OPEN_APPROVAL_EXPIRED')
            result=dict(startStage=('NOT_ATTEMPTED','INTENT_RETAINED',
                'RUNTIME_RECORDED_PENDING_FULL_COLD_CONFIRMATION')[len(suffix)],completedOriginalOpenBound=True,
                coldStartConfirmed=False,fullPreOpenGuard=False,releaseReady=False,serviceActionsPerformed=False,
                productionEvidence=False,fullDrain=False,fullHostFence=False)
            self.event_names={'event-%06d.json'%event['sequence'] for event in self.claim.events}
            self.claim.assert_owned()
            for path,(mode,limit,pair) in self.pins.items():
                require(boot._read_secure(path,mode,limit,no_atime=True)==pair,'FORMAL_COLD_OPEN_INPUT_CHANGED')
            require(boot._read_secure(self.target,0o644,4096,no_atime=True)==self.target_pair,
                'FORMAL_COLD_OPEN_TARGET_CHANGED')
            self.assert_signatures()
            return result
        except OSError:raise FormalSnapshotError('FORMAL_COLD_OPEN_IO_FAILED_RETAINED') from None

    def assert_signatures(self):
        """No content reads or owner callbacks after the observer's native reads."""
        try:
            for path,(_,_,pair) in self.pins.items():
                require(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],'FORMAL_COLD_OPEN_INPUT_CHANGED')
            require(boot._signature(os.stat(self.target,follow_symlinks=False))==self.target_pair[1],
                'FORMAL_COLD_OPEN_TARGET_CHANGED')
            with boot._directory(self.target.parent,no_atime=True) as (_,identity):
                require(identity==self.target_directory and
                    boot._signature(os.stat(self.target.parent/(self.target.name+'.writer.lock'),follow_symlinks=False))==
                    self.target_lock[1],'FORMAL_COLD_OPEN_TARGET_LOCK_CHANGED')
            with boot._directory(self.claim.root,no_atime=True) as (directory,identity):
                require(identity==self.root_identity and
                    {name for name in os.listdir(directory) if name.startswith('event-')}==self.event_names,
                    'FORMAL_COLD_OPEN_JOURNAL_CHANGED')
            require(boot._signature(os.stat(self.claim.root/'ownership.lock',follow_symlinks=False))==self.lock[1] and
                boot._signature(os.fstat(self.claim._fd))==self.lock[1],'FORMAL_COLD_OPEN_CLAIM_CHANGED')
            now=time.time();elapsed=time.monotonic()-self.approved_monotonic
            require(elapsed>=0 and self.verified['issuedAt']<=now<self.verified['expiresAt'] and
                self.approved_wall+elapsed<self.verified['expiresAt'],'FORMAL_COLD_OPEN_APPROVAL_EXPIRED')
            require(time.monotonic()<self.deadline,'FORMAL_COLD_OPEN_DEADLINE_EXPIRED')
            snapshot.observation_timeout(1)
        except OSError:raise FormalSnapshotError('FORMAL_COLD_OPEN_IO_FAILED_RETAINED') from None


def restore_saved_original_open(claim, approval_path, trusted_key_path,
                                trusted_key_sha256, expected_binding, *, live_guard):
    """One non-replayable attempt under the existing claim and target lock.

    Neither expected binding nor a Python callback proves actual original launch
    or dependencies. Production orchestration must bind those before exposing
    this operation. The returned finite receipt never claims those facts.
    """
    require_native_runtime()
    require(os.geteuid() == 0, 'FORMAL_OPEN_ROOT_REQUIRED')
    require(type(claim) is snapshot.FormalMaintenanceClaim and callable(live_guard),
            'FORMAL_OPEN_WRITER_INPUT_INVALID')
    authorization._binding(expected_binding, 'FORMAL_OPEN_WRITER_INPUT_INVALID')
    # Detach caller-owned input so a guard cannot mutate the expected binding.
    expected = dict(expected_binding)
    prefix = 'boot-'+expected['role']
    marker = claim.root/(prefix+'-open-approval-consumed.json')
    try:
        claim.assert_owned(); snapshot.observation_timeout(1)
        root = boot._absolute(str(claim.root))
        with boot._directory(root) as (_, root_identity):
            require(stat.S_IMODE(root.stat().st_mode) == 0o700, 'FORMAL_BOOT_DIRECTORY_UNTRUSTED')
        claim_plan, claim_plan_identity = boot._read_secure(root/'binding.json', 0o600, 16384)
        require(claim_plan == claim._plan and json.loads(claim_plan)['operationId'] == expected['operationId'],
                'FORMAL_OPEN_BINDING_CHANGED')
        require(not any(event['step'].startswith(prefix+'-open-') for event in claim.events) and
                not os.path.lexists(marker), 'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
        bound = _one(claim, prefix+'-bound')
        intent = _one(claim, prefix+'-close-intent')
        completed = _one(claim, prefix+'-closed')
        require(type(bound) is dict and set(bound) ==
                {'requestSha256','path','hostBootId','binding','savedOriginalSha256'} and intent == bound and
                set(completed) == set(bound) | {'publishedIdentity'} and
                {key:completed[key] for key in bound} == bound,
                'FORMAL_OPEN_CLOSE_COMPLETION_REQUIRED')
        selected = bound['binding']
        # Validate the same exact finite close binding, rather than inventing an
        # OPEN schema that could loosen the original close contract.
        boot._validate_request(dict(schemaVersion='release-formal-capture-request/v6',
            action='close-durable-boot-state', claimRoot=str(root), claimBinding=json.loads(claim_plan),
            totalSeconds=1, hostBootId=bound['hostBootId'], bootBinding=selected))
        require(bound['path'] == selected['path'] and bound['hostBootId'] == expected['hostBootId'] and
                bound['savedOriginalSha256'] == expected['originalOpenSha256'] and
                all(selected[key] == expected[key] for key in
                    ('role','artifactSha256','originalOpenSha256','closedSha256')) and
                selected['epoch'] == expected['operationId'] and
                authorization._hex(bound['requestSha256']), 'FORMAL_OPEN_BINDING_CHANGED')
        published_identity = completed['publishedIdentity']
        require(type(published_identity) is dict and set(published_identity) == {'device','inode'} and
                all(type(value) is int and value > 0 for value in published_identity.values()),
                'FORMAL_OPEN_CLOSE_COMPLETION_REQUIRED')
        lineage = json.loads(snapshot._canonical_bytes([bound,intent,completed]))
        saved_path = root/(prefix+'-original-open.json')
        saved, saved_identity = boot._read_secure(saved_path, 0o600, 4096)
        closed = boot._closed_bytes(saved, selected)
        require(boot._sha(saved) == expected['originalOpenSha256'] and
                boot._sha(closed) == expected['closedSha256'], 'FORMAL_OPEN_SAVED_BYTES_CHANGED')
        original_binding = _one(claim, 'maintenance-originals-bound')
        require(set(original_binding) == {'originalFileSha256'} and
                type(original_binding['originalFileSha256']) is dict and
                set(original_binding['originalFileSha256']) == boot.ORIGINALS,
                'FORMAL_BOOT_ORIGINALS_REQUIRED')
        originals = dict(original_binding['originalFileSha256'])
        target = boot._absolute(selected['path'])
        def source_guard():
            snapshot.observation_timeout(1); claim.assert_owned()
            live_guard(); snapshot.observation_timeout(1); claim.assert_owned()
            boot._directory_unchanged(root, root_identity)
            require(boot._read_secure(root/'binding.json',0o600,16384) == (claim_plan,claim_plan_identity),
                    'FORMAL_OPEN_BINDING_CHANGED')
            require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == expected['hostBootId'],
                    'FORMAL_BOOT_HOST_CHANGED')
            require([_one(claim, prefix+suffix) for suffix in ('-bound','-close-intent','-closed')] == lineage,
                    'FORMAL_OPEN_BINDING_CHANGED')
            require(boot._read_secure(saved_path,0o600,4096) == (saved,saved_identity),
                    'FORMAL_OPEN_SAVED_BYTES_CHANGED')
            require(_one(claim,'maintenance-originals-bound') == original_binding,
                    'FORMAL_BOOT_ORIGINALS_CHANGED')
            for name, digest in originals.items():
                require(authorization._hex(digest) and boot._sha(boot._read_secure(root/name,0o600,16384)[0]) == digest,
                        'FORMAL_BOOT_ORIGINALS_CHANGED')
        source_guard()
        # Actual current time is sampled again by action guards below; a caller
        # cannot supply a stale epoch value to extend the signed lifetime.
        approved_wall = time.time(); approved_monotonic = time.monotonic()
        verified = authorization.verify_original_open_approval(approval_path, trusted_key_path,
            trusted_key_sha256, expected, now_seconds=int(approved_wall), guard=source_guard)
        global_marker = root/('original-open-grant-'+verified['grantId']+'.json')
        require(not os.path.lexists(global_marker), 'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
        approval_raw, approval_identity = boot._read_secure(approval_path,0o600,8192,no_atime=True)
        key_raw, key_identity = boot._read_secure(trusted_key_path,0o644,4096,no_atime=True)
        require(boot._sha(approval_raw) == verified['approvalSha256'] and
                boot._sha(key_raw) == verified['keySha256'], 'FORMAL_OPEN_APPROVAL_CHANGED')
        def approval_guard():
            source_guard()
            require(boot._read_secure(approval_path,0o600,8192,no_atime=True) == (approval_raw,approval_identity),
                    'FORMAL_OPEN_APPROVAL_CHANGED')
            require(boot._read_secure(trusted_key_path,0o644,4096,no_atime=True) == (key_raw,key_identity),
                    'FORMAL_OPEN_TRUSTED_KEY_CHANGED')
            now = time.time()
            elapsed = time.monotonic()-approved_monotonic
            require(elapsed >= 0 and verified['issuedAt'] <= now < verified['expiresAt'] and
                    approved_wall+elapsed < verified['expiresAt'], 'FORMAL_OPEN_PAYLOAD_INVALID')
        with boot._directory(target.parent) as (directory, directory_identity):
            lock_name = target.name+'.writer.lock'
            pending = '.boot-open-'+verified['approvalSha256']+'.pending'
            name_max = os.fpathconf(directory, 'PC_NAME_MAX')
            require(type(name_max) is int and name_max > 0 and
                    all(len(name.encode()) <= name_max for name in (lock_name,pending)),
                    'FORMAL_BOOT_NAME_LIMIT_INVALID')
            require(not os.path.lexists(target.parent/pending), 'FORMAL_OPEN_TRANSITION_ALREADY_ATTEMPTED')
            # The close operation already made this shared target lock. Missing
            # or untrusted locks are refused, never silently recreated.
            fd = os.open(lock_name, os.O_RDWR|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC, dir_fd=directory)
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and
                        stat.S_IMODE(info.st_mode) == 0o600 and info.st_size == 0,
                        'FORMAL_BOOT_LOCK_UNTRUSTED')
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: raise FormalSnapshotError('FORMAL_BOOT_TARGET_BUSY') from None
                lock_identity = boot._signature(info)
                def target_guard():
                    approval_guard(); boot._directory_unchanged(target.parent,directory_identity)
                    require(boot._signature(os.fstat(fd)) == lock_identity and
                            boot._signature(os.stat(lock_name,dir_fd=directory,follow_symlinks=False)) == lock_identity,
                            'FORMAL_BOOT_LOCK_CHANGED')
                target_guard()
                current, closed_identity = boot._read_at(directory,target.name,0o644,4096)
                require(current == closed and {'device':closed_identity[0],'inode':closed_identity[1]} == published_identity,
                        'FORMAL_OPEN_CLOSED_BINDING_CHANGED')
                def closed_guard():
                    target_guard()
                    require(boot._read_at(directory,target.name,0o644,4096) == (closed,closed_identity),
                            'FORMAL_OPEN_CLOSED_BINDING_CHANGED')
                details = dict(binding=expected,path=str(target),savedOriginalSha256=boot._sha(saved),
                    approvalSha256=verified['approvalSha256'],keySha256=verified['keySha256'],
                    **{key:verified[key] for key in ('grantId','actorId','tenantId','issuedAt','expiresAt')})
                consumed_raw = snapshot._canonical_bytes(dict(schemaVersion='formal-original-open-consumption/v1', **details))
                require(len(consumed_raw) <= 16384, 'FORMAL_OPEN_WRITER_INPUT_INVALID')
                closed_guard(); claim.record(prefix+'-open-intent',details)
                closed_guard(); claim._write(global_marker,consumed_raw)
                global_consumed, global_identity = boot._read_secure(global_marker,0o600,16384)
                require(global_consumed == consumed_raw, 'FORMAL_OPEN_CONSUMPTION_UNCONFIRMED')
                closed_guard(); claim._write(marker,consumed_raw)
                consumed, consumed_identity = boot._read_secure(marker,0o600,16384)
                require(consumed == consumed_raw, 'FORMAL_OPEN_CONSUMPTION_UNCONFIRMED')
                def consumed_guard():
                    target_guard()
                    require(boot._read_secure(marker,0o600,16384) == (consumed_raw,consumed_identity),
                            'FORMAL_OPEN_CONSUMPTION_UNCONFIRMED')
                    require(boot._read_secure(global_marker,0o600,16384) == (consumed_raw,global_identity),
                            'FORMAL_OPEN_CONSUMPTION_UNCONFIRMED')
                closed_guard(); consumed_guard(); claim.record(prefix+'-open-approval-consumed',details)
                closed_guard(); consumed_guard()
                temporary = os.open(pending,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644,dir_fd=directory)
                try:
                    os.fchmod(temporary,0o644)
                    with os.fdopen(temporary,'wb',closefd=False) as output:
                        output.write(saved); output.flush(); os.fsync(temporary)
                finally: os.close(temporary)
                closed_guard(); consumed_guard()
                require(boot._read_at(directory,pending,0o644,4096)[0] == saved,
                        'FORMAL_OPEN_PUBLICATION_UNCONFIRMED')
                closed_guard(); consumed_guard()
                os.replace(pending,target.name,src_dir_fd=directory,dst_dir_fd=directory)
                os.fsync(directory); consumed_guard()
                published, new_identity = boot._read_at(directory,target.name,0o644,4096)
                require(published == saved and new_identity[:2] != closed_identity[:2],
                        'FORMAL_OPEN_PUBLICATION_UNCONFIRMED')
                def published_guard():
                    consumed_guard()
                    require(boot._read_at(directory,target.name,0o644,4096) == (saved,new_identity),
                            'FORMAL_OPEN_PUBLICATION_UNCONFIRMED')
                published_guard()
                claim.record(prefix+'-open-restored',dict(details,
                    publishedIdentity={'device':new_identity[0],'inode':new_identity[1]}))
                published_guard()
                return dict(state='SAVED_ORIGINAL_OPEN_RESTORED_PENDING_COLD_START',
                    role=expected['role'],epoch=expected['operationId'],approvalSha256=verified['approvalSha256'],
                    grantId=verified['grantId'],originalOpenSha256=expected['originalOpenSha256'],
                    approvalConsumed=True,durableOriginalOpenConfirmed=True,originalLaunchVerified=False,
                    serviceActionsPerformed=False,claimReleased=False,productionEvidence=False,releaseReady=False)
            finally: os.close(fd)
    except OSError:
        raise FormalSnapshotError('FORMAL_OPEN_IO_FAILED_RETAINED') from None
