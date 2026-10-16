"""Finite native custodian entries and the existing W05 A-role control signer.

No key creation, IntRuoyi authorization, arbitrary payload signing or resource
discovery. Initial records require an independent protected root approval and
a separate 0600 capability-free signer. Operation records use the established
0400 A role with its independently signed exact issuance plan.
"""
from pathlib import Path
import stat

from recovery_environment_contract import decode, exact, require
from recovery_native_process import pinned_bytes, signed_payload, lab_path
from recovery_native_signer import AuthoritySigningService
from recovery_control_smallapp import BATCH, fingerprint, request
from recovery_control_smallapp_native import (ACTION, BINDING_FIELDS, CLAIM_FIELDS, RESOURCE_FIELDS,
    OBSERVATION_FIELDS, OWNERSHIP_FIELDS, window)

PLAN_FIELDS = set(('schemaVersion batchId operationId uiRequest sourceBindingPin targetBindingPin pointBindingPin '
    'installationPin authorityKeyPin resourceObservationPin originalPins leaseId fenceToken executorId '
    'issuedAt expiresAt approved').split())
RECORDS = {
    'RepositoryAuthorization/v1': set(('schemaVersion repositoryId operationId actions sourceOrTargetRef '
                                      'policyPin resourcePin notBefore expiresAt leaseRef').split()),
    'RepositoryLease/v1': set('schemaVersion repositoryId operationId ownerIdentityPin expiresAt'.split()),
    'RecoveryEnvironmentAuthorization/v1': set(('schemaVersion operationId targetId executorId mode actions '
                                               'notBefore expiresAt approved').split()),
    'RecoveryEnvironmentLease/v1': set(('schemaVersion operationId targetId executorId leaseId fenceToken '
                                      'notBefore expiresAt state').split()),
    'SmallAppExecutionClaim/v1': set(CLAIM_FIELDS.split()),
    'SmallAppNativeOperationBinding/v1': set(BINDING_FIELDS.split()),
    'BackupRehearsalAuthorityContext/v1': set(('schemaVersion rehearsalId environment sourceIdentityPin executionHostPin '
        'labScopePin operationRequestPin installedClosurePin authorizationPin leasePin authorityKeyPin issuedAt expiresAt').split()),
}


def issuance_plan_shape(plan, authority):
    """Finite permission shape only; callers still must authenticate the exact plan."""
    exact(plan, PLAN_FIELDS, 'SMALLAPP_ISSUER_PLAN_FIELDS_INVALID')
    require(plan['schemaVersion'] == 'SmallAppControlIssuancePlan/v1' and plan['batchId'] == BATCH and
            plan['approved'] is True and plan['authorityKeyPin'] == authority and
            plan['operationId'] == request(plan['uiRequest'])['operationId'], 'SMALLAPP_ISSUER_PERMISSION_REQUIRED')
    window(plan)
    require(type(plan['originalPins']) is list and 1 <= len(plan['originalPins']) <= 8 and
            len({pin['path'] for pin in plan['originalPins']}) == len(plan['originalPins']) and
            type(plan['fenceToken']) is int and plan['fenceToken'] > 0 and
            type(plan['leaseId']) is str and plan['leaseId'] and type(plan['executorId']) is str and plan['executorId'],
            'SMALLAPP_ISSUER_FINITE_HELD_SELECTION_REQUIRED')
    from recovery_control_executor import pin_reference
    for field in ('sourceBindingPin', 'installationPin', 'authorityKeyPin', 'resourceObservationPin'):
        pin_reference(plan[field])
    for pin in [*plan['originalPins'], plan['targetBindingPin'], plan['pointBindingPin']]:
        if pin is not None:
            pin_reference(pin)


def control_record_window(value, plan):
    """A finite original cannot outlive or precede its independently approved plan."""
    require(value['expiresAt'] == plan['expiresAt'], 'SMALLAPP_ISSUER_RECORD_WINDOW_MISMATCH')
    if 'issuedAt' in value:
        window(value)
        require(value['issuedAt'] == plan['issuedAt'], 'SMALLAPP_ISSUER_RECORD_WINDOW_MISMATCH')


class SmallAppAuthoritySigningService(AuthoritySigningService):
    def __init__(self, *, issuance_plan_pin, **kwargs):
        # Authenticate current finite permission before the inherited A role opens its key.
        self.plan_pin = issuance_plan_pin
        authority = kwargs['authority_key_pin']
        self.plan = signed_payload(issuance_plan_pin, authority)
        self.validate_plan(authority)
        super().__init__(**kwargs)

    def validate_plan(self, authority):
        plan = self.plan
        issuance_plan_shape(plan, authority)
        source = signed_payload(plan['sourceBindingPin'], authority)
        exact(source, set(RESOURCE_FIELDS.split()), 'SMALLAPP_ISSUER_SOURCE_FIELDS_INVALID')
        require(source['batchId'] == BATCH and source['role'] == 'SOURCE' and source['tenantId'] == 122,
                'SMALLAPP_ISSUER_NEW_SOURCE_REQUIRED')
        require(source['configRef'] == plan['uiRequest']['sourceConfigRef'], 'SMALLAPP_ISSUER_REGISTERED_SOURCE_MISMATCH')
        selected = source
        restore = plan['uiRequest']['action'] == 'RESTORE'
        require((plan['targetBindingPin'] is not None) == restore and
                (plan['pointBindingPin'] is not None) == (plan['uiRequest']['action'] != 'FULL'),
                'SMALLAPP_ISSUER_SELECTION_CONFLICT')
        if restore:
            selected = signed_payload(plan['targetBindingPin'], authority)
            exact(selected, set(RESOURCE_FIELDS.split()), 'SMALLAPP_ISSUER_TARGET_FIELDS_INVALID')
            require(selected['batchId'] == BATCH and selected['role'] == 'TARGET' and selected['fresh'] is True and
                    selected['configRef'] == plan['uiRequest']['targetConfigRef'] and selected['tenantId'] == 122 and
                    selected['sourceIdentityPin'] == source['sourceIdentityPin'] and
                    selected['databaseUuid'] != source['databaseUuid'], 'SMALLAPP_ISSUER_FRESH_TARGET_REQUIRED')
        observed = signed_payload(plan['resourceObservationPin'], authority)
        exact(observed, set(OBSERVATION_FIELDS.split()), 'SMALLAPP_ISSUER_OBSERVATION_FIELDS_INVALID')
        require(observed['schemaVersion'] == 'SmallAppResourceObservation/v1' and observed['batchId'] == BATCH and
                observed['operationId'] == plan['operationId'] and observed['state'] == 'HELD' and
                observed['leaseId'] == plan['leaseId'] and observed['fenceToken'] == plan['fenceToken'] and
                observed['databaseUuid'] == selected['databaseUuid'] and observed['resourceBindingPin'] ==
                    (plan['targetBindingPin'] if restore else plan['sourceBindingPin']),
                'SMALLAPP_ISSUER_REAL_HELD_OBSERVATION_REQUIRED')
        window(observed)
        require(type(observed['originalObservationPins']) is list and observed['originalObservationPins'],
                'SMALLAPP_ISSUER_REAL_OBSERVATION_ORIGINALS_REQUIRED')
        for original_pin in observed['originalObservationPins']:
            pinned_bytes(original_pin)
        self.source, self.selected = source, selected

    def _sign(self, reference):
        self.guard()
        require(signed_payload(self.plan_pin, self.authority_key_pin) == self.plan,
                'SMALLAPP_ISSUER_PLAN_CHANGED')
        self.validate_plan(self.authority_key_pin)
        require(reference in self.plan['originalPins'], 'SMALLAPP_ISSUER_ORIGINAL_NOT_SELECTED')
        path = lab_path(reference['path'])
        require(self.root in path.parents and path.name.endswith('-control-original.json'),
                'SMALLAPP_ISSUER_PRIVATE_ORIGINAL_REQUIRED')
        info = path.stat()
        import os
        require(info.st_uid == self.peer_uid and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600 and
                os.statvfs(path).f_flag & os.ST_RDONLY, 'SMALLAPP_ISSUER_READONLY_ORIGINAL_REQUIRED')
        raw = pinned_bytes(reference); value = decode(raw)
        version = value.get('schemaVersion'); fields = RECORDS.get(version)
        require(fields is not None, 'SMALLAPP_ISSUER_RECORD_UNSUPPORTED')
        exact(value, fields, 'SMALLAPP_ISSUER_RECORD_FIELDS_INVALID')
        require(value.get('operationId', self.plan['operationId']) == self.plan['operationId'],
                'SMALLAPP_ISSUER_OPERATION_MISMATCH')
        # Every finite original shares the current approved plan's expiry.
        control_record_window(value, self.plan)
        if version in ('RepositoryAuthorization/v1', 'RecoveryEnvironmentAuthorization/v1'):
            action = self.plan['uiRequest']['action']
            expected = ['REHEARSAL', 'RESTORE_EXECUTE', 'PREPARE_TARGET', 'START_APPLICATION'] if action == 'RESTORE' else [ACTION[action]]
            require(value['actions'] == expected and value['notBefore'] == self.plan['issuedAt'] and
                    value['expiresAt'] == self.plan['expiresAt'], 'SMALLAPP_ISSUER_GRANT_SCOPE_MISMATCH')
        if version.startswith('Repository'):
            require(self.plan['uiRequest']['action'] != 'RESTORE', 'SMALLAPP_ISSUER_SOURCE_GRANT_ONLY')
        if version == 'RepositoryAuthorization/v1':
            require(value['sourceOrTargetRef'] == value['resourcePin'] == self.source['nativeConfigPin'],
                    'SMALLAPP_ISSUER_SOURCE_GRANT_MISMATCH')
        if version.startswith('RecoveryEnvironment'):
            require(self.plan['uiRequest']['action'] == 'RESTORE' and value['targetId'] == self.selected['targetId'] and
                    value['executorId'] == self.plan['executorId'], 'SMALLAPP_ISSUER_TARGET_CONTROL_MISMATCH')
        if version == 'RecoveryEnvironmentAuthorization/v1':
            require(value['approved'] is True and value['mode'] == 'REHEARSAL', 'SMALLAPP_ISSUER_RESTORE_ONLY')
        if version in ('RecoveryEnvironmentLease/v1', 'SmallAppExecutionClaim/v1'):
            require(value['state'] == 'HELD' and value['leaseId'] == self.plan['leaseId'] and
                    value['fenceToken'] == self.plan['fenceToken'], 'SMALLAPP_ISSUER_CURRENT_FENCE_MISMATCH')
        if version == 'SmallAppExecutionClaim/v1':
            require(value['batchId'] == BATCH and value['sourceIdentityPin'] == self.source['sourceIdentityPin'] and
                    value['targetIdentityPin'] == (None if self.plan['targetBindingPin'] is None else self.selected['identityPin']) and
                    value['resourceObservationPin'] == self.plan['resourceObservationPin'], 'SMALLAPP_ISSUER_CLAIM_MISMATCH')
        if version == 'SmallAppNativeOperationBinding/v1':
            require(value['batchId'] == BATCH and value['uiRequestSha256'] == fingerprint(self.plan['uiRequest']) and
                    value['action'] == self.plan['uiRequest']['action'] and all(value[k] == self.plan[k] for k in
                    ('sourceBindingPin', 'targetBindingPin', 'pointBindingPin')), 'SMALLAPP_ISSUER_BINDING_MISMATCH')
        if version == 'BackupRehearsalAuthorityContext/v1':
            require(value['sourceIdentityPin'] == self.source['sourceIdentityPin'] and
                    value['installedClosurePin'] == self.plan['installationPin'] and
                    value['authorityKeyPin'] == self.authority_key_pin and value['environment'] == 'backup-lab',
                    'SMALLAPP_ISSUER_CONTEXT_MISMATCH')
        # Inherited trusted W05 admission independently checks actual installed
        # runtime/producer/key denial/current resources, never a caller success flag.
        self.admit(value); self.guard()
        require(pinned_bytes(reference) == raw, 'SMALLAPP_ISSUER_ORIGINAL_CHANGED')
        return self._publish(value, reference['sha256'] + '.smallapp.signed.json')


# Bootstrap permission is a root-custodian original, never a record issued by
# either this finite entry or the business worker. Each invocation selects ONE
# existing original; subsequent records consume already issued dependency Pins.
INITIAL_SELECTION_FIELDS = set(('schemaVersion batchId kind approvalPin originalPin authorityKeyPin '
    'sourceIdentityPin hostBootId installedFilePins pythonPin dependencyPins engineSelection '
    'producerIdentityPin custodianIdentityPin issuerEntryPin signerUid signerGid signerRootPath '
    'privateKeyReference outputRoot installationAdmissionPin issuedAt expiresAt deadlineMilliseconds').split())
INITIAL_APPROVAL_FIELDS = INITIAL_SELECTION_FIELDS - {
    'schemaVersion', 'approvalPin', 'privateKeyReference', 'signerRootPath', 'outputRoot', 'deadlineMilliseconds'} | {
    'schemaVersion', 'approved', 'scope'}
INITIAL_KINDS = {
    'RUNTIME_TRUST': 'RepositoryLabNativeRuntimeTrust/v1',
    'RUNTIME_PROOF': 'RepositoryLabNativeRuntimeProof/v1',
    'INSTALLATION': 'RepositoryNativeInstallation/v2',
    'SOURCE_OWNERSHIP': 'SmallAppResourceOwnership/v1',
    'SOURCE_BINDING': 'SmallAppResourceBinding/v1',
    'SERVICE_CONFIGURATION': 'SmallAppExecutionServiceConfig/v1',
    'OPERATION_PLAN': 'SmallAppControlIssuancePlan/v1',
}
# The seven existing kinds remain unchanged. These are the exact additional
# native repository originals consumed by W03, each selected separately.
REPOSITORY_INITIAL_KINDS = {
    'LAB_SCOPE': ('RepositoryLabScope/v1', 'schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix allowedActions expiresAt'),
    'REPOSITORY_POLICY': ('RepositoryPolicy/v1', 'schemaVersion repositoryId sourceIdentityPin supportedVersionPins supportedToolPins maxChainPoints maxChainAgeSeconds retainNewestPoints minValidFullPoints retentionSeconds legalHoldPointPins copyProtectionPin'),
    'NATIVE_PEER_CONFIGURATION': ('RepositoryNativePeerConfig/v2', 'schemaVersion repositoryId sourceIdentityPin programPin ownerPythonPin ownerEntryPin ownerDependencyPins recipeTemplatePin assemblyTemplatePin sessionRoot custodyPaths resourceRoots sourceRoots sourceRootProofPins writerContainers dockerPin nftPin writerRulesSha256 readbackConfig signingKeyPin nativeImplementationPins executionHostPin labScopePin'),
    'LAB_COPY_PROTECTION': ('RepositoryLabCopyProtection/v1', 'schemaVersion repositoryId sourceIdentityPin labScopePin sourceDeletionDenied independentFailureDomain recoveryKeysAvailable aclEvidencePin readbackEndpointEvidencePin validUntil'),
    'LAB_ACL_EVIDENCE': ('RepositoryLabAclEvidence/v1', 'schemaVersion labScopePin sourceIdentityPin archiveRoot sourceAccountPin writerAccountPin readerAccountPin deletionAttemptPin keyAccessEvidencePin'),
    'LAB_READBACK_ENDPOINT': ('RepositoryLabReadbackEndpoint/v1', 'schemaVersion labScopePin archiveRoot uncRoot encrypted signingRequired independentConnectionId readerAccountPin readbackOriginalPin observedAt'),
    'LAB_DELETION_PROBE': ('RepositoryLabDeletionProbe/v1', 'schemaVersion labScopePin accountPin archiveRoot deleteDenied probeOriginalPin'),
    'LAB_KEY_ACCESS': ('RepositoryLabKeyAccess/v1', 'schemaVersion labScopePin recoveryKeysAvailable probeOriginalPin'),
}
INITIAL_KINDS.update({kind: fields[0] for kind, fields in REPOSITORY_INITIAL_KINDS.items()})


