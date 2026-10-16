"""Read-only selection and complete ancestry verification; no target writes."""
from __future__ import annotations

import os
import base64
from datetime import datetime, timezone
from pathlib import Path

from recovery_engine import (absolute, authorities, check_pin, current_window, digest, load,
                             pinned_json, read_bytes, require, validate_record, repository_guard)


def trusted_configuration(request):
    path = os.environ.get('RECOVERY_DATA_TRUST_FILE')
    sha = os.environ.get('RECOVERY_DATA_TRUST_SHA256')
    require(path and sha, 'RECOVERY_DATA_TRUST_NOT_CONFIGURED')
    import hashlib
    raw = read_bytes(path)
    require(hashlib.sha256(raw).hexdigest() == sha, 'RECOVERY_DATA_TRUST_CHANGED')
    from recovery_engine import parse
    trust = parse(raw)
    require(trust['schemaVersion'] in ('RecoveryDataTrust/v1', 'RecoveryDataLabTrust/v1') and
            request['policyPin']['sha256'] == trust['policySha256'] and
            request['sourceOrTargetRef']['sha256'] == trust['targetConfigSha256'],
            'REQUEST_NOT_IN_PROVISIONED_TRUST')
    policy = pinned_json(trust['dataPolicyPin'])
    selected_policy = {'RecoveryDataTrust/v1': 'RecoveryDataPolicy/v1',
                       'RecoveryDataLabTrust/v1': 'RecoveryDataLabPolicy/v1'}[trust['schemaVersion']]
    require(policy['schemaVersion'] == selected_policy and
            policy['recordSchemasPin'] == trust['recordSchemasPin'] and
            policy['environmentPolicyPin'] == request['policyPin'], 'POLICY_VERSION_INVALID')
    validate_record(request, 'OperationRequest', policy['recordSchemasPin'])
    target = pinned_json(request['sourceOrTargetRef'])
    require(target['schemaVersion'] == 'RecoveryEnvironmentConfig/v1', 'TARGET_CONFIGURATION_VERSION_INVALID')
    require(policy['pythonPin'] == target['pythonPin'], 'CONFIGURED_PYTHON_MISMATCH')
    own_root = Path(__file__).absolute().parent
    own_files = {own_root/'recovery_cli.py', *own_root.glob('recovery_engine*.py'), *own_root.glob('recovery_plan*.py'),
                 *own_root.glob('recovery_data*.py'), *own_root.glob('recovery_cutover*.py')}
    require({absolute(item['path']) for item in policy['moduleSourcePins']} == own_files,
            'RECOVERY_MODULE_CLOSURE_NOT_PINNED')
    require(absolute(policy['dataWorkerPin']['path']) == own_root/'recovery_data.py', 'WRONG_DATA_WORKER')
    for item in policy['moduleSourcePins']: check_pin(item, content=False)
    validate_record(pinned_json(policy['dataTargetPin'])['targetIdentityPin'], 'Pin', policy['recordSchemasPin'])
    if selected_policy == 'RecoveryDataLabPolicy/v1':
        from recovery_plan_lab import admit
        policy = dict(policy, selectedLabContextPin=admit(request, policy, trust, target))
    else:
        require('labProfilePin' not in trust and 'labProfilePin' not in policy and
                pinned_json(policy['sourceScopePin']).get('environment') != 'backup-lab',
                'LAB_PROFILE_IN_PRODUCTION_TRUST')
    return trust, policy, target


