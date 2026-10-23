"""Concrete Linux assembly of the normal capture owner's existing producers.

Deployment values are explicit pinned configuration. All source/action
transports below are real native implementations. The independent NAS/staging
author is retained on an inherited authenticated channel, never replaced by
configuration flags or a fabricated admission result.
"""
import hashlib
import os
from pathlib import Path
import threading
import time

import formal_snapshot_linux as snapshot
from formal_normal_owner import (NormalOwnerInputs, NativeAllocationObservation,
    TrustedTransportObservation, binding, canonical, integer, pin, require, strict_document)
from formal_native_owner_transport import NativeObservationChannel

INPUT_NAMES = frozenset({'policy', 'source_context', 'installed_context', 'release_binding',
    'coverage', 'allocation', 'source_guard', 'archive_program', 'staging_admission', 'mysql_credential'})
DOCUMENT_NAMES = ('sourceReferencesPin', 'bootSourcesPin', 'bootConnectionsPin', 'controlledSourcesPin',
    'resumeRequestPin', 'captureRequestPin', 'recoveryFlowsPin', 'seriesPin', 'catalogBindingPin', 'channelPin')


def validate_capture_claim(capture,*,claim_root,claim_plan,credential_path):
    require(capture['claimRoot']==str(claim_root) and
        snapshot._canonical_bytes(capture['claimBinding'])==claim_plan and
        capture['mysqlCredentialFile']==credential_path,'BACKUP_INTERFACE_BINDING_INVALID')


def validate_configuration(value):
    fields = {'schemaVersion', 'binding', 'programPin', 'inputReferences', 'controlRoot', 'registryRoot',
              'maintenanceMilliseconds', *DOCUMENT_NAMES}
    require(type(value) is dict and set(value) == fields and
            value['schemaVersion'] == 'backup-normal-owner-assembly/v1' and
            type(value['inputReferences']) is dict and set(value['inputReferences']) == INPUT_NAMES,
            'BACKUP_INTERFACE_SCHEMA_INVALID')
    binding(value['binding'])
    for reference in (value['programPin'], *value['inputReferences'].values(),
                      *(value[name] for name in DOCUMENT_NAMES)):
        pin(reference)
    for name in ('controlRoot', 'registryRoot'):
        require(type(value[name]) is str and value[name].startswith('/') and '\\' not in value[name],
                'BACKUP_INTERFACE_SCHEMA_INVALID')
    integer(value['maintenanceMilliseconds'], 1, 7200000)
    return value


