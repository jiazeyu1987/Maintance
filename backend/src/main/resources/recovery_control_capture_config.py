"""Bind an immutable capture configuration to the explicitly selected request.

The owner still validates the entire repository chain and capture material.
This module supplies that owner's inputs; it never chooses a parent or changes
the shared source configuration after a successful backup.
"""
from copy import deepcopy
from pathlib import Path
import re

import recovery_control_executor as executor
from recovery_control_smallapp import Failure, canonical, need, opaque, persist


def program_policy(configuration, source_ref):
    policies = configuration.get('sourceProgramPolicies', {})
    need(type(policies) is dict, 'SOURCE_PROGRAM_POLICIES_INVALID')
    if source_ref not in policies:
        return None
    policy = policies[source_ref]
    epochs = configuration.get('sourceEpochPolicies', {})
    need(type(policy) is dict and type(epochs) is dict and source_ref in epochs and
         type(policy.get('backupEpochPolicy')) is dict and
         policy['backupEpochPolicy'] == epochs[source_ref], 'SOURCE_PROGRAM_EPOCH_BINDING_INVALID')
    return policy


def validate_source_epoch_scope(owner, capture, policy, source_ref):
    """Verify the physical source before any automatic epoch metadata append."""
    need(policy.get('sourceIdentity') == capture['source']['sourceIdentity'] and
         policy.get('databaseUuid') == capture['source']['databaseUuid'] and
         policy.get('sourceLockPath') == capture.get('sourceLockPath') and
         type(policy.get('sourceLockPath')) is str, 'SOURCE_EPOCH_POLICY_BINDING_INVALID')
    selected_source = owner['sources'][source_ref]
    storage = [capture.get('archiveRoot'), capture['source'].get('minioDataPath'),
               selected_source.get('stagingRoot'), owner.get('repositoryRoot'), owner.get('operationRoot')]
    for value in (value for value in storage if value is not None):
        need(type(value) is str and Path(value).is_absolute(), 'SOURCE_EPOCH_STORAGE_INVALID')
        scope = Path(value)
        for protected in (Path(policy['root']), Path(policy['sourceLockPath'])):
            need(protected != scope and protected not in scope.parents and scope not in protected.parents,
                 'SOURCE_EPOCH_STORAGE_OVERLAP')


def read_capture_configuration(reader, configuration, owner, source_ref):
    """Resolve the source through the caller's pinned reader and shared budget."""
    policy = program_policy(configuration, source_ref)
    base_pin = executor.pin(owner['sources'][source_ref]['configurationPath'])
    capture_pin, evidence = base_pin, []
    if policy is not None:
        from recovery_program_generation import resolve_capture
        from recovery_engine import RecoveryError
        from recovery_backup_epoch import try_reconcile_current
        guard = getattr(reader, 'guard', None)
        def resolve():
            return resolve_capture(policy, source_ref, base_pin, reader=reader.document, guard=guard)
        try:
            try:
                capture_pin, evidence = resolve()
            except (ValueError, RecoveryError) as error:
                if getattr(error, 'code', str(error)) != 'PROGRAM_EPOCH_NOT_READY':
                    raise
                # Preserve the existing crash-after-receipt metadata closure.
                # Normal READY reads do not incur another journal scan. The
                # original physical scope is checked before taking a real
                # nonblocking source lock or appending the original receipt.
                base = reader.document(base_pin)
                validate_source_epoch_scope(owner, base, policy['backupEpochPolicy'], source_ref)
                kwargs = {'guard': guard} if guard is not None else {}
                current = try_reconcile_current(policy['backupEpochPolicy'], **kwargs)
                need(current['state'] == 'READY', 'PROGRAM_EPOCH_NOT_READY')
                capture_pin, evidence = resolve()
        except (ValueError, RecoveryError) as error:
            code = getattr(error, 'code', str(error))
            raise Failure(code if type(code) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,95}', code)
                          else 'SOURCE_PROGRAM_GENERATION_INVALID') from None
        need(type(evidence) is list and evidence, 'SOURCE_PROGRAM_EVIDENCE_REQUIRED')
        # Register every original with PlanReader's final identity check, even
        # when the generation resolver can validate it without reading a body.
        for reference in evidence:
            reader.document(reference)
    capture = reader.document(capture_pin)
    need(capture.get('sourceConfigRef') == source_ref, 'CAPTURE_REQUEST_SOURCE_MISMATCH')
    return capture_pin, capture, evidence


