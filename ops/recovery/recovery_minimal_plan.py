"""Resolve existing W03 repository records without the retired signing gates."""
from pathlib import Path
import re

from recovery_engine import absolute, check_pin, pinned_json, require
from recovery_plan import validate_material
from recovery_plan_objects import object_index_chain, repository_binding
from recovery_plan_tree import archived_tree


UI_FIELDS = {'schemaVersion', 'operationId', 'action', 'sourceConfigRef',
             'parentChainRef', 'recoveryPointRef', 'targetConfigRef'}


def request_contract(request):
    require(type(request) is dict and set(request) == UI_FIELDS and
            request['schemaVersion'] == 'SmallAppBackupUiRequest/v1' and
            request['action'] in ('FULL', 'INCREMENTAL', 'RESTORE'), 'MINIMAL_REQUEST_INVALID')
    require(type(request['operationId']) is str and
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', request['operationId']), 'OPERATION_ID_INVALID')
    for key in UI_FIELDS - {'schemaVersion', 'operationId', 'action'}:
        value = request[key]
        require(value is None or type(value) is str and 0 < len(value) <= 256 and
                not any(ord(c) < 32 for c in value), 'CONFIGURATION_REFERENCE_INVALID')
    require(request['sourceConfigRef'] is not None, 'SOURCE_REFERENCE_REQUIRED')


def configuration_contract(value):
    absolute(value['operationsRoot'])


def disjoint(left, right):
    a, b = absolute(str(left)), absolute(str(right))
    return not (a == b or a.is_relative_to(b) or b.is_relative_to(a))


def selected_chain(configuration, request):
    """Follow the selected ancestry; do not validate lineage, source or payloads."""
    source = configuration['sources'][request['sourceConfigRef']]
    policy = dict(source, maxChainLength=configuration['maxChainLength'])
    reference = source['recoveryPoints'][request['recoveryPointRef']]
    chain, seen = [], set()
    while reference is not None:
        # A cycle has no executable ordering; stop instead of looping forever.
        key = reference['path']
        if key in seen:
            raise ValueError('Recovery ancestry has no finite ordering')
        seen.add(key)
        point = pinned_json(reference)
        binding = pinned_json(source['repositoryBindingPinsByManifestSha256'][point['manifestPin']['sha256']])
        material_ref = binding['recoveryMaterialPin']
        chain.append((reference, point, pinned_json(material_ref), material_ref))
        reference = point['parentPointPins'][-1] if point['pointType'] != 'FULL' else None
    chain.reverse()
    return source, policy, chain


def target_configuration(configuration, request, source):
    return configuration['targets'][request['targetConfigRef']]