class PrivateOriginals:
    def __init__(self, claim, guard, deadline):
        self.claim = claim
        self.guard = guard
        self.deadline = deadline
        self.files = {}
        self.directories = {}

    def read(self, reference, limit=16*1024*1024):
        import formal_boot_state as boot
        reference = pin(reference)
        path = boot._absolute(reference['path'])
        if path in self.files:
            pair, saved_limit, saved_reference = self.files[path]
            require(reference == saved_reference and limit >= len(pair[0]),
                    'BACKUP_INTERFACE_SOURCE_CHANGED')
            self.check()
            return pair[0]
        self.guard()
        pair = boot._read_secure(path, 0o600, limit, no_atime=True)
        require(pair[1][0] == self.claim.root.stat().st_dev and
                len(pair[0]) == reference['bytes'] and hashlib.sha256(pair[0]).hexdigest() == reference['sha256'],
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        with boot._directory(path.parent, no_atime=True) as (_, chain):
            self.directories[path.parent] = chain
        self.files[path] = (pair, limit, dict(reference))
        self.check()
        return pair[0]

    def document(self, reference, limit=16*1024*1024):
        return strict_document(self.read(reference, limit), limit)

    def check(self):
        import formal_boot_state as boot
        require(time.monotonic() < self.deadline, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
        self.guard()
        self.claim.assert_owned()
        for path, chain in self.directories.items():
            boot._directory_unchanged(path, chain)
        for path, (pair, limit, _) in self.files.items():
            require(boot._read_secure(path, 0o600, limit, no_atime=True) == pair,
                    'BACKUP_INTERFACE_SOURCE_CHANGED')
        self.guard()
        self.claim.assert_owned()
        for path, (pair, _, _) in self.files.items():
            require(boot._signature(path.lstat()) == pair[1], 'BACKUP_INTERFACE_SOURCE_CHANGED')
        for path, chain in self.directories.items():
            boot._directory_unchanged(path, chain)


class NativeAssemblyAdapter:
    def __init__(self, claim, configuration, originals, documents, channel, *, deadline):
        self.claim = claim
        self.configuration = configuration
        self.configuration_raw = canonical(configuration)
        self.originals = originals
        self.documents = documents
        self.channel = channel
        self.deadline = deadline
        self.pid = os.getpid()
        self.thread = threading.get_ident()
        self.fd = claim._fd
        self.owner = None
        self.author = None
        self.inputs = None
        self.protection_reference = None
        self.final_guard = None
        self.host_checks = None

    def check_original_owner(self, claim, fd, pid, thread, deadline):
        require(claim is self.claim and fd == self.fd == claim._fd and
                pid == self.pid == os.getpid() and thread == self.thread == threading.get_ident() and
                time.monotonic() < min(deadline, self.deadline), 'BACKUP_INTERFACE_AUTHOR_LOST')
        self.control_guard()

    def control_guard(self):
        require(os.getpid() == self.pid and threading.get_ident() == self.thread and
                self.claim._fd == self.fd and canonical(self.configuration) == self.configuration_raw,
                'BACKUP_INTERFACE_AUTHOR_LOST')
        self.originals.check()
        self.channel.check()
        self.claim.assert_owned()

    def bind_original_author(self, owner, author):
        require(self.owner is None and owner.claim is self.claim and author.owner is owner,
                'BACKUP_INTERFACE_SEQUENCE_INVALID')
        self.owner = owner
        self.author = author
        self.control_guard()

    def observation(self, action, payload, reference, deadline, *, sequence=None):
        require(self.owner is not None and self.author is not None,
                'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        raw, actual_reference, channel_sequence, sent, received, guard = self.channel.exchange(
            action, payload, expected_reference=reference, deadline=deadline)
        return TrustedTransportObservation(self.owner, self.author, raw=raw, reference=actual_reference,
            sequence=channel_sequence if sequence is None else sequence, sent=sent, received=received,
            current_guard=guard)

    def verify_allocation(self, root, identity, proof, verification, budget, deadline):
        observed = self.observation('allocation-local', dict(binding=self.inputs.binding,
            root=str(root), deviceIdentityReference=identity.reference, allocationProofReference=proof.reference,
            budgetPolicySha256=hashlib.sha256(canonical(budget.policy)).hexdigest()), verification.reference, deadline)
        require(observed.raw == verification.raw, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        value = strict_document(observed.raw)
        require(type(value) is dict and set(value) == {'schemaVersion', 'binding', 'target',
                'deviceIdentityReference', 'allocationProofReference', 'rulesSha256', 'authorHeld', 'approved'} and
                value['schemaVersion'] == 'backup-native-allocation-verification/v1' and
                value['binding'] == self.inputs.binding and value['target'] == str(root) and
                value['deviceIdentityReference'] == identity.reference and
                value['allocationProofReference'] == proof.reference and
                value['rulesSha256'] == hashlib.sha256(canonical(strict_document(proof.raw)['rules'])).hexdigest() and
                value['authorHeld'] is True and value['approved'] is True,
                'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        return NativeAllocationObservation(self.owner, self.author, device_reference=identity,
            rule_reference=proof, target=str(root), peak=integer(budget.policy['totalBytes'], 1),
            current_guard=observed.check)

    def verify_remote_allocation(self, target, reference, peak, budget, binding, deadline):
        observed = self.observation('allocation-'+target, dict(binding=binding,
            allocatedUpperBoundBytes=integer(peak, 1)), reference.reference, deadline)
        require(observed.raw == reference.raw, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        value = strict_document(observed.raw)
        require(type(value) is dict and set(value) == {'schemaVersion', 'binding', 'target',
                'allocatedUpperBoundBytes', 'resourceObservationReference', 'authorHeld', 'approved'} and
                value['schemaVersion'] == 'backup-native-remote-allocation-verification/v1' and
                value['binding'] == binding and value['target'] == target and
                value['allocatedUpperBoundBytes'] == peak and value['authorHeld'] is True and
                value['approved'] is True, 'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        pin(value['resourceObservationReference'])
        return NativeAllocationObservation(self.owner, self.author, device_reference=None,
            rule_reference=reference, target=target, peak=peak, current_guard=observed.check)

    def observe_nas_admission(self, intent, raw, deadline):
        document = strict_document(raw)
        # The original NAS document is echoed only by the held native author;
        # the file's existence and JSON booleans alone never admit capture.
        observed = self.observation('admission-nas', dict(intentReference=intent.reference.reference,
            admissionId=document['admissionId'], admissionSha256=hashlib.sha256(raw).hexdigest()), None, deadline)
        require(observed.raw == raw, 'BACKUP_INTERFACE_SOURCE_CHANGED')
        return observed

    def observe_staging_admission(self, intent, reference, deadline):
        return self.observation('admission-staging', dict(intentReference=intent.reference.reference,
            intentSha256=hashlib.sha256(intent.raw).hexdigest(),
            peakAllocatedBytes=intent.document['windowsStagingPeakAllocatedBytes']), reference, deadline)

    def observe_control_budget(self, request, deadline):
        return self.observation('control-budget', dict(sequence=request['sequence'],
            remainingMilliseconds=request['budget']['remainingMilliseconds']),
            request['budget']['observationReference'], deadline, sequence=request['sequence'])

    def verify_parent_repository(self, owner, series, deadline):
        return self.observation('repository-parent', dict(binding=self.inputs.binding,
            repositoryPointPin=series.spec['parentRepositoryPointPin'], capturePointPin=series.spec['parentPointPin']),
            series.spec['parentRepositoryPointPin'], deadline)

    def verify_catalog_sources(self, owner, series, prepare, capture, recovery):
        expected = self.documents['catalogBindingPin']
        fields = {'schemaVersion', 'sourceIdentity', 'claimBindingSha256', 'databaseUuid',
            'databaseName', 'mysqlContainerId', 'minioContainerId', 'approvedSourceTargetPin',
            'sharedScopeSha256', 'assetReferences', 'writerReferences', 'binlogDatabaseScope'}
        require(type(expected) is dict and set(expected) == fields and
                expected['schemaVersion'] == 'backup-native-catalog-binding/v1' and
                expected['sourceIdentity'] == series.catalog['sourceIdentity'] and
                expected['claimBindingSha256'] == hashlib.sha256(owner.claim._plan).hexdigest() and
                expected['databaseUuid'] == strict_document(owner.claim._plan)['databaseUuid'] and
                expected['minioContainerId'] == strict_document(owner.claim._plan)['minioContainerId'] and
                expected['databaseName'] == capture['database'] and
                expected['mysqlContainerId'] == capture['mysqlContainerId'] == prepare['mysql'].container and
                expected['sharedScopeSha256'] == capture['sharedScopeSha256'] and
                expected['assetReferences'] == series.catalog['assets'] and
                expected['writerReferences'] == series.catalog['writers'] and
                expected['binlogDatabaseScope'] == [capture['database']],
                'BACKUP_INTERFACE_BINDING_INVALID')
        target = pin(expected['approvedSourceTargetPin'])
        self.originals.read(target)
        require(target['path'] == prepare['source_refs']['approved-source-target.json']['path'] and
                target['sha256'] == prepare['source_refs']['approved-source-target.json']['sha256'],
                'BACKUP_INTERFACE_BINDING_INVALID')
        # Retain the approved scope. Current databases are an extra preflight;
        # actual historical events are independently inspected before SQL export.
        series.binlog_database_scope = list(expected['binlogDatabaseScope'])
        databases = prepare['mysql'].query('SHOW DATABASES;').splitlines()
        require(all(name and name.strip() == name for name in databases) and
                len(databases) == len(set(databases)) and
                set(databases)-{'information_schema', 'mysql', 'performance_schema', 'sys'} == {capture['database']},
                'BACKUP_INTERFACE_BINDING_INVALID')
        from formal_capture_semantics import SemanticCapture
        object_asset = next(asset for asset in series.catalog['assets'] if asset['class'] == 'objects')
        series.semantic_source = SemanticCapture(series, self.originals,
            self.originals.document(object_asset['reference']))
        series.semantic_source.verify_endpoint(self.control_guard)
        # Source storage and registered writer barriers are observed by native
        # code before preparation and again immediately before protected capture.
        self.source_guard()

    def source_guard(self):
        import formal_capture_producer as producer
        import formal_external_callers as external
        import formal_host_admission as host
        import formal_ingress_control as ingress
        self.control_guard()
        capture = self.documents['captureRequestPin']
        target = self.documents['catalogBindingPin']['approvedSourceTargetPin']
        producer.verify_approved_source_storage(self.claim, capture, self.originals.read(target))
        external.guard_external_callers(self.claim, self.inputs.recovery_arguments['external_transport'])
        if self.host_checks is None:
            self.host_checks = host.ClosedHostAdmissionChecks(self.claim,
                native=self.inputs.recovery_arguments['host_native'], controlled_stop=True)
        self.host_checks.prepare(guard=self.control_guard, deadline=self.deadline)
        self.host_checks.assert_native(deadline=self.deadline)
        observed = ingress.assert_ingress(self.claim, native=self.inputs.recovery_arguments['ingress_native'])
        require(observed['rulesSha256'] == capture['ingressRulesSha256'] or
                observed.get('phase') == 'RECOVERY_DEPENDENCIES_PERMITTED',
                'BACKUP_INTERFACE_BINDING_INVALID')
        self.control_guard()

    def bind_prepared(self, prepared):
        import formal_controlled_container_sources as controlled
        self.control_guard()
        require(prepared.owner is self.owner and prepared.inputs is self.inputs and
                self.inputs.recovery_arguments['container_actions'] is None,
                'BACKUP_INTERFACE_SEQUENCE_INVALID')
        actions = controlled.ControlledSharedContainerActions(prepared.result['controlledOriginals'],
            controlled.NativeControlledDockerActions(self.documents['channelPin']['hostBootId']))
        self.inputs.recovery_arguments['container_actions'] = actions
        self.control_guard()

    def bind_capture_result(self, result):
        require(type(result) is tuple and len(result) == 2 and callable(result[1]) and
                result[0].get('state') == 'A_ORIGINAL_CAPTURE_AND_RECOVERY_COMPLETED_PENDING_NAS',
                'BACKUP_INTERFACE_COMPONENT_FAILED')
        result[1]()
        self.final_guard = result[1]

    def protect_sources(self, owner, resume_checks, admission):
        require(owner is self.owner and resume_checks.claim is self.claim and resume_checks.consumed is not None,
                'BACKUP_INTERFACE_AUTHORITY_INVALID')
        admission.check_budget(self.inputs.budget)
        observed = self.observation('writer-protection', dict(binding=self.inputs.binding,
            sourceInventoryReference=admission.intent.prepared.inventory.reference,
            writerReferences=self.inputs.series.catalog['writers']), None, owner.deadline)
        value = strict_document(observed.raw)
        require(type(value) is dict and set(value) == {'schemaVersion', 'binding',
                'sourceInventoryReference', 'writerReferences', 'authorHeld', 'protectionHeld'} and
                value['schemaVersion'] == 'backup-native-writer-protection/v1' and
                value['binding'] == self.inputs.binding and
                value['sourceInventoryReference'] == admission.intent.prepared.inventory.reference and
                value['writerReferences'] == self.inputs.series.catalog['writers'] and
                value['authorHeld'] is True and value['protectionHeld'] is True,
                'BACKUP_INTERFACE_ADMISSION_REQUIRED')
        observed.check()
        self.protection_reference = observed.reference
        self.source_guard()

    def failure_restore(self, owner, resume_checks, error):
        require(owner is self.owner, 'BACKUP_INTERFACE_AUTHOR_LOST')
        require(getattr(error, 'clientCleanupUncertain', False) is not True,
                'BACKUP_INTERFACE_TERMINAL_UNKNOWN')
        if self.final_guard is not None:
            self.final_guard()
            return dict(sourceRestored=True, disasterRecoveryVerified=False,
                        recoveryActionReplayed=False), self.final_guard
        from formal_capture_failure_recovery import restore_failed_capture_source
        with self.inputs.budget.activate():
            result, guard = restore_failed_capture_source(owner, resume_checks,
                capture_request=self.inputs.capture_request, recovery=self.inputs.recovery_arguments,
                control_guard=self.control_guard, deadline=owner.deadline)
        self.final_guard = guard
        return result, guard

    def close(self):
        self.channel.close()


def assemble_original_normal_owner(claim, configuration, *, original_guard, deadline):
    from formal_filesystem_watchdog import require_native_runtime
    import formal_capture_producer as producer
    import formal_controlled_container_sources as controlled
    import formal_external_callers as external
    import formal_host_admission as host
    import formal_ingress_control as ingress
    import formal_service_health as health
    import formal_capture_failure_recovery
    import formal_capture_recovery_inputs
    import formal_capture_semantics
    from formal_backup_lab import approved_capture_source as approved_source_scope
    require_native_runtime()
    lab = type(configuration) is dict and configuration.get('schemaVersion')=='backup-lab-native-assembly-config/v1'
    if lab:
        from formal_backup_lab import validate_assembly, current_authority
        validate_assembly(configuration);authority=current_authority()
        require(configuration['labContextPin']==authority.context_pin,'BACKUP_LAB_CONTEXT_CHANGED')
    else:validate_configuration(configuration)
    configuration = strict_document(canonical(configuration), 16*1024*1024)
    require(os.geteuid() == 0 and type(claim) is snapshot.FormalMaintenanceClaim,
            'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
    originals = PrivateOriginals(claim, original_guard, deadline)
    program = configuration['programPin']
    originals.read(program, 1048576)
    require(Path(program['path']).resolve() == Path(__file__).resolve(),
            'BACKUP_INTERFACE_SOURCE_CHANGED')
    documents = {name: originals.document(configuration[name]) for name in DOCUMENT_NAMES}
    references = configuration['inputReferences']
    for name, reference in references.items():
        # Credentials are held privately and never added to capture materials.
        originals.read(reference, 1048576 if name == 'archive_program' else 16*1024*1024)
    capture = documents['captureRequestPin']
    validate_capture_claim(capture,claim_root=claim.root,claim_plan=claim._plan,
        credential_path=references['mysql_credential']['path'])
    credential = producer.read_credential(capture['mysqlCredentialFile'])
    mysql = producer.PrivateDockerMySql(capture['mysqlContainerId'], credential, timeout=5)
    boot_sources = documents['bootSourcesPin']
    connections = documents['bootConnectionsPin']
    require(type(boot_sources) is dict and type(connections) is dict and
            set(connections) == {role for role, source in boot_sources.items() if source['peer'] != 'local'},
            'BACKUP_INTERFACE_SCHEMA_INVALID')
    target_pin = documents['catalogBindingPin']['approvedSourceTargetPin']
    source = approved_source_scope(originals.read(target_pin), target_pin['sha256'], claim._plan, capture['database'])
    producer._validate_selected_source_request(capture, source)
    if lab:
        require(configuration['binding']['releaseTag']==authority.context['rehearsalId'] and
                configuration['inputReferences']['source_context']==authority.context['sourceIdentityPin'] and
                configuration['inputReferences']['installed_context']==authority.context['executionHostPin'],
                'BACKUP_LAB_BINDING_INVALID')
    owner_binding = binding(configuration['binding'])
    channel_configuration = documents['channelPin']
    require(channel_configuration['bindingSha256'] == hashlib.sha256(canonical(owner_binding)).hexdigest(),
            'BACKUP_INTERFACE_BINDING_INVALID')
    channel = NativeObservationChannel(channel_configuration, original_guard=originals.check,
        deadline=deadline, control_device=claim.root.stat().st_dev)
    try:
        adapter = NativeAssemblyAdapter(claim, configuration, originals, documents, channel, deadline=deadline)
        inputs = NormalOwnerInputs(binding_value=owner_binding, policy_reference=references['policy'],
            source_context_reference=references['source_context'], installed_context_reference=references['installed_context'],
            release_binding_reference=references['release_binding'], coverage_reference=references['coverage'],
            allocation_reference=references['allocation'], source_guard_reference=references['source_guard'],
            program_reference=program, archive_program_reference=references['archive_program'],
            staging_admission_reference=references['staging_admission'],
            control_root=Path(configuration['controlRoot']), registry_root=Path(configuration['registryRoot']),
            prepare_arguments=dict(source_refs=documents['sourceReferencesPin'], boot_sources=boot_sources,
                controlled_sources=documents['controlledSourcesPin'], mysql=mysql, boot_connections=connections,
                docker_sources=controlled.NativeControlledDockerSources()),
            resume_request=documents['resumeRequestPin'], capture_request=capture,
            recovery_arguments=dict(approved_source=source, container_actions=None,
                # The legacy signed authority uses this host's wall-clock
                # expiry; transport/capture deadlines remain monotonic.
                maintenance_end=time.time()+min(deadline-time.monotonic(),
                    configuration['maintenanceMilliseconds']/1000),
                recovery_flows=documents['recoveryFlowsPin'], external_transport=external.SshDockerTransport(),
                host_native=host.NativeHostAdmission(), health_probe=health.NativeNetworkProbe(),
                ingress_native=ingress.NativeNft()), series_specification=documents['seriesPin'], adapter=adapter)
        adapter.inputs = inputs
        originals.check()
        return inputs
    except BaseException:
        channel.close()
        raise
