"""Bind one MAIN target to its proven active program without rewriting owners."""
from copy import deepcopy

from recovery_engine import require
from recovery_program_generation import document


def resolve_configuration(configuration, target_ref, *, reader=document, guard=None):
    """Return an effective owner and a private immutable-program binding.

    Owners without a policy for this target retain their existing contract.
    Evidence is for internal original verification, never a public response.
    """
    if 'targetProgramPolicies' not in configuration:
        return configuration, None
    policies = configuration['targetProgramPolicies']
    targets = configuration.get('targets')
    require(type(policies) is dict and type(targets) is dict and
            set(policies) <= set(targets), 'PROGRAM_TARGET_POLICIES_INVALID')
    if target_ref not in policies:
        return configuration, None
    policy = policies[target_ref]
    require(type(policy) is dict and policy.get('targetConfigRef') == target_ref and
            'baselineTargetPin' in policy, 'PROGRAM_TARGET_POLICY_BINDING_INVALID')
    original = targets[target_ref]
    require(type(original) is dict and 'mainApplication' in original, 'PROGRAM_TARGET_MAIN_REQUIRED')
    epochs = configuration.get('targetBackupEpochPolicies')
    require(type(epochs) is dict and target_ref in epochs and
            type(policy.get('backupEpochPolicy')) is dict and
            policy['backupEpochPolicy'] == epochs[target_ref], 'PROGRAM_TARGET_EPOCH_BINDING_INVALID')
    if guard is not None: guard()
    baseline = reader(policy['baselineTargetPin'])
    if guard is not None: guard()
    require(baseline == original, 'PROGRAM_TARGET_BASELINE_CHANGED')
    from recovery_program_generation import resolve_target
    target, target_pin, evidence = resolve_target(policy, reader=reader, guard=guard)
    effective = deepcopy(configuration)
    effective['targets'][target_ref] = deepcopy(target)
    binding = dict(policy=deepcopy(policy), targetPin=deepcopy(target_pin), evidencePins=deepcopy(evidence))
    if guard is not None: guard()
    return effective, binding


def resolve_restore_configuration(configuration, target_ref, *, purpose, source_ref,
                                  recovery_point_ref=None, operation_id=None, reader=document, guard=None):
    """Explicit target admission, separate from the public READY-only resolver."""
    require(purpose in ('SOURCE_CANDIDATE', 'RESTORE_REQUEST'), 'PROGRAM_RETRY_PURPOSE_REQUIRED')
    policies = configuration.get('targetProgramPolicies', {})
    require(type(policies) is dict, 'PROGRAM_TARGET_POLICIES_INVALID')
    if target_ref not in policies:
        return resolve_configuration(configuration, target_ref, reader=reader, guard=guard)
    from recovery_backup_epoch import read_current
    current = read_current(policies[target_ref]['backupEpochPolicy'], guard=guard)
    if current['state'] != 'FAILED_RETAINED':
        return resolve_configuration(configuration, target_ref, reader=reader, guard=guard)
    from recovery_program_retry import resolve_retry_target
    result = resolve_retry_target(configuration, target_ref, purpose=purpose, source_ref=source_ref,
        recovery_point_ref=recovery_point_ref, operation_id=operation_id, reader=reader, guard=guard)
    effective = deepcopy(configuration)
    effective['targets'][target_ref] = deepcopy(result['target'])
    return effective, dict(policy=deepcopy(policies[target_ref]), targetPin=deepcopy(result['targetPin']),
        evidencePins=deepcopy(result['evidencePins']), retryAuthorization=deepcopy(result['authorization']))
