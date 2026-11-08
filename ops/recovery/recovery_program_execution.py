"""Prove an operation's private program view without changing its original owner.

Only a fresh READY start and that operation's REPLACING phase are supported.
Retained failure authorization and retry contexts require a separate contract.
"""
from copy import deepcopy
import os
from pathlib import Path
import stat

from recovery_engine import RecoveryError, absolute, digest, require
from recovery_backup_epoch import _assert_lock, _read_file, read_current
from recovery_minimal_plan import request_contract
from recovery_program_activation import CONTEXT_FIELDS, _claim, _exclusive, _reader
from recovery_program_generation import (GENERATION_FIELDS, document, validate_policy,
    _resolve_at_ready, _target_transition, _capture_transition)

BINDING_FIELDS = {'schemaVersion', 'operationId', 'targetConfigRef', 'policySha256',
                  'configurationPin', 'requestPin', 'reservationPin', 'contextPin'}
MAX_BYTES = 4*1024*1024


def _directory(path, code):
    path = absolute(str(path))
    require(path.is_dir(), code)
    info = path.stat()
    require(stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.geteuid(), code)
    return info.st_dev, info.st_ino


def _inputs(owner, request, operation_root, lock_fd, guard):
    guard()
    request_contract(request)
    require(request['action'] == 'RESTORE' and request['targetConfigRef'] is not None and
            request['recoveryPointRef'] is not None, 'PROGRAM_EXECUTION_REQUEST_INVALID')
    root = absolute(str(operation_root))
    require(root == absolute(owner['operationsRoot'])/request['operationId'],
            'PROGRAM_EXECUTION_ROOT_INVALID')
    root_identity = _directory(root, 'PROGRAM_EXECUTION_ROOT_INVALID')
    observed = []
    tracked, unchanged = _reader(document, guard)
    def read(reference):
        result = tracked(reference)
        if reference not in observed: observed.append(deepcopy(reference))
        return result
    def fixed(path):
        guard()
        _, reference = _read_file(path, MAX_BYTES)
        return read(reference), reference
    original, configuration_pin = fixed(root/'configuration.json')
    require(original == owner, 'PROGRAM_EXECUTION_OWNER_CHANGED')
    original_request, request_pin = fixed(root/'request.json')
    require(original_request == request, 'PROGRAM_EXECUTION_REQUEST_CHANGED')
    target_ref = request['targetConfigRef']
    policies, targets = owner.get('targetProgramPolicies'), owner.get('targets')
    require(type(policies) is dict and type(targets) is dict and
            set(policies) <= set(targets) and target_ref in policies,
            'PROGRAM_EXECUTION_POLICY_REQUIRED')
    policy = policies[target_ref]
    validate_policy(policy)
    require(policy['targetConfigRef'] == target_ref, 'PROGRAM_TARGET_POLICY_BINDING_INVALID')
    target = targets[target_ref]
    require(type(target) is dict and 'mainApplication' in target, 'PROGRAM_TARGET_MAIN_REQUIRED')
    epochs = owner.get('targetBackupEpochPolicies')
    require(type(epochs) is dict and epochs.get(target_ref) == policy['backupEpochPolicy'],
            'PROGRAM_TARGET_EPOCH_BINDING_INVALID')
    require(target['replacement'].get('backupEpoch', policy['backupEpochPolicy']) == policy['backupEpochPolicy'],
            'PROGRAM_TARGET_EPOCH_BINDING_INVALID')
    _assert_lock(policy['backupEpochPolicy'], lock_fd)
    claim, baseline = _claim(policy, request['operationId'], read)
    require(baseline == target, 'PROGRAM_TARGET_BASELINE_CHANGED')
    claim_identity = _directory(claim, 'PROGRAM_CLAIM_INVALID')
    reservation, reservation_pin = fixed(root/'resource-reservation.json')
    require(reservation.get('schemaVersion') == 'RestoreHostReservation/v1',
            'PROGRAM_EXECUTION_RESERVATION_INVALID')
    from recovery_resource_admission import verify_reservation
    require(verify_reservation(owner, request, root) == reservation_pin,
            'PROGRAM_EXECUTION_RESERVATION_CHANGED')
    def held():
        guard()
        _assert_lock(policy['backupEpochPolicy'], lock_fd)
        require(_directory(root, 'PROGRAM_EXECUTION_ROOT_INVALID') == root_identity and
                _directory(claim, 'PROGRAM_CLAIM_INVALID') == claim_identity,
                'PROGRAM_EXECUTION_DIRECTORY_CHANGED')
        unchanged()
        require(document(configuration_pin) == owner and document(request_pin) == request,
                'PROGRAM_EXECUTION_ORIGINAL_CHANGED')
        require(verify_reservation(owner, request, root) == reservation_pin,
                'PROGRAM_EXECUTION_RESERVATION_CHANGED')
        guard()
    return dict(root=root, claim=claim, policy=policy, baseline=baseline, read=read, held=held,
        evidence=observed, configurationPin=configuration_pin, requestPin=request_pin,
        reservationPin=reservation_pin)


