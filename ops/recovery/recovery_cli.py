"""Configured W04 file entry: preflight, ordered restore, rehearsal and cutover."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from contextlib import ExitStack

from recovery_engine import (Budget, InvocationRunner, RecoveryError, absolute, authorities,
    check_pin, digest, load, pin, pinned_json, require, utc, validate_record, write,
    persist_evidence, repository_guard)
from recovery_engine_state import FileLock, Journal, target_lock_path
from recovery_engine_read_guard import RepositoryReadGuard, repository_root
from recovery_plan import (immutable_inputs, preflight, prepared_target, resolve_chain, trusted_configuration)
from recovery_plan_application import protected_application


KEYS = {'RESTORE_PREFLIGHT': {'repositoryPoint'}, 'REHEARSAL': {'repositoryPoint'},
        'RESTORE_EXECUTE': {'restorePlan', 'recoveryTarget'},
        'CONTROLLED_CUTOVER': {'repositoryPoint', 'recoveryVerificationReport'}}


class PublicOutput:
    """One admission rule for every public success/error publication."""
    # Explicit input-field contract: byte originals are protected leaves;
    # only named document references may expand the exclusion scope. Unknown
    # Pin fields fail closed instead of guessing their type from their bytes.
    # W03 types follow repository_installer/records/native_peer/wsl_carrier:
    # keys, executable/dependency closures and retained archive bytes are leaves;
    # source/peer/service/host/carrier configurations and recipe templates expand.
    BYTE_INPUTS = {'pythonPin', 'scriptPin', 'executorPin', 'toolPins', 'toolPin', 'mysqlbinlogPin',
        'moduleSourcePins', 'formalModulePins', 'supportedVersionPins', 'versionPins', 'imagePins',
        'repositoryEvidenceKeyPins', 'authorityKeyPins', 'originalProcessPin', 'originalResultPins',
        'payloadRefs', 'payloadPins', 'payloadPin', 'filePayloadPins', 'contentPins', 'sqlPin', 'rawSqlPin', 'rawPin',
        'inventoryPin', 'expectedInventoryPin', 'recordSchemasPin', 'approvedReadOnlyQueryPins',
        'environmentCliPin', 'dataWorkerPin', 'dataCliPin', 'sourceEvidencePins', 'filePin',
        'iptablesPin', 'dockerPin', 'probePin', 'toolAndVersionPins', 'supportedToolPins',
        'nativeAuthorityKeyPins', 'evidenceSigningKeyPin', 'evidenceKeyPins', 'signingKeyPin',
        'executablePin', 'programPin', 'programPins', 'netExePin', 'nftPin', 'powershellPin',
        'ownerPythonPin', 'ownerEntryPin', 'ownerDependencyPins', 'nativeImplementationPins',
        'nativeDependencyPins', 'implementationPins', 'captureBinderDependencyPins', 'libraryPins',
        'publisherPin', 'installerPin', 'dispatcherPin', 'launcherPin', 'resourceObserverPin',
        'baseSchemaPin', 'controlAddendumPin', 'schemaPin', 'nasCredentialPin', 'credentialPin',
        'archiveFilePins', 'archivedFilePins', 'readbackOriginalPins', 'contentPin', 'sourceSqlPin',
        'queryPin', 'remoteTerminalKeyPins', 'enforceScriptPin', 'observeScriptPin',
        'nativeAssemblyProgramPin', 'archive_program', 'mysql_credential', 'configurationPins',
        'objectInventoryPin', 'sourcePin', 'custodyPaths', 'authorityKeyPin',
        'repositoryAuthorityKeyPins', 'copyProtectionEvidenceKeyPins', 'archivePin', 'originalEvidencePins',
        'sourceAccountPin', 'writerAccountPin', 'readerAccountPin', 'accountPin', 'probeOriginalPin',
        'readbackOriginalPin', 'sourceToolkitPin', 'readOnlyMountEvidencePin',
        'managerIdentityEvidencePin', 'nativeLinkageEvidencePin'}
    DOCUMENT_INPUTS = {
        'selectedPointPin', 'parentPointPins', 'repositoryPointPins', 'repositoryPointPin', 'repositoryPoint',
        'manifestPin', 'payloadTreePin', 'copyProtectionPin', 'ownerCloseEvidencePin', 'readbackEvidencePin',
        'originalExitEvidencePin', 'sourceScopePin', 'sourceIdentityPin', 'targetIdentityPin', 'targetRef',
        'sourceOrTargetRef', 'authorizationRefs', 'leaseRef', 'policyPin', 'dataPolicyPin', 'dataTargetPin',
        'environmentPolicyPin', 'configurationPin', 'secretRefs', 'repositoryBindingPinsByManifestSha256',
        'recoveryMaterialPin', 'materialPin', 'allMaterialPins', 'capturePointPin', 'capturePoint',
        'referenceInventoryPin', 'derivedInventoryPin', 'fileInventoryPin', 'exportReceiptPin',
        'expectedDataPin', 'deltaPin', 'objectContentIndexPin', 'sourceObjectContentIndexPin',
        'chainObjectContentIndexPins', 'parentExportIndexPin', 'objectExportReceiptPin',
        'inventoryPins', 'planPin', 'restorePlan', 'recoveryTarget', 'recoveryTargetPin', 'candidatePin',
        'orderedChainPins', 'backupAndChainPins', 'baselinePointPin', 'rebuildFromPin', 'protectionPointPin',
        'reportPin', 'recoveryVerificationReport', 'verificationReportPin', 'controlledRestoreReportPin',
        'approvalPin', 'postVerificationApprovalPin', 'physicalStartupApprovalPin', 'recoveryApprovalPins',
        'dataEvidencePins', 'playwrightEvidencePins', 'targetApprovalRefs', 'restoreResultPin',
        'restoreExecutionResultPin', 'applicationStartPin', 'applicationStartResultPin',
        'applicationWriteProtectionPin', 'applicationWriteProtectionPolicyPin', 'sideEffectPolicyPin',
        'sideEffectIsolationPin', 'sourceFencePin', 'sourceFencePointEvidencePin', 'newGenerationPointPin',
        'cutoverRecipePins', 'recipePin', 'executionContextPins', 'executionHostIdentityPin',
        'originalRequestPin', 'requestPin', 'operationRequestPin', 'resultPin', 'cacheEvidencePins',
        'databaseResultPin', 'objectResultPin', 'previousDatabaseResultPin', 'previousObjectResultPin',
        'dbStepEvidencePins', 'objectStepEvidencePins', 'physicalStepEvidencePins', 'stepResultPins',
        'consistencyEvidencePin', 'derivedEvidencePin', 'originalConsistencyResultPin', 'classificationPin',
        'commandConfigPin', 'commandIntentPin', 'intentPin', 'exitEvidencePin', 'enforcementPin',
        'comparisonPin', 'permissionEvidencePin', 'healthEvidencePin', 'resourcesProofPin',
        'isolationProofPin', 'modePreconditionsPin', 'expectedProtectionPin', 'bucketProtectionPin',
        'actualTargetIdentityPin', 'activeTargetIdentityPin', 'sourceTargetIdentityPin', 'switchedTargetPin',
        'writeProtectionBeforePin', 'writeProtectionAfterPin', 'versionMappingPin', 'segmentEvidencePins',
        'initializationInventoryPin', 'startupInventoryPins', 'restoreReceiptPin', 'expandedPin',
        'localExitPin', 'remoteTerminalProofPin', 'remoteTerminalProofPins', 'independentCallerBindingPin',
        'environmentFenceHandoffCapabilityPin', 'observationPins', 'rejectionObservationPins', 'observedPin',
        'originalInvocationPin', 'originalInvocationPins', 'originalStartResultPins', 'originalStepPins',
        'originalPins', 'evidencePins', 'verificationPins',
        # Actual W03 signed publication -> native response -> source/peer/host/carrier graph.
        'nativeCaptureResponsePin', 'nativeResponsePin', 'transportedResponsePin', 'sourceConfigPin',
        'nativePeerConfigPin', 'nativePeerConfigurationPin', 'nativeServiceConfigurationPin',
        'hostViewPin', 'windowsHostViewPin', 'nativeHostViewPin', 'wslCarrierConfigPin', 'carrierConfigPin',
        'executionHostPin', 'sourceProfilePin', 'workspacePin', 'prepareRequestPin', 'captureRequestPin',
        'recipeTemplatePin', 'assemblyTemplatePin', 'nativeAssemblyConfigPin', 'catalogBindingPin',
        'archiveHeaderPin', 'manifestReference', 'recoveryReceiptReference',
        'capturePointReference', 'originalRecoveryReference',
        'nativeEvidencePins', 'originalRecordsPin', 'terminalPin', 'carrierPin',
        'channelPin', 'publicationPin', 'sourceRootProofPins', 'identityPin', 'observationPin',
        'ownerIdentityPin', 'resourcePin', 'legalHoldPointPins',
        # W02 templates consumed by the selected W03 native peer, not programs.
        'executionContractPin', 'creationResultsPin', 'sourceReferencesPin', 'bootSourcesPin',
        'bootConnectionsPin', 'controlledSourcesPin', 'resumeRequestPin', 'recoveryFlowsPin',
        'seriesPin', 'catalogPin', 'parentPointPin', 'parentRepositoryPointPin', 'approvedSourceTargetPin',
        'materialIndexPin', 'configurationReference', 'protectionReference', 'reference',
        'authorIdentityReference', 'resourceObservationReference', 'allocationProofReference',
        'observationReference', 'expectedReference', 'intentReference', 'payloadReference',
        'policy', 'source_context', 'installed_context', 'release_binding', 'coverage', 'allocation',
        'source_guard', 'staging_admission', 'labProfilePin', 'labContextPin', 'labScopePin',
        'installedClosurePin', 'installationManifestPin', 'authorizationPin', 'leasePin',
        'copyProtectionPinsByManifestSha256', 'aclEvidencePin', 'readbackEndpointEvidencePin',
        'copyProtectionEvidencePins', 'localRootIdentityPin', 'captureSourceScopePin',
        'captureContextPin', 'selectedLabContextPin', 'deletionAttemptPin', 'keyAccessEvidencePin',
        'nativeRuntimeTrustPin', 'nativeRuntimeProofPin'}
    # Signed installation records distinguish installed bytes from configuration documents.
    # Capture materials intentionally contain arbitrary byte files. Other
    # "files" fields (material-index entries) retain ordinary nested typing.
    BYTE_CONTAINERS_BY_SCHEMA = {'backup-capture-materials/v1': {'files'},
                                'RepositoryNativeInstallation/v1': {'filePins', 'dependencyPins'},
                                'RepositoryNativeInstallation/v2': {'filePins', 'dependencyPins'},
                                'RepositoryLabNativeRuntimeTrust/v1': {'vendorArtifactPins', 'nativeFilePins'}}
    MAX_DOCUMENTS = 4096
    MAX_JSON_BYTES = 64*1024*1024
    MAX_NODES = 100000

    def __init__(self, path):
        self.path = path
        self.context = None
        self.protected = set()
        self.roots = set()
        self.documents = {}
        self.nodes = self.json_bytes = 0
        self.complete = False

    def bind(self, request, request_pin, trust, policy, config, budget):
        self.context = request, policy
        self.budget = budget
        # The deny scope persists on this publisher through every error unwind.
        # It confers no trust/permission: existing signatures and admission gates
        # still decide whether these referenced inputs may be used for recovery.
        self.protected.add(absolute(request_pin['path']))
        trust_path = os.environ.get('RECOVERY_DATA_TRUST_FILE')
        if trust_path is not None: self.protected.add(absolute(trust_path))
        self.roots.add(repository_root(request['selectedPointPin'], policy))
        for value in (request, trust, policy, config): self.collect(value)
        self.complete = True
        self.check()

    def collect(self, value, field=None, depth=0):
        self.budget.remaining()
        self.nodes += 1
        require(self.nodes <= self.MAX_NODES and depth <= 128, 'PUBLIC_OUTPUT_SCOPE_LIMIT')
        if isinstance(value, dict):
            if set(value) == {'path', 'bytes', 'sha256'} and type(value['path']) is str:
                path = absolute(value['path'])
                # Protect first: reading the referenced document can fail.
                self.protected.add(path)
                if field in self.BYTE_INPUTS: return
                require(field in self.DOCUMENT_INPUTS, 'PUBLIC_OUTPUT_SCOPE_REFERENCE_TYPE_UNKNOWN')
                previous = self.documents.get(path)
                if previous is not None:
                    require(previous == value, 'PUBLIC_OUTPUT_SCOPE_PIN_CONFLICT')
                    return
                require(len(self.documents) < self.MAX_DOCUMENTS and type(value['bytes']) is int and
                        value['bytes'] >= 0, 'PUBLIC_OUTPUT_SCOPE_LIMIT')
                self.json_bytes += value['bytes']
                require(self.json_bytes <= self.MAX_JSON_BYTES, 'PUBLIC_OUTPUT_SCOPE_LIMIT')
                self.documents[path] = value
                document = pinned_json(value, budget=self.budget)
                self.collect(document, depth=depth+1)
            else:
                for key, item in value.items():
                    if key in ('journalRoot', 'privateRoot', 'repositoryRoot', 'versionedDataLocation', 'existingDataLocation', 'backingRootPath') and item is not None:
                        self.roots.add(absolute(item))
                    elif key == 'materialPaths':
                        self.roots.update(absolute(item_path) for item_path in item)
                    child_field = field if field in self.BYTE_INPUTS or field in self.DOCUMENT_INPUTS else key
                    if key in self.BYTE_CONTAINERS_BY_SCHEMA.get(value.get('schemaVersion'), set()):
                        child_field = 'payloadPins'
                    self.collect(item, child_field, depth+1)
        elif isinstance(value, (list, tuple)):
            for item in value: self.collect(item, field, depth+1)

    def check(self, extra=()):
        require(self.context is not None, 'PUBLIC_OUTPUT_NOT_ADMITTED')
        require(self.complete, 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE')
        self.budget.remaining()
        self.complete = False
        self.collect(extra)
        self.complete = True
        request, policy = self.context
        path = absolute(str(self.path)); parent = absolute(str(path.parent))
        require(parent.is_dir() and (os.name != 'posix' or parent.stat().st_mode & 0o077 == 0),
                'PRIVATE_PUBLIC_OUTPUT_DIRECTORY_REQUIRED')
        evidence = absolute(policy['evidenceRoot'])
        # Reserve the entire internal directory tree and root control namespace.
        # A public file directly under evidenceRoot may have a nonreserved name.
        destinations = (path, path.with_name(path.name + '.recording-failure.json'))
        for destination in destinations:
            require(destination not in self.protected and not any(destination.is_relative_to(root) for root in self.roots),
                    'PUBLIC_OUTPUT_PROTECTED_PATH')
            if destination.is_relative_to(evidence):
                parts = destination.relative_to(evidence).parts
                require(len(parts) == 1 and not parts[0].startswith(('request-', 'target-', 'operation-', '.')),
                        'PUBLIC_OUTPUT_RESERVED_EVIDENCE_PATH')
        if path.exists():
            existing = load(path, budget=self.budget)
            require(type(existing) is dict and existing.get('schemaVersion') == 'backup-restore-operation-result/v1' and
                    all(type(existing.get(key)) is str and existing[key] for key in ('operationId', 'requestId', 'action')),
                    'PUBLIC_OUTPUT_OWNERSHIP_REQUIRED')
            previous = load(evidence/('request-' + digest(existing['requestId']) + '.json'), budget=self.budget)
            require(previous['operationId'] == existing['operationId'] and previous['requestId'] == existing['requestId'],
                    'PUBLIC_OUTPUT_OWNERSHIP_REQUIRED')
            declared = any(absolute(ref['path']) == path for ref in previous.get('cacheEvidencePins', []))
            # Safe new cache views may not be in the original journal. Permit
            # their exact pinned result bytes; a matching identity alone is not
            # evidence of ownership of an arbitrary existing destination.
            require(declared or previous['resultPin'] is not None and pinned_json(previous['resultPin'], budget=self.budget) == existing,
                    'PUBLIC_OUTPUT_OWNERSHIP_REQUIRED')
            # Check single-link ownership without treating its current content
            # as trusted success. Journal cache validation is independent.
            pin(path, budget=self.budget)
        fault_path = destinations[1]
        if fault_path.exists():
            fault = load(fault_path, budget=self.budget)
            require(type(fault) is dict and fault.get('schemaVersion') == 'RecoveryEvidenceRecordingFailure/v1' and
                    all(fault.get('failedEvidence', {}).get(key) == request[key] for key in ('operationId', 'requestId', 'action')),
                    'PUBLIC_OUTPUT_FAULT_RECEIPT_OWNERSHIP_REQUIRED')
            pin(fault_path, budget=self.budget)
        self.budget.remaining()
        return path

    def publish(self, result, *, exit_code=None):
        path = self.check(result)
        return persist_evidence(path, result, unknown=result['state'] == 'TERMINAL_UNKNOWN', exit_code=exit_code)


class RecoveryOperation:
    def __init__(self, request, request_pin, trust, policy, config, runner, journal, lock):
        self.request, self.request_pin, self.trust, self.policy, self.config = request, request_pin, trust, policy, config
        self.runner, self.journal, self.lock = runner, journal, lock
        self.identity_pin = pinned_json(policy['dataTargetPin'])['targetIdentityPin']
        self.execution_context = None
        self.restore_original_start = 0

    def guard(self):
        active = repository_guard()
        if active is not None: active.check()
        self.runner.budget.remaining(); check_pin(self.request_pin)
        current = trusted_configuration(self.request)
        require(current == (self.trust, self.policy, self.config), 'OPERATION_INPUT_DRIFT')
        authorities(self.request, self.identity_pin, ['RESTORE_EXECUTE'], self.trust)
        for ref in self.request['inputPins'].values(): check_pin(ref, content=False)
        for ref in self.policy['toolPins']: check_pin(ref, content=False)

    def environment(self, action, inputs):
        child = dict(self.request, action=action, requestId=self.request['requestId']+'-'+action,
                     inputPins=inputs, deadlineMilliseconds=self.runner.budget.milliseconds())
        result, ref = self.runner.run(self.policy['pythonPin'], self.policy['environmentCliPin'], child,
                                      guard=self.guard, lock_fd=self.lock.fd, execution_context=self.execution_context)
        validate_record(result, 'OperationResult', self.policy['recordSchemasPin'])
        self.journal.phase(action, [ref])
        return result, ref

    def worker(self, action, plan_pin, target_pin, material_pin, **inputs):
        child = dict(schemaVersion='RecoveryDataRequest/v1', operationId=self.request['operationId'],
            requestId=self.request['requestId']+'-'+action+'-'+str(self.runner.sequence), action=action,
            originalRequestPin=self.request_pin, planPin=plan_pin, recoveryTargetPin=target_pin,
            materialPin=material_pin, deadlineMilliseconds=self.runner.budget.milliseconds(), **inputs)
        result, ref = self.runner.run(self.policy['pythonPin'], self.policy['dataWorkerPin'], child,
                                      guard=self.guard, lock_fd=self.lock.fd, execution_context=self.execution_context)
        require(result['schemaVersion'] == 'RecoveryDataStepResult/v1' and
                result['data']['recoveryPoint'] == pinned_json(material_pin)['recoveryPoint'], 'DATA_RESULT_POINT_MISMATCH')
        self.journal.phase(action, [ref])
        return result['data'], ref

    def restore(self, plan_pin, target_pin):
        plan = validate_record(pinned_json(plan_pin), 'RestorePlan', self.policy['recordSchemasPin'])
        chain = resolve_chain(self.request['selectedPointPin'], self.policy)
        require(plan['operationId'] == self.request['operationId'] and plan['mode'] == self.request['mode'] and
                plan['candidatePin'] == self.request['selectedPointPin'] and
                plan['targetRef'] == self.request['sourceOrTargetRef'] and
                plan['orderedChainPins'] == [step[0] for step in chain] and
                plan['immutableInputsSha256'] == digest(immutable_inputs(self.request, self.policy, chain)),
                'RESTORE_PLAN_IMMUTABLE_INPUT_MISMATCH')
        target_request = dict(self.request, inputPins={'recoveryTarget': target_pin})
        target = prepared_target(target_request, plan, self.policy, self.trust)
        require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        db_refs = []; object_refs = []; db_result = object_result = None
        for index, (_, point, material, material_pin) in enumerate(chain):
            db, ref = self.worker('DATABASE_FULL' if index == 0 else 'DATABASE_INCREMENTAL', plan_pin, target_pin, material_pin,
                                 **({} if index == 0 else {'previousDatabaseResultPin': db_result}))
            db_refs.append(ref); db_result = write(self.runner.root/('database-result-%03d.json' % index), db)
        physical = [step[2]['objects']['method'] == 'PHYSICAL_FILES' for step in chain]
        require(all(physical) or not any(physical), 'MIXED_PHYSICAL_AND_LOGICAL_OBJECT_CHAIN_UNSUPPORTED')
        if all(physical):
            data, ref = self.worker('OBJECT_CHAIN_PHYSICAL', plan_pin, target_pin, chain[-1][3],
                                    allMaterialPins=[step[3] for step in chain])
            object_refs.append(ref); object_result = write(self.runner.root/'objects-final.json', data)
        else:
            for index, (_, point, material, material_pin) in enumerate(chain):
                data, ref = self.worker('OBJECT_FULL' if index == 0 else 'OBJECT_INCREMENTAL', plan_pin, target_pin, material_pin,
                    previousObjectResultPin=object_result, parentRecoveryPoint=None if index == 0 else chain[index-1][2]['recoveryPoint'])
                object_refs.append(ref); object_result = write(self.runner.root/('objects-result-%03d.json' % index), data)
        derived, derived_ref = self.worker('DERIVED_DATA', plan_pin, target_pin, chain[-1][3],
                    databaseResultPin=db_result, objectResultPin=object_result)
        consistent, consistent_ref = self.worker('CONSISTENCY', plan_pin, target_pin, chain[-1][3],
                    databaseResultPin=db_result, objectResultPin=object_result)
        consistency_pin = write(self.runner.root/'consistency.json', dict(**consistent, derivedEvidencePin=derived_ref,
                                                                         originalConsistencyResultPin=consistent_ref))
        result = dict(schemaVersion='RestoreExecutionResult/v1', operationId=self.request['operationId'],
            restoreId=plan['restoreId'], planPin=plan_pin, targetIdentityPin=target['targetIdentityPin'],
            recoveryPoint=plan['recoveryPoint'], dbStepEvidencePins=db_refs, objectStepEvidencePins=object_refs,
            consistencyEvidencePin=consistency_pin, originalInvocationPins=list(self.runner.original_pins[self.restore_original_start:]),
            state='SUCCEEDED', writeProtectionState='ENFORCED')
        validate_record(result, 'RestoreExecutionResult', self.policy['recordSchemasPin'])
        result_pin = write(self.runner.root/'restore-execution-result.json', result)
        self.journal.phase('DATA_RESTORED', [result_pin])
        return result, result_pin

    def run(self):
        request = self.request; self.guard()
        if request['action'] in ('RESTORE_PREFLIGHT', 'REHEARSAL'):
            plan, _, _ = preflight(request, self.trust, self.policy, self.config)
            plan_pin = write(self.runner.root/'restore-plan.json', plan)
            self.journal.phase('PREFLIGHT_COMPLETE', [plan_pin])
            if request['action'] == 'RESTORE_PREFLIGHT': return plan
            require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
            target_result, _ = self.environment('PREPARE_TARGET', {'restorePlan': plan_pin})
            target = validate_record(target_result['data'], 'RecoveryTarget', self.policy['recordSchemasPin'])
            target_pin = write(self.runner.root/'recovery-target.json', target)
            execution, execution_pin = self.restore(plan_pin, target_pin)
            started, started_ref = self.environment('START_APPLICATION',
                          {'restoreExecutionResult': execution_pin, 'recoveryTarget': target_pin})
            application = validate_record(started['data'], 'ApplicationStartResult', self.policy['recordSchemasPin'])
            protected_application(application, execution_pin, plan, target, request, self.policy)
            application_pin = write(self.runner.root/'application-start-result.json', application)
            # W06 produces PASSED independently; rehearsal cannot sign its own acceptance.
            return dict(schemaVersion='RecoveryRehearsalResult/v1', planPin=plan_pin,
                recoveryTargetPin=target_pin, restoreExecutionResultPin=execution_pin,
                applicationStartResultPin=application_pin, verificationRequired=True, recoveryAccepted=False)
        if request['action'] == 'RESTORE_EXECUTE':
            return self.restore(request['inputPins']['restorePlan'], request['inputPins']['recoveryTarget'])[0]
        from recovery_cutover_orchestration import controlled_restore
        return controlled_restore(self)


def execute(request, request_pin, output_path=None):
    started = utc(); runner = journal = None; root = None
    budget = Budget(request['deadlineMilliseconds'])
    trust, policy, config = trusted_configuration(request)
    require(request['action'] in KEYS and set(request['inputPins']) == KEYS[request['action']], 'ACTION_INPUT_KEYS_INVALID')
    evidence = absolute(policy['evidenceRoot'])
    require(evidence.is_dir() and (os.name != 'posix' or evidence.stat().st_mode & 0o077 == 0), 'PRIVATE_EVIDENCE_ROOT_REQUIRED')
    public = output_path if isinstance(output_path, PublicOutput) else PublicOutput(output_path) if output_path is not None else None
    if public is not None: public.bind(request, request_pin, trust, policy, config, budget)
    identity = pinned_json(policy['dataTargetPin'])['targetIdentityPin']
    # Lock precedes journal admission and every mutation. No TTL-based takeover.
    with FileLock(target_lock_path(policy, identity)) as lock, ExitStack() as guard_scope:
        journal = Journal(evidence, request)
        if journal.path.exists():
            cached = journal.begin(budget=budget)
            if cached is not None:
                if request['action'] != 'RESTORE_PREFLIGHT':
                    control = repository_root(request['selectedPointPin'], policy)/'.repository-control'
                    for name in ('recovery-read-guard.json', 'write-unknown.json'):
                        try: (control/name).lstat()
                        except FileNotFoundError: continue
                        raise RecoveryError('REPOSITORY_RECOVERY_RECONCILIATION_REQUIRED', unknown=True)
                if public is not None:
                    public.publish(cached, exit_code=cached['actualExitCode'])
                return cached
        target_state_path = evidence/('target-' + digest(identity) + '.state.json')
        if target_state_path.exists() and request['action'] != 'RESTORE_PREFLIGHT':
            old = load(target_state_path)
            if old['state'] != 'SUCCEEDED':
                raise RecoveryError('TARGET_PREVIOUS_EXECUTION_RECONCILIATION_REQUIRED', unknown=True)
            require(False, 'TARGET_ALREADY_RESTORED_NEW_VERSIONED_TARGET_REQUIRED')
        journal.begin(budget=budget)
        root = evidence/('operation-' + digest({'operation': request['operationId'], 'request': request['requestId']}))
        root.mkdir(mode=0o700)
        runner = InvocationRunner(root, budget)
        operation = RecoveryOperation(request, request_pin, trust, policy, config, runner, journal, lock)
        read_guard = None
        if request['action'] != 'RESTORE_PREFLIGHT':
            check_pin(request_pin)
            actions = ['RESTORE_EXECUTE'] + (['CONTROLLED_CUTOVER'] if request['action'] == 'CONTROLLED_CUTOVER' else [])
            authorities(request, identity, actions, trust)
            read_guard = guard_scope.enter_context(RepositoryReadGuard(request, request_pin, policy, budget))
            write(target_state_path, dict(schemaVersion='RecoveryTargetExecutionState/v1',
                operationId=request['operationId'], requestId=request['requestId'], targetIdentityPin=identity,
                state='RUNNING', resultPin=None, updatedAt=utc()))
        try:
            data = operation.run(); state = 'SUCCEEDED'; failure = None
        except Exception as error:
            state = 'TERMINAL_UNKNOWN' if getattr(error, 'unknown', False) else 'FAILED_RETAINED'
            failure = getattr(error, 'code', 'RECOVERY_'+type(error).__name__.upper()); data = None
            persist_evidence(root/'failure-protection.json', dict(schemaVersion='RecoveryFailureProtection/v1',
                operationId=request['operationId'], targetIdentityPin=identity, partialTargetRetained=True,
                automaticReplayPermitted=False, automaticRollbackPerformed=False, writeProtectionState='UNKNOWN',
                failureCode=failure, originalResultPins=runner.original_pins), runner.original_pins,
                unknown=state == 'TERMINAL_UNKNOWN', exit_code=runner.actual_exit_code)
        result = dict(schemaVersion='backup-restore-operation-result/v1', operationId=request['operationId'],
            requestId=request['requestId'], action=request['action'], state=state, failureCode=failure,
            message='Recovery operation completed; independent acceptance remains required.' if state == 'SUCCEEDED'
                else 'Recovery stopped; retained evidence and target require reconciliation.', data=data,
            originalResultPins=runner.original_pins, startedAt=started, finishedAt=utc(), actualExitCode=runner.actual_exit_code)
        try:
            validate_record(result, 'OperationResult', policy['recordSchemasPin'])
            result_pin = persist_evidence(root/'operation-result.json', result, unknown=state == 'TERMINAL_UNKNOWN',
                                          exit_code=runner.actual_exit_code)
            if request['action'] != 'RESTORE_PREFLIGHT':
                persist_evidence(target_state_path, dict(schemaVersion='RecoveryTargetExecutionState/v1',
                    operationId=request['operationId'], requestId=request['requestId'], targetIdentityPin=identity,
                    state=state, resultPin=result_pin, updatedAt=utc()), unknown=state == 'TERMINAL_UNKNOWN',
                    exit_code=runner.actual_exit_code)
            if public is not None:
                public_pin = public.publish(result, exit_code=runner.actual_exit_code)
            # Bind the successful cache to its original published views. An
            # UNKNOWN public correction must invalidate it even if correction
            # of the journal and operation result is unavailable.
            journal.value['cacheEvidencePins'] = [result_pin] + ([public_pin] if public is not None else [])
            if read_guard is not None:
                read_guard.finish(terminal_known=state != 'TERMINAL_UNKNOWN' and runner.readers_terminal)
            # RUNNING continues to exclude cached replay until repository guard
            # removal has its terminal receipt. A failed unlink/fsync/restore
            # must never leave a previously published SUCCEEDED journal.
            journal.finish(result_pin, state)
        except Exception as error:
            error.unknown = bool(getattr(error, 'unknown', False)) or state == 'TERMINAL_UNKNOWN' or read_guard is not None
            error.original_pins = list(runner.original_pins) + [ref for ref in getattr(error, 'original_pins', [])
                                                             if ref not in runner.original_pins]
            error.exit_code = runner.actual_exit_code
            if read_guard is not None:
                # A thrown write can have replaced SUCCEEDED on disk. Exclude
                # that cache before attempting result/target/output correction.
                try:
                    journal.reconcile(error)
                except Exception as recording:
                    failure = RecoveryError('RECOVERY_TERMINAL_STATE_PERSISTENCE_FAILED',
                        unknown=True, exit_code=runner.actual_exit_code)
                    failure.original_code = getattr(error, 'code', type(error).__name__)
                    failure.original_pins = error.original_pins
                    failure.recording_error = type(recording).__name__
                    raise failure from recording
                result.update(state='TERMINAL_UNKNOWN', data=None,
                    failureCode=getattr(error, 'code', 'RECOVERY_'+type(error).__name__.upper()),
                    message='Recovery stopped; retained evidence and target require reconciliation.',
                    finishedAt=utc())
                unknown_pin = persist_evidence(root/'operation-result.json', result,
                    unknown=True, exit_code=runner.actual_exit_code)
                persist_evidence(target_state_path, dict(schemaVersion='RecoveryTargetExecutionState/v1',
                    operationId=request['operationId'], requestId=request['requestId'], targetIdentityPin=identity,
                    state='TERMINAL_UNKNOWN', resultPin=unknown_pin, updatedAt=utc()),
                    unknown=True, exit_code=runner.actual_exit_code)
                if public is not None:
                    public.publish(result, exit_code=runner.actual_exit_code)
                try:
                    journal.finish(unknown_pin, 'TERMINAL_UNKNOWN')
                except Exception as recording:
                    failure = RecoveryError('RECOVERY_TERMINAL_STATE_PERSISTENCE_FAILED',
                        unknown=True, exit_code=runner.actual_exit_code)
                    failure.original_code = getattr(error, 'code', type(error).__name__)
                    failure.original_pins = error.original_pins
                    failure.recording_error = type(recording).__name__
                    raise failure from recording
            raise
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv); started = utc(); request = None
    public = PublicOutput(args.output)
    try:
        request_pin = pin(args.request); request = pinned_json(request_pin)
        result = execute(request, request_pin, public)
    except Exception as error:
        # Malformed identity cannot be repaired with invented operation IDs.
        if not isinstance(request, dict) or not all(type(request.get(key)) is str and request[key]
            for key in ('operationId', 'requestId', 'action')):
            print('RECOVERY_REQUEST_INVALID'); return 1
        state = 'TERMINAL_UNKNOWN' if getattr(error, 'unknown', False) else 'FAILED_RETAINED'
        result = dict(schemaVersion='backup-restore-operation-result/v1', operationId=request['operationId'],
            requestId=request['requestId'], action=request['action'], state=state,
            failureCode=getattr(error, 'code', 'RECOVERY_'+type(error).__name__.upper()),
            message='Required recovery input or authority failed validation.', data=None,
            originalResultPins=getattr(error, 'original_pins', []),
            startedAt=started, finishedAt=utc(), actualExitCode=getattr(error, 'exit_code', None))
        try:
            public.publish(result, exit_code=getattr(error, 'exit_code', None))
        except Exception as recording:
            print(getattr(error, 'code', 'RECOVERY_'+type(error).__name__.upper()))
            print(getattr(recording, 'code', 'RECOVERY_'+type(recording).__name__.upper()))
            return 2 if state == 'TERMINAL_UNKNOWN' or getattr(recording, 'unknown', False) else 1
    return {'SUCCEEDED': 0, 'FAILED_RETAINED': 1, 'TERMINAL_UNKNOWN': 2}[result['state']]


if __name__ == '__main__':
    raise SystemExit(main())
