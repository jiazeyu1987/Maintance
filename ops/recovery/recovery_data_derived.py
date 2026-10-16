"""Explicit Redis/MQ classifications dispatch approved target-bound executors."""
from recovery_engine import InvocationRunner, check_pin, pinned_json, require, write


def restored_inputs(native):
    """Derived writes require the final database and object results, at one point."""
    database = pinned_json(native.request['databaseResultPin'])
    objects = pinned_json(native.request['objectResultPin'])
    require(database['recoveryPoint'] == objects['recoveryPoint'] == native.plan['recoveryPoint'] and
            database['databaseUuid'] == native.db_uuid and
            database['endPosition'] == native.material['database']['endPosition'] and
            database['fullSchemaDataEquivalenceVerified'] is True,
            'DERIVED_RESTORED_INPUTS_REQUIRED')
    for ref in (database['observedPin'], database['comparisonPin'], objects['versionMappingPin']):
        check_pin(ref, content=False)


def restore_derived(native):
    inventory_pin = native.material['derivedInventoryPin']
    inventory = pinned_json(inventory_pin)
    require(inventory['schemaVersion'] == 'RecoveryDerivedInventory/v1' and inventory['complete'] is True and
            inventory['recoveryPoint'] == native.plan['recoveryPoint'] and
            set(inventory['classes']) == {'redis', 'queue'}, 'DERIVED_CLASSIFICATION_REQUIRED')
    restored_inputs(native)
    records = []; runner = InvocationRunner(native.root, native.budget)
    for name, item in inventory['classes'].items():
        require(item['classification'] in ('RESTORE', 'REBUILD', 'NOT_PRESENT'), 'DERIVED_CLASSIFICATION_INVALID')
        require(type(item['requiredForBusiness']) is bool, 'DERIVED_BUSINESS_POLICY_REQUIRED')
        if item['classification'] == 'NOT_PRESENT':
            require(not item['requiredForBusiness'] and item['payloadPins'] == [] and item['executorKey'] is None,
                    'REQUIRED_DERIVED_DATA_CANNOT_BE_ABSENT')
            records.append(dict(className=name, classification='NOT_PRESENT', inventoryPin=inventory_pin))
            continue
        require(item['executorKey'] in native.policy['derivedAdapters'], 'DERIVED_EXECUTOR_NOT_REGISTERED')
        adapter = native.policy['derivedAdapters'][item['executorKey']]
        require(adapter['className'] == name and adapter['classification'] == item['classification'] and
                adapter['scriptPin']['sha256'] in native.trust['derivedExecutorSha256s'], 'DERIVED_EXECUTOR_NOT_APPROVED')
        for ref in item['payloadPins']:
            check_pin(ref, content=False)
            require(ref in native.material['payloadPins'], 'DERIVED_PAYLOAD_NOT_ARCHIVED')
        if item['classification'] == 'RESTORE':
            require(item['payloadPins'], 'DURABLE_DERIVED_PAYLOAD_REQUIRED')
        else:
            require(item['rebuildFrom'] in ('DATABASE', 'OBJECTS'), 'DERIVED_REBUILD_SOURCE_NOT_RESTORED')
        rebuild_pin = None if item['classification'] == 'RESTORE' else \
            native.request['databaseResultPin' if item['rebuildFrom'] == 'DATABASE' else 'objectResultPin']
        native.bound(); native.mutation_dispatched = True
        request = dict(schemaVersion='RecoveryDerivedRequest/v1', operationId=native.original['operationId'],
            requestId=native.request['requestId']+'-'+name, action='DERIVED_'+item['classification'],
            className=name, targetIdentityPin=native.target['targetIdentityPin'], recoveryPoint=native.plan['recoveryPoint'],
            classificationPin=inventory_pin, originalRequestPin=native.request['originalRequestPin'],
            planPin=native.request['planPin'], recoveryTargetPin=native.request['recoveryTargetPin'],
            inputPins=item['payloadPins'], rebuildFromPin=rebuild_pin,
            deadlineMilliseconds=native.budget.milliseconds())
        from recovery_engine_state import inherited_target_lock
        original_count = len(runner.original_pins)
        try:
            result, ref = runner.run(native.config['pythonPin'], adapter['scriptPin'], request, guard=native.bound,
                lock_fd=inherited_target_lock(native.policy, native.target['targetIdentityPin']))
        finally:
            native.last_exit = runner.actual_exit_code
            native.original_pins.extend(runner.original_pins[original_count:])
        observed = result['data']
        require(observed['schemaVersion'] == 'RecoveryDerivedExecution/v1' and observed['state'] == 'VERIFIED' and
                observed['className'] == name and observed['classification'] == item['classification'] and
                observed['targetIdentityPin'] == native.target['targetIdentityPin'] and
                observed['recoveryPoint'] == native.plan['recoveryPoint'] and
                observed['verificationPins'] and observed['externalDispatchBlocked'] is True,
                'DERIVED_RESTORE_OR_REBUILD_NOT_VERIFIED')
        for proof in observed['verificationPins']:
            check_pin(proof)
        records.append(dict(className=name, classification=item['classification'], resultPin=ref))
    native.bound()
    return dict(schemaVersion='RecoveryDerivedEvidence/v1', recoveryPoint=native.plan['recoveryPoint'],
                targetIdentityPin=native.target['targetIdentityPin'], inventoryPin=inventory_pin, classes=records)
