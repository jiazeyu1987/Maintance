"""Fenced cutover through independently provisioned executors, without rollback."""
from __future__ import annotations

from recovery_engine import (RecoveryError, authorities, check_pin, current_window, pinned_json,
                             require, utc, validate_record, write)
from recovery_plan import verify_report


class Cutover:
    def __init__(self, request, plan, target, policy, trust, runner, guard, journal, lock_fd, original_request_pin,
                 *, plan_pin, target_pin=None, report_pin=None, approval_pin=None, phase='TARGET_CUTOVER', execution_context=None):
        self.request, self.plan, self.target = request, plan, target
        self.policy, self.trust, self.runner, self.guard, self.journal = policy, trust, runner, guard, journal
        self.lock_fd = lock_fd
        self.original_request_pin = original_request_pin
        self.plan_pin, self.target_pin = plan_pin, target_pin
        self.report_pin = report_pin or request['inputPins']['recoveryVerificationReport']
        self.phase, self.execution_context = phase, execution_context
        self.approval_pin = approval_pin
        self.released = False; self.release_dispatched = False; self.switched = False; self.switch_dispatched = False
        self.refs = []

    def execute(self, action, inputs):
        self.guard()
        authorities(self.request, self.target['targetIdentityPin'], ['CONTROLLED_CUTOVER', action], self.trust)
        adapter = self.policy['cutoverAdapters'][action]
        require(adapter['scriptPin']['sha256'] in self.trust['cutoverExecutorSha256s'] and adapter['action'] == action,
                'CUTOVER_EXECUTOR_NOT_TRUSTED')
        child = dict(schemaVersion='RecoveryCutoverRequest/v1', operationId=self.request['operationId'],
            requestId=self.request['requestId']+'-'+action, action=action, mode=self.request['mode'],
            originalRequestPin=self.original_request_pin,
            targetIdentityPin=self.target['targetIdentityPin'], sourceScopePin=self.policy['sourceScopePin'],
            planPin=self.plan_pin, recoveryTargetPin=self.target_pin, phase=self.phase,
            reportPin=self.report_pin, postVerificationApprovalPin=self.approval_pin, authorizationRefs=self.request['authorizationRefs'],
            leaseRef=self.request['leaseRef'], inputPins=inputs, deadlineMilliseconds=self.runner.budget.milliseconds())
        self.journal.phase(action+'_DISPATCH', [])
        from recovery_cutover_terminal import verified_step_terminal
        result, ref = self.runner.run(self.policy['pythonPin'], adapter['scriptPin'], child,
            guard=self.guard, lock_fd=self.lock_fd, execution_context=self.execution_context,
            terminal_verifier=lambda result, request: verified_step_terminal(result, request, self.policy))
        data = result['data']
        require(data['schemaVersion'] == 'RecoveryCutoverStep/v1' and data['action'] == action and
                data['operationId'] == self.request['operationId'] and data['state'] == 'VERIFIED' and
                data['targetIdentityPin'] == self.target['targetIdentityPin'] and
                data['sourceScopePin'] == self.policy['sourceScopePin'] and data['recoveryPoint'] == self.plan['recoveryPoint'] and
                data['originalInvocationPins'] and data['observationPins'], 'CUTOVER_STEP_NOT_VERIFIED')
        for proof in data['originalInvocationPins'] + data['observationPins']:
            check_pin(proof)
        current_window(data)
        if action in ('STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE'):
            require(data['retainedSourceResources'] is True and
                    set(data['writerCoverage']) == {'HTTP', 'QUARTZ', 'MQ', 'EXTERNAL', 'DIRECT_ACCOUNTS'} and
                    all(value == 'ENFORCED' for value in data['writerCoverage'].values()), 'CURRENT_COMPLETE_SOURCE_FENCE_REQUIRED')
            # Never discard writes newer than the selected restored snapshot.
            from recovery_plan_objects import repository_binding
            _, binding = repository_binding(self.plan['candidatePin'], pinned_json(self.plan['candidatePin']), self.policy)
            material = pinned_json(binding['recoveryMaterialPin'])
            require(data['currentSourceRecoveryPoint'] == self.plan['recoveryPoint'] and
                    data['currentSourceDatabasePosition'] == material['database']['endPosition'] and
                    data['sourceDataAndObjectsUnchangedSincePoint'] is True,
                    'SOURCE_ADVANCED_BEYOND_RESTORED_POINT')
        if action == 'VERIFY_TARGET_PROTECTION':
            require(data['applicationWrites'] == data['sideEffectIsolation'] == 'ENFORCED' and
                    data['actualTargetIdentityPin'] == self.target['targetIdentityPin'], 'LIVE_TARGET_PROTECTION_NOT_PROVEN')
        self.refs.append(ref); self.journal.phase(action+'_VERIFIED', [ref])
        return data, ref

    def run(self):
        require(self.request['mode'] == 'CONTROLLED_RESTORE', 'CONTROLLED_MODE_REQUIRED')
        report = verify_report(self.report_pin, self.plan,
                               self.policy, self.trust, require_execution=True, approval_pin=self.approval_pin)
        restore = validate_record(pinned_json(report['restoreResultPin']), 'RestoreExecutionResult', self.policy['recordSchemasPin'])
        application = validate_record(pinned_json(report['applicationStartPin']), 'ApplicationStartResult', self.policy['recordSchemasPin'])
        from recovery_plan_application import protected_application
        protected_application(application, report['restoreResultPin'], self.plan, self.target, self.request, self.policy)
        require(restore['writeProtectionState'] == 'ENFORCED' and
                restore['planPin'] == report['planPin'] == self.plan_pin,
                'CUTOVER_CURRENT_PROTECTED_EXECUTION_REQUIRED')
        data_target = pinned_json(self.policy['dataTargetPin'])
        require(data_target['restoreMode'] in ('REPLACE_EXISTING', 'REBUILD_EMPTY') and data_target['preserveExisting'] is True,
                'CUTOVER_RESTORE_MODE_REQUIRED')
        try:
            self.execute('VERIFY_TARGET_PROTECTION', {'restoreResult': report['restoreResultPin'], 'applicationStart': report['applicationStartPin']})
            from recovery_cutover_fence import fence_handoff
            handoff = fence_handoff(self.request, self.policy)
            stop_ref = handoff['sourceFencePin']
            _, fence_ref = self.execute('OBSERVE_SOURCE_FENCE', {'sourceFence': stop_ref})
            self.execute('VERIFY_TARGET_PROTECTION', {'restoreResult': report['restoreResultPin'], 'applicationStart': report['applicationStartPin']})
            self.switch_dispatched = True
            switch, switch_ref = self.execute('SWITCH_TARGET', {'sourceFence': fence_ref})
            require(switch['retainedSourceResources'] is True and switch['activeTargetIdentityPin'] == self.target['targetIdentityPin'] and
                    switch['applicationWrites'] == 'ENFORCED', 'PROTECTED_TARGET_SWITCH_NOT_PROVEN')
            self.switched = True
            verify_report(self.report_pin, self.plan, self.policy, self.trust, require_execution=True, approval_pin=self.approval_pin)
            _, fence_ref = self.execute('OBSERVE_SOURCE_FENCE', {'sourceFence': stop_ref})
            # Persist the boundary before dispatch. An interrupted release must
            # never imply that writes stayed blocked or trigger an old rollback.
            self.release_dispatched = True
            write(self.runner.root/'write-release-intent.json', dict(schemaVersion='RecoveryWriteReleaseIntent/v1',
                operationId=self.request['operationId'], targetIdentityPin=self.target['targetIdentityPin'],
                switchedTargetPin=switch_ref, dispatchedAt=utc(), automaticRollbackPermitted=False))
            released, released_ref = self.execute('RELEASE_TARGET_WRITES', {'switchResult': switch_ref, 'sourceFence': fence_ref})
            require(released['applicationWrites'] == 'RELEASED' and released['releasedAt'].endswith('Z'),
                    'WRITE_RELEASE_TIME_NOT_PROVEN')
            self.released = True
            generation, generation_ref = self.execute('ESTABLISH_NEW_GENERATION', {'releaseResult': released_ref})
            baseline = validate_record(pinned_json(generation['baselinePointPin']), 'RepositoryPoint', self.policy['recordSchemasPin'])
            old_point = pinned_json(self.plan['candidatePin'])
            require(baseline['pointType'] == 'FULL' and baseline['integrityState'] == 'COMPLETE' and
                    not baseline['parentPointPins'] and baseline['generationId'] != old_point['generationId'] and
                    generation['sourceTargetIdentityPin'] == self.target['targetIdentityPin'] and
                    generation['oldGenerationContinued'] is False, 'NEW_FULL_BACKUP_GENERATION_REQUIRED')
            from recovery_plan import legacy_completion
            legacy_completion(baseline, self.policy)
            return dict(schemaVersion='RecoveryCutoverResult/v1', operationId=self.request['operationId'],
                restoreId=self.plan['restoreId'], targetIdentityPin=self.target['targetIdentityPin'],
                recoveryPoint=self.plan['recoveryPoint'], state='SUCCEEDED', writeProtectionState='RELEASED',
                releasedAt=released['releasedAt'], retainedSourceResources=True, automaticRollbackPermitted=False,
                newGenerationPointPin=generation['baselinePointPin'], stepResultPins=self.refs)
        except Exception as error:
            protection = 'UNKNOWN' if self.release_dispatched else 'ENFORCED'
            # A fresh, separately authorized protection action may stop new
            # writes; it never reverts routing/data to the old environment.
            if self.switch_dispatched:
                try:
                    protected, _ = self.execute('PROTECT_TARGET', {})
                    require(protected['applicationWrites'] == 'ENFORCED' and protected['automaticRollbackPerformed'] is False,
                            'FAILURE_TARGET_PROTECTION_NOT_PROVEN')
                    protection = 'ENFORCED'
                except Exception as protection_error:
                    write(self.runner.root/'cutover-protection-error.json', dict(errorType=type(protection_error).__name__,
                        failureCode=getattr(protection_error, 'code', 'CUTOVER_PROTECTION_FAILURE'), writeProtectionState='UNKNOWN'))
                    protection = 'UNKNOWN'
            write(self.runner.root/'cutover-failure.json', dict(schemaVersion='RecoveryCutoverFailure/v1',
                operationId=self.request['operationId'], targetIdentityPin=self.target['targetIdentityPin'],
                switched=self.switched, switchDispatched=self.switch_dispatched, releaseDispatched=self.release_dispatched,
                released=self.released, writeProtectionState=protection, automaticRollbackPerformed=False,
                oldGenerationMayContinue=False, reconciliationRequired=True, originalStepPins=self.refs))
            if self.release_dispatched or protection == 'UNKNOWN':
                raise RecoveryError('CUTOVER_RECONCILIATION_REQUIRED', unknown=True) from error
            raise
