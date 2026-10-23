"""ApplicationRegistration metadata import into the existing private registry.

Metadata cannot publish resources, issue authority or prove an installation.
Every executable selection is rebound to authenticated actual owner originals.
"""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import os
import re

import recovery_control_executor as executor
from recovery_control_smallapp import (BATCH, ROOT, Failure, canonical, exact, local_read, need, opaque,
    persist, public_error, sync_directory)

FIELDS = ('schemaVersion schemaRevision requiredComponents applicationId displayName batchId engineSelectionRef '
          'sourceConfigRef source runtime redisRecovery secretReferences archive allowedRestoreTargets schedule retention evidencePins')
REVISION = 'three-component-20261014-r1'
REDIS_FIELDS = ('state role configRef instanceId containerId endpoint databaseIndex keyPrefix serverVersion runtimeConfigurationPin '
                'secretRole secretReference resourceProofPin applicationUseProofPin')
ENGINE_FIELDS = 'engineSelectionRef engineArtifactPin engineVersionPin engineEntryPin'
CHOICE_FIELDS = ('applicationId sourceConfigRef engineSelectionRef fullReady fullErrorCode parentChainRefs '
                 'recoveryPointRefs freshTargetConfigRefs')


def optional_reference(value):
    if value is not None:
        opaque(value)


def optional_pin(value):
    if value is not None:
        executor.pin_reference(value)


def text(value):
    need(value is None or type(value) is str and value and not any(ord(c) < 32 for c in value),
         'REGISTRATION_TEXT_INVALID')


def no_secret(value):
    forbidden = {'password', 'passwordhash', 'password_hash', 'token', 'accesstoken', 'accesskey',
        'secretkey', 'privatekey', 'connectionstring', 'authkeybase64', 'controltoken', 'signature'}
    if type(value) is dict:
        for key, item in value.items():
            need(key.lower() not in forbidden, 'REGISTRATION_SECRET_MATERIAL_REFUSED'); no_secret(item)
    elif type(value) is list:
        for item in value:
            no_secret(item)
    elif type(value) is str:
        need(not re.search(r'://[^/\s]*@', value), 'REGISTRATION_CREDENTIAL_URL_REFUSED')


def metadata(value):
    """Validate W08's actual exact structure without treating evidence paths as live proof."""
    exact(value, FIELDS, 'REGISTRATION_FIELDS_INVALID'); no_secret(value)
    need(value['schemaVersion'] == 'ApplicationRegistration/v1' and value['batchId'] == BATCH,
         'REGISTRATION_BATCH_INVALID')
    need(value['schemaRevision'] == REVISION and value['requiredComponents'] == ['MySQL', 'MinIO', 'Redis'],
         'COMPONENT_CONTRACT_INVALID')
    opaque(value['applicationId']); text(value['displayName'])
    need(value['displayName'] is not None, 'REGISTRATION_NAME_REQUIRED')
    optional_reference(value['engineSelectionRef']); optional_reference(value['sourceConfigRef'])
    source = value['source']
    exact(source, 'hostAddress root database objects redis assetInventory resourceBindingPin nativeConfigPin',
          'REGISTRATION_SOURCE_FIELDS_INVALID')
    for key in ('hostAddress', 'root'):
        text(source[key])
    for key in ('resourceBindingPin', 'nativeConfigPin'):
        optional_pin(source[key])
    for lane, fields in (('database', 'name state serverUuid containerId endpoint tableNames coveragePin'),
                         ('objects', 'bucket state keyPrefix containerId endpoint coveragePin')):
        item = source[lane]; exact(item, fields, 'REGISTRATION_ASSET_FIELDS_INVALID')
        need(item['state'] in ('UNCONFIGURED', 'PROPOSED_NOT_ALLOCATED', 'OBSERVED_ALLOCATED'),
             'REGISTRATION_ASSET_STATE_INVALID')
        optional_pin(item['coveragePin'])
        need(item['state'] != 'UNCONFIGURED' or item['coveragePin'] is None,
             'REGISTRATION_UNKNOWN_COVERAGE_REFUSED')
        for key, val in item.items():
            if key not in ('coveragePin', 'tableNames'):
                text(val)
        if lane == 'database':
            need(type(item['tableNames']) is list and len(set(item['tableNames'])) == len(item['tableNames']) and
                 all(type(name) is str and re.fullmatch('[a-zA-Z0-9_]+', name) for name in item['tableNames']),
                 'REGISTRATION_TABLE_INVENTORY_INVALID')
    inventory = source['assetInventory']
    exact(inventory, 'state applicationFilePins applicationDeliveryPin runtimeClosurePin writerInventoryPin capturedInventoryPin',
          'REGISTRATION_INVENTORY_FIELDS_INVALID')
    need(inventory['state'] in ('UNCONFIGURED', 'OBSERVED_WORKING_SOURCE_INSTALL_PENDING', 'OWNER_DELIVERED') and
         type(inventory['applicationFilePins']) is list, 'REGISTRATION_INVENTORY_STATE_INVALID')
    for item in inventory['applicationFilePins']:
        executor.pin_reference(item)
    for key in ('applicationDeliveryPin', 'runtimeClosurePin', 'writerInventoryPin', 'capturedInventoryPin'):
        optional_pin(inventory[key])
    runtime = value['runtime']
    exact(runtime, 'version pythonPin dependencyNames dependencyClosurePin configurationPin startupDescriptorPin '
          'quiescenceDescriptorPin sourceConfigurationFields', 'REGISTRATION_RUNTIME_FIELDS_INVALID')
    text(runtime['version'])
    need(type(runtime['dependencyNames']) is list and all(type(name) is str and name for name in runtime['dependencyNames']),
         'REGISTRATION_DEPENDENCIES_INVALID')
    for key in ('pythonPin', 'dependencyClosurePin', 'configurationPin', 'startupDescriptorPin', 'quiescenceDescriptorPin'):
        optional_pin(runtime[key])
    need(runtime['sourceConfigurationFields'] is None or type(runtime['sourceConfigurationFields']) is dict,
         'REGISTRATION_RUNTIME_CONFIG_INVALID')
    need(type(value['secretReferences']) is list, 'REGISTRATION_SECRET_REFS_INVALID')
    roles = set()
    for item in value['secretReferences']:
        exact(item, 'role reference state resolverOwner', 'REGISTRATION_SECRET_REF_FIELDS_INVALID')
        opaque(item['role']); text(item['reference'])
        need(item['role'] not in roles and item['resolverOwner'] == 'W05' and
             item['state'] in ('UNCONFIGURED', 'GENERATED_UNRESOLVED', 'OWNER_BOUND') and
             (item['reference'] is None) == (item['state'] == 'UNCONFIGURED'), 'REGISTRATION_SECRET_REF_STATE_INVALID')
        roles.add(item['role'])
    archive = value['archive']
    exact(archive, 'root repositoryId servicePin policyPin fullParentChainRef recoveryPointRef independentReadbackRequired',
          'REGISTRATION_ARCHIVE_FIELDS_INVALID')
    text(archive['root'])
    need(archive['independentReadbackRequired'] is True, 'REGISTRATION_READBACK_REQUIRED')
    for key in ('repositoryId', 'fullParentChainRef', 'recoveryPointRef'):
        optional_reference(archive[key])
    for key in ('servicePin', 'policyPin'):
        optional_pin(archive[key])
    need(type(value['allowedRestoreTargets']) is list, 'REGISTRATION_TARGETS_INVALID')
    targets = set()
    for target in value['allowedRestoreTargets']:
        exact(target, 'configRef hostAddress root resourceBindingPin nativeConfigPin freshnessProofPin allowedModes redis',
              'REGISTRATION_TARGET_FIELDS_INVALID')
        opaque(target['configRef'])
        need(target['configRef'] not in targets and target['configRef'] != value['sourceConfigRef'] and
             target['allowedModes'] == ['REHEARSAL'], 'REGISTRATION_TARGET_CONFLICT')
        targets.add(target['configRef'])
        for key in ('hostAddress', 'root'):
            text(target[key])
        for key in ('resourceBindingPin', 'nativeConfigPin', 'freshnessProofPin'):
            optional_pin(target[key])
    exact(value['schedule'], 'state timezone fullFrequency incrementalFrequency', 'REGISTRATION_SCHEDULE_FIELDS_INVALID')
    exact(value['retention'], 'state policyPin configuration', 'REGISTRATION_RETENTION_FIELDS_INVALID')
    for lane in ('schedule', 'retention'):
        item = value[lane]
        need(item['state'] in ('UNCONFIGURED', 'CONFIGURED') and all(
            (val is None) == (item['state'] == 'UNCONFIGURED') for key, val in item.items() if key != 'state'),
            'REGISTRATION_POLICY_STATE_INVALID')
    for key in ('timezone', 'fullFrequency', 'incrementalFrequency'):
        text(value['schedule'][key])
    optional_pin(value['retention']['policyPin'])
    need(value['retention']['configuration'] is None or type(value['retention']['configuration']) is dict,
         'REGISTRATION_RETENTION_INVALID')
    need(type(value['evidencePins']) is dict and value['evidencePins'], 'REGISTRATION_EVIDENCE_REQUIRED')
    for item in value['evidencePins'].values():
        executor.pin_reference(item)
    redis_metadata(value)
    return value


