"""Exact current-control originals for W05's trusted private issuer.

These builders create unsigned originals only. The independently provisioned
issuer must sign them and publish registry selections after native observation.
They do not manufacture resource values, claims, authority or signatures.
"""
from recovery_control_smallapp import BATCH, exact, fingerprint, need, request
from recovery_control_smallapp_native import ACTION, BINDING_FIELDS, CLAIM_FIELDS, CONFIG_FIELDS, window


def service_configuration(original):
    """Validate a complete unsigned installation original; never fill missing inputs."""
    import ipaddress
    from pathlib import PurePosixPath
    import recovery_control_executor as executor
    from recovery_control_registration import ENGINE_FIELDS, inside, no_secret
    exact(original, CONFIG_FIELDS, 'SERVER_CONFIGURATION_FIELDS_INVALID'); no_secret(original)
    need(original['schemaVersion'] == 'SmallAppExecutionServiceConfig/v1' and original['batchId'] == BATCH and
         original['hostAddress'] == original['listenAddress'] == '172.30.30.59', 'SERVER_CONFIGURATION_BINDING_INVALID')
    ledger, registry = (PurePosixPath(original[key]) for key in ('ledgerRoot', 'registryRoot'))
    for path in (ledger, registry):
        inside(str(path))
    need(ledger != registry and ledger not in registry.parents and registry not in ledger.parents, 'SERVER_ROOTS_INVALID')
    need(type(original['listenPort']) is int and 1024 <= original['listenPort'] <= 65535 and
         original['listenPort'] not in (8081, 9000, 2375, 2376), 'TRANSPORT_TASK_BIND_REQUIRED')
    clients = original['allowedClientAddresses']
    need(type(clients) is list and clients and all(type(item) is str and str(ipaddress.ip_address(item)) == item
         for item in clients) and len(clients) == len(set(clients)), 'TRANSPORT_CLIENT_ADDRESSES_REQUIRED')
    credential = original['authCredentialRef']
    exact(credential, 'path uid gid mode', 'TRANSPORT_CREDENTIAL_REFERENCE_INVALID')
    inside(credential['path'])
    need(type(credential['uid']) is type(credential['gid']) is int and credential['uid'] == credential['gid'] == 0 and
         type(credential['mode']) is int and credential['mode'] == 0o600, 'TRANSPORT_CREDENTIAL_CUSTODY_REQUIRED')
    for key, name in (('serviceEntryPin', 'recovery_control_smallapp.py'),
                      ('nativeEntryPin', 'recovery_control_smallapp_native.py'),
                      ('httpEntryPin', 'recovery_control_smallapp_http.py'),
                      ('supervisorPin', 'recovery_environment_supervisor.py')):
        executor.pin_reference(original[key]); inside(original[key]['path'])
        need(PurePosixPath(original[key]['path']).name == name, 'SERVER_ENTRY_MISMATCH')
    for key in ('installationPin', 'authorityKeyPin'):
        executor.pin_reference(original[key]); inside(original[key]['path'])
    dependencies = original['dependencyPins']
    need(type(dependencies) is list and dependencies and len({item['path'] for item in dependencies}) == len(dependencies),
         'SERVER_DEPENDENCY_PINS_REQUIRED')
    for item in dependencies:
        executor.pin_reference(item); inside(item['path'])
    names = {PurePosixPath(item['path']).name for item in dependencies}
    need({'recovery_control_registration.py', 'recovery_control_smallapp_controls.py',
          'recovery_control_smallapp_issuer.py'}.issubset(names), 'REGISTRATION_CONSUMER_NOT_INSTALLED')
    selection = original['engineSelection']
    exact(selection, ENGINE_FIELDS, 'ENGINE_SELECTION_FIELDS_INVALID')
    from recovery_control_smallapp import opaque
    opaque(selection['engineSelectionRef'])
    for key in ('engineArtifactPin', 'engineVersionPin', 'engineEntryPin'):
        executor.pin_reference(selection[key]); inside(selection[key]['path'])
    need(PurePosixPath(selection['engineEntryPin']['path']).name == 'recovery_control_executor.py',
         'ENGINE_ORIGINAL_ENTRY_REQUIRED')
    window(original)
    return original


def repository_lease_original(ui_request, *, resource_binding, repository_id,
                              owner_identity_pin, not_before, expires_at):
    """Prepare the first unsigned source lease before a signed lease Pin exists."""
    value = request(ui_request)
    need(value['action'] in ('FULL', 'INCREMENTAL') and resource_binding['role'] == 'SOURCE' and
         resource_binding['batchId'] == BATCH and resource_binding['configRef'] == value['sourceConfigRef'] and
         type(repository_id) is str and repository_id, 'NEW_SOURCE_AUTHORITY_REQUIRED')
    from recovery_control_executor import pin_reference
    pin_reference(owner_identity_pin)
    window({'issuedAt': not_before, 'expiresAt': expires_at})
    return dict(schemaVersion='RepositoryLease/v1', repositoryId=repository_id,
                operationId=value['operationId'], ownerIdentityPin=owner_identity_pin, expiresAt=expires_at)