def verify_request_epoch(native, configuration, request, epoch):
    """Do not pair a pinned request configuration with a later restore epoch."""
    if program_policy(configuration, request['sourceConfigRef']) is None:
        return
    path = Path(configuration['taskRoot'])/'request-configurations'/opaque(request['operationId'])/'request-inputs.json'
    inputs = native.document(executor.pin(path))
    need(inputs.get('request') == request and type(epoch) is dict and epoch.get('state') == 'READY' and
         epoch.get('eventPin') in inputs.get('programGenerationEvidencePins', []),
         'SOURCE_PROGRAM_EPOCH_CHANGED')


def bind_documents(request, repository, capture, objects, parent):
    repository, capture, objects = (deepcopy(value) for value in (repository, capture, objects))
    source = request['sourceConfigRef']
    need(request['action'] in ('FULL', 'INCREMENTAL') and capture['sourceConfigRef'] == source
         and source in repository['sources'], 'CAPTURE_REQUEST_SOURCE_MISMATCH')
    if request['action'] == 'FULL':
        need(request['parentChainRef'] is None and parent is None, 'FULL_REFERENCES_FORBIDDEN')
        capture['parent'] = None
        repository['parentChains'] = {}
        objects['parentExportIndexPin'] = None
    else:
        need(parent is not None and parent['reference'] == request['parentChainRef']
             and parent['sourceConfigRef'] == source, 'CAPTURE_PARENT_SOURCE_MISMATCH')
        point, captured, material, binding = (parent[key] for key in ('point', 'capturePoint', 'material', 'binding'))
        need(point['backupId'] == captured['backupId'] == parent['reference']
             and point['generationId'] == captured['generationId']
             and material['sourceDatabaseUuid'] == captured['databaseEnd']['databaseUuid'] == capture['source']['databaseUuid']
             and captured['sourceIdentity'] == capture['source']['sourceIdentity']
             and point['commonRecoveryPoint'] == captured['commonRecoveryPoint'] == material['recoveryPoint'],
             'CAPTURE_PARENT_IDENTITY_MISMATCH')
        exporters = [row for row in capture['source']['materialPins'] if row['purpose'] == 'mysqlbinlog-exporter']
        need(len(exporters) == 1, 'CAPTURE_BINLOG_EXPORTER_REQUIRED')
        capture['parent'] = dict(parentChainRef=parent['reference'],
            capturePointPin=material['database']['capturePointPin'],
            repositoryPointPin=parent['pointPin'], objectContentIndexPin=binding['objectContentIndexPin'])
        repository['parentChains'] = {parent['reference']: parent['pointPin']}
        objects['parentExportIndexPin'] = binding['objectContentIndexPin']
    return repository, capture, objects


def for_request(native, configuration, request, owner_pin, point_binding_pin):
    repository = native.document(owner_pin)
    capture_pin, capture, generation_evidence = read_capture_configuration(
        native, configuration, repository, request['sourceConfigRef'])
    objects_pin = capture['source']['objectSourcePin']
    objects = native.document(objects_pin)
    parent = None
    if request['action'] == 'INCREMENTAL':
        selected = native.document(point_binding_pin)
        output = native.document(selected['resultPin'])
        point_pin = output['data']['pointPin']
        binding = native.document(output['data']['repositoryBindingPin'])
        material = native.document(binding['recoveryMaterialPin'])
        parent = dict(reference=selected['reference'], sourceConfigRef=selected['sourceConfigRef'],
            pointPin=point_pin, point=native.document(point_pin), binding=binding, material=material,
            capturePoint=native.document(material['database']['capturePointPin']))
    repository, capture, objects = bind_documents(request, repository, capture, objects, parent)

    # Configuration inputs live separately from the dispatch ledger. Resolving
    # a request must not create an incomplete dispatch reservation.
    from recovery_control_smallapp_native import directory
    root = Path(configuration['taskRoot'])/'request-configurations'
    root.mkdir(mode=0o700, exist_ok=True)
    directory(root, configuration['taskRoot'])
    root = root/opaque(request['operationId'])
    root.mkdir(mode=0o700, exist_ok=True)
    directory(root, configuration['taskRoot'])

    def immutable(name, value):
        path = root/name
        if path.exists():
            reference = executor.pin(path)
            need(native.raw(reference) == canonical(value), 'ORIGINAL_CAPTURE_CONFIGURATION_CHANGED')
            return reference
        persist(path, value)
        return executor.pin(path)

    inputs = dict(request=request, ownerConfigurationPin=owner_pin,
        captureConfigurationPin=capture_pin, objectSourcePin=objects_pin, pointBindingPin=point_binding_pin)
    if generation_evidence:
        inputs['programGenerationEvidencePins'] = generation_evidence
    immutable('request-inputs.json', inputs)
    capture['source']['objectSourcePin'] = immutable('objects.json', objects)
    repository['sources'][request['sourceConfigRef']]['configurationPath'] = immutable('capture.json', capture)['path']
    return immutable('repository.json', repository)
