"""Stage immutable MAIN program generations under the real physical source lock.

Staging does not publish READY. Only the complete restore's original successful
receipt and its existing epoch transition can activate these configurations.
Partial evidence is retained and never overwritten or replayed.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import stat

from recovery_engine import canonical, digest, require
from recovery_backup_epoch import _assert_lock, _snapshot, read_current
from recovery_program_generation import (document, validate_policy, _pin, _resolve,
    _target_transition, _capture_transition)

CONTEXT_FIELDS = {'schemaVersion', 'policySha256', 'operationId', 'readyEpoch',
                  'targetPin', 'parentGenerationPin', 'capturePins', 'evidencePins'}
MAX_BYTES = 4*1024*1024


def _operation(value):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value),
            'PROGRAM_OPERATION_INVALID')
    return value


def _reader(reader, guard):
    seen = {}
    def read(reference):
        guard(); _pin(reference)
        key = reference['path']
        require(key not in seen or seen[key] == reference, 'PROGRAM_DOCUMENT_PIN_CONFLICT')
        value = reader(reference)
        seen[key] = deepcopy(reference)
        guard()
        return value
    def unchanged():
        for reference in seen.values():
            guard(); document(reference); guard()
    return read, unchanged


def _claim(policy, operation, read):
    baseline = read(policy['baselineTargetPin'])
    path = Path(baseline['replacement']['stateRoot'])/_operation(operation)
    require(path.is_absolute() and path.resolve(strict=True) == path,
            'PROGRAM_CLAIM_INVALID')
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700 and
            info.st_uid == os.geteuid(), 'PROGRAM_CLAIM_INVALID')
    return path, baseline


def _exclusive(path, value, held):
    held()
    require(not os.path.lexists(path), 'PROGRAM_METADATA_ALREADY_EXISTS')
    raw = canonical(value)
    require(0 < len(raw) <= MAX_BYTES, 'PROGRAM_DOCUMENT_PIN_INVALID')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        require(False, 'PROGRAM_METADATA_ALREADY_EXISTS')
    # A crash leaves the exclusively created file as evidence and blocks replay.
    with os.fdopen(fd, 'wb') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    held()
    reference = dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    require(document(reference) == value, 'PROGRAM_DOCUMENT_CHANGED')
    return reference


def snapshot_restore(policy, operation_id, lock_fd, *, reader=document, guard=None, owner=None, request=None):
    """Freeze the last successful program before this restore enters REPLACING."""
    guard = (lambda: None) if guard is None else guard
    guard(); validate_policy(policy); _assert_lock(policy['backupEpochPolicy'], lock_fd)
    read, unchanged = _reader(reader, guard)
    root, _ = _claim(policy, operation_id, read)
    require(not os.path.lexists(root/'program-context.json'), 'PROGRAM_METADATA_ALREADY_EXISTS')
    current = read_current(policy['backupEpochPolicy'], guard=guard)
    if current['state'] == 'FAILED_RETAINED':
        require(type(owner) is dict and type(request) is dict and
            request['operationId'] == operation_id and request['targetConfigRef'] == policy['targetConfigRef'] and
            owner['targetProgramPolicies'][policy['targetConfigRef']] == policy, 'PROGRAM_RETRY_REQUEST_REQUIRED')
        from recovery_program_retry import resolve_retry_target
        result = resolve_retry_target(owner, policy['targetConfigRef'], purpose='CONSUMED_EXECUTION',
            source_ref=request['sourceConfigRef'], recovery_point_ref=request['recoveryPointRef'],
            operation_id=operation_id, reader=read, guard=guard)
        context = dict(schemaVersion='MainProgramRestoreContext/v2', policySha256=digest(policy),
            operationId=operation_id, readyEpoch=result['readyEpoch'], targetPin=result['targetPin'],
            parentGenerationPin=result['generationPin'], capturePins=result['captures'],
            evidencePins=result['evidencePins'], startEpoch=result['startEpoch'], retryAuthorization=result['authorization'])
        expected_epoch = result['startEpoch']
    else:
        result = _resolve(policy, read, guard)
        context = dict(schemaVersion='MainProgramRestoreContext/v1', policySha256=digest(policy),
            operationId=operation_id, readyEpoch=result['epoch'], targetPin=result['targetPin'],
            parentGenerationPin=result['generationPin'], capturePins=result['captures'], evidencePins=result['evidence'])
        expected_epoch = result['epoch']
    def held():
        guard(); _assert_lock(policy['backupEpochPolicy'], lock_fd)
        require(read_current(policy['backupEpochPolicy'], guard=guard) == expected_epoch,
                'PROGRAM_RESTORE_EPOCH_CHANGED')
    unchanged(); held()
    return _exclusive(root/'program-context.json', context, held)


def stage_generation(policy, context_pin, *, target_pin, capture_pins, switch_result_pin,
                     lock_fd, reader=document, guard=None, owner=None, request=None):
    """Validate and stage one candidate; the caller must finish the real restore."""
    guard = (lambda: None) if guard is None else guard
    guard(); validate_policy(policy); _assert_lock(policy['backupEpochPolicy'], lock_fd)
    read, unchanged = _reader(reader, guard)
    context = read(context_pin)
    retry = context.get('schemaVersion') == 'MainProgramRestoreContext/v2'
    if retry:
        from recovery_program_retry import validate_retry_context, CONTEXT_V2_FIELDS
        require(type(owner) is dict and type(request) is dict and
            owner['targetProgramPolicies'][policy['targetConfigRef']] == policy, 'PROGRAM_RETRY_REQUEST_REQUIRED')
        validate_retry_context(owner, request, context, reader=read, guard=guard)
        fields = CONTEXT_V2_FIELDS
    else:
        fields = CONTEXT_FIELDS
    require(type(context) is dict and set(context) == fields and
            context['schemaVersion'] == ('MainProgramRestoreContext/v2' if retry else 'MainProgramRestoreContext/v1') and
            context['policySha256'] == digest(policy) and
            type(context['readyEpoch']) is dict and context['readyEpoch'].get('state') == 'READY' and
            context['readyEpoch'].get('policySha256') == digest(policy['backupEpochPolicy']) and
            type(context['capturePins']) is dict and
            set(context['capturePins']) == set(policy['captureConfigurationPins']) and
            type(context['evidencePins']) is list and context['evidencePins'],
            'PROGRAM_RESTORE_CONTEXT_INVALID')
    root, baseline = _claim(policy, context['operationId'], read)
    require(Path(context_pin['path']) == root/'program-context.json', 'PROGRAM_RESTORE_CONTEXT_INVALID')
    require(not os.path.lexists(root/'generation.json'), 'PROGRAM_METADATA_ALREADY_EXISTS')
    def started():
        guard(); _assert_lock(policy['backupEpochPolicy'], lock_fd)
        current = read_current(policy['backupEpochPolicy'], guard=guard)
        require(current['state'] == 'REPLACING' and current['operationId'] == context['operationId'],
                'PROGRAM_RESTORE_EPOCH_CHANGED')
        event = read(current['eventPin'])
        start_epoch = context['startEpoch'] if retry else context['readyEpoch']
        start_pin = start_epoch['eventPin']; start = read(start_pin)
        ready_pin = context['readyEpoch']['eventPin']
        ready = read(ready_pin)
        require(event['kind'] == 'RESTORE_STARTED' and
                event['previousSha256'] == start_pin['sha256'] and
                event['sequence'] == start['sequence']+1 and ready['state'] == 'READY' and
                _snapshot(ready, ready_pin) == context['readyEpoch'] and
                Path(ready_pin['path']) == Path(policy['backupEpochPolicy']['root'])/('%020d.json' % ready['sequence']),
                'PROGRAM_RESTORE_EPOCH_CHANGED')
        if ready_pin == policy['initialEpochPin']:
            expected_target = policy['baselineTargetPin']
            expected_parent = None
            expected_captures = policy['captureConfigurationPins']
        else:
            require(ready['kind'] == 'RESTORE_FINISHED' and ready['evidencePin'] is not None,
                    'PROGRAM_RESTORE_CONTEXT_INVALID')
            completed = read(ready['evidencePin'])
            expected_parent = completed.get('programGenerationPin')
            require(expected_parent is not None, 'PROGRAM_RESTORE_CONTEXT_INVALID')
            previous_generation = read(expected_parent)
            require(previous_generation.get('schemaVersion') == 'MainProgramGeneration/v1' and
                    previous_generation.get('policySha256') == digest(policy) and
                    previous_generation.get('epochId') == ready['epochId'] and
                    previous_generation.get('operationId') == ready['operationId'] and
                    type(previous_generation.get('captureBindings')) is dict and
                    set(previous_generation['captureBindings']) == set(policy['captureConfigurationPins']),
                    'PROGRAM_RESTORE_CONTEXT_INVALID')
            expected_target = previous_generation['targetPin']
            expected_captures = {source: binding['capturePin']
                for source, binding in previous_generation['captureBindings'].items()}
        require(context['targetPin'] == expected_target and context['parentGenerationPin'] == expected_parent and
                context['capturePins'] == expected_captures, 'PROGRAM_RESTORE_CONTEXT_INVALID')
        intent = read(event['evidencePin'])
        require(intent['targetConfigRef'] == policy['targetConfigRef'] and
                Path(intent['replacementReceiptPath']) == root/'replacement-result.json',
                'PROGRAM_RESTORE_CONTEXT_INVALID')
        return current
    current = started()
    if not retry:
        for reference in context['evidencePins']:
            read(reference)
    require(context['readyEpoch']['eventPin'] in context['evidencePins'] and
            context['targetPin'] in context['evidencePins'], 'PROGRAM_RESTORE_CONTEXT_INVALID')
    previous = read(context['targetPin']); target = read(target_pin)
    _target_transition(previous, target, switch_result_pin, context['operationId'], read)
    require(type(capture_pins) is dict and set(capture_pins) == set(policy['captureConfigurationPins']),
            'PROGRAM_CAPTURE_BINDINGS_INVALID')
    bindings = {}
    for source_ref, base_pin in policy['captureConfigurationPins'].items():
        _capture_transition(read(base_pin), read(capture_pins[source_ref]), baseline,
            target, source_ref, policy['backupEpochPolicy'], read)
        bindings[source_ref] = dict(baseCapturePin=deepcopy(base_pin), capturePin=deepcopy(capture_pins[source_ref]))
    generation = dict(schemaVersion='MainProgramGeneration/v1', operationId=context['operationId'],
        epochId=current['epochId'], policySha256=digest(policy), targetConfigRef=policy['targetConfigRef'],
        baselineTargetPin=deepcopy(policy['baselineTargetPin']), parentGenerationPin=context['parentGenerationPin'],
        targetPin=deepcopy(target_pin), captureBindings=bindings, switchResultPin=deepcopy(switch_result_pin))
    def held():
        require(started() == current, 'PROGRAM_RESTORE_EPOCH_CHANGED')
    unchanged(); held()
    return _exclusive(root/'generation.json', generation, held)