def _context(inputs, request, context_pin, lock_fd, guard, *, ready_only=False):
    read, policy, claim = inputs['read'], inputs['policy'], inputs['claim']
    require(Path(context_pin['path']) == claim/'program-context.json', 'PROGRAM_RESTORE_CONTEXT_INVALID')
    context = read(context_pin)
    require(type(context) is dict and set(context) == CONTEXT_FIELDS and
            context['schemaVersion'] == 'MainProgramRestoreContext/v1' and
            context['operationId'] == request['operationId'] and
            context['policySha256'] == digest(policy) and type(context['readyEpoch']) is dict and
            type(context['evidencePins']) is list, 'PROGRAM_RESTORE_CONTEXT_INVALID')
    current = read_current(policy['backupEpochPolicy'], guard=guard)
    ready_pin = context['readyEpoch']['eventPin']
    historical = _resolve_at_ready(policy, ready_pin, read, guard)
    require(context['readyEpoch'] == historical['epoch'] and
            context['targetPin'] == historical['targetPin'] and
            context['parentGenerationPin'] == historical['generationPin'] and
            context['capturePins'] == historical['captures'], 'PROGRAM_RESTORE_CONTEXT_INVALID')
    # Historical lookup also observes the current tail. The snapshot's proof
    # set is the exact READY prefix; ordering is not an identity convention.
    expected = [p for p in historical['evidence']
                if p != current['eventPin'] or p == ready_pin]
    require(len(context['evidencePins']) == len(expected) and
            all(p in context['evidencePins'] for p in expected), 'PROGRAM_RESTORE_CONTEXT_INVALID')
    for reference in context['evidencePins']: read(reference)
    if current['state'] == 'READY':
        require(current == context['readyEpoch'], 'PROGRAM_RESTORE_EPOCH_CHANGED')
    else:
        require(not ready_only and current['state'] == 'REPLACING' and
                current['operationId'] == request['operationId'], 'PROGRAM_RESTORE_EPOCH_CHANGED')
        event, ready = read(current['eventPin']), read(ready_pin)
        require(event['kind'] == 'RESTORE_STARTED' and event['previousSha256'] == ready_pin['sha256'] and
                event['sequence'] == ready['sequence']+1, 'PROGRAM_RESTORE_EPOCH_CHANGED')
        intent = read(event['evidencePin'])
        require(intent['operationId'] == request['operationId'] and
                intent['targetConfigRef'] == request['targetConfigRef'] and
                intent['databaseUuid'] == policy['backupEpochPolicy']['databaseUuid'] and
                Path(intent['replacementReceiptPath']) == claim/'replacement-result.json',
                'PROGRAM_RESTORE_CONTEXT_INVALID')
    def held():
        inputs['held']()
        require(read_current(policy['backupEpochPolicy'], guard=guard) == current,
                'PROGRAM_RESTORE_EPOCH_CHANGED')
        _assert_lock(policy['backupEpochPolicy'], lock_fd)
        guard()
    held()
    return context, historical, current, held


def bind_execution(owner, request, operation_root, context_pin, lock_fd, guard=None):
    """Exclusively bind the original reservation to a real READY snapshot."""
    guard = (lambda: None) if guard is None else guard
    try:
        inputs = _inputs(owner, request, operation_root, lock_fd, guard)
        _, _, _, held = _context(inputs, request, context_pin, lock_fd, guard, ready_only=True)
        require(not os.path.lexists(inputs['claim']/'generation.json'),
                'PROGRAM_EXECUTION_GENERATION_UNEXPECTED')
        value = dict(schemaVersion='MainProgramExecutionBinding/v1', operationId=request['operationId'],
            targetConfigRef=request['targetConfigRef'], policySha256=digest(inputs['policy']),
            configurationPin=inputs['configurationPin'], requestPin=inputs['requestPin'],
            reservationPin=inputs['reservationPin'], contextPin=deepcopy(context_pin))
        return _exclusive(inputs['claim']/'program-execution-binding.json', value, held)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise RecoveryError('PROGRAM_EXECUTION_FORMAT_INVALID') from error


