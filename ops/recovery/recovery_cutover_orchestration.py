"""Frozen public cutover inputs; all execution originals are generated internally."""
import os

from recovery_engine import authorities, check_pin, digest, pinned_json, require, validate_record, write
from recovery_plan import preflight, prepared_target, verify_report
from recovery_plan_application import protected_application
from recovery_cutover import Cutover
from recovery_cutover_fence import CONTEXT_KEY, establish_fence


def controlled_restore(operation):
    request, policy, trust = operation.request, operation.policy, operation.trust
    require(request['mode'] == 'CONTROLLED_RESTORE' and os.name == 'posix', 'CONTROLLED_NATIVE_MODE_REQUIRED')
    plan, chain, data_target = preflight(request, trust, policy, operation.config)
    identity = data_target['targetIdentityPin']
    authorities(request, identity, ['CONTROLLED_CUTOVER', 'RESTORE_EXECUTE', 'PREPARE_TARGET', 'START_APPLICATION'], trust)
    # Resolve all command and independent verification prerequisites before
    # the first source stop. Future reports are selected by the provisioned
    # independent service and require post-report repository signatures.
    capability_pin = policy.get('environmentFenceHandoffCapabilityPin')
    require(type(capability_pin) is dict and capability_pin['sha256'] in trust['environmentFenceHandoffCapabilitySha256s'],
            'ENVIRONMENT_FENCE_HANDOFF_CONSUMER_NOT_CONFIGURED')
    capability = pinned_json(capability_pin)
    environment_policy = pinned_json(request['policyPin'])
    require(capability['schemaVersion'] == 'RecoveryEnvironmentFenceCapability/v1' and
            capability['handoffSchemaVersion'] == 'RecoveryControlledFenceHandoff/v1' and
            capability['contextEnvironmentKey'] == CONTEXT_KEY and capability['environmentCliPin'] == policy['environmentCliPin'] and
            capability['moduleSourcePins'] == environment_policy['moduleSourcePins'] and
            capability['checksOriginalProcessTermination'] is True, 'ENVIRONMENT_FENCE_HANDOFF_CAPABILITY_INVALID')
    for ref in capability['moduleSourcePins']: check_pin(ref, content=False)
    adapter = policy.get('controlledVerificationAdapter')
    require(type(adapter) is dict and adapter['schemaVersion'] == 'RecoveryControlledVerificationAdapter/v1' and
            adapter['scriptPin']['sha256'] in trust['controlledVerificationExecutorSha256s'] and
            adapter['independentCallerBindingPin']['sha256'] in trust['controlledVerificationCallerBindingSha256s'],
            'INDEPENDENT_CONTROLLED_VERIFICATION_ADAPTER_REQUIRED')
    for field in ('scriptPin', 'independentCallerBindingPin', 'configurationPin'): check_pin(adapter[field])
    binding = pinned_json(adapter['independentCallerBindingPin'])
    require(binding['schemaVersion'] == 'RecoveryControlledVerificationCaller/v1' and
            binding['operationId'] == request['operationId'] and binding['targetIdentityPin'] == identity and
            binding['sourceScopePin'] == policy['sourceScopePin'] and binding['selectedPointPin'] == request['selectedPointPin'] and
            binding['callerId'] != trust['executorId'] and binding['configurationPin'] == adapter['configurationPin'],
            'CONTROLLED_VERIFIER_CALLER_NOT_INDEPENDENT')
    from recovery_engine import current_window
    current_window(binding)
    require(policy['repositoryId'] and policy['repositoryEvidenceKeyPins'], 'POST_VERIFICATION_APPROVAL_AUTHORITY_REQUIRED')
    for action, executor in policy['cutoverAdapters'].items():
        require(executor['action'] == action and executor['scriptPin']['sha256'] in trust['cutoverExecutorSha256s'], 'CUTOVER_EXECUTOR_NOT_TRUSTED')
        check_pin(executor['scriptPin'])
        recipe_pin = policy['cutoverRecipePins'][action]
        require(recipe_pin['sha256'] in trust['cutoverRecipeSha256s'], 'CUTOVER_RECIPE_NOT_INDEPENDENTLY_TRUSTED')
        recipe = pinned_json(recipe_pin); current_window(recipe)
        require(recipe['action'] == action and recipe['targetIdentityPin'] == identity and
                recipe['sourceScopePin'] == policy['sourceScopePin'] and recipe['recoveryPoint'] == plan['recoveryPoint'] and
                recipe['commands'], 'CUTOVER_RECIPE_SCOPE_INVALID')
        authorities(request, identity, ['CONTROLLED_CUTOVER', action], trust)
        for command in recipe['commands']:
            require(command['executionKind'] in ('LOCAL', 'REMOTE') and command['toolPin']['sha256'] in trust['cutoverToolSha256s'],
                    'CUTOVER_COMMAND_NOT_APPROVED')
            for field in ('toolPin', 'configurationPin', 'executionHostIdentityPin'): check_pin(command[field], content=False)
            if command['executionKind'] == 'REMOTE':
                require(policy['remoteTerminalKeyPins'], 'REMOTE_TERMINAL_AUTHORITY_REQUIRED')
                for ref in policy['remoteTerminalKeyPins']: check_pin(ref)
    require(set(policy['cutoverAdapters']) == {'VERIFY_TARGET_PROTECTION', 'STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE',
            'SWITCH_TARGET', 'RELEASE_TARGET_WRITES', 'ESTABLISH_NEW_GENERATION', 'PROTECT_TARGET'}, 'CUTOVER_ACTION_CLOSURE_INCOMPLETE')
    plan_pin = write(operation.runner.root/'restore-plan.json', plan)
    source = Cutover(request, plan, {'targetIdentityPin': identity}, policy, trust, operation.runner, operation.guard,
        operation.journal, operation.lock.fd, operation.request_pin, plan_pin=plan_pin, phase='SOURCE_FENCE')
    handoff_pin = establish_fence(source, operation.request_pin)
    operation.execution_context = {CONTEXT_KEY: handoff_pin}
    old_context = os.environ.get(CONTEXT_KEY)
    os.environ[CONTEXT_KEY] = __import__('recovery_engine').canonical(handoff_pin).decode('utf-8')
    try:
        operation.journal.phase('SOURCE_FENCE_VERIFIED', [handoff_pin])
        operation.restore_original_start = len(operation.runner.original_pins)
        target_result, _ = operation.environment('PREPARE_TARGET', {'restorePlan': plan_pin})
        target = validate_record(target_result['data'], 'RecoveryTarget', policy['recordSchemasPin'])
        target_pin = write(operation.runner.root/'recovery-target.json', target)
        prepared_target(dict(request, inputPins={'recoveryTarget': target_pin}), plan, policy, trust)
        execution, execution_pin = operation.restore(plan_pin, target_pin)
        started, _ = operation.environment('START_APPLICATION', {'restoreExecutionResult': execution_pin, 'recoveryTarget': target_pin})
        application = validate_record(started['data'], 'ApplicationStartResult', policy['recordSchemasPin'])
        protected_application(application, execution_pin, plan, target, request, policy)
        application_pin = write(operation.runner.root/'application-start-result.json', application)
        child = dict(schemaVersion='RecoveryControlledVerificationRequest/v1', operationId=request['operationId'],
            requestId=request['requestId']+'-INDEPENDENT_VERIFY', action='VERIFY_RECOVERY', originalRequestPin=operation.request_pin,
            independentCallerBindingPin=adapter['independentCallerBindingPin'], configurationPin=adapter['configurationPin'],
            planPin=plan_pin, recoveryTargetPin=target_pin, restoreResultPin=execution_pin, applicationStartPin=application_pin,
            deadlineMilliseconds=operation.runner.budget.milliseconds())
        result, original_ref = operation.runner.run(policy['pythonPin'], adapter['scriptPin'], child,
            guard=operation.guard, lock_fd=operation.lock.fd, execution_context=operation.execution_context)
        verified = result['data']
        require(verified['schemaVersion'] == 'RecoveryControlledVerificationResult/v1' and
                verified['operationId'] == request['operationId'] and verified['restoreId'] == plan['restoreId'] and
                verified['independentCallerBindingPin'] == adapter['independentCallerBindingPin'],
                'CONTROLLED_VERIFIER_RESULT_UNBOUND')
        report = verify_report(verified['reportPin'], plan, policy, trust, require_execution=True,
                               approval_pin=verified['postVerificationApprovalPin'])
        require(report['planPin'] == plan_pin and report['restoreResultPin'] == execution_pin and
                report['applicationStartPin'] == application_pin, 'CONTROLLED_VERIFICATION_CURRENT_ORIGINALS_REQUIRED')
        operation.journal.phase('INDEPENDENT_VERIFICATION_PASSED', [original_ref, verified['reportPin'], verified['postVerificationApprovalPin']])
        return Cutover(request, plan, target, policy, trust, operation.runner, operation.guard, operation.journal,
            operation.lock.fd, operation.request_pin, plan_pin=plan_pin, target_pin=target_pin,
            report_pin=verified['reportPin'], approval_pin=verified['postVerificationApprovalPin'],
            execution_context=operation.execution_context).run()
    finally:
        if old_context is None: os.environ.pop(CONTEXT_KEY, None)
        else: os.environ[CONTEXT_KEY] = old_context