def legacy_completion(point, policy):
    close = signed_evidence(point['ownerCloseEvidencePin'], policy)
    readback = signed_evidence(point['readbackEvidencePin'], policy)
    original = signed_evidence(point['originalExitEvidencePin'], policy)
    for record, schema in ((close, 'RepositoryOwnerClose/v1'), (readback, 'RepositoryReadback/v1'),
                           (original, 'RepositoryOriginalExit/v1')):
        require(record['schemaVersion'] == schema and record['backupId'] == point['backupId'] and
                record['manifestPin'] == point['manifestPin'], 'REPOSITORY_EVIDENCE_BINDING_INVALID')
    require(close['exactReaderCloseVerified'] is True and close['sourceFinalGuardVerified'] is True and
            readback['independentConnection'] is True and readback['payloadRefs'] == point['payloadRefs'] and
            original['actualExitCode'] == 0 and type(original['actualExitCode']) is int and
            original['rawTerminalVerified'] is True and original['processTerminated'] is True and
            close['originalProcessPin'] == readback['originalProcessPin'] == original['originalProcessPin'] and
            close['operationId'] == readback['operationId'] == original['operationId'],
            'OWNER_CLOSE_OR_ORIGINAL_EXIT_NOT_COMPLETE')
    active = repository_guard()
    if active is not None:
        active.original_pins([record['originalProcessPin'] for record in (close, readback, original)])
    check_pin(original['originalProcessPin'])
    # The repository supplies original whole-tree readback and process records.
    # Require the provisioned adapter field mapping, not an invented success enum.
    for record, rule in ((readback, policy['readbackRule']), (original, policy['originalExitRule'])):
        for name, expected in rule['requiredValues'].items():
            node = record
            for component in name.split('.'):
                require(type(node) is dict and component in node, 'ORIGINAL_EVIDENCE_FIELD_MISSING')
                node = node[component]
            require(type(node) is type(expected) and node == expected, 'ORIGINAL_EVIDENCE_NOT_COMPLETE')
    check_pin(point['manifestPin'])
    return pinned_json(point['manifestPin'])


def signed_evidence(ref, policy):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from recovery_engine import canonical
    value = pinned_json(ref)
    require(set(value) == {'schemaVersion', 'keySha256', 'payload', 'signature'} and
            value['schemaVersion'] == 'RepositorySignedRecord/v1', 'SIGNED_REPOSITORY_EVIDENCE_REQUIRED')
    keys = [item for item in policy['repositoryEvidenceKeyPins'] if item['sha256'] == value['keySha256']]
    require(len(keys) == 1, 'REPOSITORY_EVIDENCE_AUTHORITY_UNKNOWN')
    key = load_pem_public_key(check_pin(keys[0]))
    require(isinstance(key, Ed25519PublicKey), 'REPOSITORY_EVIDENCE_KEY_INVALID')
    key.verify(base64.b64decode(value['signature'], validate=True), canonical(value['payload']))
    return value['payload']


