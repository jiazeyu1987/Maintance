"""Execute trusted native cutover recipes once and retain their real exits.

Site-specific routing and writer controls are provisioned commands with hashed
tools, fixed argv and independently approved observation requirements. Missing
recipes are hard failures; no shell, retries or inferred successful probes.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import signal
from pathlib import Path

from recovery_engine import (Budget, RecoveryError, authorities, canonical, check_pin, current_window,
    digest, load, parse, pinned_json, require, utc, write, persist_evidence, repository_guard)
from recovery_engine_read_guard import inherit_read_guard
from recovery_engine_state import inherited_target_lock
from recovery_plan import immutable_inputs, prepared_target, resolve_chain, trusted_configuration, verify_report
from recovery_cutover_terminal import remote_terminal


ACTIONS = {'VERIFY_TARGET_PROTECTION', 'STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE', 'SWITCH_TARGET',
           'RELEASE_TARGET_WRITES', 'ESTABLISH_NEW_GENERATION', 'PROTECT_TARGET'}


def run(request, root, pins):
    budget = Budget(request['deadlineMilliseconds'])
    require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
    original = pinned_json(request['originalRequestPin'])
    trust, policy, config = trusted_configuration(original)
    identity = pinned_json(policy['dataTargetPin'])['targetIdentityPin']
    authorities(original, identity, ['CONTROLLED_CUTOVER', request['action']], trust)
    inherit_read_guard(original, request['originalRequestPin'], policy, budget)
    plan = pinned_json(request['planPin'])
    source_phase = request['phase'] == 'SOURCE_FENCE'
    require(request['phase'] in ('SOURCE_FENCE', 'TARGET_CUTOVER') and
            (not source_phase or request['action'] in ('STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE')),
            'CUTOVER_WORKER_PHASE_INVALID')
    target = {'targetIdentityPin': pinned_json(policy['dataTargetPin'])['targetIdentityPin']} if source_phase else pinned_json(request['recoveryTargetPin'])
    chain = resolve_chain(original['selectedPointPin'], policy)
    require(request['action'] in ACTIONS and original['action'] == 'CONTROLLED_CUTOVER' and
            request['mode'] == original['mode'] == 'CONTROLLED_RESTORE' and
            request['operationId'] == original['operationId'] == plan['operationId'] and
            request['targetIdentityPin'] == target['targetIdentityPin'] == plan['plannedWrites'][0]['targetIdentityPin'] and
            (not source_phase or request['reportPin'] == original['inputPins']['recoveryVerificationReport']) and
            request['sourceScopePin'] == policy['sourceScopePin'] and
            plan['candidatePin'] == original['selectedPointPin'] == original['inputPins']['repositoryPoint'] and
            plan['orderedChainPins'] == [step[0] for step in chain] and
            plan['immutableInputsSha256'] == digest(immutable_inputs(original, policy, chain)) and
            plan['targetRef'] == original['sourceOrTargetRef'] and
            (not source_phase or request['recoveryTargetPin'] is None) and
            request['authorizationRefs'] == original['authorizationRefs'] and request['leaseRef'] == original['leaseRef'],
            'CUTOVER_WORKER_BINDING_INVALID')
    recipe_pin = policy['cutoverRecipePins'][request['action']]
    require(recipe_pin['sha256'] in trust['cutoverRecipeSha256s'], 'CUTOVER_RECIPE_NOT_INDEPENDENTLY_TRUSTED')
    recipe = pinned_json(recipe_pin)
    require(recipe['schemaVersion'] == 'RecoveryCutoverRecipe/v1' and recipe['action'] == request['action'] and
            recipe['targetIdentityPin'] == request['targetIdentityPin'] and recipe['sourceScopePin'] == request['sourceScopePin'] and
            recipe['recoveryPoint'] == plan['recoveryPoint'] and recipe['commands'], 'CUTOVER_RECIPE_SCOPE_INVALID')

    def guard():
        repository_guard().check()
        budget.remaining(); check_pin(request['originalRequestPin']); check_pin(recipe_pin)
        require(trusted_configuration(original) == (trust, policy, config), 'CUTOVER_TRUST_DRIFT')
        inherited_target_lock(policy, target['targetIdentityPin'])
        authorities(original, target['targetIdentityPin'], ['CONTROLLED_CUTOVER', request['action']], trust)
        current_window(recipe)
        if not source_phase:
            prepared_target(dict(original, inputPins={'recoveryTarget': request['recoveryTargetPin']}), plan, policy, trust)
        if request['action'] != 'PROTECT_TARGET':
            verify_report(request['reportPin'], plan, policy, trust, require_execution=not source_phase,
                          approval_pin=request['postVerificationApprovalPin'])
        for ref in request['inputPins'].values(): check_pin(ref)

    observations = []; last_exit = None
    for index, command in enumerate(recipe['commands']):
        guard(); check_pin(command['toolPin'], content=False)
        require(command['toolPin']['sha256'] in trust['cutoverToolSha256s'] and
                type(command['argv']) is list and all(type(value) is str and '\0' not in value for value in command['argv']) and
                type(command['mutation']) is bool and command['executionKind'] in ('LOCAL', 'REMOTE'), 'CUTOVER_COMMAND_NOT_APPROVED')
        check_pin(command['executionHostIdentityPin'])
        host = pinned_json(command['executionHostIdentityPin'])
        if command['executionKind'] == 'LOCAL':
            require(host['machineId'] == pinned_json(target['targetIdentityPin'])['machineId'], 'LOCAL_EXECUTION_HOST_MISMATCH')
        if request['action'] in ('STOP_SOURCE_WRITES', 'OBSERVE_SOURCE_FENCE'):
            source = pinned_json(request['sourceScopePin'])
            require(host['machineId'] == source['machineId'] and
                    (source['machineId'] == pinned_json(target['targetIdentityPin'])['machineId'] or command['executionKind'] == 'REMOTE'),
                    'SOURCE_FENCE_EXECUTION_HOST_MISMATCH')
        command_intent_pin = write(root/('command-%03d-intent.json' % index), dict(schemaVersion='RecoveryCutoverCommandIntent/v1',
            operationId=request['operationId'], action=request['action'], targetIdentityPin=target['targetIdentityPin'],
            sourceScopePin=request['sourceScopePin'], recoveryPoint=plan['recoveryPoint'], recipePin=recipe_pin,
            toolPin=command['toolPin'], argvSha256=digest(command['argv']), configurationPin=command['configurationPin'],
            executionKind=command['executionKind'], executionHostIdentityPin=command['executionHostIdentityPin'], startedAt=utc()))
        pins.append(command_intent_pin)
        # Operation binding is transmitted as non-secret structured stdin.
        # The approved tool must reject mismatching target/source identities.
        stdin = canonical(dict(schemaVersion='RecoveryCutoverCommandInput/v1', operationId=request['operationId'],
            action=request['action'], targetIdentityPin=request['targetIdentityPin'], sourceScopePin=request['sourceScopePin'],
            recoveryPoint=plan['recoveryPoint'], inputPins=request['inputPins'], commandConfigPin=command['configurationPin'],
            commandIntentPin=command_intent_pin, executionHostIdentityPin=command['executionHostIdentityPin']))
        check_pin(command['configurationPin'])
        intent_path = root/('command-%03d.json' % index)
        intent = dict(schemaVersion='RecoveryCutoverInvocation/v1', operationId=request['operationId'],
            action=request['action'], toolPin=command['toolPin'], configurationPin=command['configurationPin'],
            argvSha256=digest(command['argv']), startedAt=utc(), actualExitCode=None, state='TERMINAL_UNKNOWN', nativePid=None,
            commandIntentPin=command_intent_pin, executionKind=command['executionKind'],
            executionHostIdentityPin=command['executionHostIdentityPin'], remoteTerminalProofPin=None)
        write(intent_path, intent)
        process = None; raw = stderr = b''
        try:
            timeout = budget.remaining()
            options = repository_guard().child_options(
                {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
                (inherited_target_lock(policy, target['targetIdentityPin']),))
            process = subprocess.Popen([command['toolPin']['path'], *command['argv']], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                **options)
            intent['nativePid'] = process.pid; write(intent_path, intent)
            try:
                raw, stderr = process.communicate(stdin, timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                try: raw, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired: raise RecoveryError('CUTOVER_TOOL_TERMINAL_UNKNOWN', unknown=True) from None
                raise RecoveryError('CUTOVER_TOOL_TIMEOUT', unknown=command['mutation'], exit_code=process.returncode) from None
            last_exit = process.returncode
            require(last_exit == 0 and not stderr and len(raw) <= 1024*1024, 'CUTOVER_TOOL_FAILED')
            value = parse(raw)
            require(value['schemaVersion'] == 'RecoveryCutoverObservation/v1' and value['state'] == 'OBSERVED' and
                    value['operationId'] == request['operationId'] and value['action'] == request['action'] and
                    value['targetIdentityPin'] == target['targetIdentityPin'] and value['sourceScopePin'] == request['sourceScopePin'] and
                    value['recoveryPoint'] == plan['recoveryPoint'], 'CUTOVER_OBSERVATION_BINDING_INVALID')
            current_window(value)
            if command['executionKind'] == 'REMOTE':
                expected = {key: request[key] for key in ('operationId', 'action', 'targetIdentityPin', 'sourceScopePin')}
                expected.update(recoveryPoint=plan['recoveryPoint'], executionHostIdentityPin=command['executionHostIdentityPin'])
                pins.extend(remote_terminal(value['remoteTerminalProofPin'], command_intent_pin, expected, policy))
                intent['remoteTerminalProofPin'] = value['remoteTerminalProofPin']
            else:
                require(value['remoteTerminalProofPin'] is None, 'LOCAL_COMMAND_REMOTE_PROOF_REJECTED')
            require(command['requiredObservations'] and all(type(value['observations'].get(key)) is type(expected) and
                    value['observations'].get(key) == expected for key, expected in command['requiredObservations'].items()),
                    'CUTOVER_POSTCONDITION_NOT_OBSERVED')
            proof = write(root/('observation-%03d.json' % index), value); observations.append(proof)
            intent['state'] = 'SUCCEEDED'; guard()
        except Exception as error:
            error.exit_code = None if process is None else process.poll()
            if process is not None and process.poll() is None: error.unknown = True
            if (command['mutation'] or command['executionKind'] == 'REMOTE') and intent['state'] != 'SUCCEEDED': error.unknown = True
            raise
        finally:
            intent.update(finishedAt=utc(), actualExitCode=None if process is None else process.poll(),
                          stdoutSha256=hashlib.sha256(raw).hexdigest(), stdoutBytes=len(raw),
                          stderrSha256=hashlib.sha256(stderr).hexdigest(), stderrBytes=len(stderr))
            persist_evidence(intent_path, intent, pins,
                unknown=process is not None and (command['mutation'] or command['executionKind'] == 'REMOTE' or process.poll() is None),
                exit_code=intent['actualExitCode'])
    values = {}
    for ref in observations:
        for name, value in pinned_json(ref)['observations'].items():
            require(name not in values or values[name] == value, 'CUTOVER_OBSERVATIONS_CONFLICT')
            values[name] = value
    require(set(recipe['resultFields']) <= set(values), 'CUTOVER_RESULT_FIELD_NOT_OBSERVED')
    result = dict(schemaVersion='RecoveryCutoverStep/v1', operationId=request['operationId'], action=request['action'],
        targetIdentityPin=target['targetIdentityPin'], sourceScopePin=request['sourceScopePin'], recoveryPoint=plan['recoveryPoint'],
        state='VERIFIED', originalInvocationPins=pins, observationPins=observations,
        validFrom=recipe['validFrom'], validUntil=recipe['validUntil'], **{key: values[key] for key in recipe['resultFields']})
    return result, last_exit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv); request = load(args.request); started = utc(); pins = []; actual = None
    try:
        data, actual = run(request, Path(args.output).absolute().parent, pins)
        state = 'SUCCEEDED'; failure = None
    except Exception as error:
        state = 'TERMINAL_UNKNOWN' if getattr(error, 'unknown', False) else 'FAILED_RETAINED'
        failure = getattr(error, 'code', 'CUTOVER_'+type(error).__name__.upper()); data = None
        actual = getattr(error, 'exit_code', None)
    result = dict(schemaVersion='RecoveryCutoverWorkerResult/v1', operationId=request['operationId'],
        requestId=request['requestId'], action=request['action'], state=state, failureCode=failure, data=data,
        originalResultPins=pins, actualExitCode=actual, startedAt=started, finishedAt=utc())
    try:
        persist_evidence(args.output, result, pins, unknown=state == 'TERMINAL_UNKNOWN', exit_code=actual)
    except RecoveryError as recording:
        print(recording.code)
        return 2 if recording.unknown else 1
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[state]


if __name__ == '__main__': raise SystemExit(main())