def redis_metadata(value):
    roles = {item['role']: item for item in value['secretReferences']}
    source = value['source']['redis']
    for instance, role, reference in [(source, 'SOURCE', value['sourceConfigRef']),
        *[(item['redis'], 'TARGET', item['configRef']) for item in value['allowedRestoreTargets']]]:
        exact(instance, REDIS_FIELDS, 'REGISTRATION_REDIS_FIELDS_INVALID')
        need(instance['role'] == role and instance['configRef'] == reference, 'REDIS_ROLE_OR_CONFIG_REFERENCE_MISMATCH')
        need(instance['state'] in ('UNCONFIGURED', 'OBSERVED_ALLOCATED'), 'REDIS_STATE_INVALID')
        optional_reference(instance['configRef']); optional_reference(instance['secretRole']); text(instance['secretReference'])
        for key in ('instanceId', 'containerId', 'endpoint', 'keyPrefix', 'serverVersion'):
            text(instance[key])
        prefix = instance['keyPrefix']
        need(prefix is None or not any(c in prefix for c in '*?[]'), 'REDIS_KEY_PREFIX_INVALID')
        need(instance['databaseIndex'] is None or type(instance['databaseIndex']) is int and instance['databaseIndex'] >= 0,
             'REDIS_DATABASE_INDEX_INVALID')
        for key in ('runtimeConfigurationPin', 'resourceProofPin', 'applicationUseProofPin'):
            optional_pin(instance[key])
        need(instance['secretRole'] is None or instance['secretRole'] in roles, 'REDIS_SECRET_ROLE_NOT_REGISTERED')
        if instance['state'] == 'UNCONFIGURED':
            need(instance['resourceProofPin'] is None and instance['applicationUseProofPin'] is None,
                 'UNKNOWN_REDIS_CANNOT_HAVE_PROOF')
        else:
            need((instance['containerId'] is not None or instance['endpoint'] is not None) and all(
                instance[key] is not None for key in ('configRef', 'instanceId', 'databaseIndex', 'keyPrefix', 'serverVersion',
                    'runtimeConfigurationPin', 'secretRole', 'secretReference', 'resourceProofPin')), 'ALLOCATED_REDIS_FIELDS_REQUIRED')
        if role == 'TARGET':
            need(all(instance[key] is None or source[key] is None or instance[key] != source[key]
                 for key in ('containerId', 'endpoint')), 'REDIS_TARGET_REUSES_SOURCE_RESOURCE')
            need(instance['databaseIndex'] is None or source['databaseIndex'] is None or
                 instance['databaseIndex'] == source['databaseIndex'], 'REDIS_TARGET_DATABASE_MISMATCH')
            # W02 r2 explicitly selects different source/target key namespaces.
            if instance['keyPrefix'] is not None and source['keyPrefix'] is not None:
                need(not instance['keyPrefix'].startswith(source['keyPrefix']) and
                     not source['keyPrefix'].startswith(instance['keyPrefix']), 'REDIS_TARGET_KEYSPACE_OVERLAP')
            need(instance['secretReference'] is None or source['secretReference'] is None or
                 instance['secretReference'] != source['secretReference'], 'REDIS_TARGET_REUSES_SOURCE_SECRET')
        elif instance['secretReference'] is not None:
            need(instance['secretRole'] in roles and instance['secretReference'] == roles[instance['secretRole']]['reference'],
                 'REDIS_SOURCE_SECRET_REFERENCE_MISMATCH')
    need(value['runtime']['configurationPin'] is None or source['runtimeConfigurationPin'] is None or
         value['runtime']['configurationPin'] == source['runtimeConfigurationPin'], 'REDIS_RUNTIME_CONFIGURATION_MISMATCH')
    recovery = value['redisRecovery']
    exact(recovery, 'state applicationVersion sourceConfigRef sourceDeliveryPin semanticsPin consumerPin classifications freshTarget',
          'REDIS_RECOVERY_FIELDS_INVALID')
    need(recovery['state'] in ('UNCONFIGURED', 'OWNER_DELIVERED'), 'REDIS_SEMANTICS_STATE_INVALID')
    text(recovery['applicationVersion']); optional_reference(recovery['sourceConfigRef'])
    for key in ('sourceDeliveryPin', 'semanticsPin', 'consumerPin'):
        optional_pin(recovery[key])
    fresh = recovery['freshTarget']
    exact(fresh, 'initialState startupState reloginRequired policyPin', 'REDIS_TARGET_POLICY_FIELDS_INVALID')
    optional_pin(fresh['policyPin'])
    need(type(recovery['classifications']) is list, 'REDIS_CLASSIFICATIONS_INVALID')
    if recovery['state'] == 'UNCONFIGURED':
        need(all(recovery[key] is None for key in ('applicationVersion', 'sourceConfigRef', 'sourceDeliveryPin',
            'semanticsPin', 'consumerPin')) and recovery['classifications'] == [] and all(v is None for v in fresh.values()),
            'UNCONFIGURED_REDIS_SEMANTICS_HAS_VALUES')
        return
    need(all(recovery[key] is not None for key in ('applicationVersion', 'sourceConfigRef', 'sourceDeliveryPin',
        'semanticsPin', 'consumerPin')) and recovery['classifications'] and source['keyPrefix'] is not None,
        'DELIVERED_REDIS_SEMANTICS_FIELDS_REQUIRED')
    need(recovery['applicationVersion'] == value['runtime']['version'] and
         recovery['sourceConfigRef'] == value['sourceConfigRef'] and
         recovery['sourceDeliveryPin'] == value['source']['assetInventory']['applicationDeliveryPin'] and
         recovery['sourceDeliveryPin'] != value['evidencePins'].get('historicalTwoComponentSourceDelivery'),
         'REDIS_SEMANTICS_SOURCE_MISMATCH')
    names, patterns, treatments = set(), [], set()
    for item in recovery['classifications']:
        exact(item, 'dataClass keyPatterns treatment authoritativeSources recipePin', 'REDIS_CLASSIFICATION_FIELDS_INVALID')
        opaque(item['dataClass']); need(item['dataClass'] not in names, 'REDIS_CLASSIFICATION_DUPLICATE'); names.add(item['dataClass'])
        need(item['treatment'] in ('RECOVER', 'REBUILD', 'RELOGIN'), 'REDIS_CLASSIFICATION_UNKNOWN')
        treatments.add(item['treatment']); authorities = item['authoritativeSources']
        need(type(authorities) is list and authorities and len(set(authorities)) == len(authorities) and
             all(a in ('MYSQL', 'MINIO', 'REDIS') for a in authorities), 'REDIS_AUTHORITY_INVALID')
        need((item['treatment'] != 'RECOVER' or 'REDIS' in authorities) and
             (item['treatment'] != 'REBUILD' or 'REDIS' not in authorities), 'REDIS_TREATMENT_AUTHORITY_CONFLICT')
        keys = item['keyPatterns']
        need(type(keys) is list and keys and all(type(k) is str and k.startswith(source['keyPrefix']) and
             not any(ord(c) < 32 or c in '?[]' for c in k) and
             ('*' not in k or k.endswith('*') and k.count('*') == 1) for k in keys), 'REDIS_KEY_SCOPE_INVALID')
        for key in keys:
            need(not any(key == old or key.endswith('*') and old.startswith(key[:-1]) or
                old.endswith('*') and key.startswith(old[:-1]) for old in patterns), 'REDIS_KEY_CLASS_OVERLAP')
            patterns.append(key)
        executor.pin_reference(item['recipePin'])
    need(fresh['initialState'] == ('RESTORE_REQUIRED' if 'RECOVER' in treatments else 'EMPTY') and
         fresh['startupState'] == 'PROTECTED' and type(fresh['reloginRequired']) is bool and
         ('RELOGIN' not in treatments or fresh['reloginRequired'] is True) and fresh['policyPin'] is not None,
         'REDIS_FRESH_TARGET_POLICY_CONFLICT')