def resolve_chain(candidate_pin, policy):
    catalog = {item['sha256']: item for item in policy['repositoryPointPins']}
    require(len(catalog) == len(policy['repositoryPointPins']), 'POINT_CATALOG_DUPLICATE')
    visiting = set(); chain = []; source = None; generation = None

    def visit(ref):
        nonlocal source, generation
        require(catalog.get(ref['sha256']) == ref, 'POINT_NOT_IN_APPROVED_REPOSITORY')
        require(ref['sha256'] not in visiting, 'CHAIN_CYCLE')
        visiting.add(ref['sha256'])
        active = repository_guard()
        if active is not None: active.point(ref)
        point = validate_record(pinned_json(ref), 'RepositoryPoint', policy['recordSchemasPin'])
        if active is not None:
            active.archive_pins(ref, [point[name] for name in ('manifestPin', 'ownerCloseEvidencePin',
                'readbackEvidencePin', 'originalExitEvidencePin')] + point['payloadRefs'])
        require(point['integrityState'] == 'COMPLETE' and point['blockedReason'] in
                (None, 'REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED') and
                point['rehearsalEligible'] is True, 'POINT_NOT_REHEARSAL_ELIGIBLE')
        binding = legacy_completion(point, policy)
        if active is not None: active.archive_pins(ref, [binding['payloadTreePin']])
        require(binding['schemaVersion'] == 'RepositoryManifest/v1' and
                all(binding[key] == point[key] for key in ('backupId', 'generationId', 'pointType',
                    'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')), 'MANIFEST_POINT_MISMATCH')
        check_pin(binding['payloadTreePin']); check_pin(binding['copyProtectionPin'])
        from recovery_plan_tree import archived_tree
        archived_tree(point, binding)
        for item in binding['toolPins'] + binding['versionPins']:
            check_pin(item, content=False)
        from recovery_plan_objects import repository_binding
        _, repository = repository_binding(ref, point, policy)
        material_pin = repository['recoveryMaterialPin']
        material = pinned_json(material_pin)
        require(material['schemaVersion'] == 'RecoveryMaterial/v1' and
                material['manifestPin'] == point['manifestPin'] and
                material['pointType'] == point['pointType'] and
                material['recoveryPoint'] == point['commonRecoveryPoint'], 'MATERIAL_POINT_MISMATCH')
        source_scope = pinned_json(material['sourceScopePin'])
        source_identity = pinned_json(source_scope['sourceIdentityPin'])
        from recovery_plan_lab import chain_binding
        chain_binding(point, binding, source_scope, policy)
        require(source_scope['sourceIdentityPin'] == binding['sourceIdentityPin'] and
                source_identity['sourceFingerprint'] == material['sourceFingerprint'] and
                source_identity['databaseUuid'] == material['sourceDatabaseUuid'], 'SOURCE_BINDING_MISMATCH')
        if source is None:
            source = material['sourceScopePin']; generation = point['generationId']
        require(source == material['sourceScopePin'] and generation == point['generationId'],
                'CROSS_SOURCE_OR_GENERATION_CHAIN')
        for ref_payload in point['payloadRefs']:
            check_pin(ref_payload, content=False)
        declared = material['payloadPins']
        require(declared == point['payloadRefs'], 'MATERIAL_PAYLOAD_SCOPE_MISMATCH')
        for version_pin in material['versionPins']:
            check_pin(version_pin)
            require(version_pin in policy['supportedVersionPins'], 'UNSUPPORTED_VERSION_COMBINATION')
        require(material['versionPins'], 'VERSION_COMBINATION_REQUIRED')
        require(material['versionPins'] == binding['versionPins'], 'MATERIAL_MANIFEST_VERSION_MISMATCH')
        if point['pointType'] == 'FULL':
            require(not point['parentPointPins'] and material['database']['startPosition'] is None and
                    material['database']['method'] == 'FORMAL_SQL_FULL', 'FULL_BASELINE_INVALID')
        else:
            require(point['parentPointPins'] and
                    material['database']['method'] in ('MYSQL_BINLOG', 'BINLOG_SQL'), 'REAL_INCREMENTAL_CHAIN_REQUIRED')
            visit(point['parentPointPins'][-1])
            require(point['parentPointPins'] == [s[0] for s in chain], 'COMPLETE_PARENT_PREFIX_REQUIRED')
            require(chain[-1][2]['database']['endPosition'] == material['database']['startPosition'],
                    'DATABASE_LOG_GAP')
        chain.append((ref, point, material, material_pin))
        require(len(chain) <= policy['maxChainLength'], 'CHAIN_LENGTH_LIMIT')

    visit(candidate_pin)
    # The consistency marker describes data, so a genuine no-change increment
    # can retain it. Immutable backup identities must still be distinct.
    require(len({p['backupId'] for _, p, _, _ in chain}) == len(chain), 'POINT_IDENTITY_DUPLICATE')
    physical = [step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain]
    require(all(physical) or not any(physical), 'MIXED_PHYSICAL_AND_LOGICAL_OBJECT_CHAIN_UNSUPPORTED')
    for index, (_, _, material, _) in enumerate(chain):
        validate_material(material, full=index == 0)
    from recovery_plan_objects import object_index_chain
    object_index_chain(chain, policy)
    if all(physical):
        from recovery_data_files import physical_chain_inputs
        physical_chain_inputs(chain)
    return chain