def authorization_originals(ui_request, *, resource_binding, policy_pin, repository_id,
                            executor_id, owner_identity_pin, lease_pin, lease_id, fence_token,
                            not_before, expires_at):
    """Fixed wire originals; independent issuer supplies the signatures and real claim."""
    value = request(ui_request)
    need(type(executor_id) is str and executor_id and type(lease_id) is str and lease_id and
         type(fence_token) is int and fence_token > 0 and resource_binding['batchId'] == BATCH,
         'REAL_CURRENT_AUTHORITY_INPUTS_REQUIRED')
    window({'issuedAt': not_before, 'expiresAt': expires_at})
    if value['action'] == 'RESTORE':
        need(resource_binding['configRef'] == value['targetConfigRef'] and resource_binding['role'] == 'TARGET' and
             resource_binding['fresh'] is True,
             'NEW_TARGET_AUTHORITY_REQUIRED')
        target_id = resource_binding['targetId']
        grant = dict(schemaVersion='RecoveryEnvironmentAuthorization/v1', operationId=value['operationId'],
            targetId=target_id, executorId=executor_id, mode='REHEARSAL', approved=True,
            actions=['REHEARSAL', 'RESTORE_EXECUTE', 'PREPARE_TARGET', 'START_APPLICATION'],
            notBefore=not_before, expiresAt=expires_at)
        lease = dict(schemaVersion='RecoveryEnvironmentLease/v1', operationId=value['operationId'],
            targetId=target_id, executorId=executor_id, leaseId=lease_id, fenceToken=fence_token,
            state='HELD', notBefore=not_before, expiresAt=expires_at)
    else:
        need(resource_binding['configRef'] == value['sourceConfigRef'] and resource_binding['role'] == 'SOURCE' and
             type(repository_id) is str and repository_id and
             owner_identity_pin is not None and lease_pin is not None, 'NEW_SOURCE_AUTHORITY_REQUIRED')
        lease = repository_lease_original(value, resource_binding=resource_binding, repository_id=repository_id,
            owner_identity_pin=owner_identity_pin, not_before=not_before, expires_at=expires_at)
        grant = dict(schemaVersion='RepositoryAuthorization/v1', repositoryId=repository_id,
            operationId=value['operationId'], actions=[ACTION[value['action']]],
            sourceOrTargetRef=resource_binding['nativeConfigPin'], resourcePin=resource_binding['nativeConfigPin'],
            policyPin=policy_pin, leaseRef=lease_pin, notBefore=not_before, expiresAt=expires_at)
    return grant, lease


def operation_request(ui_request, *, source_binding, target_binding, point_binding,
                      policy_pin, authorization_pin, lease_pin, deadline_milliseconds):
    value = request(ui_request)
    need(source_binding['configRef'] == value['sourceConfigRef'] and source_binding['role'] == 'SOURCE' and
         source_binding['batchId'] == BATCH,
         'NEW_SOURCE_SELECTION_REQUIRED')
    restore = value['action'] == 'RESTORE'
    need((target_binding is not None) == restore and
         (point_binding is not None) == (value['action'] != 'FULL'), 'CURRENT_CONTROL_SELECTION_CONFLICT')
    if restore:
        need(target_binding['configRef'] == value['targetConfigRef'] and target_binding['role'] == 'TARGET' and
             target_binding['fresh'] is True and
             target_binding['sourceIdentityPin'] == source_binding['sourceIdentityPin'], 'FRESH_TARGET_SELECTION_REQUIRED')
    if point_binding is not None:
        need(point_binding['sourceIdentityPin'] == source_binding['sourceIdentityPin'] and
             point_binding['reference'] == (value['recoveryPointRef'] if restore else value['parentChainRef']),
             'CURRENT_POINT_SELECTION_MISMATCH')
    need(type(deadline_milliseconds) is int and 0 < deadline_milliseconds <= 3600000,
         'ORIGINAL_DEADLINE_REQUIRED')
    return dict(schemaVersion='backup-restore-operation/v1', operationId=value['operationId'],
        requestId=value['operationId'] + '-execute', action=ACTION[value['action']], mode='REHEARSAL',
        selectedPointPin=None if point_binding is None else point_binding['pointPin'],
        sourceOrTargetRef=(target_binding if restore else source_binding)['nativeConfigPin'],
        policyPin=policy_pin, authorizationRefs=[authorization_pin], leaseRef=lease_pin,
        inputPins={} if not restore else {'repositoryPoint': point_binding['pointPin']},
        deadlineMilliseconds=deadline_milliseconds)


