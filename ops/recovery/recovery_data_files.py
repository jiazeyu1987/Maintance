"""Offline versioned MinIO full tree and exact file deltas, without source writes."""
from __future__ import annotations

import os
from pathlib import PurePosixPath
import shutil

from recovery_engine import absolute, check_pin, pin, require


def relative(value):
    require(type(value) is str and value and '\\' not in value and '\0' not in value,
            'FILE_RELATIVE_PATH_INVALID')
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(part not in ('', '.', '..') for part in value.split('/')) and
            str(path) == value, 'FILE_RELATIVE_PATH_INVALID')
    return path


def validate_inventory(value):
    require(type(value) is dict, 'COMPLETE_FILE_INVENTORY_REQUIRED')
    for name, item in value.items():
        path = relative(name)
        require(type(item) is dict and item.get('kind') in ('file', 'directory'), 'FILE_INVENTORY_ENTRY_INVALID')
        require(set(item) == ({'kind'} if item['kind'] == 'directory' else {'kind', 'bytes', 'sha256'}),
                'FILE_INVENTORY_ENTRY_INVALID')
        if item['kind'] == 'file':
            # The path-free pin components receive the same type checks as a pin.
            require(type(item['bytes']) is int and item['bytes'] >= 0 and type(item['sha256']) is str and
                    len(item['sha256']) == 64 and set(item['sha256']) <= set('0123456789abcdef'), 'FILE_INVENTORY_ENTRY_INVALID')
        for parent in path.parents:
            if str(parent) != '.':
                require(value.get(str(parent)) == {'kind': 'directory'}, 'FILE_INVENTORY_PARENT_MISSING')
    return value


def inventory(root, guard, *, content=True):
    root = absolute(str(root)); require(root.is_dir(), 'FILE_TARGET_DIRECTORY_REQUIRED')
    result = {}
    for base, directories, files in os.walk(root, followlinks=False):
        guard()
        for name in sorted(directories + files):
            path = absolute(str(root / os.path.relpath(os.path.join(base, name), root)))
            key = path.relative_to(root).as_posix()
            require(not path.is_symlink(), 'FILE_TREE_ALIAS_REJECTED')
            if path.is_dir():
                result[key] = {'kind': 'directory'}
            else:
                if content:
                    item = pin(path); result[key] = dict(kind='file', bytes=item['bytes'], sha256=item['sha256'])
                else:
                    result[key] = dict(kind='file', bytes=path.stat().st_size)
    return validate_inventory(result) if content else result


def tree_delta(before, after, *, verify_inventory=True):
    if verify_inventory:
        before = validate_inventory(before); after = validate_inventory(after)
    changed = sorted(name for name, item in after.items() if before.get(name) != item)
    removed = {name for name in before if name not in after or before[name]['kind'] != after[name]['kind']}
    return changed, sorted(removed, key=lambda name: (-len(relative(name).parts), name))


def physical_chain_inputs(chain, *, verify_content=True):
    """Validate the capture chain; optionally verify payload bytes."""
    from recovery_engine import pinned_json
    prior = {}; result = []
    for _, point, material, material_pin in chain:
        descriptor = material['objects']; capture = pinned_json(descriptor['capturePointPin'])
        expected = validate_inventory(capture['fileInventory'])
        require(capture['commonRecoveryPoint'] == material['recoveryPoint'] and
                capture['pointType'] == point['pointType'] and
                pinned_json(descriptor['fileInventoryPin']) == expected, 'PHYSICAL_CAPTURE_INVENTORY_MISMATCH')
        changed, removed = tree_delta(prior, expected)
        require(capture['fileDelta']['changedPaths'] == changed and
                capture['fileDelta']['deletedPaths'] == removed, 'CAPTURED_FILE_DELTA_MISMATCH')
        payloads = descriptor['filePayloadPins']
        require(set(payloads) == {name for name in changed if expected[name]['kind'] == 'file'} and
                all(ref in material['payloadPins'] for ref in payloads.values()), 'PHYSICAL_CONTENT_NOT_ARCHIVED')
        for name, ref in payloads.items():
            if verify_content:
                require(pin(ref['path']) == ref, 'PIN_CHANGED')
            require((ref['bytes'], ref['sha256']) == (expected[name]['bytes'], expected[name]['sha256']),
                    'FILE_DELTA_CONTENT_MISMATCH')
        result.append((material_pin, prior, expected, payloads, changed, removed)); prior = expected
    return result


def apply_tree(root, before, after, payloads, *, full, guard, ownership=None, verify_content=True):
    """Diff must be exact. All mutation paths stay inside the dedicated root."""
    root = absolute(str(root))
    if verify_content:
        before = validate_inventory(before); after = validate_inventory(after)
        require(inventory(root, guard) == before, 'OFFLINE_TARGET_TREE_CHANGED')
    changed = {name for name, item in after.items() if item['kind'] == 'file' and before.get(name) != item}
    if verify_content:
        require(set(payloads) == changed, 'FILE_DELTA_CONTENT_SCOPE_MISMATCH')
    if full:
        require(not before, 'FULL_FILE_TARGET_NOT_EMPTY')
    if verify_content:
        for name, ref in payloads.items():
            relative(name)
            require(pin(ref['path']) == ref, 'PIN_CHANGED')
            require((ref['bytes'], ref['sha256']) == (after[name]['bytes'], after[name]['sha256']), 'FILE_DELTA_CONTENT_MISMATCH')
            source = absolute(ref['path'])
            require(not source.is_relative_to(root) and not root.is_relative_to(source), 'FILE_SOURCE_TARGET_OVERLAP')
    # Remove only this restore's prior tree entries, deepest first.
    _, removed = tree_delta(before, after, verify_inventory=verify_content)
    for name in removed:
        guard(); path = absolute(str(root.joinpath(*relative(name).parts)))
        if before[name]['kind'] == 'directory':
            path.rmdir()
        else:
            path.unlink()
    for name in sorted(after, key=lambda name: (len(relative(name).parts), name)):
        guard(); path = absolute(str(root.joinpath(*relative(name).parts)))
        item = after[name]
        if item['kind'] == 'directory':
            if name not in before or name in removed:
                path.mkdir(mode=0o700)
        elif name in changed:
            # Previous version is already recoverable from the pinned parent.
            temporary = path.with_name(path.name + '.recovery-' + os.urandom(8).hex())
            with temporary.open('xb') as target, absolute(payloads[name]['path']).open('rb') as source:
                os.chmod(temporary, 0o600)
                while chunk := source.read(1024*1024):
                    guard(); target.write(chunk)
                target.flush(); os.fsync(target.fileno())
            if verify_content:
                require(pin(payloads[name]['path']) == payloads[name], 'PIN_CHANGED')
                copied = pin(temporary)
                require(copied['sha256'] == item['sha256'] and copied['bytes'] == item['bytes'],
                        'COPIED_FILE_READBACK_MISMATCH')
            os.replace(temporary, path)
        if ownership is not None:
            require(os.name == 'posix' and len(ownership) == 2 and all(type(v) is int and v >= 0 for v in ownership),
                    'FILE_OWNERSHIP_INVALID')
            os.chown(path, *ownership)
    if verify_content:
        require(inventory(root, guard) == after, 'OFFLINE_FILE_READBACK_MISMATCH')
    if os.name == 'posix':
        for path in [root, *(root.joinpath(*relative(name).parts) for name, item in after.items() if item['kind'] == 'directory')]:
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
    guard()
    return {'changedFileCount': len(changed), 'deletedPathCount': len(removed),
            'completeTreeReadback': verify_content}