def engine(selection, installation, dispatcher_pin):
    exact(selection, ENGINE_FIELDS, 'ENGINE_SELECTION_FIELDS_INVALID')
    opaque(selection['engineSelectionRef'])
    need(selection['engineEntryPin'] == dispatcher_pin and all(selection[key] in installation['filePins']
         for key in ('engineArtifactPin', 'engineVersionPin', 'engineEntryPin')), 'ENGINE_INSTALLED_MEMBERSHIP_REQUIRED')
    for key in ('engineArtifactPin', 'engineVersionPin', 'engineEntryPin'):
        executor.verify(selection[key])
    return selection


def action_missing(value, action, target_ref=None):
    """Metadata prerequisites only; a zero list is never native readiness."""
    metadata(value)
    need(action in ('FULL', 'INCREMENTAL', 'RESTORE', 'START_APPLICATION'), 'REGISTERED_ACTION_INVALID')
    need(action in ('RESTORE', 'START_APPLICATION') or target_ref is None, 'REGISTERED_TARGET_NOT_APPLICABLE')
    missing = []
    def check(path, item, owner):
        if item is None or item == []:
            missing.append(dict(field=path, owner=owner))
    capture = action in ('FULL', 'INCREMENTAL')
    source_start = action == 'START_APPLICATION' and target_ref is None
    for key in ('sourceConfigRef',):
        check(key, value[key], 'W01/W08')
    for key in ('version', 'pythonPin', 'dependencyNames', 'dependencyClosurePin', 'configurationPin', 'sourceConfigurationFields'):
        check('runtime.' + key, value['runtime'][key], 'W02/W05')
    check('source.assetInventory.applicationDeliveryPin', value['source']['assetInventory']['applicationDeliveryPin'], 'W02/W08')
    check('source.assetInventory.applicationFilePins', value['source']['assetInventory']['applicationFilePins'], 'W02/W05')
    for key in ('resourceBindingPin', 'nativeConfigPin'):
        check('source.' + key, value['source'][key], 'W01/W05')
    if capture or source_start:
        for lane in ('database', 'objects'):
            if value['source'][lane]['state'] != 'OBSERVED_ALLOCATED':
                missing.append(dict(field='source.' + lane + '.state', owner='W05'))
            check('source.' + lane + '.coveragePin', value['source'][lane]['coveragePin'], 'W02/W05')
        for key in ('runtimeClosurePin', 'writerInventoryPin') if capture else ('runtimeClosurePin',):
            check('source.assetInventory.' + key, value['source']['assetInventory'][key], 'W02/W05')
        for key in ('startupDescriptorPin', 'quiescenceDescriptorPin') if capture else ('startupDescriptorPin',):
            check('runtime.' + key, value['runtime'][key], 'W02/W05')
    if action != 'START_APPLICATION':
        for key in ('root', 'repositoryId', 'servicePin', 'policyPin'):
            check('archive.' + key, value['archive'][key], 'W03')
    recovery = value['redisRecovery']
    if recovery['state'] != 'OWNER_DELIVERED':
        missing.append(dict(field='redisRecovery.state', owner='W02/W08'))
    for key in ('applicationVersion', 'sourceConfigRef', 'sourceDeliveryPin', 'semanticsPin', 'consumerPin', 'classifications'):
        check('redisRecovery.' + key, recovery[key], 'W02/W08')
    for key, item in recovery['freshTarget'].items():
        check('redisRecovery.freshTarget.' + key, item, 'W02/W08')
    source = value['source']['redis']
    for key in ('databaseIndex', 'keyPrefix'):
        check('source.redis.' + key, source[key], 'W05/W08')
    target_action = action == 'RESTORE' or action == 'START_APPLICATION' and target_ref is not None
    selected = None
    if target_action:
        if target_ref is None:
            missing.append(dict(field='selectedTargetConfigRef', owner='caller')); return missing
        selected = registered_target(value, target_ref)
        for key in ('resourceBindingPin', 'nativeConfigPin', 'freshnessProofPin'):
            check('allowedRestoreTargets.' + target_ref + '.' + key, selected[key], 'W05/W01')
    instance = selected['redis'] if target_action else source
    path = 'allowedRestoreTargets.' + target_ref + '.redis.' if target_action else 'source.redis.'
    if instance['state'] != 'OBSERVED_ALLOCATED':
        missing.append(dict(field=path + 'state', owner='W05'))
    if instance['containerId'] is None and instance['endpoint'] is None:
        missing.append(dict(field=path + 'containerIdOrEndpoint', owner='W05'))
    for key in ('instanceId', 'databaseIndex', 'keyPrefix', 'serverVersion', 'runtimeConfigurationPin', 'secretRole', 'secretReference', 'resourceProofPin'):
        check(path + key, instance[key], 'W05')
    if capture:
        check(path + 'applicationUseProofPin', instance['applicationUseProofPin'], 'W05/W06')
    roles = {item['role']: item for item in value['secretReferences']}
    required_roles = [] if target_action else [instance['secretRole']]
    fields = value['runtime']['sourceConfigurationFields']
    if (capture or source_start) and fields is not None:
        need(type(fields.get('secretRefs')) is dict, 'REGISTERED_SECRET_ROLE_FIELDS_INVALID')
        required_roles.extend(fields['secretRefs'].values())
    for role in set(required_roles):
        if role not in roles or roles[role]['state'] != 'OWNER_BOUND':
            missing.append(dict(field=path + 'secretReference.' + str(role), owner='W05'))
    # The actual UI request supplies selected parent/point; never invent future
    # points or require a full target for FULL. Native resolves those real refs.
    return missing