def repository_initial_shape(selection, value):
    """Fixed existing schemas only; independent approval selects every original."""
    from datetime import datetime, timezone
    from recovery_control_smallapp import ROOT
    from recovery_control_smallapp_native import stamp
    from recovery_control_registration import inside
    kind = selection['kind']
    schema, fields = REPOSITORY_INITIAL_KINDS[kind]
    exact(value, fields.split(), 'SMALLAPP_INITIAL_REPOSITORY_FIELDS_INVALID')
    require(value['schemaVersion'] == schema, 'SMALLAPP_INITIAL_REPOSITORY_SCHEMA_INVALID')
    if 'repositoryId' in value:
        require(type(value['repositoryId']) is str and value['repositoryId'], 'SMALLAPP_INITIAL_REPOSITORY_ID_REQUIRED')
    if 'sourceIdentityPin' in value:
        require(value['sourceIdentityPin'] == selection['sourceIdentityPin'], 'SMALLAPP_INITIAL_SOURCE_MISMATCH')
    now = datetime.now(timezone.utc)
    for name in ('expiresAt', 'validUntil'):
        if name in value:
            require(now < stamp(value[name]) <= stamp(selection['expiresAt']), 'SMALLAPP_INITIAL_WINDOW_MISMATCH')
    if kind == 'LAB_SCOPE':
        from recovery_native_process import REHEARSAL_ID
        allowed = {'BACKUP_FULL', 'BACKUP_INCREMENTAL', 'LIST_POINTS', 'POINT_DETAIL', 'READBACK_VERIFY',
            'RESTORE_PREFLIGHT', 'PREPARE_TARGET', 'RESTORE_EXECUTE', 'START_APPLICATION', 'VERIFY_RECOVERY',
            'REHEARSAL', 'PLAN_REHEARSAL'}
        actions = value['allowedActions']
        require(value['rehearsalId'] == REHEARSAL_ID and value['host'] == '172.30.30.59' and value['root'] == ROOT and
            value['resourcePrefix'] == 'brlab-20261012' and type(actions) is list and actions and
            all(type(action) is str for action in actions) and len(actions) == len(set(actions)) and set(actions) <= allowed,
            'SMALLAPP_INITIAL_LAB_SCOPE_INVALID')
    elif kind == 'REPOSITORY_POLICY':
        require(all(type(value[k]) is int and value[k] > 0 for k in ('maxChainPoints', 'maxChainAgeSeconds',
            'retainNewestPoints', 'minValidFullPoints', 'retentionSeconds')) and
            all(type(value[k]) is list for k in ('supportedVersionPins', 'supportedToolPins', 'legalHoldPointPins')) and
            value['supportedVersionPins'] and value['supportedToolPins'], 'SMALLAPP_INITIAL_REPOSITORY_POLICY_INVALID')
    elif kind == 'LAB_COPY_PROTECTION':
        require(value['independentFailureDomain'] is False and value['sourceDeletionDenied'] is True and
                value['recoveryKeysAvailable'] is True, 'SMALLAPP_INITIAL_LAB_COPY_PROTECTION_INVALID')
    elif kind == 'LAB_READBACK_ENDPOINT':
        require(value['encrypted'] is True and value['signingRequired'] is True and
            type(value['independentConnectionId']) is str and value['independentConnectionId'] and
            stamp(value['observedAt']) <= now, 'SMALLAPP_INITIAL_LAB_READBACK_INVALID')
    elif kind == 'LAB_DELETION_PROBE':
        require(value['deleteDenied'] is True, 'SMALLAPP_INITIAL_LAB_DELETION_DENIAL_REQUIRED')
    elif kind == 'LAB_KEY_ACCESS':
        require(value['recoveryKeysAvailable'] is True, 'SMALLAPP_INITIAL_LAB_KEY_ACCESS_REQUIRED')
    for name in ('archiveRoot', 'sessionRoot'):
        if name in value:
            inside(value[name])


def initial_selection_original(selection, output_path):
    """Persist a complete selection referencing an existing independent approval."""
    from recovery_control_smallapp import native_required, persist
    from recovery_control_executor import pin
    native_required()
    context = object.__new__(InitialCustodianContext)
    import time
    context.deadline = time.monotonic() + 300
    context.selection = selection
    exact(selection, INITIAL_SELECTION_FIELDS, 'SMALLAPP_INITIAL_SELECTION_FIELDS_INVALID')
    approval = context.document(selection['approvalPin'])
    initial_selection_shape(selection, approval)
    output = lab_path(output_path, exists=False)
    lab_path(output.parent, directory=True)
    persist(output, selection)
    return dict(selectionPin=pin(output), unsigned=True, approvalCreated=False, nativeInstallationVerified=False)


def native_source_configuration_original(fields, *, service_pin, peer_pin, installation_pin, authority_pin, output_path):
    """Call the selected unchanged W03 builder; never measure or invent inputs."""
    from recovery_control_smallapp import native_required, persist
    from recovery_control_executor import native_installation, installed_repository, pin
    native_required()
    installation = native_installation(installation_pin, authority_pin)
    service = decode(pinned_bytes(service_pin))
    require(service['schemaVersion'] == 'RepositoryNativeServiceConfig/v1' and authority_pin in service['authorityKeyPins'],
            'SMALLAPP_NATIVE_SOURCE_AUTHORITY_NOT_SELECTED')
    host = decode(pinned_bytes(service['executionHostPin']))
    require(host['installationManifestPin'] == installation_pin, 'SMALLAPP_NATIVE_SOURCE_INSTALLATION_NOT_SELECTED')
    with installed_repository(installation):
        from repository_native_lab import native_source_configuration
        from repository_records import RepositoryError
        from recovery_environment_contract import EnvironmentFailure
        try:
            value = native_source_configuration(fields, service_pin=service_pin, peer_pin=peer_pin)
        except RepositoryError as error:
            raise EnvironmentFailure(error.code, unknown=error.unknown) from error
    output = lab_path(output_path, exists=False)
    lab_path(output.parent, directory=True)
    persist(output, value)
    return dict(nativeConfigPin=pin(output), unsigned=True, sourceIdentityCreated=False, businessDispatched=False)


def initial_selection_shape(selection, approval):
    """Portable rejection checks; this function never establishes native custody."""
    from recovery_control_executor import pin_reference
    from recovery_control_registration import ENGINE_FIELDS, inside
    exact(selection, INITIAL_SELECTION_FIELDS, 'SMALLAPP_INITIAL_SELECTION_FIELDS_INVALID')
    exact(approval, INITIAL_APPROVAL_FIELDS, 'SMALLAPP_INITIAL_APPROVAL_FIELDS_INVALID')
    require(selection['schemaVersion'] == 'SmallAppInitialCustodianSelection/v1' and
            selection['batchId'] == BATCH and selection['kind'] in INITIAL_KINDS,
            'SMALLAPP_INITIAL_FINITE_SELECTION_REQUIRED')
    scope = ('APPROVE_CURRENT_OPERATION_PLAN' if selection['kind'] == 'OPERATION_PLAN'
             else 'INITIALIZE_TASK_SOURCE_SERVICE')
    require(approval['schemaVersion'] == 'SmallAppInitialCustodianApproval/v1' and
            approval['approved'] is True and approval['scope'] == scope and
            all(approval[field] == selection[field] for field in
                INITIAL_APPROVAL_FIELDS - {'schemaVersion', 'approved', 'scope'}),
            'SMALLAPP_INITIAL_INDEPENDENT_APPROVAL_REQUIRED')
    window(selection); window(approval)
    require(type(selection['deadlineMilliseconds']) is int and
            0 < selection['deadlineMilliseconds'] <= 300000 and
            type(selection['signerUid']) is type(selection['signerGid']) is int and
            selection['signerUid'] > 0 and selection['signerGid'] > 0 and
            type(selection['hostBootId']) is str and selection['hostBootId'],
            'SMALLAPP_INITIAL_FINITE_NATIVE_ROLE_REQUIRED')
    key = selection['privateKeyReference']
    exact(key, {'path', 'uid', 'gid', 'mode'}, 'SMALLAPP_INITIAL_PRIVATE_KEY_REFERENCE_INVALID')
    require(key['uid'] == selection['signerUid'] and key['gid'] == selection['signerGid'] and
            type(key['mode']) is int and key['mode'] == 0o600,
            'SMALLAPP_INITIAL_0600_ROLE_REQUIRED')
    for field in ('path',):
        inside(key[field])
    for field in ('signerRootPath', 'outputRoot'):
        inside(selection[field])
    for field in ('approvalPin', 'originalPin', 'authorityKeyPin', 'sourceIdentityPin', 'pythonPin',
                  'producerIdentityPin', 'custodianIdentityPin', 'issuerEntryPin'):
        pin_reference(selection[field]); inside(selection[field]['path'])
        require(selection[field]['path'] != key['path'], 'SMALLAPP_INITIAL_KEY_HASH_INPUT_REFUSED')
    require(selection['originalPin']['path'] != selection['approvalPin']['path'] and
            selection['producerIdentityPin'] != selection['custodianIdentityPin'],
            'SMALLAPP_INITIAL_SELF_PERMISSION_REFUSED')
    exact(selection['engineSelection'], ENGINE_FIELDS.split(), 'ENGINE_SELECTION_FIELDS_INVALID')
    require(type(selection['installedFilePins']) is type(selection['dependencyPins']) is list and
            selection['installedFilePins'] and selection['dependencyPins'], 'SMALLAPP_INITIAL_EXACT_MEMBERS_REQUIRED')
    members = selection['installedFilePins'] + selection['dependencyPins'] + [selection['pythonPin']]
    require(
            len(members) <= 4096 and len({pin['path'] for pin in members}) == len(members),
            'SMALLAPP_INITIAL_EXACT_MEMBERS_REQUIRED')
    for pin in members:
        pin_reference(pin)
        require(pin['path'] != key['path'], 'SMALLAPP_INITIAL_KEY_HASH_INPUT_REFUSED')
    require(selection['issuerEntryPin'] in selection['installedFilePins'] and
            all(selection['engineSelection'][field] in selection['installedFilePins'] for field in
                ('engineArtifactPin', 'engineVersionPin', 'engineEntryPin')),
            'SMALLAPP_INITIAL_ENGINE_MEMBERS_MISMATCH')
    require((selection['installationAdmissionPin'] is not None) ==
            (selection['kind'] in ('SERVICE_CONFIGURATION', 'OPERATION_PLAN')),
            'SMALLAPP_INITIAL_ADMISSION_PHASE_MISMATCH')
    if selection['installationAdmissionPin'] is not None:
        pin_reference(selection['installationAdmissionPin'])
        require(selection['installationAdmissionPin']['path'] != key['path'],
                'SMALLAPP_INITIAL_KEY_HASH_INPUT_REFUSED')


def initial_record_scope(selection, value):
    """Reject cross-source, cross-installation and self-referential originals."""
    from recovery_control_executor import pin_reference
    require(type(value) is dict and value.get('schemaVersion') == INITIAL_KINDS[selection['kind']],
            'SMALLAPP_INITIAL_RECORD_UNSUPPORTED')
    forbidden = {selection['approvalPin']['path'], selection['originalPin']['path'],
                 selection['privateKeyReference']['path']}
    def references(item, depth=0):
        require(depth <= 64, 'SMALLAPP_INITIAL_GRAPH_LIMIT')
        if type(item) is dict:
            if set(item) == {'path', 'bytes', 'sha256'}:
                pin_reference(item)
                require(item['path'] not in forbidden, 'SMALLAPP_INITIAL_CIRCULAR_PIN_REFUSED')
            else:
                for child in item.values(): references(child, depth + 1)
        elif type(item) is list:
            for child in item: references(child, depth + 1)
    references(value)
    if 'authorityKeyPin' in value:
        require(value['authorityKeyPin'] == selection['authorityKeyPin'], 'SMALLAPP_INITIAL_AUTHORITY_MISMATCH')
    if 'sourceIdentityPin' in value:
        require(value['sourceIdentityPin'] == selection['sourceIdentityPin'], 'SMALLAPP_INITIAL_SOURCE_MISMATCH')
    if 'bootId' in value:
        require(value['bootId'] == selection['hostBootId'], 'SMALLAPP_INITIAL_BOOT_MISMATCH')
    if 'batchId' in value:
        require(value['batchId'] == BATCH, 'SMALLAPP_INITIAL_BATCH_MISMATCH')
    if 'role' in value:
        require(value['role'] == 'SOURCE' and value['tenantId'] == 122 and value['fresh'] is False and
                value['targetId'] is None, 'SMALLAPP_INITIAL_SOURCE_ONLY')
    if 'issuedAt' in value:
        from recovery_control_smallapp_native import stamp
        window(value)
        require(stamp(selection['issuedAt']) <= stamp(value['issuedAt']) and
                stamp(value['expiresAt']) <= stamp(selection['expiresAt']), 'SMALLAPP_INITIAL_WINDOW_MISMATCH')


