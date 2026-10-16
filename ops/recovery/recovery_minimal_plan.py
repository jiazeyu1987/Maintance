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
    require(type(value) is dict and value.get('schemaVersion') == 'RecoveryMinimalConfiguration/v1',
            'MINIMAL_CONFIGURATION_INVALID')
    absolute(value['operationsRoot'])
    require(type(value['deadlineMilliseconds']) is int and 1 <= value['deadlineMilliseconds'] <= 7200000,
            'DEADLINE_INVALID')
    require(type(value['sources']) is dict and value['sources'] and type(value['targets']) is dict,
            'EXPLICIT_SOURCE_AND_TARGET_REGISTRY_REQUIRED')
    for source in value['sources'].values():
        require(type(source) is dict and all(type(source.get(key)) is list and
                all(type(path) is str for path in source[key]) for key in ('sourcePaths', 'archiveRoots')),
                'EXPLICIT_SOURCE_AND_ARCHIVE_PATHS_REQUIRED')
    for target in value['targets'].values():
        require(type(target) is dict and type(target.get('dataRoot')) is str and
                type(target.get('dataPaths')) is list and target['dataPaths'], 'EXPLICIT_TARGET_PATHS_REQUIRED')
    check_pin(value['pythonPin'], content=False)
    require(type(value['maxChainLength']) is int and 1 <= value['maxChainLength'] <= 10000,
            'CHAIN_LENGTH_LIMIT_INVALID')


def disjoint(left, right):
    a, b = absolute(str(left)), absolute(str(right))
    return not (a == b or a.is_relative_to(b) or b.is_relative_to(a))


def selected_chain(configuration, request):
    """Pins identify bytes, not approvals. Keep W03's material/index unchanged."""
    require(request['action'] == 'RESTORE', 'CAPTURE_ACTION_REQUIRES_W03_ENTRY')
    require(request['sourceConfigRef'] in configuration['sources'], 'SOURCE_NOT_REGISTERED')
    source = configuration['sources'][request['sourceConfigRef']]
    require(request['recoveryPointRef'] in source['recoveryPoints'], 'RECOVERY_POINT_NOT_REGISTERED')
    candidate = source['recoveryPoints'][request['recoveryPointRef']]
    catalog = {ref['sha256']: ref for ref in source['repositoryPointPins']}
    require(len(catalog) == len(source['repositoryPointPins']), 'POINT_CATALOG_DUPLICATE')
    roots = [absolute(path) for path in source['archiveRoots']]
    require(roots, 'ARCHIVE_ROOT_REQUIRED')
    policy = dict(source, maxChainLength=configuration['maxChainLength'])
    chain, visiting = [], set()
    identity = pinned_json(pinned_json(source['sourceScopePin'])['sourceIdentityPin'])

    def visit(ref):
        require(catalog.get(ref['sha256']) == ref, 'POINT_NOT_IN_CONFIGURED_REPOSITORY')
        require(ref['sha256'] not in visiting, 'CHAIN_CYCLE')
        require(len(visiting) < configuration['maxChainLength'], 'CHAIN_LENGTH_LIMIT')
        visiting.add(ref['sha256'])
        require(any(absolute(ref['path']).is_relative_to(root) for root in roots), 'POINT_OUTSIDE_ARCHIVE')
        point = pinned_json(ref)
        require(point['schemaVersion'] == 'RepositoryPoint/v1' and point['pointType'] in ('FULL', 'INCREMENTAL'),
                'REPOSITORY_POINT_INVALID')
        manifest = pinned_json(point['manifestPin'])
        require(manifest['schemaVersion'] == 'RepositoryManifest/v1' and all(
            manifest[key] == point[key] for key in ('backupId', 'generationId', 'pointType',
                'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')), 'MANIFEST_POINT_MISMATCH')
        archive = archived_tree(point, manifest)
        require(any(archive.is_relative_to(root) for root in roots), 'MATERIAL_OUTSIDE_ARCHIVE')
        _, binding = repository_binding(ref, point, policy)
        material_ref = binding['recoveryMaterialPin']; material = pinned_json(material_ref)
        require(material['schemaVersion'] == 'RecoveryMaterial/v1' and
                material['manifestPin'] == point['manifestPin'] and material['pointType'] == point['pointType'] and
                material['recoveryPoint'] == point['commonRecoveryPoint'] and
                material['payloadPins'] == point['payloadRefs'] and
                material['sourceScopePin'] == source['sourceScopePin'] and
                manifest['sourceIdentityPin'] == pinned_json(source['sourceScopePin'])['sourceIdentityPin'] and
                material['sourceFingerprint'] == identity['sourceFingerprint'] and
                material['sourceDatabaseUuid'] == identity['databaseUuid'], 'MATERIAL_SOURCE_OR_POINT_MISMATCH')
        require(material['versionPins'] and material['versionPins'] == manifest['versionPins'],
                'ARCHIVED_APPLICATION_VERSION_REQUIRED')
        for version in material['versionPins']:
            check_pin(version, content=False)
        if point['pointType'] == 'FULL':
            require(not point['parentPointPins'] and material['database']['startPosition'] is None and
                    material['database']['method'] == 'FORMAL_SQL_FULL', 'FULL_BASELINE_INVALID')
        else:
            require(point['parentPointPins'] and material['database']['method'] in ('BINLOG_SQL', 'MYSQL_BINLOG'),
                    'REAL_INCREMENTAL_REQUIRED')
            visit(point['parentPointPins'][-1])
            require(point['parentPointPins'] == [item[0] for item in chain], 'COMPLETE_PARENT_PREFIX_REQUIRED')
            require(chain[-1][1]['generationId'] == point['generationId'] and
                    chain[-1][2]['database']['endPosition'] == material['database']['startPosition'],
                    'DATABASE_LOG_GAP_OR_GENERATION_CHANGED')
        validate_material(material, full=point['pointType'] == 'FULL')
        chain.append((ref, point, material, material_ref))

    visit(candidate)
    require(len({item[1]['backupId'] for item in chain}) == len(chain), 'POINT_IDENTITY_DUPLICATE')
    if request['parentChainRef'] is not None:
        require(source['parentChains'].get(request['parentChainRef']) == [item[0] for item in chain[:-1]],
                'SELECTED_PARENT_CHAIN_MISMATCH')
    physical = [item[2]['objects']['method'] == 'PHYSICAL_FILES' for item in chain]
    require(all(physical) or not any(physical), 'MIXED_PHYSICAL_AND_LOGICAL_OBJECT_CHAIN_UNSUPPORTED')
    object_index_chain(chain, policy)
    if all(physical):
        from recovery_data_files import physical_chain_inputs
        physical_chain_inputs(chain)
    return source, policy, chain