def execution_claim(*, operation_id, source_identity_pin, target_identity_pin, lease_ref,
                    executor_id, lease_id, fence_token, resource_observation_pin, issued_at, expires_at):
    need(type(fence_token) is int and fence_token > 0 and type(lease_id) is str and lease_id and
         type(executor_id) is str and executor_id, 'REAL_HELD_CLAIM_INPUTS_REQUIRED')
    value = dict(schemaVersion='SmallAppExecutionClaim/v1', batchId=BATCH, operationId=operation_id,
        sourceIdentityPin=source_identity_pin, targetIdentityPin=target_identity_pin, leaseRef=lease_ref,
        executorId=executor_id, state='HELD', leaseId=lease_id, fenceToken=fence_token,
        resourceObservationPin=resource_observation_pin, issuedAt=issued_at, expiresAt=expires_at)
    exact(value, CLAIM_FIELDS, 'CURRENT_CLAIM_FIELDS_INVALID'); window(value)
    return value


def operation_binding(ui_request, *, source_binding_pin, target_binding_pin, point_binding_pin,
                      operation_request_pin, dispatch_pin, native_launch_pin, grant_envelope_pin,
                      lease_envelope_pin, claim_pin, issued_at, expires_at):
    value = request(ui_request)
    need((target_binding_pin is not None) == (value['action'] == 'RESTORE') and
         (point_binding_pin is not None) == (value['action'] != 'FULL') and
         (value['action'] != 'RESTORE' or native_launch_pin is not None), 'CURRENT_BINDING_SELECTION_CONFLICT')
    original = dict(schemaVersion='SmallAppNativeOperationBinding/v1', batchId=BATCH,
        operationId=value['operationId'], uiRequestSha256=fingerprint(value), action=value['action'],
        sourceBindingPin=source_binding_pin, targetBindingPin=target_binding_pin, pointBindingPin=point_binding_pin,
        operationRequestPin=operation_request_pin, dispatchPin=dispatch_pin, nativeLaunchPin=native_launch_pin,
        grantEnvelopePin=grant_envelope_pin, leaseEnvelopePin=lease_envelope_pin, claimPin=claim_pin,
        issuedAt=issued_at, expiresAt=expires_at)
    exact(original, BINDING_FIELDS, 'CURRENT_BINDING_FIELDS_INVALID'); window(original)
    return original


def authority_context_original(ui_request, *, source_identity_pin, execution_host_pin,
                               lab_scope_pin, operation_request_pin, installed_closure_pin,
                               authorization_pin, lease_pin, authority_key_pin, issued_at, expires_at):
    """Bind the actual request and already produced controls; never sign the context."""
    request(ui_request)
    from recovery_control_executor import pin_reference
    from recovery_control_lab import CONTEXT, ID
    original = dict(schemaVersion='BackupRehearsalAuthorityContext/v1', rehearsalId=ID, environment='backup-lab',
        sourceIdentityPin=source_identity_pin, executionHostPin=execution_host_pin, labScopePin=lab_scope_pin,
        operationRequestPin=operation_request_pin, installedClosurePin=installed_closure_pin,
        authorizationPin=authorization_pin, leasePin=lease_pin, authorityKeyPin=authority_key_pin,
        issuedAt=issued_at, expiresAt=expires_at)
    exact(original, CONTEXT, 'CURRENT_CONTEXT_FIELDS_INVALID')
    for key, value in original.items():
        if key.endswith('Pin'):
            pin_reference(value)
    window(original)
    return original


def backup_dispatch_original(ui_request, *, execution_host_pin, service_pin, program_pin,
                             lab_context_pin, authority_key_pin):
    """Use the existing fixed owner CLI selected by the real UI action."""
    from pathlib import PurePosixPath
    from recovery_control_executor import pin_reference
    from recovery_control_registration import inside
    value = request(ui_request)
    original = dict(schemaVersion='RecoveryControlBackupLabDispatch/v1', executionHostPin=execution_host_pin,
        servicePin=service_pin, programPin=program_pin, labContextPin=lab_context_pin, authorityKeyPin=authority_key_pin)
    for key, reference in original.items():
        if key.endswith('Pin'):
            pin_reference(reference); inside(reference['path'])
    need(PurePosixPath(program_pin['path']).name ==
         ('recovery_cli.py' if value['action'] == 'RESTORE' else 'repository_cli.py'), 'ORIGINAL_OWNER_PROGRAM_REQUIRED')
    return original
