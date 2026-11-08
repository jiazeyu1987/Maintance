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
    fields = 'schemaVersion maximumPointFiles maximumMetadataBytes sourceAdmissionPin'
    multiple_scopes = type(catalogue) is dict and catalogue.get('schemaVersion') == 'RecoveryArchiveCatalogue/v2'
    exact(catalogue, fields + (' sourceScopePins' if multiple_scopes else ''),
          'ARCHIVE_CATALOGUE_FIELDS_INVALID')
    need(catalogue['schemaVersion'] in ('RecoveryArchiveCatalogue/v1', 'RecoveryArchiveCatalogue/v2') and
         type(catalogue['maximumPointFiles']) is int and 1 <= catalogue['maximumPointFiles'] <= 10000 and
         type(catalogue['maximumMetadataBytes']) is int and
         1024 <= catalogue['maximumMetadataBytes'] <= 64 * 1024 * 1024, 'ARCHIVE_CATALOGUE_LIMIT_INVALID')
    maximum = catalogue['maximumMetadataBytes']
    roots = [Path(value) for value in source['archiveRoots']]
    need(roots and len(roots) == len(set(roots)) and all(root.is_absolute() and
         root.resolve() == root and root.is_dir() for root in roots), 'ARCHIVE_ROOT_UNAVAILABLE')
    scopes = catalogue['sourceScopePins'] if multiple_scopes else [source['sourceScopePin']]
    need(type(scopes) is list and 1 <= len(scopes) <= 32 and
         source['sourceScopePin'] in scopes and len({canonical(pin) for pin in scopes}) == len(scopes),
         'ARCHIVE_SOURCE_SCOPES_INVALID')
    identity = read_document(source['sourceScopePin'], maximum)['sourceIdentityPin']
    identities = {canonical(source['sourceScopePin']): identity}
    if multiple_scopes:
        read_document(identity, maximum)
        for pin in scopes:
            scope = read_document(pin, maximum)
            selected_identity = scope.get('sourceIdentityPin')
            need(scope.get('schemaVersion') == 'RecoverySourceScope/v1' and
                 type(selected_identity) is dict and all(selected_identity.get(key) == identity[key]
                     for key in ('bytes','sha256')), 'ARCHIVE_SCOPE_IDENTITY_MISMATCH')
            # Historical installations can retain identical identity bytes at
            # different immutable paths. Verify each explicit original pin;
            # do not translate manifest pins or infer identity from a host name.
            read_document(selected_identity, maximum)
            identities[canonical(pin)] = selected_identity
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
    points, bindings, evidence, visiting = [], {}, [], set()
    selected_scope = None

    def visit(pin):
        nonlocal selected_scope
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
             manifest['sourceIdentityPin'] in identities.values(), 'ARCHIVE_SOURCE_BINDING_INVALID')
        binding_pin = executor.pin(path.parent/'recovery-repository-binding.json')
        binding = read_document(binding_pin, maximum)
        exact(binding, 'schemaVersion backupId generationId repositoryPointPin manifestPin sourceScopePin '
              'recoveryMaterialPin objectContentIndexPin', 'ARCHIVE_REPOSITORY_BINDING_INVALID')
        need(binding['schemaVersion'] == 'RecoveryRepositoryBinding/v1' and
             binding['repositoryPointPin'] == pin and binding['manifestPin'] == point['manifestPin'] and
             binding['sourceScopePin'] in scopes and
             manifest['sourceIdentityPin'] == identities[canonical(binding['sourceScopePin'])] and
             binding['backupId'] == point['backupId'] and binding['generationId'] == point['generationId'],
             'ARCHIVE_SOURCE_BINDING_INVALID')
        if selected_scope is None:
            selected_scope = binding['sourceScopePin']
        need(binding['sourceScopePin'] == selected_scope, 'ARCHIVE_CHAIN_SCOPE_MISMATCH')
        parents = point['parentPointPins']
        need(type(parents) is list, 'ARCHIVE_PARENT_PREFIX_INVALID')
        if point['pointType'] == 'FULL':
            need(not parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
        else:
            need(parents, 'ARCHIVE_PARENT_PREFIX_INVALID')
            visit(parents[-1])
            need(parents == points and all(read_document(parent, maximum)['generationId'] ==
                 point['generationId'] for parent in points), 'ARCHIVE_PARENT_PREFIX_INVALID')
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
             readback.get('sourceScopePin') == selected_scope and
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
    resolved.update(sourceScopePin=selected_scope, recoveryPoints={reference: matches[0]}, repositoryPointPins=points,
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


def archive_references(native, configuration, source_ref):
    """Explicit historical admission, independent of native capture/epoch history.

    An immutable index selects the original points to admit. NAS discovery alone
    never authorizes a new source or a formerly quarantined point.
    """
    reference = configuration.get('archiveRestoreCatalogues', {}).get(source_ref)
    if reference is None:
        return {}
    value = native.document(reference)
    exact(value, 'schemaVersion sourceConfigRef source pointPins', 'ARCHIVE_ADMISSION_FIELDS_INVALID')
    need(value['schemaVersion'] == 'SmallAppArchiveRestoreCatalogue/v1' and
         value['sourceConfigRef'] == source_ref, 'ARCHIVE_CATALOGUE_SOURCE_MISMATCH')
    pins = value['pointPins']
    need(type(pins) is list and 1 <= len(pins) <= 1000 and
         len({canonical(pin) for pin in pins}) == len(pins), 'ARCHIVE_ADMISSION_POINTS_INVALID')
    source = value['source']
    maximum = source['archiveCatalogue']['maximumMetadataBytes']
    admitted = {}
    for pin in pins:
        point = read_document(pin, maximum)
        point_ref = opaque(point['backupId'])
        need(point_ref not in admitted, 'ARCHIVE_POINT_REFERENCE_AMBIGUOUS')
        admitted[point_ref] = pin
    for point_ref, pin in admitted.items():
        resolved, binding = bind_archive_chain(source, dict(sourceConfigRef=source_ref,recoveryPointRef=point_ref))
        need(binding['pointPin'] == pin, 'ARCHIVE_ADMISSION_POINT_CHANGED')
        for parent in resolved['repositoryPointPins']:
            parent_ref = read_document(parent, maximum)['backupId']
            need(admitted.get(parent_ref) == parent, 'ARCHIVE_PARENT_NOT_ADMITTED')
            quarantine = (Path(configuration['registryRoot'])/'quarantined-points'/
                          (opaque(parent_ref) + '.json'))
            # A preserved marker blocks archive admission even if its former
            # native selector is no longer installed. Never bypass it by using
            # a different restore catalogue or by repinning its archive.
            need(not quarantine.exists() and not quarantine.is_symlink(), 'POINT_QUARANTINED')
    return admitted