def source_metadata_gate(value, action='FULL', target_ref=None):
    metadata(value)
    if action == 'RESTORE' or action == 'START_APPLICATION' and target_ref is not None:
        need(not action_missing(value, action, target_ref), 'REGISTERED_ACTION_INPUTS_UNCONFIGURED')
        return
    need(value['sourceConfigRef'] is not None and value['runtime']['version'] is not None and
         all(value['source'][lane]['state'] == 'OBSERVED_ALLOCATED' and value['source'][lane]['coveragePin'] is not None
             for lane in ('database', 'objects')) and value['source']['assetInventory']['state'] == 'OWNER_DELIVERED',
         'REGISTERED_SOURCE_NOT_INSTALLED')
    need(not action_missing(value, action, target_ref), 'REGISTERED_ACTION_INPUTS_UNCONFIGURED')
    need(value['source']['database']['tableNames'], 'REGISTERED_ASSET_INPUTS_UNCONFIGURED')


def source_binding_inputs(value, action, target_ref=None):
    """Select actual originals for this phase before any native reads."""
    need(action in ('FULL', 'INCREMENTAL', 'RESTORE', 'START_APPLICATION'), 'REGISTERED_ACTION_INVALID')
    source, runtime = value['source'], value['runtime']
    source_start = action == 'START_APPLICATION' and target_ref is None
    originals = [source['assetInventory']['applicationDeliveryPin'], runtime['dependencyClosurePin']]
    if action in ('FULL', 'INCREMENTAL') or source_start:
        originals.extend([source['database']['coveragePin'], source['objects']['coveragePin'],
                          source['assetInventory']['runtimeClosurePin'], runtime['startupDescriptorPin']])
    if action in ('FULL', 'INCREMENTAL'):
        originals.extend([source['assetInventory']['writerInventoryPin'], runtime['quiescenceDescriptorPin']])
    return originals, not source_start