def validate_material(material, *, full):
    """Resolve every necessary payload/evidence before target preparation."""
    database = material['database']; objects = material['objects']; payloads = material['payloadPins']
    require(database['endPosition'] is not None, 'REAL_DATABASE_RECOVERY_POSITION_REQUIRED')
    for key in ('expectedDataPin',): check_pin(database[key])
    require(material['referenceInventoryPin'] and material['derivedInventoryPin'], 'BUSINESS_DATA_CLASSIFICATIONS_REQUIRED')
    reference = pinned_json(material['referenceInventoryPin']); derived = pinned_json(material['derivedInventoryPin'])
    require(reference['schemaVersion'] == 'RecoveryReferenceInventory/v1' and reference['complete'] is True and
            reference['recoveryPoint'] == material['recoveryPoint'] and
            derived['schemaVersion'] == 'RecoveryDerivedInventory/v1' and derived['complete'] is True and
            derived['recoveryPoint'] == material['recoveryPoint'] and set(derived['classes']) == {'redis', 'queue'},
            'COMPLETE_SAME_POINT_REFERENCE_AND_DERIVED_INVENTORIES_REQUIRED')
    if database['method'] in ('FORMAL_SQL_FULL', 'BINLOG_SQL'):
        require(database['sqlPin'] in payloads, 'SQL_PAYLOAD_NOT_ARCHIVED')
        if not full:
            require(database['rawSqlPin'] in payloads, 'BINLOG_SQL_RAW_NOT_ARCHIVED')
            capture = pinned_json(database['capturePointPin'])
            require(capture['commonRecoveryPoint'] == material['recoveryPoint'] and capture['pointType'] == 'INCREMENTAL' and
                    capture['databaseEnd'] == database['endPosition'], 'BINLOG_CAPTURE_POINT_INVALID')
    else:
        from recovery_data import ordered_segments
        ordered_segments(material)
    if objects['method'] == 'PHYSICAL_FILES':
        require(objects['filePayloadPins'] is not None and all(ref in payloads for ref in objects['filePayloadPins'].values()),
                'PHYSICAL_FILE_PAYLOAD_NOT_ARCHIVED')
        for key in ('capturePointPin', 'fileInventoryPin', 'inventoryPin', 'exportReceiptPin'): check_pin(objects[key])
    elif full:
        require(objects['method'] == 'FORMAL_OBJECT_EXPORT', 'FULL_OBJECT_METHOD_UNSUPPORTED')
        for key in ('inventoryPin', 'exportReceiptPin'): check_pin(objects[key])
    else:
        require(objects['method'] == 'VERSION_DELTA', 'REAL_OBJECT_DELTA_REQUIRED')
        check_pin(objects['deltaPin']); check_pin(objects['expectedInventoryPin'])


def verify_report(report_pin, plan, policy, trust, *, require_execution=False, approval_pin=None):
    if approval_pin is None:
        require(report_pin['sha256'] in trust['verificationReportSha256s'], 'REPORT_NOT_INDEPENDENTLY_TRUSTED')
    else:
        approval = signed_evidence(approval_pin, policy)
        source = pinned_json(policy['sourceScopePin'])
        require(set(approval) == {'schemaVersion', 'repositoryId', 'reportPin', 'targetIdentityPin', 'sourceIdentityPin', 'validUntil'} and
                approval['schemaVersion'] == 'RepositoryRecoveryApproval/v1' and approval['reportPin'] == report_pin and
                approval['repositoryId'] == policy['repositoryId'] and approval['sourceIdentityPin'] == source['sourceIdentityPin'] and
                approval['targetIdentityPin'] == plan['plannedWrites'][0]['targetIdentityPin'], 'POST_REPORT_PROMOTION_APPROVAL_INVALID')
        current_window({'validFrom': '1970-01-01T00:00:00Z', 'validUntil': approval['validUntil']})
    report = validate_record(pinned_json(report_pin), 'RecoveryVerificationReport', policy['recordSchemasPin'])
    require(report['verdict'] == 'PASSED' and not report['invalidatedBy'] and
            report['backupAndChainPins'] == plan['orderedChainPins'] and
            report['targetIdentityPin'] == plan['plannedWrites'][0]['targetIdentityPin'] and
            report['sourceScopePin'] == policy['sourceScopePin'] and
            report['toolAndVersionPins'] == plan['toolPins'] + plan['supportedVersionPins'] and
            report['dataEvidencePins'] and report['playwrightEvidencePins'], 'CURRENT_MATCHING_PASSED_REPORT_REQUIRED')
    old_plan = validate_record(pinned_json(report['planPin']), 'RestorePlan', policy['recordSchemasPin'])
    require(old_plan['candidatePin'] == plan['candidatePin'] and old_plan['recoveryPoint'] == plan['recoveryPoint'],
            'REPORT_PLAN_MISMATCH')
    old_target = pinned_json(old_plan['targetRef']); current_target = pinned_json(plan['targetRef'])
    require({key: value for key, value in old_target.items() if key != 'controlledPreconditions'} ==
            {key: value for key, value in current_target.items() if key != 'controlledPreconditions'},
            'REPORT_TARGET_CONFIGURATION_CHANGED')
    for key in ('restoreResultPin', 'applicationStartPin'):
        evidence = pinned_json(report[key])
        require(evidence['state'] == 'SUCCEEDED' and evidence['restoreId'] == report['restoreId'] and
                evidence['targetIdentityPin'] == report['targetIdentityPin'], 'REPORT_EXECUTION_NOT_SUCCESSFUL')
    if require_execution:
        require(report['operationId'] == plan['operationId'] and report['restoreId'] == plan['restoreId'],
                'CUTOVER_REPORT_NOT_CURRENT_EXECUTION')
    for key in ('rtoObservation', 'rpoObservation'):
        item = report[key]
        require(item['state'] == 'MEASURED' and item['observedMilliseconds'] is not None and
                item['objectiveMilliseconds'] is not None and
                item['observedMilliseconds'] <= item['objectiveMilliseconds'] and item['evidencePins'],
                'RECOVERY_OBJECTIVE_NOT_PROVEN')
    for key in ('dataEvidencePins', 'playwrightEvidencePins', 'toolAndVersionPins', 'targetApprovalRefs'):
        for ref in report[key]:
            check_pin(ref, content=False)
    if approval_pin is None:
        freshness = pinned_json(policy['verificationFreshnessPinsByReportSha256'][report_pin['sha256']])
        require(freshness['reportPin'] == report_pin and freshness['invalidated'] is False, 'REPORT_FRESHNESS_INVALID')
        current_window(freshness)
    return report


