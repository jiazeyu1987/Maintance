"""Internal, pinned source-fence handoff without changing the frozen request."""
import os

from recovery_engine import canonical, check_pin, current_window, parse, pinned_json, require, write

CONTEXT_KEY = 'RECOVERY_CONTROLLED_FENCE_HANDOFF_PIN'


def fence_handoff(request, policy):
    raw = os.environ.get(CONTEXT_KEY)
    require(raw is not None, 'CONTROLLED_FENCE_HANDOFF_REQUIRED')
    ref = parse(raw.encode('utf-8')); value = pinned_json(ref)
    require(set(value) == {'schemaVersion', 'operationId', 'originalRequestPin', 'planPin', 'targetIdentityPin',
                           'sourceScopePin', 'selectedPointPin', 'leaseRef', 'sourceFencePin', 'sourceFencePointEvidencePin'} and
            value['schemaVersion'] == 'RecoveryControlledFenceHandoff/v1' and
            value['operationId'] == request['operationId'] and value['sourceScopePin'] == policy['sourceScopePin'] and
            value['selectedPointPin'] == request['selectedPointPin'] and value['leaseRef'] == request['leaseRef'] and
            value['targetIdentityPin'] == pinned_json(policy['dataTargetPin'])['targetIdentityPin'],
            'CONTROLLED_FENCE_HANDOFF_BINDING_INVALID')
    original = pinned_json(value['originalRequestPin']); plan = pinned_json(value['planPin'])
    require(original['action'] == 'CONTROLLED_CUTOVER' and original['mode'] == request['mode'] == 'CONTROLLED_RESTORE' and
            all(original[key] == request[key] for key in ('operationId', 'selectedPointPin', 'sourceOrTargetRef', 'policyPin',
                                                        'authorizationRefs', 'leaseRef')) and
            plan['candidatePin'] == request['selectedPointPin'] and plan['operationId'] == request['operationId'] and
            plan['targetRef'] == request['sourceOrTargetRef'], 'CONTROLLED_FENCE_ORIGINAL_REQUEST_INVALID')
    point = pinned_json(value['sourceFencePointEvidencePin']); fence = pinned_json(value['sourceFencePin'])
    require(point['sourceFencePin'] == value['sourceFencePin'] and point['selectedPointPin'] == value['selectedPointPin'] and
            point['sourceScopePin'] == value['sourceScopePin'] and point['databaseAndObjectsUnchanged'] is True,
            'CONTROLLED_FENCE_POINT_BINDING_INVALID')
    from recovery_plan_objects import repository_binding
    _, binding = repository_binding(request['selectedPointPin'], pinned_json(request['selectedPointPin']), policy)
    material = pinned_json(binding['recoveryMaterialPin'])
    require(point['observationPins'], 'SOURCE_FENCE_OBSERVATION_ORIGINALS_REQUIRED')
    for ref in point['observationPins']:
        observation = pinned_json(ref)
        require(observation['schemaVersion'] == 'RecoveryCutoverObservation/v1' and observation['state'] == 'OBSERVED' and
                observation['action'] == 'OBSERVE_SOURCE_FENCE' and observation['operationId'] == request['operationId'] and
                observation['targetIdentityPin'] == value['targetIdentityPin'] and observation['sourceScopePin'] == value['sourceScopePin'] and
                observation['recoveryPoint'] == plan['recoveryPoint'], 'SOURCE_FENCE_OBSERVATION_UNBOUND')
        current_window(observation)
    observations = {}
    for ref in point['observationPins']:
        for key, observed in pinned_json(ref)['observations'].items():
            require(key not in observations or observations[key] == observed, 'SOURCE_FENCE_OBSERVATION_CONFLICT')
            observations[key] = observed
    require(observations['retainedSourceResources'] is True and
            observations['writerCoverage'] == fence['writerCoverage'] and
            observations['currentSourceRecoveryPoint'] == plan['recoveryPoint'] and
            observations['currentSourceDatabasePosition'] == material['database']['endPosition'] and
            observations['sourceDataAndObjectsUnchangedSincePoint'] is True, 'SOURCE_FENCE_POINT_NOT_ACTUALLY_OBSERVED')
    # Validate the worker's actual native command originals again at every
    # consumer boundary, including signed remote PID/start/wait evidence.
    from recovery_cutover_terminal import verified_step_terminal
    for action in ('STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE'):
        command_refs = [ref for ref in fence['originalInvocationPins']
                        if pinned_json(ref).get('schemaVersion') == 'RecoveryCutoverInvocation/v1' and
                        pinned_json(ref)['action'] == action]
        require(command_refs, 'CONTROLLED_FENCE_NATIVE_ORIGINALS_MISSING')
        child = dict(operationId=request['operationId'], action=action, targetIdentityPin=value['targetIdentityPin'],
                     sourceScopePin=value['sourceScopePin'])
        verified_step_terminal({'data': {'originalInvocationPins': command_refs, 'recoveryPoint': plan['recoveryPoint']}}, child, policy)
    current_window(point)
    current_window({'validFrom': fence['observedAt'], 'validUntil': fence['expiresAt']})
    return value