def nonoverlap(source, target):
    need(target['sourceIdentityPin'] == source['sourceIdentityPin'] and target['fresh'] is True and
         target['databaseUuid'] != source['databaseUuid'] and
         all(target[key] != source[key] for key in ('identityPin', 'databaseContainerId', 'objectContainerId',
                                                   'applicationContainerId')), 'SOURCE_TARGET_NOT_DISJOINT')


def redis_semantic_policy(value, delivery, semantics, policy, recipe):
    """Check the original r2 recipe contents separately from native Pin custody."""
    recovery, runtime = value['redisRecovery'], value['runtime']
    same = lambda a, b: a['bytes'] == b['bytes'] and a['sha256'] == b['sha256']
    need(semantics['schemaVersion'] == 'SmallAppRecoverySemantics/v1' and policy['schemaVersion'] ==
         'SmallAppRedisRecoveryPolicy/v1' and semantics['version'] == policy['version'] == runtime['version'],
         'REGISTERED_REDIS_SEMANTIC_VERSION_MISMATCH')
    redis = policy['redis']
    need(redis['classification'] == 'REBUILD' and redis['requiredForBusiness'] is True and
         redis['rebuildFrom'] == 'DATABASE' and redis['captureRedisPayload'] is False and
         redis['executorKey'] == 'smallapp.redis-session-cache.mysql.v1' and
         len(recovery['classifications']) == 1 and all(item['dataClass'] == 'redis' and item['treatment'] == 'REBUILD' and
             item['authoritativeSources'] == ['MYSQL'] and item['keyPatterns'] == [value['source']['redis']['keyPrefix'] + '*'] and
             same(item['recipePin'], delivery['existingDerivedAdapterContractPin']) for item in recovery['classifications']) and
         recovery['freshTarget']['initialState'] == 'EMPTY' and recovery['freshTarget']['startupState'] == 'PROTECTED' and
         recovery['freshTarget']['reloginRequired'] is True and semantics['restoreExpectations']['freshTargetLogin'],
         'REGISTERED_REDIS_ENGINE_RECIPE_UNSUPPORTED')
    need(recipe['schemaVersion'] == 'SmallAppExistingDerivedAdapterContract/v1' and
         recipe['version'] == runtime['version'] and recipe['className'] == 'redis' and
         recipe['classification'] == redis['classification'] and recipe['rebuildFrom'] == redis['rebuildFrom'] and
         recipe['executorKey'] == redis['executorKey'] and same(recipe['policyPin'], delivery['redisPolicyPin']) and
         same(recipe['cacheSourcePin'], recovery['consumerPin']), 'REGISTERED_REDIS_ADAPTER_CONTRACT_MISMATCH')
    return policy


def registered_source(records, config_ref):
    refs = [value['sourceConfigRef'] for value in records if value['sourceConfigRef'] is not None]
    need(len(refs) == len(set(refs)), 'REGISTERED_SOURCE_AMBIGUOUS')
    matches = [value for value in records if value['sourceConfigRef'] == config_ref]
    need(len(matches) == 1, 'SOURCE_NOT_REGISTERED')
    return matches[0]


def registered_target(value, config_ref):
    matches = [target for target in value['allowedRestoreTargets'] if target['configRef'] == config_ref]
    need(len(matches) == 1, 'TARGET_NOT_REGISTERED_FOR_SOURCE')
    return matches[0]


def blocked_choice(value, error_code):
    return dict(applicationId=value['applicationId'], sourceConfigRef=value['sourceConfigRef'],
        engineSelectionRef=None, fullReady=False, fullErrorCode=error_code, parentChainRefs=[],
        recoveryPointRefs=[], freshTargetConfigRefs=[])


def inside(value):
    path = PurePosixPath(value)
    need(path.is_absolute() and PurePosixPath(ROOT) in path.parents and not {'.', '..'} & set(value.split('/')) and
         '\\' not in value and '//' not in value, 'REGISTERED_ROOT_OUTSIDE_SCOPE')


def publish_registration(path, registration_pin, expected_pin):
    """Exact CAS under a private native import lock; preserve prior selected original."""
    if path.exists():
        previous = local_read(path)
        if previous == registration_pin:
            return
        need(expected_pin is not None and previous == expected_pin, 'REGISTRATION_REPLACEMENT_EXPECTED_PIN_REQUIRED')
        history = path.parent / (path.name[:-9] + '-' + previous['sha256'] + '.previous.json')
        if history.exists():
            need(local_read(history) == previous, 'REGISTRATION_HISTORY_CHANGED')
        else:
            persist(history, previous)
        temporary = path.with_name(path.name + '-' + registration_pin['sha256'] + '.pending')
        persist(temporary, registration_pin)
        os.replace(temporary, path); sync_directory(path.parent)
    else:
        need(expected_pin is None, 'REGISTRATION_EXPECTED_ORIGINAL_MISSING')
        persist(path, registration_pin)