def preflight(request, trust, policy, target_config):
    require(request['selectedPointPin'] is not None, 'SELECTED_POINT_REQUIRED')
    require(request['inputPins']['repositoryPoint'] == request['selectedPointPin'], 'SELECTION_INPUT_MISMATCH')
    chain = resolve_chain(request['selectedPointPin'], policy)
    data_target = pinned_json(policy['dataTargetPin'])
    identity_pin = data_target['targetIdentityPin']; identity = pinned_json(identity_pin)
    source = pinned_json(chain[-1][2]['sourceScopePin'])
    require(chain[-1][2]['sourceScopePin'] == policy['sourceScopePin'] and
            target_config['targetId'] == identity['targetId'] and
            target_config['targetIdentityPin'] == identity_pin and
            identity['sourceIdentityPin'] == source['sourceIdentityPin'] and
            data_target['database'] == target_config['database'], 'SOURCE_TARGET_OVERLAP')
    require(data_target['restoreMode'] in ('REBUILD_EMPTY', 'REPLACE_EXISTING') and
            data_target['versionedDataLocation'] != data_target['existingDataLocation'] and
            data_target['preserveExisting'] is True, 'VERSIONED_TARGET_REQUIRED')
    absolute(data_target['versionedDataLocation'])
    location = absolute(data_target['versionedDataLocation'])
    old_location = absolute(data_target['existingDataLocation'])
    require(not location.is_relative_to(old_location) and not old_location.is_relative_to(location) and
            not any(location.is_relative_to(absolute(root)) or absolute(root).is_relative_to(location)
                    for root in source['materialPaths']), 'SOURCE_TARGET_PATH_OVERLAP')
    require(all(item in chain[-1][2]['versionPins'] for item in target_config['imagePins']), 'TARGET_IMAGE_VERSION_MISMATCH')
    for ref in policy['toolPins'] + policy['supportedVersionPins']:
        check_pin(ref, content=False)
    for step in chain:
        require(step[2]['versionPins'] == chain[-1][2]['versionPins'], 'MIXED_CHAIN_VERSION_UNSUPPORTED')
    authorities(request, identity_pin, ['RESTORE_EXECUTE'], trust)
    planned = [dict(resource=resource, action=action, targetIdentityPin=identity_pin) for resource, action in
               [('database', 'FULL_THEN_ORDERED_BINLOG'), ('objects', 'FULL_THEN_CONTENT_AND_DELETE_MARKERS'),
                ('derivedData', 'RESTORE_OR_REBUILD_BY_CLASSIFICATION')]]
    plan = dict(schemaVersion='RestorePlan/v1', operationId=request['operationId'],
                restoreId='restore-' + digest({'operation': request['operationId'], 'request': request['requestId']})[:24],
                mode=request['mode'], candidatePin=request['selectedPointPin'], orderedChainPins=[s[0] for s in chain],
                recoveryPoint=chain[-1][2]['recoveryPoint'], targetRef=request['sourceOrTargetRef'],
                supportedVersionPins=chain[-1][2]['versionPins'], toolPins=policy['toolPins'], plannedWrites=planned,
                sideEffectPolicyPin=request['policyPin'], authorizationRefs=request['authorizationRefs'],
                leaseRef=request['leaseRef'], immutableInputsSha256=digest(immutable_inputs(request, policy, chain)))
    if request['mode'] == 'CONTROLLED_RESTORE':
        report_pin = request['inputPins']['recoveryVerificationReport'] if request['action'] == 'CONTROLLED_CUTOVER' else policy['controlledRestoreReportPin']
        verify_report(report_pin, plan, policy, trust)
        controlled_protection(request, target_config, data_target, policy)
    validate_record(plan, 'RestorePlan', policy['recordSchemasPin'])
    return plan, chain, data_target


