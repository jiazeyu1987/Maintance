"""Bind an immutable capture configuration to the explicitly selected request.

The owner still validates the entire repository chain and capture material.
This module supplies that owner's inputs; it never chooses a parent or changes
the shared source configuration after a successful backup.
"""
from copy import deepcopy
from pathlib import Path

import recovery_control_executor as executor
from recovery_control_smallapp import canonical, need, opaque, persist


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
    source = repository['sources'][request['sourceConfigRef']]
    capture_pin = executor.pin(source['configurationPath'])
    capture = native.document(capture_pin)
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

    immutable('request-inputs.json', dict(request=request, ownerConfigurationPin=owner_pin,
        captureConfigurationPin=capture_pin, objectSourcePin=objects_pin, pointBindingPin=point_binding_pin))
    capture['source']['objectSourcePin'] = immutable('objects.json', objects)
    repository['sources'][request['sourceConfigRef']]['configurationPath'] = immutable('capture.json', capture)['path']
    return immutable('repository.json', repository)
