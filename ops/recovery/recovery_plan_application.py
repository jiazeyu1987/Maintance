"""Consume frozen startup results and W05's actual before/after protection."""
from datetime import datetime, timezone

from recovery_engine import check_pin, digest, pinned_json, require, validate_record

SCOPES = {'BUSINESS_DATABASE', 'BUSINESS_OBJECTS', 'BUSINESS_DERIVED', 'APPLICATION_MUTATIONS', 'SCHEDULERS', 'EXTERNAL_DISPATCH'}


def protected_application(application, execution_pin, plan, target, request, policy):
    validate_record(application, 'ApplicationStartResult', policy['recordSchemasPin'])
    execution = validate_record(pinned_json(execution_pin), 'RestoreExecutionResult', policy['recordSchemasPin'])
    config = pinned_json(request['sourceOrTargetRef']); environment_policy = pinned_json(request['policyPin'])
    require(application['state'] == execution['state'] == 'SUCCEEDED' and execution['writeProtectionState'] == 'ENFORCED' and
            application['operationId'] == execution['operationId'] == plan['operationId'] == request['operationId'] and
            application['restoreId'] == execution['restoreId'] == plan['restoreId'] and
            execution['recoveryPoint'] == plan['recoveryPoint'] and pinned_json(execution['planPin']) == plan and
            application['restoreResultPin'] == execution_pin and
            application['targetIdentityPin'] == execution['targetIdentityPin'] == target['targetIdentityPin'] and
            application['configurationPin'] == target['configurationPin'] == config['configurationPin'] and
            application['imagePins'] == config['imagePins'], 'APPLICATION_START_BINDING_INVALID')
    side = pinned_json(application['sideEffectIsolationPin'])
    require(side['schemaVersion'] == 'RecoverySideEffectIsolation/v1' and side['state'] == 'ENFORCED' and
            side['operationId'] == request['operationId'] and side['targetIdentityPin'] == target['targetIdentityPin'] and
            side['policyPin'] == request['policyPin'] and side['sourceWritesPerformed'] is False and
            side['writeProtectionState'] == 'ENFORCED' and
            side['startupInventoryPins'] == environment_policy['startupInventoryPins'] and
            side['applicationWriteProtectionPolicyPin'] == environment_policy['applicationWriteProtectionPin'],
            'APPLICATION_PROTECTED_START_REQUIRED')
    fresh(side, policy)
    spec = pinned_json(side['applicationWriteProtectionPolicyPin'])
    require(spec['schemaVersion'] == 'RecoveryApplicationWriteProtectionPolicy/v1' and
            spec['targetIdentityPin'] == target['targetIdentityPin'] and spec['configurationPin'] == config['configurationPin'] and
            spec['imagePins'] == config['imagePins'] and set(spec['requiredScopes']) == SCOPES and spec['sourceEvidencePins'],
            'APPLICATION_PROTECTION_POLICY_INVALID')
    for ref in spec['sourceEvidencePins']: check_pin(ref, content=False)
    containers = None
    for phase, field, executor in (('BEFORE_START', 'writeProtectionBeforePin', 'enforceScriptPin'),
                                    ('AFTER_START', 'writeProtectionAfterPin', 'observeScriptPin')):
        proof = pinned_json(side[field]); fresh(proof, policy)
        require(proof['schemaVersion'] == 'RecoveryApplicationWriteProtectionObservation/v1' and proof['phase'] == phase and
                proof['operationId'] == request['operationId'] and proof['restoreId'] == plan['restoreId'] and
                proof['targetIdentityPin'] == target['targetIdentityPin'] and proof['recoveryPoint'] == plan['recoveryPoint'] and
                proof['policyPin'] == side['applicationWriteProtectionPolicyPin'] and proof['state'] == 'ENFORCED' and
                proof['executorPin'] == spec[executor], 'APPLICATION_PROTECTION_OBSERVATION_UNBOUND')
        check_pin(proof['executorPin'], content=False)
        original = pinned_json(proof['originalInvocationPin'])
        # Both phases attempt writes to establish refusal, including AFTER_START.
        require(proof['originalInvocationPin'] in application['originalStartResultPins'] and
                original['schemaVersion'] == 'RecoveryEnvironmentInvocation/v1' and original['state'] == 'SUCCEEDED' and
                type(original['actualExitCode']) is int and original['actualExitCode'] == 0 and type(original['pid']) is int and
                original['pid'] > 0 and original['mutation'] is True and
                original['argvSha256'] == digest([config['pythonPin']['path'], '-I', spec[executor]['path']]) and
                type(original['stdoutBytes']) is int and original['stdoutBytes'] > 0 and
                type(original['stdoutSha256']) is str and len(original['stdoutSha256']) == 64 and
                datetime.fromisoformat(original['startedAt'].replace('Z', '+00:00')) <=
                datetime.fromisoformat(proof['observedAt'].replace('Z', '+00:00')) <=
                datetime.fromisoformat(original['finishedAt'].replace('Z', '+00:00')),
                'APPLICATION_PROTECTION_ORIGINAL_EXIT_REQUIRED')
        scopes = proof['scopeObservations']
        require(type(scopes) is list and len(scopes) == len(SCOPES) and {item['scope'] for item in scopes} == SCOPES,
                'APPLICATION_PROTECTION_COVERAGE_INCOMPLETE')
        require(type(proof['containers']) is dict and proof['containers'], 'APPLICATION_PROTECTION_CONTAINERS_REQUIRED')
        if containers is not None:
            require(all(proof['containers'].get(role) == identity for role, identity in containers.items()),
                    'APPLICATION_PROTECTION_DEPENDENCY_CHANGED')
        containers = proof['containers']
        for item in scopes:
            require(type(item['beforeFingerprint']) is str and len(item['beforeFingerprint']) == 64 and
                    set(item['beforeFingerprint']) <= set('0123456789abcdef') and
                    item['beforeFingerprint'] == item['afterFingerprint'] and item['rejectionObservationPins'],
                    'APPLICATION_PROTECTION_REFUSAL_REQUIRED')
            check_pin(item['enforcementPin'], content=False)
            for ref in item['rejectionObservationPins']:
                refusal = pinned_json(ref)
                require(refusal['schemaVersion'] == 'RecoveryApplicationWriteRefusal/v1' and refusal['scope'] == item['scope'] and
                        refusal['phase'] == phase and refusal['denied'] is True and refusal['operationId'] == request['operationId'] and
                        refusal['targetIdentityPin'] == target['targetIdentityPin'] and refusal['recoveryPoint'] == plan['recoveryPoint'] and
                        refusal['containers'] == proof['containers'] and refusal['beforeFingerprint'] == item['beforeFingerprint'] ==
                        refusal['afterFingerprint'] and refusal['originalInvocationPins'], 'APPLICATION_PROTECTION_REFUSAL_UNBOUND')
                for original_ref in refusal['originalInvocationPins']:
                    invocation = pinned_json(original_ref)
                    require(invocation['schemaVersion'] == 'RecoveryEnvironmentInvocation/v1' and
                            invocation['mutation'] is True and type(invocation['actualExitCode']) is int and
                            invocation['state'] in ('SUCCEEDED', 'FAILED_RETAINED') and
                            type(invocation['pid']) is int and invocation['pid'] > 0 and
                            datetime.fromisoformat(original['startedAt'].replace('Z', '+00:00')) <=
                            datetime.fromisoformat(invocation['startedAt'].replace('Z', '+00:00')) <=
                            datetime.fromisoformat(invocation['finishedAt'].replace('Z', '+00:00')) <=
                            datetime.fromisoformat(original['finishedAt'].replace('Z', '+00:00')),
                            'APPLICATION_PROTECTION_REFUSAL_TERMINATION_UNPROVEN')
    for ref in application['originalStartResultPins']: check_pin(ref, content=False)
    health = pinned_json(application['healthEvidencePin'])
    require(health['schemaVersion'] == 'RecoveryApplicationHealth/v1' and health['state'] == 'SUCCEEDED' and
            health['operationId'] == request['operationId'] and health['restoreId'] == plan['restoreId'] and
            health['targetIdentityPin'] == target['targetIdentityPin'], 'APPLICATION_HEALTH_UNBOUND')
    fresh(health, policy); return side


def fresh(record, policy):
    observed = datetime.fromisoformat(record['observedAt'].replace('Z', '+00:00'))
    require(0 <= (datetime.now(timezone.utc)-observed).total_seconds() <= policy['maximumProofAgeSeconds'],
            'APPLICATION_PROTECTION_PROOF_STALE')