def controlled_preconditions(request, config, data_target, policy):
    from recovery_cutover_fence import fence_handoff
    handoff = fence_handoff(request, policy)
    value = config['controlledPreconditions']
    require(type(value) is dict and value['restoreKind'] == data_target['restoreMode'], 'CONTROLLED_TARGET_MODE_MISMATCH')
    source = pinned_json(policy['sourceScopePin'])
    fence = pinned_json(handoff['sourceFencePin'])
    require(fence['schemaVersion'] == 'RecoverySourceFence/v1' and fence['state'] == 'ENFORCED' and
            fence['operationId'] == request['operationId'] and fence['sourceIdentityPin'] == source['sourceIdentityPin'] and
            fence['leaseRef'] == request['leaseRef'] and fence['retainedSourceResources'] is True and
            set(fence['writerCoverage']) == {'HTTP', 'QUARTZ', 'MQ', 'EXTERNAL', 'DIRECT_ACCOUNTS'} and
            all(item == 'ENFORCED' for item in fence['writerCoverage'].values()) and fence['originalInvocationPins'],
            'CONTROLLED_SOURCE_FENCE_REQUIRED')
    point_evidence = pinned_json(handoff['sourceFencePointEvidencePin'])
    require(point_evidence['schemaVersion'] == 'RecoverySourceFencePoint/v1' and
            point_evidence['sourceFencePin'] == handoff['sourceFencePin'] and
            point_evidence['sourceScopePin'] == policy['sourceScopePin'] and
            point_evidence['selectedPointPin'] == request['selectedPointPin'] and
            point_evidence['databaseAndObjectsUnchanged'] is True and point_evidence['observationPins'],
            'SOURCE_FENCE_SELECTED_POINT_EQUIVALENCE_REQUIRED')
    current_window(point_evidence)
    for ref in point_evidence['observationPins']: check_pin(ref)
    current_window({'validFrom': fence['observedAt'], 'validUntil': fence['expiresAt']})
    current_window({'validFrom': fence['observedAt'], 'validUntil': value['validUntil']})
    for ref in fence['originalInvocationPins']: check_pin(ref)
    controlled_protection(request, config, data_target, policy)


def controlled_protection(request, config, data_target, policy):
    """Read-only mode/protection admission, with no future fence prerequisite."""
    value = config['controlledPreconditions']
    require(type(value) is dict and value['restoreKind'] == data_target['restoreMode'], 'CONTROLLED_TARGET_MODE_MISMATCH')
    current_window({'validFrom': '1970-01-01T00:00:00Z', 'validUntil': value['validUntil']})
    if data_target['restoreMode'] == 'REBUILD_EMPTY':
        require(value['protectionPointPin'] is None and value['verificationReportPin'] is None, 'EMPTY_REBUILD_PROTECTION_INVALID')
    else:
        point = validate_record(pinned_json(value['protectionPointPin']), 'RepositoryPoint', policy['recordSchemasPin'])
        legacy_completion(point, policy)
        report = validate_record(pinned_json(value['verificationReportPin']), 'RecoveryVerificationReport', policy['recordSchemasPin'])
        require(report['verdict'] == 'PASSED' and not report['invalidatedBy'] and
                value['protectionPointPin'] in report['backupAndChainPins'] and report['sourceScopePin'] == policy['sourceScopePin'],
                'REPLACE_EXISTING_VERIFIED_PROTECTION_POINT_REQUIRED')
        freshness = pinned_json(policy['verificationFreshnessPinsByReportSha256'][value['verificationReportPin']['sha256']])
        require(freshness['reportPin'] == value['verificationReportPin'] and freshness['invalidated'] is False, 'PROTECTION_REPORT_STALE')
        current_window(freshness)


