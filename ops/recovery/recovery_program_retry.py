"""One explicit no-mutation v1 failure may precede a private v2 MAIN restore.

This target-only authority never publishes READY or changes a source reader.
The predecessor must have a v1 context before its clearance is validated; this
keeps the historical proof graph acyclic and rejects retries of v2 failures.
"""
from copy import deepcopy
import os
from pathlib import Path
import re

from recovery_engine import RecoveryError, absolute, digest, require
from recovery_backup_epoch import _read_file, _snapshot, read_current
from recovery_program_generation import document, validate_policy, _resolve_at_ready

CONTEXT_V2_FIELDS = {'schemaVersion', 'policySha256', 'operationId', 'readyEpoch',
    'targetPin', 'parentGenerationPin', 'capturePins', 'evidencePins', 'startEpoch', 'retryAuthorization'}
PURPOSES = {'SOURCE_CANDIDATE', 'RESTORE_REQUEST', 'CONSUMED_EXECUTION'}


def _unique(references):
    result = {}; order = []
    for reference in references:
        key = reference['path']
        require(key not in result or result[key] == reference, 'PROGRAM_RETRY_PIN_CONFLICT')
        if key not in result:
            result[key] = deepcopy(reference); order.append(key)
    return [result[key] for key in order]


def _resolve(configuration, target_ref, *, purpose, source_ref, recovery_point_ref,
             operation_id, reader, guard, start_epoch=None):
    guard = (lambda: None) if guard is None else guard
    require(purpose in PURPOSES, 'PROGRAM_RETRY_PURPOSE_REQUIRED')
    if purpose == 'SOURCE_CANDIDATE':
        require(recovery_point_ref is None and operation_id is None, 'PROGRAM_RETRY_PURPOSE_INVALID')
    else:
        require(type(recovery_point_ref) is str and bool(recovery_point_ref) and
            type(operation_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', operation_id),
            'PROGRAM_RETRY_REQUEST_REQUIRED')
    require(type(source_ref) is str and source_ref in configuration['sources'], 'PROGRAM_RETRY_SOURCE_CHANGED')
    guard(); policy = configuration['targetProgramPolicies'][target_ref]; validate_policy(policy)
    require(policy['targetConfigRef'] == target_ref and
        configuration['targetBackupEpochPolicies'][target_ref] == policy['backupEpochPolicy'],
        'PROGRAM_RETRY_POLICY_CHANGED')
    references = []
    def read(reference):
        guard(); value = reader(reference); references.append(deepcopy(reference)); guard(); return value
    def fixed(path):
        guard(); _, reference = _read_file(path, 4*1024*1024)
        return read(reference), reference
    target = configuration['targets'][target_ref]
    require(read(policy['baselineTargetPin']) == target, 'PROGRAM_TARGET_BASELINE_CHANGED')
    current = read_current(policy['backupEpochPolicy'], guard=guard)
    failed = current if start_epoch is None else start_epoch
    require(type(failed) is dict and failed.get('state') == 'FAILED_RETAINED', 'PROGRAM_RETRY_FAILED_EPOCH_REQUIRED')
    event = read(failed['eventPin']); tail = read(current['eventPin'])
    require(event['kind'] == 'RESTORE_FINISHED' and event['state'] == 'FAILED_RETAINED' and
        _snapshot(event, failed['eventPin']) == failed and
        Path(failed['eventPin']['path']) == Path(policy['backupEpochPolicy']['root'])/('%020d.json' % event['sequence']) and
        event['sequence'] <= tail['sequence'], 'PROGRAM_RETRY_EPOCH_CHANGED')
    if start_epoch is None:
        require(current == failed, 'PROGRAM_RETRY_EPOCH_CHANGED')
    old_operation = event['operationId']
    require(operation_id is None or operation_id != old_operation, 'PROGRAM_RETRY_NEW_OPERATION_REQUIRED')
    claim = absolute(target['replacement']['stateRoot'])/old_operation
    require(claim.is_dir(), 'PROGRAM_RETRY_PREDECESSOR_MISSING')
    context, context_pin = fixed(claim/'program-context.json')
    # This check precedes validate_clearance, which validates the old proof.
    require(context.get('schemaVersion') != 'MainProgramRestoreContext/v2',
        'PROGRAM_RETRY_PREDECESSOR_V2_UNSUPPORTED')
    from recovery_program_activation import CONTEXT_FIELDS
    require(type(context) is dict and set(context) == CONTEXT_FIELDS and
        context['schemaVersion'] == 'MainProgramRestoreContext/v1' and context['operationId'] == old_operation and
        context['policySha256'] == digest(policy), 'PROGRAM_RETRY_PREDECESSOR_INVALID')
    from recovery_retained_retry import validate_clearance
    clearance = validate_clearance(target, claim)
    require(type(clearance) is dict and clearance.get('schemaVersion') == 'RetainedReplacementRecovery/v2' and
        clearance.get('failurePhase') == 'BEFORE_MUTATION' and 'inheritedQuiescencePin' not in clearance and
        clearance['operationId'] == old_operation and clearance['targetConfigRef'] == target_ref and
        (recovery_point_ref is None or clearance['recoveryPointRef'] == recovery_point_ref) and
        clearance['replacementResultPin'] == event['evidencePin'], 'PROGRAM_RETRY_CLEARANCE_INVALID')
    require(clearance['sourceConfigRef'] == source_ref, 'PROGRAM_RETRY_SOURCE_NOT_AUTHORIZED')
    clearance_value, clearance_pin = fixed(claim/'recovery-clearance.json')
    require(clearance_value == clearance, 'PROGRAM_RETRY_CLEARANCE_CHANGED')
    old_owner = read(clearance['configurationPin']); old_request = read(clearance['requestPin'])
    require(old_owner['targets'][target_ref] == target and old_owner['targetProgramPolicies'][target_ref] == policy and
        Path(clearance['requestPin']['path']).parent == absolute(old_owner['operationsRoot'])/old_operation and
        all(old_request[k] == clearance[k] for k in ('sourceConfigRef', 'recoveryPointRef', 'targetConfigRef')),
        'PROGRAM_RETRY_PREDECESSOR_CHANGED')
    from recovery_program_evidence import validate_program_evidence
    from recovery_resource_admission import _unmutated_program_preparation
    proof = validate_program_evidence(old_owner, old_request,
        Path(clearance['requestPin']['path']).parent, result_pin=clearance['resultPin'], guard=guard)
    require(_unmutated_program_preparation(proof) and proof['contextPin'] == context_pin and
        proof['epoch']['state'] == 'FAILED_RETAINED' and proof['epoch']['eventPin'] == failed['eventPin'],
        'PROGRAM_RETRY_PREPARATION_UNPROVEN')
    ready, ready_pin = fixed(claim/'recovery-ready.json')
    require(ready['clearancePin'] == clearance_pin, 'PROGRAM_RETRY_CLEARANCE_CHANGED')
    consumption_pin = None
    used_path = claim/'recovery-consumption.json'
    if purpose == 'CONSUMED_EXECUTION':
        require(used_path.is_file(), 'PROGRAM_RETRY_CONSUMPTION_REQUIRED')
        used, consumption_pin = fixed(used_path)
        require(set(used) == {'schemaVersion', 'clearancePin', 'replacementOperationId', 'consumedAt'} and
            used['schemaVersion'] == 'RetainedReplacementConsumption/v1' and used['clearancePin'] == clearance_pin and
            used['replacementOperationId'] == operation_id, 'PROGRAM_RETRY_CONSUMPTION_CHANGED')
    else:
        require(not os.path.lexists(used_path), 'PROGRAM_RETRY_CLEARANCE_ALREADY_CONSUMED')
    for key in ('resultPin', 'exitPin', 'replacementResultPin', 'noMutationReleasePin', 'observationPin'):
        read(clearance[key])
    read(ready['releasePin'])
    historical = _resolve_at_ready(policy, context['readyEpoch']['eventPin'], read, guard)
    require(context['readyEpoch'] == historical['epoch'] and context['targetPin'] == historical['targetPin'] and
        context['parentGenerationPin'] == historical['generationPin'] and context['capturePins'] == historical['captures'],
        'PROGRAM_RETRY_PREDECESSOR_CHANGED')
    authorization = dict(schemaVersion='MainProgramRetainedRetryAuthorization/v1', predecessorOperationId=old_operation,
        sourceConfigRef=source_ref, recoveryPointRef=clearance['recoveryPointRef'], targetConfigRef=target_ref,
        configurationPin=clearance['configurationPin'], requestPin=clearance['requestPin'],
        resultPin=clearance['resultPin'], exitPin=clearance['exitPin'], replacementResultPin=clearance['replacementResultPin'],
        contextPin=context_pin, clearancePin=clearance_pin, readyPin=ready_pin,
        noMutationReleasePin=clearance['noMutationReleasePin'], recoveryReleasePin=ready['releasePin'],
        observationPin=clearance['observationPin'], consumptionPin=consumption_pin)
    # The current tail is a live check, not part of the immutable start proof.
    evidence = _unique([p for p in [*references, *proof['originalResultPins']]
        if p != current['eventPin'] or p == failed['eventPin']])
    require(read_current(policy['backupEpochPolicy'], guard=guard) == current, 'PROGRAM_RETRY_EPOCH_CHANGED')
    guard()
    return dict(target=historical['target'], targetPin=historical['targetPin'], captures=historical['captures'],
        generationPin=historical['generationPin'], readyEpoch=historical['epoch'], startEpoch=deepcopy(failed),
        authorization=authorization, evidencePins=evidence)


def resolve_retry_target(configuration, target_ref, *, purpose, source_ref, recovery_point_ref=None,
                         operation_id=None, reader=document, guard=None):
    """Explicit read-only candidate/request or already-consumed execution proof."""
    try:
        return _resolve(configuration, target_ref, purpose=purpose, source_ref=source_ref,
            recovery_point_ref=recovery_point_ref, operation_id=operation_id, reader=reader, guard=guard)
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise RecoveryError('PROGRAM_RETRY_FORMAT_INVALID') from error


def observe_retry_admission(configuration, target_ref, *, source_ref, reader=document, guard=None):
    result = resolve_retry_target(configuration, target_ref, purpose='SOURCE_CANDIDATE',
        source_ref=source_ref, reader=reader, guard=guard)
    auth = result['authorization']
    return dict(schemaVersion='MainProgramRetainedRetryAdmission/v1', state='FAILED_RETAINED_RETRY_ADMITTED',
        sourceConfigRef=source_ref, targetConfigRef=target_ref, recoveryPointRef=auth['recoveryPointRef'],
        predecessorOperationId=auth['predecessorOperationId'], epoch=result['startEpoch'], readyEpoch=result['readyEpoch'],
        targetPin=result['targetPin'], parentGenerationPin=result['generationPin'], capturePins=result['captures'],
        authorization=auth, evidencePins=result['evidencePins'], serverWrites=False)


def validate_retry_context(configuration, request, context, *, reader=document, guard=None):
    """Reconstruct one consumed v2 context; no current-state authority is inferred."""
    require(type(context) is dict and set(context) == CONTEXT_V2_FIELDS and
        context['schemaVersion'] == 'MainProgramRestoreContext/v2' and context['operationId'] == request['operationId'] and
        context['policySha256'] == digest(configuration['targetProgramPolicies'][request['targetConfigRef']]),
        'PROGRAM_RESTORE_CONTEXT_INVALID')
    result = _resolve(configuration, request['targetConfigRef'], purpose='CONSUMED_EXECUTION',
        source_ref=request['sourceConfigRef'], recovery_point_ref=request['recoveryPointRef'],
        operation_id=request['operationId'], reader=reader, guard=guard, start_epoch=context['startEpoch'])
    require(context['readyEpoch'] == result['readyEpoch'] and context['targetPin'] == result['targetPin'] and
        context['parentGenerationPin'] == result['generationPin'] and context['capturePins'] == result['captures'] and
        context['retryAuthorization'] == result['authorization'] and context['evidencePins'] == result['evidencePins'],
        'PROGRAM_RESTORE_CONTEXT_INVALID')
    return result
