"""Bind an explicitly selected historical point to its original program inputs.

This is a source-material contract, not restore-chain admission or permission to
run archived containers. The caller retains those gates and the archive lease.
No target policy, Docker tag or current container name participates in selection.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from recovery_archive_versions import resolve_archive_images
from recovery_engine import (RecoveryError, absolute, check_pin, digest, parse,
                             require, signature)
from recovery_minimal_plan import request_contract


ROLES = frozenset(('backend', 'frontend', 'mysql', 'redis', 'minio'))
POLICY_FIELDS = frozenset(('schemaVersion', 'sourceConfigRef', 'roleVersionBindings',
                           'architecture', 'maxArchiveBytes', 'maxImportBytes'))
PIN_FIELDS = frozenset(('path', 'bytes', 'sha256'))
ARCHIVE_NAME = 'original-application-images.tar'
POINT_IDENTITY = ('backupId', 'generationId', 'pointType', 'parentPointPins',
                  'commonRecoveryPoint', 'payloadRefs')


def _text(value):
    return (type(value) is str and 0 < len(value) <= 256 and
            not any(ord(char) < 32 for char in value))


def _version_path(value):
    return (type(value) is list and 0 < len(value) <= 64 and all(
        _text(key) or type(key) is int and 0 <= key < 2**63 for key in value))


def _pin_contract(reference):
    require(type(reference) is dict and set(reference) == PIN_FIELDS and
            type(reference['path']) is str and Path(reference['path']).is_absolute() and
            type(reference['bytes']) is int and 0 <= reference['bytes'] < 2**63 and
            type(reference['sha256']) is str and
            re.fullmatch('[0-9a-f]{64}', reference['sha256']),
            'SOURCE_PROGRAM_PIN_INVALID')


def validate_source_policy(owner, source_ref):
    """Return a detached, complete policy; there are no implicit role bindings."""
    require(type(owner) is dict and type(owner.get('sources')) is dict and
            _text(source_ref) and source_ref in owner['sources'],
            'SOURCE_PROGRAM_POLICIES_INVALID')
    policies = owner.get('sourceProgramArchivePolicies')
    require(policies is not None, 'SOURCE_PROGRAM_POLICY_REQUIRED')
    require(type(policies) is dict and set(policies) <= set(owner['sources']),
            'SOURCE_PROGRAM_POLICIES_INVALID')
    require(source_ref in policies, 'SOURCE_PROGRAM_POLICY_REQUIRED')
    policy = policies[source_ref]
    require(type(policy) is dict and set(policy) == POLICY_FIELDS and
            policy['schemaVersion'] == 'MainProgramSourceArchivePolicy/v1' and
            policy['sourceConfigRef'] == source_ref and
            type(policy['architecture']) is str and
            re.fullmatch('[a-z0-9_]{1,32}', policy['architecture']) and all(
                type(policy[key]) is int and 0 < policy[key] < 2**63
                for key in ('maxArchiveBytes', 'maxImportBytes')),
            'SOURCE_PROGRAM_POLICY_INVALID')
    bindings = policy['roleVersionBindings']
    require(type(bindings) is list and len(bindings) == len(ROLES) and all(
        type(binding) is dict and set(binding) == {'role', 'versionPath'} and
        type(binding['role']) is str and binding['role'] in ROLES and
        _version_path(binding['versionPath']) for binding in bindings),
        'SOURCE_PROGRAM_POLICY_INVALID')
    require({binding['role'] for binding in bindings} == ROLES and
            len({tuple(binding['versionPath']) for binding in bindings}) == len(ROLES),
            'SOURCE_PROGRAM_POLICY_INVALID')
    return deepcopy(policy)


def _original_document(reference):
    """Use the public NAS reader and its 64 MiB limit, with full pin checking."""
    path = absolute(reference['path'])
    before = signature(path.stat())
    raw = check_pin(reference)
    after = signature(path.stat())
    require(before == after and len(raw) == reference['bytes'] and
            hashlib.sha256(raw).hexdigest() == reference['sha256'],
            'SOURCE_PROGRAM_ORIGINAL_PIN_CHANGED')
    return parse(raw)


def _request(request):
    try:
        request_contract(request)
    except RecoveryError as error:
        raise RecoveryError('SOURCE_PROGRAM_REQUEST_INVALID') from error
    require(request['action'] == 'RESTORE' and request['recoveryPointRef'] is not None and
            request['targetConfigRef'] is not None, 'SOURCE_PROGRAM_REQUEST_INVALID')


def _selected_archive(point_pin, point, policy):
    point_path = absolute(point_pin['path'])
    require(point_path.name == 'point.json' and point_path.parent.name == '.repository',
            'SOURCE_PROGRAM_POINT_MISMATCH')
    expected = point_path.parent.parent / 'payload' / ARCHIVE_NAME
    payloads = point.get('payloadRefs')
    require(type(payloads) is list, 'SOURCE_PROGRAM_ARCHIVE_REQUIRED')
    for reference in payloads:
        _pin_contract(reference)
    candidates = [reference for reference in payloads
                  if Path(reference['path']).name == ARCHIVE_NAME]
    require(len(candidates) == 1 and Path(candidates[0]['path']) == expected,
            'SOURCE_PROGRAM_ARCHIVE_REQUIRED')
    archive_pin = candidates[0]
    require(archive_pin['bytes'] > 0, 'SOURCE_PROGRAM_ARCHIVE_REQUIRED')
    require(archive_pin['bytes'] <= policy['maxArchiveBytes'],
            'SOURCE_PROGRAM_ARCHIVE_LIMIT_EXCEEDED')
    # Validate path aliases without reading the binary as a JSON record. Full
    # archive hash/config/layer validation belongs to inspect_program_archive.
    absolute(archive_pin['path'])
    return archive_pin


def resolve_source_program(owner, request, chain, *, guard, reader=None):
    """Bind the last selected point, original archive and all five image roles.

    An injected reader must implement the existing public, pin-verified original
    document contract. Guards wrap every call; reader/guard errors propagate.
    This does not replace lineage, source-scope or restore readback admission.
    """
    require(callable(guard), 'SOURCE_PROGRAM_GUARD_INVALID')
    require(reader is None or callable(reader), 'SOURCE_PROGRAM_READER_INVALID')
    _request(request)
    source_ref = request['sourceConfigRef']
    policy = validate_source_policy(owner, source_ref)
    require(type(chain) in (list, tuple) and chain and
            type(chain[-1]) in (list, tuple) and len(chain[-1]) == 4,
            'SOURCE_PROGRAM_CHAIN_INVALID')
    point_pin, selected_point, selected_material, material_pin = chain[-1]
    source = owner['sources'][source_ref]
    require(type(source) is dict and type(source.get('recoveryPoints')) is dict and
            source['recoveryPoints'].get(request['recoveryPointRef']) == point_pin,
            'SOURCE_PROGRAM_POINT_MISMATCH')
    read = _original_document if reader is None else reader

    def document(reference):
        guard()
        _pin_contract(reference)
        value = read(deepcopy(reference))
        guard()
        return value

    guard()
    point = document(point_pin)
    require(type(point) is dict and point == selected_point and
            point.get('schemaVersion') == 'RepositoryPoint/v1' and
            all(key in point for key in POINT_IDENTITY), 'SOURCE_PROGRAM_POINT_MISMATCH')
    manifest_pin = point.get('manifestPin')
    manifest = document(manifest_pin)
    require(type(manifest) is dict and manifest.get('schemaVersion') == 'RepositoryManifest/v1' and
            all(key in manifest and manifest[key] == point[key] for key in POINT_IDENTITY),
            'SOURCE_PROGRAM_MANIFEST_MISMATCH')
    bindings = source.get('repositoryBindingPinsByManifestSha256')
    require(type(bindings) is dict and manifest_pin['sha256'] in bindings,
            'SOURCE_PROGRAM_BINDING_MISMATCH')
    binding_pin = bindings[manifest_pin['sha256']]
    binding = document(binding_pin)
    require(type(binding) is dict and binding.get('schemaVersion') == 'RecoveryRepositoryBinding/v1' and
            binding.get('repositoryPointPin') == point_pin and
            binding.get('manifestPin') == manifest_pin and
            binding.get('backupId') == point['backupId'] and
            binding.get('generationId') == point['generationId'],
            'SOURCE_PROGRAM_BINDING_MISMATCH')
    require(binding.get('recoveryMaterialPin') == material_pin, 'SOURCE_PROGRAM_MATERIAL_MISMATCH')
    material = document(material_pin)
    require(type(material) is dict and material == selected_material and
            material.get('schemaVersion') == 'RecoveryMaterial/v1' and
            material.get('manifestPin') == manifest_pin and
            material.get('pointType') == point['pointType'] and
            material.get('recoveryPoint') == point['commonRecoveryPoint'] and
            'versionPins' in manifest and material.get('versionPins') == manifest['versionPins'] and
            material.get('payloadPins') == point['payloadRefs'],
            'SOURCE_PROGRAM_MATERIAL_MISMATCH')
    archive_pin = _selected_archive(point_pin, point, policy)
    version_bindings = resolve_archive_images(material['versionPins'], policy['roleVersionBindings'],
        reader=document, mismatch_code='SOURCE_PROGRAM_IMAGE_BINDING_MISMATCH')
    guard()
    return deepcopy(dict(schemaVersion='MainProgramSourceArchive/v1', sourceConfigRef=source_ref,
        recoveryPointRef=request['recoveryPointRef'], recoveryPoint=point['commonRecoveryPoint'],
        selectedPointPin=point_pin, manifestPin=manifest_pin, repositoryBindingPin=binding_pin,
        materialPin=material_pin, policySha256=digest(policy),
        roleImages={role: value['imageId'] for role, value in version_bindings.items()},
        versionBindings=version_bindings, archivePin=archive_pin, architecture=policy['architecture'],
        maxArchiveBytes=policy['maxArchiveBytes'], maxImportBytes=policy['maxImportBytes']))
