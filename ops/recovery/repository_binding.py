"""Publish W02's two outputs from independently read, byte-exact originals."""
import hashlib
from pathlib import Path
import sys
import types

from repository_records import (absolute, canonical, document, exact, pin_file,
                                read_pin, require, safe_path, write_new)


def load_capture_binder(config):
    reference = config.implementation['captureBinder']
    raw = read_pin(reference, 1024 * 1024)
    name = 'repository_capture_binder_' + reference['sha256']
    module = types.ModuleType(name)
    module.__file__ = reference['path']
    # The pinned binder imports W02's existing source interfaces. Its complete
    # approved source closure remains the native source configuration's job.
    directory = str(absolute(reference['path']).parent)
    approved = {absolute(pin['path']): pin for pin in config.value['captureBinderDependencyPins']}
    approved[absolute(reference['path'])] = reference
    # Before importing, every local module the binder may resolve is explicitly
    # pinned. Unlisted files cannot enter the import closure.
    for path in Path(directory).glob('*.py'):
        require(path in approved, 'REPOSITORY_CAPTURE_BINDER_DEPENDENCY_NOT_APPROVED')
        read_pin(approved[path], 32 * 1024 * 1024)
    sys.path.insert(0, directory)
    old_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        exec(compile(raw, reference['path'], 'exec'), module.__dict__)
    finally:
        sys.dont_write_bytecode = old_bytecode
        sys.path.remove(directory)
    for loaded in list(sys.modules.values()):
        filename = getattr(loaded, '__file__', None)
        if filename and Path(filename).is_absolute() and Path(filename).parent == Path(directory):
            require(Path(filename) in approved and pin_file(filename) == approved[Path(filename)],
                    'REPOSITORY_CAPTURE_BINDER_DEPENDENCY_CHANGED')
    require(callable(getattr(module, 'assemble_repository_capture_records', None)),
            'REPOSITORY_CAPTURE_BINDER_REQUIRED')
    return module.assemble_repository_capture_records


def publish_capture_bindings(config, catalog, request, manifest_pin, readback, deadline):
    manifest = document(read_pin(manifest_pin, deadline=deadline))
    parent_binding = catalog.binding(manifest['parentPointPins'][-1]) if manifest['parentPointPins'] else None
    outputs = assemble_readback_bindings(manifest_pin, readback, deadline,
        load_capture_binder(config), parent_binding)
    config.current()
    config.authorization(request, request['sourceOrTargetRef'])
    sidecar = safe_path(Path(manifest_pin['path']).parent)
    return {'recoveryMaterialPin': write_new(sidecar / 'recovery-material.json', outputs['recoveryMaterial']),
            'objectContentIndexPin': write_new(sidecar / 'object-content-index.json', outputs['objectContentIndex']),
            'sourceScopePin': outputs['recoveryMaterial']['sourceScopePin']}


def assemble_readback_bindings(manifest_pin, readback, deadline, binder, parent_binding=None):
    """Shared real-byte assembly; admission and publication belong to the caller."""
    manifest = document(read_pin(manifest_pin, deadline=deadline))
    archive = safe_path(Path(manifest_pin['path']).parent.parent)
    originals = document(read_pin(readback['originalRecordsPin'], 96 * 1024 * 1024, deadline))
    exact(originals, 'schemaVersion manifestPin archivedFilePins readbackOriginalPins',
          'RepositoryReadbackOriginals/v1')
    require(originals['manifestPin'] == manifest_pin, 'REPOSITORY_READBACK_BINDING_CHANGED')
    mapping = originals['archivedFilePins']
    require(type(mapping) is dict and mapping,
            'REPOSITORY_READBACK_BINDING_INVALID')
    require('capture-recovery-inputs.json' in mapping and
            sorted(mapping.values(), key=lambda p: p['path']) ==
            sorted(manifest['payloadRefs'], key=lambda p: p['path']),
            'REPOSITORY_READBACK_PAYLOAD_SET_MISMATCH')
    for name, reference in mapping.items():
        require(absolute(reference['path']) == archive / name,
                'REPOSITORY_READBACK_PATH_CHANGED')
        require(pin_file(reference['path'], deadline) == reference,
                'REPOSITORY_READBACK_PAYLOAD_CHANGED')
    raw_records = {}
    for source_path, reference in originals['readbackOriginalPins'].items():
        raw_records[source_path] = read_pin(reference, 64 * 1024 * 1024, deadline)
    inputs_reference = mapping['capture-recovery-inputs.json']
    # The independently read copy has the published file's exact bytes, never
    # a canonical re-encoding of the ASCII/newline capture original.
    matching = [raw for raw in raw_records.values()
                if len(raw) == inputs_reference['bytes'] and
                hashlib.sha256(raw).hexdigest() == inputs_reference['sha256']]
    require(len(matching) == 1, 'REPOSITORY_CAPTURE_INPUT_ORIGINAL_REQUIRED')
    inputs = document(matching[0])
    parent_index = None
    if manifest['parentPointPins']:
        require(parent_binding is not None, 'REPOSITORY_PARENT_INDEX_REQUIRED')
        parent_index = document(read_pin(parent_binding['objectContentIndexPin'],
                                        64 * 1024 * 1024, deadline))
        source_index = document(raw_records[inputs['objectContentIndexPin']['path']])
        require(source_index['parentExportIndexPin'] ==
                parent_binding['objectContentIndexPin'], 'REPOSITORY_PARENT_INDEX_MISMATCH')
    deadline.check()
    outputs = binder(inputs, manifest, manifest_pin=manifest_pin,
        archived_file_pins=mapping, original_records=raw_records,
        parent_object_index=parent_index)
    deadline.check()
    require(type(outputs) is dict and set(outputs) == {'recoveryMaterial', 'objectContentIndex'},
            'REPOSITORY_CAPTURE_BINDER_OUTPUT_INVALID')
    material, index = outputs['recoveryMaterial'], outputs['objectContentIndex']
    require(material['manifestPin'] == index['manifestPin'] == manifest_pin and
            index['repositoryBound'] is True, 'REPOSITORY_CAPTURE_BINDER_OUTPUT_INVALID')
    for reference in index['contentPins'].values():
        require(pin_file(reference['path'], deadline) == reference,
                'REPOSITORY_OBJECT_CONTENT_CHANGED')
    return outputs


def repository_binding(config, point_pin, point, material_pin, index_pin):
    material = document(read_pin(material_pin, 64 * 1024 * 1024))
    index = document(read_pin(index_pin, 64 * 1024 * 1024))
    require(material['manifestPin'] == index['manifestPin'] == point['manifestPin'] and
            material['recoveryPoint'] == index['recoveryPoint'] == point['commonRecoveryPoint'] and
            index['backupId'] == point['backupId'] and index['generationId'] == point['generationId'] and
            index['repositoryBound'] is True, 'REPOSITORY_CAPTURE_BINDING_INVALID')
    scope = document(read_pin(material['sourceScopePin']))
    identity = document(read_pin(scope['sourceIdentityPin']))
    require(scope['sourceIdentityPin'] == config.policy['sourceIdentityPin'] and
            material['sourceFingerprint'] == index['sourceIdentity'] == identity['sourceFingerprint'],
            'REPOSITORY_BUSINESS_SOURCE_MISMATCH')
    return dict(schemaVersion='RecoveryRepositoryBinding/v1', backupId=point['backupId'],
                generationId=point['generationId'], repositoryPointPin=point_pin,
                manifestPin=point['manifestPin'], sourceScopePin=material['sourceScopePin'],
                recoveryMaterialPin=material_pin, objectContentIndexPin=index_pin)