def resolve_execution_configuration(owner, request, operation_root, *, binding_pin,
                                    generation_pin=None, lock_fd, guard=None, runtime=False):
    """Return a fully proven private owner; never publish or reconcile an epoch."""
    guard = (lambda: None) if guard is None else guard
    try:
        require(type(runtime) is bool, 'PROGRAM_EXECUTION_RUNTIME_INVALID')
        inputs = _inputs(owner, request, operation_root, lock_fd, guard)
        read, policy, claim = inputs['read'], inputs['policy'], inputs['claim']
        require(Path(binding_pin['path']) == claim/'program-execution-binding.json',
                'PROGRAM_EXECUTION_BINDING_INVALID')
        binding = read(binding_pin)
        require(type(binding) is dict and set(binding) == BINDING_FIELDS and
                binding['schemaVersion'] == 'MainProgramExecutionBinding/v1' and
                binding['operationId'] == request['operationId'] and
                binding['targetConfigRef'] == request['targetConfigRef'] and
                binding['policySha256'] == digest(policy) and
                all(binding[k] == inputs[k] for k in ('configurationPin','requestPin','reservationPin')),
                'PROGRAM_EXECUTION_BINDING_INVALID')
        context, historical, current, held = _context(inputs, request, binding['contextPin'], lock_fd, guard)
        target, target_pin, captures = historical['target'], historical['targetPin'], historical['captures']
        if generation_pin is None:
            require(not os.path.lexists(claim/'generation.json'), 'PROGRAM_EXECUTION_GENERATION_REQUIRED')
        else:
            require(current['state'] == 'REPLACING' and Path(generation_pin['path']) == claim/'generation.json',
                    'PROGRAM_EXECUTION_GENERATION_INVALID')
            generation = read(generation_pin)
            require(type(generation) is dict and set(generation) == GENERATION_FIELDS and
                    generation['schemaVersion'] == 'MainProgramGeneration/v1' and
                    generation['operationId'] == request['operationId'] and generation['epochId'] == current['epochId'] and
                    generation['targetConfigRef'] == request['targetConfigRef'] and
                    generation['policySha256'] == digest(policy) and
                    generation['baselineTargetPin'] == policy['baselineTargetPin'] and
                    generation['parentGenerationPin'] == context['parentGenerationPin'],
                    'PROGRAM_GENERATION_BINDING_INVALID')
            target_pin = generation['targetPin']; target = read(target_pin)
            _target_transition(historical['target'], target, generation['switchResultPin'], request['operationId'], read)
            require(type(generation['captureBindings']) is dict and
                    set(generation['captureBindings']) == set(policy['captureConfigurationPins']),
                    'PROGRAM_CAPTURE_BINDINGS_INVALID')
            captures = {}
            for source_ref, base_pin in policy['captureConfigurationPins'].items():
                entry = generation['captureBindings'][source_ref]
                require(type(entry) is dict and set(entry) == {'baseCapturePin','capturePin'} and
                        entry['baseCapturePin'] == base_pin, 'PROGRAM_CAPTURE_BASE_CHANGED')
                _capture_transition(read(base_pin), read(entry['capturePin']), inputs['baseline'],
                    target, source_ref, policy['backupEpochPolicy'], read)
                captures[source_ref] = entry['capturePin']
        effective = deepcopy(owner)
        effective['targets'][request['targetConfigRef']] = deepcopy(target)
        if runtime:
            runtime_path = claim/'runtime'
            _directory(runtime_path, 'PROGRAM_EXECUTION_RUNTIME_INVALID')
            effective['targets'][request['targetConfigRef']]['dataRoot'] = str(runtime_path)
        held()
        return effective, dict(bindingPin=deepcopy(binding_pin), contextPin=binding['contextPin'],
            generationPin=deepcopy(generation_pin), targetPin=target_pin, capturePins=captures,
            reservationPin=inputs['reservationPin'], epoch=current, evidencePins=deepcopy(inputs['evidence']))
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise RecoveryError('PROGRAM_EXECUTION_FORMAT_INVALID') from error
