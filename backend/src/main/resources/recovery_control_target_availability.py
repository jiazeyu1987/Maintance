"""Exclude claimed restore targets from admission; owner still checks emptiness."""
from pathlib import Path

from recovery_control_smallapp import need


def unclaimed_target(target, source_ref, target_ref):
    need(target_ref != source_ref and target['targetId'] != source_ref,
         'SOURCE_TARGET_OVERLAP')
    need(target['sourceConfigRef'] == source_ref, 'TARGET_SOURCE_MISMATCH')
    if 'replacement' in target:
        from recovery_replace import available
        return available(target)
    root = Path(target['dataRoot'])
    need(root.is_absolute() and root.resolve() == root and root.is_dir(),
         'TARGET_DATA_PATHS_REQUIRED')
    try:
        (root / '.recovery-operation.json').lstat()
    except FileNotFoundError:
        return True
    # Includes malformed claims, directories and dangling symlinks. A retained
    # failed target is never made available again by interpreting its contents.
    return False


def available(native, configuration_pin, target_ref, source_ref):
    configuration = native.document(configuration_pin)
    need(target_ref in configuration['targets'], 'NEW_TARGET_CONFIGURATION_REQUIRED')
    return unclaimed_target(configuration['targets'][target_ref], source_ref, target_ref)