def immutable_inputs(request, policy, chain):
    from recovery_plan_objects import repository_binding
    bindings = [repository_binding(step[0], step[1], policy) for step in chain]
    # Lab admission injects authority for this complete request. A later request
    # needs its own context, while consuming the same stable preflight plan.
    stable_policy = ({name: value for name, value in policy.items() if name != 'selectedLabContextPin'}
                     if policy['schemaVersion'] == 'RecoveryDataLabPolicy/v1' else policy)
    value = dict(candidate=request['selectedPointPin'], chain=[s[0] for s in chain],
                materials=[s[3] for s in chain], target=request['sourceOrTargetRef'],
                repositoryBindings=[ref for ref, _ in bindings],
                objectContentIndexes=[value['objectContentIndexPin'] for _, value in bindings],
                policy=request['policyPin'], dataPolicySha256=digest(stable_policy),
                authorizations=request['authorizationRefs'], lease=request['leaseRef'])
    if policy['schemaVersion'] == 'RecoveryDataLabPolicy/v1':
        from recovery_plan_lab import immutable_binding
        value['labBinding'] = immutable_binding(policy, chain)
    return value


def prepared_target(request, plan, policy, trust):
    target = validate_record(pinned_json(request['inputPins']['recoveryTarget']), 'RecoveryTarget', policy['recordSchemasPin'])
    data_target = pinned_json(policy['dataTargetPin'])
    require(target['targetIdentityPin'] == data_target['targetIdentityPin'] and
            target['leaseRef'] == request['leaseRef'] == plan['leaseRef'] and
            target['targetId'] == pinned_json(target['targetIdentityPin'])['targetId'] and
            target['configurationPin'] == pinned_json(request['sourceOrTargetRef'])['configurationPin'] and
            target['versionPins'] == plan['supportedVersionPins'], 'PREPARED_TARGET_BINDING_INVALID')
    schemas = {'resourcesProofPin': 'RecoveryEnvironmentProof/v1', 'isolationProofPin': 'RecoveryIsolationProof/v1',
               'sideEffectIsolationPin': 'RecoverySideEffectIsolation/v1', 'modePreconditionsPin': 'RecoveryModePreconditions/v1'}
    for key in ('resourcesProofPin', 'isolationProofPin', 'sideEffectIsolationPin', 'modePreconditionsPin'):
        proof = pinned_json(target[key])
        require(proof['schemaVersion'] == schemas[key] and proof['operationId'] == plan['operationId'],
                'TARGET_PROOF_OPERATION_MISMATCH')
        observed = datetime.fromisoformat(proof['observedAt'].replace('Z', '+00:00'))
        require(0 <= (datetime.now(timezone.utc)-observed).total_seconds() <= policy['maximumProofAgeSeconds'],
                'TARGET_PROOF_STALE')
        rule = policy['targetProofRules'][key]
        for name, expected in rule.items():
            require(proof.get(name) == expected and type(proof.get(name)) is type(expected),
                    'TARGET_PROOF_INVALID_' + key.upper())
    resources = pinned_json(target['resourcesProofPin']); isolation = pinned_json(target['isolationProofPin'])
    side_effects = pinned_json(target['sideEffectIsolationPin']); mode = pinned_json(target['modePreconditionsPin'])
    require(resources['configurationRef'] == request['sourceOrTargetRef'] and
            resources['targetIdentityPin'] == target['targetIdentityPin'] and
            resources['leaseRef'] == target['leaseRef'] and resources['recoveryPoint'] == plan['recoveryPoint'] and
            resources['sourceWritesPerformed'] is False and resources['planPin'] == mode['planPin'] and
            pinned_json(mode['planPin']) == plan and isolation['state'] == side_effects['state'] == 'ENFORCED' and
            mode['targetIdentityPin'] == side_effects['targetIdentityPin'] == target['targetIdentityPin'] and
            mode['emptyDatabase'] is True and mode['emptyObjectStore'] is True and mode['emptyRedis'] is True and
            mode['resourcesProofPin'] == target['resourcesProofPin'], 'TARGET_PROTECTION_PRECONDITIONS_INVALID')
    require(resources['network'] == isolation['network'], 'TARGET_NETWORK_PROOF_MISMATCH')
    authorities(request, target['targetIdentityPin'], ['RESTORE_EXECUTE'], trust)
    if request['mode'] == 'CONTROLLED_RESTORE':
        controlled_preconditions(request, pinned_json(request['sourceOrTargetRef']), data_target, policy)
    return target