class Registry:
    def __init__(self, native, config):
        self.native, self.config = native, config
        self.root = Path(config['registryRoot'])

    def registrations(self):
        values = []
        for path in sorted((self.root / 'applications').iterdir()):
            if path.name.endswith('.previous.json') or path.name == 'import.lock':
                continue
            need(path.name.endswith('.pin.json'), 'REGISTRATION_SELECTOR_FILE_INVALID')
            reference = opaque(path.name[:-9])
            selected = self.native.selector(self.root / 'applications', reference)
            value = metadata(self.native.document(selected))
            need(value['applicationId'] == reference, 'REGISTRATION_APPLICATION_ID_MISMATCH')
            values.append(value)
        refs = [value['sourceConfigRef'] for value in values if value['sourceConfigRef'] is not None]
        need(len(refs) == len(set(refs)), 'REGISTERED_SOURCE_AMBIGUOUS')
        return values

    def source(self, config_ref):
        return registered_source(self.registrations(), config_ref)

    def target(self, value, config_ref):
        return registered_target(value, config_ref)

    def bind_host(self, resource, host_pin=None):
        native_config = self.native.document(resource['nativeConfigPin'])
        # Frozen RecoveryEnvironmentConfig has no executionHostPin. The actual
        # host comes from the registered archive service and later from the
        # independently authenticated per-operation dispatch/context.
        if resource['role'] == 'SOURCE':
            host_pin = native_config['executionHostPin']
        else:
            need(host_pin is not None, 'REGISTERED_TARGET_HOST_REQUIRED')
        host = self.native.document(host_pin)
        actual_identity = self.native.document(resource['hostIdentityPin'])
        need(host['installationManifestPin'] == self.config['installationPin'] and
             host['dispatcherPin'] == self.config['engineSelection']['engineEntryPin'] and
             host['pythonPin'] == resource['runtimePin'] and
             all(actual_identity[key] == host[key] for key in ('hostId', 'bootId')),
             'REGISTERED_INSTALLED_HOST_MISMATCH')
        return native_config

    def bind_semantics(self, value, resource):
        recovery = value['redisRecovery']; runtime = value['runtime']
        delivery = self.native.document(recovery['sourceDeliveryPin'])
        need(delivery['schemaVersion'] == 'SmallAppThreeComponentSourceDelivery/v1' and
             delivery['version'] == runtime['version'] == recovery['applicationVersion'], 'REGISTERED_R2_DELIVERY_MISMATCH')
        same = lambda a, b: a['bytes'] == b['bytes'] and a['sha256'] == b['sha256']
        need(same(delivery['sourceArtifactPin'], resource['applicationArtifactPin']), 'REGISTERED_INSTALLED_APP_ARTIFACT_MISMATCH')
        need(same(recovery['semanticsPin'], delivery['recoverySemanticsPin']) and
             same(recovery['freshTarget']['policyPin'], delivery['redisPolicyPin']) and
             any(Path(item['path']).name == 'redis_cache.py' and same(item, recovery['consumerPin'])
                 for item in delivery['sourcePins']), 'REGISTERED_REDIS_SEMANTIC_ASSETS_MISMATCH')
        descriptor_pins = [item for item in value['source']['assetInventory']['applicationFilePins']
                           if Path(item['path']).name == 'config-contract.json']
        need(len(descriptor_pins) == 1 and same(descriptor_pins[0], delivery['configurationDescriptorPin']),
             'REGISTERED_R2_CONFIG_DESCRIPTOR_MISSING')
        descriptor = self.native.document(descriptor_pins[0])
        need(descriptor['schemaVersion'] == 'SmallAppConfigurationDescriptor/v2' and
             descriptor['version'] == runtime['version'], 'REGISTERED_R2_CONFIG_DESCRIPTOR_MISMATCH')
        fields = runtime['sourceConfigurationFields']
        exact(fields, ' '.join(descriptor['backendRequiredFields']), 'REGISTERED_R2_CONFIG_FIELDS_INVALID')
        for lane, key in (('database', 'databaseRequiredFields'), ('s3', 's3RequiredFields'),
                          ('redis', 'redisRequiredFields'), ('http', 'backendHttpRequiredFields')):
            exact(fields[lane], ' '.join(descriptor[key]), 'REGISTERED_R2_CONFIG_FIELDS_INVALID')
        need(fields['schemaVersion'] == descriptor['backendRuntimeSchema'] and fields['secretRefs'] ==
             descriptor['secretReferences'] and fields['version'] == runtime['version'] and
             fields['logicalConfigRef'] == value['sourceConfigRef'] and fields['runtimeRole'] == 'SOURCE' and
             fields['tenantId'] == 122 and fields['username'] == 'aoteman', 'REGISTERED_R2_CONFIG_IDENTITY_MISMATCH')
        need(fields['database']['host'] == value['source']['database']['endpoint'] and
             fields['database']['name'] == value['source']['database']['name'] and
             fields['s3']['bucket'] == value['source']['objects']['bucket'] and
             fields['s3']['keyPrefix'] == value['source']['objects']['keyPrefix'] == descriptor['keyPrefix'],
             'REGISTERED_R2_ASSET_CONFIG_MISMATCH')
        semantics = self.native.document(recovery['semanticsPin'])
        policy = self.native.document(recovery['freshTarget']['policyPin'])
        self.native.raw(recovery['consumerPin'])
        recipe = self.native.document(recovery['classifications'][0]['recipePin'])
        return redis_semantic_policy(value, delivery, semantics, policy, recipe)

    def bind_redis(self, value, resource, instance, action):
        need(instance['runtimeConfigurationPin'] == resource['configurationPin'], 'REGISTERED_REDIS_RUNTIME_MISMATCH')
        public = self.native.document(resource['configurationPin'])
        if public.get('schemaVersion') == 'SmallAppPublicConfiguration/v2':
            configuration = public['backend']
        else:
            # A selected exact backend config is also an original consumed
            # descriptor; never a downgrade to r1 or to an invented endpoint.
            need(public.get('schemaVersion') == 'SmallAppRuntimeConfig/v2', 'REGISTERED_R2_RUNTIME_REQUIRED')
            configuration = public
        redis = configuration['redis']
        need(configuration['version'] == value['runtime']['version'] and configuration['runtimeRole'] == resource['role'] and
             configuration['logicalConfigRef'] == resource['configRef'] and configuration['tenantId'] == 122 and
             redis['host'] == instance['endpoint'] and redis['database'] == instance['databaseIndex'] and
             redis['keyPrefix'] == instance['keyPrefix'] and redis['instanceId'] == instance['instanceId'] and
             redis['serverVersion'] == instance['serverVersion'] and
             type(redis['serverVersion']) is str and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', redis['serverVersion']) and
             tuple(map(int, redis['serverVersion'].split('.'))) >= (6, 2, 0), 'REGISTERED_REDIS_SCOPE_MISMATCH')
        need(redis['database'] == 0 and redis['keyPrefix'] == 'brlab-20261012:smallapp:122:' + resource['role'].lower() + ':' and
             re.fullmatch('brlab-20261012-smallapp-' + resource['role'].lower() + '-[a-z0-9-]+', redis['instanceId']) and
             (resource['role'] != 'TARGET' or configuration['startState'] == 'PROTECTED'), 'REGISTERED_REDIS_ROLE_SCOPE_MISMATCH')
        # The public application uses a logical credential key. The W05
        # per-instance role resolves it in its separate private namespace.
        roles = {item['role']: item for item in value['secretReferences']}
        need(instance['secretRole'] == configuration['secretRefs']['redis'] and instance['secretReference'] is not None and
             (resource['role'] == 'TARGET' or instance['secretRole'] in roles and
              roles[instance['secretRole']]['state'] == 'OWNER_BOUND' and
              roles[instance['secretRole']]['reference'] == instance['secretReference']),
             'REGISTERED_REDIS_PRIVATE_REFERENCE_UNBOUND')
        ownership = self.native.signed(resource['ownerProofPin'])
        required = [instance['resourceProofPin']]
        if action in ('FULL', 'INCREMENTAL'):
            required.append(instance['applicationUseProofPin'])
        need(all(pin is not None and pin in ownership['originalObservationPins'] for pin in required),
             'REGISTERED_REDIS_ORIGINAL_NOT_AUTHENTICATED')
        for pin in required:
            self.native.raw(pin)
        observation = self.native.document(instance['resourceProofPin'])
        need(observation['schemaVersion'] == 'W05SmallAppInstallationPhase/v1' and
             observation['hostBootId'] == self.native.document(resource['hostIdentityPin'])['bootId'] and
             observation['existingSharedRedisModified'] is False, 'REGISTERED_REDIS_OWNER_OBSERVATION_INVALID')
        observed = observation['actualRedisResources'][resource['role']]
        need(observed['containerId'] == instance['containerId'] and observed['name'] == instance['instanceId'] and
             observed['endpointIp'] == redis['host'] and observed['endpointPort'] == redis['port'] and
             observed['redisVersion'] == instance['serverVersion'] and observed['actualAuthenticatedPing'] == 'PONG' and
             observed['privatePasswordLogicalRef'] == instance['secretReference'], 'REGISTERED_REDIS_NATIVE_IDENTITY_MISMATCH')
        inside(observed['dataRoot']); inside(observed['publicConfigPin']['path'])
        self.native.raw(observed['publicConfigPin'])
        need(resource['role'] != 'TARGET' or observed['actualDbSize'] == 0, 'REGISTERED_TARGET_REDIS_NOT_EMPTY')
        if resource['role'] == 'TARGET':
            peer = observation['actualRedisResources']['SOURCE']
            need(all(observed[key] != peer[key] for key in ('containerId', 'endpointIp', 'dataRoot',
                 'networkId', 'serverRunId', 'privatePasswordLogicalRef')), 'REGISTERED_REDIS_NATIVE_TARGET_OVERLAP')
        if action in ('FULL', 'INCREMENTAL'):
            usage = self.native.document(instance['applicationUseProofPin'])
            need(usage['version'] == configuration['version'] and usage['tenantId'] == 122 and
                 usage['username'] == 'aoteman' and usage['sessionCache'] == 'REDIS_READ_BACK_WITH_SQL_AUTHORITY',
                 'REGISTERED_REDIS_CONSUMER_NOT_OBSERVED')
        return configuration

    def bind(self, value, resource, resource_pin, action='FULL', target_ref=None):
        source_metadata_gate(value, action, target_ref)
        selection = self.config['engineSelection']
        need(value['engineSelectionRef'] in (None, selection['engineSelectionRef']), 'REGISTERED_ENGINE_MISMATCH')
        source, runtime, archive = value['source'], value['runtime'], value['archive']
        need(source['hostAddress'] == resource['hostAddress'] == '172.30.30.59', 'REGISTERED_HOST_MISMATCH')
        inside(source['root'])
        need(source['resourceBindingPin'] == resource_pin and source['nativeConfigPin'] == resource['nativeConfigPin'] and
             value['sourceConfigRef'] == resource['configRef'] and resource['role'] == 'SOURCE' and
             source['database']['serverUuid'] == resource['databaseUuid'] and
             source['database']['name'] == resource['database'] and
             source['database']['containerId'] == resource['databaseContainerId'] and
             source['objects']['containerId'] == resource['objectContainerId'] and
             runtime['pythonPin'] == resource['runtimePin'] and runtime['configurationPin'] == resource['configurationPin'],
             'REGISTERED_ACTUAL_RESOURCE_MISMATCH')
        native_config = self.bind_host(resource)
        configuration = self.native.document(resource['configurationPin'])
        fields = configuration['backend'] if configuration.get('schemaVersion') == 'SmallAppPublicConfiguration/v2' else configuration
        need(runtime['sourceConfigurationFields'] is not None and runtime['sourceConfigurationFields'] == fields,
             'REGISTERED_RUNTIME_FIELDS_NOT_ACTUAL')
        # Installed application members can be large. Reuse the existing streaming
        # Pin verifier after exact authenticated resource binding and lab scope.
        for pin in source['assetInventory']['applicationFilePins']:
            inside(pin['path']); executor.verify(pin)
        actual_pins, archive_required = source_binding_inputs(value, action, target_ref)
        for pin in actual_pins:
            self.native.raw(pin)
        self.bind_semantics(value, resource)
        if action != 'RESTORE':
            self.bind_redis(value, resource, source['redis'], action)
        if archive_required:
            service = self.native.document(archive['servicePin'])
            need(archive['repositoryId'] == service['repositoryId'] and archive['policyPin'] == service['policyPin'] and
                 archive['root'] == service['repositoryRoot'] and service['executionHostPin'] == native_config['executionHostPin'],
                 'REGISTERED_ARCHIVE_SERVICE_MISMATCH')
            policy = self.native.signed(archive['policyPin'])
            need(policy['sourceIdentityPin'] == resource['sourceIdentityPin'], 'REGISTERED_ARCHIVE_SOURCE_MISMATCH')
        return selection['engineSelectionRef']

    def bind_target(self, value, target, target_pin):
        need(not action_missing(value, 'RESTORE', target['configRef']), 'REGISTERED_ACTION_INPUTS_UNCONFIGURED')
        selected = self.target(value, target['configRef'])
        inside(selected['root'])
        need(selected['hostAddress'] == target['hostAddress'] == '172.30.30.59' and
             selected['resourceBindingPin'] == target_pin and selected['nativeConfigPin'] == target['nativeConfigPin'] and
             selected['freshnessProofPin'] == target['ownerProofPin'], 'REGISTERED_FRESH_TARGET_MISMATCH')
        source_pin = self.native.selector(self.root / 'resources', value['sourceConfigRef'])
        source = self.native.resource(source_pin, 'SOURCE', value['sourceConfigRef'])
        nonoverlap(source, target)
        host_pin = self.native.document(value['archive']['servicePin'])['executionHostPin']
        self.bind_host(target, host_pin)
        self.bind_redis(value, target, selected['redis'], 'RESTORE')
        need(target['applicationArtifactPin']['sha256'] == source['applicationArtifactPin']['sha256'] and
             target['versionPins'] == source['versionPins'] and target['runtimePin'] == source['runtimePin'],
             'REGISTERED_TARGET_VERSION_MISMATCH')

    def import_registration(self, registration_pin, expected_pin=None):
        executor.pin_reference(registration_pin)
        value = metadata(self.native.document(registration_pin))
        source_ref = value['sourceConfigRef']
        if expected_pin is not None:
            executor.pin_reference(expected_pin); self.native.raw(expected_pin)
        import fcntl
        import stat
        path = self.root / 'applications' / (value['applicationId'] + '.pin.json')
        fd = os.open(path.parent / 'import.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == info.st_gid == 0 and
                 stat.S_IMODE(info.st_mode) == 0o600, 'REGISTRATION_IMPORT_LOCK_CUSTODY_INVALID')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            existing = self.registrations()
            need(not any(item['applicationId'] != value['applicationId'] and source_ref is not None and
                         item['sourceConfigRef'] == source_ref for item in existing), 'REGISTERED_SOURCE_AMBIGUOUS')
            publish_registration(path, registration_pin, expected_pin)
        finally:
            os.close(fd)
        # Import never publishes a resource selector or marks metadata native-ready.
        return dict(applicationId=value['applicationId'], metadataImported=True,
                    nativeProofCreated=False, executionReady=False)

    def point_choices(self, value, source):
        parents, points = [], []
        for path in sorted((self.root / 'points').iterdir()):
            need(path.name.endswith('.pin.json'), 'POINT_SELECTOR_FILE_INVALID')
            reference = opaque(path.name[:-9])
            selected = self.native.selector(self.root / 'points', reference)
            point = self.native.signed(selected)
            from recovery_control_smallapp_native import POINT_FIELDS, window
            exact(point, POINT_FIELDS, 'POINT_BINDING_FIELDS_INVALID')
            need(point['schemaVersion'] == 'SmallAppPointBinding/v1', 'POINT_BINDING_VERSION_INVALID')
            if point['sourceIdentityPin'] != source['sourceIdentityPin']:
                continue
            window(point)
            need(point['batchId'] == BATCH and point['reference'] == reference and
                 point['orderedChainPins'] and point['orderedChainPins'][-1] == point['pointPin'], 'POINT_ANCESTRY_INVALID')
            prior = self.native.document(point['acceptedResultPin'])
            operation = point['ownerOperationId']
            directory = Path(self.config['ledgerRoot']) / opaque(operation)
            saved = local_read(directory / 'request.json'); intent = local_read(directory / 'intent.json')
            accepted = self.native.reconcile(saved, directory, intent['selection'])
            need(accepted is not None and accepted['state'] == 'SUCCEEDED' and
                 prior['operationId'] == operation and prior['state'] == 'SUCCEEDED', 'POINT_ORIGINAL_ACCEPTANCE_REQUIRED')
            binding = self.native.signed(intent['selection']['operationBindingPin'])
            dispatch = self.native.document(binding['dispatchPin'])
            need(dispatch['servicePin'] == value['archive']['servicePin'], 'POINT_REGISTERED_ARCHIVE_MISMATCH')
            self.native.archive_chain(saved, dispatch, source, point)
            parents.append(reference)
            if len(point['orderedChainPins']) >= 2:
                points.append(reference)
        need(len(parents) <= 1000, 'POINT_SELECTION_LIMIT')
        return parents, points

    def selections(self):
        rows = []
        for value in self.registrations():
            if value['sourceConfigRef'] is None:
                continue
            row = blocked_choice(value, 'REGISTERED_SOURCE_NOT_INSTALLED')
            try:
                pin = self.native.selector(self.root / 'resources', value['sourceConfigRef'])
                source = self.native.resource(pin, 'SOURCE', value['sourceConfigRef'])
                row['engineSelectionRef'] = self.bind(value, source, pin)
            except Failure as error:
                # Explicit blocked row, never an invented ready resource or point.
                row.update(fullReady=False, fullErrorCode=public_error(error), parentChainRefs=[],
                           recoveryPointRefs=[], freshTargetConfigRefs=[])
            else:
                row['fullReady'], row['fullErrorCode'] = True, None
                row['parentChainRefs'], row['recoveryPointRefs'] = self.point_choices(value, source)
                for item in value['allowedRestoreTargets']:
                    # A declared unconfigured target is not an eligible selection
                    # and is not a prerequisite for a manual source FULL.
                    if action_missing(value, 'RESTORE', item['configRef']):
                        continue
                    selected = self.native.selector(self.root / 'resources', item['configRef'])
                    target = self.native.resource(selected, 'TARGET', item['configRef'])
                    self.bind_target(value, target, selected)
                    row['freshTargetConfigRefs'].append(item['configRef'])
            exact(row, CHOICE_FIELDS, 'SELECTION_FIELDS_INVALID'); rows.append(row)
        return dict(observedAt=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), applications=rows)
