"""Resolve a selected archive into request-owned inputs, never rewrite originals.

The source's authenticated live catalogue remains the eligibility authority.
The safe recovery owner independently verifies the complete material and payload
chain. Canonical archive and identity paths must be readable on the destination;
this resolver does not translate pins or copy source application data.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

import recovery_control_executor as executor
from recovery_control_smallapp import canonical, decode, exact, need, opaque, persist


def read_document(reference, limit):
    need(type(reference) is dict and type(reference.get('bytes')) is int and
         0 <= reference['bytes'] <= limit, 'ARCHIVE_METADATA_LIMIT_EXCEEDED')
    executor.verify(reference)
    actual, raw = executor.pinned_read(reference['path'], True)
    need(actual == reference, 'ARCHIVE_METADATA_CHANGED')
    return decode(raw)


def bind_archive_chain(source, request):
    catalogue = source['archiveCatalogue']
    exact(catalogue, 'schemaVersion maximumPointFiles maximumMetadataBytes sourceAdmissionPin',
          'ARCHIVE_CATALOGUE_FIELDS_INVALID')
    need(catalogue['schemaVersion'] == 'RecoveryArchiveCatalogue/v1' and
         type(catalogue['maximumPointFiles']) is int and 1 <= catalogue['maximumPointFiles'] <= 10000 and
         type(catalogue['maximumMetadataBytes']) is int and
         1024 <= catalogue['maximumMetadataBytes'] <= 64 * 1024 * 1024, 'ARCHIVE_CATALOGUE_LIMIT_INVALID')
    maximum = catalogue['maximumMetadataBytes']
    roots = [Path(value) for value in source['archiveRoots']]
    need(roots and len(roots) == len(set(roots)) and all(root.is_absolute() and
         root.resolve() == root and root.is_dir() for root in roots), 'ARCHIVE_ROOT_UNAVAILABLE')
    reference = opaque(request['recoveryPointRef'])
    matches = []
    count = 0
    for root in roots:
        for path in root.glob('*/.repository/point.json'):
            count += 1
            need(count <= catalogue['maximumPointFiles'], 'ARCHIVE_POINT_LIMIT_EXCEEDED')
            need(path.resolve() == path, 'ARCHIVE_POINT_PATH_CHANGED')
            candidate = executor.pin(path)
            value = read_document(candidate, maximum)
            if value.get('backupId') == reference:
                matches.append(candidate)
    need(len(matches) == 1, 'ARCHIVE_POINT_REFERENCE_AMBIGUOUS' if matches else 'ARCHIVE_POINT_NOT_FOUND')
    identity = read_document(source['sourceScopePin'], maximum)['sourceIdentityPin']
    points, bindings, evidence, visiting = [], {}, [], set()

    def visit(pin):
        need(pin['sha256'] not in visiting and len(visiting) < catalogue['maximumPointFiles'],
             'ARCHIVE_CHAIN_CYCLE_OR_LIMIT')
        visiting.add(pin['sha256'])
        path = Path(pin['path'])
        need(path.name == 'point.json' and path.parent.name == '.repository' and
             any(path.parent.parent.parent == root for root in roots), 'ARCHIVE_PARENT_OUTSIDE_ROOT')
        point = read_document(pin, maximum)
        need(point.get('schemaVersion') == 'RepositoryPoint/v1' and
             point.get('integrityState') == 'COMPLETE' and point.get('pointType') in ('FULL','INCREMENTAL'),
             'ARCHIVE_POINT_INCOMPLETE')
        manifest = read_document(point['manifestPin'], maximum)
        need(Path(point['manifestPin']['path']) == path.parent/'manifest.json' and
             manifest.get('schemaVersion') == 'RepositoryManifest/v1' and all(
                 point[key] == manifest[key] for key in ('backupId','generationId','pointType','parentPointPins')) and
             manifest['sourceIdentityPin'] == identity, 'ARCHIVE_SOURCE_BINDING_INVALID')
        parents = point['parentPointPins']
        need(type(parents) is list, 'ARCHIVE_PARENT_PREFIX_INVALID')
        if point['pointType'] == 'FULL':
            need(not parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
        else:
            need(parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
            visit(parents[-1])
            need(parents == points and all(read_document(parent, maximum)['generationId'] ==
                 point['generationId'] for parent in points), 'ARCHIVE_PARENT_PREFIX_INVALID')
        binding_pin = executor.pin(path.parent/'recovery-repository-binding.json')
        binding = read_document(binding_pin, maximum)
        exact(binding, 'schemaVersion backupId generationId repositoryPointPin manifestPin sourceScopePin '
              'recoveryMaterialPin objectContentIndexPin', 'ARCHIVE_REPOSITORY_BINDING_INVALID')
        need(binding['schemaVersion'] == 'RecoveryRepositoryBinding/v1' and
             binding['repositoryPointPin'] == pin and binding['manifestPin'] == point['manifestPin'] and
             binding['sourceScopePin'] == source['sourceScopePin'] and
             binding['backupId'] == point['backupId'] and binding['generationId'] == point['generationId'],
             'ARCHIVE_SOURCE_BINDING_INVALID')
        terminal, readback, close = [read_document(point[key], maximum) for key in
            ('originalExitEvidencePin','readbackEvidencePin','ownerCloseEvidencePin')]
        for key, filename in [('originalExitEvidencePin','original-exit.json'),
                              ('readbackEvidencePin','readback-original.json'),
                              ('ownerCloseEvidencePin','archive-close.json')]:
            need(Path(point[key]['path']) == path.parent/filename, 'ARCHIVE_ORIGINAL_OUTSIDE_SIDECAR')
            evidence.append(point[key])
        need(terminal.get('state') == 'EXITED' and terminal.get('processTerminated') is True and
             type(terminal.get('actualExitCode')) is int and terminal['actualExitCode'] == 0 and
             readback.get('schemaVersion') == 'RepositoryMinimumReadback/v1' and
             readback.get('operationId') == point['backupId'] and readback.get('manifestPin') == point['manifestPin'] and
             readback.get('sourceScopePin') == source['sourceScopePin'] and
             close.get('schemaVersion') == 'RepositoryMinimumArchiveClose/v1' and
             close.get('operationId') == point['backupId'] and close.get('archiveReaderClosed') is True,
             'ARCHIVE_ORIGINAL_PUBLICATION_INVALID')
        need(point['manifestPin']['sha256'] not in bindings, 'ARCHIVE_MANIFEST_DUPLICATE')
        points.append(pin)
        bindings[point['manifestPin']['sha256']] = binding_pin
        evidence.extend([pin, point['manifestPin'], binding_pin])

    visit(matches[0])
    resolved = deepcopy(source)
    resolved.pop('archiveCatalogue')
    resolved.update(recoveryPoints={reference: matches[0]}, repositoryPointPins=points,
                    repositoryBindingPinsByManifestSha256=bindings, parentChains={})
    return resolved, dict(schemaVersion='SmallAppArchivePointBinding/v1', reference=reference,
        sourceConfigRef=request['sourceConfigRef'], pointPin=matches[0], evidencePins=evidence)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def admit_source_catalogue(value, access, request):
    exact(value, 'observedAt applications', 'SOURCE_CATALOGUE_RESPONSE_INVALID')
    from recovery_control_smallapp_native import stamp
    age = (datetime.now(timezone.utc) - stamp(value['observedAt'])).total_seconds()
    need(0 <= age <= 60, 'SOURCE_CATALOGUE_EXPIRED')
    need(type(value['applications']) is list, 'SOURCE_CATALOGUE_RESPONSE_INVALID')
    matches = [row for row in value['applications'] if row.get('sourceConfigRef') == request['sourceConfigRef']]
    need(len(matches) == 1 and matches[0].get('applicationId') == access['applicationId'] and
         matches[0].get('engineSelectionRef') == access['engineSelectionRef'] and
         matches[0].get('historyErrorCode') is None and
         request['recoveryPointRef'] in matches[0].get('recoveryPointRefs', []), 'SOURCE_POINT_NOT_CURRENTLY_ELIGIBLE')
    return matches[0]['recoveryPointRefs']


def source_admits(native, source, request):
    access = native.document(source['archiveCatalogue']['sourceAdmissionPin'])
    exact(access, 'schemaVersion selectionUrl authCredentialRef applicationId engineSelectionRef',
          'SOURCE_CATALOGUE_ACCESS_INVALID')
    need(access['schemaVersion'] == 'SmallAppSourceCatalogueAccess/v1', 'SOURCE_CATALOGUE_ACCESS_INVALID')
    url = urllib.parse.urlsplit(access['selectionUrl'])
    need(url.scheme in ('http','https') and url.hostname and url.port and not url.username and not url.password
         and url.path == '/selections' and not url.query and not url.fragment, 'SOURCE_CATALOGUE_URL_INVALID')
    from recovery_control_smallapp_http import credential
    headers = {'Authorization':credential(access['authCredentialRef']), 'Accept':'application/json'}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(urllib.request.Request(access['selectionUrl'],headers=headers), timeout=10) as response:
            need(response.status == 200, 'SOURCE_CATALOGUE_UNAVAILABLE')
            raw = response.read(1048577)
            need(len(raw) <= 1048576, 'SOURCE_CATALOGUE_RESPONSE_TOO_LARGE')
            value = decode(raw)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError('SOURCE_CATALOGUE_UNAVAILABLE') from None
    return admit_source_catalogue(value, access, request)


def for_request(native, configuration, request, owner_pin):
    owner = native.document(owner_pin)
    source = owner['sources'][request['sourceConfigRef']]
    admitted = source_admits(native, source, request)
    resolved, binding = bind_archive_chain(source, request)
    need(all(read_document(pin, source['archiveCatalogue']['maximumMetadataBytes'])['backupId'] in admitted
         for pin in resolved['repositoryPointPins']), 'SOURCE_PARENT_NOT_CURRENTLY_ELIGIBLE')
    owner = deepcopy(owner)
    owner['sources'][request['sourceConfigRef']] = resolved
    from recovery_control_smallapp_native import directory
    root = Path(configuration['taskRoot'])/'request-configurations'
    root.mkdir(mode=0o700, exist_ok=True)
    directory(root, configuration['taskRoot'])
    root = root/opaque(request['operationId'])
    root.mkdir(mode=0o700, exist_ok=True)
    directory(root, configuration['taskRoot'])

    def immutable(name, document):
        path = root/name
        if path.exists():
            reference = executor.pin(path)
            need(native.raw(reference) == canonical(document), 'ORIGINAL_RESTORE_CONFIGURATION_CHANGED')
            return reference
        persist(path, document)
        return executor.pin(path)

    immutable('restore-inputs.json', dict(request=request, ownerConfigurationPin=owner_pin))
    binding_pin = immutable('archive-point.json', binding)
    return immutable('recovery.json', owner), binding_pin