class InitialCustodianContext:
    """Independent root parent; no caller-supplied guard/admit/ready callbacks."""
    def __init__(self, selection_pin):
        import os
        import sys
        import time
        from recovery_native_launcher import measure_process
        require(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0,
                'SMALLAPP_INITIAL_NATIVE_ROOT_REQUIRED')
        self.deadline = time.monotonic() + 300
        self.selection_pin = selection_pin
        self.selection = {}
        self.selection = self.document(selection_pin)
        self.approval = self.document(self.selection['approvalPin'])
        initial_selection_shape(self.selection, self.approval)
        self.deadline = time.monotonic() + self.selection['deadlineMilliseconds'] / 1000
        self.producer = self.document(self.selection['producerIdentityPin'])
        self.custodian = self.document(self.selection['custodianIdentityPin'])
        actual = measure_process(os.getpid())
        require(all(self.custodian[key] == actual[key] for key in self.custodian if key != 'state') and
                self.custodian['pid'] != self.producer['pid'] and
                self.custodian['mountNamespace'] != self.producer['mountNamespace'] and
                self.custodian['bootId'] == self.producer['bootId'] == self.selection['hostBootId'],
                'SMALLAPP_INITIAL_INDEPENDENT_CUSTODIAN_REQUIRED')
        self.guard()

    def raw(self, reference):
        from recovery_native_browser import descriptor_read
        # The established public trust lane is root-owned group-readable data.
        if reference == self.selection.get('authorityKeyPin'):
            return descriptor_read(reference, owners={0}, deadline=self.deadline,
                                   modes=(0o400, 0o440, 0o444, 0o600), readonly=True)
        return descriptor_read(reference, owners={0}, owner_gid=0, deadline=self.deadline,
                               modes=(0o400, 0o600, 0o700), readonly=True)

    def document(self, reference):
        return decode(self.raw(reference))

    def guard(self):
        import os
        import time
        from recovery_native_launcher import match_process, status
        from recovery_control_executor import pin
        require(time.monotonic() < self.deadline and
                self.document(self.selection_pin) == self.selection and
                self.document(self.selection['approvalPin']) == self.approval,
                'SMALLAPP_INITIAL_CURRENT_APPROVAL_CHANGED')
        initial_selection_shape(self.selection, self.approval)
        match_process(self.custodian, os.getpid(), 0)
        match_process(self.producer, self.producer['pid'], 0)
        require(pin(Path(__file__).resolve()) == self.selection['issuerEntryPin'],
                'SMALLAPP_INITIAL_ENTRY_NOT_INSTALLED')
        worker_status = status(self.producer['pid'])
        require(all(int(worker_status[name], 16) == 0 for name in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                int(worker_status.get('CapAmb', '0'), 16) == 0 and worker_status['NoNewPrivs'] == '1' and
                not worker_status['Groups'].split(), 'SMALLAPP_INITIAL_WORKER_CAPABILITIES_REFUSED')
        # Large programs, Python and dependencies use the mature streaming verifier.
        from recovery_control_executor import verify
        for reference in [*self.selection['installedFilePins'], *self.selection['dependencyPins'], self.selection['pythonPin']]:
            verify(reference)
        self.raw(self.selection['authorityKeyPin']); self.raw(self.selection['sourceIdentityPin'])

    def admit(self, value):
        """Finite schema admission; signed dependencies must already exist."""
        self.guard()
        initial_record_scope(self.selection, value)
        kind = self.selection['kind']
        from recovery_control_smallapp_native import ROOT
        if kind in ('RUNTIME_TRUST', 'RUNTIME_PROOF', 'INSTALLATION'):
            from recovery_control_executor import installed_repository
            with installed_repository({'filePins': self.selection['installedFilePins']}):
                from repository_native_runtime import INSTALL_FIELDS, TRUST_FIELDS, PROOF_FIELDS, _trust_shape, _proof_shape
                fields = {'RUNTIME_TRUST': TRUST_FIELDS, 'RUNTIME_PROOF': PROOF_FIELDS, 'INSTALLATION': INSTALL_FIELDS}[kind]
                exact(value, fields.split(), 'SMALLAPP_INITIAL_RUNTIME_RECORD_FIELDS_INVALID')
                if kind == 'RUNTIME_TRUST':
                    catalog = _trust_shape(value)
                    require(value['runtimeRole'] == 'EXECUTOR' and
                            all(item['pin'] in self.selection['dependencyPins'] for item in catalog.values()),
                            'SMALLAPP_INITIAL_RUNTIME_MEMBER_MISMATCH')
                    from recovery_control_executor import verify
                    for reference in value['vendorArtifactPins']: verify(reference)
                elif kind == 'RUNTIME_PROOF':
                    trust = signed_payload(value['nativeRuntimeTrustPin'], self.selection['authorityKeyPin'])
                    _proof_shape(value, trust, value['nativeRuntimeTrustPin'])
                    require(value['bootId'] == self.selection['hostBootId'], 'SMALLAPP_INITIAL_BOOT_MISMATCH')
                    for field in ('readOnlyMountEvidencePin', 'managerIdentityEvidencePin', 'nativeLinkageEvidencePin'):
                        self.raw(value[field])
                else:
                    require(value['root'] == ROOT and value['filePins'] == self.selection['installedFilePins'] and
                            value['dependencyPins'] == self.selection['dependencyPins'] and
                            value['pythonPin'] == self.selection['pythonPin'] and
                            value['sourceToolkitPin'] == self.selection['engineSelection']['engineArtifactPin'],
                            'SMALLAPP_INITIAL_INSTALLATION_MEMBER_MISMATCH')
                    trust = signed_payload(value['nativeRuntimeTrustPin'], self.selection['authorityKeyPin'])
                    proof = signed_payload(value['nativeRuntimeProofPin'], self.selection['authorityKeyPin'])
                    _trust_shape(trust); _proof_shape(proof, trust, value['nativeRuntimeTrustPin'])
                    require(proof['bootId'] == self.selection['hostBootId'], 'SMALLAPP_INITIAL_BOOT_MISMATCH')
        elif kind in REPOSITORY_INITIAL_KINDS:
            self.repository_original(value, kind)
        elif kind == 'SERVICE_CONFIGURATION':
            from recovery_control_smallapp_controls import service_configuration
            service_configuration(value)
            require(value['engineSelection'] == self.selection['engineSelection'], 'SMALLAPP_INITIAL_ENGINE_MISMATCH')
            require(all(reference in self.selection['installedFilePins'] for reference in
                [value['serviceEntryPin'], value['nativeEntryPin'], value['httpEntryPin'], value['supervisorPin'],
                 *value['dependencyPins']]), 'SMALLAPP_INITIAL_SERVICE_MEMBERS_MISMATCH')
            self.installation_admission(value['installationPin'])
        elif kind == 'SOURCE_BINDING':
            exact(value, RESOURCE_FIELDS.split(), 'SMALLAPP_INITIAL_SOURCE_FIELDS_INVALID')
            from recovery_control_smallapp_native import Native
            # Existing resource admission verifies the signed ownership and actual originals.
            native = Native(self.selection['originalPin'], self.selection['authorityKeyPin'])
            self.source_original(value)
            ownership = native.signed(value['ownerProofPin'])
            self.source_original(ownership)
            require(all(ownership[k] == value[k] for k in set(RESOURCE_FIELDS.split()) & set(OWNERSHIP_FIELDS.split())
                        if k != 'schemaVersion'), 'SMALLAPP_INITIAL_OWNERSHIP_MISMATCH')
        elif kind == 'SOURCE_OWNERSHIP':
            exact(value, OWNERSHIP_FIELDS.split(), 'SMALLAPP_INITIAL_OWNERSHIP_FIELDS_INVALID')
            self.source_original(value)
            require(value['resourcePrefix'] == 'brlab-20261012-' and value['state'] == 'READY' and
                    value['isolatedFromProtectedResources'] is True and value['originalObservationPins'],
                    'SMALLAPP_INITIAL_TASK_OWNERSHIP_REQUIRED')
            for reference in value['originalObservationPins']: self.raw(reference)
        else:
            issuance_plan_shape(value, self.selection['authorityKeyPin'])
            temporary = object.__new__(SmallAppAuthoritySigningService)
            temporary.plan = value
            temporary.validate_plan(self.selection['authorityKeyPin'])
            require(temporary.source['sourceIdentityPin'] == self.selection['sourceIdentityPin'],
                    'SMALLAPP_INITIAL_SOURCE_MISMATCH')
            self.installation_admission(value['installationPin'])
        self.guard()

    def repository_signed(self, reference, kind):
        from recovery_native_process import authenticate_payload
        value = authenticate_payload(self.document(reference), self.raw(self.selection['authorityKeyPin']),
                                     self.selection['authorityKeyPin']['sha256'])
        repository_initial_shape({**self.selection, 'kind': kind}, value)
        return value

    def repository_original(self, value, kind):
        """Consume the exact native repository chain before the finite signer."""
        from recovery_control_executor import installed_repository, installation_shape, verify, pin_reference
        from recovery_control_registration import inside
        repository_initial_shape({**self.selection, 'kind': kind}, value)
        identity = self.document(self.selection['sourceIdentityPin'])
        require(type(identity.get('sourceFingerprint')) is str and identity['sourceFingerprint'] and
                type(identity.get('databaseUuid')) is str and identity['databaseUuid'],
                'SMALLAPP_INITIAL_ACTUAL_SOURCE_REQUIRED')
        if kind == 'LAB_SCOPE':
            return
        if kind == 'REPOSITORY_POLICY':
            proof = self.repository_signed(value['copyProtectionPin'], 'LAB_COPY_PROTECTION')
            require(proof['repositoryId'] == value['repositoryId'] and proof['sourceIdentityPin'] == value['sourceIdentityPin'],
                    'SMALLAPP_INITIAL_REPOSITORY_POLICY_SCOPE_MISMATCH')
            self.repository_original(proof, 'LAB_COPY_PROTECTION')
            for name in ('supportedVersionPins', 'supportedToolPins', 'legalHoldPointPins'):
                for reference in value[name]:
                    verify(reference)
            return
        scope = self.repository_signed(value['labScopePin'], 'LAB_SCOPE')
        if 'repositoryId' in value:
            require(value['repositoryId'] == scope['repositoryId'], 'SMALLAPP_INITIAL_REPOSITORY_SCOPE_MISMATCH')
        if kind == 'LAB_DELETION_PROBE':
            self.raw(value['accountPin']); self.raw(value['probeOriginalPin'])
        elif kind == 'LAB_KEY_ACCESS':
            self.raw(value['probeOriginalPin'])
        elif kind == 'LAB_READBACK_ENDPOINT':
            self.raw(value['readerAccountPin']); self.raw(value['readbackOriginalPin'])
        elif kind == 'LAB_ACL_EVIDENCE':
            require(len({value[name]['sha256'] for name in ('sourceAccountPin', 'writerAccountPin', 'readerAccountPin')}) == 3,
                    'SMALLAPP_INITIAL_LAB_ACCOUNTS_NOT_DISTINCT')
            for name in ('sourceAccountPin', 'writerAccountPin', 'readerAccountPin'):
                self.raw(value[name])
            deletion = self.repository_signed(value['deletionAttemptPin'], 'LAB_DELETION_PROBE')
            keys = self.repository_signed(value['keyAccessEvidencePin'], 'LAB_KEY_ACCESS')
            require(deletion['labScopePin'] == keys['labScopePin'] == value['labScopePin'] and
                    deletion['accountPin'] == value['sourceAccountPin'] and deletion['archiveRoot'] == value['archiveRoot'],
                    'SMALLAPP_INITIAL_LAB_ACL_SCOPE_MISMATCH')
            self.repository_original(deletion, 'LAB_DELETION_PROBE')
            self.repository_original(keys, 'LAB_KEY_ACCESS')
        elif kind == 'LAB_COPY_PROTECTION':
            acl = self.repository_signed(value['aclEvidencePin'], 'LAB_ACL_EVIDENCE')
            endpoint = self.repository_signed(value['readbackEndpointEvidencePin'], 'LAB_READBACK_ENDPOINT')
            require(acl['labScopePin'] == endpoint['labScopePin'] == value['labScopePin'] and
                    acl['sourceIdentityPin'] == value['sourceIdentityPin'] and acl['archiveRoot'] == endpoint['archiveRoot'] and
                    acl['readerAccountPin'] == endpoint['readerAccountPin'], 'SMALLAPP_INITIAL_LAB_COPY_SCOPE_MISMATCH')
            self.repository_original(acl, 'LAB_ACL_EVIDENCE')
            self.repository_original(endpoint, 'LAB_READBACK_ENDPOINT')
        elif kind == 'NATIVE_PEER_CONFIGURATION':
            with installed_repository({'filePins': self.selection['installedFilePins']}):
                from repository_native_lab import ROLES, HOST_FIELDS
                exact(value['nativeImplementationPins'], ROLES.keys(), 'SMALLAPP_INITIAL_NATIVE_PEER_ROLES_INVALID')
                host = self.document(value['executionHostPin'])
                exact(host, HOST_FIELDS.split(), 'SMALLAPP_INITIAL_NATIVE_HOST_FIELDS_INVALID')
            require(host['schemaVersion'] == 'RepositoryNativeExecutionHost/v1' and host['hostOs'] == 'Linux' and
                host['bootId'] == self.selection['hostBootId'] and host['pythonPin'] == value['ownerPythonPin'] ==
                self.selection['pythonPin'] and type(host['uid']) is type(host['gid']) is int and host['uid'] == host['gid'] == 0,
                'SMALLAPP_INITIAL_NATIVE_PEER_HOST_MISMATCH')
            installed = signed_payload(host['installationManifestPin'], self.selection['authorityKeyPin'])
            require(installation_shape(installed) == 'RepositoryNativeInstallation/v2' and
                    installed['filePins'] == self.selection['installedFilePins'] and
                    installed['dependencyPins'] == self.selection['dependencyPins'] and
                    installed['pythonPin'] == self.selection['pythonPin'], 'SMALLAPP_INITIAL_CURRENT_INSTALLATION_MISMATCH')
            proof = signed_payload(installed['nativeRuntimeProofPin'], self.selection['authorityKeyPin']); window(proof)
            trust = signed_payload(installed['nativeRuntimeTrustPin'], self.selection['authorityKeyPin'])
            with installed_repository(installed):
                from repository_native_runtime import _trust_shape, _proof_shape
                _trust_shape(trust); _proof_shape(proof, trust, installed['nativeRuntimeTrustPin'])
            require(trust['runtimeRole'] == 'EXECUTOR' and all(host[k] == proof[k] for k in
                ('hostId', 'bootId', 'pidNamespace', 'mountNamespace')) and
                value['programPin'] == value['nativeImplementationPins']['nativePeer'] and
                all(reference in installed['filePins'] for reference in value['nativeImplementationPins'].values()),
                'SMALLAPP_INITIAL_NATIVE_PEER_INSTALLATION_MISMATCH')
            for role, reference in value['nativeImplementationPins'].items():
                require(Path(reference['path']).name == ROLES[role], 'SMALLAPP_INITIAL_NATIVE_PEER_PROGRAM_MISMATCH')
                verify(reference)
            for name in ('ownerDependencyPins', 'custodyPaths', 'sourceRoots', 'sourceRootProofPins', 'writerContainers'):
                require(type(value[name]) is list and value[name], 'SMALLAPP_INITIAL_NATIVE_PEER_INPUTS_REQUIRED')
            for reference in [value['ownerEntryPin'], value['recipeTemplatePin'], value['assemblyTemplatePin'],
                              *value['ownerDependencyPins'], *value['custodyPaths']]:
                self.raw(reference)
            require(len(value['sourceRoots']) == len(value['sourceRootProofPins']), 'SMALLAPP_INITIAL_NATIVE_SOURCE_ROOTS_REQUIRED')
            for path, reference in zip(value['sourceRoots'], value['sourceRootProofPins']):
                inside(path)
                actual = lab_path(path, directory=True).stat()
                require(self.document(reference) == dict(path=path, device=actual.st_dev, inode=actual.st_ino),
                        'SMALLAPP_INITIAL_NATIVE_SOURCE_ROOT_CHANGED')
            require(type(value['resourceRoots']) is dict and value['resourceRoots'], 'SMALLAPP_INITIAL_NATIVE_RESOURCE_ROOTS_REQUIRED')
            for resource in value['resourceRoots'].values():
                exact(resource, 'root identityPin observationPin reserveBytes budgetBytes'.split(),
                      'SMALLAPP_INITIAL_NATIVE_RESOURCE_FIELDS_INVALID')
                inside(resource['root'])
                self.raw(resource['identityPin']); self.raw(resource['observationPin'])
                require(type(resource['reserveBytes']) is type(resource['budgetBytes']) is int and
                        resource['reserveBytes'] >= 0 and resource['budgetBytes'] > 0,
                        'SMALLAPP_INITIAL_NATIVE_RESOURCE_BUDGET_REQUIRED')
            import re
            require(type(value['writerRulesSha256']) is str and re.fullmatch('[0-9a-f]{64}', value['writerRulesSha256']),
                    'SMALLAPP_INITIAL_NATIVE_WRITER_RULES_REQUIRED')
            for reference in (value['dockerPin'], value['nftPin']):
                require(reference in installed['dependencyPins'], 'SMALLAPP_INITIAL_NATIVE_TOOL_NOT_SELECTED')
                verify(reference)
            reader = value['readbackConfig']
            exact(reader, 'schemaVersion uncRoot repositoryRelativePath repositoryRoot credentialPin port authProtocol recordRoot maximumRecordBytes maximumTotalRecordBytes libraryPins'.split(),
                  'SMALLAPP_INITIAL_NATIVE_READBACK_FIELDS_INVALID')
            require(reader['schemaVersion'] == 'RepositorySmbReadbackConfig/v1', 'SMALLAPP_INITIAL_NATIVE_READBACK_SCHEMA_INVALID')
            # Native peer owns its evidence key and SMB credential. Their exact
            # existing Pins are selection metadata, never read/hash here.
            pin_reference(value['signingKeyPin']); pin_reference(reader['credentialPin'])

    def source_original(self, value):
        initial_record_scope({**self.selection, 'kind': 'SOURCE_OWNERSHIP' if value['schemaVersion'] ==
                             'SmallAppResourceOwnership/v1' else 'SOURCE_BINDING'}, value)
        self.native_source_original(value)

    def native_source_original(self, value):
        """Shared source consumption for issuance and service initialization."""
        import re
        require(value['hostAddress'] == '172.30.30.59' and value['identityPin'] == value['sourceIdentityPin'] and
                value['targetId'] is None, 'SMALLAPP_INITIAL_ACTUAL_SOURCE_REQUIRED')
        require(type(value['databaseUuid']) is str and re.fullmatch('[0-9a-fA-F-]{36}', value['databaseUuid']) and
                type(value['database']) is str and re.fullmatch('[a-zA-Z][a-zA-Z0-9_]{0,63}', value['database']) and
                value['database'] not in {'mysql', 'sys', 'information_schema', 'performance_schema'} and
                all(type(value[field]) is str and re.fullmatch('[0-9a-f]{64}', value[field]) for field in
                    ('databaseContainerId', 'objectContainerId', 'applicationContainerId')),
                'SMALLAPP_INITIAL_ACTUAL_RESOURCE_IDENTITIES_REQUIRED')
        for field in ('identityPin', 'sourceIdentityPin', 'hostIdentityPin', 'configurationPin', 'nativeConfigPin'):
            self.raw(value[field])
        identity = self.document(value['identityPin'])
        config = self.document(value['nativeConfigPin'])
        from recovery_control_executor import installed_repository
        with installed_repository({'filePins': self.selection['installedFilePins']}):
            from repository_native_lab import SOURCE_FIELDS, HOST_FIELDS
            exact(config, SOURCE_FIELDS.split(), 'SMALLAPP_INITIAL_NATIVE_SOURCE_FIELDS_INVALID')
            host = self.document(config['executionHostPin'])
            exact(host, HOST_FIELDS.split(), 'SMALLAPP_INITIAL_NATIVE_HOST_FIELDS_INVALID')
        source_native_binding(value, identity, config, self.document(value['hostIdentityPin']), host,
                              self.selection['hostBootId'], self.selection['pythonPin'],
                              self.selection['engineSelection']['engineEntryPin'])
        installed = signed_payload(host['installationManifestPin'], self.selection['authorityKeyPin'])
        require(installed['filePins'] == self.selection['installedFilePins'] and
                installed['dependencyPins'] == self.selection['dependencyPins'] and
                installed['pythonPin'] == self.selection['pythonPin'], 'SMALLAPP_INITIAL_SOURCE_INSTALLATION_MISMATCH')
        from recovery_control_executor import installation_shape
        require(installation_shape(installed) == 'RepositoryNativeInstallation/v2', 'SMALLAPP_INITIAL_EXPLICIT_V2_REQUIRED')
        proof = signed_payload(installed['nativeRuntimeProofPin'], self.selection['authorityKeyPin'])
        trust = signed_payload(installed['nativeRuntimeTrustPin'], self.selection['authorityKeyPin'])
        window(proof)
        with installed_repository(installed):
            from repository_native_runtime import _trust_shape, _proof_shape
            _trust_shape(trust); _proof_shape(proof, trust, installed['nativeRuntimeTrustPin'])
        require(trust['runtimeRole'] == 'EXECUTOR' and host['hostOs'] == 'Linux' and
                type(host['uid']) is type(host['gid']) is int and host['uid'] == host['gid'] == 0 and
                all(host[field] == proof[field] for field in ('hostId', 'bootId', 'pidNamespace', 'mountNamespace')),
                'SMALLAPP_INITIAL_SOURCE_CURRENT_RUNTIME_MISMATCH')
        from recovery_control_executor import verify
        require(type(value['versionPins']) is list and value['versionPins'], 'SMALLAPP_INITIAL_SOURCE_VERSIONS_REQUIRED')
        for reference in [value['applicationArtifactPin'], value['runtimePin'], *value['versionPins']]:
            verify(reference)

    def installation_admission(self, installation_pin):
        """Consume the mature owned native verifier's actual signed admission."""
        from recovery_native_installation_admission import (ADMISSION_FIELDS, ADMISSION_SCHEMA,
            invocation_originals, installation_argv, installation_sources)
        from recovery_native_process import LAB_ROOT
        from recovery_native_observation import wire_canonical
        authority = self.selection['authorityKeyPin']
        installation = signed_payload(installation_pin, authority)
        from recovery_control_executor import installation_shape
        require(installation_shape(installation) == 'RepositoryNativeInstallation/v2', 'SMALLAPP_INITIAL_EXPLICIT_V2_REQUIRED')
        require(installation['filePins'] == self.selection['installedFilePins'] and
                installation['dependencyPins'] == self.selection['dependencyPins'] and
                installation['pythonPin'] == self.selection['pythonPin'] and
                installation['sourceToolkitPin'] == self.selection['engineSelection']['engineArtifactPin'],
                'SMALLAPP_INITIAL_CURRENT_INSTALLATION_MISMATCH')
        proof = signed_payload(installation['nativeRuntimeProofPin'], authority); window(proof)
        trust = signed_payload(installation['nativeRuntimeTrustPin'], authority)
        from recovery_control_executor import installed_repository
        with installed_repository(installation):
            from repository_native_runtime import _trust_shape, _proof_shape
            _trust_shape(trust); _proof_shape(proof, trust, installation['nativeRuntimeTrustPin'])
        admission = signed_payload(self.selection['installationAdmissionPin'], authority)
        exact(admission, ADMISSION_FIELDS, 'SMALLAPP_INITIAL_ADMISSION_FIELDS_INVALID'); window(admission)
        from recovery_native_process import REHEARSAL_ID
        require(admission['schemaVersion'] == ADMISSION_SCHEMA and admission['rehearsalId'] == REHEARSAL_ID and
                admission['installationPin'] == installation_pin and trust['runtimeRole'] == 'EXECUTOR' and
                admission['nativeRuntimeTrustPin'] == installation['nativeRuntimeTrustPin'] and
                admission['nativeRuntimeProofPin'] == installation['nativeRuntimeProofPin'] and
                proof['bootId'] == self.selection['hostBootId'], 'SMALLAPP_INITIAL_ADMISSION_SELECTION_MISMATCH')
        _, call, process = invocation_originals(admission['invocationPin'], authority, LAB_ROOT)
        from recovery_native_installation_admission import verify_admission_parent
        from recovery_control_executor import pin
        producer = self.document(admission['producerIdentityPin'])
        parent = self.document(pin(Path(admission['invocationPin']['path']).parent / 'supervisor-terminal.json'))
        verify_admission_parent(parent, process, producer)
        require(all(producer[field] == proof[field] for field in
            ('hostId', 'bootId', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace', 'rootDevice', 'rootInode')),
            'SMALLAPP_INITIAL_ADMISSION_PRODUCER_MISMATCH')
        require(process['operationId'] == call['operationId'] and process['stage'] == call['stage'],
                'SMALLAPP_INITIAL_ADMISSION_OPERATION_MISMATCH')
        entries = [pin for pin in installation['filePins'] if pin['path'].endswith('/recovery_native_launcher.py')]
        require(len(entries) == 1 and call['argv'] == installation_argv(installation, entries[0], installation_pin, authority) and
                process['sourcePins'] == installation_sources(installation, entries[0]) and
                process['pythonPin'] == installation['pythonPin'] and process['uid'] == process['gid'] == 0 and
                process['nativeRuntimeProofPin'] == installation['nativeRuntimeProofPin'] and
                all(process[field] == proof[field] for field in
                    ('hostId', 'bootId', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace')) and
                admission['manifestResultPin'] == call['resultPin'] == process['resultPin'] == process['stdoutPin'] and
                self.raw(admission['manifestResultPin']) == wire_canonical(installation) and
                self.raw(process['stderrPin']) == b'', 'SMALLAPP_INITIAL_ACTUAL_NATIVE_ADMISSION_REQUIRED')
        from recovery_control_smallapp_native import stamp
        require(admission['startedAt'] == call['startedAt'] == process['startedAt'] and
                admission['finishedAt'] == call['finishedAt'] == process['finishedAt'] and
                stamp(proof['issuedAt']) <= stamp(admission['startedAt']) < stamp(admission['finishedAt']) <=
                stamp(admission['issuedAt']) and stamp(admission['expiresAt']) <= stamp(proof['expiresAt']),
                'SMALLAPP_INITIAL_NATIVE_ADMISSION_WINDOW_MISMATCH')
        from recovery_control_registration import engine
        from recovery_control_executor import pin
        import recovery_control_executor
        engine(self.selection['engineSelection'], installation, pin(Path(recovery_control_executor.__file__).resolve()))
        return installation

    def on_ready(self, signer_pid):
        """Actual separate signer and key denial precede any signing request."""
        self.guard()
        from recovery_native_process import persist_bytes
        from recovery_native_observation import wire_canonical
        measured = initial_key_denial(self, signer_pid)
        return persist_bytes(lab_path(self.selection['outputRoot'], directory=True) /
            (self.selection['originalPin']['sha256'] + '.key-denial.json'), wire_canonical(measured))


def source_native_binding(resource, identity, config, host_identity, host, boot, python_pin, dispatcher_pin):
    """Consume W03's real source and host originals; never derive identity from metadata."""
    require(type(identity.get('sourceFingerprint')) is str and identity['sourceFingerprint'] and
            identity.get('databaseUuid') == resource['databaseUuid'] and
            config['schemaVersion'] == 'RepositoryNativeBackupSource/v1' and
            config['sourceIdentityPin'] == resource['sourceIdentityPin'], 'SMALLAPP_INITIAL_SOURCE_CONFIG_MISMATCH')
    require(host['schemaVersion'] == 'RepositoryNativeExecutionHost/v1' and
            host['hostId'] == host_identity['hostId'] and host['bootId'] == host_identity['bootId'] == boot and
            config['pythonPin'] == host['pythonPin'] == resource['runtimePin'] == python_pin and
            config['resourceObserverPin'] == host['resourceObserverPin'] and host['dispatcherPin'] == dispatcher_pin,
            'SMALLAPP_INITIAL_SOURCE_HOST_MISMATCH')


def initial_key_denial(context, signer_pid):
    """Owned native probe uses the mature namespace/capability custody primitives."""
    import errno
    import os
    import signal
    import time
    from recovery_native_launcher import native_call, drop_capabilities, measure_process, status
    producer = context.producer
    root = os.open(f'/proc/{producer["pid"]}/root', os.O_RDONLY | os.O_DIRECTORY)
    namespace = os.open(f'/proc/{producer["pid"]}/ns/mnt', os.O_RDONLY)
    reader, writer = os.pipe(); gate_reader, gate_writer = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(reader); native_call('setns', namespace, 0)
            os.fchdir(root); os.chroot('.'); os.chdir('/')
            start = 3
            for descriptor in sorted((writer, gate_reader)):
                os.closerange(start, descriptor); start = descriptor + 1
            os.closerange(start, os.sysconf('SC_OPEN_MAX'))
            drop_capabilities(producer['uid'], producer['gid'], 0)
            require(os.statvfs('/').f_flag & os.ST_RDONLY, 'SMALLAPP_INITIAL_WORKER_ROOT_NOT_READONLY')
            os.write(writer, b'R')
            require(os.read(gate_reader, 1) == b'G', 'SMALLAPP_INITIAL_PROBE_NOT_SELECTED')
            paths = [context.selection['privateKeyReference']['path'],
                f'/proc/{signer_pid}/root' + context.selection['privateKeyReference']['path'], f'/proc/{signer_pid}/mem']
            for path in paths:
                try: fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                except OSError as error:
                    require(error.errno in (errno.EACCES, errno.EPERM, errno.ENOENT), 'SMALLAPP_INITIAL_KEY_DENIAL_ERROR')
                else:
                    os.close(fd); require(False, 'SMALLAPP_INITIAL_WORKER_CAN_OPEN_KEY')
            os.write(writer, b'DENIED'); os._exit(0)
        except BaseException as error:
            import sys
            print('SMALLAPP_INITIAL_KEY_DENIAL_FAILED:' + getattr(error, 'code', type(error).__name__),
                  file=sys.stderr, flush=True)
            os._exit(1)
    os.close(writer); os.close(root); os.close(namespace); os.close(gate_reader)
    terminal = None
    try:
        import select
        require(select.select([reader], [], [], max(0, context.deadline - time.monotonic()))[0] and
                os.read(reader, 1) == b'R', 'SMALLAPP_INITIAL_PROBE_NOT_READY')
        actual_probe = measure_process(child); probe_status = status(child)
        require(all(actual_probe[field] == producer[field] for field in
                    ('uid', 'gid', 'rootDevice', 'rootInode', 'mountNamespace')) and
                all(int(probe_status[name], 16) == 0 for name in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                int(probe_status.get('CapAmb', '0'), 16) == 0 and probe_status['NoNewPrivs'] == '1' and
                not probe_status['Groups'].split(), 'SMALLAPP_INITIAL_PROBE_CONTEXT_MISMATCH')
        os.write(gate_writer, b'G')
        require(select.select([reader], [], [], max(0, context.deadline - time.monotonic()))[0] and
                os.read(reader, 7) == b'DENIED', 'SMALLAPP_INITIAL_ACTUAL_KEY_DENIAL_REQUIRED')
        while terminal is None:
            require(time.monotonic() < context.deadline, 'SMALLAPP_INITIAL_KEY_DENIAL_DEADLINE')
            pid, value = os.waitpid(child, os.WNOHANG)
            if pid: terminal = value
            else: select.select([], [], [], .01)
        require(os.WIFEXITED(terminal) and os.WEXITSTATUS(terminal) == 0,
                'SMALLAPP_INITIAL_KEY_DENIAL_CHILD_FAILED')
        signer = measure_process(signer_pid)
        values = status(signer_pid)
        require(signer['uid'] == context.selection['signerUid'] and signer['gid'] == context.selection['signerGid'] and
                signer['mountNamespace'] != producer['mountNamespace'] and
                all(int(values[name], 16) == 0 for name in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                int(values.get('CapAmb', '0'), 16) == 0 and values['NoNewPrivs'] == '1' and
                not values['Groups'].split(), 'SMALLAPP_INITIAL_CURRENT_SIGNER_ROLE_REQUIRED')
        from recovery_environment_contract import utc_now
        return dict(selectionPin=context.selection_pin, worker=producer, signer=signer, probeIdentity=actual_probe,
            probeCapabilities={name: probe_status[name] for name in
                ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'NoNewPrivs')}, actualWaitStatus=terminal,
            soleParentPid=os.getpid(), deniedOpenCount=3, measuredAt=utc_now())
    finally:
        os.close(reader); os.close(gate_writer)
        if terminal is None:
            os.kill(child, signal.SIGKILL); os.waitpid(child, 0)


def initial_custodian_entry(selection_pin):
    """Execute one finite approval with the existing 0600 capability-free role."""
    import base64
    import os
    import signal
    from recovery_native_launcher import native_call, drop_capabilities
    from recovery_native_process import open_lab_file, file_metadata, persist_bytes, authenticate_payload
    from recovery_native_observation import receive_frame, send_frame, wire_canonical
    context = InitialCustodianContext(selection_pin)
    selection = context.selection
    value = context.document(selection['originalPin'])
    context.admit(value)
    output = lab_path(selection['outputRoot'], directory=True)
    info = output.stat()
    require(info.st_uid == info.st_gid == 0 and stat.S_IMODE(info.st_mode) == 0o700,
            'SMALLAPP_INITIAL_ROOT_OUTPUT_CUSTODY_REQUIRED')
    root = lab_path(selection['signerRootPath'], directory=True)
    mirrored_key = root / selection['privateKeyReference']['path'].lstrip('/')
    metadata = mirrored_key.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and
            metadata.st_uid == selection['signerUid'] and metadata.st_gid == selection['signerGid'] and
            stat.S_IMODE(metadata.st_mode) == 0o600, 'SMALLAPP_INITIAL_PRIVATE_PROVISION_REQUIRED')
    require(os.statvfs(mirrored_key).f_flag & os.ST_RDONLY, 'SMALLAPP_INITIAL_PRIVATE_KEY_VIEW_NOT_READONLY')
    reservation = output / ('initial-reservation-' + selection['originalPin']['sha256'] + '.json')
    persist_bytes(reservation, wire_canonical({'selectionPin': selection_pin, 'retryAllowed': False}))
    import socket
    parent, channel = socket.socketpair()
    child = os.fork()
    if child == 0:
        try:
            parent.close(); native_call('unshare', 0x20000)
            native_call('mount', None, b'/', None, (1 << 18) | 16384, None)
            os.chroot(root); os.chdir('/')
            drop_capabilities(selection['signerUid'], selection['signerGid'], 0)
            # Only the independently created parent channel survives the fork.
            descriptor = channel.fileno()
            os.closerange(3, descriptor); os.closerange(descriptor + 1, os.sysconf('SC_OPEN_MAX'))
            fd, directory_fd = open_lab_file(selection['privateKeyReference']['path'], os.O_RDONLY)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                        before.st_uid == os.geteuid() and before.st_gid == os.getegid() and
                        stat.S_IMODE(before.st_mode) == 0o600 and 0 < before.st_size <= 8192,
                        'SMALLAPP_INITIAL_PRIVATE_KEY_CUSTODY_REQUIRED')
                secret = os.read(fd, 8193)
                reopened, reopened_parent = open_lab_file(selection['privateKeyReference']['path'], os.O_RDONLY)
                try:
                    require(len(secret) == before.st_size and file_metadata(before) == file_metadata(os.fstat(fd)) ==
                            file_metadata(os.fstat(reopened)), 'SMALLAPP_INITIAL_PRIVATE_KEY_CHANGED')
                finally:
                    os.close(reopened); os.close(reopened_parent)
            finally:
                os.close(fd); os.close(directory_fd)
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            key = serialization.load_pem_private_key(secret, password=None); del secret
            require(isinstance(key, Ed25519PrivateKey), 'SMALLAPP_INITIAL_PRIVATE_KEY_TYPE')
            send_frame(channel, {'state': 'READY'}, context.deadline)
            message = receive_frame(channel, context.deadline)
            exact(message, {'publicKey', 'payload'}, 'SMALLAPP_INITIAL_PARENT_FRAME_INVALID')
            public = base64.b64decode(message['publicKey'], validate=True)
            require(key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo) == public,
                    'SMALLAPP_INITIAL_PRIVATE_PUBLIC_KEY_MISMATCH')
            require(message['payload'] == value, 'SMALLAPP_INITIAL_PARENT_ORIGINAL_CHANGED')
            envelope = dict(schemaVersion='RepositorySignedRecord/v1', keySha256=selection['authorityKeyPin']['sha256'],
                payload=value, signature=base64.b64encode(key.sign(wire_canonical(value))).decode('ascii'))
            send_frame(channel, envelope, context.deadline); channel.close(); os._exit(0)
        except BaseException as error:
            import sys
            print('SMALLAPP_INITIAL_SIGNER_FAILED:' + getattr(error, 'code', type(error).__name__), file=sys.stderr, flush=True)
            os._exit(1)
    channel.close(); terminal = None
    try:
        ready = receive_frame(parent, context.deadline)
        require(ready == {'state': 'READY'}, 'SMALLAPP_INITIAL_READY_REQUIRED')
        key_denial_pin = context.on_ready(child); context.admit(value)
        require(context.document(selection['originalPin']) == value, 'SMALLAPP_INITIAL_ORIGINAL_CHANGED')
        public = context.raw(selection['authorityKeyPin'])
        send_frame(parent, {'publicKey': base64.b64encode(public).decode('ascii'), 'payload': value}, context.deadline)
        envelope = receive_frame(parent, context.deadline)
        require(authenticate_payload(envelope, public, selection['authorityKeyPin']['sha256']) == value,
                'SMALLAPP_INITIAL_SIGNED_ORIGINAL_MISMATCH')
        import select
        import time
        while terminal is None:
            require(time.monotonic() < context.deadline, 'SMALLAPP_INITIAL_SIGNER_DEADLINE')
            pid, wait = os.waitpid(child, os.WNOHANG)
            if pid: terminal = wait
            else: select.select([], [], [], .01)
        require(os.WIFEXITED(terminal) and os.WEXITSTATUS(terminal) == 0, 'SMALLAPP_INITIAL_SIGNER_CHILD_FAILED')
        context.admit(value)
        signed = persist_bytes(output / (selection['originalPin']['sha256'] + '.initial.signed.json'), wire_canonical(envelope))
        return dict(signedPin=signed, keyDenialEvidencePin=key_denial_pin, kind=selection['kind'], nativeInstallationVerified=False,
                    serviceStarted=False, sourceOpened=False, businessDispatched=False)
    finally:
        parent.close()
        if terminal is None:
            os.kill(child, signal.SIGKILL); os.waitpid(child, 0)


OPERATION_AUTHORITY_FIELDS = set(('schemaVersion batchId issuancePlanPin installationAdmissionPin authorityKeyPin '
    'producerIdentityPin custodianIdentityPin issuerEntryPin signerUid signerGid signerRootPath privateKeyPin '
    'originalRoot socketPath outputRoot engineSelection issuedAt expiresAt deadlineMilliseconds').split())


def operation_public_pins(selection, references):
    """Only the separate A child may consume its private key Pin."""
    from recovery_control_executor import pin_reference
    for reference in references:
        pin_reference(reference)
    operation_public_paths(selection, [reference['path'] for reference in references])


def operation_public_paths(selection, paths):
    """Metadata only: refuse both private views and bind/hard-link inode aliases."""
    key_path = Path(selection['privateKeyPin']['path'])
    private_root = Path(selection['signerRootPath'])
    candidates = [Path(path) for path in paths]
    for path in candidates:
        require(path != key_path and path != private_root and private_root not in path.parents,
                'SMALLAPP_OPERATION_KEY_HASH_INPUT_REFUSED')
        resolved = path.resolve()
        require(resolved != private_root.resolve() and private_root.resolve() not in resolved.parents,
                'SMALLAPP_OPERATION_KEY_HASH_INPUT_REFUSED')
    mirrored = private_root / selection['privateKeyPin']['path'].lstrip('/')
    private_files = [mirrored.stat()]
    if key_path.exists():
        private_files.append(key_path.stat())
    private_inodes = {(info.st_dev, info.st_ino) for info in private_files}
    for path in candidates:
        info = path.stat()
        require((info.st_dev, info.st_ino) not in private_inodes, 'SMALLAPP_OPERATION_KEY_HASH_INPUT_REFUSED')


def operation_public_record(selection, value):
    from recovery_native_launcher import selected_graph_pins
    operation_public_pins(selection, selected_graph_pins([value]))


INSTALLATION_SELECTION_FIELDS = (OPERATION_AUTHORITY_FIELDS - {'issuancePlanPin', 'installationAdmissionPin'} |
    {'approvalPin', 'installationPin', 'sourceIdentityPin', 'initializationId', 'workingDirectory', 'serviceBindingPin'})
INSTALLATION_APPROVAL_FIELDS = (INSTALLATION_SELECTION_FIELDS -
    {'schemaVersion', 'approvalPin', 'privateKeyPin', 'signerRootPath', 'socketPath', 'outputRoot'} |
    {'schemaVersion', 'approved', 'scope'})


def installation_selection_shape(selection, approval):
    from recovery_control_executor import pin_reference
    from recovery_control_registration import inside, ENGINE_FIELDS
    exact(selection, INSTALLATION_SELECTION_FIELDS, 'SMALLAPP_INSTALLATION_SELECTION_FIELDS_INVALID')
    exact(approval, INSTALLATION_APPROVAL_FIELDS, 'SMALLAPP_INSTALLATION_APPROVAL_FIELDS_INVALID')
    require(selection['schemaVersion'] == 'SmallAppInstallationAdmissionSelection/v1' and selection['batchId'] == BATCH and
            approval['schemaVersion'] == 'SmallAppInstallationAdmissionApproval/v1' and approval['approved'] is True and
            approval['scope'] == 'INITIALIZE_TASK_SOURCE_SERVICE' and
            all(approval[k] == selection[k] for k in INSTALLATION_APPROVAL_FIELDS - {'schemaVersion', 'approved', 'scope'}),
            'SMALLAPP_INSTALLATION_INDEPENDENT_APPROVAL_REQUIRED')
    window(selection); window(approval)
    require(type(selection['initializationId']) is str and selection['initializationId'].startswith('installation-') and
            all(c.isalnum() or c in '-_' for c in selection['initializationId']) and
            type(selection['deadlineMilliseconds']) is int and 0 < selection['deadlineMilliseconds'] <= 300000 and
            type(selection['signerUid']) is type(selection['signerGid']) is int and
            selection['signerUid'] > 0 and selection['signerGid'] > 0,
            'SMALLAPP_INSTALLATION_FINITE_ROLE_REQUIRED')
    for field in ('approvalPin', 'installationPin', 'authorityKeyPin', 'sourceIdentityPin', 'producerIdentityPin',
                  'custodianIdentityPin', 'issuerEntryPin', 'serviceBindingPin', 'privateKeyPin'):
        pin_reference(selection[field]); inside(selection[field]['path'])
    for field in ('signerRootPath', 'socketPath', 'outputRoot', 'originalRoot', 'workingDirectory'):
        inside(selection[field])
    exact(selection['engineSelection'], ENGINE_FIELDS.split(), 'ENGINE_SELECTION_FIELDS_INVALID')
    require(selection['producerIdentityPin'] != selection['custodianIdentityPin'] and
            selection['approvalPin'] != selection['installationPin'], 'SMALLAPP_INSTALLATION_SELF_APPROVAL_REFUSED')


class InstallationAdmissionContext:
    """Finite technical installation admission, with an independent root original."""

    def __init__(self, selection_pin, *, parent_role):
        import os
        import sys
        import time
        require(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0,
                'SMALLAPP_INSTALLATION_NATIVE_ROOT_REQUIRED')
        self.selection_pin = self.launch_pin = selection_pin
        self.parent_role = parent_role
        self.deadline = time.monotonic() + 300
        self.selection = {}
        self.selection = self.document(selection_pin)
        self.original_selection = self.selection
        self.approval = self.document(self.selection['approvalPin'])
        installation_selection_shape(self.selection, self.approval)
        self.deadline = time.monotonic() + self.selection['deadlineMilliseconds'] / 1000
        if parent_role:
            OperationAuthorityContext.public_graph(self)
        self.authority_pin = self.selection['authorityKeyPin']
        self.installation = signed_payload(self.selection['installationPin'], self.authority_pin)
        from recovery_control_executor import installation_shape
        require(installation_shape(self.installation) == 'RepositoryNativeInstallation/v2', 'SMALLAPP_INITIAL_EXPLICIT_V2_REQUIRED')
        self.proof_pin = self.installation['nativeRuntimeProofPin']
        self.proof = signed_payload(self.proof_pin, self.authority_pin)
        self.trust = signed_payload(self.installation['nativeRuntimeTrustPin'], self.authority_pin)
        self.selection = {**self.selection, 'installedFilePins': self.installation['filePins'],
            'dependencyPins': self.installation['dependencyPins'], 'pythonPin': self.installation['pythonPin'],
            'hostBootId': self.proof['bootId']}
        self.producer = self.producer_identity = self.document(self.selection['producerIdentityPin'])
        self.custodian = self.document(self.selection['custodianIdentityPin'])
        self.provision = dict(privateKeyPin=self.selection['privateKeyPin'], signerSocketPath=self.selection['socketPath'],
            signerUid=self.selection['signerUid'], signerGid=self.selection['signerGid'])
        self.native_tool_pins, self.commands = [], []
        self.launch = dict(installationPin=self.selection['installationPin'], evidenceRoot=self.selection['originalRoot'])
        from recovery_control_smallapp_native import stamp
        self.expires_at = min(self.selection['expiresAt'], self.proof['expiresAt'], key=stamp)
        from recovery_native_installation_admission import installation_argv, installation_sources
        entries = [p for p in self.installation['filePins'] if p['path'].endswith('/ops/recovery/recovery_native_launcher.py')]
        require(len(entries) == 1, 'SMALLAPP_INSTALLATION_LAUNCHER_REQUIRED')
        self.entry_pin = entries[0]
        self.installation_command = installation_argv(self.installation, self.entry_pin, self.selection['installationPin'], self.authority_pin)
        self.sources = installation_sources(self.installation, self.entry_pin)
        self.operation_binding = dict(operationId=self.selection['initializationId'], restoreId=None,
            targetIdentityPin=None, recoveryPoint=None, stage='INSTALLATION_ADMISSION')
        self.command_id = 'observe-1-installation_admission-installation'
        self.guard()

    def raw(self, reference):
        if self.parent_role:
            return OperationAuthorityContext.raw(self, reference)
        # The native producer is capability-free; only root-private public originals are eligible.
        info = Path(reference['path']).stat()
        require(info.st_uid == 0 and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'SMALLAPP_INSTALLATION_PUBLIC_ORIGINAL_REQUIRED')
        if 'privateKeyPin' in self.selection:
            require(reference['path'] != self.selection['privateKeyPin']['path'] and
                    Path(self.selection['signerRootPath']) not in Path(reference['path']).parents,
                    'SMALLAPP_OPERATION_KEY_HASH_INPUT_REFUSED')
        if hasattr(self, 'command_id'):
            original_directory = Path(self.selection['originalRoot']) / self.command_id
            path = Path(reference['path'])
            if path.parent == original_directory and path.name in {
                    'stdout', 'stderr', 'supervisor-terminal.json', 'process-original.json', 'invocation.json'}:
                # These exact originals were written by this root EXECUTOR.
                # A and its parent consume their separately mounted readonly
                # views; the producing namespace keeps its own output writable.
                from recovery_native_browser import descriptor_read
                return descriptor_read(reference, owners={0}, owner_gid=0, deadline=self.deadline,
                                       modes=(0o600,), readonly=False)
        return InitialCustodianContext.raw(self, reference)

    def document(self, reference):
        return decode(self.raw(reference))

    def public_pin(self, path):
        return OperationAuthorityContext.public_pin(self, path)

    def guard(self):
        import os
        import time
        from recovery_native_launcher import match_process, status
        from recovery_control_executor import installed_repository, pin, verify
        if self.parent_role:
            OperationAuthorityContext.public_graph(self)
        require(time.monotonic() < self.deadline and self.document(self.selection_pin) == self.original_selection and
                self.document(self.selection['approvalPin']) == self.approval,
                'SMALLAPP_INSTALLATION_CURRENT_PERMISSION_CHANGED')
        installation_selection_shape(self.original_selection, self.approval)
        for reference, value in ((self.selection['installationPin'], self.installation),
                                (self.proof_pin, self.proof), (self.installation['nativeRuntimeTrustPin'], self.trust)):
            require(signed_payload(reference, self.authority_pin) == value, 'SMALLAPP_INSTALLATION_CURRENT_INPUT_CHANGED')
        window(self.proof)
        with installed_repository(self.installation):
            from repository_native_runtime import _trust_shape, _proof_shape, verify_native_installation
            _trust_shape(self.trust); _proof_shape(self.proof, self.trust, self.installation['nativeRuntimeTrustPin'])
            if not self.parent_role:
                require(verify_native_installation(self.selection['installationPin'], [self.authority_pin],
                    deadline=self.deadline) == self.installation, 'SMALLAPP_INSTALLATION_EXECUTOR_CHANGED')
        require(self.trust['runtimeRole'] == 'EXECUTOR' and self.producer['bootId'] == self.custodian['bootId'] == self.proof['bootId'] and
                self.producer['pid'] != self.custodian['pid'] and self.producer['mountNamespace'] != self.custodian['mountNamespace'],
                'SMALLAPP_INSTALLATION_CURRENT_ROLE_REQUIRED')
        if self.parent_role:
            match_process(self.custodian, os.getpid(), 0)
        else:
            match_process(self.producer, os.getpid(), 0)
        match_process(self.producer, self.producer['pid'], 0)
        require(all(self.producer[k] == self.proof[k] for k in
            ('hostId', 'bootId', 'rootDevice', 'rootInode', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace')),
            'SMALLAPP_INSTALLATION_PRODUCER_PROOF_MISMATCH')
        values = status(self.producer['pid'])
        require(all(int(values[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb')) and
                values['NoNewPrivs'] == '1' and not values['Groups'].split(), 'SMALLAPP_INSTALLATION_EXECUTOR_CAPABILITIES')
        require(pin(Path(__file__).resolve()) == self.selection['issuerEntryPin'] and
                self.selection['issuerEntryPin'] in self.installation['filePins'], 'SMALLAPP_OPERATION_ENTRY_NOT_INSTALLED')
        from recovery_control_registration import engine
        import recovery_control_executor
        engine(self.selection['engineSelection'], self.installation, pin(Path(recovery_control_executor.__file__).resolve()))
        for reference in [*self.installation['filePins'], *self.installation['dependencyPins'], self.installation['pythonPin']]:
            verify(reference)
        identity = self.document(self.selection['sourceIdentityPin'])
        require(type(identity.get('sourceFingerprint')) is str and identity['sourceFingerprint'] and
                type(identity.get('databaseUuid')) is str and identity['databaseUuid'],
                'SMALLAPP_INSTALLATION_ACTUAL_SOURCE_IDENTITY_REQUIRED')
        from recovery_control_smallapp_controls import service_configuration
        service = service_configuration(self.document(self.selection['serviceBindingPin']))
        require(service['installationPin'] == self.selection['installationPin'] and
                service['authorityKeyPin'] == self.authority_pin and service['engineSelection'] == self.selection['engineSelection'],
                'SMALLAPP_INSTALLATION_SERVICE_BINDING_MISMATCH')

    def dispatch_guard(self, payload):
        self.guard()
        require(all(payload[k] == v for k, v in self.operation_binding.items()) and
                payload['commandId'] == self.command_id and payload['argv'] == self.installation_command and
                payload['cwd'] == self.selection['workingDirectory'] and payload['sourcePins'] == self.sources,
                'SMALLAPP_INSTALLATION_ONLY_DISPATCH_REQUIRED')

    def signing_runtime(self, value):
        from recovery_native_installation_admission import ADMISSION_SCHEMA
        require(value['schemaVersion'] in ('RecoveryNativeProcessResult/v1', ADMISSION_SCHEMA),
                'SMALLAPP_INSTALLATION_RECORD_UNSUPPORTED')
        return self.proof_pin

    def admit(self, value):
        if self.parent_role:
            OperationAuthorityContext.public_graph(self, extra_roots=[value])
        self.guard(); self.signing_runtime(value)
        from recovery_native_process import PROCESS_FIELDS, LAB_ROOT
        from recovery_native_installation_admission import ADMISSION_FIELDS, invocation_originals, verify_admission_parent
        from recovery_native_signer import verify_parent_terminal
        from recovery_native_observation import wire_canonical
        from recovery_control_smallapp_native import stamp
        if value['schemaVersion'] == 'RecoveryNativeProcessResult/v1':
            exact(value, PROCESS_FIELDS, 'SMALLAPP_INSTALLATION_PROCESS_FIELDS_INVALID')
            self.dispatch_guard(value)
            parent_path = Path(self.selection['originalRoot']) / self.command_id / 'supervisor-terminal.json'
            if self.parent_role:
                parent_pin = self.public_pin(parent_path)
            else:
                from recovery_control_executor import pin
                parent_pin = pin(parent_path)
            parent = self.document(parent_pin)
            verify_parent_terminal(value, parent); verify_admission_parent(parent, value, self.producer_identity)
            original_path = parent_path.with_name('process-original.json')
            if self.parent_role:
                original_pin = self.public_pin(original_path)
            else:
                from recovery_control_executor import pin
                original_pin = pin(original_path)
            require(self.document(original_pin) == value, 'SMALLAPP_INSTALLATION_PROCESS_ORIGINAL_CHANGED')
            installation_process_result(value, self.installation, self.proof, self.operation_binding,
                self.command_id, self.installation_command, self.sources, self.selection['workingDirectory'])
            require(self.raw(value['stdoutPin']) == wire_canonical(self.installation) and self.raw(value['stderrPin']) == b'',
                    'SMALLAPP_INSTALLATION_MANIFEST_RESULT_REQUIRED')
        else:
            exact(value, ADMISSION_FIELDS, 'SMALLAPP_INITIAL_ADMISSION_FIELDS_INVALID'); window(value)
            require(value['rehearsalId'] == self.proof['rehearsalId'] and value['collectionId'] == self.selection['initializationId'] and
                    value['sequence'] == 1 and value['phase'] == 'INSTALLATION_ADMISSION' and
                    value['operationRequestPin'] == value['launchPin'] == self.selection_pin and
                    value['serviceBindingPin'] == self.selection['serviceBindingPin'] and
                    value['installationPin'] == self.selection['installationPin'] and
                    value['nativeRuntimeTrustPin'] == self.installation['nativeRuntimeTrustPin'] and
                    value['nativeRuntimeProofPin'] == self.proof_pin and value['producerIdentityPin'] == self.selection['producerIdentityPin'],
                    'SMALLAPP_INSTALLATION_ADMISSION_BINDING_MISMATCH')
            _, call, process = invocation_originals(value['invocationPin'], self.authority_pin, LAB_ROOT)
            self.admit(process)
            require(value['manifestResultPin'] == call['resultPin'] == process['stdoutPin'] and
                    value['startedAt'] == call['startedAt'] and value['finishedAt'] == call['finishedAt'] and
                    max(stamp(self.selection['issuedAt']), stamp(self.approval['issuedAt'])) <= stamp(value['startedAt']) and
                    stamp(value['finishedAt']) <= stamp(value['issuedAt']) and
                    stamp(value['expiresAt']) <= stamp(self.expires_at), 'SMALLAPP_INSTALLATION_ADMISSION_RESULT_MISMATCH')

    def on_ready(self, signer_pid):
        OperationAuthorityContext.on_ready(self, signer_pid)

    def completed(self):
        from recovery_control_executor import pin
        original = self.public_pin(Path(self.selection['originalRoot']) / 'observe-1-installation_admission-installation-original.json')
        signed = self.public_pin(Path(self.selection['socketPath']).parent / (original['sha256'] + '.signed.json'))
        value = signed_payload(signed, self.authority_pin)
        require(value == self.document(original), 'SMALLAPP_INSTALLATION_ADMISSION_ORIGINAL_CHANGED')
        self.admit(value)
        return dict(installationAdmissionPin=signed, nativeInstallationAdmissionVerified=True,
                    serviceStarted=False, businessDispatched=False)


def installation_process_result(value, installation, proof, binding, command_id, argv, sources, cwd):
    from recovery_control_smallapp_native import stamp
    require(all(value[k] == v for k, v in binding.items()) and value['commandId'] == command_id and
            value['argv'] == argv and value['sourcePins'] == sources and value['cwd'] == cwd and
            value['pythonPin'] == installation['pythonPin'] and value['nativeRuntimeProofPin'] == installation['nativeRuntimeProofPin'] and
            value['uid'] == value['gid'] == 0 and value['terminationKind'] == 'EXITED' and
            type(value['actualExitCode']) is type(value['waitStatus']) is int and
            value['actualExitCode'] == value['waitStatus'] == 0 and value['descendantState'] == 'REAPED' and
            value['resultPin'] == value['stdoutPin'] and all(value[k] == proof[k] for k in
                ('hostId', 'bootId', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace')) and
            stamp(proof['issuedAt']) <= stamp(value['startedAt']) < stamp(value['finishedAt']) <= stamp(proof['expiresAt']),
            'SMALLAPP_INSTALLATION_ACTUAL_EXIT_AND_MANIFEST_REQUIRED')
    from recovery_native_observation import wire_canonical
    require(value['command'] == wire_canonical(argv).decode('utf-8'), 'SMALLAPP_INSTALLATION_LITERAL_COMMAND_REQUIRED')


def installation_authority_entry(selection_pin):
    return _native_authority_entry(InstallationAdmissionContext(selection_pin, parent_role=True), installation=True)


def installation_producer_entry(selection_pin, authority_identity_pin):
    from recovery_native_launcher import selected_producer_process, finish_authority
    from recovery_native_process import persist_bytes, REHEARSAL_ID
    from recovery_native_observation import wire_canonical
    from recovery_environment_contract import utc_now
    from recovery_control_executor import installed_repository
    context = InstallationAdmissionContext(selection_pin, parent_role=False)
    with installed_repository(context.installation):
        peer, signer, process = selected_producer_process(context, authority_identity_pin)
        invocation = process.run(command_id=context.command_id, argv=context.installation_command,
            cwd=context.selection['workingDirectory'], source_pins=context.sources, binding=context.operation_binding)
        call = decode(pinned_bytes(invocation))
        admission = dict(schemaVersion='RepositoryLabNativeInstallationAdmission/v1', rehearsalId=REHEARSAL_ID,
            collectionId=context.selection['initializationId'], sequence=1, phase='INSTALLATION_ADMISSION',
            operationRequestPin=selection_pin, serviceBindingPin=context.selection['serviceBindingPin'], launchPin=selection_pin,
            installationPin=context.selection['installationPin'], nativeRuntimeTrustPin=context.installation['nativeRuntimeTrustPin'],
            nativeRuntimeProofPin=context.proof_pin, producerIdentityPin=context.selection['producerIdentityPin'],
            invocationPin=invocation, manifestResultPin=call['resultPin'], startedAt=call['startedAt'],
            finishedAt=call['finishedAt'], issuedAt=utc_now(), expiresAt=context.expires_at)
        context.admit(admission)
        original = persist_bytes(process.root / 'observe-1-installation_admission-installation-original.json', wire_canonical(admission))
        signed = signer.sign(original, deadline=context.deadline, worker_uid=0)
        require(signed_payload(signed, context.authority_pin) == admission, 'SMALLAPP_INSTALLATION_SIGNED_ADMISSION_CHANGED')
        finish_authority(context, peer)
        # Keep the measured producer live until its independent parent has
        # reaped A and validated the same signed admission. No inferred exit.
        import time
        completion_path = Path(context.selection['outputRoot']) / ('installation-completion-' + selection_pin['sha256'] + '.json')
        while not completion_path.exists():
            context.guard()
            time.sleep(min(.05, max(0, context.deadline - time.monotonic())))
        from recovery_control_executor import pin
        completion = context.document(pin(completion_path))
        exact(completion, 'schemaVersion selectionPin installationAdmissionPin signerPid terminationKind actualExitCode waitStatus descendantState'.split(),
              'SMALLAPP_INSTALLATION_COMPLETION_FIELDS_INVALID')
        require(completion == dict(schemaVersion='SmallAppInstallationAuthorityCompletion/v1', selectionPin=selection_pin,
            installationAdmissionPin=signed, signerPid=peer['pid'], terminationKind='EXITED', actualExitCode=0,
            waitStatus=0, descendantState='REAPED'), 'SMALLAPP_INSTALLATION_PARENT_COMPLETION_REQUIRED')
        return dict(installationAdmissionPin=signed, nativeInstallationAdmissionVerified=True,
                    serviceStarted=False, businessDispatched=False)


SERVICE_INITIALIZATION_FIELDS = set(('schemaVersion batchId approvalPin serviceConfigurationPin sourceBindingPin '
    'registrationPin expectedRegistrationPin expectedSourceBindingPin authorityKeyPin installationAdmissionPin '
    'deadlineMilliseconds issuedAt expiresAt').split())
SERVICE_INITIALIZATION_APPROVAL_FIELDS = (SERVICE_INITIALIZATION_FIELDS - {'approvalPin'} | {'approved', 'scope'})


def service_initialization_shape(selection, approval):
    from recovery_control_executor import pin_reference
    from recovery_control_registration import inside
    exact(selection, SERVICE_INITIALIZATION_FIELDS, 'SMALLAPP_SERVICE_INITIALIZATION_FIELDS_INVALID')
    exact(approval, SERVICE_INITIALIZATION_APPROVAL_FIELDS, 'SMALLAPP_SERVICE_INITIALIZATION_APPROVAL_FIELDS_INVALID')
    require(selection['schemaVersion'] == 'SmallAppServiceInitializationSelection/v1' and selection['batchId'] == BATCH and
        approval['schemaVersion'] == 'SmallAppServiceInitializationApproval/v1' and approval['approved'] is True and
        approval['scope'] == 'INITIALIZE_TASK_SOURCE_SERVICE' and all(approval[k] == selection[k] for k in
            SERVICE_INITIALIZATION_FIELDS - {'schemaVersion', 'approvalPin'}), 'SMALLAPP_SERVICE_INDEPENDENT_APPROVAL_REQUIRED')
    window(selection); window(approval)
    require(type(selection['deadlineMilliseconds']) is int and 0 < selection['deadlineMilliseconds'] <= 300000,
            'SMALLAPP_SERVICE_INITIALIZATION_DEADLINE_REQUIRED')
    for field in ('approvalPin', 'serviceConfigurationPin', 'sourceBindingPin', 'registrationPin', 'authorityKeyPin',
                  'installationAdmissionPin', 'expectedRegistrationPin', 'expectedSourceBindingPin'):
        if field in ('expectedRegistrationPin', 'expectedSourceBindingPin') and selection[field] is None:
            continue
        pin_reference(selection[field]); inside(selection[field]['path'])
    require(selection['approvalPin'] not in [selection[field] for field in
        ('serviceConfigurationPin', 'sourceBindingPin', 'registrationPin', 'authorityKeyPin', 'installationAdmissionPin')],
        'SMALLAPP_SERVICE_SELF_APPROVAL_REFUSED')


def initialize_service_entry(selection_pin):
    """Initialize the selected signed SOURCE and enter the actual HTTP service."""
    import time
    from recovery_control_smallapp import native_required, serve
    from recovery_control_smallapp_native import Native
    from recovery_control_registration import Registry, metadata, publish_registration
    from recovery_control_executor import installed_repository
    native_required()
    # The selection and approval are actual immutable root originals. This
    # context only consumes already signed records and never starts a signer.
    context = object.__new__(InitialCustodianContext)
    context.deadline = time.monotonic() + 300
    context.selection = {}
    selected = context.document(selection_pin)
    exact(selected, SERVICE_INITIALIZATION_FIELDS, 'SMALLAPP_SERVICE_INITIALIZATION_FIELDS_INVALID')
    context.selection = selected
    approval = context.document(selected['approvalPin'])
    service_initialization_shape(selected, approval)
    context.deadline = time.monotonic() + selected['deadlineMilliseconds'] / 1000
    native = Native(selected['serviceConfigurationPin'], selected['authorityKeyPin'])
    config = native.configuration()
    from recovery_control_smallapp_controls import service_configuration
    service_configuration(config)
    installation = native.signed(config['installationPin'])
    proof = native.signed(installation['nativeRuntimeProofPin'])
    admission = native.signed(selected['installationAdmissionPin'])
    from recovery_native_installation_admission import ADMISSION_FIELDS
    exact(admission, ADMISSION_FIELDS, 'SMALLAPP_INITIAL_ADMISSION_FIELDS_INVALID')
    require(admission['operationRequestPin'] == admission['launchPin'], 'SMALLAPP_SERVICE_TECHNICAL_ADMISSION_REQUIRED')
    installation_selection = context.document(admission['launchPin'])
    exact(installation_selection, INSTALLATION_SELECTION_FIELDS, 'SMALLAPP_INSTALLATION_SELECTION_FIELDS_INVALID')
    installation_approval = context.document(installation_selection['approvalPin'])
    installation_selection_shape(installation_selection, installation_approval)
    require(installation_selection['installationPin'] == config['installationPin'] and
        installation_selection['authorityKeyPin'] == selected['authorityKeyPin'] and
        installation_selection['engineSelection'] == config['engineSelection'] and
        installation_selection['serviceBindingPin'] == admission['serviceBindingPin'] and
        context.document(admission['serviceBindingPin']) == config and
        installation_selection['producerIdentityPin'] == admission['producerIdentityPin'] and
        admission['collectionId'] == installation_selection['initializationId'] and
        admission['sequence'] == 1 and admission['phase'] == 'INSTALLATION_ADMISSION',
        'SMALLAPP_SERVICE_CURRENT_ADMISSION_BINDING_REQUIRED')
    from recovery_control_smallapp_native import stamp
    require(max(stamp(installation_selection['issuedAt']), stamp(installation_approval['issuedAt'])) <=
            stamp(admission['startedAt']), 'SMALLAPP_SERVICE_ADMISSION_PREDATES_PERMISSION')
    context.selection = {**selected, 'authorityKeyPin': selected['authorityKeyPin'],
        'installedFilePins': installation['filePins'], 'dependencyPins': installation['dependencyPins'],
        'pythonPin': installation['pythonPin'], 'hostBootId': proof['bootId'], 'engineSelection': config['engineSelection'],
        'sourceIdentityPin': installation_selection['sourceIdentityPin']}
    with installed_repository(installation):
        require(context.installation_admission(config['installationPin']) == installation,
                'SMALLAPP_SERVICE_ACTUAL_INSTALLATION_ADMISSION_REQUIRED')
        resource = native.signed(selected['sourceBindingPin'])
        exact(resource, RESOURCE_FIELDS.split(), 'RESOURCE_BINDING_FIELDS_INVALID')
        resource = native.resource(selected['sourceBindingPin'], 'SOURCE', resource['configRef'])
        require(resource['sourceIdentityPin'] == context.selection['sourceIdentityPin'] and
            resource['fresh'] is False and resource['targetId'] is None, 'SMALLAPP_SERVICE_CURRENT_SOURCE_REQUIRED')
        context.native_source_original(resource)
        context.native_source_original(native.signed(resource['ownerProofPin']))
        registry = Registry(native, config)
        registration = metadata(native.document(selected['registrationPin']))
        # This validates the current source, host and runtime configuration.
        # START_APPLICATION does not require a future target or FULL controls.
        registry.bind(registration, resource, selected['sourceBindingPin'], action='START_APPLICATION')
    def current_initialization_permission():
        require(context.document(selection_pin) == selected and context.document(selected['approvalPin']) == approval,
                'SMALLAPP_SERVICE_INITIALIZATION_INPUT_CHANGED')
        service_initialization_shape(selected, approval)
        require(time.monotonic() < context.deadline, 'SMALLAPP_SERVICE_INITIALIZATION_DEADLINE_EXCEEDED')

    current_initialization_permission()
    native.configuration()
    current_initialization_permission()
    from recovery_control_smallapp import local_read
    selector = registry.root / 'resources' / (resource['configRef'] + '.pin.json')
    registry.import_registration(selected['registrationPin'], selected['expectedRegistrationPin'])
    import fcntl
    import os
    # import_registration released this existing lock. Reacquire it for the
    # complete SOURCE read/expected-Pin/publication, using the same custody.
    fd = os.open(registry.root / 'applications' / 'import.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == info.st_gid == 0 and
                stat.S_IMODE(info.st_mode) == 0o600, 'REGISTRATION_IMPORT_LOCK_CUSTODY_INVALID')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if selector.exists():
            previous = local_read(selector)
            require(previous == selected['sourceBindingPin'] or selected['expectedSourceBindingPin'] == previous,
                    'SMALLAPP_SERVICE_SOURCE_REPLACEMENT_EXPECTED_PIN_REQUIRED')
        else:
            require(selected['expectedSourceBindingPin'] is None, 'SMALLAPP_SERVICE_EXPECTED_SOURCE_MISSING')
        current_initialization_permission()
        publish_registration(selector, selected['sourceBindingPin'], selected['expectedSourceBindingPin'])
    finally:
        os.close(fd)
    # Binding success is reported only by the real server; this call blocks.
    current_initialization_permission()
    serve(selected['serviceConfigurationPin'], selected['authorityKeyPin'])
    require(False, 'SMALLAPP_INITIALIZED_SERVICE_TERMINATED')


class OperationAuthorityContext:
    """Native parent for the unchanged per-operation 0400 A-role service."""
    def __init__(self, selection_pin):
        import os
        import sys
        import time
        from recovery_control_executor import pin_reference
        require(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0,
                'SMALLAPP_OPERATION_NATIVE_ROOT_REQUIRED')
        self.deadline = time.monotonic() + 300
        self.selection_pin = selection_pin
        self.selection = {}
        self.selection = self.document(selection_pin)
        exact(self.selection, OPERATION_AUTHORITY_FIELDS, 'SMALLAPP_OPERATION_AUTHORITY_FIELDS_INVALID')
        s = self.selection
        require(s['schemaVersion'] == 'SmallAppOperationAuthoritySelection/v1' and s['batchId'] == BATCH and
                type(s['deadlineMilliseconds']) is int and 0 < s['deadlineMilliseconds'] <= 300000 and
                type(s['signerUid']) is type(s['signerGid']) is int and s['signerUid'] > 0 and s['signerGid'] > 0,
                'SMALLAPP_OPERATION_FINITE_AUTHORITY_REQUIRED')
        window(s)
        for field in ('issuancePlanPin', 'installationAdmissionPin', 'authorityKeyPin', 'producerIdentityPin',
                      'custodianIdentityPin', 'issuerEntryPin', 'privateKeyPin'):
            pin_reference(s[field])
        operation_public_pins(s, [s[field] for field in ('issuancePlanPin', 'installationAdmissionPin',
            'authorityKeyPin', 'producerIdentityPin', 'custodianIdentityPin', 'issuerEntryPin')])
        self.deadline = time.monotonic() + s['deadlineMilliseconds'] / 1000
        self.public_graph()
        self.plan = signed_payload(s['issuancePlanPin'], s['authorityKeyPin'])
        operation_public_pins(s, [self.plan[field] for field in ('sourceBindingPin', 'installationPin',
            'resourceObservationPin')] + self.plan['originalPins'] +
            [self.plan[field] for field in ('targetBindingPin', 'pointBindingPin') if self.plan[field] is not None])
        self.plan_admission = object.__new__(SmallAppAuthoritySigningService)
        self.plan_admission.plan = self.plan
        self.plan_admission.validate_plan(s['authorityKeyPin'])
        self.installation = signed_payload(self.plan['installationPin'], s['authorityKeyPin'])
        operation_public_pins(s, [*self.installation['filePins'], *self.installation['dependencyPins'],
            self.installation['pythonPin'], self.installation['nativeRuntimeTrustPin'],
            self.installation['nativeRuntimeProofPin']])
        self.proof_pin = self.installation['nativeRuntimeProofPin']
        proof = signed_payload(self.proof_pin, s['authorityKeyPin']); window(proof)
        # These derived values come from authenticated installation/source originals.
        self.selection = {**s, 'installedFilePins': self.installation['filePins'],
            'dependencyPins': self.installation['dependencyPins'], 'pythonPin': self.installation['pythonPin'],
            'sourceIdentityPin': self.plan_admission.source['sourceIdentityPin'], 'hostBootId': proof['bootId']}
        self.original_selection = s
        self.producer = self.producer_identity = self.document(s['producerIdentityPin'])
        self.custodian = self.document(s['custodianIdentityPin'])
        self.provision = {'privateKeyPin': s['privateKeyPin'], 'signerSocketPath': s['socketPath']}
        self.native_tool_pins, self.commands = [], []
        self.guard()

    def raw(self, reference):
        if 'privateKeyPin' in self.selection:
            operation_public_pins(self.selection, [reference])
        else:
            # Before selection metadata is available, only a root-private
            # selection original is eligible; never open a non-root A key.
            info = Path(reference['path']).stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == info.st_gid == 0 and
                    stat.S_IMODE(info.st_mode) in (0o400, 0o600),
                    'SMALLAPP_OPERATION_SELECTION_CUSTODY_REQUIRED')
        return InitialCustodianContext.raw(self, reference)

    def document(self, reference):
        return decode(self.raw(reference))

    def public_pin(self, path):
        from recovery_control_executor import pin
        operation_public_paths(self.selection, [str(path)])
        return pin(path)

    def public_graph(self, *, extra_roots=()):
        """Admit every nested public dependency before invoking mature readers."""
        import time
        from recovery_control_executor import pinned_read
        from recovery_native_browser import graph_union
        # The selected private Pin is custody metadata, never a public graph root.
        selection = getattr(self, 'original_selection', self.selection)
        roots = [{key: value for key, value in selection.items() if key != 'privateKeyPin'}, *extra_roots]
        operation_public_record(self.selection, roots)
        companion_paths = set()
        def read(reference):
            require(time.monotonic() < self.deadline, 'SMALLAPP_OPERATION_PUBLIC_GRAPH_DEADLINE')
            operation_public_pins(self.selection, [reference])
            actual, first = pinned_read(reference['path'], detect_json=True)
            require(actual == reference, 'SMALLAPP_OPERATION_PUBLIC_GRAPH_PIN_CHANGED')
            if first not in (b'{', b'['):
                return b''  # The exact binary/empty bytes were streamed and verified.
            operation_public_pins(self.selection, [reference])
            actual, raw = pinned_read(reference['path'], retain=True)
            require(actual == reference, 'SMALLAPP_OPERATION_PUBLIC_GRAPH_PIN_CHANGED')
            value = decode(raw)
            if reference == self.selection_pin:
                # The exact protected selection contains private-key custody
                # metadata. Never expand that selected metadata as public data.
                require(value == selection, 'SMALLAPP_OPERATION_CURRENT_SELECTION_CHANGED')
                value = {key: item for key, item in value.items() if key != 'privateKeyPin'}
                from recovery_control_smallapp import canonical
                raw = canonical(value)
            operation_public_record(self.selection, value)
            if type(value) is dict and value.get('schemaVersion') == 'RecoveryInvocation/v1':
                # invocation_originals also hashes these directory-derived originals.
                for name in ('supervisor-terminal.json', 'process-original.json'):
                    path = Path(reference['path']).parent / name
                    if path not in companion_paths:
                        companion_paths.add(path); roots.append(self.public_pin(path))
            return raw
        return graph_union(roots, read, opaque_paths=set(), data_paths=set())

    def guard(self):
        import os
        import time
        from recovery_native_launcher import match_process, status
        from recovery_control_executor import pin, verify
        s = self.selection
        self.public_graph()
        require(time.monotonic() < self.deadline and self.document(self.selection_pin) == self.original_selection and
                signed_payload(s['issuancePlanPin'], s['authorityKeyPin']) == self.plan,
                'SMALLAPP_OPERATION_CURRENT_SELECTION_CHANGED')
        window(s); window(self.plan)
        self.plan_admission.validate_plan(s['authorityKeyPin'])
        require(self.producer['uid'] == self.producer['gid'] == 0 and
                self.custodian['pid'] != self.producer['pid'] and
                self.custodian['mountNamespace'] != self.producer['mountNamespace'] and
                self.producer['bootId'] == self.custodian['bootId'] == s['hostBootId'],
                'SMALLAPP_OPERATION_INDEPENDENT_PARENT_REQUIRED')
        match_process(self.custodian, os.getpid(), 0)
        match_process(self.producer, self.producer['pid'], 0)
        values = status(self.producer['pid'])
        require(all(int(values[name], 16) == 0 for name in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                int(values.get('CapAmb', '0'), 16) == 0 and values['NoNewPrivs'] == '1' and not values['Groups'].split(),
                'SMALLAPP_OPERATION_WORKER_CAPABILITIES_REFUSED')
        require(pin(Path(__file__).resolve()) == s['issuerEntryPin'] and s['issuerEntryPin'] in self.installation['filePins'],
                'SMALLAPP_OPERATION_ENTRY_NOT_INSTALLED')
        require(InitialCustodianContext.installation_admission(self, self.plan['installationPin']) == self.installation,
                'SMALLAPP_OPERATION_INSTALLATION_CHANGED')
        for reference in [*self.installation['filePins'], *self.installation['dependencyPins'], self.installation['pythonPin']]:
            verify(reference)
        for reference in self.plan['originalPins']:
            self.raw(reference)

    def admit(self, value):
        self.guard()
        fields = RECORDS.get(value.get('schemaVersion'))
        require(fields is not None, 'SMALLAPP_OPERATION_RECORD_UNSUPPORTED')
        exact(value, fields, 'SMALLAPP_OPERATION_RECORD_FIELDS_INVALID')
        require(sum(self.document(reference) == value for reference in self.plan['originalPins']) == 1,
                'SMALLAPP_OPERATION_ORIGINAL_NOT_SELECTED')

    def on_ready(self, signer_pid):
        from recovery_native_launcher import measure_process, status
        self.guard()
        actual = measure_process(signer_pid); values = status(signer_pid)
        require(actual['uid'] == self.selection['signerUid'] and actual['gid'] == self.selection['signerGid'] and
                actual['bootId'] == self.selection['hostBootId'] and
                int(values['CapEff'], 16) == int(values['CapPrm'], 16) == 3 and
                values['NoNewPrivs'] == '1', 'SMALLAPP_OPERATION_CURRENT_A_ROLE_REQUIRED')


def drain_operation_completion(channel, completed, termination_kind, exit_code, deadline):
    """A reaped child may still have its final frame queued on the parent socket."""
    from recovery_native_observation import receive_frame
    require(termination_kind == 'EXITED' and type(exit_code) is int and exit_code == 0,
            'SMALLAPP_OPERATION_SIGNER_CHILD_FAILED')
    if not completed:
        require(receive_frame(channel, deadline) == {'kind': 'COMPLETE'},
                'SMALLAPP_OPERATION_COMPLETION_FRAME_REQUIRED')
        completed = True
    require(completed is True, 'SMALLAPP_OPERATION_COMPLETION_FRAME_REQUIRED')
    return completed


def operation_authority_entry(selection_pin):
    """Pinned root selection wires actual guard/admit/on_ready; no callback API."""
    return _native_authority_entry(OperationAuthorityContext(selection_pin), installation=False)


def _native_authority_entry(context, *, installation):
    import os
    import select
    import signal
    import socket
    import time
    from recovery_native_launcher import (native_call, drop_capabilities, measure_process,
        measure_worker_key_denial)
    from recovery_native_observation import receive_frame, send_frame, wire_canonical
    from recovery_native_process import persist_bytes
    s = context.selection
    root = lab_path(s['signerRootPath'], directory=True)
    output = lab_path(s['outputRoot'], directory=True)
    require(output.stat().st_uid == output.stat().st_gid == 0 and stat.S_IMODE(output.stat().st_mode) == 0o700,
            'SMALLAPP_OPERATION_ROOT_OUTPUT_CUSTODY_REQUIRED')
    key = root / s['privateKeyPin']['path'].lstrip('/')
    info = key.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == s['signerUid'] and
            info.st_gid == s['signerGid'] and stat.S_IMODE(info.st_mode) == 0o400,
            'SMALLAPP_OPERATION_0400_A_PROVISION_REQUIRED')
    require(os.statvfs(key).f_flag & os.ST_RDONLY, 'SMALLAPP_OPERATION_PRIVATE_KEY_VIEW_NOT_READONLY')
    permission_pin = context.selection_pin if installation else s['issuancePlanPin']
    persist_bytes(output / ('operation-reservation-' + permission_pin['sha256'] + '.json'),
                  wire_canonical({'selectionPin': context.selection_pin, 'retryAllowed': False}))
    parent, channel = socket.socketpair(); child = os.fork()
    if child == 0:
        try:
            parent.close(); native_call('unshare', 0x20000)
            native_call('mount', None, b'/', None, (1 << 18) | 16384, None)
            os.chroot(root); os.chdir('/')
            drop_capabilities(s['signerUid'], s['signerGid'], 3)
            descriptor = channel.fileno()
            os.closerange(3, descriptor); os.closerange(descriptor + 1, os.sysconf('SC_OPEN_MAX'))
            def guard():
                send_frame(channel, {'kind': 'GUARD'}, context.deadline)
                return receive_frame(channel, context.deadline)
            def admit(value):
                send_frame(channel, {'kind': 'ADMIT', 'payload': value}, context.deadline)
                require(receive_frame(channel, context.deadline) == {'admitted': True}, 'SMALLAPP_OPERATION_PARENT_ADMISSION_REQUIRED')
            def on_ready():
                message = {'kind': 'READY'}
                if installation:
                    message['authorityIdentityPin'] = service.publish_current_identity(context.proof_pin, context.expires_at)
                send_frame(channel, message, context.deadline)
                require(receive_frame(channel, context.deadline) == {'ready': True}, 'SMALLAPP_OPERATION_PARENT_READY_REQUIRED')
            service_type = AuthoritySigningService if installation else SmallAppAuthoritySigningService
            kwargs = {} if installation else {'issuance_plan_pin': s['issuancePlanPin']}
            service = service_type(**kwargs, socket_path=s['socketPath'],
                private_key_pin=s['privateKeyPin'], authority_key_pin=s['authorityKeyPin'], original_root=s['originalRoot'],
                producer_pid=context.producer['pid'], producer_start_ticks=context.producer['startTicks'], producer_uid=0,
                guard=guard, admit=admit, deadline=context.deadline, launch_pin=permission_pin)
            service.serve(64 if installation else 2 * len(context.plan['originalPins']) + 1, on_ready=on_ready)
            send_frame(channel, {'kind': 'COMPLETE'}, context.deadline); os._exit(0)
        except BaseException as error:
            import sys
            print('SMALLAPP_OPERATION_SIGNER_FAILED:' + getattr(error, 'code', type(error).__name__), file=sys.stderr, flush=True)
            os._exit(1)
    channel.close(); terminal = None; completed = False
    try:
        while terminal is None:
            context.guard()
            if completed:
                select.select([], [], [], .01)
            elif select.select([parent], [], [], min(.05, max(0, context.deadline-time.monotonic())))[0]:
                message = receive_frame(parent, context.deadline)
                if message == {'kind': 'GUARD'}:
                    context.on_ready(child)
                    measured = measure_worker_key_denial(context, child, until=min(context.deadline, time.monotonic() + 5))
                    reference = persist_bytes(output / ('key-denial-' + str(time.monotonic_ns()) + '.json'), wire_canonical(measured))
                    send_frame(parent, {'nativeRuntimeProofPin': context.proof_pin, 'workerKeyDenial': measured,
                        'measurementPin': reference, 'signer': measure_process(child)}, context.deadline)
                elif message == {'kind': 'READY'} or installation and set(message) == {'kind', 'authorityIdentityPin'} and message['kind'] == 'READY':
                    context.on_ready(child)
                    ready = {'authoritySocketReady': True, 'businessDispatched': False}
                    if installation:
                        operation_public_pins(s, [message['authorityIdentityPin']])
                        peer = signed_payload(message['authorityIdentityPin'], s['authorityKeyPin'])
                        actual = measure_process(child)
                        require(all(peer[k] == actual[k] for k in
                            ('pid', 'startTicks', 'uid', 'gid', 'hostId', 'bootId', 'mountNamespace', 'rootDevice', 'rootInode')),
                            'SMALLAPP_INSTALLATION_AUTHORITY_READY_MISMATCH')
                        ready['authorityIdentityPin'] = message['authorityIdentityPin']
                    print(wire_canonical(ready).decode(), flush=True)
                    send_frame(parent, {'ready': True}, context.deadline)
                elif message == {'kind': 'COMPLETE'}:
                    completed = True
                else:
                    exact(message, {'kind', 'payload'}, 'SMALLAPP_OPERATION_PARENT_FRAME_INVALID')
                    require(message['kind'] == 'ADMIT', 'SMALLAPP_OPERATION_PARENT_ACTION_INVALID')
                    context.admit(message['payload']); send_frame(parent, {'admitted': True}, context.deadline)
            pid, wait = os.waitpid(child, os.WNOHANG)
            if pid:
                terminal = wait
                exited = os.WIFEXITED(terminal)
                completed = drain_operation_completion(parent, completed, 'EXITED' if exited else 'UNKNOWN',
                    os.WEXITSTATUS(terminal) if exited else None, context.deadline)
        require(completed and os.WIFEXITED(terminal) and os.WEXITSTATUS(terminal) == 0,
                'SMALLAPP_OPERATION_SIGNER_CHILD_FAILED')
        if installation:
            result = context.completed()
            persist_bytes(output / ('installation-completion-' + context.selection_pin['sha256'] + '.json'), wire_canonical(dict(
                schemaVersion='SmallAppInstallationAuthorityCompletion/v1', selectionPin=context.selection_pin,
                installationAdmissionPin=result['installationAdmissionPin'], signerPid=child,
                terminationKind='EXITED', actualExitCode=0, waitStatus=terminal, descendantState='REAPED')))
            return result
        for original in context.plan['originalPins']:
            signed_path = Path(s['socketPath']).parent / (original['sha256'] + '.smallapp.signed.json')
            signed_pin = context.public_pin(signed_path)
            operation_public_pins(s, [signed_pin, s['authorityKeyPin']])
            require(signed_payload(signed_pin, s['authorityKeyPin']) == context.document(original),
                    'SMALLAPP_OPERATION_FINITE_RECORDS_INCOMPLETE')
        return dict(authorityCompleted=True, serviceStarted=False, sourceOpened=False, businessDispatched=False)
    finally:
        parent.close()
        if terminal is None:
            os.kill(child, signal.SIGKILL); os.waitpid(child, 0)