def target_configuration(configuration, request, source):
    reference = request['targetConfigRef']
    require(reference is not None and reference != request['sourceConfigRef'] and
            reference in configuration['targets'], 'NEW_TARGET_REFERENCE_REQUIRED')
    target = configuration['targets'][reference]
    require({'targetId', 'sourceConfigRef', 'dataRoot', 'dataPaths', 'machineId', 'dockerEngineId',
             'networkId', 'database', 'buckets', 'services', 'dockerPin', 'iptablesPin', 'redisClientPath',
             'dataPolicy', 'secrets', 'bucketProtection', 'application'} <= set(target),
            'RESTORE_TARGET_CONFIGURATION_INCOMPLETE')
    require(target['sourceConfigRef'] == request['sourceConfigRef'], 'TARGET_SOURCE_MISMATCH')
    require(target['targetId'] != request['sourceConfigRef'], 'SOURCE_TARGET_OVERLAP')
    root = absolute(target['dataRoot'])
    require(root.is_dir() and type(target['dataPaths']) is list and target['dataPaths'], 'TARGET_DATA_PATHS_REQUIRED')
    for candidate in [str(root), *target['dataPaths']]:
        require(all(disjoint(candidate, path) for path in source['sourcePaths'] + source['archiveRoots'] +
                    [configuration['operationsRoot']]), 'TARGET_DATA_PATH_OVERLAP')
    ids = [item['id'] for item in target['services']]
    require(len(ids) == len(set(ids)) and all(re.fullmatch('[0-9a-f]{64}', value) for value in ids) and
            not set(ids) & set(source['sourceContainerIds']), 'SOURCE_CONTAINER_TARGET_REJECTED')
    roles = [item['role'] for item in target['services']]
    require(len(roles) == len(set(roles)) and {'mysql', 'minio', 'redis'} < set(roles), 'TARGET_SERVICES_REQUIRED')
    require(target['networkId'] not in source['sourceNetworkIds'], 'SOURCE_NETWORK_TARGET_REJECTED')
    return target