def establish_fence(cutover, original_request_pin):
    stop, stop_ref = cutover.execute('STOP_SOURCE_WRITES', {})
    observed, observed_ref = cutover.execute('OBSERVE_SOURCE_FENCE', {'stopWrites': stop_ref})
    current_window(observed)
    source = pinned_json(cutover.policy['sourceScopePin'])
    # Include verified remote terminal originals, without interpreting client
    # exits with unknown remote state as evidence of remote termination.
    originals = []
    for ref in cutover.runner.original_pins:
        if os.path.basename(ref['path']) in ('intent.json', 'request.json', 'exit.json'):
            originals.append(ref)
    originals += stop['originalInvocationPins'] + observed['originalInvocationPins']
    require(originals and observed['observationPins'], 'SOURCE_FENCE_NATIVE_ORIGINALS_REQUIRED')
    from datetime import datetime
    from recovery_engine import utc
    established_at = utc()
    require(datetime.fromisoformat(observed['validFrom'].replace('Z', '+00:00')) <=
            datetime.fromisoformat(established_at.replace('Z', '+00:00')) <
            datetime.fromisoformat(observed['validUntil'].replace('Z', '+00:00')), 'SOURCE_FENCE_OBSERVATION_WINDOW_INVALID')
    fence_pin = write(cutover.runner.root/'source-fence.json', dict(schemaVersion='RecoverySourceFence/v1',
        operationId=cutover.request['operationId'], sourceIdentityPin=source['sourceIdentityPin'], state='ENFORCED',
        writerCoverage=observed['writerCoverage'], leaseRef=cutover.request['leaseRef'], observedAt=established_at,
        expiresAt=observed['validUntil'], originalInvocationPins=originals, retainedSourceResources=True))
    point_pin = write(cutover.runner.root/'source-fence-point.json', dict(schemaVersion='RecoverySourceFencePoint/v1',
        sourceFencePin=fence_pin, sourceScopePin=cutover.policy['sourceScopePin'], selectedPointPin=cutover.plan['candidatePin'],
        databaseAndObjectsUnchanged=True, observationPins=observed['observationPins'],
        validFrom=observed['validFrom'], validUntil=observed['validUntil']))
    ref = write(cutover.runner.root/'controlled-fence-handoff.json', dict(schemaVersion='RecoveryControlledFenceHandoff/v1',
        operationId=cutover.request['operationId'], originalRequestPin=original_request_pin, planPin=cutover.plan_pin,
        targetIdentityPin=cutover.target['targetIdentityPin'], sourceScopePin=cutover.policy['sourceScopePin'],
        selectedPointPin=cutover.plan['candidatePin'], leaseRef=cutover.request['leaseRef'], sourceFencePin=fence_pin,
        sourceFencePointEvidencePin=point_pin))
    return ref
