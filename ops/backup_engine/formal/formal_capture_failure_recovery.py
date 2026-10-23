"""Restore this capture's original source after a confirmed local failure.

The same consumed grant, claim, native transports and positive thaw remain
required. A failed payload is never promoted or needed to reconstruct the
original service identity. Completed actions are observed; pending effects are
not repeated. Missing/ambiguous evidence leaves the source state unknown.
"""
import hashlib
import time

import formal_snapshot_linux as snapshot
from formal_normal_owner import canonical, require


def action_state(names, intent, completed):
    """A durable intent alone never permits another service action."""
    require(len(names) == len(set(names)), 'BACKUP_INTERFACE_BINDING_INVALID')
    require(completed not in names or intent in names, 'BACKUP_INTERFACE_BINDING_INVALID')
    if completed in names:
        require(names.index(intent) < names.index(completed), 'BACKUP_INTERFACE_BINDING_INVALID')
        return 'COMPLETE'
    return 'PENDING' if intent in names else 'NEW'


def restore_failed_capture_source(owner, resume_checks, *, capture_request, recovery,
                                  control_guard, deadline):
    from formal_filesystem_watchdog import require_native_runtime
    import formal_capture_producer as producer
    import formal_split_capture as split
    import formal_service_health as health
    import formal_external_callers as external
    import formal_host_admission as host
    import formal_ingress_control as ingress
    require_native_runtime()
    require(producer._valid_resume_owner(resume_checks,owner.claim) and
            resume_checks.claim is owner.claim and resume_checks.consumed is not None and
            callable(control_guard), 'BACKUP_INTERFACE_AUTHORITY_INVALID')
    claim = owner.claim
    deadline = min(owner.deadline, deadline)
    authority_guard = resume_checks.control_phase_guard(maintenance_end=recovery['maintenance_end'], deadline=deadline)
    mysql = producer.PrivateDockerMySql(capture_request['mysqlContainerId'],
        producer.read_credential(capture_request['mysqlCredentialFile']), timeout=5)
    actions = recovery['container_actions']
    require(actions is not None, 'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    original_flags = resume_checks.database_prefence_flags
    original_source = canonical(actions._originals)
    states = {}

    def names():
        return [event['step'] for event in claim.events]

    def private():
        require(time.monotonic() < deadline, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
        owner.owned()
        control_guard()
        authority_guard()
        # A timeout/failed copy still needs the real native thaw receipt. The
        # absence of a copy result is never treated as positive thaw evidence.
        split._thaw_receipt(claim)
        require(canonical(actions._originals) == original_source, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        owner.owned()

    def observe_role(role):
        private()
        original, current, scope_sha = split._shared_role(claim, role)
        actions.assert_role(role, original, current, guard=private, deadline=deadline)
        private()
        return original, current, scope_sha

    def step_names(role):
        return 'backup-failure-'+role+'-restore-intent', 'backup-failure-'+role+'-restored'

    def effect_matches(original, current, intent):
        before = intent['before']
        state = current['state']
        if intent['actionRequired']:
            return state['Running'] is True and state['StartedAt'] != before['StartedAt']
        return state == before and state['Running'] == original['state']['Running']

    def recover_role(role):
        original, current, scope_sha = observe_role(role)
        # An interrupted original start is only reconciled using its own
        # original journal and native guards. Its command is never reissued.
        old_intent, old_complete = split._action_names(role, 'start')
        old_state = action_state(names(), old_intent, old_complete)
        if old_state == 'PENDING':
            split.reconcile_shared_container(claim, role, 'start', guard=private,
                thaw_guard=lambda: split._thaw_receipt(claim), _controlled_container_actions=actions)
            original, current, scope_sha = observe_role(role)
        elif old_state == 'COMPLETE':
            require(current['state'] == split._event(claim, old_complete)['runtime'],
                    'BACKUP_INTERFACE_SOURCE_CHANGED')
        intent_name, complete_name = step_names(role)
        state = action_state(names(), intent_name, complete_name)
        if state != 'NEW':
            intent = split._event(claim, intent_name)
            require(intent['scopeSha256'] == scope_sha and effect_matches(original, current, intent),
                    'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
            if state == 'PENDING':
                claim.record(complete_name, dict(scopeSha256=scope_sha, runtime=current['state'],
                    intentSha256=hashlib.sha256(canonical(intent)).hexdigest(), actionReplayed=False))
            else:
                completed = split._event(claim, complete_name)
                require(completed['runtime'] == current['state'] and
                        completed['intentSha256'] == hashlib.sha256(canonical(intent)).hexdigest(),
                        'BACKUP_INTERFACE_SOURCE_CHANGED')
            states[role] = current
            return
        stop_intent, stop_complete = split._action_names(role, 'stop')
        stop_state = action_state(names(), stop_intent, stop_complete)
        if stop_state == 'PENDING':
            # This path is an actual pending conditional Docker command. Even
            # an apparently unchanged runtime cannot prove its helper exited.
            raise snapshot.FormalSnapshotError('BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        require(current['state']['Running'] == original['state']['Running'] or
                stop_state == 'COMPLETE' and current['state'] == split._event(claim, stop_complete)['runtime'],
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        required = original['state']['Running'] and not current['state']['Running']
        require(not current['state']['Running'] or original['state']['Running'],
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        intent = dict(scopeSha256=scope_sha, before=current['state'], actionRequired=required)
        claim.record(intent_name, intent)
        observed_original, before, observed_sha = observe_role(role)
        require(observed_original == original and before == current and observed_sha == scope_sha,
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        if required:
            actions.action(role, 'start', original, current, guard=private, deadline=deadline)
        _, after, after_sha = observe_role(role)
        require(after_sha == scope_sha and effect_matches(original, after, intent),
                'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        claim.record(complete_name, dict(scopeSha256=scope_sha, runtime=after['state'],
            intentSha256=hashlib.sha256(canonical(intent)).hexdigest(), actionReplayed=False))
        states[role] = after

    def restore_flags():
        private()
        # An outstanding original SET may still change global flags after a
        # readback. Do not reopen writers or issue a competing SET.
        for intent, completed in (('db-fence-intent', 'db-fenced'),
                ('shared-db-restore-intent', 'shared-db-restored'), ('db-restore-intent', 'db-restored')):
            require(action_state(names(), intent, completed) != 'PENDING', 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        observed = snapshot._database_flags(mysql, original_flags['serverUuid'])
        intent_name = 'backup-failure-database-restore-intent'
        complete_name = 'backup-failure-database-restored'
        state = action_state(names(), intent_name, complete_name)
        if state == 'NEW':
            require(observed in (original_flags, dict(serverUuid=original_flags['serverUuid'],
                    readOnly=1, superReadOnly=1)), 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
            if observed != original_flags:
                require('db-fenced' in names(), 'BACKUP_INTERFACE_AUTHORITY_INVALID')
                snapshot.observe_database_barrier(mysql)
            intent = dict(original=original_flags, before=observed, actionRequired=observed != original_flags)
            claim.record(intent_name, intent)
            private()
            require(snapshot._database_flags(mysql, original_flags['serverUuid']) == observed,
                    'BACKUP_INTERFACE_SOURCE_CHANGED')
            if intent['actionRequired']:
                mysql.query('SET GLOBAL super_read_only=OFF; SET GLOBAL read_only='+
                    ('ON' if original_flags['readOnly'] else 'OFF')+'; SET GLOBAL super_read_only='+
                    ('ON' if original_flags['superReadOnly'] else 'OFF')+';')
        else:
            intent = split._event(claim, intent_name)
            require(intent['original'] == original_flags, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        private()
        require(snapshot._database_flags(mysql, original_flags['serverUuid']) == original_flags,
                'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        if state != 'COMPLETE':
            claim.record(complete_name, dict(originalFlags=original_flags,
                intentSha256=hashlib.sha256(canonical(intent)).hexdigest(), actionReplayed=False))
        else:
            completed = split._event(claim, complete_name)
            require(completed == dict(originalFlags=original_flags,
                intentSha256=hashlib.sha256(canonical(intent)).hexdigest(), actionReplayed=False),
                'BACKUP_INTERFACE_SOURCE_CHANGED')

    def seconds():
        private()
        return min(120, max(1, int(deadline-time.monotonic())))

    def shared_health():
        private()
        require(set(states) == set(split.RESTORE_ORDER), 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        for role in split.RESTORE_ORDER:
            original, current, _ = observe_role(role)
            require(current == states[role] and current['state']['Running'] == original['state']['Running'],
                    'BACKUP_INTERFACE_SOURCE_CHANGED')
        require(snapshot._database_flags(mysql, original_flags['serverUuid']) == original_flags,
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        expected = health._original_health(claim)['health']
        observations = {}
        for role in split.RESTORE_ORDER:
            original, current, _ = observe_role(role)
            if role == 'mysql':
                proof = health._mysql_proof(mysql, current, original_flags)
            else:
                proof = health._await_role(claim, role, current, recovery['health_probe'], private, deadline)
            require(proof['state'] == expected[role]['state'], 'BACKUP_INTERFACE_COMPONENT_FAILED')
            if role in ('frontend', 'showroom') and proof['state'] == 'HEALTHY':
                require(proof['proof']['sha256'] == expected[role]['proof']['sha256'],
                        'BACKUP_INTERFACE_SOURCE_CHANGED')
            observations[role] = proof
        private()
        return observations

    def full_health():
        shared_health()
        result = external.observe_external_restoration_health(claim, recovery['external_transport'],
            dependency_guard=shared_health, seconds=seconds())
        require(result['state'] == 'EXTERNAL_CALLERS_HEALTHY_INGRESS_HELD',
                'BACKUP_INTERFACE_COMPONENT_FAILED')
        private()
        return result

    private()
    held = ingress.observe_ingress_reconciliation(claim, native=recovery['ingress_native'])
    require(held['state'] in ('HELD', 'RELEASED'), 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
    if held['state'] == 'HELD' and 'ingress-recovery-permitted' not in names():
        ingress.permit_recovery_dependencies(claim, recovery['recovery_flows'], guard=private,
            thaw_guard=lambda: split._thaw_receipt(claim), native=recovery['ingress_native'])
    # Restore DB before any data-dependent writer and preserve exact originals.
    for role in split.RESTORE_ORDER:
        recover_role(role)
        if role == 'mysql':
            while not mysql.ready():
                private()
                require(time.monotonic()+.2 < deadline, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
                time.sleep(.2)
                private()
            restore_flags()
    shared_health()
    transport = recovery['external_transport']
    if 'external-recovery-intent' not in names():
        external.begin_external_recovery(claim, transport, dependency_guard=shared_health)
    for role in external.ROLES:
        intent, completed = external._names(role, 'start')
        state = action_state(names(), intent, completed)
        if state == 'NEW':
            external.restore_external_caller(claim, role, transport, dependency_guard=shared_health)
        elif state == 'PENDING':
            external.reconcile_external_caller(claim, role, 'start', transport, dependency_guard=shared_health)
        shared_health()
    full_health()
    for unit in host.RESTORE_ORDER:
        intent, completed = host._step(unit, '-restore-intent'), host._step(unit, '-restored')
        state = action_state(names(), intent, completed)
        require(state != 'PENDING', 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        if state == 'NEW':
            host.restore_host_admission(claim, unit, guard=private, recovery_guard=full_health,
                native=recovery['host_native'], timeout=seconds())
        full_health()
    if held['state'] != 'RELEASED':
        require('ingress-release-intent' not in names(), 'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        ingress.release_ingress(claim, full_health, native=recovery['ingress_native'])

    def final_guard():
        private()
        full_health()
        host._prefix(claim, host._bound(claim), recovery['host_native'], host.RESTORE_ORDER,
            deadline, restored=True)
        observed = ingress.observe_ingress_reconciliation(claim, native=recovery['ingress_native'])
        require(observed['state'] == 'RELEASED' and observed['present'] is False,
                'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        private()

    final_guard()
    return dict(state='FAILED_CAPTURE_SOURCE_ORIGINALS_RESTORED', sourceRestored=True,
        disasterRecoveryVerified=False, capturePayloadAccepted=False, claimReleased=False,
        recoveryActionReplayed=False), final_guard
